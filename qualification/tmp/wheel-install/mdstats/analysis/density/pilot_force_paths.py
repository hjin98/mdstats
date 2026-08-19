"""Stage-11E8a-S4 force-density and transition-path readiness pilot.

This source-bound boundary executes the existing Stage-11E3 force-refinement
contract without weakening its PMF provenance requirements.  It also evaluates
whether the Stage-11E4 provisional temporal result is ready for Stage-11E6 and
11E6b execution.  Final segmentation and observed paths are executed only when
an externally supplied validated frozen-state catalog is source-compatible and
the S2 spatial hypothesis is authoritative.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from time import perf_counter
from types import MappingProxyType
from typing import Any

import numpy as np

from ...collection import AtomisticFrameCollection
from .attractors import DensityAttractorOptions, DensityAttractorResourcePolicy
from .final_segmentation import (
    FinalHystereticSegmentationCatalog,
    FinalSegmentationOptions,
    FinalSegmentationResourcePolicy,
    prepare_final_hysteretic_segmentation,
)
from .force_refinement import (
    ForceEvidenceStatus,
    ForceRefinementCatalog,
    LocalMeanForceOptions,
    LocalMeanForceResourcePolicy,
    prepare_force_refinement_catalog,
)
from ._pilot_common import (
    array_payload_bytes as _array_payload_bytes,
    canonical_json as _canonical_json,
    digest as _digest,
    fraction as _fraction,
    freeze as _freeze,
    json_value as _json_value,
    positive as _positive,
    replace_evidence as _replace_evidence,
)

from .pilot_audit import (
    NaLta300KPilotReport,
    PilotAuditInputError,
    PilotAuditResourcePolicy,
    PilotEvidenceRecord,
    PilotEvidenceStatus,
    PilotPMFStatus,
    PilotRateStatus,
    PilotResourceUsage,
    PilotScientificOutcome,
    prepare_na_lta_300k_pilot_report,
)
from .pilot_density_attractors import NaLta300KDensityAttractorPilotOptions
from .pilot_refinement_lineage import NaLta300KRefinementLineageOptions
from .pilot_structural_temporal import (
    NaLta300KStructuralTemporalOptions,
    NaLta300KStructuralTemporalPilot,
    prepare_na_lta_300k_structural_temporal_pilot,
)
from .species import SpeciesDensityResourcePolicy
from .temporal_assignment import PassageOutcome, TemporalAssignmentResourcePolicy
from .transition_paths import (
    ObservedTransitionPathCatalog,
    TransitionPathOptions,
    TransitionPathResourcePolicy,
    prepare_observed_transition_paths,
)

PILOT_FORCE_PATH_STAGE = "11E8a-S4"
PILOT_FORCE_PATH_OPTIONS_SCHEMA = "mdstats.na-lta-300k-force-path-options.v1"
FORCE_DENSITY_CERTIFICATE_SCHEMA = "mdstats.na-lta-force-density-certificate.v1"
TRANSITION_PATH_PREPARATION_SCHEMA = "mdstats.na-lta-transition-path-preparation.v1"


















class ForceDensityAgreementStatus(str, Enum):
    RESOLVED = "resolved"
    PMF_PROVENANCE_REJECTED = "pmf_provenance_rejected"
    FORCE_UNAVAILABLE = "force_unavailable"
    INSUFFICIENT_SUPPORT = "insufficient_support"
    DISAGREEMENT = "disagreement"
    SPATIAL_HYPOTHESIS_UNRESOLVED = "spatial_hypothesis_unresolved"


class TransitionPathPreparationStatus(str, Enum):
    READY = "ready"
    EXECUTED_NO_CONNECTIONS = "executed_no_connections"
    MISSING_VALIDATED_STATES = "missing_validated_states"
    SPATIAL_HYPOTHESIS_UNRESOLVED = "spatial_hypothesis_unresolved"
    NO_PROVISIONAL_JUMPS = "no_provisional_jumps"


@dataclass(frozen=True, slots=True)
class NaLta300KForcePathOptions:
    minimum_force_supported_node_fraction: float = 0.05
    minimum_resolved_refinement_fraction: float = 0.50
    maximum_median_relative_residual: float = 1.0
    residual_scale_floor: float = 1.0e-8
    require_authoritative_spatial_hypothesis: bool = True
    force_options: LocalMeanForceOptions = field(default_factory=LocalMeanForceOptions)
    final_segmentation_options: FinalSegmentationOptions = field(default_factory=FinalSegmentationOptions)
    transition_path_options: TransitionPathOptions = field(default_factory=TransitionPathOptions)
    signature: str = ""

    def __post_init__(self) -> None:
        supported = _fraction(self.minimum_force_supported_node_fraction, "minimum_force_supported_node_fraction")
        refined = _fraction(self.minimum_resolved_refinement_fraction, "minimum_resolved_refinement_fraction")
        residual = _positive(self.maximum_median_relative_residual, "maximum_median_relative_residual")
        floor = _positive(self.residual_scale_floor, "residual_scale_floor")
        if not isinstance(self.force_options, LocalMeanForceOptions):
            raise PilotAuditInputError("force_options must be LocalMeanForceOptions.")
        if not isinstance(self.final_segmentation_options, FinalSegmentationOptions):
            raise PilotAuditInputError("final_segmentation_options must be FinalSegmentationOptions.")
        if not isinstance(self.transition_path_options, TransitionPathOptions):
            raise PilotAuditInputError("transition_path_options must be TransitionPathOptions.")
        payload = {
            "schema": PILOT_FORCE_PATH_OPTIONS_SCHEMA,
            "minimum_force_supported_node_fraction": supported,
            "minimum_resolved_refinement_fraction": refined,
            "maximum_median_relative_residual": residual,
            "residual_scale_floor": floor,
            "require_authoritative_spatial_hypothesis": bool(self.require_authoritative_spatial_hypothesis),
            "force_options_signature": self.force_options.signature,
            "final_segmentation_options_signature": self.final_segmentation_options.signature,
            "transition_path_options_signature": self.transition_path_options.signature,
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("S4 options signature is inconsistent.")
        object.__setattr__(self, "minimum_force_supported_node_fraction", supported)
        object.__setattr__(self, "minimum_resolved_refinement_fraction", refined)
        object.__setattr__(self, "maximum_median_relative_residual", residual)
        object.__setattr__(self, "residual_scale_floor", floor)
        object.__setattr__(self, "require_authoritative_spatial_hypothesis", bool(self.require_authoritative_spatial_hypothesis))
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PILOT_FORCE_PATH_OPTIONS_SCHEMA,
            "minimum_force_supported_node_fraction": self.minimum_force_supported_node_fraction,
            "minimum_resolved_refinement_fraction": self.minimum_resolved_refinement_fraction,
            "maximum_median_relative_residual": self.maximum_median_relative_residual,
            "residual_scale_floor": self.residual_scale_floor,
            "require_authoritative_spatial_hypothesis": self.require_authoritative_spatial_hypothesis,
            "force_options": self.force_options.to_dict(),
            "final_segmentation_options": self.final_segmentation_options.to_dict(),
            "transition_path_options": self.transition_path_options.to_dict(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NaLta300KForcePathOptions":
        if payload.get("schema") != PILOT_FORCE_PATH_OPTIONS_SCHEMA:
            raise PilotAuditInputError("Unsupported S4 options schema.")
        return cls(
            minimum_force_supported_node_fraction=float(payload["minimum_force_supported_node_fraction"]),
            minimum_resolved_refinement_fraction=float(payload["minimum_resolved_refinement_fraction"]),
            maximum_median_relative_residual=float(payload["maximum_median_relative_residual"]),
            residual_scale_floor=float(payload["residual_scale_floor"]),
            require_authoritative_spatial_hypothesis=bool(payload["require_authoritative_spatial_hypothesis"]),
            force_options=LocalMeanForceOptions.from_dict(payload["force_options"]),
            final_segmentation_options=FinalSegmentationOptions.from_dict(payload["final_segmentation_options"]),
            transition_path_options=TransitionPathOptions.from_dict(payload["transition_path_options"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class ForceDensityAgreementCertificate:
    status: ForceDensityAgreementStatus
    sample_catalog_signature: str
    density_estimate_signature: str
    attractor_catalog_signature: str
    force_refinement_signature: str
    joint_force_sample_count: int
    pmf_force_sample_count: int
    density_supported_node_count: int
    force_supported_node_count: int
    force_supported_node_fraction: float
    refinement_status_counts: Mapping[str, int]
    resolved_refinement_fraction: float
    residual_count: int
    median_residual_norm: float | None
    maximum_residual_norm: float | None
    median_relative_residual: float | None
    maximum_relative_residual: float | None
    median_cosine_alignment: float | None
    minimum_cosine_alignment: float | None
    spatial_hypothesis_authoritative: bool
    messages: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        status = ForceDensityAgreementStatus(self.status)
        counts = MappingProxyType({str(k): int(v) for k, v in sorted(self.refinement_status_counts.items())})
        if any(v < 0 for v in counts.values()):
            raise PilotAuditInputError("Refinement counts must be nonnegative.")
        values = {
            "joint_force_sample_count": int(self.joint_force_sample_count),
            "pmf_force_sample_count": int(self.pmf_force_sample_count),
            "density_supported_node_count": int(self.density_supported_node_count),
            "force_supported_node_count": int(self.force_supported_node_count),
            "residual_count": int(self.residual_count),
        }
        if any(v < 0 for v in values.values()):
            raise PilotAuditInputError("Force-density counters must be nonnegative.")
        fsf = _fraction(self.force_supported_node_fraction, "force_supported_node_fraction")
        rrf = _fraction(self.resolved_refinement_fraction, "resolved_refinement_fraction")
        optional = []
        for name in (
            "median_residual_norm", "maximum_residual_norm", "median_relative_residual",
            "maximum_relative_residual", "median_cosine_alignment", "minimum_cosine_alignment",
        ):
            value = getattr(self, name)
            optional.append((name, None if value is None else float(value)))
            if value is not None and not np.isfinite(float(value)):
                raise PilotAuditInputError(f"{name} must be finite when present.")
        messages = tuple(str(v) for v in self.messages)
        payload = {
            "schema": FORCE_DENSITY_CERTIFICATE_SCHEMA,
            "status": status.value,
            "sample_catalog_signature": self.sample_catalog_signature,
            "density_estimate_signature": self.density_estimate_signature,
            "attractor_catalog_signature": self.attractor_catalog_signature,
            "force_refinement_signature": self.force_refinement_signature,
            **values,
            "force_supported_node_fraction": fsf,
            "refinement_status_counts": dict(counts),
            "resolved_refinement_fraction": rrf,
            **dict(optional),
            "spatial_hypothesis_authoritative": bool(self.spatial_hypothesis_authoritative),
            "messages": list(messages),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Force-density certificate signature is inconsistent.")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "refinement_status_counts", counts)
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "force_supported_node_fraction", fsf)
        object.__setattr__(self, "resolved_refinement_fraction", rrf)
        for name, value in optional:
            object.__setattr__(self, name, value)
        object.__setattr__(self, "spatial_hypothesis_authoritative", bool(self.spatial_hypothesis_authoritative))
        object.__setattr__(self, "messages", messages)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FORCE_DENSITY_CERTIFICATE_SCHEMA,
            "status": self.status.value,
            "sample_catalog_signature": self.sample_catalog_signature,
            "density_estimate_signature": self.density_estimate_signature,
            "attractor_catalog_signature": self.attractor_catalog_signature,
            "force_refinement_signature": self.force_refinement_signature,
            "joint_force_sample_count": self.joint_force_sample_count,
            "pmf_force_sample_count": self.pmf_force_sample_count,
            "density_supported_node_count": self.density_supported_node_count,
            "force_supported_node_count": self.force_supported_node_count,
            "force_supported_node_fraction": self.force_supported_node_fraction,
            "refinement_status_counts": dict(self.refinement_status_counts),
            "resolved_refinement_fraction": self.resolved_refinement_fraction,
            "residual_count": self.residual_count,
            "median_residual_norm": self.median_residual_norm,
            "maximum_residual_norm": self.maximum_residual_norm,
            "median_relative_residual": self.median_relative_residual,
            "maximum_relative_residual": self.maximum_relative_residual,
            "median_cosine_alignment": self.median_cosine_alignment,
            "minimum_cosine_alignment": self.minimum_cosine_alignment,
            "spatial_hypothesis_authoritative": self.spatial_hypothesis_authoritative,
            "messages": list(self.messages),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ForceDensityAgreementCertificate":
        if payload.get("schema") != FORCE_DENSITY_CERTIFICATE_SCHEMA:
            raise PilotAuditInputError("Unsupported force-density certificate schema.")
        return cls(
            status=ForceDensityAgreementStatus(payload["status"]),
            sample_catalog_signature=str(payload["sample_catalog_signature"]),
            density_estimate_signature=str(payload["density_estimate_signature"]),
            attractor_catalog_signature=str(payload["attractor_catalog_signature"]),
            force_refinement_signature=str(payload["force_refinement_signature"]),
            joint_force_sample_count=int(payload["joint_force_sample_count"]),
            pmf_force_sample_count=int(payload["pmf_force_sample_count"]),
            density_supported_node_count=int(payload["density_supported_node_count"]),
            force_supported_node_count=int(payload["force_supported_node_count"]),
            force_supported_node_fraction=float(payload["force_supported_node_fraction"]),
            refinement_status_counts=dict(payload["refinement_status_counts"]),
            resolved_refinement_fraction=float(payload["resolved_refinement_fraction"]),
            residual_count=int(payload["residual_count"]),
            median_residual_norm=payload.get("median_residual_norm"),
            maximum_residual_norm=payload.get("maximum_residual_norm"),
            median_relative_residual=payload.get("median_relative_residual"),
            maximum_relative_residual=payload.get("maximum_relative_residual"),
            median_cosine_alignment=payload.get("median_cosine_alignment"),
            minimum_cosine_alignment=payload.get("minimum_cosine_alignment"),
            spatial_hypothesis_authoritative=bool(payload["spatial_hypothesis_authoritative"]),
            messages=tuple(payload.get("messages", ())),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class TransitionPathPreparationCertificate:
    status: TransitionPathPreparationStatus
    sample_catalog_signature: str
    temporal_assignment_signature: str
    structural_mapping_signature: str
    validated_frozen_catalog_signature: str | None
    final_segmentation_signature: str | None
    transition_path_catalog_signature: str | None
    provisional_passage_count: int
    provisional_outcome_counts: Mapping[str, int]
    provisional_jump_count: int
    final_passage_count: int
    observed_event_count: int
    observed_connection_count: int
    path_ensemble_count: int
    spatial_hypothesis_authoritative: bool
    messages: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        status = TransitionPathPreparationStatus(self.status)
        counts = MappingProxyType({str(k): int(v) for k, v in sorted(self.provisional_outcome_counts.items())})
        counters = {
            "provisional_passage_count": int(self.provisional_passage_count),
            "provisional_jump_count": int(self.provisional_jump_count),
            "final_passage_count": int(self.final_passage_count),
            "observed_event_count": int(self.observed_event_count),
            "observed_connection_count": int(self.observed_connection_count),
            "path_ensemble_count": int(self.path_ensemble_count),
        }
        if any(v < 0 for v in counters.values()) or any(v < 0 for v in counts.values()):
            raise PilotAuditInputError("Transition-path counters must be nonnegative.")
        messages = tuple(str(v) for v in self.messages)
        payload = {
            "schema": TRANSITION_PATH_PREPARATION_SCHEMA,
            "status": status.value,
            "sample_catalog_signature": self.sample_catalog_signature,
            "temporal_assignment_signature": self.temporal_assignment_signature,
            "structural_mapping_signature": self.structural_mapping_signature,
            "validated_frozen_catalog_signature": self.validated_frozen_catalog_signature,
            "final_segmentation_signature": self.final_segmentation_signature,
            "transition_path_catalog_signature": self.transition_path_catalog_signature,
            **counters,
            "provisional_outcome_counts": dict(counts),
            "spatial_hypothesis_authoritative": bool(self.spatial_hypothesis_authoritative),
            "messages": list(messages),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Transition-path preparation signature is inconsistent.")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "provisional_outcome_counts", counts)
        for name, value in counters.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "spatial_hypothesis_authoritative", bool(self.spatial_hypothesis_authoritative))
        object.__setattr__(self, "messages", messages)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TRANSITION_PATH_PREPARATION_SCHEMA,
            "status": self.status.value,
            "sample_catalog_signature": self.sample_catalog_signature,
            "temporal_assignment_signature": self.temporal_assignment_signature,
            "structural_mapping_signature": self.structural_mapping_signature,
            "validated_frozen_catalog_signature": self.validated_frozen_catalog_signature,
            "final_segmentation_signature": self.final_segmentation_signature,
            "transition_path_catalog_signature": self.transition_path_catalog_signature,
            "provisional_passage_count": self.provisional_passage_count,
            "provisional_outcome_counts": dict(self.provisional_outcome_counts),
            "provisional_jump_count": self.provisional_jump_count,
            "final_passage_count": self.final_passage_count,
            "observed_event_count": self.observed_event_count,
            "observed_connection_count": self.observed_connection_count,
            "path_ensemble_count": self.path_ensemble_count,
            "spatial_hypothesis_authoritative": self.spatial_hypothesis_authoritative,
            "messages": list(self.messages),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransitionPathPreparationCertificate":
        if payload.get("schema") != TRANSITION_PATH_PREPARATION_SCHEMA:
            raise PilotAuditInputError("Unsupported transition-path preparation schema.")
        return cls(
            status=TransitionPathPreparationStatus(payload["status"]),
            sample_catalog_signature=str(payload["sample_catalog_signature"]),
            temporal_assignment_signature=str(payload["temporal_assignment_signature"]),
            structural_mapping_signature=str(payload["structural_mapping_signature"]),
            validated_frozen_catalog_signature=payload.get("validated_frozen_catalog_signature"),
            final_segmentation_signature=payload.get("final_segmentation_signature"),
            transition_path_catalog_signature=payload.get("transition_path_catalog_signature"),
            provisional_passage_count=int(payload["provisional_passage_count"]),
            provisional_outcome_counts=dict(payload["provisional_outcome_counts"]),
            provisional_jump_count=int(payload["provisional_jump_count"]),
            final_passage_count=int(payload["final_passage_count"]),
            observed_event_count=int(payload["observed_event_count"]),
            observed_connection_count=int(payload["observed_connection_count"]),
            path_ensemble_count=int(payload["path_ensemble_count"]),
            spatial_hypothesis_authoritative=bool(payload["spatial_hypothesis_authoritative"]),
            messages=tuple(payload.get("messages", ())),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class NaLta300KForcePathPilot:
    report: NaLta300KPilotReport
    s3_pilot: NaLta300KStructuralTemporalPilot
    force_refinement: ForceRefinementCatalog
    force_density_agreement: ForceDensityAgreementCertificate
    transition_path_preparation: TransitionPathPreparationCertificate
    final_segmentation: FinalHystereticSegmentationCatalog | None
    transition_paths: ObservedTransitionPathCatalog | None
    wall_seconds: float

    def __post_init__(self) -> None:
        central_index = self.s3_pilot.s2_pilot.options.bandwidth_sigmas_angstrom.index(
            self.s3_pilot.s2_pilot.options.central_bandwidth_sigma_angstrom
        )
        central = self.s3_pilot.s2_pilot.lineage_catalogs[central_index]
        if self.force_refinement.attractor_catalog_signature != central.signature:
            raise PilotAuditInputError("S4 force refinement is not bound to the central S2 attractor catalog.")
        if self.force_density_agreement.force_refinement_signature != self.force_refinement.signature:
            raise PilotAuditInputError("S4 force-density certificate is not bound to its E3 result.")
        if self.transition_path_preparation.temporal_assignment_signature != self.s3_pilot.temporal_assignment.signature:
            raise PilotAuditInputError("S4 path preparation is not bound to the S3 temporal assignment.")


def _spatial_authoritative(s3: NaLta300KStructuralTemporalPilot) -> bool:
    return (
        s3.s2_pilot.scale_consensus.status.value == "resolved"
        and s3.s2_pilot.grid_refinement.certificate.status.value == "stable"
    )


def _force_density_certificate(
    s3: NaLta300KStructuralTemporalPilot,
    force: ForceRefinementCatalog,
    options: NaLta300KForcePathOptions,
) -> ForceDensityAgreementCertificate:
    samples = s3.s2_pilot.s1_pilot.pilot_samples
    central_index = s3.s2_pilot.options.bandwidth_sigmas_angstrom.index(
        s3.s2_pilot.options.central_bandwidth_sigma_angstrom
    )
    density = s3.s2_pilot.density_ladder.estimates[central_index]
    attractors = s3.s2_pilot.lineage_catalogs[central_index]
    joint_count = int(samples.sample_indices_for("joint").size)
    pmf_count = int(samples.sample_indices_for("pmf_force").size)
    density_supported = int(np.count_nonzero(density.realization.support_mask_dense()))
    field = force.mean_force_field
    force_supported = 0 if field is None else int(np.count_nonzero(field.support_mask))
    force_fraction = force_supported / max(1, density_supported)
    status_counts = Counter(item.evidence_status.value for item in force.refinements)
    resolved_count = sum(item.evidence_status is ForceEvidenceStatus.RESOLVED for item in force.refinements)
    resolved_fraction = resolved_count / max(1, len(force.refinements))
    residuals = np.asarray(
        [item.density_force_residual_norm for item in force.refinements if item.density_force_residual_norm is not None],
        dtype=float,
    )
    relative: list[float] = []
    cosine: list[float] = []
    if field is not None and samples.pmf_temperature.temperature_kelvin is not None:
        kbt = options.force_options.boltzmann_constant * samples.pmf_temperature.temperature_kelvin
        mean = field.conditional_force_covector.reshape(-1, 3)
        support = field.support_mask.reshape(-1)
        score = density.realization.density_score_covector_dense().reshape(-1, 3)
        for item in attractors.attractors:
            node = int(item.representative_node_index)
            if not support[node]:
                continue
            a = mean[node]
            b = kbt * score[node]
            scale = max(float(np.linalg.norm(a)), float(np.linalg.norm(b)), options.residual_scale_floor)
            relative.append(float(np.linalg.norm(a - b)) / scale)
            denom = float(np.linalg.norm(a) * np.linalg.norm(b))
            if denom > options.residual_scale_floor**2:
                cosine.append(float(np.dot(a, b) / denom))
    authoritative = _spatial_authoritative(s3)
    messages: list[str] = []
    if samples.transformed_forces is None or joint_count == 0:
        status = ForceDensityAgreementStatus.FORCE_UNAVAILABLE
        messages.append("No source-compatible transformed force samples are available.")
    elif pmf_count == 0:
        status = ForceDensityAgreementStatus.PMF_PROVENANCE_REJECTED
        messages.append(
            "Physical forces are available, but equilibrium, stationarity, and declared constant-temperature PMF provenance are not jointly satisfied."
        )
    elif force_fraction < options.minimum_force_supported_node_fraction or resolved_fraction < options.minimum_resolved_refinement_fraction or not relative:
        status = ForceDensityAgreementStatus.INSUFFICIENT_SUPPORT
        messages.append("Matched force support or resolved local refinements are below the declared S4 threshold.")
    elif float(np.median(relative)) > options.maximum_median_relative_residual:
        status = ForceDensityAgreementStatus.DISAGREEMENT
        messages.append("The median matched-force versus density-score residual exceeds the declared threshold.")
    elif options.require_authoritative_spatial_hypothesis and not authoritative:
        status = ForceDensityAgreementStatus.SPATIAL_HYPOTHESIS_UNRESOLVED
        messages.append("Force-density diagnostics pass locally, but the S2 spatial scale/topology is not authoritative.")
    else:
        status = ForceDensityAgreementStatus.RESOLVED
    return ForceDensityAgreementCertificate(
        status=status,
        sample_catalog_signature=samples.signature,
        density_estimate_signature=density.signature,
        attractor_catalog_signature=attractors.signature,
        force_refinement_signature=force.signature,
        joint_force_sample_count=joint_count,
        pmf_force_sample_count=pmf_count,
        density_supported_node_count=density_supported,
        force_supported_node_count=force_supported,
        force_supported_node_fraction=force_fraction,
        refinement_status_counts=dict(status_counts),
        resolved_refinement_fraction=resolved_fraction,
        residual_count=int(residuals.size),
        median_residual_norm=None if residuals.size == 0 else float(np.median(residuals)),
        maximum_residual_norm=None if residuals.size == 0 else float(np.max(residuals)),
        median_relative_residual=None if not relative else float(np.median(relative)),
        maximum_relative_residual=None if not relative else float(np.max(relative)),
        median_cosine_alignment=None if not cosine else float(np.median(cosine)),
        minimum_cosine_alignment=None if not cosine else float(np.min(cosine)),
        spatial_hypothesis_authoritative=authoritative,
        messages=tuple(messages),
    )


def _path_preparation(
    s3: NaLta300KStructuralTemporalPilot,
    options: NaLta300KForcePathOptions,
    validated_frozen_catalog: Any | None,
    segmentation_resources: FinalSegmentationResourcePolicy | None,
    transition_resources: TransitionPathResourcePolicy | None,
) -> tuple[TransitionPathPreparationCertificate, FinalHystereticSegmentationCatalog | None, ObservedTransitionPathCatalog | None]:
    temporal = s3.temporal_assignment
    sample_catalog = s3.s2_pilot.s1_pilot.source_bootstrap.na_samples
    counts = Counter(item.outcome.value for item in temporal.passages)
    jumps = int(counts.get(PassageOutcome.JUMP.value, 0))
    authoritative = _spatial_authoritative(s3)
    validated_signature = None if validated_frozen_catalog is None else getattr(validated_frozen_catalog, "signature", None)
    final: FinalHystereticSegmentationCatalog | None = None
    paths: ObservedTransitionPathCatalog | None = None
    messages: list[str] = []
    if options.require_authoritative_spatial_hypothesis and not authoritative:
        status = TransitionPathPreparationStatus.SPATIAL_HYPOTHESIS_UNRESOLVED
        messages.append("S2 bandwidth/grid saddle topology is unresolved; Stage 11E6 final segmentation is not executed.")
    elif validated_frozen_catalog is None:
        status = TransitionPathPreparationStatus.MISSING_VALIDATED_STATES
        messages.append("A source-compatible Stage 11E5 validated frozen-state catalog is required before final segmentation.")
    else:
        final = prepare_final_hysteretic_segmentation(
            sample_catalog,
            validated_frozen_catalog,
            temporal,
            options=options.final_segmentation_options,
            resources=segmentation_resources,
        )
        paths = prepare_observed_transition_paths(
            sample_catalog,
            final,
            options=options.transition_path_options,
            resources=transition_resources,
        )
        connections = int(sum(item.successful_connection for item in paths.events))
        if connections == 0:
            status = TransitionPathPreparationStatus.EXECUTED_NO_CONNECTIONS
            messages.append("Final segmentation and path reconstruction executed, but no successful observed connection is present.")
        else:
            status = TransitionPathPreparationStatus.READY
    if validated_frozen_catalog is None and not (options.require_authoritative_spatial_hypothesis and not authoritative) and jumps == 0:
        status = TransitionPathPreparationStatus.NO_PROVISIONAL_JUMPS
        messages.append("No provisional inter-attractor jump is present in the represented trajectory.")
    return (
        TransitionPathPreparationCertificate(
            status=status,
            sample_catalog_signature=sample_catalog.signature,
            temporal_assignment_signature=temporal.signature,
            structural_mapping_signature=s3.structural_mapping.signature,
            validated_frozen_catalog_signature=validated_signature,
            final_segmentation_signature=None if final is None else final.signature,
            transition_path_catalog_signature=None if paths is None else paths.signature,
            provisional_passage_count=len(temporal.passages),
            provisional_outcome_counts=dict(counts),
            provisional_jump_count=jumps,
            final_passage_count=0 if final is None else len(final.passages),
            observed_event_count=0 if paths is None else len(paths.events),
            observed_connection_count=0 if paths is None else int(sum(v.successful_connection for v in paths.events)),
            path_ensemble_count=0 if paths is None else len(paths.ensembles),
            spatial_hypothesis_authoritative=authoritative,
            messages=tuple(messages),
        ),
        final,
        paths,
    )


def prepare_na_lta_300k_force_path_pilot(
    collection: AtomisticFrameCollection,
    trajectory_path: str | Path,
    *,
    options: NaLta300KForcePathOptions | None = None,
    s3_options: NaLta300KStructuralTemporalOptions | None = None,
    s2_options: NaLta300KRefinementLineageOptions | None = None,
    s1_options: NaLta300KDensityAttractorPilotOptions | None = None,
    density_resources: SpeciesDensityResourcePolicy | None = None,
    attractor_options: DensityAttractorOptions | None = None,
    attractor_resources: DensityAttractorResourcePolicy | None = None,
    temporal_resources: TemporalAssignmentResourcePolicy | None = None,
    force_resources: LocalMeanForceResourcePolicy | None = None,
    validated_frozen_catalog: Any | None = None,
    segmentation_resources: FinalSegmentationResourcePolicy | None = None,
    transition_resources: TransitionPathResourcePolicy | None = None,
    audit_policy: PilotAuditResourcePolicy | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> NaLta300KForcePathPilot:
    """Execute Stage 11E8a-S4 without weakening E3, E6, or E6b gates."""
    active = options or NaLta300KForcePathOptions()
    started = perf_counter()
    s3 = prepare_na_lta_300k_structural_temporal_pilot(
        collection,
        trajectory_path,
        options=s3_options,
        s2_options=s2_options,
        s1_options=s1_options,
        density_resources=density_resources,
        attractor_options=attractor_options,
        attractor_resources=attractor_resources,
        temporal_resources=temporal_resources,
        audit_policy=audit_policy,
        metadata={"requested_by_stage": PILOT_FORCE_PATH_STAGE},
    )
    central_index = s3.s2_pilot.options.bandwidth_sigmas_angstrom.index(
        s3.s2_pilot.options.central_bandwidth_sigma_angstrom
    )
    density = s3.s2_pilot.density_ladder.estimates[central_index]
    attractors = s3.s2_pilot.lineage_catalogs[central_index]
    force = prepare_force_refinement_catalog(
        s3.s2_pilot.s1_pilot.pilot_samples,
        density,
        attractors,
        options=active.force_options,
        resources=force_resources,
    )
    agreement = _force_density_certificate(s3, force, active)
    path_preparation, final, paths = _path_preparation(
        s3, active, validated_frozen_catalog, segmentation_resources, transition_resources
    )
    elapsed = perf_counter() - started
    source_digest = s3.s2_pilot.s1_pilot.source_bootstrap.trajectory_sha256

    if agreement.status is ForceDensityAgreementStatus.RESOLVED:
        force_evidence_status = PilotEvidenceStatus.RESOLVED
    elif agreement.status in {
        ForceDensityAgreementStatus.PMF_PROVENANCE_REJECTED,
        ForceDensityAgreementStatus.FORCE_UNAVAILABLE,
    }:
        force_evidence_status = PilotEvidenceStatus.BLOCKED
    else:
        force_evidence_status = PilotEvidenceStatus.PARTIAL

    if path_preparation.status is TransitionPathPreparationStatus.READY:
        path_evidence_status = PilotEvidenceStatus.RESOLVED
    elif path_preparation.status is TransitionPathPreparationStatus.EXECUTED_NO_CONNECTIONS:
        path_evidence_status = PilotEvidenceStatus.PARTIAL
    else:
        path_evidence_status = PilotEvidenceStatus.BLOCKED

    replacements = {
        "force_density_agreement": PilotEvidenceRecord(
            "force_density_agreement",
            "11E3/S4",
            force_evidence_status,
            source_digest=source_digest,
            accepted_fraction=agreement.resolved_refinement_fraction,
            unresolved_fraction=1.0 - agreement.resolved_refinement_fraction,
            metrics={
                "certificate_signature": agreement.signature,
                "force_refinement_signature": force.signature,
                "status": agreement.status.value,
                "joint_force_sample_count": agreement.joint_force_sample_count,
                "pmf_force_sample_count": agreement.pmf_force_sample_count,
                "force_supported_node_fraction": agreement.force_supported_node_fraction,
                "refinement_status_counts": dict(agreement.refinement_status_counts),
                "median_relative_residual": agreement.median_relative_residual,
                "spatial_hypothesis_authoritative": agreement.spatial_hypothesis_authoritative,
            },
            messages=agreement.messages,
        ),
        "transition_paths": PilotEvidenceRecord(
            "transition_paths",
            "11E6/11E6b/S4",
            path_evidence_status,
            source_digest=source_digest,
            accepted_fraction=(
                1.0 if path_preparation.status is TransitionPathPreparationStatus.READY else 0.0
            ),
            unresolved_fraction=(
                0.0 if path_preparation.status is TransitionPathPreparationStatus.READY else 1.0
            ),
            metrics={
                "preparation_signature": path_preparation.signature,
                "status": path_preparation.status.value,
                "provisional_passage_count": path_preparation.provisional_passage_count,
                "provisional_outcome_counts": dict(path_preparation.provisional_outcome_counts),
                "provisional_jump_count": path_preparation.provisional_jump_count,
                "final_passage_count": path_preparation.final_passage_count,
                "observed_event_count": path_preparation.observed_event_count,
                "observed_connection_count": path_preparation.observed_connection_count,
                "path_ensemble_count": path_preparation.path_ensemble_count,
                "final_segmentation_executed": final is not None,
                "transition_path_reconstruction_executed": paths is not None,
                "spatial_hypothesis_authoritative": path_preparation.spatial_hypothesis_authoritative,
            },
            messages=path_preparation.messages,
        ),
    }
    resident_bytes = _array_payload_bytes(collection, s3, force, agreement, path_preparation, final, paths)
    replacements["cost"] = PilotEvidenceRecord(
        "cost", PILOT_FORCE_PATH_STAGE, PilotEvidenceStatus.RESOLVED,
        source_digest=source_digest, accepted_fraction=1.0, unresolved_fraction=0.0,
        metrics={"s4_total_wall_seconds": elapsed, "force_refinement_count": len(force.refinements)},
    )
    replacements["memory"] = PilotEvidenceRecord(
        "memory", PILOT_FORCE_PATH_STAGE, PilotEvidenceStatus.RESOLVED,
        source_digest=source_digest, accepted_fraction=1.0, unresolved_fraction=0.0,
        metrics={"resident_numerical_payload_bytes": resident_bytes,
                 "measurement_kind": "deduplicated recursive ndarray payload estimate"},
    )
    evidence = _replace_evidence(s3.report.evidence, replacements)
    report = prepare_na_lta_300k_pilot_report(
        s3.report.dataset,
        evidence,
        artifacts=s3.report.artifacts,
        resources=PilotResourceUsage(
            wall_seconds=elapsed,
            peak_memory_bytes=resident_bytes,
            worker_count=1,
            output_bytes=sum(item.byte_count for item in s3.report.artifacts),
            metadata={"scope": "S0-S4 force-density and path readiness"},
        ),
        outcome=PilotScientificOutcome(
            site_center_count=s3.report.outcome.site_center_count,
            supported_basin_count=s3.report.outcome.supported_basin_count,
            observed_connection_count=path_preparation.observed_connection_count,
            transition_path_ensemble_count=path_preparation.path_ensemble_count,
            undersampled_path_ensemble_count=(
                None if paths is None else sum(item.status.value != "path_ensemble_resolved" for item in paths.ensembles)
            ),
            rate_status=PilotRateStatus.UNIDENTIFIED,
            global_pmf_status=(
                PilotPMFStatus.SUPPORT_LIMITED if agreement.pmf_force_sample_count > 0 else PilotPMFStatus.UNSUPPORTED
            ),
            conclusions=(
                f"S4 force-density status is {agreement.status.value}.",
                f"S4 transition-path preparation status is {path_preparation.status.value}.",
                "No PMF, barrier, representative path, transition rate, or kinetic network is inferred by this boundary.",
            ),
        ),
        metadata={
            **dict(metadata or {}),
            "audit_kind": "real_force_path_pilot",
            "s1_complete": True,
            "s2_complete": True,
            "s3_complete": True,
            "s4_complete": True,
            "options_signature": active.signature,
            "force_density_certificate_signature": agreement.signature,
            "transition_path_preparation_signature": path_preparation.signature,
            "next_execution_boundary": "11E8a closure review before Stage 11E8b",
        },
        policy=audit_policy,
    )
    return NaLta300KForcePathPilot(report, s3, force, agreement, path_preparation, final, paths, elapsed)


__all__ = [
    "PILOT_FORCE_PATH_STAGE", "PILOT_FORCE_PATH_OPTIONS_SCHEMA",
    "FORCE_DENSITY_CERTIFICATE_SCHEMA", "TRANSITION_PATH_PREPARATION_SCHEMA",
    "ForceDensityAgreementStatus", "TransitionPathPreparationStatus",
    "NaLta300KForcePathOptions", "ForceDensityAgreementCertificate",
    "TransitionPathPreparationCertificate", "NaLta300KForcePathPilot",
    "prepare_na_lta_300k_force_path_pilot",
]
