"""The fresh final-production plan.

Final production is new training, not a promotion.  It uses the full exact
``T_selected``, the shared method that cross-validation actually accepted, and
the independent production policy - and it starts from canonical initialization
with a fresh optimizer and fresh RNG state.  A screening trajectory or a CV fold
that happened to score well is not an admissible parent; that is what makes the
production run an honest realization of the validated method rather than a
best-of selection over development runs.

The plan binds exact inherited scientific lineage: the current selected data,
the accepted CV authorization, and the frozen P2 ``M3`` reserve that serves as
final development/model-selection evidence.  M3 lives here, in the plan, and not
in the production policy: it is inherited P2/P4 evidence, not a knob.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionBinding,
    PostSelectionError,
)
from .post_selection_cv_acceptance import (
    CvCampaignAcceptance,
    require_cv_acceptance_for_method,
)
from .post_selection_cv_plan import PostSelectionCvPlan
from .post_selection_identity import (
    FinalProductionPolicyIdentity,
    PostSelectionMethodIdentity,
)
from .post_selection_run_identity import (
    PostSelectionRunRole,
    post_selection_run_identity,
)

FINAL_PRODUCTION_PLAN_SCHEMA = "mdstats.post-selection-final-production-plan.v1"
FINAL_PRODUCTION_RUN_PLAN_SCHEMA = "mdstats.post-selection-final-production-run-plan.v1"


@dataclass(frozen=True, slots=True)
class FinalProductionPlan:
    """One immutable authorization to produce the CV-accepted method."""

    binding: PostSelectionBinding
    method_identity_digest: str
    final_production_policy_digest: str
    cv_plan_digest: str
    cv_authorization_digest: str
    m3_evaluation_size: int
    m3_membership_digest: str
    target_membership_digest: str
    n_selected: int
    planned_epochs: int
    required_final_seeds: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.binding, PostSelectionBinding):
            raise TrainingDataInputError(
                "A final-production plan requires the authenticated selected binding."
            )
        for name in (
            "method_identity_digest",
            "final_production_policy_digest",
            "cv_plan_digest",
            "cv_authorization_digest",
            "m3_membership_digest",
            "target_membership_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.target_membership_digest != self.binding.selected_membership_digest:
            raise PostSelectionError(
                "Final production trains on the full exact T_selected; its target "
                "membership must be the authenticated selected membership."
            )
        n_selected = int(self.n_selected)
        if n_selected != self.binding.n_selected:
            raise PostSelectionError(
                "Final production must use every selected frame, not a fold subset."
            )
        object.__setattr__(self, "n_selected", n_selected)
        size = int(self.m3_evaluation_size)
        if size <= 0:
            raise TrainingDataInputError("m3_evaluation_size must be positive.")
        object.__setattr__(self, "m3_evaluation_size", size)
        planned = int(self.planned_epochs)
        if planned <= 0:
            raise TrainingDataInputError("planned_epochs must be positive.")
        object.__setattr__(self, "planned_epochs", planned)
        seeds = tuple(sorted(int(v) for v in self.required_final_seeds))
        if not seeds or len(set(seeds)) != len(seeds):
            raise TrainingDataInputError(
                "A final-production plan requires a non-empty unique seed matrix."
            )
        object.__setattr__(self, "required_final_seeds", seeds)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_PRODUCTION_PLAN_SCHEMA,
            "binding": self.binding.to_dict(),
            "method_identity_digest": self.method_identity_digest,
            "final_production_policy_digest": self.final_production_policy_digest,
            "cv_plan_digest": self.cv_plan_digest,
            "cv_authorization_digest": self.cv_authorization_digest,
            "m3_evaluation_size": self.m3_evaluation_size,
            "m3_membership_digest": self.m3_membership_digest,
            "target_membership_digest": self.target_membership_digest,
            "n_selected": self.n_selected,
            "planned_epochs": self.planned_epochs,
            "required_final_seeds": list(self.required_final_seeds),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalProductionPlan":
        if payload.get("schema") != FINAL_PRODUCTION_PLAN_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported final-production plan schema."
            )
        result = cls(
            binding=PostSelectionBinding.from_dict(payload["binding"]),
            method_identity_digest=str(payload["method_identity_digest"]),
            final_production_policy_digest=str(
                payload["final_production_policy_digest"]
            ),
            cv_plan_digest=str(payload["cv_plan_digest"]),
            cv_authorization_digest=str(payload["cv_authorization_digest"]),
            m3_evaluation_size=int(payload["m3_evaluation_size"]),
            m3_membership_digest=str(payload["m3_membership_digest"]),
            target_membership_digest=str(payload["target_membership_digest"]),
            n_selected=int(payload["n_selected"]),
            planned_epochs=int(payload["planned_epochs"]),
            required_final_seeds=tuple(int(v) for v in payload["required_final_seeds"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Final-production plan digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class FinalProductionRunPlan:
    """One exact fresh final-production job."""

    final_plan_digest: str
    method_identity_digest: str
    final_production_policy_digest: str
    selected_binding_digest: str
    optimizer_seed: int
    planned_epochs: int
    run_identity: str
    run_role: str = PostSelectionRunRole.FINAL_PRODUCTION.value

    def __post_init__(self) -> None:
        for name in (
            "final_plan_digest",
            "method_identity_digest",
            "final_production_policy_digest",
            "selected_binding_digest",
            "run_identity",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if (
            PostSelectionRunRole(self.run_role)
            is not PostSelectionRunRole.FINAL_PRODUCTION
        ):
            raise TrainingDataInputError(
                "A final-production run plan must carry the final-production role."
            )
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        planned = int(self.planned_epochs)
        if planned <= 0:
            raise TrainingDataInputError("planned_epochs must be positive.")
        object.__setattr__(self, "planned_epochs", planned)
        expected = post_selection_run_identity(
            role=PostSelectionRunRole.FINAL_PRODUCTION,
            plan_digest=self.final_plan_digest,
            optimizer_seed=self.optimizer_seed,
        )
        if expected != self.run_identity:
            raise TrainingDataInputError(
                "Final-production run identity does not match its (plan, seed) position."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_PRODUCTION_RUN_PLAN_SCHEMA,
            "final_plan_digest": self.final_plan_digest,
            "method_identity_digest": self.method_identity_digest,
            "final_production_policy_digest": self.final_production_policy_digest,
            "selected_binding_digest": self.selected_binding_digest,
            "optimizer_seed": self.optimizer_seed,
            "planned_epochs": self.planned_epochs,
            "run_role": PostSelectionRunRole(self.run_role).value,
            "run_identity": self.run_identity,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalProductionRunPlan":
        if payload.get("schema") != FINAL_PRODUCTION_RUN_PLAN_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported final-production run-plan schema."
            )
        result = cls(
            final_plan_digest=str(payload["final_plan_digest"]),
            method_identity_digest=str(payload["method_identity_digest"]),
            final_production_policy_digest=str(
                payload["final_production_policy_digest"]
            ),
            selected_binding_digest=str(payload["selected_binding_digest"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            planned_epochs=int(payload["planned_epochs"]),
            run_role=str(payload["run_role"]),
            run_identity=str(payload["run_identity"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Final-production run-plan digest mismatch."
            )
        return result


def frozen_m3_development_evidence(
    context: CurrentSelectedTrainingContext,
) -> tuple[int, tuple[str, ...], str]:
    """Return the frozen P2 ``M3`` reserve used for final model selection.

    ``M3`` already participated in target-size development, so it is legitimate
    development/model-selection evidence and explicitly *not* independent
    validation.  It is inherited from the accepted P2 experiment definition, so
    nothing here chooses or configures it.
    """

    definition = context.definition
    sizes = tuple(int(v) for v in definition.policy.evaluation_sizes)
    if not sizes:
        raise PostSelectionError(
            "The accepted P2 experiment definition exposes no evaluation ladder, so "
            "no frozen M3 development evidence is available for final model "
            "selection."
        )
    m3 = int(definition.policy.m3)
    membership = tuple(definition.evaluation_membership(m3))
    overlap = set(membership) & set(context.selected_membership)
    if overlap:
        raise PostSelectionError(
            "The frozen M3 development reserve overlaps T_selected; final "
            "model-selection evidence may not contain training frames."
        )
    return m3, membership, definition.evaluation_order.membership_digest(m3)


def build_final_production_plan(
    context: CurrentSelectedTrainingContext,
    method: PostSelectionMethodIdentity,
    policy: FinalProductionPolicyIdentity,
    *,
    cv_plan: PostSelectionCvPlan,
    cv_acceptance: CvCampaignAcceptance,
) -> FinalProductionPlan:
    """Authorize fresh full-``T_selected`` production under the accepted method.

    The CV authorization is checked before the plan exists, so an unaccepted or
    method-mismatched cross-validation cannot produce a plan that later looks
    legitimate.
    """

    context.require_binding(cv_plan.binding)
    require_cv_acceptance_for_method(
        cv_acceptance,
        plan=cv_plan,
        method_identity_digest=method.content_digest,
        selected_binding_digest=context.binding.content_digest,
    )
    if cv_plan.method_identity_digest != method.content_digest:
        raise PostSelectionError(
            "The cross-validation plan validated a different shared method."
        )
    m3_size, _m3_membership, m3_digest = frozen_m3_development_evidence(context)
    return FinalProductionPlan(
        binding=context.binding,
        method_identity_digest=method.content_digest,
        final_production_policy_digest=policy.content_digest,
        cv_plan_digest=cv_plan.content_digest,
        cv_authorization_digest=cv_acceptance.content_digest,
        m3_evaluation_size=m3_size,
        m3_membership_digest=m3_digest,
        target_membership_digest=context.selected_membership_digest,
        n_selected=context.n_selected,
        planned_epochs=policy.production_max_num_epochs,
        required_final_seeds=policy.production_seeds,
    )


def validate_final_production_plan(
    plan: FinalProductionPlan,
    context: CurrentSelectedTrainingContext,
    *,
    method: PostSelectionMethodIdentity,
    policy: FinalProductionPolicyIdentity | None = None,
) -> None:
    """Re-authenticate a stored final plan against freshly resolved authority.

    Restart authenticates the full parent chain rather than trusting the stored
    plan digest, so a changed selected generation, a changed M3 lineage, or a
    changed method rejects the plan instead of silently continuing.
    """

    context.require_binding(plan.binding)
    if plan.method_identity_digest != method.content_digest:
        raise PostSelectionError(
            "The stored final-production plan binds a different shared method than "
            "the current configuration resolves."
        )
    if policy is not None and plan.final_production_policy_digest != (
        policy.content_digest
    ):
        raise PostSelectionError(
            "The stored final-production plan binds a different production policy; "
            "its descendants are stale and must be rebuilt."
        )
    m3_size, _membership, m3_digest = frozen_m3_development_evidence(context)
    if plan.m3_evaluation_size != m3_size or plan.m3_membership_digest != m3_digest:
        raise PostSelectionError(
            "The stored final-production plan binds retired M3 development lineage; "
            "the current authenticated predecessor evidence is different."
        )
    if plan.target_membership_digest != context.selected_membership_digest:
        raise PostSelectionError(
            "The stored final-production plan binds a different T_selected."
        )


def build_final_production_run_plan(
    plan: FinalProductionPlan, *, optimizer_seed: int
) -> FinalProductionRunPlan:
    """Bind one fresh final-production job below its plan."""

    if int(optimizer_seed) not in plan.required_final_seeds:
        raise PostSelectionError(
            f"Final-production seed {int(optimizer_seed)} is not in the configured "
            f"production seed matrix {list(plan.required_final_seeds)}."
        )
    plan_digest = plan.content_digest
    return FinalProductionRunPlan(
        final_plan_digest=plan_digest,
        method_identity_digest=plan.method_identity_digest,
        final_production_policy_digest=plan.final_production_policy_digest,
        selected_binding_digest=plan.binding.content_digest,
        optimizer_seed=int(optimizer_seed),
        planned_epochs=plan.planned_epochs,
        run_identity=post_selection_run_identity(
            role=PostSelectionRunRole.FINAL_PRODUCTION,
            plan_digest=plan_digest,
            optimizer_seed=int(optimizer_seed),
        ),
    )


__all__ = [
    "FINAL_PRODUCTION_PLAN_SCHEMA",
    "FINAL_PRODUCTION_RUN_PLAN_SCHEMA",
    "FinalProductionPlan",
    "FinalProductionRunPlan",
    "build_final_production_plan",
    "build_final_production_run_plan",
    "frozen_m3_development_evidence",
    "validate_final_production_plan",
]
