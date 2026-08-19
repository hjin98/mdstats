from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .storage_accounting import CampaignOwnershipBoundary

COLD_ARCHIVE_MANIFEST_SCHEMA = "mdstats.mlff-cold-archive-manifest.v1"
DEDUPLICATION_REPORT_SCHEMA = "mdstats.mlff-immutable-deduplication-report.v1"
RESTORE_RECEIPT_SCHEMA = "mdstats.mlff-cold-archive-restore.v1"


class StorageArchiveError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _workspace_relative(path: Path, workspace: Path) -> str:
    absolute = Path(os.path.abspath(os.fspath(path)))
    root = Path(os.path.abspath(os.fspath(workspace)))
    try:
        rel = absolute.relative_to(root)
    except ValueError as exc:
        raise StorageArchiveError(f"archive path escapes workspace: {path}") from exc
    if not rel.parts or ".." in rel.parts:
        raise StorageArchiveError(f"invalid archive-relative path: {path}")
    return rel.as_posix()


def _normalize_roots(paths: Sequence[Path]) -> tuple[Path, ...]:
    unique = sorted({Path(os.path.abspath(os.fspath(p))) for p in paths}, key=lambda p: (len(p.parts), str(p)))
    kept: list[Path] = []
    for path in unique:
        if any(path == parent or parent in path.parents for parent in kept):
            continue
        kept.append(path)
    return tuple(kept)


def collect_archive_entries(
    workspace: Path,
    roots: Sequence[Path],
    *,
    boundary: CampaignOwnershipBoundary,
) -> tuple[tuple[Path, ...], tuple[dict[str, Any], ...]]:
    """Collect a complete, symlink-free immutable archive inventory."""

    root = Path(os.path.abspath(os.fspath(workspace)))
    normalized = _normalize_roots([p for p in roots if p.exists() or p.is_symlink()])
    entries: list[dict[str, Any]] = []
    for candidate in normalized:
        if candidate.is_symlink():
            raise StorageArchiveError(f"refusing to archive symlink root: {candidate}")
        authorized, detail = boundary.traversal_authorization(candidate)
        if not authorized:
            raise StorageArchiveError(f"archive root is not campaign-owned: {detail}: {candidate}")
        if candidate.is_file():
            scan: Iterable[Path] = (candidate,)
        elif candidate.is_dir():
            scan = (candidate, *sorted(candidate.rglob("*")))
        else:
            raise StorageArchiveError(f"unsupported archive root type: {candidate}")
        for path in scan:
            if path.is_symlink():
                raise StorageArchiveError(f"refusing to archive symlink member: {path}")
            authorized, detail = boundary.destructive_authorization(path)
            if not authorized:
                raise StorageArchiveError(f"archive member is not campaign-owned: {detail}: {path}")
            st = path.lstat()
            rel = _workspace_relative(path, root)
            if stat.S_ISDIR(st.st_mode):
                entries.append({"path": rel, "kind": "directory", "mode": stat.S_IMODE(st.st_mode)})
            elif stat.S_ISREG(st.st_mode):
                entries.append({
                    "path": rel,
                    "kind": "file",
                    "size_bytes": int(st.st_size),
                    "mode": stat.S_IMODE(st.st_mode),
                    "sha256": _sha256_file(path),
                })
            else:
                raise StorageArchiveError(f"unsupported archive member type: {path}")
    entries.sort(key=lambda item: (item["path"], item["kind"]))
    return normalized, tuple(entries)


def verify_cold_archive(manifest_path: Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise StorageArchiveError(f"cannot read cold-archive manifest: {manifest_path}: {exc}") from exc
    if manifest.get("schema") != COLD_ARCHIVE_MANIFEST_SCHEMA:
        raise StorageArchiveError(f"unsupported cold-archive manifest schema: {manifest.get('schema')!r}")
    expected_manifest_digest = manifest.get("manifest_content_digest")
    observed_manifest_digest = _canonical_digest({k: v for k, v in manifest.items() if k != "manifest_content_digest"})
    if expected_manifest_digest != observed_manifest_digest:
        raise StorageArchiveError("cold-archive manifest content digest mismatch")
    archive_path = manifest_path.parent / str(manifest.get("archive_file", ""))
    if not archive_path.is_file():
        raise StorageArchiveError(f"cold archive is missing: {archive_path}")
    observed_archive_sha = _sha256_file(archive_path)
    if observed_archive_sha != manifest.get("archive_sha256"):
        raise StorageArchiveError("cold archive SHA-256 mismatch")

    expected = {str(item["path"]): item for item in manifest.get("entries", [])}
    observed: dict[str, dict[str, Any]] = {}
    try:
        with tarfile.open(archive_path, mode="r:gz") as tar:
            for member in tar:
                name = member.name.rstrip("/")
                path = Path(name)
                if path.is_absolute() or ".." in path.parts or not path.parts:
                    raise StorageArchiveError(f"unsafe archive member path: {member.name!r}")
                if name in observed:
                    raise StorageArchiveError(f"duplicate archive member: {name}")
                if member.isdir():
                    observed[name] = {"path": name, "kind": "directory", "mode": member.mode & 0o7777}
                elif member.isfile():
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise StorageArchiveError(f"cannot read archive member: {name}")
                    h = hashlib.sha256(); count = 0
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        h.update(chunk); count += len(chunk)
                    observed[name] = {
                        "path": name, "kind": "file", "mode": member.mode & 0o7777,
                        "size_bytes": count, "sha256": h.hexdigest(),
                    }
                else:
                    raise StorageArchiveError(f"unsupported non-file archive member: {name}")
    except StorageArchiveError:
        raise
    except Exception as exc:
        raise StorageArchiveError(f"cold archive cannot be verified: {exc}") from exc

    if set(observed) != set(expected):
        missing = sorted(set(expected) - set(observed))[:5]
        extra = sorted(set(observed) - set(expected))[:5]
        raise StorageArchiveError(f"cold archive member set mismatch; missing={missing}, extra={extra}")
    for name, item in expected.items():
        got = observed[name]
        for key in ("kind", "mode"):
            if got.get(key) != item.get(key):
                raise StorageArchiveError(f"cold archive member metadata mismatch for {name}: {key}")
        if item["kind"] == "file":
            for key in ("size_bytes", "sha256"):
                if got.get(key) != item.get(key):
                    raise StorageArchiveError(f"cold archive member content mismatch for {name}: {key}")
    return manifest


def create_cold_archive(
    workspace: Path,
    roots: Sequence[Path],
    *,
    boundary: CampaignOwnershipBoundary,
    archive_directory: Path,
    source_actions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    workspace = Path(os.path.abspath(os.fspath(workspace)))
    archive_directory = Path(archive_directory)
    authorized, detail = boundary.destructive_authorization(archive_directory)
    if not authorized:
        raise StorageArchiveError(f"archive directory is not campaign-owned: {detail}: {archive_directory}")
    normalized_roots, entries = collect_archive_entries(workspace, roots, boundary=boundary)
    if not entries:
        raise StorageArchiveError("no eligible hot artifacts were found for cold archival")
    inventory = {
        "workspace_layout_version": 1,
        "roots": [_workspace_relative(p, workspace) for p in normalized_roots],
        "entries": list(entries),
    }
    archive_id = _canonical_digest(inventory)[:32]
    archive_directory.mkdir(parents=True, exist_ok=True)
    archive_name = f"cold-{archive_id}.tar.gz"
    manifest_name = f"cold-{archive_id}.manifest.json"
    archive_path = archive_directory / archive_name
    manifest_path = archive_directory / manifest_name

    preexisting_pair = manifest_path.is_file() and archive_path.is_file()
    if preexisting_pair:
        manifest = verify_cold_archive(manifest_path)
        if manifest.get("archive_id") == archive_id:
            return manifest

    fd, tmp_name = tempfile.mkstemp(prefix=f".{archive_name}.", suffix=".tmp", dir=archive_directory)
    os.close(fd)
    tmp_archive = Path(tmp_name)
    try:
        # Dereference campaign-internal hardlinks so the archive remains fully
        # self-contained even after the content-addressed store/hot links vanish.
        with tarfile.open(tmp_archive, mode="w:gz", compresslevel=6, dereference=True) as tar:
            for item in entries:
                source = workspace / item["path"]
                info = tar.gettarinfo(str(source), arcname=item["path"])
                info.uid = 0; info.gid = 0; info.uname = ""; info.gname = ""; info.mtime = 0
                if item["kind"] == "directory":
                    tar.addfile(info)
                else:
                    with source.open("rb") as handle:
                        tar.addfile(info, handle)
        with tmp_archive.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(tmp_archive, archive_path)
        archive_sha = _sha256_file(archive_path)
        manifest: dict[str, Any] = {
            "schema": COLD_ARCHIVE_MANIFEST_SCHEMA,
            "archive_id": archive_id,
            "compression": "tar+gzip",
            "archive_file": archive_name,
            "archive_sha256": archive_sha,
            "archive_size_bytes": archive_path.stat().st_size,
            "hot_logical_bytes": sum(int(item.get("size_bytes", 0)) for item in entries if item["kind"] == "file"),
            "roots": inventory["roots"],
            "entries": list(entries),
            "source_actions": [dict(item) for item in source_actions],
        }
        manifest["manifest_content_digest"] = _canonical_digest({k: v for k, v in manifest.items() if k != "manifest_content_digest"})
        _atomic_json(manifest_path, manifest)
        verify_cold_archive(manifest_path)
        return manifest
    except Exception:
        tmp_archive.unlink(missing_ok=True)
        # A newly created pair is transactional: failed verification leaves no
        # archive receipt behind. Never remove a pre-existing authenticated pair.
        if not preexisting_pair:
            archive_path.unlink(missing_ok=True)
            manifest_path.unlink(missing_ok=True)
        raise


def restore_cold_archive(
    workspace: Path,
    manifest_path: Path,
    *,
    boundary: CampaignOwnershipBoundary,
) -> dict[str, Any]:
    workspace = Path(os.path.abspath(os.fspath(workspace)))
    manifest = verify_cold_archive(manifest_path)
    archive_path = Path(manifest_path).parent / manifest["archive_file"]
    staging_root = workspace / ".mdstats" / "archive-restore-staging" / str(manifest["archive_id"])
    authorized, detail = boundary.destructive_authorization(staging_root)
    if not authorized:
        raise StorageArchiveError(f"restore staging root is not campaign-owned: {detail}")
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)
    expected = {str(item["path"]): item for item in manifest["entries"]}
    try:
        with tarfile.open(archive_path, mode="r:gz") as tar:
            members = {member.name.rstrip("/"): member for member in tar}
            for name, item in expected.items():
                stage = staging_root / name
                if item["kind"] == "directory":
                    stage.mkdir(parents=True, exist_ok=True)
                    os.chmod(stage, int(item["mode"]))
                    continue
                stage.parent.mkdir(parents=True, exist_ok=True)
                stream = tar.extractfile(members[name])
                if stream is None:
                    raise StorageArchiveError(f"cannot extract archived file: {name}")
                with stage.open("wb") as handle:
                    shutil.copyfileobj(stream, handle, length=1024 * 1024)
                os.chmod(stage, int(item["mode"]))
                if stage.stat().st_size != int(item["size_bytes"]) or _sha256_file(stage) != item["sha256"]:
                    raise StorageArchiveError(f"restored staging file failed authentication: {name}")

        # Fail before installing anything if a conflicting hot file exists.
        for name, item in expected.items():
            destination = workspace / name
            authorized, detail = boundary.destructive_authorization(destination)
            if not authorized:
                raise StorageArchiveError(f"restore destination is not campaign-owned: {detail}: {destination}")
            if item["kind"] == "directory":
                if destination.exists() and not destination.is_dir():
                    raise StorageArchiveError(f"restore destination conflicts with non-directory: {destination}")
            elif destination.exists():
                if not destination.is_file() or destination.is_symlink():
                    raise StorageArchiveError(f"restore destination conflicts with non-file: {destination}")
                if destination.stat().st_size != int(item["size_bytes"]) or _sha256_file(destination) != item["sha256"]:
                    raise StorageArchiveError(f"restore destination already exists with different content: {destination}")

        restored_files = 0
        reused_files = 0
        directories = sorted((item for item in expected.values() if item["kind"] == "directory"), key=lambda x: len(Path(x["path"]).parts))
        for item in directories:
            destination = workspace / item["path"]
            destination.mkdir(parents=True, exist_ok=True)
            os.chmod(destination, int(item["mode"]))
        for name, item in expected.items():
            if item["kind"] != "file":
                continue
            destination = workspace / name
            if destination.exists():
                reused_files += 1
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging_root / name, destination)
            restored_files += 1

        for name, item in expected.items():
            if item["kind"] != "file":
                continue
            destination = workspace / name
            if destination.stat().st_size != int(item["size_bytes"]) or _sha256_file(destination) != item["sha256"]:
                raise StorageArchiveError(f"post-restore authentication failed: {destination}")
        return {
            "schema": RESTORE_RECEIPT_SCHEMA,
            "archive_id": manifest["archive_id"],
            "archive_sha256": manifest["archive_sha256"],
            "restored_files": restored_files,
            "already_present_files": reused_files,
            "verified_entry_count": len(expected),
        }
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def _iter_dedup_files(roots: Sequence[Path], boundary: CampaignOwnershipBoundary) -> Iterable[Path]:
    for root in _normalize_roots([p for p in roots if p.exists()]):
        if root.is_symlink():
            continue
        authorized, _ = boundary.traversal_authorization(root)
        if not authorized:
            continue
        scan = (root,) if root.is_file() else root.rglob("*")
        for path in scan:
            if path.is_symlink() or not path.is_file():
                continue
            authorized, _ = boundary.destructive_authorization(path)
            if authorized:
                yield path


def deduplicate_immutable_files(
    workspace: Path,
    roots: Sequence[Path],
    *,
    boundary: CampaignOwnershipBoundary,
    content_store: Path,
    apply: bool,
) -> dict[str, Any]:
    """Plan/apply exact-byte hardlink deduplication for frozen immutable files."""

    workspace = Path(os.path.abspath(os.fspath(workspace)))
    by_size: dict[int, list[Path]] = {}
    for path in _iter_dedup_files(roots, boundary):
        size = path.stat().st_size
        if size <= 0:
            continue
        by_size.setdefault(size, []).append(path)
    groups: list[dict[str, Any]] = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        by_hash: dict[str, list[Path]] = {}
        for path in paths:
            by_hash.setdefault(_sha256_file(path), []).append(path)
        for sha, members in by_hash.items():
            inode_groups = {(p.stat().st_dev, p.stat().st_ino) for p in members}
            if len(members) < 2 or len(inode_groups) < 2:
                continue
            groups.append({
                "sha256": sha,
                "size_bytes": size,
                "paths": sorted(_workspace_relative(p, workspace) for p in members),
                "unique_inode_count_before": len(inode_groups),
                "potential_reclaimed_bytes": size * (len(inode_groups) - 1),
            })
    groups.sort(key=lambda item: (-int(item["potential_reclaimed_bytes"]), item["sha256"]))
    reclaimed = 0
    linked = 0
    skipped: list[str] = []
    if apply and groups:
        authorized, detail = boundary.destructive_authorization(content_store)
        if not authorized:
            raise StorageArchiveError(f"content store is not campaign-owned: {detail}: {content_store}")
        for group in groups:
            sha = str(group["sha256"]); size = int(group["size_bytes"])
            members = [workspace / rel for rel in group["paths"]]
            object_path = content_store / "sha256" / sha[:2] / sha
            object_path.parent.mkdir(parents=True, exist_ok=True)
            if object_path.exists():
                if not object_path.is_file() or object_path.stat().st_size != size or _sha256_file(object_path) != sha:
                    raise StorageArchiveError(f"content-addressed object collision/corruption: {object_path}")
            else:
                source = members[0]
                if source.stat().st_dev != object_path.parent.stat().st_dev:
                    skipped.append(f"cross-device content object not deduplicated: {source}")
                    continue
                tmp = object_path.parent / f".{sha}.tmp-{os.getpid()}"
                tmp.unlink(missing_ok=True)
                os.link(source, tmp)
                os.replace(tmp, object_path)
            obj_stat = object_path.stat()
            for member in members:
                st = member.stat()
                if (st.st_dev, st.st_ino) == (obj_stat.st_dev, obj_stat.st_ino):
                    continue
                if st.st_dev != obj_stat.st_dev:
                    skipped.append(f"cross-device duplicate not deduplicated: {member}")
                    continue
                if member.stat().st_size != size or _sha256_file(member) != sha:
                    raise StorageArchiveError(f"deduplication source changed during operation: {member}")
                tmp = member.parent / f".{member.name}.dedup-{os.getpid()}"
                tmp.unlink(missing_ok=True)
                os.link(object_path, tmp)
                os.replace(tmp, member)
                linked += 1
                reclaimed += size
        # Remove orphan content objects that have no campaign path link.
        if content_store.exists():
            for object_path in content_store.rglob("*"):
                if object_path.is_file() and not object_path.is_symlink() and object_path.stat().st_nlink <= 1:
                    object_path.unlink()
    return {
        "schema": DEDUPLICATION_REPORT_SCHEMA,
        "applied": bool(apply),
        "group_count": len(groups),
        "groups": groups,
        "potential_reclaimed_bytes": sum(int(item["potential_reclaimed_bytes"]) for item in groups),
        "reclaimed_bytes_estimate": reclaimed,
        "links_replaced": linked,
        "skipped": skipped,
        "method": "same-filesystem-content-addressed-hardlink",
    }


def prune_orphan_content_store(content_store: Path, *, boundary: CampaignOwnershipBoundary) -> dict[str, int]:
    """Remove CAS objects whose only remaining hardlink is the store object itself."""

    content_store = Path(content_store)
    if not content_store.exists():
        return {"objects_removed": 0, "bytes_released_estimate": 0}
    authorized, detail = boundary.traversal_authorization(content_store)
    if not authorized:
        raise StorageArchiveError(f"content-store traversal is not campaign-owned: {detail}: {content_store}")
    removed = 0; released = 0
    for path in sorted(content_store.rglob("*"), reverse=True):
        if path.is_symlink():
            continue
        if path.is_file():
            auth, _ = boundary.destructive_authorization(path)
            if not auth:
                continue
            st = path.stat()
            if st.st_nlink <= 1:
                released += int(st.st_size)
                path.unlink()
                removed += 1
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    try:
        content_store.rmdir()
    except OSError:
        pass
    return {"objects_removed": removed, "bytes_released_estimate": released}
