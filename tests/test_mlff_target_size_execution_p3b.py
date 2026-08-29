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


def test_p3b_worker_resource_field_is_bound_not_silently_excluded(tmp_path: Path) -> None:
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
    # num_workers is not proven execution-only for sample-order semantics, so
    # it stays bound inside the seed-neutral training-policy identity: a
    # changed worker count yields a different (rejected) trajectory identity.
    changed = build_target_size_candidate_trajectory(
        definition,
        build_target_size_execution_context(
            definition,
            common,
            schedule,
            seed_neutral_optimizer_policy=replace(optimizer, num_workers=3),
        ),
        common,
        schedule,
        target_size=n,
        optimizer_policy=replace(optimizer, num_workers=3),
        optimizer_seed=1,
    )
    assert changed.seed_neutral_training_policy_digest != (
        trajectory.seed_neutral_training_policy_digest
    )
