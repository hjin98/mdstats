from __future__ import annotations
import json
from pathlib import Path
import mdstats
ROOT=Path(__file__).resolve().parents[1]

def test_replay_unify1e_release_graph_and_manual_are_synchronized():
    assert tuple(int(part) for part in mdstats.__version__.split("a", 1)[0].split(".")) >= (0, 20, 214)
    manual=(ROOT/'docs/arch_manuals/mlff_training_data_architecture.md').read_text()
    note=(ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV81.md").read_text()
    assert 'Revision 81 current gate: REPLAY-UNIFY1E' in manual
    assert 'mdstats.replay-invalidation-plan.v1' in manual
    assert 'REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION' in manual
    assert '0.20.214a0' in note and 'schema:** 63' in note
    graph=json.loads((ROOT/'docs/arch_manuals/mlff_training_data_dependency_graph.json').read_text())
    assert graph['architecture_revision']>=81 and graph['schema_version']>=63
    assert any(n['id']=='REPLAY_UNIFY1E_MIGRATION_HARDENING' for n in graph['nodes'])
    nodes={n['id']:n for n in graph['nodes']}
    gate=nodes['REPLAY_UNIFY1E_MIGRATION_HARDENING']
    assert gate['implementation_status']=='implemented_migration_hardening_final_gpu1_regenerated'
    assert gate['invalidation_plan_schema']==mdstats.REPLAY_INVALIDATION_PLAN_SCHEMA
    final=nodes['FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION']
    assert final['final_gpu1_policy_schema']==mdstats.FINAL_GPU1_POLICY_SCHEMA
    assert final['final_gpu1_qualification_schema']==mdstats.FINAL_GPU1_QUALIFICATION_SCHEMA
    assert final['required_pass_gates']==list(mdstats.FINAL_GPU1_REQUIRED_PASS_GATES)
    assert 'REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION' in final['runtime_bound_gates']
    assert final['workstation_bundle_current'] is True

def test_final_gpu1_v3_matrix_adds_replay_gpu_gate_and_keeps_v2_deserializable():
    assert 'REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION' in mdstats.FINAL_GPU1_REQUIRED_PASS_GATES
    assert 'REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION' in mdstats.FINAL_GPU1_RUNTIME_BOUND_GATES
    assert mdstats.FINAL_GPU1_POLICY_SCHEMA.endswith('.v3')
    assert mdstats.FINAL_GPU1_QUALIFICATION_SCHEMA.endswith('.v3')
