from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator

from mdstats.training_data._common import digest
from mdstats.training_data.relax_verify import (
    RelaxVerifyPolicy,
    RelaxBaseSet,
    RelaxModelQualification,
    RelaxVerifyRunRecord,
    RelaxVerifyCampaignRecord,
    assess_relaxed_geometry,
    build_relax_base_set,
    load_relax_reference_extxyz,
    write_relax_reference_request,
)


def _sha(label: str) -> str:
    return digest({"label": label})


def _labeled(atoms: Atoms, *, energy: float = 0.0, forces: np.ndarray | None = None) -> Atoms:
    result = atoms.copy()
    if forces is None:
        forces = np.zeros((len(result), 3), dtype=float)
    result.calc = SinglePointCalculator(result, energy=float(energy), forces=np.asarray(forces, dtype=float))
    return result


def _chain() -> Atoms:
    return Atoms(
        symbols="OSiO",
        positions=[[3.4, 5.0, 5.0], [5.0, 5.0, 5.0], [6.6, 5.0, 5.0]],
        cell=[10.0, 10.0, 10.0],
        pbc=True,
    )


def _base_set(atoms: Atoms) -> RelaxBaseSet:
    policy = RelaxVerifyPolicy(topology_group_ids=())
    fake_pes = SimpleNamespace(
        content_digest=_sha("pes"),
        target_role_digest=_sha("role"),
        target_artifact_digest=_sha("artifact"),
        target_artifact_sha256=_sha("bytes"),
        base_frame_uids=(_sha("frame"),),
        base_configuration_indices=(0,),
    )
    result, values = build_relax_base_set(fake_pes, (atoms,), policy=policy)
    assert len(values) == 1
    return result


def test_relax_policy_and_base_set_roundtrip() -> None:
    policy = RelaxVerifyPolicy(topology_group_ids=("framework",))
    assert RelaxVerifyPolicy.from_dict(policy.to_dict()) == policy
    base = _base_set(_chain())
    assert RelaxBaseSet.from_dict(base.to_dict()) == base



def test_lta_framework_group_excludes_mobile_ions_from_topology_scope() -> None:
    from mdstats.training_data import campaign_cli

    atoms = Atoms(
        symbols="OSiONa",
        positions=[[3.4, 5, 5], [5.0, 5, 5], [6.6, 5, 5], [5.0, 7.5, 5]],
        cell=[10, 10, 10], pbc=True,
    )
    fake_pes = SimpleNamespace(
        content_digest=_sha("pes-lta"), target_role_digest=_sha("role-lta"),
        target_artifact_digest=_sha("artifact-lta"), target_artifact_sha256=_sha("bytes-lta"),
        base_frame_uids=(_sha("frame-lta"),), base_configuration_indices=(0,),
    )
    policy = RelaxVerifyPolicy(topology_group_ids=("framework",))
    base, _ = build_relax_base_set(fake_pes, (atoms,), policy=policy, material_contracts=campaign_cli._lta_contracts({}))
    assert base.topology_atom_indices_by_base == ((0, 1, 2),)

def test_periodic_wrapping_is_not_topology_or_geometry_damage() -> None:
    ref = _labeled(_chain())
    cand_atoms = _chain()
    cand_atoms.positions += np.array([10.0, 0.0, 0.0])
    cand = _labeled(cand_atoms)
    base = _base_set(_chain())
    policy = RelaxVerifyPolicy()
    metric = assess_relaxed_geometry(base, (ref,), (cand,), policy=policy)[0]
    assert metric.passed
    assert metric.topology_passed
    assert metric.rms_displacement_angstrom < 1.0e-10


def test_broken_framework_bond_fails_topology() -> None:
    ref = _labeled(_chain())
    bad = _chain()
    bad.positions[2] = [8.5, 5.0, 5.0]
    cand = _labeled(bad)
    base = _base_set(_chain())
    metric = assess_relaxed_geometry(base, (ref,), (cand,), policy=RelaxVerifyPolicy())[0]
    assert not metric.passed
    assert not metric.topology_passed
    assert metric.missing_edge_count >= 1
    assert "topology_changed" in metric.failure_reasons


def test_distorted_but_connected_geometry_fails_fidelity() -> None:
    ref = _labeled(_chain())
    distorted = _chain()
    distorted.positions[0, 0] -= 0.18
    distorted.positions[2, 0] += 0.18
    cand = _labeled(distorted)
    base = _base_set(_chain())
    policy = RelaxVerifyPolicy(
        rms_displacement_tolerance_angstrom=0.10,
        max_displacement_tolerance_angstrom=0.15,
        bond_rmse_tolerance_angstrom=0.10,
        bond_max_error_tolerance_angstrom=0.15,
    )
    metric = assess_relaxed_geometry(base, (ref,), (cand,), policy=policy)[0]
    assert metric.topology_passed
    assert not metric.passed
    assert "max_displacement_exceeded" in metric.failure_reasons
    assert "bond_max_error_exceeded" in metric.failure_reasons


def test_unconverged_candidate_fails_even_with_exact_geometry() -> None:
    ref = _labeled(_chain())
    forces = np.zeros((3, 3)); forces[1, 0] = 0.05
    cand = _labeled(_chain(), forces=forces)
    base = _base_set(_chain())
    metric = assess_relaxed_geometry(base, (ref,), (cand,), policy=RelaxVerifyPolicy(), converged=(False,), optimizer_steps=(500,))[0]
    assert not metric.passed
    assert "relaxation_not_converged" in metric.failure_reasons


def test_reference_request_and_external_reference_roundtrip(tmp_path: Path) -> None:
    from ase.io import write

    base_atoms = (_chain(),)
    base_set = _base_set(base_atoms[0])
    request = write_relax_reference_request(base_set, base_atoms, tmp_path / "request")
    assert Path(request.manifest_path).is_file()
    relaxed = _labeled(_chain())
    relaxed.info["relax_base_frame_uid"] = base_set.base_frame_uids[0]
    reference_path = tmp_path / "reference.extxyz"
    write(reference_path, [relaxed], format="extxyz")
    artifact, ordered = load_relax_reference_extxyz(
        base_set, base_atoms, reference_path, policy=RelaxVerifyPolicy(), protocol_digest=_sha("protocol")
    )
    assert artifact.configuration_count == 1
    assert len(ordered) == 1



def test_dft_reference_that_breaks_preserved_topology_is_rejected(tmp_path: Path) -> None:
    from ase.io import write

    base_atoms = (_chain(),)
    base_set = _base_set(base_atoms[0])
    broken = _chain()
    broken.positions[2] = [8.5, 5.0, 5.0]
    relaxed = _labeled(broken)
    relaxed.info["relax_base_frame_uid"] = base_set.base_frame_uids[0]
    reference_path = tmp_path / "broken-reference.extxyz"
    write(reference_path, [relaxed], format="extxyz")
    with pytest.raises(Exception, match="preserved-group topology"):
        load_relax_reference_extxyz(
            base_set, base_atoms, reference_path, policy=RelaxVerifyPolicy(), protocol_digest=_sha("protocol")
        )


def test_relax_mace_model_executes_fire_and_converges(monkeypatch) -> None:
    import mace.calculators
    from ase.calculators.calculator import Calculator, all_changes
    from mdstats.training_data.relax_verify import relax_mace_model

    class Harmonic(Calculator):
        implemented_properties = ["energy", "forces"]
        def calculate(self, atoms=None, properties=("energy", "forces"), system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            target = np.array([[0.5, 0.5, 0.5]], dtype=float)
            delta = np.asarray(atoms.positions, dtype=float) - target
            self.results["energy"] = 0.5 * float(np.sum(delta * delta))
            self.results["forces"] = -delta

    monkeypatch.setattr(mace.calculators, "MACECalculator", lambda **kwargs: Harmonic())
    atoms = Atoms("H", positions=[[1.0, 0.5, 0.5]], cell=[5, 5, 5], pbc=True)
    policy = RelaxVerifyPolicy(force_convergence_ev_per_angstrom=0.01, maximum_steps=200)
    relaxed, steps, converged, drops = relax_mace_model(
        "unused.model", (atoms,), policy=policy, device="cpu", model_dtype="float64"
    )
    assert converged == (True,)
    assert 0 < steps[0] <= 200
    assert np.linalg.norm(relaxed[0].positions[0] - np.array([0.5, 0.5, 0.5])) < 0.02
    assert drops[0] is not None and drops[0] < 0.0

def test_campaign_serialization() -> None:
    policy = RelaxVerifyPolicy()
    base = _base_set(_chain())
    ref = _labeled(_chain())
    metric = assess_relaxed_geometry(base, (ref,), (ref,), policy=policy)[0]
    qualification = RelaxModelQualification(model_sha256=_sha("model"), model_role="candidate", base_metrics=(metric,), policy_digest=policy.policy_digest)
    run = RelaxVerifyRunRecord(
        run_plan_digest=_sha("run"), pes_verify_run_digest=_sha("pes-run"), candidate_model_path="candidate.model",
        candidate_model_sha256=_sha("model"), relaxed_artifact_path="relaxed.extxyz",
        relaxed_artifact_sha256=_sha("relaxed"), qualification=qualification,
    )
    from mdstats.training_data.relax_verify import RelaxRequestArtifact, RelaxReferenceArtifact
    request = RelaxRequestArtifact(
        base_set_digest=base.content_digest, extxyz_path="request.extxyz", extxyz_sha256=_sha("req"),
        manifest_path="manifest.json", manifest_sha256=_sha("manifest"), configuration_count=1,
        poscar_sha256s=(("dft-inputs/0000/POSCAR", _sha("poscar")),),
    )
    reference = RelaxReferenceArtifact(
        base_set_digest=base.content_digest, reference_path="dft.extxyz", reference_sha256=_sha("dft"),
        configuration_count=1, protocol_digest=_sha("protocol"), protocol_source="test",
        max_force_ev_per_angstrom=(0.0,),
    )
    campaign = RelaxVerifyCampaignRecord(
        campaign_plan_digest=_sha("campaign"), pes_verify_campaign_digest=_sha("pes-campaign"), policy=policy,
        base_set=base, request_artifact=request, reference_artifact=reference, run_records=(run,), stage_context="production",
    )
    assert campaign.passed_run_count == 1
    assert RelaxVerifyCampaignRecord.from_dict(campaign.to_dict()) == campaign
