"""Finite-temperature dynamics qualification through the deployed artifact.

A potential can be accurate at a minimum and still be unusable in simulation.
This component runs the already deployment-qualified artifact through the real
supported runtime on the same candidate-independent bases, and looks for the
failure modes that matter operationally: runaway or nonfinite temperature, NVE
energy drift, atoms collapsing onto each other, unbounded forces, and persistent
damage to the protected framework topology rather than one noisy sample.

Case identity is a pure function of the frozen plan and policy, so a case means
the same thing regardless of which worker finished first.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .._common import digest
from .components import (
    COMPONENT_DYNAMICS,
    ComponentStatus,
    QualificationComponentEvidence,
    build_component_evidence,
)
from .geometry import atoms_for_frame, bond_table
from .plan import dynamics_bases

#: femtoseconds per picosecond, for drift normalization.
_FS_PER_PS = 1000.0


def dynamics_case_identity(
    *, binding_digest: str, member_id: str, frame_uid: str, temperature: float, seed: int
) -> str:
    return digest(
        {
            "schema": "mdstats.qualification-dynamics-case.v1",
            "binding_digest": binding_digest,
            "member_id": member_id,
            "frame_uid": frame_uid,
            "temperature_kelvin": float(temperature),
            "velocity_seed": int(seed),
        }
    )


def qualify_dynamics(session: Any) -> QualificationComponentEvidence:
    binding = session.binding
    policy = binding.specification.component_policy(COMPONENT_DYNAMICS)
    bases = dynamics_bases(session.plan)
    temperatures = [float(v) for v in policy["temperatures_kelvin"]]
    seeds = [int(v) for v in policy["velocity_seeds"]]
    interval_ps = (
        float(policy["timestep_femtoseconds"]) * float(policy["sample_interval_steps"]) / _FS_PER_PS
    )

    # Phase 1: enumerate every case from the frozen plan.  Execution order and
    # concurrency are chosen afterwards and cannot affect what a case *is*.
    cases: list[dict[str, Any]] = []
    atoms_by_frame: dict[str, Any] = {}
    reference_bonds_by_frame: dict[str, dict[tuple[int, int], float]] = {}
    for base in bases:
        atoms = atoms_for_frame(session.context, base.frame_uid)
        atoms_by_frame[base.frame_uid] = atoms
        reference_bonds_by_frame[base.frame_uid] = bond_table(atoms, cutoff_scale=1.20)
    for member in session.publication.members:
        for base in bases:
            for temperature in temperatures:
                for seed in seeds:
                    cases.append(
                        {
                            "member": member,
                            "frame_uid": base.frame_uid,
                            "temperature_kelvin": temperature,
                            "velocity_seed": seed,
                            "case_identity": dynamics_case_identity(
                                binding_digest=binding.content_digest,
                                member_id=member.member_id,
                                frame_uid=base.frame_uid,
                                temperature=temperature,
                                seed=seed,
                            ),
                        }
                    )

    def execute(case: dict[str, Any]) -> tuple[str, Any]:
        observation = session.run_deployed_dynamics(
            case["member"],
            atoms_by_frame[case["frame_uid"]],
            temperature_kelvin=case["temperature_kelvin"],
            velocity_seed=case["velocity_seed"],
            case_identity=case["case_identity"],
        )
        return case["case_identity"], observation

    observations = session.map_cases(execute, cases)

    # Phase 2: reduce deterministically.  The reduction reads only the frozen
    # policy and the observations, keyed by identity, so worker completion order
    # is invisible in the evidence.
    rows_by_member: dict[str, list[dict[str, Any]]] = {
        member.member_id: [] for member in session.publication.members
    }
    reasons_by_member: dict[str, list[str]] = {
        member.member_id: [] for member in session.publication.members
    }
    for case in sorted(cases, key=lambda item: item["case_identity"]):
        identity = case["case_identity"]
        member_id = case["member"].member_id
        atoms = atoms_by_frame[case["frame_uid"]]
        observation = observations[identity]
        warmup = [float(item["temperature_kelvin"]) for item in observation["warmup_samples"]]
        propagation = observation["propagation_samples"]
        totals = np.asarray(
            [float(item["total_energy_ev"]) for item in propagation], dtype=np.float64
        )
        case_reasons: list[str] = []
        if not warmup or not np.all(np.isfinite(warmup)):
            case_reasons.append("nonfinite_nvt_temperature")
        elif abs(warmup[-1] - case["temperature_kelvin"]) > float(
            policy["nvt_temperature_tolerance_kelvin"]
        ):
            case_reasons.append("nvt_temperature_out_of_tolerance")
        if totals.size < 2 or not np.all(np.isfinite(totals)):
            case_reasons.append("nonfinite_nve_energy")
            drift = float("nan")
        else:
            elapsed = interval_ps * (totals.size - 1)
            drift = float(
                abs(totals[-1] - totals[0]) / max(elapsed, 1.0e-12) / max(len(atoms), 1)
            )
            if drift > float(policy["nve_energy_drift_maximum_ev_per_atom_per_picosecond"]):
                case_reasons.append("nve_energy_drift_above_maximum")
        minimum_distance = float(observation["minimum_pair_distance_angstrom"])
        if not np.isfinite(minimum_distance) or minimum_distance < float(
            policy["minimum_pair_distance_angstrom"]
        ):
            case_reasons.append("minimum_pair_distance_below_safety_bound")
        maximum_force = float(observation["maximum_force_ev_per_angstrom"])
        if not np.isfinite(maximum_force) or maximum_force > float(
            policy["maximum_force_ev_per_angstrom"]
        ):
            case_reasons.append("maximum_force_above_safety_bound")
        final = atoms.copy()
        final.set_positions(
            np.asarray(observation["final_positions_angstrom"], dtype=np.float64)
        )
        broken = sorted(
            set(reference_bonds_by_frame[case["frame_uid"]])
            - set(bond_table(final, cutoff_scale=1.20))
        )
        if broken:
            case_reasons.append("protected_topology_damage")
        rows_by_member[member_id].append(
            {
                "case_identity": identity,
                "frame_uid": case["frame_uid"],
                "temperature_kelvin": case["temperature_kelvin"],
                "velocity_seed": case["velocity_seed"],
                "final_nvt_temperature_kelvin": (warmup[-1] if warmup else float("nan")),
                "nve_energy_drift_ev_per_atom_per_picosecond": drift,
                "minimum_pair_distance_angstrom": minimum_distance,
                "maximum_force_ev_per_angstrom": maximum_force,
                "broken_bond_count": len(broken),
                "reason_codes": case_reasons,
                "passed": not case_reasons,
            }
        )
        reasons_by_member[member_id].extend(
            f"{code}:{identity[:12]}" for code in case_reasons
        )

    expected_cases = len(bases) * len(temperatures) * len(seeds)
    member_results: list[dict[str, Any]] = []
    failures: list[str] = []
    for member in session.publication.members:
        reasons = list(reasons_by_member[member.member_id])
        rows = rows_by_member[member.member_id]
        if bool(policy["require_all_cases"]) and len(rows) != expected_cases:
            reasons.append("incomplete_required_case_coverage")
        member_passed = not reasons
        if not member_passed:
            failures.append(member.member_id)
        member_results.append(
            {
                "member_id": member.member_id,
                "reason_codes": sorted(set(reasons)),
                "cases": sorted(rows, key=lambda row: row["case_identity"]),
                "passed": member_passed,
            }
        )

    status = ComponentStatus.PASSED if not failures else ComponentStatus.REJECTED
    return build_component_evidence(
        component=COMPONENT_DYNAMICS,
        binding=binding,
        status=status,
        reason_code=("dynamics_within_policy" if not failures else "dynamics_rejected"),
        detail=(
            ""
            if not failures
            else f"Dynamics qualification rejected the exact publication for members {failures}."
        ),
        metrics={
            "case_count": sum(len(item["cases"]) for item in member_results),
            "member_count": len(member_results),
            "failed_members": failures,
        },
        payload={"members": member_results},
    )


__all__ = ["dynamics_case_identity", "qualify_dynamics"]
