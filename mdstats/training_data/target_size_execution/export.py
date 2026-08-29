"""P3-B current-generation exact export for target-size artifacts.

Target-training and harness-validation ExtXYZ/sidecar artifacts are bound to
the current P1 ``CanonicalFrameAuthority`` and the common preparation.  The
low-level exporter mechanics (high-precision ExtXYZ writer, streaming hash,
atomic publication, ASE round-trip validation) are the shared proven seam
from ``mace_export``; only the scientific parentage is current-generation.

Legacy ``frame_catalog_digest``/``data7_bundle_digest`` are not scientific
parents of these artifacts.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .._frame_access import ase_atoms_for_frame, build_frame_array_index
from ..mace_export import (
    MaceExtxyzPolicy,
    _HashingTextWriter,
    _atomic_text_bytes,
    _to_voigt6,
    _write_extxyz_high_precision,
)

TARGET_SIZE_EXTXYZ_ARTIFACT_SCHEMA = "mdstats.target-size.extxyz-artifact.v1"
TARGET_SIZE_EXTXYZ_SIDECAR_SCHEMA = "mdstats.target-size.extxyz-sidecar.v1"


@dataclass(frozen=True, slots=True)
class TargetSizeExtxyzArtifact:
    """Version-agnostic exported artifact record with canonical parentage."""

    role: str
    relative_path: str
    sha256: str
    configuration_count: int
    frame_uids: tuple[str, ...]
    atomic_numbers: tuple[int, ...]
    extxyz_policy_digest: str
    canonical_frame_authority_digest: str
    membership_digest: str
    common_preparation_digest: str | None
    sidecar_relative_path: str
    sidecar_sha256: str
    sidecar_digest: str
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "sha256",
            "extxyz_policy_digest",
            "canonical_frame_authority_digest",
            "membership_digest",
            "sidecar_sha256",
            "sidecar_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.common_preparation_digest is not None:
            object.__setattr__(
                self,
                "common_preparation_digest",
                validate_digest(
                    self.common_preparation_digest,
                    name="common_preparation_digest",
                ),
            )
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if (
            self.configuration_count != len(frames)
            or len(set(frames)) != len(frames)
            or not frames
        ):
            raise TrainingDataInputError(
                "Target-size extxyz frame count is inconsistent."
            )
        numbers = tuple(sorted(set(int(v) for v in self.atomic_numbers)))
        if any(v <= 0 for v in numbers) or not numbers:
            raise TrainingDataInputError(
                "Target-size extxyz atomic numbers are invalid."
            )
        object.__setattr__(self, "frame_uids", frames)
        object.__setattr__(self, "atomic_numbers", numbers)
        if not str(self.role).strip():
            raise TrainingDataInputError("Target-size artifact role is required.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_EXTXYZ_ARTIFACT_SCHEMA,
            "role": self.role,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "configuration_count": self.configuration_count,
            "frame_uids": list(self.frame_uids),
            "atomic_numbers": list(self.atomic_numbers),
            "extxyz_policy_digest": self.extxyz_policy_digest,
            "canonical_frame_authority_digest": self.canonical_frame_authority_digest,
            "membership_digest": self.membership_digest,
            "common_preparation_digest": self.common_preparation_digest,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeExtxyzArtifact:
        if payload.get("schema") != TARGET_SIZE_EXTXYZ_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size extxyz artifact schema."
            )
        result = cls(
            role=str(payload["role"]),
            relative_path=str(payload["relative_path"]),
            sha256=str(payload["sha256"]),
            configuration_count=int(payload["configuration_count"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            atomic_numbers=tuple(int(v) for v in payload["atomic_numbers"]),
            extxyz_policy_digest=str(payload["extxyz_policy_digest"]),
            canonical_frame_authority_digest=str(
                payload["canonical_frame_authority_digest"]
            ),
            membership_digest=str(payload["membership_digest"]),
            common_preparation_digest=(
                None
                if payload.get("common_preparation_digest") is None
                else str(payload["common_preparation_digest"])
            ),
            sidecar_relative_path=str(payload["sidecar_relative_path"]),
            sidecar_sha256=str(payload["sidecar_sha256"]),
            sidecar_digest=str(payload["sidecar_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size extxyz artifact digest mismatch."
            )
        return result


def _sha256_file(path: Path) -> str:
    import hashlib

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_target_size_extxyz_artifact(
    output_directory: str | Path,
    *,
    dataset_id: str,
    role: str,
    filename: str,
    frame_uids: Sequence[str],
    canonical_frame_authority: Any,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    membership_digest: str,
    common_preparation_digest: str | None = None,
    training_weights: Any | None = None,
    configuration_weight_scale: float = 1.0,
    policy: MaceExtxyzPolicy | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
) -> TargetSizeExtxyzArtifact:
    """Write one exact-membership ExtXYZ artifact with canonical parentage.

    Every exported geometry and canonical energy/force/stress payload is
    verified against the bound P1 ``CanonicalFrameAuthority`` and the ASE
    round trip before the artifact is published atomically.
    """

    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for extxyz export.") from exc
    active = MaceExtxyzPolicy() if policy is None else policy
    weight_scale = float(configuration_weight_scale)
    if not np.isfinite(weight_scale) or weight_scale <= 0.0:
        raise TrainingDataInputError(
            "Configuration-weight scale must be finite and positive."
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
        raise TrainingDataInputError(
            "Target-size artifact requires unique non-empty frames."
        )
    # Bind every frame to the P1 canonical authority before export.
    canonical_records: dict[str, Any] = {}
    for uid in frames:
        try:
            canonical_records[uid] = canonical_frame_authority.frame(uid)
        except KeyError:
            raise TrainingDataInputError(
                "Target-size export requires frames inside the canonical authority."
            ) from None
    sidecar_records: list[tuple[str, tuple[tuple[str, Any], ...]]] = []
    validation_metadata: list[tuple[str, tuple[float, float, float, float]]] = []
    all_numbers: set[int] = set()

    def prepare_atoms(uid: str) -> tuple[Any, tuple[tuple[str, Any], ...]]:
        record, frame_data, local_index = index[uid]
        canonical = canonical_records[uid]
        # Raw frame arrays may be reused only after exported geometry and
        # canonical payloads are verified against the bound P1 authority.
        if record.geometry_fingerprint != canonical.geometry_fingerprint:
            raise TrainingDataInputError(
                f"Frame {uid} raw-array geometry does not match the canonical authority."
            )
        if canonical.canonical_label_payload_digest is None:
            raise TrainingDataInputError(
                f"Frame {uid} carries no authoritative canonical label."
            )
        atoms = ase_atoms_for_frame(record, frame_data, local_index)
        energy = (
            None
            if frame_data.energies_ev is None
            else float(frame_data.energies_ev[local_index])
        )
        forces = (
            None
            if frame_data.forces_ev_per_angstrom is None
            else np.asarray(
                frame_data.forces_ev_per_angstrom[local_index], dtype=np.float64
            )
        )
        stress = (
            None
            if frame_data.stresses_ev_per_angstrom3 is None
            else np.asarray(
                frame_data.stresses_ev_per_angstrom3[local_index], dtype=np.float64
            )
        )
        if canonical.energy_present and energy is None:
            raise TrainingDataInputError(
                f"Frame {uid} declares energy but arrays are missing."
            )
        if canonical.forces_present and forces is None:
            raise TrainingDataInputError(
                f"Frame {uid} declares forces but arrays are missing."
            )
        if canonical.stress_present and stress is None:
            raise TrainingDataInputError(
                f"Frame {uid} declares stress but arrays are missing."
            )
        if energy is not None and not np.isfinite(energy):
            raise TrainingDataInputError(f"Frame {uid} has a non-finite energy.")
        if forces is not None and (
            forces.shape != (len(atoms), 3) or not np.all(np.isfinite(forces))
        ):
            raise TrainingDataInputError(f"Frame {uid} has invalid forces.")
        if stress is not None and (
            stress.size not in {6, 9} or not np.all(np.isfinite(stress))
        ):
            raise TrainingDataInputError(f"Frame {uid} has invalid stress.")
        if not np.all(
            np.isfinite(np.asarray(atoms.positions, dtype=np.float64))
        ):
            raise TrainingDataInputError(
                f"Frame {uid} has non-finite positions."
            )
        cell = np.asarray(atoms.cell.array, dtype=np.float64)
        if (
            cell.shape != (3, 3)
            or not np.all(np.isfinite(cell))
            or abs(float(np.linalg.det(cell))) <= 1.0e-14
        ):
            raise TrainingDataInputError(f"Frame {uid} has an invalid cell.")
        if energy is not None:
            atoms.info[active.energy_key] = energy
        if forces is not None:
            atoms.arrays[active.forces_key] = np.array(forces, copy=True)
        if stress is not None:
            atoms.info[active.stress_key] = _to_voigt6(stress)
        atoms.info["config_type"] = f"{active.config_type_prefix}_{role}"
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
        atoms.info["frame_uid"] = uid
        sidecar_record = tuple(
            sorted(
                {
                    "run_id": record.run_id,
                    "source_frame_index": int(record.source_frame_index),
                    "geometry_fingerprint": canonical.geometry_fingerprint,
                    "canonical_label_payload_digest": (
                        canonical.canonical_label_payload_digest
                    ),
                    "labeled_configuration_fingerprint": (
                        canonical.labeled_configuration_fingerprint
                    ),
                    "selected_energy_channel": canonical.selected_energy_channel,
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

    temporary_target = target.with_suffix(target.suffix + ".tmp")
    with temporary_target.open("w", encoding="utf-8", newline="") as raw_handle:
        hashing_handle = _HashingTextWriter(raw_handle)
        _write_extxyz_high_precision(hashing_handle, atoms_stream())
        hashing_handle.flush()
        os.fsync(raw_handle.fileno())
        target_sha256 = hashing_handle.hexdigest()
    os.replace(temporary_target, target)
    normalized_records = tuple(
        sorted(
            (validate_digest(uid, name="frame_uid"), tuple(sorted(values)))
            for uid, values in sidecar_records
        )
    )
    sidecar_payload_record = {
        "schema": TARGET_SIZE_EXTXYZ_SIDECAR_SCHEMA,
        "dataset_id": dataset_id,
        "role": role,
        "canonical_frame_authority_digest": (
            canonical_frame_authority.content_digest
        ),
        "membership_digest": membership_digest,
        "common_preparation_digest": common_preparation_digest,
        "extxyz_policy_digest": active.policy_digest,
        "records": {uid: dict(values) for uid, values in normalized_records},
    }
    sidecar_sha256 = _atomic_text_bytes(
        sidecar_path,
        (json.dumps(sidecar_payload_record, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    sidecar_digest = digest(sidecar_payload_record)

    # Round-trip validation through ASE and the exact MACE keys.
    observed_stream = iread(target, index=":", format="extxyz")
    observed_count = 0
    for expected_uid, metadata, observed in zip(
        frames, validation_metadata, observed_stream, strict=True
    ):
        expected_config_type, expected_weights = metadata
        record, frame_data, local_index = index[expected_uid]
        expected_numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
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
            raise TrainingDataInputError(
                "Target-size extxyz round trip changed frame identity."
            )
        if observed.info.get("config_type") != expected_config_type:
            raise TrainingDataInputError(
                "Target-size extxyz round trip changed config_type."
            )
        if not np.array_equal(np.asarray(observed.numbers), expected_numbers):
            raise TrainingDataInputError(
                "Target-size extxyz round trip changed atom identities or ordering."
            )
        if not np.allclose(
            np.asarray(observed.cell.array), expected_cell, rtol=0.0, atol=1e-10
        ):
            raise TrainingDataInputError(
                "Target-size extxyz round trip changed the cell."
            )
        observed_positions = np.asarray(observed.positions, dtype=np.float64)
        if not np.allclose(
            observed_positions, expected_positions, rtol=0.0, atol=1e-10
        ):
            raise TrainingDataInputError(
                "Target-size extxyz round trip changed positions."
            )
        if expected_energy is not None:
            if active.energy_key not in observed.info:
                raise TrainingDataInputError(
                    "Target-size extxyz round trip lost energy."
                )
            if not np.isclose(
                float(observed.info[active.energy_key]),
                expected_energy,
                rtol=0.0,
                atol=1e-12,
            ):
                raise TrainingDataInputError(
                    "Target-size extxyz round trip changed energy."
                )
        if expected_forces is not None:
            if active.forces_key not in observed.arrays:
                raise TrainingDataInputError(
                    "Target-size extxyz round trip lost forces."
                )
            if not np.allclose(
                np.asarray(observed.arrays[active.forces_key]),
                expected_forces,
                rtol=0.0,
                atol=1e-12,
            ):
                raise TrainingDataInputError(
                    "Target-size extxyz round trip changed forces."
                )
        if expected_stress is not None:
            if active.stress_key not in observed.info:
                raise TrainingDataInputError(
                    "Target-size extxyz round trip lost stress."
                )
            if not np.allclose(
                np.asarray(observed.info[active.stress_key]),
                expected_stress,
                rtol=0.0,
                atol=1e-12,
            ):
                raise TrainingDataInputError(
                    "Target-size extxyz round trip changed stress."
                )
        for weight_key, expected_weight in zip(
            ("config_weight", "config_energy_weight", "config_forces_weight", "config_stress_weight"),
            expected_weights,
            strict=True,
        ):
            if not np.isclose(
                float(observed.info[weight_key]), expected_weight, rtol=0.0, atol=1e-12
            ):
                raise TrainingDataInputError(
                    "Target-size extxyz round trip changed training weights."
                )
    if observed_count != len(frames):
        raise TrainingDataInputError(
            "Target-size extxyz round trip changed the frame count."
        )
    return TargetSizeExtxyzArtifact(
        role=role,
        relative_path=filename,
        sha256=target_sha256,
        configuration_count=len(frames),
        frame_uids=frames,
        atomic_numbers=tuple(sorted(all_numbers)),
        extxyz_policy_digest=active.policy_digest,
        canonical_frame_authority_digest=canonical_frame_authority.content_digest,
        membership_digest=membership_digest,
        common_preparation_digest=common_preparation_digest,
        sidecar_relative_path=sidecar_path.name,
        sidecar_sha256=sidecar_sha256,
        sidecar_digest=sidecar_digest,
    )


def validate_target_size_extxyz_artifact(
    artifact: TargetSizeExtxyzArtifact,
    *,
    root_directory: str | Path,
    canonical_frame_authority: Any,
) -> None:
    """Authenticate a durable artifact record against its files and the P1
    authority (restart path)."""

    root = Path(root_directory)
    target = root / artifact.relative_path
    sidecar = root / artifact.sidecar_relative_path
    if not target.is_file() or not sidecar.is_file():
        raise TrainingDataInputError(
            "Target-size extxyz artifact files are missing."
        )
    if _sha256_file(target) != artifact.sha256:
        raise TrainingDataInputError(
            "Target-size extxyz artifact bytes changed."
        )
    if _sha256_file(sidecar) != artifact.sidecar_sha256:
        raise TrainingDataInputError(
            "Target-size extxyz sidecar bytes changed."
        )
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    if payload.get("schema") != TARGET_SIZE_EXTXYZ_SIDECAR_SCHEMA:
        raise TrainingDataSerializationError(
            "Unsupported target-size extxyz sidecar schema."
        )
    if (
        payload.get("canonical_frame_authority_digest")
        != canonical_frame_authority.content_digest
    ):
        raise TrainingDataInputError(
            "Target-size extxyz sidecar binds a different canonical authority."
        )
    if digest(payload) != artifact.sidecar_digest:
        raise TrainingDataInputError(
            "Target-size extxyz sidecar content changed."
        )
    if list(payload.get("records", {})) != sorted(artifact.frame_uids):
        raise TrainingDataInputError(
            "Target-size extxyz sidecar membership changed."
        )


__all__ = [
    "TARGET_SIZE_EXTXYZ_ARTIFACT_SCHEMA",
    "TARGET_SIZE_EXTXYZ_SIDECAR_SCHEMA",
    "TargetSizeExtxyzArtifact",
    "validate_target_size_extxyz_artifact",
    "write_target_size_extxyz_artifact",
]
