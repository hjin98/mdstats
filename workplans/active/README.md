# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted architecture/specification and the implementation that conforms to them.

## Current MLFF implementation state

One MLFF implementation lineage is active on `fix/mlff-p5-cv-no-admissible-outcome-repair`:

- `MLFF_P5_CV_NO_ADMISSIBLE_CHECKPOINT_OUTCOME_REPAIR_WORKPLAN.md` — parent workplan (P5 CV fold with no admissible checkpoint as a valid rejected verdict);
- `MLFF_P5_CV_NO_ADMISSIBLE_CHECKPOINT_OUTCOME_REPAIR_IMPLEMENTATION_REVIEW_REOPEN.md` — independent review, NO-PASS / REOPENED for blockers R1-R3;
- `MLFF_P5_CV_NO_ADMISSIBLE_CHECKPOINT_OUTCOME_REPAIR_IMPLEMENTATION_EVIDENCE.md` — implementation evidence for the reopen, awaiting independent re-review.

The lineage moves to `workplans/archive/` when an independent review closes it.

The historical `MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_*` lineage has been moved to `workplans/archive/` as superseded engineering history. Its latest fifth review remained `NO-PASS / REOPENED` for terminal R5-B target-host evidence plus an independent D3 authority gate; archiving it does not retroactively relabel that historical review as PASS. Later accepted TRAIN2/replay architecture and the closed memory-pressure backoff cycle supersede its role as an active coordination contract.

The replay TRUE_DFT default, pseudolabel prepare stage ownership, and CUDA lifetime repair lineage is complete and accepted under Protocol 6.2 and remains archived as non-normative engineering history.

Completed, superseded, and retired MLFF workplans belong under `workplans/archive/`. Current product behavior is governed by accepted architecture/specification and conforming implementation, not by historical workplan presence.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains owned by the applicable current release/qualification contract; historical workplans do not create a second active qualification authority.
