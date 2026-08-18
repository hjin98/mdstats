"""Plotting compatibility adapters for analysis-owned broadening diagnostics."""

from __future__ import annotations

from typing import Any

from ..analysis.density import broadening as _common
from ..analysis.density.numerical_errors import (
    DensityNumericalInputError,
    DensityNumericalResourceError,
)
from .graph_errors import GraphAdapterError, GraphComplexityError
from .runtime_resources import resolve_density_resource_limits

DENSITY_BROADENING_SCHEMA = _common.DENSITY_BROADENING_SCHEMA
ArtificialBroadeningDiagnostic = _common.ArtificialBroadeningDiagnostic
PeriodicGaussianStencilMoments = _common.PeriodicGaussianStencilMoments


def _translate(callable_: Any, /, *args: Any, **kwargs: Any) -> Any:
    try:
        return callable_(*args, **kwargs)
    except DensityNumericalResourceError as error:
        raise GraphComplexityError(str(error)) from error
    except DensityNumericalInputError as error:
        raise GraphAdapterError(str(error)) from error



def periodic_gaussian_stencil_moments(*args: Any, **kwargs: Any) -> PeriodicGaussianStencilMoments:
    if (
        kwargs.get("max_workspace_bytes") is None
        or kwargs.get("max_candidate_contributions") is None
    ):
        budget, _model, derived = resolve_density_resource_limits()
        if kwargs.get("max_workspace_bytes") is None:
            kwargs["max_workspace_bytes"] = budget.max_memory_bytes
        if kwargs.get("max_candidate_contributions") is None:
            kwargs["max_candidate_contributions"] = derived[
                "max_density_stencil_values"
            ]
    return _translate(_common.periodic_gaussian_stencil_moments, *args, **kwargs)


def cic_assignment_covariance(*args: Any, **kwargs: Any) -> Any:
    return _translate(_common.cic_assignment_covariance, *args, **kwargs)


def effective_artificial_broadening(*args: Any, **kwargs: Any) -> ArtificialBroadeningDiagnostic:
    if (
        kwargs.get("max_workspace_bytes") is None
        or kwargs.get("max_candidate_contributions") is None
    ):
        budget, _model, derived = resolve_density_resource_limits()
        if kwargs.get("max_workspace_bytes") is None:
            kwargs["max_workspace_bytes"] = budget.max_memory_bytes
        if kwargs.get("max_candidate_contributions") is None:
            kwargs["max_candidate_contributions"] = derived[
                "max_density_stencil_values"
            ]
    return _translate(_common.effective_artificial_broadening, *args, **kwargs)


__all__ = [
    "ArtificialBroadeningDiagnostic",
    "DENSITY_BROADENING_SCHEMA",
    "PeriodicGaussianStencilMoments",
    "periodic_gaussian_stencil_moments",
    "cic_assignment_covariance",
    "effective_artificial_broadening",
]
