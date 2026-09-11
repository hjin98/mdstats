# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted architecture/specification and the implementation that conforms to them.

## Current MLFF implementation state

Two related MLFF repair tracks are active on `fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission`:

- `MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md` and its current review-reopen lineage govern TRAIN2 zero-safe admission, live aggregate VRAM safety, TRAIN-wave failure/cleanup behavior, and the remaining P5 evidence/authority closeout.
- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_WORKPLAN.md` governs the single-source replay TRUE_DFT default, restoration of prepare-owned replay preparation/currentness, and the pseudo-label provider/executor CUDA lifetime that contaminated the pre-TRAIN2 baseline.

The replay repair is upstream of the scheduler observation but does not replace or weaken the P5 resource architecture. A genuine unsafe device baseline must still be rejected by TRAIN2 admission after the replay ownership defect is removed.

Completed and superseded MLFF workplans remain under `workplans/archive/` as non-normative engineering history. Historical replay architecture remains relevant where a current workplan explicitly cites it as evidence of an already-accepted ownership contract; history itself is not a second current authority.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification follows the acceptance requirements of the active workplan that owns the specific resource claim. In particular, the current replay CUDA-lifetime repair requires real target-host evidence because provider/allocator retirement is itself under test.
