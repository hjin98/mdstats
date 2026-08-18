"""Stage-11E8a-S2 density refinement and attractor-lineage pilot.

S2 reuses the exact S1 source, registration, and represented-time contracts,
then executes an explicit Cartesian bandwidth ladder, a central-bandwidth grid
refinement series, and a declared reference-cell sensitivity comparison.  The
products are spatial robustness evidence only; temporal states, paths, force-
density agreement, rates, and a global PMF remain outside this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

from ...collection import AtomisticFrameCollection
from ...coordinates.registration import (
    FrameRegistrationPolicy,
    ReferenceTranslationOptions,
    ReferenceWeighting,
    RegistrationSpatialPolicy,
    TranslationMode,
    prepare_frame_registration,
)
from ..site_samples import (
    prepare_framework_aligned_ion_sample_catalog,
    prepare_trajectory_segment_weighting,
)
from .attractors import (
    AttractorGeometry,
    DensityAttractorCatalog,
    DensityAttractorLineage,
    DensityAttractorOptions,
    DensityAttractorRefinementSeries,
    DensityAttractorResourcePolicy,
    ScaleConsensusResult,
    ScaleDecisionStatus,
    SelectionValidationProtocol,
    TopologyStabilityStatus,
    certify_topology_refinement,
    prepare_density_attractor_catalog,
    prepare_density_attractor_lineage,
    prepare_scale_consensus,
)
from ._pilot_common import (
    array_payload_bytes as _array_payload_bytes,
    canonical_json as _canonical_json,
    digest as _digest,
    nonnegative as _nonnegative,
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
from .pilot_density_attractors import (
    NaLta300KDensityAttractorPilot,
    NaLta300KDensityAttractorPilotOptions,
    prepare_na_lta_300k_density_attractor_pilot,
)
from .species import (
    GaussianKernelCovariance,
    PeriodicDensityDomain,
    PeriodicSpeciesDensityEstimate,
    PeriodicSpeciesDensityLadder,
    SpeciesDensityOptions,
    SpeciesDensityResourcePolicy,
    prepare_periodic_species_density,
    prepare_periodic_species_density_ladder,
)

PILOT_REFINEMENT_LINEAGE_STAGE = "11E8a-S2"
PILOT_REFINEMENT_LINEAGE_OPTIONS_SCHEMA = "mdstats.na-lta-300k-refinement-lineage-options.v1"
REFERENCE_CELL_SENSITIVITY_SCHEMA = "mdstats.reference-cell-sensitivity-certificate.v1"












def _shape(value: Sequence[int], name: str) -> tuple[int, int, int]:
    result = tuple(_positive_int(v, name) for v in value)
    if len(result) != 3:
        raise PilotAuditInputError(f"{name} must contain three positive integers.")
    return result






@dataclass(frozen=True, slots=True)
class NaLta300KRefinementLineageOptions:
    """Signed S2 spatial-refinement controls."""

    bandwidth_sigmas_angstrom: tuple[float, ...] = (0.4, 0.5, 0.6)
    central_bandwidth_sigma_angstrom: float = 0.5
    lineage_grid_shape: tuple[int, int, int] = (12, 12, 12)
    refinement_grid_shapes: tuple[tuple[int, int, int], ...] = (
        (12, 12, 12),
        (16, 16, 16),
    )
    comparison_reference_frame_index: int | None = None
    minimum_lineage_overlap: float = 0.05
    minimum_refinement_basin_overlap: float = 0.20
    maximum_reference_cell_relative_difference: float = 0.02
    maximum_reference_probability_l1: float = 0.10
    maximum_reference_anchor_displacement_angstrom: float = 0.30
    maximum_reference_unmatched_attractors: int = 0
    density_query_batch_size: int = 256
    density_sample_batch_size: int = 128
    relative_image_tolerance: float = 1.0e-10
    maximum_image_radius: int = 2
    signature: str = ""

    def __post_init__(self) -> None:
        bandwidths = tuple(_positive(v, "bandwidth_sigma") for v in self.bandwidth_sigmas_angstrom)
        if len(bandwidths) < 2 or len(set(bandwidths)) != len(bandwidths):
            raise PilotAuditInputError("S2 bandwidth ladder requires at least two unique widths.")
        if tuple(sorted(bandwidths)) != bandwidths:
            raise PilotAuditInputError("S2 bandwidth widths must be strictly increasing.")
        central = _positive(self.central_bandwidth_sigma_angstrom, "central_bandwidth_sigma_angstrom")
        if central not in bandwidths:
            raise PilotAuditInputError("central bandwidth must be a member of the S2 ladder.")
        lineage_shape = _shape(self.lineage_grid_shape, "lineage_grid_shape")
        shapes = tuple(_shape(v, "refinement_grid_shape") for v in self.refinement_grid_shapes)
        if len(shapes) < 2 or len(set(shapes)) != len(shapes):
            raise PilotAuditInputError("S2 grid refinement requires at least two unique shapes.")
        for previous, current in zip(shapes[:-1], shapes[1:]):
            if any(current[i] < previous[i] for i in range(3)):
                raise PilotAuditInputError("refinement grid shapes must be componentwise nondecreasing.")
        comparison = self.comparison_reference_frame_index
        if comparison is not None and int(comparison) < 0:
            raise PilotAuditInputError("comparison_reference_frame_index must be nonnegative or None.")
        unmatched = int(self.maximum_reference_unmatched_attractors)
        if unmatched < 0:
            raise PilotAuditInputError("maximum_reference_unmatched_attractors must be nonnegative.")
        values = {
            "bandwidth_sigmas_angstrom": bandwidths,
            "central_bandwidth_sigma_angstrom": central,
            "lineage_grid_shape": lineage_shape,
            "refinement_grid_shapes": shapes,
            "comparison_reference_frame_index": None if comparison is None else int(comparison),
            "minimum_lineage_overlap": _nonnegative(self.minimum_lineage_overlap, "minimum_lineage_overlap"),
            "minimum_refinement_basin_overlap": _nonnegative(self.minimum_refinement_basin_overlap, "minimum_refinement_basin_overlap"),
            "maximum_reference_cell_relative_difference": _nonnegative(self.maximum_reference_cell_relative_difference, "maximum_reference_cell_relative_difference"),
            "maximum_reference_probability_l1": _nonnegative(self.maximum_reference_probability_l1, "maximum_reference_probability_l1"),
            "maximum_reference_anchor_displacement_angstrom": _nonnegative(self.maximum_reference_anchor_displacement_angstrom, "maximum_reference_anchor_displacement_angstrom"),
            "maximum_reference_unmatched_attractors": unmatched,
            "density_query_batch_size": _positive_int(self.density_query_batch_size, "density_query_batch_size"),
            "density_sample_batch_size": _positive_int(self.density_sample_batch_size, "density_sample_batch_size"),
            "relative_image_tolerance": _positive(self.relative_image_tolerance, "relative_image_tolerance"),
            "maximum_image_radius": _positive_int(self.maximum_image_radius, "maximum_image_radius"),
        }
        payload = {
            "schema": PILOT_REFINEMENT_LINEAGE_OPTIONS_SCHEMA,
            **{
                key: ([list(v) for v in value] if key == "refinement_grid_shapes" else list(value) if isinstance(value, tuple) else value)
                for key, value in values.items()
            },
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("S2 refinement-lineage options signature is inconsistent.")
        for key, value in values.items():
            object.__setattr__(self, key, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PILOT_REFINEMENT_LINEAGE_OPTIONS_SCHEMA,
            "bandwidth_sigmas_angstrom": list(self.bandwidth_sigmas_angstrom),
            "central_bandwidth_sigma_angstrom": self.central_bandwidth_sigma_angstrom,
            "lineage_grid_shape": list(self.lineage_grid_shape),
            "refinement_grid_shapes": [list(v) for v in self.refinement_grid_shapes],
            "comparison_reference_frame_index": self.comparison_reference_frame_index,
            "minimum_lineage_overlap": self.minimum_lineage_overlap,
            "minimum_refinement_basin_overlap": self.minimum_refinement_basin_overlap,
            "maximum_reference_cell_relative_difference": self.maximum_reference_cell_relative_difference,
            "maximum_reference_probability_l1": self.maximum_reference_probability_l1,
            "maximum_reference_anchor_displacement_angstrom": self.maximum_reference_anchor_displacement_angstrom,
            "maximum_reference_unmatched_attractors": self.maximum_reference_unmatched_attractors,
            "density_query_batch_size": self.density_query_batch_size,
            "density_sample_batch_size": self.density_sample_batch_size,
            "relative_image_tolerance": self.relative_image_tolerance,
            "maximum_image_radius": self.maximum_image_radius,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NaLta300KRefinementLineageOptions":
        if payload.get("schema") != PILOT_REFINEMENT_LINEAGE_OPTIONS_SCHEMA:
            raise PilotAuditInputError("Unsupported S2 refinement-lineage options schema.")
        return cls(
            bandwidth_sigmas_angstrom=tuple(float(v) for v in payload["bandwidth_sigmas_angstrom"]),
            central_bandwidth_sigma_angstrom=float(payload["central_bandwidth_sigma_angstrom"]),
            lineage_grid_shape=tuple(int(v) for v in payload["lineage_grid_shape"]),
            refinement_grid_shapes=tuple(tuple(int(v) for v in shape) for shape in payload["refinement_grid_shapes"]),
            comparison_reference_frame_index=(None if payload.get("comparison_reference_frame_index") is None else int(payload["comparison_reference_frame_index"])),
            minimum_lineage_overlap=float(payload["minimum_lineage_overlap"]),
            minimum_refinement_basin_overlap=float(payload["minimum_refinement_basin_overlap"]),
            maximum_reference_cell_relative_difference=float(payload["maximum_reference_cell_relative_difference"]),
            maximum_reference_probability_l1=float(payload["maximum_reference_probability_l1"]),
            maximum_reference_anchor_displacement_angstrom=float(payload["maximum_reference_anchor_displacement_angstrom"]),
            maximum_reference_unmatched_attractors=int(payload["maximum_reference_unmatched_attractors"]),
            density_query_batch_size=int(payload["density_query_batch_size"]),
            density_sample_batch_size=int(payload["density_sample_batch_size"]),
            relative_image_tolerance=float(payload["relative_image_tolerance"]),
            maximum_image_radius=int(payload["maximum_image_radius"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class ReferenceCellSensitivityCertificate:
    """Signed S2 comparison of homologous registered reference domains."""

    selected_registration_signature: str
    comparison_registration_signature: str
    selected_cell_digest: str
    comparison_cell_digest: str
    comparison_source_frame_index: int
    exact_identity_shortcut: bool
    relative_cell_frobenius_difference: float
    relative_volume_difference: float
    fractional_probability_l1: float
    matched_attractor_count: int
    unmatched_selected_count: int
    unmatched_comparison_count: int
    maximum_anchor_displacement_angstrom: float
    rms_anchor_displacement_angstrom: float
    cell_difference_limit: float
    probability_l1_limit: float
    anchor_displacement_limit_angstrom: float
    unmatched_attractor_limit: int
    accepted: bool
    signature: str = ""

    def __post_init__(self) -> None:
        sha_fields = (
            "selected_registration_signature",
            "comparison_registration_signature",
            "selected_cell_digest",
            "comparison_cell_digest",
        )
        for name in sha_fields:
            value = str(getattr(self, name))
            if len(value) != 64:
                raise PilotAuditInputError(f"{name} must be a SHA-256 digest.")
        integer_fields = (
            "comparison_source_frame_index",
            "matched_attractor_count",
            "unmatched_selected_count",
            "unmatched_comparison_count",
            "unmatched_attractor_limit",
        )
        integers = {name: int(getattr(self, name)) for name in integer_fields}
        if any(value < 0 for value in integers.values()):
            raise PilotAuditInputError("Reference-cell sensitivity counts must be nonnegative.")
        float_fields = (
            "relative_cell_frobenius_difference",
            "relative_volume_difference",
            "fractional_probability_l1",
            "maximum_anchor_displacement_angstrom",
            "rms_anchor_displacement_angstrom",
            "cell_difference_limit",
            "probability_l1_limit",
            "anchor_displacement_limit_angstrom",
        )
        floats = {name: _nonnegative(getattr(self, name), name) for name in float_fields}
        payload = {
            "schema": REFERENCE_CELL_SENSITIVITY_SCHEMA,
            **{name: str(getattr(self, name)) for name in sha_fields},
            **integers,
            **floats,
            "exact_identity_shortcut": bool(self.exact_identity_shortcut),
            "accepted": bool(self.accepted),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Reference-cell sensitivity signature is inconsistent.")
        for name, value in integers.items():
            object.__setattr__(self, name, value)
        for name, value in floats.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        result = {field.name: getattr(self, field.name) for field in fields(self)}
        result["schema"] = REFERENCE_CELL_SENSITIVITY_SCHEMA
        return result

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReferenceCellSensitivityCertificate":
        if payload.get("schema") != REFERENCE_CELL_SENSITIVITY_SCHEMA:
            raise PilotAuditInputError("Unsupported reference-cell sensitivity schema.")
        return cls(**{key: value for key, value in payload.items() if key != "schema"})


@dataclass(frozen=True, slots=True)
class NaLta300KRefinementLineagePilot:
    report: NaLta300KPilotReport
    s1_pilot: NaLta300KDensityAttractorPilot
    density_ladder: PeriodicSpeciesDensityLadder
    lineage_catalogs: tuple[DensityAttractorCatalog, ...]
    lineage: DensityAttractorLineage
    scale_consensus: ScaleConsensusResult
    grid_refinement_catalogs: tuple[DensityAttractorCatalog, ...]
    grid_refinement: DensityAttractorRefinementSeries
    reference_cell_sensitivity: ReferenceCellSensitivityCertificate
    options: NaLta300KRefinementLineageOptions
    wall_seconds: float

    def __post_init__(self) -> None:
        if self.density_ladder.catalog_signature != self.s1_pilot.pilot_samples.signature:
            raise PilotAuditInputError("S2 ladder is not bound to the S1 sample catalog.")
        if self.lineage.ladder_signature != self.density_ladder.signature:
            raise PilotAuditInputError("S2 lineage is not bound to the density ladder.")
        if tuple(item.signature for item in self.lineage_catalogs) != self.lineage.catalog_signatures:
            raise PilotAuditInputError("S2 lineage catalogs disagree with the lineage record.")
        if tuple(item.signature for item in self.grid_refinement_catalogs) != self.grid_refinement.catalog_signatures:
            raise PilotAuditInputError("S2 grid-refinement catalogs disagree with the refinement record.")
        if not isinstance(self.options, NaLta300KRefinementLineageOptions):
            raise PilotAuditInputError("S2 pilot options have the wrong type.")


def _density_options(shape: tuple[int, int, int], active: NaLta300KRefinementLineageOptions) -> SpeciesDensityOptions:
    return SpeciesDensityOptions(
        grid_shape=shape,
        query_batch_size=active.density_query_batch_size,
        sample_batch_size=active.density_sample_batch_size,
        relative_image_tolerance=active.relative_image_tolerance,
        max_image_radius=active.maximum_image_radius,
        minimum_effective_samples=1.0,
        metadata={"pilot_stage": PILOT_REFINEMENT_LINEAGE_STAGE},
    )


def _registration_policy(
    framework_indices: tuple[int, ...],
    na_indices: tuple[int, ...],
    reference_frame_index: int,
    maximum_residual: float,
) -> FrameRegistrationPolicy:
    return FrameRegistrationPolicy(
        spatial_policy=RegistrationSpatialPolicy.REFERENCE_MATERIAL,
        translation_mode=TranslationMode.MATCHED_REFERENCE,
        reference_atom_indices=framework_indices,
        reference_frame_index=reference_frame_index,
        reference_weighting=ReferenceWeighting.CENTER_OF_GEOMETRY,
        force_target_atom_indices=na_indices,
        require_fixed_registered_cell=True,
        translation_options=ReferenceTranslationOptions(maximum_residual=maximum_residual),
    )


def _cell_digest(cell: np.ndarray) -> str:
    arr = np.ascontiguousarray(np.asarray(cell, dtype=np.float64))
    h = hashlib.sha256()
    h.update(arr.dtype.str.encode("ascii"))
    h.update(str(arr.shape).encode("ascii"))
    h.update(arr.tobytes(order="C"))
    return h.hexdigest()


def _reference_anchor_matches(
    selected: DensityAttractorCatalog,
    comparison: DensityAttractorCatalog,
    selected_cell: np.ndarray,
    comparison_cell: np.ndarray,
) -> tuple[int, int, int, float, float]:
    n_selected = len(selected.attractors)
    n_comparison = len(comparison.attractors)
    if n_selected == 0 or n_comparison == 0:
        return 0, n_selected, n_comparison, 0.0, 0.0
    mean_cell = 0.5 * (np.asarray(selected_cell) + np.asarray(comparison_cell))
    cost = np.empty((n_selected, n_comparison), dtype=np.float64)
    distances = np.empty_like(cost)
    for i, source in enumerate(selected.attractors):
        for j, target in enumerate(comparison.attractors):
            delta = np.asarray(source.anchor_fractional) - np.asarray(target.anchor_fractional)
            delta -= np.rint(delta)
            distance = float(np.linalg.norm(delta @ mean_cell))
            distances[i, j] = distance
            geometry_penalty = 1.0e3 if source.geometry is not target.geometry else 0.0
            cost[i, j] = distance + geometry_penalty
    rows, cols = linear_sum_assignment(cost)
    matched_distances: list[float] = []
    matched = 0
    for row, col in zip(rows, cols, strict=True):
        if selected.attractors[int(row)].geometry is comparison.attractors[int(col)].geometry:
            matched += 1
            matched_distances.append(float(distances[int(row), int(col)]))
    maximum = max(matched_distances, default=0.0)
    rms = float(np.sqrt(np.mean(np.square(matched_distances)))) if matched_distances else 0.0
    return matched, n_selected - matched, n_comparison - matched, maximum, rms


def _reference_sensitivity(
    collection: AtomisticFrameCollection,
    s1: NaLta300KDensityAttractorPilot,
    active: NaLta300KRefinementLineageOptions,
    comparison_frame_index: int,
    central_density: PeriodicSpeciesDensityEstimate,
    central_attractors: DensityAttractorCatalog,
    density_resources: SpeciesDensityResourcePolicy,
    attractor_options: DensityAttractorOptions | None,
    attractor_resources: DensityAttractorResourcePolicy | None,
) -> ReferenceCellSensitivityCertificate:
    selected_cell = np.asarray(central_density.domain.cell, dtype=np.float64)
    comparison_source_cell = np.asarray(collection.cells[comparison_frame_index], dtype=np.float64)
    cell_scale = max(float(np.linalg.norm(selected_cell)), np.finfo(float).tiny)
    relative_cell = float(np.linalg.norm(comparison_source_cell - selected_cell) / cell_scale)
    selected_volume = abs(float(np.linalg.det(selected_cell)))
    comparison_volume = abs(float(np.linalg.det(comparison_source_cell)))
    relative_volume = abs(comparison_volume - selected_volume) / max(selected_volume, np.finfo(float).tiny)
    identity = bool(np.array_equal(comparison_source_cell, selected_cell))

    if identity:
        comparison_registration_signature = s1.source_bootstrap.registration.signature
        comparison_density = central_density
        comparison_attractors = central_attractors
    else:
        framework_indices = tuple(int(v) for v in np.flatnonzero(collection.atomic_numbers != 11))
        na_indices = tuple(int(v) for v in np.flatnonzero(collection.atomic_numbers == 11))
        comparison_registration = prepare_frame_registration(
            collection,
            policy=_registration_policy(
                framework_indices,
                na_indices,
                comparison_frame_index,
                s1.gauge_validation.residual_limit_angstrom,
            ),
            reference_frame_index=comparison_frame_index,
        )
        comparison_registration_signature = comparison_registration.signature
        temporal = prepare_trajectory_segment_weighting(
            collection,
            registration=comparison_registration,
            explicit_frame_weights=s1.pilot_samples.temporal_weighting.represented_time_weights,
            explicit_weight_units=s1.pilot_samples.temporal_weighting.weight_units,
        )
        comparison_samples = prepare_framework_aligned_ion_sample_catalog(
            collection,
            comparison_registration,
            species_atomic_number=11,
            species_label="Na",
            temporal_weighting=temporal,
            sampling_state=s1.pilot_samples.sampling_state,
            pmf_temperature=s1.pilot_samples.pmf_temperature,
            metadata={
                "pilot_stage": PILOT_REFINEMENT_LINEAGE_STAGE,
                "reference_sensitivity_comparison": True,
                "comparison_source_frame_index": comparison_frame_index,
            },
        )
        comparison_domain = PeriodicDensityDomain(
            cell=comparison_registration.registered_cells[0],
            registration_signature=comparison_registration.signature,
            source_cell_variation_max=float(np.max(np.abs(
                comparison_registration.registered_cells - comparison_registration.registered_cells[0]
            ))),
            metadata={"pilot_stage": PILOT_REFINEMENT_LINEAGE_STAGE, "reference_comparison": True},
        )
        comparison_kernel = GaussianKernelCovariance.isotropic_cartesian(
            active.central_bandwidth_sigma_angstrom,
            comparison_domain,
            label="stage11e8a-s2-reference-comparison",
        )
        comparison_density = prepare_periodic_species_density(
            comparison_samples,
            comparison_domain,
            comparison_kernel,
            options=_density_options(active.lineage_grid_shape, active),
            resources=density_resources,
        )
        comparison_attractors = prepare_density_attractor_catalog(
            comparison_density,
            options=attractor_options,
            resources=attractor_resources,
        )
        comparison_source_cell = np.asarray(comparison_domain.cell, dtype=np.float64)

    selected_probability_fractional = central_density.realization.probability_density_dense() * selected_volume
    comparison_probability_fractional = comparison_density.realization.probability_density_dense() * abs(float(np.linalg.det(comparison_source_cell)))
    if selected_probability_fractional.shape != comparison_probability_fractional.shape:
        raise PilotAuditInputError("Reference-cell sensitivity requires aligned logical grids.")
    probability_l1 = float(np.mean(np.abs(selected_probability_fractional - comparison_probability_fractional)))
    matched, unmatched_selected, unmatched_comparison, max_anchor, rms_anchor = _reference_anchor_matches(
        central_attractors,
        comparison_attractors,
        selected_cell,
        comparison_source_cell,
    )
    unmatched_total = unmatched_selected + unmatched_comparison
    accepted = bool(
        relative_cell <= active.maximum_reference_cell_relative_difference
        and probability_l1 <= active.maximum_reference_probability_l1
        and max_anchor <= active.maximum_reference_anchor_displacement_angstrom
        and unmatched_total <= active.maximum_reference_unmatched_attractors
    )
    return ReferenceCellSensitivityCertificate(
        selected_registration_signature=s1.source_bootstrap.registration.signature,
        comparison_registration_signature=comparison_registration_signature,
        selected_cell_digest=_cell_digest(selected_cell),
        comparison_cell_digest=_cell_digest(comparison_source_cell),
        comparison_source_frame_index=comparison_frame_index,
        exact_identity_shortcut=identity,
        relative_cell_frobenius_difference=relative_cell,
        relative_volume_difference=relative_volume,
        fractional_probability_l1=probability_l1,
        matched_attractor_count=matched,
        unmatched_selected_count=unmatched_selected,
        unmatched_comparison_count=unmatched_comparison,
        maximum_anchor_displacement_angstrom=max_anchor,
        rms_anchor_displacement_angstrom=rms_anchor,
        cell_difference_limit=active.maximum_reference_cell_relative_difference,
        probability_l1_limit=active.maximum_reference_probability_l1,
        anchor_displacement_limit_angstrom=active.maximum_reference_anchor_displacement_angstrom,
        unmatched_attractor_limit=active.maximum_reference_unmatched_attractors,
        accepted=accepted,
    )


def prepare_na_lta_300k_refinement_lineage_pilot(
    collection: AtomisticFrameCollection,
    trajectory_path: str | Path,
    *,
    options: NaLta300KRefinementLineageOptions | None = None,
    s1_options: NaLta300KDensityAttractorPilotOptions | None = None,
    density_resources: SpeciesDensityResourcePolicy | None = None,
    attractor_options: DensityAttractorOptions | None = None,
    attractor_resources: DensityAttractorResourcePolicy | None = None,
    audit_policy: PilotAuditResourcePolicy | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> NaLta300KRefinementLineagePilot:
    """Execute the source-bound Stage-11E8a-S2 spatial refinement pilot."""

    active = options or NaLta300KRefinementLineageOptions()
    started = perf_counter()
    s1 = prepare_na_lta_300k_density_attractor_pilot(
        collection,
        trajectory_path,
        options=s1_options,
        density_resources=density_resources,
        attractor_options=attractor_options,
        attractor_resources=attractor_resources,
        audit_policy=audit_policy,
        metadata={"requested_by_stage": PILOT_REFINEMENT_LINEAGE_STAGE},
    )
    resources = density_resources or SpeciesDensityResourcePolicy(max_image_terms=1_000_000_000)
    attractor_policy = attractor_resources or DensityAttractorResourcePolicy()
    domain = s1.density.domain
    kernels = tuple(
        GaussianKernelCovariance.isotropic_cartesian(
            sigma,
            domain,
            label=f"stage11e8a-s2-sigma-{sigma:.6g}",
        )
        for sigma in active.bandwidth_sigmas_angstrom
    )
    ladder = prepare_periodic_species_density_ladder(
        s1.pilot_samples,
        domain,
        kernels,
        options=_density_options(active.lineage_grid_shape, active),
        resources=resources,
    )
    lineage_catalogs, lineage = prepare_density_attractor_lineage(
        ladder,
        options=attractor_options,
        resources=attractor_policy,
        minimum_overlap=active.minimum_lineage_overlap,
    )
    protocol = SelectionValidationProtocol(
        discovery_block_ids=tuple(f"represented-bin-{i}" for i in range(len(s1.representative_frame_indices))),
    )
    consensus = prepare_scale_consensus(lineage_catalogs, lineage, protocol)
    central_index = active.bandwidth_sigmas_angstrom.index(active.central_bandwidth_sigma_angstrom)
    central_density = ladder.estimates[central_index]
    central_attractors = lineage_catalogs[central_index]

    grid_catalogs: list[DensityAttractorCatalog] = []
    s1_shape = tuple(int(v) for v in s1.density.realization.grid_shape)
    s1_source_covariance = s1.density.kernel_covariance.source_covariance
    s1_sigma = (
        float(np.sqrt(np.trace(s1_source_covariance) / 3.0))
        if s1_source_covariance is not None
        else float("nan")
    )
    for shape in active.refinement_grid_shapes:
        if shape == active.lineage_grid_shape:
            catalog = central_attractors
        elif (
            shape == s1_shape
            and np.isclose(
                s1_sigma,
                active.central_bandwidth_sigma_angstrom,
                rtol=0.0,
                atol=1.0e-15,
            )
        ):
            # S1 is already source-, sample-, domain-, bandwidth-, and grid-bound.
            # Reusing it avoids an identical expensive field evaluation while
            # preserving a distinct signed refinement-series catalog member.
            catalog = s1.attractors
        else:
            estimate = prepare_periodic_species_density(
                s1.pilot_samples,
                domain,
                kernels[central_index],
                options=_density_options(shape, active),
                resources=resources,
            )
            catalog = prepare_density_attractor_catalog(
                estimate,
                options=attractor_options,
                resources=attractor_policy,
            )
        grid_catalogs.append(catalog)
    refinement = certify_topology_refinement(
        grid_catalogs,
        central_density.analysis_metric,
        minimum_basin_overlap=active.minimum_refinement_basin_overlap,
    )

    if active.comparison_reference_frame_index is None:
        comparison_frame = int(s1.representative_frame_indices[len(s1.representative_frame_indices) // 2])
    else:
        comparison_frame = int(active.comparison_reference_frame_index)
    if comparison_frame >= collection.n_frames:
        raise PilotAuditInputError("S2 comparison reference frame lies outside the collection.")
    reference = _reference_sensitivity(
        collection,
        s1,
        active,
        comparison_frame,
        central_density,
        central_attractors,
        resources,
        attractor_options,
        attractor_policy,
    )
    elapsed = perf_counter() - started

    source_digest = s1.source_bootstrap.trajectory_sha256
    topology_stable = refinement.certificate.status is TopologyStabilityStatus.STABLE
    scale_resolved = consensus.status is ScaleDecisionStatus.RESOLVED
    lineage_links = sum(len(item.links) for item in lineage.correspondences)
    lineage_unmatched = sum(len(item.source_unmatched) + len(item.target_unmatched) for item in lineage.correspondences)
    lineage_total = lineage_links + lineage_unmatched
    lineage_fraction = lineage_links / max(1, lineage_total)
    central_geometry_counts: dict[str, int] = {}
    for attractor in central_attractors.attractors:
        key = AttractorGeometry(attractor.geometry).value
        central_geometry_counts[key] = central_geometry_counts.get(key, 0) + 1
    isolated_count = central_geometry_counts.get(AttractorGeometry.ISOLATED_MODE.value, 0)
    unresolved_geometry = 1.0 - isolated_count / max(1, len(central_attractors.attractors))
    resolved_core_count = sum(bool(core.resolved) for core in central_attractors.provisional_cores)
    field_realization_signatures = {
        s1.density.signature,
        *(item.signature for item in ladder.estimates),
        *(item.density_estimate_signature for item in grid_catalogs),
    }
    field_realization_count = len(field_realization_signatures)
    resident_bytes = _array_payload_bytes(
        collection,
        s1,
        ladder,
        lineage_catalogs,
        lineage,
        consensus,
        tuple(grid_catalogs),
        refinement,
        reference,
    )

    reference_status = PilotEvidenceStatus.RESOLVED if reference.accepted else PilotEvidenceStatus.BLOCKED
    topology_status = PilotEvidenceStatus.RESOLVED if topology_stable else PilotEvidenceStatus.PARTIAL
    lineage_status = PilotEvidenceStatus.RESOLVED if scale_resolved and not lineage.ambiguous else PilotEvidenceStatus.PARTIAL
    core_status = PilotEvidenceStatus.RESOLVED if topology_stable and scale_resolved else PilotEvidenceStatus.PARTIAL
    replacements = {
        "reference_cell_sensitivity": PilotEvidenceRecord(
            "reference_cell_sensitivity",
            PILOT_REFINEMENT_LINEAGE_STAGE,
            reference_status,
            source_digest=source_digest,
            accepted_fraction=1.0 if reference.accepted else 0.0,
            unresolved_fraction=0.0 if reference.accepted else 1.0,
            metrics={**reference.to_dict(), "certificate_signature": reference.signature},
            messages=(() if reference.accepted else ("Reference-cell sensitivity exceeded one or more declared limits.",)),
        ),
        "field_certificate": PilotEvidenceRecord(
            "field_certificate",
            "11E1/S2",
            PilotEvidenceStatus.RESOLVED,
            source_digest=source_digest,
            accepted_fraction=1.0,
            unresolved_fraction=0.0,
            metrics={
                "density_ladder_signature": ladder.signature,
                "bandwidth_sigmas_angstrom": active.bandwidth_sigmas_angstrom,
                "lineage_grid_shape": active.lineage_grid_shape,
                "refinement_grid_shapes": active.refinement_grid_shapes,
                "field_realization_count": field_realization_count,
                "mean_occupancy_integrals": [item.integrals.mean_occupancy_integral for item in ladder.estimates],
                "probability_integrals": [item.integrals.probability_integral for item in ladder.estimates],
                "maximum_probability_normalization_residual": max(item.error_certificate.discrete_probability_normalization_residual for item in ladder.estimates),
            },
        ),
        "topology_certificate": PilotEvidenceRecord(
            "topology_certificate",
            "11E2/S2",
            topology_status,
            source_digest=source_digest,
            accepted_fraction=1.0 if topology_stable else 0.0,
            unresolved_fraction=0.0 if topology_stable else 1.0,
            metrics={
                "grid_refinement_signature": refinement.signature,
                "certificate": refinement.certificate.to_dict(),
                "central_catalog_signature": central_attractors.signature,
                "central_attractor_count": len(central_attractors.attractors),
                "central_saddle_count": len(central_attractors.saddles),
                "central_geometry_counts": central_geometry_counts,
            },
        ),
        "attractor_lineage": PilotEvidenceRecord(
            "attractor_lineage",
            "11E2/S2",
            lineage_status,
            source_digest=source_digest,
            accepted_fraction=lineage_fraction,
            unresolved_fraction=1.0 - lineage_fraction,
            metrics={
                "lineage_signature": lineage.signature,
                "catalog_signatures": lineage.catalog_signatures,
                "survival_intervals": lineage.survival_intervals,
                "ambiguous": lineage.ambiguous,
                "correspondence_count": len(lineage.correspondences),
                "matched_links": lineage_links,
                "unmatched_attractors": lineage_unmatched,
                "scale_consensus_signature": consensus.signature,
                "scale_decision_status": consensus.status.value,
                "selected_catalog_signature": consensus.selected_catalog_signature,
                "candidate_scale_intervals": consensus.candidate_scale_intervals,
                "rationale": consensus.rationale,
            },
        ),
        "provisional_cores": PilotEvidenceRecord(
            "provisional_cores",
            "11E2/S2",
            core_status,
            source_digest=source_digest,
            accepted_fraction=resolved_core_count / max(1, len(central_attractors.provisional_cores)),
            unresolved_fraction=1.0 - resolved_core_count / max(1, len(central_attractors.provisional_cores)),
            metrics={
                "central_catalog_signature": central_attractors.signature,
                "core_count": len(central_attractors.provisional_cores),
                "resolved_core_count": resolved_core_count,
                "topology_stable": topology_stable,
                "scale_resolved": scale_resolved,
            },
            messages=(() if core_status is PilotEvidenceStatus.RESOLVED else ("Core identities remain provisional under unresolved scale or grid sensitivity.",)),
        ),
        "unresolved_fraction": PilotEvidenceRecord(
            "unresolved_fraction",
            PILOT_REFINEMENT_LINEAGE_STAGE,
            PilotEvidenceStatus.PARTIAL,
            source_digest=source_digest,
            accepted_fraction=1.0 - unresolved_geometry,
            unresolved_fraction=unresolved_geometry,
            metrics={
                "central_point_mode_fraction": 1.0 - unresolved_geometry,
                "central_unresolved_geometry_fraction": unresolved_geometry,
                "lineage_matched_fraction": lineage_fraction,
                "grid_topology_stable": topology_stable,
                "scale_resolved": scale_resolved,
                "reference_cell_accepted": reference.accepted,
            },
        ),
        "cost": PilotEvidenceRecord(
            "cost",
            PILOT_REFINEMENT_LINEAGE_STAGE,
            PilotEvidenceStatus.RESOLVED,
            source_digest=source_digest,
            accepted_fraction=1.0,
            unresolved_fraction=0.0,
            metrics={"s2_total_wall_seconds": elapsed, "field_realization_count": field_realization_count},
        ),
        "memory": PilotEvidenceRecord(
            "memory",
            PILOT_REFINEMENT_LINEAGE_STAGE,
            PilotEvidenceStatus.RESOLVED,
            source_digest=source_digest,
            accepted_fraction=1.0,
            unresolved_fraction=0.0,
            metrics={
                "resident_numerical_payload_bytes": resident_bytes,
                "measurement_kind": "deduplicated recursive ndarray payload estimate",
            },
        ),
    }
    evidence = _replace_evidence(s1.report.evidence, replacements)
    outcome = PilotScientificOutcome(
        site_center_count=isolated_count,
        supported_basin_count=len(central_attractors.attractors),
        observed_connection_count=None,
        transition_path_ensemble_count=None,
        undersampled_path_ensemble_count=None,
        rate_status=PilotRateStatus.NOT_EVALUATED,
        global_pmf_status=(
            PilotPMFStatus.SUPPORT_LIMITED
            if s1.pilot_samples.evidence_masks.pmf_force_mask.any()
            else PilotPMFStatus.UNSUPPORTED
        ),
        conclusions=(
            f"S2 executed {len(ladder.estimates)} bandwidths and {len(grid_catalogs)} grid levels.",
            f"The central realization contains {len(central_attractors.attractors)} supported basins and {isolated_count} isolated point modes.",
            f"Scale decision is {consensus.status.value}; grid refinement is {refinement.certificate.status.value}; reference-cell sensitivity accepted={reference.accepted}.",
            "Stationarity, temporal states, force-density agreement, transition paths, and rates remain unresolved.",
        ),
    )
    report = prepare_na_lta_300k_pilot_report(
        s1.report.dataset,
        evidence,
        artifacts=s1.report.artifacts,
        resources=PilotResourceUsage(
            wall_seconds=elapsed,
            peak_memory_bytes=resident_bytes,
            worker_count=1,
            output_bytes=sum(item.byte_count for item in s1.report.artifacts),
            metadata={
                "memory_measurement_kind": "deduplicated recursive ndarray payload estimate",
                "scope": "S0 source + S1 gauge/quadrature + S2 bandwidth/grid/reference spatial certification",
            },
        ),
        outcome=outcome,
        metadata={
            **dict(metadata or {}),
            "audit_kind": "real_refinement_lineage_pilot",
            "s1_complete": True,
            "s2_complete": True,
            "options_signature": active.signature,
            "reference_cell_sensitivity_signature": reference.signature,
            "next_execution_boundary": "11E8a-S3 structural mapping and temporal-support preparation",
        },
        policy=audit_policy,
    )
    return NaLta300KRefinementLineagePilot(
        report=report,
        s1_pilot=s1,
        density_ladder=ladder,
        lineage_catalogs=lineage_catalogs,
        lineage=lineage,
        scale_consensus=consensus,
        grid_refinement_catalogs=tuple(grid_catalogs),
        grid_refinement=refinement,
        reference_cell_sensitivity=reference,
        options=active,
        wall_seconds=elapsed,
    )


__all__ = [
    "PILOT_REFINEMENT_LINEAGE_STAGE",
    "PILOT_REFINEMENT_LINEAGE_OPTIONS_SCHEMA",
    "REFERENCE_CELL_SENSITIVITY_SCHEMA",
    "NaLta300KRefinementLineageOptions",
    "ReferenceCellSensitivityCertificate",
    "NaLta300KRefinementLineagePilot",
    "prepare_na_lta_300k_refinement_lineage_pilot",
]
