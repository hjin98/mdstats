# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There is currently one active MLFF implementation workplan:

- `workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`

Its current binding implementation-review amendment is:

- `workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_REVIEW_REOPEN.md`

Independent Software Design review of implementation commit `cbfd43cabfbd5e26095a564b6bb4a9c9f3787638` with generated-document head `8c0e2426ce6f9248bf6b958d48570c140bcef147` returned **NO-PASS / REOPENED**. Most original downstream path/identity/multi-size/P7/documentation repairs are accepted and must be preserved. The remaining code blocker is the over-broad P5 unaccepted-materialization reclamation path, which currently deletes corrupt state instead of distinguishing the supported internally valid pre-fix locator-only representation from corruption/foreign state. The review amendment also closes the remaining path-form/structural acceptance gaps and requires final affected regression/integration evidence.

The parent plan plus the review amendment is the snapshot-complete current handoff for downstream MLFF integration closure from post-selection cross-validation through final production/publication, restart/currentness, and qualification entry. Implementation continues on `fix/mlff-downstream-integration-closure`.

The narrow single-source replay-lineage adapter repair is implemented and retired to:

- `workplans/archive/MLFF_P5_SINGLE_SOURCE_REPLAY_LINEAGE_ADAPTER_REPAIR_WORKPLAN.md`

Its source/split adapter fix remains accepted baseline behavior and is incorporated as a preservation requirement in the broader active plan.

The most recently closed target-size integration plan before these repairs is:

- `workplans/archive/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains separate from the bounded implementation/regression work coordinated here.
