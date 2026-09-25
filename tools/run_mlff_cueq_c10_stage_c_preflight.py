#!/usr/bin/env python3
"""Freeze Candidate-10 Stage-C identity before any R1/R2/C trajectory runs."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
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
    return hashlib.sha256(canonical_json_bytes(coordinates)).hexdigest()


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
        coordinates = {name: key[name] for name in TRAIN2_KEY_COORDINATES}
        expected = train2_key_digest(coordinates)
        actual = key.get("key_digest")
        if actual != expected:
            raise RuntimeError(
                f"Candidate-10 TRAIN2 key {index} digest mismatch: expected {expected}, "
                f"got {actual}."
            )
        if expected in observed_digests:
            raise RuntimeError(f"Duplicate exact Candidate-10 TRAIN2 key at index {index}.")
        observed_digests.add(expected)


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
    return {
        "repo_root": str(repo),
        "head": _run(("git", "rev-parse", "HEAD"), cwd=repo),
        "branch": branch,
        "clean_before_manifest": True,
        "candidate_blob": candidate,
        "risk_binding_blob": _git_hash(
            repo,
            "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_RISK_BINDING.md",
        ),
        "law_binding_blob": _git_hash(
            repo,
            "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_LAW_BINDING.md",
        ),
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
        "projection_source_modules": projection_sources,
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


def collect_campaign(config_arg: str, mpa0_arg: str) -> dict[str, Any]:
    import mdstats
    from mdstats.training_data._campaign_cli_core import CampaignStore, _load_config
    from mdstats.training_data.campaign_lifecycle import campaign_owner_snapshot
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
        resolve_current_cv_plan,
        resolve_current_final_production_plan,
    )

    cfg, paths = _load_config(Path(config_arg).expanduser().resolve(), ensure=False)
    store = CampaignStore(paths.state_db, create=False)
    revision, bindings, pointers = campaign_owner_snapshot(store)
    contexts = build_post_selection_contexts(
        cfg, paths, store, trainer=object(), inference_evaluator=None, admit=False
    )
    if not contexts:
        raise RuntimeError("No frozen selected post-selection context exists.")

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

    selected_contexts: list[dict[str, Any]] = []
    for context in contexts:
        monitor, separation = context.common_target_monitor()
        try:
            cv_plan = resolve_current_cv_plan(context)
            cv_plan_value, cv_plan_error = None if cv_plan is None else cv_plan.to_dict(), None
        except Exception as exc:
            cv_plan_value, cv_plan_error = None, f"{type(exc).__name__}: {exc}"
        try:
            final_plan = resolve_current_final_production_plan(context)
            final_plan_value, final_plan_error = (
                None if final_plan is None else final_plan.to_dict(),
                None,
            )
        except Exception as exc:
            final_plan_value, final_plan_error = None, f"{type(exc).__name__}: {exc}"

        cv_tau = context.cv_policy.checkpoint_maximum_target_force_rmse_ev_per_angstrom
        cv_theta = context.cv_policy.acceptance_maximum
        prod_tau = context.production_policy.checkpoint_maximum_target_force_rmse_ev_per_angstrom
        selected_contexts.append(
            {
                "n_selected": context.selected.n_selected,
                "selected_binding": context.selected.binding.to_dict(),
                "selected_membership": [str(v) for v in context.selected.selected_membership],
                "method_training_identity": context.method.to_dict(),
                "common_monitor": monitor.to_dict(),
                "common_monitor_separation": separation.to_dict(),
                "current_cv_plan": cv_plan_value,
                "current_cv_plan_error": cv_plan_error,
                "current_final_plan": final_plan_value,
                "current_final_plan_error": final_plan_error,
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

    return {
        "config": {"path": str(paths.config), "sha256": sha256_file(paths.config)},
        "workspace": str(paths.workspace),
        "owner_snapshot": {
            "revision": _jsonable(revision),
            "bindings": _jsonable(bindings),
            "pointers": _jsonable(pointers),
        },
        "selected_contexts": selected_contexts,
        "models": {
            "mh1_source": mh1,
            "mh1_selected_head": selected,
            "mh1_selected_head_qualification": q.to_dict(),
            "mpa0": mpa0,
        },
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
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
        },
        "git": collect_git(args.repo),
        "runtime": collect_runtime(args.gpu_index),
        "campaign": collect_campaign(args.config, args.mpa0_model),
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
