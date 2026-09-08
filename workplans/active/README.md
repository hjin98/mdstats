# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

The current MLFF implementation authority is:

- `workplans/active/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

Independent Software Design review round 5 of candidate `69e5b54f0e71f73853b106d25f322829a7ee73dc` / executable `5ae3fbc8acb166881e5cb880a6bb3c88baad21b0` is **NO-PASS**, narrowly.

Round 5 accepts the major compatibility correction: the synthetic `_Legacy*` reconstruction machinery is removed, exact P5A6 selected membership is re-established from authenticated P1/P2 authority before P5 descendants are opened, descendant access is poisoned during selection resolution, and a corrupted final-plan M3 lineage is rejected against an independent P2 oracle. Previously accepted current multi-size/runtime and Part-VI documentation behavior remains accepted.

Three blockers remain:

1. `ResolvedTargetSizePolicy` accidentally stopped rejecting negative optimizer seeds. This violates the frozen P2 requirement for one ordered unique **nonnegative** seed set and disagrees with downstream target-size execution validators. Restore the existing nonnegative check; do not add compatibility machinery.
2. The recorded Round-5 regression is not the complete affected surface. It omits direct P5 R6-R9, assembled/publication consumers previously named by review and also omits the P2 statistical-authority/direct execution consumers of the newly modified `target_size_experiment.py`.
3. The historical-binding architecture guard remains too lexical. Production source appears correct, but acceptance must prove V1 head/reducer fields stay V1-wire-only and cannot feed current-V3 `target_size_binding()` ancestry. Strengthen the existing test; do not add a new scanner/framework.

Repair policy is reduction-first: preserve the accepted P5A6 parent->child reconstruction, restore the one lost validation predicate, strengthen existing oracles, reconcile the stale V1 state comment, and run the complete affected regression. No new P2 class, compatibility registry/database/sidecar, migration, descendant-to-ancestor bridge, or general scanner.

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains separate and deferred to the established final-release/user-machine qualification stage.
