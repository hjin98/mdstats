from __future__ import annotations

from dataclasses import replace

import numpy as np

from mdstats import (
    GAUSSIAN_SIGMA_BROADENING,
    DensitySourceProvenance,
    MeshSimplificationOptions,
    PeriodicWeightedSamples3D,
    pack_sparse_reference_blocks,
    prepare_sparse_canonical_density_reference,
    prepare_sparse_density_mesh,
)


def _field():
    positions = np.asarray([[0.48, 0.51, 0.54]], dtype=np.float64)
    samples = PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=np.ones(1, dtype=np.float64),
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=(0,)
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )
    reference = prepare_sparse_canonical_density_reference(
        samples,
        grid_shape=(24, 24, 24),
        display_cell=np.eye(3) * 6.0,
        gaussian_bandwidth=0.35,
        field_key="repair-test",
        label="repair test",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=500_000_000,
    )
    return pack_sparse_reference_blocks(
        reference,
        block_shape=(8, 8, 8),
        max_stored_block_values=5_000_000,
        max_planning_bytes=500_000_000,
    )


def test_invalid_local_presimplified_tiled_mesh_retries_without_it(monkeypatch) -> None:
    import mdstats.plotting.density_tiled_mesh as tiled

    original = tiled.extract_tiled_density_mesh
    calls: list[bool] = []

    def wrapped(field, plan, *, options=None, local_simplification_options=None):
        local_enabled = bool(
            local_simplification_options is not None
            and local_simplification_options.local_presimplification
        )
        calls.append(local_enabled)
        result = original(
            field,
            plan,
            options=options,
            local_simplification_options=local_simplification_options,
        )
        if local_enabled:
            # Simulate the production failure: tile-local reduction left one
            # internal edge with incidence one after global reconciliation.
            return replace(result, faces=result.faces[:-1])
        return result

    monkeypatch.setattr(tiled, "extract_tiled_density_mesh", wrapped)
    surface = prepare_sparse_density_mesh(
        _field(),
        0.8,
        simplification_options=MeshSimplificationOptions(
            enabled=False,
            local_presimplification=True,
        ),
    )
    assert calls[:2] == [True, False]
    assert surface.render_kind == "mesh"
    assert surface.mesh is not None
    assert surface.fallback_mode == "tiled_no_local_simplification"
    assert surface.mesh.topology.interior_edge_incidence_failures == 0
    assert surface.mesh.topology.unpaired_boundary_edge_count == 0
    attempts = surface.mesh.metadata["mesh_repair_attempts"]
    assert attempts[0]["valid"] is False
    assert attempts[1]["valid"] is True


def test_persistently_invalid_tiled_mesh_falls_back_to_coarse_recontour(monkeypatch) -> None:
    import mdstats.plotting.density_tiled_mesh as tiled

    original = tiled.extract_tiled_density_mesh

    def always_open(field, plan, *, options=None, local_simplification_options=None):
        result = original(
            field,
            plan,
            options=options,
            local_simplification_options=local_simplification_options,
        )
        return replace(result, faces=result.faces[:-1])

    monkeypatch.setattr(tiled, "extract_tiled_density_mesh", always_open)
    surface = prepare_sparse_density_mesh(
        _field(),
        0.8,
        simplification_options=MeshSimplificationOptions(
            enabled=False,
            local_presimplification=True,
        ),
    )
    assert surface.render_kind == "mesh"
    assert surface.mesh is not None
    assert surface.fallback_mode == "coarse_recontour"
    assert surface.mesh.topology.interior_edge_incidence_failures == 0
    assert surface.mesh.topology.unpaired_boundary_edge_count == 0
    assert surface.mesh.metadata["mesh_repair_fallback_mode"] == "coarse_recontour"
