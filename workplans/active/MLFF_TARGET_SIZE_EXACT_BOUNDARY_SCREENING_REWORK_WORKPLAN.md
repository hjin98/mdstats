---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-EXACT-BOUNDARY-SCREENING-REWORK-V1
protocol_version: 5.7.0
status: active
created_date: 2026-08-26
reviewed_head: 215b5643072455da866191a6ae4b629f36d9cdc0
supersedes_conflicting_target_size_design: true
---

# MLFF Target-Size Exact-Boundary Screening Rework Workplan

## Objective

Correct TARGET-SIZE-V5 so configurable `n1/n2/n3` target-size screening is modeled and executed purely as exact successive-halving boundaries, with no target-size-screening "horizon" concept. The only epoch horizon remains the independent post-selection production-training maximum `n`, where trajectory-wide checkpoint selection may choose an epoch earlier than the maximum.

Default behavior remains:

```text
screening boundaries: 1 -> 3 -> 10
production maximum:    30
```

The screen compares candidate target sizes only at exact configured boundaries. At each rung, the boundary checkpoint is the required checkpoint; there is no epoch search or chosen epoch distinct from the boundary.

This rework also closes the confirmed production bug in `_campaign_training_policy_family()` that currently misclassifies TRAIN2 target-size campaigns as historical because it reads a nonexistent `TrainingCampaignRunPlan.protocol` field instead of resolving the authoritative `MaceJobArtifact.protocol`. That defect bypasses boundary control and permits a coarse `n1=1` screen to continue into epoch 2.

## Authority and precedence

This workplan supersedes every current target-size statement that treats `n3` as a screen horizon, including conflicting statements in:

- `workplans/archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md`;
- `workplans/archive/MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_FINAL_CLOSURE_WORKPLAN.md`;
- `workplans/active/README.md`;
- current target-size runtime/reporting/specification/tests that encode `screen horizon = n3`, `planned_epochs=n3`, `normalized_progress=boundary/n3`, or dual `screen boundary + schedule horizon` semantics.

Still-valid nonconflicting decisions remain preserved: screening and production are distinct roles; screening continues one exact `(size,seed)` trajectory across surviving boundaries; eliminated candidates receive no later work; production starts fresh after selection; screen and production checkpoint/run namespaces remain isolated; DATA7/DATA8 scientific candidate-prefix authority remains reusable when scientifically unchanged; full GPU/long production qualification remains deferred.

## Final review diagnosis

### 1. Conceptual defect: screening horizon is not a meaningful product concept

`n1/n2/n3` are exact semantic evaluation boundaries for a successive-halving filter. They are not a trajectory from which an epoch is selected. Therefore `n3` is merely the terminal screening boundary, not an epoch-selection horizon.

The current implementation nevertheless exposes `screening_horizon_epochs`, keeps a compatibility `training_horizon_epochs`, persists `planned_epochs`, computes `normalized_schedule_progress`, renders both `screen_boundary_epochs` and `schedule_horizon_epochs`, and validates endpoint/horizon geometry. These are artifacts of the superseded model and create unnecessary authority and reporting complexity.

### 2. Confirmed execution defect: TRAIN2 campaign misclassification

`TrainingCampaignRunPlan` has no `protocol` field. `_campaign_training_policy_family()` currently evaluates TRAIN2/adaptive authority using `getattr(run, "protocol", None)`, which is therefore always `None` for campaign run plans. Real target-size TRAIN2 campaigns are consequently classified as historical.

Observed runtime evidence is consistent with this exact failure: the target-size command entered `Historical training`, budgeted a full 10-epoch run, and advanced to `phase=epoch 2/10` despite active coarse boundary `n1=1`.

The authoritative protocol is the resolved `MaceJobArtifact.protocol`, referenced by each run's `mace_job_artifact_digest`/job identity.

### 3. LR/runtime consequence requiring explicit design

Removing the screening-horizon concept must not accidentally create discontinuous or independently restarted training at each boundary. A surviving `(size,seed)` remains one deterministic training trajectory:

```text
0 -> n1 -> n2 -> n3
```

The terminal boundary `n3` may still be used internally where a deterministic optimizer/LR function mathematically requires the total length of this one screening trajectory. That value is a derived property of the configured boundary sequence (`fidelity_epochs[-1]`), not a separately named/persisted screen horizon, checkpoint-selection horizon, or competing authority.

Implementation must not expose or persist a second screen-budget concept when the exact same value is already owned by the boundary tuple.

### 4. Configuration geometry correction

The previous strict rule `n3 < n` was justified by the old screen-horizon/production-horizon model, not by target-size screening itself. Once screening boundaries and production maximum are independent roles, no scientific invariant requires `n3 < n`.

Required current geometry becomes:

```text
0 < n1 < n2 < n3
n > 0
```

`n` remains independent production authority. Equal values such as `(1,3,10)` with production `n=10` are valid unless another independent production contract rejects them. A production-budget change must not invalidate otherwise valid screening state.

### 5. Overshot-state recovery must fail closed

Current or interrupted target-size state that has executed beyond its authorized active boundary cannot be silently accepted as valid boundary evidence or resumed as though no violation occurred. If an existing run has passed `n1` before coarse ranking, or passed another active boundary before its reducer, the affected current-generation screening execution/evidence must be invalidated/restarted from the narrowest safe screen owner while preserving scientifically unchanged DATA7/DATA8.

Historical forensic records may remain readable, but overshot checkpoints/evidence must not become current exact-boundary authority.

## Protected concerns

Implementation must preserve:

- fixed candidate-size universe and MVQUAL hard admission;
- `q -> min(q,4) -> 2 -> 1` promotion geometry;
- paired screening-seed target-only ranking and existing equivalence policy;
- exact boundary evidence: coarse only at `n1`, short only at `n2`, final only at `n3`;
- exact checkpoint/optimizer/RNG continuation for survivors between boundaries;
- no work after elimination/failure;
- candidate-specific numerical/scientific failures remain distinct from infrastructure/programming failures;
- target-size screening is owned by `select-target-size` and ends after selected size is frozen;
- post-selection production starts fresh and never continues screen model/optimizer/scheduler/RNG state;
- production checkpoint selection remains trajectory-wide up to maximum `n`, so selected epoch may be `< n`;
- screen and production run/checkpoint/output identities cannot collide;
- DATA7/DATA8 candidate materialization remains policy-independent where scientific inputs are unchanged;
- existing valid performance/resource machinery remains reused;
- routine regression/integration remains distinct from deferred target-hardware/full production qualification.

## Product design

### 1. Screening authority is the ordered boundary tuple

`TargetSizeStudyPolicy.fidelity_epochs == (n1,n2,n3)` is the sole target-size epoch authority.

For current stage `k`, the target-size owner derives:

```text
active_boundary = fidelity_epochs[k]
terminal_boundary = fidelity_epochs[-1]
```

`active_boundary` authorizes execution and exact evaluation for the current rung. `terminal_boundary` may be used only as a derived numerical parameter where the deterministic continuation schedule requires the full eventual screening trajectory length. It must not be exposed as a separate screen horizon or persisted as another target-size authority.

### 2. Exact successive-halving semantics

For every surviving `(size, seed)`:

```text
coarse:       train/continue exactly through n1 -> evaluate n1 -> reduce
short:        survivors continue exactly through n2 -> evaluate n2 -> reduce
final-screen: finalists continue exactly through n3 -> evaluate n3 -> select/freeze
```

No checkpoint at a nonboundary epoch may substitute for the configured rung checkpoint. No screen reducer searches across epochs. No screening artifact describes a "best epoch".

### 3. Screening evidence schema semantics

Current-generation target-size evidence should encode what is scientifically necessary:

- stage;
- exact completed boundary epoch;
- training/run/protocol/schedule identity sufficient to prove authentic deterministic continuation;
- optimizer update/structures counts as needed for authenticity/debugging;
- target metric and qualification evidence;
- checkpoint/optimizer/RNG ancestry.

Remove current-generation semantics whose only purpose is a screen horizon, including `planned_epochs=n3` and `normalized_schedule_progress=boundary/n3`, unless a field is retained solely as a generic lower-level TRAIN2 runtime detail outside target-size scientific authority. Current target-size validation must not require a screen-horizon equality.

Schema/version changes must prevent old horizon-based evidence from being silently interpreted as current exact-boundary evidence.

### 4. Runtime/schedule realization

Reuse the existing TRAIN2 runtime rather than creating a second trainer.

For screening, runtime assembly must derive its deterministic schedule extent from the target-size boundary tuple when required by the LR function. The active execution limit is always the current boundary. Expanding from `n1` to `n2` to `n3` must preserve all scientifically defining schedule/protocol identities and exact restart state.

Generic TRAIN2 internal names such as `planned_epochs` may remain where they are truly generic runtime-budget concepts, but target-size code must not promote them into a distinct screen-horizon authority. If generic runtime APIs make this impossible without persistent semantic leakage, refactor the generic interface minimally so role-specific target-size semantics remain clean.

### 5. Production horizon remains distinct

Post-selection production retains `TrainingBudgetPolicy.planned_epochs = n` as a true maximum training/evaluation horizon. EVAL2 may evaluate checkpoints across epochs `<= n`, and selected production checkpoint may be earlier than `n`.

Production `n` is not part of target-size study identity, target-size invalidation, target-size progress, or target-size boundary authorization.

### 6. TRAIN2 policy-family classification uses authoritative job protocols

Campaign classification must resolve each run to its authoritative `MaceJobArtifact` and inspect `job.protocol`, not `run.protocol`.

Required fail-closed behavior:

- unresolved run -> job reference is an error;
- run/job protocol digest mismatch is an error;
- mixed historical/TRAIN2 authority in one campaign is rejected unless an already-defined supported mixed mode exists;
- a run cannot simultaneously carry incompatible adaptive-stop and TRAIN2 authority;
- genuine historical campaigns remain historical.

Do not add a duplicate `protocol` object to `TrainingCampaignRunPlan` merely to repair classification.

### 7. Reporting

Target-size progress must report only screening semantics, for example:

```text
stage=coarse; phase=epoch 1/1
stage=short; phase=epoch 2/3
stage=final-screen; phase=epoch 7/10
```

At boundary completion, the command returns to ranking before any next epoch begins.

Do not render `screen horizon`, `schedule_horizon`, `screen epoch X/Y; schedule epoch X/Z`, or equivalent dual-denominator target-size language. Future production `n` may be printed separately as configuration information, but never as target-size progress authority.

Production training later reports its own independent maximum `n` normally.

### 8. Compatibility and invalidation

Recognize current exact-boundary generation separately from prior fixed/full-production-schedule and decoupled-screen-horizon generations.

Where scientifically valid:

- preserve/re-authenticate REPAIR2/MVQUAL and candidate DATA7/DATA8;
- do not relabel old screen checkpoint/evidence/ranking/selection state as current exact-boundary authority;
- production-only `n` changes preserve current valid target-size screen/selection state;
- any `n1/n2/n3` change invalidates current screen execution/evidence/selection from the beginning of screening unless stronger safe partial reuse is independently proven and explicitly designed;
- overshot current-generation screen execution fails closed and restarts the affected screen authority rather than selecting from unauthorized epochs.

## Implementation obligations

### Gate A - Correct policy-family ownership and reproduce the bug

Required implementation consequences:

- repair `_campaign_training_policy_family()` or its successor to classify from resolved `MaceJobArtifact.protocol`;
- validate run/job protocol identity fail-closed;
- keep real historical classification behavior intact;
- add a focused reproducer proving the previous slotted `TrainingCampaignRunPlan.protocol` lookup cannot classify TRAIN2 correctly.

Stage-local regression must include campaign construction/classification and affected historical/adaptive/TRAIN2 paths.

### Gate B - Remove target-size horizon semantics from authority, evidence, reporting, and configuration

Required implementation consequences:

- remove `screening_horizon_epochs` / compatibility `training_horizon_epochs` as current target-size semantic API;
- remove target-size evidence requirements based on `planned_epochs == n3` and normalized `boundary/n3` progress;
- remove `schedule_horizon_epochs` / `screen_boundary_epochs` dual target-size progress semantics and simplify reporter ownership to active boundary/stage;
- remove active documentation/spec/dependency/test language that defines `n3` as screen horizon;
- remove configuration validation whose only rationale is `n3 < n`; retain independent positivity/ordering rules `0<n1<n2<n3` and `n>0`;
- version current schemas/authority where necessary so old horizon-based evidence cannot masquerade as exact-boundary evidence.

Preserve generic production TRAIN2 horizon semantics.

### Gate C - Reconcile deterministic screening continuation without reintroducing hidden horizon authority

Required implementation consequences:

- derive any LR/schedule total-length parameter needed for one screening trajectory directly from `fidelity_epochs[-1]` at runtime assembly;
- active execution authorization is the exact current boundary;
- survivor continuation preserves exact checkpoint, optimizer, scheduler/LR state, and RNG ancestry;
- `n1 -> n2 -> n3` expansion does not create a new scientific run identity;
- no target-size persisted/runtime consumer exposes a second independently mutable screen budget;
- numerical-failure and restart-companion validation continue to authenticate the exact schedule/protocol required for continuation.

If the generic TRAIN2 budget object must still carry the terminal boundary internally, target-size code must treat it as a derived runtime realization, not a separate study/horizon authority.

### Gate D - Enforce exact-boundary orchestration and fail-closed overshoot recovery

Through the real `select-target-size` owner:

```text
all qualified candidates -> exactly n1
coarse survivors         -> exactly n2
short finalists          -> exactly n3
selection freezes; command returns
```

Required behavior:

- epoch `n1+1` cannot start before coarse reduction;
- eliminated candidates cannot receive later authorization;
- epoch `n2+1` cannot start before short reduction;
- no target-size screen can execute beyond `n3`;
- existing overshot execution/evidence is rejected/invalidation-routed rather than consumed as current boundary evidence;
- final selection never falls through into production training.

### Gate E - Preserve independent production semantics

Required behavior:

- production starts fresh for the frozen selected target size;
- production maximum `n` remains independent and may equal, exceed, or be less than `n3` unless another independent product contract forbids a case;
- production checkpoint selection continues to consider admissible trajectory checkpoints up to `n` and may select epoch `< n`;
- screen checkpoints cannot resume production and production checkpoints cannot resume screening;
- production-only `n` changes invalidate production-dependent state only, not valid target-size screening/selection.

### Gate F - Documentation, migration, and structural cleanup

Update current normative architecture/spec/user/config documentation and active workplan index so:

- `n1/n2/n3` are always called screening boundaries/fidelities;
- `n3` is the terminal screening boundary, never screen horizon;
- `n` is the independent production maximum/horizon;
- old horizon-based target-size documents remain historical only and are not current authority;
- no current dependency graph or structural assertion binds a screen-horizon authority separate from the boundary tuple.

Archive/supersede the prior target-size final-closure plan only when implementation and validation under this rework are complete; until then, this workplan is the controlling correction for conflicting semantics.

## Acceptance boundary

Material acceptance must exercise the real semantic owners:

```text
current TOML/config
-> CampaignStore / current-state reconciliation
-> target-size study/boundary owner
-> campaign/run construction
-> resolved MaceJobArtifact protocol classification
-> shared scheduler
-> TRAIN2 runtime-plan assembly
-> real boundary stop/persist/restart owner
-> target-size evidence reduction
-> next-boundary survivor authorization
-> final selected-size freeze
```

Allowed doubles are below this boundary: expensive external numerical MACE stepping, GPU execution, and expensive prediction payloads may be replaced with deterministic bounded fakes after real authorization/runtime assembly.

Forbidden substitutions include patching/reimplementing the classifier, boundary decision, survivor reducer, scheduler authorization, runtime-plan owner, CampaignStore, restart validation, or selected-size state transition when those behaviors are under acceptance.

## Task-specific acceptance

Required after the final material executable edit:

1. **Default exact boundary:** `(1,3,10)`: every candidate stops after epoch 1 before coarse ranking; only survivors can reach 3; only finalists can reach 10; no screen epoch 11 exists.
2. **Nondefault exact boundary:** e.g. `(2,5,12)`: identical semantics with no screen-horizon field/denominator.
3. **Classifier regression:** real target-size campaigns classify TRAIN2; genuine historical campaigns remain historical; mixed/inconsistent protocol authority fails closed.
4. **Reporter regression:** coarse prints `epoch 1/1`, short uses `/3`, final uses `/10`; no current target-size `schedule_horizon` output exists.
5. **Continuation authenticity:** survivors resume exact parent checkpoint/optimizer/scheduler/RNG state; eliminated candidates never resume.
6. **Evidence exactness:** reducers reject nonboundary checkpoints as substitutes for the active boundary.
7. **Overshoot recovery:** persisted run/evidence beyond the active boundary cannot be accepted as current exact-boundary evidence and routes to safe screen restart/invalidation while preserving valid DATA7/DATA8.
8. **Production independence:** production `n` changes preserve valid screen/selection; production checkpoint selection still searches admissible epochs up to `n` and may choose earlier checkpoints.
9. **Geometry:** `0<n1<n2<n3` and `n>0`; no target-size rule requires `n3<n`.
10. **Cross-role restart isolation:** screen->production and production->screen continuation fail closed.
11. **Historical generation safety:** old fixed/full-schedule/horizon-based screen evidence is not silently relabeled current exact-boundary evidence; compatible candidate DATA7/DATA8 may be reused.
12. **Structural absence:** current source/docs/tests contain no active semantic target-size-screen horizon authority or dual boundary/horizon reporter.
13. **Stage-local affected regression:** required after each behavior-changing gate before dependent implementation proceeds.
14. **Final affected-surface regression:** re-derive from the assembled diff and run all plausibly affected modules/callers.
15. **Final integration:** rerun the assembled real-owner path after the last executable change.

Full GPU, long real-data, production-scale timing, RAM/VRAM, and target-workstation qualification remain deferred to the established final-release qualification workflow.

## Implementation authority

### Frozen

- target-size screening owns exactly three positive strictly increasing boundaries `(n1,n2,n3)`;
- screening has no epoch-selection horizon concept;
- the active boundary checkpoint is the only checkpoint admissible for that rung's size comparison;
- survivors continue one exact trajectory across boundaries; they do not restart independently;
- terminal boundary `n3` may be used only as a derived numerical schedule parameter where mathematically required, never as an independent persisted screen authority;
- target-size progress uses the active stage/boundary denominator only;
- production maximum `n` is independent and remains a real horizon for trajectory-wide checkpoint selection;
- no target-size rule requires `n3<n`;
- campaign policy-family classification uses authoritative resolved job protocols, not nonexistent run protocol objects;
- overshot screen state fails closed;
- production starts fresh and cross-role restart remains forbidden;
- DATA7/DATA8 scientific reuse is preserved where inputs are unchanged;
- full GPU/production qualification is deferred.

### Delegated

- exact schema/version numbers;
- exact internal generic TRAIN2 field names where production/runtime compatibility requires them;
- exact reporter phrasing consistent with boundary-only semantics;
- exact narrow refactoring used to supply resolved job protocols to campaign classification;
- exact migration record names and diagnostics;
- exact bounded fake numerical child/evaluator implementation.

### Reopen only on evidence

Reopen only the affected design surface if assembled evidence proves:

- deterministic exact continuation cannot be preserved without a separately mutable screen budget distinct from the boundary tuple;
- an external governed scientific contract explicitly requires screen checkpoint selection across nonboundary epochs;
- production checkpoint selection is intentionally coupled to target-size screen state by an authoritative contract outside this scope;
- DATA7/DATA8 content truly depends on the removed screen-horizon concept;
- current persisted state lacks sufficient authentic information to distinguish safe exact-boundary continuation from overshot/old-generation evidence.

Implementation inconvenience, old tests encoding the superseded horizon model, or compatibility with accidental current output are not redesign triggers.

## Initially expected affected surface

Primary executable/authority surface:

- `mdstats/training_data/target_size_study.py`;
- `mdstats/training_data/_campaign_cli_core.py`;
- `mdstats/training_data/train2_runtime.py`;
- `mdstats/training_data/train2_policy.py` where generic runtime contracts require adaptation;
- `mdstats/training_data/campaign_execution.py` / campaign-run resolution owners;
- target-size config validation, stage-config digests, restart/invalidation, status/progress;
- target-size/performance planning consumers such as `perf_p2r.py` if they encode screen-horizon semantics;
- persistence/serialization/migration consumers of target-size evidence.

Documentation/structural surface includes current target-size/TRAIN2/PERF-P2R specs, architecture/dependency graph, campaign guide, example/generated config comments, active workplan index, and tests protecting the superseded terminology/geometry.

Final implementation must re-derive the affected surface from the actual diff and callers rather than treating this list as exhaustive.
