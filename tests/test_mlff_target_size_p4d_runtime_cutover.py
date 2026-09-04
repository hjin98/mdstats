"""P4-D acceptance: the atomic `prepare` / `select-target-size` production switch.

These tests drive the **real** campaign CLI parser, the **real** `CampaignStore`
SQLite file, and the **real** P1/P2/P3 owners.  Only MACE's numerical work is
substituted, through the private seams that sit strictly below the accepted
owner boundary: configuration parsing, authority construction, materialization,
provider/checkpoint authentication, publication, reconciliation, and campaign
adoption all execute as production code.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import pytest

import mdstats
from mdstats.training_data._common import digest
import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3d as p3d
import tests.test_mlff_neutral_scientific_substrate as neutral_fixtures
from tests.test_mlff_neutral_scientific_substrate import _data4_bundle

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_target_size_cutover import (
    QUARANTINE_KEY_PREFIX,
    TargetSizeCutoverError,
)
from mdstats.training_data.campaign_target_size_runtime import (
    MaceTargetSizeBoundaryTrainer,
    build_current_target_size_authorities,
    TargetSizeRungRequest,
    mace_run_configuration,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    TargetSizeRegime,
    load_target_size_campaign_history,
    load_target_size_campaign_revision,
)
from mdstats.training_data.target_size_execution import (
    bind_target_size_boundary_state,
)

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"

_CONFIG = """
schema = "mdstats.mlff-campaign-cli.v2"

[campaign]
id = "p4d-current-target-size"
workspace = "{workspace}"
profile = "generic"

[paths]
training_root = "{training_root}"

[data]
dataset_id = "neutral-p1"
manifest = "manifest.json"

[partition]
minimum_block_frames = 4
explicit_block_length_frames = 4
development_minimum_independent_units = 4
outer_monitor_minimum_independent_units = 1
calibration_minimum_independent_units = 1
locked_interpolation_test_minimum_independent_units = 1
purge_units_between_roles = 0
allow_calibration_deferral = true

[training]
policy_generation = "train2"
device = "cpu"
batch_size = 4
valid_batch_size = 4
num_workers = 0
seeds = [1, 2]

[target_data.size_convergence]
target_size_power_min = 1
target_size_power_max = 3
evaluation_size_powers = [0, 1, 2]
fidelity_epochs = [1, 3, 10]
practical_equivalence_mev_per_a = 1.0
"""


def _fixture_campaign(
    tmp_path: Path, *, regime: str | None = "production", approve: bool = True
) -> tuple[Path, Path]:
    """A real campaign workspace whose lower-level inputs are already built.

    DATA2-DATA5 ingestion is target-size neutral and is deliberately reused
    rather than re-run: it is exactly the "validator-proven reusable
    lower-level input" the cutover contract permits, and the current P1 owners
    re-validate every record they consume.
    """

    training_root = tmp_path / "sources"
    training_root.mkdir(parents=True, exist_ok=True)
    manifest, sources, frames, data4 = _data4_bundle(training_root, regime=regime)

    workspace = tmp_path / "campaign"
    config = tmp_path / "campaign.toml"
    config.write_text(
        _CONFIG.format(workspace=str(workspace), training_root=str(training_root)),
        encoding="utf-8",
    )
    cfg, paths = cli._load_config(config)
    paths.manifest.parent.mkdir(parents=True, exist_ok=True)
    paths.manifest.write_text(
        json.dumps(manifest.to_dict(), sort_keys=True), encoding="utf-8"
    )
    store = CampaignStore(paths.state_db)
    # Manifest approval and the doctor-frozen acceleration realization are
    # operator/runtime-qualification state, not part of the cutover.
    if approve:
        store.set_meta("approved_manifest_digest", manifest.content_digest)
    store.put_record(
        "acceleration_realization",
        mdstats.AccelerationRealizationRecord(
            requested_backend="e3nn",
            resolved_kernel_mode="e3nn",
            training_kernel_mode="e3nn",
            device="cpu",
            dtype="float32",
            foundation_inference_identity_digest=digest({"fixture": "foundation"}),
            mace_version="0.3.16",
            qualified=True,
        ),
    )
    store.put_record("source_catalog", sources)
    store.put_record("frame_catalog", frames)
    store.put_record("data4", data4)
    store.put_record("data5", {"schema": "data5-placeholder"})
    cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture")
    store.close()
    return config, workspace


def _parse(config: Path, *argv: str):
    parser = cli.build_parser()
    return parser.parse_args(["--config", str(config), *argv])


def _run(config: Path, *argv: str, **overrides) -> int:
    args = _parse(config, *argv)
    for key, value in overrides.items():
        setattr(args, key, value)
    return args.func(args)


# --- REQ1 `prepare` reaches the current P1 path and cannot select N ---------


def test_p4d_req1_prepare_binds_current_authorities_and_selects_nothing(
    tmp_path: Path, capsys
):
    config, workspace = _fixture_campaign(tmp_path)
    assert _run(config, "prepare") == 0

    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.regime is TargetSizeRegime.CURRENT
        assert revision.state.generation == 1
        assert revision.state.lifecycle is TargetSizeLifecycle.AUTHORITIES_BOUND
        # P1 and P2 identities are bound...
        assert revision.state.frame_authority_digest is not None
        assert revision.state.neutral_statistical_base_digest is not None
        assert revision.state.split_exclusion_digest is not None
        assert revision.state.experiment_definition_digest is not None
        assert revision.state.common_preparation_digest is not None
        # ...and nothing was selected, adopted, or made terminal.
        assert revision.state.terminal is None
        assert revision.state.adopted_execution_head_digest is None
        assert revision.state.attempt is None
        # No retired selector record exists as current authority.
        assert not store.has_record("target_size_study")
    finally:
        store.close()

    captured = capsys.readouterr().out
    assert "does not select a target size" in captured


def _manifest_digest(config: Path) -> str:
    _cfg, paths = cli._load_config(config)
    return mdstats.TrainingDataManifest.load(paths.manifest).content_digest


def test_p4d_req1_prepare_approve_manifest_only_records_and_returns(
    tmp_path: Path, capsys
):
    """`--approve-manifest` is approval-and-return, not a preparation trigger."""

    config, workspace = _fixture_campaign(tmp_path, approve=False)
    assert _run(config, "prepare", "--approve-manifest") == 0

    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        assert store.get_meta("approved_manifest_digest") == _manifest_digest(config)
        # No current target-size authority was constructed or advanced.
        assert load_target_size_campaign_revision(store) is None
        state, _message = store.stage("prepare")
        assert state is cli.StageState.NOT_STARTED
    finally:
        store.close()

    captured = capsys.readouterr().out
    assert "does not select a target size" not in captured
    assert "`prepare`" in captured


def test_p4d_req1_prepare_continue_after_approval_prepares_in_one_invocation(
    tmp_path: Path,
):
    config, workspace = _fixture_campaign(tmp_path, approve=False)
    assert (
        _run(config, "prepare", "--approve-manifest", "--continue-after-approval") == 0
    )
    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        assert store.get_meta("approved_manifest_digest") == _manifest_digest(config)
        revision = load_target_size_campaign_revision(store)
        assert revision.state.lifecycle is TargetSizeLifecycle.AUTHORITIES_BOUND
        assert store.stage("prepare")[0] is cli.StageState.COMPLETE
    finally:
        store.close()


def test_p4d_req1_plain_prepare_after_approval_only_prepares(tmp_path: Path):
    config, workspace = _fixture_campaign(tmp_path, approve=False)
    assert _run(config, "prepare", "--approve-manifest") == 0
    assert _run(config, "prepare") == 0
    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.generation == 1
        assert store.stage("prepare")[0] is cli.StageState.COMPLETE
    finally:
        store.close()


def test_p4d_req1_prepare_accepts_a_source_without_a_regime_assertion(tmp_path: Path):
    """The real P4 prepare owner must reach the real P1 neutral owners.

    Fixtures that assert ``regime`` masked the current no-annotation path, so
    this exercises the same production orchestration with no regime fact.
    """

    config, workspace = _fixture_campaign(tmp_path, regime=None)
    assert _run(config, "prepare") == 0
    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.regime is TargetSizeRegime.CURRENT
        assert revision.state.neutral_statistical_base_digest is not None
        assert revision.state.terminal is None
        assert not store.has_record("target_size_study")
    finally:
        store.close()


def test_p4d_req1_prepare_is_idempotent_and_keeps_one_generation(tmp_path: Path):
    config, workspace = _fixture_campaign(tmp_path)
    assert _run(config, "prepare") == 0
    assert _run(config, "prepare") == 0
    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.generation == 1
        history = load_target_size_campaign_history(store)
        generations = {item.state.generation for item in history}
        assert generations == {0, 1}
    finally:
        store.close()


def test_p4d_req1_prepare_quarantines_retired_target_size_records(tmp_path: Path):
    config, workspace = _fixture_campaign(tmp_path)
    state_db = workspace / ".mdstats" / "campaign.sqlite3"
    seed = CampaignStore(state_db)
    seed.put_record(
        "target_size_study",
        {"schema": "retired", "outcome": "selected", "selected_target_size": 96},
    )
    seed.put_record("target_data_role_freeze", {"schema": "retired"})
    seed.put_record("materialization:naive_fine_tuning-n96-seed1", {"schema": "retired"})
    seed.close()

    assert _run(config, "prepare") == 0

    store = CampaignStore(state_db)
    try:
        assert not store.has_record("target_size_study")
        assert not store.has_record("target_data_role_freeze")
        assert not store.has_record("materialization:naive_fine_tuning-n96-seed1")
        assert store.has_record(f"{QUARANTINE_KEY_PREFIX}g1:target_size_study")
        # The lower-level inputs survive and were reused.
        assert store.has_record("source_catalog")
        assert store.has_record("data4")
    finally:
        store.close()


def test_p4d_req1_prepare_call_graph_reaches_no_retired_target_size_authority():
    """`prepare` and `select-target-size` route to the current runtime owner only."""

    source = (_TRAINING_DATA / "_campaign_cli_core.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    retired = {
        "_ensure_target_size_study",
        "_load_verified_target_size_study_authority",
        "_load_train2_study_optional",
        "_ensure_target_data_role_freeze",
        "_ensure_target_multi_view_repair_v2",
        "_ensure_target_multi_view_qualification_v2",
        "_prepare_materialization",
        "_prepare_sweep",
        "_invalidate_train2_downstream_state",
        "_target_size_materialization_variants",
        "_target_size_training_variants",
        "_execute_prepare_current_authority",
    }
    for name in ("command_prepare", "command_select_target_size"):
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == name
        )
        called = {
            node.func.id
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        offending = called & retired
        if name == "command_prepare":
            # The historical (non-TRAIN2) lifecycle keeps its own preparation.
            offending -= {"_execute_prepare_current_authority"}
        assert not offending, (name, sorted(offending))


def test_p4d_req1_current_runtime_owner_imports_no_retired_module():
    """The current orchestration owner never imports a retired target-size module."""

    retired_modules = {
        "target_size_study",
        "target_data_roles",
        "target_coverage",
        "target_coverage_feasibility",
        "target_coverage_sparse_index",
        "target_multi_view_selector",
        "target_multi_view_selector_v2",
        "target_multi_view_repair",
        "target_multi_view_repair_v2",
        "target_multi_view_qualification_v2",
        "mlcv_aggregate",
        "mlcv_final",
        "mlcv_verification",
    }
    for name in (
        "campaign_target_size_runtime.py",
        "campaign_target_size_state.py",
        "campaign_target_size_cutover.py",
        "campaign_target_size_adoption.py",
        "campaign_target_size_retention.py",
        "campaign_target_size_view.py",
    ):
        tree = ast.parse((_TRAINING_DATA / name).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.lstrip("."))
            elif isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
        assert not (imported & retired_modules), (name, sorted(imported & retired_modules))


# --- REQ2 `select-target-size` reaches P1/P2/P3 ----------------------------


class _BoundedNumericalHarness:
    """Substitute only MACE's numerical work, strictly below the owner boundary.

    Both seams receive artifacts that real P3 owners produced and validated, and
    everything they return is re-authenticated before it can become evidence:
    the rung summary by ``bind_target_size_boundary_state`` and the predictions
    by the EVAL2 owner. The two seams share the current candidate identity
    because the production orchestration executes one cell at a time, which is
    what lets the substituted predictions differ per candidate so the accepted
    P2 reducer - not this harness - decides the ranking.
    """

    def __init__(self) -> None:
        self.rungs: list[tuple[int, int, int]] = []
        self.inferences: list[str] = []
        self._current = "0"

    def train(self, request: TargetSizeRungRequest):
        self.rungs.append(
            (
                int(request.trajectory.target_size),
                int(request.trajectory.optimizer_seed),
                int(request.plan.execution_epoch_limit),
            )
        )
        self._current = str(request.trajectory.content_digest)
        # The real materialization owner must have written a usable candidate
        # configuration before any rung can run.
        config_path = (
            request.materialization_directory
            / request.materialization.mace_config_relative_path
        )
        assert config_path.is_file()
        assert mace_run_configuration(
            json.loads(config_path.read_text(encoding="utf-8"))
        )["train_file"]
        _runtime, summary, _restored, _rng = p3c._run_rung(
            request.plan,
            request.checkpoint_directory,
            start_epoch=request.start_epoch,
            updates_per_epoch=request.trajectory.realization.updates_per_epoch,
            seed=int(request.trajectory.optimizer_seed),
        )
        return summary

    def evaluate(self, provider, atoms_list):
        from mdstats.training_data.mace_export import MaceExtxyzPolicy

        policy = MaceExtxyzPolicy()
        self.inferences.append(self._current)
        offset = 1.0e-3 * (1 + int(self._current[:4], 16) % 7)
        predictions = []
        for atoms in atoms_list:
            forces = (
                np.asarray(atoms.arrays[policy.forces_key], dtype=np.float64) + offset
            )
            stress = atoms.info.get(policy.stress_key)
            stress_3x3 = None
            if stress is not None:
                flat = np.asarray(stress, dtype=np.float64).reshape(-1)
                stress_3x3 = (
                    np.array(
                        [
                            [flat[0], flat[5], flat[4]],
                            [flat[5], flat[1], flat[3]],
                            [flat[4], flat[3], flat[2]],
                        ]
                    )
                    if flat.size == 6
                    else flat.reshape(3, 3)
                )
            predictions.append(
                SimpleNamespace(
                    energy_ev=float(atoms.info[policy.energy_key]),
                    forces_ev_per_angstrom=forces,
                    stress_ev_per_angstrom3=stress_3x3,
                )
            )
        return predictions


_ORDER_DIVERGENT_CONFIG = _CONFIG.replace(
    "evaluation_size_powers = [0, 1, 2]", "evaluation_size_powers = [1, 2, 3]"
)


def _order_divergent_fixture_campaign(tmp_path: Path) -> tuple[Path, Path]:
    """A real two-condition campaign whose P_train and pi_train orders differ.

    ``pi_train`` is condition-balanced round robin, so on multi-condition data
    it is not a subsequence of the stored ``P_train``.  This is the shape the
    production LTA dataset has and the single-run fixtures never produced.
    """

    training_root = tmp_path / "sources"
    training_root.mkdir(parents=True, exist_ok=True)
    for run_id, tebeg in (("runA", 650), ("runB", 900)):
        neutral_fixtures._write(
            training_root, run_id, ("Li", "O"), n_frames=64, tebeg=tebeg
        )
    manifest = mdstats.TrainingDataManifest(
        dataset_id="neutral-p1",
        system_profile="generic",
        runs=tuple(
            mdstats.TrainingDataRunSpec(
                run_id=run_id,
                vasprun=f"{run_id}/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            )
            for run_id in ("runA", "runB")
        ),
    )
    sources = mdstats.build_training_data_source_catalog(
        manifest, base_directory=training_root
    )
    frames, data4 = mdstats.build_vasp_data4_feature_bundle(
        sources,
        base_directory=training_root,
        event_policy=mdstats.EventDetectionPolicy(
            pre_frames=1,
            post_frames=1,
            force_norm_max_threshold_ev_per_angstrom=2.0,
        ),
        partition_role_budget=neutral_fixtures._data4_role_budget(),
    )

    workspace = tmp_path / "campaign"
    config = tmp_path / "campaign.toml"
    config.write_text(
        _ORDER_DIVERGENT_CONFIG.format(
            workspace=str(workspace), training_root=str(training_root)
        ),
        encoding="utf-8",
    )
    _cfg, paths = cli._load_config(config)
    paths.manifest.parent.mkdir(parents=True, exist_ok=True)
    paths.manifest.write_text(
        json.dumps(manifest.to_dict(), sort_keys=True), encoding="utf-8"
    )
    store = CampaignStore(paths.state_db)
    store.set_meta("approved_manifest_digest", manifest.content_digest)
    store.put_record(
        "acceleration_realization",
        mdstats.AccelerationRealizationRecord(
            requested_backend="e3nn",
            resolved_kernel_mode="e3nn",
            training_kernel_mode="e3nn",
            device="cpu",
            dtype="float32",
            foundation_inference_identity_digest=digest({"fixture": "foundation"}),
            mace_version="0.3.16",
            qualified=True,
        ),
    )
    store.put_record("source_catalog", sources)
    store.put_record("frame_catalog", frames)
    store.put_record("data4", data4)
    store.put_record("data5", {"schema": "data5-placeholder"})
    cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture")
    store.close()
    return config, workspace


def test_p4d_req2_select_target_size_accepts_condition_balanced_candidates(
    tmp_path: Path,
):
    """Assembled current screen on data where T_N is not a P_train subsequence.

    Nothing below `select-target-size` is patched: the real screen context,
    candidate cell, trajectory owner, and candidate projection all execute.
    """

    config, workspace = _order_divergent_fixture_campaign(tmp_path)
    assert _run(config, "prepare") == 0

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        authorities = build_current_target_size_authorities(cfg, paths, store)
    finally:
        store.close()
    aggregate = authorities.aggregate
    training = aggregate.split.training_frame_uids
    order = aggregate.definition.training_order.frame_uids
    assert set(order) == set(training)
    assert tuple(order) != tuple(training)
    position = {uid: index for index, uid in enumerate(training)}
    divergent = [
        size
        for size in aggregate.definition.qualified_candidate_sizes
        if [
            position[uid] for uid in aggregate.definition.candidate_membership(size)
        ]
        != sorted(
            position[uid]
            for uid in aggregate.definition.candidate_membership(size)
        )
    ]
    assert divergent, "fixture no longer exercises the order-divergent projection"

    harness = _BoundedNumericalHarness()
    assert (
        _run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    assert harness.rungs, "no candidate rung reached the TRAIN2 boundary"
    # The candidate sizes whose T_N is not a P_train subsequence were executed.
    assert set(divergent) & {size for size, _seed, _epoch in harness.rungs}

    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.execution_root is not None
        assert revision.state.adopted_execution_head_digest is not None
    finally:
        store.close()


def test_p4d_req2_select_target_size_reaches_p1_p2_p3_owners(tmp_path: Path):
    config, workspace = _fixture_campaign(tmp_path)
    assert _run(config, "prepare") == 0

    harness = _BoundedNumericalHarness()
    assert (
        _run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )

    assert harness.rungs, "no candidate rung reached the TRAIN2 boundary"
    assert harness.inferences, "no candidate reached the EVAL2 inference owner"
    # The paired-seed matrix came from the accepted P2 policy, not from here.
    assert {seed for _size, seed, _epoch in harness.rungs} == {1, 2}
    assert {size for size, _seed, _epoch in harness.rungs} <= {2, 4, 8}

    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        revision = load_target_size_campaign_revision(store)
        # The bounded screen runs to a terminal P2 outcome; either way the
        # generation owns a live execution root and an adopted head.
        assert revision.state.lifecycle in (
            TargetSizeLifecycle.SCREEN_ACTIVE,
            TargetSizeLifecycle.TERMINAL_SELECTED,
            TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
        )
        assert revision.state.execution_root is not None
        assert revision.state.screen_window_digest is not None
        assert revision.state.adopted_execution_head_digest is not None
        assert revision.state.attempt == revision.state.screen_window_digest
        root = workspace / revision.state.execution_root
        assert list((root / "heads").glob("*.json"))
        assert list((root / "batches").glob("*.json"))
        assert list((root / "completions").rglob("*.json"))
        # No retired selector, role-domain, or coverage record became authority.
        for retired in (
            "target_size_study",
            "target_data_role_freeze",
            "target_multi_view_repair_v2",
            "target_multi_view_qualification_v2",
        ):
            assert not store.has_record(retired)
    finally:
        store.close()


def test_p4d_req2_select_target_size_resumes_without_rerunning_completed_cells(
    tmp_path: Path,
):
    config, workspace = _fixture_campaign(tmp_path)
    assert _run(config, "prepare") == 0
    harness = _BoundedNumericalHarness()
    _run(
        config,
        "select-target-size",
        _external_boundary_trainer=harness.train,
        _external_inference_evaluator=harness.evaluate,
    )
    first = list(harness.rungs)

    resumed = _BoundedNumericalHarness()
    _run(
        config,
        "select-target-size",
        _external_boundary_trainer=resumed.train,
        _external_inference_evaluator=resumed.evaluate,
    )
    # A second invocation reconciles the durable evidence instead of repeating
    # the boundaries that already committed.
    assert len(resumed.rungs) < len(first)


def test_p4d_req2_select_target_size_requires_the_current_regime(tmp_path: Path):
    config, workspace = _fixture_campaign(tmp_path)
    with pytest.raises(TargetSizeCutoverError) as excinfo:
        _run(config, "select-target-size")
    assert "`prepare`" in str(excinfo.value)


def test_p4d_req3_retired_lifecycle_commands_are_structurally_absent(tmp_path: Path):
    """The retired production lifecycle cannot be invoked at all.

    P6 removed `materialize`, `preflight`, `train`, `extend-seed`, `evaluate`,
    and `verify` together with the retired authorities they consumed, so the
    guard is now structural rather than a runtime redirect.
    """

    config, _workspace = _fixture_campaign(tmp_path)
    assert _run(config, "prepare") == 0
    for command in (
        "materialize", "preflight", "train", "extend-seed", "evaluate", "verify"
    ):
        with pytest.raises(SystemExit) as excinfo:
            _parse(config, command)
        assert excinfo.value.code == 2


def test_p4d_req4_only_select_target_size_can_schedule_the_screen(tmp_path: Path):
    parser = cli.build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert "select-target-size" in choices
    assert not ({"train", "evaluate", "materialize", "preflight"} & set(choices))


def test_p4d_req5_mace_run_configuration_is_translation_only():
    from mdstats.training_data.target_size_execution import (
        TARGET_SIZE_MACE_CONFIG_SCHEMA,
    )

    source = {
        "schema": TARGET_SIZE_MACE_CONFIG_SCHEMA,
        "name": "target-size-n8-seed1",
        "seed": 1,
        "target_train_file": "target_train.xyz",
        "target_valid_file": "harness_validation.xyz",
        "atomic_numbers": [3, 8],
        "E0s": {"3": -1.0, "8": -2.0},
        "energy_key": "REF_energy",
        "forces_key": "REF_forces",
        "stress_key": "REF_stress",
        "lr": 1.0e-4,
        "batch_size": 4,
        "max_num_epochs": 10,
        "default_dtype": "float64",
        "device": "cpu",
        "mace_architecture": {"num_channels": 16, "batch_size": 999},
    }
    translated = mace_run_configuration(source)
    assert translated["train_file"] == "target_train.xyz"
    assert translated["valid_file"] == "harness_validation.xyz"
    assert translated["seed"] == 1
    assert translated["num_channels"] == 16
    # The architecture never overrides an optimizer or data key.
    assert translated["batch_size"] == 4
    assert "schema" not in translated
    assert "target_train_file" not in translated

    with pytest.raises(Exception):
        mace_run_configuration({**source, "schema": "retired"})


def test_p4d_req6_no_version_prefixed_production_names():
    text = (_TRAINING_DATA / "campaign_target_size_runtime.py").read_text(
        encoding="utf-8"
    ).lower()
    assert "v7_" not in text
    assert "_v7" not in text
