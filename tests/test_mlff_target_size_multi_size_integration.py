"""Assembled acceptance: two frozen sizes through the real CV and production owners.

The whole point of the multi-size design is that the *existing* post-selection
methodology gains a size dimension and nothing else.  So this drives the real
public commands - `cross-validate`, then `train-production` - and asserts that
the production orchestrator, not the test, enumerates every frozen size and
hands each one its own exact ``T_N``, its own frozen horizons, and its own
accepted cross-validation ancestry.  Only MACE's numerics are substituted,
strictly below the P5 owner boundary.

The collection-wide production barrier is the other claim under test: a
requested two-size experiment must never quietly become the one size that
happened to succeed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import tests._mlff_post_selection_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_post_selection import (
    PostSelectionError,
    load_current_selected_training_contexts,
)
from mdstats.training_data.campaign_post_selection_runtime import (
    _resolve_post_selection_replay_resolution,
    build_post_selection_contexts,
    resolve_current_cv_acceptance,
    resolve_current_cv_plan,
    resolve_current_final_production_plan,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)
from mdstats.training_data.post_selection_publication import (
    resolve_current_final_production_publication,
)
from mdstats.training_data.replay import canonical_replay_geometry_identity
from tests.test_mlff_target_size_p5_r9_guards import _write_tiny_mace_foundation

#: Two CV-feasible qualified sizes from the fixture ladder ``[2, 4, 8, 16]``.
FIRST_SIZE = 8
SECOND_SIZE = 16


class _PoisonTrainer:
    def __call__(self, request):  # pragma: no cover - never reached
        raise AssertionError("Selection may never train a candidate.")


def _prepared(tmp_path: Path):
    from unittest.mock import patch

    with patch.object(p4d, "_CONFIG", fx.fixture_config_text()):
        config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    return config, workspace


def _select(config: Path, *argv: str) -> int:
    return p4d._run(
        config,
        "select-target-size",
        *argv,
        _external_boundary_trainer=_PoisonTrainer(),
        _external_inference_evaluator=_PoisonTrainer(),
    )


def _two_size_campaign(tmp_path: Path) -> Path:
    config, _workspace = _prepared(tmp_path)
    assert _select(config, str(FIRST_SIZE), "--horizon", "2") == 0
    assert _select(config, str(SECOND_SIZE), "--horizon", "3") == 0
    return config


def _write_single_source_replay(path: Path, count: int = 12) -> None:
    from ase import Atoms
    from ase.io import write

    frames = []
    for index in range(count):
        atoms = Atoms(
            "LiO",
            positions=((0.8 + 0.35 * index, 0.8, 0.8), (4.5, 4.5, 4.5)),
            cell=(10.0, 10.0, 10.0),
            pbc=True,
        )
        atoms.info["REF_energy"] = -10.0 + 0.01 * index
        atoms.info["replay_geometry_identity"] = canonical_replay_geometry_identity(atoms)
        atoms.arrays["REF_forces"] = np.asarray(
            [[0.1 + 0.001 * index, 0.0, 0.0], [-0.1 - 0.001 * index, 0.0, 0.0]],
            dtype=np.float64,
        )
        frames.append(atoms)
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, frames, format="extxyz")


def _two_size_single_source_replay_campaign(tmp_path: Path) -> tuple[Path, Path]:
    from unittest.mock import patch

    replay_source = tmp_path / "replay-source.extxyz"
    foundation = tmp_path / "foundation.model"
    _write_single_source_replay(replay_source)
    _write_tiny_mace_foundation(foundation)
    config_text = fx.fixture_config_text()
    config_text = config_text.replace(
        'training_root = "{training_root}"',
        "\n".join(
            (
                'training_root = "{training_root}"',
                f'foundation_model = "{foundation}"',
                f'replay_set = "{replay_source}"',
            )
        ),
    )
    config_text = config_text.replace(
        "seeds = [1, 2]",
        "seeds = [1, 2]\nmode = \"multihead_replay\"",
        1,
    )
    config_text += """

[replay]
label_mode = "true_dft"
split_ratio = "5:1"
split_seed = 42
allow_small_corpus = true
minimum_train_configurations = 1
minimum_monitor_configurations = 1
require_target_elements = false

[foundation]
family = "mace_mpa_0"
head = "default"
legacy_normalized = true
"""
    with patch.object(p4d, "_CONFIG", config_text):
        config, _workspace = p4d._fixture_campaign(tmp_path / "fixture")
    assert p4d._run(config, "prepare") == 0
    assert _select(config, str(FIRST_SIZE), "--horizon", "2") == 0
    assert _select(config, str(SECOND_SIZE), "--horizon", "3") == 0
    return config, replay_source


def _contexts(config: Path):
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        yield_value = (cfg, paths, build_post_selection_contexts(cfg, paths, store))
    finally:
        store.close()
    return yield_value


def _state(config: Path):
    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store).state
    finally:
        store.close()


# --- A10 / A12 / A13: the real owners across the size dimension -------------


def test_cross_validate_then_production_covers_every_frozen_size(tmp_path: Path):
    config = _two_size_campaign(tmp_path)

    cv = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, cv) == 0

    state = _state(config)
    assert [entry.n_selected for entry in state.frozen_entries] == [
        FIRST_SIZE,
        SECOND_SIZE,
    ]
    assert state.provisional_entries == ()

    _cfg, _paths, contexts = _contexts(config)
    assert [context.selected.n_selected for context in contexts] == [FIRST_SIZE, SECOND_SIZE]

    # Each size received the real CV plan owner with its own exact membership.
    plans = []
    for context in contexts:
        plan = resolve_current_cv_plan(context)
        assert plan is not None
        assert plan.binding.n_selected == context.selected.n_selected
        assert plan.binding.content_digest == context.selected.binding.content_digest
        acceptance = resolve_current_cv_acceptance(context)
        assert acceptance is not None and acceptance.accepted
        assert acceptance.selected_binding_digest == context.selected.binding.content_digest
        plans.append(plan)
    # No cross-size contamination: two sizes are two plans.
    assert plans[0].content_digest != plans[1].content_digest
    assert set(plans[0].folds[0].training_frame_uids) != set(
        plans[1].folds[0].training_frame_uids
    )

    production = fx.PostSelectionHarness()
    assert fx.run_train_production(config, production) == 0

    _cfg, _paths, contexts = _contexts(config)
    publications = []
    for context, expected_epochs in zip(contexts, (2, 3)):
        final_plan = resolve_current_final_production_plan(context)
        assert final_plan is not None
        # Its own frozen production horizon, not the other size's and not the
        # value the configuration file happens to hold now.
        assert final_plan.planned_epochs == expected_epochs
        assert final_plan.n_selected == context.selected.n_selected
        assert final_plan.target_membership_digest == (
            context.selected.selected_membership_digest
        )
        assert final_plan.cv_plan_digest == resolve_current_cv_plan(
            context
        ).content_digest
        decision = resolve_current_final_production_publication(context)
        assert decision is not None
        assert decision.binding.content_digest == context.selected.binding.content_digest
        publications.append(decision)
    assert publications[0].content_digest != publications[1].content_digest

    # A size can never consume its sibling's evidence.
    with pytest.raises(PostSelectionError, match="descends from"):
        contexts[0].selected.require_binding(contexts[1].selected.binding)


def test_replay_enabled_multi_size_uses_one_geometry_identity_source_per_size(
    tmp_path: Path,
):
    """Replay membership stays shared while P5 still executes both sizes."""

    config, replay_source = _two_size_single_source_replay_campaign(tmp_path)
    source_bytes = replay_source.read_bytes()

    cv_harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, cv_harness) == 0
    _cfg, _paths, contexts = _contexts(config)
    assert [context.selected.n_selected for context in contexts] == [FIRST_SIZE, SECOND_SIZE]
    for context in contexts:
        assert context.method.training_mode == "multihead_replay"
        resolution = _resolve_post_selection_replay_resolution(context)
        assert resolution is not None
        assert resolution.interface == "single_source"
        assert resolution.train_artifact.configuration_count == 10
        assert resolution.monitor_artifact.configuration_count == 2
        assert Path(resolution.source_path) == replay_source.resolve()

    production = fx.PostSelectionHarness()
    assert fx.run_train_production(config, production) == 0
    assert len(production.requests) == 2
    assert {request.replay_train_artifact.configuration_count for request in production.requests} == {
        10
    }
    assert replay_source.read_bytes() == source_bytes

    _cfg, _paths, contexts = _contexts(config)
    assert [
        resolve_current_final_production_plan(context).n_selected
        for context in contexts
    ] == [FIRST_SIZE, SECOND_SIZE]


def test_production_admits_nothing_while_any_selected_size_lacks_accepted_cv(
    tmp_path: Path,
):
    """The barrier is collection-wide, and it runs before any new job starts."""

    config = _two_size_campaign(tmp_path)

    # Freeze the design and cross-validate only the first size, by driving the
    # real CV owner for that one context directly.
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        from mdstats.training_data.campaign_post_selection_runtime import (
            execute_post_selection_cross_validation,
        )

        harness = fx.PostSelectionHarness()
        contexts = build_post_selection_contexts(
            cfg,
            paths,
            store,
            trainer=harness.train,
            inference_evaluator=harness.evaluate,
            admit=True,
        )
        _plan, acceptance = execute_post_selection_cross_validation(contexts[0])
        assert acceptance.accepted
        assert resolve_current_cv_acceptance(contexts[1]) is None
    finally:
        store.close()

    barrier = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionError, match="not admitted"):
        fx.run_train_production(config, barrier)
    assert barrier.runs == [], "no production job may be admitted behind the barrier"

    # The accepted sibling's immutable evidence is untouched by the refusal.
    _cfg, _paths, contexts = _contexts(config)
    assert resolve_current_cv_acceptance(contexts[0]).accepted
    assert resolve_current_final_production_plan(contexts[0]) is None

    # Completing the missing size unblocks the whole design, and the already
    # accepted sibling is not recomputed.
    resume = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, resume) == 0
    assert fx.run_train_production(config, fx.PostSelectionHarness()) == 0
    _cfg, _paths, contexts = _contexts(config)
    for context in contexts:
        assert resolve_current_final_production_publication(context) is not None


# --- A15: generation rollover ----------------------------------------------


def test_a_changed_prepared_identity_retires_the_entire_multi_size_design(
    tmp_path: Path,
):
    config = _two_size_campaign(tmp_path)
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0
    before = _state(config)
    generation = before.generation
    _cfg, _paths, contexts = _contexts(config)
    retired_bindings = [context.selected.binding for context in contexts]

    # An unchanged `prepare` preserves the generation and the whole design.
    assert p4d._run(config, "prepare") == 0
    unchanged = _state(config)
    assert unchanged.generation == generation
    assert unchanged.frozen_entries == before.frozen_entries

    # A changed prepared identity replaces the design with a fresh generation.
    fx.rewrite_config(config, "minimum_block_frames = 4", "minimum_block_frames = 2")
    assert p4d._run(config, "prepare") == 0
    after = _state(config)
    assert after.generation > generation
    assert after.frozen_entries is None
    assert after.provisional_entries == ()

    # No old per-size binding is current any more, and a stale writer holding
    # one cannot publish against the fresh generation.
    from mdstats.training_data.campaign_post_selection import (
        PostSelectionStaleBindingError,
    )
    from mdstats.training_data._common import digest
    from mdstats.training_data.post_selection_store import (
        POINTER_CV_PLAN,
        publish_current_post_selection_pointer,
    )

    from mdstats.training_data.campaign_target_size_selection import (
        TargetSizeSelectionError,
    )

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        for binding in retired_bindings:
            with pytest.raises(PostSelectionStaleBindingError):
                publish_current_post_selection_pointer(
                    store,
                    binding=binding,
                    kind=POINTER_CV_PLAN,
                    content_digest=digest({"stale": binding.n_selected}),
                )
        # The fresh generation carries no selection at all, so downstream work
        # requires an explicit new decision rather than inheriting the old N.
        with pytest.raises(TargetSizeSelectionError):
            load_current_selected_training_contexts(cfg, paths, store)
    finally:
        store.close()


# --- A16 / A20: coherent observation, aggregate lifecycle, routing ----------


def test_status_and_advance_report_every_selected_size(tmp_path: Path, capsys):
    from mdstats.training_data.campaign_lifecycle import (
        campaign_owner_snapshot,
        project_campaign_lifecycle,
    )

    config = _two_size_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)

    def snapshot():
        store = CampaignStore(paths.state_db)
        try:
            return project_campaign_lifecycle(paths, store)
        finally:
            store.close()

    provisional = snapshot()
    step = provisional.step("target_size_selection")
    assert step.state == "complete"
    assert "2 selected size(s)" in step.message
    assert f"N={FIRST_SIZE}" in step.message and f"N={SECOND_SIZE}" in step.message
    assert "Frozen: no" in step.message
    assert provisional.next_command == "cross-validate"

    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0
    frozen = snapshot()
    assert "Frozen: yes" in frozen.step("target_size_selection").message
    # Every requested size is accounted for in the aggregate CV answer.
    cv_message = frozen.step("post_selection_cv").message
    assert f"N={FIRST_SIZE}:" in cv_message and f"N={SECOND_SIZE}:" in cv_message
    assert frozen.step("post_selection_cv").state == "complete"
    assert frozen.next_command == "train-production"

    assert fx.run_train_production(config, fx.PostSelectionHarness()) == 0
    complete = snapshot()
    assert complete.step("final_production").state == "complete"
    production_message = complete.step("final_production").message
    assert f"N={FIRST_SIZE}:" in production_message
    assert f"N={SECOND_SIZE}:" in production_message

    # A completed multi-size training experiment is terminal, and it is not a
    # release: `advance` proposes no further consequential command.
    terminal = complete.terminal_step
    assert terminal is not None
    assert terminal.key == "post_production_qualification"
    assert "NOT release qualified" in terminal.message
    assert complete.next_command is None

    capsys.readouterr()
    assert p4d._run(config, "advance") == 0
    advanced = capsys.readouterr().out
    assert "no next production command" in advanced
    assert "NOT release qualified" in advanced

    # Observation is one coherent read over every current per-size namespace,
    # and it creates nothing.
    store = CampaignStore(paths.state_db)
    try:
        _revision, bindings, pointers = campaign_owner_snapshot(store)
        assert [binding.n_selected for binding in bindings] == [
            FIRST_SIZE,
            SECOND_SIZE,
        ]
        for binding in bindings:
            prefix = f"post_selection:{binding.content_digest}:"
            assert any(key.startswith(prefix) for key in pointers)
        # No P7 namespace is even read: qualification is not authorized here.
        assert not any(key.startswith("qualification:") for key in pointers)
    finally:
        store.close()


def test_advance_stops_at_an_empty_design(tmp_path: Path, capsys):
    from mdstats.training_data.campaign_lifecycle import project_campaign_lifecycle

    config, _workspace = _prepared(tmp_path)
    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        snapshot = project_campaign_lifecycle(paths, store)
    finally:
        store.close()
    step = snapshot.step("target_size_selection")
    assert step.state == "waiting"
    assert "no provisional target size has been chosen" in step.message
    assert snapshot.next_command == "select-target-size"

    capsys.readouterr()
    assert p4d._run(config, "advance") == 0
    assert "does not decide it for you" in capsys.readouterr().out


# --- A21: the qualification boundary ---------------------------------------


def test_multi_size_qualification_fails_closed_before_anything_is_opened(
    tmp_path: Path, capsys
):
    from mdstats.training_data.qualification.errors import (
        QualificationUnavailableError,
    )
    from mdstats.training_data.qualification.store import qualification_root

    config = _two_size_campaign(tmp_path)
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0
    assert fx.run_train_production(config, fx.PostSelectionHarness()) == 0

    _cfg, paths = cli._load_config(config)
    generation = _state(config).generation
    root = qualification_root(paths, generation)

    for argv in (
        ["qualification", "run"],
        ["qualification", "activate-locked", "--confirm"],
    ):
        with pytest.raises(QualificationUnavailableError, match="multi-size"):
            cli.main(["--config", str(config), *argv])
        # Nothing was created: no attempt, no evidence root, no locked opening.
        assert not root.exists(), sorted(p.name for p in root.iterdir())

    # `status` stays observational and explains the boundary.
    capsys.readouterr()
    assert cli.main(["--config", str(config), "qualification", "status"]) == 0
    output = capsys.readouterr().out
    assert "Qualification is unavailable for a multi-size frozen target design" in output
    assert f"[{FIRST_SIZE}, {SECOND_SIZE}]" in output
    assert not root.exists()


def test_single_size_qualification_keeps_its_existing_route(tmp_path: Path):
    """``k == 1`` still routes to the existing P7 stage, unchanged."""

    from mdstats.training_data.campaign_lifecycle import project_campaign_lifecycle

    config, _workspace = _prepared(tmp_path)
    assert _select(config, str(FIRST_SIZE)) == 0
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0
    assert fx.run_train_production(config, fx.PostSelectionHarness()) == 0

    _cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        snapshot = project_campaign_lifecycle(paths, store)
    finally:
        store.close()
    assert snapshot.terminal_step is None
    assert snapshot.next_command == "qualification run"
    step = snapshot.step("post_production_qualification")
    assert step.state == "not_started"
    assert "run `qualification run`" in step.message


# --- T1 / T2 / T3: CV currentness & collection preflight acceptance --------


def test_t1_single_size_cv_policy_currentness_guards_production(tmp_path: Path):
    """T1: changing a non-horizon CV-policy field invalidates CV currentness before production."""
    config, _workspace = _prepared(tmp_path)
    assert _select(config, str(FIRST_SIZE), "--horizon-cv", "2", "--horizon", "3") == 0

    cv_harness = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, cv_harness) == 0

    _cfg, _paths, contexts = _contexts(config)
    context = contexts[0]
    initial_plan = resolve_current_cv_plan(context)
    assert initial_plan is not None
    initial_acceptance = resolve_current_cv_acceptance(context)
    assert initial_acceptance is not None and initial_acceptance.accepted

    # Change a non-horizon CV-policy field in config: partition_seed.
    fx.rewrite_config(config, "partition_seed = 7", "partition_seed = 42")

    # Real train-production must fail before trainer launch and before publication.
    prod_harness = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionError, match="cross-validation policy"):
        fx.run_train_production(config, prod_harness)
    assert prod_harness.runs == [], "zero production trainer invocations on stale CV policy"

    _cfg, _paths, contexts = _contexts(config)
    assert resolve_current_final_production_plan(contexts[0]) is None
    assert resolve_current_final_production_publication(contexts[0]) is None

    # Rerun cross-validate under policy B; prove production can then proceed.
    cv_harness_b = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, cv_harness_b) == 0
    prod_harness_b = fx.PostSelectionHarness()
    assert fx.run_train_production(config, prod_harness_b) == 0
    _cfg, _paths, contexts = _contexts(config)
    assert resolve_current_final_production_publication(contexts[0]) is not None


def test_t2_collection_wide_stale_or_corrupt_late_member_barrier(tmp_path: Path):
    """T2: invalidating only the later frozen size stops train-production collection-wide."""
    config = _two_size_campaign(tmp_path)
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0

    _cfg, _paths, contexts = _contexts(config)
    assert len(contexts) == 2
    later_context = contexts[1]
    later_plan = resolve_current_cv_plan(later_context)
    assert later_plan is not None

    # Invalidate only the later size below the owner boundary:
    # Remove the CV plan object from the later size's evidence store so its pointer
    # references a missing object.
    object_file = later_context.evidence_store.object_path(later_plan.content_digest)
    assert object_file.is_file()
    object_file.unlink()

    # Call real public train-production.
    barrier_harness = fx.PostSelectionHarness()
    with pytest.raises(PostSelectionError) as excinfo:
        fx.run_train_production(config, barrier_harness)

    # 1. Zero new production trainer invocations for all sizes.
    assert barrier_harness.runs == [], "no production jobs admitted when any size is invalid"

    # 2. No new final-production plan or publication becomes current for the earlier size.
    _cfg, _paths, contexts = _contexts(config)
    assert resolve_current_final_production_plan(contexts[0]) is None
    assert resolve_current_final_production_publication(contexts[0]) is None

    # 3. All known blocking N/reasons are surfaced.
    assert f"N={SECOND_SIZE}" in str(excinfo.value)
    assert "not admitted" in str(excinfo.value)

    # 4. Existing immutable historical evidence of earlier size remains untouched.
    earlier_plan = resolve_current_cv_plan(contexts[0])
    assert earlier_plan is not None
    assert resolve_current_cv_acceptance(contexts[0]).accepted


def test_t3_exact_acceptance_policy_ancestry(tmp_path: Path):
    """T3: acceptance whose cv_policy_identity_digest disagrees with the plan is rejected."""
    from dataclasses import replace
    from mdstats.training_data.post_selection_cv_acceptance import (
        PostSelectionCvRejectedError,
        require_cv_acceptance_for_method,
    )

    config = _two_size_campaign(tmp_path)
    assert fx.run_cross_validate(config, fx.PostSelectionHarness()) == 0

    _cfg, _paths, contexts = _contexts(config)
    context = contexts[0]
    plan = resolve_current_cv_plan(context)
    acceptance = resolve_current_cv_acceptance(context)
    assert plan is not None and acceptance is not None

    # Tamper with the acceptance's cv_policy_identity_digest so it disagrees with the plan.
    corrupted_policy_digest = "a" * 64
    assert corrupted_policy_digest != plan.cv_policy_identity_digest
    corrupted_acceptance = replace(
        acceptance, cv_policy_identity_digest=corrupted_policy_digest
    )

    with pytest.raises(PostSelectionCvRejectedError, match="cross-validation policy"):
        require_cv_acceptance_for_method(
            corrupted_acceptance,
            plan=plan,
            method_identity_digest=context.method.content_digest,
            selected_binding_digest=context.selected.binding.content_digest,
        )
