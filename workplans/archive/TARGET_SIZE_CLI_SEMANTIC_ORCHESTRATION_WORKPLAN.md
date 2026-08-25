---
kind: implementation-workplan
workplan_id: TARGET-SIZE-CLI1
protocol_version: 5.2.0
---

# TARGET-SIZE-CLI1 - Semantic CLI and outer-loop orchestration refactor

**Status:** implementation complete - C1-C11 locally qualified against the effective baseline; target-host campaign rerun remains external qualification
**Scope:** TRAIN2 campaign CLI/orchestration boundary only
**Effective source baseline:** `mdstats-feat-target-size-v5-redesign (11).zip`, SHA-256 `1279f179adaaca66d757705cd59c16f9c197a40228deafc1b3a8d9d206dd50e1`, plus `DATA78_CLOSEOUT_C8_C13_latest11.patch`, SHA-256 `8c2d8e30c1d662faccf1e9c5ee6dd7675b609ebdb1ba6e2c82d36086326cadb2`
**Primary implementation owner:** `mdstats/training_data/_campaign_cli_core.py`

## Objective

Refactor the public TRAIN2 campaign interface so every command has one stable scientific/operational meaning, while preserving the existing target-size, TRAIN2, EVAL2, DATA7/DATA8, CV, checkpoint, persistence, and restart machinery.

The current core science is already correct:

- target-size screening uses the exact prescribed 3/10/30 epoch endpoints;
- epoch is a controlled variable during target-size selection;
- candidate DATA8 artifacts survive the full 3 -> 10 -> 30 continuation funnel;
- held-out CV is blocked until `selected_target_size` is frozen;
- post-selection EVAL2 may select an earlier admissible checkpoint from a trajectory whose ceiling is 30 epochs.

The defect is the outer interface: the static `prepare -> preflight -> train -> evaluate` vocabulary exposes hidden TARGET-SIZE-V5 state and gives the same public verbs materially different meanings before and after target-size selection.

## Frozen semantic model

### Target-size study

For target size `N` and fidelity boundary `e_k in {3, 10, 30}`, the study compares only

```text
S(N, e_k)
```

at the exact common boundary. It must not substitute an earlier better checkpoint. Epoch is controlled so the study isolates the effect of target data size.

The complete public operation is:

```text
select-target-size
    train exact surviving population to epoch 3
    evaluate exact epoch-3 endpoints
    halve
    continue survivors exactly to epoch 10
    evaluate exact epoch-10 endpoints
    halve
    continue finalists exactly to epoch 30
    evaluate exact epoch-30 endpoints
    freeze selected_target_size
```

### Production training/evaluation

After `selected_target_size = N*` is frozen, target size is fixed and checkpoint epoch becomes selectable. Production EVAL2 may therefore choose

```text
e* = best admissible checkpoint among the frozen production trajectory
```

including an epoch earlier than 30.

These are distinct statistical operations and must have distinct public owners.

## Public TRAIN2 lifecycle

```text
init
  -> doctor
  -> prepare
  -> preflight
  -> select-target-size
  -> materialize
  -> preflight
  -> train
  -> evaluate
  -> verify
```

Stable command contracts:

| Command | Stable responsibility |
| --- | --- |
| `prepare` | Establish initial DATA2-DATA9A scientific preparation and the target-size screening candidate workload. |
| `preflight` | Operationally verify the currently materialized DATA8 workload and run the bounded one-epoch smoke. It never creates scientific selection evidence. |
| `select-target-size` | Own the complete restartable 3/10/30 controlled-fidelity target-size experiment and freeze `N*`. |
| `materialize` | Given frozen `N*`, realize the selected-size final-development and canonical/per-seed CV DATA7/DATA8 production workload. |
| `train` | Train/resume the frozen selected-size production/CV workload only. |
| `evaluate` | Evaluate completed selected-size production trajectories and select admissible checkpoint(s); earlier epochs may win. |
| `verify` | Run the existing physical/deployment/locked verification path without changing target-size authority. |

Historical non-TRAIN2 campaigns retain their existing lifecycle and public behavior.

## Final-review findings incorporated into this plan

### F1 - Do not create a second persistent lifecycle authority

Adding `select-target-size` and `materialize` as new independently persisted stage states would duplicate authority already owned by `TargetSizeStudyPlan`, DATA8 materialization identities, `preflight_smoke.data8_matrix_digest`, training execution records, and EVAL2 records.

**Decision:** new public lifecycle state is a transient projection of existing authorities. Existing `StageState` records remain execution/restart receipts and backward-compatibility support, not the semantic source of truth for the new TRAIN2 lifecycle.

### F2 - Public handlers must not recursively call semantically guarded public handlers

Once public `train` and `evaluate` are restricted to post-selection production semantics, `select-target-size` cannot implement its loop by calling those public handlers.

**Decision:** factor narrow private execution engines from the current handlers. Public handlers become semantic guards around those engines. `select-target-size` calls the private screening engines directly.

### F3 - Production commands must validate current workload shape, not merely `selected_target_size`

After target-size selection, stale candidate DATA8 and its earlier preflight receipt can still exist. A guard that checks only `study.outcome == selected` is insufficient.

**Decision:** production `train` and `evaluate` require all of:

- frozen selected target size;
- current DATA8 matrix is the selected-size production/CV matrix, not screening candidates;
- production DATA8 identities match the current selected-size authority;
- `preflight_smoke.data8_matrix_digest` matches that exact production matrix.

### F4 - Screening preflight must remain valid across all 3/10/30 boundaries

The survivor set changes at epoch 3 and epoch 10, but the candidate DATA8 matrix intentionally does not. Re-preflighting after each halving would add cost without changing the validated execution artifacts.

**Decision:** `select-target-size` requires one preflight bound to the full candidate DATA8 matrix and preserves it throughout the funnel. Any DATA8 matrix change invalidates that authorization and stops the operation fail-closed.

### F5 - `prepare` restart reuse is lifecycle-state-sensitive

The existing completed-prepare fast path compares current DATA8 variant IDs against generic `_variant_specs(cfg)`. The new split needs idempotent reuse for both screening preparation and selected production materialization without inferring meaning from the old `prepare` stage bit.

**Decision:** make completed preparation/materialization reuse validate the exact expected matrix for the current target-size state via the existing target-size materialization authority, rather than generic configured variants alone.

### F6 - `status` needs two distinct preflight steps even though both invoke the same command

A command-name-only pipeline cannot represent:

```text
screening preflight
...
production preflight
```

without ambiguity.

**Decision:** transient lifecycle steps have stable semantic IDs distinct from command names, e.g. `screening_preflight` and `production_preflight`, both mapping to public command `preflight`.

### F7 - Scientific terminal target-size outcomes need a semantic terminal state

`insufficient_qualified_sizes`, `nonconverged_at_fixed_ceiling`, and `insufficient_comparable_candidates` are completed scientific outcomes, not software exceptions and not successful target-size selections.

**Decision:** the derived lifecycle displays a terminal/stopped target-size state and exposes no production next step. Do not mutate or synthesize a size. Preserve current scientific evidence and fail closed.

### F8 - Existing source-string tests are too weak for the interface refactor

Current target-size topology tests use `inspect.getsource()` to prove orchestration properties. That already failed to protect earlier real campaign bridges.

**Decision:** replace orchestration source-string assertions with behavioral tests through real command/private-engine seams. Retain source inspection only where it is genuinely checking absence of a retired symbol and cannot be expressed more directly.

### F9 - Historical campaign compatibility is an explicit boundary

`extend-seed` and historical adaptive/MLCV campaigns legitimately use the current public `train`/`evaluate` semantics.

**Decision:** new semantic guards apply only when `[training].policy_generation = "train2"`. Historical configurations continue through the existing lifecycle. `select-target-size` and `materialize` reject historical campaigns with a concise explanation rather than trying to reinterpret them.

## Non-goals

- no change to `TargetSizeStudyPolicy`, survivor rules, candidate ranking, or fixed 3/10/30 schedule;
- no change to exact REPAIR2 target membership or fixed comparison cohort;
- no change to TRAIN2 continuation, optimizer/RNG/schedule lineage, or 30-epoch horizon;
- no change to EVAL2 target/replay metrics, admissibility, shortlist/rescue, or checkpoint-selection mathematics;
- no change to DATA7/DATA8 scientific schemas or materialization identities except outer restart/reuse checks required to distinguish screening versus production matrices;
- no new persistent campaign-state schema solely for CLI presentation;
- no change to CV partition authority;
- no scheduler/performance redesign;
- no aliases that preserve the ambiguous TRAIN2 `train`/`evaluate` screening behavior.

## Staged implementation plan

### C1 - Factor private execution engines without changing behavior

**Goal:** separate execution mechanisms from public command semantics before changing the interface.

Refactor the current bodies into narrow private owners, preserving existing algorithms and record formats. The exact names are implementation-local, but the responsibilities should be equivalent to:

```text
_execute_prepare_for_current_authority(...)
_execute_preflight_current_matrix(...)
_execute_train_current_train2_boundary(...)
_advance_target_size_endpoint_once(...)
_execute_production_eval2(...)
```

Requirements:

- do not duplicate current train/evaluate algorithms;
- target-size endpoint evidence remains owned by `_eval2_target_size_endpoint_evidence()`;
- production checkpoint evaluation remains owned by `_eval2_run_record_for_completed_train2_run()`;
- public wrappers contain validation, dispatch, and user-facing handoff only;
- historical command paths continue to call their existing engines.

**Acceptance:** focused tests show byte/content identities and target-size state transitions are unchanged when the private engines are invoked directly.

### C2 - Add explicit public semantic guards

**Goal:** make ambiguous commands impossible for TRAIN2.

For TRAIN2:

- `prepare` is valid only before target-size selection; if already selected, instruct `materialize`;
- `materialize` requires `OUTCOME_SELECTED`; before selection, instruct `select-target-size`;
- `train` requires selected-size production materialization plus matching production preflight;
- `evaluate` requires selected-size production training and cannot advance target-size state;
- `select-target-size` requires active target-size state and the screening candidate workload/preflight.

Historical campaigns retain current behavior.

**Acceptance:** no TRAIN2 public `train` or `evaluate` invocation can create target-size halving evidence.

### C3 - Implement `select-target-size` as one restartable outer operation

**Goal:** make the complete controlled-fidelity experiment one user-visible command.

The command loops over the existing target-size state:

```text
while outcome in {awaiting_epoch_3, awaiting_epoch_10, awaiting_epoch_30}:
    validate screening matrix + preflight authorization
    run/resume exact current TRAIN2 fidelity boundary
    reduce exact endpoint evidence once
    reload and validate TargetSizeStudyPlan
```

Required invariants:

- epoch-3 evidence uses only exact epoch-3 checkpoints;
- epoch-10 evidence uses only exact epoch-10 checkpoints continued from authenticated epoch-3 parents;
- epoch-30 evidence uses only exact epoch-30 checkpoints continued from authenticated epoch-10 parents;
- no `best earlier checkpoint` substitution is reachable;
- no prepare/preflight occurs between fidelity boundaries;
- no CV fold is trained/evaluated before selection;
- screening population always uses the prescribed paired optimizer seeds;
- partial CLI filters (`--seed`, `--selection-size`, `--run-id`, `--max-runs`) are not exposed for this scientific operation;
- interruption preserves existing TRAIN2 execution and target-size records; rerunning resumes from the exact current boundary;
- already-selected invocation is idempotent and reports frozen `N*` without mutation;
- scientific terminal-without-selection outcomes stop cleanly with frozen evidence and no next production operation.

**Acceptance:** one invocation from `awaiting_epoch_3` reaches `selected` on a complete successful fixture; restart fixtures from epoch 10 and epoch 30 perform only remaining work.

### C4 - Add `materialize` as the selected-production realization owner

**Goal:** remove the state-dependent second meaning of public `prepare`.

`materialize` reuses the current preparation/materialization machinery but only after `selected_target_size` is frozen.

It must realize exactly:

- selected final-development domain(s);
- selected-size canonical CV domains;
- configured per-seed CV partition authority when explicitly requested by the existing method semantics;
- existing DATA9A production gate.

It must not:

- rerun target-size selection;
- create additional target sizes;
- alter `selected_target_size`;
- treat screening candidate DATA8 as production DATA8.

Update completed-reuse checks so the expected matrix is derived from the current target-size state and exact materialization authorities.

**Acceptance:** `materialize` is idempotent; stale screening DATA8 cannot satisfy production realization; unchanged selected production materialization is reused without unnecessary DATA2-DATA6 recomputation.

### C5 - Preserve one stable `preflight` meaning across two workload contexts

**Goal:** keep preflight operational and selection-inert.

The command remains one implementation and one semantic contract:

> verify the exact currently materialized DATA8 matrix and run the bounded real-MACE smoke.

Presentation may label the workload as `target-size screening` or `selected production/CV`, but no scientific rule changes.

The existing matrix binding remains authoritative:

```text
preflight_smoke.data8_matrix_digest == current DATA8 matrix digest
```

Add/retain fail-closed checks so:

- screening preflight remains valid across 3/10/30 while candidate DATA8 is unchanged;
- selected production materialization invalidates screening preflight automatically;
- production training requires the production-bound preflight receipt.

**Acceptance:** no second preflight is required during the target-size funnel; one is required after `materialize` changes the matrix.

### C6 - Restrict public production `train` and `evaluate`

**Goal:** restore stable meanings to the generic verbs.

`train` for TRAIN2 means only selected-size production/CV training.

`evaluate` for TRAIN2 means only selected-size production checkpoint evaluation. It may select an earlier admissible epoch according to the existing checkpoint-selection policy.

Add a direct semantic regression fixture where:

```text
epoch 17 production checkpoint > epoch 30 production checkpoint
```

under the frozen selection metric. Required result:

- target-size final comparison still consumes epoch 30 exactly;
- production EVAL2 may select epoch 17.

Production `evaluate` must not modify `TargetSizeStudyPlan` or selected-size authority.

**Acceptance:** the controlled-variable versus optimized-variable distinction is executable, not documentation-only.

### C7 - Replace static TRAIN2 pipeline with one derived lifecycle projection

**Goal:** make `status` accurately describe scientific responsibility without introducing persistent duplicate state.

Retain/rename the current static pipeline for historical campaigns. For TRAIN2 add one transient lifecycle resolver, e.g. conceptually:

```text
_current_public_lifecycle(cfg, paths, store)
_next_public_operation(...)
```

The resolver reads existing authorities and returns semantic steps such as:

```text
doctor
initial_prepare
screening_preflight
target_size_selection
production_materialization
production_preflight
production_train
production_evaluate
verify
```

Each step includes its public command separately, allowing both preflight steps to map to `preflight`.

The resolver must derive state from, as applicable:

- config policy generation;
- existing stage/config receipts;
- verified `TargetSizeStudyPlan`;
- expected/current DATA8 matrix identities;
- `preflight_smoke.data8_matrix_digest`;
- TRAIN2 execution records/runtime summaries;
- EVAL2 production records;
- verification/freeze authority.

It must not write scientific state.

For an active study, `status` should expose internal progress without changing the command surface, e.g.:

```text
[RUN ] select-target-size
       epoch 3: complete
       epoch 10: current
       epoch 30: pending
```

For a scientific terminal-without-selection result, show a terminal/stopped state and no production next command.

**Acceptance:** `status` never tells a TRAIN2 user to invoke screening `train` or screening `evaluate` directly.

### C8 - Make `advance` consume the same lifecycle resolver

**Goal:** eliminate duplicate next-action logic.

`advance` must call the exact public operation returned by `_next_public_operation()`.

Expected behavior:

- before screening preparation -> `prepare`;
- after screening preparation -> `preflight`;
- during target-size study -> `select-target-size`;
- after `N*` freezes -> `materialize`;
- after production materialization -> `preflight`;
- then `train -> evaluate -> verify`.

No separate `advance` state machine may be maintained.

**Acceptance:** every tested state reports the same next operation in `status` and executes that operation in `advance`.

### C9 - Update CLI/help/guide terminology only at the outer boundary

Update parser help, `GUIDE_TEXT`, stage headers, and handoff messages so they match the stable definitions.

Required user-facing distinctions:

- `select-target-size`: controlled-fidelity exact endpoint comparison;
- `materialize`: selected production/CV realization;
- `train`: production/CV training only for TRAIN2;
- `evaluate`: production checkpoint evaluation/selection only for TRAIN2;
- preflight remains an execution smoke, never a selection stage.

At final target-size selection print at minimum:

```text
Target data size selected and frozen: n=<N>
Next: `materialize`.
```

Do not rename persistent TRAIN2/EVAL2 scientific schemas merely for CLI aesthetics.

### C10 - Replace shallow orchestration tests with behavioral coverage

Required focused/integration matrix:

1. parser exposes `select-target-size` and `materialize`;
2. new commands reject historical campaign generations cleanly;
3. TRAIN2 `prepare` rejects post-selection use;
4. `materialize` rejects pre-selection use;
5. TRAIN2 public `train/evaluate` reject active target-size study states;
6. screening preflight matrix remains authorized across 3 -> 10 -> 30;
7. changed DATA8 matrix invalidates preflight;
8. `select-target-size` executes 3 -> 10 -> 30 -> selected in one invocation;
9. restart at epoch 10 skips epoch-3 work;
10. restart at epoch 30 skips epoch-3/10 work;
11. partial current-boundary training resumes without duplicate completed execution;
12. exact endpoint-only target-size evidence is enforced;
13. target-size final comparison uses epoch 30 even if an earlier checkpoint scores better;
14. production EVAL2 may select that earlier better checkpoint;
15. production evaluation cannot mutate target-size authority;
16. `materialize` creates only selected-size final/CV topology;
17. stale screening matrix cannot satisfy production train/evaluate;
18. production preflight authorizes the selected production matrix;
19. `status` and `advance` agree in every lifecycle state;
20. scientific terminal-without-selection state exposes no production next step;
21. existing `extend-seed` historical MLCV behavior remains green;
22. existing DATA7/DATA8 digest, restart, cache, CV, TRAIN2 continuation, and EVAL2 tests remain green.

Add one fast real outer-loop integration test:

```text
prepare-complete screening state
 -> preflight-complete screening matrix
 -> select-target-size
 -> selected
 -> materialize
 -> production preflight
 -> production train
 -> production evaluate
```

Stub only heavyweight external MACE execution where necessary. Do not reconstruct target-size or production-evaluation logic in the test.

### C11 - Documentation and closeout

Update only durable documentation whose current semantic contract changes:

- `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
- assembled architecture Markdown/PDF and provenance manifests required by repository policy;
- CLI guide/help text.

The documentation must explicitly state:

```text
target-size study: epoch is controlled, exact 3/10/30 endpoints only
production evaluation: epoch is selectable, earlier admissible checkpoint may win
```

Final qualification:

- focused CLI/lifecycle tests;
- target-size topology/study tests;
- TRAIN2/EVAL2 regression groups;
- DATA7/DATA8 production materialization regression groups;
- campaign CLI historical compatibility tests;
- `compileall`;
- `git diff --check`;
- derived PDF regeneration/visual verification where permanent Markdown changed;
- patch apply check against the exact effective source baseline.

## Implementation boundaries

Expected primary changes:

- `mdstats/training_data/_campaign_cli_core.py`;
- `tests/test_mlff_campaign_cli.py`;
- `tests/test_mlff_target_size_v5_topology.py`;
- one focused TRAIN2/EVAL2 integration test file if existing files cannot express the behavioral distinction cleanly;
- the two architecture-manual sections listed above and their required derived publication.

Core files should remain unchanged unless implementation reveals a genuine owner-level blocker:

- `mdstats/training_data/target_size_study.py`;
- `mdstats/training_data/eval2.py`;
- TRAIN2 runtime/schedule implementation;
- `perf_p2r.py` target-size scientific policy;
- DATA7 selection/fitted-core algorithms;
- DATA8 scientific materialization schemas;
- REPAIR2/MVQUAL2;
- CV partition authority.

Any required modification to those core owners is a redesign trigger and must be justified against this workplan rather than silently folded into the CLI refactor.

## Implementation closeout evidence

Implementation remained within the frozen boundary: no changes were required to `target_size_study.py`, `eval2.py`, TRAIN2 runtime/schedule ownership, PERF-P2R target-size policy, DATA7/DATA8 scientific algorithms, REPAIR2/MVQUAL2, or CV partition authority.

Accepted outer-boundary behavior:

- `select-target-size` is the sole TRAIN2 public owner of the restartable 3 -> 10 -> 30 controlled-fidelity study;
- screening DATA8 materialization remains the immutable full qualified matrix while training projects only the currently authorized survivor subset;
- exact epoch 3/10/30 endpoint evidence remains mandatory for target-size reduction;
- `materialize` realizes the frozen selected-size production/CV matrix and invalidates downstream receipts only when that active matrix identity actually changes;
- production `train` and `evaluate` fail closed unless the selected production matrix and its matching preflight receipt are current;
- production EVAL2 retains normal best-admissible-checkpoint semantics, including selection of an earlier checkpoint than the training ceiling;
- `status` and `advance` share one derived lifecycle projection rather than introducing a second persistent state authority.

Local qualification completed on the implementation tree using the supplied dependency bundle/offline source trees:

- campaign CLI compatibility: 43 passed, 1 expected skip;
- focused semantic-orchestration regressions: 30 passed;
- target-size/EVAL2 scientific regressions: 69 passed;
- TRAIN2 runtime/policy regressions: 24 passed;
- production materialization regressions: 47/47 non-baseline tests passed in fresh-process groups;
- DATA7/DATA8/performance runtime/scientific group: 39 passed; its two documentation-contract failures were reproduced unchanged on effective baseline commit `220a7d4`;
- durable architecture and CLI-guide Markdown were reconciled and their tracked PDFs regenerated and visually checked.

Final packaging passed: `compileall`, `git diff --check`, binary-capable patch generation, and `git apply --check --binary` against a fresh detached copy of effective baseline commit `220a7d4`.

## Freeze disposition

The design is ready for gated implementation.

The accepted architecture is an **outer orchestration refactor**, not another target-size-v5 scientific redesign. It creates no new scientific authority, preserves exact 3/10/30 target-size endpoint semantics, preserves production best-checkpoint semantics, and makes the public command vocabulary correspond one-to-one with stable responsibilities.
