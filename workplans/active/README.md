# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There is currently one active MLFF implementation workplan:

- `workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`

Its current binding implementation-review amendment is:

- `workplans/active/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_REVIEW_REOPEN.md`

Independent Software Design review of implementation commit `cbfd43cabfbd5e26095a564b6bb4a9c9f3787638` with generated-document head `8c0e2426ce6f9248bf6b958d48570c140bcef147` remains **NO-PASS / REOPENED** after a second workplan-closure review. The original foundation configured-path/identity fix, multi-size CV completion, P7 path handling, architecture reconciliation, and single-source source/split lineage repair remain accepted preservation constraints.

The binding amendment now closes the complete remaining defect family rather than only the first observed recovery symptom:

- P5 materialization recovery must authenticate and distinguish valid obsolete locator-only state, current state, corruption/foreign state, and real TRAIN2 restartable progress instead of deleting by absence or treating a nonempty checkpoint directory as proof of resumability;
- replay train and TRUE_DFT monitor filesystem paths must follow the same locator-versus-content rule already accepted for the foundation checkpoint: replay method/lineage identity is path-free, while current authenticated locators reach only the dependency-facing execution boundary;
- absolute/tilde/config-relative foundation execution, structural absence checks, replay relocation/mutation, final-production/restart coverage, and final affected regression/integration/static evidence are required before re-review.

The parent plan plus this amended review file is the snapshot-complete current handoff for downstream MLFF integration closure from post-selection cross-validation through final production/publication, restart/currentness, and qualification entry. Implementation continues on `fix/mlff-downstream-integration-closure`.

The narrow single-source replay-lineage adapter repair is implemented and retired to:

- `workplans/archive/MLFF_P5_SINGLE_SOURCE_REPLAY_LINEAGE_ADAPTER_REPAIR_WORKPLAN.md`

Its source/split adapter fix remains accepted baseline behavior and is incorporated as a preservation requirement in the broader active plan.

The most recently closed target-size integration plan before these repairs is:

- `workplans/archive/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains separate from the bounded implementation/regression work coordinated here.
