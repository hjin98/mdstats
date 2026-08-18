from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data import campaign_cli
from tests.test_mlff_data9a9a_production_model_sweep import _CountingCalculator, _provider, _inputs
from mdstats.training_data._frame_access import build_frame_array_index


def _build_audit(tmp_path: Path):
    sources, frames, frame_data, data4, data5, policy = _inputs(tmp_path / "inputs")
    policy = replace(policy, build_universal_structural_features=True)
    freeze = mdstats.build_target_data_role_freeze(sources, frames, data5)
    calc = _CountingCalculator()
    provider = _provider(calc)
    sweep = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        provider,
        tmp_path / "sweep",
    )
    assert sweep.complete
    calls = (calc.descriptor_calls, calc.prediction_calls)
    data6 = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        policy=policy,
        model_provider=provider,
        model_sweep_artifacts=sweep,
    )
    assert (calc.descriptor_calls, calc.prediction_calls) == calls
    audit = mdstats.build_foundation_target_audit(
        sources,
        frames,
        frame_data,
        data5,
        data6,
        freeze,
        sweep,
    )
    assert (calc.descriptor_calls, calc.prediction_calls) == calls
    return sources, frames, frame_data, data5, data6, freeze, sweep, audit, calc


def test_foundation_audit1_uses_exact_target_data2a_development_domains(tmp_path: Path) -> None:
    sources, frames, _, data5, data6, freeze, _, audit, _ = _build_audit(tmp_path)

    assert audit.source_catalog_digest == sources.content_digest
    assert audit.frame_catalog_digest == frames.content_digest
    assert audit.data5_bundle_digest == data5.content_digest
    assert audit.data6_bundle_digest == data6.content_digest
    assert audit.target_data_role_freeze_digest == freeze.content_digest
    assert audit.foundation_checkpoint_identity_digest == data6.checkpoint_identity.content_digest
    assert audit.foundation_checkpoint_sha256 == data6.checkpoint_identity.checkpoint_sha256

    frozen = {item.label_domain_id: tuple(sorted(item.size_development_frame_uids)) for item in freeze.domains}
    audited = {item.label_domain_id: item.frame_uids for item in audit.domains}
    assert audited == frozen

    protected = {
        uid
        for item in freeze.domains
        for uid in (*item.final_validation_frame_uids, *item.locked_test_frame_uids)
    }
    assert protected.isdisjoint({uid for item in audit.domains for uid in item.frame_uids})

    for item in audit.domains:
        families = {summary.feature_family for summary in item.metrics.conditioned_force_summaries}
        assert {"pair_distance", "coordination"} <= families
        assert families <= {"pair_distance", "angular_environment", "coordination"}


def test_foundation_audit1_metric_arithmetic_and_force_tails_match_cached_predictions(tmp_path: Path) -> None:
    _, frames, frame_data, _, _, _, sweep, audit, _ = _build_audit(tmp_path)
    index = build_frame_array_index(frames, frame_data)

    for domain in audit.domains:
        energy_abs_per_atom = []
        deltas = []
        species_deltas: dict[int, list[np.ndarray]] = {}
        for uid in domain.frame_uids:
            record, data, local_index = index[uid]
            pred = mdstats.read_atomic_model_prediction(sweep.prediction_manifest, sweep.root_directory, uid)
            ref_forces = np.asarray(data.forces_ev_per_angstrom[local_index], dtype=np.float64)
            delta = np.asarray(pred.forces_ev_per_angstrom, dtype=np.float64) - ref_forces
            deltas.append(delta)
            energy_abs_per_atom.append(abs(float(pred.energy_ev) - float(data.energies_ev[local_index])) / record.atom_count)
            numbers = np.asarray(data.atomic_numbers, dtype=np.int32)
            for z in np.unique(numbers):
                species_deltas.setdefault(int(z), []).append(delta[numbers == z])

        stacked = np.concatenate([item.reshape(-1, 3) for item in deltas], axis=0)
        assert domain.metrics.energy_mae_ev_per_atom == pytest.approx(float(np.mean(energy_abs_per_atom)))
        assert domain.metrics.force_component_rmse_ev_per_angstrom == pytest.approx(float(np.sqrt(np.mean(stacked**2))))

        vector = np.linalg.norm(stacked, axis=1)
        component = np.abs(stacked).reshape(-1)
        for item in domain.metrics.force_tail_metrics:
            assert item.vector_error_ev_per_angstrom == pytest.approx(float(np.quantile(vector, item.quantile)))
            assert item.component_abs_error_ev_per_angstrom == pytest.approx(float(np.quantile(component, item.quantile)))

        by_z = {item.atomic_number: item for item in domain.metrics.species_force_metrics}
        expected_species = []
        for z, arrays in species_deltas.items():
            selected = np.concatenate(arrays, axis=0)
            expected = float(np.sqrt(np.mean(selected**2)))
            assert by_z[z].component_rmse_ev_per_angstrom == pytest.approx(expected)
            assert by_z[z].atom_count == selected.shape[0]
            expected_species.append(expected)
        assert domain.metrics.species_macro_force_rmse_ev_per_angstrom == pytest.approx(float(np.mean(expected_species)))


def test_foundation_audit1_is_deterministic_round_trip_and_does_not_reinfer(tmp_path: Path) -> None:
    sources, frames, frame_data, data5, data6, freeze, sweep, first, calc = _build_audit(tmp_path)
    calls = (calc.descriptor_calls, calc.prediction_calls)
    second = mdstats.build_foundation_target_audit(
        sources, frames, frame_data, data5, data6, freeze, sweep
    )
    assert (calc.descriptor_calls, calc.prediction_calls) == calls
    assert second.content_digest == first.content_digest
    restored = mdstats.FoundationTargetAudit.from_dict(first.to_dict())
    assert restored == first
    assert restored.content_digest == first.content_digest


def test_foundation_audit1_probe_contracts_are_frozen_but_not_fabricated_as_passes(tmp_path: Path) -> None:
    *_, audit, _ = _build_audit(tmp_path)
    probes = {item.probe_id: item for item in audit.probe_contracts}
    assert probes["finite_displacement_restoring_force"].status == "deferred_protocol"
    assert probes["zero_k_relaxation_geometry_topology"].status == "deferred_protocol"
    assert all(item.status != "materialized" for item in probes.values())


def test_foundation_audit1_authority_fails_closed_on_live_lineage_change(tmp_path: Path) -> None:
    sources, frames, _, data5, data6, freeze, _, audit, _ = _build_audit(tmp_path)
    mdstats.validate_foundation_target_audit_authority(
        audit,
        source_catalog=sources,
        frame_catalog=frames,
        data5_bundle=data5,
        data6_bundle=data6,
        target_data_role_freeze=freeze,
    )
    stale_data6 = replace(data6, notes=data6.notes + ("stale lineage",))
    with pytest.raises(mdstats.TrainingDataInputError, match="data6_bundle_digest changed"):
        mdstats.validate_foundation_target_audit_authority(
            audit,
            source_catalog=sources,
            frame_catalog=frames,
            data5_bundle=data5,
            data6_bundle=stale_data6,
            target_data_role_freeze=freeze,
        )


def test_foundation_audit1_is_bound_into_prepare_restart_and_preflight_contract() -> None:
    assert "foundation_target_audit" in campaign_cli._PREPARE_RECEIPT_RECORD_KEYS
    contract = campaign_cli._prepare_contract_signature()
    assert contract["foundation_audit1_version"] == mdstats.FOUNDATION_AUDIT_VERSION
    assert callable(campaign_cli._load_verified_foundation_audit_authority)
    assert callable(campaign_cli._ensure_foundation_target_audit)


def test_foundation_audit1_campaign_helper_receives_cfg_and_honors_ram_limit(monkeypatch) -> None:
    class _Store:
        def __init__(self):
            self.records = {"target_data_role_freeze": object()}
        def get_record(self, key, _type):
            return self.records[key]
        def get_record_optional(self, key, _type):
            return self.records.get(key)
        def put_record(self, key, value):
            self.records[key] = value

    class _Audit:
        foundation_potential_identity = None
        foundation_inference_identity = None
        domains = ()
        content_digest = "a" * 64

    captured = {}
    def _build(*args, **kwargs):
        captured["temporary_memory_threshold_bytes"] = kwargs["temporary_memory_threshold_bytes"]
        return _Audit()

    monkeypatch.setattr(mdstats, "build_foundation_target_audit", _build)
    store = _Store()
    cfg = {"performance": {"foundation_audit_temporary_ram_mib": 321}}
    result = campaign_cli._ensure_foundation_target_audit(
        store,
        cfg=cfg,
        sources=object(),
        frames=object(),
        data5=object(),
        data6=object(),
        sweep=object(),
        frame_data_resolver=lambda: {},
    )
    assert result.content_digest == "a" * 64
    assert captured["temporary_memory_threshold_bytes"] == 321 * 1024**2
