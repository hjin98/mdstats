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

The observed candidate-thread PAR1 implementation was a failed optimization. Subsequent product-path metering established that the currently dominant production cost is not Phase-A threading but Phase-B lazy-frontier stale rescoring. The redesign therefore continues at the measured bottleneck rather than adding more worker/process machinery.

## Engineering envelope

Preserve exactly:

- exact MVIDX1 neighborhood semantics and forward-only MVSEL2/REPAIR2 runtime consumption;
- FP64 scientific arithmetic and the current `best - epsilon` contender rule;
- Phase-A hard-obligation, canonical bottleneck, total-coverage, correlation, representative, diversity, UID ordering;
- certified exact Phase-B representative frontier semantics;
- deterministic sequential authoritative mutation;
- nested rung/master-order semantics;
- MVSTATE2 restart correctness and REPAIR2 exact scientific behavior.

Production scale is approximately 36,408 candidates, 165 families, 9.505 billion forward candidate-witness edges, and requested prefixes through 16,384. The design must remain feasible on the workstation without recreating MVSEL1 eager inverse marginal state or a second persistent global graph.

## Root-cause record

### PAR1

PAR1 parallelized Python candidate/family loops containing many small NumPy/memmap gathers and temporary allocations. The real workstation showed roughly 0.5x the prior observed throughput. Candidate threading is retired.

### G4 production meter — Phase-B lazy degeneracy

The first G4 product-path meter resumed at rank 1,024 directly in `representative_fill` and therefore did not exercise Phase-A selection as the sustained workload. It established:

- one exact Phase-B resume rebase took about 67 s;
- after rebase, sustained throughput rose only to roughly 0.7-1.0 ranks/s;
- sampled accepted ranks rescored roughly 196-825 stale candidates each;
- sampled candidate-evaluation traffic was roughly 54-225 million forward edges per accepted rank;
- by rank 1,367, 343 new selections had accumulated 33,845,979,671 candidate-evaluation edges, over 3.5 complete equivalents of the 9.505-billion-edge graph;
- mutation traffic over the same interval was only 94,102,845 edges, confirming candidate evaluation rather than authoritative state mutation as the bottleneck;
- peak RSS reported by `/usr/bin/time -v` was 83,665,652 KiB with 30,670 major faults and heavy filesystem input;
- `.mdstats` remained 87 GiB before and after, so the failure is repeated working-set/graph traffic rather than scratch growth.

This is the lazy-degeneracy failure mode anticipated by the original MVSEL2 design. G4 therefore failed its throughput/resource acceptance and remains open.

## Chosen architecture

Use one production forward selection engine over the existing MVIDX1 forward view.

- Phase A: locality-oriented exact kernel with native CSR rows and bounded contiguous scratch.
- Phase B: certified exact lazy frontier with a reconstructible **per-witness FP64 representative-term execution cache**. For each witness, cache `weight / (multiplicity + 1)` once and update it only along newly selected forward rows. Stale candidate rescoring then performs native CSR gather + canonical FP64 sum instead of repeated multiplicity widening, temporary allocation, and division on every candidate edge.
- The witness-term cache is derived execution state only. It is not persisted, not included in scientific identity, and is reconstructible from MVSTATE2 multiplicities.
- The scalar selector remains the independent exact oracle/reference.
- REPAIR2 scientific ownership remains solely in `target_multi_view_repair_v2.py`.

Do not add multiprocessing, a worker supervisor, GPU selector authority, a second persistent index, or MVSEL1-style complete candidate marginal arrays.

A deterministic queue-rebase policy remains an available later execution optimization, but it will not be enabled blindly: a full production rebase itself scans approximately 9.5 billion edges, so the witness-term kernel is measured first. If stale-edge traffic remains dominant after per-edge cost reduction, the next redesign should batch/family-stream stale rescoring or introduce a small compiled CSR scan kernel before adding repeated global rescans.

## Gate status

| Gate | Status | Current result |
|---|---|---|
| G0 | PASS | PAR1 marked failed/superseded; production stopped routing Phase A through Python candidate threading. |
| G1 | PASS | Workstation validation: 51 focused tests passed in 3.84 s; locality-oriented Phase-A kernel exact against scalar reference. |
| G2 | PASS | One production fresh/resume rank loop in `mvsel2_selection_engine.py`; authenticated rank history eliminates replay-only historical scoring for new checkpoints. |
| G3 | PASS | `target_multi_view_repair_v2.py` is the sole REPAIR2 scientific owner; runtime repair code is orchestration/delegation only. |
| G4 | REDESIGN_IN_PROGRESS | First real-graph trial failed: sustained Phase B remained ~0.7-1.0 ranks/s with 33.85B evaluation edges over 343 ranks and ~83.7GB peak RSS. Production Phase B now routes through the exact witness-term cached kernel; focused exactness regression and a second bounded workstation meter are required. |

## Validation record

Accepted evidence before the current G4 redesign:

- G1 workstation focused suite: `51 passed in 3.84 s`;
- G2/G3 focused/portable evidence established fresh/resume/journal/repair routing and ownership behavior;
- earlier thread-removal regression reported `73 passed, 1 warning in 15.06 s` and no executable PAR1 source path;
- final native-row cleanup occurred after that 73-test run, so the old test result is historical rather than final-G4 evidence.

G4 production evidence is authoritative for performance and failed acceptance as described above.

For the witness-term redesign:

- production Phase B is implemented in `mdstats/training_data/mvsel2_phase_b_kernel.py`;
- `mvsel2_selection_engine.py` routes directly to this kernel; no import-time monkeypatch is used;
- a focused regression compares exact frontier initialization and repeated Phase-B choices against the scalar oracle after nonzero witness multiplicity and successive state mutations;
- an independent randomized FP64 check confirmed bitwise equality between direct per-row `weight/(multiplicity+1)` evaluation and summation of the precomputed per-witness terms.

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

#### Completed source/ownership work

- executable PAR1 candidate threading removed;
- persisted CSR rows retain native integer dtype;
- Phase A uses the locality-oriented exact kernel;
- selector/resume and repair ownership consolidated;
- Phase-B product-path degeneracy measured on the real MVIDX1 graph;
- Phase-B witness-term execution cache implemented without changing scientific/persistence authority.

#### Next validation

1. run the focused MVSEL2 oracle/forward/state/resume/repair/campaign-routing regressions including the new cached Phase-B oracle comparison;
2. run a bounded product-path meter from the existing rank-1,024 checkpoint against the same persisted MVIDX1 graph;
3. measure the first Phase-B rebase plus roughly 200-350 accepted Phase-B ranks, then stop if the rate has clearly stabilized;
4. compare throughput, candidate-evaluation edges, rescoring counts, peak RSS/page faults, and disk footprint to the failed first G4 trial.

#### Final acceptance

1. scientific choices and persisted authority remain exact;
2. no inverse MVSEL1 mutation or inverse-array paging is reintroduced;
3. PAR1 execution remains absent;
4. sustained real-graph throughput is at least no worse than the accepted pre-PAR1 observed single-worker throughput;
5. no material RAM/disk regression;
6. journal-backed selector restart performs no second historical rescoring after MVSTATE2 validation;
7. no duplicated production selector/repair scientific authority remains.

#### Escalation if the witness-term meter still fails

Use the measured result to choose exactly one next kernel change:

- if arithmetic cost falls but graph/page traffic remains dominant: implement exact batched/family-major stale-candidate rescoring;
- if Python/NumPy per-row overhead remains dominant: implement a small compiled/native CSR representative-sum kernel behind the same Phase-B interface;
- only if measured stale-bound looseness proves that a rebase pays for itself: add a deterministic adaptive rebase trigger based on stale-rescore work.

Do not add Python process/thread orchestration first and do not introduce approximation under the MVSEL2 authority.

## Non-goals

No change to target sizes, coverage threshold/tolerance, neighborhood geometry, scientific selector objectives, REPAIR2 policy, MVIDX1 scientific identity, MACE training policy, GPU training/evaluation behavior, or unrelated MLFF documentation migration.
