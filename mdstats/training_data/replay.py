"""Replay-source, monitor, provenance, and retention contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import math

import numpy as np

from ._common import sha256_file_cached
from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .replay_index import (
    ReplaySourceIndex,
    iter_indexed_replay_frames,
    replay_source_indices_for_identities,
)

REPLAY_FILE_ARTIFACT_SCHEMA = "mdstats.replay-file-artifact.v4"
REPLAY_FILE_ARTIFACT_V3_SCHEMA = "mdstats.replay-file-artifact.v3"
REPLAY_PREPARATION_PLAN_SCHEMA = "mdstats.replay-preparation-plan.v4"
REPLAY_PREPARATION_PLAN_V3_SCHEMA = "mdstats.replay-preparation-plan.v3"
REPLAY_RETENTION_POLICY_SCHEMA = "mdstats.replay-retention-policy.v1"


class ReplayMode(str, Enum):
    NONE = "none"
    MP_SHORTCUT = "mp_shortcut"
    EXTERNAL_TRUE_LABEL = "external_true_label"
    EXTERNAL_PSEUDOLABEL = "external_pseudolabel"
    PRESELECTED = "preselected"


class ReplayLabelMode(str, Enum):
    TRUE_DFT = "true_dft"
    FOUNDATION_PSEUDOLABEL = "foundation_pseudolabel"
    UNSPECIFIED = "unspecified"


# REPLAY-UNIFY1A single-source authority.  These schemas intentionally do not
# replace the historical ReplayFileArtifact identity above/below.  Legacy
# split replay artifacts remain digest-compatible and are migrated only by the
# later campaign-integration gate.
REPLAY_GEOMETRY_IDENTITY_SCHEMA = "mdstats.replay-geometry-identity.v1"
REPLAY_SOURCE_ARTIFACT_SCHEMA = "mdstats.replay-source-artifact.v1"
REPLAY_SPLIT_MANIFEST_SCHEMA = "mdstats.replay-split-manifest.v1"
REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA = "mdstats.replay-single-source-config.v1"
REPLAY_SPLIT_RANK_SCHEMA = "mdstats.replay-split-rank.v1"
REPLAY_TRUE_LABEL_CACHE_SCHEMA = "mdstats.replay-true-label-cache.v1"
REPLAY_TRUE_LABEL_VIEW_SCHEMA = "mdstats.replay-true-label-view.v1"
REPLAY_TRUE_LABEL_VIEW_RECEIPT_SCHEMA = "mdstats.replay-true-label-view-receipt.v1"
DEFAULT_REPLAY_SPLIT_RATIO = (5, 1)
DEFAULT_REPLAY_SPLIT_SEED = 42
REPLAY_GEOMETRY_QUANTIZATION_ANGSTROM = 1.0e-8


class ReplayLabelNamespace(str, Enum):
    """Logical replay-label namespace independent of ExtXYZ field names."""

    SOURCE_TRUE = "source_true"
    FOUNDATION_PSEUDOLABEL = "foundation_pseudolabel"


@dataclass(frozen=True, slots=True)
class ReplaySingleSourceConfig:
    """Normalized new-style campaign replay input.

    This record establishes the external interface only.  REPLAY-UNIFY1A does
    not yet route production TRAIN2/DATA8 execution through it; that switch is
    intentionally deferred to REPLAY-UNIFY1D.
    """

    replay_set_path: str
    label_mode: ReplayLabelMode
    split_ratio: tuple[int, int] = DEFAULT_REPLAY_SPLIT_RATIO
    split_seed: int = DEFAULT_REPLAY_SPLIT_SEED
    serialization_schema: str = REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "label_mode", ReplayLabelMode(self.label_mode))
        if self.label_mode not in {ReplayLabelMode.TRUE_DFT, ReplayLabelMode.FOUNDATION_PSEUDOLABEL}:
            raise TrainingDataInputError("Single-source replay requires true_dft or foundation_pseudolabel label mode.")
        ratio = normalize_replay_split_ratio(self.split_ratio)
        object.__setattr__(self, "split_ratio", ratio)
        if int(self.split_seed) < 0:
            raise TrainingDataInputError("Replay split seed must be nonnegative.")
        object.__setattr__(self, "split_seed", int(self.split_seed))
        path = str(self.replay_set_path).strip()
        if not path:
            raise TrainingDataInputError("Single-source replay path cannot be empty.")
        object.__setattr__(self, "replay_set_path", path)
        if self.serialization_schema != REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA:
            raise TrainingDataInputError("Unsupported single-source replay config schema.")

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "replay_set_path": self.replay_set_path,
                "label_mode": self.label_mode.value,
                "split_ratio": list(self.split_ratio),
                "split_seed": self.split_seed,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "replay_set_path": self.replay_set_path,
            "label_mode": self.label_mode.value,
            "split_ratio": list(self.split_ratio),
            "split_seed": self.split_seed,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplaySingleSourceConfig":
        if payload.get("schema") != REPLAY_SINGLE_SOURCE_CONFIG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported single-source replay config schema.")
        result = cls(
            replay_set_path=str(payload["replay_set_path"]),
            label_mode=ReplayLabelMode(payload["label_mode"]),
            split_ratio=tuple(int(v) for v in payload["split_ratio"]),
            split_seed=int(payload["split_seed"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Single-source replay config digest mismatch.")
        return result


def normalize_replay_split_ratio(value: Any) -> tuple[int, int]:
    """Return a positive two-component train:monitor ratio in lowest terms."""

    if isinstance(value, str):
        text = value.strip().replace("/", ":")
        parts = text.split(":")
    else:
        try:
            parts = list(value)
        except TypeError as exc:
            raise TrainingDataInputError("Replay split ratio must look like 5:1.") from exc
    if len(parts) != 2:
        raise TrainingDataInputError("Replay split ratio must have exactly train and monitor components.")
    try:
        train, monitor = (int(v) for v in parts)
    except (TypeError, ValueError) as exc:
        raise TrainingDataInputError("Replay split ratio components must be positive integers.") from exc
    if train <= 0 or monitor <= 0:
        raise TrainingDataInputError("Replay split ratio components must be positive integers.")
    divisor = math.gcd(train, monitor)
    return train // divisor, monitor // divisor


def single_source_replay_config_from_campaign(
    cfg: Mapping[str, Any],
    *,
    base_directory: str | Path | None = None,
) -> ReplaySingleSourceConfig | None:
    """Resolve the new one-file replay interface without changing legacy execution.

    A campaign may use the new ``[paths].replay_set`` interface or the legacy
    split-file interface, never both.  Returning ``None`` means the campaign is
    legacy/no-replay and preserves all historical behavior until UNIFY1D.
    """

    paths = cfg.get("paths", {})
    replay = cfg.get("replay", {})
    if not isinstance(paths, Mapping) or not isinstance(replay, Mapping):
        raise TrainingDataInputError("Campaign [paths] and [replay] sections must be mappings.")
    replay_set = paths.get("replay_set")
    legacy_keys = ("replay_train", "replay_monitor", "replay_true_labels")
    legacy_present = tuple(key for key in legacy_keys if paths.get(key) not in (None, ""))
    if replay_set not in (None, "") and legacy_present:
        raise TrainingDataInputError(
            "[paths].replay_set cannot be combined with legacy replay paths: " + ", ".join(legacy_present)
        )
    if replay_set in (None, ""):
        return None

    raw_label_mode = replay.get("label_mode")
    if raw_label_mode in (None, ""):
        # Controlled convenience for configurations mechanically migrated from
        # the historical mode field; new generated configs will emit label_mode.
        old_mode = str(replay.get("mode", "")).strip().lower()
        if old_mode == ReplayMode.EXTERNAL_PSEUDOLABEL.value:
            raw_label_mode = ReplayLabelMode.FOUNDATION_PSEUDOLABEL.value
        elif old_mode == ReplayMode.EXTERNAL_TRUE_LABEL.value:
            raw_label_mode = ReplayLabelMode.TRUE_DFT.value
        else:
            raise TrainingDataInputError(
                "Single-source replay requires [replay].label_mode = true_dft or foundation_pseudolabel."
            )

    source = Path(str(replay_set)).expanduser()
    if base_directory is not None and not source.is_absolute():
        source = Path(base_directory).expanduser().resolve() / source
    source = source.resolve()
    try:
        label_mode = ReplayLabelMode(str(raw_label_mode))
    except ValueError as exc:
        raise TrainingDataInputError(
            "Single-source replay label_mode must be true_dft or foundation_pseudolabel."
        ) from exc
    try:
        split_seed = int(replay.get("split_seed", DEFAULT_REPLAY_SPLIT_SEED))
    except (TypeError, ValueError) as exc:
        raise TrainingDataInputError("Replay split_seed must be a nonnegative integer.") from exc
    return ReplaySingleSourceConfig(
        replay_set_path=str(source),
        label_mode=label_mode,
        split_ratio=normalize_replay_split_ratio(replay.get("split_ratio", DEFAULT_REPLAY_SPLIT_RATIO)),
        split_seed=split_seed,
    )


def canonical_replay_geometry_identity(atoms: Any) -> str:
    """Versioned replay geometry identity with 1e-8 Angstrom quantization.

    Atomic ordering is intentionally preserved.  This identity is used only by
    the new single-source authority; historical ReplayFileArtifact identities
    retain their prior wrapped-fractional-coordinate semantics.
    """

    numbers = np.asarray(atoms.numbers, dtype="<i4")
    positions = np.asarray(atoms.positions, dtype=np.float64)
    cell = np.asarray(atoms.cell.array, dtype=np.float64)
    pbc = np.asarray(atoms.pbc, dtype=np.uint8)
    if positions.shape != (len(numbers), 3) or cell.shape != (3, 3) or pbc.shape != (3,):
        raise TrainingDataInputError("Replay geometry has an invalid positions/cell/PBC shape.")
    if not np.all(np.isfinite(positions)) or not np.all(np.isfinite(cell)):
        raise TrainingDataInputError("Replay geometry contains non-finite positions or cell values.")
    scale = REPLAY_GEOMETRY_QUANTIZATION_ANGSTROM
    q_positions = np.rint(positions / scale).astype("<i8", copy=False)
    q_cell = np.rint(cell / scale).astype("<i8", copy=False)
    h = hashlib.sha256()
    h.update(REPLAY_GEOMETRY_IDENTITY_SCHEMA.encode("ascii"))
    h.update(b"\0")
    h.update(numbers.tobytes(order="C"))
    h.update(q_positions.tobytes(order="C"))
    h.update(q_cell.tobytes(order="C"))
    h.update(pbc.tobytes(order="C"))
    return h.hexdigest()


def _optional_replay_label(atoms: Any, keys: Sequence[str], *, array: bool) -> np.ndarray | None:
    stores: list[Mapping[str, Any]] = [atoms.arrays if array else atoms.info]
    calculator = getattr(atoms, "calc", None)
    if calculator is not None and isinstance(getattr(calculator, "results", None), Mapping):
        stores.append(calculator.results)
    for store in stores:
        for key in keys:
            if key not in store or store[key] is None:
                continue
            try:
                value = np.asarray(store[key], dtype=np.float64)
            except (TypeError, ValueError):
                continue
            if np.all(np.isfinite(value)):
                return value
    return None


def _source_true_label_identity(
    energy: np.ndarray | None,
    forces: np.ndarray | None,
    stress: np.ndarray | None,
    *,
    natoms: int,
) -> str | None:
    if energy is None or forces is None:
        return None
    energy_flat = np.asarray(energy, dtype=np.float64).reshape(-1)
    forces_array = np.asarray(forces, dtype=np.float64)
    if energy_flat.size != 1 or forces_array.shape != (natoms, 3):
        return None
    payload: dict[str, Any] = {
        "namespace": ReplayLabelNamespace.SOURCE_TRUE.value,
        "energy": _array_identity(energy_flat),
        "forces": _array_identity(forces_array),
        "stress": None,
    }
    if stress is not None:
        stress_flat = np.asarray(stress, dtype=np.float64).reshape(-1)
        if stress_flat.size in (6, 9):
            payload["stress"] = _array_identity(stress_flat)
    return digest(payload)


@dataclass(frozen=True, slots=True)
class ReplaySourceArtifact:
    """Immutable authority for one externally supplied selected replay corpus."""

    path: str
    sha256: str
    configuration_count: int
    atomic_numbers: tuple[int, ...]
    geometry_identities: tuple[str, ...]
    source_label_identities: tuple[str | None, ...]
    source_energy_present_count: int
    source_forces_present_count: int
    source_stress_present_count: int
    serialization_schema: str = REPLAY_SOURCE_ARTIFACT_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_SOURCE_ARTIFACT_SCHEMA:
            raise TrainingDataInputError("Unsupported replay-source artifact schema.")
        object.__setattr__(self, "sha256", validate_digest(self.sha256, name="sha256"))
        if self.configuration_count <= 0:
            raise TrainingDataInputError("Replay source must contain at least one configuration.")
        numbers = tuple(sorted(set(int(v) for v in self.atomic_numbers)))
        if not numbers or any(v <= 0 for v in numbers):
            raise TrainingDataInputError("Replay-source atomic numbers are invalid.")
        identities = tuple(validate_digest(v, name="geometry_identity") for v in self.geometry_identities)
        if len(identities) != self.configuration_count:
            raise TrainingDataInputError("Replay-source geometry identities must match configuration count.")
        if len(set(identities)) != len(identities):
            raise TrainingDataInputError("Replay source contains duplicate canonical geometries.")
        labels: list[str | None] = []
        if len(self.source_label_identities) != self.configuration_count:
            raise TrainingDataInputError("Replay-source label identities must match configuration count.")
        for value in self.source_label_identities:
            labels.append(None if value is None else validate_digest(value, name="source_label_identity"))
        for name, count in (
            ("source_energy_present_count", self.source_energy_present_count),
            ("source_forces_present_count", self.source_forces_present_count),
            ("source_stress_present_count", self.source_stress_present_count),
        ):
            if int(count) < 0 or int(count) > self.configuration_count:
                raise TrainingDataInputError(f"{name} is outside replay-source bounds.")
        object.__setattr__(self, "atomic_numbers", numbers)
        object.__setattr__(self, "geometry_identities", identities)
        object.__setattr__(self, "source_label_identities", tuple(labels))

    @property
    def complete_true_label_count(self) -> int:
        return sum(value is not None for value in self.source_label_identities)

    @property
    def geometry_set_digest(self) -> str:
        # Order-independent set digest supports deterministic split membership
        # even when the same selected replay corpus is rewritten in a new order.
        return digest({"geometry_identities": sorted(self.geometry_identities)})

    @property
    def source_index_digest(self) -> str:
        return digest({"geometry_identities": list(self.geometry_identities)})

    @property
    def source_true_label_payload_digest(self) -> str:
        return digest({"source_label_identities": list(self.source_label_identities)})

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "sha256": self.sha256,
            "configuration_count": self.configuration_count,
            "atomic_numbers": list(self.atomic_numbers),
            "geometry_identities": list(self.geometry_identities),
            "geometry_set_digest": self.geometry_set_digest,
            "source_index_digest": self.source_index_digest,
            "source_label_identities": list(self.source_label_identities),
            "source_true_label_payload_digest": self.source_true_label_payload_digest,
            "source_energy_present_count": self.source_energy_present_count,
            "source_forces_present_count": self.source_forces_present_count,
            "source_stress_present_count": self.source_stress_present_count,
            "complete_true_label_count": self.complete_true_label_count,
            "geometry_identity_schema": REPLAY_GEOMETRY_IDENTITY_SCHEMA,
            "geometry_quantization_angstrom": REPLAY_GEOMETRY_QUANTIZATION_ANGSTROM,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "path": self.path, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplaySourceArtifact":
        if payload.get("schema") != REPLAY_SOURCE_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay-source artifact schema.")
        result = cls(
            path=str(payload["path"]),
            sha256=str(payload["sha256"]),
            configuration_count=int(payload["configuration_count"]),
            atomic_numbers=tuple(int(v) for v in payload["atomic_numbers"]),
            geometry_identities=tuple(str(v) for v in payload["geometry_identities"]),
            source_label_identities=tuple(None if v is None else str(v) for v in payload["source_label_identities"]),
            source_energy_present_count=int(payload["source_energy_present_count"]),
            source_forces_present_count=int(payload["source_forces_present_count"]),
            source_stress_present_count=int(payload["source_stress_present_count"]),
        )
        for key, expected in (
            ("geometry_set_digest", result.geometry_set_digest),
            ("source_index_digest", result.source_index_digest),
            ("source_true_label_payload_digest", result.source_true_label_payload_digest),
            ("content_digest", result.content_digest),
        ):
            if payload.get(key) not in (None, expected):
                raise TrainingDataSerializationError(f"Replay-source {key} mismatch.")
        return result


def inspect_replay_source_extxyz(path: str | Path) -> ReplaySourceArtifact:
    """Stream one selected replay ExtXYZ into the new source authority."""

    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to inspect replay source files.") from exc
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise TrainingDataInputError(f"Replay source file does not exist: {source!s}.")
    identities: list[str] = []
    source_labels: list[str | None] = []
    atomic_numbers: set[int] = set()
    energy_count = 0
    forces_count = 0
    stress_count = 0
    for atoms in iread(source, index=":", format="extxyz"):
        identity = canonical_replay_geometry_identity(atoms)
        identities.append(identity)
        atomic_numbers.update(int(v) for v in atoms.numbers)
        energy = _optional_replay_label(atoms, ("REF_energy", "energy", "corrected_total_energy"), array=False)
        forces = _optional_replay_label(atoms, ("REF_forces", "forces"), array=True)
        stress = _optional_replay_label(atoms, ("REF_stress", "stress"), array=False)
        energy_count += int(energy is not None and np.asarray(energy).size == 1)
        forces_count += int(forces is not None and np.asarray(forces).shape == (len(atoms), 3))
        stress_count += int(stress is not None and np.asarray(stress).reshape(-1).size in (6, 9))
        source_labels.append(_source_true_label_identity(energy, forces, stress, natoms=len(atoms)))
    if not identities:
        raise TrainingDataInputError(f"Replay source contains no ExtXYZ configurations: {source!s}.")
    if len(set(identities)) != len(identities):
        seen: set[str] = set()
        duplicate = ""
        for value in identities:
            if value in seen:
                duplicate = value
                break
            seen.add(value)
        raise TrainingDataInputError(f"Replay source contains duplicate canonical geometry {duplicate}.")
    return ReplaySourceArtifact(
        path=str(source),
        sha256=_sha256_file(source),
        configuration_count=len(identities),
        atomic_numbers=tuple(sorted(atomic_numbers)),
        geometry_identities=tuple(identities),
        source_label_identities=tuple(source_labels),
        source_energy_present_count=energy_count,
        source_forces_present_count=forces_count,
        source_stress_present_count=stress_count,
    )


def replay_split_rank(geometry_identity: str, seed: int) -> str:
    """Stable seeded rank used by every train/monitor split generation."""

    identity = validate_digest(geometry_identity, name="geometry_identity")
    if int(seed) < 0:
        raise TrainingDataInputError("Replay split seed must be nonnegative.")
    h = hashlib.sha256()
    h.update(REPLAY_SPLIT_RANK_SCHEMA.encode("ascii"))
    h.update(b"\0")
    h.update(str(int(seed)).encode("ascii"))
    h.update(b"\0")
    h.update(bytes.fromhex(identity))
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class ReplaySplitManifest:
    """Immutable label-independent train/monitor membership authority."""

    source_geometry_set_digest: str
    qualification_authority_digest: str | None
    eligible_geometry_set_digest: str
    split_ratio: tuple[int, int]
    split_seed: int
    train_geometry_identities: tuple[str, ...]
    monitor_geometry_identities: tuple[str, ...]
    serialization_schema: str = REPLAY_SPLIT_MANIFEST_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_SPLIT_MANIFEST_SCHEMA:
            raise TrainingDataInputError("Unsupported replay split-manifest schema.")
        object.__setattr__(self, "source_geometry_set_digest", validate_digest(self.source_geometry_set_digest, name="source_geometry_set_digest"))
        if self.qualification_authority_digest is not None:
            object.__setattr__(self, "qualification_authority_digest", validate_digest(self.qualification_authority_digest, name="qualification_authority_digest"))
        object.__setattr__(self, "eligible_geometry_set_digest", validate_digest(self.eligible_geometry_set_digest, name="eligible_geometry_set_digest"))
        object.__setattr__(self, "split_ratio", normalize_replay_split_ratio(self.split_ratio))
        if int(self.split_seed) < 0:
            raise TrainingDataInputError("Replay split seed must be nonnegative.")
        object.__setattr__(self, "split_seed", int(self.split_seed))
        train = tuple(validate_digest(v, name="train_geometry_identity") for v in self.train_geometry_identities)
        monitor = tuple(validate_digest(v, name="monitor_geometry_identity") for v in self.monitor_geometry_identities)
        if not train or not monitor:
            raise TrainingDataInputError("Replay split must contain at least one train and one monitor configuration.")
        if len(set(train)) != len(train) or len(set(monitor)) != len(monitor):
            raise TrainingDataInputError("Replay split contains duplicate geometry identities.")
        if set(train) & set(monitor):
            raise TrainingDataInputError("Replay train and monitor memberships overlap.")
        eligible_digest = digest({"geometry_identities": sorted((*train, *monitor))})
        if eligible_digest != self.eligible_geometry_set_digest:
            raise TrainingDataInputError("Replay split eligible-geometry digest does not match membership union.")
        object.__setattr__(self, "train_geometry_identities", train)
        object.__setattr__(self, "monitor_geometry_identities", monitor)

    @property
    def train_count(self) -> int:
        return len(self.train_geometry_identities)

    @property
    def monitor_count(self) -> int:
        return len(self.monitor_geometry_identities)

    @property
    def configuration_count(self) -> int:
        return self.train_count + self.monitor_count

    @property
    def train_geometry_set_digest(self) -> str:
        return digest({"geometry_identities": sorted(self.train_geometry_identities)})

    @property
    def monitor_geometry_set_digest(self) -> str:
        return digest({"geometry_identities": sorted(self.monitor_geometry_identities)})

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "source_geometry_set_digest": self.source_geometry_set_digest,
            "qualification_authority_digest": self.qualification_authority_digest,
            "eligible_geometry_set_digest": self.eligible_geometry_set_digest,
            "split_ratio": list(self.split_ratio),
            "split_seed": self.split_seed,
            "split_rank_schema": REPLAY_SPLIT_RANK_SCHEMA,
            "train_geometry_identities": list(self.train_geometry_identities),
            "monitor_geometry_identities": list(self.monitor_geometry_identities),
            "train_geometry_set_digest": self.train_geometry_set_digest,
            "monitor_geometry_set_digest": self.monitor_geometry_set_digest,
            "train_count": self.train_count,
            "monitor_count": self.monitor_count,
            "configuration_count": self.configuration_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplaySplitManifest":
        if payload.get("schema") != REPLAY_SPLIT_MANIFEST_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay split-manifest schema.")
        result = cls(
            source_geometry_set_digest=str(payload["source_geometry_set_digest"]),
            qualification_authority_digest=(None if payload.get("qualification_authority_digest") is None else str(payload["qualification_authority_digest"])),
            eligible_geometry_set_digest=str(payload["eligible_geometry_set_digest"]),
            split_ratio=tuple(int(v) for v in payload["split_ratio"]),
            split_seed=int(payload["split_seed"]),
            train_geometry_identities=tuple(str(v) for v in payload["train_geometry_identities"]),
            monitor_geometry_identities=tuple(str(v) for v in payload["monitor_geometry_identities"]),
        )
        for key, expected in (
            ("train_geometry_set_digest", result.train_geometry_set_digest),
            ("monitor_geometry_set_digest", result.monitor_geometry_set_digest),
            ("content_digest", result.content_digest),
        ):
            if payload.get(key) not in (None, expected):
                raise TrainingDataSerializationError(f"Replay split-manifest {key} mismatch.")
        return result


def build_replay_split_manifest(
    source: ReplaySourceArtifact,
    *,
    eligible_geometry_identities: Sequence[str] | None = None,
    qualification_authority_digest: str | None = None,
    split_ratio: tuple[int, int] | str = DEFAULT_REPLAY_SPLIT_RATIO,
    split_seed: int = DEFAULT_REPLAY_SPLIT_SEED,
) -> ReplaySplitManifest:
    """Build an exact, order-independent train/monitor split manifest."""

    ratio = normalize_replay_split_ratio(split_ratio)
    if int(split_seed) < 0:
        raise TrainingDataInputError("Replay split seed must be nonnegative.")
    source_set = set(source.geometry_identities)
    if eligible_geometry_identities is None:
        eligible = tuple(source_set)
    else:
        eligible = tuple(validate_digest(v, name="eligible_geometry_identity") for v in eligible_geometry_identities)
        if len(set(eligible)) != len(eligible):
            raise TrainingDataInputError("Eligible replay geometry list contains duplicates.")
        unknown = set(eligible) - source_set
        if unknown:
            raise TrainingDataInputError("Eligible replay geometry set contains identities absent from the replay source.")
    if len(eligible) < 2:
        raise TrainingDataInputError("At least two eligible replay configurations are required for train/monitor splitting.")
    ranked = sorted((replay_split_rank(identity, int(split_seed)), identity) for identity in eligible)
    train_count = (len(ranked) * ratio[0]) // (ratio[0] + ratio[1])
    train_count = min(max(train_count, 1), len(ranked) - 1)
    train = tuple(identity for _, identity in ranked[:train_count])
    monitor = tuple(identity for _, identity in ranked[train_count:])
    eligible_digest = digest({"geometry_identities": sorted(eligible)})
    return ReplaySplitManifest(
        source_geometry_set_digest=source.geometry_set_digest,
        qualification_authority_digest=qualification_authority_digest,
        eligible_geometry_set_digest=eligible_digest,
        split_ratio=ratio,
        split_seed=int(split_seed),
        train_geometry_identities=train,
        monitor_geometry_identities=monitor,
    )



@dataclass(frozen=True, slots=True)
class ReplayTrueLabelCache:
    """Logical source-true-label authority for one single replay corpus.

    The cache stores label identities rather than duplicating numerical arrays.
    Its content identity is independent of source-file ordering and location, so
    a bytewise rewrite/reorder with the same geometry->label mapping does not
    invalidate downstream logical true-label views.
    """

    source_geometry_set_digest: str
    geometry_identities: tuple[str, ...]
    source_label_identities: tuple[str | None, ...]
    stress_present_count: int
    serialization_schema: str = REPLAY_TRUE_LABEL_CACHE_SCHEMA

    def __post_init__(self) -> None:
        if self.serialization_schema != REPLAY_TRUE_LABEL_CACHE_SCHEMA:
            raise TrainingDataInputError("Unsupported replay true-label cache schema.")
        object.__setattr__(
            self,
            "source_geometry_set_digest",
            validate_digest(self.source_geometry_set_digest, name="source_geometry_set_digest"),
        )
        geometries = tuple(validate_digest(v, name="geometry_identity") for v in self.geometry_identities)
        if not geometries or len(set(geometries)) != len(geometries):
            raise TrainingDataInputError("Replay true-label cache geometry identities must be unique and non-empty.")
        if len(self.source_label_identities) != len(geometries):
            raise TrainingDataInputError("Replay true-label cache labels must match geometry count.")
        labels = tuple(
            None if value is None else validate_digest(value, name="source_label_identity")
            for value in self.source_label_identities
        )
        geometry_set_digest = digest({"geometry_identities": sorted(geometries)})
        if geometry_set_digest != self.source_geometry_set_digest:
            raise TrainingDataInputError("Replay true-label cache geometry-set digest mismatch.")
        if int(self.stress_present_count) < 0 or int(self.stress_present_count) > len(geometries):
            raise TrainingDataInputError("Replay true-label cache stress count is outside bounds.")
        # Canonicalize mapping order by geometry identity to make the logical
        # cache independent of the ExtXYZ source ordering.
        records = sorted(zip(geometries, labels, strict=True), key=lambda item: item[0])
        object.__setattr__(self, "geometry_identities", tuple(item[0] for item in records))
        object.__setattr__(self, "source_label_identities", tuple(item[1] for item in records))
        object.__setattr__(self, "stress_present_count", int(self.stress_present_count))

    @property
    def configuration_count(self) -> int:
        return len(self.geometry_identities)

    @property
    def complete_true_label_count(self) -> int:
        return sum(value is not None for value in self.source_label_identities)

    @property
    def missing_true_label_count(self) -> int:
        return self.configuration_count - self.complete_true_label_count

    @property
    def label_mapping_digest(self) -> str:
        return digest(
            {
                "namespace": ReplayLabelNamespace.SOURCE_TRUE.value,
                "records": [
                    [geometry, label]
                    for geometry, label in zip(self.geometry_identities, self.source_label_identities, strict=True)
                ],
            }
        )

    @property
    def content_digest(self) -> str:
        return digest(
            {
                "schema": self.serialization_schema,
                "source_geometry_set_digest": self.source_geometry_set_digest,
                "label_mapping_digest": self.label_mapping_digest,
                "configuration_count": self.configuration_count,
                "complete_true_label_count": self.complete_true_label_count,
                "missing_true_label_count": self.missing_true_label_count,
                "stress_present_count": self.stress_present_count,
            }
        )

    def label_identity_for(self, geometry_identity: str) -> str | None:
        identity = validate_digest(geometry_identity, name="geometry_identity")
        # The cache is normally small enough for a dict; callers processing a
        # full file should use label_mapping once rather than repeated lookup.
        return dict(zip(self.geometry_identities, self.source_label_identities, strict=True)).get(identity)

    @property
    def label_mapping(self) -> dict[str, str | None]:
        return dict(zip(self.geometry_identities, self.source_label_identities, strict=True))

    def label_set_digest_for(self, geometry_identities: Sequence[str]) -> str:
        mapping = self.label_mapping
        records: list[tuple[str, str]] = []
        for raw_identity in geometry_identities:
            identity = validate_digest(raw_identity, name="geometry_identity")
            if identity not in mapping:
                raise TrainingDataInputError("Requested true-label geometry is absent from the replay cache.")
            label_identity = mapping[identity]
            if label_identity is None:
                raise TrainingDataInputError(
                    f"Replay geometry {identity} lacks a complete finite source energy/forces label pair."
                )
            records.append((identity, label_identity))
        return digest(
            {
                "namespace": ReplayLabelNamespace.SOURCE_TRUE.value,
                "records": [[g, l] for g, l in sorted(records)],
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "source_geometry_set_digest": self.source_geometry_set_digest,
            "geometry_identities": list(self.geometry_identities),
            "source_label_identities": list(self.source_label_identities),
            "configuration_count": self.configuration_count,
            "complete_true_label_count": self.complete_true_label_count,
            "missing_true_label_count": self.missing_true_label_count,
            "stress_present_count": self.stress_present_count,
            "label_mapping_digest": self.label_mapping_digest,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayTrueLabelCache":
        if payload.get("schema") != REPLAY_TRUE_LABEL_CACHE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay true-label cache schema.")
        result = cls(
            source_geometry_set_digest=str(payload["source_geometry_set_digest"]),
            geometry_identities=tuple(str(v) for v in payload["geometry_identities"]),
            source_label_identities=tuple(
                None if value is None else str(value) for value in payload["source_label_identities"]
            ),
            stress_present_count=int(payload.get("stress_present_count", 0)),
        )
        for key, expected in (
            ("label_mapping_digest", result.label_mapping_digest),
            ("content_digest", result.content_digest),
        ):
            if payload.get(key) not in (None, expected):
                raise TrainingDataSerializationError(f"Replay true-label cache {key} mismatch.")
        return result


def build_replay_true_label_cache(source: ReplaySourceArtifact) -> ReplayTrueLabelCache:
    """Build the source-true-label cache from the streamed source artifact."""

    return ReplayTrueLabelCache(
        source_geometry_set_digest=source.geometry_set_digest,
        geometry_identities=source.geometry_identities,
        source_label_identities=source.source_label_identities,
        stress_present_count=source.source_stress_present_count,
    )


def _source_true_label_mapping_digest(source: ReplaySourceArtifact) -> str:
    records = sorted(
        zip(source.geometry_identities, source.source_label_identities, strict=True),
        key=lambda item: item[0],
    )
    return digest(
        {
            "namespace": ReplayLabelNamespace.SOURCE_TRUE.value,
            "records": [[geometry, label] for geometry, label in records],
        }
    )


class ReplaySplitRole(str, Enum):
    TRAIN = "train"
    MONITOR = "monitor"


@dataclass(frozen=True, slots=True)
class ReplayTrueLabelViewArtifact:
    """Authenticated materialized source-true-label transport view."""

    role: ReplaySplitRole
    path: str
    sha256: str
    configuration_count: int
    geometry_set_digest: str
    true_label_set_digest: str
    source_geometry_set_digest: str
    true_label_cache_digest: str
    split_manifest_digest: str
    serialization_schema: str = REPLAY_TRUE_LABEL_VIEW_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", ReplaySplitRole(self.role))
        if self.serialization_schema != REPLAY_TRUE_LABEL_VIEW_SCHEMA:
            raise TrainingDataInputError("Unsupported replay true-label view schema.")
        object.__setattr__(self, "sha256", validate_digest(self.sha256, name="sha256"))
        for name in (
            "geometry_set_digest",
            "true_label_set_digest",
            "source_geometry_set_digest",
            "true_label_cache_digest",
            "split_manifest_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if int(self.configuration_count) <= 0:
            raise TrainingDataInputError("Replay true-label view must contain at least one configuration.")
        object.__setattr__(self, "configuration_count", int(self.configuration_count))

    @property
    def logical_digest(self) -> str:
        # Excludes locator and transport bytes/order. This is the stable
        # downstream identity for lazy reconstruction of the same logical view.
        return digest(
            {
                "schema": self.serialization_schema,
                "role": self.role.value,
                "configuration_count": self.configuration_count,
                "geometry_set_digest": self.geometry_set_digest,
                "true_label_set_digest": self.true_label_set_digest,
                "source_geometry_set_digest": self.source_geometry_set_digest,
                "true_label_cache_digest": self.true_label_cache_digest,
                "split_manifest_digest": self.split_manifest_digest,
                "label_namespace": ReplayLabelNamespace.SOURCE_TRUE.value,
                "transport_fields": ["REF_energy", "REF_forces", "REF_stress"],
            }
        )

    @property
    def content_digest(self) -> str:
        return digest({"logical_digest": self.logical_digest, "sha256": self.sha256})

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "role": self.role.value,
            "path": self.path,
            "sha256": self.sha256,
            "configuration_count": self.configuration_count,
            "geometry_set_digest": self.geometry_set_digest,
            "true_label_set_digest": self.true_label_set_digest,
            "source_geometry_set_digest": self.source_geometry_set_digest,
            "true_label_cache_digest": self.true_label_cache_digest,
            "split_manifest_digest": self.split_manifest_digest,
            "logical_digest": self.logical_digest,
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayTrueLabelViewArtifact":
        if payload.get("schema") != REPLAY_TRUE_LABEL_VIEW_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay true-label view schema.")
        result = cls(
            role=ReplaySplitRole(payload["role"]),
            path=str(payload["path"]),
            sha256=str(payload["sha256"]),
            configuration_count=int(payload["configuration_count"]),
            geometry_set_digest=str(payload["geometry_set_digest"]),
            true_label_set_digest=str(payload["true_label_set_digest"]),
            source_geometry_set_digest=str(payload["source_geometry_set_digest"]),
            true_label_cache_digest=str(payload["true_label_cache_digest"]),
            split_manifest_digest=str(payload["split_manifest_digest"]),
        )
        for key, expected in (("logical_digest", result.logical_digest), ("content_digest", result.content_digest)):
            if payload.get(key) not in (None, expected):
                raise TrainingDataSerializationError(f"Replay true-label view {key} mismatch.")
        return result


class _BufferedReplayExtXYZWriter:
    """Bounded-memory ExtXYZ writer used by lazy replay materialization."""

    def __init__(self, path: Path, *, buffer_size: int) -> None:
        self.path = path
        self.buffer_size = max(1, int(buffer_size))
        self._buffer: list[Any] = []
        self._written = False
        self.count = 0
        self.path.unlink(missing_ok=True)

    def add(self, atoms: Any) -> None:
        self._buffer.append(atoms)
        if len(self._buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        from ase.io import write

        write(self.path, self._buffer, format="extxyz", append=self._written)
        self.count += len(self._buffer)
        self._written = True
        self._buffer.clear()

    def close(self) -> None:
        self.flush()
        if not self._written:
            self.path.touch()


def _split_role_geometry_identities(split: ReplaySplitManifest, role: ReplaySplitRole) -> tuple[str, ...]:
    return split.train_geometry_identities if role is ReplaySplitRole.TRAIN else split.monitor_geometry_identities


def _replay_true_label_view_expected_logical_digest(
    cache: ReplayTrueLabelCache,
    split: ReplaySplitManifest,
    role: ReplaySplitRole,
) -> tuple[str, str, int, str]:
    identities = _split_role_geometry_identities(split, role)
    geometry_set_digest = digest({"geometry_identities": sorted(identities)})
    label_set_digest = cache.label_set_digest_for(identities)
    count = len(identities)
    logical = digest(
        {
            "schema": REPLAY_TRUE_LABEL_VIEW_SCHEMA,
            "role": role.value,
            "configuration_count": count,
            "geometry_set_digest": geometry_set_digest,
            "true_label_set_digest": label_set_digest,
            "source_geometry_set_digest": cache.source_geometry_set_digest,
            "true_label_cache_digest": cache.content_digest,
            "split_manifest_digest": split.content_digest,
            "label_namespace": ReplayLabelNamespace.SOURCE_TRUE.value,
            "transport_fields": ["REF_energy", "REF_forces", "REF_stress"],
        }
    )
    return logical, geometry_set_digest, count, label_set_digest


def _load_true_label_view_cache(
    output: Path,
    *,
    expected_logical_digest: str,
) -> ReplayTrueLabelViewArtifact | None:
    receipt_path = output.with_name(output.name + ".replay.json")
    if not output.is_file() or not receipt_path.is_file():
        return None
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        if payload.get("schema") != REPLAY_TRUE_LABEL_VIEW_RECEIPT_SCHEMA:
            return None
        view = ReplayTrueLabelViewArtifact.from_dict(payload["view"])
        if view.path != str(output) or view.logical_digest != expected_logical_digest:
            return None
        if view.sha256 != _sha256_file(output):
            return None
        return view
    except Exception:
        return None


def _extract_source_true_labels(atoms: Any) -> tuple[float, np.ndarray, np.ndarray | None, str]:
    energy = _optional_replay_label(atoms, ("REF_energy", "energy", "corrected_total_energy"), array=False)
    forces = _optional_replay_label(atoms, ("REF_forces", "forces"), array=True)
    stress = _optional_replay_label(atoms, ("REF_stress", "stress"), array=False)
    label_identity = _source_true_label_identity(energy, forces, stress, natoms=len(atoms))
    if label_identity is None:
        raise TrainingDataInputError("Replay source frame lacks a complete finite source energy/forces label pair.")
    energy_array = np.asarray(energy, dtype=np.float64).reshape(-1)
    forces_array = np.asarray(forces, dtype=np.float64)
    if energy_array.size != 1 or forces_array.shape != (len(atoms), 3):
        raise TrainingDataInputError("Replay source true-label dimensions are invalid.")
    stress_array = None
    if stress is not None:
        candidate = np.asarray(stress, dtype=np.float64).reshape(-1)
        if candidate.size in (6, 9):
            stress_array = candidate.copy()
    return float(energy_array[0]), forces_array.copy(), stress_array, label_identity


def _render_source_true_label_frame(
    atoms: Any,
    *,
    geometry_identity: str,
    role: ReplaySplitRole,
    source_index: int,
    cache: ReplayTrueLabelCache,
    label_mapping: Mapping[str, str | None],
    cache_digest: str,
    split: ReplaySplitManifest,
    split_digest: str,
) -> Any:
    energy, forces, stress, label_identity = _extract_source_true_labels(atoms)
    expected = label_mapping.get(geometry_identity)
    if expected is None or expected != label_identity:
        raise TrainingDataInputError("Replay source true labels do not match the authenticated true-label cache.")
    frame = atoms.copy()
    frame.calc = None
    for key in (
        "energy", "REF_energy", "stress", "REF_stress", "virial", "virials", "REF_virial", "REF_virials"
    ):
        frame.info.pop(key, None)
    for key in ("forces", "REF_forces"):
        if key in frame.arrays:
            del frame.arrays[key]
    frame.info["REF_energy"] = energy
    frame.arrays["REF_forces"] = forces
    if stress is not None:
        frame.info["REF_stress"] = stress
    frame.info["replay_label_mode"] = ReplayLabelMode.TRUE_DFT.value
    frame.info["replay_label_namespace"] = ReplayLabelNamespace.SOURCE_TRUE.value
    frame.info["replay_geometry_identity"] = geometry_identity
    frame.info["replay_split_role"] = role.value
    frame.info["replay_source_index"] = int(source_index)
    frame.info["replay_true_label_identity"] = label_identity
    frame.info["replay_true_label_cache_digest"] = cache_digest
    frame.info["replay_split_manifest_digest"] = split_digest
    for key in tuple(frame.info):
        if key.startswith("replay_pseudolabel_"):
            frame.info.pop(key, None)
    return frame


def materialize_replay_true_label_views(
    source: ReplaySourceArtifact,
    cache: ReplayTrueLabelCache,
    split: ReplaySplitManifest,
    output_directory: str | Path,
    *,
    roles: Sequence[ReplaySplitRole | str] = (ReplaySplitRole.TRAIN, ReplaySplitRole.MONITOR),
    buffer_size: int = 64,
    source_index: ReplaySourceIndex | None = None,
) -> dict[ReplaySplitRole, ReplayTrueLabelViewArtifact]:
    """Lazily materialize requested true-label replay roles in one source pass.

    Existing authenticated views are returned without opening/parsing the replay
    source. Missing/stale requested roles are regenerated together in one
    bounded-memory streaming pass. No pseudo-label inference is involved.
    """

    if source_index is None:
        try:
            from ase.io import iread
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TrainingDataInputError("ASE is required to materialize true-label replay views.") from exc
    if int(buffer_size) <= 0:
        raise TrainingDataInputError("Replay materialization buffer_size must be positive.")
    requested: list[ReplaySplitRole] = []
    for value in roles:
        role = ReplaySplitRole(value)
        if role not in requested:
            requested.append(role)
    if not requested:
        return {}
    if source.geometry_set_digest != cache.source_geometry_set_digest:
        raise TrainingDataInputError("Replay source and true-label cache geometry authorities differ.")
    if _source_true_label_mapping_digest(source) != cache.label_mapping_digest:
        raise TrainingDataInputError("Replay source and true-label cache label authorities differ.")
    if source.geometry_set_digest != split.source_geometry_set_digest:
        raise TrainingDataInputError("Replay source and split-manifest geometry authorities differ.")
    label_mapping = cache.label_mapping
    cache_digest = cache.content_digest
    split_digest = split.content_digest

    output_root = Path(output_directory).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    outputs = {
        role: output_root / f"replay_{role.value}.true-label.extxyz"
        for role in requested
    }
    expected: dict[ReplaySplitRole, tuple[str, str, int, str]] = {
        role: _replay_true_label_view_expected_logical_digest(cache, split, role) for role in requested
    }
    results: dict[ReplaySplitRole, ReplayTrueLabelViewArtifact] = {}
    pending: list[ReplaySplitRole] = []
    for role in requested:
        cached = _load_true_label_view_cache(outputs[role], expected_logical_digest=expected[role][0])
        if cached is None:
            pending.append(role)
        else:
            results[role] = cached
    if not pending:
        return results

    source_path = Path(source.path).expanduser().resolve()
    if not source_path.is_file():
        raise TrainingDataInputError(f"Replay source file does not exist: {source_path!s}.")
    if _sha256_file(source_path) != source.sha256:
        raise TrainingDataInputError("Replay source file SHA-256 differs from the authenticated source artifact.")

    role_membership = {role: set(_split_role_geometry_identities(split, role)) for role in pending}
    identity_role = {identity: role for role, identities in role_membership.items() for identity in identities}
    all_pending = set(identity_role)
    temporary_paths = {role: outputs[role].with_name(outputs[role].name + ".tmp") for role in pending}
    writers = {role: _BufferedReplayExtXYZWriter(temporary_paths[role], buffer_size=int(buffer_size)) for role in pending}
    seen: dict[ReplaySplitRole, set[str]] = {role: set() for role in pending}
    if source_index is None:
        frame_iterator = enumerate(iread(source_path, index=":", format="extxyz"))
    else:
        selected_indices = replay_source_indices_for_identities(source, all_pending)
        frame_iterator = iter_indexed_replay_frames(
            source, source_index, source_indices=selected_indices
        )
    try:
        for source_frame_index, atoms in frame_iterator:
            identity = source.geometry_identities[source_frame_index]
            matched_role = identity_role.get(identity)
            if matched_role is None:
                continue
            if identity in seen[matched_role]:
                raise TrainingDataInputError("Replay source yielded a duplicate geometry during true-label materialization.")
            frame = _render_source_true_label_frame(
                atoms,
                geometry_identity=identity,
                role=matched_role,
                source_index=source_frame_index,
                cache=cache,
                label_mapping=label_mapping,
                cache_digest=cache_digest,
                split=split,
                split_digest=split_digest,
            )
            writers[matched_role].add(frame)
            seen[matched_role].add(identity)
        for writer in writers.values():
            writer.close()
        for role in pending:
            missing = role_membership[role] - seen[role]
            unexpected = seen[role] - role_membership[role]
            if missing or unexpected or writers[role].count != len(role_membership[role]):
                raise TrainingDataInputError(
                    f"True-label {role.value} materialization membership mismatch: "
                    f"missing={len(missing)}, unexpected={len(unexpected)}."
                )
        for role in pending:
            temporary_paths[role].replace(outputs[role])
            logical, geometry_set_digest, count, label_set_digest = expected[role]
            view = ReplayTrueLabelViewArtifact(
                role=role,
                path=str(outputs[role]),
                sha256=_sha256_file(outputs[role]),
                configuration_count=count,
                geometry_set_digest=geometry_set_digest,
                true_label_set_digest=label_set_digest,
                source_geometry_set_digest=source.geometry_set_digest,
                true_label_cache_digest=cache.content_digest,
                split_manifest_digest=split.content_digest,
            )
            if view.logical_digest != logical:
                raise TrainingDataInputError("Internal true-label view logical-digest mismatch.")
            receipt_path = outputs[role].with_name(outputs[role].name + ".replay.json")
            receipt = {
                "schema": REPLAY_TRUE_LABEL_VIEW_RECEIPT_SCHEMA,
                "view": view.to_dict(),
            }
            receipt_tmp = receipt_path.with_name(receipt_path.name + ".tmp")
            receipt_tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            receipt_tmp.replace(receipt_path)
            results[role] = view
    except Exception:
        for writer in writers.values():
            try:
                writer._buffer.clear()
            except Exception:
                pass
        for path in temporary_paths.values():
            path.unlink(missing_ok=True)
        raise
    return results

def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _array_identity(values: np.ndarray) -> str:
    array = np.ascontiguousarray(np.asarray(values, dtype=np.float64))
    return hashlib.sha256(
        b"mdstats.replay-array.v1\0"
        + array.dtype.str.encode("ascii")
        + b"\0"
        + repr(tuple(int(v) for v in array.shape)).encode("ascii")
        + b"\0"
        + array.tobytes(order="C")
    ).hexdigest()


def _geometry_identity(atoms: Any) -> str:
    cell = np.asarray(atoms.cell.array, dtype=np.float64)
    scaled = np.mod(np.asarray(atoms.get_scaled_positions(wrap=True), dtype=np.float64), 1.0)
    return digest(
        {
            "numbers": [int(v) for v in atoms.numbers],
            "cell": np.round(cell, 10).tolist(),
            "scaled_positions": np.round(scaled, 10).tolist(),
            "pbc": [bool(v) for v in atoms.pbc],
        }
    )


@dataclass(frozen=True, slots=True)
class ReplayFileArtifact:
    path: str
    sha256: str
    configuration_count: int
    atomic_numbers: tuple[int, ...]
    geometry_identities: tuple[str, ...]
    label_identities: tuple[str, ...]
    energy_key: str
    forces_key: str
    stress_key: str
    stress_present_count: int
    label_mode: ReplayLabelMode = ReplayLabelMode.UNSPECIFIED
    foundation_checkpoint_digest: str | None = None
    foundation_label_generator_identity_digest: str | None = None
    serialization_schema: str = REPLAY_FILE_ARTIFACT_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "sha256", validate_digest(self.sha256, name="sha256"))
        object.__setattr__(self, "label_mode", ReplayLabelMode(self.label_mode))
        if self.foundation_checkpoint_digest is not None:
            object.__setattr__(
                self,
                "foundation_checkpoint_digest",
                validate_digest(self.foundation_checkpoint_digest, name="foundation_checkpoint_digest"),
            )
        if self.foundation_label_generator_identity_digest is not None:
            object.__setattr__(
                self,
                "foundation_label_generator_identity_digest",
                validate_digest(
                    self.foundation_label_generator_identity_digest,
                    name="foundation_label_generator_identity_digest",
                ),
            )
        if (
            self.serialization_schema == REPLAY_FILE_ARTIFACT_SCHEMA
            and self.label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL
            and self.foundation_label_generator_identity_digest is None
            and self.foundation_checkpoint_digest is not None
        ):
            # Preserve the historical direct-construction API as a v3 artifact.
            # New canonical replay plans supply the exact generator identity.
            object.__setattr__(self, "serialization_schema", REPLAY_FILE_ARTIFACT_V3_SCHEMA)
        if self.serialization_schema not in {REPLAY_FILE_ARTIFACT_SCHEMA, REPLAY_FILE_ARTIFACT_V3_SCHEMA}:
            raise TrainingDataInputError("Unsupported replay-file serialization schema.")
        if self.configuration_count <= 0:
            raise TrainingDataInputError("Replay files must contain configurations.")
        numbers = tuple(sorted(set(int(v) for v in self.atomic_numbers)))
        if any(v <= 0 for v in numbers):
            raise TrainingDataInputError("Replay atomic numbers are invalid.")
        identities = tuple(validate_digest(v, name="geometry_identity") for v in self.geometry_identities)
        labels = tuple(validate_digest(v, name="label_identity") for v in self.label_identities)
        if len(identities) != self.configuration_count or len(labels) != self.configuration_count:
            raise TrainingDataInputError("Replay geometry and label identities must match configuration count.")
        if len(set(identities)) != len(identities):
            raise TrainingDataInputError("Replay file contains exact duplicate geometries.")
        if self.stress_present_count < 0 or self.stress_present_count > self.configuration_count:
            raise TrainingDataInputError("Replay stress coverage is invalid.")
        if self.label_mode is ReplayLabelMode.FOUNDATION_PSEUDOLABEL:
            if self.serialization_schema == REPLAY_FILE_ARTIFACT_SCHEMA:
                if self.foundation_label_generator_identity_digest is None:
                    raise TrainingDataInputError(
                        "Pseudo-labeled replay v4 requires the exact foundation label-generator identity digest."
                    )
                if self.foundation_checkpoint_digest is not None:
                    raise TrainingDataInputError(
                        "Replay v4 uses label-generator identity rather than raw checkpoint-SHA provenance."
                    )
            elif self.foundation_checkpoint_digest is None:
                raise TrainingDataInputError(
                    "Legacy pseudo-labeled replay requires the exact foundation checkpoint digest."
                )
        elif self.foundation_checkpoint_digest is not None or self.foundation_label_generator_identity_digest is not None:
            raise TrainingDataInputError("Only pseudo-labeled replay may carry foundation provenance.")
        object.__setattr__(self, "atomic_numbers", numbers)
        object.__setattr__(self, "geometry_identities", identities)
        object.__setattr__(self, "label_identities", labels)

    @property
    def stress_coverage_fraction(self) -> float:
        return self.stress_present_count / self.configuration_count

    @property
    def label_payload_digest(self) -> str:
        return digest({"label_identities": list(self.label_identities)})

    @property
    def foundation_lineage_digest(self) -> str | None:
        return self.foundation_label_generator_identity_digest or self.foundation_checkpoint_digest

    @property
    def is_head_qualified_foundation_lineage(self) -> bool:
        return self.foundation_label_generator_identity_digest is not None

    def _identity_payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "sha256": self.sha256,
            "configuration_count": self.configuration_count,
            "atomic_numbers": list(self.atomic_numbers),
            "geometry_identities": list(self.geometry_identities),
            "label_identities": list(self.label_identities),
            "label_payload_digest": self.label_payload_digest,
            "energy_key": self.energy_key,
            "forces_key": self.forces_key,
            "stress_key": self.stress_key,
            "stress_present_count": self.stress_present_count,
            "stress_coverage_fraction": self.stress_coverage_fraction,
            "label_mode": self.label_mode.value,
        }
        if self.serialization_schema == REPLAY_FILE_ARTIFACT_SCHEMA:
            payload["foundation_label_generator_identity_digest"] = self.foundation_label_generator_identity_digest
        else:
            payload["foundation_checkpoint_digest"] = self.foundation_checkpoint_digest
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "path": self.path, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayFileArtifact":
        schema = str(payload.get("schema", ""))
        if schema not in {REPLAY_FILE_ARTIFACT_SCHEMA, REPLAY_FILE_ARTIFACT_V3_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported replay-file schema; re-inspect legacy replay files.")
        result = cls(
            path=str(payload["path"]),
            sha256=str(payload["sha256"]),
            configuration_count=int(payload["configuration_count"]),
            atomic_numbers=tuple(int(v) for v in payload["atomic_numbers"]),
            geometry_identities=tuple(str(v) for v in payload["geometry_identities"]),
            label_identities=tuple(str(v) for v in payload["label_identities"]),
            energy_key=str(payload["energy_key"]),
            forces_key=str(payload["forces_key"]),
            stress_key=str(payload["stress_key"]),
            stress_present_count=int(payload["stress_present_count"]),
            label_mode=ReplayLabelMode(payload.get("label_mode", ReplayLabelMode.UNSPECIFIED.value)),
            foundation_checkpoint_digest=(None if payload.get("foundation_checkpoint_digest") is None else str(payload["foundation_checkpoint_digest"])),
            foundation_label_generator_identity_digest=(None if payload.get("foundation_label_generator_identity_digest") is None else str(payload["foundation_label_generator_identity_digest"])),
            serialization_schema=schema,
        )
        if payload.get("label_payload_digest") not in (None, result.label_payload_digest):
            raise TrainingDataSerializationError("Replay label-payload digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Replay-file digest mismatch.")
        return result




@dataclass(frozen=True, slots=True)
class TrueLabelReplayResolution:
    """Resolved evaluation/training replay files carrying independent true labels."""

    root_directory: str
    train_path: str | None
    monitor_path: str
    train_artifact: ReplayFileArtifact | None
    monitor_artifact: ReplayFileArtifact
    source_path: str | None = None
    materialized: bool = False

    def __post_init__(self) -> None:
        if self.monitor_artifact.label_mode is not ReplayLabelMode.TRUE_DFT:
            raise TrainingDataInputError("Resolved replay monitor must carry true DFT labels.")
        if self.train_artifact is not None and self.train_artifact.label_mode is not ReplayLabelMode.TRUE_DFT:
            raise TrainingDataInputError("Resolved replay training file must carry true DFT labels.")
        if (self.train_path is None) != (self.train_artifact is None):
            raise TrainingDataInputError("True-label replay train path/artifact evidence is incomplete.")


def _frame_geometry_equivalent(left: Any, right: Any, *, atol: float = 2.0e-8) -> bool:
    if tuple(int(v) for v in left.numbers) != tuple(int(v) for v in right.numbers):
        return False
    if tuple(bool(v) for v in left.pbc) != tuple(bool(v) for v in right.pbc):
        return False
    return bool(
        np.allclose(np.asarray(left.cell.array, dtype=np.float64), np.asarray(right.cell.array, dtype=np.float64), rtol=0.0, atol=atol)
        and np.allclose(np.asarray(left.positions, dtype=np.float64), np.asarray(right.positions, dtype=np.float64), rtol=0.0, atol=atol)
    )


def _source_label_value(atoms: Any, candidates: Sequence[str], *, array: bool) -> tuple[str, np.ndarray]:
    stores = [atoms.arrays if array else atoms.info]
    calculator = getattr(atoms, "calc", None)
    if calculator is not None and isinstance(getattr(calculator, "results", None), Mapping):
        stores.append(calculator.results)
    for store in stores:
        for key in candidates:
            if key in store and store[key] is not None:
                value = np.asarray(store[key], dtype=np.float64)
                if np.all(np.isfinite(value)):
                    return key, value
    kind = "array/calculator result" if array else "info/calculator result"
    raise TrainingDataInputError(
        f"True-label replay source lacks a finite {kind}; tried {tuple(candidates)!r}."
    )


def materialize_true_label_replay_split(
    source_path: str | Path,
    split_geometry_path: str | Path,
    output_path: str | Path,
    *,
    source_index_key: str = "replay_source_index",
    output_energy_key: str = "REF_energy",
    output_forces_key: str = "REF_forces",
    output_stress_key: str = "REF_stress",
) -> ReplayFileArtifact:
    """Reattach independent source labels to an existing replay split.

    The split file supplies the exact geometry/order selected for training or
    monitoring.  The original true-label corpus supplies energy, forces, and
    optional stress.  ``replay_source_index`` is used when present; otherwise
    exact geometry identities are matched.  Existing pseudo-label fields are
    replaced rather than mixed with the true labels.
    """

    try:
        from ase.io import read, write
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to materialize true-label replay files.") from exc

    source = Path(source_path).expanduser().resolve()
    split = Path(split_geometry_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    if not source.is_file() or not split.is_file():
        raise TrainingDataInputError("True-label replay source and split files must exist.")
    source_sha = _sha256_file(source)
    split_sha = _sha256_file(split)
    provenance_path = output.with_name(output.name + ".provenance.json")
    if output.is_file() and provenance_path.is_file():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            if (
                provenance.get("schema") == "mdstats.true-label-replay-materialization.v1"
                and provenance.get("source_sha256") == source_sha
                and provenance.get("split_sha256") == split_sha
                and provenance.get("output_sha256") == _sha256_file(output)
            ):
                artifact = inspect_replay_extxyz(output, label_mode=ReplayLabelMode.TRUE_DFT)
                split_artifact = inspect_replay_extxyz(split)
                if artifact.geometry_identities == split_artifact.geometry_identities:
                    return artifact
        except Exception:
            pass
    source_atoms = read(source, index=":", format="extxyz")
    split_atoms = read(split, index=":", format="extxyz")
    if not isinstance(source_atoms, list):
        source_atoms = [source_atoms]
    if not isinstance(split_atoms, list):
        split_atoms = [split_atoms]
    if not source_atoms or not split_atoms:
        raise TrainingDataInputError("True-label replay source/split cannot be empty.")

    by_geometry: dict[str, int] | None = None
    rendered = []
    used_indices: set[int] = set()
    for split_index, geometry in enumerate(split_atoms):
        source_index_raw = geometry.info.get(source_index_key)
        if source_index_raw is None:
            if by_geometry is None:
                by_geometry = {}
                for index, atoms in enumerate(source_atoms):
                    identity = _geometry_identity(atoms)
                    if identity in by_geometry:
                        raise TrainingDataInputError(
                            "True-label replay source contains duplicate exact geometries; source-index metadata is required."
                        )
                    by_geometry[identity] = index
            source_index = by_geometry.get(_geometry_identity(geometry), -1)
        else:
            try:
                source_index_value = float(source_index_raw)
                source_index = int(source_index_value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise TrainingDataInputError(
                    f"Replay split frame {split_index} has invalid {source_index_key}."
                ) from exc
            if not np.isfinite(source_index_value) or source_index_value != source_index:
                raise TrainingDataInputError(
                    f"Replay split frame {split_index} has non-integral {source_index_key}."
                )
        if source_index < 0 or source_index >= len(source_atoms):
            raise TrainingDataInputError(
                f"Replay split frame {split_index} cannot be matched to the true-label source."
            )
        if source_index in used_indices:
            raise TrainingDataInputError("Replay split maps multiple frames to the same true-label source frame.")
        used_indices.add(source_index)
        labels = source_atoms[source_index]
        if not _frame_geometry_equivalent(labels, geometry):
            raise TrainingDataInputError(
                f"Replay split frame {split_index} geometry differs from true-label source frame {source_index}."
            )

        _, energy = _source_label_value(labels, ("energy", "REF_energy", "corrected_total_energy"), array=False)
        _, forces = _source_label_value(labels, ("forces", "REF_forces"), array=True)
        if energy.size != 1 or forces.shape != (len(geometry), 3):
            raise TrainingDataInputError(
                f"True-label source frame {source_index} has incompatible energy/force dimensions."
            )
        frame = geometry.copy()
        frame.info[output_energy_key] = float(energy.reshape(-1)[0])
        frame.arrays[output_forces_key] = np.asarray(forces, dtype=np.float64).copy()
        stress = None
        stress_stores = [labels.info]
        if getattr(labels, "calc", None) is not None and isinstance(getattr(labels.calc, "results", None), Mapping):
            stress_stores.append(labels.calc.results)
        for store in stress_stores:
            for key in ("stress", "REF_stress"):
                if key in store and store[key] is not None:
                    candidate = np.asarray(store[key], dtype=np.float64).reshape(-1)
                    if candidate.size not in {6, 9} or not np.all(np.isfinite(candidate)):
                        raise TrainingDataInputError(
                            f"True-label source frame {source_index} has invalid stress."
                        )
                    stress = candidate
                    break
            if stress is not None:
                break
        if stress is None:
            frame.info.pop(output_stress_key, None)
        else:
            frame.info[output_stress_key] = stress.copy()
        frame.info["replay_label_mode"] = ReplayLabelMode.TRUE_DFT.value
        frame.info["replay_true_label_source_index"] = source_index
        frame.info["replay_true_label_source_sha256"] = source_sha
        frame.info["replay_true_label_split_sha256"] = split_sha
        for key in (
            "replay_pseudolabel_model_sha256",
            "replay_pseudolabel_dtype",
            "replay_pseudolabel_device",
            "replay_pseudolabel_cueq",
        ):
            frame.info.pop(key, None)
        rendered.append(frame)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    write(temporary, rendered, format="extxyz")
    temporary.replace(output)
    artifact = inspect_replay_extxyz(output, label_mode=ReplayLabelMode.TRUE_DFT)
    split_artifact = inspect_replay_extxyz(
        split,
        label_mode=ReplayLabelMode.UNSPECIFIED,
        foundation_checkpoint_digest=None,
    )
    if artifact.geometry_identities != split_artifact.geometry_identities:
        output.unlink(missing_ok=True)
        provenance_path.unlink(missing_ok=True)
        raise TrainingDataInputError("True-label replay materialization changed replay geometry/order.")
    provenance = {
        "schema": "mdstats.true-label-replay-materialization.v1",
        "source_path": str(source),
        "source_sha256": source_sha,
        "split_path": str(split),
        "split_sha256": split_sha,
        "output_path": str(output),
        "output_sha256": artifact.sha256,
        "output_artifact_digest": artifact.content_digest,
    }
    temporary_provenance = provenance_path.with_name(provenance_path.name + ".tmp")
    temporary_provenance.write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary_provenance.replace(provenance_path)
    return artifact


def resolve_true_label_replay_directory(
    directory: str | Path,
    *,
    replay_train_path: str | Path | None,
    replay_monitor_path: str | Path,
    output_directory: str | Path,
    require_train: bool = False,
) -> TrueLabelReplayResolution:
    """Resolve split true-label replay files from a campaign input directory.

    Accepted layouts are either already-split files under ``true_labels/`` (or
    explicit ``replay_true_{train,monitor}.extxyz`` names), or the mdstats replay
    preparation layout containing ``mp_replay_selected.extxyz`` plus the
    pseudo-labelled replay split files carrying ``replay_source_index``.
    """

    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise TrainingDataInputError(f"True-label replay directory does not exist: {root!s}.")
    monitor_split = Path(replay_monitor_path).expanduser().resolve()
    train_split = None if replay_train_path is None else Path(replay_train_path).expanduser().resolve()
    if not monitor_split.is_file() or (require_train and (train_split is None or not train_split.is_file())):
        raise TrainingDataInputError("Configured replay split files are unavailable for true-label alignment.")

    paired_candidates = (
        (root / "true_labels" / "replay_train.extxyz", root / "true_labels" / "replay_monitor.extxyz"),
        (root / "replay_true_train.extxyz", root / "replay_true_monitor.extxyz"),
        (root / "true_replay_train.extxyz", root / "true_replay_monitor.extxyz"),
    )
    for train_candidate, monitor_candidate in paired_candidates:
        if monitor_candidate.is_file() and (not require_train or train_candidate.is_file()):
            monitor_artifact = inspect_replay_extxyz(
                monitor_candidate, label_mode=ReplayLabelMode.TRUE_DFT
            )
            split_monitor_artifact = inspect_replay_extxyz(monitor_split)
            if monitor_artifact.geometry_identities != split_monitor_artifact.geometry_identities:
                raise TrainingDataInputError(
                    "True-label replay monitor geometry/order does not match the configured replay monitor."
                )
            train_artifact = None
            train_value = None
            if train_candidate.is_file():
                train_artifact = inspect_replay_extxyz(
                    train_candidate, label_mode=ReplayLabelMode.TRUE_DFT
                )
                train_value = str(train_candidate)
                if train_split is not None:
                    split_train_artifact = inspect_replay_extxyz(train_split)
                    if train_artifact.geometry_identities != split_train_artifact.geometry_identities:
                        raise TrainingDataInputError(
                            "True-label replay training geometry/order does not match the configured replay training split."
                        )
            return TrueLabelReplayResolution(
                root_directory=str(root),
                train_path=train_value,
                monitor_path=str(monitor_candidate),
                train_artifact=train_artifact,
                monitor_artifact=monitor_artifact,
                source_path=None,
                materialized=False,
            )

    source = next(
        (
            candidate
            for candidate in (
                root / "mp_replay_selected.extxyz",
                root / "replay_true_source.extxyz",
                root / "true_labels.extxyz",
            )
            if candidate.is_file()
        ),
        None,
    )
    if source is None:
        raise TrainingDataInputError(
            "True-label replay directory must contain split true-label files or an original true-label source such as mp_replay_selected.extxyz."
        )
    output_root = Path(output_directory).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    monitor_output = output_root / "replay_monitor.true-label.extxyz"
    monitor_artifact = materialize_true_label_replay_split(
        source, monitor_split, monitor_output
    )
    train_artifact = None
    train_output_value = None
    if require_train:
        assert train_split is not None
        train_output = output_root / "replay_train.true-label.extxyz"
        train_artifact = materialize_true_label_replay_split(
            source, train_split, train_output
        )
        train_output_value = str(train_output)
    return TrueLabelReplayResolution(
        root_directory=str(root),
        train_path=train_output_value,
        monitor_path=str(monitor_output),
        train_artifact=train_artifact,
        monitor_artifact=monitor_artifact,
        source_path=str(source),
        materialized=True,
    )


def inspect_replay_extxyz(
    path: str | Path,
    *,
    energy_key: str = "REF_energy",
    forces_key: str = "REF_forces",
    stress_key: str = "REF_stress",
    label_mode: ReplayLabelMode = ReplayLabelMode.UNSPECIFIED,
    foundation_checkpoint_digest: str | None = None,
    foundation_label_generator_identity_digest: str | None = None,
) -> ReplayFileArtifact:
    try:
        from ase.io import read
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to inspect replay files.") from exc
    source = Path(path)
    if not source.is_file():
        raise TrainingDataInputError(f"Replay file does not exist: {source!s}.")
    atoms_list = read(source, index=":", format="extxyz")
    if not isinstance(atoms_list, list):
        atoms_list = [atoms_list]
    numbers: set[int] = set()
    identities: list[str] = []
    label_identities: list[str] = []
    stress_present = 0
    for index, atoms in enumerate(atoms_list):
        positions = np.asarray(atoms.positions, dtype=np.float64)
        cell = np.asarray(atoms.cell.array, dtype=np.float64)
        if positions.shape != (len(atoms), 3) or not np.all(np.isfinite(positions)):
            raise TrainingDataInputError(f"Replay frame {index} has invalid positions.")
        if cell.shape != (3, 3) or not np.all(np.isfinite(cell)) or abs(float(np.linalg.det(cell))) <= 1.0e-14:
            raise TrainingDataInputError(f"Replay frame {index} has an invalid cell.")
        numbers.update(int(v) for v in atoms.numbers)
        identities.append(_geometry_identity(atoms))
        if energy_key not in atoms.info:
            raise TrainingDataInputError(f"Replay frame {index} lacks {energy_key}.")
        energy = np.asarray(atoms.info[energy_key], dtype=np.float64)
        if energy.size != 1 or not np.all(np.isfinite(energy)):
            raise TrainingDataInputError(f"Replay frame {index} has invalid {energy_key}.")
        if forces_key not in atoms.arrays:
            raise TrainingDataInputError(f"Replay frame {index} lacks {forces_key}.")
        forces = np.asarray(atoms.arrays[forces_key], dtype=np.float64)
        if forces.shape != (len(atoms), 3) or not np.all(np.isfinite(forces)):
            raise TrainingDataInputError(f"Replay frame {index} has invalid {forces_key}.")
        stress = None
        if stress_key in atoms.info and atoms.info[stress_key] is not None:
            stress = np.asarray(atoms.info[stress_key], dtype=np.float64)
            if stress.size not in {6, 9} or not np.all(np.isfinite(stress)):
                raise TrainingDataInputError(f"Replay frame {index} has invalid {stress_key}.")
            stress_present += 1
        label_identities.append(digest({
            "energy": _array_identity(energy.reshape(1)),
            "forces": _array_identity(forces),
            "stress": None if stress is None else _array_identity(stress.reshape(-1)),
        }))
    if len(set(identities)) != len(identities):
        raise TrainingDataInputError("Replay file contains exact duplicate geometries.")
    return ReplayFileArtifact(
        path=str(source.resolve()),
        sha256=_sha256_file(source),
        configuration_count=len(atoms_list),
        atomic_numbers=tuple(numbers),
        geometry_identities=tuple(identities),
        label_identities=tuple(label_identities),
        energy_key=energy_key,
        forces_key=forces_key,
        stress_key=stress_key,
        stress_present_count=stress_present,
        label_mode=label_mode,
        foundation_checkpoint_digest=foundation_checkpoint_digest,
        foundation_label_generator_identity_digest=foundation_label_generator_identity_digest,
        serialization_schema=(
            REPLAY_FILE_ARTIFACT_SCHEMA
            if foundation_label_generator_identity_digest is not None or label_mode is not ReplayLabelMode.FOUNDATION_PSEUDOLABEL
            else REPLAY_FILE_ARTIFACT_V3_SCHEMA
        ),
    )


@dataclass(frozen=True, slots=True)
class ReplayRetentionPolicy:
    metric: str = "force_rmse"
    maximum_degradation_fraction: float = 0.20
    require_disjoint_monitor: bool = True
    failure_behavior: str = "reject_checkpoint"

    def __post_init__(self) -> None:
        if self.metric not in {"force_rmse", "combined_loss", "energy_force_stress"}:
            raise TrainingDataInputError("Unsupported replay-retention metric.")
        if not np.isfinite(self.maximum_degradation_fraction) or self.maximum_degradation_fraction < 0.0:
            raise TrainingDataInputError("Replay degradation tolerance is invalid.")
        if self.failure_behavior not in {"reject_checkpoint", "require_override"}:
            raise TrainingDataInputError("Unsupported replay-retention failure behavior.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REPLAY_RETENTION_POLICY_SCHEMA,
            "metric": self.metric,
            "maximum_degradation_fraction": self.maximum_degradation_fraction,
            "require_disjoint_monitor": self.require_disjoint_monitor,
            "failure_behavior": self.failure_behavior,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayRetentionPolicy":
        if payload.get("schema") != REPLAY_RETENTION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay-retention schema.")
        result = cls(
            metric=str(payload["metric"]),
            maximum_degradation_fraction=float(payload["maximum_degradation_fraction"]),
            require_disjoint_monitor=bool(payload["require_disjoint_monitor"]),
            failure_behavior=str(payload["failure_behavior"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Replay-retention digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReplayPreparationPlan:
    mode: ReplayMode
    train_artifact: ReplayFileArtifact | None = None
    monitor_artifact: ReplayFileArtifact | None = None
    source_replay_path: str | None = None
    requested_train_count: int | None = None
    filtering_type: str = "combinations"
    subselect: str = "fps"
    seed: int = 42
    head_weight: float = 1.0
    target_weight: float = 10.0
    selection_command: tuple[str, ...] = ()
    retention_policy: ReplayRetentionPolicy = ReplayRetentionPolicy()

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", ReplayMode(self.mode))
        if self.seed < 0:
            raise TrainingDataInputError("Replay seed must be nonnegative.")
        if self.head_weight <= 0.0 or self.target_weight <= 0.0:
            raise TrainingDataInputError("Replay and target head weights must be positive.")
        if self.mode is ReplayMode.NONE:
            if self.train_artifact is not None or self.monitor_artifact is not None:
                raise TrainingDataInputError("Replay NONE cannot carry artifacts.")
        elif self.mode is ReplayMode.MP_SHORTCUT:
            if self.requested_train_count is None or self.requested_train_count <= 0:
                raise TrainingDataInputError("MP shortcut requires requested_train_count.")
            if self.monitor_artifact is None:
                raise TrainingDataInputError("MP shortcut requires an external retention monitor.")
            if self.train_artifact is not None:
                raise TrainingDataInputError("MP shortcut train data are not local yet.")
        else:
            if self.train_artifact is None or self.monitor_artifact is None:
                raise TrainingDataInputError("Local replay modes require train and monitor artifacts.")
            overlap = set(self.train_artifact.geometry_identities) & set(self.monitor_artifact.geometry_identities)
            if self.retention_policy.require_disjoint_monitor and overlap:
                raise TrainingDataInputError("Replay train and monitor sets are not disjoint.")
            if self.mode is ReplayMode.EXTERNAL_PSEUDOLABEL:
                if self.train_artifact.label_mode is not ReplayLabelMode.FOUNDATION_PSEUDOLABEL or self.monitor_artifact.label_mode is not ReplayLabelMode.FOUNDATION_PSEUDOLABEL:
                    raise TrainingDataInputError("Pseudo-label replay mode requires checkpoint-bound pseudo-label artifacts.")
                if self.train_artifact.foundation_lineage_digest != self.monitor_artifact.foundation_lineage_digest:
                    raise TrainingDataInputError("Replay train and monitor pseudo-labels use different foundation label generators.")
        object.__setattr__(self, "selection_command", tuple(str(v) for v in self.selection_command))

    @property
    def train_count(self) -> int:
        if self.train_artifact is not None:
            return self.train_artifact.configuration_count
        return int(self.requested_train_count or 0)

    @property
    def monitor_count(self) -> int:
        return 0 if self.monitor_artifact is None else self.monitor_artifact.configuration_count

    @property
    def ready_for_fixed_file_training(self) -> bool:
        return self.mode is ReplayMode.NONE or (self.train_artifact is not None and self.monitor_artifact is not None)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (REPLAY_PREPARATION_PLAN_SCHEMA if any(a is not None and a.serialization_schema == REPLAY_FILE_ARTIFACT_SCHEMA for a in (self.train_artifact, self.monitor_artifact)) else REPLAY_PREPARATION_PLAN_V3_SCHEMA),
            "mode": self.mode.value,
            "train_artifact": None if self.train_artifact is None else self.train_artifact.to_dict(),
            "monitor_artifact": None if self.monitor_artifact is None else self.monitor_artifact.to_dict(),
            "source_replay_path": self.source_replay_path,
            "requested_train_count": self.requested_train_count,
            "filtering_type": self.filtering_type,
            "subselect": self.subselect,
            "seed": self.seed,
            "head_weight": self.head_weight,
            "target_weight": self.target_weight,
            "selection_command": list(self.selection_command),
            "retention_policy": self.retention_policy.to_dict(),
            "ready_for_fixed_file_training": self.ready_for_fixed_file_training,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayPreparationPlan":
        schema = payload.get("schema")
        if schema not in {REPLAY_PREPARATION_PLAN_SCHEMA, REPLAY_PREPARATION_PLAN_V3_SCHEMA, "mdstats.replay-preparation-plan.v1"}:
            raise TrainingDataSerializationError("Unsupported replay-plan schema.")
        result = cls(
            mode=ReplayMode(payload["mode"]),
            train_artifact=None if payload.get("train_artifact") is None else ReplayFileArtifact.from_dict(payload["train_artifact"]),
            monitor_artifact=None if payload.get("monitor_artifact") is None else ReplayFileArtifact.from_dict(payload["monitor_artifact"]),
            source_replay_path=None if payload.get("source_replay_path") is None else str(payload["source_replay_path"]),
            requested_train_count=None if payload.get("requested_train_count") is None else int(payload["requested_train_count"]),
            filtering_type=str(payload["filtering_type"]),
            subselect=str(payload["subselect"]),
            seed=int(payload["seed"]),
            head_weight=float(payload["head_weight"]),
            target_weight=float(payload["target_weight"]),
            selection_command=tuple(str(v) for v in payload.get("selection_command", ())),
            retention_policy=ReplayRetentionPolicy.from_dict(payload["retention_policy"]),
        )
        if schema in {REPLAY_PREPARATION_PLAN_SCHEMA, REPLAY_PREPARATION_PLAN_V3_SCHEMA} and payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Replay-plan digest mismatch.")
        return result


def build_local_replay_plan(
    train_path: str | Path,
    monitor_path: str | Path,
    *,
    mode: ReplayMode = ReplayMode.PRESELECTED,
    seed: int = 42,
    head_weight: float = 1.0,
    target_weight: float = 10.0,
    retention_policy: ReplayRetentionPolicy | None = None,
    foundation_checkpoint_digest: str | None = None,
    foundation_label_generator_identity_digest: str | None = None,
) -> ReplayPreparationPlan:
    if mode not in {ReplayMode.PRESELECTED, ReplayMode.EXTERNAL_TRUE_LABEL, ReplayMode.EXTERNAL_PSEUDOLABEL}:
        raise TrainingDataInputError("build_local_replay_plan requires a local replay mode.")
    if mode is ReplayMode.EXTERNAL_TRUE_LABEL:
        label_mode = ReplayLabelMode.TRUE_DFT
    elif mode is ReplayMode.EXTERNAL_PSEUDOLABEL:
        label_mode = ReplayLabelMode.FOUNDATION_PSEUDOLABEL
    else:
        label_mode = ReplayLabelMode.UNSPECIFIED
    return ReplayPreparationPlan(
        mode=mode,
        train_artifact=inspect_replay_extxyz(
            train_path,
            label_mode=label_mode,
            foundation_checkpoint_digest=foundation_checkpoint_digest,
            foundation_label_generator_identity_digest=foundation_label_generator_identity_digest,
        ),
        monitor_artifact=inspect_replay_extxyz(
            monitor_path,
            label_mode=label_mode,
            foundation_checkpoint_digest=foundation_checkpoint_digest,
            foundation_label_generator_identity_digest=foundation_label_generator_identity_digest,
        ),
        seed=seed,
        head_weight=head_weight,
        target_weight=target_weight,
        retention_policy=ReplayRetentionPolicy() if retention_policy is None else retention_policy,
    )
