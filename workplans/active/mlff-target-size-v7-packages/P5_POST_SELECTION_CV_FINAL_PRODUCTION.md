---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: active
package_revision: 2
amended_date: 2026-08-29
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision1_baseline_commit: 5bf53c99ce31d1438c21bae81c0f30c79176bdc4
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: P4 revision 8 is formally closed, so P5 is no longer blocked. Revision 2 reconciles the P5 entry contract with the implemented CampaignStore-backed P4 current-terminal authority, corrects T_selected terminology to mean the exact selected target dataset rather than an epoch, cuts current post-selection CV authority away from legacy DATA5 label-domain/CV lineage, and freezes a fresh final-production path whose configured [training].max_num_epochs horizon is independent of target-size screening n3. The frozen parent remains the sole scientific and architectural verdict.
---

# P5 revision 2 — post-selection CV and fresh final production

## 0. Authority, revision boundary, and preserved doctrine

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. This package translates parent Gate G into implementation-ready work against the accepted P1-P4 product state; it does not amend the parent.

P4 revision 8 is formally closed at `145388e5ad11733be1c19539886e34b82cc7d7d2`. P5 therefore enters from the implemented current-generation runtime rather than from the pre-P4 assumptions in revision 1. The revision-1 P5 blob remains available in git history at `5bf53c99ce31d1438c21bae81c0f30c79176bdc4` and is superseded only where this revision is more specific.

The one-way scientific dependency is immutable:

```text
current authenticated target-size selection
  -> exact selected-data freeze
  -> post-selection CV / downstream method validation
  -> fresh final-production training
```

No CV configuration, fold assignment, CV evidence, downstream checkpoint choice, final-production setting, or downstream failure may mutate, reinterpret, or become authority for the already-selected target size.

### 0.1 Terminology correction: `T_selected` is data, not an epoch

The parent defines:

```text
T_N        = pi_train[:N]
T_selected = pi_train[:N_selected]
```

Therefore:

- `N_selected` is the selected target-training cardinality;
- `T_selected` is the exact ordered selected target-frame membership/prefix;
- target-size screening fidelity is `n1 -> n2 -> n3`;
- the final-production epoch horizon is the resolved `[training].max_num_epochs`, materialized through the existing version-agnostic TRAIN2 budget owner, and is a separate downstream quantity from screening fidelity.

P5 MUST NOT introduce or preserve any API/documentation meaning in which `T_selected` denotes an epoch, checkpoint boundary, or training horizon. P5 MUST NOT infer or overwrite the production horizon from `n3`.

### 0.2 Preserved accepted predecessor behavior

P5 does not reopen:

- P1 neutral scientific/provenance substrate;
- P2 one split, one `pi_train`, one `pi_eval`, nested target/evaluation ladders, or target-size statistical policy;
- P3 candidate execution, paired optimizer-seed trajectories, exact continuation, checkpoint/provider authentication, reducer replay, execution-head reconciliation, or exact-M evaluation ownership;
- P4 CampaignStore generation/current-state ownership, canonical terminal loader/currentness chain, current result-view sealing, canonical execution-root construction, storage ownership, or first-publication retention behavior;
- target-size ranking/scientific policy or the selected `N_selected/T_selected` result.

Any implementation pressure that would change those accepted predecessor semantics is a design stop/reopen condition rather than P5-local license to reinterpret them.

---

## 1. Implemented entry status and discovered reconciliation surface

### 1.1 Current P4 terminal-selection authority

P5 current execution MUST enter through the accepted P4 current exposure/loader path using the same invocation's `cfg`, `paths`, and real `CampaignStore`:

```text
expose_current_target_size_terminal_result(cfg, paths, store, expected_revision=...)
  -> load_validated_target_size_terminal_result(...)
  -> ValidatedTargetSizeTerminalResult
```

The current loader begins from the actual current CampaignStore revision and authenticates the complete predecessor chain. A caller-supplied expected revision or previously validated object is only a stale/assertion token; it is never current authority.

P5 entry requires terminal state `SELECTED`. Terminal `FAILED_SCIENTIFIC` is a valid P4 terminal outcome but is not a valid P5 execution entry and MUST fail closed before CV/final-production state is created or exposed.

For a selected terminal result:

```text
N_selected = validated.selected_target_size
T_selected = validated.revision.definition.training_order[:N_selected]
```

The accepted P4 terminal validator already proves that the selected-membership digest matches exactly that prefix. P5 MUST consume that authenticated fact rather than create an independent target-size membership algorithm or digest authority.

Derived `target-size-state.json`/human-readable result views, retained `ValidatedTargetSizeTerminalResult` objects, and historical target-size revisions are not current-selection authority.

### 1.2 Current legacy MLCV/TRAIN2 surface

The repository already contains useful lower-level machinery in:

- `mlcv_roles.py`;
- `mlcv_select.py`;
- `mlcv_aggregate.py`;
- `mlcv_final.py`;
- `mlcv_verification.py`;
- `mlcv_monitors.py`;
- DATA7/DATA8 materialization;
- `train2_policy.py` / `train2_runtime.py`;
- EVAL2/checkpoint/evaluation owners.

These components are reuse candidates, not automatically current authorities.

Known reconciliation drifts that P5 must close:

1. current legacy `MlcvRoleCatalog` is explicitly derived from DATA5/label-domain/unit-ID/CV lineage; the parent requires new MLCV role records to descend from exact `T_selected` membership and neutral correlation groups;
2. existing MLCV checkpoint/aggregate/final structures contain useful role guards, evaluation and aggregation semantics, but their persisted lineage must not preserve old DATA5 CV authority on the current path;
3. existing TRAIN2 `TrainingBudgetPolicy.planned_epochs` is a reusable execution budget owner, but final production must resolve that budget from `[training].max_num_epochs`; target-size `n3` cannot become the production budget by inheritance, default propagation, checkpoint continuation, or name conflation;
4. existing final-selection/committee machinery cannot substitute selection among old screening/CV trajectories for the parent-required fresh final-production run;
5. no existing pre-target CV plan may be revived merely to satisfy old MLCV constructor expectations.

The implementation MUST reconcile these surfaces by reusing compatible kernels/records below the new authority boundary and replacing/bypassing obsolete authority topology. Compatibility with old derived P5/CV records is not a requirement; V7 derived descendants are rebuildable.

---

## 2. Frozen P5 decision contract

### 2.1 One canonical current selected-training adapter

Create one version-agnostic P5 entry owner, preferably in `campaign_post_selection.py`, with a single canonical operation equivalent to:

```python
load_current_selected_training_context(
    cfg,
    paths,
    store,
    *,
    expected_revision=None,
) -> CurrentSelectedTrainingContext
```

The exact symbol/module name may change only for a demonstrably better repository fit, but the ownership semantics may not.

`CurrentSelectedTrainingContext` is a downstream projection of the canonical P4 current-terminal loader. It should carry only facts needed downstream, including at minimum:

- current target-size generation/state revision/sequence identity sufficient for stale-binding comparison;
- `N_selected`;
- exact ordered `T_selected` frame/member IDs;
- accepted selected-membership digest;
- predecessor scientific/definition identity needed to bind downstream evidence;
- authenticated current terminal result or opaque lineage reference as needed without duplicating its validation logic.

Rules:

- it MUST call the P4 current loader in the same current exposure/start/resume invocation;
- it MUST require state `SELECTED`;
- it MUST derive `T_selected` only as the authenticated `training_order[:N_selected]` prefix;
- it MUST NOT read the human result JSON as authority;
- it MUST NOT cache currentness in a second registry/file/global singleton;
- it MUST NOT duplicate P4 terminal validation, reducer replay, or current-generation selection logic;
- it MUST NOT expose a stale historical context as current merely because its internal digests remain valid.

### 2.2 Downstream immutable selection binding is lineage, not target-size authority

P5 may persist an immutable content-addressed `PostSelectionBinding` (or repository-equivalent record) to bind CV/final-production artifacts to the selected input. It must contain enough lineage to reject stale descendants, for example:

```text
P4 generation/revision identity
N_selected
ordered T_selected identity / membership digest
current target-size scientific/definition identity
P5 downstream policy identities that actually affect the descendant
```

This record is a dependency snapshot only. On every public/current P5 start, resume, report, write, or final-production exposure that claims to be current, P5 MUST re-establish current P4 authority through `load_current_selected_training_context(...)` and compare the persisted binding. The binding itself cannot make an old P4 generation current.

### 2.3 Authority uniqueness

There must be:

- one P4 current target-size loader/currentness owner;
- one thin P5 selected-training adapter delegating to it;
- no second mutable `N_selected/T_selected` authority;
- no P5 writer capable of changing P4 selection fields/current revision;
- no P5 fallback that recomputes target size from CV evidence or legacy DATA5 state.

---

## 3. Pass P5-A — current selected-data freeze and entry cutover

Implement the canonical current selected-training adapter and immutable downstream selection binding before modifying MLCV execution.

### Required behavior

1. Real config/path loading and a real CampaignStore are used at the production P5 entry boundary.
2. A current `SELECTED` P4 terminal result produces exactly one `CurrentSelectedTrainingContext`.
3. `N_selected` is exactly P4's selected size.
4. `T_selected` is exactly `training_order[:N_selected]`, including order and membership; group/correlation metadata cannot enlarge it.
5. `FAILED_SCIENTIFIC`, OPEN_ATTEMPT, AUTHORITIES_BOUND, corrupt current state, stale generation, or predecessor-authentication failure cannot enter P5.
6. Missing/stale/rebuildable result-view files do not become blockers or authority when CampaignStore/P3 evidence is valid.
7. A retained legitimate g1 selected snapshot/binding becomes stale after real `prepare` advances to g2 and must be rejected before downstream publication/work is claimed current.

### Acceptance closure

Mandatory real-owner tests:

- real current selected terminal -> adapter -> exact `N_selected/T_selected` prefix and digest lineage;
- current scientific terminal failure -> P5 entry rejects before downstream files/store rows are created;
- retain legitimate g1 terminal + P5 binding, perform real `prepare` to g2, then prove all current P5 entry/resume/report/write paths reject g1 before publication;
- stale/missing derived target-size result view while authoritative P4 state is current does not redirect P5 to JSON or force re-selection;
- structural test proves no P5 current path parses result JSON or invokes an alternative terminal/currentness implementation.

Run complete affected P4 terminal/currentness regression, including P3A9 only if the implementation touches or wraps its authority boundary, plus new P5-A tests before P5-B begins.

---

## 4. Pass P5-B — post-selection CV role-authority cutover

Replace the current-path old DATA5/label-domain CV authority with selected-data-derived role records.

### Scientific contract

CV is created only after `T_selected` is frozen. It owns its own:

- fold count;
- fold/partition seed;
- exact fold memberships;
- checkpoint-monitor/evaluation roles;
- fold-local preparation required by accepted CV methodology.

CV consumes only frames in `T_selected`.

Neutral duplicate/correlation groups constrain assignment among already-selected frames. They may force related selected frames into safe compatible roles or purge a selected frame from a fold, but MUST NEVER pull an unselected sibling into the CV population.

### Reuse and retirement boundary

Preserve/reuse where semantics remain valid:

- `MlcvDataRole` / evidence-operation authorization ideas;
- leakage/disjointness checks;
- deterministic fold construction kernels that operate on neutral selected-frame/group identities;
- monitor/evaluation kernels;
- replay TRUE_DFT role separation;
- serialization helpers when the resulting schema no longer claims obsolete authority.

Replace/remove from the current P5 path:

- `label_domain_id` as CV scientific authority;
- DATA5 bundle digest as the root of current CV selected-membership authority;
- pre-target `cross_validation_plans` ownership;
- unit/domain expansion that can introduce frames outside `T_selected`;
- any compatibility adapter that silently translates old derived CV records into current authority.

If old schema types remain temporarily for unreachable/tests/migration diagnostics, they must not be used by the current P5 orchestrator and P6 must be able to retire them cleanly.

### Acceptance closure

- every target frame in every fold role is a member of exact `T_selected`;
- fold gradient/checkpoint/outer-evaluation roles obey required disjointness and neutral group constraints;
- adversarial group fixture with selected member + unselected correlated sibling proves no expansion beyond `T_selected`;
- fold seed/count changes change only P5 descendants and leave current P4 revision/result/digest byte-for-byte unchanged;
- no pre-target CV record is required to `prepare` or `select-target-size`;
- deterministic same-input fold construction reproduces exact membership/digests;
- affected neutral partition/group, MLCV-role and authorization regression passes.

---

## 5. Pass P5-C — CV execution, evaluation, aggregation, and failure semantics

Route post-selection folds through the existing shared DATA7/DATA8/TRAIN2/EVAL2 execution machinery rather than creating a second training engine.

### Required execution semantics

For each CV fold/run:

- materialize only the authorized fold-local gradient/monitor/evaluation memberships descended from `T_selected`;
- use accepted source/replay roles according to the downstream training method;
- start from canonical accepted foundation/initialization state;
- create a fresh optimizer state for that fold/run;
- do not resume a target-size screening checkpoint/optimizer/RNG trajectory;
- preserve TRAIN2 resource ownership, exact checkpoint publication, provider validation, evaluation kernels, caches, concurrency, telemetry and bounded resource scheduling where semantically reusable;
- use post-selection CV EVAL2 roles, never target-size M1/M2/M3 ranking roles.

Fold-local checkpoint selection/monitoring may choose representatives for CV methodology, but those choices are downstream evidence only and cannot rank `N` or change target-size current state.

### CV outcome semantics

- CV success accepts the already-selected dataset/training method for downstream production/tuning.
- CV failure is a methodological-validation failure and cannot select another N, resume target-size screening, or reinterpret the selected prefix.
- If CV demonstrates that a material training-method/protocol change is required, that changed method requires a new target-size scientific experiment under the appropriate new upstream identity; P5 does not silently apply the changed method to the old selection.
- Diagnostic dispersion remains diagnostic unless the frozen parent/current accepted CV policy explicitly makes it a downstream gate; it never becomes target-size evidence.

### Acceptance closure

- bounded integration through real P5 role owner -> DATA7/DATA8 -> TRAIN2 -> EVAL2 -> MLCV aggregation, with expensive numerical training/inference faked only below the production owner boundary where needed;
- spies/records prove a new model initialization and optimizer are created for each fold and no target-size checkpoint/optimizer continuation is loaded;
- fold-local checkpoint/evaluation identities bind the exact post-selection roles;
- CV failure path leaves P4 CampaignStore target-size revision/state/result unchanged and cannot reach target-size reducer/selection mutation;
- restart of an incomplete CV campaign reauthenticates current P4 selection before reusing downstream evidence;
- affected MLCV select/aggregate/monitor/checkpoint, DATA7/DATA8/TRAIN2/EVAL2 and storage regression passes.

---

## 6. Pass P5-D — configured production policy and fresh final-production training

After accepted post-selection methodological validation, construct a genuinely fresh final-production run.

### 6.1 Production input

Final target gradients use the full exact `T_selected` membership. No fold subset, M1/M2/M3 population, unselected correlated sibling, or old DATA5 domain expansion may alter it.

Source/replay training and validation inputs follow the accepted current downstream training policy. Their roles remain explicit and may not be reclassified as target-size evidence.

### 6.2 Freshness

Final production MUST:

- start from the accepted canonical foundation/initialization;
- create fresh model-training state as required by that initialization contract;
- create a fresh optimizer;
- create fresh run/RNG state according to the accepted final-production seed policy;
- never continue a target-size screening trajectory;
- never continue a CV fold optimizer/checkpoint trajectory merely because it scored well;
- use the shared DATA8/TRAIN2 execution engine rather than a parallel trainer.

Existing MLCV final-selection/committee records may be retained only where their semantics remain valid downstream. They cannot turn a screening/CV representative into the parent-required fresh final-production training run.

### 6.3 Production horizon authority: `[training].max_num_epochs`

The frozen parent explicitly keeps `[training].max_num_epochs` as the production epoch horizon. P5 MUST preserve that configuration authority and materialize it through the existing version-agnostic TRAIN2 budget owner (for example `TrainingBudgetPolicy.planned_epochs`) rather than create a new P5 horizon-selection authority.

Rules:

- resolved `production_horizon = [training].max_num_epochs` for the final-production run;
- no `production_horizon = n3` derivation or target-size override;
- no fallback to the last screening checkpoint epoch;
- no CV-selected replacement horizon unless a future parent-level scientific revision explicitly changes this authority;
- no reuse of target-size continuation state to reach the production horizon;
- the resolved production horizon is content-addressed in the final run plan;
- changing `[training].max_num_epochs` invalidates the affected downstream production descendants according to the existing scientific-identity DAG, but P5 itself must not translate that setting into target-size `n3`.

Acceptance MUST include a configuration with `[training].max_num_epochs != n3` and prove the actual TRAIN2 final run receives/executes `[training].max_num_epochs` while P4 selection remains unchanged. A coincidental equal numeric value is legal only when independently configured; equality must never arise from a dependency edge.

### 6.4 Locked/final evidence discipline

P5 does not authorize leakage of locked-test evidence into training, target-size selection, CV tuning, production-horizon configuration, checkpoint choice, or seed choice. Any final validation/physical verification/locked evaluation retains its existing downstream role and must not be relabeled independent if it influenced model choice.

### Acceptance closure

- exact final DATA8 target membership equals full ordered `T_selected` and nothing else;
- fresh initialization/optimizer/RNG provenance is distinct from screening and CV trajectories;
- `[training].max_num_epochs` differs from `n3` in an explicit regression fixture and the actual runtime follows the configured production value;
- no screening/CV checkpoint is accepted as the final-production starting state;
- bounded real-owner final-production entry reaches shared DATA8/TRAIN2 scheduling/materialization;
- affected final-selection/production/materialization/TRAIN2 regression passes.

---

## 7. Pass P5-E — persistence, restart, and invalidation DAG

P5 descendants must be restartable without creating a second upstream authority.

### Required invalidation behavior

1. **P4 current generation/selection changes**: stale P5 selection binding, CV state and final-production state become non-current and must be rejected before current publication/resume.
2. **P4 remains the same current selected terminal result**: missing rebuildable P5 views may be recreated without target-size recomputation.
3. **CV-only fold count/partition seed/monitor policy changes**: invalidate affected CV and production descendants only; do not invalidate/rebuild P4 target-size state.
4. **Final-production-only output/runtime changes**: invalidate affected final-production descendants only when scientifically appropriate; `[training].max_num_epochs` follows the existing parent scientific-identity DAG and is never silently reclassified by P5.
5. **Material training-method/protocol change**: follow the parent scientific identity DAG; if it changes the method whose target-size convergence is being claimed, a new target-size experiment is required rather than a P5-local override.
6. **Corrupt/incomplete downstream evidence**: fail/rebuild downstream evidence according to its ownership; never repair it by altering target-size selection.

Currentness comparisons must use content/revision lineage, not timestamps or existence of result files.

### Storage/concurrency rules

- use existing atomic publication/content-addressed storage/CampaignStore transaction primitives where applicable;
- immutable P5 evidence may be reused only after current upstream binding revalidation;
- same logical descendant publication must be conflict-safe/idempotent under concurrent writers;
- P5 storage cleanup cannot delete accepted P1-P4 authorities required to reauthenticate its own lineage;
- no direct unlink/rmtree cleanup path may bypass the accepted production storage ownership boundary.

### Acceptance closure

- same-current-selection restart reuses valid P5 evidence without rerunning P4;
- real g1 selected -> partial/complete P5 -> real prepare g2 -> old P5 resume/publication rejects before numerical work/public exposure;
- CV-only config mutation leaves P4 current selection unchanged;
- final-production-only output/runtime mutation leaves P4 and unaffected CV evidence unchanged where scientifically allowed;
- corruption/fork/conflict/concurrent-publication tests fail closed at the owning downstream layer;
- affected CampaignStore/storage/restart regression passes.

---

## 8. Pass P5-F — CLI/orchestrator/public-surface cutover

Wire all current post-selection CV and final-production entrypoints through the canonical selected-training adapter and revised post-selection role authority.

### Current-path requirements

- current public/orchestrated P5 commands begin from real config/paths/store and reauthenticate P4 current selection;
- no current path accepts a bare historical `ValidatedTargetSizeTerminalResult`, result JSON, old DATA5 CV catalog, or persisted P5 binding as sufficient current authority;
- no ordinary generic `train`/`evaluate` command becomes a second target-size or P5 scheduler;
- no current P5 API can write/change `N_selected`, selected-membership digest, P4 reducer/head, or CampaignStore target-size revision;
- no version-prefixed (`v7_`, `V7*`) production module/class/function/file/schema naming is introduced merely because this package belongs to V7;
- old MLCV/DATA5 preselection entrypoints that conflict with the parent are made unreachable from current orchestration and left for P6 destructive cleanup if immediate deletion would unnecessarily broaden P5.

### Structural acceptance

Prove by source/import/call-graph inspection plus tests:

- one current selected-training adapter;
- one upstream current terminal loader/currentness chain;
- zero current P5 reads of target-size result JSON as authority;
- zero old DATA5/label-domain CV authority edges from current P5 orchestration;
- zero CV/final-production -> target-size mutation edges;
- zero `[training].max_num_epochs` -> target-size `n3` or target-size `n3` -> production-budget derivation edges;
- zero duplicate current-selection caches/registries;
- zero V7-prefixed production symbols introduced by P5.

Run stage-local affected CLI/orchestrator/import regression before final closure.

---

## 9. Pass P5-G — fresh assembled acceptance and package closure

P5-G is blocked until P5-A through P5-F have both semantic/conformance closure and functional closure.

### 9.1 Mandatory assembled lifecycle

Exercise, through real production owners with bounded numerical fakes only below those owners where necessary:

```text
real config + real CampaignStore
 -> current accepted P4 SELECTED terminal authority
 -> canonical current selected-training context
 -> exact T_selected post-selection CV plan
 -> bounded CV DATA7/DATA8/TRAIN2/EVAL2 execution
 -> CV aggregate/outcome without P4 mutation
 -> configured [training].max_num_epochs production budget
 -> fresh final-production DATA8/TRAIN2 entry on full T_selected
 -> persist/reload P5 descendants
 -> re-load current P4 terminal selection
```

Final assertions:

- same `N_selected` before and after CV/final production;
- same exact `T_selected` membership/digest before and after;
- P4 current revision/head/reducer evidence unchanged by downstream work;
- each CV fold is inside `T_selected` and group-safe;
- final production uses full `T_selected`;
- fresh final optimizer/init does not descend from screening/CV continuation state;
- actual final production horizon is the resolved `[training].max_num_epochs` and is demonstrably independent of `n3`;
- restart returns the same current downstream result only after fresh P4 currentness validation.

### 9.2 Mandatory negative matrix

At minimum include:

- P4 `FAILED_SCIENTIFIC` terminal cannot enter P5;
- stale legitimate g1 selection/binding after real g2 `prepare` cannot resume/report/write current P5 results;
- wrong/reordered/expanded selected membership rejects;
- selected + unselected sibling correlation group cannot expand CV population;
- CV fold-role leakage rejects;
- screening checkpoint/optimizer continuation offered to a CV fold rejects or is structurally unreachable;
- screening/CV checkpoint/optimizer continuation offered to final production rejects or is structurally unreachable;
- CV failure cannot invoke target-size reducer/reselection;
- with `[training].max_num_epochs != n3`, final TRAIN2 receives the configured production horizon; if the two values are equal in another configuration, structural tests still prove no dependency edge;
- locked-test evidence cannot influence P5 selection/tuning paths;
- stale/missing derived target-size result JSON cannot supersede CampaignStore authority.

### 9.3 Final affected regression

Re-derive the affected surface from the complete P5 implementation diff. At minimum include all modified/new P5 modules plus affected:

- P4 current terminal exposure/loader/currentness tests;
- P3A9/reducer/head tests if the wrapper touches those surfaces;
- neutral selected-frame/correlation-group partition tests;
- MLCV roles/select/aggregate/final/verification/monitor tests actually reused;
- DATA7/DATA8 materialization;
- TRAIN2/EVAL2 policy/runtime/checkpoint/provider tests;
- configuration resolution for `[training].max_num_epochs`;
- CampaignStore/storage/restart/concurrency tests;
- CLI/orchestrator tests;
- assembled P4 -> P5 integration.

Stage-local affected regression after each material behavior-changing pass is mandatory. P5-G then runs a fresh complete affected regression on the assembled candidate. If the final diff crosses broader common execution/storage surfaces, run the broader repository suite unless a smaller surface is independently proven complete.

Long GPU/data-heavy production qualification is **not** P5 functional closure. It remains deferred to final release/target-machine qualification as already frozen by the project; P5 must nevertheless execute bounded functional and real-owner integration sufficient to prove control flow, lineage, restart, and freshness.

---

## 10. Explicit non-goals and stop/reopen conditions

P5 MUST NOT:

- change target-size ranking, size ladder, M ladder, fidelity ladder, paired optimizer seeds, or practical-equivalence policy;
- change P4 currentness/persistence semantics merely to simplify downstream CV;
- add a second target-size current-state file/cache/registry;
- reintroduce label-domain fanout or pre-target CV planning;
- reinterpret `T_selected` as a training epoch;
- make screening `n3` the production horizon authority or create a competing P5 horizon-selection authority to `[training].max_num_epochs`;
- use CV to choose another `N_selected`;
- use locked-test evidence to tune/select the production model;
- fork a second DATA8/TRAIN2/EVAL2 execution engine;
- migrate old derived MLCV/CV records into current scientific authority merely for reuse.

Stop and return to design if implementation shows any of the following is necessary:

1. the accepted P4 terminal result cannot expose exact authenticated `N_selected/T_selected` without changing predecessor science/authority;
2. current neutral correlation-group evidence is insufficient to construct leakage-safe CV on the selected frames without altering P1/P2 scientific semantics;
3. fresh final production cannot be expressed through the shared DATA8/TRAIN2 execution machinery without changing accepted common training semantics;
4. a required material training-method change would invalidate the target-size experiment whose result P5 is consuming;
5. the frozen parent and implemented predecessor authority are materially contradictory rather than merely requiring an adapter.

---

## 11. Exit gate

P5 revision 2 is accepted only when:

> The current P4-selected dataset is reauthenticated at downstream exposure time, frozen exactly as `T_selected = pi_train[:N_selected]`, used exclusively for post-selection CV, and then used in full by a genuinely fresh final-production run. CV cannot alter or enlarge the selected dataset, legacy DATA5 label-domain CV authority is absent from the current path, final production does not continue screening/CV optimizer state, and its resolved `[training].max_num_epochs` production horizon is scientifically and programmatically independent of target-size screening `n3`.

After P5 implementation, stage-local closure, fresh assembled affected regression, and independent review all pass, mark this package implemented/accepted and commit the P5 closure checkpoint. P6 remains blocked until that formal P5 closure.