"""The one canonical membership-obligation authority for ``pi_train``.

D1 section 5 / D2 section 6 define every hard membership obligation by a
scientific support locus ``L(o)``, an exact incidence set ``A(o)`` on the
current ``P_train`` and a positive minimum ``k(o)``.  Automatic obligations
(current P2 conditions, P1 correlation units, recognized structural events and
both sides of every extent channel) and the explicit current P2
``hard_support_obligations`` are projected here exactly once.  FEAS1, MVIDX,
MVSEL2, REPAIR2 and MVQUAL consume this authority; none of them re-derives an
obligation.

Canonicalization is exactly D2 section 6: source IDs are unique inside their
namespace, grouping is by locus identity only (never by incidence equality),
equal loci must have identical incidence, the effective minimum is
``max(k)`` and aliases/minima remain provenance only.  A purported same-locus
disagreement fails closed; distinct loci with identical incidence stay
distinct.  Profile-environment obligations have no active provider in the
current protocol and are therefore absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .coverage_reference import TargetCoverageReference

TARGET_OBLIGATION_SCHEMA = "mdstats.target-membership-obligation.v1"
TARGET_OBLIGATION_AUTHORITY_SCHEMA = "mdstats.target-membership-obligation-authority.v1"
TARGET_OBLIGATION_POLICY_VERSION = "mdstats.target-order.canonical-obligations.v1"

_EXTENT_TOLERANCE = 1.0e-12
_P_TRAIN_DOMAIN = "exact_p_train"

KIND_CONDITION = "condition"
KIND_CONDITION_ATTRIBUTE = "condition_attribute"
KIND_CORRELATION_UNIT = "correlation_unit"
KIND_STRUCTURAL_EVENT = "structural_event"
KIND_EXTENT_LOWER = "extent_lower"
KIND_EXTENT_UPPER = "extent_upper"
_KINDS = frozenset(
    {
        KIND_CONDITION,
        KIND_CONDITION_ATTRIBUTE,
        KIND_CORRELATION_UNIT,
        KIND_STRUCTURAL_EVENT,
        KIND_EXTENT_LOWER,
        KIND_EXTENT_UPPER,
    }
)
NAMESPACE_AUTOMATIC = "automatic"
NAMESPACE_EXPLICIT = "explicit"


@dataclass(frozen=True, slots=True)
class ObligationLocus:
    """``L(o)``: scientific identity independent of strength and source ID."""

    kind: str
    applicability_scope: str
    family_id: str | None
    target: str
    relation: str
    applicability_domain: str = _P_TRAIN_DOMAIN

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise TrainingDataInputError(f"Unknown membership-obligation kind {self.kind!r}.")
        for name in ("applicability_scope", "target", "relation", "applicability_domain"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"Membership-obligation locus {name} must be non-empty.")
        if self.family_id is not None and not str(self.family_id).strip():
            raise TrainingDataInputError("Membership-obligation locus family must be non-empty when supplied.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "applicability_scope": self.applicability_scope,
            "family_id": self.family_id,
            "target": self.target,
            "relation": self.relation,
            "applicability_domain": self.applicability_domain,
        }

    @property
    def digest(self) -> str:
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObligationLocus":
        return cls(
            kind=str(payload["kind"]),
            applicability_scope=str(payload["applicability_scope"]),
            family_id=None if payload.get("family_id") is None else str(payload["family_id"]),
            target=str(payload["target"]),
            relation=str(payload["relation"]),
            applicability_domain=str(payload["applicability_domain"]),
        )


@dataclass(frozen=True, slots=True)
class ObligationSource:
    """Provenance of one source requirement merged into a canonical locus."""

    namespace: str
    source_id: str
    minimum_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "source_id": self.source_id,
            "minimum_count": int(self.minimum_count),
        }


@dataclass(frozen=True, slots=True, eq=False)
class TargetMembershipObligation:
    """One canonical hard obligation ``(L, A, k)`` with provenance."""

    locus: ObligationLocus
    minimum_count: int
    candidate_indices: np.ndarray | Sequence[int]
    sources: tuple[ObligationSource, ...]
    obligation_policy_digest: str
    _obligation_id: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        minimum = int(self.minimum_count)
        if isinstance(self.minimum_count, bool) or minimum < 1:
            raise TrainingDataInputError("Canonical obligation minimum must be a positive integer.")
        rows = np.asarray(self.candidate_indices, dtype=np.int64)
        if rows.ndim != 1 or rows.size == 0:
            raise TrainingDataInputError(
                f"Canonical obligation {self.locus.kind}:{self.locus.target} has no support in exact P_train."
            )
        if np.any(rows[1:] <= rows[:-1]) or int(rows[0]) < 0:
            raise TrainingDataInputError("Canonical obligation incidence must be sorted, unique and nonnegative.")
        rows = np.ascontiguousarray(rows, dtype="<i8")
        rows.setflags(write=False)
        sources = tuple(sorted(self.sources, key=lambda item: (item.namespace, item.source_id)))
        if not sources or minimum != max(item.minimum_count for item in sources):
            raise TrainingDataInputError("Canonical obligation minimum must be the strongest source minimum.")
        object.__setattr__(self, "minimum_count", minimum)
        object.__setattr__(self, "candidate_indices", rows)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(
            self,
            "obligation_policy_digest",
            validate_digest(self.obligation_policy_digest, name="obligation_policy_digest"),
        )
        # D2 section 6 step 10: one deterministic ID binding locus, effective
        # minimum, incidence, applicability and governing policy identity.
        object.__setattr__(
            self,
            "_obligation_id",
            f"{self.locus.kind}:"
            + digest(
                {
                    "locus": self.locus.to_dict(),
                    "minimum_count": minimum,
                    "incidence_digest": digest(rows.tolist()),
                    "obligation_policy_digest": self.obligation_policy_digest,
                }
            )[:32],
        )

    @property
    def obligation_id(self) -> str:
        return self._obligation_id

    @property
    def minimum_selected_frames(self) -> int:
        return self.minimum_count

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_OBLIGATION_SCHEMA,
            "obligation_id": self.obligation_id,
            "locus": self.locus.to_dict(),
            "minimum_count": self.minimum_count,
            "candidate_indices": self.candidate_indices.tolist(),
            "sources": [item.to_dict() for item in self.sources],
            "obligation_policy_digest": self.obligation_policy_digest,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMembershipObligation":
        if payload.get("schema") != TARGET_OBLIGATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported membership-obligation schema.")
        result = cls(
            locus=ObligationLocus.from_dict(payload["locus"]),
            minimum_count=int(payload["minimum_count"]),
            candidate_indices=tuple(int(v) for v in payload["candidate_indices"]),
            sources=tuple(
                ObligationSource(str(item["namespace"]), str(item["source_id"]), int(item["minimum_count"]))
                for item in payload["sources"]
            ),
            obligation_policy_digest=str(payload["obligation_policy_digest"]),
        )
        if payload.get("obligation_id") != result.obligation_id or payload.get(
            "content_digest"
        ) != result.to_dict()["content_digest"]:
            raise TrainingDataSerializationError("Membership-obligation identity mismatch.")
        return result


@dataclass(frozen=True, slots=True, eq=False)
class TargetMembershipObligationAuthority:
    """The canonical obligation set on the reference's exact candidate order."""

    target_coverage_reference_digest: str
    frame_domain_digest: str
    candidate_count: int
    obligation_policy_digest: str
    obligations: tuple[TargetMembershipObligation, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("target_coverage_reference_digest", "frame_domain_digest", "obligation_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        count = int(self.candidate_count)
        obligations = tuple(sorted(self.obligations, key=lambda item: item.obligation_id))
        if count < 1 or not obligations:
            raise TrainingDataInputError("The canonical obligation authority requires candidates and obligations.")
        if len({item.obligation_id for item in obligations}) != len(obligations):
            raise TrainingDataInputError("Canonical obligation IDs collided.")
        if len({item.locus.digest for item in obligations}) != len(obligations):
            raise TrainingDataInputError("A canonical locus appears more than once.")
        for item in obligations:
            if int(item.candidate_indices[-1]) >= count:
                raise TrainingDataInputError("Canonical obligation incidence lies outside exact P_train.")
            if item.obligation_policy_digest != self.obligation_policy_digest:
                raise TrainingDataInputError("Canonical obligation policy lineage mismatch.")
        object.__setattr__(self, "candidate_count", count)
        object.__setattr__(self, "obligations", obligations)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_OBLIGATION_AUTHORITY_SCHEMA,
            "policy_version": TARGET_OBLIGATION_POLICY_VERSION,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "frame_domain_digest": self.frame_domain_digest,
            "candidate_count": self.candidate_count,
            "obligation_policy_digest": self.obligation_policy_digest,
            "obligations": [item.to_dict() for item in self.obligations],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMembershipObligationAuthority":
        if payload.get("schema") != TARGET_OBLIGATION_AUTHORITY_SCHEMA or payload.get(
            "policy_version"
        ) != TARGET_OBLIGATION_POLICY_VERSION:
            raise TrainingDataSerializationError("Unsupported canonical obligation authority schema.")
        result = cls(
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            frame_domain_digest=str(payload["frame_domain_digest"]),
            candidate_count=int(payload["candidate_count"]),
            obligation_policy_digest=str(payload["obligation_policy_digest"]),
            obligations=tuple(TargetMembershipObligation.from_dict(item) for item in payload["obligations"]),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataSerializationError("Canonical obligation authority digest mismatch.")
        return result

    def selected_counts(self, selected_candidate_indices: Sequence[int]) -> np.ndarray:
        """Independent ``q_o(S) = |S intersect A_o|`` for every obligation."""

        selected = np.unique(np.asarray(tuple(int(v) for v in selected_candidate_indices), dtype=np.int64))
        return np.asarray(
            [np.intersect1d(item.candidate_indices, selected, assume_unique=True).size for item in self.obligations],
            dtype=np.int64,
        )

    def unsatisfied(self, selected_candidate_indices: Sequence[int]) -> tuple[str, ...]:
        counts = self.selected_counts(selected_candidate_indices)
        return tuple(
            item.obligation_id
            for item, count in zip(self.obligations, counts, strict=True)
            if int(count) < item.minimum_count
        )


def obligation_policy_digest(training_order_policy: str, hard_support_obligations: Sequence[Any]) -> str:
    """Identity of the policy inputs that govern canonical obligations only.

    Candidate ladder, seeds and reducer settings are deliberately excluded:
    they cannot change what membership support means.
    """

    return digest(
        {
            "schema": "mdstats.target-obligation-policy.v1",
            "policy_version": TARGET_OBLIGATION_POLICY_VERSION,
            "training_order_policy": str(training_order_policy),
            "hard_support_obligations": [item.to_dict() for item in hard_support_obligations],
        }
    )


@dataclass(slots=True)
class _Group:
    locus: ObligationLocus
    incidence: tuple[int, ...]
    sources: list[ObligationSource]


def build_canonical_obligation_authority(
    reference: TargetCoverageReference,
    population: Any,
    *,
    training_order_policy: str,
    hard_support_obligations: Sequence[Any],
) -> TargetMembershipObligationAuthority:
    """Project automatic + explicit requirements onto one canonical set."""

    policy_digest = obligation_policy_digest(training_order_policy, hard_support_obligations)
    frame_uids = reference.frame_uids
    groups: dict[str, _Group] = {}
    source_semantics: dict[tuple[str, str], str] = {}

    def add(namespace: str, source_id: str, locus: ObligationLocus, rows: Sequence[int], minimum: int) -> None:
        incidence = tuple(sorted(set(int(value) for value in rows)))
        key = (namespace, source_id)
        semantics = digest({"locus": locus.to_dict(), "incidence": list(incidence)})
        previous = source_semantics.get(key)
        if previous is not None and previous != semantics:
            raise TrainingDataInputError(
                f"Source obligation ID {namespace}:{source_id} is reused for different semantics."
            )
        source_semantics[key] = semantics
        if not incidence:
            raise TrainingDataInputError(
                f"Obligation {namespace}:{source_id} has no support in exact P_train; "
                "the configured membership policy is infeasible."
            )
        group = groups.get(locus.digest)
        if group is None:
            groups[locus.digest] = _Group(locus, incidence, [ObligationSource(namespace, source_id, int(minimum))])
            return
        if group.incidence != incidence:
            raise TrainingDataInputError(
                f"Obligations for the same support locus {locus.kind}:{locus.target} project to "
                "different P_train incidence; the conflict fails closed."
            )
        if previous is None:
            group.sources.append(ObligationSource(namespace, source_id, int(minimum)))

    attributes_by_row = [dict(population.frame(uid).condition_attributes) for uid in frame_uids]
    conditions: dict[str, list[int]] = {}
    for row, uid in enumerate(frame_uids):
        conditions.setdefault(population.frame(uid).condition_id, []).append(row)
    for condition_id, rows in sorted(conditions.items()):
        add(
            NAMESPACE_AUTOMATIC,
            f"condition:{condition_id}",
            ObligationLocus(KIND_CONDITION, "p2_condition", None, condition_id, "member"),
            rows,
            1,
        )
    units: dict[str, list[int]] = {}
    for row, unit_id in enumerate(reference.correlation_unit_ids):
        units.setdefault(unit_id, []).append(row)
    for unit_id, rows in sorted(units.items()):
        add(
            NAMESPACE_AUTOMATIC,
            f"correlation_unit:{unit_id}",
            ObligationLocus(KIND_CORRELATION_UNIT, "p1_correlation_unit", None, unit_id, "member"),
            rows,
            1,
        )
    for event_type, rows in reference.structural_event_support:
        add(
            NAMESPACE_AUTOMATIC,
            f"structural_event:{event_type}",
            ObligationLocus(
                KIND_STRUCTURAL_EVENT,
                f"universal_structural_catalog:{reference.structural_catalog_digest}",
                None,
                event_type,
                "member",
            ),
            rows,
            1,
        )
    for family in reference.families:
        values = np.asarray(family.values, dtype=np.float64)
        frame_indices = np.asarray(family.frame_indices, dtype=np.int64)
        for channel in family.extent_channels:
            column = values[:, int(channel.feature_index)]
            for kind, side, rows in (
                (
                    KIND_EXTENT_LOWER,
                    "lower",
                    frame_indices[column <= float(channel.lower_reference_quantile) + _EXTENT_TOLERANCE],
                ),
                (
                    KIND_EXTENT_UPPER,
                    "upper",
                    frame_indices[column >= float(channel.upper_reference_quantile) - _EXTENT_TOLERANCE],
                ),
            ):
                add(
                    NAMESPACE_AUTOMATIC,
                    f"extent:{family.family_id}:{channel.feature_name}:{side}",
                    ObligationLocus(kind, "coverage_family_extent", family.family_id, channel.feature_name, side),
                    rows,
                    1,
                )
    explicit_ids: set[str] = set()
    for item in hard_support_obligations:
        if item.obligation_id in explicit_ids:
            raise TrainingDataInputError(f"Explicit obligation ID {item.obligation_id!r} is not unique.")
        explicit_ids.add(item.obligation_id)
        rows = [row for row, attributes in enumerate(attributes_by_row) if attributes.get(item.attribute) == item.value]
        if item.attribute == "condition_id":
            # P2 condition_id is the sole target-size condition identity, so an
            # explicit condition requirement is the automatic condition locus.
            locus = ObligationLocus(KIND_CONDITION, "p2_condition", None, item.value, "member")
        else:
            locus = ObligationLocus(
                KIND_CONDITION_ATTRIBUTE, "p2_condition_attribute", None, f"{item.attribute}={item.value}", "member"
            )
        add(NAMESPACE_EXPLICIT, item.obligation_id, locus, rows, item.minimum_count)
    obligations = tuple(
        TargetMembershipObligation(
            locus=group.locus,
            minimum_count=max(source.minimum_count for source in group.sources),
            candidate_indices=group.incidence,
            sources=tuple(group.sources),
            obligation_policy_digest=policy_digest,
        )
        for group in groups.values()
    )
    for item in obligations:
        if item.candidate_indices.size < item.minimum_count:
            raise TrainingDataInputError(
                f"Canonical obligation {item.locus.kind}:{item.locus.target} requires "
                f"{item.minimum_count} frames but exact P_train supports {item.candidate_indices.size}; "
                "the membership policy is infeasible."
            )
    return TargetMembershipObligationAuthority(
        target_coverage_reference_digest=reference.content_digest,
        frame_domain_digest=reference.frame_domain_digest,
        candidate_count=reference.candidate_count,
        obligation_policy_digest=policy_digest,
        obligations=obligations,
    )


__all__ = [
    "KIND_CONDITION",
    "KIND_CONDITION_ATTRIBUTE",
    "KIND_CORRELATION_UNIT",
    "KIND_EXTENT_LOWER",
    "KIND_EXTENT_UPPER",
    "KIND_STRUCTURAL_EVENT",
    "ObligationLocus",
    "ObligationSource",
    "TargetMembershipObligation",
    "TargetMembershipObligationAuthority",
    "build_canonical_obligation_authority",
    "obligation_policy_digest",
]
