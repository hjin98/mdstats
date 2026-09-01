"""P7 revision-12 repair acceptance.

Revision 12 is narrow. It closes three source-level defects the revision-11
implementation still carried:

* **R12-B9** the LAMMPS pressure -> canonical stress boundary was converting bar
  as GPa and defaulting the pressure/tension sign, and stress applicability was
  an operator switch rather than a capability decision;
* **R12-B13** the exact three-axis periodicity was collapsed to one boolean at
  the deployed runtime boundary, so a mixed-boundary system was silently
  executed as a different physical system;
* **R12-B7** release evidence recorded a resource *identity* but never what the
  qualification actually cost, and had no disk-safety integration.

Revision-10 and revision-11 acceptance remain binding and are not restated here.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import tests._mlff_qualification_fixture as fx
import tests._mlff_post_selection_fixture as p5

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data.qualification import (
    COMPONENT_DEPLOYMENT_PARITY,
    COMPONENT_DYNAMICS,
    COMPONENT_PHYSICAL_PES,
    ComponentStatus,
    QualificationError,
    QualificationVerdict,
    resolve_current_qualification_verdict,
)


def _campaign(tmp_path: Path, *, config_text: str | None = None, **harness_kwargs):
    harness = fx.QualificationHarness(**harness_kwargs)
    config, workspace = fx.build_qualified_campaign(
        tmp_path, config_text=config_text, harness=harness
    )
    return config, workspace, harness


def _supply_reference(config: Path, harness) -> None:
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        fx.supply_analytic_reference_bundle(session, harness)
    finally:
        store.close()


def _qualify_nonlocked(config: Path, harness, **extra) -> int:
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _supply_reference(config, harness)
    return fx.run_qualification_command(config, "run", harness=harness, **extra)


def _current(config: Path, harness):
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        return resolve_current_qualification_verdict(
            store, paths, session.context, binding=session.binding
        )
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R12-B9 — the LAMMPS pressure -> canonical stress boundary
# ---------------------------------------------------------------------------


def test_r12b9_lammps_metal_pressure_converts_to_canonical_stress():
    """Known bar pressures, including shear, become the expected eV/A^3 stress."""

    from mdstats.training_data.qualification.stress import (
        BAR_TO_GPA,
        CANONICAL_VOIGT_ORDER,
        EV_PER_ANGSTROM3_TO_GPA,
        canonical_stress_from_lammps_metal_pressure,
    )

    # pxx, pyy, pzz, pxy, pyz, pxz in bar, with genuinely distinct shears so a
    # transposed or rotated ordering cannot pass.
    pressures = np.array([1000.0, -2000.0, 3000.0, 40.0, 50.0, 60.0], dtype=np.float64)
    tensor = canonical_stress_from_lammps_metal_pressure(
        pressures, voigt_order=CANONICAL_VOIGT_ORDER
    )

    factor = BAR_TO_GPA / EV_PER_ANGSTROM3_TO_GPA
    expected = -factor * np.array(
        [
            [1000.0, 40.0, 60.0],
            [40.0, -2000.0, 50.0],
            [60.0, 50.0, 3000.0],
        ],
        dtype=np.float64,
    )
    assert np.allclose(tensor, expected, rtol=0.0, atol=1.0e-18)
    assert np.allclose(tensor, tensor.T)

    # Each shear lands in its own slot: swapping two of them changes the result.
    swapped = canonical_stress_from_lammps_metal_pressure(
        np.array([1000.0, -2000.0, 3000.0, 40.0, 60.0, 50.0], dtype=np.float64),
        voigt_order=CANONICAL_VOIGT_ORDER,
    )
    assert not np.allclose(swapped, tensor)


def test_r12b9_positive_compression_becomes_negative_tensile_stress():
    """LAMMPS pressure is positive in compression; canonical stress is tension."""

    from mdstats.training_data.qualification.stress import (
        canonical_stress_from_lammps_metal_pressure,
    )

    compressed = canonical_stress_from_lammps_metal_pressure(
        np.array([5000.0, 5000.0, 5000.0, 0.0, 0.0, 0.0], dtype=np.float64)
    )
    assert np.all(np.diag(compressed) < 0.0)

    tensioned = canonical_stress_from_lammps_metal_pressure(
        np.array([-5000.0, -5000.0, -5000.0, 0.0, 0.0, 0.0], dtype=np.float64)
    )
    assert np.all(np.diag(tensioned) > 0.0)


def test_r12b9_bar_misclassified_as_gpa_differs_by_ten_thousand():
    """The exact defect revision 12 reopened is detected, not just avoided."""

    from mdstats.training_data.qualification.stress import (
        canonical_stress_from_lammps_metal_pressure,
        canonical_stress_tensor,
    )

    pressures = np.array([1000.0, 2000.0, 3000.0, 10.0, 20.0, 30.0], dtype=np.float64)
    correct = canonical_stress_from_lammps_metal_pressure(pressures)
    misclassified = canonical_stress_tensor(pressures, units="gpa", sign=-1.0)
    ratio = misclassified[0, 0] / correct[0, 0]
    assert ratio == pytest.approx(1.0e4, rel=1.0e-9)
    assert not np.allclose(correct, misclassified)


def test_r12b9_worker_conversion_owns_units_and_sign_without_request_input():
    """Units and sign are source facts, so the request cannot supply them."""

    worker = (
        Path(cli.__file__).resolve().parent / "qualification" / "_lammps_worker.py"
    ).read_text(encoding="utf-8")
    assert "canonical_stress_from_lammps_metal_pressure" in worker
    assert 'units="gpa"' not in worker
    assert "stress_sign" not in worker
    assert 'request.get("stress_voigt_order"' not in worker

    # And the specification no longer offers them as operator knobs.
    from mdstats.training_data.qualification.spec import (
        resolve_qualification_spec_identity,
    )

    policy = resolve_qualification_spec_identity({}).component_policy(
        COMPONENT_DEPLOYMENT_PARITY
    )
    assert "stress_sign" not in policy
    assert "stress_voigt_order" not in policy
    assert "stress_applicable" not in policy


# ---------------------------------------------------------------------------
# R12-B9 — stress applicability is a capability decision
# ---------------------------------------------------------------------------


def _stress_config(**kwargs) -> str:
    overrides = "".join(f"{key} = {value}\n" for key, value in kwargs.items())
    return fx.fixture_config_text().replace(
        "require_deployed_runtime = false",
        f"require_deployed_runtime = false\n{overrides}",
    )


def test_r12b9_capability_resolves_applicable_and_stress_is_compared(tmp_path: Path):
    """A product that actually has a stress channel gets its stress qualified."""

    config, _workspace, harness = _campaign(
        tmp_path, potential=fx.AnalyticPairPotential(report_stress=True)
    )
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(
            COMPONENT_DEPLOYMENT_PARITY,
            session.component_input_digest(COMPONENT_DEPLOYMENT_PARITY, None),
        )
        assert evidence.status is ComponentStatus.PASSED
        metrics = dict(evidence.metrics)
        assert metrics["stress_applicable"] is True
        assert int(metrics["stress_compared_configurations"]) > 0
        capability = evidence.payload["stress_capability"]
        assert capability["applicable"] is True
        assert "training_objective_weights_stress" in capability["reason_codes"]
        assert "authenticated_model_returns_stress" in capability["reason_codes"]
    finally:
        store.close()


def test_r12b9_deployed_stress_divergence_rejects(tmp_path: Path):
    """Stress is genuinely compared, not merely recorded as available."""

    config, _workspace, harness = _campaign(
        tmp_path, potential=fx.AnalyticPairPotential(report_stress=True)
    )
    harness.deployed_stress_offset = 1.0
    with pytest.raises(QualificationError, match="rejected the exact frozen publication"):
        _qualify_nonlocked(config, harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(
            COMPONENT_DEPLOYMENT_PARITY,
            session.component_input_digest(COMPONENT_DEPLOYMENT_PARITY, None),
        )
        assert evidence.status is ComponentStatus.REJECTED
        assert (
            float(
                evidence.payload["members"][0][
                    "maximum_stress_tolerance_excess_ev_per_angstrom3"
                ]
            )
            > 0.0
        )
    finally:
        store.close()


def test_r12b9_operator_cannot_suppress_an_available_stress_channel(tmp_path: Path):
    """A declared-inapplicable reason is recorded, never obeyed over capability."""

    config, _workspace, harness = _campaign(
        tmp_path,
        config_text=_stress_config(
            stress_declared_inapplicable_reason='"operator would rather not"'
        ),
        potential=fx.AnalyticPairPotential(report_stress=True),
    )
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        from mdstats.training_data.qualification.geometry import atoms_for_frame

        atoms = [
            atoms_for_frame(session.context, base.frame_uid)
            for base in session.plan.physical_plan.bases
        ]
        capability = session.stress_capability(atoms)
        assert capability.applicable is True
        assert capability.policy_declared_inapplicable_reason == "operator would rather not"
        assert "frozen_policy_declared_inapplicable" in capability.reason_codes
    finally:
        store.close()


def test_r12b9_capability_reasons_are_auditable_when_inapplicable(tmp_path: Path):
    """A product with no stress channel says so, with its reasons."""

    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        from mdstats.training_data.qualification.geometry import atoms_for_frame

        atoms = [
            atoms_for_frame(session.context, base.frame_uid)
            for base in session.plan.physical_plan.bases
        ]
        capability = session.stress_capability(atoms)
        assert capability.applicable is False
        assert "authenticated_model_returns_no_stress" in capability.reason_codes
        assert capability.required is False
        assert capability.content_digest
    finally:
        store.close()


def test_r12b9_required_stress_on_an_incapable_product_fails_closed(tmp_path: Path):
    from mdstats.training_data.qualification.stress_capability import (
        StressCapabilityDecision,
    )

    with pytest.raises(QualificationError, match="requires stress"):
        StressCapabilityDecision(
            training_objective_weights_stress=False,
            reference_labels_available=False,
            model_reports_stress=False,
            fully_periodic=True,
            runtime_reports_stress=True,
            policy_requires_stress=True,
            policy_declared_inapplicable_reason=None,
            reason_codes=("training_objective_does_not_weight_stress",),
        )


def test_r12b9_capability_participates_in_stress_bearing_identity(tmp_path: Path):
    """A capability change stales stress-bearing component evidence."""

    import dataclasses

    from mdstats.training_data.qualification.stress_capability import (
        StressCapabilityDecision,
    )

    base = StressCapabilityDecision(
        training_objective_weights_stress=True,
        reference_labels_available=True,
        model_reports_stress=True,
        fully_periodic=True,
        runtime_reports_stress=True,
        policy_requires_stress=False,
        policy_declared_inapplicable_reason=None,
        reason_codes=("training_objective_weights_stress",),
    )
    assert base.applicable is True
    for field, value in (
        ("model_reports_stress", False),
        ("fully_periodic", False),
        ("training_objective_weights_stress", False),
    ):
        other = dataclasses.replace(base, **{field: value})
        assert other.content_digest != base.content_digest
        assert other.applicable is False


def test_r12b9_nonperiodic_configuration_is_not_stress_applicable():
    """A Cauchy stress is undefined without a cell; capability says so."""

    from ase import Atoms

    potential = fx.AnalyticPairPotential(report_stress=True)
    open_system = Atoms(
        "Li2", positions=[[0.0, 0.0, 0.0], [6.0, 0.0, 0.0]], cell=[10.0, 10.0, 10.0],
        pbc=[True, True, False],
    )
    assert potential.virial_stress(open_system) is None
    periodic = open_system.copy()
    periodic.set_pbc([True, True, True])
    assert potential.virial_stress(periodic) is not None


# ---------------------------------------------------------------------------
# R12-B13 — exact per-axis periodic boundary conditions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pbc,expected",
    [
        ((True, True, True), "boundary p p p"),
        ((False, False, False), "boundary f f f"),
        ((True, True, False), "boundary p p f"),
        ((True, False, False), "boundary p f f"),
        ((False, True, False), "boundary f p f"),
    ],
)
def test_r12b13_boundary_command_is_axis_exact(pbc, expected):
    from mdstats.training_data.qualification._lammps_worker import _boundary_command

    assert _boundary_command(pbc) == expected


def test_r12b13_request_without_periodicity_fails_closed():
    from mdstats.training_data.qualification._lammps_worker import _request_pbc

    with pytest.raises(ValueError, match="three-axis periodicity"):
        _request_pbc({"mode": "static"})
    with pytest.raises(ValueError, match="three-axis"):
        _request_pbc({"pbc": [True, True]})
    assert _request_pbc({"pbc": [True, False, True]}) == (True, False, True)


def test_r12b13_minimum_image_honours_each_axis_separately():
    """Wrapping a nonperiodic axis would invent an image that does not exist."""

    from mdstats.training_data.qualification._lammps_worker import _minimum_pair_distance

    cell = np.eye(3, dtype=np.float64) * 10.0
    # Two atoms 9 A apart along z: periodic in z they are 1 A apart, but with a
    # nonperiodic z they are genuinely 9 A apart.
    positions = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 9.0]], dtype=np.float64)
    assert _minimum_pair_distance(positions, cell, (True, True, True)) == pytest.approx(1.0)
    assert _minimum_pair_distance(positions, cell, (True, True, False)) == pytest.approx(9.0)
    assert _minimum_pair_distance(positions, cell, (False, False, False)) == pytest.approx(9.0)
    # A periodic x with a nonperiodic z still wraps x.
    positions_x = np.array([[0.0, 0.0, 0.0], [9.0, 0.0, 0.0]], dtype=np.float64)
    assert _minimum_pair_distance(positions_x, cell, (True, False, False)) == pytest.approx(1.0)
    assert _minimum_pair_distance(positions_x, cell, (False, False, False)) == pytest.approx(9.0)


def test_r12b13_runtime_requests_carry_the_exact_periodicity_vector():
    source_root = Path(cli.__file__).resolve().parent / "qualification"
    for name in ("runtime.py", "runtime_capability.py"):
        text = (source_root / name).read_text(encoding="utf-8")
        assert '"periodic": bool(np.all(' not in text, name
        assert '"pbc": [bool(value) for value in np.asarray(atoms.get_pbc()' in text, name
    worker = (source_root / "_lammps_worker.py").read_text(encoding="utf-8")
    assert 'request.get("periodic"' not in worker
    assert "boundary p p p\" if" not in worker


def test_r12b13_case_identity_distinguishes_periodicity():
    from mdstats.training_data.qualification.dynamics import dynamics_case_identity

    common = {
        "binding_digest": "a" * 64,
        "member_id": "seed-5",
        "frame_uid": "frame",
        "temperature": 300.0,
        "seed": 7,
        "reference_bundle_digest": "b" * 64,
        "relaxed_geometry_identity": "c" * 64,
    }
    full = dynamics_case_identity(**common, pbc=(True, True, True))
    mixed = dynamics_case_identity(**common, pbc=(True, True, False))
    none = dynamics_case_identity(**common, pbc=(False, False, False))
    assert len({full, mixed, none}) == 3


def test_r12b13_deployed_dynamics_preserves_periodicity_end_to_end(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(
            COMPONENT_DYNAMICS,
            session.component_input_digest(
                COMPONENT_DYNAMICS, session.authenticated_reference_bundle()
            ),
        )
        case = evidence.payload["members"][0]["cases"][0]
        sample = case["nve_samples"][0]
        assert sample["pbc"] == [True, True, True]
        assert len(sample["pbc"]) == 3
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R12-B7 — measured resource observation and disk safety
# ---------------------------------------------------------------------------


def test_r12b7_release_evidence_carries_a_measured_resource_observation(tmp_path: Path):
    from mdstats.training_data.qualification.record import ReleaseEvidenceIndex
    from mdstats.training_data.qualification.resource_observation import (
        QualificationResourceObservation,
    )
    from mdstats.training_data.qualification.runtime import (
        resolve_current_release_evidence,
    )

    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    record = _current(config, harness)
    assert record.resource_observation_digest is not None

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        index = resolve_current_release_evidence(
            store, paths, session.context, binding=session.binding
        )
        assert index.resource_observation_digest == record.resource_observation_digest
        observation = session.store.get(
            index.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        )
        # It authenticates to this exact attempt, not merely to the campaign.
        assert observation.binding_digest == session.binding.content_digest
        assert observation.attempt_identity == session.binding.attempt_identity
        assert observation.resource_scope_digest == session.binding.resource_scope_digest
        # And it is a measurement, not a placeholder.
        assert observation.is_measured
        assert observation.elapsed_seconds > 0.0
        components = {item.component for item in observation.component_timings}
        assert COMPONENT_DEPLOYMENT_PARITY in components
        assert any(item.elapsed_seconds > 0.0 for item in observation.component_timings)
        labels = {sample.label for sample in observation.filesystem_samples}
        assert {"start", "end"} <= labels
        for sample in observation.filesystem_samples:
            assert sample.total_bytes > 0
            assert sample.free_bytes > 0
        assert observation.minimum_free_disk_gib > 0.0
        assert observation.disk_reserve_satisfied is True
    finally:
        store.close()


def test_r12b7_low_disk_fails_before_unsafe_materialization(tmp_path: Path):
    """The configured reserve stops the attempt before it consumes the workspace."""

    from mdstats.training_data.qualification.resource_observation import (
        QualificationDiskReserveError,
        require_free_disk_reserve,
    )

    # An impossible reserve stands in for an exhausted filesystem.
    with pytest.raises(QualificationDiskReserveError, match="free-disk reserve"):
        require_free_disk_reserve(
            tmp_path, minimum_free_gib=1.0e12, operation="qualification component test"
        )
    # A satisfiable reserve returns the observed headroom and does nothing else.
    free = require_free_disk_reserve(
        tmp_path, minimum_free_gib=0.0, operation="qualification component test"
    )
    assert free > 0.0


def test_r12b7_disk_exhaustion_aborts_without_touching_science(tmp_path: Path):
    """An operational abort is not a scientific result and changes no identity."""

    config, _workspace, harness = _campaign(tmp_path)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _supply_reference(config, harness)

    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        binding_before = session.binding.content_digest
        plan_before = session.plan.content_digest
        publication_before = session.publication.content_digest
    finally:
        store.close()

    # An unsatisfiable reserve stands in for an exhausted filesystem. It is read
    # from the campaign's existing [execution] policy, not from a P7 knob.
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text + "\n[execution]\nminimum_free_disk_gib = 100000000.0\n", encoding="utf-8"
    )
    cfg, paths = cli._load_config(config)
    from mdstats.training_data._campaign_cli_core import CampaignStore

    store = CampaignStore(paths.state_db)
    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture")
    finally:
        store.close()

    with pytest.raises(Exception, match="free-disk reserve"):
        fx.run_qualification_command(config, "run", harness=harness)

    # Restore the policy; nothing scientific moved because of the abort.
    config.write_text(text, encoding="utf-8")
    store = CampaignStore(paths.state_db)
    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture")
    finally:
        store.close()
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert session.binding.content_digest == binding_before
        assert session.plan.content_digest == plan_before
        assert session.publication.content_digest == publication_before
    finally:
        store.close()


def test_r12b7_resource_observation_does_not_stale_scientific_evidence(tmp_path: Path):
    """Volatile cost observations are evidence, never identity."""

    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    first = _current(config, harness)

    # Re-running reuses every completed component, so the scientific record is
    # byte-identical even though the run cost different wall time.
    resumed = fx.QualificationHarness()
    fx.attach_labels(resumed, config)
    assert fx.run_qualification_command(config, "run", harness=resumed) == 0
    second = _current(config, resumed)
    assert second.components == first.components
    assert second.verdict is first.verdict
    assert second.plan_digest == first.plan_digest


def test_r12b7_restart_extends_one_attempt_without_rewriting_samples(tmp_path: Path):
    from mdstats.training_data.qualification.resource_observation import (
        QualificationResourceObservation,
    )

    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    first = _current(config, harness)

    resumed = fx.QualificationHarness()
    fx.attach_labels(resumed, config)
    assert fx.run_qualification_command(config, "run", harness=resumed) == 0
    second = _current(config, resumed)

    _cfg, _paths, store, session = fx.load_session(config, resumed)
    try:
        assert session.binding.attempt_identity
        earlier = session.store.get(
            first.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        )
        later = session.store.get(
            second.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        )
        # Both belong to the same attempt, and the earlier one is untouched.
        assert earlier.attempt_identity == later.attempt_identity
        assert session.store.has(earlier.content_digest)
        # The resumed run reused completed components and says so.
        assert any(item.reused for item in later.component_timings)
    finally:
        store.close()


def test_r12b7_observation_records_accelerator_and_memory_when_available(tmp_path: Path):
    from mdstats.training_data.qualification.resource_observation import (
        accelerator_observation,
        peak_process_rss_bytes,
    )

    peak = peak_process_rss_bytes()
    assert peak is None or peak > 0
    model, total, allocated = accelerator_observation("cpu")
    assert (model, total, allocated) == (None, None, None)
    model, total, allocated = accelerator_observation("cuda")
    # Either the host has no accelerator, or the existing telemetry answered.
    assert model is None or (isinstance(model, str) and total and total > 0)


# ---------------------------------------------------------------------------
# R12-B11 — an actual frozen publication member through the real owners
# ---------------------------------------------------------------------------


def test_r12b11_frozen_publication_member_drives_the_real_deployment_owners(
    tmp_path: Path,
):
    """The published member's own bytes go through the real export/ML-IAP owners.

    This is the publication path, not the tiny-model owner smoke: the campaign
    publishes a genuine multihead MACE checkpoint, P5 decides the member, and
    that exact member's authenticated bytes are exported at the canonical target
    head and wrapped by the real ``LAMMPS_MLIAP_MACE`` builder.
    """

    torch = pytest.importorskip("torch")
    pytest.importorskip("mace")

    from mdstats.training_data.post_selection_identity import (
        POST_SELECTION_TARGET_HEAD_NAME,
    )
    from mdstats.training_data.qualification.deployment import (
        default_deployment_exporter,
        default_mliap_artifact_builder,
    )
    from mdstats.training_data.qualification.publication import (
        authenticate_member_bytes,
        checkpoint_path_for_member,
    )

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(
        tmp_path, harness=harness, real_mace_checkpoint=True
    )
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        assert member.target_head_name == POST_SELECTION_TARGET_HEAD_NAME
        # The member's bytes are the exact authenticated published checkpoint.
        sha = authenticate_member_bytes(session.context, member)
        assert sha == member.representative_checkpoint_sha256
        source = checkpoint_path_for_member(session.context, member)

        artifact = default_deployment_exporter(
            source,
            tmp_path / "member-deploy",
            deployment_dtype=session.binding.environment.default_dtype,
            target_head=member.target_head_name,
        )
        assert artifact.target_head == member.target_head_name
        deployment_path = tmp_path / "member-deploy" / artifact.deployment_relative_path
        assert deployment_path.is_file()

        mliap_path = default_mliap_artifact_builder(
            deployment_path,
            tmp_path / "member-mliap.pt",
            head=member.target_head_name,
        )
        built = torch.load(mliap_path, map_location="cpu", weights_only=False)
        # The canonical target head, not the last head, is what would execute.
        assert int(built.model.head.item()) == 1
    finally:
        store.close()


def test_r12b11_real_publication_execution_is_blocking_until_a_capable_runtime(
    tmp_path: Path,
):
    """Execute the published member in LAMMPS, or record the gate as blocking."""

    from mdstats.training_data.qualification import probe_lammps_runtime

    probe = probe_lammps_runtime(refresh=True)
    if not probe.supports_deployed_execution:
        pytest.skip(
            "UNAVAILABLE/BLOCKING: this host lacks the supported LAMMPS/ML-IAP "
            f"runtime ({probe.detail}); R12-B11 is deferred to the supported "
            "target machine and is not downgraded to an analytic ML-IAP pass."
        )

    torch = pytest.importorskip("torch")
    from mdstats.training_data.qualification.deployment import (
        default_deployment_exporter,
        default_mliap_artifact_builder,
    )
    from mdstats.training_data.qualification.geometry import atoms_for_frame
    from mdstats.training_data.qualification.publication import (
        checkpoint_path_for_member,
    )
    from mdstats.training_data.qualification.runtime_capability import (
        deployed_static_evaluation,
    )
    from mdstats.training_data.qualification.errors import QualificationUnavailableError

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(
        tmp_path, harness=harness, real_mace_checkpoint=True
    )
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        try:
            artifact = default_deployment_exporter(
                checkpoint_path_for_member(session.context, member),
                tmp_path / "d",
                deployment_dtype=session.binding.environment.default_dtype,
                target_head=member.target_head_name,
            )
            mliap_path = default_mliap_artifact_builder(
                tmp_path / "d" / artifact.deployment_relative_path,
                tmp_path / "m.pt",
                head=member.target_head_name,
            )
            atoms = atoms_for_frame(
                session.context, session.plan.physical_plan.bases[0].frame_uid
            )
            kokkos_gpu_count = 1 if torch.cuda.is_available() else 0
            selected_cuda_device = 0 if torch.cuda.is_available() else None
            energy, forces = deployed_static_evaluation(
                atoms,
                artifact_path=mliap_path,
                element_types=("Li", "O"),
                working_directory=tmp_path / "work",
                timeout_seconds=900.0,
                kokkos_gpu_count=kokkos_gpu_count,
                selected_cuda_device=selected_cuda_device,
            )
        except QualificationUnavailableError as exc:
            pytest.skip(
                "UNAVAILABLE/BLOCKING: actual frozen-publication MACE execution "
                f"could not run on this host ({exc}); deferred to target-machine qualification."
            )
        assert np.isfinite(energy)
        assert forces.shape == (len(atoms), 3)
    finally:
        store.close()


def test_r12b9_missing_required_reference_stress_fails_closed(tmp_path: Path):
    """Requiring stress the references cannot supply is a contradiction."""

    from mdstats.training_data.qualification.stress_capability import (
        StressCapabilityDecision,
    )

    # The product has a stress channel and policy requires it, but the reference
    # side has no stress labels: the comparison cannot be made, and the decision
    # records that rather than quietly comparing nothing.
    decision = StressCapabilityDecision(
        training_objective_weights_stress=True,
        reference_labels_available=False,
        model_reports_stress=True,
        fully_periodic=True,
        runtime_reports_stress=True,
        policy_requires_stress=True,
        policy_declared_inapplicable_reason=None,
        reason_codes=("reference_frames_carry_no_stress_labels",),
    )
    assert decision.required is True
    assert decision.reference_comparable is False
    assert "reference_frames_carry_no_stress_labels" in decision.reason_codes

    # And a runtime that cannot report stress cannot be compared through
    # deployment even when the product itself has the channel.
    import dataclasses

    blind_runtime = dataclasses.replace(decision, runtime_reports_stress=False)
    assert blind_runtime.deployed_comparable is False
    assert blind_runtime.content_digest != decision.content_digest


def test_r12b7_concurrency_changes_cost_but_not_scientific_evidence(tmp_path: Path):
    """Observations may differ with execution cost; the evidence may not."""

    from mdstats.training_data.qualification.resource_observation import (
        QualificationResourceObservation,
    )

    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    serial = _current(config, harness)

    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        position = session.attempt_root / "components" / COMPONENT_DYNAMICS
        for entry in position.glob("*.json"):
            entry.unlink()
        (session.attempt_root / "components" / f"{COMPONENT_DYNAMICS}.json").unlink()
        serial_dynamics = session.completed_component(
            COMPONENT_DYNAMICS,
            session.component_input_digest(
                COMPONENT_DYNAMICS, session.authenticated_reference_bundle()
            ),
        )
        assert serial_dynamics is None
    finally:
        store.close()

    concurrent = fx.QualificationHarness()
    fx.attach_labels(concurrent, config)
    assert (
        fx.run_qualification_command(config, "run", harness=concurrent, case_workers=4)
        == 0
    )
    parallel = _current(config, concurrent)

    # Same science.
    assert parallel.components == serial.components
    assert parallel.verdict is serial.verdict
    # Different, truthful cost records under the same attempt.
    _cfg, _paths, store, session = fx.load_session(config, concurrent)
    try:
        first = session.store.get(
            serial.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        )
        second = session.store.get(
            parallel.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        )
        assert first.attempt_identity == second.attempt_identity
        assert first.content_digest != second.content_digest
        assert second.is_measured
    finally:
        store.close()
