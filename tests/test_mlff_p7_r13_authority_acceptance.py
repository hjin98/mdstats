"""Fresh revision-13 authority acceptance.

These tests cover the reopened ownership boundaries directly.  The campaign
cases still use the bounded P5/P7 harness below the real semantic owners; the
real MACE/LAMMPS target-machine gate remains a separate, explicitly unavailable
integration when that runtime is not present.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

import tests._mlff_qualification_fixture as fx

from mdstats.training_data._common import TrainingDataSerializationError, digest
from mdstats.training_data.qualification.errors import (
    QualificationError,
    QualificationLineageError,
    QualificationUnavailableError,
)
from mdstats.training_data.qualification.reference import (
    AuthenticatedReferenceBundle,
    PhysicalReferenceRequest,
    ReferenceGeometryRequest,
    ReferenceObservation,
    write_reference_bundle,
)
from mdstats.training_data.qualification.resource_observation import (
    QualificationDiskReserveError,
    ResourceObservationRecorder,
    accelerator_observation,
    require_free_disk_reserve,
)
from mdstats.training_data.qualification.components import COMPONENT_LOCKED_TEST
from mdstats.training_data.qualification.stress import (
    CANONICAL_VOIGT_ORDER,
    ExternalStressProvenance,
    canonical_stress_from_virial,
    canonical_stress_tensor,
    canonicalize_external_stress,
)
from mdstats.training_data.qualification.stress_capability import (
    resolve_stress_capability,
)


def _geometry_digest(label: str) -> str:
    return digest({"r13-test-geometry": label})


def _reference_observation(
    geometry_identity: str,
    *,
    stress_value=None,
    provenance: ExternalStressProvenance | None = None,
) -> ReferenceObservation:
    common = {
        "geometry_identity": geometry_identity,
        "energy_ev": 0.0,
        "forces_ev_per_angstrom": ((0.0, 0.0, 0.0),),
    }
    if stress_value is None:
        return ReferenceObservation(**common)
    return ReferenceObservation.from_external_stress(
        **common,
        stress_value=stress_value,
        stress_provenance=provenance,
    )


def test_r13_external_stress_provenance_converts_voigt_tensor_and_virial_once():
    """Source units, sign, order, and virial volume are all replayable facts."""

    raw_gpa = np.array([1.0, -2.0, 3.0, 0.4, 0.5, 0.6])
    order = ("zz", "yy", "xx", "xz", "xy", "yz")
    gpa_provenance = ExternalStressProvenance(
        representation="voigt",
        units="GPa",
        sign_convention="tensile_positive",
        source="dft-adapter.v1",
        voigt_order=order,
    )
    observed = canonicalize_external_stress(raw_gpa, gpa_provenance)
    expected = canonical_stress_tensor(raw_gpa, units="gpa", voigt_order=order)
    assert np.array_equal(observed, expected)
    assert np.array_equal(
        _reference_observation(
            _geometry_digest("gpa"),
            stress_value=raw_gpa,
            provenance=gpa_provenance,
        ).stress,
        expected,
    )

    raw_virial = np.array([10.0, 20.0, 30.0, 4.0, 5.0, 6.0])
    virial_provenance = ExternalStressProvenance(
        representation="virial",
        units="eV",
        sign_convention="tensile_positive",
        source="dft-virial-adapter.v1",
        volume_angstrom3=2.0,
        volume_source="instantaneous-cell.v1",
    )
    assert np.array_equal(
        canonicalize_external_stress(raw_virial, virial_provenance),
        canonical_stress_from_virial(raw_virial, volume_angstrom3=2.0),
    )

    compression = ExternalStressProvenance(
        representation="voigt",
        units="bar",
        sign_convention="compressive_positive",
        source="pressure-adapter.v1",
    )
    compressed = canonicalize_external_stress(
        np.array([1000.0, 1000.0, 1000.0, 40.0, 50.0, 60.0]), compression
    )
    assert np.all(np.diag(compressed) < 0.0)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ExternalStressProvenance(
            representation="voigt",
            units="GPa",
            sign_convention="missing-sign",
            source="test",
        ),
        lambda: ExternalStressProvenance(
            representation="voigt",
            units="GPa",
            sign_convention="tensile_positive",
            source="test",
            voigt_order=("xx", "xx", "zz", "xy", "yz", "xz"),
        ),
        lambda: ExternalStressProvenance(
            representation="virial",
            units="eV",
            sign_convention="tensile_positive",
            source="test",
        ),
    ],
)
def test_r13_external_stress_bad_metadata_fails_closed(factory):
    with pytest.raises((QualificationError, QualificationLineageError)):
        factory()


def test_r13_external_stress_cannot_be_double_canonicalized_or_undeclared():
    provenance = ExternalStressProvenance(
        representation="voigt",
        units="GPa",
        sign_convention="tensile_positive",
        source="external.v1",
    )
    with pytest.raises(QualificationLineageError, match="raw source value"):
        ReferenceObservation(
            geometry_identity=_geometry_digest("double"),
            energy_ev=0.0,
            forces_ev_per_angstrom=((0.0, 0.0, 0.0),),
            stress_ev_per_angstrom3=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            stress_provenance=provenance,
        )
    with pytest.raises(QualificationLineageError):
        canonicalize_external_stress(
            np.eye(3), ExternalStressProvenance.canonical_inline()
        )

    persisted = _reference_observation(
        _geometry_digest("persisted"),
        stress_value=np.eye(3),
        provenance=ExternalStressProvenance(
            representation="tensor",
            units="ev_per_angstrom3",
            sign_convention="tensile_positive",
            source="external.v1",
        ),
    ).to_dict()
    del persisted["stress_provenance"]
    with pytest.raises(QualificationLineageError, match="source provenance"):
        ReferenceObservation.from_dict(persisted)


def test_r13_required_reference_stress_and_bundle_provenance_are_authenticated(tmp_path: Path):
    geometry = _geometry_digest("required")
    request = PhysicalReferenceRequest(
        protocol_identity="real-reference-protocol.v1",
        physical_plan_digest="a" * 64,
        geometries=(
            ReferenceGeometryRequest(
                frame_uid="frame-1",
                mode="base",
                geometry_identity=geometry,
                atom_count=1,
            ),
        ),
        stress_required_geometry_identities=(geometry,),
    )
    with pytest.raises(QualificationLineageError, match="requires stress"):
        write_reference_bundle(
            tmp_path,
            request,
            [_reference_observation(geometry)],
        )

    provenance_a = ExternalStressProvenance(
        representation="tensor",
        units="ev_per_angstrom3",
        sign_convention="tensile_positive",
        source="adapter-a.v1",
    )
    provenance_b = ExternalStressProvenance(
        representation="tensor",
        units="ev_per_angstrom3",
        sign_convention="tensile_positive",
        source="adapter-b.v1",
    )
    bundle_a = AuthenticatedReferenceBundle(
        request_digest=request.content_digest,
        protocol_identity=request.protocol_identity,
        observations={
            geometry: _reference_observation(
                geometry, stress_value=np.eye(3), provenance=provenance_a
            )
        },
    )
    bundle_b = AuthenticatedReferenceBundle(
        request_digest=request.content_digest,
        protocol_identity=request.protocol_identity,
        observations={
            geometry: _reference_observation(
                geometry, stress_value=np.eye(3), provenance=provenance_b
            )
        },
    )
    assert bundle_a.content_digest != bundle_b.content_digest


def _stress_context(stress_weight: float = 1.0):
    return SimpleNamespace(
        method_policies=SimpleNamespace(
            common_training=SimpleNamespace(
                objective_policy=SimpleNamespace(stress_weight=stress_weight)
            )
        ),
        selected=SimpleNamespace(
            authorities=SimpleNamespace(frame_array_index={})
        ),
    )


def _resolve_claim(
    context,
    atoms,
    stresses,
    *,
    member_id: str,
    component: str = "deployment_parity",
    claim_kind: str = "deployment",
    runtime_reports_stress: bool = True,
    reference_by_geometry=None,
):
    return resolve_stress_capability(
        context,
        policy={"stress_required": component == "physical_pes"},
        probe_atoms=atoms,
        probe_stresses=stresses,
        runtime_reports_stress=runtime_reports_stress,
        reference_stress_available_by_geometry=reference_by_geometry,
        qualification_binding_digest="b" * 64,
        component=component,
        claim_kind=claim_kind,
        member_id=member_id,
        geometry_or_cohort_digest="c" * 64,
    )


def test_r13_stress_capability_is_member_component_and_geometry_scoped():
    from ase import Atoms

    context = _stress_context()
    full = Atoms("Li", positions=[[0.0, 0.0, 0.0]], cell=np.eye(3) * 5.0, pbc=[True] * 3)
    mixed = full.copy()
    mixed.set_pbc([True, True, False])
    stress = np.zeros((3, 3))

    member_a = _resolve_claim(
        context, [full], [stress], member_id="seed-5", reference_by_geometry=[True]
    )
    member_b = _resolve_claim(
        context, [full], [None], member_id="seed-6", reference_by_geometry=[True]
    )
    assert member_a.applicable is True
    assert member_b.applicable is False
    assert member_a.model_reports_stress is True
    assert member_b.model_reports_stress is False
    assert member_a.content_digest != member_b.content_digest

    mixed_claim = _resolve_claim(
        context,
        [full, mixed],
        [stress, None],
        member_id="seed-5",
        runtime_reports_stress=False,
        reference_by_geometry=[True, False],
    )
    assert mixed_claim.geometry_applicability == (True, False)
    assert mixed_claim.geometry_is_applicable(0)
    assert not mixed_claim.geometry_is_applicable(1)
    assert mixed_claim.deployed_comparable is False

    physical_claim = _resolve_claim(
        context,
        [full],
        [stress],
        member_id="seed-5",
        component="physical_pes",
        claim_kind="physical",
        reference_by_geometry=[True],
    )
    assert physical_claim.policy_requires_stress is True
    assert physical_claim.required is True
    assert physical_claim.component != member_a.component
    assert physical_claim.content_digest != member_a.content_digest


def test_r13_new_reference_request_names_exact_applicable_stress_geometries(
    tmp_path: Path,
):
    harness = fx.QualificationHarness(
        potential=fx.AnalyticPairPotential(report_stress=True),
    )
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        expected = {
            item.geometry_identity
            for item in session.reference_request.geometries
            if item.mode != "relaxed"
        }
        assert set(session.reference_request.stress_required_geometry_identities) == expected
    finally:
        store.close()


def _supply_reference(config: Path, harness) -> None:
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        fx.supply_analytic_reference_bundle(session, harness)
    finally:
        store.close()


def _current_record(config: Path, harness):
    from mdstats.training_data.qualification.runtime import (
        resolve_current_qualification_verdict,
    )

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        record = resolve_current_qualification_verdict(
            store, paths, session.context, binding=session.binding
        )
        assert record is not None
        return record
    finally:
        store.close()


def test_r13_two_member_deployed_stress_missing_rejects_exact_committee(tmp_path: Path):
    """Member 0's stress capability cannot rescue a member 1 omission."""

    harness = fx.QualificationHarness(
        potential=fx.AnalyticPairPotential(report_stress=True),
        deployed_stress_members_without={"seed-6"},
    )
    config, _workspace = fx.build_qualified_campaign(
        tmp_path,
        config_text=fx.fixture_config_text(production_seeds="[5,6]"),
        harness=harness,
    )
    _supply_reference(config, harness)
    with pytest.raises(QualificationError, match="rejected the exact frozen publication"):
        fx.run_qualification_command(config, "run", harness=harness)

    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        evidence = session.completed_component(
            "deployment_parity",
            session.component_input_digest("deployment_parity", None),
        )
        assert evidence is not None
        assert evidence.status.value == "rejected"
        members = {row["member_id"]: row for row in evidence.payload["members"]}
        assert set(members) == {"seed-5", "seed-6"}
        assert members["seed-5"]["stress_applicable"] is True
        assert members["seed-6"]["stress_applicable"] is True
        assert members["seed-6"]["missing_stress_count"] > 0
        assert set(evidence.payload["stress_capabilities"]) == set(members)
    finally:
        store.close()


def test_r13_unavailable_deployment_stress_cannot_be_rescued_by_injected_tensor(
    tmp_path: Path,
):
    """Runtime capability evidence owns applicability even at default policy."""

    from mdstats.training_data.qualification.deployment import qualify_deployment_parity

    harness = fx.QualificationHarness(
        potential=fx.AnalyticPairPotential(report_stress=True),
    )
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    _supply_reference(config, harness)
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        # The bounded evaluator still returns stress, but the authenticated
        # deployment capability says the actual runtime cannot expose it.
        session.deployed_stress_supported = False
        evidence = qualify_deployment_parity(session)
        assert evidence.status.value == "rejected"
        assert evidence.metrics["stress_applicable"] is True
        assert evidence.payload["members"][0]["missing_stress_count"] > 0
        assert evidence.payload["members"][0]["stress_capability"] == "unavailable"
    finally:
        store.close()


def test_r13_stress_claim_set_digest_is_invariant_to_member_order(tmp_path: Path):
    """Member order changes evidence presentation, never claim semantics."""

    import dataclasses

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(
        tmp_path,
        config_text=fx.fixture_config_text(production_seeds="[5,6]"),
        harness=harness,
    )
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        forward = session.stress_capability_digest("deployment_parity", None)
        # Publication authentication deliberately requires canonical seed
        # order.  Exercise the order-independent claim-set owner by reversing
        # the insertion order of the already authenticated decisions instead
        # of manufacturing an invalid publication.
        reversed_session = dataclasses.replace(
            session,
            _stress_capabilities=dict(reversed(list(session._stress_capabilities.items()))),
        )
        reverse = reversed_session._cached_capability_digest("deployment_parity")
        assert reverse == forward
    finally:
        store.close()


def test_r13_component_input_changes_when_runtime_capability_changes(tmp_path: Path):
    """A changed claim fact makes the old deployment evidence unreachable."""

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        before_input = session.component_input_digest("deployment_parity", None)
        existing = session.completed_component("deployment_parity", before_input)
        assert existing is not None
        decision = existing.payload["stress_capabilities"]["seed-5"]
        session.deployed_stress_supported = not bool(decision["runtime_reports_stress"])
        after_input = session.component_input_digest("deployment_parity", None)
        assert after_input != before_input
        assert session.completed_component("deployment_parity", after_input) is None
    finally:
        store.close()


@pytest.mark.parametrize("pbc", [(True, True, True), (False, False, False), (True, True, False), (True, False, False)])
def test_r13_static_runtime_observation_preserves_exact_pbc_and_cell(
    tmp_path: Path, monkeypatch, pbc
):
    from ase import Atoms
    import mdstats.training_data.qualification.runtime_capability as runtime

    atoms = Atoms(
        "Li2",
        positions=[[0.0, 0.0, 0.0], [6.0, 0.0, 0.0]],
        cell=np.diag([10.0, 11.0, 12.0]),
        pbc=pbc,
    )
    observed_cell = np.asarray(atoms.get_cell(), dtype=np.float64).tolist()

    def fake_execute(request, **_kwargs):
        assert request["pbc"] == list(pbc)
        return {
            "potential_energy_ev": 0.0,
            "forces_ev_per_angstrom": np.zeros((2, 3)).tolist(),
            "stress_ev_per_angstrom3": None,
            "cell_angstrom": observed_cell,
            "pbc": list(pbc),
            "runtime_evidence": {
                "mliappy_activated": True,
                "product_callback_executed": True,
            },
        }

    monkeypatch.setattr(runtime, "execute_lammps_request", fake_execute)
    observation = runtime.deployed_static_observation(
        atoms,
        artifact_path=tmp_path / "artifact.pt",
        element_types=("Li",),
        working_directory=tmp_path / "runtime",
    )
    assert observation.pbc == pbc
    assert np.array_equal(observation.cell_angstrom, atoms.get_cell())


@pytest.mark.parametrize("field", ["pbc", "cell_angstrom"])
def test_r13_static_runtime_observation_mismatch_fails_closed(
    tmp_path: Path, monkeypatch, field
):
    from ase import Atoms
    import mdstats.training_data.qualification.runtime_capability as runtime

    atoms = Atoms(
        "Li",
        positions=[[0.0, 0.0, 0.0]],
        cell=np.diag([8.0, 9.0, 10.0]),
        pbc=[True, True, False],
    )
    result = {
        "potential_energy_ev": 0.0,
        "forces_ev_per_angstrom": [[0.0, 0.0, 0.0]],
        "stress_ev_per_angstrom3": None,
        "cell_angstrom": np.asarray(atoms.get_cell()).tolist(),
        "pbc": [True, True, False],
        "runtime_evidence": {},
    }
    if field == "pbc":
        result["pbc"] = [True, True, True]
    else:
        result["cell_angstrom"] = (np.asarray(atoms.get_cell()) + np.eye(3)).tolist()
    monkeypatch.setattr(runtime, "execute_lammps_request", lambda *_a, **_k: result)
    with pytest.raises(QualificationLineageError, match="different post-build|different per-axis"):
        runtime.deployed_static_observation(
            atoms,
            artifact_path=tmp_path / "artifact.pt",
            element_types=("Li",),
            working_directory=tmp_path / "runtime",
        )


def test_r13_deployed_evaluation_rejects_nonboolean_observed_pbc():
    from mdstats.training_data.qualification.deployment import DeployedEvaluation

    with pytest.raises(QualificationLineageError, match="three-axis boolean"):
        DeployedEvaluation(
            energies_ev=(0.0,),
            forces_ev_per_angstrom=(np.zeros((1, 3)),),
            artifact_sha256="a" * 64,
            runtime_identity="b" * 64,
            cells_angstrom=(np.eye(3),),
            pbc=((1, False, False),),
        )


def test_r13_worker_uses_authenticated_kokkos_args_and_activation_order(monkeypatch, tmp_path: Path):
    import mdstats.training_data.qualification._lammps_worker as worker
    import mdstats.training_data.qualification.runtime_capability as runtime

    assert runtime._effective_lammps_cmdargs({"kokkos_gpu_count": 1}) == [
        "-k",
        "on",
        "g",
        "1",
        "-sf",
        "kk",
    ]
    assert runtime._effective_lammps_cmdargs({"kokkos_gpu_count": 2})[3] == "2"
    assert worker._effective_lammps_cmdargs({"kokkos_gpu_count": 1}) == (
        "-k",
        "on",
        "g",
        "1",
        "-sf",
        "kk",
    )

    events = []

    class FakeLammps:
        def command(self, line):
            events.append(("command", line))

    instance = FakeLammps()
    module = ModuleType("lammps")
    module.lammps = lambda *, cmdargs: (events.append(("launch", tuple(cmdargs))) or instance)
    module.mliap = SimpleNamespace(
        activate_mliappy=lambda value: events.append(("activate", value)),
        load_unified=lambda value: events.append(("load_unified", value)),
    )
    monkeypatch.setitem(__import__("sys").modules, "lammps", module)
    monkeypatch.setattr(
        worker,
        "_load_deployed_model",
        lambda path: (events.append(("load_model", path)) or object()),
    )
    built = worker._build(
        {
            "data_path": str(tmp_path / "probe.data"),
            "artifact_path": str(tmp_path / "model.pt"),
            "element_types": ["Li"],
            "pbc": [True, False, False],
            "lammps_cmdargs": ["-k", "on", "g", "1", "-sf", "kk"],
        }
    )
    assert built is instance
    assert events[0] == ("launch", ("-log", "none", "-screen", "none", "-nocite", "-k", "on", "g", "1", "-sf", "kk"))
    names = [item[0] for item in events]
    assert names.index("activate") < names.index("load_model")
    assert names.index("activate") < names.index("load_unified")
    assert ("command", "boundary p f f") in events

    source = Path(worker.__file__).read_text(encoding="utf-8")
    assert "lammps.finalize" not in source
    assert "lammps_python_finalize" not in source


def test_r13_actual_callback_failure_is_runtime_unavailable_not_scientific_pass(
    tmp_path: Path, monkeypatch
):
    import mdstats.training_data.qualification.runtime_capability as runtime

    probe = runtime.LammpsRuntimeProbe(
        available=True,
        version="20250910",
        mliap_available=True,
        mliappy_available=True,
        python_module_path="/target/lammps.py",
        mace_mliap_supported=False,
        detail="static exchange introspection is not authoritative",
    )
    monkeypatch.setattr(runtime, "_require_supported_runtime", lambda: probe)

    class FailedProcess:
        returncode = 1
        stdout = io.StringIO("")
        stderr = io.StringIO("forward_exchange callback failure")

        def communicate(self, timeout):
            Path(self.argv[-1]).write_text(
                json.dumps(
                    {
                        "ok": False,
                        "error": "AttributeError: forward_exchange",
                    }
                ),
                encoding="utf-8",
            )
            return "", self.stderr.getvalue()

    def fake_popen(argv, **_kwargs):
        process = FailedProcess()
        process.argv = argv
        return process

    monkeypatch.setattr(runtime.subprocess, "Popen", fake_popen)
    with pytest.raises(QualificationUnavailableError, match="forward_exchange"):
        runtime.execute_lammps_request(
            {"mode": "static", "pbc": [True, True, True]},
            working_directory=tmp_path,
        )


def test_r13_static_mace_diagnostic_failure_does_not_demote_live_mliappy(
    monkeypatch,
):
    """Only the actual worker callback owns MACE product availability."""

    import sys
    import mdstats.training_data.qualification.runtime_capability as runtime

    class FakeLammps:
        def version(self):
            return 20250910

        def has_style(self, kind, name):
            return kind == "pair" and name == "mliap"

        def close(self):
            return None

    module = ModuleType("lammps")
    module.__file__ = "/target/lammps.py"
    module.lammps = lambda **_kwargs: FakeLammps()
    module.mliap = SimpleNamespace(activate_mliappy=lambda _instance: None)

    def diagnostic_failure():
        raise RuntimeError("static import probe failed")

    monkeypatch.setitem(sys.modules, "lammps", module)
    monkeypatch.setattr(runtime, "_mace_mliap_interface_supported", diagnostic_failure)
    monkeypatch.setattr(runtime, "_PROBE_CACHE", None)
    probe = runtime.probe_lammps_runtime(refresh=True)
    assert probe.mliappy_available is True
    assert probe.supports_deployed_execution is True
    assert probe.supports_mace_product_execution is False


def test_r13_resource_observation_is_cumulative_and_scope_material_is_bound(tmp_path: Path):
    material = {
        "schema": "r13-resource-scope-test.v1",
        "cpu_threads_budget": 4,
        "selected_device": "cuda:1",
        "native_openmp_threads": 1,
    }
    recorder = ResourceObservationRecorder(
        binding_digest="a" * 64,
        attempt_identity="b" * 64,
        resource_scope_digest=digest(material),
        workspace=tmp_path,
        attempt_root=tmp_path / "attempt",
        minimum_free_disk_gib=0.0,
        resource_scope_material=material,
    )
    recorder.record_component(
        "deployment_parity", started="2026-01-01T00:00:00+00:00", elapsed=1.0, reused=False
    )
    first = recorder.finish()
    first_bytes = first.to_dict()
    recorder.mark_published(first)
    recorder.record_component(
        "locked_test", started="2026-01-01T00:00:01+00:00", elapsed=0.25, reused=False
    )
    second = recorder.finish()
    assert first.to_dict() == first_bytes
    assert second.previous_observation_digest == first.content_digest
    assert second.elapsed_seconds >= first.elapsed_seconds
    assert {item.component for item in second.component_timings} == {
        "deployment_parity",
        "locked_test",
    }
    assert second.resource_scope_material == material
    assert digest(second.resource_scope_material) == second.resource_scope_digest
    assert second.is_measured


def test_r13_wait_resume_locked_resource_lineage_is_complete(tmp_path: Path):
    """Each restart generation remains reachable from the terminal record."""

    from mdstats.training_data.qualification.resource_observation import (
        QualificationResourceObservation,
    )

    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    first_record = _current_record(config, harness)
    assert first_record.resource_observation_digest is not None
    _supply_reference(config, harness)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    second_record = _current_record(config, harness)
    assert second_record.resource_observation_digest is not None
    assert fx.run_qualification_command(
        config, "activate-locked", harness=harness, confirm=True
    ) == 0
    terminal = _current_record(config, harness)
    assert terminal.resource_observation_digest is not None

    _cfg, _paths, store, session = fx.load_session(config, harness)
    try:
        first = session.store.get(
            first_record.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        )
        second = session.store.get(
            second_record.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        )
        final = session.store.get(
            terminal.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        )
        assert first.to_dict() == session.store.get(
            first_record.resource_observation_digest,
            QualificationResourceObservation.from_dict,
        ).to_dict()
        assert second.previous_observation_digest == first.content_digest
        assert final.previous_observation_digest == second.content_digest
        assert any(
            timing.component == COMPONENT_LOCKED_TEST and timing.elapsed_seconds > 0.0
            for timing in final.component_timings
        )
    finally:
        store.close()


def test_r13_selected_accelerator_telemetry_does_not_fall_back_to_device_zero(monkeypatch):
    calls = []

    class FakeDevice:
        def __enter__(self):
            calls.append(("enter", 1))

        def __exit__(self, *_args):
            calls.append(("exit", 1))

    class FakeCuda:
        def is_available(self):
            return True

        def device_count(self):
            return 2

        def get_device_properties(self, index):
            calls.append(("properties", index))
            return SimpleNamespace(name="GPU-1", total_memory=2000)

        def device(self, index):
            calls.append(("device", index))
            return FakeDevice()

        def max_memory_allocated(self, index):
            calls.append(("allocated", index))
            return 123

    torch = ModuleType("torch")
    torch.cuda = FakeCuda()
    monkeypatch.setitem(__import__("sys").modules, "torch", torch)
    assert accelerator_observation("cuda:1") == ("GPU-1", 2000, 123)
    assert ("properties", 1) in calls
    assert ("allocated", 1) in calls
    assert ("properties", 0) not in calls


def test_r13_disk_headroom_is_reserved_before_materialization(monkeypatch, tmp_path: Path):
    reserve_bytes = 1024**3
    monkeypatch.setattr(
        "mdstats.training_data.qualification.resource_observation.shutil.disk_usage",
        lambda _path: SimpleNamespace(
            total=10 * reserve_bytes,
            used=9 * reserve_bytes,
            free=reserve_bytes + 99,
        ),
    )
    with pytest.raises(QualificationDiskReserveError, match="headroom"):
        require_free_disk_reserve(
            tmp_path,
            minimum_free_gib=1.0,
            operation="deployment artifact",
            required_incremental_headroom_bytes=100,
        )
    assert require_free_disk_reserve(
        tmp_path,
        minimum_free_gib=1.0,
        operation="deployment artifact",
        required_incremental_headroom_bytes=99,
    ) == pytest.approx(1.0 + 99 / reserve_bytes)


def test_r13_public_release_graph_rejects_missing_resource_or_indexed_terminal(
    tmp_path: Path,
):
    harness = fx.QualificationHarness()
    config, _workspace = fx.build_qualified_campaign(tmp_path, harness=harness)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    _supply_reference(config, harness)
    assert fx.run_qualification_command(config, "run", harness=harness) == 0

    from mdstats.training_data.qualification.runtime import resolve_current_release_evidence

    _cfg, paths, store, session = fx.load_session(config, harness)
    try:
        index = resolve_current_release_evidence(
            store, paths, session.context, binding=session.binding
        )
        assert index is not None
        resource_path = session.store.object_path(index.resource_observation_digest)
        resource_bytes = resource_path.read_bytes()
        resource_path.unlink()
        with pytest.raises((QualificationLineageError, TrainingDataSerializationError)):
            resolve_current_release_evidence(
                store, paths, session.context, binding=session.binding
            )
        resource_path.write_bytes(resource_bytes)

        terminal_path = session.store.object_path(index.qualification_record_digest)
        terminal_bytes = terminal_path.read_bytes()
        terminal_path.unlink()
        with pytest.raises(QualificationLineageError):
            resolve_current_release_evidence(
                store, paths, session.context, binding=session.binding
            )
        terminal_path.write_bytes(terminal_bytes)

        # A syntactically valid replacement index whose terminal pointer does
        # not agree with the original graph is still rejected at exposure.
        index_path = session.store.object_path(index.content_digest)
        index_bytes = index_path.read_bytes()
        payload = json.loads(index_bytes.decode("utf-8"))
        payload["qualification_record_digest"] = "0" * 64
        payload["content_digest"] = digest(
            {key: value for key, value in payload.items() if key != "content_digest"}
        )
        index_path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises((QualificationLineageError, TrainingDataSerializationError)):
            resolve_current_release_evidence(
                store, paths, session.context, binding=session.binding
            )
        index_path.write_bytes(index_bytes)
        assert resolve_current_release_evidence(
            store, paths, session.context, binding=session.binding
        ).content_digest == index.content_digest
    finally:
        store.close()
