# CAMPAIGN-PERF-QUAL1 CPU closure evidence

Release: mdstats 0.20.235a0  
Architecture revision: 102  
Active qualification foundation: MACE-MPA-0 medium (`75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`)  
MACE-MH-1 compatibility: retained by the same execution/scientific contracts.

## Scope

This gate re-profiles the accumulated CPU optimization program. It is measurement/integration authority only: it does not change scientific algorithms, runtime model inference, or GPU numerical authority. Timing is execution evidence. Exact persisted/scientific digests remain the authority.

The target-data chain uses one deterministic 8,192-candidate / six-family fixture and executes FEAS1 -> exact neighborhoods -> MVIDX1 -> MVSEL1 -> REPAIR1 -> MVQUAL1 as an actual chain. The control is an untouched 0.20.225a0 PERFBASE1-era tree. Replay, EVAL2/bootstrap, and Foundation Audit are rechecked on their production-scale or frozen CPU fixtures.

## Integrated target-data chain

| Realization | Wall (s) | Peak RSS (MiB) | FEAS+neighbor | MVIDX | MVSEL | REPAIR | MVQUAL |
|---|---:|---:|---:|---:|---:|---:|---:|
| untouched 0.20.225a0, 4 requested workers | 27.255 | 305.9 | 0.788 | 2.204 | 11.220 | 10.981 | 2.062 |
| current optimized realization, 4 lanes median | 11.948 | 343.5 | 1.033 | 0.089 | 4.873 | 5.420 | 0.533 |

End-to-end target-data speedup: **2.28x**. Scientific reference/role/FEAS/MVIDX/MVSEL/REPAIR/MVQUAL digests are exact between control and current realizations. The current neighborhood cache adds its authenticated execution digest without changing FEAS/MVIDX authority.

Current worker scaling is 12.914 s at one lane, 12.074 s at two lanes, and 11.948 s median at four lanes. Scaling now saturates because the remaining wall time is dominated by sequential-authority sparse state updates rather than starved parallel kernels.

## Shifted hotspot

The integrated profile changes the optimization conclusion. Current four-lane stage fractions are approximately:

- REPAIR1: 45.4%
- MVSEL1: 40.8%
- FEAS1 + neighborhood cache: 8.6%
- MVQUAL1: 4.5%
- MVIDX1: 0.7%

MVSEL profiling attributes about 5.197 s cumulative to 4,096 `_select_and_update` calls, including about 4.565 s in exact paired sparse decrements; `_choose_candidate` is only about 0.900 s. The rank decision itself is therefore no longer the dominant selector cost.

More importantly, REPAIR profiling shows **4,098 additional `_select_and_update` calls** before/around repair, about 5.336 s cumulative, because REPAIR reconstructs essentially the complete selector sparse state from the ordered selection. This is duplicated reconstructible execution work. Proposal scoring itself is much smaller (`_shell_removal_scan` about 0.977 s cumulative and `_best_repair_proposal` about 0.729 s). Per-iteration executor shutdown also contributes about 0.699 s cumulative.

Therefore CAMPAIGN-PERF-QUAL1 does **not** close the CPU optimization program. It opens one exact-equivalence follow-up, `MVSTATE-REUSE1`, to authenticate and hand terminal selector sparse state into REPAIR and to keep reusable repair proposal execution resources alive where appropriate. The sequential selector rank decision, repair objective/tie authority, and full repair trace remain unchanged.

## Replay restart

The supplied 12,000-frame replay corpus retains source-index digest `ce6c678ad556cff63be8ee75754d87cba2b3d08e80f544c5983fe4498dc0c5e1`. A fresh index build takes about 0.411 s, authenticated restart hit about 0.070 s, and monitor-only exact materialization about 2.758 s. Monitor logical digest and ExtXYZ bytes remain exact.

## EVAL2 and Foundation Audit

The current repeated EVAL2 reduction re-runs at about 0.471 s median with exact metric digest `d9dd9db2c2d47e2d6f034e0b58f094c04c516d5a0dc4f0089d3f15762d434658`. The 2,000-replicate paired bootstrap is about 0.0153 s with exact bootstrap digest `9664354fd2d871e67113ff5b9ef28118c9414a59f29a5fd4114acb729590397e`. Foundation Audit is about 0.0540 s median and keeps model-provider call counts exactly [44, 44].

## Memory and restart acceptance

The integrated target chain peaks near 343.5 MiB versus 305.9 MiB in the PERFBASE-era control. The increase reflects retained authenticated sparse execution state and remains far below the qualification cgroup ceiling; no scheduler backpressure or memory-ceiling violation was observed. NEIGHBOR1/MVIDX zero-repeat-geometry and REPLAY-PERF1 authenticated restart contracts remain qualified.

## Decision

**CAMPAIGN-PERF-QUAL1: PASS, FOLLOW-UP REQUIRED.**

The cumulative optimization program has produced a large integrated speedup and preserves exact authority, but the integrated profile exposes a new dominant duplicated state-reconstruction cost. The next gate is **MVSTATE-REUSE1**. Final CPU optimization closure and FINAL-GPU1/PERF-CERT1 remain deferred until that follow-up is qualified.
