"""Assembled real-MACE evidence for the reopened P5 execution seam."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import mdstats
import tests.test_mlff_target_size_p3_realized_mace_architecture as p3_real
import tests.test_mlff_target_size_mace_objective_realization as objective_real
import tests.test_mlff_neutral_scientific_substrate as neutral_fixtures
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data.campaign_post_selection_runtime import (
    _resolve_post_selection_replay_resolution,
    build_post_selection_context,
    execute_post_selection_run,
)
from mdstats.training_data.post_selection_cv_plan import (
    build_cv_fold_run_plan,
    build_post_selection_cv_plan,
    build_selected_relation_projection,
)
from mdstats.training_data.post_selection_identity import (
    compute_replay_lineage_digest,
    cv_training_budget_policy,
)
from mdstats.training_data.post_selection_execution import (
    PostSelectionMaterialization,
    post_selection_mace_run_configuration,
)
from mdstats.training_data.train2_runtime import load_train2_runtime_summary
from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    fixture_config_text,
    load_context,
)
from tests.test_mlff_target_size_p5_r9_guards import (
    _write_replay_file,
    _write_tiny_mace_foundation,
)


pytestmark = pytest.mark.slow


def _two_condition_data4_bundle(
    training_root: Path,
    *,
    regime: str | None = "production",
    elements: tuple[str, ...] = ("Li", "O"),
    **_ignored,
):
    """Build the same real P1--P3 inputs with two temperature conditions."""

    for run_id, tebeg, position_offset in (
        ("run-a", 700, 0.0),
        ("run-b", 900, 0.05),
    ):
        neutral_fixtures._write(
            training_root,
            run_id,
            elements,
            n_frames=48,
            force_event_frame=8,
            tebeg=tebeg,
            position_offset=position_offset,
        )
    assertions = () if regime is None else (("regime", regime),)
    manifest = mdstats.TrainingDataManifest(
        dataset_id="neutral-p1",
        system_profile="generic",
        runs=tuple(
            mdstats.TrainingDataRunSpec(
                run_id=run_id,
                vasprun=f"{run_id}/vasprun.xml",
                reference_group="bulk",
                assertions=assertions,
            )
            for run_id in ("run-a", "run-b")
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
    return manifest, sources, frames, data4


def test_p5_real_replay_run_crosses_materialization_native_mace_and_train2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One real P5 fold proves exported semantics reach native MACE and TRAIN2.

    The P4 screen remains the established bounded fixture seam.  P5 itself is
    assembled through the real selected context, replay resolver, materializer,
    qualified wrapper, pinned MACE ``run_train``, native optimizer, and durable
    TRAIN2 summary.  Only EVAL2 prediction numbers use the existing bounded
    evaluator below the P5 owner boundary.
    """

    root = tmp_path / "inputs"
    foundation = root / "foundation.model"
    pseudo_train = root / "replay-pseudo-train.extxyz"
    pseudo_monitor = root / "replay-pseudo-monitor.extxyz"
    true_root = root / "true-replay"
    true_train = true_root / "true_labels" / "replay_train.extxyz"
    true_monitor = true_root / "true_labels" / "replay_monitor.extxyz"
    foundation.parent.mkdir(parents=True, exist_ok=True)
    _write_tiny_mace_foundation(foundation)
    _write_replay_file(pseudo_train, list(range(60)), energy_offset=0.25)
    _write_replay_file(pseudo_monitor, [60, 61], energy_offset=0.25)
    _write_replay_file(true_train, list(range(60)), energy_offset=0.0)
    _write_replay_file(true_monitor, [60, 61], energy_offset=0.0)

    config_text = fixture_config_text()
    config_text = config_text.replace(
        'training_root = "{training_root}"',
        "\n".join(
            (
                'training_root = "{training_root}"',
                f'foundation_model = "{foundation}"',
                f'replay_train = "{pseudo_train}"',
                f'replay_monitor = "{pseudo_monitor}"',
                f'replay_true_labels = "{true_root}"',
            )
        ),
    )
    config_text = config_text.replace(
        "batch_size = 4",
        "batch_size = 4\nlearning_rate = 0.0123\nema = true\nema_decay = 0.87",
        1,
    )
    config_text = config_text.replace(
        "seeds = [1, 2]",
        "seeds = [1, 2]\nmode = \"multihead_replay\"",
        1,
    )
    # Partition seed 2 assigns the selected two-frame split-exclusion
    # component to gradient training in one fold.  That keeps the assembled
    # path representative of production weight fitting: a one-frame fold is
    # correctly mean-normalized to 1.0 and cannot prove a non-unit export.
    config_text = config_text.replace("partition_seed = 7", "partition_seed = 2", 1)
    config_text += """

[objective]
energy_weight = 2.0
forces_weight = 7.0
stress_weight = 3.0

[replay]
mode = "external_pseudolabel"
seed = 42
allow_small_corpus = true
minimum_train_configurations = 1
minimum_monitor_configurations = 1
require_target_elements = false

[foundation]
family = "mace_mpa_0"
head = "default"
legacy_normalized = true
"""

    config, _workspace = build_selected_campaign(
        tmp_path / "campaign",
        config_text=config_text,
        data4_bundle=_two_condition_data4_bundle,
    )
    monkeypatch.setattr(
        cli,
        "_ensure_local_wrappers",
        lambda _paths: {"mdstats-mace-train": p3_real._wrapper(tmp_path)},
    )

    cfg, paths, store = load_context(config)
    try:
        context = build_post_selection_context(
            cfg,
            paths,
            store,
            inference_evaluator=PostSelectionHarness().evaluate,
        )
        assert context.method.training_mode == "multihead_replay"
        resolution = _resolve_post_selection_replay_resolution(context)
        assert resolution is not None
        assert resolution.train_artifact.configuration_count == 60
        assert resolution.monitor_artifact.configuration_count == 2

        projection = build_selected_relation_projection(context.selected)
        replay_lineage_digest = compute_replay_lineage_digest(resolution)
        cv_plan = build_post_selection_cv_plan(
            context.selected,
            context.method,
            context.cv_policy,
            projection=projection,
            replay_lineage_digest=replay_lineage_digest,
        )
        fold = cv_plan.fold(0)
        run_plan = build_cv_fold_run_plan(
            cv_plan,
            fold_index=fold.fold_index,
            optimizer_seed=context.cv_policy.required_cv_seeds[0],
            planned_epochs=context.cv_policy.cv_max_num_epochs,
        )
        evidence, _representative, _outer_metrics = execute_post_selection_run(
            context,
            run_plan=run_plan,
            budget_policy=cv_training_budget_policy(context.method, context.cv_policy),
            training_frame_uids=fold.training_frame_uids,
            monitor_frame_uids=fold.checkpoint_monitor_frame_uids,
            outer_evaluation_frame_uids=None,
        )

        run_root = context.run_root(run_plan.run_identity)
        summary = load_train2_runtime_summary(run_root / "checkpoints")
        assert summary.completed_updates > 0
        assert summary.completed_updates == (
            summary.completed_epochs * summary.updates_per_epoch
        )
        mace_evidence = summary.mace_execution_evidence
        assert mace_evidence is not None
        assert mace_evidence["loss_class"] == (
            "mace.modules.loss.WeightedEnergyForcesStressLoss"
        )
        assert mace_evidence["multiheads_finetuning"] is True
        assert mace_evidence["force_mh_ft_lr"] is True
        assert mace_evidence["real_pt_data_ratio_threshold"] == 0.0
        assert mace_evidence["target_duplication_factor"] == 1
        assert mace_evidence["replay_train_count"] == 60
        assert mace_evidence["target_train_count"] == len(fold.training_frame_uids)

        materialization_path = run_root / "materialization" / "materialization.json"
        materialization = PostSelectionMaterialization.from_dict(
            json.loads(materialization_path.read_text(encoding="utf-8"))
        )
        config_payload = json.loads(
            (
                run_root
                / "materialization"
                / materialization.mace_config_relative_path
            ).read_text(encoding="utf-8")
        )
        assert config_payload["energy_weight"] == 2.0
        assert config_payload["forces_weight"] == 7.0
        assert config_payload["stress_weight"] == 3.0
        executable = post_selection_mace_run_configuration(config_payload)
        assert executable["force_mh_ft_lr"] is True
        assert executable["real_pt_data_ratio_threshold"] == 0.0

        from ase.io import read

        target_path = (
            run_root
            / "materialization"
            / materialization.target_train_artifact.relative_path
        )
        target_frames = read(target_path, index=":", format="extxyz")
        assert target_frames
        assert any(
            float(frame.info["config_weight"]) != pytest.approx(1.0)
            for frame in target_frames
        )
        assert all(float(frame.info["config_energy_weight"]) > 0.0 for frame in target_frames)
        assert all(float(frame.info["config_forces_weight"]) > 0.0 for frame in target_frames)
        assert all(float(frame.info["config_stress_weight"]) > 0.0 for frame in target_frames)
        assert any(
            float(frame.info["config_weight"]) != pytest.approx(1.0)
            for frame in target_frames
        )

        # Feed that exact production-exported batch to MACE's own parser,
        # resolver, and native loss.  This companion oracle keeps the global
        # E/F/S coefficients distinct from the local configuration weights
        # without replacing the real trainer integration above.
        parsed = objective_real._parse_with_pinned_mace(
            executable, run_root / "materialization"
        )
        loss_fn = objective_real._loss_from_pinned_mace(parsed)
        assert float(loss_fn.energy_weight) == pytest.approx(2.0)
        assert float(loss_fn.forces_weight) == pytest.approx(7.0)
        assert float(loss_fn.stress_weight) == pytest.approx(3.0)
        batch = objective_real._batch_from_exported_atoms(tuple(target_frames))
        prediction = {
            "energy": batch["energy"] + 0.3,
            "forces": batch["forces"] + 0.05,
            "stress": batch["stress"] + 0.02,
        }
        observed_loss = float(loss_fn(ref=batch, pred=prediction, ddp=False))
        atoms_per_config = batch.ptr[1:] - batch.ptr[:-1]
        expected_energy = objective_real.torch.mean(
            batch.weight
            * batch.energy_weight
            * objective_real.torch.square(
                (batch["energy"] - prediction["energy"]) / atoms_per_config
            )
        )
        repeated_weight = objective_real.torch.repeat_interleave(
            batch.weight, atoms_per_config
        ).unsqueeze(-1)
        repeated_forces_weight = objective_real.torch.repeat_interleave(
            batch.forces_weight, atoms_per_config
        ).unsqueeze(-1)
        expected_forces = objective_real.torch.mean(
            repeated_weight
            * repeated_forces_weight
            * objective_real.torch.square(batch["forces"] - prediction["forces"])
        )
        expected_stress = objective_real.torch.mean(
            batch.weight.view(-1, 1, 1)
            * batch.stress_weight.view(-1, 1, 1)
            * objective_real.torch.square(batch["stress"] - prediction["stress"])
        )
        expected_loss = 2.0 * expected_energy + 7.0 * expected_forces + 3.0 * expected_stress
        assert observed_loss == pytest.approx(float(expected_loss))
        assert evidence.runtime_summary_digest == summary.content_digest
    finally:
        store.close()
