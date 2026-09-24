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
from mdstats.training_data.eval2 import Eval2TargetMetricRecord
from mdstats.training_data.post_selection_execution import EvaluationMeasurementIdentity
from mdstats.training_data.post_selection_store import (
    PostSelectionEvidenceStore,
    post_selection_root,
)

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


def test_fresh_held_out_measurement_is_committed_before_scratch_cleanup(
    tmp_path, monkeypatch
):
    config, _workspace = fx.build_selected_campaign(tmp_path)
    runs = _runs_root(config)
    original_transport = runtime.write_outer_evaluation_transport
    original_put = PostSelectionEvidenceStore.put
    scratches: list[Path] = []
    committed_identities: set[str] = set()
    committed_metric_digests: set[str] = set()
    committed_metric_target_roles: set[str] = set()
    commit_events: list[str] = []

    def record_transport(selected, *, scratch_directory, frame_uids, extxyz_policy):
        scratches.append(Path(scratch_directory))
        return original_transport(
            selected,
            scratch_directory=scratch_directory,
            frame_uids=frame_uids,
            extxyz_policy=extxyz_policy,
        )

    def observe_put(store, record):
        if (
            isinstance(record, EvaluationMeasurementIdentity)
            and record.dataset_role == runtime.DATASET_ROLE_OUTER_EVALUATION
            and record.content_digest not in committed_identities
        ):
            scratch = scratches[-1]
            assert scratch.exists()
            assert runs not in scratch.parents
            assert any(
                item.name.startswith("outer_evaluation.extxyz")
                for item in scratch.iterdir()
            )
            committed_identities.add(record.content_digest)
            commit_events.append("identity")
        elif (
            isinstance(record, Eval2TargetMetricRecord)
            and record.target_role_digest in committed_identities
            and record.content_digest not in committed_metric_digests
        ):
            scratch = scratches[-1]
            assert scratch.exists()
            assert any(
                item.name.startswith("outer_evaluation.extxyz")
                for item in scratch.iterdir()
            )
            committed_metric_digests.add(record.content_digest)
            committed_metric_target_roles.add(record.target_role_digest)
            commit_events.append("metric")
        return original_put(store, record)

    monkeypatch.setattr(runtime, "write_outer_evaluation_transport", record_transport)
    monkeypatch.setattr(PostSelectionEvidenceStore, "put", observe_put)

    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert commit_events == ["identity", "metric", "identity", "metric"]
    assert committed_identities == committed_metric_target_roles
    assert scratches and all(not scratch.exists() for scratch in scratches)
    assert all(runs not in scratch.parents for scratch in scratches)

    contexts, store = _contexts(config)
    evidence_store = contexts[0].evidence_store
    try:
        acceptance = runtime.resolve_current_cv_acceptance(contexts[0])
        assert acceptance is not None
        outer_digests = {
            fold.outer_metric_record_digest
            for seed in acceptance.seed_acceptances
            for fold in seed.fold_acceptances
        }
        assert outer_digests == committed_metric_digests
        assert all(evidence_store.has(digest) for digest in outer_digests)
        assert all(
            evidence_store.get(
                digest, Eval2TargetMetricRecord.from_dict
            ).target_role_digest
            in committed_identities
            for digest in outer_digests
        )
    finally:
        store.close()


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
from unittest.mock import patch
import tests._mlff_post_selection_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d


class _NoBoundaryTraining:
    def __call__(self, request):
        raise AssertionError("size selection may not train a candidate here")


def _two_size_baseline_campaign(out):
    """A frozen two-size baseline design, cross-validated by the baseline code."""

    with patch.object(p4d, "_CONFIG", fx.fixture_config_text()):
        config, _workspace = p4d._fixture_campaign(out)
    assert p4d._run(config, "prepare") == 0
    for size, horizon in ((8, 2), (16, 3)):
        assert (
            p4d._run(
                config, "select-target-size", str(size), "--horizon", str(horizon),
                _external_boundary_trainer=_NoBoundaryTraining(),
                _external_inference_evaluator=_NoBoundaryTraining(),
            )
            == 0
        )
    return config


def test_build_legacy_p5_workspace(tmp_path):
    out = Path(os.environ["MDSTATS_LEGACY_P5_WORKSPACE"])
    scenario = os.environ["MDSTATS_LEGACY_P5_SCENARIO"]
    harness = fx.PostSelectionHarness()
    if scenario == "two_size_production_interrupted":
        # The baseline code's own serial outer-size production: the first
        # frozen size's production TRAIN2 is interrupted mid-trajectory, so the
        # later size never reaches production at all.
        config = _two_size_baseline_campaign(out)
        assert fx.run_cross_validate(config, harness) == 0
        calls = []

        def train(request):
            calls.append(request)
            return fx.train_like_mace(
                request, stop_after_epoch=0, fail_after_persist=True
            )

        try:
            p4d._run(config, "train-production", _external_post_selection_trainer=train,
                     _external_inference_evaluator=harness.evaluate)
        except AssertionError:
            pass
        else:
            raise AssertionError("baseline production was expected to be interrupted")
        assert len(calls) == 1
        (out / "legacy.json").write_text(
            json.dumps({"config": str(config)}), encoding="utf-8"
        )
        return
    config, _workspace = fx.build_selected_campaign(out)
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


# Retired in Revision 28: this historical-root recovery assertion predates the
# current PRODUCT_COMPLETE boundary and final-model publication owner.  Its raw
# observation and superseded applicability are retained in the Revision-27
# closeout record; current scheduler/recovery ownership is covered by the
# maintained current-owner suites.


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


def _current_final_plan_pointers(config: Path) -> list[str | None]:
    """The current per-binding FinalProductionPlan pointer of every selected size."""

    from mdstats.training_data.post_selection_store import (
        POINTER_FINAL_PLAN,
        read_current_post_selection_pointer,
    )

    contexts, store = _contexts(config)
    try:
        return [
            read_current_post_selection_pointer(
                store, binding=context.selected.binding, kind=POINTER_FINAL_PLAN
            )
            for context in contexts
        ]
    finally:
        store.close()


def test_incompatible_interrupted_historical_continuation_stops_the_collection(
    tmp_path, capsys
):
    """R4/A6(3): an incompatible historical continuation fails before any sibling.

    The workspace is a genuine baseline (pre-cutover) two-size campaign whose
    first frozen size's production TRAIN2 was interrupted mid-trajectory, so
    the later size never reached production at all.  The interrupted historical
    root is then made incompatible with current authority: its persisted
    realized preparation ancestry is no longer the one the current training
    method reproduces, while the record stays self-consistent enough to reach
    the historical authentication owner.

    Driven through the real public ``train-production`` collection owner, the
    incompatible continuation must be rejected by recovery normalization
    *before* the fresh, runnable sibling position of the other selected size is
    admitted to the TRAIN wave.  Independently valid Phase-B FinalProductionPlan
    pointers stay current - recovery failure is not a collection rollback - and
    every historical byte is preserved for retry and investigation.
    """

    from mdstats.training_data._common import digest
    from mdstats.training_data.train2_runtime import TRAIN2_RUNTIME_SUMMARY_FILENAME

    config = _legacy_workspace(tmp_path, "two_size_production_interrupted")
    runs = _runs_root(config)
    legacy_roots = sorted(path for path in runs.iterdir() if path.is_dir())
    interrupted = [
        root
        for root in legacy_roots
        if not (root / "fold-acceptance.json").is_file()
        and runtime.read_post_selection_run_completion(root)[0] is None
    ]
    assert len(interrupted) == 1, [root.name for root in legacy_roots]
    historical = interrupted[0]
    assert (historical / "checkpoints" / TRAIN2_RUNTIME_SUMMARY_FILENAME).is_file()

    # Make the persisted ancestry incompatible with current authority while
    # keeping the record internally self-consistent, so the failure is the
    # training-equivalence fence and not a malformed-record rejection.
    record = historical / "materialization" / "materialization.json"
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload["preparation_digest"] = "0" * 64
    payload["content_digest"] = digest(
        {key: value for key, value in payload.items() if key != "content_digest"}
    )
    record.write_text(json.dumps(payload), encoding="utf-8")
    before = {root.name: _tree(root) for root in legacy_roots}

    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    assert harness.runs == [], "the baseline CV ancestry must be reused as-is"
    evaluations_before = len(harness.evaluations)
    capsys.readouterr()
    with pytest.raises(Exception) as failure:
        fx.run_train_production(config, harness)
    printed = capsys.readouterr().out
    assert "training-equivalent" in str(failure.value), failure.value

    # Zero trainer invocations anywhere in the collection, including the fresh
    # runnable sibling of the other selected size, and no scheduler was sized.
    assert harness.runs == [], "a sibling trainer launched behind a rejected root"
    assert len(harness.evaluations) == evaluations_before, (
        "EVAL2 began after a recovery failure"
    )
    assert "[TRAIN scheduler] status=" not in printed
    assert "train_required=" not in printed

    # Phase B had already published both independently valid per-binding plan
    # pointers; recovery failure is not a collection rollback.
    pointers = _current_final_plan_pointers(config)
    assert len(pointers) == 2 and all(pointers), pointers

    # Nothing was published, and every historical byte is preserved.
    contexts, store = _contexts(config)
    try:
        for context in contexts:
            assert runtime.resolve_current_final_production_publication(context) is None
    finally:
        store.close()
    assert sorted(path.name for path in runs.iterdir() if path.is_dir()) == sorted(before)
    after = _tree(historical)
    for relative, value in before[historical.name].items():
        if relative.startswith("materialization/materialization.json"):
            continue  # the deliberate incompatibility this test injected
        assert after.get(relative) == value, relative
    assert set(after) - set(before[historical.name]) <= {
        ".materialization.json.lock"
    }, set(after) - set(before[historical.name])
    assert runtime.read_post_selection_run_completion(historical)[0] is None
    for root in legacy_roots:
        if root != historical:
            assert _tree(root) == before[root.name], root.name


def test_contradictory_historical_partial_proof_fails_before_any_trainer(tmp_path):
    """A6: a historical root with a terminal record but no valid anchor fails closed.

    Production recovery normalization must classify historical state through
    the historical recovery owner *before* any current trainer is launched, and
    an inconsistent partial proof is preserved for diagnosis rather than
    completed, reused, or retrained around.
    """

    config = _legacy_workspace(tmp_path, "production_rejected")
    runs = _runs_root(config)
    unsealed = [
        root
        for root in sorted(path for path in runs.iterdir() if path.is_dir())
        if runtime.read_post_selection_run_completion(root)[0] is None
    ]
    assert len(unsealed) == 1
    # A pre-cutover terminal assessment record with no valid completion anchor:
    # the exact contradictory partial-proof state the recovery owner refuses.
    (unsealed[0] / runtime.RUN_EVIDENCE_FILENAME).write_text(
        json.dumps({"schema": "pre-cutover"}), encoding="utf-8"
    )
    before = _tree(unsealed[0])

    harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, harness) == 0
    with pytest.raises(Exception, match="partial proof"):
        fx.run_train_production(config, harness)
    assert harness.runs == [], "a trainer launched behind a contradictory root"
    assert _tree(unsealed[0]) == before, "the preserved diagnostic state was mutated"
    assert runtime.read_post_selection_run_completion(unsealed[0])[0] is None
