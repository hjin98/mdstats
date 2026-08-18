"""Focused tests for the analysis-owned observable dispatch surface."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.analysis.observable_validation import (
    CollectionRequirement,
    ObservableAnalysisCall,
    ObservableAnalysisRecipe,
    ObservableDependencyError,
    ObservableParameterError,
    ObservableRequirementError,
    execute_observable_recipe,
    get_observable_capability,
    list_observable_capabilities,
)


def make_collection(*, scale: float = 1.0, velocities: bool = True) -> AtomisticFrameCollection:
    n_frames = 16
    times = np.arange(n_frames, dtype=np.float64) * 0.1
    cells = np.repeat((np.eye(3) * 12.0)[None, :, :], n_frames, axis=0)
    positions = np.zeros((n_frames, 3, 3), dtype=np.float64)
    positions[:, 0, 0] = -1.0
    positions[:, 1, 0] = 0.0
    positions[:, 2, 0] = 1.0
    positions[:, 0, 1] = scale * 0.02 * np.sin(times)
    positions[:, 2, 1] = -scale * 0.02 * np.sin(times)
    velocity_values = np.gradient(positions, times, axis=0) if velocities else None
    fractional = np.einsum("tni,tij->tnj", positions, np.linalg.inv(cells), optimize=True)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.array([8, 11, 8], dtype=np.int32),
        masses=np.array([15.999, 22.990, 15.999], dtype=np.float64),
        pbc=np.array([True, True, True]),
        steps=np.arange(n_frames, dtype=np.int64),
        times=times,
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=fractional,
        velocities=velocity_values,
        provenance=FrameCollectionProvenance(
            source_format="ase-structure-collection",
            source_files=("synthetic",),
            velocity_source="native" if velocities else "unavailable",
            coordinate_normalization="native_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def make_recipe() -> ObservableAnalysisRecipe:
    return ObservableAnalysisRecipe(
        recipe_id="structural-and-dynamical-smoke",
        calls=(
            ObservableAnalysisCall(
                "na_o_rdf",
                "structure.rdf",
                {"species_a": "Na", "species_b": "O", "r_max": 4.0, "n_bins": 40},
            ),
            ObservableAnalysisCall(
                "na_o_coordination",
                "structure.coordination",
                {"species_a": "Na", "species_b": "O", "cutoff": 1.5},
            ),
            ObservableAnalysisCall(
                "o_na_o_angle",
                "structure.bond_angle",
                {
                    "triplet": ["O", "Na", "O"],
                    "cutoffs": [{"pair": ["Na", "O"], "radius": 1.5}],
                    "bins": 18,
                },
            ),
            ObservableAnalysisCall(
                "connectivity",
                "topology.atomic_connectivity",
                {
                    "definition": {
                        "kind": "distance",
                        "cutoffs": [{"pair": ["Na", "O"], "radius": 1.5}],
                    }
                },
            ),
            ObservableAnalysisCall(
                "connectivity_stats",
                "topology.atomic_statistics",
                input_bindings={"catalog": "connectivity"},
            ),
            ObservableAnalysisCall(
                "oxygen_msd",
                "dynamics.msd",
                {"species": "O", "max_lag": 5, "backend": "direct"},
            ),
            ObservableAnalysisCall(
                "oxygen_vacf",
                "dynamics.vacf",
                {"species": "O", "max_lag": 5, "backend": "direct"},
            ),
            ObservableAnalysisCall(
                "oxygen_diffusion",
                "transport.vacf_diffusion",
                {"dimensions": 3},
                input_bindings={"vacf": "oxygen_vacf"},
            ),
            ObservableAnalysisCall(
                "oxygen_spectrum",
                "spectrum.velocity_welch",
                {"species": "O", "segment_length": 16, "overlap": 0, "window": "boxcar"},
            ),
            ObservableAnalysisCall(
                "oxygen_vdos",
                "spectrum.vdos",
                input_bindings={"spectrum": "oxygen_spectrum"},
            ),
        ),
    )


def test_registry_reports_owner_requirements_and_versioned_schema() -> None:
    capabilities = list_observable_capabilities()
    assert len(capabilities) == 22
    rdf = get_observable_capability("structure.rdf")
    assert rdf.owner_module == "mdstats.analysis.rdf"
    assert CollectionRequirement.POSITIONS_AND_CELLS in rdf.collection_requirements
    assert rdf.owner_manual == "structural-observables-architecture"
    assert rdf.owner_manual_source_path.endswith("structural_observables_architecture.md")
    assert rdf.owner_manual_uri.startswith("mdstats-doc://")
    assert rdf.parameter_schema_version == "v1"
    assert rdf.owner_api_version.startswith("python-source-sha256:")
    assert "neighbor_search_options" not in rdf.supported_arguments
    assert len(rdf.content_digest) == 64


def test_every_capability_has_machine_checkable_contract() -> None:
    for capability in list_observable_capabilities():
        assert capability.supported_arguments
        assert set(capability.required_arguments).issubset(capability.supported_arguments)
        assert set(capability.dependency_arguments).issubset(capability.supported_arguments)
        assert capability.result_type_hint
        payload = capability.to_dict()
        assert payload["content_digest"] == capability.content_digest


def test_recipe_round_trip_and_tamper_rejection() -> None:
    recipe = make_recipe()
    restored = ObservableAnalysisRecipe.from_dict(recipe.to_dict())
    assert restored.content_digest == recipe.content_digest
    payload = recipe.to_dict()
    payload["calls"][0]["parameters"]["n_bins"] = 41
    with pytest.raises(ObservableParameterError, match="digest mismatch"):
        ObservableAnalysisRecipe.from_dict(payload)


def test_recipe_rejects_forward_self_unknown_and_missing_dependencies() -> None:
    with pytest.raises(ObservableDependencyError, match="forward dependencies"):
        ObservableAnalysisRecipe(
            recipe_id="forward",
            calls=(
                ObservableAnalysisCall("vdos", "spectrum.vdos", input_bindings={"spectrum": "spectrum"}),
                ObservableAnalysisCall("spectrum", "spectrum.velocity_welch", {"species": "O"}),
            ),
        )
    with pytest.raises(ObservableDependencyError, match="depend on itself"):
        ObservableAnalysisRecipe(
            recipe_id="self",
            calls=(ObservableAnalysisCall("x", "spectrum.vdos", input_bindings={"spectrum": "x"}),),
        )
    with pytest.raises(ObservableDependencyError, match="unknown calls"):
        ObservableAnalysisRecipe(
            recipe_id="unknown",
            calls=(ObservableAnalysisCall("x", "spectrum.vdos", input_bindings={"spectrum": "missing"}),),
        )
    with pytest.raises(ObservableParameterError, match="missing required arguments"):
        ObservableAnalysisRecipe(
            recipe_id="missing",
            calls=(ObservableAnalysisCall("angle", "structure.bond_angle", {"triplet": ["O", "Na", "O"]}),),
        )



def test_native_result_arguments_must_use_input_bindings() -> None:
    with pytest.raises(ObservableParameterError, match="must be supplied by input_bindings"):
        ObservableAnalysisRecipe(
            recipe_id="bad-native-result",
            calls=(
                ObservableAnalysisCall(
                    "coord",
                    "structure.coordination",
                    {"species_a": "Na", "species_b": "O", "rdf_result": {}},
                ),
            ),
        )


def test_preflight_rejects_missing_collection_capability() -> None:
    recipe = ObservableAnalysisRecipe(
        recipe_id="vacf",
        calls=(ObservableAnalysisCall("vacf", "dynamics.vacf", {"species": "O"}),),
    )
    collection = make_collection()
    collection.velocities = None
    with pytest.raises(ObservableRequirementError, match="velocities"):
        execute_observable_recipe(collection, recipe)


def test_structural_and_dynamical_recipe_executes_through_owner_modules() -> None:
    result = execute_observable_recipe(make_collection(), make_recipe())
    assert result.results["na_o_coordination"].mean == pytest.approx(2.0)
    assert result.results["o_na_o_angle"].n_angles == 16
    assert len(result.results["connectivity"].states) == 1
    assert result.results["connectivity_stats"].axis.n_frames == 16
    assert result.results["oxygen_msd"].msd.shape[0] == 6
    assert result.results["oxygen_vacf"].scalar_mean.shape[0] == 6
    assert result.results["oxygen_diffusion"].running_diffusion_a2_per_ps.shape[0] == 6
    assert result.results["oxygen_vdos"].total.shape == result.results["oxygen_spectrum"].scalar_spectrum.shape
    assert set(result.warnings_by_call) == {call.call_id for call in make_recipe().calls}
    assert result.runtime_identity["observable_api_version"].endswith("v2")
    assert result.runtime_identity["mdstats_executing_version"] == "0.20.99a0"
    assert len(result.runtime_identity["executing_module_sha256"]) == 64
    assert all(len(value) == 64 for value in result.capability_digests.values())
    assert set(result.result_identities) == {call.call_id for call in make_recipe().calls}
    assert all(len(value.content_digest) == 64 for value in result.result_identities.values())
    assert set(result.duration_seconds_by_call) == {call.call_id for call in make_recipe().calls}
    assert all(value >= 0.0 for value in result.duration_seconds_by_call.values())


def test_all_registered_capabilities_execute_through_standardized_dependency_chains() -> None:
    """Exercise every registry binding, including nested species-diffusion inputs."""

    recipe = ObservableAnalysisRecipe(
        recipe_id="all-registered-capabilities-smoke",
        calls=(
            ObservableAnalysisCall("rdf", "structure.rdf", {"species_a": "Na", "species_b": "O", "r_max": 4.0, "n_bins": 40}),
            ObservableAnalysisCall("coord", "structure.coordination", {"species_a": "Na", "species_b": "O", "cutoff": 1.5}),
            ObservableAnalysisCall("angle", "structure.bond_angle", {"triplet": ["O", "Na", "O"], "cutoffs": [{"pair": ["Na", "O"], "radius": 1.5}], "bins": 18}),
            ObservableAnalysisCall("connectivity", "topology.atomic_connectivity", {"definition": {"kind": "distance", "cutoffs": [{"pair": ["Na", "O"], "radius": 1.5}]}}),
            ObservableAnalysisCall("topology_stats", "topology.atomic_statistics", input_bindings={"catalog": "connectivity"}),
            ObservableAnalysisCall("o_msd", "dynamics.msd", {"species": "O", "max_lag": 8, "backend": "direct"}),
            ObservableAnalysisCall("o_vacf", "dynamics.vacf", {"species": "O", "max_lag": 8, "backend": "direct"}),
            ObservableAnalysisCall("na_vacf", "dynamics.vacf", {"species": "Na", "max_lag": 8, "backend": "direct"}),
            ObservableAnalysisCall("vacf_spectrum", "spectrum.vacf", input_bindings={"vacf": "o_vacf"}),
            ObservableAnalysisCall("welch", "spectrum.velocity_welch", {"species": "O", "segment_length": 16, "overlap": 0, "window": "boxcar"}),
            ObservableAnalysisCall("welch_vdos", "spectrum.vdos", input_bindings={"spectrum": "welch"}),
            ObservableAnalysisCall("o_running_d", "transport.vacf_diffusion", {"dimensions": 3}, input_bindings={"vacf": "o_vacf"}),
            ObservableAnalysisCall("na_running_d", "transport.vacf_diffusion", {"dimensions": 3}, input_bindings={"vacf": "na_vacf"}),
            ObservableAnalysisCall("o_d", "transport.diffusion_plateau", {"time_range_ps": [0.1, 0.8], "minimum_points": 8}, input_bindings={"running": "o_running_d"}),
            ObservableAnalysisCall("na_d", "transport.diffusion_plateau", {"time_range_ps": [0.1, 0.8], "minimum_points": 8}, input_bindings={"running": "na_running_d"}),
            ObservableAnalysisCall("msd_from_vacf", "dynamics.msd_from_vacf", input_bindings={"vacf": "o_vacf"}),
            ObservableAnalysisCall("msd_vacf_compare", "transport.msd_vacf_comparison", {"msd_fit_range_ps": [0.1, 0.8]}, input_bindings={"msd": "o_msd", "vacf_diffusion": "o_d"}),
            ObservableAnalysisCall("van_hove", "dynamics.self_van_hove", {"species": "O", "max_lag": 4, "r_max": 1.0, "n_bins": 20}),
            ObservableAnalysisCall("non_gaussian", "dynamics.non_gaussian", {"species": "O", "max_lag": 4}),
            ObservableAnalysisCall("self_isf", "dynamics.self_intermediate_scattering", {"species": "O", "q_magnitudes": [1.0], "max_lag": 4}),
            ObservableAnalysisCall("charge_current", "transport.charge_current", {"species_charges": {"O": -1.0, "Na": 2.0}, "species_groups": {"O": "O", "Na": "Na"}}),
            ObservableAnalysisCall("current_corr", "transport.current_correlation", {"max_lag": 8, "backend": "direct"}, input_bindings={"current": "charge_current"}),
            ObservableAnalysisCall("conductivity_running", "transport.ionic_conductivity", {"temperature_k": 700.0}, input_bindings={"correlation": "current_corr"}),
            ObservableAnalysisCall("conductivity", "transport.conductivity_plateau", {"time_range_ps": [0.1, 0.8], "minimum_points": 8}, input_bindings={"running": "conductivity_running"}),
            ObservableAnalysisCall("nernst_einstein", "transport.nernst_einstein_comparison", input_bindings={"conductivity": "conductivity", "species_diffusion": {"O": "o_d", "Na": "na_d"}}),
        ),
    )
    result = execute_observable_recipe(make_collection(), recipe)
    exercised = {call.observable_id for call in recipe.calls}
    assert exercised == {item.observable_id for item in list_observable_capabilities()}
    assert result.results["nernst_einstein"].group_names == ("Na", "O")
    assert result.results["conductivity"].n_points == 8


def test_preflight_rejects_nonmonotonic_time_and_singular_cells() -> None:
    vacf_recipe = ObservableAnalysisRecipe(
        recipe_id="vacf-invalid-time",
        calls=(ObservableAnalysisCall("vacf", "dynamics.vacf", {"species": "O"}),),
    )
    collection = make_collection()
    collection.times[3] = collection.times[2]
    with pytest.raises(ObservableRequirementError, match="strictly increasing"):
        execute_observable_recipe(collection, vacf_recipe)

    rdf_recipe = ObservableAnalysisRecipe(
        recipe_id="rdf-singular-cell",
        calls=(ObservableAnalysisCall("rdf", "structure.rdf", {"r_max": 4.0}),),
    )
    collection = make_collection()
    collection.cells[0, 2] = collection.cells[0, 1]
    with pytest.raises(ObservableRequirementError, match="nonsingular"):
        execute_observable_recipe(collection, rdf_recipe)
