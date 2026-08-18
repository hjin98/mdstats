#!/usr/bin/env python3
"""FINAL-GPU1 release preflight, immutable evidence handoff, and reducer.

The tool separates readiness from qualification. It can record negative/deferred
preflight evidence on a CPU-only development host, but positive FINAL-GPU1
authority exists only after the complete release-matched workstation matrix is
registered, integrity-verified, and reduced.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Any, Mapping

import mdstats

SCHEMA = "mdstats.mlff-final-gpu1.preflight.2026-08.v10"
LOCKED_MODELS = {
    "mace_mh_1": {
        "label": "MACE-MH-1",
        "sha256": "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde",
        "required_head": "omat_pbe",
    },
    "mace_mpa_0": {
        "label": "MACE-MPA-0-medium",
        "sha256": "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638",
        "required_head": "default",
    },
}
DEFERRED_GPU_GATES = (
    "PREC3_REAL_CUEQ_ACTIVATION",
    "MH1_ACCEL1_CUEQ_NUMERICAL_PARITY",
    "MH1_DATA6_1_CUEQ_DESCRIPTOR_SELECTION_PARITY",
    "MH1_TRAIN1_CUEQ_TRAINING_REALIZATION",
    "MH1_CERT1_GENERATED_DEFAULT_CUEQ_MATRIX",
    "SIZE_FIDELITY1_EXHAUSTIVE_CALIBRATION",
    "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION",
    "TARGET_DATA2C_MVMIGRATE1_LEARNING_CONTROLS",
    "REPLAY_UNIFY1_GPU_PSEUDOLABEL_EXECUTION",
    "PERF_P2R_WHOLE_FUNNEL_GPU_PERFORMANCE",
    "CUEQ_DEP1_RUNTIME_FREEZE",
    "CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION",
    "CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL",
    "PERF_CERT1_END_TO_END_CERTIFICATION",
    "VRAM1_PERF_P4_ACCELERATOR_MEMORY_THROUGHPUT",
    "PERF_P5_ACCELERATOR_PERSISTENCE_REUSE",
    "E3NN_BASELINE_COMPLETE_CAMPAIGN",
)
OPTIONAL_FINAL_DEPLOYMENT_GATES = (
    "MH1_DEPLOY1_MLIAP_EXPORT_AND_LAMMPS_RUN0",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _dist_version(name: str) -> str | None:
    try:
        import importlib.metadata as metadata
        return metadata.version(name)
    except Exception:
        return None



def _dist_version_candidates(*names: str) -> str | None:
    for name in names:
        value = _dist_version(name)
        if value is not None:
            return value
    return None

def _torch_snapshot() -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": _module_available("torch"),
        "version": _dist_version("torch"),
        "cuda_available": False,
        "cuda_device_count": 0,
        "cuda_version": None,
        "devices": [],
    }
    if not result["available"]:
        return result
    try:
        import torch
        result["version"] = str(torch.__version__)
        result["cuda_available"] = bool(torch.cuda.is_available())
        result["cuda_device_count"] = int(torch.cuda.device_count()) if torch.cuda.is_available() else 0
        result["cuda_version"] = getattr(torch.version, "cuda", None)
        devices = []
        for index in range(result["cuda_device_count"]):
            props = torch.cuda.get_device_properties(index)
            devices.append({
                "index": index,
                "name": props.name,
                "total_memory_bytes": int(props.total_memory),
                "compute_capability": [int(props.major), int(props.minor)],
            })
        result["devices"] = devices
    except Exception as exc:
        result["probe_error"] = f"{type(exc).__name__}: {exc}"
    return result


def _nvidia_smi_snapshot() -> dict[str, Any]:
    exe = shutil.which("nvidia-smi")
    if exe is None:
        return {"available": False}
    command = [
        exe,
        "--query-gpu=index,name,driver_version,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=15)
        return {
            "available": True,
            "returncode": int(completed.returncode),
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"available": True, "probe_error": f"{type(exc).__name__}: {exc}"}


def _model_record(path: Path, family: str) -> dict[str, Any]:
    expected = LOCKED_MODELS[family]
    record: dict[str, Any] = {
        "family": family,
        "label": expected["label"],
        "required_head": expected["required_head"],
        "path": str(path.resolve()),
        "exists": path.is_file(),
        "expected_sha256": expected["sha256"],
    }
    if path.is_file():
        record["size_bytes"] = path.stat().st_size
        record["sha256"] = _sha256(path)
        record["identity_passed"] = record["sha256"] == expected["sha256"]
    else:
        record["sha256"] = None
        record["identity_passed"] = False
    return record


def build_preflight(mh1_model: Path, mpa0_model: Path, release_archive: Path | None = None) -> dict[str, Any]:
    modules = {
        name: {"available": _module_available(module), "version": _dist_version(dist)}
        for name, module, dist in (
            ("mace", "mace", "mace-torch"),
            ("e3nn", "e3nn", "e3nn"),
            ("cuequivariance", "cuequivariance", "cuequivariance"),
            ("cuequivariance_torch", "cuequivariance_torch", "cuequivariance-torch"),
            ("openequivariance", "openequivariance", "openequivariance"),
        )
    }
    modules["cuequivariance_ops_torch"] = {
        "available": _module_available("cuequivariance_ops_torch"),
        "version": _dist_version_candidates(
            "cuequivariance-ops-torch-cu13",
            "cuequivariance-ops-torch-cu12",
            "cuequivariance-ops-torch-cu11",
            "cuequivariance-ops-torch",
        ),
    }
    models = [
        _model_record(mh1_model, "mace_mh_1"),
        _model_record(mpa0_model, "mace_mpa_0"),
    ]
    torch = _torch_snapshot()
    cuda_ready = bool(torch.get("cuda_available"))
    try:
        import mdstats
        cueq_dep1_record = mdstats.capture_cueq_dep1_runtime()
        cueq_dep1 = cueq_dep1_record.to_dict()
        cueq_ready = bool(cueq_dep1_record.passed)
        cueq_phase1_record = mdstats.build_cueq_phase1_qualification(runtime=cueq_dep1_record)
        cueq_phase2_record = mdstats.build_cueq_phase2_qualification(runtime=cueq_dep1_record)
        perf_cert1_record = mdstats.build_perf_cert1_qualification(
            phase1=cueq_phase1_record, phase2=cueq_phase2_record
        )
        cueq_phase1 = cueq_phase1_record.to_dict()
        cueq_phase2 = cueq_phase2_record.to_dict()
        perf_cert1 = perf_cert1_record.to_dict()
    except Exception as exc:
        cueq_dep1 = {
            "schema": "mdstats.cueq-dep1-runtime.capture-error.v1",
            "passed": False,
            "blocking_reasons": ["cueq_dep1_capture_error"],
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        cueq_ready = False
        cueq_phase1 = {
            "schema": "mdstats.cueq-phase1-qualification.capture-error.v1",
            "passed": False,
            "blocking_reasons": ["CUEQ_DEP1_RUNTIME_FREEZE"],
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        cueq_phase2 = {
            "schema": "mdstats.cueq-phase2-qualification.capture-error.v1",
            "passed": False,
            "blocking_reasons": ["CUEQ_DEP1_RUNTIME_FREEZE", "development_path_assessment_missing"],
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        perf_cert1 = {
            "schema": "mdstats.perf-cert1-qualification.capture-error.v1",
            "passed": False,
            "blocking_reasons": [
                "CUEQ_PHASE1_TRAINING_QUALIFICATION",
                "authoritative_e3nn_baseline_missing",
                "accelerated_profile_evidence_missing",
            ],
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    model_ready = all(bool(item["identity_passed"]) for item in models)
    release_record = {
        "path": None if release_archive is None else str(Path(release_archive).resolve()),
        "exists": False if release_archive is None else Path(release_archive).is_file(),
        "sha256": None,
    }
    if release_archive is not None and Path(release_archive).is_file():
        release_record["sha256"] = _sha256(Path(release_archive))
    release_ready = release_record["sha256"] is not None
    # Bind FINAL-GPU1 readiness to both permanent TRAIN2 parity authorities:
    # the tight stable-channel policy and the FP32 noise-normalized force policy.
    from mdstats.training_data import campaign_cli as _campaign_cli
    train2_parity_policy = _campaign_cli._training_acceleration_parity_policy()
    train2_noise_policy = _campaign_cli._training_acceleration_noise_normalized_policy()
    return {
        "schema": SCHEMA,
        "qualification_state": "ready_for_final_gpu_execution" if (cuda_ready and cueq_ready and model_ready and release_ready) else "deferred_not_executed",
        "policy": {
            "gpu_qualification_deferred_until_final_release": True,
            "intermediate_gpu_success_claims_allowed": False,
            "cpu_reference_qualification_continues_during_development": True,
        },
        "host": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "torch": torch,
        "nvidia_smi": _nvidia_smi_snapshot(),
        "modules": modules,
        "cueq_dep1_runtime": cueq_dep1,
        "cueq_phase1_state": cueq_phase1,
        "cueq_phase2_state": cueq_phase2,
        "perf_cert1_state": perf_cert1,
        "gate_schemas": {
            "cueq_dep1_runtime": "mdstats.cueq-dep1-runtime.v1",
            "cueq_phase1_qualification": "mdstats.cueq-phase1-qualification.v1",
            "cueq_phase2_qualification": "mdstats.cueq-phase2-qualification.v1",
            "perf_cert1_qualification": mdstats.PERF_CERT1_QUALIFICATION_SCHEMA,
            "size_fidelity2_qualification": mdstats.SIZE_FIDELITY2_REPORT_SCHEMA,
            "target_mv_learning_control": mdstats.TARGET_MV_LEARNING_CONTROL_REPORT_SCHEMA,
            "final_gpu1_qualification": mdstats.FINAL_GPU1_QUALIFICATION_SCHEMA,
        },
        "executables": {"lmp": shutil.which("lmp"), "python": sys.executable},
        "foundation_models": models,
        "release_artifact": release_record,
        "final_gpu1_policy": mdstats.FinalGpu1Policy().to_dict(),
        "train2_acceleration_parity_policy": train2_parity_policy.to_dict(),
        "train2_acceleration_parity_policy_digest": train2_parity_policy.policy_digest,
        "train2_noise_normalized_parity_policy": train2_noise_policy.to_dict(),
        "train2_noise_normalized_parity_policy_digest": train2_noise_policy.policy_digest,
        "deferred_gpu_gates": list(DEFERRED_GPU_GATES),
        "optional_final_deployment_gates": list(OPTIONAL_FINAL_DEPLOYMENT_GATES),
        "blocking_requirements": [
            name for name, passed in (
                ("locked_foundation_model_identities", model_ready),
                ("torch_cuda_available", cuda_ready),
                ("cueq_dep1_runtime_freeze", cueq_ready),
                ("release_artifact_binding", release_ready),
            ) if not passed
        ],
    }



def _json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_read(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


def _safe_gate_filename(gate_id: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in gate_id).strip("_") + ".json"


def _handoff_manifest(root: Path) -> Path:
    return root / "final_gpu1_handoff.json"


def initialize_handoff(root: Path, mh1_model: Path, mpa0_model: Path, release_archive: Path) -> dict[str, Any]:
    import mdstats

    root = root.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError(
            f"FINAL-GPU1 handoff root already contains data: {root}. "
            "Reuse it with status/record/reduce, or choose a new run root."
        )
    root.mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir(exist_ok=True)
    (root / "records").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    preflight = build_preflight(mh1_model, mpa0_model, release_archive)
    _json_write(root / "preflight.json", preflight)
    if not all(bool(item.get("identity_passed")) for item in preflight["foundation_models"]):
        raise ValueError("FINAL-GPU1 handoff initialization requires both locked foundation-model identities to pass.")
    release_sha = str(preflight["release_artifact"]["sha256"] or "")
    if not release_sha:
        raise ValueError("Release archive is required and must be readable for FINAL-GPU1 handoff initialization.")
    policy = mdstats.FinalGpu1Policy()
    manifest = {
        "schema": "mdstats.mlff-final-gpu1.handoff.2026-08.v1",
        "preflight_schema": SCHEMA,
        "final_qualification_schema": mdstats.FINAL_GPU1_QUALIFICATION_SCHEMA,
        "release_archive": str(release_archive.resolve()),
        "release_artifact_sha256": release_sha,
        "foundation_models": preflight["foundation_models"],
        "policy": policy.to_dict(),
        "train2_acceleration_parity_policy": preflight["train2_acceleration_parity_policy"],
        "train2_acceleration_parity_policy_digest": preflight["train2_acceleration_parity_policy_digest"],
        "train2_noise_normalized_parity_policy": preflight["train2_noise_normalized_parity_policy"],
        "train2_noise_normalized_parity_policy_digest": preflight["train2_noise_normalized_parity_policy_digest"],
        "matrix": [
            {
                "gate_id": gate,
                "acceptance": policy.acceptance_for(gate),
                "record": f"records/{_safe_gate_filename(gate)}",
                "state": "pending",
            }
            for gate in policy.all_gates
        ],
        "qualification_output": "FINAL_GPU1_QUALIFICATION.json",
        "instructions": {
            "evidence_registration": "Register each GPU result with the record subcommand; never edit record JSON by hand.",
            "reduction": "Run reduce with the positive CUEQ-DEP1 runtime, PERF-CERT1, SIZE-FIDELITY2, and MVMIGRATE1 learning-control records after all required evidence is registered.",
            "source_edits_allowed": False,
            "generated_default_change_authorized": False,
        },
    }
    _json_write(_handoff_manifest(root), manifest)
    return manifest


def _root_relative_path(root: Path, relative_path: str, *, label: str, failures: list[str]) -> Path | None:
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        failures.append(f"{label}:path_escape")
        return None
    return candidate


def verify_handoff_integrity(root: Path) -> dict[str, Any]:
    """Re-hash every mutable handoff input and registered evidence artifact."""
    import mdstats

    root = root.resolve()
    manifest = _json_read(_handoff_manifest(root))
    failures: list[str] = []

    try:
        policy = mdstats.FinalGpu1Policy.from_dict(manifest["policy"])
        default_policy = mdstats.FinalGpu1Policy()
        if policy.content_digest != default_policy.content_digest:
            failures.append("policy_record:authority_changed")
    except Exception as exc:
        policy = None
        failures.append(f"policy_record:{type(exc).__name__}")

    try:
        from mdstats.training_data import campaign_cli as _campaign_cli
        active_train2_parity = _campaign_cli._training_acceleration_parity_policy()
        recorded_train2_parity = mdstats.MaceAccelerationParityPolicy.from_dict(
            manifest["train2_acceleration_parity_policy"]
        )
        if recorded_train2_parity.policy_digest != active_train2_parity.policy_digest:
            failures.append("train2_parity_policy:authority_changed")
        if str(manifest.get("train2_acceleration_parity_policy_digest", "")) != active_train2_parity.policy_digest:
            failures.append("train2_parity_policy:digest_changed")
        active_noise = _campaign_cli._training_acceleration_noise_normalized_policy()
        recorded_noise = mdstats.TrainingAccelerationNoiseNormalizedParityPolicy.from_dict(
            manifest["train2_noise_normalized_parity_policy"]
        )
        if recorded_noise.policy_digest != active_noise.policy_digest:
            failures.append("train2_noise_parity_policy:authority_changed")
        if str(manifest.get("train2_noise_normalized_parity_policy_digest", "")) != active_noise.policy_digest:
            failures.append("train2_noise_parity_policy:digest_changed")
    except Exception as exc:
        failures.append(f"train2_parity_policy:{type(exc).__name__}")

    release_expected = str(manifest.get("release_artifact_sha256", ""))
    release_observed: str | None = None
    release_value = manifest.get("release_archive")
    if not release_value:
        failures.append("release_artifact:path_missing")
    else:
        release_path = Path(str(release_value)).expanduser().resolve()
        if not release_path.is_file():
            failures.append("release_artifact:file_missing")
        else:
            release_observed = _sha256(release_path)
            if release_observed != release_expected:
                failures.append("release_artifact:sha256_changed")

    foundations: dict[str, str] = {}
    foundation_items = tuple(manifest.get("foundation_models", ()))
    foundation_families = [str(item.get("family", "")).strip() or "unknown" for item in foundation_items]
    if set(foundation_families) != set(LOCKED_MODELS) or len(foundation_families) != len(LOCKED_MODELS):
        failures.append("foundation_models:locked_set_changed")
    for item, family in zip(foundation_items, foundation_families):
        model_path = Path(str(item.get("path", ""))).expanduser().resolve()
        expected = item.get("sha256")
        locked = LOCKED_MODELS.get(family, {}).get("sha256")
        if locked is None or expected is None or str(expected) != str(locked):
            failures.append(f"foundation_model:{family}:locked_identity_changed")
        if not model_path.is_file():
            failures.append(f"foundation_model:{family}:file_missing")
            continue
        observed = _sha256(model_path)
        foundations[family] = observed
        if expected is None or observed != str(expected):
            failures.append(f"foundation_model:{family}:sha256_changed")

    matrix = manifest.get("matrix", ())
    matrix_gate_list = [str(item.get("gate_id", "")) for item in matrix]
    matrix_gates = set(matrix_gate_list)
    if len(matrix_gate_list) != len(matrix_gates):
        failures.append("matrix:duplicate_gate")
    if policy is not None:
        expected_gate_list = list(policy.all_gates)
        if matrix_gate_list != expected_gate_list:
            failures.append("matrix:policy_gate_order_changed")
        allowed_states = {"pending", "pass", "fail", "superseded", "not_applicable"}
        for item in matrix:
            gate = str(item.get("gate_id", ""))
            try:
                expected_acceptance = policy.acceptance_for(gate)
            except Exception:
                failures.append(f"matrix:{gate}:unknown_gate")
                continue
            if str(item.get("acceptance", "")) != expected_acceptance:
                failures.append(f"matrix:{gate}:acceptance_changed")
            expected_record = f"records/{_safe_gate_filename(gate)}"
            if str(item.get("record", "")) != expected_record:
                failures.append(f"matrix:{gate}:record_path_changed")
            if str(item.get("state", "pending")) not in allowed_states:
                failures.append(f"matrix:{gate}:invalid_state")
    parsed_records = 0
    for item in matrix:
        gate = str(item.get("gate_id", ""))
        state = str(item.get("state", "pending"))
        record_rel = str(item.get("record", ""))
        record_path = _root_relative_path(root, record_rel, label=f"record:{gate}", failures=failures)
        if record_path is None:
            continue
        if state == "pending":
            if record_path.exists():
                failures.append(f"record:{gate}:pending_record_present")
            continue
        if not record_path.is_file():
            failures.append(f"record:{gate}:file_missing")
            continue
        try:
            record = mdstats.FinalGpu1EvidenceRecord.from_dict(_json_read(record_path))
        except Exception as exc:
            failures.append(f"record:{gate}:invalid:{type(exc).__name__}")
            continue
        parsed_records += 1
        if record.gate_id != gate:
            failures.append(f"record:{gate}:gate_mismatch")
        if record.disposition != state:
            failures.append(f"record:{gate}:state_mismatch")
        if policy is not None:
            try:
                if record.acceptance != policy.acceptance_for(gate):
                    failures.append(f"record:{gate}:acceptance_mismatch")
            except Exception:
                failures.append(f"record:{gate}:unknown_gate")
        if record.release_artifact_sha256 != release_expected:
            failures.append(f"record:{gate}:release_binding_mismatch")
        if record.evidence_present:
            if not record.evidence_relative_path:
                failures.append(f"evidence:{gate}:relative_path_missing")
                continue
            evidence_path = _root_relative_path(
                root, record.evidence_relative_path, label=f"evidence:{gate}", failures=failures
            )
            if evidence_path is None:
                continue
            if not evidence_path.is_file():
                failures.append(f"evidence:{gate}:file_missing")
                continue
            if _sha256(evidence_path) != record.evidence_sha256:
                failures.append(f"evidence:{gate}:sha256_changed")
                continue
            try:
                payload = _json_read(evidence_path)
            except Exception as exc:
                failures.append(f"evidence:{gate}:invalid_json:{type(exc).__name__}")
                continue
            schema = payload.get("schema")
            content_digest = payload.get("content_digest")
            if record.evidence_schema != (None if schema is None else str(schema)):
                failures.append(f"evidence:{gate}:schema_changed")
            if record.evidence_content_digest != (None if content_digest is None else str(content_digest)):
                failures.append(f"evidence:{gate}:content_digest_changed")

    records_dir = root / "records"
    if records_dir.is_dir():
        for path in records_dir.glob("*.json"):
            try:
                payload = _json_read(path)
                gate = str(payload.get("gate_id", ""))
            except Exception:
                gate = ""
            if gate not in matrix_gates:
                failures.append(f"record_file:{path.name}:unregistered_gate")

    unique_failures = tuple(dict.fromkeys(failures))
    return {
        "schema": "mdstats.mlff-final-gpu1.handoff-integrity.2026-08.v1",
        "root": str(root),
        "passed": not unique_failures,
        "failures": list(unique_failures),
        "release_artifact_expected_sha256": release_expected or None,
        "release_artifact_observed_sha256": release_observed,
        "foundation_model_observed_sha256": foundations,
        "registered_record_count": parsed_records,
        "matrix_item_count": len(matrix),
    }


def register_evidence(
    root: Path,
    gate_id: str,
    evidence_path: Path,
    *,
    disposition: str,
    cueq_runtime_digest: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    import mdstats

    root = root.resolve()
    integrity = verify_handoff_integrity(root)
    if not integrity["passed"]:
        raise ValueError(
            "FINAL-GPU1 handoff integrity is already broken: " + ", ".join(integrity["failures"])
        )
    manifest = _json_read(_handoff_manifest(root))
    policy = mdstats.FinalGpu1Policy.from_dict(manifest["policy"])
    acceptance = policy.acceptance_for(gate_id)
    source = evidence_path.resolve()
    payload = _json_read(source)

    inferred: str | None = None
    if isinstance(payload.get("passed"), bool):
        inferred = "pass" if payload["passed"] else "fail"
    else:
        state = str(payload.get("status", "")).strip().lower()
        if state in {"pass", "passed", "qualified", "closed"}:
            inferred = "pass"
        elif state in {"fail", "failed", "rejected"}:
            inferred = "fail"
    if disposition == "auto":
        if inferred is None:
            raise ValueError(
                "Could not infer evidence disposition. Supply --disposition pass|fail|superseded|not_applicable explicitly."
            )
        disposition = inferred
    elif disposition in {"pass", "fail"} and inferred is not None and disposition != inferred:
        raise ValueError(
            f"Explicit disposition {disposition!r} contradicts evidence payload state {inferred!r}."
        )

    if cueq_runtime_digest is None:
        if gate_id == "CUEQ_DEP1_RUNTIME_FREEZE":
            cueq_runtime_digest = payload.get("content_digest")
        elif gate_id in {"CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION", "CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL"}:
            cueq_runtime_digest = payload.get("cueq_dep1_runtime_digest")
        elif gate_id == "PERF_CERT1_END_TO_END_CERTIFICATION":
            cueq_runtime_digest = payload.get("upstream", {}).get("cueq_dep1_runtime_digest")
    if gate_id in policy.runtime_bound_gates and cueq_runtime_digest is None:
        raise ValueError(
            f"FINAL-GPU1 gate {gate_id} requires the frozen CUEQ-DEP1 runtime digest. "
            "Supply --cueq-runtime-digest when the producer schema does not expose it."
        )

    evidence_dir = root / "evidence"
    target = evidence_dir / _safe_gate_filename(gate_id)
    record_path = root / "records" / _safe_gate_filename(gate_id)
    record = mdstats.FinalGpu1EvidenceRecord.from_json_file(
        gate_id=gate_id,
        acceptance=acceptance,
        disposition=disposition,
        release_artifact_sha256=str(manifest["release_artifact_sha256"]),
        evidence_path=source,
        cueq_dep1_runtime_digest=cueq_runtime_digest,
        evidence_relative_path=str(target.relative_to(root)),
        note=note,
    )
    if record_path.is_file():
        existing = mdstats.FinalGpu1EvidenceRecord.from_dict(_json_read(record_path))
        if existing.content_digest == record.content_digest and target.is_file() and _sha256(target) == existing.evidence_sha256:
            return existing.to_dict()
        raise ValueError(
            f"FINAL-GPU1 gate {gate_id} is already registered in this immutable run root. "
            "Use a new run root for replacement evidence."
        )
    if target.exists():
        raise ValueError(f"Unregistered evidence target already exists: {target}")
    shutil.copy2(source, target)
    _json_write(record_path, record.to_dict())
    for item in manifest["matrix"]:
        if item["gate_id"] == gate_id:
            item["state"] = disposition
            item["record"] = str(record_path.relative_to(root))
            break
    _json_write(_handoff_manifest(root), manifest)
    return record.to_dict()

def reduce_handoff(
    root: Path,
    runtime_path: Path,
    perf_cert1_path: Path,
    size_fidelity2_path: Path,
    mv_learning_control_path: Path,
    output: Path | None = None,
) -> dict[str, Any]:
    import mdstats

    root = root.resolve()
    manifest = _json_read(_handoff_manifest(root))
    integrity = verify_handoff_integrity(root)
    integrity_failures = list(integrity["failures"])
    runtime = mdstats.CueqDep1RuntimeRecord.from_dict(_json_read(runtime_path))
    perf = mdstats.PerfCert1QualificationRecord.from_dict(_json_read(perf_cert1_path))
    size_fidelity2 = mdstats.SizeFidelity2QualificationReport.from_dict(_json_read(size_fidelity2_path))
    mv_learning_control = mdstats.TargetMultiViewLearningControlReport.from_dict(_json_read(mv_learning_control_path))
    records = []
    for path in sorted((root / "records").glob("*.json")):
        try:
            records.append(mdstats.FinalGpu1EvidenceRecord.from_dict(_json_read(path)))
        except Exception as exc:
            integrity_failures.append(f"record:{path.name}:invalid:{type(exc).__name__}")
    foundations = dict(integrity.get("foundation_model_observed_sha256", {}))
    observed_release = integrity.get("release_artifact_observed_sha256")
    release_digest = str(observed_release or manifest["release_artifact_sha256"])
    record = mdstats.build_final_gpu1_qualification(
        release_artifact_sha256=release_digest,
        foundation_model_sha256=foundations,
        cueq_dep1_runtime=runtime,
        perf_cert1=perf,
        size_fidelity2=size_fidelity2,
        target_mv_learning_control=mv_learning_control,
        evidence=records,
        policy=mdstats.FinalGpu1Policy.from_dict(manifest["policy"]),
        handoff_integrity_failures=tuple(dict.fromkeys(integrity_failures)),
    )
    target = output.resolve() if output is not None else root / "FINAL_GPU1_QUALIFICATION.json"
    _json_write(target, record.to_dict())
    return record.to_dict()

def handoff_status(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = _json_read(_handoff_manifest(root))
    counts: dict[str, int] = {}
    for item in manifest["matrix"]:
        counts[item["state"]] = counts.get(item["state"], 0) + 1
    integrity = verify_handoff_integrity(root)
    qualification = root / "FINAL_GPU1_QUALIFICATION.json"
    result = {
        "schema": "mdstats.mlff-final-gpu1.handoff-status.2026-08.v1",
        "root": str(root),
        "release_artifact_sha256": manifest["release_artifact_sha256"],
        "matrix_counts": counts,
        "matrix": manifest["matrix"],
        "handoff_integrity_passed": integrity["passed"],
        "handoff_integrity_failures": integrity["failures"],
        "qualification_present": qualification.is_file(),
    }
    if qualification.is_file():
        payload = _json_read(qualification)
        result["qualification_passed"] = bool(payload.get("passed", False))
        result["blocking_reasons"] = list(payload.get("blocking_reasons", ()))
        result["recommended_profile_id"] = payload.get("authorization", {}).get("recommended_profile_id")
    return result

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="Capture release/model/runtime readiness without claiming GPU qualification.")
    pre.add_argument("--mh1-model", type=Path, required=True)
    pre.add_argument("--mpa0-model", type=Path, required=True)
    pre.add_argument("--release-archive", type=Path)
    pre.add_argument("--output", type=Path, required=True)

    init = sub.add_parser("init", help="Initialize a content-addressed FINAL-GPU1 qualification root.")
    init.add_argument("--root", type=Path, required=True)
    init.add_argument("--mh1-model", type=Path, required=True)
    init.add_argument("--mpa0-model", type=Path, required=True)
    init.add_argument("--release-archive", type=Path, required=True)

    rec = sub.add_parser("record", help="Register one immutable JSON evidence artifact for the final matrix.")
    rec.add_argument("--root", type=Path, required=True)
    rec.add_argument("--gate", required=True)
    rec.add_argument("--evidence", type=Path, required=True)
    rec.add_argument("--disposition", choices=("auto", "pass", "fail", "superseded", "not_applicable"), default="auto")
    rec.add_argument("--cueq-runtime-digest")
    rec.add_argument("--note")

    red = sub.add_parser("reduce", help="Build the fail-closed FINAL-GPU1 qualification record.")
    red.add_argument("--root", type=Path, required=True)
    red.add_argument("--runtime", type=Path, required=True)
    red.add_argument("--perf-cert1", type=Path, required=True)
    red.add_argument("--size-fidelity2", type=Path, required=True)
    red.add_argument("--mv-learning-control", type=Path, required=True)
    red.add_argument("--output", type=Path)

    stat = sub.add_parser("status", help="Summarize the handoff matrix and final reduction state.")
    stat.add_argument("--root", type=Path, required=True)

    verify = sub.add_parser("verify", help="Re-hash the release, models, records, and evidence without reducing.")
    verify.add_argument("--root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    commands = {"preflight", "init", "record", "reduce", "status", "verify"}
    # Backward-compatible pre-v6 invocation: bare --mh1-model/--mpa0-model/--output
    # is treated as the preflight subcommand, while bare/help invocation exposes
    # the full handoff command surface.
    if not args_list:
        args_list = ["--help"]
    elif args_list[0] not in commands and args_list[0] not in {"-h", "--help"}:
        args_list = ["preflight", *args_list]
    args = _build_parser().parse_args(args_list)

    if args.command == "preflight":
        payload = build_preflight(args.mh1_model, args.mpa0_model, args.release_archive)
        _json_write(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if all(item["identity_passed"] for item in payload["foundation_models"]) else 2
    if args.command == "init":
        payload = initialize_handoff(args.root, args.mh1_model, args.mpa0_model, args.release_archive)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "record":
        payload = register_evidence(
            args.root, args.gate, args.evidence,
            disposition=args.disposition,
            cueq_runtime_digest=args.cueq_runtime_digest,
            note=args.note,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "reduce":
        payload = reduce_handoff(
            args.root, args.runtime, args.perf_cert1, args.size_fidelity2,
            args.mv_learning_control, args.output,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["passed"] else 3
    if args.command == "verify":
        payload = verify_handoff_integrity(args.root)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["passed"] else 4
    payload = handoff_status(args.root)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["handoff_integrity_passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
