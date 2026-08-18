"""Universal renderer-independent 3-D graphics contracts for :mod:`mdstats`."""

from .contracts import (
    GRAPHICS_DEPENDENCY_KEY_SCHEMA,
    GRAPHICS_LAYER_REQUEST_SCHEMA,
    GRAPHICS_PREPARED_LAYER_SCHEMA,
    GRAPHICS_PREPARED_SCENE_SCHEMA,
    GRAPHICS_SCENE_REQUEST_SCHEMA,
    GRAPHICS_SELECTION_SCHEMA,
    GraphicsDependencyKey,
    GraphicsDependencyRequest,
    GraphicsLayer3DRequest,
    GraphicsScene3DRequest,
    GraphicsSelection,
    PreparedGraphicsLayer3D,
    PreparedGraphicsScene3D,
)
from .context import GraphicsSceneContext
from .dependencies import GraphicsDependencyPlanEntry, deduplicate_dependency_requests
from .errors import (
    Graphics3DDependencyError,
    Graphics3DError,
    Graphics3DRegistryError,
    Graphics3DValidationError,
)
from .identity import canonical_json, canonical_value, identity_digest
from .legacy import (
    LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA,
    adapt_framework_dynamics_render_result,
    adapt_framework_dynamics_scene,
)
from .manifest import GRAPHICS_SCENE_MANIFEST_SCHEMA, GraphicsSceneManifest
from .primitives import (
    ArrowSet3D,
    CellWireframe3D,
    GraphicsPrimitive3D,
    LegendGroup,
    PointSet3D,
    PolylineSet3D,
    SegmentSet3D,
    TextLabelSet3D,
    TriangleMesh3D,
)
from .registry import (
    DEFAULT_GRAPHICS_LAYER_REGISTRY,
    GraphicsLayer3DAdapter,
    GraphicsLayerRegistration,
    GraphicsLayerRegistry,
)
from .render_result import Graphics3DRenderResult, GraphicsLayerRenderResult

from .layers import (
    GFX3D2_LAYER_SCHEMA,
    GFX3D4_LAYER_SCHEMA,
    AtomicConnectivityLayer,
    AtomicDensityLayer,
    AtomicTrajectoryLayer,
    FrameworkTopologyLayer,
    register_builtin_graphics3d_layers,
)

from .providers import (
    CONNECTIVITY_PRODUCT_PROVIDER,
    DENSITY_PRODUCT_PROVIDER,
    FRAMEWORK_PRODUCT_PROVIDER,
    TRAJECTORY_PRODUCT_PROVIDER,
    Graphics3DDependencySource,
    GraphicsDensityProduct,
    GraphicsScientificProduct,
)
from .lta_preset import LTAGraphics3DDependencySource
from .prepare import prepare_graphics3d_scene
from .plotly_renderer import GFX3D5_PLOTLY_SCHEMA, render_graphics3d_plotly
from .browser import GraphicsBrowserBudget, GraphicsBrowserPayload, measure_browser_payload, scale_browser_payload
from .view import resolve_camera, resolve_cell_mode, resolve_periodic_image_shifts, resolve_view_visibility

register_builtin_graphics3d_layers(DEFAULT_GRAPHICS_LAYER_REGISTRY)
from .scene import build_graphics_scene_manifest, plan_graphics_scene_dependencies

__all__ = [name for name in globals() if not name.startswith("_")]

from .config import (
    BUILTIN_PRESETS,
    GFX3D_CONFIG_SCHEMA,
    LTA_MIXED_ALKALI_PRESET,
    CompiledGraphics3DConfig,
    compile_graphics3d_config,
    layer_from_mapping,
    load_graphics3d_toml,
    parse_layer_shorthand,
    selection_from_mapping,
)
