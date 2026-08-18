from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

import mdstats
from tests.test_mlff_data8_mace_artifacts import _data7_bundles, _probe

RUNTIME_RECORD = Path(os.environ.get("MDSTATS_MACE_RUNTIME_RECORD", "/mnt/data/mlff_fp32_runtime_record.json"))
FOUNDATION_MODEL = Path(os.environ.get("MDSTATS_MACE_FOUNDATION_MODEL", "/mnt/data/mace-mpa-0-medium.model"))


def _runtime() -> mdstats.MaceRuntimeEnvironmentRecord:
    if not RUNTIME_RECORD.is_file():
        pytest.skip("qualified MACE runtime record is not mounted")
    result = mdstats.MaceRuntimeEnvironmentRecord.from_dict(json.loads(RUNTIME_RECORD.read_text()))
    if not result.qualified_for_cli_smoke:
        pytest.skip("mounted MACE runtime is not qualified")
    return result


def _bundle(tmp_path: Path, dtype: str) -> mdstats.Data8PreparationBundle:
    if not FOUNDATION_MODEL.is_file():
        pytest.skip("foundation checkpoint is not mounted")
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    return mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=tmp_path / f"bundle_{dtype}",
        foundation_checkpoint=mdstats.FoundationCheckpointIdentity.from_file(FOUNDATION_MODEL),
        compatibility_probe=_probe(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(
            default_dtype=dtype,
            device="cpu",
            max_num_epochs=1,
            batch_size=1,
            valid_batch_size=1,
        ),
        real_pt_data_ratio_threshold=0.0,
        require_foundation_residual_e0=False,
        selection_size=4,
    )


@pytest.mark.parametrize("dtype", ["float32", "float64"])
def test_generated_config_binds_selected_dtype(tmp_path: Path, dtype: str) -> None:
    bundle = _bundle(tmp_path, dtype)
    job = next(v for v in bundle.jobs if v.kind is mdstats.MaceJobKind.FINAL_DEVELOPMENT)
    config = yaml.safe_load((Path(bundle.output_directory) / job.config_relative_path).read_text())
    assert config["default_dtype"] == dtype
    assert job.protocol.optimizer_policy.default_dtype == dtype


@pytest.mark.slow
@pytest.mark.parametrize("dtype", ["float32", "float64"])
def test_real_foundation_transfer_produces_selected_precision(tmp_path: Path, dtype: str) -> None:
    runtime = _runtime()
    bundle = _bundle(tmp_path, dtype)
    job = next(v for v in bundle.jobs if v.kind is mdstats.MaceJobKind.FINAL_DEVELOPMENT)
    realization = mdstats.realize_mace_job_config(
        runtime,
        bundle.output_directory,
        job,
        policy=mdstats.MaceConfigRealizationPolicy(timeout_seconds=300.0),
    )
    assert realization.passed, realization.to_dict()
    assert realization.parsed_default_dtype == dtype
    smoke = mdstats.run_mace_job_execution_smoke(
        runtime,
        bundle.output_directory,
        job,
        realization,
        tmp_path / f"smoke_{dtype}",
        policy=mdstats.MaceJobExecutionSmokePolicy(
            max_num_epochs=1,
            device="cpu",
            default_dtype="protocol",
            timeout_seconds=900.0,
        ),
    )
    assert smoke.passed, smoke.to_dict()
    assert smoke.precision_transition is not None
    transition = smoke.precision_transition
    assert transition.foundation_precision.uniform_floating_dtype == "float64"
    assert transition.trained_model_precision.uniform_floating_dtype == dtype
    assert transition.extracted_model_precision is not None
    assert transition.extracted_model_precision.uniform_floating_dtype == dtype
    assert transition.conversion_performed is (dtype == "float32")
    assert mdstats.MaceJobExecutionSmokeRecord.from_dict(smoke.to_dict()) == smoke
