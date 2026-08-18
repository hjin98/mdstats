"""Public exception hierarchy for graph visualization."""


class GraphVisualizationError(Exception):
    """Base class for graph-visualization failures."""


class GraphViewValidationError(GraphVisualizationError):
    """Raised when a decorated graph view is malformed."""


class GraphFilterError(GraphVisualizationError):
    """Raised when focus or filtering requests are invalid."""


class GraphStyleError(GraphVisualizationError):
    """Raised when style configuration is invalid or incomplete."""


class GraphLayoutError(GraphVisualizationError):
    """Raised when graph layout or projection fails."""


class GraphComplexityError(GraphVisualizationError):
    """Raised when a graph exceeds an explicit rendering complexity policy."""


class GraphAdapterError(GraphVisualizationError):
    """Raised when a scientific graph cannot be adapted consistently."""


class GraphOptionalDependencyError(GraphVisualizationError):
    """Raised when an explicitly requested optional backend is unavailable."""


class GraphUnsupportedFeatureError(GraphVisualizationError):
    """Raised for graph features unsupported by the selected renderer."""
