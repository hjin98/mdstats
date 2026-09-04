"""P3 realized-MACE architecture identity: real TRAIN2 owner-boundary evidence.

The existing P3A4 real-MACE fixtures build their model with
``build_mace_model_from_configuration`` and then authenticate a checkpoint
saved from that same model.  That proves checkpoint/EMA/state handling but it
never executes pinned MACE's own pre-``configure_model`` training path, so it
cannot see MACE renaming the head to ``Default`` or replacing the configured
neighbor normalization from the candidate training loader.

These tests cross that owner boundary: real ``mace.cli.run_train`` builds the
model from the production candidate configuration, and the production EVAL2
authentication reconstructs from that same canonical configuration with no
architecture or provider override.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import mdstats
import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3e as p3e
from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.campaign_target_size_runtime import (
    MaceTargetSizeBoundaryTrainer,
    TargetSizeRungRequest,
    mace_run_configuration,
)
from mdstats.training_data.model_features import (
    build_mace_model_from_configuration,
    mace_candidate_architecture_defaults,
    mace_model_execution_architecture_digest,
)
from mdstats.training_data.target_size_execution import (
    bind_target_size_boundary_state,
    build_target_size_candidate_trajectory,
    build_target_size_eval2_role,
    materialize_target_size_candidate,
    project_target_size_candidate_preparation,
    promote_target_size_boundary_snapshot,
    run_target_size_direct_boundary_inference,
    target_size_rung_plan,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution.common import (
    build_target_size_common_preparation,
    fit_common_mace_neighbor_normalization,
)
from mdstats.training_data.target_size_execution.evaluation import (
    authenticate_train2_checkpoint_provider,
)

pytestmark = pytest.mark.slow


def _wrapper(tmp_path: Path) -> Path:
    """The real qualified ``mdstats-mace-train`` entry point, as production uses."""

    source_root = Path(mdstats.__file__).resolve().parents[1]
    path = tmp_path / "mdstats-mace-train"
    path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"sys.path.insert(0, {str(source_root)!r})\n"
        "from mdstats.training_data.critical_precision_cli import train_main\n"
        "raise SystemExit(train_main())\n",
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def _materialize(env, tmp_path: Path, *, target_size: int, optimizer_seed: int):
    definition = env["aggregate"].definition
    trajectory = build_target_size_candidate_trajectory(
        definition,
        env["context"],
        env["common"],
        env["schedule"],
        target_size=target_size,
        optimizer_policy=env["optimizer"],
        optimizer_seed=optimizer_seed,
    )
    projection = project_target_size_candidate_preparation(
        env["common"], definition, target_size
    )
    directory = tmp_path / f"materialization-n{target_size}-s{optimizer_seed}"
    directory.mkdir(parents=True, exist_ok=True)
    materialization = materialize_target_size_candidate(
        trajectory,
        projection,
        env["common"],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        output_directory=directory,
        optimizer_policy=env["optimizer"],
        extxyz_policy=env["authority"].extxyz_policy,
        frame_array_index=env["index"],
        mace_architecture=env["common"].realized_mace_architecture,
    )
    return trajectory, materialization, directory


def _train_real_boundary(env, tmp_path: Path, trajectory, materialization, directory):
    """Run one durable TRAIN2 boundary through the real pinned MACE trainer."""

    boundary = env["schedule"].fidelity_epochs[0]
    checkpoint_directory = tmp_path / f"train2-{trajectory.content_digest[:12]}"
    checkpoint_directory.mkdir(parents=True, exist_ok=True)
    plan = target_size_rung_plan(trajectory, env["schedule"], boundary_epoch=boundary)
    trainer = MaceTargetSizeBoundaryTrainer(wrapper_path=_wrapper(tmp_path))
    summary = trainer(
        TargetSizeRungRequest(
            plan=plan,
            trajectory=trajectory,
            materialization=materialization,
            materialization_directory=directory,
            checkpoint_directory=checkpoint_directory,
            start_epoch=0,
            optimizer_policy=env["optimizer"],
        )
    )
    return boundary, checkpoint_directory, summary


def _candidate_config(materialization, directory: Path) -> dict:
    return json.loads(
        (directory / materialization.mace_config_relative_path).read_text(
            encoding="utf-8"
        )
    )


def test_p3_real_train2_builds_the_canonical_target_head_and_common_normalization(
    tmp_path: Path,
):
    """Real MACE constructs ``target_head`` with the common fitted normalization.

    This is the exact production boundary the reported failure crossed: the
    candidate configuration is written by the real materialization owner, the
    real wrapper launches pinned MACE, and MACE's own head preparation and
    dataset loading run before ``configure_model``.
    """

    env = p3e._env(tmp_path, batch_size=1)
    common = env["common"]
    trajectory, materialization, directory = _materialize(
        env, tmp_path, target_size=2, optimizer_seed=1
    )
    _boundary, checkpoint_directory, summary = _train_real_boundary(
        env, tmp_path, trajectory, materialization, directory
    )

    log_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (checkpoint_directory.parent / "logs").glob("*")
        if path.is_file()
    )
    # MACE announces its own fallback namespace and its own recomputation; both
    # would mean a model P3 did not ask for.
    assert "Using heads: ['target_head']" in log_text
    assert "Using heads: ['Default']" not in log_text
    assert "Computing average number of neighbors" not in log_text
    assert (
        f"Average number of neighbors: {common.common_avg_num_neighbors}" in log_text
    )
    # The fitted value is genuinely the corpus's, not MACE's parser default.
    assert common.common_avg_num_neighbors != pytest.approx(
        mace_candidate_architecture_defaults()["avg_num_neighbors"]
    )

    # The architecture the real model reports is the one the canonical
    # configuration describes, not a value MACE derived from this candidate.
    assert summary.model_architecture_digest is not None
    config_payload = _candidate_config(materialization, directory)
    reconstructed = build_mace_model_from_configuration(config_payload)
    assert [str(v) for v in reconstructed.heads] == ["target_head"]
    assert all(
        float(interaction.avg_num_neighbors)
        == pytest.approx(common.common_avg_num_neighbors)
        for interaction in reconstructed.interactions
    )
    assert (
        mace_model_execution_architecture_digest(reconstructed)
        == summary.model_architecture_digest
    )


def test_p3_two_candidate_sizes_consume_one_common_normalization(tmp_path: Path):
    """``N`` changes data cardinality only; model construction is invariant."""

    env = p3e._env(tmp_path, batch_size=1)
    common = env["common"]
    digests = []
    for target_size in (2, 4):
        trajectory, materialization, directory = _materialize(
            env, tmp_path, target_size=target_size, optimizer_seed=1
        )
        _boundary, _checkpoints, summary = _train_real_boundary(
            env, tmp_path, trajectory, materialization, directory
        )
        payload = _candidate_config(materialization, directory)
        assert payload["mace_architecture"]["avg_num_neighbors"] == (
            common.common_avg_num_neighbors
        )
        assert payload["compute_avg_num_neighbors"] is False
        digests.append(summary.model_architecture_digest)
    # Different training memberships, one realized execution architecture.
    assert digests[0] == digests[1]


def test_p3_authenticated_eval2_accepts_the_real_train2_model(tmp_path: Path):
    """Production EVAL2 authentication accepts the real TRAIN2 architecture.

    No architecture override, no provider override, and no checkpoint-derived
    architecture: the canonical candidate configuration alone must reconstruct
    the model pinned MACE actually trained.
    """

    env = p3e._env(tmp_path, batch_size=1)
    definition = env["aggregate"].definition
    trajectory, materialization, directory = _materialize(
        env, tmp_path, target_size=2, optimizer_seed=1
    )
    boundary, checkpoint_directory, summary = _train_real_boundary(
        env, tmp_path, trajectory, materialization, directory
    )
    boundary_state = bind_target_size_boundary_state(
        trajectory, env["schedule"], summary, checkpoint_directory=checkpoint_directory
    )
    snapshot = promote_target_size_boundary_snapshot(
        trajectory,
        boundary_state,
        checkpoint_directory=checkpoint_directory,
        snapshot_root=env["root"],
    )
    evaluation_directory = tmp_path / "evaluation"
    evaluation_directory.mkdir(parents=True, exist_ok=True)
    evaluation_data = write_target_size_evaluation_artifact(
        evaluation_directory,
        definition=definition,
        evaluation_size=definition.policy.evaluation_sizes[0],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )
    role = build_target_size_eval2_role(
        trajectory=trajectory,
        boundary_state=snapshot,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=env["blocks"],
        evaluation_data=evaluation_data,
    )
    evidence = run_target_size_direct_boundary_inference(
        trajectory=trajectory,
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=evaluation_data,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        materialization_directory=directory,
        snapshot_root=env["root"],
        evaluation_directory=evaluation_directory,
        root_directory=env["root"],
        extxyz_policy=env["authority"].extxyz_policy,
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )
    # A real CPU forward through the production provider actually ran.
    assert evidence.device == "cpu"
    assert evidence.prediction_count == len(evidence.predictions) > 0
    for entry in evidence.predictions:
        assert np.isfinite(entry.energy_ev)
        assert np.all(np.isfinite(np.asarray(entry.forces_ev_per_angstrom)))


def test_p3_default_head_train2_model_cannot_authenticate(tmp_path: Path):
    """A ``Default``-head TRAIN2 model is rejected against the P3 configuration.

    This is the pre-repair realization.  It must fail on architecture identity
    before any checkpoint state can control inference.
    """

    env = p3e._env(tmp_path, batch_size=1)
    trajectory, materialization, directory = _materialize(
        env, tmp_path, target_size=2, optimizer_seed=1
    )
    _boundary, checkpoint_directory, summary = _train_real_boundary(
        env, tmp_path, trajectory, materialization, directory
    )
    config_payload = _candidate_config(materialization, directory)
    fallback = {
        **config_payload,
        "mace_architecture": {
            **config_payload["mace_architecture"],
            "heads": ["Default"],
        },
    }
    # The canonical architecture owner refuses a non-P3 head namespace outright.
    with pytest.raises(TrainingDataInputError):
        build_mace_model_from_configuration(fallback)

    # And a candidate-local normalization is a different architecture, so the
    # persisted real-TRAIN2 digest no longer matches.
    drifted = {
        **config_payload,
        "mace_architecture": {
            **config_payload["mace_architecture"],
            "avg_num_neighbors": (
                float(config_payload["mace_architecture"]["avg_num_neighbors"]) + 1.0
            ),
        },
    }
    assert mace_model_execution_architecture_digest(
        build_mace_model_from_configuration(drifted)
    ) != summary.model_architecture_digest


def test_p3_common_normalization_is_fitted_over_p_train_only(tmp_path: Path):
    """The normalization is a study-wide constant fitted over the exact P_train."""

    manifest, _fa, _nb, aggregate, common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _ = p3a._frame_arrays(tmp_path, manifest)
    architecture = p3a.fixture_mace_architecture()

    expected = fit_common_mace_neighbor_normalization(
        frames,
        frame_data_by_run,
        aggregate.split.training_frame_uids,
        r_max=float(architecture["r_max"]),
        frame_array_index=index,
    )
    assert common.common_avg_num_neighbors == pytest.approx(expected)
    # Deterministic for a fixed membership and architecture identity.
    assert expected == fit_common_mace_neighbor_normalization(
        frames,
        frame_data_by_run,
        aggregate.split.training_frame_uids,
        r_max=float(architecture["r_max"]),
        frame_array_index=index,
    )
    # A candidate subset is not the fit membership: T_N would give a different
    # value, which is exactly the candidate-local drift P3 forbids.
    subset = tuple(aggregate.split.training_frame_uids)[:2]
    candidate_value = fit_common_mace_neighbor_normalization(
        frames,
        frame_data_by_run,
        subset,
        r_max=float(architecture["r_max"]),
        frame_array_index=index,
    )
    assert isinstance(candidate_value, float)

    # Changing the common normalization changes the whole P3 execution identity.
    widened = dict(architecture)
    widened["r_max"] = float(architecture["r_max"]) + 1.0
    other = build_target_size_common_preparation(
        aggregate,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=index,
        mace_architecture=widened,
    )
    assert other.content_digest != common.content_digest


def test_p3_pre_repair_executable_shape_reproduces_the_reported_mismatch(
    tmp_path: Path,
):
    """The superseded executable projection still produces the reported failure.

    Running real MACE with no dataset-head mapping and with candidate-local
    average-neighbor recomputation -- the shape this repair replaced -- makes
    pinned MACE build head ``Default`` with a normalization derived from this
    candidate's loader, and the canonical reconstruction therefore reports a
    different execution architecture.
    """

    env = p3e._env(tmp_path, batch_size=1)
    trajectory, materialization, directory = _materialize(
        env, tmp_path, target_size=2, optimizer_seed=1
    )
    config_payload = _candidate_config(materialization, directory)
    run_config = mace_run_configuration(config_payload)
    # Exactly the superseded projection: no `--heads`, MACE recomputes.
    run_config.pop("heads")
    run_config["compute_avg_num_neighbors"] = True
    # A distinctive configured normalization makes MACE's replacement of it
    # observable independently of what this bounded corpus happens to average.
    run_config["avg_num_neighbors"] = 7.5

    work = tmp_path / "pre-repair"
    work.mkdir(parents=True, exist_ok=True)
    config_path = work / "mace_run_config.yaml"
    config_path.write_text(
        json.dumps(run_config, indent=2, sort_keys=True), encoding="utf-8"
    )
    probe = work / "probe.py"
    probe.write_text(
        "import json, sys\n"
        f"sys.path.insert(0, {str(Path(mdstats.__file__).resolve().parents[1])!r})\n"
        "import mace.cli.run_train as rt\n"
        "from mace.tools import build_default_arg_parser\n"
        "from mdstats.training_data.model_features import (\n"
        "    mace_model_execution_architecture_digest,\n"
        ")\n"
        "captured = {}\n"
        "real = rt.configure_model\n"
        "def spy(args, train_loader, atomic_energies, model_foundation=None,\n"
        "        heads=None, z_table=None, head_configs=None):\n"
        "    model, out = real(args, train_loader, atomic_energies,\n"
        "                      model_foundation, heads, z_table, head_configs)\n"
        "    captured['heads'] = [str(v) for v in model.heads]\n"
        "    captured['avg'] = float(args.avg_num_neighbors)\n"
        "    captured['digest'] = mace_model_execution_architecture_digest(model)\n"
        "    raise SystemExit('captured')\n"
        "rt.configure_model = spy\n"
        "try:\n"
        "    rt.run(build_default_arg_parser().parse_args(['--config', sys.argv[1]]))\n"
        "except SystemExit as exc:\n"
        "    if str(exc) != 'captured':\n"
        "        raise\n"
        "print(json.dumps(captured))\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [sys.executable, str(probe), str(config_path)],
        cwd=str(directory),
        env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
        capture_output=True,
        text=True,
        check=True,
    )
    observed = json.loads(completed.stdout.strip().splitlines()[-1])

    # Both reported drifts reproduce under the superseded shape: MACE renames
    # the head to its own fallback, and it discards the configured
    # normalization in favour of one derived from this candidate's loader.
    assert observed["heads"] == ["Default"]
    assert observed["avg"] != pytest.approx(7.5)
    # ...and they are exactly what made authenticated EVAL2 reject the model.
    canonical = mace_model_execution_architecture_digest(
        build_mace_model_from_configuration(config_payload)
    )
    assert observed["digest"] != canonical
