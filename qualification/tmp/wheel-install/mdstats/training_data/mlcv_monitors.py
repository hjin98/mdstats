"""MLCV-MON1 role-correct monitor materialization and diagnostic history.

The monitor catalog is deliberately separate from the historical ADAPT-MON1
single common online target monitor.  Fold jobs receive a lightweight subset of
that fold's nested DATA5 checkpoint-selection domain; final jobs receive a
lightweight subset of final validation D.  Replay monitoring always uses an
independent TRUE_DFT validation corpus.  Training-diagnostic monitors are
selection-inert by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import csv
import hashlib
import json
import math
import os

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .protocol import MaceJobKind
from .replay import ReplayFileArtifact, ReplayLabelMode

MLCV_MONITOR_POLICY_SCHEMA = "mdstats.mlcv-monitor-policy.v1"
MLCV_RUN_MONITOR_RECORD_SCHEMA = "mdstats.mlcv-run-monitor-record.v1"
MLCV_REPLAY_MONITOR_RECORD_SCHEMA = "mdstats.mlcv-replay-monitor-record.v1"
MLCV_MONITOR_CATALOG_SCHEMA = "mdstats.mlcv-monitor-catalog.v1"
MLCV_DIAGNOSTIC_HISTORY_SCHEMA = "mdstats.mlcv-diagnostic-history.v2"
MLCV_TRAINING_DIAGNOSTIC_PATH_ENVIRONMENT_VARIABLE = "MDSTATS_MLCV_TRAINING_DIAGNOSTIC_PATH"
MLCV_TRAINING_DIAGNOSTIC_HEAD_NAME = "target_train_diagnostic"


def _hash_fraction(seed: int, namespace: str) -> float:
    raw = hashlib.sha256(f"{int(seed)}\0{namespace}".encode("utf-8")).digest()
    integer = int.from_bytes(raw[:8], byteorder="big", signed=False)
    return (integer + 0.5) / float(1 << 64)


def _systematic_positions(count: int, selected: int, *, seed: int, namespace: str) -> tuple[int, ...]:
    if count <= 0 or selected <= 0 or selected > count:
        raise TrainingDataInputError("Invalid deterministic monitor sample request.")
    if count == selected:
        return tuple(range(count))
    start = _hash_fraction(seed, namespace)
    positions = tuple(
        min(count - 1, int(math.floor((index + start) * count / selected)))
        for index in range(selected)
    )
    if len(set(positions)) != selected:
        raise TrainingDataInputError("Deterministic monitor sampler generated duplicate positions.")
    return positions


def _balanced_quotas(capacities: Mapping[str, int], requested: int, *, seed: int, namespace: str) -> dict[str, int]:
    keys = tuple(sorted(str(key) for key in capacities))
    total = sum(int(capacities[key]) for key in keys)
    target = min(int(requested), total)
    if target <= 0:
        raise TrainingDataInputError("Monitor parent domain is empty.")
    quotas = {key: 0 for key in keys}
    order = tuple(
        sorted(
            keys,
            key=lambda key: hashlib.sha256(f"{seed}\0{namespace}\0quota\0{key}".encode()).hexdigest(),
        )
    )
    assigned = 0
    while assigned < target:
        progressed = False
        for key in order:
            if assigned >= target:
                break
            if quotas[key] < int(capacities[key]):
                quotas[key] += 1
                assigned += 1
                progressed = True
        if not progressed:  # pragma: no cover - defensive
            break
    if assigned != target:
        raise TrainingDataInputError("Could not realize deterministic balanced monitor quota.")
    return quotas


@dataclass(frozen=True, slots=True)
class MlcvMonitorPolicy:
    """Identity-bearing MLCV monitor budgets and deterministic sampling policy."""

    target_light_configurations: int = 256
    replay_light_configurations: int = 512
    training_diagnostic_configurations: int = 256
    seed: int = 161803
    target_strategy: str = "balanced_run_time_systematic"
    replay_strategy: str = "chemistry_size_systematic"
    training_diagnostic_strategy: str = "balanced_run_time_systematic"

    def __post_init__(self) -> None:
        if min(
            int(self.target_light_configurations),
            int(self.replay_light_configurations),
            int(self.training_diagnostic_configurations),
        ) <= 0:
            raise TrainingDataInputError("MLCV monitor budgets must be positive.")
        if int(self.seed) < 0:
            raise TrainingDataInputError("MLCV monitor seed must be nonnegative.")
        if self.target_strategy != "balanced_run_time_systematic":
            raise TrainingDataInputError("Unsupported MLCV target-light monitor strategy.")
        if self.replay_strategy != "chemistry_size_systematic":
            raise TrainingDataInputError("Unsupported MLCV replay-light monitor strategy.")
        if self.training_diagnostic_strategy != "balanced_run_time_systematic":
            raise TrainingDataInputError("Unsupported MLCV training-diagnostic strategy.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_MONITOR_POLICY_SCHEMA,
            "target_light_configurations": int(self.target_light_configurations),
            "replay_light_configurations": int(self.replay_light_configurations),
            "training_diagnostic_configurations": int(self.training_diagnostic_configurations),
            "seed": int(self.seed),
            "target_strategy": self.target_strategy,
            "replay_strategy": self.replay_strategy,
            "training_diagnostic_strategy": self.training_diagnostic_strategy,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvMonitorPolicy":
        if payload.get("schema") != MLCV_MONITOR_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV monitor-policy schema.")
        result = cls(
            target_light_configurations=int(payload["target_light_configurations"]),
            replay_light_configurations=int(payload["replay_light_configurations"]),
            training_diagnostic_configurations=int(payload["training_diagnostic_configurations"]),
            seed=int(payload["seed"]),
            target_strategy=str(payload["target_strategy"]),
            replay_strategy=str(payload["replay_strategy"]),
            training_diagnostic_strategy=str(payload["training_diagnostic_strategy"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MLCV monitor-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvRunMonitorRecord:
    """Exact target monitor membership for one fold/final training run."""

    job_id: str
    kind: MaceJobKind
    fold_index: int | None
    target_statistical_role: str
    target_full_parent_digest: str
    target_full_frame_uids: tuple[str, ...]
    target_light_frame_uids: tuple[str, ...]
    training_parent_digest: str
    training_frame_uids: tuple[str, ...]
    training_diagnostic_frame_uids: tuple[str, ...]
    policy_digest: str
    fallback_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", MaceJobKind(self.kind))
        if not self.job_id.strip() or not self.target_statistical_role.strip():
            raise TrainingDataInputError("MLCV run-monitor identifiers must be non-empty.")
        if self.kind is MaceJobKind.FINAL_DEVELOPMENT and self.fold_index is not None:
            raise TrainingDataInputError("Final-development monitor cannot carry a fold index.")
        if self.kind is MaceJobKind.CROSS_VALIDATION_FOLD and self.fold_index is None:
            raise TrainingDataInputError("Fold monitor requires a fold index.")
        for name in ("target_full_parent_digest", "training_parent_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "target_full_frame_uids", "target_light_frame_uids",
            "training_frame_uids", "training_diagnostic_frame_uids",
        ):
            values = tuple(validate_digest(str(v), name="frame_uid") for v in getattr(self, name))
            if not values or len(set(values)) != len(values):
                raise TrainingDataInputError(f"MLCV {name} must contain unique non-empty membership.")
            object.__setattr__(self, name, values)
        if not set(self.target_light_frame_uids).issubset(self.target_full_frame_uids):
            raise TrainingDataInputError("MLCV target-light membership must be contained in target-full.")
        if not set(self.training_diagnostic_frame_uids).issubset(self.training_frame_uids):
            raise TrainingDataInputError("MLCV training diagnostic membership must be contained in gradient training.")
        if set(self.target_full_frame_uids) & set(self.training_frame_uids):
            raise TrainingDataInputError("MLCV target checkpoint-selection and gradient-training frames overlap.")
        object.__setattr__(self, "fallback_reason_codes", tuple(sorted(set(str(v) for v in self.fallback_reason_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_RUN_MONITOR_RECORD_SCHEMA,
            "job_id": self.job_id,
            "kind": self.kind.value,
            "fold_index": self.fold_index,
            "target_statistical_role": self.target_statistical_role,
            "target_full_parent_digest": self.target_full_parent_digest,
            "target_full_frame_uids": list(self.target_full_frame_uids),
            "target_light_frame_uids": list(self.target_light_frame_uids),
            "training_parent_digest": self.training_parent_digest,
            "training_frame_uids": list(self.training_frame_uids),
            "training_diagnostic_frame_uids": list(self.training_diagnostic_frame_uids),
            "policy_digest": self.policy_digest,
            "fallback_reason_codes": list(self.fallback_reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvRunMonitorRecord":
        if payload.get("schema") != MLCV_RUN_MONITOR_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV run-monitor schema.")
        result = cls(
            job_id=str(payload["job_id"]), kind=MaceJobKind(str(payload["kind"])),
            fold_index=None if payload.get("fold_index") is None else int(payload["fold_index"]),
            target_statistical_role=str(payload["target_statistical_role"]),
            target_full_parent_digest=str(payload["target_full_parent_digest"]),
            target_full_frame_uids=tuple(str(v) for v in payload["target_full_frame_uids"]),
            target_light_frame_uids=tuple(str(v) for v in payload["target_light_frame_uids"]),
            training_parent_digest=str(payload["training_parent_digest"]),
            training_frame_uids=tuple(str(v) for v in payload["training_frame_uids"]),
            training_diagnostic_frame_uids=tuple(str(v) for v in payload["training_diagnostic_frame_uids"]),
            policy_digest=str(payload["policy_digest"]),
            fallback_reason_codes=tuple(str(v) for v in payload.get("fallback_reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV run-monitor digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvReplayMonitorRecord:
    """Exact TRUE_DFT full/light replay validation lineage."""

    full_artifact_digest: str
    full_geometry_identities: tuple[str, ...]
    light_geometry_identities: tuple[str, ...]
    light_source_indices: tuple[int, ...]
    policy_digest: str
    fallback_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("full_artifact_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        full = tuple(validate_digest(str(v), name="geometry_identity") for v in self.full_geometry_identities)
        light = tuple(validate_digest(str(v), name="geometry_identity") for v in self.light_geometry_identities)
        indices = tuple(int(v) for v in self.light_source_indices)
        if not full or len(set(full)) != len(full):
            raise TrainingDataInputError("MLCV replay full validation membership is invalid.")
        if not light or len(light) != len(indices) or len(set(light)) != len(light):
            raise TrainingDataInputError("MLCV replay-light membership is invalid.")
        if not set(light).issubset(full):
            raise TrainingDataInputError("MLCV replay-light membership must be contained in replay-full.")
        if any(v < 0 or v >= len(full) for v in indices) or len(set(indices)) != len(indices):
            raise TrainingDataInputError("MLCV replay-light source indices are invalid.")
        object.__setattr__(self, "full_geometry_identities", full)
        object.__setattr__(self, "light_geometry_identities", light)
        object.__setattr__(self, "light_source_indices", indices)
        object.__setattr__(self, "fallback_reason_codes", tuple(sorted(set(str(v) for v in self.fallback_reason_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_REPLAY_MONITOR_RECORD_SCHEMA,
            "full_artifact_digest": self.full_artifact_digest,
            "full_geometry_identities": list(self.full_geometry_identities),
            "light_geometry_identities": list(self.light_geometry_identities),
            "light_source_indices": list(self.light_source_indices),
            "policy_digest": self.policy_digest,
            "fallback_reason_codes": list(self.fallback_reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvReplayMonitorRecord":
        if payload.get("schema") != MLCV_REPLAY_MONITOR_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV replay-monitor schema.")
        result = cls(
            full_artifact_digest=str(payload["full_artifact_digest"]),
            full_geometry_identities=tuple(str(v) for v in payload["full_geometry_identities"]),
            light_geometry_identities=tuple(str(v) for v in payload["light_geometry_identities"]),
            light_source_indices=tuple(int(v) for v in payload["light_source_indices"]),
            policy_digest=str(payload["policy_digest"]),
            fallback_reason_codes=tuple(str(v) for v in payload.get("fallback_reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV replay-monitor digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvMonitorCatalog:
    """Restart-stable MLCV monitor memberships for one DATA8 realization."""

    role_catalog_digest: str
    policy: MlcvMonitorPolicy
    runs: tuple[MlcvRunMonitorRecord, ...]
    replay: MlcvReplayMonitorRecord

    def __post_init__(self) -> None:
        object.__setattr__(self, "role_catalog_digest", validate_digest(self.role_catalog_digest, name="role_catalog_digest"))
        runs = tuple(sorted(self.runs, key=lambda item: (item.kind.value, -1 if item.fold_index is None else item.fold_index, item.job_id)))
        if not runs or len({item.job_id for item in runs}) != len(runs):
            raise TrainingDataInputError("MLCV monitor catalog requires unique run records.")
        if any(item.policy_digest != self.policy.policy_digest for item in runs):
            raise TrainingDataInputError("MLCV run-monitor/policy mismatch.")
        if self.replay.policy_digest != self.policy.policy_digest:
            raise TrainingDataInputError("MLCV replay-monitor/policy mismatch.")
        object.__setattr__(self, "runs", runs)

    def run(self, job_id: str) -> MlcvRunMonitorRecord:
        matches = [item for item in self.runs if item.job_id == job_id]
        if len(matches) != 1:
            raise TrainingDataInputError(f"MLCV monitor catalog does not contain unique job {job_id!r}.")
        return matches[0]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_MONITOR_CATALOG_SCHEMA,
            "role_catalog_digest": self.role_catalog_digest,
            "policy": self.policy.to_dict(),
            "runs": [item.to_dict() for item in self.runs],
            "replay": self.replay.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvMonitorCatalog":
        if payload.get("schema") != MLCV_MONITOR_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV monitor-catalog schema.")
        result = cls(
            role_catalog_digest=str(payload["role_catalog_digest"]),
            policy=MlcvMonitorPolicy.from_dict(payload["policy"]),
            runs=tuple(MlcvRunMonitorRecord.from_dict(v) for v in payload["runs"]),
            replay=MlcvReplayMonitorRecord.from_dict(payload["replay"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV monitor-catalog digest mismatch.")
        return result


def sample_target_frames(
    frame_uids: Sequence[str], frame_catalog: Any, *, requested: int, seed: int, namespace: str
) -> tuple[str, ...]:
    """Run-balanced, chronology-spread deterministic subset of explicit parent frames."""

    unique = tuple(dict.fromkeys(str(v) for v in frame_uids))
    if not unique:
        raise TrainingDataInputError("MLCV target monitor parent is empty.")
    groups: dict[str, list[Any]] = {}
    for uid in unique:
        record = frame_catalog.frame(uid)
        groups.setdefault(record.run_id, []).append(record)
    for values in groups.values():
        values.sort(key=lambda item: (item.source_frame_index, item.frame_uid))
    quotas = _balanced_quotas(
        {key: len(values) for key, values in groups.items()}, requested,
        seed=seed, namespace=namespace,
    )
    chosen: list[Any] = []
    for key in sorted(groups):
        values = groups[key]
        quota = quotas[key]
        if quota:
            positions = _systematic_positions(
                len(values), quota, seed=seed, namespace=f"{namespace}:{key}"
            )
            chosen.extend(values[position] for position in positions)
    chosen.sort(key=lambda item: (item.run_id, item.source_frame_index, item.frame_uid))
    return tuple(item.frame_uid for item in chosen)


def build_run_monitor_record(
    *, job_id: str, kind: MaceJobKind, fold_index: int | None,
    target_statistical_role: str, target_full_frame_uids: Sequence[str],
    training_frame_uids: Sequence[str], frame_catalog: Any, policy: MlcvMonitorPolicy,
    target_full_parent_digest: str, training_parent_digest: str,
) -> MlcvRunMonitorRecord:
    full = tuple(dict.fromkeys(str(v) for v in target_full_frame_uids))
    train = tuple(dict.fromkeys(str(v) for v in training_frame_uids))
    light = sample_target_frames(
        full, frame_catalog, requested=min(policy.target_light_configurations, len(full)),
        seed=policy.seed, namespace=f"target-light:{job_id}",
    )
    diagnostic = sample_target_frames(
        train, frame_catalog, requested=min(policy.training_diagnostic_configurations, len(train)),
        seed=policy.seed, namespace=f"training-diagnostic:{job_id}",
    )
    fallback: list[str] = []
    if len(full) < policy.target_light_configurations:
        fallback.append("target_light_parent_smaller_than_requested")
    if len(train) < policy.training_diagnostic_configurations:
        fallback.append("training_diagnostic_parent_smaller_than_requested")
    return MlcvRunMonitorRecord(
        job_id=job_id, kind=kind, fold_index=fold_index,
        target_statistical_role=target_statistical_role,
        target_full_parent_digest=target_full_parent_digest,
        target_full_frame_uids=full, target_light_frame_uids=light,
        training_parent_digest=training_parent_digest, training_frame_uids=train,
        training_diagnostic_frame_uids=diagnostic,
        policy_digest=policy.policy_digest, fallback_reason_codes=tuple(fallback),
    )


def build_replay_monitor_record(source: ReplayFileArtifact, policy: MlcvMonitorPolicy) -> MlcvReplayMonitorRecord:
    """Choose R_light deterministically from the complete TRUE_DFT R_full artifact."""

    if source.label_mode is not ReplayLabelMode.TRUE_DFT:
        raise TrainingDataInputError("MLCV replay-full validation must carry TRUE_DFT labels.")
    try:
        from ase.io import iread
        import numpy as np
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE and NumPy are required to construct MLCV replay monitors.") from exc
    rows: list[tuple[Any, int, str]] = []
    for index, atoms in enumerate(iread(source.path, index=":", format="extxyz")):
        numbers = tuple(sorted(int(v) for v in atoms.numbers))
        unique, counts = np.unique(np.asarray(numbers, dtype=np.int32), return_counts=True)
        composition = tuple((int(z), int(c)) for z, c in zip(unique, counts, strict=True))
        atom_count = len(numbers)
        size_bucket = 0 if atom_count <= 1 else int(math.floor(math.log2(atom_count)))
        identity = source.geometry_identities[index]
        rows.append(((composition, size_bucket, atom_count, index, identity), index, identity))
    if len(rows) != source.configuration_count:
        raise TrainingDataInputError("MLCV replay-full source count changed during inspection.")
    rows.sort(key=lambda row: row[0])
    realized = min(policy.replay_light_configurations, len(rows))
    positions = _systematic_positions(len(rows), realized, seed=policy.seed, namespace="mlcv-replay-light")
    selected = [rows[position] for position in positions]
    selected.sort(key=lambda row: row[1])
    fallback = () if len(rows) >= policy.replay_light_configurations else ("replay_light_parent_smaller_than_requested",)
    return MlcvReplayMonitorRecord(
        full_artifact_digest=source.content_digest,
        full_geometry_identities=tuple(source.geometry_identities),
        light_geometry_identities=tuple(row[2] for row in selected),
        light_source_indices=tuple(row[1] for row in selected),
        policy_digest=policy.policy_digest,
        fallback_reason_codes=fallback,
    )


def write_replay_light_subset(source: ReplayFileArtifact, record: MlcvReplayMonitorRecord, output_path: str | Path) -> ReplayFileArtifact:
    if source.content_digest != record.full_artifact_digest:
        raise TrainingDataInputError("MLCV replay-light source/record lineage mismatch.")
    try:
        from ase.io import iread
        from .mace_export import _write_extxyz_high_precision
        from .replay import inspect_replay_extxyz
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to materialize MLCV replay-light validation.") from exc
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    chosen = set(record.light_source_indices)
    temp = target.with_suffix(target.suffix + ".tmp")
    def stream():
        emitted = 0
        for index, atoms in enumerate(iread(source.path, index=":", format="extxyz")):
            if index in chosen:
                emitted += 1
                yield atoms
        if emitted != len(record.light_source_indices):
            raise TrainingDataInputError("MLCV replay-light materialization emitted the wrong count.")
    try:
        with temp.open("w", encoding="utf-8", newline="") as handle:
            _write_extxyz_high_precision(handle, stream())
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, target)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    artifact = inspect_replay_extxyz(target, label_mode=ReplayLabelMode.TRUE_DFT)
    if artifact.geometry_identities != record.light_geometry_identities:
        raise TrainingDataInputError("MLCV replay-light materialized membership changed.")
    return artifact


def _read_jsonl_metrics(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows



def prepare_training_diagnostic_validation_loader(
    model: Any, valid_loaders: Mapping[str, Any]
) -> dict[str, Any]:
    """Prepend the selection-inert MLCV target-training diagnostic loader.

    The diagnostic configurations are encoded through the ordinary target head
    but logged under a distinct loader name.  They are prepended so MACE 0.3.16
    continues to use the final ordinary target-validation loader for its native
    checkpoint/patience scalar.  The loader is activated only when the campaign
    supplies ``MDSTATS_MLCV_TRAINING_DIAGNOSTIC_PATH``.
    """

    raw_path = os.environ.get(MLCV_TRAINING_DIAGNOSTIC_PATH_ENVIRONMENT_VARIABLE)
    if not raw_path:
        return dict(valid_loaders)
    if MLCV_TRAINING_DIAGNOSTIC_HEAD_NAME in valid_loaders:
        return dict(valid_loaders)
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"MLCV-MON1 training diagnostic monitor is missing: {path}")
    if not valid_loaders:
        raise RuntimeError("MLCV-MON1 cannot infer validation batching without a target loader.")

    try:
        from mace import data as mace_data
        from mace.data import KeySpecification
        from mace.tools import AtomicNumberTable, torch_geometric
    except Exception as exc:  # pragma: no cover - production dependency guard
        raise RuntimeError(
            "MLCV-MON1 could not import MACE data utilities for training-diagnostic validation."
        ) from exc

    heads = [str(value) for value in getattr(model, "heads", ["target_head"])]
    # Prefer the canonical target head, then MACE's one-head Default, then the
    # sole non-replay head.  Ambiguous multi-head models fail closed.
    if "target_head" in heads:
        target_head = "target_head"
    elif "Default" in heads:
        target_head = "Default"
    else:
        non_replay = [head for head in heads if head not in {"pt_head", "replay_head"}]
        if len(non_replay) != 1:
            raise RuntimeError(
                "MLCV-MON1 could not identify one target head for the training diagnostic: "
                f"model heads={heads!r}."
            )
        target_head = non_replay[0]

    keys = KeySpecification.from_defaults()
    keys.update(
        info_keys={"energy": "REF_energy", "stress": "REF_stress"},
        arrays_keys={"forces": "REF_forces"},
    )
    _, configurations = mace_data.load_from_xyz(
        str(path),
        key_specification=keys,
        head_name=target_head,
        keep_isolated_atoms=True,
        no_data_ok=False,
    )
    atomic_numbers = getattr(model, "atomic_numbers", None)
    if atomic_numbers is None:
        raise RuntimeError(
            "MLCV-MON1 model does not expose atomic_numbers for training-diagnostic validation."
        )
    if hasattr(atomic_numbers, "detach"):
        atomic_numbers = atomic_numbers.detach().cpu().tolist()
    z_table = AtomicNumberTable([int(value) for value in atomic_numbers])
    cutoff = float(getattr(model, "r_max"))
    dataset = [
        mace_data.AtomicData.from_config(config, z_table=z_table, cutoff=cutoff, heads=heads)
        for config in configurations
    ]
    if not dataset:
        raise RuntimeError("MLCV-MON1 training diagnostic monitor is empty.")
    reference_loader = next(iter(valid_loaders.values()))
    batch_size = int(getattr(reference_loader, "batch_size", 1) or 1)
    diagnostic_loader = torch_geometric.dataloader.DataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=False,
        drop_last=False,
        pin_memory=bool(getattr(reference_loader, "pin_memory", False)),
        num_workers=int(getattr(reference_loader, "num_workers", 0) or 0),
    )
    return {MLCV_TRAINING_DIAGNOSTIC_HEAD_NAME: diagnostic_loader, **dict(valid_loaders)}


def write_mlcv_diagnostic_history(
    log_path: str | Path,
    output_directory: str | Path,
    *,
    target_head_name: str = "target_head",
    replay_head_name: str = "pt_head",
    full_target_threshold: float = 0.030,
    replay_degradation_budget: float = 0.030,
    replay_foundation_light_rmse: float | None = None,
    target_success_fraction: float = 0.80,
    replay_exhaustion_factor: float = 1.20,
    stop_epoch: int | None = None,
    stop_reason: str | None = None,
    # Historical keyword alias. For current evidence this is a degradation
    # budget, never an absolute replay threshold.
    full_replay_threshold: float | None = None,
) -> dict[str, Any]:
    """Render zero-inference MLCV diagnostics with explicit replay semantics."""
    if full_replay_threshold is not None:
        replay_degradation_budget = float(full_replay_threshold)
    rows = _read_jsonl_metrics(Path(log_path))
    epochs = sorted({int(v["epoch"]) for v in rows if v.get("epoch") is not None and str(v.get("epoch")).lstrip("-").isdigit()})
    history: list[dict[str, Any]] = []
    replay_aliases = {replay_head_name, "pt_head", "replay_head"}
    for epoch in epochs:
        opt_losses: list[float] = []
        target = None
        replay = None
        training_diagnostic = None
        for item in rows:
            if item.get("epoch") != epoch:
                continue
            if item.get("mode") == "opt":
                try:
                    value = float(item.get("loss"))
                except (TypeError, ValueError):
                    value = math.nan
                if math.isfinite(value):
                    opt_losses.append(value)
            elif item.get("mode") == "eval":
                try:
                    value = float(item.get("rmse_f"))
                except (TypeError, ValueError):
                    continue
                if not math.isfinite(value):
                    continue
                head = str(item.get("head", "Default"))
                if head == MLCV_TRAINING_DIAGNOSTIC_HEAD_NAME:
                    training_diagnostic = value
                elif head in replay_aliases:
                    replay = value
                elif head in {target_head_name, "target_head", "Default"} or target is None:
                    target = value
        degradation = None if replay is None or replay_foundation_light_rmse is None else replay - float(replay_foundation_light_rmse)
        history.append({
            "epoch": epoch,
            "train_objective_loss": None if not opt_losses else sum(opt_losses) / len(opt_losses),
            "train_target_diagnostic_force_rmse": training_diagnostic,
            "checkpoint_target_force_rmse": target,
            "checkpoint_replay_force_rmse": replay,
            "checkpoint_replay_absolute_force_rmse": replay,
            "replay_light_foundation_force_rmse": replay_foundation_light_rmse,
            "checkpoint_replay_degradation_force_rmse": degradation,
        })
    budget = float(replay_degradation_budget)
    target_full = float(full_target_threshold)
    thresholds = {
        "target_success_stop": float(target_success_fraction) * target_full,
        "target_full_acceptance": target_full,
        "replay_degradation_budget": budget,
        "replay_degradation_exhaustion_stop": float(replay_exhaustion_factor) * budget,
        "replay_foundation_light_rmse": replay_foundation_light_rmse,
        "replay_light_absolute_acceptance_ceiling": None if replay_foundation_light_rmse is None else float(replay_foundation_light_rmse) + budget,
        "replay_light_absolute_exhaustion_ceiling": None if replay_foundation_light_rmse is None else float(replay_foundation_light_rmse) + float(replay_exhaustion_factor) * budget,
        # Compatibility aliases carry the corrected degradation-space values.
        "full_target_acceptance_reference": target_full,
        "full_replay_acceptance_reference": budget,
        "replay_exhaustion_stop": float(replay_exhaustion_factor) * budget,
    }
    payload = {
        "schema": MLCV_DIAGNOSTIC_HISTORY_SCHEMA,
        "source_log": str(Path(log_path)),
        "metrics": history,
        "thresholds": thresholds,
        "stop_epoch": stop_epoch,
        "stop_reason": stop_reason,
        "reporting_inference_count": 0,
        "replay_semantics": "foundation_relative_degradation",
        "note": "Target RMSE is absolute. Replay absolute RMSE is diagnostic; replay degradation relative to R0_light controls stopping/ranking.",
    }
    payload["content_digest"] = digest({k: v for k, v in payload.items() if k != "content_digest"})
    out = Path(output_directory)
    out.mkdir(parents=True, exist_ok=True)
    (out / "training_history.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csv_path = out / "training_history.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            "epoch", "train_objective_loss", "train_target_diagnostic_force_rmse",
            "checkpoint_target_force_rmse", "checkpoint_replay_absolute_force_rmse",
            "replay_light_foundation_force_rmse", "checkpoint_replay_degradation_force_rmse",
        ))
        writer.writeheader()
        writer.writerows([{k: row.get(k) for k in writer.fieldnames} for row in history])
    png_path = out / "validation_history.png"
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        xs = [item["epoch"] for item in history]
        fig, ax = plt.subplots(figsize=(9.0, 5.5))
        target_values = [item["checkpoint_target_force_rmse"] for item in history]
        replay_values = [item["checkpoint_replay_absolute_force_rmse"] for item in history]
        diagnostic_values = [item["train_target_diagnostic_force_rmse"] for item in history]
        if any(v is not None for v in diagnostic_values):
            ax.plot(xs, [math.nan if v is None else 1e3 * v for v in diagnostic_values], marker="o", label="target training diagnostic")
        if any(v is not None for v in target_values):
            ax.plot(xs, [math.nan if v is None else 1e3 * v for v in target_values], marker="o", label="target lightweight validation")
        if any(v is not None for v in replay_values):
            ax.plot(xs, [math.nan if v is None else 1e3 * v for v in replay_values], marker="o", label="replay absolute RMSE")
        ax.axhline(1e3 * thresholds["target_success_stop"], linestyle="--", label=f"target {100.0*float(target_success_fraction):g}% stop")
        ax.axhline(1e3 * thresholds["target_full_acceptance"], linestyle=":", label="target full threshold")
        if replay_foundation_light_rmse is not None:
            ax.axhline(1e3 * float(replay_foundation_light_rmse), linestyle="-.", label="foundation R0_light")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Absolute force RMSE (meV/Å)")
        ax2 = ax.twinx()
        degradation_values = [item["checkpoint_replay_degradation_force_rmse"] for item in history]
        if any(v is not None for v in degradation_values):
            ax2.plot(xs, [math.nan if v is None else 1e3 * v for v in degradation_values], marker="s", label="replay degradation R-R0")
        ax2.axhline(1e3 * budget, linestyle=":", label="replay degradation budget")
        ax2.axhline(1e3 * thresholds["replay_degradation_exhaustion_stop"], linestyle="--", label=f"replay {100.0*float(replay_exhaustion_factor):g}% exhaustion")
        ax2.set_ylabel("Replay degradation (meV/Å)")
        if stop_epoch is not None:
            ax.axvline(int(stop_epoch), linestyle="-.", label=f"adaptive stop: {stop_reason or 'unspecified'}")
        ax.set_title("MLCV lightweight validation: absolute quality and foundation-relative retention")
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize="small")
        fig.tight_layout()
        temp = png_path.with_suffix(".png.tmp")
        fig.savefig(temp, dpi=140, format="png")
        plt.close(fig)
        os.replace(temp, png_path)
    except Exception as exc:  # pragma: no cover
        raise TrainingDataInputError(f"Could not render MLCV diagnostic PNG: {type(exc).__name__}: {exc}") from exc
    return payload
