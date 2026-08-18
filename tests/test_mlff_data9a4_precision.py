from __future__ import annotations

from pathlib import Path

import pytest
import torch

import mdstats
from tests.test_mlff_data8_mace_artifacts import _data7_bundles, _probe


class _Toy(torch.nn.Module):
    def __init__(self, dtype: torch.dtype) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(3, 2, dtype=dtype)
        self.register_buffer("scale", torch.ones(2, dtype=dtype))
        self.register_buffer("indices", torch.arange(2, dtype=torch.int64))


def _save(path: Path, dtype: torch.dtype) -> None:
    torch.save(_Toy(dtype), path)


def test_model_precision_record_detects_float32_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "model.pt"
    _save(path, torch.float32)
    record = mdstats.inspect_mace_model_precision(path, expected_dtype="float32")
    assert record.passed
    assert record.uniform_floating_dtype == "float32"
    assert record.non_floating_buffer_count == 2
    assert mdstats.MaceModelPrecisionRecord.from_dict(record.to_dict()) == record


def test_model_precision_record_rejects_expected_dtype_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "model.pt"
    _save(path, torch.float64)
    record = mdstats.inspect_mace_model_precision(path, expected_dtype="float32")
    assert not record.passed
    assert "unexpected_floating_dtype" in record.failure_reasons



class _Mixed(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.fp32 = torch.nn.Parameter(torch.ones(2, dtype=torch.float32))
        self.fp64 = torch.nn.Parameter(torch.ones(2, dtype=torch.float64))


def test_model_precision_record_rejects_mixed_floating_state(tmp_path: Path) -> None:
    path = tmp_path / "mixed.pt"
    torch.save(_Mixed(), path)
    record = mdstats.inspect_mace_model_precision(path)
    assert not record.passed
    assert record.uniform_floating_dtype is None
    assert "mixed_floating_dtypes" in record.failure_reasons


def test_optimizer_precision_is_protocol_identity(tmp_path: Path) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    foundation_path = tmp_path / "foundation.model"
    _save(foundation_path, torch.float64)
    foundation = mdstats.FoundationCheckpointIdentity.from_file(foundation_path)
    common = dict(
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        foundation_checkpoint=foundation,
        compatibility_probe_digest=_probe().content_digest,
        data7_bundle_digest=bundles[0].content_digest,
        target_train_artifact_digest="1" * 64,
        target_valid_artifact_digest="2" * 64,
        replay_plan_digest=None,
        training_objective_policy_digest="3" * 64,
        configuration_weight_policy_digest="4" * 64,
        checkpoint_metric_policy_digest="5" * 64,
        checkpoint_control_policy=mdstats.MaceCheckpointControlPolicy(),
        selection_size=4,
    )
    fp32 = mdstats.TrainingProtocolIdentity(
        **common, optimizer_policy=mdstats.MaceOptimizerPolicy(default_dtype="float32")
    )
    fp64 = mdstats.TrainingProtocolIdentity(
        **common, optimizer_policy=mdstats.MaceOptimizerPolicy(default_dtype="float64")
    )
    assert fp32.content_digest != fp64.content_digest


def test_smoke_policy_defaults_to_protocol_precision() -> None:
    policy = mdstats.MaceJobExecutionSmokePolicy()
    assert policy.default_dtype == "protocol"
    assert mdstats.MaceJobExecutionSmokePolicy.from_dict(policy.to_dict()) == policy
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.MaceJobExecutionSmokePolicy(default_dtype="float16")
