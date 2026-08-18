from __future__ import annotations

from pathlib import Path

import numpy as np
from ase.io import read

import mdstats
from mdstats import AtomisticFrameCollection, FrameCollectionProvenance
from mdstats.analysis.density import (
    NaLta300KDensityAttractorPilotOptions,
    NaLta300KRefinementLineageOptions,
    NaLta300KStructuralTemporalOptions,
    PilotOverallStatus,
    SpeciesDensityResourcePolicy,
    StructuralMappingCatalog,
    TemporalAssignmentOptions,
    prepare_na_lta_300k_structural_temporal_pilot,
)


def _collection() -> AtomisticFrameCollection:
    atoms = read(Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR")
    numbers = np.asarray(atoms.numbers, dtype=np.int32)
    masses = np.asarray(atoms.get_masses(), dtype=np.float64)
    cell = np.asarray(atoms.cell.array, dtype=np.float64)
    base_frac = np.asarray(atoms.get_scaled_positions(wrap=True), dtype=np.float64)
    n_frames = 10
    frac = np.repeat(base_frac[None, :, :], n_frames, axis=0)
    drift = np.arange(n_frames, dtype=float)[:, None, None] * np.array([1.0e-4, -8.0e-5, 6.0e-5])
    frac += drift
    # Small framework vibration and larger Na motion without changing topology.
    phase = np.arange(n_frames, dtype=float)[:, None]
    frac[:, :144, 0] += 2.0e-5 * np.sin(phase)
    frac[:, 144:, 1] += 5.0e-4 * np.sin(phase + np.arange(24)[None, :])
    rng = np.random.default_rng(20260726)
    return AtomisticFrameCollection(
        frame_semantics="trajectory",
        frame_ids=np.arange(n_frames),
        atomic_numbers=numbers,
        masses=masses,
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames),
        times=np.arange(n_frames, dtype=float) * 0.001,
        cells=np.repeat(cell[None, :, :], n_frames, axis=0),
        origins=np.zeros((n_frames, 3)),
        fractional_positions=frac,
        velocities=np.zeros((n_frames, numbers.size, 3)),
        forces=rng.normal(scale=0.1, size=(n_frames, numbers.size, 3)),
        temperatures=np.full(n_frames, 300.0),
        provenance=FrameCollectionProvenance(
            source_format="vasp-vasprun-xml",
            source_files=("vasprun.xml",),
            velocity_source="source",
            coordinate_normalization="wrapped_fractional",
            stress_source="unavailable",
            units_source="VASP native units",
        ),
    )


def _raw_file(tmp_path: Path) -> Path:
    path = tmp_path / "vasprun.xml"
    path.write_bytes(b"synthetic Na-LTA S3 source\n")
    return path


def _s1_options() -> NaLta300KDensityAttractorPilotOptions:
    return NaLta300KDensityAttractorPilotOptions(
        representative_frame_count=5,
        grid_shape=(8, 8, 8),
        kernel_sigma_angstrom=0.8,
        density_query_batch_size=64,
        density_sample_batch_size=64,
        relative_image_tolerance=1.0e-8,
        maximum_image_radius=2,
    )


def _s2_options() -> NaLta300KRefinementLineageOptions:
    return NaLta300KRefinementLineageOptions(
        bandwidth_sigmas_angstrom=(0.7, 0.8, 0.9),
        central_bandwidth_sigma_angstrom=0.8,
        lineage_grid_shape=(6, 6, 6),
        refinement_grid_shapes=((6, 6, 6), (8, 8, 8)),
        minimum_lineage_overlap=0.0,
        minimum_refinement_basin_overlap=0.0,
        density_query_batch_size=64,
        density_sample_batch_size=64,
        relative_image_tolerance=1.0e-8,
        maximum_image_radius=2,
    )


def test_s3_options_and_public_exports_round_trip():
    options = NaLta300KStructuralTemporalOptions(
        maximum_ring_association_distance_angstrom=3.0,
        temporal_options=TemporalAssignmentOptions(minimum_decorrelation_samples=4),
    )
    assert NaLta300KStructuralTemporalOptions.from_dict(options.to_dict()) == options
    assert mdstats.PILOT_STRUCTURAL_TEMPORAL_STAGE == "11E8a-S3"
    assert "NaLta300KStructuralTemporalPilot" in mdstats.__all__


def test_s3_maps_packaged_rings_and_transfers_partition_to_full_temporal_catalog(tmp_path: Path):
    result = prepare_na_lta_300k_structural_temporal_pilot(
        _collection(),
        _raw_file(tmp_path),
        options=NaLta300KStructuralTemporalOptions(
            maximum_ring_association_distance_angstrom=4.0,
            minimum_unique_margin_angstrom=0.0,
            temporal_options=TemporalAssignmentOptions(
                minimum_decorrelation_samples=4,
                maximum_autocorrelation_lag=4,
                stride_factors=(1, 2),
            ),
        ),
        s2_options=_s2_options(),
        s1_options=_s1_options(),
        density_resources=SpeciesDensityResourcePolicy(max_image_terms=50_000_000),
    )
    mapping = result.structural_mapping
    assert len(mapping.ring_geometries) == 82
    assert dict(mapping.metadata["ring_size_counts"]) == {"4": 36, "6": 40, "8": 6}
    assert mapping.metadata["serrated_polygon_mapping"] is True
    assert mapping.metadata["circle_or_ellipse_substitution"] is False
    assert StructuralMappingCatalog.from_dict(mapping.to_dict()).signature == mapping.signature
    assert result.temporal_assignment.metadata["partition_transfer_performed"] is True
    assert result.temporal_assignment.membership.raw_classification.size == 10 * 24
    assert result.temporal_assignment.sample_catalog_signature == result.s2_pilot.s1_pilot.source_bootstrap.na_samples.signature
    assert result.report.overall_status is PilotOverallStatus.BLOCKED_MISSING_REQUIRED_EVIDENCE
    assert result.report.missing_required_evidence == (
        "force_density_agreement",
        "transition_paths",
    )
    assert result.report.metadata["s3_complete"] is True
