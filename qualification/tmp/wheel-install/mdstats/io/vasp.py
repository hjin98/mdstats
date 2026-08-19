"""VASP reader for trajectory or independent frame collections."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Literal, Mapping

import numpy as np
from ase.io import read
from ase.stress import voigt_6_to_full_3x3_stress

from ..exceptions import (
    IncompleteFieldError,
    MissingPositionError,
    MissingTimeError,
    SpeciesConsistencyError,
)
from ..preprocess.normalize import normalize_raw_frame_collection
from ..collection import AtomisticFrameCollection
from ..semantics import FrameSemantics, coerce_frame_semantics
from .common import RawFrameCollection
from .vasp_contcar_trajectory import read_vasp_contcar_trajectory
from .vasp_controls import (
    _VaspXmlParseResult,
    _VaspXmlSupplement,
    _parse_vasp_xml,
)
from .vasp_ensemble import certify_vasp_simulation_controls


def _consolidate_optional(
    values: list[np.ndarray | float | None],
    *,
    strict: bool,
    name: str,
) -> np.ndarray | None:
    present = [value is not None for value in values]
    if all(present):
        return np.asarray(values, dtype=np.float64)
    if not any(present):
        return None
    message = f"{name} is present in only some selected VASP frames."
    if strict:
        raise IncompleteFieldError(message)
    warnings.warn(message + " Omitting the incomplete field.", stacklevel=3)
    return None


def _extract_ase_optional_vectors(
    frames: list,
    result_name: str,
    *,
    strict: bool,
) -> np.ndarray | None:
    values: list[np.ndarray | None] = []
    for atoms in frames:
        result = None
        if atoms.calc is not None:
            result = atoms.calc.results.get(result_name)
        values.append(None if result is None else np.asarray(result, dtype=np.float64))
    return _consolidate_optional(values, strict=strict, name=result_name)


def _detect_vasp_trajectory_format(
    filename: str | Path,
    explicit_format: Literal[
        "vasp-xml", "vasp-xdatcar", "vasp-contcar-trajectory"
    ] | None = None,
) -> str:
    """Infer the supported VASP trajectory format from the file name.

    XML files are treated as ``vasprun.xml``-style trajectories.  Any file
    whose basename ends with ``XDATCAR`` (case-insensitive) is treated as an
    XDATCAR trajectory, which also supports names such as ``run.XDATCAR`` or
    ``backup_XDATCAR``.
    """
    if explicit_format is not None:
        if explicit_format not in {
            "vasp-xml",
            "vasp-xdatcar",
            "vasp-contcar-trajectory",
        }:
            raise ValueError(f"Unsupported VASP trajectory format {explicit_format!r}.")
        return explicit_format

    path = Path(filename)
    name_upper = path.name.upper()
    if path.suffix.lower() == ".xml":
        return "vasp-xml"
    if name_upper.endswith("XDATCAR"):
        return "vasp-xdatcar"
    raise ValueError(
        f"Cannot infer VASP trajectory format from {path!s}. Expected a file "
        "ending in '.xml' or a basename ending in 'XDATCAR'. The custom "
        "concatenated CONTCAR stream must be selected explicitly with "
        "format='vasp-contcar-trajectory'."
    )


def read_vasp_frames(
    filename: str,
    *,
    format: Literal[
        "vasp-xml", "vasp-xdatcar", "vasp-contcar-trajectory"
    ] | None = None,
    start: int | None = None,
    stop: int | None = None,
    stride: int = 1,
    timestep_fs: float | None = None,
    reconstruct_velocities: bool = True,
    frame_semantics: FrameSemantics | str = FrameSemantics.TRAJECTORY,
    strict: bool = True,
    mass_map: Mapping[str, float] | None = None,
    assess_quality: bool = True,
    quality_policy: object | None = None,
    quality_emit_warning: bool = True,
    quality_raise_on_unqualified: bool = True,
    assess_stationarity: bool = True,
    production_window_policy: object | None = None,
    assess_admissibility: bool = True,
    admissibility_policy: object | None = None,
    reweighting_provenance: object | None = None,
    approximation_provenance: object | None = None,
    _parsed_vasp_xml: _VaspXmlParseResult | None = None,
) -> AtomisticFrameCollection:
    """Read and normalize a supported VASP trajectory source.

    ``vasprun.xml`` and ``XDATCAR`` retain their existing automatic filename
    detection.  The custom watcher-generated stream of concatenated complete
    MD ``CONTCAR`` records must be selected explicitly with
    ``format="vasp-contcar-trajectory"``.  That format requires native
    Cartesian ion velocities in every record and never uses finite-difference
    reconstruction, regardless of ``reconstruct_velocities``.

    Parameters
    ----------
    format
        Explicit source format. Required for ``vasp-contcar-trajectory``
        because a file named ``TRAJECTORY`` has no unique native VASP suffix.
    timestep_fs
        Saved-frame spacing in femtoseconds. For the concatenated CONTCAR
        format this is mandatory and may be an integer multiple of the embedded
        VASP POTIM when the watcher saves every ``k``-th ionic step.
    mass_map
        Optional element-to-mass mapping in atomic mass units for the custom
        CONTCAR trajectory. Missing entries use ASE standard atomic masses.
    assess_quality
        For a complete unstrided ``vasprun.xml`` trajectory, run Stage 11E-STAT0
        and attach the signed quality verdict to collection metadata. Subselected
        sources require a dedicated segment assessment and are not silently
        assigned the full-source verdict.
    assess_stationarity
        After STAT0, run Stage 11E-STAT1 for a complete unstrided trajectory and
        attach the source-observable production-regime catalog. This never uses
        adaptive site density to select a production interval.
    assess_admissibility
        After ENS1, STAT0, and STAT1, run Stage 11E-STAT2 for a complete
        unstrided trajectory and attach the source- and policy-bound preliminary
        PMF admissibility certificate. Subselected sources are never assigned
        the full-source certificate.
    """
    if stride <= 0:
        raise ValueError("stride must be a positive integer.")
    semantics = coerce_frame_semantics(frame_semantics)

    ase_format = _detect_vasp_trajectory_format(filename, format)
    if ase_format == "vasp-contcar-trajectory":
        if semantics is not FrameSemantics.TRAJECTORY:
            raise ValueError(
                "vasp-contcar-trajectory is intrinsically time ordered and "
                "must be read with trajectory semantics."
            )
        return read_vasp_contcar_trajectory(
            filename,
            start=start,
            stop=stop,
            stride=stride,
            timestep_fs=timestep_fs,
            strict=strict,
            mass_map=mass_map,
        )
    if mass_map is not None:
        raise ValueError(
            "mass_map is currently supported only for "
            "format='vasp-contcar-trajectory'."
        )
    try:
        all_frames = list(read(filename, index=":", format=ase_format))
    except Exception as exc:
        raise MissingPositionError(
            f"ASE could not read ionic frames from {filename!s} as {ase_format}: {exc}."
        ) from exc
    if not all_frames:
        raise MissingPositionError(f"No ionic frames found in {filename!s}.")

    selection = slice(start, stop, stride)

    if ase_format == "vasp-xml":
        parsed_vasp_xml = (
            _parse_vasp_xml(filename)
            if _parsed_vasp_xml is None
            else _parsed_vasp_xml
        )
        control_bundle = parsed_vasp_xml.bundle
        control_certificate = certify_vasp_simulation_controls(control_bundle)
        supplement = parsed_vasp_xml.supplement
        source_timestep_fs = (
            float(timestep_fs) if timestep_fs is not None else supplement.potim_fs
        )
        time_source = (
            "explicit timestep_fs" if timestep_fs is not None else "vasprun.xml POTIM"
        )
    else:
        control_bundle = None
        control_certificate = None
        supplement = _VaspXmlSupplement(
            potim_fs=None,
            per_atom_masses=None,
            velocities=[],
            kinetic_energies=[],
            total_energies=[],
            temperatures=[],
        )
        source_timestep_fs = float(timestep_fs) if timestep_fs is not None else None
        time_source = "explicit timestep_fs"

    if ase_format == "vasp-xml":
        parsed_count = control_bundle.source_identity.ionic_step_count
        if parsed_count != len(all_frames):
            if control_bundle.numerical_quality_controls.source_parse_complete:
                raise IncompleteFieldError(
                    "VASP control records do not align with ASE ionic frames "
                    f"({parsed_count} != {len(all_frames)})."
                )
            common_count = min(parsed_count, len(all_frames))
            if common_count <= 0:
                raise MissingPositionError(
                    "Interrupted VASP XML has no common complete ionic records."
                )
            warnings.warn(
                "Interrupted VASP XML produced different frame counts in the ASE and "
                f"control parsers ({len(all_frames)} and {parsed_count}); retaining "
                f"their common complete prefix of {common_count} frames.",
                stacklevel=2,
            )
            all_frames = all_frames[:common_count]

    all_indices = np.arange(len(all_frames), dtype=np.int64)
    frames = all_frames[selection]
    selected_indices = all_indices[selection]
    if not frames:
        raise MissingPositionError("Frame selection produced an empty trajectory.")

    if source_timestep_fs is None or source_timestep_fs <= 0.0:
        if semantics is FrameSemantics.TRAJECTORY:
            if ase_format == "vasp-xdatcar":
                raise MissingTimeError(
                    "XDATCAR does not store POTIM. Supply timestep_fs explicitly "
                    "for trajectory semantics."
                )
            raise MissingTimeError(
                "POTIM is absent or invalid. Supply timestep_fs explicitly."
            )
        source_timestep_fs = None
        time_source = "unavailable for independent ensemble"

    n_atoms = len(frames[0])
    pbc = np.asarray(frames[0].pbc, dtype=np.bool_)
    cells: list[np.ndarray] = []
    positions: list[np.ndarray] = []
    numbers: list[np.ndarray] = []
    masses: list[np.ndarray] = []

    for local_index, atoms in enumerate(frames):
        if len(atoms) != n_atoms:
            raise SpeciesConsistencyError(
                f"Atom count changed at selected VASP frame {local_index}."
            )
        if not np.array_equal(np.asarray(atoms.pbc, dtype=np.bool_), pbc):
            raise SpeciesConsistencyError(
                f"PBC flags changed at selected VASP frame {local_index}."
            )
        cells.append(np.asarray(atoms.cell.array, dtype=np.float64))
        positions.append(
            np.asarray(atoms.get_scaled_positions(wrap=False), dtype=np.float64)
        )
        numbers.append(np.asarray(atoms.numbers, dtype=np.int32))
        if (
            supplement.per_atom_masses is not None
            and supplement.per_atom_masses.shape == (n_atoms,)
        ):
            masses.append(supplement.per_atom_masses.copy())
        else:
            masses.append(np.asarray(atoms.get_masses(), dtype=np.float64))

    forces = _extract_ase_optional_vectors(frames, "forces", strict=strict)
    raw_stress = _extract_ase_optional_vectors(frames, "stress", strict=strict)
    stresses: np.ndarray | None
    if raw_stress is None:
        stresses = None
        stress_source = None
    elif raw_stress.shape == (len(frames), 6):
        stresses = np.stack([voigt_6_to_full_3x3_stress(value) for value in raw_stress])
        stress_source = "ASE vasprun.xml stress"
    elif raw_stress.shape == (len(frames), 3, 3):
        stresses = raw_stress
        stress_source = "ASE vasprun.xml stress"
    else:
        raise IncompleteFieldError(f"Unexpected ASE stress shape {raw_stress.shape}.")

    potential_values: list[float | None] = []
    for atoms in frames:
        value = None
        if atoms.calc is not None:
            result = atoms.calc.results.get("energy")
            if result is not None:
                value = float(result)
        potential_values.append(value)
    potential = _consolidate_optional(
        potential_values, strict=strict, name="potential energy"
    )

    def selected_supplement(
        values: list[np.ndarray | float | None], name: str
    ) -> np.ndarray | None:
        if ase_format != "vasp-xml":
            return None
        if len(values) != len(all_frames):
            if any(value is not None for value in values):
                message = f"VASP {name} blocks do not align with all ASE ionic frames."
                if strict:
                    raise IncompleteFieldError(message)
                warnings.warn(message + " Omitting the field.", stacklevel=2)
            return None
        selected = [values[int(index)] for index in selected_indices]
        return _consolidate_optional(selected, strict=strict, name=name)

    native_velocities = selected_supplement(
        supplement.velocities, "velocity trajectory"
    )
    if native_velocities is not None:
        native_velocities = native_velocities * 1.0e3

    kinetic = selected_supplement(supplement.kinetic_energies, "kinetic energy")
    total = selected_supplement(supplement.total_energies, "total energy")
    temperature = selected_supplement(supplement.temperatures, "temperature")

    steps = selected_indices.astype(np.int64)
    times = (
        None
        if source_timestep_fs is None
        else steps.astype(np.float64) * source_timestep_fs * 1.0e-3
    )

    raw = RawFrameCollection(
        frame_ids=np.arange(len(frames), dtype=np.int64),
        source_ids=None,
        source_type_ids=None,
        atomic_numbers=np.stack(numbers),
        masses=np.stack(masses),
        steps=steps,
        times=times,
        cells=np.stack(cells),
        origins=np.zeros((len(frames), 3), dtype=np.float64),
        pbc=pbc,
        coordinate_kind="wrapped_fractional",
        coordinates=np.stack(positions),
        image_flags=None,
        velocities=native_velocities,
        forces=forces,
        stresses=stresses,
        scalar_pressures=None,
        temperatures=temperature,
        potential_energies=potential,
        kinetic_energies=kinetic,
        total_energies=total,
        source_units="VASP native",
        metadata={
            "vasp_input_format": ase_format,
            "potim_fs": source_timestep_fs,
            "time_source": time_source,
            "source_frame_count": len(all_frames),
            "selected_frame_count": len(frames),
            **(
                {}
                if control_bundle is None
                else {
                    "source_trajectory_bundle_identity": control_bundle.source_identity.to_dict(),
                    "source_trajectory_bundle_signature": control_bundle.source_identity.signature,
                    "vasp_source_control_bundle_signature": control_bundle.signature,
                    "vasp_run_controls": control_bundle.run_controls.to_dict(),
                    "frame_energy_catalog": control_bundle.energy_catalog.to_dict(
                        include_values=True
                    ),
                    "numerical_md_quality_controls": (
                        control_bundle.numerical_quality_controls.to_dict()
                    ),
                    "simulation_control_certificate": control_certificate.to_dict(),
                    "simulation_control_certificate_signature": control_certificate.signature,
                }
            ),
        },
    )

    collection = normalize_raw_frame_collection(
        raw,
        frame_semantics=semantics,
        source_format=(
            "vasp-vasprun-xml" if ase_format == "vasp-xml" else "vasp-xdatcar"
        ),
        source_files=(filename,),
        units_source="VASP native units",
        stress_source=stress_source,
        reconstruct_missing_velocities=reconstruct_velocities,
    )
    assess_any = assess_quality or assess_stationarity or assess_admissibility
    if (
        assess_any
        and ase_format == "vasp-xml"
        and semantics is FrameSemantics.TRAJECTORY
    ):
        full_selection = (start is None or start == 0) and stop is None and stride == 1
        if full_selection:
            from .admissibility import (
                EnsembleAdmissibilityPolicy,
                EnsembleApproximationProvenance,
                ReweightingProvenance,
                assess_pmf_admissibility,
            )
            from .production_regimes import (
                ProductionWindowPolicy,
                assess_production_regimes,
            )
            from .trajectory_quality import (
                TrajectoryQualityPolicy,
                assess_trajectory_quality,
            )

            if quality_policy is not None and not isinstance(
                quality_policy, TrajectoryQualityPolicy
            ):
                raise TypeError("quality_policy must be a TrajectoryQualityPolicy.")
            if production_window_policy is not None and not isinstance(
                production_window_policy, ProductionWindowPolicy
            ):
                raise TypeError(
                    "production_window_policy must be a ProductionWindowPolicy."
                )
            if admissibility_policy is not None and not isinstance(
                admissibility_policy, EnsembleAdmissibilityPolicy
            ):
                raise TypeError(
                    "admissibility_policy must be an EnsembleAdmissibilityPolicy."
                )
            if reweighting_provenance is not None and not isinstance(
                reweighting_provenance, ReweightingProvenance
            ):
                raise TypeError(
                    "reweighting_provenance must be a ReweightingProvenance."
                )
            if approximation_provenance is not None and not isinstance(
                approximation_provenance, EnsembleApproximationProvenance
            ):
                raise TypeError(
                    "approximation_provenance must be an "
                    "EnsembleApproximationProvenance."
                )
            assert control_bundle is not None and control_certificate is not None
            verdict = assess_trajectory_quality(
                collection,
                energy_catalog=control_bundle.energy_catalog,
                numerical_quality_controls=control_bundle.numerical_quality_controls,
                simulation_control_certificate=control_certificate,
                source_identity_signature=control_bundle.source_identity.signature,
                policy=quality_policy,
                emit_warning=quality_emit_warning,
                raise_on_unqualified=quality_raise_on_unqualified,
            )
            if assess_quality:
                collection.metadata["trajectory_quality_verdict"] = verdict.to_dict(
                    include_series=True
                )
                collection.metadata["trajectory_quality_verdict_signature"] = (
                    verdict.signature
                )
            regimes = None
            if assess_stationarity or assess_admissibility:
                regimes = assess_production_regimes(
                    collection,
                    energy_catalog=control_bundle.energy_catalog,
                    simulation_control_certificate=control_certificate,
                    trajectory_quality_verdict=verdict,
                    source_identity_signature=control_bundle.source_identity.signature,
                    policy=production_window_policy,
                )
            if assess_stationarity:
                assert regimes is not None
                collection.metadata["production_regime_catalog"] = regimes.to_dict()
                collection.metadata["production_regime_catalog_signature"] = (
                    regimes.signature
                )
            if assess_admissibility:
                assert regimes is not None
                admissibility = assess_pmf_admissibility(
                    simulation_control_certificate=control_certificate,
                    trajectory_quality_verdict=verdict,
                    production_regime_catalog=regimes,
                    source_identity_signature=control_bundle.source_identity.signature,
                    policy=admissibility_policy,
                    reweighting_provenance=reweighting_provenance,
                    approximation_provenance=approximation_provenance,
                )
                collection.metadata["pmf_admissibility_certificate"] = (
                    admissibility.to_dict()
                )
                collection.metadata["pmf_admissibility_certificate_signature"] = (
                    admissibility.signature
                )
        else:
            if assess_quality:
                collection.metadata["trajectory_quality_assessment_status"] = (
                    "not_evaluated_for_subselected_source_segment"
                )
            if assess_stationarity:
                collection.metadata["production_regime_assessment_status"] = (
                    "not_evaluated_for_subselected_source_segment"
                )
            if assess_admissibility:
                collection.metadata["pmf_admissibility_assessment_status"] = (
                    "not_evaluated_for_subselected_source_segment"
                )
    return collection
