"""Forward-only runtime projection of the persisted TARGET-DATA2C-MVIDX1 graph.

MVIDX1 remains the scientific/persistence identity.  This module exposes only
candidate-to-witness and candidate-to-obligation CSR plus correlation codes so
MVSEL2/REPAIR2 cannot accidentally depend on inverse adjacency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import TrainingDataInputError, validate_digest
from .target_coverage_sparse_index import (
    TargetCoverageHardObligation,
    TargetCoverageSparseIndex,
    _canonical_array,
    _validate_offsets,
    _validate_sorted_unique_rows,
)


@dataclass(frozen=True, slots=True)
class TargetCoverageSparseForwardFamilyView:
    family_id: str
    family_digest: str
    mvidx1_family_digest: str
    candidate_count: int
    witness_count: int
    candidate_offsets: np.ndarray | Sequence[int]
    candidate_witnesses: np.ndarray | Sequence[int]
    _array_references: Mapping[str, Mapping[str, Any]] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not self.family_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward family ID is empty.")
        object.__setattr__(self, "family_digest", validate_digest(self.family_digest, name="family_digest"))
        object.__setattr__(
            self,
            "mvidx1_family_digest",
            validate_digest(self.mvidx1_family_digest, name="mvidx1_family_digest"),
        )
        candidate_count = int(self.candidate_count)
        witness_count = int(self.witness_count)
        if candidate_count < 1 or witness_count < 1:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward family cardinality is invalid.")
        offsets = _canonical_array(
            self.candidate_offsets, dtype="<u8", ndim=1, name="forward candidate_offsets"
        )
        witnesses = _canonical_array(
            self.candidate_witnesses, dtype="<u4", ndim=1, name="forward candidate_witnesses"
        )
        _validate_offsets(
            offsets,
            item_count=candidate_count,
            edge_count=len(witnesses),
            name="forward candidate",
        )
        if witnesses.size and int(np.max(witnesses)) >= witness_count:
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward family contains an out-of-range witness.")
        _validate_sorted_unique_rows(offsets, witnesses, name="forward candidate-to-witness")
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "witness_count", witness_count)
        object.__setattr__(self, "candidate_offsets", offsets)
        object.__setattr__(self, "candidate_witnesses", witnesses)
        object.__setattr__(
            self,
            "_array_references",
            {str(name): dict(value) for name, value in self._array_references.items()},
        )

    @property
    def edge_count(self) -> int:
        return len(self.candidate_witnesses)

    @property
    def array_references(self) -> Mapping[str, Mapping[str, Any]]:
        return self._array_references

    def candidate_witness_indices(self, candidate_index: int) -> np.ndarray:
        candidate = int(candidate_index)
        if candidate < 0 or candidate >= self.candidate_count:
            raise IndexError(candidate)
        start = int(self.candidate_offsets[candidate])
        stop = int(self.candidate_offsets[candidate + 1])
        return self.candidate_witnesses[start:stop]


@dataclass(frozen=True, slots=True)
class TargetCoverageSparseForwardDomainView:
    label_domain_id: str
    frame_domain_digest: str
    mvidx1_domain_digest: str
    candidate_count: int
    families: tuple[TargetCoverageSparseForwardFamilyView, ...]
    obligations: tuple[TargetCoverageHardObligation, ...]
    candidate_obligation_offsets: np.ndarray | Sequence[int]
    candidate_obligations: np.ndarray | Sequence[int]
    correlation_unit_ids: tuple[str, ...]
    candidate_correlation_unit_codes: np.ndarray | Sequence[int]
    _family_by_id: Mapping[str, TargetCoverageSparseForwardFamilyView] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward domain ID is empty.")
        object.__setattr__(
            self, "frame_domain_digest", validate_digest(self.frame_domain_digest, name="frame_domain_digest")
        )
        object.__setattr__(
            self,
            "mvidx1_domain_digest",
            validate_digest(self.mvidx1_domain_digest, name="mvidx1_domain_digest"),
        )
        candidate_count = int(self.candidate_count)
        families = tuple(sorted(self.families, key=lambda item: item.family_id))
        obligations = tuple(sorted(self.obligations, key=lambda item: item.obligation_id))
        if candidate_count < 1 or not families or any(
            family.candidate_count != candidate_count for family in families
        ):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward domain cardinality is invalid.")
        if len({family.family_id for family in families}) != len(families):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward domain family IDs are not unique.")
        if not obligations or len({item.obligation_id for item in obligations}) != len(obligations):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward obligations are invalid.")
        offsets = _canonical_array(
            self.candidate_obligation_offsets,
            dtype="<u8",
            ndim=1,
            name="forward candidate_obligation_offsets",
        )
        incidence = _canonical_array(
            self.candidate_obligations,
            dtype="<u4",
            ndim=1,
            name="forward candidate_obligations",
        )
        _validate_offsets(
            offsets,
            item_count=candidate_count,
            edge_count=len(incidence),
            name="forward candidate-obligation",
        )
        if incidence.size and int(np.max(incidence)) >= len(obligations):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward obligation incidence is out of range.")
        _validate_sorted_unique_rows(offsets, incidence, name="forward candidate-to-obligation")
        unit_ids = tuple(validate_digest(value, name="correlation_unit_id") for value in self.correlation_unit_ids)
        unit_codes = _canonical_array(
            self.candidate_correlation_unit_codes,
            dtype="<u4",
            ndim=1,
            name="forward candidate_correlation_unit_codes",
        )
        if (
            not unit_ids
            or tuple(sorted(set(unit_ids))) != unit_ids
            or unit_codes.shape != (candidate_count,)
            or int(np.max(unit_codes)) >= len(unit_ids)
        ):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward correlation units are invalid.")
        object.__setattr__(self, "candidate_count", candidate_count)
        object.__setattr__(self, "families", families)
        object.__setattr__(self, "obligations", obligations)
        object.__setattr__(self, "candidate_obligation_offsets", offsets)
        object.__setattr__(self, "candidate_obligations", incidence)
        object.__setattr__(self, "correlation_unit_ids", unit_ids)
        object.__setattr__(self, "candidate_correlation_unit_codes", unit_codes)
        object.__setattr__(self, "_family_by_id", {item.family_id: item for item in families})

    def family(self, family_id: str) -> TargetCoverageSparseForwardFamilyView:
        try:
            return self._family_by_id[family_id]
        except KeyError:
            raise KeyError(family_id) from None

    def candidate_obligation_indices(self, candidate_index: int) -> np.ndarray:
        candidate = int(candidate_index)
        if candidate < 0 or candidate >= self.candidate_count:
            raise IndexError(candidate)
        start = int(self.candidate_obligation_offsets[candidate])
        stop = int(self.candidate_obligation_offsets[candidate + 1])
        return self.candidate_obligations[start:stop]


@dataclass(frozen=True, slots=True)
class TargetCoverageSparseForwardIndexView:
    dataset_id: str
    mvidx1_content_digest: str
    target_coverage_reference_digest: str
    target_data_role_freeze_digest: str
    target_coverage_feasibility_digest: str
    domains: tuple[TargetCoverageSparseForwardDomainView, ...]
    _domain_by_id: Mapping[str, TargetCoverageSparseForwardDomainView] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not self.dataset_id.strip():
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward index dataset ID is empty.")
        for name in (
            "mvidx1_content_digest",
            "target_coverage_reference_digest",
            "target_data_role_freeze_digest",
            "target_coverage_feasibility_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("TARGET-DATA2C-MVIDX1 forward index domains are invalid.")
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "_domain_by_id", {item.label_domain_id: item for item in domains})

    def domain(self, label_domain_id: str) -> TargetCoverageSparseForwardDomainView:
        try:
            return self._domain_by_id[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None


def target_coverage_sparse_forward_view(
    index: TargetCoverageSparseIndex,
) -> TargetCoverageSparseForwardIndexView:
    """Project an already-authenticated in-memory MVIDX1 into forward-only views."""

    domains: list[TargetCoverageSparseForwardDomainView] = []
    for domain in index.domains:
        families = tuple(
            TargetCoverageSparseForwardFamilyView(
                family_id=family.family_id,
                family_digest=family.family_digest,
                mvidx1_family_digest=family.content_digest,
                candidate_count=family.candidate_count,
                witness_count=family.witness_count,
                candidate_offsets=family.candidate_offsets,
                candidate_witnesses=family.candidate_witnesses,
                _array_references={
                    name: family.array_references[name]
                    for name in ("candidate_offsets", "candidate_witnesses")
                },
            )
            for family in domain.families
        )
        domains.append(
            TargetCoverageSparseForwardDomainView(
                label_domain_id=domain.label_domain_id,
                frame_domain_digest=domain.frame_domain_digest,
                mvidx1_domain_digest=domain.content_digest,
                candidate_count=domain.candidate_count,
                families=families,
                obligations=domain.obligations,
                candidate_obligation_offsets=domain.candidate_obligation_offsets,
                candidate_obligations=domain.candidate_obligations,
                correlation_unit_ids=domain.correlation_unit_ids,
                candidate_correlation_unit_codes=domain.candidate_correlation_unit_codes,
            )
        )
    return TargetCoverageSparseForwardIndexView(
        dataset_id=index.dataset_id,
        mvidx1_content_digest=index.content_digest,
        target_coverage_reference_digest=index.target_coverage_reference_digest,
        target_data_role_freeze_digest=index.target_data_role_freeze_digest,
        target_coverage_feasibility_digest=index.target_coverage_feasibility_digest,
        domains=tuple(domains),
    )
