"""Stage-11E8a-S1 framework-registered density and attractor pilot.

The S1 boundary selects and validates the analysis-specific Na-LTA framework
translation gauge, compresses the full represented-time measure into a
deterministic pilot quadrature, executes one E1 density realization and one E2
attractor realization, and extends the fail-closed Stage-11E8a dossier.  The
single-grid/single-bandwidth products are pilot evidence only; they do not
certify topology lineage, temporal states, transition paths, or rates.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

import numpy as np

from ...collection import AtomisticFrameCollection
from ...coordinates.registration import (
    FrameRegistrationPolicy,
    FrameRegistrationResult,
    ReferenceTranslationOptions,
    ReferenceWeighting,
    RegistrationSpatialPolicy,
    TranslationMode,
    prepare_frame_registration,
)
from ..site_samples import (
    FrameworkAlignedIonSampleCatalog,
    PMFTemperatureProvenance,
    SamplingStateProvenance,
    TrajectorySegmentWeighting,
    prepare_framework_aligned_ion_sample_catalog,
    prepare_trajectory_segment_weighting,
)
from .attractors import (
    AttractorGeometry,
    DensityAttractorCatalog,
    DensityAttractorOptions,
    DensityAttractorResourcePolicy,
    prepare_density_attractor_catalog,
)
from ._pilot_common import (
    array_payload_bytes as _array_payload_bytes,
    canonical_json as _canonical_json,
    digest as _digest,
    positive as _positive,
    positive_int as _positive_int,
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
from .pilot_execution import (
    NaLta300KSourceBootstrap,
    prepare_na_lta_300k_source_bootstrap,
)
from .species import (
    GaussianKernelCovariance,
    PeriodicDensityDomain,
    PeriodicSpeciesDensityEstimate,
    SpeciesDensityOptions,
    SpeciesDensityResourcePolicy,
    prepare_periodic_species_density,
)

PILOT_DENSITY_ATTRACTOR_STAGE = "11E8a-S1"
PILOT_DENSITY_ATTRACTOR_OPTIONS_SCHEMA = "mdstats.na-lta-300k-density-attractor-pilot-options.v1"
FRAMEWORK_REGISTRATION_GAUGE_SCHEMA = "mdstats.framework-registration-gauge-validation.v1"










def _grid_shape(value: tuple[int, int, int]) -> tuple[int, int, int]:
    result = tuple(_positive_int(item, "grid_shape") for item in value)
    if len(result) != 3:
        raise PilotAuditInputError("grid_shape must contain three positive integers.")
    return result


@dataclass(frozen=True, slots=True)
class NaLta300KDensityAttractorPilotOptions:
    """Resolved S1 scientific and resource-facing pilot controls."""

    representative_frame_count: int = 60
    grid_shape: tuple[int, int, int] = (16, 16, 16)
    kernel_sigma_angstrom: float = 0.5
    maximum_framework_residual_angstrom: float = 2.0
    maximum_gauge_weighting_difference_angstrom: float = 0.05
    maximum_translation_step_angstrom: float = 0.05
    density_query_batch_size: int = 256
    density_sample_batch_size: int = 128
    relative_image_tolerance: float = 1.0e-10
    maximum_image_radius: int = 2
    signature: str = ""

    def __post_init__(self) -> None:
        values = {
            "representative_frame_count": _positive_int(self.representative_frame_count, "representative_frame_count"),
            "grid_shape": _grid_shape(self.grid_shape),
            "kernel_sigma_angstrom": _positive(self.kernel_sigma_angstrom, "kernel_sigma_angstrom"),
            "maximum_framework_residual_angstrom": _positive(self.maximum_framework_residual_angstrom, "maximum_framework_residual_angstrom"),
            "maximum_gauge_weighting_difference_angstrom": _positive(self.maximum_gauge_weighting_difference_angstrom, "maximum_gauge_weighting_difference_angstrom"),
            "maximum_translation_step_angstrom": _positive(self.maximum_translation_step_angstrom, "maximum_translation_step_angstrom"),
            "density_query_batch_size": _positive_int(self.density_query_batch_size, "density_query_batch_size"),
            "density_sample_batch_size": _positive_int(self.density_sample_batch_size, "density_sample_batch_size"),
            "relative_image_tolerance": _positive(self.relative_image_tolerance, "relative_image_tolerance"),
            "maximum_image_radius": _positive_int(self.maximum_image_radius, "maximum_image_radius"),
        }
        payload = {"schema": PILOT_DENSITY_ATTRACTOR_OPTIONS_SCHEMA, **values}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("S1 pilot-options signature is inconsistent.")
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PILOT_DENSITY_ATTRACTOR_OPTIONS_SCHEMA,
            "representative_frame_count": self.representative_frame_count,
            "grid_shape": list(self.grid_shape),
            "kernel_sigma_angstrom": self.kernel_sigma_angstrom,
            "maximum_framework_residual_angstrom": self.maximum_framework_residual_angstrom,
            "maximum_gauge_weighting_difference_angstrom": self.maximum_gauge_weighting_difference_angstrom,
            "maximum_translation_step_angstrom": self.maximum_translation_step_angstrom,
            "density_query_batch_size": self.density_query_batch_size,
            "density_sample_batch_size": self.density_sample_batch_size,
            "relative_image_tolerance": self.relative_image_tolerance,
            "maximum_image_radius": self.maximum_image_radius,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NaLta300KDensityAttractorPilotOptions":
        if payload.get("schema") != PILOT_DENSITY_ATTRACTOR_OPTIONS_SCHEMA:
            raise PilotAuditInputError("Unsupported S1 pilot-options schema.")
        return cls(
            representative_frame_count=int(payload["representative_frame_count"]),
            grid_shape=tuple(int(v) for v in payload["grid_shape"]),
            kernel_sigma_angstrom=float(payload["kernel_sigma_angstrom"]),
            maximum_framework_residual_angstrom=float(payload["maximum_framework_residual_angstrom"]),
            maximum_gauge_weighting_difference_angstrom=float(payload["maximum_gauge_weighting_difference_angstrom"]),
            maximum_translation_step_angstrom=float(payload["maximum_translation_step_angstrom"]),
            density_query_batch_size=int(payload["density_query_batch_size"]),
            density_sample_batch_size=int(payload["density_sample_batch_size"]),
            relative_image_tolerance=float(payload["relative_image_tolerance"]),
            maximum_image_radius=int(payload["maximum_image_radius"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class FrameworkRegistrationGaugeValidation:
    """Signed scientific validation of the selected CoG framework gauge."""

    selected_registration_signature: str
    comparison_registration_signature: str
    framework_atom_count: int
    selected_weighting: str
    comparison_weighting: str
    solver_method_counts: Mapping[str, int]
    maximum_residual_rms_angstrom: float
    maximum_residual_angstrom: float
    minimum_uniqueness_margin_angstrom: float
    temporal_continuity_available: bool
    maximum_translation_step_angstrom: float
    maximum_lattice_branch_index: int
    maximum_translation_norm_angstrom: float
    maximum_weighting_difference_angstrom: float
    rms_weighting_difference_angstrom: float
    residual_limit_angstrom: float
    weighting_difference_limit_angstrom: float
    translation_step_limit_angstrom: float
    accepted: bool
    signature: str = ""

    def __post_init__(self) -> None:
        if len(self.selected_registration_signature) != 64 or len(self.comparison_registration_signature) != 64:
            raise PilotAuditInputError("Gauge validation requires registration SHA-256 signatures.")
        counts = {str(k): int(v) for k, v in sorted(self.solver_method_counts.items())}
        if not counts or any(v < 0 for v in counts.values()):
            raise PilotAuditInputError("solver_method_counts must be nonempty and nonnegative.")
        payload = {
            "schema": FRAMEWORK_REGISTRATION_GAUGE_SCHEMA,
            "selected_registration_signature": self.selected_registration_signature,
            "comparison_registration_signature": self.comparison_registration_signature,
            "framework_atom_count": int(self.framework_atom_count),
            "selected_weighting": str(self.selected_weighting),
            "comparison_weighting": str(self.comparison_weighting),
            "solver_method_counts": counts,
            "maximum_residual_rms_angstrom": float(self.maximum_residual_rms_angstrom),
            "maximum_residual_angstrom": float(self.maximum_residual_angstrom),
            "minimum_uniqueness_margin_angstrom": float(self.minimum_uniqueness_margin_angstrom),
            "temporal_continuity_available": bool(self.temporal_continuity_available),
            "maximum_translation_step_angstrom": float(self.maximum_translation_step_angstrom),
            "maximum_lattice_branch_index": int(self.maximum_lattice_branch_index),
            "maximum_translation_norm_angstrom": float(self.maximum_translation_norm_angstrom),
            "maximum_weighting_difference_angstrom": float(self.maximum_weighting_difference_angstrom),
            "rms_weighting_difference_angstrom": float(self.rms_weighting_difference_angstrom),
            "residual_limit_angstrom": float(self.residual_limit_angstrom),
            "weighting_difference_limit_angstrom": float(self.weighting_difference_limit_angstrom),
            "translation_step_limit_angstrom": float(self.translation_step_limit_angstrom),
            "accepted": bool(self.accepted),
        }
        for name, value in payload.items():
            if name in {"schema", "selected_registration_signature", "comparison_registration_signature", "selected_weighting", "comparison_weighting", "solver_method_counts", "temporal_continuity_available", "accepted", "framework_atom_count", "maximum_lattice_branch_index"}:
                continue
            if not np.isfinite(float(value)) or float(value) < 0.0:
                raise PilotAuditInputError(f"{name} must be finite and nonnegative.")
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Gauge-validation signature is inconsistent.")
        object.__setattr__(self, "solver_method_counts", counts)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        result = {field.name: getattr(self, field.name) for field in fields(self)}
        result["schema"] = FRAMEWORK_REGISTRATION_GAUGE_SCHEMA
        result["solver_method_counts"] = dict(self.solver_method_counts)
        return result

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkRegistrationGaugeValidation":
        if payload.get("schema") != FRAMEWORK_REGISTRATION_GAUGE_SCHEMA:
            raise PilotAuditInputError("Unsupported framework-gauge-validation schema.")
        return cls(**{k: v for k, v in payload.items() if k != "schema"})


@dataclass(frozen=True, slots=True)
class NaLta300KDensityAttractorPilot:
    """Runtime products from the real S1 density/attractor pilot."""

    report: NaLta300KPilotReport
    source_bootstrap: NaLta300KSourceBootstrap
    gauge_validation: FrameworkRegistrationGaugeValidation
    pilot_samples: FrameworkAlignedIonSampleCatalog
    density: PeriodicSpeciesDensityEstimate
    attractors: DensityAttractorCatalog
    representative_frame_indices: tuple[int, ...]
    wall_seconds: float

    def __post_init__(self) -> None:
        if self.report.dataset.registration_signature != self.source_bootstrap.registration.signature:
            raise PilotAuditInputError("S1 report and selected registration disagree.")
        if self.pilot_samples.registration_signature != self.source_bootstrap.registration.signature:
            raise PilotAuditInputError("S1 samples are not bound to the selected registration.")
        if self.density.catalog_signature != self.pilot_samples.signature:
            raise PilotAuditInputError("S1 density is not bound to the pilot sample catalog.")
        if self.attractors.density_estimate_signature != self.density.signature:
            raise PilotAuditInputError("S1 attractor catalog is not bound to the density estimate.")


def _registration_policy(
    framework_indices: tuple[int, ...],
    na_indices: tuple[int, ...],
    *,
    weighting: ReferenceWeighting,
    maximum_residual: float,
) -> FrameRegistrationPolicy:
    return FrameRegistrationPolicy(
        spatial_policy=RegistrationSpatialPolicy.TRANSLATION_REGISTERED,
        translation_mode=TranslationMode.MATCHED_REFERENCE,
        reference_atom_indices=framework_indices,
        reference_frame_index=0,
        reference_weighting=weighting,
        force_target_atom_indices=na_indices,
        require_fixed_registered_cell=True,
        translation_options=ReferenceTranslationOptions(maximum_residual=maximum_residual),
    )


def _gauge_validation(
    selected: FrameRegistrationResult,
    comparison: FrameRegistrationResult,
    options: NaLta300KDensityAttractorPilotOptions,
) -> FrameworkRegistrationGaugeValidation:
    gauge = selected.reference_translation_gauge
    comparison_gauge = comparison.reference_translation_gauge
    branch = selected.translation_branch_lift
    if gauge is None or comparison_gauge is None or branch is None:
        raise PilotAuditInputError("S1 requires matched-reference gauges and a trajectory branch lift.")
    methods: dict[str, int] = {}
    for frame in gauge.frames:
        methods[frame.solver_method] = methods.get(frame.solver_method, 0) + 1
    margins = [frame.uniqueness_radius_margin for frame in gauge.frames if frame.uniqueness_radius_margin is not None]
    differences = np.linalg.norm(
        gauge.torus_translations - comparison_gauge.torus_translations, axis=1
    )
    selected_translation = np.asarray(branch.lifted_translations, dtype=np.float64)
    max_branch = int(np.max(np.abs(branch.lattice_branches)))
    accepted = bool(
        all(frame.converged and not frame.ambiguous for frame in gauge.frames)
        and len(margins) == len(gauge.frames)
        and min(margins) > 0.0
        and max(frame.residual_maximum for frame in gauge.frames) <= options.maximum_framework_residual_angstrom
        and float(np.max(differences)) <= options.maximum_gauge_weighting_difference_angstrom
        and float(np.max(branch.continuity_residuals)) <= options.maximum_translation_step_angstrom
        and branch.temporal_continuity_available
    )
    result = FrameworkRegistrationGaugeValidation(
        selected_registration_signature=selected.signature,
        comparison_registration_signature=comparison.signature,
        framework_atom_count=len(gauge.reference_atom_indices),
        selected_weighting=gauge.weighting.value,
        comparison_weighting=comparison_gauge.weighting.value,
        solver_method_counts=methods,
        maximum_residual_rms_angstrom=max(frame.residual_rms for frame in gauge.frames),
        maximum_residual_angstrom=max(frame.residual_maximum for frame in gauge.frames),
        minimum_uniqueness_margin_angstrom=min(margins) if margins else 0.0,
        temporal_continuity_available=branch.temporal_continuity_available,
        maximum_translation_step_angstrom=float(np.max(branch.continuity_residuals)),
        maximum_lattice_branch_index=max_branch,
        maximum_translation_norm_angstrom=float(np.max(np.linalg.norm(selected_translation, axis=1))),
        maximum_weighting_difference_angstrom=float(np.max(differences)),
        rms_weighting_difference_angstrom=float(np.sqrt(np.mean(differences * differences))),
        residual_limit_angstrom=options.maximum_framework_residual_angstrom,
        weighting_difference_limit_angstrom=options.maximum_gauge_weighting_difference_angstrom,
        translation_step_limit_angstrom=options.maximum_translation_step_angstrom,
        accepted=accepted,
    )
    if not result.accepted:
        raise PilotAuditInputError(
            "Stage 11E8a-S1 framework-registration gauge failed its declared acceptance limits."
        )
    return result


def _representative_weighting(
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
    count: int,
) -> tuple[TrajectorySegmentWeighting, tuple[int, ...]]:
    base = prepare_trajectory_segment_weighting(collection, registration=registration)
    positive = np.flatnonzero(base.temporal_mask)
    if positive.size == 0:
        raise PilotAuditInputError("S1 has no positive represented-time frames.")
    n_bins = min(int(count), int(positive.size))
    weights = np.zeros(collection.n_frames, dtype=np.float64)
    representatives: list[int] = []
    for chunk in np.array_split(positive, n_bins):
        local_weights = base.represented_time_weights[chunk]
        if not np.any(local_weights > 0.0):
            continue
        target = float(np.average(chunk.astype(np.float64), weights=local_weights))
        representative = int(chunk[np.argmin(np.abs(chunk.astype(np.float64) - target))])
        weights[representative] = float(np.sum(local_weights))
        representatives.append(representative)
    pilot = prepare_trajectory_segment_weighting(
        collection,
        registration=registration,
        explicit_frame_weights=weights,
        explicit_weight_units=base.weight_units,
    )
    if not np.isclose(
        pilot.included_represented_time,
        base.included_represented_time,
        rtol=0.0,
        atol=max(1.0e-14, 1.0e-12 * base.included_represented_time),
    ):
        raise PilotAuditInputError("S1 quadrature did not preserve represented time.")
    return pilot, tuple(representatives)






def prepare_na_lta_300k_density_attractor_pilot(
    collection: AtomisticFrameCollection,
    trajectory_path: str | Path,
    *,
    options: NaLta300KDensityAttractorPilotOptions | None = None,
    density_options: SpeciesDensityOptions | None = None,
    density_resources: SpeciesDensityResourcePolicy | None = None,
    attractor_options: DensityAttractorOptions | None = None,
    attractor_resources: DensityAttractorResourcePolicy | None = None,
    audit_policy: PilotAuditResourcePolicy | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> NaLta300KDensityAttractorPilot:
    """Execute the real Stage-11E8a-S1 framework/density/attractor pilot."""

    active = options or NaLta300KDensityAttractorPilotOptions()
    framework_indices = tuple(int(v) for v in np.flatnonzero(collection.atomic_numbers != 11))
    na_indices = tuple(int(v) for v in np.flatnonzero(collection.atomic_numbers == 11))
    if len(framework_indices) != 144 or len(na_indices) != 24:
        raise PilotAuditInputError("S1 requires 144 framework atoms and 24 Na atoms.")

    started = perf_counter()
    selected_policy = _registration_policy(
        framework_indices,
        na_indices,
        weighting=ReferenceWeighting.CENTER_OF_GEOMETRY,
        maximum_residual=active.maximum_framework_residual_angstrom,
    )
    # Bind raw bytes and S0 products directly to the selected S1 gauge.
    source = prepare_na_lta_300k_source_bootstrap(
        collection,
        trajectory_path,
        registration_policy=selected_policy,
        audit_policy=audit_policy,
        metadata={"requested_by_stage": PILOT_DENSITY_ATTRACTOR_STAGE},
    )
    comparison = prepare_frame_registration(
        collection,
        policy=_registration_policy(
            framework_indices,
            na_indices,
            weighting=ReferenceWeighting.CENTER_OF_MASS,
            maximum_residual=active.maximum_framework_residual_angstrom,
        ),
    )
    validation = _gauge_validation(source.registration, comparison, active)

    temporal_weighting, representatives = _representative_weighting(
        collection, source.registration, active.representative_frame_count
    )
    sampling_state = SamplingStateProvenance(
        declaration_source="Stage 11E8a-S1 density/attractor pilot",
        notes=(
            "Represented time is preserved by deterministic frame quadrature.",
            "Equilibrium and stationarity remain unresolved at this boundary.",
        ),
    )
    pilot_samples = prepare_framework_aligned_ion_sample_catalog(
        collection,
        source.registration,
        species_atomic_number=11,
        species_label="Na",
        temporal_weighting=temporal_weighting,
        sampling_state=sampling_state,
        pmf_temperature=PMFTemperatureProvenance.from_collection(collection),
        metadata={
            "pilot_stage": PILOT_DENSITY_ATTRACTOR_STAGE,
            "quadrature_kind": "contiguous_represented_time_bins",
            "representative_frame_indices": representatives,
        },
    )

    domain = PeriodicDensityDomain(
        cell=source.registration.registered_cells[0],
        registration_signature=source.registration.signature,
        source_cell_variation_max=float(np.max(np.abs(
            source.registration.registered_cells - source.registration.registered_cells[0]
        ))),
        metadata={"pilot_stage": PILOT_DENSITY_ATTRACTOR_STAGE},
    )
    kernel = GaussianKernelCovariance.isotropic_cartesian(
        active.kernel_sigma_angstrom, domain, label="stage11e8a-s1-pilot"
    )
    resolved_density_options = density_options or SpeciesDensityOptions(
        grid_shape=active.grid_shape,
        query_batch_size=active.density_query_batch_size,
        sample_batch_size=active.density_sample_batch_size,
        relative_image_tolerance=active.relative_image_tolerance,
        max_image_radius=active.maximum_image_radius,
        minimum_effective_samples=1.0,
        metadata={"pilot_stage": PILOT_DENSITY_ATTRACTOR_STAGE},
    )
    resolved_density_resources = density_resources or SpeciesDensityResourcePolicy(
        max_image_terms=250_000_000
    )
    density = prepare_periodic_species_density(
        pilot_samples,
        domain,
        kernel,
        options=resolved_density_options,
        resources=resolved_density_resources,
    )
    attractors = prepare_density_attractor_catalog(
        density,
        options=attractor_options,
        resources=attractor_resources,
    )
    elapsed = perf_counter() - started

    geometry_counts: dict[str, int] = {}
    for attractor in attractors.attractors:
        geometry = AttractorGeometry(attractor.geometry).value
        geometry_counts[geometry] = geometry_counts.get(geometry, 0) + 1
    isolated_count = geometry_counts.get(AttractorGeometry.ISOLATED_MODE.value, 0)
    resolved_core_count = sum(bool(core.resolved) for core in attractors.provisional_cores)
    support_fraction = density.error_certificate.support_node_count / density.error_certificate.total_node_count
    representative_fraction = len(representatives) / collection.n_frames
    unresolved_mode_fraction = (
        1.0 - isolated_count / len(attractors.attractors)
        if attractors.attractors else 1.0
    )
    resident_bytes = _array_payload_bytes(
        collection, source.registration, comparison, pilot_samples, density, attractors
    )
    source_digest = source.trajectory_sha256

    replacements = {
        "registration": PilotEvidenceRecord(
            "registration", PILOT_DENSITY_ATTRACTOR_STAGE, PilotEvidenceStatus.RESOLVED,
            source_digest=source_digest, accepted_fraction=1.0, unresolved_fraction=0.0,
            metrics={**validation.to_dict(), "gauge_validation_signature": validation.signature},
            artifact_ids=("raw_trajectory",),
        ),
        "kernel_metric_periodization": PilotEvidenceRecord(
            "kernel_metric_periodization", "11E1/S1", PilotEvidenceStatus.RESOLVED,
            source_digest=source_digest, accepted_fraction=1.0, unresolved_fraction=0.0,
            metrics={
                "domain_signature": domain.signature,
                "kernel_covariance_signature": kernel.signature,
                "analysis_metric_signature": density.analysis_metric.signature,
                "image_truncation_signature": density.image_truncation.signature,
                "image_radius": density.image_truncation.radius,
                "image_count": density.image_truncation.image_count,
                "relative_peak_density_bound": density.image_truncation.relative_peak_density_bound,
                "grid_shape": density.realization.grid_shape,
                "kernel_sigma_angstrom": active.kernel_sigma_angstrom,
            },
        ),
        "field_certificate": PilotEvidenceRecord(
            "field_certificate", "11E1/S1", PilotEvidenceStatus.PARTIAL,
            source_digest=source_digest,
            accepted_fraction=representative_fraction,
            unresolved_fraction=1.0 - representative_fraction,
            metrics={
                "density_signature": density.signature,
                "pilot_sample_catalog_signature": pilot_samples.signature,
                "representative_frame_count": len(representatives),
                "source_frame_count": collection.n_frames,
                "positive_weight_sample_count": len(representatives) * len(na_indices),
                "represented_time_fraction": 1.0,
                "observation_measure": density.integrals.observation_measure,
                "observation_measure_units": density.integrals.observation_measure_units,
                "mean_occupancy_integral": density.integrals.mean_occupancy_integral,
                "probability_integral": density.integrals.probability_integral,
                "support_fraction": support_fraction,
                "error_certificate": density.error_certificate.to_dict(),
            },
            messages=("One coarse grid and one bandwidth were executed; convergence is not certified.",),
        ),
        "topology_certificate": PilotEvidenceRecord(
            "topology_certificate", "11E2/S1", PilotEvidenceStatus.PARTIAL,
            source_digest=source_digest,
            accepted_fraction=isolated_count / max(1, len(attractors.attractors)),
            unresolved_fraction=unresolved_mode_fraction,
            metrics={
                "attractor_catalog_signature": attractors.signature,
                "attractor_count": len(attractors.attractors),
                "saddle_count": len(attractors.saddles),
                "geometry_counts": geometry_counts,
                "certificate_status": (
                    None if attractors.topology_certificate is None
                    else attractors.topology_certificate.status.value
                ),
            },
            messages=("Single-realization topology has no grid/bandwidth stability certificate.",),
        ),
        "attractor_lineage": PilotEvidenceRecord(
            "attractor_lineage", "11E2/S1", PilotEvidenceStatus.PARTIAL,
            source_digest=source_digest, accepted_fraction=0.0, unresolved_fraction=1.0,
            metrics={"single_scale_catalog_signature": attractors.signature, "lineage_executed": False},
            messages=("A single bandwidth cannot establish attractor lineage.",),
        ),
        "provisional_cores": PilotEvidenceRecord(
            "provisional_cores", "11E2/S1", PilotEvidenceStatus.PARTIAL,
            source_digest=source_digest,
            accepted_fraction=resolved_core_count / max(1, len(attractors.provisional_cores)),
            unresolved_fraction=1.0 - resolved_core_count / max(1, len(attractors.provisional_cores)),
            metrics={
                "core_count": len(attractors.provisional_cores),
                "resolved_core_count": resolved_core_count,
                "core_signatures": [core.signature for core in attractors.provisional_cores],
            },
            messages=("Core depth is provisional until topology lineage and reference sensitivity pass.",),
        ),
        "unresolved_fraction": PilotEvidenceRecord(
            "unresolved_fraction", PILOT_DENSITY_ATTRACTOR_STAGE, PilotEvidenceStatus.PARTIAL,
            source_digest=source_digest,
            accepted_fraction=1.0 - unresolved_mode_fraction,
            unresolved_fraction=unresolved_mode_fraction,
            metrics={
                "point_mode_fraction": 1.0 - unresolved_mode_fraction,
                "unresolved_geometry_fraction": unresolved_mode_fraction,
                "representative_frame_fraction": representative_fraction,
                "represented_time_fraction": 1.0,
            },
        ),
        "cost": PilotEvidenceRecord(
            "cost", PILOT_DENSITY_ATTRACTOR_STAGE, PilotEvidenceStatus.RESOLVED,
            source_digest=source_digest, accepted_fraction=1.0, unresolved_fraction=0.0,
            metrics={"s1_total_wall_seconds": elapsed},
        ),
        "memory": PilotEvidenceRecord(
            "memory", PILOT_DENSITY_ATTRACTOR_STAGE, PilotEvidenceStatus.RESOLVED,
            source_digest=source_digest, accepted_fraction=1.0, unresolved_fraction=0.0,
            metrics={
                "resident_numerical_payload_bytes": resident_bytes,
                "measurement_kind": "deduplicated recursive ndarray payload estimate",
            },
        ),
    }
    evidence = _replace_evidence(source.report.evidence, replacements)
    outcome = PilotScientificOutcome(
        site_center_count=isolated_count,
        supported_basin_count=len(attractors.attractors),
        observed_connection_count=None,
        transition_path_ensemble_count=None,
        undersampled_path_ensemble_count=None,
        rate_status=PilotRateStatus.NOT_EVALUATED,
        global_pmf_status=(
            PilotPMFStatus.SUPPORT_LIMITED
            if pilot_samples.evidence_masks.pmf_force_mask.any()
            else PilotPMFStatus.UNSUPPORTED
        ),
        conclusions=(
            f"The S1 coarse realization contains {len(attractors.attractors)} supported basins and {isolated_count} isolated point modes.",
            "Framework registration, periodized density, and one attractor realization are source-bound.",
            "Grid/bandwidth lineage, stationarity, temporal states, transition paths, and rates remain unresolved.",
        ),
    )
    report = prepare_na_lta_300k_pilot_report(
        source.report.dataset,
        evidence,
        artifacts=source.report.artifacts,
        resources=PilotResourceUsage(
            wall_seconds=elapsed,
            peak_memory_bytes=resident_bytes,
            worker_count=1,
            output_bytes=sum(item.byte_count for item in source.report.artifacts),
            metadata={
                "memory_measurement_kind": "deduplicated recursive ndarray payload estimate",
                "scope": "S0 source binding + S1 gauge + E1 density + E2 attractor pilot",
            },
        ),
        outcome=outcome,
        metadata={
            **dict(metadata or {}),
            "audit_kind": "real_density_attractor_pilot",
            "s1_complete": True,
            "options_signature": active.signature,
            "gauge_validation_signature": validation.signature,
            "next_execution_boundary": "11E8a-S2 density refinement, reference-cell sensitivity, and attractor lineage",
        },
        policy=audit_policy,
    )
    return NaLta300KDensityAttractorPilot(
        report=report,
        source_bootstrap=source,
        gauge_validation=validation,
        pilot_samples=pilot_samples,
        density=density,
        attractors=attractors,
        representative_frame_indices=representatives,
        wall_seconds=elapsed,
    )


__all__ = [
    "PILOT_DENSITY_ATTRACTOR_STAGE",
    "PILOT_DENSITY_ATTRACTOR_OPTIONS_SCHEMA",
    "FRAMEWORK_REGISTRATION_GAUGE_SCHEMA",
    "NaLta300KDensityAttractorPilotOptions",
    "FrameworkRegistrationGaugeValidation",
    "NaLta300KDensityAttractorPilot",
    "prepare_na_lta_300k_density_attractor_pilot",
]
