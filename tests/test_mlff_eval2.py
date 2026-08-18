from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import mdstats
from mdstats.training_data.model_features import AtomicModelPrediction

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
D6 = "6" * 64


def point(epoch: int, score: float, *, refinement: bool = False, sha: str | None = None) -> mdstats.Eval2TrajectoryPoint:
    if sha is None:
        sha = f"{epoch + 1:064x}"[-64:]
    return mdstats.Eval2TrajectoryPoint(
        epoch=epoch,
        checkpoint_sha256=sha,
        lightweight_target_score_ev_per_angstrom=score,
        normalized_schedule_progress=0.85 if refinement else 0.50,
        instantaneous_learning_rate=1e-5 if refinement else 1e-4,
        phase="refinement" if refinement else "adaptation",
        runtime_summary_digest=D1,
        stable_candidate_identity=f"epoch-{epoch}:{sha}",
    )


def target_metrics(
    rmse: float,
    *,
    blocks: int = 12,
    secondary: float | None = None,
    pred_digest: str = D2,
) -> mdstats.Eval2TargetMetricRecord:
    components = 30
    block_metrics = tuple(
        mdstats.Eval2TargetBlockMetric(
            block_id=f"block-{i:02d}",
            force_squared_error_sum=(rmse**2) * components,
            force_component_count=components,
            configuration_count=1,
        )
        for i in range(blocks)
    )
    sec = rmse if secondary is None else secondary
    return mdstats.Eval2TargetMetricRecord(
        configuration_count=blocks,
        atom_count=blocks * 10,
        energy_mae_ev_per_atom=0.001,
        relative_energy_rmse_ev_per_atom=0.0005,
        force_component_rmse_ev_per_angstrom=rmse,
        species_macro_force_rmse_ev_per_angstrom=sec,
        species_force_rmse_ev_per_angstrom=(("Na", sec),),
        force_error_p90_ev_per_angstrom=sec,
        force_error_p95_ev_per_angstrom=sec,
        force_error_p99_ev_per_angstrom=sec,
        worst_stratum_force_rmse_ev_per_angstrom=sec,
        stratum_force_rmse_ev_per_angstrom=(("species:Na", sec),),
        stress_rmse_ev_per_angstrom3=None,
        block_metrics=block_metrics,
        target_role_digest=D1,
        prediction_digest=pred_digest,
    )


def checkpoint(
    p: mdstats.Eval2TrajectoryPoint,
    rmse: float,
    *,
    replay: float = 0.020,
    baseline: float = 0.020,
    secondary: float | None = None,
    policy: mdstats.CheckpointAdmissibilityPolicy | None = None,
    blocks: int = 12,
) -> mdstats.Eval2CheckpointRecord:
    policy = policy or mdstats.CheckpointAdmissibilityPolicy()
    return mdstats.assess_eval2_checkpoint(
        p,
        evaluation_record_digest=D3,
        target_metrics=target_metrics(rmse, blocks=blocks, secondary=secondary),
        admissibility_policy=policy,
        replay_candidate_force_rmse_ev_per_angstrom=replay,
        replay_foundation_force_rmse_ev_per_angstrom=baseline,
        replay_label_mode="true_dft",
    )


def test_eval2_shortlist_is_three_overall_plus_two_refinement_and_has_no_replay_input():
    policy = mdstats.CheckpointSelectionPolicy()
    points = tuple(
        point(i, score, refinement=(i >= 8))
        for i, score in enumerate((0.010, 0.011, 0.012, 0.013, 0.014, 0.015, 0.016, 0.017, 0.019, 0.018))
    )
    result = mdstats.build_eval2_shortlist(points, policy)
    assert len(result) == 5
    epochs = [p.epoch for p, _ in result]
    assert {0, 1, 2}.issubset(epochs)
    assert {8, 9}.issubset(epochs)
    refinement = [p for p, reasons in result if "best_lightweight_target_refinement" in reasons]
    assert {p.epoch for p in refinement} == {8, 9}


def test_target_metric_reducer_builds_species_tails_conditions_and_blocks():
    view = SimpleNamespace(
        configuration_count=2,
        total_atom_count=4,
        atom_counts=np.asarray([2, 2]),
        force_offsets=np.asarray([0, 2, 4]),
        reference_energies=np.asarray([0.0, 2.0]),
        reference_forces=np.zeros((4, 3)),
        atomic_numbers=np.asarray([11, 8, 11, 8]),
        focus_atomic_numbers=(11,),
        condition_labels=("cold", "hot"),
        condition_ids=np.asarray([0, 1]),
        stress_present=np.asarray([False, False]),
        reference_stresses=np.zeros((2, 6)),
    )
    preds = (
        AtomicModelPrediction(energy_ev=0.2, forces_ev_per_angstrom=np.asarray([[0.01, 0, 0], [0.02, 0, 0]]), stress_ev_per_angstrom3=None),
        AtomicModelPrediction(energy_ev=2.4, forces_ev_per_angstrom=np.asarray([[0.03, 0, 0], [0.04, 0, 0]]), stress_ev_per_angstrom3=None),
    )
    record = mdstats.eval2_target_metrics_from_prediction_view(
        view,
        preds,
        block_ids=("trajectory-A", "trajectory-B"),
        target_role_digest=D1,
        prediction_digest=D2,
    )
    assert record.configuration_count == 2
    assert record.atom_count == 4
    assert record.energy_mae_ev_per_atom == pytest.approx(0.15)
    assert record.relative_energy_rmse_ev_per_atom == pytest.approx(0.05)
    assert record.force_component_rmse_ev_per_angstrom == pytest.approx(np.sqrt((0.01**2 + 0.02**2 + 0.03**2 + 0.04**2) / 12))
    assert set(dict(record.species_force_rmse_ev_per_angstrom)) == {"O", "Na"}
    assert record.force_error_p99_ev_per_angstrom > record.force_error_p90_ev_per_angstrom
    assert {b.block_id for b in record.block_metrics} == {"trajectory-A", "trajectory-B"}
    assert any(k.startswith("condition:") for k, _ in record.stratum_force_rmse_ev_per_angstrom)
    assert {k for k, _ in record.stratum_force_rmse_ev_per_angstrom if k.startswith("group:")} == {"group:focus", "group:nonfocus"}
    assert mdstats.Eval2TargetMetricRecord.from_dict(record.to_dict()) == record


def test_paired_bootstrap_is_deterministic_and_detects_material_improvement():
    policy = mdstats.CheckpointSelectionPolicy(bootstrap_replicates=500)
    first = checkpoint(point(20, 0.020, refinement=True), 0.020)
    second = checkpoint(point(21, 0.024, refinement=True), 0.024)
    a = mdstats.paired_block_bootstrap_compare(first, second, policy=policy, seed_material_digest=D5)
    b = mdstats.paired_block_bootstrap_compare(first, second, policy=policy, seed_material_digest=D5)
    assert a == b
    assert a.decision == "first_materially_better"
    assert a.confidence_high_ev_per_angstrom is not None and a.confidence_high_ev_per_angstrom < 0
    assert a.seed is not None


def test_bootstrap_below_block_floor_has_no_authority_and_one_mev_rule_remains():
    policy = mdstats.CheckpointSelectionPolicy(bootstrap_min_independent_blocks=10)
    first = checkpoint(point(10, 0.020), 0.020, blocks=5)
    second = checkpoint(point(11, 0.022), 0.022, blocks=5)
    comparison = mdstats.paired_block_bootstrap_compare(first, second, policy=policy, seed_material_digest=D4)
    assert comparison.decision == "insufficient_blocks"
    ordered, _ = mdstats.order_eval2_admissible_candidates((second, first), policy=policy, seed_material_digest=D4)
    assert ordered[0].stable_candidate_identity == first.stable_candidate_identity


def test_practical_equivalence_prefers_target_secondary_and_refinement_not_replay_margin():
    policy = mdstats.CheckpointSelectionPolicy()
    # Later candidate is 0.8 meV/A worse on primary (inside 1 meV/A equivalence),
    # but has better target-tail evidence and is mature refinement.
    early = checkpoint(point(12, 0.0200), 0.0200, replay=0.020, secondary=0.025)
    mature = checkpoint(point(28, 0.0208, refinement=True), 0.0208, replay=0.045, secondary=0.020)
    assert early.admissible and mature.admissible
    ordered, comparisons = mdstats.order_eval2_admissible_candidates((early, mature), policy=policy, seed_material_digest=D5)
    assert comparisons[0].decision == "indistinguishable"
    assert ordered[0].stable_candidate_identity == mature.stable_candidate_identity

    # Make replay much better on the otherwise target-worse candidate: ordering
    # is unchanged because replay is not accepted by the ranking API.
    mature_better_replay = checkpoint(point(28, 0.0208, refinement=True), 0.0208, replay=0.001, secondary=0.020)
    ordered2, _ = mdstats.order_eval2_admissible_candidates((early, mature_better_replay), policy=policy, seed_material_digest=D5)
    assert ordered2[0].trajectory_point.epoch == 28


def test_replay_is_hard_constraint_only():
    policy = mdstats.CheckpointAdmissibilityPolicy(replay_degradation_budget_ev_per_angstrom=0.030)
    accepted = checkpoint(point(25, 0.020, refinement=True), 0.020, replay=0.049, baseline=0.020, policy=policy)
    rejected = checkpoint(point(26, 0.019, refinement=True), 0.019, replay=0.051, baseline=0.020, policy=policy)
    assert accepted.admissible
    assert not rejected.admissible
    assert "replay_retention_ceiling_exceeded" in rejected.rejection_reasons
    ordered, _ = mdstats.order_eval2_admissible_candidates((rejected, accepted), policy=mdstats.CheckpointSelectionPolicy(), seed_material_digest=D6)
    assert ordered == (accepted,)


def test_eval2_run_record_round_trip_and_rescue():
    selection = mdstats.CheckpointSelectionPolicy(initial_full_evaluation_candidates=2, refinement_reserved_candidates=1)
    admissibility = mdstats.CheckpointAdmissibilityPolicy()
    points = (point(1, 0.020), point(2, 0.021, refinement=True), point(3, 0.022, refinement=True))
    plan = mdstats.Eval2EvaluationPlan(
        run_plan_digest=D1,
        training_protocol_digest=D2,
        selection_policy_digest=selection.policy_digest,
        admissibility_policy_digest=admissibility.policy_digest,
        target_role_digest=D3,
        replay_role_digest=D4,
        candidate_rescue_cap=1,
        bootstrap_seed_material_digest=D5,
    )
    bad = checkpoint(points[0], 0.040, replay=0.060)
    record = mdstats.build_eval2_run_record(
        evaluation_plan=plan,
        trajectory_points=points,
        evaluated_checkpoints=(bad,),
        selection_policy=selection,
    )
    assert record.outcome == "awaiting_more_evaluations"
    batch = mdstats.next_eval2_checkpoint_batch(record, trajectory_points=points, policy=selection, rescue_cap=1)
    assert len(batch) == 1
    assert batch[0].checkpoint_sha256 != bad.trajectory_point.checkpoint_sha256
    assert mdstats.Eval2RunRecord.from_dict(record.to_dict()) == record


def test_read_train2_history_authenticates_checkpoint_bytes(tmp_path: Path):
    root = tmp_path / "checkpoints"
    root.mkdir()
    sha1 = "a" * 64
    sha2 = "b" * 64
    payloads = [
        {
            "schema": "mdstats.train2-epoch-history.v1",
            "epoch": 9,
            "normalized_progress": 0.30,
            "instantaneous_learning_rate": 1e-4,
            "phase": "adaptation",
            "validation_force_rmse_ev_per_angstrom": {"target": 0.021, "train2_true_replay": 0.030},
            "raw_checkpoint_sha256": sha1,
            "runtime_summary_digest": D1,
        },
        {
            "schema": "mdstats.train2-epoch-history.v1",
            "epoch": 29,
            "normalized_progress": 1.0,
            "instantaneous_learning_rate": 1e-6,
            "phase": "refinement",
            "validation_force_rmse_ev_per_angstrom": {"target": 0.019},
            "raw_checkpoint_sha256": sha2,
            "runtime_summary_digest": D2,
        },
    ]
    (root / "train2_history.jsonl").write_text("\n".join(json.dumps(v) for v in payloads) + "\n")
    catalog = SimpleNamespace(checkpoints=(SimpleNamespace(epoch=9, sha256=sha1), SimpleNamespace(epoch=29, sha256=sha2)))
    result = mdstats.read_train2_trajectory_points(root, checkpoint_catalog=catalog, target_head_name="target")
    assert [v.epoch for v in result] == [9, 29]
    payloads[1]["raw_checkpoint_sha256"] = "c" * 64
    (root / "train2_history.jsonl").write_text("\n".join(json.dumps(v) for v in payloads) + "\n")
    with pytest.raises(mdstats.TrainingDataInputError, match="bytes disagree"):
        mdstats.read_train2_trajectory_points(root, checkpoint_catalog=catalog, target_head_name="target")

class _FakeRoleDomain:
    def __init__(self):
        self.size_development_frame_uids = tuple(f"{i:064x}" for i in range(1, 9))
        self.development_intervals = (
            SimpleNamespace(unit_id="a" * 64, frame_uids=self.size_development_frame_uids[:4]),
            SimpleNamespace(unit_id="b" * 64, frame_uids=self.size_development_frame_uids[4:]),
        )
        self.cv_checkpoint_monitor_unit_ids_by_fold = ((0, ("a" * 64,)), (1, ("b" * 64,)))


class _FakeRoleFreeze:
    content_digest = "c" * 64
    def __init__(self): self._domain = _FakeRoleDomain()
    def domain(self, label_domain_id): return self._domain
    def require_size_selection_frames(self, frames, **kwargs): return tuple(frames)


class _FakeLadder:
    content_digest = "d" * 64
    def __init__(self, excluded): self.excluded = excluded
    def domain(self, label_domain_id):
        return SimpleNamespace(rungs=(SimpleNamespace(materializable=True, target_size=len(self.excluded), frame_uids=self.excluded),))


def test_eval2_size_role_is_common_development_complement_and_cv_role_is_authorized():
    freeze = _FakeRoleFreeze()
    excluded = freeze._domain.size_development_frame_uids[:4]
    role = mdstats.build_eval2_size_study_target_role(freeze, _FakeLadder(excluded), label_domain_id="target", maximum_training_size=4)
    assert role.role_kind == "size_development_complement"
    assert set(role.evaluation_frame_uids).isdisjoint(excluded)
    assert role.evaluation_frame_uids == freeze._domain.size_development_frame_uids[4:]
    assert set(role.correlation_block_ids) == {"b" * 64}
    assert mdstats.Eval2TargetRole.from_dict(role.to_dict()) == role

    cv = mdstats.build_eval2_cv_target_role(freeze, label_domain_id="target", fold_index=0)
    assert cv.role_kind == "cv_checkpoint_monitor"
    assert cv.evaluation_frame_uids == freeze._domain.size_development_frame_uids[:4]
    assert set(cv.correlation_block_ids) == {"a" * 64}


def test_eval2_coarse_size_role_is_fixed_deterministic_balanced_subset():
    freeze = _FakeRoleFreeze()
    excluded = freeze._domain.size_development_frame_uids[:2]
    ladder = _FakeLadder(excluded)
    full = mdstats.build_eval2_size_study_target_role(
        freeze, ladder, label_domain_id="target", maximum_training_size=2
    )
    first = mdstats.build_eval2_coarse_size_study_target_role(
        freeze, ladder, label_domain_id="target", maximum_training_size=2, maximum_configurations=4
    )
    second = mdstats.build_eval2_coarse_size_study_target_role(
        freeze, ladder, label_domain_id="target", maximum_training_size=2, maximum_configurations=4
    )
    assert first == second
    assert first.role_kind == "size_development_coarse"
    assert len(first.evaluation_frame_uids) == 4
    assert set(first.evaluation_frame_uids).issubset(full.evaluation_frame_uids)
    assert first.excluded_training_frame_uids == full.excluded_training_frame_uids
    counts = {block: first.correlation_block_ids.count(block) for block in set(first.correlation_block_ids)}
    assert max(counts.values()) - min(counts.values()) <= 1
    assert mdstats.Eval2TargetRole.from_dict(first.to_dict()) == first


def test_eval2_size_role_fails_if_largest_rung_consumes_all_development():
    freeze = _FakeRoleFreeze()
    all_frames = freeze._domain.size_development_frame_uids
    with pytest.raises(mdstats.TrainingDataInputError, match="role is empty"):
        mdstats.build_eval2_size_study_target_role(freeze, _FakeLadder(all_frames), label_domain_id="target", maximum_training_size=8)


def test_eval2_development_role_materialization_reconstructs_exact_order_from_cv_artifacts(tmp_path: Path):
    from ase import Atoms
    from ase.io import write
    from mdstats.training_data import campaign_cli

    config = tmp_path / "campaign.toml"
    config.write_text("", encoding="utf-8")
    paths = campaign_cli.CampaignPaths.from_config(config, {"campaign": {"workspace": str(tmp_path / "work")}})
    paths.ensure()
    store = campaign_cli.CampaignStore(paths.state_db)
    root = tmp_path / "data8"
    root.mkdir()

    uids = ("a" * 64, "b" * 64, "c" * 64)
    artifacts = []
    jobs = []
    for index, uid in enumerate(uids):
        job_dir = root / "jobs" / f"fold_{index:02d}"
        job_dir.mkdir(parents=True)
        source = job_dir / "fold_evaluation.xyz"
        write(source, [Atoms("H", positions=[[float(index), 0.0, 0.0]])], format="extxyz")
        sidecar = job_dir / "fold_evaluation.json"
        sidecar.write_text("{}\n", encoding="utf-8")
        artifact = mdstats.MaceExtxyzArtifact(
            role="cross_validation_evaluation",
            relative_path=source.name,
            sha256=campaign_cli._sha256(source),
            configuration_count=1,
            frame_uids=(uid,),
            atomic_numbers=(1,),
            policy_digest=D1,
            sidecar_relative_path=sidecar.name,
            sidecar_sha256=campaign_cli._sha256(sidecar),
            sidecar_digest=D2,
        )
        artifacts.append(artifact)
        jobs.append(SimpleNamespace(
            relative_directory=str(job_dir.relative_to(root)),
            fold_evaluation_artifact_digest=artifact.content_digest,
        ))

    role = mdstats.Eval2TargetRole(
        label_domain_id="domain",
        role_kind="size_development_complement",
        target_data_role_freeze_digest=D3,
        target_data_ladder_digest=D4,
        evaluation_frame_uids=(uids[2], uids[0]),
        correlation_block_ids=(D5, D6),
        excluded_training_frame_uids=(uids[1],),
    )
    bundle = SimpleNamespace(fold_evaluation_artifacts=tuple(artifacts), jobs=tuple(jobs))
    artifact, path = campaign_cli._eval2_materialize_development_target_artifact(
        paths=paths, store=store, bundle=bundle, root=root, role=role
    )
    assert artifact.frame_uids == (uids[2], uids[0])
    assert artifact.configuration_count == 2
    assert artifact.role == "eval2_size_development_complement"
    assert path.is_file()
    # Cached reuse must authenticate and return the same bytes/identity.
    again, again_path = campaign_cli._eval2_materialize_development_target_artifact(
        paths=paths, store=store, bundle=bundle, root=root, role=role
    )
    assert again.content_digest == artifact.content_digest
    assert again_path == path


def test_bootstrap_cannot_reverse_material_point_estimate_direction():
    policy = mdstats.CheckpointSelectionPolicy(bootstrap_replicates=2000, bootstrap_min_independent_blocks=10)
    p1, p2 = point(1, 0.010), point(2, 0.020)

    def metrics(primary: float, first: bool) -> mdstats.Eval2TargetMetricRecord:
        blocks = []
        for i in range(12):
            # Equal-block resampling favors candidate 2 in most blocks, while
            # the frozen unrounded global primary says candidate 1 is better.
            rmse = (0.030 if first else 0.010) if i < 11 else (0.001 if first else 0.080)
            blocks.append(mdstats.Eval2TargetBlockMetric(
                block_id=f"block-{i:02d}", force_squared_error_sum=rmse * rmse * 30,
                force_component_count=30, configuration_count=1,
            ))
        return mdstats.Eval2TargetMetricRecord(
            configuration_count=12, atom_count=120, energy_mae_ev_per_atom=0.001,
            relative_energy_rmse_ev_per_atom=0.0005,
            force_component_rmse_ev_per_angstrom=primary,
            species_macro_force_rmse_ev_per_angstrom=primary,
            species_force_rmse_ev_per_angstrom=(("Na", primary),),
            force_error_p90_ev_per_angstrom=primary, force_error_p95_ev_per_angstrom=primary,
            force_error_p99_ev_per_angstrom=primary,
            worst_stratum_force_rmse_ev_per_angstrom=primary,
            stratum_force_rmse_ev_per_angstrom=(("species:Na", primary),),
            stress_rmse_ev_per_angstrom3=None, block_metrics=tuple(blocks),
            target_role_digest=D1, prediction_digest=D2 if first else D4,
        )

    admissibility = mdstats.CheckpointAdmissibilityPolicy(replay_enabled=False, replay_degradation_budget_ev_per_angstrom=None)
    first = mdstats.assess_eval2_checkpoint(
        p1, evaluation_record_digest=D3, target_metrics=metrics(0.010, True),
        admissibility_policy=admissibility,
        replay_candidate_force_rmse_ev_per_angstrom=None,
        replay_foundation_force_rmse_ev_per_angstrom=None, replay_label_mode=None,
    )
    second = mdstats.assess_eval2_checkpoint(
        p2, evaluation_record_digest=D5, target_metrics=metrics(0.020, False),
        admissibility_policy=admissibility,
        replay_candidate_force_rmse_ev_per_angstrom=None,
        replay_foundation_force_rmse_ev_per_angstrom=None, replay_label_mode=None,
    )
    comparison = mdstats.paired_block_bootstrap_compare(first, second, policy=policy, seed_material_digest=D6)
    assert comparison.first_minus_second_ev_per_angstrom < -policy.practical_equivalence_ev_per_angstrom
    assert comparison.decision != "second_materially_better"
