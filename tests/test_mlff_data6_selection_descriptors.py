from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from ase.calculators.calculator import Calculator, all_changes

import mdstats
from tests.test_mlff_data4_raw_features_events import _site_catalogs
from tests.test_mlff_data5_partition_roles import _build


class _FakeMaceCalculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        positions = np.asarray(self.atoms.positions, dtype=float)
        self.results = {
            "energy": float(np.sum(positions**2)),
            "forces": -2.0 * positions,
            "stress": np.asarray([0.01, 0.02, 0.03, 0.004, 0.005, 0.006]),
        }

    def get_descriptors(self, atoms, *, invariants_only=True, num_layers=None):
        numbers = np.asarray(atoms.numbers, dtype=float)[:, None]
        positions = np.asarray(atoms.positions, dtype=float)
        scale = 1.0 if invariants_only else 2.0
        layer = 0.0 if num_layers is None else float(num_layers)
        return np.column_stack((numbers, scale * positions, np.full(len(atoms), layer)))


def _provider() -> mdstats.MaceCalculatorProvider:
    identity = mdstats.ModelCheckpointIdentity(
        model_family="fake-mace",
        checkpoint_locator="memory://fake-mace",
        checkpoint_sha256="a" * 64,
        calculator_class="tests._FakeMaceCalculator",
        model_version="0.test",
        supported_atomic_numbers=(3, 8, 11, 13, 14, 19),
        device="cpu",
        default_dtype="float64",
    )
    return mdstats.MaceCalculatorProvider.from_calculator(
        _FakeMaceCalculator(), checkpoint_identity=identity
    )


def test_supplied_ase_version() -> None:
    import ase

    assert ase.__version__ == "3.29.0"


def test_lta_selection_descriptors_are_species_resolved_and_deterministic(tmp_path: Path) -> None:
    sources, frames, frame_data, site_policy = _site_catalogs(tmp_path)
    data4 = mdstats.build_data4_feature_bundle(
        sources,
        frames,
        frame_data,
        raw_feature_policy=mdstats.RawFeaturePolicy.lta_default(),
        lta_profile_policy=mdstats.LtaPartitionProfilePolicy(
            ring_definitions=site_policy.ring_definitions,
            require_oxygen_framework_coordination=1,
        ),
        event_policy=mdstats.EventDetectionPolicy(pre_frames=1, post_frames=1),
        partition_role_budget=mdstats.PartitionRoleBudgetPolicy(cross_validation_folds=2),
    )
    catalog = mdstats.build_lta_selection_feature_catalog(frames, frame_data, data4)
    assert len(catalog.frame_descriptors) == 2
    assert len(catalog.atomic_environment_descriptors) == 6
    assert {item.symbol for item in catalog.atomic_environment_descriptors} == {"Li", "Na", "K"}
    assert all(item.feature_names == catalog.policy.environment_feature_names for item in catalog.atomic_environment_descriptors)
    uid_by_source_index = {record.source_frame_index: record.frame_uid for record in frames.frames}
    second = catalog.for_frame(uid_by_source_index[1])
    features = dict(second.named_features)
    assert features["ring_crossing"] == pytest.approx(1.0)
    assert features["site_change"] == pytest.approx(1.0)
    assert mdstats.LtaSelectionFeatureCatalog.from_dict(catalog.to_dict()) == catalog

    one_uid = (catalog.frame_descriptors[0].frame_uid,)
    subset = mdstats.build_lta_selection_feature_catalog(
        frames, frame_data, data4, frame_uids=one_uid
    )
    assert tuple(item.frame_uid for item in subset.frame_descriptors) == one_uid
    assert {item.frame_uid for item in subset.atomic_environment_descriptors} == set(one_uid)


def test_lta_environment_labels_survive_compact_production_materialization(tmp_path: Path) -> None:
    sources, frames, frame_data, site_policy = _site_catalogs(tmp_path)
    data4 = mdstats.build_data4_feature_bundle(
        sources,
        frames,
        frame_data,
        raw_feature_policy=mdstats.RawFeaturePolicy.lta_default(),
        lta_profile_policy=mdstats.LtaPartitionProfilePolicy(
            ring_definitions=site_policy.ring_definitions,
            require_oxygen_framework_coordination=1,
        ),
        event_policy=mdstats.EventDetectionPolicy(pre_frames=1, post_frames=1),
        partition_role_budget=mdstats.PartitionRoleBudgetPolicy(cross_validation_folds=2),
    )
    catalog = mdstats.build_lta_selection_feature_catalog(
        frames,
        frame_data,
        data4,
        policy=mdstats.LtaSelectionPolicy(materialize_atomic_environments=False),
    )
    assert not catalog.atomic_environment_descriptors
    labels = {
        label
        for record in catalog.frame_descriptors
        for label in catalog.environment_class_labels_for_frame(record.frame_uid)
    }
    assert labels
    assert {label.split(":", 2)[1] for label in labels} == {"Li", "Na", "K"}

    extension = mdstats.wrap_lta_selection_features(
        catalog,
        data4_bundle_digest=data4.content_digest,
    )
    assert set(extension.environment_class_labels({
        record.frame_uid for record in catalog.frame_descriptors
    })) == labels


def test_mace_descriptor_sidecars_bind_checkpoint_and_reject_tampering(tmp_path: Path) -> None:
    sources, frames, data4, data5 = _build(tmp_path)
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    provider = _provider()
    development = tuple(
        sorted(
            frame_uid
            for outer in data5.outer_partitions
            for unit_id in outer.units_for(mdstats.OuterRole.DEVELOPMENT)
            for frame_uid in data5.unit_catalog.unit(unit_id).frame_uids
        )
    )
    manifest = mdstats.build_mace_descriptor_manifest(
        frames,
        frame_data,
        data5,
        provider,
        tmp_path / "mace-sidecars",
        frame_uids=development[:3],
    )
    assert len(manifest.records) == 3
    array = mdstats.read_mace_descriptor_array(
        manifest, tmp_path / "mace-sidecars", manifest.records[0].frame_uid
    )
    assert array.shape == (2, 5)
    assert not array.flags.writeable
    assert mdstats.MaceDescriptorManifest.from_dict(manifest.to_dict()) == manifest

    path = tmp_path / "mace-sidecars" / manifest.records[0].relative_path
    altered = np.load(path, allow_pickle=False)
    altered[0, 0] += 1.0
    np.save(path, altered, allow_pickle=False)
    with pytest.raises(mdstats.TrainingDataSerializationError):
        mdstats.read_mace_descriptor_array(
            manifest, tmp_path / "mace-sidecars", manifest.records[0].frame_uid
        )


def test_training_residuals_are_authorized_and_evaluation_predictions_remain_blinded(tmp_path: Path) -> None:
    sources, frames, data4, data5 = _build(tmp_path)
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    provider = _provider()

    domains = mdstats.build_training_difficulty_domains(data5)
    assert any(domain.kind is mdstats.TrainingDifficultyDomainKind.FINAL_DEVELOPMENT for domain in domains)
    catalog = mdstats.build_training_difficulty_feature_catalog(
        frames, frame_data, data5, domains[0], provider
    )
    assert catalog.records
    assert all(item.species_force_errors for item in catalog.records)
    assert mdstats.TrainingDifficultyFeatureCatalog.from_dict(catalog.to_dict()) == catalog

    unauthorized = mdstats.TrainingDifficultyDomain(
        label_domain_id=domains[0].label_domain_id,
        kind=mdstats.TrainingDifficultyDomainKind.FINAL_DEVELOPMENT,
        data5_bundle_digest=data5.content_digest,
        unit_ids=domains[0].unit_ids,
        frame_uids=domains[0].frame_uids[:-1],
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.build_training_difficulty_feature_catalog(
            frames, frame_data, data5, unauthorized, provider
        )

    blinded_domains = mdstats.build_blinded_prediction_domains(data5)
    outer = next(
        domain for domain in blinded_domains
        if domain.kind is mdstats.BlindedPredictionDomainKind.OUTER_MONITOR
    )
    blinded = mdstats.build_blinded_evaluation_prediction_catalog(
        frames, frame_data, data5, outer, provider
    )
    assert blinded.records
    payload_text = repr(blinded.to_dict()).lower()
    assert "reference_energy" not in payload_text
    assert "energy_error" not in payload_text
    assert "force_error" not in payload_text

    locked = next(
        domain for domain in blinded_domains
        if domain.kind is mdstats.BlindedPredictionDomainKind.LOCKED_INTERPOLATION_TEST
    )
    sealed = mdstats.build_blinded_evaluation_prediction_catalog(
        frames, frame_data, data5, locked, provider
    )
    assert sealed.domain.materialization_status is mdstats.PredictionMaterializationStatus.SEALED_NOT_MATERIALIZED
    assert sealed.records == ()


def test_data6_bundle_real_vasp_path_and_roundtrip(tmp_path: Path) -> None:
    sources, frames, data4, data5 = _build(tmp_path)
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    provider = _provider()
    bundle = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        policy=mdstats.Data6Policy(
            build_lta_selection_features=False,
            build_mace_descriptors=True,
            build_training_difficulty=True,
            build_blinded_predictions=True,
        ),
        model_provider=provider,
        descriptor_output_directory=tmp_path / "data6",
    )
    assert bundle.checkpoint_identity == provider.checkpoint_identity
    assert bundle.mace_descriptor_manifest is not None
    assert bundle.training_difficulty_catalogs
    assert bundle.blinded_prediction_catalogs
    assert mdstats.Data6FeatureBundle.from_dict(bundle.to_dict()) == bundle

    tampered = deepcopy(bundle.to_dict())
    tampered["notes"] = ["changed"]
    with pytest.raises(mdstats.TrainingDataSerializationError):
        mdstats.Data6FeatureBundle.from_dict(tampered)


def test_model_free_data6_bundle_accepts_no_checkpoint(tmp_path: Path) -> None:
    sources, frames, data4, data5 = _build(tmp_path)
    frame_data, _ = mdstats.load_vasp_frame_data_by_run(sources, base_directory=tmp_path)
    bundle = mdstats.build_data6_feature_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        policy=mdstats.Data6Policy(
            build_lta_selection_features=False,
            build_mace_descriptors=False,
            build_training_difficulty=False,
            build_blinded_predictions=False,
        ),
    )
    assert bundle.checkpoint_identity is None
    assert bundle.mace_descriptor_manifest is None
