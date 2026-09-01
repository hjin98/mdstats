"""Finite-temperature qualification through the deployed artifact.

The dynamics cases begin at the authenticated reference-relaxed geometry.  The
runtime worker only returns raw samples; all temperature, drift, topology, and
geometry decisions are made here from the frozen specification.  This keeps a
single noisy sample from silently becoming a scientific verdict and makes the
reducer deterministic under serial or bounded concurrent execution.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .._common import digest
from .components import (
    COMPONENT_DYNAMICS,
    ComponentStatus,
    QualificationComponentEvidence,
    build_component_evidence,
)
from .errors import QualificationError
from .geometry import (
    angle_table,
    atoms_for_frame,
    bond_table,
    displacement_metrics,
    minimum_image_delta,
    paired_statistics,
)
from .plan import dynamics_bases
from .reference import AuthenticatedReferenceBundle, RELAXED_MODE, geometry_identity

#: femtoseconds per picosecond, for drift normalization.
_FS_PER_PS = 1000.0


def dynamics_case_identity(
    *,
    binding_digest: str,
    member_id: str,
    frame_uid: str,
    temperature: float,
    seed: int,
    reference_bundle_digest: str | None = None,
    relaxed_geometry_identity: str | None = None,
    pbc: Sequence[bool] = (True, True, True),
) -> str:
    """Identity of one exact deployed dynamics case and its initial geometry.

    Periodicity is part of the identity because two otherwise identical
    geometries executed under different boundary conditions are different
    physical systems, and their evidence must not be interchangeable.
    """

    return digest(
        {
            "schema": "mdstats.qualification-dynamics-case.v3",
            "binding_digest": binding_digest,
            "member_id": member_id,
            "frame_uid": frame_uid,
            "temperature_kelvin": float(temperature),
            "velocity_seed": int(seed),
            "reference_bundle_digest": reference_bundle_digest,
            "relaxed_geometry_identity": relaxed_geometry_identity,
            "pbc": [bool(value) for value in pbc],
        }
    )


def _waiting_for_relaxed_reference(session: Any, detail: str) -> QualificationComponentEvidence:
    return build_component_evidence(
        component=COMPONENT_DYNAMICS,
        binding=session.binding,
        status=ComponentStatus.WAITING_FOR_REFERENCE,
        reason_code="reference_relaxed_geometry_not_supplied",
        detail=detail,
        metrics={"requested_geometry_count": len(session.reference_request.geometries)},
        payload={
            "reference_request_digest": session.reference_request.content_digest,
            "reference_bundle_digest": None,
        },
        component_input_digest=session.component_input_digest(COMPONENT_DYNAMICS, None),
    )


def _protected_indices(policy: Mapping[str, Any], atom_count: int) -> tuple[int, ...]:
    configured = tuple(int(value) for value in policy.get("protected_atom_indices", ()))
    if not configured:
        return tuple(range(atom_count))
    if any(value < 0 or value >= atom_count for value in configured):
        raise QualificationError(
            "The configured dynamics protected_atom_indices contain an out-of-range atom."
        )
    return tuple(sorted(set(configured)))


def _finite_array(value: Any, *, shape: tuple[int, ...] | None = None) -> np.ndarray | None:
    if value is None:
        return None
    array = np.asarray(value, dtype=np.float64)
    if shape is not None and array.shape != shape:
        return None
    if not np.all(np.isfinite(array)):
        return None
    return array


def _sample_atoms(reference: Any, sample: Mapping[str, Any]) -> Any | None:
    # Dynamics evidence is lossless runtime evidence.  Falling back to the
    # reference cell/PBC would make a worker that forgot to emit its geometry
    # look like it had recorded one.
    if "cell_angstrom" not in sample or "pbc" not in sample:
        return None
    positions = _finite_array(sample.get("positions_angstrom"), shape=(len(reference), 3))
    if positions is None:
        return None
    atoms = reference.copy()
    atoms.set_positions(positions)
    pbc = np.asarray(sample["pbc"], dtype=bool)
    if pbc.shape != (3,):
        return None
    atoms.set_pbc(pbc)
    cell = sample.get("cell_angstrom")
    cell_array = _finite_array(cell, shape=(3, 3))
    if cell_array is None:
        return None
    if abs(float(np.linalg.det(cell_array))) <= 1.0e-12 and np.any(pbc):
        return None
    atoms.set_cell(cell_array, scale_atoms=False)
    return atoms


def _minimum_pair_distance(atoms: Any) -> float:
    positions = np.asarray(atoms.get_positions(), dtype=np.float64)
    if len(positions) < 2:
        return float("inf")
    distances: list[float] = []
    for index in range(len(positions) - 1):
        vectors = minimum_image_delta(
            positions[index + 1 :] - positions[index],
            np.asarray(atoms.get_cell(), dtype=np.float64),
            np.asarray(atoms.get_pbc(), dtype=bool),
        )
        distances.extend(float(value) for value in np.linalg.norm(vectors, axis=1))
    return min(distances) if distances else float("inf")


def _reportable(value: Any) -> float | None:
    """Record a measurement, or ``None`` when it was not a finite number.

    A nonfinite observation is a rejection *reason*, and the reason has already
    been recorded by the time this runs.  Immutable evidence is JSON-exact and
    deliberately refuses NaN/inf, so the measurement column carries ``None``
    rather than making an unqualifiable run unserializable.
    """

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _reportable_sample(sample: Mapping[str, Any]) -> dict[str, Any]:
    """Retain one raw sample as evidence, with nonfinite values recorded absent."""

    def convert(value: Any) -> Any:
        if isinstance(value, (float, np.floating)):
            return _reportable(value)
        if isinstance(value, Mapping):
            return {str(key): convert(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [convert(item) for item in value]
        return value

    return {str(key): convert(value) for key, value in sample.items()}


def _protected_mapping(values: Mapping[Any, float], indices: set[int]) -> dict[Any, float]:
    return {
        key: float(value)
        for key, value in values.items()
        if all(int(value) in indices for value in key)
    }


def _raw_samples(observation: Mapping[str, Any], primary: str, fallback: str) -> list[Mapping[str, Any]]:
    values = observation.get(primary)
    if values is None:
        values = observation.get(fallback, ())
    return [item for item in values if isinstance(item, Mapping)]


def _temperature_samples(samples: Sequence[Mapping[str, Any]], *, nve: bool) -> list[float]:
    key = "nve_temperature_kelvin" if nve else "temperature_kelvin"
    result: list[float] = []
    for sample in samples:
        if nve and key not in sample:
            result.append(float("nan"))
            continue
        value = sample.get(key, sample.get("temperature_kelvin"))
        try:
            result.append(float(value))
        except (TypeError, ValueError):
            result.append(float("nan"))
    return result


def protected_geometry_metrics(
    reference: Any,
    sample: Mapping[str, Any],
    reference_bonds: Mapping[tuple[int, int], float],
    reference_angles: Mapping[tuple[int, int, int], float],
    protected: set[int],
    cutoff_scale: float,
) -> dict[str, Any] | None:
    atoms = _sample_atoms(reference, sample)
    if atoms is None:
        return None
    current_bonds = _protected_mapping(bond_table(atoms, cutoff_scale=cutoff_scale), protected)
    current_angles = _protected_mapping(angle_table(atoms, current_bonds), protected)
    protected_bonds = _protected_mapping(reference_bonds, protected)
    protected_angles = _protected_mapping(reference_angles, protected)
    bond_rmse, bond_max, bond_count = paired_statistics(protected_bonds, current_bonds)
    angle_rmse, angle_max, angle_count = paired_statistics(protected_angles, current_angles)
    displacement_rms, displacement_max = displacement_metrics(
        reference, atoms, atom_indices=tuple(sorted(protected))
    )
    forces = _finite_array(sample.get("forces_ev_per_angstrom"), shape=(len(atoms), 3))
    max_force = float(np.max(np.linalg.norm(forces, axis=1))) if forces is not None else float("nan")
    return {
        "positions_angstrom": np.asarray(atoms.get_positions(), dtype=np.float64).tolist(),
        "cell_angstrom": np.asarray(atoms.get_cell(), dtype=np.float64).tolist(),
        "pbc": [bool(value) for value in atoms.get_pbc()],
        "forces_ev_per_angstrom": None if forces is None else forces.tolist(),
        "missing_raw_forces": forces is None,
        "minimum_pair_distance_angstrom": _reportable(_minimum_pair_distance(atoms)),
        "maximum_force_ev_per_angstrom": _reportable(max_force),
        "protected_bonds": [list(key) for key in sorted(current_bonds)],
        "protected_angles": [list(key) for key in sorted(current_angles)],
        "broken_protected_bonds": [
            list(key) for key in sorted(set(protected_bonds) - set(current_bonds))
        ],
        "formed_protected_bonds": [
            list(key) for key in sorted(set(current_bonds) - set(protected_bonds))
        ],
        "protected_bond_rmse_angstrom": bond_rmse,
        "protected_bond_maximum_error_angstrom": bond_max,
        "protected_bond_count": bond_count,
        "protected_angle_rmse_degrees": angle_rmse,
        "protected_angle_maximum_error_degrees": angle_max,
        "protected_angle_count": angle_count,
        "protected_displacement_rms_angstrom": displacement_rms,
        "protected_displacement_maximum_angstrom": displacement_max,
    }


def qualify_dynamics(
    session: Any, bundle: AuthenticatedReferenceBundle | None
) -> QualificationComponentEvidence:
    """Qualify every frozen case from authenticated reference-relaxed bases."""

    if bundle is None:
        return _waiting_for_relaxed_reference(
            session,
            "Dynamics qualification is waiting for the authenticated reference-relaxed "
            "coordinates requested for every physical base.",
        )
    binding = session.binding
    policy = binding.specification.component_policy(COMPONENT_DYNAMICS)
    bases = dynamics_bases(session.plan)
    temperatures = [float(v) for v in policy["temperatures_kelvin"]]
    seeds = [int(v) for v in policy["velocity_seeds"]]
    interval_ps = (
        float(policy["timestep_femtoseconds"])
        * float(policy["sample_interval_steps"])
        / _FS_PER_PS
    )

    cases: list[dict[str, Any]] = []
    relaxed_by_frame: dict[str, Any] = {}
    reference_bonds_by_frame: dict[str, dict[tuple[int, int], float]] = {}
    reference_angles_by_frame: dict[str, dict[tuple[int, int, int], float]] = {}
    protected_by_frame: dict[str, set[int]] = {}
    for base in bases:
        original = atoms_for_frame(session.context, base.frame_uid)
        relaxed_identity = geometry_identity(
            original, frame_uid=base.frame_uid, mode=RELAXED_MODE
        )
        observation = bundle.observation(relaxed_identity)
        relaxed_positions = observation.relaxed_positions
        if relaxed_positions is None:
            return _waiting_for_relaxed_reference(
                session,
                f"Reference bundle is authenticated but has no relaxed coordinates for "
                f"base {base.frame_uid!r}; dynamics cannot fall back to OUTER_MONITOR.",
            )
        if relaxed_positions.shape != (len(original), 3) or not np.all(
            np.isfinite(relaxed_positions)
        ):
            raise QualificationError(
                f"Reference-relaxed coordinates for base {base.frame_uid!r} have the wrong shape."
            )
        relaxed = original.copy()
        relaxed.set_positions(relaxed_positions)
        relaxed_by_frame[base.frame_uid] = relaxed
        protected = set(_protected_indices(policy, len(relaxed)))
        protected_by_frame[base.frame_uid] = protected
        reference_bonds_by_frame[base.frame_uid] = bond_table(
            relaxed, cutoff_scale=float(policy["protected_topology_cutoff_scale"])
        )
        reference_angles_by_frame[base.frame_uid] = angle_table(
            relaxed, reference_bonds_by_frame[base.frame_uid]
        )
        for member in session.publication.members:
            for temperature in temperatures:
                for seed in seeds:
                    cases.append(
                        {
                            "member": member,
                            "frame_uid": base.frame_uid,
                            "temperature_kelvin": temperature,
                            "velocity_seed": seed,
                            "relaxed_geometry_identity": relaxed_identity,
                            "case_identity": dynamics_case_identity(
                                binding_digest=binding.content_digest,
                                member_id=member.member_id,
                                frame_uid=base.frame_uid,
                                temperature=temperature,
                                seed=seed,
                                reference_bundle_digest=bundle.content_digest,
                                relaxed_geometry_identity=relaxed_identity,
                                pbc=tuple(
                                    bool(value) for value in relaxed.get_pbc()
                                ),
                            ),
                        }
                    )

    def execute(case: dict[str, Any]) -> tuple[str, Any]:
        observation = session.run_deployed_dynamics(
            case["member"],
            relaxed_by_frame[case["frame_uid"]],
            temperature_kelvin=case["temperature_kelvin"],
            velocity_seed=case["velocity_seed"],
            case_identity=case["case_identity"],
        )
        return case["case_identity"], observation

    observations = session.map_cases(execute, cases)
    rows_by_member: dict[str, list[dict[str, Any]]] = {
        member.member_id: [] for member in session.publication.members
    }
    reasons_by_member: dict[str, list[str]] = {
        member.member_id: [] for member in session.publication.members
    }

    for case in sorted(cases, key=lambda item: item["case_identity"]):
        identity = case["case_identity"]
        member_id = case["member"].member_id
        reference = relaxed_by_frame[case["frame_uid"]]
        observation = observations[identity]
        warmup = _raw_samples(observation, "nvt_samples", "warmup_samples")
        propagation = _raw_samples(observation, "nve_samples", "propagation_samples")
        case_reasons: list[str] = []
        nvt_temperatures = _temperature_samples(warmup, nve=False)
        nve_temperatures = _temperature_samples(propagation, nve=True)
        nvt_minimum = int(policy["nvt_minimum_samples"])
        nve_minimum = int(policy["nve_minimum_samples"])
        if len(warmup) < nvt_minimum or not nvt_temperatures or not np.all(
            np.isfinite(nvt_temperatures)
        ):
            case_reasons.append("nonfinite_or_incomplete_nvt_temperature")
        elif abs(nvt_temperatures[-1] - case["temperature_kelvin"]) > float(
            policy["nvt_temperature_tolerance_kelvin"]
        ):
            case_reasons.append("nvt_temperature_out_of_tolerance")
        if len(propagation) < nve_minimum or not nve_temperatures or not np.all(
            np.isfinite(nve_temperatures)
        ):
            case_reasons.append("nonfinite_or_incomplete_nve_temperature")
        elif bool(policy["require_nve_temperature"]) and abs(
            float(np.mean(nve_temperatures)) - case["temperature_kelvin"]
        ) > float(policy["nve_temperature_tolerance_kelvin"]):
            case_reasons.append("nve_temperature_out_of_tolerance")

        energy_components: dict[str, list[float]] = {
            key: []
            for key in ("potential_energy_ev", "kinetic_energy_ev", "total_energy_ev")
        }
        for item in propagation:
            for key in energy_components:
                try:
                    energy_components[key].append(float(item[key]))
                except (KeyError, TypeError, ValueError):
                    energy_components[key].append(float("nan"))
        totals = energy_components["total_energy_ev"]
        totals_array = np.asarray(totals, dtype=np.float64)
        components_complete = all(
            len(values) >= nve_minimum and np.all(np.isfinite(values))
            for values in energy_components.values()
        )
        if (
            totals_array.size < nve_minimum
            or not np.all(np.isfinite(totals_array))
            or not components_complete
        ):
            case_reasons.append("nonfinite_nve_energy")
            if not components_complete:
                case_reasons.append("nonfinite_nve_energy_components")
            drift = float("nan")
        else:
            elapsed = interval_ps * (totals_array.size - 1)
            drift = float(
                abs(totals_array[-1] - totals_array[0])
                / max(elapsed, 1.0e-12)
                / max(len(reference), 1)
            )
            if drift > float(policy["nve_energy_drift_maximum_ev_per_atom_per_picosecond"]):
                case_reasons.append("nve_energy_drift_above_maximum")

        reference_bonds = reference_bonds_by_frame[case["frame_uid"]]
        reference_angles = reference_angles_by_frame[case["frame_uid"]]
        protected = protected_by_frame[case["frame_uid"]]
        geometry_rows: list[dict[str, Any]] = []
        topology_run = 0
        persistent_topology = False
        minimum_distance = float("inf")
        maximum_force = 0.0
        missing_raw_geometry = False
        missing_raw_forces = False
        for sample_index, sample in enumerate(propagation):
            metrics = protected_geometry_metrics(
                reference,
                sample,
                reference_bonds,
                reference_angles,
                protected,
                float(policy["protected_topology_cutoff_scale"]),
            )
            if metrics is None:
                missing_raw_geometry = True
                topology_run = 0
                continue
            geometry_rows.append({"sample_index": sample_index, **metrics})
            missing_raw_forces = missing_raw_forces or bool(metrics["missing_raw_forces"])
            minimum_distance = min(minimum_distance, float(metrics["minimum_pair_distance_angstrom"]))
            maximum_force = max(maximum_force, float(metrics["maximum_force_ev_per_angstrom"]))
            changed = bool(metrics["broken_protected_bonds"] or metrics["formed_protected_bonds"])
            topology_run = topology_run + 1 if changed else 0
            if topology_run >= int(policy["minimum_consecutive_topology_violations"]):
                persistent_topology = True
            if float(metrics["protected_displacement_maximum_angstrom"]) > float(
                policy["protected_displacement_maximum_angstrom"]
            ):
                case_reasons.append("protected_displacement_above_maximum")
            if int(metrics["protected_bond_count"]) and (
                float(metrics["protected_bond_rmse_angstrom"])
                > float(policy["protected_bond_rmse_maximum_angstrom"])
                or float(metrics["protected_bond_maximum_error_angstrom"])
                > float(policy["protected_bond_maximum_error_angstrom"])
            ):
                case_reasons.append("protected_bond_degradation_above_maximum")
            if int(metrics["protected_angle_count"]) and (
                float(metrics["protected_angle_rmse_degrees"])
                > float(policy["protected_angle_rmse_maximum_degrees"])
                or float(metrics["protected_angle_maximum_error_degrees"])
                > float(policy["protected_angle_maximum_error_degrees"])
            ):
                case_reasons.append("protected_angle_degradation_above_maximum")
        if missing_raw_geometry:
            case_reasons.append("missing_lossless_nve_geometry")
        if missing_raw_forces:
            case_reasons.append("missing_lossless_nve_forces")
        if bool(policy["require_protected_topology"]) and persistent_topology:
            case_reasons.append("persistent_protected_topology_damage")

        reported_minimum = float(observation.get("minimum_pair_distance_angstrom", minimum_distance))
        minimum_distance = min(minimum_distance, reported_minimum)
        if not np.isfinite(minimum_distance) or minimum_distance < float(
            policy["minimum_pair_distance_angstrom"]
        ):
            case_reasons.append("minimum_pair_distance_below_safety_bound")
        reported_force = float(observation.get("maximum_force_ev_per_angstrom", maximum_force))
        maximum_force = max(maximum_force, reported_force)
        if not np.isfinite(maximum_force) or maximum_force > float(
            policy["maximum_force_ev_per_angstrom"]
        ):
            case_reasons.append("maximum_force_above_safety_bound")
        final_positions = observation.get("final_positions_angstrom")
        if propagation and propagation[-1].get("positions_angstrom") is not None:
            final_positions = propagation[-1]["positions_angstrom"]
        if final_positions is None or _finite_array(
            final_positions, shape=(len(reference), 3)
        ) is None:
            case_reasons.append("missing_final_geometry")
        rows_by_member[member_id].append(
            {
                "case_identity": identity,
                "frame_uid": case["frame_uid"],
                "temperature_kelvin": case["temperature_kelvin"],
                "velocity_seed": case["velocity_seed"],
                "reference_bundle_digest": bundle.content_digest,
                "relaxed_geometry_identity": case["relaxed_geometry_identity"],
                "final_nvt_temperature_kelvin": _reportable(
                    nvt_temperatures[-1] if nvt_temperatures else None
                ),
                "nve_temperature_mean_kelvin": _reportable(
                    np.mean(nve_temperatures) if nve_temperatures else None
                ),
                "nve_energy_drift_ev_per_atom_per_picosecond": _reportable(drift),
                "minimum_pair_distance_angstrom": _reportable(minimum_distance),
                "maximum_force_ev_per_angstrom": _reportable(maximum_force),
                "persistent_topology_damage": persistent_topology,
                "geometry_samples": geometry_rows,
                "nvt_samples": [_reportable_sample(item) for item in warmup],
                "nve_samples": [_reportable_sample(item) for item in propagation],
                "final_positions_angstrom": final_positions,
                "reason_codes": sorted(set(case_reasons)),
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
            "reference_bundle_digest": bundle.content_digest,
            "protected_topology_source": "authenticated_reference_relaxed_bond_graph",
        },
        payload={
            "reference_bundle_digest": bundle.content_digest,
            "members": member_results,
        },
        component_input_digest=session.component_input_digest(COMPONENT_DYNAMICS, bundle),
    )


__all__ = [
    "dynamics_case_identity",
    "protected_geometry_metrics",
    "qualify_dynamics",
]
