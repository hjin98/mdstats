"""The one-shot locked interpolation test and its explicit activation.

Locked evidence is only meaningful while it is unseen.  Activation is therefore
a separate, explicit, recorded event that binds the exact product bytes, the
exact reserved cohort, the exact policy, and the moment of opening - so "this
was decided after the product was frozen" is checkable rather than asserted.
Activation is refused twice for the same publication and cohort generation, and
a locked failure has exactly one meaning: this exact published product is
rejected.  It can never be repaired by choosing another member, loosening the
policy, or retraining and calling the same revealed cohort fresh again.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .components import (
    COMPONENT_LOCKED_TEST,
    ComponentStatus,
    QualificationComponentEvidence,
    build_component_evidence,
)
from .errors import QualificationActivationError
from .geometry import atoms_for_frame, labels_for_frame
from .providers import energy_of, forces_of, member_provider, predict_all

LOCKED_ACTIVATION_SCHEMA = "mdstats.qualification-locked-activation.v1"


@dataclass(frozen=True, slots=True)
class LockedActivationRecord:
    """Immutable proof that locked evidence was opened after the freeze."""

    selected_binding_digest: str
    binding_digest: str
    publication_digest: str
    publication_member_digest: str
    locked_role_digest: str
    locked_policy_digest: str
    environment_digest: str
    executable_digest: str
    prerequisite_component_digests: tuple[str, ...]
    activated_at: str

    def __post_init__(self) -> None:
        for name in (
            "selected_binding_digest",
            "binding_digest",
            "publication_digest",
            "publication_member_digest",
            "locked_role_digest",
            "locked_policy_digest",
            "environment_digest",
            "executable_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        prerequisites = tuple(
            validate_digest(str(v), name="prerequisite_component_digest")
            for v in sorted(self.prerequisite_component_digests)
        )
        object.__setattr__(self, "prerequisite_component_digests", prerequisites)
        stamp = str(self.activated_at).strip()
        if not stamp:
            raise TrainingDataInputError("Locked activation requires an activation timestamp.")
        object.__setattr__(self, "activated_at", stamp)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LOCKED_ACTIVATION_SCHEMA,
            "selected_binding_digest": self.selected_binding_digest,
            "binding_digest": self.binding_digest,
            "publication_digest": self.publication_digest,
            "publication_member_digest": self.publication_member_digest,
            "locked_role_digest": self.locked_role_digest,
            "locked_policy_digest": self.locked_policy_digest,
            "environment_digest": self.environment_digest,
            "executable_digest": self.executable_digest,
            "prerequisite_component_digests": list(self.prerequisite_component_digests),
            "activated_at": self.activated_at,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def cohort_generation_identity(self) -> str:
        """What "the same reserved locked cohort" means, exactly.

        Product identity is intentionally absent.  Once this role is opened,
        replacing the publication must not make the same held-out cohort appear
        fresh; the activation's product fields still record which product was
        actually tested.
        """

        return digest(
            {
                "schema": "mdstats.qualification-locked-cohort.v2",
                "locked_role_digest": self.locked_role_digest,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LockedActivationRecord":
        if payload.get("schema") != LOCKED_ACTIVATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported locked-activation schema.")
        result = cls(
            selected_binding_digest=str(payload["selected_binding_digest"]),
            binding_digest=str(payload["binding_digest"]),
            publication_digest=str(payload["publication_digest"]),
            publication_member_digest=str(payload["publication_member_digest"]),
            locked_role_digest=str(payload["locked_role_digest"]),
            locked_policy_digest=str(payload["locked_policy_digest"]),
            environment_digest=str(payload["environment_digest"]),
            executable_digest=str(payload["executable_digest"]),
            prerequisite_component_digests=tuple(payload["prerequisite_component_digests"]),
            activated_at=str(payload["activated_at"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Locked-activation digest mismatch.")
        return result


def locked_policy_digest(binding: Any) -> str:
    return digest({"locked": dict(binding.specification.component_policy(COMPONENT_LOCKED_TEST))})


def build_locked_activation(
    session: Any, *, prerequisite_component_digests: tuple[str, ...]
) -> LockedActivationRecord:
    binding = session.binding
    return LockedActivationRecord(
        selected_binding_digest=binding.selected_binding_digest,
        binding_digest=binding.content_digest,
        publication_digest=binding.publication_digest,
        publication_member_digest=binding.publication_member_digest,
        locked_role_digest=binding.evidence_roles.locked_digest,
        locked_policy_digest=locked_policy_digest(binding),
        environment_digest=binding.environment.content_digest,
        executable_digest=binding.executable.content_digest,
        prerequisite_component_digests=prerequisite_component_digests,
        activated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def qualify_locked_test(
    session: Any, activation: LockedActivationRecord
) -> QualificationComponentEvidence:
    """Evaluate the frozen publication once on the reserved locked cohort."""

    binding = session.binding
    policy = binding.specification.component_policy(COMPONENT_LOCKED_TEST)
    frames = binding.evidence_roles.locked_frame_uids
    if len(frames) < int(policy["minimum_frames"]):
        raise QualificationActivationError(
            "The reserved LOCKED_INTERPOLATION_TEST role does not contain enough "
            "frames for the frozen locked policy. A locked test is never run on a "
            "substitute cohort."
        )
    atoms_list = [atoms_for_frame(session.context, uid) for uid in frames]
    labels = [labels_for_frame(session.context, uid) for uid in frames]

    member_rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for member in session.publication.members:
        with member_provider(session.context, member) as provider:
            predictions = predict_all(session.context, provider, atoms_list)
        force_errors = np.concatenate(
            [
                (forces_of(prediction) - np.asarray(reference, dtype=np.float64)).reshape(-1)
                for prediction, (_energy, reference) in zip(predictions, labels)
            ]
        )
        energy_errors = np.asarray(
            [
                (energy_of(prediction) - float(energy)) / max(len(atoms), 1)
                for prediction, (energy, _forces), atoms in zip(predictions, labels, atoms_list)
            ],
            dtype=np.float64,
        )
        force_rmse = float(np.sqrt(np.mean(force_errors**2)))
        energy_rmse = float(np.sqrt(np.mean(energy_errors**2)))
        passed = bool(
            np.isfinite(force_rmse)
            and np.isfinite(energy_rmse)
            and force_rmse <= float(policy["force_component_rmse_maximum_ev_per_angstrom"])
            and energy_rmse <= float(policy["energy_rmse_maximum_ev_per_atom"])
        )
        if not passed:
            failures.append(member.member_id)
        member_rows.append(
            {
                "member_id": member.member_id,
                "force_component_rmse_ev_per_angstrom": force_rmse,
                "energy_rmse_ev_per_atom": energy_rmse,
                "passed": passed,
            }
        )

    status = ComponentStatus.PASSED if not failures else ComponentStatus.REJECTED
    return build_component_evidence(
        component=COMPONENT_LOCKED_TEST,
        binding=binding,
        status=status,
        reason_code=("locked_test_within_policy" if not failures else "locked_test_rejected"),
        detail=(
            ""
            if not failures
            else (
                "The locked interpolation test rejected the exact published product. "
                "This cohort is now revealed: it cannot be reused as a fresh locked "
                "test for a retrained product without new independent evidence."
            )
        ),
        metrics={
            "locked_frame_count": len(frames),
            "member_count": len(member_rows),
            "failed_members": failures,
        },
        payload={
            "activation_digest": activation.content_digest,
            "cohort_generation_identity": activation.cohort_generation_identity,
            "locked_role_digest": binding.evidence_roles.locked_digest,
            "members": member_rows,
        },
        component_input_digest=session.component_input_digest(
            COMPONENT_LOCKED_TEST,
            None,
            extra={"activation_digest": activation.content_digest},
        ),
    )


__all__ = [
    "LOCKED_ACTIVATION_SCHEMA",
    "LockedActivationRecord",
    "build_locked_activation",
    "locked_policy_digest",
    "qualify_locked_test",
]
