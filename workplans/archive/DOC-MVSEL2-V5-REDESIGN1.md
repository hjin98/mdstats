---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-V5-REDESIGN1
protocol_version: 5.0.0
status: DONE
analysis_base_ref: feat/mvsel2-forward-lazy
supersedes_execution_workplan: DOC-MVSEL2-PAR1
completed_date: 2026-08-20
---

# DOC-MVSEL2-V5-REDESIGN1 — completed MVSEL2 exact native Phase-B redesign

## Terminal decision

DONE. G4-N0 through G4-N3 are closed.

The accepted production design keeps MVSEL2 scientific and persistence authority in Python while moving only the repeated family-local candidate-row scoring primitive into a private CPython C/OpenMP extension. Authoritative lazy-frontier certification, contender formation, correlation/diversity/UID tie handling, mutation, checkpointing, and restart remain deterministic and sequential in Python.

The backend consumes the existing authenticated forward-only MVIDX1 CSR and creates no inverse adjacency, second graph, or persistent candidate-marginal authority. `workers=1` retains the proven G4b Python/NumPy execution path; parallel execution is enabled only after bitwise native qualification and bounded real-MVIDX scaling preflight.

## Scientific invariants preserved

The completed implementation preserves:

- exact MVIDX1 neighborhood semantics and forward-only MVSEL2/REPAIR2 consumption;
- FP64 representative arithmetic and the existing contender tolerance;
- canonical family-order accumulation;
- certified lazy-frontier semantics;
- deterministic sequential authoritative mutation;
- nested rung/master-order semantics;
- MVSTATE2 + authenticated journal restart semantics;
- REPAIR2 scientific ownership in `target_multi_view_repair_v2.py`;
- no approximation, inverse adjacency, second persistent graph, multiprocessing selector authority, or GPU selector authority.

The native row reducer reproduces NumPy's deterministic FP64 pairwise summation order and is compiled with strict floating-point flags. OpenMP distributes independent candidate rows only; it does not parallelize or reorder a single row reduction or authoritative selection decision.

## Historical performance decisions

### G4a/G4b

Phase-B repeated exact representative rescoring was identified as the dominant product cost. Caching one FP64 term per witness, `weight/(multiplicity+1)`, produced the proven G4b baseline of about 2.0 ranks/s and approximately 95.8 million candidate-evaluation edges/rank.

### G4c/G4d rejected

Aggressive mmap page release reduced residency but caused release/refault churn, high system time and filesystem input, and only about 1.6--1.7 ranks/s. Those policies remain retired.

### G4-N0/G4-N1/G4-N2

The implementation restored G4b serial semantics, added the exact private native row scorer, added bitwise qualification, routed campaign workers through the native execution path, and added a bounded real-MVIDX preflight with automatic G4b fallback if parallel speedup is below 1.75x.

## G4-N3 product qualification

Raw evidence is preserved in:

- `g4n3-mvsel2.txt`
- `g4n3-time.txt`
- `g4n3-disk-before.txt`
- `g4n3-disk-after.txt`

The normalized closeout record is `benchmarks/mvsel2_g4n3_native_closeout.md`.

Real-MVIDX preflight over 64,869,475 edges:

- 1 worker: 0.037 s, 1.00x
- 2 workers: 0.024 s, 1.56x
- 4 workers: 0.016 s, 2.34x
- 8 workers: 0.014 s, 2.59x

The 2.59x result passed the 1.75x activation threshold and selected 8 workers.

Product execution from the journal-backed 2,048 state to 16,384:

- `resume_mode=mvstate2+journal`
- `phase_b_backend=native-openmp`
- effective workers: 8
- selection progress time: 00:06:17
- final throughput: 37.996 ranks/s
- complete MVSEL2 acceptance time: 00:10:12
- checkpoints: 7
- cumulative candidate-evaluation edges: 1,031,737,100,160
- approximately 72.0 million candidate-evaluation edges/new rank

Relative to G4b, sustained rank throughput improved by roughly 19x and candidate-evaluation edge demand fell by roughly 25%.

The enclosing 20-minute command continued into REPAIR2, so its 90,532,644 KiB peak RSS is not an isolated MVSEL2 measurement. Whole-command evidence nevertheless showed zero swap and an unchanged 87G `.mdstats` footprint before/after, with no second graph.

## Gate status

| Gate | Terminal status | Result |
|---|---|---|
| G4-N0 | PASS | Proven G4b serial cached-witness path restored. |
| G4-N1 | PASS | Exact native row scorer and strict bitwise runtime qualification established. |
| G4-N2 | PASS | Real-MVIDX preflight measured 2.59x best parallel speedup and selected 8 workers. |
| G4-N3 | PASS | Product selector reached 37.996 ranks/s and accepted the full 16,384 authority with exact journal restart semantics. |

## Accepted extension boundary

Future MVSEL2 work should not reopen this design merely for incremental tuning. Reopen only if one of the following is demonstrated on the real product path:

- scientific/parity failure;
- restart/persistence failure;
- material memory or I/O regression attributable specifically to MVSEL2;
- a downstream requirement that invalidates the current forward-only interface;
- a new whole-system profile showing MVSEL2 again dominates preparation wall time.

Any future native targets must use the package-wide native build registry rather than one-off build machinery.

## Handoff

The G4-N3 run moved the measured bottleneck downstream. MVSEL2 completed before the external timeout; REPAIR2 reported rungs 128/256/512 with zero proposals and then did not report the next rung before the 20-minute command timeout. REPAIR2 performance therefore moves to the successor workplan.
