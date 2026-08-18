from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import campaign_cli
from mdstats.training_data.storage_accounting import (
    ArtifactRetentionClass,
    build_campaign_storage_report,
    configured_protected_inputs,
)


_LOCKED_MH1_SHA = "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"
_LOCKED_MPA0_SHA = "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _storage_config(tmp_path: Path) -> Path:
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"external-foundation")
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="../training",
            foundation_model="foundation.model",
            replay_train="../replay-train.xyz",
            replay_monitor="../replay-monitor.xyz",
            replay_true_labels="../true-labels",
        ),
        encoding="utf-8",
    )
    return config


def test_cert1_storage_protects_external_and_selected_head_foundations(tmp_path: Path) -> None:
    config = _storage_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    selected_root = paths.internal / "foundation-selected-head"
    selected_root.mkdir(parents=True)
    selected = selected_root / "mace_mh_1-omat_pbe.model"
    selected.write_bytes(b"qualified-derived-training-foundation")

    report = build_campaign_storage_report(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
        largest_limit=100,
    ).to_dict()
    families = {item["family"]: item for item in report["families"]}

    protected = {
        item["key"]: item for item in report["ownership_catalog"]["protected_inputs"]
    }
    external = protected["foundation_model"]
    assert external["retention_class"] == ArtifactRetentionClass.PROTECTED_INPUT.value
    assert external["automatic_reclamation_eligibility"] == "prohibited"
    assert external["manual_reclamation_eligibility"] == "prohibited"

    derived = families["selected_head_training_foundation"]
    assert derived["retention_class"] == ArtifactRetentionClass.RESTART_CRITICAL.value
    assert derived["automatic_reclamation_eligibility"] == "prohibited"
    assert derived["manual_reclamation_eligibility"] == "prohibited"
    assert "mh1_selected_head_training_restart" in derived["capability_lost_if_deleted"]
    assert "exact_training_foundation_reproduction" in derived["capability_lost_if_deleted"]


def test_cert1_manual_and_automatic_cleanup_never_select_selected_head_foundation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _storage_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    selected = paths.internal / "foundation-selected-head" / "mace_mh_1-omat_pbe.model"
    selected.parent.mkdir(parents=True)
    selected.write_bytes(b"qualified-derived-training-foundation")

    auto = campaign_cli._campaign_cleanup(cfg, paths, store, phase="cert1")
    assert selected.is_file()
    assert all(Path(str(item["path"])) != selected for item in auto.actions)

    # Exercise the most consequential STOR4 plan without requiring unrelated
    # historical authority fixtures.  The selected-head training foundation is
    # not a candidate even when compact planning is otherwise authorized.
    campaign_cli._mark_stage(store, paths, "verify", campaign_cli.StageState.COMPLETE, "complete")
    (paths.models / "production.model").write_bytes(b"production")
    monkeypatch.setattr(campaign_cli, "_has_authoritative_protocol_freeze", lambda _store: True)
    compact = campaign_cli._build_manual_tier_report(
        "compact", cfg, paths, store, dry_run=True
    )
    assert selected.is_file()
    assert all(Path(str(item["path"])) != selected for item in compact.actions)
    plan = campaign_cli._manual_reclamation_plan_payload(
        tier="compact", reports=(compact,), apply_requested=False, archive_pending=False
    )
    assert "qualified_selected_head_training_foundation" in plan["protected_by_all_tiers"]
    assert plan["capability_report"]["capabilities"]["selected_head_training_foundation"]["status"] == "preserved"


@pytest.mark.slow
def test_cert1_locked_real_fixture_identity_matrix() -> None:
    mh1 = Path(os.environ.get("MDSTATS_TEST_MH1_MODEL", "/mnt/data/mace-mh-1.model"))
    mpa0 = Path(os.environ.get("MDSTATS_TEST_MPA0_MODEL", "/mnt/data/mace-mpa-0-medium.model"))
    if not mh1.is_file() or not mpa0.is_file():
        pytest.skip("locked MACE foundation fixtures are not available")

    assert _sha256(mh1) == _LOCKED_MH1_SHA
    assert _sha256(mpa0) == _LOCKED_MPA0_SHA

    mh1_omat = mdstats.MaceFoundationSpec(
        family="mace_mh_1", requested_head="omat_pbe", requested_atomic_numbers=(3, 11, 19)
    ).resolve_file(mh1)
    mh1_second = mdstats.MaceFoundationSpec(
        family="mace_mh_1", requested_head="omol", requested_atomic_numbers=(3, 11, 19)
    ).resolve_file(mh1)
    mpa = mdstats.MaceFoundationSpec(
        family="mace_mpa_0", requested_head="default", requested_atomic_numbers=(3, 11, 19)
    ).resolve_file(mpa0)

    assert mh1_omat.sha256 == _LOCKED_MH1_SHA
    assert mh1_second.sha256 == _LOCKED_MH1_SHA
    assert mh1_omat.canonical_content_digest != mh1_second.canonical_content_digest
    assert "omat_pbe" in mh1_omat.available_heads and "omol" in mh1_omat.available_heads
    assert mpa.available_heads == ("default",)

    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.MaceFoundationSpec(
            family="mace_mh_1", requested_head="not_a_real_head", requested_atomic_numbers=(3,)
        ).resolve_file(mh1)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.MaceFoundationSpec(
            family="mace_mh_1", requested_head=None, requested_atomic_numbers=(3,)
        ).resolve_file(mh1)

    # Certification itself must never mutate the source foundation bytes.
    assert _sha256(mh1) == _LOCKED_MH1_SHA
    assert _sha256(mpa0) == _LOCKED_MPA0_SHA


@pytest.mark.slow
def test_cert1_second_real_mh1_head_e3nn_inference_and_data6_lineage(tmp_path: Path) -> None:
    mh1 = Path(os.environ.get("MDSTATS_TEST_MH1_MODEL", "/mnt/data/mace-mh-1.model"))
    if not mh1.is_file():
        pytest.skip("locked MH-1 fixture is not available")

    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="training",
            foundation_model=str(mh1),
            replay_train="replay-train.xyz",
            replay_monitor="replay-monitor.xyz",
            foundation_family="mace_mh_1",
            foundation_head="omol",
            acceleration_backend="e3nn",
            default_device="cpu",
            precision_profile="double",
        ),
        encoding="utf-8",
    )
    cfg, paths = campaign_cli._load_config(config)
    identity = campaign_cli._model_checkpoint_identity(cfg, paths)
    assert identity.foundation_head == "omol"
    assert identity.foundation_bound

    provider, returned = campaign_cli._provider(cfg, paths, checkpoint_identity=identity)
    assert returned.content_digest == identity.content_digest
    from ase import Atoms
    atoms = Atoms(
        symbols=["Na", "Cl"],
        positions=[[0.0, 0.0, 0.0], [2.8, 0.0, 0.0]],
        cell=[12.0, 12.0, 12.0],
        pbc=True,
    )
    descriptors, predictions = provider.evaluate_batch(
        (atoms,), mdstats.MaceDescriptorPolicy(invariants_only=True)
    )
    prediction = predictions[0]
    assert prediction.energy_ev == pytest.approx(float(prediction.energy_ev))
    assert prediction.forces_ev_per_angstrom.shape == (2, 3)
    assert descriptors[0].shape[0] == 2
    assert descriptors[0].shape[1] > 0

    omat = mdstats.MaceFoundationSpec(
        family="mace_mh_1", requested_head="omat_pbe", requested_atomic_numbers=(11, 17)
    ).resolve_file(mh1)
    assert identity.foundation_potential_digest != omat.canonical_content_digest
