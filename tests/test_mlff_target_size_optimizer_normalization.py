"""Target-size optimizer-normalization policy, realization, and identity.

The mathematical claims are checked against the exact batch-aware definition
rather than against implementation output, and the identity claims are driven
through the real P3 owners that build schedules, execution contexts, and
candidate trajectories.
"""
from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.mace_export import MaceExtxyzPolicy
from mdstats.training_data.objectives import TrainingObjectivePolicy
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    DEFAULT_REFERENCE_EMA_DECAY,
    DEFAULT_REFERENCE_LEARNING_RATE,
    DEFAULT_REFERENCE_TARGET_SIZE,
    TargetSizeCommonTrainingPolicy,
    TargetSizeOptimizerNormalizationPolicy,
    build_target_size_candidate_trajectory,
    build_target_size_common_preparation,
    build_target_size_execution_context,
    build_target_size_screen_schedule,
    project_target_size_candidate_preparation,
    resolve_target_size_common_training_policy,
    resolve_target_size_optimizer_normalization_policy,
)
from mdstats.training_data.target_size_execution.execution import (
    target_size_realized_learning_rate_policy,
    target_size_rung_plan,
)
import tests.test_mlff_target_size_execution_p3a as p3a


# --- policy resolution, defaults, and validation ---------------------------


def test_defaults_are_the_specified_reference_point() -> None:
    policy = resolve_target_size_optimizer_normalization_policy({})
    assert policy.reference_target_size == DEFAULT_REFERENCE_TARGET_SIZE == 1024
    assert policy.reference_learning_rate == DEFAULT_REFERENCE_LEARNING_RATE == 1.0e-4
    assert policy.reference_ema_decay == DEFAULT_REFERENCE_EMA_DECAY == 0.99999


def test_overrides_resolve_serialize_and_participate_in_identity() -> None:
    config = {
        "target_data": {
            "size_convergence": {
                "optimizer_normalization": {
                    "reference_target_size": 512,
                    "reference_learning_rate": 5.0e-5,
                    "reference_ema_decay": 0.9999,
                }
            }
        }
    }
    policy = resolve_target_size_optimizer_normalization_policy(config)
    assert policy.reference_target_size == 512
    assert policy.reference_learning_rate == 5.0e-5
    assert policy.reference_ema_decay == 0.9999
    assert policy.content_digest != (
        TargetSizeOptimizerNormalizationPolicy().content_digest
    )
    round_tripped = TargetSizeOptimizerNormalizationPolicy.from_dict(policy.to_dict())
    assert round_tripped == policy
    assert round_tripped.content_digest == policy.content_digest
    # Each reference value moves identity on its own.
    for field, value in (
        ("reference_target_size", 2048),
        ("reference_learning_rate", 2.0e-4),
        ("reference_ema_decay", 0.999),
    ):
        assert (
            replace(policy, **{field: value}).content_digest != policy.content_digest
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("reference_target_size", 0),
        ("reference_target_size", -8),
        ("reference_learning_rate", 0.0),
        ("reference_learning_rate", -1.0e-4),
        ("reference_learning_rate", float("nan")),
        ("reference_learning_rate", float("inf")),
        ("reference_ema_decay", 0.0),
        ("reference_ema_decay", 1.0),
        ("reference_ema_decay", 1.5),
        ("reference_ema_decay", float("nan")),
    ],
)
def test_invalid_reference_values_fail_closed(field, value) -> None:
    with pytest.raises(TrainingDataInputError):
        TargetSizeOptimizerNormalizationPolicy(**{field: value})


def test_algorithm_identity_is_specification_owned() -> None:
    with pytest.raises(TrainingDataInputError):
        TargetSizeOptimizerNormalizationPolicy(algorithm="user_plugin.v9")
    with pytest.raises(TrainingDataSerializationError):
        TargetSizeOptimizerNormalizationPolicy.from_dict(
            {"schema": "foreign", "algorithm": "x"}
        )


def test_reference_size_need_not_be_a_candidate_or_inside_the_ladder() -> None:
    ladder = tuple(2**p for p in range(7, 15))
    for reference in (3, 100, 1_000_000):
        assert reference not in ladder
        policy = TargetSizeOptimizerNormalizationPolicy(reference_target_size=reference)
        scale = policy.optimizer_progress_scale(
            batch_size=4, updates_per_epoch=math.ceil(1024 / 4)
        )
        assert math.isfinite(scale) and scale > 0.0


# --- exact batch-aware mathematics -----------------------------------------


@pytest.mark.parametrize("batch_size", [1, 2, 3, 4, 7, 16])
@pytest.mark.parametrize("n", [1, 5, 128, 1000, 1024, 1025, 2048, 12288])
def test_scale_matches_the_exact_ceiling_definition(n, batch_size) -> None:
    policy = TargetSizeOptimizerNormalizationPolicy()
    u_ref = math.ceil(policy.reference_target_size / batch_size)
    u_n = math.ceil(n / batch_size)
    assert policy.reference_updates_per_epoch(batch_size) == u_ref
    scale = policy.optimizer_progress_scale(
        batch_size=batch_size, updates_per_epoch=u_n
    )
    assert scale == pytest.approx(u_ref / u_n, rel=0.0, abs=0.0)

    # Total LR-integral and total EMA horizon per epoch are invariant in N.
    lr = policy.effective_base_learning_rate(scale)
    assert lr * u_n == pytest.approx(policy.reference_learning_rate * u_ref, rel=1e-12)
    beta = policy.effective_ema_decay(scale)
    assert beta**u_n == pytest.approx(
        policy.reference_ema_decay**u_ref, rel=1e-12
    )
    # No cap, floor, or clipping is applied anywhere in the range.
    assert lr == pytest.approx(policy.reference_learning_rate * scale, rel=0.0)


def test_reference_size_gives_unit_scale_and_exact_reference_values() -> None:
    policy = TargetSizeOptimizerNormalizationPolicy()
    for batch_size in (1, 2, 4, 8, 1024):
        u = math.ceil(policy.reference_target_size / batch_size)
        scale = policy.optimizer_progress_scale(
            batch_size=batch_size, updates_per_epoch=u
        )
        assert scale == 1.0
        assert policy.effective_base_learning_rate(scale) == (
            policy.reference_learning_rate
        )
        assert policy.effective_ema_decay(scale) == pytest.approx(
            policy.reference_ema_decay, rel=1e-15
        )


def test_exact_doubling_halves_lr_and_square_roots_beta() -> None:
    policy = TargetSizeOptimizerNormalizationPolicy()
    batch_size = 4
    # Powers of two divide the batch exactly, so update geometry doubles exactly.
    single = policy.optimizer_progress_scale(
        batch_size=batch_size, updates_per_epoch=math.ceil(1024 / batch_size)
    )
    double = policy.optimizer_progress_scale(
        batch_size=batch_size, updates_per_epoch=math.ceil(2048 / batch_size)
    )
    half = policy.optimizer_progress_scale(
        batch_size=batch_size, updates_per_epoch=math.ceil(512 / batch_size)
    )
    assert double == pytest.approx(single / 2.0)
    assert half == pytest.approx(single * 2.0)
    lr_n = policy.effective_base_learning_rate(single)
    assert policy.effective_base_learning_rate(double) == pytest.approx(lr_n / 2.0)
    assert policy.effective_base_learning_rate(half) == pytest.approx(lr_n * 2.0)
    beta_n = policy.effective_ema_decay(single)
    assert policy.effective_ema_decay(double) == pytest.approx(math.sqrt(beta_n))
    assert policy.effective_ema_decay(half) == pytest.approx(beta_n**2)


def test_non_power_of_two_uses_ceiling_update_geometry_exactly() -> None:
    policy = TargetSizeOptimizerNormalizationPolicy(reference_target_size=1000)
    # 1000/3 -> 334 updates, not 333.33; 1001/3 -> 334 as well, so the scale is
    # equal for both: partial final batches are real optimizer updates.
    assert policy.reference_updates_per_epoch(3) == 334
    a = policy.optimizer_progress_scale(batch_size=3, updates_per_epoch=math.ceil(1000 / 3))
    b = policy.optimizer_progress_scale(batch_size=3, updates_per_epoch=math.ceil(1001 / 3))
    assert a == b == 1.0


def test_lr_multiplier_shape_is_unchanged_by_normalization() -> None:
    """Only amplitude is normalized; the normalized-progress curve is fixed."""

    schedule = build_target_size_screen_schedule((1, 3, 10))
    reference = schedule.learning_rate_policy
    realized = schedule.realized_learning_rate_policy(3.7e-5)
    assert realized.base_learning_rate == pytest.approx(3.7e-5)
    for name in (
        "warmup_end_fraction",
        "adaptation_end_fraction",
        "initial_multiplier",
        "adaptation_end_multiplier",
        "final_multiplier",
    ):
        assert getattr(realized, name) == getattr(reference, name)
    for step in range(0, 101):
        progress = step / 100.0
        assert realized.multiplier(progress) == reference.multiplier(progress)
        assert realized.phase(progress) == reference.phase(progress)
    # The realized policy is a distinct identity precisely because amplitude
    # changed, which is what invalidates a stale fixed-LR trajectory.
    assert realized.policy_digest != reference.policy_digest


# --- realization and identity through the real P3 owners -------------------


def _env(tmp_path: Path, *, normalization=None, objective=None, batch_size=4):
    manifest, fa, _nb, aggregate, _common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, manifest)
    common = build_target_size_common_preparation(
        aggregate,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=index,
        policy=TargetSizeCommonTrainingPolicy(
            objective_policy=objective or TrainingObjectivePolicy()
        ),
    )
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs),
        normalization_policy=normalization,
    )
    optimizer = MaceOptimizerPolicy(
        max_num_epochs=schedule.n3, batch_size=batch_size
    )
    context = build_target_size_execution_context(
        aggregate.definition,
        common,
        schedule,
        seed_neutral_optimizer_policy=optimizer,
    )
    return aggregate, common, schedule, context, optimizer


def _trajectory(env, *, target_size, seed=1, optimizer=None):
    aggregate, common, schedule, context, default_optimizer = env
    return build_target_size_candidate_trajectory(
        aggregate.definition,
        context,
        common,
        schedule,
        target_size=target_size,
        optimizer_policy=optimizer or default_optimizer,
        optimizer_seed=seed,
    )


def test_candidate_realization_binds_the_derived_normalization(tmp_path: Path) -> None:
    # Batch size 1 makes update geometry equal to N, and a reference size inside
    # the ladder puts candidates on both sides of N_ref -- the case the screen
    # actually has to normalize.
    env = _env(
        tmp_path,
        normalization=TargetSizeOptimizerNormalizationPolicy(
            reference_target_size=4
        ),
        batch_size=1,
    )
    aggregate, _common, schedule, _context, optimizer = env
    sizes = aggregate.definition.qualified_candidate_sizes
    batch = optimizer.batch_size
    normalization = schedule.normalization_policy
    for size in sizes:
        realization = _trajectory(env, target_size=size).realization
        u_n = math.ceil(size / batch)
        assert realization.updates_per_epoch == u_n
        assert realization.reference_updates_per_epoch == (
            math.ceil(normalization.reference_target_size / batch)
        )
        assert realization.optimizer_progress_scale == pytest.approx(
            realization.reference_updates_per_epoch / u_n
        )
        assert realization.effective_base_learning_rate == pytest.approx(
            normalization.reference_learning_rate
            * realization.optimizer_progress_scale
        )
        assert realization.effective_ema_decay == pytest.approx(
            normalization.reference_ema_decay
            ** realization.optimizer_progress_scale
        )
        assert realization.normalization_policy_digest == (
            normalization.content_digest
        )
        assert realization.realized_learning_rate_policy_digest == (
            schedule.realized_learning_rate_policy(
                realization.effective_base_learning_rate
            ).policy_digest
        )
    # Distinct candidate sizes really do get distinct realized amplitudes under
    # an identical epoch/pass policy.
    realizations = [_trajectory(env, target_size=s).realization for s in sizes]
    assert len({r.effective_base_learning_rate for r in realizations}) == len(sizes)
    assert len({r.effective_ema_decay for r in realizations}) == len(sizes)
    # Epoch/pass policy is identical: only amplitude varies with N.
    assert len({r.max_num_epochs for r in realizations}) == 1
    assert len({r.batch_size for r in realizations}) == 1
    # Candidates really do sit on both sides of the reference size.
    scales = sorted(r.optimizer_progress_scale for r in realizations)
    assert scales[0] < 1.0 < scales[-1]


def test_ema_disabled_realization_records_no_effective_decay(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, common, schedule, _context, _optimizer = env
    no_ema = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4, ema=False)
    context = build_target_size_execution_context(
        aggregate.definition, common, schedule, seed_neutral_optimizer_policy=no_ema
    )
    trajectory = build_target_size_candidate_trajectory(
        aggregate.definition,
        context,
        common,
        schedule,
        target_size=aggregate.definition.qualified_candidate_sizes[0],
        optimizer_policy=no_ema,
        optimizer_seed=1,
    )
    assert trajectory.realization.effective_ema_decay is None


def test_one_realization_is_replayed_across_every_rung(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, _common, schedule, _context, _optimizer = env
    trajectory = _trajectory(
        env, target_size=aggregate.definition.qualified_candidate_sizes[0]
    )
    realized = target_size_realized_learning_rate_policy(trajectory, schedule)
    plans = [
        target_size_rung_plan(trajectory, schedule, boundary_epoch=boundary)
        for boundary in schedule.fidelity_epochs
    ]
    assert {plan.learning_rate_policy.policy_digest for plan in plans} == {
        realized.policy_digest
    }
    assert {plan.budget_policy.policy_digest for plan in plans} == {
        schedule.budget_policy.policy_digest
    }
    # The pause limit is the only rung-varying input.
    assert [plan.execution_epoch_limit for plan in plans] == list(
        schedule.fidelity_epochs
    )


def test_survivor_elimination_cannot_alter_a_surviving_realization(
    tmp_path: Path,
) -> None:
    """Normalization is derived from N and B alone, never from the active set."""

    env = _env(tmp_path)
    aggregate, _common, _schedule, _context, _optimizer = env
    sizes = aggregate.definition.qualified_candidate_sizes
    before = {s: _trajectory(env, target_size=s).content_digest for s in sizes}
    # Re-derive only the "survivors" and confirm byte-identical trajectories.
    survivors = sizes[:2]
    after = {s: _trajectory(env, target_size=s).content_digest for s in survivors}
    assert all(after[s] == before[s] for s in survivors)


def test_changed_normalization_changes_p3_identity_only(tmp_path: Path) -> None:
    env_a = _env(tmp_path / "a")
    env_b = _env(
        tmp_path / "b",
        normalization=TargetSizeOptimizerNormalizationPolicy(
            reference_target_size=512
        ),
    )
    agg_a, common_a, schedule_a, context_a, _o = env_a
    agg_b, common_b, schedule_b, context_b, _o2 = env_b

    # P2 membership/order/common statistical products are untouched.
    assert agg_a.definition.content_digest == agg_b.definition.content_digest
    assert agg_a.policy.content_digest == agg_b.policy.content_digest
    assert common_a.content_digest == common_b.content_digest
    assert common_a.fitted_weights_digest == common_b.fitted_weights_digest

    # P3 execution identity does change, so a stale trajectory cannot resume.
    assert schedule_a.content_digest != schedule_b.content_digest
    assert context_a.content_digest != context_b.content_digest
    size = agg_a.definition.qualified_candidate_sizes[0]
    traj_a = _trajectory(env_a, target_size=size)
    traj_b = _trajectory(env_b, target_size=size)
    assert traj_a.content_digest != traj_b.content_digest
    assert traj_a.realization.content_digest != traj_b.realization.content_digest


def test_drifted_realization_is_diagnosed_and_rejected(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, _common, schedule, _context, _optimizer = env
    trajectory = _trajectory(
        env, target_size=aggregate.definition.qualified_candidate_sizes[0]
    )
    tampered = replace(
        trajectory,
        realization=replace(
            trajectory.realization,
            realized_learning_rate_policy_digest=digest({"forged": "lr-policy"}),
        ),
    )
    with pytest.raises(TrainingDataInputError, match="normalization"):
        target_size_realized_learning_rate_policy(tampered, schedule)
    with pytest.raises(TrainingDataInputError):
        replace(
            trajectory.realization,
            optimizer_progress_scale=trajectory.realization.optimizer_progress_scale
            * 2.0,
        )


def test_objective_changes_invalidate_common_preparation_but_normalization_does_not(
    tmp_path: Path,
) -> None:
    default = _env(tmp_path / "default")
    normalized = _env(
        tmp_path / "normalized",
        normalization=TargetSizeOptimizerNormalizationPolicy(
            reference_learning_rate=5.0e-5
        ),
    )
    reweighted = _env(
        tmp_path / "reweighted",
        objective=TrainingObjectivePolicy(forces_weight=25.0),
    )
    assert normalized[1].content_digest == default[1].content_digest
    assert reweighted[1].content_digest != default[1].content_digest
    assert reweighted[1].objective_policy.forces_weight == 25.0


def test_screen_reference_lr_is_the_sole_amplitude_authority() -> None:
    """A competing [training].learning_rate cannot reach the screen schedule."""

    config = {
        "training": {"learning_rate": 9.9e-3},
        "target_data": {
            "size_convergence": {
                "optimizer_normalization": {"reference_learning_rate": 3.0e-5}
            }
        },
    }
    normalization = resolve_target_size_optimizer_normalization_policy(config)
    schedule = build_target_size_screen_schedule(
        (1, 3, 10), normalization_policy=normalization
    )
    assert schedule.learning_rate_policy.base_learning_rate == 3.0e-5
    assert normalization.reference_learning_rate == 3.0e-5


def test_common_training_policy_resolver_honours_the_configured_objective() -> None:
    policy = resolve_target_size_common_training_policy(
        {"objective": {"energy_weight": 2.0, "forces_weight": 20.0}}
    )
    assert policy.objective_policy.energy_weight == 2.0
    assert policy.objective_policy.forces_weight == 20.0
    assert policy.objective_policy.stress_weight == 1.0
    assert policy.content_digest != TargetSizeCommonTrainingPolicy().content_digest


# --- assembled integration through the real select-target-size command ------


def test_assembled_screen_normalizes_every_current_candidate_route(
    tmp_path: Path,
) -> None:
    """Drive the real `select-target-size` command and inspect what it wrote.

    Only MACE's numerical training/inference is substituted, strictly below the
    owner boundary. Configuration resolution, schedule construction, execution
    context, candidate realization, materialization, and the MACE config writer
    are all production code here, so this is what proves that no current route
    into candidate execution bypasses the normalization.
    """

    import json

    import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
    from mdstats.training_data._campaign_cli_core import _load_config
    from mdstats.training_data.campaign_target_size_runtime import (
        mace_run_configuration,
    )

    # Candidate ladder is 2/4/8 with batch_size 4, so a reference size of 2
    # straddles it: N=2 sits at the reference and N=8 needs half the amplitude.
    normalization_table = (
        "\n\n[target_data.size_convergence.optimizer_normalization]\n"
        "reference_target_size = 2\n"
        "reference_learning_rate = 4.0e-4\n"
        "reference_ema_decay = 0.999\n"
    )
    original = p4d._CONFIG
    p4d._CONFIG = original.rstrip() + normalization_table
    try:
        config, workspace = p4d._fixture_campaign(tmp_path)
    finally:
        p4d._CONFIG = original

    cfg, _paths = _load_config(config)
    normalization = resolve_target_size_optimizer_normalization_policy(cfg)
    assert normalization.reference_target_size == 2
    assert normalization.reference_learning_rate == 4.0e-4
    assert normalization.reference_ema_decay == 0.999

    assert p4d._run(config, "prepare") == 0
    harness = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )

    # Every candidate configuration the real materialization owner wrote.
    configs = {}
    for path in sorted(workspace.rglob("mace_config_n*_seed*.yaml")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        configs.setdefault(
            (int(payload["batch_size"]), path.name.split("_")[2]), []
        ).append(payload)
    written = [p for group in configs.values() for p in group]
    assert written, "the real screen materialized no candidate configuration"

    by_size: dict[int, list[dict]] = {}
    for payload in written:
        size = int(payload["name"].split("-n")[1].split("-")[0])
        by_size.setdefault(size, []).append(payload)
    assert len(by_size) >= 2, "need candidates on both sides of N_ref"

    batch = int(written[0]["batch_size"])
    u_ref = math.ceil(normalization.reference_target_size / batch)
    for size, payloads in by_size.items():
        expected_scale = u_ref / math.ceil(size / batch)
        for payload in payloads:
            assert payload["lr"] == pytest.approx(
                normalization.reference_learning_rate * expected_scale
            )
            assert payload["ema_decay"] == pytest.approx(
                normalization.reference_ema_decay**expected_scale
            )
            # Epoch/pass policy is identical across candidates.
            assert payload["max_num_epochs"] == written[0]["max_num_epochs"]
            assert payload["batch_size"] == batch
            # The corrected objective/loss reaches every executable config, and
            # MACE's own parser accepts what was written.
            assert payload["loss"] == "stress"
            assert payload["forces_weight"] == 10.0
            assert payload["energy_weight"] == 1.0
            assert payload["stress_weight"] == 1.0
            assert mace_run_configuration(payload)["loss"] == "stress"

    # A candidate below and a candidate above the reference really do differ.
    lrs = {size: by_size[size][0]["lr"] for size in by_size}
    assert len(set(lrs.values())) >= 2
