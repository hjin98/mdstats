---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-V5-REDESIGN1
protocol_version: 5.0.0
status: G4_NATIVE_PARALLELIZATION_IN_PROGRESS
analysis_base_ref: feat/mvsel2-forward-lazy
supersedes_execution_workplan: DOC-MVSEL2-PAR1
---

# DOC-MVSEL2-V5-REDESIGN1 — MVSEL2 exact native Phase-B execution plan

## Objective

Restore the last proven ~2.0 ranks/s Phase-B implementation, then move the exact Phase-B representative scoring primitive into a narrow native/OpenMP backend without changing MVSEL2 science, persistence, restart, or repair authority.

The optimization target is the sustained production Phase-B path on the real MVIDX1 graph, not a synthetic candidate-thread loop.

## Engineering envelope

Preserve exactly:

- exact MVIDX1 neighborhood semantics and forward-only MVSEL2/REPAIR2 consumption;
- FP64 representative arithmetic and the current `best - epsilon` contender rule;
- canonical family-order accumulation for every candidate;
- certified lazy-frontier semantics, correlation preference, sparse-diversity tie handling, and UID terminal tie-break;
- deterministic sequential authoritative mutation;
- nested rung/master-order semantics;
- MVSTATE2 + authenticated journal restart semantics;
- REPAIR2 scientific ownership in `target_multi_view_repair_v2.py`.

Production scale is approximately 36,408 candidates, 165 families, 9.505 billion forward candidate-witness edges, and target prefixes through 16,384. Persisted family CSR remains `uint64` offsets + `uint32` witness indices. No inverse adjacency, complete candidate marginal array, or second persistent graph may be introduced.

## Evidence and decisions

### PAR1 — rejected

Python candidate threading approximately halved real throughput. It remains retired.

### G4a — Phase-B stale rescoring identified

The real product showed roughly 1.0 ranks/s with about 98 million candidate-evaluation edges per accepted rank. Mutation traffic was tiny by comparison. The dominant cost is repeated exact representative rescoring.

### G4b — accepted performance baseline

Caching one FP64 term per witness, `weight / (multiplicity + 1)`, restored roughly 2.0 ranks/s and reduced the resume rebase from about 67 s to about 36 s. This is the baseline to restore before native work.

G4b retained high mapped-page residency (~88.9 GB peak RSS), but it is the last proven compute-efficient exact implementation.

### G4c — rejected release policy

Family-major stale batches with `MADV_DONTNEED` after every batch reduced peak RSS to ~76.6 GB but throughput fell to ~1.7 ranks/s while system time, minor faults, and filesystem input increased sharply. The release/refault churn was unacceptable.

### G4d — rejected release-cadence follow-up

The once-per-accepted-rank release policy did not recover G4b performance. The latest product meter still remained in the ~1.6–1.7 ranks/s regime and reported:

- 20:01.94 wall time under the expected timeout;
- 800.65 s user time and 341.05 s system time;
- 80,133,136 KiB peak RSS;
- 37,024 major faults and 61,032,452 minor faults;
- 152,034,240 filesystem input blocks;
- correct `resume_size=2048` and `resume_mode=mvstate2+journal`.

Decision: remove the batched stale rescoring/release experiment and restore the exact G4b candidate-local cached-witness path before native execution is introduced.

## Chosen architecture

Use one production selector engine and one scientific Python oracle/reference.

### Python semantic owner

Python continues to own:

- lazy-heap certification;
- canonical family traversal;
- exact contender formation;
- correlation/diversity/UID tie handling;
- authoritative selection mutation;
- checkpoint/history persistence and restart.

### Native execution owner

Add one small private CPython C extension for the repeated family-local operation:

```text
score_family_batch(offsets_u64,
                   witnesses_u32,
                   terms_f64,
                   candidates_u32,
                   output_f64,
                   workers)
```

The extension receives existing authenticated forward CSR buffers directly; it creates no persistent scientific state.

Parallelization unit:

- keep the Python outer loop family-major;
- within one active family, parallelize independent candidate rows with OpenMP;
- one worker owns one complete candidate row;
- never parallel-reduce within a row;
- never parallelize authoritative selection/mutation;
- use static scheduling for deterministic work assignment.

This avoids PAR1-style Python dispatch and avoids concurrently streaming unrelated family mmaps.

### Exact FP64 reduction contract

The current oracle evaluates each family subtotal as:

```python
np.sum(terms[witnesses], dtype=np.float64)
```

The native backend may become authoritative only if it is bitwise identical to that reduction for supported execution. Ordinary C left-to-right summation and OpenMP reduction are not acceptable substitutes.

Implement the NumPy-compatible deterministic pairwise FP64 row reducer and compile without fast-math/reassociation. Runtime qualification must compare native results bitwise against NumPy before native authority is used. If qualification fails, the backend is unavailable; do not silently weaken the numerical contract.

### Portability and fallback

- The extension is private and optional at package-build level.
- `workers=1` may fall back to the exact Python/NumPy G4b path if the extension is unavailable.
- `workers>1` requires a qualified native OpenMP backend and fails clearly if it is unavailable.
- No new runtime dependency such as Numba, Cython, pybind11, or CFFI is introduced.

## Gates

### G4-N0 — restore G4b baseline

Remove the G4c/G4d stale-batch machinery and rank-level mmap release from the production Phase-B path. Restore candidate-local cached-witness rescoring exactly as in the proven G4b implementation.

**Pass:** source again contains no Phase-B stale-batch executor and no per-rank forward-page release; oracle behavior remains unchanged.

### G4-N1 — exact native family scorer

Add the private C extension and Python wrapper.

Requirements:

- direct buffer access to canonical `uint64` offsets, `uint32` witnesses, FP64 terms, and `uint32` candidate IDs;
- no NumPy C API dependency required for the kernel;
- deterministic NumPy-compatible FP64 pairwise reduction;
- bounds/type/shape validation sufficient to prevent unsafe native access;
- no fast-math or reassociation;
- private runtime qualification covering row lengths around pairwise boundaries and realistic production lengths;
- bitwise equality against the Python NumPy oracle before native execution is accepted.

Integrate the same family scorer into both:

- full Phase-B frontier rebase;
- stale candidate rescoring.

At this gate, `workers=1` is sufficient to establish numerical authority.

**Pass:** focused native-vs-NumPy tests and repeated selector/oracle tests are bitwise/scientifically identical.

### G4-N2 — deterministic OpenMP candidate parallelism

Enable OpenMP only across independent candidate rows within one active family.

Requirements:

- `workers=1,2,4,8,16` produce bitwise-identical family outputs where supported;
- selected candidate, exact score, selected order, multiplicities, coverage masses, obligation counts, correlation counts, representative utility, and rungs remain identical to the scalar oracle;
- backend and active worker count are visible in selector progress telemetry;
- no Python thread/process pool is added.

A small real-MVIDX scorer meter should compare 1/2/4/8/16 workers through the production native primitive, allowing worker-count selection without five full campaign runs.

**Pass:** best worker count shows material scaling on the real graph; target is >=1.75x over native one-thread scorer throughput before a full campaign meter is justified.

### G4-N3 — one product-path closeout meter

Using the best qualified worker count from N2, run the normal product `prepare` path from the existing journal-backed checkpoint.

Measure separately:

- Phase-B resume rebase wall time;
- post-rebase delta-rank/delta-time sustained throughput;
- peak RSS and swap;
- user/system time;
- major/minor faults;
- filesystem input normalized by accepted rank or evaluated billion edges;
- evaluation-edge demand;
- `.mdstats` size;
- restart mode.

Acceptance targets:

1. scientific behavior remains exact;
2. restart remains `mvstate2+journal` without historical rescoring;
3. sustained product throughput materially exceeds G4b; design target >=4 ranks/s and minimum native-specialization justification >=3 ranks/s;
4. peak RSS does not exceed the G4b ~88.9 GB baseline and no swap occurs;
5. G4c/G4d release/refault pathology does not return;
6. disk remains bounded with no second graph;
7. no duplicated selector/repair scientific authority is introduced.

## Redesign triggers after N3

- If native one-thread is much faster than Python and OpenMP scales well, retain the native backend.
- If native one-thread is faster but OpenMP is nearly flat, the next limit is memory latency/bandwidth; stop thread tuning and examine exact stale-edge reduction/adaptive rebase.
- If native one-thread is only marginally faster than G4b, Python dispatch is not the dominant remaining cost; stop native tuning and redesign the exact lazy-bound/rebase policy.
- If native/OpenMP improves compute but faults/RSS become unacceptable, revisit page/block lifecycle without multiprocessing or inverse state.
- Adaptive full frontier rebasing is considered only after the native rebase cost is measured; it must remain exact and must amortize its own 9.5B-edge scan.

Do not introduce approximation under MVSEL2 authority.

## Non-goals

No change to target sizes, coverage threshold/tolerance, neighborhood geometry, target/reference scientific identity, REPAIR2 policy, MACE training policy, GPU training/evaluation behavior, or unrelated documentation migration.
