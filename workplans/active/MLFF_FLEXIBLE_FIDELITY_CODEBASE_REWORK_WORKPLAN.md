---
kind: implementation-workplan
workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1
protocol_version: 5.4.0
---

# MLFF Flexible-Fidelity Codebase Rework Workplan

## Objective

Refactor the target-size screening implementation from a fixed `3 -> 10 -> 30` architecture into a configurable three-boundary successive-fidelity funnel `(n1, n2, n3)` with default `(1, 3, 10)`, while keeping the full TRAIN2 training horizon `n` independent and authoritative through the existing training budget with default `30`.

The implementation must be semantically clean, persistence-safe, scientifically correct, regression-tested, integration-tested, and free of unquarantined current-code leakage from epoch-number-specific state/API/schema assumptions.

This workplan is intentionally prescriptive. The implementer must not invent alternate architecture, new competing epoch authorities, or compatibility behavior that changes the frozen semantics below.

## Diagnosis

The reviewed branch contains multiple fixed-policy couplings rather than a single literal-default problem:

1. target-size state, fields, constants, serializers, and transition logic are named around epochs 3/10/30;
2. `TargetSizeStudyPolicy` currently rejects any fidelity tuple other than `(3, 10, 30)`;
3. PERF-P2R currently treats the third fidelity endpoint as the planned final epoch, so changing the tuple alone would incorrectly collapse production training to `n3`;
4. SIZE-FIDELITY1 currently treats the third screening endpoint as the eventual/full-reference endpoint, so changing the default tuple alone would validate early screens against epoch 10 rather than the full epoch-30 trajectory;
5. campaign configuration exposes three target-size epoch keys in parallel with `[training].max_num_epochs`, creating duplicated/ambiguous epoch ownership;
6. user-facing progress/reporting can show the full schedule denominator during a bounded screening stage, obscuring the actual authorized stop boundary;
7. persisted artifacts and restart state encode numeric-stage names, so schema migration is required; silent reinterpretation is not acceptable.

Therefore this is a cross-cutting authority/state/schema rework, not a literal substitution.

## Engineering envelope

### Required target behavior

For a configured fidelity tuple:

```text
(n1, n2, n3)
```

and full TRAIN2 horizon:

```text
n
```

require:

```text
0 < n1 < n2 < n3 <= n
```

Default current behavior after migration:

```text
(n1, n2, n3) = (1, 3, 10)
n = 30
```

### Screening execution semantics

The implementation must execute:

```text
all qualified candidates: 0 -> n1
survivors:              n1 -> n2
finalists:              n2 -> n3
selection/freeze at:          n3
production model:        0 -> n
```

The following are hard invariants:

- A screening candidate is initialized once for its authenticated TRAIN2 trajectory and then paused/resumed across screening boundaries.
- A survivor must resume from the preceding boundary checkpoint; it must not restart training from epoch zero.
- LR schedule, optimizer configuration, RNG/data ancestry, schedule identity, training-run identity, and checkpoint ancestry remain those of the full `n`-epoch trajectory.
- The current screening stop is an execution limit only; it must not redefine the full schedule horizon.
- Only exact checkpoints at `n1`, `n2`, and `n3` may participate in their corresponding ranking decisions.
- Work beyond a candidate's elimination boundary must not execute.
- Target size freezes only after the final-screen decision at `n3`.
- The selected production model trains to `n`, not merely to `n3`.

### Authority ownership

There must be exactly one conceptual authority for each dimension:

- `(n1,n2,n3)` is owned by target-size size-convergence policy/configuration;
- `n` is owned by the existing TRAIN2 training budget / optimizer max-epoch authority.

Do not add a second user-configurable full-training horizon under target-size configuration.

The implementation must validate consistency between `TrainingBudgetPolicy.planned_epochs` and `MaceOptimizerPolicy.max_num_epochs` using the existing ownership path rather than creating another equality mechanism unless required by actual repository architecture.

### Configuration contract

New/current campaign authoring must use:

```toml
[target_data.size_convergence]
fidelity_epochs = [1, 3, 10]

[training]
max_num_epochs = 30
```

The old keys:

```text
coarse_training_epochs
short_training_epochs
final_training_epochs
```

must not remain current authoring keys.

Legacy campaign configuration may be supported only by an explicit compatibility path. It must never silently inherit the new `(1,3,10)` default if it previously encoded the old fixed behavior.

### Persistence and compatibility

Persisted artifacts that encode old numeric-stage field names or schemas must be handled by one of two explicit outcomes:

1. deserialize through a quarantined legacy adapter that reconstructs the historical old semantics exactly; or
2. reject/fail closed with a clear unsupported-legacy error if exact meaning cannot be recovered safely.

Forbidden behavior:

- reading an old artifact and applying the new default tuple;
- accepting old stage data under a new schema without semantic migration;
- treating an old epoch-30 final-screen artifact as if it were generated by `(1,3,10)` simply because both full horizons are 30;
- silently preserving old numeric public state/API names in current writers.

### Scientific calibration

SIZE-FIDELITY1 must distinguish:

```text
screening checkpoints = n1, n2, n3
full-reference checkpoint = n
```

The full-reference checkpoint is the oracle for eventual/reference finalist and winner behavior.

If `n3 == n`, the same checkpoint may satisfy both roles. The implementation must deduplicate physical evidence/checkpoint requirements where appropriate but preserve both semantic roles.

### Performance/scaling expectations

For `q` initial candidates, `S` coarse survivors, and `F` short finalists, screening candidate-epoch work must follow:

```text
q*n1 + S*(n2-n1) + F*(n3-n2)
```

not:

```text
q*n1 + S*n2 + F*n3
```

because continuation reuses completed prefix work.

For the common old and new defaults with `S=4`, `F=2`:

```text
old: 3q + 7S + 20F
new: 1q + 2S + 7F
```

The implementation must not add redundant retraining, duplicate inference, or checkpoint materialization that materially defeats this reduction.

### Testing/qualification boundary

Regression and integration testing are mandatory throughout implementation.

Full production/data-heavy GPU qualification is deferred. Do not substitute heavy production qualification for functional regression; do not block implementation on machine-specific production benchmarking unless a genuine correctness issue requires it.

## Product design

### Target-size policy model

`TargetSizeStudyPolicy` must carry the three fidelity boundaries as data, defaulting to `(1, 3, 10)`, and validate exactly three ordered positive integer epochs.

Recommended canonical naming:

```text
fidelity_epochs: tuple[int, int, int]
coarse_survivor_limit
short_finalist_count
```

Do not retain epoch-number names such as `epoch3_survivor_limit` or `epoch10_finalist_count` in current public/in-memory models.

The policy must not own `n`; code that needs to validate `n3 <= n` must receive/access the canonical training-budget authority.

### Semantic target-size state machine

Use semantic stage/state names. The current state machine must conceptually support:

```text
awaiting_coarse
awaiting_short
awaiting_final_screen
selected/frozen
```

and stage labels:

```text
coarse
short
final_screen
production
```

Do not encode configured epoch values into stage constants, field names, method names, or serializer keys.

A stage-to-boundary mapping must be derived from the active policy, for example:

```text
coarse       -> fidelity_epochs[0]
short        -> fidelity_epochs[1]
final_screen -> fidelity_epochs[2]
```

Do not maintain a global literal mapping such as `{3: coarse, 10: short, 30: final}`.

### Full horizon

The full training horizon must be read from canonical TRAIN2 policy, e.g. `TrainingBudgetPolicy.planned_epochs`, with existing optimizer-policy consistency enforcement retained.

If a central default constant is introduced, use it only to remove scattered defaults, not to create a new runtime authority. A suitable pattern is:

```text
DEFAULT_TRAINING_EPOCHS = 30
DEFAULT_TARGET_SIZE_FIDELITY_EPOCHS = (1, 3, 10)
```

with runtime values still owned by policy objects/configuration.

### SIZE-FIDELITY1 design

Refactor SIZE-FIDELITY1 so execution plans carry the independent full-reference horizon explicitly and derive screening boundaries from target-size policy.

Recommended semantic model:

```text
coarse_screen_epoch        = n1
short_screen_epoch         = n2
final_screen_epoch         = n3
reference_training_epoch   = n
required_checkpoint_epochs = union(calibration coarse candidates, n2, n3, n)
```

If calibration still evaluates alternative coarse endpoints, those candidates must remain less than `n2` and the first candidate must equal the configured production `n1` default/hypothesis according to existing calibration policy semantics.

Replace ambiguous numeric/final naming such as:

```text
final_training_epoch       # if meaning n3
eventual_finalists         # if actually n3-derived
```

with semantics that distinguish final screen from full reference.

Qualification must derive reference finalists/winner from full `n` metrics.

Failure reason names must be semantic, e.g.:

```text
coarse_screen_drops_reference_finalist
short_screen_drops_reference_finalist
final_screen_drops_reference_finalist
```

Exact names may follow repository naming conventions, but no failure reason may encode fixed epoch numbers as current semantics.

### PERF-P2R design

PERF-P2R stage plans must carry both:

```text
target_epoch            # current stage boundary
schedule_horizon_epoch  # full n
```

or clearly equivalent names.

Required stage meanings:

```text
coarse       target=n1, schedule=n
short        target=n2, schedule=n
final_screen target=n3, schedule=n
production   target=n,  schedule=n
```

Do not populate production target from `fidelity_epochs[2]`.

The stage plan builder must destructure the three screen epochs semantically and separately obtain `n` from the training budget.

### Reporter/progress design

Training progress must distinguish:

1. currently authorized stage endpoint;
2. full schedule horizon.

Required semantics for screening:

```text
stage=coarse-screen; phase=epoch 1/1; schedule_horizon=30
stage=short-screen; phase=epoch 2/3; schedule_horizon=30
stage=final-screen; phase=epoch 7/10; schedule_horizon=30
```

For production:

```text
stage=production; phase=epoch 17/30
```

The exact formatting is delegated, but stage denominators must describe current authorized work and full horizon must be separately visible when useful.

Progress/ETA denominators for a bounded screening stage must not pretend all `n` epochs are currently authorized.

### Identity and cache semantics

The following must participate in identity/digest/invalidation wherever they materially define an artifact:

- fidelity tuple `(n1,n2,n3)` for target-size policy/state/evidence;
- full horizon `n` for TRAIN2 schedule/training/checkpoint identity;
- both tuple and `n` for artifacts that depend on both, such as screening execution plans and SIZE-FIDELITY qualification plans.

Changing `(n1,n2,n3)` must invalidate target-size evidence/plans that depend on screening boundaries.

Changing `n` must invalidate schedule/training/checkpoint evidence whose optimizer/LR trajectory depends on the full horizon.

A checkpoint created under `n=30` must not be accepted as the same trajectory under `n=40` merely because its current epoch equals a shared screening boundary.

## Implementation authority

### Frozen

The implementer must preserve all of the following exactly unless a redesign trigger fires:

- three configurable target-size screen epochs;
- default `(1,3,10)`;
- independent full training horizon `n`, default `30`;
- invariant `0 < n1 < n2 < n3 <= n`;
- no duplicate target-size-owned `n` configuration;
- all screens are checkpoints on the full `n` TRAIN2 trajectory;
- survivor continuation reuses checkpoints and does not restart;
- exact-boundary evidence only;
- final target-size freeze at `n3`;
- production training to `n`;
- semantic stage/API/state names on current surfaces;
- old schemas/configs either explicitly migrated with historical semantics or rejected closed;
- SIZE-FIDELITY1 reference endpoint is full `n`;
- PERF-P2R production horizon is full `n`;
- reporter separates current stage target from full schedule horizon;
- tuple and horizon changes invalidate dependent identities;
- current source/tests/config must be free of unquarantined fixed-epoch assumptions;
- full production GPU qualification remains deferred.

### Delegated

The implementer may choose:

- exact helper/function boundaries;
- whether semantic enum/state values are strings or existing enum patterns;
- exact schema version suffixes, provided every materially changed schema receives a new version and old schemas are not silently accepted as new;
- exact legacy-adapter module/file location;
- exact test file organization;
- exact CLI punctuation/field ordering;
- whether shared default constants are introduced, provided authority ownership remains unchanged.

### Explicitly forbidden implementation shortcuts

Do not:

- simply change `(3,10,30)` to `(1,3,10)` without decoupling `n3` from `n`;
- rename only printed strings while retaining numeric-stage current state/API ownership;
- keep `final_training_epochs` as a current target-size configuration field meaning `n3`;
- add `full_training_epochs` or equivalent under target-size configuration as a second authority for `n`;
- hard-code 30 in validation such as `planned_epochs == 30`;
- infer full horizon from `fidelity_epochs[-1]`;
- restart surviving candidates from epoch zero at later screens;
- rescale/retime LR schedule to each shortened screen;
- weaken SIZE-FIDELITY acceptance criteria merely to make epoch 1 pass;
- make legacy readers silently default missing values to the new tuple;
- globally ban the numeric literal `30`; legitimate unrelated/default-horizon uses are allowed;
- skip affected regressions because focused new tests pass;
- run data-heavy production qualification as a substitute for normal regression/integration.

### Reopen only on evidence

Reopen only the affected design surface if one of these occurs:

1. repository inspection proves the reviewed ownership path is no longer current and the proposed edit would create a second authority;
2. exact legacy artifact semantics cannot be reconstructed safely;
3. current restart/checkpoint machinery cannot preserve the same full-`n` trajectory across pauses without redesign;
4. SIZE-FIDELITY scientific evidence shows the default `(1,3,10)` fails existing required recall/equivalence criteria;
5. a nondefault integration case exposes another hidden epoch coupling that requires an additional schema/API redesign;
6. tests prove the full horizon is legitimately owned somewhere other than the existing TRAIN2 training budget.

If triggered, stop only dependent work, preserve unaffected completed gates, document the evidence, and reopen the minimum necessary design surface.

## Initially expected affected behavioral surface

At minimum inspect and expect changes in:

- `mdstats/training_data/target_size_study.py`;
- `mdstats/training_data/size_fidelity.py`;
- `mdstats/training_data/perf_p2r.py`;
- `mdstats/training_data/train2_policy.py` if shared defaults/validation wiring are needed;
- `mdstats/training_data/train2_runtime.py` only as needed to preserve boundary execution/reporting semantics; reuse existing `execution_epoch_limit` and continuation machinery rather than replacing it without evidence;
- `mdstats/training_data/protocol.py` for config/policy plumbing and optimizer/training-budget consistency;
- campaign configuration parser/writer/schema code;
- `campaign.toml.example`;
- campaign CLI/orchestration code including the actual training progress emitter, likely within `_campaign_cli_core.py` or its current replacement;
- persistence/restart/scheduler artifacts that serialize target-size stage/state names;
- package exports/public APIs exposing renamed fields/classes/constants;
- tests for all above modules;
- CLI snapshots/status payload tests;
- cache/reuse/digest tests;
- integration tests from campaign configuration through target-size freeze and production training planning.

This list is not exhaustive. Before implementation, run a local full-tree source/test/config search and extend the affected surface based on actual hits/callers.

## Task-specific acceptance

### Mandatory anti-hardcoding test configuration

At least one integration/regression test must use:

```text
fidelity_epochs = (2, 5, 12)
full horizon n = 40
```

This case is mandatory because it proves the implementation does not merely special-case the new defaults.

The `(2,5,12)/40` case must establish all of the following:

1. all initial candidates are authorized only through epoch 2 at coarse screen;
2. only coarse survivors continue from epoch 2 to epoch 5;
3. only short finalists continue from epoch 5 to epoch 12;
4. ranking accepts exact epoch-2, epoch-5, and epoch-12 checkpoints for their respective screens;
5. off-boundary checkpoints cannot satisfy those screen decisions;
6. every screening checkpoint identifies a full 40-epoch schedule/trajectory;
7. target size freezes after epoch-12 final screen;
8. production planning/training horizon is epoch 40, not 12;
9. screening reporter denominators show `/2`, `/5`, and `/12` for stage progress, not `/40`;
10. the full schedule horizon is separately recoverable/reported as 40 during screening;
11. production progress/planning uses `/40`;
12. changing `(2,5,12)` to another tuple changes target-size-dependent identities;
13. changing `n=40` to another horizon changes TRAIN2 schedule/training identities;
14. a checkpoint generated under the 40-epoch schedule is rejected where a different full-horizon schedule identity is required.

### Default behavior test configuration

Tests must also cover:

```text
fidelity_epochs = (1, 3, 10)
n = 30
```

and verify equivalent semantics.

### Validation edge cases

Add focused tests for at least:

```text
(0,3,10)      -> reject
(1,1,10)      -> reject
(3,1,10)      -> reject
(1,10,3)      -> reject
(1,3,31), n30 -> reject
(1,3,30), n30 -> accept
```

Also reject wrong tuple length, non-integer/invalid parsed values according to existing config validation conventions, and any negative/zero boundary.

### Continuation/restart acceptance

Tests must prove:

- survivor continuation starts from the previous checkpoint rather than epoch zero;
- resumed run preserves training-run/schedule ancestry;
- restart from persisted state at each of coarse, short, and final-screen boundaries reconstructs the same next authorized action;
- interruption during a segment does not permit ranking before the exact boundary checkpoint exists;
- eliminated candidates do not schedule later work;
- failed/invalid candidates follow existing failure semantics without causing a stage to use off-boundary or stale evidence.

### Persistence/schema acceptance

Every materially changed serialized current artifact must have a bumped schema/version.

For each old supported schema:

- add explicit legacy parser/adapter tests;
- verify reconstructed policy semantics are the historical old policy `(3,10,30)` with the historical full horizon if encoded/authoritatively recoverable;
- verify serialization back through current writers emits only the new current schema and semantic names, unless repository convention requires immutable legacy round-trip fixtures;
- verify missing/ambiguous required semantic data fails closed.

Do not accept old artifacts as current merely by ignoring unknown old fields.

### Configuration migration acceptance

New schema/current authoring:

```toml
[target_data.size_convergence]
fidelity_epochs = [1, 3, 10]
[training]
max_num_epochs = 30
```

Legacy config path:

- if an old schema explicitly contains `coarse_training_epochs=3`, `short_training_epochs=10`, `final_training_epochs=30`, map these to historical `fidelity_epochs=(3,10,30)`;
- derive full `n` from the historical canonical training setting, not from `final_training_epochs` merely because they were equal in the old default;
- if legacy data conflicts with canonical historical training horizon in a way that cannot be reconciled under old semantics, reject clearly rather than guessing;
- never map a missing old triple to the new default during legacy parsing.

Add parser tests for new config, valid old config, conflicting old config, incomplete old config, and current config accidentally mixing old and new keys. Mixed current/legacy keys must fail rather than choose one silently unless repository schema-dispatch already provides an unambiguous version boundary.

### SIZE-FIDELITY1 acceptance

Tests must construct evidence where epoch `n3` ranking differs from epoch `n` ranking and prove qualification uses epoch `n` as reference.

Example requirement:

- create synthetic valid metrics for a policy such as `(2,5,12), n=40` where the epoch-12 winner/finalists differ from epoch-40 winner/finalists;
- verify `reference_*`/equivalent results come from epoch 40;
- verify failure/recall outcomes reflect retention relative to epoch 40, not epoch 12.

Also test `n3 == n` such as `(1,3,30), n=30`:

- required checkpoint set contains epoch 30 only once physically;
- final-screen and reference semantics both operate correctly from that evidence.

### PERF-P2R acceptance

For `(2,5,12), n=40`, assert stage plans exactly equal:

```text
coarse:       target=2,  schedule_horizon=40
short:        target=5,  schedule_horizon=40
final_screen: target=12, schedule_horizon=40
production:   target=40, schedule_horizon=40
```

Cost tests must assert continuation accounting:

```text
screen_cost = q*2 + S*3 + F*7
```

for this case, not `q*2 + S*5 + F*12`.

### Reporter acceptance

Locate the actual user-facing training reporter through local source search before editing.

Add or update tests so a bounded screening run reports current stage endpoint separately from full horizon.

For `(2,5,12)/40`, acceptable semantic examples are:

```text
coarse:       epoch 1/2,  schedule_horizon=40
short:        epoch 4/5,  schedule_horizon=40
final_screen: epoch 8/12, schedule_horizon=40
production:   epoch 8/40
```

Do not assert only literal formatting if repository tests conventionally validate structured progress payloads; assert the semantic fields at the lowest stable interface.

### Identity/cache acceptance

Add tests proving:

- same inputs and same tuple/horizon produce stable digests;
- changing only `n1`, `n2`, or `n3` changes target-size policy/plan identities that depend on screening geometry;
- changing only `n` changes schedule/training identity and any cross-dependent screening execution-plan identity;
- old evidence is rejected when tuple or horizon identity does not match;
- cache/reuse does not reuse a final-screen result generated under a different fidelity tuple;
- checkpoint reuse does not cross full-horizon schedule identity.

### Legacy leakage acceptance

Before editing, run a full-tree search in source/tests/config/current docs for at least:

```text
3/10/30
3 -> 10 -> 30
(3, 10, 30)
epoch3_
epoch10_
epoch30_
awaiting_epoch_3
awaiting_epoch_10
awaiting_epoch_30
STAGE_FINAL
final_training_epochs
planned_epochs == 30
planned_epochs != 30
```

After implementation, every remaining hit must be manually classified.

Allowed remaining hits:

- explicit legacy adapters/parsers;
- legacy-schema constants;
- migration fixtures/tests that intentionally exercise historical artifacts;
- historical archived workplans/docs.

Not allowed on current runtime/API/config/current-schema paths:

- numeric-stage field/method names;
- fixed-fidelity assertions;
- fixed epoch diagnostics;
- third-screen-as-production terminology;
- hard-coded `planned_epochs == 30` target-size assumptions.

The string/literal `30` itself is not prohibited.

### Scientific default acceptance

Do not alter established SIZE-FIDELITY recall/equivalence thresholds solely to approve `(1,3,10)`.

If existing representative calibration evidence/tests demonstrate that epoch 1 cannot satisfy the current scientific qualification contract:

1. treat that as a redesign trigger for the default tuple only;
2. preserve the flexible architecture;
3. do not weaken scientific gates;
4. report the failing evidence and propose the smallest justified default adjustment, e.g. `(2,4,10)` or `(2,5,10)`, for review.

If no production-scale calibration data is available in the implementation environment, complete architecture/functionality tests and leave heavy empirical default qualification explicitly deferred rather than fabricating a pass.

### Performance acceptance

Use deterministic/synthetic accounting tests to prove no later stage schedules eliminated candidates and continuation cost uses epoch deltas.

Where lightweight runtime instrumentation/tests already exist, verify:

- no retraining from zero on continuation;
- no duplicate full-role inference caused solely by the new reference endpoint when an existing checkpoint/evaluation can be reused;
- no repeated checkpoint materialization for semantically identical `n3 == n` evidence.

Do not require full GPU timing qualification in this workplan.

Production qualification: deferred. Final production GPU/data-heavy qualification remains a later release activity. Functional correctness, affected regressions, integration, and lightweight performance/identity checks are required now.

## Implementation sequence

### C0 — Characterization and complete leakage inventory

Actions:

1. Work from the latest branch head; record the exact starting commit.
2. Run local full-tree searches for the legacy patterns listed above because remote code search may be incomplete.
3. Identify all callers/serializers/tests/config paths for `TargetSizeStudyPolicy`, target-size stage state, SIZE-FIDELITY1, PERF-P2R, TRAIN2 execution limits, and progress emission.
4. Locate the actual user-facing `gradient-update`/training progress emitter and its structured source data.
5. Run the existing focused target-size/SIZE-FIDELITY/PERF-P2R/config/restart test subsets before changes to establish characterization.
6. Add characterization tests first where current behavior is important for migration/restart and currently untested.

Gate acceptance:

- affected surface has been expanded based on actual repository hits;
- pre-change focused regressions either pass or existing failures are documented and clearly unrelated;
- exact progress emitter and persistence paths are known;
- no implementation begins while a major unlocated serializer/state authority remains unknown.

### C1 — Introduce canonical flexible policy/configuration

Actions:

1. Change `TargetSizeStudyPolicy.fidelity_epochs` default to `(1,3,10)` and remove rejection of non-`(3,10,30)` tuples.
2. Validate exactly three strictly increasing positive integer epochs.
3. Rename current policy fields from epoch-number names to semantic names, especially survivor/finalist counts.
4. Add cross-policy validation `n3 <= TrainingBudgetPolicy.planned_epochs` at the existing assembly/config boundary where both authorities are available.
5. Preserve existing `MaceOptimizerPolicy.max_num_epochs` vs `TrainingBudgetPolicy.planned_epochs` consistency enforcement.
6. Add `fidelity_epochs` to current campaign config parser/writer/schema.
7. Remove old three target-size epoch keys from current-schema authoring.
8. Implement explicit legacy config schema dispatch/adapter for old keys; do not use heuristic key guessing if an existing schema/version field is available.
9. Ensure target-size policy digest includes the tuple.

Focused tests:

- valid/invalid tuple unit tests;
- default `(1,3,10)` test;
- `(2,5,12)` test;
- cross-policy `n3 <= n` tests;
- config new-schema and legacy migration tests;
- mixed-key rejection tests.

Affected regression required before C2:

- target-size policy tests;
- campaign config/protocol parsing tests;
- training budget/optimizer consistency tests;
- serialization tests touched by policy rename.

Gate acceptance:

- current config has one tuple authority plus one full-horizon authority;
- no current parser derives `n` from `n3`;
- regressions pass.

### C2 — Refactor target-size state machine and current schemas to semantic stages

Actions:

1. Replace current numeric state names with semantic state names.
2. Replace numeric stage constants/mappings with semantic stage identifiers.
3. Derive each stage boundary from `policy.fidelity_epochs`.
4. Rename public/current fields and methods from `epoch3_*`, `epoch10_*`, `epoch30_*` to `coarse_*`, `short_*`, `final_screen_*` equivalents.
5. Update current serializers/writers to semantic keys and bump materially changed schemas.
6. Implement legacy artifact adapters for old schemas where exact semantics are recoverable.
7. Update ranking guards so each stage accepts only evidence whose checkpoint epoch equals the configured boundary and whose full schedule/training identity matches canonical `n`.
8. Preserve existing selection ordering/equivalence logic unless required to remove epoch coupling.

Focused tests:

- state transitions under `(1,3,10)` and `(2,5,12)`;
- off-boundary rejection;
- semantic serializer round-trip;
- legacy artifact migration/fail-closed behavior.

Affected regression required before C3:

- all target-size-study tests;
- restart/persistence tests touching target-size state;
- callers that consume serialized target-size evidence;
- any package export/API tests affected by renames.

Gate acceptance:

- no current runtime transition depends on literal epochs 3/10/30;
- current schemas contain semantic stage keys;
- legacy support is quarantined;
- regressions pass.

### C3 — Preserve TRAIN2 continuation and full-schedule identity

Actions:

1. Reuse existing `Train2RuntimePlan.execution_epoch_limit` and pause/continuation mechanisms where they already satisfy the frozen semantics.
2. Wire coarse/short/final-screen runtime plans so execution limits are `n1`, `n2`, `n3` while frozen training budget remains `n`.
3. Verify survivor continuation loads the previous authenticated checkpoint and continues the same run/schedule identity.
4. Remove any code path that creates a shortened independent schedule for a screening stage.
5. Ensure eliminated candidates do not receive later runtime plans.
6. Ensure restart reconstruction after each boundary produces the correct next segment.

Focused tests:

- `(2,5,12)/40` continuation ancestry;
- no-restart-from-zero assertions;
- pause/continue at all three boundaries;
- eliminated-candidate no-later-work;
- schedule digest changes with `n` but not merely current execution limit.

Affected regression required before C4:

- TRAIN2 runtime/pause/restart tests;
- target-size orchestration tests;
- checkpoint identity/reuse tests.

Gate acceptance:

- screening boundaries are execution limits, not schedule horizons;
- continuation behavior is proven;
- regressions pass.

### C4 — Redesign SIZE-FIDELITY1 around independent full-reference horizon

Actions:

1. Change SIZE-FIDELITY1 module terminology/schema versions to remove fixed `3/10/30` authority wording.
2. Update execution plan to carry/derive `short_screen_epoch=n2`, `final_screen_epoch=n3`, and `reference_training_epoch=n` distinctly.
3. Build `required_checkpoint_epochs` as the unique union of coarse calibration candidates, `n2`, `n3`, and `n`.
4. Validate all coarse calibration candidates precede `n2`.
5. Derive reference finalist/winner order exclusively from full-role metrics at epoch `n`.
6. Evaluate coarse/short/final-screen retention against that reference order according to existing scientific criteria.
7. Rename assessment/report fields from `eventual_*` or numeric meanings to `reference_*` / semantic equivalents.
8. Replace numeric failure reason codes with semantic stage/reference reason codes.
9. Handle `n3 == n` without duplicate physical checkpoint requirements.
10. Bump all materially changed SIZE-FIDELITY schemas and add legacy behavior only where exact old semantics are safe.

Focused tests:

- synthetic `(2,5,12)/40` case with epoch-12 vs epoch-40 disagreement;
- `n3 == n` dedup case;
- reference horizon identity mismatch rejection;
- schema migration/round-trip tests.

Affected regression required before C5:

- complete SIZE-FIDELITY1 test suite;
- target-size policy integration tests that invoke calibration;
- serialization/digest tests for qualification artifacts.

Gate acceptance:

- full `n`, not `n3`, is the scientific reference;
- no fixed epoch diagnostic remains on current paths;
- regressions pass.

### C5 — Decouple PERF-P2R screening endpoint from production horizon

Actions:

1. Rename `final` stage to `final_screen` where it means third target-size screen.
2. Add explicit full schedule/training horizon to stage-plan data.
3. Build stage plans with `target_epoch={n1,n2,n3,n}` for coarse/short/final_screen/production respectively.
4. Ensure production is `0 -> n`, not `0 -> n3`.
5. Rewrite cost accounting to use incremental continuation deltas.
6. Rename config/grid fields that currently use `short_training_epochs`/`final_training_epochs` when they refer to screen endpoints.
7. Bump affected PERF-P2R schemas and migrate/reject old artifacts explicitly.

Focused tests:

- exact `(2,5,12)/40` stage-plan assertions;
- incremental cost formula assertions;
- production target=40 assertion;
- old schema migration/fail-closed tests.

Affected regression required before C6:

- complete PERF-P2R test suite;
- target-size orchestration/planning tests consuming PERF-P2R outputs;
- persistence/digest tests.

Gate acceptance:

- no code path infers production horizon from `fidelity_epochs[2]`;
- regressions pass.

### C6 — Update campaign orchestration, progress reporting, CLI/status surfaces

Actions:

1. Thread semantic stage and configured stage target through campaign orchestration.
2. Update user-facing progress emitter so screening phase denominator is the current stage endpoint.
3. Expose full schedule horizon separately in structured progress/status data where screening can otherwise be ambiguous.
4. Update JSON/status snapshots, CLI messages, sidecar/status persistence, exceptions, and tests that encode numeric stage names or fixed epochs.
5. Ensure final-screen selection log prints the selected/frozen target size after the configured `n3` decision.
6. Ensure production messages describe training to full `n`.

Focused tests:

- structured progress tests for `(2,5,12)/40`;
- CLI snapshot/status tests;
- selected target-size freeze message test;
- restart/status serialization test if progress state persists.

Affected regression required before C7:

- campaign CLI tests;
- progress/status tests;
- target-size campaign orchestration tests;
- any integration tests that parse emitted status.

Gate acceptance:

- screening progress cannot be mistaken for an authorized 40-epoch/30-epoch run;
- full schedule horizon remains observable;
- regressions pass.

### C7 — Identity, cache, reuse, and compatibility closure

Actions:

1. Audit every digest/cache/reuse key affected by tuple/horizon semantics.
2. Make tuple changes invalidate target-size-dependent artifacts.
3. Make horizon changes invalidate TRAIN2 schedule/training/checkpoint artifacts and cross-dependent plans.
4. Ensure checkpoint reuse validates full schedule identity, not only epoch and target size.
5. Ensure old caches/artifacts cannot be reused under new default semantics unless explicitly migrated with preserved historical policy identity.
6. Audit package exports and remove current numeric-stage API aliases unless compatibility policy independently requires a deprecated adapter. If aliases are retained, quarantine/deprecate them and prevent new writers from emitting them.

Focused tests:

- digest perturbation tests for each boundary and for `n`;
- stale cache rejection;
- cross-horizon checkpoint rejection;
- legacy/current identity separation.

Affected regression required before C8:

- cache/reuse tests;
- serialization tests;
- public API/export tests;
- all target-size/Train2 tests affected by identity changes.

Gate acceptance:

- no stale evidence can masquerade as valid under a changed tuple/horizon;
- regressions pass.

### C8 — Mandatory end-to-end nondefault integration

Actions:

Create/run an integration test through the real product boundaries using:

```text
fidelity=(2,5,12)
n=40
```

It must cover configuration -> policy assembly -> target-size stage planning -> checkpoint/evidence admission -> survivor transitions -> final-screen freeze -> production plan/horizon -> progress semantics.

Use lightweight/synthetic training/evidence fixtures where needed; the goal is functional integration, not full GPU production qualification.

Required assertions are the 14 anti-hardcoding requirements listed in Task-specific acceptance.

Also run a default `(1,3,10)/30` integration case.

Gate acceptance:

- both nondefault and default end-to-end paths pass;
- no hidden fixed-epoch dependency is observed.

### C9 — Scientific default check without weakening gates

Actions:

1. Run existing lightweight/available SIZE-FIDELITY calibration tests/evidence applicable to the proposed `(1,3,10)/30` default.
2. Do not change scientific recall/equivalence thresholds to force a pass.
3. If representative evidence is unavailable, record that full empirical default qualification is deferred.
4. If representative evidence exists and epoch 1 fails established criteria, trigger a narrow redesign of the default tuple only; preserve the flexible implementation.

Gate acceptance:

- either current evidence supports the default under existing criteria, or the lack/failure of empirical evidence is explicitly reported without compromising architecture correctness.

### C10 — Final affected-surface re-derivation and regression/integration closure

Actions:

1. Re-derive the affected behavioral surface from the assembled diff rather than relying only on the initial list.
2. Run all focused new tests.
3. Run all affected module regressions for target-size, SIZE-FIDELITY1, PERF-P2R, TRAIN2 runtime/policy, config/protocol, campaign CLI/progress, persistence/restart, cache/reuse, and package APIs.
4. Run repository-required checks for the touched Python surface: formatting/lint/type/static checks where configured, unit regressions, and relevant integration tests.
5. If impact cannot be bounded confidently because shared protocol/orchestration code changed broadly, run the broader available test suite.
6. Re-run the full-tree legacy leakage search and manually classify every remaining hit.
7. Verify no current documentation/config example was left inconsistent if the documentation workplan has already landed on the branch.

Final acceptance:

- all stage-local accepted regressions remain valid or have been rerun where later changes invalidated them;
- final affected-surface regression passes;
- mandatory `(2,5,12)/40` and default `(1,3,10)/30` integrations pass;
- current runtime/API/config/schema surfaces are legacy-leak-free;
- remaining old terms exist only in explicit legacy/history locations;
- no unresolved correctness/scientific/persistence issue remains;
- heavy production GPU qualification remains explicitly deferred.

## Required implementation checklist

The implementer must not declare completion until each item below is explicitly verified:

- [ ] `TargetSizeStudyPolicy` accepts configurable three-epoch tuples.
- [ ] Default fidelity tuple is `(1,3,10)` unless C9 fires the scientific-default redesign trigger.
- [ ] `n3 <= n` is validated at the proper cross-policy assembly boundary.
- [ ] Current target-size state/API names are semantic, not epoch-number-specific.
- [ ] Current serializers use bumped semantic schemas.
- [ ] Legacy artifacts/configs are explicitly migrated or rejected closed.
- [ ] Legacy configs preserve historical `(3,10,30)` semantics rather than inheriting new defaults.
- [ ] TRAIN2 screening uses execution limits while preserving full schedule `n`.
- [ ] Survivor training resumes checkpoints; no screening retrain from zero.
- [ ] Exact-boundary evidence validation uses configured boundaries.
- [ ] SIZE-FIDELITY1 full reference is epoch `n`.
- [ ] `n3 == n` works without duplicate physical checkpoint requirements.
- [ ] PERF-P2R has separate `target_epoch` and full schedule horizon.
- [ ] PERF-P2R production target is `n`.
- [ ] PERF-P2R screening cost uses incremental epoch deltas.
- [ ] Reporter distinguishes current stage endpoint from full schedule horizon.
- [ ] Target-size selection/freeze message prints selected size after final screen.
- [ ] Tuple changes invalidate dependent target-size identities.
- [ ] Horizon changes invalidate schedule/training/checkpoint identities.
- [ ] `(2,5,12)/40` integration passes all anti-hardcoding assertions.
- [ ] `(1,3,10)/30` default integration passes.
- [ ] Invalid tuple/order/boundary tests pass.
- [ ] Restart at each screen boundary is regression-tested.
- [ ] Stale cache/cross-horizon reuse tests pass.
- [ ] Final legacy leakage scan has no unquarantined current-path hits.
- [ ] Final affected-surface regression and integration pass.
- [ ] No full production GPU qualification was incorrectly substituted for functional acceptance.

## Risks / redesign triggers

### Scientific default risk

Epoch 1 may be too noisy to preserve full-horizon finalist/winner recall under existing SIZE-FIDELITY criteria. This does not invalidate configurable architecture. It may invalidate only the proposed default. Do not weaken the qualification rule to preserve the default.

### Legacy ambiguity risk

Old persisted artifacts may omit enough context that full horizon or old stage semantics cannot be reconstructed. Fail closed rather than guessing. Supporting fewer ambiguous legacy artifacts is preferable to silently corrupting scientific identity.

### Hidden reporter/runtime coupling

The actual training reporter resides in a large campaign orchestration surface and may couple denominator/ETA computation to full planned epochs. Fix the reporting contract without changing TRAIN2 scheduling unless evidence shows the scheduling mechanism itself is wrong.

### Shared-schema blast radius

Renaming current state/API fields can affect restart/cache/status consumers beyond the initially reviewed modules. This is why C0 search and C10 final affected-surface re-derivation are mandatory.

### Performance regression risk

A naive implementation may issue repeated inference/materialization at `n3` and `n`, or restart survivors, defeating the screening savings. Preserve prefix reuse and reuse identical checkpoint/evaluation evidence when semantic identities match.
