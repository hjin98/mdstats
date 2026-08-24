from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import mdstats
from mdstats.training_data import campaign_cli


def _frame_data() -> mdstats.FrameData:
    return mdstats.FrameData(
        source_frame_indices=np.array([0, 1], dtype=np.int64),
        frame_ids=np.array([7, 8], dtype=np.int64),
        steps=np.array([0, 1], dtype=np.int64),
        times_ps=np.array([0.0, 0.001]),
        atomic_numbers=np.array([3, 8], dtype=np.int32),
        pbc=np.array([True, True, True]),
        cells_angstrom=np.repeat(np.eye(3)[None, :, :] * 10.0, 2, axis=0),
        fractional_positions=np.array(
            [
                [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]],
                [[0.01, 0.0, 0.0], [0.25, 0.25, 0.25]],
            ]
        ),
        energies_ev=np.array([-10.0, -9.9]),
        forces_ev_per_angstrom=np.zeros((2, 2, 3)),
        stresses_ev_per_angstrom3=np.zeros((2, 3, 3)),
        temperatures_kelvin=np.array([700.0, np.nan]),
        scf_iteration_limit_reached=(False, None),
    )


def _catalog() -> SimpleNamespace:
    source = SimpleNamespace(
        run_id="run-a",
        source_identity_signature="1" * 64,
        source_control_bundle_signature="2" * 64,
        frame_count=2,
        composition=SimpleNamespace(atom_count=2),
    )
    return SimpleNamespace(sources=(source,), content_digest="3" * 64)


def test_normalized_frame_cache_roundtrip_and_corruption_detection(tmp_path: Path) -> None:
    catalog = _catalog()
    expected = _frame_data()
    manifest = mdstats.write_frame_data_cache(catalog, {"run-a": expected}, tmp_path / "cache")
    assert manifest.is_file()
    restored = mdstats.load_frame_data_cache(catalog, tmp_path / "cache")["run-a"]
    for name in (
        "source_frame_indices",
        "frame_ids",
        "steps",
        "times_ps",
        "atomic_numbers",
        "pbc",
        "cells_angstrom",
        "fractional_positions",
        "energies_ev",
        "forces_ev_per_angstrom",
        "stresses_ev_per_angstrom3",
        "temperatures_kelvin",
    ):
        np.testing.assert_equal(getattr(restored, name), getattr(expected, name))
    assert restored.scf_iteration_limit_reached == expected.scf_iteration_limit_reached

    cache_manifest = json.loads(manifest.read_text(encoding="utf-8"))
    array_path = manifest.parent / cache_manifest["records"][0]["relative_path"]
    array_path.write_bytes(array_path.read_bytes() + b"corruption")
    with pytest.raises(mdstats.TrainingDataSerializationError, match="hash mismatch"):
        mdstats.load_frame_data_cache(catalog, tmp_path / "cache")


def test_campaign_store_externalizes_large_records_and_verifies_checksum(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / ".mdstats" / "campaign.sqlite3")
    payload = {"schema": "large.v1", "values": list(range(300_000))}
    store.put_record("data4", payload)
    assert store.get_payload("data4") == payload

    import sqlite3

    with sqlite3.connect(store.path) as db:
        stored = json.loads(db.execute("SELECT payload FROM records WHERE key='data4'").fetchone()[0])
    assert stored["schema"] == campaign_cli.EXTERNAL_RECORD_POINTER_SCHEMA
    external = store.path.parent / stored["relative_path"]
    assert external.is_file()
    assert store.path.stat().st_size < external.stat().st_size

    external.write_text("{}", encoding="utf-8")
    with pytest.raises(campaign_cli.CampaignCliError, match="checksum mismatch"):
        store.get_payload("data4")


def test_campaign_store_keeps_small_records_inline(tmp_path: Path) -> None:
    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite3")
    payload = {"schema": "small.v1", "value": 4}
    store.put_record("small", payload)
    assert store.get_payload("small") == payload
    assert not store.external_record_directory.exists()


def test_campaign_store_shards_data4_without_full_payload_materialization(tmp_path: Path) -> None:
    from tests.test_mlff_data9a7d_profile_extension_migration import _lta_data4

    _, _, _, bundle = _lta_data4(tmp_path / "dataset")
    store = campaign_cli.CampaignStore(tmp_path / "campaign" / ".mdstats" / "campaign.sqlite3")
    store.put_record("data4", bundle)
    restored = store.get_record("data4", mdstats.Data4FeatureBundle)
    assert restored == bundle
    assert restored.content_digest == bundle.content_digest

    import sqlite3

    with sqlite3.connect(store.path) as db:
        pointer = json.loads(db.execute("SELECT payload FROM records WHERE key='data4'").fetchone()[0])
    from mdstats.training_data.data4_sharded_store import DATA4_SHARDED_POINTER_SCHEMA

    assert pointer["schema"] == DATA4_SHARDED_POINTER_SCHEMA
    manifest = store.path.parent / pointer["relative_path"]
    assert manifest.is_file()
    assert (manifest.parent / "raw-records.jsonl").is_file()
    assert (manifest.parent / "lta-mobile-states.jsonl").is_file()

    (manifest.parent / "raw-records.jsonl").write_text("{}\n", encoding="utf-8")
    with pytest.raises(campaign_cli.CampaignCliError, match="Checksum mismatch"):
        store.get_record("data4", mdstats.Data4FeatureBundle)


def test_campaign_store_rewrites_corrupt_existing_data4_shards(tmp_path: Path) -> None:
    from tests.test_mlff_data9a7d_profile_extension_migration import _lta_data4

    _, _, _, bundle = _lta_data4(tmp_path / "dataset")
    store = campaign_cli.CampaignStore(tmp_path / "campaign" / ".mdstats" / "campaign.sqlite3")
    store.put_record("data4", bundle)

    import sqlite3

    with sqlite3.connect(store.path) as db:
        pointer = json.loads(db.execute("SELECT payload FROM records WHERE key='data4'").fetchone()[0])
    manifest = store.path.parent / pointer["relative_path"]
    raw = manifest.parent / "raw-records.jsonl"
    raw.write_text("{}\n", encoding="utf-8")

    # Re-persisting the same content-addressed bundle must not silently reuse
    # corrupt shards.  The directory is validated, discarded, and rebuilt.
    store.put_record("data4", bundle)
    restored = store.get_record("data4", mdstats.Data4FeatureBundle)
    assert restored == bundle
    assert restored.content_digest == bundle.content_digest


def test_cached_sha256_reuses_unchanged_file_and_invalidates_on_change(tmp_path):
    import mdstats.training_data._common as common

    path = tmp_path / "large-artifact.bin"
    path.write_bytes(b"first-version")
    common._sha256_file_for_identity.cache_clear()
    before = common._sha256_file_for_identity.cache_info()
    first = common.sha256_file_cached(path)
    after_first = common._sha256_file_for_identity.cache_info()
    second = common.sha256_file_cached(path)
    after_second = common._sha256_file_for_identity.cache_info()
    assert first == second
    assert after_first.misses == before.misses + 1
    assert after_second.hits == after_first.hits + 1

    path.write_bytes(b"second-version-with-different-size")
    third = common.sha256_file_cached(path)
    after_third = common._sha256_file_for_identity.cache_info()
    assert third != first
    assert after_third.misses == after_second.misses + 1


def test_prepare_sweep_reuses_matching_complete_checkpoint_without_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    frames = SimpleNamespace(frames=(SimpleNamespace(frame_uid="f0"),), content_digest="f" * 64)
    data5 = SimpleNamespace(content_digest="5" * 64)
    sources = SimpleNamespace(content_digest="s" * 64)
    expected_plan = SimpleNamespace(content_digest="p" * 64, requested_frame_uids=("f0",))
    checkpoint = SimpleNamespace(
        plan=expected_plan,
        content_digest="c" * 64,
        status=SimpleNamespace(value="complete"),
        completed_frame_uids=("f0",),
    )
    restored = SimpleNamespace(complete=True, checkpoint=checkpoint)

    monkeypatch.setattr(
        campaign_cli._core,
        "_load_prepared",
        lambda store, include_data4=False: (sources, frames, None, data5),
    )
    monkeypatch.setattr(
        campaign_cli._core,
        "_model_checkpoint_identity",
        lambda cfg, paths: SimpleNamespace(content_digest="i" * 64),
    )
    monkeypatch.setattr(
        mdstats,
        "build_data6_model_sweep_plan",
        lambda *args, **kwargs: expected_plan,
    )
    monkeypatch.setattr(
        mdstats,
        "load_data6_model_sweep_artifacts",
        lambda *args, **kwargs: restored,
    )
    monkeypatch.setattr(
        campaign_cli._core,
        "_provider",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("provider must not load")),
    )

    class Store:
        def __init__(self):
            self.records = {}

        def put_record(self, key, value):
            self.records[key] = value

    store = Store()
    internal = tmp_path / ".mdstats"
    internal.mkdir()
    paths = SimpleNamespace(internal=internal, workspace=tmp_path, config=tmp_path / "campaign.toml", config_dir=tmp_path)
    result = campaign_cli._prepare_sweep(
        {"paths": {"training_root": str(tmp_path)}}, paths, store, max_new_frames=None, frame_data_by_run={}
    )
    assert result is restored
    assert store.records["model_sweep_checkpoint"]["completed_frames"] == 1



def test_prepare_sweep_recovery_calibration_uses_numpy_linspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    requested = tuple(f"f{i}" for i in range(10))
    frames = SimpleNamespace(
        frames=tuple(SimpleNamespace(frame_uid=uid) for uid in requested),
        content_digest="f" * 64,
    )
    data5 = SimpleNamespace(content_digest="5" * 64)
    sources = SimpleNamespace(content_digest="s" * 64)
    expected_plan = SimpleNamespace(content_digest="p" * 64, requested_frame_uids=requested)

    monkeypatch.setattr(
        campaign_cli._core,
        "_load_prepared",
        lambda store, include_data4=False: (sources, frames, None, data5),
    )
    monkeypatch.setattr(
        campaign_cli._core,
        "_model_checkpoint_identity",
        lambda cfg, paths: SimpleNamespace(content_digest="i" * 64, device="cuda"),
    )
    monkeypatch.setattr(
        mdstats,
        "build_data6_model_sweep_plan",
        lambda *args, **kwargs: expected_plan,
    )
    monkeypatch.setattr(
        mdstats,
        "load_data6_model_sweep_artifacts",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("checkpoint absent")),
    )
    monkeypatch.setattr(
        campaign_cli._core,
        "_load_or_rebuild_frame_data",
        lambda *args, **kwargs: {"run": object()},
    )
    monkeypatch.setattr(
        campaign_cli._core,
        "build_frame_array_index",
        lambda *args, **kwargs: {
            uid: (SimpleNamespace(frame_uid=uid), object(), index)
            for index, uid in enumerate(requested)
        },
    )
    monkeypatch.setattr(
        campaign_cli._core,
        "ase_atoms_for_frame",
        lambda record, frame_values, local_index: record.frame_uid,
    )

    class ExpectedStop(RuntimeError):
        pass

    class Provider:
        def descriptor_signature(self, policy):
            return SimpleNamespace(content_digest="d" * 64)

        def calibrate_batch_capacity(self, calibration_atoms, *args, **kwargs):
            # Default stress sample count is 8, so the 10 requested frames must
            # exercise the np.linspace branch that failed on the workstation.
            assert tuple(calibration_atoms) == (
                "f0", "f1", "f2", "f3", "f5", "f6", "f7", "f9"
            )
            raise ExpectedStop("reached DATA6 recovery calibration")

    monkeypatch.setattr(campaign_cli._core, "_provider", lambda *args, **kwargs: (Provider(), None))
    monkeypatch.setattr(
        campaign_cli._core,
        "_performance_resources",
        lambda cfg: SimpleNamespace(gpu=SimpleNamespace(budget_bytes=2**30)),
    )

    class Store:
        def get_record_optional(self, *args, **kwargs):
            return None

        def put_record(self, *args, **kwargs):
            pass

    sweep_root = tmp_path / ".mdstats" / "data6-model-sweep"
    sweep_root.mkdir(parents=True)
    paths = SimpleNamespace(
        internal=tmp_path / ".mdstats",
        workspace=tmp_path,
        config=tmp_path / "campaign.toml",
        config_dir=tmp_path,
    )
    cfg = {
        "paths": {"training_root": str(tmp_path)},
        "model": {"batch_calibration_stress_structures": 8},
    }
    with pytest.raises(ExpectedStop, match="DATA6 recovery calibration"):
        campaign_cli._prepare_sweep(cfg, paths, Store(), max_new_frames=None)

def test_data6_restart_match_requires_exact_scientific_lineage() -> None:
    policy = SimpleNamespace(policy_digest="p" * 64)
    sweep_plan = SimpleNamespace(
        content_digest="q" * 64,
        checkpoint_identity=SimpleNamespace(content_digest="i" * 64),
    )
    sweep = SimpleNamespace(
        checkpoint=SimpleNamespace(plan=sweep_plan, content_digest="c" * 64),
        descriptor_manifest=SimpleNamespace(content_digest="d" * 64),
        prediction_manifest=SimpleNamespace(content_digest="r" * 64),
    )
    data6 = SimpleNamespace(
        source_catalog_digest="s" * 64,
        frame_catalog_digest="f" * 64,
        data4_bundle_digest="4" * 64,
        data5_bundle_digest="5" * 64,
        policy=policy,
        model_sweep_plan=sweep_plan,
        model_sweep_checkpoint_digest="c" * 64,
        checkpoint_identity=SimpleNamespace(content_digest="i" * 64),
        mace_descriptor_manifest=SimpleNamespace(content_digest="d" * 64),
        prediction_manifest=SimpleNamespace(content_digest="r" * 64),
    )
    kwargs = dict(
        sources=SimpleNamespace(content_digest="s" * 64),
        frames=SimpleNamespace(content_digest="f" * 64),
        data4=SimpleNamespace(content_digest="4" * 64),
        data5=SimpleNamespace(content_digest="5" * 64),
        sweep=sweep,
        policy=policy,
    )
    assert campaign_cli._data6_bundle_matches_live_inputs(data6, **kwargs)
    data6.model_sweep_checkpoint_digest = "x" * 64
    assert not campaign_cli._data6_bundle_matches_live_inputs(data6, **kwargs)


def test_campaign_materialization_restart_reuses_matching_variant_without_tree_hash(
    tmp_path: Path,
) -> None:
    variant_id = "multihead_replay-n512-seed2"
    root = tmp_path / "variant"
    (root / "data8").mkdir(parents=True)
    (root / "data8" / "data8_preparation_bundle.json").write_text("{}")
    plan = SimpleNamespace(content_digest="p" * 64)
    bundle = SimpleNamespace(
        content_digest="b" * 64,
        jobs=(
            SimpleNamespace(
                protocol=SimpleNamespace(
                    training_mode=SimpleNamespace(value="multihead_replay"),
                    selection_size=512,
                    optimizer_policy=SimpleNamespace(seed=2),
                )
            ),
        ),
    )
    artifact = SimpleNamespace(
        bundle_digest=bundle.content_digest,
        relative_directory="data8",
        bundle_relative_path="data8/data8_preparation_bundle.json",
    )
    record = SimpleNamespace(
        complete=True,
        root_directory=str(root),
        checkpoint=SimpleNamespace(plan=plan, data8_artifact=artifact),
    )

    class Store:
        def has_record(self, key):
            return True

        def get_record(self, key, cls):
            return record if key.startswith("materialization:") else bundle

    assert campaign_cli._reuse_materialization_if_current(
        Store(), variant_id=variant_id, plan=plan
    ) == (record, bundle)
    changed_plan = SimpleNamespace(content_digest="z" * 64)
    assert campaign_cli._reuse_materialization_if_current(
        Store(), variant_id=variant_id, plan=changed_plan
    ) is None


def test_completed_prepare_receipt_is_true_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    variant_id = "multihead_replay-n512-seed2"
    artifact = SimpleNamespace(tree_digest="t" * 64)
    materialization = SimpleNamespace(
        checkpoint=SimpleNamespace(
            plan=SimpleNamespace(content_digest="p" * 64),
            data8_artifact=artifact,
        )
    )
    bundle = SimpleNamespace(content_digest="b" * 64)
    entry = SimpleNamespace(
        variant_id=variant_id,
        materialization=materialization,
        bundle=bundle,
    )
    digests = {key: (key[0] * 64) for key in campaign_cli._PREPARE_RECEIPT_RECORD_KEYS}
    pointer = {
        "checkpoint_digest": "c" * 64,
        "plan_digest": "q" * 64,
        "status": "complete",
        "completed_frames": 10,
        "requested_frames": 10,
        "relative_directory": ".mdstats/model-sweep",
    }
    receipt = {
        "schema": campaign_cli.PREPARE_RESTART_RECEIPT_SCHEMA,
        "contract": {"contract": "current"},
        "config_sha256": "cfg",
        "input_identities": [{"path": "inputs", "size": 1}],
        "record_digests": digests,
        "model_sweep": pointer,
        "data8": [
            {
                "variant_id": variant_id,
                "bundle_digest": bundle.content_digest,
                "plan_digest": materialization.checkpoint.plan.content_digest,
                "tree_digest": artifact.tree_digest,
            }
        ],
    }
    source_catalog = SimpleNamespace(sources=())
    qualification = SimpleNamespace(
        status=SimpleNamespace(value="passed"), full_data9a_passed=True
    )

    class Store:
        def stage(self, name):
            return campaign_cli.StageState.COMPLETE, "done"

        def get_meta(self, key):
            return "cfg"

        def has_record(self, key):
            return key == "prepare_restart_receipt" or key in digests or key == "model_sweep_checkpoint"

        def get_payload(self, key):
            return receipt if key == "prepare_restart_receipt" else pointer

        def get_record(self, key, cls):
            return source_catalog if key == "source_catalog" else qualification

        def record_digest(self, key):
            return digests[key]

    monkeypatch.setattr(campaign_cli._core, "_sha256", lambda path: "cfg")
    monkeypatch.setattr(
        campaign_cli._core, "_prepare_contract_signature", lambda: {"contract": "current"}
    )
    monkeypatch.setattr(
        campaign_cli._core,
        "_prepare_input_identities",
        lambda cfg, paths, sources: [{"path": "inputs", "size": 1}],
    )
    monkeypatch.setattr(campaign_cli._core, "_current_data8_entries", lambda store: [entry])
    cfg = {
        "training": {"modes": ["multihead_replay"], "seeds": [2]},
        "selection": {"sizes": [512]},
    }
    paths = SimpleNamespace(config=tmp_path / "campaign.toml")
    assert campaign_cli._try_reuse_completed_prepare(cfg, paths, Store())
