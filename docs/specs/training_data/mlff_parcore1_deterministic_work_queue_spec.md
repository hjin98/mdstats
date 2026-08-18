# MLFF PARCORE1 deterministic work-queue specification

**Release:** `mdstats 0.20.226a0`  
**Architecture revision:** 93  
**Gate:** `PARCORE1`  
**Authority:** execution optimization only; scientific authority unchanged

## 1. Scope

PARCORE1 defines the reusable CPU task scheduler for MLFF stages with independent exact work. It MUST NOT change scientific input identity, exact numerical kernels, canonical FP64 reduction order, target selection, training/evaluation semantics, or model authority. The active qualification uses MACE-MPA-0 medium, but the queue contains no foundation-specific behavior and SHALL support MACE-MH-1 without a scheduler-contract change.

## 2. Resource contract

`DeterministicWorkQueue` SHALL execute under one `StageResourceScope`. Simultaneously executing Python lanes MUST NOT exceed `python_workers`. When an explicit campaign scope is supplied, BLAS/OpenMP native pools are quarantined once at queue scope and workers MUST NOT independently toggle process-global native-thread limits. `ram_budget_bytes` is execution-only and participates in admission.

Ready, submitted/in-flight, and completed work SHALL be bounded independently. More futures MAY be submitted than executing lanes to hide coordinator hand-off latency, provided the executor thread count remains bounded by `python_workers` and memory admission succeeds.

## 3. Determinism contract

Every work item SHALL have a deterministic `task_id`, canonical-order key, task kind, memory estimate, and optional locality key. Task completion MAY occur out of order. `DeterministicOrderedReducer` SHALL commit FP-sensitive results only in the caller-provided canonical key sequence. Worker exceptions SHALL be re-raised with deterministic task identity.

## 4. Memory/backpressure contract

The queue SHALL account admitted in-flight/completed task estimates plus explicit persistent reservations against the stage RAM budget. Tasks that cannot be admitted SHALL remain ready and increment memory-backpressure telemetry rather than violating the budget. Queue-capacity pressure SHALL be separately visible. Persistent reservations SHALL be releasable when the caller finalizes the owning state.

## 5. Telemetry/locality contract

Snapshots SHALL expose allocated/busy lanes, ready/in-flight/completed counts, submitted/finished/committed totals, current/peak accounted memory, queue/memory backpressure counts, and heartbeat count. Optional locality metadata SHALL not enter scientific identity. Revision 93 reserves NUMA-locality metadata but does not activate NUMA pinning, node-local queues, or stealing policies.

## 6. FEAS1 consumer contract

FEAS1 SHALL use PARCORE1 instead of owning a private `ThreadPoolExecutor` coordinator. Profile preparation and witness blocks SHALL share the same global queue. Parallel FEAS1 cKDTree calls SHALL use one native tree worker/task while outer work can fill the CPU budget. Per-profile witness blocks SHALL be committed in exactly the pre-PARCORE canonical order, preserving support/capacity floating-point authority and all scientific record digests.

Direct `build_target_coverage_feasibility_report` callers MAY omit an explicit resource scope; this preserves pre-PARCORE direct-API resource-control semantics. Campaign execution SHALL pass its explicit `StageResourceScope` so the queue owns native-thread quarantine and RAM admission.

## 7. Qualification acceptance

PARCORE1 passes only if:

1. queue contract tests prove bounded multi-lane execution, canonical out-of-order reduction, memory backpressure/release, and deterministic task-identity exceptions;
2. FEAS1 scientific output digest is identical to PERFBASE1 at every tested worker schedule;
3. no worker/native-thread oversubscription is observed;
4. the automatic-budget workload populates all assigned lanes; and
5. same-host comparison against the untouched PERFBASE1 implementation establishes no material throughput regression.

The revision-93 qualification digest is `937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613`. `NEIGHBOR1` is the next gate.
