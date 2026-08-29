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

import io
import json
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
    _to_voigt6,
    _write_extxyz_high_precision,
)
from .persistence import (
    publish_immutable_bytes_create_or_verify,
    publish_immutable_json_create_or_verify,
)

TARGET_SIZE_EXTXYZ_ARTIFACT_SCHEMA = "mdstats.target-size.extxyz-artifact.v1"
TARGET_SIZE_EXTXYZ_SIDECAR_SCHEMA = "mdstats.target-size.extxyz-sidecar.v1"
TARGET_SIZE_EVALUATION_ARTIFACT_SCHEMA = (
    "mdstats.target-size.evaluation-artifact.v1"
)
TARGET_SIZE_EVALUATION_VIEW_SCHEMA = "mdstats.target-size.evaluation-view.v1"


def _evaluation_view_content_digest(view: Any) -> str:
    """Digest all parsed view arrays used by EVAL2, not just their shape."""

    import hashlib

    hasher = hashlib.sha256()
    hasher.update(b"mdstats.target-size.authenticated-evaluation-view-content.v1\0")
    for name in (
        "configuration_count",
        "focus_atomic_numbers",
        "condition_labels",
    ):
        hasher.update(str(name).encode("utf-8"))
        hasher.update(repr(getattr(view, name)).encode("utf-8"))
        hasher.update(b"\0")
    for name in (
        "atom_counts",
        "force_offsets",
        "reference_energies",
        "reference_forces",
        "atomic_numbers",
        "condition_ids",
        "reference_stresses",
        "stress_present",
    ):
        value = np.ascontiguousarray(np.asarray(getattr(view, name)))
        hasher.update(name.encode("utf-8"))
        hasher.update(value.dtype.str.encode("ascii"))
        hasher.update(repr(tuple(int(item) for item in value.shape)).encode("ascii"))
        hasher.update(memoryview(value).cast("B"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def _evaluation_view_authentication_marker(
    *,
    artifact_content_digest: str,
    artifact_sha256: str,
    evaluation_view_digest: str,
    evaluation_size: int,
    evaluation_frame_uids: Sequence[str],
    evaluation_membership_digest: str,
    canonical_frame_authority_digest: str,
    extxyz_policy_digest: str,
    energy_key: str,
    forces_key: str,
    stress_key: str,
    view: Any,
) -> str:
    return digest(
        {
            "schema": TARGET_SIZE_AUTHENTICATED_VIEW_SCHEMA,
            "artifact_content_digest": artifact_content_digest,
            "artifact_sha256": artifact_sha256,
            "evaluation_view_digest": evaluation_view_digest,
            "evaluation_size": int(evaluation_size),
            "evaluation_frame_uids": list(evaluation_frame_uids),
            "evaluation_membership_digest": evaluation_membership_digest,
            "canonical_frame_authority_digest": canonical_frame_authority_digest,
            "extxyz_policy_digest": extxyz_policy_digest,
            "energy_key": energy_key,
            "forces_key": forces_key,
            "stress_key": stress_key,
            "view_content_digest": _evaluation_view_content_digest(view),
        }
    )


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


def _resolve_artifact_path(root_directory: str | Path, relative_path: str, *, name: str) -> Path:
    """Resolve a declared artifact locator without allowing path traversal."""

    root = Path(root_directory).resolve()
    relative = Path(str(relative_path))
    if relative.is_absolute() or ".." in relative.parts:
        raise TrainingDataInputError(f"{name} must be a relative in-root path.")
    resolved = (root / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise TrainingDataInputError(f"{name} resolves outside its declared root.")
    return resolved


def _validate_parsed_extxyz_frames(
    frames: Sequence[Any],
    *,
    artifact: TargetSizeExtxyzArtifact,
    sidecar_payload: Mapping[str, Any],
    canonical_frame_authority: Any,
    policy: MaceExtxyzPolicy | None,
    frame_catalog: Any | None,
    frame_data_by_run: Mapping[str, Any] | None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None,
) -> None:
    """Cross-check parsed bytes against P1 identity and source arrays.

    The exporter already performs this check before publication.  Restart must
    repeat it against the bytes currently on disk so a self-consistent but
    foreign ExtXYZ payload cannot be accepted by a copied sidecar.
    """

    if len(frames) != artifact.configuration_count:
        raise TrainingDataInputError("Target-size extxyz frame count mismatch.")
    observed_uids = tuple(str(frame.info.get("frame_uid", "")) for frame in frames)
    if observed_uids != artifact.frame_uids:
        raise TrainingDataInputError(
            "Target-size extxyz frame UIDs or order do not match the authenticated artifact."
        )
    observed_numbers: set[int] = set()
    source_index = None
    if frame_catalog is not None and frame_data_by_run is not None:
        source_index = (
            build_frame_array_index(frame_catalog, frame_data_by_run)
            if frame_array_index is None
            else frame_array_index
        )

    for uid, observed in zip(artifact.frame_uids, frames, strict=True):
        canonical = canonical_frame_authority.frame(uid)
        sidecar_record = sidecar_payload.get("records", {}).get(uid)
        if not isinstance(sidecar_record, Mapping):
            raise TrainingDataInputError(f"Sidecar record missing for frame {uid}.")
        sidecar_record = dict(sidecar_record)
        if sidecar_record.get("run_id") != canonical.run_id:
            raise TrainingDataInputError(f"Sidecar run identity mismatch for frame {uid}.")
        if int(sidecar_record.get("source_frame_index", -1)) != int(canonical.source_frame_index):
            raise TrainingDataInputError(f"Sidecar source-frame identity mismatch for frame {uid}.")
        for field_name in (
            "geometry_fingerprint",
            "canonical_label_payload_digest",
            "labeled_configuration_fingerprint",
        ):
            if sidecar_record.get(field_name) != getattr(canonical, field_name):
                raise TrainingDataInputError(
                    f"Sidecar {field_name} mismatch for frame {uid}."
                )
        selected_channel = getattr(canonical, "selected_energy_channel", None)
        if selected_channel is not None and sidecar_record.get("selected_energy_channel") != selected_channel:
            raise TrainingDataInputError(f"Sidecar selected energy channel mismatch for frame {uid}.")

        observed_numbers.update(int(value) for value in np.asarray(observed.numbers))
        if source_index is None:
            # The canonical sidecar and frame UID/order checks remain useful
            # when a caller only has the durable P1 identity object.  Full
            # numerical payload re-derivation is required by the assembled
            # restart authority, which supplies the source index below.
            continue

        try:
            source_record, frame_data, local_index = source_index[uid]
        except KeyError as exc:
            raise TrainingDataInputError(
                f"P1 frame-array authority is missing frame {uid}."
            ) from exc
        expected_numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
        if not np.array_equal(np.asarray(observed.numbers, dtype=np.int32), expected_numbers):
            raise TrainingDataInputError(f"ExtXYZ atom ordering differs for frame {uid}.")
        expected_cell = np.asarray(frame_data.cells_angstrom[local_index], dtype=np.float64)
        if not np.allclose(np.asarray(observed.cell.array, dtype=np.float64), expected_cell, rtol=0.0, atol=1.0e-10):
            raise TrainingDataInputError(f"ExtXYZ cell differs for frame {uid}.")
        expected_fractional = np.asarray(
            frame_data.fractional_positions[local_index], dtype=np.float64
        )
        expected_positions = expected_fractional @ expected_cell
        if not np.allclose(np.asarray(observed.positions, dtype=np.float64), expected_positions, rtol=0.0, atol=1.0e-10):
            raise TrainingDataInputError(f"ExtXYZ geometry differs for frame {uid}.")
        if tuple(bool(value) for value in observed.pbc) != tuple(bool(value) for value in frame_data.pbc):
            raise TrainingDataInputError(f"ExtXYZ periodic-boundary identity differs for frame {uid}.")
        if source_record.run_id != canonical.run_id or int(source_record.source_frame_index) != int(canonical.source_frame_index):
            raise TrainingDataInputError(f"P1 source occurrence identity differs for frame {uid}.")

        energy = None if frame_data.energies_ev is None else float(frame_data.energies_ev[local_index])
        forces = None if frame_data.forces_ev_per_angstrom is None else np.asarray(frame_data.forces_ev_per_angstrom[local_index], dtype=np.float64)
        stress = None if frame_data.stresses_ev_per_angstrom3 is None else _to_voigt6(np.asarray(frame_data.stresses_ev_per_angstrom3[local_index], dtype=np.float64))
        active = MaceExtxyzPolicy() if policy is None else policy
        if energy is not None:
            if active.energy_key not in observed.info or not np.isclose(float(observed.info[active.energy_key]), energy, rtol=0.0, atol=1.0e-12):
                raise TrainingDataInputError(f"ExtXYZ energy labels differ for frame {uid}.")
        if forces is not None:
            if active.forces_key not in observed.arrays or not np.allclose(np.asarray(observed.arrays[active.forces_key], dtype=np.float64), forces, rtol=0.0, atol=1.0e-12):
                raise TrainingDataInputError(f"ExtXYZ force labels differ for frame {uid}.")
        if stress is not None:
            if active.stress_key not in observed.info or not np.allclose(np.asarray(observed.info[active.stress_key], dtype=np.float64).reshape(-1), stress.reshape(-1), rtol=0.0, atol=1.0e-12):
                raise TrainingDataInputError(f"ExtXYZ stress labels differ for frame {uid}.")

    if tuple(sorted(observed_numbers)) != tuple(artifact.atomic_numbers):
        raise TrainingDataInputError(
            "Target-size extxyz atomic-number identity differs from the artifact."
        )


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

    string_buffer = io.StringIO()
    hashing_handle = _HashingTextWriter(string_buffer)
    _write_extxyz_high_precision(hashing_handle, atoms_stream())
    target_sha256 = hashing_handle.hexdigest()
    target_bytes = string_buffer.getvalue().encode("utf-8")
    publish_immutable_bytes_create_or_verify(
        target, target_bytes, expected_sha256=target_sha256
    )

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
        "energy_key": active.energy_key,
        "forces_key": active.forces_key,
        "stress_key": active.stress_key,
        "canonical_frame_authority_digest": (
            canonical_frame_authority.content_digest
        ),
        "membership_digest": membership_digest,
        "common_preparation_digest": common_preparation_digest,
        "extxyz_policy_digest": active.policy_digest,
        "records": {uid: dict(values) for uid, values in normalized_records},
    }
    publish_immutable_json_create_or_verify(
        sidecar_path, sidecar_payload_record
    )
    sidecar_sha256 = _sha256_file(sidecar_path)
    sidecar_digest = digest(sidecar_payload_record)

    # Round-trip validation through ASE and the exact MACE keys.
    observed_stream = iread(io.StringIO(target_bytes.decode("utf-8")), index=":", format="extxyz")
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
    policy: MaceExtxyzPolicy,
    frame_catalog: Any | None = None,
    frame_data_by_run: Mapping[str, Any] | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
) -> None:
    """Authenticate a durable artifact record against its files and the P1
    authority (restart path)."""

    import hashlib

    if not isinstance(policy, MaceExtxyzPolicy):
        raise TrainingDataInputError(
            "Target-size ExtXYZ validation requires the accepted MaceExtxyzPolicy."
        )

    target = _resolve_artifact_path(
        root_directory, artifact.relative_path, name="ExtXYZ artifact path"
    )
    sidecar = _resolve_artifact_path(
        root_directory, artifact.sidecar_relative_path, name="ExtXYZ sidecar path"
    )
    if not target.is_file() or not sidecar.is_file():
        raise TrainingDataInputError(
            "Target-size extxyz artifact files are missing."
        )
    target_bytes = target.read_bytes()
    sidecar_bytes = sidecar.read_bytes()
    if hashlib.sha256(target_bytes).hexdigest() != artifact.sha256:
        raise TrainingDataInputError(
            "Target-size extxyz artifact bytes changed."
        )
    if hashlib.sha256(sidecar_bytes).hexdigest() != artifact.sidecar_sha256:
        raise TrainingDataInputError(
            "Target-size extxyz sidecar bytes changed."
        )
    if artifact.canonical_frame_authority_digest != canonical_frame_authority.content_digest:
        raise TrainingDataInputError(
            "Target-size extxyz artifact binds a different canonical authority."
        )
    try:
        payload = json.loads(sidecar_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrainingDataSerializationError(
            "Target-size extxyz sidecar cannot be parsed."
        ) from exc
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
    if artifact.extxyz_policy_digest != policy.policy_digest:
        raise TrainingDataInputError(
            "Target-size extxyz artifact extxyz policy digest mismatch."
        )
    if payload.get("extxyz_policy_digest") != policy.policy_digest:
        raise TrainingDataInputError(
            "Target-size extxyz sidecar extxyz policy digest mismatch."
        )
    for field_name in ("energy_key", "forces_key", "stress_key"):
        if payload.get(field_name) != getattr(policy, field_name):
            raise TrainingDataInputError(
                f"Target-size extxyz sidecar {field_name} mismatch."
            )
    records = payload.get("records")
    if not isinstance(records, Mapping):
        raise TrainingDataSerializationError(
            "Target-size extxyz sidecar records must be an object."
        )
    if tuple(records) != tuple(sorted(artifact.frame_uids)):
        raise TrainingDataInputError(
            "Target-size extxyz sidecar membership changed."
        )

    if payload.get("dataset_id") != canonical_frame_authority.dataset_id:
        raise TrainingDataInputError(
            "Target-size extxyz sidecar dataset_id mismatch."
        )
    if payload.get("role") != artifact.role:
        raise TrainingDataInputError(
            "Target-size extxyz sidecar role mismatch."
        )
    if payload.get("membership_digest") != artifact.membership_digest:
        raise TrainingDataInputError(
            "Target-size extxyz sidecar membership digest mismatch."
        )
    if payload.get("common_preparation_digest") != artifact.common_preparation_digest:
        raise TrainingDataInputError(
            "Target-size extxyz sidecar common preparation digest mismatch."
        )

    try:
        import ase.io
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to validate ExtXYZ artifacts.") from exc
    try:
        frames = ase.io.read(
            io.StringIO(target_bytes.decode("utf-8")), format="extxyz", index=":"
        )
    except (UnicodeDecodeError, OSError, ValueError) as exc:
        raise TrainingDataInputError("Target-size ExtXYZ bytes cannot be parsed.") from exc
    _validate_parsed_extxyz_frames(
        frames,
        artifact=artifact,
        sidecar_payload=payload,
        canonical_frame_authority=canonical_frame_authority,
        policy=policy,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
    )


@dataclass(frozen=True, slots=True)
class TargetSizeEvaluationArtifact:
    """Exact-M evaluation data authority with canonical P1 and P2 parentage."""

    experiment_definition_digest: str
    dataset_id: str
    canonical_frame_authority_digest: str
    evaluation_size: int
    evaluation_frame_uids: tuple[str, ...]
    evaluation_membership_digest: str
    energy_key: str
    forces_key: str
    stress_key: str
    extxyz_policy_digest: str
    relative_path: str
    sha256: str
    sidecar_relative_path: str
    sidecar_sha256: str
    sidecar_digest: str
    evaluation_view_digest: str
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "canonical_frame_authority_digest",
            "evaluation_membership_digest",
            "extxyz_policy_digest",
            "sha256",
            "sidecar_sha256",
            "sidecar_digest",
            "evaluation_view_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        size = int(self.evaluation_size)
        if size <= 0:
            raise TrainingDataInputError("evaluation_size must be a positive integer.")
        object.__setattr__(self, "evaluation_size", size)
        frames = tuple(
            validate_digest(v, name="evaluation frame UID")
            for v in self.evaluation_frame_uids
        )
        if len(frames) != size or len(set(frames)) != len(frames) or not frames:
            raise TrainingDataInputError(
                "Evaluation artifact frame count is inconsistent with evaluation_size."
            )
        object.__setattr__(self, "evaluation_frame_uids", frames)
        for name in (
            "dataset_id",
            "energy_key",
            "forces_key",
            "stress_key",
            "relative_path",
            "sidecar_relative_path",
        ):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} cannot be empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_EVALUATION_ARTIFACT_SCHEMA,
            "experiment_definition_digest": self.experiment_definition_digest,
            "dataset_id": self.dataset_id,
            "canonical_frame_authority_digest": (
                self.canonical_frame_authority_digest
            ),
            "evaluation_size": self.evaluation_size,
            "evaluation_frame_uids": list(self.evaluation_frame_uids),
            "evaluation_membership_digest": self.evaluation_membership_digest,
            "energy_key": self.energy_key,
            "forces_key": self.forces_key,
            "stress_key": self.stress_key,
            "extxyz_policy_digest": self.extxyz_policy_digest,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "sidecar_relative_path": self.sidecar_relative_path,
            "sidecar_sha256": self.sidecar_sha256,
            "sidecar_digest": self.sidecar_digest,
            "evaluation_view_digest": self.evaluation_view_digest,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeEvaluationArtifact:
        if payload.get("schema") != TARGET_SIZE_EVALUATION_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size evaluation artifact schema."
            )
        result = cls(
            experiment_definition_digest=str(
                payload["experiment_definition_digest"]
            ),
            dataset_id=str(payload["dataset_id"]),
            canonical_frame_authority_digest=str(
                payload["canonical_frame_authority_digest"]
            ),
            evaluation_size=int(payload["evaluation_size"]),
            evaluation_frame_uids=tuple(
                str(v) for v in payload["evaluation_frame_uids"]
            ),
            evaluation_membership_digest=str(
                payload["evaluation_membership_digest"]
            ),
            energy_key=str(payload["energy_key"]),
            forces_key=str(payload["forces_key"]),
            stress_key=str(payload["stress_key"]),
            extxyz_policy_digest=str(payload["extxyz_policy_digest"]),
            relative_path=str(payload["relative_path"]),
            sha256=str(payload["sha256"]),
            sidecar_relative_path=str(payload["sidecar_relative_path"]),
            sidecar_sha256=str(payload["sidecar_sha256"]),
            sidecar_digest=str(payload["sidecar_digest"]),
            evaluation_view_digest=str(payload["evaluation_view_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size evaluation artifact digest mismatch."
            )
        return result

    def build_authenticated_evaluation_view(
        self,
        root_directory: str | Path,
        *,
        definition: Any | None = None,
        canonical_frame_authority: Any | None = None,
        policy: MaceExtxyzPolicy | None = None,
        frame_catalog: Any | None = None,
        frame_data_by_run: Mapping[str, Any] | None = None,
        frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    ) -> TargetSizeAuthenticatedEvaluationView:
        """Instantiate sealed, validated evaluation dataset view from exact-M bytes."""
        import hashlib
        from ..evaluation_views import build_evaluation_dataset_view

        try:
            import ase.io
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError(
                "ASE is required to build evaluation dataset view."
            ) from exc
        target = _resolve_artifact_path(
            root_directory, self.relative_path, name="Evaluation artifact path"
        )
        sidecar = _resolve_artifact_path(
            root_directory, self.sidecar_relative_path, name="Evaluation sidecar path"
        )
        if not target.is_file():
            raise TrainingDataInputError(
                f"Target-size evaluation artifact file is missing: {target}"
            )
        raw_bytes = target.read_bytes()
        computed_sha = hashlib.sha256(raw_bytes).hexdigest()
        if computed_sha != self.sha256:
            raise TrainingDataInputError(
                "Evaluation artifact file SHA-256 changed on disk."
            )
        sidecar_bytes = sidecar.read_bytes() if sidecar.is_file() else b""
        if not sidecar.is_file() or hashlib.sha256(sidecar_bytes).hexdigest() != self.sidecar_sha256:
            raise TrainingDataInputError(
                "Evaluation artifact sidecar bytes changed on disk."
            )
        try:
            sidecar_payload = json.loads(sidecar_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TrainingDataSerializationError(
                "Evaluation artifact sidecar cannot be parsed."
            ) from exc
        if (
            sidecar_payload.get("schema") != TARGET_SIZE_EXTXYZ_SIDECAR_SCHEMA
            or digest(sidecar_payload) != self.sidecar_digest
        ):
            raise TrainingDataInputError(
                "Evaluation artifact sidecar content is not authenticated."
            )
        if tuple(sidecar_payload.get("records", {})) != tuple(
            sorted(self.evaluation_frame_uids)
        ):
            raise TrainingDataInputError(
                "Evaluation artifact sidecar membership is not authenticated."
            )
        if definition is not None or canonical_frame_authority is not None:
            if definition is None or canonical_frame_authority is None:
                raise TrainingDataInputError(
                    "Authenticated evaluation view validation requires both definition and P1 authority."
                )
            validate_target_size_evaluation_artifact(
                self,
                root_directory=root_directory,
                definition=definition,
                canonical_frame_authority=canonical_frame_authority,
                policy=policy,
                frame_catalog=frame_catalog,
                frame_data_by_run=frame_data_by_run,
                frame_array_index=frame_array_index,
            )
        atoms = ase.io.read(io.StringIO(raw_bytes.decode("utf-8")), format="extxyz", index=":")
        if len(atoms) != self.evaluation_size:
            raise TrainingDataInputError(
                "Evaluation artifact frame count mismatch."
            )
        view = build_evaluation_dataset_view(
            atoms,
            energy_key=self.energy_key,
            forces_key=self.forces_key,
            stress_key=self.stress_key,
            focus_atomic_numbers=(),
            condition_keys=(),
        )
        observed_uids = tuple(str(item.info.get("frame_uid", "")) for item in atoms)
        if observed_uids != self.evaluation_frame_uids:
            raise TrainingDataInputError(
                "Authenticated evaluation view frame order differs from the artifact."
            )
        expected_view_digest = digest(
            {
                "schema": TARGET_SIZE_EVALUATION_VIEW_SCHEMA,
                "experiment_definition_digest": self.experiment_definition_digest,
                "canonical_frame_authority_digest": self.canonical_frame_authority_digest,
                "evaluation_size": self.evaluation_size,
                "evaluation_membership_digest": self.evaluation_membership_digest,
                "evaluation_frame_uids": list(self.evaluation_frame_uids),
                "artifact_sha256": self.sha256,
                "energy_key": self.energy_key,
                "forces_key": self.forces_key,
                "stress_key": self.stress_key,
                "extxyz_policy_digest": self.extxyz_policy_digest,
            }
        )
        if expected_view_digest != self.evaluation_view_digest:
            raise TrainingDataInputError(
                "Evaluation artifact view digest does not match its bound fields."
            )
        result = TargetSizeAuthenticatedEvaluationView(
            artifact_content_digest=self.content_digest,
            artifact_sha256=self.sha256,
            evaluation_view_digest=self.evaluation_view_digest,
            evaluation_size=self.evaluation_size,
            evaluation_frame_uids=self.evaluation_frame_uids,
            evaluation_membership_digest=self.evaluation_membership_digest,
            canonical_frame_authority_digest=self.canonical_frame_authority_digest,
            extxyz_policy_digest=self.extxyz_policy_digest,
            energy_key=self.energy_key,
            forces_key=self.forces_key,
            stress_key=self.stress_key,
            view=view,
        )
        object.__setattr__(
            result,
            "_authentication_marker",
            _evaluation_view_authentication_marker(
                artifact_content_digest=result.artifact_content_digest,
                artifact_sha256=result.artifact_sha256,
                evaluation_view_digest=result.evaluation_view_digest,
                evaluation_size=result.evaluation_size,
                evaluation_frame_uids=result.evaluation_frame_uids,
                evaluation_membership_digest=result.evaluation_membership_digest,
                canonical_frame_authority_digest=result.canonical_frame_authority_digest,
                extxyz_policy_digest=result.extxyz_policy_digest,
                energy_key=result.energy_key,
                forces_key=result.forces_key,
                stress_key=result.stress_key,
                view=result.view,
            ),
        )
        object.__setattr__(view, "evaluation_view_digest", self.evaluation_view_digest)
        return result

    def build_evaluation_view(self, root_directory: str | Path) -> Any:
        """Instantiate evaluation view."""
        auth_view = self.build_authenticated_evaluation_view(root_directory)
        return auth_view.view


TARGET_SIZE_AUTHENTICATED_VIEW_SCHEMA = (
    "mdstats.target-size-authenticated-view.v1"
)


@dataclass(frozen=True, slots=True)
class TargetSizeAuthenticatedEvaluationView:
    """Dedicated immutable authenticated evaluation view wrapper."""

    artifact_content_digest: str
    artifact_sha256: str
    evaluation_view_digest: str
    evaluation_size: int
    evaluation_frame_uids: tuple[str, ...]
    evaluation_membership_digest: str
    canonical_frame_authority_digest: str
    extxyz_policy_digest: str
    energy_key: str
    forces_key: str
    stress_key: str
    view: Any
    _authentication_marker: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "artifact_content_digest",
            "artifact_sha256",
            "evaluation_view_digest",
            "evaluation_membership_digest",
            "canonical_frame_authority_digest",
            "extxyz_policy_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        size = int(self.evaluation_size)
        if size <= 0:
            raise TrainingDataInputError("Evaluation size must be positive.")
        object.__setattr__(self, "evaluation_size", size)
        uids = tuple(
            validate_digest(str(v), name="authenticated evaluation frame UID")
            for v in self.evaluation_frame_uids
        )
        if len(uids) != size or len(set(uids)) != len(uids):
            raise TrainingDataInputError(
                "Authenticated view frame count mismatch."
            )
        object.__setattr__(self, "evaluation_frame_uids", uids)
        if int(getattr(self.view, "configuration_count", -1)) != size:
            raise TrainingDataInputError(
                "Authenticated view underlying configuration count mismatch."
            )
        for name in ("energy_key", "forces_key", "stress_key"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(
                    f"Authenticated view {name} must be non-empty."
                )


def write_target_size_evaluation_artifact(
    output_directory: str | Path,
    *,
    definition: Any,
    evaluation_size: int,
    canonical_frame_authority: Any,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    policy: MaceExtxyzPolicy | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    filename: str | None = None,
) -> TargetSizeEvaluationArtifact:
    """Write one exact M_i evaluation artifact and compute its view authority."""
    size = int(evaluation_size)
    if size not in definition.policy.evaluation_sizes:
        raise TrainingDataInputError(
            f"Evaluation size {size} is not among policy evaluation sizes: "
            f"{definition.policy.evaluation_sizes}"
        )
    frame_uids = definition.evaluation_membership(size)
    membership_digest = definition.evaluation_order.membership_digest(size)
    active = MaceExtxyzPolicy() if policy is None else policy
    fname = filename or f"target_size_eval_m{size}.extxyz"
    raw_artifact = write_target_size_extxyz_artifact(
        output_directory,
        dataset_id=canonical_frame_authority.dataset_id,
        role=f"eval_m{size}",
        filename=fname,
        frame_uids=frame_uids,
        canonical_frame_authority=canonical_frame_authority,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        membership_digest=membership_digest,
        common_preparation_digest=None,
        training_weights=None,
        policy=active,
        frame_array_index=frame_array_index,
    )
    view_digest = digest(
        {
            "schema": TARGET_SIZE_EVALUATION_VIEW_SCHEMA,
            "experiment_definition_digest": definition.content_digest,
            "canonical_frame_authority_digest": (
                canonical_frame_authority.content_digest
            ),
            "evaluation_size": size,
            "evaluation_membership_digest": membership_digest,
            "evaluation_frame_uids": list(frame_uids),
            "artifact_sha256": raw_artifact.sha256,
            "energy_key": active.energy_key,
            "forces_key": active.forces_key,
            "stress_key": active.stress_key,
            "extxyz_policy_digest": active.policy_digest,
        }
    )
    return TargetSizeEvaluationArtifact(
        experiment_definition_digest=definition.content_digest,
        dataset_id=canonical_frame_authority.dataset_id,
        canonical_frame_authority_digest=(
            canonical_frame_authority.content_digest
        ),
        evaluation_size=size,
        evaluation_frame_uids=frame_uids,
        evaluation_membership_digest=membership_digest,
        energy_key=active.energy_key,
        forces_key=active.forces_key,
        stress_key=active.stress_key,
        extxyz_policy_digest=active.policy_digest,
        relative_path=raw_artifact.relative_path,
        sha256=raw_artifact.sha256,
        sidecar_relative_path=raw_artifact.sidecar_relative_path,
        sidecar_sha256=raw_artifact.sidecar_sha256,
        sidecar_digest=raw_artifact.sidecar_digest,
        evaluation_view_digest=view_digest,
    )


def validate_target_size_evaluation_artifact(
    artifact: TargetSizeEvaluationArtifact,
    *,
    root_directory: str | Path,
    definition: Any,
    canonical_frame_authority: Any,
    policy: MaceExtxyzPolicy,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    frame_array_index: Mapping[str, tuple[Any, Any, int]],
) -> None:
    """Validate that durable evaluation artifact files and metadata are authentic."""

    import hashlib
    if not isinstance(policy, MaceExtxyzPolicy):
        raise TrainingDataInputError(
            "Evaluation artifact validation requires the accepted MaceExtxyzPolicy."
        )
    if frame_catalog is None or frame_data_by_run is None or frame_array_index is None:
        raise TrainingDataInputError(
            "Evaluation artifact validation requires the complete canonical P1 frame authority."
        )
    if artifact.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError(
            "Evaluation artifact binds a different experiment definition."
        )
    if artifact.evaluation_size not in definition.policy.evaluation_sizes:
        raise TrainingDataInputError(
            "Evaluation artifact size is not in policy evaluation sizes."
        )
    expected_uids = definition.evaluation_membership(artifact.evaluation_size)
    if artifact.evaluation_frame_uids != expected_uids:
        raise TrainingDataInputError(
            "Evaluation artifact frame UIDs do not match P2 evaluation membership."
        )
    expected_membership_digest = definition.evaluation_order.membership_digest(
        artifact.evaluation_size
    )
    if artifact.evaluation_membership_digest != expected_membership_digest:
        raise TrainingDataInputError(
            "Evaluation artifact membership digest does not match P2 evaluation order."
        )
    if (
        artifact.canonical_frame_authority_digest
        != canonical_frame_authority.content_digest
    ):
        raise TrainingDataInputError(
            "Evaluation artifact binds a different canonical frame authority."
        )
    target = _resolve_artifact_path(
        root_directory, artifact.relative_path, name="Evaluation artifact path"
    )
    sidecar = _resolve_artifact_path(
        root_directory, artifact.sidecar_relative_path, name="Evaluation sidecar path"
    )
    if not target.is_file() or not sidecar.is_file():
        raise TrainingDataInputError("Evaluation artifact files are missing.")
    target_bytes = target.read_bytes()
    sidecar_bytes = sidecar.read_bytes()
    if hashlib.sha256(target_bytes).hexdigest() != artifact.sha256:
        raise TrainingDataInputError("Evaluation artifact file bytes changed.")
    if hashlib.sha256(sidecar_bytes).hexdigest() != artifact.sidecar_sha256:
        raise TrainingDataInputError("Evaluation artifact sidecar bytes changed.")
    try:
        payload = json.loads(sidecar_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrainingDataSerializationError(
            "Evaluation artifact sidecar cannot be parsed."
        ) from exc
    if payload.get("schema") != TARGET_SIZE_EXTXYZ_SIDECAR_SCHEMA:
        raise TrainingDataSerializationError(
            "Unsupported evaluation sidecar schema."
        )
    if digest(payload) != artifact.sidecar_digest:
        raise TrainingDataInputError(
            "Evaluation artifact sidecar content changed."
        )
    if payload.get("dataset_id") != canonical_frame_authority.dataset_id:
        raise TrainingDataInputError(
            "Evaluation artifact sidecar dataset_id mismatch."
        )
    if (
        payload.get("canonical_frame_authority_digest")
        != canonical_frame_authority.content_digest
    ):
        raise TrainingDataInputError(
            "Evaluation artifact sidecar canonical frame authority mismatch."
        )
    if payload.get("membership_digest") != artifact.evaluation_membership_digest:
        raise TrainingDataInputError(
            "Evaluation artifact sidecar membership digest mismatch."
        )
    if payload.get("extxyz_policy_digest") != artifact.extxyz_policy_digest:
        raise TrainingDataInputError(
            "Evaluation artifact sidecar extxyz policy digest mismatch."
        )
    if payload.get("role") != f"eval_m{artifact.evaluation_size}":
        raise TrainingDataInputError("Evaluation artifact sidecar role mismatch.")
    if payload.get("common_preparation_digest") is not None:
        raise TrainingDataInputError(
            "Evaluation artifact sidecar must not bind common preparation."
        )
    if policy is not None:
        if artifact.extxyz_policy_digest != policy.policy_digest:
            raise TrainingDataInputError(
                "Evaluation artifact policy digest differs from the accepted ExtXYZ policy."
            )
        for field_name in ("energy_key", "forces_key", "stress_key"):
            if getattr(artifact, field_name) != getattr(policy, field_name):
                raise TrainingDataInputError(
                    f"Evaluation artifact {field_name} differs from the accepted ExtXYZ policy."
                )
            if payload.get(field_name) != getattr(policy, field_name):
                raise TrainingDataInputError(
                    f"Evaluation artifact sidecar {field_name} differs from the accepted ExtXYZ policy."
                )
    try:
        import ase.io
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to validate evaluation artifacts.") from exc
    try:
        frames = ase.io.read(
            io.StringIO(target_bytes.decode("utf-8")), format="extxyz", index=":"
        )
    except (UnicodeDecodeError, OSError, ValueError) as exc:
        raise TrainingDataInputError("Evaluation artifact ExtXYZ bytes cannot be parsed.") from exc
    if len(frames) != artifact.evaluation_size:
        raise TrainingDataInputError("Evaluation artifact frame count mismatch.")
    records = payload.get("records")
    if not isinstance(records, Mapping) or tuple(records) != tuple(sorted(expected_uids)):
        raise TrainingDataInputError(
            "Evaluation artifact sidecar does not contain the exact ordered membership."
        )
    extxyz_like = TargetSizeExtxyzArtifact(
        role=f"eval_m{artifact.evaluation_size}",
        relative_path=artifact.relative_path,
        sha256=artifact.sha256,
        configuration_count=artifact.evaluation_size,
        frame_uids=expected_uids,
        atomic_numbers=tuple(
            sorted({int(value) for frame in frames for value in np.asarray(frame.numbers)})
        ),
        extxyz_policy_digest=artifact.extxyz_policy_digest,
        canonical_frame_authority_digest=artifact.canonical_frame_authority_digest,
        membership_digest=artifact.evaluation_membership_digest,
        common_preparation_digest=None,
        sidecar_relative_path=artifact.sidecar_relative_path,
        sidecar_sha256=artifact.sidecar_sha256,
        sidecar_digest=artifact.sidecar_digest,
    )
    _validate_parsed_extxyz_frames(
        frames,
        artifact=extxyz_like,
        sidecar_payload=payload,
        canonical_frame_authority=canonical_frame_authority,
        policy=policy,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
    )

    recomputed_view_digest = digest(
        {
            "schema": TARGET_SIZE_EVALUATION_VIEW_SCHEMA,
            "experiment_definition_digest": definition.content_digest,
            "canonical_frame_authority_digest": (
                canonical_frame_authority.content_digest
            ),
            "evaluation_size": artifact.evaluation_size,
            "evaluation_membership_digest": artifact.evaluation_membership_digest,
            "evaluation_frame_uids": list(artifact.evaluation_frame_uids),
            "artifact_sha256": artifact.sha256,
            "energy_key": artifact.energy_key,
            "forces_key": artifact.forces_key,
            "stress_key": artifact.stress_key,
            "extxyz_policy_digest": artifact.extxyz_policy_digest,
        }
    )
    if artifact.evaluation_view_digest != recomputed_view_digest:
        raise TrainingDataInputError(
            "Evaluation artifact evaluation view digest mismatch."
        )


__all__ = [
    "TARGET_SIZE_AUTHENTICATED_VIEW_SCHEMA",
    "TARGET_SIZE_EVALUATION_ARTIFACT_SCHEMA",
    "TARGET_SIZE_EVALUATION_VIEW_SCHEMA",
    "TARGET_SIZE_EXTXYZ_ARTIFACT_SCHEMA",
    "TARGET_SIZE_EXTXYZ_SIDECAR_SCHEMA",
    "TargetSizeAuthenticatedEvaluationView",
    "TargetSizeEvaluationArtifact",
    "TargetSizeExtxyzArtifact",
    "validate_target_size_evaluation_artifact",
    "validate_target_size_extxyz_artifact",
    "write_target_size_evaluation_artifact",
    "write_target_size_extxyz_artifact",
]
