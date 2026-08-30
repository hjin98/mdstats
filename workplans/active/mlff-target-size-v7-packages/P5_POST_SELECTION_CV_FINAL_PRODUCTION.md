---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: active
package_revision: 10
amended_date: 2026-08-30
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision9_implementation_baseline_commit: 6eca41720acecabf0e53c2f7d30aa288b66951ce
revision8_implementation_baseline_commit: 21dac6360000d909d4c48958d87aff03850ecb42
revision7_implementation_baseline_commit: d1575a26426339d67c856ed0d66ea3e394bba30a
revision6_implementation_baseline_commit: 81e72cdb22cdbfddae0508592b2b38b3f80aae2f
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: Independent review of P5A4 found three bounded P5-local closure defects after the revision-9 replay/head/trainer repairs landed. Current replay lineage still infers missing interface/training semantics and defaults incomplete evidence to TRUE_DFT; replay configuration can coexist with scratch or naive fine-tuning even though the method identity claims separate replay training while execution omits it; and the assembled R9C test still monkeypatches MaceCalculatorProvider.from_model_path, replacing a required foundation-baseline semantic owner rather than faking below it. Revision 10 freezes fail-closed lineage, an exact training-mode/foundation/replay compatibility matrix, and the lower allowed numerical fake boundary without reopening P1-P4 or the parent scientific design.
---

# P5 revision 10 — fail-closed replay lineage, mode/exposure parity, and real provider closure

## 0. Authority, scope, and precedence

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific and architectural verdict. P5 remains bound to **Protocol 5.8.0**. Revision 10 is the current snapshot-complete P5 implementation handoff and supersedes earlier P5 revisions as task-local authority.

The implementation baseline under correction is:

```text
6eca41720acecabf0e53c2f7d30aa288b66951ce  P5A4
```

This is a **bounded P5 implementation repair**. Do not reopen P1-P4, target-size science, selected-set semantics, P1 split-exclusion authority, CV acceptance science, replay-retention science, M3's role, or final-production freshness unless evidence reaches a reopen trigger in Section 8.

P6 remains blocked until revision 10 reaches semantic/conformance closure, stage-local functional closure, final affected-surface regression/integration, and an independent P5 Software Design review pass.

Full production/GPU qualification remains deferred. P5 closure requires bounded CPU-safe functional/regression/integration evidence only.

---

## 1. Frozen P5 product semantics

### 1.1 Selection authority

- P4 `CampaignStore` current-terminal authority is the only current owner of `N_selected` and `T_selected`.
- `T_selected = pi_train[:N_selected]` exactly.
- Replay, CV, M3, final production, and all P5 descendants may not widen, redefine, or back-write the selected target set.
- P5 evidence is always descendant of the current selected binding and can never become target-size authority.

### 1.2 Cross-validation

- CV occurs only after P4 selection is current and terminal.
- CV uses configured `K >= 2`, exact selected-only coverage, and the full canonical P1 split-exclusion/protected-relation projection.
- Every required fold and every required CV seed/variant must pass. Mean/majority/best-seed/partial/K0/K1/`cv_not_performed` authorization is forbidden.
- Fold-local fitted preparation, training, checkpoint selection, and replay admissibility may not see that fold's held-out outer target set.
- Held-out outer evaluation occurs only after the representative is frozen from legal monitor/admissibility evidence.

### 1.3 Replay science

Replay has two distinct roles:

```text
replay training exposure
    = replay labels/artifact actually consumed by MACE training

TRUE_DFT replay admissibility monitor
    = independent DFT-labeled replay evidence used only to gate retention
```

- Replay training exposure is part of the shared scientific method and therefore part of `PostSelectionMethodIdentity`.
- TRUE_DFT replay admissibility is a hard checkpoint gate/diagnostic only.
- Replay may reject a checkpoint but receives zero target ranking, tie-breaking, fold acceptance, seed/committee ranking, or target-size credit.
- Candidate and canonical foundation baseline are evaluated on the exact same authenticated TRUE_DFT replay monitor through the existing EVAL2 reduction path.
- Pseudolabel training replay is never independent accuracy evidence and must never be silently replaced or relabeled as TRUE_DFT training merely because a TRUE_DFT monitor exists.

### 1.4 Final production and M3

- M3 remains development/model-selection evidence only, not independent validation.
- Final production is fresh from the full exact `T_selected`, with fresh optimizer/RNG/run state and no continuation from screening/CV checkpoint or optimizer state.
- `[training].max_num_epochs` is final-production horizon authority only and remains independent from target-size `n3` and CV budget.
- Screen/CV/final namespaces and evidence identities remain collision-proof.
- Policy -> plan -> realized evidence remains acyclic.

---

## 2. Accepted implementation state that revision 10 must preserve

The following revision-8/revision-9 repairs are accepted and must not regress.

### 2.1 Foundation identity and foundation baseline

`resolve_post_selection_foundation_identity()` remains fail-closed:

```text
existing file
 -> inspect_mace_foundation(...)
 -> MaceFoundationSpec(family, requested_head).resolve(...)
 -> inspection_state == inspected
```

No broad fallback to byte-only `FoundationPotentialIdentity.from_file()` is allowed for current P5 authorization.

Foundation invariants remain:

- omitted head remains unresolved until canonical inspection;
- singleton omitted head may resolve canonically;
- multi-head omitted head fails;
- unavailable explicit head, wrong family, corrupt/unsupported checkpoint, or inspection failure fails before training;
- runtime path is locator only;
- canonical content/head identity is scientific identity;
- relocation with identical bytes/head preserves method identity;
- changed bytes/head invalidates stale CV/final authorization.

The replay-retention baseline must continue to use `build_post_selection_foundation_baseline_provider()` -> real `MaceCalculatorProvider` ownership with the canonical foundation identity/head and the same TRUE_DFT monitor used for the candidate.

### 2.2 Replay semantic ownership

Preserve the revision-9 separation of replay roles. `PostSelectionReplayResolution` or equivalent transport may carry canonical artifacts but is not a new scientific authority.

Supported current replay training semantics are exactly:

```text
single-source or legacy external_pseudolabel
    -> training_label_mode = foundation_pseudolabel

single-source or legacy external_true_label
    -> training_label_mode = true_dft
```

Legacy unsupported/ambiguous replay modes fail before P5 training.

Replay method identity remains path-free. Exact replay bytes belong to plan lineage, not method identity. Canonical single-source lineage binds source content/SHA, split-manifest digest, training-view identity/SHA, TRUE_DFT monitor identity/SHA, and normalized label semantics. Legacy lineage binds the actual training replay identity/SHA, independent TRUE_DFT monitor identity/SHA, normalized training-label semantic, and canonical true-label source identity when the existing replay owner exposes one.

CV binds replay lineage. Final production and fresh restart re-resolve current replay lineage and require exact equality to the accepted CV lineage.

### 2.3 Canonical P5 head namespace

Current P5 fine-tuning head names remain fixed:

```python
POST_SELECTION_TARGET_HEAD_NAME = "target_head"
POST_SELECTION_REPLAY_HEAD_NAME = "pt_head"
```

- omitted or explicit `target_head` is accepted;
- any other target fine-tuning head rejects before training;
- no new replay-head option is introduced merely for P5; any existing replay-head surface must normalize to `pt_head` or reject;
- method/replay identity, `TargetSizeCommonTrainingPolicy`, `Train2RuntimePlan`, internal P5 configuration, executable MACE `heads`, and relevant summary/provider validation all use the same canonical names.

Foundation checkpoint head selection remains a separate concept owned by canonical foundation identity.

### 2.4 Identity -> execution parity and TRAIN2

Preserve:

- accepted dtypes exactly `float32` / `float64`; invalid values reject;
- accepted training modes exactly `scratch`, `naive_fine_tuning`, `multihead_replay` subject to the compatibility matrix in Section 4;
- unsupported optimizer family rejects;
- `eval_interval` is method identity and reaches the executable MACE config;
- checkpoint interval is method identity and reaches role `TrainingBudgetPolicy` / `Train2RuntimePlan`;
- acceleration is normalized through existing `MaceAccelerationPolicy`; method backend and optimizer backend must agree; canonical `training_config()` reaches `enable_cueq` / `only_cueq`;
- `post_selection_mace_run_configuration()` remains the sole internal-P5 -> parser-facing MACE translator;
- real `MacePostSelectionTrainer` authenticates internal config, target train/monitor, foundation, replay train, replay monitor, and runtime TRUE_DFT SHA before subprocess launch;
- scientific file hashing uses `sha256_file_cached` where applicable;
- wrapper cwd/environment remain production-owned, including exact `MDSTATS_TRAIN2_RUNTIME_PLAN`, optimizer-seed `PYTHONHASHSEED`, and replay-enabled `MDSTATS_TRAIN2_TRUE_REPLAY_PATH`;
- nonzero wrapper exit fails;
- successful wrapper exit without valid canonical `load_train2_runtime_summary(request.checkpoint_directory)` evidence fails;
- canonical summary plan/optimizer/budget/LR/structure geometry remains authenticated before checkpoint evaluation.

### 2.5 Assembled orchestration already corrected in P5A4

Preserve the real CLI/CampaignStore/P4 selected authority, real CV/final currentness, real `MacePostSelectionTrainer`, real replay training-vs-TRUE_DFT role separation, real target-only checkpoint selection, real final fresh-run orchestration, and fresh reopened-store restart validation introduced by the revision-9 implementation.

Do not revert to `PostSelectionHarness` as the trainer owner for the final assembled acceptance claim.

---

## 3. Revision-10 defect A — replay lineage must be fully explicit and fail closed

### 3.1 Problem

At baseline `6eca4172`, `compute_replay_lineage_digest()` still supports incomplete transport shapes by:

- inferring `interface` when it is absent; and
- defaulting missing replay training semantics to `ReplayLabelMode.TRUE_DFT` when neither the resolution nor authenticated training artifact supplies a mode.

That compatibility behavior can convert incomplete/ambiguous evidence into a current scientific lineage. It is incompatible with P5's current-generation cutover and with the frozen rule that replay training exposure is the artifact/semantic actually consumed by MACE.

### 3.2 Frozen correction

**Primary owner:** `mdstats/training_data/post_selection_identity.py`

Current P5 `compute_replay_lineage_digest()` must require explicit authenticated state. Do not infer scientific meaning from object shape.

Required preconditions:

```text
interface is explicitly one of:
    single_source
    legacy_split

train_artifact exists
monitor_artifact exists
training_label_mode exists and is one of:
    true_dft
    foundation_pseudolabel
true_label_mode exists/resolves to exactly true_dft
```

The training artifact's label mode, when the artifact exposes one, must equal normalized `training_label_mode`. The monitor artifact's label mode, when exposed, must equal `true_dft`. Any disagreement or missing required semantic raises `PostSelectionError` / `TrainingDataInputError`; there is no semantic fallback.

For all current lineage inputs require path-independent content identity plus bytes:

```text
train_artifact:
    content_digest or canonical logical_digest
    sha256

monitor_artifact:
    content_digest or canonical logical_digest
    sha256
```

For `single_source`, additionally require:

```text
source_content_digest
source_sha256
split_manifest_digest
```

Do not use `source_sha256` as a substitute for a missing `source_content_digest` if the canonical `ReplaySourceArtifact` owns a content digest. Missing canonical identity is a hard error.

For `legacy_split`, bind normalized training label mode, train identity/SHA, TRUE_DFT monitor identity/SHA, and canonical separate true-label source identity when the existing replay owner exposes it. Do not invent a path-based replacement for absent source identity.

No lineage payload contains filesystem paths.

### 3.3 Compatibility disposition

P5's declared compatibility policy is `current-generation-cutover-no-derived-migration`. Therefore:

- incomplete R8/R9-shaped helper objects are **not** valid current P5 authorization evidence;
- no TRUE_DFT default is retained merely to keep old guard fixtures green;
- no interface inference is retained merely to deserialize helper-shaped evidence;
- persisted old CV/final evidence that cannot reauthenticate under the current explicit lineage is stale and must be recomputed rather than upgraded by assumption.

This does not require migration of authoritative user data. It is derived P5 evidence invalidation.

### 3.4 R10A direct acceptance

Tests must execute the actual lineage owner and prove:

1. missing `interface` rejects;
2. unsupported `interface` rejects;
3. missing `training_label_mode` rejects even if train/monitor SHA fields exist;
4. missing train or monitor content identity/SHA rejects;
5. single-source missing source content digest, source SHA, or split-manifest digest rejects;
6. training semantic mismatching authenticated train artifact rejects;
7. non-TRUE_DFT monitor semantic rejects;
8. complete single-source and complete legacy lineage remain path-independent under relocation;
9. training bytes, monitor bytes, source bytes, or split membership changes invalidate lineage as appropriate;
10. existing R8/R9 tests are updated to construct semantically complete canonical artifacts/resolutions rather than relying on implicit defaults.

Do not weaken production validation to preserve an old test shape.

---

## 4. Revision-10 defect B — exact training-mode / foundation / replay compatibility

### 4.1 Problem

At baseline `6eca4172`, replay configuration can make `replay_exposure_policy_digest` claim `training_exposure="separate_multihead_replay"` while an explicit `scratch` or `naive_fine_tuning` training mode remains accepted. Execution enables MACE multihead replay only when `training_mode == "multihead_replay"`.

This permits identity to claim replay training that the executable method does not perform.

### 4.2 Frozen current-P5 compatibility matrix

Current P5 has exactly three supported scientific training modes and one legal foundation/replay topology for each:

| training mode | foundation checkpoint | replay training source | independent TRUE_DFT monitor | executable replay training |
| --- | --- | --- | --- | --- |
| `scratch` | absent | absent | absent | no |
| `naive_fine_tuning` | required | absent | absent | no |
| `multihead_replay` | required | required | required | yes |

Any other combination is invalid and must fail during canonical method-policy resolution **before** CV plan construction, materialization, or wrapper launch.

Specifically:

- `scratch` + configured foundation -> reject;
- `scratch` + any P5 replay source/path/config -> reject;
- `naive_fine_tuning` without foundation -> reject;
- `naive_fine_tuning` + any P5 replay source/path/config -> reject;
- `multihead_replay` without foundation -> reject;
- `multihead_replay` without canonical replay training source -> reject;
- `multihead_replay` without resolvable independent TRUE_DFT monitor -> reject before executable training;
- replay source configured while mode is not `multihead_replay` -> reject rather than silently treating replay as monitor-only.

Do **not** add a fourth "replay-admissibility-only" training mode or reinterpret existing modes in this repair. That would be a product-semantic redesign.

### 4.3 Canonical owner and implementation consequence

**Primary owner:** `resolve_post_selection_method_policies()` in `post_selection_identity.py` (or one existing policy-normalization helper called uniquely by it).

Resolve in this order:

```text
canonical replay interface/semantic presence
canonical training_mode
canonical foundation identity/presence
validate compatibility matrix
construct shared method/replay policy identity
```

No downstream caller may need to repair an illegal combination.

Required identity/execution invariant:

```text
method training_mode == multihead_replay
    <=> replay_exposure_policy says separate_multihead_replay
    <=> canonical replay training resolution exists
    <=> MACE multiheads_finetuning is true
    <=> executable config carries pt_train_file + canonical pt_head
```

For `scratch` and `naive_fine_tuning`, the shared replay policy is the stable disabled/no-replay policy and no replay TRAIN2/MACE fields may be emitted.

The independent TRUE_DFT monitor is mandatory only for `multihead_replay` under current P5. It remains admissibility-only and receives zero target ranking credit.

### 4.4 R10A compatibility acceptance

Direct tests through `resolve_post_selection_method_policies()` and assembled materialization must prove all legal/illegal matrix cells.

At minimum:

- legal scratch resolves with no foundation/replay identity and produces non-multihead config;
- legal naive fine-tuning resolves canonical foundation identity, no replay exposure, and produces non-multihead config;
- legal multihead replay resolves canonical foundation + replay training + TRUE_DFT monitor and produces exact `pt_train_file` / `pt_valid_file` / `pt_head` semantics;
- every illegal matrix combination above rejects before materialization;
- a campaign cannot change from accepted multihead CV to naive/scratch and retain final authorization;
- a campaign cannot add replay configuration to accepted naive/scratch CV without invalidating/rejecting the current method;
- method/replay identity and executable MACE mode cannot disagree under any supported configuration.

---

## 5. Revision-10 defect C — assembled foundation-provider owner must remain real

### 5.1 Problem

The P5A4 assembled replay-enabled/non-scratch test correctly leaves `MacePostSelectionTrainer` real and fakes the external numerical wrapper below it, but it monkeypatches `MaceCalculatorProvider.from_model_path` for the foundation replay baseline.

That replaces a required semantic owner. The test could remain green while real provider construction/head/identity validation is broken.

### 5.2 Frozen real-owner boundary

The final assembled test must execute production code through:

```text
build_post_selection_foundation_baseline_provider(...)
 -> MaceCalculatorProvider.from_model_path(...)
 -> provider object accepted by real P5/EVAL2 orchestration
```

These functions/classes are **inside** the acceptance boundary and may not be monkeypatched/replaced for the R10 assembled claim:

- `build_post_selection_foundation_baseline_provider`;
- `MaceCalculatorProvider.from_model_path`;
- P5 foundation identity resolver/spec/head resolution;
- provider identity/head/dtype/backend validation performed by those owners;
- replay baseline cache-key construction;
- EVAL2 reduction/admissibility orchestration.

### 5.3 Allowed bounded fake boundary

Expensive numerical MACE work may still be replaced **below** `MaceCalculatorProvider.from_model_path`.

Acceptable approaches include a deterministic fake at the lowest MACE-library/model-loading or forward-calculation dependency that lets `from_model_path()` itself execute its real mdstats validation/control path. Exact helper choice is delegated to Implementation based on the existing provider internals.

The allowed fake must not:

- directly return a preconstructed `MaceCalculatorProvider` from a monkeypatched `from_model_path`;
- bypass checkpoint SHA/canonical foundation identity checks;
- bypass requested/canonical head validation;
- bypass provider dtype/backend/inference-identity construction that `from_model_path` owns;
- fabricate post-provider EVAL2 records or replay metrics.

If a tiny real test checkpoint already allows real provider construction cheaply on CPU, prefer it over patching internals.

### 5.4 R10B assembled lifecycle

Retain the revision-9 non-scratch replay-enabled lifecycle and strengthen only the fake boundary. One bounded test must traverse:

```text
real campaign config
 -> real CampaignStore/current P4 SELECTED authority
 -> real method policy/identity resolution
 -> real canonical foundation inspection/spec/head
 -> real canonical replay training + independent TRUE_DFT monitor resolution
 -> real fail-closed replay lineage
 -> real CV plan/folds from selected/P1 authority
 -> real DATA7/DATA8 preparation/materialization
 -> real Train2RuntimePlan
 -> real MacePostSelectionTrainer
      -> real prelaunch authentication/config/env/cwd
      -> fake external numerical training wrapper below trainer
 -> real canonical TRAIN2 summary/checkpoint authentication
 -> real candidate provider authentication
 -> real build_post_selection_foundation_baseline_provider
 -> real MaceCalculatorProvider.from_model_path
      -> bounded fake only below provider semantic owner if necessary
 -> real EVAL2 candidate + foundation replay evaluation on same TRUE_DFT monitor
 -> real target-only representative selection
 -> real held-out outer acceptance
 -> real all-required CV campaign acceptance
 -> real final method/replay-lineage reauthentication
 -> fresh full-T_selected final orchestration
 -> real M3 development semantics
 -> real currentness-fenced publication
 -> fresh context/reopened CampaignStore restart reauthentication
```

The test remains invalid if it injects a precomputed replay lineage, seeds `CvCampaignAcceptance`/final authorization, replaces `MacePostSelectionTrainer`, replaces `MaceCalculatorProvider.from_model_path`, bypasses CampaignStore/currentness/restart, or directly fabricates post-decision EVAL2 metrics.

### 5.5 Provider counterfactuals

The assembled/focused provider tests must prove that production provider ownership would catch at least:

- foundation bytes changed after canonical identity resolution;
- wrong/unavailable foundation head;
- identity/head mismatch between P5 method and provider construction;
- provider construction failure propagates and prevents replay-baseline admissibility from being synthesized;
- candidate and foundation replay evaluations use exactly the same authenticated TRUE_DFT monitor identity/SHA.

Numerical force values may remain deterministic substitutes below the provider/EVAL2 semantic owners.

---

## 6. Implementation stages

### P5-R10A — fail-closed lineage and mode/exposure parity

**Expected affected files**

- `mdstats/training_data/post_selection_identity.py`
- `mdstats/training_data/campaign_post_selection_runtime.py` only if runtime assertions/adapters need tightening
- replay/P5 guard tests

**Required edits**

1. Remove current P5 interface inference in replay lineage.
2. Remove implicit TRUE_DFT training-label fallback.
3. Require canonical explicit lineage identities/semantics and fail on missing state.
4. Enforce the exact scratch/naive/multihead foundation/replay compatibility matrix before method identity construction.
5. Ensure replay policy identity and executable training mode are biconditionally aligned.
6. Update old helper-shaped guards instead of retaining production compatibility fallbacks for them.

**Stage closure**

Run focused R10A tests plus affected replay single-source/legacy, P5 identity, CV-plan/final-plan/currentness, DATA8 materialization, TRAIN2 plan/config, and restart regression. Do not proceed to R10B with a new affected failure.

### P5-R10B — real provider assembled closure

**Expected affected files**

- `tests/test_mlff_target_size_p5_r9_guards.py` or successor revision-10 guard file;
- bounded test support around the existing MACE provider's lower numerical seam;
- production provider code only if the stronger real-owner test exposes a genuine implementation consequence already implied by this contract.

**Required edits**

1. Remove monkeypatch/replacement of `MaceCalculatorProvider.from_model_path` from the assembled acceptance test.
2. Keep `build_post_selection_foundation_baseline_provider` and provider construction real.
3. Move any numerical fake below provider semantic ownership or use a tiny real CPU-safe checkpoint.
4. Retain the real trainer + fake external training-wrapper boundary already established by P5A4.
5. Execute the complete assembled chain in Section 5 on the same candidate used for final regression.

**Stage closure**

The strengthened R10B assembled integration and focused provider counterfactuals must pass before final package regression.

---

## 7. Final acceptance and affected-surface regression

All previously accepted P5 obligations remain binding. Final completion must establish, on one assembled candidate:

### 7.1 Scientific/configuration identity

- canonical fail-closed foundation identity/head;
- path-free replay method identity;
- explicit fail-closed replay lineage with no inferred interface or default label semantic;
- pseudolabel versus TRUE_DFT training semantics remain distinct;
- exact mode/foundation/replay compatibility matrix;
- canonical `target_head` / `pt_head` parity;
- method identity changes or configuration rejects whenever executable scientific semantics change.

### 7.2 Execution/authentication

- target/foundation/replay scientific inputs authenticate before wrapper launch;
- replay training artifact exposed to MACE matches method training semantics;
- independent TRUE_DFT monitor exposed to TRAIN2/EVAL2 remains separate and authenticated;
- `eval_interval`, checkpoint interval, optimizer, dtype, acceleration, head names, training mode, foundation, and replay semantics reach the appropriate real execution owners;
- canonical TRAIN2 summary/checkpoint/provider authentication remains mandatory.

### 7.3 CV/final/restart science

- replay receives zero target-ranking credit;
- outer CV target data cannot select the checkpoint it evaluates;
- every required fold/seed is mandatory;
- accepted CV method + replay lineage is exactly the method + replay lineage final production reauthenticates;
- final production remains fresh full-`T_selected` training;
- M3 remains development-only;
- current P4 generation races reject stale publication;
- restart reauthenticates selected binding, method, foundation/head, replay lineage, canonical head namespace, accepted CV, and final plan.

### 7.4 Real-owner acceptance

- assembled non-scratch replay-enabled lifecycle uses real `MacePostSelectionTrainer`;
- assembled foundation replay baseline uses real `build_post_selection_foundation_baseline_provider` and real `MaceCalculatorProvider.from_model_path`;
- only external/low-level expensive numerical dependencies below those owners are faked;
- a defect in trainer/provider/currentness/lineage semantic owners would make the assembled evidence fail.

### 7.5 Minimum final regression surface

After all revision-10 executable edits, re-derive the affected surface. At minimum run bounded regression covering:

- revision-10 focused and assembled guards;
- prior revision-9/revision-8 guards for still-binding obligations, corrected where old fixture shape relied on removed fallbacks;
- P4 selected/currentness/stale-generation fencing;
- foundation inspection/head/provider construction;
- replay single-source and supported legacy pseudolabel/TRUE_DFT paths;
- replay source/split/train/TRUE_DFT lineage and relocation/tamper behavior;
- common DATA7/DATA8 preparation/materialization;
- MACE config, optimizer, eval/checkpoint intervals, acceleration;
- TRAIN2 runtime/environment/wrapper/summary/checkpoint/provider authentication;
- EVAL2 target/replay admissibility and target-only ordering;
- CV fold/seed/outer-holdout/all-required acceptance;
- final production/M3/fresh-run semantics;
- persistence/current pointers/restart;
- CLI/orchestrator `cross-validate` and `train-production` entrypoints.

If impact cannot be confidently bounded, run the broader available MLFF training-data regression suite.

A required check that does not execute is not a pass. No GitHub CI status is required if the repository does not provide one, but Implementation must report the actually executed regression/integration commands and results. Green helper tests cannot substitute for missing real-owner execution.

Do **not** run long production/GPU qualification for this package.

---

## 8. Completion conditions and design-reopen triggers

P5 revision 10 may be marked implemented only when all are true:

```text
semantic/conformance closure
+ canonical foundation behavior preserved
+ replay lineage fully explicit and fail closed
+ no implicit current-P5 lineage compatibility fallback
+ exact scratch/naive/multihead foundation/replay compatibility
+ replay method identity == replay execution semantics
+ canonical target_head/pt_head parity
+ all scientific training inputs authenticate before wrapper launch
+ qualified TRAIN2 path preserved
+ real candidate/foundation replay admissibility path preserved
+ real MaceCalculatorProvider.from_model_path exercised in assembled acceptance
+ stage-local R10A regression passed
+ R10B assembled real-owner integration passed
+ final affected-surface regression/integration passed
```

### Reopen Design only on evidence

Reopen only the affected P5 design surface if repository evidence proves one of these assumptions false:

- a governed current product contract requires replay configuration to coexist with `scratch` or `naive_fine_tuning` as an admissibility-only mode, so the frozen compatibility matrix would remove a supported capability;
- canonical replay owners cannot expose explicit training/interface/source/split identities without material replay-architecture change;
- a real `MaceCalculatorProvider.from_model_path` cannot be exercised in a bounded CPU-safe test while keeping the fake below provider semantics, and closing that boundary would require production provider architecture changes;
- a revision-10 correction conflicts irreconcilably with the frozen parent/P1-P4 contract.

Absent such evidence, all remaining work is implementation repair under this workplan, not redesign.
