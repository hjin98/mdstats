---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 12
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
parent_plan_revisions: [11]
reviewed_assembled_candidate: 029b274474c1adc3b4ea0021a82abf6a5de8c27d
reviewed_r11_implementation_commit: dd96ede2b24540977ee0bb280764907ea258e356
highest_affected_domain: D4
challenge_state: D4_NO_PASS_PERFORMANCE_AND_EVIDENCE_CLOSURE_REQUIRED
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
---

# MLFF `pi_train` MVSEL2-chain restoration — Revision 12 current-envelope closure repair

## 0. Independent re-review verdict and scope

Fresh independent review of assembled candidate `029b274474c1adc3b4ea0021a82abf6a5de8c27d` against Revision 11 and the accepted scoped D1/D2/D3 authority is **NO-PASS**.

The six Revision-11 correctness/ownership blockers are closed by the assembled candidate and SHALL NOT be reopened or reimplemented without new contradictory evidence:

1. REPAIR2 no longer suppresses zero-new-coverage proposals and v1 defective build identities are invalidated;
2. immutable target-order publication is locked create-or-verify and fails closed;
3. same-build `prepare` is single-flight while different build identities remain independent;
4. the frozen universal structural-family set reaches the target-order reference and missing required families fail closed;
5. the general D1/D2 papers delegate `pi_train` authority to the scoped papers and the targeted static closure batch is green;
6. the representative current campaign now supplies complete-path execution evidence and downstream commands consume the prepared definition without reconstructing target-order science.

The remaining NO-PASS is deliberately narrow. It is not a scientific or numerical challenge. It is a D4 current-envelope performance/resource/evidence closure problem exposed only after the D2-correct REPAIR2 semantics were restored.

## 1. Frozen authority and protected implementation topology

Preserve all Revision-11 invariants and the current chain:

```text
exact P_train
 -> TargetCoverageReference
 -> canonical obligations
 -> shared FEAS1/NEIGHBOR1
 -> MVIDX
 -> MVSEL2 configured prefix
 -> REPAIR2
 -> exact repaired-prefix reconstruction
 -> same MVSEL2 suffix to all P_train
 -> independent MVQUAL
 -> prepared-generation/CampaignStore adoption
```

Do not restore the deleted REPAIR2 shortcut, weaken `J`, reduce the family catalog, alter qualification, truncate the complete order, append a fallback suffix, add a second selector, add a second currentness/checkpoint database, or move scientific decisions into execution timing/worker completion order.

The accepted D3 architecture remains adequate for the first repair attempt: vectorized/native execution primitives are already delegated to D4 and do not require a new D3 component. Reopen D3 only if exact representative evidence demonstrates that the current component/restart topology itself cannot meet the current envelope after the avoidable D4 execution bottleneck is removed.

## 2. Blocking finding B12-1 — REPAIR2 is exact but materially serialized

### 2.1 Representative evidence

Revision-11 evidence used the current LTA campaign with exact `|P_train| = 33,984`, configured `N_max = 16,384`, 78 reference families, 739 canonical obligations and approximately 2.22 billion NEIGHBOR1 edges.

On the fresh representative run:

- target-order wall time: approximately **2 h 19 m**;
- REPAIR2 wall time: **6,156 s (about 1 h 42 m, 74% of target-order wall)**;
- MVSEL2 configured-prefix wall: 233 s;
- complete suffix wall: 164 s;
- native Phase-B preflight passed at 3.28x best speedup and selected width 16;
- REPAIR2 proposal execution nevertheless used only about **1.6 CPU cores** in the measured hot path.

The evidence localizes the avoidable serialization to `target_order/repair.py::_best_proposal` / `_proposal`: a Python-thread queue evaluates removal-dependent candidate proposals through Python dictionaries/loops and NumPy row calls. Once coverage is saturated, the D2-correct frontier can retain many zero-new-coverage candidates, so the per-removal proposal work scales over a large frontier while remaining GIL-bound.

This satisfies Revision-11's own trigger for a material performance defect: the accepted sparse/lazy/native execution closure is active, yet one required D2 stage dominates the assembled current-envelope critical path for an avoidable execution reason. Merely recording or routing that defect does not satisfy R11-H.

### 2.2 Owning code

Primary owner:

- `mdstats/training_data/target_order/repair.py`
  - `_build_frontier`
  - `_proposal`
  - `_best_proposal`
  - removal-dependent representative/diversity evaluation

Existing lower execution substrate that may be reused/extended if necessary:

- current MVIDX forward CSR arrays;
- existing selector/native row primitives;
- existing `_mvsel2_native` extension and its installed-package qualification route;
- existing deterministic work queue and `StageResourceScope`.

Do not create a separate REPAIR2 backend module, execution router, alternate repair algorithm, or compatibility mode.

### 2.3 Required repair strategy

Repair the demonstrated execution bottleneck at the existing REPAIR2 owner while preserving the D2 algorithm exactly.

1. **Keep the scientific state transition unchanged.** `_build_frontier` must retain hard-gain, canonical bottleneck, bottleneck coverage, and total-coverage filters exactly. `_proposal` semantics must retain hypothetical post-removal correlation balance, representative gain after removal, sparse diversity, UID, family non-regression, and `strictly_better(J_before, J_after)` exactly.

2. **Replace Python candidate-at-a-time hot loops with batch execution over existing arrays.** Prefer NumPy/compiled/native bulk operations over the current Python dictionaries and per-candidate thread tasks. Candidate IDs remain in canonical order and all FP64 reductions whose association is scientific remain in the accepted canonical order.

3. **Exploit state invariance only within one unchanged repair state.** Frontier-wide quantities that are independent of the contemplated removal may be computed once in canonical arrays and reused across the removal shortlist. Removal-dependent quantities may be batched, but every accepted swap invalidates/recomputes any cached quantity whose value depends on the old state.

4. **Use the current sparse representation directly.** Do not materialize dense candidate-by-witness matrices or introduce a second incidence representation. Work from MVIDX CSR/packed roots and the existing correlation-unit codes.

5. **Do not use Python threads as the numerical optimization if the work remains GIL-bound.** If NumPy batching alone is insufficient, extend the existing `_mvsel2_native` execution backend with the minimum exact FP64 REPAIR2 batch primitive needed to evaluate the same formulas. That is an extension of the existing execution primitive, not a new selector or numerical authority. The Python layer remains the owner of canonical frontier/reduction/admission semantics.

6. **Keep final reduction deterministic.** Completion order, worker count, batch boundaries and native width are execution-only. Objective-equivalent proposals still reduce by the accepted `(representative_loss, removed_rank, removed_UID, replacement_UID)` rule.

7. **Prefer one optimization that fixes fresh and restart cost.** Do not add a durable REPAIR2 cache/checkpoint merely to mask the current slow evaluator before its avoidable serialization is removed.

### 2.4 Required correctness falsification

The optimized implementation must preserve or strengthen all R11 owner tests, including the zero-new-coverage `U_rep` witness, no-strict-`J` control, worker invariance, post-repair reconstruction and complete suffix.

Add focused exact-equivalence coverage for the optimized proposal path:

- bounded adversarial states with hard deficit pending and satisfied;
- zero bottleneck/total-new-coverage frontiers;
- correlation-unit balance-only filtering;
- representative-gain ties within `1e-14`;
- diversity/UID terminal ties;
- removal shortlists of size 1 and 64;
- worker/batch-width variation and perturbed task completion order;
- at least one state where a swap is accepted and the next iteration proves all state-dependent batch quantities were invalidated.

Where an optimized/native batch kernel is introduced, compare its raw outputs bitwise or at the exact accepted tolerance against the existing scalar D2 formula/oracle on bounded fixtures before the scalar test oracle is allowed to disappear from test scope.

### 2.5 Representative acceptance evidence

Rerun the same current LTA substrate used by R11 so the comparison is paired rather than anecdotal. Record at least:

- exact input/configuration identities;
- full build identity, repair-plan digest, complete-order digest and MVQUAL digest;
- REPAIR2 wall by configured shell and total;
- proposal counts/frontier sizes/removal shortlist sizes;
- CPU utilization/effective execution width for the hot proposal stage;
- target-order and whole-`prepare` wall/RSS/I/O;
- native/vector execution disposition;
- fresh versus resumed exact identity.

The optimized execution must produce the same scientific products as the R11-correct baseline on identical input. A speedup is not acceptable if any repair trace, final order, qualification result or scientific digest changes.

No arbitrary new time SLA is introduced. Closure is cause-based: the known GIL-bound candidate-at-a-time serialization must no longer be the material reason REPAIR2 dominates current-envelope wall time. If representative profiling still shows the same serialization mechanism dominating the critical path, B12-1 remains open regardless of a small incidental timing improvement.

## 3. Blocking finding B12-2 — post-`N_max` restart repeats the entire expensive REPAIR2 stage

### 3.1 Observed behavior

The representative interrupted run was killed during suffix continuation at rank 18,432. The successor correctly restored the pure MVSEL2 checkpoint and later the suffix checkpoint, and it published the identical final scientific build. Exactness therefore passes.

However, before it can discover the suffix checkpoint identity, current `prepare` recomputes REPAIR2 and its repair-plan digest. The resumed representative run therefore spent **6,610 s** replaying REPAIR2 before continuing the suffix. The resumed whole prepare still took approximately **2 h**.

### 3.2 Repair ordering

Do not introduce another persistence boundary yet. First implement B12-1 and repeat the same post-`N_max` interruption/resume qualification.

If the optimized exact REPAIR2 replay is no longer a material restart cost, retain the simpler current topology and record that result.

If REPAIR2 replay remains a material current-envelope restart cost after the evaluator is no longer serial/GIL-bound, stop at the D3 boundary and raise a focused D3 Challenge. A reusable authenticated repair result would affect pre-adoption restart-state topology/identity and must not be invented as a D4 side cache. Any such D3 proposal must first show why existing build/checkpoint identities cannot be rewired more simply.

This ordering applies the project remove/rewire-first doctrine and avoids solving a computational defect by creating another durable authority.

## 4. Blocking finding B12-3 — representative RAM-budget evidence is unresolved

The R11 evidence reports an interrupted-run peak RSS of **36.4 GiB** while the campaign's resolved resource snapshot printed a **34.5 GiB RAM budget** after COVREF-PAR1 was enabled. The report itself leaves this as “the reviewer may wish to route to the resource owner.” That is not sufficient for a final resource acceptance claim.

This observation does **not** by itself prove an over-budget product defect: `ram_budget_bytes` is an execution/admission budget derived from currently available RAM, while process peak RSS includes memory already resident before a nested stage. Resolve the accounting instead of comparing incomparable numbers.

For the same representative run, record:

1. process RSS and `MemAvailable` immediately before entering TargetCoverageReference;
2. TargetCoverageReference peak process RSS and incremental RSS above that stage baseline;
3. its `StageResourceScope.ram_budget_bytes`;
4. deterministic-work-queue peak accounted in-flight/completed/reserved memory and backpressure events;
5. worker width/block size actually selected;
6. process RSS after the reference stage releases its temporary execution state.

Then classify:

- if stage incremental/accounted demand stays within the governing budget and no admission contract is exceeded, amend the evidence record to explain why total process peak RSS was not the budget quantity and close B12-3 without code change;
- if the stage actually exceeds its authorized budget, reduce existing COVREF parallel width/block admission using the current resource planner / `resolve_worker_count` / queue memory accounting. Do not add a second memory manager or silently raise the RAM fraction.

The serial/parallel TargetCoverageReference digest-equivalence proof must remain exact.

## 5. Blocking finding B12-4 — Protocol 6.3 PEM/HAS applicability closure is missing

Revision 8 retained PEM/Historical Applicability Set closure as an acceptance criterion, and Revision 11 explicitly required the implementer to read applicable project engineering memory. The R11 evidence record contains no session-local HAS or exact PEM-basis disposition.

For this branch, the accepted project base at review start is `e72090e21cec5311ce87745b03603f8783cd15a7` (`main`). The `PROJECT-ENGINEERING-MEMORY.md` carried by that accepted base has `coverage_state: PARTIAL`, is reconciled through `4eabe2ae9783c7ff92f3a1093c37502a01380812`, and has no high-impact unresolved notice. Its literal `candidate_overlay` text belongs to an older unrelated feature branch and is **not** an overlay for this MVSEL2 restoration candidate.

Record a bounded session-local HAS in the R12 evidence with at least these applicable accepted lessons:

- `SP-001`: owner-layer reduction/consolidation — applicable; supports avoiding new repair routers/checkpoint authorities;
- `SP-002`: fail-closed authenticated durable boundaries — applicable to artifact/build/checkpoint authentication;
- `SP-003`: immutable durable boundaries and exact restart/reuse — applicable to expensive preparation and the restart-cost decision;
- `SP-004`: real-owner/current-regime qualification — applicable and satisfied only by the representative LTA run plus real-owner tests;
- `FF-002`: continuation authority before authenticated restart boundary — applicable to MVSTATE/checkpoint/restart decisions;
- `FF-003`: duplicated destructive-storage authority — applicable to the fail-closed publication/cleanup boundary;
- `FF-005`: downstream commands reconstructing preparation-owned science — applicable to manual/automatic selection and confirmed absent by the no-rebuild evidence.

For each, record `applied`, `rejected`, or `review-required` plus one sentence of rationale. Do not mutate the canonical PEM merely to satisfy this paperwork. Promote new project memory only if the final accepted repair produces evidence that meets Protocol 6.3's learning threshold; the current one-off performance observation alone does not establish a new recurring failure family.

## 6. Findings that do not block this bounded re-review

The R11 evidence records 10 failures in a 98-file regression batch, all reproduced at the pre-R11 baseline with identical node IDs: eight assertions against retired revision-109 architecture material and two tests depending on an untracked `Na_LTA_relaxed.POSCAR`. They prevent a claim that the repository is globally green, but no evidence currently binds them to the R11 product changes. Preserve them as explicit baseline-equal, out-of-scope evidence rather than hiding them with skips/xfails. If R12 changes touch those owners, they become affected and must be reconciled.

No CI status is currently attached to assembled candidate `029b2744`; implementation-recorded local test results therefore remain evidence to be independently assessed, not CI-attested facts.

## 7. Required implementation evidence

Append to the R11 evidence record or create one bounded R12 D4 closure record containing:

- implementation commit(s) and exact changed-file list;
- B12-1 profile/repair trace from Python hot path to final optimized execution primitive;
- exact bounded scalar/optimized/native equivalence commands and results;
- full real-owner suite and affected regression results;
- paired representative LTA fresh-run metrics versus the R11 baseline;
- paired post-`N_max` kill/resume metrics after B12-1;
- B12-2 disposition: replay no longer material, or an explicit D3 Challenge before adding persistence;
- B12-3 RAM-budget accounting and disposition;
- B12-4 session-local HAS with the exact accepted/base PEM identity and applicability decisions;
- explicit confirmation that all six R11 correctness/ownership repairs remain intact;
- explicit confirmation that no fallback selector/router, alternate suffix, second currentness/checkpoint store, repair-side cache authority, or compatibility mode was introduced.

Production-scale GPU qualification remains deferred to the final release package on the stakeholder machine.

## 8. Re-review gate

A fresh independent assembled-candidate re-review may PASS only when:

1. every R11 correctness/ownership closure remains intact;
2. REPAIR2 exact semantics and scientific products are unchanged;
3. the measured GIL-bound candidate-at-a-time proposal bottleneck has been removed at its D4 owner and paired current-scale evidence demonstrates that the same mechanism no longer materially dominates REPAIR2;
4. fresh and post-`N_max` resumed execution produce identical repair/order/MVQUAL identities;
5. restart replay is either no longer a material cost after B12-1 or is escalated to D3 before any new durable repair state is introduced;
6. the COVREF-PAR1 RAM-budget question is quantitatively resolved and any real over-budget behavior is corrected using the existing resource owner;
7. the session-local PEM/HAS disposition is recorded against the exact accepted/base project state and accepted PEM publication;
8. required real-owner, native/reference, OOC/FD, publication/currentness, documentation/static, downstream no-rebuild and affected regression evidence remains applicable and green or preserved-with-reason;
9. no new competing scientific, persistence, currentness, cleanup, or compatibility owner exists.

Until all nine conditions hold, this workplan remains **ACTIVE / D4 NO-PASS** and must not be closed or archived.
