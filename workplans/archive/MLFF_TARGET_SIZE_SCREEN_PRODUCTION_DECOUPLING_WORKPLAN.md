---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-SCREEN-PRODUCTION-DECOUPLING-V1
protocol_version: 5.7.0
status: complete
created_date: 2026-08-25
completed_date: 2026-08-25
reviewed_head: ea196babecd951491ae4656d3b3e38b8eb866144
supersedes_conflicting_target_size_design: true
---

# MLFF Target-Size Screening / Production-Horizon Decoupling Workplan

## Objective

Correct TARGET-SIZE-V5 so target-size selection is a lightweight configurable successive-fidelity screen whose own training/scheduler horizon is the final screening boundary `n3`, while the expensive configurable production horizon `n` is reserved for a separate fresh production-training campaign after target size is frozen.

The default product behavior is:

```text
screening:  1 -> 3 -> 10, horizon = 10
production: fresh 0 -> 30, selected target size only
```

The durable success criterion is that screening, persistence/restart, migration, scheduling, progress, invalidation, and downstream authorization all preserve this authority split without rebuilding scientifically unchanged DATA7/DATA8, without relabeling historical screen evidence, and without allowing screen checkpoints/optimizer state to become production continuation state.

## Authority and precedence

This workplan is the controlling target-size scientific/design contract for the decoupling revision. It supersedes every conflicting target-size/full-horizon statement in:

- `workplans/active/MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`;
- `workplans/active/MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md`; and
- `workplans/active/MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW2_AMENDMENT.md`.

In particular, the following earlier decisions are obsolete for current TARGET-SIZE-V5 execution:

- screening boundaries as checkpoints on the production full-`n` schedule;
- `0 < n1 < n2 < n3 <= n` as the current executable geometry;
- current `(3,10,30)/30` as a valid screen/production combination;
- production `n` as part of target-size study/screen evidence authority;
- production-horizon changes requiring target-size screening to restart;
- `FULL_TRAIN2_SCHEDULE -> COARSE_SCREEN/SHORT_SCREEN/FINAL_SCREEN` as current identity dependencies;
- target-size live progress using production `n` as its schedule denominator.

Nonconflicting Rework-3 decisions remain preserved and are incorporated here where material, especially policy-independent DATA7/DATA8 candidate-prefix authority, exact checkpoint/optimizer/RNG continuation inside screening, fail-closed compatibility, immutable predecessor DATA8 reuse only after authentic re-authentication, real-owner/proxy-proof acceptance, and deferred full GPU/production qualification.

## Diagnosis and protected concerns

### Current-state diagnosis

At reviewed head `ea196babecd951491ae4656d3b3e38b8eb866144`, the source has the desired fresh default `TargetSizeStudyPolicy.fidelity_epochs == (1,3,10)` and the desired shrinking candidate state machine, but the screen remains coupled to production horizon `n` in several authorities:

1. `TargetSizeStudyPlan` persists `training_horizon_epochs` and validates `n3 <= training_horizon_epochs`.
2. Successful screen evidence requires `planned_epochs == plan.training_horizon_epochs` and normalized progress against that horizon.
3. runtime assembly uses the production training budget as the frozen scheduler horizon while `execution_epoch_limit` only pauses at the active screen boundary.
4. TRAIN2 planned optimizer updates/structures and LR progress are therefore computed against production `n`, even when execution stops at `n1`, `n2`, or `n3`.
5. PERF-P2R derives both screen schedule horizon and production target epoch from `study.training_horizon_epochs`.
6. the dependency graph explicitly binds `FULL_TRAIN2_SCHEDULE` into all three screen stages.
7. the fixed predecessor migration can reconstruct live current `(3,10,30)/30` screening state.
8. the existing flexible-fidelity tests and workplans intentionally protect these full-`n` semantics.

This is a workplan/design deficiency in the earlier flexible-fidelity contract, not merely a reporter defect.

### Final independent-review additions

The final Software Design challenge identified further consequences that must not be left for implementation to infer:

- **run identity/namespace:** a 10-epoch screen and a fresh 30-epoch production run for the same selected size/seed must not collide in run digest, checkpoint directory, runtime summary, model export, or restart ownership;
- **boundary identity:** `n1 -> n2 -> n3` remains one screening trajectory, so changing only `execution_epoch_limit` between screen commands must not create a different scientific screen run;
- **configuration identity:** production `n` must be removed from target-size screen/study identity and target-size restart invalidation, but other training hyperparameters that materially affect screen ranking remain screen-authoritative;
- **generation separation:** authenticated fixed predecessor state, the pre-decoupling flexible-fidelity generation, and the new decoupled-screen generation must be distinguishable; no old plan/evidence may be silently reinterpreted under new planned-epoch semantics;
- **mid-screen production-budget edits:** `n:30->40` while a valid 1/3/10 screen is partially complete must preserve/resume that screen; only future production authority changes;
- **failure evidence:** target-size numerical/scientific failure records must bind the screen budget/schedule, not production `n`, just as successful evidence does;
- **boundary durability:** screen checkpoints at exact `n1/n2/n3` endpoints must remain durably resumable regardless of production checkpoint policy;
- **production multiplicity:** “selected size only” constrains data size, not the configured production protocol topology; production may still own its configured seeds/folds/final-development jobs, all fresh and distinct from screening jobs;
- **SIZE-FIDELITY isolation:** explicit exhaustive calibration may retain a full-reference horizon when scientifically required, but routine `select-target-size` must never schedule that exhaustive full-`n` calibration as part of ordinary selection;
- **operator reporting:** production `n` may be displayed as a separate future-production setting, but it must never serve as the screen scheduler denominator, screen run identity, or authorization horizon.

### Protected concerns

Implementation must preserve:

- fixed TARGET-SIZE-V5 candidate universe and MVQUAL hard admission;
- `q -> min(q,4) -> 2 -> 1` promotion geometry;
- paired screening-seed target-only ranking and existing equivalence rules;
- exact continuation ancestry between screen boundaries using checkpoint, optimizer, and RNG state;
- candidate-specific numerical/scientific failure semantics without converting infrastructure/programming failures into scientific evidence;
- policy-independent DATA7/DATA8 candidate-prefix scientific authority;
- immutable scientifically identical DATA7/DATA8 reuse across downstream fidelity/production-budget changes;
- immediate-predecessor compatibility only when authenticated; unknown/ambiguous generations fail closed;
- no historical target-size screen/checkpoint/evaluation/selection evidence relabeling as current decoupled evidence;
- current preparation-scientific identity boundaries unless direct evidence shows a true dependency change;
- routine functional regression/integration distinct from final production/GPU qualification.

## Engineering envelope

### Functional/scientific geometry

Current executable configuration must satisfy:

```text
0 < n1 < n2 < n3 < n
```

where:

- `n1,n2,n3` are target-size screening boundaries;
- screen training/scheduler horizon is exactly `n3`;
- `n` is the separate production training horizon;
- default `(n1,n2,n3,n) = (1,3,10,30)`.

A current explicit `(3,10,30)/30` configuration is invalid because it consumes the full production budget during screening. A historical fixed `(3,10,30)/30` record remains readable only as historical compatibility evidence and never becomes current executable screen state.

### Screening cost geometry

For `q` qualified sizes, `s` screening seeds, `c=min(q,4)` coarse survivors, and `f=2` finalists, authorized successful screening work is bounded by:

```text
q*s*n1 + c*s*(n2-n1) + f*s*(n3-n2)
```

subject to earlier candidate failures/eliminations reducing later work.

For five sizes and two seeds under default 1/3/10 this is at most 54 candidate-epochs, not a hidden 30-epoch trajectory per candidate.

### Runtime/resources

Reuse the existing TRAIN2 runtime and continuation machinery. Do not create a second trainer, scheduler implementation, or duplicate checkpoint system solely for screening. Screening may use the same training hyperparameter families and execution backend as production where scientifically appropriate, but it has its own budget authority (`planned_epochs=n3`).

No full production/GPU qualification is required for implementation closure. Bounded CPU/synthetic/reduced-data functional tests may fake expensive MACE execution only below the real authorization/runtime-plan/persistence owners.

## Product design

### 1. Two training roles, one generic runtime

Define two semantically distinct roles:

```text
TARGET-SIZE SCREEN
  data population: qualified/surviving candidate sizes
  screen seeds: TargetSizeStudyPolicy.screening_optimizer_seeds
  budget horizon: n3
  active stop: n1, then n2, then n3
  continuation: exact within one screen trajectory
  evaluation: target-size target-only evidence
  terminal action: freeze selected target size and stop

PRODUCTION TRAINING
  data population: selected target size only
  topology: configured production seeds/folds/final jobs
  budget horizon: n
  start: fresh from the configured/frozen foundation/training initialization authority
  optimizer/scheduler/RNG: fresh production state
  evaluation/admissibility: normal production TRAIN2/EVAL2 authority
```

Both roles should reuse existing TRAIN2 primitives where possible. Role separation must live in authority/run identity and orchestration, not in duplicated algorithms.

### 2. Target-size study owns screen policy, not production budget

`TargetSizeStudyPolicy` remains the sole owner of `(n1,n2,n3)`.

Current `TargetSizeStudyPlan` must not persist production `n`. Prefer a derived screen-horizon property:

```text
screening_horizon_epochs = policy.fidelity_epochs[-1]
```

rather than persisting a redundant second screen-horizon field.

Production `n` remains owned by `TrainingBudgetPolicy` / production training configuration and is consumed only after target-size selection where production work is assembled.

### 3. Screen evidence semantics

For default 1/3/10, successful screen evidence is:

```text
coarse: completed=1,  planned=10, normalized_progress=1/10
short:  completed=3,  planned=10, normalized_progress=3/10
final:  completed=10, planned=10, normalized_progress=1
```

All successful and failure screen evidence must authenticate the same screen training protocol/budget/LR schedule for a surviving `(size,seed)` trajectory. The schedule/budget identity must bind horizon `n3`; production `n` must not be recoverable as a hidden screen schedule authority.

### 4. Continuation and pause control

The screen is not three independent retrainings. It is one trajectory per `(size,seed)`:

```text
0 -> n1 -> n2 -> n3
```

Only surviving candidates resume. Existing exact parent checkpoint/optimizer/RNG ancestry remains required.

`execution_epoch_limit` is a command-local pause boundary, not a scientific trajectory identity. Moving the limit from `n1` to `n2` to `n3` must preserve schedule-defining authorities and permit exact restart. The current runtime behavior that tolerates a changed runtime-plan digest when only the execution limit expands may be retained if it continues to prove equality of all schedule-defining authorities.

### 5. Fresh production boundary

After final-screen selection:

- `select-target-size` terminates successfully; it does not continue into production training;
- the selected target size is persisted/frozen;
- immutable selected-size DATA7/DATA8 may be reused;
- production begins under a distinct training role and run namespace;
- production model/optimizer/scheduler/RNG state is fresh and must not descend from the final screen checkpoint;
- production may execute all configured folds/seeds/final-development jobs for the selected size.

If the existing run digest/path schema already distinguishes screen vs production robustly, reuse it. Otherwise add the minimum explicit versioned role identity necessary to prevent collisions. Do not add role to DATA7/DATA8 scientific identity.

### 6. Configuration and invalidation ownership

Only production budget `n` is decoupled from target-size screen identity. Do not broadly remove training configuration from screen authority.

Training/model parameters that affect screen trajectories or ranking (for example optimizer policy, learning-rate shape/base rate, objective weights, batch/exposure semantics, model/foundation identity, and any other scientifically material training control) remain part of the appropriate screen training authority and invalidate stale screen evidence when changed.

Production `n` must not participate in:

- target-size study content identity;
- target-size policy digest;
- screen runtime budget/schedule identity;
- target-size stage config digest/restart equivalence;
- candidate DATA7/DATA8 authority.

Production `n` must participate in production budget/schedule/run identity.

### 7. Generation/compatibility model

Recognize at least three populations explicitly where persistence requires the distinction:

1. authenticated fixed predecessor: fixed `(3,10,30)/30`, historical v8-study/v6-policy semantics;
2. pre-decoupling flexible-fidelity: configurable boundaries but screen evidence/checkpoints bound to production full-`n` schedule;
3. current decoupled-screen generation: screen horizon `n3`, production horizon independent.

Current target-size plan/evidence schemas or authority version(s) must be bumped/changed as necessary so generation 2 cannot deserialize as generation 3 with silently changed `planned_epochs` meaning.

Candidate-prefix DATA7/DATA8 authority should remain stable/policy-independent where its semantic formula is unchanged. Compatibility may re-authenticate immutable predecessor materialization, but not old screening evidence.

### 8. SIZE-FIDELITY

SIZE-FIDELITY exhaustive calibration is a separate scientific qualification workflow. It may own an explicit full-reference horizon when that is necessary to measure fidelity quality. Routine `select-target-size` does not execute that exhaustive matrix and does not use its full-reference horizon as ordinary screening budget.

Current acceptance that depends on `final_screen_epoch == production/reference_epoch` as an ordinary configuration must be retired for the current target-size product because executable `n3 < n` is strict.

## Implementation obligations

### O1 - Establish current schema/authority separation

**Protected concern:** current persistence encodes production horizon inside target-size study and screen evidence.

**Required end state:** current target-size plan/evidence represent the decoupled generation and cannot silently accept old full-`n` semantics.

**Required implementation consequences:**

- remove current production-horizon ownership from `TargetSizeStudyPlan`;
- derive screen horizon from `policy.fidelity_epochs[-1]`;
- update `build_target_size_study()` and `validate_target_size_study_authority()` accordingly;
- require successful screen evidence `planned_epochs == n3` and `completed_epochs == active semantic boundary`;
- require normalized progress against `n3`;
- ensure trajectory-failure evidence authenticates the decoupled screen budget/schedule identity;
- bump target-size study/plan/evidence authority/schema where necessary to distinguish old flexible full-`n` records from current decoupled records;
- retain candidate-prefix authority formula/version when its semantics are unchanged rather than forcing DATA7/DATA8 rebuild.

**Forbidden behavior:** dropping the horizon field while still supplying production `n` through another screen digest or schedule owner.

**Expected surface:** `target_size_study.py`, exports/serialization, target-size tests, migration/restart consumers.

**Acceptance:** focused round-trip, boundary, wrong-horizon, old-generation rejection/migration, continuation ancestry, failure-evidence, and candidate-authority tests.

### O2 - Enforce current configuration geometry without broad semantic decoupling

**Protected concern:** old config normalization can activate 3/10/30 and config identity can still bind production `n` to screening.

**Required end state:** current config validates `0 < n1 < n2 < n3 < n`; fresh default resolves to `(1,3,10)/30`; production `n` is excluded only from target-size screening identity.

**Required implementation consequences:**

- update generated template/example comments and validators;
- reject current explicit `(3,10,30)/30` before persisted state is mutated;
- recognized historical-only epoch keys may authenticate historical state but must not become current executable boundaries;
- when no explicit current `fidelity_epochs` exists in a supported historical migration, current effective screen defaults to `[1,3,10]`;
- mixed/ambiguous legacy and current fidelity declarations fail closed rather than guessing;
- audit `_stage_config_digest`, target-size configuration projections, restart reconciliation, and all equivalent identity owners so production `max_num_epochs` does not invalidate a current screen/selection;
- retain other training fields in screen authority when they materially affect the screen trajectory/ranking.

**Acceptance:** real config loading for default, nondefault `(2,5,12)/40`, invalid equal-horizon cases, ambiguous migration cases, and identity-digest comparison proving only `n` is decoupled where intended.

### O3 - Assemble a screen-budget TRAIN2 runtime

**Protected concern:** current `execution_epoch_limit` pauses work but runtime budget/planned updates/LR progress remain production-horizon based.

**Required end state:** target-size screen runtime uses `TrainingBudgetPolicy(planned_epochs=n3)` with boundary-specific execution limits `n1`, `n2`, `n3`.

**Required implementation consequences:**

- screen MACE/runtime `max_num_epochs` authority equals `n3`;
- planned optimizer updates and planned structures are computed from `n3`;
- LR progress/multiplier uses the `n3` screen budget;
- runtime summary, companion, history, numerical-failure record, checkpoint validation, and schedule/budget digests bind screen horizon `n3`;
- exact checkpoint persistence exists at each semantic screen boundary independent of production checkpoint policy;
- extending `execution_epoch_limit` within the same screen trajectory preserves the schedule-defining budget/LR/protocol identities;
- production continues using `TrainingBudgetPolicy(planned_epochs=n)` separately.

**Suggested realization:** reuse `Train2RuntimePlan`; do not create a second runtime implementation.

**Acceptance boundary:** real runtime-plan/budget/schedule assembly must execute; actual heavy MACE stepping may be replaced below that boundary. A helper that merely constructs `TrainingBudgetPolicy(10)` is not sufficient acceptance.

### O4 - Make screen and production run identities collision-proof

**Protected concern:** same selected size/seed can exist in both screen and production, and old artifacts/checkpoints must not be resumed under the wrong role.

**Required end state:** screen and production have distinct semantic training-run identity and noncolliding filesystem/output ownership while DATA7/DATA8 remains shared/reusable.

**Required implementation consequences:**

- audit training run digest, job/variant identity, checkpoint/model directories, runtime summary/companion paths, execution records, and model export names;
- ensure role/stage identity distinguishes target-size screen from production when existing identity is insufficient;
- screen `n1/n2/n3` continuation for the same `(size,seed)` must retain one screen-run identity despite execution-limit changes;
- production starts from fresh model initialization authority and fresh optimizer/scheduler/RNG state, never from final-screen continuation state;
- a stale screen companion/checkpoint presented as production must fail closed; a stale production companion presented as screen must fail closed.

**Acceptance:** bounded same-size/same-seed fixtures prove no collisions, cross-role restart is rejected, and normal within-screen continuation succeeds.

### O5 - Correct orchestration and candidate elimination

**Protected concern:** policy fields alone do not prove that later training is actually prevented for eliminated candidates.

**Required end state:** real `select-target-size` orchestration authorizes only:

```text
all qualified (size,seed)        -> n1
coarse survivors only            -> n2
short finalists only             -> n3
then selection freezes and command returns
```

**Required implementation consequences:**

- boundary loop remains driven by current study state;
- no eliminated/failed candidate receives later screen authorization;
- no screen candidate can be authorized beyond `n3`;
- selection command must not fall through into production training;
- operator output may display future production `n` separately but screen phase/progress/schedule denominator must be `n3`.

**Acceptance boundary:** current TOML -> real `CampaignStore` -> real preflight/current-state authorization -> real target-size study -> real runtime-plan/job authorization -> fake external train/eval -> real evidence reduction -> next boundary. Do not patch the owners deciding sizes, boundaries, schedule budget, or state transition.

### O6 - Separate PERF-P2R screen planning from production planning

**Protected concern:** PERF-P2R currently derives both screen horizon and production target epoch from `study.training_horizon_epochs`.

**Required end state:** screen plans derive horizon `n3`; production plan consumes independent production budget `n` after selected size is frozen.

**Required implementation consequences:**

- remove production-horizon lookup from target-size study;
- screening stages use `schedule_horizon_epoch=n3` and preserve continuation start/end boundaries;
- production stage is `start_epoch=0`, selected-size only, fresh/noncontinuing, horizon `n`;
- production topology may include configured seeds/folds/final jobs; target-size screening seeds do not become production-run authority;
- bump PERF-P2R serialization schema if existing persisted meaning changes.

**Acceptance:** current screen plans are 1/10, 3/10, 10/10 for default; production plan is fresh 0/30 and rejects screen continuation state.

### O7 - Reconcile historical and transitional persistence without expensive DATA7/DATA8 rebuild

**Protected concern:** fixed predecessor migration can currently resurrect 3/10/30; pre-decoupling flexible records could be silently misread after schema change.

**Required end state:** historical scientific candidate materialization is reused when authentically equivalent, while all old screen execution/evidence/selection semantics that depend on full-`n` schedule are invalidated as current authority.

**Required implementation consequences:**

For authenticated fixed predecessor and supported pre-decoupling flexible generation:

- preserve authenticated REPAIR2/MVQUAL and scientifically identical candidate DATA7/DATA8;
- preserve/reuse existing predecessor candidate-authority compatibility receipts only when their inputs remain valid;
- do not promote historical screen checkpoint, optimizer/RNG, evaluation, ranking, selected-size, or production state into current decoupled authority;
- construct a fresh current target-size study from current policy and start at `n1`;
- current default migration therefore authorizes epoch 1, not epoch 3;
- unsupported/ambiguous generations fail closed with actionable generation-specific diagnostics;
- retain forensic historical records under existing historical-state conventions where applicable rather than deleting them silently.

**Acceptance boundary:** real persisted `CampaignStore` close/reopen, authentic historical study/policy population, real DATA8 discovery/compatibility owner, real study reconstruction, real next-operation/authorization. No custom store, DB rewrite to expected current digest, DATA8 deletion/rebuild, or patched matrix validator may close this claim.

### O8 - Implement exact invalidation/restart frontiers

**Protected concern:** decoupling is incomplete if config reconciliation still restarts the screen when only production `n` changes or incorrectly preserves screen evidence when screen geometry changes.

**Required current frontiers:**

| Change | prepare/REPAIR2/MVQUAL/DATA7/DATA8 | screen evidence/state | selected target size | production state |
| --- | --- | --- | --- | --- |
| `n1` | preserve when science unchanged | invalidate/restart from new `n1` | invalidate | invalidate |
| `n2` | preserve when science unchanged | invalidate/restart from `n1` | invalidate | invalidate |
| `n3` | preserve when science unchanged | invalidate/restart from `n1` because screen budget/LR horizon changed | invalidate | invalidate |
| production `n` | preserve | preserve/resume | preserve | invalidate/rebuild production budget/schedule/downstream only |
| material screen-training hyperparameter | preserve upstream data when valid | invalidate as required | invalidate | invalidate |
| true preparation-scientific input | invalidate/reopen at narrowest correct upstream owner | invalidate | invalidate | invalidate |

Production `n:30->40` must preserve both completed selection and a partially completed valid 1/3/10 screen. A currently running/restartable screen continues on horizon 10; eventual production uses 40.

**Acceptance boundary:** modify actual TOML, close store, reopen through normal config/restart/next-operation reconciliation; direct invocation of an invalidation helper cannot close the frontier claim.

### O9 - Isolate SIZE-FIDELITY calibration from routine selection

**Protected concern:** explicit fidelity calibration can legitimately require expensive reference trajectories, but ordinary target-size selection must remain lightweight.

**Required end state:** `select-target-size` does not schedule exhaustive SIZE-FIDELITY full-reference runs. Explicit calibration remains available under its own scientific authority/command/lifecycle if currently supported.

**Required implementation consequences:**

- trace every routine selection caller/consumer of `size_fidelity.py`;
- remove any implicit full-reference calibration from normal selection if present;
- revise current tests/spec language that treats `n3 == n` as an ordinary target-size execution case;
- preserve explicit calibration reference semantics where they are independently required and clearly separated from production training authority.

**Acceptance:** instrumented normal selection proves only the successive-fidelity population is trained; no exhaustive all-size full-`n` reference matrix is authorized.

### O10 - Reconcile architecture, documentation, and observability

**Protected concern:** old normative docs/tests/dependency graph currently encode the architecture being removed and could reintroduce it later.

**Required end state:** all current authoritative docs and structural tests describe the two-authority design consistently.

**Required implementation consequences:**

- remove current dependency edges `FULL_TRAIN2_SCHEDULE -> COARSE_SCREEN/SHORT_SCREEN/FINAL_SCREEN`;
- represent screening schedule/budget as target-size-screen authority derived from `TargetSizeStudyPolicy`/`n3`;
- keep `FULL_TRAIN2_SCHEDULE` as production authority downstream of frozen target-size decision/data prefix;
- update target-size spec, architecture manual/source, dependency graph, campaign guide, example/generated TOML comments, and relevant revision/index history;
- update TRAIN2 runtime documentation from “original full-horizon trajectory” language to role-local frozen budget semantics where needed;
- screen progress/status reports effective fidelity tuple, screen horizon `n3`, active boundary, and optionally future production horizon as a separate field;
- `/30` must not appear as default screen schedule progress for a 1/3/10 screen.

**Structural acceptance:** repository search/graph assertions prove no current normative full-`n` screen dependency remains, while historical documents may retain historical wording only when clearly noncurrent.

### O11 - Preserve proxy-proof acceptance and affected regression

Material acceptance must execute the real production owner whose behavior is claimed. Existing Rework-3 anti-bypass principles remain binding.

For claims involving config normalization, `CampaignStore`, target-size construction, migration, DATA8 compatibility, runtime budget/schedule assembly, job authorization, evidence reduction, restart/invalidation, PERF-P2R production handoff, or SIZE-FIDELITY isolation, the corresponding real owner/path must execute.

Allowed doubles are below/outside those boundaries: physical MACE training, GPU work, expensive prediction values, and reduced bounded scientific payloads after real authorization.

Forbidden acceptance substitutions include patching/reimplementing:

- current config normalization/geometry validation;
- `_ensure_target_size_study` or successor;
- current DATA8 discovery/compatibility/matrix owner when reuse is the claim;
- runtime budget/schedule-plan assembly when horizon semantics are the claim;
- target-size next-size/next-boundary authorization;
- evidence reduction/selection state transitions;
- `CampaignStore` when persistence/restart is the claim;
- normal restart/next-operation/config-change detection;
- direct invalidation helper calls as frontier acceptance;
- PERF-P2R production consumer when screen->production separation is the claim;
- routine-selection caller when SIZE-FIDELITY isolation is the claim.

Extend/restore the existing targeted anti-bypass guard only as needed to cover the new gate-closing tests; do not create a repository-wide mock ban.

## Implementation authority

### Frozen

- current executable geometry is `0 < n1 < n2 < n3 < n`;
- defaults are `(1,3,10)/30`;
- screen horizon is exactly `n3`;
- production horizon `n` is independent and reserved for production;
- screens continue one exact trajectory through `n1 -> n2 -> n3`; they are not independent retrainings;
- eliminated/failed candidates receive no later screen work;
- `select-target-size` terminates after selection and cannot authorize epoch `> n3`;
- production is fresh, selected-size-only with respect to data size, and does not continue screen model/optimizer/scheduler/RNG state;
- production may retain its configured seed/fold/final topology;
- screen and production run/filesystem identities must not collide;
- only production budget `n` is decoupled; other scientifically material training controls remain screen-authoritative;
- candidate DATA7/DATA8 scientific identity remains independent of downstream screen geometry/production horizon;
- supported historical DATA7/DATA8 may be re-authenticated/reused, but old screen/evaluation/selection state is never relabeled current;
- production `n` change preserves valid current screening/selection and invalidates production-dependent state only;
- any `n1/n2/n3` change invalidates current screen evidence from `n1` rather than attempting partial evidence reuse;
- routine selection does not execute exhaustive SIZE-FIDELITY full-reference calibration;
- full GPU/production qualification is deferred.

### Delegated

- exact field/type names for screen-vs-production role identity if existing identities are insufficient;
- whether screen horizon is exposed as a derived property or local helper, provided no redundant persisted authority is created;
- exact schema/version numbers, provided generations are unambiguous and old full-`n` evidence cannot deserialize as current;
- exact command/status wording;
- exact bounded fake trainer/evaluator implementation;
- exact historical forensic-record naming under existing conventions;
- exact structural/AST mechanism for targeted anti-bypass protection;
- local refactoring needed to share runtime assembly cleanly between screen and production.

Delegated mechanics may not change frozen authority boundaries or reintroduce production `n` into screen identity.

### Reopen only on evidence

Reopen only the affected design surface if direct repository/assembled-integration evidence proves one of these premises false:

- current TRAIN2 runtime cannot support a role-local `n3` budget with expanding execution limits without changing training semantics in a way that breaks exact continuation;
- production initialization is intentionally specified elsewhere to continue target-size screen state and that external governed contract cannot be changed within this scope;
- scientifically valid screen ranking requires the production `n` LR/schedule trajectory rather than a screen-local `n3` schedule, contradicting the explicit stakeholder requirement for lightweight screening;
- DATA7/DATA8 content truly depends on screen/production horizon despite current policy-independent candidate-prefix authority;
- an explicit SIZE-FIDELITY calibration consumer is inseparable from normal selection without removing a required product capability;
- supported persisted generations lack sufficient authentic information to preserve DATA7/DATA8 while safely invalidating old screen state;
- final assembled integration exposes an independent scientific/state-machine defect that invalidates the frozen funnel.

Implementation inconvenience, failing old full-horizon tests, or a desire to preserve obsolete schema behavior is not a redesign trigger.

## Initially expected affected behavioral surface

Primary executable/authority surface:

- `mdstats/training_data/target_size_study.py`;
- `mdstats/training_data/_campaign_cli_core.py`;
- `mdstats/training_data/train2_runtime.py`;
- `mdstats/training_data/train2_policy.py` where budget/schedule assembly contracts require it;
- `mdstats/training_data/perf_p2r.py`;
- `mdstats/training_data/size_fidelity.py` and its routine callers;
- training campaign/run identity and checkpoint/output ownership in `campaign_execution.py` / current run owner as discovered;
- production materialization/DATA8 compatibility metadata only where role/horizon assumptions currently leak into training authority;
- configuration normalization, stage config digests, restart/invalidation, next-operation/status/progress;
- exports/serialization schemas affected by target-size/plan changes.

Persistence/compatibility surface:

- fixed v8/v6 predecessor authentication and DATA8 bridge;
- pre-decoupling flexible-fidelity target-size plan/evidence;
- current decoupled plan/evidence;
- historical/forensic retention and current-state invalidation.

Documentation/structural surface:

- `campaign.toml.example` and generated config template;
- `docs/specs/training_data/mlff_target_subset_size_study_spec.md`;
- `docs/specs/training_data/mlff_perf_p2r_successive_fidelity_execution_spec.md`;
- `docs/specs/training_data/mlff_size_fidelity1_calibration_spec.md` where role separation changes current wording;
- `docs/arch_manuals/mlff_training_data_dependency_graph.json`;
- current architecture/manual and campaign user-guide source plus revision/index entry;
- generated documentation descendants only where repository policy requires regeneration.

Primary tests include current equivalents of:

- `tests/test_mlff_flexible_fidelity.py`;
- `tests/test_mlff_target_size_study_v5.py`;
- `tests/test_mlff_target_size_v5_topology.py`;
- campaign CLI/store/config/status/restart tests;
- TRAIN2 runtime/continuation tests;
- progress-reporting tests;
- PERF-P2R tests/specification tests;
- SIZE-FIDELITY tests/specification tests;
- DATA7/DATA8 production materialization and predecessor-authority bridge tests;
- architecture/dependency/specification tests;
- any callers/consumers identified by the final diff.

This list is provisional. Final implementation must re-derive the affected behavioral surface from the assembled diff and actual callers.

## Task-specific acceptance

Generic functional acceptance is inherited from Protocol 5.7.0: focused checks, stage-local affected regression after each material executable stage, final affected-surface re-derivation/regression, assembled integration, and repository-required/broader checks when impact cannot be bounded.

### A - Fresh default selection

Real generated/current TOML and real persistence/orchestration must establish:

```text
fidelity=(1,3,10)
screen horizon=10
production horizon=30
```

Per `(size,seed)` authorization proves all qualified candidates stop at 1 unless promoted, only coarse survivors reach 3, only finalists reach 10, no screen job reaches 11, selected size freezes durably, and `select-target-size` returns without production training.

### B - Nondefault selection

With `(2,5,12)/40`, screen planned horizon is 12 at every screen endpoint and production is fresh horizon 40. No screen denominator/schedule authority is 40.

### C - Production-budget-only change after completed selection

Change `n:30->40` through actual TOML, close/reopen, and normal reconciliation. Preserve DATA7/DATA8, complete screen evidence, and selected size byte/identity-equivalently where applicable. Invalidate old production schedule/checkpoint/downstream state and authorize fresh selected-size production horizon 40.

### D - Production-budget-only change during partial screen

Starting from a durable valid default screen paused after `n1` or `n2`, change `n:30->40`, close/reopen, and prove the exact same screen trajectory resumes on horizon 10 without restarting from zero. Eventual production uses 40.

### E - Screen-boundary change

Independently change `n1`, `n2`, or `n3` through actual TOML/reopen. Preserve scientifically unchanged upstream DATA7/DATA8; invalidate old screen evidence/selection; construct fresh screen from configured `n1`. An `n3` change must invalidate earlier evidence because the screen budget/LR trajectory changed.

### F - Invalid equal-horizon current configuration

Current `(3,10,30)/30`, `(1,3,10)/10`, or any `n3 >= n` fails validation before current persisted authority is mutated. Historical fixed 3/10/30 remains recognizable only as historical evidence.

### G - Historical fixed predecessor -> current default

Real authenticated fixed predecessor store plus complete DATA8 candidate matrix reopens through real compatibility/restart owners. DATA7/DATA8 scientific/tree bytes are preserved; historical 3/10/30 screen/checkpoints/evaluation/selection are not current; fresh current screen is 1/3/10 horizon 10 and first authorized boundary is 1.

### H - Pre-decoupling flexible generation -> current decoupled generation

Persisted old flexible 1/3/10-on-30 evidence must not deserialize/relabel as 1/3/10-on-10 evidence. Reuse authenticated candidate DATA7/DATA8 where compatible, invalidate old screen/selection, and start a fresh current screen.

### I - Cross-role restart isolation

For the selected size and overlapping seed, screen checkpoint/companion cannot satisfy production restart and production checkpoint/companion cannot satisfy screen restart. Normal screen n1->n2->n3 continuation remains valid.

### J - SIZE-FIDELITY isolation

Routine selection authorization logs/records prove no exhaustive all-qualified-size full-production-horizon calibration jobs are scheduled. Explicit SIZE-FIDELITY calibration tests remain separate.

### K - Observability

Default target-size live progress reports schedule horizon 10 and active boundary semantics. Production horizon 30 may appear only as a distinct future-production setting, not as screen schedule denominator. Production training later reports its own 30-epoch horizon.

### L - Structural absence/current-authority checks

Current source/docs/graph/tests contain no active identity edge from production full schedule to target-size screens and no current specification that blesses `n3 == n` for normal execution. Historical/archive material is exempt when clearly historical.

### M - Final affected regression/integration

On one assembled candidate:

1. reconcile every obligation above;
2. re-derive affected callers/consumers from final diff;
3. rerun all stage-local tests invalidated by later edits;
4. run complete affected-surface regression;
5. run real-owner assembled integration for A-I plus J/K where applicable;
6. run repository-required checks and broader/full suite if the affected surface cannot be bounded confidently;
7. record any genuinely unavailable environment-dependent check as unavailable, not passed.

Production qualification: **deferred**. Do not run long real-data/GPU production qualification as part of this implementation workplan; it remains part of final release qualification.

## Implementation sequence

### G0 - Authority/specification freeze and old-contract reconciliation

- install this workplan as controlling target-size authority;
- identify every current source/test/spec/graph assertion that encodes full-`n` screening;
- classify each as change-required, historical-only, or independently valid;
- map current persisted generations and run/checkpoint identity owners.

**Gate:** no implementation stage depends on an unresolved authority conflict; generation populations and role identities are explicit.

### G1 - Target-size schema/config/generation correction

Implement O1, O2, and the persistence-generation portion of O7. Add focused serialization/config/migration tests and stage-local affected target-size/config regression.

**Gate:** new current study/evidence cannot contain production horizon; old full-`n` evidence cannot deserialize as current; config enforces strict geometry; DATA7/DATA8 candidate authority remains reusable.

### G2 - Runtime budget/continuation/run-identity correction

Implement O3 and O4. Exercise real runtime-plan assembly, exact screen continuation, cross-role rejection, numerical failure evidence, and checkpoint/output identity. Run stage-local TRAIN2/campaign execution regression.

**Gate:** screen planned horizon is n3 everywhere; n1->n2->n3 resumes exactly; production role is collision-proof and fresh.

### G3 - Orchestration/PERF-P2R/production handoff

Implement O5 and O6. Drive bounded real-owner default/nondefault screening with fake heavy compute only below authorization, then freeze selected size and authorize separate production plan.

**Gate:** population pruning is enforced per candidate, no screen work >n3, command stops after selection, production is fresh selected-size horizon n.

### G4 - Restart/invalidation/compatibility frontiers

Complete O7 and O8. Use real close/reopen and normal reconciliation for historical fixed, old flexible, n1/n2/n3, completed-selection `n` change, and mid-screen `n` change.

**Gate:** exact preservation/invalidation matrix passes; expensive unchanged DATA7/DATA8 is not rebuilt; production `n` no longer invalidates valid screen/selection.

### G5 - SIZE-FIDELITY isolation, docs, graph, observability

Implement O9/O10 and reconcile old full-horizon tests/specs. Preserve explicit calibration capability where independent. Run stage-local SIZE-FIDELITY/progress/architecture/documentation regression.

**Gate:** current architecture is internally consistent and routine selection has no exhaustive full-`n` calibration path.

### G6 - Proxy-proof assembled acceptance and final regression

Complete O11 and task-specific A-M on one assembled commit. Re-derive final affected surface and run final affected regression/integration plus repository-required checks.

**Gate:** no material claim is closed by a proxy that can stay green while its semantic owner is broken; no required affected check is failing or unexecuted.

## Implementation closeout evidence

The implementation gates G0-G6 are complete on the current development branch.

- The affected CPU/control-plane regression passed with `216 passed, 1 skipped`. The one skip is the environment-dependent real-LTA campaign path (`real LTA training root not supplied`); it is recorded as unavailable rather than treated as a pass.
- The direct campaign owner regression covers screen/production namespace separation, digest separation, and fail-closed namespace validation.
- The current documentation and assembled architecture were reconciled to screen horizon `n3` and fresh production horizon `n`; current PDFs were regenerated with the pinned Pandoc/Typst toolchain from `archive/mace-dependencies` and visually checked with Poppler.
- GPU and long real-data production qualification remain explicitly deferred to FINAL-GPU1 as required by this workplan.

The unrelated legacy specification slice still reports baseline failures for historical release/version/graph assertions and one raw-config normalization contract; those failures are outside this target-size implementation surface and are not used as acceptance evidence for this closeout.

### G7 - Closeout

Only after G6:

- mark this workplan complete;
- archive/supersede obsolete active flexible-fidelity planning artifacts according to repository workplan policy;
- update `workplans/active/README.md` to remove obsolete target-size precedence language;
- retain explicit production/GPU qualification as deferred final-release work.

## Design handoff closure

The final review reconciled:

```text
explicit stakeholder requirement:
  screening must be lightweight 1/3/10 by default;
  expensive n=30 is reserved for real training

+ diagnosed protected concerns:
  persisted full-n horizon coupling;
  LR/update/schedule coupling;
  legacy 3/10/30 activation;
  run namespace/restart collisions;
  invalidation/config identity;
  generation migration;
  DATA7/DATA8 preservation;
  SIZE-FIDELITY isolation;
  proxy-proof acceptance

+ accepted design:
  screen horizon=n3;
  production horizon=n;
  exact intra-screen continuation;
  fresh post-selection production;
  strict n3<n;
  production-n-only decoupling;
  policy-independent candidate materialization

-> implementation obligations O1-O11
-> task-specific acceptance A-M
-> gated sequence G0-G7.
```

No material requirement or known cross-module consequence identified by the final Software Design review is intentionally left to implementation rediscovery.

## Risks / redesign triggers

The principal remaining risks are implementation-discovery risks rather than unresolved design choices:

- hidden target-size/full-horizon coupling in stage config digests, job identity, checkpoint directories, or schedule validators outside the initially identified files;
- pre-decoupling flexible-fidelity records whose generation cannot be authenticated strongly enough for safe DATA7/DATA8 reuse;
- an explicit calibration/production contract elsewhere that assumes final-screen and full-reference checkpoints are physically identical;
- a training-run naming scheme that cannot distinguish screen and production without a schema/namespace change.

These risks require implementation to trace and reconcile the actual owner. They reopen design only if they invalidate a frozen premise listed under `Reopen only on evidence`; otherwise they are required local consequences under this workplan.
