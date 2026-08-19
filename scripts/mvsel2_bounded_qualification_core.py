#!/usr/bin/env python3
"""Authority-cache and orphan-checkpoint wrapper for REV8 qualification.

This wrapper keeps the frozen REV8 engine and the metadata-streaming missing-plan
recovery launcher unchanged while supplying two qualification-only adaptations:

* reuse the first production TARGET-DATA2B reference and native-forward MVIDX
  objects opened in each process so missing-plan recovery does not duplicate
  large mapped authorities; and
* when MVSTATE2 SQLite pointer rows are absent, perform a bounded read-only scan
  under the production ``.mdstats`` root for immutable
  ``target-multi-view-selection-state-v2-*`` bundles, synthesize the canonical
  pointer for an unambiguous bundle, and feed that same pointer set to plan
  recovery and LQ2/LQ3/LQ4.

No production file is created, changed, or repaired.  Discovered bundles are
still authenticated by the normal metadata-streaming/full-state readers before
they can serve as evidence.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from mdstats.training_data import target_coverage_store as _reference_store
from mdstats.training_data import target_coverage_sparse_index_store as _forward_store

_ORIGINAL_READ_REFERENCE = _reference_store.read_target_coverage_native_record
_ORIGINAL_READ_FORWARD = (
    _forward_store.read_target_coverage_sparse_index_forward_view_native_record
)
_REFERENCE_CACHE: dict[tuple[str, str], Any] = {}
_FORWARD_CACHE: dict[tuple[str, str], Any] = {}


def _cache_key(pointer: Mapping[str, Any], root: str | Path) -> tuple[str, str]:
    identity = str(
        pointer.get("content_digest")
        or pointer.get("pointer_digest")
        or pointer.get("sha256")
        or repr(sorted(pointer.items()))
    )
    return str(Path(root).resolve()), identity


def _cached_read_reference(pointer: Mapping[str, Any], root: str | Path) -> Any:
    key = _cache_key(pointer, root)
    cached = _REFERENCE_CACHE.get(key)
    if cached is not None:
        return cached
    value = _ORIGINAL_READ_REFERENCE(pointer, root)
    _REFERENCE_CACHE[key] = value
    return value


def _cached_read_forward(pointer: Mapping[str, Any], root: str | Path) -> Any:
    key = _cache_key(pointer, root)
    cached = _FORWARD_CACHE.get(key)
    if cached is not None:
        return cached
    value = _ORIGINAL_READ_FORWARD(pointer, root)
    _FORWARD_CACHE[key] = value
    return value


_reference_store.read_target_coverage_native_record = _cached_read_reference
_forward_store.read_target_coverage_sparse_index_forward_view_native_record = (
    _cached_read_forward
)

import mvsel2_bounded_qualification_recovery as recovery

_ORIGINAL_RECOVERY_ROWS_ALL = recovery._checkpoint_rows_all
_ORIGINAL_RECOVERY_JSON_DUMP = recovery._json_dump

_BUNDLE_PREFIX = "target-multi-view-selection-state-v2-"
_MAX_DISCOVERY_DEPTH = 4
_MAX_DISCOVERY_DIRECTORIES = 4096
_MAX_DISCOVERY_BUNDLES = 128
_ROWS_CACHE: dict[str, dict[str, dict[int, dict[str, Any]]]] = {}
_DISCOVERY_REPORT: dict[str, Any] | None = None


def _database_path(connection: sqlite3.Connection) -> Path:
    return recovery._database_path(connection)


def _discover_manifest_paths(root: Path) -> tuple[list[Path], int]:
    """Find MVSTATE2 manifests with a bounded directory-only walk."""

    root = root.resolve()
    queue: list[tuple[Path, int]] = [(root, 0)]
    manifests: list[Path] = []
    directories = 0
    while queue:
        directory, depth = queue.pop(0)
        directories += 1
        if directories > _MAX_DISCOVERY_DIRECTORIES:
            raise RuntimeError(
                "MVSTATE2 orphan discovery exceeded bounded directory budget "
                f"({_MAX_DISCOVERY_DIRECTORIES}) under {root}"
            )
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            raise RuntimeError(
                f"MVSTATE2 orphan discovery cannot scan {directory}: {exc}"
            ) from exc
        for entry in entries:
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if not is_dir:
                continue
            child = Path(entry.path)
            if child.name.startswith(_BUNDLE_PREFIX):
                manifest = child / "manifest.json"
                if manifest.is_file():
                    manifests.append(manifest.resolve())
                    if len(manifests) > _MAX_DISCOVERY_BUNDLES:
                        raise RuntimeError(
                            "MVSTATE2 orphan discovery exceeded bounded bundle "
                            f"budget ({_MAX_DISCOVERY_BUNDLES}) under {root}"
                        )
                # Content-addressed bundle directories are leaves for discovery.
                continue
            if depth < _MAX_DISCOVERY_DEPTH:
                queue.append((child, depth + 1))
    manifests.sort(key=lambda path: str(path))
    return manifests, directories


def _pointer_from_manifest(root: Path, manifest_path: Path) -> tuple[str, int, dict[str, Any]] | None:
    """Build the canonical pointer from a minimally valid MVSTATE2 manifest."""

    from mdstats.training_data._common import digest, sha256_file_cached
    from mdstats.training_data.target_multi_view_selection_state_v2 import (
        MVSTATE2_PERSISTENCE_VERSION,
        MVSTATE2_POINTER_SCHEMA,
        MVSTATE2_SCHEMA,
    )

    root = root.resolve()
    manifest_path = manifest_path.resolve()
    if root not in manifest_path.parents:
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(manifest, dict):
        return None
    if (
        manifest.get("schema") != MVSTATE2_SCHEMA
        or manifest.get("persistence_version") != MVSTATE2_PERSISTENCE_VERSION
    ):
        return None
    identity = manifest.get("identity")
    if not isinstance(identity, Mapping):
        return None
    domain = str(identity.get("label_domain_id", "")).strip()
    try:
        size = int(manifest.get("selected_count", -1))
    except Exception:
        return None
    content_digest = str(manifest.get("content_digest", ""))
    if not domain or size < 1 or len(content_digest) != 64:
        return None
    relative = manifest_path.relative_to(root)
    pointer: dict[str, Any] = {
        "schema": MVSTATE2_POINTER_SCHEMA,
        "persistence_version": MVSTATE2_PERSISTENCE_VERSION,
        "relative_path": str(relative),
        "sha256": sha256_file_cached(manifest_path),
        "content_digest": content_digest,
    }
    pointer["pointer_digest"] = digest(pointer)
    return domain, size, pointer


def _checkpoint_rows_all(connection: sqlite3.Connection) -> dict[str, dict[int, dict[str, Any]]]:
    """Return DB checkpoint pointers supplemented by unique orphan bundles."""

    global _DISCOVERY_REPORT

    database = _database_path(connection).resolve()
    cache_key = str(database)
    cached = _ROWS_CACHE.get(cache_key)
    if cached is not None:
        return {
            domain: {size: dict(pointer) for size, pointer in rows.items()}
            for domain, rows in cached.items()
        }

    db_rows = _ORIGINAL_RECOVERY_ROWS_ALL(connection)
    merged: dict[str, dict[int, dict[str, Any]]] = {
        domain: {size: dict(pointer) for size, pointer in rows.items()}
        for domain, rows in db_rows.items()
    }
    root = database.parent
    manifests, directories_scanned = _discover_manifest_paths(root)
    candidates: dict[str, dict[int, list[tuple[Path, dict[str, Any]]]]] = {}
    rejected_manifests = 0
    for manifest in manifests:
        parsed = _pointer_from_manifest(root, manifest)
        if parsed is None:
            rejected_manifests += 1
            continue
        domain, size, pointer = parsed
        candidates.setdefault(domain, {}).setdefault(size, []).append(
            (manifest, pointer)
        )

    recovered: dict[str, dict[str, Any]] = {}
    ambiguous: dict[str, dict[str, Any]] = {}
    for domain, by_size in candidates.items():
        for size, items in by_size.items():
            if size in merged.get(domain, {}):
                continue
            by_digest: dict[str, tuple[Path, dict[str, Any]]] = {}
            for manifest, pointer in items:
                by_digest.setdefault(str(pointer["content_digest"]), (manifest, pointer))
            if len(by_digest) != 1:
                ambiguous.setdefault(domain, {})[str(size)] = {
                    "content_digests": sorted(by_digest),
                    "manifests": sorted(str(item[0]) for item in items),
                }
                continue
            manifest, pointer = next(iter(by_digest.values()))
            merged.setdefault(domain, {})[size] = dict(pointer)
            recovered.setdefault(domain, {})[str(size)] = {
                "content_digest": str(pointer["content_digest"]),
                "manifest": str(manifest),
                "source": "ORPHAN_BUNDLE_RECOVERED",
            }

    _DISCOVERY_REPORT = {
        "schema": "mdstats.mvsel2-qualification-checkpoint-discovery.v1",
        "root": str(root),
        "directories_scanned": directories_scanned,
        "bundle_manifests_found": len(manifests),
        "rejected_manifests": rejected_manifests,
        "db_pointer_sizes": {
            domain: sorted(int(size) for size in rows)
            for domain, rows in db_rows.items()
        },
        "recovered": recovered,
        "ambiguous": ambiguous,
        "production_mutated": False,
    }

    if ambiguous:
        raise RuntimeError(
            "MVSTATE2 orphan discovery found ambiguous content-addressed bundles; "
            f"details={ambiguous}"
        )
    if not any(merged.values()) and not manifests:
        raise RuntimeError(
            "no MVSTATE2 checkpoint pointer rows and no orphan MVSTATE2 bundle "
            f"manifests were found under production root {root}; "
            f"directories_scanned={directories_scanned}"
        )

    _ROWS_CACHE[cache_key] = {
        domain: {size: dict(pointer) for size, pointer in rows.items()}
        for domain, rows in merged.items()
    }
    return merged


def _checkpoint_rows_ro(
    connection: sqlite3.Connection, domain: str
) -> dict[int, dict[str, Any]]:
    rows = _checkpoint_rows_all(connection)
    return {
        int(size): dict(pointer)
        for size, pointer in rows.get(str(domain), {}).items()
    }


def _json_dump(path: Path, payload: Mapping[str, Any]) -> None:
    # Attach discovery evidence whether plan recovery succeeded or failed.
    if _DISCOVERY_REPORT is not None:
        if recovery._RECOVERY is not None:
            recovery._RECOVERY["checkpoint_discovery"] = _DISCOVERY_REPORT
        elif Path(path).name == "worker.json":
            enriched = dict(payload)
            enriched["checkpoint_discovery"] = _DISCOVERY_REPORT
            payload = enriched
    _ORIGINAL_RECOVERY_JSON_DUMP(path, payload)


# One unified discovery authority feeds both the missing-plan reconstruction and
# the frozen worker's later LQ2/LQ3/LQ4 checkpoint lookup.
recovery._checkpoint_rows_all = _checkpoint_rows_all
recovery.engine._checkpoint_rows_ro = _checkpoint_rows_ro
recovery.engine.json_dump = _json_dump

# The frozen engine constructs its worker subprocess from engine.__file__.  Keep
# every worker launch routed through this wrapper so both the no-duplicate
# authority cache and orphan-bundle discovery apply in supervisor/worker mode.
recovery.engine.__file__ = __file__


if __name__ == "__main__":
    raise SystemExit(recovery.engine.main())
