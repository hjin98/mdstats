---
kind: independent-review-record
protocol_version: 6.4.0
status: NO_PASS
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
immutable_candidate_target: 045cb5a052fdb83b6c6cd561142b24fdf5d023b5
binding_handoff: 5347daa00afb131e0206e99d37ddaad33529ecc6
prior_candidate_target: a09e2b857da64e18fd7a6044f0fdad29aa29365d
prior_review_result: R2_NO_PASS
serious_challenge: NONE
---

# Independent Review R3 — MLFF D1/D2 Protocol-6.4 formalization

## 1. Verdict

**NO-PASS.**

No Serious Challenge is raised against the accepted D1/D2 authority at `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`.

The repaired R3 D1/D2 kernels close the substantive R2 semantic blockers found in the prior review, and the direct D4 weighted-quantile source repair is numerically consistent with accepted D2. Two genuine acceptance blockers remain:

1. the Protocol-6.4 direct semantic dependency trace is still materially incomplete; and
2. the D4 executable change has focused/source-level evidence but has not received the required affected-surface real-owner regression/integration acceptance on the reviewed candidate.

The immutable target must not be promoted or ratified. Repair must produce a new immutable review target because the dependency trace is part of the assembled candidate.

## 2. Review basis and independence

This Review independently reconstructed the accepted method from the four canonical papers at the accepted basis:

- `docs/methods/mlff_scientific_method.md`;
- `docs/methods/mlff_target_training_order_scientific_method.md`;
- `docs/methods/mlff_numerical_algorithmic_method.md`;
- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

`main` was re-resolved at review time and remained exactly `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`; there is no accepted-basis drift or rebase blocker.

The R2/R3 repair closures, prior reviews, PR comments, implementation and tests were treated as evidence/challenges only. Their conclusions were not inherited.

The Project Engineering Memory on current accepted `main` has the same canonical blob as the handoff-pinned `b5d101d8f73d3efd63ef4e70b3913e7d281406ce` publication. It reports no high-impact unresolved notice. The applicable Historical Applicability Set remains:

```yaml
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

The PEM is evidence-only and does not alter D1-D4 authority.

## 3. D1 review — substantive closure passes

The R3 D1 kernel is losslessly aligned on the reviewed high-risk surfaces:

- physical/source/label compatibility and energy-conserving E/F/stress semantics remain imported from the accepted general D1 owner;
- `D1.DEF.007` now obtains the correlation estimand from exact `D1.IMP.STAT = D1.SRC.GENERAL §2.2`, rather than the evidence-role import;
- protected-relation closure and evidence noninterference remain intact;
- exact `U_size = P_train dot-union M3`, one complete deterministic `pi_train`, exact nested prefixes, authorized selector evidence, required family roles, fixed `0.95` coverage and `0.01/0.99` extents, canonical obligations, repair continuity and MVQUAL separation are preserved;
- `D1.DEF.018` correctly distinguishes an unqualified configured prefix from whole-method failure: the prefix is excluded from `Q_cfg` and cannot be manually admitted, while automatic comparison proceeds when at least three other configured candidates remain qualified;
- robust foundation-P5 semantics, selected-head E0 identifiability, common monitor, CV/production role separation and configurable `45/45/30 meV/angstrom` generated defaults remain faithful;
- `D1.DEF.022` now carries replay qualification identity/currentness `Q_r` as a first-class replay-lineage coordinate, and a label-mode change alone still cannot change replay geometry membership.

No D1 blocker or Serious Challenge was found.

## 4. D2 review — substantive closure passes

The R3 D2 kernel restores the required numerical closure without changing the accepted method. Independently checked material surfaces include:

- unbiased finite-sequence autocovariance, Geyer initial-positive-sequence truncation, complete-frame block construction and protected-event/relation closure;
- current target-size structural-policy domain, five-step protected-component ordering, exact first-predecessor `M3` subset-sum membership, condition-balanced `pi_eval` and candidate-common preparation;
- complete target-order family catalog and applicability;
- exactly one binary64 correlation-balanced family-weight normalization and stable weighted quantiles consuming stored weights directly;
- robust scale, leave-one-out local radius, exact adjacency, distinct MVQUAL `1e-12` and MVSEL2 `1e-14` predicates and extent rules;
- canonical obligations, FEAS1, exact MVSEL2 priorities, certified-lazy termination/guard, complete REPAIR2 frontier/objective/limits/rank inheritance/no-extra-shell semantics and independent MVQUAL;
- automatic admission from qualified `Q_cfg` with minimum three qualified candidates;
- target E0 fit/null-space transfer and separate replay/pretraining-head E0;
- `D2.DEF.051A` exact import from general-D2 §8.3, selected checkpoint/head binding and separation from target corrected E0;
- replay qualification/currentness, replay-first corpus exposure, true-reference retention, common monitor/folds, checkpoint/CV/production predicates and selective invalidation;
- practical-equivalence reducer, exact funnel/success sufficiency and configured-ceiling rule;
- the new `D2.DEF.060A` removes the R2 free-text equality/tolerance endpoint and gives a bounded equivalence registry.

No accepted D2 numerical method defect was found; there is no upward D2 Challenge.

## 5. R3-B1 — direct dependency trace remains incomplete

**Blocking.**

The workplan requires recoverable direct material `USES_DEFINITION` edges. R3 correctly repairs the R2 correlation owner, replay-head E0 owner and free-text equivalence endpoint, but the trace still omits direct prerequisites for material formal objects.

The clearest falsifying witness is `D2.DEF.062 — Typed failure set`. The candidate definition explicitly fails closed for, among other cases:

- `non-finite P3 outcome`;
- `insufficient reducer comparison`;
- `no admissible checkpoint`; and
- `materially different objective/exposure/method`.

Those outcomes are directly defined by candidate objects including:

- `D2.DEF.047` — P3 estimator/complete-seed score;
- `D2.DEF.049` — funnel/comparison sufficiency;
- `D2.DEF.058` — role-effective checkpoint predicate;
- `D2.DEF.045` — foundation-P5 objective; and
- `D2.DEF.053` — combined corpus/update geometry.

Yet the R3 trace row for `D2.DEF.062` omits all five. The trace itself states that this row enumerates definitions that directly contribute typed failure members, so these omissions are not merely transitive-edge compression. Changing any of those omitted definitions can directly change the denotation of a `D2.DEF.062` failure member without reverse traversal reaching `D2.DEF.062`.

This violates the candidate's bounded completeness claim and the workplan's direct-edge acceptance condition.

### Required repair

Do not change accepted D1/D2 semantics. Repair the derived Protocol-6.4 trace at the real representation owner:

1. add the missing direct `D2.DEF.062` prerequisites, including at minimum `D2.DEF.045`, `D2.DEF.047`, `D2.DEF.049`, `D2.DEF.053`, and `D2.DEF.058`;
2. re-run an object-by-object forward source-availability and reverse-impact pass over the complete R3 graph rather than patching only those witness edges;
3. specifically challenge catch-all/currentness/continuation/equivalence objects for the same kind of hidden local-definition dependency;
4. keep transitive-only edges omitted, but ensure every edge whose prerequisite can directly change a subject's denotation, validity, failure classification, equality relation or interpretation is present;
5. retain exact basis-pinned import roots; do not reintroduce generic policy/provider/equality/tolerance endpoints;
6. verify acyclicity after the repair and recheck parameter-anchor reverse impact.

Because the assembled trace changes, cut a new immutable semantic/review target rather than rewriting `045cb5a0...` in place.

## 6. R3-B2 — D4 executable acceptance evidence is incomplete

**Blocking evidence gap; the source repair itself is not rejected.**

The real D4 owner `mdstats/training_data/target_order/coverage_reference.py::_weighted_quantiles` now compares cumulative stored weights directly to `requested`, retaining `cumulative[-1]` only for positive/finite mass validation. This is the direct minimal repair required by accepted D2 and introduces no wrapper, fallback, tolerance widening or second owner.

Independent binary64 reconstruction of the production `correlation_balanced_weights` arithmetic and the exact former `cumulative[-1]` rescaling produced the following discriminators:

```text
counts (2,6),   q=.25: direct 0, old residual-rescaled 1
counts (50,1),  q=.01: direct 0, old residual-rescaled 1
counts (1,6),   q=.75: direct 4, old residual-rescaled 3
counts (1,150), q=.99: direct 148, old residual-rescaled 147
```

Thus the repaired algorithm and focused test oracle are numerically sound.

However, the reviewed target has no executed affected-surface D4 regression/integration evidence. The repository's only GitHub Actions workflow is documentation publication; the only branch workflow run is the earlier renderer build at `c9d3a9b4...`. No target-order functional CI ran on `045cb5a0...`. The current review environment also lacks a repository checkout, so the real owner and assembled target-order consumer chain cannot be executed here.

A material executable change requires focused evidence **and** affected regression/integration through the real owner. Source inspection plus a reconstructed arithmetic oracle cannot substitute for that assembled boundary.

### Required acceptance evidence

On the repaired new target, execute at least:

```text
pytest -q tests/test_mlff_target_order_weighted_quantiles_fp64.py
pytest -q tests/test_mlff_target_order_real_owner.py
```

The second command is the current real-owner D4 target-order suite and exercises the assembled `TargetCoverageReference` / preparation / selector / qualification chain. If a failure or collection constraint shows that these do not bound the affected surface, expand to the relevant `tests/test_mlff_target_order_*.py` affected suite rather than weakening/skipping the check.

Record the exact candidate commit and numerical environment. GPU qualification is not required for this CPU numerical repair and remains deferred under project policy.

## 7. Prior-blocker disposition

R1 findings:

- B1 weighted-quantile candidate semantics: **CLOSED**; D4 source repair is correct, but executable acceptance remains open as R3-B2.
- B2 selector/MVQUAL tolerance separation: **CLOSED**.
- B3 P1/P2/P3 numerical closure: **CLOSED**.
- B4 required family catalog: **CLOSED**.
- B5 REPAIR2 completeness: **CLOSED**.
- B6 replay semantics: **CLOSED**.
- B7 definition/source trace: **NOT FULLY CLOSED**; R2-specific defects are repaired, but R3-B1 identifies remaining direct-edge omissions.
- B8 binding classes: **CLOSED**.
- B9 PEM/HAS interface: **CLOSED for this candidate**.

R2 findings:

- R2-B1 configured-prefix exclusion versus whole-method failure: **CLOSED**.
- R2-B2 replay qualification lineage: **CLOSED**.
- R2-B3 named R2 correlation/equivalence/E0 trace defects: **CLOSED**, with new broader trace-completeness defect R3-B1.
- R2-B4 replay-head E0 definition-before-use: **CLOSED**.

Renderer repair: **PASS**. The target scoped-D2 file has the same blob as the earlier renderer commit `c9d3a9b4...`, whose documentation-build workflow succeeded; direct inspection confirms the cardinality and nested-mean rewrites are algebraically identical and the repaired surface contains neither raw `\\#\\{...\\}` cardinality nor `\\operatorname{...}` usage.

## 8. Lifecycle disposition

The active workplan remains **REVIEW_NO_PASS_REOPENED**.

A next review must use a new immutable target after R3-B1 repair and must receive current R3-B2 real-owner executable evidence. It must be a fresh assembled-candidate review, not a delta acceptance of this record.

No stakeholder ratification or canonical promotion is permitted from this R3 result.
