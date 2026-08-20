---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-V5-REDESIGN1
protocol_version: 5.0.0
status: G4_REDESIGN_IN_PROGRESS
analysis_base_ref: feat/mvsel2-forward-lazy
supersedes_execution_workplan: DOC-MVSEL2-PAR1
---

# DOC-MVSEL2-V5-REDESIGN1 — MVSEL2 forward-kernel and ownership redesign

## Objective

Restore and materially improve MVSEL2 production throughput without changing the frozen scientific selector/repair semantics, while reducing the accumulated execution and recovery complexity around MVSEL2.

The observed candidate-thread PAR1 implementation was a failed optimization. Product-path metering subsequently established that the sustained production cost is Phase-B lazy-frontier stale rescoring. G4 therefore proceeds only against measured Phase-B bottlenecks rather than adding worker/process machinery.

## Engineering envelope

Preserve exactly:

- exact MVIDX1 neighborhood semantics and forward-only MVSEL2/REPAIR2 runtime consumption;
- FP64 scientific arithmetic and the current `best - epsilon` contender rule;
- Phase-A hard-obligation, canonical bottleneck, total-coverage, correlation, representative, diversity, UID ordering;
- certified exact Phase-B representative frontier semantics;
- deterministic sequential authoritative mutation;
- nested rung/master-order semantics;
- MVSTATE2 restart correctness and REPAIR2 exact scientific behavior.

Production scale is approximately 36,408 candidates, 165 families, 9.505 billion forward candidate-witness edges, and requested prefixes through 16,384. The design must remain feasible without recreating MVSEL1 eager inverse marginal state or a second persistent global graph.

## Root-cause record

### PAR1

PAR1 parallelized Python candidate/family loops containing many small NumPy/memmap gathers and temporary allocations. The real workstation showed roughly 0.5x the prior observed throughput. Candidate threading is retired.

### G4a production meter — Phase-B lazy degeneracy

The first G4 product-path meter resumed at rank 1,024 directly in `representative_fill` and established:

- one exact Phase-B resume rebase took about 67 s;
- sustained throughput rose only to about 1.0 ranks/s;
- by rank 1,367, 343 new selections had accumulated 33,845,979,671 candidate-evaluation edges, about 98.7 million evaluation edges per accepted rank;
- mutation traffic over the same interval was only 94,102,845 edges;
- peak RSS was 83,665,652 KiB with 30,670 major faults;
- `.mdstats` remained 87 GiB before and after.

The failure was repeated sparse working-set traffic, not scratch growth.

### G4b production meter — witness-term arithmetic fix

Production Phase B was changed to cache one exact FP64 representative term per witness, `weight / (multiplicity + 1)`, updating only newly selected forward rows. The second product meter again resumed at rank 1,024 and established:

- Phase-B resume rebase fell from about 67 s to about 36 s;
- throughput reached 1.361 ranks/s by rank 1,113 and stabilized near 2.0 ranks/s, reaching 2.029 ranks/s by rank 2,603;
- by rank 2,603, 1,580 new selections had accumulated 151,376,661,218 candidate-evaluation edges, about 95.8 million evaluation edges per accepted rank;
- mutation traffic was 432,360,137 edges, about 0.274 million per accepted rank;
- the evaluation/mutation traffic ratio therefore remained roughly 350:1: arithmetic got cheaper but lazy-frontier edge demand did not materially change;
- peak RSS increased to 88,879,608 KiB with 42,918 major faults over the longer 20-minute run;
- filesystem input was 132,349,496 blocks and `.mdstats` remained exactly 87 GiB before/after;
- the run crossed the 2,048 rung, so the normal checkpoint/history callbacks should have published a new MVSTATE2 + authenticated rank-history pair for the next restart.

G4b therefore **passes the compute-throughput diagnosis but fails resource closeout**. The remaining problem is candidate-major sparse mmap locality / retained mapped working set.

## Chosen architecture

Use one production forward selection engine over the existing MVIDX1 forward view.

- Phase A: locality-oriented exact kernel with native CSR rows and bounded contiguous scratch.
- Phase B representative arithmetic: reconstructible per-witness FP64 term cache; no candidate marginal array and no inverse adjacency.
- Phase B stale rescoring: bounded top-of-heap batches, traversed family-major. Candidate IDs are sorted only within each family for CSR locality; each candidate still receives one FP64 family subtotal in canonical family order. After each family batch, that family's mmap pages are released.
- Lazy certification remains exact. Batch execution may refresh additional stale bounds earlier than scalar execution would, but this is reconstructible execution state only; scientific contender certification, score, UID tie-break, and authoritative mutation are unchanged.
- The scalar selector remains the independent exact oracle/reference.
- REPAIR2 scientific ownership remains solely in `target_multi_view_repair_v2.py`.

Do not add multiprocessing, a worker supervisor, GPU selector authority, a second persistent index, or MVSEL1-style complete candidate marginal arrays.

## Gate status

| Gate | Status | Current result |
|---|---|---|
| G0 | PASS | PAR1 marked failed/superseded; production stopped routing Phase A through Python candidate threading. |
| G1 | PASS | Workstation validation: 51 focused tests passed in 3.84 s; locality-oriented Phase-A kernel exact against scalar reference. |
| G2 | PASS | One production fresh/resume rank loop in `mvsel2_selection_engine.py`; authenticated rank history eliminates replay-only historical scoring for new checkpoints. |
| G3 | PASS | `target_multi_view_repair_v2.py` is the sole REPAIR2 scientific owner; runtime repair code is orchestration/delegation only. |
| G4 | REDESIGN_IN_PROGRESS | G4a exposed ~1.0 rank/s Phase-B degeneracy and ~83.7GB RSS. G4b witness-term caching restored ~2.0 ranks/s but RSS still reached ~88.9GB. Current gate tests bounded family-major stale rescoring plus mmap release. |

## Validation record

Accepted evidence before the current G4 locality gate:

- G1 workstation focused suite: `51 passed in 3.84 s`;
- G2/G3 focused/portable evidence established fresh/resume/journal/repair routing and ownership behavior;
- earlier thread-removal regression reported `73 passed, 1 warning in 15.06 s`; it predates the final native-row cleanup and remains historical only;
- G4a and G4b production meters are the current performance/resource evidence.

Witness-term exactness evidence:

- production Phase B routes directly through `mdstats/training_data/mvsel2_phase_b_kernel.py`;
- focused regression compares exact frontier initialization and repeated Phase-B choices against the scalar oracle after nonzero witness multiplicity and successive mutations;
- randomized FP64 checking established bitwise equality between direct `weight/(multiplicity+1)` row evaluation and summation of the precomputed per-witness terms.

Current family-major batch exactness contract:

- batching may change execution telemetry (`rescoring_count`, evaluation edges) because extra stale bounds may be refreshed early;
- it may not change selected candidate, exact candidate score, selected order, multiplicities, coverage masses, obligation counts, correlation counts, or representative utility;
- focused tests therefore compare scientific state/choices against the scalar oracle independently of execution telemetry.

## Gates

### G0 — stop regression and freeze baseline

Retire PAR1 and preserve scientific/API compatibility without Python candidate threading.

**Pass:** production no longer routes Phase-A candidate scoring through PAR1 threading.

### G1 — canonical forward scoring kernel

Use native CSR rows, bounded contiguous scratch, and family-major broad Phase-A scans while preserving the frozen comparator.

**Pass:** focused oracle/equivalence tests produce identical choices/scores/rungs; no inverse adjacency is touched.

### G2 — one selector/resume authority

Use one production rank loop for fresh/resumed selection and authenticated compact rank history for replay-free history reconstruction after MVSTATE2 validation.

**Pass:** fresh/resumed execution is field-equivalent and campaign routing points to the single production engine.

### G3 — one REPAIR2/runtime authority

Keep repair science in `target_multi_view_repair_v2.py`; runtime owns only I/O/authentication/invocation/persistence/resources/progress.

**Pass:** runtime contains no independent repair science and repair fixtures remain exact.

### G4 — product-path performance closeout

#### Completed

- executable PAR1 candidate threading removed;
- persisted CSR rows retain native integer dtype;
- Phase A uses the locality-oriented exact kernel;
- selector/resume and repair ownership consolidated;
- Phase-B lazy degeneracy measured on the real graph;
- per-witness representative-term cache restored roughly the lost factor-of-two compute throughput;
- resource evidence isolated candidate-major mmap locality as the remaining failure;
- bounded family-major stale-rescoring batches with per-family mmap release implemented.

#### Next validation

1. run the focused MVSEL2 oracle/forward/state/resume/repair/campaign-routing suite including the batched Phase-B oracle comparison;
2. rerun the normal product `prepare` path without deleting MVIDX1/MVSTATE2/history;
3. verify restart is now `resume_size=2048` and `resume_mode=mvstate2+journal`; otherwise diagnose restart persistence before using the performance result;
4. meter sustained Phase-B throughput, peak RSS, major faults, filesystem input, evaluation-edge count, and disk footprint;
5. compare against G4b: approximately 2.0 ranks/s, 88,879,608 KiB peak RSS, 42,918 major faults, and flat 87-GiB `.mdstats`.

#### Final acceptance

1. scientific choices and persisted authority remain exact;
2. no inverse MVSEL1 mutation or inverse-array paging is reintroduced;
3. PAR1 execution remains absent;
4. sustained real-graph throughput is at least no worse than the accepted pre-PAR1 observed single-worker throughput;
5. peak RSS / paging is materially reduced from G4b and compatible with the intended workstation resource envelope;
6. no material disk regression;
7. journal-backed selector restart performs no second historical rescoring after MVSTATE2 validation;
8. no duplicated production selector/repair scientific authority remains.

#### Escalation if family-major batching still fails

- If RSS falls but throughput collapses because repeated mmap release becomes I/O-bound, tune only the bounded batch/release cadence from measured evidence.
- If page pressure remains dominant, move representative batch summation behind a small compiled/native CSR kernel with explicit family-bounded traversal.
- If Python row-dispatch dominates despite bounded pages, use the same compiled/native CSR kernel; do not add threads/processes first.
- Add adaptive full frontier rebasing only if measured stale-bound looseness shows that a 9.5-billion-edge rebase amortizes its own cost.

Do not introduce approximation under the MVSEL2 authority.

## Non-goals

No change to target sizes, coverage threshold/tolerance, neighborhood geometry, scientific selector objectives, REPAIR2 policy, MVIDX1 scientific identity, MACE training policy, GPU training/evaluation behavior, or unrelated MLFF documentation migration.
