"""P3-D direct exact-checkpoint EVAL2 on exact P2 M_i memberships.

This layer carries the version-agnostic direct target-size EVAL2 role and
prediction-evidence authorities.  It authenticates exactly one authorized
boundary checkpoint per ordinary successful ``(N, seed, n_i, M_i)`` through
the bound :class:`TargetSizeBoundaryState` or :class:`TargetSizeBoundarySnapshot`,
validates the exact P2 evaluation data authority (:class:`TargetSizeEvaluationArtifact`)
and canonical P1 correlation blocks, executes direct single-checkpoint inference,
constructs immutable :class:`TargetSizePredictionEvidence`, and reduces only
authenticated prediction evidence through the EVAL2 metric engine into
``TargetSizeBoundaryMetric``::

    target_force_rmse_mev_per_a
        = force_component_rmse_ev_per_angstrom * 1000.0

No historical shortlist, rescue checkpoint, replay admissibility, bootstrap
comparison, generic MACE-validation score, or checkpoint-selection machinery
is reachable from this layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

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
    EVALUATION_MODEL_STATE_EMA,
    EVALUATION_MODEL_STATE_LIVE,
    TargetSizeBoundarySnapshot,
    TargetSizeBoundaryState,
    target_size_evaluation_membership_digest_for_boundary,
    target_size_evaluation_size_for_boundary,
)
from .export import TargetSizeEvaluationArtifact
from .schedule import TargetSizeScreenSchedule

TARGET_SIZE_EVAL2_ROLE_SCHEMA = "mdstats.target-size.eval2-role.v1"
TARGET_SIZE_EVAL2_PREDICTION_SCHEMA = "mdstats.target-size.eval2-prediction.v1"
TARGET_SIZE_PREDICTION_EVIDENCE_SCHEMA = (
    "mdstats.target-size.prediction-evidence.v1"
)

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
    "eval_nonfinite_target_metric": (
        NumericalFailureKind.EVAL_NONFINITE_TARGET_METRIC
    ),
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
    derived = {component for _, component in assignment}
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
    evaluation_data_digest: str | None = None

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
        if self.evaluation_data_digest is not None:
            object.__setattr__(
                self,
                "evaluation_data_digest",
                validate_digest(
                    self.evaluation_data_digest, name="evaluation_data_digest"
                ),
            )
        for name in ("target_size", "boundary_epoch", "evaluation_size"):
            value = int(getattr(self, name))
            if value <= 0:
                raise TrainingDataInputError(
                    f"{name} must be a positive integer."
                )
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
        frames = tuple(
            validate_digest(str(v), name="evaluation frame UID")
            for v in self.evaluation_frame_uids
        )
        if (
            len(frames) != self.evaluation_size
            or len(set(frames)) != len(frames)
        ):
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
        payload: dict[str, Any] = {
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
        if self.evaluation_data_digest is not None:
            payload["evaluation_data_digest"] = self.evaluation_data_digest
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeEval2Role:
        if payload.get("schema") != TARGET_SIZE_EVAL2_ROLE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported EVAL2 role schema."
            )
        result = cls(
            experiment_definition_digest=str(
                payload["experiment_definition_digest"]
            ),
            execution_context_digest=str(payload["execution_context_digest"]),
            target_size=int(payload["target_size"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            evaluation_size=int(payload["evaluation_size"]),
            evaluation_membership_digest=str(
                payload["evaluation_membership_digest"]
            ),
            evaluation_frame_uids=tuple(
                str(v) for v in payload["evaluation_frame_uids"]
            ),
            correlation_block_ids=tuple(
                str(v) for v in payload["correlation_block_ids"]
            ),
            boundary_state_digest=str(payload["boundary_state_digest"]),
            trajectory_digest=str(payload["trajectory_digest"]),
            evaluation_data_digest=(
                None
                if payload.get("evaluation_data_digest") is None
                else str(payload["evaluation_data_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("EVAL2 role digest mismatch.")
        return result


def build_target_size_eval2_role(
    *,
    trajectory: TargetSizeCandidateTrajectory,
    boundary_state: TargetSizeBoundaryState | TargetSizeBoundarySnapshot,
    definition: TargetSizeExperimentDefinition,
    schedule: TargetSizeScreenSchedule,
    correlation_blocks: Mapping[str, str],
    evaluation_data: TargetSizeEvaluationArtifact | None = None,
) -> TargetSizeEval2Role:
    """Authenticate one direct EVAL2 role for the exact active boundary."""

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
    eval_data_digest = None
    if evaluation_data is not None:
        if (
            evaluation_data.experiment_definition_digest
            != definition.content_digest
        ):
            raise TrainingDataInputError(
                "Evaluation data binds a different experiment definition."
            )
        if evaluation_data.evaluation_size != evaluation_size:
            raise TrainingDataInputError(
                "Evaluation data size does not match the active boundary."
            )
        if evaluation_data.evaluation_frame_uids != membership:
            raise TrainingDataInputError(
                "Evaluation data frame UIDs do not match P2 evaluation membership."
            )
        if evaluation_data.evaluation_membership_digest != membership_digest:
            raise TrainingDataInputError(
                "Evaluation data membership digest does not match P2 evaluation order."
            )
        eval_data_digest = evaluation_data.content_digest

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
        evaluation_data_digest=eval_data_digest,
    )


@dataclass(frozen=True, slots=True)
class TargetSizePredictionEntry:
    """Canonical single-frame prediction entry covering energy/forces/stress."""

    energy_ev: float
    forces_ev_per_angstrom: np.ndarray | Sequence[Sequence[float]] | None
    stress_ev_per_angstrom3: np.ndarray | Sequence[Sequence[float]] | None = None

    def __post_init__(self) -> None:
        energy = float(self.energy_ev)
        object.__setattr__(self, "energy_ev", energy)
        if self.forces_ev_per_angstrom is not None:
            forces = np.asarray(self.forces_ev_per_angstrom, dtype=np.float64)
            object.__setattr__(self, "forces_ev_per_angstrom", forces)
        if self.stress_ev_per_angstrom3 is not None:
            stress = np.asarray(self.stress_ev_per_angstrom3, dtype=np.float64)
            object.__setattr__(self, "stress_ev_per_angstrom3", stress)

    def _payload(self) -> dict[str, Any]:
        return {
            "energy_ev": repr(self.energy_ev),
            "forces_ev_per_angstrom": (
                [
                    [repr(float(c)) for c in row]
                    for row in np.asarray(
                        self.forces_ev_per_angstrom, dtype=np.float64
                    )
                ]
                if self.forces_ev_per_angstrom is not None
                else None
            ),
            "stress_ev_per_angstrom3": (
                [
                    [repr(float(c)) for c in row]
                    for row in np.asarray(
                        self.stress_ev_per_angstrom3, dtype=np.float64
                    )
                ]
                if self.stress_ev_per_angstrom3 is not None
                else None
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return self._payload()

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> TargetSizePredictionEntry:
        forces_raw = payload.get("forces_ev_per_angstrom")
        stress_raw = payload.get("stress_ev_per_angstrom3")
        forces = (
            np.asarray(
                [[float(c) for c in row] for row in forces_raw],
                dtype=np.float64,
            )
            if forces_raw is not None
            else None
        )
        stress = (
            np.asarray(
                [[float(c) for c in row] for row in stress_raw],
                dtype=np.float64,
            )
            if stress_raw is not None
            else None
        )
        return cls(
            energy_ev=float(payload["energy_ev"]),
            forces_ev_per_angstrom=forces,
            stress_ev_per_angstrom3=stress,
        )


@dataclass(frozen=True, slots=True)
class TargetSizePredictionEvidence:
    """Authenticated prediction evidence binding direct checkpoint inference origin."""

    role_digest: str
    trajectory_digest: str
    boundary_state_digest: str
    boundary_epoch: int
    evaluation_model_state: str
    evaluated_model_state_digest: str
    evaluation_data_digest: str
    evaluation_membership_digest: str
    evaluation_size: int
    prediction_count: int
    prediction_payload_digest: str
    predictions: tuple[TargetSizePredictionEntry, ...]
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "role_digest",
            "trajectory_digest",
            "boundary_state_digest",
            "evaluated_model_state_digest",
            "evaluation_data_digest",
            "evaluation_membership_digest",
            "prediction_payload_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for name in ("boundary_epoch", "evaluation_size", "prediction_count"):
            val = int(getattr(self, name))
            if val <= 0:
                raise TrainingDataInputError(
                    f"{name} must be a positive integer."
                )
            object.__setattr__(self, name, val)
        if self.evaluation_model_state not in (
            EVALUATION_MODEL_STATE_LIVE,
            EVALUATION_MODEL_STATE_EMA,
        ):
            raise TrainingDataInputError(
                "Prediction evidence evaluation model state must be 'live' or 'ema'."
            )
        preds = tuple(self.predictions)
        if (
            len(preds) != self.prediction_count
            or len(preds) != self.evaluation_size
        ):
            raise TrainingDataInputError(
                "Prediction count does not equal exact evaluation size."
            )
        object.__setattr__(self, "predictions", preds)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_PREDICTION_EVIDENCE_SCHEMA,
            "role_digest": self.role_digest,
            "trajectory_digest": self.trajectory_digest,
            "boundary_state_digest": self.boundary_state_digest,
            "boundary_epoch": self.boundary_epoch,
            "evaluation_model_state": self.evaluation_model_state,
            "evaluated_model_state_digest": self.evaluated_model_state_digest,
            "evaluation_data_digest": self.evaluation_data_digest,
            "evaluation_membership_digest": self.evaluation_membership_digest,
            "evaluation_size": self.evaluation_size,
            "prediction_count": self.prediction_count,
            "prediction_payload_digest": self.prediction_payload_digest,
            "predictions": [item.to_dict() for item in self.predictions],
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
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> TargetSizePredictionEvidence:
        if payload.get("schema") != TARGET_SIZE_PREDICTION_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size prediction evidence schema."
            )
        result = cls(
            role_digest=str(payload["role_digest"]),
            trajectory_digest=str(payload["trajectory_digest"]),
            boundary_state_digest=str(payload["boundary_state_digest"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            evaluation_model_state=str(payload["evaluation_model_state"]),
            evaluated_model_state_digest=str(
                payload["evaluated_model_state_digest"]
            ),
            evaluation_data_digest=str(payload["evaluation_data_digest"]),
            evaluation_membership_digest=str(
                payload["evaluation_membership_digest"]
            ),
            evaluation_size=int(payload["evaluation_size"]),
            prediction_count=int(payload["prediction_count"]),
            prediction_payload_digest=str(payload["prediction_payload_digest"]),
            predictions=tuple(
                TargetSizePredictionEntry.from_dict(item)
                for item in payload["predictions"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size prediction evidence digest mismatch."
            )
        return result


def target_size_eval2_prediction_digest(
    role: TargetSizeEval2Role, predictions: Sequence[Any]
) -> str:
    """Deterministic identity of one prediction set bound to the role."""

    entries = []
    for prediction in predictions:
        energy = float(prediction.energy_ev)
        forces = getattr(prediction, "forces_ev_per_angstrom", None)
        stress = getattr(prediction, "stress_ev_per_angstrom3", None)
        entries.append(
            {
                "energy_ev": repr(energy),
                "forces": (
                    [
                        repr(float(v))
                        for v in np.asarray(
                            forces, dtype=np.float64
                        ).reshape(-1)
                    ]
                    if forces is not None
                    else None
                ),
                "stress": (
                    [
                        repr(float(v))
                        for v in np.asarray(
                            stress, dtype=np.float64
                        ).reshape(-1)
                    ]
                    if stress is not None
                    else None
                ),
            }
        )
    return digest(
        {
            "schema": TARGET_SIZE_EVAL2_PREDICTION_SCHEMA,
            "role_digest": role.content_digest,
            "predictions": entries,
        }
    )


def run_target_size_direct_boundary_inference(
    *,
    trajectory: TargetSizeCandidateTrajectory,
    materialization: Any,
    boundary_state: TargetSizeBoundaryState | TargetSizeBoundarySnapshot,
    role: TargetSizeEval2Role,
    evaluation_data: TargetSizeEvaluationArtifact,
    root_directory: str | Path,
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]]
    | None = None,
) -> TargetSizePredictionEvidence:
    """Real semantic owner for single exact boundary checkpoint inference."""
    if materialization.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Candidate materialization belongs to a different trajectory."
        )
    if boundary_state.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Boundary state belongs to a different candidate trajectory."
        )
    if role.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Direct EVAL2 role belongs to a different candidate trajectory."
        )
    if role.boundary_state_digest != boundary_state.content_digest:
        raise TrainingDataInputError(
            "Direct EVAL2 role binds a different boundary state."
        )
    if role.experiment_definition_digest != trajectory.experiment_definition_digest:
        raise TrainingDataInputError(
            "Direct EVAL2 role binds a different experiment definition."
        )
    if role.execution_context_digest != trajectory.execution_context_digest:
        raise TrainingDataInputError(
            "Direct EVAL2 role binds a different execution context."
        )
    if (
        role.target_size != trajectory.target_size
        or role.optimizer_seed != trajectory.optimizer_seed
    ):
        raise TrainingDataInputError(
            "Direct EVAL2 role matrix position does not match trajectory."
        )
    if boundary_state.boundary_epoch != role.boundary_epoch:
        raise TrainingDataInputError(
            "Boundary state epoch does not match direct EVAL2 role boundary."
        )
    if (
        boundary_state.rung_runtime_summary.completed_epochs
        != role.boundary_epoch
    ):
        raise TrainingDataInputError(
            "Boundary state runtime summary completed epochs mismatch."
        )
    if role.evaluation_size != evaluation_data.evaluation_size:
        raise TrainingDataInputError(
            "Direct EVAL2 role evaluation size does not match evaluation data."
        )
    if role.evaluation_frame_uids != evaluation_data.evaluation_frame_uids:
        raise TrainingDataInputError(
            "Direct EVAL2 role frame UIDs do not match evaluation data."
        )
    if (
        role.evaluation_membership_digest
        != evaluation_data.evaluation_membership_digest
    ):
        raise TrainingDataInputError(
            "Direct EVAL2 role membership digest does not match evaluation data."
        )
    if (
        role.evaluation_data_digest is not None
        and role.evaluation_data_digest != evaluation_data.content_digest
    ):
        raise TrainingDataInputError(
            "Direct EVAL2 role binds a different evaluation data authority."
        )
    if (
        boundary_state.evaluation_model_state
        != trajectory.evaluation_model_state
    ):
        raise TrainingDataInputError(
            "Boundary state evaluation model-state mismatch."
        )

    if trajectory.evaluation_model_state == EVALUATION_MODEL_STATE_LIVE:
        evaluated_model_state_digest = (
            boundary_state.rung_runtime_summary.live_parameter_digest
        )
    elif trajectory.evaluation_model_state == EVALUATION_MODEL_STATE_EMA:
        if boundary_state.rung_runtime_summary.ema_state_digest is None:
            raise TrainingDataInputError(
                "EMA trajectory convention requires authenticated EMA boundary state."
            )
        evaluated_model_state_digest = (
            boundary_state.rung_runtime_summary.ema_state_digest
        )
    else:
        raise TrainingDataInputError(
            f"Unsupported evaluation model state: {trajectory.evaluation_model_state!r}"
        )

    try:
        import ase.io
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for inference.") from exc

    target_path = Path(root_directory) / evaluation_data.relative_path
    if not target_path.is_file():
        raise TrainingDataInputError(
            f"Evaluation artifact file is missing: {target_path}"
        )
    atoms_list = ase.io.read(str(target_path), index=":")
    if len(atoms_list) != evaluation_data.evaluation_size:
        raise TrainingDataInputError(
            "Evaluation artifact frame count mismatch."
        )

    if inference_evaluator is not None:
        raw_predictions = inference_evaluator(boundary_state, atoms_list)
    else:
        # Default MACE CPU inference from checkpoint
        from types import SimpleNamespace
        import torch

        if isinstance(boundary_state, TargetSizeBoundarySnapshot):
            ckpt_dir = Path(root_directory) / boundary_state.snapshot_relative_dir
        else:
            ckpt_dir = Path(root_directory)
        summary = boundary_state.rung_runtime_summary
        raw_checkpoint_path = ckpt_dir / summary.raw_checkpoint_name if hasattr(summary, "raw_checkpoint_name") else ckpt_dir / f"epoch-{summary.raw_checkpoint_epoch}.pt"
        if not raw_checkpoint_path.is_file():
            # Search for matching epoch checkpoint
            candidates = list(ckpt_dir.glob(f"*epoch*{summary.raw_checkpoint_epoch}*.pt"))
            if not candidates:
                raise TrainingDataInputError(f"Raw checkpoint not found for epoch {summary.raw_checkpoint_epoch} in {ckpt_dir}")
            raw_checkpoint_path = candidates[0]
        model = torch.load(raw_checkpoint_path, map_location="cpu", weights_only=False)
        if trajectory.evaluation_model_state == EVALUATION_MODEL_STATE_EMA:
            companion_path = ckpt_dir / "train2_runtime.pt"
            if not companion_path.is_file():
                raise TrainingDataInputError(f"Continuation companion missing in {ckpt_dir}")
            companion = torch.load(companion_path, map_location="cpu", weights_only=False)
            ema_state = companion.get("ema_state")
            if ema_state is not None and "shadow_params" in ema_state:
                for p, shadow in zip(model.parameters(), ema_state["shadow_params"]):
                    p.data.copy_(shadow)
        from mace.calculators import MACECalculator
        calc = MACECalculator(models=[model], device="cpu", default_dtype="float64")
        raw_predictions = []
        for atoms in atoms_list:
            local = atoms.copy()
            local.calc = calc
            e = float(local.get_potential_energy())
            f = np.asarray(local.get_forces(), dtype=np.float64)
            s = None
            try:
                s = np.asarray(local.get_stress(voigt=False), dtype=np.float64)
            except Exception:
                s = None
            raw_predictions.append(SimpleNamespace(energy_ev=e, forces_ev_per_angstrom=f, stress_ev_per_angstrom3=s))

    if len(raw_predictions) != evaluation_data.evaluation_size:
        raise TrainingDataInputError(
            "Inference predictions count does not match evaluation size."
        )

    entries: list[TargetSizePredictionEntry] = []
    for p in raw_predictions:
        energy = float(p.energy_ev)
        forces = None
        if getattr(p, "forces_ev_per_angstrom", None) is not None:
            forces = np.asarray(p.forces_ev_per_angstrom, dtype=np.float64)
        stress = None
        if getattr(p, "stress_ev_per_angstrom3", None) is not None:
            stress = np.asarray(p.stress_ev_per_angstrom3, dtype=np.float64)
        entries.append(
            TargetSizePredictionEntry(
                energy_ev=energy,
                forces_ev_per_angstrom=forces,
                stress_ev_per_angstrom3=stress,
            )
        )

    prediction_payload_digest = target_size_eval2_prediction_digest(
        role, entries
    )
    return TargetSizePredictionEvidence(
        role_digest=role.content_digest,
        trajectory_digest=trajectory.content_digest,
        boundary_state_digest=boundary_state.content_digest,
        boundary_epoch=role.boundary_epoch,
        evaluation_model_state=trajectory.evaluation_model_state,
        evaluated_model_state_digest=evaluated_model_state_digest,
        evaluation_data_digest=evaluation_data.content_digest,
        evaluation_membership_digest=(
            evaluation_data.evaluation_membership_digest
        ),
        evaluation_size=evaluation_data.evaluation_size,
        prediction_count=len(entries),
        prediction_payload_digest=prediction_payload_digest,
        predictions=tuple(entries),
    )


def run_target_size_eval2_reduction(
    role: TargetSizeEval2Role,
    evaluation_data: TargetSizeEvaluationArtifact,
    prediction_evidence: TargetSizePredictionEvidence,
    *,
    view: Any = None,
    root_directory: str | Path | None = None,
) -> Eval2TargetMetricRecord:
    """Reduce the authorized boundary predictions through the EVAL2 engine."""
    if prediction_evidence.role_digest != role.content_digest:
        raise TrainingDataInputError(
            "Prediction evidence does not bind this direct EVAL2 role."
        )
    if prediction_evidence.evaluation_data_digest != evaluation_data.content_digest:
        raise TrainingDataInputError(
            "Prediction evidence binds a different evaluation data authority."
        )
    if (
        prediction_evidence.evaluation_membership_digest
        != role.evaluation_membership_digest
    ):
        raise TrainingDataInputError(
            "Prediction evidence evaluation membership does not match role."
        )
    if prediction_evidence.evaluation_size != role.evaluation_size:
        raise TrainingDataInputError(
            "Prediction evidence size does not match role evaluation size."
        )
    if prediction_evidence.boundary_state_digest != role.boundary_state_digest:
        raise TrainingDataInputError(
            "Prediction evidence binds a different boundary state."
        )
    if (
        evaluation_data.evaluation_membership_digest
        != role.evaluation_membership_digest
    ):
        raise TrainingDataInputError(
            "Evaluation data membership digest does not match role."
        )
    if evaluation_data.evaluation_size != role.evaluation_size:
        raise TrainingDataInputError(
            "Evaluation data size does not match role evaluation size."
        )
    if (
        role.evaluation_data_digest is not None
        and role.evaluation_data_digest != evaluation_data.content_digest
    ):
        raise TrainingDataInputError(
            "Direct EVAL2 role binds a different evaluation data authority."
        )

    active_view = view
    if active_view is None:
        if root_directory is None:
            raise TrainingDataInputError(
                "root_directory is required when view is not provided."
            )
        active_view = evaluation_data.build_evaluation_view(root_directory)

    if int(active_view.configuration_count) != role.evaluation_size:
        raise TrainingDataInputError(
            "EVAL2 view population does not equal the exact P2 M-membership."
        )
    if len(prediction_evidence.predictions) != role.evaluation_size:
        raise TrainingDataInputError(
            "EVAL2 predictions do not cover the exact P2 M-membership."
        )

    return eval2_target_metrics_from_prediction_view(
        active_view,
        prediction_evidence.predictions,
        block_ids=role.correlation_block_ids,
        target_role_digest=role.content_digest,
        prediction_digest=prediction_evidence.prediction_payload_digest,
    )


def translate_target_size_eval2_failure(
    role: TargetSizeEval2Role, error: Eval2NumericalEvaluationError
) -> TargetSizeNumericalFailure:
    """Translate one authenticated EVAL2 numerical failure to P2 evidence."""

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
    evaluation_data: TargetSizeEvaluationArtifact,
    prediction_evidence: TargetSizePredictionEvidence,
    *,
    view: Any = None,
    root_directory: str | Path | None = None,
) -> TargetSizeBoundaryMetric | TargetSizeNumericalFailure:
    """Evaluate exactly one authorized boundary checkpoint on exact M_i."""

    try:
        record = run_target_size_eval2_reduction(
            role,
            evaluation_data,
            prediction_evidence,
            view=view,
            root_directory=root_directory,
        )
    except Eval2NumericalEvaluationError as error:
        return translate_target_size_eval2_failure(role, error)
    return target_size_boundary_metric_from_eval2_record(role, record)


__all__ = [
    "TARGET_SIZE_EVAL2_PREDICTION_SCHEMA",
    "TARGET_SIZE_EVAL2_ROLE_SCHEMA",
    "TARGET_SIZE_PREDICTION_EVIDENCE_SCHEMA",
    "TargetSizeEval2Role",
    "TargetSizePredictionEntry",
    "TargetSizePredictionEvidence",
    "build_target_size_eval2_role",
    "evaluate_target_size_boundary",
    "run_target_size_direct_boundary_inference",
    "run_target_size_eval2_reduction",
    "target_size_boundary_metric_from_eval2_record",
    "target_size_eval2_prediction_digest",
    "target_size_population_correlation_blocks",
    "translate_target_size_eval2_failure",
]
