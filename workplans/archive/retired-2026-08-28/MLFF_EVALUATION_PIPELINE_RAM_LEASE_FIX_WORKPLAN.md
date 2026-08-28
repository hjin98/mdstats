---
kind: implementation-workplan
workplan_id: MLFF-EVAL-PIPELINE-RAM-LEASE-FIX
protocol_version: 5.8.0
---

# MLFF Evaluation Pipeline RAM Lease Fix Workplan

## Current status

**REWORK REQUIRED after REVIEW4 independent Software Design review.**

The implementation through executable commit `9bde51fa4dd7ba13ade9840c40a6cfb873e0e9f3` and closure-evidence commit `1e1b3a069cc9d17c2a3bd000edd0b2be003d46a7` correctly removes the REVIEW3 fixed `2 * J1` evaluation heuristic, introduces an explicit `retained_upper_bound` contract, conservatively sequences unbounded transitions, and closes the previously open O3 RAM-coordinate profile re-clamp evidence. REVIEW4 nevertheless found one remaining blocking producer-admission defect: the bounded-retained worst-case equation reconstructs coexistence from retained payloads, active inference, prospective bounds, and J=1 but omits other live staged-ledger ownership, notably `shared:runtime-residency`. It can therefore approve bounded concurrent preparation that the real ledger cannot sustain, manufacturing an avoidable J=1 failure.

The accepted architecture remains valid. Rework is restricted to the bounded-retained prospective ledger projection plus final affected regression. O3 profile re-clamping and the authentic O9 target-size restart/cache integration remain semantically credited unless the new source delta touches their owning surfaces; O9 must still rerun in final assembled regression because scheduler behavior changes again.

The previously recorded **267 passed, 1 skipped** result is useful baseline evidence but no longer constitutes final R3 closure because the scheduler requires another executable correction.

## Objective and protected concerns

Repair staged-evaluation RAM admission so every producer decision is made in the same staged-ledger coordinate that actually owns runtime memory, without weakening bounded-memory execution, static-inference optimization, cache/restart behavior, target-size scientific semantics, or the one-outer-owner evaluation architecture.

Protected concerns:

- Preserve exactly one outer evaluation inference owner.
- Preserve launch-local largest-admissible inner `joint_model_jobs` selection.
- Preserve the existing joint static-inference batch/model-shell optimizer and RAM/VRAM/OOM learning.
- Preserve global RAM policy and the stricter staged-pipeline RAM sub-budget; do not widen or disable either bound.
- Preserve real shared/base runtime residency, working reservations, retained prepared/result payloads, finalization reservations, and any other live staged-ledger owner.
- Preserve preparation -> inference -> finalization overlap whenever coexistence is actually provable.
- Preserve conservative sequencing when retained growth is unknown.
- Preserve cache-only bypass, restart/reuse, publication, and target-size reducer behavior.
- Preserve target-size ranking, target/replay semantics, seeds, flexible-fidelity boundaries, screen/production horizons, checkpoint authority, metrics, scientific/numerical policy, data identity, cache identity, and persisted campaign authority.
- Preserve dynamics staged-pipeline semantics except where a shared helper must remain ledger-correct.
- Do not introduce a second persistent resource authority, public buffering contract, or persisted lease/profile identity merely to repair admission arithmetic.
- Full production GPU qualification remains deferred to FINAL-GPU1; ordinary acceptance uses bounded functional coverage only if accelerator behavior is affected.

## Engineering envelope and frozen product design

### 1. Single staged RAM authority and forward progress

The staged pipeline owns its RAM sub-budget. Nested static inference consumes a scoped runtime lease from that owner and never independently assumes the whole process-global RAM budget.

For every nonterminal state containing work that may require inference, the scheduler must preserve a path to at least one runnable J=1 inference. Once inference-ready work exists, one of these must be true:

1. an admissible inference owner can launch;
2. an active owned operation can genuinely release the blocking resource; or
3. execution terminates with a causal resource-admission error representing a genuinely irreducible state.

The scheduler must not create case (3) by over-admitting producers.

### 2. Exact inference-lease coordinate

The outer inference lease is incremental inference-stage RAM inside the staged ledger. It includes incremental private-provider-pool growth and inference execution/transient memory.

It excludes memory already charged elsewhere in the staged ledger, including shared/base runtime residency, prepared payloads, finalize payload/working reservations, and other concurrent stage owners. Exclusion from the **inference lease** does not mean exclusion from the **pipeline admission equation**: all live staged-ledger ownership remains part of total pipeline feasibility.

Preserve the positive explicit `evaluation_inference_working_memory_mib` meaning as total inference-stage working memory.

### 3. Joint-model width is a ceiling

For evaluation, `joint_model_jobs` is a theoretical inner concurrency ceiling, not mandatory preallocation. Automatic admission chooses the largest current width `J >= 1` whose inference reservation fits after transfer of any prospective J=1 progress ownership. Explicit total-stage inference-memory overrides retain their existing semantics.

### 4. Nested static inference consumes the lease

The assembled prediction path must enforce:

```text
maximum_concurrent_model_jobs <= current outer leased J ceiling
live incremental RAM allowance <= min(current safe process-global allowance,
                                      current outer inference lease RAM)
```

Compatible persisted runtime-profile evidence may be reused only after job-width and RAM re-clamping to the current lease. The lease is ephemeral runtime state and does not alter scientific, persistence, checkpoint/cache, or profile-compatibility identity.

**REVIEW4 state:** O3 is semantically closed by the actual execution-path test that excludes prior 60,000-byte evidence under a later 25,000-byte lease. Preserve that behavior and rerun its regression if the final source delta can plausibly affect it.

### 5. Provable retained-growth admission

A fixed multiple of J=1 or preparation working memory is not a retained-payload bound. Concurrent unclassified evaluation preparation is permitted only when every modeled unresolved retained transition has an authoritative prospective upper bound and the complete prospective staged-ledger equation fits. If no sound bound exists, conservatively sequence the unresolved transition.

A sound retained bound must come from authoritative pre-prepare production information already owned by the task contract. Do not invent a constant multiplier merely to preserve concurrency.

### 6. Complete prospective ledger projection — REVIEW4 correction

The bounded-retained admission test must project the **real live staged ledger**, not reconstruct only selected memory classes.

Frozen behavior:

- Start from current ledger ownership in the same byte coordinate used by `_PipelineByteLedger`.
- Identify exactly which currently owned reservations are being replaced by prospective retained bounds. Normally this includes the `prepare:<task>` working reservations for already-active bounded unclassified tasks whose future retained payloads are represented by those bounds.
- Preserve every other live owner that survives the modeled transition, including at minimum:
  - `shared:runtime-residency`;
  - already-retained `prepared:` / `result:` payloads not being replaced;
  - active `inference:` reservations;
  - active/waiting finalization-related reservations or other ledger owners that can coexist with the projected transition;
  - any future staged owner added by the scheduler unless it is explicitly and correctly replaced in the projection.
- If an existing `progress:minimum-inference` owner is already present and the projection separately adds the required J=1 envelope, subtract/replace that exact owner so the envelope is counted exactly once.
- Add the authoritative retained upper bounds for every unresolved transition represented by the projection, including the proposed new task.
- Add one minimum J=1 envelope exactly once when no active inference reservation already supplies that progress path.
- Separately retain ordinary launch-time admission for the proposed preparation working reservation; a safe retained-state projection does not waive the requirement that the current working phase itself fit.
- Do not use `retained_payload_bytes` alone as the fixed baseline because it intentionally excludes shared residency and other working/stage reservations.
- Do not simply use `ledger.total_bytes + sum(bounds)`: current preparation working reservations represented by retained bounds must be replaced, not double-counted.

Conceptually:

```text
fixed_live_ownership
    = current ledger ownership
      - exact current reservations replaced by prospective retained bounds
      - existing progress owner if that same envelope is re-added below

prospective_retained_state
    = fixed_live_ownership
      + sum(authoritative retained upper bounds for modeled unresolved tasks)
      + one J=1 progress envelope when not already supplied by active inference

admit bounded concurrency only if:
    current working-phase admission fits
    AND prospective_retained_state <= pipeline budget
```

The implementation may realize this with a helper, ledger projection API, explicit owner filtering, or equivalent local mechanism. The material invariant is exact replacement accounting over the complete live ledger.

#### Required REVIEW4 counterexample

The corrected scheduler must handle this real-scheduler geometry:

```text
pipeline budget              = 5.0 MiB
shared runtime residency     = 1.0 MiB
prepare working reservation  = 1.0 MiB
minimum inference J=1        = 1.0 MiB
prepare workers              = 2
retained upper bound A       = 2.0 MiB
retained upper bound B       = 2.0 MiB
actual retained A            = 2.0 MiB
actual retained B            = 2.0 MiB
```

The REVIEW4 implementation at `9bde51f...` can evaluate only `2 + 2 + 1 = 5 MiB` and admit both preparations because it omits the 1 MiB shared residency. The actual projected ledger is `1 + 2 + 2 + 1 = 6 MiB`, so concurrent admission is unsafe.

Safe sequencing is feasible because each task individually satisfies:

```text
shared 1.0 + retained 2.0 + J=1 1.0 = 4.0 MiB <= 5.0 MiB
```

The scheduler must therefore delay the unsafe second transition and complete both tasks rather than manufacture an irreducible failure.

Retain the REVIEW2 3 MiB retained-growth cases and the REVIEW3 5 MiB 2.25+2.75 MiB unbounded-sequencing case as regression boundaries.

### 7. Causal diagnostics

RAM admission failures must report the actual failed equation with truthful terminology: queued/ready counts where relevant, pipeline budget, total ledger-owned bytes, retained payload bytes where useful, minimum inference reservation, relevant model-job width/cap, and any material fixed owner needed to explain the failure. Aggregate ledger ownership must not be mislabeled as retained payload.

A producer-created conflict must not be reported as an irreducible J=1 failure.

### 8. Lease/progress/reservation lifecycle

Every inference lease, inference reservation, progress owner/credit, and any admission token introduced by this repair must be transferred or released exactly once on success, ordinary failure, sibling cancellation, bounded OOM terminal failure, `KeyboardInterrupt`, and propagated exceptions.

Cache-only bypass acquires no inference lease. Context-local lease state may not leak. All-cache-only completion leaves no stale progress owner.

**REVIEW4 state:** existing O6 evidence is materially adequate for the current ownership model. If the REVIEW4 implementation introduces a new temporary projection/admission owner, add lifecycle tests for it; pure arithmetic projection with no new owner may reuse the existing lifecycle evidence subject to final rerun.

## Implementation obligations

### O1 — Production geometry

Preserve bounded production-equivalent J=8 / ~4 GiB-per-job / ~18.6 GiB staged-budget coverage proving descent to the widest admissible inner J with one outer inference owner.

### O2 — Launch-local RAM-aware inner width

Preserve largest-safe-J, exact-fit, one-unit-over-boundary, J=1 minimum, explicit total-stage override semantics, and outer peak=1 evidence through the real scheduler.

### O3 — Nested-runtime lease and profile re-clamp

**Semantically closed by REVIEW4.** Preserve the actual `_predict_model_on_atoms` / static-executor test where compatible prior RAM evidence above the later lease is excluded from selection/attempt while an in-lease point remains usable. Rerun when affected by final source changes.

### O4 — Complete starvation-proof producer/backpressure policy

**Required end state:** no preparation admission or prepare->retained transition can consume the future J=1 path when safe sequencing could avoid the conflict.

Required consequences:

- retain authoritative `retained_upper_bound` semantics;
- conservatively sequence unbounded unclassified transitions;
- for bounded overlap, use complete live-ledger replacement projection per Section 6;
- preserve every non-replaced live ledger owner, especially shared runtime residency;
- count prospective J=1 exactly once;
- avoid double-counting replaced prepare/progress reservations;
- resume multi-prepare/stage overlap when the complete equation proves it safe;
- preserve cache-only bypass.

**Required REVIEW4 regression — must fail on `9bde51fa4dd7ba13ade9840c40a6cfb873e0e9f3`:** use the real staged evaluation scheduler with at least two configured prepare workers and the 5 MiB budget / 1 MiB shared residency / 1 MiB prepare / 1 MiB J=1 / bounded 2+2 MiB retained geometry above. Prove the old projection over-admits and the corrected implementation safely orders both tasks to completion.

Add a positive companion where shared residency plus bounded transitions genuinely fit and verify multi-prepare overlap remains available. This prevents the repair from degenerating into unconditional serialization.

### O5 — Genuine irreducibility and truthful diagnostics

Required acceptance:

- genuine isolated single-task retained + fixed-live-ownership + J=1 impossibility fails causally;
- REVIEW2/REVIEW3/REVIEW4 avoidable producer-created geometries progress;
- diagnostics report the real ledger coordinate and do not omit a material fixed owner from the causal equation.

### O6 — Lifecycle

Preserve same-owner/call-through evidence for success capacity reuse, ordinary failure, bounded OOM, sibling cancellation, `KeyboardInterrupt`, cache-only no-lease behavior, progress->inference transfer without double-counting, and all-cache-only release. Add coverage only for any new lifecycle-bearing owner introduced by the REVIEW4 repair.

### O7 — Scientific, persistence, and identity non-regression

No target-size decision rule, epoch boundary, seed semantics, metric, target/replay membership, checkpoint authority, cache identity, persisted authority, runtime-profile compatibility identity, or screen/production horizon semantics may change.

### O8 — Shared staged-runner compatibility

Evaluation-specific bounded-retained projection changes must not alter dynamics job-count/resource semantics. Shared helper refactors must preserve dynamics overlap, cache/authenticated bypass, failure cancellation, interruption, serial/low-CPU behavior, and existing RAM accounting.

### O9 — Authentic assembled cache-only -> uncached target-size/evaluation path

**Semantically credited.** Preserve the existing real target-size/evaluation orchestration with real SQLite restart/reuse, real staged scheduler, production cache-bypass decision, lease acquisition for missing work, publication, and final reduction. Expensive numerical inference may remain the only substituted layer below that semantic-owner boundary.

Because R1 changes again, rerun this assembled path on the final candidate.

### O10 — Final regression/check evidence

The complete final affected-surface regression and repository/project-required checks must execute on the final assembled commit. Missing GitHub CI is acceptable only if equivalent repository-approved local commands execute and are recorded. An unexecuted required check is not a pass.

The earlier 267-passed baseline does not close O10 after REVIEW4 because the scheduler source must change again.

## Implementation authority

### Frozen

- One outer evaluation inference owner.
- Theoretical joint-model width is an upper bound.
- Staged pipeline RAM ledger is the single pipeline-memory authority.
- Incremental inference lease excludes already-ledgered shared/base residency, but producer admission must still include that residency through the live ledger.
- Automatic inference reservation and explicit total-stage override semantics remain unchanged.
- One J=1 progress path remains feasible across unresolved preparation/retention.
- No arbitrary fixed multiplier substitutes for retained-size bounds.
- Unbounded transitions are conservatively sequenced.
- Bounded concurrent admission uses complete live-ledger **replacement projection**, preserving every non-replaced owner.
- Shared runtime residency and future unknown ledger-owner classes are not silently dropped from prospective feasibility.
- Replaced preparation/progress reservations are not double-counted.
- Compatible static-inference evidence re-clamps to current job and RAM lease.
- Runtime-only resource ownership; no scientific/persistence/profile identity changes.
- Full production GPU qualification remains deferred.

### Delegated

- Exact helper/API used to calculate projected ledger ownership.
- Whether projected replacement owners are identified by explicit owner names/prefixes, scheduler task identity, or a local structured accounting helper.
- Exact retained-bound derivation where an authoritative production bound exists.
- Conservative sequencing mechanics for unbounded tasks.
- Exact progress->inference transfer implementation provided J=1 is counted exactly once.
- Local refactoring that centralizes admission arithmetic without expanding public API.
- Diagnostic formatting provided accounting labels and values remain truthful.

### Reopen only on evidence

Reopen only the affected accounting surface if implementation proves:

1. `selected_concurrent_model_jobs` is an exact mandatory width in a production consumer rather than a ceiling;
2. base/shared residency cannot be represented as ordinary persistent staged-ledger ownership without changing established resource identity;
3. explicit inference working-memory override semantics differ authoritatively from total inference-stage memory;
4. correct replacement projection is impossible with current ledger ownership metadata and requires a new public resource contract;
5. product requirements demand concurrent unclassified work without a sound retained bound;
6. production `requires_inference` can be authoritatively known before preparation for all relevant tasks, allowing the conservative rule to narrow.

Do not reopen target-size science, flexible fidelity/horizon semantics, one-outer-owner evaluation, or unrelated PERF1 machinery absent independent evidence.

## Expected affected surface

Re-derive from the final diff. Initially expect:

- `mdstats/training_data/_campaign_cli_core.py` — bounded-retained prospective projection and possibly diagnostics only.
- `tests/test_mlff_opt_eval4_staged_evaluation_pipeline.py` — REVIEW4 shared-residency bounded-overlap negative/positive cases plus affected scheduler regression.
- `campaign_execution.py`, `inference_parallel.py`, `model_features.py` should not require changes unless new evidence surfaces; O3/lease behavior is already accepted.
- target-size/evaluation integration and shared dynamics tests must be rerun as final affected evidence.

Do not modify target-size scientific decision logic or persistence schemas.

## Task-specific acceptance matrix

1. Production J=8 geometry selects widest safe J.
2. Largest-safe-J exact-fit and one-unit-over boundaries pass.
3. Outer inference peak remains one.
4. Outer RAM/job lease bounds nested static inference.
5. Prior profile RAM evidence above a smaller current lease is excluded in actual execution.
6. Cache-only tasks acquire no inference lease.
7. REVIEW2 retained-growth cases remain green.
8. REVIEW3 unbounded 5 MiB / 2.25+2.75 MiB geometry progresses by safe sequencing.
9. **REVIEW4 5 MiB + 1 MiB shared residency + bounded 2+2 MiB geometry is not concurrently over-admitted and completes by safe ordering.**
10. A companion bounded geometry that truly fits including shared residency still achieves multi-prepare overlap.
11. Prospective bounded admission preserves all non-replaced ledger owners and replaces only the exact modeled prepare/progress reservations.
12. No arbitrary `N * J1` heuristic admits unbounded retained growth.
13. Genuine isolated J=1 impossibility fails causally; producer-created impossibility does not.
14. Explicit inference-memory override retains total-stage semantics.
15. Progress/inference/admission owners are never double-counted or leaked.
16. Lifecycle coverage remains green across success/failure/OOM/cancellation/interrupt/cache-only/all-cache-only paths.
17. Serial/low-CPU and dynamics shared-runner behavior remain valid.
18. Authentic target-size/evaluation cache-only -> uncached restart/reuse path reruns successfully.
19. Diagnostics distinguish total ledger ownership from retained payload and expose material fixed ownership when needed.
20. If CUDA-specific behavior changes, bounded functional accelerator checks run; no long production qualification.
21. Final complete affected regression and repository-required checks execute and pass, or unavailable required checks remain explicitly blocking.

The principal semantic owner is the real staged evaluation scheduler as invoked by real evaluation/target-size orchestration. Helper tests or patched scheduler decisions cannot close owner-level claims; call-through instrumentation may observe but not replace production decisions.

## Rework implementation sequence

### Gate R1 — REVIEW4 complete-ledger projection closure

Repair O4/O5 as one localized scheduler stage:

- replace the partial bounded-retained equation with complete live-ledger replacement projection;
- preserve shared runtime residency and every other non-replaced live owner;
- subtract only exact current reservations replaced by modeled retained bounds;
- count J=1 exactly once;
- preserve existing working-phase admission and safe bounded overlap;
- do not introduce new persistent authority.

Required stage-local evidence:

- REVIEW4 shared-residency 5 / 1 / 1 / 1 / 2+2 MiB reproducer failing on `9bde51f...` and passing after repair;
- positive bounded-overlap case with nonzero shared residency that genuinely fits;
- REVIEW2 and REVIEW3 retained-growth regressions;
- genuine irreducible J=1 case;
- production geometry and J-boundary tests;
- existing lifecycle tests if no new owner is introduced, otherwise new lifecycle coverage for that owner;
- shared dynamics affected regression.

### Gate R2 — retained accepted lease/profile evidence

O3 is already semantically closed. No new R2 implementation is required unless R1 touches nested lease/profile code. Reuse the accepted O3 evidence when unaffected; otherwise rerun the RAM/job profile re-clamp test before R3.

### Gate R3 — final assembled closure

After the REVIEW4 executable correction:

1. reconcile every frozen obligation and REVIEW1-REVIEW4 finding against the assembled candidate;
2. re-derive the final affected behavioral surface from the final diff;
3. run complete affected regression across staged evaluation, target-size/evaluation, static inference where affected, shared dynamics, lifecycle/failure/cache/restart, and low-resource paths;
4. rerun the authentic target-size cache-only -> uncached restart/reuse integration;
5. run repository/project-required checks;
6. record commands/CI, exact final commit, and pass/fail results; unavailable required checks remain blocking;
7. structurally confirm no target-size science, identity, persistence, or configuration-semantics drift.

Only after R1 and R3 close, with R2 still valid or freshly rerun as required, may this workplan be marked complete/archived.

## Relationship to active workplans

This workplan repairs a PERF1 staged-evaluation scheduler/resource-authority regression surfaced by target-size screening. On `fix/target-size-exact-boundary-screening`, `MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_WORKPLAN.md` remains the controlling target-size scientific/campaign authority. This RAM-lease plan is orthogonal resource/backpressure work and does not supersede or reopen that scientific design.

The older target-size production-decoupling final-closure and Repair1 chain remain archived historical material and impose no active gates.

## REVIEW4 handoff closure

Independent review after `1e1b3a069cc9d17c2a3bd000edd0b2be003d46a7` preserves the accepted architecture and routes bounded rework as follows:

1. **Blocking implementation nonconformance — incomplete bounded-retained projection:** the current equation omits live ledger owners such as `shared:runtime-residency`; bounded concurrency must project the complete live ledger and replace only the exact reservations represented by prospective retained bounds.
2. **Required reproducer:** add the 5 MiB budget / 1 MiB shared residency / 1 MiB prepare / 1 MiB J=1 / bounded 2+2 MiB retained geometry that defeats `9bde51f...` while remaining feasible under safe sequencing.
3. **Positive concurrency proof:** retain multi-prepare overlap when the same complete equation, including shared residency, genuinely fits.
4. **O3 credited:** actual RAM-coordinate profile re-clamping is accepted and need not be redesigned.
5. **O6 credited:** current lifecycle ownership evidence is materially adequate unless REVIEW4 introduces a new lifecycle-bearing owner.
6. **O9 credited:** authentic target-size cache-only -> uncached restart/reuse integration remains adequate but must rerun after the scheduler correction.
7. **R3 invalidated only where affected:** the prior 267-pass baseline remains useful, but final closure requires fresh affected regression and repository checks against the corrected final commit.

No current evidence requires reopening one-outer-owner evaluation, launch-local lease semantics, nested static-inference architecture, target-size science, flexible fidelity/horizon semantics, or persistence identity.
