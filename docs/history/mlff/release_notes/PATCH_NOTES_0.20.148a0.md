# mdstats 0.20.148a0 patch notes

## GFX3D-3 - universal CLI and declarative configuration

This revision promotes the former mixed-alkali LTA visualization example into the universal configurable GFX3D command surface while keeping scientific preparation owned by the already-qualified framework/connectivity/density subsystems.

### Added

- packaged `mdstats-3d` console command backed by `mdstats.graphics3d.cli.main`;
- source-tree `tools/mdstats-3d.py` launcher;
- strict TOML configuration compilation into one canonical `GraphicsScene3DRequest`;
- repeated `--layer TYPE[:SELECTOR][@NAME]` shorthand for framework, connectivity, trajectory, and density layers;
- deterministic configuration precedence: defaults < preset < TOML < explicit CLI;
- replacement semantics for layer lists so explicit CLI layers never silently merge with configured/preset layers;
- source-aware `lta-mixed-alkali-density` compatibility preset;
- canonical scene-manifest output and `--manifest-only`/`--print-manifest` modes;
- protected HTML/manifest outputs with explicit `--force` overwrite authority;
- VASP/LAMMPS trajectory input handling migrated from the prototype, including LAMMPS units/timestep/type-map and topology overrides;
- concise fail-closed handling for source, selection, plotting-complexity, and output errors;
- short 3-D graphics user guide and complete normative CLI specification;
- reusable example configuration at `examples/gfx3d_na_lta.toml`.

### Compatibility

- `examples/plot_lta_mixed_alkali_density.py` is now a thin compatibility launcher over the universal CLI rather than an independent plotting implementation;
- the old example automatically injects the `lta-mixed-alkali-density` preset when no config/preset/layer is supplied;
- its historical default HTML filename is retained;
- historical trajectory-format inference, LAMMPS type-map parsing, and namespace-based input reader helpers remain importable;
- `--max-wall-time` remains an alias for `--wall-time-target`, and `--max-browser-faces` is retained;
- GFX3D-3 still prepares current scientific products through one `FrameworkDynamicsScene` compatibility provider; GFX3D-4 will split raw preparation into generic shared dependencies.

### Focused qualification

Focused tests cover:

- strict TOML parsing and unknown-key rejection;
- shorthand species/pair selection;
- source-aware preset expansion;
- preset/TOML/CLI precedence;
- manifest-only source resolution;
- overwrite refusal and explicit force;
- all GFX3D-1/2 contract and layer regressions;
- current framework-dynamics/Plotly behavior;
- historical LTA example input-helper compatibility.

Result: **83 passed, 0 failed, 0 skipped**.

The observed warnings are the existing equal-aspect/orientation diagnostics from the qualified legacy Plotly backend.

### Real Na-LTA CLI smoke

The supplied authenticated 300 K Na-LTA LAMMPS dump was read with stride 500, yielding 21 frames x 168 atoms. The promoted CLI compiled exactly:

```text
framework
trajectory:Na
density:Na
```

and wrote a canonical scene manifest. Under a bounded non-adaptive density smoke configuration (`grid_interval = 0.35 A`, compact browser profile), the same command completed full preparation/rendering and wrote a self-contained **6.5 MiB** HTML artifact.

## Next gate

GFX3D-4 - shared dependency planning and cache authority.
