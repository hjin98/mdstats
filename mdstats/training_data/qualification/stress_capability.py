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
    validate_digest,
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
    # The fields below make the decision a claim-scoped object rather than a
    # session-wide singleton.  Defaults preserve deserialization of the
    # earlier in-memory API; new qualification evidence always supplies them.
    qualification_binding_digest: str | None = None
    component: str = ""
    claim_kind: str = ""
    member_id: str | None = None
    geometry_or_cohort_digest: str | None = None
    reference_stress_available: bool | None = None
    # When a claim covers a cohort, retain the per-geometry facts instead of
    # collapsing a mixed periodic/open cohort to the first caller's boolean.
    geometry_applicability: tuple[bool, ...] = ()
    model_stress_by_geometry: tuple[bool, ...] = ()
    reference_stress_available_by_geometry: tuple[bool, ...] = ()

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
        if self.qualification_binding_digest is not None:
            object.__setattr__(
                self,
                "qualification_binding_digest",
                validate_digest(
                    self.qualification_binding_digest,
                    name="qualification_binding_digest",
                ),
            )
        for name in ("component", "claim_kind"):
            object.__setattr__(self, name, str(getattr(self, name)).strip())
        if self.member_id is not None:
            member = str(self.member_id).strip()
            object.__setattr__(self, "member_id", member or None)
        if self.geometry_or_cohort_digest is not None:
            object.__setattr__(
                self,
                "geometry_or_cohort_digest",
                validate_digest(
                    self.geometry_or_cohort_digest,
                    name="geometry_or_cohort_digest",
                ),
            )
        if self.reference_stress_available is not None:
            object.__setattr__(
                self,
                "reference_stress_available",
                bool(self.reference_stress_available),
            )
        for name in (
            "geometry_applicability",
            "model_stress_by_geometry",
            "reference_stress_available_by_geometry",
        ):
            values = tuple(bool(value) for value in getattr(self, name))
            if values and not self.geometry_applicability:
                raise TrainingDataInputError(
                    f"{name} cannot be supplied without geometry_applicability."
                )
            if values and len(values) != len(self.geometry_applicability):
                raise TrainingDataInputError(
                    f"{name} must align with geometry_applicability."
                )
            object.__setattr__(self, name, values)
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

        if self.geometry_applicability:
            return bool(
                self.training_objective_weights_stress
                and any(self.geometry_applicability)
            )
        return bool(
            self.training_objective_weights_stress
            and self.model_reports_stress
            and self.fully_periodic
        )

    @property
    def applicable_geometry_count(self) -> int:
        if self.geometry_applicability:
            return sum(self.geometry_applicability)
        return int(self.applicable)

    @property
    def inapplicable_geometry_count(self) -> int:
        if self.geometry_applicability:
            return len(self.geometry_applicability) - self.applicable_geometry_count
        return 0 if self.applicable else 1

    def geometry_is_applicable(self, index: int) -> bool:
        """Return the exact claim applicability for one cohort geometry."""

        if self.geometry_applicability:
            try:
                return bool(self.geometry_applicability[int(index)])
            except IndexError as exc:
                raise QualificationError(
                    "Stress capability geometry index is outside its authenticated cohort."
                ) from exc
        return bool(self.applicable)

    def reference_stress_is_available(self, index: int) -> bool:
        if self.reference_stress_available_by_geometry:
            try:
                return bool(self.reference_stress_available_by_geometry[int(index)])
            except IndexError as exc:
                raise QualificationError(
                    "Reference stress geometry index is outside its authenticated cohort."
                ) from exc
        return self.reference_evidence_available

    @property
    def required(self) -> bool:
        return bool(self.policy_requires_stress and self.applicable)

    @property
    def deployed_comparable(self) -> bool:
        """Applicable *and* observable through the deployed runtime."""

        return bool(self.applicable and self.runtime_reports_stress)

    @property
    def reference_comparable(self) -> bool:
        return bool(self.applicable and self.reference_evidence_available)

    @property
    def reference_evidence_available(self) -> bool:
        """Whether the exact claim geometry has authenticated reference stress."""

        return bool(
            self.reference_stress_available
            if self.reference_stress_available is not None
            else self.reference_labels_available
        )

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
            "qualification_binding_digest": self.qualification_binding_digest,
            "component": self.component,
            "claim_kind": self.claim_kind,
            "member_id": self.member_id,
            "geometry_or_cohort_digest": self.geometry_or_cohort_digest,
            "reference_stress_available": self.reference_stress_available,
            "geometry_applicability": list(self.geometry_applicability),
            "model_stress_by_geometry": list(self.model_stress_by_geometry),
            "reference_stress_available_by_geometry": list(
                self.reference_stress_available_by_geometry
            ),
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
            qualification_binding_digest=payload.get("qualification_binding_digest"),
            component=str(payload.get("component", "")),
            claim_kind=str(payload.get("claim_kind", "")),
            member_id=payload.get("member_id"),
            geometry_or_cohort_digest=payload.get("geometry_or_cohort_digest"),
            reference_stress_available=payload.get("reference_stress_available"),
            geometry_applicability=tuple(payload.get("geometry_applicability", ())),
            model_stress_by_geometry=tuple(payload.get("model_stress_by_geometry", ())),
            reference_stress_available_by_geometry=tuple(
                payload.get("reference_stress_available_by_geometry", ())
            ),
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
    reference_stress_available: bool | None = None,
    qualification_binding_digest: str | None = None,
    component: str = "",
    claim_kind: str = "",
    member_id: str | None = None,
    geometry_or_cohort_digest: str | None = None,
    reference_stress_available_by_geometry: Sequence[bool] | None = None,
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
    if probe_stresses is not None and len(probe_stresses) != len(probe_atoms):
        raise TrainingDataInputError(
            "Model stress observations must align with the exact claim geometry cohort."
        )

    periodic_by_geometry = tuple(
        bool(np.all(np.asarray(atoms.get_pbc(), dtype=bool))) for atoms in probe_atoms
    )
    model_by_geometry = tuple(
        bool(probe_stresses is not None and index < len(probe_stresses) and probe_stresses[index] is not None)
        for index in range(len(probe_atoms))
    )
    periodic = bool(periodic_by_geometry and all(periodic_by_geometry))
    applicable_by_geometry = tuple(
        bool(trained and periodic_value and model_value)
        for periodic_value, model_value in zip(
            periodic_by_geometry, model_by_geometry, strict=True
        )
    )
    model_reports = bool(
        any(periodic_by_geometry)
        and all(
            model_value
            for periodic_value, model_value in zip(
                periodic_by_geometry, model_by_geometry, strict=True
            )
            if periodic_value
        )
    )
    labels = _frames_carry_stress_labels(context, reference_frame_uids)
    if reference_stress_available_by_geometry is not None:
        exact_reference_by_geometry = tuple(
            bool(value) for value in reference_stress_available_by_geometry
        )
    elif reference_stress_available is None:
        exact_reference_by_geometry = tuple(labels for _ in probe_atoms)
    else:
        exact_reference_by_geometry = tuple(
            bool(reference_stress_available) for _ in probe_atoms
        )
    if exact_reference_by_geometry and len(exact_reference_by_geometry) != len(probe_atoms):
        raise TrainingDataInputError(
            "Reference stress availability must align with the exact claim geometry cohort."
        )
    exact_reference = bool(
        exact_reference_by_geometry
        and all(
            available
            for available, applicable_value in zip(
                exact_reference_by_geometry, applicable_by_geometry, strict=True
            )
            if applicable_value
        )
    )

    declared = policy.get("stress_declared_inapplicable_reason")
    declared_reason = None if declared in (None, "") else str(declared)
    reasons = {
        REASON_TRAINED if trained else REASON_NOT_TRAINED,
        REASON_MODEL_SUPPORTS if model_reports else REASON_MODEL_UNSUPPORTED,
        REASON_PERIODIC if periodic else REASON_NOT_PERIODIC,
        REASON_RUNTIME_SUPPORTS if runtime_reports_stress else REASON_RUNTIME_UNSUPPORTED,
        REASON_REFERENCE_LABELS if labels else REASON_NO_REFERENCE_LABELS,
    }
    if reference_stress_available is not None:
        reasons.add(
            "exact_reference_stress_available"
            if exact_reference
            else "exact_reference_stress_unavailable"
        )
    if any(periodic_by_geometry) and not all(periodic_by_geometry):
        reasons.add("mixed_periodic_applicability")
    if any(applicable_by_geometry) and not all(exact_reference_by_geometry[index] for index, value in enumerate(applicable_by_geometry) if value):
        reasons.add("applicable_geometry_missing_reference_stress")
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
        qualification_binding_digest=qualification_binding_digest,
        component=component,
        claim_kind=claim_kind,
        member_id=member_id,
        geometry_or_cohort_digest=geometry_or_cohort_digest,
        reference_stress_available=exact_reference,
        geometry_applicability=applicable_by_geometry,
        model_stress_by_geometry=model_by_geometry,
        reference_stress_available_by_geometry=exact_reference_by_geometry,
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
