from pathlib import Path
import json

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'docs/specs/training_data/mlff_data9b2_execution_aggregation_freeze_spec.md'
MANUAL = ROOT / 'docs/arch_manuals/mlff_training_data_architecture.md'
STAGE = ROOT / 'docs/specs/training_data/mlff_data_stage_plan_spec.md'
GRAPH = ROOT / 'docs/arch_manuals/mlff_training_data_dependency_graph.json'


def test_data9b2_spec_version_and_public_contracts() -> None:
    text = SPEC.read_text(encoding='utf-8')
    for token in (
        'Version: 0.20.57a0',
        'TrainingRunExecutionRecord',
        'CheckpointEvaluationRecord',
        'ProtocolVariantAggregate',
        'CommitteeIdentity',
        'ProtocolFreezeRecord',
        'EvaluationActivationDecision',
        'mdstats-mace-select-head',
    ):
        assert token in text
    assert mdstats.__version__ == '0.20.140a0'
    assert mdstats.MLFF_DATA9B2_VERSION == '0.20.57a0'


def test_data9b2_manual_and_stage_plan_integration() -> None:
    manual = MANUAL.read_text(encoding='utf-8')
    stage = STAGE.read_text(encoding='utf-8')
    assert 'MLFF-DATA9B2 execution, aggregation, committee, and freeze - implemented in 0.20.57a0' in manual
    assert 'MLFF-DATA9B2 - execution, aggregation, committee, and freeze - implemented in 0.20.57a0' in stage
    assert 'Long production campaign' in manual


def test_data9b2_dependency_graph_records_and_edges() -> None:
    graph = json.loads(GRAPH.read_text(encoding='utf-8'))
    assert graph['architecture_revision'] == 34
    assert graph['schema_version'] == 26
    nodes = {v['id'] for v in graph['nodes']}
    for node in (
        'TRAINING_EXECUTION_POLICY',
        'TRAINING_RUN_ATTEMPT_RECORD',
        'TRAINING_RUN_EXECUTION_RECORD',
        'CHECKPOINT_EVALUATION_POLICY',
        'CHECKPOINT_EVALUATION_RECORD',
        'PROTOCOL_VARIANT_AGGREGATE',
        'PROTOCOL_FAMILY_AGGREGATE',
        'LEARNING_CURVE_RECORD',
        'PROTOCOL_COMPARISON_RECORD',
        'COMMITTEE_MEMBER_RECORD',
        'COMMITTEE_IDENTITY',
    ):
        assert node in nodes
    edges = {(e['from'], e['to'], e['type']) for e in graph['edges']}
    assert ('TRAINING_CAMPAIGN_RUN_PLAN', 'TRAINING_RUN_EXECUTION_RECORD', 'execution_requires') in edges
    assert ('CHECKPOINT_EVALUATION_RECORD', 'CHECKPOINT_METRIC_RECORD', 'promotion_requires') in edges
    assert ('PROTOCOL_VARIANT_AGGREGATE', 'PROTOCOL_FAMILY_AGGREGATE', 'execution_requires') in edges
    assert ('COMMITTEE_IDENTITY', 'PROTOCOL_FREEZE_RECORD', 'source_identity_requires') in edges
