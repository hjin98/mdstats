"""Assembled real-MACE evidence for the reopened P5 execution seam."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

import mdstats
import tests.test_mlff_target_size_p3_realized_mace_architecture as p3_real
import tests.test_mlff_target_size_mace_objective_realization as objective_real
import tests.test_mlff_neutral_scientific_substrate as neutral_fixtures
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
)
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data.campaign_post_selection_runtime import (
    _resolve_post_selection_replay_resolution,
    _component_block_ids,
    _optimizer_policy_for,
    build_post_selection_context,
    execute_post_selection_run,
    resolve_post_selection_evaluation_model_state,
)
from mdstats.training_data.bounded_inference import execution_batch_width
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
    DATASET_ROLE_CHECKPOINT_MONITOR,
    authenticate_post_selection_provider,
    evaluate_post_selection_dataset,
    PostSelectionMaterialization,
    post_selection_mace_run_configuration,
)
from mdstats.training_data.model_features import (
    build_mace_model_from_configuration,
    mace_model_execution_architecture_digest,
)
from mdstats.training_data.train2_runtime import (
    load_train2_runtime_boundary_summary,
    load_train2_runtime_summary,
)
from mdstats.training_data.target_size_execution.evaluation import (
    EVALUATION_MODEL_STATE_EMA,
    EVALUATION_MODEL_STATE_LIVE,
)
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


@pytest.mark.parametrize("mode", ["scratch", "naive_fine_tuning"])
def test_p5_real_nonreplay_reconstructs_default_head_and_authenticates_eval2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """Ordinary P5 modes use MACE's real ``Default`` checkpoint namespace.

    The P3 architecture projection remains ``target_head``; this exercises the
    downstream P5 materialization, real wrapper/trainer, raw checkpoint
    authentication, and bounded EVAL2 provider path that must instead rebuild
    MACE's ordinary one-head ``Default`` model.
    """

    foundation = tmp_path / "foundation.model"
    if mode == "naive_fine_tuning":
        _write_tiny_mace_foundation(foundation)

    config_text = fixture_config_text()
    if mode == "naive_fine_tuning":
        config_text = config_text.replace(
            'training_root = "{training_root}"',
            "\n".join(
                (
                    'training_root = "{training_root}"',
                    f'foundation_model = "{foundation}"',
                    'foundation_head = "default"',
                )
            ),
        )
    config_text = config_text.replace("partition_seed = 7", "partition_seed = 2", 1)
    config_text = config_text.replace(
        "batch_size = 4",
        "batch_size = 1\nlearning_rate = 0.0123\nema = false",
        1,
    )
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
        assert context.method.training_mode == mode
        projection = build_selected_relation_projection(context.selected)
        cv_plan = build_post_selection_cv_plan(
            context.selected,
            context.method,
            context.cv_policy,
            projection=projection,
            replay_lineage_digest=None,
        )
        fold = cv_plan.fold(0)
        run_plan = build_cv_fold_run_plan(
            cv_plan,
            fold_index=fold.fold_index,
            optimizer_seed=context.cv_policy.required_cv_seeds[0],
            planned_epochs=context.cv_policy.cv_max_num_epochs,
        )
        execute_post_selection_run(
            context,
            run_plan=run_plan,
            budget_policy=cv_training_budget_policy(context.method, context.cv_policy),
            training_frame_uids=fold.training_frame_uids,
            monitor_frame_uids=fold.checkpoint_monitor_frame_uids,
            outer_evaluation_frame_uids=None,
        )

        run_root = context.run_root(run_plan.run_identity)
        checkpoint_root = run_root / "checkpoints"
        summary = load_train2_runtime_summary(checkpoint_root)
        assert summary.mace_execution_evidence is not None
        assert summary.mace_execution_evidence["multiheads_finetuning"] is False
        assert summary.mace_execution_evidence["learning_rate"] == pytest.approx(
            0.0123
        )

        materialization = PostSelectionMaterialization.from_dict(
            json.loads(
                (
                    run_root
                    / "materialization"
                    / "materialization.json"
                ).read_text(encoding="utf-8")
            )
        )
        config_payload = json.loads(
            (
                run_root
                / "materialization"
                / materialization.mace_config_relative_path
            ).read_text(encoding="utf-8")
        )
        assert config_payload["schema"] == "mdstats.post-selection-mace-config.v2"
        assert "heads" not in config_payload
        assert config_payload["E0s"]
        executable = post_selection_mace_run_configuration(config_payload)
        assert executable["multiheads_finetuning"] is False
        model_shell = build_mace_model_from_configuration(config_payload)
        import torch

        shell_e0s = torch.as_tensor(
            model_shell.atomic_energies_fn.atomic_energies
        ).reshape(-1)
        expected_e0s = torch.tensor(
            [
                float(config_payload["E0s"][str(z)])
                for z in sorted(int(value) for value in config_payload["atomic_numbers"])
            ],
            dtype=shell_e0s.dtype,
        )
        assert torch.allclose(shell_e0s, expected_e0s)
        raw_checkpoints = sorted(
            path
            for path in checkpoint_root.glob("*.pt")
            if "epoch-" in path.name and path.name != "train2_runtime.pt"
        )
        assert raw_checkpoints
        raw_checkpoint = raw_checkpoints[-1]
        provider, _evaluated = authenticate_post_selection_provider(
            materialization=materialization,
            materialization_directory=run_root / "materialization",
            checkpoint_directory=checkpoint_root,
            checkpoint_name=raw_checkpoint.name,
            checkpoint_sha256=hashlib.sha256(raw_checkpoint.read_bytes()).hexdigest(),
            summary=summary,
            evaluation_model_state=resolve_post_selection_evaluation_model_state(
                context,
                seed=run_plan.optimizer_seed,
                planned_epochs=run_plan.planned_epochs,
            ),
            allow_forward_override=False,
            checkpoint_epoch=summary.raw_checkpoint_epoch,
        )
        assert tuple(str(value) for value in provider.model.heads) == ("Default",)
        assert (
            mace_model_execution_architecture_digest(provider.model)
            == summary.model_architecture_digest
        )
        optimizer_policy = _optimizer_policy_for(
            context,
            seed=run_plan.optimizer_seed,
            planned_epochs=run_plan.planned_epochs,
        )
        monitor_metrics = evaluate_post_selection_dataset(
            run_plan=run_plan,
            artifact=materialization.checkpoint_monitor_artifact,
            dataset_role=DATASET_ROLE_CHECKPOINT_MONITOR,
            root_directory=run_root / "materialization",
            provider=provider,
            block_ids=_component_block_ids(
                context.selected, fold.checkpoint_monitor_frame_uids
            ),
            execution_batch_width=execution_batch_width(optimizer_policy),
            extxyz_policy=context.method_policies.extxyz,
            inference_evaluator=None,
        )
        assert monitor_metrics is not None
    finally:
        store.close()


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
        numerical_harness = PostSelectionHarness(
            run_force_offsets={"epoch-0": 1.0e-4, "epoch-1": 2.0e-2}
        )
        evaluated_checkpoint_names: list[str] = []

        def evaluate_with_checkpoint_record(provider, atoms_list):
            locator = getattr(
                getattr(provider, "checkpoint_identity", None),
                "checkpoint_locator",
                "",
            )
            evaluated_checkpoint_names.append(Path(str(locator)).name)
            return numerical_harness.evaluate(provider, atoms_list)

        context = build_post_selection_context(
            cfg,
            paths,
            store,
            inference_evaluator=evaluate_with_checkpoint_record,
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
            outer_evaluation_frame_uids=fold.outer_evaluation_frame_uids,
        )
        assert _outer_metrics is not None
        assert evidence.outer_metric_record_digest == _outer_metrics.content_digest

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

        checkpoint_root = run_root / "checkpoints"
        raw_checkpoints = sorted(
            path
            for path in checkpoint_root.glob("*.pt")
            if "epoch-" in path.name and path.name != "train2_runtime.pt"
        )
        assert len(raw_checkpoints) >= 2
        assert [
            path.name for path in checkpoint_root.glob("train2_runtime*.pt")
        ] == ["train2_runtime.pt"]
        assert not list(checkpoint_root.glob("train2_runtime_epoch-*.pt"))
        assert len(list(checkpoint_root.glob("train2_runtime_epoch-*.json"))) >= 2
        earliest_checkpoint = raw_checkpoints[0]
        earliest_epoch = int(re.search(r"epoch-(\d+)", earliest_checkpoint.name).group(1))
        earliest_boundary = load_train2_runtime_boundary_summary(
            checkpoint_root, earliest_epoch
        )
        earliest_sha = hashlib.sha256(earliest_checkpoint.read_bytes()).hexdigest()
        assert evidence.representative_checkpoint_sha256 == earliest_sha
        # The final inference call made by the real P5 owner is the held-out
        # outer evaluation.  Its provider must therefore be the same earlier
        # native checkpoint that monitor selection froze.
        assert evaluated_checkpoint_names[-1] == earliest_checkpoint.name
        assert earliest_boundary.raw_checkpoint_sha256 == earliest_sha
        for field in (
            "plan_digest",
            "training_protocol_digest",
            "optimizer_policy_digest",
            "budget_policy_digest",
            "lr_policy_digest",
            "model_architecture_digest",
            "mace_execution_evidence",
        ):
            assert getattr(earliest_boundary, field) == getattr(summary, field)

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
        assert config_payload["lr"] == pytest.approx(0.0123)
        assert config_payload["ema"] is True
        assert config_payload["ema_decay"] == pytest.approx(0.87)
        executable = post_selection_mace_run_configuration(config_payload)
        assert executable["force_mh_ft_lr"] is True
        assert executable["real_pt_data_ratio_threshold"] == 0.0
        assert executable["lr"] == pytest.approx(0.0123)
        assert executable["ema"] is True
        assert executable["ema_decay"] == pytest.approx(0.87)
        assert (
            mace_evidence["learning_rate"] == pytest.approx(0.0123)
        )
        assert mace_evidence["ema"] is True
        assert mace_evidence["ema_decay"] == pytest.approx(0.87)
        assert (
            mace_evidence["target_train_count"] / mace_evidence["replay_train_count"]
            < 0.1
        )

        earlier_provider, earlier_digest = authenticate_post_selection_provider(
            materialization=materialization,
            materialization_directory=run_root / "materialization",
            checkpoint_directory=checkpoint_root,
            checkpoint_name=earliest_checkpoint.name,
            checkpoint_sha256=earliest_sha,
            summary=summary,
            evaluation_model_state=EVALUATION_MODEL_STATE_EMA,
            allow_forward_override=False,
            checkpoint_epoch=earliest_epoch,
        )
        assert earlier_provider.model is not None
        assert earlier_digest

        # A native EMA checkpoint cannot be admitted as historical live state,
        # even when the bounded numerical forward seam is present.  This is the
        # counterfactual that distinguishes the real P5 owner from the old
        # broad override exception.
        for allow_forward_override in (False, True):
            with pytest.raises(
                TrainingDataInputError,
                match="earlier TRAIN2 checkpoint saved with EMA",
            ):
                authenticate_post_selection_provider(
                    materialization=materialization,
                    materialization_directory=run_root / "materialization",
                    checkpoint_directory=checkpoint_root,
                    checkpoint_name=earliest_checkpoint.name,
                    checkpoint_sha256=earliest_sha,
                    summary=summary,
                    evaluation_model_state=EVALUATION_MODEL_STATE_LIVE,
                    allow_forward_override=allow_forward_override,
                    checkpoint_epoch=earliest_epoch,
                )

        # Reuse the exact native checkpoint through the P7 qualification owner,
        # including its policy-derived EMA state.  ``predict_all`` keeps the
        # existing accepted numerical seam below that owner while proving the
        # member provider actually supplies the authenticated model.
        from mdstats.training_data.qualification.providers import (
            member_provider,
            predict_all,
        )
        from mdstats.training_data.qualification.publication import (
            PublishedProductionMember,
        )

        member = PublishedProductionMember(
            optimizer_seed=run_plan.optimizer_seed,
            run_identity=run_plan.run_identity,
            run_plan_digest=run_plan.content_digest,
            run_evidence_digest=evidence.content_digest,
            representative_candidate_identity=evidence.representative_candidate_identity,
            representative_checkpoint_sha256=earliest_sha,
            checkpoint_relative_path=earliest_checkpoint.name,
            target_head_name=context.method_policies.target_head_name,
        )

        boundary_path = checkpoint_root / f"train2_runtime_epoch-{earliest_epoch}.json"
        boundary_bytes = boundary_path.read_bytes()
        tampered_boundary = json.loads(boundary_bytes.decode("utf-8"))
        tampered_boundary["raw_checkpoint_sha256"] = "0" * 64
        boundary_path.write_text(
            json.dumps(tampered_boundary, indent=2, sort_keys=True), encoding="utf-8"
        )
        try:
            with pytest.raises(TrainingDataSerializationError):
                authenticate_post_selection_provider(
                    materialization=materialization,
                    materialization_directory=run_root / "materialization",
                    checkpoint_directory=checkpoint_root,
                    checkpoint_name=earliest_checkpoint.name,
                    checkpoint_sha256=earliest_sha,
                    summary=summary,
                    evaluation_model_state=EVALUATION_MODEL_STATE_EMA,
                    allow_forward_override=False,
                    checkpoint_epoch=earliest_epoch,
                )
        finally:
            boundary_path.write_bytes(boundary_bytes)

        raw_checkpoint_bytes = earliest_checkpoint.read_bytes()
        earliest_checkpoint.write_bytes(
            raw_checkpoint_bytes[:-1]
            + bytes([raw_checkpoint_bytes[-1] ^ 1])
        )
        try:
            with pytest.raises(TrainingDataInputError):
                authenticate_post_selection_provider(
                    materialization=materialization,
                    materialization_directory=run_root / "materialization",
                    checkpoint_directory=checkpoint_root,
                    checkpoint_name=earliest_checkpoint.name,
                    checkpoint_sha256=earliest_sha,
                    summary=summary,
                    evaluation_model_state=EVALUATION_MODEL_STATE_EMA,
                    allow_forward_override=False,
                    checkpoint_epoch=earliest_epoch,
                )
        finally:
            earliest_checkpoint.write_bytes(raw_checkpoint_bytes)

        from ase.io import read

        target_path = (
            run_root
            / "materialization"
            / materialization.target_train_artifact.relative_path
        )
        target_frames = read(target_path, index=":", format="extxyz")
        assert target_frames
        with member_provider(context, member) as qualification_provider:
            assert qualification_provider.checkpoint_identity.checkpoint_locator.endswith(
                earliest_checkpoint.name
            )
            predictions = predict_all(context, qualification_provider, target_frames[:1])
            assert len(predictions) == 1
        assert evaluated_checkpoint_names[-1] == earliest_checkpoint.name
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
