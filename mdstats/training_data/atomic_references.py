"""Structural atomic-reference identifiability audits for MLFF-DATA2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

ATOMIC_REFERENCE_IDENTIFIABILITY_POLICY_SCHEMA = (
    "mdstats.atomic-reference-identifiability-policy.v1"
)
ATOMIC_REFERENCE_IDENTIFIABILITY_REPORT_SCHEMA = (
    "mdstats.atomic-reference-identifiability-report.v1"
)
ATOMIC_REFERENCE_IDENTIFIABILITY_CATALOG_SCHEMA = (
    "mdstats.atomic-reference-identifiability-catalog.v1"
)
ATOMIC_REFERENCE_IDENTIFIABILITY_POLICY_VERSION = (
    "mdstats.mlff-data2.atomic-reference-identifiability.2026-07.v1"
)


class AtomicReferenceIdentifiabilityOutcome(str, Enum):
    IDENTIFIED = "identified"
    RANK_DEFICIENT_FIXED_DOMAIN_USABLE = "rank_deficient_but_fixed_domain_usable"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class AtomicReferenceIdentifiabilityPolicy:
    relative_singular_value_tolerance: float = 1.0e-12
    allow_rank_deficient_fixed_domain: bool = True
    policy_version: str = ATOMIC_REFERENCE_IDENTIFIABILITY_POLICY_VERSION

    def __post_init__(self) -> None:
        tolerance = float(self.relative_singular_value_tolerance)
        if not math.isfinite(tolerance) or tolerance <= 0.0:
            raise TrainingDataInputError(
                "relative_singular_value_tolerance must be positive and finite."
            )
        object.__setattr__(self, "relative_singular_value_tolerance", tolerance)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOMIC_REFERENCE_IDENTIFIABILITY_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "relative_singular_value_tolerance": self.relative_singular_value_tolerance,
            "allow_rank_deficient_fixed_domain": self.allow_rank_deficient_fixed_domain,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicReferenceIdentifiabilityPolicy":
        if payload.get("schema") != ATOMIC_REFERENCE_IDENTIFIABILITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported atomic-reference policy schema.")
        result = cls(
            relative_singular_value_tolerance=float(payload["relative_singular_value_tolerance"]),
            allow_rank_deficient_fixed_domain=bool(payload["allow_rank_deficient_fixed_domain"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Atomic-reference policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AtomicReferenceIdentifiabilityReport:
    policy_digest: str
    row_ids: tuple[str, ...]
    element_order: tuple[str, ...]
    count_matrix: tuple[tuple[int, ...], ...]
    rank: int
    singular_values: tuple[float, ...]
    condition_number: float | None
    null_space_dimension: int
    identifiable_combinations: tuple[tuple[float, ...], ...]
    null_space_basis: tuple[tuple[float, ...], ...]
    outcome: AtomicReferenceIdentifiabilityOutcome
    transfer_limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        object.__setattr__(self, "outcome", AtomicReferenceIdentifiabilityOutcome(self.outcome))
        if not self.row_ids or not self.element_order:
            raise TrainingDataInputError("Atomic-reference audit requires rows and elements.")
        if len(self.count_matrix) != len(self.row_ids):
            raise TrainingDataInputError("Count matrix row count does not match row_ids.")
        if any(len(row) != len(self.element_order) for row in self.count_matrix):
            raise TrainingDataInputError("Count matrix column count is inconsistent.")
        if any(value < 0 for row in self.count_matrix for value in row):
            raise TrainingDataInputError("Element counts must be nonnegative.")
        if not 0 <= self.rank <= len(self.element_order):
            raise TrainingDataInputError("Atomic-reference rank is out of bounds.")
        if self.null_space_dimension != len(self.element_order) - self.rank:
            raise TrainingDataInputError("Null-space dimension is inconsistent with rank.")
        if self.condition_number is not None:
            value = float(self.condition_number)
            if not math.isfinite(value) or value < 1.0:
                raise TrainingDataInputError("Condition number must be finite and >= 1.")
            object.__setattr__(self, "condition_number", value)
        object.__setattr__(self, "row_ids", tuple(str(item) for item in self.row_ids))
        object.__setattr__(self, "element_order", tuple(str(item) for item in self.element_order))
        object.__setattr__(self, "count_matrix", tuple(tuple(int(v) for v in row) for row in self.count_matrix))
        object.__setattr__(self, "singular_values", tuple(float(v) for v in self.singular_values))
        object.__setattr__(self, "identifiable_combinations", tuple(tuple(float(v) for v in row) for row in self.identifiable_combinations))
        object.__setattr__(self, "null_space_basis", tuple(tuple(float(v) for v in row) for row in self.null_space_basis))
        object.__setattr__(self, "transfer_limitations", tuple(str(item) for item in self.transfer_limitations))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOMIC_REFERENCE_IDENTIFIABILITY_REPORT_SCHEMA,
            "policy_digest": self.policy_digest,
            "row_ids": list(self.row_ids),
            "element_order": list(self.element_order),
            "count_matrix": [list(row) for row in self.count_matrix],
            "rank": self.rank,
            "singular_values": list(self.singular_values),
            "condition_number": self.condition_number,
            "null_space_dimension": self.null_space_dimension,
            "identifiable_combinations": [list(row) for row in self.identifiable_combinations],
            "null_space_basis": [list(row) for row in self.null_space_basis],
            "outcome": self.outcome.value,
            "transfer_limitations": list(self.transfer_limitations),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicReferenceIdentifiabilityReport":
        if payload.get("schema") != ATOMIC_REFERENCE_IDENTIFIABILITY_REPORT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported atomic-reference-identifiability schema."
            )
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            row_ids=tuple(str(item) for item in payload["row_ids"]),
            element_order=tuple(str(item) for item in payload["element_order"]),
            count_matrix=tuple(tuple(int(v) for v in row) for row in payload["count_matrix"]),
            rank=int(payload["rank"]),
            singular_values=tuple(float(v) for v in payload["singular_values"]),
            condition_number=(None if payload.get("condition_number") is None else float(payload["condition_number"])),
            null_space_dimension=int(payload["null_space_dimension"]),
            identifiable_combinations=tuple(tuple(float(v) for v in row) for row in payload["identifiable_combinations"]),
            null_space_basis=tuple(tuple(float(v) for v in row) for row in payload["null_space_basis"]),
            outcome=AtomicReferenceIdentifiabilityOutcome(payload["outcome"]),
            transfer_limitations=tuple(str(item) for item in payload.get("transfer_limitations", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Atomic-reference-identifiability digest mismatch."
            )
        return result



@dataclass(frozen=True, slots=True)
class AtomicReferenceIdentifiabilityCatalog:
    """Per-label-domain structural identifiability reports."""

    policy_digest: str
    domain_reports: tuple[tuple[str, AtomicReferenceIdentifiabilityReport], ...]
    _by_domain_id: Mapping[str, AtomicReferenceIdentifiabilityReport] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest")
        )
        reports = tuple(sorted(
            ((str(domain_id), report) for domain_id, report in self.domain_reports),
            key=lambda item: item[0],
        ))
        if len({domain_id for domain_id, _ in reports}) != len(reports):
            raise TrainingDataInputError(
                "Atomic-reference catalog contains duplicate label-domain ids."
            )
        if any(report.policy_digest != self.policy_digest for _, report in reports):
            raise TrainingDataInputError(
                "Atomic-reference report policy does not match catalog policy."
            )
        object.__setattr__(self, "domain_reports", reports)
        object.__setattr__(self, "_by_domain_id", dict(reports))

    def report_for_domain(self, domain_id: str) -> AtomicReferenceIdentifiabilityReport:
        try:
            return self._by_domain_id[domain_id]
        except KeyError:
            raise KeyError(domain_id) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ATOMIC_REFERENCE_IDENTIFIABILITY_CATALOG_SCHEMA,
            "policy_digest": self.policy_digest,
            "domain_reports": {
                domain_id: report.to_dict() for domain_id, report in self.domain_reports
            },
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
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "AtomicReferenceIdentifiabilityCatalog":
        if payload.get("schema") != ATOMIC_REFERENCE_IDENTIFIABILITY_CATALOG_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported atomic-reference-identifiability-catalog schema."
            )
        reports = payload.get("domain_reports", {})
        if not isinstance(reports, Mapping):
            raise TrainingDataSerializationError("domain_reports must be a mapping.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            domain_reports=tuple(
                (str(domain_id), AtomicReferenceIdentifiabilityReport.from_dict(report))
                for domain_id, report in reports.items()
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Atomic-reference-identifiability-catalog digest mismatch."
            )
        return result

def analyze_atomic_reference_identifiability(
    composition_counts: Mapping[str, Mapping[str, int]],
    *,
    policy: AtomicReferenceIdentifiabilityPolicy | None = None,
) -> AtomicReferenceIdentifiabilityReport:
    """Audit the rank of the element-count design matrix without using energies."""

    active = AtomicReferenceIdentifiabilityPolicy() if policy is None else policy
    if not composition_counts:
        raise TrainingDataInputError("At least one composition count vector is required.")
    row_ids = tuple(sorted(str(key) for key in composition_counts))
    element_order = tuple(sorted({
        str(element)
        for row in composition_counts.values()
        for element in row
    }))
    if not element_order:
        raise TrainingDataInputError("Composition count vectors contain no elements.")
    matrix = np.asarray(
        [
            [int(composition_counts[row_id].get(element, 0)) for element in element_order]
            for row_id in row_ids
        ],
        dtype=np.float64,
    )
    if np.any(matrix < 0) or not np.all(np.equal(matrix, np.floor(matrix))):
        raise TrainingDataInputError("Composition counts must be nonnegative integers.")
    _, singular_values, vh = np.linalg.svd(matrix, full_matrices=True)
    scale = float(singular_values[0]) if singular_values.size else 0.0
    threshold = active.relative_singular_value_tolerance * max(scale, 1.0)
    rank = int(np.count_nonzero(singular_values > threshold))
    n_elements = len(element_order)
    null_dimension = n_elements - rank
    condition_number = None
    if rank == n_elements and singular_values.size:
        condition_number = float(singular_values[0] / singular_values[rank - 1])
    identifiable = tuple(tuple(float(v) for v in row) for row in vh[:rank])
    null_space = tuple(tuple(float(v) for v in row) for row in vh[rank:])
    if rank == n_elements:
        outcome = AtomicReferenceIdentifiabilityOutcome.IDENTIFIED
        limitations: tuple[str, ...] = ()
    elif active.allow_rank_deficient_fixed_domain and rank > 0:
        outcome = AtomicReferenceIdentifiabilityOutcome.RANK_DEFICIENT_FIXED_DOMAIN_USABLE
        limitations = (
            "Individual elemental reference corrections are non-unique along the recorded null space.",
            "The audit does not establish transferability to compositions outside the observed count-vector span.",
            "Defects, changed framework stoichiometry, changed cation count, salt phases, and interfaces require new reference support.",
        )
    else:
        outcome = AtomicReferenceIdentifiabilityOutcome.REJECTED
        limitations = (
            "Element-count design matrix is rank deficient under the active policy.",
        )
    return AtomicReferenceIdentifiabilityReport(
        policy_digest=active.policy_digest,
        row_ids=row_ids,
        element_order=element_order,
        count_matrix=tuple(tuple(int(v) for v in row) for row in matrix.astype(np.int64)),
        rank=rank,
        singular_values=tuple(float(v) for v in singular_values),
        condition_number=condition_number,
        null_space_dimension=null_dimension,
        identifiable_combinations=identifiable,
        null_space_basis=null_space,
        outcome=outcome,
        transfer_limitations=limitations,
    )
