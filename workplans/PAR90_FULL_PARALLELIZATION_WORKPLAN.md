---
kind: implementation-workplan
workplan_id: PAR90
protocol_version: 5.2.0
---

# PAR90 Full Parallelization Workplan

## Objective

Make the campaign use the runtime-discovered CPU capacity consistently: the global automatic CPU budget is `floor(cpu_fraction * available_threads)` with production `cpu_fraction = 0.90`, and active stages may use any scientifically exact, RAM-safe, throughput-effective width inside that budget without host-specific 4/8/16/28 capacity ceilings.

## Diagnosis

`detect_system_resources()` already owns the correct runtime budget, including CPU affinity/cgroup restrictions, but downstream execution policies fragment that authority. Explicit `resolve_worker_count()` requests can currently use `cpu_threads_available` rather than `cpu_threads_budget`; `StageResourceScope` has no native/OpenMP width and MVSEL2 therefore mislabels native threads as Python workers; MVSEL2 inherits the TARGET-DATA2B cKDTree auto cap of eight and then applies a second ceiling of sixteen; its meter probes only 1/2/4/8/16 and fresh runs skip the real-graph preflight. REPAIR2 similarly inherits the cKDTree resolver while its v2 proposal loop remains serial. MVQUAL and structural selection retain historical small automatic caps, and MVIDX OOC admission contains an eight-lane assumption. These are execution-policy defects, not scientific-policy requirements.

## Design

### Resource invariant

Let `N_available` be the runtime CPU availability after process affinity and cgroup constraints. The single campaign CPU capacity is

`B_cpu = max(1, floor(cpu_fraction * N_available))`, with default `cpu_fraction = 0.90`.

Every active stage satisfies `effective <= authorized <= B_cpu`. Explicit stage worker settings are caps within `B_cpu`; changing `cpu_fraction` is the only supported way to change the campaign-wide fraction. Fewer effective workers are valid only because of task count, RAM/I/O admission, backend availability, a scientific serial mutation boundary, or measured throughput saturation.

Nested/concurrent execution shares one budget. Prefer one parallel layer: broad deterministic outer work queues with inner BLAS/tree/OpenMP width one where independent coarse work exists. Native kernels may use the budget directly when they are the single parallel layer. Runtime resource/tuning decisions remain execution-only and must not enter scientific digests.

### Scientific invariants

- MVSEL2: identical rank history/master order; exact FP64 Phase-B parity across qualified native widths.
- REPAIR2: identical shortlist, proposal metrics, accepted swap trace, repaired master order, rung coverage, and digest.
- MVIDX: identical scientific CSR/CSC content and digest.
- TARGET-DATA2C v5 coverage, MVQUAL, and structural selection: identical scientific authorities/digests.
- Old TARGET-DATA2C v4 rescue machinery is compatibility-only and is not a PAR90 optimization target.

### Complexity policy

Reuse `SystemResourceSnapshot`, `StageResourceScope`, and `DeterministicWorkQueue`. Extend their semantic ownership rather than adding another scheduler. Remove superseded cKDTree-worker reuse, fixed CPU capacity ceilings, and misleading unused worker plumbing after replacements qualify.

## Acceptance

- Runtime affinity/cgroup tests establish the 90% budget without host-specific constants.
- Explicit worker requests cannot exceed `cpu_threads_budget`.
- Resource scopes accurately model Python, structural, tree, BLAS, native/OpenMP, and PyTorch widths.
- No active production path contains an unexplained 4/8/16 CPU capacity ceiling.
- Fresh and resumed MVSEL2 use qualified native capacity from the real runtime budget.
- Concurrent sibling pools collectively stay within the same stage budget.
- Scientific equivalence/determinism tests pass at serial, selected effective, and budget-endpoint widths where applicable.
- Representative product-path timing does not regress; performance claims use comparable workloads.
- Clean source/editable/wheel native import paths are exercised where environment support exists. GPU qualification remains deferred to the final release workflow.

## Implementation sequence

### PAR90-G0 — Baseline and invariant tests

Capture focused product-path/resource baselines and add tests that freeze the resource, determinism, and digest invariants required by later gates.

### PAR90-G1 — Canonical 90% worker authority

Make `SystemResourceSnapshot.cpu_threads_budget` the sole automatic CPU capacity; make explicit stage requests cap inside that budget; remove local reconstructions/semantic reuse of the cKDTree worker resolver by unrelated stages.

### PAR90-G2 — Correct nested/native resource accounting

Extend `StageResourceScope` with explicit native/OpenMP width and separate it from Python-worker ownership. Preserve one-parallel-layer admission and prevent nested oversubscription.

### PAR90-G3 — MVSEL2 Phase-B full-budget execution

Decouple MVSEL2 from TARGET-DATA2B cKDTree workers, remove the 16-worker ceiling, generate logarithmic-plus-budget runtime meter widths, fix fresh-run qualification, and select the smallest width within a small tolerance of best measured throughput while retaining bitwise FP64 parity.

### PAR90-G4 — MVSEL2 Phase-A hotspot optimization

Profile the Phase-A primitives on representative density, then parallelize/vectorize/compile the largest exact read-only primitive. Do not revive the previously regressive Python fine-grain thread design. Preserve the serial lexicographic authority and complete selection identity.

### PAR90-G5 — REPAIR2 ownership and proposal parallelism

Give REPAIR2 its own budget derived from the shared resource snapshot. After the existing state-invariant/frontier factorization, parallelize immutable proposal evaluation using deterministic result ordering and one serial authoritative mutation. Escalate to a native primitive only if Python concurrency remains materially ineffective.

### PAR90-G6 — Coverage/MVIDX/MVQUAL/structural capacity cleanup

Use full-budget outer family/block parallelism with inner cKDTree width one where appropriate; replace MVIDX's fixed eight-lane OOC memory assumption with actual per-task RAM admission; remove MVQUAL and structural automatic 4/8 capacity ceilings and let bounded runtime scaling select economical effective widths.

### PAR90-G7 — Concurrent pipeline budget partitioning

Ensure prepare/inference/finalize and any sibling pools partition one aggregate CPU budget rather than independently claiming 90%. Retain small DataLoader/side-pool widths when they are throughput-effective rather than treating CPU occupancy as the objective.

### PAR90-G8 — End-to-end qualification and consolidation

Exercise fresh/resumed campaign paths under multiple affinity/cgroup budgets, RAM constraints, native source/editable/wheel installs, and representative production-density inputs. Compare end-to-end prepare wall time, then delete obsolete worker-cap/authority paths and reconcile durable architecture documentation if the accepted contracts changed.

## Risks / redesign triggers

- If a Python-threaded hotspot fails to scale because of GIL/small-kernel overhead, stop adding concurrency wrappers and move only the measured primitive to an exact native/shared-memory implementation.
- If memory or I/O bandwidth saturates before `B_cpu`, retain the smaller measured effective width and report the reason; do not hard-code the observed host count as global capacity.
- If native exactness cannot preserve the established scientific reduction convention, keep that reduction in the trusted reference path and optimize surrounding independent work instead of relaxing fidelity.
- If concurrent pipeline stages require dynamic CPU redistribution to avoid GPU starvation, extend the existing stage resource planner; do not create a second global scheduler.

## Implementation status — 2026-08-22

- G0: resource/scientific invariants frozen in focused tests; historical production-density MVSEL2 evidence plus a local synthetic Phase-A benchmark establish the optimization target without changing scientific policy.
- G1-G2: complete. Explicit workers are capped by `cpu_threads_budget`; `StageResourceScope` owns native/OpenMP width explicitly.
- G3-G4: complete. MVSEL2 uses the runtime CPU budget, dynamic logarithmic-plus-endpoint native metering, fresh-state preflight, and exact native Phase-A CSR reductions.
- G5: complete. REPAIR2 owns its resource budget and evaluates immutable shortlist proposals through `DeterministicWorkQueue` with canonical serial winner/mutation authority.
- G6: complete. Active cKDTree/MVQUAL/structural capacity ceilings and the MVIDX eight-lane OOC assumption are removed; structural autotuning probes through the runtime endpoint.
- G7: complete. Evaluation prepare/inference/finalize share one aggregate CPU budget, including process-wide native-thread width; a one-thread budget serializes all three stages.
- G8: focused CPU/resource/native/determinism suites pass in the available container; source native build and clean wheel install/import both qualify the OpenMP backend. Full repository tests and production-scale timing remain workstation qualification because this container does not provide the required `mace` Conda environment/ASE dependency. GPU qualification remains deferred by project policy.
