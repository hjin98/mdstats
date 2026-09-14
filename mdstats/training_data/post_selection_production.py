"""The fresh final-production plan.

Final production is new training, not a promotion.  It uses the full exact
``T_selected``, the shared method that cross-validation actually accepted, and
the independent production policy - and it starts from canonical initialization
with a fresh optimizer and fresh RNG state.  A screening trajectory or a CV fold
that happened to score well is not an admissible parent; that is what makes the
production run an honest realization of the validated method rather than a
best-of selection over development runs.

The plan binds exact inherited scientific lineage: the current selected data,
the accepted CV authorization, and the same exact campaign-common target
checkpoint monitor (with its P1 separation evidence) that controlled every CV
checkpoint.  P3 ``M3`` has no role here: it is target-size evidence, not a final
checkpoint-control or seed-ranking parent.
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
from .post_selection_cv_plan import (
    CommonMonitorSeparationEvidence,
    PostSelectionCvPlan,
    require_common_monitor_lineage,
)
from .post_selection_identity import (
    FinalProductionPolicyIdentity,
    PostSelectionMethodIdentity,
)
from .post_selection_run_identity import (
    PostSelectionRunRole,
    post_selection_run_identity,
)

# v2 removes the M3 fields and binds the common target monitor.
FINAL_PRODUCTION_PLAN_SCHEMA = "mdstats.post-selection-final-production-plan.v2"
FINAL_PRODUCTION_RUN_PLAN_SCHEMA = "mdstats.post-selection-final-production-run-plan.v1"


@dataclass(frozen=True, slots=True)
class FinalProductionPlan:
    """One immutable authorization to produce the CV-accepted method."""

    binding: PostSelectionBinding
    method_identity_digest: str
    final_production_policy_digest: str
    cv_plan_digest: str
    cv_authorization_digest: str
    common_monitor_record_digest: str
    monitor_separation_digest: str
    target_membership_digest: str
    n_selected: int
    planned_epochs: int
    required_final_seeds: tuple[int, ...]
    replay_lineage_digest: str | None = None

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
            "common_monitor_record_digest",
            "monitor_separation_digest",
            "target_membership_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.replay_lineage_digest is not None:
            object.__setattr__(
                self,
                "replay_lineage_digest",
                validate_digest(
                    self.replay_lineage_digest, name="replay_lineage_digest"
                ),
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
        payload: dict[str, Any] = {
            "schema": FINAL_PRODUCTION_PLAN_SCHEMA,
            "binding": self.binding.to_dict(),
            "method_identity_digest": self.method_identity_digest,
            "final_production_policy_digest": self.final_production_policy_digest,
            "cv_plan_digest": self.cv_plan_digest,
            "cv_authorization_digest": self.cv_authorization_digest,
            "common_monitor_record_digest": self.common_monitor_record_digest,
            "monitor_separation_digest": self.monitor_separation_digest,
            "target_membership_digest": self.target_membership_digest,
            "n_selected": self.n_selected,
            "planned_epochs": self.planned_epochs,
            "required_final_seeds": list(self.required_final_seeds),
        }
        if self.replay_lineage_digest is not None:
            payload["replay_lineage_digest"] = self.replay_lineage_digest
        return payload

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
            common_monitor_record_digest=str(payload["common_monitor_record_digest"]),
            monitor_separation_digest=str(payload["monitor_separation_digest"]),
            target_membership_digest=str(payload["target_membership_digest"]),
            n_selected=int(payload["n_selected"]),
            planned_epochs=int(payload["planned_epochs"]),
            required_final_seeds=tuple(int(v) for v in payload["required_final_seeds"]),
            replay_lineage_digest=(
                None
                if payload.get("replay_lineage_digest") is None
                else str(payload["replay_lineage_digest"])
            ),
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


def build_final_production_plan(
    context: CurrentSelectedTrainingContext,
    method: PostSelectionMethodIdentity,
    policy: FinalProductionPolicyIdentity,
    *,
    cv_plan: PostSelectionCvPlan,
    cv_acceptance: CvCampaignAcceptance,
    common_monitor: Any,
    monitor_separation: CommonMonitorSeparationEvidence,
    replay_lineage_digest: str | None = None,
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
    if cv_plan.replay_lineage_digest != replay_lineage_digest:
        raise PostSelectionError(
            "The accepted cross-validation plan bound a different replay lineage "
            "than current replay authority resolves."
        )
    # Final checkpoint control uses the exact monitor CV used.
    require_common_monitor_lineage(
        cv_plan, common_monitor=common_monitor, monitor_separation=monitor_separation
    )
    return FinalProductionPlan(
        binding=context.binding,
        method_identity_digest=method.content_digest,
        final_production_policy_digest=policy.content_digest,
        cv_plan_digest=cv_plan.content_digest,
        cv_authorization_digest=cv_acceptance.content_digest,
        common_monitor_record_digest=common_monitor.content_digest,
        monitor_separation_digest=monitor_separation.content_digest,
        target_membership_digest=context.selected_membership_digest,
        n_selected=context.n_selected,
        planned_epochs=policy.production_max_num_epochs,
        required_final_seeds=policy.production_seeds,
        replay_lineage_digest=replay_lineage_digest,
    )


def validate_final_production_plan(
    plan: FinalProductionPlan,
    context: CurrentSelectedTrainingContext,
    *,
    method: PostSelectionMethodIdentity,
    common_monitor: Any,
    monitor_separation: CommonMonitorSeparationEvidence,
    policy: FinalProductionPolicyIdentity | None = None,
    replay_lineage_digest: str | None = None,
) -> None:
    """Re-authenticate a stored final plan against freshly resolved authority.

    Restart authenticates the full parent chain rather than trusting the stored
    plan digest, so a changed selected generation, a changed common monitor, or
    a changed method rejects the plan instead of silently continuing.
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
    if (
        replay_lineage_digest is not None
        and plan.replay_lineage_digest != replay_lineage_digest
    ):
        raise PostSelectionError(
            "The stored final-production plan binds a different replay lineage."
        )
    require_common_monitor_lineage(
        plan, common_monitor=common_monitor, monitor_separation=monitor_separation
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
    "validate_final_production_plan",
]
