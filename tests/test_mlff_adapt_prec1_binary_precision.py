from __future__ import annotations

import argparse
from pathlib import Path
import tomllib

import pytest

import mdstats
from mdstats.training_data import campaign_cli


def _cfg(profile: str = "single") -> dict:
    text = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="replay-train.xyz",
        replay_monitor="replay-monitor.xyz",
        precision_profile=profile,
        acceleration_backend="e3nn",
        default_device="cpu",
    )
    return tomllib.loads(text)


def test_init_parser_exposes_only_binary_precision_choices() -> None:
    parser = campaign_cli.build_parser()
    # argparse should reject retired production profiles before config generation.
    with pytest.raises(SystemExit):
        parser.parse_args(["init", "--precision", "refine"])
    with pytest.raises(SystemExit):
        parser.parse_args(["init", "--precision", "mixed"])
    assert parser.parse_args(["init", "--precision", "single"]).precision == "single"
    assert parser.parse_args(["init", "--precision", "double"]).precision == "double"


@pytest.mark.parametrize(("profile", "dtype"), [("single", "float32"), ("double", "float64")])
def test_generated_binary_config_has_one_model_dtype_and_no_schedule(profile: str, dtype: str) -> None:
    cfg = _cfg(profile)
    assert cfg["campaign"]["precision_profile"] == profile
    assert cfg["model"]["dtype"] == dtype
    assert cfg["training"]["dtype"] == dtype
    assert cfg["evaluation"]["dtype"] == dtype
    assert cfg["verification"]["dtype"] == dtype
    assert cfg["export"]["dtype"] == dtype
    assert "precision" not in cfg["training"]

    contract = campaign_cli._binary_model_precision_contract(cfg)
    assert contract["requested_profile"] == profile
    assert contract["model_dtype"] == dtype
    assert campaign_cli._precision_schedule_policy(cfg) is None

    payload = campaign_cli._precision_profile_payload(cfg)
    assert payload["mode"] == "binary_model_dtype"
    assert payload["model_dtype"] == dtype
    assert payload["training_dtype"] == dtype
    assert payload["evaluation_dtype"] == dtype
    assert payload["verification_dtype"] == dtype
    assert payload["export_dtype"] == dtype
    assert payload["critical_operation_dtype"] == "float64"
    assert payload["analysis_dtype"] == "float64"
    assert payload["stages"] == []


@pytest.mark.parametrize("field", ["model", "training", "evaluation", "verification", "export"])
def test_binary_precision_rejects_cross_dtype_inference_or_export_surface(field: str) -> None:
    cfg = _cfg("single")
    cfg[field]["dtype"] = "float64"
    with pytest.raises(campaign_cli.CampaignCliError, match="requires learned-model dtype float32"):
        campaign_cli._binary_model_precision_contract(cfg)


def test_single_optimizer_is_fp32_model_with_fp64_critical_policy_and_no_schedule() -> None:
    cfg = _cfg("single")
    optimizer = campaign_cli._optimizer_policy(cfg, seed=1, num_workers=0)
    assert optimizer.default_dtype == "float32"
    assert optimizer.precision_schedule_policy is None
    assert optimizer.critical_precision_policy.canonical_dtype == "float64"
    assert optimizer.critical_precision_policy.observable_output_dtype == "float64"
    assert optimizer.to_dict()["schema"] == "mdstats.mace-optimizer-policy.v4"


def test_double_optimizer_is_fp64_model_with_fp64_critical_policy_and_no_schedule() -> None:
    cfg = _cfg("double")
    optimizer = campaign_cli._optimizer_policy(cfg, seed=2, num_workers=0)
    assert optimizer.default_dtype == "float64"
    assert optimizer.precision_schedule_policy is None
    assert optimizer.critical_precision_policy.canonical_dtype == "float64"


def _historical_refine_cfg() -> dict:
    policy = mdstats.canonical_precision_schedule_policy("refine")
    return {
        "campaign": {"precision_profile": "refine"},
        "model": {"dtype": "float64"},
        "training": {
            "dtype": "float32",
            "max_num_epochs": 30,
            "precision": {
                "mode": "staged",
                "minimum_final_stage_epochs": policy.minimum_final_stage_epochs,
                "minimum_final_stage_gradient_updates": policy.minimum_final_stage_gradient_updates,
                "preserve_optimizer_state": True,
                "preserve_scheduler_state": True,
                "preserve_ema_state": True,
                "critical_operation_dtype": "float64",
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
        "evaluation": {"dtype": "float64"},
        "verification": {"dtype": "float64"},
        "export": {"dtype": "float64"},
    }


def test_historical_refine_is_readable_but_not_production_executable() -> None:
    cfg = _historical_refine_cfg()
    payload = campaign_cli._precision_profile_payload(cfg)
    assert payload["historical_read_only"] is True
    assert payload["requested_profile"] == "refine"
    assert [(stage["epoch_count"], stage["dtype"]) for stage in payload["stages"]] == [
        (24, "float32"),
        (6, "float64"),
    ]
    with pytest.raises(campaign_cli.CampaignCliError, match="retired"):
        campaign_cli._binary_model_precision_contract(cfg)
    with pytest.raises(campaign_cli.CampaignCliError, match="retired"):
        campaign_cli._optimizer_policy(cfg, seed=1, num_workers=0)


def test_historical_single_stage_metadata_is_validated_but_not_activated() -> None:
    cfg = _cfg("single")
    cfg["training"]["precision"] = {
        "mode": "single_stage",
        "minimum_final_stage_epochs": 0,
        "minimum_final_stage_gradient_updates": 0,
        "preserve_optimizer_state": True,
        "preserve_scheduler_state": True,
        "preserve_ema_state": True,
        # Historical 0.20.121 single profiles used FP32 here. It is retained only
        # as old metadata; ADAPT-PREC1 runtime critical arithmetic is now FP64.
        "critical_operation_dtype": "float32",
        "stage": [
            {"dtype": "float32", "fraction": 1.0, "learning_rate_scale": 1.0}
        ],
    }
    contract = campaign_cli._binary_model_precision_contract(cfg)
    assert contract["model_dtype"] == "float32"
    assert contract["historical_schedule"] is not None
    assert campaign_cli._precision_schedule_policy(cfg) is None
    optimizer = campaign_cli._optimizer_policy(cfg, seed=1, num_workers=0)
    assert optimizer.precision_schedule_policy is None
    assert optimizer.critical_precision_policy.canonical_dtype == "float64"


def test_new_data8_protocol_has_no_resolved_precision_schedule(tmp_path: Path) -> None:
    from tests.test_mlff_data8_mace_artifacts import _data7_bundles, _foundation, _probe

    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    optimizer = campaign_cli._optimizer_policy(_cfg("single"), seed=1, num_workers=0)
    bundle = mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=tmp_path / "data8_adapt_prec1",
        foundation_checkpoint=_foundation(tmp_path),
        compatibility_probe=_probe(),
        optimizer_policy=optimizer,
        require_foundation_residual_e0=False,
    )
    assert bundle.jobs
    assert all(job.protocol.resolved_precision_schedule is None for job in bundle.jobs)
    assert all(job.protocol.optimizer_policy.precision_schedule_policy is None for job in bundle.jobs)
    assert all(job.protocol.optimizer_policy.default_dtype == "float32" for job in bundle.jobs)
