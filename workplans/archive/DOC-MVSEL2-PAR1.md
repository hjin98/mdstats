---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-PAR1
protocol_version: 4.0.0
status: SUPERSEDED_FAILED
analysis_base_ref: feat/mvsel2-forward-lazy
superseded_by: DOC-MVSEL2-V5-REDESIGN1
---

# DOC-MVSEL2-PAR1 — MVSEL2 candidate-parallel CPU scoring

## Outcome

This execution design is retired. A real production workstation run showed that enabling the candidate-thread implementation reduced MVSEL2 throughput to roughly half of the prior single-worker path.

The observed result satisfies this workplan's own redesign trigger: practical threading scaling is poor. Do not add multiprocessing, shared-state worker machinery, or further Python candidate-thread tuning. `DOC-MVSEL2-V5-REDESIGN1` supersedes this plan and returns optimization to data movement, vectorized/streaming sparse kernels, and ownership consolidation under Software Development Protocol 5.

## Historical objective

Make the existing MVSEL2 `workers` setting perform useful multi-core CPU work without changing selector semantics, persistence identity, or authoritative state ownership.

## Historical design

The implementation used a standard-library `ThreadPoolExecutor` per Phase-A choice. Workers evaluated disjoint canonical candidate blocks against the same read-only forward MVIDX and immutable current selector state. Candidate-local FP64 reduction order and controlling-thread mutation remained unchanged.

The attempted parallel stages were bottleneck-family coverage gain, total coverage gain, representative gain, and diversity. Hard-obligation and correlation filtering remained serial.

## Failed acceptance

- Exact worker-count equivalence remained a required semantic contract.
- The focused regression demonstrated that multiple Python threads executed candidate scoring.
- The material acceptance requirement was a representative real Phase-A run showing useful multi-core speedup without material memory multiplication.
- The production observation instead showed an approximately 0.5x throughput ratio versus the prior single-worker path.

Therefore the performance acceptance criterion failed and the plan is closed as a failed optimization experiment.

## Redesign trigger reached

The likely causes are the ones anticipated by the original plan: Python/GIL overhead, many small NumPy operations, file-backed sparse page/cache pressure, allocator contention, and memory-bandwidth contention. The correct next action is kernel/data-layout redesign rather than more concurrency machinery.
