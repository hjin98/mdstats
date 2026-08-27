---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-SCREEN-PRODUCTION-DECOUPLING-REPAIR1-REVIEW1
protocol_version: 5.7.0
status: active
created_date: 2026-08-25
reviewed_head: bdad4f78f6790412114a6de5af45cfc3b2b23fe9
parent_workplan: MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md
routing: implementation-nonconformance
---

# Repair-1 Review-1 Amendment — Semantic lifecycle/recovery ownership

## Why this amendment exists

A target-host interruption trace exposed a second concrete acceptance defect in the target-size screen/production decoupling implementation. During public `select-target-size`, the private generic TRAIN2 scheduler emitted:

```text
[TRAIN scheduler] interruption received ...
... interrupted after preserving its latest checkpoint; rerun `train` to continue with --restart_latest
[TRAIN scheduler] holding ... queued run(s) ... rerun `train` to resume
```

Current source still contains those role-blind recovery strings. At the same time, current public `train` correctly rejects a nonterminal target-size study and states that `select-target-size` owns the flexible-fidelity experiment; public `evaluate` likewise rejects pre-selection use. Therefore the interruption instruction is not merely imprecise wording: it directs the operator to a public command that is intentionally unauthorized for the current lifecycle state, and mentions `--restart_latest` even though that is not a public campaign-CLI option.

This is an **implementation nonconformance/local consequence** under the already accepted CLI and decoupling architecture. It does not reopen the scientific screen/production design and does not justify a second scheduler.

## Current architecture audit

The reviewed implementation already aligns with the clean architecture in several important respects and these behaviors are protected by this amendment:

1. Public `select-target-size` owns the complete nonterminal target-size experiment.
2. Public TRAIN2 `train` is production-only and fails closed before target-size selection is frozen.
3. Public TRAIN2 `evaluate` is production-checkpoint evaluation only and fails closed before target-size selection is frozen.
4. `_next_public_operation()` derives the TRAIN2 public operation from the semantic lifecycle rather than the historical static `prepare -> preflight -> train -> evaluate` sequence.
5. Target-size screen execution reuses the generic private TRAIN2 execution/evaluation engines rather than duplicating them.
6. Screen runtime authorization filters to `study.next_training_sizes`, the ordered screening seed set, final-development jobs, and the active semantic boundary.
7. Screen and production run IDs/filesystem roots are separated by `target-size-screen` versus `production` namespaces.
8. Screen scheduler/budget horizon is `n3`; production `n` is independent.
9. Selected production materialization explicitly reopens production preflight/train/evaluate state so completed internal screening markers cannot by themselves mark production work complete.

The remaining confusion is concentrated in **execution-role context that is lost inside the shared scheduler/recovery surface**. Internal stage keys `train`/`evaluate` are also reused as physical-engine progress markers during selection, but current lifecycle projection and production-materialization reset contain that reuse. Do not introduce new persistent stage schemas solely for aesthetics. Refactor those keys only if the real-owner tests below expose an actual collision or false authorization.

## Frozen semantic ownership

The public TRAIN2 lifecycle remains:

```text
prepare
  -> preflight [screening]
  -> select-target-size
       -> private TRAIN2 engine to n1
       -> private target-size endpoint evaluation/reduction
       -> private TRAIN2 continuation to n2
       -> private target-size endpoint evaluation/reduction
       -> private TRAIN2 continuation to n3
       -> private target-size endpoint evaluation/reduction
       -> freeze N*
  -> materialize
  -> preflight [production]
  -> train
  -> evaluate
  -> verify
```

The distinction is ownership, not implementation duplication:

```text
public select-target-size
    owns screen lifecycle/recovery
    reuses private TRAIN2 scheduler/runtime

public train
    owns production training lifecycle/recovery
    reuses the same private TRAIN2 scheduler/runtime
```

A private engine may retain generic TRAIN2 terminology internally, but no user-facing instruction, next-action message, retry/restart instruction, or durable public lifecycle projection may contradict the semantic public owner.

## Required repair design

### A1 — Make shared scheduler execution context explicit

Give the generic TRAIN2 execution path one authoritative semantic execution context, derived from the actual current authority rather than guessed from log text.

Minimum required information is equivalent to:

```text
execution_role: target-size-screen | production | historical
public_owner_command: select-target-size | train
resume_command: select-target-size | train
operator_label: target-size screen | production training | historical training
```

This does not require a new public class or persistent schema. A small immutable private context/helper or explicit parameters are acceptable. Prefer deriving the context from the verified target-size study/policy generation already loaded by the execution owner so caller flags cannot create a contradictory role.

Do not create a second scheduler, second restart mechanism, or parallel checkpoint state machine.

### A2 — Recovery instructions must follow the semantic owner

For a nonterminal target-size screen:

- Ctrl-C/SIGTERM/disk-stop/retriable infrastructure interruption must preserve the same durable screen checkpoint semantics as today;
- operator-facing recovery must say to rerun `select-target-size`;
- it must state that the screen resumes from the latest authenticated durable checkpoint when appropriate;
- it must not instruct the operator to invoke public `train` or `evaluate`;
- it must not expose `--restart_latest` as a campaign-CLI option unless that option actually exists and is part of the accepted public interface. Under the current interface, automatic restart is preferred and no such flag should be advertised.

For selected production training, the corresponding recovery owner is public `train`.

For historical non-TRAIN2 campaigns, preserve their established public semantics unless an affected regression proves a problem.

### A3 — Contextualize scheduler/progress presentation without duplicating machinery

The current screen can print `Training campaign`, `[TRAIN ...]`, and `[TRAIN scheduler]` while the public operation is `select-target-size`. That is not itself a scientific-state defect, but it amplifies the same lifecycle ambiguity that produced the invalid recovery advice.

Make the operator-visible role unambiguous with the smallest coherent change. Acceptable forms include, for example:

```text
Target-size screen execution
[TARGET-SIZE 1/10] ...
[TARGET-SIZE scheduler] ...
```

or a clearly stated role line followed by generic private-engine labels. The exact typography is delegated; the required outcome is that an operator can distinguish target-size screening from production training without interpreting run internals.

Do not rename scientific schemas or duplicate progress infrastructure merely for presentation.

### A4 — Preserve public command guards and semantic status/advance

Current public guards are correct and must remain fail-closed:

```text
nonterminal target-size study + public train    -> reject, no mutation
nonterminal target-size study + public evaluate -> reject, no mutation
```

After a screen interruption and process/store reopen:

```text
status next command  = select-target-size
advance executes     = select-target-size
```

A stale internal `train`/`evaluate` stage marker must never make public status or `advance` recommend production `train`/`evaluate` before selection and production materialization/preflight are complete.

### A5 — Re-derive queued work from current screen authority on every resume

The scheduler may report that queued tasks were held when a process is interrupted, but those in-memory tasks are not a second persisted authorization authority.

On rerun of `select-target-size`, real orchestration must rebuild the admissible population from the current persisted study:

```text
study.next_training_sizes
x screening_optimizer_seeds
x final-development screen jobs
x current boundary execution limit
```

Required consequences:

- interrupted coarse screen may resume remaining coarse candidates;
- after coarse reduction, eliminated candidates cannot reappear at the short stage;
- after short reduction, non-finalists cannot reappear at the final stage;
- a stale screen campaign/run-plan record cannot authorize work outside the current study population;
- the surviving `(size,seed)` trajectory retains its exact screen run identity and checkpoint/optimizer/RNG continuation ancestry.

### A6 — Contain the existing internal `train`/`evaluate` stage-marker reuse

The current implementation projects internal `store.stage("train")` / `store.stage("evaluate")` activity into the semantic `select-target-size` public step and later resets production train/evaluate state during selected-size materialization. This is acceptable only while it remains an internal implementation detail with no cross-role authorization leak.

Do not add a persistent role-scoped stage schema preemptively. Instead prove:

1. interrupted screening can leave the internal train stage WAITING/RUNNING while public status remains `select-target-size`;
2. final screen selection cannot make production `evaluate` appear complete;
3. selected-size materialization resets/rebinds production preflight/train/evaluate as required;
4. screen execution records/checkpoints remain role-namespaced and cannot satisfy production restart;
5. production records cannot satisfy screen restart.

If any of these fail under real-owner tests, then minimally role-scope the affected persistent stage/record authority. That evidence, not naming preference, is the redesign trigger.

## Proxy-proof acceptance additions

These tests extend Repair-1 and use the same bounded disk-backed real-campaign harness. Only expensive external MACE numerical computation may be faked below the real orchestration/runtime owners.

### T1 — Real screen interruption/recovery at the first boundary

Drive the real public `command_select_target_size` path with an active default screen. Let the real scheduler/runtime owner launch a bounded fake external child that produces a valid durable partial checkpoint, then trigger the real interruption path.

Required observations:

- interruption returns the established interruption status (currently 130) without corrupting the store;
- durable screen checkpoint/attempt record exists under a `target-size-screen-*` run namespace;
- output clearly identifies target-size screen execution;
- output says to rerun `select-target-size` (or equivalently that `select-target-size` is the resume owner);
- output contains no instruction to rerun public `train` or `evaluate`;
- output does not advertise nonexistent campaign flag `--restart_latest`;
- public status after close/reopen reports `select-target-size` as the next operation;
- public `advance` resolves to the same operation.

Do not monkeypatch the scheduler interruption handler, command routing, `_next_public_operation`, `CampaignStore`, screen run-plan builder, TRAIN2 runtime-plan builder, or restart/companion validation to obtain this result.

### T2 — Public train/evaluate remain fail-closed while screen is active

Against the same persisted interrupted screen:

- invoke public `train` and public `evaluate`;
- both must fail before scheduling/evaluation work;
- target-size study digest, execution records, stage authority, checkpoint files, and DATA8 scientific payloads must remain unchanged except permitted diagnostic/event logging;
- error text must direct the operator to `select-target-size`.

### T3 — Real screen resume uses the same continuation authority

Rerun public `select-target-size` after T1 without manually supplying a restart flag.

Required observations:

- the same surviving screen run identity is used;
- the latest durable screen checkpoint is selected by the real restart owner;
- optimizer/RNG/schedule authority remains the same screen trajectory;
- planned horizon remains `n3`, execution limit remains the active boundary;
- completed work is not restarted from epoch zero or duplicated;
- selection proceeds through the normal endpoint evaluation/reduction owner.

Repeat a bounded version after at least one reduction boundary so stale queued/eliminated candidates are proven absent from the next stage.

### T4 — Production interruption uses production recovery semantics

After target size is frozen, selected production materialization and production preflight are current, invoke real public `train` through the same bounded fake numerical seam and interrupt it.

Required observations:

- run namespace is `production-*`;
- recovery directs to public `train`, not `select-target-size`;
- automatic restart behavior is described accurately without exposing private/nonexistent flags;
- no screen checkpoint can satisfy the production restart owner.

### T5 — Stage-marker containment across the role boundary

Exercise real selection completion -> materialize -> production preflight lifecycle.

Required observations:

- target-size completion does not cause production train/evaluate to report complete;
- materialization/preflight establish fresh production lifecycle state;
- `status` and `advance` agree at every boundary;
- internal screen `train`/`evaluate` markers cannot authorize production work;
- no new persistent role-scoped stage schema is required if the existing projection/reset mechanism proves these invariants.

### T6 — Structural anti-regression check

Add a narrow source/behavioral guard for the shared scheduler recovery path:

- role-independent interruption/failure messages must not hard-code `rerun `train``;
- role-independent messages must not advertise `--restart_latest` as a campaign-CLI flag;
- the public owner/resume command must come from the semantic execution context.

This guard complements T1-T5; it does not replace them.

## Integration with the parent Repair-1 gates

This amendment is mandatory for Repair-1 closeout.

- Incorporate A1-A5 into the real-owner harness and default/nondefault screening gate.
- Incorporate A6/T5 into the cross-role restart and lifecycle gate.
- T1-T4 are stage-local affected regression for the scheduler/recovery repair.
- T1-T6 must pass again on the final assembled candidate after any later executable edits that can affect campaign orchestration/restart.
- Existing proxy tests may remain as cheap unit coverage, but they cannot close these semantic-owner claims.

Repair-1 remains **NO-PASS** until the original real-owner acceptance obligations and this amendment are both closed.

## Reopen only on evidence

Reopen the architecture beyond this bounded repair only if real-owner tests show one of the following:

- the generic TRAIN2 scheduler cannot carry semantic execution role without duplicating or corrupting restart authority;
- existing internal `train`/`evaluate` stage-marker reuse actually causes cross-role authorization/restart corruption that cannot be contained by the current lifecycle projection/reset;
- screen and production run namespaces still collide in a real filesystem/restart consumer;
- current target-size screen restart requires an operator-visible manual flag that the accepted public lifecycle cannot represent safely.

Absent such evidence, preserve the existing clean architecture and repair the shared scheduler/recovery context locally.
