# mdstats 0.20.207a0 - SIZE-FIDELITY2

This release implements the eighth gate of the optimized multi-view target-data roadmap.

## Added

- `SizeFidelity2Policy`, `SizeFidelity2ExecutionPlan`, checkpoint/monitor evidence, per-q assessments, and qualification reports.
- Exhaustive q=4..8 retrospective survivor calibration using one seed x size trajectory matrix rather than independent training campaigns per q.
- Exact 3/10/30 continuation/identity/exposure validation and 100% eventual-two-finalist recall requirements at epochs 3 and 10.
- Fixed-16,384 material-superiority/nonconvergence rejection.
- 128/256/512/1024 monitor-view calibration derived from one epoch-3 full prediction product, with zero additional model inference.
- Campaign prepare/restart receipt integration for `size_fidelity2_execution_plan`.

## Unchanged

- Revision-64 TARGET-DATA2C v4 and TARGET-DATA2D v2 remain production authorities.
- DATA8 membership, coverage threshold, fixed 16,384 ceiling, e3nn source/DATA6 policy, and CuEq TRAIN2 policy are unchanged.
- Positive SIZE-FIDELITY2 MACE/GPU execution remains deferred to FINAL-GPU1.

Architecture revision advances to 74 and dependency-graph schema to 56. The next gate is `TARGET-DATA2C-MVMIGRATE1`.
