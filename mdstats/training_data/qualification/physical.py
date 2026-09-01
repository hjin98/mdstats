"""Local PES qualification against matched external reference evidence.

A good static force RMSE is compatible with a potential that has the wrong local
curvature or, worse, a non-restoring response.  This component therefore probes
deterministic symmetric displacement modes and checks three separate things that
a single error metric cannot separate: pointwise force agreement, the *sign* of
the restoring response, and the second-order stiffness/curvature.  Every mode is
matched ``+/-`` against the same external reference protocol, so an asymmetric
or missing pair fails closed rather than being averaged away.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .components import (
    COMPONENT_PHYSICAL_PES,
    ComponentStatus,
    QualificationComponentEvidence,
    build_component_evidence,
)
from .errors import QualificationError
from .geometry import atoms_for_frame, displaced_atoms, strained_atoms
from .plan import PhysicalValidationBase
from .providers import energy_of, forces_of, member_provider, predict_all, stress_of
from .reference import (
    AuthenticatedReferenceBundle,
    BASE_MODE,
    geometry_identity,
    mode_name,
    strain_mode_name,
)

_AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


def _amplitude_pairs(base: PhysicalValidationBase) -> tuple[float, ...]:
    positive = sorted(value for value in base.amplitudes_angstrom if value > 0.0)
    for value in positive:
        if -value not in base.amplitudes_angstrom:
            raise QualificationError(
                "The frozen physical plan contains an unmatched displacement "
                "amplitude; every mode must have a matched +/- reference pair."
            )
    return tuple(positive)


def qualify_physical_pes(
    session: Any, bundle: AuthenticatedReferenceBundle
) -> QualificationComponentEvidence:
    binding = session.binding
    policy = binding.specification.component_policy(COMPONENT_PHYSICAL_PES)
    plan = session.plan.physical_plan
    require_all = bool(policy["require_all_modes"])
    floor = float(policy["resolution_floor_ev"])
    # Resolve the exact physical claim cohort once as input material, then make
    # one immutable member-scoped decision per published member. Reference
    # availability is deliberately separate from applicability: missing
    # external stress cannot turn an applicable claim into a pass.
    (
        claim_geometries,
        claim_frames,
        exact_reference,
        exact_reference_by_geometry,
        claim_geometry_digest,
    ) = session._physical_stress_inputs(bundle)

    member_results: list[dict[str, Any]] = []
    failures: list[str] = []
    for member in session.publication.members:
        capability = session.stress_capability(
            claim_geometries,
            probe=claim_frames,
            member=member,
            component=COMPONENT_PHYSICAL_PES,
            claim_kind="physical",
            reference_stress_available=exact_reference,
            reference_stress_available_by_geometry=exact_reference_by_geometry,
            geometry_or_cohort_digest=claim_geometry_digest,
        )
        stress_applicable = capability.applicable
        stress_required = capability.required
        reasons: list[str] = []
        squared_error = 0.0
        counted = 0
        stiffness_rows: list[dict[str, Any]] = []
        strain_rows: list[dict[str, Any]] = []
        stress_rows: list[dict[str, Any]] = []
        stress_compared = 0
        stress_unavailable = 0
        claim_offset = 0
        for base in plan.bases:
            atoms = atoms_for_frame(session.context, base.frame_uid)
            geometries: list[Any] = [atoms]
            identities: list[str] = [
                geometry_identity(atoms, frame_uid=base.frame_uid, mode=BASE_MODE)
            ]
            labels: list[tuple[int, str, float]] = [(-1, "x", 0.0)]
            for atom_index, axis, amplitude in base.modes():
                moved = displaced_atoms(
                    atoms, atom_index=atom_index, axis=axis, amplitude=amplitude
                )
                geometries.append(moved)
                identities.append(
                    geometry_identity(
                        moved, frame_uid=base.frame_uid, mode=mode_name(atom_index, axis, amplitude)
                    )
                )
                labels.append((atom_index, axis, amplitude))
            strain_labels: list[float] = []
            strain_claim_indices: dict[float, int] = {}
            for magnitude in plan.strain_magnitudes:
                strained = strained_atoms(atoms, magnitude)
                geometries.append(strained)
                identities.append(
                    geometry_identity(
                        strained, frame_uid=base.frame_uid, mode=strain_mode_name(magnitude)
                    )
                )
                labels.append((-2, "strain", float(magnitude)))
                strain_labels.append(float(magnitude))
                strain_claim_indices[float(magnitude)] = claim_offset + len(labels) - 1
            with member_provider(session.context, member) as provider:
                predictions = predict_all(session.context, provider, geometries)
            model_energy = {
                label: energy_of(prediction) for label, prediction in zip(labels, predictions)
            }
            model_forces = {
                label: forces_of(prediction) for label, prediction in zip(labels, predictions)
            }
            model_stress = {
                label: stress_of(prediction) for label, prediction in zip(labels, predictions)
            }
            reference = {
                label: bundle.observation(identity)
                for label, identity in zip(labels, identities)
            }
            for label_index, label in enumerate(labels):
                claim_index = claim_offset + label_index
                geometry_stress_applicable = capability.geometry_is_applicable(claim_index)
                error = model_forces[label] - reference[label].forces
                if not np.all(np.isfinite(error)):
                    reasons.append(f"nonfinite_force:{base.frame_uid}:{label}")
                    continue
                squared_error += float(np.sum(error**2))
                counted += error.size
                if geometry_stress_applicable:
                    expected_stress = reference[label].stress
                    observed_stress = model_stress[label]
                    reference_stress_available = capability.reference_stress_is_available(
                        claim_index
                    )
                    if (
                        not reference_stress_available
                        or expected_stress is None
                        or observed_stress is None
                    ):
                        stress_unavailable += 1
                        stress_rows.append(
                            {
                                "frame_uid": base.frame_uid,
                                "label": list(label),
                                "capability": "unavailable",
                                "applicable": True,
                                "reference_stress_available": reference_stress_available,
                                "maximum_stress_tolerance_excess_ev_per_angstrom3": None,
                                "passed": False,
                            }
                        )
                        reasons.append(f"missing_stress:{base.frame_uid}:{label}")
                    else:
                        tolerance = float(policy["stress_atol_ev_per_angstrom3"]) + float(
                            policy["stress_rtol"]
                        ) * np.abs(expected_stress)
                        excess = float(
                            np.max(np.abs(observed_stress - expected_stress) - tolerance)
                        )
                        stress_compared += 1
                        stress_rows.append(
                            {
                                "frame_uid": base.frame_uid,
                                "label": list(label),
                                "capability": "authenticated",
                                "applicable": True,
                                "reference_stress_available": True,
                                "maximum_stress_tolerance_excess_ev_per_angstrom3": excess,
                                "passed": excess <= 0.0,
                            }
                        )
                        if excess > 0.0:
                            reasons.append(f"stress_out_of_tolerance:{base.frame_uid}:{label}")

            claim_offset += len(labels)

            # Deterministic isotropic strain response for periodic systems.
            # Volumetric curvature is the strain analogue of the displacement
            # stiffness: it must be positive and must track the reference,
            # otherwise the potential does not resist compression correctly.
            for magnitude in sorted(value for value in strain_labels if value > 0.0):
                plus = (-2, "strain", magnitude)
                minus = (-2, "strain", -magnitude)
                if plus not in model_energy or minus not in model_energy:
                    reasons.append(f"missing_strain_mode_pair:{base.frame_uid}:{magnitude}")
                    continue
                model_strain_curvature = (
                    model_energy[plus] + model_energy[minus] - 2.0 * model_energy[(-1, "x", 0.0)]
                ) / (magnitude**2)
                reference_strain_curvature = (
                    reference[plus].energy_ev
                    + reference[minus].energy_ev
                    - 2.0 * reference[(-1, "x", 0.0)].energy_ev
                ) / (magnitude**2)
                strain_rows.append(
                    {
                        "frame_uid": base.frame_uid,
                        "strain_magnitude": float(magnitude),
                        "model_volumetric_curvature_ev": model_strain_curvature,
                        "reference_volumetric_curvature_ev": reference_strain_curvature,
                    }
                )
                if bool(policy["require_restoring_sign"]) and not model_strain_curvature > 0.0:
                    reasons.append(f"non_restoring_strain_response:{base.frame_uid}:{magnitude}")
                scale = abs(reference_strain_curvature)
                if scale * magnitude * magnitude > floor:
                    relative = abs(model_strain_curvature - reference_strain_curvature) / scale
                    if relative > float(policy["stiffness_relative_tolerance"]):
                        reasons.append(
                            f"strain_curvature_out_of_tolerance:{base.frame_uid}:{magnitude}"
                        )
                if bool(policy.get("strain_response_required", False)):
                    plus_claim_index = strain_claim_indices.get(float(magnitude))
                    minus_claim_index = strain_claim_indices.get(float(-magnitude))
                    if (
                        plus_claim_index is None
                        or minus_claim_index is None
                        or not capability.geometry_is_applicable(plus_claim_index)
                        or not capability.geometry_is_applicable(minus_claim_index)
                    ):
                        # An open/non-periodic strain is outside the Cauchy
                        # stress domain.  The exact applicability decision is
                        # already retained in the claim-scoped capability; it
                        # must not be turned into a fake missing-stress failure.
                        continue
                    model_plus_stress = model_stress.get(plus)
                    model_minus_stress = model_stress.get(minus)
                    reference_plus_stress = reference[plus].stress
                    reference_minus_stress = reference[minus].stress
                    if (
                        model_plus_stress is None
                        or model_minus_stress is None
                        or reference_plus_stress is None
                        or reference_minus_stress is None
                    ):
                        reasons.append(
                            f"missing_strain_stress_response:{base.frame_uid}:{magnitude}"
                        )
                    else:
                        response_error = max(
                            float(
                                np.max(
                                    np.abs(model_plus_stress - reference_plus_stress)
                                )
                            ),
                            float(
                                np.max(
                                    np.abs(model_minus_stress - reference_minus_stress)
                                )
                            ),
                        )
                        strain_rows[-1]["stress_response_maximum_error_ev_per_angstrom3"] = (
                            response_error
                        )
                        response_scale = max(
                            float(np.max(np.abs(reference_plus_stress))),
                            float(np.max(np.abs(reference_minus_stress))),
                        )
                        response_tolerance = float(
                            policy["stress_atol_ev_per_angstrom3"]
                        ) + float(policy["stress_rtol"]) * response_scale
                        response_excess = response_error - response_tolerance
                        strain_rows[-1][
                            "stress_response_tolerance_excess_ev_per_angstrom3"
                        ] = response_excess
                        if response_excess > 0.0:
                            reasons.append(
                                f"strain_stress_response_out_of_tolerance:{base.frame_uid}:{magnitude}"
                            )

            for atom_index in base.displaced_atom_indices:
                for axis in base.axes:
                    component = _AXIS_INDEX[axis]
                    for amplitude in _amplitude_pairs(base):
                        plus = (atom_index, axis, amplitude)
                        minus = (atom_index, axis, -amplitude)
                        if plus not in model_energy or minus not in model_energy:
                            reasons.append(f"missing_mode_pair:{base.frame_uid}:{atom_index}:{axis}")
                            continue
                        model_plus = float(model_forces[plus][atom_index, component])
                        model_minus = float(model_forces[minus][atom_index, component])
                        reference_plus = float(reference[plus].forces[atom_index, component])
                        reference_minus = float(reference[minus].forces[atom_index, component])
                        model_stiffness = -(model_plus - model_minus) / (2.0 * amplitude)
                        reference_stiffness = -(reference_plus - reference_minus) / (2.0 * amplitude)
                        model_curvature = (
                            model_energy[plus] + model_energy[minus] - 2.0 * model_energy[(-1, "x", 0.0)]
                        ) / (amplitude**2)
                        reference_curvature = (
                            reference[plus].energy_ev
                            + reference[minus].energy_ev
                            - 2.0 * reference[(-1, "x", 0.0)].energy_ev
                        ) / (amplitude**2)
                        row = {
                            "frame_uid": base.frame_uid,
                            "atom_index": int(atom_index),
                            "axis": axis,
                            "amplitude_angstrom": float(amplitude),
                            "model_stiffness_ev_per_angstrom2": model_stiffness,
                            "reference_stiffness_ev_per_angstrom2": reference_stiffness,
                            "model_curvature_ev_per_angstrom2": model_curvature,
                            "reference_curvature_ev_per_angstrom2": reference_curvature,
                        }
                        stiffness_rows.append(row)
                        # A restoring response is a *positive local stiffness*:
                        # the central-difference force change must oppose the
                        # displacement.  The absolute force at the base geometry
                        # is irrelevant, because a validation base is not
                        # required to sit at a minimum.
                        if bool(policy["require_restoring_sign"]) and not model_stiffness > 0.0:
                            reasons.append(
                                f"non_restoring_response:{base.frame_uid}:{atom_index}:{axis}"
                            )
                        if model_curvature < float(policy["energy_curvature_minimum_ev_per_angstrom2"]):
                            reasons.append(
                                f"energy_curvature_below_minimum:{base.frame_uid}:{atom_index}:{axis}"
                            )
                        scale = abs(reference_stiffness)
                        if scale * amplitude * amplitude > floor:
                            relative = abs(model_stiffness - reference_stiffness) / scale
                            if relative > float(policy["stiffness_relative_tolerance"]):
                                reasons.append(
                                    f"stiffness_out_of_tolerance:{base.frame_uid}:{atom_index}:{axis}"
                                )
        rmse = float(np.sqrt(squared_error / counted)) if counted else float("nan")
        if not counted:
            reasons.append("no_comparable_force_components")
        elif rmse > float(policy["force_component_rmse_maximum_ev_per_angstrom"]):
            reasons.append("force_component_rmse_above_maximum")
        member_passed = not reasons if require_all else not [
            item for item in reasons if not item.startswith("missing_mode_pair")
        ]
        if not member_passed:
            failures.append(member.member_id)
        member_results.append(
            {
                "member_id": member.member_id,
                "force_component_rmse_ev_per_angstrom": rmse,
                "reason_codes": sorted(set(reasons)),
                "modes": stiffness_rows,
                "strain_modes": strain_rows,
                "stress": stress_rows,
                "stress_applicable": stress_applicable,
                "stress_required": stress_required,
                "stress_capability_digest": capability.content_digest,
                "stress_capability_reasons": list(capability.reason_codes),
                "stress_capability_decision": capability.to_dict(),
                "stress_compared_configurations": stress_compared,
                "stress_unavailable_configurations": stress_unavailable,
                "stress_capability": (
                    "authenticated"
                    if stress_applicable and stress_unavailable == 0
                    else "unavailable"
                    if stress_applicable
                    else "not_applicable"
                ),
                "passed": member_passed,
            }
        )

    status = ComponentStatus.PASSED if not failures else ComponentStatus.REJECTED
    capability_set_digest = session.stress_capability_digest(
        COMPONENT_PHYSICAL_PES, bundle
    )
    return build_component_evidence(
        component=COMPONENT_PHYSICAL_PES,
        binding=binding,
        status=status,
        reason_code=("local_pes_within_policy" if not failures else "local_pes_rejected"),
        detail=(
            ""
            if not failures
            else f"Local PES qualification rejected the exact publication for members {failures}."
        ),
        metrics={
            "base_count": len(plan.bases),
            "member_count": len(member_results),
            "failed_members": failures,
            "stress_applicable": any(
                bool(row["stress_applicable"]) for row in member_results
            ),
            "stress_required": any(
                bool(row["stress_required"]) for row in member_results
            ),
            "stress_capability_reasons": sorted(
                {
                    reason
                    for row in member_results
                    for reason in row.get("stress_capability_reasons", ())
                }
            ),
            "stress_compared_configurations": sum(
                int(row["stress_compared_configurations"]) for row in member_results
            ),
            "stress_unavailable_configurations": sum(
                int(row["stress_unavailable_configurations"]) for row in member_results
            ),
            "stress_unavailable_members": [
                row["member_id"]
                for row in member_results
                if int(row["stress_unavailable_configurations"]) > 0
            ],
        },
        payload={
            "physical_plan_digest": plan.content_digest,
            "reference_bundle_digest": bundle.content_digest,
            "reference_protocol_identity": bundle.protocol_identity,
            "stress_capabilities": {
                row["member_id"]: row["stress_capability_decision"]
                for row in member_results
            },
            "stress_capability_set_digest": capability_set_digest,
            "members": member_results,
        },
        component_input_digest=session.component_input_digest(
            COMPONENT_PHYSICAL_PES, bundle
        ),
    )


__all__ = ["qualify_physical_pes"]
