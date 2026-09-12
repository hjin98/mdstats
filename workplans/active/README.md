# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted architecture/specification and the implementation that conforms to them.

## Current MLFF implementation state

One MLFF repair track remains active on `fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission`:

- `MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md` and its current review-reopen lineage govern TRAIN2 zero-safe admission, live aggregate VRAM safety, TRAIN-wave failure/cleanup behavior, and the remaining P5 evidence/authority closeout.

The replay TRUE_DFT default, pseudolabel prepare stage ownership, and CUDA lifetime repair (`MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_WORKPLAN.md` and its review-reopen lineage 1-6) is complete and accepted under Protocol 6.2 with all 320 functional tests and target-host E1/E2 qualification passing for candidate `eb3221397457b5cf374298c4b4979e1e1d0c0c96`. It has been moved to `workplans/archive/` as non-normative engineering history.

Completed and superseded MLFF workplans remain under `workplans/archive/` as non-normative engineering history. Historical replay architecture may be consulted as semantic-evolution evidence, but history is not a second current authority; current Architecture Manual/specification plus the active cycle contract govern implementation.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification follows the acceptance requirements of the active workplan that owns the specific resource claim. In particular, the current replay CUDA-lifetime repair required real target-host evidence because provider/allocator retirement was itself under test.
