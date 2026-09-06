"""P3-B gate evidence: candidate realization, current-generation export,
generic exact-membership materialization, and fixed harness validation."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
import tests.test_mlff_target_size_execution_p3a as p3a
from mdstats.training_data._common import digest
from mdstats.training_data.mace_export import MaceExtxyzPolicy
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    TargetSizeCandidateRealization,
    TargetSizeCandidateTrajectory,
    build_target_size_candidate_trajectory,
    build_target_size_screen_schedule,
    materialize_target_size_candidate,
    project_target_size_candidate_preparation,
    validate_target_size_candidate_trajectory,
    validate_target_size_materialization,
    write_target_size_extxyz_artifact,
)
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
    validate_candidate_optimizer_policy,
)

def _context_for(aggregate, common, schedule, *, optimizer_policy=None):
    return build_target_size_execution_context(
        aggregate.definition,
        common,
        schedule,
        seed_neutral_optimizer_policy=(
            MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
            if optimizer_policy is None
            else optimizer_policy
        ),
    )


def _candidate(env, *, target_size, seed, batch_size=4):
    optimizer = MaceOptimizerPolicy(
        max_num_epochs=env["schedule"].n3, batch_size=batch_size
    )
    trajectory = build_target_size_candidate_trajectory(
        env["aggregate"].definition,
        env["context"],
        env["common"],
        env["schedule"],
        target_size=target_size,
        optimizer_policy=optimizer,
        optimizer_seed=seed,
    )
    projection = project_target_size_candidate_preparation(
        env["common"], env["aggregate"].definition, target_size
    )
    return trajectory, projection, optimizer


def test_p3b_exact_tn_membership_and_digest_through_real_owner(
    tmp_path: Path,
) -> None:
    env = {}
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    env.update(
        aggregate=aggregate, common=common, schedule=schedule,
        context=_context_for(aggregate, common, schedule),
    )
    trajectory, projection, _optimizer = _candidate(env, target_size=aggregate.definition.qualified_candidate_sizes[0], seed=1)
    definition = aggregate.definition
    membership = definition.candidate_membership(trajectory.target_size)
    assert trajectory.candidate_membership == membership
    assert trajectory.candidate_membership_digest == (
        definition.training_order.candidate_digest(trajectory.target_size)
    )
    out = tmp_path / "candidate"
    record = materialize_target_size_candidate(
        trajectory,
        projection,
        common,
        canonical_frame_authority=fa,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        output_directory=out,
        optimizer_policy=MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4),
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=index,
    )
    assert record.target_train_artifact.frame_uids == tuple(membership)
    assert record.target_train_artifact.configuration_count == len(membership)
    # Restart authentication through the real owner.
    validate_target_size_materialization(
        record,
        trajectory,
        canonical_frame_authority=fa,
        extxyz_policy=MaceExtxyzPolicy(),
    )


def test_p3b_unqualified_n_and_alternative_membership_rejected(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    unqualified = [
        n
        for n in definition.policy.candidate_sizes
        if n not in definition.qualified_candidate_sizes
    ]
    if unqualified:
        with pytest.raises(mdstats.TrainingDataInputError):
            build_target_size_candidate_trajectory(
                definition,
                context,
                common,
                schedule,
                target_size=unqualified[0],
                optimizer_policy=MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4),
                optimizer_seed=1,
            )
    # Foreign seeds are rejected.
    with pytest.raises(mdstats.TrainingDataInputError):
        build_target_size_candidate_trajectory(
            definition,
            context,
            common,
            schedule,
            target_size=definition.qualified_candidate_sizes[0],
            optimizer_policy=MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4),
            optimizer_seed=999,
        )
    # An alternative same-sized membership cannot be supplied: the trajectory
    # builder derives membership only from P2 authority, and the dataclass
    # rejects a forged membership/digest pair.
    with pytest.raises(mdstats.TrainingDataInputError):
        TargetSizeCandidateTrajectory(
            experiment_definition_digest=trajectory_parents(definition, common)[0],
            execution_context_digest=context.content_digest,
            target_size=definition.qualified_candidate_sizes[0],
            training_order_digest=definition.training_order.content_digest,
            candidate_membership_digest="0" * 64,
            candidate_membership=("f" * 64,),
            optimizer_seed=1,
            seed_neutral_training_policy_digest="2" * 64,
            common_preparation_digest=common.content_digest,
            replay_foundation_identity_digest="3" * 64,
            realization=build_target_size_candidate_trajectory(
                definition,
                context,
                common,
                schedule,
                target_size=definition.qualified_candidate_sizes[0],
                optimizer_policy=MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4),
                optimizer_seed=1,
            ).realization,
            evaluation_model_state="live",
            candidate_training_protocol_digest="4" * 64,
        )


def trajectory_parents(definition, common):
    return (definition.content_digest, common.content_digest)


def test_p3b_one_trajectory_per_n_seed_no_rung_drift(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    n = definition.qualified_candidate_sizes[0]
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    first = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=n, optimizer_policy=optimizer, optimizer_seed=1,
    )
    second = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=n, optimizer_policy=optimizer, optimizer_seed=1,
    )
    assert first.content_digest == second.content_digest
    assert first.trajectory_id() == second.trajectory_id()
    # A different seed is a different trajectory but the same scientific
    # candidate lineage shape.
    other_seed = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=n, optimizer_policy=replace(optimizer, seed=2),
        optimizer_seed=2,
    )
    assert other_seed.content_digest != first.content_digest
    # Rung limits do not redefine the trajectory: the realization binds the
    # full-n3 plan, and the runtime plan at any rung limit stays inside it.
    for limit in schedule.fidelity_epochs:
        plan = schedule.runtime_plan(
            training_protocol_digest="a" * 64,
            optimizer_policy_digest="b" * 64,
            structures_per_epoch=first.realization.structures_per_epoch,
            execution_epoch_limit=limit,
        )
        assert plan.budget_policy.planned_epochs == schedule.n3


def test_p3b_n_changes_realization_not_context(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    sizes = sorted(definition.qualified_candidate_sizes)
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    small = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=sizes[0], optimizer_policy=optimizer, optimizer_seed=1,
    )
    large = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=sizes[1], optimizer_policy=optimizer, optimizer_seed=1,
    )
    assert small.realization.target_train_count == sizes[0]
    assert large.realization.target_train_count == sizes[1]
    assert large.realization.structures_per_epoch > small.realization.structures_per_epoch
    assert small.execution_context_digest == large.execution_context_digest
    assert small.seed_neutral_training_policy_digest == (
        large.seed_neutral_training_policy_digest
    )


def test_p3b_stale_realization_rejected_on_restart(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    n = definition.qualified_candidate_sizes[0]
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    trajectory = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=n, optimizer_policy=optimizer, optimizer_seed=1,
    )
    # Restart with the same authority succeeds.
    validate_target_size_candidate_trajectory(
        trajectory, definition, context, common, schedule, optimizer_policy=optimizer
    )
    # A stale loader/update geometry (different batch size) is rejected even
    # though the global execution context digest is unchanged.
    stale_optimizer = replace(optimizer, batch_size=optimizer.batch_size * 2)
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_target_size_candidate_trajectory(
            trajectory, definition, context, common, schedule,
            optimizer_policy=stale_optimizer,
        )
    # A tampered precision realization is rejected.
    stale = TargetSizeCandidateTrajectory.from_dict(trajectory.to_dict())
    tampered = json.loads(json.dumps(stale.to_dict()))
    tampered["realization"]["default_dtype"] = "float32"
    with pytest.raises((mdstats.TrainingDataInputError, mdstats.TrainingDataSerializationError)):
        TargetSizeCandidateTrajectory.from_dict(tampered)


def test_p3b_rematerialization_is_idempotent(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    n = definition.qualified_candidate_sizes[0]
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    trajectory = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=n, optimizer_policy=optimizer, optimizer_seed=1,
    )
    projection = project_target_size_candidate_preparation(common, definition, n)
    out = tmp_path / "candidate"
    first = materialize_target_size_candidate(
        trajectory, projection, common,
        canonical_frame_authority=fa,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        output_directory=out,
        optimizer_policy=optimizer,
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=index,
    )
    second = materialize_target_size_candidate(
        trajectory, projection, common,
        canonical_frame_authority=fa,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        output_directory=out,
        optimizer_policy=optimizer,
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=index,
    )
    assert first.content_digest == second.content_digest
    assert first.target_train_artifact.sha256 == second.target_train_artifact.sha256
    # A different candidate cannot claim the same directory.
    other_projection = project_target_size_candidate_preparation(
        common, definition, sorted(definition.qualified_candidate_sizes)[-1]
    )
    other_trajectory = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=sorted(definition.qualified_candidate_sizes)[-1],
        optimizer_policy=optimizer, optimizer_seed=1,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        materialize_target_size_candidate(
            other_trajectory, other_projection, common,
            canonical_frame_authority=fa,
            frame_catalog=frames,
            frame_data_by_run=frame_data_by_run,
            output_directory=out,
            optimizer_policy=optimizer,
            extxyz_policy=MaceExtxyzPolicy(),
            frame_array_index=index,
        )


def test_p3b_export_authenticates_against_canonical_authority(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, manifest)
    definition = aggregate.definition
    n = definition.qualified_candidate_sizes[0]
    membership = definition.candidate_membership(n)
    projection = project_target_size_candidate_preparation(common, definition, n)
    out = tmp_path / "export"
    artifact = write_target_size_extxyz_artifact(
        out,
        dataset_id=fa.dataset_id,
        role="target_train",
        filename="target.extxyz",
        frame_uids=membership,
        canonical_frame_authority=fa,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        membership_digest=projection.candidate_membership_digest,
        common_preparation_digest=common.content_digest,
        training_weights=projection.frame_weight_table(),
        frame_array_index=index,
    )
    assert artifact.canonical_frame_authority_digest == fa.content_digest
    # Sidecar binds canonical label identity, not legacy catalog/domain digests.
    sidecar = json.loads((out / "target.extxyz.manifest.json").read_text())
    record = sidecar["records"][membership[0]]
    canonical = fa.frame(membership[0])
    assert record["canonical_label_payload_digest"] == (
        canonical.canonical_label_payload_digest
    )
    assert "label_domain_id" not in record
    assert "frame_catalog_digest" not in sidecar
    assert "data7_bundle_digest" not in sidecar
    # A foreign frame cannot be exported.
    with pytest.raises(mdstats.TrainingDataInputError):
        write_target_size_extxyz_artifact(
            out,
            dataset_id=fa.dataset_id,
            role="target_train",
            filename="foreign.extxyz",
            frame_uids=("f" * 64,),
            canonical_frame_authority=fa,
            frame_catalog=frames,
            frame_data_by_run=frame_data_by_run,
            membership_digest=projection.candidate_membership_digest,
            frame_array_index=index,
        )
    # Tampered artifact bytes fail restart validation.
    target_file = out / "target.extxyz"
    original = target_file.read_bytes()
    target_file.write_bytes(original + b"\n")
    from mdstats.training_data.target_size_execution import (
        validate_target_size_extxyz_artifact,
    )

    with pytest.raises(mdstats.TrainingDataInputError):
        validate_target_size_extxyz_artifact(
            artifact,
            root_directory=out,
            canonical_frame_authority=fa,
            policy=MaceExtxyzPolicy(),
        )
    target_file.write_bytes(original)


def test_p3b_harness_validation_is_fixed_and_non_controlling(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    harness_digests = set()
    for n in sorted(definition.qualified_candidate_sizes):
        for seed in definition.policy.optimizer_seeds:
            trajectory = build_target_size_candidate_trajectory(
                definition, context, common, schedule,
                target_size=n, optimizer_policy=replace(optimizer, seed=seed),
                optimizer_seed=seed,
            )
            projection = project_target_size_candidate_preparation(common, definition, n)
            out = tmp_path / f"c-{n}-{seed}"
            record = materialize_target_size_candidate(
                trajectory, projection, common,
                canonical_frame_authority=fa,
                frame_catalog=frames,
                frame_data_by_run=frame_data_by_run,
                output_directory=out,
                optimizer_policy=replace(optimizer, seed=seed),
                extxyz_policy=MaceExtxyzPolicy(),
                frame_array_index=index,
            )
            harness_digests.add(record.harness_validation_artifact.content_digest)
            # The harness artifact never enters the training structures count.
            assert trajectory.realization.structures_per_epoch == n
            # It is derived from training-side data only (a P_train subset).
            assert set(record.harness_validation_artifact.frame_uids) <= set(
                aggregate.split.training_frame_uids
            )
    # Identical across all N and seeds under the same context.
    assert len(harness_digests) == 1


def test_p3b_mace_config_binds_exact_seed_and_target_artifact(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    n = definition.qualified_candidate_sizes[0]
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    trajectory = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=n, optimizer_policy=replace(optimizer, seed=2), optimizer_seed=2,
    )
    projection = project_target_size_candidate_preparation(common, definition, n)
    out = tmp_path / "candidate"
    record = materialize_target_size_candidate(
        trajectory, projection, common,
        canonical_frame_authority=fa,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        output_directory=out,
        optimizer_policy=replace(optimizer, seed=2),
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=index,
    )
    config = json.loads((out / record.mace_config_relative_path).read_text())
    assert config["seed"] == 2
    assert config["target_train_file"] == record.target_train_artifact.relative_path
    assert config["max_num_epochs"] == schedule.n3
    # E0s come from the common fitted references.
    fitted = dict(common.fitted_atomic_references.reference_energies_ev)
    assert {int(k): v for k, v in config["E0s"].items()} == fitted
    validate_target_size_materialization(
        record,
        trajectory,
        canonical_frame_authority=fa,
        extxyz_policy=MaceExtxyzPolicy(),
    )


def test_p3b_structural_absence_no_legacy_authority_in_p3_records(tmp_path: Path) -> None:
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    n = definition.qualified_candidate_sizes[0]
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    trajectory = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=n, optimizer_policy=optimizer, optimizer_seed=1,
    )
    projection = project_target_size_candidate_preparation(common, definition, n)
    out = tmp_path / "candidate"
    record = materialize_target_size_candidate(
        trajectory, projection, common,
        canonical_frame_authority=fa,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        output_directory=out,
        optimizer_policy=optimizer,
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=index,
    )
    forbidden = {
        "label_domain_id",
        "frame_catalog_digest",
        "data7_bundle_digest",
        "data5_bundle_digest",
        "selection_size",
        "selection_ladder",
        "cv_fold",
        "fold_index",
    }
    for payload in (
        common.to_dict(),
        projection.to_dict(),
        trajectory.to_dict(),
        record.to_dict(),
    ):
        text = json.dumps(payload)
        for token in forbidden:
            assert token not in text
    sidecar = json.loads(
        (out / record.target_train_artifact.sidecar_relative_path).read_text()
    )
    for token in forbidden:
        assert token not in json.dumps(sidecar)


def test_p3b_worker_count_is_execution_only_but_batch_size_is_scientific(
    tmp_path: Path,
) -> None:
    """Loader worker count is resource realization; batch size is the method.

    ``num_workers`` chooses how many DataLoader processes feed the same exact
    ``T_N`` in the same exact order under the qualified deterministic loader.
    It moves no parameter trajectory, LR schedule, checkpoint admissibility, or
    ranking, so it must not retire an otherwise identical screen - retuning it
    mid-screen is ordinary resource work.  ``batch_size`` is the opposite: it
    fixes the ``ceil(N/B)`` update geometry the whole normalization rests on.
    """

    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    definition = aggregate.definition
    n = definition.qualified_candidate_sizes[0]
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    trajectory = build_target_size_candidate_trajectory(
        definition, context, common, schedule,
        target_size=n, optimizer_policy=optimizer, optimizer_seed=1,
    )

    def _trajectory_for(policy):
        return build_target_size_candidate_trajectory(
            definition,
            build_target_size_execution_context(
                definition, common, schedule, seed_neutral_optimizer_policy=policy
            ),
            common,
            schedule,
            target_size=n,
            optimizer_policy=policy,
            optimizer_seed=1,
        )

    # A changed worker count is the same screen method, down to the realized
    # loader geometry and the whole candidate trajectory identity.
    workers_changed = _trajectory_for(replace(optimizer, num_workers=3))
    assert workers_changed.seed_neutral_training_policy_digest == (
        trajectory.seed_neutral_training_policy_digest
    )
    assert workers_changed.realization.loader_geometry_digest == (
        trajectory.realization.loader_geometry_digest
    )
    assert workers_changed.content_digest == trajectory.content_digest
    # The candidate policy carrying the different worker count is still an
    # admissible realization of the accepted screen template.
    validate_candidate_optimizer_policy(
        context.seed_neutral_optimizer_policy_digest,
        replace(optimizer, num_workers=3),
        authorized_seed=1,
    )

    # A changed gradient batch size is a different method: it changes the
    # update geometry, hence the realized normalization and the trajectory.
    batch_changed = _trajectory_for(replace(optimizer, batch_size=8))
    assert batch_changed.seed_neutral_training_policy_digest != (
        trajectory.seed_neutral_training_policy_digest
    )
    # This fixture's smallest N happens to need one update per epoch at either
    # batch size, so the visible consequence is the reference geometry the
    # normalization scales against - and therefore the realized amplitude.
    assert batch_changed.realization.reference_updates_per_epoch != (
        trajectory.realization.reference_updates_per_epoch
    )
    assert batch_changed.realization.effective_base_learning_rate != (
        trajectory.realization.effective_base_learning_rate
    )
    assert batch_changed.realization.content_digest != (
        trajectory.realization.content_digest
    )


def test_p3b_order_divergent_candidate_materializes_in_exact_p2_order(
    tmp_path: Path,
) -> None:
    """Real trajectory/projection/materialization owners on divergent orders.

    ``pi_train`` is condition-balanced and therefore not a subsequence of the
    stored ``P_train``; the exact P2 ``T_N`` must survive to the target-train
    artifact, and the projected weights must remain the common fitted weights
    attached by frame UID.
    """

    env = p3a.order_divergent_environment(tmp_path)
    aggregate, common = env["aggregate"], env["common"]
    definition = aggregate.definition
    size = p3a._first_non_subsequence_size(aggregate)
    schedule = build_target_size_screen_schedule(
        tuple(definition.policy.fidelity_epochs)
    )
    context = _context_for(aggregate, common, schedule)
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    trajectory = build_target_size_candidate_trajectory(
        definition,
        context,
        common,
        schedule,
        target_size=size,
        optimizer_policy=optimizer,
        optimizer_seed=1,
    )
    projection = project_target_size_candidate_preparation(common, definition, size)

    membership = definition.candidate_membership(size)
    assert trajectory.candidate_membership == tuple(membership)
    assert trajectory.candidate_membership_digest == (
        definition.training_order.candidate_digest(size)
    )
    assert projection.candidate_membership == tuple(membership)

    record = materialize_target_size_candidate(
        trajectory,
        projection,
        common,
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        output_directory=tmp_path / "divergent-candidate",
        optimizer_policy=optimizer,
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=env["index"],
    )
    # The artifact carries the exact P2 prefix order, not P_train order.
    assert record.target_train_artifact.frame_uids == tuple(membership)
    assert tuple(membership) != tuple(
        uid for uid in aggregate.split.training_frame_uids if uid in set(membership)
    )
    validate_target_size_materialization(
        record,
        trajectory,
        canonical_frame_authority=env["frame_authority"],
        extxyz_policy=MaceExtxyzPolicy(),
    )
    # Weights attach by UID and are the untouched common fitted values.
    table = projection.frame_weight_table()
    common_weight_by_uid = {
        item.frame_uid: item for item in common.fitted_frame_weights
    }
    for uid in membership:
        assert table.for_frame(uid).to_dict() == common_weight_by_uid[uid].to_dict()
    # No candidate-specific refit: the bound common state is unchanged.
    assert projection.common_preparation_digest == common.content_digest


# ---------------------------------------------------------------------------
# Historical replay across acceleration-realization turnover
#
# The seed-neutral screen identity deliberately excludes the optimizer seed and
# the acceleration realization, and each trajectory binds its own realization
# instead.  Replay of an already published cell must therefore authenticate the
# realization that trajectory actually bound, not whichever one this invocation
# currently qualifies -- while every consequence the current screen authority
# still determines stays fail-closed.
# ---------------------------------------------------------------------------

_ACCEL_A = digest({"training-acceleration-realization": "A"})
_ACCEL_B = digest({"training-acceleration-realization": "B"})


def _accelerated_optimizer(schedule, *, realization_digest, **overrides):
    return MaceOptimizerPolicy(
        max_num_epochs=schedule.n3,
        batch_size=4,
        acceleration_realization_digest=realization_digest,
        resolved_acceleration_kernel_mode="e3nn",
        **overrides,
    )


def _accelerated_env(tmp_path: Path):
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    optimizer_a = _accelerated_optimizer(schedule, realization_digest=_ACCEL_A)
    context = _context_for(aggregate, common, schedule, optimizer_policy=optimizer_a)
    definition = aggregate.definition
    trajectory = build_target_size_candidate_trajectory(
        definition,
        context,
        common,
        schedule,
        target_size=definition.qualified_candidate_sizes[0],
        optimizer_policy=optimizer_a,
        optimizer_seed=1,
    )
    return {
        "manifest": manifest,
        "frame_authority": fa,
        "aggregate": aggregate,
        "definition": definition,
        "common": common,
        "index": index,
        "schedule": schedule,
        "context": context,
        "optimizer_a": optimizer_a,
        "trajectory": trajectory,
    }


def _replay(env, trajectory, optimizer_policy):
    return validate_target_size_candidate_trajectory(
        trajectory,
        env["definition"],
        env["context"],
        env["common"],
        env["schedule"],
        optimizer_policy=optimizer_policy,
    )


def _drifted(trajectory, **realization_overrides):
    """A trajectory whose realization drifted from the accepted derivation.

    ``replace`` is used deliberately: a serialized tamper is already refused by
    the realization content digest, and the claim under test is the *replay*
    comparison, which must reject an internally consistent but non-derivable
    realization.
    """

    realization = replace(trajectory.realization, **realization_overrides)
    return replace(trajectory, realization=realization)


def test_p3b_replay_authenticates_the_historical_acceleration_realization(
    tmp_path: Path,
) -> None:
    env = _accelerated_env(tmp_path)
    trajectory = env["trajectory"]
    assert trajectory.realization.acceleration_realization_digest == _ACCEL_A

    # A -> A: unchanged realization replays.
    _replay(env, trajectory, env["optimizer_a"])

    # A -> B: the current invocation qualifies a different acceleration
    # realization.  The screen-wide seed-neutral identity is unchanged, so the
    # published cell must still authenticate -- against A, the realization it
    # actually bound.
    optimizer_b = _accelerated_optimizer(
        env["schedule"], realization_digest=_ACCEL_B
    )
    assert optimizer_b.policy_digest != env["optimizer_a"].policy_digest
    from mdstats.training_data.target_size_execution.context import (
        seed_neutral_optimizer_policy_digest,
    )

    assert seed_neutral_optimizer_policy_digest(optimizer_b) == (
        env["context"].seed_neutral_optimizer_policy_digest
    )
    _replay(env, trajectory, replace(optimizer_b, seed=1))

    # Nothing about the historical trajectory is rewritten to the current
    # realization.
    assert trajectory.realization.acceleration_realization_digest == _ACCEL_A


def test_p3b_replay_across_acceleration_turnover_keeps_drift_fail_closed(
    tmp_path: Path,
) -> None:
    env = _accelerated_env(tmp_path)
    trajectory = env["trajectory"]
    optimizer_b = replace(
        _accelerated_optimizer(env["schedule"], realization_digest=_ACCEL_B), seed=1
    )
    realization = trajectory.realization

    # Update geometry: a different batch size and its derived update counts.
    with pytest.raises(mdstats.TrainingDataInputError, match="update geometry"):
        _replay(
            env,
            _drifted(
                trajectory,
                batch_size=realization.batch_size * 2,
                updates_per_epoch=(realization.structures_per_epoch + 7) // 8,
                planned_updates=((realization.structures_per_epoch + 7) // 8)
                * env["schedule"].n3,
            ),
            optimizer_b,
        )

    # Validation batch semantics are identity-bound through loader geometry.
    with pytest.raises(mdstats.TrainingDataInputError, match="loader geometry"):
        _replay(
            env,
            _drifted(
                trajectory,
                loader_geometry_digest=digest({"valid_batch_size": "changed"}),
            ),
            optimizer_b,
        )

    # Precision realization.
    with pytest.raises(mdstats.TrainingDataInputError, match="precision realization"):
        _replay(env, _drifted(trajectory, default_dtype="float32"), optimizer_b)
    with pytest.raises(mdstats.TrainingDataInputError, match="precision realization"):
        _replay(
            env,
            _drifted(
                trajectory,
                precision_schedule_digest=digest({"precision": "changed"}),
            ),
            optimizer_b,
        )

    # Full-n3 screen horizon.
    with pytest.raises(mdstats.TrainingDataInputError, match="screen budget"):
        _replay(
            env,
            _drifted(
                trajectory,
                max_num_epochs=realization.max_num_epochs + 1,
                planned_updates=realization.updates_per_epoch
                * (realization.max_num_epochs + 1),
                planned_structures_presented=realization.structures_per_epoch
                * (realization.max_num_epochs + 1),
            ),
            optimizer_b,
        )

    # Exact T_N / candidate membership.
    other_sizes = [
        n
        for n in env["definition"].qualified_candidate_sizes
        if n != trajectory.target_size
    ]
    assert other_sizes
    with pytest.raises(mdstats.TrainingDataInputError):
        _replay(env, replace(trajectory, target_size=other_sizes[0]), optimizer_b)
    with pytest.raises(mdstats.TrainingDataInputError):
        _replay(
            env,
            replace(
                trajectory,
                candidate_membership_digest=digest({"membership": "foreign"}),
            ),
            optimizer_b,
        )

    # Unauthorized optimizer seed.
    unauthorized = max(env["definition"].policy.optimizer_seeds) + 17
    with pytest.raises(mdstats.TrainingDataInputError):
        _replay(
            env,
            replace(trajectory, optimizer_seed=unauthorized),
            replace(optimizer_b, seed=unauthorized),
        )


def test_p3b_forged_historical_acceleration_provenance_is_rejected(
    tmp_path: Path,
) -> None:
    env = _accelerated_env(tmp_path)
    trajectory = env["trajectory"]
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, env["manifest"])
    projection = project_target_size_candidate_preparation(
        env["common"], env["definition"], trajectory.target_size
    )
    out = tmp_path / "candidate"
    record = materialize_target_size_candidate(
        trajectory,
        projection,
        env["common"],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        output_directory=out,
        optimizer_policy=env["optimizer_a"],
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=env["index"],
    )

    # Rewriting the persisted acceleration provenance changes the trajectory's
    # own content identity, so a serialized forgery cannot even be loaded back.
    forged_payload = json.loads(json.dumps(trajectory.to_dict()))
    forged_payload["realization"]["acceleration_realization_digest"] = _ACCEL_B
    with pytest.raises(
        (mdstats.TrainingDataInputError, mdstats.TrainingDataSerializationError)
    ):
        TargetSizeCandidateTrajectory.from_dict(forged_payload)

    # And a forgery assembled in memory is contradicted by the durable
    # materialization parent, which binds the real historical trajectory.
    forged = _drifted(trajectory, acceleration_realization_digest=_ACCEL_B)
    assert forged.content_digest != trajectory.content_digest
    with pytest.raises(mdstats.TrainingDataInputError, match="different trajectory"):
        validate_target_size_materialization(
            record,
            forged,
            canonical_frame_authority=env["frame_authority"],
            materialization_directory=out,
            projection=projection,
            definition=env["definition"],
            common=env["common"],
            optimizer_policy=env["optimizer_a"],
            extxyz_policy=MaceExtxyzPolicy(),
            frame_catalog=frames,
            frame_data_by_run=frame_data_by_run,
            frame_array_index=env["index"],
        )


def test_p3b_every_realization_field_is_classified_for_diagnostics() -> None:
    """The drift diagnostic must not silently stop naming a new field.

    The digest comparison over the whole canonical payload remains the
    authority, so an unclassified field still rejects -- but restart
    diagnostics only stay actionable while every identity-bearing dimension
    has a class, so a new realization field has to be classified with it.
    """

    from mdstats.training_data.target_size_execution.candidate import (
        _REALIZATION_DRIFT_CLASSES,
    )

    classified = {name for _label, fields in _REALIZATION_DRIFT_CLASSES for name in fields}
    payload_fields = {
        name
        for name in TargetSizeCandidateRealization.__dataclass_fields__
        if name != "schema"
    }
    assert payload_fields - classified == set()
    assert classified - payload_fields == set()


@pytest.mark.parametrize("backend", ["e3nn", "cueq"])
@pytest.mark.parametrize("realization_digest", [None, _ACCEL_A, _ACCEL_B])
@pytest.mark.parametrize("seed", [0, 1, 7])
def test_p3b_candidate_binding_never_moves_the_seed_neutral_identity(
    backend: str, realization_digest: str | None, seed: int
) -> None:
    """The invariant the whole replay repair rests on.

    Recombining the template with a seed and an acceleration realization must
    change only candidate-local identity.  If it could move the seed-neutral
    digest, replaying historical provenance would silently redefine the screen
    -- so this is enumerated over the entire space that space actually has:
    both backends, both realizations plus the unbound case, and several seeds.
    """

    from mdstats.training_data.acceleration import MaceAccelerationPolicy
    from mdstats.training_data.target_size_execution.context import (
        bind_candidate_optimizer_policy,
        seed_neutral_optimizer_policy_digest,
    )

    template = MaceOptimizerPolicy(
        max_num_epochs=10,
        batch_size=4,
        acceleration_policy=MaceAccelerationPolicy(backend=backend),
    )
    bound = bind_candidate_optimizer_policy(
        template,
        optimizer_seed=seed,
        acceleration_realization_digest=realization_digest,
    )
    assert seed_neutral_optimizer_policy_digest(bound) == (
        seed_neutral_optimizer_policy_digest(template)
    )
    assert bound.seed == seed
    assert bound.acceleration_realization_digest == realization_digest
    # The resolved kernel mode is derived from the accepted backend, never
    # guessed: an unbound realization stays unbound, and a bound one carries
    # the only training kernel that backend admits.
    assert bound.resolved_acceleration_kernel_mode == (
        None if realization_digest is None
        else ("e3nn" if backend == "e3nn" else "cueq_pure")
    )
