---
kind: implementation-workplan
workplan_id: DATA78-CLOSEOUT1
protocol_version: 5.2.0
---

# DATA78-CLOSEOUT1 — Post-implementation materialization closeout

**Status:** active — local C5 remediation implemented; target-host screening rerun pending
**Current authority:** `docs/specs/training_data/mlff_data9a9b_production_materialization_spec.md`, `docs/specs/training_data/mlff_cpu_resource_budget_spec.md`, `docs/arch_manuals/mlff_training_data/60_execution_performance.md`
**Target branch/base:** `feat/data78-c5-screening-closeout` / `473c455` (`DATA78-CLOSEOUT1` latest source state)

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
- `mdstats/training_data/production_materialization.py` for restart/cache identity, fitted-core reuse, and plan validation
- `mdstats/training_data/target_size_study.py` and `target_multi_view_repair_v2.py` for bulk prefix authority and immutable digest reuse
- `mdstats/training_data/data7_bundle.py` for authenticated fitted-component reuse
- focused DATA7/DATA8/restart/resource tests
- permanent performance/materialization documentation only for accepted current-state changes

No new global DAG, scheduler, scientific authority, or CUDA DATA7/DATA8 execution.

## Gates

### C0 — Reopen closeout authority and freeze baseline

**Goal:** bind this closeout to the accepted PAR1 implementation state and preserve patch provenance.

**Acceptance:** closeout provenance remains rooted in the accepted prior implementation; C5 remediation is isolated on `feat/data78-c5-screening-closeout` against latest-source baseline `473c455`; baseline focused tests remain reproducible.

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

### C5 — Target-size screening remediation and representative performance qualification

**Goal:** remove the observed single-threaded planning pathology and avoid recomputing selection-invariant DATA7 fitted products across target sizes before deciding whether finer intra-domain parallelism is justified.

#### C5A — Linearize target-size planning

- add one bulk authenticated candidate-prefix materialization operation that validates REPAIR2 once and materializes each unique `(label_domain_id, target_size)` prefix once;
- compute the pre-selection evaluation cohort once from the maximum **qualified** target-size prefix, never from a shrinking next-stage candidate set;
- precompute domain membership sets once in `ProductionMaterializationPlan.__post_init__`; eliminate `set(...)` construction from per-UID membership loops;
- add call-count/scaling regression coverage proving prefix work scales with unique domains/sizes rather than development frames × variants.

#### C5B — Remove repeated immutable planning work

- memoize immutable REPAIR2 domain/plan digests, target-size candidate-authority digest, and production materialization plan digest;
- reuse already-built feature-fit domains and target-size prefix/evaluation authority across optimizer-only variants;
- expose planning subphase telemetry so no expensive operation remains hidden behind `building-materialization-plan`.

#### C5C — Correct DATA7 execution identity

- introduce a new shared DATA7 recipe schema keyed only by inputs capable of changing DATA7 bytes;
- remove DATA8-only target-size evaluation membership and unrelated target-study outcome state from the DATA7 recipe;
- preserve exact prescribed training prefix/selection authority identity;
- retain authenticated v1 cache read compatibility and allow valid legacy artifacts to be promoted/reindexed rather than refit.

#### C5D — Factor and reuse the expensive DATA7 fitted core

- define an execution-only fitted-core recipe over the domain-local feature metric, atomic-reference fit, training weights, checkpoint metric policy, and their exact upstream policies/lineage;
- build the fitted core at most once per unique `(domain, fitted-core recipe)` and realize size-specific selection/coverage from that core;
- use a reconstructible authenticated execution index/reference to an existing full DATA7 artifact carrying the fitted core; do not create a second scientific authority;
- every realized size-specific `Data7PreparationBundle` must retain the exact scientific component digests and final bundle digest produced by the unoptimized reference path.

Physical core/overlay archive splitting is **not** part of this gate unless post-C5D profiling shows repeated archive I/O/storage remains material.

#### C5E — Optimize selection realization only under exact numerical equivalence

- materialize prescribed prefixes once;
- test multi-size incremental coverage against independent size-specific reference calculations; use it only if all `SelectionCoverageLevel` values and digests are exact; otherwise retain independent coverage realization.

#### C5F — Reprofile the actual screening topology and conditionally add intra-domain parallelism

- profile the observed `folds=0`, `domains=1`, multi-size × optimizer-seed screening topology;
- report planning time, fitted-core count/time, selection/coverage time, archive I/O, effective CPU workers, peak RSS, and disk writes;
- if one fitted core remains wall-time dominant and materially CPU-idle, first vectorize/reuse remaining raw extraction, then expose scientifically independent within-domain components through the existing global resource budget;
- domain-level and within-domain schedulers must not nest blindly or oversubscribe RAM/CPU;
- measure DATA8 storage-width scaling before adding any throughput cap.

#### C5G — Full regression and restart qualification

Require exact reference equivalence for every target size, unchanged DATA8 bytes/identities, optimizer-seed reuse, 3→10→30 continuation, completed-materialization reuse, legacy v1 DATA7 cache restoration/promotion, failure/restart after fitted-core publication, and no regression to ordinary CV materialization.

**Acceptance:**

- planning complexity is linear in development membership plus unique requested prefixes, not frame count × prefix work × variant count;
- for one unchanged final-development domain, expensive fitted-core construction count is one regardless of candidate sizes/optimizer seeds;
- no cache or parallelism optimization changes scientific component digests or final DATA7 bundle digests;
- benchmark claims distinguish cold computation, shared-cache reuse, and completed-materialization reuse.

### C6 — Target GPU qualification boundary

**Goal:** verify on supported CUDA hardware that DATA6 releases model ownership/allocator state before DATA7/DATA8.

**Acceptance:** code/test path is ready locally; actual RTX 3090 observation remains an external qualification requirement when target hardware is unavailable and is never fabricated.

### C7 — Independent closeout review and patch

**Goal:** remove superseded helpers, reconcile accepted docs, run focused/integrated regressions, and produce the C5 remediation Git patch against latest-source baseline `473c455`. Keep the workplan active only for target-host screening evidence that cannot be established in the local fixture.

## Redesign triggers

- one DATA7 domain cannot fit by itself in the configured RAM envelope;
- immutable snapshot/cache storage cannot fit even at serial width while preserving the configured reserve;
- representative profiling shows DATA7 dominated by an inherently serial algorithm after raw-extraction cleanup;
- DATA8 throughput is storage-bound at low width, requiring an evidence-backed cap rather than more workers.

## Closeout implementation status — 2026-08-23

| Gate | Status | Evidence / disposition |
| --- | --- | --- |
| C0 | complete | Original closeout provenance is preserved; C5 remediation is isolated on `feat/data78-c5-screening-closeout` from latest-source baseline `473c455`. |
| C1 | complete | External foundation/selected-head/replay bytes cross an authenticated inode-independent snapshot boundary before mdstats-owned reuse; mutation-isolation and reuse tests pass. |
| C2 | complete | MLCV TRUE_DFT monitor/light realization is recipe-cached across optimizer-only variants; concurrent publication converges; one parent frame-array index is reused by setup/DATA7. |
| C3 | complete | DATA8 admission includes estimated/measured worker-context spill, final output bytes, RAM reservation, reserve, and conservative dead-PID/age-gated staging scavenging. |
| C4 | complete | Real coordinator tests cover out-of-order completion, worker failure with later cache publication, restart reuse, legacy checkpoint order, cache races, and external-source mutation isolation. A plan-order checkpoint defect discovered by this gate was fixed with legacy PAR1 digest read compatibility. |
| C5A | complete | Bulk prefix authority validates REPAIR2 once, materializes each unique domain/size once, and precomputes the maximum-qualified evaluation complement once. Membership validation is linearized. A 4,000-frame/2,048-prefix bounded microbenchmark measured 1.392 s for the pathological repeated-prefix pattern versus 0.00083 s for the bulk pattern (~1,676x); this is scaling evidence, not a production wall-time claim. |
| C5B | complete | REPAIR2 domain/plan, target candidate-authority, and production-plan digests are memoized; feature domains and target-size authority are reused across optimizer variants; planning has explicit progress before variant materialization. |
| C5C | complete | Shared DATA7 recipe schema v2 excludes DATA8-only evaluation membership and target-study state while retaining exact selection-prefix identity. True v1 recipe/cache generations remain authenticated read-compatible and can seed current reuse. |
| C5D | complete | Selection-invariant fitted metric/E0/training weights are reusable through a reconstructible fit-core index pointing at a full DATA7 carrier; no second scientific artifact authority was introduced. Persistent-restart and direct prescribed-target tests prove reused size-specific bundles exactly match clean refits. Small standard domains retain a 128-frame amortization floor because local timing showed archive/carrier overhead can exceed refit cost on tiny fixtures. |
| C5E | complete — conservative | Prefixes are materialized once. Multi-size coverage was exact on the bounded fixture, but no additional cross-size coverage persistence/scheduler was added because fitted-core reuse removes the dominant repeated work and the remaining benefit is not yet material enough to justify another cache path. |
| C5F | local implementation complete; target-host profile pending | The immediate planning pathology and repeated cross-size fits are removed before adding another scheduler. The bounded fit fixture showed that reuse can be slower on tiny domains, motivating the amortization floor; it cannot establish production CPU/RAM/I/O saturation. No nested intra-domain scheduler or storage cap is added without the real `folds=0, domains=1` screening rerun. |
| C5G | local complete | Target-size/REPAIR2 aggregate: 61 passed. Modified production-materialization file: 33 passed with only the two known baseline preflight cases excluded. Exact fitted-core reuse/refit equivalence, persistent restart reuse, v1 cache compatibility, serial/parallel DATA7 behavior, and affected restart/resource cases pass. The six stale doc/spec assertions reproduce identically on `473c455` and are not C5 regressions. |
| C6 | target-host VRAM release observed | User target-host log at the DATA7/DATA8 boundary reports 22.7 GiB free on the RTX 3090 after DATA6 cleanup, materially confirming model-memory release. No further GPU optimization is justified for this CPU-side planning/DATA7 bottleneck. |
| C7 | local complete; target rerun remains external | Durable execution/materialization docs are reconciled and the assembled architecture Markdown regenerated. `compileall` and `git diff --check` pass; the incremental patch is generated and apply-checked against `473c455`. The workplan remains active only for the real target-size screening rerun needed to decide whether finer single-domain parallelism is materially justified. |

### Local bounded benchmark artifacts

The development comparison was executed with the same deterministic test fixture and distinct cold caches. The PAR1 baseline and closeout candidate results are stored outside the repository as session evidence; they intentionally are not normative benchmark records because the fixture is too small to establish production throughput.

### Remaining external qualification command

Rerun the real target-size preparation campaign on the target host with normal runtime resource discovery and retain the planning/DATA7/DATA8 progress log. C6 VRAM release is already observed. Remaining C5F acceptance is: (1) `building-materialization-plan` no longer exhibits the previous single-threaded stall; (2) each unique target-size prefix is planned once and the expensive DATA7 fitted core is built once for the unchanged screening domain, then reused across candidate sizes/optimizer seeds; (3) record fitted-core wall time, CPU utilization, peak RSS, and DATA8 storage throughput. Only if that single remaining fit is still wall-time dominant while CPU and memory bandwidth are materially idle should within-domain feature/component parallelism be designed.
