from __future__ import annotations

from pathlib import Path

import pytest
import numpy as np
from ase import Atoms
from ase.io import write

import mdstats
from mdstats.training_data import campaign_execution as ce
from mdstats.training_data.evaluation_predictions import prediction_key


def _digest(ch: str) -> str:
    return ch * 64


def _foundation(*, head: str = "omat_pbe"):
    potential = mdstats.FoundationPotentialIdentity(
        reference="/tmp/mace-mh-1.model",
        sha256=_digest("a"),
        foundation_head=head,
        model_family="mace_mh_1",
        architecture_signature=_digest("b"),
        model_atomic_numbers=(3, 8, 11, 13, 14, 17, 19),
        available_heads=("omat_pbe", "omol"),
        inspection_state="inspected",
    )
    inference = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="0.3.16",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    return potential, inference


def _policy(*, inference=None, potential=None):
    return mdstats.CheckpointEvaluationPolicy(
        target_head_name="target_head",
        replay_head_name="pt_head",
        replay_baseline_head_name=None if potential is not None else "default",
        foundation_potential_identity=potential,
        foundation_inference_identity=inference,
        default_dtype="float32",
        device="cpu",
        acceleration_policy=mdstats.MaceAccelerationPolicy(backend="e3nn"),
    )


def test_eval1_policy_derives_source_head_and_preserves_candidate_heads():
    potential, inference = _foundation()
    policy = _policy(potential=potential, inference=inference)
    assert policy.source_foundation_head_name == "omat_pbe"
    assert policy.target_head_name == "target_head"
    assert policy.replay_head_name == "pt_head"
    assert policy.to_dict()["schema"] == "mdstats.checkpoint-evaluation-policy.v8"
    assert "replay_baseline_head_name" not in policy.to_dict()
    restored = mdstats.CheckpointEvaluationPolicy.from_dict(policy.to_dict())
    assert restored.policy_digest == policy.policy_digest
    assert restored.source_foundation_head_name == "omat_pbe"
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.CheckpointEvaluationPolicy(
            replay_baseline_head_name="omol",
            foundation_potential_identity=potential,
            foundation_inference_identity=inference,
            default_dtype="float32",
            acceleration_policy=mdstats.MaceAccelerationPolicy(backend="e3nn"),
        )


def test_eval1_prediction_cache_key_binds_foundation_inference_only_for_baseline():
    potential, inference = _foundation()
    policy = _policy(potential=potential, inference=inference)
    candidate = ce._evaluation_prediction_key(
        model_sha256=_digest("c"), head="target_head", geometry_identities=("g1",), policy=policy
    )
    baseline = ce._evaluation_prediction_key(
        model_sha256=potential.sha256,
        head=potential.foundation_head,
        geometry_identities=("g1",),
        policy=policy,
        foundation_inference_digest=inference.content_digest,
    )
    assert candidate.to_dict()["schema"] == "mdstats.evaluation-prediction-key.v1"
    assert baseline.to_dict()["schema"] == "mdstats.evaluation-prediction-key.v2"
    assert baseline.foundation_inference_digest == inference.content_digest
    other = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="0.3.17",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    other_key = prediction_key(
        model_sha256=potential.sha256,
        head_name=potential.foundation_head,
        geometry_identities=("g1",),
        default_dtype="float32",
        device="cpu",
        acceleration_policy_digest=policy.acceleration_policy.policy_digest,
        foundation_inference_digest=other.content_digest,
    )
    assert other_key.content_digest != baseline.content_digest


def test_eval1_v4_pseudolabels_reuse_only_exact_generator_identity(tmp_path: Path):
    potential, inference = _foundation()
    policy = _policy(potential=potential, inference=inference)
    atoms = Atoms("LiCl", positions=[[0, 0, 0], [2.0, 0, 0]], cell=[8, 8, 8], pbc=True)
    atoms.info["REF_energy"] = -1.25
    atoms.arrays["REF_forces"] = np.asarray([[0.1, 0.0, 0.0], [-0.1, 0.0, 0.0]], dtype=float)
    atoms.info["REF_stress"] = np.zeros(6, dtype=float)
    path = tmp_path / "replay.extxyz"
    write(path, [atoms], format="extxyz")
    artifact = mdstats.inspect_replay_extxyz(
        path,
        label_mode=mdstats.ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        foundation_label_generator_identity_digest=inference.content_digest,
    )
    result = ce._pseudolabel_foundation_predictions(
        path,
        artifact,
        artifact,
        baseline_sha256=potential.sha256,
        head=potential.foundation_head,
        policy=policy,
    )
    assert result is not None and len(result[0]) == 1
    wrong = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="0.3.17",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    bad_policy = _policy(potential=potential, inference=wrong)
    assert ce._pseudolabel_foundation_predictions(
        path, artifact, artifact,
        baseline_sha256=potential.sha256,
        head=potential.foundation_head,
        policy=bad_policy,
    ) is None


def test_eval1_data6_reuse_requires_exact_inference_identity(monkeypatch, tmp_path: Path):
    from types import SimpleNamespace
    from mdstats.training_data import production_model_sweep as pms

    potential, inference = _foundation()
    policy = _policy(potential=potential, inference=inference)
    checkpoint = SimpleNamespace(
        foundation_bound=True,
        checkpoint_sha256=potential.sha256,
        foundation_head=potential.foundation_head,
        foundation_potential_digest=potential.canonical_content_digest,
        foundation_inference_digest=inference.content_digest,
        default_dtype="float32",
        device="cpu",
        metadata=(("acceleration_policy_digest", policy.acceleration_policy.policy_digest),),
    )
    manifest = SimpleNamespace(checkpoint_identity=checkpoint, content_digest=_digest("d"))
    monkeypatch.setattr(pms, "read_atomic_model_prediction", lambda *_args, **_kwargs: "prediction")
    good = ce._data6_foundation_predictions(
        manifest, tmp_path, ("frame-1",),
        baseline_sha256=potential.sha256,
        head=potential.foundation_head,
        policy=policy,
    )
    assert good is not None and good[0] == ("prediction",)

    other = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="0.3.17",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    bad_policy = _policy(potential=potential, inference=other)
    assert ce._data6_foundation_predictions(
        manifest, tmp_path, ("frame-1",),
        baseline_sha256=potential.sha256,
        head=potential.foundation_head,
        policy=bad_policy,
    ) is None


def test_eval1_foundation_audit_v2_round_trip(tmp_path: Path):
    from dataclasses import replace
    from tests.test_mlff_foundation_audit1 import _build_audit

    *_, audit, _ = _build_audit(tmp_path / "audit")
    potential = mdstats.FoundationPotentialIdentity(
        reference="/tmp/foundation.model",
        sha256=audit.foundation_checkpoint_sha256,
        foundation_head="omat_pbe",
        model_family="mace_mh_1",
        architecture_signature=_digest("b"),
        model_atomic_numbers=(3, 8, 11, 13, 14, 17, 19),
        available_heads=("omat_pbe", "omol"),
        inspection_state="inspected",
    )
    inference = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="0.3.16",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    canonical = replace(
        audit,
        foundation_potential_identity=potential,
        foundation_inference_identity=inference,
        serialization_schema="mdstats.foundation-target-audit.v2",
    )
    payload = canonical.to_dict()
    assert payload["schema"] == "mdstats.foundation-target-audit.v2"
    assert payload["foundation_potential_identity"]["foundation_head"] == "omat_pbe"
    restored = mdstats.FoundationTargetAudit.from_dict(payload)
    assert restored.content_digest == canonical.content_digest
    assert restored.foundation_inference_identity.content_digest == inference.content_digest


def test_eval1_pes_campaign_v2_round_trip():
    from tests.test_mlff_pes_verify1 import _base_atoms, _deploy_probe_set, _reference_payload, _d

    targets = (_base_atoms(),)
    pes_policy = mdstats.PESVerifyPolicy(maximum_base_configurations=1, maximum_modes_per_base=2, include_strain_modes=False)
    probe_set, request_atoms = mdstats.build_pes_probe_set(_deploy_probe_set(1), targets, policy=pes_policy)
    reference = _reference_payload(request_atoms)
    foundation_sha = _d("foundation")
    foundation = mdstats.assess_pes_model(
        probe_set, reference, reference, policy=pes_policy, model_role="foundation", model_sha256=foundation_sha
    )
    candidate = mdstats.assess_pes_model(
        probe_set, reference, reference, policy=pes_policy, model_role="candidate", model_sha256=_d("candidate")
    )
    request = mdstats.PESProbeRequestArtifact(
        probe_set_digest=probe_set.content_digest,
        extxyz_path="request.extxyz", extxyz_sha256=_d("request"),
        manifest_path="manifest.json", manifest_sha256=_d("manifest"),
        configuration_count=len(probe_set.probes),
        poscar_sha256s=tuple((f"{i}/POSCAR", _d(f"poscar-{i}")) for i in range(len(probe_set.probes))),
    )
    ref_artifact = mdstats.PESReferenceArtifact(
        probe_set_digest=probe_set.content_digest,
        reference_path="reference.extxyz", reference_sha256=_d("reference"), configuration_count=len(probe_set.probes),
        prediction_digest=_d("predictions"), protocol_digest=_d("protocol"), protocol_source="test",
    )
    run = mdstats.PESVerifyRunRecord(
        run_plan_digest=_d("run"), deploy_verify_run_digest=_d("deploy-run"),
        candidate_model_path="candidate.model", candidate_model_sha256=_d("candidate"), candidate_qualification=candidate,
    )
    potential = mdstats.FoundationPotentialIdentity(
        reference="/tmp/mace-mh-1.model", sha256=foundation_sha, foundation_head="omat_pbe",
        model_family="mace_mh_1", architecture_signature=_digest("b"),
        model_atomic_numbers=(3, 8, 11, 13, 14, 17, 19), available_heads=("omat_pbe", "omol"), inspection_state="inspected",
    )
    inference = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest, default_dtype="float32",
        backend="e3nn", resolved_kernel_mode="e3nn", mace_version="0.3.16", adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    campaign = mdstats.PESVerifyCampaignRecord(
        campaign_plan_digest=_d("campaign"), deploy_verify_campaign_digest=_d("deploy-campaign"),
        foundation_audit_digest=_d("foundation-audit"), foundation_model_sha256=foundation_sha,
        policy=pes_policy, probe_set=probe_set, probe_request=request, reference_artifact=ref_artifact,
        foundation_qualification=foundation, run_records=(run,), stage_context="production",
        foundation_head_name="omat_pbe", foundation_potential_identity=potential, foundation_inference_identity=inference,
    )
    payload = campaign.to_dict()
    assert payload["schema"] == "mdstats.pes-verify-campaign.v2"
    restored = mdstats.PESVerifyCampaignRecord.from_dict(payload)
    assert restored.content_digest == campaign.content_digest
    assert restored.foundation_potential_identity.canonical_content_digest == potential.canonical_content_digest
    assert restored.foundation_inference_identity.content_digest == inference.content_digest
