---
kind: implementation-workplan
workplan_id: DOC-REPAIR2-PERF1
protocol_version: 5.1.0
status: R0_READY
analysis_base_ref: feat/mvsel2-forward-lazy
predecessor_workplan: DOC-MVSEL2-V5-REDESIGN1
review_status: FINAL_REVIEW_HARDENED
---

# DOC-REPAIR2-PERF1 — exact REPAIR2 scaling and downstream preparation optimization

## Objective

Remove the newly exposed TARGET-DATA2C-REPAIR2 product bottleneck without changing repair science, then continue the same real `prepare` path far enough to identify the next measured bottleneck rather than speculatively optimizing downstream stages.

The first optimization target is not thread count. It is repeated state-invariant work inside the exact no-copy proposal search.

## Product evidence that opens this plan

G4-N3 closed MVSEL2 successfully. The exact native/OpenMP selector resumed from 2,048 through `mvstate2+journal`, selected 8 workers after a 2.59x real-MVIDX preflight speedup, reached 16,384 at 37.996 ranks/s, and accepted its authority before the enclosing 20-minute command timeout.

The timeout occurred later in REPAIR2. REPAIR2 reported:

- rung 128: about 00:00:37, proposals=0, swaps=0;
- rung 256: about 00:00:38, proposals=0, swaps=0;
- rung 512: about 00:00:41, proposals=0, swaps=0;
- no next-rung report before the enclosing 00:20:02 timeout.

The raw G4-N3 evidence is retained in the repository and normalized in `benchmarks/mvsel2_g4n3_native_closeout.md`.

## Scientific and architectural envelope

Preserve exactly:

- REPAIR2 as the single scientific repair owner in `target_multi_view_repair_v2.py`;
- active-shell-only repair and immutable lower prefixes;
- rank inheritance and future-order displacement semantics;
- exact hard-obligation non-regression;
- exact same-N coverage non-regression relative to MVSEL2;
- the existing lexicographic objective and tolerance rules;
- deterministic removal ordering, proposal comparison, replacement UID tie-break, and authoritative mutation order;
- forward-only MVIDX1 consumption;
- no inverse adjacency or inverse mutation;
- no full-state copy per proposal;
- no approximation, stochastic pruning, approximate nearest-neighbor search, or changed repair shortlist policy;
- no process pool or duplicate repair implementation in the campaign seam;
- bounded persistent storage with no second product-scale graph.

Execution-only caches and native kernels may be introduced only when they are reconstructible from authenticated authority and cannot become independent scientific state.

### Frozen-reference rule

This is an execution optimization of the **current REPAIR2 authority**, not an opportunity to reinterpret its hypothetical exchange mathematics.

In particular, preserve the following current behaviors even where another formulation might appear more natural:

1. `_proposal()` builds its hard, bottleneck-family, and total-coverage frontiers from the current unmodified state before any hypothetical removal is applied.
2. A selected removal candidate is not reintroduced into the replacement pool during the hypothetical proposal search; the pool is the current `state.available` population.
3. Removals qualify when unique coverage is `<= unique_coverage_tolerance`, not only when unique coverage is mathematically zero. Therefore a small positive unique mass within tolerance must behave exactly as it does before optimization.
4. The bottleneck family is the **first canonical family** whose coverage mass lies within `min_mass + gain_tie_tolerance`; it is not replaceable by an arbitrary `argmin`/parallel reduction result.
5. Every `_filter()` stage preserves its incoming canonical candidate order; only the existing terminal UID rule resolves the final replacement tie.

If an implementation changes any of these behaviors, R1 fails. Such a change would require a separately approved scientific redesign rather than a performance workplan update.

### Authority/version rule

R0/R1/R2 are execution-only changes. They must not change:

- REPAIR2 policy/schema/version;
- serialized rung/swap fields;
- repair plan digest for identical inputs;
- campaign persistence key or lineage;
- scientific output merely to accommodate a faster implementation.

Do not update a golden digest to bless a changed result. Any output/digest change is a failed equivalence gate unless separately reviewed as a scientific change.

## Source review — current execution path

### Ownership is sound

`mvsel2_hardening_runtime.py` opens authenticated forward MVIDX1 state, invokes `target_multi_view_repair_v2.py`, validates the resulting authority, persists it, and contains no candidate scoring, proposal algorithm, mutation algorithm, or repair loop of its own.

This single-owner architecture is retained.

### Rung continuation is sound but not restartable mid-REPAIR2

Within one invocation, repaired state is carried forward from rung to rung. REPAIR2 is not rebuilding each rung from rank zero.

However, the campaign currently persists `target_multi_view_repair_v2` only after the complete plan builds and validates. An interruption therefore reruns REPAIR2 from its beginning. Restart optimization is considered only after the primary algorithmic bottleneck is removed.

### Worker configuration is currently execution-inert

`build_target_multi_view_repair_plan_v2()` accepts `workers` and `batch_size`, but the current scalar authority deletes `batch_size` and does not use `workers` for proposal execution. The campaign resource scope simultaneously fixes `python_workers=1`.

Until a later parallel gate is justified, telemetry must describe REPAIR2 as scalar rather than imply that configured query workers accelerate it.

## Primary scaling defect

For each unchanged authoritative state, the repair loop may shortlist up to 64 removable active-shell candidates. `_proposal()` is then called independently for each removal.

For every one of those removals, the current implementation repeats state-invariant work:

1. enumerate the current available candidate set;
2. recompute representative utility and the current objective;
3. recompute hard-gain values/frontier;
4. recompute current family masses and the canonical bottleneck family;
5. scan candidate rows in that bottleneck family and filter them;
6. for every survivor, compute total coverage gain by traversing all forward families;
7. rediscover the same state-level no-positive-coverage-gain early-exit condition.

Only after those repeated scans does proposal evaluation become removal-dependent through the removed correlation unit, shared-witness representative effect, pair diversity, and terminal UID tie.

The authoritative state is not mutated while alternative removals are being compared. Therefore the repeated steps above are candidates for exact factorization.

The current algorithm can approach repeated product-scale forward scans per unchanged state. With a removal shortlist limit of 64 this is an algorithmic amplification problem, not primarily a threading problem.

## Chosen design — execution-only proposal frontier context

Introduce one private execution-only `RepairProposalFrontierContextV2` (name may change during implementation) for one repair-loop state iteration.

### Lifetime and invalidation

Prefer a **lexically local context** constructed after the removal shortlist for the current `while` iteration and discarded before that iteration exits. This is safer than a long-lived cache plus generation bookkeeping.

The context must never survive:

- an accepted deselect/select swap;
- selector-prefix extension into another rung;
- any other authoritative mutation of multiplicity, coverage, obligation, availability, or correlation-unit state.

A fresh context is built for the next unchanged state. If implementation instead introduces a reusable object, it must carry an explicit state-generation guard and fail closed on a generation mismatch; lexical lifetime remains preferred.

### Permitted contents

The context may contain only state-invariant information such as:

- current representative utility and objective tuple;
- canonical available candidate tuple/order;
- whether a hard deficit is pending;
- hard-gain values/frontier when required;
- current family masses and deterministic bottleneck family;
- bottleneck-family candidate gains and filtered frontier;
- total coverage-gain values and the filtered coverage frontier;
- an exact state-level `proposal_possible` decision corresponding to the existing early-return rule;
- small static candidate metadata needed by later filters.

The context must not contain persisted scientific authority.

### Memory constraint

Do **not** cache a candidate-by-family gain matrix or per-removal candidate table.

For shared frontier construction, retain at most O(candidate-count) scalar/index data plus existing state. No new array may have a material dimension proportional to `candidate_count * family_count`, `removal_count * candidate_count`, or total forward-edge count.

Per-family gain vectors may be transient. When a final replacement requires its full family-gain tuple for `coverage_after`, recompute that one candidate through the same canonical `_total_coverage_gains()` reduction path or prove an exactly equivalent bounded representation.

R0/R1 must report attributable execution-only allocation/RSS. Design target is well below 512 MiB incremental execution memory; any unexplained multi-GiB increase or OS swap fails the gate even if wall time improves.

No new `MADV_DONTNEED`/explicit page-release loop is authorized by this plan; G4c/G4d already demonstrated the risk of release/refault churn.

### Exactness argument to qualify

The factorization is justified by **frozen implementation dataflow**, not by assuming hypothetical removal has zero physical effect.

The current `_proposal()` computes the hard/bottleneck/total-coverage frontier from the unmodified current state. This remains true even when a removable candidate has small positive unique mass allowed by `unique_coverage_tolerance`. R1 must reproduce those same pre-removal values and decisions exactly; it must not recompute them from a more literal post-removal state.

Removal-dependent operations remain per removal:

- mark the removed candidate in `_RepairProposalScratchV2`;
- removed-unit correlation-count adjustment;
- `_pair_representative_gain()`;
- `_pair_diversity()`;
- replacement UID tie-break;
- exact `before`/`after` objective construction using that removal's loss and the chosen replacement;
- strict-improvement/non-regression check.

Hard-frontier factorization likewise preserves current execution order: shortlist removals are already `_hard_safe`, and `_proposal()` computes replacement hard gain from the current state rather than a mutated hypothetical state.

The optimization is accepted only if oracle tests demonstrate exactly identical proposal presence/absence, replacement, objective tuple, winning removal, swap sequence, repaired master order, rung evidence, serialized authority, and final content digest.

### State-level early termination

The current scientific rule returns no proposal when there is no hard deficit and the best surviving total coverage gain is at or below tolerance. That condition is evaluated from the unmodified current state and is therefore identical for every removal considered in that state iteration.

The frontier context may therefore conclude once per unchanged state that **no shortlisted removal can produce a proposal under the frozen authority**. In that case all removal-dependent proposal evaluations are skipped.

This is expected to be the highest-leverage improvement at highly covered large rungs.

## Gate sequence

### R0 — exact profiling and operation accounting

Add low-overhead execution telemetry before changing the algorithm.

For every rung and repair-state iteration record separately:

- selected-prefix extension/replay wall time;
- initial `zero_unique_shell_fraction` scan wall/rows/edges separately from later removal-shortlist scans;
- removal-metric scan wall time and forward rows/edges inspected;
- representative-utility/objective wall time;
- number of zero/negligible-unique hard-safe removals;
- removal shortlist size;
- proposal-frontier/state-invariant wall time;
- number of candidates after hard, bottleneck, total-coverage, and unit filters;
- total candidate-family rows/forward edges evaluated for coverage gains;
- removal-dependent representative/diversity wall time;
- accepted mutation wall time;
- proposal counts both per state/rung and cumulative per domain;
- accepted swap count;
- final independent validation wall time;
- major/minor faults and filesystem input around REPAIR2 when cheaply available;
- fixed `hh:mm:ss` elapsed/ETA formatting where an ETA is meaningful; report ETA as unavailable rather than inventing a misleading rung-linear estimate before enough comparable work exists.

#### Instrumentation constraints

Telemetry is execution-only and cannot affect scientific digests. Edge counts should be derived from existing CSR offset differences/row lengths rather than adding a Python increment inside every forward edge. Timers/counters must not allocate product-scale copies.

Focused instrumentation qualification must show no result/digest change and no material distortion of a representative REPAIR2 fixture; target overhead is <5% on a repeatable fixture when timing noise permits comparison.

The R0 real-product meter may terminate after the first completed pathological/proposal-bearing rung. Do not add a production scientific `stop_after_rung` policy. Use an external meter timeout or a clearly benchmark-only completion callback/private sentinel that cannot be reached through normal campaign authority construction.

**Pass:** identify the first expensive rung and quantify which portion is repeated state-invariant proposal work versus initial/removal metrics, representative utility, pair terms, state mutation, and validation.

### R1 — scalar proposal-frontier factorization

Implement the execution-only frontier context described above while leaving all authoritative decisions and mutation scalar.

Requirements:

- construct one context per unchanged `while`-iteration state, after the current removal shortlist is known;
- discard it at the iteration/mutation boundary; no cross-mutation reuse;
- preserve the exact current `state.available` replacement pool; do not reinsert the removed selected candidate;
- preserve the exact first-family-within-tolerance bottleneck rule;
- preserve incoming candidate order through hard/bottleneck/total/unit/representative/diversity filters;
- preserve the existing FP64 summation/reduction path for values that participate in decisions or persisted evidence;
- full per-family gain matrices are not retained;
- state-level no-proposal early termination is used only when exactly equivalent to the current frozen condition;
- retain the old scalar proposal path only as a test/reference oracle, unreachable from the product campaign path; add a focused source/call-path assertion if useful to prevent two product authorities from surviving.

Focused qualification must include:

- hand-constructed hard-deficit and no-hard-deficit cases;
- no-proposal fully/highly covered cases;
- exact-zero unique removal and **positive-but-within-`unique_coverage_tolerance`** removal;
- multiple qualifying removals with different correlation units;
- candidates sharing removed witnesses;
- two or more family masses within the bottleneck tolerance, proving the same canonical first-family choice;
- coverage/representative filter values exactly on and immediately around tolerance boundaries;
- empty/near-empty available frontier and single-candidate frontier behavior;
- deterministic UID terminal ties;
- randomized authenticated small forward graphs;
- exact old-vs-new proposal result and whole-rung swap sequence;
- exact final repair authority serialization and content digest for identical inputs;
- existing REPAIR2-vs-REPAIR1 nonempty trace parity and forward-only dependency tests.

#### R1 structural performance acceptance

Instrumentation must prove the intended asymptotic change, not merely one noisy wall-time win:

- `frontier_build_count` is at most one per unchanged proposal-state iteration;
- state-invariant bottleneck/total-coverage scans do not scale with `removal_shortlist_size`;
- candidate-family forward-edge evaluations attributable to the shared frontier are performed once per state rather than once per shortlisted removal;
- no new product-scale persistent file or inverse graph is created;
- no OS swap and no unexplained multi-GiB execution-memory increase occurs.

**Product pass:** the first pathological rung must show a material reduction in both repeated frontier-edge work and wall time. As a decision guide, >=4x reduction in state-invariant repeated edge work or >=3x pathological-rung wall-time speedup is strong evidence to proceed directly to R5; if the full REPAIR2 stage already completes <=10 minutes including validation, stop adding optimization complexity. Failure to obtain a material improvement sends the measured residual bottleneck to R2 rather than relaxing exactness.

### R2 — remaining scalar/local work, conditional

Run only if R1 leaves a material REPAIR2 bottleneck.

Profile-guided candidates, in priority order:

1. reuse the already computed initial active-shell removal metrics for the first repair iteration **only if no state mutation occurs between the two scans**; retain/recompute `_hard_safe` as required by exact current state;
2. combine/reuse later shell removal metrics only where exact state validity can be proven;
3. reduce allocation in pair representative/diversity evaluation using the existing epoch/stamp scratch mechanism;
4. introduce reconstructible per-family uncovered-term execution caches only if measured candidate coverage-row evaluation remains dominant;
5. optimize final independent validation by incremental nested-prefix replay only if validation itself becomes a measured bottleneck.

Every cache is execution-only and invalidated/updated by the same authoritative mutation boundary. No inverse mapping may be introduced.

### R3 — checkpoint-assisted execution, conditional

Run only if REPAIR2 remains long enough that interruption/restart cost is operationally material after R1/R2.

#### Pre-divergence MVSTATE2 reuse

Checkpoint reuse must be implemented inside the canonical REPAIR2 owner, not in a second campaign-side repair loop.

A crucial boundary is the active shell: restoring the current implementation at a checkpoint whose size equals the rung being repaired sets `previous_size` to that rung and would make its shell empty. Therefore do **not** simply restore the target rung and claim it has been repaired.

Prefer one of these provably exact designs:

- restore the authenticated checkpoint for the **predecessor materializable rung / active-shell start**, then extend and repair the complete next shell normally; or
- extend the canonical owner with explicit authenticated `repair_shell_start` metadata and prove that a state restored at a later size still evaluates exactly the same active shell and frozen proposal semantics.

The predecessor-rung form is preferred because it reuses the current state machine with less exceptional logic. Never restore all rung states simultaneously.

#### Post-divergence journal, only if still needed

If post-divergence restart remains operationally necessary, design a compact REPAIR2 journal/checkpoint that persists only completed authoritative boundaries and enough information to reconstruct state by exact forward replay. Its authenticated identity must include at least:

- target coverage reference digest;
- MVIDX1 content/domain digest;
- MVSEL2 plan/domain digest;
- REPAIR2 policy digest/version;
- completed rung/swap boundary;
- repaired-order/prefix identity;
- checkpoint/journal payload digest.

Writes must be atomic/transactional. Never persist partial proposal-frontier context, per-removal candidate state, another graph, or an unauthenticated scratch cache.

Qualification must prove restart equivalence to uninterrupted execution, including repaired order, swap history, rung digests, and final plan digest.

### R4 — native/shared-memory execution, conditional last resort

Run only if R1/R2 leave repeated read-only candidate-row scoring as a measured dominant cost.

- use the package-wide native extension registry/build machinery;
- parallelize independent read-only candidate rows only;
- keep removal ordering, proposal winner choice, and authoritative mutation serial;
- reproduce the frozen NumPy FP64 reduction/filter semantics exactly, including masked/compacted summation order and tolerance-boundary decisions;
- qualify native output against the Python oracle at bitwise/exact decision level;
- use a bounded real-MVIDX worker preflight and automatic scalar fallback;
- do not add Python process pools or inverse-edge state.

Do not assume the existing MVSEL2 row scorer can be reused directly: REPAIR2's masked/compacted coverage summation can have different FP64 grouping from a dense term-with-zeros row sum.

### R5 — full REPAIR2 product closeout

Run the normal product path through all materializable rungs to 16,384 and final independent validation.

Required acceptance:

1. exact scientific regression suite passes;
2. final repair authority validates independently;
3. no coverage/hard-obligation regression versus MVSEL2;
4. deterministic repaired order/swap history is proven by repeated bounded recomputation and product content-digest comparison; a cache-hit/reuse invocation alone does not count as a determinism rerun;
5. no inverse adjacency or full-state proposal copies;
6. no second product-scale graph;
7. zero swap at the OS level;
8. persistent `.mdstats` growth remains bounded and justified;
9. R1/R2 execution-only changes leave REPAIR2 schema/version and identical-input authority digest unchanged;
10. complete **build plus independent validation** comfortably inside the former 20-minute enclosing meter.

Report build and validation wall times separately even though the closeout target applies to their sum.

Performance target: <=10 minutes for full REPAIR2 build + validation is sufficient to close the pathological gate; <=5 minutes is the preferred design target. If R1 alone reaches that regime, stop optimization and proceed downstream.

## Downstream observation gates

The design review does **not** authorize speculative rewrites of every later stage.

### O0 — continue the same real `prepare` path

After R5, continue the same invocation and record per-stage:

- wall/user/system time;
- worker topology/resource class (CPU preparation, GPU inference, GPU training, I/O-heavy materialization);
- peak incremental RSS where attributable;
- filesystem input/output;
- cache/reuse status;
- restart behavior;
- product-scale row/edge/configuration counts when meaningful.

A downstream stage becomes an optimization target if either:

- it exceeds about 5 minutes on the product case or materially dominates other stages in the **same resource class**; or
- source review plus product counters demonstrates a clear asymptotic/repeated-scan pathology likely to worsen materially with scale.

Do not use a long GPU TRAIN2 wall time to make a CPU preparation stage look artificially insignificant, or vice versa.

### O1 — REPAIR2 final validator watch

The current validator independently recomputes coverage and hard-obligation evidence for every materializable nested rung. Preserve independent validation, but measure it separately after R1. If it becomes dominant, redesign it as an independent incremental nested-prefix validator rather than removing or weakening the check. The optimized validator must remain independent of proposal-context caches and repair-time derived coverage evidence.

### O2 — MVQUAL1 watch

Current MVQUAL1 already has a credible scaling architecture:

- independent domain/selector/size score jobs;
- deterministic work queue;
- explicit per-job temporary-memory estimates;
- outer scoring parallelism with inner cKDTree queries constrained to one worker when appropriate;
- canonical result reassembly before scientific comparison.

Therefore measure first. Optimize only if the real product meter shows a material bottleneck. Do not replace its independent TARGET-DATA2B scientific scoring with MVIDX-only authority merely for speed.

### O3 — TARGET-DATA2D / production materialization watch

TARGET-DATA2D's 3/10/30 successive-fidelity work is predominantly scientific training/evaluation rather than the same CPU graph-selection problem. Treat GPU/training optimization as a separate gate if it becomes dominant.

Production DATA6--DATA8 materialization already owns restart checkpoints, immutable lineage, artifact verification/reuse, and atomic promotion. Measure hashing, archive I/O, DATA7 feature fitting, and DATA8 construction independently before changing those contracts.

Pure decision/provenance stages such as TARGET-DATA2E should not be optimized without evidence.

## Final independent-review findings incorporated

The final adversarial review applies the protocol's software-design independent-review criteria to correctness, numerical fidelity, asymptotic scaling, memory/I/O, recovery, ownership, complexity, and representative qualification.

It adds or tightens the following boundaries:

1. **Factorization proof is based on frozen dataflow, not exact-zero uniqueness.** Positive-but-within-tolerance unique mass is an explicit regression case.
2. **Replacement-pool semantics are frozen.** The hypothetical removal is not reinserted into `state.available`.
3. **Tolerance-order semantics are frozen.** Canonical first-family bottleneck selection and candidate filter order must survive refactoring.
4. **Context lifetime is lexical per unchanged state.** This prevents stale execution caches from crossing prefix extension or accepted swaps.
5. **Execution-only means no authority migration.** R0/R1/R2 cannot change schema, version, persistence lineage, or identical-input content digest.
6. **Instrumentation must be cheap.** Edge accounting derives from CSR lengths rather than per-edge Python hooks, and benchmark stopping cannot become a scientific production policy.
7. **Performance acceptance is structural as well as temporal.** R1 must prove removal-shortlist amplification is gone, not merely produce one favorable wall-clock run.
8. **Memory/I/O regression is a gate.** No candidate×family/per-removal matrix, second graph, page-release churn, swap, or unexplained multi-GiB allocation is acceptable.
9. **Checkpoint reuse must respect the active-shell boundary.** A checkpoint at the rung being repaired cannot simply be fed to the current continuation hook because that would make the shell empty; predecessor-rung restore is preferred.
10. **Restart journals, if ever needed, have explicit lineage/atomicity requirements** and cannot persist proposal scratch.
11. **Product determinism and validation timing are defined precisely.** A cache-hit run is not a determinism rerun; build and independent validation are timed separately and jointly.
12. **Downstream bottlenecks are compared within resource class**, preventing long GPU stages from obscuring CPU/I/O pathologies.

The reviewed plan continues to reject these tempting approaches:

- parallelism first;
- REPAIR1 inverse-edge machinery;
- candidate×family gain matrices;
- unproven direct MVSEL2 native scorer reuse;
- restoring all MVSTATE2 rung states at once;
- speculative downstream rewrites before measurement.

## Implementation boundary

This workplan is design/review output only. No REPAIR2 scientific implementation is changed by this plan commit.

The next implementation action is R0 instrumentation, followed by a bounded real-product meter. R1 is implemented only against the evidence and exactness contract established by R0.
