"""P7 acceptance: V7-native post-production qualification and release evidence.

Every test drives production owners.  The campaign, the P1-P5 lifecycle, the
accepted final-production publication resolver, the P7 binding/plan/reference/
component/record owners, the campaign-store currentness fences, the storage
ownership boundary, and the real CLI parser and dispatch all execute.  Only MACE
training, the numerical model forward, and the conversion/execution of a toy
checkpoint by the real deployment runtime are substituted, and each of those
sits strictly below an already accepted owner boundary.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest

import tests._mlff_qualification_fixture as fx
import tests._mlff_post_selection_fixture as p5
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_post_selection import PostSelectionStaleBindingError
from mdstats.training_data.qualification import (
    COMPONENT_CALIBRATION,
    COMPONENT_DEPLOYMENT_PARITY,
    COMPONENT_DYNAMICS,
    COMPONENT_LOCKED_TEST,
    COMPONENT_PHYSICAL_PES,
    COMPONENT_RELAXATION,
    ComponentStatus,
    LockedActivationRecord,
    ProductionQualificationRecord,
    QualificationActivationError,
    QualificationError,
    QualificationLineageError,
    QualificationVerdict,
    build_qualification_retention_fence,
    executable_source_tree_digest,
    probe_lammps_runtime,
    qualification_root,
    resolve_current_locked_activation,
    resolve_current_qualification_verdict,
)
from mdstats.training_data.qualification.publication import (
    checkpoint_path_for_member,
    resolve_authenticated_final_publication,
)
from mdstats.training_data.qualification.store import (
    ATTEMPT_ACTIVE,
    ATTEMPT_TERMINAL,
    read_attempt_state,
)

QUALIFICATION_SOURCE_ROOT = (
    Path(cli.__file__).resolve().parent / "qualification"
)


# ---------------------------------------------------------------------------
# Shared construction helpers
# ---------------------------------------------------------------------------


def _campaign(tmp_path: Path, *, config_text: str | None = None):
    harness = fx.QualificationHarness()
    config, workspace = fx.build_qualified_campaign(
        tmp_path, config_text=config_text, harness=harness
    )
    return config, workspace, harness


def _run_to_waiting(config: Path, harness) -> int:
    return fx.run_qualification_command(config, "run", harness=harness)


def _supply_reference(config: Path, harness) -> None:
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        fx.supply_analytic_reference_bundle(session, harness)
    finally:
        store.close()


def _qualify_nonlocked(config: Path, harness, **extra) -> int:
    assert _run_to_waiting(config, harness) == 0
    _supply_reference(config, harness)
    return fx.run_qualification_command(config, "run", harness=harness, **extra)


def _current_record(config: Path, harness) -> ProductionQualificationRecord | None:
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        return resolve_current_qualification_verdict(store, paths, session.context)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# 9.1 structural / authority acceptance
# ---------------------------------------------------------------------------


def _qualification_sources() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(QUALIFICATION_SOURCE_ROOT.rglob("*.py"))
    }


def test_p7_structural_no_second_publication_or_selection_authority():
    """Qualification is a consumer: it has no way to write product identity."""

    sources = _qualification_sources()
    joined = "\n".join(sources.values())
    # Exactly one module resolves the final publication, and it does so through
    # the accepted P5 completion resolver rather than reimplementing it.
    resolvers = {
        name
        for name, text in sources.items()
        if "resolve_current_final_production_completion" in text
    }
    assert resolvers == {"publication.py"}
    assert "def build_final_production_plan" not in joined
    assert "def execute_final_production" not in joined
    # No qualification path writes selection, CV, or production authority.
    for forbidden in (
        "publish_current_post_selection_pointer",
        "execute_post_selection_cross_validation",
        "execute_current_train_production",
        "build_post_selection_binding",
        "select_cv_fold_representative",
    ):
        assert forbidden not in joined, forbidden
    # A publication view cannot be rehydrated from bytes, so no alternate
    # publication registry can exist.
    from mdstats.training_data.qualification.publication import (
        AuthenticatedFinalPublication,
    )

    with pytest.raises(Exception):
        AuthenticatedFinalPublication.from_dict({})


def test_p7_structural_absence_of_retired_and_successor_architecture():
    """No SELECT2 fallback, retired target-size lineage, or successor storage."""

    joined = "\n".join(_qualification_sources().values())
    for forbidden in (
        "SELECT2",
        "target_size_study_digest",
        "target_data_role_freeze_digest",
        "label_domain_id",
        "StorageInventorySnapshot",
        "_family_for",
        "storage_archive",
        "storage_reclamation",
        "recompute_capability",
    ):
        assert forbidden not in joined, forbidden


def test_p7_structural_locked_evidence_is_unreachable_without_activation():
    """Only the locked module reads the reserved cohort, and only on activation."""

    sources = _qualification_sources()
    readers = {
        name
        for name, text in sources.items()
        if "locked_frame_uids" in text and name != "binding.py"
    }
    assert readers == {"locked.py"}

    runtime = sources["runtime.py"]
    run_section = runtime[
        runtime.index("def execute_nonlocked_components") : runtime.index("def _locked_required")
    ]
    # The run path never evaluates the locked component; it only ever reads
    # already published locked evidence through the terminal record builder.
    assert "qualify_locked_test" not in run_section
    assert "locked_frame_uids" not in run_section
    assert "build_locked_activation" not in run_section

    activation_section = runtime[runtime.index("def activate_locked_test") :]
    assert "qualify_locked_test" in activation_section
    assert "build_locked_activation" in activation_section

    # No training, selection, CV, or production module can reach the locked
    # component at all.
    package = Path(cli.__file__).resolve().parent
    for name in (
        "campaign_post_selection_runtime.py",
        "campaign_post_selection.py",
        "post_selection_production.py",
        "post_selection_execution.py",
        "campaign_target_size_runtime.py",
    ):
        text = (package / name).read_text(encoding="utf-8")
        for forbidden in (
            "from .qualification",
            "import qualification",
            "qualify_locked_test",
            "activate_locked_test",
            "LOCKED_INTERPOLATION_TEST",
        ):
            assert forbidden not in text, f"{name}: {forbidden}"


def test_p7_advance_never_activates_locked_evidence():
    """`advance` remains bounded to the P1-P5 training lifecycle."""

    core = Path(cli.__file__).read_text(encoding="utf-8")
    advance = core[core.index("def command_advance") : core.index("def command_guide")]
    assert "qualification" not in advance
    assert "activate" not in advance
    assert all(
        name != "post_production_qualification" for name, _description in cli.PIPELINE
    )


# ---------------------------------------------------------------------------
# P7-A publication intake and authentication
# ---------------------------------------------------------------------------


def test_p7a_publication_is_resolved_through_the_accepted_owner(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        publication = session.publication
        assert publication.committee_policy == "all_qualified_final_seeds"
        assert [member.member_id for member in publication.members] == ["seed-5"]
        # Reopening resolves the identical product identity, deterministically.
        again = resolve_authenticated_final_publication(session.context)
        assert again.content_digest == publication.content_digest
        assert again.member_digest == publication.member_digest
    finally:
        store.close()


def test_p7a_member_byte_mutation_fails_closed(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        path = checkpoint_path_for_member(session.context, member)
        payload = bytearray(path.read_bytes())
        payload[-1] = (payload[-1] + 1) % 256
        path.write_bytes(bytes(payload))
        with pytest.raises(Exception):
            resolve_authenticated_final_publication(session.context)
    finally:
        store.close()


def test_p7a_single_best_committee_policy_is_predecessor_published(tmp_path: Path):
    """P7 consumes the predecessor's deterministic single-best decision."""

    text = fx.fixture_config_text(committee_policy="single_best_final_seed")
    config, workspace, harness = _campaign(tmp_path, config_text=text)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert session.publication.committee_policy == "single_best_final_seed"
        assert [member.member_id for member in session.publication.members] == ["seed-5"]
    finally:
        store.close()


# ---------------------------------------------------------------------------
# P7-C physical plan independence
# ---------------------------------------------------------------------------


def test_p7c_physical_plan_is_candidate_independent(tmp_path: Path):
    """The plan cannot see a model, so every member is judged identically."""

    config, workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        first = session.plan.physical_plan
        # A model that predicts something completely different produces the
        # byte-identical plan.
        other = fx.QualificationHarness(potential=fx.AnalyticPairPotential(stiffness=97.0))
        fx.attach_labels(other, config)
        _c2, _p2, store2, session2 = fx.load_session(config, other)
        try:
            assert session2.plan.physical_plan.content_digest == first.content_digest
        finally:
            store2.close()
        # Structurally, the plan owner cannot reach a model or a member: it
        # imports neither the provider nor the publication module, and its
        # construction signature accepts neither.
        source = (QUALIFICATION_SOURCE_ROOT / "plan.py").read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        for forbidden in (
            "from .providers",
            "from .publication",
            "predict_all",
            "member_provider",
            "optimizer_seed",
        ):
            assert forbidden not in code, forbidden
        import inspect

        from mdstats.training_data.qualification.plan import build_physical_validation_plan

        parameters = set(inspect.signature(build_physical_validation_plan).parameters)
        assert parameters == {"context", "evidence_roles", "specification"}
    finally:
        store.close()


# ---------------------------------------------------------------------------
# External reference boundary
# ---------------------------------------------------------------------------


def test_p7c_missing_reference_waits_and_publishes_an_actionable_request(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _run_to_waiting(config, harness) == 0
    record = _current_record(config, harness)
    assert record.verdict is QualificationVerdict.WAITING_FOR_REFERENCE
    assert record.outcome(COMPONENT_PHYSICAL_PES).status is ComponentStatus.WAITING_FOR_REFERENCE
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        request_path = session.reference_root / "reference-request.json"
        assert request_path.is_file()
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert payload["protocol_identity"] == "bounded-analytic-reference.v1"
        assert payload["physical_plan_digest"] == session.plan.physical_plan.content_digest
    finally:
        store.close()


def test_p7c_reference_protocol_mismatch_is_never_a_pass(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _run_to_waiting(config, harness) == 0
    _supply_reference(config, harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        bundle_path = session.reference_root / "reference-bundle.json"
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        payload["protocol_identity"] = "some-other-protocol"
        bundle_path.write_text(json.dumps(payload), encoding="utf-8")
    finally:
        store.close()
    with pytest.raises(QualificationLineageError, match="different reference protocol"):
        fx.run_qualification_command(config, "run", harness=harness)


def test_p7c_partial_reference_bundle_is_rejected(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _run_to_waiting(config, harness) == 0
    _supply_reference(config, harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        bundle_path = session.reference_root / "reference-bundle.json"
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        payload["observations"] = payload["observations"][:-1]
        bundle_path.write_text(json.dumps(payload), encoding="utf-8")
    finally:
        store.close()
    with pytest.raises(QualificationLineageError, match="frozen request geometry"):
        fx.run_qualification_command(config, "run", harness=harness)


# ---------------------------------------------------------------------------
# Assembled integration: the mandatory end-to-end path
# ---------------------------------------------------------------------------


def test_p7_assembled_integration_through_real_parser_and_owners(tmp_path: Path, capsys):
    config, workspace, harness = _campaign(tmp_path)

    assert _qualify_nonlocked(config, harness) == 0
    record = _current_record(config, harness)
    assert record.verdict is QualificationVerdict.INCOMPLETE
    assert record.reason_code == f"required_component_missing:{COMPONENT_LOCKED_TEST}"
    assert record.outcome(COMPONENT_DEPLOYMENT_PARITY).status is ComponentStatus.PASSED
    assert record.outcome(COMPONENT_PHYSICAL_PES).status is ComponentStatus.PASSED
    assert record.outcome(COMPONENT_RELAXATION).status is ComponentStatus.PASSED
    assert record.outcome(COMPONENT_DYNAMICS).status is ComponentStatus.PASSED
    assert record.outcome(COMPONENT_CALIBRATION).status is ComponentStatus.NOT_APPLICABLE

    # status is observational and changes nothing.
    before = record.content_digest
    assert fx.run_qualification_command(config, "status", harness=harness) == 0
    assert _current_record(config, harness).content_digest == before

    # Locked activation requires explicit confirmation.
    with pytest.raises(QualificationError, match="--confirm"):
        fx.run_qualification_command(config, "activate-locked", harness=harness)

    assert (
        fx.run_qualification_command(config, "activate-locked", harness=harness, confirm=True) == 0
    )
    terminal = _current_record(config, harness)
    assert terminal.verdict is QualificationVerdict.RELEASE_QUALIFIED
    assert terminal.locked_activation_digest is not None
    assert terminal.predecessor_reclosure_digest
    assert terminal.predecessor_executable_tree_digest
    assert terminal.predecessor_evidence_commit == terminal.predecessor_reclosure_digest

    # Close/reopen reauthenticates the exact terminal state.
    reopened = _current_record(config, harness)
    assert reopened.to_dict() == terminal.to_dict()

    # The release-evidence index points at, and never duplicates, the evidence.
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        from mdstats.training_data.qualification.record import ReleaseEvidenceIndex
        from mdstats.training_data.qualification.store import (
            POINTER_RELEASE_EVIDENCE,
            resolve_current_qualification_record,
        )

        index = resolve_current_qualification_record(
            store,
            paths,
            session.context.selected,
            kind=POINTER_RELEASE_EVIDENCE,
            deserializer=ReleaseEvidenceIndex.from_dict,
        )
        assert index.qualification_record_digest == terminal.content_digest
        assert index.verdict is QualificationVerdict.RELEASE_QUALIFIED
        assert len(index.component_evidence_digests) == 6
    finally:
        store.close()


# ---------------------------------------------------------------------------
# 9.2 identity / currentness negative tests
# ---------------------------------------------------------------------------


def test_p7_executable_identity_ignores_documentation_and_tracks_source(tmp_path: Path):
    """Plan-only changes never stale executable evidence; source changes do."""

    root = tmp_path / "pkg"
    (root / "sub").mkdir(parents=True)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / "sub" / "b.py").write_text("y = 2\n", encoding="utf-8")
    (root / "NOTES.md").write_text("plan\n", encoding="utf-8")
    baseline = executable_source_tree_digest(root)

    (root / "NOTES.md").write_text("plan, revised extensively\n", encoding="utf-8")
    (root / "WORKPLAN.md").write_text("a whole new workplan\n", encoding="utf-8")
    assert executable_source_tree_digest(root) == baseline

    (root / "sub" / "b.py").write_text("y = 3\n", encoding="utf-8")
    assert executable_source_tree_digest(root) != baseline


def test_p7_identity_changes_stale_the_attempt(tmp_path: Path):
    """Executable, environment, and specification each key the attempt."""

    config, workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        binding = session.binding
        baseline = binding.attempt_identity
        import dataclasses

        from mdstats.training_data.qualification.identity import (
            EnvironmentFingerprint,
            ExecutableCandidateIdentity,
        )

        other_executable = dataclasses.replace(
            binding.executable, source_tree_digest="0" * 64
        )
        assert (
            dataclasses.replace(binding, executable=other_executable).attempt_identity
            != baseline
        )
        # A documentation-only Git move does not change the identity.
        documentary = dataclasses.replace(binding.executable, git_commit="deadbeef")
        assert (
            dataclasses.replace(binding, executable=documentary).attempt_identity == baseline
        )
        other_environment = dataclasses.replace(
            binding.environment, accelerator_model="some-other-gpu"
        )
        assert (
            dataclasses.replace(binding, environment=other_environment).attempt_identity
            != baseline
        )
        # Machine capacity is recorded but is not identity.
        capacity = dataclasses.replace(binding.environment, cpu_thread_count=1)
        assert (
            dataclasses.replace(binding, environment=capacity).attempt_identity == baseline
        )
        assert (
            dataclasses.replace(binding, publication_member_digest="1" * 64).attempt_identity
            != baseline
        )
    finally:
        store.close()


def test_p7_specification_change_stales_qualification_evidence(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    original_attempt = session.binding.attempt_identity
    store.close()

    p5.rewrite_config(config, "probe_configurations = 2", "probe_configurations = 3")
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert session.binding.attempt_identity != original_attempt
        # None of the previously completed components is reachable under the
        # new specification identity.
        for component in session.plan.planned_components:
            assert session.completed_component(component) is None
    finally:
        store.close()


def test_p7_tampered_terminal_record_is_a_hard_failure(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        record = resolve_current_qualification_verdict(store, paths, session.context)
        path = session.store.object_path(record.content_digest)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["verdict"] = "release_qualified"
        path.write_text(json.dumps(payload), encoding="utf-8")
    finally:
        store.close()
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        with pytest.raises(Exception):
            resolve_current_qualification_verdict(store, paths, session.context)
    finally:
        store.close()


def test_p7_stale_generation_cannot_publish_qualification(tmp_path: Path):
    """A newer campaign generation makes an in-flight qualification stale."""

    config, workspace, harness = _campaign(tmp_path)
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        from mdstats.training_data.qualification.store import (
            POINTER_QUALIFICATION_PLAN,
            publish_current_qualification_pointer,
        )
        import dataclasses

        stale = dataclasses.replace(
            session.context.selected.binding, campaign_generation=99
        )
        with pytest.raises(PostSelectionStaleBindingError):
            publish_current_qualification_pointer(
                store,
                binding=stale,
                kind=POINTER_QUALIFICATION_PLAN,
                content_digest="a" * 64,
            )
    finally:
        store.close()


# ---------------------------------------------------------------------------
# 9.3 resume, cleanup, resource
# ---------------------------------------------------------------------------


def test_p7_resume_reuses_only_authenticated_same_identity_evidence(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    first = harness.evaluated_atoms
    assert first > 0

    resumed = fx.QualificationHarness()
    fx.attach_labels(resumed, config)
    assert fx.run_qualification_command(config, "run", harness=resumed) == 0
    # Every completed component was reused from authenticated stored evidence.
    assert resumed.evaluated_atoms == 0
    assert resumed.deployed_calls == []
    assert resumed.dynamics_calls == []


def test_p7_partial_component_publication_is_not_accepted_as_complete(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        position = session.attempt_root / "components" / f"{COMPONENT_DYNAMICS}.json"
        assert position.is_file()
        position.unlink()
        assert session.completed_component(COMPONENT_DYNAMICS) is None
    finally:
        store.close()
    # The dynamics component is recomputed rather than assumed complete.
    resumed = fx.QualificationHarness()
    fx.attach_labels(resumed, config)
    assert fx.run_qualification_command(config, "run", harness=resumed) == 0
    assert resumed.dynamics_calls


def test_p7_cleanup_preserves_referenced_artifacts_and_release_evidence(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        _c, _p, session_store, session = fx.load_session(config, harness)
        member = session.publication.members[0]
        checkpoint = checkpoint_path_for_member(session.context, member)
        session_store.close()

        from mdstats.training_data.qualification.store import acquire_attempt_reference

        acquire_attempt_reference(
            paths,
            session.context.selected.binding,
            attempt_identity=session.binding.attempt_identity,
            publication_digest=session.binding.publication_digest,
            binding_digest=session.binding.content_digest,
            referenced_paths=[str(checkpoint)],
        )
        boundary = cli._campaign_ownership_boundary(cfg, paths, store)
        authorized, detail = boundary.destructive_authorization(checkpoint)
        assert not authorized
        assert "actively referenced" in detail

        evidence_root = qualification_root(paths, session.context.selected.binding.campaign_generation)
        authorized, detail = boundary.destructive_authorization(evidence_root / "objects")
        assert not authorized
        assert "never reconstructible scratch" in detail

        # Releasing the attempt releases only the reference, never the evidence.
        from mdstats.training_data.qualification.store import release_attempt_reference

        release_attempt_reference(
            paths,
            session.context.selected.binding,
            attempt_identity=session.binding.attempt_identity,
        )
        boundary = cli._campaign_ownership_boundary(cfg, paths, store)
        authorized, _detail = boundary.destructive_authorization(checkpoint)
        assert authorized
        authorized, _detail = boundary.destructive_authorization(evidence_root / "objects")
        assert not authorized
    finally:
        store.close()


def test_p7_terminal_completion_releases_the_attempt_reference(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        state = read_attempt_state(
            paths, session.context.selected.binding, session.binding.attempt_identity
        )
        # The nonlocked stage is not terminal yet: the locked test is required.
        assert state.state == ATTEMPT_ACTIVE
        assert state.referenced_paths
    finally:
        store.close()
    assert fx.run_qualification_command(config, "activate-locked", harness=harness, confirm=True) == 0
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        state = read_attempt_state(
            paths, session.context.selected.binding, session.binding.attempt_identity
        )
        assert state.state == ATTEMPT_TERMINAL
        assert state.referenced_paths == ()
        # A crash-restart reconstructs the released state from durable evidence.
        fence = build_qualification_retention_fence(paths)
        assert fence.referenced_paths == frozenset()
    finally:
        store.close()


def test_p7_bounded_concurrency_yields_identical_evidence(tmp_path: Path):
    """Scheduling is not science: case workers cannot change the evidence."""

    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        serial = session.completed_component(COMPONENT_DYNAMICS)
        position = session.attempt_root / "components" / f"{COMPONENT_DYNAMICS}.json"
        position.unlink()
    finally:
        store.close()

    concurrent_harness = fx.QualificationHarness()
    fx.attach_labels(concurrent_harness, config)
    assert (
        fx.run_qualification_command(
            config, "run", harness=concurrent_harness, case_workers=4
        )
        == 0
    )
    assert len(concurrent_harness.dynamics_calls) == len(serial.payload["members"][0]["cases"])
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        concurrent = session.completed_component(COMPONENT_DYNAMICS)
    finally:
        store.close()
    # Byte-identical evidence, not merely an equal verdict.
    assert concurrent.content_digest == serial.content_digest


# ---------------------------------------------------------------------------
# 9.4 scientific anti-fallback
# ---------------------------------------------------------------------------


def test_p7_deployment_divergence_rejects_the_exact_publication(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    harness.member_bias = {"seed-5": 5.0}
    with pytest.raises(QualificationError, match="rejected the exact frozen publication"):
        _qualify_nonlocked(config, harness)
    record = _current_record(config, harness)
    assert record.verdict is QualificationVerdict.REJECTED
    assert record.outcome(COMPONENT_DEPLOYMENT_PARITY).status is ComponentStatus.REJECTED
    # The publication is untouched: no member was substituted or removed.
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert [m.member_id for m in session.publication.members] == ["seed-5"]
    finally:
        store.close()


def test_p7_dynamics_instability_rejects_and_never_reselects(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    harness.dynamics_overrides = {"minimum_pair_distance_angstrom": 0.05}
    with pytest.raises(QualificationError, match="rejected the exact frozen publication"):
        _qualify_nonlocked(config, harness)
    record = _current_record(config, harness)
    assert record.outcome(COMPONENT_DYNAMICS).status is ComponentStatus.REJECTED
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(COMPONENT_DYNAMICS)
        reasons = evidence.payload["members"][0]["reason_codes"]
        assert any("minimum_pair_distance_below_safety_bound" in item for item in reasons)
        # The selected binding and CV acceptance are entirely unchanged.
        assert session.context.selected.binding.n_selected == 4
    finally:
        store.close()


def test_p7_committee_member_failure_rejects_rather_than_shrinking(tmp_path: Path):
    """With two frozen members, one failure rejects the committee as published."""

    text = fx.fixture_config_text(production_seeds="[5, 6]")
    config, workspace, harness = _campaign(tmp_path, config_text=text)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        members = [member.member_id for member in session.publication.members]
    finally:
        store.close()
    assert members == ["seed-5", "seed-6"]
    harness.member_bias = {"seed-6": 5.0}
    with pytest.raises(QualificationError, match="rejected the exact frozen publication"):
        _qualify_nonlocked(config, harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(COMPONENT_DEPLOYMENT_PARITY)
        assert evidence.metrics["failed_members"] == ["seed-6"]
        # The surviving member is not promoted; membership is byte-identical.
        assert [m.member_id for m in session.publication.members] == ["seed-5", "seed-6"]
    finally:
        store.close()


def test_p7_calibration_recovers_known_committee_scaling(tmp_path: Path):
    """A deterministic two-member offset recovers an exactly known scaling."""

    text = fx.fixture_config_text(
        production_seeds="[5, 6]",
        calibration_overrides="coverage_target = 1.0\ncoverage_tolerance = 0.02\n",
    )
    config, workspace, harness = _campaign(tmp_path, config_text=text)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        runs = [member.run_identity for member in session.publication.members]
        # The two members differ only on the reserved calibration role, so the
        # other components still judge the same product.
        harness.bias_frame_uids = set(session.binding.evidence_roles.calibration_frame_uids)
    finally:
        store.close()
    # members are truth + d and truth + 3d, so scaling is exactly sqrt(2).
    harness.checkpoint_force_bias = {runs[0]: 0.01, runs[1]: 0.03}
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(COMPONENT_CALIBRATION)
        assert evidence.status is ComponentStatus.PASSED
        assert evidence.metrics["scaling_factor"] == pytest.approx(np.sqrt(2.0), rel=1e-6)
        assert evidence.metrics["empirical_coverage"] == pytest.approx(1.0)
    finally:
        store.close()


def test_p7_calibration_is_not_applicable_for_a_single_model_publication(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(COMPONENT_CALIBRATION)
        assert evidence.status is ComponentStatus.NOT_APPLICABLE
        assert evidence.reason_code == "single_model_publication_without_uncertainty_estimator"
    finally:
        store.close()


# ---------------------------------------------------------------------------
# P7-F locked activation
# ---------------------------------------------------------------------------


def test_p7f_locked_activation_requires_completed_mandatory_components(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    with pytest.raises(QualificationActivationError, match="mandatory nonlocked component"):
        fx.run_qualification_command(config, "activate-locked", harness=harness, confirm=True)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert resolve_current_locked_activation(store, _paths, session.context) is None
        assert session.completed_component(COMPONENT_LOCKED_TEST) is None
    finally:
        store.close()


def test_p7f_second_activation_of_the_same_cohort_is_refused(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    assert fx.run_qualification_command(config, "activate-locked", harness=harness, confirm=True) == 0
    with pytest.raises(QualificationActivationError, match="already been activated"):
        fx.run_qualification_command(config, "activate-locked", harness=harness, confirm=True)


def test_p7f_locked_failure_rejects_and_cannot_be_repaired(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        run_identity = session.publication.members[0].run_identity
    finally:
        store.close()
    harness.checkpoint_force_bias = {run_identity: 3.0}
    with pytest.raises(QualificationError, match="locked interpolation test rejected"):
        fx.run_qualification_command(config, "activate-locked", harness=harness, confirm=True)
    record = _current_record(config, harness)
    assert record.verdict is QualificationVerdict.REJECTED
    assert record.outcome(COMPONENT_LOCKED_TEST).status is ComponentStatus.REJECTED
    # Loosening the locked policy afterwards does not create a fresh locked test.
    p5.rewrite_config(config, "[qualification.locked]", "[qualification.locked]\nforce_component_rmse_maximum_ev_per_angstrom = 100.0")
    relaxed = fx.QualificationHarness()
    fx.attach_labels(relaxed, config)
    # The revealed cohort is identified by the product and the locked role, not
    # by the policy, so a loosened policy cannot manufacture a fresh locked test.
    with pytest.raises(QualificationActivationError, match="already been activated"):
        fx.run_qualification_command(config, "activate-locked", harness=relaxed, confirm=True)


def test_p7f_locked_activation_binds_the_exact_product_and_cohort(tmp_path: Path):
    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    assert fx.run_qualification_command(config, "activate-locked", harness=harness, confirm=True) == 0
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        activation = resolve_current_locked_activation(store, paths, session.context)
        assert activation.publication_digest == session.binding.publication_digest
        assert activation.publication_member_digest == session.binding.publication_member_digest
        assert activation.locked_role_digest == session.binding.evidence_roles.locked_digest
        assert activation.executable_digest == session.binding.executable.content_digest
        assert activation.environment_digest == session.binding.environment.content_digest
        assert activation.prerequisite_component_digests
        assert activation.activated_at
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Runtime capability: a real bounded LAMMPS/ML-IAP execution
# ---------------------------------------------------------------------------


def test_p7b_supported_runtime_probe_reflects_the_real_environment():
    probe = probe_lammps_runtime(refresh=True)
    assert isinstance(probe.available, bool)
    if probe.available:
        assert probe.version
        assert probe.content_digest


def test_p7b_bounded_real_lammps_mliap_execution(tmp_path: Path):
    """A genuine LAMMPS/ML-IAP run through the real deployed-artifact path.

    The numerical model is a deterministic analytic unified ML-IAP potential -
    a toy MACE checkpoint cannot be converted at all - but the artifact, the
    pickle, the pair style, the neighbor list, the process group, and the
    energy/force extraction are all the real runtime.
    """

    probe = probe_lammps_runtime()
    if not probe.supports_deployed_execution:
        pytest.skip(f"supported LAMMPS/ML-IAP runtime unavailable: {probe.detail}")

    import pickle

    from ase import Atoms
    from lammps.mliap.mliap_unified_lj import MLIAPUnifiedLJ

    from mdstats.training_data.qualification.runtime_capability import (
        deployed_static_evaluation,
    )

    artifact = tmp_path / "unified.pkl"
    with artifact.open("wb") as handle:
        pickle.dump(MLIAPUnifiedLJ(["Ar"], epsilon=1.0, sigma=1.0, rcutfac=2.5), handle)

    atoms = Atoms(
        "Ar4",
        positions=[[0.0, 0.0, 0.0], [1.6, 0.0, 0.0], [0.0, 1.6, 0.0], [0.0, 0.0, 1.6]],
        cell=[8.0, 8.0, 8.0],
        pbc=True,
    )
    energy, forces = deployed_static_evaluation(
        atoms,
        artifact_path=artifact,
        element_types=("Ar",),
        working_directory=tmp_path / "work",
        timeout_seconds=300.0,
    )
    assert np.isfinite(energy)
    assert forces.shape == (4, 3)
    assert np.all(np.isfinite(forces))
    # Newton's third law holds for the real deployed pair interaction.
    assert np.allclose(forces.sum(axis=0), 0.0, atol=1.0e-8)


def test_p7b_unavailable_runtime_is_blocking_not_passing(tmp_path: Path, monkeypatch):
    """An absent supported runtime is reported as unavailable, never as a pass."""

    from mdstats.training_data.qualification import runtime_capability

    config, workspace, harness = _campaign(
        tmp_path,
        config_text=fx.fixture_config_text().replace(
            "require_deployed_runtime = false", "require_deployed_runtime = true"
        ),
    )
    monkeypatch.setattr(
        runtime_capability,
        "probe_lammps_runtime",
        lambda **_kwargs: runtime_capability.LammpsRuntimeProbe(
            available=False,
            version=None,
            mliap_available=False,
            mliappy_available=False,
            python_module_path=None,
            detail="not installed in this environment",
        ),
    )
    from mdstats.training_data.qualification import deployment as deployment_module

    monkeypatch.setattr(
        deployment_module, "probe_lammps_runtime", runtime_capability.probe_lammps_runtime
    )
    with pytest.raises(Exception) as excinfo:
        fx.run_qualification_command(config, "run", harness=harness)
    assert "unavailable" in str(excinfo.value)
    assert _current_record(config, harness) is None


def test_p7_attempt_reference_survives_process_death_and_grants_no_currentness(
    tmp_path: Path,
):
    """A retention reference is coordination metadata, not scientific authority."""

    config, workspace, harness = _campaign(tmp_path)
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        checkpoint = checkpoint_path_for_member(session.context, member)
        binding = session.context.selected.binding
        attempt = session.binding.attempt_identity

        from mdstats.training_data.qualification.store import acquire_attempt_reference

        acquire_attempt_reference(
            paths,
            binding,
            attempt_identity=attempt,
            publication_digest=session.binding.publication_digest,
            binding_digest=session.binding.content_digest,
            referenced_paths=[str(checkpoint)],
        )
    finally:
        store.close()

    # A fresh process reconstructs the reference from durable attempt state
    # alone, with no in-memory carry-over.
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        restored = read_attempt_state(
            paths, session.context.selected.binding, session.binding.attempt_identity
        )
        assert restored.state == ATTEMPT_ACTIVE
        assert str(checkpoint_path_for_member(session.context, session.publication.members[0])) in (
            restored.referenced_paths
        )
        fence = build_qualification_retention_fence(paths)
        assert fence.protects(checkpoint)[0]
        # The fence can only ever reduce deletion authority: it exposes no
        # publication, membership, currentness, or verdict surface.
        surface = {name for name in dir(fence) if not name.startswith("_")}
        assert surface == {"qualification_roots", "referenced_paths", "is_active", "protects"}
    finally:
        store.close()


def test_p7_provider_is_released_on_success_and_on_exception(tmp_path: Path):
    """Model ownership is released deterministically on both paths."""

    from mdstats.training_data.qualification.providers import member_provider

    config, workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        with member_provider(session.context, member) as provider:
            assert not provider.closed
        assert provider.closed

        with pytest.raises(RuntimeError, match="deliberate"):
            with member_provider(session.context, member) as provider:
                raise RuntimeError("deliberate qualification failure")
        assert provider.closed
    finally:
        store.close()


def test_p7_release_evidence_points_at_the_predecessor_baseline(tmp_path: Path):
    """Terminal evidence records the current P5/P6 reclosure it descends from."""

    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    record = _current_record(config, harness)
    assert record.predecessor_reclosure_digest
    assert record.predecessor_executable_tree_digest
    assert record.predecessor_executable_commit
    assert record.predecessor_evidence_commit == record.predecessor_reclosure_digest


def test_p7c_strain_modes_are_requested_and_qualified_when_enabled(tmp_path: Path):
    """Enabled strain modes are matched-pair reference requests, not a no-op."""

    text = fx.fixture_config_text(strain_magnitudes="[-0.01, 0.01]")
    config, workspace, harness = _campaign(tmp_path, config_text=text)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert session.plan.physical_plan.strain_magnitudes == (-0.01, 0.01)
        modes = {item.mode for item in session.reference_request.geometries}
        assert "strain:iso:+0.010000" in modes
        assert "strain:iso:-0.010000" in modes
    finally:
        store.close()
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(COMPONENT_PHYSICAL_PES)
        assert evidence.status is ComponentStatus.PASSED
        rows = evidence.payload["members"][0]["strain_modes"]
        assert rows and all(
            row["model_volumetric_curvature_ev"] > 0.0 for row in rows
        )
    finally:
        store.close()


def test_p7c_asymmetric_strain_configuration_fails_closed(tmp_path: Path):
    from mdstats.training_data._common import TrainingDataInputError
    from mdstats.training_data.qualification import resolve_qualification_spec_identity

    with pytest.raises(TrainingDataInputError, match="matched \\+/- reference pair"):
        resolve_qualification_spec_identity(
            {"qualification": {"physical": {"strain_magnitudes": [0.01]}}}
        )


def test_p7_publication_identity_composes_the_full_upstream_lineage(tmp_path: Path):
    """A CV, method, production-policy, or member change stales qualification."""

    config, workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        payload = session.publication.to_dict()
        for field in (
            "selected_binding_digest",
            "final_plan_digest",
            "completion_digest",
            "method_identity_digest",
            "final_production_policy_digest",
            "cv_plan_digest",
            "cv_authorization_digest",
            "committee_policy",
            "m3_membership_digest",
        ):
            assert payload[field], field
        # The qualification binding descends from the publication and its exact
        # ordered member bytes, so any upstream change stales every descendant.
        assert session.binding.publication_digest == session.publication.content_digest
        assert session.binding.publication_member_digest == session.publication.member_digest
        assert session.binding.selected_binding_digest == (
            session.context.selected.binding.content_digest
        )
    finally:
        store.close()


def test_p7_introduces_no_second_cache_or_cleanup_authority():
    """Cache and safe cleanup remain the single accepted P6 owners."""

    joined = "\n".join(_qualification_sources().values())
    for forbidden in (
        "def command_cleanup",
        "def command_storage",
        "_MANUAL_RECLAMATION_TIERS",
        "frame_cache",
        "def evict",
        "def reclaim",
    ):
        assert forbidden not in joined, forbidden
    core = Path(cli.__file__).read_text(encoding="utf-8")
    assert core.count("def command_cleanup") == 1
    assert core.count("_MANUAL_RECLAMATION_TIERS = ") == 1
    # The qualification fence only ever *reduces* deletion authority; it is
    # composed with the target-size fence rather than replacing it.
    from mdstats.training_data.storage_accounting import CompositeRetentionFence

    composite = CompositeRetentionFence(())
    assert composite.protects(Path("/tmp")) == (False, "")


def test_p7d_topology_change_is_detected_independently_of_averaged_error():
    """A broken bond is visible even when averaged geometry error is small."""

    from ase import Atoms

    from mdstats.training_data.qualification.geometry import (
        angle_table,
        bond_table,
        displacement_metrics,
        paired_statistics,
    )

    reference = Atoms(
        "OSiO",
        positions=[[0.0, 0.0, 0.0], [1.62, 0.0, 0.0], [3.24, 0.0, 0.0]],
        cell=[20.0, 20.0, 20.0],
        pbc=True,
    )
    reference_bonds = bond_table(reference, cutoff_scale=1.20)
    assert set(reference_bonds) == {(0, 1), (1, 2)}
    assert set(angle_table(reference, reference_bonds)) == {(1, 0, 2)}

    intact = reference.copy()
    intact.set_positions(
        [[0.0, 0.0, 0.0], [1.66, 0.0, 0.0], [3.24, 0.0, 0.0]]
    )
    assert set(bond_table(intact, cutoff_scale=1.20)) == set(reference_bonds)
    bond_rmse, bond_max, compared = paired_statistics(
        reference_bonds, bond_table(intact, cutoff_scale=1.20)
    )
    assert compared == 2 and bond_max == pytest.approx(0.04, abs=1e-9)

    broken = reference.copy()
    broken.set_positions(
        [[0.0, 0.0, 0.0], [1.62, 0.0, 0.0], [6.20, 0.0, 0.0]]
    )
    broken_bonds = bond_table(broken, cutoff_scale=1.20)
    assert (1, 2) not in broken_bonds
    # The surviving bond is still essentially perfect, which is exactly why a
    # topology check cannot be replaced by an averaged geometry error.
    surviving_rmse, _max, surviving_count = paired_statistics(reference_bonds, broken_bonds)
    assert surviving_count == 1 and surviving_rmse == pytest.approx(0.0, abs=1e-12)
    rms, maximum = displacement_metrics(reference, broken)
    assert maximum > 2.0


def test_p7d_relaxation_divergence_rejects_the_exact_publication(tmp_path: Path):
    """A model that relaxes away from the reference geometry is rejected."""

    text = fx.fixture_config_text().replace(
        "rms_displacement_maximum_angstrom = 0.30",
        "rms_displacement_maximum_angstrom = 0.30",
    )
    config, workspace, harness = _campaign(tmp_path, config_text=text)
    assert _run_to_waiting(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        # The reference relaxations are produced by a materially softer
        # potential, so its relaxed geometry is somewhere the frozen product
        # does not go.  (A different equilibrium distance alone would not do
        # it: the label anchoring cancels r0 from the restoring force.)
        reference_harness = fx.QualificationHarness(
            potential=fx.AnalyticPairPotential(stiffness=0.05)
        )
        fx.attach_labels(reference_harness, config)
        fx.supply_analytic_reference_bundle(session, reference_harness)
    finally:
        store.close()
    with pytest.raises(QualificationError, match="rejected the exact frozen publication"):
        fx.run_qualification_command(config, "run", harness=harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(COMPONENT_RELAXATION)
        assert evidence.status is ComponentStatus.REJECTED
        reasons = evidence.payload["members"][0]["reason_codes"]
        assert any("displacement_above_maximum" in item for item in reasons)
        # Membership is untouched by the rejection.
        assert [m.member_id for m in session.publication.members] == ["seed-5"]
    finally:
        store.close()


def test_p7g_qualification_policy_change_leaves_the_publication_current(tmp_path: Path):
    """Invalidation scope: a qualification-only change stales only descendants."""

    config, workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        publication_before = session.publication.content_digest
        members_before = session.publication.member_digest
        selected_before = session.context.selected.binding.content_digest
    finally:
        store.close()

    p5.rewrite_config(config, "probe_configurations = 2", "probe_configurations = 3")
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert session.publication.content_digest == publication_before
        assert session.publication.member_digest == members_before
        assert session.context.selected.binding.content_digest == selected_before
        # Only the qualification descendants are stale.
        for component in session.plan.planned_components:
            assert session.completed_component(component) is None
    finally:
        store.close()
