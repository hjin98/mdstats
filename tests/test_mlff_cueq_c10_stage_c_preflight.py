from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "run_mlff_cueq_c10_stage_c_preflight.py"
spec = importlib.util.spec_from_file_location("c10_preflight", MODULE_PATH)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_canonical_json_digest_is_order_independent():
    a = {"b": 2, "a": [1, {"z": 3}]}
    b = {"a": [1, {"z": 3}], "b": 2}
    assert hashlib.sha256(m.canonical_json_bytes(a)).hexdigest() == hashlib.sha256(
        m.canonical_json_bytes(b)
    ).hexdigest()


def test_selected_gpu_apps_filters_to_selected_uuid():
    gpu = "NVIDIA GeForce RTX 3090, GPU-AAA, 555.1, 24576, 24000"
    apps = "100, python, 1024, GPU-BBB\n200, python, 2048, GPU-AAA"
    assert m._selected_gpu_apps(gpu, apps) == [
        {
            "pid": "200",
            "process_name": "python",
            "used_gpu_memory_mib": "2048",
            "gpu_uuid": "GPU-AAA",
        }
    ]


def test_source_relations_remain_accepted_parent_values():
    assert m.SOURCE_RELATIONS["cv_checkpoint_target_force_rmse_ev_per_angstrom"] == 0.045
    assert m.SOURCE_RELATIONS["cv_outer_target_force_rmse_ev_per_angstrom"] == 0.045
    assert m.SOURCE_RELATIONS["production_checkpoint_target_force_rmse_ev_per_angstrom"] == 0.030
    assert m.SOURCE_RELATIONS["replay_degradation_hard_budget_ev_per_angstrom"] == 0.030


def test_risk_binding_is_frozen_instance_choice():
    assert m.RISK_BINDING == {
        "eta_NI": 0.09,
        "q_cat": 0.09,
        "n_triplets": 300,
        "n_eval_triplets": 300,
        "simultaneous_confidence": 0.95,
        "per_statement_alpha": 0.0125,
    }


def test_git_identity_contains_the_accepted_parent_and_ratified_bindings(monkeypatch, tmp_path):
    blobs = {
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_10.md": m.CANDIDATE_BLOB,
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_RISK_BINDING.md": m.RISK_BINDING_BLOB,
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_LAW_BINDING.md": m.LAW_BINDING_BLOB,
    }
    monkeypatch.setattr(
        m,
        "_run",
        lambda argv, *, cwd=None: {
            ("git", "rev-parse", "--show-toplevel"): str(tmp_path),
            ("git", "status", "--porcelain=v1", "--untracked-files=all"): "",
            ("git", "branch", "--show-current"): m.EXPECTED_BRANCH,
            ("git", "rev-parse", "HEAD"): "head-commit",
        }[tuple(argv)],
    )
    monkeypatch.setattr(m, "_git_hash", lambda _repo, path: blobs[path])
    monkeypatch.setattr(m, "_require_candidate_ancestor", lambda *_args: None)
    monkeypatch.setattr(m, "_require_exact_commit", lambda *_args: None)

    identity = m.collect_git(str(tmp_path))
    assert identity["accepted_parent_kernel"] == m.ACCEPTED_PARENT_KERNEL
    assert identity["accepted_parent_source"] == m.ACCEPTED_PARENT_SOURCE
    assert identity["candidate_commit"] == m.CANDIDATE_COMMIT
    assert identity["risk_binding_blob"] == m.RISK_BINDING_BLOB
    assert identity["law_binding_blob"] == m.LAW_BINDING_BLOB


def test_git_identity_rejects_a_changed_ratified_law_binding(monkeypatch, tmp_path):
    blobs = {
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_10.md": m.CANDIDATE_BLOB,
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_RISK_BINDING.md": m.RISK_BINDING_BLOB,
        "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_LAW_BINDING.md": "0" * 40,
    }
    monkeypatch.setattr(
        m,
        "_run",
        lambda argv, *, cwd=None: {
            ("git", "rev-parse", "--show-toplevel"): str(tmp_path),
            ("git", "status", "--porcelain=v1", "--untracked-files=all"): "",
            ("git", "branch", "--show-current"): m.EXPECTED_BRANCH,
            ("git", "rev-parse", "HEAD"): "head-commit",
        }[tuple(argv)],
    )
    monkeypatch.setattr(m, "_git_hash", lambda _repo, path: blobs[path])
    monkeypatch.setattr(m, "_require_candidate_ancestor", lambda *_args: None)
    monkeypatch.setattr(m, "_require_exact_commit", lambda *_args: None)

    with pytest.raises(RuntimeError, match="law/role binding mismatch"):
        m.collect_git(str(tmp_path))


def _git_repo(tmp_path: Path, *, candidate_bytes: bytes | None = None) -> Path:
    repo = tmp_path / "repo"
    candidate = (
        repo
        / "workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_10.md"
    )
    candidate.parent.mkdir(parents=True)
    if candidate_bytes is None:
        source = MODULE_PATH.parents[1] / candidate.relative_to(repo)
        shutil.copyfile(source, candidate)
    else:
        candidate.write_bytes(candidate_bytes)
    for name in (
        "MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_RISK_BINDING.md",
        "MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_LAW_BINDING.md",
    ):
        shutil.copyfile(
            MODULE_PATH.parents[1] / "workplans/active" / name,
            repo / "workplans/active" / name,
        )
    subprocess.run(
        ["git", "init", "--initial-branch", m.EXPECTED_BRANCH],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Preflight test"], cwd=repo, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "preflight@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


def _head(repo: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_collect_git_accepts_only_clean_requested_branch_and_exact_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _git_repo(tmp_path)
    monkeypatch.setattr(m, "CANDIDATE_COMMIT", _head(repo))
    monkeypatch.setattr(m, "_require_exact_commit", lambda *_args: None)
    record = m.collect_git(str(repo))
    assert record["branch"] == m.EXPECTED_BRANCH
    assert record["candidate_blob"] == m.CANDIDATE_BLOB

    (repo / "untracked.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(RuntimeError, match="clean repository"):
        m.collect_git(str(repo))


def test_collect_git_rejects_wrong_candidate_blob_and_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    changed = _git_repo(tmp_path / "changed", candidate_bytes=b"tampered\n")
    monkeypatch.setattr(m, "CANDIDATE_COMMIT", _head(changed))
    with pytest.raises(RuntimeError, match="Candidate-10 blob mismatch"):
        m.collect_git(str(changed))

    wrong_branch = _git_repo(tmp_path / "branch")
    monkeypatch.setattr(m, "CANDIDATE_COMMIT", _head(wrong_branch))
    subprocess.run(
        ["git", "switch", "-c", "other-branch"],
        cwd=wrong_branch,
        check=True,
        capture_output=True,
        text=True,
    )
    with pytest.raises(RuntimeError, match="requires branch"):
        m.collect_git(str(wrong_branch))


def test_collect_git_rejects_disconnected_candidate_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo = _git_repo(tmp_path)
    branch_head = _head(repo)
    subprocess.run(
        ["git", "checkout", "--orphan", "unrelated-history"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "disconnected candidate copy"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    disconnected = _head(repo)
    subprocess.run(
        ["git", "switch", m.EXPECTED_BRANCH],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert _head(repo) == branch_head
    monkeypatch.setattr(m, "CANDIDATE_COMMIT", disconnected)
    with pytest.raises(RuntimeError, match="is not an ancestor"):
        m.collect_git(str(repo))


def test_locked_model_and_checkpoint_files_reject_wrong_bytes(tmp_path: Path):
    model = tmp_path / "model"
    model.write_bytes(b"wrong locked model")
    with pytest.raises(RuntimeError, match="MH-1 source SHA-256 mismatch"):
        m._locked_file_record(model, m.MH1_SOURCE_SHA256, "MH-1 source")


def test_runtime_and_device_mismatches_fail_closed():
    versions = {
        key: value
        for key, value in m.EXPECTED_RUNTIME.items()
        if key != "torch_cuda"
    }
    m._require_runtime_family(versions, m.EXPECTED_RUNTIME["torch_cuda"])
    with pytest.raises(RuntimeError, match="Runtime family mismatch"):
        m._require_runtime_family({**versions, "mace": "0.0.0"}, "12.6")
    with pytest.raises(RuntimeError, match="Runtime family mismatch"):
        m._require_runtime_family(versions, "wrong-cuda")

    m._require_rtx3090("NVIDIA GeForce RTX 3090", 8, 6)
    with pytest.raises(RuntimeError, match="RTX 3090"):
        m._require_rtx3090("other GPU", 8, 6)
    with pytest.raises(RuntimeError, match="RTX 3090"):
        m._require_rtx3090("NVIDIA GeForce RTX 3090", 9, 0)


def test_competing_selected_gpu_process_fails_closed():
    gpu = "NVIDIA GeForce RTX 3090, GPU-AAA, 555.1, 24576, 24000"
    with pytest.raises(RuntimeError, match="already has compute processes"):
        m._require_no_selected_gpu_apps(
            gpu, "200, python, 2048, GPU-AAA\n201, python, 1024, GPU-BBB"
        )


def test_manifest_digest_verification_covers_all_fields():
    payload = {"schema": m.SCHEMA, "candidate": "C10"}
    payload["content_digest"] = m.manifest_content_digest(payload)
    assert m.verify_manifest_content_digest(payload)
    assert not m.verify_manifest_content_digest({**payload, "candidate": "C9"})


def _manifest_with_exact_key():
    coordinates = {
        "d": "float32",
        "theta_0": {"model_family": "mace_mh_1", "sha256": "a" * 64},
        "q_0": {"sha256": "b" * 64},
        "D": {
            "selected_binding": {"content_digest": "c" * 64},
            "sha256": "c" * 64,
        },
        "E": {"role": "cv", "sha256": "d" * 64},
        "O": {"sha256": "e" * 64},
        "H": {"sha256": "f" * 64},
        "K": [
            {"kernel": "e3nn", "calculator_kwargs": {"enable_cueq": False, "enable_oeq": False}},
            {"kernel": "cueq_pure", "calculator_kwargs": {"enable_cueq": True, "enable_oeq": False}},
        ],
        "rho": {"sha256": "1" * 64},
        "m": {"sha256": "2" * 64},
        "R": {"sha256": "3" * 64},
    }
    exact_key = {
        **coordinates,
        "key_digest": m.train2_key_digest(coordinates),
    }
    body = {"schema": m.SCHEMA, "candidate10": {"exact_train2_keys": [exact_key]}}
    return {**body, "content_digest": m.manifest_content_digest(body)}


def test_preflight_publication_requires_exact_candidate10_key_coordinates():
    with pytest.raises(RuntimeError, match="No exact Candidate-10 TRAIN2 key"):
        m._require_exact_train2_keys({"candidate10": {}})

    payload = _manifest_with_exact_key()
    m._require_exact_train2_keys(payload)
    m._require_candidate10_key_coverage(
        payload,
        [
            {
                "model_family": "mace_mh_1",
                "role": "cv",
                "selected_binding_digest": "c" * 64,
            }
        ],
    )
    with pytest.raises(RuntimeError, match="coverage is incomplete"):
        m._require_candidate10_key_coverage(
            payload,
            [
                {
                    "model_family": "mace_mpa_0",
                    "role": "final_production",
                    "selected_binding_digest": "c" * 64,
                }
            ],
        )
    key = payload["candidate10"]["exact_train2_keys"][0]
    with pytest.raises(RuntimeError, match="digest mismatch"):
        m._require_exact_train2_keys(
            {
                "candidate10": {
                    "exact_train2_keys": [{**key, "E": {"sha256": "0" * 64}}]
                }
            }
        )

    with pytest.raises(RuntimeError, match="exact DEF.001 coordinates"):
        m._require_exact_train2_keys(
            {"candidate10": {"exact_train2_keys": [{"key_digest": "0" * 64}]}}
        )
    with pytest.raises(RuntimeError, match="Duplicate exact Candidate-10 TRAIN2 key"):
        m._require_exact_train2_keys(
            {"candidate10": {"exact_train2_keys": [key, dict(key)]}}
        )


def test_target_key_projection_requires_existing_authenticated_extxyz(tmp_path: Path):
    binding = SimpleNamespace(campaign_generation=3)
    context = SimpleNamespace(
        paths=SimpleNamespace(internal=tmp_path),
        selected=SimpleNamespace(binding=binding),
        method_policies=SimpleNamespace(extxyz=object()),
    )
    trajectory = {"content_digest": "a" * 64}
    with pytest.raises(RuntimeError, match="cannot bind the exact target ExtXYZ transport"):
        m._target_transport_identity(
            context,
            trajectory=trajectory,
            training_frame_uids=("frame-1",),
            monitor_frame_uids=("frame-2",),
        )
    assert not (tmp_path / "post-selection" / "g3" / "runs" / ("a" * 64)).exists()


def test_campaign_store_missing_or_unselected_lineage_fails_closed(tmp_path: Path):
    import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
    from mdstats.training_data._campaign_cli_core import (
        CampaignCliError,
        CampaignStore,
        _load_config,
    )
    from mdstats.training_data.campaign_target_size_cutover import (
        TargetSizeCutoverError,
    )

    config, _workspace = p4d._fixture_campaign(tmp_path)
    _cfg, paths = _load_config(config, ensure=False)

    paths.state_db.unlink()
    with pytest.raises(CampaignCliError, match="Campaign state database is missing"):
        m.collect_campaign(str(config), str(tmp_path / "unused-mpa0.model"))

    # An initialized store without the selected/frozen P4 lineage is not a
    # valid exact Candidate-10 key. Exercise the production context owner.
    store = CampaignStore(paths.state_db)
    store.close()
    with pytest.raises(TargetSizeCutoverError, match="retired target-size selection state"):
        m.collect_campaign(str(config), str(tmp_path / "unused-mpa0.model"))


def test_output_creation_is_exclusive_even_if_another_writer_wins_the_race(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output = tmp_path / "preflight.json"
    real_open = m.os.open

    def concurrent_create(path, flags, mode=0o777):
        if Path(path) == output:
            output.write_text("other writer", encoding="utf-8")
        return real_open(path, flags, mode)

    monkeypatch.setattr(m, "build_manifest", lambda _args: _manifest_with_exact_key())
    monkeypatch.setattr(m.os, "open", concurrent_create)
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        m.main(
            [
                "--config",
                str(tmp_path / "unused.toml"),
                "--mpa0-model",
                str(tmp_path / "unused.model"),
                "--output",
                str(output),
            ]
        )
    assert output.read_text(encoding="utf-8") == "other writer"


def test_output_is_durable_content_addressed_and_never_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output = tmp_path / "nested" / "preflight.json"
    payload = _manifest_with_exact_key()
    monkeypatch.setattr(m, "build_manifest", lambda _args: payload)
    args = [
        "--config",
        str(tmp_path / "unused.toml"),
        "--mpa0-model",
        str(tmp_path / "unused.model"),
        "--output",
        str(output),
    ]
    assert m.main(args) == 0
    written = json.loads(output.read_text(encoding="utf-8"))
    assert m.verify_manifest_content_digest(written)
    original = output.read_bytes()
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        m.main(args)
    assert output.read_bytes() == original


def test_preflight_never_publishes_observations_without_a_frozen_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    output = tmp_path / "preflight.json"
    monkeypatch.setattr(
        m,
        "build_manifest",
        lambda _args: {"schema": m.SCHEMA, "candidate10": {"exact_train2_keys": []}},
    )
    with pytest.raises(RuntimeError, match="No exact Candidate-10 TRAIN2 key"):
        m.main(
            [
                "--config",
                str(tmp_path / "unused.toml"),
                "--mpa0-model",
                str(tmp_path / "unused.model"),
                "--output",
                str(output),
            ]
        )
    assert not output.exists()
