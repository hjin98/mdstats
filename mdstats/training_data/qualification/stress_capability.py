"""Whether stress is a real capability of this product, not a config switch.

A boolean in the qualification configuration cannot decide whether stress is
scientifically applicable: an operator could clear it and silently drop a
channel the product actually trained, exports, and could be judged on. So the
decision is resolved before any component executes, from facts about the
accepted product and the runtime that will execute it:

* did the accepted training objective actually weight stress;
* do the reference frames this qualification uses carry stress labels;
* does the authenticated in-framework model return a stress tensor;
* is the configuration periodic, so that a Cauchy stress is even defined;
* can the deployed runtime report stress.

Policy composes with those facts in one direction only. It may *require* stress,
and it may record a scientifically justified reason that a channel is
inapplicable, but it cannot relabel an available trained channel as
``not_applicable`` to avoid qualifying it. The resulting decision is immutable,
carries its reasons, and participates in component identity, so changing any
input stales the stress-bearing descendants rather than silently reinterpreting
existing evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from .errors import QualificationError

STRESS_CAPABILITY_SCHEMA = "mdstats.qualification-stress-capability.v1"

#: Why stress is or is not applicable.  These are facts, and they are recorded
#: whether they support or oppose applicability, so an audit can see the whole
#: basis rather than only the deciding one.
REASON_TRAINED = "training_objective_weights_stress"
REASON_NOT_TRAINED = "training_objective_does_not_weight_stress"
REASON_REFERENCE_LABELS = "reference_frames_carry_stress_labels"
REASON_NO_REFERENCE_LABELS = "reference_frames_carry_no_stress_labels"
REASON_MODEL_SUPPORTS = "authenticated_model_returns_stress"
REASON_MODEL_UNSUPPORTED = "authenticated_model_returns_no_stress"
REASON_PERIODIC = "configuration_is_periodic_in_every_axis"
REASON_NOT_PERIODIC = "configuration_is_not_fully_periodic"
REASON_RUNTIME_SUPPORTS = "deployed_runtime_reports_stress"
REASON_RUNTIME_UNSUPPORTED = "deployed_runtime_reports_no_stress"
REASON_POLICY_REQUIRES = "frozen_policy_requires_stress"
REASON_POLICY_DECLARED_INAPPLICABLE = "frozen_policy_declared_inapplicable"


@dataclass(frozen=True, slots=True)
class StressCapabilityDecision:
    """One immutable, reasoned decision about the stress channel."""

    training_objective_weights_stress: bool
    reference_labels_available: bool
    model_reports_stress: bool
    fully_periodic: bool
    runtime_reports_stress: bool
    policy_requires_stress: bool
    policy_declared_inapplicable_reason: str | None
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "training_objective_weights_stress",
            "reference_labels_available",
            "model_reports_stress",
            "fully_periodic",
            "runtime_reports_stress",
            "policy_requires_stress",
        ):
            object.__setattr__(self, name, bool(getattr(self, name)))
        reason = self.policy_declared_inapplicable_reason
        object.__setattr__(
            self,
            "policy_declared_inapplicable_reason",
            None if reason is None else (str(reason).strip() or None),
        )
        object.__setattr__(
            self, "reason_codes", tuple(sorted({str(v) for v in self.reason_codes}))
        )
        if self.policy_requires_stress and not self.applicable:
            # A policy that requires stress on a product that cannot produce it
            # is a contradiction the operator has to resolve, not something to
            # resolve silently in either direction.
            raise QualificationError(
                "The frozen qualification policy requires stress, but this product "
                f"cannot supply it ({sorted(self.reason_codes)}). Either the product "
                "or the policy is wrong; qualification does not choose."
            )

    @property
    def applicable(self) -> bool:
        """Stress is applicable when the product can actually produce it."""

        return bool(
            self.training_objective_weights_stress
            and self.model_reports_stress
            and self.fully_periodic
        )

    @property
    def required(self) -> bool:
        return bool(self.policy_requires_stress and self.applicable)

    @property
    def deployed_comparable(self) -> bool:
        """Applicable *and* observable through the deployed runtime."""

        return bool(self.applicable and self.runtime_reports_stress)

    @property
    def reference_comparable(self) -> bool:
        return bool(self.applicable and self.reference_labels_available)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": STRESS_CAPABILITY_SCHEMA,
            "training_objective_weights_stress": self.training_objective_weights_stress,
            "reference_labels_available": self.reference_labels_available,
            "model_reports_stress": self.model_reports_stress,
            "fully_periodic": self.fully_periodic,
            "runtime_reports_stress": self.runtime_reports_stress,
            "policy_requires_stress": self.policy_requires_stress,
            "policy_declared_inapplicable_reason": self.policy_declared_inapplicable_reason,
            "applicable": self.applicable,
            "required": self.required,
            "reason_codes": list(self.reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StressCapabilityDecision":
        if payload.get("schema") != STRESS_CAPABILITY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported qualification stress-capability schema."
            )
        result = cls(
            training_objective_weights_stress=bool(
                payload["training_objective_weights_stress"]
            ),
            reference_labels_available=bool(payload["reference_labels_available"]),
            model_reports_stress=bool(payload["model_reports_stress"]),
            fully_periodic=bool(payload["fully_periodic"]),
            runtime_reports_stress=bool(payload["runtime_reports_stress"]),
            policy_requires_stress=bool(payload["policy_requires_stress"]),
            policy_declared_inapplicable_reason=payload.get(
                "policy_declared_inapplicable_reason"
            ),
            reason_codes=tuple(payload.get("reason_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Qualification stress-capability digest mismatch."
            )
        return result


def _frames_carry_stress_labels(context: Any, frame_uids: Sequence[str]) -> bool:
    index = context.selected.authorities.frame_array_index
    for frame_uid in frame_uids:
        entry = index.get(str(frame_uid))
        if entry is None:
            continue
        _record, frame_data, _local = entry
        if getattr(frame_data, "stresses_ev_per_angstrom3", None) is not None:
            return True
    return False


def resolve_stress_capability(
    context: Any,
    *,
    policy: Mapping[str, Any],
    probe_atoms: Sequence[Any],
    probe_stresses: Sequence[Any] | None,
    runtime_reports_stress: bool,
    reference_frame_uids: Sequence[str] = (),
) -> StressCapabilityDecision:
    """Decide the stress channel from product/runtime capability plus policy."""

    common = context.method_policies.common_training
    objective = getattr(common, "objective_policy", None)
    if objective is None:
        raise QualificationError(
            "The accepted training method exposes no objective policy, so stress "
            "applicability cannot be resolved from product capability."
        )
    trained = float(getattr(objective, "stress_weight", 0.0)) > 0.0

    model_reports = bool(
        probe_stresses is not None
        and len(probe_stresses) > 0
        and all(item is not None for item in probe_stresses)
    )
    periodic = bool(
        probe_atoms
        and all(np.all(np.asarray(atoms.get_pbc(), dtype=bool)) for atoms in probe_atoms)
    )
    labels = _frames_carry_stress_labels(context, reference_frame_uids)

    declared = policy.get("stress_declared_inapplicable_reason")
    declared_reason = None if declared in (None, "") else str(declared)
    reasons = {
        REASON_TRAINED if trained else REASON_NOT_TRAINED,
        REASON_MODEL_SUPPORTS if model_reports else REASON_MODEL_UNSUPPORTED,
        REASON_PERIODIC if periodic else REASON_NOT_PERIODIC,
        REASON_RUNTIME_SUPPORTS if runtime_reports_stress else REASON_RUNTIME_UNSUPPORTED,
        REASON_REFERENCE_LABELS if labels else REASON_NO_REFERENCE_LABELS,
    }
    if bool(policy.get("stress_required", False)):
        reasons.add(REASON_POLICY_REQUIRES)
    if declared_reason is not None:
        reasons.add(REASON_POLICY_DECLARED_INAPPLICABLE)
    return StressCapabilityDecision(
        training_objective_weights_stress=trained,
        reference_labels_available=labels,
        model_reports_stress=model_reports,
        fully_periodic=periodic,
        runtime_reports_stress=bool(runtime_reports_stress),
        policy_requires_stress=bool(policy.get("stress_required", False)),
        policy_declared_inapplicable_reason=declared_reason,
        reason_codes=tuple(reasons),
    )


__all__ = [
    "REASON_MODEL_SUPPORTS",
    "REASON_MODEL_UNSUPPORTED",
    "REASON_NOT_PERIODIC",
    "REASON_NOT_TRAINED",
    "REASON_NO_REFERENCE_LABELS",
    "REASON_PERIODIC",
    "REASON_POLICY_DECLARED_INAPPLICABLE",
    "REASON_POLICY_REQUIRES",
    "REASON_REFERENCE_LABELS",
    "REASON_RUNTIME_SUPPORTS",
    "REASON_RUNTIME_UNSUPPORTED",
    "REASON_TRAINED",
    "STRESS_CAPABILITY_SCHEMA",
    "StressCapabilityDecision",
    "resolve_stress_capability",
]
