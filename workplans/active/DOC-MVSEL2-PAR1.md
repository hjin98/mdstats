---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-PAR1
protocol_version: 4.0.0
status: IN_PROGRESS
analysis_base_ref: feat/mvsel2-forward-lazy
---

# DOC-MVSEL2-PAR1 — MVSEL2 candidate-parallel CPU scoring

## Objective

Make the existing MVSEL2 `workers` setting perform useful multi-core CPU work without changing selector semantics, persistence identity, or authoritative state ownership.

## Diagnosis

MVSEL2 accepts and propagates `workers`, but the Phase-A scoring stages currently iterate candidates serially. A production run therefore consumes roughly one CPU core during the CPU-intensive selector despite a multi-worker campaign resource plan.

## Design

Use one standard-library `ThreadPoolExecutor` per Phase-A choice. Workers evaluate disjoint canonical candidate blocks against the same read-only forward MVIDX and immutable current selector state. Each candidate retains the existing canonical FP64 family-reduction order. `executor.map` preserves block order, after which the existing deterministic filtering and UID tie-break execute unchanged. The controlling thread remains the only owner allowed to mutate selector state.

Parallelize only the expensive independent Phase-A candidate stages in this pass:

- bottleneck-family coverage gain;
- total coverage gain;
- representative gain;
- diversity.

Keep hard-obligation and correlation filtering serial because they are cheap. Keep Phase-B lazy certification, REPAIR2, MVIDX construction, persistence, and scientific policy unchanged until real measurements justify further work.

## Acceptance

- [ ] `workers=1` and `workers>1` produce identical candidate scores, choices, telemetry, prefixes, rungs, and plan digests on focused fixtures.
- [ ] A focused regression demonstrates that `workers>1` actually executes candidate scoring on multiple threads.
- [ ] Existing MVSEL2 oracle, mutation, resume, checkpoint, forward-only, and REPAIR2 regressions remain passing.
- [x] The normal campaign still supplies its configured worker count to MVSEL2.
- [ ] A representative real Phase-A run shows materially greater than one-core CPU utilization without material memory multiplication.
- [ ] If practical scaling is poor despite active threading, stop and reconsider a compiled/vectorized kernel rather than adding process/shared-state machinery.

## Implementation sequence

- [x] Identify the single-owner read-only scoring boundary.
- [x] Design deterministic candidate-block threading with no new scientific state.
- [x] Implement owning-layer Phase-A candidate-block threading.
- [x] Add focused multi-thread-execution regression.
- [x] Publish implementation to `feat/mvsel2-forward-lazy`.
- [ ] Run focused MVSEL2 regressions.
- [ ] Run representative real Phase-A workload with multiple worker counts.
- [ ] Continue the real MLFF campaign if the production result is acceptable.

## Risks / redesign triggers

- Threading produces little material speedup because Python/GIL or memory bandwidth dominates.
- Worker-count scaling causes unacceptable page-fault pressure or temporary-array memory growth.
- Exact single-worker versus multi-worker identity changes.
- A proposed fix requires duplicated selector state, multiprocessing synchronization, another persistent graph, or a worker supervisor.

Any of these should trigger reconsideration rather than additional machinery.
