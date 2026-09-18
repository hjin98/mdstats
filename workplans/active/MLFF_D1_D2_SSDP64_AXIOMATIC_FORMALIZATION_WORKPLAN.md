---
kind: abstraction-concretization-change-plan
protocol_version: 6.4.0
status: REVIEW_NO_PASS_REOPENED
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
highest_domain: D1
---

# MLFF D1/D2 SSDP 6.4 axiomatic formalization workplan

## Background and terminology

This cycle upgrades the current machine-learned force-field (MLFF) D1/D2 authority representation from the accepted Protocol-6.3 narrative contract style to the Protocol-6.4 formal-first style while preserving accepted scientific and numerical meaning unless an independently reviewed semantic defect is found.

An **axiom** here is a primitive governing proposition accepted by the D1 owner for the bounded MLFF method. A **definition** introduces an object without asserting empirical truth. A **derived invariant** follows from definitions and axioms. A **parameter family** distinguishes a semantic family from a concrete parameter binding and from a default. A **semantic dependency edge** `A USES_DEFINITION -> B` means that materially changing definition `B` can change the denotation, domain, validity, or interpretation of `A`.

This work does not create a universal ontology, a fifth authority layer, or a machine checker. The dependency record is a bounded review/impact aid under SSDP 6.4.

## 1. Outcome and authority

- Protected outcome: preserve the accepted mdstats MLFF scientific experiment and numerical method while removing definition-order ambiguity, hidden assumptions, overloaded prose, and renderer-invalid mathematical notation.
- Highest potentially affected domain: D1 scientific formulation.
- Current owners: `docs/methods/mlff_scientific_method.md`, `docs/methods/mlff_target_training_order_scientific_method.md`, `docs/methods/mlff_numerical_algorithmic_method.md`, and `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.
- Accepted basis: repository `hjin98/mdstats` at `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`.
- Protocol owner: SSDP 6.4.0, accepted recovery `74bc572ef516cae417437a2027eeff52a2e25c15`.
- Proposed authority state: D1/D2 candidate only until fresh independent D1/D2 review passes and the stakeholder ratifies the exact candidate. No file in this workplan may self-promote to accepted-current authority.

## 2. Governing contract

### Invariants

1. Preserve every accepted P1/P2/P3 scientific and numerical invariant not explicitly reopened by this workplan.
2. Preserve the scoped target-order authority split: the general D1/D2 papers delegate `TargetTrainingOrder` / `pi_train` construction and qualification to the scoped target-order D1/D2 papers.
3. Preserve the post-selection restoration and configurable foundation role-threshold semantics ratified on 2026-09-14/15.
4. Preserve MVSEL2/REPAIR2/MVQUAL scientific and numerical meaning, including exact `P_train`, one complete nested master order, canonical obligations, independent qualification, and execution invariance.
5. Definitions do not establish empirical adequacy, convergence, optimality, or authority. Claims and warrant remain separate.
6. Parameter families distinguish family, instance, and default, especially `tau_cv`, `theta_cv`, `tau_prod`, target-size ladder values, tolerances, fold count, monitor size, Huber thresholds, and selector thresholds.
7. Direct `USES_DEFINITION` edges are recorded only for material semantic prerequisites; transitive closure is derived, not hand-duplicated.
8. Every mathematical symbol used in a normative formula is defined before or at first substantive use with domain, units, and failure/undefined conditions where material.
9. Renderer compatibility is part of representation quality. Current MLFF authority text must not use unsupported `\operatorname{...}` or raw `\#` cardinality notation in math where the current renderer rejects them.

### Cycle-scoped decisions

- Formal object identifiers use stable `D1.*` and `D2.*` IDs local to the candidate authority family.
- Axioms are grouped by semantic owner rather than mirroring implementation stages.
- The dependency trace is human-readable Markdown, not a new runtime artifact.
- Renderer-safe cardinality uses `|A|`; arithmetic means are written as explicit sums divided by cardinality.

### Delegated space

D3/D4 remain free to choose persistence, sparse layout, queues, threading, GPU/CPU realization, caching, restart encoding, and equivalent execution strategies provided D1/D2 semantics are unchanged.

### Non-goals

- No redesign of target-size selection, replay, checkpointing, cross-validation, or training objective.
- No new threshold, tolerance, family, evidence role, or target-size candidate.
- No reinterpretation of historical evidence under new thresholds.
- No global cleanup of unrelated repository `\operatorname{...}` usage outside the MLFF D1/D2 authority family.
- No GPU qualification in this cycle; existing project policy defers GPU qualification to final release qualification.

## 3. Adequacy and affected surface

The candidate must preserve and formalize the following semantic chain:

```text
source/frame/label conventions
 -> protected statistical relations and evidence roles
 -> U_size
 -> exact P_train + M3 split
 -> scoped target-order D1
 -> scoped target-order D2
 -> exact T_N prefixes + MVQUAL admission
 -> P3 training/evaluation/reducer experiment
 -> operator-frozen post-selection design
 -> foundation/scratch post-selection method
 -> common monitor + CV role policy
 -> fresh production role policy
 -> downstream qualification
```

Material descendants to inspect after candidate stabilization include current architecture manual sections and current MLFF D4 specifications that cite formulas or semantic definitions changed in wording. Representation-only wording changes do not make unaffected implementation evidence stale.

## 4. Evidence and falsification

Reverse-semantic verification questions:

- Can every normative MLFF D1/D2 object be reconstructed without hidden chat or historical workplans?
- Does each scoped D2 definition concretize exactly one D1 owner without strengthening or weakening it?
- Does changing a parameter default leave the family semantics unchanged where the current authority says it should?
- Can every direct material prerequisite be followed by `USES_DEFINITION` without circular claim warrant?
- Are all formulas well-defined over their stated domains and dimensionally interpretable?
- Do renderer-safe rewrites produce the identical mathematical quantity?

Required falsification includes:

1. search the candidate MLFF D1/D2 family for unsupported `\operatorname` and raw `\#` math syntax;
2. compare every existing accepted equation and decision predicate against the candidate for semantic equality;
3. challenge each definition for undefined empty-set, zero-denominator, missing-provider, rank-deficient, or non-finite regimes;
4. challenge each parameterized family for hidden default-as-invariant coupling;
5. challenge D1/D2 ownership boundaries for duplicate authority;
6. inspect downstream D3/D4 references for wording that would become semantically false under the formalized definitions;
7. verify no historical artifact is promoted into current authority merely because it supplied reconstruction evidence.

## 5. Concretization sequence

### A. D1 formalization

Create a complete candidate D1 authority representation in dependency order:

1. foundational configuration/label/evidence objects;
2. protected relations and evidence roles;
3. target-size experiment objects;
4. target-order scientific axioms and definitions;
5. post-selection adaptation, monitor, CV, production, and qualification objects;
6. validity, uncertainty, falsification, and D1->D2 handoff.

### B. D2 formalization

Create a complete candidate D2 representation in dependency order:

1. numeric domains/precision/order conventions;
2. exact split/order/prefix objects;
3. target-order metrics, coverage, obligations, selector, repair, and qualification operators;
4. atomic-reference fit and identifiability;
5. objective/loss definitions;
6. P3 optimizer/evaluation/reducer algorithms;
7. P5 exposure/monitor/CV/checkpoint algorithms;
8. error/conditioning/restart/equivalence semantics;
9. D2->D3 handoff.

### C. Semantic dependency trace

Record direct `USES_DEFINITION` edges for every material D1/D2 object whose prerequisite meaning can change its denotation or validity. The trace declares its bounded scope as the four MLFF method papers and remains non-authoritative.

### D. Rendering repair

Replace renderer-invalid notation in the scoped D2 formulae with mathematically equivalent supported notation. Search all four MLFF D1/D2 current/candidate files for the same classes of defect.

### E. Independent review and ratification

A fresh reviewer must compare the exact candidate against accepted `cb07d683...`, the accepted historical D1/D2 reconstruction/promotions, and current implementation/architecture evidence. PASS is required before stakeholder ratification and canonical promotion.

## 6. Reopen / simplification / human triggers

Reopen D1 if formalization reveals a scientific object whose accepted meaning is genuinely ambiguous or contradictory. Reopen D2 if two materially different numerical algorithms satisfy the current prose but yield different accepted outputs. Do not repair either by adding implementation wrappers.

Human ratification is required for any semantic change, including newly explicit assumptions if they exclude a regime previously admissible, changed threshold/default ownership, changed evidence-role interpretation, or changed selector/qualification meaning.

## 7. Impact and history

If the candidate is accepted, record a concise semantic-evolution entry: Protocol-6.4 formalization made prior implicit dependencies and parameter-family semantics explicit without changing accepted scientific/numerical behavior, plus any independently reviewed semantic corrections if discovered.

Unaffected historical reviews, tests, and observations remain valid when their governed claim and parameter regime are unchanged. Renderer-only changes do not stale numerical evidence.

## 8. Acceptance and handoff

Acceptance requires all of the following:

- complete D1 and D2 candidate documents exist and are internally definition-closed for their declared competent reader;
- direct material `USES_DEFINITION` edges are recoverable and acyclic after composite recursive groups are condensed;
- no material first-use definition gap remains;
- family/instance/default semantics are explicit for material parameterized objects;
- formulas are renderer-safe in the four MLFF authority files;
- no accepted 6.3 invariant is lost or silently strengthened;
- fresh independent D1/D2 review returns PASS;
- stakeholder ratifies the exact reviewed candidate;
- canonical papers are promoted/reconciled only after that ratification;
- affected D3/D4 documentation is reconciled for terminology/locators without inventing a new software mechanism.

## 9. Independent Review R1 — NO-PASS and reopen instructions

Independent review of immutable candidate `c9d3a9b4d8a226a7298e4e6088d3db19e98c1ea2` is recorded in `MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R1.md` and returned **NO-PASS**. The accepted D1/D2 authority is not challenged; repair the proposed Protocol-6.4 representation only.

The renderer-only formula correction is accepted and should remain unchanged unless a new representation defect is found.

### R1 blockers that must all close before R2

1. **Weighted quantile:** remove the second binary64 normalization in candidate `D2.DEF.005`; quantiles consume the once-normalized stored weights from `D2.DEF.004`. Add the 37-witness/2-witness adversarial `Q(0.5)` oracle from R1.
2. **Selector vs qualification coverage predicates:** bind MVSEL2 Phase-A completion explicitly to `C_m < 0.95 - 1e-14`; retain independent MVQUAL coverage at `C_m + 1e-12 >= 0.95`; represent them as distinct numerical predicates and dependencies.
3. **Complete P1/P2/P3 numerical closure:** formalize or exact-import the current five-step component ordering for `M3`, condition-balanced `pi_eval`, P2 structural policy, minimum-three-qualified admission, exact reducer funnel/success sufficiency/configured-ceiling rule, autocorrelation truncation, complete-frame blocks, and protected-event merge semantics.
4. **Required-family catalog:** formalize the current universal/profile/pair-response/foundation-residual family catalog and extent/applicability rules. Generic `m` is not enough.
5. **REPAIR2:** restore exact replacement-frontier ranking, 2-pass/32-swap limits, rank-inheritance/future-displacement semantics, and final-shell/no-extra-repair continuation.
6. **Replay:** add D1/D2 true-reference default, explicit pseudo-label opt-in, foundation identity binding, separate true-reference replay-monitor lineage, geometry/label-lineage separation, and geometry-membership invariance under label-mode changes.
7. **Definition-source trace:** replace generic/dangling prerequisite labels by exact source/owner references or first-class definitions; create the missing D2 correlation-truncation owner; type/source `Perm(role)`; add every missing material node/edge; re-run reverse-impact closure.
8. **Parameter ledger:** split fixed method coordinates from configurable families/defaults/derived values. In particular do not represent target-order `0.95` or extent `0.01/0.99` as ordinary configurable defaults; preserve current ladder structural constraints.
9. **PEM/HAS:** add the canonical basis/applicability interface below and reconcile any newer validated overlay before cutting R2.

```yaml
pem_basis:
  accepted_project_state: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
  accepted_pem: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: formalization must preserve one canonical semantic owner instead of creating duplicated authority
  - id: SP-002
    disposition: APPLICABLE
    reason: fail-closed exact identity and state boundaries are central to D1/D2 definitions
  - id: SP-003
    disposition: APPLICABLE
    reason: immutable/content-addressed candidate and continuation identities are material
  - id: SP-004
    disposition: APPLICABLE
    reason: real-owner/current-implementation comparison is needed to falsify numerical equivalence
  - id: FF-001
    disposition: APPLICABLE
    reason: foundation checkpoint/head and realized-model identity are material to E0 and P5 authority
  - id: FF-002
    disposition: APPLICABLE
    reason: authenticated continuation/restart authority is formalized by this candidate
  - id: FF-003
    disposition: NOT_APPLICABLE
    reason: destructive storage routing is outside this D1/D2 documentation formalization
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: GPU admission/cancellation/residency policy is outside the semantic candidate
  - id: FF-005
    disposition: APPLICABLE
    reason: formal ownership must prevent downstream reconstruction of preparation-owned scientific state
```

### R2 gate

After repair, cut a **new immutable semantic target**. Do not revise the meaning of `c9d3a9b4...` in place. A fresh independent D1/D2 review must re-run the full review, not only the nine repaired findings, because definition closure and dependency edges will materially change.

## 10. Independent Review R3 — NO-PASS and R4 repair gate

Independent review of immutable R3 target `045cb5a052fdb83b6c6cd561142b24fdf5d023b5` is recorded in `MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R3.md` and returned **NO-PASS** without a Serious Challenge to accepted D1/D2.

R3 independently closed all four R2 semantic blockers and accepted the direct D4 weighted-quantile source repair numerically. Two blockers remain for R4:

1. **R3-B1 — direct dependency completeness.** Replace the R3 trace with one R4 trace after a complete object-by-object forward source-availability and reverse-impact pass. At minimum close the missing typed-failure edges `D2.DEF.045`, `D2.DEF.047`, `D2.DEF.049`, `D2.DEF.053`, and `D2.DEF.058`; challenge selector/oracle, repair, qualification, reducer, currentness, continuation and equivalence rows for the same defect. Do not change accepted D1/D2 semantics or reintroduce free-text endpoints.
2. **R3-B2 — D4 executable acceptance.** Execute the focused FP64 regression and current real-owner target-order suite on the repaired descendant. The minimum commands are `pytest -q tests/test_mlff_target_order_weighted_quantiles_fp64.py` and `pytest -q tests/test_mlff_target_order_real_owner.py`. Expand to the affected target-order suite if those commands expose a wider affected surface. Record the exact tested commit and environment. GPU qualification is not part of this CPU numerical repair.

R4 may reuse the exact R3 D1/D2 kernel blobs if the repair audit finds no semantic-kernel defect. The old immutable R3 target remains historical evidence and must not be rewritten. A temporary validation-only CI harness is permitted only as evidence machinery: it must not become product/runtime authority and must be removed before the new immutable R4 semantic target is bound.

### R4 gate

Cut a new immutable target only after R3-B1 is structurally closed and R3-B2 has current real-owner executable evidence. Fresh R4 review must inspect the complete assembled candidate against accepted `cb07d683...`; it may not inherit R3 author closure. PASS remains prerequisite to stakeholder ratification and canonical promotion.


## 11. R4 author closure and independent-review handoff state

R4 author repair is complete for the two blockers in Independent Review R3. The R4 direct dependency trace is structurally closed author-side, and current real-owner D4 evidence exists on the unchanged executable owner/test blobs. Primary passing evidence is run `35300235175` at `dbe6c552b216d583caf9230d2c1e0879b68f8c3e`; confirmatory passing evidence is run `35300268107` at `17af93877ba312600ab1bf7a2f1f2990c9c2ef00`. Both required target-order commands passed in the supported CPU MLFF environment.

The temporary R4 validation workflow has been removed. The next clean commit containing the unchanged D1/D2 kernels, R4 trace, D4 repair/tests, workplan and R4 repair closure may be bound directly as the immutable R4 candidate by a descendant handoff. Do not add a no-op marker merely to obtain another SHA.

The active workplan remains review-open until fresh independent R4 Review returns PASS. Author repair closure does not ratify or promote the candidate. GPU qualification remains deferred and is not an R4 gate.


## 12. Independent Review R4 — NO-PASS and R5 repair gate

Independent review of immutable R4 target `86fa8acec3cfc84584bfbd380163545d80de7a27` is recorded in
`MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R4.md` and returned **NO-PASS** without a Serious Challenge to accepted D1/D2.

R4 closes the D4 executable-evidence blocker: both the focused FP64 regression and full real-owner target-order suite passed in the supported CPU MLFF/test environment, and the tested owner/test blobs are identical to the immutable R4 target.

One blocker remains:

- **R4-B1 — direct dependency trace completeness.** The trace is structurally complete but semantically incomplete under the workplan's direct-edge definition. Definitive witness: `D2.DEF.019` directly concretizes the D1 covered-mass object `D1.DEF.015`, but the trace omits `D2.DEF.019 -> D1.DEF.015`. Additional witnesses include omitted configured-prefix owners from `D1.DEF.023`, omitted role-permission owner `D1.DEF.006` from `D1.DEF.024`, and omitted D1 fold/production-domain owners from `D2.DEF.041`.

### R5 gate

Repair the derived trace at its real representation owner, perform a fresh semantic directness/reverse-impact pass over all 106 objects, and cut a new immutable target. Do not change the accepted/proposed D1/D2 kernels or D4 weighted-quantile implementation merely to close this representation defect unless the audit independently discovers a semantic defect.

Current R4 D4 evidence may remain applicable to an R5 documentation-only descendant only if the D4 owner and both affected test blobs remain identical and no executable dependency/environment assumption changes. GPU qualification remains outside this gate.


## 13. R5 author repair closure and fresh-review gate

R5 repairs the sole blocker from Independent Review R4 without changing either proposed semantic kernel or any executable owner.

The R5 trace replaces the R4 trace after a complete semantic directness/reverse-impact pass over all 106 formal objects. The repair adds fourteen direct edges across nine rows, including the four R4 review witness classes and additional same-class omissions found during the full pass. Mechanical validation after those semantic decisions reports one row per formal subject, no unresolved prerequisite and no object-level cycle. A formal-ID mention cross-check leaves only the deliberate `D2.DEF.029` statement that its Phase-A predicate is distinct from `D2.DEF.020`; that mention is intentionally not a dependency.

The D1 kernel, D2 kernel, weighted-quantile D4 owner, focused FP64 regression and full real-owner test suite are unchanged from R4. Therefore passing CPU evidence runs `35300235175` and `35300268107` remain applicable provided blob identity is rechecked at the new immutable target. No functional rerun is required for this documentation-only trace repair unless an executable blob or environment contract changes.

R5 must cut a new immutable target containing the R5 trace, this workplan state and an R5 repair-closure record. A descendant handoff must request a fresh full assembled-candidate Review; author-side closure is not PASS, ratification or promotion. GPU qualification remains deferred and outside this gate.


## 14. Independent Review R5 — NO-PASS and R6 repair gate

Independent review of immutable R5 target `058b856df249bd28212ba70e459babd1f29a6c42` is recorded in
`MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R5.md` and returned **NO-PASS** without a Serious Challenge to accepted D1/D2.

R5 preserves the substantive D1/D2 kernels, renderer repair and current D4 executable acceptance. The remaining blocker is dependency-trace semantic completeness.

Definitive missed direct-owner edges include:

- `D1.AX.004 -> D1.DEF.012` for exact `T_N` controlled-variable meaning;
- `D1.AX.004 -> D1.DEF.010` for the evaluation ladder held candidate-independent;
- `D1.DEF.013 -> D1.DEF.010` for excluded `M1/M2` selector evidence;
- `D1.DEF.020 -> D1.DEF.006` for authorized E0 fit-role permissions.

The same-class audit also requires challenging/repairing direct local-owner edges for `D1.AX.003`, `D1.AX.008`, `D1.AX.010`, `D2.DEF.030`, `D2.DEF.031` and `D2.DEF.041` as specified in the R5 review record.

### R6 gate

Repair the derived trace only unless the new semantic audit independently finds a kernel defect. Re-run all 106 objects with explicit local-symbol/local-domain owner resolution plus reverse impact; structural row/endpoint/acyclicity checks remain necessary but are not sufficient.

Cut a new immutable target after the repaired trace. Existing passing CPU D4 evidence may remain applicable only if the weighted-quantile owner, focused regression and real-owner suite blobs remain unchanged and no environment contract changes. GPU qualification remains outside this gate.


## 15. R6 author repair closure and fresh-review gate

R6 repairs the sole blocker from Independent Review R5 at the derived dependency
representation owner. Neither proposed D1/D2 semantic kernel nor any executable
D4 owner/test is changed.

The R6 pass resolves both explicit formal IDs and local mathematical/semantic
symbols to their formal owners across all 106 objects. It adds seventeen direct
edges across thirteen subjects: every witness named by R5 plus seven additional
same-class dependencies found during the complete pass. The audit separately
records intentionally transitive/non-dependency cases so the graph is not
densified merely to avoid future review.

The resulting graph has one row per formal subject, exact endpoint/source
closure, no object-level cycle and no D1->D2 authority inversion. The explicit
formal-ID scan leaves only the deliberate `D2.DEF.029` statement that its
selector predicate is distinct from `D2.DEF.020`.

The D1 kernel, D2 kernel, weighted-quantile D4 owner, focused FP64 regression and
full real-owner test suite remain unchanged. Passing CPU runs `35300235175`
and `35300268107` therefore remain applicable to a documentation-only R6
descendant if exact blob identity is reverified at the immutable target.

Cut a new immutable R6 target containing the R6 trace, this workplan state and
the R6 repair-closure record. A descendant handoff must request a fresh complete
assembled-candidate Review. Author repair closure is not PASS, stakeholder
ratification, promotion or merge. GPU qualification remains deferred and
outside this gate.


## 16. Independent Review R6 — NO-PASS and R7 repair gate

Independent review of immutable R6 target
`12af89b860511277246e853a1e7ba22b86cec39f` is recorded in
`MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R6.md` and returned **NO-PASS** without
a Serious Challenge to accepted D1/D2.

The D1/D2 kernels, renderer repair and D4 executable evidence remain acceptable.
Two direct dependency-trace blockers remain:

- `D2.DEF.062 -> D2.DEF.015`: robust-scale non-finite input is an explicit
  fail-preparation rule and directly contributes the typed “non-finite fitted
  statistics” failure member;
- `D1.DEF.010 -> D1.DEF.006`: the evaluation ladder explicitly classifies
  `M_i` as P3 model-selection and not held-out/checkpoint-monitor evidence,
  whose local role/permission owner is D1.DEF.006.

### R7 gate

Repair the derived trace only unless the renewed audit discovers an actual
kernel defect. Re-run all 106 objects with focused role-owner and typed-failure
sweeps in addition to the general local-symbol/directness audit. Preserve
intentional transitive/non-dependency cases rather than dense-connecting the
graph.

Cut a new immutable target after exact structural and semantic checks. Existing
CPU D4 evidence may remain applicable only if the weighted-quantile owner,
focused regression and real-owner suite blobs remain unchanged and the
environment contract is unaffected. GPU qualification remains outside this
gate.
