from __future__ import annotations

from dataclasses import replace

import pytest

import mdstats
from tests.test_observable_validation_api import make_collection

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64


def _recipe() -> mdstats.ObservableAnalysisRecipe:
    return mdstats.ObservableAnalysisRecipe(
        recipe_id="comparison-smoke",
        calls=(
            mdstats.ObservableAnalysisCall(
                "rdf", "structure.rdf",
                {"species_a": "Na", "species_b": "O", "r_max": 4.0, "n_bins": 80},
            ),
        ),
    )


def _policy(recipe, *, quality: float = 0.05, acceptance: float = 0.50, uncertainty=None):
    return mdstats.ObservableComparisonPolicy(
        policy_id="generic-rdf-policy",
        recipe_digest=recipe.content_digest,
        recommendation_profile=mdstats.ObservableRecommendationProfile.GENERIC_CONDENSED,
        rules=(
            mdstats.ObservableComparisonRule(
                rule_id="rdf-curve",
                call_id="rdf",
                observable_id="structure.rdf",
                metric=mdstats.ObservableComparisonMetric.INTEGRATED_ABSOLUTE_ERROR,
                value_path="g_r",
                axis_path="r",
                allow_interpolation=True,
                thresholds=mdstats.ObservableComparisonThresholds(quality, acceptance),
                uncertainty=mdstats.ObservableScoreUncertainty() if uncertainty is None else uncertainty,
                atom_group_id="all_atoms",
                condition_id="synthetic",
            ),
        ),
    )


def _generation(collection, label: str, kind: str):
    identity = mdstats.ObservableCollectionIdentity.from_collection(collection, label=label)
    return mdstats.TrajectoryGenerationIdentity(
        generator_kind=kind,
        generator_artifact_digest=D0 if kind == "mlff" else D1,
        protocol_digest=D2,
        output_collection_digest=identity.content_digest,
        engine_name="ASE" if kind == "mlff" else "reference",
        engine_version="test",
    )


def _evidence(reference, candidate, policy):
    activation = mdstats.ObservableValidationActivationRecord(
        mdstats.ObservableEvidenceRole.CHECKPOINT_MONITOR,
        comparison_policy_digest=policy.content_digest,
    )
    plan = mdstats.MLFFObservableValidationPlan(
        plan_id="comparison-plan",
        recommendation_profile=mdstats.ObservableRecommendationProfile.GENERIC_CONDENSED,
        recipe=_recipe(),
        activation=activation,
    )
    return mdstats.run_mlff_observable_validation(
        reference,
        candidate,
        plan,
        reference_generation=_generation(reference, "reference", "electronic_reference"),
        candidate_generation=_generation(candidate, "mlff", "mlff"),
    )


def test_identical_observables_pass_and_records_round_trip() -> None:
    reference = make_collection()
    recipe = _recipe()
    policy = _policy(recipe)
    evidence = _evidence(reference, make_collection(), policy)
    result = mdstats.compare_mlff_observable_validation(evidence, policy)
    decision = mdstats.decide_observable_acceptance(result, policy)
    assert result.overall_outcome is mdstats.ObservableComparisonOutcome.PASS
    assert result.rule_results[0].raw_score == pytest.approx(0.0)
    assert decision.accepted
    assert mdstats.ObservableComparisonPolicy.from_dict(policy.to_dict()) == policy
    assert mdstats.ObservableComparisonResult.from_dict(result.to_dict()) == result
    assert mdstats.ObservableAcceptanceDecision.from_dict(decision.to_dict()) == decision


def test_changed_observable_fails_predeclared_threshold() -> None:
    reference = make_collection()
    candidate = make_collection(scale=20.0)
    policy = _policy(_recipe(), quality=1.0e-6, acceptance=1.0e-5)
    evidence = _evidence(reference, candidate, policy)
    result = mdstats.compare_mlff_observable_validation(evidence, policy)
    decision = mdstats.decide_observable_acceptance(result, policy)
    assert result.overall_outcome is mdstats.ObservableComparisonOutcome.FAIL
    assert not decision.accepted
    assert decision.blocking_rule_ids == ("rdf-curve",)
    assert "condition=synthetic|group=all_atoms" in result.scope_outcomes


def test_score_uncertainty_can_only_relax_a_predeclared_score() -> None:
    reference = make_collection()
    candidate = make_collection(scale=20.0)
    base = _policy(_recipe(), quality=0.0, acceptance=1.0)
    evidence = _evidence(reference, candidate, base)
    raw = mdstats.compare_mlff_observable_validation(evidence, base).rule_results[0].raw_score
    assert raw is not None and raw > 0.0
    uncertainty = mdstats.ObservableScoreUncertainty(
        reference_standard_uncertainty=raw,
        candidate_standard_uncertainty=0.0,
        coverage_multiplier=1.0,
        provenance="independent-block-bootstrap",
    )
    adjusted_policy = _policy(_recipe(), quality=0.0, acceptance=1.0, uncertainty=uncertainty)
    adjusted_evidence = _evidence(reference, candidate, adjusted_policy)
    result = mdstats.compare_mlff_observable_validation(adjusted_evidence, adjusted_policy)
    assert result.rule_results[0].adjusted_score == pytest.approx(0.0)
    assert result.overall_outcome is mdstats.ObservableComparisonOutcome.PASS


def test_policy_must_be_bound_before_observable_execution() -> None:
    reference = make_collection()
    policy = _policy(_recipe())
    evidence = _evidence(reference, make_collection(), policy)
    other = replace(policy, policy_id="other-policy")
    with pytest.raises(mdstats.TrainingDataInputError, match="predeclared"):
        mdstats.compare_mlff_observable_validation(evidence, other)


def test_recommendations_do_not_invent_thresholds() -> None:
    templates = mdstats.recommended_observable_comparison_templates("structure.rdf")
    assert {item["metric"] for item in templates} == {"integrated_absolute_error", "peak_shift"}
    assert all("threshold" not in item for item in templates)
    assert mdstats.recommended_observable_comparison_templates("topology.atomic_connectivity") == ()


def test_deprecated_public_aliases_are_removed() -> None:
    assert not hasattr(mdstats, "MaterialValidationProfile")
    assert not hasattr(mdstats, "MLFFTrajectoryGenerationIdentity")
    objective = mdstats.TrainingObjectivePolicy()
    checkpoint = mdstats.CheckpointMetricPolicy()
    assert not hasattr(objective, "cation_atomic_numbers")
    assert not hasattr(objective, "species_aware_force_objective")
    assert not hasattr(checkpoint, "maximum_cation_force_rmse_ev_per_angstrom")


def test_quality_and_acceptance_boundaries_produce_degraded_result() -> None:
    reference = make_collection()
    candidate = make_collection(scale=20.0)
    probe = _policy(_recipe(), quality=0.0, acceptance=10.0)
    raw = mdstats.compare_mlff_observable_validation(
        _evidence(reference, candidate, probe), probe
    ).rule_results[0].raw_score
    assert raw is not None and raw > 0.0
    policy = _policy(_recipe(), quality=0.5 * raw, acceptance=1.5 * raw)
    result = mdstats.compare_mlff_observable_validation(
        _evidence(reference, candidate, policy), policy
    )
    decision = mdstats.decide_observable_acceptance(result, policy)
    assert result.overall_outcome is mdstats.ObservableComparisonOutcome.DEGRADED
    assert decision.accepted
    assert decision.degraded_rule_ids == ("rdf-curve",)


def test_required_indeterminate_rule_fails_closed() -> None:
    reference = make_collection()
    recipe = _recipe()
    policy = mdstats.ObservableComparisonPolicy(
        policy_id="invalid-scalar-policy",
        recipe_digest=recipe.content_digest,
        recommendation_profile=mdstats.ObservableRecommendationProfile.GENERIC_CONDENSED,
        rules=(
            mdstats.ObservableComparisonRule(
                rule_id="array-as-scalar",
                call_id="rdf",
                observable_id="structure.rdf",
                metric=mdstats.ObservableComparisonMetric.ABSOLUTE_ERROR,
                value_path="g_r",
                thresholds=mdstats.ObservableComparisonThresholds(0.0, 1.0),
            ),
        ),
    )
    result = mdstats.compare_mlff_observable_validation(
        _evidence(reference, make_collection(), policy), policy
    )
    decision = mdstats.decide_observable_acceptance(result, policy)
    assert result.overall_outcome is mdstats.ObservableComparisonOutcome.INDETERMINATE
    assert result.rule_results[0].diagnostics
    assert not decision.accepted
    assert decision.blocking_rule_ids == ("array-as-scalar",)


def test_jensen_shannon_distance_is_zero_for_identical_distributions() -> None:
    reference = make_collection()
    recipe = _recipe()
    policy = mdstats.ObservableComparisonPolicy(
        policy_id="rdf-js-policy",
        recipe_digest=recipe.content_digest,
        recommendation_profile=mdstats.ObservableRecommendationProfile.GENERIC_CONDENSED,
        rules=(
            mdstats.ObservableComparisonRule(
                rule_id="rdf-js",
                call_id="rdf",
                observable_id="structure.rdf",
                metric=mdstats.ObservableComparisonMetric.JENSEN_SHANNON_DISTANCE,
                value_path="g_r",
                thresholds=mdstats.ObservableComparisonThresholds(0.0, 0.1),
            ),
        ),
    )
    result = mdstats.compare_mlff_observable_validation(
        _evidence(reference, make_collection(), policy), policy
    )
    assert result.rule_results[0].raw_score == pytest.approx(0.0)
    assert result.overall_outcome is mdstats.ObservableComparisonOutcome.PASS


def test_material_profile_identity_is_enforced() -> None:
    reference = make_collection()
    recipe = _recipe()
    policy = replace(_policy(recipe), material_profile_digest="a" * 64)
    evidence = _evidence(reference, make_collection(), policy)
    with pytest.raises(mdstats.TrainingDataInputError, match="material-profile"):
        mdstats.compare_mlff_observable_validation(evidence, policy)


def test_profile_aware_builder_binds_contract_identity_without_threshold_defaults() -> None:
    profile = mdstats.build_single_phase_material_profile(
        profile_id="liquid",
        phase_kind=mdstats.MaterialPhaseKind.LIQUID,
    )
    contracts = mdstats.build_material_profile_contracts(profile)
    recipe = _recipe()
    rule = _policy(recipe).rules[0]
    policy = mdstats.build_profile_aware_observable_comparison_policy(
        policy_id="liquid-rdf",
        recipe=recipe,
        recommendation_profile=mdstats.ObservableRecommendationProfile.LIQUID,
        material_profile_contracts=contracts,
        rules=(rule,),
    )
    assert policy.material_profile_digest == contracts.content_digest
    assert policy.recipe_digest == recipe.content_digest
    assert policy.rules[0].thresholds == rule.thresholds
