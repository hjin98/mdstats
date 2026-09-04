"""P3-A target-size common preparation and exact candidate projection.

This module implements the canonical deterministic common preparation for the
whole target-size study (one fitted preparation per P2 experiment, normally
over the accepted ``P_train`` membership) and the exact selection-only
projection of that common fitted state onto each accepted ``T_N``.

The common preparation is rooted only in accepted current-generation P1/P2
authority: the ``CanonicalFrameAuthority``-bound population, the neutral
statistical base, and the exact P2 split membership.  Retired label-domain,
DATA5-CV, selection-ladder, and candidate-complement objects are not scientific
parents of any object defined here.

Version-agnostic naming: no symbol in this package encodes a historical
generation label; generation identity lives only in workplan metadata.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import digest, validate_digest
from .._frame_access import build_frame_array_index
from .._common import TrainingDataInputError, TrainingDataSerializationError
from ..objectives import (
    ConfigurationWeightPolicy,
    FrameTrainingWeight,
    FrameTrainingWeightTable,
    TrainingObjectivePolicy,
)
from ..reference_fit import (
    AtomicReferenceFitMode,
    AtomicReferenceFitPolicy,
    solve_atomic_reference_least_squares,
)
from ..target_size_experiment import (
    TargetSizeStatisticalAggregate,
    target_training_prefix_digest,
)

TARGET_SIZE_COMMON_POLICY_SCHEMA = "mdstats.target-size.common-training-policy.v2"
TARGET_SIZE_COMMON_ATOMIC_REFERENCE_SCHEMA = (
    "mdstats.target-size.common-atomic-reference.v1"
)
TARGET_SIZE_COMMON_PREPARATION_SCHEMA = "mdstats.target-size.common-preparation.v2"
TARGET_SIZE_CANDIDATE_PREPARATION_SCHEMA = (
    "mdstats.target-size.candidate-preparation.v1"
)

REPLAY_EXPOSURE_NONE_DIGEST = digest(
    {"schema": "mdstats.target-size.replay-exposure.v1", "mode": "none"}
)
EVAL2_TARGET_METRIC_POLICY_DIGEST = digest(
    {
        "schema": "mdstats.target-size.eval2-metric-policy.v1",
        "primary_target_metric": "force_component_rmse_ev_per_angstrom",
        "unit_conversion": "ev_per_angstrom_to_mev_per_angstrom_x_1000",
    }
)


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TrainingDataInputError(f"{name} must be a positive integer.")
    return int(value)


@dataclass(frozen=True, slots=True)
class TargetSizeCommonTrainingPolicy:
    """Seed-neutral, N-neutral common training/preparation policy template.

    Every fitted quantity actually consumed by candidate training is frozen
    here or derived once by the common preparation built under this policy.
    The policy never carries an optimizer seed, a candidate size, an M-rung,
    or any evaluation/CV/held-out identity.
    """

    objective_policy: TrainingObjectivePolicy = field(
        default_factory=TrainingObjectivePolicy
    )
    configuration_weight_policy: ConfigurationWeightPolicy = field(
        default_factory=ConfigurationWeightPolicy
    )
    atomic_reference_policy: AtomicReferenceFitPolicy = field(
        default_factory=AtomicReferenceFitPolicy
    )
    replay_exposure_policy_digest: str = REPLAY_EXPOSURE_NONE_DIGEST
    foundation_checkpoint_digest: str | None = None
    selected_head_name: str | None = None
    eval2_metric_policy_digest: str = EVAL2_TARGET_METRIC_POLICY_DIGEST
    batch_size: int = 4
    default_dtype: str = "float64"
    harness_validation_frame_count: int = 4

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "replay_exposure_policy_digest",
            validate_digest(
                self.replay_exposure_policy_digest,
                name="replay_exposure_policy_digest",
            ),
        )
        object.__setattr__(
            self,
            "eval2_metric_policy_digest",
            validate_digest(
                self.eval2_metric_policy_digest, name="eval2_metric_policy_digest"
            ),
        )
        if self.foundation_checkpoint_digest is not None:
            object.__setattr__(
                self,
                "foundation_checkpoint_digest",
                validate_digest(
                    self.foundation_checkpoint_digest,
                    name="foundation_checkpoint_digest",
                ),
            )
        if self.selected_head_name is not None and not str(
            self.selected_head_name
        ).strip():
            raise TrainingDataInputError("selected_head_name must be non-empty.")
        batch = _positive_int(self.batch_size, name="batch_size")
        object.__setattr__(self, "batch_size", batch)
        harness = _positive_int(
            self.harness_validation_frame_count,
            name="harness_validation_frame_count",
        )
        object.__setattr__(self, "harness_validation_frame_count", harness)
        if self.default_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Unsupported common default dtype.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_COMMON_POLICY_SCHEMA,
            "objective_policy": self.objective_policy.to_dict(),
            "configuration_weight_policy": self.configuration_weight_policy.to_dict(),
            "atomic_reference_policy": self.atomic_reference_policy.to_dict(),
            "replay_exposure_policy_digest": self.replay_exposure_policy_digest,
            "foundation_checkpoint_digest": self.foundation_checkpoint_digest,
            "selected_head_name": self.selected_head_name,
            "eval2_metric_policy_digest": self.eval2_metric_policy_digest,
            "batch_size": self.batch_size,
            "default_dtype": self.default_dtype,
            "harness_validation_frame_count": self.harness_validation_frame_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCommonTrainingPolicy:
        if payload.get("schema") != TARGET_SIZE_COMMON_POLICY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size common training-policy schema."
            )
        result = cls(
            objective_policy=TrainingObjectivePolicy.from_dict(
                payload["objective_policy"]
            ),
            configuration_weight_policy=ConfigurationWeightPolicy.from_dict(
                payload["configuration_weight_policy"]
            ),
            atomic_reference_policy=AtomicReferenceFitPolicy.from_dict(
                payload["atomic_reference_policy"]
            ),
            replay_exposure_policy_digest=str(payload["replay_exposure_policy_digest"]),
            foundation_checkpoint_digest=(
                None
                if payload.get("foundation_checkpoint_digest") is None
                else str(payload["foundation_checkpoint_digest"])
            ),
            selected_head_name=(
                None
                if payload.get("selected_head_name") is None
                else str(payload["selected_head_name"])
            ),
            eval2_metric_policy_digest=str(payload["eval2_metric_policy_digest"]),
            batch_size=int(payload["batch_size"]),
            default_dtype=str(payload["default_dtype"]),
            harness_validation_frame_count=int(
                payload["harness_validation_frame_count"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size common training-policy digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class CommonAtomicReferenceFit:
    """Version-agnostic atomic-reference (E0) fit over one exact membership.

    This reuses the exact shared least-squares recipe of the DATA7
    atomic-reference owner (``solve_atomic_reference_least_squares``) while
    binding the current P1/P2 membership authority instead of a legacy
    ``FeatureFitDomain``.
    """

    policy_digest: str
    membership_digest: str
    element_order: tuple[int, ...]
    count_matrix_digest: str
    target_energies_digest: str
    reference_energies_ev: tuple[tuple[int, float], ...]
    rank: int
    singular_values_digest: str
    residual_rmse_ev: float
    residual_mae_ev: float
    maximum_absolute_residual_ev: float
    rank_deficient: bool
    transfer_warnings: tuple[str, ...]
    foundation_checkpoint_digest: str | None = None
    foundation_identity_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "policy_digest",
            "membership_digest",
            "count_matrix_digest",
            "target_energies_digest",
            "singular_values_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        elements = tuple(int(v) for v in self.element_order)
        if (
            not elements
            or len(set(elements)) != len(elements)
            or any(v <= 0 for v in elements)
            or tuple(sorted(elements)) != elements
        ):
            raise TrainingDataInputError(
                "Common atomic-reference element order must be unique increasing atomic numbers."
            )
        references = tuple(
            (int(z), float(v)) for z, v in self.reference_energies_ev
        )
        if (
            len(references) != len(elements)
            or tuple(z for z, _ in references) != elements
            or any(not math.isfinite(v) for _, v in references)
        ):
            raise TrainingDataInputError(
                "Common atomic-reference fitted values must align with the element order."
            )
        object.__setattr__(self, "element_order", elements)
        object.__setattr__(self, "reference_energies_ev", references)
        rank = int(self.rank)
        if rank <= 0:
            raise TrainingDataInputError("Common atomic-reference fit rank is invalid.")
        object.__setattr__(self, "rank", rank)
        for name in (
            "residual_rmse_ev",
            "residual_mae_ev",
            "maximum_absolute_residual_ev",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(
                    f"Common atomic-reference {name} must be finite and nonnegative."
                )
            object.__setattr__(self, name, value)
        object.__setattr__(
            self, "transfer_warnings", tuple(str(v) for v in self.transfer_warnings)
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_COMMON_ATOMIC_REFERENCE_SCHEMA,
            "policy_digest": self.policy_digest,
            "membership_digest": self.membership_digest,
            "element_order": list(self.element_order),
            "count_matrix_digest": self.count_matrix_digest,
            "target_energies_digest": self.target_energies_digest,
            "reference_energies_ev": {
                str(z): v for z, v in self.reference_energies_ev
            },
            "rank": self.rank,
            "singular_values_digest": self.singular_values_digest,
            "residual_rmse_ev": self.residual_rmse_ev,
            "residual_mae_ev": self.residual_mae_ev,
            "maximum_absolute_residual_ev": self.maximum_absolute_residual_ev,
            "rank_deficient": self.rank_deficient,
            "transfer_warnings": list(self.transfer_warnings),
            "foundation_checkpoint_digest": self.foundation_checkpoint_digest,
            "foundation_identity_digest": self.foundation_identity_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> CommonAtomicReferenceFit:
        if payload.get("schema") != TARGET_SIZE_COMMON_ATOMIC_REFERENCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported common atomic-reference schema."
            )
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            membership_digest=str(payload["membership_digest"]),
            element_order=tuple(int(v) for v in payload["element_order"]),
            count_matrix_digest=str(payload["count_matrix_digest"]),
            target_energies_digest=str(payload["target_energies_digest"]),
            reference_energies_ev=tuple(
                (int(z), float(v))
                for z, v in payload["reference_energies_ev"].items()
            ),
            rank=int(payload["rank"]),
            singular_values_digest=str(payload["singular_values_digest"]),
            residual_rmse_ev=float(payload["residual_rmse_ev"]),
            residual_mae_ev=float(payload["residual_mae_ev"]),
            maximum_absolute_residual_ev=float(
                payload["maximum_absolute_residual_ev"]
            ),
            rank_deficient=bool(payload["rank_deficient"]),
            transfer_warnings=tuple(
                str(v) for v in payload.get("transfer_warnings", ())
            ),
            foundation_checkpoint_digest=(
                None
                if payload.get("foundation_checkpoint_digest") is None
                else str(payload["foundation_checkpoint_digest"])
            ),
            foundation_identity_digest=(
                None
                if payload.get("foundation_identity_digest") is None
                else str(payload["foundation_identity_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Common atomic-reference digest mismatch."
            )
        return result


def fit_common_atomic_reference_energies(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    membership: Sequence[str],
    *,
    policy: AtomicReferenceFitPolicy,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    foundation_prediction_energy_by_frame: Mapping[str, float] | None = None,
    foundation_reference_energies: Mapping[int, float] | None = None,
    foundation_checkpoint_digest: str | None = None,
    foundation_identity_digest: str | None = None,
) -> CommonAtomicReferenceFit:
    """Fit common atomic reference energies once over one exact membership.

    The numeric recipe is the shared DATA7 least-squares seam; the fit domain
    is the exact current-generation membership supplied by the caller (the
    P2 ``P_train``), never a legacy ``FeatureFitDomain``.
    """

    index = (
        build_frame_array_index(frame_catalog, frame_data_by_run)
        if frame_array_index is None
        else frame_array_index
    )
    frame_uids = tuple(str(v) for v in membership)
    if not frame_uids or len(set(frame_uids)) != len(frame_uids):
        raise TrainingDataInputError(
            "Common atomic-reference fitting requires a unique non-empty membership."
        )
    counts_by_run: dict[str, Mapping[int, int]] = {}
    element_set: set[int] = set()
    for uid in frame_uids:
        record, _data, _local = index[uid]
        run_id = str(record.run_id)
        counts = counts_by_run.get(run_id)
        if counts is None:
            data = frame_data_by_run[run_id]
            numbers = np.asarray(data.atomic_numbers, dtype=np.int32)
            unique, multiplicities = np.unique(numbers, return_counts=True)
            counts = {
                int(z): int(count)
                for z, count in zip(unique, multiplicities, strict=True)
            }
            counts_by_run[run_id] = counts
        element_set.update(int(z) for z in counts)
    elements = tuple(sorted(element_set))
    element_position = {z: position for position, z in enumerate(elements)}
    A = np.zeros((len(frame_uids), len(elements)), dtype=np.float64)
    target = np.empty(len(frame_uids), dtype=np.float64)
    for row, uid in enumerate(frame_uids):
        record, data, local = index[uid]
        counts = counts_by_run[str(record.run_id)]
        for z, count in counts.items():
            A[row, element_position[int(z)]] = int(count)
        if data.energies_ev is None:
            raise TrainingDataInputError(
                "Common atomic-reference fitting requires total energies on every frame."
            )
        value = float(data.energies_ev[local])
        if not math.isfinite(value):
            raise TrainingDataInputError(
                "Common atomic-reference fitting encountered a non-finite target energy."
            )
        target[row] = value
    foundation_refs: dict[int, float] = {}
    predictions: np.ndarray | None = None
    checkpoint_digest: str | None = None
    identity_digest: str | None = None
    if policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
        if (
            foundation_prediction_energy_by_frame is None
            or foundation_reference_energies is None
        ):
            raise TrainingDataInputError(
                "Foundation-residual E0 fitting requires foundation predictions and E0s."
            )
        missing = [uid for uid in frame_uids if uid not in foundation_prediction_energy_by_frame]
        if missing:
            raise TrainingDataInputError(
                "Foundation predictions are missing for common-preparation frames."
            )
        predictions = np.asarray(
            [float(foundation_prediction_energy_by_frame[uid]) for uid in frame_uids],
            dtype=np.float64,
        )
        if not np.all(np.isfinite(predictions)):
            raise TrainingDataInputError(
                "Foundation predictions contain non-finite values."
            )
        foundation_refs = {
            int(z): float(v) for z, v in foundation_reference_energies.items()
        }
        missing_refs = sorted(set(elements) - set(foundation_refs))
        if missing_refs or any(
            not math.isfinite(foundation_refs[z]) for z in elements
        ):
            raise TrainingDataInputError(
                "Foundation E0 mapping is missing or invalid for the common membership."
            )
        fit_target = target - predictions
        if foundation_checkpoint_digest is not None:
            checkpoint_digest = validate_digest(
                foundation_checkpoint_digest, name="foundation_checkpoint_digest"
            )
        if foundation_identity_digest is not None:
            identity_digest = validate_digest(
                foundation_identity_digest, name="foundation_identity_digest"
            )
    else:
        if (
            foundation_prediction_energy_by_frame is not None
            or foundation_reference_energies is not None
            or foundation_checkpoint_digest is not None
            or foundation_identity_digest is not None
        ):
            raise TrainingDataInputError(
                "Foundation data were supplied to a from-scratch common fit."
            )
        fit_target = target
    solve = solve_atomic_reference_least_squares(A, fit_target, policy)
    fitted = np.asarray(solve.fitted_reference_energies_ev, dtype=np.float64)
    if policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
        final_map = {
            z: foundation_refs[z] + float(fitted[position])
            for position, z in enumerate(elements)
        }
    else:
        final_map = {
            z: float(fitted[position]) for position, z in enumerate(elements)
        }
    warnings = list(solve.transfer_warnings)
    if policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL:
        warnings.append("foundation_residual_corrections_are_checkpoint_bound")
    return CommonAtomicReferenceFit(
        policy_digest=policy.policy_digest,
        membership_digest=digest({"frame_uids": list(frame_uids)}),
        element_order=elements,
        count_matrix_digest=digest(
            {"count_matrix": [[int(v) for v in row] for row in A]}
        ),
        target_energies_digest=digest({"target_energies_ev": [float(v) for v in target]}),
        reference_energies_ev=tuple((z, final_map[z]) for z in elements),
        rank=solve.rank,
        singular_values_digest=digest(
            {"singular_values": list(solve.singular_values)}
        ),
        residual_rmse_ev=solve.residual_rmse_ev,
        residual_mae_ev=solve.residual_mae_ev,
        maximum_absolute_residual_ev=solve.maximum_absolute_residual_ev,
        rank_deficient=solve.rank_deficient,
        transfer_warnings=tuple(warnings),
        foundation_checkpoint_digest=checkpoint_digest,
        foundation_identity_digest=identity_digest,
    )


def fit_common_configuration_weights(
    population: Any,
    membership: Sequence[str],
    *,
    policy: ConfigurationWeightPolicy,
) -> tuple[FrameTrainingWeight, ...]:
    """Fit deterministic per-frame configuration weights once, mean-one
    normalized over the exact common membership.

    Projection later selects these frozen values and never renormalizes them,
    so the objective changes with N only through the intended data-cardinality
    change.
    """

    frame_uids = tuple(str(v) for v in membership)
    if not frame_uids or len(set(frame_uids)) != len(frame_uids):
        raise TrainingDataInputError(
            "Common configuration weights require a unique non-empty membership."
        )
    known = set(population.frame_uids)
    unknown = [uid for uid in frame_uids if uid not in known]
    if unknown:
        raise TrainingDataInputError(
            "Common configuration weights require frames inside the bound population."
        )
    condition_counts: dict[str, int] = {}
    for uid in frame_uids:
        condition_id = str(population.frame(uid).condition_id)
        condition_counts[condition_id] = condition_counts.get(condition_id, 0) + 1
    frame_count = len(frame_uids)
    condition_count = len(condition_counts)
    records: list[FrameTrainingWeight] = []
    for uid in frame_uids:
        condition_id = str(population.frame(uid).condition_id)
        if policy.equalize_condition_strata:
            raw = float(frame_count) / (
                float(condition_count) * float(condition_counts[condition_id])
            )
            reason_codes: tuple[str, ...] = ("condition_stratum_equalized",)
        else:
            raw = 1.0
            reason_codes = ("uniform_configuration_weight",)
        records.append(
            FrameTrainingWeight(
                frame_uid=uid,
                configuration_weight=raw,
                energy_weight=raw,
                forces_weight=raw,
                stress_weight=raw,
                reason_codes=reason_codes,
            )
        )
    # One single normalization to mean one over the exact common membership.
    # This happens exactly once at common-fit time; candidate projection must
    # never repeat it.
    mean = sum(item.configuration_weight for item in records) / frame_count
    if not math.isfinite(mean) or mean <= 0.0:
        raise TrainingDataInputError(
            "Common configuration weights collapsed to a degenerate normalization."
        )
    normalized = [
        FrameTrainingWeight(
            frame_uid=item.frame_uid,
            configuration_weight=item.configuration_weight / mean,
            energy_weight=item.energy_weight / mean,
            forces_weight=item.forces_weight / mean,
            stress_weight=item.stress_weight / mean,
            reason_codes=item.reason_codes,
        )
        for item in records
    ]
    return tuple(sorted(normalized, key=lambda item: item.frame_uid))


def _fitted_frame_weights(
    index: Mapping[str, tuple[Any, Any, int]],
    membership: Sequence[str],
    *,
    objective_policy: TrainingObjectivePolicy,
    configuration_weights: Mapping[str, FrameTrainingWeight],
) -> tuple[FrameTrainingWeight, ...]:
    """Freeze per-frame property weights from the objective policy and the
    canonical label presence of each frame."""

    records: list[FrameTrainingWeight] = []
    for uid in membership:
        _record, data, local = index[uid]
        weight = configuration_weights[uid]
        energy_weight = (
            objective_policy.energy_weight if data.energies_ev is not None else 0.0
        )
        forces_weight = (
            objective_policy.forces_weight
            if data.forces_ev_per_angstrom is not None
            else 0.0
        )
        stress_weight = (
            objective_policy.stress_weight
            if data.stresses_ev_per_angstrom3 is not None
            else 0.0
        )
        records.append(
            FrameTrainingWeight(
                frame_uid=uid,
                configuration_weight=weight.configuration_weight,
                energy_weight=energy_weight,
                forces_weight=forces_weight,
                stress_weight=stress_weight,
                reason_codes=weight.reason_codes,
            )
        )
    return tuple(sorted(records, key=lambda item: item.frame_uid))


def fit_common_mace_neighbor_normalization(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    membership: Sequence[str],
    *,
    r_max: float,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
) -> float:
    """Fit the one common MACE neighbor normalization over the P2 ``P_train``.

    ``avg_num_neighbors`` is a model-construction input: pinned MACE consumes
    it when building every interaction block, so it must be a study-wide fitted
    constant rather than a function of ``T_N``.  This computes exactly what
    pinned MACE 0.3.16 computes -- the mean, over every atom that has at least
    one neighbour, of that atom's in-cutoff neighbour count -- using MACE's own
    ``get_neighborhood`` so the cutoff/periodic-image semantics are the
    dependency's and not a second approximate formula.  The result is
    independent of batching because each count is per-atom.
    """

    try:
        from mace.data.neighborhood import get_neighborhood
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
        raise TrainingDataInputError(
            "Common MACE neighbor normalization requires the pinned mace-torch dependency."
        ) from exc

    from .._frame_access import ase_atoms_for_frame

    cutoff = float(r_max)
    if not math.isfinite(cutoff) or cutoff <= 0.0:
        raise TrainingDataInputError(
            "Common MACE neighbor normalization requires a positive finite r_max."
        )
    index = (
        build_frame_array_index(frame_catalog, frame_data_by_run)
        if frame_array_index is None
        else frame_array_index
    )
    frames = tuple(str(v) for v in membership)
    if not frames:
        raise TrainingDataInputError(
            "Common MACE neighbor normalization requires a non-empty membership."
        )
    total_neighbors = 0
    total_atoms = 0
    for uid in frames:
        try:
            record, frame_data, local_index = index[uid]
        except KeyError:
            raise TrainingDataInputError(
                f"Common membership frame {uid!r} has no normalized array binding."
            ) from None
        atoms = ase_atoms_for_frame(record, frame_data, local_index)
        edge_index, _shifts, _unit_shifts, _cell = get_neighborhood(
            positions=np.asarray(atoms.positions, dtype=np.float64),
            cutoff=cutoff,
            pbc=tuple(bool(v) for v in atoms.pbc),
            cell=np.asarray(atoms.cell.array, dtype=np.float64),
        )
        receivers = np.asarray(edge_index[1], dtype=np.int64)
        # MACE counts through ``torch.unique(receivers, return_counts=True)``,
        # so an atom with no neighbour inside the cutoff contributes no sample.
        counts = np.bincount(receivers)
        counts = counts[counts > 0]
        total_neighbors += int(counts.sum())
        total_atoms += int(counts.size)
    if total_atoms == 0:
        raise TrainingDataInputError(
            "Common MACE neighbor normalization found no in-cutoff neighbours; "
            "the architecture r_max cannot describe this corpus."
        )
    value = float(total_neighbors) / float(total_atoms)
    if not math.isfinite(value) or value <= 0.0:
        raise TrainingDataInputError(
            "Common MACE neighbor normalization must be finite and positive."
        )
    return value


def realize_common_mace_architecture(
    template: Mapping[str, Any] | None,
    *,
    avg_num_neighbors: float,
) -> dict[str, Any]:
    """Bind the fitted neighbor normalization into the study-wide template.

    The template is the seed-neutral, ``N``-neutral P3 architecture; the only
    value this stamps into it is the common fitted normalization.  The result
    is the single realized architecture consumed by candidate materialization,
    real TRAIN2, and EVAL2 reconstruction alike.
    """

    from ..model_features import canonicalize_mace_candidate_architecture

    resolved = canonicalize_mace_candidate_architecture(template)
    resolved["avg_num_neighbors"] = float(avg_num_neighbors)
    return canonicalize_mace_candidate_architecture(resolved)


@dataclass(frozen=True, slots=True)
class TargetSizeCommonPreparation:
    """One canonical deterministic fitted preparation per P2 experiment.

    All fitted quantities consumed by candidate training are frozen here once
    over the common membership (normally ``P_train``): atomic references (E0),
    deterministic per-frame configuration weights, and per-frame property
    weights.  The preparation binds the accepted P2 aggregate lineage and the
    seed-neutral common training policy, and carries no candidate-varying or
    evaluation-side state.
    """

    experiment_definition_digest: str
    frame_authority_digest: str
    neutral_statistical_base_digest: str
    common_training_policy_digest: str
    common_membership: tuple[str, ...]
    common_membership_digest: str
    fitted_atomic_references: CommonAtomicReferenceFit
    fitted_frame_weights: tuple[FrameTrainingWeight, ...]
    fitted_weights_digest: str
    harness_validation_membership: tuple[str, ...]
    harness_validation_membership_digest: str
    realized_mace_architecture: Mapping[str, Any]

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "common_training_policy_digest",
            "common_membership_digest",
            "fitted_weights_digest",
            "harness_validation_membership_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        membership = tuple(str(v) for v in self.common_membership)
        if not membership or len(set(membership)) != len(membership):
            raise TrainingDataInputError(
                "Common preparation requires a unique non-empty membership."
            )
        if digest({"frame_uids": list(membership)}) != self.common_membership_digest:
            raise TrainingDataInputError(
                "Common membership does not match its digest."
            )
        weights = tuple(self.fitted_frame_weights)
        if tuple(item.frame_uid for item in weights) != tuple(
            sorted(membership)
        ):
            raise TrainingDataInputError(
                "Common fitted weights must cover exactly the common membership in canonical order."
            )
        if (
            digest(
                {"frame_weights": [item.to_dict() for item in weights]}
            )
            != self.fitted_weights_digest
        ):
            raise TrainingDataInputError(
                "Common fitted weights do not match their digest."
            )
        harness = tuple(str(v) for v in self.harness_validation_membership)
        if (
            not harness
            or len(set(harness)) != len(harness)
            or any(v not in membership for v in harness)
        ):
            raise TrainingDataInputError(
                "Harness-validation membership must be a non-empty subset of the common membership."
            )
        if (
            digest({"frame_uids": list(harness)})
            != self.harness_validation_membership_digest
        ):
            raise TrainingDataInputError(
                "Harness-validation membership does not match its digest."
            )
        from ..model_features import canonicalize_mace_candidate_architecture

        try:
            architecture = canonicalize_mace_candidate_architecture(
                self.realized_mace_architecture
            )
        except TrainingDataInputError as exc:
            raise TrainingDataInputError(
                f"Common preparation carries an unrealizable MACE architecture: {exc}"
            ) from exc
        object.__setattr__(self, "common_membership", membership)
        object.__setattr__(self, "fitted_frame_weights", weights)
        object.__setattr__(self, "harness_validation_membership", harness)
        object.__setattr__(self, "realized_mace_architecture", architecture)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_COMMON_PREPARATION_SCHEMA,
            "experiment_definition_digest": self.experiment_definition_digest,
            "frame_authority_digest": self.frame_authority_digest,
            "neutral_statistical_base_digest": self.neutral_statistical_base_digest,
            "common_training_policy_digest": self.common_training_policy_digest,
            "common_membership": list(self.common_membership),
            "common_membership_digest": self.common_membership_digest,
            "fitted_atomic_references": self.fitted_atomic_references.to_dict(),
            "fitted_frame_weights": [
                item.to_dict() for item in self.fitted_frame_weights
            ],
            "fitted_weights_digest": self.fitted_weights_digest,
            "harness_validation_membership": list(self.harness_validation_membership),
            "harness_validation_membership_digest": (
                self.harness_validation_membership_digest
            ),
            # The realized architecture carries the one common fitted MACE
            # neighbor normalization, so a change to model construction changes
            # this digest and therefore the whole P3 execution identity.
            "realized_mace_architecture": dict(self.realized_mace_architecture),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def common_avg_num_neighbors(self) -> float:
        """The one study-wide MACE neighbor normalization."""

        return float(self.realized_mace_architecture["avg_num_neighbors"])

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> TargetSizeCommonPreparation:
        if payload.get("schema") != TARGET_SIZE_COMMON_PREPARATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size common-preparation schema."
            )
        result = cls(
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            frame_authority_digest=str(payload["frame_authority_digest"]),
            neutral_statistical_base_digest=str(
                payload["neutral_statistical_base_digest"]
            ),
            common_training_policy_digest=str(
                payload["common_training_policy_digest"]
            ),
            common_membership=tuple(
                str(v) for v in payload["common_membership"]
            ),
            common_membership_digest=str(payload["common_membership_digest"]),
            fitted_atomic_references=CommonAtomicReferenceFit.from_dict(
                payload["fitted_atomic_references"]
            ),
            fitted_frame_weights=tuple(
                FrameTrainingWeight.from_dict(item)
                for item in payload["fitted_frame_weights"]
            ),
            fitted_weights_digest=str(payload["fitted_weights_digest"]),
            harness_validation_membership=tuple(
                str(v) for v in payload["harness_validation_membership"]
            ),
            harness_validation_membership_digest=str(
                payload["harness_validation_membership_digest"]
            ),
            realized_mace_architecture=payload["realized_mace_architecture"],
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size common-preparation digest mismatch."
            )
        return result

    def validate_against_aggregate(
        self, aggregate: TargetSizeStatisticalAggregate
    ) -> None:
        """Fail closed unless this preparation is the exact common preparation
        of the supplied accepted P2 aggregate."""

        definition = aggregate.definition
        if self.experiment_definition_digest != definition.content_digest:
            raise TrainingDataInputError(
                "Common preparation binds a different experiment definition."
            )
        if self.frame_authority_digest != aggregate.frame_authority_digest:
            raise TrainingDataInputError(
                "Common preparation frame-authority lineage mismatch."
            )
        if (
            self.neutral_statistical_base_digest
            != aggregate.neutral_statistical_base_digest
        ):
            raise TrainingDataInputError(
                "Common preparation neutral-base lineage mismatch."
            )
        if self.common_membership != tuple(aggregate.split.training_frame_uids):
            raise TrainingDataInputError(
                "Common preparation membership is not the exact P2 P_train."
            )
        if (
            self.fitted_atomic_references.membership_digest
            != self.common_membership_digest
        ):
            raise TrainingDataInputError(
                "Common atomic-reference fit is not bound to the common membership."
            )


def build_target_size_common_preparation(
    aggregate: TargetSizeStatisticalAggregate,
    *,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    policy: TargetSizeCommonTrainingPolicy | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    foundation_prediction_energy_by_frame: Mapping[str, float] | None = None,
    foundation_reference_energies: Mapping[int, float] | None = None,
    mace_architecture: Mapping[str, Any] | None = None,
) -> TargetSizeCommonPreparation:
    """Build the one canonical common preparation for a P2 experiment.

    The common fit consumes only P1/P2-authorized training-side data: the
    exact ``P_train`` membership, canonical labels, composition counts, and
    the fixed common training policy.  It never consumes M-ladder/CV/held-out
    labels, optimizer seeds, candidate sizes, or candidate outcomes.
    """

    from ..model_features import canonicalize_mace_candidate_architecture

    active = TargetSizeCommonTrainingPolicy() if policy is None else policy
    definition = aggregate.definition
    membership = tuple(aggregate.split.training_frame_uids)
    index = (
        build_frame_array_index(frame_catalog, frame_data_by_run)
        if frame_array_index is None
        else frame_array_index
    )
    atomic_references = fit_common_atomic_reference_energies(
        frame_catalog,
        frame_data_by_run,
        membership,
        policy=active.atomic_reference_policy,
        frame_array_index=index,
        foundation_prediction_energy_by_frame=foundation_prediction_energy_by_frame,
        foundation_reference_energies=foundation_reference_energies,
        foundation_checkpoint_digest=active.foundation_checkpoint_digest,
        foundation_identity_digest=active.foundation_checkpoint_digest,
    )
    configuration_weights = fit_common_configuration_weights(
        aggregate.population,
        membership,
        policy=active.configuration_weight_policy,
    )
    weight_by_uid = {item.frame_uid: item for item in configuration_weights}
    fitted_weights = _fitted_frame_weights(
        index,
        membership,
        objective_policy=active.objective_policy,
        configuration_weights=weight_by_uid,
    )
    harness_count = active.harness_validation_frame_count
    if harness_count > len(membership):
        raise TrainingDataInputError(
            "Fixed harness-validation size exceeds the common training membership."
        )
    harness_membership = tuple(sorted(membership)[:harness_count])
    # One seed-neutral, N-neutral MACE construction identity for the whole
    # study: the architecture template is resolved once here and its neighbor
    # normalization is fitted once over the exact P2 P_train, so no candidate
    # ever refits a model-construction input.
    template = canonicalize_mace_candidate_architecture(mace_architecture)
    realized_architecture = realize_common_mace_architecture(
        template,
        avg_num_neighbors=fit_common_mace_neighbor_normalization(
            frame_catalog,
            frame_data_by_run,
            membership,
            r_max=float(template["r_max"]),
            frame_array_index=index,
        ),
    )
    return TargetSizeCommonPreparation(
        experiment_definition_digest=definition.content_digest,
        frame_authority_digest=aggregate.frame_authority_digest,
        neutral_statistical_base_digest=aggregate.neutral_statistical_base_digest,
        common_training_policy_digest=active.content_digest,
        common_membership=membership,
        common_membership_digest=digest({"frame_uids": list(membership)}),
        fitted_atomic_references=atomic_references,
        fitted_frame_weights=fitted_weights,
        fitted_weights_digest=digest(
            {"frame_weights": [item.to_dict() for item in fitted_weights]}
        ),
        harness_validation_membership=harness_membership,
        harness_validation_membership_digest=digest(
            {"frame_uids": list(harness_membership)}
        ),
        realized_mace_architecture=realized_architecture,
    )


@dataclass(frozen=True, slots=True)
class TargetSizeCandidatePreparation:
    """Exact selection-only projection of the common fitted state onto ``T_N``.

    Every fitted value is byte-identical to the common preparation; only the
    membership is projected.  No refitting, renormalization, clipping, or
    rebalancing happens here.
    """

    target_size: int
    training_order_digest: str
    candidate_membership: tuple[str, ...]
    candidate_membership_digest: str
    common_preparation_digest: str
    projected_atomic_reference_digest: str
    projected_frame_weights: tuple[FrameTrainingWeight, ...]
    projected_weights_digest: str

    def __post_init__(self) -> None:
        target_size = _positive_int(self.target_size, name="target_size")
        object.__setattr__(self, "target_size", target_size)
        object.__setattr__(
            self,
            "training_order_digest",
            validate_digest(self.training_order_digest, name="training_order_digest"),
        )
        membership = tuple(str(v) for v in self.candidate_membership)
        if len(membership) != target_size or len(set(membership)) != len(membership):
            raise TrainingDataInputError(
                "Candidate preparation membership must have exactly target_size unique frames."
            )
        if (
            target_training_prefix_digest(
                self.training_order_digest, target_size, membership
            )
            != self.candidate_membership_digest
        ):
            raise TrainingDataInputError(
                "Candidate preparation membership does not match its digest."
            )
        weights = tuple(self.projected_frame_weights)
        if tuple(item.frame_uid for item in weights) != tuple(sorted(membership)):
            raise TrainingDataInputError(
                "Projected weights must cover exactly the candidate membership in canonical order."
            )
        if (
            digest({"frame_weights": [item.to_dict() for item in weights]})
            != self.projected_weights_digest
        ):
            raise TrainingDataInputError(
                "Projected weights do not match their digest."
            )
        object.__setattr__(self, "candidate_membership", membership)
        object.__setattr__(self, "projected_frame_weights", weights)

    def frame_weight_table(self) -> FrameTrainingWeightTable:
        return FrameTrainingWeightTable.from_records(self.projected_frame_weights)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_CANDIDATE_PREPARATION_SCHEMA,
            "target_size": self.target_size,
            "training_order_digest": self.training_order_digest,
            "candidate_membership": list(self.candidate_membership),
            "candidate_membership_digest": self.candidate_membership_digest,
            "common_preparation_digest": self.common_preparation_digest,
            "projected_atomic_reference_digest": (
                self.projected_atomic_reference_digest
            ),
            "projected_frame_weights": [
                item.to_dict() for item in self.projected_frame_weights
            ],
            "projected_weights_digest": self.projected_weights_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCandidatePreparation:
        if payload.get("schema") != TARGET_SIZE_CANDIDATE_PREPARATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size candidate-preparation schema."
            )
        result = cls(
            target_size=int(payload["target_size"]),
            training_order_digest=str(payload["training_order_digest"]),
            candidate_membership=tuple(
                str(v) for v in payload["candidate_membership"]
            ),
            candidate_membership_digest=str(payload["candidate_membership_digest"]),
            common_preparation_digest=str(payload["common_preparation_digest"]),
            projected_atomic_reference_digest=str(
                payload["projected_atomic_reference_digest"]
            ),
            projected_frame_weights=tuple(
                FrameTrainingWeight.from_dict(item)
                for item in payload["projected_frame_weights"]
            ),
            projected_weights_digest=str(payload["projected_weights_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size candidate-preparation digest mismatch."
            )
        return result


def project_target_size_candidate_preparation(
    common: TargetSizeCommonPreparation,
    definition: Any,
    target_size: int,
) -> TargetSizeCandidatePreparation:
    """Project the common fitted state onto the exact P2 ``T_N``.

    Membership comes only from ``definition.candidate_membership(N)``; callers
    cannot supply an alternative same-sized list.  Fitted weights and atomic
    references are selected verbatim and never recomputed or renormalized.
    """

    if common.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError(
            "Candidate projection requires the bound experiment definition."
        )
    qualified = definition.qualified_candidate_sizes
    if target_size not in qualified:
        raise TrainingDataInputError(
            "Candidate projection accepts only qualified candidate sizes."
        )
    membership = tuple(definition.candidate_membership(target_size))
    expected_digest = target_training_prefix_digest(
        definition.training_order.content_digest, target_size, membership
    )
    if expected_digest != definition.training_order.candidate_digest(target_size):
        raise TrainingDataInputError(
            "Candidate membership does not match the P2 membership digest."
        )
    # ``T_N`` is the exact P2 ``pi_train`` prefix.  ``pi_train`` is a separate
    # condition-balanced order over the same frames as ``P_train``, so the
    # candidate is a subset of the common membership but is not in general a
    # subsequence of its storage order.  Containment is the whole requirement:
    # fitted values are selected by frame UID, never by position.
    common_members = set(common.common_membership)
    if any(uid not in common_members for uid in membership):
        raise TrainingDataInputError(
            "Candidate membership is not contained in the common preparation membership."
        )
    weight_by_uid = {item.frame_uid: item for item in common.fitted_frame_weights}
    projected_weights = tuple(
        weight_by_uid[uid] for uid in sorted(membership)
    )
    return TargetSizeCandidatePreparation(
        target_size=target_size,
        training_order_digest=definition.training_order.content_digest,
        candidate_membership=membership,
        candidate_membership_digest=expected_digest,
        common_preparation_digest=common.content_digest,
        projected_atomic_reference_digest=common.fitted_atomic_references.content_digest,
        projected_frame_weights=projected_weights,
        projected_weights_digest=digest(
            {"frame_weights": [item.to_dict() for item in projected_weights]}
        ),
    )


def fit_membership_frame_training_weights(
    frame_array_index: Mapping[str, tuple[Any, Any, int]],
    membership: Sequence[str],
    *,
    objective_policy: TrainingObjectivePolicy,
    configuration_weights: Mapping[str, FrameTrainingWeight],
) -> tuple[FrameTrainingWeight, ...]:
    """Freeze per-frame training weights over one exact membership.

    This is the shared objective-weighting seam.  The common P3 preparation and
    any downstream fold-local or final-production preparation produce their
    weights through this one recipe, so that "the same method" means the same
    arithmetic applied to whatever membership the caller is authorized to fit.
    """

    return _fitted_frame_weights(
        frame_array_index,
        membership,
        objective_policy=objective_policy,
        configuration_weights=configuration_weights,
    )


__all__ = [
    "CommonAtomicReferenceFit",
    "EVAL2_TARGET_METRIC_POLICY_DIGEST",
    "REPLAY_EXPOSURE_NONE_DIGEST",
    "TARGET_SIZE_CANDIDATE_PREPARATION_SCHEMA",
    "TARGET_SIZE_COMMON_ATOMIC_REFERENCE_SCHEMA",
    "TARGET_SIZE_COMMON_POLICY_SCHEMA",
    "TARGET_SIZE_COMMON_PREPARATION_SCHEMA",
    "TargetSizeCandidatePreparation",
    "TargetSizeCommonPreparation",
    "TargetSizeCommonTrainingPolicy",
    "build_target_size_common_preparation",
    "fit_common_atomic_reference_energies",
    "fit_common_configuration_weights",
    "fit_membership_frame_training_weights",
    "project_target_size_candidate_preparation",
]
