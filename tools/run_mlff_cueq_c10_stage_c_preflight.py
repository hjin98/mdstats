#!/usr/bin/env python3
"""Freeze Candidate-10 Stage-C identity before any R1/R2/C trajectory runs."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

SCHEMA = "mdstats.mlff-cueq-c10-stage-c-preflight.v2"
EXPECTED_BRANCH = "design/mlff-train2-cueq-parity-requalification"
TRAIN2_KEY_COORDINATES = (
    "d",
    "theta_0",
    "q_0",
    "D",
    "E",
    "O",
    "H",
    "K",
    "rho",
    "m",
    "R",
)
CANDIDATE_COMMIT = "db2ed47e8c999cb61507803610c72c0fa7ffaaf7"
CANDIDATE_BLOB = "7843a41172d25c231d4c589aebc0214ddec42bd1"
ACCEPTED_PARENT_KERNEL = "a759e81aa1b4c70c8fb513c569ddce57e99cbdb2"
ACCEPTED_PARENT_SOURCE = "a4824d28775164aa942fd29fa97ee0957eb87e6f"
RISK_BINDING_BLOB = "8bdb8be9b0229dad9063e28e83c9ba6cfb092ce8"
LAW_BINDING_BLOB = "7b936d85d73e3bc7a18a8e20a57653e7e454d007"
MH1_SOURCE_SHA256 = "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"
MH1_SELECTED_HEAD_SHA256 = "61c83c377dae92bf37c5412a263687237fbc4b9790828868ec0887cc992be928"
MH1_SELECTED_HEAD_QUALIFICATION_DIGEST = "66867d6b08fc8af279c2f5e449168afa148d2f43aaa6fd745ae4524025c62244"
MPA0_SHA256 = "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
RISK_BINDING = {
    "eta_NI": 0.09,
    "q_cat": 0.09,
    "n_triplets": 300,
    "n_eval_triplets": 300,
    "simultaneous_confidence": 0.95,
    "per_statement_alpha": 0.0125,
}
SOURCE_RELATIONS = {
    "cv_checkpoint_target_force_rmse_ev_per_angstrom": 0.045,
    "cv_outer_target_force_rmse_ev_per_angstrom": 0.045,
    "production_checkpoint_target_force_rmse_ev_per_angstrom": 0.030,
    "replay_degradation_hard_budget_ev_per_angstrom": 0.030,
    "checkpoint_threshold_boundary": "inclusive_binary64_no_epsilon",
    "replay_reference_requirement": "authenticated_true_dft",
    "required_physical_gates": [],
}
EXPECTED_RUNTIME = {
    "torch": "2.13.0+cu126",
    "mace": "0.3.16",
    "e3nn": "0.4.4",
    "cueq-core": "0.10.0",
    "cueq-torch": "0.10.0",
    "cueq-ops": "0.10.0",
    "torch_cuda": "12.6",
}
PROJECTION_MODULES = (
    "mace.cli.convert_e3nn_cueq",
    "mace.cli.convert_cueq_e3nn",
    "mace.tools.cg_cueq_tools",
)
TRAIN2_EXECUTION_OWNER_MODULES = (
    "mdstats.training_data.acceleration",
    "mdstats.training_data.campaign_post_selection_runtime",
    "mdstats.training_data.post_selection_execution",
    "mdstats.training_data.train2_runtime",
)
ENV_KEYS = (
    "CUDA_VISIBLE_DEVICES",
    "CUBLAS_WORKSPACE_CONFIG",
    "NVIDIA_TF32_OVERRIDE",
    "PYTORCH_CUDA_ALLOC_CONF",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def manifest_content_digest(payload: Mapping[str, Any]) -> str:
    """Return the digest over the manifest body, excluding its digest field."""

    body = dict(payload)
    body.pop("content_digest", None)
    return hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def verify_manifest_content_digest(payload: Mapping[str, Any]) -> bool:
    """Check a preflight digest without interpreting any of its observations."""

    claimed = payload.get("content_digest")
    return isinstance(claimed, str) and claimed == manifest_content_digest(payload)


def train2_key_digest(coordinates: Mapping[str, Any]) -> str:
    """Content-address one exact D2.CUEQ10.DEF.001 coordinate mapping."""

    if set(coordinates) != set(TRAIN2_KEY_COORDINATES):
        raise RuntimeError(
            "Candidate-10 key must contain exactly the DEF.001 coordinates: "
            + ", ".join(TRAIN2_KEY_COORDINATES)
        )
    from mdstats.training_data.acceleration import (
        TRAINING_ACCELERATION_CUEQ_C10_KEY_COORDINATES,
        TrainingAccelerationCueqCandidate10Key,
    )

    if tuple(TRAIN2_KEY_COORDINATES) != tuple(
        TRAINING_ACCELERATION_CUEQ_C10_KEY_COORDINATES
    ):
        raise RuntimeError("Preflight and acceleration owner disagree on DEF.001 coordinates.")
    return TrainingAccelerationCueqCandidate10Key.from_coordinates(
        coordinates
    ).key_digest


def _require_exact_train2_keys(payload: Mapping[str, Any]) -> None:
    candidate10 = payload.get("candidate10")
    keys = candidate10.get("exact_train2_keys") if isinstance(candidate10, Mapping) else None
    if not isinstance(keys, list) or not keys:
        raise RuntimeError(
            "No exact Candidate-10 TRAIN2 key was frozen; refusing to publish preflight JSON."
        )
    observed_digests: set[str] = set()
    required_fields = set(TRAIN2_KEY_COORDINATES) | {"key_digest"}
    for index, key in enumerate(keys):
        if not isinstance(key, Mapping) or set(key) != required_fields:
            raise RuntimeError(
                f"Candidate-10 TRAIN2 key {index} does not contain the exact DEF.001 "
                "coordinates and key_digest."
            )
        from mdstats.training_data.acceleration import (
            TrainingAccelerationCueqCandidate10Key,
        )

        try:
            canonical_key = TrainingAccelerationCueqCandidate10Key.from_dict(key)
        except Exception as exc:
            raise RuntimeError(
                f"Candidate-10 TRAIN2 key {index} failed owning-layer validation: {exc}"
            ) from exc
        expected = canonical_key.key_digest
        actual = key.get("key_digest")
        if actual != expected:
            raise RuntimeError(
                f"Candidate-10 TRAIN2 key {index} digest mismatch: expected {expected}, "
                f"got {actual}."
            )
        if expected in observed_digests:
            raise RuntimeError(f"Duplicate exact Candidate-10 TRAIN2 key at index {index}.")
        observed_digests.add(expected)


def _require_candidate10_key_coverage(
    payload: Mapping[str, Any], expected_scopes: Sequence[Mapping[str, str]]
) -> None:
    """Reject a manifest that froze only a subset of its declared model/role keys."""

    candidate10 = payload.get("candidate10")
    keys = candidate10.get("exact_train2_keys") if isinstance(candidate10, Mapping) else None
    if not isinstance(keys, list):
        raise RuntimeError("Candidate-10 key coverage cannot be checked without exact keys.")
    expected = {
        (str(item["model_family"]), str(item["role"]), str(item["selected_binding_digest"]))
        for item in expected_scopes
    }
    actual: set[tuple[str, str, str]] = set()
    for index, key in enumerate(keys):
        try:
            coordinates = {name: key[name] for name in TRAIN2_KEY_COORDINATES}
            scope = (
                str(coordinates["theta_0"]["model_family"]),
                str(coordinates["E"]["role"]),
                str(coordinates["D"]["selected_binding"]["content_digest"]),
            )
        except (KeyError, TypeError) as exc:
            raise RuntimeError(
                f"Candidate-10 TRAIN2 key {index} lacks model, role, or selected-binding scope."
            ) from exc
        if scope in actual:
            raise RuntimeError(f"Duplicate Candidate-10 model/role scope: {scope}.")
        actual.add(scope)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise RuntimeError(
            "Candidate-10 exact-key coverage is incomplete; "
            f"missing={missing}, unexpected={extra}."
        )


def _run(argv: Sequence[str], *, cwd: Path | None = None) -> str:
    return subprocess.run(
        list(argv), cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _run_optional(argv: Sequence[str]) -> dict[str, Any]:
    try:
        return {"ok": True, "stdout": _run(argv)}
    except (OSError, subprocess.CalledProcessError) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "stderr": str(getattr(exc, "stderr", "") or "").strip(),
        }


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if hasattr(value, "content_digest"):
        return {"type": value.__class__.__name__, "content_digest": str(value.content_digest)}
    return repr(value)


def _git_hash(repo: Path, relative: str) -> str | None:
    path = repo / relative
    return None if not path.is_file() else _run(("git", "hash-object", str(path)), cwd=repo)


def _require_candidate_ancestor(repo: Path, candidate_path: str) -> None:
    try:
        frozen_blob = _run(
            ("git", "rev-parse", f"{CANDIDATE_COMMIT}:{candidate_path}"), cwd=repo
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Frozen Candidate-10 commit is unavailable: {CANDIDATE_COMMIT}"
        ) from exc
    if frozen_blob != CANDIDATE_BLOB:
        raise RuntimeError(
            "Frozen Candidate-10 commit does not contain the reviewed semantic blob: "
            f"expected {CANDIDATE_BLOB}, got {frozen_blob}."
        )
    result = subprocess.run(
        ("git", "merge-base", "--is-ancestor", CANDIDATE_COMMIT, "HEAD"),
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if result.returncode == 1:
            raise RuntimeError(
                f"Frozen Candidate-10 commit {CANDIDATE_COMMIT} is not an ancestor of HEAD."
            )
        raise RuntimeError(
            "Unable to verify Candidate-10 ancestry: "
            + (result.stderr or result.stdout).strip()
        )


def _require_exact_commit(repo: Path, commit: str, label: str) -> None:
    try:
        resolved = _run(("git", "rev-parse", "--verify", f"{commit}^{{commit}}"), cwd=repo)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{label} commit is unavailable: {commit}") from exc
    if resolved != commit:
        raise RuntimeError(
            f"{label} commit did not resolve to its frozen identity: {resolved}."
        )


def collect_git(repo_arg: str) -> dict[str, Any]:
    repo = Path(_run(("git", "rev-parse", "--show-toplevel"), cwd=Path(repo_arg))).resolve()
    status = _run(("git", "status", "--porcelain=v1", "--untracked-files=all"), cwd=repo)
    if status:
        raise RuntimeError("Stage-C preflight requires a clean repository.\n" + status)
    branch = _run(("git", "branch", "--show-current"), cwd=repo)
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(
            f"Stage-C preflight requires branch {EXPECTED_BRANCH!r}, got {branch!r}."
        )
    candidate_path = (
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_10.md"
    )
    candidate = _git_hash(repo, candidate_path)
    if candidate != CANDIDATE_BLOB:
        raise RuntimeError(
            f"Candidate-10 blob mismatch: expected {CANDIDATE_BLOB}, got {candidate}."
        )
    _require_candidate_ancestor(repo, candidate_path)
    _require_exact_commit(repo, ACCEPTED_PARENT_KERNEL, "Accepted parent kernel")
    _require_exact_commit(repo, ACCEPTED_PARENT_SOURCE, "Accepted parent source")
    risk_path = (
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_RISK_BINDING.md"
    )
    law_path = (
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_LAW_BINDING.md"
    )
    risk_blob = _git_hash(repo, risk_path)
    law_blob = _git_hash(repo, law_path)
    if risk_blob != RISK_BINDING_BLOB:
        raise RuntimeError(
            f"Candidate-10 risk-instance binding mismatch: expected {RISK_BINDING_BLOB}, got {risk_blob}."
        )
    if law_blob != LAW_BINDING_BLOB:
        raise RuntimeError(
            f"Candidate-10 law/role binding mismatch: expected {LAW_BINDING_BLOB}, got {law_blob}."
        )
    return {
        "repo_root": str(repo),
        "head": _run(("git", "rev-parse", "HEAD"), cwd=repo),
        "branch": branch,
        "clean_before_manifest": True,
        "candidate_blob": candidate,
        "accepted_parent_kernel": ACCEPTED_PARENT_KERNEL,
        "accepted_parent_source": ACCEPTED_PARENT_SOURCE,
        "candidate_commit": CANDIDATE_COMMIT,
        "risk_binding_blob": risk_blob,
        "law_binding_blob": law_blob,
    }


def _selected_gpu_apps(gpu_query: str, apps_query: str) -> list[dict[str, str]]:
    gpu_fields = [v.strip() for v in gpu_query.split(",")]
    uuid = gpu_fields[1] if len(gpu_fields) > 1 else None
    found: list[dict[str, str]] = []
    for line in apps_query.splitlines():
        parts = [v.strip() for v in line.split(",")]
        if len(parts) < 4 or (uuid is not None and parts[3] != uuid):
            continue
        found.append(
            {
                "pid": parts[0],
                "process_name": parts[1],
                "used_gpu_memory_mib": parts[2],
                "gpu_uuid": parts[3],
            }
        )
    return found


def _require_no_selected_gpu_apps(gpu_query: str, apps_query: str) -> list[dict[str, str]]:
    active = _selected_gpu_apps(gpu_query, apps_query)
    if active:
        raise RuntimeError(
            "Selected GPU already has compute processes; Candidate-10 first law requires "
            f"one governed child at a time: {active}"
        )
    return active


def _require_runtime_family(
    versions: Mapping[str, Any], torch_cuda_version: Any
) -> None:
    mismatches = {
        name: {"expected": expected, "observed": versions.get(name)}
        for name, expected in EXPECTED_RUNTIME.items()
        if name != "torch_cuda" and versions.get(name) != expected
    }
    if str(torch_cuda_version) != EXPECTED_RUNTIME["torch_cuda"]:
        mismatches["torch_cuda"] = {
            "expected": EXPECTED_RUNTIME["torch_cuda"],
            "observed": torch_cuda_version,
        }
    if mismatches:
        raise RuntimeError("Runtime family mismatch: " + json.dumps(mismatches, sort_keys=True))


def _require_rtx3090(name: str, major: int, minor: int) -> None:
    if "RTX 3090" not in name or (major, minor) != (8, 6):
        raise RuntimeError(
            f"Expected RTX 3090 / compute capability 8.6, got {name} {major}.{minor}."
        )


def collect_runtime(gpu_index: int) -> dict[str, Any]:
    gpu = _run_optional(
        (
            "nvidia-smi",
            f"--id={gpu_index}",
            "--query-gpu=name,uuid,driver_version,memory.total,memory.free",
            "--format=csv,noheader,nounits",
        )
    )
    apps = _run_optional(
        (
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_gpu_memory,gpu_uuid",
            "--format=csv,noheader,nounits",
        )
    )
    if not gpu["ok"] or not apps["ok"]:
        raise RuntimeError(f"nvidia-smi precheck failed: gpu={gpu}, apps={apps}")
    active = _require_no_selected_gpu_apps(str(gpu["stdout"]), str(apps["stdout"]))

    import mdstats
    import torch

    dep1 = mdstats.capture_cueq_dep1_runtime()
    if not dep1.passed:
        raise RuntimeError("CUEQ-DEP1 runtime does not pass: " + ", ".join(dep1.blocking_reasons))
    dep = dep1.to_dict()
    versions = {str(v["logical_name"]): v.get("version") for v in dep["distributions"]}
    _require_runtime_family(versions, dep1.device.torch_cuda_version)
    if not torch.cuda.is_available() or gpu_index >= torch.cuda.device_count():
        raise RuntimeError(f"CUDA device {gpu_index} is unavailable to Torch.")
    props = torch.cuda.get_device_properties(gpu_index)
    _require_rtx3090(props.name, props.major, props.minor)

    projection_sources: dict[str, Any] = {}
    for name in PROJECTION_MODULES:
        module = importlib.import_module(name)
        source = inspect.getsourcefile(module)
        if source is None:
            raise RuntimeError(f"Cannot locate installed source for {name}.")
        path = Path(source).resolve()
        projection_sources[name] = {"path": str(path), "sha256": sha256_file(path)}

    train2_owner_sources: dict[str, Any] = {}
    for name in TRAIN2_EXECUTION_OWNER_MODULES:
        module = importlib.import_module(name)
        source = inspect.getsourcefile(module)
        if source is None:
            raise RuntimeError(f"Cannot locate installed source for {name}.")
        path = Path(source).resolve()
        train2_owner_sources[name] = {"path": str(path), "sha256": sha256_file(path)}

    torch_arithmetic_flags = {
        "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
        "deterministic_debug_mode": int(torch.get_deterministic_debug_mode()),
        "float32_matmul_precision": str(torch.get_float32_matmul_precision()),
        "cuda_matmul_allow_tf32": bool(torch.backends.cuda.matmul.allow_tf32),
        "cudnn_available": bool(torch.backends.cudnn.is_available()),
        "cudnn_enabled": bool(torch.backends.cudnn.enabled),
        "cudnn_deterministic": bool(torch.backends.cudnn.deterministic),
        "cudnn_benchmark": bool(torch.backends.cudnn.benchmark),
        "cudnn_allow_tf32": bool(torch.backends.cudnn.allow_tf32),
    }

    return {
        "cueq_dep1_runtime": dep,
        "gpu_pre_cuda_initialization": gpu,
        "compute_apps_pre_cuda_initialization": apps,
        "selected_gpu_compute_apps_pre_cuda_initialization": active,
        "torch_selected_device": {
            "index": gpu_index,
            "name": props.name,
            "compute_capability": [props.major, props.minor],
            "total_memory_bytes": props.total_memory,
        },
        "environment": {key: os.environ.get(key) for key in ENV_KEYS},
        "torch_arithmetic_flags": torch_arithmetic_flags,
        "projection_source_modules": projection_sources,
        "train2_execution_owner_modules": train2_owner_sources,
        "python_executable": sys.executable,
    }


def _configured_path(cfg: Mapping[str, Any], config_dir: Path, key: str) -> Path | None:
    raw = cfg.get("paths", {}).get(key)
    if raw in (None, ""):
        return None
    path = Path(str(raw)).expanduser()
    return (path if path.is_absolute() else config_dir / path).resolve()


def _file_record(path: Path | None, *, required: bool = False) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        if required:
            raise RuntimeError(f"Required input file is missing: {path}")
        return None
    return {"path": str(path), "size": path.stat().st_size, "sha256": sha256_file(path)}


def _locked_file_record(path: Path | None, expected_sha256: str, label: str) -> dict[str, Any]:
    record = _file_record(path, required=True)
    assert record is not None
    if record["sha256"] != expected_sha256:
        raise RuntimeError(f"{label} SHA-256 mismatch: {record['sha256']}")
    return record


def _replay_transport_identity(context: Any) -> dict[str, Any]:
    """Read and byte-authenticate the exact replay source and transport artifacts."""

    from mdstats.training_data.campaign_post_selection_runtime import (
        _training_replay_resolution,
    )
    from mdstats.training_data.post_selection_identity import (
        compute_replay_lineage_digest,
    )

    resolution = _training_replay_resolution(context)
    if resolution is None:
        if context.method_policies.replay_enabled:
            raise RuntimeError("Replay is enabled but has no authenticated P5 replay resolution.")
        return {"enabled": False, "lineage_digest": None}

    def transport(label: str, path_value: Any, artifact: Any) -> dict[str, Any]:
        path = Path(str(path_value)).expanduser().resolve()
        record = _file_record(path, required=True)
        expected_sha = str(getattr(artifact, "sha256", ""))
        if not expected_sha or record["sha256"] != expected_sha:
            raise RuntimeError(
                f"Replay {label} transport bytes do not match their authenticated artifact SHA-256."
            )
        return {
            "path": record["path"],
            "size": record["size"],
            "sha256": record["sha256"],
            "artifact_content_digest": str(
                getattr(artifact, "content_digest", getattr(artifact, "logical_digest", ""))
            ),
            "role": str(getattr(artifact, "role", label)),
        }

    lineage_digest = compute_replay_lineage_digest(resolution)
    source_path_value = getattr(resolution, "source_path", None)
    source_sha256 = getattr(resolution, "source_sha256", None)
    if source_sha256 is None:
        source_sha256 = getattr(resolution, "true_label_source_sha256", None)
    source: dict[str, Any] = {
        "content_digest": getattr(resolution, "source_content_digest", None),
        "sha256": source_sha256,
        "split_manifest_digest": getattr(resolution, "split_manifest_digest", None),
    }
    if source_path_value is not None:
        source_record = _file_record(Path(str(source_path_value)).expanduser().resolve(), required=True)
        if source_sha256 and source_record["sha256"] != str(source_sha256):
            raise RuntimeError("Replay source bytes do not match their authenticated SHA-256.")
        source = {**source, "path": source_record["path"], "size": source_record["size"], "sha256": source_record["sha256"]}
    elif source_sha256 is not None:
        source["sha256"] = str(source_sha256)

    return {
        "enabled": True,
        "interface": str(resolution.interface),
        "lineage_digest": lineage_digest,
        "source": source,
        "training_label_mode": str(
            getattr(resolution.training_label_mode, "value", resolution.training_label_mode)
        ),
        "true_monitor_label_mode": str(
            getattr(resolution.true_label_mode, "value", resolution.true_label_mode)
        ),
        "training_transport": transport(
            "training", resolution.train_path, resolution.train_artifact
        ),
        "true_monitor_transport": transport(
            "true-monitor", resolution.monitor_path, resolution.monitor_artifact
        ),
    }


def _target_transport_identity(
    context: Any,
    *,
    trajectory: Mapping[str, Any],
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
) -> dict[str, Any]:
    """Authenticate an existing P5 target/monitor transport without creating it."""

    from mdstats.training_data.campaign_post_selection_runtime import (
        _validate_post_selection_materialization_artifacts,
    )
    from mdstats.training_data.post_selection_execution import PostSelectionMaterialization
    from mdstats.training_data.post_selection_store import post_selection_root

    trajectory_digest = str(trajectory["content_digest"])
    material_directory = (
        post_selection_root(context.paths, context.selected.binding.campaign_generation)
        / "runs"
        / trajectory_digest
        / "materialization"
    )
    record_path = material_directory / "materialization.json"
    if not record_path.is_file():
        raise RuntimeError(
            "Candidate-10 preflight cannot bind the exact target ExtXYZ transport: "
            f"authenticated P5 materialization is absent for trajectory {trajectory_digest}."
        )
    try:
        record = PostSelectionMaterialization.from_dict(
            json.loads(record_path.read_text(encoding="utf-8"))
        )
        if record.training_trajectory_identity != trajectory_digest:
            raise RuntimeError("P5 target transport belongs to another training trajectory.")
        _validate_post_selection_materialization_artifacts(
            context.selected,
            material_directory=material_directory,
            record=record,
            training_frame_uids=training_frame_uids,
            monitor_frame_uids=monitor_frame_uids,
            preparation=SimpleNamespace(content_digest=record.preparation_digest),
            extxyz_policy=context.method_policies.extxyz,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Candidate-10 preflight could not authenticate P5 target transports for {trajectory_digest}: {exc}"
        ) from exc

    def artifact_identity(artifact: Any) -> dict[str, Any]:
        return {
            "role": artifact.role,
            "sha256": artifact.sha256,
            "content_digest": artifact.content_digest,
            "membership_digest": artifact.membership_digest,
            "configuration_count": artifact.configuration_count,
            "frame_uid_sequence_digest": hashlib.sha256(
                canonical_json_bytes(list(artifact.frame_uids))
            ).hexdigest(),
        }

    return {
        "training_trajectory_identity": trajectory_digest,
        "preparation_digest": record.preparation_digest,
        "target_train_artifact": artifact_identity(record.target_train_artifact),
        "checkpoint_monitor_artifact": artifact_identity(
            record.checkpoint_monitor_artifact
        ),
    }


def _resolve_candidate10_mpa0_method(
    cfg: Mapping[str, Any], *, config_dir: Path, mpa0_model: Path
) -> tuple[Any, Any, dict[str, Any]]:
    """Resolve MPA-0 through the current P5 policy owner using the bound model/head."""

    from mdstats.training_data.post_selection_identity import (
        resolve_post_selection_method_identity,
        resolve_post_selection_method_policies,
    )

    candidate_cfg = copy.deepcopy(dict(cfg))
    candidate_cfg["foundation"] = {
        **dict(candidate_cfg.get("foundation", {})),
        "family": "mace_mpa_0",
        "head": "default",
    }
    candidate_cfg.setdefault("paths", {})["foundation_model"] = str(mpa0_model)
    training = candidate_cfg.setdefault("training", {})
    if not isinstance(training, dict):
        raise RuntimeError("[training] must be a table to resolve the MPA-0 method identity.")
    training["foundation_head"] = "default"

    policies = resolve_post_selection_method_policies(
        candidate_cfg, config_dir=config_dir
    )
    method = resolve_post_selection_method_identity(candidate_cfg, policies=policies)
    foundation = policies.foundation_potential_identity
    if foundation is None:
        raise RuntimeError("MPA-0 method identity has no inspected foundation checkpoint.")
    identity = foundation.to_dict()
    if identity.get("model_family") != "mace_mpa_0" or identity.get("foundation_head") != "default":
        raise RuntimeError(
            "MPA-0 key did not resolve the ratified mace_mpa_0/default foundation."
        )
    return candidate_cfg, (policies, method), identity


def _candidate10_run_trajectories(
    context: Any,
    *,
    method: Any,
    policies: Any,
    cv_plan: Any,
    final_plan: Any,
    monitor: Any,
    monitor_separation: Any,
    replay_lineage_digest: str | None,
) -> dict[str, list[dict[str, Any]]]:
    """Project each exact role/seed/fold through the existing P5 trajectory owner."""

    from mdstats.training_data.post_selection_execution import (
        transfer_consumer_composition_digest,
    )
    from mdstats.training_data.post_selection_run_identity import (
        PostSelectionRunRole,
        TrainingTrajectoryIdentity,
    )

    common = {
        "selected_binding_digest": context.selected.binding.content_digest,
        "method_identity_digest": method.content_digest,
        "common_monitor_record_digest": monitor.content_digest,
        "replay_lineage_digest": replay_lineage_digest,
    }
    cv_runs: list[dict[str, Any]] = []
    cv_horizon = int(context.cv_policy.cv_max_num_epochs)
    for seed in cv_plan.required_cv_seeds:
        for fold in cv_plan.folds:
            composition_digest = transfer_consumer_composition_digest(
                context.selected,
                training_mode=method.training_mode,
                consumer_frame_uids=(
                    tuple(monitor.selected_identities)
                    + tuple(fold.outer_evaluation_frame_uids)
                ),
            )
            trajectory = TrainingTrajectoryIdentity(
                run_role=PostSelectionRunRole.POST_SELECTION_CV.value,
                **common,
                training_membership_digest=hashlib.sha256(
                    canonical_json_bytes({"frame_uids": list(fold.training_frame_uids)})
                ).hexdigest(),
                optimizer_seed=int(seed),
                planned_epochs=cv_horizon,
                transfer_consumer_composition_digest=composition_digest,
            )
            if method.content_digest == context.method.content_digest:
                from mdstats.training_data.post_selection_cv_plan import (
                    build_cv_fold_run_plan,
                )

                owned = build_cv_fold_run_plan(
                    cv_plan,
                    fold_index=fold.fold_index,
                    optimizer_seed=int(seed),
                    planned_epochs=cv_horizon,
                )
                if owned.training_trajectory.content_digest != trajectory.content_digest:
                    raise RuntimeError(
                        "CV Candidate-10 key trajectory differs from the existing P5 run-identity owner."
                    )
            cv_runs.append(
                {
                    "optimizer_seed": int(seed),
                    "fold_index": int(fold.fold_index),
                    "training_frame_uids": list(fold.training_frame_uids),
                    "training_trajectory": trajectory.to_dict(),
                }
            )

    final_runs: list[dict[str, Any]] = []
    final_horizon = int(final_plan.planned_epochs)
    if final_horizon != int(context.production_policy.production_max_num_epochs):
        raise RuntimeError(
            "Current final-production plan horizon differs from its resolved policy."
        )
    for seed in final_plan.required_final_seeds:
        composition_digest = transfer_consumer_composition_digest(
            context.selected,
            training_mode=method.training_mode,
            consumer_frame_uids=tuple(monitor.selected_identities),
        )
        trajectory = TrainingTrajectoryIdentity(
            run_role=PostSelectionRunRole.FINAL_PRODUCTION.value,
            **common,
            training_membership_digest=final_plan.target_membership_digest,
            optimizer_seed=int(seed),
            planned_epochs=final_horizon,
            transfer_consumer_composition_digest=composition_digest,
        )
        if method.content_digest == context.method.content_digest:
            from mdstats.training_data.post_selection_production import (
                build_final_production_run_plan,
            )

            owned = build_final_production_run_plan(
                final_plan, optimizer_seed=int(seed)
            )
            if owned.training_trajectory.content_digest != trajectory.content_digest:
                raise RuntimeError(
                    "Production Candidate-10 key trajectory differs from the existing P5 run-identity owner."
                )
        final_runs.append(
            {
                "optimizer_seed": int(seed),
                "training_frame_uids": list(context.selected.selected_membership),
                "training_trajectory": trajectory.to_dict(),
            }
        )
    return {"cv": cv_runs, "final_production": final_runs}


def _candidate10_key_for_role(
    *,
    context: Any,
    method: Any,
    policies: Any,
    model_identity: Mapping[str, Any],
    role: str,
    cv_plan: Any,
    final_plan: Any,
    monitor: Any,
    monitor_separation: Any,
    trajectories: Mapping[str, Sequence[Mapping[str, Any]]],
    replay_identity: Mapping[str, Any],
    target_transport_artifacts: Sequence[Mapping[str, Any]],
    runtime: Mapping[str, Any],
    static_bindings: Mapping[str, Any],
) -> dict[str, Any]:
    from mdstats.training_data.acceleration import (
        MaceAccelerationKernelMode,
        TrainingAccelerationCueqCandidate10Key,
    )
    from mdstats.training_data.training_settings import shared_optimizer_settings_payload

    if role == "cv":
        source_plan = cv_plan
        role_runs = list(trajectories["cv"])
        role_membership = {
            "folds": [
                {
                    "fold_index": fold.fold_index,
                    "training_frame_uids": list(fold.training_frame_uids),
                    "outer_evaluation_frame_uids": list(
                        fold.outer_evaluation_frame_uids
                    ),
                    "purged_frame_uids": list(fold.purged_frame_uids),
                }
                for fold in cv_plan.folds
            ],
            "relation_authority_digest": cv_plan.relation_authority_digest,
            "projection_digest": cv_plan.projection_digest,
            "required_seeds": list(cv_plan.required_cv_seeds),
            "horizon_epochs": int(context.cv_policy.cv_max_num_epochs),
        }
    elif role == "final_production":
        source_plan = final_plan
        role_runs = list(trajectories["final_production"])
        role_membership = {
            "target_membership_digest": final_plan.target_membership_digest,
            "n_selected": final_plan.n_selected,
            "required_seeds": list(final_plan.required_final_seeds),
            "horizon_epochs": int(final_plan.planned_epochs),
        }
    else:
        raise RuntimeError(f"Unsupported Candidate-10 TRAIN2 role: {role!r}.")

    if not role_runs:
        raise RuntimeError(f"Candidate-10 {role} key has no exact training trajectories.")
    shared_optimizer = shared_optimizer_settings_payload(context.cfg)
    theta0 = dict(model_identity)
    selected_binding = context.selected.binding.to_dict()
    consumer_identity = {
        "role": role,
        "common_monitor": monitor.to_dict(),
        "monitor_separation": monitor_separation.to_dict(),
        "role_membership": role_membership,
        "replay_lineage_digest": source_plan.replay_lineage_digest,
        "accepted_source_relations": SOURCE_RELATIONS,
    }
    data_identity = {
        "selected_binding": selected_binding,
        "selected_membership": list(context.selected.selected_membership),
        "replay_transport": dict(replay_identity),
        "target_transport_artifacts": [dict(item) for item in target_transport_artifacts],
        "training_trajectories": [
            dict(item["training_trajectory"]) for item in role_runs
        ],
        "training_exposure": {
            "training_mode": method.training_mode,
            "exposure_policy": method.exposure_policy,
            "replay_exposure_policy_digest": method.replay_exposure_policy_digest,
            "extxyz_policy_digest": method.extxyz_policy_digest,
            "shared_optimizer_settings_digest": method.shared_optimizer_settings_digest,
        },
    }
    objective_identity = {
        "model_family": theta0["model_family"],
        "foundation_head": theta0["foundation_head"],
        "training_mode": method.training_mode,
        "objective_policy_digest": method.objective_policy_digest,
        "preparation_policy_digest": method.preparation_policy_digest,
        "mace_architecture_digest": method.mace_architecture_digest,
        "target_head_name": policies.target_head_name,
        "replay_head_name": policies.replay_head_name,
        "extxyz_policy_digest": method.extxyz_policy_digest,
    }
    horizon_identity = {
        **role_membership,
        "checkpoint_interval_epochs": method.checkpoint_interval_epochs,
        "learning_rate_schedule_policy_digest": method.learning_rate_schedule_policy_digest,
        "shared_optimizer_settings": shared_optimizer,
        "trajectory_digests": [
            item["training_trajectory"]["content_digest"] for item in role_runs
        ],
    }
    kernel_pair = [
        {
            "kernel": MaceAccelerationKernelMode.E3NN.value,
            "calculator_kwargs": MaceAccelerationKernelMode.E3NN.calculator_kwargs(),
        },
        {
            "kernel": MaceAccelerationKernelMode.CUEQ_PURE.value,
            "calculator_kwargs": MaceAccelerationKernelMode.CUEQ_PURE.calculator_kwargs(),
        },
    ]
    method_identity = {
        "candidate_commit": static_bindings["candidate_commit"],
        "candidate_blob": static_bindings["candidate_blob"],
        "accepted_parent_kernel": static_bindings["accepted_parent_kernel"],
        "accepted_parent_source": static_bindings["accepted_parent_source"],
        "risk_binding_blob": static_bindings["risk_binding_blob"],
        "law_binding_blob": static_bindings["law_binding_blob"],
    }
    owner_sources = runtime.get("train2_execution_owner_modules")
    if not isinstance(owner_sources, Mapping) or set(owner_sources) != set(
        TRAIN2_EXECUTION_OWNER_MODULES
    ):
        raise RuntimeError(
            "Candidate-10 key lacks exact current TRAIN2 execution-owner source identities."
        )
    risk_identity = {
        "eta_NI": RISK_BINDING["eta_NI"],
        "q_cat": RISK_BINDING["q_cat"],
        "n": RISK_BINDING["n_triplets"],
        "Q": {
            "ratified_law_role_binding_blob": static_bindings["law_binding_blob"],
            "execution_owner_sources": dict(owner_sources),
        },
    }
    coordinates = {
        "d": str(method.default_dtype),
        "theta_0": theta0,
        "q_0": {
            "initial_model_identity_digest": hashlib.sha256(
                canonical_json_bytes(theta0)
            ).hexdigest(),
            "fresh_child_start_contract": {
                "reference_child": "fresh OS process/private child state/e3nn",
                "candidate_child": "fresh OS process/private child state/cueq_pure",
                "optimizer_and_rng": "reinitialized from each exact training trajectory",
            },
            "training_trajectories": [
                dict(item["training_trajectory"]) for item in role_runs
            ],
        },
        "D": data_identity,
        "E": consumer_identity,
        "O": objective_identity,
        "H": horizon_identity,
        "K": kernel_pair,
        "rho": dict(runtime),
        "m": method_identity,
        "R": risk_identity,
    }
    if coordinates["d"] != "float32":
        raise RuntimeError(
            f"Candidate-10 key requires float32; current method resolves {coordinates['d']!r}."
        )
    return TrainingAccelerationCueqCandidate10Key.from_coordinates(
        _jsonable(coordinates)
    ).to_dict()


def collect_campaign(
    config_arg: str,
    mpa0_arg: str,
    *,
    runtime: Mapping[str, Any] | None = None,
    static_bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    import mdstats
    from dataclasses import replace
    from mdstats.training_data._campaign_cli_core import CampaignStore, _load_config
    from mdstats.training_data.campaign_lifecycle import campaign_owner_snapshot
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        resolve_current_cv_plan,
        resolve_current_final_production_plan,
    )
    from mdstats.training_data.post_selection_identity import (
        resolve_cv_validation_policy_identity,
        resolve_final_production_policy_identity,
    )

    cfg, paths = _load_config(Path(config_arg).expanduser().resolve(), ensure=False)
    runtime = {} if runtime is None else runtime
    static_bindings = {} if static_bindings is None else static_bindings
    store = CampaignStore(paths.state_db, create=False)
    revision, bindings, pointers = campaign_owner_snapshot(store)
    contexts = build_post_selection_contexts(
        cfg, paths, store, trainer=object(), inference_evaluator=None, admit=False
    )
    if not contexts:
        raise RuntimeError("No frozen selected post-selection context exists.")
    foundation_cfg = cfg.get("foundation", {})
    if not isinstance(foundation_cfg, Mapping) or (
        str(foundation_cfg.get("family", "")) != "mace_mh_1"
        or str(foundation_cfg.get("head", "")) != "omat_pbe"
    ):
        raise RuntimeError(
            "Candidate-10 preflight --config must resolve the ratified MH-1/omat_pbe campaign."
        )

    mh1 = _locked_file_record(
        _configured_path(cfg, paths.config_dir, "foundation_model"),
        MH1_SOURCE_SHA256,
        "MH-1 source",
    )
    q = store.get_record_optional(
        "selected_head_qualification", mdstats.MaceSelectedHeadQualificationRecord
    )
    if q is None or q.content_digest != MH1_SELECTED_HEAD_QUALIFICATION_DIGEST:
        raise RuntimeError(
            "Selected-head qualification is missing or not the frozen Stage-A identity."
        )
    selected = _locked_file_record(
        Path(q.extraction.derived_checkpoint_reference).expanduser().resolve(),
        MH1_SELECTED_HEAD_SHA256,
        "MH-1 selected-head",
    )
    mpa0 = _locked_file_record(
        Path(mpa0_arg).expanduser().resolve(), MPA0_SHA256, "MPA-0 checkpoint"
    )
    mpa0_path = Path(mpa0_arg).expanduser().resolve()
    mpa0_cfg, (mpa0_policies, mpa0_method), mpa0_foundation = (
        _resolve_candidate10_mpa0_method(
            cfg, config_dir=paths.config_dir, mpa0_model=mpa0_path
        )
    )
    if mpa0_policies.default_dtype != "float32" or mpa0_method.default_dtype != "float32":
        raise RuntimeError("MPA-0 Candidate-10 method did not resolve to learned-model float32.")
    if str(mpa0_foundation.get("sha256")) != MPA0_SHA256:
        raise RuntimeError("MPA-0 foundation resolver does not match the locked checkpoint bytes.")

    selected_contexts: list[dict[str, Any]] = []
    exact_keys: list[dict[str, Any]] = []
    expected_key_scopes: list[dict[str, str]] = []
    for context in contexts:
        monitor, separation = context.common_target_monitor()
        try:
            cv_plan = resolve_current_cv_plan(context)
        except Exception as exc:
            raise RuntimeError(
                f"Current CV plan is unavailable for selected binding "
                f"{context.selected.binding.content_digest}: {type(exc).__name__}: {exc}"
            ) from exc
        if cv_plan is None:
            raise RuntimeError(
                "Candidate-10 CV key requires a current authenticated CV plan for each selected binding."
            )
        try:
            final_plan = resolve_current_final_production_plan(context)
        except Exception as exc:
            raise RuntimeError(
                f"Current final-production plan is unavailable for selected binding "
                f"{context.selected.binding.content_digest}: {type(exc).__name__}: {exc}"
            ) from exc
        if final_plan is None:
            raise RuntimeError(
                "Candidate-10 production key requires a current authenticated final-production plan for each selected binding."
            )
        replay_identity = _replay_transport_identity(context)
        replay_lineage_digest = replay_identity.get("lineage_digest")
        if (
            cv_plan.replay_lineage_digest != replay_lineage_digest
            or final_plan.replay_lineage_digest != replay_lineage_digest
        ):
            raise RuntimeError(
                "Current CV/final plans do not bind the exact authenticated replay lineage."
            )

        cv_tau = context.cv_policy.checkpoint_maximum_target_force_rmse_ev_per_angstrom
        cv_theta = context.cv_policy.acceptance_maximum
        prod_tau = context.production_policy.checkpoint_maximum_target_force_rmse_ev_per_angstrom
        mh1_foundation = context.method_policies.foundation_potential_identity
        if mh1_foundation is None:
            raise RuntimeError("MH-1 method identity has no inspected foundation checkpoint.")
        if (
            mh1_foundation.model_family != "mace_mh_1"
            or mh1_foundation.foundation_head != "omat_pbe"
        ):
            raise RuntimeError("Current P5 method is not the ratified MH-1/omat_pbe realization.")
        mh1_identity = {
            "model_family": "mace_mh_1",
            "foundation_head": "omat_pbe",
            "source_foundation_checkpoint": mh1,
            "training_initial_checkpoint": selected,
            "selected_head_qualification": q.to_dict(),
            "foundation_identity": mh1_foundation.to_dict(),
        }
        mpa0_identity = {
            "model_family": "mace_mpa_0",
            "foundation_head": "default",
            "source_foundation_checkpoint": mpa0,
            "training_initial_checkpoint": mpa0,
            "selected_head_qualification": {
                "applicability": "not_required_single_head_default",
                "foundation_identity": mpa0_foundation,
            },
            "foundation_identity": mpa0_foundation,
        }
        mpa0_cv_policy = resolve_cv_validation_policy_identity(
            mpa0_cfg,
            max_num_epochs=context.cv_policy.cv_max_num_epochs,
            training_mode=mpa0_policies.training_mode,
        )
        mpa0_final_policy = resolve_final_production_policy_identity(
            mpa0_cfg,
            max_num_epochs=context.production_policy.production_max_num_epochs,
            training_mode=mpa0_policies.training_mode,
        )
        if (
            mpa0_cv_policy.to_dict() != context.cv_policy.to_dict()
            or mpa0_final_policy.to_dict() != context.production_policy.to_dict()
        ):
            raise RuntimeError(
                "The ratified MPA-0 model substitution changes a source-owned CV/production role policy."
            )
        if (
            mpa0_method.extxyz_policy_digest != context.method.extxyz_policy_digest
            or mpa0_method.replay_exposure_policy_digest
            != context.method.replay_exposure_policy_digest
        ):
            raise RuntimeError(
                "The MPA-0 model substitution changes the source-owned target/replay transport policy."
            )
        mpa0_context = replace(
            context,
            cfg=mpa0_cfg,
            method=mpa0_method,
            method_policies=mpa0_policies,
            cv_policy=mpa0_cv_policy,
            production_policy=mpa0_final_policy,
        )
        mh1_trajectories = _candidate10_run_trajectories(
            context,
            method=context.method,
            policies=context.method_policies,
            cv_plan=cv_plan,
            final_plan=final_plan,
            monitor=monitor,
            monitor_separation=separation,
            replay_lineage_digest=replay_lineage_digest,
        )
        target_transport_artifacts: dict[str, list[dict[str, Any]]] = {
            "cv": [],
            "final_production": [],
        }
        for role, items in mh1_trajectories.items():
            for item in items:
                target_transport_artifacts[role].append(
                    {
                        "optimizer_seed": item["optimizer_seed"],
                        "fold_index": item.get("fold_index"),
                        **_target_transport_identity(
                            context,
                            trajectory=item["training_trajectory"],
                            training_frame_uids=item["training_frame_uids"],
                            monitor_frame_uids=monitor.selected_identities,
                        ),
                    }
                )
        selected_contexts.append(
            {
                "n_selected": context.selected.n_selected,
                "selected_binding": context.selected.binding.to_dict(),
                "selected_membership": [str(v) for v in context.selected.selected_membership],
                "method_training_identity": context.method.to_dict(),
                "common_monitor": monitor.to_dict(),
                "common_monitor_separation": separation.to_dict(),
                "replay_transport_identity": replay_identity,
                "target_transport_artifacts": target_transport_artifacts,
                "current_cv_plan": cv_plan.to_dict(),
                "current_final_plan": final_plan.to_dict(),
                "current_d4_assessment_policy_observation": {
                    "cv_policy": context.cv_policy.to_dict(),
                    "production_policy": context.production_policy.to_dict(),
                    "matches_candidate10_parent_defaults": (
                        cv_tau == 0.045 and cv_theta == 0.045 and prod_tau == 0.030
                    ),
                    "authority_note": (
                        "Observed D4 policy is not Candidate-10 authority. The branch's "
                        "75/75/50 renewal is unratified; Stage C uses accepted-parent "
                        "45/45/30 and Stage D reconciles D3/D4 afterward."
                    ),
                },
            }
        )
        for family_context, model_identity, family_trajectories in (
            (context, mh1_identity, mh1_trajectories),
            (
                mpa0_context,
                mpa0_identity,
                _candidate10_run_trajectories(
                    mpa0_context,
                    method=mpa0_method,
                    policies=mpa0_policies,
                    cv_plan=cv_plan,
                    final_plan=final_plan,
                    monitor=monitor,
                    monitor_separation=separation,
                    replay_lineage_digest=replay_lineage_digest,
                ),
            ),
        ):
            method = family_context.method
            policies = family_context.method_policies
            for role in ("cv", "final_production"):
                exact_key = _candidate10_key_for_role(
                    context=family_context,
                    method=method,
                    policies=policies,
                    model_identity=model_identity,
                    role=role,
                    cv_plan=cv_plan,
                    final_plan=final_plan,
                    monitor=monitor,
                    monitor_separation=separation,
                    trajectories=family_trajectories,
                    replay_identity=replay_identity,
                    target_transport_artifacts=target_transport_artifacts[role],
                    runtime=runtime,
                    static_bindings=static_bindings,
                )
                exact_keys.append(exact_key)
                expected_key_scopes.append(
                    {
                        "model_family": str(model_identity["model_family"]),
                        "role": role,
                        "selected_binding_digest": context.selected.binding.content_digest,
                    }
                )

    return {
        "config": {"path": str(paths.config), "sha256": sha256_file(paths.config)},
        "workspace": str(paths.workspace),
        "owner_snapshot": {
            "revision": _jsonable(revision),
            "bindings": _jsonable(bindings),
            "pointers": _jsonable(pointers),
        },
        "selected_contexts": selected_contexts,
        "exact_train2_keys": exact_keys,
        "expected_key_scopes": expected_key_scopes,
        "models": {
            "mh1_source": mh1,
            "mh1_selected_head": selected,
            "mh1_selected_head_qualification": q.to_dict(),
            "mpa0": mpa0,
        },
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    git = collect_git(args.repo)
    runtime = collect_runtime(args.gpu_index)
    campaign = collect_campaign(
        args.config,
        args.mpa0_model,
        runtime=runtime,
        static_bindings=git,
    )
    exact_keys = campaign["exact_train2_keys"]
    expected_key_scopes = campaign["expected_key_scopes"]
    campaign = {
        key: value
        for key, value in campaign.items()
        if key not in {"exact_train2_keys", "expected_key_scopes"}
    }
    payload = {
        "schema": SCHEMA,
        "candidate10": {
            "candidate_commit": CANDIDATE_COMMIT,
            "candidate_blob": CANDIDATE_BLOB,
            "accepted_parent_kernel": ACCEPTED_PARENT_KERNEL,
            "accepted_parent_source": ACCEPTED_PARENT_SOURCE,
            "risk_binding": RISK_BINDING,
            "source_relations": SOURCE_RELATIONS,
            "kernel_pair": {"reference": "e3nn", "candidate": "cueq_pure"},
            "learned_model_dtype": "float32",
            "production_law_scope": "one_active_governed_training_process_per_gpu",
            "exact_train2_keys": exact_keys,
            "expected_key_scopes": expected_key_scopes,
        },
        "git": git,
        "runtime": runtime,
        "campaign": campaign,
        "renewal_contract": {
            "pre_assignment": "Candidate-10 W_pre from exact law-binding record",
            "reference_child": "fresh OS process/private child state/e3nn",
            "candidate_child": "fresh OS process/private child state/cueq_pure",
            "sibling_overlap": False,
            "adaptive_warmup": False,
            "same_key_retry": False,
            "assignment": "uniform S3 after Lambda freeze; OS cryptographic entropy",
        },
        "pre_output_assertions": {
            "candidate10_training_executed": False,
            "manifest_is_identity_evidence_not_qualification_evidence": True,
        },
    }
    _require_exact_train2_keys(payload)
    _require_candidate10_key_coverage(payload, expected_key_scopes)
    payload["content_digest"] = manifest_content_digest(payload)
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Current campaign TOML.")
    parser.add_argument("--mpa0-model", required=True, help="Locked MPA-0-medium model.")
    parser.add_argument("--output", required=True, help="New preflight JSON path.")
    parser.add_argument(
        "--repo", default=str(Path(__file__).resolve().parents[1]), help="mdstats repo root."
    )
    parser.add_argument("--gpu-index", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output = Path(args.output).expanduser().resolve()
    payload = build_manifest(args)
    _require_exact_train2_keys(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        payload, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False
    ) + "\n"
    try:
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f"Refusing to overwrite preflight artifact: {output}") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    directory_fd = os.open(output.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    print(f"Candidate-10 Stage-C preflight written: {output}")
    print(f"content_digest={payload['content_digest']}")
    print("No Candidate-10 training trajectory was executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
