# MLFF-END-TO-END-PERF1 Reopen Implementation Workplan

Status: **FUNCTIONAL IMPLEMENTATION ACCEPTED — TARGET-WORKSTATION GPU QUALIFICATION DEFERRED**
Branch: `feat/mlff-end-to-end-performance-v1`  
Reopens: `MLFF_END_TO_END_PARALLELIZATION_OPTIMIZATION_WORKPLAN.md` closeout status  
Date reopened: 2026-08-24

## 1. Authority and purpose

This workplan is the authoritative reopening amendment for the next implementation round of MLFF-END-TO-END-PERF1.

The original `MLFF_END_TO_END_PARALLELIZATION_OPTIMIZATION_WORKPLAN.md` remains the architectural baseline and source of the original G0-G10 requirements. This amendment supersedes only its implementation-closeout claim. It does **not** discard accepted mechanisms or broaden scientific scope.

The previous statement that G0-G9 were functionally closed and G10 was closed subject only to target-workstation production qualification is withdrawn. Independent closeout review found one deterministic late-stage command failure and several material architecture/acceptance gaps. Functional acceptance is therefore reopened before production GPU qualification.

Implementation may proceed gate-by-gate under this plan without another design round unless a redesign trigger or genuine blocker below is reached.

## 2. Engineering envelope retained from PERF1

The reopened implementation must preserve all scientific and campaign semantics already frozen by the parent plan:

- no change to target-size authority, 3 -> 10 -> 30 dependency/freeze semantics, selection/ranking rules, candidate population, seeds, scientific thresholds, dtype/precision policy, or production verification resolution merely to improve throughput;
- execution choices such as inference batch size, model-job concurrency, cache use, queue depth, worker count, staging method, and scheduling order remain execution state unless numerical evidence proves otherwise;
- scientific ordering and durable authority must be independent of concurrent completion order;
- accepted immutable/restart evidence must be authenticated before reuse;
- CPU/RAM/VRAM/storage/I/O admission must fail closed when even one required unit of work cannot fit its configured safety envelope;
- cancellation/failure must stop new admission, clean up owned workers/process groups, and preserve previously accepted atomic state;
- full production-scale GPU qualification remains separate from functional regression/integration and remains deferred to the final assembled candidate on the target workstation.

## 3. Reopen findings that are now implementation requirements

### F1 — DEPLOY/PES hard command-path failure

`InferenceExecutionPlan` defines `selected_batch_size`, while current DEPLOY/PES command orchestration reads `selected_inference_batch_size`. The real command path can therefore raise `AttributeError` before prediction.

Required outcome: one canonical field/API is used consistently across all production callers. Do not add a second long-lived synonym merely to hide caller drift unless compatibility requires it.

### F2 — scientific policy and runtime execution identity remain entangled

`CheckpointEvaluationPolicy.batch_size` still participates in policy serialization/digest while the new `InferenceExecutionPlan` also owns runtime batch selection. The command path copies runtime selection back into the policy.

Required outcome: runtime batch/concurrency/cache/stream/profile choices must not mutate scientific evaluation identity. Historical serialized policies must remain readable and existing accepted evidence must retain explicit compatibility rules.

### F3 — canonical static inference owner is incomplete and authority is duplicated

`StaticMaceInferenceExecutor` currently provides deterministic batching, graph reuse and bounded OOM backoff, but joint `(batch_size, concurrent_model_jobs)` selection, compatible profile reuse, live VRAM re-clamping and outer concurrency remain outside it or unintegrated. `StaticInferenceOperatingPoint` selection exists but is not the authoritative production path.

Required outcome: consolidate static inference resource/operating-point ownership so there is one coherent production authority for batch size, model-job concurrency, profile compatibility and OOM/re-clamp behavior. Reuse existing mechanisms rather than introducing a third scheduler/profile layer.

### F4 — CUDA/RAM admission can force one job even when one job is infeasible

Current planning can coerce RAM-derived capacity to at least one job. CUDA calibration can likewise retain one job even when projected one-job resource use breaches the configured ceiling. VRAM calibration also peak-trims the observations used for concurrency projection.

Required outcome: explicit one-unit feasibility checks before admission; impossible budgets fail closed. VRAM safety must be based on a peak-safe/high-confidence bound with headroom rather than discarding safety-relevant peaks. Live VRAM re-clamping must occur before new overlapping admission, not only after the ceiling is already reached.

### F5 — EVAL byte-aware backpressure is not authoritative for real resident payloads

The current recursive object-size estimator can shallow-count non-dataclass containers such as ASE `Atoms`, and it does not form an explicit ownership ledger for prepared graphs, predictions, model/provider residency and queued result state.

Required outcome: replace inference-by-introspection with explicit byte reservations/measurements attached to staged pipeline payloads and release them on ownership transitions. Queue admission must remain bounded under representative low-RAM conditions.

### F6 — immutable artifact staging publication is not race-safe against conflicting concurrent publishers

Current staging can use unconditional replacement after an initial destination-existence check.

Required outcome: accepted immutable destinations must never be silently replaced by a competing publisher. Use no-clobber publication or a keyed lock plus post-race byte comparison. Identical concurrent publishers may converge to the same accepted artifact; different bytes must fail without replacement.

### F7 — DYN does not implement the intended simulation -> reduction pipeline

A DYN scheduler task currently owns model staging, full LAMMPS execution, trajectory/log parsing, hashing and CPU reduction before releasing the scheduler slot. With the conservative one-LAMMPS-process default, CPU reduction therefore leaves the GPU idle instead of overlapping case N reduction with case N+1 simulation.

Required outcome: split DYN into independently bounded external-simulation and CPU/I/O-reduction phases with deterministic aggregation and authenticated case completion. A valid final GPU simulation concurrency may remain one.

### F8 — DYN streaming is improved but still performs redundant full passes and has an unbounded rare fallback

Normal trajectory handling performs an ordering pass and then a second parse pass; hashing adds another full read. The out-of-order fallback retains all frames in a dictionary.

Required outcome: make the canonical LAMMPS-produced path single-pass or bounded-pass for parse/reduce/hash where practical. Preserve exact duplicate-timestep last-wins semantics. Bound or explicitly reject pathological noncanonical out-of-order inputs rather than silently materializing arbitrarily large trajectories.

### F9 — final affected-surface regression/integration did not exercise the real command boundary strongly enough

Focused tests passed while the real DEPLOY/PES field mismatch remained. The real bounded assembled campaign path was not completed.

Required outcome: every materially affected CLI/public command must be exercised through its production boundary, with stubbing only below that boundary. Final functional acceptance requires bounded assembled integration through preflight -> preparation/materialization -> training/evaluation -> DEPLOY/PES/RELAX/DYN -> selection/publication as applicable.

## 4. Product-complexity rule for the reopen

Prefer, in order:

`reuse -> consolidate -> refactor -> delete`

The reopen is not permission to accumulate compatibility wrappers or parallel schedulers. In particular:

- do not retain two active batch/concurrency authorities;
- do not retain both scientific-policy batch ownership and runtime-plan batch ownership after migration is complete;
- do not create a second DYN restart authority beside authenticated case receipts;
- do not create a second generic memory estimator when explicit payload/resource reservations can be owned by the scheduler;
- keep historical readers only where required for compatibility, and isolate them from the new canonical write path.

## 5. Reopened implementation sequence

### R0 — hard-failure repair and real-boundary smoke gate

Implement first:

1. fix the `selected_batch_size` production API drift across DEPLOY/PES and any other callers;
2. search all `InferenceExecutionPlan` consumers for stale/nonexistent fields;
3. add production-boundary smoke tests for DEPLOY and PES command orchestration that resolve the real execution plan and reach the prediction owner;
4. add an API/schema test that rejects future field drift by constructing the real plan and exercising all command consumers.

Stage-local acceptance:

- focused execution-plan/DEPLOY/PES tests pass;
- real CLI/internal command boundary reaches the static executor without `AttributeError`/schema drift;
- existing DEPLOY checkpoint <-> target and PES scientific parity/pass-fail tests remain unchanged;
- no compatibility alias is added unless an actually supported external API requires it.

Do not proceed to broader architectural edits while this hard failure remains.

### R1 — complete G1 scientific-policy / execution-plan separation

Implement:

1. define the canonical scientific `CheckpointEvaluationPolicy` identity independently of runtime batch size/concurrency/cache/streams/profile;
2. move active runtime batch ownership to `InferenceExecutionPlan` only;
3. preserve historical policy schema/digest readers and explicit evidence compatibility;
4. ensure current canonical writes do not fold runtime-only fields into scientific policy identity;
5. ensure EVAL persistence stores runtime execution evidence separately from scientific evaluation evidence;
6. document migration behavior for legacy `evaluation.batch_size` and fixed-batch configurations.

Required regression:

- two execution plans with different batch sizes produce identical scientific policy digest and identical bounded scientific metrics;
- differing model-job concurrency/cache/stream choices likewise leave scientific identity unchanged;
- historical serialized policy fixtures round-trip/read with correct legacy digest semantics;
- existing EVAL2 ranking, candidate admissibility and restart evidence remain unchanged;
- config precedence for legacy fixed batch, explicit new fixed batch and auto mode is deterministic.

Gate close only after affected EVAL2 and persistence regression passes.

### R2 — complete G3 canonical static inference and fail-closed resource ownership

Consolidate rather than layer new machinery.

Implement:

1. make one production owner responsible for static inference batch selection, model-job concurrency and compatible operating-point evidence;
2. integrate `StaticInferenceOperatingPoint`/equivalent measured operating-point selection into the real production path or remove it if a simpler existing mechanism becomes canonical;
3. support bounded cold-start operation followed by compatible profile reuse and live re-clamping;
4. require explicit one-job feasibility before any CUDA/RAM admission;
5. use VRAM peak-safe/high-confidence evidence with configured reserve/headroom; do not discard safety-relevant allocation peaks merely as utilization noise;
6. make aggregate live VRAM/RAM checks occur before additional admission;
7. retain bounded per-executor OOM batch backoff and learned safe ceiling;
8. define whether one worker owns one model shell and prohibit unsafe mutable shell sharing across concurrent workers;
9. either implement currently exposed execution fields (`concurrent_model_jobs`, `use_cuda_streams`, compatible profile identity, host RAM budget) or remove/defer them from active production configuration so configuration does not advertise inert behavior.

Required regression:

- batch-1/reference versus optimized energy/force/stress equivalence;
- deterministic output order under concurrent completion;
- forced OOM halves batch only within bounded retry budget and retains the learned safe ceiling;
- one-job RAM infeasibility fails before launch;
- one-job VRAM infeasibility fails before launch;
- spiky VRAM calibration cannot promote concurrency based on a trimmed-away unsafe peak;
- stale/incompatible execution profiles are ignored/rebuilt;
- live resource change re-clamps future admission without changing scientific results;
- no second active batch/concurrency authority remains after gate close.

Representative CPU-only evidence may establish functional behavior in CI/development. Target-workstation GPU throughput qualification remains deferred.

### R3 — complete G4 EVAL explicit byte-ledger/backpressure

Implement:

1. replace generic shallow object introspection as the scheduling authority with explicit byte reservations or measured payload sizes for each pipeline stage;
2. account separately for active prepare reservations, prepared graph/data payloads, active inference residency, inference result payloads, finalize backlog and relevant worker/model/cache reservations;
3. transfer/release reservations exactly when ownership moves between prepare -> inference -> finalize;
4. keep queue-depth limits in addition to byte limits;
5. fail closed when the configured RAM envelope cannot admit one required payload;
6. retain bounded cancellation/failure cleanup so reservations and queues cannot leak.

Required regression:

- ASE `Atoms`/graph-containing prepared payloads are charged by their real/explicit retained bytes rather than shallow `sys.getsizeof()`;
- low-RAM fixture demonstrates producer backpressure and bounded ready/finalize queues;
- one-payload infeasibility fails deterministically instead of overcommitting;
- out-of-order completion produces the same evaluation records/ranking;
- worker failure/cancellation drains/releases reservations;
- cold/warm EVAL2 integration remains scientifically identical.

### R4 — close G2 concurrent immutable-publication race

Implement the smallest ownership fix:

1. no-clobber or keyed-lock immutable destination publication;
2. if a concurrent writer wins, verify accepted bytes against the intended source;
3. identical bytes -> reuse accepted destination;
4. different bytes -> hard failure without replacement;
5. cleanup attempt-local temporary paths on all failure/interruption paths.

Required regression:

- two simultaneous identical publishers converge safely;
- two simultaneous different publishers cannot replace each other;
- interrupted/corrupt attempt leaves accepted destination unchanged;
- SHA/authority checks and direct-reference/hardlink/copy semantics remain unchanged.

After R4, G2 may be considered closed again.

### R5 — finish G6 DEPLOY/PES consolidation on the corrected static authority

After R1-R4 stabilize the shared execution layer:

1. route DEPLOY and PES through the corrected canonical static inference owner only;
2. keep sparse target reads and stable geometry graph reuse;
3. ensure execution-plan evidence is separate from scientific probe/policy identity;
4. ensure GPU/resource admission covers actual accelerator work rather than unrelated CPU/I/O finalization where practical;
5. verify immutable staging and external LAMMPS run-0 cleanup/cancellation semantics;
6. remove stale duplicate static-prediction paths if no longer needed for compatibility.

Required regression:

- checkpoint target head <-> exported target-only model <-> ML-IAP parity remains unchanged;
- PES request/probe identities and pass/fail remain unchanged;
- sparse target lookup equals full-reference lookup;
- shared graph cache is identity-safe under candidate/model changes;
- command-level DEPLOY and PES tests execute the real orchestration boundary;
- external process failure/cancellation leaves no orphan process group or accepted partial artifact;
- deterministic aggregation independent of completion order.

### R6 — complete G8 DYN external simulation/reduction pipeline

Refactor around two explicit resource domains rather than treating the entire case as one GPU task.

Implement:

1. **simulation phase**: immutable staging/input creation + external LAMMPS process under CPU/RAM/GPU/VRAM/disk/I/O admission;
2. **reduction phase**: trajectory/log parse, metric reduction, digest verification and receipt publication under CPU/RAM/I/O admission without holding a GPU simulation slot;
3. bounded handoff queue between simulation completion and reduction;
4. permit CPU reduction of case N to overlap GPU simulation of case N+1 when resources permit;
5. retain conservative `maximum_parallel_dynamics_jobs = 1` unless representative target-GPU evidence later justifies more;
6. keep authenticated case-level receipts as the sole restart authority;
7. preserve deterministic final run-record assembly from the canonical case inventory;
8. integrate digest computation into the streaming pass when practical, or explicitly bound/justify an additional sequential read;
9. canonical LAMMPS-produced trajectory reduction must be streaming/bounded;
10. preserve duplicate timestep ordering/last-wins, reference-frame, force, NVT/NVE boundary, drift, minimum-distance, topology and persistent-damage semantics exactly;
11. bound or fail explicitly on noncanonical out-of-order trajectory fallback rather than accumulating an unbounded frame dictionary;
12. preserve process-group cancellation and file-backed logs.

Required regression:

- old/reference versus new pipeline DYN metrics and pass/fail are identical on frozen fixtures;
- duplicate timestep/reference-frame/seed/NVT/NVE semantics explicitly match the oracle;
- reduction of one completed case overlaps the next simulated case in a deterministic concurrency test;
- GPU simulation concurrency can remain one while reduction concurrency is independently >0;
- case receipt is published only after successful complete reduction/digest validation;
- restart reuses only authenticated accepted cases and reruns stale/corrupt/incomplete cases;
- simulated ENOSPC/write failure leaves earlier accepted receipts untouched;
- process cancellation kills owned process groups and preserves accepted prior cases;
- queue, log and trajectory-reduction memory are bounded;
- final candidate/run ordering is independent of completion order.

### R7 — G7/RELAX regression preservation and complexity reconciliation

No redesign of RELAX is required unless a regression is discovered.

Revalidate:

- global `(candidate, base)` scheduling;
- worker-private calculator reuse with no cross-worker mutable sharing;
- sequential ASE FIRE semantics per trajectory;
- convergence/pass-fail equivalence;
- vectorized topology reductions;
- bounded nested native CPU width and resource admission;
- deterministic aggregation and failure cleanup.

Remove any superseded wrapper/scheduler path exposed by R2/R5 consolidation.

### R8 — reopened G10 final affected-surface reconciliation and functional acceptance

After all executable reopen gates close:

1. re-derive the complete affected behavioral surface from the assembled source; do not use this file list as a hard boundary;
2. search for stale field names, duplicate schedulers, duplicate runtime/scientific policy authorities, obsolete compatibility write paths, unused execution fields and superseded caches;
3. run complete focused tests for every new/modified mechanism;
4. run the full affected regression surface for all modified **and transitively affected** old modules;
5. run repository-required broader/full available tests, triaging every failure/error that touches the affected surface rather than dismissing failures by aggregate category;
6. execute bounded integration through real production interfaces from preflight through preparation/materialization, TRAIN/EVAL, DEPLOY, PES, RELAX, DYN and final selection/publication boundaries available in the representative fixture;
7. execute restart integration at EVAL and DYN partial-completion boundaries;
8. execute cancellation/failure integration across worker and owned external-process boundaries;
9. confirm LOCKED-TEST2 activation boundary and prediction-evidence isolation remain unchanged;
10. record unavailable checks explicitly.

A test harness may stub heavyweight dependencies **below** the production command/public boundary, but it must not reconstruct the orchestration logic being tested.

Functional G10 acceptance requires all material command paths to execute successfully on bounded representative data. The target-workstation production-scale GPU qualification remains deferred after this acceptance.

## 6. Initially expected affected behavioral surface for the reopen

At minimum re-evaluate:

- `mdstats/training_data/campaign_execution.py`;
- `mdstats/training_data/model_features.py`;
- `mdstats/training_data/inference_parallel.py`;
- `mdstats/training_data/_campaign_cli_core.py` and any current CLI facade/owner;
- `mdstats/training_data/deploy_verify.py`;
- `mdstats/training_data/pes_verify.py`;
- `mdstats/training_data/relax_verify.py`;
- `mdstats/training_data/dyn_verify.py`;
- `mdstats/training_data/artifact_staging.py`;
- indexed ExtXYZ/replay helpers and sparse target consumers;
- resource-plan/work-queue helpers used by evaluation or verification;
- configuration generation/resolution and legacy migration paths;
- state-store/persistence readers and writers for evaluation execution evidence and DYN receipts;
- LOCKED static inference consumers after the activation boundary;
- all tests that call the affected production interfaces or monkeypatch previous ownership boundaries.

The final R8 review must expand this list when implementation changes reveal additional callers/consumers.

## 7. Stage-local regression rule

Every R0-R6 material behavior-changing stage must pass, before dependent work continues:

1. focused tests for the new/changed mechanism;
2. regression for all old behavior plausibly affected by that stage;
3. direct integration through the real affected product boundary where appropriate.

A later final test run does not substitute for a failed or skipped stage-local regression gate.

## 8. Production qualification boundary

Do **not** perform full production-scale GPU qualification during this reopen implementation round.

After R8 functional acceptance, prepare the final target-workstation qualification handoff. That qualification should characterize the assembled final candidate on the user's target GPU/system, including:

- joint static inference `(batch_size, concurrent_jobs)` optimum and headroom;
- GPU utilization and peak/steady VRAM;
- CPU/RAM usage;
- LAMMPS external process concurrency;
- DYN simulation/reduction overlap;
- disk/I/O and scratch footprint;
- cold/warm cache and restart behavior;
- end-to-end/per-stage wall time.

No accelerator-performance claim is accepted before that qualification.

## 9. Genuine redesign triggers

Stop the current implementation gate and reopen design only if one of these occurs:

- batching/concurrency changes accepted scientific results beyond frozen tolerances, proving the supposedly runtime-only choice is scientifically material;
- the clean removal of batch size from scientific identity would invalidate accepted historical evidence without a defensible compatibility migration;
- one canonical inference owner cannot represent both EVAL and verification resource requirements without reintroducing materially different semantics;
- target-GPU evidence later proves multi-model static concurrency or multi-LAMMPS concurrency needs a qualitatively different resource model;
- DYN streaming cannot preserve required duplicate-timestep/reference semantics without a different file/index representation;
- post-R6 representative profiling shows exact topology/neighbor operations dominate enough to justify a separately qualified compiled kernel;
- implementation broadens the affected surface into an architectural subsystem not covered by the parent PERF1 design.

Ordinary bugs, missing tests, local API drift, conservative resource-estimate corrections and scheduler refactoring are **not** redesign triggers.

## 10. Completion condition

This reopen workplan can be closed only when:

- R0-R8 are accepted;
- the prior DEPLOY/PES hard failure is covered by a real-boundary regression;
- scientific policy and runtime execution identity are cleanly separated;
- static inference has one authoritative operating-point/resource owner;
- one-unit resource infeasibility fails closed;
- EVAL backpressure uses explicit bounded resource accounting;
- immutable concurrent publication cannot overwrite accepted different bytes;
- DYN simulation and reduction are independently scheduled and restart-safe;
- the re-derived affected surface passes final regression and bounded assembled integration;
- unavailable checks are explicitly recorded;
- production GPU qualification is left as a separate final handoff rather than being conflated with implementation acceptance.

Until those conditions are met, MLFF-END-TO-END-PERF1 remains **ACTIVE / OPEN FOR IMPLEMENTATION**.

## 11. Implementation acceptance record (2026-08-24)

R0-R8 functional implementation is accepted on branch
`feat/mlff-end-to-end-performance-v1`.

- Stage-local focused gates passed after each material change. The final
  re-derived affected surface passed `250 passed, 2 skipped`; the skips require
  a real LTA training root and an explicitly supplied real MACE model.
- Bounded production-interface acceptance passed `121 passed`, covering the
  available preparation/materialization and preflight authorities, EVAL,
  command-level DEPLOY/PES consumers, RELAX, split DYN and restart behavior,
  SELECT2, and LOCKED-TEST2 boundaries. Heavy dependencies were stubbed only
  below the production boundary under test.
- Static checks passed: module compilation, `git diff --check`, and searches for
  removed field names, superseded operating-point/cache owners, and the former
  shallow pipeline estimator.
- The repository-wide available run, excluding the independently uncollectable
  `tests/test_mesh_topology_revision_stage1.py` missing-fixture module, reached
  `3183 passed, 36 skipped, 261 failed, 84 errors` in 511.67 seconds. The error
  population is dominated by absent repository LTA JSON/data fixtures. The
  failure population is dominated by historical release/manual assertions and
  tests monkeypatching the user-facing CLI facade rather than its implementation
  owner. Every failure touching this reopen's changed or transitively affected
  execution surface was isolated and rerun after repair; the final affected
  surface above is green.
- No supported target GPU qualification was run. Production-scale GPU/VRAM,
  LAMMPS concurrency, disk/I/O, cold/warm cache, restart, and end-to-end timing
  qualification remains the separate handoff defined in section 8.

The reopened functional acceptance conditions are therefore closed. This
workplan remains in `workplans/active/` only as the handoff authority for the
explicitly deferred target-workstation qualification; repository hygiene may
archive it after that separate qualification is accepted.
