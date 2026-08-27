from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats
from mdstats.training_data._common import TrainingDataInputError, digest


def _d(char: str) -> str:
    return char * 64


def _artifact(*, geom: str, generator: str | None = None, legacy_sha: str | None = None) -> mdstats.ReplayFileArtifact:
    return mdstats.ReplayFileArtifact(
        path=f"/{geom}.xyz",
        sha256=digest({"file": geom}),
        configuration_count=1,
        atomic_numbers=(3, 17),
        geometry_identities=(digest({"geometry": geom}),),
        label_identities=(digest({"labels": geom}),),
        energy_key="energy",
        forces_key="forces",
        stress_key="stress",
        stress_present_count=1,
        label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        foundation_checkpoint_digest=legacy_sha,
        foundation_label_generator_identity_digest=generator,
    )


def _mh1(head: str) -> mdstats.FoundationPotentialIdentity:
    return mdstats.FoundationPotentialIdentity(
        reference="/foundation/mace-mh-1.model",
        sha256=_d("1"),
        foundation_head=head,
        model_family="mace_mh_1",
        architecture_signature=_d("a"),
        model_atomic_numbers=(1, 3, 8, 11, 17),
        available_heads=("omol", "omat_pbe"),
        inspection_state="inspected",
    )


def _mpa0() -> mdstats.FoundationPotentialIdentity:
    return mdstats.FoundationPotentialIdentity(
        reference="/foundation/mace-mpa-0.model",
        sha256=_d("2"),
        foundation_head="default",
        model_family="mace_mpa_0",
        architecture_signature=_d("b"),
        model_atomic_numbers=(1, 3, 8, 11, 17),
        available_heads=("default",),
        inspection_state="inspected",
    )


def test_lineage1_replay_v4_binds_exact_generator_and_v3_roundtrips() -> None:
    generator_a = _d("a")
    generator_b = _d("b")
    train = _artifact(geom="train", generator=generator_a)
    monitor = _artifact(geom="monitor", generator=generator_a)
    plan = mdstats.ReplayPreparationPlan(
        mode=mdstats.ReplayMode.EXTERNAL_PSEUDOLABEL,
        train_artifact=train,
        monitor_artifact=monitor,
    )
    assert train.serialization_schema == "mdstats.replay-file-artifact.v4"
    assert plan.to_dict()["schema"] == "mdstats.replay-preparation-plan.v4"
    assert train.foundation_lineage_digest == generator_a
    assert mdstats.ReplayPreparationPlan.from_dict(plan.to_dict()) == plan

    with pytest.raises(TrainingDataInputError, match="different foundation label generators"):
        replace(plan, monitor_artifact=_artifact(geom="monitor2", generator=generator_b))

    legacy = _artifact(geom="legacy", legacy_sha=_d("c"))
    payload = legacy.to_dict()
    assert payload["schema"] == "mdstats.replay-file-artifact.v3"
    assert "foundation_checkpoint_digest" in payload
    assert "foundation_label_generator_identity_digest" not in payload
    assert mdstats.ReplayFileArtifact.from_dict(payload).to_dict() == payload


def test_lineage1_same_mh1_bytes_different_heads_and_execution_have_distinct_lineage() -> None:
    omat = _mh1("omat_pbe")
    omol = _mh1("omol")
    assert omat.sha256 == omol.sha256
    assert omat.canonical_content_digest != omol.canonical_content_digest

    e3nn = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=omat.canonical_content_digest,
        default_dtype="float32",
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="0.3.16",
        adapter_version="lineage-test-v1",
    )
    cueq = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=omat.canonical_content_digest,
        default_dtype="float32",
        backend="cueq",
        resolved_kernel_mode="cueq_pure",
        mace_version="0.3.16",
        adapter_version="lineage-test-v1",
    )
    assert e3nn.content_digest != cueq.content_digest
    assert _artifact(geom="e3nn", generator=e3nn.content_digest).content_digest != _artifact(
        geom="cueq", generator=cueq.content_digest
    ).content_digest


def test_lineage1_raw_sha_legacy_is_fail_closed_for_inspected_multihead() -> None:
    mh1 = _mh1("omat_pbe")
    mpa0 = _mpa0()
    assert not mdstats.foundation_identity_matches_lineage(mh1, legacy_checkpoint_digest=mh1.sha256)
    assert mdstats.foundation_identity_matches_lineage(mpa0, legacy_checkpoint_digest=mpa0.sha256)
    assert mdstats.foundation_identity_matches_lineage(
        mh1, foundation_identity_digest=mh1.canonical_content_digest
    )
    assert not mdstats.foundation_identity_matches_lineage(
        _mh1("omol"), foundation_identity_digest=mh1.canonical_content_digest
    )

    # ID1 deliberately retained a lightweight byte-only constructor for old
    # synthetic/legacy callers.  Its uninspected state is explicit, so matching
    # old SHA-bound evidence remains readable without claiming head knowledge.
    lightweight = mdstats.FoundationPotentialIdentity(
        reference="/legacy/fake.model",
        sha256=_d("3"),
        foundation_head="default",
        model_family="mace_mpa_0",
        inspection_state="uninspected",
    )
    assert mdstats.foundation_identity_matches_lineage(lightweight, legacy_checkpoint_digest=lightweight.sha256)


def _domain() -> mdstats.FeatureFitDomain:
    return mdstats.FeatureFitDomain(
        label_domain_id="domain",
        kind=mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT,
        data5_bundle_digest=_d("4"),
        unit_ids=(_d("5"),),
        frame_uids=(_d("6"),),
    )


def _reference_fit(*, identity: str | None = None, legacy_sha: str | None = None) -> mdstats.AtomicReferenceFitRecord:
    return mdstats.AtomicReferenceFitRecord(
        domain=_domain(),
        policy=mdstats.AtomicReferenceFitPolicy(fit_mode=mdstats.AtomicReferenceFitMode.FOUNDATION_RESIDUAL),
        frame_catalog_digest=_d("7"),
        element_order=(3,),
        element_symbols=("Li",),
        count_matrix=((1,),),
        target_energies_ev=(-2.0,),
        fitted_targets_ev=(-2.0,),
        foundation_prediction_energies_ev=(-1.5,),
        foundation_reference_energies_ev=((3, -1.0),),
        correction_energies_ev=((3, -1.0),),
        reference_energies_ev=((3, -2.0),),
        foundation_checkpoint_digest=legacy_sha,
        rank=1,
        singular_values=(1.0,),
        null_space_dimension=0,
        residual_rmse_ev=0.0,
        residual_mae_ev=0.0,
        maximum_absolute_residual_ev=0.0,
        rank_deficient=False,
        transfer_warnings=(),
        foundation_identity_digest=identity,
        serialization_schema=(
            "mdstats.atomic-reference-fit-record.v2" if legacy_sha is not None else "mdstats.atomic-reference-fit-record.v3"
        ),
    )


def test_lineage1_reference_fit_v3_and_v2_preserve_correct_authority() -> None:
    mh1 = _mh1("omat_pbe")
    fit = _reference_fit(identity=mh1.canonical_content_digest)
    payload = fit.to_dict()
    assert payload["schema"] == "mdstats.atomic-reference-fit-record.v3"
    assert payload["foundation_identity_digest"] == mh1.canonical_content_digest
    assert "foundation_checkpoint_digest" not in payload
    assert mdstats.AtomicReferenceFitRecord.from_dict(payload).to_dict() == payload

    legacy = _reference_fit(legacy_sha=_mpa0().sha256)
    legacy_payload = legacy.to_dict()
    assert legacy_payload["schema"] == "mdstats.atomic-reference-fit-record.v2"
    assert mdstats.AtomicReferenceFitRecord.from_dict(legacy_payload).to_dict() == legacy_payload
    assert mdstats.foundation_identity_matches_lineage(
        _mpa0(), legacy_checkpoint_digest=legacy.foundation_checkpoint_digest
    )
    assert not mdstats.foundation_identity_matches_lineage(
        mh1, legacy_checkpoint_digest=mh1.sha256
    )


def _training_evidence(*, identity: str) -> mdstats.TargetSizeStudyTrainingEvidence:
    return mdstats.TargetSizeStudyTrainingEvidence(
        stage="coarse", target_size=128, optimizer_seed=1, completed_epochs=3,
        optimizer_update_count=30, structures_presented=384,
        instantaneous_learning_rate=1e-4, wall_time_seconds=1.0, target_force_score_mev_per_a=20.0,
        foundation_identity_digest=identity, evaluation_role_digest=_d("8"), training_policy_digest=_d("9"),
        target_size_study_policy_digest=_d("0"), training_run_digest=_d("a"),
        candidate_data_digest=_d("1"),
        checkpoint_digest=_d("b"), schedule_digest=_d("c"), optimizer_state_digest=_d("d"),
        rng_state_digest=_d("f"), target_evaluation_digest=_d("e"),
    )


def test_lineage1_target_size_evidence_v3_binds_head_qualified_identity() -> None:
    omat = _mh1("omat_pbe")
    omol = _mh1("omol")
    a = _training_evidence(identity=omat.canonical_content_digest)
    b = _training_evidence(identity=omol.canonical_content_digest)
    assert a.to_dict()["schema"] == "mdstats.target-size-training-evidence.v10"
    assert a.to_dict()["content_digest"] != b.to_dict()["content_digest"]
    assert mdstats.TargetSizeStudyTrainingEvidence.from_dict(a.to_dict()).to_dict() == a.to_dict()
