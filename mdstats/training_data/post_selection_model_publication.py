"""The subordinate P5 record of the materialized full-model representation.

``FinalProductionPublicationDecision`` remains the sole owner of *which*
seeds ship and *which* representative checkpoint each contributes.  That
decision is a scientific selection, and it stays free of serialized-artifact
identity: a pickle rebuilt under a newer Torch is the same product, and a
decision that changed whenever the bytes did would stale every descendant for
a representation event.

What the decision does not provide is a usable product.  MACE's own terminal
``.model`` belongs to the trainer's last epoch, which is routinely *not* the
P5-selected representative.  This module owns the immutable record of the
explicit full MACE models materialized from the exact selected checkpoints, and
the path-independent ``model_artifact_set_digest`` that deployment descendants
bind.  It is subordinate to the decision in both directions: it may represent
the decided member set, and it may never add, drop, reorder or re-rank it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import PostSelectionError
from .model_artifact_trust import normalize_relative_artifact_path

FINAL_PRODUCTION_MODEL_MEMBER_SCHEMA = (
    "mdstats.post-selection-final-production-model-member.v1"
)
FINAL_PRODUCTION_MODEL_PUBLICATION_SCHEMA = (
    "mdstats.post-selection-final-production-model-publication.v1"
)
MODEL_ARTIFACT_SET_SCHEMA = (
    "mdstats.post-selection-final-production-model-artifact-set.v1"
)

#: The only serialization format this cycle publishes: a complete MACE model
#: object reloadable through ``torch.load(..., weights_only=False)``.
SERIALIZATION_FORMAT_TORCH_FULL_MODEL = "torch.full-model.pickle.v1"

#: Identity of the serializer implementation itself.  It is representation
#: compatibility metadata, never scientific or deployment identity.
MODEL_SERIALIZER_IDENTITY = "mdstats.p5-final-production-model-serializer.2026-09.v1"

#: Operator-facing projection name at the stable ``N_<size>`` level.
PUBLICATION_PROJECTION_FILENAME = "publication.json"
PUBLICATION_PROJECTION_SCHEMA = (
    "mdstats.post-selection-final-production-model-projection.v1"
)

#: Accepted P5 evaluation-state conventions, mirrored from the provider owner.
_EVALUATION_MODEL_STATES = ("live", "ema")

#: Accepted uniform learned-model dtypes.
_MODEL_DTYPES = ("float32", "float64")


def production_models_relative_root(generation: int | str, n_selected: int) -> str:
    """``production/g<generation>/N_<size>`` beneath ``CampaignPaths.models``."""

    return f"production/g{int(generation)}/N_{int(n_selected)}"


def decision_directory_relative_path(
    generation: int | str, n_selected: int, final_publication_decision_digest: str
) -> str:
    """The immutable per-decision directory, keyed by the *full* decision digest.

    Truncation is display-only everywhere in this feature: an authoritative
    immutable path that depended on a digest prefix would make two distinct
    decisions collide by construction.
    """

    value = validate_digest(
        str(final_publication_decision_digest), name="final_publication_decision_digest"
    )
    return f"{production_models_relative_root(generation, n_selected)}/decision-{value}"


def model_artifact_basename(
    *, member_id: str, model_sha256: str, artifact_locator_token: str
) -> str:
    """The immutable leaf name of one published member model.

    It composes already-known parent/member identity, the *full* serialized
    model SHA, and a fresh collision-resistant locator token.  The locator is
    what makes same-SHA recovery possible: a corrupted occupied leaf whose
    rebuild deterministically reproduces the identical model SHA is republished
    at a new name rather than overwritten, so byte corruption can never wedge
    reclosure.  The name deliberately does not depend on the model-publication
    record digest, because that record contains this path.
    """

    member = str(member_id).strip()
    if not member or "/" in member or member in (".", ".."):
        raise TrainingDataInputError("A model artifact member id must be one path-safe name.")
    sha = validate_digest(str(model_sha256), name="model_sha256")
    token = validate_locator_token(artifact_locator_token)
    return f"{member}-{sha}-artifact-{token}.model"


def validate_locator_token(value: str) -> str:
    """One non-authoritative collision-resistant create-once locator token."""

    token = str(value).strip().lower()
    if len(token) != 32 or any(char not in "0123456789abcdef" for char in token):
        raise TrainingDataInputError(
            "An artifact locator token is 32 lowercase hexadecimal characters."
        )
    return token


def fresh_locator_token() -> str:
    """Generate one fresh locator token before placement."""

    import secrets

    return secrets.token_hex(16)


@dataclass(frozen=True, slots=True)
class PublishedModelMember:
    """One published member's exact selected state and its serialized product."""

    member_id: str
    optimizer_seed: int
    run_identity: str
    representative_checkpoint_relative_path: str
    representative_checkpoint_sha256: str
    evaluation_model_state: str
    evaluated_model_state_digest: str
    model_execution_architecture_digest: str
    model_state_sha256: str
    model_dtype: str
    artifact_locator_token: str
    model_relative_path: str
    model_sha256: str
    model_size_bytes: int

    def __post_init__(self) -> None:
        for name in (
            "run_identity",
            "representative_checkpoint_sha256",
            "evaluated_model_state_digest",
            "model_execution_architecture_digest",
            "model_state_sha256",
            "model_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        member = str(self.member_id).strip()
        if not member:
            raise TrainingDataInputError("A published model member requires its member id.")
        object.__setattr__(self, "member_id", member)
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        checkpoint = str(self.representative_checkpoint_relative_path).strip()
        if not checkpoint or PurePosixPath(checkpoint).is_absolute():
            raise TrainingDataInputError(
                "A published model member's checkpoint path must be run-root relative."
            )
        object.__setattr__(self, "representative_checkpoint_relative_path", checkpoint)
        state = str(self.evaluation_model_state).strip()
        if state not in _EVALUATION_MODEL_STATES:
            raise TrainingDataInputError(
                f"Unsupported evaluation model state {state!r}; the serialized product "
                "always carries the exact state P5 evaluated."
            )
        object.__setattr__(self, "evaluation_model_state", state)
        dtype = str(self.model_dtype).strip()
        if dtype not in _MODEL_DTYPES:
            raise TrainingDataInputError(
                f"Unsupported published model dtype {dtype!r}."
            )
        object.__setattr__(self, "model_dtype", dtype)
        object.__setattr__(
            self, "artifact_locator_token", validate_locator_token(self.artifact_locator_token)
        )
        relative = normalize_relative_artifact_path(self.model_relative_path)
        if PurePosixPath(relative).name != model_artifact_basename(
            member_id=member,
            model_sha256=self.model_sha256,
            artifact_locator_token=self.artifact_locator_token,
        ):
            raise TrainingDataInputError(
                "A published model path must carry its member, full model SHA and "
                "artifact locator token; a bare mutable seed path is never authority."
            )
        object.__setattr__(self, "model_relative_path", relative)
        size = int(self.model_size_bytes)
        if size <= 0:
            raise TrainingDataInputError("A published model records a positive byte count.")
        object.__setattr__(self, "model_size_bytes", size)

    @property
    def deployment_source_identity(self) -> dict[str, Any]:
        """Exactly the member material deployment currentness may depend on.

        Path and locator are excluded on purpose: relocating an intact
        workspace must not invalidate numerical evidence, while any change in
        executable model bytes must.
        """

        return {
            "member_id": self.member_id,
            "representative_checkpoint_sha256": self.representative_checkpoint_sha256,
            "evaluation_model_state": self.evaluation_model_state,
            "evaluated_model_state_digest": self.evaluated_model_state_digest,
            "model_execution_architecture_digest": self.model_execution_architecture_digest,
            "model_state_sha256": self.model_state_sha256,
            "model_dtype": self.model_dtype,
            "model_sha256": self.model_sha256,
            "model_size_bytes": self.model_size_bytes,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_PRODUCTION_MODEL_MEMBER_SCHEMA,
            "member_id": self.member_id,
            "optimizer_seed": self.optimizer_seed,
            "run_identity": self.run_identity,
            "representative_checkpoint_relative_path": (
                self.representative_checkpoint_relative_path
            ),
            "representative_checkpoint_sha256": self.representative_checkpoint_sha256,
            "evaluation_model_state": self.evaluation_model_state,
            "evaluated_model_state_digest": self.evaluated_model_state_digest,
            "model_execution_architecture_digest": self.model_execution_architecture_digest,
            "model_state_sha256": self.model_state_sha256,
            "model_dtype": self.model_dtype,
            "artifact_locator_token": self.artifact_locator_token,
            "model_relative_path": self.model_relative_path,
            "model_sha256": self.model_sha256,
            "model_size_bytes": self.model_size_bytes,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PublishedModelMember":
        if payload.get("schema") != FINAL_PRODUCTION_MODEL_MEMBER_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported final-production model-member schema."
            )
        result = cls(
            member_id=str(payload["member_id"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            run_identity=str(payload["run_identity"]),
            representative_checkpoint_relative_path=str(
                payload["representative_checkpoint_relative_path"]
            ),
            representative_checkpoint_sha256=str(
                payload["representative_checkpoint_sha256"]
            ),
            evaluation_model_state=str(payload["evaluation_model_state"]),
            evaluated_model_state_digest=str(payload["evaluated_model_state_digest"]),
            model_execution_architecture_digest=str(
                payload["model_execution_architecture_digest"]
            ),
            model_state_sha256=str(payload["model_state_sha256"]),
            model_dtype=str(payload["model_dtype"]),
            artifact_locator_token=str(payload["artifact_locator_token"]),
            model_relative_path=str(payload["model_relative_path"]),
            model_sha256=str(payload["model_sha256"]),
            model_size_bytes=int(payload["model_size_bytes"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Final-production model-member digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class FinalProductionModelPublication:
    """The immutable subordinate record of one decision's serialized products."""

    selected_binding_digest: str
    final_publication_decision_digest: str
    final_publication_member_digest: str
    target_head_name: str
    members: tuple[PublishedModelMember, ...]
    serialization_format: str
    serializer_identity: str
    serialization_runtime: Mapping[str, Any]
    published_at: str

    def __post_init__(self) -> None:
        for name in (
            "selected_binding_digest",
            "final_publication_decision_digest",
            "final_publication_member_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        head = str(self.target_head_name).strip()
        if not head:
            raise TrainingDataInputError(
                "A model publication requires the canonical target head name."
            )
        object.__setattr__(self, "target_head_name", head)
        members = tuple(self.members)
        if not members:
            raise PostSelectionError(
                "A model publication represents a non-empty decided member set."
            )
        ids = [member.member_id for member in members]
        if len(set(ids)) != len(ids):
            raise PostSelectionError(
                "A model publication never carries a duplicate member identity."
            )
        paths = [member.model_relative_path for member in members]
        if len(set(paths)) != len(paths):
            raise PostSelectionError(
                "Two published members cannot name the same immutable model artifact."
            )
        object.__setattr__(self, "members", members)
        fmt = str(self.serialization_format).strip()
        if fmt != SERIALIZATION_FORMAT_TORCH_FULL_MODEL:
            raise TrainingDataSerializationError(
                f"Unsupported published-model serialization format {fmt!r}."
            )
        object.__setattr__(self, "serialization_format", fmt)
        serializer = str(self.serializer_identity).strip()
        if not serializer:
            raise TrainingDataInputError("A model publication requires its serializer identity.")
        object.__setattr__(self, "serializer_identity", serializer)
        runtime = dict(self.serialization_runtime)
        object.__setattr__(self, "serialization_runtime", runtime)
        published = str(self.published_at).strip()
        if not published:
            raise TrainingDataInputError("A model publication requires its publication time.")
        object.__setattr__(self, "published_at", published)

    def member_for(self, member_id: str) -> PublishedModelMember:
        for member in self.members:
            if member.member_id == str(member_id):
                return member
        raise PostSelectionError(f"Unknown published model member {member_id!r}.")

    @property
    def member_ids(self) -> tuple[str, ...]:
        return tuple(member.member_id for member in self.members)

    @property
    def model_artifact_set_digest(self) -> str:
        """Path-independent identity of the exact serialized representation.

        Deployment descendants bind this, never the paths.  It excludes
        ``model_relative_path``, the locator token, timestamps and the
        diagnostic exporter/runtime metadata, so a workspace relocation or a
        locator repair with identical bytes does not force requalification -
        while any changed executable model byte does.

        This is not a second member-selection identity:
        ``FinalProductionPublicationDecision.member_digest`` remains the sole
        checkpoint/member authority.
        """

        return digest(
            {
                "schema": MODEL_ARTIFACT_SET_SCHEMA,
                "final_publication_decision_digest": self.final_publication_decision_digest,
                "target_head_name": self.target_head_name,
                "members": [member.deployment_source_identity for member in self.members],
            }
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_PRODUCTION_MODEL_PUBLICATION_SCHEMA,
            "selected_binding_digest": self.selected_binding_digest,
            "final_publication_decision_digest": self.final_publication_decision_digest,
            "final_publication_member_digest": self.final_publication_member_digest,
            "target_head_name": self.target_head_name,
            "members": [member.to_dict() for member in self.members],
            "serialization_format": self.serialization_format,
            "serializer_identity": self.serializer_identity,
            "serialization_runtime": dict(self.serialization_runtime),
            "published_at": self.published_at,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalProductionModelPublication":
        if payload.get("schema") != FINAL_PRODUCTION_MODEL_PUBLICATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported final-production model-publication schema."
            )
        result = cls(
            selected_binding_digest=str(payload["selected_binding_digest"]),
            final_publication_decision_digest=str(
                payload["final_publication_decision_digest"]
            ),
            final_publication_member_digest=str(
                payload["final_publication_member_digest"]
            ),
            target_head_name=str(payload["target_head_name"]),
            members=tuple(
                PublishedModelMember.from_dict(item) for item in payload["members"]
            ),
            serialization_format=str(payload["serialization_format"]),
            serializer_identity=str(payload["serializer_identity"]),
            serialization_runtime=dict(payload.get("serialization_runtime") or {}),
            published_at=str(payload["published_at"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Final-production model-publication digest mismatch."
            )
        return result


def validate_model_publication_against_decision(
    record: FinalProductionModelPublication, decision: Any
) -> None:
    """Enforce - not merely document - subordination to the exact P5 decision.

    A subordinate record may represent the decision; it may never redefine
    committee membership, order, checkpoint ancestry, target head or learned
    state.  The constructor cannot see the decision, so this is the one place
    that relation is proved, and every resolver/constructor path calls it.
    """

    mismatches: dict[str, tuple[Any, Any]] = {
        "selected_binding_digest": (
            record.selected_binding_digest,
            decision.binding.content_digest,
        ),
        "final_publication_decision_digest": (
            record.final_publication_decision_digest,
            decision.content_digest,
        ),
        "final_publication_member_digest": (
            record.final_publication_member_digest,
            decision.member_digest,
        ),
        "target_head_name": (record.target_head_name, decision.target_head_name),
    }
    stale = sorted(name for name, (stored, current) in mismatches.items() if stored != current)
    if stale:
        raise PostSelectionError(
            "The final-production model publication does not bind its parent "
            f"decision ({stale}); a representation never redefines the decision."
        )
    expected_ids = tuple(decision.published_member_ids)
    if record.member_ids != expected_ids:
        raise PostSelectionError(
            "The final-production model publication member set "
            f"{list(record.member_ids)} is not the decision's exact ordered set "
            f"{list(expected_ids)}; representation never adds, drops or reorders "
            "committee membership."
        )
    for member, evidence in zip(record.members, decision.published_seed_evidence, strict=True):
        if member.member_id != evidence.member_id:
            raise PostSelectionError(
                "Published model members are not in exact decision member order."
            )
        seed_mismatch = {
            "optimizer_seed": (member.optimizer_seed, evidence.optimizer_seed),
            "run_identity": (member.run_identity, evidence.run_identity),
            "representative_checkpoint_relative_path": (
                member.representative_checkpoint_relative_path,
                evidence.checkpoint_relative_path,
            ),
            "representative_checkpoint_sha256": (
                member.representative_checkpoint_sha256,
                evidence.representative_checkpoint_sha256,
            ),
        }
        bad = sorted(name for name, (left, right) in seed_mismatch.items() if left != right)
        if bad:
            raise PostSelectionError(
                f"Published model member {member.member_id} disagrees with the "
                f"decision's published seed evidence ({bad})."
            )


__all__ = [
    "FINAL_PRODUCTION_MODEL_MEMBER_SCHEMA",
    "FINAL_PRODUCTION_MODEL_PUBLICATION_SCHEMA",
    "MODEL_ARTIFACT_SET_SCHEMA",
    "MODEL_SERIALIZER_IDENTITY",
    "PUBLICATION_PROJECTION_FILENAME",
    "PUBLICATION_PROJECTION_SCHEMA",
    "SERIALIZATION_FORMAT_TORCH_FULL_MODEL",
    "FinalProductionModelPublication",
    "PublishedModelMember",
    "decision_directory_relative_path",
    "fresh_locator_token",
    "model_artifact_basename",
    "production_models_relative_root",
    "validate_locator_token",
    "validate_model_publication_against_decision",
]
