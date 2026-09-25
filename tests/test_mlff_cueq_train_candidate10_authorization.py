from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import acceleration, campaign_cli


def _candidate10_key(*, horizon: int = 30):
    method = {
        "candidate_commit": acceleration.CUEQ_C10_CANDIDATE_COMMIT,
        "candidate_blob": acceleration.CUEQ_C10_CANDIDATE_BLOB,
        "accepted_parent_kernel": acceleration.CUEQ_C10_ACCEPTED_PARENT_KERNEL,
        "accepted_parent_source": acceleration.CUEQ_C10_ACCEPTED_PARENT_SOURCE,
        "risk_binding_blob": acceleration.CUEQ_C10_RISK_BINDING_BLOB,
        "law_binding_blob": acceleration.CUEQ_C10_LAW_BINDING_BLOB,
    }
    coordinates = {
        "d": "float32",
        "theta_0": {"model": "model-digest"},
        "q_0": {"state": "state-digest"},
        "D": {"corpus": "corpus-digest"},
        "E": {"role": "cv", "consumer": "consumer-digest"},
        "O": {"objective": "objective-digest"},
        "H": {"horizon": horizon, "schedule": "schedule-digest"},
        "K": {"reference": "e3nn", "candidate": "cueq_pure"},
        "rho": {"runtime": "runtime-digest"},
        "m": method,
        "R": {
            "eta_NI": 0.09,
            "q_cat": 0.09,
            "n": 300,
            "Q": {
                "ratified_law_role_binding_blob": acceleration.CUEQ_C10_LAW_BINDING_BLOB,
                "execution_owner_sources": {"owner": "source-digest"},
            },
        },
    }
    return mdstats.TrainingAccelerationCueqCandidate10Key.from_coordinates(coordinates)


def _passing_record(key):
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    manifest = {
        "preflight": {"content_digest": digest("preflight")},
        "production_law": {"content_digest": digest("production-law")},
        "runtime": {"content_digest": digest("runtime")},
        "triplets": [
            {"triplet_index": index, "content_digest": digest(f"triplet-{index}")}
            for index in range(1, 301)
        ],
        "production_start_fixture": {"content_digest": digest("production-start")},
        "materiality": {"content_digest": digest("materiality")},
        "systematic_scores": {"content_digest": digest("systematic-scores")},
        "scientific_decisions": {"content_digest": digest("decisions")},
        "adversaries": {"content_digest": digest("adversaries")},
        "independent_reducer_recheck": {"content_digest": digest("reducer-recheck")},
    }
    assessment = {
        "triplet_count": 300,
        "valid_triplet_count": 300,
        "reference_materiality_events": 0,
        "candidate_materiality_events": 0,
        "reference_materiality_cp_upper": 0.014500594315008053,
        "candidate_materiality_cp_upper": 0.014500594315008053,
        "score_max_worse_count": 154,
        "score_max_cp_upper": 0.5791687402693169,
        "score_sigma_worse_count": 154,
        "score_sigma_cp_upper": 0.5791687402693169,
        "exact_scientific_decisions_equal": True,
        "production_start_law_passed": True,
        "adversaries_passed": True,
        "same_key_retry": False,
    }
    return mdstats.TrainingAccelerationCueqCandidate10QualificationRecord.create(
        key=key,
        status="PASS",
        candidate_identity={
            "candidate_commit": acceleration.CUEQ_C10_CANDIDATE_COMMIT,
            "candidate_blob": acceleration.CUEQ_C10_CANDIDATE_BLOB,
            "accepted_parent_kernel": acceleration.CUEQ_C10_ACCEPTED_PARENT_KERNEL,
            "accepted_parent_source": acceleration.CUEQ_C10_ACCEPTED_PARENT_SOURCE,
            "risk_binding_blob": acceleration.CUEQ_C10_RISK_BINDING_BLOB,
            "law_binding_blob": acceleration.CUEQ_C10_LAW_BINDING_BLOB,
        },
        risk_instance=acceleration.CUEQ_C10_RISK_INSTANCE,
        evidence_manifest=manifest,
        assessment=assessment,
    )


def _write_campaign(tmp_path: Path, *, dtype: str = "float32"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    config = tmp_path / "campaign.toml"
    text = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="mace-mh-1.model",
        replay_train="replay_train.xyz",
        replay_monitor="replay_monitor.xyz",
    ).replace('dtype = "float32"', f'dtype = "{dtype}"')
    config.write_text(text, encoding="utf-8")
    cfg, paths = campaign_cli._load_config(config)
    campaign_cli.CampaignStore(paths.state_db).close()
    return cfg, paths


def test_candidate10_record_authorizes_only_its_exact_key():
    key = _candidate10_key()
    record = _passing_record(key)
    resolved = mdstats.resolve_training_acceleration_cueq_candidate10_authorization(
        key=key, record_payload=record.to_dict()
    )
    assert resolved.authorized
    assert resolved.key_digest == key.key_digest
    assert resolved.record_digest == record.content_digest

    other_key = _candidate10_key(horizon=31)
    wrong_key = mdstats.resolve_training_acceleration_cueq_candidate10_authorization(
        key=other_key, record_payload=record.to_dict()
    )
    assert wrong_key.status is mdstats.TrainingAccelerationCueqCandidate10AuthorizationStatus.WRONG_KEY
    assert not wrong_key.authorized


def test_candidate10_stale_or_incomplete_records_never_authorize():
    key = _candidate10_key()
    record = _passing_record(key)
    stale_record = mdstats.TrainingAccelerationCueqCandidate10QualificationRecord.create(
        key=key,
        status="PASS",
        candidate_identity={**record.candidate_identity, "candidate_commit": "f" * 40},
        risk_instance=record.risk_instance,
        evidence_manifest=record.evidence_manifest,
        assessment=record.assessment,
    )
    stale = mdstats.resolve_training_acceleration_cueq_candidate10_authorization(
        key=key, record_payload=stale_record.to_dict()
    )
    assert stale.status is mdstats.TrainingAccelerationCueqCandidate10AuthorizationStatus.STALE

    incomplete = mdstats.TrainingAccelerationCueqCandidate10QualificationRecord.create(
        key=key,
        status="PASS",
        candidate_identity=record.candidate_identity,
        risk_instance=record.risk_instance,
        evidence_manifest={"triplets": []},
        assessment=record.assessment,
    )
    invalid = mdstats.resolve_training_acceleration_cueq_candidate10_authorization(
        key=key, record_payload=incomplete.to_dict()
    )
    assert invalid.status is mdstats.TrainingAccelerationCueqCandidate10AuthorizationStatus.INVALID

    failed_record = mdstats.TrainingAccelerationCueqCandidate10QualificationRecord.create(
        key=key,
        status="FAIL",
        candidate_identity=record.candidate_identity,
        risk_instance=record.risk_instance,
        evidence_manifest=record.evidence_manifest,
        assessment=record.assessment,
    )
    failed = mdstats.resolve_training_acceleration_cueq_candidate10_authorization(
        key=key, record_payload=failed_record.to_dict()
    )
    assert failed.status is mdstats.TrainingAccelerationCueqCandidate10AuthorizationStatus.FAILED


def test_legacy_rev86_qualified_record_does_not_authorize_cueq_launch(tmp_path: Path):
    cfg, paths = _write_campaign(tmp_path)
    checkpoint = tmp_path / "selected-head.model"
    checkpoint.write_bytes(b"selected-head-training-bytes")
    legacy = mdstats.TrainingAccelerationRealizationRecord(
        requested_backend="cueq",
        training_kernel_mode="cueq_pure",
        device=str(cfg["training"]["device"]),
        dtype=str(cfg["training"]["dtype"]),
        training_checkpoint_reference=str(checkpoint.resolve()),
        training_checkpoint_sha256=campaign_cli._sha256(checkpoint),
        selected_head_qualification_digest="b" * 64,
        mace_version="0.3.16",
        cueq_versions=(("cuequivariance", "test"),),
        training_parity_record_digest="c" * 64,
        qualified=True,
    )
    store = campaign_cli.CampaignStore(paths.state_db)
    store.put_record("training_acceleration_realization", legacy)
    store.close()

    optimizer = campaign_cli._optimizer_policy(cfg, seed=7, num_workers=0, paths=paths)
    assert optimizer.acceleration_realization_digest is None
    failure = mdstats.training_acceleration_candidate10_launch_failure(optimizer)
    assert failure is not None and "exact current Candidate-10 record" in failure


def test_exact_candidate10_record_is_consumed_by_optimizer_owner(tmp_path: Path):
    cfg, paths = _write_campaign(tmp_path)
    key = _candidate10_key()
    record = _passing_record(key)
    store = campaign_cli.CampaignStore(paths.state_db)
    store.put_record(
        campaign_cli._training_acceleration_cueq_candidate10_record_key(key.key_digest),
        record,
    )
    store.close()

    optimizer = campaign_cli._optimizer_policy(
        cfg, seed=7, num_workers=0, paths=paths, candidate10_key=key
    )
    assert optimizer.acceleration_policy.backend is mdstats.MaceAccelerationBackend.CUEQ
    assert optimizer.resolved_acceleration_kernel_mode == "cueq_pure"
    assert optimizer.acceleration_realization_digest == record.content_digest


def test_pending_candidate10_record_blocks_launch_and_fp64_is_unsupported(tmp_path: Path):
    cfg, paths = _write_campaign(tmp_path)
    pending = campaign_cli._stored_training_cueq_candidate10_authorization(
        cfg, paths, key=_candidate10_key()
    )
    assert pending.status is mdstats.TrainingAccelerationCueqCandidate10AuthorizationStatus.PENDING
    optimizer = campaign_cli._optimizer_policy(
        cfg, seed=1, num_workers=0, paths=paths, candidate10_key=_candidate10_key()
    )
    assert optimizer.acceleration_realization_digest is None
    assert "exact current Candidate-10 record" in mdstats.training_acceleration_candidate10_launch_failure(
        optimizer
    )

    fp64_cfg, fp64_paths = _write_campaign(tmp_path / "fp64", dtype="float64")
    unsupported = campaign_cli._stored_training_cueq_candidate10_authorization(
        fp64_cfg, fp64_paths, key=None
    )
    assert unsupported.status is mdstats.TrainingAccelerationCueqCandidate10AuthorizationStatus.UNSUPPORTED
