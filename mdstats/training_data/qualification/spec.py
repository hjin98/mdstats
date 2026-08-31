"""Resolution of the frozen qualification specification from configuration.

Every threshold, cohort bound, tolerance, and required-component decision is
resolved here, before any product outcome exists.  That ordering is the whole
point: a threshold chosen after seeing a failure is not a threshold, and the
resolved specification digest is what makes "the policy did not move" checkable
rather than merely asserted.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .._common import TrainingDataInputError
from .components import (
    ALL_COMPONENTS,
    COMPONENT_CALIBRATION,
    COMPONENT_DEPLOYMENT_PARITY,
    COMPONENT_DYNAMICS,
    COMPONENT_LOCKED_TEST,
    COMPONENT_PHYSICAL_PES,
    COMPONENT_RELAXATION,
)
from .identity import QUALIFICATION_SPEC_REVISION, QualificationSpecIdentity

#: Components a newly initialized campaign must satisfy before release.
DEFAULT_REQUIRED_COMPONENTS = (
    COMPONENT_DEPLOYMENT_PARITY,
    COMPONENT_PHYSICAL_PES,
    COMPONENT_RELAXATION,
    COMPONENT_DYNAMICS,
    COMPONENT_CALIBRATION,
)
DEFAULT_OPTIONAL_COMPONENTS: tuple[str, ...] = ()

CALIBRATION_METHOD_AUTO = "auto"
CALIBRATION_METHOD_COMMITTEE_VARIANCE = "committee_variance_scaling"
CALIBRATION_METHOD_NONE = "none"
_CALIBRATION_METHODS = (
    CALIBRATION_METHOD_AUTO,
    CALIBRATION_METHOD_COMMITTEE_VARIANCE,
    CALIBRATION_METHOD_NONE,
)


def _table(cfg: Mapping[str, Any], *path: str) -> Mapping[str, Any]:
    node: Any = cfg
    for key in path:
        if not isinstance(node, Mapping):
            return {}
        node = node.get(key, {})
    return node if isinstance(node, Mapping) else {}


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    result = int(value)
    if result < minimum:
        raise TrainingDataInputError(f"[qualification] {name} must be >= {minimum}.")
    return result


def _positive_float(value: Any, *, name: str, allow_zero: bool = False) -> float:
    result = float(value)
    if not (result > 0.0 or (allow_zero and result == 0.0)):
        raise TrainingDataInputError(
            f"[qualification] {name} must be positive{' or zero' if allow_zero else ''}."
        )
    return result


def _float_tuple(values: Any, *, name: str) -> tuple[float, ...]:
    result = tuple(float(v) for v in values)
    if len(set(result)) != len(result):
        raise TrainingDataInputError(f"[qualification] {name} must be unique.")
    return result


def _int_tuple(values: Any, *, name: str) -> tuple[int, ...]:
    result = tuple(int(v) for v in values)
    if not result or len(set(result)) != len(result):
        raise TrainingDataInputError(f"[qualification] {name} must be non-empty and unique.")
    return result


def _components(values: Any, *, name: str) -> tuple[str, ...]:
    result = tuple(str(v) for v in values)
    unknown = sorted(set(result) - set(ALL_COMPONENTS))
    if unknown:
        raise TrainingDataInputError(f"[qualification] {name} names unknown components {unknown}.")
    if COMPONENT_LOCKED_TEST in result:
        raise TrainingDataInputError(
            "The locked interpolation test is never a `qualification run` component; "
            "it is reachable only through explicit one-shot activation."
        )
    return result


def resolve_qualification_spec_identity(cfg: Mapping[str, Any]) -> QualificationSpecIdentity:
    """Freeze the complete qualification policy from campaign configuration."""

    section = _table(cfg, "qualification")
    required = _components(
        section.get("required_components", DEFAULT_REQUIRED_COMPONENTS),
        name="required_components",
    )
    optional = _components(
        section.get("optional_components", DEFAULT_OPTIONAL_COMPONENTS),
        name="optional_components",
    )

    deployment = _table(section, "deployment_parity")
    physical = _table(section, "physical")
    relaxation = _table(section, "relaxation")
    dynamics = _table(section, "dynamics")
    calibration = _table(section, "calibration")
    locked = _table(section, "locked")

    calibration_method = str(calibration.get("method", CALIBRATION_METHOD_AUTO))
    if calibration_method not in _CALIBRATION_METHODS:
        raise TrainingDataInputError(
            f"[qualification.calibration] method must be one of {list(_CALIBRATION_METHODS)}."
        )

    amplitudes = _float_tuple(
        physical.get("displacement_amplitudes_angstrom", (-0.05, -0.02, 0.02, 0.05)),
        name="physical.displacement_amplitudes_angstrom",
    )
    if not amplitudes or any(value == 0.0 for value in amplitudes):
        raise TrainingDataInputError(
            "[qualification.physical] displacement amplitudes must be non-empty and nonzero."
        )
    positive = sorted(value for value in amplitudes if value > 0.0)
    negative = sorted(-value for value in amplitudes if value < 0.0)
    if positive != negative:
        raise TrainingDataInputError(
            "[qualification.physical] displacement amplitudes must be symmetric so that "
            "every mode has a matched +/- reference pair."
        )

    strains = _float_tuple(
        physical.get("strain_magnitudes", ()), name="physical.strain_magnitudes"
    )
    if strains:
        if any(value == 0.0 for value in strains):
            raise TrainingDataInputError(
                "[qualification.physical] strain magnitudes must be nonzero."
            )
        if sorted(value for value in strains if value > 0.0) != sorted(
            -value for value in strains if value < 0.0
        ):
            raise TrainingDataInputError(
                "[qualification.physical] strain magnitudes must be symmetric so that "
                "every strain mode has a matched +/- reference pair."
            )

    payload: dict[str, Any] = {
        COMPONENT_DEPLOYMENT_PARITY: {
            "probe_configuration_count": _positive_int(
                deployment.get("probe_configurations", 4), name="deployment_parity.probe_configurations"
            ),
            "energy_atol_ev_per_atom": _positive_float(
                deployment.get("energy_atol_ev_per_atom", 1.0e-4),
                name="deployment_parity.energy_atol_ev_per_atom",
            ),
            "force_atol_ev_per_angstrom": _positive_float(
                deployment.get("force_atol_ev_per_angstrom", 1.0e-3),
                name="deployment_parity.force_atol_ev_per_angstrom",
            ),
            "force_rtol": _positive_float(
                deployment.get("force_rtol", 1.0e-3), name="deployment_parity.force_rtol"
            ),
            "require_deployed_runtime": bool(deployment.get("require_deployed_runtime", True)),
        },
        COMPONENT_PHYSICAL_PES: {
            "base_count": _positive_int(physical.get("base_count", 4), name="physical.base_count"),
            "displaced_atoms_per_base": _positive_int(
                physical.get("displaced_atoms_per_base", 2),
                name="physical.displaced_atoms_per_base",
            ),
            "displacement_amplitudes_angstrom": list(sorted(amplitudes)),
            "strain_magnitudes": list(sorted(strains)),
            "require_all_modes": bool(physical.get("require_all_modes", True)),
            "force_component_rmse_maximum_ev_per_angstrom": _positive_float(
                physical.get("force_component_rmse_maximum_ev_per_angstrom", 0.20),
                name="physical.force_component_rmse_maximum_ev_per_angstrom",
            ),
            "energy_curvature_minimum_ev_per_angstrom2": _positive_float(
                physical.get("energy_curvature_minimum_ev_per_angstrom2", 0.0),
                name="physical.energy_curvature_minimum_ev_per_angstrom2",
                allow_zero=True,
            ),
            "stiffness_relative_tolerance": _positive_float(
                physical.get("stiffness_relative_tolerance", 0.50),
                name="physical.stiffness_relative_tolerance",
            ),
            "resolution_floor_ev": _positive_float(
                physical.get("resolution_floor_ev", 1.0e-6), name="physical.resolution_floor_ev"
            ),
            "require_restoring_sign": bool(physical.get("require_restoring_sign", True)),
        },
        COMPONENT_RELAXATION: {
            "maximum_steps": _positive_int(
                relaxation.get("maximum_steps", 50), name="relaxation.maximum_steps"
            ),
            "force_convergence_ev_per_angstrom": _positive_float(
                relaxation.get("force_convergence_ev_per_angstrom", 0.05),
                name="relaxation.force_convergence_ev_per_angstrom",
            ),
            "rms_displacement_maximum_angstrom": _positive_float(
                relaxation.get("rms_displacement_maximum_angstrom", 0.30),
                name="relaxation.rms_displacement_maximum_angstrom",
            ),
            "maximum_displacement_maximum_angstrom": _positive_float(
                relaxation.get("maximum_displacement_maximum_angstrom", 0.60),
                name="relaxation.maximum_displacement_maximum_angstrom",
            ),
            "bond_rmse_maximum_angstrom": _positive_float(
                relaxation.get("bond_rmse_maximum_angstrom", 0.10),
                name="relaxation.bond_rmse_maximum_angstrom",
            ),
            "bond_maximum_error_angstrom": _positive_float(
                relaxation.get("bond_maximum_error_angstrom", 0.25),
                name="relaxation.bond_maximum_error_angstrom",
            ),
            "angle_rmse_maximum_degrees": _positive_float(
                relaxation.get("angle_rmse_maximum_degrees", 8.0),
                name="relaxation.angle_rmse_maximum_degrees",
            ),
            "angle_maximum_error_degrees": _positive_float(
                relaxation.get("angle_maximum_error_degrees", 20.0),
                name="relaxation.angle_maximum_error_degrees",
            ),
            "bond_cutoff_scale": _positive_float(
                relaxation.get("bond_cutoff_scale", 1.20), name="relaxation.bond_cutoff_scale"
            ),
            "require_all_bases": bool(relaxation.get("require_all_bases", True)),
        },
        COMPONENT_DYNAMICS: {
            "temperatures_kelvin": list(
                sorted(_float_tuple(dynamics.get("temperatures_kelvin", (300.0,)), name="dynamics.temperatures_kelvin"))
            ),
            "velocity_seeds": list(
                _int_tuple(dynamics.get("velocity_seeds", (20260831,)), name="dynamics.velocity_seeds")
            ),
            "timestep_femtoseconds": _positive_float(
                dynamics.get("timestep_femtoseconds", 0.5), name="dynamics.timestep_femtoseconds"
            ),
            "warmup_steps": _positive_int(dynamics.get("warmup_steps", 200), name="dynamics.warmup_steps"),
            "propagation_steps": _positive_int(
                dynamics.get("propagation_steps", 200), name="dynamics.propagation_steps"
            ),
            "sample_interval_steps": _positive_int(
                dynamics.get("sample_interval_steps", 50), name="dynamics.sample_interval_steps"
            ),
            "thermostat_damping_femtoseconds": _positive_float(
                dynamics.get("thermostat_damping_femtoseconds", 50.0),
                name="dynamics.thermostat_damping_femtoseconds",
            ),
            "nvt_temperature_tolerance_kelvin": _positive_float(
                dynamics.get("nvt_temperature_tolerance_kelvin", 150.0),
                name="dynamics.nvt_temperature_tolerance_kelvin",
            ),
            "nve_energy_drift_maximum_ev_per_atom_per_picosecond": _positive_float(
                dynamics.get("nve_energy_drift_maximum_ev_per_atom_per_picosecond", 0.01),
                name="dynamics.nve_energy_drift_maximum_ev_per_atom_per_picosecond",
            ),
            "minimum_pair_distance_angstrom": _positive_float(
                dynamics.get("minimum_pair_distance_angstrom", 0.80),
                name="dynamics.minimum_pair_distance_angstrom",
            ),
            "maximum_force_ev_per_angstrom": _positive_float(
                dynamics.get("maximum_force_ev_per_angstrom", 100.0),
                name="dynamics.maximum_force_ev_per_angstrom",
            ),
            "base_count": _positive_int(dynamics.get("base_count", 1), name="dynamics.base_count"),
            "require_all_cases": bool(dynamics.get("require_all_cases", True)),
        },
        COMPONENT_CALIBRATION: {
            "method": calibration_method,
            "coverage_target": _positive_float(
                calibration.get("coverage_target", 0.68), name="calibration.coverage_target"
            ),
            "coverage_tolerance": _positive_float(
                calibration.get("coverage_tolerance", 0.15), name="calibration.coverage_tolerance"
            ),
            "minimum_frames": _positive_int(
                calibration.get("minimum_frames", 2), name="calibration.minimum_frames"
            ),
        },
        COMPONENT_LOCKED_TEST: {
            "enabled": bool(locked.get("enabled", True)),
            "force_component_rmse_maximum_ev_per_angstrom": _positive_float(
                locked.get("force_component_rmse_maximum_ev_per_angstrom", 0.10),
                name="locked.force_component_rmse_maximum_ev_per_angstrom",
            ),
            "energy_rmse_maximum_ev_per_atom": _positive_float(
                locked.get("energy_rmse_maximum_ev_per_atom", 0.02),
                name="locked.energy_rmse_maximum_ev_per_atom",
            ),
            "minimum_frames": _positive_int(
                locked.get("minimum_frames", 1), name="locked.minimum_frames"
            ),
        },
    }
    if not int(payload[COMPONENT_DYNAMICS]["propagation_steps"]) >= int(
        payload[COMPONENT_DYNAMICS]["sample_interval_steps"]
    ):
        raise TrainingDataInputError(
            "[qualification.dynamics] propagation_steps must cover at least one sample interval."
        )
    return QualificationSpecIdentity(
        revision=str(section.get("spec_revision", QUALIFICATION_SPEC_REVISION)),
        required_components=required,
        optional_components=optional,
        policy_payload=payload,
    )


def enabled_components(specification: QualificationSpecIdentity) -> tuple[str, ...]:
    """Nonlocked components this specification asks the run command to produce."""

    active = set(specification.required_components) | set(specification.optional_components)
    return tuple(name for name in ALL_COMPONENTS if name in active and name != COMPONENT_LOCKED_TEST)


__all__ = [
    "CALIBRATION_METHOD_AUTO",
    "CALIBRATION_METHOD_COMMITTEE_VARIANCE",
    "CALIBRATION_METHOD_NONE",
    "DEFAULT_OPTIONAL_COMPONENTS",
    "DEFAULT_REQUIRED_COMPONENTS",
    "enabled_components",
    "resolve_qualification_spec_identity",
]
