"""MACE-readable extended-XYZ and sidecar export contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import os
import re

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest, sha256_file_cached
from ._frame_access import build_frame_array_index, ase_atoms_for_frame

MACE_EXTXYZ_POLICY_SCHEMA = "mdstats.mace-extxyz-policy.v1"
MACE_EXTXYZ_ARTIFACT_SCHEMA = "mdstats.mace-extxyz-artifact.v1"
MACE_SIDECAR_MANIFEST_SCHEMA = "mdstats.mace-sidecar-manifest.v1"
MACE_EXTXYZ_POLICY_VERSION = "mdstats.mlff-data8.extxyz.2026-07.v1"


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


class _HashingTextWriter:
    """Sequential UTF-8 writer that records the exact extxyz byte digest."""

    def __init__(self, handle: Any):
        self._handle = handle
        self._digest = hashlib.sha256()

    def write(self, value: str) -> int:
        text = str(value)
        self._digest.update(text.encode("utf-8"))
        return self._handle.write(text)

    def flush(self) -> None:
        self._handle.flush()

    def hexdigest(self) -> str:
        return self._digest.hexdigest()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._handle, name)


def _atomic_text_bytes(path: Path, payload: bytes) -> str:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return hashlib.sha256(payload).hexdigest()


def _write_extxyz_high_precision(fileobj: Any, images: Any) -> None:
    """Write ASE-compatible extxyz without the default eight-decimal loss.

    ASE 3.29 formats every floating per-atom column with ``%16.8f``.  That
    rounds positions and forces by as much as roughly 5e-9 in their native
    units, which is larger than mdstats' lossless DATA8 round-trip contract.
    The comment-line encoding (cell, scalar labels, stress, weights, and PBC)
    is already round-trip safe, so reuse ASE's canonical column/schema builder
    and replace only the floating column format with 17 significant digits.
    Seventeen significant decimal digits are sufficient to round-trip any
    finite IEEE-754 binary64 value.
    """

    try:
        from ase.io.extxyz import output_column_format
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
        raise TrainingDataInputError(
            "ASE is required for MACE extxyz export."
        ) from exc

    if hasattr(images, "get_positions"):
        images = (images,)

    excluded_arrays = {
        "symbols",
        "positions",
        "numbers",
        "species",
        "pos",
    }
    for atoms in images:
        natoms = len(atoms)
        columns = ["symbols", "positions"]
        columns.extend(
            key for key in atoms.arrays if key not in excluded_arrays
        )
        arrays: dict[str, np.ndarray] = {
            "symbols": np.asarray(atoms.get_chemical_symbols()),
            "positions": np.asarray(atoms.positions),
        }
        for key in columns[2:]:
            arrays[key] = np.asarray(atoms.arrays[key])

        comment, ncols, dtype, fmt = output_column_format(
            atoms, columns, arrays, write_info=True
        )
        # ASE 3.29 maps both float32 and float64 columns to ``%16.8f``.
        # Replace any ASE floating conversion generically so the exporter also
        # remains safe if a later supported ASE release changes field width or
        # conversion letter. Keep property ordering and non-floating formats.
        precise_fmt = re.sub(r"%[-+0-9.]*[eEfFgG]", "%24.17g", fmt)
        if precise_fmt == fmt and any(
            np.asarray(arrays[column]).dtype.kind in {"d", "f"}
            for column in columns
        ):
            raise TrainingDataSerializationError(
                "Unsupported ASE extxyz floating-column format; refusing a "
                "potentially lossy DATA8 export."
            )

        data = np.zeros(natoms, dtype=dtype)
        for column, ncol in zip(columns, ncols, strict=True):
            value = arrays[column]
            if ncol == 1:
                data[column] = np.squeeze(value)
            else:
                for component in range(ncol):
                    data[f"{column}{component}"] = value[:, component]

        fileobj.write(f"{natoms}\n")
        fileobj.write(f"{comment}\n")
        for atom_index in range(natoms):
            fileobj.write(precise_fmt % tuple(data[atom_index]))


@dataclass(frozen=True, slots=True)
class MaceExtxyzPolicy:
    energy_key: str = "REF_energy"
    forces_key: str = "REF_forces"
    stress_key: str = "REF_stress"
    stress_units: str = "eV/Angstrom^3"
    stress_representation: str = "ase_voigt_6_xx_yy_zz_yz_xz_xy"
    stress_sign: str = "ase_tensile_positive"
    config_type_prefix: str = "mdstats"
    policy_version: str = MACE_EXTXYZ_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in (
            "energy_key",
            "forces_key",
            "stress_key",
            "stress_units",
            "stress_representation",
            "stress_sign",
            "config_type_prefix",
            "policy_version",
        ):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} must be non-empty.")
        if self.stress_representation != "ase_voigt_6_xx_yy_zz_yz_xz_xy":
            raise TrainingDataInputError("DATA8 supports only ASE six-component stress export.")
        if self.stress_sign != "ase_tensile_positive":
            raise TrainingDataInputError("DATA8 supports only the ASE stress sign convention.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_EXTXYZ_POLICY_SCHEMA,
            "energy_key": self.energy_key,
            "forces_key": self.forces_key,
            "stress_key": self.stress_key,
            "stress_units": self.stress_units,
            "stress_representation": self.stress_representation,
            "stress_sign": self.stress_sign,
            "config_type_prefix": self.config_type_prefix,
            "policy_version": self.policy_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceExtxyzPolicy":
        if payload.get("schema") != MACE_EXTXYZ_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE extxyz policy schema.")
        result = cls(
            energy_key=str(payload["energy_key"]),
            forces_key=str(payload["forces_key"]),
            stress_key=str(payload["stress_key"]),
            stress_units=str(payload["stress_units"]),
            stress_representation=str(payload["stress_representation"]),
            stress_sign=str(payload["stress_sign"]),
            config_type_prefix=str(payload["config_type_prefix"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE extxyz policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceSidecarManifest:
    dataset_id: str
    role: str
    frame_catalog_digest: str
    data7_bundle_digest: str | None
    policy_digest: str
    records: tuple[tuple[str, tuple[tuple[str, Any], ...]], ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_catalog_digest", validate_digest(self.frame_catalog_digest, name="frame_catalog_digest"))
        if self.data7_bundle_digest is not None:
            object.__setattr__(self, "data7_bundle_digest", validate_digest(self.data7_bundle_digest, name="data7_bundle_digest"))
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        normalized = tuple(sorted((validate_digest(uid, name="frame_uid"), tuple(sorted((str(k), v) for k, v in values))) for uid, values in self.records))
        if len({uid for uid, _ in normalized}) != len(normalized):
            raise TrainingDataInputError("Sidecar contains duplicate frame UIDs.")
        object.__setattr__(self, "records", normalized)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_SIDECAR_MANIFEST_SCHEMA,
            "dataset_id": self.dataset_id,
            "role": self.role,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data7_bundle_digest": self.data7_bundle_digest,
            "policy_digest": self.policy_digest,
            "records": {uid: dict(values) for uid, values in self.records},
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceSidecarManifest":
        if payload.get("schema") != MACE_SIDECAR_MANIFEST_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE sidecar schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            role=str(payload["role"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data7_bundle_digest=None if payload.get("data7_bundle_digest") is None else str(payload["data7_bundle_digest"]),
            policy_digest=str(payload["policy_digest"]),
            records=tuple((str(uid), tuple((str(k), v) for k, v in values.items())) for uid, values in payload["records"].items()),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE sidecar digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceExtxyzArtifact:
    role: str
    relative_path: str
    sha256: str
    configuration_count: int
    frame_uids: tuple[str, ...]
    atomic_numbers: tuple[int, ...]
    policy_digest: str
    sidecar_relative_path: str
    sidecar_sha256: str
    sidecar_digest: str
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("sha256", "policy_digest", "sidecar_sha256", "sidecar_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if self.configuration_count != len(frames) or len(set(frames)) != len(frames):
            raise TrainingDataInputError("MACE extxyz frame count is inconsistent.")
        numbers = tuple(sorted(set(int(v) for v in self.atomic_numbers)))
        if any(v <= 0 for v in numbers):
            raise TrainingDataInputError("MACE extxyz atomic numbers are invalid.")
        object.__setattr__(self, "frame_uids", frames)
        object.__setattr__(self, "atomic_numbers", numbers)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_EXTXYZ_ARTIFACT_SCHEMA,
            "role": self.role,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "configuration_count": self.configuration_count,
            "frame_uids": list(self.frame_uids),
            "atomic_numbers": list(self.atomic_numbers),
            "policy_digest": self.policy_digest,
            "sidecar_relative_path": self.sidecar_relative_path,
            "sidecar_sha256": self.sidecar_sha256,
            "sidecar_digest": self.sidecar_digest,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceExtxyzArtifact":
        if payload.get("schema") != MACE_EXTXYZ_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE extxyz artifact schema.")
        result = cls(
            role=str(payload["role"]),
            relative_path=str(payload["relative_path"]),
            sha256=str(payload["sha256"]),
            configuration_count=int(payload["configuration_count"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            atomic_numbers=tuple(int(v) for v in payload["atomic_numbers"]),
            policy_digest=str(payload["policy_digest"]),
            sidecar_relative_path=str(payload["sidecar_relative_path"]),
            sidecar_sha256=str(payload["sidecar_sha256"]),
            sidecar_digest=str(payload["sidecar_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE extxyz artifact digest mismatch.")
        return result


def _to_voigt6(stress: np.ndarray) -> np.ndarray:
    try:
        from ase.stress import full_3x3_to_voigt_6_stress
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for stress export.") from exc
    return np.asarray(full_3x3_to_voigt_6_stress(stress), dtype=np.float64)


def write_mace_extxyz_artifact(
    output_directory: str | Path,
    *,
    dataset_id: str,
    role: str,
    filename: str,
    frame_uids: Sequence[str],
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data7_bundle: Any | None = None,
    policy: MaceExtxyzPolicy | None = None,
    training_weights: Any | None = None,
    configuration_weight_scale: float = 1.0,
    config_type_by_frame: Mapping[str, str] | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
) -> MaceExtxyzArtifact:
    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for MACE extxyz export.") from exc
    active = MaceExtxyzPolicy() if policy is None else policy
    weight_scale = float(configuration_weight_scale)
    if not np.isfinite(weight_scale) or weight_scale <= 0.0:
        raise TrainingDataInputError(
            "MACE configuration-weight scale must be finite and positive."
        )
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    target = root / filename
    sidecar_path = target.with_suffix(target.suffix + ".manifest.json")
    index = (
        build_frame_array_index(frame_catalog, frame_data_by_run)
        if frame_array_index is None
        else frame_array_index
    )
    frames = tuple(str(v) for v in frame_uids)
    if not frames or len(set(frames)) != len(frames):
        raise TrainingDataInputError("MACE artifact requires unique non-empty frames.")
    sidecar_records: list[tuple[str, tuple[tuple[str, Any], ...]]] = []
    validation_metadata: list[tuple[str, tuple[float, float, float, float]]] = []
    all_numbers: set[int] = set()

    def prepare_atoms(uid: str) -> tuple[Any, tuple[tuple[str, Any], ...]]:
        try:
            record, frame_data, local_index = index[uid]
        except KeyError as exc:
            raise TrainingDataInputError(f"Unknown frame UID {uid}.") from exc
        atoms = ase_atoms_for_frame(record, frame_data, local_index)
        energy = None if frame_data.energies_ev is None else float(frame_data.energies_ev[local_index])
        forces = None if frame_data.forces_ev_per_angstrom is None else np.asarray(frame_data.forces_ev_per_angstrom[local_index], dtype=np.float64)
        stress = None if frame_data.stresses_ev_per_angstrom3 is None else np.asarray(frame_data.stresses_ev_per_angstrom3[local_index], dtype=np.float64)
        if record.energy_present and energy is None:
            raise TrainingDataInputError(f"Frame {uid} declares energy but arrays are missing.")
        if record.forces_present and forces is None:
            raise TrainingDataInputError(f"Frame {uid} declares forces but arrays are missing.")
        if record.stress_present and stress is None:
            raise TrainingDataInputError(f"Frame {uid} declares stress but arrays are missing.")
        if energy is not None and not np.isfinite(energy):
            raise TrainingDataInputError(f"Frame {uid} has a non-finite energy.")
        if forces is not None and (forces.shape != (len(atoms), 3) or not np.all(np.isfinite(forces))):
            raise TrainingDataInputError(f"Frame {uid} has invalid forces.")
        if stress is not None and (stress.size not in {6, 9} or not np.all(np.isfinite(stress))):
            raise TrainingDataInputError(f"Frame {uid} has invalid stress.")
        if not np.all(np.isfinite(np.asarray(atoms.positions, dtype=np.float64))):
            raise TrainingDataInputError(f"Frame {uid} has non-finite positions.")
        cell = np.asarray(atoms.cell.array, dtype=np.float64)
        if cell.shape != (3, 3) or not np.all(np.isfinite(cell)) or abs(float(np.linalg.det(cell))) <= 1.0e-14:
            raise TrainingDataInputError(f"Frame {uid} has an invalid cell.")
        if energy is not None:
            atoms.info[active.energy_key] = energy
        if forces is not None:
            atoms.arrays[active.forces_key] = np.array(forces, copy=True)
        if stress is not None:
            atoms.info[active.stress_key] = _to_voigt6(stress)
        atoms.info["config_type"] = (
            config_type_by_frame.get(uid, f"{active.config_type_prefix}_{role}")
            if config_type_by_frame is not None
            else f"{active.config_type_prefix}_{role}"
        )
        weight_payload: dict[str, Any] = {}
        if training_weights is not None:
            weight = training_weights.for_frame(uid)
            base_configuration_weight = float(weight.configuration_weight)
            realized_configuration_weight = base_configuration_weight * weight_scale
            atoms.info["config_weight"] = realized_configuration_weight
            atoms.info["config_energy_weight"] = float(weight.energy_weight)
            atoms.info["config_forces_weight"] = float(weight.forces_weight)
            atoms.info["config_stress_weight"] = float(weight.stress_weight)
            weight_payload = {
                "base_configuration_weight": base_configuration_weight,
                "configuration_weight_scale": weight_scale,
                "configuration_weight": realized_configuration_weight,
                "energy_weight": float(weight.energy_weight),
                "forces_weight": float(weight.forces_weight),
                "stress_weight": float(weight.stress_weight),
                "weight_reason_codes": list(weight.reason_codes),
            }
        else:
            atoms.info["config_weight"] = weight_scale
            atoms.info["config_energy_weight"] = 1.0 if energy is not None else 0.0
            atoms.info["config_forces_weight"] = 1.0 if forces is not None else 0.0
            atoms.info["config_stress_weight"] = 1.0 if stress is not None else 0.0
            weight_payload = {
                "base_configuration_weight": 1.0,
                "configuration_weight_scale": weight_scale,
                "configuration_weight": weight_scale,
            }
        # Keep only compact stable identity in extxyz; full provenance lives in sidecar.
        atoms.info["frame_uid"] = uid
        sidecar_record = tuple(
            sorted(
                {
                    "run_id": record.run_id,
                    "source_frame_index": int(record.source_frame_index),
                    "label_domain_id": record.label_domain_id,
                    "geometry_fingerprint": record.geometry_fingerprint,
                    "labeled_configuration_fingerprint": record.labeled_configuration_fingerprint,
                    "selected_energy_channel": record.selected_energy_channel,
                    **weight_payload,
                }.items()
            )
        )
        return atoms, sidecar_record

    def atoms_stream():
        for uid in frames:
            atoms, sidecar_record = prepare_atoms(uid)
            all_numbers.update(int(v) for v in atoms.numbers)
            sidecar_records.append((uid, sidecar_record))
            validation_metadata.append(
                (
                    str(atoms.info["config_type"]),
                    (
                        float(atoms.info["config_weight"]),
                        float(atoms.info["config_energy_weight"]),
                        float(atoms.info["config_forces_weight"]),
                        float(atoms.info["config_stress_weight"]),
                    ),
                )
            )
            yield atoms

    # ``write_extxyz`` accepts an iterable.  Stream configurations instead of
    # retaining all ASE Atoms objects until the file is complete; the former
    # list plus full-file round-trip read could hold two complete copies of a
    # large training artifact and trigger swap-induced stalls.
    temporary_target = target.with_suffix(target.suffix + ".tmp")
    with temporary_target.open("w", encoding="utf-8", newline="") as raw_handle:
        hashing_handle = _HashingTextWriter(raw_handle)
        _write_extxyz_high_precision(hashing_handle, atoms_stream())
        hashing_handle.flush()
        os.fsync(raw_handle.fileno())
        target_sha256 = hashing_handle.hexdigest()
    os.replace(temporary_target, target)
    sidecar = MaceSidecarManifest(
        dataset_id=dataset_id,
        role=role,
        frame_catalog_digest=frame_catalog.content_digest,
        data7_bundle_digest=None if data7_bundle is None else data7_bundle.content_digest,
        policy_digest=active.policy_digest,
        records=tuple(sidecar_records),
    )
    sidecar_payload = (
        json.dumps(sidecar.to_dict(), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    sidecar_sha256 = _atomic_text_bytes(sidecar_path, sidecar_payload)

    # Round-trip validation through ASE and the exact MACE keys.  Stream the
    # reader and reconstruct one expected frame at a time so validation remains
    # O(1) in resident configuration count.
    observed_stream = iread(target, index=":", format="extxyz")
    observed_count = 0
    weight_keys = (
        "config_weight",
        "config_energy_weight",
        "config_forces_weight",
        "config_stress_weight",
    )
    for expected_uid, metadata, observed in zip(
        frames, validation_metadata, observed_stream, strict=True
    ):
        expected_config_type, expected_weights = metadata
        _record, frame_data, local_index = index[expected_uid]
        expected_numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
        expected_pbc = np.asarray(frame_data.pbc, dtype=np.bool_)
        expected_cell = np.asarray(
            frame_data.cells_angstrom[local_index], dtype=np.float64
        )
        expected_fractional = np.asarray(
            frame_data.fractional_positions[local_index], dtype=np.float64
        )
        expected_positions = expected_fractional @ expected_cell
        expected_energy = (
            None
            if frame_data.energies_ev is None
            else float(frame_data.energies_ev[local_index])
        )
        expected_forces = (
            None
            if frame_data.forces_ev_per_angstrom is None
            else np.asarray(
                frame_data.forces_ev_per_angstrom[local_index], dtype=np.float64
            )
        )
        expected_stress = (
            None
            if frame_data.stresses_ev_per_angstrom3 is None
            else _to_voigt6(
                np.asarray(
                    frame_data.stresses_ev_per_angstrom3[local_index],
                    dtype=np.float64,
                )
            )
        )
        observed_count += 1
        if observed.info.get("frame_uid") != expected_uid:
            raise TrainingDataInputError("MACE extxyz round trip changed frame identity.")
        if observed.info.get("config_type") != expected_config_type:
            raise TrainingDataInputError("MACE extxyz round trip changed config_type.")
        if not np.array_equal(np.asarray(observed.numbers), expected_numbers):
            raise TrainingDataInputError("MACE extxyz round trip changed atom identities or ordering.")
        if not np.array_equal(np.asarray(observed.pbc, dtype=bool), expected_pbc):
            raise TrainingDataInputError("MACE extxyz round trip changed PBC flags.")
        if not np.allclose(np.asarray(observed.cell.array), expected_cell, rtol=0.0, atol=1e-10):
            raise TrainingDataInputError("MACE extxyz round trip changed the cell.")
        observed_positions = np.asarray(observed.positions, dtype=np.float64)
        if not np.allclose(
            observed_positions, expected_positions, rtol=0.0, atol=1e-10
        ):
            maximum_error = float(
                np.max(np.abs(observed_positions - expected_positions))
            )
            raise TrainingDataInputError(
                "MACE extxyz round trip changed positions for frame "
                f"{expected_uid}; max_abs_error={maximum_error:.6e} Angstrom."
            )
        if expected_energy is not None:
            if active.energy_key not in observed.info:
                raise TrainingDataInputError("MACE extxyz round trip lost energy.")
            if not np.isclose(float(observed.info[active.energy_key]), expected_energy, rtol=0.0, atol=1e-12):
                raise TrainingDataInputError("MACE extxyz round trip changed energy.")
        if expected_forces is not None:
            if active.forces_key not in observed.arrays:
                raise TrainingDataInputError("MACE extxyz round trip lost forces.")
            if not np.allclose(np.asarray(observed.arrays[active.forces_key]), expected_forces, rtol=0.0, atol=1e-12):
                raise TrainingDataInputError("MACE extxyz round trip changed forces.")
        if expected_stress is not None:
            if active.stress_key not in observed.info:
                raise TrainingDataInputError("MACE extxyz round trip lost stress.")
            if not np.allclose(np.asarray(observed.info[active.stress_key]), expected_stress, rtol=0.0, atol=1e-12):
                raise TrainingDataInputError("MACE extxyz stress round trip changed values.")
        for weight_key, expected_weight in zip(
            weight_keys, expected_weights, strict=True
        ):
            if weight_key not in observed.info:
                raise TrainingDataInputError(
                    f"MACE extxyz round trip lost {weight_key}."
                )
            if not np.isclose(
                float(observed.info[weight_key]),
                expected_weight,
                rtol=0.0,
                atol=1e-12,
            ):
                raise TrainingDataInputError(
                    f"MACE extxyz round trip changed {weight_key}."
                )
    if observed_count != len(frames):
        raise TrainingDataInputError("MACE extxyz round trip changed configuration count.")
    return MaceExtxyzArtifact(
        role=role,
        relative_path=str(target.relative_to(root)),
        sha256=target_sha256,
        configuration_count=len(frames),
        frame_uids=frames,
        atomic_numbers=tuple(all_numbers),
        policy_digest=active.policy_digest,
        sidecar_relative_path=str(sidecar_path.relative_to(root)),
        sidecar_sha256=sidecar_sha256,
        sidecar_digest=sidecar.content_digest,
    )
