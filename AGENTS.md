# mdstats development instructions

## Environment
Use the Conda environment `mace`.

Prefer:
    conda run -n mace <command>

## Repository boundaries
Only modify files inside this repository unless explicitly authorized.

External simulation and trajectory directories are read-only inputs.

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