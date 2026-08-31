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
from ..post_selection_production import build_final_production_run_plan
from .errors import QualificationError, QualificationLineageError

PUBLISHED_MEMBER_SCHEMA = "mdstats.qualification-published-member.v1"
AUTHENTICATED_PUBLICATION_SCHEMA = "mdstats.qualification-authenticated-publication.v1"

#: The committee policies whose exact member set the accepted predecessor owner
#: can freeze from pre-qualification evidence alone.
_SUPPORTED_COMMITTEE_POLICIES = ("all_qualified_final_seeds",)


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
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Published-member digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AuthenticatedFinalPublication:
    """A read-only descendant view of the accepted P5 final publication."""

    binding: PostSelectionBinding
    final_plan_digest: str
    completion_digest: str
    method_identity_digest: str
    final_production_policy_digest: str
    cv_plan_digest: str
    cv_authorization_digest: str
    committee_policy: str
    m3_membership_digest: str
    members: tuple[PublishedProductionMember, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.binding, PostSelectionBinding):
            raise TrainingDataInputError(
                "An authenticated publication requires the accepted selected binding."
            )
        for name in (
            "final_plan_digest",
            "completion_digest",
            "method_identity_digest",
            "final_production_policy_digest",
            "cv_plan_digest",
            "cv_authorization_digest",
            "m3_membership_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        policy = str(self.committee_policy).strip()
        if policy not in _SUPPORTED_COMMITTEE_POLICIES:
            raise QualificationError(
                f"Committee policy {policy!r} cannot be frozen from the accepted "
                "predecessor final-production evidence. Qualification consumes an "
                "already decided member set; it has no authority to rank or select "
                "publication members."
            )
        object.__setattr__(self, "committee_policy", policy)
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
        object.__setattr__(self, "members", members)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": AUTHENTICATED_PUBLICATION_SCHEMA,
            "selected_binding_digest": self.binding.content_digest,
            "final_plan_digest": self.final_plan_digest,
            "completion_digest": self.completion_digest,
            "method_identity_digest": self.method_identity_digest,
            "final_production_policy_digest": self.final_production_policy_digest,
            "cv_plan_digest": self.cv_plan_digest,
            "cv_authorization_digest": self.cv_authorization_digest,
            "committee_policy": self.committee_policy,
            "m3_membership_digest": self.m3_membership_digest,
            "members": [member.to_dict() for member in self.members],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def member_digest(self) -> str:
        """Identity of the exact ordered published bytes."""

        return digest(
            {
                "members": [
                    [member.member_id, member.representative_checkpoint_sha256]
                    for member in self.members
                ]
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
    """Resolve the current publication through the real accepted P5 owner.

    ``None`` means the predecessor product does not exist yet - not that
    qualification failed.  Every identity in the returned view is re-derived
    from the accepted owner on each call, so a stale generation is unreachable
    rather than merely rejected.
    """

    from ..campaign_post_selection_runtime import (
        resolve_current_final_production_completion,
    )
    from ..post_selection_execution import post_selection_checkpoint_catalog

    completion = resolve_current_final_production_completion(context)
    if completion is None:
        return None
    plan = completion.plan
    context.selected.require_binding(plan.binding)
    policy = context.production_policy
    if tuple(plan.required_final_seeds) != tuple(policy.production_seeds):
        raise QualificationLineageError(
            "The current final-production plan seed matrix does not match the "
            "configured production policy; the publication is not authentic."
        )
    members: list[PublishedProductionMember] = []
    for evidence in completion.runs:
        run_plan = build_final_production_run_plan(plan, optimizer_seed=_seed_for(plan, evidence))
        if run_plan.content_digest != evidence.run_plan_digest:
            raise QualificationLineageError(
                "Final-production run evidence does not bind its own run plan."
            )
        catalog = post_selection_checkpoint_catalog(
            run_plan=run_plan,
            checkpoint_directory=context.run_root(run_plan.run_identity) / "checkpoints",
        )
        record = catalog.checkpoint_by_sha256(evidence.representative_checkpoint_sha256)
        members.append(
            PublishedProductionMember(
                optimizer_seed=run_plan.optimizer_seed,
                run_identity=run_plan.run_identity,
                run_plan_digest=run_plan.content_digest,
                run_evidence_digest=evidence.content_digest,
                representative_candidate_identity=evidence.representative_candidate_identity,
                representative_checkpoint_sha256=evidence.representative_checkpoint_sha256,
                checkpoint_relative_path=record.relative_path,
            )
        )
    _m3_size, _m3_membership, m3_digest = _frozen_m3(context)
    publication = AuthenticatedFinalPublication(
        binding=plan.binding,
        final_plan_digest=plan.content_digest,
        completion_digest=completion.content_digest,
        method_identity_digest=plan.method_identity_digest,
        final_production_policy_digest=plan.final_production_policy_digest,
        cv_plan_digest=plan.cv_plan_digest,
        cv_authorization_digest=plan.cv_authorization_digest,
        committee_policy=policy.committee_policy,
        m3_membership_digest=m3_digest,
        members=tuple(members),
    )
    for member in publication.members:
        authenticate_member_bytes(context, member)
    return publication


def _seed_for(plan: Any, evidence: Any) -> int:
    """Recover which required seed produced this evidence, by run identity."""

    for seed in plan.required_final_seeds:
        if build_final_production_run_plan(plan, optimizer_seed=seed).run_identity == (
            evidence.run_identity
        ):
            return int(seed)
    raise QualificationLineageError(
        "Final-production evidence does not correspond to any required production seed."
    )


def _frozen_m3(context: Any) -> tuple[int, tuple[str, ...], str]:
    from ..post_selection_production import frozen_m3_development_evidence

    return frozen_m3_development_evidence(context.selected)


__all__ = [
    "AUTHENTICATED_PUBLICATION_SCHEMA",
    "PUBLISHED_MEMBER_SCHEMA",
    "AuthenticatedFinalPublication",
    "PublishedProductionMember",
    "authenticate_member_bytes",
    "checkpoint_path_for_member",
    "resolve_authenticated_final_publication",
]
