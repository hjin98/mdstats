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
import io
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
from ..mace_export import MaceExtxyzPolicy
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


def _authenticate_target_size_provider(
    *,
    raw_checkpoint_path: Path,
    raw_checkpoint_sha256: str,
    companion_path: Path,
    companion_sha256: str,
    summary: Any,
    trajectory: TargetSizeCandidateTrajectory,
    config_payload: Mapping[str, Any],
    allow_forward_override: bool,
) -> tuple[Any, str, Mapping[str, Any]]:
    """Authenticate one TRAIN2 state through the shared provider owner.

    The returned provider is the same model owner that must perform the
    subsequent forward.  Replay uses this helper without forwarding so it can
    prove prediction provenance against the actual durable state rather than
    trusting serialized identity fields alone.
    """

    import hashlib
    import torch

    from ..model_features import MaceCalculatorProvider
    from ..train2_runtime import TRAIN2_RUNTIME_COMPANION_SCHEMA, _tensor_state_digest

    raw_checkpoint = raw_checkpoint_path.read_bytes()
    if hashlib.sha256(raw_checkpoint).hexdigest() != validate_digest(
        raw_checkpoint_sha256, name="raw_checkpoint_sha256"
    ):
        raise TrainingDataInputError(
            "TRAIN2 raw checkpoint bytes changed before provider authentication."
        )
    try:
        raw_model = torch.load(
            io.BytesIO(raw_checkpoint), map_location="cpu", weights_only=False
        )
    except TypeError:  # pragma: no cover - older torch
        try:
            raw_model = torch.load(io.BytesIO(raw_checkpoint), map_location="cpu")
        except Exception as exc:
            raise TrainingDataInputError(
                "Authenticated TRAIN2 raw checkpoint cannot be loaded."
            ) from exc
    except Exception as exc:
        raise TrainingDataInputError(
            "Authenticated TRAIN2 raw checkpoint cannot be loaded."
        ) from exc

    raw_model_candidate = raw_model
    if isinstance(raw_model_candidate, (tuple, list)):
        if len(raw_model_candidate) != 1:
            raw_model_candidate = None
        else:
            raw_model_candidate = raw_model_candidate[0]
    if isinstance(raw_model_candidate, Mapping) and "model" in raw_model_candidate:
        raw_model_candidate = raw_model_candidate.get("model")
    if not (
        hasattr(raw_model_candidate, "named_parameters")
        and hasattr(raw_model_candidate, "named_modules")
    ):
        raw_model_candidate = None

    raw_companion = companion_path.read_bytes()
    if hashlib.sha256(raw_companion).hexdigest() != validate_digest(
        companion_sha256, name="companion_sha256"
    ):
        raise TrainingDataInputError(
            "TRAIN2 continuation companion bytes changed before provider authentication."
        )
    try:
        companion = torch.load(
            io.BytesIO(raw_companion), map_location="cpu", weights_only=False
        )
    except TypeError:  # pragma: no cover - older torch
        companion = torch.load(io.BytesIO(raw_companion), map_location="cpu")
    except (OSError, RuntimeError, ValueError) as exc:
        raise TrainingDataInputError(
            "Authenticated TRAIN2 continuation companion cannot be loaded."
        ) from exc
    if (
        not isinstance(companion, Mapping)
        or companion.get("schema") != TRAIN2_RUNTIME_COMPANION_SCHEMA
    ):
        raise TrainingDataSerializationError(
            "Unsupported TRAIN2 continuation companion schema."
        )
    live_parameters = companion.get("live_parameters")
    if not isinstance(live_parameters, list) or not live_parameters:
        raise TrainingDataInputError(
            "Authenticated TRAIN2 continuation companion has no live parameter state."
        )
    device = str(config_payload.get("device", ""))
    dtype_str = str(config_payload.get("default_dtype", ""))
    if not device or not dtype_str:
        raise TrainingDataInputError(
            "Candidate MACE configuration must state device and default dtype."
        )
    provider_kwargs = {
        "checkpoint_locator": str(raw_checkpoint_path),
        "checkpoint_sha256": raw_checkpoint_sha256,
        "device": device,
        "default_dtype": dtype_str,
        "supported_atomic_numbers": tuple(
            int(value) for value in config_payload.get("atomic_numbers", ())
        ),
        "requested_atomic_numbers": tuple(
            int(value) for value in config_payload.get("atomic_numbers", ())
        ),
        "allow_forward_override": allow_forward_override,
    }
    # A deployable serialized model is an architecture source only.  The
    # authenticated snapshot companion remains the sole accepted learned-state
    # source and is copied into this same provider before any forward.  Older
    # bounded fixtures contain only parameter state, in which case the explicit
    # forward-override seam may use the provider-owned parameter shell.
    provider_model = raw_model_candidate
    if provider_model is None:
        provider_model = companion.get("model")
    if provider_model is not None:
        if not hasattr(provider_model, "named_parameters"):
            raise TrainingDataInputError(
                "TRAIN2 continuation companion model is not a torch model."
            )
        provider = MaceCalculatorProvider.from_authenticated_model(
            provider_model, **provider_kwargs
        )
        provider.load_authenticated_parameter_state(
            live_parameters, state_name="live"
        )
    else:
        provider = MaceCalculatorProvider.from_authenticated_parameter_state(
            live_parameters, **provider_kwargs
        )

    live_model_parameters = tuple(
        parameter for _name, parameter in provider.model.named_parameters()
    )
    computed_live_digest = _tensor_state_digest(
        live_model_parameters, schema="mdstats.train2-live-parameters.v1"
    )
    if computed_live_digest != summary.live_parameter_digest:
        raise TrainingDataInputError(
            "Loaded provider model live parameter digest does not match summary live parameter digest."
        )

    if trajectory.evaluation_model_state == EVALUATION_MODEL_STATE_LIVE:
        evaluated_model_state_digest = computed_live_digest
    elif trajectory.evaluation_model_state == EVALUATION_MODEL_STATE_EMA:
        if summary.ema_state_digest is None:
            raise TrainingDataInputError(
                "EMA trajectory convention requires authenticated EMA boundary state."
            )
        ema_state = companion.get("ema_state")
        if not isinstance(ema_state, Mapping):
            raise TrainingDataInputError("EMA state missing in continuation companion.")
        shadow_params = ema_state.get("shadow_params")
        if not isinstance(shadow_params, list) or not shadow_params:
            raise TrainingDataInputError(
                "EMA shadow parameter state is missing or invalid."
            )
        provider.load_authenticated_parameter_state(shadow_params, state_name="EMA shadow")
        collected = ema_state.get("collected_params")
        if collected is not None and not isinstance(collected, list):
            raise TrainingDataInputError("EMA collected parameter state is invalid.")
        ema_values = tuple(shadow_params) + tuple(collected or ())
        computed_ema_digest = _tensor_state_digest(
            ema_values, schema="mdstats.train2-ema-state.v1"
        )
        if computed_ema_digest != summary.ema_state_digest:
            raise TrainingDataInputError(
                "Loaded provider EMA state digest does not match summary EMA state digest."
            )
        provider_ema_digest = _tensor_state_digest(
            tuple(parameter for _name, parameter in provider.model.named_parameters()),
            schema="mdstats.train2-ema-state.v1",
        )
        expected_provider_ema_digest = _tensor_state_digest(
            tuple(shadow_params), schema="mdstats.train2-ema-state.v1"
        )
        if provider_ema_digest != expected_provider_ema_digest:
            raise TrainingDataInputError(
                "Provider model EMA state digest differs from the authenticated applied state."
            )
        evaluated_model_state_digest = computed_ema_digest
    else:
        raise TrainingDataInputError(
            f"Unsupported evaluation model state: {trajectory.evaluation_model_state!r}"
        )
    return provider, evaluated_model_state_digest, companion


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
    evaluation_data_digest: str

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "execution_context_digest",
            "evaluation_membership_digest",
            "boundary_state_digest",
            "trajectory_digest",
            "evaluation_data_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
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
            "evaluation_data_digest": self.evaluation_data_digest,
        }

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
        if payload.get("evaluation_data_digest") is None:
            raise TrainingDataSerializationError(
                "EVAL2 role requires evaluation_data_digest."
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
            evaluation_data_digest=str(payload["evaluation_data_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("EVAL2 role digest mismatch.")
        return result


def build_target_size_eval2_role(
    *,
    trajectory: TargetSizeCandidateTrajectory,
    boundary_state: TargetSizeBoundarySnapshot,
    definition: TargetSizeExperimentDefinition,
    schedule: TargetSizeScreenSchedule,
    correlation_blocks: Mapping[str, str],
    evaluation_data: TargetSizeEvaluationArtifact,
) -> TargetSizeEval2Role:
    """Authenticate one direct EVAL2 role for the exact active boundary."""

    if not isinstance(boundary_state, TargetSizeBoundarySnapshot):
        raise TrainingDataInputError(
            "EVAL2 role requires an immutable TargetSizeBoundarySnapshot."
        )
    if evaluation_data is None or not isinstance(
        evaluation_data, TargetSizeEvaluationArtifact
    ):
        raise TrainingDataInputError(
            "EVAL2 role requires a validated TargetSizeEvaluationArtifact."
        )
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
        evaluation_data_digest=evaluation_data.content_digest,
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
            forces = np.array(self.forces_ev_per_angstrom, dtype=np.float64, copy=True)
            forces.setflags(write=False)
            object.__setattr__(self, "forces_ev_per_angstrom", forces)
        if self.stress_ev_per_angstrom3 is not None:
            stress = np.array(self.stress_ev_per_angstrom3, dtype=np.float64, copy=True)
            stress.setflags(write=False)
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
    device: str
    default_dtype: str
    execution_architecture: str
    backend_policy: str
    batch_size: int
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
        recomputed_payload_digest = target_size_eval2_prediction_digest_from_role_digest(
            self.role_digest, preds
        )
        if self.prediction_payload_digest != recomputed_payload_digest:
            raise TrainingDataInputError(
                "Prediction evidence payload digest mismatch."
            )
        object.__setattr__(self, "predictions", preds)
        object.__setattr__(self, "device", str(self.device))
        object.__setattr__(self, "default_dtype", str(self.default_dtype))
        object.__setattr__(
            self, "execution_architecture", str(self.execution_architecture)
        )
        object.__setattr__(self, "backend_policy", str(self.backend_policy))
        bs = int(self.batch_size)
        if bs <= 0:
            raise TrainingDataInputError("Batch size must be positive.")
        object.__setattr__(self, "batch_size", bs)

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
            "device": self.device,
            "default_dtype": self.default_dtype,
            "execution_architecture": self.execution_architecture,
            "backend_policy": self.backend_policy,
            "batch_size": self.batch_size,
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
            device=str(payload["device"]),
            default_dtype=str(payload["default_dtype"]),
            execution_architecture=str(payload["execution_architecture"]),
            backend_policy=str(payload["backend_policy"]),
            batch_size=int(payload["batch_size"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size prediction evidence digest mismatch."
            )
        return result


def target_size_eval2_prediction_digest_from_role_digest(
    role_digest: str, predictions: Sequence[Any]
) -> str:
    """Deterministic identity of one prediction set bound to the role digest."""

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
            "role_digest": validate_digest(role_digest, name="role_digest"),
            "predictions": entries,
        }
    )


def target_size_eval2_prediction_digest(
    role: TargetSizeEval2Role, predictions: Sequence[Any]
) -> str:
    """Deterministic identity of one prediction set bound to the role."""
    return target_size_eval2_prediction_digest_from_role_digest(
        role.content_digest, predictions
    )


def run_target_size_direct_boundary_inference(
    *,
    trajectory: TargetSizeCandidateTrajectory,
    materialization: Any,
    boundary_state: TargetSizeBoundarySnapshot,
    role: TargetSizeEval2Role,
    evaluation_data: TargetSizeEvaluationArtifact,
    canonical_frame_authority: Any,
    definition: TargetSizeExperimentDefinition,
    context: Any,
    common: Any,
    schedule: TargetSizeScreenSchedule,
    optimizer_policy: Any,
    materialization_directory: str | Path | None = None,
    snapshot_root: str | Path | None = None,
    evaluation_directory: str | Path | None = None,
    root_directory: str | Path | None = None,
    inference_forward: Callable[[Any, Sequence[Any]], Sequence[Any]] | None = None,
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]]
    | None = None,
    extxyz_policy: MaceExtxyzPolicy,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    frame_array_index: Mapping[str, tuple[Any, Any, int]],
) -> TargetSizePredictionEvidence:
    """Real semantic owner for single exact boundary checkpoint inference."""
    if not isinstance(boundary_state, TargetSizeBoundarySnapshot):
        raise TrainingDataInputError(
            "Direct boundary inference requires an immutable TargetSizeBoundarySnapshot."
        )

    for name, val in (
        ("canonical_frame_authority", canonical_frame_authority),
        ("definition", definition),
        ("context", context),
        ("common", common),
        ("schedule", schedule),
        ("optimizer_policy", optimizer_policy),
    ):
        if val is None:
            raise TrainingDataInputError(f"Mandatory scientific authority '{name}' is missing.")
    if not isinstance(extxyz_policy, MaceExtxyzPolicy):
        raise TrainingDataInputError(
            "Direct EVAL2 inference requires the accepted MaceExtxyzPolicy."
        )
    for name, val in (
        ("frame_catalog", frame_catalog),
        ("frame_data_by_run", frame_data_by_run),
        ("frame_array_index", frame_array_index),
    ):
        if val is None:
            raise TrainingDataInputError(
                f"Direct EVAL2 inference requires canonical P1 authority '{name}'."
            )

    mat_dir = Path(
        materialization_directory
        if materialization_directory is not None
        else (getattr(materialization, "output_directory", "") or root_directory or ".")
    )
    snap_root = Path(
        snapshot_root if snapshot_root is not None else (root_directory or ".")
    )
    eval_dir = Path(
        evaluation_directory
        if evaluation_directory is not None
        else (root_directory or ".")
    )

    from .candidate import (
        validate_target_size_candidate_trajectory,
        validate_target_size_materialization,
    )
    from .execution import validate_target_size_boundary_snapshot
    from .export import validate_target_size_evaluation_artifact

    # 1. Trajectory validation
    validate_target_size_candidate_trajectory(
        trajectory,
        definition,
        context,
        common,
        schedule,
        optimizer_policy=optimizer_policy,
    )

    # 2. Materialization validation
    validate_target_size_materialization(
        materialization,
        trajectory,
        canonical_frame_authority=canonical_frame_authority,
        materialization_directory=mat_dir,
        definition=definition,
        common=common,
        optimizer_policy=optimizer_policy,
        extxyz_policy=extxyz_policy,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
    )

    # 3. Snapshot validation
    validate_target_size_boundary_snapshot(
        boundary_state,
        snapshot_root=snap_root,
        trajectory=trajectory,
        schedule=schedule,
    )

    # 4. Role bindings check
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

    # 5. Evaluation artifact validation
    validate_target_size_evaluation_artifact(
        evaluation_data,
        root_directory=eval_dir,
        definition=definition,
        canonical_frame_authority=canonical_frame_authority,
        policy=extxyz_policy,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
    )

    # 6. Live vs EMA evaluation check & parameter-state authentication
    if (
        boundary_state.evaluation_model_state
        != trajectory.evaluation_model_state
    ):
        raise TrainingDataInputError(
            "Boundary state evaluation model-state mismatch."
        )

    import hashlib
    import json

    ckpt_dir = snap_root / boundary_state.snapshot_relative_dir
    summary = boundary_state.rung_runtime_summary
    companion_path = ckpt_dir / "train2_runtime.pt"
    if not companion_path.is_file():
        raise TrainingDataInputError(
            f"Continuation companion missing in {ckpt_dir}"
        )
    config_path = mat_dir / materialization.mace_config_relative_path
    try:
        config_bytes = config_path.read_bytes()
        config_payload = json.loads(config_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrainingDataInputError(
            "Candidate MACE configuration cannot be read for provider construction."
        ) from exc
    if hashlib.sha256(config_bytes).hexdigest() != materialization.mace_config_sha256:
        raise TrainingDataInputError(
            "Candidate MACE configuration bytes changed before provider construction."
        )
    if digest(config_payload) != materialization.mace_config_digest:
        raise TrainingDataInputError(
            "Candidate MACE configuration content changed before provider construction."
        )
    device = str(config_payload.get("device", ""))
    dtype_str = str(config_payload.get("default_dtype", ""))
    if not device or not dtype_str:
        raise TrainingDataInputError(
            "Candidate MACE configuration must state device and default dtype."
        )
    if device != str(getattr(optimizer_policy, "device", device)):
        raise TrainingDataInputError(
            "Candidate MACE configuration device differs from the accepted optimizer policy."
        )
    if dtype_str != str(trajectory.realization.default_dtype):
        raise TrainingDataInputError(
            "Candidate MACE configuration dtype differs from the accepted trajectory realization."
        )

    forward_fn = inference_forward if inference_forward is not None else inference_evaluator
    provider, evaluated_model_state_digest, _companion = _authenticate_target_size_provider(
        raw_checkpoint_path=ckpt_dir / boundary_state.raw_checkpoint_name,
        raw_checkpoint_sha256=summary.raw_checkpoint_sha256,
        companion_path=companion_path,
        companion_sha256=boundary_state.companion_sha256,
        summary=summary,
        trajectory=trajectory,
        config_payload=config_payload,
        allow_forward_override=forward_fn is not None,
    )

    try:
        import ase.io
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required for inference.") from exc

    target_path = eval_dir / evaluation_data.relative_path
    if not target_path.is_file():
        raise TrainingDataInputError(
            f"Evaluation artifact file is missing: {target_path}"
        )
    raw_bytes = target_path.read_bytes()
    if hashlib.sha256(raw_bytes).hexdigest() != evaluation_data.sha256:
        raise TrainingDataInputError(
            "Evaluation artifact file SHA-256 changed on disk."
        )
    atoms_list = ase.io.read(
        io.StringIO(raw_bytes.decode("utf-8")), format="extxyz", index=":"
    )
    if len(atoms_list) != evaluation_data.evaluation_size:
        raise TrainingDataInputError(
            "Evaluation artifact frame count mismatch."
        )

    if forward_fn is not None:
        raw_predictions = forward_fn(provider, atoms_list)
    else:
        raw_predictions = provider.predict_batch(atoms_list)

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
    arch_digest = provider.runtime_architecture_digest
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
        device=provider.device,
        default_dtype=provider.default_dtype,
        execution_architecture=str(arch_digest),
        backend_policy=provider.backend_policy,
        batch_size=len(atoms_list),
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

    recomputed_payload = target_size_eval2_prediction_digest(
        role, prediction_evidence.predictions
    )
    if prediction_evidence.prediction_payload_digest != recomputed_payload:
        raise TrainingDataInputError(
            "Prediction evidence payload digest does not match predictions."
        )

    from .export import (
        TargetSizeAuthenticatedEvaluationView,
        _evaluation_view_authentication_marker,
    )

    active_view = view
    if isinstance(active_view, TargetSizeAuthenticatedEvaluationView):
        if active_view.artifact_content_digest != evaluation_data.content_digest:
            raise TrainingDataInputError(
                "Authenticated view artifact digest mismatch."
            )
        if active_view.artifact_sha256 != evaluation_data.sha256:
            raise TrainingDataInputError(
                "Authenticated view artifact SHA-256 mismatch."
            )
        if (
            active_view.evaluation_view_digest
            != evaluation_data.evaluation_view_digest
        ):
            raise TrainingDataInputError(
                "Authenticated view view digest mismatch."
            )
        if (
            active_view.evaluation_size != evaluation_data.evaluation_size
            or active_view.evaluation_frame_uids
            != evaluation_data.evaluation_frame_uids
            or active_view.evaluation_membership_digest
            != evaluation_data.evaluation_membership_digest
            or active_view.canonical_frame_authority_digest
            != evaluation_data.canonical_frame_authority_digest
            or active_view.extxyz_policy_digest
            != evaluation_data.extxyz_policy_digest
            or active_view.energy_key != evaluation_data.energy_key
            or active_view.forces_key != evaluation_data.forces_key
            or active_view.stress_key != evaluation_data.stress_key
        ):
            raise TrainingDataInputError(
                "Authenticated view fields do not match the evaluation artifact."
            )
        expected_marker = _evaluation_view_authentication_marker(
            artifact_content_digest=active_view.artifact_content_digest,
            artifact_sha256=active_view.artifact_sha256,
            evaluation_view_digest=active_view.evaluation_view_digest,
            evaluation_size=active_view.evaluation_size,
            evaluation_frame_uids=active_view.evaluation_frame_uids,
            evaluation_membership_digest=active_view.evaluation_membership_digest,
            canonical_frame_authority_digest=active_view.canonical_frame_authority_digest,
            extxyz_policy_digest=active_view.extxyz_policy_digest,
            energy_key=active_view.energy_key,
            forces_key=active_view.forces_key,
            stress_key=active_view.stress_key,
            view=active_view.view,
        )
        if not active_view._authentication_marker or active_view._authentication_marker != expected_marker:
            raise TrainingDataInputError(
                "Authenticated view was not produced by the exact-byte evaluation artifact owner."
            )
        if getattr(active_view.view, "evaluation_view_digest", evaluation_data.evaluation_view_digest) != evaluation_data.evaluation_view_digest:
            raise TrainingDataInputError(
                "Authenticated view underlying data carries a different artifact identity."
            )
        underlying_view = active_view.view
    elif active_view is not None:
        raise TrainingDataInputError(
            "Generic EvaluationDatasetView or unauthenticated view is inadmissible; "
            "TargetSizeAuthenticatedEvaluationView is required."
        )
    else:
        if root_directory is None:
            raise TrainingDataInputError(
                "root_directory is required when view is not provided."
            )
        auth_view = evaluation_data.build_authenticated_evaluation_view(
            root_directory
        )
        underlying_view = auth_view.view

    if root_directory is not None:
        target_path = Path(root_directory) / evaluation_data.relative_path
        if target_path.is_file():
            import hashlib

            if (
                hashlib.sha256(target_path.read_bytes()).hexdigest()
                != evaluation_data.sha256
            ):
                raise TrainingDataInputError(
                    "Evaluation artifact file SHA-256 changed on disk during reduction."
                )

    if int(underlying_view.configuration_count) != role.evaluation_size:
        raise TrainingDataInputError(
            "EVAL2 view population does not equal the exact P2 M-membership."
        )
    if len(prediction_evidence.predictions) != role.evaluation_size:
        raise TrainingDataInputError(
            "EVAL2 predictions do not cover the exact P2 M-membership."
        )

    return eval2_target_metrics_from_prediction_view(
        underlying_view,
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
    "target_size_eval2_prediction_digest_from_role_digest",
    "target_size_population_correlation_blocks",
    "translate_target_size_eval2_failure",
]
