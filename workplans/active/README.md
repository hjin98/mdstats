# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There are currently no active MLFF implementation workplans in this directory.

The most recently closed target-size integration plan is:

- `workplans/archive/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

Independent Software Design review round 6 accepted candidate `03ff58f9e839edf345e52b8a4aeef612dbd1b092` / executable `add7fcfe647b2d7f91e0fe94e8fc9c64a710fa75` with **PASS**. The final repair restored the P2 nonnegative optimizer-seed invariant, completed the V1-wire/current-V3 binding isolation oracle, and closed the complete P2/P5/P7 affected regression surface.

The exact accepted P5A6 historical workspace remains supported through native parent -> child compatibility semantics without preload migration or descendant-to-ancestor reconstruction.

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains separate and deferred to the established final-release/user-machine qualification stage; it is not an open blocker on the closed implementation workplan.
