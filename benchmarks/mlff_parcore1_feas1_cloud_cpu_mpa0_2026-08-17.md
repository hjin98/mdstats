# PARCORE1 FEAS1 cloud CPU qualification

**Release:** mdstats 0.20.226a0  
**Architecture revision:** 93  
**Active foundation:** MACE-MPA-0 medium (scheduler contract also supports MACE-MH-1)  
**Scientific authority change:** none

PARCORE1 replaces FEAS1's private executor coordinator with the reusable `DeterministicWorkQueue`. The benchmark uses the exact deterministic FEAS1 authority frozen by PERFBASE1: six profiles, 49,152 witnesses, and 3,194,880 neighborhood edges. Every paired trial preserves scientific digest `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613`.

## Final paired same-host results

| Schedule | Workers | PARCORE1 median (s) | Untouched 0.20.225a0 median (s) | Ratio | PARCORE1 occupancy | Control occupancy |
|---|---:|---:|---:|---:|---:|---:|
| serial | 1 | 1.4025 | 1.7908 | 0.783 | 1.061 | 1.025 |
| dual | 2 | 1.0481 | 1.1155 | 0.940 | 0.814 | 0.815 |
| intermediate | 2 | 0.9988 | 1.1198 | 0.892 | 0.803 | 0.813 |
| auto | 3 | 0.8291 | 0.9386 | 0.883 | 0.661 | 0.641 |

The automatic three-worker PARCORE1 median is 0.8291 s versus 0.9386 s for the paired untouched control (ratio 0.883). The frozen PERFBASE1 three-worker median was 0.8542 s; PARCORE1's ratio to that frozen value is 0.971. All three queue lanes were observed busy.

The timings are deliberately not scientific authority. The gate invariant is exact output equality; timing only checks that the common scheduler does not introduce a material full-budget regression.

## Scheduler contracts exercised

- bounded ready, submitted/in-flight, and completed work;
- exact O(1) queue-memory accounting and RAM admission/backpressure;
- deterministic ordered reduction despite out-of-order worker completion;
- deterministic task identity on worker failure;
- stage-scoped native-thread quarantine for campaign execution;
- locality metadata reserved without enabling NUMA affinity.

## Acceptance

**PASS.** Exact digest equality holds at every schedule, the automatic schedule reaches all three allocated lanes, and paired full-budget throughput is non-regressive. The next gate is `NEIGHBOR1`.
