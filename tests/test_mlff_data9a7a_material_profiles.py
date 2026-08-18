from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

import pytest

import mdstats
from mdstats.training_data._common import digest
from tests.test_mlff_data4_raw_features_events import _site_catalogs


def _solid_profile() -> mdstats.MaterialProfileIdentity:
    return mdstats.build_single_phase_material_profile(
        profile_id="generic-crystal",
        phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
        chemistry_modifiers=(mdstats.ChemistryModifier.IONIC,),
    )


def test_single_phase_contract_defaults_are_generic_and_round_trip() -> None:
    profile = _solid_profile()
    contracts = mdstats.build_material_profile_contracts(profile)
    assert profile.geometry is mdstats.MaterialGeometryKind.BULK
    assert profile.extensions == ()
    assert contracts.atom_groups.group_ids == ("all_atoms",)
    assert {axis.axis_id for axis in contracts.condition_axes.axes} == {
        "composition", "pressure", "regime", "temperature_kelvin"
    }
    assert {axis.axis_id for axis in contracts.independence_axes.axes} == {
        "initial_configuration", "trajectory_run"
    }
    assert mdstats.MaterialProfileContracts.from_dict(contracts.to_dict()) == contracts


def test_explicit_user_declaration_is_required_for_identity_evidence() -> None:
    phase = mdstats.PhaseComponentIdentity(
        phase_id="material",
        phase_kind=mdstats.MaterialPhaseKind.LIQUID,
        atom_group_ids=("all_atoms",),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="user-declared"):
        mdstats.MaterialProfileIdentity(
            profile_id="auto-guess",
            profile_version="1",
            phases=(phase,),
            user_declared=False,
        )


def test_interface_requires_multiple_phases_and_explicit_atom_groups() -> None:
    phase = mdstats.PhaseComponentIdentity(
        phase_id="solid",
        phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
        atom_group_ids=("solid_atoms",),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="at least two phases"):
        mdstats.MaterialProfileIdentity(
            profile_id="invalid-interface",
            profile_version="1",
            phases=(phase,),
            geometry=mdstats.MaterialGeometryKind.INTERFACE,
        )

    liquid = mdstats.PhaseComponentIdentity(
        phase_id="liquid",
        phase_kind=mdstats.MaterialPhaseKind.LIQUID,
        atom_group_ids=("liquid_atoms",),
        chemistry_modifiers=(mdstats.ChemistryModifier.IONIC,),
    )
    profile = mdstats.MaterialProfileIdentity(
        profile_id="solid-liquid-interface",
        profile_version="1",
        phases=(phase, liquid),
        geometry=mdstats.MaterialGeometryKind.INTERFACE,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="one-phase"):
        mdstats.default_atom_group_catalog(profile)


def test_structural_extension_hierarchy_is_explicit() -> None:
    with pytest.raises(mdstats.TrainingDataInputError, match="requires the zeolite"):
        mdstats.build_single_phase_material_profile(
            profile_id="bad-lta",
            phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
            extensions=(mdstats.StructuralExtension.LTA,),
        )
    with pytest.raises(mdstats.TrainingDataInputError, match="requires the porous_network"):
        mdstats.build_single_phase_material_profile(
            profile_id="bad-zeolite",
            phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
            extensions=(mdstats.StructuralExtension.ZEOLITE,),
        )
    valid = mdstats.build_single_phase_material_profile(
        profile_id="lta-profile",
        phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
        extensions=(
            mdstats.StructuralExtension.POROUS_NETWORK,
            mdstats.StructuralExtension.ZEOLITE,
            mdstats.StructuralExtension.LTA,
        ),
    )
    assert valid.extensions == ("lta", "porous_network", "zeolite")


def test_static_and_dynamic_atom_group_selectors_round_trip() -> None:
    provider = mdstats.MaterialProfileProviderIdentity(
        provider_id="profiles.interface-region",
        provider_version="1.0",
        configuration_digest="a" * 64,
    )
    static = mdstats.AtomGroupDefinition(
        group_id="alkali",
        label="Alkali atoms",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS,
            atomic_numbers=(3, 11, 19),
        ),
        roles=("mobile_ions",),
    )
    dynamic = mdstats.AtomGroupDefinition(
        group_id="interface_zone",
        label="Interface zone",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.PROVIDER,
            provider_identity=provider,
            provider_parameters={"half_width_angstrom": 3.0},
        ),
        scope=mdstats.AtomGroupScope.FRAME_DYNAMIC,
        roles=("interface_atoms",),
    )
    assert mdstats.AtomGroupDefinition.from_dict(static.to_dict()) == static
    assert mdstats.AtomGroupDefinition.from_dict(dynamic.to_dict()) == dynamic
    with pytest.raises(mdstats.TrainingDataInputError, match="frame_dynamic"):
        mdstats.AtomGroupDefinition(
            group_id="bad",
            label="Bad dynamic group",
            selector=dynamic.selector,
        )


def test_composite_groups_are_dependency_checked() -> None:
    profile = _solid_profile()
    base = mdstats.AtomGroupDefinition(
        group_id="all_atoms",
        label="All atoms",
        selector=mdstats.AtomGroupSelector(kind=mdstats.AtomGroupSelectorKind.ALL_ATOMS),
        phase_ids=("material",),
    )
    oxygen = mdstats.AtomGroupDefinition(
        group_id="oxygen",
        label="Oxygen",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS,
            atomic_numbers=(8,),
        ),
        phase_ids=("material",),
    )
    nonoxygen = mdstats.AtomGroupDefinition(
        group_id="nonoxygen",
        label="Non-oxygen",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.COMPOSITE,
            source_group_ids=("all_atoms", "oxygen"),
            operation=mdstats.AtomGroupSetOperation.DIFFERENCE,
        ),
        phase_ids=("material",),
    )
    catalog = mdstats.AtomGroupCatalog(
        material_profile_digest=profile.content_digest,
        material_phase_ids=profile.phase_ids,
        groups=(base, oxygen, nonoxygen),
    )
    assert mdstats.AtomGroupCatalog.from_dict(catalog.to_dict()) == catalog

    cyclic_a = mdstats.AtomGroupDefinition(
        group_id="a",
        label="A",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.COMPOSITE,
            source_group_ids=("b",),
            operation=mdstats.AtomGroupSetOperation.COMPLEMENT,
        ),
    )
    cyclic_b = mdstats.AtomGroupDefinition(
        group_id="b",
        label="B",
        selector=mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.COMPOSITE,
            source_group_ids=("a",),
            operation=mdstats.AtomGroupSetOperation.COMPLEMENT,
        ),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="cycle"):
        mdstats.AtomGroupCatalog(
            material_profile_digest=profile.content_digest,
            material_phase_ids=profile.phase_ids,
            groups=(cyclic_a, cyclic_b),
        )


def test_condition_axis_semantics_are_validated() -> None:
    axis = mdstats.ConditionAxisDefinition(
        axis_id="salt_loading",
        label="Salt loading",
        value_kind=mdstats.AxisValueKind.CONTINUOUS,
        roles=(mdstats.ConditionAxisRole.COVERAGE, mdstats.ConditionAxisRole.CHALLENGE),
        unit="ions/cage",
        minimum=0.0,
    )
    assert mdstats.ConditionAxisDefinition.from_dict(axis.to_dict()) == axis
    with pytest.raises(mdstats.TrainingDataInputError, match="cannot define numeric bounds"):
        mdstats.ConditionAxisDefinition(
            axis_id="termination",
            label="Termination",
            value_kind=mdstats.AxisValueKind.CATEGORICAL,
            minimum=0.0,
        )
    with pytest.raises(mdstats.TrainingDataInputError, match="cannot define allowed_values"):
        mdstats.ConditionAxisDefinition(
            axis_id="temperature",
            label="Temperature",
            value_kind=mdstats.AxisValueKind.CONTINUOUS,
            allowed_values=("300",),
        )


def test_integer_contracts_reject_lossy_coercion() -> None:
    with pytest.raises(mdstats.TrainingDataInputError, match="finite integers"):
        mdstats.AtomGroupSelector(
            kind=mdstats.AtomGroupSelectorKind.ATOM_INDICES,
            atom_indices=(1.5,),
        )
    with pytest.raises(mdstats.TrainingDataInputError, match="positive integer"):
        mdstats.IndependenceAxisDefinition(
            axis_id="replica",
            label="Replica",
            scope=mdstats.IndependenceAxisScope.REPLICA,
            minimum_distinct_values=1.5,
        )


def test_independence_axes_do_not_assert_observed_independence() -> None:
    profile = _solid_profile()
    catalog = mdstats.default_independence_axis_catalog(profile)
    assert all(axis.leakage_barrier for axis in catalog.axes)
    assert all(axis.minimum_distinct_values == 2 for axis in catalog.axes)
    assert mdstats.IndependenceAxisCatalog.from_dict(catalog.to_dict()) == catalog


def test_contract_aggregate_rejects_cross_profile_catalogs() -> None:
    profile_a = _solid_profile()
    profile_b = mdstats.build_single_phase_material_profile(
        profile_id="other",
        phase_kind=mdstats.MaterialPhaseKind.AMORPHOUS_SOLID,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="does not belong"):
        mdstats.MaterialProfileContracts(
            profile=profile_a,
            atom_groups=mdstats.default_atom_group_catalog(profile_b),
            condition_axes=mdstats.default_condition_axis_catalog(profile_a),
            independence_axes=mdstats.default_independence_axis_catalog(profile_a),
        )


def test_tamper_rejection_for_profile_contracts() -> None:
    contracts = mdstats.build_material_profile_contracts(_solid_profile())
    payload = deepcopy(contracts.to_dict())
    payload["profile"]["profile_id"] = "tampered"
    with pytest.raises(mdstats.TrainingDataSerializationError):
        mdstats.MaterialProfileContracts.from_dict(payload)


@dataclass
class _Provider:
    provider_id: str = "profiles.generic-crystal"
    provider_version: str = "1"

    def build_profile(self) -> mdstats.MaterialProfileIdentity:
        identity = mdstats.MaterialProfileProviderIdentity(
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            configuration_digest="b" * 64,
        )
        return mdstats.build_single_phase_material_profile(
            profile_id="provider-crystal",
            phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
            provider_identity=identity,
        )

    def build_atom_groups(self, profile: mdstats.MaterialProfileIdentity) -> mdstats.AtomGroupCatalog:
        return mdstats.default_atom_group_catalog(profile)

    def build_condition_axes(self, profile: mdstats.MaterialProfileIdentity) -> mdstats.ConditionAxisCatalog:
        return mdstats.default_condition_axis_catalog(profile)

    def build_independence_axes(self, profile: mdstats.MaterialProfileIdentity) -> mdstats.IndependenceAxisCatalog:
        return mdstats.default_independence_axis_catalog(profile)


def test_runtime_provider_protocol_and_materialization() -> None:
    provider = _Provider()
    assert isinstance(provider, mdstats.SystemProfileProvider)
    contracts = mdstats.contracts_from_provider(provider)
    assert contracts.profile.provider_identity is not None
    assert contracts.profile.provider_identity.provider_id == provider.provider_id


def test_data4_bundle_threads_profile_contracts_without_enabling_lta(tmp_path) -> None:
    sources, frames, data, _ = _site_catalogs(tmp_path / "sources")
    contracts = mdstats.build_material_profile_contracts(_solid_profile())
    bundle = mdstats.build_data4_feature_bundle(
        sources,
        frames,
        data,
        material_profile_contracts=contracts,
    )
    assert bundle.material_profile_contracts == contracts
    assert bundle.lta_partition_features is None
    assert mdstats.Data4FeatureBundle.from_dict(bundle.to_dict()) == bundle

    cache = tmp_path / "cache"
    mdstats.write_data4_feature_cache(bundle, cache)
    assert (cache / "material_profile_contracts.json").is_file()
    loaded, _ = mdstats.read_data4_feature_cache(cache)
    assert loaded.material_profile_contracts == contracts


def test_data4_v1_compatibility_remains_readable(tmp_path) -> None:
    sources, frames, data, _ = _site_catalogs(tmp_path / "sources")
    bundle = mdstats.build_data4_feature_bundle(sources, frames, data)
    payload = bundle.to_dict()
    payload["schema"] = "mdstats.data4-feature-bundle.v1"
    payload.pop("material_profile_contracts")
    legacy_payload = {key: value for key, value in payload.items() if key != "content_digest"}
    payload["content_digest"] = digest(legacy_payload)
    restored = mdstats.Data4FeatureBundle.from_dict(payload)
    assert restored.material_profile_contracts is None
    assert restored.dataset_id == bundle.dataset_id



def test_data4_rejects_lta_features_under_generic_profile(tmp_path) -> None:
    sources, frames, data, site_policy = _site_catalogs(tmp_path / "sources")
    contracts = mdstats.build_material_profile_contracts(_solid_profile())
    with pytest.raises(mdstats.TrainingDataInputError, match="explicit lta extension"):
        mdstats.build_data4_feature_bundle(
            sources,
            frames,
            data,
            material_profile_contracts=contracts,
            lta_profile_policy=mdstats.LtaPartitionProfilePolicy(
                ring_definitions=site_policy.ring_definitions,
                require_oxygen_framework_coordination=1,
            ),
        )

def test_data4_v1_cache_compatibility(tmp_path) -> None:
    import hashlib
    import json

    from mdstats.training_data._common import canonical_json

    sources, frames, data, _ = _site_catalogs(tmp_path / "sources")
    bundle = mdstats.build_data4_feature_bundle(sources, frames, data)
    cache = tmp_path / "legacy-cache"
    manifest = mdstats.write_data4_feature_cache(bundle, cache)

    bundle_path = cache / "data4_feature_bundle.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    payload["schema"] = "mdstats.data4-feature-bundle.v1"
    payload.pop("material_profile_contracts")
    payload["content_digest"] = digest({k: v for k, v in payload.items() if k != "content_digest"})
    bundle_path.write_text(canonical_json(payload) + "\n", encoding="utf-8")

    records = []
    for record in manifest.files:
        if record.relative_path == "data4_feature_bundle.json":
            records.append(
                mdstats.FeatureCacheFileRecord(
                    relative_path=record.relative_path,
                    sha256=hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
                    content_digest=payload["content_digest"],
                )
            )
        else:
            records.append(record)
    legacy_manifest = mdstats.FeatureCacheManifest(
        dataset_id=manifest.dataset_id,
        bundle_digest=payload["content_digest"],
        files=tuple(records),
    )
    (cache / "cache_manifest.json").write_text(
        canonical_json(legacy_manifest.to_dict()) + "\n",
        encoding="utf-8",
    )
    restored, restored_manifest = mdstats.read_data4_feature_cache(cache)
    assert restored.material_profile_contracts is None
    assert restored_manifest == legacy_manifest
