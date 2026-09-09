# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There is currently one active MLFF implementation workplan:

- `workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`

It is the snapshot-complete next-round handoff for downstream MLFF integration closure from post-selection cross-validation through final production/publication, restart/currentness, and qualification entry. The current baseline is `0dcb43611409b540b85089912761ffc0394f166c` on `fix/mlff-p5-single-source-replay-lineage-adapter`; implementation proceeds on `fix/mlff-downstream-integration-closure`.

The narrow single-source replay-lineage adapter repair is implemented and retired to:

- `workplans/archive/MLFF_P5_SINGLE_SOURCE_REPLAY_LINEAGE_ADAPTER_REPAIR_WORKPLAN.md`

Its source/split adapter fix remains accepted baseline behavior and is incorporated as a preservation requirement in the broader active plan.

The most recently closed target-size integration plan before these repairs is:

- `workplans/archive/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains separate from the bounded implementation/regression work coordinated here.
