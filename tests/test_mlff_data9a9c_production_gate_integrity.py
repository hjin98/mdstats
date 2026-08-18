from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import shutil

import pytest
from ase.io import read, write

import mdstats
from mdstats.training_data._common import digest
from mdstats.training_data.production_materialization import _replay_semantically_matches
from tests.test_mlff_data9a9b_production_materialization import _fixture


def _qualification_inputs(tmp_path: Path):
    inputs = _fixture(tmp_path)
    record = mdstats.run_restartable_production_materialization(
        *inputs[:7], inputs[7], tmp_path / "materialized"
    )
    sources, frames, _, data4, data5, data6 = inputs[:6]
    normalization = {"version": 1}
    reference = {"version": 1}
    run = {
        "run_id": "bounded-run-001",
        "frame_count": len(frames.frames),
        "energy_complete": True,
        "forces_complete": True,
        "stress_complete": True,
        "ensemble_status": "resolved",
        "quality_outcome": "qualified",
        "production_status": "accepted",
        "reduced_formula": "LiO",
        "ensemble": "NVT",
        "target_start_kelvin": 300.0,
        "target_end_kelvin": 300.0,
    }
    plan = mdstats.ProductionCorpusPlan(
        plan_id="bounded-fixture",
        dataset_id=frames.dataset_id,
        source_catalog_digest=sources.content_digest,
        frame_catalog_digest=frames.content_digest,
        normalization_manifest_digest=digest(normalization),
        reference_manifest_digest=digest(reference),
        expected_runs=(mdstats.ProductionExpectedRun(
            run_id=run["run_id"], frame_count=run["frame_count"], reduced_formula=run["reduced_formula"],
            ensemble=run["ensemble"], target_start_kelvin=300.0, target_end_kelvin=300.0,
        ),),
        expected_cross_validation_fold_count=sum(len(v.folds) for v in data5.cross_validation_plans),
    )
    return inputs, record, plan, normalization, reference, {"runs": [run]}


def test_qualification_derives_foundation_and_residual_evidence(tmp_path: Path) -> None:
    inputs, record, plan, normalization, reference, runs = _qualification_inputs(tmp_path)
    sources, frames, _, data4, data5, data6 = inputs[:6]
    result = mdstats.build_production_corpus_qualification_record(
        production_plan=plan, normalization_manifest=normalization, reference_manifest=reference,
        run_evidence_manifest=runs, source_catalog=sources, frame_catalog=frames,
        data4_bundle=data4, data5_bundle=data5, data6_bundle=data6,
        production_materialization=record,
    )
    assert result.foundation_features_materialized
    assert not result.foundation_residual_e0_materialized
    assert "foundation_residual_e0_not_materialized" in result.blockers
    assert result.status is mdstats.ProductionGateStatus.CONDITIONALLY_READY


def test_frozen_production_plan_rejects_bounded_corpus_substitution(tmp_path: Path) -> None:
    inputs, _, plan, normalization, reference, runs = _qualification_inputs(tmp_path)
    sources, frames, _, data4, data5, data6 = inputs[:6]
    foreign = replace(plan, source_catalog_digest="a" * 64)
    with pytest.raises(mdstats.TrainingDataInputError, match="frozen production corpus plan"):
        mdstats.build_production_corpus_qualification_record(
            production_plan=foreign, normalization_manifest=normalization, reference_manifest=reference,
            run_evidence_manifest=runs, source_catalog=sources, frame_catalog=frames,
            data4_bundle=data4, data5_bundle=data5, data6_bundle=data6,
        )


def test_replay_semantics_bind_numerical_labels_but_not_path(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    source = Path(inputs[7].replay_plan.train_artifact.path)
    copied = tmp_path / "copied.xyz"
    shutil.copy2(source, copied)
    copied_artifact = mdstats.inspect_replay_extxyz(copied)
    original = inputs[7].replay_plan.train_artifact
    assert copied_artifact.content_digest == original.content_digest
    assert copied_artifact.label_payload_digest == original.label_payload_digest

    atoms = read(copied, index=":", format="extxyz")
    atoms[0].info[original.energy_key] = float(atoms[0].info[original.energy_key]) + 1.0
    write(copied, atoms, format="extxyz")
    changed = mdstats.inspect_replay_extxyz(copied)
    assert changed.geometry_identities == original.geometry_identities
    assert changed.label_payload_digest != original.label_payload_digest
    staged = replace(inputs[7].replay_plan, train_artifact=changed)
    assert not _replay_semantically_matches(inputs[7].replay_plan, staged)


def test_checkpoint_identity_is_relocatable(tmp_path: Path) -> None:
    first = tmp_path / "a.model"
    second = tmp_path / "nested" / "b.model"
    second.parent.mkdir()
    first.write_bytes(b"identical-model")
    shutil.copy2(first, second)
    left = mdstats.FoundationCheckpointIdentity.from_file(first)
    right = mdstats.FoundationCheckpointIdentity.from_file(second)
    assert left.reference != right.reference
    assert left.content_digest == right.content_digest


def test_data8_promotion_and_record_loaders_verify_artifacts(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    root = tmp_path / "materialized"
    complete = mdstats.run_restartable_production_materialization(*inputs[:7], inputs[7], root)
    assert (root / "data8").is_symlink()
    assert (root / ".data8-generations").is_dir()

    restored = mdstats.ProductionMaterializationRecord.from_dict(complete.to_dict())
    victim = root / complete.checkpoint.data7_artifacts[0].relative_path
    victim.write_text("{}\n", encoding="utf-8")
    with pytest.raises(mdstats.TrainingDataSerializationError, match="before loading"):
        restored.load_data7_bundles()


def test_generic_extension_requirement_fails_closed(tmp_path: Path) -> None:
    inputs, record, plan, normalization, reference, runs = _qualification_inputs(tmp_path)
    sources, frames, _, data4, data5, data6 = inputs[:6]
    required = replace(plan, required_profile_extensions=(
        mdstats.ProfileExtensionEvidenceRequirement(extension_id="porous_network"),
    ))
    result = mdstats.build_production_corpus_qualification_record(
        production_plan=required, normalization_manifest=normalization, reference_manifest=reference,
        run_evidence_manifest=runs, source_catalog=sources, frame_catalog=frames,
        data4_bundle=data4, data5_bundle=data5, data6_bundle=data6,
        production_materialization=record,
    )
    assert not result.profile_extension_coverage_materialized
    assert "profile_extension_coverage_not_materialized" in result.blockers
