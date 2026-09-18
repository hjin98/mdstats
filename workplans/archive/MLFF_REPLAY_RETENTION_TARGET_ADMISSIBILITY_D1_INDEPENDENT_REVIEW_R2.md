---
kind: independent-d1-review
protocol_version: 6.4.0
status: COMPLETE
review_disposition: D1_PASS
serious_challenge: NONE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
reviewed_immutable_candidate: 2549dee709fb8bb383341ee3aebca7c71973a903
reviewed_d1_blob: 8667ee1abdb568a58ac945c87c9e2d7386dcf49b
dependency_trace_blob: dc8038b81f2f168cd258ba0098e9b9edcc1b6c55
review_date: 2026-09-18
highest_open_owner: D1
stakeholder_ratification_required: true
d2_gate_state: BLOCKED_PENDING_D1_RATIFICATION
---

# Independent D1 Review R2 — replay retention and target admissibility renewal

## 1. Disposition

**D1: PASS. No SERIOUS CHALLENGE.**

The reviewed immutable target is:

`2549dee709fb8bb383341ee3aebca7c71973a903`

against accepted Protocol-6.4 D1 baseline:

`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`.

The reviewed canonical D1 blob is:

`8667ee1abdb568a58ac945c87c9e2d7386dcf49b`.

The bounded dependency trace is:

`dc8038b81f2f168cd258ba0098e9b9edcc1b6c55`.

This review does not promote the candidate by itself. Exact-target stakeholder ratification is still required before D1 becomes accepted-current and before Gate C may begin.

## 2. Independent reconstruction and challenge basis

The review reconstructed the accepted D1 from the current Protocol-6.4 kernel and its exact imports, including the accepted P5 source paper at `a4824d28775164aa942fd29fa97ee0957eb87e6f`.

The R1 review, R2 repair trace, active workplan, motivating training trajectory, current implementation and Project Engineering Memory were treated as evidence/challenge material only. None was used as authority to rewrite D1.

The accepted Project Engineering Memory adds no counterexample to the repaired D1 semantics. Its relevant lessons concern authenticated TRAIN2/EVAL2 identity, immutable restart boundaries and real-owner integration; those are downstream realization constraints, not contrary scientific authority.

## 3. R1 closure verification

### 3.1 Governed checkpoint universe — CLOSED

R2 defines `C_rho` as the governed checkpoint universe of the realized fixed-budget TRAIN2 trajectory and explicitly requires every checkpoint position required by the accepted checkpoint cadence and durably committed by that trajectory to enter assessment.

The candidate now forbids replacement of `C_rho` by:

- quality-dependent shortlist;
- refinement subset;
- rescue subset;
- evaluator-purchased subset.

Failure to authenticate, reconstruct or evaluate a required member is routed through hard evidence/integrity semantics rather than permission to silently remove a potentially better checkpoint.

The representative is then selected from:

`argmin_{c in H_rho} r_mon(c)`

where `H_rho` is the hard-admissible subset of `C_rho`.

This closes R1. Exact checkpoint-cadence realization and durable enumeration remain legitimate D2 numerical-method responsibilities, but D2 may not quality-thin the governed universe.

### 3.2 Exact foundation replay baseline — CLOSED

`D1.DEF.022` now makes exact frozen foundation checkpoint/head/model identity `Phi` a mandatory replay-retention lineage parent whenever replay-retention assessment is enabled, regardless of whether training labels are `TRUE_REFERENCE` or `FOUNDATION_PSEUDO`.

`D1.DEF.022A` evaluates the foundation baseline on the same exact true-reference replay membership and therefore has a source-closed foundation-relative degradation observable.

Pseudo-label mode adds provider dependence on the same `Phi`; it is no longer the condition that makes `Phi` scientifically relevant.

### 3.3 Warning-only currentness — CLOSED

`D1.AX.010A` now makes the scientific dependency asymmetry explicit.

A `delta_warn` change affects replay-warning/diagnostic classification only. It cannot by itself move:

- `H_rho`;
- checkpoint representative;
- outer-evaluation membership;
- CV pass/fail;
- production authorization;
- publication membership.

By contrast, `delta_hard`, role target ceilings and representative/publication ordering are permitted to move their legitimate hard-decision descendants.

Neither diagnostic-only nor hard assessment-policy changes redefine an already-realized training trajectory when training-bearing scientific semantics are unchanged.

### 3.4 Threshold boundary ownership — CLOSED

R2 explicitly retains at D1:

- force-error dimension;
- warning only for strict exceedance of `delta_warn`;
- catastrophic hard failure only for strict exceedance of `delta_hard`;
- equality at either threshold does not trigger that corresponding class.

D2 is restricted to numerical realization: canonical unit representation/conversion, finite machine representation, comparison implementation, numerical boundary oracles and typed numerical failure.

There is no remaining authority path for D2 to alter the scientific inequality.

### 3.5 TRUE_REFERENCE terminology — CLOSED

The repaired candidate is source-closed against accepted:

`TRUE_REFERENCE | FOUNDATION_PSEUDO`.

The retention observable is defined on the exact independent true-reference replay monitor. DFT / `true_dft` appears only as the current project realization of that role.

No third replay label-mode or DFT-only scientific narrowing is introduced.

### 3.6 Renderer-safe representation — CLOSED

The repaired candidate contains no standalone single-dollar display fence and no duplicate formal D1 identifiers. The R1 representation repair restored the accepted `$$ ... $$` display form without changing the mathematical relations.

## 4. Dependency/source-closure review

The R2 non-authoritative dependency trace is sufficient for the changed/new D1 objects.

In particular:

```text
D1.DEF.022  -> D1.DEF.020, D1.DEF.021, D1.IMP.P5
D1.DEF.022A -> D1.DEF.020, D1.DEF.022, D1.IMP.P5
D1.DEF.025  -> D1.DEF.023, D1.DEF.024, D1.IMP.P5
D1.DEF.026  -> D1.DEF.022A, D1.DEF.023, D1.DEF.025, D1.IMP.P5
D1.DEF.027  -> D1.DEF.026, D1.IMP.P5
D1.AX.009   -> D1.DEF.024, D1.DEF.025, D1.DEF.026, D1.IMP.P5
D1.AX.010   -> D1.DEF.012, D1.DEF.020, D1.DEF.022, D1.DEF.022A,
               D1.DEF.023, D1.DEF.025, D1.DEF.026, D1.IMP.P5
D1.AX.010A  -> D1.DEF.022A, D1.DEF.025, D1.DEF.026, D1.DEF.027,
               D1.AX.009, D1.AX.010
```

The repaired wording supplies the previously missing direct foundation-identity and governed-checkpoint-universe semantics. No D1 object obtains meaning from its future D2 concretization.

## 5. Scientific Challenge Pass

### 5.1 Replay warning/hard split

No Serious Challenge is raised.

The candidate preserves mandatory independent true-reference replay evidence and a hard catastrophic-forgetting constraint while allowing moderate degradation to remain diagnostic. This is scientifically coherent because replay is explicitly an auxiliary inherited-capability observable rather than the target-domain quality estimand or downstream release criterion.

The generated defaults `50/100 meV/angstrom` are correctly scoped as stakeholder-selected configurable policy calibrations, not universal physical constants. The candidate carries an explicit reopen condition if later evidence shows the catastrophic limit permits unacceptable inherited-capability loss.

### 5.2 Production target default

No Serious Challenge is raised to `tau_prod = 50 meV/angstrom`.

The candidate correctly treats `tau_CV`, `theta_CV` and `tau_prod` as independent role-policy coordinates. It explicitly supersedes the imported historical rationale that production must be numerically stricter than CV.

The role separation remains intact:

- common monitor controls checkpoint quality;
- held-out fold controls CV acceptance;
- downstream qualification controls external/deployment adequacy.

Therefore `tau_prod > tau_CV` under current defaults is not itself a contradiction.

### 5.3 Strict target-RMSE checkpoint ordering

No Serious Challenge is raised.

After every hard validity/target/replay constraint is satisfied, minimum common-monitor target force RMSE is a coherent primary model-control objective for the stakeholder-directed target domain.

The candidate blocks every reviewed route by which a checkpoint with strictly worse target RMSE could be promoted through:

- replay margin or warning status;
- secondary target metrics;
- energy/stress diagnostics;
- maturity/refinement phase;
- practical-equivalence bands;
- bootstrap uncertainty;
- historical target/replay checkpoint-score weights.

Exact ties are correctly delegated to a deterministic non-quality D2 tie rule.

### 5.4 Final publication ordering

`single_best_final_seed` is materially narrowed but scientifically coherent: it selects the minimum target-RMSE member from already-frozen admissible seed representatives.

`all_qualified_final_seeds` remains unranked.

Downstream qualification remains downstream and cannot feed back into publication membership.

### 5.5 Fresh-production reassessment

The repaired D1 preserves fresh-production scientific meaning.

A historical final trajectory may support current reassessment only if:

- it was genuinely fresh rather than descended from a CV model/checkpoint;
- current CV authority is reclosed and accepted;
- exact training-semantic equivalence is established.

A current CV rejection blocks current publication even if historical final checkpoint bytes remain retained evidence.

No CV-trained state is promoted into final production.

## 6. Regression audit

No material drift was found in the unchanged accepted D1 siblings:

- P1-P4 and target-order semantics remain imported unchanged;
- P3 target-size and practical-equivalence semantics remain unchanged;
- foundation objective/E0/exposure semantics remain unchanged;
- common monitor cardinality and fold construction remain unchanged;
- scratch post-selection semantics remain outside this foundation-only threshold revision;
- fixed-budget training remains mandatory;
- downstream physical/deployment qualification remains a separate no-feedback layer.

The bounded import-supersession statement is sufficient to prevent the old replay hard-budget, old `30 meV/angstrom` production default, old "production must be stricter" rationale, and old uncertainty/secondary/maturity checkpoint ordering from regaining authority on the reopened surface.

## 7. D1 -> D2 handoff constraints after ratification

If the stakeholder ratifies exact target `2549dee709fb8bb383341ee3aebca7c71973a903`, D2 must concretize without changing:

1. signed foundation-relative true-reference replay degradation;
2. strict warning/hard inequalities and dimensions;
3. configurable generated defaults `50/100 meV/angstrom`;
4. foundation role thresholds `45/45/50 meV/angstrom`;
5. governed checkpoint universe with no quality-dependent thinning;
6. target-only `argmin` representative and `single_best_final_seed` ordering;
7. deterministic non-quality exact tie handling;
8. fixed-budget training;
9. warning-only diagnostic currentness;
10. hard-policy/target/selection reassessment currentness;
11. current-CV reauthorization for reusable historical fresh final trajectories;
12. typed numerical failure for missing/invalid required replay or checkpoint evidence.

Exact durable enumeration, cadence representation, floating-point comparison, unit conversion, tie keys, restart identity, evidence persistence and storage realization remain D2/D3 concerns subject to these D1 invariants.

## 8. Final disposition and lifecycle

**D1 PASS.**

No blocking D1 finding remains on immutable candidate `2549dee709fb8bb383341ee3aebca7c71973a903`.

No Serious Challenge is raised.

The candidate is **review-passed but not yet accepted-current**.

Required next lifecycle action:

1. stakeholder explicitly ratifies exact target `2549dee709fb8bb383341ee3aebca7c71973a903`;
2. only then close Gate B and begin Gate C D2 renewal.

Absent that ratification, accepted current D1 remains `main@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`.
