---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-V5-REDESIGN1
protocol_version: 5.0.0
status: IN_PROGRESS
analysis_base_ref: feat/mvsel2-forward-lazy
supersedes_execution_workplan: DOC-MVSEL2-PAR1
---

# DOC-MVSEL2-V5-REDESIGN1 — MVSEL2 forward-kernel and ownership redesign

## Objective

Restore and materially improve MVSEL2 production throughput without changing the frozen scientific selector/repair semantics, while reducing the accumulated execution and recovery complexity around MVSEL2.

The observed candidate-thread PAR1 implementation is a failed optimization: on the real workstation it reduces throughput to roughly half of the prior single-worker path. Treat that as a redesign trigger, not a request for additional worker/process machinery.

## Engineering envelope

Preserve exactly:

- exact MVIDX1 neighborhood semantics and forward-only MVSEL2/REPAIR2 runtime consumption;
- FP64 scientific arithmetic and the current `best - epsilon` contender rule;
- Phase-A hard-obligation, canonical bottleneck, total-coverage, correlation, representative, diversity, UID ordering;
- certified exact Phase-B representative frontier semantics;
- deterministic sequential authoritative mutation;
- nested rung/master-order semantics;
- MVSTATE2 restart correctness and REPAIR2 exact scientific behavior.

Production scale is approximately 36,408 candidates, 165 families, 9.5 billion forward candidate-witness edges, and requested prefixes through 16,384. The design must remain feasible on the 64 GiB-class workstation without recreating MVSEL1 eager inverse marginal state or a second persistent global graph.

## Root-cause diagnosis

PAR1 parallelizes the wrong abstraction. Threads still execute Python candidate/family loops containing many small NumPy/memmap gathers and temporary allocations. This adds scheduling, allocator, page-cache, and memory-bandwidth contention without creating a coarse vector/compiled kernel.

Additional measured/code-path problems to remove:

1. persisted `uint32` witness rows are repeatedly widened/copied to `int64`;
2. Phase A stores complete per-family gain tuples for every total-coverage contender although only the winner needs that vector;
3. broad scans traverse candidate-major across many mapped family arrays rather than streaming one family at a time;
4. Phase-B family-streaming execution is installed through runtime monkeypatching instead of being the canonical selector implementation;
5. normal and resumable selector builders duplicate substantial control flow;
6. checkpoint restore plus resume can replay the selected prefix multiple times before useful continuation;
7. REPAIR2 loop ownership is duplicated between the repair module and runtime/hardening helpers.

## Chosen architecture

Use one canonical forward scoring kernel over the existing MVIDX1 forward view. The kernel owns row traversal, score scratch arrays, exact family-major broad scans, and winner-only full score materialization. Selector/repair code owns scientific decision order and state mutation; runtime code owns only orchestration/persistence.

Do not add multiprocessing, a worker supervisor, GPU selector authority, a second persistent index, or MVSEL1-style complete candidate marginal arrays.

CPU concurrency is deferred until the clean serial/vectorized kernel is measured. Any later concurrency must operate on coarse contiguous edge ranges and demonstrate material sustained speedup over the clean baseline.

## Gates

### G0 — stop regression and freeze baseline

- Mark `DOC-MVSEL2-PAR1` superseded.
- Restore production MVSEL2 execution to the single-worker authority regardless of campaign worker budget.
- Replace the thread-scheduling regression with a correctness/performance-contract regression that prevents reintroducing PAR1 implicitly.
- Record that the current real workstation observation is approximately 0.5x the prior throughput with PAR1.

**Pass:** no production `ThreadPoolExecutor` path remains active in MVSEL2 selection; scientific API compatibility is retained.

### G1 — canonical forward scoring kernel

- Introduce one cohesive forward scoring kernel using native CSR index dtype without unconditional `uint32 -> int64` row copies.
- Use reusable contiguous candidate score scratch arrays rather than per-candidate Python dictionaries where broad scans require scalar scores.
- During Phase A, retain only scalar total-coverage values for contenders; recompute/materialize the complete family-gain vector once for the winner.
- Implement family-major exact broad scans where they preserve canonical FP64 semantics; keep staged Phase-A pruning.
- Make the family-streaming Phase-B rebase canonical and remove runtime monkeypatch installation.

**Pass:** focused oracle/equivalence tests produce identical choices/scores/rungs on existing fixtures; no inverse adjacency is touched.

### G2 — one selector/resume authority

- Collapse normal and resumable selection into one selector engine accepting an optional authenticated continuation state/history.
- Remove duplicated rank-loop ownership from the resume module.
- Keep checkpoint reconstruction validation independent, but avoid replaying the same historical prefix twice during one resume.
- Persist/reuse the compact rank journal needed to reconstruct plan history without rescoring already accepted ranks when safe under existing artifact compatibility rules.

**Pass:** fresh and resumed execution are byte/field equivalent on focused fixtures; one normal rank loop owns selection.

### G3 — one REPAIR2/runtime authority

- Move exact per-rung repair execution into `target_multi_view_repair_v2.py` as the sole scientific owner.
- Reduce hardening/runtime modules to state lookup, invocation, persistence, and progress reporting.
- Delete import-time selector monkeypatching and duplicated repair loops/helpers after callers migrate.

**Pass:** REPAIR2 fixture traces remain identical and runtime modules contain no independent repair science.

### G4 — product-path review and performance closeout

Run the smallest direct checks that establish the claims:

- focused MVSEL2 oracle/forward/state/resume/repair regressions;
- existing campaign-routing integration tests;
- representative Phase-A and Phase-B benchmark from the real production graph/cache when available;
- actual campaign continuation on the workstation for target-scale throughput/RSS/page-fault evidence.

Acceptance:

1. scientific choices and persisted authority remain exact;
2. no inverse MVSEL1 mutation or inverse-array paging is reintroduced;
3. PAR1 slowdown is eliminated;
4. sustained throughput is at least no worse than the accepted pre-PAR1 single-worker implementation, with further optimization accepted only when measured benefit justifies complexity;
5. no material RAM/disk regression;
6. restart avoids duplicate full historical replay in one invocation;
7. Protocol-5 independent review finds no remaining duplicated execution authority or unjustified compatibility machinery in the affected subsystem.

If the clean Python/NumPy family-streaming kernel is still materially too slow at production scale, the next authorized escalation is a small compiled CSR scan kernel behind the same scoring interface. Do not add Python process/thread orchestration first.

## Non-goals

No change to target sizes, coverage threshold/tolerance, neighborhood geometry, scientific selector objectives, REPAIR2 policy, MVIDX1 scientific identity, MACE training policy, GPU training/evaluation behavior, or unrelated MLFF documentation migration.
