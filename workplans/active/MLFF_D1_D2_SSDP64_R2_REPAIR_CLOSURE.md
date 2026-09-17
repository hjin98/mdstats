---
kind: author-repair-closure
protocol_version: 6.4.0
status: READY_FOR_FRESH_INDEPENDENT_R2_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
r1_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R1.md
---

# MLFF D1/D2 SSDP 6.4 — R2 repair closure

## 1. Disposition

The R1 NO-PASS findings have been repaired in a new proposed candidate. This record is author-side closure evidence only; it is not an independent R2 review and does not promote D1/D2 authority.

The exact R2 semantic candidate consists of:

1. `workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R2_REPAIRED.md`;
2. `workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R2_REVIEW_CANDIDATE.md`;
3. `workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R2_FINAL.md` as the non-authoritative bounded trace;
4. the representation-only renderer correction already present in `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

Every earlier D1/D2 candidate or R2 draft on this branch is authoring history only and is explicitly superseded by the files above. They do not compose into the R2 candidate.

## 2. Accepted basis and PEM/HAS currentness

Remote `main` was rechecked immediately before R2 target preparation and remains exactly

```text
cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
```

so the accepted authority basis and R1 PEM/HAS basis have not advanced during repair. No validated same-branch PEM candidate overlay exists for this documentation formalization. The canonical `pem_basis` and `has` block already recorded in the active workplan therefore remains current for this R2 candidate.

This repair does not mutate `PROJECT-ENGINEERING-MEMORY.md`; it applies the accepted memory only as non-authoritative decision support.

## 3. R1 blocker closure matrix

### B1 — one-time weight normalization — CLOSED FOR R2 REVIEW

`D2.DEF.013` performs exactly one canonical binary64 family-weight normalization. `D2.DEF.014` consumes the stored weights directly and explicitly forbids a second normalization. The R1 37/2-witness binary64 counterexample is a mandatory R2 oracle: stored post-normalization sum `1.0000000000000002`, cumulative mass after index 36 `0.5000000000000006`, so `Q(0.5)` selects index 36.

### B2 — selector versus qualification tolerance — CLOSED FOR R2 REVIEW

`D2.DEF.020` owns independent qualification `C_m+1e-12>=0.95`. `D2.DEF.029` separately owns MVSEL2 Phase-A completion `C_m>=0.95-1e-14`. Their distinct dependencies and counterexample interval are retained.

### B3 — P1/P2/P3 numerical closure — CLOSED FOR R2 REVIEW

The repaired D2 kernel now formalizes or exact-imports: unbiased/Geyer autocorrelation, complete-frame block semantics, event merge/relation closure, the five-step component order, first-predecessor exact `M3`, condition-balanced `pi_eval`, current P2 structural policy, P3-common preparation, minimum-three-qualified admission, exact reducer funnel/success sufficiency/configured-ceiling rule, and continuous authenticated fidelity continuation.

### B4 — exact required-family catalog — CLOSED FOR R2 REVIEW

`D2.DEF.012` contains the exact universal structural family names and the conditional profile, raw pair-geometry, target-development-response, and foundation-residual family/applicability rules. Scratch does not acquire a foundation provider solely to populate selector families.

### B5 — REPAIR2 closure — CLOSED FOR R2 REVIEW

`D2.DEF.034-037` restore removal ordering/shortlist, exact replacement frontier, global objective, maximum 2 passes / 32 accepted swaps / shortlist 64, rank inheritance, future-rank displacement, lower-prefix immutability, post-repair reconstruction, and same-MVSEL2 continuation with no extra repair shell or alternate suffix.

### B6 — replay semantics — CLOSED FOR R2 REVIEW

D1/D2 now define true-reference replay as canonical default when labels exist, pseudo replay only by explicit opt-in bound to exact frozen foundation identity, mandatory independent true-reference replay monitor, replay geometry/source/label/exposure lineage, label-mode invariance of replay geometry membership, replay-first corpus order, and no hidden target duplication or training-head scalar.

### B7 — definition/source traceability — CLOSED FOR R2 REVIEW

The R2 final dependency trace uses only exact basis-pinned imports or formal object IDs; generic “accepted policy/provider” endpoints from R1 are removed. D2 now owns the correlation estimator/block definitions explicitly. The D1 role permission relation is typed and source-bound. The author audit also removed all artificial downward D1-to-D2 dependency edges so the authority graph follows D1 abstraction -> D2 concretization rather than forming D1/D2 cycles.

### B8 — parameter binding classes — CLOSED FOR R2 REVIEW

Both kernels distinguish fixed method coordinates from configurable families, generated defaults, and derived objects. In particular `0.95`, `0.01/0.99`, P5 `1:10:1`, common monitor `256`, and target-order numerical tolerances are fixed method/numerical coordinates; `K` and role thresholds are configurable families with generated defaults; candidate/evaluation/fidelity/seed values are configurable under the fixed structural domain.

### B9 — PEM/HAS interface — CLOSED FOR R2 REVIEW

The active workplan contains the canonical Protocol-6.4 `pem_basis` + `has` shape established by R1. Since accepted `main` has not advanced and no validated overlay exists, no HAS rebase is required before the R2 target.

## 4. Renderer and representation audit

The accepted scoped target-order D2 renderer repair remains representation-only:

- hard-gain cardinality uses set cardinality rather than raw `\#`;
- sparse-diversity nested arithmetic means use explicit finite sums/cardinalities rather than `\operatorname{mean}`.

Author-side scans of the final D1 and D2 R2 candidate files and the repaired scoped D2 paper find no remaining literal `\operatorname` macro or raw `\#` cardinality construct. No accepted numerical tolerance, ordering, tie, or decision predicate was changed by the renderer repair.

## 5. Definition-order/source-availability audit

Author-side closure checked the final pair in semantic order rather than file-order inference:

- D1 uses only exact D1 imports or previously declared D1 objects;
- D2 source/statistical primitives precede downstream numerical use;
- prefix is defined before `pi_eval` uses it;
- P3 common preparation is explicit before candidate normalization/restart uses it;
- family weights are defined before quantiles/scales/radii/coverage;
- qualification and selector coverage predicates are separate and defined before their consumers;
- obligation primitives precede selector/repair/qualification;
- reducer active/successful candidate sets are locally bound before sufficiency rules use them;
- replay label mode precedes replay lineage/exposure;
- monitor construction precedes checkpoint predicate use;
- D1 does not depend semantically on D2 concretizations in the final trace.

This is author-side evidence, not proof of completeness. Fresh R2 must independently reconstruct and falsify these claims.

## 6. No accepted-authority challenge or semantic change claim

The repair found no new Serious Challenge to accepted D1/D2. The R2 candidate is intended as a lossless Protocol-6.4 representation of accepted basis semantics, not a scientific/numerical method revision. Any R2 finding that the formalization strengthens, weakens, excludes, or changes accepted behavior is a blocker rather than an editorial discrepancy.

## 7. R2 review gate

A descendant handoff must bind the exact immutable commit containing this repair closure, the final D1/D2 files, final trace, and renderer repair. Fresh independent R2 must review the full assembled candidate against accepted basis rather than only checking B1-B9. PASS remains prerequisite to stakeholder ratification and canonical promotion.