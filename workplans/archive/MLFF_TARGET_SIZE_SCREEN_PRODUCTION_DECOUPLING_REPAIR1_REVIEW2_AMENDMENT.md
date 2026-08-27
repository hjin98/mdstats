---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-SCREEN-PRODUCTION-DECOUPLING-REPAIR1-REVIEW2
protocol_version: 5.7.0
status: active
created_date: 2026-08-25
reviewed_head: 38ac522c85f65ddbfe04ca0f4b21b3ec1324d01b
parent_workplan: MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_WORKPLAN.md
parent_amendment: MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_REPAIR1_REVIEW1_AMENDMENT.md
routing: implementation-nonconformance-and-acceptance-closure-only
---

# Repair-1 Review-2 Amendment — Real Scheduler / Checkpoint / Restart Closure

## Objective

Close the remaining **real-owner functional acceptance gap** after Review-1 implementation at `38ac522c85f65ddbfe04ca0f4b21b3ec1324d01b`.

Review-1 repaired the source-level lifecycle leak correctly: the shared TRAIN2 scheduler now derives a semantic execution context, target-size screening reports itself as target-size screening, screen recovery points to `select-target-size`, production recovery points to `train`, and the obsolete operator instruction `--restart_latest` is no longer exposed.

The remaining blocker is not another architecture defect. The implementation has not yet exercised the exact production boundary that originally failed:

```text
public semantic owner
  -> real shared TRAIN2 scheduler/runtime authorization
  -> real external-child launch/control seam
  -> durable checkpoint
  -> real scheduler interruption/cancellation
  -> real execution-record/checkpoint-catalog commit
  -> store/process reopen
  -> real restart/companion authorization
  -> continuation from the durable checkpoint
```

The existing `tests/test_mlff_target_size_repair1_real_owner.py` is useful but explicitly stops below DATA8/runtime/scheduler acceptance. Review-2 requires extending that bounded real-owner harness through the scheduler/checkpoint/restart boundary and closing the still-open parent Repair-1 claims with the same acceptance discipline.

This amendment is **acceptance closure plus any local defect exposed by that acceptance**. It does not reopen the accepted target-size scientific architecture.

## Frozen product design — do not redesign unless a stated trigger fires

The implementer must preserve all of the following:

1. One shared TRAIN2 training scheduler/runtime implementation is reused by screening and production.
2. `_TrainingExecutionContext` or an equivalent single semantic-role projection remains the user-facing lifecycle authority for that shared engine.
3. Public target-size screening is owned exclusively by `select-target-size` until `N*` is frozen.
4. Public TRAIN2 `train` and `evaluate` remain production-only before/after the selected production matrix and its preflight are current.
5. Screen and production run/filesystem/restart namespaces remain distinct: `target-size-screen-*` versus `production-*`.
6. Screen budget/scheduler/LR horizon is `n3`; production horizon is independently configured `n`.
7. A surviving screen `(size, seed)` continues one exact checkpoint/optimizer/RNG/scheduler trajectory across `n1 -> n2 -> n3`.
8. Production starts fresh at epoch zero and must not continue a screen model/checkpoint/optimizer/scheduler/RNG state.
9. In-memory queued scheduler tasks are not durable authorization. Every resumed public invocation re-derives admissible work from current verified campaign authority.
10. Existing internal persistent `train`/`evaluate` stage-marker reuse may remain if real assembled tests prove it is safely contained. Do not introduce a new persistent role-scoped stage schema merely to improve naming.
11. No public manual restart flag is added merely to make testing easier. Automatic campaign restart remains the intended operator behavior.
12. Full long-running MACE/GPU production qualification remains deferred. These gates are bounded functional acceptance and must not require production-scale compute.

## The required test seam — this is the critical implementation instruction

### Real owners that must execute unchanged for gate-closing evidence

The gate-closing integration harness must execute the actual repository owners for every claim it asserts, including as applicable:

- public `command_select_target_size`;
- public `command_train`;
- `_execute_train_current_authority` or its current production successor;
- the real shared scheduler loop / task selection / worker coordination;
- real `_require_train2_preflight_authorization`;
- real `_validate_train2_data8_matrix` and schedule compatibility;
- real `_build_campaign` and run namespace construction;
- real TRAIN2 budget, optimizer, LR/schedule, runtime-plan, execution-limit construction;
- real run-root selection and training execution-record serialization;
- real checkpoint discovery/catalog construction and authentication;
- real continuation/restart companion construction and validation;
- real current-attempt/previous-attempt persistence semantics;
- real target-size endpoint authorization and reducer/state transition;
- real `CampaignStore` close/reopen behavior;
- real `_next_public_operation`, lifecycle/status projection, and `advance` routing when those are under acceptance;
- real selected-size `materialize` and production-preflight lifecycle owners for the role-boundary test;
- real normal config-change reconciliation for parent Repair-1 frontier claims.

### The only permitted training fake

The bounded fake must sit **below the real scheduler and real runtime/restart authorization** at the external numerical MACE child boundary.

The fake child/launcher must consume the already-authorized real inputs. At minimum it must observe/use the real:

- run ID and run directory;
- run role/namespace;
- job/protocol identity;
- planned scheduler/training horizon;
- current execution-limit boundary;
- attempt index;
- restart/continuation checkpoint supplied by the production restart owner, if any.

It must emit the minimum authentic filesystem/runtime artifacts expected by the unchanged parent consumers, including a restart-capable durable checkpoint and whatever log/runtime evidence the real checkpoint-catalog/execution-record owners require.

The fake must **not**:

- return a fabricated `TrainingRunExecutionRecord` directly to bypass normal child execution/finalization;
- directly insert an `INTERRUPTED` record into `CampaignStore`;
- directly construct a post-interruption checkpoint catalog instead of letting the real owner discover/serialize it;
- directly mutate `TargetSizeStudyPlan` or manufacture endpoint evidence after a reduction;
- decide which candidates survive or which jobs are admissible;
- choose or validate the restart checkpoint on behalf of the production restart owner;
- bypass scheduler cancellation/cleanup/finalization code.

If the current subprocess abstraction makes this seam awkward, introduce the **smallest private injectable external-child launcher/process adapter** needed to fake only process execution. The adapter must be below run/runtime-plan/restart authorization and above OS process mechanics. Do not move scheduling, checkpoint selection, restart validation, or execution-record construction into the adapter.

## Deterministic interruption design

Do not make the acceptance test depend on arbitrary sleeps or timing races.

Use a deterministic synchronization point at the permitted external-child seam:

1. the real scheduler selects and authorizes a real run;
2. the fake child starts under the real scheduler;
3. it writes a minimally valid durable checkpoint to the real run directory;
4. it signals a test `Event`/barrier that the checkpoint is durable;
5. the test triggers the **same scheduler interruption/cancellation path used by normal Ctrl-C/SIGTERM handling**;
6. the real scheduler stops/cancels the active child through its normal control path;
7. the real parent discovers the checkpoint, builds/commits the interrupted execution record/catalog, marks resumable lifecycle state, and returns its normal interruption code.

A test-only helper may trigger the already-existing interruption callback or deliver a real process signal to the invoking campaign process, whichever is safer and less racy. It may not replace the interruption handler or construct the result that handler is supposed to produce.

The gate is about the scheduler/checkpoint/restart product boundary, not OS signal mechanics. Therefore a deterministic callback trigger is acceptable **only if the production interruption handler, cancellation, child stop, artifact discovery, execution-record commit, and return path all execute unchanged**.

## Completion gates

### R2-G1 — Real screen interruption at the first boundary

Build a current default `1/3/10` screen with production `n=30` using real config, store, DATA8 compatibility/preflight, campaign construction, and runtime authorization.

Invoke public `command_select_target_size`; do not call `_execute_train_current_authority` directly as a substitute for public ownership.

Before interruption, establish from real runtime/run state:

- run namespace/root begins with `target-size-screen-`;
- screen `planned_epochs == 10`;
- optimizer/LR schedule horizon is 10;
- active execution limit is exactly coarse boundary 1;
- selected/queued population is the real qualified-size × screening-seed population allowed by the study;
- no production/CV run is authorized.

Interrupt after at least one active screen child has produced a durable checkpoint.

Required result:

- `command_select_target_size` returns the established interrupted status (`130` unless product semantics legitimately change);
- real persisted execution state is `INTERRUPTED`/resumable through the normal record owner;
- checkpoint catalog contains an authenticated restart-capable checkpoint produced in the real `target-size-screen-*` run root;
- operator output identifies target-size screening and directs recovery to `select-target-size`;
- output does not instruct public `train` or `evaluate` for screen recovery and does not expose `--restart_latest`;
- current target-size study is not corrupted or advanced by the interruption alone;
- after store close/reopen, `_next_public_operation` and `status` resolve to `select-target-size`;
- `advance` resolves/dispatches the same semantic operation through its real routing path.

### R2-G2 — Public production commands fail closed against that exact interrupted screen

Use the persisted state produced by R2-G1; do not create a fresh awaiting-screen study.

Snapshot before each command:

- target-size study digest/payload;
- interrupted training execution-record digest/payload;
- restart checkpoint path and SHA/hash/catalog identity;
- relevant stage/lifecycle state;
- DATA8 scientific payload hashes/identities;
- current run namespace/attempt metadata.

Invoke public `train`, then public `evaluate`.

Required result:

- both reject before scheduling/evaluation work;
- errors direct the operator to `select-target-size`;
- all snapshots remain unchanged except explicitly non-authoritative diagnostic/event-log additions;
- no production run directory or execution attempt is created.

### R2-G3 — Real automatic screen resume from the durable checkpoint

Rerun public `select-target-size` on the R2-G1 store with **no manual restart flag**.

Instrument only the permitted external-child seam to record what the real restart owner passes into the child.

Required result:

- same screen run identity/root is reused for the surviving interrupted run;
- real restart/companion validation selects the exact authenticated checkpoint from R2-G1;
- checkpoint path/hash supplied to the child matches the persisted real catalog;
- continuation retains the same screen training-policy/schedule identity;
- planned horizon remains 10 and execution limit remains the active semantic boundary;
- optimizer/RNG continuation authority is accepted through the real companion/restart validator;
- the run does not restart from epoch zero and does not duplicate the already durable prefix of work;
- real endpoint evaluation/reduction owner advances the study after the boundary; only expensive numerical predictions may be faked below its authorization boundary.

Then continue a bounded real-owner funnel far enough to prove pruning:

- after coarse reduction, the newly constructed authorized run IDs equal `study.next_training_sizes × screening_optimizer_seeds × final-development-screen role`;
- eliminated coarse candidates have no new attempt, queue entry, or execution authorization at `n2`;
- after short reduction, non-finalists likewise receive no `n3` work;
- preferably complete the bounded `1 -> 3 -> 10` funnel and freeze `N*` through the real reducer.

### R2-G4 — Real production interruption/restart and cross-role isolation

Using the selected target size from R2-G3 when practical:

1. invoke real selected-size `materialize`;
2. establish real production preflight authority;
3. invoke public `train` using the same bounded external-child seam;
4. interrupt after a durable production checkpoint exists.

Required pre-interruption invariants:

- run namespace/root is `production-*`;
- only frozen selected target size is authorized;
- planned horizon is production `n` (30 in the default case), not screen `n3`;
- production begins fresh at epoch zero;
- no screen checkpoint/optimizer/RNG state is presented as production restart ancestry.

Required interruption/reopen behavior:

- real production execution record/catalog is committed as resumable;
- recovery message directs to public `train`, never `select-target-size`;
- no private/nonexistent restart flag is advertised;
- after close/reopen, public lifecycle recommends `train`;
- rerunning public `train` automatically supplies the authentic production checkpoint to the child.

Explicitly prove through the real restart/companion validator:

```text
screen n1 checkpoint -> screen n2 continuation    ACCEPT
screen n2 checkpoint -> screen n3 continuation    ACCEPT
screen checkpoint     -> production restart       REJECT
production checkpoint -> screen restart           REJECT
```

Rejection must come from the production validation owner, not test-side pre-filtering.

### R2-G5 — Internal stage-marker containment across the role boundary

Use one assembled campaign and record both internal stage markers and projected public lifecycle at each boundary.

Required sequence:

```text
screen interrupted      -> public next = select-target-size
screen resumed/selected -> public next = materialize
materialized            -> public next = production preflight
production preflight    -> public next = train
production interrupted  -> public next = train
production complete     -> public next = evaluate
```

Required invariants:

- completion of internal screen `train`/`evaluate` work does not make production `train` or `evaluate` appear complete;
- selected-size materialization/preflight establishes fresh production lifecycle state;
- `status`, `_next_public_operation`, and `advance` agree on the semantic owner at each checked boundary;
- screen execution records/checkpoints cannot authorize production and production records cannot authorize screening.

Only if this real assembled test fails because internal stage keys are genuinely ambiguous may the implementer minimally role-scope persistent stage authority. Such a change is a local evidence-backed repair, not permission for a broad lifecycle rewrite.

### R2-G6 — Close parent O-R2 with the same real scheduler harness

The same harness must establish the still-open fresh-screen claims for both:

```text
default:    n1/n2/n3/n = 1/3/10/30
nondefault: n1/n2/n3/n = 2/5/12/40
```

For each case prove through real campaign/runtime owners:

- every screen job's planned training/scheduler horizon is `n3`, never production `n`;
- optimizer maximum epoch/update budget and LR horizon are bound to `n3`;
- active execution limit is exactly the current boundary;
- initial population covers every qualified size × screen seed;
- coarse pruning reduces to `min(q,4)` and short pruning to 2 finalists;
- eliminated candidates receive no later work;
- survivors continue same screen run/checkpoint/optimizer/RNG ancestry;
- no screen authorization exceeds `n3`;
- `select-target-size` freezes `N*` and returns before any production training.

For a representative `q=5`, two-seed default case, observed authorized successful work must be consistent with the 54 candidate-epoch maximum geometry without physically requiring 54 expensive MACE epochs.

### R2-G7 — Close parent O-R3/O-R4 through normal close/reopen reconciliation, not target-study reconstruction alone

#### Production `n` change during a partial screen

Persist a real partial screen with a valid durable checkpoint after `n1`, close the store/process, edit TOML `30 -> 40`, and reopen through normal campaign status/advance/reconciliation.

Prove:

- screen target-size authority remains current;
- screen horizon remains 10;
- same surviving screen run/checkpoint resumes toward `n2`, not epoch zero;
- scientific DATA7/DATA8 payload hashes remain unchanged;
- eventual selected production runtime is built with horizon 40.

#### Production `n` change after selection/production work exists

Persist selected target size and at least one production-dependent receipt/attempt under `n=30`, close, edit to `n=40`, reopen through normal reconciliation.

Prove:

- screen evidence and frozen target size remain current;
- scientifically unchanged DATA7/DATA8 payloads remain preserved;
- obsolete production budget/schedule/run/checkpoint/evaluation-dependent state is invalidated by its normal caller;
- fresh production authorization is selected-size-only with horizon 40 and no screen ancestry.

#### Screen-boundary changes

Independently exercise edits to `n1`, `n2`, and `n3` with real persisted screen state.

Prove:

- REPAIR2/MVQUAL and scientifically unchanged DATA7/DATA8 corpus payload bytes/hashes are preserved;
- old screen evidence/selection is invalidated;
- schedule-bearing realization is regenerated as required;
- current screen restarts from the new `n1`;
- old checkpoints are rejected under changed schedule identity;
- especially, an `n3` change invalidates earlier `n1/n2` evidence because LR/scheduler trajectory changed.

Calling `_ensure_target_size_study` alone is insufficient for this gate; the normal close/reopen reconciliation/next-operation caller must execute.

### R2-G8 — Close parent O-R5 historical/pre-decoupling migration with authentic persisted generations

Exercise two persisted historical populations through the real current compatibility/reconciliation path:

1. authenticated fixed predecessor with historical `(3,10,30)/30` semantics;
2. pre-decoupling flexible `1/3/10` screen execution/evidence whose trainer/scheduler horizon was 30.

Use authentic historical serialized payloads/digests produced by the historical serializer or frozen golden fixtures captured from the relevant historical revision. Do not hand-reimplement the historical digest algorithm in the acceptance test.

Required real owners include `CampaignStore`, historical authentication, candidate/data discovery, DATA8/scientific compatibility, schedule compatibility, target-size reconstruction/reconciliation, and next-operation routing.

Prove:

- historical generation is authenticated or fails closed if genuinely unsupported/ambiguous;
- historical screen checkpoints/evaluations/rankings/selections are not relabeled current;
- unchanged scientific REPAIR2/MVQUAL/DATA7/DATA8 corpus payloads are reused byte-for-byte where the frozen preservation boundary says they should survive;
- cheap schedule/job realization may be regenerated to the current screen horizon 10;
- no horizon-30 screen execution protocol becomes current horizon-10 authority;
- fresh current screening begins at current `n1`;
- no expensive scientifically unchanged candidate corpus is recomputed merely because schedule realization changed.

If the real path unnecessarily rebuilds scientific payloads, repair the local scientific-payload versus schedule-realization ownership boundary. Do not weaken compatibility validation.

### R2-G9 — Anti-bypass guard must cover the actual gate-closing modules

Extend the targeted structural guard so the module(s) that claim R2-G1 through R2-G8 cannot replace the owners they are proving.

When those owners are under acceptance, forbid monkeypatching/replacing/bypassing at least:

- `command_select_target_size` / `command_train`;
- `_execute_train_current_authority`;
- scheduler interruption/cancellation/finalization handler;
- `CampaignStore`;
- `_require_train2_preflight_authorization`;
- `_current_data8_entries`, `_validate_train2_data8_matrix`, schedule compatibility;
- `_build_campaign`;
- `_train2_policy_set`, `_optimizer_policy`, runtime-plan/execution-limit owner;
- checkpoint discovery/catalog/serialization;
- restart/continuation companion construction/validation;
- target-size reducers/state-transition owner;
- normal config reconciliation/invalidation caller;
- `_next_public_operation`, status, or `advance` when routing is the claim;
- selected-size materialize/preflight owner when lifecycle containment is the claim.

The guard must explicitly permit the identified external numerical-child seam and, where required, numerical target-evaluation calculation below the real evaluation authorization/checkpoint consumer.

Do not create a repository-wide mock ban.

### R2-G10 — Required execution evidence and regression closure

Source inspection alone cannot close Review-2.

After the last executable change that can affect this surface, execute and record:

1. focused real scheduler/checkpoint/restart acceptance tests R2-G1 through R2-G5;
2. parent real-owner closure R2-G6 through R2-G8;
3. existing target-size/flexible-fidelity/CLI semantic orchestration tests;
4. affected TRAIN2 runtime/checkpoint/restart/companion tests;
5. affected DATA7/DATA8 materialization/schedule compatibility tests;
6. affected persistence/config-reconciliation/migration tests;
7. final assembled integration through public `select-target-size` and public production `train` using the bounded external-child seam;
8. broader repository regression only if final impact analysis cannot confidently bound the affected surface.

Stage-local rule: if implementing the injectable child seam or changing restart semantics materially alters executable behavior, run focused + affected regression for that stage before proceeding to dependent lifecycle/migration changes.

A required test that is skipped, xfailed, replaced with a proxy, or never executed is not a pass. Existing unrelated pre-existing failures may be attributed only with concrete evidence.

No GitHub CI is required if equivalent local executed command output is available and credible. No long GPU/full-production qualification is required.

## Completion / closeout rule

Review-2 and parent Repair-1 may be marked complete only when **all** of the following are true:

- Review-1 T1-T6 claims are established through the real owners specified here;
- parent Repair-1 O-R1 through O-R7 material claims are established or legitimately reconciled with equal/stronger evidence;
- the exact screen interruption -> reopen -> automatic screen continuation path passes;
- the exact production interruption -> reopen -> automatic production continuation path passes;
- cross-role restart isolation passes through the real restart validator;
- default/nondefault screen budget and pruning behavior passes through real scheduler authorization;
- config-change and historical migration preservation/invalidation boundaries pass through normal persisted reconciliation;
- final affected regression and assembled integration have actually executed after the last material executable edit;
- any local defect exposed by those tests has been repaired and the invalidated evidence rerun.

Do **not** mark this amendment complete merely because `_TrainingExecutionContext` source code is correct, recovery strings look correct, unit tests pass, or helper-level persistence tests pass.

If the implementer cannot create a safe bounded fake below the real scheduler/restart owner without replacing those owners, stop and report that concrete seam limitation as an evidence-backed design-reopen trigger. Do not silently downgrade the gate to proxy acceptance.

## Genuine redesign triggers

Reopen design only if real acceptance proves one of these material facts:

- current process-launch architecture cannot expose a bounded external numerical-child seam without moving scheduler/restart ownership into a test adapter;
- the shared scheduler cannot preserve correct screen versus production restart authority even with semantic execution context;
- internal `train`/`evaluate` stage-marker reuse causes real cross-role false completion/authorization that cannot be locally contained;
- screen/production checkpoint namespaces collide in an actual restart consumer;
- automatic restart semantics cannot recover a valid interrupted screen/production attempt without a new public operator contract.

Absent one of those findings, implementation must remain a bounded repair of the current accepted architecture.
