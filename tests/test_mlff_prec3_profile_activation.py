from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import campaign_cli
from mdstats.training_data import campaign_execution
from mdstats.training_data import critical_precision as cp


torch = pytest.importorskip("torch")


class _TinyTargetModel(torch.nn.Module):
    def __init__(self, dtype: torch.dtype = torch.float32) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(3, 2, bias=True, dtype=dtype)
        self.register_buffer("scale", torch.ones(1, dtype=dtype))
        self.heads = ["target_head"]

    def forward(self, value):
        return self.linear(value) * self.scale


def _cfg(profile: str) -> dict:
    policy = mdstats.canonical_precision_schedule_policy(profile)
    return {
        "campaign": {"precision_profile": profile},
        "model": {"dtype": policy.model_dtype},
        "training": {
            "dtype": policy.stages[0].dtype,
            "max_num_epochs": 30,
            "precision": {
                "mode": policy.mode,
                "minimum_final_stage_epochs": policy.minimum_final_stage_epochs,
                "minimum_final_stage_gradient_updates": policy.minimum_final_stage_gradient_updates,
                "critical_operation_dtype": policy.critical_operation_dtype,
                "stage": [
                    {
                        "dtype": stage.dtype,
                        "fraction": stage.fraction,
                        "learning_rate_scale": stage.learning_rate_scale,
                    }
                    for stage in policy.stages
                ],
            },
        },
        "evaluation": {"dtype": policy.evaluation_dtype},
        "verification": {"dtype": policy.verification_dtype},
        "export": {"dtype": policy.export_dtype},
    }


def test_adapt_prec1_binary_profiles_bind_invariant_fp64_critical_policy() -> None:
    single = campaign_cli._critical_precision_policy(_cfg("single"))
    double = campaign_cli._critical_precision_policy(_cfg("double"))
    legacy = campaign_cli._critical_precision_policy({"training": {"dtype": "float32"}})

    assert single.observable_output_dtype == "float64"
    assert single.strategy == "scaleshift_mace_0.3.16_runtime_patch_v1"
    assert double.observable_output_dtype == "float64"
    assert legacy.observable_output_dtype == "float64"

    with pytest.raises(campaign_cli.CampaignCliError, match="retired"):
        campaign_cli._critical_precision_policy(_cfg("refine"))


def test_prec3_precision_report_is_profile_complete() -> None:
    payload = campaign_cli._precision_profile_payload(_cfg("refine"))
    assert payload["requested_profile"] == "refine"
    assert payload["critical_operation_dtype"] == "float64"
    assert payload["evaluation_dtype"] == "float64"
    assert payload["verification_dtype"] == "float64"
    assert payload["export_dtype"] == "float64"
    assert [(stage["epoch_count"], stage["dtype"]) for stage in payload["stages"]] == [
        (24, "float32"),
        (6, "float64"),
    ]


def test_adapt_prec1_evaluation_policy_keeps_fp32_model_with_fp64_scientific_reductions() -> None:
    critical = mdstats.MaceCriticalPrecisionPolicy()
    policy = mdstats.CheckpointEvaluationPolicy(
        device="cpu",
        default_dtype="float32",
        critical_precision_policy=critical,
    )
    restored = mdstats.CheckpointEvaluationPolicy.from_dict(policy.to_dict())
    assert restored.default_dtype == "float32"
    assert restored.active_critical_precision_policy.policy_digest == critical.policy_digest
    assert restored.active_critical_precision_policy.observable_output_dtype == "float64"
    assert restored.to_dict()["schema"] == "mdstats.checkpoint-evaluation-policy.v8"


def test_prec3_refine_export_promotes_fp32_target_model_to_fp64(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    output = tmp_path / "refine-target.model"
    torch.save(_TinyTargetModel(torch.float32), source)

    campaign_execution._export_target_head_model_with_dtype(
        source,
        output,
        target_head_name="target_head",
        target_device="cpu",
        wrapper_path=None,
        required_wrapper="mdstats-mace-select-head",
        failure_prefix="PREC3 test export",
        deployment_dtype="float64",
    )

    precision = mdstats.inspect_mace_model_precision(output, expected_dtype="float64")
    assert precision.passed
    assert precision.uniform_floating_dtype == "float64"
    assert (tmp_path / "refine-target.model.manifest.json").is_file()


def test_prec3_single_export_remains_uniform_fp32(tmp_path: Path) -> None:
    source = tmp_path / "source.model"
    output = tmp_path / "single-target.model"
    torch.save(_TinyTargetModel(torch.float64), source)

    campaign_execution._export_target_head_model_with_dtype(
        source,
        output,
        target_head_name="target_head",
        target_device="cpu",
        wrapper_path=None,
        required_wrapper="mdstats-mace-select-head",
        failure_prefix="PREC3 test export",
        deployment_dtype="float32",
    )

    precision = mdstats.inspect_mace_model_precision(output, expected_dtype="float32")
    assert precision.passed
    assert precision.uniform_floating_dtype == "float32"


def test_prec3_native_activation_uninstalls_legacy_patch(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(cp, "uninstall_mace_critical_fp64_patch", lambda: calls.append("uninstall"))
    monkeypatch.setattr(cp, "configure_torch_critical_precision", lambda policy=None: calls.append(policy.observable_output_dtype))
    monkeypatch.setattr(cp, "install_mace_critical_fp64_patch", lambda policy=None: calls.append("install"))

    cp.activate_mace_critical_precision_policy(mdats := mdstats.MaceCriticalPrecisionPolicy.for_dtype("float32"))
    assert mdats.observable_output_dtype == "float32"
    assert calls == ["uninstall", "float32"]
