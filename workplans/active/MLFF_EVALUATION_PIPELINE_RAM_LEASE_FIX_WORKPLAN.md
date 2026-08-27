---
kind: implementation-workplan
workplan_id: MLFF-EVAL-PIPELINE-RAM-LEASE-FIX
protocol_version: 5.8.0
---

# MLFF Evaluation Pipeline RAM Lease Fix Workplan

## Current status

**R1–R3 closed by commit `9bde51f` on branch `workplan/eval-pipeline-ram-lease-fix`; awaiting REVIEW4 acceptance.**

The implementation series through commit `8b3c34e99559350718f574e709c9884f29a1b90d` preserves the accepted one-outer-owner RAM-lease architecture and closes the original 3 MiB retained-growth fixture, but REVIEW3 found that the implementation still substitutes a fixed `2 * minimum_inference_reservation` admission heuristic for a real bound on unknown prepare -> retained-payload growth. That heuristic is not invariant-preserving and can still manufacture avoidable J=1 admission failures under larger but feasible retained-growth geometries.

REVIEW3 also confirms that the nested lease binding remains directionally correct, the authentic target-size cache-only -> uncached integration path is substantially closed, and no target-size scientific/persistence drift is evident.

## Closure evidence (`9bde51f`)

- **O4 — producer/backpressure:** `_unclassified_prepare_admissible` replaces the `2 * J1` heuristic; `test_review3_5mib_retained_growth_geometry_sequences_and_completes` fails on `8b3c34e` (observed `prepared:review3-1` charge against `ledger_owned=3407872 / budget=5242880`) and passes after repair with no simultaneous retained charge (`retained_peak == 1`); `test_bounded_retained_upper_bound_preserves_multi_prepare_overlap` proves overlap survives when a sound bound exists. REVIEW2 `(1.5, 1.5)` / `(1.25, 1.75)` and cache-only -> uncached cases retained.
- **O3 — RAM-coordinate re-clamp:** `test_staged_lease_ram_reclamp_excludes_out_of_lease_profile_evidence` proves prior 60 000-byte evidence is excluded under a later 25 000-byte lease (selection-level, not constructor-field inspection).
- **O6 — lifecycle:** `test_success_reuses_released_inference_reservation_in_same_invocation`, `test_bounded_oom_inference_terminal_failure_releases_ledger`, `test_all_cache_only_terminal_state_releases_unused_progress_owner` added; existing ordinary-failure / KeyboardInterrupt / sibling-cancellation coverage retained.
- **O9/O10 — regression:** affected-surface regression green — **267 passed, 1 skipped** across `test_mlff_opt_eval4_staged_evaluation_pipeline.py`, `test_mlff_static_mace_inference.py`, `test_mlff_target_size_v5_topology.py`, `test_mlff_inference_parallel_scheduler.py`, `test_mlff_dyn_verify2.py`, `test_mlff_campaign_cli.py`, `test_mlff_target_size_study_v5.py`, `test_mlff_target_size_repair1_real_owner.py` (skip = `real LTA training root not supplied`). Two **pre-existing, unrelated** failures remain in `test_mlff_opt_eval4_specification.py` (stale `0.20.140a0` version pin; missing `OPT-EVAL4` architecture-manual heading), outside this workplan's frozen scope.

The accepted architecture remains valid. Do not reopen target-size science, flexible fidelity, one-outer-owner evaluation, or static-inference architecture unless a stated redesign trigger fires.

## Objective and protected concerns

Repair the staged-evaluation resource-admission deadlock introduced by the PERF1 nested inference topology without weakening bounded-memory execution, static-inference optimization, target-size scientific behavior, or the one-outer-owner evaluation architecture.

The original production failure is not a TARGET-SIZE-V5 ranking/checkpoint defect. `_run_staged_evaluation_tasks(...)` intentionally collapses evaluation to one outer inference owner while allowing that owner a theoretical inner `joint_model_jobs` ceiling. Under the reported production geometry, a fixed reservation for all theoretical inner jobs exceeds the staged RAM sub-budget. The accepted correction is launch-local selection of the widest currently admissible inner width plus a scoped incremental RAM lease consumed by nested static inference.

The remaining REVIEW3 defect is producer-side: retained prepared-payload size is not generally known before preparation, yet the current implementation permits concurrent unclassified preparation based on a fixed multiple of minimum inference memory. Because retained growth is not bounded by that multiple, concurrency can still create a state that safe sequencing would avoid.

Protected concerns:

- Preserve exactly one outer evaluation inference owner.
- Preserve the existing joint static-inference batch/model-shell optimizer and RAM/VRAM/OOM learning.
- Preserve global RAM policy and the stricter staged-pipeline RAM sub-budget; do not widen or disable either bound.
- Preserve real shared-residency, working-reservation, retained prepared/result, and finalization accounting.
- Preserve preparation -> inference -> finalization overlap whenever resource feasibility is actually provable.
- Preserve cache-only bypass, restart/reuse, and authentic publication behavior.
- Preserve target-size ranking, target/replay semantics, seeds, flexible-fidelity boundaries, screen/production horizons, checkpoint authority, metrics, numerical/scientific policy, data identity, and persisted campaign authority.
- Preserve dynamics staged-pipeline semantics except where shared scheduler accounting must be corrected consistently.
- Do not add a second persistent resource authority, public buffering contract, or persisted lease/profile identity merely to repair this local scheduler defect.
- Full production GPU qualification remains deferred to FINAL-GPU1; only bounded functional accelerator checks are part of ordinary acceptance if affected.

## Engineering envelope and frozen product design

### 1. Single RAM owner and forward-progress invariant

The staged pipeline owns its RAM sub-budget. Nested static inference consumes a scoped lease from that owner and must never assume the whole process-global RAM budget is available.

For every nonterminal state containing work that may require inference, the scheduler must preserve a path to at least one minimum runnable J=1 inference. Once inference-ready work exists, exactly one of these must be true:

1. an admissible inference owner can launch;
2. an active owned operation exists whose completion can genuinely release the blocking resource; or
3. execution terminates with a causal resource-admission error representing a genuinely irreducible state.

The scheduler must never create case (3) by over-admitting earlier work.

### 2. Exact RAM-lease coordinate

The outer inference lease is the incremental inference-stage RAM envelope inside the staged ledger. It includes incremental private-provider-pool growth and inference execution/transient memory.

It excludes:

- shared/base runtime residency already charged once by the staged ledger;
- prepared payload bytes charged separately;
- finalize payload/working reservations charged separately; and
- other concurrently owned stage reservations.

Do not re-charge base-provider residency merely to satisfy this repair. Preserve the existing automatic inference-reservation semantics and the positive explicit `evaluation_inference_working_memory_mib` meaning as total inference-stage working memory.

### 3. Joint-model width remains a ceiling

For evaluation, `joint_model_jobs` remains a theoretical inner concurrency ceiling, not mandatory preallocation.

For automatic inference working-memory accounting, choose the largest launch-local width `J >= 1` whose existing reservation policy fits the current staged ledger:

```text
for J = theoretical_joint_cap ... 1:
    reservation(J) = existing inference working-reservation policy
    choose first J admitted by the current ledger
```

A positive explicit inference working-memory override remains total-stage memory, not per-model memory.

### 4. Nested static-inference authority consumes the lease

The assembled prediction path must bind `StaticInferenceRuntimeAuthority` to the current outer lease:

```text
maximum_concurrent_model_jobs <= current outer leased J ceiling
live incremental RAM allowance <= min(current safe process-global allowance,
                                      current outer inference lease RAM)
```

VRAM remains governed by existing live VRAM authority. The lease is runtime-only and must not change scientific identity, checkpoint/cache identity, campaign persistence, or runtime-profile compatibility identity.

Compatible persisted runtime-profile evidence may be reused only after re-clamping against both current job-width and current RAM lease coordinates on every invocation.

### 5. Provable retained-growth admission — REVIEW3 correction

REVIEW3 establishes that a fixed multiplier such as `prepare_reservation + 2 * minimum_inference_reservation` is **not** a valid proxy for unknown prepared-payload growth. If no authoritative pre-prepare bound relates the future retained payload to that quantity, the multiplier has no safety meaning.

Frozen behavior:

- The scheduler must protect one minimum J=1 inference envelope while admitted work is unclassified or known inference-requiring and no real inference reservation already supplies that envelope.
- A prepare-working reservation and the future retained prepared payload are distinct accounting coordinates. The future retained payload may exceed the preparation working reservation.
- Concurrent unclassified preparation is allowed only when the scheduler has a **sound prospective upper bound** for the retained transition(s) being admitted and the complete worst-case admission equation fits the staged budget while preserving one J=1 envelope.
- A sound bound must come from authoritative pre-prepare information already available to the production scheduler/task contract. Do not invent a constant multiple of J=1, preparation working memory, or another unrelated estimate merely to retain concurrency.
- If no sound retained-payload upper bound exists for an unclassified task, the scheduler must conservatively sequence that unknown transition. At minimum, do not admit another unbounded unclassified transition whose eventual retained growth cannot be proven coexistible with already-owned retained/working/inference state plus one J=1 envelope.
- Conservative sequencing is not considered an illicit global serialization workaround when the live equation cannot prove concurrent safety. Multi-prepare overlap remains required where a real bound or already-resolved retained size makes safety provable.
- Once a retained payload is known and authoritatively charged, normal overlap may resume whenever the live ledger equation permits it.
- A cache-only classification may bypass inference. If no remaining admitted/pending work can require inference, unused prospective headroom may be released.
- The prospective J=1 envelope must transfer into the real inference reservation without transient overbooking or double-counting.
- When inference is active, its real reservation is the progress envelope for that owner; do not add a duplicate synthetic J=1 guard for the same inference.
- If a single task's actual retained payload plus minimum J=1 genuinely cannot fit even when safely isolated from avoidable concurrent producers, fail causally as an irreducible task geometry rather than misclassifying a scheduler-created conflict.

The implementation must not preserve the REVIEW3 `2 * J1` heuristic unless independent evidence proves it is derived from a real retained-size upper bound for every affected production task. In the currently reviewed code, no such contract is established.

Required REVIEW3 counterexample:

```text
pipeline budget              = 5.0 MiB
prepare working reservation  = 1.0 MiB
minimum inference J=1        = 1.0 MiB
prepare workers              = 2
prepared payload A           = 2.25 MiB
prepared payload B           = 2.75 MiB
```

A fixed `2 * J1` launch heuristic may admit both preparations even though their later retained transitions can fill or exceed the ledger while J=1 is required. Yet safe sequencing is feasible because each retained payload individually coexists with J=1:

```text
2.25 + 1.0 <= 5.0 MiB
2.75 + 1.0 <= 5.0 MiB
```

The scheduler must complete this geometry by safe admission/ordering rather than manufacture a false irreducible failure.

### 6. Causal admission diagnostics

Distinguish controller admission, staged byte-ledger/RAM admission, and true invariant stall. A RAM admission failure must truthfully report enough of the failed equation to diagnose it, including relevant queued/ready counts, pipeline budget, total ledger-owned bytes, retained payload bytes/reservations where available, minimum inference reservation, and relevant job ceiling/selected width.

Do not label aggregate ledger ownership as merely `retained`.

### 7. Lease/progress lifecycle

Every inference lease, inference reservation, prospective progress owner/credit, and any retained-growth admission token introduced by this repair must be transferred or released exactly once on all terminal paths: success, ordinary stage failure, sibling cancellation, bounded OOM terminal failure, `KeyboardInterrupt`, and propagated exceptions.

Cache-only bypass must not acquire an inference lease. Task/context-local lease state must not leak into later work. An all-cache-only terminal state must not leave a stale progress owner.

## Implementation obligations

### O1 — Production geometry

A deterministic bounded real-scheduler test must retain the production-equivalent J=8 / ~4 GiB-per-job / ~18.6 GiB staged-budget arithmetic and prove descent to the widest admissible J with one outer inference owner.

### O2 — Launch-local RAM-aware inner width

Preserve largest-safe-J, exact-fit, one-unit-over-boundary, J=1 minimum, explicit-override semantics, and outer peak=1 evidence through the real scheduler.

### O3 — Nested-runtime lease binding and RAM/job profile re-clamp

**Required end state:** nested static inference receives no larger job ceiling or incremental RAM allowance than the current outer lease while retaining live global RAM/VRAM clamping and OOM learning.

**Still open after REVIEW3:** the current reused-profile test proves job-width narrowing but does not prove RAM-coordinate exclusion.

**Required acceptance:** exercise the actual `_predict_model_on_atoms` / static-executor path with a compatible prior profile containing at least one previously feasible operating point whose RAM requirement exceeds the later smaller `InferenceLease.ram_allowance_bytes`. Under that smaller lease, prove the out-of-lease RAM point is not selected or attempted, while job-width re-clamping also remains enforced. Constructor-field inspection or a numerically large lease that all old evidence already fits is insufficient.

### O4 — Provable starvation-proof producer/backpressure policy

**Required end state:** no prepare admission or prepare -> retained transition may consume the future J=1 progress path when safe sequencing could avoid the conflict.

Required consequences:

- remove or justify with a real retained-size contract any fixed `N * J1` proxy used as a retained-growth safety bound;
- use an authoritative prospective retained upper bound when one exists;
- otherwise sequence unbounded unclassified retained transitions conservatively;
- preserve one J=1 envelope across unresolved classification/retention;
- transfer that envelope into inference without double-counting;
- resume multi-prepare/stage overlap whenever retained sizes/bounds make the equation provably safe;
- preserve cache-only bypass.

**Required REVIEW3 regression — must fail on `8b3c34e99559350718f574e709c9884f29a1b90d`:** exercise the real staged scheduler with the 5 MiB / 1 MiB prepare / 1 MiB J=1 / 2.25+2.75 MiB retained geometry above and at least two configured preparation workers. Prove the scheduler does not admit work into an avoidable retained-growth collision and completes both tasks through a feasible safe ordering.

Retain the REVIEW2 3 MiB `(1.5, 1.5)` and heterogeneous `(1.25, 1.75)` regressions as useful boundary coverage, but they no longer constitute sufficient proof by themselves.

Also retain a cache-only -> uncached ordering case through the real scheduler.

### O5 — Genuine irreducible admission and truthful diagnostics

A task is irreducible only after avoidable producer-created conflicts are excluded. Required acceptance includes:

- a single-task retained payload + J=1 geometry that genuinely cannot fit and fails causally;
- the REVIEW3 avoidable multi-prepare retained-growth geometry, which must progress;
- truthful diagnostic terminology/values for genuine failures.

### O6 — Lease, progress, retained-growth admission, cleanup, and cancellation

**Still open after REVIEW3.** Successful progress-owner transfer evidence and the existing KeyboardInterrupt observation are useful but incomplete.

Required same-owner/call-through evidence through the real scheduler must cover:

- success where later work in the same scheduler invocation reuses released capacity;
- ordinary inference/stage exception;
- bounded OOM terminal failure where applicable to touched runtime behavior;
- sibling failure/cancellation;
- `KeyboardInterrupt`;
- cache-only bypass with no inference lease;
- progress guard/credit -> inference transfer with no double-counting or stale guard;
- all-cache-only terminal state releasing unused progress ownership;
- any new retained-bound/admission token introduced by REVIEW3, on success and exceptional exits.

Tests may observe real ledger/context operations by call-through instrumentation but may not replace scheduler decisions. Starting a new scheduler invocation is not evidence that the prior scheduler cleaned up its owners.

### O7 — Scientific, persistence, and identity non-regression

No target-size decision rule, epoch boundary, seed semantics, training/evaluation metric, target/replay membership, checkpoint identity, persisted authority, prediction-cache identity, runtime-profile compatibility identity, or screen/production horizon semantics may change.

Run affected target-size/evaluation regression and structurally inspect the final diff for unauthorized schema/identity/scientific changes.

### O8 — Shared staged-runner compatibility

Evaluation-specific RAM leasing and producer/backpressure changes must not alter dynamics job-count/resource semantics. Preserve dynamics overlap, authenticated-receipt/cache-only bypass, failure cancellation, interruption, low-CPU/serial behavior, and any shared multi-prepare paths affected by the final scheduler change.

### O9 — Authentic assembled cache-only -> uncached target-size/evaluation path

**Semantically closed by REVIEW3, subject to final rerun after R1 changes.**

The existing bounded integration exercises the real target-size/evaluation orchestration, real SQLite restart/reuse, real staged scheduler, production cache-bypass decision, lease acquisition for missing work, publication, and final reduction while faking expensive numerical inference below the semantic-owner boundary.

Do not weaken that test. Because R1 will change scheduler behavior again, rerun this assembled path on the final candidate as part of R3.

### O10 — Final regression/check evidence

Repository/project-required checks and the complete affected-surface regression must execute on the final assembled commit. Missing GitHub CI is not itself a failure if equivalent repository-approved local commands execute and their results are recorded, but an unexecuted required check is not a pass.

Record commands/CI, final commit identity, and pass/fail results. Source review or a production run cannot substitute for missing regression/integration evidence.

## Implementation authority

### Frozen

- One outer evaluation inference owner.
- Theoretical joint-model width is an upper bound, not mandatory preallocation.
- The staged pipeline owns its RAM sub-budget; nested static inference consumes a scoped incremental RAM lease.
- Shared/base residency already charged once is outside the incremental inference lease; private provider-pool growth and inference transient memory are inside it.
- Automatic inference reservation retains existing conservative semantics; explicit inference working-memory overrides remain total-stage overrides.
- No widening/removal of RAM bounds and no deletion of provider/job RAM accounting as a shortcut.
- One minimum J=1 progress path must remain feasible across unclassified preparation and retained-payload transitions.
- **No fixed multiplier of J=1 or preparation working memory may be treated as a retained-payload upper bound unless an authoritative production contract actually establishes that relationship.**
- Concurrent unclassified preparation requires a sound prospective retained upper bound; absent such a bound, conservative sequencing is required until the unknown retained transition is resolved.
- Progress ownership transfers into real inference without double-counting.
- The scheduler may not create false irreducible states by over-admitting producer work.
- Compatible static-inference profiles re-clamp to current job-width and RAM lease coordinates on every invocation.
- Lease/reservation/progress/admission cleanup on every terminal path.
- Runtime-only resource ownership; no scientific/persisted/profile-compatibility identity changes.
- Full production GPU qualification remains deferred.

### Delegated

- Exact helper/data-structure names for progress ownership, retained-bound claims, or admission tokens.
- Whether a real retained upper bound is derived from existing task metadata, input geometry, a production size estimator already owned by the task, or another authoritative pre-prepare source.
- Exact transfer mechanics between progress ownership and inference reservation, provided no transient overbooking/double-counting occurs.
- Conservative sequencing mechanics when no retained upper bound exists.
- Local refactoring that centralizes admission arithmetic without expanding public surface.
- Exact diagnostic formatting provided accounting coordinates remain truthful.

### Reopen only on evidence

Reopen only the affected accounting surface if implementation proves one of the following:

1. `selected_concurrent_model_jobs` is an exact required width rather than a ceiling in a production consumer.
2. Base-provider residency cannot be separated from incremental private-provider/transient accounting without changing the established evidence model.
3. Explicit inference working-memory override semantics differ authoritatively from total inference-stage memory.
4. Normal supported automatic configuration makes genuine J=1 falsely impossible solely because unavoidable accounting double-counts a material component.
5. Correct retained-growth/progress protection cannot be represented inside the existing staged-ledger scheduler without a public buffering/configuration contract change.
6. Production `requires_inference` classification can be authoritatively known before preparation for all affected task types.
7. Product requirements demand concurrent unclassified preparation even when no sound retained upper bound exists; this would require an explicit retained-size/resource contract redesign rather than another heuristic.

Do not reopen target-size scientific architecture, flexible fidelity, production horizon semantics, or unrelated PERF1 machinery absent independent evidence.

## Expected affected surface

Re-derive from the final diff. Initially expect:

- `mdstats/training_data/_campaign_cli_core.py` — producer admission, retained-growth feasibility, progress ownership, guard-to-lease transfer, diagnostics, cleanup.
- `campaign_execution.py` / `model_features.py` only if actual RAM-coordinate profile re-clamp is defective; no redesign expected.
- `inference_parallel.py` only if lease/context lifecycle needs correction.
- `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py` — REVIEW3 retained-growth reproducer, prior REVIEW2 boundaries, genuine irreducible case, lifecycle and shared-runner regressions.
- `tests/test_mlff_static_mace_inference.py` — prior-larger-RAM-profile -> smaller-current-RAM-lease execution evidence.
- target-size/evaluation topology/integration tests — preserve and rerun the authentic cache-only -> uncached assembled path.
- shared dynamics staged-runner regressions.

Do not modify target-size scientific decision logic or persistence schemas as part of this rework.

## Task-specific acceptance matrix

1. Production J=8 / ~4 GiB/job / ~18.6 GiB staged geometry selects the largest safe J.
2. Largest-safe-J exact fit and one-unit-over boundaries pass.
3. One outer evaluation owner remains peak=1.
4. Outer RAM/job lease hard-bounds nested static inference.
5. A compatible profile containing RAM evidence above a later smaller lease is actually re-clamped; the out-of-lease RAM point is not selected/attempted.
6. Cache-only tasks acquire no inference lease.
7. REVIEW2 3 MiB retained-growth cases remain green.
8. **REVIEW3 5 MiB / 2.25+2.75 MiB retained-growth geometry progresses by safe ordering and fails on `8b3c34e...`.**
9. No arbitrary `N * J1` heuristic can admit an unbounded retained transition unless backed by an authoritative retained-size bound.
10. When no bound exists, unclassified transitions are conservatively sequenced; when a bound exists and fits, multi-prepare overlap remains available.
11. Genuine single-task J=1 impossibility fails causally; producer-created impossibility does not.
12. Explicit inference-memory override retains total-stage semantics.
13. Progress/inference/admission owners are never double-counted or leaked.
14. Cleanup is demonstrated on success, ordinary exception, bounded OOM, sibling cancellation, KeyboardInterrupt, cache-only, and all-cache-only termination.
15. Serial/low-CPU and dynamics shared-runner behavior remain valid.
16. Authentic target-size/evaluation cache-only -> uncached restart/reuse path reruns successfully on the final candidate.
17. Diagnostics distinguish aggregate ledger ownership from retained payload/reservations.
18. If CUDA-specific behavior changes, bounded functional accelerator checks run; no long production qualification.
19. Complete final affected regression and repository-required checks execute and pass, or unavailable required checks remain explicitly blocking.

The principal semantic owner is the real staged evaluation scheduler as invoked by real evaluation/target-size orchestration. Direct helper tests or patched scheduler decisions cannot close owner-level claims. Call-through instrumentation is allowed only for observation.

Production qualification remains **deferred**. Long real-data GPU performance/RAM/VRAM qualification remains FINAL-GPU1 work on the target machine.

## Rework implementation sequence

### Gate R1 — REVIEW3 producer-admission closure

Repair O4/O5/O6 as one coherent scheduler stage:

- remove the fixed `2 * J1` retained-growth heuristic unless it is proved to arise from an authoritative retained upper bound;
- locate/reuse a sound pre-prepare retained upper bound if one already exists;
- otherwise conservatively sequence unbounded unclassified retained transitions;
- preserve the J=1 progress path through retained transitions;
- transfer progress ownership to inference without double-counting;
- preserve largest-safe-J and work-conserving overlap where safety is provable;
- close progress/admission-owner lifecycle on all terminal paths.

Required stage-local evidence before R2/R3 closure:

- REVIEW3 5 MiB / 2.25+2.75 MiB real-scheduler reproducer failing on `8b3c34e...` and passing after repair;
- REVIEW2 retained-growth and cache-only -> uncached scheduler regressions;
- a positive high-headroom/bounded-retained case proving multi-prepare overlap is not gratuitously disabled when safety is provable;
- genuine irreducible single-task J=1 case;
- production geometry and J boundaries;
- same-owner success/exception/OOM/cancellation/KeyboardInterrupt/cache-only/all-cache-only cleanup evidence;
- staged scheduler and shared dynamics affected regression.

### Gate R2 — Profile RAM/job evidence closure

Close the remaining O3 evidence gap:

- execute a compatible larger-cap profile under a smaller current RAM/job lease;
- ensure at least one prior feasible RAM operating point exceeds the new lease;
- prove that point is not selected or attempted;
- retain job-width cap propagation evidence.

O9 assembled integration is already semantically credited, but must be rerun after R1 because scheduler changes can invalidate its execution evidence.

### Gate R3 — Final assembled closure

After all executable edits:

1. reconcile every frozen obligation and REVIEW1/REVIEW2/REVIEW3 finding against the assembled candidate;
2. re-derive the final affected behavioral surface from the final diff;
3. run complete affected regression across target-size/evaluation, static inference, staged scheduler, shared dynamics, cleanup/failure, cache/restart, and low-resource paths;
4. rerun the authentic target-size cache-only -> uncached integration path;
5. run repository/project-required checks;
6. record commands/CI, final commit identity, and pass/fail results; an unavailable required check remains blocking;
7. structurally confirm no target-size science, identity, persistence, or configuration-semantics drift.

Only after R1-R3 close may this workplan be marked complete/archived.

## Relationship to active workplans

This workplan repairs a PERF1 staged-evaluation scheduler/resource-authority regression surfaced by target-size screening. On `fix/target-size-exact-boundary-screening`, the controlling target-size scientific/campaign correction remains `MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md` with its active amendments. This RAM-lease plan is orthogonal resource-authority/backpressure work required for reliable uncached staged evaluation and does not supersede or reopen the exact-boundary scientific design.

`MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_FINAL_CLOSURE_WORKPLAN.md` and the older Repair1 chain remain archived historical material and impose no active gates.

## REVIEW3 handoff closure

Independent review after `8b3c34e99559350718f574e709c9884f29a1b90d` preserves the accepted architecture and routes bounded rework as follows:

1. **Blocking implementation nonconformance — retained-growth safety:** a fixed `2 * J1` admission heuristic is not a retained-payload bound. Concurrency requires an authoritative prospective retained upper bound; absent one, conservatively sequence the unresolved transition.
2. **Required reproducer:** add the 5 MiB / 1 MiB prepare / 1 MiB J=1 / 2.25+2.75 MiB retained geometry that defeats the current heuristic while remaining feasible under safe ordering.
3. **O3 evidence blocker:** prove actual RAM-coordinate profile re-clamping with prior evidence above the later lease, not merely job-width narrowing.
4. **O6 evidence blocker:** prove progress/admission-owner cleanup on success, ordinary failure, bounded OOM, sibling cancellation, KeyboardInterrupt, cache-only, and all-cache-only paths.
5. **O9 credited:** the authentic target-size cache-only -> uncached restart/reuse integration is materially adequate, subject to final rerun after scheduler changes.
6. **R3 evidence blocker:** execute and record complete affected regression/repository checks on the final assembled commit.

No current evidence requires reopening one-outer-owner evaluation, the launch-local lease coordinate, nested static-inference architecture, target-size science, flexible-fidelity/horizon semantics, or persistence identity.