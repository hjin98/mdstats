"""Declarative configuration compilation for the universal GFX3D CLI."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .contracts import GraphicsLayer3DRequest, GraphicsScene3DRequest, GraphicsSelection
from .errors import Graphics3DValidationError

GFX3D_CONFIG_SCHEMA = "mdstats.graphics3d.cli-config.v1"
LTA_MIXED_ALKALI_PRESET = "lta-mixed-alkali-density"
BUILTIN_PRESETS = (LTA_MIXED_ALKALI_PRESET,)
_ALLOWED_TOP_LEVEL = frozenset({"scene", "input", "resources", "output", "layer"})
_ALLOWED_SCENE = frozenset({
    "preset", "title", "registration", "trajectory_display_mode", "display_cell",
    "connectivity_mode", "occupancy_threshold", "density_grid_interval",
    "density_gaussian_to_grid_ratio", "density_adaptive_smearing",
    "density_max_smearing_to_sample_sd_ratio", "density_sample_sd_quantile",
    "projection", "camera", "periodic_images", "visible_layers", "cell_mode",
    "show_axes", "background", "width", "height",
})
_ALLOWED_INPUT = frozenset({
    "format", "stride", "timestep_fs", "lammps_log", "lammps_units",
    "lammps_timestep", "lammps_type_map", "topology", "topology_cache",
    "no_topology_cache", "framework_formation_cutoff", "framework_breaking_cutoff",
})
_ALLOWED_RESOURCES = frozenset({"max_memory", "max_threads", "wall_time_target"})
_ALLOWED_OUTPUT = frozenset({"path", "manifest", "browser_profile", "max_browser_faces"})
_ALLOWED_LAYER = frozenset({
    "type", "name", "enabled", "visible", "initially_visible", "priority",
    "selection", "analysis", "render", "metadata",
})
_ALLOWED_SELECTION = frozenset(GraphicsSelection.__dataclass_fields__)


def _load_tomllib():
    try:
        import tomllib  # type: ignore
    except ImportError:  # pragma: no cover - Python 3.10 only
        try:
            import tomli as tomllib  # type: ignore
        except ImportError as error:  # pragma: no cover
            raise Graphics3DValidationError(
                "Python 3.10 requires the 'tomli' package to read GFX3D TOML configuration."
            ) from error
    return tomllib


def load_graphics3d_toml(path: str | Path) -> dict[str, Any]:
    """Load one strict GFX3D TOML file."""
    source = Path(path).expanduser().resolve()
    try:
        with source.open("rb") as handle:
            payload = _load_tomllib().load(handle)
    except OSError as error:
        raise Graphics3DValidationError(f"Could not read GFX3D config {source}: {error}") from error
    if not isinstance(payload, dict):
        raise Graphics3DValidationError("GFX3D TOML root must be a table.")
    unknown = set(payload) - _ALLOWED_TOP_LEVEL
    if unknown:
        raise Graphics3DValidationError(
            "Unknown GFX3D TOML top-level tables/keys: " + ", ".join(sorted(unknown))
        )
    for table_name, allowed in (("scene", _ALLOWED_SCENE), ("input", _ALLOWED_INPUT), ("resources", _ALLOWED_RESOURCES), ("output", _ALLOWED_OUTPUT)):
        table = payload.get(table_name, {})
        if not isinstance(table, dict):
            raise Graphics3DValidationError(f"GFX3D TOML [{table_name}] must be a table.")
        unknown_table = set(table) - allowed
        if unknown_table:
            raise Graphics3DValidationError(
                f"Unknown keys in GFX3D [{table_name}]: " + ", ".join(sorted(unknown_table))
            )
    layers = payload.get("layer", [])
    if not isinstance(layers, list):
        raise Graphics3DValidationError("GFX3D TOML [[layer]] entries must form an array of tables.")
    for position, layer in enumerate(layers):
        if not isinstance(layer, dict):
            raise Graphics3DValidationError(f"GFX3D TOML layer #{position + 1} must be a table.")
        unknown_layer = set(layer) - _ALLOWED_LAYER
        if unknown_layer:
            raise Graphics3DValidationError(
                f"Unknown keys in GFX3D layer #{position + 1}: " + ", ".join(sorted(unknown_layer))
            )
        selection = layer.get("selection", {})
        if not isinstance(selection, dict):
            raise Graphics3DValidationError(f"GFX3D layer #{position + 1} selection must be a table.")
        unknown_selection = set(selection) - _ALLOWED_SELECTION
        if unknown_selection:
            raise Graphics3DValidationError(
                f"Unknown selection keys in GFX3D layer #{position + 1}: "
                + ", ".join(sorted(unknown_selection))
            )
    payload["_config_path"] = str(source)
    return payload


def _pairs_from_value(value: Any) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise Graphics3DValidationError("selection.pairs must be an array.")
    for item in value:
        if isinstance(item, str):
            text = item.strip()
            if "-" not in text:
                raise Graphics3DValidationError(
                    f"Pair selector {text!r} must use ELEMENT-ELEMENT syntax."
                )
            left, right = text.split("-", 1)
            pairs.append((left.strip(), right.strip()))
        else:
            try:
                left, right = item
            except Exception as error:
                raise Graphics3DValidationError(
                    "selection.pairs entries must be 'Na-O' strings or two-element arrays."
                ) from error
            pairs.append((str(left), str(right)))
    return tuple(pairs)


def selection_from_mapping(value: Mapping[str, Any] | None) -> GraphicsSelection:
    raw = dict(value or {})
    if "pairs" in raw:
        raw["pairs"] = _pairs_from_value(raw["pairs"])
    for field_name in (
        "species", "atom_indices", "atom_ids", "framework_roles", "topology_ids",
        "ring_sizes", "ring_ids", "cage_types", "cage_ids", "site_types", "site_ids",
        "state_ids", "transitions",
    ):
        if field_name in raw and raw[field_name] is None:
            raw[field_name] = ()
        elif field_name in raw and isinstance(raw[field_name], list):
            raw[field_name] = tuple(raw[field_name])
    return GraphicsSelection(**raw)


def layer_from_mapping(value: Mapping[str, Any]) -> GraphicsLayer3DRequest:
    if "type" not in value:
        raise Graphics3DValidationError("Every [[layer]] table requires type = '...'.")
    layer_type = str(value["type"]).strip().lower()
    selection = selection_from_mapping(value.get("selection", {}))
    name = str(value.get("name") or _default_layer_name(layer_type, selection)).strip()
    visible = value.get("initially_visible", value.get("visible", True))
    for key in ("analysis", "render", "metadata"):
        if key in value and not isinstance(value[key], Mapping):
            raise Graphics3DValidationError(f"Layer {name!r} {key} must be a table/mapping.")
    return GraphicsLayer3DRequest(
        name=name,
        layer_type=layer_type,
        selection=selection,
        analysis_options=dict(value.get("analysis", {})),
        render_options=dict(value.get("render", {})),
        enabled=bool(value.get("enabled", True)),
        initially_visible=bool(visible),
        render_priority=int(value.get("priority", 0)),
        metadata=dict(value.get("metadata", {})),
    )


def _default_layer_name(layer_type: str, selection: GraphicsSelection) -> str:
    if selection.pairs:
        target = ",".join(f"{a}-{b}" for a, b in selection.pairs)
        return f"{layer_type}:{target}"
    if selection.species:
        return f"{layer_type}:{','.join(selection.species)}"
    if selection.atom_indices:
        return f"{layer_type}:atoms-{','.join(str(v) for v in selection.atom_indices)}"
    return layer_type


def parse_layer_shorthand(text: str) -> GraphicsLayer3DRequest:
    """Parse ``TYPE[:SELECTOR][@NAME]`` into one canonical layer request."""
    raw = str(text).strip()
    if not raw:
        raise Graphics3DValidationError("--layer cannot be empty.")
    body, separator, explicit_name = raw.partition("@")
    if separator and not explicit_name.strip():
        raise Graphics3DValidationError("Layer shorthand after '@' must contain a nonempty name.")
    layer_type, colon, selector = body.partition(":")
    layer_type = layer_type.strip().lower()
    if layer_type not in {"framework", "connectivity", "trajectory", "density"}:
        raise Graphics3DValidationError(
            f"Unknown built-in GFX3D layer type {layer_type!r}; choose framework, connectivity, trajectory, or density."
        )
    selection = GraphicsSelection()
    selector = selector.strip()
    if colon:
        if not selector:
            raise Graphics3DValidationError("Layer shorthand after ':' must contain a selector.")
        tokens = tuple(part.strip() for part in selector.split(",") if part.strip())
        if layer_type == "framework":
            raise Graphics3DValidationError("The framework shorthand does not accept a selector in GFX3D-3.")
        if layer_type == "connectivity" and any("-" in token for token in tokens):
            if not all("-" in token for token in tokens):
                raise Graphics3DValidationError(
                    "Connectivity shorthand cannot mix pair and species selectors; use TOML for compound selections."
                )
            selection = GraphicsSelection(pairs=tuple(tuple(token.split("-", 1)) for token in tokens))
        else:
            selection = GraphicsSelection(species=tokens)
    name = explicit_name.strip() if separator else _default_layer_name(layer_type, selection)
    return GraphicsLayer3DRequest(name=name, layer_type=layer_type, selection=selection)


def _preset_layers(preset: str, *, present_species: Sequence[str] | None) -> tuple[GraphicsLayer3DRequest, ...]:
    key = str(preset).strip().lower()
    if key != LTA_MIXED_ALKALI_PRESET:
        raise Graphics3DValidationError(
            f"Unknown GFX3D preset {preset!r}; available: {', '.join(BUILTIN_PRESETS)}."
        )
    if present_species is None:
        raise Graphics3DValidationError(
            f"Preset {LTA_MIXED_ALKALI_PRESET!r} requires source species resolution before expansion."
        )
    ordered = tuple(symbol for symbol in ("Si", "Al", "O", "Li", "Na", "K") if symbol in set(present_species))
    mobile = tuple(symbol for symbol in ("Li", "Na", "K") if symbol in set(ordered))
    layers: list[GraphicsLayer3DRequest] = [
        GraphicsLayer3DRequest(name="framework", layer_type="framework"),
        GraphicsLayer3DRequest(name="atomic connectivity", layer_type="connectivity"),
        GraphicsLayer3DRequest(
            name="atomic trajectories",
            layer_type="trajectory",
            selection=GraphicsSelection(species=ordered),
            render_options={"line_width": 1.6, "opacity": 0.28, "show_legend": True},
        ),
    ]
    for symbol in ordered:
        layers.append(
            GraphicsLayer3DRequest(
                name=f"{symbol} density",
                layer_type="density",
                selection=GraphicsSelection(species=(symbol,)),
                render_options={
                    "mass_fractions": [0.50, 0.80, 0.95],
                    "inner_opacity": 0.22,
                    "outer_opacity": 0.04,
                    "render_mode": "mesh",
                    "show_samples": False,
                    "show_legend": True,
                },
                metadata={"preset_mobile_species": symbol in mobile},
            )
        )
    return tuple(layers)


@dataclass(frozen=True, slots=True)
class CompiledGraphics3DConfig:
    request: GraphicsScene3DRequest
    input_options: Mapping[str, Any] = field(default_factory=dict)
    preset: str | None = None
    config_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_options", MappingProxyType(dict(self.input_options)))


def compile_graphics3d_config(
    payload: Mapping[str, Any] | None = None,
    *,
    preset: str | None = None,
    cli_layers: Sequence[str] = (),
    present_species: Sequence[str] | None = None,
    cli_scene: Mapping[str, Any] | None = None,
    cli_resources: Mapping[str, Any] | None = None,
    cli_output: Mapping[str, Any] | None = None,
    cli_input: Mapping[str, Any] | None = None,
) -> CompiledGraphics3DConfig:
    """Compile defaults/preset/TOML/CLI into one canonical scene request.

    Precedence is deterministic: built-in defaults < preset < TOML < explicit CLI.
    A TOML ``[[layer]]`` list replaces preset layers; repeated ``--layer`` values
    replace both TOML and preset layers.
    """
    cfg = dict(payload or {})
    raw_scene_cfg = dict(cfg.get("scene", {}))
    input_cfg = dict(cfg.get("input", {}))
    resources_cfg = dict(cfg.get("resources", {}))
    output_cfg = dict(cfg.get("output", {}))
    if not all(isinstance(value, Mapping) for value in (raw_scene_cfg, input_cfg, resources_cfg, output_cfg)):
        raise Graphics3DValidationError("[scene], [input], [resources], and [output] must be TOML tables.")

    configured_preset = raw_scene_cfg.pop("preset", None)
    selected_preset = preset or configured_preset
    scene_cfg: dict[str, Any] = {}
    if selected_preset:
        if str(selected_preset).strip().lower() != LTA_MIXED_ALKALI_PRESET:
            raise Graphics3DValidationError(
                f"Unknown GFX3D preset {selected_preset!r}; available: {', '.join(BUILTIN_PRESETS)}."
            )
        scene_cfg.update({
            "registration": "framework_registered",
            "trajectory_display_mode": "folded",
            "display_cell": "reference",
            "connectivity_mode": "occupancy",
            "occupancy_threshold": 0.95,
            "density_grid_interval": 0.20,
            "density_gaussian_to_grid_ratio": 2.0,
            "density_adaptive_smearing": True,
            "density_max_smearing_to_sample_sd_ratio": 0.50,
            "density_sample_sd_quantile": 0.10,
            "projection": "orthographic",
        })
        output_cfg = {"browser_profile": "balanced", **output_cfg}
    scene_cfg.update(raw_scene_cfg)
    layers: tuple[GraphicsLayer3DRequest, ...] = ()
    if selected_preset:
        layers = _preset_layers(str(selected_preset), present_species=present_species)
    toml_layers = cfg.get("layer", [])
    if toml_layers:
        layers = tuple(layer_from_mapping(value) for value in toml_layers)
    if cli_layers:
        layers = tuple(parse_layer_shorthand(value) for value in cli_layers)
    if not layers:
        raise Graphics3DValidationError(
            "No GFX3D layers were requested. Supply [[layer]], --layer, or --preset."
        )

    if cli_scene:
        scene_cfg.update({k: v for k, v in cli_scene.items() if v is not None})
    if cli_resources:
        resources_cfg.update({k: v for k, v in cli_resources.items() if v is not None})
    if cli_output:
        output_cfg.update({k: v for k, v in cli_output.items() if v is not None})
    if cli_input:
        input_cfg.update({k: v for k, v in cli_input.items() if v is not None})

    # Pull view-only settings out of scene for an explicit identity boundary.
    view_keys = ("projection", "camera", "periodic_images", "visible_layers", "cell_mode", "show_axes", "background", "width", "height")
    view = {key: scene_cfg.pop(key) for key in view_keys if key in scene_cfg}
    request = GraphicsScene3DRequest(
        layers=layers,
        scene_options=scene_cfg,
        view=view,
        resources=resources_cfg,
        output=output_cfg,
        metadata={
            "config_schema": GFX3D_CONFIG_SCHEMA,
            "preset": selected_preset,
            "config_path": cfg.get("_config_path"),
        },
    )
    return CompiledGraphics3DConfig(
        request=request,
        input_options=input_cfg,
        preset=None if selected_preset is None else str(selected_preset),
        config_path=cfg.get("_config_path"),
    )
