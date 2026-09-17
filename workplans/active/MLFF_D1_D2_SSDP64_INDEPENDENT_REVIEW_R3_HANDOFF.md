---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_R3_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: 7a7316eef3a63e560d2d5be69835f454b5c6a8df
prior_candidate_target: a09e2b857da64e18fd7a6044f0fdad29aa29365d
prior_review_result: R2_NO_PASS
branch: design/mlff-d1-d2-ssdp64-axiomatic-formalization
pem_basis: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
---

# Independent Review R3 handoff — MLFF D1/D2 Protocol-6.4 formalization

## 1. Binding target and review posture

Perform a fresh independent Protocol-6.4 assembled-candidate Review of immutable target

`7a7316eef3a63e560d2d5be69835f454b5c6a8df`

against accepted basis

`cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`.

This is a full-candidate review, not a delta review and not a confirmation of the author repair closure. Treat `MLFF_D1_D2_SSDP64_R3_REPAIR_CLOSURE.md`, prior reviews, PR comments, implementation behavior and test outputs strictly as evidence/challenges to independently reconstruct and falsify. They are not authority and their conclusions must not be inherited.

The accepted D1/D2 basis remains the four canonical method papers at `cb07d683...`. If accepted authority itself appears materially false, contradictory, ambiguous or impossible to concretize, raise a Serious Challenge rather than silently changing it. Otherwise candidate defects are ordinary NO-PASS findings.

## 2. Exact R3 candidate surface

Proposed authority/review representation:

- `workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`;
- `workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md`;
- `workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R3_FINAL.md` — non-authoritative derived trace.

Governing workflow/evidence history retained in target:

- `workplans/active/MLFF_D1_D2_SSDP64_AXIOMATIC_FORMALIZATION_WORKPLAN.md`;
- `workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R1.md`;
- `workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R2.md`;
- `workplans/active/MLFF_D1_D2_SSDP64_R2_REPAIR_CLOSURE.md`;
- `workplans/active/MLFF_D1_D2_SSDP64_R3_REPAIR_CLOSURE.md`.

Executable descendant conformance change/evidence:

- `mdstats/training_data/target_order/coverage_reference.py`;
- `tests/test_mlff_target_order_weighted_quantiles_fp64.py`.

Representation-only accepted-paper correction retained from the earlier candidate:

- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

Superseded R2 candidate kernels, R2 dependency trace and R2 handoff are absent from the immutable R3 target and remain recoverable only from Git history.

## 3. Required D1 Review

Reconstruct accepted D1 independently and challenge the R3 D1 kernel for lossless equivalence, including at least:

1. source/configuration/label compatibility and energy-conserving E/F/stress meaning;
2. protected relation and evidence-role/noninterference semantics;
3. exact `U_size = P_train dot-union M3`, controlled target-size experiment, target-force RMSE and recommendation/decision separation;
4. one deterministic complete `pi_train`, exact nested prefixes, selector-information boundary, family-role/catalog ownership, fixed 0.95 coverage and 0.01/0.99 extent coordinates, canonical hard obligations and repair continuity;
5. configured-prefix qualification versus automatic-screen sufficiency: an unqualified configured prefix must be excluded from `Q_cfg` and forbidden from manual admission without causing whole-method failure when at least three other configured candidates remain qualified;
6. foundation objective, exact foundation identity, composition-transfer identifiability and target-only correction fitting;
7. replay true-reference default/pseudo explicit opt-in, exact foundation binding, separate true-reference monitor, geometry invariance and the replay qualification coordinate `Q_r` as a lineage/currentness coordinate;
8. monitor/CV/production role semantics and independent role thresholds;
9. validity/failure language, parameter binding classes and D1->D2 handoff without silent strengthening or weakening.

Specifically verify that `D1.DEF.007` obtains the correlation estimand from the exact general-D1 Section 2.2 statistical import rather than the evidence-role import.

## 4. Required D2 Review

Reconstruct accepted D2 independently and challenge the R3 D2 kernel for exact numerical equivalence and definition closure, including at least:

1. source conventions, finite-sequence autocorrelation/Geyer truncation, complete-frame blocks and protected-event/relation construction;
2. structural policy, five-step protected-component ordering, exact first-predecessor `M3`, condition-balanced `pi_eval` and P3-common preparation;
3. exact target-order family catalog/applicability;
4. one and only one binary64 family-weight normalization; weighted quantiles must consume stored weights directly and compare cumulative mass to governed `q`, never `q * residual_sum`;
5. robust scale, local radius, adjacency, distinct MVQUAL `1e-12` versus MVSEL2 `1e-14` predicates, extents and hard obligations;
6. FEAS1/MVSEL2/certified-lazy equivalence/REPAIR2/MVQUAL/automatic admission, including the unqualified-prefix case in Section 3;
7. target E0 correction/null-space transfer and the separate replay/pretraining-head foundation E0 mapping;
8. `D2.DEF.051A` definition-before-use, exact `D2.IMP.E0_HEADS` Section 8.3 source, binding to the selected authenticated foundation checkpoint/head/lineage, and separation from `e_target(Phi)`;
9. replay geometry/mode/qualification lineage, true-reference retention, corpus exposure and checkpoint/currentness consequences;
10. monitor/fold/checkpoint/CV/fresh-production predicates and threshold boundaries;
11. `D2.DEF.060A` equivalence relation registry and `D2.DEF.061` source closure, with no free-text or backend-observed tolerance owner;
12. typed failures and D2->D3 handoff.

## 5. Reattempt every prior blocking class

Reattempt all R1 findings B1-B9, not just their repair sites:

- weighted quantile normalization;
- selector/MVQUAL tolerance separation;
- P1/P2/P3 numerical closure;
- required-family catalog;
- REPAIR2 completeness;
- replay mode/lineage;
- definition/source/dependency trace;
- parameter binding classes;
- PEM/HAS interface.

Reattempt all R2 findings B1-B4:

- configured-prefix exclusion versus whole-method failure;
- replay qualification lineage;
- dependency-trace exact source resolution;
- replay-head E0 definition-before-use.

A prior closure statement is not evidence that the blocker is closed.

## 6. Protocol-6.4 definition/dependency challenge

Independently inspect every material candidate object for definition-before-substantive-use and source availability. For the R3 trace specifically verify:

- every prerequisite is an exact candidate object or basis-pinned import/locator;
- no generic policy/provider/equality/tolerance endpoint remains;
- `D1.DEF.007 -> D1.IMP.STAT` is correct;
- `D2.DEF.051A -> D2.IMP.E0_HEADS` and `D2.DEF.052 -> D2.DEF.051A` are present and semantically direct;
- `D2.DEF.061 -> D2.DEF.060A` closes numerical-equivalence relation ownership;
- D1 has no downward semantic dependency on D2;
- the bounded candidate graph has no accidental strongly connected component;
- reverse-impact traversal from fixed/configurable parameters reaches all material descendants.

Do not accept the trace's own completeness claim as proof.

## 7. D4 weighted-quantile conformance challenge

R2 discovered that current D4 rescaled governed quantiles by the residual sum of already-normalized stored weights. The R3 target changes the real owner directly:

```python
indices = np.searchsorted(cumulative, requested, side="left")
```

The reviewer must verify the source diff is semantically exactly accepted D2.DEF.014 and does not create another normalization/tolerance/fallback path.

Independently execute or reconstruct discriminating FP64 cases generated by the production correlation-balanced weight constructor. The committed focused test currently uses:

- `(50,15)`, `q=0.01`: direct index 1 versus residual-rescaled index 0;
- `(2,57)`, `q=0.25`: direct index 1 versus residual-rescaled index 0;
- `(1,6)`, `q=0.75`: direct index 4 versus residual-rescaled index 3;
- `(14,50)`, `q=0.99`: direct index 62 versus residual-rescaled index 63.

Check these independently rather than inheriting the author's isolated result. Review affected tests/consumers sufficiently to determine whether the D4 repair is integrated cleanly. The author did not execute the full repository suite in the available tool sandbox, and there are no attached status checks on the immutable target; neither fact is a PASS.

## 8. Renderer, PEM/HAS and currentness checks

Verify the accepted scoped-D2 renderer rewrite remains mathematically identical: raw cardinality notation became explicit set cardinality and nested named means became the identical explicit finite sums/cardinalities. Search the candidate D1/D2 surfaces for unsupported renderer syntax classes previously identified.

Re-resolve current accepted basis and PEM before verdict. At handoff creation `main` remains exactly `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824` and the governing PEM basis is unchanged. Reconcile if either has advanced.

Canonical HAS dispositions to challenge for this cycle are:

```yaml
pem_basis:
  accepted_project_state: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
  accepted_pem: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
  - id: SP-002
    disposition: APPLICABLE
  - id: SP-003
    disposition: APPLICABLE
  - id: SP-004
    disposition: APPLICABLE
  - id: FF-001
    disposition: APPLICABLE
  - id: FF-002
    disposition: APPLICABLE
  - id: FF-003
    disposition: NOT_APPLICABLE
  - id: FF-004
    disposition: NOT_APPLICABLE
  - id: FF-005
    disposition: APPLICABLE
```

GPU qualification remains outside this cycle and must not be requested as an intermediate review gate.

## 9. Verdict and lifecycle rule

Return **PASS** only if the entire immutable R3 target is losslessly equivalent to accepted D1/D2, materially definition-closed/source-resolvable, the D4 quantile descendant conforms, and no genuinely blocking issue remains. Otherwise return **NO-PASS** with precise owner-level repair instructions and reopen the active workplan without mutating this immutable target.

A PASS does not promote this proposal. The exact reviewed R3 target must still receive stakeholder ratification before canonical D1/D2 promotion/reconciliation. Do not self-ratify or merge merely because the review passes.