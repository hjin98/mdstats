---
kind: implementation-workplan
workplan_id: DOC-MVSEL2
plan_revision: 4
status: READY_FOR_IMPLEMENTATION
protocol_version: 2.0.1
analysis_base_ref: main
analysis_base_commit: 1918f940debecade786b9b89c13c1bca3d787c89
assumption_paths:
  - mdstats/training_data/target_multi_view_selector.py
  - mdstats/training_data/target_multi_view_selection_state.py
  - mdstats/training_data/target_multi_view_repair.py
  - mdstats/training_data/target_coverage_sparse_index.py
  - mdstats/training_data/campaign_cli.py
  - tests/test_mlff_mvkernel1.py
  - docs/arch_manuals/mlff_training_data/50_target_multiview.md
  - docs/arch_manuals/mlff_training_data/60_execution_performance.md
  - docs/specs/training_data/mlff_mvkernel1_sparse_vector_kernels_spec.md
  - benchmarks/mlff_mvsel_production_density_2026-08-18.json
architecture_refs:
  - docs/arch_manuals/mlff_training_data_architecture.md
  - docs/arch_manuals/mlff_training_data/50_target_multiview.md
  - docs/arch_manuals/mlff_training_data/60_execution_performance.md
  - docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md
spec_refs:
  - docs/specs/training_data/mlff_mvkernel1_sparse_vector_kernels_spec.md
expected_change_paths:
  - mdstats/training_data/target_multi_view_selector_v2.py
  - mdstats/training_data/target_multi_view_selection_state_v2.py
  - mdstats/training_data/target_multi_view_repair_v2.py
  - mdstats/training_data/target_coverage_sparse_index.py
  - mdstats/training_data/campaign_cli.py
  - mdstats/training_data/__init__.py
  - tests/
  - benchmarks/
  - docs/specs/training_data/
  - docs/arch_manuals/mlff_training_data/
  - docs/arch_manuals/mlff_training_data_architecture.md
  - docs/history/mlff/
  - CHANGELOG.md
  - mdstats/_version.py
  - pyproject.toml
default_gate_approval: AUTO
---

# TARGET-DATA2C MVSEL2 Forward/Lazy Selector Implementation Workplan

## 1. Objective and governance

Replace the computationally non-viable eager inverse-scatter selector/repair execution path with a new exact forward-state chain **MVSEL2 + MVSTATE2 + REPAIR2**, while preserving current scientific selection and repair semantics.

This document is the implementation authority for the transition. The DOC-GOV1 migration is already merged into `main`; normative architecture/specifications describe accepted current behavior only. Proposed MVSEL2 behavior and developer gates remain here until G8 accepts and migrates the implementation. Gate/status chronology must not be reintroduced into architecture manuals.

## 2. Current diagnosis

The production graph is approximately 36,408 candidates, 165 families, and 9,505,021,522 candidate-witness edges, with target sizes through 16,384. `mdstats 0.20.241a0` reduced MVSEL1 initialization plus rank 0 from about 320 s to 106 s and rank-0 update from about 240 s to 49.7 s, but later ranks still project to 100+ hour execution.

MVSEL1 maintains complete per-candidate marginal arrays. Selecting candidate `s` changes witness state and eagerly propagates decrements through witness->candidate inverse adjacency, with mutation work approximately

\[
\sum_{w\in N(s)} \deg_{inverse}(w),
\]

which can approach `O(E)` work per rank and `O(K E)` over target size `K`.

MVSTATE-REUSE1 persists this eager candidate-level state, and REPAIR1 restores/reconstructs it and calls MVSEL1 select/deselect mutation. Therefore **REPAIR2 is mandatory before MVMIGRATE2**; production MVSEL2 cannot remain coupled to REPAIR1 without recreating the same inverse work or synthesizing obsolete eager state.

## 3. Frozen scientific semantics

MVSEL2 changes execution/state representation, not policy.

### 3.1 Global policy

- Target sizes remain `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`.
- Coverage threshold remains `tau = 0.95`.
- Default absolute gain tolerance remains `epsilon = 1e-14`; caller-supplied values remain governed by the existing MVSEL policy contract.
- Scientific scoring is FP64.
- Canonical family/candidate/CSR witness order, correlation-unit codes, obligation incidence, and frame UIDs come from authenticated current authorities.
- Stable frame UID is the terminal deterministic tie-break.

### 3.2 Best-relative floating contender rule

For a floating criterion with best value `G*`, a candidate remains in the contender set iff

\[
G \ge G^* - \epsilon.
\]

This is a best-relative rule, not a transitive equivalence relation; do not replace it with pairwise `isclose` classes.

### 3.3 Phase and bottleneck family

`hard_pending` means at least one required obligation is unsatisfied. `coverage_pending` means at least one required family has `C_f < tau - epsilon`. Phase is `hard_coverage` if either is true, otherwise `representative_fill`.

If `hard_pending`, restrict candidates first to the exact maximum integer hard-gain class.

During `hard_coverage`, compute `r_f=C_f/tau` in canonical family order. Let `r_min=min(r_f)`. The bottleneck family is the **first canonical family** satisfying `r_f <= r_min + epsilon`. Do not replace this with a post-selection max-min objective.

### 3.4 Lexicographic decision order

Phase A, after optional maximum hard-gain restriction:

1. bottleneck-family coverage marginal;
2. total coverage marginal;
3. least-selected candidate correlation unit;
4. total harmonic representative marginal;
5. sparse diversity;
6. stable UID.

Phase B:

1. total harmonic representative marginal;
2. least-selected candidate correlation unit;
3. sparse diversity;
4. stable UID.

Every floating filter uses the frozen `best - epsilon` rule.

### 3.5 Forward objectives

For family `f`, witness weight `omega_fw`, multiplicity `m_fw`, and candidate row `N_f(c)`:

\[
G_{cov,f}(c,S)=\sum_{w\in N_f(c)}\omega_{fw}\,1[m_{fw}=0],
\]

and total coverage marginal is summed in canonical family order.

Representative utility is

\[
U_{rep}(S)=\sum_f\sum_w\omega_{fw}H_{m_{fw}},
\]

with add marginal

\[
G_{rep}(c,S)=\sum_f\sum_{w\in N_f(c)}\frac{\omega_{fw}}{m_{fw}+1}.
\]

Because multiplicity only increases during MVSEL selection, previously exact representative scores are monotone upper bounds, subject to conservative FP64 rounding.

Sparse diversity remains the current unweighted late tie-break: for each non-empty family row, FP64 mean of `1/(1+m)` over row witnesses, then FP64 mean over non-empty families in canonical order; all-empty returns zero.

## 4. Frozen architecture

### 4.1 Separate v2 modules

Do not silently change MVSEL1 identity. Prefer:

```text
mdstats/training_data/target_multi_view_selector_v2.py
mdstats/training_data/target_multi_view_selection_state_v2.py
mdstats/training_data/target_multi_view_repair_v2.py
```

MVSEL1/MVSTATE-REUSE1/REPAIR1 remain legacy authorities and bounded qualification oracles.

### 4.2 Forward mutable state

Per family: witness weights, witness multiplicity, family coverage mass, and candidate->witness forward CSR. Domain state: selected/availability state, obligation counts/satisfaction, compact hard-obligation incidence/gain state, correlation-unit counts, and cumulative representative utility as needed.

`covered` is derived from `multiplicity > 0` unless retained only as a validated execution cache after measurement.

Selecting/deselecting candidate `c` mutates only its forward rows plus obligation/correlation incidence:

\[
O(|N(c)| + obligation\_incidence(c)).
\]

No v2 mutation maintains complete candidate marginal arrays or touches witness->candidate inverse adjacency.

### 4.3 MVIDX1 runtime view

Keep MVIDX1 on disk for current legacy consumers. MVSEL2/REPAIR2 must consume a forward-only runtime view that does not materialize, touch, or page-fault inverse arrays for their own operation. Exposing that view must not change MVIDX1 scientific graph identity. MVIDX2/inverse removal is a separate later workplan.

## 5. Exact Phase A execution

At each `hard_coverage` rank:

1. restrict to max hard-gain class if required;
2. identify exact bottleneck family;
3. scan eligible candidate rows for that family and compute exact coverage marginals;
4. form the complete `best - epsilon` contender set;
5. compute total coverage only for contenders;
6. apply correlation-unit balance;
7. compute representative marginal only for remaining contenders;
8. compute diversity only when still required;
9. apply UID.

Candidate evaluation may be chunked or parallelized across candidates with bounded memory; canonical candidate results are reduced deterministically.

## 6. Certified lazy Phase B

At the Phase-A -> Phase-B transition, run one deterministic exact **Phase-B rebase** over all available candidates and seed one global lazy queue with current exact representative marginals.

A stale score is valid only as a conservative upper bound. If ordinary FP64 evaluation could undercut the mathematical bound, outward-round the stored value (for example with `nextafter(+inf)`) or use an equivalently proven conservative representation. Qualification builds should assert monotone non-increase under the selected bound scheme.

Let `G*` be the best current exact representative score. A stale candidate with upper bound `U(c)` cannot enter the contender set once

\[
U(c) < G^* - \epsilon.
\]

Refresh largest stale bounds until every remaining stale bound satisfies that exclusion; then apply correlation balance, diversity, and UID to the complete exact representative contender set.

Queue entries identify candidate, upper bound, and generation/epoch. Duplicate stale entries and deterministic rebuilds are execution-only. Prefer packed/array-backed storage if Python object overhead becomes material.

## 7. Exact fallback policy

Full-forward candidate-pool rescore is the correctness oracle and bounded emergency fallback, not normal production execution.

- It must select the identical MVSEL2 winner.
- G4 fails if fallback exceeds **1% of Phase-B accepted ranks or more than 3 consecutive accepted ranks**.
- Crossing that limit is `DESIGN_REVISION_REQUIRED`.
- No stochastic greedy, random candidate subsampling, approximate neighborhoods, or hardware-dependent scientific ordering.

## 8. REPAIR2

Preserve REPAIR1 scientific semantics: active-shell-only repair, immutable lower prefixes, exact unique-coverage/hard-safety removal, exact deficit-frontier replacement, strict no-coverage regression, current objective/tolerance/tie hierarchy, replacement rank inheritance, future displacement semantics, bounded passes/swaps/shortlist, and deterministic swap trace.

REPAIR2 consumes MVSTATE2 witness/obligation/correlation state directly. Removal and hypothetical replacement scores are computed forward on demand over bounded shells/frontiers. Select/deselect mutation touches only affected forward rows plus obligation/correlation state. REPAIR2 must not reconstruct MVSEL1 eager gain arrays or call MVSEL1 inverse mutation in production.

## 9. MVSTATE2 persistence

MVSTATE2 is authenticated reconstructible checkpoint state, not independent scientific authority.

Persist only exact continuation state: selected-prefix identity/cardinality, witness multiplicity, family coverage mass under one validated rule, obligation counts/satisfaction, correlation counts, cumulative representative utility when needed, and lineage/schema identities. Do not persist complete per-candidate coverage/representative arrays.

Compatibility:

```text
reader / artifact        MVSTATE-REUSE1      MVSTATE2
MVSEL1 / REPAIR1         READ                REJECT
MVSEL2                    REJECT + REBUILD    READ/WRITE
REPAIR2                   REJECT + REBUILD    READ
```

No MVSTATE1 -> MVSTATE2 migration is required; incompatible reconstructible state is rejected and rebuilt.

Identity binds dataset/domain, candidate/UID order, reference identity, forward graph/MVIDX identity, canonical family order, witness weights, obligations, correlation units, selector policy including target sizes/tau/epsilon/objectives/ties, selected prefix, and v2 schema/kernel versions. Worker count, batch size, queue depth, rebuild policy, progress cadence, and storage location are execution-only.

Checkpoint publication is transactional: write temporary state, authenticate completely, then publish atomically. Reject partial, truncated, stale-lineage, digest-mismatched, and unsupported artifacts. Heap contents are reconstructible execution state and are not persisted as authority.

## 10. Preflight and deterministic execution

Before rank 1, fail closed on invalid candidate/UID identity, family order, CSR dimensions/offsets, row uniqueness/order contract, non-finite/negative weights, obligation feasibility/incidence, coverage capacity, correlation codes, or requested cardinality. Validate or explicitly handle duplicate witnesses within candidate rows; never silently double-increment multiplicity.

Candidate parallelism may evaluate independent rows concurrently, but authoritative scores are gathered by candidate ID and compared canonically. One candidate score must not depend on worker completion order or nondeterministic native reduction. Persisted winner scores are recomputed through canonical row-local authority if an optimized batch implementation uses a different internal layout.

## 11. Performance and observability

Report phase, rank, fixed `HH:MM:SS` elapsed/ETA, throughput, mutation forward edges, candidate-evaluation forward edges, cumulative edge traffic by category, eligible count, Phase-A contender width, Phase-B certified frontier width, rescoring count, heap/stale/rebuild statistics, fallback count, RSS where available, forward-index I/O where measurable, and checkpoint timing/bytes from G5 onward.

Production qualification requires:

1. zero inverse witness->candidate propagation in MVSEL2/REPAIR2 mutation;
2. v2 operation without inverse-array materialization/page touching;
3. at least **10x** projected or measured full 16,384-order selector-time improvement versus equivalent same-host MVSEL1 production baseline/projection;
4. fallback within the frozen limit;
5. bounded RAM/object/checkpoint growth under `StageResourceScope`;
6. separate cold-start, warm-cache, and checkpoint-resume measurements.

Failure of the 10x criterion or persistent lazy degeneracy is a design signal, not permission to approximate.

## 12. Non-goals

Do not combine this work with target-size changes, coverage/tolerance changes, post-selection max-min redesign, master-order/rung digest decomposition, MVIDX2/inverse removal, approximate/stochastic selection, GPU selector authority, unrelated MACE/training changes, or broad NUMA/scheduler redesign.

## 13. Resource/workflow constraints

- Work on `feat/mvsel2-forward-lazy`, not `main`.
- Use `conda run -n mace ...` unless a test requires otherwise.
- External simulation/trajectory inputs are read-only.
- Profile before optimizing; benchmark before/after under equivalent conditions.
- Use bounded queues/batches and existing `StageResourceScope` resource ownership.
- Suppress nested BLAS/OpenMP parallelism when outer candidate work fills the CPU budget unless measured exact-equivalent evidence justifies otherwise.
- Do not commit production caches, large trajectories, checkpoints, or scratch output.
- Do not claim GPU qualification without supported hardware and explicit qualification.

## 14. Gate sequence

| Gate | Approval | Initial status | Purpose |
|---|---|---|---|
| G0 BASELINE-ORACLE | AUTO | PENDING | stale-plan guard, frozen semantics, independent exact oracle |
| G1 MVSEL2-FWD1 | AUTO | PENDING | forward scoring/mutation + forward-only MVIDX1 consumption |
| G2 MVSEL2-PHASEA1 | AUTO | PENDING | exact Phase A + production scaling preflight |
| G3 MVSEL2-CELF1 | AUTO | PENDING | certified exact Phase-B lazy frontier |
| G4 MVSEL2-PERF1 | AUTO | PENDING | production-density selector performance qualification |
| G5 MVSTATE2 | AUTO | PENDING | compact authenticated restart state |
| G6 MVSEL2-QUAL1 | AUTO | PENDING | independent selector scientific/deterministic qualification |
| G7 REPAIR2 | AUTO | PENDING | forward-state exact repair replacing v1 eager dependency |
| G8 MVMIGRATE2 | AUTO | PENDING | end-to-end migration and permanent-artifact closeout |
| Follow-up MVIDX2 | separate workplan | DEFERRED | audit/remove inverse storage after consumers are gone |

### G0 — BASELINE-ORACLE

Verify branch ancestry against `1918f940debecade786b9b89c13c1bca3d787c89`; verify assumption paths still match the frozen semantics; build an independent small exact selector directly from witness state/forward rows; add adversarial preflight fixtures.

**PASS:** exact hand-built cases cover ties, exact/inside/outside epsilon, tied bottleneck families, hard-obligation threshold transitions, correlation balance, diversity, zero-degree rows, row-contract failures, and `tau-epsilon` phase transition. Material base disagreement => `STALE_WORKPLAN`.

Before runtime code changes, run the canonical MLFF architecture assembler/render/provenance workflow so the small current-state Part-V source edit on this branch is synchronized into generated Markdown/PDF artifacts. This is documentation synchronization, not implementation of MVSEL2.

### G1 — MVSEL2-FWD1

Implement canonical forward state/scoring/mutation and forward-only graph access.

**PASS:** scores equal independent oracle on deterministic/random small graphs; select/deselect preserves multiplicity/coverage/obligations/correlation/representative utility; inverse-access sentinels prove no v2 mutation reads inverse adjacency; worker/batch choices preserve authority.

### G2 — MVSEL2-PHASEA1

Implement complete exact Phase A.

**PASS:** every Phase-A accepted rank equals independent full-forward oracle; worker/batch changes preserve prefix; production preflight records evaluation/mutation edges, contender widths, RSS, and completion projection. If projected Phase-A improvement is <10x versus current MVSEL1 selector baseline, stop `DESIGN_REVISION_REQUIRED` before Phase B.

### G3 — MVSEL2-CELF1

Implement single global certified lazy representative frontier with exact Phase-B rebase.

**PASS:** lazy and full-forward v2 selectors produce identical master orders, criterion records, phase transition, and rungs on deterministic/random/adversarial fixtures; queue rebuild/batch/worker settings do not alter authority; conservative bound assertions hold.

### G4 — MVSEL2-PERF1

Production-density selector qualification.

**PASS:** zero inverse propagation; >=10x projected/measured full-order selector improvement; fallback <=1% Phase-B ranks and never >3 consecutive; bounded memory/object growth; cold and warm index behavior reported. Otherwise `DESIGN_REVISION_REQUIRED`.

### G5 — MVSTATE2

Add compact authenticated exact checkpoint/restart.

**PASS:** uninterrupted/resumed results identical; worker/batch/rebuild settings preserve continuation; stale/tampered/truncated/interrupted state fails safely or rebuilds; MVSTATE1 is never misread as MVSTATE2; no complete candidate gain arrays persisted; footprint and recovery cost measured.

### G6 — MVSEL2-QUAL1

Independent scientific selector qualification.

**PASS:** TARGET-DATA2B/MVQUAL independently validates every materializable rung, obligations, coverage, cardinality, nesting, UID validity, and deficit metrics; deterministic replay across worker/batch/rebuild/restart; lazy/full-forward v2 orders match. MVSEL1 same-N comparison is diagnostic only; obsolete eager arrays need not match.

### G7 — REPAIR2

Replace REPAIR1 eager-state dependency with forward-state repair.

**PASS:** legacy repair fixtures reproduce complete accepted swap trace and terminal order under frozen semantics, or any numerical-authority difference receives explicit review before acceptance; same-N coverage/obligations do not regress relative to MVSEL2; worker/batch schedule preserves trace; production repair performs no MVSEL1 eager reconstruction/inverse mutation; repair performance/restart cost is measured and bounded.

### G8 — MVMIGRATE2

Wire MVSEL2 + MVSTATE2 + REPAIR2 into production TARGET-DATA2C, preserving explicit v1 legacy identity/readability. Run end-to-end TARGET-DATA2B -> MVIDX1 -> MVSEL2 -> MVSTATE2 -> REPAIR2 -> MVQUAL and relevant broad regressions.

After implementation acceptance only:

- write/update current MVSEL2/MVSTATE2/REPAIR2 specifications;
- revise Part V/VI and affected ownership chapters to describe accepted current state, never gate chronology;
- rebuild assembled architecture Markdown/PDF/provenance;
- update history/changelog/version/schema records according to repository policy;
- record exact workplan SHA-256 and archive this workplan under `workplans/archive/`.

**PASS:** new campaigns explicitly use v2 chain; old products remain identifiable; incompatible caches rebuild rather than misdeserialize; independent end-to-end qualification passes at every rung/repaired output; performance survives checkpoint/repair overhead; permanent docs/specs/evidence match accepted code.

## 15. Design-revision triggers

Stop `DESIGN_REVISION_REQUIRED` rather than improvising if implementation would require any of the following:

- changing `tau`, target sizes, gain-tolerance semantics, hard-obligation semantics, bottleneck rule, lexicographic order, diversity, or UID tie-break;
- changing Phase A scientific objective;
- inability to maintain/prove conservative stale representative upper bounds;
- approximate/stochastic/hardware-dependent scientific selection;
- fallback beyond G4 limits or failure of the 10x scaling criterion;
- changing MVIDX scientific schema merely to expose forward-only access;
- unresolved duplicate/ordering defects in candidate CSR without changing graph semantics;
- retaining REPAIR1 eager gain arrays/inverse mutation behind MVSEL2;
- changing REPAIR1 scientific repair semantics rather than execution/state representation;
- destructive authoritative migration or mandatory MVSTATE1->MVSTATE2 conversion instead of rebuild;
- expansion into MVIDX2, GPU authority, target-data policy, training policy, or unrelated architecture.

Use `STALE_WORKPLAN` when the implementation base materially diverges from the analyzed authority.

## 16. Final closeout checklist

- [ ] G0-G8 evidence recorded honestly as PASS/FAIL/BLOCKED.
- [ ] Current specs match accepted v2 code.
- [ ] Architecture describes accepted behavior only.
- [ ] Legacy MVSEL1/MVSTATE-REUSE1/REPAIR1 compatibility is explicit.
- [ ] History/changelog/version/schema follow repository governance.
- [ ] Markdown/PDF/provenance rebuilt and verified.
- [ ] Production performance, cold/warm I/O, checkpoint recovery, and repair overhead measured.
- [ ] Broad/release qualification complete or explicitly BLOCKED/DEFERRED.
- [ ] Final evidence records `workplan_id=DOC-MVSEL2`, `plan_revision=4`, exact workplan SHA-256.
- [ ] Workplan moved to `workplans/archive/` only after final acceptance.

## 17. Implementation start instruction

Codex starts at **G0 BASELINE-ORACLE** on `feat/mvsel2-forward-lazy`. Gates are `AUTO`: after objective PASS, record evidence and continue without routine approval. Stop only on persistent FAIL, BLOCKED, `STALE_WORKPLAN`, `DESIGN_REVISION_REQUIRED`, an irreversible/external action requiring approval, or a genuinely unresolved user decision.
