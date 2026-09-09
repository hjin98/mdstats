# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

There are currently no active MLFF downstream-integration workplans.

The most recently completed downstream integration closure was reviewed and closed under **Scientific Software Development Protocol 6.0.0** on 2026-09-09. Its exact executable candidate was:

- `13859556cd4d472837a9e171c2be32e59d5e6d82`

Archived coordination/review artifacts:

- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md`
- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_REVIEW_REOPEN.md`
- `workplans/archive/MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_FINAL_REVIEW.md`

The final independent Protocol 6 review is **PASS / CLOSED**. No executable change was required after the accepted candidate; closure followed successful final affected functional evidence reported for that unchanged executable tree.

Non-blocking residuals are recorded in the final review: three pre-existing stale campaign-warning CLI tests, one broad high-fanout storage diagnostic timeout despite passing exact affected storage cases and storage core, and deferred target-machine MLIAP/GPU/CuEq/LAMMPS qualification.

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains deferred until the final release qualification package.

The earlier single-source replay-lineage adapter repair remains archived at:

- `workplans/archive/MLFF_P5_SINGLE_SOURCE_REPLAY_LINEAGE_ADAPTER_REPAIR_WORKPLAN.md`

The most recently closed target-size integration plan before these repairs remains:

- `workplans/archive/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`
