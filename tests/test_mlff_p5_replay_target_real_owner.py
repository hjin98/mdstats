"""Real-owner acceptance of the training-root / measurement / assessment split.

Every P1-P5 owner runs as production code through the real ``cross-validate``
and ``train-production`` commands; only MACE is substituted below the owner
boundary (the shared P5 harness).  The claims exercised here are those of the
reviewed D3/D4 contract (de360579):

* a post-cutover run root is training-only, sealed at authenticated terminal
  TRAIN2 before EVAL2, and never contains held-out evaluation transport or an
  assessment file;
* current CV/final assessments are immutable evidence-store objects located
  through the one position-addressed CampaignStore locator;
* assessment-policy-only edits launch zero TRAIN2 and reuse exact measurements;
* held-out label-only changes move only measurement/EVAL2/verdict descendants;
* attempt-local held-out scratch is outside the root, reclaimed, and carries no
  currentness;
* a genuine pre-cutover (baseline-code) workspace is reassessed with zero
  retraining and no historical-byte mutation, including the one append-only
  seal of a terminal-but-unsealed root and continuation of an interrupted one;
* root-dependent EVAL2 holds the run-activity lease against storage mutation.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
from pathlib import Path

import pytest

import tests._mlff_post_selection_fixture as fx
from mdstats.training_data import campaign_post_selection_runtime as runtime
from mdstats.training_data.post_selection_store import post_selection_root

pytestmark = pytest.mark.slow

#: The pre-cutover code (policy-overbound identities, root-local verdicts).
BASELINE_COMMIT = "afe6cb50dc6840799e86e1183c071761dab4e246"
REPOSITORY = Path(__file__).resolve().parents[1]


def _runs_root(config: Path) -> Path:
    _cfg, paths, store = fx.load_context(config)
    store.close()
    return post_selection_root(paths, 1) / "runs"


def _tree(root: Path) -> dict[str, str]:
    """Every node below ``root``: files by SHA-256, directories by kind."""

    nodes: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            nodes[relative] = "symlink"
        elif path.is_dir():
            nodes[relative] = "dir"
        else:
            nodes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return nodes


def _contexts(config: Path):
    cfg, paths, store = fx.load_context(config)
    return runtime.build_post_selection_contexts(cfg, paths, store), store


def _current_cv(config: Path):
    contexts, store = _contexts(config)
    try:
        context = contexts[0]
        return runtime.resolve_current_cv_plan(context), runtime.resolve_current_cv_acceptance(context)
    finally:
        store.close()


def _assert_training_only_sealed(run_root: Path) -> None:
    completion, why = runtime.read_post_selection_run_completion(run_root)
    assert completion is not None, why
    assert completion.terminal_proof is not None
    closed, why = runtime.certify_closed_post_selection_run_root(run_root)
    assert closed, why
    names = {path.name for path in run_root.rglob("*")}
    assert not any(name.startswith("outer_evaluation.extxyz") for name in names)
    assert "fold-acceptance.json" not in names and "run-evidence.json" not in names
    payload = json.loads((run_root / "materialization" / "materialization.json").read_text())
    assert not any("outer" in key for key in payload)


@pytest.fixture()
def completed_campaign(tmp_path: Path):
    config, _workspace = fx.build_selected_campaign(tmp_path)
    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert fx.run_train_production(config, harness) == 0
    assert len(harness.runs) == 3  # two CV folds + one production seed
    return config


def test_cutover_roots_are_training_only_and_assessments_are_external(completed_campaign):
    config = completed_campaign
    runs = _runs_root(config)
    roots = sorted(path for path in runs.iterdir() if path.is_dir())
    assert len(roots) == 3
    for root in roots:
        _assert_training_only_sealed(root)

    contexts, store = _contexts(config)
    try:
        context = contexts[0]
        plan = runtime.resolve_current_cv_plan(context)
        acceptance = runtime.resolve_current_cv_acceptance(context)
        assert acceptance is not None and acceptance.accepted
        policy = runtime.cv_assessment_position_policy_digest(
            runtime.post_selection_checkpoint_admissibility(
                context.method_policies, context.cv_policy
            ),
            context.cv_policy,
        )
        for seed, fold_index in plan.required_run_matrix:
            run_plan = runtime.build_cv_fold_run_plan(
                plan,
                fold_index=fold_index,
                optimizer_seed=seed,
                planned_epochs=context.cv_policy.cv_max_num_epochs,
            )
            located = runtime.resolve_current_post_selection_record(
                context.store,
                context.paths,
                context.selected,
                kind=runtime.POINTER_ASSESSMENT_POSITION,
                deserializer=runtime.CvFoldAcceptance.from_dict,
                position=runtime._cv_position(context, run_plan, policy),
            )
            assert located is not None and located.is_current
            assert located.training_trajectory_identity == run_plan.run_identity
            assert (runs / run_plan.run_identity).is_dir()
        completion = runtime.resolve_current_final_production_completion(context)
        assert completion is not None
        assert all(item.training_root_identity == item.training_trajectory_identity for item in completion.runs)
        assert runtime.resolve_current_final_production_publication(context) is not None
    finally:
        store.close()


def test_policy_only_edits_reassess_with_zero_train2_and_no_root_mutation(completed_campaign):
    config = completed_campaign
    runs = _runs_root(config)
    before = _tree(runs)
    _plan, old_acceptance = _current_cv(config)

    # theta_CV (outer verdict) and tau_prod (final hard policy) are both
    # assessment-only coordinates of this scratch campaign.
    fx.rewrite_config(config, "acceptance_maximum = 0.5", "acceptance_maximum = 0.4")
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text + "\n[acceptance]\nmaximum_target_force_rmse_ev_per_angstrom = 0.029\n",
        encoding="utf-8",
    )
    fx.rewrite_config(config, "0.029", "0.029")
    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert fx.run_train_production(config, harness) == 0

    assert harness.runs == []  # zero TRAIN2 launches
    assert harness.evaluations == []  # every measurement reused by exact identity
    assert _tree(runs) == before  # sealed roots untouched
    _plan, new_acceptance = _current_cv(config)
    assert new_acceptance.content_digest != old_acceptance.content_digest
    assert new_acceptance.accepted


def test_held_out_label_only_change_moves_only_measurement_descendants(
    completed_campaign, monkeypatch
):
    config = completed_campaign
    runs = _runs_root(config)
    before = _tree(runs)
    plan_before, acceptance_before = _current_cv(config)
    trajectories_before = {
        fold.training_trajectory_identity
        for seed in acceptance_before.seed_acceptances
        for fold in seed.fold_acceptances
    }
    outer_before = {
        fold.outer_metric_record_digest
        for seed in acceptance_before.seed_acceptances
        for fold in seed.fold_acceptances
    }
    original = runtime.write_outer_evaluation_transport
    scratch_seen: list[Path] = []

    def relabel(selected, *, scratch_directory, frame_uids, extxyz_policy):
        """Change only held-out reference forces in the EVAL2 transport."""

        artifact = original(
            selected,
            scratch_directory=scratch_directory,
            frame_uids=frame_uids,
            extxyz_policy=extxyz_policy,
        )
        import ase.io

        path = Path(scratch_directory) / artifact.relative_path
        frames = ase.io.read(path, index=":", format="extxyz")
        for atoms in frames:
            atoms.arrays[extxyz_policy.forces_key] = (
                atoms.arrays[extxyz_policy.forces_key] + 0.01
            )
        ase.io.write(path, frames, format="extxyz")
        scratch_seen.append(Path(scratch_directory))
        return dataclasses.replace(
            artifact, sha256=hashlib.sha256(path.read_bytes()).hexdigest()
        )

    monkeypatch.setattr(runtime, "write_outer_evaluation_transport", relabel)
    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0

    assert harness.runs == []  # no TRAIN2
    assert _tree(runs) == before  # training roots/materialization untouched
    plan_after, acceptance_after = _current_cv(config)
    assert plan_after.content_digest == plan_before.content_digest
    folds_after = [
        fold for seed in acceptance_after.seed_acceptances for fold in seed.fold_acceptances
    ]
    assert {fold.training_trajectory_identity for fold in folds_after} == trajectories_before
    # Only the held-out measurement (and the verdict records binding it) moved:
    # monitor candidate measurements were reused, the outer ones recomputed.
    assert {fold.outer_metric_record_digest for fold in folds_after}.isdisjoint(outer_before)
    assert len(harness.evaluations) == len(folds_after)
    for scratch in scratch_seen:
        assert not scratch.exists()
        assert runs not in scratch.parents


def test_eval2_scratch_deletion_does_not_invalidate_durable_measurements(
    completed_campaign, monkeypatch
):
    config = completed_campaign
    runs = _runs_root(config)
    recorded: list[Path] = []
    original = runtime.write_outer_evaluation_transport

    def record(selected, *, scratch_directory, frame_uids, extxyz_policy):
        recorded.append(Path(scratch_directory))
        return original(
            selected,
            scratch_directory=scratch_directory,
            frame_uids=frame_uids,
            extxyz_policy=extxyz_policy,
        )

    monkeypatch.setattr(runtime, "write_outer_evaluation_transport", record)
    # A theta-only edit forces a new fold assessment that must re-realize the
    # held-out transport identity; the published outer measurement is reused.
    fx.rewrite_config(config, "acceptance_maximum = 0.5", "acceptance_maximum = 0.45")
    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert recorded and all(not path.exists() for path in recorded)
    assert all(runs not in path.parents and path != runs for path in recorded)
    assert harness.runs == [] and harness.evaluations == []


def test_required_composition_projection_is_training_bearing_and_label_blind(
    completed_campaign, monkeypatch
):
    from mdstats.training_data import post_selection_execution as execution

    contexts, store = _contexts(completed_campaign)
    try:
        selected = contexts[0].selected
        plan = runtime.resolve_current_cv_plan(contexts[0])
        fold = plan.fold(0)
        consumers = tuple(fold.outer_evaluation_frame_uids)
        base = execution.transfer_consumer_composition_digest(
            selected, training_mode="naive_fine_tuning", consumer_frame_uids=consumers
        )
        assert base is not None
        assert execution.transfer_consumer_composition_digest(
            selected, training_mode="scratch", consumer_frame_uids=consumers
        ) is None
        original = execution._composition_counts_by_frame

        def changed(context, frame_uids):
            result = dict(original(context, frame_uids))
            first = str(frame_uids[0])
            result[first] = ((1, 1),) + tuple(result[first])
            return result

        monkeypatch.setattr(execution, "_composition_counts_by_frame", changed)
        moved = execution.transfer_consumer_composition_digest(
            selected, training_mode="naive_fine_tuning", consumer_frame_uids=consumers
        )
        assert moved != base
        trajectory = runtime.build_cv_fold_run_plan(
            plan, fold_index=0, optimizer_seed=plan.required_cv_seeds[0], planned_epochs=2
        ).training_trajectory
        assert dataclasses.replace(
            trajectory, transfer_consumer_composition_digest=moved
        ).content_digest != trajectory.content_digest
    finally:
        store.close()


def test_root_dependent_eval2_excludes_storage_mutation_without_lock_inversion(
    tmp_path, monkeypatch
):
    from mdstats.training_data.storage.lease import (
        OwnerSynchronization,
        owner_mutation_barrier,
    )

    config, _workspace = fx.build_selected_campaign(tmp_path)
    harness = fx.PostSelectionHarness()
    in_eval2 = threading.Event()
    release = threading.Event()
    original = harness.evaluate
    storage_entered: list[float] = []
    import time

    def slow_evaluate(provider, atoms_list):
        if not in_eval2.is_set():
            in_eval2.set()
            assert release.wait(30.0)
        return original(provider, atoms_list)

    harness.evaluate = slow_evaluate
    result: dict[str, object] = {}

    def cross_validate():
        try:
            result["code"] = fx.run_cross_validate(config, harness)
        except BaseException as exc:  # pragma: no cover - reported below
            result["error"] = exc

    worker = threading.Thread(target=cross_validate)
    worker.start()
    assert in_eval2.wait(120.0)
    runs = _runs_root(config)
    sealed = [
        root for root in runs.iterdir()
        if runtime.read_post_selection_run_completion(root)[0] is not None
    ]
    assert sealed
    _cfg, paths, store = fx.load_context(config)
    store.close()

    def mutate():
        with owner_mutation_barrier(
            paths,
            OwnerSynchronization(generations=(1,), run_roots=tuple(sealed), attempt_roots=()),
        ):
            storage_entered.append(time.monotonic())

    mutator = threading.Thread(target=mutate)
    mutator.start()
    mutator.join(1.0)
    # Storage cannot enter while a root is being read by EVAL2.
    assert mutator.is_alive() and not storage_entered
    released_at = time.monotonic()
    release.set()
    worker.join(300.0)
    mutator.join(300.0)
    assert not worker.is_alive() and not mutator.is_alive()
    assert result.get("code") == 0, result.get("error")
    assert storage_entered and storage_entered[0] >= released_at


# ---------------------------------------------------------------------------
# Genuine pre-cutover workspaces, built by the baseline code itself
# ---------------------------------------------------------------------------

_LEGACY_BUILDER = '''
import json, os
from pathlib import Path
import tests._mlff_post_selection_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d


def test_build_legacy_p5_workspace(tmp_path):
    out = Path(os.environ["MDSTATS_LEGACY_P5_WORKSPACE"])
    scenario = os.environ["MDSTATS_LEGACY_P5_SCENARIO"]
    config, _workspace = fx.build_selected_campaign(out)
    harness = fx.PostSelectionHarness()
    if scenario == "cv_interrupted":
        calls = []

        def train(request):
            calls.append(request)
            if len(calls) == 2:
                return fx.train_like_mace(request, stop_after_epoch=0, fail_after_persist=True)
            return harness.train(request)

        try:
            p4d._run(config, "cross-validate", _external_post_selection_trainer=train,
                     _external_inference_evaluator=harness.evaluate)
        except AssertionError:
            pass
        else:
            raise AssertionError("the baseline CV was expected to be interrupted")
    else:
        assert fx.run_cross_validate(config, harness) == 0
        # The baseline production trains to its terminal epoch and then finds
        # no admissible checkpoint (the measured target error exceeds the
        # 0.030 ceiling), so its root is terminal but never sealed - the state
        # the motivating failed production run left behind.
        harness.force_offset = 1.0
        try:
            fx.run_train_production(config, harness)
        except Exception as exc:
            assert "passed" in str(exc) and "admissib" in str(exc), exc
        else:
            raise AssertionError("baseline production was expected to reject every checkpoint")
    (out / "legacy.json").write_text(json.dumps({"config": str(config)}), encoding="utf-8")
'''


def _legacy_workspace(tmp_path: Path, scenario: str) -> Path:
    """Build one workspace with the baseline (pre-cutover) code itself."""

    if shutil.which("git") is None:
        pytest.skip("git is required to realize the baseline pre-cutover code")
    source = tmp_path / "baseline-source"
    source.mkdir()
    archive = subprocess.run(
        ["git", "-C", str(REPOSITORY), "archive", "--format=tar", BASELINE_COMMIT,
         "mdstats", "tests", "pyproject.toml", "setup.cfg"],
        capture_output=True,
        check=False,
    )
    if archive.returncode != 0:
        pytest.skip(f"baseline commit {BASELINE_COMMIT[:12]} is unavailable in this repository")
    import io

    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(source)
    (source / "tests" / "test_mlff_zz_build_legacy_p5_workspace.py").write_text(
        _LEGACY_BUILDER, encoding="utf-8"
    )
    workspace = tmp_path / "legacy"
    workspace.mkdir()
    environment = {
        **os.environ,
        "PYTHONPATH": str(source),
        "MDSTATS_LEGACY_P5_WORKSPACE": str(workspace),
        "MDSTATS_LEGACY_P5_SCENARIO": scenario,
    }
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly", "-p", "no:cacheprovider",
         "tests/test_mlff_zz_build_legacy_p5_workspace.py"],
        cwd=str(source),
        env=environment,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout[-4000:] + completed.stderr[-4000:]
    return Path(json.loads((workspace / "legacy.json").read_text())["config"])


def test_sealed_and_terminal_unsealed_legacy_roots_are_reused_without_byte_mutation(tmp_path):
    config = _legacy_workspace(tmp_path, "production_rejected")
    runs = _runs_root(config)
    legacy_roots = sorted(path for path in runs.iterdir() if path.is_dir())
    assert len(legacy_roots) == 3
    sealed_cv = [root for root in legacy_roots if (root / "fold-acceptance.json").is_file()]
    unsealed = [root for root in legacy_roots if root not in sealed_cv]
    assert len(sealed_cv) == 2 and len(unsealed) == 1
    assert runtime.read_post_selection_run_completion(unsealed[0])[0] is None
    before = {root.name: _tree(root) for root in legacy_roots}

    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert fx.run_train_production(config, harness) == 0
    assert harness.runs == []  # zero TRAIN2 launches: every trajectory reused
    assert harness.evaluations  # historical measurements are not scalar-reused

    # No new training root was created under the current trajectory names.
    assert sorted(path.name for path in runs.iterdir() if path.is_dir()) == sorted(before)
    for root in sealed_cv:  # already sealed: strictly read-only
        assert _tree(root) == before[root.name]
    after = _tree(unsealed[0])
    for relative, value in before[unsealed[0].name].items():
        assert after[relative] == value  # no pre-existing byte rewritten
    appended = set(after) - set(before[unsealed[0].name])
    assert appended <= {
        "run-topology.json", "run-completion.json",
        ".run-topology.json.lock", ".run-completion.json.lock",
    }
    assert {"run-topology.json", "run-completion.json"} <= appended
    completion, why = runtime.read_post_selection_run_completion(unsealed[0])
    assert completion is not None and completion.terminal_proof is not None, why

    contexts, store = _contexts(config)
    try:
        context = contexts[0]
        _plan, acceptance = runtime.resolve_current_cv_plan(context), runtime.resolve_current_cv_acceptance(context)
        assert acceptance.accepted
        folds = [f for s in acceptance.seed_acceptances for f in s.fold_acceptances]
        assert {f.training_root_identity for f in folds} == {root.name for root in sealed_cv}
        assert all(f.training_trajectory_identity != f.training_root_identity for f in folds)
        decision = runtime.resolve_current_final_production_publication(context)
        assert decision is not None
        assert [item.run_identity for item in decision.published_seed_evidence] == [unsealed[0].name]
    finally:
        store.close()


def test_interrupted_legacy_cv_continues_under_historical_identities(tmp_path):
    config = _legacy_workspace(tmp_path, "cv_interrupted")
    runs = _runs_root(config)
    legacy_roots = sorted(path for path in runs.iterdir() if path.is_dir())
    assert len(legacy_roots) == 2
    before = {root.name: _tree(root) for root in legacy_roots}

    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    # Exactly the interrupted trajectory continued; nothing trained from scratch.
    assert len(harness.requests) == 1
    request = harness.requests[0]
    assert request.start_epoch > 0
    assert request.materialization_directory.parent.name in before
    assert sorted(path.name for path in runs.iterdir() if path.is_dir()) == sorted(before)
    for root in legacy_roots:
        completion, why = runtime.read_post_selection_run_completion(root)
        assert completion is not None, why
        after = _tree(root)
        for relative, value in before[root.name].items():
            if relative.startswith("checkpoints/") or relative.startswith("results") or relative in {
                "metrics.jsonl", "materialization/mace_run_config.yaml"
            }:
                continue  # the continued trajectory legitimately appends TRAIN2 state
            assert after.get(relative) == value, relative
    _plan, acceptance = _current_cv(config)
    assert acceptance is not None and acceptance.accepted
