"""Analysis-domain errors for common scientific density numerics.

These exceptions deliberately contain no plotting, mesh, browser, or graph
terminology.  Presentation adapters may translate them at their boundary.
"""

from __future__ import annotations


class DensityNumericalError(Exception):
    """Base class for backend-neutral density numerical failures."""


class DensityNumericalInputError(DensityNumericalError, ValueError):
    """Invalid cell, grid, sample, weight, or numerical-policy input."""


class DensityNumericalResourceError(DensityNumericalError, RuntimeError):
    """A valid numerical request exceeds an explicit scientific limit."""


class DensityNumericalSerializationError(DensityNumericalError, ValueError):
    """A serialized numerical record is unsupported or inconsistent."""
