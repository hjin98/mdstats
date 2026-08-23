---
kind: implementation-workplan
workplan_id: DATA78-CLOSEOUT1
protocol_version: 5.2.0
---

# DATA78-CLOSEOUT1 — Post-implementation materialization closeout

**Status:** active — post-implementation closeout required
**Current authority:** `docs/specs/training_data/mlff_data9a9b_production_materialization_spec.md`, `docs/specs/training_data/mlff_cpu_resource_budget_spec.md`, `docs/arch_manuals/mlff_training_data/60_execution_performance.md`
**Target branch/base:** `feat/data78-postimpl-closeout` / `da74002` (`DATA78-PAR1` implementation state)

## Objective

Close the remaining correctness, resource-accounting, restart, and performance gaps found by the independent post-implementation review without changing DATA7 scientific semantics or introducing a second scheduler/persistence authority.

## Invariants

- External authoritative inputs are never hardlinked directly into durable materialization or reusable execution caches.
- Efficient linking is allowed only from mdstats-owned immutable content-addressed snapshots/caches.
- Source authentication precedes snapshot ownership transfer; cached snapshots are independently authenticated.
- MLCV replay realization is keyed by TRUE_DFT source identity plus complete monitor policy, not optimizer variant.
- DATA7 fitted scaler/PCA/E0/weight/selection state remains domain-local and canonical checkpoint order remains coordinator-owned.
- Parallel admission honors runtime 90% CPU, RAM, free-disk reserve, temporary context spill, and task count; throughput caps are evidence-driven rather than hard-coded host counts.
- Large arrays are not copied through DATA8 task IPC.
- Warm completed-materialization reuse remains lazy.
- No performance gain weakens hashes, byte identity, validation, DATA9A qualification, or scientific digests.

## Scope

Primary implementation areas:

- `mdstats/training_data/data8_bundle.py`
- `mdstats/training_data/_campaign_cli_core.py`
- `mdstats/training_data/production_materialization.py` only where shared-index/failure semantics require it
- focused DATA7/DATA8/restart/resource tests
- permanent performance/materialization documentation only for accepted current-state changes

No new global DAG, scheduler, scientific authority, or CUDA DATA7/DATA8 execution.

## Gates

### C0 — Reopen closeout authority and freeze baseline

**Goal:** bind this closeout to the accepted PAR1 implementation state and preserve patch provenance.

**Acceptance:** active workplan exists on a dedicated branch based on `da74002`; baseline focused tests remain reproducible.

### C1 — Restore immutable external-input snapshot semantics

**Goal:** prevent external source mutation from changing staged DATA8 bytes and eliminate repeated source hashing/copying across variants.

**Work:**

- introduce one content-addressed mdstats-owned immutable byte-snapshot cache keyed by expected SHA/content identity;
- authenticate external source, copy to a staged generation, fsync/authenticate, then atomically publish;
- stage foundation, selected-head, replay monitor, and TRUE_DFT replay validation from owned snapshots, not external paths;
- retain hardlink-or-copy only between mdstats-owned immutable artifacts and consumers.

**Acceptance:** mutating/replacing an external source after materialization cannot alter staged bytes; equivalent variants reuse one owned snapshot; corrupt/racing generations fail closed.

### C2 — Complete shared-work elimination and shared frame-index ownership

**Goal:** remove repeated optimizer-invariant replay scans and duplicate frame-index construction.

**Work:**

- add content-addressed MLCV TRUE_DFT monitor/light realization keyed by source identity, monitor policy, and serializer/schema versions;
- cache both `MlcvReplayMonitorRecord` and the light ExtXYZ artifact atomically;
- changing optimizer seed alone must reuse the realization; changing source/policy must invalidate it;
- use one lazy parent `frame_array_index` for foundation-energy restoration and DATA7 materialization.

**Acceptance:** identical optimizer variants perform no repeated TRUE_DFT full-corpus monitor/light scans after first realization; one parent frame index serves both setup consumers.

### C3 — Close DATA8 resource accounting

**Goal:** make fresh-process admission safe for RAM and transient disk usage.

**Work:**

- serialize worker context before final worker launch decision and measure actual context spill bytes;
- include context spill, scheduled immutable outputs, reserve, and known scratch amplification in disk feasibility;
- conservatively calibrate worker RSS from task/context characteristics while retaining a safe floor;
- report residual stale staging bytes; only remove demonstrably dead/old cache-owned staging safely.

**Acceptance:** impossible disk/RAM workloads fail before subprocess launch; serial-feasible low-resource cases are not rejected merely because parallel width can be reduced.

### C4 — Materialization-path restart/failure qualification

**Goal:** qualify real coordinator semantics rather than only generic queue behavior.

**Acceptance tests:** out-of-order DATA7 completion; worker failure after later cache publication; interruption after cache publication/before checkpoint commit; restart reuse; concurrent monitor-cache publication; external-source mutation isolation; exact clean-run digest equivalence.

### C5 — Representative performance qualification and conditional G4 closeout

**Goal:** distinguish cold computation, shared-cache reuse, and completed-materialization reuse and decide whether finer DATA7 work is justified.

**Work:** measure equivalent baseline/candidate fixtures for wall time, effective workers, CPU/RSS, disk written, and cache mode; provide a target-workload command when full production data/hardware are unavailable. If DATA7 remains wall-time-dominant and materially CPU-idle, first reduce/vectorize repeated raw extraction; add finer task granularity only if evidence still justifies it. Measure DATA8 width scaling before adding any storage-throughput cap.

**Acceptance:** benchmark claims never conflate cache hits with cold-path speedup; no speculative nested scheduler is added without evidence.

### C6 — Target GPU qualification boundary

**Goal:** verify on supported CUDA hardware that DATA6 releases model ownership/allocator state before DATA7/DATA8.

**Acceptance:** code/test path is ready locally; actual RTX 3090 observation remains an external qualification requirement when target hardware is unavailable and is never fabricated.

### C7 — Independent closeout review and patch

**Goal:** remove superseded helpers, reconcile accepted docs, run focused/integrated regressions, archive this workplan only if all implementable gates pass, and produce a Git patch against `da74002`.

## Redesign triggers

- one DATA7 domain cannot fit by itself in the configured RAM envelope;
- immutable snapshot/cache storage cannot fit even at serial width while preserving the configured reserve;
- representative profiling shows DATA7 dominated by an inherently serial algorithm after raw-extraction cleanup;
- DATA8 throughput is storage-bound at low width, requiring an evidence-backed cap rather than more workers.

## Closeout implementation status — 2026-08-23

| Gate | Status | Evidence / disposition |
| --- | --- | --- |
| C0 | complete | Dedicated closeout branch based on `da74002`; patch provenance preserved. |
| C1 | complete | External foundation/selected-head/replay bytes cross an authenticated inode-independent snapshot boundary before mdstats-owned reuse; mutation-isolation and reuse tests pass. |
| C2 | complete | MLCV TRUE_DFT monitor/light realization is recipe-cached across optimizer-only variants; concurrent publication converges; one parent frame-array index is reused by setup/DATA7. |
| C3 | complete | DATA8 admission includes estimated/measured worker-context spill, final output bytes, RAM reservation, reserve, and conservative dead-PID/age-gated staging scavenging. |
| C4 | complete | Real coordinator tests cover out-of-order completion, worker failure with later cache publication, restart reuse, legacy checkpoint order, cache races, and external-source mutation isolation. A plan-order checkpoint defect discovered by this gate was fixed with legacy PAR1 digest read compatibility. |
| C5 | local closeout complete; target workload pending | Bounded development fixture keeps cold computation, shared-cache reuse, and completed reuse separate. It exposed excessive fresh-interpreter startup for small DATA8 workloads; a 32 MiB estimated-output amortization guard now keeps those batches serial. On this fixture candidate 4-thread cold materialization is 0.283 s versus 0.289 s one-thread; PAR1 baseline 4-thread cold was 5.45 s. These figures are not production-volume evidence. No finer DATA7 scheduler or storage-throughput cap is justified without the target workload. |
| C6 | external qualification pending | CUDA lifecycle code is unchanged from PAR1 and locally testable, but this environment has no RTX 3090/CUDA runtime. Target-machine VRAM observation remains required and is not fabricated. |
| C7 | local implementation closeout complete; external qualification remains | Accepted docs regenerated; focused/integrated regressions are complete and the incremental patch applies cleanly to `da74002`. Workplan remains active only for C5 target-workload evidence and C6 RTX 3090 observation. |

### Local bounded benchmark artifacts

The development comparison was executed with the same deterministic test fixture and distinct cold caches. The PAR1 baseline and closeout candidate results are stored outside the repository as session evidence; they intentionally are not normative benchmark records because the fixture is too small to establish production throughput.

### Remaining external qualification command

Run the real preparation campaign on the target host with normal runtime resource discovery and retain the DATA6/DATA7/DATA8 resource/progress log. Acceptance requires: (1) materially restored free VRAM after DATA6 provider close, (2) DATA7 effective width/resource pressure consistent with the runtime 90% CPU/RAM envelope, and (3) DATA8 worker width no larger than the point at which target-storage throughput ceases to improve. If DATA7 remains wall-time dominant while CPUs and memory bandwidth are materially idle, reopen C5 for raw-feature/vectorization profiling before considering finer scheduling.
