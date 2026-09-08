# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

The current MLFF implementation authority is:

- `workplans/active/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

This repair round was reopened by independent Software Design review after the prior multi-size closure pass. The accepted scientific architecture remains intact; the open blockers are integration closure defects:

1. manual `select-target-size N --horizon-cv HC --horizon H` currently depends on a full prepared-generation/P3-ready loader and can perform unnecessary corpus-scale prepared-data hydration/index construction despite being a zero-screen-work operator decision;
2. when prior automatic-diagnostic evidence exists, a manual selection can re-enter strict P3 diagnostic validation solely to refresh a non-authoritative derived view;
3. the P5A6 baseline-produce/current-reopen compatibility driver still uses retired scalar current-state access on the current reopen side;
4. structural scalar-access guards do not cover all current consumers such as qualification tooling;
5. current architecture/specification/user/runbook documentation still contains scalar target-selection claims and retired `--select-horizon*` CLI spellings.

The repair policy is dependency reduction and current-owner rewiring, not additive wrappers, caches, duplicate state, or compatibility machinery.

Previous completed workplans remain archived as historical evidence and are not current implementation authority.

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains separate and deferred to the established final-release/user-machine qualification stage.
