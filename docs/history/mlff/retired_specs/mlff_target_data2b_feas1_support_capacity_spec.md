---
title: "TARGET-DATA2B-FEAS1 support-fragility and capacity-bound specification"
author: "mdstats project"
date: "2026-08-16"
geometry: margin=0.78in
fontsize: 10pt
---

# TARGET-DATA2B-FEAS1

**Release:** `mdstats 0.20.200a0`  
**Architecture:** revision 67 / dependency-graph schema 49  
**Status:** implemented diagnostic authority; TARGET-DATA2C v4 selection remains unchanged.

FEAS1 consumes the frozen TARGET-DATA2A development-role authority and TARGET-DATA2B coverage reference. It performs no target-frame selection and never reads locked-test evidence.

## Exact support diagnostics

For every required coverage-family witness, FEAS1 evaluates the existing TARGET-DATA2B scaled-RMS/local-radius neighborhood and reduces matching family elements to unique candidate frame identities. It records support after (a) removing only the witness frame and (b) removing the witness's complete TARGET-DATA2A development interval / DATA5 partition unit. The second view is the cross-support fragility diagnostic.

Weighted mass is recorded for zero support, exactly one supporting frame, and cumulative support degree `<=2`, `<=4`, `<=8`, `<=16`, and `<=32`. Required-family positive zero cross-unit support mass yields `cross_support_fragile` but does not modify the current selector.

## Conservative lower bound

For each required family, exact singleton candidate gains are accumulated in FP64. If sorted singleton gains are `g_(i)`, the smallest `k` satisfying `sum(g_(1..k)) >= 0.95` is a valid cardinality lower bound because overlap is ignored. Hard protected-stratum minima, lower/upper extent obligations, and one-frame-per-development-interval reservations provide an independent hard-obligation lower bound. Since development intervals are disjoint, their count is itself an exact lower bound.

`K_min_lower_bound` is the maximum of the required-family coverage and hard-obligation bounds. A bound above `min(16384, N_development)` yields `provably_capacity_infeasible`.

## State and execution contract

Every valid report includes `self_consistent` plus exactly one terminal state: `optimization_required`, `cross_support_fragile`, or `provably_capacity_infeasible`. Domain/index defects fail immediately rather than becoming normal states.

FP64 accumulation is deterministic. cKDTree worker count and query block size are execution-only. No persistent dense all-pairs matrix or selector graph is created; sparse bidirectional graph persistence belongs to TARGET-DATA2C-MVIDX1.

Campaign record: `target_coverage_feasibility`. Restart reuse requires unchanged TARGET-DATA2B reference digest, TARGET-DATA2A role-freeze digest, coverage threshold, and FEAS1 policy digest.
