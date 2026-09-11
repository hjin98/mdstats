# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted architecture/specification and the implementation that conforms to them.

## Current MLFF implementation state

Two related MLFF repair tracks are active on `fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission`:

- `MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md` and its current review-reopen lineage govern TRAIN2 zero-safe admission, live aggregate VRAM safety, TRAIN-wave failure/cleanup behavior, and the remaining P5 evidence/authority closeout.
- `MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_WORKPLAN.md` is the consolidated, final-reviewed replay repair contract. It governs the single-source TRUE_DFT default, doctor/prepare/P5 stage ownership, exact current-alias replacement, replay currentness and storage-safe reconstruction, lifecycle/P5 currentness under an unchanged target binding, concurrent cold-build safety, and pseudo-label provider/executor CUDA lifetime. The temporary second-review amendment/closure documents were folded into this snapshot-complete plan and retired from the active set.

The replay repair is upstream of the scheduler observation but does not replace or weaken the P5 resource architecture. A genuine unsafe device baseline must still be rejected by TRAIN2 admission after the replay ownership defect is removed.

Completed and superseded MLFF workplans remain under `workplans/archive/` as non-normative engineering history. Historical replay architecture may be consulted as semantic-evolution evidence, but history is not a second current authority; current Architecture Manual/specification plus the active cycle contract govern implementation.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification follows the acceptance requirements of the active workplan that owns the specific resource claim. In particular, the current replay CUDA-lifetime repair requires real target-host evidence because provider/allocator retirement is itself under test.
