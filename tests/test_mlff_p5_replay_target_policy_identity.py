"""Replay-retention / target-admissibility policy, identity and currentness owners.

These tests exercise the real policy, configuration, identity, selection,
measurement and completion-proof owners of the reviewed D3/D4 contract
(de360579): catastrophic replay hard limit versus diagnostic-only warning, the
foundation 75/75/50 role defaults and the narrow ``p5_target_replay_v2``
migration, the training-only method and pre-fit training-trajectory identity,
assessment-independent measurement identity, the narrow assessment-position
policy projections, strict D2.DEF.059A/059B ordering, outcome-discriminated
final-seed assessment, and the training-only completion proof.
"""

from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.post_selection_identity import (
    P5_CHECKPOINT_POLICY_GENERATION,
    cv_assessment_position_policy_digest,
    final_publication_policy_digest,
    final_seed_assessment_policy_digest,
    historical_method_training_projection,
    post_selection_checkpoint_admissibility,
    resolve_cv_validation_policy_identity,
    resolve_final_production_policy_identity,
    resolve_p5_checkpoint_policy_configuration,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)
from mdstats.training_data.train2_policy import (
    CHECKPOINT_ADMISSIBILITY_POLICY_SCHEMA_V1,
    REPLAY_CATASTROPHIC_FORGETTING_REASON,
    REPLAY_WARNING_CODE,
    CheckpointAdmissibilityPolicy,
    ReplayWarningDiagnosticPolicy,
)
from tests.test_mlff_target_size_p5_r10_guards import (
    _foundation_inspection,
    _policy_config,
)

FOUNDATION_MODES = ("naive_fine_tuning", "multihead_replay")


def _above(value: float) -> float:
    return math.nextafter(value, math.inf)


def _config(mode: str, *, foundation: Path | None, **tables) -> dict:
    replay = mode == "multihead_replay"
    config = _policy_config(
        mode, foundation=foundation if mode != "scratch" else None, replay=replay
    )
    if replay:
        config["foundation"] = {"family": "mace_mpa_0", "head": "default"}
    for name, value in tables.items():
        config[name] = copy.deepcopy(value)
    return config


@pytest.fixture()
def foundation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "foundation.model"
    path.write_bytes(b"bounded-foundation")
    monkeypatch.setattr(
        "mdstats.training_data.foundation.inspect_mace_foundation",
        lambda item: _foundation_inspection(Path(item)),
    )
    return path


def _resolved(config: dict):
    policies = resolve_post_selection_method_policies(config)
    method = resolve_post_selection_method_identity(config, policies=policies)
    cv = resolve_cv_validation_policy_identity(config, training_mode=policies.training_mode)
    production = resolve_final_production_policy_identity(
        config, training_mode=policies.training_mode
    )
    return policies, method, cv, production


# ---------------------------------------------------------------------------
# D2.DEF.057: catastrophic hard limit versus diagnostic warning
# ---------------------------------------------------------------------------


def _hard(**kwargs) -> CheckpointAdmissibilityPolicy:
    return CheckpointAdmissibilityPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.050,
        replay_degradation_hard_limit_ev_per_angstrom=0.100,
        **kwargs,
    )


@pytest.mark.parametrize(
    "degradation, warns, rejects",
    [
        (0.050, False, False),
        (_above(0.050), True, False),
        (0.100, True, False),
        (_above(0.100), True, True),
        (-0.020, False, False),
    ],
)
def test_replay_boundaries_are_exact_strict_binary64(degradation, warns, rejects):
    hard = _hard()
    warning = ReplayWarningDiagnosticPolicy(warning_threshold_ev_per_angstrom=0.050)
    reasons = hard.failure_reasons(
        target_force_rmse_ev_per_angstrom=0.010,
        replay_degradation_ev_per_angstrom=degradation,
        replay_label_mode="true_dft",
    )
    assert (REPLAY_CATASTROPHIC_FORGETTING_REASON in reasons) is rejects
    assert (warning.diagnostic_warnings(degradation) == (REPLAY_WARNING_CODE,)) is warns
    # A warning never becomes a hard reason.
    assert REPLAY_WARNING_CODE not in reasons


def test_missing_or_nonfinite_true_dft_replay_evidence_is_a_hard_failure():
    hard = _hard()
    assert "replay_degradation_missing" in hard.failure_reasons(
        target_force_rmse_ev_per_angstrom=0.01,
        replay_degradation_ev_per_angstrom=None,
        replay_label_mode="true_dft",
    )
    assert "replay_true_dft_evidence_missing" in hard.failure_reasons(
        target_force_rmse_ev_per_angstrom=0.01,
        replay_degradation_ev_per_angstrom=0.0,
        replay_label_mode="foundation_pseudolabel",
    )
    assert "replay_metric_nonfinite" in hard.failure_reasons(
        target_force_rmse_ev_per_angstrom=0.01,
        replay_degradation_ev_per_angstrom=math.nan,
        replay_label_mode="true_dft",
    )
    assert ReplayWarningDiagnosticPolicy().diagnostic_warnings(math.nan) == ()


def test_warning_threshold_is_not_a_hard_policy_parent():
    hard = _hard()
    payload = hard.to_dict()
    assert "warning" not in json.dumps(payload)
    assert ReplayWarningDiagnosticPolicy(0.040).policy_digest != (
        ReplayWarningDiagnosticPolicy(0.050).policy_digest
    )


def test_historical_v1_admissibility_payload_stays_readable_byte_identical():
    legacy_payload = {
        "schema": CHECKPOINT_ADMISSIBILITY_POLICY_SCHEMA_V1,
        "maximum_target_force_rmse_ev_per_angstrom": 0.030,
        "replay_enabled": True,
        "replay_degradation_budget_ev_per_angstrom": 0.030,
        "replay_label_requirement": "true_dft",
        "require_finite_metrics": True,
        "required_physical_gates": [],
    }
    legacy_payload["policy_digest"] = digest(legacy_payload)
    restored = CheckpointAdmissibilityPolicy.from_dict(legacy_payload)
    assert restored.to_dict() == legacy_payload
    assert restored.is_historical
    assert "replay_retention_ceiling_exceeded" in restored.failure_reasons(
        target_force_rmse_ev_per_angstrom=0.01,
        replay_degradation_ev_per_angstrom=0.031,
        replay_label_mode="true_dft",
    )


# ---------------------------------------------------------------------------
# Role target defaults and the p5_target_replay_v2 migration table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", FOUNDATION_MODES)
def test_foundation_defaults_resolve_75_75_50_and_replay_50_100(mode, foundation):
    policies, _method, cv, production = _resolved(_config(mode, foundation=foundation))
    assert cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.075
    assert cv.acceptance_maximum == 0.075
    assert production.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.050
    configuration = policies.checkpoint_policy_configuration
    assert configuration.replay_warning_ev_per_angstrom == 0.050
    assert configuration.replay_hard_limit_ev_per_angstrom == 0.100


@pytest.mark.parametrize("mode", FOUNDATION_MODES)
def test_role_boundaries_75_and_50_are_inclusive_and_60_is_discriminating(mode, foundation):
    policies, _method, cv, production = _resolved(_config(mode, foundation=foundation))
    cv_hard = post_selection_checkpoint_admissibility(policies, cv)
    production_hard = post_selection_checkpoint_admissibility(policies, production)

    def target_reasons(policy, value):
        return [
            reason
            for reason in policy.failure_reasons(
                target_force_rmse_ev_per_angstrom=value,
                replay_degradation_ev_per_angstrom=0.0,
                replay_label_mode="true_dft",
            )
            if reason.startswith("target_")
        ]

    assert target_reasons(cv_hard, 0.075) == []
    assert target_reasons(cv_hard, _above(0.075)) == ["target_threshold_exceeded"]
    assert target_reasons(production_hard, 0.050) == []
    assert target_reasons(production_hard, _above(0.050)) == ["target_threshold_exceeded"]
    assert target_reasons(cv_hard, 0.060) == []
    assert target_reasons(production_hard, 0.060) == ["target_threshold_exceeded"]


def test_scratch_keeps_0030_and_rejects_the_foundation_cv_field():
    policies, _method, cv, production = _resolved(_config("scratch", foundation=None))
    assert cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.030
    assert cv.acceptance_maximum == 0.030
    assert production.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.030
    legacy = _config(
        "scratch", foundation=None, acceptance={"maximum_target_force_rmse_ev_per_angstrom": 0.030}
    )
    assert _resolved(legacy)[3].checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.030
    bad = _config(
        "scratch",
        foundation=None,
        post_selection={"cv": {"checkpoint_maximum_target_force_rmse_ev_per_angstrom": 0.05}},
    )
    with pytest.raises(PostSelectionError, match="foundation adaptation"):
        resolve_p5_checkpoint_policy_configuration(bad, training_mode="scratch")


@pytest.mark.parametrize("mode", FOUNDATION_MODES)
def test_unmarked_historical_generated_defaults_migrate(mode, foundation, capsys):
    config = _config(
        mode,
        foundation=foundation,
        acceptance={
            "maximum_target_force_rmse_ev_per_angstrom": 0.030,
            "allowed_replay_degradation_mev_per_a": 30.0,
        },
        post_selection={
            "cv": {
                "checkpoint_maximum_target_force_rmse_ev_per_angstrom": 0.045,
                "acceptance_maximum": 0.045,
            }
        },
    )
    policies, _method, cv, production = _resolved(config)
    assert (cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom, cv.acceptance_maximum) == (
        0.075,
        0.075,
    )
    assert production.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.050
    configuration = policies.checkpoint_policy_configuration
    assert (configuration.replay_warning_ev_per_angstrom, configuration.replay_hard_limit_ev_per_angstrom) == (0.050, 0.100)
    assert len(configuration.migration_notices) == 4


@pytest.mark.parametrize("mode", FOUNDATION_MODES)
def test_marked_explicit_historical_values_are_intentional_overrides(mode, foundation):
    config = _config(
        mode,
        foundation=foundation,
        acceptance={
            "post_selection_checkpoint_policy_generation": P5_CHECKPOINT_POLICY_GENERATION,
            "maximum_target_force_rmse_ev_per_angstrom": 0.030,
        },
        post_selection={
            "cv": {
                "checkpoint_maximum_target_force_rmse_ev_per_angstrom": 0.045,
                "acceptance_maximum": 0.045,
            }
        },
    )
    _policies, _method, cv, production = _resolved(config)
    assert (cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom, cv.acceptance_maximum) == (
        0.045,
        0.045,
    )
    assert production.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.030


@pytest.mark.parametrize("mode", FOUNDATION_MODES)
def test_non_default_legacy_values_are_preserved_and_alt_metric_is_not_migrated(mode, foundation):
    config = _config(
        mode,
        foundation=foundation,
        acceptance={"maximum_target_force_rmse_ev_per_angstrom": 0.041},
        post_selection={
            "cv": {
                "checkpoint_maximum_target_force_rmse_ev_per_angstrom": 0.061,
                "acceptance_metric": "energy_mae_ev_per_atom",
            }
        },
    )
    _policies, _method, cv, production = _resolved(config)
    assert cv.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.061
    assert production.checkpoint_maximum_target_force_rmse_ev_per_angstrom == 0.041
    # The alternative metric keeps its accepted pre-amendment resolution.
    assert cv.acceptance_maximum == 0.045
    explicit = _config(
        mode,
        foundation=foundation,
        post_selection={
            "cv": {"acceptance_metric": "energy_mae_ev_per_atom", "acceptance_maximum": 0.045}
        },
    )
    assert _resolved(explicit)[2].acceptance_maximum == 0.045


@pytest.mark.parametrize(
    "acceptance, match",
    [
        ({"allowed_replay_degradation_mev_per_a": 45.0}, "custom historical"),
        ({"replay_degradation_warning_mev_per_a": 50.0}, "current checkpoint-policy generation"),
        (
            {
                "allowed_replay_degradation_mev_per_a": 30.0,
                "replay_degradation_hard_limit_mev_per_a": 100.0,
            },
            "current checkpoint-policy generation",
        ),
        (
            {
                "post_selection_checkpoint_policy_generation": P5_CHECKPOINT_POLICY_GENERATION,
                "allowed_replay_degradation_mev_per_a": 30.0,
            },
            "retired one-number",
        ),
        (
            {
                "post_selection_checkpoint_policy_generation": P5_CHECKPOINT_POLICY_GENERATION,
                "replay_degradation_warning_mev_per_a": 100.0,
                "replay_degradation_hard_limit_mev_per_a": 100.0,
            },
            "strictly below",
        ),
        ({"post_selection_checkpoint_policy_generation": "p5_target_replay_v9"}, "must be"),
    ],
)
def test_ambiguous_or_mixed_replay_generations_fail_closed(acceptance, match, foundation):
    config = _config("multihead_replay", foundation=foundation, acceptance=acceptance)
    with pytest.raises(PostSelectionError, match=match):
        resolve_p5_checkpoint_policy_configuration(config, training_mode="multihead_replay")


@pytest.mark.parametrize("value", [True, "50", math.nan, math.inf, 0.0, -1.0])
def test_threshold_type_and_domain_validation(value, foundation):
    config = _config(
        "multihead_replay",
        foundation=foundation,
        acceptance={
            "post_selection_checkpoint_policy_generation": P5_CHECKPOINT_POLICY_GENERATION,
            "replay_degradation_warning_mev_per_a": value,
        },
    )
    with pytest.raises((TrainingDataInputError, PostSelectionError)):
        resolve_p5_checkpoint_policy_configuration(config, training_mode="multihead_replay")
    target = _config(
        "multihead_replay",
        foundation=foundation,
        acceptance={"maximum_target_force_rmse_ev_per_angstrom": value},
    )
    with pytest.raises((TrainingDataInputError, PostSelectionError)):
        resolve_p5_checkpoint_policy_configuration(target, training_mode="multihead_replay")


def test_omitted_and_explicit_current_defaults_have_identical_identities(foundation):
    omitted = _config(
        "multihead_replay",
        foundation=foundation,
        acceptance={"post_selection_checkpoint_policy_generation": P5_CHECKPOINT_POLICY_GENERATION},
    )
    explicit = _config(
        "multihead_replay",
        foundation=foundation,
        acceptance={
            "post_selection_checkpoint_policy_generation": P5_CHECKPOINT_POLICY_GENERATION,
            "maximum_target_force_rmse_ev_per_angstrom": 0.050,
            "replay_degradation_warning_mev_per_a": 50.0,
            "replay_degradation_hard_limit_mev_per_a": 100.0,
        },
        post_selection={
            "cv": {
                "checkpoint_maximum_target_force_rmse_ev_per_angstrom": 0.075,
                "acceptance_maximum": 0.075,
            }
        },
    )
    left, right = _resolved(omitted), _resolved(explicit)
    assert left[1].content_digest == right[1].content_digest
    assert left[2].content_digest == right[2].content_digest
    assert left[3].content_digest == right[3].content_digest
    assert post_selection_checkpoint_admissibility(left[0], left[3]).policy_digest == (
        post_selection_checkpoint_admissibility(right[0], right[3]).policy_digest
    )
    assert left[0].replay_warning_policy.policy_digest == right[0].replay_warning_policy.policy_digest


# ---------------------------------------------------------------------------
# Training-only method identity and assessment-position projections
# ---------------------------------------------------------------------------


def _replay_config(foundation, **acceptance) -> dict:
    return _config(
        "multihead_replay",
        foundation=foundation,
        acceptance={
            "post_selection_checkpoint_policy_generation": P5_CHECKPOINT_POLICY_GENERATION,
            **acceptance,
        },
    )


def _positions(config: dict) -> dict[str, str]:
    policies, method, cv, production = _resolved(config)
    cv_hard = post_selection_checkpoint_admissibility(policies, cv)
    final_hard = post_selection_checkpoint_admissibility(policies, production)
    return {
        "method": method.content_digest,
        "cv_position": cv_assessment_position_policy_digest(cv_hard, cv),
        "final_seed_position": final_seed_assessment_policy_digest(final_hard),
        "publication": final_publication_policy_digest(production),
        "warning": policies.replay_warning_policy.policy_digest,
    }


@pytest.mark.parametrize(
    "edit, moved",
    [
        ({"acceptance": {"replay_degradation_warning_mev_per_a": 40.0}}, {"warning"}),
        (
            {"acceptance": {"replay_degradation_hard_limit_mev_per_a": 90.0}},
            {"cv_position", "final_seed_position"},
        ),
        ({"acceptance": {"maximum_target_force_rmse_ev_per_angstrom": 0.045}}, {"final_seed_position"}),
        (
            {"post_selection": {"cv": {"checkpoint_maximum_target_force_rmse_ev_per_angstrom": 0.06}}},
            {"cv_position"},
        ),
        ({"post_selection": {"cv": {"acceptance_maximum": 0.06}}}, {"cv_position"}),
        (
            {"post_selection": {"production": {"committee_policy": "single_best_final_seed"}}},
            {"publication"},
        ),
    ],
)
def test_policy_edits_move_only_their_governed_projection(edit, moved, foundation):
    base = _replay_config(foundation)
    changed = copy.deepcopy(base)
    for table, values in edit.items():
        if table == "post_selection":
            for sub, entries in values.items():
                changed.setdefault("post_selection", {}).setdefault(sub, {}).update(entries)
        else:
            changed.setdefault(table, {}).update(values)
    before, after = _positions(base), _positions(changed)
    assert {name for name in before if before[name] != after[name]} == moved
    # No assessment-only edit ever moves the training method.
    assert "method" not in moved


def test_training_bearing_edit_moves_the_method(foundation):
    base = _replay_config(foundation)
    changed = copy.deepcopy(base)
    changed["training"]["learning_rate"] = 3.0e-4
    assert _positions(base)["method"] != _positions(changed)["method"]


def test_method_identity_is_training_only(foundation):
    _policies, method, _cv, _production = _resolved(_replay_config(foundation))
    payload = method.to_dict()
    assert "shared_checkpoint_constraints_digest" not in payload
    assert "checkpoint_selection_policy_digest" not in payload


def test_historical_v3_method_projection_excludes_only_retired_fields(foundation):
    _policies, method, _cv, _production = _resolved(_replay_config(foundation))
    historical = {
        **method.training_projection(),
        "schema": "mdstats.post-selection-method-identity.v3",
        "shared_checkpoint_constraints_digest": "a" * 64,
        "checkpoint_selection_policy_digest": "b" * 64,
    }
    historical["content_digest"] = digest(historical)
    assert historical_method_training_projection(historical) == method.training_projection()
    tampered = dict(historical, learning_rate_schedule_policy_digest="c" * 64)
    with pytest.raises(TrainingDataSerializationError):
        historical_method_training_projection(tampered)
    different = {key: value for key, value in historical.items() if key != "content_digest"}
    different["mace_architecture_digest"] = "d" * 64
    different["content_digest"] = digest(different)
    assert historical_method_training_projection(different) != method.training_projection()


# ---------------------------------------------------------------------------
# Strict D2.DEF.059A / 059B ordering
# ---------------------------------------------------------------------------


def _candidate(epoch: int, rmse: float, sha: str, *, admissible: bool = True, **extra):
    return SimpleNamespace(
        admissible=admissible,
        stable_candidate_identity=f"epoch-{epoch}:{sha}",
        trajectory_point=SimpleNamespace(epoch=epoch, checkpoint_sha256=sha, in_refinement_phase=bool(extra.get("refinement"))),
        target_metrics=SimpleNamespace(
            force_component_rmse_ev_per_angstrom=rmse,
            worst_stratum_force_rmse_ev_per_angstrom=extra.get("worst", rmse),
        ),
        replay_degradation_ev_per_angstrom=extra.get("replay", 0.0),
        content_digest=digest({"epoch": epoch, "sha": sha}),
    )


def test_lower_target_rmse_wins_regardless_of_replay_secondary_or_maturity():
    from mdstats.training_data.post_selection_cv_acceptance import (
        select_post_selection_representative,
    )

    better = _candidate(3, 0.0201, "a" * 64, replay=0.095, worst=0.9, refinement=False)
    worse = _candidate(9, 0.02010001, "b" * 64, replay=-0.1, worst=0.0, refinement=True)
    inadmissible = _candidate(5, 0.001, "c" * 64, admissible=False)
    assert select_post_selection_representative([worse, inadmissible, better]) is better
    assert select_post_selection_representative([inadmissible]) is None
    with pytest.raises(PostSelectionError):
        select_post_selection_representative([])


def test_exact_within_run_ties_resolve_by_epoch_then_sha256():
    from mdstats.training_data.post_selection_cv_acceptance import (
        select_post_selection_representative,
    )

    early = _candidate(2, 0.02, "f" * 64)
    late = _candidate(7, 0.02, "0" * 64)
    assert select_post_selection_representative([late, early]) is early


def test_exact_cross_seed_ties_resolve_by_seed_then_sha256():
    from mdstats.training_data.post_selection_publication import _rank_single_best

    def seed(optimizer_seed: int, rmse: float, sha: str):
        record = _candidate(1, rmse, sha)
        evidence = SimpleNamespace(
            optimizer_seed=optimizer_seed, representative_checkpoint_sha256=sha
        )
        return evidence, record

    tie_high_seed = seed(9, 0.02, "0" * 64)
    tie_low_seed = seed(4, 0.02, "f" * 64)
    worse = seed(1, 0.021, "1" * 64)
    assert _rank_single_best([tie_high_seed, worse, tie_low_seed]) is tie_low_seed[0]


# ---------------------------------------------------------------------------
# Measurement identity and outcome-discriminated final-seed assessment
# ---------------------------------------------------------------------------


def _artifact(**overrides):
    base = dict(
        role="outer_evaluation",
        relative_path="outer_evaluation.extxyz",
        sidecar_relative_path="outer_evaluation.extxyz.manifest.json",
        sha256="a" * 64,
        configuration_count=2,
        frame_uids=("1" * 64, "2" * 64),
        membership_digest="3" * 64,
        extxyz_policy_digest="4" * 64,
        canonical_frame_authority_digest="5" * 64,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _measurement(**overrides):
    from mdstats.training_data.post_selection_execution import (
        post_selection_eval_role_digest,
    )

    kwargs = dict(
        dataset_role="outer_evaluation",
        artifact=_artifact(),
        model_state={"kind": "train2_checkpoint", "checkpoint_sha256": "6" * 64, "evaluation_model_state": "ema"},
        provider_realization={"provider": "p", "default_dtype": "float64"},
        prediction_head="target_head",
        metric_policy_digest="7" * 64,
        block_ids=("b1", "b2"),
    )
    kwargs.update(overrides)
    return post_selection_eval_role_digest(**kwargs).content_digest


def test_measurement_identity_binds_only_the_numerical_experiment():
    base = _measurement()
    # The scratch locator is not identity.
    assert _measurement(artifact=_artifact(relative_path="/tmp/other/outer.extxyz", sidecar_relative_path="x")) == base
    for override in (
        {"artifact": _artifact(sha256="8" * 64)},  # label/reference bytes
        {"artifact": _artifact(frame_uids=("1" * 64, "9" * 64))},
        {"model_state": {"kind": "train2_checkpoint", "checkpoint_sha256": "e" * 64, "evaluation_model_state": "ema"}},
        {"provider_realization": {"provider": "p", "default_dtype": "float32"}},
        {"metric_policy_digest": "d" * 64},
        {"block_ids": ("b1",)},
    ):
        assert _measurement(**override) != base


def test_final_seed_assessment_outcomes_are_tagged_and_complete():
    from mdstats.training_data.post_selection_execution import (
        RUN_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE,
        RUN_OUTCOME_REPRESENTATIVE_SELECTED,
        PostSelectionRunEvidence,
    )

    common = dict(
        selected_binding_digest="1" * 64,
        assessment_position_policy_digest="2" * 64,
        training_trajectory_identity="3" * 64,
        training_root_identity="3" * 64,
        optimizer_seed=5,
        materialization_digest="4" * 64,
        runtime_summary_digest="5" * 64,
        candidate_record_digests=("a" * 64, "b" * 64),
    )
    selected = PostSelectionRunEvidence(
        **common,
        outcome=RUN_OUTCOME_REPRESENTATIVE_SELECTED,
        checkpoint_rejection_reasons=("target_threshold_exceeded",),
        representative_candidate_identity="epoch-1:x",
        representative_checkpoint_sha256="c" * 64,
        representative_record_digest="b" * 64,
        monitor_metric_record_digest="d" * 64,
    )
    assert PostSelectionRunEvidence.from_dict(selected.to_dict()) == selected
    with pytest.raises(TrainingDataInputError, match="member"):
        PostSelectionRunEvidence(
            **{**common, "candidate_record_digests": ("a" * 64,)},
            outcome=RUN_OUTCOME_REPRESENTATIVE_SELECTED,
            checkpoint_rejection_reasons=(),
            representative_candidate_identity="epoch-1:x",
            representative_checkpoint_sha256="c" * 64,
            representative_record_digest="b" * 64,
            monitor_metric_record_digest="d" * 64,
        )
    with pytest.raises(TrainingDataInputError, match="no representative"):
        PostSelectionRunEvidence(
            **common,
            outcome=RUN_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE,
            checkpoint_rejection_reasons=("target_threshold_exceeded",),
            representative_record_digest="b" * 64,
        )
    negative = PostSelectionRunEvidence(
        **common,
        outcome=RUN_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE,
        checkpoint_rejection_reasons=(REPLAY_CATASTROPHIC_FORGETTING_REASON,),
    )
    assert negative.candidate_record_digests == common["candidate_record_digests"]
    payload = negative.to_dict()
    for forbidden in ("final_plan_digest", "cv_authorization_digest", "committee_policy"):
        assert forbidden not in payload


# ---------------------------------------------------------------------------
# Training-only completion proof (seal)
# ---------------------------------------------------------------------------


def _terminal_summary(epochs: int = 3):
    return SimpleNamespace(
        content_digest="a" * 64, completed_epochs=epochs, planned_epochs=epochs
    )


def _sealable_root(tmp_path: Path) -> Path:
    root = tmp_path / ("f" * 64)
    (root / "materialization").mkdir(parents=True)
    (root / "checkpoints").mkdir()
    (root / "materialization" / "materialization.json").write_text("{}", encoding="utf-8")
    (root / "checkpoints" / "model_run-7_epoch-2.pt").write_bytes(b"x")
    return root


def _seal(root: Path, **overrides):
    from mdstats.training_data.campaign_post_selection_runtime import (
        record_post_selection_training_completion,
    )

    kwargs = dict(
        runtime_summary=_terminal_summary(),
        runtime_plan_digest="b" * 64,
        materialization_digest="c" * 64,
    )
    kwargs.update(overrides)
    return record_post_selection_training_completion(root, **kwargs)


def test_terminal_train2_seals_without_any_assessment_file(tmp_path):
    from mdstats.training_data.campaign_post_selection_runtime import (
        certify_closed_post_selection_run_root,
        read_post_selection_run_completion,
    )

    root = _sealable_root(tmp_path)
    _seal(root)
    completion, why = read_post_selection_run_completion(root)
    assert completion is not None, why
    assert completion.terminal_proof["runtime_summary_digest"] == "a" * 64
    assert not (root / "fold-acceptance.json").exists()
    assert not (root / "run-evidence.json").exists()
    closed, why = certify_closed_post_selection_run_root(root)
    assert closed, why
    # Idempotent: an identical re-seal verifies and does not rescan.
    (root / "checkpoints" / "model_run-7_epoch-2.pt").unlink()  # gone cold
    _seal(root)
    assert read_post_selection_run_completion(root)[0] == completion


def test_non_terminal_train2_is_not_sealable(tmp_path):
    from mdstats.training_data.post_selection_execution import PostSelectionExecutionError

    root = _sealable_root(tmp_path)
    with pytest.raises(PostSelectionExecutionError, match="terminal"):
        _seal(root, runtime_summary=SimpleNamespace(content_digest="a" * 64, completed_epochs=2, planned_epochs=3))


def test_conflicting_reseal_fails_closed(tmp_path):
    from mdstats.training_data.post_selection_execution import PostSelectionExecutionError

    root = _sealable_root(tmp_path)
    _seal(root)
    with pytest.raises(PostSelectionExecutionError, match="different terminal"):
        _seal(root, materialization_digest="d" * 64)


def test_tampered_copied_or_symlinked_proofs_grant_nothing(tmp_path):
    from mdstats.training_data.campaign_post_selection_runtime import (
        RUN_COMPLETION_ANCHOR_FILENAME,
        certify_closed_post_selection_run_root,
        read_post_selection_run_completion,
    )

    root = _sealable_root(tmp_path)
    _seal(root)
    anchor = root / RUN_COMPLETION_ANCHOR_FILENAME
    original = anchor.read_text(encoding="utf-8")

    payload = json.loads(original)
    payload["terminal_proof"]["runtime_summary_digest"] = "e" * 64
    anchor.write_text(json.dumps(payload), encoding="utf-8")
    assert read_post_selection_run_completion(root)[0] is None

    copied = tmp_path / ("0" * 64)
    copied.mkdir()
    (copied / RUN_COMPLETION_ANCHOR_FILENAME).write_text(original, encoding="utf-8")
    (copied / "run-topology.json").write_text(
        (root / "run-topology.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    assert read_post_selection_run_completion(copied)[0] is None

    anchor.unlink()
    outside = tmp_path / "outside.json"
    outside.write_text(original, encoding="utf-8")
    os.symlink(outside, anchor)
    assert read_post_selection_run_completion(root)[0] is None
    assert certify_closed_post_selection_run_root(root)[0] is False


def test_foreign_node_makes_sealed_root_uncertified(tmp_path):
    from mdstats.training_data.campaign_post_selection_runtime import (
        certify_closed_post_selection_run_root,
    )

    root = _sealable_root(tmp_path)
    _seal(root)
    (root / "materialization" / "outer_evaluation.extxyz").write_text("x", encoding="utf-8")
    closed, why = certify_closed_post_selection_run_root(root)
    assert not closed and "outer_evaluation.extxyz" in why


# ---------------------------------------------------------------------------
# Property oracles (Hypothesis)
# ---------------------------------------------------------------------------

from hypothesis import given, settings, strategies as st  # noqa: E402

_rmse = st.floats(min_value=0.0, max_value=0.2, allow_nan=False, allow_infinity=False)


@settings(max_examples=200, deadline=None)
@given(
    st.lists(
        st.tuples(
            _rmse,
            st.booleans(),
            st.floats(min_value=-0.2, max_value=0.2, allow_nan=False),
            st.booleans(),
            st.sampled_from(["0" * 64, "7" * 64, "f" * 64]),
        ),
        min_size=1,
        max_size=12,
    )
)
def test_representative_is_the_brute_force_059a_minimum(rows):
    """Replay, secondary and maturity attributes never change the winner."""

    from mdstats.training_data.post_selection_cv_acceptance import (
        select_post_selection_representative,
    )

    candidates = [
        _candidate(
            epoch,
            rmse,
            sha,
            admissible=admissible,
            replay=replay,
            refinement=refinement,
            worst=1.0 - rmse,
        )
        for epoch, (rmse, admissible, replay, refinement, sha) in enumerate(rows)
    ]
    admissible = [
        (c.target_metrics.force_component_rmse_ev_per_angstrom, c.trajectory_point.epoch, c.trajectory_point.checkpoint_sha256, id(c))
        for c in candidates
        if c.admissible
    ]
    chosen = select_post_selection_representative(candidates)
    if not admissible:
        assert chosen is None
        return
    expected = min(admissible)
    assert (
        chosen.target_metrics.force_component_rmse_ev_per_angstrom,
        chosen.trajectory_point.epoch,
        chosen.trajectory_point.checkpoint_sha256,
        id(chosen),
    ) == expected


@settings(max_examples=300, deadline=None)
@given(
    warning=st.floats(min_value=1e-4, max_value=0.2, allow_nan=False),
    gap=st.floats(min_value=1e-6, max_value=0.2, allow_nan=False),
    degradation=st.floats(min_value=-0.5, max_value=0.5, allow_nan=False),
)
def test_replay_classification_matches_strict_predicates(warning, gap, degradation):
    hard_limit = warning + gap
    hard = CheckpointAdmissibilityPolicy(
        maximum_target_force_rmse_ev_per_angstrom=1.0,
        replay_degradation_hard_limit_ev_per_angstrom=hard_limit,
    )
    diagnostic = ReplayWarningDiagnosticPolicy(warning_threshold_ev_per_angstrom=warning)
    reasons = hard.failure_reasons(
        target_force_rmse_ev_per_angstrom=0.0,
        replay_degradation_ev_per_angstrom=degradation,
        replay_label_mode="true_dft",
    )
    assert (REPLAY_CATASTROPHIC_FORGETTING_REASON in reasons) == (degradation > hard_limit)
    assert bool(diagnostic.diagnostic_warnings(degradation)) == (degradation > warning)
    assert reasons in ((), (REPLAY_CATASTROPHIC_FORGETTING_REASON,))


def test_observed_production_trajectory_oracle_under_current_defaults():
    """Workplan 10.7: the diagnosed 40-epoch trajectory under 50/100 defaults."""

    foundation_rmse = 0.07934333438787265
    hard = CheckpointAdmissibilityPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.050,
        replay_degradation_hard_limit_ev_per_angstrom=0.100,
    )
    warning = ReplayWarningDiagnosticPolicy(0.050)
    observed = {
        7: (0.0299156, 0.1146174, False),
        8: (0.0290000, foundation_rmse + 0.05178, True),
        21: (0.0246485, 0.1550590, True),
        40: (0.0290870, 0.1684228, True),
    }
    for _epoch, (target, replay, warns) in observed.items():
        degradation = replay - foundation_rmse
        assert hard.failure_reasons(
            target_force_rmse_ev_per_angstrom=target,
            replay_degradation_ev_per_angstrom=degradation,
            replay_label_mode="true_dft",
        ) == ()
        assert bool(warning.diagnostic_warnings(degradation)) is warns


def test_diagnostics_reconstruct_every_replay_coordinate_and_selected_warning():
    from mdstats.training_data.post_selection_execution import (
        PostSelectionCheckpointDiagnostics,
        post_selection_checkpoint_diagnostic_rows,
    )

    hard = _hard()
    warning = ReplayWarningDiagnosticPolicy(0.050)
    selected = SimpleNamespace(
        stable_candidate_identity="epoch-21:" + "a" * 64,
        trajectory_point=SimpleNamespace(epoch=21, checkpoint_sha256="a" * 64),
        target_metrics=SimpleNamespace(force_component_rmse_ev_per_angstrom=0.0246485),
        replay_candidate_force_rmse_ev_per_angstrom=0.1550590,
        replay_foundation_force_rmse_ev_per_angstrom=0.0793433,
        replay_degradation_ev_per_angstrom=0.1550590 - 0.0793433,
        rejection_reasons=(),
        admissible=True,
    )
    rejected = SimpleNamespace(
        stable_candidate_identity="epoch-40:" + "b" * 64,
        trajectory_point=SimpleNamespace(epoch=40, checkpoint_sha256="b" * 64),
        target_metrics=SimpleNamespace(force_component_rmse_ev_per_angstrom=0.02),
        replay_candidate_force_rmse_ev_per_angstrom=0.19,
        replay_foundation_force_rmse_ev_per_angstrom=0.0793433,
        replay_degradation_ev_per_angstrom=0.19 - 0.0793433,
        rejection_reasons=(REPLAY_CATASTROPHIC_FORGETTING_REASON,),
        admissible=False,
    )
    rows = post_selection_checkpoint_diagnostic_rows(
        [rejected, selected], hard_policy=hard, warning_policy=warning, representative=selected
    )
    assert [row["epoch"] for row in rows] == [21, 40]
    first = rows[0]
    for key in (
        "target_force_rmse_ev_per_angstrom",
        "target_ceiling_ev_per_angstrom",
        "target_margin_ev_per_angstrom",
        "replay_candidate_force_rmse_ev_per_angstrom",
        "replay_foundation_force_rmse_ev_per_angstrom",
        "replay_degradation_ev_per_angstrom",
        "replay_warning_ev_per_angstrom",
        "replay_warning_margin_ev_per_angstrom",
        "replay_hard_limit_ev_per_angstrom",
        "replay_hard_margin_ev_per_angstrom",
        "warning_codes",
        "hard_rejection_reasons",
        "checkpoint_sha256",
        "selected",
    ):
        assert key in first
    assert first["selected"] and first["warning_codes"] == [REPLAY_WARNING_CODE]
    assert first["hard_rejection_reasons"] == []  # a warning, not a failure
    assert rows[1]["warning_codes"] == [REPLAY_WARNING_CODE]
    assert rows[1]["hard_rejection_reasons"] == [REPLAY_CATASTROPHIC_FORGETTING_REASON]
    diagnostics = PostSelectionCheckpointDiagnostics(
        training_trajectory_identity="c" * 64,
        run_role="final_production",
        hard_policy=hard.to_dict(),
        warning_policy=warning.to_dict(),
        rows=rows,
        representative_candidate_identity=selected.stable_candidate_identity,
    )
    assert diagnostics.representative_warning_codes == (REPLAY_WARNING_CODE,)
    assert diagnostics.to_dict()["decision_authority"] == "diagnostic_only"
