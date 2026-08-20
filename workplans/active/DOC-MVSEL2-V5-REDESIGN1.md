---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-V5-REDESIGN1
protocol_version: 5.0.0
status: G4_AWAITING_PRODUCTION_METER
analysis_base_ref: feat/mvsel2-forward-lazy
supersedes_execution_workplan: DOC-MVSEL2-PAR1
---

# DOC-MVSEL2-V5-REDESIGN1 — MVSEL2 forward-kernel and ownership redesign

## Objective

Restore and materially improve MVSEL2 production throughput without changing the frozen scientific selector/repair semantics, while reducing the accumulated execution and recovery complexity around MVSEL2.

The observed candidate-thread PAR1 implementation is a failed optimization: on the real workstation it reduced throughput to roughly half of the prior single-worker path. Treat that as a redesign trigger, not a request for additional worker/process machinery.

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

PAR1 parallelized the wrong abstraction. Threads executed Python candidate/family loops containing many small NumPy/memmap gathers and temporary allocations. This added scheduling, allocator, page-cache, and memory-bandwidth contention without creating a coarse vector/compiled kernel.

Additional problems addressed by this redesign:

1. persisted `uint32` witness rows were repeatedly widened/copied to `int64` in the broad Phase-A path;
2. Phase A stored complete per-family Python gain tuples for every total-coverage contender although only the winner required the complete score;
3. broad scans traversed candidate-major across many mapped family arrays rather than streaming one family at a time;
4. Phase-B family-streaming execution was installed through runtime monkeypatching instead of the production selector engine;
5. normal and resumable selector builders duplicated substantial control flow;
6. checkpoint restore plus resume could replay/rescore the selected prefix again solely to reconstruct plan history;
7. REPAIR2 loop ownership was duplicated between the canonical repair module and runtime helpers;
8. the retired PAR1 `ThreadPoolExecutor` remained executable in the scalar/reference selector source even after production routing stopped using it.

## Chosen architecture

Use one production forward selection engine over the existing MVIDX1 forward view. Phase A uses the locality-oriented kernel; Phase B uses the family-streaming exact frontier; the authoritative mutation order remains sequential. MVSTATE2 remains compact continuation state, paired with an authenticated rank-history journal for replay-free plan-history reconstruction after checkpoint validation.

`target_multi_view_repair_v2.py` is the sole REPAIR2 scientific owner. Runtime code performs only persisted-forward lookup, checkpoint authentication needed by selector restart, invocation, resource scoping, persistence, and progress plumbing.

Do not add multiprocessing, a worker supervisor, GPU selector authority, a second persistent index, or MVSEL1-style complete candidate marginal arrays. PAR1 candidate threading is retired at the source: the retained scalar selector is an independent oracle/reference and ignores the positive `workers` value semantically.

## Gate status

| Gate | Status | Current result |
|---|---|---|
| G0 | PASS | PAR1 marked failed/superseded; production stopped routing Phase A through Python candidate threading. |
| G1 | PASS | Workstation validation supplied by project owner: 51 focused tests passed in 3.84 s. Locality-oriented Phase-A kernel is exact against the scalar reference. |
| G2 | PASS | One production fresh/resume rank loop lives in `mvsel2_selection_engine.py`; authenticated identity/prefix-bound rank history removes post-validation historical rescoring for new MVSTATE2 checkpoints. Independent clean runner: 56 passed in 5.78 s on Python 3.11.15. |
| G3 | PASS | Runtime duplicate REPAIR2 science removed; `target_multi_view_repair_v2.py` is the sole repair-science owner and the old checkpoint runtime is delegation-only compatibility. Independent expanded runner: 70 passed, 1 pre-existing warning, in 9.12 s. |
| G4 | AWAITING_PRODUCTION_METER | Executable PAR1 threading removed from the retained scalar/reference selector. Final clean runner: 73 passed, 1 pre-existing warning, in 15.06 s; explicit source scan `PAR1_SOURCE_PRESENT=0`. Only real production-graph throughput/RSS/page-fault acceptance remains. |

## Validation record

Executed evidence accepted so far:

- G1 workstation focused suite: `51 passed in 3.84 s`;
- G2 independent clean Python 3.11.15 runner: `56 passed in 5.78 s`;
- G3 independent clean Python 3.11.15 runner, including ownership and production-style repair integration: `70 passed, 1 warning in 9.12 s`;
- post-G4-source-cleanup independent runner: `73 passed, 1 warning in 15.06 s`;
- post-G4 source scan: `PAR1_SOURCE_PRESENT=0` for `ThreadPoolExecutor`, the MVSEL2 thread-name prefix, and `executor.map` in `target_multi_view_selector_v2.py`;
- clean editable installation succeeded using the package-declared scientific-Python dependencies plus pytest. No additional MACE/GPU/local-workstation dependency is required for these focused selector/repair tests.

The warning in the 70/73-test suites is the existing `VelocityReconstructionWarning` emitted by the VASP I/O path in `test_repair1_accepts_production_style_multifamily_target_data2b`; it is not an MVSEL2/REPAIR2 failure.

Temporary CI branches used to obtain independent execution evidence are not scientific or release authorities and must not be merged into the feature branch.

## Gates

### G0 — stop regression and freeze baseline

- Mark `DOC-MVSEL2-PAR1` superseded.
- Restore production MVSEL2 execution to the single-worker authority regardless of campaign worker budget.
- Replace thread-scheduling evidence with correctness/performance-contract regression.
- Record the real workstation PAR1 observation of approximately 0.5x the prior throughput.

**Pass:** production no longer routes Phase-A candidate scoring through PAR1 threading and API compatibility is retained.

### G1 — canonical forward scoring kernel

- Introduce a locality-oriented exact Phase-A kernel using native CSR integer dtype without unconditional `uint32 -> int64` row copies in the broad path.
- Use reusable contiguous score scratch arrays rather than per-candidate dictionaries where broad scans require scalar scores.
- Replace per-contender Python family tuples with bounded FP64 contender-by-family scratch and materialize the winner score.
- Traverse broad coverage family-major while preserving exact FP64 decision semantics.
- Use the family-streaming Phase-B rebase directly from the production selector engine.

**Pass:** focused oracle/equivalence tests produce identical choices/scores/rungs; no inverse adjacency is touched.

### G2 — one selector/resume authority

- Collapse production fresh and resumable selection into one selector engine accepting optional authenticated continuation state/history.
- Reduce the resume module to compatibility/delegation; retain the original fresh builder only as an independent reference/oracle.
- Keep MVSTATE2 reconstruction validation independent.
- Persist/reuse a compact identity- and exact-selected-prefix-bound rank journal containing prior entries, completed rungs, and the Phase-A boundary.
- New checkpoints resume without historical rescoring after MVSTATE2 validation; old checkpoints without a journal use one compatibility history reconstruction.

**Pass:** fresh/resumed execution is field-equivalent; journal-backed resume does not invoke selected-prefix history reconstruction; campaign routing points to the single production engine.

### G3 — one REPAIR2/runtime authority

- Keep exact per-rung repair execution in `target_multi_view_repair_v2.py` as the sole scientific owner.
- Reduce runtime modules to I/O, authentication helpers used by selection restart, invocation, persistence, resources, and progress.
- Remove import-time repair monkeypatching and the duplicate proposal/scoring/mutation loop.

Production REPAIR2 intentionally does not discover/reuse every pure-selector rung checkpoint. Authenticating each MVSTATE2 rung itself replays that selected prefix, so loading all nested checkpoints can add a cumulative historical scan before repair. Canonical rank-zero repair construction instead performs one sequential selected-prefix buildup while processing the repair rungs. A checkpoint optimization may be reconsidered only if target-scale metering demonstrates a material benefit and it is implemented inside the canonical repair owner with exact-equivalence evidence.

**Pass:** runtime contains no independent repair science; compatibility calls delegate to the canonical owner; repair fixtures and production-style integration remain exact.

### G4 — product-path review and performance closeout

Completed portable checks:

- focused MVSEL2 oracle/forward/state/resume/repair regressions;
- campaign routing and production-style repair integration;
- removal of executable PAR1 candidate threading from the retained scalar/reference selector;
- source assertion preventing `ThreadPoolExecutor`, `executor.map`, or the old MVSEL2 thread pool from returning;
- clean dependency installation and test execution outside the project workstation.

Remaining production-only meter:

- run the current branch against the already-persisted real production MVIDX1 graph/cache;
- record sustained Phase-A/Phase-B rank throughput, peak RSS, major page faults or equivalent paging evidence, and on-disk scratch growth;
- compare sustained throughput directly to the accepted pre-PAR1 single-worker implementation and to the failed PAR1 observation.

Final acceptance requires:

1. scientific choices and persisted authority remain exact;
2. no inverse MVSEL1 mutation or inverse-array paging is reintroduced;
3. PAR1 execution is absent and its slowdown is eliminated;
4. sustained real-graph throughput is at least no worse than the accepted pre-PAR1 single-worker implementation;
5. no material RAM/disk regression;
6. journal-backed selector restart performs no second historical rescoring after MVSTATE2 validation;
7. no duplicated production selector/repair scientific authority remains.

If the clean Python/NumPy family-streaming kernel remains materially too slow at production scale, the next authorized escalation is a small compiled CSR scan kernel behind the same scoring interface. Do not add Python process/thread orchestration first.

## Non-goals

No change to target sizes, coverage threshold/tolerance, neighborhood geometry, scientific selector objectives, REPAIR2 policy, MVIDX1 scientific identity, MACE training policy, GPU training/evaluation behavior, or unrelated MLFF documentation migration.
