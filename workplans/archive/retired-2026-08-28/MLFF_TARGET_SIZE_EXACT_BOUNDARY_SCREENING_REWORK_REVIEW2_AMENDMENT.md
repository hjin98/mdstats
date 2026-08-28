---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-EXACT-BOUNDARY-SCREENING-REWORK-V1-REVIEW2
parent_workplan: CODE-MLFF-TARGET-SIZE-EXACT-BOUNDARY-SCREENING-REWORK-V1-REVIEW1
protocol_version: 5.7.0
status: active
created_date: 2026-08-26
reviewed_implementation_head: 41715aa212a9e4cf5d10e26a91ad6ebde734c959
review_verdict: fail
routing: implementation_nonconformance
---

# Exact-Boundary Screening Rework — Review-2 Final Functional Closure Amendment

## Authority

This amendment extends `MLFF_TARGET_SIZE_EXACT_BOUNDARY_SCREENING_REWORK_REVIEW1_AMENDMENT.md` after review of implementation head `41715aa212a9e4cf5d10e26a91ad6ebde734c959`.

The parent product design remains accepted. No target-size architecture redesign is required. Exact `n1 -> n2 -> n3` screening, independent production `n`, authoritative DATA8 job-protocol classification, boundary-only target-size reporting/evidence, fresh production training, and cross-role restart isolation remain frozen.

Where this amendment is more specific than Review-1 concerning remaining blockers, functional acceptance, or production qualification, this amendment controls.

## Review-2 disposition

The implementation now materially closes the earlier R1 source-level recovery defect:

- durable TRAIN2 runtime state is reconciled before scheduler disposition rather than only for `SUCCEEDED` outer execution records;
- overshot authenticated progress routes through target-size overshoot invalidation;
- runtime activation rejects restored/current epochs above the active `execution_epoch_limit` before another optimizer update.

Those mechanisms do not require redesign. Remaining closure consists of:

1. one genuine continuation-integrity implementation defect: persisted companion model/EMA/RNG content is not fully authenticated against the summary digests before restart state is applied; and
2. bounded functional integration/recovery acceptance through the real target-size orchestration owners.

**Full production campaign/GPU qualification is not an implementation blocker and is explicitly deferred to the user.**

## R3 — authenticate exact TRAIN2 continuation content, not only companion structure

### Protected concern

Exact-boundary screening requires a surviving `(size, seed)` to continue the same scientific trajectory across boundaries. TRAIN2 persists a raw MACE checkpoint together with a runtime companion containing state not safely reducible to the raw checkpoint alone, including live model parameters, EMA state, and RNG state.

The runtime summary already records content digests for this continuation state. A restart validator that verifies only protocol/budget/LR identities, checkpoint SHA, counters, filenames, and the presence/type of companion fields is insufficient: a syntactically valid `.pt` companion can contain modified model, EMA, or RNG values while retaining matching metadata.

Such corruption must not be silently accepted because it can change the post-boundary scientific trajectory.

### Frozen invariant

Before any persisted TRAIN2 companion state is used to mutate a resumed model/process:

```text
recomputed_live_parameter_digest == summary.live_parameter_digest
recomputed_rng_state_digest       == summary.rng_state_digest
recomputed_ema_state_digest       == summary.ema_state_digest
```

with the EMA rule interpreted as:

```text
EMA enabled  -> companion EMA content exists and digest matches
EMA disabled -> summary and companion both prove no EMA continuation state
```

The raw checkpoint SHA remains the authority for the raw MACE checkpoint, including optimizer/checkpoint content covered by that file. Do not create a second independent optimizer-state authority merely to satisfy this amendment.

### Required implementation consequences

1. Reuse the same canonical digest algorithms/schemas used when TRAIN2 persists:
   - live model parameters;
   - EMA state;
   - RNG state.
2. `validate_train2_runtime_continuation_artifacts()` or its owning successor must recompute those digests from the loaded companion and compare them to the authenticated runtime summary.
3. The normal `_restore_continuation()` path must not apply companion model/EMA/RNG state until equivalent content authentication has succeeded. Prefer one shared validation owner rather than duplicating subtly different checks.
4. Shape/type validation remains required, but shape/type validation does not substitute for content-digest validation.
5. Any digest mismatch is a fail-closed continuation-integrity error. Do not silently fall back to fresh training while stale continuation artifacts remain discoverable.
6. Preserve legitimate boundary expansion: changing only the active execution limit `n1 -> n2 -> n3` must not invalidate an otherwise authentic companion because the deterministic schedule/budget authorities remain unchanged.

### R3 focused acceptance

Add bounded regressions proving that a valid Torch companion is rejected when, independently:

- one live model parameter value is modified while metadata remains unchanged;
- one EMA tensor/state value is modified while metadata remains unchanged;
- one RNG state value is modified while metadata remains unchanged.

Also retain positive continuation coverage proving an untouched authentic companion resumes successfully and preserves the exact deterministic trajectory.

Replacing the whole companion with unreadable bytes is useful corruption coverage but does **not** satisfy these content-authentication cases.

## Functional acceptance versus production qualification

### Functional acceptance — implementation-owned and blocking

The remaining real-owner tests are ordinary bounded functional integration tests. They must be designed to run without production-scale training, long datasets, or target GPU hardware.

Their purpose is to establish orchestration/restart/authorization correctness, not performance or physical-model quality.

Required real semantic path remains:

```text
current TOML/config
-> real CampaignStore/current-state reconciliation
-> real target-size study/boundary owner
-> real DATA8 job lookup
-> real TrainingCampaignPlan/run construction
-> real MaceJobArtifact protocol classification
-> real shared scheduler authorization
-> real TRAIN2 runtime-plan assembly
-> bounded numerical child seam
-> real training persistence/recovery consumer
-> real exact-boundary evidence assembly
-> real reducer/ranking
-> real survivor authorization
-> real selected-size freeze
```

The public owner must remain `command_select_target_size` or the exact public CLI entry that delegates to it without replacing those semantics.

### Allowed bounded test seam

The integration harness may replace expensive work below the semantic-owner boundary:

- numerical MACE optimizer stepping/subprocess compute;
- GPU execution;
- expensive model prediction;
- large datasets, using deterministic reduced fixtures.

The bounded child may consume the **real** runtime plan/environment and emit the minimum authentic artifacts required by the real parent consumer. It must not decide:

- policy family;
- current screen boundary;
- survivor set;
- whether continuation is authorized;
- whether overshoot is valid;
- selected target size.

Those decisions remain owned by production code.

### Forbidden substitution remains unchanged

Closure evidence must not replace or substantially reimplement:

- `command_select_target_size`;
- campaign policy-family classification;
- target-size stage/boundary owner;
- shared scheduler disposition/authorization;
- `build_train2_runtime_plan()` or equivalent runtime-plan owner;
- `CampaignStore` persistence/reopen behavior;
- TRAIN2 continuation authentication;
- target-size reducer/ranking;
- survivor authorization;
- selected-size freeze/state transition.

If `_execute_train_current_authority()` or `_execute_evaluate_current_authority()` contains one of those semantic decisions, that owner cannot be patched away for the claim being tested.

### Production qualification — user-owned and nonblocking

Full real campaign qualification is intentionally outside implementation closure and will be performed by the user on the target environment.

It includes, as applicable:

- real MACE training over realistic data;
- target GPU behavior and VRAM utilization;
- production wall time/throughput;
- long-run RAM/storage/I/O behavior;
- realistic end-to-end campaign stability;
- final numerical/scientific behavior at production scale.

Codex or another implementation agent must **not** mark the implementation blocked merely because it cannot perform these production-scale or target-hardware runs.

Conversely, the deferred user qualification does not waive bounded functional tests that can establish orchestration/recovery semantics without production-scale compute.

## Gate I — continuation-content integrity

Gate I is added before final assembled acceptance.

Required completion:

- implement R3 canonical model/EMA/RNG content verification;
- ensure restart state is authenticated before application;
- run positive exact-continuation regression;
- run valid-payload tamper regressions for model, EMA, and RNG state;
- rerun affected TRAIN2 persistence/restart regression.

Gate I **fails** if a syntactically valid companion whose scientific continuation content differs from its recorded summary digests can reach resumed execution.

## Gate H — bounded real-owner functional integration closure

Review-1 Gate H remains the final executable acceptance gate, with the following explicit clarification:

**Gate H is not production qualification.** It is a bounded functional integration/recovery test suite and must not require target GPU hardware, long production data, or full scientific campaign runtime.

Required scenarios remain:

### H-A — default exact-boundary funnel `(1,3,10)`

Prove through the real target-size owners:

1. all qualified candidates are authorized only through epoch 1;
2. coarse ranking occurs before any epoch-2 authorization;
3. eliminated candidates receive no later training authorization;
4. survivors continue authentically only through epoch 3;
5. short ranking occurs before epoch-4 authorization;
6. finalists continue only through epoch 10;
7. final reduction freezes exactly one target size;
8. epoch 11 is never authorized for screening;
9. `select-target-size` returns without entering production training.

A regression to `Historical training` or a coarse full-10-epoch run must make this test fail.

### H-B — interruption/reopen continuation

Using the real persistence/recovery owners and a bounded numerical child:

1. persist authentic partial or exact-boundary TRAIN2 continuation state;
2. interrupt/close the outer command state;
3. reopen `CampaignStore` and rerun the public target-size owner;
4. prove authentic continuation is reused rather than restarting the survivor trajectory;
5. prove the reducer still interposes before authorization of the next boundary.

### H-C — interrupted overshoot

Using authentic serialized TRAIN2 state produced through the allowed bounded child seam:

1. create outer non-successful/interrupted state whose authenticated completed epoch is above the current boundary;
2. reopen through the public target-size owner;
3. prove overshoot is detected before new optimizer work;
4. prove current screen execution/evidence/selection authority is invalidated and returns to coarse;
5. prove scientifically unchanged DATA7/DATA8 remain reusable;
6. prove unauthorized checkpoint state cannot become reducer evidence.

### Scheduler-level R1 coverage

At least one focused/affected test in addition to H-C must exercise the actual production scheduler/recovery caller for the state-disposition cases that materially branch:

- recoverable progress below boundary;
- recoverable progress exactly at boundary;
- recoverable progress above boundary.

Direct helper invocation alone is insufficient for those caller-routing claims.

## Final regression closure

After Gate I and any final Gate-H harness changes:

1. re-derive the affected behavioral surface from the final diff;
2. run focused TRAIN2 persistence/restart/integrity tests;
3. run target-size classifier/scheduler/reducer/restart affected regression;
4. execute H-A/H-B/H-C on the final candidate;
5. run repository-required checks intersecting the affected surface;
6. record unavailable **bounded functional** checks as blocking rather than silently converting them into deferred production qualification.

Do not require full production campaign execution for implementation PASS.

## Merge/PASS boundary

The implementation may be judged **PASS for merge/functional closure** when all of the following hold:

- parent exact-boundary workplan obligations remain satisfied;
- Review-1 R1 implementation remains state-agnostic and fail-closed;
- Gate I companion-content integrity passes;
- bounded scheduler/recovery coverage passes;
- Gate H H-A/H-B/H-C real-owner functional integration passes;
- final affected-surface regression passes;
- no newly discovered material correctness/scientific/recovery blocker remains.

The implementation does **not** need real production campaign/GPU qualification to reach this PASS boundary.

After merge/functional closure, the user will perform the deferred real campaign qualification. Any defect discovered there reopens only the affected product surface based on evidence.

## Implementation authority

### Frozen

- exact target-size screening remains `n1 -> n2 -> n3` with reducer interposition at every boundary;
- production `n` remains independent and production starts fresh;
- authentic continuation is required for checkpoint/model/EMA/RNG state;
- model/EMA/RNG companion content must match the summary digests before restart state is applied;
- overshoot authorization is based on authenticated runtime progress, not outer execution terminality;
- bounded real-owner functional integration is implementation-owned and blocking;
- production-scale/GPU campaign qualification is user-owned and deferred, not an implementation blocker.

### Delegated

- exact factoring of shared companion-content digest validation;
- exact bounded child implementation/transport;
- exact interruption injection point;
- exact test fixture size and synthetic data representation;
- exact diagnostics for integrity mismatches and overshoot recovery.

### Reopen only on evidence

Reopen the affected design surface only if concrete implementation evidence proves one of the following:

- persisted TRAIN2 companion state cannot be canonically authenticated against its summary without changing the persistence contract materially;
- exact deterministic continuation requires scientific state not currently persisted/authenticated;
- the real target-size semantic owner cannot be exercised with a bounded numerical seam and would intrinsically require production-scale/GPU execution.

Missing target GPU access, long runtime, production data volume, or inability to perform final real campaign qualification is **not** a redesign or implementation blocker.
