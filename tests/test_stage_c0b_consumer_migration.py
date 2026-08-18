"""Focused Stage-C0B consumer-migration regression tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    AtomicDensityOptions,
    AtomicDensitySelection,
    ConsumerSpatialMode,
    DistanceConnectivity,
    FrameCollectionProvenance,
    FrameSemantics,
    FrameworkAtomRole,
    FrameworkDensityOptions,
    FrameworkDynamicsOptions,
    FrameworkDynamicsResources,
    FrameworkMapping,
    FrameworkPathRule,
    PairCutoffRegistry,
    SpatialRegistrationMode,
    build_framework_topology,
    compute_atomic_connectivity,
    prepare_displacement_coordinate_view,
    prepare_plotting_coordinate_view,
    prepare_velocity_translation_view,
)
from mdstats.analysis._displacement_common import prepare_displacement_inputs
from mdstats.analysis._velocity_common import prepare_velocity_inputs
from mdstats.coordinates import RegistrationSpatialPolicy, TranslationMode
from mdstats.plotting.atomic_density import prepare_atomic_density_fields
from mdstats.plotting.density_contracts import DENSE_BACKEND, DensityStorageOptions
from mdstats.plotting.framework_dynamics import prepare_framework_dynamics_scene


def make_collection(
    fractional: np.ndarray,
    *,
    cells: np.ndarray | None = None,
    velocities: np.ndarray | None = None,
    pbc: tuple[bool, bool, bool] = (True, True, True),
) -> AtomisticFrameCollection:
    frac = np.asarray(fractional, dtype=np.float64)
    n_frames, n_atoms, _ = frac.shape
    if cells is None:
        cells = np.repeat((10.0 * np.eye(3))[None, :, :], n_frames, axis=0)
    cells = np.asarray(cells, dtype=np.float64)
    if velocities is None:
        velocities = np.zeros((n_frames, n_atoms, 3), dtype=np.float64)
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=np.asarray([14, 8, 13, 11][:n_atoms], dtype=np.int32),
        masses=np.asarray([28.0, 16.0, 27.0, 23.0][:n_atoms], dtype=np.float64),
        pbc=np.asarray(pbc, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=np.float64) * 0.2,
        cells=cells,
        origins=np.zeros((n_frames, 3), dtype=np.float64),
        fractional_positions=frac,
        velocities=np.asarray(velocities, dtype=np.float64),
        provenance=FrameCollectionProvenance(
            source_format="synthetic-c0b",
            source_files=("synthetic-c0b",),
            velocity_source="native",
            coordinate_normalization="time_unwrapped_fractional",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def base_fractional(n_frames: int = 3) -> np.ndarray:
    one = np.asarray(
        [
            [0.10, 0.10, 0.10],
            [0.20, 0.10, 0.10],
            [0.30, 0.10, 0.10],
            [0.80, 0.50, 0.50],
        ],
        dtype=np.float64,
    )
    return np.repeat(one[None, :, :], n_frames, axis=0)


def framework_mapping() -> FrameworkMapping:
    return FrameworkMapping.from_symbol_roles(
        {
            "Si": FrameworkAtomRole.VERTEX,
            "Al": FrameworkAtomRole.VERTEX,
            "O": FrameworkAtomRole.LINKER,
            "Na": FrameworkAtomRole.SPECTATOR,
        },
        path_rules=(
            FrameworkPathRule.from_symbols(
                "T-O-T", ("O",), edge_kind="oxygen_bridge"
            ),
        ),
    )


def topology_for(collection: AtomisticFrameCollection):
    connectivity = DistanceConnectivity(
        cutoffs=PairCutoffRegistry.from_mapping(
            {("Si", "O"): 2.1, ("Al", "O"): 2.1}
        )
    )
    state = compute_atomic_connectivity(collection, connectivity).states[0]
    return build_framework_topology(state, framework_mapping())


def test_displacement_adapter_is_exact_for_legacy_coordinate_modes_and_drift() -> None:
    n_frames = 4
    cells = np.repeat(np.eye(3)[None, :, :], n_frames, axis=0)
    cells[:, 0, 0] = np.asarray([10.0, 11.0, 12.5, 14.0])
    fractional = base_fractional(n_frames)
    fractional[:, :, 0] += np.arange(n_frames)[:, None] * 0.07
    collection = make_collection(fractional, cells=cells)

    laboratory = prepare_displacement_inputs(collection)
    np.testing.assert_allclose(laboratory.positions, collection.get_positions())

    reference_cell = np.mean(cells, axis=0)
    reference = prepare_displacement_inputs(
        collection,
        coordinate_mode="reference_cell",
        reference_cell="mean",
        drift_mode="center_of_geometry",
        drift_atom_indices=[0, 2],
    )
    manual = fractional @ reference_cell
    manual -= np.mean(manual[:, [0, 2], :], axis=1)[:, None, :]
    np.testing.assert_allclose(reference.positions, manual, rtol=0.0, atol=2.0e-12)
    assert reference.metadata["consumer_migration_stage"] == "C0B"
    assert reference.metadata["scientific_drift_owner"].endswith("consumer_adapters")
    assert isinstance(reference.metadata["consumer_registration_signature"], str)

    direct_view = prepare_displacement_coordinate_view(
        collection,
        coordinate_mode="reference_cell",
        reference_cell=reference_cell,
        reference_cell_mode="mean",
        drift_mode="center_of_geometry",
        drift_atom_indices=[0, 2],
    )
    assert direct_view.registration.policy.spatial_policy is RegistrationSpatialPolicy.REFERENCE_MATERIAL
    np.testing.assert_allclose(direct_view.positions, manual, rtol=0.0, atol=2.0e-12)
    assert not direct_view.positions.flags.writeable
    with pytest.raises(TypeError):
        direct_view.metadata["tamper"] = True


def test_velocity_adapter_preserves_instantaneous_vacf_translation_semantics() -> None:
    velocities = np.zeros((5, 4, 3), dtype=np.float64)
    velocities[:, 0, 0] = 1.0
    velocities[:, 1, 0] = 4.0
    velocities[:, 2, 0] = -2.0
    collection = make_collection(base_fractional(5), velocities=velocities)

    view = prepare_velocity_translation_view(
        collection,
        velocities=velocities,
        drift_mode="center_of_mass",
        drift_atom_indices=[0, 1],
    )
    expected = (28.0 * 1.0 + 16.0 * 4.0) / 44.0
    np.testing.assert_allclose(view.drift_velocity[:, 0], expected)
    np.testing.assert_allclose(view.correction_velocity[:, 0], -expected)
    assert view.policy.translation_mode is TranslationMode.MATCHED_REFERENCE

    bundle = prepare_velocity_inputs(
        collection,
        analysis_name="VACF",
        atom_indices=[0, 1],
        drift_mode="center_of_mass",
        drift_atom_indices=[0, 1],
    )
    np.testing.assert_array_equal(bundle.drift_velocity, view.drift_velocity)
    assert bundle.translation_policy_signature == view.policy.signature
    assert bundle.consumer_registration_signature == view.signature
    assert bundle.scientific_drift_owner.endswith("consumer_adapters")


def test_plotting_adapter_reproduces_all_legacy_spatial_modes() -> None:
    n_frames = 3
    cells = np.asarray(
        [
            np.diag([10.0, 10.0, 10.0]),
            np.diag([12.0, 10.0, 10.0]),
            np.diag([14.0, 10.0, 10.0]),
        ]
    )
    fractional = base_fractional(n_frames)
    fractional[:, :, 0] += np.asarray([0.0, 0.15, 0.30])[:, None]
    collection = make_collection(fractional, cells=cells)
    display = np.mean(cells, axis=0)
    frames = (0, 1, 2)
    framework_atoms = (0, 2)
    framework_fractional = fractional[:, framework_atoms, :]

    material = prepare_plotting_coordinate_view(
        collection,
        frame_indices=frames,
        display_cell=display,
        spatial_mode=ConsumerSpatialMode.MATERIAL,
        framework_atom_indices=framework_atoms,
        framework_fractional_by_frame=framework_fractional,
    )
    np.testing.assert_allclose(material.positions, fractional @ display)

    registered = prepare_plotting_coordinate_view(
        collection,
        frame_indices=frames,
        display_cell=display,
        spatial_mode=ConsumerSpatialMode.FRAMEWORK_REGISTERED,
        framework_atom_indices=framework_atoms,
        framework_fractional_by_frame=framework_fractional,
    )
    drift = np.mean(framework_fractional, axis=1)
    drift -= drift[0]
    expected_registered = (fractional - drift[:, None, :]) @ display
    np.testing.assert_allclose(registered.positions, expected_registered, atol=2.0e-12)

    laboratory = prepare_plotting_coordinate_view(
        collection,
        frame_indices=frames,
        display_cell=display,
        spatial_mode=ConsumerSpatialMode.LABORATORY,
        framework_atom_indices=framework_atoms,
        framework_fractional_by_frame=framework_fractional,
    )
    np.testing.assert_allclose(laboratory.positions, fractional @ cells)

    shifts = np.asarray([[1.0, 0.0, 0.0]])
    np.testing.assert_allclose(
        material.transform_lattice_shifts(shifts, frame_indices=frames),
        np.broadcast_to(shifts[None, :, :], (3, 1, 3)),
    )
    expected_lab_shift = np.asarray(
        [[shift @ cell @ np.linalg.inv(display)] for cell in cells for shift in shifts]
    ).reshape(3, 1, 3)
    np.testing.assert_allclose(
        laboratory.transform_lattice_shifts(shifts, frame_indices=frames),
        expected_lab_shift,
    )


def test_partial_periodicity_compatibility_does_not_preempt_density_preflight() -> None:
    collection = make_collection(base_fractional(2), pbc=(True, True, False))
    view = prepare_plotting_coordinate_view(
        collection,
        frame_indices=(0, 1),
        display_cell=collection.cells[0],
        spatial_mode="material",
        framework_atom_indices=(0, 2),
        framework_fractional_by_frame=collection.fractional_positions[:, [0, 2], :],
    )
    np.testing.assert_allclose(
        view.positions, collection.fractional_positions @ collection.cells[0]
    )
    assert view.registration.policy.spatial_policy is RegistrationSpatialPolicy.PHYSICAL


def test_framework_scene_and_atomic_density_use_the_shared_registration_view() -> None:
    fractional = base_fractional(3)
    fractional[:, :, 0] += np.asarray([0.0, 0.12, 0.24])[:, None]
    collection = make_collection(fractional)
    topology = topology_for(collection)
    scene = prepare_framework_dynamics_scene(
        collection,
        topology,
        options=FrameworkDynamicsOptions(
            registration_mode=SpatialRegistrationMode.FRAMEWORK_REGISTERED
        ),
        framework_density_options=FrameworkDensityOptions(
            grid_shape=(8, 8, 8),
            gaussian_bandwidth=0.40,
            edge_sample_spacing=0.40,
            adaptive_smearing=False,
            storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
        ),
        resources=FrameworkDynamicsResources(
            max_density_voxels=100_000,
            max_density_samples=100_000,
            max_density_component_values=100_000,
            max_density_mesh_cells=100_000,
            max_density_mesh_faces=1_000_000,
        ),
    )
    assert scene.metadata["consumer_migration_stage"] == "C0B"
    assert scene.metadata["scientific_drift_owner"].endswith("consumer_adapters")
    assert scene.metadata["pair_geometry_policy"] == "physical"
    assert isinstance(scene.metadata["consumer_registration_signature"], str)
    assert scene.framework_density_fields is not None
    assert scene.framework_density_fields.vertex_density is not None
    assert scene.framework_density_fields.edge_length_density is not None
    assert (
        scene.framework_density_fields.vertex_density.metadata[
            "consumer_registration_signature"
        ]
        == scene.metadata["consumer_registration_signature"]
    )
    assert (
        scene.framework_density_fields.edge_length_density.metadata[
            "scientific_drift_owner"
        ]
        == "mdstats.coordinates.consumer_adapters"
    )

    display = collection.cells[0]
    framework_fractional = fractional[:, [0, 2], :]
    view = prepare_plotting_coordinate_view(
        collection,
        frame_indices=(0, 1, 2),
        display_cell=display,
        spatial_mode="framework_registered",
        framework_atom_indices=(0, 2),
        framework_fractional_by_frame=framework_fractional,
    )
    drift = np.mean(framework_fractional, axis=1)
    drift -= drift[0]
    options = AtomicDensityOptions(
        grid_shape=(8, 8, 8),
        gaussian_bandwidth=0.40,
        adaptive_smearing=False,
        storage_options=DensityStorageOptions(grid_backend=DENSE_BACKEND),
    )
    common = dict(
        collection=collection,
        frame_indices=(0, 1, 2),
        frame_weights=np.full(3, 1.0 / 3.0),
        display_cell=display,
        registration_mode="framework_registered",
        selections=(AtomicDensitySelection(atom_indices=(3,)),),
        options=options,
        max_fields=2,
        max_total_voxels=10_000,
        max_samples=100,
        max_nonzero_nodes=10_000,
        max_stored_block_values=100_000,
        max_blocks=10_000,
        max_kernel_pairs=1_000_000,
        max_planning_bytes=100_000_000,
        max_workspace_bytes=100_000_000,
        max_cic_contributions=10_000,
    )
    legacy = prepare_atomic_density_fields(
        **common,
        framework_drift=drift,
    )[0]
    migrated = prepare_atomic_density_fields(
        **common,
        framework_drift=np.zeros_like(drift),
        registration_view=view,
    )[0]
    np.testing.assert_allclose(migrated.values, legacy.values, rtol=0.0, atol=5.0e-16)
    assert migrated.metadata["consumer_registration_signature"] == view.signature
    assert migrated.metadata["scientific_drift_owner"].endswith("consumer_adapters")


def test_public_legacy_options_remain_accepted_after_migration() -> None:
    import mdstats

    for name in (
        "ConsumerCoordinateView",
        "VelocityTranslationView",
        "prepare_displacement_coordinate_view",
        "prepare_plotting_coordinate_view",
        "prepare_velocity_translation_view",
    ):
        assert name in mdstats.__all__

    options = FrameworkDynamicsOptions(
        registration_mode="framework_registered",
        display_cell="mean",
    )
    assert options.registration_mode is SpatialRegistrationMode.FRAMEWORK_REGISTERED
    assert options.display_cell == "mean"
    with pytest.raises(ValueError):
        ConsumerSpatialMode("unknown")
