"""P5 CV fold outcomes when no checkpoint passes mandatory admissibility.

A nonempty checkpoint-candidate set in which every candidate fails mandatory
admissibility is a valid negative cross-validation result for that fold: it is
a completed, rejected fold verdict with no representative and no held-out outer
evaluation.  An empty candidate set, corrupt candidate evidence, or an outer
evaluation failure after a representative was frozen stay hard failures.

The result-boundary tests drive ``select_cv_fold_representative``,
``build_cv_fold_acceptance`` and ``CvFoldAcceptance`` directly.  The runtime
tests drive the real ``cross-validate`` command through the shared bounded
MACE seams, instrumenting the real dataset-evaluation seam to count outer
evaluations.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given, settings, strategies as st

import mdstats
from tests.test_mlff_eval2 import point, target_metrics

from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.post_selection_cv_acceptance import (
    CV_FOLD_ACCEPTANCE_SCHEMA,
    CV_FOLD_ACCEPTANCE_SCHEMA_V1,
    CV_FOLD_NO_ADMISSIBLE_REASON,
    CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE,
    CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED,
    CvCampaignAcceptance,
    CvFoldAcceptance,
    build_cv_fold_acceptance,
    select_cv_fold_representative,
)

_SELECTION = mdstats.CheckpointSelectionPolicy()
_SEED_DIGEST = "5" * 64
_POLICY = SimpleNamespace(
    acceptance_metric="target_force_rmse_ev_per_angstrom", acceptance_maximum=0.02
)
_RUN_PLAN = SimpleNamespace(
    cv_plan_digest="a" * 64,
    content_digest="b" * 64,
    run_identity="c" * 64,
    fold_index=0,
    optimizer_seed=11,
)


def _candidate(
    epoch: int,
    rmse: float,
    *,
    policy: mdstats.CheckpointAdmissibilityPolicy,
    replay_candidate: float | None = None,
):
    replay = policy.replay_enabled
    return mdstats.assess_eval2_checkpoint(
        point(epoch, rmse),
        evaluation_record_digest=f"{epoch + 1:x}".rjust(64, "d"),
        target_metrics=target_metrics(rmse, pred_digest=f"{epoch + 1:x}".rjust(64, "e")),
        admissibility_policy=policy,
        replay_candidate_force_rmse_ev_per_angstrom=replay_candidate if replay else None,
        replay_foundation_force_rmse_ev_per_angstrom=0.020 if replay else None,
        replay_label_mode="true_dft" if replay else None,
    )


def _no_replay(**kwargs) -> mdstats.CheckpointAdmissibilityPolicy:
    return mdstats.CheckpointAdmissibilityPolicy(
        replay_enabled=False, replay_degradation_budget_ev_per_angstrom=None, **kwargs
    )


_REPLAY = mdstats.CheckpointAdmissibilityPolicy()


def _decide(candidates, *, outer_rmse: float | None = None):
    """The runtime order: select, evaluate outer only for a representative, judge."""

    representative = select_cv_fold_representative(
        candidates, selection_policy=_SELECTION, seed_material_digest=_SEED_DIGEST
    )
    outer = None
    if representative is not None:
        outer = target_metrics(outer_rmse, pred_digest="f" * 64)
    return representative, build_cv_fold_acceptance(
        run_plan=_RUN_PLAN,
        candidates=candidates,
        representative=representative,
        outer_metrics=outer,
        policy=_POLICY,
    )


def _assert_no_admissible(acceptance, reasons: set[str], candidates) -> None:
    assert acceptance.outcome == CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE
    assert acceptance.accepted is False
    assert acceptance.rejection_reasons == (CV_FOLD_NO_ADMISSIBLE_REASON,)
    assert set(acceptance.checkpoint_rejection_reasons) == reasons
    assert set(acceptance.candidate_record_digests) == {
        item.content_digest for item in candidates
    }
    # No candidate identity leaks into a representative-bearing field.
    for name in (
        "representative_candidate_identity",
        "representative_checkpoint_record_digest",
        "outer_metric_record_digest",
        "outer_metric_value",
        "replay_degradation_ev_per_angstrom",
    ):
        assert getattr(acceptance, name) is None, name
    serialized = json.dumps(acceptance.to_dict())
    for item in candidates:
        assert item.stable_candidate_identity not in serialized
    assert CvFoldAcceptance.from_dict(acceptance.to_dict()) == acceptance


# --- the acceptance matrix at the result boundary (rows A-H) ----------------


def test_case_a_and_b_admissible_representative_is_judged_on_the_outer_fold():
    policy = _no_replay()
    candidates = [_candidate(1, 0.010, policy=policy), _candidate(2, 0.050, policy=policy)]
    representative, accepted = _decide(candidates, outer_rmse=0.010)
    assert representative is candidates[0]
    assert accepted.outcome == CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
    assert accepted.accepted
    assert accepted.representative_checkpoint_record_digest == candidates[0].content_digest
    assert accepted.checkpoint_rejection_reasons == ("target_threshold_exceeded",)

    _representative, rejected = _decide(candidates, outer_rmse=0.040)
    assert rejected.outcome == CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
    assert not rejected.accepted
    assert rejected.rejection_reasons == (
        "outer_target_metric_above_configured_maximum",
    )


def test_case_c_all_candidates_fail_the_target_threshold():
    policy = _no_replay()
    candidates = [_candidate(1, 0.031, policy=policy), _candidate(2, 0.040, policy=policy)]
    representative, acceptance = _decide(candidates)
    assert representative is None
    _assert_no_admissible(acceptance, {"target_threshold_exceeded"}, candidates)


def test_case_d_all_candidates_fail_replay_retention():
    candidates = [
        _candidate(1, 0.010, policy=_REPLAY, replay_candidate=0.060),
        _candidate(2, 0.012, policy=_REPLAY, replay_candidate=0.070),
    ]
    representative, acceptance = _decide(candidates)
    assert representative is None
    _assert_no_admissible(acceptance, {"replay_retention_ceiling_exceeded"}, candidates)


def test_case_e_distinct_mandatory_reasons_are_all_preserved():
    candidates = [
        _candidate(1, 0.040, policy=_REPLAY, replay_candidate=0.021),
        _candidate(2, 0.010, policy=_REPLAY, replay_candidate=0.070),
    ]
    representative, acceptance = _decide(candidates)
    assert representative is None
    _assert_no_admissible(
        acceptance,
        {"target_threshold_exceeded", "replay_retention_ceiling_exceeded"},
        candidates,
    )


def test_case_f_all_candidates_fail_a_required_physical_gate():
    policy = _no_replay(required_physical_gates=("stress_finite",))
    candidates = [_candidate(1, 0.010, policy=policy), _candidate(2, 0.011, policy=policy)]
    representative, acceptance = _decide(candidates)
    assert representative is None
    _assert_no_admissible(acceptance, {"physical_gate_failed:stress_finite"}, candidates)


def test_case_g_zero_candidates_is_missing_evidence_not_a_verdict():
    with pytest.raises(PostSelectionError, match="no checkpoint candidates"):
        select_cv_fold_representative(
            [], selection_policy=_SELECTION, seed_material_digest=_SEED_DIGEST
        )
    with pytest.raises(PostSelectionError, match="no checkpoint candidates"):
        build_cv_fold_acceptance(
            run_plan=_RUN_PLAN,
            candidates=[],
            representative=None,
            outer_metrics=None,
            policy=_POLICY,
        )


def test_case_h_corrupt_or_inconsistent_candidate_evidence_fails_hard():
    policy = _no_replay()
    good = _candidate(1, 0.010, policy=policy)
    bad = _candidate(2, 0.040, policy=policy)

    # A candidate record whose admissibility disagrees with its reasons cannot
    # even be read back.
    tampered = {**bad.to_dict(), "admissible": True, "rejection_reasons": []}
    with pytest.raises(Exception, match="digest|disagrees"):
        mdstats.Eval2CheckpointRecord.from_dict(tampered)

    # An admissible candidate with no frozen representative is an impossible
    # state, not a rejection.
    with pytest.raises(PostSelectionError, match="must freeze a representative"):
        build_cv_fold_acceptance(
            run_plan=_RUN_PLAN,
            candidates=[good, bad],
            representative=None,
            outer_metrics=None,
            policy=_POLICY,
        )
    # Outer evidence without a representative is refused.
    with pytest.raises(PostSelectionError, match="cannot carry held-out outer"):
        build_cv_fold_acceptance(
            run_plan=_RUN_PLAN,
            candidates=[bad],
            representative=None,
            outer_metrics=target_metrics(0.010),
            policy=_POLICY,
        )
    # An inadmissible or foreign "representative" is never promoted.
    for representative, candidates in ((bad, [good, bad]), (good, [bad])):
        with pytest.raises(PostSelectionError, match="never promoted"):
            build_cv_fold_acceptance(
                run_plan=_RUN_PLAN,
                candidates=candidates,
                representative=representative,
                outer_metrics=target_metrics(0.010),
                policy=_POLICY,
            )
    # A representative that reached acceptance without outer evidence fails.
    with pytest.raises(PostSelectionError, match="no held-out outer evaluation"):
        build_cv_fold_acceptance(
            run_plan=_RUN_PLAN,
            candidates=[good],
            representative=good,
            outer_metrics=None,
            policy=_POLICY,
        )


# --- construction invariants: mixed states are refused, not normalized -----


def _no_admissible_payload() -> dict:
    policy = _no_replay()
    candidates = [_candidate(1, 0.040, policy=policy)]
    return _decide(candidates)[1].to_dict()


def _selected_payload() -> dict:
    policy = _no_replay()
    candidates = [_candidate(1, 0.010, policy=policy)]
    return _decide(candidates, outer_rmse=0.010)[1].to_dict()


@pytest.mark.parametrize(
    "mutation",
    [
        {"representative_candidate_identity": "epoch-1:" + "1" * 64},
        {"representative_checkpoint_record_digest": "1" * 64},
        {"outer_metric_record_digest": "1" * 64},
        {"outer_metric_value": 0.001},
        {"replay_degradation_ev_per_angstrom": 0.0},
        {"accepted": True, "rejection_reasons": []},
        {"rejection_reasons": ["outer_target_metric_above_configured_maximum"]},
        {"checkpoint_rejection_reasons": []},
        {"candidate_record_digests": []},
    ],
)
def test_no_admissible_record_refuses_any_mixed_state(mutation):
    payload = {**_no_admissible_payload(), **mutation, "content_digest": None}
    with pytest.raises(Exception):
        CvFoldAcceptance.from_dict(payload)


@pytest.mark.parametrize(
    "mutation",
    [
        {"representative_candidate_identity": None},
        {"representative_checkpoint_record_digest": None},
        {"outer_metric_record_digest": None},
        {"outer_metric_value": None},
        {"representative_checkpoint_record_digest": "1" * 64},
        {"candidate_record_digests": []},
        {"outcome": "best_rejected_checkpoint"},
    ],
)
def test_selected_record_refuses_missing_or_foreign_representative_evidence(mutation):
    payload = {**_selected_payload(), **mutation, "content_digest": None}
    with pytest.raises(Exception):
        CvFoldAcceptance.from_dict(payload)


def test_tampered_fold_verdict_fails_its_content_digest():
    payload = _no_admissible_payload()
    payload["checkpoint_rejection_reasons"] = ["replay_retention_ceiling_exceeded"]
    with pytest.raises(Exception, match="digest mismatch"):
        CvFoldAcceptance.from_dict(payload)


# --- persistence compatibility (8.6) ----------------------------------------


def _pre_repair_fold_payloads() -> list[dict]:
    fixture = Path(__file__).with_name("fixtures") / "p5_pre_repair_authorization_v2.json"
    acceptance = json.loads(fixture.read_text(encoding="utf-8"))["acceptance"]
    folds = [
        fold for seed in acceptance["seed_acceptances"] for fold in seed["fold_acceptances"]
    ]
    assert folds and all(fold["schema"] == CV_FOLD_ACCEPTANCE_SCHEMA_V1 for fold in folds)
    return folds


def test_pre_change_v1_fold_records_read_losslessly_and_are_not_rewritten():
    for payload in _pre_repair_fold_payloads():
        record = CvFoldAcceptance.from_dict(payload)
        assert record.outcome == CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
        assert record.serialization_schema == CV_FOLD_ACCEPTANCE_SCHEMA_V1
        assert record.candidate_record_digests == ()
        # Reading is not migration: the record re-serializes to the exact
        # pre-change bytes and digest.
        assert record.to_dict() == payload
    fixture = Path(__file__).with_name("fixtures") / "p5_pre_repair_authorization_v2.json"
    acceptance = json.loads(fixture.read_text(encoding="utf-8"))["acceptance"]
    assert CvCampaignAcceptance.from_dict(acceptance).to_dict() == acceptance


def test_v1_schema_cannot_express_the_new_outcome_by_relabeling():
    payload = _no_admissible_payload()
    for key in ("outcome", "candidate_record_digests", "checkpoint_rejection_reasons"):
        payload.pop(key)
    payload.update(schema=CV_FOLD_ACCEPTANCE_SCHEMA_V1, content_digest=None)
    with pytest.raises(Exception):
        CvFoldAcceptance.from_dict(payload)
    v2 = {**_pre_repair_fold_payloads()[0], "schema": CV_FOLD_ACCEPTANCE_SCHEMA}
    v2["content_digest"] = None
    # A v2 record must state its outcome and candidates; nothing is guessed.
    with pytest.raises(Exception):
        CvFoldAcceptance.from_dict(v2)


def test_new_records_use_the_current_schema():
    assert _no_admissible_payload()["schema"] == CV_FOLD_ACCEPTANCE_SCHEMA
    assert _selected_payload()["schema"] == CV_FOLD_ACCEPTANCE_SCHEMA


# --- property: no inadmissible promotion, for any candidate set -------------


_candidate_specs = st.lists(
    st.tuples(
        st.floats(min_value=0.001, max_value=0.060, allow_nan=False),
        st.floats(min_value=0.0, max_value=0.080, allow_nan=False),
    ),
    min_size=1,
    max_size=6,
)


@settings(max_examples=150, deadline=None)
@given(specs=_candidate_specs, outer=st.floats(min_value=0.0, max_value=0.05))
def test_property_outcome_is_determined_by_admissibility_alone(specs, outer):
    candidates = [
        _candidate(index, rmse, policy=_REPLAY, replay_candidate=replay)
        for index, (rmse, replay) in enumerate(specs)
    ]
    representative, acceptance = _decide(candidates, outer_rmse=outer)
    admissible = [item for item in candidates if item.admissible]
    if admissible:
        assert representative is not None and representative.admissible
        assert acceptance.outcome == CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
        assert acceptance.representative_checkpoint_record_digest in {
            item.content_digest for item in admissible
        }
    else:
        assert representative is None
        _assert_no_admissible(
            acceptance,
            {reason for item in candidates for reason in item.rejection_reasons},
            candidates,
        )


# --- the scientific boundary is unchanged (O11 / 8.7) ------------------------


def test_mandatory_admissibility_boundaries_are_unchanged():
    policy = mdstats.CheckpointAdmissibilityPolicy()
    assert policy.maximum_target_force_rmse_ev_per_angstrom == 0.030
    assert policy.replay_enabled is True
    assert policy.replay_degradation_budget_ev_per_angstrom == 0.030
    assert policy.replay_label_requirement == "true_dft"
    above = math.nextafter(0.030, math.inf)

    def reasons(target: float, replay: float, label: str = "true_dft"):
        return policy.failure_reasons(
            target_force_rmse_ev_per_angstrom=target,
            replay_degradation_ev_per_angstrom=replay,
            replay_label_mode=label,
        )

    assert reasons(0.030, 0.030) == ()
    assert reasons(above, 0.030) == ("target_threshold_exceeded",)
    assert reasons(0.030, above) == ("replay_retention_ceiling_exceeded",)
    assert "replay_true_dft_evidence_missing" in reasons(0.010, 0.010, "foundation")
    # Replay remains a constraint with no ranking credit: the selector never
    # sees a replay-aware key.
    assert "replay" not in json.dumps(_SELECTION.to_dict()).lower()


# ===========================================================================
# Real-owner runtime: EVAL2 -> fold verdict -> size -> campaign (8.2-8.5, I)
# ===========================================================================

import tests._mlff_post_selection_fixture as fx  # noqa: E402
import tests.test_mlff_target_size_multi_size_integration as multi  # noqa: E402
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d  # noqa: E402

from mdstats.training_data import _campaign_cli_core as cli  # noqa: E402
from mdstats.training_data import campaign_post_selection_runtime as runtime  # noqa: E402
from mdstats.training_data.campaign_post_selection_runtime import (  # noqa: E402
    FOLD_ACCEPTANCE_FILENAME,
    build_post_selection_contexts,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
)
from mdstats.training_data.post_selection_cv_acceptance import (  # noqa: E402
    PostSelectionCvRejectedError,
)
from mdstats.training_data.post_selection_cv_plan import (  # noqa: E402
    build_cv_fold_run_plan,
)
from mdstats.training_data.post_selection_execution import (  # noqa: E402
    DATASET_ROLE_OUTER_EVALUATION,
)

#: Admissible under the mandatory 0.030 eV/A target gate and inside the
#: fixture's CV acceptance maximum.
_GOOD_OFFSET = 1.0e-4
#: Every checkpoint of a run at this per-component force error fails the
#: mandatory target gate, so that fold has no admissible representative.
_INADMISSIBLE_OFFSET = 0.05
#: The stakeholder run had five required folds.  Five outer folds need at least
#: five independent split-exclusion components per frozen size, which the
#: fixture's size-8 selection (four components) cannot hold, so these suites
#: extend only the fixture's size ladder and freeze sizes 16 and 32 instead.
_FOLD_COUNT = 5
_FIVE_FOLD_SIZES = (16, 32)


class _PlannedOffsetHarness(fx.PostSelectionHarness):
    """The bounded MACE seam, with force error chosen from the run's own plan.

    The real owner still enumerates sizes, plans folds, trains, assesses every
    checkpoint and reaches every verdict; only the substituted arithmetic
    depends on which ``(size, fold)`` the owner handed this run.  One instance
    is reused across invocations so a resumed run that is *not* retrained is
    still recognized.
    """

    def __init__(self, offset_for_plan) -> None:
        super().__init__()
        self._offset_for_plan = offset_for_plan
        self.plans: dict[str, object] = {}

    def train(self, request):
        self.plans[request.run_plan.run_identity] = request.run_plan
        return super().train(request)

    def _offset_for(self, provider) -> float:
        identity = getattr(provider, "checkpoint_identity", None)
        locator = "" if identity is None else str(
            getattr(identity, "checkpoint_locator", "")
        )
        for run_identity, plan in self.plans.items():
            if run_identity in locator:
                return float(self._offset_for_plan(plan))
        raise AssertionError(f"no executed run owns {locator!r}")


def _count_outer_evaluations(monkeypatch, *, fail_for=None) -> dict[str, int]:
    """Instrument the runtime owner's real dataset-evaluation seam."""

    real = runtime.evaluate_post_selection_dataset
    calls: dict[str, int] = {}

    def observed(**kwargs):
        if kwargs["dataset_role"] == DATASET_ROLE_OUTER_EVALUATION:
            plan = kwargs["run_plan"]
            calls[plan.run_identity] = calls.get(plan.run_identity, 0) + 1
            if fail_for is not None and fail_for(plan):
                raise RuntimeError("injected held-out outer evaluation failure")
        return real(**kwargs)

    monkeypatch.setattr(runtime, "evaluate_post_selection_dataset", observed)
    return calls


def _main_cross_validate(config: Path, harness, monkeypatch) -> int:
    """Invoke the operator entry point, attaching the bounded seams to its args."""

    parser = cli.build_parser()
    parse = parser.parse_args

    def parse_with_seams(argv=None, namespace=None):
        args = parse(argv, namespace)
        args._external_post_selection_trainer = harness.train
        args._external_inference_evaluator = harness.evaluate
        return args

    monkeypatch.setattr(parser, "parse_args", parse_with_seams)
    monkeypatch.setattr(cli, "build_parser", lambda: parser)
    return cli.main(["--config", str(config), "cross-validate"])


def _fold_verdicts(config: Path):
    """Every size's persisted fold verdicts, read through the current owners."""

    from mdstats.training_data.eval2 import Eval2CheckpointRecord

    cfg, paths, store = fx.load_context(config)
    try:
        sizes = []
        for context in build_post_selection_contexts(cfg, paths, store):
            plan = resolve_current_cv_plan(context)
            folds = {}
            for seed, fold_index in () if plan is None else plan.required_run_matrix:
                run_plan = build_cv_fold_run_plan(
                    plan,
                    fold_index=fold_index,
                    optimizer_seed=seed,
                    planned_epochs=context.cv_policy.cv_max_num_epochs,
                )
                path = context.run_root(run_plan.run_identity) / FOLD_ACCEPTANCE_FILENAME
                if not path.is_file():
                    folds[fold_index] = None
                    continue
                verdict = CvFoldAcceptance.from_dict(json.loads(path.read_text()))
                # The candidate evidence a verdict binds is durable and real.
                records = [
                    context.evidence_store.get(item, Eval2CheckpointRecord.from_dict)
                    for item in verdict.candidate_record_digests
                ]
                assert records
                if verdict.outcome == CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE:
                    assert not any(record.admissible for record in records)
                folds[fold_index] = (run_plan.run_identity, verdict)
            sizes.append(
                SimpleNamespace(
                    n_selected=context.selected.n_selected,
                    binding=context.selected.binding.content_digest,
                    folds=folds,
                    acceptance=resolve_current_cv_acceptance(context),
                )
            )
        return sizes
    finally:
        store.close()


@pytest.mark.slow
def test_all_inadmissible_fold_is_a_completed_rejection_and_siblings_complete(
    tmp_path: Path, monkeypatch, capsys
):
    """8.2 + 8.3 + O9: one early all-inadmissible fold among every required fold."""

    config = _five_fold_campaign(tmp_path, _FIVE_FOLD_SIZES[:1])
    capsys.readouterr()
    rejected_fold = 1
    harness = _PlannedOffsetHarness(
        lambda plan: _INADMISSIBLE_OFFSET if plan.fold_index == rejected_fold else _GOOD_OFFSET
    )
    outer_calls = _count_outer_evaluations(monkeypatch)

    assert _main_cross_validate(config, harness, monkeypatch) == 2
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out + captured.err
    assert "cross-validation rejected the training method" in captured.err
    assert "no admissible checkpoint (methodological rejection)" in captured.out
    assert "target_threshold_exceeded" in captured.out

    (size,) = _fold_verdicts(config)
    assert sorted(size.folds) == list(range(_FOLD_COUNT))
    for fold_index, entry in size.folds.items():
        assert entry is not None, f"fold {fold_index} has no persisted verdict"
        run_identity, verdict = entry
        if fold_index == rejected_fold:
            assert verdict.outcome == CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE
            assert verdict.checkpoint_rejection_reasons == ("target_threshold_exceeded",)
            assert outer_calls.get(run_identity, 0) == 0
        else:
            assert verdict.outcome == CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
            assert verdict.accepted
            assert outer_calls[run_identity] == 1
    assert len(harness.runs) == _FOLD_COUNT

    acceptance = size.acceptance
    assert acceptance is not None and not acceptance.accepted
    (seed_record,) = acceptance.seed_acceptances
    assert seed_record.rejection_reasons == (
        f"fold_{rejected_fold}_{CV_FOLD_NO_ADMISSIBLE_REASON}",
    )
    assert len(seed_record.fold_acceptances) == _FOLD_COUNT


@pytest.mark.slow
def test_outer_evaluation_failure_after_selection_stays_a_hard_failure(
    tmp_path: Path, monkeypatch
):
    """Row I: a crash in outer evaluation is never turned into a verdict."""

    config, _workspace = fx.build_selected_campaign(tmp_path)
    harness = _PlannedOffsetHarness(lambda plan: _GOOD_OFFSET)
    outer_calls = _count_outer_evaluations(
        monkeypatch, fail_for=lambda plan: plan.fold_index == 0
    )
    with pytest.raises(RuntimeError, match="injected held-out outer evaluation"):
        fx.run_cross_validate(config, harness)
    assert sum(outer_calls.values()) == 1
    (size,) = _fold_verdicts(config)
    assert all(entry is None for entry in size.folds.values())
    assert size.acceptance is None


def _five_fold_campaign(tmp_path: Path, sizes, *, acceptance_maximum: str = "0.5") -> Path:
    """A prepared campaign with ``sizes`` frozen by explicit operator selection."""

    config_text = (
        fx.fixture_config_text()
        .replace("target_size_power_max = 4", "target_size_power_max = 5")
        .replace("acceptance_maximum = 0.5", f"acceptance_maximum = {acceptance_maximum}")
        .replace("fold_count = 2", f"fold_count = {_FOLD_COUNT}")
    )
    from unittest.mock import patch

    with patch.object(p4d, "_CONFIG", config_text):
        config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    for horizon, size in enumerate(sizes, start=2):
        assert multi._select(config, str(size), "--horizon", str(horizon)) == 0
    return config


def _legacy_selection_that_aborts(monkeypatch) -> None:
    """Reproduce the pre-repair executable's abort at no-admissible selection."""

    real = runtime.select_cv_fold_representative

    def legacy(candidates, **kwargs):
        chosen = real(candidates, **kwargs)
        if chosen is None:
            raise PostSelectionError(
                "No CV fold checkpoint passed mandatory admissibility; rejection "
                "reasons: ['target_threshold_exceeded']. An inadmissible checkpoint "
                "is never promoted to a fold representative."
            )
        return chosen

    monkeypatch.setattr(runtime, "select_cv_fold_representative", legacy)


@pytest.mark.slow
def test_stakeholder_shaped_recovery_reuses_train2_and_completes_every_size(
    tmp_path: Path, monkeypatch
):
    """8.5: all TRAIN2 complete, EVAL2 aborted at slot 0 by the old executable."""

    config = _five_fold_campaign(tmp_path, _FIVE_FOLD_SIZES, acceptance_maximum="0.005")
    cfg, paths, store = fx.load_context(config)
    try:
        contexts = build_post_selection_contexts(cfg, paths, store, admit=True)
        first_binding = contexts[0].selected.binding.content_digest
    finally:
        store.close()
    harness = _PlannedOffsetHarness(
        lambda plan: _INADMISSIBLE_OFFSET
        if plan.selected_binding_digest == first_binding and plan.fold_index == 0
        else _GOOD_OFFSET
    )

    # The legacy invocation: TRAIN2 for the first size completes, EVAL2 stops at
    # slot 0, and neither a fold verdict nor the second size exists.
    with monkeypatch.context() as legacy:
        _legacy_selection_that_aborts(legacy)
        with pytest.raises(PostSelectionError, match="No CV fold checkpoint passed"):
            fx.run_cross_validate(config, harness)
    trained_by_legacy = list(harness.runs)
    assert len(trained_by_legacy) == _FOLD_COUNT
    assert {harness.plans[run].selected_binding_digest for run in trained_by_legacy} == {
        first_binding
    }
    first, second = _fold_verdicts(config)
    assert len(first.folds) == _FOLD_COUNT
    assert all(entry is None for entry in first.folds.values())
    assert first.acceptance is None
    assert second.folds == {} and second.acceptance is None

    # The repaired invocation, same workspace.
    outer_calls = _count_outer_evaluations(monkeypatch)
    with pytest.raises(PostSelectionCvRejectedError, match="cross-validation rejected"):
        fx.run_cross_validate(config, harness)

    retrained = harness.runs[len(trained_by_legacy):]
    assert not set(retrained) & set(trained_by_legacy), "completed TRAIN2 was retrained"
    assert {harness.plans[run].selected_binding_digest for run in retrained} == {
        second.binding
    }
    assert len(retrained) == _FOLD_COUNT

    first, second = _fold_verdicts(config)
    for size in (first, second):
        assert len(size.folds) == _FOLD_COUNT
        assert all(entry is not None for entry in size.folds.values()), size.n_selected
        assert size.acceptance is not None
    stuck_run, stuck = first.folds[0]
    assert stuck.outcome == CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE
    assert outer_calls.get(stuck_run, 0) == 0
    assert all(
        verdict.outcome == CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
        for fold_index, (_run, verdict) in first.folds.items()
        if fold_index != 0
    )
    assert [first.acceptance.accepted, second.acceptance.accepted] == [False, True]

    production = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionError, match="not admitted"):
        fx.run_train_production(config, production)
    assert production.runs == []


# --- restart reuse re-authenticates the candidate evidence a verdict binds ---


def _completed_rejected_campaign(tmp_path: Path):
    """Two required folds persisted: fold 0 no-admissible, fold 1 selected."""

    config, _workspace = fx.build_selected_campaign(tmp_path)
    harness = _PlannedOffsetHarness(
        lambda plan: _INADMISSIBLE_OFFSET if plan.fold_index == 0 else _GOOD_OFFSET
    )
    with pytest.raises(PostSelectionCvRejectedError):
        fx.run_cross_validate(config, harness)
    (size,) = _fold_verdicts(config)
    return config, harness, size


def _object_path(config: Path, content_digest: str) -> Path:
    cfg, paths, store = fx.load_context(config)
    try:
        (context,) = build_post_selection_contexts(cfg, paths, store)
        return context.evidence_store.object_path(content_digest)
    finally:
        store.close()


def _rewrite_verdict(config: Path, run_identity: str, verdict: CvFoldAcceptance) -> None:
    cfg, paths, store = fx.load_context(config)
    try:
        (context,) = build_post_selection_contexts(cfg, paths, store)
        path = context.run_root(run_identity) / FOLD_ACCEPTANCE_FILENAME
    finally:
        store.close()
    path.write_text(json.dumps(verdict.to_dict(), sort_keys=True), encoding="utf-8")


def _corrupt_object(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["full_evaluation_rank"] = int(payload.get("full_evaluation_rank") or 0) + 7
    path.write_text(json.dumps(payload), encoding="utf-8")


def _tamper_candidate_admissible(config: Path, run_identity: str, verdict) -> None:
    """Swap a bound candidate for an admissible one and re-bind the verdict to it."""

    import dataclasses

    from mdstats.training_data.eval2 import Eval2CheckpointRecord

    digests = list(verdict.candidate_record_digests)
    assert len(digests) >= 2, "the reason union must survive the swap"
    path = _object_path(config, digests[0])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(admissible=True, rejection_reasons=[], content_digest=None)
    forged = Eval2CheckpointRecord.from_dict(payload)
    forged_path = _object_path(config, forged.content_digest)
    forged_path.parent.mkdir(parents=True, exist_ok=True)
    forged_path.write_text(json.dumps(forged.to_dict()), encoding="utf-8")
    _rewrite_verdict(
        config,
        run_identity,
        dataclasses.replace(
            verdict, candidate_record_digests=(forged.content_digest, *digests[1:])
        ),
    )


def _tamper_reason_union(config: Path, run_identity: str, verdict) -> None:
    import dataclasses

    _rewrite_verdict(
        config,
        run_identity,
        dataclasses.replace(
            verdict,
            checkpoint_rejection_reasons=(
                *verdict.checkpoint_rejection_reasons,
                "replay_retention_ceiling_exceeded",
            ),
        ),
    )


_NOT_REPRODUCED = "not reproduced by the checkpoint candidate evidence"


@pytest.mark.slow
@pytest.mark.parametrize(
    "fold_index, tamper, match",
    [
        (0, lambda c, run, v: _object_path(c, v.candidate_record_digests[0]).unlink(), "missing"),
        (0, lambda c, run, v: _corrupt_object(_object_path(c, v.candidate_record_digests[0])), "digest"),
        (0, _tamper_candidate_admissible, _NOT_REPRODUCED),
        (0, _tamper_reason_union, _NOT_REPRODUCED),
        (
            1,
            lambda c, run, v: _object_path(c, v.representative_checkpoint_record_digest).unlink(),
            "missing",
        ),
        (
            1,
            lambda c, run, v: _corrupt_object(
                _object_path(c, v.representative_checkpoint_record_digest)
            ),
            "digest",
        ),
    ],
    ids=[
        "no-admissible-candidate-deleted",
        "no-admissible-candidate-corrupt",
        "no-admissible-candidate-forged-admissible",
        "no-admissible-reason-union-tampered",
        "selected-representative-deleted",
        "selected-representative-corrupt",
    ],
)
def test_restart_refuses_a_verdict_whose_candidate_evidence_no_longer_proves_it(
    tmp_path: Path, monkeypatch, fold_index, tamper, match
):
    """R1: a persisted v2 verdict is reused only on authentic candidate evidence."""

    config, harness, size = _completed_rejected_campaign(tmp_path)
    run_identity, verdict = size.folds[fold_index]
    expected = (
        CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE
        if fold_index == 0
        else CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
    )
    assert verdict.outcome == expected
    tamper(config, run_identity, verdict)
    trained, evaluated = list(harness.runs), list(harness.evaluations)
    outer_calls = _count_outer_evaluations(monkeypatch)

    with pytest.raises((PostSelectionError, ValueError), match=match) as excinfo:
        fx.run_cross_validate(config, harness)
    # A hard failure, never translated into (or hidden behind) a rejection.
    assert not isinstance(excinfo.value, PostSelectionCvRejectedError)
    assert harness.runs == trained and harness.evaluations == evaluated
    assert outer_calls == {}


@pytest.mark.slow
def test_restart_reuses_authentic_negative_and_v1_verdicts_without_retraining(
    tmp_path: Path, monkeypatch
):
    """R1: authentic v2 negative folds and v1 selected folds are reused as stored."""

    config, harness, size = _completed_rejected_campaign(tmp_path)
    (_negative_run, negative), (selected_run, selected) = size.folds[0], size.folds[1]
    assert negative.outcome == CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE
    # A pre-repair representative-bearing record for the same run plan: v1
    # binds no candidate set, and none is guessed for it.
    v1 = selected.to_dict()
    for key in ("outcome", "candidate_record_digests", "checkpoint_rejection_reasons"):
        v1.pop(key)
    v1.update(schema=CV_FOLD_ACCEPTANCE_SCHEMA_V1, content_digest=None)
    v1 = CvFoldAcceptance.from_dict(v1).to_dict()
    cfg, paths, store = fx.load_context(config)
    try:
        (context,) = build_post_selection_contexts(cfg, paths, store)
        selected_path = context.run_root(selected_run) / FOLD_ACCEPTANCE_FILENAME
    finally:
        store.close()
    selected_path.write_text(json.dumps(v1, sort_keys=True), encoding="utf-8")
    v1_bytes = selected_path.read_bytes()
    trained, evaluated = list(harness.runs), list(harness.evaluations)
    outer_calls = _count_outer_evaluations(monkeypatch)
    real_reuse = runtime._completed_fold_acceptance
    reused = []

    def observed(context, run_plan):
        result = real_reuse(context, run_plan)
        reused.append(result)
        return result

    monkeypatch.setattr(runtime, "_completed_fold_acceptance", observed)

    with pytest.raises(PostSelectionCvRejectedError):
        fx.run_cross_validate(config, harness)
    assert harness.runs == trained, "a completed fold was retrained"
    assert harness.evaluations == evaluated and outer_calls == {}
    assert [item.outcome for item in reused] == [
        CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE,
        CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED,
    ]
    assert reused[0] == negative
    assert reused[1].serialization_schema == CV_FOLD_ACCEPTANCE_SCHEMA_V1
    assert reused[1].candidate_record_digests == ()
    assert reused[1].to_dict() == v1
    assert selected_path.read_bytes() == v1_bytes


@pytest.mark.slow
def test_final_production_without_an_admissible_checkpoint_still_fails_hard(
    tmp_path: Path,
):
    """F9: success-shaped production evidence never gains a negative state."""

    from mdstats.training_data.campaign_post_selection_runtime import (
        RUN_EVIDENCE_FILENAME,
        resolve_current_final_production_completion,
    )

    config, _workspace = fx.build_selected_campaign(tmp_path)
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0
    production = fx.PostSelectionHarness(force_offset=_INADMISSIBLE_OFFSET)
    with pytest.raises(PostSelectionError, match="passed mandatory admissibility"):
        fx.run_train_production(config, production)
    assert production.runs
    cfg, paths, store = fx.load_context(config)
    try:
        (context,) = build_post_selection_contexts(cfg, paths, store)
        assert resolve_current_final_production_completion(context) is None
        for run_identity in production.runs:
            assert not (context.run_root(run_identity) / RUN_EVIDENCE_FILENAME).exists()
    finally:
        store.close()
