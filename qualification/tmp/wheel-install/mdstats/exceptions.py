"""Exceptions raised by :mod:`mdstats` frame readers and analyses."""


class FrameCollectionError(Exception):
    """Base class for normalized frame-collection errors."""


class MissingPositionError(FrameCollectionError):
    """Raised when no complete atomic coordinate field is available."""


class MissingTimeError(FrameCollectionError):
    """Raised when a required physical time axis cannot be established."""


class AtomIdentityError(FrameCollectionError):
    """Raised when persistent atom identities change across frames."""


class SpeciesConsistencyError(FrameCollectionError):
    """Raised when an atom changes species or mass across frames."""


class CoordinateFormatError(FrameCollectionError):
    """Raised for missing, partial, or unsupported coordinate columns."""


class UnwrappingError(FrameCollectionError):
    """Raised when periodic unwrapping cannot be performed safely."""


class UnitConversionError(FrameCollectionError):
    """Raised for unknown or unsupported source units."""


class IncompleteFieldError(FrameCollectionError):
    """Raised when an optional frame field is only partly present."""


class InvalidCellError(FrameCollectionError):
    """Raised when a simulation cell is singular or malformed."""


class AnalysisRequirementError(FrameCollectionError):
    """Raised when a collection lacks data or semantics required by analysis."""


class InsufficientFramesError(AnalysisRequirementError):
    """Raised when an analysis requires more stored frames."""


class MissingVelocityError(AnalysisRequirementError):
    """Raised when an analysis requires velocities that are unavailable."""


class MissingTimeAxisError(AnalysisRequirementError):
    """Raised when an analysis requires physical frame times."""


class TrajectoryRequiredError(AnalysisRequirementError):
    """Raised when an ordered temporal analysis receives an ensemble."""


class VaspContcarTrajectoryError(FrameCollectionError):
    """Base error for watcher-generated concatenated VASP CONTCAR input."""


class TruncatedVaspRecordError(VaspContcarTrajectoryError):
    """Raised when a concatenated CONTCAR record ends before all sections."""


class MissingNativeVelocityError(VaspContcarTrajectoryError):
    """Raised when the required native Cartesian ion velocity block is absent."""


class InconsistentVaspRecordError(VaspContcarTrajectoryError):
    """Raised when concatenated records disagree on fixed trajectory identity."""
