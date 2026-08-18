from __future__ import annotations

from pathlib import Path
import ast
import json
import os

import pytest
import yaml

import mdstats
from tests.test_mlff_data8_mace_artifacts import (
    _data7_bundles,
    _probe,
    _write_replay,
)


RUNTIME_RECORD = Path(
    os.environ.get(
        "MDSTATS_MACE_RUNTIME_RECORD",
        "/mnt/data/mlff_realtest/results/mdstats_offline_runtime_record.json",
    )
)
FOUNDATION_MODEL = Path(
    os.environ.get("MDSTATS_MACE_FOUNDATION_MODEL", "/mnt/data/mace-mpa-0-medium.model")
)


def _runtime() -> mdstats.MaceRuntimeEnvironmentRecord:
    if not RUNTIME_RECORD.is_file():
        pytest.skip("qualified supplied MACE runtime record is not mounted")
    record = mdstats.MaceRuntimeEnvironmentRecord.from_dict(
        json.loads(RUNTIME_RECORD.read_text())
    )
    if not record.qualified_for_cli_smoke:
        pytest.skip("supplied MACE runtime record is not qualified")
    return record


def _foundation() -> mdstats.FoundationCheckpointIdentity:
    if not FOUNDATION_MODEL.is_file():
        pytest.skip("supplied MACE-MPA-0 checkpoint is not mounted")
    return mdstats.FoundationCheckpointIdentity.from_file(FOUNDATION_MODEL)


def _bundle(tmp_path: Path, *, replay: bool) -> mdstats.Data8PreparationBundle:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    replay_plan = None
    if replay:
        replay_train = tmp_path / "replay_train.xyz"
        replay_monitor = tmp_path / "replay_monitor.xyz"
        _write_replay(replay_train, offset=0.0, count=5)
        _write_replay(replay_monitor, offset=0.3, count=2)
        replay_plan = mdstats.build_local_replay_plan(
            replay_train,
            replay_monitor,
            head_weight=1.5,
            target_weight=4.0,
        )
    return mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=tmp_path / ("replay_bundle" if replay else "naive_bundle"),
        foundation_checkpoint=_foundation(),
        compatibility_probe=_probe(),
        replay_plan=replay_plan,
        optimizer_policy=mdstats.MaceOptimizerPolicy(
            device="cpu", max_num_epochs=1, batch_size=1, valid_batch_size=1
        ),
        real_pt_data_ratio_threshold=0.0,
        require_foundation_residual_e0=False,
        selection_size=4,
    )


def test_data8_v0316_yaml_is_scalar_literal_serialized(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path, replay=True)
    root = Path(bundle.output_directory)
    config = yaml.safe_load((root / bundle.jobs[0].config_relative_path).read_text())
    assert isinstance(config["atomic_numbers"], str)
    assert isinstance(config["heads"], str)
    numbers = ast.literal_eval(config["atomic_numbers"])
    heads = ast.literal_eval(config["heads"])
    assert numbers == sorted(numbers)
    assert list(heads) == ["target_head", "pt_head"]
    assert isinstance(heads["target_head"]["E0s"], str)
    assert set(ast.literal_eval(heads["target_head"]["E0s"])) <= set(numbers)
    assert config["loss"] == "universal"
    for forbidden in ("weight_pt", "weight_ft"):
        assert forbidden not in config


def test_real_mace_parser_and_loader_dry_run_for_naive_and_replay(tmp_path: Path) -> None:
    environment = _runtime()
    for replay in (False, True):
        bundle = _bundle(tmp_path / ("replay" if replay else "naive"), replay=replay)
        job = next(item for item in bundle.jobs if item.kind is mdstats.MaceJobKind.FINAL_DEVELOPMENT)
        record = mdstats.realize_mace_job_config(
            environment,
            bundle.output_directory,
            job,
            policy=mdstats.MaceConfigRealizationPolicy(timeout_seconds=300.0),
        )
        assert record.passed, record.to_dict()
        assert record.parsed_loss == "universal"
        assert record.parsed_head_names == (
            ("target_head", "pt_head") if replay else ("target_head",)
        )
        assert set(record.parsed_e0_atomic_numbers) <= set(record.parsed_atomic_numbers)
        assert mdstats.MaceConfigRealizationRecord.from_dict(record.to_dict()) == record


@pytest.mark.slow
def test_real_mace_one_epoch_replay_extract_and_evaluate(tmp_path: Path) -> None:
    environment = _runtime()
    bundle = _bundle(tmp_path, replay=True)
    job = next(item for item in bundle.jobs if item.kind is mdstats.MaceJobKind.FINAL_DEVELOPMENT)
    realization = mdstats.realize_mace_job_config(
        environment,
        bundle.output_directory,
        job,
        policy=mdstats.MaceConfigRealizationPolicy(timeout_seconds=300.0),
    )
    assert realization.passed, realization.to_dict()
    smoke = mdstats.run_mace_job_execution_smoke(
        environment,
        bundle.output_directory,
        job,
        realization,
        tmp_path / "execution_smoke",
        policy=mdstats.MaceJobExecutionSmokePolicy(
            max_num_epochs=1,
            device="cpu",
            timeout_seconds=600.0,
        ),
    )
    assert smoke.passed, smoke.to_dict()
    assert "target_head" in smoke.head_names
    assert "pt_head" in smoke.head_names
    assert smoke.target_head_model is not None
    assert smoke.evaluation_configuration_count > 0
    assert smoke.evaluation_fields_finite
    assert mdstats.MaceJobExecutionSmokeRecord.from_dict(smoke.to_dict()) == smoke
