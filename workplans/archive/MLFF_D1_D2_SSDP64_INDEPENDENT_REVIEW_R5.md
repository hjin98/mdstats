---
kind: independent-review-record
protocol_version: 6.4.0
status: NO_PASS
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: 058b856df249bd28212ba70e459babd1f29a6c42
binding_handoff: a32e74ad594de363bbf38ddb3def4cb89e11c49e
prior_candidate_target: 86fa8acec3cfc84584bfbd380163545d80de7a27
prior_review_result: R4_NO_PASS
serious_challenge: NONE
---

# Independent Review R5 — MLFF D1/D2 Protocol-6.4 formalization

## 1. Verdict

**NO-PASS.**

No Serious Challenge is raised against accepted D1/D2 authority at
`cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`.

The R5 candidate preserves the accepted scientific and numerical method on fresh
review. The D4 weighted-quantile repair remains correct and its real-owner
evidence remains current and applicable. The renderer repair remains
representation-equivalent.

One genuine Protocol-6.4 blocker remains: the R5 dependency trace is still
semantically incomplete under the active workplan's own direct-edge criterion.
R5 repaired the R4 witnesses but did not fully close symbol/domain owner
dependencies in the unchanged D1/D2 kernels.

## 2. Review basis and independence

This Review reconstructed accepted meaning from the four canonical accepted
method papers at basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`:

- `docs/methods/mlff_scientific_method.md`;
- `docs/methods/mlff_target_training_order_scientific_method.md`;
- `docs/methods/mlff_numerical_algorithmic_method.md`;
- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

At review time, `main` still resolves exactly to the accepted basis. PR #16 is
open/draft and points to the R5 handoff descendant, while the immutable target
under review remains `058b856d...`.

The R5 handoff, repair closure, prior reviews, CI evidence and PR comments were
treated as evidence/challenges only.

The accepted Project Engineering Memory remains blob
`67e3130d3703d9fc26ed0afe94fa2506a176e9ce` and reports no high-impact
unresolved notice. Fresh HAS challenge supports the same bounded dispositions:
SP-001/SP-002/SP-003/SP-004, FF-001/FF-002/FF-005 applicable; FF-003/FF-004 not
applicable to this formalization. PEM remains evidence-only.

## 3. D1 substantive review — PASS

The proposed D1 kernel remains blob
`dc05bc0a8fe5790b6ffe91bfacbd2bb25360a498` and was rechecked against accepted
D1 rather than inherited from prior review.

No scientific drift was found in:

- source occurrence/geometry/label identity and compatibility;
- energy-conserving E/F/stress semantics and physical conventions;
- protected-relation closure, evidence roles and noninterference;
- correlation estimand imported from the exact statistical owner;
- exact `U_size = P_train dot-union M3` controlled target-size experiment;
- deterministic complete `pi_train`, exact nested prefixes and selector
  evidence boundary;
- required family roles, correlation-balanced reference measure, fixed
  `0.95` hard coverage and `0.01/0.99` extents;
- canonical hard obligations, configured-shell repair continuity and independent
  membership qualification;
- qualified configured-candidate admission and recommendation/decision
  separation;
- foundation-P5 objective, selected-head E0 composition identifiability,
  replay label-mode/lineage/currentness semantics;
- common protected 256-frame monitor, post-selection folds, independent role
  thresholds, all-position CV and fresh production.

No D1 Challenge is raised.

## 4. D2 substantive review — PASS

The proposed D2 kernel remains blob
`74c0c0588617b7f48fd93bc21e534f538f037ef8`.

Fresh reconstruction found no numerical-method drift in:

- finite-sequence autocovariance/Geyer IPS, complete-frame blocks and protected
  event/relation closure;
- exact structural target-size policy and first-predecessor M3 allocation;
- condition-balanced `pi_eval` and candidate-common P3 preparation;
- required-family catalog/applicability;
- exactly one binary64 family-weight normalization and direct-q weighted
  quantiles;
- robust scale, leave-one-out radius, exact adjacency, distinct MVQUAL/MVSEL2
  tolerances and extents;
- canonical obligations, FEAS1, MVSEL2, certified-lazy execution, REPAIR2 and
  independent MVQUAL;
- P3 normalization, estimator, reducer/funnel/configured-ceiling and restart;
- foundation-residual E0/null-space transfer and replay-head E0 separation;
- replay qualification and exposure semantics;
- monitor/fold/checkpoint/CV/production predicates and currentness;
- authenticated continuation, numerical-equivalence registry and execution
  noninterference.

No upward D2 Challenge is raised.

## 5. R5-B1 — dependency trace remains semantically incomplete

**Blocking.**

The workplan defines a direct edge when changing prerequisite `B` can directly
change subject `A`'s denotation, domain, validity or interpretation. R5's
structural checks are clean (106 subjects, all endpoints resolved, no cycles),
but several local semantic owners are still omitted.

### 5.1 Definitive disconnected witnesses

These are not merely missing duplicate/transitive paths. Reverse traversal from
the omitted owner does not reach the subject at all.

1. **`D1.AX.004 -> D1.DEF.012` is missing.**

   `D1.AX.004` states that changing candidate cardinality changes only exact
   target prefix `T_N` and its consequences. `D1.DEF.012` is the local
   definition of `pi_train` and exact `T_N`. A material change to
   `D1.DEF.012` directly changes the controlled-variable axiom's meaning, but
   the current row is only `D1.DEF.008; D1.DEF.009; D1.IMP.P3`.

2. **`D1.AX.004 -> D1.DEF.010` is missing.**

   The same axiom explicitly requires the evaluation ladder to remain
   candidate-independent. `D1.DEF.010` is the local evaluation-ladder owner.
   Changing its membership semantics directly changes what the axiom requires
   to remain fixed, yet reverse impact does not reach `D1.AX.004`.

3. **`D1.DEF.013 -> D1.DEF.010` is missing.**

   Authorized selector evidence explicitly excludes `M3/M1/M2`.
   `D1.DEF.010` defines `M_i`, including `M1/M2`. Changing the evaluation
   ladder changes the evidence excluded from `I_sel`, but the current trace
   does not propagate that change to `D1.DEF.013`.

4. **`D1.DEF.020 -> D1.DEF.006` is missing.**

   `D1.DEF.020` requires target residual corrections to be fitted only on the
   authorized target-gradient domain and forbids monitor/held-out labels from
   resolving null directions. `D1.DEF.006` is the local role/permission owner
   and explicitly includes E0 fitting in the operation vocabulary. Changing that
   permission relation can directly change the authorized fit domain, but the
   current `D1.DEF.020` row contains only `D1.IMP.P5`.

These four witnesses alone falsify R5's semantic completeness claim.

### 5.2 Additional same-class missing direct edges

The row-by-row challenge also found the same defect class where reverse
reachability may already exist through another path but the required **direct**
semantic edge is absent:

- `D1.AX.003 -> D1.DEF.012`: the no-feedback axiom explicitly prohibits P3
  outcomes feeding backward into local `pi_train`;
- `D1.AX.008 -> D1.DEF.012`: post-selection CV is forbidden from altering
  local `T_N/pi_train`;
- `D1.AX.010 -> D1.DEF.008`: fresh production explicitly excludes P3 `M3`
  from checkpoint control;
- `D2.DEF.030 -> D2.DEF.012`: Phase A is active when **any required family**
  fails, and its canonical bottleneck domain is the local required-family
  catalog;
- `D2.DEF.031 -> D2.DEF.012`: entry to Phase B requires the relevant family
  predicates to have passed, so the required-family domain is material;
- `D2.DEF.041 -> D1.DEF.006`: the numerical E0 fit excludes monitor/held-out
  labels and therefore directly consumes the D1 role/E0-fitting permission
  boundary in addition to the fold/production membership owners added in R5.

The first four disconnected witnesses are independently sufficient for
NO-PASS; the additional edges are included so the next repair is not another
single-witness patch.

### 5.3 Required R6 repair

Do not change accepted D1/D2 meaning.

1. Repair the R5 trace at the derived representation owner, including at
   minimum every edge above.
2. Re-run all 106 objects with a **local-symbol/local-domain-owner pass**, not
   only explicit formal-ID mentions. Backticked or mathematical symbols such as
   `T_N`, `pi_train`, `M_i`, `M3`, role domains, required-family domains
   and local currentness coordinates must resolve to their local formal owners
   when those owners directly determine the subject.
3. Preserve the distinction between direct and transitive-only effects. Do not
   solve this by connecting every descendant to every upstream owner.
4. Re-run reverse-impact from all D1 local owners and D2 catalogs/predicates,
   specifically checking whether a material owner mutation reaches every
   proposition that explicitly constrains or excludes that object.
5. Retain the intentional `D2.DEF.029 !-> D2.DEF.020` non-edge: the text names
   the latter only to state that the predicates are distinct.
6. Retain bounded `D2.DEF.060A` relation-registry semantics unless a relation
   owner itself is directly consumed.
7. Recheck source closure, one-row-per-object, acyclicity and D1/D2 abstraction
   direction after semantic decisions.
8. Cut a new immutable target; do not mutate `058b856d...`.

## 6. D4 executable evidence — PASS/current

The real weighted-quantile owner at R5 is blob
`15d20eae5a7b481d636d20fc2281c743e9abe0df`; focused regression blob is
`8da42708ac601b335dfb3c9d818c302baccb1a78`; real-owner suite blob is
`01c6d99872c136cff91777e65ce8331807f8a016`.

Actions runs `35300235175` and `35300268107` both completed successfully,
including the focused FP64 regression and full real-owner target-order suite in
the supported CPU MLFF/test environment. Comparison from both evidence commits
to R5 shows only workflow/documentation/review changes; all three executable
evidence-target blobs are unchanged.

Independent binary64 reconstruction again gives:

```text
(2,6),   q=.25: direct 0, old residual-rescaled 1
(50,1),  q=.01: direct 0, old residual-rescaled 1
(1,6),   q=.75: direct 4, old residual-rescaled 3
(1,150), q=.99: direct 148, old residual-rescaled 147
```

Thus R3-B2 remains closed and no D4 rerun is required for a documentation-only
R6 trace repair unless executable evidence targets or environment assumptions
change.

## 7. Renderer / PEM / lifecycle

Renderer repair: **PASS**. The target scoped-D2 narrative has neither
`\operatorname` nor raw escaped-hash cardinality on the repaired surface; the
branch delta is the algebraically identical cardinality/nested-mean rewrite.

PEM/HAS: no blocker. No high-impact unresolved notice exists on accepted main;
the existing applicability set remains coherent for this bounded formalization.

## 8. Lifecycle disposition

Immutable R5 target
`058b856df249bd28212ba70e459babd1f29a6c42` remains **NO-PASS**.

The active workplan remains `REVIEW_NO_PASS_REOPENED`. No stakeholder
ratification, canonical promotion or merge is permitted from R5.

A fresh R6 assembled-candidate review is required after dependency-trace repair.
Because the semantic kernels and D4 owner/tests need not change for this
blocker, current executable evidence may be reused if exact blob/environment
applicability remains intact.
