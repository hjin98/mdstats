"""Durable normalized VASP frame-array cache for MLFF campaigns.

The cache is a performance artifact, not a scientific source of truth. Every
entry is bound to the immutable DATA2 source identity and control signature.

Schema v2 stores each normalized array as an independent ``.npy`` member. The
members can be opened read-only with ``mmap_mode='r'`` and shared by forked or
spawned workers without decoding one monolithic NPZ into private memory.
Schema-v1 NPZ entries remain readable.

Entries are **content-addressed and immutable**. A prepared campaign generation
binds exact member identities, so publishing new normalized content for the same
run must never overwrite or delete the bytes an already adopted generation still
requires. Writing an entry whose content identity already exists is a no-op that
reuses the published member, which is also what makes two generations share the
normalized payload of every unchanged run instead of copying it. The top-level
``frame-cache.json`` remains a convenience discovery alias for the most recently
finalized catalog; it is never the authority for a prepared generation.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Mapping

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    sha256_file_cached,
)
from .frame_catalog import FrameData

FRAME_CACHE_SCHEMA = "mdstats.mlff-frame-cache.v2"
FRAME_CACHE_LEGACY_SCHEMA = "mdstats.mlff-frame-cache.v1"
FRAME_CACHE_ENTRY_SCHEMA = "mdstats.mlff-frame-cache-entry.v2"
FRAME_CACHE_ENTRY_DIRECTORY = "entries"


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _safe_name(run_id: str) -> str:
    """Legacy schema-v1 NPZ name."""

    value = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]
    return f"run-{value}.npz"


def _safe_directory_name(run_id: str) -> str:
    value = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]
    return f"run-{value}"


def _scf_array(values: tuple[bool | None, ...]) -> np.ndarray:
    return np.asarray(
        [-1 if value is None else int(bool(value)) for value in values],
        dtype=np.int8,
    )


def _decode_scf(values: np.ndarray) -> tuple[bool | None, ...]:
    result: list[bool | None] = []
    for raw in np.asarray(values, dtype=np.int8).tolist():
        if raw == -1:
            result.append(None)
        elif raw in (0, 1):
            result.append(bool(raw))
        else:
            raise TrainingDataSerializationError(
                "Invalid tri-state SCF flag in frame cache."
            )
    return tuple(result)


class _HashingBinaryWriter:
    """Sequential binary writer used by ``np.save`` without a hash reread."""

    def __init__(self, handle: Any):
        self._handle = handle
        self._digest = hashlib.sha256()

    def write(self, payload: bytes | bytearray | memoryview) -> int:
        view = memoryview(payload)
        self._digest.update(view)
        return self._handle.write(view)

    def hexdigest(self) -> str:
        return self._digest.hexdigest()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._handle, name)


def _atomic_npy(path: Path, array: np.ndarray) -> tuple[str, tuple[int, ...], str]:
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    contiguous = np.asarray(array, order="C")
    try:
        with temporary.open("wb") as raw_handle:
            handle = _HashingBinaryWriter(raw_handle)
            np.save(handle, contiguous, allow_pickle=False)
            raw_handle.flush()
            os.fsync(raw_handle.fileno())
            sha256 = handle.hexdigest()
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return sha256, tuple(int(value) for value in contiguous.shape), contiguous.dtype.str


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> str:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(encoded).hexdigest()


def _payload_arrays(data: FrameData) -> dict[str, np.ndarray]:
    payload: dict[str, np.ndarray] = {
        "source_frame_indices": data.source_frame_indices,
        "frame_ids": data.frame_ids,
        "atomic_numbers": data.atomic_numbers,
        "pbc": data.pbc,
        "cells_angstrom": data.cells_angstrom,
        "fractional_positions": data.fractional_positions,
        "scf_iteration_limit_reached": _scf_array(
            data.scf_iteration_limit_reached
        ),
    }
    for name in (
        "steps",
        "times_ps",
        "energies_ev",
        "forces_ev_per_angstrom",
        "stresses_ev_per_angstrom3",
        "temperatures_kelvin",
    ):
        value = getattr(data, name)
        if value is not None:
            payload[name] = np.asarray(value)
    return payload


def _entry_identity(manifest: Mapping[str, Any]) -> str:
    """Content identity of one normalized entry, covering every member hash."""

    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def frame_cache_entry_relative_path(entry_identity: str) -> str:
    return f"{FRAME_CACHE_ENTRY_DIRECTORY}/{entry_identity}/arrays.json"


def authenticate_frame_data_cache_entry(
    entry_manifest_path: Path, run_id: str, entry_identity: str
) -> None:
    """Prove an already published entry still *is* what its identity names.

    The entry identity is the SHA-256 of the entry manifest's own canonical
    bytes, and that manifest names every member with its hash, shape, and
    dtype.  Authenticating the manifest and then loading it through the same
    verifying reader downstream uses is therefore complete member validation,
    and it reuses that reader rather than restating its rules here.
    """

    if _sha256_file(entry_manifest_path) != entry_identity:
        raise TrainingDataSerializationError(
            f"Published frame-cache entry {entry_identity[:12]}... for {run_id!r} "
            "does not contain the manifest its content identity names."
        )
    _load_v2_entry(entry_manifest_path, {"run_id": run_id}, verify_hashes=True)


def write_frame_data_cache_entry(
    run_id: str,
    source: Any,
    data: FrameData,
    directory: str | Path,
) -> dict[str, Any]:
    """Publish one normalized run immutably and return its manifest record.

    Every array is an independently authenticated NPY member. This removes NPZ
    decompression/materialization and lets later stages share immutable arrays
    through the operating-system page cache.

    The published location is derived from the entry content itself, so the
    same normalized bytes are written once and reused by every generation that
    binds them, and differing bytes never collide with -- or destroy -- an
    entry that a current or in-flight prepared generation still requires.
    """

    root = Path(directory)
    entries_root = root / FRAME_CACHE_ENTRY_DIRECTORY
    entries_root.mkdir(parents=True, exist_ok=True)
    if source.run_id != run_id:
        raise TrainingDataInputError("Frame-cache source/run identity mismatch.")
    if (
        data.n_frames != source.frame_count
        or data.n_atoms != source.composition.atom_count
    ):
        raise TrainingDataInputError(
            f"Frame-cache dimensions disagree for {run_id!r}."
        )

    temporary = entries_root / f".staging-{_safe_directory_name(run_id)}.{os.getpid()}.tmp"
    shutil.rmtree(temporary, ignore_errors=True)
    temporary.mkdir(parents=True)
    arrays = _payload_arrays(data)
    member_records: list[dict[str, Any]] = []
    try:
        for name in sorted(arrays):
            member_path = temporary / f"{name}.npy"
            sha256, shape, dtype = _atomic_npy(member_path, arrays[name])
            member_records.append(
                {
                    "name": name,
                    "relative_path": member_path.name,
                    "sha256": sha256,
                    "shape": list(shape),
                    "dtype": dtype,
                }
            )
        entry_manifest = {
            "schema": FRAME_CACHE_ENTRY_SCHEMA,
            "run_id": run_id,
            "source_identity_signature": source.source_identity_signature,
            "source_control_bundle_signature": source.source_control_bundle_signature,
            "frame_count": data.n_frames,
            "atom_count": data.n_atoms,
            "members": member_records,
        }
        entry_manifest_path = temporary / "arrays.json"
        entry_sha256 = _atomic_json(entry_manifest_path, entry_manifest)
        identity = _entry_identity(entry_manifest)
        destination = entries_root / identity
        if (destination / "arrays.json").is_file():
            # Content that already carries this identity is reused rather than
            # replaced, because another adopted generation may depend on it --
            # but only after it is *authenticated*, not merely found. An entry
            # manifest can be intact while one of the NPY members it names has
            # rotted, and a prepared generation that binds such an entry would
            # not fail until a downstream command loaded it.
            authenticate_frame_data_cache_entry(
                destination / "arrays.json", run_id, identity
            )
            shutil.rmtree(temporary, ignore_errors=True)
        else:
            try:
                os.replace(temporary, destination)
            except OSError:
                # A concurrent publisher won the race; its content must still
                # authenticate before this one adopts it.
                if not (destination / "arrays.json").is_file():
                    raise
                authenticate_frame_data_cache_entry(
                    destination / "arrays.json", run_id, identity
                )
                shutil.rmtree(temporary, ignore_errors=True)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return {
        "run_id": run_id,
        "source_identity_signature": source.source_identity_signature,
        "source_control_bundle_signature": source.source_control_bundle_signature,
        "frame_count": data.n_frames,
        "atom_count": data.n_atoms,
        "storage_kind": "npy_directory",
        "relative_path": frame_cache_entry_relative_path(identity),
        "entry_identity": identity,
        "sha256": entry_sha256,
        "arrays": sorted(arrays),
    }


def finalize_frame_data_cache(
    source_catalog: Any,
    records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    directory: str | Path,
    *,
    verify_entry_hashes: bool = True,
) -> Path:
    """Write the catalog-bound cache manifest after entry workers finish."""

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    source_by_run = {source.run_id: source for source in source_catalog.sources}
    by_run = {str(record["run_id"]): dict(record) for record in records}
    if set(by_run) != set(source_by_run):
        raise TrainingDataInputError(
            "Frame-cache records must cover the DATA2 catalog exactly."
        )
    normalized: list[dict[str, Any]] = []
    for run_id in sorted(source_by_run):
        source = source_by_run[run_id]
        record = by_run[run_id]
        if (
            record.get("source_identity_signature")
            != source.source_identity_signature
        ):
            raise TrainingDataInputError(
                f"Frame-cache source identity changed for {run_id!r}."
            )
        if (
            record.get("source_control_bundle_signature")
            != source.source_control_bundle_signature
        ):
            raise TrainingDataInputError(
                f"Frame-cache controls changed for {run_id!r}."
            )
        path = root / str(record.get("relative_path", ""))
        if not path.is_file():
            raise TrainingDataSerializationError(
                f"Frame-cache entry is missing for {run_id!r}."
            )
        expected_hash = str(record.get("sha256", ""))
        if len(expected_hash) != 64 or any(
            ch not in "0123456789abcdef" for ch in expected_hash
        ):
            raise TrainingDataSerializationError(
                f"Frame-cache entry hash is invalid for {run_id!r}."
            )
        if verify_entry_hashes and _sha256_file(path) != expected_hash:
            raise TrainingDataSerializationError(
                f"Frame-cache entry changed for {run_id!r}."
            )
        normalized.append(record)
    manifest = {
        "schema": FRAME_CACHE_SCHEMA,
        "source_catalog_digest": source_catalog.content_digest,
        "records": normalized,
    }
    path = root / "frame-cache.json"
    _atomic_json(path, manifest)
    return path


def write_frame_data_cache(
    source_catalog: Any,
    frame_data_by_run: Mapping[str, FrameData],
    directory: str | Path,
) -> Path:
    """Atomically write normalized frame arrays for later campaign stages."""

    source_by_run = {source.run_id: source for source in source_catalog.sources}
    if set(source_by_run) != set(frame_data_by_run):
        raise TrainingDataInputError(
            "Frame-cache run IDs must match the DATA2 catalog."
        )
    records = [
        write_frame_data_cache_entry(
            run_id,
            source_by_run[run_id],
            frame_data_by_run[run_id],
            directory,
        )
        for run_id in sorted(source_by_run)
    ]
    return finalize_frame_data_cache(source_catalog, records, directory)


def _contained_member(entry_root: Path, relative_path: str) -> Path:
    member = (entry_root / relative_path).resolve()
    try:
        member.relative_to(entry_root.resolve())
    except ValueError as exc:
        raise TrainingDataSerializationError(
            "Frame-cache member escapes its entry directory."
        ) from exc
    if not member.is_file():
        raise TrainingDataSerializationError("Frame-cache array member is missing.")
    return member


def _load_v2_entry(
    path: Path,
    record: Mapping[str, Any],
    *,
    verify_hashes: bool,
) -> FrameData:
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrainingDataSerializationError(
            "Normalized frame-cache entry manifest is invalid."
        ) from exc
    if entry.get("schema") != FRAME_CACHE_ENTRY_SCHEMA:
        raise TrainingDataSerializationError(
            "Unsupported normalized frame-cache entry schema."
        )
    if str(entry.get("run_id")) != str(record["run_id"]):
        raise TrainingDataSerializationError("Frame-cache entry run ID changed.")
    member_records = {
        str(item["name"]): item for item in entry.get("members", ())
    }
    required = {
        "source_frame_indices",
        "frame_ids",
        "atomic_numbers",
        "pbc",
        "cells_angstrom",
        "fractional_positions",
        "scf_iteration_limit_reached",
    }
    if not required.issubset(member_records):
        raise TrainingDataSerializationError("Frame cache is incomplete.")
    arrays: dict[str, np.ndarray] = {}
    entry_root = path.parent
    for name, member_record in member_records.items():
        member_path = _contained_member(
            entry_root, str(member_record["relative_path"])
        )
        if verify_hashes and _sha256_file(member_path) != str(
            member_record["sha256"]
        ):
            raise TrainingDataSerializationError(
                f"Frame-cache array hash mismatch for {name!r}."
            )
        try:
            array = np.load(member_path, mmap_mode="r", allow_pickle=False)
        except Exception as exc:
            raise TrainingDataSerializationError(
                f"Cannot read frame-cache array {name!r}."
            ) from exc
        if (
            list(array.shape) != list(member_record.get("shape", ()))
            or array.dtype.str != str(member_record.get("dtype"))
        ):
            raise TrainingDataSerializationError(
                f"Frame-cache array metadata mismatch for {name!r}."
            )
        arrays[name] = array

    optional = lambda name: None if name not in arrays else arrays[name]
    constructor = (
        FrameData._from_authenticated_arrays if verify_hashes else FrameData
    )
    kwargs = dict(
        source_frame_indices=arrays["source_frame_indices"],
        frame_ids=arrays["frame_ids"],
        steps=optional("steps"),
        times_ps=optional("times_ps"),
        atomic_numbers=arrays["atomic_numbers"],
        pbc=arrays["pbc"],
        cells_angstrom=arrays["cells_angstrom"],
        fractional_positions=arrays["fractional_positions"],
        energies_ev=optional("energies_ev"),
        forces_ev_per_angstrom=optional("forces_ev_per_angstrom"),
        stresses_ev_per_angstrom3=optional("stresses_ev_per_angstrom3"),
        temperatures_kelvin=optional("temperatures_kelvin"),
        scf_iteration_limit_reached=_decode_scf(
            arrays["scf_iteration_limit_reached"]
        ),
    )
    if verify_hashes:
        kwargs.update(
            expected_n_frames=int(entry["frame_count"]),
            expected_n_atoms=int(entry["atom_count"]),
        )
    return constructor(**kwargs)


def _load_v1_entry(path: Path) -> FrameData:
    with np.load(path, allow_pickle=False) as arrays:
        names = set(arrays.files)
        required = {
            "source_frame_indices",
            "frame_ids",
            "atomic_numbers",
            "pbc",
            "cells_angstrom",
            "fractional_positions",
            "scf_iteration_limit_reached",
        }
        if not required.issubset(names):
            raise TrainingDataSerializationError("Frame cache is incomplete.")
        optional = lambda name: None if name not in names else arrays[name]
        return FrameData(
            source_frame_indices=arrays["source_frame_indices"],
            frame_ids=arrays["frame_ids"],
            steps=optional("steps"),
            times_ps=optional("times_ps"),
            atomic_numbers=arrays["atomic_numbers"],
            pbc=arrays["pbc"],
            cells_angstrom=arrays["cells_angstrom"],
            fractional_positions=arrays["fractional_positions"],
            energies_ev=optional("energies_ev"),
            forces_ev_per_angstrom=optional("forces_ev_per_angstrom"),
            stresses_ev_per_angstrom3=optional("stresses_ev_per_angstrom3"),
            temperatures_kelvin=optional("temperatures_kelvin"),
            scf_iteration_limit_reached=_decode_scf(
                arrays["scf_iteration_limit_reached"]
            ),
        )


def load_frame_data_cache_records(
    source_catalog: Any,
    records: Any,
    directory: str | Path,
    *,
    verify_hashes: bool = True,
) -> dict[str, FrameData]:
    """Load normalized frame arrays from an exact, caller-supplied record set.

    This is the authoritative entry point for a prepared campaign generation:
    it binds the exact immutable members that generation published instead of
    whatever the mutable discovery alias happens to name now.
    """

    root = Path(directory)
    source_by_run = {source.run_id: source for source in source_catalog.sources}
    by_run = {str(record["run_id"]): record for record in records}
    if set(by_run) != set(source_by_run):
        raise TrainingDataSerializationError(
            "Normalized frame cache does not cover the DATA2 runs exactly."
        )

    output: dict[str, FrameData] = {}
    root_resolved = root.resolve()
    for run_id in sorted(source_by_run):
        source = source_by_run[run_id]
        record = by_run[run_id]
        if (
            record.get("source_identity_signature")
            != source.source_identity_signature
        ):
            raise TrainingDataInputError(
                f"Cached source identity changed for {run_id!r}."
            )
        if (
            record.get("source_control_bundle_signature")
            != source.source_control_bundle_signature
        ):
            raise TrainingDataInputError(
                f"Cached source controls changed for {run_id!r}."
            )
        path = (root / str(record["relative_path"])).resolve()
        try:
            path.relative_to(root_resolved)
        except ValueError as exc:
            raise TrainingDataSerializationError(
                f"Invalid frame-cache path for {run_id!r}."
            ) from exc
        if not path.is_file():
            raise TrainingDataSerializationError(
                f"Invalid frame-cache path for {run_id!r}."
            )
        if verify_hashes and _sha256_file(path) != record.get("sha256"):
            raise TrainingDataSerializationError(
                f"Frame-cache hash mismatch for {run_id!r}."
            )
        if record.get("storage_kind") == "npy_directory":
            data = _load_v2_entry(path, record, verify_hashes=verify_hashes)
        else:
            data = _load_v1_entry(path)
        if (
            data.n_frames != source.frame_count
            or data.n_atoms != source.composition.atom_count
        ):
            raise TrainingDataSerializationError(
                f"Frame-cache dimensions disagree for {run_id!r}."
            )
        output[run_id] = data
    return output


def read_frame_data_cache_manifest(directory: str | Path) -> dict[str, Any]:
    """Read the non-authoritative discovery alias for a cache directory."""

    manifest_path = Path(directory) / "frame-cache.json"
    if not manifest_path.is_file():
        raise TrainingDataInputError(
            "Normalized frame cache is absent; rebuild the prepare catalog."
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TrainingDataSerializationError(
            "Normalized frame-cache manifest is invalid."
        ) from exc
    if manifest.get("schema") not in {FRAME_CACHE_SCHEMA, FRAME_CACHE_LEGACY_SCHEMA}:
        raise TrainingDataSerializationError(
            "Unsupported normalized frame-cache schema."
        )
    return manifest


def load_frame_data_cache(
    source_catalog: Any,
    directory: str | Path,
    *,
    verify_hashes: bool = True,
) -> dict[str, FrameData]:
    """Load normalized frame arrays bound to ``source_catalog``."""

    manifest = read_frame_data_cache_manifest(directory)
    if manifest.get("source_catalog_digest") != source_catalog.content_digest:
        raise TrainingDataInputError(
            "Normalized frame cache belongs to another DATA2 catalog."
        )
    return load_frame_data_cache_records(
        source_catalog,
        manifest.get("records", ()),
        directory,
        verify_hashes=verify_hashes,
    )


__all__ = [
    "FRAME_CACHE_SCHEMA",
    "FRAME_CACHE_LEGACY_SCHEMA",
    "FRAME_CACHE_ENTRY_SCHEMA",
    "FRAME_CACHE_ENTRY_DIRECTORY",
    "authenticate_frame_data_cache_entry",
    "finalize_frame_data_cache",
    "frame_cache_entry_relative_path",
    "load_frame_data_cache",
    "load_frame_data_cache_records",
    "read_frame_data_cache_manifest",
    "write_frame_data_cache",
    "write_frame_data_cache_entry",
]
