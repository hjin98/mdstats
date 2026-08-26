---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-SCREEN-PRODUCTION-FINAL-CLOSURE
protocol_version: 5.7.0
status: active
created_date: 2026-08-25
reviewed_head: 892bed8ee2320d76e17491b7c71d29f46417adb2
supersedes_for_active_closure:
  - MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md
  - MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW1_AMENDMENT.md
  - MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW2_AMENDMENT.md
---

# MLFF Target-Size Screen/Production Final Closure Workplan

## Objective

Close the single remaining blocker in the target-size screen/production decoupling work: prove, through the real public orchestration owners, that interrupted target-size screening and interrupted selected-size production training persist authentic resumable state across close/reopen and resume through the correct semantic owner without cross-role checkpoint leakage.

This is the final revision of this repair chain. It is an implementation/acceptance closure plan, not an architecture redesign.

## Diagnosis and protected concerns

Independent review of head `892bed8ee2320d76e17491b7c71d29f46417adb2` found the product mechanism substantially correct by source inspection:

- one shared scheduler is retained;
- screen and production roles are distinct;
- screen horizon remains `n3`, production horizon remains independent `n`;
- `select-target-size` owns screening and public `train` owns selected-size production;
- role-aware recovery messaging is corrected;
- interrupted execution may persist an authenticated checkpoint catalog;
- checkpoint bytes are re-authenticated before continuation;
- stale TRAIN2 schedule authority is rejected before training;
- the private external numerical-child seam is below scheduler/runtime/restart ownership.

The remaining blocker is narrower: the committed tests still prove interruption/reopen/resume mainly at `execute_training_run` level and manually persist the interrupted record. They do not yet prove the assembled path in which the real public command, shared scheduler, scheduler interruption/finalization, `CampaignStore`, lifecycle projection, reopen, and restart owner all participate.

Protected concerns:

1. A green lower-level executor test must not substitute for proof of the scheduler/orchestration owner that previously contained the lifecycle bug.
2. Testability must not introduce a second scheduler, restart authority, checkpoint selector, or parallel persistence path.
3. The external fake may replace numerical MACE work only; it must not manufacture scheduler state, execution records, checkpoint catalogs, survivor sets, lifecycle transitions, or restart decisions.
4. Existing accepted architecture and already-cleared source behavior must not be reopened merely to satisfy a test harness.

## Scope reduction and retirement of prior obligations

This plan intentionally retires the broad Repair-1 / Review-1 / Review-2 closure matrix as standalone active gates.

The following are **retired from active rework** because the latest independent review found no demonstrated product defect in them and they are not necessary to close the remaining blocker:

- redesign of the screen/production architecture;
- replacement of the shared scheduler;
- role-scoped persistent train/evaluate stage keys absent a demonstrated collision;
- re-proving every historical migration permutation as a standalone gate;
- re-running every production-`n` and `n1/n2/n3` configuration frontier as a standalone gate;
- re-proving nondefault `2/5/12/40` funnel geometry as a standalone final-closure requirement;
- re-proving DATA7/DATA8 scientific-payload preservation when no final-closure code change touches that boundary;
- re-proving source-level public `train`/`evaluate` ownership guards independently of the assembled recovery test;
- repeating prior helper/unit evidence for checkpoint tamper rejection, stale schedule rejection, or semantic role messaging unless final code changes plausibly invalidate it;
- broad repository-wide qualification or GPU/long real-data production qualification.

Those areas may be inspected or tested only when the final assembled test exposes a concrete failure that implicates them, or when a final code change plausibly affects them. Existing still-valid evidence is reused.

The archived decoupling architecture remains authoritative and unchanged.

## Engineering envelope

The final accepted behavior is:

```text
screening:
  public select-target-size
  -> real TRAIN2 authorization
  -> real shared scheduler
  -> target-size-screen run namespace
  -> interruption persists authentic resumable execution/checkpoint state
  -> close/reopen
  -> next public operation remains select-target-size
  -> rerun select-target-size automatically resumes through the real restart owner

production:
  selected target size
  -> materialize + production preflight
  -> public train
  -> real shared scheduler
  -> production run namespace
  -> interruption persists authentic resumable execution/checkpoint state
  -> close/reopen
  -> next public operation remains train
  -> rerun train automatically resumes through the real restart owner
```

Cross-role authority must remain fail-closed:

```text
screen checkpoint     -> production restart   REJECT
production checkpoint -> screen restart       REJECT
```

No manual public restart flag is introduced. Internal MACE `--restart_latest` may remain an implementation detail of the wrapper/restart owner but must not be exposed as the public recovery contract.

Full GPU and long production qualification remain deferred to the established final-release qualification workflow.

## Product design

No product redesign is authorized.

Use the already-added private external-child seam as the bounded test seam. The fake executable must run under the unchanged production scheduler and consume the already-authorized runtime inputs. The real product remains responsible for:

- public command ownership;
- config/TOML loading;
- `CampaignStore` persistence;
- target-size study authority;
- DATA8/preflight authorization;
- campaign construction and run filtering;
- shared scheduler/concurrency control;
- interruption/cancellation/finalization;
- run-root and namespace selection;
- checkpoint discovery/catalog construction;
- execution-record persistence;
- close/reopen state restoration;
- lifecycle/status/next-operation routing;
- restart/continuation checkpoint validation;
- cross-role rejection.

The fake child may only emulate external numerical MACE execution by creating the minimal authentic filesystem artifacts expected by those owners and by synchronizing deterministically with the test.

## Implementation obligations

### 1. Build one real assembled screen interruption/reopen/resume test

Invoke public `command_select_target_size` against a bounded real-owner fixture using the existing private external-child seam.

The fixture must execute the real scheduler and scheduler interruption path. The fake child must:

- start from a real authorized screen run;
- observe a `target-size-screen-*` run root/identity;
- receive a screen runtime plan with planned horizon `n3` and current boundary execution limit;
- write a minimally valid durable checkpoint in the real run directory;
- signal deterministic readiness to the test;
- remain alive until the real scheduler interruption/cancellation path terminates it.

Required observable result after interruption:

- public `command_select_target_size` returns the established interruption result (`130` unless current product semantics already define an equivalent value);
- the scheduler's normal finalization path persists an `INTERRUPTED` execution record;
- the persisted record contains the authentic checkpoint catalog discovered by the real checkpoint owner;
- no test code directly inserts or edits that execution record/catalog;
- target-size study state is not spuriously advanced by the interruption;
- recovery output names target-size screening / `select-target-size`, not public `train` or `evaluate`, and does not advertise a public `--restart_latest` flag.

Then close the store/process context and reopen normally. Prove:

- `_next_public_operation` resolves to `select-target-size`;
- public status projects the same semantic owner;
- `advance` routes to the same operation through its production routing path.

Rerun public `command_select_target_size` with no manual restart option. The fake child may record what the real restart owner supplies, but must not choose it. Prove:

- the same interrupted screen run identity/root is reused;
- the restart owner authenticates and selects the persisted checkpoint;
- the child receives continuation/restart state rather than epoch-zero execution;
- screen schedule/policy identity and boundary remain correct;
- no production run is authorized by this screen continuation.

It is sufficient to complete one bounded screen continuation boundary. Full `1 -> 3 -> 10` pruning is not a final-closure requirement unless needed to expose or repair the scheduler bug.

### 2. Prove public production commands fail closed against that exact interrupted screen

Using the state persisted by obligation 1, invoke public `train` and public `evaluate` before resuming the screen.

Required result:

- both reject before production work is scheduled;
- operator guidance points back to `select-target-size`;
- interrupted screen execution/checkpoint authority remains unchanged;
- no production run directory or execution attempt is created.

This is part of the same assembled lifecycle test, not a separate broad ownership requalification.

### 3. Build one real assembled production interruption/reopen/resume test

Use a selected target-size fixture through the real selected-size production lifecycle far enough to establish production training authorization. Reuse existing validated helpers/fixtures where they do not replace the owners under acceptance.

Invoke public `command_train` using the same external-child seam. Prove before interruption:

- run namespace/root is `production-*`;
- only the frozen selected target size is authorized;
- planned horizon is production `n`, not screen `n3`;
- no screen checkpoint is accepted as production ancestry.

Interrupt after the fake child writes a real durable production checkpoint. Required result:

- the real scheduler/finalizer persists the interrupted production execution record/catalog;
- recovery output directs the operator to public `train`, not `select-target-size`;
- no public/private restart flag is advertised.

After normal close/reopen:

- next public operation is `train`;
- rerunning public `train` automatically continues from the real authenticated production checkpoint through the real restart owner.

### 4. Prove cross-role restart rejection through the real restart consumer

Within the assembled screen and production fixtures, attempt the two material invalid crossings:

```text
screen checkpoint     -> production restart
production checkpoint -> screen restart
```

The rejection must arise from the production restart/companion/lineage validator or another genuine owning consumer, not a test-side pre-filter.

No broader restart-combination matrix is required.

### 5. Repair only concrete defects exposed by obligations 1-4

If the assembled tests fail because of a genuine product bug, make the smallest correction that preserves the frozen architecture.

Examples of locally authorized correction include:

- scheduler persistence failing to retain the interrupted checkpoint catalog;
- reopen failing to load the real interrupted execution record;
- scheduler restart failing to pass the authenticated checkpoint to the existing executor;
- lifecycle routing returning the wrong semantic command after interruption;
- role identity being lost before restart validation;
- screen/production restart ancestry not failing closed.

Do not preemptively redesign stage persistence, campaign schemas, namespaces, DATA8 materialization, or target-size reducers.

## Acceptance boundary

### Required real path

The final gate must execute, as applicable:

```text
public command
-> current config/store/authority loading
-> TRAIN2 preflight/runtime authorization
-> _build_campaign / current run filtering
-> shared scheduler
-> real scheduler interruption/cancellation/finalization
-> real execute_training_run boundary
-> real checkpoint discovery/catalog
-> real execution-record persistence
-> close/reopen CampaignStore
-> real lifecycle/next-operation routing
-> real restart/continuation validation
-> resumed scheduler execution
```

### Allowed doubles

Only:

- the external numerical `mdstats-mace-train` child beneath the existing private seam;
- minimal numerical/evaluation payload production if strictly necessary to move a bounded fixture into selected production state, provided no owner under the recovery claim is replaced.

### Forbidden substitutions

The gate-closing test must not monkeypatch, bypass, or directly manufacture the behavior of:

- `command_select_target_size` or `command_train`;
- `_execute_train_current_authority`;
- the shared scheduler/interruption/finalization path;
- `CampaignStore`;
- scheduler execution-record persistence;
- checkpoint discovery/catalog construction;
- restart checkpoint selection/validation;
- `_next_public_operation`, public status, or `advance` when their routing result is asserted;
- public `train`/`evaluate` fail-closed guards when tested against the interrupted screen.

It may observe these owners, but not replace the decision/result they are supposed to produce.

## Implementation authority

### Frozen

- Current accepted decoupling architecture.
- One shared scheduler.
- Screening owned by `select-target-size`; selected production owned by `train`.
- Screen horizon = `n3`; production horizon = independent `n`.
- Screen and production run/checkpoint namespaces remain distinct.
- Screen continuation resumes screen state; production begins fresh from screen state and only resumes production checkpoints after a production interruption.
- Private external-child seam remains test-only and non-public.
- No new public restart flag.
- Existing valid source/helper/unit evidence remains valid unless a final code change can plausibly affect its claim.

### Delegated

- Deterministic synchronization mechanism used by the fake child/test.
- Exact minimal fake checkpoint/log artifact contents, provided unchanged real consumers accept them.
- Test module organization and fixture factoring.
- Whether screen and production flows share one fixture implementation or two closely related fixtures.

### Reopen only on evidence

Reopen design only if the assembled test proves one of these:

- the current external-child seam cannot exercise the real scheduler/restart owner without moving semantic ownership into the test adapter;
- the shared scheduler cannot preserve distinct screen and production recovery authority;
- existing persistent stage-marker reuse causes an actual false public lifecycle transition after interruption/reopen;
- screen and production checkpoint namespaces/lineage cannot be separated by the current restart consumer;
- correct automatic continuation fundamentally requires a new public operator contract.

Absent such evidence, all failures route as bounded implementation repair under this plan.

## Initially expected affected behavioral surface

Primary expected changes are tests/fixtures only.

Product code should change only if the assembled test exposes a real defect, and then only at the narrowest implicated surface among:

- `_campaign_cli_core.py` scheduler orchestration/recovery persistence/lifecycle routing;
- `campaign_execution.py` interrupted execution/restart persistence semantics;
- restart/companion validation directly consumed by those paths.

Do not touch scientific selection, DATA7/DATA8 corpus generation, target-size ranking, optimizer algorithms, or unrelated performance machinery without direct failure evidence.

## Task-specific acceptance

Final closure requires all of the following after the last material executable change:

1. assembled public screen interruption -> persisted scheduler state -> close/reopen -> automatic screen continuation;
2. public `train` and `evaluate` rejection against that exact interrupted screen;
3. assembled public production interruption -> persisted scheduler state -> close/reopen -> automatic production continuation;
4. real-consumer rejection of screen->production and production->screen checkpoint ancestry;
5. focused tests for any code actually changed while fixing failures;
6. affected TRAIN2 scheduler/checkpoint/restart/lifecycle regression sufficient for the final changed surface;
7. final assembled integration rerun after the last material executable edit.

No requirement remains to rerun every historical Repair-1/Review-1/Review-2 test category merely because it appeared in an older plan. Run an older category only when the final affected-surface analysis shows it can plausibly regress.

Production qualification: **deferred**. No GPU, long MACE, long real-data, performance, RAM/VRAM, or production-scale qualification is required for this closure.

## Implementation sequence

### Final Gate A — Build the real-owner screen recovery test

Implement the deterministic fake child orchestration and execute the assembled screen interruption/reopen/resume path. If it passes without product changes, preserve that evidence and proceed. If it exposes a product defect, repair locally and rerun focused + affected regression before proceeding.

### Final Gate B — Add production and cross-role closure using the same seam

Execute production interruption/reopen/resume and the two invalid cross-role restart cases. Reuse the same test infrastructure; do not create a second scheduler/test orchestration model.

### Final Gate C — Final affected regression and closeout

Re-derive the final affected surface from the actual diff. Run only the complete affected regression plus the assembled final integration after the last executable change.

If A-C pass and no redesign trigger fires, archive this final workplan together with the superseded Repair-1 review chain and close target-size screen/production decoupling implementation work. Do not create another amendment for equivalent-preference findings or already-retired obligations.

## Deferred qualification record (2026-08-25)

The stakeholder directed implementation to finish the executable gates available
from this checkout and defer unavailable qualification.  This is not a PASS or
an archive authorization for Final Gates A-C.

The available persisted LTA campaign has authentic candidate DATA8 authority,
but no selected target-size/selected-production DATA8 fixture.  Its immutable
externalized record tree is approximately 103 GiB and cannot be safely cloned
into the test workspace: a copy exceeds the available temporary storage and
the source and test workspaces do not support hard links across their storage
boundary.  Running the public commands in place would mutate an external,
read-only campaign and is therefore out of scope.  Test-side manufacture of
selected state, production materialization, execution records, checkpoint
catalogs, or cross-role ancestry remains forbidden.

Accordingly, the following evidence remains deferred pending an authorized,
bounded, isolated fixture with authentic selected-production authority:

- assembled public screen interruption/reopen/automatic continuation (Gate A);
- public production interruption/reopen/automatic continuation and both real
  restart-consumer cross-role rejections (Gate B);
- final assembled integration and workplan archival (Gate C).

Existing owner-level scheduler/checkpoint/restart and public-command guard
regressions may be executed and reported as limited evidence only.  They do
not replace the deferred assembled public-owner proof.

## Design handoff closure

The final implementation contract preserves every still-material unresolved concern from the latest independent review:

```text
remaining blocker
= real public-command/shared-scheduler interruption + persistence + reopen + authentic continuation
+ correct semantic owner after reopen
+ fail-closed cross-role restart
```

All other previously reviewed target-size repair obligations are intentionally retired from active gating unless this final assembled path produces concrete evidence that one of them is actually broken.

No implementation actor should reconstruct or reopen the earlier broad Repair-1 acceptance matrix.

## Risks / redesign triggers

The only material remaining risk is that the real scheduler/reopen path behaves differently from the already-correct lower-level executor behavior. The final assembled tests directly target that risk.

If those tests pass, there is no remaining evidence-backed reason to continue this repair chain.
