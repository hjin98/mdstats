---
kind: implementation-workplan
workplan_id: DOC-REPAIR2-PERF1
protocol_version: 5.1.0
status: R0_READY
analysis_base_ref: feat/mvsel2-forward-lazy
predecessor_workplan: DOC-MVSEL2-V5-REDESIGN1
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

## Source review — current execution path

### Ownership is sound

`mvsel2_hardening_runtime.py` opens authenticated forward MVIDX1 state, invokes `target_multi_view_repair_v2.py`, validates the resulting authority, persists it, and contains no candidate scoring, proposal algorithm, mutation algorithm, or repair loop of its own.

This single-owner architecture is retained.

### Rung continuation is sound but not restartable mid-REPAIR2

Within one invocation, repaired state is carried forward from rung to rung. REPAIR2 is not rebuilding each rung from rank zero.

However, the campaign currently persists `target_multi_view_repair_v2` only after the complete plan builds and validates. The accepted status explicitly reports `repair_checkpoint_reuse=false`. An interruption therefore reruns REPAIR2 from its beginning. Restart optimization is considered only after the primary algorithmic bottleneck is removed.

### Worker configuration is currently execution-inert

`build_target_multi_view_repair_plan_v2()` accepts `workers` and `batch_size`, but the current scalar authority deletes `batch_size` and does not use `workers` for proposal execution. The campaign resource scope simultaneously fixes `python_workers=1`.

Until a later parallel gate is justified, telemetry must describe REPAIR2 as scalar rather than imply that configured query workers accelerate it.

## Primary scaling defect

For each unchanged authoritative state, the repair loop may shortlist up to 64 removable active-shell candidates. `_proposal()` is then called independently for each removal.

For every one of those removals, the current implementation repeats state-invariant work:

1. enumerate the entire currently available candidate set;
2. recompute representative utility and the current objective;
3. recompute hard-gain values/frontier;
4. recompute the current family masses and bottleneck family;
5. scan candidate rows in that bottleneck family and filter them;
6. for every survivor, compute total coverage gain by traversing all forward families;
7. rediscover the same state-level no-positive-coverage-gain early-exit condition.

Only after those repeated scans does proposal evaluation become removal-dependent through the removed correlation unit, shared-witness representative effect, pair diversity, and terminal UID tie.

The authoritative state is not mutated while alternative removals are being compared. Therefore the repeated steps above are candidates for exact factorization.

The current algorithm can approach repeated product-scale forward scans per unchanged state. With a removal shortlist limit of 64 this is an algorithmic amplification problem, not primarily a threading problem.

## Chosen design — execution-only proposal frontier context

Introduce one private execution-only `RepairProposalFrontierContextV2` (name may change during implementation) built once for each unchanged authoritative state and invalidated immediately after any accepted swap.

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

For shared frontier construction, retain at most O(candidate-count) scalar/index data plus existing state. Per-family gain vectors may be transient. When a final replacement requires its full family gain tuple for the `coverage_after` objective, recompute that one candidate's family gains in canonical family order or use an equivalently bounded exact cache.

This prevents a CPU optimization from recreating the memory-scaling failure that motivated the forward-only redesign.

### Exactness argument to qualify

The current `_proposal()` performs the hard/bottleneck/total-coverage frontier computation from the **unmodified current state** before applying any hypothetical removal. Consequently those steps are already removal-invariant in the frozen implementation. Moving them out of the per-removal function changes execution placement, not scientific inputs.

Removal-dependent operations remain per removal:

- mark the removed candidate in `_RepairProposalScratchV2`;
- removed-unit correlation-count adjustment;
- `_pair_representative_gain()`;
- `_pair_diversity()`;
- replacement UID tie-break;
- exact `before`/`after` objective construction using that removal's loss and chosen replacement;
- strict-improvement/non-regression check.

The optimization is accepted only if oracle tests demonstrate exactly identical proposal presence/absence, replacement, objective tuple, winning removal, swap sequence, repaired master order, rung evidence, and serialized authority.

### State-level early termination

The current scientific rule returns no proposal when there is no hard deficit and the best surviving total coverage gain is at or below tolerance. That condition is independent of the removal candidate because it is evaluated from the unmodified state.

The frontier context may therefore conclude once per unchanged state that **no shortlisted removal can produce a proposal under the existing authority**. In that case all per-removal proposal calls are skipped exactly.

This is expected to be the highest-leverage improvement at highly covered large rungs.

## Gate sequence

### R0 — exact profiling and operation accounting

Add low-overhead execution telemetry before changing the algorithm.

For every rung and repair-state iteration record separately:

- selected-prefix extension/replay wall time;
- removal-metric scan wall time and forward rows/edges inspected;
- number of zero/negligible-unique hard-safe removals;
- removal shortlist size;
- proposal-frontier/state-invariant wall time;
- number of candidates after hard, bottleneck, total-coverage, and unit filters;
- total candidate-family rows/forward edges evaluated for coverage gains;
- removal-dependent representative/diversity wall time;
- accepted mutation wall time;
- proposal count and accepted swap count;
- final independent validation wall time;
- fixed `hh:mm:ss` progress timing/ETA where an ETA is meaningful.

The R0 real-product meter may stop after the first proposal-bearing/pathological rung. It need not spend another long timeout merely to prove the already observed problem.

**Pass:** identify the first expensive rung and quantify which portion is repeated state-invariant proposal work versus removal metrics, pair terms, state mutation, and validation.

### R1 — scalar proposal-frontier factorization

Implement the execution-only frontier context described above while leaving all authoritative decisions and mutation scalar.

Requirements:

- context is built at most once per unchanged authoritative state;
- context is invalidated immediately after every accepted swap;
- no context survives across a state mutation;
- canonical candidate order is preserved through every filter;
- full per-family gain matrices are not retained;
- existing `_proposal()` behavior remains available as a test oracle/private reference, not as a second product authority;
- state-level no-proposal early termination is used only when exactly equivalent to the current frozen condition.

Focused qualification:

- hand-constructed hard-deficit and no-hard-deficit cases;
- no-proposal fully/highly covered cases;
- multiple qualifying removals with different correlation units;
- candidates sharing removed witnesses;
- tolerance-boundary coverage/representative cases;
- deterministic UID tie cases;
- randomized authenticated small forward graphs;
- exact old-vs-new proposal result and whole-rung swap sequence;
- exact final repair authority serialization/digest where inputs are identical.

**Product pass:** materially reduce candidate-family forward-edge evaluations per unchanged state and the first pathological-rung wall time. If the full REPAIR2 stage then completes comfortably, do not add native complexity merely because it is available.

### R2 — remaining scalar/local work, conditional

Run only if R1 leaves a material REPAIR2 bottleneck.

Profile-guided candidates, in priority order:

1. combine/reuse shell removal metrics where exact and state-valid;
2. reduce allocation in pair representative/diversity evaluation using the existing epoch/stamp scratch mechanism;
3. introduce reconstructible per-family uncovered-term execution caches only if measured candidate coverage-row evaluation remains dominant;
4. optimize final independent validation by incremental nested-prefix replay only if validation itself becomes a measured bottleneck.

Every cache is execution-only and invalidated/updated by the same authoritative mutation boundary. No inverse mapping may be introduced.

### R3 — checkpoint-assisted execution, conditional

Run only if REPAIR2 remains long enough that interruption/restart cost is operationally material.

Prefer reuse of existing authenticated MVSTATE2 rung checkpoints **before the first repair divergence**, but only through a canonical-owner API that still evaluates that rung's active shell. Never restore all rung states simultaneously.

If post-divergence restart remains necessary, design a compact REPAIR2 journal/checkpoint that persists completed rung evidence and enough repaired-order information to reconstruct state by exact forward replay. Do not persist another product-scale graph or a removal×candidate cache.

Qualification must prove restart equivalence to uninterrupted execution, including repaired order, swap history, rung digests, and final plan digest.

### R4 — native/shared-memory execution, conditional last resort

Run only if R1/R2 leave repeated read-only candidate-row scoring as a measured dominant cost.

- use the package-wide native extension registry/build machinery;
- parallelize independent read-only candidate rows only;
- keep removal ordering, proposal winner choice, and authoritative mutation serial;
- reproduce the frozen NumPy FP64 reduction/filter semantics exactly, including any masked/compacted summation order;
- qualify native output against the Python oracle at bitwise/exact decision level;
- use a bounded real-MVIDX worker preflight and automatic scalar fallback;
- do not add Python process pools or inverse-edge state.

Do not assume the existing MVSEL2 row scorer can be reused directly: REPAIR2's masked coverage sums must first be proven to have identical FP64 reduction semantics.

### R5 — full REPAIR2 product closeout

Run the normal product path through all materializable rungs to 16,384 and final independent validation.

Required acceptance:

1. exact scientific regression suite passes;
2. final repair authority validates independently;
3. no coverage/hard-obligation regression versus MVSEL2;
4. deterministic repaired order/swap history across repeated runs;
5. no inverse adjacency or full-state proposal copies;
6. no second product-scale graph;
7. zero swap at the OS level;
8. persistent `.mdstats` growth remains bounded and justified;
9. complete REPAIR2 comfortably inside the former 20-minute enclosing meter.

Performance target: <=10 minutes for full REPAIR2 is sufficient to close the pathological gate; <=5 minutes is the preferred design target. If R1 alone reaches that regime, stop optimization and proceed downstream.

## Downstream observation gates

The design review does **not** authorize speculative rewrites of every later stage.

### O0 — continue the same real `prepare` path

After R5, continue the same invocation and record per-stage:

- wall/user/system time;
- worker topology;
- peak incremental RSS where attributable;
- filesystem input/output;
- cache/reuse status;
- restart behavior;
- product-scale row/edge/configuration counts when meaningful.

A downstream stage becomes an optimization target only if either:

- it consumes more than about 20% of the remaining preparation wall time or more than about 5 minutes on the product case; or
- source review plus product counters demonstrates a clear asymptotic/repeated-scan pathology likely to worsen materially with scale.

### O1 — REPAIR2 final validator watch

The current validator independently recomputes coverage and hard-obligation evidence for every materializable nested rung. Preserve independent validation, but measure it separately after R1. If it becomes dominant, redesign it as an independent incremental nested-prefix validator rather than removing or weakening the check.

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

## Independent design-review findings incorporated

The reviewed plan explicitly rejects the following initially tempting approaches:

1. **Parallelism first** — rejected because the source-level amplification repeats the same state-invariant frontier up to the removal-shortlist limit. Parallelizing redundant work preserves the wrong algorithm.
2. **Port REPAIR1 inverse-edge optimization** — rejected because REPAIR2's accepted architecture is forward-only and inverse scientific/mutation state would recreate the design that MVSEL2 deliberately removed.
3. **Cache all candidate×family gains** — rejected because it can create large execution memory proportional to candidate count × family count and is unnecessary for the final objective.
4. **Reuse the MVSEL2 native row scorer without proof** — rejected because filtered/compacted REPAIR2 coverage summation can have different FP64 grouping from a dense term-with-zeros row sum.
5. **Restore all MVSTATE2 rung states at once** — rejected because that can multiply forward-state memory. Any checkpoint-assisted execution must be lazy and one-rung-at-a-time.
6. **Optimize downstream stages before measurement** — rejected because MVQUAL1 and production materialization already contain explicit parallel/restart machinery and may not be the next wall-time bottleneck.

## Implementation boundary

This workplan is design/review output only. No REPAIR2 scientific implementation is changed by this plan commit.

The next implementation action is R0 instrumentation, followed by a bounded real-product meter. R1 is implemented only against the evidence and exactness contract established by R0.
