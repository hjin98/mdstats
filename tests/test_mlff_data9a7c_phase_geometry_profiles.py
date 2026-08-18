from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import mdstats

from mdstats.training_data._common import digest
from tests.test_mlff_data5_partition_roles import _build, _policy


def _contracts(
    *,
    phase_kind: mdstats.MaterialPhaseKind,
    geometry: mdstats.MaterialGeometryKind = mdstats.MaterialGeometryKind.BULK,
):
    profile = mdstats.build_single_phase_material_profile(
        profile_id=f"{phase_kind.value}-{geometry.value}",
        phase_kind=phase_kind,
        geometry=geometry,
    )
    return mdstats.build_material_profile_contracts(profile)


def test_phase_defaults_differentiate_crystal_liquid_and_molecular() -> None:
    crystal = mdstats.derive_phase_geometry_selection_plan(
        _contracts(phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID)
    )
    liquid = mdstats.derive_phase_geometry_selection_plan(
        _contracts(phase_kind=mdstats.MaterialPhaseKind.LIQUID)
    )
    molecular = mdstats.derive_phase_geometry_selection_plan(
        _contracts(phase_kind=mdstats.MaterialPhaseKind.MOLECULAR_OR_GAS)
    )
    assert "orientational_order" in crystal.feature_families
    assert "orientational_order" in liquid.feature_families
    assert "orientational_order" not in molecular.feature_families
    assert liquid.local_structure_policy.density_radius_angstrom > crystal.local_structure_policy.density_radius_angstrom
    assert max(liquid.local_structure_policy.radial_centers_angstrom) == 6.0
    assert crystal.observable_recommendation_profiles == ("crystalline_solid",)
    assert liquid.observable_recommendation_profiles == ("liquid",)
    assert mdstats.PhaseGeometrySelectionPlan.from_dict(liquid.to_dict()) == liquid


def test_surface_profile_warns_when_region_groups_are_not_declared() -> None:
    plan = mdstats.derive_phase_geometry_selection_plan(
        _contracts(
            phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
            geometry=mdstats.MaterialGeometryKind.SURFACE,
        )
    )
    assert "surface_region_groups_not_declared" in plan.warning_codes
    assert plan.priority_group_ids == ("all_atoms",)
    assert plan.priority_group_roles[:3] == ("surface", "subsurface", "bulk_like")


def _interface_contracts() -> mdstats.MaterialProfileContracts:
    framework = mdstats.AtomGroupDefinition(
        group_id="framework",
        label="Framework phase",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS,
            atomic_numbers=(8,),
        ),
        phase_ids=("solid",),
        roles=("phase_bulk",),
    )
    salt = mdstats.AtomGroupDefinition(
        group_id="salt",
        label="Liquid phase",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS,
            atomic_numbers=(3,),
        ),
        phase_ids=("liquid",),
        roles=("phase_bulk",),
    )
    interface = mdstats.AtomGroupDefinition(
        group_id="interface_atoms",
        label="Interface atoms",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.COMPOSITE,
            source_group_ids=("framework", "salt"),
            operation=mdstats.AtomGroupSetOperation.UNION,
        ),
        phase_ids=("solid", "liquid"),
        roles=("interface",),
    )
    profile = mdstats.MaterialProfileIdentity(
        profile_id="solid-liquid-interface",
        profile_version="1",
        phases=(
            mdstats.PhaseComponentIdentity(
                phase_id="solid",
                phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
                atom_group_ids=("framework",),
            ),
            mdstats.PhaseComponentIdentity(
                phase_id="liquid",
                phase_kind=mdstats.MaterialPhaseKind.LIQUID,
                atom_group_ids=("salt",),
                chemistry_modifiers=(mdstats.ChemistryModifier.IONIC.value,),
            ),
        ),
        geometry=mdstats.MaterialGeometryKind.INTERFACE,
        chemistry_modifiers=(mdstats.ChemistryModifier.IONIC.value,),
    )
    groups = mdstats.AtomGroupCatalog(
        material_profile_digest=profile.content_digest,
        material_phase_ids=profile.phase_ids,
        groups=(framework, salt, interface),
    )
    return mdstats.build_material_profile_contracts(profile, atom_groups=groups)


def test_interface_composes_phase_profiles_and_prioritizes_interface_groups() -> None:
    contracts = _interface_contracts()
    plan = mdstats.derive_phase_geometry_selection_plan(contracts)
    assert plan.geometry is mdstats.MaterialGeometryKind.INTERFACE
    assert set(plan.phase_kinds) == {"crystalline_solid", "liquid"}
    assert plan.priority_group_ids[0] == "interface_atoms"
    assert set(plan.observable_recommendation_profiles) == {
        "crystalline_solid",
        "liquid",
        "interface",
    }
    recommended = mdstats.recommended_observable_ids_for_material_profile(
        contracts,
        ionic_transport=True,
    )
    assert "structure.rdf" in recommended
    assert "transport.vacf_diffusion" in recommended
    assert "transport.ionic_conductivity" in recommended


def test_data6_threads_phase_geometry_plan_and_filters_molecular_features(tmp_path: Path) -> None:
    sources, frames, data4, _ = _build(tmp_path)
    contracts = _contracts(phase_kind=mdstats.MaterialPhaseKind.MOLECULAR_OR_GAS)
    profiled_data4 = replace(data4, material_profile_contracts=contracts)
    data5 = mdstats.build_data5_partition_bundle(
        sources,
        frames,
        profiled_data4,
        partition_policy=_policy(),
    )
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    bundle = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        profiled_data4,
        data5,
        policy=None,
    )
    assert bundle.phase_geometry_profile_plan is not None
    catalog = bundle.universal_structural_features[0]
    assert catalog.policy.phase_geometry_plan_digest == bundle.phase_geometry_profile_plan.content_digest
    assert all(
        not name.startswith("bond_orientational_")
        for name in catalog.atomic_environment_descriptors[0].feature_names
    )
    assert mdstats.Data6FeatureBundle.from_dict(bundle.to_dict()) == bundle


def test_data6_v2_bundle_without_phase_geometry_plan_remains_readable(tmp_path: Path) -> None:
    sources, frames, data4, data5 = _build(tmp_path)
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    current = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        policy=mdstats.Data6Policy(
            build_universal_structural_features=False,
            build_lta_selection_features=False,
        ),
    )
    payload = {
        key: value
        for key, value in current.to_dict().items()
        if key not in {"content_digest", "phase_geometry_profile_plan"}
    }
    payload["schema"] = "mdstats.data6-feature-bundle.v2"
    payload["parser_version"] = "0.20.48a0"
    payload["content_digest"] = digest(payload)
    restored = mdstats.Data6FeatureBundle.from_dict(payload)
    assert restored.phase_geometry_profile_plan is None
    assert restored.universal_structural_features == ()


def test_plan_tampering_and_foreign_policy_digest_fail_closed(tmp_path: Path) -> None:
    contracts = _contracts(phase_kind=mdstats.MaterialPhaseKind.LIQUID)
    plan = mdstats.derive_phase_geometry_selection_plan(contracts)
    payload = plan.to_dict()
    payload["feature_families"] = ["pair_distance"]
    with pytest.raises(mdstats.TrainingDataSerializationError):
        mdstats.PhaseGeometrySelectionPlan.from_dict(payload)

    sources, frames, data4, _ = _build(tmp_path)
    profiled_data4 = replace(data4, material_profile_contracts=contracts)
    data5 = mdstats.build_data5_partition_bundle(
        sources,
        frames,
        profiled_data4,
        partition_policy=_policy(),
    )
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    foreign_policy = mdstats.UniversalStructuralSelectionPolicy(
        phase_geometry_plan_digest=digest({"foreign": True})
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="different phase/geometry plan"):
        mdstats.build_data6_feature_bundle(
            sources,
            frames,
            frame_data,
            profiled_data4,
            data5,
            universal_structural_policy=foreign_policy,
        )
