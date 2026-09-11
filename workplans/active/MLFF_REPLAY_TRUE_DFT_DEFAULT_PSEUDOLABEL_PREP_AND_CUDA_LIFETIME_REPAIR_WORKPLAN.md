---
kind: implementation-workplan
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
protocol_version: 6.2
status: active-ready-for-implementation
plan_review_state: final-design-review-consolidated
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
implementation_baseline_commit: 2f56df276d022760588aa5fd3ec7bbe5479ad6ea
reviewed_cycle_head: 709a0a1f9cd656e94e7fe8c6acc32c28d1157466
highest_affected_domain: D3 configuration/stage/persistence/currentness/concurrency/resource architecture -> D4 implementation
upstream_policy_constraint: new single-source replay defaults to source TRUE_DFT labels; foundation pseudo-label replay remains explicit opt-in
serious_challenge: none
related_active_workplan: workplans/active/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md
related_review_reopen: workplans/active/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_FIFTH_REVIEW_REOPEN.md
consolidates_cycle_artifacts:
  - workplans/active/MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_SECOND_REVIEW_AMENDMENT.md
  - workplans/active/MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_SECOND_REVIEW_FINAL_CLOSURE.md
precedence: This file is the snapshot-complete D3 -> D4 implementation contract for this replay repair. It incorporates the prior review amendments and replaces them as active handoff material. It does not supersede the separate TRAIN2 zero-safe-admission/live-memory-safety repair, target-size scientific authority, or any non-conflicting CV, production, optimizer, precision, backend, checkpoint, publication, storage, or restart authority.
---

# MLFF replay TRUE_DFT default, prepare ownership, and pseudo-label CUDA lifetime repair

## 0. Final Software Design review disposition

### 0.1 Disposition

Independent Protocol 6.2 Software Design review was repeated against implementation baseline `2f56df276d022760588aa5fd3ec7bbe5479ad6ea` and the accumulated cycle plan through `709a0a1f9cd656e94e7fe8c6acc32c28d1157466`. The review reconstructed current configuration, target-size, replay, post-selection, persistence, lifecycle, storage, concurrency, and provider-lifetime behavior rather than inheriting prior PASS conclusions.

The earlier plan family was directionally correct but remained incomplete as a D3 -> D4 handoff. The final pass found residual gaps around doctor-stage ownership, exact replay record publication, concurrent cold-cache creation, process-local cache masquerade, pseudo-mode TRUE_DFT-monitor invalidation, execution-only cache knobs, lifecycle currentness, and provider-scope overlap.

Those gaps are closed in this consolidated workplan. The resulting workplan is **PASS / frozen for implementation**. No Serious Challenge is active: the accepted current target-size architecture, post-selection method/replay identity, replay invalidation layering, storage/reconstruction contract, provider-lifetime doctrine, public lifecycle, and stakeholder default-policy decision are jointly realizable.

### 0.2 Governing simplification

The repair is a restoration and reduction, not a new subsystem:

```text
cheap canonical config/topology validation
    -> doctor validates replay/source/runtime prerequisites only
       (no replay-wide pseudo prediction, no prepared replay publication)
    -> prepare owns replay scientific construction/reuse
       alongside, but not inside, the independent target-size prepared generation
    -> one coherent current replay alias set publishes atomically
    -> post-selection reads/authenticates current replay lineage
       and may repair only disposable representations
    -> explicit pseudo cold build is single-flight
       with one device-correct inference/OOM-learning lifetime
       and exactly one provider-retirement owner
    -> TRAIN2 sees the resulting real aggregate device occupancy
       under the existing unchanged zero-safe admission controller
```

Do not fix the symptom by adding a scheduler cleanup hook, a replay-ready database, a provider registry, a second replay generation, a CV fallback builder, or a target-size replay dependency.

## 1. Governing outcome and authority

### 1.1 Product outcome

For the current single-source replay interface:

```text
[paths].replay_set absent
    -> no single-source replay

[paths].replay_set present
    + [replay].label_mode omitted
        -> TRUE_DFT replay                         [new default]

    + label_mode = "true_dft"
        -> TRUE_DFT replay                         [explicit equivalent]

    + label_mode = "foundation_pseudolabel"
        -> foundation pseudo-label replay          [explicit opt-in]
```

New `campaign init` output and `campaign.toml.example` must explicitly emit `label_mode = "true_dft"` so the effective scientific choice is visible even though omission resolves identically.

TRUE_DFT and foundation pseudo-label replay remain existing, distinct scientific label authorities. This cycle changes which existing mode new single-source configuration selects by default; it does not change the scientific/numerical semantics inside either mode.

Missing or invalid source truth in TRUE_DFT mode fails closed. It never triggers an automatic pseudo-label fallback.

### 1.2 D1/D2 boundary

No method-internal D1/D2 change is authorized. Preserve:

- target and replay head semantics;
- objective/loss/weighting semantics;
- replay split algorithm and statistical role definitions;
- pseudo-label prediction numerical identity and qualification meaning;
- TRUE_DFT replay monitor meaning;
- optimizer, LR, precision, backend, checkpoint, CV and final-production science except where their existing identities correctly become stale because replay method/lineage changed.

If implementation demonstrates that TRUE_DFT replay cannot satisfy the accepted multi-head label-domain/E0/objective method without changing D1/D2 semantics, stop and route to the earliest affected scientific/numerical owner.

### 1.3 D3 ownership

D3 owns here:

- one canonical replay configuration normalization path;
- replay versus target-size preparation ownership;
- persistent current replay record grouping and currentness;
- construction versus downstream read interfaces;
- representation/cache recovery boundaries;
- concurrent cache publication and single-flight resource ownership;
- provider/executor lifetime;
- public lifecycle observation/routing consequences.

D4 owns the exact helper factoring, lock helper, in-memory object layout, logging wording, and local implementation as long as this contract holds.

## 2. High-level architecture and global invariants

### 2.1 Replay authority chain

```text
single external replay_set
  -> authenticated ReplaySourceArtifact / source index representation
  -> source TRUE_DFT label cache
  -> mode branch
       TRUE_DFT
         -> source-truth qualification basis
       FOUNDATION_PSEUDOLABEL
         -> ReplayFoundationPredictionPolicy
         -> foundation prediction cache
         -> pseudo qualification
  -> one deterministic split authority
  -> training transport for effective mode
  -> independent TRUE_DFT monitor transport
  -> post-selection replay lineage + method identity
  -> CV / final-production descendants
```

Source, prediction, qualification, split, and materialized views remain separate layers so changes invalidate only materially dependent descendants.

### 2.2 Target-size independence

The current target-size screen is target-only. Its common policy carries `REPLAY_EXPOSURE_NONE_DIGEST`, and target-size MACE execution rejects multi-head replay. `campaign_prepared_generation.preparation_configuration_identity()` likewise excludes replay configuration.

Therefore replay-only changes do **not** by themselves invalidate:

- the immutable target-size prepared generation;
- target-size screen trajectories/evidence/recommendation;
- a provisional target-size selection;
- a frozen target-size collection or exact target membership.

Do not add replay source, label mode, prediction policy/cache, qualification, split, or replay currentness to `CurrentTargetSizeAuthorities`, target-size generation identity, target-size screen identity, recommendation, provisional entry, or frozen target binding merely to enforce public command order.

Public `prepare` may coordinate two independent preparation owners. That orchestration does not make them one scientific generation.

### 2.3 Public lifecycle versus scientific ownership

```text
public lifecycle:
  init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production

scientific target-size ownership:
  target P1/P2/P3 parents only; replay exposure = none

post-selection replay ownership:
  current replay method/lineage parents P5 descendants
```

A replay failure can make public `prepare` incomplete while an independently published target-size generation remains scientifically valid. A replay-method change can retire P5 CV/final descendants while leaving the frozen target collection intact.

## 3. Canonical configuration and topology contract

### R1 - normalize every single-source replay selector once

When `replay_set` is present, normalize all replay label selectors before source/model work:

```text
label_mode omitted + legacy mode omitted
    -> TRUE_DFT

label_mode=true_dft
    -> TRUE_DFT

label_mode=foundation_pseudolabel
    -> FOUNDATION_PSEUDOLABEL

legacy mode=external_true_label
    -> TRUE_DFT compatibility alias

legacy mode=external_pseudolabel
    -> FOUNDATION_PSEUDOLABEL compatibility alias

new + supported legacy selector agree
    -> one canonical effective ReplayLabelMode

new + legacy selector disagree
    -> reject

legacy mode=none | mp_shortcut | preselected | unsupported value with replay_set
    -> reject; never silently ignore and default TRUE_DFT
```

Mixed `replay_set` and legacy split replay paths remain rejected. Legacy split-file replay without `replay_set` preserves its historical compatibility behavior, including its existing omitted-mode semantics.

Downstream code consumes the normalized single-source result; it does not maintain an independent default.

### R2 - exact configuration domains; no Python coercion as policy

At the resolver/config owners touched by this repair:

- `split_seed` is an exact nonnegative integer; reject booleans, fractional values, NaN/Inf, and non-integer objects rather than truncating through `int(...)`;
- sequence-form split-ratio components are exact positive integers; reject booleans/fractions; retain the documented lexical string form such as `"5:1"`;
- prediction batch/shard controls and qualification booleans/numerics continue through their established validated owners; do not add truthiness/int-cast shortcuts;
- replay prediction device/backend/dtype/head come from the existing canonical foundation/acceleration/prediction resolution, not independent defaults in prepare/executor/method identity.

### R3 - validate method/replay topology before expensive public prepare work

Replay-wide preparation is authorized only for a configuration whose accepted post-selection method topology enables replay. Scratch/naive-fine-tuning/orphan replay declarations must retain their existing fail-closed semantics.

At public `prepare` entry, before target-size source-wide reconstruction, replay source-wide parsing, model inspection/inference, materialization, or new scientific publication, perform the cheap canonical configuration/topology preflight sufficient to reject:

- invalid/conflicting selectors;
- invalid exact split domains;
- mixed new/legacy replay topology;
- replay declaration incompatible with resolved training-method topology;
- other contradictions knowable without reading the replay corpus or loading the model.

Reuse the existing canonical topology/configuration owners. Do not create a prepare-only replay interpretation.

A runtime/data failure that can only be discovered after valid cheap preflight retains the independent partial-success rule: a valid target-size generation already published is not rolled back merely because later replay preparation failed.

## 4. Stage ownership

### R4 - doctor is preflight/qualification, never replay preparation

Baseline currently violates this contract: `doctor` can reach `_qualify_replay()` -> `_build_replay_plan()` -> `_single_source_replay_context()`, and then `_persist_single_source_replay_authority()`. On an explicit pseudo cold path that can construct the prediction cache and foundation provider before `prepare`.

Remove that construction leak.

For current single-source replay, `doctor` may:

- normalize/validate replay configuration and method topology;
- validate source accessibility/schema and source TRUE_DFT inventory as required by the accepted doctor contract;
- validate foundation/head/runtime/acceleration prerequisites for explicit pseudo mode;
- run its existing bounded accelerator smoke/qualification if that doctor owner requires it;
- reuse/create non-authoritative source-inspection receipts if the existing source-validation owner permits.

`doctor` must **not**:

- call the replay-wide prediction-cache builder;
- perform full pseudo-label foundation inference over the replay corpus;
- run pseudo qualification that depends on those predictions;
- create mode-specific train/monitor replay materializations merely to qualify the campaign;
- publish the prepared/current single-source replay alias set.

Pseudo eligibility/train-monitor cardinalities that depend on foundation predictions are **deferred to prepare**. Doctor output must represent that truthfully as deferred/not-yet-realized rather than fabricate a final qualified replay plan. Prepare owns the post-prediction minimum-count/qualification failure.

This does not prohibit a small doctor-owned acceleration smoke; the prohibition is against replay-wide pseudo preparation and its durable current replay publication.

### R5 - public prepare restores replay preparation ownership

When valid single-source replay is configured, `prepare` owns construction/reuse of the replay state needed downstream.

TRUE_DFT prepare:

- authenticate/reuse source and source index;
- build/reuse TRUE_DFT label cache;
- build/reuse deterministic split under the TRUE_DFT qualification authority;
- materialize/authenticate required TRUE_DFT training/monitor transports;
- perform zero replay foundation pseudo inference.

Explicit pseudo prepare:

- authenticate/reuse source/true-label basis;
- resolve the current foundation prediction policy;
- build/reuse prediction cache under the concurrency/resource rules below;
- qualify cached predictions under current qualification policy;
- build/reuse the deterministic split;
- materialize/authenticate pseudo training transport and independent TRUE_DFT monitor transport, plus any other existing mode-required replay transport;
- enforce post-qualification minimum train/monitor requirements here;
- retire prepare-owned accelerator state before returning.

`StageState.COMPLETE` for public prepare means every configured preparation prerequisite required by this invocation is current/authenticated. If replay fails after a valid target-size generation has published, mark public prepare failed/incomplete but preserve that valid target-size generation; retry uses normal target-size owner currentness and completes/reuses replay work without destructive rollback.

Do not create a combined target/replay generation or resurrect a retired generic restart authority to synchronize them.

### R6 - all post-selection replay consumers are scientific-read-only

Every current P5 consumer—CV setup/execution, final production, restart/continuation, representative re-evaluation/recovery, and future callers of the same owner—must obtain replay science through authenticated current persisted replay state.

No production P5 path may reach a construction-capable single-source helper that can:

- build/rebuild foundation predictions;
- requalify pseudo predictions under a changed policy;
- create a new scientific split;
- decide a different replay method.

This prohibition includes indirect routes through helpers equivalent to current `_build_replay_plan()`, `_resolve_true_label_replay_inputs()`, or `_single_source_replay_context()` when they are construction-capable.

P5 may repair a **disposable representation** when all scientific parents needed for that repair are already current/authenticated and the repair performs no foundation inference, no policy-dependent requalification, and no scientific resplit.

Examples:

- missing train/monitor ExtXYZ view + current required parent cache -> representation-only rematerialization allowed;
- authenticated pseudo train view retained while bulky prediction payload was legitimately reclaimed -> P5 may consume that view if compact current lineage proves it belongs to current parents;
- missing view + missing/corrupt prediction values required to reconstruct it -> P5 fails actionably and routes to `prepare`.

Within one post-selection command/shared replay context, authenticate expensive source/view state once where practical and reuse the immutable resolution across folds/sizes/runs. Do not replace hidden GPU work with O(folds/runs) parsing of a 12k replay source.

## 5. Persistence, currentness, and publication

### R7 - persisted replay state is one coherent current alias set

Build and validate mode-specific filesystem/cache products first. Then publish the exact current compact replay record aliases as one short atomic group.

Use the existing `CampaignStore.replace_records_atomically(records, delete_keys=...)` capability or an equivalently narrow existing transactional owner rather than adding a replay generation/currentness database.

For each successful single-source prepare:

- install exactly the common replay current records plus the records applicable to the effective mode;
- atomically remove inactive mode-specific **current aliases** from the generic current namespace in the same transaction;
- do not delete underlying content-addressed/reconstructable prediction cache bytes merely because their mutable current alias is inactive;
- historical P5 evidence remains immutable history and is never rewritten/deleted to make currentness look correct;
- readers observe one coherent old alias set or one coherent new alias set, never a hybrid assembled from independent transitions.

A crash after filesystem product creation but before compact alias commit leaves inert/reusable content, not a partially current replay authority.

The long build must not hold CampaignStore's global writer lock. At compact commit, revalidate the canonical source/policy/currentness token (or equivalent existing compare/recheck condition) so a stale long-running builder cannot overwrite a newer prepared replay state.

Mode transitions such as pseudo -> true and true -> pseudo must leave no stale mode-specific alias falsely current or unnecessarily pinning storage through the current-record namespace.

### R8 - downstream replay reads are coherent and identity-based

P5/lifecycle readers must resolve a coherent replay snapshot and verify internal parent bindings. Pointer/key existence is never sufficient.

At minimum currentness covers, where applicable:

- effective normalized label mode;
- replay source scientific content/true-label authority;
- split policy and current split authority;
- pseudo foundation prediction policy/cache logical identity;
- pseudo qualification authority;
- training transport lineage;
- independent TRUE_DFT monitor lineage;
- current post-selection replay-policy/method identity.

Do not use pathful `ReplaySingleSourceConfig.content_digest` or the old broad `_preparation_config_digest` as a coarse replay scientific identity. They contain locators and/or execution-only fields and would create false invalidation.

### R9 - process-local replay caches never authenticate currentness

A process-local `_UNIFIED_REPLAY_CONTEXT_CACHE` may remain only as a bounded execution optimization, preferably restricted to prepare/read scopes that already possess authenticated parents. It is not currentness authority.

A cache hit cannot bypass the content checks required without it. Same-process replacement of replay source or foundation checkpoint bytes at the same configured locator must invalidate/reject stale cached science even when size/mtime/stat shortcuts collide. Identical-byte relocation remains scientifically reusable.

Prefer deleting/narrowing the cache or keying/revalidating it from already-authenticated identities over adding another cache-validation layer.

## 6. Minimal invalidation and identity

### R10 - preserve layered replay invalidation, with explicit TRUE_DFT-monitor branch

Preserve the semantics of the existing replay invalidation decomposition instead of replacing it with a coarse prepared digest.

Required outcomes include:

- identical source bytes relocated -> no scientific invalidation/replay foundation inference solely because the path changed;
- source geometry change -> reindex and invalidate geometry-dependent pseudo predictions as currently governed;
- TRUE_DFT-mode source truth change -> refresh truth-dependent qualification/split/materializations and downstream P5 lineage as governed;
- pseudo prediction-policy change (foundation checkpoint/head/inference identity) -> invalidate prediction cache and dependent pseudo qualification/split/view/P5 lineage;
- pseudo qualification-threshold change -> requalify cached audit/prediction evidence without foundation inference; resplit/rematerialize only as required by the qualification result/identity;
- split ratio/seed change -> resplit/rematerialize without foundation inference;
- materialized view deletion -> reconstruct from authenticated parents without foundation inference;
- missing/corrupt required prediction state -> rebuild only in prepare.

**Pseudo-mode source TRUE_DFT-label-only mutation requires special clarity:** when geometry and prediction policy are unchanged, preserve the foundation prediction cache and, under the existing pseudo invalidation owner, preserve pseudo qualification/split where their parents are unchanged. However the independent mandatory TRUE_DFT monitor is a parallel label-dependent descendant. Its view/artifact/lineage must refresh/re-authenticate from the changed source truth, and P5 replay lineage/CV/final descendants become stale when that monitor lineage changes.

Do not misread `ReplayInvalidationPlan`'s pseudo-training result as permission to keep a stale TRUE_DFT monitor.

If review discovers that an existing invalidation rule is itself scientifically wrong, route to its owner rather than silently invalidating everything.

### R11 - execution/storage knobs stay out of scientific replay identity

Preserve the current prediction-cache identity separation:

Scientific prediction identity includes the semantically governing foundation/inference fields already defined by `ReplayFoundationPredictionPolicy` (including its current device/backend/dtype/head/checkpoint semantics).

The following remain execution/storage realization only unless a current specification independently makes them scientific:

- configured prediction `batch_size`;
- physical `shard_size` and shard grouping/layout;
- graph-cache locator/layout;
- process-local learned safe OOM batch width;
- progress/logging/worker realization.

Changing prediction batch size or shard size while a logically valid prediction cache exists must not trigger foundation reinference or change post-selection replay/method scientific lineage. A genuinely cold future build may use/relearn the new execution realization.

Do not persist learned OOM-safe width as scientific/currentness identity merely to reuse it across commands.

### R12 - no gratuitous scientific/schema version churn

Do not bump `POST_SELECTION_METHOD_RECIPE_VERSION`, replay config/invalidation schemas, target-size generation tokens, or unrelated TRAIN2/replay-lineage schemas merely because routing/lifetime code moved.

Explicit TRUE_DFT campaigns and explicit pseudo campaigns should retain their existing scientific method identity if their effective semantics are unchanged. Omitted single-source mode is the deliberate semantic default change and therefore resolves to TRUE_DFT; evidence that previously depended on a different omitted-value interpretation is review-required/historical.

A schema/version bump requires a real persisted-semantic representation change that existing identities cannot express, with owning-layer justification and impact closure.

## 7. CUDA/resource ownership and concurrency

### R13 - exactly one provider-retirement owner

For an internally constructed replay prediction provider there is exactly one terminal retirement owner.

Permitted forms include:

- cache/preparation builder owns provider; operation-scoped executor is non-owning; builder closes in `finally`; or
- ownership transfers exactly once to the operation-scoped executor, whose context/finally closes it.

Do not make both layers owners and rely on idempotent `close()` to hide ambiguity.

Cleanup must cover:

- provider validation failure after construction;
- executor construction/ownership-transfer failure;
- graph-cache initialization failure;
- source iteration;
- prediction/OOM terminal failure;
- shard/audit/materialization I/O failure;
- publication failure;
- ordinary exceptions;
- cancellation/`KeyboardInterrupt`/other catchable `BaseException` after acquisition.

Caller-supplied providers remain caller-owned absent an explicit pre-existing transfer contract. Returned cache/records contain no live provider/executor/model reference.

Forced process kill is outside exception cleanup and cannot be used as proof of explicit retirement.

### R14 - one device-correct inference/OOM-learning lifetime per cold build

Current per-outer-batch `StaticMaceInferenceExecutor` recreation loses learned OOM-safe batch state and can default the executor device to CPU despite a CUDA-backed provider.

Required end state:

- execution binds the effective replay prediction device;
- synchronization/OOM/cache behavior follows that real device;
- one coherent OOM-learning state spans the complete cold prediction-cache build;
- once an oversized batch is shown unsafe, later outer batches do not retry it merely because iteration advanced;
- geometry order, prediction values/identity, audit values, and logical cache semantics remain unchanged.

Reusing one existing static executor for the operation is the preferred simplification, but the invariant is one coherent resource-learning lifetime rather than a class name.

### R15 - same-key cold cache creation is single-flight and crash-safe

Two concurrent `prepare` invocations for the same source-geometry + prediction-policy cache identity must not each load a model and perform duplicate replay-wide inference.

Required flow:

```text
contender enters narrow cache/artifact execution-publication fence
  -> RECHECK authenticated cache after acquiring fence
  -> winner exists: reuse, zero inference
  -> still absent/stale: exactly one contender builds
  -> validate/publish cache
  -> retire provider
  -> release fence
```

Use/factor an existing advisory artifact/publication lock pattern where possible. The lock is execution state, not scientific state. Do not introduce a replay lock subsystem, GPU lease database, provider registry, or hold the CampaignStore global writer lock across GPU work.

Fixed temporary paths must not let concurrent attempts delete/corrupt each other's live work. Under a single-flight owner, only that owner may reclaim its known scratch; alternatively use unique attempt scratch plus create/verify winner publication if simpler. A loser rechecks the winner instead of blindly replacing it.

Apply equivalent existing atomic/fenced publication discipline to replay materialized views if they can be concurrently reconstructed by more than one command.

### R16 - pseudo inference remains label-blind

Executor/provider consolidation must preserve the existing anti-leakage boundary: foundation pseudo prediction receives geometry-only copies. Source TRUE_DFT energy/forces/stress, attached calculator results, qualification outcomes, and generated training labels must not enter the foundation forward graph.

### R17 - public prepare provider scopes remain non-overlapping

Current execution architecture requires large prepare-owned accelerator providers/references to end at their final preparation consumer. This repair must not merely close the replay provider eventually while overlapping it with another prepare-owned model-scale provider.

Within one public prepare process, acquire the replay pseudo provider only after any earlier prepare-owned model-scale provider whose final consumer has completed has been retired, unless an existing resource owner explicitly admits concurrent residency under a proven budget. The default repair is sequencing and release, not a new GPU scheduler.

## 8. Lifecycle/currentness consequences

### R18 - status/advance observe composite prepare truth without new state

`status` and `advance` remain derived/read-only projections.

They must distinguish:

- target-size generation current but replay preparation failed/incomplete -> public prepare not ready; `advance` routes through `prepare`;
- replay-only config/source/method lineage change under unchanged target generation -> target design remains current, old P5 descendants may become historical;
- semantically identical replay reprepare/identical-byte relocation -> applicable P5 evidence remains current;
- representation-only deletion/reconstruction with unchanged scientific lineage -> applicable P5 evidence remains current.

Do not add a new lifecycle enum or state machine. Derive from existing stage, target-size, replay, and P5 owners.

### R19 - P5/P7 pointer existence is insufficient after replay-only reprepare

A replay-only change deliberately need not change the target binding, so binding-keyed CV/final/P7 pointers can still exist while their replay parents are stale.

Currentness is identity-based:

- if effective replay mode, scientific source/true-label authority, pseudo prediction/qualification/split, training transport, or TRUE_DFT monitor lineage changes such that current P5 method/replay lineage differs, old CV acceptance/final publication is historical and cannot authorize production/qualification;
- the frozen target collection remains the input to newly required CV;
- identical-byte relocation or representation-only reconstruction that preserves replay scientific lineage does not stale P5 evidence;
- a P7 qualification/release descendant cannot remain current if its parent final publication is no longer current.

Do not delete immutable P5/P7 evidence merely to make status correct. Currentness is validated, not manufactured by cleanup.

### R20 - observation purity

`status`, `advance` planning, and qualification status must not:

- parse the full replay corpus;
- construct a MACE replay provider;
- run foundation prediction;
- run pseudo qualification/split construction;
- materialize replay views;
- hash/read all prediction shards;
- create evidence/cache/workspace state or mutate CampaignStore.

They may read TOML plus compact CampaignStore/receipt/P5/P7 metadata needed for currentness. If compact evidence is insufficient, report blocked/waiting rather than performing expensive work or declaring stale evidence current.

## 9. Cache disposition and user-visible observability

### R21 - expensive replay work is observable at its owner

At `prepare`, explicit pseudo mode distinguishes at minimum:

- authenticated prediction-cache hit;
- cold prediction build because no current cache exists;
- rebuild because stored prediction state is stale/incompatible/corrupt/unusable.

Report effective replay mode and enough stage context to explain a long/high-VRAM operation. Do not create a durable cache-status database.

P5 output describes consumption/authentication of prepared replay state, not pseudo-label generation.

Doctor output for explicit pseudo mode distinguishes prerequisite validation from prediction-dependent qualification deferred to prepare.

## 10. Affected implementation surface

Implementation must inspect at minimum:

- `mdstats/training_data/replay.py`
  - single-source selector normalization/default;
  - exact split seed/ratio validation;
  - source/true-label/view identities and relocation semantics.
- `mdstats/training_data/replay_invalidation.py`
  - preserve minimal invalidation; explicitly account for the parallel TRUE_DFT monitor branch in pseudo mode.
- `mdstats/training_data/replay_pseudolabel.py`
  - cache hit/miss diagnostics;
  - single-flight publication/scratch ownership;
  - provider ownership/lifetime;
  - executor lifetime/device/OOM learning;
  - label-blind input.
- `mdstats/training_data/model_features.py`
  - only if existing provider/executor lifecycle primitives need narrowing/factoring; prefer existing close/executor machinery.
- `mdstats/training_data/_campaign_cli_core.py`
  - doctor replay validation leak;
  - construction-oriented `_single_source_replay_context` separation/narrowing;
  - `_persist_single_source_replay_authority` atomic exact-alias replacement;
  - `_build_replay_plan` / `_resolve_true_label_replay_inputs` construction-capable downstream routes;
  - process-local replay context cache;
  - init/example generation and messages.
- `mdstats/training_data/campaign_target_size_runtime.py`
  - public prepare orchestration/preflight only; target-size scientific generation remains replay-independent.
- `mdstats/training_data/campaign_prepared_generation.py`
  - verify replay remains absent from target-size preparation identity; change only if needed to preserve, not expand, that contract.
- `mdstats/training_data/campaign_post_selection_runtime.py`
  - all replay consumers use authenticated read/currentness path; no cold pseudo construction.
- `mdstats/training_data/post_selection_identity.py`
  - canonical effective mode/path-free replay policy and replay-lineage currentness; avoid gratuitous version bump.
- `CampaignStore` replay grouped read/replacement call sites
  - reuse existing atomic transaction and writer-exclusion semantics.
- replay source/index/view/cache storage owners
  - concurrent publication, retention and reconstructability.
- `campaign_lifecycle.py` plus status/advance/qualification projections
  - replay-aware P5 currentness under unchanged target binding, observation purity.
- configuration/example/README/current Architecture Manual source/specification chapters and semantic-evolution history.
- replay-unification, post-selection, multi-size, restart/currentness, storage/invalidation, lifecycle, target-size independence, P5 resource, and real-provider tests affected by the final edits.

Re-derive the final affected surface after implementation. This list is a floor, not a ceiling; affected-surface growth is not permission to expand requirements.

## 11. Acceptance matrix

| Scenario | Required outcome |
|---|---|
| no single-source or legacy replay configured | no replay work/state introduced |
| legacy split replay, no `replay_set` | historical supported behavior retained |
| single-source, omitted selector | TRUE_DFT effective mode |
| generated new campaign | explicit `label_mode = "true_dft"` |
| explicit `true_dft` | method-equivalent to omitted new default |
| explicit `foundation_pseudolabel` | pseudo mode; replay-wide prediction only in prepare cold build |
| agreeing new/legacy selectors | one canonical mode |
| conflicting/unsupported single-source selector | fail before expensive work |
| invalid scratch/naive + replay topology | fail at cheap topology preflight before target/replay expensive work |
| boolean/fractional split seed or ratio component | reject without coercion |
| cold explicit-pseudo `doctor` | no replay prediction-cache builder/provider; prediction-dependent qualification deferred |
| TRUE_DFT missing required truth | fail closed; zero pseudo fallback |
| replay-only policy edit | target-size generation/screen/provisional/frozen design unchanged; P5 descendants revalidate |
| pseudo cache hit | prepare reuses; zero model inference |
| prediction batch/shard knob edit with valid logical cache | zero reinference; no scientific replay/P5 lineage churn |
| pseudo threshold edit | requalify cached evidence; zero model inference |
| split ratio/seed edit | resplit/rematerialize; zero model inference |
| identical-byte source relocation | preserve scientific replay identity/reuse |
| pseudo source TRUE_DFT-label-only mutation, geometry unchanged | preserve pseudo predictions; refresh TRUE_DFT monitor lineage; stale P5 descendants rejected |
| deleted view + current parents | representation-only rebuild allowed; zero foundation inference |
| retained authenticated pseudo train view + reclaimed bulky prediction payload where storage allows | P5 may consume if compact current lineage authenticates |
| missing view + missing/corrupt required prediction values | P5 fails to prepare; only prepare may infer |
| pseudo -> true mode prepare | exact true-mode current alias set; stale pseudo aliases removed atomically; physical cache may remain |
| true -> pseudo mode prepare | exact coherent pseudo current alias set |
| crash before replay alias commit | prior coherent alias set remains current; new inert content not misrepresented as current |
| stale concurrent builder reaches commit after newer state | stale adoption rejected/rechecked |
| same-process source/model mutation after context-cache hit | stale context cannot authenticate |
| two same-key concurrent cold prepares | one inference owner; waiter rechecks/reuses winner |
| cold-build owner failure | no valid partial cache; later contender can safely rebuild |
| provider constructed then executor construction fails | internally owned provider retired exactly once |
| `KeyboardInterrupt` after provider acquisition | owned provider retired before surviving process regains control |
| caller-supplied provider | not closed by non-owner |
| first oversized pseudo batch OOM | learned safe bound reused by later outer batches |
| labeled source passed into pseudo pipeline | provider receives geometry-only structures |
| replay failure after target-size publication | target-size generation survives; public prepare incomplete/failed |
| `status`/`advance` after replay failure | read-only projection routes back to prepare; no hidden replay construction |
| accepted CV then replay lineage changes, same frozen target | old CV/final/P7 non-current; target binding unchanged; route to CV |
| identical replay reprepare/relocation | applicable P5 evidence stays current |
| representation-only reconstruction | applicable P5 evidence stays current |
| high genuine external VRAM baseline | unchanged TRAIN2 zero-safe admission blocks correctly |

## 12. Required validation and falsification

### Stage A - configuration/topology/doctor ownership

Required focused + affected regression:

- omitted/explicit/legacy/conflict/unsupported selector tests through the real resolver;
- exact integer/ratio malformed counterfactuals;
- generated init/example TRUE_DFT checks;
- replay/method topology preflight tests proving invalid config fails before target builder and replay source/provider work;
- explicit-pseudo cold doctor test with live failpoint below replay prediction construction proving the replay prediction path does not fire and no prepared replay current aliases/prediction cache are created;
- doctor output test proving prediction-dependent pseudo qualification is deferred rather than fabricated;
- TRUE_DFT default real-owner test proving no replay foundation-prediction constructor fires, paired with explicit-pseudo prepare cold case proving the hook is live.

### Stage B - prepare/persistence/currentness rewiring

Required focused + affected regression:

- doctor -> prepare cases for no replay, TRUE_DFT, pseudo hit, pseudo cold, pseudo post-qualification failure, and retry;
- target-size generation survives replay runtime failure and replay-only edits;
- exact alias replacement pseudo -> true -> pseudo;
- failure injection between filesystem build and compact alias commit;
- stale-builder commit-time revalidation;
- coherent group read/no hybrid old-new record set;
- same-process replay context source/foundation mutation and identical-byte relocation control;
- P5 CV/final/recovery read-only routes; structural negative call-graph search proving no production P5 route can reach foundation prediction construction;
- missing-view/current-parent representation-only repair and missing-prediction fail-to-prepare cases;
- repeated fold/size/run instrumentation proving no O(folds/runs) whole-corpus replay reconstruction.

### Stage C - invalidation/storage/lifecycle

Required focused + affected regression:

- existing ReplayInvalidationPlan matrix remains correct;
- explicit pseudo TRUE_DFT-label-only mutation counterfactual: prediction cache reused, pseudo qualification/split preserved when their parents are unchanged, TRUE_DFT monitor lineage refreshed, P5 descendants stale;
- prediction batch/shard knob changes do not reinfer or churn scientific lineage on a valid cache;
- storage-allowed bulky prediction-payload reclaim with authenticated view retained;
- target-size replay-independence tests;
- `status`/`advance`/qualification-status cases for replay failure, replay lineage change, no-op reprepare, relocation, representation repair, and old P5/P7 pointers;
- observer-purity instrumentation: zero whole-corpus parse, provider construction, prediction, qualification, materialization, or write.

### Stage D - provider/concurrency/resource lifetime

Required focused + affected regression:

- exactly-one provider close ownership on success/failure/transfer-gap;
- caller-owned provider not closed;
- bounded `KeyboardInterrupt`/cancellation cleanup;
- device-binding and persistent OOM-learning test across outer batches;
- label-blind provider-facing input test;
- two concurrent cold prepares for the same cache key -> exactly one inference owner, winner recheck/reuse;
- owner failure then waiter takeover; no live scratch deletion/corrupt final cache;
- concurrent representation publication if affected;
- no overlap of prepare-owned model-scale providers after each one's final consumer.

Each coherent executable stage runs its focused and affected stage-local regression before dependent executable work proceeds.

### Stage E - final assembled and target-host evidence

Before implementation Review readiness:

- re-derive the final affected surface;
- run complete affected replay/post-selection/currentness/restart/storage/lifecycle/target-size/P5 scheduler regression;
- run project-required lint/type/build/package checks applicable to the changed surface;
- regenerate required current documentation/package derivatives through repository owners; unavailable required tooling is blocking;
- reconcile materially affected existing P5 target-host evidence on the final candidate;
- run both real target-host resource realizations below.

#### E1 - in-process real MACE/CUDA provider-retirement proof

Use the production replay prediction/preparation owner with real MACE/CUDA in a Python process that stays alive after the owner returns. Force a cold explicit-pseudo prediction path by removing only reconstructable cache state.

Capture as available:

- NVML aggregate/process occupancy;
- `torch.cuda.memory_allocated()`;
- `torch.cuda.memory_reserved()`;
- max allocated/reserved;
- acquisition, inference high-water, final-consumer, close, and post-close boundaries.

Required signature:

```text
clean/context-scale baseline
  -> one replay provider/model resident
  -> bounded inference high-water
  -> final replay prediction consumer completes
  -> explicit owner cleanup returns
  -> process remains alive
  -> allocated/reserved/NVML return to ordinary context-scale residency
```

A shell process exiting after prepare is not sufficient; process exit would mask an unclosed provider.

#### E2 - assembled CLI stage proof

**TRUE_DFT default:**

- representative valid `replay_set`, omitted `label_mode`;
- `doctor` performs no replay-wide foundation prediction;
- `prepare` performs zero replay pseudo prediction;
- `cross-validate` reaches initial TRAIN2 admission without replay-foundation model-scale residue or prediction pass.

**Explicit pseudo cold cache:**

- clean baseline; remove only reconstructable state required to force cold prediction;
- `doctor` performs no replay-wide prediction;
- `prepare` performs exactly the legitimate replay prediction workload, under single-flight ownership, and retires its provider;
- immediately run `cross-validate`; no replay foundation prediction occurs there before TRAIN2;
- no orphan owned provider/process remains after normal completion or controlled interruption;
- TRAIN2 admission observes only real current occupancy and retains zero-safe behavior.

The pseudo prediction peak itself need not be small. The governed claim is correct stage ownership, bounded execution, non-overlap/single-flight, and retirement before downstream training. If correct pseudo prediction itself exceeds the supported prepare-time resource envelope, route that separate resource issue; do not weaken lifetime/admission semantics.

## 13. Evidence applicability and relationship to existing P5 CUDA work

### Still applicable with impact review

- target-size P1/P2/common prepared-generation evidence, because replay exposure is absent;
- target-size screen/reducer evidence for its target-only method;
- manual provisional/frozen target-data choices;
- TRAIN2 zero-safe/live-memory controller evidence whose executable owner is unchanged;
- explicit historical pseudo-mode evidence as evidence of pseudo mode, not of the new default;
- replay tests whose propositions are mode-independent and unaffected.

### Review-required/rerun

- generated/default config tests that assumed pseudo by omission;
- doctor replay tests that assumed doctor materializes/qualifies full single-source pseudo replay;
- replay prepare/restart/currentness tests that relied on construction-capable P5 helpers;
- P5 lifecycle/currentness tests under unchanged target binding;
- concurrent replay cache publication tests;
- real CUDA pseudo evidence that allowed process exit to stand in for provider retirement;
- assembled P5 target-host evidence that traversed the old pre-CV replay construction path.

The separate active TRAIN2 P5 workplan remains binding. This plan removes an owned pre-TRAIN2 source of high baseline occupancy but does not weaken the scheduler's 90% envelope, per-job estimate, zero-safe admission, live-memory checks, cancellation/reaping, or fail-before-EVAL2 behavior. Genuine external/process pressure must still block.

## 14. Documentation, specification, and semantic history

### Current owners to reconcile

Update current configuration/specification/Architecture Manual sources so they state, without contradiction:

- single-source omitted default is TRUE_DFT; generated config says it explicitly;
- foundation pseudo replay remains explicit opt-in;
- doctor validates but does not run replay-wide pseudo prediction or publish prepared replay state;
- public prepare coordinates independent target-size and replay preparation;
- target-size scientific generation/screen remains replay-independent;
- post-selection consumes authenticated replay authority and never cold-builds pseudo science;
- disposable replay representations may be repaired from current parents without foundation inference;
- replay current alias publication is coherent/atomic and currentness is identity-based;
- provider ownership ends at final preparation consumer; model-scale prepare scopes do not silently overlap;
- execution batch/shard/OOM-learning realization is not scientific replay identity;
- post-selection-only replay changes invalidate P5 descendants, not the current target-only target-size experiment.

Current Part IV wording that broadly says a materially different method requires a new target-size experiment must be reconciled with the more precise current target-only screen ownership: only a method dimension that actually parents/is measured by that screen invalidates it; downstream replay-only method changes do not.

Regenerate tracked assembled/generated docs through repository publication owners. Do not hand-edit generated derivatives.

### Semantic evolution

Record concise history because the recurrence is likely to matter again:

- new single-source replay defaults to source truth while pseudo remains supported explicit opt-in;
- later orchestration refactoring regressed the already intended doctor/prepare/P5 separation and allowed replay-wide foundation inference/provider residency to leak before TRAIN2;
- the repair restores preparation/consumption ownership, atomic currentness, single-flight cache publication, and explicit provider lifetime rather than compensating in the scheduler;
- execution-only replay batch/shard choices remain outside scientific identity;
- pseudo training predictions can survive source-truth-only changes while the independent TRUE_DFT monitor lineage must refresh.

History explains why; current configuration/architecture/specification remains normative.

## 15. Explicit non-goals

Do not:

- change TRAIN2 VRAM fraction, per-job estimate, zero-safe/live-memory safety to accommodate leaked replay residency;
- add scheduler-entry `torch.cuda.empty_cache()` as the primary lifetime fix;
- add a second replay cache family/readiness database/currentness generation/provider registry/GPU lease manager/scheduler/retry DB;
- make replay a target-size prepared-generation parent;
- add a P5 fallback builder for missing pseudo science;
- silently fall back from missing TRUE_DFT labels to pseudo labels;
- remove pseudo replay support;
- change pseudo scientific numerical settings merely to reduce peak VRAM;
- persist OOM-learned batch size as scientific identity;
- bulk-invalidate target-size/P5 evidence or bump method/schema versions for a routing-only correction;
- delete immutable historical evidence or valid physical caches merely to make mutable current aliases look clean;
- rewrite frozen historical records under the new default.

## 16. Reopen, simplification, and Challenge triggers

### D4-local blockers

Remain under this workplan for ordinary nonconformance such as:

- another construction-capable doctor/P5 call site;
- stale mode alias;
- missed provider exit;
- invalid cache/currentness check;
- concurrency race;
- repeated source scans;
- observer side effect;
- stale test/doc/generated artifact.

### D3 reopen

Reopen D3 only if evidence establishes that the accepted contract cannot be implemented without materially changing architecture, for example:

- replay science genuinely must become part of target-size prepared-generation identity;
- P5 genuinely requires live foundation-provider ownership beyond prepare;
- safe replay currentness requires a new durable currentness authority rather than the existing compact record transaction + identity checks;
- safe concurrent cache creation cannot be achieved by a narrow existing/generalized artifact fence plus winner recheck;
- current replay invalidation/storage reconstruction is structurally incapable of representing the required semantics.

Before adding machinery, re-attempt the simpler reduction: separate construction from consumption, normalize once, publish one coherent alias set, use content identities, make ownership single-valued, and remove duplicate paths.

### D1/D2 route

Route upstream only if the TRUE_DFT default or existing pseudo/true modes reveal a real scientific/numerical incompatibility or require a changed statistical/numerical method.

### Serious Challenge

Raise `SERIOUS CHALLENGE` only if accepted current authorities become materially contradictory, ambiguous, inadequate, or unrealizable. None is established by this final review.

## 17. Final PASS criteria

Implementation is Review-ready only when all of the following hold on the final assembled candidate:

1. omitted current single-source mode resolves canonically to TRUE_DFT; generated config states TRUE_DFT explicitly;
2. explicit pseudo and supported historical compatibility meanings remain correct; unsupported/conflicting selectors fail before expensive work;
3. exact replay config domains reject coercion-based malformed values;
4. invalid replay/method topology fails at cheap public-prepare preflight before target/replay expensive work;
5. doctor performs no replay-wide pseudo prediction/materialization/prepared-alias publication and truthfully defers prediction-dependent qualification;
6. TRUE_DFT prepare performs zero pseudo inference/fallback;
7. prepare owns explicit pseudo prediction/qualification/materialization while replay remains outside target-size prepared-generation identity;
8. replay-only changes preserve target-size generation/screen/provisional/frozen target design exactly when target parents are unchanged;
9. prepared replay current aliases publish as one coherent exact mode-appropriate group; stale mode aliases are atomically retired without deleting valid physical/history content;
10. stale/concurrent builders cannot overwrite newer replay state; readers cannot assemble hybrid generations;
11. process-local replay caching cannot bypass authenticated source/foundation/current-policy identity;
12. all P5 consumers are scientific-read-only and no production P5 route can cold-run replay foundation inference;
13. disposable views remain reconstructable from authenticated parents, while missing required prediction values route only to prepare;
14. minimal invalidation and identical-byte relocation are preserved;
15. pseudo source-truth-only mutation preserves valid pseudo prediction science while refreshing the independent TRUE_DFT monitor lineage and invalidating dependent P5 evidence;
16. prediction batch/shard/graph-cache/OOM-learning execution realization does not cause scientific lineage churn or needless reinference on a valid logical cache;
17. exactly one owner retires every internally acquired pseudo provider across success, failure, transfer gap and catchable cancellation; caller-owned providers remain caller-owned;
18. one device-correct OOM-learning lifetime spans a cold prediction build and later batches do not retry a known-unsafe size;
19. same-key concurrent cold builds are single-flight, recheck after fencing, and cannot corrupt/delete another live attempt;
20. pseudo foundation inputs remain geometry-only/source-label-blind;
21. prepare-owned model-scale provider scopes do not silently overlap after their final consumers;
22. cache hit/cold/rebuild and deferred-doctor-versus-prepare ownership are user-visible without a second status authority;
23. `status`/`advance`/qualification currentness distinguishes replay-lineage changes from relocation/representation changes, stays observational, and never runs expensive replay/model work;
24. old P5/P7 pointers cannot authorize stale descendants under changed replay lineage, while immutable history remains intact;
25. TRAIN2 zero-safe/live-memory protections remain unchanged and continue to reject genuine unsafe occupancy;
26. explicit true/pseudo method/schema identities do not churn merely because routing/lifetime code was repaired;
27. current docs/spec/config and required generated derivatives agree with final ownership/default/currentness semantics;
28. semantic history records the recurring stage/lifetime/currentness lessons without becoming current authority;
29. all focused/stage-local/final affected regression and project-required checks pass on the final candidate;
30. real target-host E1 proves provider retirement while the process remains alive, and E2 proves doctor/prepare/P5 stage routing plus clean pre-TRAIN2 ownership;
31. materially affected evidence from the related P5 workplan is rerun/reassessed, and every required unavailable/unexecuted check remains explicitly blocking rather than inferred green.

Literal compliance with helper names is insufficient. Independent Software Design Review must reconstruct the assembled behavior and reject any implementation that still performs replay-wide pseudo work in doctor/P5, duplicates currentness/ownership, over-invalidates target-size or execution-only knobs, leaves a concurrent/provider lifetime race, weakens storage reconstruction, or relies on process exit/scheduler cleanup to conceal an unretired owner.
