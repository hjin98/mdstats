"""Automatic, reviewable manifest metadata inference for MLFF-DATA2.

The inference gate deliberately separates operational assertions from diagnostics:
XML controls and verified geometry may promote assertions, while rejected filename
hints remain visible only in the ``inference`` record and cannot influence later
partitioning or strain reconstruction.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from pathlib import Path
import re
from typing import Any, Mapping
import xml.etree.ElementTree as ET

import numpy as np

from ._common import TrainingDataInputError, digest, json_value
from .manifest import (
    TRAINING_DATA_MANIFEST_VERSION,
    TrainingDataManifest,
    TrainingDataRunSpec,
)

MANIFEST_INFERENCE_POLICY_SCHEMA = "mdstats.manifest-inference-policy.v1"
MANIFEST_INFERENCE_POLICY_VERSION = "mdstats.mlff-data2.manifest-inference.2026-08.v1"


@dataclass(frozen=True, slots=True)
class ManifestInferencePolicy:
    """Tolerances and filename conventions for reviewable DATA2 inference."""

    fixed_cell_relative_tolerance: float = 1.0e-7
    reference_cell_relative_tolerance: float = 1.0e-7
    strain_matrix_absolute_tolerance: float = 5.0e-5
    strain_volume_ratio_tolerance: float = 5.0e-5
    maximum_rotation_radians: float = 1.0e-4
    conventional_axis_orthogonality_tolerance: float = 5.0e-6
    temperature_equality_tolerance_kelvin: float = 1.0e-6
    filename_values_at_or_above_one_are_percent: bool = True
    policy_version: str = MANIFEST_INFERENCE_POLICY_VERSION

    def __post_init__(self) -> None:
        for name in (
            "fixed_cell_relative_tolerance",
            "reference_cell_relative_tolerance",
            "strain_matrix_absolute_tolerance",
            "strain_volume_ratio_tolerance",
            "maximum_rotation_radians",
            "conventional_axis_orthogonality_tolerance",
            "temperature_equality_tolerance_kelvin",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MANIFEST_INFERENCE_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "fixed_cell_relative_tolerance": self.fixed_cell_relative_tolerance,
            "reference_cell_relative_tolerance": self.reference_cell_relative_tolerance,
            "strain_matrix_absolute_tolerance": self.strain_matrix_absolute_tolerance,
            "strain_volume_ratio_tolerance": self.strain_volume_ratio_tolerance,
            "maximum_rotation_radians": self.maximum_rotation_radians,
            "conventional_axis_orthogonality_tolerance": self.conventional_axis_orthogonality_tolerance,
            "temperature_equality_tolerance_kelvin": self.temperature_equality_tolerance_kelvin,
            "filename_values_at_or_above_one_are_percent": self.filename_values_at_or_above_one_are_percent,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}


@dataclass(frozen=True, slots=True)
class ManifestInferenceResult:
    manifest: TrainingDataManifest
    policy_digest: str
    resolved_xml_metadata_runs: int
    fixed_cell_runs: int
    strain_candidate_runs: int
    verified_strain_runs: int
    rejected_strain_runs: int
    ambiguous_strain_runs: int
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "mdstats.manifest-inference-result.v1",
            "manifest_digest": self.manifest.content_digest,
            "policy_digest": self.policy_digest,
            "resolved_xml_metadata_runs": self.resolved_xml_metadata_runs,
            "fixed_cell_runs": self.fixed_cell_runs,
            "strain_candidate_runs": self.strain_candidate_runs,
            "verified_strain_runs": self.verified_strain_runs,
            "rejected_strain_runs": self.rejected_strain_runs,
            "ambiguous_strain_runs": self.ambiguous_strain_runs,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class _RunObservation:
    run: TrainingDataRunSpec
    path: Path
    assertions: Mapping[str, Any]
    inference: Mapping[str, Any]
    representative_cell: np.ndarray | None
    cell_count: int
    fixed_cell: bool
    fixed_cell_relative_deviation: float | None
    atom_symbols: tuple[str, ...]
    ensemble: str | None
    thermostat: str | None


@dataclass(frozen=True, slots=True)
class _TolerantXmlMetadata:
    atom_symbols: tuple[str, ...]
    initial_cell: np.ndarray | None
    calculation_cells: tuple[np.ndarray, ...]
    controls: Mapping[str, Any]
    parse_complete: bool
    parse_warning: str | None


@dataclass(frozen=True, slots=True)
class _StrainFilenameCandidate:
    kind: str
    signed_value: float
    raw_value: str
    value_interpretation: str
    reference_prefix: str
    reference_suffix: str


_STRAIN_PATTERN = re.compile(
    r"^(?P<prefix>.+?)(?:_|\.)strained\."
    r"(?P<kind>hydro|ortho|shear)"
    r"(?P<value>[+-](?:\d+(?:\.\d*)?|\.\d+)%?)"
    r"(?P<suffix>(?:\..*)?)$",
    re.IGNORECASE,
)


_AUTOMATIC_STRAIN_ASSERTION_KEYS = {
    "intended_strain_class",
    "intended_strain_signed_value",
    "intended_volume_change",
    "intended_strain_magnitude",
    "intended_strain_sign",
    "strain_definition",
    "strain_inference_basis",
    "is_reference_cell",
}
_AUTOMATIC_STRAIN_INFERENCE_KEYS = {
    "strain_candidate",
    "strain_verification",
    "strain_reference",
}


def _clear_prior_automatic_strain_inference(run: TrainingDataRunSpec) -> TrainingDataRunSpec:
    """Remove only relationships previously generated by this inference gate.

    User-authored reference groups remain untouched unless the run carries the
    gate's own strain diagnostic keys.  This makes refresh transactional: stale
    passed relationships cannot survive a changed source cell.
    """

    inference = dict(run.inference)
    generated = bool(_AUTOMATIC_STRAIN_INFERENCE_KEYS & set(inference))
    if not generated:
        return run
    assertions = {
        key: value
        for key, value in dict(run.assertions).items()
        if key not in _AUTOMATIC_STRAIN_ASSERTION_KEYS
    }
    inference = {
        key: value
        for key, value in inference.items()
        if key not in _AUTOMATIC_STRAIN_INFERENCE_KEYS
    }
    return replace(
        run,
        reference_group=None,
        reference_run_id=None,
        assertions=tuple(assertions.items()),
        inference=tuple(inference.items()),
    )

_TEMPERATURE_TOKEN_PATTERN = re.compile(
    r"\.(?:\d+(?:\.\d+)?)K(?=\.|$)",
    re.IGNORECASE,
)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _positive_gamma(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        values = tuple(_float_or_none(item) for item in value)
    else:
        values = (_float_or_none(value),)
    if not values or any(item is None for item in values):
        return None
    return any(float(item) > 0.0 for item in values if item is not None)


def _parse_control_text(element: ET.Element) -> Any:
    text = (element.text or "").strip()
    if not text:
        return None
    type_name = str(element.get("type", "")).lower()
    tokens = text.split()
    if element.tag == "v":
        values: list[Any] = []
        for token in tokens:
            try:
                values.append(float(token))
            except ValueError:
                values.append(token)
        return tuple(values)
    if type_name in {"int", "integer"}:
        try:
            return int(text)
        except ValueError:
            return text
    if type_name in {"logical", "bool", "boolean"}:
        return text.strip().lower() in {"t", "true", ".true."}
    if type_name in {"string"}:
        return text
    try:
        return float(text)
    except ValueError:
        return text


def _xml_metadata_tolerant(path: Path) -> _TolerantXmlMetadata:
    """Recover completed XML records in one bounded-memory streaming pass."""

    symbols: list[str] = []
    initial: np.ndarray | None = None
    cells: list[np.ndarray] = []
    controls: dict[str, Any] = {}
    parse_complete = True
    warning: str | None = None

    def matrix(structure: ET.Element) -> np.ndarray | None:
        basis = structure.find("./crystal/varray[@name='basis']")
        if basis is None:
            return None
        rows: list[list[float]] = []
        for vector in basis.findall("v"):
            if vector.text:
                rows.append([float(token) for token in vector.text.split()])
        if len(rows) != 3 or any(len(row) != 3 for row in rows):
            return None
        result = np.asarray(rows, dtype=np.float64)
        if not np.all(np.isfinite(result)) or float(np.linalg.det(result)) <= 0.0:
            return None
        return result

    stack: list[ET.Element] = []
    try:
        for event, element in ET.iterparse(path, events=("start", "end")):
            if event == "start":
                stack.append(element)
                continue

            ancestors = stack[:-1]
            inside_structure = any(item.tag == "structure" for item in ancestors)
            inside_atom_array = any(
                item.tag == "array" and item.get("name") == "atoms"
                for item in ancestors
            )

            if element.tag in {"i", "v"} and element.get("name"):
                value = _parse_control_text(element)
                if value is not None:
                    controls[str(element.get("name"))] = value
            elif element.tag == "array" and element.get("name") == "atoms":
                atom_set = element.find("set")
                if atom_set is not None and not symbols:
                    for record in atom_set.findall("rc"):
                        first = record.find("c")
                        if first is not None and first.text:
                            symbols.append(first.text.strip())
            elif element.tag == "structure":
                value = matrix(element)
                if value is not None:
                    if element.get("name") == "initialpos":
                        initial = value
                    elif element.get("name") in (None, ""):
                        cells.append(value)

            # Preserve descendants until the containing structure/atom array is
            # complete; clear everything else immediately to keep memory bounded.
            if not inside_structure and not inside_atom_array:
                element.clear()
            if stack:
                stack.pop()
    except ET.ParseError as exc:
        parse_complete = False
        warning = f"partial vasprun.xml recovered before parse error: {exc}"

    return _TolerantXmlMetadata(
        atom_symbols=tuple(symbols),
        initial_cell=initial,
        calculation_cells=tuple(cells),
        controls=controls,
        parse_complete=parse_complete,
        parse_warning=warning,
    )


def _cell_deviation(reference: np.ndarray, cells: tuple[np.ndarray, ...]) -> float:
    denominator = max(float(np.linalg.norm(reference)), np.finfo(float).tiny)
    return max(
        (float(np.linalg.norm(cell - reference)) / denominator for cell in cells),
        default=0.0,
    )


def _observe_run(
    run: TrainingDataRunSpec,
    *,
    base_directory: Path,
    policy: ManifestInferencePolicy,
) -> _RunObservation:
    path, companions = run.resolve(base_directory)
    tolerant = _xml_metadata_tolerant(path)
    symbols = tolerant.atom_symbols
    initial_cell = tolerant.initial_cell
    calculation_cells = tolerant.calculation_cells
    # The review-manifest pass intentionally performs one tolerant XML scan.
    # Full parser/certificate qualification remains a later DATA2 production gate.
    strict_parse_error: str | None = None
    representative = initial_cell if initial_cell is not None else (
        calculation_cells[0] if calculation_cells else None
    )
    cells_for_check = calculation_cells
    if representative is not None and initial_cell is not None:
        cells_for_check = (initial_cell, *calculation_cells)
    deviation = (
        None
        if representative is None
        else _cell_deviation(representative, cells_for_check)
    )

    isif_value = tolerant.controls.get("ISIF")
    try:
        fixed_control = int(isif_value) <= 2
    except (TypeError, ValueError):
        fixed_control = False
    cell_control_kind = "fixed_cell" if fixed_control else "unknown"
    fixed_geometry = (
        deviation is not None
        and deviation <= policy.fixed_cell_relative_tolerance
    )
    fixed_cell = bool(fixed_control and fixed_geometry)

    def control(name: str) -> Any:
        return tolerant.controls.get(name)

    tebeg = _float_or_none(control("TEBEG"))
    teend = _float_or_none(control("TEEND"))
    potim = _float_or_none(control("POTIM"))
    nsw = control("NSW")

    ensemble: str | None = None
    thermostat: str | None = None
    ensemble_basis: str | None = None
    ibrion = control("IBRION")
    mdalgo = control("MDALGO")
    smass = _float_or_none(control("SMASS"))
    isif = control("ISIF")
    gamma = control("LANGEVIN_GAMMA")
    try:
        ibrion_i = int(ibrion) if ibrion is not None else None
        mdalgo_i = int(mdalgo) if mdalgo is not None else None
        isif_i = int(isif) if isif is not None else None
    except (TypeError, ValueError):
        ibrion_i = mdalgo_i = isif_i = None
    gamma_active = _positive_gamma(gamma)
    if (
        ibrion_i == 0
        and mdalgo_i == 3
        and isif_i is not None
        and isif_i <= 2
        and gamma_active is True
    ):
        ensemble = "nvt"
        thermostat = "langevin"
        ensemble_basis = (
            "vasprun.xml controls: IBRION=0, MDALGO=3, fixed cell, "
            "positive LANGEVIN_GAMMA"
        )
    elif (
        ibrion_i == 0
        and mdalgo_i == 3
        and isif_i is not None
        and isif_i <= 2
        and gamma_active is False
    ):
        ensemble = "nve"
        thermostat = "none"
        ensemble_basis = (
            "vasprun.xml controls: IBRION=0, MDALGO=3, fixed cell, zero LANGEVIN_GAMMA"
        )
    elif ibrion_i == 0 and mdalgo_i in {0, 2} and smass == -3.0:
        ensemble = "nve"
        thermostat = "none"
        ensemble_basis = "vasprun.xml controls: IBRION=0, MDALGO in {0,2}, SMASS=-3"
    elif ibrion_i == 0 and mdalgo_i in {0, 2} and smass is not None and smass != -3.0:
        ensemble = "nvt"
        thermostat = "nose_hoover_family"
        ensemble_basis = "vasprun.xml controls: IBRION=0, MDALGO in {0,2}, thermostatted SMASS"
    elif ibrion_i == 0 and mdalgo_i == 4:
        ensemble = "nvt"
        thermostat = "nose_hoover_chain"
        ensemble_basis = "vasprun.xml controls: IBRION=0, MDALGO=4"
    elif ibrion_i == 0 and mdalgo_i == 5:
        ensemble = "nvt"
        thermostat = "csvr"
        ensemble_basis = "vasprun.xml controls: IBRION=0, MDALGO=5"

    assertions = dict(run.assertions)
    if tebeg is not None:
        assertions["target_temperature_start_kelvin"] = tebeg
    if teend is not None:
        assertions["target_temperature_end_kelvin"] = teend
    if (
        tebeg is not None
        and teend is not None
        and abs(tebeg - teend) <= policy.temperature_equality_tolerance_kelvin
    ):
        assertions["target_temperature_kelvin"] = 0.5 * (tebeg + teend)
    if potim is not None:
        assertions["timestep_fs"] = potim
    if nsw is not None:
        try:
            assertions["requested_ionic_steps"] = int(nsw)
        except (TypeError, ValueError):
            pass
    if ensemble is not None:
        assertions["ensemble"] = ensemble
        assertions["ensemble_assertion_basis"] = ensemble_basis
    if thermostat is not None:
        assertions["thermostat_type"] = thermostat
    assertions["cell_control"] = cell_control_kind
    assertions["fixed_cell"] = fixed_cell
    if deviation is not None:
        assertions["fixed_cell_relative_deviation"] = deviation

    inference = dict(run.inference)
    inference["xml_metadata"] = {
        "status": "resolved" if ensemble is not None and representative is not None else "partial",
        "basis": "vasprun.xml",
        "xml_parse_complete": tolerant.parse_complete,
        "xml_parse_warning": tolerant.parse_warning,
        "strict_control_parse_error": strict_parse_error,
        "ensemble_certificate_status": "deferred_to_data2_source_gate",
        "ensemble": ensemble,
        "thermostat": thermostat,
        "cell_control": cell_control_kind,
        "fixed_cell_control": fixed_control,
        "fixed_cell_geometry": fixed_geometry,
        "fixed_cell_relative_deviation": deviation,
        "target_temperature_start_kelvin": tebeg,
        "target_temperature_end_kelvin": teend,
        "timestep_fs": potim,
        "calculation_cell_count": len(calculation_cells),
    }

    return _RunObservation(
        run=run,
        path=path,
        assertions=assertions,
        inference=inference,
        representative_cell=representative,
        cell_count=len(calculation_cells),
        fixed_cell=fixed_cell,
        fixed_cell_relative_deviation=deviation,
        atom_symbols=symbols,
        ensemble=ensemble,
        thermostat=thermostat,
    )


def _parse_strain_candidate(stem: str, policy: ManifestInferencePolicy) -> _StrainFilenameCandidate | None:
    match = _STRAIN_PATTERN.match(stem)
    if match is None:
        return None
    raw = match.group("value")
    percent_marked = raw.endswith("%")
    numeric_text = raw[:-1] if percent_marked else raw
    value = float(numeric_text)
    if percent_marked:
        value /= 100.0
        interpretation = "explicit_percent"
    elif policy.filename_values_at_or_above_one_are_percent and abs(value) >= 1.0:
        value /= 100.0
        interpretation = "percent_by_magnitude"
    else:
        interpretation = "fraction"
    if not np.isfinite(value) or 1.0 + value <= 0.0:
        return None
    kind = match.group("kind").lower()
    return _StrainFilenameCandidate(
        kind=kind,
        signed_value=value,
        raw_value=raw,
        value_interpretation=interpretation,
        reference_prefix=match.group("prefix"),
        reference_suffix=match.group("suffix") or "",
    )


def _without_temperature_tokens(stem: str) -> str:
    """Remove filename temperature tokens without touching strain magnitudes."""

    return _TEMPERATURE_TOKEN_PATTERN.sub("", stem)


def _candidate_reference_stem(candidate: _StrainFilenameCandidate, stem: str) -> bool:
    # A strained filename may omit temperature, include its own target
    # temperature, or be paired to a reference generated at another
    # temperature.  Temperature is therefore removed for identity matching and
    # used later only as a ranking hint after cell geometry passes.
    expected = _without_temperature_tokens(
        candidate.reference_prefix + candidate.reference_suffix
    )
    observed = _without_temperature_tokens(stem)
    return observed.casefold() == expected.casefold()


def _right_polar_stretch(deformation: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    left, singular, right_t = np.linalg.svd(deformation)
    rotation = left @ right_t
    if np.linalg.det(rotation) < 0.0:
        left = left.copy()
        left[:, -1] *= -1.0
        singular = singular.copy()
        singular[-1] *= -1.0
        rotation = left @ right_t
    if np.linalg.det(rotation) <= 0.0 or np.any(singular <= 0.0):
        raise TrainingDataInputError("Deformation has no proper positive polar decomposition.")
    stretch = right_t.T @ np.diag(singular) @ right_t
    cosine = float(np.clip((np.trace(rotation) - 1.0) / 2.0, -1.0, 1.0))
    return rotation, stretch, float(math.acos(cosine))


def _lta_conventional_axes(reference_cell: np.ndarray, policy: ManifestInferencePolicy) -> np.ndarray:
    a, b, c = reference_cell
    conventional = np.asarray((b + c - a, a + c - b, a + b - c), dtype=np.float64)
    norms = np.linalg.norm(conventional, axis=1)
    if np.any(norms <= 0.0):
        raise TrainingDataInputError("LTA primitive cell cannot define conventional axes.")
    axes = conventional / norms[:, None]
    residual = float(np.max(np.abs(axes @ axes.T - np.eye(3))))
    if residual > policy.conventional_axis_orthogonality_tolerance:
        raise TrainingDataInputError(
            "LTA primitive cell conventional axes are not orthogonal within tolerance "
            f"({residual:.6e} > {policy.conventional_axis_orthogonality_tolerance:.6e})."
        )
    return axes


def _matrix_sqrt_spd(matrix: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eigh(matrix)
    if np.any(values <= 0.0):
        raise TrainingDataInputError("Expected shear metric is not positive definite.")
    return vectors @ np.diag(np.sqrt(values)) @ vectors.T


def _expected_lta_stretch(
    reference_cell: np.ndarray,
    candidate: _StrainFilenameCandidate,
    policy: ManifestInferencePolicy,
) -> tuple[np.ndarray, float, str]:
    value = candidate.signed_value
    if candidate.kind == "hydro":
        scale = (1.0 + value) ** (1.0 / 3.0)
        return scale * np.eye(3), 1.0 + value, "relative_volume_change"

    axes = _lta_conventional_axes(reference_cell, policy)
    if candidate.kind == "ortho":
        if abs(value) >= 1.0:
            raise TrainingDataInputError("Orthorhombic strain magnitude must be below one.")
        aligned = np.diag((1.0 + value, 1.0 - value, 1.0 / (1.0 - value**2)))
        return axes.T @ aligned @ axes, 1.0, "signed_axial_delta"

    if candidate.kind == "shear":
        simple_shear = np.eye(3)
        simple_shear[0, 1] = value
        aligned = _matrix_sqrt_spd(simple_shear.T @ simple_shear)
        return axes.T @ aligned @ axes, 1.0, "signed_engineering_shear_gamma"

    raise TrainingDataInputError(f"Unsupported LTA strain kind {candidate.kind!r}.")


def _relative_cell_difference(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.linalg.norm(first - second)) / max(
        float(np.linalg.norm(first)), np.finfo(float).tiny
    )


def _verify_strain(
    strained: _RunObservation,
    reference: _RunObservation,
    candidate: _StrainFilenameCandidate,
    policy: ManifestInferencePolicy,
) -> tuple[bool, dict[str, Any], tuple[str, ...]]:
    reasons: list[str] = []
    if not strained.fixed_cell:
        reasons.append("strained run is not verified fixed-cell MD")
    if not reference.fixed_cell:
        reasons.append("candidate reference is not verified fixed-cell MD")
    if strained.representative_cell is None or reference.representative_cell is None:
        reasons.append("one or both cell matrices are unavailable")
    if strained.atom_symbols and reference.atom_symbols and strained.atom_symbols != reference.atom_symbols:
        reasons.append("ordered atom identities differ")
    if reasons:
        return False, {"status": "rejected"}, tuple(reasons)

    assert strained.representative_cell is not None
    assert reference.representative_cell is not None
    try:
        deformation = np.linalg.solve(reference.representative_cell, strained.representative_cell).T
        observed_volume = float(np.linalg.det(deformation))
        _, observed_stretch, rotation_angle = _right_polar_stretch(deformation)
        expected_stretch, expected_volume, semantics = _expected_lta_stretch(
            reference.representative_cell, candidate, policy
        )
    except (np.linalg.LinAlgError, TrainingDataInputError) as exc:
        return False, {"status": "rejected"}, (str(exc),)

    matrix_residual = float(np.max(np.abs(observed_stretch - expected_stretch)))
    relative_residual = float(np.linalg.norm(observed_stretch - expected_stretch)) / max(
        float(np.linalg.norm(expected_stretch)), np.finfo(float).tiny
    )
    volume_residual = abs(observed_volume - expected_volume)
    if matrix_residual > policy.strain_matrix_absolute_tolerance:
        reasons.append(
            "right-stretch matrix residual exceeds tolerance "
            f"({matrix_residual:.6e} > {policy.strain_matrix_absolute_tolerance:.6e})"
        )
    if volume_residual > policy.strain_volume_ratio_tolerance:
        reasons.append(
            "volume-ratio residual exceeds tolerance "
            f"({volume_residual:.6e} > {policy.strain_volume_ratio_tolerance:.6e})"
        )
    if rotation_angle > policy.maximum_rotation_radians:
        reasons.append(
            "rotation exceeds tolerance "
            f"({rotation_angle:.6e} rad > {policy.maximum_rotation_radians:.6e} rad)"
        )

    evidence = {
        "status": "passed" if not reasons else "rejected",
        "reference_run_id": reference.run.run_id,
        "strain_kind": candidate.kind,
        "raw_filename_value": candidate.raw_value,
        "signed_value": candidate.signed_value,
        "value_interpretation": candidate.value_interpretation,
        "value_semantics": semantics,
        "expected_volume_ratio": expected_volume,
        "observed_volume_ratio": observed_volume,
        "volume_ratio_residual": volume_residual,
        "maximum_absolute_stretch_residual": matrix_residual,
        "relative_stretch_residual": relative_residual,
        "rotation_angle_radians": rotation_angle,
        "policy_digest": policy.policy_digest,
    }
    return not reasons, evidence, tuple(reasons)


def _strain_assertions(candidate: _StrainFilenameCandidate) -> dict[str, Any]:
    strain_class = {
        "hydro": "hydrostatic",
        "ortho": "orthorhombic",
        "shear": "shear",
    }[candidate.kind]
    result: dict[str, Any] = {
        "intended_strain_class": strain_class,
        "intended_strain_signed_value": candidate.signed_value,
        "strain_inference_basis": "filename candidate verified against fixed-cell geometry",
    }
    if candidate.kind == "hydro":
        result["intended_volume_change"] = candidate.signed_value
    else:
        result["intended_strain_magnitude"] = abs(candidate.signed_value)
        result["intended_strain_sign"] = 1 if candidate.signed_value >= 0.0 else -1
    if candidate.kind == "ortho":
        result["strain_definition"] = "diag(1+d,1-d,1/(1-d^2)) in LTA conventional axes"
    elif candidate.kind == "shear":
        result["strain_definition"] = (
            "symmetric right-polar stretch of xy engineering simple shear gamma "
            "in LTA conventional axes"
        )
    else:
        result["strain_definition"] = "isotropic stretch with requested relative volume change"
    return result


def _target_temperature(observation: _RunObservation) -> float | None:
    assertions = observation.assertions
    value = assertions.get("target_temperature_kelvin")
    return _float_or_none(value)


def infer_training_manifest_metadata(
    manifest: TrainingDataManifest,
    *,
    base_directory: str | Path,
    policy: ManifestInferencePolicy | None = None,
) -> ManifestInferenceResult:
    """Populate reviewable XML metadata and promote only geometry-verified strain hints.

    The LTA strain convention is profile-specific.  Other system profiles still
    receive XML-derived temperature, ensemble, thermostat, and fixed-cell metadata,
    but filename strain candidates are not promoted.
    """

    active = ManifestInferencePolicy() if policy is None else policy
    base = Path(base_directory)
    normalized_runs = tuple(
        _clear_prior_automatic_strain_inference(run) for run in manifest.runs
    )
    observations = {
        run.run_id: _observe_run(run, base_directory=base, policy=active)
        for run in normalized_runs
    }

    xml_warnings = [
        f"{run_id}: {dict(observation.inference).get('xml_metadata', {}).get('xml_parse_warning')}"
        for run_id, observation in sorted(observations.items())
        if dict(observation.inference).get("xml_metadata", {}).get("xml_parse_warning")
    ]

    updated: dict[str, TrainingDataRunSpec] = {}
    for run_id, observation in observations.items():
        updated[run_id] = replace(
            observation.run,
            assertions=tuple(observation.assertions.items()),
            inference=tuple(observation.inference.items()),
        )

    warnings: list[str] = list(xml_warnings)
    strain_candidates = 0
    verified = 0
    rejected = 0
    ambiguous = 0
    reference_usage: dict[str, set[str]] = {}

    if manifest.system_profile.strip().lower() == "lta":
        ordered_observations = tuple(sorted(observations.items()))
        strain_candidate_by_run = {
            run_id: _parse_strain_candidate(Path(observation.run.vasprun).stem, active)
            for run_id, observation in ordered_observations
        }
        unstrained_by_identity: dict[
            tuple[str, tuple[str, ...]], list[_RunObservation]
        ] = {}
        for run_id, observation in ordered_observations:
            if strain_candidate_by_run[run_id] is not None:
                continue
            identity = (
                _without_temperature_tokens(Path(observation.run.vasprun).stem).casefold(),
                observation.atom_symbols,
            )
            unstrained_by_identity.setdefault(identity, []).append(observation)

        for run_id, strained in ordered_observations:
            filename_candidate = strain_candidate_by_run[run_id]
            if filename_candidate is None:
                continue
            strain_candidates += 1

            expected_identity = (
                _without_temperature_tokens(
                    filename_candidate.reference_prefix + filename_candidate.reference_suffix
                ).casefold(),
                strained.atom_symbols,
            )
            candidate_refs = list(unstrained_by_identity.get(expected_identity, ()))

            attempt_records: list[dict[str, Any]] = []
            passing: list[_RunObservation] = []
            rejection_reasons: list[str] = []
            for reference in candidate_refs:
                passed, evidence, reasons = _verify_strain(
                    strained, reference, filename_candidate, active
                )
                attempt_records.append({**evidence, "reasons": list(reasons)})
                if passed:
                    passing.append(reference)
                else:
                    rejection_reasons.extend(
                        f"{reference.run.run_id}: {reason}" for reason in reasons
                    )

            status = "rejected"
            selected_refs: list[_RunObservation] = []
            if not candidate_refs:
                rejection_reasons.append("no filename-compatible unstrained reference candidate")
            elif passing:
                # Prefer an exact/nearest target-temperature reference when the
                # strained filename omits temperature.  Temperature is only a
                # ranking hint after geometry has passed; it never overrides a
                # failed cell relationship.
                ranked = list(passing)
                strained_temperature = _target_temperature(strained)
                if strained_temperature is not None:
                    with_temperature = [
                        (abs(float(value) - strained_temperature), reference)
                        for reference in passing
                        if (value := _target_temperature(reference)) is not None
                    ]
                    if with_temperature:
                        minimum = min(distance for distance, _ in with_temperature)
                        ranked = [
                            reference
                            for distance, reference in with_temperature
                            if abs(distance - minimum) <= active.temperature_equality_tolerance_kelvin
                        ]

                representative = ranked[0].representative_cell
                assert representative is not None
                all_equivalent = all(
                    reference.representative_cell is not None
                    and _relative_cell_difference(representative, reference.representative_cell)
                    <= active.reference_cell_relative_tolerance
                    for reference in ranked[1:]
                )
                if len(ranked) == 1 or all_equivalent:
                    selected_refs = ranked
                    status = "passed"
                else:
                    status = "ambiguous"
                    rejection_reasons.append(
                        "multiple equally ranked, non-equivalent reference cells satisfy the filename and strain test"
                    )

            current = updated[run_id]
            inference = dict(current.inference)
            inference["strain_candidate"] = {
                "basis": "filename",
                "kind": filename_candidate.kind,
                "raw_value": filename_candidate.raw_value,
                "signed_value": filename_candidate.signed_value,
                "value_interpretation": filename_candidate.value_interpretation,
                "reference_prefix": filename_candidate.reference_prefix,
                "reference_suffix": filename_candidate.reference_suffix,
            }
            inference["strain_verification"] = {
                "status": status,
                "candidate_reference_run_ids": [item.run.run_id for item in candidate_refs],
                "passing_reference_run_ids": [item.run.run_id for item in passing],
                "selected_reference_run_ids": [item.run.run_id for item in selected_refs],
                "attempts": attempt_records,
                "reasons": rejection_reasons,
            }

            if status == "passed":
                verified += 1
                group = re.sub(
                    r"[^A-Za-z0-9_.-]+",
                    "__",
                    filename_candidate.reference_prefix + "_strain_family",
                ).strip("._-")
                assertions = dict(current.assertions)
                assertions.update(_strain_assertions(filename_candidate))
                updated[run_id] = replace(
                    current,
                    reference_group=group,
                    reference_run_id=(selected_refs[0].run.run_id if len(selected_refs) == 1 else None),
                    assertions=tuple(assertions.items()),
                    inference=tuple(inference.items()),
                )
                for reference in selected_refs:
                    reference_usage.setdefault(reference.run.run_id, set()).add(group)
            else:
                rejected += 1
                if status == "ambiguous":
                    ambiguous += 1
                # Conservative state: retain XML metadata but remove every
                # operational strain assertion and relationship.
                assertions = {
                    key: value
                    for key, value in dict(current.assertions).items()
                    if not key.startswith("intended_strain")
                    and key not in {"strain_definition", "strain_inference_basis", "is_reference_cell"}
                }
                updated[run_id] = replace(
                    current,
                    reference_group=None,
                    reference_run_id=None,
                    assertions=tuple(assertions.items()),
                    inference=tuple(inference.items()),
                )
                warnings.append(
                    f"Strain inference {status} for {run_id}: "
                    + "; ".join(rejection_reasons or ("geometry did not verify the filename intent",))
                )

    # Promote reference runs only after at least one verified strained sibling
    # uses them.  A reference shared by equivalent-temperature runs may belong
    # to one consensus group; conflicting multi-group use remains conservative.
    for reference_id, groups in sorted(reference_usage.items()):
        current = updated[reference_id]
        inference = dict(current.inference)
        if len(groups) == 1:
            group = next(iter(groups))
            assertions = dict(current.assertions)
            assertions.update(
                {
                    "is_reference_cell": True,
                    "intended_strain_class": "unstrained",
                    "strain_inference_basis": "verified reference for filename-derived strain family",
                }
            )
            inference["strain_reference"] = {
                "status": "verified",
                "reference_group": group,
                "policy_digest": active.policy_digest,
            }
            updated[reference_id] = replace(
                current,
                reference_group=group,
                reference_run_id=None,
                assertions=tuple(assertions.items()),
                inference=tuple(inference.items()),
            )
        else:
            warnings.append(
                f"Reference run {reference_id} was proposed for multiple strain groups {sorted(groups)}; "
                "the relationship was not promoted."
            )

    resolved_xml = sum(
        1
        for observation in observations.values()
        if observation.ensemble is not None and observation.representative_cell is not None
    )
    fixed_count = sum(1 for observation in observations.values() if observation.fixed_cell)
    notes = tuple(
        dict.fromkeys(
            (
                *manifest.notes,
                "XML controls and fixed-cell geometry were inferred automatically and remain subject to manifest approval.",
                "LTA filename strain hints were promoted only after exact profile-specific cell-matrix verification.",
                *warnings,
            )
        )
    )
    inferred_manifest = TrainingDataManifest(
        dataset_id=manifest.dataset_id,
        system_profile=manifest.system_profile,
        runs=tuple(updated.values()),
        manifest_version=TRAINING_DATA_MANIFEST_VERSION,
        notes=notes,
    )
    return ManifestInferenceResult(
        manifest=inferred_manifest,
        policy_digest=active.policy_digest,
        resolved_xml_metadata_runs=resolved_xml,
        fixed_cell_runs=fixed_count,
        strain_candidate_runs=strain_candidates,
        verified_strain_runs=verified,
        rejected_strain_runs=rejected,
        ambiguous_strain_runs=ambiguous,
        warnings=tuple(warnings),
    )
