from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import os

import pytest

import mdstats
from mdstats.training_data._common import digest
from tests.test_mlff_data7_fitted_metrics_selection import _inputs
from tests.test_mlff_data8_mace_artifacts import _probe, _write_replay


MH1_MODEL = Path(os.environ.get("MDSTATS_MH1_MODEL", "/mnt/data/mace-mh-1.model"))
EXTRACT1_EVIDENCE = Path(
    os.environ.get(
        "MDSTATS_MH1_EXTRACT1_EVIDENCE",
        "/mnt/data/mh1_gate5_work/mdstats-0.20.177a0-complete-source-package/"
        "audits/analysis/mlff_mh1_extract1_selected_head_evidence.json",
    )
)
RUNTIME_RECORD = Path(
    os.environ.get(
        "MDSTATS_MACE_RUNTIME_RECORD",
        "/mnt/data/mh1_gate9_work/direct_runtime_record.json",
    )
)


def _minimal_precision(path: str, sha: str, *, expected: str | None = None) -> mdstats.MaceModelPrecisionRecord:
    return mdstats.MaceModelPrecisionRecord(
        artifact_path=path,
        artifact_sha256=sha,
        model_class="ScaleShiftMACE",
        floating_parameter_dtypes=(("float64", 1),),
        floating_buffer_dtypes=(),
        non_floating_parameter_count=0,
        non_floating_buffer_count=0,
        expected_dtype=expected,
    )


def test_train1_protocol_v7_and_precision_v2_preserve_scientific_and_executable_lineage(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    source.write_bytes(b"source")
    foundation = mdstats.FoundationCheckpointIdentity.from_file(source)
    scientific_sha = foundation.sha256
    training_sha = "b" * 64
    qualification_digest = "a" * 64
    optimizer = mdstats.MaceOptimizerPolicy(device="cpu", default_dtype="float64")
    protocol = mdstats.TrainingProtocolIdentity(
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        foundation_checkpoint=foundation,
        compatibility_probe_digest="1" * 64,
        data7_bundle_digest="2" * 64,
        target_train_artifact_digest="3" * 64,
        target_valid_artifact_digest="4" * 64,
        replay_plan_digest=None,
        training_objective_policy_digest="5" * 64,
        configuration_weight_policy_digest="6" * 64,
        checkpoint_metric_policy_digest="7" * 64,
        checkpoint_control_policy=mdstats.MaceCheckpointControlPolicy(),
        optimizer_policy=optimizer,
        selection_size=1,
        real_pt_data_ratio_threshold=0,
        selected_head_qualification_digest=qualification_digest,
        training_foundation_checkpoint_reference="shared/foundation/selected_head/source.model",
        training_foundation_checkpoint_sha256=training_sha,
    )
    payload = protocol.to_dict()
    assert payload["schema"] == "mdstats.training-protocol-identity.v7"
    assert payload["foundation_checkpoint"]["sha256"] == scientific_sha
    assert payload["training_foundation_checkpoint_sha256"] == training_sha
    assert mdstats.TrainingProtocolIdentity.from_dict(payload) == protocol

    transition = mdstats.MacePrecisionTransitionRecord(
        foundation_checkpoint=foundation,
        job_digest="8" * 64,
        optimizer_policy_digest=optimizer.policy_digest,
        requested_dtype="float64",
        foundation_precision=_minimal_precision("derived.model", training_sha),
        trained_model_precision=_minimal_precision("trained.model", "c" * 64, expected="float64"),
        extracted_model_precision=_minimal_precision("target.model", "d" * 64, expected="float64"),
        training_foundation_checkpoint_sha256=training_sha,
        selected_head_qualification_digest=qualification_digest,
    )
    assert transition.passed
    assert transition.to_dict()["schema"] == "mdstats.mace-precision-transition-record.v2"
    assert mdstats.MacePrecisionTransitionRecord.from_dict(transition.to_dict()) == transition

    legacy = replace(
        transition,
        foundation_precision=_minimal_precision("source.model", scientific_sha),
        training_foundation_checkpoint_sha256=None,
        selected_head_qualification_digest=None,
    )
    assert legacy.to_dict()["schema"] == "mdstats.mace-precision-transition-record.v1"
    assert mdstats.MacePrecisionTransitionRecord.from_dict(legacy.to_dict()) == legacy


def test_train1_realization_v3_payload_remains_digest_stable() -> None:
    policy = mdstats.MaceConfigRealizationPolicy(run_loader_dry_run=False, timeout_seconds=120)
    command = mdstats.MaceCliCommandResult(
        command=("python", "probe"),
        resolved_executable="python",
        returncode=0,
        stdout_sha256="1" * 64,
        stderr_sha256="2" * 64,
        stdout_tail="",
        stderr_tail="",
        skipped_reason=None,
    )
    record = mdstats.MaceConfigRealizationRecord(
        environment_digest="3" * 64,
        job_digest="4" * 64,
        config_relative_path="jobs/final/mace_config.yaml",
        config_sha256="5" * 64,
        policy=policy,
        parser_result=command,
        loader_dry_run_result=None,
        parsed_name="job",
        parsed_loss="universal",
        parsed_default_dtype="float64",
        parsed_atomic_numbers=(3, 8),
        parsed_head_names=("target_head", "pt_head"),
        parsed_e0_atomic_numbers=(3, 8),
        parsed_enable_cueq=False,
        parsed_only_cueq=False,
        serialization_schema="mdstats.mace-config-realization-record.v3",
    )
    payload = record.to_dict()
    assert payload["schema"] == "mdstats.mace-config-realization-record.v3"
    assert "parsed_foundation_model_sha256" not in payload
    loaded = mdstats.MaceConfigRealizationRecord.from_dict(payload)
    assert loaded.content_digest == record.content_digest
    assert loaded.to_dict() == payload


def _real_train1_bundle(tmp_path: Path) -> tuple[mdstats.Data8PreparationBundle, mdstats.MaceJobArtifact]:
    if not MH1_MODEL.is_file() or not EXTRACT1_EVIDENCE.is_file():
        pytest.skip("locked MH-1/EXTRACT1 fixtures are not mounted")
    evidence = json.loads(EXTRACT1_EVIDENCE.read_text())
    qualification = mdstats.MaceSelectedHeadQualificationRecord.from_dict(evidence["qualification"])
    foundation = mdstats.MaceFoundationSpec(
        "mace_mh_1", "omat_pbe", requested_atomic_numbers=(3, 8)
    ).resolve_file(MH1_MODEL)

    sources, frames, frame_data, data4, data5, data6, domains, _ = _inputs(tmp_path / "inputs")
    bundles = tuple(
        mdstats.build_data7_preparation_bundle(
            sources,
            frames,
            frame_data,
            data4,
            data5,
            data6,
            domain,
            feature_metric_policy=mdstats.FeatureMetricPolicyTemplate(
                blocks=(mdstats.FeatureBlockPolicy("raw_physical", required=True),)
            ),
            selection_budget_policy=mdstats.SelectionBudgetPolicy(target_sizes=(1, 2)),
        )
        for domain in domains
    )
    replay_train = tmp_path / "replay_train.xyz"
    replay_monitor = tmp_path / "replay_monitor.xyz"
    _write_replay(replay_train, offset=0.0, count=1)
    _write_replay(replay_monitor, offset=0.3, count=1)
    replay = mdstats.build_local_replay_plan(
        replay_train,
        replay_monitor,
        head_weight=1.0,
        target_weight=1.0,
    )
    bundle = mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=tmp_path / "bundle",
        foundation_checkpoint=foundation,
        selected_head_qualification=qualification,
        compatibility_probe=_probe(),
        replay_plan=replay,
        optimizer_policy=mdstats.MaceOptimizerPolicy(
            device="cpu",
            default_dtype="float64",
            max_num_epochs=1,
            batch_size=1,
            valid_batch_size=1,
        ),
        real_pt_data_ratio_threshold=0.0,
        require_foundation_residual_e0=False,
        selection_size=1,
    )
    job = next(item for item in bundle.jobs if item.kind is mdstats.MaceJobKind.FINAL_DEVELOPMENT)
    return bundle, job


@pytest.mark.slow
def test_train1_real_mh1_data8_uses_qualified_selected_head_and_realizes_cli(tmp_path: Path) -> None:
    if not RUNTIME_RECORD.is_file():
        pytest.skip("qualified MACE runtime record is not mounted")
    environment = mdstats.MaceRuntimeEnvironmentRecord.from_dict(json.loads(RUNTIME_RECORD.read_text()))
    if not environment.qualified_for_cli_smoke:
        pytest.skip("mounted MACE runtime is not CLI-qualified")
    bundle, job = _real_train1_bundle(tmp_path)
    protocol = job.protocol
    assert protocol.foundation_checkpoint.sha256 == "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"
    assert protocol.foundation_checkpoint.foundation_head == "omat_pbe"
    assert protocol.training_foundation_checkpoint_sha256 == "7b6f3cce6d2086164082f1cb5739098de2db990d6a49f0d60e66a3a0f1ae545e"
    assert protocol.selected_head_qualification_digest == "0f49db0ff9da291fbb4d70430c71189552a531d0239d92c06d0ca4024b05e365"

    record = mdstats.realize_mace_job_config(
        environment,
        bundle.output_directory,
        job,
        policy=mdstats.MaceConfigRealizationPolicy(run_loader_dry_run=True, timeout_seconds=60.0),
    )
    assert record.passed, record.to_dict()
    assert record.parsed_foundation_model_sha256 == protocol.training_foundation_checkpoint_sha256
    assert record.parsed_foundation_head == "omat_pbe"
    assert record.parsed_multiheads_finetuning
    assert record.parsed_head_names == ("target_head", "pt_head")


@pytest.mark.slow
def test_train1_real_mh1_bounded_epoch_extracts_and_reloads_target_head(tmp_path: Path) -> None:
    if not RUNTIME_RECORD.is_file():
        pytest.skip("qualified MACE runtime record is not mounted")
    environment = mdstats.MaceRuntimeEnvironmentRecord.from_dict(json.loads(RUNTIME_RECORD.read_text()))
    if not environment.qualified_for_cli_smoke:
        pytest.skip("mounted MACE runtime is not CLI-qualified")
    bundle, job = _real_train1_bundle(tmp_path)
    realization = mdstats.realize_mace_job_config(
        environment,
        bundle.output_directory,
        job,
        policy=mdstats.MaceConfigRealizationPolicy(run_loader_dry_run=False, timeout_seconds=60.0),
    )
    smoke = mdstats.run_mace_job_execution_smoke(
        environment,
        bundle.output_directory,
        job,
        realization,
        tmp_path / "execution_smoke",
        policy=mdstats.MaceJobExecutionSmokePolicy(
            max_num_epochs=1,
            device="cpu",
            timeout_seconds=120.0,
            num_threads=2,
        ),
    )
    assert smoke.passed, smoke.to_dict()
    assert {"target_head", "pt_head"} <= set(smoke.head_names)
    assert smoke.target_head_model is not None
    assert smoke.evaluation_configuration_count > 0
    assert smoke.evaluation_fields_finite
