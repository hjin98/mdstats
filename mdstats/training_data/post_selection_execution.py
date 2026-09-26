"""Materialization, TRAIN2 execution, and EVAL2 evidence below the P5 plans.

Everything in this module is a *descendant*: it binds the CV or final-production
run plan it was produced under, and it can never rewrite that plan, the policy
identities above it, or the selected binding at the root.  That direction is the
whole invalidation contract - corrupt or changed fitted evidence invalidates
itself, not its parents.

Two scientific rules shape the code rather than merely being asserted by it.
Fold-local preparation is fitted from the fold's authorized *training* frames
only, so the held-out outer fold cannot leak into E0, weights, or checkpoint
choice.  And nothing here forks a second training engine: preparation reuses the
shared DATA7 fitting seam, export reuses the shared DATA8 ExtXYZ owner, training
reuses the TRAIN2 runtime plan, and evaluation reuses the EVAL2 reduction and
its target-only admissibility/ordering owners.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .bounded_inference import run_bounded_inference
from .campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionError,
)
from .mace_compatibility import (
    FOUNDATION_ADAPTATION_TRAINING_MODES,
    MACE_REPLAY_FORCE_MH_FT_LR,
    MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD,
    POST_SELECTION_TRAINING_MODES,
)
from .post_selection_identity import (
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    PostSelectionMethodIdentity,
    canonical_post_selection_head_names,
)
from .progress_timing import (
    ProgressRateTracker,
    format_progress_fraction,
    format_progress_timing_fields,
)

# v3 preparations are tagged and mode-disjoint; v3 MACE configurations carry
# the authenticated training mode and its mode-specific native loss.
# v4 binds the pre-fit training trajectory instead of the policy-bearing run
# plan; v3 records remain immutable history.
POST_SELECTION_PREPARATION_SCHEMA = "mdstats.post-selection-fitted-preparation.v4"
POST_SELECTION_PREPARATION_SCHEMA_V3 = "mdstats.post-selection-fitted-preparation.v3"
POST_SELECTION_TRANSFER_CONSUMER_SCHEMA = (
    "mdstats.post-selection-transfer-consumer-compositions.v1"
)
POST_SELECTION_COMPOSITION_TRANSFER_SCHEMA = "mdstats.post-selection-composition-transfer.v1"
POST_SELECTION_COMPOSITION_SET_SCHEMA = "mdstats.post-selection-composition-set.v1"
POST_SELECTION_FOUNDATION_RESIDUAL_INPUTS_SCHEMA = (
    "mdstats.post-selection-foundation-residual-inputs.v1"
)
POST_SELECTION_FOUNDATION_RESIDUAL_INPUTS_FILENAME = "foundation_residual_inputs.json"
# v3 is training-only: no held-out outer-evaluation transport and no
# policy-bearing run plan.  v2 records/roots remain immutable history.
POST_SELECTION_MATERIALIZATION_SCHEMA = "mdstats.post-selection-materialization.v3"
POST_SELECTION_MATERIALIZATION_SCHEMA_V2 = "mdstats.post-selection-materialization.v2"
POST_SELECTION_MACE_CONFIG_SCHEMA = "mdstats.post-selection-mace-config.v3"
POST_SELECTION_REPLAY_FORCE_MH_FT_LR = MACE_REPLAY_FORCE_MH_FT_LR
POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD = (
    MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD
)
# Pinned MACE's ordinary one-head parser projection uses this source-owned
# namespace when no explicit ``heads`` mapping is supplied. Replay paths use
# the canonical target_head mapping below.
POST_SELECTION_SINGLE_HEAD_NAME = "Default"
# v2 is the assessment-independent EvaluationMeasurementIdentity: it binds the
# exact numerical experiment and nothing from any run or assessment plan.
POST_SELECTION_EVAL_ROLE_SCHEMA = "mdstats.post-selection-eval2-measurement.v2"
POST_SELECTION_EVAL_PREDICTIONS_SCHEMA = "mdstats.post-selection-eval2-predictions.v2"
POST_SELECTION_RUN_EVIDENCE_SCHEMA = "mdstats.post-selection-run-evidence.v2"
POST_SELECTION_RUN_EVIDENCE_SCHEMA_V1 = "mdstats.post-selection-run-evidence.v1"

#: Dataset roles a post-selection run materializes.  ``target_train`` receives
#: gradients; ``checkpoint_monitor`` may control checkpoint choice;
#: ``outer_evaluation`` is held out until the representative is frozen.
DATASET_ROLE_TARGET_TRAIN = "target_train"
DATASET_ROLE_CHECKPOINT_MONITOR = "checkpoint_monitor"
DATASET_ROLE_OUTER_EVALUATION = "outer_evaluation"


class PostSelectionExecutionError(PostSelectionError):
    """A post-selection execution owner refused to produce or accept evidence."""


class PostSelectionCancelledError(PostSelectionExecutionError):
    """A requested cooperative stop was observed and the owned child reaped.

    This is the execution owner's *explicit* statement that the caller's own
    cancellation request - not a backend fault, a nonzero MACE exit, a CUDA
    allocation failure, or a programmer error - ended this attempt, and that it
    ended through the normal child termination/finalization path. It is
    therefore the only execution outcome a supervisor may treat as retractable
    work rather than an execution failure: a supervisor's intent to stop a job
    is never by itself evidence about why the job raised.
    """


# ---------------------------------------------------------------------------
# Fitted preparation (fold-local or final)
# ---------------------------------------------------------------------------


def _composition_key(counts: Mapping[int, int]) -> tuple[tuple[int, int], ...]:
    return tuple(sorted((int(z), int(n)) for z, n in counts.items() if int(n) != 0))


def _composition_counts_by_frame(
    selected: CurrentSelectedTrainingContext, frame_uids: Sequence[str]
) -> dict[str, tuple[tuple[int, int], ...]]:
    """Element-count composition class of each frame, from geometry only.

    Labels are never read here: common-monitor and held-out consumers are
    inspected only for the composition classes whose E0 correction they
    consume.
    """

    import numpy as np

    authorities = selected.authorities
    index = authorities.frame_array_index
    by_run: dict[str, tuple[tuple[int, int], ...]] = {}
    result: dict[str, tuple[tuple[int, int], ...]] = {}
    for uid in frame_uids:
        record, data, _local = index[str(uid)]
        run_id = str(record.run_id)
        if run_id not in by_run:
            numbers = np.asarray(data.atomic_numbers, dtype=np.int64)
            unique, counts = np.unique(numbers, return_counts=True)
            by_run[run_id] = _composition_key(
                {int(z): int(n) for z, n in zip(unique, counts, strict=True)}
            )
        result[str(uid)] = by_run[run_id]
    return result


def transfer_consumer_composition_digest(
    selected: CurrentSelectedTrainingContext,
    *,
    training_mode: str,
    consumer_frame_uids: Sequence[str],
) -> str | None:
    """Label-blind composition identity of a trajectory's governed transfer consumers.

    This is the only held-out-derived coordinate that may descend into a
    training trajectory: the element-count composition classes of the common
    monitor and held-out frames whose E0 correction foundation preparation must
    transfer to.  It is computed from geometry alone - no label, reference
    value, or serialized evaluation artifact is read - so held-out label or
    transport changes cannot move it, while a changed composition does.  Scratch
    preparation has no composition transfer and binds none.
    """

    if str(training_mode) not in FOUNDATION_ADAPTATION_TRAINING_MODES:
        return None
    classes = sorted(
        set(_composition_counts_by_frame(selected, tuple(consumer_frame_uids)).values())
    )
    if not classes:
        raise PostSelectionExecutionError(
            "Foundation-P5 composition transfer requires governed consumer frames."
        )
    return digest(
        {
            "schema": POST_SELECTION_TRANSFER_CONSUMER_SCHEMA,
            "compositions": [[list(pair) for pair in item] for item in classes],
        }
    )


@dataclass(frozen=True, slots=True)
class CompositionTransferResult:
    """Composition-level E0 transfer evidence for one foundation-residual fit.

    The fit's elemental corrections need not be unique.  What must be unique is
    the correction ``c^T delta_e`` consumed by every governed composition ``c``,
    which holds iff ``c`` is orthogonal to the unanchored null space of the
    authorized count matrix.  Count matrices are integers, so the null space and
    the orthogonality test are evaluated in exact rational arithmetic; the
    solver's numerical rank at the accepted tolerance must agree with the exact
    rank, otherwise the fit is too ill-conditioned to interpret and fails.
    No prior/anchor is currently accepted.
    """

    element_order: tuple[int, ...]
    fit_composition_classes: tuple[tuple[tuple[int, int], ...], ...]
    numerical_rank: int
    exact_rank: int
    relative_singular_value_tolerance: float
    null_space_basis: tuple[tuple[str, ...], ...]
    anchor_identity: str | None
    required_compositions: tuple[tuple[tuple[int, int], ...], ...]
    non_transferable_compositions: tuple[tuple[tuple[int, int], ...], ...]

    def __post_init__(self) -> None:
        elements = tuple(int(z) for z in self.element_order)
        if not elements or tuple(sorted(set(elements))) != elements:
            raise TrainingDataInputError(
                "Composition-transfer element order must be unique increasing atomic numbers."
            )
        object.__setattr__(self, "element_order", elements)
        for name in (
            "fit_composition_classes",
            "required_compositions",
            "non_transferable_compositions",
        ):
            classes = tuple(
                sorted({_composition_key(dict(item)) for item in getattr(self, name)})
            )
            object.__setattr__(self, name, classes)
        if not self.fit_composition_classes or not self.required_compositions:
            raise TrainingDataInputError(
                "Composition transfer requires fit and required composition classes."
            )
        if self.anchor_identity is not None:
            raise PostSelectionExecutionError(
                "No foundation-P5 E0 anchor is currently accepted."
            )
        if int(self.exact_rank) + len(self.null_space_basis) != len(elements):
            raise TrainingDataInputError(
                "Composition-transfer rank and null-space dimension are inconsistent."
            )

    @property
    def transferable(self) -> bool:
        return not self.non_transferable_compositions

    @property
    def required_composition_set_digest(self) -> str:
        return digest(
            {
                "schema": POST_SELECTION_COMPOSITION_SET_SCHEMA,
                "compositions": [
                    [list(pair) for pair in item] for item in self.required_compositions
                ],
            }
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_COMPOSITION_TRANSFER_SCHEMA,
            "element_order": list(self.element_order),
            "fit_composition_classes": [
                [list(pair) for pair in item] for item in self.fit_composition_classes
            ],
            "numerical_rank": int(self.numerical_rank),
            "exact_rank": int(self.exact_rank),
            "relative_singular_value_tolerance": float(
                self.relative_singular_value_tolerance
            ),
            "null_space_dimension": len(self.null_space_basis),
            "null_space_basis": [list(row) for row in self.null_space_basis],
            "anchor_identity": self.anchor_identity,
            "required_composition_set_digest": self.required_composition_set_digest,
            "required_compositions": [
                [list(pair) for pair in item] for item in self.required_compositions
            ],
            "non_transferable_compositions": [
                [list(pair) for pair in item]
                for item in self.non_transferable_compositions
            ],
            "transferable": self.transferable,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompositionTransferResult":
        if payload.get("schema") != POST_SELECTION_COMPOSITION_TRANSFER_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection composition-transfer schema."
            )

        def classes(name: str) -> tuple[tuple[tuple[int, int], ...], ...]:
            return tuple(
                tuple((int(z), int(n)) for z, n in item) for item in payload[name]
            )

        result = cls(
            element_order=tuple(int(z) for z in payload["element_order"]),
            fit_composition_classes=classes("fit_composition_classes"),
            numerical_rank=int(payload["numerical_rank"]),
            exact_rank=int(payload["exact_rank"]),
            relative_singular_value_tolerance=float(
                payload["relative_singular_value_tolerance"]
            ),
            null_space_basis=tuple(
                tuple(str(v) for v in row) for row in payload["null_space_basis"]
            ),
            anchor_identity=payload.get("anchor_identity"),
            required_compositions=classes("required_compositions"),
            non_transferable_compositions=classes("non_transferable_compositions"),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection composition-transfer digest mismatch."
            )
        return result


def _exact_null_space(
    rows: Sequence[Sequence[int]], column_count: int
) -> tuple[int, tuple[tuple[Any, ...], ...]]:
    """Exact rank and rational null-space basis of an integer matrix."""

    from fractions import Fraction

    matrix = [[Fraction(int(v)) for v in row] for row in rows]
    pivots: list[int] = []
    row_position = 0
    for column in range(column_count):
        pivot = next(
            (r for r in range(row_position, len(matrix)) if matrix[r][column] != 0),
            None,
        )
        if pivot is None:
            continue
        matrix[row_position], matrix[pivot] = matrix[pivot], matrix[row_position]
        scale = matrix[row_position][column]
        matrix[row_position] = [value / scale for value in matrix[row_position]]
        for r in range(len(matrix)):
            if r != row_position and matrix[r][column] != 0:
                factor = matrix[r][column]
                matrix[r] = [
                    a - factor * b for a, b in zip(matrix[r], matrix[row_position])
                ]
        pivots.append(column)
        row_position += 1
        if row_position == len(matrix):
            break
    free = [column for column in range(column_count) if column not in pivots]
    basis = []
    for free_column in free:
        vector = [Fraction(0)] * column_count
        vector[free_column] = Fraction(1)
        for r, pivot_column in enumerate(pivots):
            vector[pivot_column] = -matrix[r][free_column]
        basis.append(tuple(vector))
    return len(pivots), tuple(basis)


def validate_composition_transfer(
    fit: Any,
    *,
    fit_compositions: Sequence[tuple[tuple[int, int], ...]],
    required_compositions: Sequence[tuple[tuple[int, int], ...]],
    relative_singular_value_tolerance: float,
) -> CompositionTransferResult:
    """Decide composition-level E0 transfer feasibility for one residual fit.

    ``fit`` is the existing atomic-reference fitter's record; this owner never
    re-solves E0.  Required compositions are the governed training,
    common-monitor, and held-out consumer classes.  An element absent from the
    fit spans a free null direction by itself, so any required composition
    containing it is non-transferable absent an accepted anchor.  A
    minimum-norm solver output is never treated as identification.
    """

    fit_classes = sorted({_composition_key(dict(item)) for item in fit_compositions})
    required = sorted(
        {_composition_key(dict(item)) for item in required_compositions}
        | set(fit_classes)
    )
    elements = tuple(
        sorted({z for item in required for z, _ in item} | set(fit.element_order))
    )
    position = {z: i for i, z in enumerate(elements)}

    def dense(item: tuple[tuple[int, int], ...]) -> list[int]:
        vector = [0] * len(elements)
        for z, n in item:
            vector[position[z]] = int(n)
        return vector

    fit_rows = [dense(item) for item in fit_classes]
    exact_rank, basis = _exact_null_space(fit_rows, len(elements))
    # The solver's numerical rank is over the fit's own element columns; an
    # element absent from every fit row adds a free direction but no rank.
    if exact_rank != int(fit.rank):
        raise PostSelectionExecutionError(
            f"The foundation-residual E0 fit has numerical rank {fit.rank} at the "
            f"accepted tolerance but exact composition rank {exact_rank}; the fit is "
            "too ill-conditioned to decide composition transfer."
        )
    non_transferable = tuple(
        item
        for item in required
        if any(sum(a * b for a, b in zip(dense(item), v)) != 0 for v in basis)
    )
    return CompositionTransferResult(
        element_order=elements,
        fit_composition_classes=tuple(fit_classes),
        numerical_rank=int(fit.rank),
        exact_rank=exact_rank,
        relative_singular_value_tolerance=float(relative_singular_value_tolerance),
        null_space_basis=tuple(tuple(str(v) for v in row) for row in basis),
        anchor_identity=None,
        required_compositions=tuple(required),
        non_transferable_compositions=non_transferable,
    )


@dataclass(frozen=True, slots=True)
class FoundationResidualInputs:
    """Selected-head foundation predictions and reference E0s for one fit.

    Predictions are acquired once per run and persisted with its materialization,
    so restart re-fits E0 from the exact same inputs instead of repeating
    accelerator inference whose floating-point reductions need not be bitwise
    reproducible.
    """

    foundation_checkpoint_digest: str
    foundation_head: str
    membership: tuple[str, ...]
    prediction_energies_ev: tuple[float, ...]
    reference_energies_ev: tuple[tuple[int, float], ...]

    def __post_init__(self) -> None:
        import math

        object.__setattr__(
            self,
            "foundation_checkpoint_digest",
            validate_digest(
                self.foundation_checkpoint_digest, name="foundation_checkpoint_digest"
            ),
        )
        head = str(self.foundation_head).strip()
        if not head:
            raise TrainingDataInputError("Foundation-residual inputs require a head.")
        object.__setattr__(self, "foundation_head", head)
        membership = tuple(str(v) for v in self.membership)
        energies = tuple(float(v) for v in self.prediction_energies_ev)
        if (
            not membership
            or len(set(membership)) != len(membership)
            or len(energies) != len(membership)
            or not all(math.isfinite(v) for v in energies)
        ):
            raise TrainingDataInputError(
                "Foundation-residual predictions must be finite and align one-to-one "
                "with a unique fit membership."
            )
        references = tuple(
            sorted((int(z), float(e)) for z, e in self.reference_energies_ev)
        )
        if not references or len({z for z, _ in references}) != len(references) or not all(
            math.isfinite(e) for _, e in references
        ):
            raise TrainingDataInputError(
                "Foundation reference E0s must be a finite per-element mapping."
            )
        object.__setattr__(self, "membership", membership)
        object.__setattr__(self, "prediction_energies_ev", energies)
        object.__setattr__(self, "reference_energies_ev", references)

    @property
    def prediction_energy_by_frame(self) -> dict[str, float]:
        return dict(zip(self.membership, self.prediction_energies_ev, strict=True))

    @property
    def reference_energies(self) -> dict[int, float]:
        return dict(self.reference_energies_ev)

    @property
    def prediction_digest(self) -> str:
        return digest(
            {
                "schema": "mdstats.post-selection-foundation-residual-predictions.v1",
                "foundation_checkpoint_digest": self.foundation_checkpoint_digest,
                "foundation_head": self.foundation_head,
                "membership": list(self.membership),
                "energy_ev": list(self.prediction_energies_ev),
            }
        )

    @property
    def reference_energy_digest(self) -> str:
        return digest(
            {
                "schema": "mdstats.post-selection-foundation-reference-e0.v1",
                "foundation_checkpoint_digest": self.foundation_checkpoint_digest,
                "foundation_head": self.foundation_head,
                "reference_energies_ev": {
                    str(z): e for z, e in self.reference_energies_ev
                },
            }
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_FOUNDATION_RESIDUAL_INPUTS_SCHEMA,
            "foundation_checkpoint_digest": self.foundation_checkpoint_digest,
            "foundation_head": self.foundation_head,
            "membership": list(self.membership),
            "prediction_energies_ev": list(self.prediction_energies_ev),
            "reference_energies_ev": {str(z): e for z, e in self.reference_energies_ev},
            "prediction_digest": self.prediction_digest,
            "reference_energy_digest": self.reference_energy_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationResidualInputs":
        if payload.get("schema") != POST_SELECTION_FOUNDATION_RESIDUAL_INPUTS_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported foundation-residual input schema."
            )
        result = cls(
            foundation_checkpoint_digest=str(payload["foundation_checkpoint_digest"]),
            foundation_head=str(payload["foundation_head"]),
            membership=tuple(str(v) for v in payload["membership"]),
            prediction_energies_ev=tuple(float(v) for v in payload["prediction_energies_ev"]),
            reference_energies_ev=tuple(
                (int(z), float(e)) for z, e in payload["reference_energies_ev"].items()
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Foundation-residual input digest mismatch."
            )
        return result


def resolve_foundation_residual_inputs(
    selected: CurrentSelectedTrainingContext,
    *,
    membership: Sequence[str],
    foundation_model_path: str | os.PathLike[str],
    foundation_identity: Any,
    foundation_head: str,
    device: str,
    default_dtype: str,
    execution_batch_width: int,
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]] | None = None,
) -> FoundationResidualInputs:
    """Acquire exact selected-head predictions and E0s over the fit membership.

    The canonical foundation provider is built for the exact selected head and
    its head binding is verified: pinned MACE silently falls back to the last
    head for an unknown name, which is not the selected head.  Only geometry is
    evaluated; the fit membership's labels are consumed later by the fitter.
    """

    from ._frame_access import ase_atoms_for_frame

    head = str(foundation_head).strip()
    if not head or str(getattr(foundation_identity, "foundation_head", "")) != head:
        raise PostSelectionExecutionError(
            "Foundation-residual inputs require the exact selected foundation head."
        )
    frames = tuple(str(v) for v in membership)
    provider = build_post_selection_foundation_baseline_provider(
        foundation_path=foundation_model_path,
        foundation_identity=foundation_identity,
        foundation_head=head,
        device=device,
        default_dtype=default_dtype,
    )
    try:
        calculator = getattr(provider, "_calculator", None)
        available = tuple(str(v) for v in getattr(calculator, "available_heads", ()))
        if str(getattr(calculator, "head", "")) != head or head not in available:
            raise PostSelectionExecutionError(
                f"The foundation provider resolved head "
                f"{getattr(calculator, 'head', None)!r}, not the selected head {head!r}."
            )
        model = provider.model
        table = model.atomic_energies_fn.atomic_energies.detach().cpu()
        if table.ndim == 2:
            heads = tuple(str(v) for v in getattr(model, "heads", ()))
            if head not in heads or table.shape[0] != len(heads):
                raise PostSelectionExecutionError(
                    "The foundation E0 table cannot be resolved for the selected head."
                )
            table = table[heads.index(head)]
        reference = {
            int(z): float(value)
            for z, value in zip(model.atomic_numbers.tolist(), table.tolist(), strict=True)
        }
        authorities = selected.authorities
        atoms = [
            ase_atoms_for_frame(*authorities.frame_array_index[uid]) for uid in frames
        ]
        predictions = run_bounded_inference(
            provider,
            atoms,
            batch_width=int(execution_batch_width),
            forward=inference_evaluator,
        )
    finally:
        close = getattr(provider, "close", None)
        if callable(close):
            close()
    return FoundationResidualInputs(
        foundation_checkpoint_digest=str(foundation_identity.canonical_content_digest),
        foundation_head=head,
        membership=frames,
        prediction_energies_ev=tuple(float(item.energy_ev) for item in predictions),
        reference_energies_ev=tuple(reference.items()),
    )


@dataclass(frozen=True, slots=True)
class PostSelectionFittedPreparation:
    """Fitted P5 preparation over one exact authorized membership.

    The membership is an authorization boundary, not a convenience: a CV fold
    fits only from its gradient-training frames, and final production fits from
    the full ``T_selected``.  The record binds the pre-fit training trajectory
    that owns it - never the policy-bearing assessment plan - so a fitted
    product is traceable to the exact position it was allowed to see while a
    policy-only edit cannot orphan it.

    The representation is tagged and mode-disjoint.  ``scratch`` carries its
    accepted from-scratch E0 and fitted configuration-weight table.  Foundation
    modes carry the selected-head foundation-residual E0 fit, its prediction and
    reference-E0 lineage, the common-monitor record whose compositions it must
    serve, and the composition-transfer result; they carry no P3 objective, no
    configuration-weight policy, and no weight table.
    """

    training_trajectory_identity: str
    dataset_role: str
    training_mode: str
    preparation_policy_digest: str
    membership: tuple[str, ...]
    membership_digest: str
    fitted_atomic_reference_digest: str
    fitted_atomic_references: Any
    fitted_weights_digest: str | None = None
    fitted_frame_weights: tuple[Any, ...] | None = None
    foundation_checkpoint_digest: str | None = None
    foundation_head: str | None = None
    foundation_prediction_digest: str | None = None
    foundation_reference_energy_digest: str | None = None
    common_monitor_record_digest: str | None = None
    composition_transfer: CompositionTransferResult | None = None

    def __post_init__(self) -> None:
        for name in (
            "training_trajectory_identity",
            "preparation_policy_digest",
            "membership_digest",
            "fitted_atomic_reference_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        mode = str(self.training_mode)
        if mode not in POST_SELECTION_TRAINING_MODES:
            raise TrainingDataInputError(
                f"Unsupported post-selection training mode: {mode!r}."
            )
        object.__setattr__(self, "training_mode", mode)
        membership = tuple(str(v) for v in self.membership)
        if not membership or len(set(membership)) != len(membership):
            raise TrainingDataInputError(
                "A fitted preparation requires a unique non-empty membership."
            )
        if digest({"frame_uids": list(membership)}) != self.membership_digest:
            raise TrainingDataInputError(
                "Fitted preparation membership does not match its digest."
            )
        if self.fitted_atomic_references.content_digest != self.fitted_atomic_reference_digest:
            raise TrainingDataInputError(
                "Fitted atomic references do not match their digest."
            )
        object.__setattr__(self, "membership", membership)
        object.__setattr__(self, "dataset_role", str(self.dataset_role))
        foundation_fields = (
            "foundation_checkpoint_digest",
            "foundation_head",
            "foundation_prediction_digest",
            "foundation_reference_energy_digest",
            "common_monitor_record_digest",
            "composition_transfer",
        )
        if self.is_foundation:
            if self.fitted_weights_digest is not None or self.fitted_frame_weights is not None:
                raise PostSelectionExecutionError(
                    "A foundation-P5 preparation cannot carry configuration weights."
                )
            if any(getattr(self, name) is None for name in foundation_fields):
                raise PostSelectionExecutionError(
                    "A foundation-P5 preparation requires selected-head residual "
                    "inputs, the common-monitor record, and composition transfer."
                )
            for name in (
                "foundation_checkpoint_digest",
                "foundation_prediction_digest",
                "foundation_reference_energy_digest",
                "common_monitor_record_digest",
            ):
                object.__setattr__(
                    self, name, validate_digest(getattr(self, name), name=name)
                )
            if not self.fitted_atomic_references.foundation_checkpoint_digest:
                raise PostSelectionExecutionError(
                    "A foundation-P5 preparation requires a foundation-residual E0 fit."
                )
            if not self.composition_transfer.transferable:
                raise PostSelectionExecutionError(
                    "Foundation-residual E0 corrections are not identifiable for "
                    "governed compositions "
                    f"{list(self.composition_transfer.non_transferable_compositions)}."
                )
        else:
            if any(getattr(self, name) is not None for name in foundation_fields):
                raise PostSelectionExecutionError(
                    "A P5 scratch preparation cannot carry foundation residual fields."
                )
            if self.fitted_weights_digest is None or self.fitted_frame_weights is None:
                raise PostSelectionExecutionError(
                    "A P5 scratch preparation requires its fitted configuration weights."
                )
            object.__setattr__(
                self,
                "fitted_weights_digest",
                validate_digest(self.fitted_weights_digest, name="fitted_weights_digest"),
            )
            weights = tuple(self.fitted_frame_weights)
            if tuple(item.frame_uid for item in weights) != tuple(sorted(membership)):
                raise TrainingDataInputError(
                    "Fitted weights must cover exactly the fitted membership."
                )
            if (
                digest({"frame_weights": [item.to_dict() for item in weights]})
                != self.fitted_weights_digest
            ):
                raise TrainingDataInputError(
                    "Fitted weights do not match their digest."
                )
            object.__setattr__(self, "fitted_frame_weights", weights)

    @property
    def is_foundation(self) -> bool:
        return self.training_mode in FOUNDATION_ADAPTATION_TRAINING_MODES

    def frame_weight_table(self) -> Any:
        """The scratch weight table; foundation P5 exports neutral transport."""

        if self.fitted_frame_weights is None:
            return None
        from .objectives import FrameTrainingWeightTable

        return FrameTrainingWeightTable.from_records(self.fitted_frame_weights)

    def _payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": POST_SELECTION_PREPARATION_SCHEMA,
            "training_trajectory_identity": self.training_trajectory_identity,
            "dataset_role": self.dataset_role,
            "training_mode": self.training_mode,
            "preparation_policy_digest": self.preparation_policy_digest,
            "membership": list(self.membership),
            "membership_digest": self.membership_digest,
            "fitted_atomic_reference_digest": self.fitted_atomic_reference_digest,
            "fitted_atomic_references": self.fitted_atomic_references.to_dict(),
        }
        if self.is_foundation:
            payload.update(
                {
                    "foundation_checkpoint_digest": self.foundation_checkpoint_digest,
                    "foundation_head": self.foundation_head,
                    "foundation_prediction_digest": self.foundation_prediction_digest,
                    "foundation_reference_energy_digest": (
                        self.foundation_reference_energy_digest
                    ),
                    "common_monitor_record_digest": self.common_monitor_record_digest,
                    "composition_transfer": self.composition_transfer.to_dict(),
                }
            )
        else:
            payload.update(
                {
                    "fitted_weights_digest": self.fitted_weights_digest,
                    "fitted_frame_weights": [
                        item.to_dict() for item in self.fitted_frame_weights
                    ],
                }
            )
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionFittedPreparation":
        from .objectives import FrameTrainingWeight
        from .target_size_execution import CommonAtomicReferenceFit

        # v3 preparations bound the policy-bearing run plan and v2 the whole P3
        # common policy; both are history, never current.
        if payload.get("schema") != POST_SELECTION_PREPARATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection fitted-preparation schema."
            )
        allowed = (
            {
                "foundation_checkpoint_digest",
                "foundation_head",
                "foundation_prediction_digest",
                "foundation_reference_energy_digest",
                "common_monitor_record_digest",
                "composition_transfer",
            }
            if str(payload.get("training_mode")) in FOUNDATION_ADAPTATION_TRAINING_MODES
            else {"fitted_weights_digest", "fitted_frame_weights"}
        )
        common = {
            "schema",
            "content_digest",
            "training_trajectory_identity",
            "dataset_role",
            "training_mode",
            "preparation_policy_digest",
            "membership",
            "membership_digest",
            "fitted_atomic_reference_digest",
            "fitted_atomic_references",
        }
        foreign = sorted(set(payload) - common - allowed)
        if foreign:
            raise TrainingDataSerializationError(
                f"Post-selection fitted preparation carries cross-mode fields {foreign}."
            )
        transfer = payload.get("composition_transfer")
        weights = payload.get("fitted_frame_weights")
        result = cls(
            training_trajectory_identity=str(payload["training_trajectory_identity"]),
            dataset_role=str(payload["dataset_role"]),
            training_mode=str(payload["training_mode"]),
            preparation_policy_digest=str(payload["preparation_policy_digest"]),
            membership=tuple(str(v) for v in payload["membership"]),
            membership_digest=str(payload["membership_digest"]),
            fitted_atomic_reference_digest=str(
                payload["fitted_atomic_reference_digest"]
            ),
            fitted_atomic_references=CommonAtomicReferenceFit.from_dict(
                payload["fitted_atomic_references"]
            ),
            fitted_weights_digest=payload.get("fitted_weights_digest"),
            fitted_frame_weights=(
                None
                if weights is None
                else tuple(FrameTrainingWeight.from_dict(item) for item in weights)
            ),
            foundation_checkpoint_digest=payload.get("foundation_checkpoint_digest"),
            foundation_head=payload.get("foundation_head"),
            foundation_prediction_digest=payload.get("foundation_prediction_digest"),
            foundation_reference_energy_digest=payload.get(
                "foundation_reference_energy_digest"
            ),
            common_monitor_record_digest=payload.get("common_monitor_record_digest"),
            composition_transfer=(
                None if transfer is None else CompositionTransferResult.from_dict(transfer)
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection fitted-preparation digest mismatch."
            )
        return result


def fit_post_selection_preparation(
    context: CurrentSelectedTrainingContext,
    *,
    membership: Sequence[str],
    training_trajectory_identity: str,
    preparation_policy: Any,
    dataset_role: str = DATASET_ROLE_TARGET_TRAIN,
    foundation_residual_inputs: FoundationResidualInputs | None = None,
    common_monitor_record_digest: str | None = None,
    consumer_frame_uids: Sequence[str] = (),
) -> PostSelectionFittedPreparation:
    """Fit one authorized P5 preparation through the existing E0 fitter.

    The membership is checked against ``T_selected`` before anything is fitted,
    so a caller cannot widen the fit domain past the selected data even by
    mistake.  ``consumer_frame_uids`` are the governed common-monitor and
    held-out frames whose composition classes a foundation fit must serve; only
    their geometry is inspected - no held-out label or evaluation artifact.
    """

    from .target_size_execution import (
        fit_common_atomic_reference_energies,
        fit_common_configuration_weights,
        fit_membership_frame_training_weights,
    )

    policy = preparation_policy
    frames = tuple(str(v) for v in membership)
    outside = set(frames) - set(context.selected_membership)
    if outside:
        raise PostSelectionExecutionError(
            f"{len(outside)} frame(s) in this preparation membership are outside "
            "T_selected; post-selection preparation is fitted only from selected "
            "training data."
        )
    consumers = tuple(str(v) for v in consumer_frame_uids)
    if set(consumers) & set(frames):
        raise PostSelectionExecutionError(
            "Governed consumer frames overlap the preparation fit membership."
        )
    authorities = context.authorities
    if not policy.is_foundation:
        atomic_references = fit_common_atomic_reference_energies(
            authorities.frame_catalog,
            authorities.frame_data_by_run,
            frames,
            policy=policy.atomic_reference_policy,
            frame_array_index=authorities.frame_array_index,
        )
        configuration_weights = fit_common_configuration_weights(
            authorities.aggregate.population,
            frames,
            policy=policy.configuration_weight_policy,
        )
        fitted_weights = fit_membership_frame_training_weights(
            authorities.frame_array_index,
            frames,
            configuration_weights={
                item.frame_uid: item for item in configuration_weights
            },
        )
        return PostSelectionFittedPreparation(
            training_trajectory_identity=str(training_trajectory_identity),
            dataset_role=dataset_role,
            training_mode=policy.training_mode,
            preparation_policy_digest=policy.policy_digest,
            membership=frames,
            membership_digest=digest({"frame_uids": list(frames)}),
            fitted_atomic_reference_digest=atomic_references.content_digest,
            fitted_atomic_references=atomic_references,
            fitted_weights_digest=digest(
                {"frame_weights": [item.to_dict() for item in fitted_weights]}
            ),
            fitted_frame_weights=fitted_weights,
        )

    inputs = foundation_residual_inputs
    if inputs is None:
        raise PostSelectionExecutionError(
            "Foundation-P5 preparation requires selected-head foundation predictions "
            "and reference E0s over its exact fit membership."
        )
    if (
        inputs.foundation_checkpoint_digest != policy.foundation_checkpoint_digest
        or inputs.foundation_head != policy.foundation_head
    ):
        raise PostSelectionExecutionError(
            "Foundation-residual inputs come from a different checkpoint or head than "
            "the selected foundation identity."
        )
    if tuple(inputs.membership) != frames:
        raise PostSelectionExecutionError(
            "Foundation-residual predictions cover a different membership than the fit."
        )
    if common_monitor_record_digest is None:
        raise PostSelectionExecutionError(
            "Foundation-P5 preparation requires the exact common target-monitor record."
        )
    head_bound_identity = digest(
        {
            "foundation_checkpoint_digest": inputs.foundation_checkpoint_digest,
            "foundation_head": inputs.foundation_head,
        }
    )
    atomic_references = fit_common_atomic_reference_energies(
        authorities.frame_catalog,
        authorities.frame_data_by_run,
        frames,
        policy=policy.atomic_reference_policy,
        frame_array_index=authorities.frame_array_index,
        foundation_prediction_energy_by_frame=inputs.prediction_energy_by_frame,
        foundation_reference_energies=inputs.reference_energies,
        foundation_checkpoint_digest=inputs.foundation_checkpoint_digest,
        foundation_identity_digest=head_bound_identity,
    )
    compositions = _composition_counts_by_frame(context, frames + consumers)
    transfer = validate_composition_transfer(
        atomic_references,
        fit_compositions=[compositions[uid] for uid in frames],
        required_compositions=[compositions[uid] for uid in consumers],
        relative_singular_value_tolerance=(
            policy.atomic_reference_policy.relative_singular_value_tolerance
        ),
    )
    if not transfer.transferable:
        raise PostSelectionExecutionError(
            "Foundation-residual E0 corrections are not identifiable for governed "
            f"compositions {list(transfer.non_transferable_compositions)}; no anchor "
            "is accepted, so this P5 run is infeasible."
        )
    return PostSelectionFittedPreparation(
        training_trajectory_identity=str(training_trajectory_identity),
        dataset_role=dataset_role,
        training_mode=policy.training_mode,
        preparation_policy_digest=policy.policy_digest,
        membership=frames,
        membership_digest=digest({"frame_uids": list(frames)}),
        fitted_atomic_reference_digest=atomic_references.content_digest,
        fitted_atomic_references=atomic_references,
        foundation_checkpoint_digest=inputs.foundation_checkpoint_digest,
        foundation_head=inputs.foundation_head,
        foundation_prediction_digest=inputs.prediction_digest,
        foundation_reference_energy_digest=inputs.reference_energy_digest,
        common_monitor_record_digest=str(common_monitor_record_digest),
        composition_transfer=transfer,
    )


# ---------------------------------------------------------------------------
# DATA8 materialization
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostSelectionMaterialization:
    """The exact training-only DATA8 workload one post-selection run executes.

    It binds the pre-fit training trajectory and the exact fitted preparation,
    the trainer's target-training and checkpoint-monitor (``valid_file``)
    transports, and the generated MACE configuration.  It deliberately carries
    no held-out outer-evaluation transport: held-out labels, their serialized
    artifact and every EVAL2 provider are measurement ancestry realized only
    after the representative is frozen, outside the training root.
    """

    training_trajectory_identity: str
    preparation_digest: str
    target_train_artifact: Any
    checkpoint_monitor_artifact: Any
    mace_config_relative_path: str
    mace_config_sha256: str
    mace_config_digest: str
    output_directory: str

    def __post_init__(self) -> None:
        for name in (
            "training_trajectory_identity",
            "preparation_digest",
            "mace_config_sha256",
            "mace_config_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for name in ("mace_config_relative_path", "output_directory"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} cannot be empty.")

    @property
    def run_identity(self) -> str:
        return self.training_trajectory_identity

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_MATERIALIZATION_SCHEMA,
            "training_trajectory_identity": self.training_trajectory_identity,
            "preparation_digest": self.preparation_digest,
            "target_train_artifact": self.target_train_artifact.to_dict(),
            "checkpoint_monitor_artifact": self.checkpoint_monitor_artifact.to_dict(),
            "mace_config_relative_path": self.mace_config_relative_path,
            "mace_config_sha256": self.mace_config_sha256,
            "mace_config_digest": self.mace_config_digest,
            "output_directory": self.output_directory,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionMaterialization":
        from .target_size_execution import TargetSizeExtxyzArtifact

        # Historical v2 (with held-out outer-evaluation transport and a
        # policy-bearing run plan) is readable only through the one-time
        # historical recovery derivation, never as current training state.
        if payload.get("schema") != POST_SELECTION_MATERIALIZATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection materialization schema."
            )
        foreign = sorted(
            set(payload)
            - {
                "schema",
                "content_digest",
                "training_trajectory_identity",
                "preparation_digest",
                "target_train_artifact",
                "checkpoint_monitor_artifact",
                "mace_config_relative_path",
                "mace_config_sha256",
                "mace_config_digest",
                "output_directory",
            }
        )
        if foreign:
            raise TrainingDataSerializationError(
                f"Post-selection training materialization carries foreign fields {foreign}."
            )
        result = cls(
            training_trajectory_identity=str(payload["training_trajectory_identity"]),
            preparation_digest=str(payload["preparation_digest"]),
            target_train_artifact=TargetSizeExtxyzArtifact.from_dict(
                payload["target_train_artifact"]
            ),
            checkpoint_monitor_artifact=TargetSizeExtxyzArtifact.from_dict(
                payload["checkpoint_monitor_artifact"]
            ),
            mace_config_relative_path=str(payload["mace_config_relative_path"]),
            mace_config_sha256=str(payload["mace_config_sha256"]),
            mace_config_digest=str(payload["mace_config_digest"]),
            output_directory=str(payload["output_directory"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection materialization digest mismatch."
            )
        return result


def _write_role_artifact(
    context: CurrentSelectedTrainingContext,
    *,
    output_directory: Path,
    role: str,
    frame_uids: Sequence[str],
    extxyz_policy: Any,
    preparation: PostSelectionFittedPreparation | None,
) -> Any:
    from .target_size_execution import write_target_size_extxyz_artifact

    authorities = context.authorities
    frames = tuple(str(v) for v in frame_uids)
    return write_target_size_extxyz_artifact(
        output_directory,
        dataset_id=str(authorities.frame_authority.dataset_id),
        role=role,
        filename=f"{role}.extxyz",
        frame_uids=frames,
        canonical_frame_authority=authorities.frame_authority,
        frame_catalog=authorities.frame_catalog,
        frame_data_by_run=authorities.frame_data_by_run,
        membership_digest=digest({"frame_uids": list(frames)}),
        common_preparation_digest=(
            None if preparation is None else preparation.content_digest
        ),
        training_weights=(
            None if preparation is None else preparation.frame_weight_table()
        ),
        policy=extxyz_policy,
        frame_array_index=authorities.frame_array_index,
    )


def _post_selection_mace_config(
    *,
    run_identity: str,
    optimizer_seed: int,
    planned_epochs: int,
    preparation: PostSelectionFittedPreparation,
    objective: Any,
    optimizer_policy: Any,
    target_train: Any,
    monitor: Any,
    extxyz_policy: Any,
    method: PostSelectionMethodIdentity,
    mace_architecture: Mapping[str, Any] | None = None,
    foundation_head: str | None = None,
    multiheads_finetuning: bool = False,
    replay_train: Any = None,
    replay_monitor: Any = None,
) -> dict[str, Any]:
    """Translate the frozen post-selection run description into MACE arguments.

    Nothing is decided here.  Every value already belongs to the run plan, the
    fitted preparation, or the accepted optimizer policy; this is a rename.
    """

    from .model_features import canonicalize_mace_candidate_architecture

    training_mode = str(method.training_mode).strip()
    if training_mode not in POST_SELECTION_TRAINING_MODES:
        raise PostSelectionExecutionError(
            f"Unsupported post-selection training mode: {training_mode!r}."
        )
    if (
        preparation.training_mode != training_mode
        or objective.policy_digest != method.objective_policy_digest
    ):
        raise PostSelectionExecutionError(
            "Post-selection preparation/objective do not belong to the method identity."
        )
    expected_multihead = training_mode == "multihead_replay"
    if bool(multiheads_finetuning) != expected_multihead:
        raise PostSelectionExecutionError(
            "Post-selection method identity and MACE multihead execution mode "
            "disagree."
        )
    if expected_multihead:
        if not foundation_head:
            raise PostSelectionExecutionError(
                "multihead_replay materialization requires the canonical "
                "foundation head."
            )
        if replay_train is None or replay_monitor is None:
            raise PostSelectionExecutionError(
                "multihead_replay materialization requires both replay training "
                "and independent TRUE_DFT monitor artifacts."
            )
    elif training_mode == "scratch":
        if foundation_head:
            raise PostSelectionExecutionError(
                "scratch materialization cannot carry a foundation checkpoint."
            )
        if replay_train is not None or replay_monitor is not None:
            raise PostSelectionExecutionError(
                "scratch materialization cannot carry replay training fields."
            )
    else:
        if not foundation_head:
            raise PostSelectionExecutionError(
                "naive_fine_tuning materialization requires the canonical "
                "foundation head."
            )
        if replay_train is not None or replay_monitor is not None:
            raise PostSelectionExecutionError(
                "naive_fine_tuning materialization cannot carry replay training "
                "fields."
            )

    fitted_e0s = {
        int(z): float(value)
        for z, value in preparation.fitted_atomic_references.reference_energies_ev
    }
    atomic_numbers = set(int(z) for z in target_train.atomic_numbers) | set(
        int(z) for z in monitor.atomic_numbers
    )
    missing = sorted(atomic_numbers - set(fitted_e0s))
    if missing:
        raise PostSelectionExecutionError(
            f"The fold-local E0 fit is missing atomic numbers {missing}; the "
            "authorized training membership does not cover this workload."
        )
    arch = canonicalize_mace_candidate_architecture(mace_architecture)
    config: dict[str, Any] = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": f"post-selection-{run_identity[:16]}",
        "seed": int(optimizer_seed),
        "target_train_file": target_train.relative_path,
        "target_valid_file": monitor.relative_path,
        "atomic_numbers": sorted(atomic_numbers),
        "E0s": {str(z): fitted_e0s[z] for z in sorted(atomic_numbers)},
        "energy_key": extxyz_policy.energy_key,
        "forces_key": extxyz_policy.forces_key,
        "stress_key": extxyz_policy.stress_key,
        "lr": float(optimizer_policy.learning_rate),
        "training_mode": training_mode,
        # The method's own objective is the objective actually optimized.  P5
        # scratch selects the weighted family, whose native reductions consume
        # ``config_weight`` and the local masks linearly.  Foundation P5 selects
        # native UniversalLoss with its one fixed ``huber_delta``.  The global
        # coefficients are always explicit: MACE's own defaults differ.
        "loss": str(objective.loss_family),
        "energy_weight": float(objective.energy_weight),
        "forces_weight": float(objective.forces_weight),
        "stress_weight": float(objective.stress_weight),
        "batch_size": int(optimizer_policy.batch_size),
        "valid_batch_size": int(optimizer_policy.valid_batch_size),
        "num_workers": int(optimizer_policy.num_workers),
        "max_num_epochs": int(planned_epochs),
        "ema": bool(optimizer_policy.ema),
        "ema_decay": float(optimizer_policy.ema_decay),
        # TRAIN2 authenticates each completed epoch against the raw MACE
        # checkpoint for that epoch.  Retaining every checkpoint is the
        # existing checkpoint-control policy, not a post-hoc evidence aid.
        "save_all_checkpoints": True,
        "amsgrad": bool(optimizer_policy.amsgrad),
        "weight_decay": float(optimizer_policy.weight_decay),
        "clip_grad": float(optimizer_policy.clip_grad),
        "default_dtype": str(method.default_dtype),
        "device": str(optimizer_policy.device),
        "method_identity_digest": method.content_digest,
        # MACE 0.3.16 otherwise recomputes this from the local training
        # collection. The fitted value is a common architecture input, so
        # local data must not be allowed to change it between target sizes or
        # replay/target representations.
        "compute_avg_num_neighbors": False,
        "mace_architecture": arch,
        "target_head_name": POST_SELECTION_TARGET_HEAD_NAME,
        "replay_head_name": POST_SELECTION_REPLAY_HEAD_NAME,
    }
    if training_mode in FOUNDATION_ADAPTATION_TRAINING_MODES:
        config["huber_delta"] = float(objective.huber_delta)
    if hasattr(optimizer_policy, "eval_interval"):
        config["eval_interval"] = int(optimizer_policy.eval_interval)
    if hasattr(optimizer_policy, "acceleration_policy") and optimizer_policy.acceleration_policy is not None:
        config.update(optimizer_policy.acceleration_policy.training_config())
    if foundation_head:
        # Only the checkpoint's *scientific* selection lives in the immutable
        # execution representation.  The filesystem locator is a runtime
        # address: it is authenticated per launch from the request, so a
        # byte-identical checkpoint reached through a different valid path
        # neither changes this run's identity nor blocks its execution.
        config["foundation_head"] = str(foundation_head)
    if multiheads_finetuning:
        config["multiheads_finetuning"] = True
        # These are explicit mdstats method controls.  MACE 0.3.16 otherwise
        # mutates LR/EMA and may duplicate target frames for low replay ratios.
        config["force_mh_ft_lr"] = POST_SELECTION_REPLAY_FORCE_MH_FT_LR
        config["real_pt_data_ratio_threshold"] = (
            POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD
        )
        if replay_train is not None:
            config["pt_train_file"] = (
                replay_train.relative_path
                if hasattr(replay_train, "relative_path")
                else str(replay_train)
            )
        if replay_monitor is not None:
            config["pt_valid_file"] = (
                replay_monitor.relative_path
                if hasattr(replay_monitor, "relative_path")
                else str(replay_monitor)
            )
        config["heads"] = {
            POST_SELECTION_TARGET_HEAD_NAME: {
                "train_file": target_train.relative_path,
                "valid_file": monitor.relative_path,
                "atomic_numbers": sorted(atomic_numbers),
                "E0s": {str(z): fitted_e0s[z] for z in sorted(atomic_numbers)},
                "energy_key": extxyz_policy.energy_key,
                "forces_key": extxyz_policy.forces_key,
                "stress_key": extxyz_policy.stress_key,
            },
            POST_SELECTION_REPLAY_HEAD_NAME: {
                "energy_key": extxyz_policy.energy_key,
                "forces_key": extxyz_policy.forces_key,
                "stress_key": extxyz_policy.stress_key,
            },
        }
    return config


def materialize_post_selection_run(
    context: CurrentSelectedTrainingContext,
    *,
    run_plan: Any,
    method: PostSelectionMethodIdentity,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    transfer_consumer_frame_uids: Sequence[str] = (),
    optimizer_policy: Any,
    extxyz_policy: Any = None,
    output_directory: str | os.PathLike[str],
    preparation: PostSelectionFittedPreparation,
    objective: Any,
    mace_architecture: Mapping[str, Any] | None = None,
    foundation_head: str | None = None,
    multiheads_finetuning: bool = False,
    replay_train: Any = None,
    replay_monitor: Any = None,
) -> tuple[PostSelectionFittedPreparation, PostSelectionMaterialization]:
    """Export and configure one training-only post-selection run.

    Only the trainer's inputs are serialized: gradient-training frames and the
    campaign-common checkpoint monitor it validates on.  Held-out frames enter
    only through ``transfer_consumer_frame_uids``, whose *geometry* re-checks
    that the fitted composition transfer serves the trajectory's label-blind
    consumer projection; no held-out label or EXTXYZ is written here.
    """

    from .mace_export import MaceExtxyzPolicy
    from .target_size_execution import (
        publish_immutable_bytes_create_or_verify,
        publish_immutable_json_create_or_verify,
    )

    policy = MaceExtxyzPolicy() if extxyz_policy is None else extxyz_policy
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    training = tuple(str(v) for v in training_frame_uids)
    monitor_frames = tuple(str(v) for v in monitor_frame_uids)
    consumers = tuple(str(v) for v in transfer_consumer_frame_uids)
    if set(training) & set(monitor_frames) or set(training) & set(consumers):
        raise PostSelectionExecutionError(
            "Post-selection training membership must be disjoint from the "
            "checkpoint monitor and every held-out transfer consumer."
        )
    trajectory = run_plan.training_trajectory
    fitted = preparation
    if fitted.training_trajectory_identity != trajectory.content_digest:
        raise PostSelectionExecutionError(
            "The supplied fitted preparation belongs to a different training trajectory."
        )
    expected_consumers = transfer_consumer_composition_digest(
        context,
        training_mode=method.training_mode,
        consumer_frame_uids=monitor_frames + consumers,
    )
    if expected_consumers != trajectory.transfer_consumer_composition_digest:
        raise PostSelectionExecutionError(
            "The run's transfer-consumer geometry does not reproduce the "
            "composition identity its training trajectory binds."
        )
    if fitted.is_foundation:
        consumed = set(
            _composition_counts_by_frame(context, monitor_frames + consumers).values()
        )
        if not consumed <= set(fitted.composition_transfer.required_compositions):
            raise PostSelectionExecutionError(
                "The foundation preparation's composition transfer was not decided "
                "for every common-monitor and held-out composition of this run."
            )
    if set(fitted.membership) != set(training):
        raise PostSelectionExecutionError(
            "The supplied fitted preparation was fitted from a different "
            "membership than this run trains on."
        )
    target_train = _write_role_artifact(
        context,
        output_directory=root,
        role=DATASET_ROLE_TARGET_TRAIN,
        frame_uids=training,
        extxyz_policy=policy,
        preparation=fitted,
    )
    monitor = _write_role_artifact(
        context,
        output_directory=root,
        role=DATASET_ROLE_CHECKPOINT_MONITOR,
        frame_uids=monitor_frames,
        extxyz_policy=policy,
        preparation=None,
    )
    config = _post_selection_mace_config(
        run_identity=trajectory.content_digest,
        optimizer_seed=run_plan.optimizer_seed,
        planned_epochs=run_plan.planned_epochs,
        preparation=fitted,
        objective=objective,
        optimizer_policy=optimizer_policy,
        target_train=target_train,
        monitor=monitor,
        extxyz_policy=policy,
        method=method,
        mace_architecture=mace_architecture,
        foundation_head=foundation_head,
        multiheads_finetuning=multiheads_finetuning,
        replay_train=replay_train,
        replay_monitor=replay_monitor,
    )
    config_path = root / "post_selection_mace_config.yaml"
    config_bytes = json.dumps(config, indent=2, sort_keys=True).encode("utf-8")
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    publish_immutable_bytes_create_or_verify(
        config_path, config_bytes, expected_sha256=config_sha256
    )
    record = PostSelectionMaterialization(
        training_trajectory_identity=trajectory.content_digest,
        preparation_digest=fitted.content_digest,
        target_train_artifact=target_train,
        checkpoint_monitor_artifact=monitor,
        mace_config_relative_path=config_path.name,
        mace_config_sha256=config_sha256,
        mace_config_digest=digest(config),
        output_directory=str(root),
    )
    publish_immutable_json_create_or_verify(
        root / "materialization.json",
        record.to_dict(),
        deserializer=PostSelectionMaterialization.from_dict,
    )
    return fitted, record


def write_outer_evaluation_transport(
    context: CurrentSelectedTrainingContext,
    *,
    scratch_directory: str | os.PathLike[str],
    frame_uids: Sequence[str],
    extxyz_policy: Any,
) -> Any:
    """Realize the held-out outer-evaluation EXTXYZ as attempt-local scratch.

    The EVAL2 owner calls this only after the run representative is frozen,
    in a bounded scratch directory outside every training root.  The returned
    artifact record authenticates exact membership and the serialized
    label/reference bytes; its locator carries no identity or currentness.
    """

    return _write_role_artifact(
        context,
        output_directory=Path(scratch_directory),
        role=DATASET_ROLE_OUTER_EVALUATION,
        frame_uids=tuple(str(v) for v in frame_uids),
        extxyz_policy=extxyz_policy,
        preparation=None,
    )


# ---------------------------------------------------------------------------
# TRAIN2 execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostSelectionRungRequest:
    """Everything one post-selection TRAIN2 run needs, already authenticated."""

    plan: Any
    run_plan: Any
    materialization: PostSelectionMaterialization
    materialization_directory: Path
    checkpoint_directory: Path
    optimizer_policy: Any
    start_epoch: int = 0
    # ``foundation_identity`` is the scientific source foundation (content,
    # family, selected head).  ``foundation_model_path`` is the TRAIN2
    # construction checkpoint: the source checkpoint itself, or, under a
    # phase-separated TRAIN2 realization, ``training_realization``'s exact
    # (for multi-head sources, selected-head) checkpoint.
    foundation_identity: Any | None = None
    foundation_model_path: Path | None = None
    training_realization: Any | None = None
    replay_train_artifact: Any | None = None
    replay_train_path: Path | None = None
    replay_monitor_artifact: Any | None = None
    replay_monitor_path: Path | None = None
    # Parent-side source/split sequence used to compose the authenticated
    # replay set digest. It is not serialized into the child environment.
    replay_geometry_identities: tuple[str, ...] | None = None
    # The following values are execution-only supervision seams. They are not
    # persisted in the TRAIN2 plan, materialization, or evidence identities.
    progress_context: Mapping[str, Any] | None = None
    cancellation_event: Any | None = None
    progress_callback: Callable[[str], None] | None = None
    progress_observer: Callable[[Mapping[str, Any]], None] | None = None
    telemetry_ref: Any | None = None
    # Runtime-only freshness bound for optimizer liveness. It is resolved
    # from the existing execution configuration and is not serialized into any
    # scientific or restart identity.
    optimizer_activity_timeout_seconds: float = 120.0


class PostSelectionTrainer(Protocol):
    """The one accepted substitution point for expensive post-selection training.

    It sits strictly below the owner boundary: the run plan, fitted preparation,
    materialization, and TRAIN2 runtime plan handed to it were all produced by
    real owners, and the summary it returns is re-authenticated before it can
    become evidence.
    """

    def __call__(self, request: PostSelectionRungRequest) -> Any:
        ...


def _mace_execution_frame_uid_set_digest(
    artifact: Any,
    *,
    role: str = "target",
) -> str | None:
    """Resolve the exact membership token set consumed by the MACE loader.

    Target DATA8 artifacts already carry their authenticated ``frame_uids``.
    Replay artifacts are resolved through the existing file metadata adapter:
    single-source views use ``replay_geometry_identity`` and supported legacy
    files retain their explicit ``frame_uid`` domain.  No token is inferred
    from order, count, pathname, or a newly generated replay namespace.
    """

    from .mace_compatibility import (
        _mace_execution_membership_values,
        mace_frame_uid_set_digest,
    )

    if role not in {"target", "replay"}:
        raise PostSelectionExecutionError(
            f"Unsupported MACE execution membership role: {role!r}."
        )
    if role == "target":
        values = getattr(artifact, "frame_uids", None)
        if values is None:
            path_value = getattr(artifact, "path", None)
            if path_value is None:
                return None
            values = _mace_execution_membership_values(
                path_value,
                role="target",
                head_name="target",
            )
    else:
        # ReplayFileArtifact already owns the canonical replay geometry
        # identities. Reuse that authenticated sequence at the parent
        # boundary; reparsing the same ExtXYZ here was the first half of the
        # P5 defect and made the child repeat it after MACE loaded its
        # Configuration objects. The path adapter remains the compatibility
        # route for older minimal artifacts that predate geometry identities.
        values = getattr(artifact, "geometry_identities", None)
        if values is None:
            path_value = getattr(artifact, "path", None)
            if path_value is None:
                return None
            values = _mace_execution_membership_values(
                path_value,
                role="replay",
                head_name="replay",
            )
    expected_count = getattr(artifact, "configuration_count", None)
    if expected_count is not None and len(tuple(values)) != int(expected_count):
        raise TrainingDataInputError(
            f"MACE {role} execution membership count differs from its artifact."
        )
    return mace_frame_uid_set_digest(values)


def _build_post_selection_mace_execution_authority(
    *,
    materialization: PostSelectionMaterialization,
    internal_payload: Mapping[str, Any],
    executable_payload: Mapping[str, Any],
    optimizer_policy: Any,
    replay_train_artifact: Any | None,
    replay_geometry_identities: Sequence[str] | None = None,
    structures_per_epoch: int | None = None,
) -> dict[str, Any]:
    """Build the one MACE authority used by launch and continuation checks."""

    from .mace_compatibility import (
        MACE_REPLAY_IDENTITY_DOMAIN_CANONICAL,
        MACE_REPLAY_IDENTITY_DOMAIN_LEGACY,
        build_mace_execution_authority,
        mace_frame_uid_set_digest,
    )

    target_train_art = materialization.target_train_artifact
    target_uid_digest = _mace_execution_frame_uid_set_digest(
        target_train_art,
        role="target",
    )
    internal_multihead = bool(internal_payload.get("multiheads_finetuning"))
    if internal_multihead:
        replay_count = int(
            getattr(
                replay_train_artifact,
                "configuration_count",
                max(
                    0,
                    int(
                        structures_per_epoch
                        if structures_per_epoch is not None
                        else getattr(optimizer_policy, "structures_per_epoch", 0)
                    )
                    - int(target_train_art.configuration_count),
                ),
            )
        )
    else:
        # A single-head P5/final request has no replay exposure.  Do not infer a
        # synthetic replay count merely because an older minimal fixture used
        # ``structures_per_epoch`` as a total-size hint.
        replay_count = 0
    replay_uid_digest = None
    if replay_train_artifact is not None:
        if replay_geometry_identities is None:
            replay_uid_digest = _mace_execution_frame_uid_set_digest(
                replay_train_artifact,
                role="replay",
            )
        else:
            replay_geometry_identities = tuple(
                validate_digest(str(value), name="replay_geometry_identity")
                for value in replay_geometry_identities
            )
            if len(replay_geometry_identities) != int(
                getattr(replay_train_artifact, "configuration_count", replay_count)
            ):
                raise PostSelectionExecutionError(
                    "P5 replay geometry transport does not match its artifact count."
                )
            replay_uid_digest = mace_frame_uid_set_digest(replay_geometry_identities)

    # Production projections always contain these canonical optimizer fields. A
    # few pre-launch guard fixtures intentionally stop at a minimal config
    # boundary; resolve their omitted values from the already-authenticated
    # optimizer policy so authority construction does not mask the guard being
    # tested.
    def executable_optimizer_value(name: str, default: Any) -> Any:
        if name in executable_payload:
            return executable_payload[name]
        return getattr(optimizer_policy, name, default)

    configured_ema = bool(executable_optimizer_value("ema", True))
    training_mode = internal_payload.get("training_mode")
    foundation = training_mode in FOUNDATION_ADAPTATION_TRAINING_MODES
    return build_mace_execution_authority(
        role="post_selection",
        config_digest=materialization.mace_config_digest,
        method_identity_digest=internal_payload.get("method_identity_digest"),
        training_mode=training_mode,
        loss_family=executable_payload.get("loss"),
        huber_delta=executable_payload.get("huber_delta") if foundation else None,
        energy_weight=executable_payload.get("energy_weight") if foundation else None,
        forces_weight=executable_payload.get("forces_weight") if foundation else None,
        stress_weight=executable_payload.get("stress_weight") if foundation else None,
        learning_rate=float(executable_optimizer_value("lr", 1.0e-4)),
        ema=configured_ema,
        ema_decay=(
            None
            if not configured_ema
            else float(executable_optimizer_value("ema_decay", 0.99999))
        ),
        multiheads_finetuning=internal_multihead,
        force_mh_ft_lr=(
            executable_payload.get("force_mh_ft_lr")
            if internal_multihead
            else None
        ),
        real_pt_data_ratio_threshold=(
            executable_payload.get("real_pt_data_ratio_threshold")
            if internal_multihead
            else None
        ),
        target_train_count=int(target_train_art.configuration_count),
        replay_train_count=replay_count,
        batch_size=int(executable_optimizer_value("batch_size", 2)),
        target_updates_per_epoch=None,
        target_drop_last=None,
        # Foundation P5 is qualified only for the single-process loader.
        distributed_allowed=not foundation,
        target_frame_uid_set_digest=target_uid_digest,
        replay_frame_uid_set_digest=replay_uid_digest,
        target_head_name=(
            POST_SELECTION_TARGET_HEAD_NAME
            if internal_multihead
            else POST_SELECTION_SINGLE_HEAD_NAME
        ),
        replay_head_name=POST_SELECTION_REPLAY_HEAD_NAME,
        replay_identity_domain=(
            MACE_REPLAY_IDENTITY_DOMAIN_CANONICAL
            if internal_multihead and replay_geometry_identities is not None
            else (
                MACE_REPLAY_IDENTITY_DOMAIN_LEGACY
                if internal_multihead
                else None
            )
        ),
    )


def _terminate_post_selection_process(
    process: subprocess.Popen[Any], *, grace_seconds: float
) -> None:
    """Stop one detached wrapper/process group without leaving descendants.

    This is the only owner of child-termination timing. The escalation is
    bounded by construction - SIGINT, one grace, SIGTERM, one grace, then an
    unconditional SIGKILL and reap - so a stopped child always terminates here
    and no supervisor above needs, or is entitled to, a termination clock of its
    own for work it does not own.
    """

    if process.poll() is not None:
        return
    grace = max(0.1, float(grace_seconds))

    def send(signal_number: int) -> None:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal_number)
            except ProcessLookupError:
                return
        else:  # pragma: no cover - Windows fallback
            if signal_number == signal.SIGKILL:
                process.kill()
            else:
                process.terminate()

    send(signal.SIGINT)
    try:
        process.wait(timeout=grace)
        return
    except subprocess.TimeoutExpired:
        pass
    send(signal.SIGTERM)
    try:
        process.wait(timeout=grace)
        return
    except subprocess.TimeoutExpired:
        pass
    send(signal.SIGKILL)
    process.wait()


def _bounded_process_output(stream: Any, *, limit: int = 64 * 1024) -> str:
    """Read only the diagnostic tail of one completed subprocess stream."""

    try:
        stream.flush()
        stream.seek(0, os.SEEK_END)
        size = int(stream.tell())
        stream.seek(max(0, size - int(limit)), os.SEEK_SET)
        raw = stream.read(int(limit))
    except (OSError, ValueError):
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


class _PostSelectionTrainingProgress:
    """Observe the existing MACE metrics stream for one supervised child."""

    def __init__(
        self,
        request: PostSelectionRungRequest,
        *,
        metric_path: Path,
        initial_summary: Any | None,
        summary_loader: Callable[[Path], Any],
    ) -> None:
        self.metric_path = metric_path
        self.summary_loader = summary_loader
        self._launch_completed_updates = max(
            0,
            int(getattr(initial_summary, "completed_updates", 0) or 0),
        )
        self.last_visible_monotonic: float | None = None
        self.started_monotonic = time.monotonic()
        self.metric_offset = (
            metric_path.stat().st_size if metric_path.is_file() else 0
        )
        self.metric_remainder = ""
        self.optimizer_updates_since_launch = 0
        try:
            self.optimizer_activity_timeout_seconds = float(
                getattr(request, "optimizer_activity_timeout_seconds", 120.0)
            )
        except (TypeError, ValueError) as exc:
            raise PostSelectionExecutionError(
                "Post-selection optimizer activity timeout is invalid."
            ) from exc
        if (
            self.optimizer_activity_timeout_seconds < 0.0
            or not math.isfinite(self.optimizer_activity_timeout_seconds)
        ):
            raise PostSelectionExecutionError(
                "Post-selection optimizer activity timeout must be finite and non-negative."
            )
        self.last_optimizer_update_monotonic: float | None = None
        self.last_loss: Any | None = None
        self.last_metric_epoch: int | None = None
        self.phase = "launching"
        self.execution_phase = "launching"
        self.summary = initial_summary
        self.summary_signature: tuple[int, int] | None = None
        self.completed_updates = self._launch_completed_updates
        planned = getattr(initial_summary, "planned_updates", None)
        self.planned_updates = (
            None if planned in (None, 0) else max(1, int(planned))
        )
        self.completed_epochs = max(
            0,
            int(getattr(initial_summary, "completed_epochs", 0) or 0),
        )
        self.planned_epochs = max(
            0,
            int(
                getattr(
                    getattr(request.plan, "budget_policy", None),
                    "planned_epochs",
                    0,
                )
                or 0
            ),
        )
        if self.planned_updates is None:
            structures = getattr(request.plan, "structures_per_epoch", None)
            # The post-selection runtime plan retains the target-side
            # structures-presented identity for compatibility.  MACE's
            # multihead loader, however, takes one combined target+replay
            # collection, so the launch-time progress projection must use that
            # authenticated loader count until the durable summary publishes
            # its exact ``len(train_loader)`` value.
            target_artifact = getattr(
                getattr(request.materialization, "target_train_artifact", None),
                "configuration_count",
                None,
            )
            replay_artifact = getattr(
                request.replay_train_artifact, "configuration_count", None
            )
            if target_artifact is not None:
                structures = int(target_artifact) + (
                    int(replay_artifact)
                    if bool(getattr(request.plan, "replay_monitor_enabled", False))
                    and replay_artifact is not None
                    else 0
                )
            batch_size = getattr(request.optimizer_policy, "batch_size", None)
            if (
                structures is not None
                and batch_size is not None
                and int(structures) > 0
                and int(batch_size) > 0
                and self.planned_epochs > 0
            ):
                # Current post-selection execution retains MACE's native
                # ``drop_last=True`` training-loader geometry. The target-size
                # owner has a separate authenticated ``drop_last=False``
                # rewrite, but this shared P5 trainer does not; use the same
                # floor update count that TRAIN2 will observe after MACE
                # constructs the real loader. The durable summary still
                # supersedes this launch-time projection when available.
                projected_updates = (
                    int(structures) // int(batch_size)
                    * self.planned_epochs
                )
                # A small fold can be below MACE's native full-batch
                # projection. Until TRAIN2 publishes the actual loader
                # geometry, retain an unknown horizon rather than exposing a
                # zero denominator that makes a live optimizer event look
                # invalid (and cannot satisfy the progress contract).
                if projected_updates > 0:
                    self.planned_updates = projected_updates
        self.last_learning_rate = getattr(
            initial_summary, "instantaneous_learning_rate", None
        )
        self.tracker = ProgressRateTracker(
            completed=self.completed_updates,
            started_at=self.started_monotonic,
        )

    def _read_metrics(self) -> None:
        if not self.metric_path.is_file():
            return
        try:
            size = int(self.metric_path.stat().st_size)
        except OSError:
            return
        if size < self.metric_offset:
            raise PostSelectionExecutionError(
                "MACE training metrics stream was truncated during execution."
            )
        if size == self.metric_offset:
            return
        with self.metric_path.open("rb") as stream:
            stream.seek(self.metric_offset)
            chunk = stream.read()
        self.metric_offset += len(chunk)
        text = self.metric_remainder + chunk.decode("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        self.metric_remainder = ""
        if lines and not lines[-1].endswith(("\n", "\r")):
            self.metric_remainder = lines.pop()
        for line in lines:
            try:
                record = json.loads(line)
            except (TypeError, ValueError):
                continue
            if not isinstance(record, Mapping):
                continue
            mode = str(record.get("mode", ""))
            if mode == "opt":
                # MetricsLogger writes this record only after MACE's optimizer
                # step returns. Validation records never enter this numerator.
                self.optimizer_updates_since_launch += 1
                self.phase = "training"
                self.execution_phase = "training"
                self.last_optimizer_update_monotonic = time.monotonic()
            elif mode == "eval":
                self.phase = "validation"
                self.execution_phase = "validation"
            if "loss" in record:
                self.last_loss = record.get("loss")
            if record.get("epoch") is not None:
                try:
                    self.last_metric_epoch = int(record["epoch"])
                except (TypeError, ValueError):
                    pass

    def refresh(self, checkpoint_directory: Path) -> dict[str, Any]:
        summary_path = checkpoint_directory / "train2_runtime.json"
        if summary_path.is_file():
            try:
                stat = summary_path.stat()
                signature = (int(stat.st_size), int(stat.st_mtime_ns))
            except OSError:
                signature = None
            if signature is not None and signature != self.summary_signature:
                try:
                    self.summary = self.summary_loader(checkpoint_directory)
                except Exception:
                    # Atomic publication can briefly expose a partial file. The
                    # next control poll retries it; the child remains supervised.
                    pass
                else:
                    self.summary_signature = signature
        phase = getattr(self.summary, "phase", None)
        if phase and self.execution_phase == "launching":
            # A durable TRAIN2 phase may describe a learning-rate phase such
            # as ``adaptation``. Keep it visible until the first live MACE
            # record, but never treat that summary phase as optimizer-active
            # scheduler evidence.
            self.phase = str(phase)
            if str(phase) in {"training", "validation"}:
                self.execution_phase = str(phase)
        learning_rate = getattr(
            self.summary, "instantaneous_learning_rate", self.last_learning_rate
        )
        if learning_rate is not None:
            self.last_learning_rate = learning_rate
        # Read after the durable summary so a current validation metric remains
        # the visible phase during a long evaluation interval instead of being
        # overwritten by the summary's learning-rate phase.
        self._read_metrics()
        durable_updates = int(
            getattr(self.summary, "completed_updates", 0) or 0
        )
        self.completed_updates = max(
            durable_updates,
            self._launch_completed_updates + self.optimizer_updates_since_launch,
        )
        planned = getattr(self.summary, "planned_updates", None)
        if planned not in (None, 0):
            self.planned_updates = max(1, int(planned))
        epochs = getattr(self.summary, "completed_epochs", None)
        if epochs is not None:
            self.completed_epochs = max(self.completed_epochs, int(epochs))
        now = time.monotonic()
        last_update = self.last_optimizer_update_monotonic
        optimizer_active = (
            self.execution_phase == "training"
            and self.optimizer_updates_since_launch > 0
            and last_update is not None
            and 0.0 <= now - last_update <= self.optimizer_activity_timeout_seconds
        )
        return {
            "completed_updates": int(self.completed_updates),
            "planned_updates": self.planned_updates,
            "completed_epochs": int(self.completed_epochs),
            "planned_epochs": int(self.planned_epochs),
            "phase": self.phase,
            "true_epoch": bool(optimizer_active),
            "loss": self.last_loss,
            "learning_rate": self.last_learning_rate,
            "optimizer_updates_since_launch": int(
                self.optimizer_updates_since_launch
            ),
        }

    def emit(
        self,
        request: PostSelectionRungRequest,
        *,
        checkpoint_directory: Path,
        visible_interval_seconds: float,
        status: str,
        force: bool = False,
    ) -> dict[str, Any]:
        observation = self.refresh(checkpoint_directory)
        callback = request.progress_observer
        if callback is not None:
            callback({**observation, "status": status, "alive": status == "running"})
        now = time.monotonic()
        last_visible = getattr(self, "last_visible_monotonic", None)
        interval = max(0.05, float(visible_interval_seconds))
        should_emit = force or last_visible is None or now - last_visible >= interval
        if not should_emit:
            return observation
        self.last_visible_monotonic = now
        total = observation["planned_updates"]
        if total is None:
            progress = f"{observation['completed_updates']:,}/? (--.-%)"
            timing_total = max(1, int(observation["completed_updates"]) + 1)
        else:
            progress = format_progress_fraction(
                int(observation["completed_updates"]), int(total)
            )
            timing_total = int(total)
        snapshot = self.tracker.snapshot(
            completed=int(observation["completed_updates"]),
            total=timing_total,
            now=now,
        )
        eta = snapshot.eta_seconds if total is not None else None
        timing = format_progress_timing_fields(
            elapsed_seconds=snapshot.elapsed_seconds,
            eta_seconds=eta,
            recent_rate=snapshot.recent_rate,
            average_rate=snapshot.average_rate,
            rate_unit="gradient-update/s",
        )
        telemetry = None
        if isinstance(request.telemetry_ref, Mapping):
            telemetry = request.telemetry_ref.get("sample")
        if telemetry is None:
            gpu_fields = ("gpu=unavailable", "vram=unavailable")
        else:
            total_bytes = max(1, int(getattr(telemetry, "total_bytes", 0)))
            used_bytes = max(0, int(getattr(telemetry, "used_bytes", 0)))
            gpu_fields = (
                f"gpu={float(getattr(telemetry, 'utilization_percent', 0.0)):.0f}%",
                f"vram={used_bytes / 1024**3:.1f}/{total_bytes / 1024**3:.1f}GiB",
            )
        fields = [
            f"[TRAIN] status={status}",
            f"progress={progress}",
            "unit=gradient-update",
            f"phase={observation['phase']}",
            f"epoch={observation['completed_epochs']}/{observation['planned_epochs']}",
            timing,
            *gpu_fields,
        ]
        if observation["loss"] is not None:
            fields.append(f"loss={observation['loss']}")
        if observation["learning_rate"] is not None:
            fields.append(f"lr={observation['learning_rate']}")
        for key, value in (request.progress_context or {}).items():
            fields.append(f"{key}={value}")
        line = "; ".join(fields)
        if request.progress_callback is None:
            print(line, flush=True)
        else:
            request.progress_callback(line)
        return observation


@dataclass(frozen=True, slots=True)
class MacePostSelectionTrainer:
    """The production trainer: drives MACE through the accepted wrapper script."""

    wrapper_path: Path
    poll_interval_seconds: float = 1.0
    visible_progress_interval_seconds: float = 10.0
    minimum_free_disk_bytes: int | None = None
    timeout_seconds: float | None = None
    terminate_grace_seconds: float = 30.0

    def __call__(self, request: PostSelectionRungRequest) -> Any:
        import os
        import subprocess

        import yaml

        from ._common import sha256_file_cached
        from .precision_runtime import MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE
        from .train2_runtime import (
            TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE,
            TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE,
            load_train2_runtime_summary,
        )

        # 1. Internal P5 configuration bytes, SHA256, digest, and schema
        internal_config_path = (
            request.materialization_directory
            / request.materialization.mace_config_relative_path
        )
        if not internal_config_path.is_file():
            raise PostSelectionExecutionError(
                f"Post-selection MACE configuration is missing: {internal_config_path}"
            )
        config_bytes = internal_config_path.read_bytes()
        if (
            hashlib.sha256(config_bytes).hexdigest()
            != request.materialization.mace_config_sha256
        ):
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration bytes changed before training."
            )
        internal_payload = json.loads(config_bytes.decode("utf-8"))
        if digest(internal_payload) != request.materialization.mace_config_digest:
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration content changed before training."
            )
        if internal_payload.get("schema") != POST_SELECTION_MACE_CONFIG_SCHEMA:
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration schema mismatch."
            )
        configured_method_digest = internal_payload.get("method_identity_digest")
        runtime_method_digest = getattr(
            request.plan, "training_protocol_digest", None
        )
        if (
            configured_method_digest is not None
            and runtime_method_digest is not None
            and str(configured_method_digest) != str(runtime_method_digest)
        ):
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration method identity does not "
                "match the TRAIN2 runtime plan."
            )
        try:
            configured_target_head, configured_replay_head = (
                canonical_post_selection_head_names(
                    target_head_name=internal_payload.get(
                        "target_head_name", POST_SELECTION_TARGET_HEAD_NAME
                    ),
                    replay_head_name=internal_payload.get(
                        "replay_head_name", POST_SELECTION_REPLAY_HEAD_NAME
                    ),
                )
            )
            plan_target_head, plan_replay_head = canonical_post_selection_head_names(
                target_head_name=getattr(
                    request.plan, "target_head_name", POST_SELECTION_TARGET_HEAD_NAME
                ),
                replay_head_name=getattr(
                    request.plan, "replay_head_name", POST_SELECTION_REPLAY_HEAD_NAME
                ),
            )
        except TrainingDataInputError as exc:
            raise PostSelectionExecutionError(
                "Post-selection runtime and executable configuration disagree "
                "with the canonical P5 fine-tuning head namespace."
            ) from exc
        if (configured_target_head, configured_replay_head) != (
            plan_target_head,
            plan_replay_head,
        ):
            raise PostSelectionExecutionError(
                "Post-selection runtime plan and internal configuration use "
                "different fine-tuning head names."
            )
        internal_multihead = bool(internal_payload.get("multiheads_finetuning"))
        runtime_multihead = bool(
            getattr(request.plan, "replay_monitor_enabled", False)
        )
        if internal_multihead != runtime_multihead:
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration and TRAIN2 runtime plan "
                "disagree about replay execution."
            )
        if internal_multihead:
            heads = internal_payload.get("heads")
            if not isinstance(heads, Mapping) or set(heads) != {
                POST_SELECTION_TARGET_HEAD_NAME,
                POST_SELECTION_REPLAY_HEAD_NAME,
            }:
                raise PostSelectionExecutionError(
                    "Post-selection multihead configuration must expose exactly "
                    "the canonical target_head and pt_head heads."
                )
            if request.replay_train_artifact is None or request.replay_train_path is None:
                raise PostSelectionExecutionError(
                    "Multihead post-selection configuration requires the "
                    "authenticated replay training request artifact and path."
                )
            if request.replay_monitor_artifact is None or request.replay_monitor_path is None:
                raise PostSelectionExecutionError(
                    "Multihead post-selection configuration requires the "
                    "authenticated TRUE_DFT monitor request artifact and path."
                )
        elif any(
            key in internal_payload
            for key in ("pt_train_file", "pt_valid_file", "heads")
        ) or any(
            value is not None
            for value in (
                request.replay_train_artifact,
                request.replay_train_path,
                request.replay_monitor_artifact,
                request.replay_monitor_path,
            )
        ):
            raise PostSelectionExecutionError(
                "Non-multihead post-selection configuration cannot carry replay "
                "training fields."
            )

        # 2. Target training ExtXYZ at materialization_directory / target_train_artifact.relative_path
        target_train_art = request.materialization.target_train_artifact
        target_train_path = request.materialization_directory / target_train_art.relative_path
        if not target_train_path.is_file():
            raise PostSelectionExecutionError(
                f"Target training ExtXYZ is missing: {target_train_path}"
            )
        if sha256_file_cached(target_train_path) != target_train_art.sha256:
            raise PostSelectionExecutionError(
                "Target training ExtXYZ SHA256 does not match materialization artifact."
            )

        # 3. Target validation/checkpoint-monitor ExtXYZ
        target_valid_art = request.materialization.checkpoint_monitor_artifact
        target_valid_path = request.materialization_directory / target_valid_art.relative_path
        if not target_valid_path.is_file():
            raise PostSelectionExecutionError(
                f"Target validation ExtXYZ is missing: {target_valid_path}"
            )
        if sha256_file_cached(target_valid_path) != target_valid_art.sha256:
            raise PostSelectionExecutionError(
                "Target validation ExtXYZ SHA256 does not match materialization artifact."
            )

        # 4. Foundation checkpoint for non-scratch methods.  The executable
        # configuration and authenticated request must agree on whether this
        # method is foundation-backed; otherwise a scratch request could carry
        # an unclaimed foundation input that never entered its identity.
        internal_foundation_head = internal_payload.get("foundation_head")
        internal_has_foundation = bool(internal_foundation_head)
        request_has_foundation = (
            request.foundation_identity is not None
            or request.foundation_model_path is not None
            or request.training_realization is not None
        )
        if internal_has_foundation != request_has_foundation:
            raise PostSelectionExecutionError(
                "Post-selection foundation configuration and authenticated "
                "request disagree about foundation execution."
            )
        authenticated_foundation_path: Path | None = None
        if internal_has_foundation:
            if request.foundation_identity is None or request.foundation_model_path is None:
                raise PostSelectionExecutionError(
                    "Non-scratch training requires canonical foundation identity and path in request."
                )
            # 5. The locator is a runtime address, so it is re-authenticated
            # here rather than compared against a stored pathname.  The source
            # head is what the frozen method bound; the bytes reached through
            # the locator must be the TRAIN2 construction checkpoint, which is
            # the source checkpoint unless a phase-separated training
            # realization froze a distinct one.
            if internal_foundation_head != request.foundation_identity.foundation_head:
                raise PostSelectionExecutionError(
                    "Internal config foundation_head does not match the scientific "
                    "source foundation head."
                )
            f_path = Path(request.foundation_model_path).resolve()
            if not f_path.is_file():
                raise PostSelectionExecutionError(
                    f"TRAIN2 construction checkpoint is missing: {f_path}"
                )
            realization = request.training_realization
            if realization is None:
                if sha256_file_cached(f_path) != request.foundation_identity.sha256:
                    raise PostSelectionExecutionError(
                        "TRAIN2 construction checkpoint SHA256 does not match the "
                        "scientific source foundation identity."
                    )
            else:
                if (
                    not realization.qualified
                    or realization.content_digest
                    != getattr(request.optimizer_policy, "acceleration_realization_digest", None)
                ):
                    raise PostSelectionExecutionError(
                        "TRAIN2 construction checkpoint realization is unqualified or "
                        "is not the realization bound by the optimizer policy."
                    )
                if (
                    Path(realization.training_checkpoint_reference).resolve() != f_path
                    or sha256_file_cached(f_path) != realization.training_checkpoint_sha256
                ):
                    raise PostSelectionExecutionError(
                        "TRAIN2 construction checkpoint bytes do not match the stored "
                        "TRAIN2 training realization."
                    )
            authenticated_foundation_path = f_path

        # 6. For multihead_replay: replay train path/artifact present and file SHA matches
        if internal_payload.get("multiheads_finetuning") or request.replay_train_artifact is not None or request.replay_train_path is not None:
            if request.replay_train_artifact is None or request.replay_train_path is None:
                raise PostSelectionExecutionError(
                    "multihead_replay training requires replay train artifact and path in request."
                )
            rp_train_p = Path(request.replay_train_path).resolve()
            if not rp_train_p.is_file():
                raise PostSelectionExecutionError(
                    f"Replay train file is missing: {rp_train_p}"
                )
            artifact_path = getattr(request.replay_train_artifact, "path", None)
            if artifact_path is not None and Path(str(artifact_path)).resolve() != rp_train_p:
                raise PostSelectionExecutionError(
                    "Replay train path does not match its authenticated artifact."
                )
            if sha256_file_cached(rp_train_p) != request.replay_train_artifact.sha256:
                raise PostSelectionExecutionError(
                    "Replay train file SHA256 does not match replay train artifact."
                )

        # 7. When replay monitor is passed: replay monitor path/artifact present and file SHA matches
        if request.replay_monitor_artifact is not None or request.replay_monitor_path is not None:
            if request.replay_monitor_artifact is None or request.replay_monitor_path is None:
                raise PostSelectionExecutionError(
                    "Replay monitor requires both artifact and path in request."
                )
            rp_mon_p = Path(request.replay_monitor_path).resolve()
            if not rp_mon_p.is_file():
                raise PostSelectionExecutionError(
                    f"Replay monitor file is missing: {rp_mon_p}"
                )
            artifact_path = getattr(request.replay_monitor_artifact, "path", None)
            if artifact_path is not None and Path(str(artifact_path)).resolve() != rp_mon_p:
                raise PostSelectionExecutionError(
                    "Replay monitor path does not match its authenticated artifact."
                )
            if sha256_file_cached(rp_mon_p) != request.replay_monitor_artifact.sha256:
                raise PostSelectionExecutionError(
                    "Replay monitor file SHA256 does not match replay monitor artifact."
                )
            # 8. when request.plan.replay_monitor_enabled: monitor SHA must equal true_replay_monitor_sha256
            if request.plan.replay_monitor_enabled:
                if request.replay_monitor_artifact.sha256 != request.plan.true_replay_monitor_sha256:
                    raise PostSelectionExecutionError(
                        "Replay monitor SHA256 does not match runtime plan true_replay_monitor_sha256."
                    )
        elif request.plan.replay_monitor_enabled:
            raise PostSelectionExecutionError(
                "Runtime plan requires replay monitor, but none was provided in request."
            )

        if internal_multihead:
            def configured_path(name: str) -> Path:
                raw = internal_payload.get(name)
                if raw in (None, ""):
                    raise PostSelectionExecutionError(
                        f"Multihead post-selection configuration is missing {name}."
                    )
                path = Path(str(raw))
                if not path.is_absolute():
                    path = request.materialization_directory / path
                return path.resolve()

            if configured_path("pt_train_file") != Path(
                request.replay_train_path
            ).resolve():
                raise PostSelectionExecutionError(
                    "Executable pt_train_file does not match the authenticated "
                    "replay training request path."
                )
            if configured_path("pt_valid_file") != Path(
                request.replay_monitor_path
            ).resolve():
                raise PostSelectionExecutionError(
                    "Executable pt_valid_file does not match the authenticated "
                    "TRUE_DFT monitor request path."
                )

        # 9. Write executable configuration and execute wrapper subprocess
        executable_payload = post_selection_mace_run_configuration(
            internal_payload, foundation_model_path=authenticated_foundation_path
        )
        executable_config_path = (
            request.materialization_directory / "mace_run_config.yaml"
        )
        executable_config_path.write_text(
            yaml.safe_dump(executable_payload, sort_keys=False), encoding="utf-8"
        )

        # The wrapper receives a process-local authority derived only from the
        # authenticated materialization and runtime plan.  It is not a user
        # configuration escape hatch: the wrapper validates every field again
        # after MACE's own argument-mutation region and records the resolved
        # facts in the existing TRAIN2 summary.
        from .mace_compatibility import (
            MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
            mace_execution_authority_to_environment,
        )

        authority = _build_post_selection_mace_execution_authority(
            materialization=request.materialization,
            internal_payload=internal_payload,
            executable_payload=executable_payload,
            optimizer_policy=request.optimizer_policy,
            replay_train_artifact=request.replay_train_artifact,
            replay_geometry_identities=request.replay_geometry_identities,
            structures_per_epoch=getattr(request.plan, "structures_per_epoch", None),
        )

        run_root = request.materialization_directory.parent
        command = [
            str(self.wrapper_path),
            "--config",
            str(executable_config_path.name),
            "--model_dir",
            str(run_root / "models"),
            "--checkpoints_dir",
            str(request.checkpoint_directory),
            "--log_dir",
            str(run_root / "logs"),
            "--results_dir",
            str(run_root / "results"),
        ]
        if int(request.start_epoch) > 0:
            command.append("--restart_latest")

        env = dict(os.environ)
        if int(request.start_epoch) > 0:
            env[MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE] = str(
                int(request.start_epoch) - 1
            )
        else:
            env.pop(MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE, None)
        env[MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE] = (
            mace_execution_authority_to_environment(authority)
        )
        env[TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE] = json.dumps(request.plan.to_dict())
        env["PYTHONHASHSEED"] = str(request.plan.optimizer_policy_digest[:8])
        if hasattr(request.optimizer_policy, "seed"):
            env["PYTHONHASHSEED"] = str(int(request.optimizer_policy.seed))
        if request.plan.replay_monitor_enabled and request.replay_monitor_path is not None:
            env[TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE] = str(
                Path(request.replay_monitor_path).resolve()
            )

        # MACE's MetricsLogger is the existing live-training observation
        # stream. Start at its current byte boundary so a restart's historical
        # lines cannot be counted twice; the authenticated TRAIN2 summary
        # supplies the durable predecessor numerator and exact denominator.
        seed_value = internal_payload.get(
            "seed", getattr(request.optimizer_policy, "seed", 0)
        )
        try:
            seed_text = str(int(seed_value))
        except (TypeError, ValueError):
            seed_text = str(seed_value)
        metric_path = run_root / "results" / (
            f"{internal_payload.get('name', 'post-selection')}_run-{seed_text}_train.txt"
        )
        initial_summary = None
        if (request.checkpoint_directory / "train2_runtime.json").is_file():
            try:
                initial_summary = load_train2_runtime_summary(
                    request.checkpoint_directory
                )
            except Exception:
                # Continuation authentication above remains authoritative. A
                # transient/legacy summary is simply not used for the first
                # heartbeat and is retried by the observer after launch.
                initial_summary = None
        progress = _PostSelectionTrainingProgress(
            request,
            metric_path=metric_path,
            initial_summary=initial_summary,
            summary_loader=load_train2_runtime_summary,
        )
        process: subprocess.Popen[Any] | None = None
        poll_interval = max(0.05, float(self.poll_interval_seconds))
        try:
            with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(
                mode="w+b"
            ) as stderr_file:
                process = subprocess.Popen(
                    command,
                    cwd=str(request.materialization_directory),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    start_new_session=(os.name == "posix"),
                )
                while True:
                    return_code = process.poll()
                    if return_code is None:
                        if (
                            request.cancellation_event is not None
                            and request.cancellation_event.is_set()
                        ):
                            _terminate_post_selection_process(
                                process,
                                grace_seconds=self.terminate_grace_seconds,
                            )
                            progress.emit(
                                request,
                                checkpoint_directory=request.checkpoint_directory,
                                visible_interval_seconds=self.visible_progress_interval_seconds,
                                status="cancelled",
                                force=True,
                            )
                            raise PostSelectionCancelledError(
                                "Post-selection MACE training was cancelled."
                            )
                        if self.minimum_free_disk_bytes is not None:
                            try:
                                free_bytes = int(shutil.disk_usage(run_root).free)
                            except OSError:
                                free_bytes = None
                            if (
                                free_bytes is not None
                                and free_bytes < int(self.minimum_free_disk_bytes)
                            ):
                                _terminate_post_selection_process(
                                    process,
                                    grace_seconds=self.terminate_grace_seconds,
                                )
                                progress.emit(
                                    request,
                                    checkpoint_directory=request.checkpoint_directory,
                                    visible_interval_seconds=self.visible_progress_interval_seconds,
                                    status="stopped-disk",
                                    force=True,
                                )
                                raise PostSelectionExecutionError(
                                    "Post-selection MACE training stopped because the "
                                    "configured free-disk reserve was reached."
                                )
                        if self.timeout_seconds is not None:
                            elapsed = time.monotonic() - progress.started_monotonic
                            if elapsed >= float(self.timeout_seconds):
                                _terminate_post_selection_process(
                                    process,
                                    grace_seconds=self.terminate_grace_seconds,
                                )
                                progress.emit(
                                    request,
                                    checkpoint_directory=request.checkpoint_directory,
                                    visible_interval_seconds=self.visible_progress_interval_seconds,
                                    status="stopped-timeout",
                                    force=True,
                                )
                                raise PostSelectionExecutionError(
                                    "Post-selection MACE training exceeded its configured timeout."
                                )
                    progress.emit(
                        request,
                        checkpoint_directory=request.checkpoint_directory,
                        visible_interval_seconds=self.visible_progress_interval_seconds,
                        status=(
                            "running"
                            if return_code is None
                            else ("completed" if return_code == 0 else "failed")
                        ),
                        force=return_code is not None,
                    )
                    if return_code is not None:
                        stdout_tail = _bounded_process_output(stdout_file)
                        stderr_tail = _bounded_process_output(stderr_file)
                        break
                    time.sleep(poll_interval)
        except BaseException:
            if process is not None and process.poll() is None:
                _terminate_post_selection_process(
                    process,
                    grace_seconds=self.terminate_grace_seconds,
                )
            raise
        if return_code != 0:
            raise PostSelectionExecutionError(
                f"Post-selection MACE training failed (exit {return_code}):\n"
                f"stdout:\n{stdout_tail}\n"
                f"stderr:\n{stderr_tail}"
            )

        try:
            summary = load_train2_runtime_summary(request.checkpoint_directory)
        except Exception as exc:
            raise PostSelectionExecutionError(
                "The MACE wrapper exited successfully without a valid canonical "
                "TRAIN2 runtime summary."
            ) from exc
        if summary.plan_digest != request.plan.content_digest:
            raise PostSelectionExecutionError(
                "Loaded TRAIN2 runtime summary plan digest does not match request."
            )
        if summary.optimizer_policy_digest != request.plan.optimizer_policy_digest:
            raise PostSelectionExecutionError(
                "Loaded TRAIN2 runtime summary optimizer policy digest does not match request."
            )
        return summary


def build_post_selection_foundation_baseline_provider(
    *,
    foundation_path: str | Path,
    foundation_identity: Any,
    foundation_head: str | None = None,
    device: str = "cpu",
    default_dtype: str = "float64",
) -> Any:
    """Construct the canonical foundation baseline prediction provider.

    Foundation replay baselines always use the deployable MACE provider.  Any
    bounded numerical substitution belongs below ``from_model_path`` in tests;
    this owner must retain its checkpoint, head, dtype, and inference-identity
    validation path.
    """

    from ._common import sha256_file_cached
    from .model_features import MaceCalculatorProvider

    path = Path(foundation_path)
    if not path.is_file():
        raise PostSelectionExecutionError(
            f"Foundation baseline checkpoint does not exist: {path}"
        )
    current_sha = sha256_file_cached(path)
    if foundation_identity is not None and hasattr(foundation_identity, "sha256"):
        if current_sha != foundation_identity.sha256:
            raise PostSelectionExecutionError(
                "Foundation baseline model bytes changed on disk (SHA256 mismatch)."
            )
    head = foundation_head or (
        foundation_identity.foundation_head
        if foundation_identity is not None
        and hasattr(foundation_identity, "foundation_head")
        else "default"
    )
    foundation_inference_identity = None
    if foundation_identity is not None and hasattr(foundation_identity, "canonical_content_digest"):
        from .foundation import FoundationInferenceIdentity

        foundation_inference_identity = FoundationInferenceIdentity(
            foundation_potential_digest=foundation_identity.canonical_content_digest,
            default_dtype="float64" if default_dtype == "float64" else "float32",
            backend="e3nn",
            resolved_kernel_mode="eager",
            mace_version="unknown",
            adapter_version="v1",
        )
    return MaceCalculatorProvider.from_model_path(
        path,
        device=device,
        default_dtype=default_dtype,
        foundation_potential_identity=foundation_identity,
        foundation_inference_identity=foundation_inference_identity,
        head=head,
    )


_MACE_CONFIG_PASSTHROUGH_KEYS = (
    "name",
    "seed",
    "atomic_numbers",
    "E0s",
    "energy_key",
    "forces_key",
    "stress_key",
    "lr",
    "loss",
    "force_mh_ft_lr",
    "real_pt_data_ratio_threshold",
    "energy_weight",
    "forces_weight",
    "stress_weight",
    "huber_delta",
    "batch_size",
    "valid_batch_size",
    "num_workers",
    "max_num_epochs",
    "ema",
    "ema_decay",
    "save_all_checkpoints",
    "amsgrad",
    "weight_decay",
    "clip_grad",
    "default_dtype",
    "device",
    "eval_interval",
    "enable_cueq",
    "only_cueq",
    "compute_avg_num_neighbors",
)


def post_selection_mace_run_configuration(
    config: Mapping[str, Any],
    *,
    foundation_model_path: str | Path | None = None,
) -> dict[str, Any]:
    """Project the frozen post-selection configuration into MACE arguments.

    Renaming, explicit architecture projection, and the pinned parser's
    scalar-literal spelling all happen here; the canonical configuration and its
    digests are untouched.

    ``foundation_model_path`` is the authenticated *current* runtime locator of
    the foundation checkpoint.  It is supplied per launch rather than stored,
    because the immutable configuration owns the checkpoint's scientific
    selection while the filesystem address it is reached through is not part of
    the method.
    """

    from .mace_compatibility import (
        encode_mace_executable_configuration,
        project_mace_architecture_arguments,
    )

    if config.get("schema") != POST_SELECTION_MACE_CONFIG_SCHEMA:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration does not carry the accepted schema."
        )
    try:
        target_head_name, replay_head_name = canonical_post_selection_head_names(
            target_head_name=config.get(
                "target_head_name", POST_SELECTION_TARGET_HEAD_NAME
            ),
            replay_head_name=config.get(
                "replay_head_name", POST_SELECTION_REPLAY_HEAD_NAME
            ),
        )
    except TrainingDataInputError as exc:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration carries a noncanonical "
            "fine-tuning head namespace."
        ) from exc
    training_mode = config.get("training_mode")
    if training_mode not in POST_SELECTION_TRAINING_MODES:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration does not carry a supported training mode."
        )
    if (training_mode in FOUNDATION_ADAPTATION_TRAINING_MODES) != ("huber_delta" in config):
        raise PostSelectionExecutionError(
            "Only foundation-P5 MACE configurations carry the UniversalLoss huber_delta."
        )
    result: dict[str, Any] = {
        key: config[key] for key in _MACE_CONFIG_PASSTHROUGH_KEYS if key in config
    }
    result["train_file"] = config["target_train_file"]
    result["valid_file"] = config["target_valid_file"]
    if foundation_model_path is not None:
        result["foundation_model"] = str(foundation_model_path)
    if config.get("foundation_head"):
        result["foundation_head"] = str(config["foundation_head"])
    multihead = bool(config.get("multiheads_finetuning"))
    replay_fields_present = any(
        key in config for key in ("pt_train_file", "pt_valid_file", "heads")
    )
    if not multihead and replay_fields_present:
        raise PostSelectionExecutionError(
            "Non-multihead post-selection MACE configuration cannot expose "
            "replay training files or heads."
        )
    if not multihead and any(
        key in config for key in ("force_mh_ft_lr", "real_pt_data_ratio_threshold")
    ):
        raise PostSelectionExecutionError(
            "Non-multihead post-selection MACE configuration cannot carry "
            "multihead replay controls."
        )
    # MACE 0.3.16's parser default is ``True``. Emit the ordinary single-head
    # value explicitly as well, otherwise a no-replay P5/final request is
    # silently promoted into multihead execution.
    result["multiheads_finetuning"] = multihead
    if config.get("compute_avg_num_neighbors", False) is not False:
        raise PostSelectionExecutionError(
            "Post-selection MACE execution must disable local average-neighbor recomputation."
        )
    result["compute_avg_num_neighbors"] = False
    if multihead:
        configured_force = config.get(
            "force_mh_ft_lr", POST_SELECTION_REPLAY_FORCE_MH_FT_LR
        )
        configured_threshold = config.get(
            "real_pt_data_ratio_threshold",
            POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD,
        )
        if configured_force is not POST_SELECTION_REPLAY_FORCE_MH_FT_LR:
            raise PostSelectionExecutionError(
                "Post-selection replay must explicitly force the authenticated "
                "MACE LR/EMA settings."
            )
        try:
            threshold_matches = (
                float(configured_threshold)
                == POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD
            )
        except (TypeError, ValueError):
            threshold_matches = False
        if not threshold_matches:
            raise PostSelectionExecutionError(
                "Post-selection replay must explicitly disable MACE target duplication."
            )
        # Emit the controls even for legacy in-memory fixtures that predate the
        # repaired internal schema; the parser-facing bytes must never depend on
        # a MACE default.
        result["force_mh_ft_lr"] = POST_SELECTION_REPLAY_FORCE_MH_FT_LR
        result["real_pt_data_ratio_threshold"] = (
            POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD
        )
        if not config.get("pt_train_file") or not config.get("pt_valid_file"):
            raise PostSelectionExecutionError(
                "Post-selection multihead configuration must expose both "
                "pt_train_file and pt_valid_file."
            )
        result["pt_train_file"] = config["pt_train_file"]
        result["pt_valid_file"] = config["pt_valid_file"]
        heads = config.get("heads")
        if not isinstance(heads, Mapping) or set(heads) != {
            target_head_name,
            replay_head_name,
        }:
            raise PostSelectionExecutionError(
                "Post-selection multihead configuration must expose exactly "
                f"{target_head_name!r} and {replay_head_name!r}."
            )
        result["heads"] = dict(heads)
    for key, value in project_mace_architecture_arguments(
        config.get("mace_architecture")
    ).items():
        # The internal architecture head list is mdstats metadata and must never
        # become MACE's dataset-head argument; only the P5 multihead mapping can
        # set ``heads``.
        result.setdefault(key, value)
    try:
        return encode_mace_executable_configuration(result)
    except TrainingDataInputError as exc:
        raise PostSelectionExecutionError(
            f"Post-selection MACE configuration cannot be spelled for MACE: {exc}"
        ) from exc


def post_selection_runtime_plan(
    *,
    method: PostSelectionMethodIdentity,
    optimizer_policy: Any,
    budget_policy: Any,
    structures_per_epoch: int,
    learning_rate_policy: Any = None,
    replay_monitor_enabled: bool = False,
    true_replay_monitor_sha256: str | None = None,
    target_head_name: str = POST_SELECTION_TARGET_HEAD_NAME,
    replay_head_name: str = POST_SELECTION_REPLAY_HEAD_NAME,
) -> Any:
    """Build the TRAIN2 runtime plan for one post-selection role.

    The budget arrives from the *role* policy - the CV budget for a fold, the
    configured production horizon for a final run - while the method identity
    and the LR/optimizer policies are shared.  That is the identity split made
    executable.
    """

    from .train2_policy import LearningRateSchedulePolicy
    from .train2_runtime import Train2RuntimePlan

    try:
        target_head_name, replay_head_name = canonical_post_selection_head_names(
            target_head_name=target_head_name,
            replay_head_name=replay_head_name,
        )
    except TrainingDataInputError as exc:
        raise PostSelectionExecutionError(
            "Post-selection TRAIN2 runtime plan carries a noncanonical "
            "fine-tuning head namespace."
        ) from exc

    training_mode = str(getattr(method, "training_mode", "")).strip()
    if training_mode not in {
        "scratch",
        "naive_fine_tuning",
        "multihead_replay",
    }:
        raise PostSelectionExecutionError(
            f"Unsupported post-selection training mode: {training_mode!r}."
        )
    replay_enabled = training_mode == "multihead_replay"
    if bool(replay_monitor_enabled) != replay_enabled:
        raise PostSelectionExecutionError(
            "Post-selection method identity and TRAIN2 replay execution mode "
            "disagree."
        )

    return Train2RuntimePlan(
        training_protocol_digest=method.content_digest,
        optimizer_policy_digest=optimizer_policy.policy_digest,
        budget_policy=budget_policy,
        learning_rate_policy=(
            LearningRateSchedulePolicy()
            if learning_rate_policy is None
            else learning_rate_policy
        ),
        structures_per_epoch=int(structures_per_epoch),
        replay_monitor_enabled=bool(replay_monitor_enabled),
        target_head_name=target_head_name,
        replay_head_name=replay_head_name,
        true_replay_monitor_sha256=true_replay_monitor_sha256,
        execution_epoch_limit=int(budget_policy.planned_epochs),
    )


# ---------------------------------------------------------------------------
# EVAL2 evidence
# ---------------------------------------------------------------------------


#: Artifact coordinates that carry the exact numerical population: serialized
#: bytes (hence labels/reference values), membership, transport policy and the
#: canonical frame/label authority.  Locators (paths, sidecar paths) are never
#: identity: scratch may be removed and regenerated.
_MEASUREMENT_ARTIFACT_FIELDS = (
    "role",
    "sha256",
    "configuration_count",
    "frame_uids",
    "atomic_numbers",
    "membership_digest",
    "geometry_set_digest",
    "logical_digest",
    "extxyz_policy_digest",
    "policy_digest",
    "canonical_frame_authority_digest",
    "common_preparation_digest",
    "sidecar_sha256",
    "sidecar_digest",
    "label_mode",
)


def _measurement_artifact_projection(artifact: Any) -> dict[str, Any]:
    projection: dict[str, Any] = {}
    for name in _MEASUREMENT_ARTIFACT_FIELDS:
        value = getattr(artifact, name, None)
        if value is None:
            continue
        value = getattr(value, "value", value)
        projection[name] = list(value) if isinstance(value, (tuple, list)) else value
    if "sha256" not in projection:
        raise PostSelectionExecutionError(
            "A measurement artifact must authenticate its serialized bytes."
        )
    return projection


@dataclass(frozen=True, slots=True)
class EvaluationMeasurementIdentity:
    """Assessment-independent identity of one numerical EVAL2 measurement.

    It binds exactly the D2.DEF.060B coordinates that can change the number:
    the evaluation population/artifact (membership, serialized label/reference
    bytes, transport policy), the checkpoint/model state, the metric/reduction
    policy, the prediction head, the provider realization and numerically
    material precision/backend.  No run plan, assessment threshold, warning
    policy, selection policy or publication policy is an input, and neither is
    the artifact's scratch locator.
    """

    dataset_role: str
    artifact: Mapping[str, Any]
    model_state: Mapping[str, Any]
    metric_policy_digest: str
    reduction_block_digest: str
    prediction_head: str | None
    provider_realization: Mapping[str, Any]

    def __post_init__(self) -> None:
        role = str(self.dataset_role).strip()
        if not role:
            raise TrainingDataInputError("A measurement requires its dataset role.")
        object.__setattr__(self, "dataset_role", role)
        for name in ("metric_policy_digest", "reduction_block_digest"):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        object.__setattr__(self, "artifact", dict(self.artifact))
        object.__setattr__(self, "model_state", dict(self.model_state))
        object.__setattr__(self, "provider_realization", dict(self.provider_realization))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_EVAL_ROLE_SCHEMA,
            "dataset_role": self.dataset_role,
            "artifact": dict(self.artifact),
            "model_state": dict(self.model_state),
            "metric_policy_digest": self.metric_policy_digest,
            "reduction_block_digest": self.reduction_block_digest,
            "prediction_head": self.prediction_head,
            "provider_realization": dict(self.provider_realization),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvaluationMeasurementIdentity":
        if payload.get("schema") != POST_SELECTION_EVAL_ROLE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection measurement-identity schema."
            )
        result = cls(
            dataset_role=str(payload["dataset_role"]),
            artifact=dict(payload["artifact"]),
            model_state=dict(payload["model_state"]),
            metric_policy_digest=str(payload["metric_policy_digest"]),
            reduction_block_digest=str(payload["reduction_block_digest"]),
            prediction_head=payload.get("prediction_head"),
            provider_realization=dict(payload["provider_realization"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection measurement-identity digest mismatch."
            )
        return result


def post_selection_eval_role_digest(
    *,
    dataset_role: str,
    artifact: Any,
    model_state: Mapping[str, Any],
    provider_realization: Mapping[str, Any],
    prediction_head: str | None,
    metric_policy_digest: str,
    block_ids: Sequence[str],
) -> EvaluationMeasurementIdentity:
    """The assessment-independent measurement identity of one evaluation.

    Historically this hashed the full run-plan digest and run identity, which
    made a policy-only plan edit look like a different measurement.  It now
    binds only coordinates that independently change the numerical experiment.
    """

    return EvaluationMeasurementIdentity(
        dataset_role=str(dataset_role),
        artifact=_measurement_artifact_projection(artifact),
        model_state=dict(model_state),
        metric_policy_digest=str(metric_policy_digest),
        reduction_block_digest=digest(
            {"schema": "mdstats.eval2-reduction-blocks.v1", "block_ids": [str(v) for v in block_ids]}
        ),
        prediction_head=None if prediction_head is None else str(prediction_head),
        provider_realization=dict(provider_realization),
    )


def _authenticated_atoms(artifact: Any, root_directory: Path) -> list[Any]:
    import ase.io

    if hasattr(artifact, "path") and Path(str(artifact.path)).is_absolute():
        path = Path(artifact.path)
    else:
        rel = getattr(artifact, "relative_path", getattr(artifact, "path", ""))
        path = root_directory / rel
    if not path.is_file():
        raise PostSelectionExecutionError(
            f"Post-selection evaluation artifact is missing: {path}"
        )
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != artifact.sha256:
        raise PostSelectionExecutionError(
            "Post-selection evaluation artifact bytes changed on disk."
        )
    return ase.io.read(io.StringIO(raw.decode("utf-8")), format="extxyz", index=":")


def evaluate_post_selection_dataset(
    *,
    measurement: EvaluationMeasurementIdentity,
    artifact: Any,
    dataset_role: str,
    root_directory: str | os.PathLike[str],
    provider: Any,
    block_ids: Sequence[str],
    execution_batch_width: int,
    extxyz_policy: Any = None,
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]] | None = None,
) -> Any:
    """Reduce one authenticated dataset evaluation through the EVAL2 engine.

    The artifact bytes are re-hashed before they are read, and the reduction is
    the shared EVAL2 owner rather than a P5-local metric implementation, so a
    post-selection metric means exactly what a screening metric means.
    """

    import numpy as np

    from .eval2 import eval2_target_metrics_from_prediction_view
    from .evaluation_views import build_evaluation_dataset_view

    root = Path(root_directory)
    atoms_list = _authenticated_atoms(artifact, root)
    frame_count = (
        len(artifact.frame_uids)
        if hasattr(artifact, "frame_uids")
        else int(getattr(artifact, "configuration_count", len(atoms_list)))
    )
    if len(atoms_list) != frame_count:
        raise PostSelectionExecutionError(
            "Post-selection evaluation artifact frame count mismatch."
        )
    if len(block_ids) != len(atoms_list):
        raise PostSelectionExecutionError(
            "Post-selection evaluation requires one split-exclusion component "
            "identity per evaluated frame."
        )
    from .mace_export import MaceExtxyzPolicy

    keys = MaceExtxyzPolicy() if extxyz_policy is None else extxyz_policy
    artifact_policy = getattr(
        artifact, "extxyz_policy_digest", getattr(artifact, "policy_digest", None)
    )
    if artifact_policy is not None and keys.policy_digest != artifact_policy:
        raise PostSelectionExecutionError(
            "The evaluation artifact was exported under a different ExtXYZ policy "
            "than this evaluation reads it with."
        )
    view = build_evaluation_dataset_view(
        atoms_list,
        energy_key=keys.energy_key,
        forces_key=keys.forces_key,
        stress_key=keys.stress_key,
        focus_atomic_numbers=(),
        condition_keys=(),
    )
    # The evaluation population is scientific membership; the device batch is
    # not. Post-selection evaluation shares the bounded execution boundary with
    # target-size EVAL2 so the same oversized-batch failure cannot reappear on
    # a CV monitor, replay, or outer population.
    raw_predictions = run_bounded_inference(
        provider,
        atoms_list,
        batch_width=execution_batch_width,
        forward=inference_evaluator,
    )
    if len(raw_predictions) != len(atoms_list):
        raise PostSelectionExecutionError(
            "Post-selection inference returned the wrong number of predictions."
        )
    if (
        measurement.dataset_role != str(dataset_role)
        or measurement.artifact != _measurement_artifact_projection(artifact)
        or measurement.reduction_block_digest
        != digest(
            {"schema": "mdstats.eval2-reduction-blocks.v1", "block_ids": [str(v) for v in block_ids]}
        )
    ):
        raise PostSelectionExecutionError(
            "The measurement identity does not describe the evaluated artifact."
        )
    role_digest = measurement.content_digest
    prediction_digest = digest(
        {
            "schema": POST_SELECTION_EVAL_PREDICTIONS_SCHEMA,
            "role_digest": role_digest,
            "predictions": [
                {
                    "energy_ev": float(item.energy_ev),
                    "forces_ev_per_angstrom": np.asarray(
                        item.forces_ev_per_angstrom, dtype=np.float64
                    ).tolist(),
                }
                for item in raw_predictions
            ],
        }
    )
    return eval2_target_metrics_from_prediction_view(
        view,
        raw_predictions,
        block_ids=list(block_ids),
        target_role_digest=role_digest,
        prediction_digest=prediction_digest,
    )


def post_selection_checkpoint_catalog(
    *, run_identity: str, checkpoint_directory: str | os.PathLike[str]
) -> Any:
    """Inventory the durable checkpoint bytes this run actually produced.

    ``run_identity`` names the training root (the pre-fit trajectory for a
    current run).  The glob matches only epoch-stamped checkpoints, which is
    what the TRAIN2 naming convention writes; the continuation companion and
    any other sibling ``.pt`` state is deliberately not a candidate.
    """

    from .campaign_control import inventory_checkpoint_files

    identity = validate_digest(str(run_identity), name="run_identity")
    return inventory_checkpoint_files(
        checkpoint_directory,
        run_plan_digest=identity,
        run_id=identity,
        pattern="*epoch*.pt",
    )


def post_selection_checkpoint_candidates(
    *,
    run_identity: str,
    checkpoint_directory: str | os.PathLike[str],
    runtime_plan: Any,
) -> tuple[Any, ...]:
    """Authenticate this run's complete TRAIN2 history into EVAL2 points.

    Every governed durable checkpoint must become a candidate: a catalogued
    checkpoint the TRAIN2 history cannot turn into a trajectory point is an
    integrity failure, never a silently thinned candidate universe.
    """

    from .eval2 import read_train2_trajectory_points

    catalog = post_selection_checkpoint_catalog(
        run_identity=run_identity, checkpoint_directory=checkpoint_directory
    )
    try:
        canonical_post_selection_head_names(
            target_head_name=runtime_plan.target_head_name,
            replay_head_name=runtime_plan.replay_head_name,
        )
    except TrainingDataInputError as exc:
        raise PostSelectionExecutionError(
            "Post-selection checkpoint trajectory uses a noncanonical "
            "fine-tuning head namespace."
        ) from exc
    points = read_train2_trajectory_points(
        checkpoint_directory,
        checkpoint_catalog=catalog,
        target_head_name=runtime_plan.target_head_name,
    )
    if {item.checkpoint_sha256 for item in points} != {
        item.sha256 for item in catalog.checkpoints
    }:
        raise PostSelectionExecutionError(
            "The TRAIN2 history does not cover every durable P5 checkpoint; the "
            "complete checkpoint universe must be assessed, so no checkpoint is "
            "silently omitted."
        )
    return points


def authenticate_post_selection_provider(
    *,
    materialization: PostSelectionMaterialization,
    materialization_directory: str | os.PathLike[str],
    checkpoint_directory: str | os.PathLike[str],
    checkpoint_name: str,
    checkpoint_sha256: str,
    summary: Any,
    evaluation_model_state: str,
    allow_forward_override: bool,
    checkpoint_epoch: int | None = None,
    foundation_model_path: str | os.PathLike[str] | None = None,
) -> tuple[Any, str]:
    """Authenticate one post-selection checkpoint through the shared provider owner.

    This is the same TRAIN2 provider authentication the target-size screen uses;
    post-selection evaluation does not get a weaker checkpoint-provenance rule
    just because it happens later in the lifecycle.
    """

    from .target_size_execution import authenticate_train2_checkpoint_provider

    material_root = Path(materialization_directory)
    config_path = material_root / materialization.mace_config_relative_path
    config_bytes = config_path.read_bytes()
    if hashlib.sha256(config_bytes).hexdigest() != materialization.mace_config_sha256:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration bytes changed before evaluation."
        )
    config_payload = json.loads(config_bytes.decode("utf-8"))
    if digest(config_payload) != materialization.mace_config_digest:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration content changed before evaluation."
        )
    checkpoint_root = Path(checkpoint_directory)
    effective_summary = summary
    effective_companion_path: Path | None = checkpoint_root / "train2_runtime.pt"
    effective_checkpoint_epoch = checkpoint_epoch
    if effective_checkpoint_epoch is None:
        import re

        match = re.search(r"_epoch-(\d+)\.pt$", Path(checkpoint_name).name)
        if match is not None:
            effective_checkpoint_epoch = int(match.group(1))
    if effective_checkpoint_epoch is not None:
        from .train2_runtime import (
            load_train2_runtime_boundary_summary,
        )

        try:
            candidate_summary = load_train2_runtime_boundary_summary(
                checkpoint_root, effective_checkpoint_epoch
            )
        except TrainingDataInputError:
            latest_epoch = getattr(summary, "raw_checkpoint_epoch", None)
            if latest_epoch != effective_checkpoint_epoch:
                raise PostSelectionExecutionError(
                    "The selected TRAIN2 checkpoint has no authenticated per-epoch runtime boundary."
                )
        else:
            if candidate_summary.raw_checkpoint_sha256 != checkpoint_sha256:
                raise PostSelectionExecutionError(
                    "The selected TRAIN2 checkpoint disagrees with its per-epoch runtime boundary."
                )
            for field in (
                "plan_digest",
                "training_protocol_digest",
                "optimizer_policy_digest",
                "budget_policy_digest",
                "lr_policy_digest",
                "model_architecture_digest",
                "mace_execution_evidence",
            ):
                if getattr(candidate_summary, field, None) != getattr(summary, field, None):
                    raise PostSelectionExecutionError(
                        "The selected TRAIN2 boundary does not belong to the authenticated run authority."
                    )
            summary_epoch = getattr(summary, "raw_checkpoint_epoch", None)
            if isinstance(summary, Mapping) and summary_epoch is None:
                summary_epoch = summary.get("raw_checkpoint_epoch")
            if summary_epoch is None:
                raise PostSelectionExecutionError(
                    "The authenticated TRAIN2 run summary has no latest checkpoint epoch."
                )
            if int(effective_checkpoint_epoch) != int(summary_epoch):
                # The immutable boundary record and raw checkpoint are the
                # complete historical evaluation authority.  Do not retain or
                # consult a second full-model state archive for this path.
                # A bounded forward override may still need the latest-only
                # companion to construct its explicit synthetic provider shell
                # when a toy checkpoint has no native model state.  Native MACE
                # earlier-checkpoint authentication ignores this path and uses
                # the raw checkpoint plus its immutable boundary only.
                effective_companion_path = (
                    checkpoint_root / "train2_runtime.pt"
                    if allow_forward_override
                    else None
                )
    provider, evaluated_digest, _companion = authenticate_train2_checkpoint_provider(
        raw_checkpoint_path=checkpoint_root / checkpoint_name,
        raw_checkpoint_sha256=checkpoint_sha256,
        companion_path=effective_companion_path,
        companion_sha256=(
            None
            if effective_companion_path is None
            else _companion_sha256(effective_companion_path)
        ),
        summary=effective_summary,
        evaluation_model_state=evaluation_model_state,
        config_payload=config_payload,
        allow_forward_override=allow_forward_override,
        raw_checkpoint_epoch=effective_checkpoint_epoch,
        foundation_model_path=foundation_model_path,
    )
    return provider, evaluated_digest


def _companion_sha256(companion: Path) -> str:
    companion = Path(companion)
    if not companion.is_file():
        raise PostSelectionExecutionError(
            f"TRAIN2 continuation companion missing: {companion}."
        )
    return hashlib.sha256(companion.read_bytes()).hexdigest()


RUN_OUTCOME_REPRESENTATIVE_SELECTED = "representative_selected"
RUN_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE = "no_admissible_representative"
POST_SELECTION_CHECKPOINT_DIAGNOSTICS_SCHEMA = (
    "mdstats.post-selection-checkpoint-diagnostics.v1"
)


@dataclass(frozen=True, slots=True)
class PostSelectionCheckpointDiagnostics:
    """Reconstructable per-checkpoint target/replay diagnostics of one run.

    This is *diagnostic* evidence: it records, for every assessed checkpoint,
    target RMSE with its role ceiling and margin, candidate/foundation replay
    RMSE, signed degradation, the warning threshold/margin and hard limit/margin,
    warning codes, hard rejection reasons, and whether the checkpoint is the
    frozen representative.  Nothing references its digest: the warning policy
    has no edge into admissibility, selection, verdicts or publication.
    """

    training_trajectory_identity: str
    run_role: str
    hard_policy: Mapping[str, Any]
    warning_policy: Mapping[str, Any] | None
    rows: tuple[Mapping[str, Any], ...]
    representative_candidate_identity: str | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "training_trajectory_identity",
            validate_digest(
                self.training_trajectory_identity, name="training_trajectory_identity"
            ),
        )
        object.__setattr__(self, "hard_policy", dict(self.hard_policy))
        if self.warning_policy is not None:
            object.__setattr__(self, "warning_policy", dict(self.warning_policy))
        object.__setattr__(self, "rows", tuple(dict(row) for row in self.rows))

    @property
    def representative_warning_codes(self) -> tuple[str, ...]:
        for row in self.rows:
            if row["selected"]:
                return tuple(row["warning_codes"])
        return ()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_CHECKPOINT_DIAGNOSTICS_SCHEMA,
            "training_trajectory_identity": self.training_trajectory_identity,
            "run_role": str(self.run_role),
            "hard_policy": dict(self.hard_policy),
            "warning_policy": (
                None if self.warning_policy is None else dict(self.warning_policy)
            ),
            "rows": [dict(row) for row in self.rows],
            "representative_candidate_identity": self.representative_candidate_identity,
            "decision_authority": "diagnostic_only",
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}


def post_selection_checkpoint_diagnostic_rows(
    candidates: Sequence[Any],
    *,
    hard_policy: Any,
    warning_policy: Any | None,
    representative: Any | None,
) -> tuple[dict[str, Any], ...]:
    """One bounded diagnostic row per assessed checkpoint (epoch order)."""

    rows = []
    selected_identity = (
        None if representative is None else representative.stable_candidate_identity
    )
    ceiling = float(hard_policy.maximum_target_force_rmse_ev_per_angstrom)
    hard_limit = hard_policy.replay_degradation_hard_limit_ev_per_angstrom
    warning = (
        None if warning_policy is None else warning_policy.warning_threshold_ev_per_angstrom
    )
    for item in sorted(candidates, key=lambda value: value.trajectory_point.epoch):
        target = float(item.target_metrics.force_component_rmse_ev_per_angstrom)
        degradation = item.replay_degradation_ev_per_angstrom
        rows.append(
            {
                "epoch": int(item.trajectory_point.epoch),
                "checkpoint_sha256": item.trajectory_point.checkpoint_sha256,
                "candidate_identity": item.stable_candidate_identity,
                "target_force_rmse_ev_per_angstrom": target,
                "target_ceiling_ev_per_angstrom": ceiling,
                "target_margin_ev_per_angstrom": ceiling - target,
                "replay_candidate_force_rmse_ev_per_angstrom": (
                    item.replay_candidate_force_rmse_ev_per_angstrom
                ),
                "replay_foundation_force_rmse_ev_per_angstrom": (
                    item.replay_foundation_force_rmse_ev_per_angstrom
                ),
                "replay_degradation_ev_per_angstrom": degradation,
                "replay_warning_ev_per_angstrom": warning,
                "replay_warning_margin_ev_per_angstrom": (
                    None
                    if warning is None or degradation is None
                    else float(warning) - float(degradation)
                ),
                "replay_hard_limit_ev_per_angstrom": hard_limit,
                "replay_hard_margin_ev_per_angstrom": (
                    None
                    if hard_limit is None or degradation is None
                    else float(hard_limit) - float(degradation)
                ),
                "warning_codes": list(
                    ()
                    if warning_policy is None
                    else warning_policy.diagnostic_warnings(degradation)
                ),
                "hard_rejection_reasons": list(item.rejection_reasons),
                "admissible": bool(item.admissible),
                "selected": item.stable_candidate_identity == selected_identity,
            }
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class PostSelectionRunEvidence:
    """The current outcome-discriminated assessment of one final-production seed.

    It binds its assessment position - selected binding, final-seed assessment
    policy (final hard policy + D2.DEF.059A only), training trajectory and the
    root that holds its bytes, seed - the realized training ancestry it
    assessed, and the complete ordered candidate-record set.  Exactly one of two
    outcomes is representable: ``representative_selected`` names one member of
    that set plus its common-monitor metric; ``no_admissible_representative``
    names none.  Current-CV authorization, publication mode and D2.DEF.059B are
    deliberately not parents: they belong to authorization and aggregate
    publication.  It lives in the evidence store behind the position locator,
    never inside a sealed training root.
    """

    selected_binding_digest: str
    assessment_position_policy_digest: str
    training_trajectory_identity: str
    training_root_identity: str
    optimizer_seed: int
    materialization_digest: str
    runtime_summary_digest: str
    outcome: str
    candidate_record_digests: tuple[str, ...]
    checkpoint_rejection_reasons: tuple[str, ...]
    representative_candidate_identity: str | None = None
    representative_checkpoint_sha256: str | None = None
    representative_record_digest: str | None = None
    monitor_metric_record_digest: str | None = None
    run_role: str = "final_production"

    def __post_init__(self) -> None:
        for name in (
            "selected_binding_digest",
            "assessment_position_policy_digest",
            "training_trajectory_identity",
            "training_root_identity",
            "materialization_digest",
            "runtime_summary_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if str(self.run_role) != "final_production":
            raise TrainingDataInputError(
                "A final-seed assessment carries the final-production role."
            )
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        candidates = tuple(
            validate_digest(str(v), name="candidate_record_digest")
            for v in self.candidate_record_digests
        )
        if not candidates or len(set(candidates)) != len(candidates):
            raise TrainingDataInputError(
                "A final-seed assessment binds a non-empty unique ordered candidate set."
            )
        object.__setattr__(self, "candidate_record_digests", candidates)
        object.__setattr__(
            self,
            "checkpoint_rejection_reasons",
            tuple(sorted({str(v) for v in self.checkpoint_rejection_reasons})),
        )
        representative_fields = (
            "representative_candidate_identity",
            "representative_checkpoint_sha256",
            "representative_record_digest",
            "monitor_metric_record_digest",
        )
        if self.outcome == RUN_OUTCOME_REPRESENTATIVE_SELECTED:
            identity = str(self.representative_candidate_identity or "").strip()
            if not identity:
                raise TrainingDataInputError(
                    "A selected final-seed assessment requires its representative identity."
                )
            object.__setattr__(self, "representative_candidate_identity", identity)
            for name in representative_fields[1:]:
                object.__setattr__(
                    self, name, validate_digest(str(getattr(self, name)), name=name)
                )
            if self.representative_record_digest not in candidates:
                raise TrainingDataInputError(
                    "A selected representative must be a member of the bound candidate set."
                )
        elif self.outcome == RUN_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE:
            if any(getattr(self, name) is not None for name in representative_fields):
                raise TrainingDataInputError(
                    "A no-admissible final-seed assessment carries no representative."
                )
            if not self.checkpoint_rejection_reasons:
                raise TrainingDataInputError(
                    "A no-admissible final-seed assessment names the hard reasons its "
                    "candidates failed."
                )
        else:
            raise TrainingDataInputError(
                f"Unsupported final-seed assessment outcome {self.outcome!r}."
            )

    @property
    def run_identity(self) -> str:
        return self.training_trajectory_identity

    @property
    def selected(self) -> bool:
        return self.outcome == RUN_OUTCOME_REPRESENTATIVE_SELECTED

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_RUN_EVIDENCE_SCHEMA,
            "selected_binding_digest": self.selected_binding_digest,
            "assessment_position_policy_digest": self.assessment_position_policy_digest,
            "training_trajectory_identity": self.training_trajectory_identity,
            "training_root_identity": self.training_root_identity,
            "optimizer_seed": self.optimizer_seed,
            "run_role": self.run_role,
            "materialization_digest": self.materialization_digest,
            "runtime_summary_digest": self.runtime_summary_digest,
            "outcome": self.outcome,
            "candidate_record_digests": list(self.candidate_record_digests),
            "checkpoint_rejection_reasons": list(self.checkpoint_rejection_reasons),
            "representative_candidate_identity": self.representative_candidate_identity,
            "representative_checkpoint_sha256": self.representative_checkpoint_sha256,
            "representative_record_digest": self.representative_record_digest,
            "monitor_metric_record_digest": self.monitor_metric_record_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionRunEvidence":
        # v1 run evidence (selected representative only, no candidate set, bound
        # to the policy-bearing run plan) is historical root-local provenance.
        if payload.get("schema") != POST_SELECTION_RUN_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection run-evidence schema."
            )

        def optional(name: str) -> str | None:
            value = payload.get(name)
            return None if value is None else str(value)

        result = cls(
            selected_binding_digest=str(payload["selected_binding_digest"]),
            assessment_position_policy_digest=str(
                payload["assessment_position_policy_digest"]
            ),
            training_trajectory_identity=str(payload["training_trajectory_identity"]),
            training_root_identity=str(payload["training_root_identity"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            run_role=str(payload["run_role"]),
            materialization_digest=str(payload["materialization_digest"]),
            runtime_summary_digest=str(payload["runtime_summary_digest"]),
            outcome=str(payload["outcome"]),
            candidate_record_digests=tuple(
                str(v) for v in payload["candidate_record_digests"]
            ),
            checkpoint_rejection_reasons=tuple(
                str(v) for v in payload["checkpoint_rejection_reasons"]
            ),
            representative_candidate_identity=optional(
                "representative_candidate_identity"
            ),
            representative_checkpoint_sha256=optional("representative_checkpoint_sha256"),
            representative_record_digest=optional("representative_record_digest"),
            monitor_metric_record_digest=optional("monitor_metric_record_digest"),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection run-evidence digest mismatch."
            )
        return result


__all__ = [
    "EvaluationMeasurementIdentity",
    "POST_SELECTION_CHECKPOINT_DIAGNOSTICS_SCHEMA",
    "PostSelectionCheckpointDiagnostics",
    "post_selection_checkpoint_diagnostic_rows",
    "POST_SELECTION_EVAL_PREDICTIONS_SCHEMA",
    "POST_SELECTION_MATERIALIZATION_SCHEMA_V2",
    "POST_SELECTION_PREPARATION_SCHEMA_V3",
    "POST_SELECTION_RUN_EVIDENCE_SCHEMA_V1",
    "RUN_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE",
    "RUN_OUTCOME_REPRESENTATIVE_SELECTED",
    "transfer_consumer_composition_digest",
    "write_outer_evaluation_transport",
    "DATASET_ROLE_CHECKPOINT_MONITOR",
    "DATASET_ROLE_OUTER_EVALUATION",
    "DATASET_ROLE_TARGET_TRAIN",
    "POST_SELECTION_EVAL_ROLE_SCHEMA",
    "POST_SELECTION_MACE_CONFIG_SCHEMA",
    "POST_SELECTION_MATERIALIZATION_SCHEMA",
    "POST_SELECTION_PREPARATION_SCHEMA",
    "POST_SELECTION_RUN_EVIDENCE_SCHEMA",
    "POST_SELECTION_REPLAY_HEAD_NAME",
    "POST_SELECTION_TARGET_HEAD_NAME",
    "MacePostSelectionTrainer",
    "PostSelectionCancelledError",
    "PostSelectionExecutionError",
    "PostSelectionFittedPreparation",
    "PostSelectionMaterialization",
    "PostSelectionRunEvidence",
    "PostSelectionRungRequest",
    "PostSelectionTrainer",
    "authenticate_post_selection_provider",
    "build_post_selection_foundation_baseline_provider",
    "evaluate_post_selection_dataset",
    "fit_post_selection_preparation",
    "materialize_post_selection_run",
    "post_selection_checkpoint_candidates",
    "post_selection_checkpoint_catalog",
    "post_selection_eval_role_digest",
    "post_selection_mace_run_configuration",
    "post_selection_runtime_plan",
]
