"""VASP Stage 11E-ENS1 ensemble and force-provenance inference."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .control_certificates import (
    ENSEMBLE_INFERENCE_POLICY_VERSION,
    EnsembleKind,
    InferenceStatus,
    SimulationControlCertificate,
    SimulationControlComponent,
    SimulationControlDecision,
)
from .source_controls import CompanionFileState
from .vasp_controls import VaspSourceControlBundle, read_vasp_run_controls

VASP_ENSEMBLE_INFERENCE_POLICY_VERSION = (
    ENSEMBLE_INFERENCE_POLICY_VERSION + "+vasp-wiki-2026-06"
)


def _value(bundle: VaspSourceControlBundle, name: str, default: Any = None) -> Any:
    return bundle.run_controls.effective_value(name, default)


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool) or isinstance(value, tuple):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool) or isinstance(value, tuple):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "t", ".true.", "1"}:
        return True
    if text in {"false", "f", ".false.", "0"}:
        return False
    return None


def _as_floats(value: Any) -> tuple[float, ...] | None:
    if value is None:
        return None
    items = value if isinstance(value, tuple) else (value,)
    try:
        return tuple(float(item) for item in items)
    except (TypeError, ValueError):
        return None


def _component(
    status: InferenceStatus,
    kind: str,
    active: bool | None,
    *,
    parameters: Mapping[str, Any] | None = None,
    evidence: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
) -> SimulationControlComponent:
    return SimulationControlComponent(
        status=status,
        kind=kind,
        active=active,
        parameters=tuple((str(k), v) for k, v in (parameters or {}).items()),
        evidence=evidence,
        notes=notes,
    )


def _parse_iconst_statuses(path: Path | None) -> tuple[int, ...] | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    statuses: list[int] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].split("!", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        try:
            statuses.append(int(float(parts[-1])))
        except (IndexError, ValueError):
            continue
    return tuple(statuses)


def _bias_and_constraints(
    bundle: VaspSourceControlBundle,
    companion_files: Mapping[str, str | Path] | None,
) -> tuple[SimulationControlComponent, SimulationControlComponent, list[str]]:
    iconst_record = bundle.manifest.by_role("constraint_definition")
    iconst_path = None
    if companion_files and "constraint_definition" in companion_files:
        iconst_path = Path(companion_files["constraint_definition"])
    statuses = _parse_iconst_statuses(iconst_path)
    hills = {
        name: _value(bundle, name)
        for name in ("HILLS_H", "HILLS_W", "HILLS_BIN")
        if _value(bundle, name) is not None
    }
    warnings: list[str] = []
    if statuses is not None:
        constrained = any(status == 0 for status in statuses)
        biased = any(status in {3, 4, 5, 8} for status in statuses)
        bias_kinds = tuple(sorted({status for status in statuses if status in {3, 4, 5, 8}}))
        constraint = _component(
            InferenceStatus.RESOLVED,
            "geometric_constraints" if constrained else "none",
            constrained,
            parameters={"iconst_statuses": statuses},
            evidence=("bound ICONST content",),
        )
        bias = _component(
            InferenceStatus.RESOLVED,
            "iconst_bias_or_metadynamics" if biased else "none",
            biased,
            parameters={"iconst_bias_statuses": bias_kinds, **hills},
            evidence=("bound ICONST content",),
        )
        return bias, constraint, warnings
    if iconst_record is not None and iconst_record.state is CompanionFileState.PRESENT_AND_BOUND:
        warnings.append("ICONST is bound but its content was unavailable to ENS1.")
    if hills:
        bias = _component(
            InferenceStatus.RESOLVED,
            "metadynamics_or_bias_controls_present",
            True,
            parameters=hills,
            evidence=tuple(f"effective {name}" for name in hills),
            notes=("Exact collective-variable definition requires bound ICONST content.",),
        )
    else:
        bias = _component(
            InferenceStatus.UNRESOLVED,
            "unknown",
            None,
            evidence=("no affirmative bias companion evidence",),
            notes=("Missing companion evidence is not treated as affirmative absence.",),
        )
    constraint = _component(
        InferenceStatus.UNRESOLVED,
        "unknown",
        None,
        evidence=("no parsed ICONST content",),
        notes=("Constraint nonuse cannot be asserted from a missing companion file.",),
    )
    return bias, constraint, warnings


def certify_vasp_simulation_controls(
    source: str | Path | VaspSourceControlBundle,
    *,
    companion_files: Mapping[str, str | Path] | None = None,
) -> SimulationControlCertificate:
    """Create a deterministic ENS1 certificate from an ENS0 VASP bundle."""

    bundle = (
        source
        if isinstance(source, VaspSourceControlBundle)
        else read_vasp_run_controls(source, companion_files=companion_files)
    )
    controls = bundle.run_controls
    decisions: list[SimulationControlDecision] = []
    warnings: list[str] = []
    unresolved: list[str] = []

    ibrion = _as_int(_value(bundle, "IBRION"))
    mdalgo = _as_int(_value(bundle, "MDALGO"))
    smass = _as_float(_value(bundle, "SMASS"))
    isif = _as_int(_value(bundle, "ISIF"))
    evidence_base = (f"IBRION={ibrion}", f"MDALGO={mdalgo}", f"ISIF={isif}")

    if ibrion is None:
        dynamics_status = InferenceStatus.UNRESOLVED
        dynamics_mode = "unknown"
        ensemble_status = InferenceStatus.UNRESOLVED
        ensemble = EnsembleKind.UNKNOWN
        propagator = _component(
            InferenceStatus.UNRESOLVED, "unknown", None, evidence=("IBRION unavailable",)
        )
        thermostat = _component(InferenceStatus.UNRESOLVED, "unknown", None)
        barostat = _component(InferenceStatus.UNRESOLVED, "unknown", None)
        unresolved.append("IBRION is unavailable; molecular dynamics cannot be established.")
    elif ibrion != 0:
        dynamics_status = InferenceStatus.RESOLVED
        dynamics_mode = "not_molecular_dynamics"
        ensemble_status = InferenceStatus.NOT_APPLICABLE
        ensemble = EnsembleKind.UNKNOWN
        propagator = _component(
            InferenceStatus.NOT_APPLICABLE,
            "none",
            False,
            evidence=(f"effective IBRION={ibrion}",),
        )
        thermostat = _component(InferenceStatus.NOT_APPLICABLE, "none", False)
        barostat = _component(InferenceStatus.NOT_APPLICABLE, "none", False)
        decisions.append(
            SimulationControlDecision("vasp.ibrion", dynamics_mode, evidence_base)
        )
    else:
        dynamics_status = InferenceStatus.RESOLVED
        dynamics_mode = "molecular_dynamics"
        ensemble_status = InferenceStatus.UNRESOLVED
        ensemble = EnsembleKind.UNKNOWN
        propagator = _component(
            InferenceStatus.UNRESOLVED,
            "unknown",
            None,
            parameters={"MDALGO": mdalgo},
            evidence=evidence_base,
        )
        thermostat = _component(InferenceStatus.UNRESOLVED, "unknown", None)
        barostat = _component(InferenceStatus.NOT_APPLICABLE, "none", False)

        if mdalgo in {0, 2}:
            propagator = _component(
                InferenceStatus.RESOLVED,
                "nose_hoover_family",
                True,
                parameters={"MDALGO": mdalgo, "SMASS": smass},
                evidence=(f"effective MDALGO={mdalgo}", f"effective SMASS={smass}"),
            )
            if smass == -3.0:
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.NVE
                thermostat = _component(
                    InferenceStatus.RESOLVED,
                    "none",
                    False,
                    parameters={"friction": "not_applicable", "SMASS": smass},
                    evidence=("SMASS=-3",),
                )
                decisions.append(
                    SimulationControlDecision(
                        "vasp.nose.smass_minus_3", "fixed-cell NVE", evidence_base
                    )
                )
            elif smass == -2.0:
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.CONSTANT_VELOCITY_PATH
                dynamics_mode = "constant_velocity_path"
                thermostat = _component(
                    InferenceStatus.NOT_APPLICABLE,
                    "none",
                    False,
                    parameters={"SMASS": smass},
                    evidence=("SMASS=-2",),
                )
            elif smass == -1.0:
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.TEMPERATURE_RAMP
                dynamics_mode = "velocity_rescaled_temperature_schedule"
                thermostat = _component(
                    InferenceStatus.RESOLVED,
                    "deterministic_velocity_rescaling",
                    True,
                    parameters={
                        "SMASS": smass,
                        "TEBEG": _value(bundle, "TEBEG"),
                        "TEEND": _value(bundle, "TEEND"),
                        "NBLOCK": _value(bundle, "NBLOCK"),
                    },
                    evidence=("SMASS=-1",),
                )
            elif smass is not None and smass >= 0.0:
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.NVT
                thermostat = _component(
                    InferenceStatus.RESOLVED,
                    "nose_hoover",
                    True,
                    parameters={"SMASS": smass, "friction": "not_applicable"},
                    evidence=("SMASS>=0",),
                )
            else:
                unresolved.append("SMASS is missing or unsupported for the Nosé family.")
        elif mdalgo == 1:
            prob = _as_float(_value(bundle, "ANDERSEN_PROB"))
            propagator = _component(
                InferenceStatus.RESOLVED,
                "andersen",
                True,
                parameters={"ANDERSEN_PROB": prob},
                evidence=("MDALGO=1",),
            )
            if prob == 0.0:
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.NVE
                thermostat = _component(
                    InferenceStatus.RESOLVED,
                    "none",
                    False,
                    parameters={"ANDERSEN_PROB": prob, "friction": "not_applicable"},
                    evidence=("ANDERSEN_PROB=0",),
                )
            elif prob is not None and prob > 0.0:
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.NVT
                thermostat = _component(
                    InferenceStatus.RESOLVED,
                    "andersen",
                    True,
                    parameters={"ANDERSEN_PROB": prob},
                    evidence=("ANDERSEN_PROB>0",),
                )
            else:
                unresolved.append("ANDERSEN_PROB is missing or invalid.")
        elif mdalgo == 3:
            gammas = _as_floats(_value(bundle, "LANGEVIN_GAMMA"))
            gamma_l = _as_float(_value(bundle, "LANGEVIN_GAMMA_L"))
            atomic_active = None if gammas is None else any(value > 0 for value in gammas)
            lattice_active = None if gamma_l is None else gamma_l > 0
            propagator = _component(
                InferenceStatus.RESOLVED,
                "langevin_parrinello_rahman",
                True,
                parameters={
                    "LANGEVIN_GAMMA": gammas,
                    "LANGEVIN_GAMMA_L": gamma_l,
                    "PMASS": _value(bundle, "PMASS"),
                },
                evidence=("MDALGO=3",),
            )
            if isif is not None and isif <= 2:
                barostat = _component(InferenceStatus.NOT_APPLICABLE, "none", False)
                if atomic_active is True:
                    ensemble_status = InferenceStatus.RESOLVED
                    ensemble = EnsembleKind.NVT
                    thermostat = _component(
                        InferenceStatus.RESOLVED,
                        "langevin",
                        True,
                        parameters={"friction_ps^-1": gammas},
                        evidence=("LANGEVIN_GAMMA has positive entries",),
                    )
                elif atomic_active is False:
                    ensemble_status = InferenceStatus.RESOLVED
                    ensemble = EnsembleKind.NVE
                    thermostat = _component(
                        InferenceStatus.RESOLVED,
                        "none",
                        False,
                        parameters={"friction_ps^-1": gammas},
                        evidence=("all LANGEVIN_GAMMA entries are zero",),
                    )
                else:
                    unresolved.append("LANGEVIN_GAMMA is unavailable.")
            elif isif == 3:
                barostat = _component(
                    InferenceStatus.RESOLVED,
                    "parrinello_rahman",
                    True,
                    parameters={"lattice_friction_ps^-1": gamma_l, "PMASS": _value(bundle, "PMASS")},
                    evidence=("ISIF=3", "MDALGO=3"),
                )
                if atomic_active is True and lattice_active is True:
                    ensemble_status = InferenceStatus.RESOLVED
                    ensemble = EnsembleKind.NPT
                    thermostat = _component(
                        InferenceStatus.RESOLVED,
                        "langevin",
                        True,
                        parameters={"friction_ps^-1": gammas},
                        evidence=("positive atomic and lattice Langevin friction",),
                    )
                elif atomic_active is False and lattice_active is False:
                    ensemble_status = InferenceStatus.RESOLVED
                    ensemble = EnsembleKind.NPH
                    thermostat = _component(
                        InferenceStatus.RESOLVED,
                        "none",
                        False,
                        parameters={"friction_ps^-1": gammas},
                        evidence=("zero atomic and lattice Langevin friction",),
                    )
                else:
                    ensemble_status = InferenceStatus.CONFLICTING
                    ensemble = EnsembleKind.UNKNOWN
                    thermostat = _component(
                        InferenceStatus.CONFLICTING,
                        "partially_active_langevin",
                        atomic_active,
                        parameters={"friction_ps^-1": gammas},
                        evidence=("mixed or incomplete Langevin friction controls",),
                    )
                    unresolved.append("Variable-cell Langevin controls are mixed or incomplete.")
            else:
                unresolved.append("MDALGO=3 has unsupported or missing ISIF.")
        elif mdalgo == 4:
            nchains = _as_int(_value(bundle, "NHC_NCHAINS"))
            period = _as_float(_value(bundle, "NHC_PERIOD"))
            params = {
                "NHC_NCHAINS": nchains,
                "NHC_PERIOD": period,
                "NHC_NRESPA": _value(bundle, "NHC_NRESPA"),
                "NHC_NS": _value(bundle, "NHC_NS"),
            }
            if nchains is not None and nchains > 0 and period is not None and period > 0:
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.NVT
                propagator = _component(InferenceStatus.RESOLVED, "nose_hoover_chain", True, parameters=params, evidence=("MDALGO=4",))
                thermostat = _component(InferenceStatus.RESOLVED, "nose_hoover_chain", True, parameters=params)
            else:
                propagator = _component(InferenceStatus.UNRESOLVED, "nose_hoover_chain", None, parameters=params, evidence=("MDALGO=4",))
                thermostat = _component(InferenceStatus.UNRESOLVED, "nose_hoover_chain", None, parameters=params)
                unresolved.append("Nose-Hoover-chain controls are incomplete.")
        elif mdalgo == 5:
            period = _as_float(_value(bundle, "CSVR_PERIOD"))
            params = {"CSVR_PERIOD": period}
            if period is not None and period > 0:
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.NVT
                propagator = _component(InferenceStatus.RESOLVED, "csvr", True, parameters=params, evidence=("MDALGO=5",))
                thermostat = _component(InferenceStatus.RESOLVED, "csvr", True, parameters=params)
            else:
                propagator = _component(InferenceStatus.UNRESOLVED, "csvr", None, parameters=params, evidence=("MDALGO=5",))
                thermostat = _component(InferenceStatus.UNRESOLVED, "csvr", None, parameters=params)
                unresolved.append("CSVR_PERIOD is missing or invalid.")
        elif mdalgo == 13:
            params = {
                "NSUBSYS": _value(bundle, "NSUBSYS"),
                "TSUBSYS": _value(bundle, "TSUBSYS"),
                "PSUBSYS": _value(bundle, "PSUBSYS"),
            }
            if all(value is not None for value in params.values()):
                ensemble_status = InferenceStatus.RESOLVED
                ensemble = EnsembleKind.MULTI_THERMOSTAT
                propagator = _component(InferenceStatus.RESOLVED, "multiple_andersen_subsystems", True, parameters=params, evidence=("MDALGO=13",))
                thermostat = _component(InferenceStatus.RESOLVED, "multiple_andersen_subsystems", True, parameters=params)
            else:
                propagator = _component(InferenceStatus.UNRESOLVED, "multiple_andersen_subsystems", None, parameters=params, evidence=("MDALGO=13",))
                thermostat = _component(InferenceStatus.UNRESOLVED, "multiple_andersen_subsystems", None, parameters=params)
                unresolved.append("Multiple-Andersen subsystem controls are incomplete.")
        else:
            unresolved.append(f"Unsupported or missing MDALGO={mdalgo!r}.")

    if isif is None:
        cell = _component(InferenceStatus.UNRESOLVED, "unknown", None)
    elif isif <= 2:
        cell = _component(
            InferenceStatus.RESOLVED,
            "fixed_cell",
            False,
            parameters={"ISIF": isif},
            evidence=(f"ISIF={isif}",),
        )
    elif isif == 3:
        cell = _component(
            InferenceStatus.RESOLVED,
            "variable_volume_and_shape",
            True,
            parameters={"ISIF": isif},
            evidence=("ISIF=3",),
        )
    else:
        cell = _component(
            InferenceStatus.UNRESOLVED,
            "partially_variable_or_unsupported",
            None,
            parameters={"ISIF": isif},
            evidence=(f"ISIF={isif}",),
        )
        unresolved.append(f"Cell-control semantics for ISIF={isif} are unresolved.")

    bias, constraints, companion_warnings = _bias_and_constraints(bundle, companion_files)
    warnings.extend(companion_warnings)

    ml_lmlff = _as_bool(_value(bundle, "ML_LMLFF"))
    ml_mode = str(_value(bundle, "ML_MODE", "")).strip().lower() or None
    if ml_lmlff:
        if ml_mode == "run":
            provider = "vasp_mlff_prediction"
        elif ml_mode == "train":
            provider = "vasp_mlff_on_the_fly_hybrid"
        else:
            provider = "vasp_mlff_unknown_mode"
    else:
        provider = "vasp_dft_hellmann_feynman"
    force_complete = bundle.numerical_quality_controls.forces_complete
    applied_force_status = (
        InferenceStatus.RESOLVED
        if bias.status is InferenceStatus.RESOLVED
        and constraints.status is InferenceStatus.RESOLVED
        else InferenceStatus.UNRESOLVED
    )
    force = _component(
        applied_force_status,
        provider,
        force_complete,
        parameters={
            "force_array_complete": force_complete,
            "ML_LMLFF": ml_lmlff,
            "ML_MODE": ml_mode,
            "bias_status": bias.status.value,
            "constraint_status": constraints.status.value,
        },
        evidence=("VASP effective force-provider controls", "vasprun.xml force arrays"),
        notes=(
            "Complete force arrays do not prove absence of constraint or bias contributions.",
        ),
    )

    kinetic = bundle.energy_catalog.channel("kinetic")
    first_kinetic = None if kinetic is None or not kinetic.values else kinetic.values[0]
    native_count = bundle.numerical_quality_controls.native_velocity_frame_count
    if native_count > 0:
        initial_velocity = _component(
            InferenceStatus.RESOLVED,
            "native_velocity_records_present",
            True,
            parameters={"native_velocity_frame_count": native_count},
            evidence=("native velocity arrays",),
        )
    elif first_kinetic is not None and first_kinetic > 0.0:
        initial_velocity = _component(
            InferenceStatus.UNRESOLVED,
            "nonzero_initial_kinetic_energy_source_unknown",
            True,
            parameters={"first_kinetic_energy_eV": first_kinetic},
            evidence=("first-frame kinetic energy is positive",),
            notes=("The XML does not identify whether velocities came from a restart or initialization.",),
        )
    else:
        initial_velocity = _component(
            InferenceStatus.UNRESOLVED,
            "unknown",
            None,
            evidence=("no native velocity provenance",),
        )
    continuation = _component(
        InferenceStatus.UNRESOLVED,
        "continuation_or_external_initialization_possible",
        None,
        parameters={
            "native_velocity_frame_count": native_count,
            "first_kinetic_energy_eV": first_kinetic,
            "TEBEG": _value(bundle, "TEBEG"),
            "TEEND": _value(bundle, "TEEND"),
        },
        evidence=("initial kinetic and velocity provenance",),
        notes=("Continuation lineage requires a bound parent source or restart record.",),
    )

    if thermostat.active is False and thermostat.parameter("friction") is None:
        thermostat = _component(
            thermostat.status,
            thermostat.kind,
            thermostat.active,
            parameters={**dict(thermostat.parameters), "friction": "not_applicable"},
            evidence=thermostat.evidence,
            notes=thermostat.notes,
        )

    decisions.extend((
        SimulationControlDecision("vasp.cell_control", f"{cell.status.value}:{cell.kind}", evidence=cell.evidence),
        SimulationControlDecision("vasp.bias", f"{bias.status.value}:{bias.kind}", evidence=bias.evidence),
        SimulationControlDecision("vasp.constraints", f"{constraints.status.value}:{constraints.kind}", evidence=constraints.evidence),
        SimulationControlDecision("vasp.force_provider", f"{force.status.value}:{force.kind}", evidence=force.evidence),
        SimulationControlDecision("vasp.initial_velocity", f"{initial_velocity.status.value}:{initial_velocity.kind}", evidence=initial_velocity.evidence),
    ))
    if ensemble_status is not InferenceStatus.RESOLVED:
        unresolved.append("A standard ensemble could not be resolved from effective controls.")
    decisions.append(
        SimulationControlDecision(
            "vasp.final_ensemble",
            f"{ensemble_status.value}:{ensemble.value}",
            evidence=evidence_base,
        )
    )

    return SimulationControlCertificate(
        source_identity_signature=bundle.source_identity.signature,
        source_control_bundle_signature=bundle.signature,
        run_controls_signature=controls.signature,
        policy_version=VASP_ENSEMBLE_INFERENCE_POLICY_VERSION,
        dynamics_status=dynamics_status,
        dynamics_mode=dynamics_mode,
        ensemble_status=ensemble_status,
        ensemble=ensemble,
        propagator=propagator,
        thermostat=thermostat,
        barostat=barostat,
        cell_control=cell,
        bias=bias,
        constraints=constraints,
        force_provenance=force,
        initial_velocity_provenance=initial_velocity,
        continuation_provenance=continuation,
        decisions=tuple(decisions),
        unresolved_reasons=tuple(dict.fromkeys(unresolved)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


__all__ = [
    "VASP_ENSEMBLE_INFERENCE_POLICY_VERSION",
    "certify_vasp_simulation_controls",
]
