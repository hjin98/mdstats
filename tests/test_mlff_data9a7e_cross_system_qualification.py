from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import os
import subprocess
import sys

import pytest

import mdstats
from tests.test_mlff_data5_partition_roles import _build, _policy


def _clean_import_evidence() -> mdstats.ImportIsolationEvidence:
    return mdstats.ImportIsolationEvidence(
        probe_id="clean-generic-import",
        clean_interpreter=True,
        modules_before=(),
        modules_after_generic_import=(),
        forbidden_module_prefixes=mdstats.CrossSystemQualificationPolicy().forbidden_generic_module_prefixes,
        probe_script_digest="a" * 64,
        passed=True,
    )


def _single_contract(kind: mdstats.MaterialPhaseKind) -> mdstats.MaterialProfileContracts:
    return mdstats.build_material_profile_contracts(
        mdstats.build_single_phase_material_profile(
            profile_id=f"qualification-{kind.value}",
            phase_kind=kind,
        )
    )


def _interface_contracts() -> mdstats.MaterialProfileContracts:
    profile = mdstats.MaterialProfileIdentity(
        profile_id="qualification-interface",
        profile_version="1",
        phases=(
            mdstats.PhaseComponentIdentity(
                phase_id="solid",
                phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
                atom_group_ids=("solid_phase",),
            ),
            mdstats.PhaseComponentIdentity(
                phase_id="liquid",
                phase_kind=mdstats.MaterialPhaseKind.LIQUID,
                atom_group_ids=("liquid_phase",),
            ),
        ),
        geometry=mdstats.MaterialGeometryKind.INTERFACE,
    )
    groups = mdstats.AtomGroupCatalog(
        material_profile_digest=profile.content_digest,
        material_phase_ids=profile.phase_ids,
        groups=(
            mdstats.AtomGroupDefinition(
                group_id="solid_phase", label="Solid phase",
                selector=mdstats.AtomGroupSelector(
                    kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS,
                    atomic_numbers=(8,),
                ),
                phase_ids=("solid",), roles=("phase_bulk",),
            ),
            mdstats.AtomGroupDefinition(
                group_id="liquid_phase", label="Liquid phase",
                selector=mdstats.AtomGroupSelector(
                    kind=mdstats.AtomGroupSelectorKind.ATOMIC_NUMBERS,
                    atomic_numbers=(3,),
                ),
                phase_ids=("liquid",), roles=("phase_bulk",),
            ),
            mdstats.AtomGroupDefinition(
                group_id="interface_atoms", label="Interface atoms",
                selector=mdstats.AtomGroupSelector(
                    kind=mdstats.AtomGroupSelectorKind.COMPOSITE,
                    source_group_ids=("solid_phase", "liquid_phase"),
                    operation=mdstats.AtomGroupSetOperation.UNION,
                ),
                phase_ids=("solid", "liquid"), roles=("interface",),
            ),
        ),
    )
    return mdstats.build_material_profile_contracts(profile, atom_groups=groups)


def _lta_contracts() -> mdstats.MaterialProfileContracts:
    return mdstats.build_material_profile_contracts(
        mdstats.build_single_phase_material_profile(
            profile_id="qualification-lta",
            phase_kind=mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID,
            extensions=(
                mdstats.StructuralExtension.POROUS_NETWORK,
                mdstats.StructuralExtension.ZEOLITE,
                mdstats.StructuralExtension.LTA,
            ),
        )
    )


def _pipeline(
    sources,
    frames,
    frame_data,
    contracts,
    *,
    lta: bool = False,
):
    lta_policy = None
    if lta:
        lta_policy = mdstats.LtaPartitionProfilePolicy(
            ring_definitions=(),
            require_oxygen_framework_coordination=1,
        )
    data4 = mdstats.build_data4_feature_bundle(
        sources,
        frames,
        frame_data,
        material_profile_contracts=contracts,
        lta_profile_policy=lta_policy,
        partition_role_budget=_policy().role_budget,
    )
    data5 = mdstats.build_data5_partition_bundle(
        sources, frames, data4, partition_policy=_policy()
    )
    data6 = mdstats.build_data6_feature_bundle(
        sources, frames, frame_data, data4, data5, policy=None
    )
    domains = mdstats.build_feature_fit_domains(data5)
    final = next(
        item for item in domains
        if item.kind is mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT
    )
    target = min(8, len(final.frame_uids))
    blocks = [mdstats.FeatureBlockPolicy("universal_structural", required=True)]
    if lta:
        blocks.append(mdstats.FeatureBlockPolicy("profile_extensions", required=True))
    data7 = mdstats.build_data7_preparation_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        data6,
        final,
        feature_metric_policy=mdstats.FeatureMetricPolicyTemplate(blocks=tuple(blocks)),
        selection_budget_policy=mdstats.SelectionBudgetPolicy(target_sizes=(target,)),
    )
    return data4, data5, data6, data7


def test_cross_system_data4_to_data7_suite(tmp_path: Path) -> None:
    sources, frames, _, _ = _build(tmp_path / "base")
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(
        sources, base_directory=tmp_path / "base"
    )
    policy = mdstats.CrossSystemQualificationPolicy()
    cases = []
    definitions = (
        (mdstats.CrossSystemCaseKind.GENERIC_CRYSTAL, _single_contract(mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID), False),
        (mdstats.CrossSystemCaseKind.AMORPHOUS_SOLID, _single_contract(mdstats.MaterialPhaseKind.AMORPHOUS_SOLID), False),
        (mdstats.CrossSystemCaseKind.LIQUID, _single_contract(mdstats.MaterialPhaseKind.LIQUID), False),
        (mdstats.CrossSystemCaseKind.MULTIPHASE_INTERFACE, _interface_contracts(), False),
        (mdstats.CrossSystemCaseKind.LTA_EXTENSION, _lta_contracts(), True),
    )
    for kind, contracts, lta in definitions:
        data4, data5, data6, data7 = _pipeline(
            sources, frames, frame_data, contracts, lta=lta
        )
        record = mdstats.qualify_cross_system_case(
            case_id=kind.value,
            case_kind=kind,
            data4_bundle=data4,
            data5_bundle=data5,
            data6_bundle=data6,
            data7_bundle=data7,
            policy=policy,
            import_isolation_evidence=_clean_import_evidence(),
        )
        assert record.passed
        if not lta:
            assert record.profile_extension_ids == ()
            assert record.forbidden_imported_modules == ()
            assert record.forbidden_serialized_paths == ()
        else:
            assert record.profile_extension_ids == ("lta",)
        assert mdstats.CrossSystemQualificationCaseRecord.from_dict(record.to_dict()) == record
        cases.append(record)

    suite = mdstats.build_cross_system_qualification_suite(
        "bounded-cross-system-v1", cases, policy=policy
    )
    assert suite.passed
    path = suite.write_json(tmp_path / "qualification.json")
    assert mdstats.CrossSystemQualificationSuiteRecord.read_json(path) == suite


def test_generic_case_rejects_forbidden_import_evidence(tmp_path: Path) -> None:
    sources, frames, _, _ = _build(tmp_path / "base")
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(
        sources, base_directory=tmp_path / "base"
    )
    bundles = _pipeline(
        sources, frames, frame_data,
        _single_contract(mdstats.MaterialPhaseKind.CRYSTALLINE_SOLID),
    )
    record = mdstats.qualify_cross_system_case(
        "bad-generic",
        mdstats.CrossSystemCaseKind.GENERIC_CRYSTAL,
        *bundles,
        import_isolation_evidence=mdstats.ImportIsolationEvidence(
            probe_id="bad", clean_interpreter=True, modules_before=(),
            modules_after_generic_import=("mdstats.training_data.lta_profile",),
            forbidden_module_prefixes=mdstats.CrossSystemQualificationPolicy().forbidden_generic_module_prefixes,
            probe_script_digest="b" * 64, passed=False,
        ),
    )
    assert not record.passed
    assert record.forbidden_imported_modules == ("mdstats.training_data.lta_profile",)


def test_clean_top_level_import_does_not_load_mlff_lta_modules() -> None:
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root), "/mnt/data/deps_7d/ase", env.get("PYTHONPATH", "")]
    )
    script = """
import json, sys
import mdstats
before = sorted(name for name in sys.modules if name.startswith('mdstats.training_data.lta_'))
_ = mdstats.Data6Policy
middle = sorted(name for name in sys.modules if name.startswith('mdstats.training_data.lta_'))
_ = mdstats.LtaSelectionPolicy
late = sorted(name for name in sys.modules if name.startswith('mdstats.training_data.lta_'))
print(json.dumps({'before': before, 'middle': middle, 'late': late}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script], env=env, check=True,
        capture_output=True, text=True,
    )
    import json
    payload = json.loads(completed.stdout)
    assert payload["before"] == []
    assert payload["middle"] == []
    assert payload["late"] == ["mdstats.training_data.lta_selection"]


def test_suite_requires_all_declared_cases() -> None:
    policy = mdstats.CrossSystemQualificationPolicy()
    with pytest.raises(mdstats.TrainingDataInputError, match="missing required cases"):
        mdstats.build_cross_system_qualification_suite("incomplete", (), policy=policy)
