from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from ase import Atoms
from ase.calculators.singlepoint import SinglePointCalculator

from mdstats.training_data._common import digest
from mdstats.training_data.dyn_verify import (
    DynVerifyPolicy, DynVerifyPlan, DynCaseMetric, DynVerifyRunRecord, DynVerifyCampaignRecord,
    build_dyn_verify_plan, assess_dyn_trajectory,
)


def _sha(label: str) -> str:
    return digest({"label": label})


def _chain() -> Atoms:
    return Atoms("OSiO", positions=[[3.4, 5, 5], [5.0, 5, 5], [6.6, 5, 5]], cell=[10, 10, 10], pbc=True)


def _frame(atoms: Atoms, force: float = 0.01) -> Atoms:
    out = atoms.copy()
    forces = np.zeros((len(out), 3)); forces[:, 0] = force
    out.calc = SinglePointCalculator(out, energy=-10.0, forces=forces)
    return out


def _thermo(policy: DynVerifyPolicy, temp: float, drift: float = 0.0):
    steps = list(range(0, policy.nvt_steps + policy.nve_steps + 1, policy.sample_interval_steps))
    rows = []
    natoms = 3
    for step in steps:
        time_ps = max(0, step - policy.nvt_steps) * policy.timestep_fs / 1000.0
        etotal = -10.0 + drift * time_ps * natoms
        rows.append((step, temp, -11.0, 1.0, etotal))
    return rows


def _frames(policy: DynVerifyPolicy, *, damaged_range=()):
    count = (policy.nvt_steps + policy.nve_steps) // policy.sample_interval_steps + 1
    result = []
    for i in range(count):
        atoms = _chain()
        if i in damaged_range:
            atoms.positions[2, 0] = 8.6
        result.append(_frame(atoms))
    return result


def test_policy_roundtrip_and_defaults() -> None:
    policy = DynVerifyPolicy()
    assert policy.temperatures_kelvin == (300.0, 800.0)
    assert policy.nvt_steps * policy.timestep_fs == pytest.approx(200.0)
    assert policy.nve_steps * policy.timestep_fs == pytest.approx(1000.0)
    assert DynVerifyPolicy.from_dict(policy.to_dict()) == policy


def test_clean_rollout_passes() -> None:
    policy = DynVerifyPolicy(persistent_damage_samples=5)
    metric = assess_dyn_trajectory(
        _chain(), _frames(policy), _thermo(policy, 300.0), base_frame_uid=_sha("base"),
        topology_atom_indices=(0, 1, 2), temperature_kelvin=300.0, velocity_seed=42, policy=policy,
    )
    assert metric.passed
    assert not metric.persistent_structural_damage
    assert metric.absolute_energy_drift_ev_per_atom_per_ps < 1e-10


def test_transient_topology_excursion_does_not_fail_persistence_gate() -> None:
    policy = DynVerifyPolicy(persistent_damage_samples=5)
    metric = assess_dyn_trajectory(
        _chain(), _frames(policy, damaged_range=range(20, 23)), _thermo(policy, 300.0),
        base_frame_uid=_sha("base"), topology_atom_indices=(0, 1, 2), temperature_kelvin=300.0,
        velocity_seed=42, policy=policy,
    )
    assert metric.damaged_sample_count >= 3
    assert metric.maximum_consecutive_damage_samples == 3
    assert metric.passed


def test_persistent_framework_damage_is_hard_failure() -> None:
    policy = DynVerifyPolicy(persistent_damage_samples=5)
    metric = assess_dyn_trajectory(
        _chain(), _frames(policy, damaged_range=range(20, 30)), _thermo(policy, 800.0),
        base_frame_uid=_sha("base"), topology_atom_indices=(0, 1, 2), temperature_kelvin=800.0,
        velocity_seed=42, policy=policy,
    )
    assert not metric.passed
    assert metric.persistent_structural_damage
    assert "persistent_structural_damage" in metric.failure_reasons


def test_large_nve_energy_drift_fails_even_without_structure_damage() -> None:
    policy = DynVerifyPolicy()
    metric = assess_dyn_trajectory(
        _chain(), _frames(policy), _thermo(policy, 300.0, drift=0.040),
        base_frame_uid=_sha("base"), topology_atom_indices=(0, 1, 2), temperature_kelvin=300.0,
        velocity_seed=42, policy=policy,
    )
    assert not metric.passed
    assert metric.absolute_energy_drift_ev_per_atom_per_ps == pytest.approx(0.040, rel=1e-6)
    assert "nve_energy_drift_exceeded" in metric.failure_reasons


def test_temperature_diagnostics_are_hard_bounded() -> None:
    policy = DynVerifyPolicy()
    metric = assess_dyn_trajectory(
        _chain(), _frames(policy), _thermo(policy, 500.0),
        base_frame_uid=_sha("base"), topology_atom_indices=(0, 1, 2), temperature_kelvin=300.0,
        velocity_seed=42, policy=policy,
    )
    assert not metric.passed
    assert "nvt_temperature_out_of_range" in metric.failure_reasons
    assert "nve_temperature_out_of_range" in metric.failure_reasons


def test_plan_uses_common_relax_reference_and_candidate_independent_seeds() -> None:
    policy = DynVerifyPolicy(maximum_base_configurations=2, temperatures_kelvin=(300.0, 800.0))
    relax = SimpleNamespace(
        content_digest=_sha("relax-campaign"),
        reference_artifact=SimpleNamespace(content_digest=_sha("reference-record"), reference_sha256=_sha("reference-bytes")),
        base_set=SimpleNamespace(
            base_frame_uids=(_sha("b0"), _sha("b1"), _sha("b2")),
            topology_atom_indices_by_base=((0, 1, 2), (0, 1, 2), (0, 1, 2)),
        ),
    )
    first = build_dyn_verify_plan(relax, policy=policy)
    second = build_dyn_verify_plan(relax, policy=policy)
    assert first == second
    assert len(first.base_frame_uids) == 2
    assert len(first.case_velocity_seeds) == 4
    assert DynVerifyPlan.from_dict(first.to_dict()) == first


def test_campaign_roundtrip_and_all_cases_are_hard() -> None:
    policy = DynVerifyPolicy(maximum_base_configurations=1, temperatures_kelvin=(300.0,))
    relax = SimpleNamespace(
        content_digest=_sha("relax-campaign"),
        reference_artifact=SimpleNamespace(content_digest=_sha("reference-record"), reference_sha256=_sha("reference-bytes")),
        base_set=SimpleNamespace(base_frame_uids=(_sha("b0"),), topology_atom_indices_by_base=((0, 1, 2),)),
    )
    plan = build_dyn_verify_plan(relax, policy=policy)
    metric = assess_dyn_trajectory(
        _chain(), _frames(policy), _thermo(policy, 300.0), base_frame_uid=_sha("b0"), topology_atom_indices=(0,1,2),
        temperature_kelvin=300.0, velocity_seed=plan.case_velocity_seeds[0], policy=policy,
    )
    run = DynVerifyRunRecord(
        run_plan_digest=_sha("run"), relax_verify_run_digest=_sha("relax-run"), deploy_verify_run_digest=_sha("deploy-run"),
        mliap_artifact_path="mliap.pt", mliap_artifact_sha256=_sha("mliap"), lammps_executable_path="lmp",
        lammps_executable_sha256=_sha("lmp"), lammps_arguments=("-k", "on"), policy_digest=policy.policy_digest,
        plan_digest=plan.content_digest, case_metrics=(metric,),
    )
    campaign = DynVerifyCampaignRecord(
        campaign_plan_digest=_sha("campaign"), relax_verify_campaign_digest=relax.content_digest,
        deploy_verify_campaign_digest=_sha("deploy-campaign"), policy=policy, plan=plan, run_records=(run,), stage_context="production",
    )
    assert campaign.passed_run_count == 1
    assert DynVerifyCampaignRecord.from_dict(campaign.to_dict()) == campaign


def test_lammps_runner_materializes_and_parses_short_rollout(tmp_path: Path, monkeypatch) -> None:
    from types import SimpleNamespace
    import mdstats.training_data.dyn_verify as dv

    policy = DynVerifyPolicy(
        temperatures_kelvin=(300.0,), nvt_steps=20, nve_steps=40, sample_interval_steps=10,
        persistent_damage_samples=3,
    )
    executable = tmp_path / "fake-lmp"
    executable.write_text("fake executable", encoding="utf-8")
    mliap = tmp_path / "model.pt"
    mliap.write_bytes(b"mliap")

    def fake_run(command, cwd, **kwargs):
        root = Path(cwd)
        rows = []
        dump = []
        for step in range(0, 61, 10):
            rows.append(f"{step} 300 -11 1 -10")
            dump.extend([
                "ITEM: TIMESTEP", str(step), "ITEM: NUMBER OF ATOMS", "3",
                "ITEM: BOX BOUNDS pp pp pp", "0 10", "0 10", "0 10",
                "ITEM: ATOMS id type x y z fx fy fz",
                "1 1 3.4 5 5 0.01 0 0", "2 2 5.0 5 5 0.01 0 0", "3 1 6.6 5 5 0.01 0 0",
            ])
        (root / "log.lammps").write_text(
            "LAMMPS fake\nStep Temp PotEng KinEng TotEng\n" + "\n".join(rows) + "\nLoop time\n",
            encoding="utf-8",
        )
        (root / "trajectory.dump").write_text("\n".join(dump) + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(dv.subprocess, "run", fake_run)
    metric = dv.run_lammps_mliap_dynamics_case(
        mliap, _chain(), base_frame_uid=_sha("base-runner"), topology_atom_indices=(0, 1, 2),
        temperature_kelvin=300.0, velocity_seed=12345, element_order=("O", "Si"), policy=policy,
        lammps_executable=executable, work_directory=tmp_path / "case",
        expected_executable_sha256=dv._sha256_file(executable),
    )
    assert metric.passed
    assert metric.sample_count == 7
    assert Path(metric.trajectory_path).is_file()
    assert metric.trajectory_sha256 == dv._sha256_file(metric.trajectory_path)
