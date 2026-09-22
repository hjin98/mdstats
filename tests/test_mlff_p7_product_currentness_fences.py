"""P7 acceptance for the P5-product fences this cycle introduces.

Model representation is deliberately outside `QualificationInputBinding`, which
is what keeps a rebuilt pickle from staling the one-shot locked test. The price
of that choice is that an in-flight attempt can overlap a representation-only
P5 successor, so the commit boundary - not the binding - has to refuse a stale
terminal pointer. These cases exercise exactly that boundary, plus the
observational owner that decides what the public is told afterwards.
"""

from __future__ import annotations

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d  # noqa: F401
from tests import _mlff_qualification_fixture as qual

from mdstats.training_data.campaign_lifecycle import campaign_owner_snapshot
from mdstats.training_data.campaign_post_selection import (
    PostSelectionStaleBindingError,
)
from mdstats.training_data.qualification.errors import QualificationLineageError


@pytest.fixture(scope="module")
def session_bundle(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("p7-fences")
    harness = qual.QualificationHarness()
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
    cfg, paths, store, session = qual.load_session(config, harness)
    yield config, cfg, paths, store, session, harness
    store.close()


def test_admission_captures_one_coherent_p5_parent_graph(session_bundle):
    """No session may combine parents from two CampaignStore moments."""

    _config, _cfg, _paths, _store, session, _harness = session_bundle
    from mdstats.training_data.qualification.runtime import (
        expected_p5_parent_pointers,
    )

    expected = expected_p5_parent_pointers(session)
    # The complete moving parent graph, not the decision row alone.
    kinds = {key.rsplit(":", 1)[-1] for key in expected}
    assert "final_production_publication" in kinds
    assert "final_production_model_publication" in kinds
    assert "p5_p6_predecessor_reclosure" in kinds
    assert "final_production_plan" in kinds
    assert "cv_plan" in kinds and "cv_acceptance" in kinds
    # ... including every required final-seed assessment position, derived by
    # key rather than discovered by searching captured values.
    assert session.admitted_position_locators
    assert set(session.admitted_position_locators).issubset(set(expected))


def test_terminal_publication_refuses_a_moved_p5_parent(session_bundle):
    """A representation successor stales the pointer, not the history."""

    from mdstats.training_data.qualification.store import (
        POINTER_QUALIFICATION_RECORD,
        publish_current_qualification_pointer,
    )
    from mdstats.training_data.qualification.runtime import (
        expected_p5_parent_pointers,
    )

    _config, _cfg, _paths, store, session, _harness = session_bundle
    expected = dict(expected_p5_parent_pointers(session))
    moved = dict(expected)
    key = next(
        key for key in moved if key.endswith("final_production_model_publication")
    )
    moved[key] = "c" * 64

    with pytest.raises(PostSelectionStaleBindingError, match="has advanced"):
        publish_current_qualification_pointer(
            store,
            binding=session.context.selected.binding,
            kind=POINTER_QUALIFICATION_RECORD,
            content_digest="d" * 64,
            expected_post_selection_pointers=moved,
        )
    # ... and the unchanged parent set still commits.
    publish_current_qualification_pointer(
        store,
        binding=session.context.selected.binding,
        kind=POINTER_QUALIFICATION_RECORD,
        content_digest="d" * 64,
        expected_post_selection_pointers=expected,
    )


def test_terminal_publication_refuses_a_moved_assessment_parent(session_bundle):
    """A decision pointer that has not moved does not rescue a parent advance."""

    from mdstats.training_data.qualification.store import (
        POINTER_QUALIFICATION_RECORD,
        publish_current_qualification_pointer,
    )
    from mdstats.training_data.qualification.runtime import (
        expected_p5_parent_pointers,
    )

    _config, _cfg, _paths, store, session, _harness = session_bundle
    expected = dict(expected_p5_parent_pointers(session))
    assert session.admitted_position_locators
    position_key = sorted(session.admitted_position_locators)[0]
    expected[position_key] = "e" * 64
    with pytest.raises(PostSelectionStaleBindingError, match="has advanced"):
        publish_current_qualification_pointer(
            store,
            binding=session.context.selected.binding,
            kind=POINTER_QUALIFICATION_RECORD,
            content_digest="d" * 64,
            expected_post_selection_pointers=expected,
        )


def test_binding_drift_before_publication_is_refused(session_bundle, monkeypatch):
    """A specification or executable edit must abort before terminal exposure."""

    from dataclasses import replace

    from mdstats.training_data.qualification import runtime as rt

    _config, _cfg, _paths, _store, session, _harness = session_bundle
    rt.require_current_qualification_binding(session)

    from dataclasses import replace as _replace

    real = rt.resolve_executable_candidate_identity
    drifted = _replace(
        session.binding.executable, source_tree_digest="f" * 64
    )
    monkeypatch.setattr(rt, "resolve_executable_candidate_identity", lambda: drifted)
    with pytest.raises(QualificationLineageError, match="drifted"):
        rt.require_current_qualification_binding(session)
    monkeypatch.setattr(rt, "resolve_executable_candidate_identity", real)
    rt.require_current_qualification_binding(session)
    assert replace is not None


def test_release_claim_requires_its_matching_index(session_bundle):
    """A crash between the terminal record and its index is not a release."""

    from dataclasses import replace

    from mdstats.training_data.qualification.observation import (
        release_currentness_failure,
    )
    from mdstats.training_data.qualification.record import (
        ProductionQualificationRecord,
        QualificationVerdict,
        ReleaseEvidenceIndex,
        utc_now,
    )

    _config, _cfg, _paths, _store, session, _harness = session_bundle
    record = ProductionQualificationRecord(
        selected_binding_digest=session.binding.selected_binding_digest,
        binding_digest=session.binding.content_digest,
        publication_digest=session.binding.publication_digest,
        publication_member_digest=session.binding.publication_member_digest,
        plan_digest=session.plan.content_digest,
        specification_digest=session.binding.specification.content_digest,
        environment_digest=session.binding.environment.content_digest,
        executable_digest=session.binding.executable.content_digest,
        predecessor_executable_commit="commit",
        predecessor_evidence_commit=session.predecessor_reclosure.content_digest,
        components=(),
        locked_activation_digest=None,
        verdict=QualificationVerdict.RELEASE_QUALIFIED,
        reason_code="ok",
        recorded_at=utc_now(),
        model_artifact_set_digest=session.model_artifact_set_digest,
        deployment_realization_set_digest="not_applicable",
    )
    assert "no release-evidence index" in release_currentness_failure(record, None)

    index = ReleaseEvidenceIndex(
        qualification_record_digest=record.content_digest,
        selected_binding_digest=record.selected_binding_digest,
        publication_digest=record.publication_digest,
        publication_member_digest=record.publication_member_digest,
        executable_digest=record.executable_digest,
        specification_digest=record.specification_digest,
        environment_digest=record.environment_digest,
        plan_digest=record.plan_digest,
        component_evidence_digests=(),
        locked_activation_digest=None,
        verdict=record.verdict,
        published_at=utc_now(),
        model_artifact_set_digest=record.model_artifact_set_digest,
        deployment_realization_set_digest=record.deployment_realization_set_digest,
    )
    assert release_currentness_failure(record, index) is None
    # An index belonging to another model-artifact set is not this release.
    other = replace(index, model_artifact_set_digest="a" * 64)
    assert "model_artifact_set_digest" in release_currentness_failure(record, other)


def test_status_survives_released_scratch_cleanup_without_recreating_it(
    session_bundle,
):
    """Observation reads immutable evidence, never attempt deployment scratch."""

    import shutil

    from mdstats.training_data.qualification.observation import (
        observe_current_qualification,
    )

    _config, _cfg, paths, store, session, _harness = session_bundle
    member = session.publication.members[0]
    session.deployed_artifact(member)
    root = session._deployment_root(member)
    assert root.is_dir()
    shutil.rmtree(root)
    session._deployment_cache.clear()
    session._frozen_realization_set = None

    _revision, bindings, pointers = campaign_owner_snapshot(store)
    observation = observe_current_qualification(paths, bindings[0], pointers)
    assert observation is not None
    # Status performs zero scratch reconstruction.
    assert not root.exists()


def test_locked_cohort_reveal_history_is_representation_independent():
    """`LockedActivationRecord` keeps prerequisite digests, not model identity."""

    from mdstats.training_data.qualification.locked import (
        LOCKED_ACTIVATION_SCHEMA,
        LockedActivationRecord,
    )

    fields = set(LockedActivationRecord.__dataclass_fields__)
    assert "prerequisite_component_digests" in fields, (
        "the activation record must keep recording the exact prerequisite "
        "evidence that authorized first reveal"
    )
    for forbidden in (
        "model_artifact_set_digest",
        "deployment_realization_set_digest",
        "model_relative_path",
        "model_sha256",
    ):
        assert forbidden not in fields, (
            f"{forbidden} would make the cohort/reveal identity "
            "representation-specific"
        )
    assert LOCKED_ACTIVATION_SCHEMA.endswith(".v1"), (
        "the locked activation schema is unchanged by this cycle"
    )


def test_the_scientific_binding_stays_checkpoint_based():
    """Blocking condition 13, as a structural fact about the binding."""

    from mdstats.training_data.qualification.binding import QualificationInputBinding

    fields = set(QualificationInputBinding.__dataclass_fields__)
    for forbidden in (
        "model_artifact_set_digest",
        "model_publication_digest",
        "model_relative_path",
        "model_sha256",
        "deployment_realization_set_digest",
    ):
        assert forbidden not in fields, (
            f"{forbidden} in the whole binding would stale every component - "
            "including the one-shot locked test - when only serialization changed"
        )
    # What it does identify is unchanged.
    assert {
        "selected_binding_digest",
        "publication_digest",
        "publication_member_digest",
        "executable",
        "environment",
        "specification",
        "evidence_roles",
    } <= fields


def test_checkpoint_only_components_do_not_reserve_model_staging(session_bundle):
    """Blocking condition 51: resource semantics follow actual dependency."""

    from mdstats.training_data.qualification.components import (
        COMPONENT_CALIBRATION,
        COMPONENT_DEPLOYMENT_PARITY,
        COMPONENT_DYNAMICS,
        COMPONENT_LOCKED_TEST,
        COMPONENT_PHYSICAL_PES,
        COMPONENT_RELAXATION,
    )

    _config, _cfg, _paths, _store, session, _harness = session_bundle
    model_bytes = sum(
        int(member.model_size_bytes) for member in session.model_publication.members
    )
    deployment = session.required_incremental_headroom_bytes(
        COMPONENT_DEPLOYMENT_PARITY
    )
    assert deployment >= 3 * model_bytes
    assert session.required_incremental_headroom_bytes(COMPONENT_DYNAMICS) == deployment
    for component in (
        COMPONENT_PHYSICAL_PES,
        COMPONENT_RELAXATION,
        COMPONENT_CALIBRATION,
        COMPONENT_LOCKED_TEST,
    ):
        assert session.required_incremental_headroom_bytes(component) != deployment
