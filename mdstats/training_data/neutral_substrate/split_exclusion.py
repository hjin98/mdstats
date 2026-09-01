"""Canonical P1 split-exclusion relation authority.

P1 owns the accepted semantics that make canonical frames statistically
non-separable across a later train/evaluation boundary.  This module exposes
those existing P1 semantics as one deterministic, canonically digested relation
evidence object.  Downstream split owners must consume this single authority;
they may not rediscover or reinterpret P1 relations from raw features, labels,
provenance, or ad hoc state.

The authority is derived content: it is always rebuilt from the accepted P1
owners (``CanonicalFrameAuthority`` + ``NeutralStatisticalBase``) and its
canonical identity is derived from canonical P1 relation content and lineage,
never from Python object identity or traversal order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .partition import CanonicalFrameAuthority, NeutralStatisticalBase

NEUTRAL_SPLIT_EXCLUSION_GROUP_SCHEMA = "mdstats.neutral-split-exclusion-group.v1"
NEUTRAL_SPLIT_EXCLUSION_EVIDENCE_SCHEMA = "mdstats.neutral-split-exclusion-evidence.v1"

# Relation kinds.  Each kind restates an existing P1 semantic; the taxonomy is
# owned here and must not be extended by downstream consumers.
RELATION_KIND_CORRELATION_UNIT = "correlation_unit"
RELATION_KIND_GEOMETRY_DUPLICATE = "geometry_duplicate"
RELATION_KIND_PROTECTED_EVENT = "protected_event"
RELATION_KIND_REPLICA_LINEAGE = "replica_lineage"
RELATION_KIND_STRUCTURAL_REALIZATION = "structural_realization"

RELATION_KINDS = (
    RELATION_KIND_CORRELATION_UNIT,
    RELATION_KIND_GEOMETRY_DUPLICATE,
    RELATION_KIND_PROTECTED_EVENT,
    RELATION_KIND_REPLICA_LINEAGE,
    RELATION_KIND_STRUCTURAL_REALIZATION,
)


@dataclass(frozen=True, slots=True)
class NeutralSplitExclusionGroup:
    """One P1 split-excluding relation over canonical frame UIDs.

    The group representation is deliberately relational: every pair of members
    is non-separable, so reduction to a connected-component closure is a
    downstream implementation detail rather than part of P1 semantics.
    """

    relation_kind: str
    relation_key: str
    frame_uids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.relation_kind not in RELATION_KINDS:
            raise TrainingDataInputError(
                f"Unknown P1 split-exclusion relation kind: {self.relation_kind!r}."
            )
        object.__setattr__(self, "relation_kind", str(self.relation_kind))
        object.__setattr__(self, "relation_key", str(self.relation_key))
        uids = tuple(sorted(set(str(v) for v in self.frame_uids)))
        if len(uids) < 2:
            raise TrainingDataInputError(
                "A split-exclusion relation must bind at least two distinct frames."
            )
        object.__setattr__(self, "frame_uids", uids)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": NEUTRAL_SPLIT_EXCLUSION_GROUP_SCHEMA,
            "relation_kind": self.relation_kind,
            "relation_key": self.relation_key,
            "frame_uids": list(self.frame_uids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NeutralSplitExclusionGroup":
        if payload.get("schema") != NEUTRAL_SPLIT_EXCLUSION_GROUP_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported neutral split-exclusion group schema."
            )
        result = cls(
            relation_kind=str(payload["relation_kind"]),
            relation_key=str(payload["relation_key"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Split-exclusion group digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class NeutralSplitExclusionEvidence:
    """Canonical P1 split-exclusion relation evidence for one accepted base."""

    dataset_id: str
    frame_authority_digest: str
    unit_catalog_digest: str
    groups: tuple[NeutralSplitExclusionGroup, ...]
    _content_digest_cache: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("frame_authority_digest", "unit_catalog_digest"):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if not self.dataset_id.strip():
            raise TrainingDataInputError("dataset_id must be non-empty.")
        groups = tuple(sorted(self.groups, key=lambda item: (item.relation_kind, item.relation_key)))
        if len({(item.relation_kind, item.relation_key) for item in groups}) != len(groups):
            raise TrainingDataInputError(
                "Split-exclusion relation groups must be unique per kind and key."
            )
        object.__setattr__(self, "groups", groups)

    def groups_for(self, frame_uids: Any) -> tuple[NeutralSplitExclusionGroup, ...]:
        """Project relations onto a frame subset.

        Relations wholly outside the projection create no membership; a
        relation touching outside frames still binds every in-subset endpoint.
        """
        members = set(frame_uids)
        projected: list[NeutralSplitExclusionGroup] = []
        for group in self.groups:
            inside = tuple(uid for uid in group.frame_uids if uid in members)
            if len(inside) >= 2:
                projected.append(
                    NeutralSplitExclusionGroup(
                        relation_kind=group.relation_kind,
                        relation_key=group.relation_key,
                        frame_uids=inside,
                    )
                )
        return tuple(sorted(projected, key=lambda item: (item.relation_kind, item.relation_key)))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": NEUTRAL_SPLIT_EXCLUSION_EVIDENCE_SCHEMA,
            "dataset_id": self.dataset_id,
            "frame_authority_digest": self.frame_authority_digest,
            "unit_catalog_digest": self.unit_catalog_digest,
            "groups": [item.to_dict() for item in self.groups],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NeutralSplitExclusionEvidence":
        if payload.get("schema") != NEUTRAL_SPLIT_EXCLUSION_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported neutral split-exclusion evidence schema."
            )
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_authority_digest=str(payload["frame_authority_digest"]),
            unit_catalog_digest=str(payload["unit_catalog_digest"]),
            groups=tuple(
                NeutralSplitExclusionGroup.from_dict(item)
                for item in payload.get("groups", ())
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Split-exclusion evidence digest mismatch."
            )
        return result


def split_exclusion_component_digest(component: Any) -> str:
    """Stable identity of one connected split-exclusion component.

    This is the single canonical identity scheme for constraint components;
    both P2 split construction and per-frame correlation-block assignment
    must name components identically.
    """

    members = tuple(
        sorted(validate_digest(str(uid), name="component frame UID") for uid in component)
    )
    if not members or len(set(members)) != len(members):
        raise TrainingDataInputError(
            "Split-exclusion components require unique frame UIDs."
        )
    return digest({"frame_uids": list(members)})


def project_split_exclusion_constraint_components(
    frame_uids: Any,
    split_exclusion_evidence: NeutralSplitExclusionEvidence,
    *,
    frame_authority_digest: str,
    neutral_unit_catalog_digest: str,
) -> tuple[tuple[str, ...], ...]:
    """Transitive closure of the complete inherited P1 relation authority.

    One canonical implementation shared by P2 exact split construction and
    any later correlation-block assignment: correlation units, exact geometry
    duplicates, protected event windows, and condition-scoped
    replica/structural-realization lineages are consumed only from the bound
    evidence object.  Reduction is a deterministic union over the projected
    groups, so a chain through unit, duplicate, and additional protected
    relations collapses into one indivisible component.
    """

    members_uids = tuple(
        validate_digest(str(uid), name="component frame UID") for uid in frame_uids
    )
    if not members_uids or len(set(members_uids)) != len(members_uids):
        raise TrainingDataInputError(
            "Component projection requires unique frame UIDs."
        )
    if (
        split_exclusion_evidence.frame_authority_digest != frame_authority_digest
        or split_exclusion_evidence.unit_catalog_digest
        != neutral_unit_catalog_digest
    ):
        raise TrainingDataInputError(
            "Split-exclusion relation authority does not bind this U_size population."
        )
    parent = {uid: uid for uid in members_uids}

    def find(uid: str) -> str:
        while parent[uid] != uid:
            parent[uid] = parent[parent[uid]]
            uid = parent[uid]
        return uid

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            if b < a:
                a, b = b, a
            parent[b] = a

    members = set(members_uids)
    for group in split_exclusion_evidence.groups_for(members):
        first = group.frame_uids[0]
        for uid in group.frame_uids[1:]:
            union(first, uid)
    components: dict[str, list[str]] = {}
    for uid in members_uids:
        components.setdefault(find(uid), []).append(uid)
    return tuple(
        sorted((tuple(sorted(v)) for v in components.values()), key=lambda v: v[0])
    )


def frame_split_exclusion_component_membership(
    frame_uids: Any,
    split_exclusion_evidence: NeutralSplitExclusionEvidence,
    *,
    frame_authority_digest: str,
    neutral_unit_catalog_digest: str,
) -> tuple[tuple[str, str], ...]:
    """Per-frame assignment of canonical component identities.

    Each frame receives the identity of its full closure component; subsets
    of the projection therefore retain their parent component identities
    instead of recomputing prefix-local names.
    """

    components = project_split_exclusion_constraint_components(
        frame_uids,
        split_exclusion_evidence,
        frame_authority_digest=frame_authority_digest,
        neutral_unit_catalog_digest=neutral_unit_catalog_digest,
    )
    assignment: list[tuple[str, str]] = []
    for component in components:
        identity = split_exclusion_component_digest(component)
        for uid in component:
            assignment.append((uid, identity))
    return tuple(sorted(assignment))


def _condition_scoped_lineage_groups(
    unit_catalog,
    *,
    relation_kind: str,
    lineage_of_unit,
) -> list[NeutralSplitExclusionGroup]:
    """Group units sharing one condition-scoped lineage identity.

    P1's accepted independence semantics scope replica and structural
    realization identities to the exact condition.  Units of one run are
    autocorrelation-aware temporal blocks whose separability P1 already grades,
    so a lineage relation exists only when at least two distinct runs claim the
    same lineage under the same condition.
    """
    grouped: dict[tuple[str, str], dict[str, set[str]]] = {}
    for unit in unit_catalog.units:
        lineage = lineage_of_unit(unit)
        if lineage is None:
            continue
        key = (unit.condition.condition_id, str(lineage))
        entry = grouped.setdefault(key, {})
        entry.setdefault(unit.run_id, set()).update(unit.frame_uids)
    groups: list[NeutralSplitExclusionGroup] = []
    for (condition_id, lineage), by_run in sorted(grouped.items()):
        if len(by_run) < 2:
            continue
        frames: set[str] = set()
        for uids in by_run.values():
            frames.update(uids)
        if len(frames) < 2:
            continue
        groups.append(
            NeutralSplitExclusionGroup(
                relation_kind=relation_kind,
                relation_key=f"{condition_id}|{lineage}",
                frame_uids=tuple(sorted(frames)),
            )
        )
    return groups


def build_neutral_split_exclusion_evidence(
    frame_authority,
    neutral_base,
) -> NeutralSplitExclusionEvidence:
    """Derive the complete P1 split-exclusion relation authority.

    The relation semantics belong to P1.  Every relation whose accepted P1
    semantics is split-excluding or protected enters this evidence:

    - ``correlation_unit``: exact neutral partition/correlation unit membership;
    - ``geometry_duplicate``: exact canonical geometry-duplicate groups;
    - ``protected_event``: frames sharing one protected event window;
    - ``replica_lineage``: units of distinct runs sharing one replica identity
      under the exact same condition;
    - ``structural_realization``: units of distinct runs sharing one structural
      realization identity under the exact same condition.
    """
    from .frame_authority import CanonicalFrameAuthority
    from .partition import NeutralStatisticalBase

    if not isinstance(frame_authority, CanonicalFrameAuthority):
        raise TrainingDataInputError(
            "Split-exclusion evidence requires CanonicalFrameAuthority."
        )
    if not isinstance(neutral_base, NeutralStatisticalBase):
        raise TrainingDataInputError(
            "Split-exclusion evidence requires NeutralStatisticalBase."
        )
    catalog = neutral_base.unit_catalog
    if catalog.frame_authority_digest != frame_authority.content_digest:
        raise TrainingDataInputError(
            "Neutral base does not bind the supplied frame authority."
        )
    if frame_authority.dataset_id != neutral_base.dataset_id:
        raise TrainingDataInputError(
            "P1 split-exclusion evidence dataset lineage mismatch."
        )

    groups: list[NeutralSplitExclusionGroup] = []

    for unit in catalog.units:
        if unit.frame_count >= 2:
            groups.append(
                NeutralSplitExclusionGroup(
                    relation_kind=RELATION_KIND_CORRELATION_UNIT,
                    relation_key=unit.unit_id,
                    frame_uids=unit.frame_uids,
                )
            )

    event_frames: dict[str, set[str]] = {}
    for unit in catalog.units:
        for event_id in unit.event_ids:
            event_frames.setdefault(str(event_id), set()).update(unit.frame_uids)
    for event_id, uids in sorted(event_frames.items()):
        if len(uids) >= 2:
            groups.append(
                NeutralSplitExclusionGroup(
                    relation_kind=RELATION_KIND_PROTECTED_EVENT,
                    relation_key=str(event_id),
                    frame_uids=tuple(sorted(uids)),
                )
            )

    for duplicate in frame_authority.duplicates.geometry_groups:
        groups.append(
            NeutralSplitExclusionGroup(
                relation_kind=RELATION_KIND_GEOMETRY_DUPLICATE,
                relation_key=duplicate.geometry_fingerprint,
                frame_uids=duplicate.frame_uids,
            )
        )

    groups.extend(
        _condition_scoped_lineage_groups(
            catalog,
            relation_kind=RELATION_KIND_REPLICA_LINEAGE,
            lineage_of_unit=lambda unit: unit.replica_id,
        )
    )
    groups.extend(
        _condition_scoped_lineage_groups(
            catalog,
            relation_kind=RELATION_KIND_STRUCTURAL_REALIZATION,
            lineage_of_unit=lambda unit: unit.structural_realization_id,
        )
    )

    return NeutralSplitExclusionEvidence(
        dataset_id=frame_authority.dataset_id,
        frame_authority_digest=frame_authority.content_digest,
        unit_catalog_digest=catalog.content_digest,
        groups=tuple(groups),
    )
