"""Deterministic nested multi-fidelity checkpoint evaluation contracts.

EVAL-MF1 keeps partial monitor results strictly separate from authoritative
full-fidelity checkpoint evaluation records and provides nested prediction
coverage.  EVAL-MF2 adds conservative paired/block-aware survivor guards and
ranking-instability expansion without changing the authoritative full-monitor
checkpoint selection policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import math
from typing import Any, Mapping, Sequence

import numpy as np
from ase.stress import full_3x3_to_voigt_6_stress

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .campaign_control import CheckpointMetricRecord
from .campaign_execution import CheckpointEvaluationRecord

MULTI_FIDELITY_EVALUATION_POLICY_LEGACY_SCHEMA = "mdstats.mlff-multi-fidelity-evaluation-policy.v1"
MULTI_FIDELITY_EVALUATION_POLICY_SCHEMA = "mdstats.mlff-multi-fidelity-evaluation-policy.v2"
MULTI_FIDELITY_MONITOR_LADDER_LEGACY_SCHEMA = "mdstats.mlff-multi-fidelity-monitor-ladder.v1"
MULTI_FIDELITY_MONITOR_LADDER_SCHEMA = "mdstats.mlff-multi-fidelity-monitor-ladder.v2"
MULTI_FIDELITY_ROUND_RECORD_LEGACY_SCHEMA = "mdstats.mlff-multi-fidelity-round-record.v1"
MULTI_FIDELITY_ROUND_RECORD_SCHEMA = "mdstats.mlff-multi-fidelity-round-record.v2"
MULTI_FIDELITY_SURVIVOR_DECISION_SCHEMA = "mdstats.mlff-multi-fidelity-survivor-decision.v1"
MULTI_FIDELITY_RUN_STATE_SCHEMA = "mdstats.mlff-multi-fidelity-run-state.v1"


@dataclass(frozen=True, slots=True)
class MultiFidelityEvaluationPolicy:
    round_fractions: tuple[float, ...] = (0.10, 0.33, 1.0)
    survival_fraction: float = 1.0 / 3.0
    minimum_finalists: int = 4
    guard_band_enabled: bool = True
    guard_standard_error_multiplier: float = 2.0
    guard_relative_margin: float = 0.02
    guard_minimum_blocks: int = 4
    instability_inversion_fraction: float = 0.25
    instability_survival_fraction: float = 0.50

    def __post_init__(self) -> None:
        values = tuple(float(v) for v in self.round_fractions)
        if len(values) < 2:
            raise TrainingDataInputError("Multi-fidelity evaluation requires at least two rounds.")
        if any(not math.isfinite(v) or v <= 0.0 or v > 1.0 for v in values):
            raise TrainingDataInputError("Multi-fidelity round fractions must be finite in (0, 1].")
        if any(b <= a for a, b in zip(values, values[1:])):
            raise TrainingDataInputError("Multi-fidelity round fractions must be strictly increasing.")
        if values[-1] != 1.0:
            raise TrainingDataInputError("The final multi-fidelity round must use the complete monitor (1.0).")
        if not math.isfinite(self.survival_fraction) or not 0.0 < self.survival_fraction < 1.0:
            raise TrainingDataInputError("Multi-fidelity survival_fraction must be in (0, 1).")
        if int(self.minimum_finalists) <= 0:
            raise TrainingDataInputError("Multi-fidelity minimum_finalists must be positive.")
        if not math.isfinite(self.guard_standard_error_multiplier) or self.guard_standard_error_multiplier < 0.0:
            raise TrainingDataInputError("guard_standard_error_multiplier must be finite and nonnegative.")
        if not math.isfinite(self.guard_relative_margin) or not 0.0 <= self.guard_relative_margin < 1.0:
            raise TrainingDataInputError("guard_relative_margin must be finite in [0, 1).")
        if int(self.guard_minimum_blocks) < 2:
            raise TrainingDataInputError("guard_minimum_blocks must be at least two.")
        if not math.isfinite(self.instability_inversion_fraction) or not 0.0 <= self.instability_inversion_fraction <= 1.0:
            raise TrainingDataInputError("instability_inversion_fraction must be in [0, 1].")
        if not math.isfinite(self.instability_survival_fraction) or not 0.0 < self.instability_survival_fraction <= 1.0:
            raise TrainingDataInputError("instability_survival_fraction must be in (0, 1].")
        if self.instability_survival_fraction < self.survival_fraction:
            raise TrainingDataInputError("instability_survival_fraction cannot be smaller than survival_fraction.")
        object.__setattr__(self, "round_fractions", values)
        object.__setattr__(self, "minimum_finalists", int(self.minimum_finalists))
        object.__setattr__(self, "guard_band_enabled", bool(self.guard_band_enabled))
        object.__setattr__(self, "guard_minimum_blocks", int(self.guard_minimum_blocks))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MULTI_FIDELITY_EVALUATION_POLICY_SCHEMA,
            "round_fractions": list(self.round_fractions),
            "survival_fraction": self.survival_fraction,
            "minimum_finalists": self.minimum_finalists,
            "guard_band_enabled": self.guard_band_enabled,
            "guard_standard_error_multiplier": self.guard_standard_error_multiplier,
            "guard_relative_margin": self.guard_relative_margin,
            "guard_minimum_blocks": self.guard_minimum_blocks,
            "instability_inversion_fraction": self.instability_inversion_fraction,
            "instability_survival_fraction": self.instability_survival_fraction,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MultiFidelityEvaluationPolicy":
        schema = payload.get("schema")
        if schema not in (MULTI_FIDELITY_EVALUATION_POLICY_SCHEMA, MULTI_FIDELITY_EVALUATION_POLICY_LEGACY_SCHEMA):
            raise TrainingDataSerializationError("Unsupported multi-fidelity evaluation policy schema.")
        result = cls(
            round_fractions=tuple(float(v) for v in payload["round_fractions"]),
            survival_fraction=float(payload["survival_fraction"]),
            minimum_finalists=int(payload["minimum_finalists"]),
            guard_band_enabled=bool(payload.get("guard_band_enabled", True)),
            guard_standard_error_multiplier=float(payload.get("guard_standard_error_multiplier", 2.0)),
            guard_relative_margin=float(payload.get("guard_relative_margin", 0.02)),
            guard_minimum_blocks=int(payload.get("guard_minimum_blocks", 4)),
            instability_inversion_fraction=float(payload.get("instability_inversion_fraction", 0.25)),
            instability_survival_fraction=float(payload.get("instability_survival_fraction", 0.50)),
        )
        if schema == MULTI_FIDELITY_EVALUATION_POLICY_LEGACY_SCHEMA:
            legacy_payload = dict(payload)
            legacy_payload.pop("policy_digest", None)
            expected = digest(legacy_payload)
        else:
            expected = result.policy_digest
        if payload.get("policy_digest") not in (None, expected):
            raise TrainingDataSerializationError("Multi-fidelity evaluation policy digest mismatch.")
        return result


def _spread_positions(count: int) -> tuple[int, ...]:
    """Return a deterministic coarse-to-fine order over one temporal sequence."""

    if count <= 0:
        return ()
    heap: list[tuple[int, int, int]] = []
    heapq.heappush(heap, (-count, -1, count))
    result: list[int] = []
    while heap:
        _, left, right = heapq.heappop(heap)
        if right - left <= 1:
            continue
        mid = (left + right) // 2
        result.append(mid)
        if mid - left > 1:
            heapq.heappush(heap, (-(mid - left - 1), left, mid))
        if right - mid > 1:
            heapq.heappush(heap, (-(right - mid - 1), mid, right))
    if len(result) != count or len(set(result)) != count:
        raise RuntimeError("Internal temporal spread-order construction failed.")
    return tuple(result)


def deterministic_balanced_order(
    geometry_identities: Sequence[str],
    *,
    stratum_labels: Sequence[str] | None = None,
    source_labels: Sequence[str] | None = None,
    temporal_indices: Sequence[int] | None = None,
) -> tuple[int, ...]:
    """Build a label-independent order balanced across available source strata."""

    identities = tuple(str(v) for v in geometry_identities)
    count = len(identities)
    if count <= 0 or len(set(identities)) != count:
        raise TrainingDataInputError("Monitor geometry identities must be non-empty and unique.")
    strata = tuple("all" for _ in identities) if stratum_labels is None else tuple(str(v) for v in stratum_labels)
    sources = tuple("all" for _ in identities) if source_labels is None else tuple(str(v) for v in source_labels)
    temporal = tuple(range(count)) if temporal_indices is None else tuple(int(v) for v in temporal_indices)
    if not (len(strata) == len(sources) == len(temporal) == count):
        raise TrainingDataInputError("Monitor ordering metadata must match the geometry count.")

    groups: dict[tuple[str, str], list[int]] = {}
    for index, key in enumerate(zip(strata, sources)):
        groups.setdefault(key, []).append(index)
    ordered_groups: list[tuple[tuple[str, str], tuple[int, ...]]] = []
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda i: (temporal[i], identities[i], i))
        spread = _spread_positions(len(members))
        ordered_groups.append((key, tuple(members[position] for position in spread)))

    result: list[int] = []
    cursor = 0
    while len(result) < count:
        progressed = False
        for _, members in ordered_groups:
            if cursor < len(members):
                result.append(members[cursor])
                progressed = True
        if not progressed:
            break
        cursor += 1
    if len(result) != count or len(set(result)) != count:
        raise RuntimeError("Internal balanced monitor-order construction failed.")
    return tuple(result)


def deterministic_block_labels(
    geometry_identities: Sequence[str],
    *,
    source_labels: Sequence[str] | None = None,
    temporal_indices: Sequence[int] | None = None,
) -> tuple[str, ...]:
    """Create source/trajectory-aware decorrelated blocks for paired MF2 guards.

    Existing source/trajectory identities are primary.  When there are too few
    sources to estimate dispersion, each source is split into deterministic,
    contiguous temporal chunks.  No reference or model labels participate.
    """

    identities = tuple(str(v) for v in geometry_identities)
    count = len(identities)
    if count <= 0:
        raise TrainingDataInputError("Cannot build uncertainty blocks for an empty monitor.")
    sources = tuple("all" for _ in identities) if source_labels is None else tuple(str(v) for v in source_labels)
    temporal = tuple(range(count)) if temporal_indices is None else tuple(int(v) for v in temporal_indices)
    if len(sources) != count or len(temporal) != count:
        raise TrainingDataInputError("Block metadata must match the monitor size.")
    groups: dict[str, list[int]] = {}
    for index, source in enumerate(sources):
        groups.setdefault(source or "all", []).append(index)
    # Aim for enough independent-ish blocks for a useful paired standard error,
    # while keeping each temporal chunk large enough to absorb frame correlation.
    target_blocks = min(12, max(4, int(round(math.sqrt(count)))))
    labels = ["" for _ in range(count)]
    for source in sorted(groups):
        members = sorted(groups[source], key=lambda i: (temporal[i], identities[i], i))
        proportional = max(1, int(round(target_blocks * len(members) / count)))
        chunk_count = min(len(members), proportional)
        for local_pos, index in enumerate(members):
            chunk = min(chunk_count - 1, (local_pos * chunk_count) // len(members))
            labels[index] = f"source:{source}|block:{chunk:03d}"
    if any(not value for value in labels):
        raise RuntimeError("Internal uncertainty-block construction failed.")
    return tuple(labels)


@dataclass(frozen=True, slots=True)
class MultiFidelityMonitorLadder:
    domain: str
    monitor_artifact_digest: str
    geometry_identities: tuple[str, ...]
    ordered_indices: tuple[int, ...]
    round_fractions: tuple[float, ...]
    round_indices: tuple[tuple[int, ...], ...]
    round_delta_indices: tuple[tuple[int, ...], ...]
    stratum_labels: tuple[str, ...] = ()
    source_labels: tuple[str, ...] = ()
    temporal_indices: tuple[int, ...] = ()
    block_labels: tuple[str, ...] = ()
    metadata_version: int = 2
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "monitor_artifact_digest", validate_digest(self.monitor_artifact_digest, name="monitor_artifact_digest"))
        count = len(self.geometry_identities)
        if count <= 0 or sorted(self.ordered_indices) != list(range(count)):
            raise TrainingDataInputError("Multi-fidelity monitor order must be a permutation of the monitor.")
        for name in ("stratum_labels", "source_labels", "temporal_indices", "block_labels"):
            values = getattr(self, name)
            if values and len(values) != count:
                raise TrainingDataInputError(f"Multi-fidelity ladder {name} must match the monitor size.")
        if self.block_labels and any(not str(value) for value in self.block_labels):
            raise TrainingDataInputError("Multi-fidelity uncertainty block labels must be non-empty.")
        if len(self.round_fractions) != len(self.round_indices) or len(self.round_indices) != len(self.round_delta_indices):
            raise TrainingDataInputError("Multi-fidelity ladder round counts are inconsistent.")
        previous: tuple[int, ...] = ()
        for fraction, indices, delta in zip(self.round_fractions, self.round_indices, self.round_delta_indices):
            if not indices or tuple(indices) != self.ordered_indices[: len(indices)]:
                raise TrainingDataInputError("Multi-fidelity round subsets must be prefixes of the immutable order.")
            if previous and tuple(indices[: len(previous)]) != previous:
                raise TrainingDataInputError("Multi-fidelity monitor subsets must be nested.")
            if tuple(indices[len(previous):]) != tuple(delta):
                raise TrainingDataInputError("Multi-fidelity round delta does not match nested-prefix growth.")
            previous = tuple(indices)
        if tuple(self.round_indices[-1]) != self.ordered_indices:
            raise TrainingDataInputError("Final multi-fidelity monitor round must contain the complete monitor.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MULTI_FIDELITY_MONITOR_LADDER_SCHEMA,
            "domain": self.domain,
            "monitor_artifact_digest": self.monitor_artifact_digest,
            "configuration_count": len(self.geometry_identities),
            "geometry_identities": list(self.geometry_identities),
            "ordered_indices": list(self.ordered_indices),
            "round_fractions": list(self.round_fractions),
            "round_indices": [list(v) for v in self.round_indices],
            "round_delta_indices": [list(v) for v in self.round_delta_indices],
            "stratum_labels": list(self.stratum_labels),
            "source_labels": list(self.source_labels),
            "temporal_indices": list(self.temporal_indices),
            "block_labels": list(self.block_labels),
            "metadata_version": int(self.metadata_version),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MultiFidelityMonitorLadder":
        schema = payload.get("schema")
        if schema not in (MULTI_FIDELITY_MONITOR_LADDER_SCHEMA, MULTI_FIDELITY_MONITOR_LADDER_LEGACY_SCHEMA):
            raise TrainingDataSerializationError("Unsupported multi-fidelity monitor ladder schema.")
        identities = tuple(str(v) for v in payload["geometry_identities"])
        result = cls(
            domain=str(payload["domain"]),
            monitor_artifact_digest=str(payload["monitor_artifact_digest"]),
            geometry_identities=identities,
            ordered_indices=tuple(int(v) for v in payload["ordered_indices"]),
            round_fractions=tuple(float(v) for v in payload["round_fractions"]),
            round_indices=tuple(tuple(int(v) for v in values) for values in payload["round_indices"]),
            round_delta_indices=tuple(tuple(int(v) for v in values) for values in payload["round_delta_indices"]),
            stratum_labels=tuple(str(v) for v in payload.get("stratum_labels", ())),
            source_labels=tuple(str(v) for v in payload.get("source_labels", ())),
            temporal_indices=tuple(int(v) for v in payload.get("temporal_indices", ())),
            block_labels=tuple(str(v) for v in payload.get("block_labels", ())),
            metadata_version=int(payload.get("metadata_version", 1 if schema == MULTI_FIDELITY_MONITOR_LADDER_LEGACY_SCHEMA else 2)),
        )
        if schema == MULTI_FIDELITY_MONITOR_LADDER_LEGACY_SCHEMA:
            legacy_payload = dict(payload)
            legacy_payload.pop("content_digest", None)
            expected = digest(legacy_payload)
        else:
            expected = result.content_digest
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("Multi-fidelity monitor ladder digest mismatch.")
        return result


def build_monitor_ladder(
    *,
    domain: str,
    monitor_artifact_digest: str,
    geometry_identities: Sequence[str],
    policy: MultiFidelityEvaluationPolicy,
    stratum_labels: Sequence[str] | None = None,
    source_labels: Sequence[str] | None = None,
    temporal_indices: Sequence[int] | None = None,
) -> MultiFidelityMonitorLadder:
    identities = tuple(str(v) for v in geometry_identities)
    count = len(identities)
    strata = tuple("all" for _ in identities) if stratum_labels is None else tuple(str(v) for v in stratum_labels)
    sources = tuple("all" for _ in identities) if source_labels is None else tuple(str(v) for v in source_labels)
    temporal = tuple(range(count)) if temporal_indices is None else tuple(int(v) for v in temporal_indices)
    if not (len(strata) == len(sources) == len(temporal) == count):
        raise TrainingDataInputError("Monitor ladder metadata must match the geometry count.")
    order = deterministic_balanced_order(
        identities,
        stratum_labels=strata,
        source_labels=sources,
        temporal_indices=temporal,
    )
    blocks = deterministic_block_labels(
        identities, source_labels=sources, temporal_indices=temporal
    )
    rounds: list[tuple[int, ...]] = []
    deltas: list[tuple[int, ...]] = []
    previous_size = 0
    for position, fraction in enumerate(policy.round_fractions):
        size = count if position == len(policy.round_fractions) - 1 else max(1, int(math.ceil(fraction * count)))
        size = max(size, previous_size + (1 if previous_size < count else 0))
        size = min(size, count)
        indices = tuple(order[:size])
        rounds.append(indices)
        deltas.append(tuple(order[previous_size:size]))
        previous_size = size
    return MultiFidelityMonitorLadder(
        domain=str(domain),
        monitor_artifact_digest=monitor_artifact_digest,
        geometry_identities=identities,
        ordered_indices=order,
        round_fractions=policy.round_fractions,
        round_indices=tuple(rounds),
        round_delta_indices=tuple(deltas),
        stratum_labels=strata,
        source_labels=sources,
        temporal_indices=temporal,
        block_labels=blocks,
        metadata_version=2,
    )


def _block_metric_scalars(
    view: Any,
    predictions: Sequence[Any],
    block_labels: Sequence[str],
    *,
    metric_name: str,
    combined_energy_weight: float,
    combined_force_weight: float,
    combined_stress_weight: float,
) -> tuple[tuple[str, float], ...]:
    if len(predictions) != int(view.configuration_count) or len(block_labels) != int(view.configuration_count):
        raise TrainingDataInputError("Block metric inputs must match the evaluation subset size.")
    stats: dict[str, list[float]] = {}
    # values: configurations, energy_abs_sum, force_sse, force_components,
    # stress_sse, stress_components
    for index, (prediction, raw_block) in enumerate(zip(predictions, block_labels)):
        block = str(raw_block)
        values = stats.setdefault(block, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        atom_count = int(view.atom_counts[index])
        start = int(view.force_offsets[index])
        stop = int(view.force_offsets[index + 1])
        energy_error = abs(float(prediction.energy_ev) - float(view.reference_energies[index])) / atom_count
        force = np.asarray(prediction.forces_ev_per_angstrom, dtype=np.float64)
        if force.shape != (atom_count, 3) or np.any(~np.isfinite(force)):
            raise TrainingDataInputError("Invalid prediction while building multi-fidelity block metrics.")
        force_error = force - view.reference_forces[start:stop]
        values[0] += 1.0
        values[1] += energy_error
        values[2] += float(np.sum(force_error * force_error, dtype=np.float64))
        values[3] += float(force_error.size)
        if bool(view.stress_present[index]):
            if prediction.stress_ev_per_angstrom3 is None:
                raise TrainingDataInputError("Stress-labelled block is missing a predicted stress.")
            stress = full_3x3_to_voigt_6_stress(
                np.asarray(prediction.stress_ev_per_angstrom3, dtype=np.float64)
            ).reshape(-1)
            stress_error = stress - view.reference_stresses[index]
            values[4] += float(np.sum(stress_error * stress_error, dtype=np.float64))
            values[5] += float(stress_error.size)
    result: list[tuple[str, float]] = []
    for block, values in sorted(stats.items()):
        configuration_count, energy_abs_sum, force_sse, force_components, stress_sse, stress_components = values
        energy_mae = energy_abs_sum / configuration_count
        force_rmse = math.sqrt(force_sse / force_components)
        stress_rmse = 0.0 if stress_components <= 0 else math.sqrt(stress_sse / stress_components)
        if metric_name in ("target_force_component_rmse", "force_rmse"):
            scalar = force_rmse
        elif metric_name == "target_energy_mae_per_atom":
            scalar = energy_mae
        elif metric_name in ("target_combined_loss", "combined_loss"):
            scalar = (
                combined_energy_weight * energy_mae
                + combined_force_weight * force_rmse
                + combined_stress_weight * stress_rmse
            )
        elif metric_name == "euclidean_bundle":
            scalar = math.sqrt(energy_mae * energy_mae + force_rmse * force_rmse + stress_rmse * stress_rmse)
        else:
            raise TrainingDataInputError(f"Unsupported multi-fidelity block metric {metric_name!r}.")
        if not math.isfinite(scalar) or scalar < 0.0:
            raise TrainingDataInputError("Multi-fidelity block metric must be finite and nonnegative.")
        result.append((block, float(scalar)))
    return tuple(result)


def target_primary_block_values(
    view: Any,
    predictions: Sequence[Any],
    block_labels: Sequence[str],
    *,
    primary_metric: str,
    combined_energy_weight: float,
    combined_force_weight: float,
    combined_stress_weight: float,
) -> tuple[tuple[str, float], ...]:
    return _block_metric_scalars(
        view,
        predictions,
        block_labels,
        metric_name=primary_metric,
        combined_energy_weight=combined_energy_weight,
        combined_force_weight=combined_force_weight,
        combined_stress_weight=combined_stress_weight,
    )


def replay_degradation_block_values(
    view: Any,
    candidate_predictions: Sequence[Any],
    baseline_predictions: Sequence[Any],
    block_labels: Sequence[str],
    *,
    replay_metric: str,
    replay_baseline_floor: float,
    combined_energy_weight: float,
    combined_force_weight: float,
    combined_stress_weight: float,
) -> tuple[tuple[str, float], ...]:
    candidate = dict(
        _block_metric_scalars(
            view,
            candidate_predictions,
            block_labels,
            metric_name=replay_metric,
            combined_energy_weight=combined_energy_weight,
            combined_force_weight=combined_force_weight,
            combined_stress_weight=combined_stress_weight,
        )
    )
    baseline = dict(
        _block_metric_scalars(
            view,
            baseline_predictions,
            block_labels,
            metric_name=replay_metric,
            combined_energy_weight=combined_energy_weight,
            combined_force_weight=combined_force_weight,
            combined_stress_weight=combined_stress_weight,
        )
    )
    if set(candidate) != set(baseline):
        raise TrainingDataInputError("Candidate and baseline replay blocks do not match.")
    return tuple(
        (
            block,
            max(0.0, candidate[block] - baseline[block]) / max(baseline[block], float(replay_baseline_floor)),
        )
        for block in sorted(candidate)
    )


@dataclass(frozen=True, slots=True)
class MultiFidelityCheckpointRoundRecord:
    run_plan_digest: str
    checkpoint_sha256: str
    round_index: int
    round_fraction: float
    target_ladder_digest: str
    replay_ladder_digest: str | None
    target_configuration_count: int
    replay_configuration_count: int
    evaluation_record: CheckpointEvaluationRecord
    full_fidelity: bool
    target_primary_block_values: tuple[tuple[str, float], ...] = ()
    replay_degradation_block_values: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        for name in ("run_plan_digest", "checkpoint_sha256", "target_ladder_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.replay_ladder_digest is not None:
            object.__setattr__(self, "replay_ladder_digest", validate_digest(self.replay_ladder_digest, name="replay_ladder_digest"))
        if self.evaluation_record.run_plan_digest != self.run_plan_digest or self.evaluation_record.checkpoint_sha256 != self.checkpoint_sha256:
            raise TrainingDataInputError("Multi-fidelity round evaluation lineage mismatch.")
        if self.evaluation_record.target_configuration_count != self.target_configuration_count:
            raise TrainingDataInputError("Multi-fidelity target count disagrees with evaluation record.")
        if self.evaluation_record.replay_configuration_count != self.replay_configuration_count:
            raise TrainingDataInputError("Multi-fidelity replay count disagrees with evaluation record.")
        if self.round_index < 0 or not 0.0 < float(self.round_fraction) <= 1.0:
            raise TrainingDataInputError("Invalid multi-fidelity round identity.")
        if self.full_fidelity != math.isclose(float(self.round_fraction), 1.0, rel_tol=0.0, abs_tol=0.0):
            raise TrainingDataInputError("Only the complete 1.0 round may be marked full fidelity.")
        for name in ("target_primary_block_values", "replay_degradation_block_values"):
            values = tuple(sorted((str(k), float(v)) for k, v in getattr(self, name)))
            if len({key for key, _ in values}) != len(values) or any(not key or not math.isfinite(value) or value < 0.0 for key, value in values):
                raise TrainingDataInputError(f"Invalid {name} evidence.")
            object.__setattr__(self, name, values)

    @property
    def metric_record(self) -> CheckpointMetricRecord:
        return self.evaluation_record.metric_record

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MULTI_FIDELITY_ROUND_RECORD_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "checkpoint_sha256": self.checkpoint_sha256,
            "round_index": self.round_index,
            "round_fraction": self.round_fraction,
            "target_ladder_digest": self.target_ladder_digest,
            "replay_ladder_digest": self.replay_ladder_digest,
            "target_configuration_count": self.target_configuration_count,
            "replay_configuration_count": self.replay_configuration_count,
            "full_fidelity": self.full_fidelity,
            "evidence_class": "authoritative_full" if self.full_fidelity else "screening_partial",
            "target_primary_block_values": dict(self.target_primary_block_values),
            "replay_degradation_block_values": dict(self.replay_degradation_block_values),
            "evaluation_record": self.evaluation_record.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MultiFidelityCheckpointRoundRecord":
        schema = payload.get("schema")
        if schema not in (MULTI_FIDELITY_ROUND_RECORD_SCHEMA, MULTI_FIDELITY_ROUND_RECORD_LEGACY_SCHEMA):
            raise TrainingDataSerializationError("Unsupported multi-fidelity round record schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            round_index=int(payload["round_index"]),
            round_fraction=float(payload["round_fraction"]),
            target_ladder_digest=str(payload["target_ladder_digest"]),
            replay_ladder_digest=None if payload.get("replay_ladder_digest") is None else str(payload["replay_ladder_digest"]),
            target_configuration_count=int(payload["target_configuration_count"]),
            replay_configuration_count=int(payload["replay_configuration_count"]),
            evaluation_record=CheckpointEvaluationRecord.from_dict(payload["evaluation_record"]),
            full_fidelity=bool(payload["full_fidelity"]),
            target_primary_block_values=tuple((str(k), float(v)) for k, v in payload.get("target_primary_block_values", {}).items()),
            replay_degradation_block_values=tuple((str(k), float(v)) for k, v in payload.get("replay_degradation_block_values", {}).items()),
        )
        if schema == MULTI_FIDELITY_ROUND_RECORD_LEGACY_SCHEMA:
            legacy_payload = dict(payload)
            legacy_payload.pop("content_digest", None)
            expected = digest(legacy_payload)
        else:
            expected = result.content_digest
        if payload.get("content_digest") not in (None, expected):
            raise TrainingDataSerializationError("Multi-fidelity round record digest mismatch.")
        return result


def provisional_ranking_key(metric: CheckpointMetricRecord, checkpoint_epoch: int, checkpoint_sha256: str, metric_policy: Any) -> tuple[float, float, int, str]:
    primary = metric.primary_metric_value(metric_policy)
    primary_key = float("inf") if primary is None else float(primary)
    replay = metric.replay_degradation_fraction
    if metric.replay_label_mode is not None and getattr(metric.replay_label_mode, "value", "") == "foundation_pseudolabel":
        replay_key = 0.0
    else:
        replay_key = float("inf") if replay is None else float(replay)
    return primary_key, replay_key, int(checkpoint_epoch), str(checkpoint_sha256)


def survivor_count(candidate_count: int, policy: MultiFidelityEvaluationPolicy, *, next_round_is_final: bool) -> int:
    if candidate_count <= 0:
        return 0
    nominal = max(1, int(math.ceil(candidate_count * policy.survival_fraction)))
    if next_round_is_final:
        nominal = max(nominal, min(candidate_count, policy.minimum_finalists))
    return min(candidate_count, nominal)


def _pairwise_inversion_fraction(previous: Sequence[str], current: Sequence[str]) -> float:
    common = [value for value in previous if value in set(current)]
    if len(common) < 2:
        return 0.0
    current_rank = {value: index for index, value in enumerate(current)}
    discordant = 0
    total = 0
    for left in range(len(common)):
        for right in range(left + 1, len(common)):
            total += 1
            if current_rank[common[left]] > current_rank[common[right]]:
                discordant += 1
    return 0.0 if total == 0 else discordant / total


def _paired_primary_ambiguous(
    candidate: MultiFidelityCheckpointRoundRecord,
    cutoff: MultiFidelityCheckpointRoundRecord,
    *,
    candidate_primary: float,
    cutoff_primary: float,
    policy: MultiFidelityEvaluationPolicy,
) -> tuple[bool, int, float | None, float | None]:
    relative_allowance = policy.guard_relative_margin * max(abs(cutoff_primary), 1.0e-12)
    candidate_blocks = dict(candidate.target_primary_block_values)
    cutoff_blocks = dict(cutoff.target_primary_block_values)
    common = sorted(set(candidate_blocks) & set(cutoff_blocks))
    if len(common) >= policy.guard_minimum_blocks:
        differences = np.asarray([candidate_blocks[key] - cutoff_blocks[key] for key in common], dtype=np.float64)
        mean_difference = float(np.mean(differences))
        standard_error = float(np.std(differences, ddof=1) / math.sqrt(len(differences))) if len(differences) > 1 else 0.0
        allowance = relative_allowance + policy.guard_standard_error_multiplier * standard_error
        return mean_difference <= allowance, len(common), mean_difference, standard_error
    return candidate_primary <= cutoff_primary + relative_allowance, len(common), None, None


@dataclass(frozen=True, slots=True)
class MultiFidelitySurvivorDecision:
    nominal_keep_count: int
    retained_checkpoint_sha256s: tuple[str, ...]
    guard_retained_checkpoint_sha256s: tuple[str, ...] = ()
    replay_rescued_checkpoint_sha256s: tuple[str, ...] = ()
    instability_expanded: bool = False
    inversion_fraction: float = 0.0
    cutoff_checkpoint_sha256: str | None = None
    candidate_diagnostics: tuple[tuple[str, Mapping[str, Any]], ...] = ()

    def __post_init__(self) -> None:
        if self.nominal_keep_count < 0:
            raise TrainingDataInputError("nominal_keep_count cannot be negative.")
        for name in ("retained_checkpoint_sha256s", "guard_retained_checkpoint_sha256s", "replay_rescued_checkpoint_sha256s"):
            values = tuple(validate_digest(value, name="checkpoint_sha256") for value in getattr(self, name))
            if len(set(values)) != len(values):
                raise TrainingDataInputError(f"{name} contains duplicate checkpoints.")
            object.__setattr__(self, name, values)
        if self.cutoff_checkpoint_sha256 is not None:
            object.__setattr__(self, "cutoff_checkpoint_sha256", validate_digest(self.cutoff_checkpoint_sha256, name="cutoff_checkpoint_sha256"))
        if not 0.0 <= float(self.inversion_fraction) <= 1.0:
            raise TrainingDataInputError("inversion_fraction must be in [0, 1].")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": MULTI_FIDELITY_SURVIVOR_DECISION_SCHEMA,
            "nominal_keep_count": self.nominal_keep_count,
            "retained_checkpoint_sha256s": list(self.retained_checkpoint_sha256s),
            "guard_retained_checkpoint_sha256s": list(self.guard_retained_checkpoint_sha256s),
            "replay_rescued_checkpoint_sha256s": list(self.replay_rescued_checkpoint_sha256s),
            "instability_expanded": self.instability_expanded,
            "inversion_fraction": self.inversion_fraction,
            "cutoff_checkpoint_sha256": self.cutoff_checkpoint_sha256,
            "candidate_diagnostics": {key: dict(value) for key, value in self.candidate_diagnostics},
        }
        return {**payload, "content_digest": digest(payload)}


def conservative_survivor_decision(
    ranked_checkpoint_sha256s: Sequence[str],
    round_records: Mapping[str, MultiFidelityCheckpointRoundRecord],
    *,
    metric_policy: Any,
    policy: MultiFidelityEvaluationPolicy,
    next_round_is_final: bool,
    previous_ranking_sha256s: Sequence[str] = (),
    maximum_replay_degradation_fraction: float | None = None,
) -> MultiFidelitySurvivorDecision:
    """Return a conservative MF2 survivor set for one partial evaluation round.

    The nominal top fraction is always retained.  Candidates just below the
    cutoff are retained when paired source/block evidence cannot separate them
    from the cutoff by more than the frozen two-SE-plus-relative-margin guard.
    For true-label replay, a small reserve of provisionally replay-admissible
    checkpoints is also retained so target-only ranking cannot eliminate every
    plausible replay-retaining solution.  Large round-to-round rank inversions
    expand the next round deterministically.
    """

    ranked = tuple(validate_digest(value, name="checkpoint_sha256") for value in ranked_checkpoint_sha256s)
    if not ranked:
        return MultiFidelitySurvivorDecision(0, ())
    if set(ranked) != set(round_records):
        raise TrainingDataInputError("Survivor decision requires one round record per ranked checkpoint.")
    nominal = survivor_count(len(ranked), policy, next_round_is_final=next_round_is_final)
    retained = set(ranked[:nominal])
    cutoff_sha = ranked[nominal - 1]
    cutoff_record = round_records[cutoff_sha]
    cutoff_primary_raw = cutoff_record.metric_record.primary_metric_value(metric_policy)
    cutoff_primary = float("inf") if cutoff_primary_raw is None else float(cutoff_primary_raw)
    guard_retained: list[str] = []
    diagnostics: dict[str, dict[str, Any]] = {}

    if policy.guard_band_enabled and math.isfinite(cutoff_primary):
        for sha in ranked[nominal:]:
            record = round_records[sha]
            primary_raw = record.metric_record.primary_metric_value(metric_policy)
            primary = float("inf") if primary_raw is None else float(primary_raw)
            ambiguous, common_blocks, mean_difference, standard_error = _paired_primary_ambiguous(
                record,
                cutoff_record,
                candidate_primary=primary,
                cutoff_primary=cutoff_primary,
                policy=policy,
            )
            diagnostics[sha] = {
                "primary_metric_value": primary,
                "paired_common_block_count": common_blocks,
                "paired_mean_difference": mean_difference,
                "paired_standard_error": standard_error,
                "guard_ambiguous_with_cutoff": bool(ambiguous),
            }
            if ambiguous:
                retained.add(sha)
                guard_retained.append(sha)

    replay_rescued: list[str] = []
    if maximum_replay_degradation_fraction is not None:
        threshold = float(maximum_replay_degradation_fraction)
        if math.isfinite(threshold) and threshold >= 0.0:
            replay_candidates = []
            for sha in ranked:
                degradation = round_records[sha].metric_record.replay_degradation_fraction
                if degradation is None:
                    continue
                if degradation <= threshold * (1.0 + policy.guard_relative_margin):
                    primary = round_records[sha].metric_record.primary_metric_value(metric_policy)
                    replay_candidates.append((float("inf") if primary is None else float(primary), float(degradation), sha))
            reserve_count = min(len(ranked), policy.minimum_finalists)
            for _, _, sha in sorted(replay_candidates)[:reserve_count]:
                if sha not in retained:
                    retained.add(sha)
                    replay_rescued.append(sha)

    inversion_fraction = _pairwise_inversion_fraction(previous_ranking_sha256s, ranked)
    instability_expanded = False
    if (
        previous_ranking_sha256s
        and inversion_fraction >= policy.instability_inversion_fraction
        and len(ranked) > len(retained)
    ):
        expanded_count = max(
            nominal,
            int(math.ceil(len(ranked) * policy.instability_survival_fraction)),
        )
        before = len(retained)
        retained.update(ranked[:expanded_count])
        instability_expanded = len(retained) > before

    ordered_retained = tuple(sha for sha in ranked if sha in retained)
    return MultiFidelitySurvivorDecision(
        nominal_keep_count=nominal,
        retained_checkpoint_sha256s=ordered_retained,
        guard_retained_checkpoint_sha256s=tuple(sha for sha in ranked if sha in set(guard_retained)),
        replay_rescued_checkpoint_sha256s=tuple(sha for sha in ranked if sha in set(replay_rescued)),
        instability_expanded=instability_expanded,
        inversion_fraction=float(inversion_fraction),
        cutoff_checkpoint_sha256=cutoff_sha,
        candidate_diagnostics=tuple((sha, diagnostics[sha]) for sha in ranked if sha in diagnostics),
    )


__all__ = [
    "MULTI_FIDELITY_EVALUATION_POLICY_SCHEMA",
    "MULTI_FIDELITY_MONITOR_LADDER_SCHEMA",
    "MULTI_FIDELITY_ROUND_RECORD_SCHEMA",
    "MULTI_FIDELITY_SURVIVOR_DECISION_SCHEMA",
    "MULTI_FIDELITY_RUN_STATE_SCHEMA",
    "MultiFidelityEvaluationPolicy",
    "MultiFidelityMonitorLadder",
    "MultiFidelityCheckpointRoundRecord",
    "MultiFidelitySurvivorDecision",
    "deterministic_balanced_order",
    "deterministic_block_labels",
    "build_monitor_ladder",
    "target_primary_block_values",
    "replay_degradation_block_values",
    "provisional_ranking_key",
    "survivor_count",
    "conservative_survivor_decision",
]
