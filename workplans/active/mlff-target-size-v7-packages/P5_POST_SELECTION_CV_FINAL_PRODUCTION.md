---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: active
package_revision: 9
amended_date: 2026-08-30
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
revision8_implementation_baseline_commit: 21dac6360000d909d4c48958d87aff03850ecb42
revision7_implementation_baseline_commit: d1575a26426339d67c856ed0d66ea3e394bba30a
revision6_implementation_baseline_commit: 81e72cdb22cdbfddae0508592b2b38b3f80aae2f
compatibility_policy: current-generation-cutover-no-derived-migration
reconciliation_reason: Independent review of the revision-8 implementation found three bounded P5-local closure defects after the major revision-8 fixes landed successfully. Legacy split-file replay still collapses pseudolabel and TRUE_DFT training semantics into one method identity and risks conflating training replay with the independent TRUE_DFT admissibility monitor; configurable P5 target-head identity can diverge from the hard-coded executable MACE head map; and the required assembled acceptance test still substitutes PostSelectionHarness for MacePostSelectionTrainer and exercises scratch/no-replay rather than the required non-scratch replay-enabled owner chain. Revision 9 freezes exact repairs and proxy-proof acceptance without reopening P1-P4 or the parent scientific design.
---

# P5 revision 9 — legacy replay semantics, head-name parity, and real-owner assembled closure

## 0. Authority, scope, and precedence

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the scientific and architectural verdict. P5 remains bound to **Protocol 5.8.0**. Revision 9 is the current P5 implementation handoff and supersedes earlier P5 revisions as the task-local authority. All still-binding P5 semantics are restated below so implementation does not need prior chat or superseded workplans to reconstruct the target.

The implementation baseline under correction is:

```text
21dac6360000d909d4c48958d87aff03850ecb42  P5A3
```

This is a **bounded P5 implementation repair**. Do not reopen P1-P4, target-size science, selected-set semantics, P1 split-exclusion authority, CV acceptance science, replay-retention science, M3's role, or final-production freshness unless repository evidence meets a reopen trigger in Section 9.

P6 remains blocked until revision 9 reaches semantic closure, functional closure, final affected-surface regression/integration, and an independent P5 Software Design review pass.

Full production/GPU qualification remains deferred. This package requires bounded functional, regression, and integration evidence only; it must not consume long target-machine production workloads merely to close P5.

---

## 1. Frozen P5 product semantics

The implementation must preserve all of the following.

### 1.1 Selection authority and selected data

- P4 `CampaignStore` current-terminal authority is the only current owner of `N_selected` and `T_selected`.
- `T_selected = pi_train[:N_selected]` exactly.
- Replay, CV, M3, final production, or any post-selection helper may not widen, redefine, or back-write the selected target set.
- P5 evidence is a descendant of the current P4 selected binding; it can never become target-size authority.

### 1.2 Cross-validation

- CV occurs only after P4 selection is current and terminal.
- CV uses configured `K >= 2`, exact selected-only coverage, and the full canonical P1 split-exclusion/protected-relation projection.
- Every required fold and every required CV seed/variant must pass.
- Mean, majority, best-seed, partial-fold, K0/K1, or `cv_not_performed` authorization is forbidden.
- Fold-local fitted preparation, training, checkpoint choice, and replay admissibility may not see that fold's held-out outer target set.
- The held-out outer set evaluates a representative already frozen from the fold's legal monitor/admissibility evidence.

### 1.3 Replay science

Replay has two distinct responsibilities that must never be conflated:

```text
replay training exposure
    = the replay labels/artifact actually consumed by MACE training

TRUE_DFT replay admissibility monitor
    = independent DFT-labeled replay evidence used to measure retention
```

- Replay training exposure is part of the shared scientific method and therefore part of `PostSelectionMethodIdentity`.
- TRUE_DFT replay admissibility is a hard checkpoint gate/diagnostic only.
- Replay may reject a checkpoint but receives **zero target-ranking, tie-breaking, fold-acceptance, seed-ranking, committee-ranking, or target-size-selection credit**.
- Candidate and foundation baseline must be evaluated on the exact same authenticated TRUE_DFT replay monitor through the existing EVAL2 reduction path.
- Pseudolabel training replay is not independent accuracy evidence and must never be silently relabeled TRUE_DFT merely because a TRUE_DFT evaluation view exists.

### 1.4 M3 and final production

- M3 remains development/model-selection evidence only, not independent validation.
- Final production is fresh from the full exact `T_selected`.
- Final runs use fresh optimizer/RNG/run state and do not continue from screening or CV checkpoints/optimizer state.
- `[training].max_num_epochs` is the sole final-production horizon authority and remains independent of target-size `n3` and the CV budget.
- Screen/CV/final namespaces and run identities remain collision-proof.
- Policy -> plan -> realized evidence remains acyclic.

---

## 2. Revision-8 repairs that are already accepted and must not regress

Revision 9 does **not** reopen these implementations. Preserve them unless a direct dependency of the three revision-9 fixes requires a local mechanical adjustment.

### 2.1 Canonical foundation identity

`resolve_post_selection_foundation_identity()` must continue to:

```text
Path.exists/file check
 -> inspect_mace_foundation(...)
 -> MaceFoundationSpec(family, requested_head).resolve(inspection)
 -> require inspection_state == "inspected"
```

There is no broad `except Exception` fallback to `FoundationPotentialIdentity.from_file()` for current P5 authorization.

Foundation rules remain:

- omitted head remains `None` until canonical inspection;
- singleton model may resolve its canonical singleton head;
- multi-head model with omitted head fails closed;
- unavailable explicit head fails closed;
- wrong family/corrupt checkpoint/inspection failure fails before training;
- runtime foundation path is a locator only;
- scientific identity is `FoundationPotentialIdentity.canonical_content_digest` plus canonical head/spec semantics;
- same bytes/head moved to a new path preserve method identity;
- changed bytes or canonical head invalidate stale CV.

### 2.2 Path-free replay scientific identity and plan lineage

For canonical single-source replay, the shared replay-policy digest remains path-free and binds normalized semantic policy only: enabled state, interface, training exposure/label mode, split policy, required TRUE_DFT monitor semantics, and canonical P5 head names.

Exact replay bytes belong to plan lineage, not the shared method identity. Single-source lineage must continue to bind at least:

- canonical replay-source content identity and SHA-256;
- `ReplaySplitManifest.content_digest`;
- replay training-view logical/content identity and file SHA-256;
- TRUE_DFT replay monitor-view logical/content identity and file SHA-256;
- normalized label semantics.

Missing required identities fail closed. No path hash, `None` placeholder, or exception-swallowing fallback may weaken lineage.

### 2.3 Identity -> execution parity already repaired

Preserve the following:

- invalid dtype rejects; accepted current values are exactly `float32` and `float64`;
- explicit unsupported training mode rejects; accepted P5 modes are exactly `scratch`, `naive_fine_tuning`, and `multihead_replay`;
- unsupported optimizer family remains rejected rather than being represented as an identity-only knob;
- `eval_interval` remains in shared method identity and reaches the internal P5 config and translated MACE config;
- acceleration remains normalized through existing `MaceAccelerationPolicy` / `MaceOptimizerPolicy.acceleration_policy` ownership;
- method `acceleration_backend` equals the canonical backend value;
- `_optimizer_policy_for()` fails closed if the run optimizer backend disagrees with the method;
- `optimizer_policy.acceleration_policy.training_config()` reaches MACE as the canonical `enable_cueq` / `only_cueq` realization;
- `checkpoint_interval_epochs` remains routed through CV/final `TrainingBudgetPolicy` -> `Train2RuntimePlan`, not an invented MACE knob.

### 2.4 Final pre-launch scientific-file authentication

`PostSelectionRungRequest` and real `MacePostSelectionTrainer` must continue to carry/authenticate enough canonical state to verify, before child launch:

1. internal P5 config bytes, SHA/digest, and schema;
2. target training ExtXYZ bytes against its materialization artifact;
3. target validation/checkpoint-monitor ExtXYZ bytes against its materialization artifact;
4. foundation checkpoint bytes against canonical foundation SHA for non-scratch methods;
5. foundation locator/head agreement between request and internal config;
6. replay training artifact/path bytes for multihead replay;
7. replay monitor artifact/path bytes when exposed to TRAIN2/MACE;
8. `request.plan.true_replay_monitor_sha256` against the same authenticated TRUE_DFT monitor.

Any disagreement raises `PostSelectionExecutionError` with **zero wrapper launches**. Scientific files use `sha256_file_cached`; do not add whole-file `read_bytes()` hashing for large artifacts.

### 2.5 Qualified TRAIN2/MACE launch and replay baseline

Preserve:

- `post_selection_mace_run_configuration()` as the one internal-P5 -> parser-facing MACE translation owner;
- executable `mace_run_config.yaml` rather than handing the internal P5 schema directly to MACE;
- wrapper `cwd=request.materialization_directory` while artifact paths are materialization-relative;
- copied `os.environ` plus canonical `MDSTATS_TRAIN2_RUNTIME_PLAN`;
- `PYTHONHASHSEED` equal to optimizer seed;
- replay-enabled `MDSTATS_TRAIN2_TRUE_REPLAY_PATH` equal to the exact authenticated TRUE_DFT replay monitor path;
- runtime plan carrying exact replay monitor SHA and correct target/replay head names;
- nonzero wrapper exit fails closed;
- wrapper success without valid canonical `load_train2_runtime_summary(request.checkpoint_directory)` evidence fails closed;
- summary plan/optimizer/budget/LR/structure geometry is authenticated before checkpoint evaluation;
- existing wrapper completion/signal supervision remains authoritative;
- foundation replay baseline uses real `MaceCalculatorProvider`/existing provider ownership, canonical foundation identity/head, and the exact same TRUE_DFT replay monitor as candidate;
- replay baseline cache identity remains content/head/monitor/evaluation-policy/dtype/backend based rather than path based.

---

## 3. Revision-9 defect A — legacy replay method identity and executable training semantics

### 3.1 Problem

At baseline `21dac636`, legacy split-file replay is represented by a single boolean `has_legacy_replay`, and `resolve_post_selection_replay_policy_digest()` hardcodes `training_label_mode="true_dft"` for every legacy replay configuration.

That is wrong because the supported legacy replay contract distinguishes at least:

```text
[replay].mode = "external_pseudolabel"
    -> MACE trains from foundation-pseudolabeled replay

[replay].mode = "external_true_label"
    -> MACE trains from the canonical TRUE_DFT replay training view
```

Those are scientifically different methods and must not share `PostSelectionMethodIdentity`.

A second risk follows from the current orchestration's use of the TRUE_DFT replay resolver: obtaining the independent TRUE_DFT admissibility monitor must not silently replace pseudolabel replay **training** with TRUE_DFT replay training.

### 3.2 Frozen correction: one normalized replay-training semantic

**Primary owners:**

- `mdstats/training_data/post_selection_identity.py`
- `mdstats/training_data/campaign_post_selection_runtime.py`
- existing canonical replay/configuration owners in `replay.py` and `_campaign_cli_core.py`

Do not create a second replay mode enum or a P5-specific interpretation of legacy files. Consume the repository's existing `ReplayMode`, `ReplayLabelMode`, single-source config, and canonical replay artifact resolvers.

Resolve one normalized P5 replay-training semantic before method identity is constructed. It must distinguish at least:

```text
no replay
    enabled = false
    training_label_mode = none

single-source replay
    training_label_mode = canonical ReplaySingleSourceConfig.label_mode

legacy external_pseudolabel
    training_label_mode = foundation_pseudolabel

legacy external_true_label
    training_label_mode = true_dft
```

For another legacy mode (`none`, `mp_shortcut`, `preselected`, or future values), do **not** guess. If an existing canonical replay owner currently resolves that mode to one unambiguous supported training artifact/label semantic, consume that owner. Otherwise reject the configuration before CV/training with `TrainingDataInputError`/`PostSelectionError`.

Conflicting replay configuration forms remain errors. The semantic digest must contain no filesystem paths.

### 3.3 Required shared replay-policy payload

Refactor `resolve_post_selection_replay_policy_digest()` as needed so it receives the normalized replay semantic rather than merely `has_legacy_replay: bool`.

For legacy split replay, the payload must be equivalent to:

```python
{
    "schema": "mdstats.post-selection-replay-policy.v3",
    "enabled": True,
    "interface": "legacy_split",
    "training_exposure": "separate_multihead_replay",
    "training_label_mode": <normalized ReplayLabelMode value>,
    "true_dft_monitor_required": True,
    "target_head_name": POST_SELECTION_TARGET_HEAD_NAME,
    "replay_head_name": POST_SELECTION_REPLAY_HEAD_NAME,
}
```

Include any other already-supported semantic policy field only when it materially changes replay training. **Do not include** `replay_train`, `replay_monitor`, `replay_true_labels`, `replay_set`, source directories, or other locators.

Changing only file location with identical bytes/semantics must preserve method identity. Changing pseudolabel <-> TRUE_DFT training semantics must change the method identity before any training runs.

### 3.4 Frozen correction: training replay and TRUE_DFT monitor are separate resolved roles

P5 orchestration must carry two conceptually distinct products, even if an existing canonical resolver returns them together:

```text
ReplayTrainingResolution
    train_path
    train_artifact
    normalized training_label_mode

ReplayTrueDftMonitorResolution
    monitor_path
    monitor_artifact
    label_mode = true_dft
```

Do not invent new persisted classes if existing replay owners already expose these values. A small P5 adapter/dataclass is acceptable only as a transport wrapper around canonical artifacts; it must not become a new scientific authority.

Required behavior:

- `multihead_replay` MACE `pt_train_file` is built from the canonical **training** replay artifact selected by configured replay mode.
- For legacy `external_pseudolabel`, MACE must continue to train from pseudolabeled replay even when a separate TRUE_DFT replay source exists for admissibility.
- For legacy `external_true_label`, MACE uses the canonical TRUE_DFT training replay artifact.
- `MDSTATS_TRAIN2_TRUE_REPLAY_PATH`, candidate replay evaluation, and foundation-baseline replay evaluation use the exact independent TRUE_DFT **monitor** artifact.
- TRUE_DFT monitor resolution may never mutate the shared training-label semantic.

If the current `_resolve_true_label_replay_inputs(..., require_train=True)` API returns only TRUE_DFT train/monitor views and cannot also identify the configured training replay artifact, do not force it to serve both roles. Reuse the existing DATA8/replay training artifact resolver for training exposure and keep `_resolve_true_label_replay_inputs` (or an equivalent shared owner) for independent TRUE_DFT admissibility evidence.

### 3.5 Legacy replay lineage

Plan-level replay lineage must bind the exact artifacts actually governing both roles.

For supported legacy replay, include at least:

```text
schema/interface = legacy_split
normalized training_label_mode
training replay logical/content digest + file SHA256
TRUE_DFT monitor logical/content digest + file SHA256
canonical separate true-label artifact/source identity when the existing replay owner exposes one
```

Do not include paths.

For single-source replay, retain the revision-8 source/split/train/TRUE_DFT-monitor lineage. If training pseudolabel materialization introduces a distinct canonical training-view identity, include it rather than incorrectly treating the TRUE_DFT train view as the training artifact.

CV plans bind this lineage. Final production and restart must re-resolve current replay training + TRUE_DFT monitor lineage and require exact equality to the accepted CV plan.

### 3.6 R9A acceptance

Direct tests must prove the **production owners**, not helper-shaped `SimpleNamespace` payloads alone:

1. same legacy replay bytes/split with `external_pseudolabel` versus `external_true_label` -> different `PostSelectionMethodIdentity`;
2. legacy pseudolabel MACE materialization points `pt_train_file` to the canonical pseudolabel training artifact;
3. legacy TRUE_DFT mode points `pt_train_file` to the canonical TRUE_DFT training artifact;
4. both modes use the independent authenticated TRUE_DFT replay monitor for admissibility;
5. switching replay training mode after accepted CV prevents final authorization;
6. relocating identical legacy files without semantic change preserves method identity and lineage;
7. changing training replay bytes or TRUE_DFT monitor bytes invalidates lineage/fails currentness;
8. unsupported or ambiguous legacy replay mode fails before materialization/training.

After R9A, run focused tests plus affected replay/P5 identity/CV-plan/final-plan regression before proceeding to R9B.

---

## 4. Revision-9 defect B — one authoritative P5 fine-tuning head namespace

### 4.1 Problem

At baseline `21dac636`, method/replay identity and `Train2RuntimePlan.target_head_name` may consume configurable `[training].selected_head_name`, while `_post_selection_mace_config()` hardcodes the actual MACE multihead map as `"target_head"` and `"pt_head"`.

Therefore identity/runtime control can name one target head while executable MACE trains another.

Foundation checkpoint head selection is a separate concept and remains governed by canonical `FoundationPotentialIdentity.foundation_head`. Do not conflate foundation head with the P5 fine-tuning head namespace.

### 4.2 Frozen correction: current P5 uses fixed canonical fine-tuning head names

Use one canonical owner for current P5 fine-tuning head names:

```python
POST_SELECTION_TARGET_HEAD_NAME = "target_head"
POST_SELECTION_REPLAY_HEAD_NAME = "pt_head"
```

The constants may live in `post_selection_identity.py` or another existing P5 policy owner with no import cycle. Do not duplicate string literals across method resolution, runtime-plan construction, and executable configuration once this correction lands.

Current-generation P5 does **not** need arbitrary fine-tuning head names. Therefore:

- omitted `[training].selected_head_name` -> canonical `target_head`;
- explicit `[training].selected_head_name = "target_head"` -> accepted and scientifically identical to omission;
- any other non-empty target-head value -> fail closed before plan/materialization/training;
- if a replay-head configuration surface already exists, omitted/`pt_head` is accepted and any other value rejects; do not introduce a new user-facing replay-head option merely for this repair.

### 4.3 Required consumers

The same canonical constants must drive:

- shared replay policy digest;
- `TargetSizeCommonTrainingPolicy.selected_head_name` or equivalent method policy field;
- `Train2RuntimePlan.target_head_name` / `replay_head_name`;
- internal P5 multihead config;
- `_post_selection_mace_config()` `heads` mapping keys;
- any provider/summary/head validation that compares run semantics with checkpoint evidence.

Required invariant:

```text
method target/replay head names
== Train2RuntimePlan target/replay head names
== executable MACE heads mapping keys
```

No string rewrite/fallback may occur after method identity is frozen.

### 4.4 R9B direct acceptance and repair of proxy guards

Repair the revision-8 guard suite so the following claims execute their actual production owners rather than manually reproducing the desired assertion:

- `eval_interval`: build the real canonical optimizer policy -> `_post_selection_mace_config()` -> `post_selection_mace_run_configuration()`; changing `eval_interval` must change method identity and the executable config value.
- checkpoint interval: mutate the config and traverse method identity -> real CV/final `TrainingBudgetPolicy` -> `Train2RuntimePlan` checkpoint policy/interval semantics.
- acceleration: resolve actual configured acceleration -> method policies -> actual `_optimizer_policy_for()` -> internal config -> translated MACE config; assert canonical training config.
- backend mismatch: call the actual mismatch owner; do not manually compare fields and `raise PostSelectionError` inside the test.
- runtime TRUE_DFT mismatch: actual `MacePostSelectionTrainer` with artifact/path/plan SHA disagreement must show zero wrapper launches.
- canonical summary requirement: fake wrapper exits zero but canonical TRAIN2 summary is missing or invalid -> `PostSelectionExecutionError`.
- head namespace: omitted and explicit canonical target head produce the same method identity; noncanonical target head rejects before materialization; runtime-plan head names exactly equal actual executable MACE `heads` keys.

After R9B, run focused tests plus affected MACE-config, optimizer, acceleration, TRAIN2 runtime/wrapper, materialization, provider, and prior P5 regression before R9C.

---

## 5. Revision-9 defect C — assembled replay-enabled non-scratch real-owner acceptance

### 5.1 Required semantic-owner boundary

The existing scratch/no-replay `PostSelectionHarness` lifecycle remains useful regression coverage but **cannot close P5 assembled acceptance**.

Create one bounded assembled test dedicated to the revision-9 owner chain. It must traverse:

```text
real campaign config
 -> real CampaignStore and current P4 SELECTED authority
 -> real resolve_post_selection_method_policies
 -> real canonical foundation inspection/spec/head resolution
 -> real canonical replay training resolution
 -> real canonical replay TRUE_DFT monitor/source/split resolution
 -> real path-free PostSelectionMethodIdentity
 -> real authenticated replay-lineage digest
 -> real CV plan/folds from selected data + P1 relation authority
 -> real fold DATA7/DATA8 preparation/materialization
 -> real Train2RuntimePlan
 -> real MacePostSelectionTrainer
      -> real internal-config authentication
      -> real target/foundation/replay pre-launch authentication
      -> real config translation/environment/cwd
      -> deterministic fake wrapper below the trainer
 -> real canonical TRAIN2 summary/checkpoint authentication
 -> real post-selection provider authentication
 -> real EVAL2 decision path
 -> candidate replay evaluation + canonical foundation baseline on same TRUE_DFT monitor
 -> real target-only representative selection
 -> real held-out outer acceptance
 -> real all-required-fold/seed CV campaign acceptance
 -> real final-plan method + replay-lineage reauthentication
 -> fresh full-T_selected final orchestration
 -> real M3 development semantics
 -> real currentness-fenced publication
 -> fresh context/reopened CampaignStore restart authentication
```

### 5.2 Required campaign fixture

The assembled test must be **non-scratch and replay-enabled**.

It may reuse the existing tiny P4 campaign fixture to establish a real current `SELECTED` authority, but before P5 execution its configuration/data must include:

- a canonically inspectable foundation checkpoint and explicit canonical head when the fixture is multihead;
- replay training data under one supported mode;
- a canonical independent TRUE_DFT replay monitor/source sufficient for the existing replay owner;
- enough tiny target/replay structures to satisfy bounded CV and replay evaluation.

Prefer an existing tiny real MACE checkpoint fixture if one is already in the test suite. If loading a real model would make the functional test hardware/dependency-heavy, the **allowed fake boundary is below canonical P5 foundation resolution**: a deterministic low-level model/checkpoint loader may return a real `MaceFoundationInspection` shape while `resolve_post_selection_foundation_identity()` and `MaceFoundationSpec.resolve()` themselves remain unpatched and execute normally. Do not patch the P5 foundation resolver or directly inject `FoundationPotentialIdentity.from_file()` as authorization.

Likewise, do not patch replay policy/lineage resolvers. Build tiny real replay files and let the existing replay owners create source/split/view artifacts.

### 5.3 Real trainer; fake wrapper only below it

The test must instantiate/use the real `MacePostSelectionTrainer` selected by production orchestration. It must **not** pass `_external_post_selection_trainer=PostSelectionHarness.train` and must not replace `MacePostSelectionTrainer` when claiming R9C.

A deterministic fake `mdstats-mace-train` executable is allowed because the external numerical process is below the trainer semantic owner. The fake wrapper must:

- receive the translated MACE config through the real trainer;
- capture/validate cwd and required environment;
- consume or at least authenticate the real materialized filenames it was given;
- produce bounded canonical TRAIN2 runtime summary/checkpoint artifacts in the locations/formats expected by existing owners;
- produce deterministic tiny checkpoint state sufficient for the real downstream checkpoint/provider authentication path, or use an accepted lower-level provider numerical seam without bypassing provider authentication.

Do not write a P5-only summary or checkpoint format.

### 5.4 Allowed numerical substitution

To keep the test fast and CPU-safe, deterministic numerical prediction may be substituted below the real provider/EVAL2 orchestration boundary. The following must still execute as production code:

- candidate checkpoint/provider authentication;
- canonical foundation baseline provider construction/head selection;
- artifact loading and EVAL2 reduction;
- replay admissibility decision;
- target-only representative selection;
- outer acceptance;
- campaign/final/restart authorization.

The test may use tiny synthetic structures and deterministic force offsets. It does not need real long MACE optimization or GPU execution.

### 5.5 Forbidden proxy substitutions

The R9C claim is invalid if the test:

- patches/replaces `resolve_post_selection_method_policies()`;
- patches/replaces `resolve_post_selection_foundation_identity()` or `MaceFoundationSpec.resolve()`;
- directly constructs `FoundationPotentialIdentity.from_file()` in place of P5 foundation authorization;
- patches/replaces canonical replay training/source/split/TRUE_DFT resolvers;
- precomputes a replay-lineage digest and injects it into a plan;
- seeds `CvCampaignAcceptance` or final authorization;
- directly constructs post-decision `Eval2CheckpointRecord` replay metrics rather than exercising the EVAL2 decision owner;
- replaces `MacePostSelectionTrainer` with `PostSelectionHarness`;
- replaces `CampaignStore`, currentness fencing, or restart ownership with a custom/in-memory stand-in.

### 5.6 Counterfactual requirements

The assembled test must fail if any of these regressions are introduced:

- canonical foundation inspection is bypassed/falls back;
- pseudolabel replay training is silently replaced by TRUE_DFT training;
- replay paths enter scientific method/lineage identity;
- target/replay head names diverge between method/runtime/executable MACE;
- pre-launch target/foundation/replay authentication is bypassed;
- candidate/foundation replay evaluation no longer uses the same TRUE_DFT monitor;
- replay changes target-only ranking credit;
- accepted CV replay lineage differs from current final-production lineage;
- final production reuses CV state instead of fresh full-`T_selected` training;
- stale P4 generation/currentness is accepted;
- fresh restart accepts stale method/foundation/replay/final-plan evidence.

After R9C, run the final affected-surface regression defined in Section 7.

---

## 6. Mandatory negative/parity matrix

All prior revision-8 claims remain binding. They may be covered by existing tests if those tests truly exercise the stated owner. Claim numbering is for review convenience only; do not create one test per number.

### Revision-8 claims 1-38

1. real foundation resolver executes without missing imports;
2. corrupt/unsupported foundation cannot downgrade to byte-only identity;
3. wrong foundation family fails;
4. multi-head omitted head fails;
5. unavailable explicit head fails;
6. foundation relocation with same bytes/head preserves P5 method identity;
7. foundation bytes changed at same path invalidate/fail old method/CV;
8. replay shared method digest contains no filesystem path;
9. replay source relocation with same bytes/policy/split preserves method identity;
10. replay lineage contains no filesystem path;
11. replay source byte mutation invalidates CV->final authorization;
12. replay split seed/ratio/membership mutation invalidates the appropriate policy/lineage;
13. TRUE_DFT monitor byte mutation fails before training/evaluation;
14. invalid dtype rejects instead of coercing to float64;
15. invalid training mode rejects;
16. unsupported optimizer family remains rejected;
17. `eval_interval` mutation changes both method identity and executable MACE config;
18. checkpoint interval mutation changes method identity and TRAIN2 budget/checkpoint policy;
19. acceleration backend mutation changes method identity and canonical MACE acceleration training config/policy;
20. method acceleration backend cannot disagree with run optimizer acceleration backend;
21. target train artifact tamper blocks wrapper launch;
22. target monitor artifact tamper blocks wrapper launch;
23. foundation artifact tamper blocks wrapper launch;
24. replay train artifact tamper blocks wrapper launch;
25. replay monitor artifact tamper blocks wrapper launch;
26. runtime TRUE_DFT SHA/path mismatch blocks wrapper launch;
27. internal P5 config cannot be handed directly to MACE;
28. TRAIN2 runtime environment remains exact;
29. canonical TRAIN2 summary is mandatory after wrapper success;
30. canonical foundation replay baseline uses the canonical head and same TRUE_DFT monitor as candidate;
31. replay remains zero-credit to target ordering/ties/acceptance ranking;
32. held-out outer CV target data cannot select the checkpoint it evaluates;
33. all required folds/seeds remain mandatory;
34. M3 remains development/model-selection only;
35. production horizon remains independent from `n3` and CV budget;
36. current P4 generation race still rejects stale publication;
37. CV/final evidence cannot modify target-size authority;
38. restart reload reauthenticates method, foundation, replay lineage, selected binding, and final plan.

### Revision-9 claims 39-48

39. legacy pseudolabel replay training and legacy TRUE_DFT replay training produce distinct shared method identities;
40. the replay training artifact actually exposed to MACE has label semantics equal to the method identity's normalized replay-training semantic;
41. the independent TRUE_DFT monitor is admissibility-only and cannot silently replace pseudolabel replay training;
42. relocating identical legacy replay files with unchanged semantics preserves method identity and replay lineage;
43. changing legacy replay training semantic after accepted CV invalidates final authorization;
44. the current P5 fine-tuning head namespace is exactly `target_head` / `pt_head` across method, runtime plan, and executable MACE configuration;
45. any unsupported noncanonical P5 fine-tuning head configuration rejects before training;
46. `Train2RuntimePlan.target_head_name/replay_head_name` exactly match the actual executable MACE `heads` keys;
47. one assembled non-scratch replay-enabled lifecycle uses the real `MacePostSelectionTrainer` and real P5 foundation/replay/CV/final/currentness owners, faking only below the accepted numerical boundary;
48. a fresh context/reopened store reauthenticates selected binding, method, canonical foundation/head, replay training + TRUE_DFT lineage, canonical head namespace, accepted CV, and final plan.

A green numbered guard file is not completion if its assertions could remain green while the production owner is broken.

---

## 7. Implementation stages and regression requirements

### P5-R9A — legacy replay semantic/execution closure

**Expected affected files**

- `mdstats/training_data/post_selection_identity.py`
- `mdstats/training_data/campaign_post_selection_runtime.py`
- existing replay/config modules only if a small shared canonical accessor is genuinely required
- focused tests

**Required edits**

1. Replace legacy replay boolean identity with canonical normalized training-label semantics.
2. Separate actual replay training resolution from independent TRUE_DFT admissibility monitor resolution.
3. Make MACE replay training consume the artifact matching configured replay-training semantic.
4. Extend legacy plan lineage to bind actual training artifact + TRUE_DFT monitor identities without paths.
5. Preserve single-source path-free identity/lineage and revision-8 fail-closed behavior.

**Stage closure**

Run focused R9A tests plus affected replay, true-label replay, P5 identity, CV-plan, final-plan, and restart regression. Do not proceed to R9B with a newly failing affected test.

### P5-R9B — head parity and direct guard repair

**Expected affected files**

- `post_selection_identity.py`
- `post_selection_execution.py`
- `campaign_post_selection_runtime.py`
- P5 R8/R9 tests

**Required edits**

1. Define/reuse one canonical P5 target/replay head-name owner.
2. Reject unsupported custom P5 fine-tuning head names.
3. Route canonical names through method identity, TRAIN2 runtime plan, internal config, and executable MACE head map.
4. Replace proxy/self-fulfilling R8 tests for claims 17-20, 26, and 29 with direct owner execution.
5. Preserve all revision-8 pre-launch/config/summary fixes.

**Stage closure**

Run focused R9B tests plus affected optimizer/acceleration/MACE-config, TRAIN2 runtime/wrapper, materialization/provider, foundation, and P5 regression.

### P5-R9C — assembled real-owner closure

**Expected affected files**

- test fixture/support code
- P5 R9 integration test
- production code only if the assembled test exposes a real implementation consequence already implied by this workplan

Build the exact owner chain in Section 5. Do not weaken the owner boundary to make the fixture easier.

**Stage closure**

The replay-enabled non-scratch assembled integration must pass on the same source candidate that proceeds to final regression.

---

## 8. Final affected-surface regression

After all R9 executable changes, re-derive the affected surface from the assembled candidate. At minimum execute bounded regression covering:

- P5 revision-9 guards and assembled replay-enabled non-scratch integration;
- prior P5 revision-8/revision-7 and earlier P5 guards that protect still-binding obligations;
- P4 selected/currentness and commit-time stale-generation fencing;
- generalized foundation identity/head inspection and provider construction;
- replay single-source and supported legacy normalization;
- pseudolabel training exposure and independent TRUE_DFT replay evaluation;
- replay source/split/view/currentness/restart behavior;
- common DATA7/DATA8 preparation/materialization reused by P5;
- `MaceOptimizerPolicy`, `eval_interval`, checkpoint interval, and acceleration training config;
- TRAIN2 budget/LR/runtime/environment/wrapper/summary/checkpoint/provider authentication;
- EVAL2 target/replay admissibility and target-only ordering;
- CV plan/fold/acceptance, all-required seed/fold semantics, and outer holdout ordering;
- final production/M3/fresh-run semantics;
- persistence/current-pointer/restart resolution;
- CLI/orchestrator `cross-validate` and `train-production` entrypoints.

If impact analysis cannot confidently bound the affected surface after implementation, run the broader available MLFF training-data regression suite.

A required check that does not execute is not a pass. Stage-local evidence does not replace the fresh final assembled affected-surface regression/integration.

Do **not** run long production/GPU qualification for this package. CPU-safe bounded tests and deterministic numerical substitutes below the accepted owner boundary are sufficient for functional closure.

---

## 9. Completion conditions and reopen triggers

P5 revision 9 may be marked implemented only when all are true on one assembled candidate:

```text
semantic closure
+ canonical foundation fail-closed behavior preserved
+ single-source and legacy replay scientific identity path-free
+ legacy pseudolabel vs TRUE_DFT training semantics distinguished
+ replay training artifact matches method identity
+ independent TRUE_DFT monitor remains admissibility-only
+ exact replay lineage reauthenticated CV -> final -> restart
+ one canonical target_head/pt_head namespace across identity/runtime/MACE
+ complete retained method identity -> execution parity
+ all scientific training inputs authenticated before wrapper launch
+ qualified TRAIN2 translation/environment/summary path preserved
+ canonical candidate/foundation replay admissibility path preserved
+ stage-local affected regression passed for R9A and R9B
+ replay-enabled non-scratch real-owner R9C integration passed
+ final affected-surface regression/integration passed
```

### Reopen Design only on evidence

Reopen only the affected P5 design surface if repository evidence proves one of these assumptions false:

- existing canonical replay owners cannot expose the configured replay **training** artifact separately from independent TRUE_DFT admissibility evidence without a material replay-architecture change;
- a currently supported legacy replay mode has materially different semantics that cannot be normalized through existing `ReplayMode`/`ReplayLabelMode` ownership;
- current accepted MACE/TRAIN2 multihead execution requires user-configurable fine-tuning head names rather than fixed `target_head`/`pt_head` and rejecting custom names would break a governed product contract;
- canonical foundation inspection/spec ownership cannot support a bounded real-owner fixture without changing production foundation architecture;
- real `MacePostSelectionTrainer` cannot be exercised with a fake external wrapper while preserving canonical TRAIN2 summary/checkpoint ownership;
- a revision-9 correction conflicts irreconcilably with a frozen parent/P1-P4 contract.

Absent such evidence, the remaining work is implementation repair under this workplan, not redesign.
