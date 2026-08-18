---
title: "mdstats GFX3D CLI Specification"
subtitle: "Normative command, TOML, preset, manifest, and compatibility contract for mdstats-3d"
author: "mdstats specification"
date: "2026-08-11"
geometry: margin=0.76in
fontsize: 10pt
toc: true
toc-depth: 3
numbersections: true
colorlinks: true
header-includes:
  - |
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{enumitem}
    \usepackage{fvextra}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
    \RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\small}
---

# Status and authority

This specification is the normative user-facing contract for the universal CLI through **GFX3D-5**, implemented in `mdstats 0.20.150a0` and hardened for the existing layer families in `mdstats 0.20.156a0`.

Architecture authority remains:

```text
docs/arch_manuals/mdstats_3d_graphics_architecture.md
```

The command surface is owned by:

```text
mdstats.graphics3d.cli
```

The source-tree launcher is:

```text
python tools/mdstats-3d.py ...
```

An installed package exposes:

```text
mdstats-3d ...
```

The historical `examples/plot_lta_mixed_alkali_density.py` is a compatibility launcher, not a second implementation.

# Core compilation rule

Every input form MUST compile into exactly one canonical `GraphicsScene3DRequest` before scientific scene preparation.

The supported configuration sources are:

1. built-in defaults;
2. one optional preset;
3. one optional TOML file;
4. explicit command-line overrides.

Precedence is:

```text
defaults < preset < TOML < explicit CLI
```

Layer lists use replacement rather than implicit union:

- preset supplies its layer list;
- any TOML `[[layer]]` entries replace the preset layer list;
- any repeated `--layer` values replace both TOML and preset layers.

This rule is deliberate. A user-visible figure must never gain an unrequested layer through an implicit merge.

# Invocation grammar

The canonical syntax is:

```text
mdstats-3d TRAJECTORY [OPTIONS]
```

A scene MUST contain at least one enabled layer after configuration compilation.

Initial built-in layer types are:

```text
framework
connectivity
trajectory
density
```

Multiple instances of one layer type are valid when names are unique.

# Layer shorthand

The command accepts repeated:

```text
--layer TYPE[:SELECTOR][@NAME]
```

Examples:

```text
--layer framework
--layer trajectory:Na
--layer trajectory:Li,Na,K@mobile-cations
--layer connectivity:Na-O
--layer connectivity:Li-O,K-O@alkali-oxygen
--layer density:Na@Na-density
```

Rules:

- `framework` has no shorthand selector in GFX3D-3;
- trajectory and density selectors are species lists;
- connectivity selectors may be a species list or a homogeneous list of species pairs;
- pair syntax is `ELEMENT-ELEMENT`;
- pair and species shorthand cannot be mixed in one connectivity selector;
- `@NAME` supplies the unique layer name;
- when `@NAME` is omitted, a deterministic name is derived from layer type and selector.

Compound selections involving atom indices plus species/pairs belong in TOML.

# TOML schema

A TOML configuration may contain these top-level tables:

```text
[scene]
[input]
[resources]
[output]
[[layer]]
```

Unknown top-level tables or unknown keys in the currently defined tables fail closed.

## Scene table

Current keys are:

```toml
[scene]
preset = "lta-mixed-alkali-density" # optional
title = "Na-LTA 300 K"
registration = "framework_registered"
trajectory_display_mode = "folded"
display_cell = "reference"
connectivity_mode = "occupancy"
occupancy_threshold = 0.95
density_grid_interval = 0.20
density_gaussian_to_grid_ratio = 2.0
density_adaptive_smearing = true
density_max_smearing_to_sample_sd_ratio = 0.50
density_sample_sd_quantile = 0.10
projection = "orthographic"
camera = "[111]"
periodic_images = "2x2x1"
visible_layers = ["framework", "Na density"]
cell_mode = "reference"
show_axes = false
background = "light"
width = 1000
height = 800
```

The view-only keys above are render provenance and do not enter scene/layer scientific identities. `camera` accepts `[100]`, `[010]`, `[001]`, `[110]`, `[101]`, `[011]`, `[111]`, `isometric`, a three-value eye, or an explicit camera table. `periodic_images` accepts `reference`, an `NxMxK` count, a three-integer count array, an explicit array of lattice shifts, or `{counts=[...], origin=[...]}`. Periodic display is applied scene-wide to all renderer-neutral primitives.

The density numerical options above remain source-wide because the qualified density owner performs one jointly planned density scene. Under GFX3D-4, density layers depend on the product-level `atomic_density_product` key rather than on a monolithic scene key; duplicate density layers share that dependency.

## Input table

```toml
[input]
format = "auto"
stride = 1
timestep_fs = 1.0
lammps_log = "log.lammps"
lammps_units = "metal"
lammps_timestep = 0.001
lammps_type_map = "1=Si,2=Al,3=O,4=Na"
topology = "topology.json"
topology_cache = "topology-cache.json"
no_topology_cache = false
framework_formation_cutoff = 2.05
framework_breaking_cutoff = 2.30
```

Path values in TOML are resolved relative to the TOML file. Explicit CLI path overrides are resolved normally by the shell/current working directory.

## Resources table

```toml
[resources]
max_memory = "12GiB"
max_threads = 8
wall_time_target = 1200.0
```

These compile to execution-only resource requests. They do not alter scientific identities.

## Output table

```toml
[output]
path = "scene.html"
manifest = "scene.scene.json"
browser_profile = "balanced"
max_browser_faces = 600000
```

`browser_profile` accepts `compact`, `balanced`, or `quality`.

## Layer tables

```toml
[[layer]]
type = "trajectory"
name = "Na trajectories"
selection = { species = ["Na"] }
render = { line_width = 1.6, opacity = 0.28, show_legend = true }
visible = true
enabled = true
priority = 0

[[layer]]
type = "connectivity"
name = "Na-O connectivity"
selection = { pairs = ["Na-O"] }
render = { edge_width = 1.6, edge_opacity = 0.45 }

[[layer]]
type = "density"
name = "Na density"
selection = { species = ["Na"] }
render = { mass_fractions = [0.50, 0.80, 0.95], inner_opacity = 0.22, outer_opacity = 0.04 }
```

The universal selection vocabulary also reserves atom IDs, atom indices, framework roles, topology IDs, rings, cages, sites, states, and transitions. A registered layer MUST reject selection fields it does not support.

Scientific `analysis` tables are included in the canonical layer contract. GFX3D adapters accept only analysis values that can actually be applied by the owning scientific provider; silently ignored scientific options are forbidden.

# Built-in compatibility preset

GFX3D-3 defines:

```text
lta-mixed-alkali-density
```

The preset is source-aware. After trajectory parsing it expands to:

- framework topology;
- atomic mean connectivity;
- one trajectory layer containing all detected supported species;
- one atomic-density layer for every detected species among Si, Al, O, Li, Na, and K.

It preserves the prior hybrid example defaults for:

- T-O-T aluminosilicate framework mapping;
- framework-registered coordinates;
- folded trajectories;
- reference display cell;
- occupancy connectivity with threshold 0.95;
- density grid interval 0.20 A;
- Gaussian-to-grid ratio 2.0;
- adaptive smearing policy;
- 50/80/95% HDR shells;
- orthographic projection;
- balanced browser mesh profile.

The preset is a compatibility configuration, not an LTA dependency of the universal scene contracts.

# Input formats

The CLI currently accepts time-ordered sources supported by the promoted prototype:

```text
vasp-xml
vasp-xdatcar
vasp-contcar-trajectory
lammps-dump
```

`--format auto` recognizes `vasprun.xml`, `XDATCAR`, `TRAJECTORY`, `.lammpstrj`, `.dump`, `.lammpsdump`, and common `dump.*` names, including recognized compression suffixes.

LAMMPS numeric atom types require an explicit type map when no element column is present:

```text
--lammps-type-map "1=Si,2=Al,3=O,4=Na"
```

If units or physical time cannot be established from the dump/log, the CLI fails closed and requests `--lammps-units`, `--lammps-timestep`, or a suitable log/TIME record.

# Output and overwrite authority

Normal execution writes:

1. one self-contained Plotly HTML file;
2. one canonical scene-manifest JSON file.

Default HTML path:

```text
graphics3d.html
```

Default manifest path for `graphics3d.html`:

```text
graphics3d.scene.json
```

Existing HTML or manifest outputs are never replaced implicitly. Use:

```text
--force
```

for explicit overwrite authority.

The historical example shim retains its old default HTML filename:

```text
lta_density_framework_trajectories.html
```

when no config/output override is supplied.

# Canonical manifest

The manifest is `mdstats.graphics3d.scene-manifest.v1` evidence and records, at minimum:

- mdstats version;
- source path, byte size, and SHA-256;
- resolved input format;
- resolved species/atom mapping;
- frame-count/atom-count evidence;
- ordered normalized layer requests;
- scene, view, resource, and output requests;
- expanded preset names;
- deduplicated dependency plan;
- separate request identity domains inherited from GFX3D contracts.

Manifest serialization MUST be canonical and deterministic for equivalent normalized requests.

# Manifest-only mode

```text
--manifest-only
```

parses/resolves the input source and source-aware preset, compiles the canonical request, and writes the manifest **without** framework topology construction, atomic-connectivity preparation, density preparation, or Plotly rendering.

`--print-manifest` additionally writes canonical manifest JSON to stdout.

Manifest-only mode is intended for configuration review, provenance inspection, automation, and preflight.

# Compatibility behavior

`examples/plot_lta_mixed_alkali_density.py` delegates to `mdstats.graphics3d.cli.main`.

When the caller supplies no `--config`, `--preset`, or `--layer`, the shim injects:

```text
--preset lta-mixed-alkali-density
```

and, absent an explicit output path, preserves:

```text
--output lta_density_framework_trajectories.html
```

Historical trajectory-format inference, LAMMPS type-map parsing, and `read_input_trajectory(argparse.Namespace)` helpers remain importable for compatibility tests and downstream scripts.

Compatibility aliases include:

```text
--max-wall-time  -> --wall-time-target
```

and the historical `--max-browser-faces` capability is retained.

# Current scientific-provider boundary

Through GFX3D-4 the command is universal at both the **scene/CLI composition** and **product dependency** levels for the four current layer families.

The built-in raw-source dependency types are `framework_topology_product`, `atomic_connectivity_product`, `atomic_trajectory_product`, and `atomic_density_product`. Equal scientific dependency keys deduplicate before execution, and concurrent requests for the same key are single-flight. The current aluminosilicate/LTA scientific provider may batch compatible framework-dynamics work once under the existing qualified CPU/RAM scheduler, but layers consume separate scientific products rather than a monolithic scene key.

The current provider still uses framework registration as a scientific prerequisite for framework-registered trajectory, connectivity, and density products. This is legitimate scientific dependency reuse, not a renderer requirement. Future ring/cage/site providers must join the same DAG with their own explicit product keys.

# Error and exit semantics

Successful execution returns exit status `0`.

Configuration, input, scientific-selection, graph-complexity, and output-authority failures return status `2` from the packaged command and print one concise `mdstats-3d:` error to stderr.

Argparse usage errors retain normal argparse behavior.

The CLI does not silently:

- guess unknown chemical species;
- guess LAMMPS units or type mappings;
- merge conflicting layer lists;
- ignore unsupported scientific layer options;
- overwrite existing outputs;
- remove a requested layer to satisfy rendering/resource limits.

# Focused acceptance authority

The GFX3D-3 focused suite covers:

- TOML parsing and strict unknown-key handling;
- shorthand species and pair selection;
- preset/TOML/CLI precedence;
- source-aware preset density expansion;
- manifest-only source resolution;
- overwrite refusal and explicit `--force`;
- GFX3D-1 identities/dependency/manifest contracts;
- GFX3D-2 independent layer composition;
- current framework/Plotly compatibility;
- historical LTA example input-helper compatibility.

The GFX3D-5 implementation record for `0.20.150a0` reports **83 focused tests passed** across GFX3D-1 through GFX3D-5 plus the legacy framework/graph renderers. The real Na-LTA renderer-neutral qualification is recorded separately in the release evidence.

A bounded real source-tree smoke used the authenticated 300 K Na-LTA trajectory with stride 500 (21 frames x 168 atoms), compiled `framework + trajectory:Na + density:Na`, wrote the canonical manifest, and generated a self-contained HTML artifact using a bounded non-adaptive density configuration.

## Hardening authority in 0.20.156a0

Topology cache reuse is authenticated. When `topology_cache` is omitted, the CLI may use its normal output-derived sidecar path; an existing cache is reused only if its `mdstats.graphics3d.topology-cache.v2` authority matches the exact parsed trajectory geometry/frame identity, framework-connectivity definition, and framework mapping. `no_topology_cache = true` disables both reuse and writing. Legacy raw catalog JSON remains accepted as an explicit `topology` input, but it is not silently treated as an authenticated automatic cache.

View validation is fail-closed. Periodic `counts`, `origin`, and explicit lattice shifts require exact integers; floats such as `1.9` are invalid rather than truncated. Camera vectors must be finite; `eye` and `up` must be nonzero. Browser limits are checked against the predicted periodically replicated payload before replicated arrays are allocated.

`cell_mode = "reference"` is scene-owned and applies even when no framework layer is present. Universal trajectory layers honor `enable_hover` using renderer-neutral hover metadata. These are render-only changes and do not alter scientific layer identity.

