from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

import mdstats


def _tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "run_mlff_final_gpu_qualification.py"
    spec = importlib.util.spec_from_file_location("mdstats_final_gpu1_tool", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_final_gpu1_preflight_fails_closed_without_locked_models(tmp_path: Path) -> None:
    module = _tool()
    mh1 = tmp_path / "mh1.model"
    mpa0 = tmp_path / "mpa0.model"
    mh1.write_bytes(b"not-the-locked-model")
    mpa0.write_bytes(b"not-the-locked-model")
    payload = module.build_preflight(mh1, mpa0)
    assert payload["schema"] == "mdstats.mlff-final-gpu1.preflight.target-size-v5.2026-08.v11"
    assert payload["qualification_state"] == "deferred_not_executed"
    assert "locked_foundation_model_identities" in payload["blocking_requirements"]
    assert not any(item["identity_passed"] for item in payload["foundation_models"])
    assert payload["policy"]["gpu_qualification_deferred_until_final_release"] is True
    assert payload["policy"]["intermediate_gpu_success_claims_allowed"] is False
    assert payload["gate_schemas"]["cueq_phase1_qualification"] == mdstats.CUEQ_PHASE1_QUALIFICATION_SCHEMA
    assert payload["cueq_phase1_state"]["passed"] is False
    assert payload["gate_schemas"]["cueq_phase2_qualification"] == mdstats.CUEQ_PHASE2_QUALIFICATION_SCHEMA
    assert payload["cueq_phase2_state"]["passed"] is False
    assert "development_path_assessment_missing" in payload["cueq_phase2_state"]["blocking_reasons"]
    assert payload["gate_schemas"]["perf_cert1_qualification"] == mdstats.PERF_CERT1_QUALIFICATION_SCHEMA
    assert payload["gate_schemas"]["final_gpu1_qualification"] == mdstats.FINAL_GPU1_QUALIFICATION_SCHEMA
    assert payload["final_gpu1_policy"]["generated_default_change_authorized"] is False
    assert payload["train2_acceleration_parity_policy"]["float32_rtol"] == 1.0e-5
    assert payload["train2_acceleration_parity_policy"]["float32_atol"] == 1.0e-6
    assert payload["train2_noise_normalized_parity_policy"]["force_distribution_ratio_ceiling"] == 1.25
    assert payload["train2_noise_normalized_parity_policy"]["force_max_absolute_ceiling"] == 1.0e-4
    assert payload["train2_noise_normalized_parity_policy_digest"] == payload["train2_noise_normalized_parity_policy"]["policy_digest"]
    assert payload["train2_acceleration_parity_policy_digest"] == payload["train2_acceleration_parity_policy"]["policy_digest"]
    assert "release_artifact_binding" in payload["blocking_requirements"]
    assert payload["perf_cert1_state"]["passed"] is False
    assert "authoritative_e3nn_baseline_missing" in payload["perf_cert1_state"]["blocking_reasons"]
    assert "accelerated_profile_evidence_missing" in payload["perf_cert1_state"]["blocking_reasons"]
    assert "short_paired_adaptation_missing" in payload["cueq_phase1_state"]["blocking_reasons"]


def test_final_gpu1_locked_scope_contains_science_and_performance_gates() -> None:
    module = _tool()
    assert module.LOCKED_MODELS["mace_mh_1"]["sha256"] == "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"
    assert module.LOCKED_MODELS["mace_mpa_0"]["sha256"] == "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    assert "SIZE_FIDELITY1_EXHAUSTIVE_CALIBRATION" in module.DEFERRED_GPU_GATES
    assert "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION" not in module.DEFERRED_GPU_GATES
    assert "TARGET_DATA2C_MVMIGRATE1_LEARNING_CONTROLS" not in module.DEFERRED_GPU_GATES
    assert "PERF_P2R_WHOLE_FUNNEL_GPU_PERFORMANCE" in module.DEFERRED_GPU_GATES
    assert "CUEQ_DEP1_RUNTIME_FREEZE" in module.DEFERRED_GPU_GATES
    assert "CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION" in module.DEFERRED_GPU_GATES
    assert "PERF_P5_ACCELERATOR_PERSISTENCE_REUSE" in module.DEFERRED_GPU_GATES
    assert "MH1_DEPLOY1_MLIAP_EXPORT_AND_LAMMPS_RUN0" in module.OPTIONAL_FINAL_DEPLOYMENT_GATES


@pytest.mark.slow
def test_final_gpu1_real_supplied_model_identities_when_mounted() -> None:
    module = _tool()
    mh1 = Path(os.environ.get("MDSTATS_TEST_MH1_MODEL", "/mnt/data/mace-mh-1.model"))
    mpa0 = Path(os.environ.get("MDSTATS_TEST_MPA0_MODEL", "/mnt/data/mace-mpa-0-medium.model"))
    if not mh1.is_file() or not mpa0.is_file():
        pytest.skip("locked foundation models are not mounted")
    payload = module.build_preflight(mh1, mpa0)
    assert all(item["identity_passed"] for item in payload["foundation_models"])
