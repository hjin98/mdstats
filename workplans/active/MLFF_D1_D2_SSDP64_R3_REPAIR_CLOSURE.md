---
kind: author-repair-closure
protocol_version: 6.4.0
status: READY_FOR_FRESH_INDEPENDENT_R3_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
prior_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R2.md
prior_immutable_target: a09e2b857da64e18fd7a6044f0fdad29aa29365d
superseded_preliminary_r3_target: 7a7316eef3a63e560d2d5be69835f454b5c6a8df
pem_basis: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
---

# MLFF D1/D2 Protocol-6.4 R3 repair closure

## 1. Author-side disposition

R2 returned NO-PASS with four candidate blockers and one separate downstream D4 conformance defect. This repair cycle does not change accepted D1/D2 meaning. It repairs the proposed Protocol-6.4 representation and the nonconformant D4 weighted-quantile realization.

A preliminary R3 target, `7a7316eef3a63e560d2d5be69835f454b5c6a8df`, was cut before independent review but is superseded author-side: its FP64 falsification fixture compared against `np.sum(weights)` rather than the exact residual quantity used by the old D4 implementation, `np.cumsum(weights, dtype=np.float64)[-1]`. That made three listed counterexamples non-discriminating for the actual defect. The preliminary target and its descendant handoff are historical only and must not be reviewed as the current R3 candidate.

The corrected proposed R3 authority surface is:

- `workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`;
- `workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`;
- `workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R3_FINAL.md` as non-authoritative review/impact evidence.

The executable descendant repair is:

- `mdstats/training_data/target_order/coverage_reference.py`;
- `tests/test_mlff_target_order_weighted_quantiles_fp64.py`.

Earlier R1/R2 candidate kernels/traces are superseded authoring history and must not compose with R3.

## 2. R2 blocker closure

### R2-B1 — configured-prefix validity: closed author-side

R3 D1 states explicitly that `Q_cfg` is the qualified subset of the configured ladder. One unqualified configured prefix is excluded from automatic screening and cannot be manually/operator admitted, but it does not fail the whole experiment when at least three other configured prefixes remain qualified. Fewer than three qualified configured candidates yields insufficient automatic comparison. D2.DEF.039 states the same numerical admission semantics.

### R2-B2 — replay qualification lineage: closed author-side

R3 D1.DEF.022 adds exact replay qualification-policy/evidence/current-state coordinate `Q_r` to replay lineage and states that qualification changes invalidate dependent P5 evidence. R3 D2.DEF.052 concretizes `Q_r`; checkpoint/currentness and production clauses consume the current lineage. Label-mode changes alone still cannot change authenticated replay geometry membership.

### R2-B3 — dependency trace closure: closed author-side

R3 adds exact D1 statistical import `D1.IMP.STAT` and binds D1.DEF.007 to it. R3 adds D2.DEF.060A as the explicit numerical-equivalence relation registry, so D2.DEF.061 no longer depends on a free-text equality/tolerance endpoint. R3 trace binds replay E0 through D2.DEF.051A and `D2.IMP.E0_HEADS`. The trace contains no intentional D1->D2 dependency and no intended strongly connected component.

### R2-B4 — replay-head E0 definition-before-use: closed author-side

R3 D2 imports accepted general D2 Section 8.3 as `D2.IMP.E0_HEADS` and defines D2.DEF.051A before replay lineage. `e_replay(Phi)` is bound to the same authenticated selected foundation checkpoint/head/lineage and is explicitly distinct from fitted target `e_target(Phi)`. Missing/mismatched replay-head E0 is fail-closed.

## 3. D4-F1 descendant conformance repair

Accepted D2 requires one normalization of correlation-balanced family weights and weighted quantiles that compare cumulative stored mass directly with governed `q`.

The real owner `coverage_reference.py::_weighted_quantiles` previously compared against `requested * total`, where `total = cumulative[-1]` was the residual terminal binary64 cumulative mass of already-normalized stored weights. The repair changes only that comparison to `requested`; the positive-finite stored-mass validation remains unchanged. Commit `3edcfced3d6111e1cf6d4d7cc6eceefce16fd2dd` is exactly one source-line replacement.

The corrected focused regression uses the production `correlation_balanced_weights` constructor, forms the exact old-code residual quantity with `cumulative = np.cumsum(weights, dtype=np.float64)` and `terminal_mass = cumulative[-1]`, and exercises governed quantiles. Discriminating cases are:

- counts `(50,1)`, `q=0.01`: direct index 0, residual-terminal-mass-rescaled index 1;
- counts `(2,6)`, `q=0.25`: direct index 0, rescaled index 1;
- counts `(1,6)`, `q=0.75`: direct index 4, rescaled index 3;
- counts `(1,150)`, `q=0.99`: direct index 148, rescaled index 147.

For these cases the terminal cumulative mass is respectively `1.0000000000000002`, `1.0000000000000002`, `0.9999999999999996`, and `0.999999999999995`, so all four distinguish direct-`q` from the prior `q * total` implementation. `np.sum(weights)` is deliberately not used as a substitute for `cumulative[-1]`: different binary64 reduction order can make `np.sum(weights)` exactly one even when the prior implementation's terminal cumulative mass is not.

An isolated execution of the exact production weight-construction and old/new threshold arithmetic passed all four corrected witnesses. The full repository regression suite was not executable in the current tool sandbox because no repository checkout/runtime environment is available there. This is not recorded as a pass; fresh review/CI must inspect or execute the committed test and affected regression as available.

## 4. Representation checks

Author-side inspection confirms:

- R3 D1 binds correlation estimand to the exact general-D1 Section 2.2 import;
- R3 D1 configured-prefix failure text is consistent with `Q_cfg` sufficiency;
- replay qualification is present in D1 and D2 lineage/currentness;
- replay-head E0 is defined/imported before lineage use;
- R3 D2 equivalence consumes D2.DEF.060A rather than a generic endpoint;
- the R3 trace names D2.DEF.051A and exact E0-head import directly;
- D4 source diff is exactly one line and does not widen tolerance or add fallback/wrapper machinery;
- the preliminary R3 FP64 oracle defect was caught before independent review and corrected against the exact old-code terminal cumulative-mass operation.

No Serious Challenge is raised against accepted D1/D2. No GPU qualification is part of this cycle.

## 5. R3 gate

The next descendant handoff must bind a new immutable corrected R3 semantic target and explicitly mark preliminary target `7a7316eef3a63e560d2d5be69835f454b5c6a8df` and its handoff as superseded. Fresh independent R3 review must examine the complete assembled corrected target, not inherit this closure as authority. At minimum it must reattempt all R1 findings, all R2-B1 through R2-B4 findings, definition/source/trace closure, renderer equivalence, and D4-F1 conformance using the exact `cumulative[-1]` counterfactual. PASS remains prerequisite to stakeholder ratification and canonical promotion.
