---
kind: implementation-workplan
workplan_id: MLFF-END-TO-END-PERF1
protocol_version: 5.3.0
status: active
base_branch: main
implementation_branch: feat/mlff-end-to-end-performance-v1
base_commit: d718d6ce52406fd38a02a45d3fde9bc53e031a74
---

# MLFF End-to-End Parallelization and Optimization Workplan

## Objective

Bring the MLFF campaign execution path from preflight through final verification/publication onto a coherent, resource-aware execution architecture that eliminates avoidable serial work, repeated parsing/data movement, under-batched accelerator execution, unbounded RAM/storage buffering, and duplicated scheduling/inference authorities while preserving all frozen scientific, numerical, persistence, restart, ordering, and candidate-selection semantics.

The implementation must reuse and consolidate the mature resource, work-queue, mmap/indexed-data, batch-calibration, graph-cache, and restart/materialization machinery already present in `prepare` wherever semantic ownership matches. New execution machinery is justified only where the workload is genuinely distinct, principally iterative relaxation and external LAMMPS dynamics.

## Diagnosis

The current tree has three materially different optimization maturity levels.

1. `prepare` / target-data preparation is mature and should be treated as the reference architecture: runtime-discovered CPU budgeting, RAM admission, deterministic bounded work queues, process isolation where the GIL matters, native-thread-width control, mmap/file-reference transport, content-addressed reuse, MACE batch-capacity calibration, persistent graph caching, and deliberate serial authority commits already exist.
2. TRAIN2 training and ordinary EVAL2 have substantial adaptive orchestration, but EVAL2 still uses a fixed inference batch size, a long forced single-job calibration period, object-count rather than byte-aware pipeline buffering, and large-monitor representations that can force repeated parsing. Evaluation execution policy is also partially mixed with scientific/evidence identity.
3. The later TRAIN2 physical verification path (`DEPLOY -> PES -> RELAX -> DYN -> LOCKED`) frequently bypasses the stronger execution machinery. It contains serial candidate/case loops, one-structure MACE inference, repeated full ExtXYZ parsing, repeated ML-IAP model copies/startup, serial relaxations, serial LAMMPS case matrices, whole-trajectory ASE materialization, Python-level geometry reductions, incomplete storage admission, and coarse persistence granularity.

The root problem is therefore not absence of optimization primitives. It is fragmented execution ownership and late-stage drift away from existing resource/data/inference authorities.

## Engineering envelope

### Scientific and numerical invariants

Implementation must not change:

- model/checkpoint/head identity or candidate population;
- target-size 3/10/30 dependency semantics and halving/freeze decisions;
- training dataset ordering/seeds/optimizer semantics/checkpoint semantics;
- evaluation metric definitions, reference labels, candidate ranking, pass/fail thresholds, or accepted precision policy;
- deployment checkpoint <-> target-model <-> ML-IAP parity semantics;
- PES probe definitions and parity/selection semantics;
- ASE FIRE convergence criteria and physical relaxation semantics unless a separately qualified later redesign is explicitly triggered;
- DYN velocity seeds, NVT/NVE boundaries, sampled timesteps, duplicate-timestep semantics, structural reference-frame semantics, minimum-distance semantics, protected topology definitions, consecutive/persistent damage rules, drift definitions, pass/fail thresholds, or deterministic case ordering;
- SELECT2 ordering/authority mutation;
- LOCKED-TEST2 information boundary: no locked-test prediction or graph materialization may occur before the existing activation boundary;
- final publication/authority semantics.

Discrete identities, graph/topology identities, ordering, seeds, and persistence schemas must remain exact where contractually discrete. Floating accelerator/vectorized results require justified existing or newly frozen numerical tolerances and must be validated on final physical/scientific observables rather than only intermediate arrays.

### Resource envelope

- Effective CPU allocation is runtime discovered from the actual process allocation/affinity/cgroup/scheduler environment. The default campaign CPU target remains at most approximately 90% of the effective allocation; this is an upper budget, not an occupancy requirement.
- Nested parallelism must be explicitly bounded. When an outer worker/process layer owns parallelism, BLAS/OpenMP/PyTorch/native inner width must not independently assume the whole machine.
- RAM admission must account for shared data, prepared buffers, active jobs, waiting prediction results, reducers, caches, and process overhead rather than only active worker count.
- GPU/VRAM batching and model-job concurrency must share one live stage VRAM budget and retain meaningful headroom. Live free VRAM is always re-sampled and re-clamped; persisted profiles are advisory compatibility evidence, never physical authority.
- Disk is a first-class resource. Long verification stages must account for current free space, minimum retained reserve, expected in-flight trajectory/log/scratch bytes, cache growth, and concurrent I/O pressure.
- I/O concurrency is independent of CPU worker count and must be bounded according to the storage domain.
- No unbounded futures/result queues, trajectory object lists, logs, cache growth, or temporary-file growth are acceptable in the optimized path.

### Performance envelope

Optimize in this order unless measurement disproves it:

1. eliminate redundant computation, parsing, serialization, startup, copies, and I/O;
2. improve asymptotic access/representation;
3. reuse validated compact/indexed/graph intermediates;
4. batch accelerator work;
5. vectorize/GIL-releasing compiled-library work;
6. reduce temporary allocations and copies;
7. add CPU/process concurrency for genuinely independent work;
8. add/adjust GPU job concurrency based on measured aggregate throughput;
9. add a custom native kernel only if the remaining measured hotspot materially justifies it.

For static accelerator inference, do not optimize batch size and model-job concurrency independently. Choose the joint operating point

`(batch_size*, concurrent_jobs*) = argmax throughput(batch_size, concurrent_jobs)`

subject to the shared CPU/RAM/VRAM execution envelope. Prefer a lower-resource point within a near-optimal throughput band when it preserves materially useful headroom/concurrency without meaningful throughput loss.

### Compatibility and recovery

- Existing persisted scientific/evaluation records and fixed historical policies must remain readable or receive an explicit schema compatibility path.
- Dynamic execution choices must not silently become scientific identity.
- Derived caches/indexes may invalidate/rebuild when compatibility changes; authoritative data must not be destructively migrated as a side effect of cache access.
- Concurrent/resumable operations must distinguish complete, partial, stale, corrupt, scientific-fail, infrastructure-fail, cancelled, and retryable resource-adaptive outcomes where those states are materially different.
- File existence alone is never completion evidence.

### Target hardware and qualification

Implementation testing must use bounded representative CPU/dependency-backed workloads and accelerator smoke/equivalence checks where available. Full production GPU qualification remains deferred to the final assembled candidate and the target workstation, consistent with project policy. No RTX 3090 throughput/resource claim may be treated as accepted until that final target-hardware qualification is run.

## Product design

### 1. One campaign resource authority

`SystemResourceSnapshot` / `StageResourceScope` and the existing campaign resource model remain the owning source for:

- effective CPU allocation and <=90% target budget;
- current RAM envelope;
- accelerator/device/free-VRAM state;
- disk/free-space policy;
- resolved stage resource plan.

Stage schedulers consume this authority; nested schedulers may not independently claim the entire machine.

### 2. Separate scientific evaluation semantics from runtime execution planning

Introduce a versioned execution representation, conceptually `InferenceExecutionPlan`, distinct from `CheckpointEvaluationPolicy` scientific/evidence semantics.

The execution plan owns runtime choices such as:

- auto versus fixed inference batch policy;
- selected batch size;
- compatible calibration/profile identity;
- concurrent model-job limit;
- CUDA stream use;
- host RAM estimates/reservations;
- graph/cache execution choices;
- runtime rationale/telemetry.

Existing historical fixed batch values remain readable. New generated configuration must distinguish explicit fixed execution from `auto`; do not silently reinterpret an old positive value as automatic.

Before moving batch/cache execution knobs out of scientific identity, establish numerical equivalence under the frozen prediction contract. Persist the resolved execution plan as reproducibility/performance evidence where backend/batching can materially affect interpretation.

### 3. One static MACE inference authority

Consolidate ordinary EVAL2, DEPLOY static predictions, PES foundation/candidate predictions, and LOCKED-TEST2 onto one canonical batched inference owner, conceptually `StaticMaceInferenceExecutor`.

It owns:

- authenticated model/provider construction;
- backend/precision realization;
- reusable graph preparation/cache;
- prediction-only batch calibration;
- joint `(batch_size, concurrent_model_jobs)` throughput selection;
- live VRAM re-clamping;
- bounded learned OOM ceiling/backoff;
- byte-aware host admission;
- deterministic result ordering;
- optional per-worker model-shell reuse only if separately qualified.

`predict_mace_model_on_probe()` must cease to be an independent production inference implementation after migration. It may remain only as a thin compatibility/reference adapter if callers still require its API.

### 4. Generalized authenticated sparse ExtXYZ access

Refactor the semantically generic byte-index machinery currently used for replay data into a reusable authenticated immutable ExtXYZ index abstraction. Replay-specific lineage remains a specialization; target verification consumers bind their own source identity.

Use this authority for sparse DEPLOY/PES/verification probe access so small probe sets do not require parsing/materializing the entire target ExtXYZ.

Required properties:

- source SHA/content identity;
- schema/index format version;
- frame offsets/lengths/atom counts;
- direct sparse seek and bounded contiguous reads;
- deterministic requested-frame ordering;
- atomic/concurrent-safe index creation;
- invalidation on source identity mismatch.

### 5. Cache/storage classification and lifecycle

Classify reusable ExtXYZ indexes, persistent MACE graph shards, and compatible execution profiles as derived caches, not authorities.

Each must define:

- semantic identity and format version;
- integrity/validity checking;
- atomic creation/publication;
- owner and scratch/cache location;
- size accounting;
- bounded retention/eviction;
- STOR3/reclamation integration where semantically appropriate;
- safe concurrent creation behavior.

Do not let optimization caches become an undocumented second source of truth.

### 6. EVAL2 staged pipeline with byte-aware backpressure

Retain the existing `CPU prepare -> GPU inference -> CPU finalize` architecture, but change admission from job-count-only buffering to aggregate byte/resource accounting.

Account for, as applicable:

- prepared monitor/graph bytes;
- shared cached bytes;
- active inference host bytes;
- prediction arrays waiting for finalization;
- active finalizer bytes;
- worker/process overhead.

Upstream preparation must stop when the aggregate reservation approaches the stage RAM envelope.

Replace the fixed five-minute single-job calibration behavior with sufficient-evidence convergence using representative active samples, stable VRAM/utilization observations, minimum useful activity, and a bounded maximum calibration window. Compatible persisted execution profiles may seed admission, but live resources always re-clamp them.

### 7. Prediction-only calibration generalized from existing MACE batch calibration

Generalize the qualified core of existing `MaceCalculatorProvider.calibrate_batch_capacity()` rather than duplicating calibration logic. DATA6 remains a consumer; static prediction gains a compatible prediction-only profile whose identity is not unnecessarily bound to an exact checkpoint when architecture/backend/dtype/workload envelope equivalence is sufficient.

Execution-profile compatibility should include all materially relevant dimensions, including:

- GPU/device identity or compute capability as justified;
- CUDA/driver/runtime-relevant identity;
- PyTorch/MACE/backend/kernel realization;
- dtype;
- model architecture/head topology/element set/cutoff and other graph-footprint determinants;
- representative graph-size/footprint envelope;
- calibration/profile schema version.

Current free VRAM is not part of persistent identity; it is live state used for re-clamping.

### 8. GPU scheduling at the actual accelerator boundary

Do not mark an entire candidate as GPU-active while it is hashing, exporting, staging files, or performing CPU-only work. Verification paths should adopt the staged pattern:

`CPU/I/O prepare -> accelerator section -> CPU/I/O finalize`.

Accelerator admission applies only around the actual GPU-owned section. This prevents idle GPU reservations from reducing useful concurrency.

### 9. DEPLOY/PES consolidation

DEPLOY/PES must:

- use sparse authenticated target-frame access;
- build/reuse common probe graphs once when geometry is shared across models;
- perform calibrated batched static inference;
- use adaptive accelerator admission only after intra-model batching is efficient;
- avoid per-probe/per-case full ML-IAP copies where immutable direct reference or generic hardlink->copy staging is safe;
- measure and reduce LAMMPS run-0 startup/model-load amplification before blindly increasing process count.

If a persistent/multi-case LAMMPS execution form can preserve exact parity semantics and materially reduces startup cost, it may be adopted after focused equivalence tests. Otherwise independent run-0 cases use bounded external GPU-process admission.

### 10. Generic immutable artifact staging

Promote the DATA8 hardlink/copy pattern into a generic immutable artifact staging utility rather than importing a DATA8-private helper.

Initial behavior should prefer:

1. direct immutable canonical reference when the consumer safely supports it;
2. safe same-filesystem hardlink;
3. copy fallback.

A reflink path is optional only if it can be implemented portably and justified without complicating correctness.

Use for ML-IAP verification artifacts where applicable.

### 11. RELAX execution

The first implementation keeps each conventional ASE FIRE trajectory temporally sequential, but flattens scientifically independent `(candidate, base)` relaxation cases into one global resource-admitted queue. Do not nest candidate and base pools.

Reuse worker/candidate calculator/model state where safe and deterministic.

Precompute immutable protected topology arrays and vectorize topology metrics using NumPy/established compiled primitives. ASE's trusted sequential FIRE path remains the oracle.

Batched multi-trajectory FIRE is not part of the initial required implementation. It becomes a redesign trigger only if post-G7 profiling shows RELAX still materially dominates and GPU utilization remains poor after case-level scheduling.

### 12. DYN external-process pipeline

Redesign DYN as a bounded external GPU-simulation -> CPU-reduction pipeline.

Each independent `(candidate, base, temperature, seed)` case is scheduled subject to the minimum of:

- CPU/process budget;
- RAM budget;
- GPU/VRAM/external-job budget;
- disk-space reserve;
- I/O-concurrency budget.

Do not assume multiple LAMMPS/Kokkos jobs are beneficial. Calibrate/measure external GPU-job concurrency; a correct optimum may remain one GPU simulation at a time while overlapping CPU reduction of case N with GPU simulation of case N+1.

Long LAMMPS stdout/stderr must be file-backed/bounded rather than captured unboundedly in Python memory.

### 13. DYN case-level resumability

Accepted-work durability must match the concurrent scheduling granularity.

Persist authenticated case-level completion records keyed by the materially relevant identity, including run/candidate, base, temperature, velocity seed, DYN policy, deployed model identity, LAMMPS/runtime identity, and schema version.

Required flow:

`case identity -> validated accepted receipt? -> reuse; otherwise attempt-local execution -> stream/reduce/hash -> validate -> atomic accepted case receipt`.

A candidate-level `DynVerifyRunRecord` is assembled deterministically only from the complete required canonical case inventory.

Leftover files or a vanished process are not completion evidence. On interruption, restart cost should be proportional to unfinished/invalid cases rather than the whole candidate matrix.

RELAX does not require equivalent fine-grained persistence initially unless profiling shows its restart cost is material.

### 14. DYN streaming/vectorized reduction

Do not materialize the full trajectory as a Python list of ASE `Atoms` before analysis.

Use streaming or bounded chunks while preserving the current exact semantics, including:

- duplicate timestep resolution (including which occurrence wins);
- deterministic timestep ordering;
- structural reference-frame choice;
- force availability/shape semantics;
- NVT/NVE boundary handling;
- consecutive/persistent damage logic;
- minimum-distance calculation;
- protected bond/angle definitions;
- drift and pass/fail metrics.

Precompute invariant arrays:

- selected/protected atom indices;
- reference bond pairs and lengths;
- reference angle triplets and values.

Vectorize MIC displacement, bond lengths, broken-bond masks, bond RMSE, angle vectors/dot products/norms/arccos, displacement RMS/max, and other dense per-frame reductions using NumPy/established compiled primitives.

Retain ASE's exact compiled neighbor-list machinery initially for dynamic new-bond/minimum-neighbor work. A new custom native kernel is required only if post-vectorization representative profiling shows that exact remaining topology operation is still a material hotspot.

Where practical, compute trajectory/log digests during the same sequential pass used for streaming reduction to avoid a second full read. If not practical, benchmark and justify the additional pass.

### 15. Failure, cancellation, and deterministic aggregation

Classify outcomes explicitly:

- scientific FAIL: successful execution producing `passed=False`; never infrastructure-retried;
- resource-adaptive failure such as retry-safe CUDA OOM: bounded corrective retry with reduced batch/concurrency;
- deterministic malformed/corrupt/schema/lineage failure: hard failure, not hidden by retry loops;
- user cancellation/preemption: stop new admission, cancel pending work, terminate owned children/process groups, preserve atomically accepted work.

Scheduler completion order must not affect scientific order, random seeds, candidate ranking, SELECT2, durable record ordering, or digest construction.

Attempt-local outputs must remain separate from accepted durable state until validation and atomic publication complete.

### 16. LOCKED-TEST2 boundary

LOCKED-TEST2 must use the canonical batched static inference owner only after the existing locked-test activation boundary. Shared code, execution machinery, and post-activation graph caching are allowed; pre-activation graph/prediction materialization or reuse of locked-test prediction evidence is prohibited.

### 17. TRAIN measurement-driven cleanup

Training is lower priority because its outer scheduler already accounts for DataLoader processes, RAM, VRAM, CPU and disk pressure.

Measure before changing:

- outer training jobs;
- DataLoader worker processes/job;
- native thread counts/CPU utilization inside parent and loader workers;
- RSS per loader/job;
- GPU utilization/VRAM versus job count.

If loader workers exhibit nested native oversubscription, explicitly contain loader-side native pools. Remove/relax the current artificial maximum-parallel-training-jobs ceiling only if representative measurements show the fixed cap strands useful throughput and the existing resource admission remains safe.

Do not change training batch size or other optimization semantics solely for throughput.

### 18. Preflight reuse

Separate reusable immutable qualification evidence from live resource checks.

Reusable qualification may be keyed by model/backend/runtime/precision/head/adapter/calibration identity. Live checks such as CUDA availability, current free VRAM/RAM, effective CPU allocation, disk free space, and executable availability must always be reacquired.

Do not parallelize tiny preflight/config operations merely to increase worker count. Small bounded I/O concurrency is acceptable only if profiling shows a material benefit.

### 19. Intentionally serial boundaries

Keep serial:

- 3 -> 10 -> 30 target-size dependency/freeze boundaries;
- deterministic serial authority commits where existing prepare/repair semantics require them;
- SELECT2 candidate authority mutation;
- final model/publication transaction;
- temporal steps within one conventional FIRE trajectory until/unless a separately qualified batched optimizer redesign is triggered.

## Initially expected affected behavioral surface

At minimum, implementation should assume impact across:

- `campaign_execution.py` evaluation policy, prediction, monitor/cache, persistence, and consumer paths;
- `model_features.py` MACE provider, graph cache, calibration/profile identities, and prediction-only execution;
- `inference_parallel.py` calibration/admission/resource state;
- `_campaign_cli_core.py` preflight, EVAL2 orchestration, TRAIN2 verification orchestration, LOCKED, configuration generation/resolution, and persistence integration;
- `resources.py` / stage resource-plan consumers if shared resource admission needs extension;
- `work_queue.py` consumers and possibly generic byte-aware admission helpers;
- `replay_index.py` or its refactored generic ExtXYZ indexed-access owner and all replay consumers;
- `deploy_verify.py` probe loading, static prediction, ML-IAP staging, LAMMPS run-0 execution;
- `pes_verify.py` static prediction/probe reuse consumers;
- `relax_verify.py` case orchestration and topology reductions;
- `dyn_verify.py` external process execution, trajectory reading/reduction, persistence, logging, hashing, topology kernels;
- training scheduler/resource code if G9 measurements justify executable changes;
- configuration schema/defaults/serialization/migration and generated campaign configuration;
- cache/persistence schemas and state-store readers/writers;
- tests for all callers/consumers, restart/recovery, concurrency, configuration, scientific equivalence, and integration paths;
- architecture/user documentation if accepted execution/configuration behavior changes materially.

This surface is provisional. The final assembled implementation must re-derive all plausibly affected callers, consumers, shared utilities, schemas, caches, orchestration paths, and package/CLI boundaries before final acceptance.

## Acceptance

### Protocol-wide acceptance

Every material executable gate must close with:

1. focused tests for the new/modified mechanism;
2. the affected regression subset for that gate before dependent implementation proceeds;
3. direct integration through the real affected product boundary where appropriate.

Final acceptance must:

- re-derive the affected surface from the assembled implementation;
- rerun complete affected-surface regression after all material executable edits;
- run repository/project-required broader checks, using the broader/full available suite if the affected surface cannot be confidently bounded;
- run assembled integration through the actual preflight -> target-size/materialization -> training/evaluation -> verification -> final path using bounded representative data;
- honestly report unavailable checks;
- keep full production GPU qualification separate from functional acceptance.

### Scientific equivalence

Require, as applicable:

- serial/reference versus concurrent result equivalence;
- batch-1/reference versus calibrated batching energy/force/stress equivalence under justified tolerances;
- candidate ranking and pass/fail identity;
- exact sparse-index versus full ASE parsing structure/order equivalence;
- sequential ASE FIRE reference versus scheduled RELAX equivalence;
- current/reference DYN reducer versus streaming/vectorized reducer equivalence, including difficult periodic/topological cases;
- identical velocity/task seeds independent of scheduling;
- unchanged LOCKED activation semantics.

### Concurrency/recovery/resource acceptance

Test:

- deterministic ordering under out-of-order completion;
- bounded queues/backpressure;
- low-RAM admission behavior;
- bounded OOM backoff and learned safe ceiling;
- worker/subprocess failure propagation;
- cancellation during compute and publication;
- cleanup of process groups/temp paths/locks;
- concurrent cache/index creation;
- stale/corrupt cache/profile invalidation;
- DYN restart after partial case completion;
- storage admission / simulated write failure or ENOSPC-like refusal without corruption;
- native-thread/nested-parallelism budget behavior.

### Performance/resource evidence

Representative baseline/candidate measurements must record, where material:

- end-to-end and per-stage wall time;
- throughput;
- CPU utilization/thread/process count;
- peak RSS/RAM;
- GPU utilization and peak VRAM;
- batch size and concurrent-job operating point;
- model load/conversion time;
- bytes read/written;
- peak scratch/cache footprint;
- cold versus warm cache/restart behavior;
- trajectory/log sizes and DYN reduction time;
- worker/concurrency configuration.

Do not accept a speedup produced by reduced scientific resolution, changed dtype/precision policy, weaker thresholds, omitted output, smaller candidate population, shorter production semantics, or work moved outside the measured interval.

### Production qualification

Deferred until the fully assembled functionally accepted candidate is ready. The target workstation GPU qualification must characterize the final end-to-end system, including joint static-inference batch/job optimum, LAMMPS external-job concurrency, VRAM/RAM behavior, and representative storage/I/O behavior. No final accelerator performance claim is accepted before this qualification.

## Implementation sequence

### G0 - Baseline, contracts, and benchmark fixtures

Freeze representative bounded workloads and baseline evidence for PRE-FLIGHT, TRAIN2 training slice, EVAL2, DEPLOY, PES, RELAX, DYN, and LOCKED. Record stage time, CPU/RAM/VRAM, process/thread counts, GPU utilization, load/conversion time, bytes read/written, scratch/trajectory sizes, and cold/warm behavior where practical.

Freeze exact existing semantics needed for later equivalence tests, particularly evaluation policy identity, sparse structure ordering, RELAX metrics, DYN duplicate timesteps/reference frame/damage logic, and LOCKED activation.

Gate close: no production behavior change. Baseline fixtures and focused semantic/oracle tests exist and pass.

### G1 - Evaluation scientific-policy / execution-plan separation

Introduce the versioned runtime inference execution plan and explicit auto/fixed configuration resolution without changing scientific outcomes. Preserve historical policy/schema readability and cache/evidence compatibility rules.

Gate close regression:

- configuration precedence/default/migration/serialization tests;
- old fixed-batch policy compatibility;
- evaluation policy digest/schema tests;
- ordinary EVAL2 outputs, ranking, persistence/restart behavior unchanged on bounded fixtures.

### G2 - Indexed immutable-data and cache/storage ownership

Generalize authenticated ExtXYZ byte indexing; migrate sparse target probe consumers; promote immutable artifact staging; define cache/profile lifecycle, identity, atomic creation, and bounded retention.

Gate close regression:

- sparse direct seek equals full ASE read exactly in configuration/order;
- stale/corrupt index rejected/rebuilt;
- concurrent index/cache creation is race-safe;
- immutable staging preserves exact SHA bytes and failure cleanup;
- replay-index existing behavior unchanged;
- DEPLOY/PES probe identities unchanged.

### G3 - Canonical calibrated static MACE inference

Create/consolidate the shared static inference owner. Generalize prediction-only calibration. Implement shared live VRAM budget and joint `(batch_size, concurrent_jobs)` calibration/profile selection, live re-clamping, bounded OOM learning, and deterministic outputs. Route EVAL2 static inference through it first.

Gate close regression:

- reference/batch-1 versus optimized energy/force/stress equivalence;
- forced OOM -> bounded backoff -> retained safe ceiling;
- execution-profile compatibility/invalidation tests;
- serial/concurrent deterministic prediction order;
- EVAL2 metrics/ranking/persistence unchanged;
- representative throughput/resource evidence shows no material regression in the reference path.

### G4 - EVAL2 pipeline/backpressure and calibration convergence

Make staged pipeline admission byte-aware and replace the fixed five-minute single-job calibration requirement with evidence-based convergence plus compatible profile reuse and live re-clamping.

Gate close regression:

- bounded low-RAM/backpressure tests;
- no unbounded prepared/result queues;
- worker failure/cancellation cleanup;
- serial versus pipelined semantic equivalence;
- cold/warm evaluation integration;
- representative evaluation throughput/resource benchmark.

### G5 - Conditional accelerator model-shell reload qualification

Benchmark the existing compatible same-architecture shell/state-reload concept against fresh provider/model construction on the available/target accelerator path, including total model load/conversion/inference throughput and VRAM.

Decision gate:

- if no material end-to-end benefit, retain current fresh-construction behavior and close G5 with no production code enablement;
- if materially beneficial and numerically equivalent, enable one private compatible shell per inference worker under strict identity checks and rerun affected EVAL regression.

Do not share a mutable model shell across concurrent workers.

### G6 - DEPLOY and PES consolidation

Route static predictions through the canonical inference executor; use sparse target access and common graph reuse; stage candidate execution so GPU admission covers the actual accelerator section only. Eliminate avoidable per-case model copies. Measure/reduce LAMMPS run-0 startup/model-load overhead before selecting external process concurrency.

Gate close regression:

- checkpoint <-> target-model <-> ML-IAP parity unchanged;
- PES pass/fail/request identities unchanged;
- shared probe graph/cache correctness;
- out-of-order candidate completion aggregates deterministically;
- external-process failures/cancellation leave no orphan processes/temp authority;
- representative DEPLOY/PES wall-time/resource evidence.

### G7 - RELAX independent-case scheduling and vectorized metrics

Flatten independent `(candidate, base)` cases into one global resource-admitted queue. Reuse worker-local model/calculator state safely. Vectorize immutable topology reductions while retaining ASE FIRE as the oracle.

Gate close regression:

- serial ASE FIRE versus scheduled execution equivalence under frozen tolerances;
- exact convergence/pass-fail identity;
- deterministic aggregation and seeds;
- nested CPU/native width bounded;
- failure/cancellation cleanup;
- representative RELAX scaling/resource benchmark.

Redesign trigger: only if post-G7 profiling shows RELAX remains materially dominant with low GPU utilization may batched multi-trajectory FIRE be separately designed and qualified.

### G8 - DYN resource-aware external pipeline, resumability, streaming/vectorized reduction

Implement:

1. bounded external LAMMPS GPU-process scheduling;
2. separate disk/I/O admission and expected in-flight footprint accounting;
3. file-backed bounded subprocess logging;
4. immutable model reference/hardlink staging rather than per-case full copies where safe;
5. case-level authenticated completion receipts and restart reuse;
6. streamed/bounded trajectory reduction;
7. overlap of CPU reduction with subsequent GPU simulation where resources permit;
8. precomputed topology arrays and vectorized dense geometry reductions;
9. one-pass digest integration where practical;
10. exact existing dynamic neighbor/topology reference behavior until profiling justifies a later custom kernel.

Gate close regression:

- reference versus streamed/vectorized DYN metrics/pass-fail equivalence;
- duplicate timestep, reference-frame, NVT/NVE, force, damage, and seed semantics explicitly tested;
- restart reuses only authenticated completed cases and recomputes incomplete/stale/corrupt cases;
- simulated write/storage-admission failure leaves accepted state intact;
- bounded logs/RAM/queues;
- process-group cancellation and orphan cleanup;
- deterministic run-record assembly independent of completion order;
- representative trajectory-size and case-count scaling/resource benchmark.

Redesign trigger: a custom compiled periodic/topology kernel is justified only if representative post-vectorization profiling shows the remaining exact neighbor/topology step materially dominates.

### G9 - TRAIN measurement-driven resource cleanup and preflight reuse

Measure DataLoader/native threading and job concurrency. Only then implement loader inner-thread containment and/or relax the artificial training-job ceiling if evidence shows a real throughput/resource problem. Separate reusable immutable doctor/acceleration qualification evidence from always-live resource checks.

Gate close regression for any executable change:

- training seeds/dataset ordering/checkpoint semantics/numerical policy unchanged;
- training scheduler CPU/RAM/VRAM/disk admission tests;
- nested native width behavior verified;
- preflight stale qualification invalidation and live resource refresh tested;
- bounded representative training/preflight measurement supports the change.

If measurements do not justify a production change, document/close the subitem without adding machinery.

### G10 - Final affected-surface reconciliation, assembled regression, integration, and qualification handoff

Re-derive the complete affected behavioral surface from the assembled implementation. Remove superseded duplicated production paths where compatibility does not require them. Confirm no second resource/inference/index authority remains accidentally active.

Run:

- complete focused tests for all new mechanisms;
- final regression across the re-derived affected surface;
- repository-required broader/full available tests where impact cannot be confidently bounded;
- assembled bounded integration through the real campaign path from preflight through final verification/publication;
- restart/cancellation integration at representative recovery boundaries;
- final complexity review for stale wrappers/fallbacks/duplicated schedulers/caches.

After functional acceptance, prepare the final target-workstation GPU production qualification package. Production GPU qualification remains separate from implementation acceptance and is run only on the final assembled candidate.

## Risks / redesign triggers

- **Batching changes numerical outputs beyond the accepted evaluation tolerance.** If observed, batch size cannot be treated as purely execution-only; persist/identity it accordingly and preserve the scientifically accepted policy.
- **Joint batch/job calibration complexity does not produce material benefit over a simpler robust rule.** Prefer the simpler policy if representative end-to-end throughput lies within the accepted near-optimal band while preserving headroom.
- **GPU model-shell reload is not faster end-to-end.** Do not enable it.
- **A single LAMMPS/Kokkos job already saturates the GPU.** Keep simulation GPU concurrency at one and exploit CPU-reduction overlap instead.
- **RELAX remains dominant after case scheduling.** Only then consider separately qualified batched FIRE.
- **DYN exact neighbor/topology work remains dominant after vectorization.** Only then consider an exact native kernel with the existing ASE/Python path retained as oracle.
- **Generalized ExtXYZ index ownership becomes more complex than separate semantically justified indexes.** Share the generic byte-index core without forcing replay- and target-specific lineage semantics into one inappropriate authority.
- **Derived cache growth or invalidation becomes operationally expensive.** Adjust bounded retention/eviction or prefer rebuild over migration; do not turn cache state into authority.
- **Concurrent verification introduces nondeterminism in scientific ordering/seeds/persistence.** Block the gate and fix ownership/aggregation before proceeding.
- **Resource estimates are materially inaccurate at production scale.** Use live measurement/adaptive admission and retain conservative headroom; do not increase concurrency to satisfy occupancy targets.
- **Implementation broadens the affected surface beyond the initial plan.** Expand stage/final regression accordingly; initial file lists are not acceptance boundaries.
- **Target GPU qualification contradicts bounded benchmark assumptions.** Reopen only the affected execution policy/resource design, not scientific semantics, unless evidence demonstrates a deeper correctness issue.
