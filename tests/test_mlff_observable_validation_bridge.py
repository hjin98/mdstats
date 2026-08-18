"""Focused tests for MLFF orchestration of analysis-owned observables."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mdstats.analysis.observable_validation import ObservableAnalysisCall, ObservableAnalysisRecipe
from mdstats.training_data._common import TrainingDataInputError, TrainingDataSerializationError
from mdstats.training_data.observable_validation import (
    MLFFObservableValidationEvidenceRecord,
    MLFFObservableValidationPlan,
    ObservableCollectionIdentity,
    ObservableEvidenceRole,
    ObservableRecommendationProfile,
    ObservableValidationActivationRecord,
    TrajectoryGenerationIdentity,
    recommended_observable_ids,
    run_mlff_observable_validation,
)

from tests.test_observable_validation_api import make_collection


D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64


def generation_identity(collection, *, label: str, kind: str) -> TrajectoryGenerationIdentity:
    identity = ObservableCollectionIdentity.from_collection(collection, label=label)
    return TrajectoryGenerationIdentity(
        generator_kind=kind,
        generator_artifact_digest=D0 if kind == "mlff" else D1,
        generator_manifest_digest=D1 if kind == "mlff" else None,
        protocol_digest=D2,
        output_collection_digest=identity.content_digest,
        source_provenance_digest=identity.provenance_digest,
        engine_name="ASE" if kind == "mlff" else "VASP",
        engine_version="3.29.0" if kind == "mlff" else "6.x",
        precision_policy="model-fp32-state-fp64" if kind == "mlff" else "electronic-reference",
        random_seed=17 if kind == "mlff" else None,
    )


def test_profile_recommendations_are_advisory_analysis_ids() -> None:
    liquid = recommended_observable_ids(ObservableRecommendationProfile.LIQUID, ionic_transport=True)
    assert "structure.rdf" in liquid
    assert "transport.diffusion_plateau" in liquid
    assert "transport.ionic_conductivity" in liquid
    assert all("lta" not in item for item in liquid)
    assert not hasattr(__import__("mdstats"), "MaterialValidationProfile")


def test_ionic_transport_flag_requires_complete_recipe_chain() -> None:
    recipe = ObservableAnalysisRecipe(
        recipe_id="rdf-only",
        calls=(ObservableAnalysisCall("rdf", "structure.rdf", {"r_max": 4.0}),),
    )
    with pytest.raises(TrainingDataInputError, match="complete declared ionic transport chain"):
        MLFFObservableValidationPlan(
            plan_id="bad-ionic",
            recommendation_profile=ObservableRecommendationProfile.LIQUID,
            recipe=recipe,
            ionic_transport=True,
        )


def test_locked_test_requires_predeclared_policy_freeze_and_activation() -> None:
    with pytest.raises(TrainingDataInputError, match="partition policy"):
        ObservableValidationActivationRecord(ObservableEvidenceRole.LOCKED_TEST)
    activation = ObservableValidationActivationRecord(
        ObservableEvidenceRole.LOCKED_TEST,
        partition_policy_digest=D0,
        partition_assignment_digest=D1,
        comparison_policy_digest=D2,
        protocol_freeze_digest=D3,
        locked_test_activation_digest=D4,
    )
    assert activation.role is ObservableEvidenceRole.LOCKED_TEST


def test_paired_mlff_validation_records_symmetric_lineage_result_identity_and_runtime() -> None:
    recipe = ObservableAnalysisRecipe(
        recipe_id="paired-rdf-msd",
        calls=(
            ObservableAnalysisCall(
                "rdf",
                "structure.rdf",
                {"species_a": "Na", "species_b": "O", "r_max": 4.0, "n_bins": 40},
            ),
            ObservableAnalysisCall(
                "msd",
                "dynamics.msd",
                {"species": "O", "max_lag": 4, "backend": "direct"},
            ),
        ),
    )
    plan = MLFFObservableValidationPlan(
        plan_id="initial-model-physical-smoke",
        recommendation_profile=ObservableRecommendationProfile.CRYSTALLINE_SOLID,
        recipe=recipe,
        notes=("Comparison tolerances remain a separate predeclared policy.",),
    )
    reference_collection = make_collection(scale=1.0)
    candidate_collection = make_collection(scale=1.2)
    with pytest.raises(TrainingDataInputError, match="reference_generation and candidate_generation"):
        run_mlff_observable_validation(reference_collection, candidate_collection, plan)

    reference_generation = generation_identity(reference_collection, label="reference", kind="electronic-structure")
    candidate_generation = generation_identity(candidate_collection, label="mlff", kind="mlff")
    evidence = run_mlff_observable_validation(
        reference_collection,
        candidate_collection,
        plan,
        reference_generation=reference_generation,
        candidate_generation=candidate_generation,
    )
    payload = evidence.to_evidence_dict()
    assert payload["plan_digest"] == plan.content_digest
    assert payload["comparison_and_acceptance"] == "predeclared-policy-identity-required-by-statistical-role"
    assert set(evidence.result_type_pairs) == {"rdf", "msd"}
    assert payload["candidate_generation"]["generator_artifact_digest"] == D0
    assert payload["reference_collection"]["geometry_digest"] != payload["candidate_collection"]["geometry_digest"]
    assert payload["reference_runtime_identity"]["observable_api_version"].endswith("v2")
    assert payload["reference_runtime_identity"]["mdstats_executing_version"] == "0.20.140a0"
    assert set(payload["warnings_by_call"]) == {"rdf", "msd"}
    assert set(payload["duration_seconds_by_call"]) == {"rdf", "msd"}
    assert set(payload["result_identities"]) == {"rdf", "msd"}
    assert all(
        len(side["content_digest"]) == 64
        for pair in payload["result_identities"].values()
        for side in pair.values()
    )
    assert len(payload["content_digest"]) == 64

    record = evidence.to_record()
    restored = MLFFObservableValidationEvidenceRecord.from_dict(record.to_dict())
    assert restored.content_digest == record.content_digest
    tampered = record.to_dict()
    tampered["plan_digest"] = D5
    with pytest.raises(TrainingDataSerializationError, match="digest mismatch"):
        MLFFObservableValidationEvidenceRecord.from_dict(tampered)


def test_supplied_collection_identity_is_verified_against_actual_collection() -> None:
    recipe = ObservableAnalysisRecipe(
        recipe_id="rdf",
        calls=(ObservableAnalysisCall("rdf", "structure.rdf", {"r_max": 4.0}),),
    )
    plan = MLFFObservableValidationPlan(
        plan_id="identity-check",
        recommendation_profile=ObservableRecommendationProfile.GENERIC_CONDENSED,
        recipe=recipe,
        require_complete_lineage=False,
    )
    reference = make_collection(scale=1.0)
    candidate = make_collection(scale=1.2)
    wrong = ObservableCollectionIdentity.from_collection(make_collection(scale=3.0), label="reference")
    with pytest.raises(TrainingDataInputError, match="does not match the collection"):
        run_mlff_observable_validation(
            reference,
            candidate,
            plan,
            reference_identity=wrong,
        )


def test_generation_identity_must_bind_output_collection() -> None:
    recipe = ObservableAnalysisRecipe(
        recipe_id="rdf",
        calls=(ObservableAnalysisCall("rdf", "structure.rdf", {"r_max": 4.0}),),
    )
    plan = MLFFObservableValidationPlan(
        plan_id="generation-check",
        recommendation_profile=ObservableRecommendationProfile.GENERIC_CONDENSED,
        recipe=recipe,
    )
    reference = make_collection(scale=1.0)
    candidate = make_collection(scale=1.2)
    reference_generation = generation_identity(reference, label="reference", kind="electronic-structure")
    bad_candidate = replace(
        generation_identity(candidate, label="mlff", kind="mlff"),
        output_collection_digest=D5,
    )
    with pytest.raises(TrainingDataInputError, match="not bound to the analyzed collection"):
        run_mlff_observable_validation(
            reference,
            candidate,
            plan,
            reference_generation=reference_generation,
            candidate_generation=bad_candidate,
        )


def test_collection_identity_round_trip_tamper_rejection_and_relocation() -> None:
    identity = ObservableCollectionIdentity.from_collection(make_collection(), label="reference")
    restored = ObservableCollectionIdentity.from_dict(identity.to_dict())
    assert restored.content_digest == identity.content_digest
    relocated = replace(identity, source_files=("/another/location/synthetic",))
    assert relocated.content_digest == identity.content_digest
    payload = identity.to_dict()
    payload["n_frames"] += 1
    with pytest.raises(Exception, match="digest mismatch"):
        ObservableCollectionIdentity.from_dict(payload)


def test_collection_identity_rejects_object_dtype_arrays() -> None:
    collection = make_collection()
    collection.fractional_positions = np.asarray(collection.fractional_positions, dtype=object)
    with pytest.raises(TrainingDataInputError, match="[Oo]bject-dtype"):
        ObservableCollectionIdentity.from_collection(collection, label="reference")
