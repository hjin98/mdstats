---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_D1_R2_REVIEW
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
failed_r1_candidate: 06f1255ed39f41d178daf73985829a2190a2bee8
r1_review_commit: a1e086645708b273382ed3742a8788ce01592b80
immutable_d1_r2_candidate: 2549dee709fb8bb383341ee3aebca7c71973a903
d1_r2_candidate_blob: 8667ee1abdb568a58ac945c87c9e2d7386dcf49b
dependency_trace_blob: dc8038b81f2f168cd258ba0098e9b9edcc1b6c55
highest_review_owner: D1
d2_gate_state: BLOCKED_PENDING_D1_ACCEPTANCE
---

# Independent D1 R2 Review handoff — replay retention and target admissibility

## 1. Binding and independence

Perform a fresh Protocol-6.4 D1 re-review of immutable target:

`2549dee709fb8bb383341ee3aebca7c71973a903`

against accepted current baseline:

`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`.

Canonical repaired D1 blob:

`8667ee1abdb568a58ac945c87c9e2d7386dcf49b`.

The prior failed candidate and review are evidence/challenge material only:

- R1 candidate: `06f1255ed39f41d178daf73985829a2190a2bee8`;
- R1 review: `a1e086645708b273382ed3742a8788ce01592b80`;
- R1 review record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D1_INDEPENDENT_REVIEW_R1.md`.

The bounded dependency trace in the R2 candidate is a non-authoritative review aid:

`workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D1_DEPENDENCY_TRACE_R2.md`.

Do not inherit the author claim that R1 is closed. Reconstruct the accepted baseline/imports and falsify the repaired text independently.

## 2. R1 findings that R2 claims to repair

### R1 — checkpoint universe

Challenge whether `D1.DEF.026` now actually requires the best target-RMSE representative over the entire governed checkpoint universe, rather than merely a purchased/shortlisted fully evaluated subset.

Verify in particular:

- `C_rho` contains every checkpoint position required by accepted checkpoint cadence and durably committed by the realized fixed-budget trajectory;
- every member must enter assessment;
- authentication/evaluation failure is hard evidence/integrity handling rather than permission to omit a quality-relevant checkpoint;
- D2 enumeration mechanics cannot replace `C_rho` by a quality-dependent shortlist.

Raise a blocking finding if a downstream implementation can still lawfully avoid evaluating a committed checkpoint that could have lower target RMSE.

### R2 — exact foundation baseline

Challenge whether exact frozen `Phi` is now an unavoidable parent of foundation-relative replay retention for **both** `TRUE_REFERENCE` and `FOUNDATION_PSEUDO` training-label modes.

Verify that the degradation baseline is the same exact foundation checkpoint/head/model identity whose inherited capability is claimed.

### R3 — warning-only currentness

Challenge whether changing only `delta_warn` is scientifically guaranteed to affect diagnostics only.

It must not by itself change:

- hard-admissible set `H_rho`;
- representative;
- outer-evaluation membership;
- CV pass/fail;
- production authorization;
- publication membership.

Verify that `delta_hard`, role target ceilings and selection policy remain allowed to move their legitimate hard-decision descendants without changing realized training when training-bearing semantics are unchanged.

### R4 — threshold boundary ownership

Verify that D1, not D2, owns:

- force-error dimension;
- warning iff degradation strictly exceeds `delta_warn`;
- catastrophic hard failure iff degradation strictly exceeds `delta_hard`;
- equality at either threshold does not trigger that corresponding strict-exceedance class.

D2 may own canonical unit conversion, finite representation, comparison implementation and numerical boundary oracles, but may not change the scientific inequality.

### R5 — true-reference terminology

Verify source closure against accepted `D1.DEF.021`:

`TRUE_REFERENCE | FOUNDATION_PSEUDO`.

R2 should use true-reference as the D1 role and mention DFT / `true_dft` only as the current project realization. Raise a blocker if the repair creates a third scientific replay role or narrows accepted true-reference meaning to DFT without authority.

### R6 — renderer-safe representation

Verify every new/edited display equation uses the accepted renderer-safe block form and that no representation repair changed the mathematics.

## 3. Direct dependency trace challenge

Independently challenge the direct edges in the R2 trace. In particular verify that:

```text
D1.DEF.022A -> D1.DEF.020, D1.DEF.022, D1.IMP.P5
D1.DEF.026  -> D1.DEF.022A, D1.DEF.023, D1.DEF.025, D1.IMP.P5
D1.AX.010A  -> D1.DEF.022A, D1.DEF.025, D1.DEF.026, D1.DEF.027,
               D1.AX.009, D1.AX.010
```

are direct and sufficient after the repaired wording.

The trace is not authority. If a prerequisite is missing, repair the canonical D1 owner rather than treating the trace as semantic compensation.

## 4. Regression challenge outside R1

Re-review must also check that the repair did **not** drift:

- P1-P4 or target-order semantics;
- P3 target-size or practical-equivalence semantics;
- foundation objective, E0, replay exposure, monitor cardinality or fold construction;
- scratch post-selection policy;
- downstream physical/deployment qualification;
- fixed-budget training;
- current-CV authorization for current final publication;
- target-only foundation-P5 checkpoint and `single_best_final_seed` ordering;
- the configurable/default status of replay `50/100 meV/angstrom` and foundation-production target `50 meV/angstrom`.

No current D4 behavior is authority for this review.

## 5. Review disposition

Return **D1 PASS** only if:

1. all six R1 blockers are actually closed;
2. no new material D1 contradiction or ambiguity is introduced;
3. the dependency/source closure is sufficient for D2 handoff;
4. unchanged accepted siblings remain unchanged in meaning.

If PASS, stakeholder ratification of exact target `2549dee709fb8bb383341ee3aebca7c71973a903` remains required before D1 becomes accepted-current and before D2 Gate C starts.

If NO-PASS, identify exact canonical D1 repair owners and keep Gate C blocked.
