---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-V5-REDESIGN1
protocol_version: 5.0.0
status: G4_IN_PROGRESS
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

## Gate status

| Gate | Status | Current result |
|---|---|---|
| G0 | PASS | PAR1 marked failed/superseded; production facade no longer routes Phase A through Python candidate threading. |
| G1 | PASS | Exact project validation on the workstation: 51 focused tests passed in 3.84 s. Locality-oriented Phase-A kernel is exact against the serial reference; production Phase-B rebase uses family streaming. |
| G2 | PASS | One production fresh/resume rank loop now lives in `mvsel2_selection_engine.py`; authenticated companion rank history removes post-validation historical rescoring for new MVSTATE2 checkpoints. Portable orchestration validation executed by the implementation agent: 5/5 tests passed in 0.11 s, covering fresh invariance, journal-backed replay-free resume, one-time legacy fallback, digest binding, and campaign routing. |
| G3 | PASS | Production/runtime REPAIR2 duplicate science removed. `target_multi_view_repair_v2.py` is the sole repair-science owner; the old checkpoint runtime is a deprecated delegation shim. Portable delegation/ownership validation executed by the implementation agent: 5/5 tests passed in 0.03 s; repository search found no caller of the retired per-rung helper. The canonical repair science itself was unchanged from the 51-test exact baseline. |
| G4 | IN_PROGRESS | Static/product-path review is active. Real target-scale throughput/RSS/page-fault acceptance remains to be measured on the production graph/cache. |

## Validation record

The protocol requires executed evidence; it does not require the project owner personally to operate every test. Tests that do not depend on the workstation, GPU, MACE installation, or production dataset are run by the implementation agent when a suitable execution environment is available.

Evidence accepted so far:

- exact project suite through G1: `51 passed in 3.84 s`;
- G2 portable orchestration suite: `5 passed in 0.11 s`;
- G3 portable delegation/ownership suite: `5 passed in 0.03 s`.

The temporary branch-local GitHub Actions workflow created while attempting an additional clean runner was removed after the connector could not provide a trustworthy run result; no CI success claim is based on that attempt.

## Gates

### G0 — stop regression and freeze baseline

- Mark `DOC-MVSEL2-PAR1` superseded.
- Restore production MVSEL2 execution to the single-worker authority regardless of campaign worker budget.
- Replace thread-scheduling evidence with a correctness/performance-contract regression that prevents reintroducing PAR1 implicitly.
- Record that the current real workstation observation is approximately 0.5x the prior throughput with PAR1.

**Pass:** the production campaign no longer routes Phase-A candidate scoring through PAR1 threading and scientific API compatibility is retained.

### G1 — canonical forward scoring kernel

- Introduce one cohesive forward scoring kernel using native CSR index dtype without unconditional `uint32 -> int64` row copies.
- Use reusable contiguous candidate score scratch arrays rather than per-candidate Python dictionaries where broad scans require scalar scores.
- During Phase A, avoid complete per-candidate Python family-gain tuples; use bounded contiguous FP64 scratch and materialize the winner score once.
- Implement family-major exact broad scans where they preserve canonical FP64 semantics; keep staged Phase-A pruning.
- Make the family-streaming Phase-B rebase canonical in the production selector engine and remove selector-side runtime monkeypatch installation.

**Pass:** focused oracle/equivalence tests produce identical choices/scores/rungs on existing fixtures; no inverse adjacency is touched.

### G2 — one selector/resume authority

- Collapse production fresh and resumable selection into one selector engine accepting an optional authenticated continuation state/history.
- Remove duplicated rank-loop ownership from the resume module; retain the original fresh builder only as an independent reference/oracle.
- Keep MVSTATE2 reconstruction validation independent.
- Persist/reuse a compact identity- and selected-prefix-bound rank journal containing only prior entries, completed rungs, and the Phase-A boundary.
- New checkpoints resume without historical scoring after MVSTATE2 validation; old checkpoints without a journal use one compatibility history reconstruction.

**Pass:** fresh and resumed execution are field-equivalent on focused fixtures; journal-backed resume does not invoke selected-prefix history replay; the campaign facade routes selection directly through the single-owner v5 runtime.

### G3 — one REPAIR2/runtime authority

- Keep exact per-rung repair execution in `target_multi_view_repair_v2.py` as the sole scientific owner.
- Reduce hardening/runtime modules to state lookup, invocation, persistence, and progress reporting.
- Remove import-time repair monkeypatching and duplicated repair loops/helpers.

The existing canonical `initial_states` continuation hook is not used for production selector-rung reuse in this gate. A pure-selector checkpoint at rung `N` would make that rung's active shell empty under the current hook, which can skip repair at that rung. G3 therefore fails closed to canonical rank-zero repair replay rather than preserving an unsafe cache optimization. If repair replay is material in G4, checkpoint consumption must be implemented inside the canonical repair owner and proven equivalent before being enabled.

**Pass:** production runtime contains no independent repair proposal/scoring/mutation loop; compatibility calls delegate to the canonical owner; repair scientific authority remains unchanged.

### G4 — product-path review and performance closeout

Run the smallest direct checks that establish the claims:

- focused MVSEL2 oracle/forward/state/resume/repair regressions;
- existing campaign-routing integration tests;
- review remaining legacy/reference-only selector machinery and remove any path that could accidentally restore PAR1 as production execution;
- representative Phase-A and Phase-B benchmark from the real production graph/cache when available;
- actual campaign continuation on the workstation for target-scale throughput/RSS/page-fault evidence.

Acceptance:

1. scientific choices and persisted authority remain exact;
2. no inverse MVSEL1 mutation or inverse-array paging is reintroduced;
3. PAR1 slowdown is eliminated;
4. sustained throughput is at least no worse than the accepted pre-PAR1 single-worker implementation, with further optimization accepted only when measured benefit justifies complexity;
5. no material RAM/disk regression;
6. journal-backed restart performs no second full selected-prefix replay after MVSTATE2 validation;
7. Protocol-5 independent review finds no remaining duplicated production execution authority or unjustified compatibility machinery in the affected subsystem.

If the clean Python/NumPy family-streaming kernel is still materially too slow at production scale, the next authorized escalation is a small compiled CSR scan kernel behind the same scoring interface. Do not add Python process/thread orchestration first.

## Non-goals

No change to target sizes, coverage threshold/tolerance, neighborhood geometry, scientific selector objectives, REPAIR2 policy, MVIDX1 scientific identity, MACE training policy, GPU training/evaluation behavior, or unrelated MLFF documentation migration.
