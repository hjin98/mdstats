---
kind: independent-review-record
protocol_version: 6.4.0
status: NO_PASS
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: 12af89b860511277246e853a1e7ba22b86cec39f
binding_handoff: fbf4d9f92be47efb84280590d8be41b713592a6b
prior_candidate_target: 058b856df249bd28212ba70e459babd1f29a6c42
prior_review_result: R5_NO_PASS
serious_challenge: NONE
---

# Independent Review R6 — MLFF D1/D2 Protocol-6.4 formalization

## 1. Verdict

**NO-PASS.**

No Serious Challenge is raised against accepted D1/D2 authority at
`cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`.

Fresh assembled-candidate review finds the proposed D1 and D2 kernels
substantively lossless, the weighted-quantile D4 repair current and applicable,
the renderer repair equivalent, and PEM/HAS state coherent.

The remaining blocker is again confined to the non-authoritative dependency
trace. R6 closes the R5 local-symbol/domain-owner witnesses, but two direct
semantic prerequisites remain omitted under the workplan's own criterion.

## 2. Review basis and independence

The exact immutable candidate reviewed is
`12af89b860511277246e853a1e7ba22b86cec39f`, bound by descendant handoff
`fbf4d9f92be47efb84280590d8be41b713592a6b`.

At review time accepted `main` still resolves exactly to
`cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. PR #16 remains open/draft and
points to the handoff descendant.

Accepted D1/D2 meaning was reconstructed from the four canonical method papers,
not inherited from R5/R6 author claims:

- `docs/methods/mlff_scientific_method.md`;
- `docs/methods/mlff_target_training_order_scientific_method.md`;
- `docs/methods/mlff_numerical_algorithmic_method.md`;
- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

Prior reviews, repair closures, handoff text, CI and PR comments were treated
only as evidence/challenge material.

The accepted Project Engineering Memory remains blob
`67e3130d3703d9fc26ed0afe94fa2506a176e9ce` and reports no high-impact
unresolved notice. The bounded HAS dispositions remain coherent:
SP-001/SP-002/SP-003/SP-004 and FF-001/FF-002/FF-005 applicable;
FF-003/FF-004 not applicable to this formalization.

## 3. D1 substantive review — PASS

The proposed D1 kernel remains blob
`dc05bc0a8fe5790b6ffe91bfacbd2bb25360a498`.

Fresh review found no scientific drift in:

- source occurrence/geometry/label identity, compatibility and physical
  E/F/stress semantics;
- protected-relation closure, role permissions and evidence noninterference;
- statistical estimand ownership;
- exact `U_size = P_train dot-union M3` experiment;
- one deterministic complete `pi_train`, nested `T_N`, authorized selector
  evidence and no-feedback semantics;
- correlation-balanced required-family measure, fixed 0.95 coverage and
  0.01/0.99 extents;
- canonical hard obligations, shell-repair continuity, independent membership
  qualification and qualified-candidate admission;
- P3 response/recommendation versus operator decision;
- foundation-P5 1:10:1 robust objective, selected-head E0 identifiability,
  replay label/lineage/currentness;
- common 256-frame target monitor, protected post-selection folds, independent
  role thresholds, all-position CV and fresh production.

No D1 Challenge is raised.

## 4. D2 substantive review — PASS

The proposed D2 kernel remains blob
`74c0c0588617b7f48fd93bc21e534f538f037ef8`.

Fresh review found no numerical-method drift in:

- finite-sequence autocorrelation, complete-frame blocks and protected-event
  relation closure;
- exact P2 structural policy, first-predecessor M3 split and condition-balanced
  evaluation order;
- P3 common preparation;
- required-family catalog and one-normalization binary64 witness weights;
- direct-q stable weighted quantiles, robust scale, local radius and exact
  adjacency;
- distinct MVSEL2 and MVQUAL tolerances, extents, canonical obligations and
  FEAS1;
- exact MVSEL2/full-forward/lazy semantics, REPAIR2 and independent MVQUAL;
- P3 normalization, estimator, practical-equivalence reducer, funnel,
  configured-ceiling rule and authenticated restart;
- foundation residual E0/null-space transfer and selected replay-head E0;
- robust P5 objective and replay-first exposure;
- monitor/fold/checkpoint/CV/production/currentness semantics;
- authenticated continuation, equivalence registry and execution
  noninterference.

No upward D2 Challenge is raised.

## 5. R6-B1 — typed-failure aggregation omits D2.DEF.015

**Blocking.**

`D2.DEF.015 — Robust scale` explicitly states:

> Non-finite input fails preparation.

`D2.DEF.062 — Typed failure set` explicitly says to fail closed for
“non-finite fitted statistics.”

The trace itself states that the `D2.DEF.062` row enumerates definitions that
**directly contribute one of the typed failure members**. Yet its prerequisite
row omits `D2.DEF.015`.

This is a direct semantic edge:

```text
D2.DEF.062 -> D2.DEF.015
```

A material change to D2.DEF.015 from fail-closed non-finite input to clamping,
fallback or another policy would directly change the typed failure set. The
existing transitive reverse path

```text
D2.DEF.015 -> D2.DEF.016 -> D2.DEF.017 -> D2.DEF.062
```

does not close that direct dependency; Protocol 6.4 requires the direct edge
when the prerequisite itself defines a typed member.

This witness independently falsifies R6 trace completeness.

## 6. R6-B2 — evaluation-ladder role classification omits D1.DEF.006

**Blocking.**

`D1.DEF.010 — Evaluation ladder` does more than construct nested `M_i`.
It normatively states:

> `M_i` are P3 model-selection populations, not post-selection held-out or
> checkpoint-monitor evidence.

`D1.DEF.006 — Evidence-role permission system` is the local formal owner for
the evidence-role vocabulary and authorization relation, explicitly including
P3 model selection, checkpoint monitor and held-out CV roles.

Therefore changing D1.DEF.006's role vocabulary/meaning can directly change the
interpretation and validity of D1.DEF.010's role classification. The required
direct edge is:

```text
D1.DEF.010 -> D1.DEF.006
```

The current reverse path

```text
D1.DEF.006 -> D1.DEF.008 -> D1.DEF.010
```

is insufficient: D1.DEF.008 carries the target-size split and M3 reserve, but
does not own D1.DEF.010's explicit negative role statement distinguishing the
evaluation ladder from held-out and checkpoint-monitor evidence.

This is the same local-domain-owner defect class that R6 intended to close.

## 7. Same-class challenges examined

The review did not promote heuristic symbol matches into dependencies without
semantic ownership.

In particular:

- `D2.DEF.056` may remain mediated by `D1.DEF.024` for frozen `T_N`,
  fold roles and monitor externality;
- `D2.AX.005` may remain mediated by `D1.AX.010`, `D2.DEF.052` and
  `D2.DEF.058` for M3/monitor/replay/production-threshold semantics;
- `D2.DEF.029 !-> D2.DEF.020` remains a genuine non-dependency because the
  former names the latter only to assert the predicates are distinct;
- `D2.DEF.060A` remains a comparison-relation registry rather than a direct
  consumer of every value-generating operand;
- target-size foundation/head identity used by P3/order remains scoped through
  the exact P3/order imports unless a local object actually consumes the
  post-selection composition-correction object of `D1.DEF.020`;
- an empty extent predicate in `D2.DEF.021` is a qualification predicate
  failure, not automatically a member of the global typed-error set;
- `D2.DEF.055`'s distinct systematic positions are an exact monitor
  construction invariant under its stated domain, not independently treated as
  the “impossible 256-monitor” source already owned by `D2.DEF.054`.

These classifications should still be challenged again by the next independent
review, but they are not R6 blockers on current evidence.

## 8. D4 executable evidence — PASS/current

At the R6 target:

- weighted-quantile owner blob:
  `15d20eae5a7b481d636d20fc2281c743e9abe0df`;
- focused FP64 regression blob:
  `8da42708ac601b335dfb3c9d818c302baccb1a78`;
- real-owner target-order suite blob:
  `01c6d99872c136cff91777e65ce8331807f8a016`.

Actions runs `35300235175` and `35300268107` both completed successfully,
including the focused weighted-quantile regression and real-owner target-order
integration/regression in the supported CPU MLFF/test environment.

Comparison from each evidence commit to the immutable R6 target changes only
the temporary validation workflow and documentation/review artifacts; all three
executable evidence-target blobs remain byte-identical.

Independent binary64 reconstruction again reproduces the four required
discriminators:

```text
(2,6),   q=.25: direct 0, old residual-rescaled 1
(50,1),  q=.01: direct 0, old residual-rescaled 1
(1,6),   q=.75: direct 4, old residual-rescaled 3
(1,150), q=.99: direct 148, old residual-rescaled 147
```

No D4 rerun is required for a documentation-only R7 trace repair unless the
owner/tests or execution-environment contract change.

## 9. Renderer / PEM / lifecycle

Renderer repair: **PASS**. The current scoped target-order D2 paper on the R6
target contains neither unsupported `\operatorname` nor raw escaped
cardinality `\#`; the rewrite remains mathematically equivalent.

PEM/HAS: **PASS** for this bounded cycle. No high-impact unresolved notice is
active and no newer accepted semantic basis displaced the pinned main commit.

## 10. Required R7 repair

Do not alter accepted/proposed D1 or D2 semantics.

1. Repair the derived trace at its real representation owner by adding at
   minimum:
   - `D2.DEF.062 -> D2.DEF.015`;
   - `D1.DEF.010 -> D1.DEF.006`.
2. Re-run the complete 106-object semantic pass, with two explicit focused
   sweeps:
   - every normative evidence-role classification/exclusion against
     `D1.DEF.006`;
   - every explicit fail/failure/infeasible/undefined typed member against
     `D2.DEF.062`.
3. Preserve direct-versus-transitive distinction; do not dense-connect the
   graph merely because an upstream object is reverse-reachable.
4. Recheck every R6 deliberate non-edge independently.
5. Re-run one-row-per-object, endpoint/source closure, acyclicity, abstraction
   direction and reverse-impact checks.
6. Cut a new immutable target. Do not mutate
   `12af89b860511277246e853a1e7ba22b86cec39f`.
7. Reuse current D4 evidence only if the exact owner/test blobs and environment
   applicability remain unchanged.

GPU qualification remains outside this gate.

## 11. Lifecycle disposition

Immutable R6 target
`12af89b860511277246e853a1e7ba22b86cec39f` remains **NO-PASS**.

No stakeholder ratification, canonical promotion or merge is permitted from
R6. A fresh R7 assembled-candidate review is required after the trace-only
repair.
