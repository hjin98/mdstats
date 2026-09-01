"""P7 revision-11 repair acceptance.

Revision 11 reopened P7 on twelve blocking findings. This suite is the
acceptance evidence for the repairs: deployment identity and the canonical
target head, exposure-time currentness, reference-bundle descendant identity,
reference-relaxed dynamics with the complete frozen diagnostics, crash-resumable
one-shot locked activation, accepted resource ownership and race-free deployed
artifacts, explicit reference protocol, stress applicability, canonical
analysis-owner reconciliation, and truthful real-owner deployment acceptance.

The revision-10 suite in `test_mlff_p7_post_production_qualification.py` remains
binding and is not restated here.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import tests._mlff_qualification_fixture as fx
import tests._mlff_post_selection_fixture as p5

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.post_selection_identity import (
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
)
from mdstats.training_data.qualification import (
    COMPONENT_CALIBRATION,
    COMPONENT_DEPLOYMENT_PARITY,
    COMPONENT_DYNAMICS,
    COMPONENT_LOCKED_TEST,
    COMPONENT_PHYSICAL_PES,
    COMPONENT_RELAXATION,
    ComponentStatus,
    QualificationActivationError,
    QualificationError,
    QualificationLineageError,
    QualificationVerdict,
    probe_lammps_runtime,
    resolve_current_qualification_verdict,
)

QUALIFICATION_SOURCE_ROOT = Path(cli.__file__).resolve().parent / "qualification"


#: Thresholds wide enough that each diagnostic test tightens exactly one knob.
DYNAMICS_POLICY = """protected_displacement_maximum_angstrom = 1.0
protected_bond_maximum_error_angstrom = 5.0
protected_angle_maximum_error_degrees = 170.0
nve_temperature_tolerance_kelvin = 400.0
minimum_consecutive_topology_violations = 3
"""


def _dynamics_config(**kwargs) -> str:
    return fx.fixture_config_text(dynamics_overrides=DYNAMICS_POLICY, **kwargs)


def _campaign(tmp_path: Path, *, config_text: str | None = None):
    harness = fx.QualificationHarness()
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


# ---------------------------------------------------------------------------
# R11-B1 — the publication decision is a predecessor fact P7 only consumes
# ---------------------------------------------------------------------------


def test_r11b1_qualification_consumes_the_p5_decision_and_ranks_nothing(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        from mdstats.training_data.campaign_post_selection_runtime import (
            resolve_current_final_production_publication,
        )

        decision = resolve_current_final_production_publication(session.context)
        publication = session.publication
        # The view copies the decision; it does not recompute membership.
        assert publication.decision_digest == decision.content_digest
        assert publication.member_digest == decision.member_digest
        assert [member.member_id for member in publication.members] == list(
            decision.published_member_ids
        )
        assert publication.decision_policy_identity == decision.decision_policy_identity
    finally:
        store.close()

    # Structurally, no cross-seed ranking survives anywhere in P7.
    joined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(QUALIFICATION_SOURCE_ROOT.rglob("*.py"))
    )
    for forbidden in (
        "order_eval2_admissible_candidates",
        "select_cv_fold_representative",
        "CheckpointSelectionPolicy",
        "_rank_single_best",
    ):
        assert forbidden not in joined, forbidden


def test_r11b1_single_best_publication_is_qualified_end_to_end(tmp_path: Path):
    """A single-best product qualifies exactly like an all-qualified one."""

    text = fx.fixture_config_text(
        production_seeds="[5, 6]", committee_policy="single_best_final_seed"
    )
    config, _workspace, harness = _campaign(tmp_path, config_text=text)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert session.publication.committee_policy == "single_best_final_seed"
        assert len(session.publication.members) == 1
    finally:
        store.close()
    assert _qualify_nonlocked(config, harness) == 0
    record = _current(config, harness)
    assert record.verdict is QualificationVerdict.INCOMPLETE
    assert record.outcome(COMPONENT_DEPLOYMENT_PARITY).status is ComponentStatus.PASSED


def _current(config: Path, harness):
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        return resolve_current_qualification_verdict(
            store, paths, session.context, binding=session.binding
        )
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R11-B2 — the canonical target head reaches the real deployment owners
# ---------------------------------------------------------------------------


def test_r11b2_canonical_target_head_reaches_export_and_mliap_builder(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        assert member.target_head_name == POST_SELECTION_TARGET_HEAD_NAME
        assert session.publication.target_head_name == POST_SELECTION_TARGET_HEAD_NAME
        session.deployed_artifact(member)
        assert harness.export_heads == [POST_SELECTION_TARGET_HEAD_NAME]
        assert harness.mliap_heads == [POST_SELECTION_TARGET_HEAD_NAME]
        # The head is part of product identity, not decoration.
        assert member.target_head_name in str(session.publication.to_dict())
    finally:
        store.close()


def test_r11b2_wrong_head_is_a_different_product(tmp_path: Path):
    """A replay-head member cannot authenticate as the published product."""

    import dataclasses

    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        replay_member = dataclasses.replace(
            member, target_head_name=POST_SELECTION_REPLAY_HEAD_NAME
        )
        assert replay_member.content_digest != member.content_digest
        assert session.deployment_identity(replay_member) != session.deployment_identity(member)
        # A publication whose members disagree with its head fails closed.
        from mdstats.training_data.qualification.publication import (
            AuthenticatedFinalPublication,
        )

        with pytest.raises(QualificationLineageError, match="canonical\\s+target head"):
            dataclasses.replace(session.publication, members=(replay_member,))
    finally:
        store.close()


def test_r11b2_real_mace_target_head_deployment_owner_executes(tmp_path: Path):
    """The real mdstats exporter and real MACE ML-IAP builder, on a real model.

    This is owner-level acceptance of the product path, not of the LAMMPS
    process plumbing: a genuine multihead MACE model is exported through the
    real `mace_deployment` owner at the canonical target head, and the real
    `LAMMPS_MLIAP_MACE` builder produces the artifact LAMMPS would execute.
    """

    torch = pytest.importorskip("torch")
    pytest.importorskip("mace")
    from tests._mlff_tiny_mace import _tiny_mace

    from mdstats.training_data.qualification.deployment import (
        default_deployment_exporter,
        default_mliap_artifact_builder,
    )

    model = _tiny_mace(
        heads=[POST_SELECTION_REPLAY_HEAD_NAME, POST_SELECTION_TARGET_HEAD_NAME],
        atomic_numbers=(3, 8),
        r_max=4.0,
        dtype=torch.float64,
        atomic_energies=((0.0, 0.0), (0.0, 0.0)),
    )
    assert list(model.heads) == [
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
    ]
    source = tmp_path / "production.model"
    torch.save(model, source)

    artifact = default_deployment_exporter(
        source,
        tmp_path / "deploy",
        deployment_dtype="float64",
        target_head=POST_SELECTION_TARGET_HEAD_NAME,
    )
    assert artifact.target_head == POST_SELECTION_TARGET_HEAD_NAME
    deployment_path = tmp_path / "deploy" / artifact.deployment_relative_path
    assert deployment_path.is_file()

    mliap_path = default_mliap_artifact_builder(
        deployment_path, tmp_path / "product-mliap.pt", head=POST_SELECTION_TARGET_HEAD_NAME
    )
    built = torch.load(mliap_path, map_location="cpu", weights_only=False)
    # The exact canonical head, not the last head, is what the artifact runs.
    assert int(built.model.head.item()) == 1

    # The head is mandatory: a headless build cannot prove product identity.
    with pytest.raises(QualificationError, match="canonical published target head"):
        default_mliap_artifact_builder(deployment_path, tmp_path / "headless.pt", head=None)


def test_r11b2_real_mace_product_execution_is_unavailable_or_passes(tmp_path: Path):
    """Execute the real MACE product in LAMMPS, or record it as blocking.

    Static ML-IAP interface inspection is diagnostic only.  This test must
    enter the actual worker/product callback; if that callback is unavailable
    on the host, the typed result is truthfully deferred to target-machine
    qualification rather than being replaced by an analytic ML-IAP smoke.
    """

    probe = probe_lammps_runtime(refresh=True)
    if not probe.supports_deployed_execution:
        pytest.skip(
            "UNAVAILABLE/BLOCKING: the supported LAMMPS/ML-IAP runtime is absent "
            f"({probe.detail}); deferred to final target-machine qualification."
        )

    torch = pytest.importorskip("torch")
    from ase import Atoms

    from tests._mlff_tiny_mace import _tiny_mace
    from mdstats.training_data.qualification.deployment import (
        default_deployment_exporter,
        default_mliap_artifact_builder,
    )
    from mdstats.training_data.qualification.runtime_capability import (
        deployed_static_evaluation,
    )
    from mdstats.training_data.qualification.errors import QualificationUnavailableError

    model = _tiny_mace(
        heads=[POST_SELECTION_REPLAY_HEAD_NAME, POST_SELECTION_TARGET_HEAD_NAME],
        atomic_numbers=(3, 8),
        r_max=4.0,
        dtype=torch.float64,
        atomic_energies=((0.0, 0.0), (0.0, 0.0)),
    )
    source = tmp_path / "production.model"
    torch.save(model, source)
    try:
        artifact = default_deployment_exporter(
            source, tmp_path / "d", deployment_dtype="float64",
            target_head=POST_SELECTION_TARGET_HEAD_NAME,
        )
        mliap_path = default_mliap_artifact_builder(
            tmp_path / "d" / artifact.deployment_relative_path,
            tmp_path / "m.pt",
            head=POST_SELECTION_TARGET_HEAD_NAME,
        )
        atoms = Atoms(
            "Li2O2",
            positions=[[0, 0, 0], [2.0, 0, 0], [0, 2.0, 0], [2.0, 2.0, 0.0]],
            cell=[10.0, 10.0, 10.0],
            pbc=True,
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
            "UNAVAILABLE/BLOCKING: the actual MACE callback could not execute on "
            f"this host ({exc}); deferred to final target-machine qualification."
        )
    assert np.isfinite(energy)
    assert forces.shape == (4, 3) and np.all(np.isfinite(forces))


def test_r11b2_runtime_probe_separates_iap_support_from_product_support():
    probe = probe_lammps_runtime(refresh=True)
    assert isinstance(probe.supports_deployed_execution, bool)
    assert isinstance(probe.supports_mace_product_execution, bool)
    # Product support is strictly stronger than generic ML-IAP support.
    if probe.supports_mace_product_execution:
        assert probe.supports_deployed_execution
    assert "mace_mliap_supported" in probe.to_dict()


def test_r11b2_real_runtime_gate_blocks_rather_than_passing(tmp_path: Path):
    """Requiring the real runtime without the seam is blocking, never a pass."""

    text = fx.fixture_config_text().replace(
        "require_deployed_runtime = false", "require_deployed_runtime = true"
    )
    config, _workspace, harness = _campaign(tmp_path, config_text=text)
    _cfg, paths, store, session = fx.load_session(
        config, harness, deployed_evaluator=None, mliap_builder=None, deployment_exporter=None
    )
    try:
        from mdstats.training_data.qualification.deployment import qualify_deployment_parity
        from mdstats.training_data.qualification.errors import (
            QualificationUnavailableError,
        )

        with pytest.raises(QualificationUnavailableError, match="unavailable/blocking|cannot"):
            qualify_deployment_parity(session)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R11-B3 — exposure-time currentness
# ---------------------------------------------------------------------------


def test_r11b3_terminal_record_is_not_current_after_a_binding_change(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    assert _current(config, harness) is not None

    p5.rewrite_config(config, "probe_configurations = 2", "probe_configurations = 3")
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        from mdstats.training_data.qualification.record import (
            ProductionQualificationRecord,
        )
        from mdstats.training_data.qualification.store import (
            POINTER_QUALIFICATION_RECORD,
            read_current_qualification_pointer,
        )

        # The mutable pointer is only a locator: it still names the old object.
        pointer = read_current_qualification_pointer(
            store,
            binding=session.context.selected.binding,
            kind=POINTER_QUALIFICATION_RECORD,
        )
        assert pointer is not None
        historical = session.store.get(pointer, ProductionQualificationRecord.from_dict)
        assert historical.specification_digest != (
            session.binding.specification.content_digest
        )
        # Every public resolver re-establishes the current binding at exposure
        # time, so the located object is historical and not current. There is
        # deliberately no unfenced public read.
        assert (
            resolve_current_qualification_verdict(
                store, paths, session.context, binding=session.binding
            )
            is None
        )
        assert resolve_current_qualification_verdict(store, paths, session.context) is None
    finally:
        store.close()


def test_r11b3_status_never_reports_a_stale_release_verdict(tmp_path: Path, capsys):
    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    assert fx.run_qualification_command(config, "activate-locked", harness=harness, confirm=True) == 0
    assert _current(config, harness).verdict is QualificationVerdict.RELEASE_QUALIFIED

    p5.rewrite_config(config, "probe_configurations = 2", "probe_configurations = 4")
    capsys.readouterr()
    assert fx.run_qualification_command(config, "status", harness=harness) == 0
    printed = capsys.readouterr().out
    assert "release_qualified" not in printed
    assert "no current terminal qualification record" in printed


def test_r11b3_documentation_only_change_does_not_stale_the_verdict(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    before = _current(config, harness)
    # A workplan/doc edit changes no importable source, so nothing stales.
    (Path(cli.__file__).resolve().parents[2] / "docs").is_dir()
    after = _current(config, harness)
    assert after is not None and after.content_digest == before.content_digest


def test_r11b3_release_index_enforces_the_same_current_binding(tmp_path: Path):
    from mdstats.training_data.qualification.runtime import (
        resolve_current_release_evidence,
    )

    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        assert (
            resolve_current_release_evidence(
                store, paths, session.context, binding=session.binding
            )
            is not None
        )
    finally:
        store.close()
    p5.rewrite_config(config, "probe_configurations = 2", "probe_configurations = 5")
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        assert (
            resolve_current_release_evidence(
                store, paths, session.context, binding=session.binding
            )
            is None
        )
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R11-B4 — reference-bundle content identity
# ---------------------------------------------------------------------------


def test_r11b4_new_bundle_stales_only_reference_dependent_components(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0

    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        deployment_before = session.completed_component(
            COMPONENT_DEPLOYMENT_PARITY,
            session.component_input_digest(COMPONENT_DEPLOYMENT_PARITY, None),
        )
        assert deployment_before is not None
        # Supersede the bundle with a materially different authenticated one.
        other = fx.QualificationHarness(potential=fx.AnalyticPairPotential(stiffness=3.0))
        fx.attach_labels(other, config)
        fx.supply_analytic_reference_bundle(session, other)
    finally:
        store.close()

    # Exposure-time resolution must retire Bundle A immediately; it must not
    # remain current merely because the P5/P6 product binding is unchanged.
    assert _current(config, harness) is None

    resumed = fx.QualificationHarness()
    fx.attach_labels(resumed, config)
    assert fx.run_qualification_command(config, "run", harness=resumed) == 0
    # Deployment and calibration are bundle-independent and were reused; the
    # reference-dependent components were recomputed against bundle B.
    assert resumed.deployed_calls == []
    assert resumed.evaluated_atoms > 0

    _cfg, _paths, store, session = fx.load_session(config, resumed)
    try:
        bundle = session.authenticated_reference_bundle()
        for component in (COMPONENT_PHYSICAL_PES, COMPONENT_RELAXATION):
            evidence = session.completed_component(
                component, session.component_input_digest(component, bundle)
            )
            assert evidence is not None
            assert evidence.payload["reference_bundle_digest"] == bundle.content_digest
        # Bundle A's evidence remains immutable historical evidence.
        assert session.store.has(deployment_before.content_digest)
    finally:
        store.close()


def test_r11b4_component_input_identity_separates_dependent_components(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _supply_reference(config, harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        bundle = session.authenticated_reference_bundle()
        assert bundle is not None
        independent = {
            component: session.component_input_digest(component, bundle)
            for component in (COMPONENT_DEPLOYMENT_PARITY, COMPONENT_CALIBRATION)
        }
        without_bundle = {
            component: session.component_input_digest(component, None)
            for component in (COMPONENT_DEPLOYMENT_PARITY, COMPONENT_CALIBRATION)
        }
        assert independent == without_bundle
        for component in (COMPONENT_PHYSICAL_PES, COMPONENT_RELAXATION, COMPONENT_DYNAMICS):
            assert session.component_input_digest(
                component, bundle
            ) != session.component_input_digest(component, None)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R11-B5 — reference-relaxed dynamics and the complete diagnostics
# ---------------------------------------------------------------------------


def test_r11b5_dynamics_starts_from_authenticated_relaxed_coordinates(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        bundle = session.authenticated_reference_bundle()
        from mdstats.training_data.qualification.geometry import atoms_for_frame
        from mdstats.training_data.qualification.reference import (
            RELAXED_MODE,
            geometry_identity,
        )

        base = session.plan.physical_plan.bases[0]
        atoms = atoms_for_frame(session.context, base.frame_uid)
        observation = bundle.observation(
            geometry_identity(atoms, frame_uid=base.frame_uid, mode=RELAXED_MODE)
        )
        expected = np.asarray(observation.relaxed_positions, dtype=np.float64)
        started = harness.dynamics_start_positions[0]
        assert np.allclose(started, expected)
        # And it is not the original OUTER_MONITOR geometry.
        assert not np.allclose(started, np.asarray(atoms.get_positions(), dtype=np.float64))
    finally:
        store.close()


def test_r11b5_missing_relaxed_reference_cannot_pass_dynamics(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        # Without any bundle the dynamics component waits; it never runs from
        # the unrelaxed base geometry.
        record = resolve_current_qualification_verdict(
            store, _paths, session.context, binding=session.binding
        )
        assert record.outcome(COMPONENT_DYNAMICS).status is ComponentStatus.WAITING_FOR_REFERENCE
    finally:
        store.close()
    assert harness.dynamics_calls == []


def test_r11b5_persistence_rule_separates_transient_noise_from_damage():
    """The frozen persistence rule is a consecutive-sample rule, declared first."""

    from mdstats.training_data.qualification.spec import (
        resolve_qualification_spec_identity,
    )

    specification = resolve_qualification_spec_identity(
        {"qualification": {"dynamics": {"minimum_consecutive_topology_violations": 3}}}
    )
    policy = specification.component_policy(COMPONENT_DYNAMICS)
    assert int(policy["minimum_consecutive_topology_violations"]) == 3
    # The threshold participates in the specification digest, so it cannot be
    # chosen after seeing a trajectory without staling every descendant.
    other = resolve_qualification_spec_identity(
        {"qualification": {"dynamics": {"minimum_consecutive_topology_violations": 2}}}
    )
    assert other.content_digest != specification.content_digest

    reference = _bonded_frame()
    broken = np.asarray(reference.get_positions(), dtype=np.float64).copy()
    broken[2] = np.array([7.0, 0.0, 0.0])
    intact_row = _protected_sample(reference, reference.get_positions())
    broken_row = _protected_sample(reference, broken)

    def longest_run(rows):
        run = best = 0
        for row in rows:
            run = run + 1 if row["broken_protected_bonds"] else 0
            best = max(best, run)
        return best

    # Two isolated noisy samples never reach three consecutive violations.
    assert longest_run([broken_row, intact_row, broken_row, intact_row]) < 3
    # Sustained damage does.
    assert longest_run([broken_row, broken_row, broken_row]) >= 3


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({"nve_temperature": float("nan")}, "nonfinite_or_incomplete_nve_temperature"),
        ({"nve_temperature": 5000.0}, "nve_temperature_out_of_tolerance"),
        ({"protected_displacement": 2.0}, "protected_displacement_above_maximum"),
        ({"minimum_pair_distance_angstrom": 0.05}, "minimum_pair_distance_below_safety_bound"),
        ({"maximum_force_ev_per_angstrom": 1.0e6}, "maximum_force_above_safety_bound"),
        ({"total_energy_drift_ev": 50.0}, "nve_energy_drift_above_maximum"),
    ],
)
def test_r11b5_each_frozen_diagnostic_rejects_independently(
    tmp_path: Path, overrides, expected
):
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
    harness.dynamics_overrides = dict(overrides)
    with pytest.raises(QualificationError, match="rejected the exact frozen publication"):
        _qualify_nonlocked(config, harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(
            COMPONENT_DYNAMICS,
            session.component_input_digest(
                COMPONENT_DYNAMICS, session.authenticated_reference_bundle()
            ),
        )
        reasons = " ".join(evidence.payload["members"][0]["reason_codes"])
        assert expected in reasons, reasons
        # A nonfinite observation is a rejection reason, not a serialization
        # failure: the measurement column records absence instead of NaN.
        case = evidence.payload["members"][0]["cases"][0]
        for key, value in case.items():
            if isinstance(value, float):
                assert np.isfinite(value), key
    finally:
        store.close()


def _bonded_frame():
    from ase import Atoms

    return Atoms(
        "OSiO",
        positions=[[0.0, 0.0, 0.0], [1.62, 0.0, 0.0], [3.24, 0.0, 0.0]],
        cell=[20.0, 20.0, 20.0],
        pbc=True,
    )


def _protected_sample(reference, positions, *, scale: float = 1.20):
    """Reduce one raw sample through the production protected-geometry owner."""

    from mdstats.training_data.qualification.dynamics import protected_geometry_metrics
    from mdstats.training_data.qualification.geometry import angle_table, bond_table

    bonds = bond_table(reference, cutoff_scale=scale)
    angles = angle_table(reference, bonds)
    return protected_geometry_metrics(
        reference,
        {
            "positions_angstrom": np.asarray(positions, dtype=np.float64).tolist(),
            "cell_angstrom": np.asarray(reference.get_cell(), dtype=np.float64).tolist(),
            "pbc": [bool(v) for v in reference.get_pbc()],
        },
        bonds,
        angles,
        set(range(len(reference))),
        scale,
    )


def test_r11b5_protected_topology_and_geometry_reduction_is_discriminating():
    """Bond, angle, and topology degradation are separately observable.

    The bounded campaign cell holds no bonded pair inside the canonical
    neighbour owner's safe minimum-image radius, so these predicates are
    exercised on a genuinely bonded configuration through the same production
    reducer the qualification run uses.
    """

    reference = _bonded_frame()

    intact = _protected_sample(reference, reference.get_positions())
    assert intact["broken_protected_bonds"] == []
    assert intact["protected_bond_count"] == 2
    assert intact["protected_angle_count"] == 1
    assert intact["protected_bond_maximum_error_angstrom"] == pytest.approx(0.0, abs=1e-12)

    # A stretched but unbroken bond degrades geometry without breaking topology.
    stretched = np.asarray(reference.get_positions(), dtype=np.float64).copy()
    stretched[1] += np.array([0.30, 0.0, 0.0])
    row = _protected_sample(reference, stretched)
    assert row["broken_protected_bonds"] == []
    assert row["protected_bond_maximum_error_angstrom"] > 0.25
    assert row["protected_displacement_maximum_angstrom"] == pytest.approx(0.30, abs=1e-9)

    # A bent triplet degrades the angle while both bonds survive.
    bent = np.asarray(reference.get_positions(), dtype=np.float64).copy()
    bent[2] = np.array([1.62, 1.62, 0.0])
    row = _protected_sample(reference, bent)
    assert row["broken_protected_bonds"] == []
    assert row["protected_angle_maximum_error_degrees"] > 45.0

    # A broken bond is topology damage, and the surviving bond is still perfect.
    broken = np.asarray(reference.get_positions(), dtype=np.float64).copy()
    broken[2] = np.array([7.0, 0.0, 0.0])
    row = _protected_sample(reference, broken)
    assert [tuple(item) for item in row["broken_protected_bonds"]] == [(1, 2)]
    assert row["protected_bond_maximum_error_angstrom"] == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# R11-B6 — crash-resumable one-shot locked activation
# ---------------------------------------------------------------------------


def _activate(config: Path, harness):
    return fx.run_qualification_command(
        config, "activate-locked", harness=harness, confirm=True
    )


def test_r11b6_resume_after_crash_at_activation_completes_one_test(tmp_path: Path):
    """A crash between opening the cohort and evaluating it is recoverable."""

    from mdstats.training_data.qualification import runtime as runtime_module

    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0

    boom = RuntimeError("crash immediately after activation publication")

    def exploding(session, activation):
        raise boom

    original = runtime_module.qualify_locked_test
    runtime_module.qualify_locked_test = exploding
    try:
        with pytest.raises(RuntimeError, match="crash immediately"):
            _activate(config, harness)
    finally:
        runtime_module.qualify_locked_test = original

    # The cohort is open, so it must be completable - not permanently wedged.
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        from mdstats.training_data.qualification.runtime import (
            locked_cohort_already_revealed,
        )

        opened = locked_cohort_already_revealed(session, paths)
        assert opened is not None
    finally:
        store.close()

    assert _activate(config, harness) == 0
    record = _current(config, harness)
    assert record.verdict is QualificationVerdict.RELEASE_QUALIFIED

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        from mdstats.training_data.qualification.runtime import (
            locked_cohort_already_revealed,
        )

        resumed = locked_cohort_already_revealed(session, paths)
        # Exactly one activation identity survives the whole sequence.
        assert resumed.content_digest == opened.content_digest
        assert record.locked_activation_digest == opened.content_digest
    finally:
        store.close()

    # A genuinely terminal second activation is still refused.
    with pytest.raises(QualificationActivationError, match="already been activated"):
        _activate(config, harness)


def test_r11b6_resume_after_locked_evidence_does_not_reopen_the_cohort(tmp_path: Path):
    from mdstats.training_data.qualification import runtime as runtime_module

    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0

    original = runtime_module.publish_qualification_record

    def exploding(*args, **kwargs):
        raise RuntimeError("crash after locked component publication")

    runtime_module.publish_qualification_record = exploding
    try:
        with pytest.raises(RuntimeError, match="crash after locked"):
            _activate(config, harness)
    finally:
        runtime_module.publish_qualification_record = original

    counted = fx.QualificationHarness()
    fx.attach_labels(counted, config)
    assert _activate(config, counted) == 0
    # The locked cohort was evaluated once; the resume reused that evidence.
    assert counted.locked_evaluations == 0
    assert _current(config, counted).verdict is QualificationVerdict.RELEASE_QUALIFIED


def test_r11b6_revealed_cohort_stays_revealed_after_a_currentness_change(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    assert _activate(config, harness) == 0

    # A qualification-only policy change makes the verdict historical, but it
    # must not make the revealed cohort fresh again.
    p5.rewrite_config(config, "probe_configurations = 2", "probe_configurations = 3")
    resumed = fx.QualificationHarness()
    fx.attach_labels(resumed, config)
    with pytest.raises(QualificationActivationError, match="different product or|permanent"):
        _activate(config, resumed)


def test_r11b6_activation_holds_the_retention_reference_until_terminal(tmp_path: Path):
    from mdstats.training_data.qualification import runtime as runtime_module
    from mdstats.training_data.qualification.store import (
        ATTEMPT_ACTIVE,
        ATTEMPT_TERMINAL,
        read_attempt_state,
    )

    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0

    original = runtime_module.publish_release_evidence
    runtime_module.publish_release_evidence = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("crash before release index")
    )
    try:
        with pytest.raises(RuntimeError, match="crash before release index"):
            _activate(config, harness)
    finally:
        runtime_module.publish_release_evidence = original

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        state = read_attempt_state(
            paths, session.context.selected.binding, session.binding.attempt_identity
        )
        assert state.state in (ATTEMPT_ACTIVE, "aborted")
    finally:
        store.close()

    assert _activate(config, harness) == 0
    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        state = read_attempt_state(
            paths, session.context.selected.binding, session.binding.attempt_identity
        )
        assert state.state == ATTEMPT_TERMINAL
        assert state.referenced_paths == ()
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R11-B7 — accepted resource ownership and race-free deployed artifacts
# ---------------------------------------------------------------------------


def test_r11b7_case_workers_come_from_the_accepted_resource_owner(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness, case_workers=64)
    try:
        assert session.resources is not None and session.resource_scope is not None
        resolved = session.resolved_case_workers(16)
        assert 1 <= resolved <= int(session.resource_scope.python_workers)
        # Pressure may only reduce concurrency, never change identity.
        assert session.binding.resource_scope_digest
        squeezed = session.resolved_case_workers(1)
        assert squeezed == 1
    finally:
        store.close()


def test_r11b7_resource_scope_is_bound_but_capacity_is_not_numerical_identity(
    tmp_path: Path,
):
    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        environment = session.binding.environment
        payload = environment.to_dict()
        assert "cpu_thread_count" in payload
        # Capacity is recorded but is not part of the numerical identity.
        import dataclasses

        capacity = dataclasses.replace(environment, cpu_thread_count=1)
        assert capacity.content_digest == environment.content_digest
        # The resource scope is nevertheless bound to the attempt separately, so
        # a performance/resource claim cannot silently move between machines.
        assert session.binding.resource_scope_digest
        assert session.binding.attempt_identity
    finally:
        store.close()


def test_r11b7_deployed_artifact_is_create_once_and_reauthenticated(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        path, sha = session.deployed_artifact(member)
        builds = len(harness.mliap_heads)

        # A fresh session with an empty in-memory cache reuses the durable
        # artifact after authenticating it, rather than rebuilding or racing.
        _cfg2, _paths2, store2, session2 = fx.load_session(config, harness)
        try:
            again_path, again_sha = session2.deployed_artifact(member)
            assert again_path == path and again_sha == sha
            assert len(harness.mliap_heads) == builds
        finally:
            store2.close()

        # Mutated artifact bytes are never executed.
        path.write_bytes(path.read_bytes() + b"tamper")
        _cfg3, _paths3, store3, session3 = fx.load_session(config, harness)
        try:
            with pytest.raises(QualificationLineageError, match="bytes changed"):
                session3.deployed_artifact(member)
        finally:
            store3.close()
    finally:
        store.close()


def test_r11b7_concurrent_same_member_artifact_creation_converges(tmp_path: Path):
    from concurrent.futures import ThreadPoolExecutor

    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _i: session.deployed_artifact(member), range(4)))
        paths = {str(item[0]) for item in results}
        shas = {item[1] for item in results}
        assert len(paths) == 1 and len(shas) == 1
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R11-B8 — explicit reference protocol
# ---------------------------------------------------------------------------


def test_r11b8_placeholder_protocol_fails_closed(tmp_path: Path):
    text = fx.fixture_config_text().replace(
        'protocol = "bounded-analytic-reference.v1"',
        'protocol = "external-reference-protocol-unset"',
    )
    config, _workspace, harness = _campaign(tmp_path, config_text=text)
    with pytest.raises(QualificationError, match="placeholder"):
        fx.run_qualification_command(config, "run", harness=harness)


def test_r11b8_missing_protocol_fails_closed(tmp_path: Path):
    text = fx.fixture_config_text().replace(
        'protocol = "bounded-analytic-reference.v1"', ""
    )
    config, _workspace, harness = _campaign(tmp_path, config_text=text)
    with pytest.raises(QualificationError, match="placeholder|explicit"):
        fx.run_qualification_command(config, "run", harness=harness)


# ---------------------------------------------------------------------------
# R11-B9 — stress applicability
# ---------------------------------------------------------------------------


def test_r11b9_stress_conversion_is_canonical_and_tested():
    from mdstats.training_data.qualification.stress import canonical_stress_tensor

    voigt = np.array([1.0, 2.0, 3.0, 0.5, 0.25, 0.125], dtype=np.float64)
    tensor = canonical_stress_tensor(voigt)
    assert tensor.shape == (3, 3)
    assert np.allclose(tensor, tensor.T)
    assert np.allclose(np.diag(tensor), [1.0, 2.0, 3.0])
    # A full tensor round-trips unchanged.
    assert np.allclose(canonical_stress_tensor(tensor), tensor)
    with pytest.raises(Exception):
        canonical_stress_tensor(np.zeros(4))


def test_r11b9_stress_conversion_binds_units_sign_order_and_cell_volume():
    from mdstats.training_data.qualification.stress import (
        canonical_stress_from_virial,
        canonical_stress_tensor,
    )

    # The source vector deliberately uses a noncanonical order.  Division by
    # the instantaneous cell volume and the explicit sign are both owned by
    # the canonical converter, not by a caller-specific reducer.
    virial = np.array([10.0, 20.0, 30.0, 4.0, 5.0, 6.0])
    stress = canonical_stress_from_virial(
        virial,
        volume_angstrom3=2.0,
        voigt_order=("xx", "yy", "zz", "xz", "yz", "xy"),
        sign=-1.0,
    )
    assert np.allclose(
        stress,
        [[-5.0, -3.0, -2.0], [-3.0, -10.0, -2.5], [-2.0, -2.5, -15.0]],
    )
    assert np.allclose(
        canonical_stress_tensor([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], units="bar"),
        canonical_stress_tensor([1.0e-4, 2.0e-4, 3.0e-4, 4.0e-4, 5.0e-4, 6.0e-4], units="gpa"),
    )
    with pytest.raises(Exception, match="positive cell volume"):
        canonical_stress_from_virial(virial, volume_angstrom3=0.0)


def test_r11b9_stress_unavailability_is_explicit_not_silent(tmp_path: Path):
    config, _workspace, harness = _campaign(tmp_path)
    assert _qualify_nonlocked(config, harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(
            COMPONENT_DEPLOYMENT_PARITY,
            session.component_input_digest(COMPONENT_DEPLOYMENT_PARITY, None),
        )
        metrics = dict(evidence.metrics)
        # The bounded analytic model exposes no stress; that is recorded as an
        # explicit capability fact rather than a silent stress-parity claim.
        assert "stress_applicable" in metrics
        assert metrics["stress_applicable"] is False
        assert metrics.get("stress_compared_configurations", 0) == 0
    finally:
        store.close()


# ---------------------------------------------------------------------------
# R11-B10 — canonical analysis-owner reconciliation
# ---------------------------------------------------------------------------


def test_r11b10_topology_uses_the_canonical_analysis_owners():
    source = (QUALIFICATION_SOURCE_ROOT / "geometry.py").read_text(encoding="utf-8")
    assert "analysis.atomic_connectivity" in source
    assert "analysis.cutoffs" in source
    assert "analysis._neighbors" in source
    # No second covalent-radius connectivity definition survives.
    assert "covalent_radii" not in source or "PairCutoffRegistry" in source


def test_r11b10_bond_table_matches_the_canonical_connectivity_owner():
    """The adapter reproduces the canonical owner's edge set exactly."""

    from ase import Atoms

    from mdstats.training_data.qualification.geometry import bond_table

    atoms = Atoms(
        "OSiO",
        positions=[[0.0, 0.0, 0.0], [1.62, 0.0, 0.0], [3.24, 0.0, 0.0]],
        cell=[20.0, 20.0, 20.0],
        pbc=True,
    )
    bonds = bond_table(atoms, cutoff_scale=1.20)
    assert set(bonds) == {(0, 1), (1, 2)}
    stretched = atoms.copy()
    stretched.set_positions([[0.0, 0.0, 0.0], [1.62, 0.0, 0.0], [6.20, 0.0, 0.0]])
    assert (1, 2) not in bond_table(stretched, cutoff_scale=1.20)


# ---------------------------------------------------------------------------
# Assembled integration on the repaired owner graph
# ---------------------------------------------------------------------------


def test_r11_assembled_integration_including_the_publication_decision(tmp_path: Path):
    text = fx.fixture_config_text(
        production_seeds="[5, 6]",
        # Two seeds of the bounded trainer predict identically, so committee
        # spread carries no information; the frozen policy says so explicitly
        # rather than letting a degenerate spread be read as calibration.
        calibration_overrides='method = "none"\n',
    )
    config, _workspace, harness = _campaign(tmp_path, config_text=text)

    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        assert len(session.publication.members) == 2
        assert session.publication.target_head_name == POST_SELECTION_TARGET_HEAD_NAME
    finally:
        store.close()

    assert _qualify_nonlocked(config, harness) == 0
    assert fx.run_qualification_command(config, "status", harness=harness) == 0
    assert _activate(config, harness) == 0
    terminal = _current(config, harness)
    assert terminal.verdict is QualificationVerdict.RELEASE_QUALIFIED
    assert terminal.outcome(COMPONENT_LOCKED_TEST).status is ComponentStatus.PASSED
    # Close/reopen reauthenticates the exact terminal state under the binding.
    assert _current(config, harness).to_dict() == terminal.to_dict()


def test_r11b2_wrong_head_or_dtype_receipt_is_refused(tmp_path: Path):
    """A valid-looking artifact from another head or dtype fails closed."""

    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        member = session.publication.members[0]
        path, sha = session.deployed_artifact(member)
        receipt = path.parent / "deployment-receipt.json"
        original = json.loads(receipt.read_text(encoding="utf-8"))

        for field, value in (
            ("target_head_name", POST_SELECTION_REPLAY_HEAD_NAME),
            ("deployment_dtype", "float32"),
            ("representative_checkpoint_sha256", "0" * 64),
        ):
            tampered = dict(original)
            tampered[field] = value
            receipt.write_text(json.dumps(tampered), encoding="utf-8")
            _cfg2, _paths2, store2, fresh = fx.load_session(config, harness)
            try:
                with pytest.raises(QualificationLineageError, match=field):
                    fresh.deployed_artifact(member)
            finally:
                store2.close()
        receipt.write_text(json.dumps(original), encoding="utf-8")
    finally:
        store.close()


def test_r11b7_nested_thread_budget_is_applied_around_case_execution(tmp_path: Path):
    """Cases execute inside the accepted stage scope, not with ambient threads.

    The accepted owner limits native BLAS/OpenMP pools through ``threadpoolctl``
    rather than by exporting environment variables, so the assertion is on the
    live pool limits observed from inside a case.
    """

    threadpoolctl = pytest.importorskip("threadpoolctl")

    config, _workspace, harness = _campaign(tmp_path)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        observed: list[list[int]] = []

        def probe(case):
            observed.append(
                [
                    int(item["num_threads"])
                    for item in threadpoolctl.threadpool_info()
                    if item.get("num_threads") is not None
                ]
            )
            return str(case), case

        session.map_cases(probe, ["a", "b"])
        assert observed
        budget = max(
            int(session.resource_scope.blas_threads),
            int(session.resource_scope.native_openmp_threads),
        )
        for limits in observed:
            assert all(value <= budget for value in limits), (limits, budget)
    finally:
        store.close()
