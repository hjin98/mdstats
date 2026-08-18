from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from mdstats.plotting import (
    DensitySourceProvenance,
    MultilevelFieldResearchProfile,
    MultilevelResearchDecision,
    MultilevelResearchOptions,
    PeriodicScalarField3D,
    PeriodicWeightedSamples3D,
    decide_multilevel_research,
    pack_sparse_reference_blocks,
    prepare_sparse_canonical_density_optimized,
    profile_multilevel_field,
)
from mdstats.plotting.graph_errors import GraphComplexityError


def lta_cell(scale: float = 1.0) -> np.ndarray:
    return scale * np.asarray(
        [
            [3.0, 0.0, 0.0],
            [1.5, 2.598076211353316, 0.0],
            [1.5, 0.8660254037844386, 2.449489742783178],
        ],
        dtype=np.float64,
    )


def sample_batch(positions: np.ndarray) -> PeriodicWeightedSamples3D:
    positions = np.asarray(positions, dtype=np.float64)
    return PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=np.full(positions.shape[0], 1.0 / positions.shape[0]),
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy",
            atom_indices=tuple(range(positions.shape[0])),
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )


def sparse_field(
    positions: np.ndarray,
    *,
    shape: tuple[int, int, int] = (32, 32, 32),
    sigma: float = 0.32,
    block_shape: tuple[int, int, int] = (16, 16, 16),
    field_key: str = "sparse",
):
    batch = sample_batch(positions)
    reference = prepare_sparse_canonical_density_optimized(
        batch,
        grid_shape=shape,
        display_cell=lta_cell(3.0),
        gaussian_bandwidth=sigma,
        field_key=field_key,
        label=field_key,
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
        cache_stencil_supports=False,
    )
    return pack_sparse_reference_blocks(
        reference,
        block_shape=block_shape,
        selected_atom_indices=tuple(range(positions.shape[0])),
    )


def dense_field(values: np.ndarray, *, field_key: str) -> PeriodicScalarField3D:
    values = np.asarray(values, dtype=np.float64)
    voxel_volume = 1.0 / float(values.size)
    total = float(np.sum(values, dtype=np.float64)) * voxel_volume
    return PeriodicScalarField3D(
        field_key=field_key,
        label=field_key,
        values=values,
        display_cell=np.eye(3),
        total_measure=total,
        selected_atom_indices=(0,),
        gaussian_bandwidth=0.0,
        metadata={
            "smoothing_operator": "discrete_periodized_v1",
            "broadening_metric": "gaussian_sigma_v1",
            "physical_units": "angstrom^-3",
        },
    )


def test_multilevel_options_json_round_trip() -> None:
    options = MultilevelResearchOptions(
        coarsening_factors=(2, 4),
        fine_mass_fractions=(0.9, 0.97),
        block_shapes=((4, 4, 4), (8, 8, 8)),
        metadata={"purpose": "test"},
    )
    restored = MultilevelResearchOptions.from_json_dict(options.to_json_dict())
    assert restored == options


def test_uniform_broad_field_has_exact_coarse_surrogate() -> None:
    field = dense_field(np.ones((16, 16, 16)), field_key="broad")
    profile = profile_multilevel_field(
        field,
        options=MultilevelResearchOptions(
            coarsening_factors=(2,),
            fine_mass_fractions=(0.9,),
            block_shapes=((4, 4, 4),),
        ),
    )
    candidate = profile.best_candidate
    assert profile.support_regime == "broad"
    assert profile.single_level_sufficient
    assert candidate is not None
    assert candidate.all_phases_pass
    assert candidate.worst_relative_l1_error == 0.0
    assert candidate.worst_relative_linf_error == 0.0
    assert candidate.worst_mass_error == 0.0


def test_localized_sparse_profile_is_deterministic_and_mass_conservative() -> None:
    positions = np.asarray([[0.21, 0.31, 0.41], [0.24, 0.34, 0.44]])
    field = sparse_field(positions, shape=(48, 48, 48), field_key="localized")
    options = MultilevelResearchOptions(
        coarsening_factors=(2,),
        fine_mass_fractions=(0.9, 0.95),
        block_shapes=((4, 4, 4), (8, 8, 8), (16, 16, 16)),
    )
    first = profile_multilevel_field(field, options=options)
    second = profile_multilevel_field(field, options=options)
    assert first.to_json_dict(include_phases=True) == second.to_json_dict(include_phases=True)
    restored = MultilevelFieldResearchProfile.from_json_dict(
        json.loads(json.dumps(first.to_json_dict(include_phases=True), sort_keys=True))
    )
    assert restored == first
    assert first.support_regime == "localized"
    assert first.single_level_sufficient
    assert first.candidates
    for candidate in first.candidates:
        assert candidate.phase_count == 8
        assert candidate.worst_mass_error <= 5.0e-13


def test_phase_sweep_reports_every_periodic_offset() -> None:
    field = sparse_field(
        np.asarray([[0.01, 0.02, 0.03], [0.99, 0.98, 0.97]]),
        field_key="boundary",
    )
    options = MultilevelResearchOptions(
        coarsening_factors=(2, 4),
        fine_mass_fractions=(0.95,),
        block_shapes=((8, 8, 8),),
    )
    profile = profile_multilevel_field(field, options=options)
    counts = {item.coarsening_factor: item.phase_count for item in profile.candidates}
    assert counts == {2: 8, 4: 64}
    for candidate in profile.candidates:
        assert len({item.phase for item in candidate.phase_profiles}) == candidate.phase_count


def test_nondivisible_coarsening_factor_is_skipped() -> None:
    field = dense_field(np.ones((18, 16, 16)), field_key="nondivisible")
    profile = profile_multilevel_field(
        field,
        options=MultilevelResearchOptions(
            coarsening_factors=(2, 4),
            fine_mass_fractions=(0.9,),
            block_shapes=((4, 4, 4),),
        ),
    )
    assert {item.coarsening_factor for item in profile.candidates} == {2}


def test_profile_node_limit_fails_before_candidate_work() -> None:
    field = dense_field(np.ones((16, 16, 16)), field_key="limit")
    with pytest.raises(GraphComplexityError, match="max_profile_nodes"):
        profile_multilevel_field(
            field,
            options=MultilevelResearchOptions(max_profile_nodes=100),
        )


def test_decision_requires_localized_and_broad_coverage() -> None:
    field = sparse_field(np.asarray([[0.2, 0.3, 0.4]]), field_key="only_local")
    profile = profile_multilevel_field(
        field,
        options=MultilevelResearchOptions(
            coarsening_factors=(2,),
            fine_mass_fractions=(0.95,),
        ),
    )
    decision = decide_multilevel_research([profile])
    assert decision.outcome == "insufficient_evidence"


def test_representative_efficient_backends_retain_single_level() -> None:
    options = MultilevelResearchOptions(
        coarsening_factors=(2,),
        fine_mass_fractions=(0.9, 0.95),
    )
    localized = profile_multilevel_field(
        sparse_field(
            np.asarray([[0.2, 0.3, 0.4]]),
            shape=(48, 48, 48),
            field_key="localized",
        ),
        options=options,
    )
    broad = profile_multilevel_field(
        dense_field(np.ones((16, 16, 16)), field_key="broad"),
        options=options,
    )
    decision = decide_multilevel_research([localized, broad], options=options)
    assert decision.outcome == "retain_single_level"
    assert decision.insufficient_profile_count == 0
    restored = MultilevelResearchDecision.from_json_dict(
        json.loads(json.dumps(decision.to_json_dict(), sort_keys=True))
    )
    assert restored == decision


def test_policy_can_request_future_multilevel_specification() -> None:
    options = MultilevelResearchOptions(
        coarsening_factors=(2,),
        fine_mass_fractions=(0.95,),
        block_shapes=((4, 4, 4),),
        minimum_incremental_storage_reduction=1.1,
        minimum_adoption_cases=2,
    )
    localized = profile_multilevel_field(
        sparse_field(
            np.asarray([[0.2, 0.3, 0.4]]),
            shape=(48, 48, 48),
            field_key="localized",
        ),
        options=options,
    )
    broad = profile_multilevel_field(
        dense_field(np.ones((16, 16, 16)), field_key="broad"), options=options
    )
    base_candidate = localized.candidates[0]
    qualifying_candidate = replace(
        base_candidate,
        all_phases_pass=True,
        meets_incremental_reduction_gate=True,
    )
    first = replace(
        localized,
        field_key="intermediate_a",
        support_regime="intermediate",
        single_level_sufficient=False,
        candidates=(qualifying_candidate,),
        best_candidate_index=0,
    )
    second = replace(first, field_key="intermediate_b")
    decision = decide_multilevel_research(
        [first, second, broad, localized], options=options
    )
    assert decision.outcome == "write_multilevel_specification"
