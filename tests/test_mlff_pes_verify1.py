from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import mdstats
from mdstats.training_data._common import digest


def _d(label: str) -> str:
    return digest({"label": label})


def _base_atoms(shift: float = 0.0):
    from ase import Atoms

    # Tetrahedral-ish local environment: Si-O bonds are inside natural cutoffs,
    # O-O pairs are outside them, so bond/angle/coordination discovery is stable.
    center = np.array([5.0, 5.0, 5.0])
    directions = np.array(
        [
            [1.0, 1.0, 1.0],
            [1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0],
        ],
        dtype=float,
    )
    directions /= np.linalg.norm(directions, axis=1)[:, None]
    positions = np.vstack([center, center + 1.63 * directions])
    positions[:, 0] += shift
    return Atoms("SiO4", positions=positions, cell=[10.0, 10.0, 10.0], pbc=True)


def _deploy_probe_set(count: int = 4):
    return mdstats.DeployVerifyProbeSet(
        target_role_digest=_d("target-role"),
        target_artifact_digest=_d("target-artifact"),
        target_artifact_sha256=_d("target-bytes"),
        frame_uids=tuple(_d(f"frame-{i}") for i in range(count)),
        correlation_block_ids=tuple(_d(f"block-{i}") for i in range(count)),
        configuration_indices=tuple(range(count)),
    )


def _reference_payload(request_atoms, *, k: float = 4.0):
    # A simple deterministic quadratic around each base's q=0 geometry.  The
    # strain stress is synthetic but self-consistent enough to exercise the
    # comparison contract.
    base_by_uid = {}
    for atoms in request_atoms:
        if int(atoms.info["pes_side"]) == 0:
            base_by_uid[str(atoms.info["pes_base_frame_uid"])] = atoms.copy()
    energies = []
    forces = []
    stresses = []
    for atoms in request_atoms:
        base = base_by_uid[str(atoms.info["pes_base_frame_uid"])]
        delta = np.asarray(atoms.positions) - np.asarray(base.positions)
        # Cell contribution makes strain modes nonzero as well.
        cell_delta = np.asarray(atoms.cell.array) - np.asarray(base.cell.array)
        energy = 0.5 * k * float(np.sum(delta * delta)) + 0.25 * k * float(np.sum(cell_delta * cell_delta))
        force = -k * delta
        stress = 0.02 * cell_delta
        energies.append(energy)
        forces.append(force)
        stresses.append(stress)
    return {
        "energy": np.asarray(energies),
        "forces_by_configuration": tuple(np.asarray(v) for v in forces),
        "stress": np.stack(stresses),
    }


def test_probe_set_is_deterministic_and_semantically_diverse() -> None:
    targets = tuple(_base_atoms(0.01 * i) for i in range(4))
    deploy = _deploy_probe_set()
    policy = mdstats.PESVerifyPolicy(maximum_base_configurations=4, maximum_modes_per_base=4)
    first, first_atoms = mdstats.build_pes_probe_set(deploy, targets, policy=policy)
    second, second_atoms = mdstats.build_pes_probe_set(deploy, targets, policy=policy)
    assert first.content_digest == second.content_digest
    assert len(first.base_frame_uids) == 4
    assert len(first.probes) == len(second_atoms) == len(first_atoms)
    for frame_uid in first.base_frame_uids:
        mode_types = {m.mode_type for m in first.modes if m.base_frame_uid == frame_uid}
        assert {"bond_stretch", "angle_bend", "coordination_breathing", "strain"}.issubset(mode_types)
    assert all(m.mode_id for m in first.modes)


def test_request_roundtrip_and_reference_extxyz_are_geometry_locked(tmp_path: Path) -> None:
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.io import write

    targets = tuple(_base_atoms(0.01 * i) for i in range(2))
    deploy = _deploy_probe_set(2)
    policy = mdstats.PESVerifyPolicy(maximum_base_configurations=2, maximum_modes_per_base=3, include_strain_modes=False)
    probe_set, request_atoms = mdstats.build_pes_probe_set(deploy, targets, policy=policy)
    request = mdstats.write_pes_probe_request(probe_set, request_atoms, tmp_path / "request")
    assert Path(request.extxyz_path).is_file()
    assert Path(request.manifest_path).is_file()
    assert len(request.poscar_sha256s) == len(probe_set.probes)

    ref = _reference_payload(request_atoms)
    labeled = []
    for i, atoms in enumerate(request_atoms):
        item = atoms.copy()
        item.calc = SinglePointCalculator(item, energy=float(ref["energy"][i]), forces=ref["forces_by_configuration"][i])
        labeled.append(item)
    ref_path = tmp_path / "reference.extxyz"
    write(ref_path, labeled, format="extxyz")
    artifact, ordered, loaded = mdstats.load_pes_reference_extxyz(
        probe_set,
        request_atoms,
        ref_path,
        policy=policy,
        protocol_digest=_d("dft-protocol"),
    )
    assert artifact.configuration_count == len(probe_set.probes)
    assert len(ordered) == len(probe_set.probes)
    assert np.allclose(loaded["energy"], ref["energy"])

    broken = [v.copy() for v in labeled]
    broken[1].positions[0, 0] += 1.0e-3
    broken_path = tmp_path / "broken.extxyz"
    write(broken_path, broken, format="extxyz")
    with pytest.raises(mdstats.TrainingDataInputError, match="geometry changed"):
        mdstats.load_pes_reference_extxyz(
            probe_set,
            request_atoms,
            broken_path,
            policy=policy,
            protocol_digest=_d("dft-protocol"),
        )


def test_correct_local_pes_passes_and_reversed_restoring_force_fails() -> None:
    targets = tuple(_base_atoms(0.01 * i) for i in range(2))
    policy = mdstats.PESVerifyPolicy(maximum_base_configurations=2, maximum_modes_per_base=3, include_strain_modes=False)
    probe_set, request_atoms = mdstats.build_pes_probe_set(_deploy_probe_set(2), targets, policy=policy)
    reference = _reference_payload(request_atoms, k=4.0)
    passed = mdstats.assess_pes_model(
        probe_set,
        reference,
        reference,
        policy=policy,
        model_role="candidate",
        model_sha256=_d("candidate-good"),
    )
    assert passed.passed
    assert passed.failed_mode_count == 0

    wrong = {
        "energy": np.asarray(reference["energy"]).copy(),
        "forces_by_configuration": tuple(-np.asarray(v) for v in reference["forces_by_configuration"]),
        "stress": np.asarray(reference["stress"]).copy(),
    }
    failed = mdstats.assess_pes_model(
        probe_set,
        reference,
        wrong,
        policy=policy,
        model_role="candidate",
        model_sha256=_d("candidate-reversed"),
    )
    assert not failed.passed
    assert failed.restoring_sign_mismatch_count > 0
    assert any(
        "direction_mismatch" in reason
        for metric in failed.mode_metrics
        for reason in metric.rejection_reasons
    )


def test_wrong_curvature_fails_even_when_force_directions_are_same() -> None:
    targets = tuple(_base_atoms(0.01 * i) for i in range(1))
    policy = mdstats.PESVerifyPolicy(
        maximum_base_configurations=1,
        maximum_modes_per_base=3,
        include_strain_modes=False,
        projected_force_rtol=0.25,
        force_stiffness_rtol=0.30,
        energy_curvature_rtol=0.30,
    )
    probe_set, request_atoms = mdstats.build_pes_probe_set(_deploy_probe_set(1), targets, policy=policy)
    reference = _reference_payload(request_atoms, k=4.0)
    # Same restoring directions, but 2x curvature is outside the mixed tolerance.
    wrong = {
        "energy": 2.0 * np.asarray(reference["energy"]),
        "forces_by_configuration": tuple(2.0 * np.asarray(v) for v in reference["forces_by_configuration"]),
        "stress": 2.0 * np.asarray(reference["stress"]),
    }
    failed = mdstats.assess_pes_model(
        probe_set,
        reference,
        wrong,
        policy=policy,
        model_role="candidate",
        model_sha256=_d("candidate-stiff"),
    )
    assert not failed.passed
    assert failed.restoring_sign_mismatch_count == 0
    assert any(
        "stiffness_mismatch" in reason or "curvature_mismatch" in reason
        for metric in failed.mode_metrics
        for reason in metric.rejection_reasons
    )


def test_campaign_record_preserves_failed_candidate_evidence() -> None:
    targets = (_base_atoms(),)
    policy = mdstats.PESVerifyPolicy(maximum_base_configurations=1, maximum_modes_per_base=2, include_strain_modes=False)
    probe_set, request_atoms = mdstats.build_pes_probe_set(_deploy_probe_set(1), targets, policy=policy)
    reference = _reference_payload(request_atoms)
    foundation = mdstats.assess_pes_model(
        probe_set, reference, reference, policy=policy, model_role="foundation", model_sha256=_d("foundation")
    )
    candidate = mdstats.assess_pes_model(
        probe_set,
        reference,
        {"energy": 2 * reference["energy"], "forces_by_configuration": tuple(-v for v in reference["forces_by_configuration"]), "stress": reference["stress"]},
        policy=policy,
        model_role="candidate",
        model_sha256=_d("candidate"),
    )
    request = mdstats.PESProbeRequestArtifact(
        probe_set_digest=probe_set.content_digest,
        extxyz_path="request.extxyz", extxyz_sha256=_d("request"),
        manifest_path="manifest.json", manifest_sha256=_d("manifest"),
        configuration_count=len(probe_set.probes),
        poscar_sha256s=tuple((f"{i}/POSCAR", _d(f"poscar-{i}")) for i in range(len(probe_set.probes))),
    )
    ref_artifact = mdstats.PESReferenceArtifact(
        probe_set_digest=probe_set.content_digest,
        reference_path="reference.extxyz", reference_sha256=_d("reference"), configuration_count=len(probe_set.probes),
        prediction_digest=_d("predictions"), protocol_digest=_d("protocol"), protocol_source="test",
    )
    run = mdstats.PESVerifyRunRecord(
        run_plan_digest=_d("run"), deploy_verify_run_digest=_d("deploy-run"),
        candidate_model_path="candidate.model", candidate_model_sha256=_d("candidate"), candidate_qualification=candidate,
    )
    campaign = mdstats.PESVerifyCampaignRecord(
        campaign_plan_digest=_d("campaign"), deploy_verify_campaign_digest=_d("deploy-campaign"),
        foundation_audit_digest=_d("foundation-audit"), foundation_model_sha256=_d("foundation"),
        policy=policy, probe_set=probe_set, probe_request=request, reference_artifact=ref_artifact,
        foundation_qualification=foundation, run_records=(run,), stage_context="production",
        foundation_head_name="foundation_head",
    )
    assert campaign.all_candidates_failed
    restored = mdstats.PESVerifyCampaignRecord.from_dict(campaign.to_dict())
    assert restored.foundation_head_name == "foundation_head"
    assert restored.content_digest == campaign.content_digest


def test_strain_stress_path_passes_identity_and_rejects_reversed_increment() -> None:
    targets = (_base_atoms(),)
    policy = mdstats.PESVerifyPolicy(
        maximum_base_configurations=1,
        maximum_modes_per_base=4,
        include_strain_modes=True,
    )
    probe_set, request_atoms = mdstats.build_pes_probe_set(_deploy_probe_set(1), targets, policy=policy)
    assert any(mode.coordinate_kind == "strain" for mode in probe_set.modes)
    reference = _reference_payload(request_atoms, k=4.0)
    identity = mdstats.assess_pes_model(
        probe_set,
        reference,
        reference,
        policy=policy,
        model_role="candidate",
        model_sha256=_d("candidate-strain-good"),
    )
    assert identity.passed

    wrong_stress = np.asarray(reference["stress"]).copy()
    for probe in probe_set.probes:
        if probe.mode_id is None:
            continue
        mode = next(mode for mode in probe_set.modes if mode.mode_id == probe.mode_id)
        if mode.coordinate_kind == "strain":
            wrong_stress[probe.request_index] *= -1.0
    wrong = {
        "energy": np.asarray(reference["energy"]).copy(),
        "forces_by_configuration": tuple(np.asarray(v).copy() for v in reference["forces_by_configuration"]),
        "stress": wrong_stress,
    }
    failed = mdstats.assess_pes_model(
        probe_set,
        reference,
        wrong,
        policy=policy,
        model_role="candidate",
        model_sha256=_d("candidate-strain-wrong"),
    )
    assert not failed.passed
    strain_metrics = [metric for metric in failed.mode_metrics if metric.coordinate_kind == "strain"]
    assert strain_metrics and any(not metric.passed for metric in strain_metrics)


def test_v1_policy_rejects_partial_mode_qualification() -> None:
    with pytest.raises(mdstats.TrainingDataInputError, match="requires all generated modes"):
        mdstats.PESVerifyPolicy(require_all_modes=False)


def test_strain_reference_extxyz_requires_and_roundtrips_stress(tmp_path: Path) -> None:
    from ase.calculators.singlepoint import SinglePointCalculator
    from ase.io import write

    targets = (_base_atoms(),)
    policy = mdstats.PESVerifyPolicy(maximum_base_configurations=1, maximum_modes_per_base=4, include_strain_modes=True)
    probe_set, request_atoms = mdstats.build_pes_probe_set(_deploy_probe_set(1), targets, policy=policy)
    reference = _reference_payload(request_atoms)
    labeled = []
    for i, atoms in enumerate(request_atoms):
        item = atoms.copy()
        item.calc = SinglePointCalculator(
            item,
            energy=float(reference["energy"][i]),
            forces=reference["forces_by_configuration"][i],
            stress=reference["stress"][i],
        )
        labeled.append(item)
    path = tmp_path / "strain-reference.extxyz"
    write(path, labeled, format="extxyz")
    artifact, _, loaded = mdstats.load_pes_reference_extxyz(
        probe_set,
        request_atoms,
        path,
        policy=policy,
        protocol_digest=_d("strain-dft-protocol"),
    )
    assert artifact.configuration_count == len(request_atoms)
    assert loaded["stress"] is not None
    assert np.asarray(loaded["stress"]).shape == (len(request_atoms), 3, 3)
