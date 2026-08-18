"""Plotting compatibility adapters for analysis-owned density diagnostics."""

from __future__ import annotations

from typing import Any

from ..analysis.density import diagnostics as _common
from ..analysis.density.numerical_errors import (
    DensityNumericalInputError,
    DensityNumericalResourceError,
)
from .graph_errors import GraphAdapterError, GraphComplexityError

CELL_EQUIVALENCE_ABSOLUTE_TOLERANCE = _common.CELL_EQUIVALENCE_ABSOLUTE_TOLERANCE
CELL_EQUIVALENCE_RELATIVE_TOLERANCE = _common.CELL_EQUIVALENCE_RELATIVE_TOLERANCE
SPREAD_QUANTILE_METHOD = _common.SPREAD_QUANTILE_METHOD
PERIODIC_MEAN_DIAGNOSTIC_SCHEMA = _common.PERIODIC_MEAN_DIAGNOSTIC_SCHEMA
PERIODIC_SPREAD_DIAGNOSTIC_SCHEMA = _common.PERIODIC_SPREAD_DIAGNOSTIC_SCHEMA
RECIPROCAL_RESOLUTION_SCHEMA = _common.RECIPROCAL_RESOLUTION_SCHEMA
CELL_EQUIVALENCE_SCHEMA = _common.CELL_EQUIVALENCE_SCHEMA

PeriodicMeanPolicy = _common.PeriodicMeanPolicy
CellEquivalenceReport = _common.CellEquivalenceReport
ReciprocalResolutionDiagnostic = _common.ReciprocalResolutionDiagnostic
PeriodicMeanDiagnostic = _common.PeriodicMeanDiagnostic
PeriodicSpreadDiagnostics = _common.PeriodicSpreadDiagnostics
BasinSpreadDiagnostic = _common.BasinSpreadDiagnostic
SpreadConvergenceDiagnostic = _common.SpreadConvergenceDiagnostic


def _translate(callable_: Any, /, *args: Any, **kwargs: Any) -> Any:
    try:
        return callable_(*args, **kwargs)
    except DensityNumericalResourceError as error:
        raise GraphComplexityError(str(error)) from error
    except DensityNumericalInputError as error:
        raise GraphAdapterError(str(error)) from error


def evaluate_cell_equivalence(*args: Any, **kwargs: Any) -> CellEquivalenceReport:
    return _translate(_common.evaluate_cell_equivalence, *args, **kwargs)


def require_equivalent_laboratory_density_cells(
    *args: Any, **kwargs: Any
) -> CellEquivalenceReport:
    return _translate(
        _common.require_equivalent_laboratory_density_cells, *args, **kwargs
    )


def reciprocal_resolution_diagnostic(
    *args: Any, **kwargs: Any
) -> ReciprocalResolutionDiagnostic:
    return _translate(_common.reciprocal_resolution_diagnostic, *args, **kwargs)


def periodic_frechet_mean_diagnostic(
    *args: Any, **kwargs: Any
) -> PeriodicMeanDiagnostic:
    return _translate(_common.periodic_frechet_mean_diagnostic, *args, **kwargs)


def periodic_item_spread_diagnostics(
    *args: Any, **kwargs: Any
) -> PeriodicSpreadDiagnostics:
    return _translate(_common.periodic_item_spread_diagnostics, *args, **kwargs)


def spread_basin_labels_from_site_assignment(*args: Any, **kwargs: Any) -> Any:
    return _translate(_common.spread_basin_labels_from_site_assignment, *args, **kwargs)


def spread_basin_labels_from_final_segmentation(*args: Any, **kwargs: Any) -> Any:
    return _translate(_common.spread_basin_labels_from_final_segmentation, *args, **kwargs)


__all__ = [
    "CELL_EQUIVALENCE_ABSOLUTE_TOLERANCE",
    "CELL_EQUIVALENCE_RELATIVE_TOLERANCE",
    "SPREAD_QUANTILE_METHOD",
    "BasinSpreadDiagnostic",
    "CellEquivalenceReport",
    "PeriodicMeanDiagnostic",
    "PeriodicMeanPolicy",
    "PeriodicSpreadDiagnostics",
    "SpreadConvergenceDiagnostic",
    "ReciprocalResolutionDiagnostic",
    "evaluate_cell_equivalence",
    "periodic_frechet_mean_diagnostic",
    "periodic_item_spread_diagnostics",
    "spread_basin_labels_from_final_segmentation",
    "spread_basin_labels_from_site_assignment",
    "reciprocal_resolution_diagnostic",
    "require_equivalent_laboratory_density_cells",
]
