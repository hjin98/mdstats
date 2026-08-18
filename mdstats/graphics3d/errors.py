"""Exception hierarchy for the universal GFX3D scene contracts."""


class Graphics3DError(Exception):
    """Base class for universal 3-D graphics failures."""


class Graphics3DValidationError(Graphics3DError):
    """Raised when a scene, layer, selection, or primitive is malformed."""


class Graphics3DRegistryError(Graphics3DError):
    """Raised for deterministic layer-registry contract violations."""


class Graphics3DDependencyError(Graphics3DError):
    """Raised when a scientific dependency cannot be planned or resolved."""
