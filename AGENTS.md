# mdstats development instructions

## Environment
Use the Conda environment `mace`.

Prefer:
    conda run -n mace <command>

## Repository boundaries
Only modify files inside this repository unless explicitly authorized.

External simulation and trajectory directories are read-only inputs.

## Documentation authority
Permanent documentation describes the accepted current software. Keep artifact responsibilities distinct:

- architecture manuals -> current structure, ownership, data/control flow, algorithms, and accepted extension boundaries;
- specifications -> current normative behavior and contracts;
- `workplans/` -> proposed transitions, developer implementation gates, and temporary execution coordination;
- history/changelog/release notes -> completed chronology;
- audits/qualification evidence -> correctness evidence;
- benchmarks -> performance evidence;
- guides/runbooks -> stable operational usage.

Do not use architecture manuals or specifications as task trackers. Runtime/product gates that define current software behavior remain architecture/specification; developer gates that organize a change belong in a workplan. Move completed workplan chronology to history/evidence as appropriate and archive the workplan when the transition is accepted.

Changed permanent Markdown documentation must follow the repository's established PDF/provenance policy where applicable. `workplans/` is repository-internal coordination material and must not be distributed in source or wheel artifacts.

## Validation
Run targeted tests before broader regression tests.

Do not claim GPU qualification unless explicitly run on supported hardware.

## Git workflow
Do not modify `main` directly for substantial changes.

Use a dedicated branch or worktree per task.

Do not commit generated data, large trajectories, checkpoints, or scratch output.

## Performance work
Profile before optimizing.

Preserve numerical/scientific semantics.

Benchmark before and after under equivalent conditions.
