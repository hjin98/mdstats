---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: active
package_revision: 7
amended_date: 2026-08-30
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision6_implementation_baseline_commit: 81e72cdb22cdbfddae0508592b2b38b3f80aae2f
revision5_implementation_baseline_commit: ca1c402645fc210c38a15e55c81cdf30e6b459ab
revision4_baseline_commit: e19962966116586da8a028c252a53deb80cd6795
revision3_baseline_commit: 178a4e653693b810cb02e5ea8bd6bd376da93ab0
revision2_baseline_commit: 2a3c3776aa03ac7e45dd0de2986a6bb390deb710
revision1_baseline_commit: 5bf53c99ce31d1438c21bae81c0f30c79176bdc4
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: Independent review of the revision-6 implementation found two remaining P5-local blocking implementation defects without invalidating the frozen parent or P1-P4/P5 scientific design. First, the real MacePostSelectionTrainer no longer executes the qualified TRAIN2 wrapper contract: replay-enabled Train2RuntimePlan construction omits the required TRUE_DFT monitor SHA, the child environment does not carry the TRAIN2 plan/replay path, the internal post-selection configuration is handed directly to MACE instead of passing through the established translator, the trainer looks for a non-canonical summary path, and the replay foundation baseline is represented by a test-only proxy. Second, PostSelectionMethodIdentity still binds path/config spellings rather than authenticated foundation/replay scientific content and contains at least one field, optimizer family, that does not reach the executable MACE job. Revision 7 specifies the exact owning execution and identity contracts needed for closure while preserving every unaffected prior P5 obligation.
---

# P5 revision 7 — qualified TRAIN2 execution and content-authenticated method closure

## 0. Authority, scope, and preserved contract

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific and architectural verdict. P5 remains bound to Protocol 5.8.0. This revision is a P5 implementation-correction handoff; it does not reopen P1-P4, target-size selection science, the P1 split-exclusion authority, or the post-selection CV/final-production model.

The revision-6 implementation at `81e72cdb22cdbfddae0508592b2b38b3f80aae2f` is the immediate baseline under correction. Revision 7 supersedes revision 6 only where this document gives more specific identity, launch, replay-lineage, and acceptance requirements. All unaffected P5 requirements remain binding.

The following are frozen and must not regress:

- P4 CampaignStore/current-terminal authority is the sole upstream current `N_selected/T_selected` owner.
- `T_selected = pi_train[:N_selected]` exactly. CV, replay, M3, or production may not widen, replace, or reselect it.
- P5 current reads/writes must reauthenticate the current P4 binding; current-facing publication remains protected by the existing commit-time stale-generation fence.
- Post-selection CV occurs only after target-size selection, uses configured `K >= 2`, exact selected-only coverage, and the complete canonical P1 split-exclusion/protected-relation projection.
- Every required CV fold and required CV seed/variant must pass. Mean-only, majority, best-seed, partial-fold, K=0/K=1, and `cv_not_performed` production authorization remain forbidden.
- Held-out outer CV target evidence cannot affect that fold's fitted preparation, training, checkpoint choice, or replay admissibility calculation.
- Replay/physical evidence are hard admissibility/diagnostic evidence only. They may reject a checkpoint but receive zero target-ranking, tie-breaking, fold-acceptance, seed-ranking, committee-ranking, or target-size-selection credit.
- M3 remains development/model-selection evidence for final checkpoint selection, not independent validation.
- Final production is fresh: full exact `T_selected`, canonical method initialization, fresh optimizer/RNG/run state, and no continuation from target-size/CV checkpoints or optimizer state.
- `[training].max_num_epochs` remains final-production-only horizon authority. It is independent of target-size `n3` and the CV training budget.
- Screen/CV/final run, checkpoint, restart, and evidence namespaces remain collision-proof.
- Policy -> plan -> realized evidence dependency direction remains acyclic.
- CV/final evidence may not mutate or reinterpret P4 target-size authority.
- Long GPU/data-heavy production qualification remains deferred to final release. Bounded functional regression/integration is required now.

P6 remains blocked until revision 7 reaches semantic closure, functional closure, and independent P5 review pass.

---

## 1. Exact defects revision 7 must close

### 1.1 Qualified TRAIN2 execution contract is currently bypassed

The revision-6 implementation has a production-path defect, not merely a test gap:

1. `execute_post_selection_run()` enables replay monitoring in `post_selection_runtime_plan()` when replay admissibility is enabled.
2. `Train2RuntimePlan` requires `true_replay_monitor_sha256` whenever `replay_monitor_enabled=True`, but the P5 builder does not currently supply it.
3. `MacePostSelectionTrainer` currently invokes `mdstats-mace-train` without installing `MDSTATS_TRAIN2_RUNTIME_PLAN`, so `runtime_plan_from_environment()` sees no TRAIN2 plan and the qualified TRAIN2 runtime cannot activate.
4. The trainer does not install `MDSTATS_TRAIN2_TRUE_REPLAY_PATH` for the authenticated TRUE_DFT monitor.
5. The trainer hands `post_selection_mace_config.yaml` directly to the wrapper even though that file uses internal P5 keys such as `target_train_file` / `target_valid_file`. `post_selection_mace_run_configuration()` is the established translation owner that produces executable MACE keys such as `train_file` / `valid_file` and carries foundation/multihead replay arguments.
6. The trainer currently searches `results/train2_runtime_summary.json`, while TRAIN2 owns its canonical summary and loader under the checkpoint directory (`TRAIN2_RUNTIME_SUMMARY_FILENAME`, currently `train2_runtime.json`).
7. Replay baseline evaluation currently constructs a `SimpleNamespace` in place of a production-capable foundation prediction provider. `evaluate_post_selection_dataset()` requires the real provider path when no test inference callback is installed.
8. Replay resolution currently catches broad exceptions and converts them to `replay_resolution=None`; that can turn a malformed replay-required method into an apparent replay-disabled/incomplete run instead of failing before training.

These defects must be corrected at the owning execution boundary. Tests that fabricate a runtime summary, replay metric, or baseline provider below this boundary do not close the production claim.

### 1.2 Shared method identity is still location/config-spelling based in material places

The revision-6 implementation also leaves identity/execution divergence:

- foundation identity is currently derived from a path string (`digest({"foundation_model": path})`) rather than the authenticated model/head scientific identity;
- byte-identical relocation therefore changes identity even though the method is unchanged;
- replacing model bytes at the same path can leave identity unchanged while training a different scientific model;
- replay policy/legacy identity can likewise depend on path/config spelling while the actual source/split/TRUE_DFT view bytes change;
- `resolve_shared_optimizer_settings()` includes `optimizer_family`, but the canonical `MaceOptimizerPolicy` and current P5 executable MACE configuration do not carry an optimizer-family field, so changing this value can change method identity without changing the executed training algorithm.

Revision 7 freezes content-authenticated identity semantics and removes the need for the implementer to invent a new identity scheme.

---

## 2. Frozen canonical post-selection method identity

### 2.1 Foundation model/head identity — reuse the existing foundation owner

P5 must use the repository's existing generalized foundation identity machinery in `mdstats/training_data/foundation.py` rather than hashing a path string.

For every non-scratch method:

1. Resolve the configured foundation checkpoint through the existing `MaceFoundationSpec` / `inspect_mace_foundation()` / `FoundationPotentialIdentity` path.
2. Require an inspected/canonical foundation identity before CV/final work can be authorized. Multi-head checkpoints must resolve an explicit valid head; do not rely on MACE fallback head selection.
3. Store both:
   - a runtime locator/reference used to open the checkpoint; and
   - the scientific identity used for method lineage.
4. The scientific identity must be `FoundationPotentialIdentity.canonical_content_digest` or an equivalent digest containing at least the exact checkpoint SHA-256, resolved foundation head, model family, architecture signature, supported species/head information, and correction stack already owned by `FoundationPotentialIdentity`.
5. `TargetSizeCommonTrainingPolicy.foundation_checkpoint_digest` and `PostSelectionMethodIdentity` must bind this canonical content identity, not `digest(path_string)`.
6. Immediately before a real training or foundation-baseline evaluation uses the file, reauthenticate that the current file bytes still match the resolved foundation SHA-256. A same-path byte replacement must fail closed or produce a new method identity before CV/final authorization can be reused.

Required invariants:

```text
same authenticated checkpoint bytes + same head/specification + different filesystem path
    -> same scientific method identity

different checkpoint bytes at same filesystem path
    -> different scientific method identity / stale prior CV authorization

same checkpoint bytes + different resolved head
    -> different scientific method identity
```

Scratch training is the only valid case with no foundation identity. A configured fine-tuning or multihead-replay method with no authenticated foundation identity must fail before expensive work.

### 2.2 Replay identity — separate stable method policy from realized source lineage

Do not place raw replay path spelling in the shared scientific method identity.

Resolve replay through the existing canonical replay owners (`single_source_replay_config_from_campaign`, replay source inspection, deterministic split manifest, true-label cache/view materialization, or the normalized legacy compatibility path already owned by replay code).

The identity split is frozen as follows:

- **PostSelectionMethodIdentity / shared method policy** binds replay semantics: replay enabled/disabled, exposure mode, head/role semantics, split-policy parameters, TRUE_DFT retention requirement, degradation budget/admissibility policy, and any other stable method-defining replay policy.
- **CV plan** binds the exact authenticated replay source/split/view lineage used by that CV campaign.
- **CV acceptance/authorization** is valid only for the replay lineage bound by its CV plan.
- **Final production plan** must bind the current replay lineage and require exact equality with the replay lineage accepted by CV before production can be authorized.
- **Realized fold/final evidence** binds the exact replay train/monitor artifacts and candidate/baseline metric records it consumed.

At minimum, one deterministic `replay_lineage_digest` used by plans must cover the canonical authenticated identities of:

```text
ReplaySourceArtifact content identity / source bytes identity
+ ReplaySplitManifest.content_digest
+ replay train-view logical/content identity
+ replay TRUE_DFT monitor-view logical/content identity
+ exact monitor file SHA-256 used by TRAIN2/EVAL2
```

Use existing artifact digests rather than inventing path hashes.

Required invariants:

```text
same replay bytes/policy/split at different path
    -> same replay scientific lineage

changed replay bytes at same path
    -> changed replay lineage; prior CV cannot authorize final production

changed split seed/ratio or TRUE_DFT monitor membership
    -> changed replay lineage; prior CV cannot authorize final production
```

### 2.3 Field-by-field identity -> execution parity

`PostSelectionMethodIdentity` may contain a field only when the real execution path consumes/enforces the corresponding value. The implementer must perform and test this audit for all current fields.

Required mapping after revision 7:

| Method concern | Identity owner | Required executable consumer |
| --- | --- | --- |
| training mode | `PostSelectionMethodIdentity` / resolved method | MACE single-head vs multihead/fine-tuning configuration |
| foundation model/head | canonical `FoundationPotentialIdentity` digest | actual `foundation_model` / `foundation_head` passed to MACE and real foundation baseline provider |
| common objective/weights/E0 policy | `TargetSizeCommonTrainingPolicy` digest | `fit_post_selection_preparation()` and exported DATA8 training weights/E0 |
| MACE architecture | canonical architecture digest | executable MACE config generated for every CV/final run |
| LR schedule | `LearningRateSchedulePolicy` digest | `Train2RuntimePlan.learning_rate_policy` |
| batch/EMA/weight-decay/clip/dtype/device and other supported optimizer settings | resolved shared settings / `MaceOptimizerPolicy` | executable MACE configuration + TRAIN2 optimizer policy digest |
| replay policy | shared replay policy digest | replay training exposure + TRUE_DFT admissibility path |
| checkpoint admissibility | `CheckpointAdmissibilityPolicy` digest | `assess_eval2_checkpoint()` with real required evidence |
| target-only checkpoint ordering | `CheckpointSelectionPolicy` digest | existing EVAL2/P5 representative selection owner |
| backend/acceleration when method-defining | resolved acceleration identity | actual MACE/qualified acceleration execution path |

#### Optimizer-family decision is frozen

The current canonical `MaceOptimizerPolicy` does **not** define an independent optimizer-family field. Revision 7 therefore forbids P5 from inventing one only for identity purposes.

Implementation must do one of these, in priority order:

1. **Preferred current correction:** remove `optimizer_family` from `resolve_shared_optimizer_settings()` and from any method digest if the accepted current training stack does not expose it as a real supported policy. If `[training].optimizer` is supplied despite not being an accepted current configuration field, reject it before training rather than hashing and ignoring it.
2. Only if repository evidence proves that the accepted current MACE training owner already has a supported optimizer-family control that P5 failed to route may the implementation bind it; then it must be normalized through that existing owner and passed to the executable MACE job.

Do not add a new optimizer-family product capability solely to satisfy the revision-6 test. The protected requirement is identity/execution equivalence, not preservation of an accidental unsupported knob.

### 2.4 Location fields remain runtime locators, not scientific identity

Foundation/replay paths may remain in resolved runtime objects because the process must open files. They must not be the authoritative digest material when content/semantic identities already exist.

A path may affect an operational cache key only when location itself changes an operational contract; it must not invalidate accepted scientific CV evidence merely because identical immutable input bytes were relocated.

---

## 3. Frozen qualified TRAIN2/MACE execution contract

### 3.1 Resolve all replay/foundation prerequisites before launching MACE

`build_post_selection_context()` / `execute_post_selection_run()` must establish the complete current method and, when enabled, replay authority before child training starts.

For replay-enabled runs, use `_resolve_true_label_replay_inputs(cfg, paths, require_train=True)` or a public/shared extracted equivalent with identical semantics. Do not wrap this call in `except Exception: replay_resolution = None`.

Allowed handling:

- propagate canonical `TrainingDataInputError` / `PostSelectionError` with useful context; or
- catch only a known exception to add context and re-raise.

Forbidden handling:

- convert replay-resolution failure to replay-disabled behavior;
- proceed with `replay_monitor_enabled=True` while the exact monitor artifact/path/SHA is missing;
- proceed with multihead replay while replay training input is missing.

### 3.2 Exact runtime-plan construction

Extend `post_selection_runtime_plan()` (or replace it with a shared canonical builder) so the resulting `Train2RuntimePlan` is complete at construction time.

Required call semantics:

```text
post_selection_runtime_plan(
    method=<current PostSelectionMethodIdentity>,
    optimizer_policy=<this run's canonical MaceOptimizerPolicy>,
    budget_policy=<CV or final role budget>,
    structures_per_epoch=<exact target training structures presented per epoch under current TRAIN2 semantics>,
    learning_rate_policy=<resolved shared LR policy>,
    replay_monitor_enabled=<resolved checkpoint admissibility replay flag>,
    true_replay_monitor_sha256=(
        replay_resolution.monitor_artifact.sha256 when replay enabled
        else None
    ),
    target_head_name=<resolved target head>,
    replay_head_name=<resolved replay/PT head when applicable>,
)
```

The exact function signature may differ, but the resulting `Train2RuntimePlan` must contain those values.

When `replay_monitor_enabled=True`:

- `true_replay_monitor_sha256` must equal the SHA-256 of the exact TRUE_DFT monitor file that the child receives;
- the path and SHA must be reauthenticated before launch;
- target/replay head names must match the actual multihead MACE configuration.

When replay is disabled:

- `replay_monitor_enabled=False`;
- `true_replay_monitor_sha256=None`;
- no replay path environment variable may be required.

TRAIN2 replay monitoring remains diagnostic/validation-loader exposure only. It must not introduce adaptive stopping or checkpoint-ranking control.

### 3.3 Internal P5 configuration is not the executable MACE configuration

`materialize_post_selection_run()` may continue to persist its internal `post_selection_mace_config.yaml` record because it is useful evidence. The production child must not consume that internal schema directly.

`MacePostSelectionTrainer.__call__()` must perform this exact ownership chain:

```text
load and authenticate PostSelectionMaterialization
 -> read internal post_selection_mace_config payload
 -> validate POST_SELECTION_MACE_CONFIG_SCHEMA
 -> post_selection_mace_run_configuration(internal_payload)
 -> write an executable MACE config file for this run
 -> invoke the qualified mdstats-mace-train wrapper with the executable config
```

The executable config must contain the current MACE parser-facing names, including `train_file`, `valid_file`, the resolved foundation/head settings, multihead/replay settings, architecture fields, and all supported shared optimizer settings.

The translator is the one owner for internal-P5-name -> MACE-name conversion. Do not duplicate that mapping inside the trainer command builder.

The executable file may be named `mace_run_config.yaml` or another version-agnostic name. Its bytes or digest should be retained/authenticated as realized descendant evidence when practical, but it must not become a second scientific policy authority.

### 3.4 Required wrapper child environment

The qualified child environment is part of the TRAIN2 control contract.

`MacePostSelectionTrainer` must launch with a copied environment (`env = dict(os.environ)` plus any explicitly supported injected environment) and set:

```text
MDSTATS_TRAIN2_RUNTIME_PLAN = canonical JSON serialization of request.plan.to_dict()
PYTHONHASHSEED = decimal optimizer seed
```

When replay monitoring is enabled, also set:

```text
MDSTATS_TRAIN2_TRUE_REPLAY_PATH = absolute path to the exact authenticated TRUE_DFT replay monitor file
```

Use the exported constants from `train2_runtime.py` rather than duplicating variable-name strings where possible:

- `TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE`;
- `TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE`.

The child environment must preserve any already-qualified critical-precision/acceleration environment required by the existing wrapper launch path. Do not erase inherited environment state by constructing an incomplete environment from scratch.

### 3.5 Required working-directory and path semantics

Run the wrapper with `cwd=request.materialization_directory` unless the executable config is changed to use fully absolute artifact paths. This preserves the existing materialization-relative `train_file` / `valid_file` / replay file semantics.

Do not rely on the caller's current working directory.

Before launch, authenticate:

- internal materialization config SHA/digest;
- target/monitor artifact bytes already owned by materialization;
- foundation bytes against canonical foundation SHA;
- replay train/monitor bytes against canonical replay artifacts when enabled.

### 3.6 Canonical TRAIN2 summary ownership

Do not look for `results/train2_runtime_summary.json` and do not create a P5-only summary format.

After wrapper success, load the runtime result through the canonical TRAIN2 owner:

```text
summary = load_train2_runtime_summary(request.checkpoint_directory)
```

or an equivalent exported canonical loader using `TRAIN2_RUNTIME_SUMMARY_FILENAME`.

Then require/authenticate at least:

- `summary.plan_digest == request.plan.content_digest`;
- optimizer-policy digest matches the runtime plan;
- budget/LR/structures-per-epoch geometry matches the plan;
- checkpoint count/epoch bounds remain valid;
- continuation/model-architecture evidence is authenticated through existing TRAIN2/provider owners before EVAL2 uses a checkpoint.

A wrapper return code of zero with no valid canonical TRAIN2 summary is failure.

### 3.7 Preserve supervision behavior

Do not replace the qualified `mdstats-mace-train` completion/signal supervision machinery. P5 must invoke the established wrapper and let it own MACE child completion, stable-artifact validation, lingering-process termination, and signal forwarding.

P5's trainer should supervise only the wrapper process and authenticate its outputs.

---

## 4. Frozen replay training and admissibility execution

### 4.1 Replay training exposure

For `training_mode == "multihead_replay"`:

- `replay_resolution.train_path` must exist and be authenticated before materialization/launch;
- the executable MACE config must actually expose replay training through the established multihead/replay fields (`multiheads_finetuning`, replay/PT train file, replay/PT validation file, and head definitions as required by the accepted MACE path);
- CV target training membership remains the fold-local target gradient set only;
- final target training membership remains full exact `T_selected` only;
- replay membership is a separate role and must never be unioned into `T_selected`, CV fold construction, target E0 fitting, target configuration weighting, or P4 selection authority.

### 4.2 Candidate replay TRUE_DFT evaluation

For each candidate checkpoint considered for a CV or final representative:

1. authenticate the candidate checkpoint through the existing post-selection/TRAIN2 provider owner;
2. evaluate that candidate against the exact authenticated replay TRUE_DFT monitor artifact;
3. reduce through the existing EVAL2 metric owner;
4. obtain actual candidate force-component RMSE in eV/A;
5. pass it to `assess_eval2_checkpoint()` with the matching baseline RMSE and `replay_label_mode="true_dft"`.

Do not construct replay RMSE directly in P5 using a separate formula.

### 4.3 Canonical foundation baseline provider

The replay foundation baseline must be a production-capable provider derived from the same canonical `FoundationPotentialIdentity` bound by the shared method.

The current `SimpleNamespace(is_baseline=True, foundation_model=...)` is forbidden in production code because it is not a prediction provider and works only when a test callback intercepts inference.

Required end state:

```text
resolved canonical foundation identity + resolved head
 -> existing MACE/foundation provider constructor
 -> provider exposing the normal prediction interface used by evaluate_post_selection_dataset
 -> predictions on the exact same TRUE_DFT monitor artifact as candidate
 -> existing EVAL2 reduction
 -> baseline replay RMSE
```

Reuse the existing `MaceCalculatorProvider`/foundation evaluation mechanism or extract a minimal shared provider builder from an existing accepted owner. Do not implement a second MACE inference engine in P5.

Before building the baseline provider, reauthenticate the exact foundation file SHA against the canonical foundation identity.

The baseline provider must select the exact canonical foundation head. Multi-head fallback is forbidden.

### 4.4 Baseline replay cache identity

Caching the foundation replay RMSE is allowed but the current path-string cache key is insufficient.

If a cache remains, its key must cover at least:

```text
canonical FoundationPotentialIdentity.canonical_content_digest
+ exact replay TRUE_DFT monitor logical/content identity and SHA
+ EVAL2 metric policy identity
+ evaluation dtype/backend identity when scientifically material
```

A cache hit must not bypass reauthentication of referenced immutable artifacts when currentness requires it.

Caching is optional. Correct uncached evaluation is acceptable.

### 4.5 Missing replay evidence fails closed

If replay admissibility is enabled, any of these conditions must fail the run before representative selection:

- replay source/split/view cannot be resolved;
- replay train input required by the method is missing;
- replay TRUE_DFT monitor is missing or its SHA changed;
- foundation baseline identity/file/head cannot be authenticated;
- candidate or baseline replay inference fails;
- replay metric reduction fails;
- candidate/baseline evidence does not refer to the same exact monitor identity;
- replay label mode is not authenticated TRUE_DFT.

Do not convert any such condition into `None` replay metrics and continue.

When replay is genuinely disabled by the resolved method, `None` replay metrics remain valid and target-only selection proceeds normally.

---

## 5. CV/final plan and authorization lineage

### 5.1 CV plan

The CV plan must bind:

- current P4 selected binding and exact `T_selected` identity;
- shared method digest;
- canonical foundation scientific identity through the shared method;
- CV policy digest;
- current canonical P1 relation/split-exclusion authority;
- exact selected-only projected components and folds;
- required CV seed/run matrix;
- `replay_lineage_digest` when replay is enabled.

### 5.2 CV acceptance

CV acceptance remains all-required folds/seeds and target-only outer acceptance. It must retain/bind the accepted CV plan digest, so the replay lineage and foundation method identity accepted by CV are not lost when authorizing production.

### 5.3 Final production plan

Before final plan construction/publication:

- re-resolve current foundation and replay authorities;
- require current foundation shared-method identity to equal the CV-accepted method identity;
- require current `replay_lineage_digest` to equal the replay lineage bound by the accepted CV plan;
- otherwise stale CV cannot authorize production.

The final plan then binds current selected authority, exact shared method, accepted CV authorization, production-only policy, M3 lineage, final seeds, and current replay lineage.

### 5.4 Realized evidence

Fold/final evidence should bind realized materialization/runtime/evaluation descendants, including replay artifacts/metrics needed to audit the admissibility decision. Do not push candidate-specific replay metrics upward into policy identities.

---

## 6. Required implementation sequence

### P5-R7A — repair scientific identity before execution

**Owning/expected files**

- `mdstats/training_data/post_selection_identity.py`;
- `mdstats/training_data/foundation.py` only if a small reusable resolver API is genuinely missing;
- `mdstats/training_data/post_selection_cv_plan.py` / `post_selection_production.py` only as needed for replay-lineage binding;
- replay integration adapter(s) only if needed to expose canonical artifact lineage.

**Required edits**

1. Replace path-string foundation digest construction with canonical `FoundationPotentialIdentity` resolution/content identity.
2. Keep foundation path/reference separately as runtime locator.
3. Resolve explicit foundation head through canonical foundation inspection.
4. Define/calculate one deterministic replay-lineage digest from existing authenticated replay artifacts and bind it to CV/final plans.
5. Remove unsupported `optimizer_family` from method identity/settings, or route it through an already-existing accepted optimizer-family owner if repository evidence proves one exists. Do not invent new optimizer support for this repair.
6. Reject unsupported `[training].optimizer` input rather than hashing and ignoring it.
7. Audit every remaining `PostSelectionMethodIdentity` field against an actual consumer and either route it, reject unsupported configuration, or remove non-scientific identity state.

**R7A focused acceptance**

- same foundation bytes/head moved from path A to path B -> same canonical method identity;
- mutate foundation file bytes in place at path A -> different/failing canonical identity and prior CV authorization invalid;
- same multihead checkpoint + different explicit head -> different method identity;
- replay source moved without byte/policy/split change -> same replay lineage;
- replay source bytes changed in place -> different replay lineage;
- replay split seed/ratio changed -> different replay lineage;
- unsupported `[training].optimizer` -> pre-training rejection, not identity-only mutation;
- for every retained method field, a test or structural assertion demonstrates the real executable consumer.

Run stage-local affected regression for foundation identity, replay source/split/true-label identity, P5 identity hierarchy, CV/final plan validation, and any shared target-size consumers touched.

Do not proceed to final assembled closure with known R7A identity mismatch.

### P5-R7B — restore qualified TRAIN2/MACE launch path

**Owning/expected files**

- `mdstats/training_data/post_selection_execution.py`;
- `mdstats/training_data/campaign_post_selection_runtime.py`;
- `mdstats/training_data/train2_runtime.py` only if a small reusable public builder/loader API is needed;
- tests/fixtures.

**Required edits**

1. Replay resolution must fail closed; remove broad exception swallowing.
2. Pass the exact TRUE_DFT monitor SHA into replay-enabled `Train2RuntimePlan` construction.
3. Pass resolved target/replay head names into the runtime plan when they differ from defaults.
4. Restore `MacePostSelectionTrainer` environment injection:
   - serialized `request.plan` under `TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE`;
   - exact replay monitor path under `TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE` when enabled;
   - `PYTHONHASHSEED` from optimizer seed.
5. Read the internal P5 config, call `post_selection_mace_run_configuration()`, and write/use the translated executable MACE config.
6. Run wrapper with the materialization directory as cwd or fully absolutize every artifact path.
7. Use canonical `load_train2_runtime_summary(checkpoint_directory)` after child success.
8. Retain existing wrapper supervision rather than reimplementing MACE child supervision in P5.
9. Reauthenticate summary/plan/provider/checkpoint lineage before evaluation.

**R7B focused acceptance — production trainer contract test**

Create a bounded test around the real `MacePostSelectionTrainer` owner. It may replace the external wrapper executable with a deterministic fake executable/process shim, but it must execute the real trainer command/config/environment construction.

The fake must capture and assert:

- wrapper receives the translated executable MACE config, not the internal P5 config;
- executable config contains `train_file` / `valid_file`, canonical foundation/head fields, architecture fields, and multihead replay fields when required;
- `MDSTATS_TRAIN2_RUNTIME_PLAN` parses exactly to `request.plan`;
- replay-enabled run includes `MDSTATS_TRAIN2_TRUE_REPLAY_PATH` and the file SHA equals `request.plan.true_replay_monitor_sha256`;
- replay-disabled run does not require a replay path and plan contains no replay SHA;
- cwd/path resolution points at the materialized artifacts;
- trainer uses the canonical checkpoint-directory TRAIN2 summary loader;
- missing/tampered summary fails even if wrapper return code is zero;
- nonzero wrapper return code fails with useful stderr/context.

This test must fail if the production trainer again omits the TRAIN2 environment, bypasses the translator, or looks for a P5-only summary filename.

Run affected TRAIN2 runtime/wrapper/config/provider regression after this stage.

### P5-R7C — real replay baseline/admissibility and assembled closure

**Owning/expected files**

- `mdstats/training_data/campaign_post_selection_runtime.py`;
- shared provider builder only if needed;
- P5 assembled tests/fixtures.

**Required edits**

1. Replace the `SimpleNamespace` foundation baseline with the real canonical foundation provider path.
2. Reauthenticate foundation SHA/head before baseline provider construction.
3. Evaluate candidate and foundation baseline on the exact same authenticated TRUE_DFT replay monitor.
4. Use existing EVAL2 reduction and pass real candidate/baseline RMSE + TRUE_DFT label mode to `assess_eval2_checkpoint()`.
5. Fix baseline cache identity or remove the cache.
6. Ensure replay evidence remains admissibility-only before target-only ordering.
7. Ensure final M3 checkpoint choice uses the same replay admissibility contract.

**R7C assembled bounded flow**

```text
real config
 -> real CampaignStore/current P4 SELECTED authority
 -> real canonical foundation resolution
 -> real canonical replay source/split/TRUE_DFT view resolution
 -> real PostSelectionMethodIdentity + CV policy/plan
 -> real fold DATA7/DATA8 materialization
 -> real Train2RuntimePlan construction
 -> real MacePostSelectionTrainer config/environment orchestration
 -> bounded fake external numerical MACE work only
 -> real canonical TRAIN2 summary/provider authentication
 -> real EVAL2 target metrics
 -> real replay candidate + canonical foundation baseline metric path
 -> real checkpoint admissibility + target-only representative selection
 -> real held-out outer target acceptance
 -> real all-required CV authorization
 -> real final plan reauthentication of method + replay lineage
 -> fresh full-T_selected final orchestration
 -> real replay admissibility + target-only M3 selection
 -> currentness-fenced publication
 -> fresh-process reload/restart authentication
```

Allowed fakes are below the owners named above: expensive MACE numerical optimization and numerical prediction values may be deterministic bounded fakes. The real method resolver, foundation/replay authority, plan construction, materialization, trainer command/environment construction, TRAIN2 plan/summary owner, EVAL2 decision owner, CV/final authorization, persistence, restart, and currentness publication must execute.

Forbidden proxy acceptance:

- directly fabricate `Eval2CheckpointRecord` replay fields and claim runtime replay is covered;
- replace `MacePostSelectionTrainer` with the existing harness when claiming the real trainer contract is accepted;
- seed `CvCampaignAcceptance` / final authorization instead of executing fold acceptance;
- patch foundation/replay resolvers to return desired identities;
- use `SimpleNamespace` or another non-production provider for the real baseline-provider claim;
- compare only digests without inspecting the actual executable MACE config/environment;
- replace CampaignStore/currentness/restart owner when those semantics are under acceptance.

---

## 7. Mandatory negative/structural acceptance matrix

P5 revision 7 is not closed unless these claims are directly protected:

1. **foundation relocation:** identical authenticated checkpoint moved -> no scientific identity change.
2. **foundation in-place mutation:** changed bytes at same path -> stale/failing identity; old CV cannot authorize final production.
3. **foundation head:** same checkpoint with different selected head -> method identity change.
4. **replay relocation:** identical replay source/view moved -> no scientific lineage change.
5. **replay in-place mutation:** changed replay bytes at same path -> replay-lineage change; old CV cannot authorize final production.
6. **replay split mutation:** split seed/ratio/membership change invalidates CV->final replay lineage.
7. **unsupported optimizer knob:** unsupported optimizer-family input is rejected, not hashed-only.
8. **identity-only drift:** any retained method-field mutation cannot change only method digest while executable semantics remain unchanged.
9. **execution-only drift:** a material executable method change cannot occur without changing/rejecting the relevant method identity.
10. **internal-config bypass:** production trainer cannot hand `POST_SELECTION_MACE_CONFIG_SCHEMA` directly to MACE without translation.
11. **TRAIN2 environment:** production trainer must set the exact serialized runtime plan.
12. **TRUE_DFT runtime identity:** replay-enabled runtime plan SHA must equal the exact replay monitor file SHA supplied to the child.
13. **canonical summary:** production trainer must use the canonical TRAIN2 summary owner; a made-up results summary filename cannot satisfy acceptance.
14. **replay-resolution fail-closed:** malformed/missing required replay cannot become `None` and continue.
15. **real baseline provider:** production replay baseline path must expose the normal provider prediction interface and use canonical foundation/head identity.
16. **same-monitor:** candidate and baseline replay metrics must bind the same TRUE_DFT monitor identity.
17. **replay ranking:** replay can reject but cannot rank/tie-break/credit target acceptance.
18. **outer-fold isolation:** held-out outer target data cannot enter training/preparation/checkpoint/replay selection.
19. **M3 role:** M3 selects final checkpoint but is not independent validation.
20. **horizon isolation:** production horizon remains independent of target-size `n3` and CV budget.
21. **currentness:** stale P5 work cannot become current after a newer P4 generation/revision is published.
22. **no backflow:** CV/replay failure cannot invoke target-size reducer/reselection.
23. **legacy authority:** no current P5 decision edge depends on retired DATA5 label-domain CV or replay-weighted MLCV ranking.

---

## 8. Regression and integration requirements

### After R7A

Run focused identity/lineage tests and stage-local affected regression covering:

- `foundation.py` generalized foundation identity/head inspection/canonicalization;
- replay source/split/single-source/legacy normalization/TRUE_DFT view identity;
- P5 method-identity hierarchy;
- CV/final plan validation and stale authorization;
- target-size/common consumers if shared identity code changed.

### After R7B

Run focused production-trainer contract tests and affected regression covering:

- `post_selection_execution.py` materialization/config translation;
- `critical_precision_cli.py` wrapper entry behavior relevant to P5;
- TRAIN2 plan serialization/environment activation/replay loader/summary loader;
- checkpoint/provider authentication;
- P5 existing non-replay assembled paths to ensure launch repair does not regress them.

### After R7C/final assembled candidate

Re-derive the complete affected surface from the final diff and run fresh affected regression. At minimum account for:

- all still-applicable P5-A/B/C/D/E/F/G tests;
- revision-5 identity tests;
- revision-6 guard tests, corrected where a prior test encoded an accidental unsupported optimizer-family requirement;
- new R7 identity/real-trainer/replay assembled tests;
- P4 current-terminal/currentness/publication-race regression;
- foundation generalized identity/head tests;
- replay source/split/single-source/legacy normalization/TRUE_DFT-view tests;
- DATA7/DATA8 materialization/replay-role tests;
- TRAIN2 policy/runtime/environment/checkpoint/provider/continuation tests;
- critical precision wrapper tests intersecting the launch path;
- EVAL2 target/replay admissibility and target-only ordering tests;
- final-production/M3/freshness/horizon tests;
- persistence/restart/content-addressed evidence tests;
- CLI/orchestrator assembled P4 -> P5 integration.

If shared foundation/replay/TRAIN2 execution changes make the affected set uncertain, run the broader repository regression rather than assuming uninspected consumers are safe.

A required test that does not execute is not a pass. Test output or implementation notes are acceptable evidence; no new evidence database/report format is required.

### Qualification disposition

Do not run long GPU/data-heavy production qualification for this repair. Bounded CPU/available-device functional tests, deterministic wrapper/process fakes, and bounded inference fakes below the real semantic owners are appropriate. Final real-GPU/production-scale qualification remains deferred under the frozen parent.

---

## 9. Implementation authority

### Frozen

Implementation must preserve Sections 0-8. In particular:

- use canonical content-authenticated foundation identity, not path hashing;
- separate replay method policy from exact authenticated replay source/split/view lineage and enforce CV->final lineage equality;
- remove or reject unsupported identity-only optimizer-family configuration rather than creating a new capability;
- build a complete replay-enabled `Train2RuntimePlan`, including exact TRUE_DFT monitor SHA;
- use `post_selection_mace_run_configuration()` as the internal->MACE translation owner;
- launch the established `mdstats-mace-train` wrapper with the TRAIN2 plan and replay path environment;
- use the canonical TRAIN2 checkpoint-directory summary owner;
- use a real canonical foundation/head prediction provider for replay baseline evaluation;
- replay remains admissibility-only and target ordering remains target-only;
- all prior P5 CV/currentness/freshness/M3/horizon/no-backflow guarantees remain intact.

### Delegated

Implementation may choose:

- exact version-agnostic helper/class names for resolved method and replay lineage;
- whether foundation/replay resolution is cached inside one invocation after authentication;
- exact executable MACE config filename/location, provided path semantics are unambiguous and the wrapper consumes the translated config;
- whether the canonical wrapper-launch logic is factored into a shared helper used by target-size/P5 or kept in `MacePostSelectionTrainer` if there is one clear owner;
- whether foundation baseline RMSE is cached or recomputed;
- exact error wording;
- exact deterministic fake executable/prediction implementation below the frozen real-owner test boundaries.

### Reopen only on evidence

Reopen only the affected P5 design surface if repository evidence proves one of these contradictions:

1. canonical `FoundationPotentialIdentity` cannot represent the exact accepted downstream foundation/head method without changing upstream science;
2. the supported `mdstats-mace-train`/MACE 0.3.16 interface cannot execute the already-accepted post-selection method through the qualified TRAIN2 runtime;
3. canonical replay source/split/TRUE_DFT-view owners cannot supply exact replay train/monitor artifacts needed by the accepted method;
4. the existing real MACE provider cannot evaluate the canonical foundation/head on the TRUE_DFT replay monitor without changing the accepted replay scientific contract;
5. making the P5 method executable reveals that P3/P4 target-size screening used a scientifically different training method, in which case honor upstream invalidation rather than hiding the mismatch locally.

Missing helper APIs, inconvenient current factoring, failing path-hash tests, or the need to restore previously qualified launch code are not redesign triggers.

---

## 10. Exit gate

P5 revision 7 is accepted only when all of the following are simultaneously true:

> The exact current P4-selected dataset remains the sole selection authority; the shared post-selection method is identified by canonical scientific content rather than filesystem spelling; identical relocated foundation/replay inputs do not invalidate method science while changed bytes at the same path do; the exact replay source/split/TRUE_DFT lineage accepted by CV is required again for final production; every method-identity field is consumed by the real executable method or rejected/removed; every CV/final run launches the established `mdstats-mace-train` wrapper with a translated MACE configuration and the exact authenticated TRAIN2 runtime plan; replay-enabled plans bind and supply the exact TRUE_DFT monitor SHA/path; canonical TRAIN2 summary/provider authentication succeeds before EVAL2; replay candidate and canonical foundation-head baseline are evaluated through real production-capable providers on the exact same TRUE_DFT monitor; replay can only reject checkpoints and never rank them; all required selected-only CV folds/seeds pass target-only outer acceptance; and fresh full-`T_selected` final production executes exactly the CV-accepted method under independent production horizon/M3 policy without stale currentness, reverse authority, or cross-role restart collision.

After R7A and R7B stage-local semantic + functional closure, R7C fresh assembled regression/integration, and independent Software Design review pass, mark P5 implemented/accepted and commit the formal P5 closure checkpoint. P6 remains blocked until that closure.
