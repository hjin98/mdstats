"""Relaxation qualification: does minimization preserve the real structure?

Pointwise PES agreement still does not prove that energy minimization under the
deployed force field keeps the framework intact.  Topology safety and geometric
fidelity are therefore judged separately and are *not* traded off: a broken bond
rejects the product even when every averaged geometry error looks small, because
a small average over a collapsed structure is not evidence of correctness.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .components import (
    COMPONENT_RELAXATION,
    ComponentStatus,
    QualificationComponentEvidence,
    build_component_evidence,
)
from .geometry import (
    angle_table,
    atoms_for_frame,
    bond_table,
    displacement_metrics,
    paired_statistics,
    relax_fixed_cell,
)
from .providers import energy_of, forces_of, member_provider, predict_all
from .reference import AuthenticatedReferenceBundle, RELAXED_MODE, geometry_identity


def qualify_relaxation(
    session: Any, bundle: AuthenticatedReferenceBundle
) -> QualificationComponentEvidence:
    binding = session.binding
    policy = binding.specification.component_policy(COMPONENT_RELAXATION)
    plan = session.plan.physical_plan
    scale = float(policy["bond_cutoff_scale"])

    member_results: list[dict[str, Any]] = []
    failures: list[str] = []
    for member in session.publication.members:
        reasons: list[str] = []
        base_rows: list[dict[str, Any]] = []
        for base in plan.bases:
            atoms = atoms_for_frame(session.context, base.frame_uid)
            identity = geometry_identity(atoms, frame_uid=base.frame_uid, mode=RELAXED_MODE)
            observation = bundle.observation(identity)
            reference_positions = observation.relaxed_positions
            if reference_positions is None:
                reasons.append(f"missing_reference_relaxation:{base.frame_uid}")
                continue
            reference_relaxed = atoms.copy()
            reference_relaxed.set_positions(reference_positions)

            with member_provider(session.context, member) as provider:

                def evaluate(candidate: Any, _provider: Any = provider) -> tuple[float, np.ndarray]:
                    prediction = predict_all(session.context, _provider, [candidate])[0]
                    return energy_of(prediction), forces_of(prediction)

                outcome = relax_fixed_cell(
                    atoms,
                    evaluate,
                    maximum_steps=int(policy["maximum_steps"]),
                    force_convergence=float(policy["force_convergence_ev_per_angstrom"]),
                )

            reference_bonds = bond_table(reference_relaxed, cutoff_scale=scale)
            model_bonds = bond_table(outcome.relaxed, cutoff_scale=scale)
            broken = sorted(set(reference_bonds) - set(model_bonds))
            formed = sorted(set(model_bonds) - set(reference_bonds))
            bond_rmse, bond_max, bond_count = paired_statistics(reference_bonds, model_bonds)
            reference_angles = angle_table(reference_relaxed, reference_bonds)
            model_angles = angle_table(outcome.relaxed, model_bonds)
            angle_rmse, angle_max, angle_count = paired_statistics(reference_angles, model_angles)
            rms_displacement, maximum_displacement = displacement_metrics(
                reference_relaxed, outcome.relaxed
            )

            if broken or formed:
                reasons.append(f"protected_topology_changed:{base.frame_uid}")
            if not outcome.converged:
                reasons.append(f"relaxation_not_converged:{base.frame_uid}:{outcome.reason}")
            if rms_displacement > float(policy["rms_displacement_maximum_angstrom"]):
                reasons.append(f"rms_displacement_above_maximum:{base.frame_uid}")
            if maximum_displacement > float(policy["maximum_displacement_maximum_angstrom"]):
                reasons.append(f"maximum_displacement_above_maximum:{base.frame_uid}")
            if bond_count and bond_rmse > float(policy["bond_rmse_maximum_angstrom"]):
                reasons.append(f"bond_rmse_above_maximum:{base.frame_uid}")
            if bond_count and bond_max > float(policy["bond_maximum_error_angstrom"]):
                reasons.append(f"bond_maximum_error_above_maximum:{base.frame_uid}")
            if angle_count and angle_rmse > float(policy["angle_rmse_maximum_degrees"]):
                reasons.append(f"angle_rmse_above_maximum:{base.frame_uid}")
            if angle_count and angle_max > float(policy["angle_maximum_error_degrees"]):
                reasons.append(f"angle_maximum_error_above_maximum:{base.frame_uid}")

            base_rows.append(
                {
                    "frame_uid": base.frame_uid,
                    "converged": bool(outcome.converged),
                    "steps": int(outcome.steps),
                    "convergence_reason": outcome.reason,
                    "final_maximum_force_ev_per_angstrom": float(outcome.final_maximum_force),
                    "broken_bonds": [list(item) for item in broken],
                    "formed_bonds": [list(item) for item in formed],
                    "bond_rmse_angstrom": bond_rmse,
                    "bond_maximum_error_angstrom": bond_max,
                    "compared_bond_count": bond_count,
                    "angle_rmse_degrees": angle_rmse,
                    "angle_maximum_error_degrees": angle_max,
                    "compared_angle_count": angle_count,
                    "rms_displacement_angstrom": rms_displacement,
                    "maximum_displacement_angstrom": maximum_displacement,
                }
            )
        if bool(policy["require_all_bases"]) and len(base_rows) != len(plan.bases):
            reasons.append("incomplete_required_base_coverage")
        member_passed = not reasons
        if not member_passed:
            failures.append(member.member_id)
        member_results.append(
            {
                "member_id": member.member_id,
                "reason_codes": sorted(set(reasons)),
                "bases": base_rows,
                "passed": member_passed,
            }
        )

    status = ComponentStatus.PASSED if not failures else ComponentStatus.REJECTED
    return build_component_evidence(
        component=COMPONENT_RELAXATION,
        binding=binding,
        status=status,
        reason_code=("relaxation_within_policy" if not failures else "relaxation_rejected"),
        detail=(
            ""
            if not failures
            else f"Relaxation qualification rejected the exact publication for members {failures}."
        ),
        metrics={
            "base_count": len(plan.bases),
            "member_count": len(member_results),
            "failed_members": failures,
        },
        payload={
            "physical_plan_digest": plan.content_digest,
            "reference_bundle_digest": bundle.content_digest,
            "members": member_results,
        },
        component_input_digest=session.component_input_digest(
            COMPONENT_RELAXATION, bundle
        ),
    )


__all__ = ["qualify_relaxation"]
