"""Universal configurable 3-D graphics command line interface (GFX3D-3)."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

from mdstats._version import __version__
from mdstats.exceptions import FrameCollectionError
from mdstats.plotting.graph_errors import GraphVisualizationError
from mdstats.progress import TextProgressPort

from .config import (
    BUILTIN_PRESETS,
    LTA_MIXED_ALKALI_PRESET,
    compile_graphics3d_config,
    load_graphics3d_toml,
)
from .context import GraphicsSceneContext
from .errors import Graphics3DError, Graphics3DValidationError
from .lta_preset import (
    LTAGraphics3DDependencySource,
    detect_present_species,
    read_input_trajectory,
)
from .manifest import GraphicsSceneManifest
from .plotly_renderer import render_graphics3d_plotly
from .prepare import prepare_graphics3d_scene
from .scene import build_graphics_scene_manifest

GFX3D_CLI_SCHEMA = "mdstats.graphics3d.cli.v1"
DEFAULT_OUTPUT = Path("graphics3d.html")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()



def _exception_chain_message(error: BaseException) -> str:
    """Return a compact causal chain without requiring a debug traceback."""
    parts: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = str(current).strip()
        part = f"{type(current).__name__}: {text}" if text else type(current).__name__
        if not parts or part != parts[-1]:
            parts.append(part)
        current = current.__cause__ if current.__cause__ is not None else current.__context__
    return " <- ".join(parts)

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdstats-3d",
        description=(
            "Compose configurable mdstats 3-D scientific scenes from independent "
            "framework, atomic-connectivity, trajectory, and density layers."
        ),
    )
    parser.add_argument("trajectory", type=Path, help="Input trajectory file.")
    parser.add_argument("--config", type=Path, help="Declarative GFX3D TOML scene configuration.")
    parser.add_argument("--preset", choices=BUILTIN_PRESETS, help="Built-in scene preset.")
    parser.add_argument(
        "--layer",
        action="append",
        default=[],
        metavar="TYPE[:SELECTOR][@NAME]",
        help=(
            "Declare a layer. Repeating --layer replaces the configured/preset layer list. "
            "Examples: framework, trajectory:Na, connectivity:Na-O, density:Na@Na-density."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("auto", "vasp-xml", "vasp-xdatcar", "vasp-contcar-trajectory", "lammps-dump"),
        default=None,
        help="Input trajectory format (default: auto).",
    )
    parser.add_argument("--stride", type=int, default=None, help="Read every Nth frame.")
    parser.add_argument("--timestep-fs", type=float, default=None)
    parser.add_argument("--lammps-log", type=Path, default=None)
    parser.add_argument("--lammps-units", choices=("metal", "real", "si"), default=None)
    parser.add_argument("--lammps-timestep", type=float, default=None)
    parser.add_argument(
        "--lammps-type-map",
        default=None,
        help='Numeric type mapping such as "1=Si,2=Al,3=O,4=Na".',
    )
    parser.add_argument("--topology", type=Path, default=None, help="FrameworkTopology/TopologyCatalog JSON override.")
    parser.add_argument("--topology-cache", type=Path, default=None)
    parser.add_argument("--no-topology-cache", action="store_true")
    parser.add_argument("--framework-formation-cutoff", type=float, default=None)
    parser.add_argument("--framework-breaking-cutoff", type=float, default=None)
    parser.add_argument("--title", default=None, help="Figure title override.")
    parser.add_argument("--projection", choices=("orthographic", "perspective"), default=None)
    parser.add_argument("--camera", default=None, help="Camera preset ([100], [110], [111], isometric) or TOML camera record.")
    parser.add_argument("--periodic-images", default=None, help="Scene-wide display replication, e.g. 2x2x1.")
    parser.add_argument("--cell-mode", choices=("reference", "none"), default=None)
    parser.add_argument("--visible-layer", action="append", default=[], help="Initial visible-layer override; repeat by layer name.")
    parser.add_argument("--show-axes", action="store_true", default=None)
    parser.add_argument("--background", choices=("light", "dark", "transparent"), default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--max-memory", default=None, help="Package-owned memory ceiling, e.g. 12GiB.")
    parser.add_argument("--max-threads", type=int, default=None)
    parser.add_argument("--wall-time-target", "--max-wall-time", dest="wall_time_target", type=float, default=None, help="Advisory scene wall-time target; --max-wall-time is a compatibility alias.")
    parser.add_argument("--output", type=Path, default=None, help="Self-contained Plotly HTML output.")
    parser.add_argument("--manifest", type=Path, default=None, help="Canonical scene-manifest JSON output.")
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Resolve source/layers and write/print the canonical manifest without scientific scene preparation.",
    )
    parser.add_argument("--print-manifest", action="store_true", help="Print canonical manifest JSON to stdout.")
    parser.add_argument("--max-browser-faces", type=int, default=None, help="Override final browser density-face budget.")
    parser.add_argument(
        "--browser-profile",
        choices=("compact", "balanced", "quality"),
        default=None,
        help="Interactive density mesh profile.",
    )
    parser.add_argument("--force", action="store_true", help="Allow overwriting output/manifest files.")
    parser.add_argument("--quiet", action="store_true", help="Suppress stage progress messages.")
    parser.add_argument("--version", action="version", version=f"mdstats-3d {__version__}")
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _parser().parse_args(argv)


def _progress(enabled: bool, stage: str, message: str) -> None:
    if enabled:
        print(f"[GFX3D {stage}] {message}", file=sys.stderr, flush=True)


def _resolve_config_relative(value: Any, config_dir: Path | None) -> Any:
    if value is None or config_dir is None:
        return value
    path = Path(value).expanduser()
    return path if path.is_absolute() else (config_dir / path).resolve()


def _input_overrides(args: argparse.Namespace) -> dict[str, Any]:
    result = {
        "format": args.format,
        "stride": args.stride,
        "timestep_fs": args.timestep_fs,
        "lammps_log": args.lammps_log,
        "lammps_units": args.lammps_units,
        "lammps_timestep": args.lammps_timestep,
        "lammps_type_map": args.lammps_type_map,
        "topology": args.topology,
        "topology_cache": args.topology_cache,
        "framework_formation_cutoff": args.framework_formation_cutoff,
        "framework_breaking_cutoff": args.framework_breaking_cutoff,
    }
    if args.no_topology_cache:
        result["no_topology_cache"] = True
    return result


def _config_output_path(value: Any, config_dir: Path | None) -> Path | None:
    if value is None:
        return None
    return Path(_resolve_config_relative(value, config_dir))


def _default_manifest_path(output: Path) -> Path:
    return output.with_name(output.stem + ".scene.json")


def _ensure_writable(path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise Graphics3DValidationError(
            f"Refusing to overwrite existing {path}. Use --force to replace it."
        )
    path.parent.mkdir(parents=True, exist_ok=True)


def _manifest_for_source(
    request,
    *,
    trajectory_path: Path,
    source_sha256: str,
    source_format: str,
    present_species: Sequence[str],
    trajectory,
    preset: str | None,
    dependency_source: Any = None,
) -> GraphicsSceneManifest:
    mapping = {
        str(index): int(z)
        for index, z in enumerate(trajectory.atomic_numbers)
    }
    return build_graphics_scene_manifest(
        request,
        context=GraphicsSceneContext(source=dependency_source, source_identity=source_sha256),
        source_descriptors=(
            {
                "path": str(trajectory_path.resolve()),
                "sha256": source_sha256,
                "size_bytes": trajectory_path.stat().st_size,
            },
        ),
        resolved_input_format=source_format,
        atom_species_mapping={
            "present_species": tuple(present_species),
            "atomic_number_by_atom_index": mapping,
        },
        frame_selection={
            "n_frames": int(trajectory.n_frames),
            "n_atoms": int(trajectory.n_atoms),
            "frame_ids": tuple(int(v) for v in trajectory.frame_ids[: min(32, trajectory.n_frames)]),
            "frame_id_preview_truncated": bool(trajectory.n_frames > 32),
        },
        coordinate_policy={"registration": request.scene_options.get("registration", "framework_registered")},
        display_cell_policy={"display_cell": request.scene_options.get("display_cell", "reference")},
        expanded_presets=() if preset is None else (preset,),
    )


def _write_manifest(manifest: GraphicsSceneManifest, path: Path, *, force: bool) -> None:
    _ensure_writable(path, force=force)
    path.write_text(manifest.to_json(indent=2) + "\n")


def _render_output(scene, request, *, browser_profile: str, max_browser_faces: int | None = None):
    from mdstats.plotting import BrowserMeshProfile
    base_profile = BrowserMeshProfile.coerce(browser_profile)
    if max_browser_faces is None:
        mesh_profile = base_profile
    else:
        faces = int(max_browser_faces)
        base_budget = base_profile.budget
        ratio_vertices = base_budget.max_final_density_vertices / base_budget.max_final_density_faces
        ratio_html = base_budget.max_final_html_bytes / base_budget.max_final_density_faces
        custom_budget = replace(
            base_budget,
            max_final_density_faces=faces,
            max_final_density_vertices=max(
                int(base_budget.max_final_density_vertices),
                int(math.ceil(faces * ratio_vertices)),
            ),
            max_final_html_bytes=max(
                int(base_budget.max_final_html_bytes),
                int(math.ceil(faces * ratio_html)),
            ),
            metadata={
                **base_budget.metadata.to_json_dict(),
                "face_override": faces,
                "base_profile": base_profile.name,
            },
        )
        mesh_profile = BrowserMeshProfile.custom(custom_budget)
    result = render_graphics3d_plotly(scene, mesh_profile=mesh_profile)
    title = request.scene_options.get("title")
    if title:
        result.artifact.update_layout(title=str(title))
    result.artifact.update_layout(
        legend={"itemsizing": "constant", "groupclick": "togglegroup"},
        margin={"l": 0, "r": 0, "t": 55, "b": 0},
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    enabled_progress = not args.quiet
    try:
        config_payload: dict[str, Any] = {}
        config_dir: Path | None = None
        if args.config is not None:
            config_payload = load_graphics3d_toml(args.config)
            config_dir = Path(config_payload["_config_path"]).parent
        # Resolve TOML path-valued input/output fields relative to the TOML file.
        input_cfg = dict(config_payload.get("input", {}))
        for key in ("lammps_log", "topology", "topology_cache"):
            if key in input_cfg:
                input_cfg[key] = _resolve_config_relative(input_cfg[key], config_dir)
        config_payload["input"] = input_cfg
        output_cfg = dict(config_payload.get("output", {}))
        for key in ("path", "manifest"):
            if key in output_cfg:
                output_cfg[key] = _resolve_config_relative(output_cfg[key], config_dir)
        config_payload["output"] = output_cfg

        _progress(enabled_progress, "INPUT", f"reading {args.trajectory}")
        configured_preset = dict(config_payload.get("scene", {})).get("preset")
        active_preset = args.preset or configured_preset
        # Presets are source-aware, so read the trajectory before final compilation.
        preliminary_input = dict(config_payload.get("input", {}))
        preliminary_input.update({k: v for k, v in _input_overrides(args).items() if v is not None})
        preliminary_input.setdefault("format", "auto")
        preliminary_input.setdefault("stride", 1)
        started = time.perf_counter()
        trajectory, source_format = read_input_trajectory(args.trajectory, preliminary_input)
        present_species = detect_present_species(trajectory)
        _progress(
            enabled_progress,
            "INPUT",
            f"loaded {trajectory.n_frames} frames x {trajectory.n_atoms} atoms as {source_format} "
            f"in {time.perf_counter() - started:.2f}s; species={present_species}",
        )

        configured_title = dict(config_payload.get("scene", {})).get("title")
        automatic_title = None
        if active_preset == LTA_MIXED_ALKALI_PRESET and args.title is None and configured_title is None:
            mobile = tuple(symbol for symbol in ("Li", "Na", "K") if symbol in set(present_species))
            mobile_text = " + ".join(mobile) if mobile else "no alkali cations"
            automatic_title = (
                "LTA: detected-species densities, trajectories, atomic mean net, and mean framework "
                f"({mobile_text}; {trajectory.n_frames} frames)"
            )
        cli_scene = {
            "title": args.title or automatic_title,
            "projection": args.projection,
            "camera": args.camera,
            "periodic_images": args.periodic_images,
            "cell_mode": args.cell_mode,
            "visible_layers": tuple(args.visible_layer) if args.visible_layer else None,
            "show_axes": args.show_axes,
            "background": args.background,
            "width": args.width,
            "height": args.height,
        }
        cli_resources = {
            "max_memory": args.max_memory,
            "max_threads": args.max_threads,
            "wall_time_target": args.wall_time_target,
        }
        cli_output = {
            "path": None if args.output is None else str(args.output),
            "manifest": None if args.manifest is None else str(args.manifest),
            "browser_profile": args.browser_profile,
        "max_browser_faces": args.max_browser_faces,
        }
        compiled = compile_graphics3d_config(
            config_payload,
            preset=args.preset,
            cli_layers=args.layer,
            present_species=present_species,
            cli_scene=cli_scene,
            cli_resources=cli_resources,
            cli_output=cli_output,
            cli_input=_input_overrides(args),
        )
        request = compiled.request
        input_options = dict(compiled.input_options)
        input_options.setdefault("format", source_format)
        input_options.setdefault("stride", int(preliminary_input.get("stride", 1)))

        output_value = request.output.get("path")
        output_path = Path(output_value) if output_value else DEFAULT_OUTPUT
        manifest_value = request.output.get("manifest")
        manifest_path = Path(manifest_value) if manifest_value else _default_manifest_path(output_path)
        browser_profile = str(request.output.get("browser_profile") or "balanced")
        max_browser_faces = request.output.get("max_browser_faces")

        source_sha = _sha256(args.trajectory)
        science_progress = TextProgressPort(
            label="GFX3D PREPARE",
            enabled=enabled_progress,
            show_source=False,
        )
        scientific_source = LTAGraphics3DDependencySource(
            trajectory=trajectory,
            request=request,
            input_options=input_options,
            output_path=output_path,
            source_identity=source_sha,
            progress=science_progress,
        )
        manifest = _manifest_for_source(
            request,
            trajectory_path=args.trajectory,
            source_sha256=source_sha,
            source_format=source_format,
            present_species=present_species,
            trajectory=trajectory,
            preset=compiled.preset,
            dependency_source=scientific_source,
        )
        if args.print_manifest:
            print(manifest.to_json(indent=2))
        if args.manifest_only:
            _write_manifest(manifest, manifest_path, force=args.force)
            _progress(enabled_progress, "MANIFEST", f"wrote {manifest_path}")
            if not args.print_manifest:
                print(manifest_path)
            return 0

        _ensure_writable(output_path, force=args.force)
        _ensure_writable(manifest_path, force=args.force)
        _progress(enabled_progress, "PREPARE", f"preparing {len(request.enabled_layers)} enabled layers")
        context = GraphicsSceneContext(
            source=scientific_source,
            source_identity=source_sha,
            resources=dict(request.resources),
            metadata={
                "gfx3d_cli_schema": GFX3D_CLI_SCHEMA,
                "gfx3d_dependency_gate": "GFX3D-4",
            },
        )
        prepared = prepare_graphics3d_scene(request, context=context)
        prepared = replace(prepared, manifest=manifest)
        _progress(enabled_progress, "RENDER", f"rendering {len(prepared.layers)} independent layers")
        rendered = _render_output(
            prepared, request, browser_profile=browser_profile,
            max_browser_faces=None if max_browser_faces is None else int(max_browser_faces),
        )
        rendered.artifact.write_html(output_path, include_plotlyjs=True)
        _write_manifest(manifest, manifest_path, force=True)
        _progress(
            enabled_progress,
            "DONE",
            f"wrote {output_path} ({output_path.stat().st_size / 1024**2:.1f} MiB) and {manifest_path}",
        )
        print(output_path)
        return 0
    except (Graphics3DError, FrameCollectionError, GraphVisualizationError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"mdstats-3d: {_exception_chain_message(error)}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
