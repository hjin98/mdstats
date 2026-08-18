"""Bounded strong-ring classification over exact translated primitive rings.

A strong ring is a primitive ring that cannot be represented as the
symmetric-difference sum of any number of strictly smaller rings.  The concept
follows Goetzke and Klein (1991) and the discussion by Yuan and Cormack (2002).
mdstats classifies this property only inside one explicit finite placement
domain and never promotes a bounded negative result to an unqualified global
strong-ring theorem.

The first placement backend is an exact edge-incidence-depth domain.  Starting
from the target ring's physical lifted-edge support, it repeatedly follows
``physical edge -> smaller primitive-ring placement -> physical edge``
incidences.  A depth ``D`` domain contains every admitted smaller translated
ring placement reachable in at most ``D`` ring-incidence steps.  The finite
candidate support is solved exactly by Gaussian elimination over GF(2) through
:mod:`mdstats.analysis.primitive_ring_cancellation`.

The connected-witness reduction used to motivate the incidence expansion is an
mdstats derivation: in a minimum-cardinality decomposition, every component is
connected to the target in the support-incidence graph; otherwise a disconnected
zero-sum component can be removed.  Increasing the incidence depth therefore
forms a monotone sequence of finite domains and eventually contains any fixed
finite witness, although no finite depth is claimed to be globally complete.

References
----------
K. Goetzke and H.-J. Klein, J. Non-Cryst. Solids 127, 215-220 (1991),
doi:10.1016/0022-3093(91)90145-V.
X. Yuan and A. N. Cormack, Comput. Mater. Sci. 24, 343-360 (2002),
doi:10.1016/S0927-0256(01)00256-7.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from numbers import Integral
from typing import Any, Iterable, Mapping

from .periodic_cycle import RingPlacement
from .primitive_ring import PrimitiveRingFamily, PrimitiveRingKey
from .primitive_ring_cancellation import (
    FiniteRingCancellationResources,
    FiniteRingCancellationStatus,
    PrimitiveRingCancellationResourceError,
    RingCancellationWitness,
    ring_placement_support,
    solve_finite_ring_cancellation,
)
from .primitive_ring_index import (
    LiftedEdgeInstanceRef,
    PrimitiveRingIndex,
    PrimitiveRingIndexInputError,
    ring_placements_covering_edge,
)


CANONICAL_RING_STRENGTH_SCHEMA = "mdstats.ring_strength.v2"
CANONICAL_RING_STRENGTH_CATALOG_SCHEMA = "mdstats.ring_strength_catalog.v2"
RING_STRENGTH_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class RingStrengthError(ValueError):
    """Base exception for bounded strong-ring classification."""


class RingStrengthInputError(RingStrengthError):
    """Raised when a strength domain, source, or resource policy is malformed."""


class RingStrengthInvariantError(RingStrengthError):
    """Raised when exact support or result invariants fail."""


class RingStrengthSerializationError(RingStrengthError):
    """Raised when serialized strength data fail source or digest validation."""


class RingStrengthStatus(str, Enum):
    """Certified outcome for one immutable finite strength domain."""

    WEAK_CERTIFIED = "weak_certified"
    STRONG_IN_DOMAIN = "strong_in_domain"
    UNRESOLVED_TRUNCATED = "unresolved_truncated"
    UNRESOLVED_SOURCE_INCOMPLETE = "unresolved_source_incomplete"


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise RingStrengthInputError(f"{name} must be an integer.")
    result = int(value)
    if result <= 0:
        raise RingStrengthInputError(f"{name} must be positive.")
    return result


def _nonempty_digest(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise RingStrengthInputError(f"{name} must be a nonempty string.")
    return value


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _placement_to_dict(placement: RingPlacement) -> dict[str, Any]:
    return {
        "topology_graph_digest": placement.topology_graph_digest,
        "ring_key": placement.ring_key.to_dict(),
        "image_shift": list(placement.image_shift),
    }


def _placement_from_dict(payload: Mapping[str, Any]) -> RingPlacement:
    return RingPlacement(
        topology_graph_digest=str(payload["topology_graph_digest"]),
        ring_key=PrimitiveRingKey.from_dict(payload["ring_key"]),
        image_shift=tuple(int(x) for x in payload["image_shift"]),
    )


def _candidate_set_digest(candidates: Iterable[RingPlacement]) -> str:
    ordered = tuple(sorted(candidates))
    return _digest(
        {"candidate_placements": [_placement_to_dict(item) for item in ordered]}
    )


@dataclass(frozen=True, order=True, slots=True)
class EdgeIncidencePlacementDomain:
    """Finite placement domain defined by target-connected incidence depth.

    Depth one contains smaller ring placements sharing at least one exact
    physical lifted edge with the target.  Each additional depth follows one
    more ring-placement incidence through an exact physical edge.
    """

    max_incidence_depth: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_incidence_depth",
            _positive_int(self.max_incidence_depth, name="max_incidence_depth"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "edge_incidence_depth",
            "max_incidence_depth": self.max_incidence_depth,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EdgeIncidencePlacementDomain":
        if str(payload.get("kind")) != "edge_incidence_depth":
            raise RingStrengthSerializationError(
                "Unsupported ring-strength placement-domain kind."
            )
        return cls(max_incidence_depth=int(payload["max_incidence_depth"]))


@dataclass(frozen=True, order=True, slots=True)
class RingStrengthDomain:
    """Immutable mathematical domain for one target primitive-ring orbit."""

    target_ring_key: PrimitiveRingKey
    max_component_size: int
    placement_domain: EdgeIncidencePlacementDomain

    def __post_init__(self) -> None:
        if not isinstance(self.target_ring_key, PrimitiveRingKey):
            raise RingStrengthInputError("target_ring_key must be a PrimitiveRingKey.")
        maximum = _positive_int(self.max_component_size, name="max_component_size")
        if maximum < 2:
            raise RingStrengthInputError(
                "The first backend supports component ring sizes of at least two."
            )
        if not isinstance(self.placement_domain, EdgeIncidencePlacementDomain):
            raise RingStrengthInputError(
                "placement_domain must be an EdgeIncidencePlacementDomain."
            )
        object.__setattr__(self, "max_component_size", maximum)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_ring_key": self.target_ring_key.to_dict(),
            "max_component_size": self.max_component_size,
            "placement_domain": self.placement_domain.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingStrengthDomain":
        return cls(
            target_ring_key=PrimitiveRingKey.from_dict(payload["target_ring_key"]),
            max_component_size=int(payload["max_component_size"]),
            placement_domain=EdgeIncidencePlacementDomain.from_dict(
                payload["placement_domain"]
            ),
        )


@dataclass(frozen=True, slots=True)
class RingStrengthResources:
    """Execution limits, separate from the mathematical strength domain."""

    max_candidate_placements: int = 50_000
    max_search_nodes: int = 1_000_000
    max_support_terms: int = 4_000_000
    max_matrix_bits: int = 536_870_912
    max_provenance_bits: int = 268_435_456

    def __post_init__(self) -> None:
        for name in (
            "max_candidate_placements",
            "max_search_nodes",
            "max_support_terms",
            "max_matrix_bits",
            "max_provenance_bits",
        ):
            object.__setattr__(
                self,
                name,
                _positive_int(getattr(self, name), name=name),
            )

    @property
    def cancellation_resources(self) -> FiniteRingCancellationResources:
        return FiniteRingCancellationResources(
            max_matrix_bits=self.max_matrix_bits,
            max_provenance_bits=self.max_provenance_bits,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_candidate_placements": self.max_candidate_placements,
            "max_search_nodes": self.max_search_nodes,
            "max_support_terms": self.max_support_terms,
            "max_matrix_bits": self.max_matrix_bits,
            "max_provenance_bits": self.max_provenance_bits,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingStrengthResources":
        return cls(
            max_candidate_placements=int(payload["max_candidate_placements"]),
            max_search_nodes=int(payload["max_search_nodes"]),
            max_support_terms=int(payload["max_support_terms"]),
            max_matrix_bits=int(payload["max_matrix_bits"]),
            max_provenance_bits=int(payload["max_provenance_bits"]),
        )


@dataclass(frozen=True, slots=True)
class RingStrengthDiagnostics:
    """Deterministic source, enumeration, and truncation diagnostics."""

    source_complete: bool
    source_issue: str | None
    admitted_ring_key_count: int
    candidate_placement_count: int
    explored_edge_instance_count: int
    support_term_count: int
    achieved_incidence_depth: int
    requested_incidence_depth: int
    truncation_reason: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_complete", bool(self.source_complete))
        for name in (
            "admitted_ring_key_count",
            "candidate_placement_count",
            "explored_edge_instance_count",
            "support_term_count",
            "achieved_incidence_depth",
            "requested_incidence_depth",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
                raise RingStrengthInputError(f"{name} must be a nonnegative integer.")
            object.__setattr__(self, name, int(value))
        if self.achieved_incidence_depth > self.requested_incidence_depth:
            raise RingStrengthInputError(
                "achieved_incidence_depth cannot exceed requested_incidence_depth."
            )
        if self.source_complete and self.source_issue is not None:
            raise RingStrengthInputError(
                "source_complete=True requires source_issue=None."
            )
        if self.truncation_reason is not None and not self.truncation_reason:
            raise RingStrengthInputError(
                "truncation_reason must be None or a nonempty string."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_complete": self.source_complete,
            "source_issue": self.source_issue,
            "admitted_ring_key_count": self.admitted_ring_key_count,
            "candidate_placement_count": self.candidate_placement_count,
            "explored_edge_instance_count": self.explored_edge_instance_count,
            "support_term_count": self.support_term_count,
            "achieved_incidence_depth": self.achieved_incidence_depth,
            "requested_incidence_depth": self.requested_incidence_depth,
            "truncation_reason": self.truncation_reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingStrengthDiagnostics":
        return cls(
            source_complete=bool(payload["source_complete"]),
            source_issue=(
                None if payload.get("source_issue") is None else str(payload["source_issue"])
            ),
            admitted_ring_key_count=int(payload["admitted_ring_key_count"]),
            candidate_placement_count=int(payload["candidate_placement_count"]),
            explored_edge_instance_count=int(payload["explored_edge_instance_count"]),
            support_term_count=int(payload["support_term_count"]),
            achieved_incidence_depth=int(payload["achieved_incidence_depth"]),
            requested_incidence_depth=int(payload["requested_incidence_depth"]),
            truncation_reason=(
                None
                if payload.get("truncation_reason") is None
                else str(payload["truncation_reason"])
            ),
        )


@dataclass(frozen=True, slots=True)
class RingStrengthSearchWorkspace:
    """Transient exhaustive candidate workspace for one bounded classification.

    The workspace is intentionally not part of the persistent scientific result.
    It may be retained for diagnostics or debugging, but it has no ``to_dict``
    method and can always be reconstructed deterministically from the source
    catalog, target, domain, and resource policy.
    """

    topology_graph_digest: str
    primitive_ring_catalog_digest: str
    target_placement: RingPlacement
    domain: RingStrengthDomain
    resources: RingStrengthResources
    diagnostics: RingStrengthDiagnostics
    candidate_placements: tuple[RingPlacement, ...]
    candidate_set_digest: str

    def __post_init__(self) -> None:
        graph_digest = _nonempty_digest(
            self.topology_graph_digest, name="topology_graph_digest"
        )
        catalog_digest = _nonempty_digest(
            self.primitive_ring_catalog_digest,
            name="primitive_ring_catalog_digest",
        )
        if not isinstance(self.target_placement, RingPlacement):
            raise RingStrengthInputError(
                "target_placement must be a RingPlacement."
            )
        if self.target_placement.topology_graph_digest != graph_digest:
            raise RingStrengthInputError(
                "Workspace target belongs to a different topology graph."
            )
        if not isinstance(self.domain, RingStrengthDomain) or (
            self.domain.target_ring_key != self.target_placement.ring_key
        ):
            raise RingStrengthInputError(
                "Workspace domain must match the target ring key."
            )
        if not isinstance(self.resources, RingStrengthResources):
            raise RingStrengthInputError(
                "resources must be a RingStrengthResources record."
            )
        if not isinstance(self.diagnostics, RingStrengthDiagnostics):
            raise RingStrengthInputError(
                "diagnostics must be a RingStrengthDiagnostics record."
            )
        candidates = tuple(self.candidate_placements)
        if candidates != tuple(sorted(candidates)) or len(set(candidates)) != len(candidates):
            raise RingStrengthInputError(
                "candidate_placements must be sorted and unique."
            )
        if any(
            not isinstance(item, RingPlacement)
            or item.topology_graph_digest != graph_digest
            for item in candidates
        ):
            raise RingStrengthInputError(
                "candidate_placements must be source-compatible placements."
            )
        if self.diagnostics.candidate_placement_count != len(candidates):
            raise RingStrengthInputError(
                "Workspace diagnostic candidate count is inconsistent."
            )
        expected_digest = _candidate_set_digest(candidates)
        if self.candidate_set_digest != expected_digest:
            raise RingStrengthInputError(
                "candidate_set_digest is inconsistent with the workspace candidates."
            )
        object.__setattr__(self, "topology_graph_digest", graph_digest)
        object.__setattr__(self, "primitive_ring_catalog_digest", catalog_digest)
        object.__setattr__(self, "candidate_placements", candidates)


@dataclass(frozen=True, slots=True)
class RingStrengthWitness:
    """Exact weak-ring witness over physical lifted-edge support."""

    target_placement: RingPlacement
    component_placements: tuple[RingPlacement, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.target_placement, RingPlacement):
            raise RingStrengthInputError("target_placement must be a RingPlacement.")
        components = tuple(self.component_placements)
        if not components or any(
            not isinstance(item, RingPlacement) for item in components
        ):
            raise RingStrengthInputError(
                "component_placements must contain RingPlacement records."
            )
        if components != tuple(sorted(components)) or len(set(components)) != len(
            components
        ):
            raise RingStrengthInputError(
                "component_placements must be sorted and unique."
            )
        if any(
            item.topology_graph_digest != self.target_placement.topology_graph_digest
            for item in components
        ):
            raise RingStrengthInputError(
                "Witness components must share the target topology source."
            )
        object.__setattr__(self, "component_placements", components)

    @classmethod
    def from_cancellation_witness(
        cls, witness: RingCancellationWitness
    ) -> "RingStrengthWitness":
        return cls(
            target_placement=witness.target_placement,
            component_placements=witness.component_placements,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_placement": _placement_to_dict(self.target_placement),
            "component_placements": [
                _placement_to_dict(item) for item in self.component_placements
            ],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingStrengthWitness":
        return cls(
            target_placement=_placement_from_dict(payload["target_placement"]),
            component_placements=tuple(
                _placement_from_dict(item) for item in payload["component_placements"]
            ),
        )


@dataclass(frozen=True, slots=True)
class RingStrengthResult:
    """Persistent bounded certification result for one exact target placement.

    The exhaustive candidate workspace is deliberately absent.  The result
    stores only its deterministic digest/count plus a positive witness when one
    exists.  ``verify(index)`` reconstructs the finite domain and independently
    checks the certificate.
    """

    topology_graph_digest: str
    primitive_ring_catalog_digest: str
    target_placement: RingPlacement
    domain: RingStrengthDomain
    resources: RingStrengthResources
    status: RingStrengthStatus
    diagnostics: RingStrengthDiagnostics
    candidate_set_digest: str
    witness: RingStrengthWitness | None
    canonical_schema_version: str = CANONICAL_RING_STRENGTH_SCHEMA
    digest_algorithm: str = RING_STRENGTH_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        graph_digest = _nonempty_digest(
            self.topology_graph_digest, name="topology_graph_digest"
        )
        catalog_digest = _nonempty_digest(
            self.primitive_ring_catalog_digest,
            name="primitive_ring_catalog_digest",
        )
        if not isinstance(self.target_placement, RingPlacement):
            raise RingStrengthInputError("target_placement must be a RingPlacement.")
        if self.target_placement.topology_graph_digest != graph_digest:
            raise RingStrengthInputError(
                "target_placement topology source does not match the result."
            )
        if not isinstance(self.domain, RingStrengthDomain):
            raise RingStrengthInputError("domain must be a RingStrengthDomain.")
        if self.domain.target_ring_key != self.target_placement.ring_key:
            raise RingStrengthInputError(
                "domain target_ring_key does not match target_placement."
            )
        if not isinstance(self.resources, RingStrengthResources):
            raise RingStrengthInputError("resources must be RingStrengthResources.")
        if not isinstance(self.status, RingStrengthStatus):
            raise RingStrengthInputError("status must be a RingStrengthStatus.")
        if not isinstance(self.diagnostics, RingStrengthDiagnostics):
            raise RingStrengthInputError(
                "diagnostics must be RingStrengthDiagnostics."
            )
        candidate_digest = _nonempty_digest(
            self.candidate_set_digest, name="candidate_set_digest"
        )
        if len(candidate_digest) != 64:
            raise RingStrengthInputError(
                "candidate_set_digest must be a SHA-256 digest."
            )
        if self.status is RingStrengthStatus.WEAK_CERTIFIED:
            if not isinstance(self.witness, RingStrengthWitness):
                raise RingStrengthInputError(
                    "WEAK_CERTIFIED requires a RingStrengthWitness."
                )
            if self.witness.target_placement != self.target_placement:
                raise RingStrengthInputError(
                    "Witness target disagrees with result target."
                )
            if (
                len(self.witness.component_placements)
                > self.diagnostics.candidate_placement_count
            ):
                raise RingStrengthInputError(
                    "Witness cannot contain more placements than the candidate domain."
                )
        elif self.witness is not None:
            raise RingStrengthInputError(
                "Only WEAK_CERTIFIED may carry a witness."
            )
        if self.status in (
            RingStrengthStatus.WEAK_CERTIFIED,
            RingStrengthStatus.STRONG_IN_DOMAIN,
        ):
            if not self.diagnostics.source_complete:
                raise RingStrengthInputError(
                    "Certified status requires complete primitive-ring source coverage."
                )
            if self.diagnostics.truncation_reason is not None:
                raise RingStrengthInputError(
                    "Certified status cannot carry resource truncation."
                )
            if (
                self.diagnostics.achieved_incidence_depth
                != self.diagnostics.requested_incidence_depth
            ):
                raise RingStrengthInputError(
                    "Certified status requires complete requested-domain expansion."
                )
        if self.status is RingStrengthStatus.UNRESOLVED_SOURCE_INCOMPLETE:
            if self.diagnostics.source_complete:
                raise RingStrengthInputError(
                    "UNRESOLVED_SOURCE_INCOMPLETE requires source_complete=False."
                )
        if self.status is RingStrengthStatus.UNRESOLVED_TRUNCATED:
            if self.diagnostics.truncation_reason is None:
                raise RingStrengthInputError(
                    "UNRESOLVED_TRUNCATED requires a truncation reason."
                )
        if self.canonical_schema_version != CANONICAL_RING_STRENGTH_SCHEMA:
            raise RingStrengthSerializationError(
                "Unsupported ring-strength schema version."
            )
        if self.digest_algorithm != RING_STRENGTH_DIGEST_ALGORITHM:
            raise RingStrengthSerializationError(
                "Unsupported ring-strength digest algorithm."
            )
        object.__setattr__(self, "topology_graph_digest", graph_digest)
        object.__setattr__(self, "primitive_ring_catalog_digest", catalog_digest)
        object.__setattr__(self, "candidate_set_digest", candidate_digest)
        expected = _digest(self._payload_without_digest())
        digest = self.digest or expected
        if digest != expected:
            raise RingStrengthSerializationError(
                "Stored ring-strength digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    def _payload_without_digest(self) -> dict[str, Any]:
        return {
            "topology_graph_digest": self.topology_graph_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "target_placement": _placement_to_dict(self.target_placement),
            "domain": self.domain.to_dict(),
            "resources": self.resources.to_dict(),
            "status": self.status.value,
            "diagnostics": self.diagnostics.to_dict(),
            "candidate_set_digest": self.candidate_set_digest,
            "witness": None if self.witness is None else self.witness.to_dict(),
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload_without_digest()
        payload["digest"] = self.digest
        return payload

    def verify(self, index: PrimitiveRingIndex) -> None:
        """Reconstruct and independently verify this bounded result."""

        if not isinstance(index, PrimitiveRingIndex):
            raise RingStrengthSerializationError(
                "index must be a PrimitiveRingIndex for result verification."
            )
        if self.topology_graph_digest != index.topology_graph_digest:
            raise RingStrengthSerializationError(
                "Strength result belongs to another topology graph."
            )
        if self.primitive_ring_catalog_digest != index.catalog_digest:
            raise RingStrengthSerializationError(
                "Strength result belongs to another primitive-ring catalog."
            )
        if self.witness is not None:
            _verify_strength_witness(index, self.witness)
        rebuilt, _workspace = _classify_ring_strength_with_workspace(
            index,
            self.target_placement,
            self.domain,
            resources=self.resources,
        )
        if rebuilt.to_dict() != self.to_dict():
            raise RingStrengthSerializationError(
                "Stored ring-strength result failed deterministic certificate verification."
            )

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        index: PrimitiveRingIndex,
        verify: bool = True,
    ) -> "RingStrengthResult":
        result = cls(
            topology_graph_digest=str(payload["topology_graph_digest"]),
            primitive_ring_catalog_digest=str(payload["primitive_ring_catalog_digest"]),
            target_placement=_placement_from_dict(payload["target_placement"]),
            domain=RingStrengthDomain.from_dict(payload["domain"]),
            resources=RingStrengthResources.from_dict(payload["resources"]),
            status=RingStrengthStatus(str(payload["status"])),
            diagnostics=RingStrengthDiagnostics.from_dict(payload["diagnostics"]),
            candidate_set_digest=str(payload["candidate_set_digest"]),
            witness=(
                None
                if payload.get("witness") is None
                else RingStrengthWitness.from_dict(payload["witness"])
            ),
            canonical_schema_version=str(payload["canonical_schema_version"]),
            digest_algorithm=str(payload["digest_algorithm"]),
            digest=str(payload["digest"]),
        )
        if verify:
            result.verify(index)
        else:
            if result.topology_graph_digest != index.topology_graph_digest:
                raise RingStrengthSerializationError(
                    "Serialized strength result belongs to another topology graph."
                )
            if result.primitive_ring_catalog_digest != index.catalog_digest:
                raise RingStrengthSerializationError(
                    "Serialized strength result belongs to another primitive-ring catalog."
                )
        return result


@dataclass(frozen=True, slots=True)
class RingStrengthCatalog:
    """Deterministic collection of canonical bounded strength results."""

    topology_graph_digest: str
    primitive_ring_catalog_digest: str
    results: tuple[RingStrengthResult, ...]
    canonical_schema_version: str = CANONICAL_RING_STRENGTH_CATALOG_SCHEMA
    digest_algorithm: str = RING_STRENGTH_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        graph_digest = _nonempty_digest(
            self.topology_graph_digest, name="topology_graph_digest"
        )
        catalog_digest = _nonempty_digest(
            self.primitive_ring_catalog_digest,
            name="primitive_ring_catalog_digest",
        )
        results = tuple(self.results)
        if any(not isinstance(item, RingStrengthResult) for item in results):
            raise RingStrengthInputError(
                "results must contain RingStrengthResult records."
            )
        if any(
            item.topology_graph_digest != graph_digest
            or item.primitive_ring_catalog_digest != catalog_digest
            for item in results
        ):
            raise RingStrengthInputError(
                "All strength results must share the catalog source."
            )
        keys = tuple(item.target_placement.ring_key for item in results)
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise RingStrengthInputError(
                "Catalog results must be sorted and unique by target ring key."
            )
        if any(item.target_placement.image_shift != (0, 0, 0) for item in results):
            raise RingStrengthInputError(
                "RingStrengthCatalog stores canonical zero-shift target placements only."
            )
        if self.canonical_schema_version != CANONICAL_RING_STRENGTH_CATALOG_SCHEMA:
            raise RingStrengthSerializationError(
                "Unsupported ring-strength catalog schema version."
            )
        if self.digest_algorithm != RING_STRENGTH_DIGEST_ALGORITHM:
            raise RingStrengthSerializationError(
                "Unsupported ring-strength digest algorithm."
            )
        object.__setattr__(self, "topology_graph_digest", graph_digest)
        object.__setattr__(self, "primitive_ring_catalog_digest", catalog_digest)
        object.__setattr__(self, "results", results)
        expected = _digest(self._payload_without_digest())
        digest = self.digest or expected
        if digest != expected:
            raise RingStrengthSerializationError(
                "Stored ring-strength catalog digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    def _payload_without_digest(self) -> dict[str, Any]:
        return {
            "topology_graph_digest": self.topology_graph_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "results": [item.to_dict() for item in self.results],
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload_without_digest()
        payload["digest"] = self.digest
        return payload

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        index: PrimitiveRingIndex,
        verify: bool = True,
    ) -> "RingStrengthCatalog":
        catalog = cls(
            topology_graph_digest=str(payload["topology_graph_digest"]),
            primitive_ring_catalog_digest=str(payload["primitive_ring_catalog_digest"]),
            results=tuple(
                RingStrengthResult.from_dict(item, index=index, verify=verify)
                for item in payload["results"]
            ),
            canonical_schema_version=str(payload["canonical_schema_version"]),
            digest_algorithm=str(payload["digest_algorithm"]),
            digest=str(payload["digest"]),
        )
        if catalog.topology_graph_digest != index.topology_graph_digest:
            raise RingStrengthSerializationError(
                "Serialized strength catalog belongs to another topology graph."
            )
        if catalog.primitive_ring_catalog_digest != index.catalog_digest:
            raise RingStrengthSerializationError(
                "Serialized strength catalog belongs to another primitive-ring catalog."
            )
        return catalog


def _source_issue(index: PrimitiveRingIndex, domain: RingStrengthDomain) -> str | None:
    catalog = index.catalog
    issues: list[str] = []
    if catalog.ring_family is not PrimitiveRingFamily.PRIMITIVE_NO_SHORTCUT:
        issues.append("source ring family is not PRIMITIVE_NO_SHORTCUT")
    if catalog.options.min_ring_size != 2:
        issues.append("source primitive catalog is not lower-closed from ring size two")
    if not catalog.search_completed_without_resource_truncation:
        issues.append("source primitive-ring search was resource-truncated")
    if catalog.complete_for_ring_sizes_up_to < domain.max_component_size:
        issues.append(
            "source primitive catalog is incomplete for one or more admitted component sizes"
        )
    return None if not issues else "; ".join(issues)


def _ring_size(index: PrimitiveRingIndex, key: PrimitiveRingKey) -> int:
    try:
        return index.ring_for_key(key).size
    except PrimitiveRingIndexInputError as exc:
        raise RingStrengthInputError(str(exc)) from exc


def _diagnostics(
    *,
    source_complete: bool,
    source_issue: str | None,
    admitted_ring_key_count: int,
    candidates: set[RingPlacement],
    explored_edges: set[LiftedEdgeInstanceRef],
    support_term_count: int,
    achieved_depth: int,
    requested_depth: int,
    truncation_reason: str | None,
) -> RingStrengthDiagnostics:
    return RingStrengthDiagnostics(
        source_complete=source_complete,
        source_issue=source_issue,
        admitted_ring_key_count=admitted_ring_key_count,
        candidate_placement_count=len(candidates),
        explored_edge_instance_count=len(explored_edges),
        support_term_count=support_term_count,
        achieved_incidence_depth=achieved_depth,
        requested_incidence_depth=requested_depth,
        truncation_reason=truncation_reason,
    )


def _enumerate_candidate_placements(
    index: PrimitiveRingIndex,
    target_placement: RingPlacement,
    domain: RingStrengthDomain,
    resources: RingStrengthResources,
) -> tuple[
    tuple[RingPlacement, ...],
    RingStrengthDiagnostics,
]:
    target_size = _ring_size(index, target_placement.ring_key)
    admitted_keys = {
        ring.key
        for ring in index.catalog.rings
        if ring.size < target_size and ring.size <= domain.max_component_size
    }
    requested_depth = domain.placement_domain.max_incidence_depth
    target_support = ring_placement_support(index, target_placement)
    frontier: set[LiftedEdgeInstanceRef] = set(target_support.edge_instances)
    explored_edges: set[LiftedEdgeInstanceRef] = set()
    candidates: set[RingPlacement] = set()
    support_term_count = 0
    achieved_depth = 0

    for depth in range(1, requested_depth + 1):
        next_frontier: set[LiftedEdgeInstanceRef] = set()
        for edge in sorted(frontier - explored_edges):
            if len(explored_edges) >= resources.max_search_nodes:
                diagnostics = _diagnostics(
                    source_complete=True,
                    source_issue=None,
                    admitted_ring_key_count=len(admitted_keys),
                    candidates=candidates,
                    explored_edges=explored_edges,
                    support_term_count=support_term_count,
                    achieved_depth=achieved_depth,
                    requested_depth=requested_depth,
                    truncation_reason="max_search_nodes exceeded",
                )
                return tuple(sorted(candidates)), diagnostics
            explored_edges.add(edge)
            for occurrence in ring_placements_covering_edge(index, edge):
                placement = occurrence.placement
                if placement.ring_key not in admitted_keys or placement in candidates:
                    continue
                if len(candidates) >= resources.max_candidate_placements:
                    diagnostics = _diagnostics(
                        source_complete=True,
                        source_issue=None,
                        admitted_ring_key_count=len(admitted_keys),
                        candidates=candidates,
                        explored_edges=explored_edges,
                        support_term_count=support_term_count,
                        achieved_depth=achieved_depth,
                        requested_depth=requested_depth,
                        truncation_reason="max_candidate_placements exceeded",
                    )
                    return tuple(sorted(candidates)), diagnostics
                support = ring_placement_support(index, placement)
                if (
                    support_term_count + len(support.edge_instances)
                    > resources.max_support_terms
                ):
                    diagnostics = _diagnostics(
                        source_complete=True,
                        source_issue=None,
                        admitted_ring_key_count=len(admitted_keys),
                        candidates=candidates,
                        explored_edges=explored_edges,
                        support_term_count=support_term_count,
                        achieved_depth=achieved_depth,
                        requested_depth=requested_depth,
                        truncation_reason="max_support_terms exceeded",
                    )
                    return tuple(sorted(candidates)), diagnostics
                candidates.add(placement)
                support_term_count += len(support.edge_instances)
                next_frontier.update(support.edge_instances)
        achieved_depth = depth
        frontier = next_frontier
        if not frontier - explored_edges:
            # The finite incidence component closed before the requested depth.
            achieved_depth = requested_depth
            break

    diagnostics = _diagnostics(
        source_complete=True,
        source_issue=None,
        admitted_ring_key_count=len(admitted_keys),
        candidates=candidates,
        explored_edges=explored_edges,
        support_term_count=support_term_count,
        achieved_depth=achieved_depth,
        requested_depth=requested_depth,
        truncation_reason=None,
    )
    return tuple(sorted(candidates)), diagnostics


def _validate_strength_inputs(
    index: PrimitiveRingIndex,
    target_placement: RingPlacement,
    domain: RingStrengthDomain,
    resources: RingStrengthResources | None,
) -> RingStrengthResources:
    if not isinstance(index, PrimitiveRingIndex):
        raise RingStrengthInputError("index must be a PrimitiveRingIndex.")
    if not isinstance(target_placement, RingPlacement):
        raise RingStrengthInputError("target_placement must be a RingPlacement.")
    if target_placement.topology_graph_digest != index.topology_graph_digest:
        raise RingStrengthInputError(
            "target_placement belongs to a different topology graph."
        )
    if not isinstance(domain, RingStrengthDomain):
        raise RingStrengthInputError("domain must be a RingStrengthDomain.")
    if domain.target_ring_key != target_placement.ring_key:
        raise RingStrengthInputError(
            "domain target_ring_key must match target_placement.ring_key."
        )
    policy = RingStrengthResources() if resources is None else resources
    if not isinstance(policy, RingStrengthResources):
        raise RingStrengthInputError("resources must be RingStrengthResources.")
    target_size = _ring_size(index, target_placement.ring_key)
    if target_size < 3:
        raise RingStrengthInputError(
            "The first bounded strength backend supports target rings of size at least three."
        )
    if domain.max_component_size >= target_size:
        raise RingStrengthInputError(
            "max_component_size must be strictly smaller than the target ring size."
        )
    return policy


def build_ring_strength_workspace(
    index: PrimitiveRingIndex,
    target_placement: RingPlacement,
    domain: RingStrengthDomain,
    *,
    resources: RingStrengthResources | None = None,
) -> RingStrengthSearchWorkspace:
    """Reconstruct the transient exhaustive candidate workspace for one domain."""

    policy = _validate_strength_inputs(index, target_placement, domain, resources)
    issue = _source_issue(index, domain)
    if issue is not None:
        diagnostics = RingStrengthDiagnostics(
            source_complete=False,
            source_issue=issue,
            admitted_ring_key_count=0,
            candidate_placement_count=0,
            explored_edge_instance_count=0,
            support_term_count=0,
            achieved_incidence_depth=0,
            requested_incidence_depth=domain.placement_domain.max_incidence_depth,
            truncation_reason=None,
        )
        candidates: tuple[RingPlacement, ...] = ()
    else:
        candidates, diagnostics = _enumerate_candidate_placements(
            index, target_placement, domain, policy
        )
    return RingStrengthSearchWorkspace(
        topology_graph_digest=index.topology_graph_digest,
        primitive_ring_catalog_digest=index.catalog_digest,
        target_placement=target_placement,
        domain=domain,
        resources=policy,
        diagnostics=diagnostics,
        candidate_placements=candidates,
        candidate_set_digest=_candidate_set_digest(candidates),
    )


def _verify_strength_witness(
    index: PrimitiveRingIndex, witness: RingStrengthWitness
) -> None:
    parity = set(
        ring_placement_support(index, witness.target_placement).edge_instances
    )
    for component in witness.component_placements:
        for edge in ring_placement_support(index, component).edge_instances:
            if edge in parity:
                parity.remove(edge)
            else:
                parity.add(edge)
    if parity:
        raise RingStrengthSerializationError(
            "Weak-ring witness fails exact physical-edge cancellation."
        )


def _classify_ring_strength_with_workspace(
    index: PrimitiveRingIndex,
    target_placement: RingPlacement,
    domain: RingStrengthDomain,
    *,
    resources: RingStrengthResources | None = None,
) -> tuple[RingStrengthResult, RingStrengthSearchWorkspace]:
    workspace = build_ring_strength_workspace(
        index, target_placement, domain, resources=resources
    )
    diagnostics = workspace.diagnostics
    if not diagnostics.source_complete:
        status = RingStrengthStatus.UNRESOLVED_SOURCE_INCOMPLETE
        witness = None
    elif diagnostics.truncation_reason is not None:
        status = RingStrengthStatus.UNRESOLVED_TRUNCATED
        witness = None
    else:
        try:
            cancellation = solve_finite_ring_cancellation(
                index,
                target_placement,
                workspace.candidate_placements,
                resources=workspace.resources.cancellation_resources,
            )
        except PrimitiveRingCancellationResourceError as exc:
            diagnostics = RingStrengthDiagnostics(
                source_complete=diagnostics.source_complete,
                source_issue=diagnostics.source_issue,
                admitted_ring_key_count=diagnostics.admitted_ring_key_count,
                candidate_placement_count=diagnostics.candidate_placement_count,
                explored_edge_instance_count=diagnostics.explored_edge_instance_count,
                support_term_count=diagnostics.support_term_count,
                achieved_incidence_depth=diagnostics.achieved_incidence_depth,
                requested_incidence_depth=diagnostics.requested_incidence_depth,
                truncation_reason=exc.reason,
            )
            workspace = RingStrengthSearchWorkspace(
                topology_graph_digest=workspace.topology_graph_digest,
                primitive_ring_catalog_digest=workspace.primitive_ring_catalog_digest,
                target_placement=workspace.target_placement,
                domain=workspace.domain,
                resources=workspace.resources,
                diagnostics=diagnostics,
                candidate_placements=workspace.candidate_placements,
                candidate_set_digest=workspace.candidate_set_digest,
            )
            status = RingStrengthStatus.UNRESOLVED_TRUNCATED
            witness = None
        else:
            if cancellation.status is FiniteRingCancellationStatus.DECOMPOSITION_FOUND:
                if cancellation.witness is None:
                    raise RingStrengthInvariantError(
                        "Finite cancellation reported a decomposition without a witness."
                    )
                status = RingStrengthStatus.WEAK_CERTIFIED
                witness = RingStrengthWitness.from_cancellation_witness(
                    cancellation.witness
                )
                _verify_strength_witness(index, witness)
            else:
                status = RingStrengthStatus.STRONG_IN_DOMAIN
                witness = None
    result = RingStrengthResult(
        topology_graph_digest=index.topology_graph_digest,
        primitive_ring_catalog_digest=index.catalog_digest,
        target_placement=target_placement,
        domain=domain,
        resources=workspace.resources,
        status=status,
        diagnostics=workspace.diagnostics,
        candidate_set_digest=workspace.candidate_set_digest,
        witness=witness,
    )
    return result, workspace


def classify_ring_strength(
    index: PrimitiveRingIndex,
    target_placement: RingPlacement,
    domain: RingStrengthDomain,
    *,
    resources: RingStrengthResources | None = None,
) -> RingStrengthResult:
    """Classify one primitive-ring placement inside an exact finite domain.

    The returned persistent result excludes the derivable candidate workspace.
    Call :func:`build_ring_strength_workspace` when candidate-level diagnostics
    are needed.
    """

    result, _workspace = _classify_ring_strength_with_workspace(
        index, target_placement, domain, resources=resources
    )
    return result

def build_ring_strength_catalog(
    index: PrimitiveRingIndex,
    domains: Iterable[RingStrengthDomain],
    *,
    resources: RingStrengthResources | None = None,
) -> RingStrengthCatalog:
    """Classify canonical zero-shift representatives for explicit domains."""

    if not isinstance(index, PrimitiveRingIndex):
        raise RingStrengthInputError("index must be a PrimitiveRingIndex.")
    try:
        domain_tuple = tuple(domains)
    except TypeError as exc:
        raise RingStrengthInputError(
            "domains must be an iterable of RingStrengthDomain records."
        ) from exc
    if any(not isinstance(item, RingStrengthDomain) for item in domain_tuple):
        raise RingStrengthInputError(
            "domains must contain RingStrengthDomain records."
        )
    sorted_domains = tuple(sorted(domain_tuple, key=lambda item: item.target_ring_key))
    keys = tuple(item.target_ring_key for item in sorted_domains)
    if len(set(keys)) != len(keys):
        raise RingStrengthInputError(
            "domains must contain at most one domain per target ring key."
        )
    policy = RingStrengthResources() if resources is None else resources
    if not isinstance(policy, RingStrengthResources):
        raise RingStrengthInputError("resources must be RingStrengthResources.")

    results = tuple(
        classify_ring_strength(
            index,
            RingPlacement(index.topology_graph_digest, domain.target_ring_key, (0, 0, 0)),
            domain,
            resources=policy,
        )
        for domain in sorted_domains
    )
    return RingStrengthCatalog(
        topology_graph_digest=index.topology_graph_digest,
        primitive_ring_catalog_digest=index.catalog_digest,
        results=results,
    )


__all__ = [
    "CANONICAL_RING_STRENGTH_CATALOG_SCHEMA",
    "CANONICAL_RING_STRENGTH_SCHEMA",
    "RING_STRENGTH_DIGEST_ALGORITHM",
    "EdgeIncidencePlacementDomain",
    "RingStrengthCatalog",
    "RingStrengthDiagnostics",
    "RingStrengthDomain",
    "RingStrengthError",
    "RingStrengthInputError",
    "RingStrengthInvariantError",
    "RingStrengthResources",
    "RingStrengthResult",
    "RingStrengthSearchWorkspace",
    "RingStrengthSerializationError",
    "RingStrengthStatus",
    "RingStrengthWitness",
    "build_ring_strength_catalog",
    "build_ring_strength_workspace",
    "classify_ring_strength",
]
