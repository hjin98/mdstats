# MLFF TARGET-DATA2C-MVMIGRATE1 Generated-Policy Migration Specification

**Gate:** `TARGET-DATA2C-MVMIGRATE1`  
**Release:** `mdstats 0.20.208a0`  
**Architecture revision:** 75  
**Status:** implementation-complete; activation deferred to FINAL-GPU1 evidence

## Purpose

MVMIGRATE1 is the sole authority allowed to retire revision-64 generated TARGET-DATA2C dynamic rescue and replace the generated target-size path with the exact sparse multi-view selector. It is an atomic migration boundary, not another selector-tuning gate.

## Migrated generation

The candidate generation is TARGET-DATA2C v5 -> TARGET-DATA2D v3 -> TARGET-DATA2E v3. The v5 target-size population is exactly `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`. Membership is the prefix geometry of the frozen REPAIR1 `repaired_master_order`; no random/FPS fallback and no dynamic upper rescue are permitted. Every materialized rung is independently rescored through TARGET-DATA2B and its DATA2A hard obligations. At least four hard-qualified sizes are required before the future 3/10/30 funnel may proceed.

Historical TARGET-DATA2C v4 / TARGET-DATA2D v2 / TARGET-DATA2E v2 remain readable and auditable. Schema/version checks prevent either generation from being interpreted as the other.

## Atomic activation latch

The MVMIGRATE1 plan binds the legacy v4 ladder, REPAIR1, MVQUAL1, SIZE-HALVE2, and SIZE-FIDELITY2 execution-plan digests. It has three states: `blocked_scientific_preconditions`, `awaiting_final_gpu_qualification`, and `authorized_for_atomic_activation`.

Authorization requires all of the following:

1. MVQUAL1 same-N and N95 non-regression pass.
2. At least four independently hard-qualified MV sizes.
3. SIZE-HALVE2 is `ready_for_size_fidelity2`.
4. SIZE-FIDELITY2 is `ready_for_final_gpu_calibration`.
5. The frozen MVQUAL1 legacy-vs-MV learning-control sizes have passed paired TRAIN2/EVAL2 controls under a common training protocol; every MV score must be no worse than the legacy score by more than the frozen practical-equivalence width.
6. SIZE-FIDELITY2 qualification passes and its `gpu_qualification_status` is exactly `passed`.

Missing final GPU evidence yields `awaiting_final_gpu_qualification`, not success. Failed scientific/GPU evidence yields `blocked_scientific_preconditions`. CPU-only tests cannot synthesize activation authority.

## Restart and cost containment

The v5 candidate is content-addressed to TARGET-DATA2B, TARGET-DATA2A, REPAIR1, MVQUAL1, and the MVMIGRATE1 plan digest. A final-GPU update therefore invalidates only the migration latch/candidate boundary. Valid DATA6, TARGET-DATA2A/B, MVIDX1, MVSEL1, REPAIR1, and other expensive upstream evidence are not recomputed.

## Non-goals

MVMIGRATE1 does not change DATA8 membership, the 0.95 hard-coverage threshold, e3nn source/DATA6 policy, CuEq TRAIN2 policy, or any selector science frozen in revision 66. It does not execute the deferred GPU campaign in this release.
