---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-V5-REDESIGN1
protocol_version: 5.0.0
status: G4_N3_PRODUCT_QUALIFICATION_PENDING
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

Caching one FP64 term per witness, `weight / (multiplicity + 1)`, restored roughly 2.0 ranks/s and reduced the resume rebase from about 67 s to about 36 s. G4b is the baseline retained for `workers=1` and for any native-scaling fallback.

G4b retained high mapped-page residency (~88.9 GB peak RSS), but it is the last proven compute-efficient exact implementation.

### G4c — rejected release policy

Family-major stale batches with `MADV_DONTNEED` after every batch reduced peak RSS to ~76.6 GB but throughput fell to ~1.7 ranks/s while system time, minor faults, and filesystem input increased sharply. The release/refault churn was unacceptable.

### G4d — rejected release-cadence follow-up

The once-per-accepted-rank release policy did not recover G4b performance. The latest product meter remained in the ~1.6–1.7 ranks/s regime and reported:

- 20:01.94 wall time under the expected timeout;
- 800.65 s user time and 341.05 s system time;
- 80,133,136 KiB peak RSS;
- 37,024 major faults and 61,032,452 minor faults;
- 152,034,240 filesystem input blocks;
- correct `resume_size=2048` and `resume_mode=mvstate2+journal`.

Decision: G4c/G4d mmap-release execution is removed from the production Phase-B path. Native work is layered on the exact G4b witness-cache baseline.

## Chosen architecture

Use one production selector engine and one scientific Python oracle/reference.

### Python semantic owner

Python continues to own:

- lazy-heap certification;
- canonical family traversal and candidate family-subtotal accumulation;
- exact contender formation;
- correlation/diversity/UID tie handling;
- authoritative selection mutation;
- checkpoint/history persistence and restart.

### Native execution owner

One private CPython C extension owns only the repeated family-local row scorer:

```text
score_family_batch(offsets_u64,
                   witnesses_u32,
                   terms_f64,
                   candidates_u32,
                   output_f64,
                   workers)
```

The extension consumes the existing authenticated MVIDX1 forward CSR and reconstructible FP64 witness-term cache directly. It creates no persistent scientific state.

Parallelization unit:

- Python remains family-major;
- within one active family, independent candidate rows are distributed with OpenMP `schedule(static)`;
- one worker owns one complete row;
- no within-row parallel reduction;
- no parallel authoritative selection/mutation;
- no Python thread/process pool.

### Exact FP64 reduction contract

The oracle family subtotal is:

```python
np.sum(terms[witnesses], dtype=np.float64)
```

The native row reducer reproduces NumPy's deterministic pairwise FP64 summation order: 128-element block cutoff, eight accumulators, recursive multiple-of-eight split, and the short-row `-0.0` initialization. Compilation explicitly disables fast-math/reassociation/FMA contraction where applicable.

The private runtime qualifier compares native output bitwise against NumPy around pairwise boundaries and realistic production row lengths before native execution can be used. OpenMP workers operate on different rows only, so worker count cannot change a row's accumulation order.

MVIDX1 already authenticates witness bounds when forward families are constructed. The native hot loop therefore does not recheck every witness edge; candidate/offset buffer safety remains checked at the native boundary and the Python owner supplies terms whose cardinality matches the authenticated family witness domain.

### Portability and fallback

- The extension is private and optional at package-build level.
- `workers=1` executes the proven G4b Python/NumPy path.
- `workers>1` requires a successfully built, runtime-qualified OpenMP backend.
- no Numba, Cython, pybind11, CFFI, multiprocessing, or GPU selector authority is added.
- the campaign's existing target-coverage worker budget remains the CPU resource authority; native MVSEL2 activation is capped at 16 workers until real-graph evidence justifies more.

## Gate status

| Gate | Status | Result / next boundary |
|---|---|---|
| G4-N0 | IMPLEMENTED | G4c/G4d stale-batch release path removed for serial execution; proven G4b candidate-local witness cache restored. |
| G4-N1 | IMPLEMENTED; LOW-LEVEL PARITY CHECKED | Private C extension, build hook, Python qualifier, exact NumPy-compatible reducer, and native-vs-oracle tests added. Independent Linux GCC/OpenMP compilation and 1/2/4/8/16 bitwise parity check succeeded; repository-focused pytest still must run in the source checkout. |
| G4-N2 | IMPLEMENTED; REAL-GRAPH PREFLIGHT PENDING | OpenMP candidate-row scoring is integrated for rebase and stale rescoring; runtime worker propagation, telemetry, regressions, and bounded real-MVIDX 1/2/4/8/16 preflight are implemented. The workstation run will execute this gate automatically before long selection. |
| G4-N3 | PENDING WORKSTATION PRODUCT METER | If N2 real-graph scaling clears 1.75x, the same `prepare` invocation continues with the fastest qualified worker count; otherwise it falls back automatically to G4b `workers=1`. |

## Implemented sequence

Key feature-branch commits, in order:

- `6b20233128257a9585734ee4dcc239ad134c8aed` — record failed G4d and native execution workplan;
- `7446fe63a0b4ffd10ae76668cfbfbd5037df3fbc` — G4-N0 restore proven cached Phase-B baseline;
- `c36bdacf0c19d53599981941951cd2c5c967b03a` — add exact native MVSEL2 row scorer;
- `6536a50cbf09a8fcced5b9d48643952778369eae` — wire private extension build;
- `4d1bea7a56a9afe9f68a2b9ec13371cf30dd004a` — add fail-closed native runtime qualifier/wrapper;
- `aa0995f18f466b27d867bacfbed31cbe63ecddef` — integrate native candidate-parallel Phase-B scoring;
- `f20acc1087d862fdeccaa28b77dfce6c56dc76e9` — route Phase-B workers/backend telemetry through the selection engine;
- `65c7fc6cd555169562e75472089889f3888737e8` — add native exactness/OpenMP selector regressions;
- `1857d21e04bcaaba5d355a8572fc3cb140a5294e` / `a165f0d86b6e3cd5490a5a62ec3f90f1d1219049` — route and resource-account campaign worker budget;
- `59b5192be5983da7adbd41fa7e718fb812760411` — add bounded real-MVIDX worker preflight;
- `9943702b5f8dcc5825f0d7aa17d7d4a67d0c61ff` — gate production workers through real-graph preflight;
- `8e0fa28a217db35bdc39986017b936f77a8a3e3b` — remove redundant per-edge native witness-bound branch;
- `aa791ed85fcf829be3a16c5b394161018e022883` — test preflight routing and G4b fallback.

## G4-N0 — restored baseline contract

Serial Phase B must remain the exact G4b path:

- per-witness FP64 term cache;
- candidate-local stale rescoring;
- no stale-batch execution in `workers=1`;
- no rank-level `MADV_DONTNEED`;
- full rebase remains family-major and may release a family only after its complete rebase scan.

## G4-N1 — native exactness qualification

Before the workstation product meter:

1. build the extension in place;
2. run the runtime qualifier;
3. run the focused MVSEL2/native/oracle/restart/repair suite.

Native authority is unavailable if bitwise qualification fails.

## G4-N2 — automatic real-MVIDX worker preflight

On a journal-backed restart with requested workers >1, the normal product path now performs a bounded execution-only preflight before the long selector:

1. choose 256 deterministic available candidates spanning the domain;
2. warm those exact rows once with native one-thread execution;
3. meter native 1/2/4/8/16 workers, capped by the authorized worker budget and native runtime capability;
4. run two timed passes per worker count and use the faster pass to reduce incidental timing noise;
5. require identical edge counts and bitwise-identical FP64 candidate scores across every tested worker count;
6. choose the fastest parallel count only if speedup over native one-thread is >=1.75x;
7. otherwise set effective workers to 1 and continue through the proven G4b path.

The preflight does not mutate selector state, does not persist results, and does not release/refault mappings between worker trials.

Expected progress evidence resembles:

```text
[TARGET-DATA2C-MVSEL2 native preflight] domain=...; sample=256; edges=...; meters=1w:.../1.00x,2w:...,...; best_parallel_speedup=...; threshold=1.75x; scaling=pass|fail; effective_workers=N
```

Normal selector progress additionally reports:

```text
phase_b_backend=python-numpy|native-openmp; phase_b_workers=N
```

## G4-N3 — one product-path closeout meter

Using the automatically selected effective worker count, continue the same normal `prepare` invocation from the existing journal-backed checkpoint.

Measure separately:

- Phase-B resume rebase wall time;
- post-rebase delta-rank/delta-time sustained throughput;
- peak RSS and swap;
- user/system time;
- major/minor faults;
- filesystem input normalized by accepted rank or evaluated billion edges;
- evaluation-edge demand;
- `.mdstats` size;
- restart mode;
- N2 preflight worker meter and selected worker count.

Acceptance targets:

1. focused exact tests pass;
2. native runtime qualifier passes;
3. scientific behavior and persistence remain exact;
4. restart remains `mvstate2+journal` without historical rescoring;
5. N2 native worker preflight shows >=1.75x best parallel speedup before native execution is retained;
6. sustained product throughput materially exceeds G4b; design target >=4 ranks/s and minimum native-specialization justification >=3 ranks/s;
7. peak RSS does not exceed the G4b ~88.9 GB baseline and no swap occurs;
8. G4c/G4d release/refault pathology does not return;
9. disk remains bounded with no second graph;
10. no duplicated selector/repair scientific authority is introduced.

## Redesign triggers after N3

- If the real-MVIDX preflight fails 1.75x scaling, the product automatically stays on G4b; remove or retain the native backend only as justified by native one-thread/rebase evidence, and move to exact stale-edge reduction/adaptive-rebase design rather than more thread tuning.
- If the preflight scales but sustained product throughput remains <3 ranks/s, Python dispatch is not the primary remaining bottleneck or batch early-refresh cost dominates; stop native tuning and redesign the exact lazy-bound/rebase policy.
- If native rebase becomes cheap enough, evaluate an exact adaptive frontier rebase only when the measured reduction in stale candidate-edge rescoring amortizes the full 9.5B-edge scan.
- If native execution improves compute but RSS/faults regress beyond G4b, revisit page/block lifecycle without multiprocessing, inverse state, or per-batch `MADV_DONTNEED`.

Do not introduce approximation under MVSEL2 authority.

## Non-goals

No change to target sizes, coverage threshold/tolerance, neighborhood geometry, target/reference scientific identity, REPAIR2 policy, MACE training policy, GPU training/evaluation behavior, or unrelated documentation migration.
