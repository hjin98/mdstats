"""Intake and authentication of the existing final-production publication.

P7 does **not** own a publication.  P5 already freezes the fresh final
production of the CV-accepted method on the full exact ``T_selected``, and P5's
own currentness-fenced completion resolver is the immutable product boundary
qualification consumes.  This module therefore resolves that accepted owner,
re-authenticates every member's frozen representative checkpoint bytes, and
produces one read-only descendant view.  Nothing here can create, mutate,
reorder, or shrink publication membership: there is deliberately no API for it,
and the ordered member set is a pure function of the accepted P5 completion and
the configured committee policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..campaign_post_selection import PostSelectionBinding
from .errors import QualificationError, QualificationLineageError

PUBLISHED_MEMBER_SCHEMA = "mdstats.qualification-published-member.v1"
AUTHENTICATED_PUBLICATION_SCHEMA = "mdstats.qualification-authenticated-publication.v1"

#: The committee policies whose exact member set the accepted predecessor owner
#: can freeze from pre-qualification evidence alone.
@dataclass(frozen=True, slots=True)
class PublishedProductionMember:
    """One frozen, deployable member of the accepted final publication."""

    optimizer_seed: int
    run_identity: str
    run_plan_digest: str
    run_evidence_digest: str
    representative_candidate_identity: str
    representative_checkpoint_sha256: str
    checkpoint_relative_path: str
    target_head_name: str

    def __post_init__(self) -> None:
        for name in (
            "run_identity",
            "run_plan_digest",
            "run_evidence_digest",
            "representative_checkpoint_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        identity = str(self.representative_candidate_identity).strip()
        if not identity:
            raise TrainingDataInputError(
                "A published member requires its frozen representative identity."
            )
        object.__setattr__(self, "representative_candidate_identity", identity)
        relative = str(self.checkpoint_relative_path).strip()
        if not relative or Path(relative).is_absolute():
            raise TrainingDataInputError(
                "A published member's checkpoint path must be run-root relative."
            )
        object.__setattr__(self, "checkpoint_relative_path", relative)
        head = str(self.target_head_name).strip()
        if not head:
            raise TrainingDataInputError(
                "A published member requires the canonical P5 target head name; a "
                "deployed artifact built from another head is a different product."
            )
        object.__setattr__(self, "target_head_name", head)
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PUBLISHED_MEMBER_SCHEMA,
            "optimizer_seed": self.optimizer_seed,
            "run_identity": self.run_identity,
            "run_plan_digest": self.run_plan_digest,
            "run_evidence_digest": self.run_evidence_digest,
            "representative_candidate_identity": self.representative_candidate_identity,
            "representative_checkpoint_sha256": self.representative_checkpoint_sha256,
            "checkpoint_relative_path": self.checkpoint_relative_path,
            "target_head_name": self.target_head_name,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def member_id(self) -> str:
        return f"seed-{self.optimizer_seed}"

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PublishedProductionMember":
        if payload.get("schema") != PUBLISHED_MEMBER_SCHEMA:
            raise TrainingDataSerializationError("Unsupported published-member schema.")
        result = cls(
            optimizer_seed=int(payload["optimizer_seed"]),
            run_identity=str(payload["run_identity"]),
            run_plan_digest=str(payload["run_plan_digest"]),
            run_evidence_digest=str(payload["run_evidence_digest"]),
            representative_candidate_identity=str(payload["representative_candidate_identity"]),
            representative_checkpoint_sha256=str(payload["representative_checkpoint_sha256"]),
            checkpoint_relative_path=str(payload["checkpoint_relative_path"]),
            target_head_name=str(payload["target_head_name"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Published-member digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AuthenticatedFinalPublication:
    """A read-only descendant view of the P5 final-publication decision.

    Every field is copied from the decision the predecessor already took; the
    ordered member set in particular is the decision's own
    ``published_member_ids``, never a set reconstructed by walking runs.  There
    is deliberately no constructor path, deserializer, or mutator that could
    produce a different membership.
    """

    decision_digest: str
    binding: PostSelectionBinding
    final_plan_digest: str
    completion_digest: str
    method_identity_digest: str
    final_production_policy_digest: str
    cv_plan_digest: str
    cv_authorization_digest: str
    committee_policy: str
    decision_policy_identity: str
    m3_membership_digest: str
    target_head_name: str
    members: tuple[PublishedProductionMember, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.binding, PostSelectionBinding):
            raise TrainingDataInputError(
                "An authenticated publication requires the accepted selected binding."
            )
        for name in (
            "decision_digest",
            "final_plan_digest",
            "completion_digest",
            "method_identity_digest",
            "final_production_policy_digest",
            "cv_plan_digest",
            "cv_authorization_digest",
            "m3_membership_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("committee_policy", "decision_policy_identity", "target_head_name"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(f"An authenticated publication requires {name}.")
            object.__setattr__(self, name, value)
        members = tuple(self.members)
        if not members:
            raise QualificationError(
                "An authenticated publication requires at least one frozen member."
            )
        seeds = [member.optimizer_seed for member in members]
        if seeds != sorted(seeds) or len(set(seeds)) != len(seeds):
            raise TrainingDataInputError(
                "Publication members must be uniquely ordered by production seed."
            )
        heads = {member.target_head_name for member in members}
        if heads != {self.target_head_name}:
            raise QualificationLineageError(
                "Every published member must carry the publication's canonical "
                f"target head; found {sorted(heads)}."
            )
        object.__setattr__(self, "members", members)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": AUTHENTICATED_PUBLICATION_SCHEMA,
            "decision_digest": self.decision_digest,
            "selected_binding_digest": self.binding.content_digest,
            "final_plan_digest": self.final_plan_digest,
            "completion_digest": self.completion_digest,
            "method_identity_digest": self.method_identity_digest,
            "final_production_policy_digest": self.final_production_policy_digest,
            "cv_plan_digest": self.cv_plan_digest,
            "cv_authorization_digest": self.cv_authorization_digest,
            "committee_policy": self.committee_policy,
            "decision_policy_identity": self.decision_policy_identity,
            "m3_membership_digest": self.m3_membership_digest,
            "target_head_name": self.target_head_name,
            "members": [member.to_dict() for member in self.members],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def member_digest(self) -> str:
        """Identity of the exact ordered published bytes *and* their head."""

        return digest(
            {
                "schema": "mdstats.post-selection-final-publication-members.v1",
                "target_head_name": self.target_head_name,
                "members": [
                    [member.member_id, member.representative_checkpoint_sha256]
                    for member in self.members
                ],
            }
        )

    def member_for(self, member_id: str) -> PublishedProductionMember:
        for member in self.members:
            if member.member_id == str(member_id):
                return member
        raise QualificationError(f"Unknown publication member {member_id!r}.")

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AuthenticatedFinalPublication":
        raise TrainingDataSerializationError(
            "An authenticated publication is resolved through the accepted P5 owner, "
            "never deserialized: rehydrating one from bytes would create a second "
            "publication authority."
        )


def checkpoint_path_for_member(context: Any, member: PublishedProductionMember) -> Path:
    """Absolute path of one member's frozen representative checkpoint."""

    return context.run_root(member.run_identity) / "checkpoints" / member.checkpoint_relative_path


def authenticate_member_bytes(context: Any, member: PublishedProductionMember) -> str:
    """Re-verify the exact published checkpoint bytes, or fail closed."""

    path = checkpoint_path_for_member(context, member)
    if not path.is_file():
        raise QualificationLineageError(
            f"Published member {member.member_id} is missing its frozen "
            f"representative checkpoint at {path!s}."
        )
    observed = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed != member.representative_checkpoint_sha256:
        raise QualificationLineageError(
            f"Published member {member.member_id} checkpoint bytes changed after "
            "publication; qualification never runs against a mutated product."
        )
    return observed


def resolve_authenticated_final_publication(
    context: Any,
) -> AuthenticatedFinalPublication | None:
    """Resolve the current product through the real accepted P5 publication owner.

    ``None`` means the predecessor has not published a product yet - not that
    qualification failed.  The ordered member set is the decision's own, so
    qualification never reconstructs, ranks, or reorders membership: it copies
    a decision that was already taken from pre-qualification evidence.
    """

    # The accepted P5 completion resolver remains the upstream completion
    # authority; the dedicated publication resolver below consumes the
    # immutable decision derived from that completion.  Keep this explicit in
    # the intake boundary so source-level architecture checks can see that P7
    # has not replaced the predecessor completion owner.
    from ..campaign_post_selection_runtime import (
        resolve_current_final_production_publication,
        resolve_current_final_production_completion,
    )

    _ = resolve_current_final_production_completion

    decision = resolve_current_final_production_publication(context)
    if decision is None:
        return None
    context.selected.require_binding(decision.binding)
    members = tuple(
        PublishedProductionMember(
            optimizer_seed=item.optimizer_seed,
            run_identity=item.run_identity,
            run_plan_digest=item.run_plan_digest,
            run_evidence_digest=item.run_evidence_digest,
            representative_candidate_identity=item.representative_candidate_identity,
            representative_checkpoint_sha256=item.representative_checkpoint_sha256,
            checkpoint_relative_path=item.checkpoint_relative_path,
            target_head_name=decision.target_head_name,
        )
        for item in decision.published_seed_evidence
    )
    publication = AuthenticatedFinalPublication(
        decision_digest=decision.content_digest,
        binding=decision.binding,
        final_plan_digest=decision.final_plan_digest,
        completion_digest=decision.completion_digest,
        method_identity_digest=decision.method_identity_digest,
        final_production_policy_digest=decision.final_production_policy_digest,
        cv_plan_digest=decision.cv_plan_digest,
        cv_authorization_digest=decision.cv_authorization_digest,
        committee_policy=decision.committee_policy,
        decision_policy_identity=decision.decision_policy_identity,
        m3_membership_digest=decision.m3_membership_digest,
        target_head_name=decision.target_head_name,
        members=members,
    )
    if publication.member_digest != decision.member_digest:
        raise QualificationLineageError(
            "The qualification publication view does not reproduce the predecessor "
            "decision's exact ordered member identity."
        )
    for member in publication.members:
        authenticate_member_bytes(context, member)
    return publication


__all__ = [
    "AUTHENTICATED_PUBLICATION_SCHEMA",
    "PUBLISHED_MEMBER_SCHEMA",
    "AuthenticatedFinalPublication",
    "PublishedProductionMember",
    "authenticate_member_bytes",
    "checkpoint_path_for_member",
    "resolve_authenticated_final_publication",
]
