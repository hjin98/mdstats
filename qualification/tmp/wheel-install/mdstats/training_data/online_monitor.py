"""ADAPT-MON1 fixed-budget online monitor construction and identity."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import math
import os

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .mace_export import _write_extxyz_high_precision
from .partition import OuterRole
from .replay import ReplayFileArtifact, ReplayLabelMode, inspect_replay_extxyz

ONLINE_MONITOR_POLICY_SCHEMA = "mdstats.online-monitor-policy.v2"
ONLINE_MONITOR_POLICY_V1_SCHEMA = "mdstats.online-monitor-policy.v1"
ONLINE_MONITOR_RECORD_SCHEMA = "mdstats.online-monitor-record.v1"


@dataclass(frozen=True, slots=True)
class OnlineMonitorPolicy:
    """Identity-bearing fixed-budget monitor policy for adaptive campaigns."""

    target_configurations: int = 256
    replay_configurations: int = 512
    training_diagnostic_configurations: int = 256
    seed: int = 161803
    target_strategy: str = "balanced_condition_run_time_systematic"
    replay_strategy: str = "chemistry_size_systematic"

    def __post_init__(self) -> None:
        if self.target_configurations <= 0 or self.replay_configurations <= 0 or self.training_diagnostic_configurations <= 0:
            raise TrainingDataInputError("Online/MLCV monitor sizes must be positive.")
        if self.seed < 0:
            raise TrainingDataInputError("Online monitor seed must be nonnegative.")
        if self.target_strategy != "balanced_condition_run_time_systematic":
            raise TrainingDataInputError("Unsupported target online-monitor strategy.")
        if self.replay_strategy != "chemistry_size_systematic":
            raise TrainingDataInputError("Unsupported replay online-monitor strategy.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ONLINE_MONITOR_POLICY_SCHEMA,
            "target_configurations": self.target_configurations,
            "replay_configurations": self.replay_configurations,
            "training_diagnostic_configurations": self.training_diagnostic_configurations,
            "seed": self.seed,
            "target_strategy": self.target_strategy,
            "replay_strategy": self.replay_strategy,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OnlineMonitorPolicy":
        if payload.get("schema") not in {ONLINE_MONITOR_POLICY_SCHEMA, ONLINE_MONITOR_POLICY_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported online-monitor policy schema.")
        result = cls(
            target_configurations=int(payload["target_configurations"]),
            replay_configurations=int(payload["replay_configurations"]),
            training_diagnostic_configurations=int(payload.get("training_diagnostic_configurations", 256)),
            seed=int(payload["seed"]),
            target_strategy=str(payload["target_strategy"]),
            replay_strategy=str(payload["replay_strategy"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Online-monitor policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class OnlineMonitorRecord:
    """Exact selected membership and parent-lineage evidence for one monitor."""

    role: str
    parent_digest: str
    policy_digest: str
    requested_size: int
    realized_size: int
    selected_identities: tuple[str, ...]
    source_indices: tuple[int, ...]
    stratum_counts: tuple[tuple[str, int, int], ...]
    strategy: str
    seed: int
    label_mode: str
    parent_role: str
    fallback_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.role not in {"target", "replay"}:
            raise TrainingDataInputError("Online monitor role must be target or replay.")
        for name in ("parent_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.requested_size <= 0 or self.realized_size <= 0:
            raise TrainingDataInputError("Online monitor sizes must be positive.")
        identities = tuple(str(v) for v in self.selected_identities)
        indices = tuple(int(v) for v in self.source_indices)
        if len(identities) != self.realized_size or len(indices) != self.realized_size:
            raise TrainingDataInputError("Online monitor membership/count evidence is inconsistent.")
        if len(set(identities)) != len(identities):
            raise TrainingDataInputError("Online monitor memberships must be unique.")
        if self.role == "replay" and len(set(indices)) != len(indices):
            raise TrainingDataInputError("Replay online-monitor source indices must be unique.")
        if any(v < 0 for v in indices):
            raise TrainingDataInputError("Online monitor source indices must be nonnegative.")
        counts = tuple((str(key), int(available), int(selected)) for key, available, selected in self.stratum_counts)
        if any(available <= 0 or selected < 0 or selected > available for _, available, selected in counts):
            raise TrainingDataInputError("Online monitor stratum counts are invalid.")
        if sum(selected for _, _, selected in counts) != self.realized_size:
            raise TrainingDataInputError("Online monitor stratum counts do not sum to realized size.")
        object.__setattr__(self, "selected_identities", identities)
        object.__setattr__(self, "source_indices", indices)
        object.__setattr__(self, "stratum_counts", counts)
        object.__setattr__(self, "fallback_reason_codes", tuple(sorted(set(str(v) for v in self.fallback_reason_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ONLINE_MONITOR_RECORD_SCHEMA,
            "role": self.role,
            "parent_digest": self.parent_digest,
            "policy_digest": self.policy_digest,
            "requested_size": self.requested_size,
            "realized_size": self.realized_size,
            "selected_identities": list(self.selected_identities),
            "source_indices": list(self.source_indices),
            "stratum_counts": [list(v) for v in self.stratum_counts],
            "strategy": self.strategy,
            "seed": self.seed,
            "label_mode": self.label_mode,
            "parent_role": self.parent_role,
            "fallback_reason_codes": list(self.fallback_reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OnlineMonitorRecord":
        if payload.get("schema") != ONLINE_MONITOR_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported online-monitor record schema.")
        result = cls(
            role=str(payload["role"]),
            parent_digest=str(payload["parent_digest"]),
            policy_digest=str(payload["policy_digest"]),
            requested_size=int(payload["requested_size"]),
            realized_size=int(payload["realized_size"]),
            selected_identities=tuple(str(v) for v in payload["selected_identities"]),
            source_indices=tuple(int(v) for v in payload["source_indices"]),
            stratum_counts=tuple((str(v[0]), int(v[1]), int(v[2])) for v in payload["stratum_counts"]),
            strategy=str(payload["strategy"]),
            seed=int(payload["seed"]),
            label_mode=str(payload["label_mode"]),
            parent_role=str(payload["parent_role"]),
            fallback_reason_codes=tuple(str(v) for v in payload.get("fallback_reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Online-monitor record digest mismatch.")
        return result


def _hash_fraction(seed: int, namespace: str) -> float:
    raw = hashlib.sha256(f"{int(seed)}\0{namespace}".encode("utf-8")).digest()
    integer = int.from_bytes(raw[:8], byteorder="big", signed=False)
    return (integer + 0.5) / float(1 << 64)


def _systematic_positions(count: int, selected: int, *, seed: int, namespace: str) -> tuple[int, ...]:
    if selected <= 0 or count <= 0 or selected > count:
        raise TrainingDataInputError("Invalid systematic online-monitor sample request.")
    if selected == count:
        return tuple(range(count))
    start = _hash_fraction(seed, namespace)
    positions = tuple(
        min(count - 1, int(math.floor((index + start) * count / selected)))
        for index in range(selected)
    )
    if len(set(positions)) != selected:
        raise TrainingDataInputError("Systematic monitor sampler generated duplicate positions.")
    return positions


def _balanced_quotas(capacities: Mapping[str, int], requested: int, *, seed: int) -> dict[str, int]:
    keys = tuple(sorted(capacities))
    total = sum(int(capacities[key]) for key in keys)
    target = min(int(requested), total)
    quotas = {key: 0 for key in keys}
    # Rotate each equal-allocation pass deterministically so remainder frames do
    # not always favor lexicographically early conditions.
    order = tuple(sorted(keys, key=lambda key: hashlib.sha256(f"{seed}\0quota\0{key}".encode()).hexdigest()))
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
        raise TrainingDataInputError("Could not realize requested balanced monitor quota.")
    return quotas


def build_target_online_monitor(
    data5_bundle: Any,
    frame_catalog: Any,
    label_domain_id: str,
    policy: OnlineMonitorPolicy,
) -> OnlineMonitorRecord:
    """Select a common condition/run-balanced, time-spread target monitor."""

    outer = data5_bundle.outer_partition_for_domain(label_domain_id)
    unit_ids = tuple(outer.units_for(OuterRole.OUTER_MONITOR))
    if not unit_ids:
        raise TrainingDataInputError("ADAPT-MON1 target monitor requires DATA5 outer-monitor units.")

    strata: dict[str, list[Any]] = {}
    for unit_id in unit_ids:
        unit = data5_bundle.unit_catalog.unit(unit_id)
        key = f"{unit.condition.condition_id}:{unit.run_id}"
        group = strata.setdefault(key, [])
        group.extend(frame_catalog.frame(uid) for uid in unit.frame_uids)
    for values in strata.values():
        values.sort(key=lambda record: (record.source_frame_index, record.frame_uid))

    quotas = _balanced_quotas(
        {key: len(values) for key, values in strata.items()},
        policy.target_configurations,
        seed=policy.seed,
    )
    selected_records: list[Any] = []
    stratum_counts: list[tuple[str, int, int]] = []
    for key in sorted(strata):
        values = strata[key]
        quota = quotas[key]
        if quota:
            positions = _systematic_positions(
                len(values), quota, seed=policy.seed, namespace=f"target:{key}"
            )
            selected_records.extend(values[position] for position in positions)
        stratum_counts.append((key, len(values), quota))

    # Stable evidence/file order by physical source chronology, after balanced
    # membership has already been decided.
    selected_records.sort(key=lambda record: (record.run_id, record.source_frame_index, record.frame_uid))
    available = sum(len(values) for values in strata.values())
    fallback = () if available >= policy.target_configurations else ("target_parent_smaller_than_requested",)
    parent_digest = digest({
        "schema": "mdstats.online-target-parent.v1",
        "data5_bundle_digest": data5_bundle.content_digest,
        "outer_partition_digest": outer.content_digest,
        "label_domain_id": label_domain_id,
        "outer_monitor_unit_ids": list(sorted(unit_ids)),
    })
    return OnlineMonitorRecord(
        role="target",
        parent_digest=parent_digest,
        policy_digest=policy.policy_digest,
        requested_size=policy.target_configurations,
        realized_size=len(selected_records),
        selected_identities=tuple(record.frame_uid for record in selected_records),
        source_indices=tuple(record.source_frame_index for record in selected_records),
        stratum_counts=tuple(stratum_counts),
        strategy=policy.target_strategy,
        seed=policy.seed,
        label_mode="true_dft",
        parent_role="data5_outer_monitor",
        fallback_reason_codes=fallback,
    )


def _replay_sort_key(atoms: Any, source_index: int, geometry_identity: str) -> tuple[Any, ...]:
    numbers = tuple(sorted(int(v) for v in atoms.numbers))
    unique, counts = np.unique(np.asarray(numbers, dtype=np.int32), return_counts=True)
    composition = tuple((int(z), int(c)) for z, c in zip(unique, counts, strict=True))
    atom_count = len(numbers)
    # Log2 bins retain size coverage without letting a few very large structures
    # dominate the sort key.
    size_bucket = 0 if atom_count <= 1 else int(math.floor(math.log2(atom_count)))
    return (composition, size_bucket, atom_count, int(source_index), geometry_identity)


def build_replay_online_monitor(
    source_artifact: ReplayFileArtifact,
    policy: OnlineMonitorPolicy,
) -> OnlineMonitorRecord:
    """Select a fixed true-label replay monitor with chemistry/size coverage."""

    if source_artifact.label_mode is not ReplayLabelMode.TRUE_DFT:
        raise TrainingDataInputError("ADAPT-MON1 replay monitor source must carry true DFT labels.")
    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to construct the replay online monitor.") from exc

    rows: list[tuple[tuple[Any, ...], int, str, str]] = []
    for index, atoms in enumerate(iread(source_artifact.path, index=":", format="extxyz")):
        geometry_identity = source_artifact.geometry_identities[index]
        key = _replay_sort_key(atoms, index, geometry_identity)
        chemistry_key = repr(key[0]) + f":sizebin={key[1]}"
        rows.append((key, index, geometry_identity, chemistry_key))
    if len(rows) != source_artifact.configuration_count:
        raise TrainingDataInputError("Replay online-monitor source count changed during inspection.")
    rows.sort(key=lambda row: row[0])
    realized = min(policy.replay_configurations, len(rows))
    positions = _systematic_positions(
        len(rows), realized, seed=policy.seed, namespace="replay:chemistry_size"
    )
    selected = [rows[position] for position in positions]
    # Materialize in original source order; this makes exact geometry alignment
    # with pseudo-label replay evidence easy to audit later.
    selected.sort(key=lambda row: row[1])

    available_by_stratum: dict[str, int] = {}
    selected_by_stratum: dict[str, int] = {}
    for _, _, _, stratum in rows:
        available_by_stratum[stratum] = available_by_stratum.get(stratum, 0) + 1
    for _, _, _, stratum in selected:
        selected_by_stratum[stratum] = selected_by_stratum.get(stratum, 0) + 1
    stratum_counts = tuple(
        (key, available_by_stratum[key], selected_by_stratum.get(key, 0))
        for key in sorted(available_by_stratum)
    )
    fallback = () if len(rows) >= policy.replay_configurations else ("replay_parent_smaller_than_requested",)
    return OnlineMonitorRecord(
        role="replay",
        parent_digest=source_artifact.content_digest,
        policy_digest=policy.policy_digest,
        requested_size=policy.replay_configurations,
        realized_size=realized,
        selected_identities=tuple(row[2] for row in selected),
        source_indices=tuple(row[1] for row in selected),
        stratum_counts=stratum_counts,
        strategy=policy.replay_strategy,
        seed=policy.seed,
        label_mode=ReplayLabelMode.TRUE_DFT.value,
        parent_role="true_label_replay_monitor",
        fallback_reason_codes=fallback,
    )


def materialize_replay_online_monitor(
    source_artifact: ReplayFileArtifact,
    record: OnlineMonitorRecord,
    output_path: str | Path,
) -> ReplayFileArtifact:
    """Write the exact replay-monitor subset and re-inspect its true labels."""

    if record.role != "replay" or record.parent_digest != source_artifact.content_digest:
        raise TrainingDataInputError("Replay monitor record/source lineage mismatch.")
    try:
        from ase.io import iread
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to materialize the replay online monitor.") from exc

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    selected = set(record.source_indices)
    temporary = target.with_suffix(target.suffix + ".tmp")

    def stream():
        emitted = 0
        for index, atoms in enumerate(iread(source_artifact.path, index=":", format="extxyz")):
            if index in selected:
                emitted += 1
                yield atoms
        if emitted != record.realized_size:
            raise TrainingDataInputError("Replay monitor materialization did not emit the selected count.")

    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            _write_extxyz_high_precision(handle, stream())
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    artifact = inspect_replay_extxyz(
        target,
        energy_key=source_artifact.energy_key,
        forces_key=source_artifact.forces_key,
        stress_key=source_artifact.stress_key,
        label_mode=ReplayLabelMode.TRUE_DFT,
    )
    if artifact.geometry_identities != record.selected_identities:
        raise TrainingDataInputError("Replay monitor materialization changed selected geometry identity/order.")
    expected_labels = tuple(source_artifact.label_identities[index] for index in record.source_indices)
    if artifact.label_identities != expected_labels:
        raise TrainingDataInputError("Replay monitor materialization changed true-label identity/order.")
    return artifact
