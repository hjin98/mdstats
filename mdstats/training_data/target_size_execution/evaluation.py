"""P3-D direct exact-checkpoint EVAL2 on exact P2 M_i memberships.

This layer carries the version-agnostic direct target-size EVAL2 role
authority.  It authenticates exactly one authorized boundary checkpoint per
ordinary successful ``(N, seed, n_i, M_i)`` through the bound
:class:`TargetSizeBoundaryState`, consumes the exact P2 evaluation membership
and the canonical P1 split-exclusion component projection, reuses the
existing EVAL2 metric engine
(:func:`mdstats.training_data.eval2.eval2_target_metrics_from_prediction_view`),
and transfers only the frozen global target force-component RMSE into the P2
``TargetSizeBoundaryMetric``::

    target_force_rmse_mev_per_a
        = force_component_rmse_ev_per_angstrom * 1000.0

No historical shortlist, rescue checkpoint, replay admissibility, bootstrap
comparison, generic MACE-validation score, or checkpoint-selection machinery
is reachable from this layer: the role binds exactly one authenticated
boundary state, and every evaluation frame carries its full M3/P1
split-exclusion component identity (M1/M2 retain their parent M3 identities).
"""

from __future__ import annotations

from dataclasses import dataclass
    
import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..eval2 import (
    EVAL2_NUMERICAL_FAILURE_CODES,
    Eval2NumericalEvaluationError,
    Eval2TargetMetricRecord,
    eval2_target_metrics_from_prediction_view,
)
from ..neutral_substrate import (
    NeutralSplitExclusionEvidence,
    frame_split_exclusion_component_membership,
)
from ..target_size_experiment import (
    NumericalFailureKind,
    TargetSizeBoundaryMetric,
    TargetSizeExperimentDefinition,
    TargetSizeNumericalFailure,
    TargetSizeStatisticalAggregate,
)
from .candidate import TargetSizeCandidateTrajectory
from .execution import (
    TargetSizeBoundaryState,
    target_size_evaluation_membership_digest_for_boundary,
    target_size_evaluation_size_for_boundary,
)
from .schedule import TargetSizeScreenSchedule

TARGET_SIZE_EVAL2_ROLE_SCHEMA = "mdstats.target-size.eval2-role.v1"
TARGET_SIZE_EVAL2_PREDICTION_SCHEMA = "mdstats.target-size.eval2-prediction.v1"

# Authenticated EVAL2 failure-code translation (lossless mapping).
_EVAL_PREDICTION_FAILURE_CODES = frozenset(
    {
        "eval_nonfinite_energy_prediction",
        "eval_nonfinite_force_prediction",
        "eval_nonfinite_stress_prediction",
    }
)
_EVAL_FAILURE_KINDS = {
    **{
        code: NumericalFailureKind.EVAL_NONFINITE_PREDICTION
        for code in sorted(_EVAL_PREDICTION_FAILURE_CODES)
    },
    "eval_nonfinite_target_metric": NumericalFailureKind.EVAL_NONFINITE_TARGET_METRIC,
}


def target_size_population_correlation_blocks(
    aggregate: TargetSizeStatisticalAggregate,
    split_exclusion_evidence: NeutralSplitExclusionEvidence,
) -> dict[str, str]:
    """Per-frame canonical correlation-block identity over the population.

    The mapping is computed through the one shared P1 component projection
    and authenticated byte-for-byte against the accepted P2 split: the
    derived component identities must equal the split's
    ``constraint_component_digests``.  Frames of every M rung keep their full
    population/M3 parent component identity; no prefix-local recomputation
    may occur.
    """

    if (
        split_exclusion_evidence.content_digest
        != aggregate.split.split_exclusion_evidence_digest
    ):
        raise TrainingDataInputError(
            "Correlation-block evidence does not bind the accepted P2 split."
        )
    assignment = frame_split_exclusion_component_membership(
        aggregate.population.frame_uids,
        split_exclusion_evidence,
        frame_authority_digest=aggregate.population.frame_authority_digest,
        neutral_unit_catalog_digest=aggregate.population.neutral_unit_catalog_digest,
    )
    derived = {
        component for _, component in assignment
    }
    expected = set(aggregate.split.constraint_component_digests)
    if derived != expected:
        raise TrainingDataInputError(
            "Correlation-block projection diverges from the accepted P2 split components."
        )
    return dict(assignment)


@dataclass(frozen=True, slots=True)
class TargetSizeEval2Role:
    """Direct target-size EVAL2 role: exact boundary, exact M_i, exact blocks.

    No label-domain, CV-fold, development-complement, coarse-fallback, or
    excluded-training-prefix semantics are representable in this record.
    """

    experiment_definition_digest: str
    execution_context_digest: str
    target_size: int
    optimizer_seed: int
    boundary_epoch: int
    evaluation_size: int
    evaluation_membership_digest: str
    evaluation_frame_uids: tuple[str, ...]
    correlation_block_ids: tuple[str, ...]
    boundary_state_digest: str
    trajectory_digest: str

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "execution_context_digest",
            "evaluation_membership_digest",
            "boundary_state_digest",
            "trajectory_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for name in ("target_size", "boundary_epoch", "evaluation_size"):
            value = int(getattr(self, name))
            if value <= 0:
                raise TrainingDataInputError(f"{name} must be a positive integer.")
            object.__setattr__(self, name, value)
        if (
            isinstance(self.optimizer_seed, bool)
            or not isinstance(self.optimizer_seed, int)
            or self.optimizer_seed < 0
        ):
            raise TrainingDataInputError(
                "optimizer_seed must be a nonnegative integer."
            )
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        frames = tuple(validate_digest(str(v), name="evaluation frame UID") for v in self.evaluation_frame_uids)
        if len(frames) != self.evaluation_size or len(set(frames)) != len(frames):
            raise TrainingDataInputError(
                "EVAL2 role evaluation frames must equal the exact evaluation size."
            )
        blocks = tuple(
            validate_digest(str(v), name="correlation block identity")
            for v in self.correlation_block_ids
        )
        if len(blocks) != len(frames):
            raise TrainingDataInputError(
                "EVAL2 role correlation blocks must align with evaluation frames."
            )
        object.__setattr__(self, "evaluation_frame_uids", frames)
        object.__setattr__(self, "correlation_block_ids", blocks)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_EVAL2_ROLE_SCHEMA,
            "experiment_definition_digest": self.experiment_definition_digest,
            "execution_context_digest": self.execution_context_digest,
            "target_size": self.target_size,
            "optimizer_seed": self.optimizer_seed,
            "boundary_epoch": self.boundary_epoch,
            "evaluation_size": self.evaluation_size,
            "evaluation_membership_digest": self.evaluation_membership_digest,
            "evaluation_frame_uids": list(self.evaluation_frame_uids),
            "correlation_block_ids": list(self.correlation_block_ids),
            "boundary_state_digest": self.boundary_state_digest,
            "trajectory_digest": self.trajectory_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeEval2Role:
        if payload.get("schema") != TARGET_SIZE_EVAL2_ROLE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported EVAL2 role schema.")
        result = cls(
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            execution_context_digest=str(payload["execution_context_digest"]),
            target_size=int(payload["target_size"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            evaluation_size=int(payload["evaluation_size"]),
            evaluation_membership_digest=str(payload["evaluation_membership_digest"]),
            evaluation_frame_uids=tuple(
                str(v) for v in payload["evaluation_frame_uids"]
            ),
            correlation_block_ids=tuple(
                str(v) for v in payload["correlation_block_ids"]
            ),
            boundary_state_digest=str(payload["boundary_state_digest"]),
            trajectory_digest=str(payload["trajectory_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("EVAL2 role digest mismatch.")
        return result


def build_target_size_eval2_role(
    *,
    trajectory: TargetSizeCandidateTrajectory,
    boundary_state: TargetSizeBoundaryState,
    definition: TargetSizeExperimentDefinition,
    schedule: TargetSizeScreenSchedule,
    correlation_blocks: Mapping[str, str],
) -> TargetSizeEval2Role:
    """Authenticate one direct EVAL2 role for the exact active boundary.

    The role derives every scientific element from the accepted owners: the
    paired ``M_i`` size and exact evaluation membership from P2, the boundary
    identity from the authenticated TRAIN2 boundary state, and the per-frame
    correlation blocks from the canonical P1 projection.  It accepts exactly
    one boundary checkpoint lineage; historical checkpoint selection has no
    parameter here.
    """

    if boundary_state.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "EVAL2 role boundary state belongs to a different trajectory."
        )
    if trajectory.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError(
            "EVAL2 role trajectory binds a different experiment definition."
        )
    boundary = schedule.validate_boundary_epoch(boundary_state.boundary_epoch)
    evaluation_size = target_size_evaluation_size_for_boundary(
        definition, schedule, boundary
    )
    membership = definition.evaluation_membership(evaluation_size)
    membership_digest = target_size_evaluation_membership_digest_for_boundary(
        definition, schedule, boundary
    )
    blocks: list[str] = []
    for uid in membership:
        block = correlation_blocks.get(uid)
        if block is None:
            raise TrainingDataInputError(
                "Evaluation frame lacks its full P1 split-exclusion component identity."
            )
        blocks.append(validate_digest(block, name="correlation block identity"))
    return TargetSizeEval2Role(
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=trajectory.execution_context_digest,
        target_size=trajectory.target_size,
        optimizer_seed=trajectory.optimizer_seed,
        boundary_epoch=boundary,
        evaluation_size=evaluation_size,
        evaluation_membership_digest=membership_digest,
        evaluation_frame_uids=membership,
        correlation_block_ids=tuple(blocks),
        boundary_state_digest=boundary_state.content_digest,
        trajectory_digest=trajectory.content_digest,
    )


def target_size_eval2_prediction_digest(
    role: TargetSizeEval2Role, predictions: Sequence[Any]
) -> str:
    """Deterministic identity of one prediction set bound to the role."""

    entries = []
    for prediction in predictions:
        energy = float(prediction.energy_ev)
        forces = getattr(prediction, "forces_ev_per_angstrom")
        stress = getattr(prediction, "stress_ev_per_angstrom3", None)
        entries.append(
            {
                "energy_ev": repr(energy),
                "forces": [repr(float(v)) for v in np.asarray(forces, dtype=np.float64).reshape(-1)]
                if forces is not None
                else None,
                "stress": [
                    repr(float(v))
                    for v in np.asarray(stress, dtype=np.float64).reshape(-1)
                ]
                if stress is not None
                else None,
            }
        )
    return digest(
        {
            "schema": TARGET_SIZE_EVAL2_PREDICTION_SCHEMA,
            "role_digest": role.content_digest,
            "predictions": entries,
        }
    )


def run_target_size_eval2_reduction(
    role: TargetSizeEval2Role,
    view: Any,
    predictions: Sequence[Any],
    *,
    prediction_digest: str | None = None,
) -> Eval2TargetMetricRecord:
    """Reduce the authorized boundary predictions through the EVAL2 engine.

    This calls the existing EVAL2 metric owner with the direct role identity;
    it performs no checkpoint selection and rejects any view whose population
    does not equal the exact P2 M-membership count.
    """

    if int(view.configuration_count) != len(role.evaluation_frame_uids):
        raise TrainingDataInputError(
            "EVAL2 view population does not equal the exact P2 M-membership."
        )
    if len(predictions) != len(role.evaluation_frame_uids):
        raise TrainingDataInputError(
            "EVAL2 predictions do not cover the exact P2 M-membership."
        )
    active_digest = (
        target_size_eval2_prediction_digest(role, predictions)
        if prediction_digest is None
        else validate_digest(prediction_digest, name="prediction_digest")
    )
    return eval2_target_metrics_from_prediction_view(
        view,
        predictions,
        block_ids=role.correlation_block_ids,
        target_role_digest=role.content_digest,
        prediction_digest=active_digest,
    )


def translate_target_size_eval2_failure(
    role: TargetSizeEval2Role, error: Eval2NumericalEvaluationError
) -> TargetSizeNumericalFailure:
    """Translate one authenticated EVAL2 numerical failure to P2 evidence.

    The failure binds the exact ``(N, seed, n_i, M_i)`` attempt of the role.
    Only positively authenticated EVAL2 numerical failures are translated;
    schema/shape/lineage/missing-artifact/programming/resource failures are
    ordinary execution errors and must not reach this adapter.
    """

    if error.target_role_digest != role.content_digest:
        raise TrainingDataInputError(
            "EVAL2 numerical failure does not bind this direct role."
        )
    kind = _EVAL_FAILURE_KINDS.get(error.failure_code)
    if kind is None:
        raise TrainingDataInputError(
            "Unauthenticated EVAL2 failure codes remain execution errors.  Codes: "
            f"{sorted(EVAL2_NUMERICAL_FAILURE_CODES)}"
        )
    evidence = digest(
        {
            "schema": "mdstats.target-size.eval2-failure-evidence.v1",
            "role_digest": role.content_digest,
            "failure_code": error.failure_code,
            "reason": error.reason,
            "prediction_digest": error.prediction_digest,
            "error_content_digest": error.content_digest,
        }
    )
    return TargetSizeNumericalFailure(
        experiment_definition_digest=role.experiment_definition_digest,
        execution_context_digest=role.execution_context_digest,
        target_size=role.target_size,
        optimizer_seed=role.optimizer_seed,
        boundary_epoch=role.boundary_epoch,
        evaluation_membership_digest=role.evaluation_membership_digest,
        kind=kind,
        classification_evidence_digest=evidence,
    )


def target_size_boundary_metric_from_eval2_record(
    role: TargetSizeEval2Role, record: Eval2TargetMetricRecord
) -> TargetSizeBoundaryMetric:
    """Transfer exactly the frozen global target force-component RMSE."""

    if record.target_role_digest != role.content_digest:
        raise TrainingDataInputError(
            "EVAL2 metric record does not bind this direct role."
        )
    if record.configuration_count != role.evaluation_size:
        raise TrainingDataInputError(
            "EVAL2 metric record population does not equal the exact M-size."
        )
    scalar = record.force_component_rmse_ev_per_angstrom * 1000.0
    return TargetSizeBoundaryMetric(
        experiment_definition_digest=role.experiment_definition_digest,
        execution_context_digest=role.execution_context_digest,
        target_size=role.target_size,
        optimizer_seed=role.optimizer_seed,
        boundary_epoch=role.boundary_epoch,
        evaluation_membership_digest=role.evaluation_membership_digest,
        target_force_rmse_mev_per_a=scalar,
    )


def evaluate_target_size_boundary(
    role: TargetSizeEval2Role,
    view: Any,
    predictions: Sequence[Any],
    *,
    prediction_digest: str | None = None,
) -> TargetSizeBoundaryMetric | TargetSizeNumericalFailure:
    """Evaluate exactly one authorized boundary checkpoint on exact M_i.

    Ordinary success yields the frozen P2 boundary metric; a positively
    authenticated EVAL2 numerical failure yields the corresponding P2
    numerical failure bound to this attempt.  Every other failure type is an
    execution error and propagates unchanged.
    """

    try:
        record = run_target_size_eval2_reduction(
            role, view, predictions, prediction_digest=prediction_digest
        )
    except Eval2NumericalEvaluationError as error:
        return translate_target_size_eval2_failure(role, error)
    return target_size_boundary_metric_from_eval2_record(role, record)


__all__ = [
    "TARGET_SIZE_EVAL2_PREDICTION_SCHEMA",
    "TARGET_SIZE_EVAL2_ROLE_SCHEMA",
    "TargetSizeEval2Role",
    "build_target_size_eval2_role",
    "evaluate_target_size_boundary",
    "run_target_size_eval2_reduction",
    "target_size_boundary_metric_from_eval2_record",
    "target_size_eval2_prediction_digest",
    "target_size_population_correlation_blocks",
    "translate_target_size_eval2_failure",
]
