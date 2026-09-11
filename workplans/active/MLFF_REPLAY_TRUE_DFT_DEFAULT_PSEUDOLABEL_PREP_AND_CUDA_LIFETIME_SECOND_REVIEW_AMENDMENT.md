---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-R2
protocol_version: 6.2
status: active-ready-for-implementation
parent_workplan: workplans/active/MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_WORKPLAN.md
parent_reviewed_commit: 741b57564470d390ae10d2ef5fddcde81af9cb09
baseline_commit: 2f56df276d022760588aa5fd3ec7bbe5479ad6ea
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
review_disposition: PASS-after-this-amendment
serious_challenge: none
precedence: This amendment is part of the implementation contract. It narrows, corrects, and completes the parent workplan at parent_reviewed_commit. Where wording conflicts, this amendment controls. All non-conflicting parent obligations remain binding.
---

# Second Software Design review amendment: replay TRUE_DFT default / prepare ownership / CUDA lifetime

## 0. Review disposition

A second independent Protocol 6.2 Software Design review was performed against baseline `2f56df276d022760588aa5fd3ec7bbe5479ad6ea`, with the parent workplan at `741b57564470d390ae10d2ef5fddcde81af9cb09` treated as the candidate D3 -> D4 handoff rather than as truth.

The parent is directionally correct and its core repair remains unchanged:

```text
single-source replay_set
  -> TRUE_DFT by default
  -> pseudo labels only by explicit opt-in

public prepare
  -> target-size preparation under its existing independent owner
  -> replay preparation under replay owners when configured

post-selection consumers
  -> authenticate/consume replay lineage
  -> never cold-run replay-wide foundation inference

explicit pseudo cold build
  -> one bounded inference/resource lifetime
  -> explicit provider retirement before downstream TRAIN2
```

No Serious Challenge is active. Current target-size prepared-generation architecture, current P5 method/replay identity, replay invalidation layering, provider-lifetime doctrine, storage/reconstruction behavior, and the stakeholder default-policy decision are jointly realizable.

The second pass nevertheless found material handoff gaps that could still permit a superficially compliant implementation to regress configuration validity, storage reclamation, concurrent cold-build safety, lifecycle routing, or evidence invalidation. The corrections below close those gaps without adding a new scientific authority, replay stage, provider registry, scheduler hook, readiness database, or target-size generation.

After applying this amendment, the combined workplan is **PASS / frozen for implementation**.

## 1. Governing clarifications

### 1.1 Historical REPLAY-UNIFY records are evidence, not current authority

The archived REPLAY-UNIFY1D/1E architecture revisions are valuable semantic history showing that replay-wide foundation prediction was deliberately assigned to `prepare`, but history is not a second current normative owner.

Implementation is governed by:

1. the stakeholder policy fixed for this cycle: new single-source replay defaults to source TRUE_DFT and pseudo replay is explicit opt-in;
2. accepted current Architecture Manual/specification invariants, including replay/method identity, target-size replay independence, provider lifetime, storage/currentness and public lifecycle ownership;
3. the parent workplan plus this amendment as the bounded cycle contract.

Use REPLAY-UNIFY history to understand/restoratively simplify the concretization, not to bypass current authority acceptance. Any Architecture Manual edits made during implementation remain candidate D3 reconciliation until they pass the repository's normal independent design review/acceptance process.

### 1.2 Target-size prepared generation is already replay-independent

Baseline inspection confirms `campaign_prepared_generation.preparation_configuration_identity()` binds only the neutral partition policy, target-size policy, and target-size common-training policy. Replay configuration is not part of that immutable generation identity.

Do **not** redesign this owner. Preserve that separation. The generic public `prepare` stage/configuration projection may include replay fields so lifecycle status becomes stale when replay prerequisites change, while the target-size scientific generation itself remains current if its own parents are unchanged.

This distinction must remain explicit:

```text
public prepare-stage currentness
  may depend on replay prerequisites

TARGET-SIZE prepared-generation currentness
  must not depend on post-selection-only replay label/source policy
```

### 1.3 No accidental target-size performance scope expansion

The parent correctly requires that a replay-preparation failure must not roll back or discard a valid target-size generation. It does **not** require this repair to optimize away whatever target-size validation/reconstruction the accepted target-size `prepare` owner legitimately performs on a retry.

On retry, execute the existing target-size preparation/currentness path as governed; if it proves the same generation, preserve/adopt it normally. Do not add a replay-specific bypass around target-size `prepare`, and do not turn this replay repair into a new target-size performance project.

## 2. Configuration contract closure

### R10 - exact single-source configuration domain; no silently ignored selector

R1 is strengthened as follows.

When `[paths].replay_set` is present, the canonical single-source resolver must normalize and validate **all** replay label selectors before source/model work:

```text
label_mode omitted, legacy mode omitted
    -> TRUE_DFT

label_mode = true_dft
    -> TRUE_DFT

label_mode = foundation_pseudolabel
    -> FOUNDATION_PSEUDOLABEL

legacy mode = external_true_label
    -> TRUE_DFT compatibility alias

legacy mode = external_pseudolabel
    -> FOUNDATION_PSEUDOLABEL compatibility alias

label_mode + supported legacy mode
    -> accepted only if both normalize to the same label authority

legacy mode = none | mp_shortcut | preselected | other unsupported value
    -> reject for single-source replay_set; do not ignore it and default TRUE_DFT

conflicting selectors
    -> reject before expensive work
```

An explicit selector can never become inert merely because a newer selector/default exists. Normalize compatibility aliases once, then downstream consumers receive only the canonical `ReplayLabelMode`.

Correct the parent's acceptance row `no replay_set -> no new replay work or state`, which was too broad. The actual cases are:

- no `replay_set`, no supported legacy replay source/configuration -> no replay;
- no `replay_set`, supported legacy split-file replay -> preserve its existing compatibility behavior exactly;
- replay policy/label declaration without the source topology required by the selected training method -> fail through the existing post-selection topology/configuration owner rather than silently treating it as no replay.

The current P5 topology remains binding: replay preparation is authorized only for a valid replay-enabled/multi-head replay method topology. Scratch or naive-fine-tuning configurations that reject replay today must still reject it **before** replay-wide preparation is attempted. Reuse the existing canonical topology/method resolver or its normalized result; do not implement a second prepare-only interpretation of whether replay is meaningful.

### R11 - exact integer/boolean/numeric validation at the resolver being changed

Because this cycle already modifies the canonical single-source resolver, close the adjacent validate-before-canonicalization defect rather than preserving silent coercion.

At minimum:

- `split_seed` must be an exact nonnegative integer; booleans, fractional numerics, NaN/Inf and non-integer objects must not be truncated/coerced by `int(...)`;
- sequence-form `split_ratio` components must be exact positive integers and must reject booleans/fractional values rather than truncating them;
- the documented string form such as `"5:1"` remains supported and is parsed according to its existing lexical contract;
- replay qualification booleans/numerics and prediction batch/shard controls touched by this implementation must continue through their existing validated owners; do not introduce a new truthiness/int-cast shortcut while rewiring prepare;
- effective replay prediction device/backend/dtype/head come from the existing resolved prediction/foundation/acceleration authorities. Do not let `prepare`, the executor, and method identity read independently defaulted configuration namespaces and disagree.

This is a narrowing/repair of the existing resolver, not a new configuration system.

**Additional evidence:** malformed exact-domain cases (`true`, `1.5`, negative seed, zero ratio component, unsupported legacy modes, conflicting aliases), plus valid canonical/compatibility cases. Prove rejection occurs before source parsing/provider construction.

## 3. Persistence, currentness, and storage closure

### R12 - process-local replay context cache may accelerate, never authenticate

The baseline `_UNIFIED_REPLAY_CONTEXT_CACHE` is keyed partly by locator/stat/config information and can return an already-built context. The parent says this cache is non-authoritative; make that executable.

A process-local cache hit must never bypass the content/currentness checks that would be required without the cache. In particular:

- source identity must be authenticated through the existing SHA/content receipt owner, not trusted from path + size + timestamp alone;
- explicit pseudo mode must authenticate the effective foundation checkpoint/prediction policy identity, not merely the foundation model pathname;
- replay policy/split/qualification identities relevant to the cached context must still agree with current canonical configuration;
- a stale in-memory context cannot survive a same-process source or foundation-file replacement merely because a cheap cache key collides;
- identical-byte source relocation remains scientifically reusable.

Prefer deleting/narrowing the process cache or keying/revalidating it from already-authenticated identities over adding another cache-validation layer. Reuse the existing SHA-256 receipt machinery; do not create a parallel hashing registry.

**Additional evidence:** in one live process, establish a cache hit, mutate/replace the replay source and (for explicit pseudo) the foundation checkpoint at the same configured locators, then prove stale replay science cannot be returned. Include an identical-byte relocation/control case so the safety fix does not become coarse invalidation.

### R13 - downstream P5 authenticates lineage, not gratuitous retention of bulky reconstruction payloads

Narrow R4 where it could be read to require physical presence of every pseudo prediction shard/cache object during every P5 use.

The scientific requirement is that P5 authenticates the **current replay lineage and method semantics** strongly enough to reject stale or masquerading training/monitor material. `ReplayPseudolabelViewArtifact` already binds prediction-cache, qualification, split and source-geometry identities into its logical lineage. Therefore:

- if a current pseudo training view and TRUE_DFT monitor view authenticate against compact persisted parent/currentness records, P5 need not keep or reread all raw prediction shard payloads merely to prove the same lineage;
- storage may reclaim reconstructable prediction payloads if the current storage owner permits that state; their absence alone must not make an already-authenticated materialized training view scientifically false;
- raw prediction/audit payload is required when an operation actually needs it to requalify or rematerialize a missing dependent representation;
- if a required view is missing and its needed prediction payload is also missing/corrupt, only `prepare` may cold-regenerate foundation predictions;
- P5 may reconstruct a view only when every required scientific parent/value needed for that reconstruction is already authenticated and the reconstruction performs no foundation inference/requalification/resplit;
- never weaken the current replay-lineage digest or artifact SHA/content checks to gain this storage flexibility.

This preserves the accepted distinction between scientific authority and reconstructable representation instead of making cache retention an accidental authority.

### R14 - replay record-group publication is atomic and readers cannot observe a hybrid generation

The existing `_persist_single_source_replay_authority()` already has a natural grouped persistence seam (`CampaignStore.put_records`). Preserve or simplify around it.

For one resolved replay authority:

- all compact records that must agree as one prepared replay snapshot are published atomically as one naturally atomic record group, after their required filesystem artifacts are durable/authenticated;
- do not expose a new source/config record while leaving old split/view/qualification records addressable as if they belonged to it;
- a downstream P5 read must either observe one internally consistent current group or reject/retry a concurrent transition; it must not assemble a hybrid old/new replay lineage from independent unfenced reads;
- do not hold the campaign-wide SQLite writer exclusion over foundation inference, source materialization, or other long work. Build outside the short commit section, then publish compact state transactionally;
- concurrent publication must not let a stale builder overwrite a semantically newer replay state. Revalidate the canonical source/policy/currentness token at commit, or use the equivalent existing compare/recheck discipline. Do not invent a second campaign-generation authority solely for replay.

**Additional evidence:** bounded concurrent/failure-injection test where configuration/source state changes or two prepares overlap between build and compact publication; prove no hybrid replay group or stale adoption becomes consumable.

## 4. CUDA/provider/concurrency closure

### R15 - exactly one provider-retirement owner, including the acquisition-transfer gap

Strengthen R5/R6. For an internally constructed prediction provider there must be **exactly one** terminal retirement owner.

Acceptable implementations include:

- cache builder retains ownership; executor is explicitly non-owning; builder closes in `finally`; or
- builder transfers ownership exactly once to the operation-scoped executor; executor closes in `finally`/context exit.

Do not have both layers independently own/close the same provider. Do not rely on idempotent `close()` to paper over ambiguous ownership.

Whichever form is selected must cover the interval:

```text
provider successfully constructed
  -> executor construction / ownership transfer has not yet completed
```

If executor construction, validation, graph-cache initialization, cancellation, `KeyboardInterrupt`, or another `BaseException` occurs in that interval or later, the internally owned provider is still retired before control returns while the Python process remains alive. Caller-supplied providers remain caller-owned.

Forced process termination is outside exception cleanup and is not evidence of correct explicit retirement.

### R16 - concurrent cold prediction builds are single-flight at the existing artifact owner

Moving pseudo inference into `prepare` must not permit two concurrent `prepare` processes for the same logical prediction-cache key to miss simultaneously and each allocate a foundation model / replay inference high-water mark on the same GPU.

For the same source-geometry + prediction-policy cache identity:

```text
contender acquires one existing/generalized artifact execution/publication fence
  -> re-authenticates/rechecks cache after acquiring the fence
  -> valid winner exists: reuse it, zero inference
  -> still absent/stale: exactly one contender becomes the cold inference owner
  -> publish/validate durable cache
  -> retire provider
  -> release fence
```

Requirements:

- use/factor an existing advisory artifact/publication lock primitive where possible; do not create a replay lock subsystem or GPU lease database;
- the fence is keyed narrowly enough that unrelated replay caches/workspaces are not globally serialized;
- do not hold the CampaignStore global writer lock across GPU inference;
- cache recheck **after** fence acquisition is mandatory, otherwise serialized contenders still duplicate the expensive build;
- interruption/failure of the owner leaves no artifact that authenticates as complete and releases the advisory OS lock when the process exits;
- the next contender may retry safely through the same owner;
- fixed temporary filenames must not allow concurrent attempts to corrupt each other. Prefer one fenced owner or unique attempt-local temporary files plus create/verify publication, rather than another cleanup/reconciliation layer;
- apply equivalent existing atomic/fenced publication discipline to concurrently reconstructed replay materialized views when they can be produced by more than one command.

This is not permission to parallelize multiple model-scale pseudo providers. Current provider scopes remain explicit/non-overlapping unless an existing resource owner specifically admits otherwise.

**Additional evidence:** two concurrent cold prepares for the same prediction identity produce exactly one foundation-inference owner and converge to one authenticated cache; a waiter after winner failure can safely become the next owner; no duplicate model-scale VRAM residency or partial valid cache occurs.

### R17 - preserve label-blind pseudo inference during executor consolidation

The one-executor simplification must preserve the existing pseudo-label anti-leakage boundary: foundation prediction consumes geometry-only copies, with source TRUE_DFT labels and attached calculator results removed before model inference.

Consolidating batching/executor/provider lifetime must not pass source labels, source calculators, qualification outcomes, or training-view labels into the foundation forward graph. The prediction identity and values for the same foundation policy/geometries must remain equivalent to the pre-refactor accepted pseudo-label method.

**Additional evidence:** use labeled replay inputs and assert that the provider-facing structures expose no source-truth/calculator label payload; pair with output identity/equivalence checks.

## 5. Public lifecycle and derived-routing closure

### R18 - `status` and `advance` must reflect the corrected composite prepare operation without creating a new state machine

The parent changes the truthful meaning of public `prepare` completion. Close the derived lifecycle consumers too.

- if target-size generation publication succeeds but configured replay preparation fails, the target-size generation remains valid, but the **public prepare stage** is not COMPLETE for the current configuration;
- `status` must expose the replay preparation failure/waiting condition rather than reporting downstream readiness solely because target-size state is current;
- `advance` must route the next consequential action back through the existing `prepare` command until configured replay prerequisites authenticate; it must not jump to selection/CV and must not invoke a hidden replay builder itself;
- a replay configuration edit that changes preparation prerequisites makes the public prepare stage stale through the existing scoped stage-config mechanism, while leaving the target-size scientific generation current if its own identity is unchanged;
- deletion of a merely reconstructable replay transport must not be represented as a new scientific generation. If current owner policy allows cheap representation reconstruction in the consuming command, `status`/`advance` need not force scientific re-prepare solely because that transport file is gone;
- no new lifecycle state enum or parallel state machine is required. Derive these outcomes from existing stage/currentness/replay owners.

**Additional evidence:** public `status`/`advance` tests for partial target-size-success/replay-failure, replay policy edit after successful prepare, valid representation-only deletion, and successful retry.

## 6. Identity/versioning and documentation closure

### R19 - do not invalidate unrelated evidence with gratuitous recipe/schema bumps

The baseline P5 method identity already contains `replay_exposure_policy_digest`, and the single-source replay policy identity already binds effective training label mode plus split semantics. Explicit TRUE_DFT and explicit pseudo therefore already separate the scientific methods once the canonical resolver is corrected.

Do **not** bump merely because code moved or a default resolver/lifetime bug was repaired:

- `POST_SELECTION_METHOD_RECIPE_VERSION`;
- `ReplaySingleSourceConfig` schema;
- `ReplayInvalidationPlan` version/schema;
- target-size generation/schema tokens;
- unrelated TRAIN2/replay-lineage schemas.

A version/schema bump is allowed only when the final implementation actually changes persisted semantics/representation in a way existing identities cannot express, with explicit owning-layer justification and dependent evidence impact. Routing/lifetime corrections should normally leave scientific identity unchanged for a campaign that already explicitly selected the same effective label mode.

Consequently:

- an existing explicit `label_mode=true_dft` campaign should retain the same replay/method semantic identity after this repair unless another independently material field changes;
- an existing explicit `foundation_pseudolabel` campaign likewise retains pseudo method identity while gaining corrected preparation/resource behavior;
- a previously omitted single-source label mode is a genuine policy-resolution change and must resolve to TRUE_DFT under the new default; any old evidence whose meaning depended on omission resolving differently is review-required/historical, not silently reused.

### R20 - reconcile current documentation at the precise ownership boundary

Current Part IV broadly says that a materially different method requires a new target-size experiment. Current target-size owners are more specific: the screen is target-only and carries no replay exposure. Reconcile this wording so future maintenance cannot reintroduce replay as a parent of the target-size screen by reading an overly broad sentence literally.

The documentation must distinguish:

```text
change to a method dimension actually measured by/parenting the target-size screen
    -> target-size evidence invalidation as currently governed

post-selection-only replay label/source policy change under a target-only screen
    -> target-size generation/screen remains applicable
    -> P5 method/CV/final descendants invalidate according to replay/method lineage
```

Also state the public prepare-stage versus target-size-generation currentness distinction from section 1.2.

Do not use historical REPLAY-UNIFY notes as the current owner; update current Architecture Manual/spec/config docs and then record only concise semantic-evolution rationale in history.

## 7. Additional affected surface

The parent affected-surface list is extended, not replaced, by:

- canonical exact-domain validation in `replay.py` for split seed/ratio and supported compatibility selectors;
- the current post-selection method/topology resolver so prepare cannot perform replay work for an invalid scratch/naive/orphan replay configuration;
- `_UNIFIED_REPLAY_CONTEXT_CACHE` or its replacement/removal, specifically its pre-return content authentication;
- `CampaignStore.put_records` / replay grouped persistence call site and downstream grouped read/currentness semantics;
- replay prediction/view publication concurrency and temporary-file behavior;
- existing advisory artifact publication/fence primitive, generalized only if necessary rather than duplicated;
- public `status` / `advance` projections of prepare currentness;
- current Architecture Manual wording that could incorrectly couple post-selection replay changes back into the target-size screen;
- version/schema constants only to verify they remain stable unless a real persisted-semantic need is demonstrated.

Affected-surface expansion does not authorize unrelated cleanup.

## 8. Additional acceptance matrix

| Scenario | Required outcome |
|---|---|
| no single-source or legacy replay configured | no replay work |
| legacy split-file replay without `replay_set` | historical supported behavior retained |
| `replay_set` + unsupported explicit legacy `mode` | fail before expensive work; never silently TRUE_DFT |
| `replay_set` + agreeing legacy mode and `label_mode` | one canonical effective label mode |
| `replay_set` + conflicting selectors | fail before source/model work |
| orphan replay label/policy under scratch/naive/no-source topology | existing topology owner rejects before replay prepare |
| boolean/fractional split seed or sequence ratio | reject, no integer truncation |
| same-process replay source/model mutation after context cache hit | stale context cannot authenticate |
| identical-byte relocation | scientific replay identity/reuse preserved |
| authenticated pseudo view present, bulky prediction payload reclaimed where storage allows | P5 may consume authenticated view without requiring needless reinference |
| missing view + current prediction payload | representation-only rematerialization allowed, zero inference |
| missing view + missing/corrupt required prediction payload | P5 fails/routes to prepare; only prepare may infer |
| concurrent replay compact publication | reader sees one internally consistent replay group or rejects/retries, never hybrid parents |
| provider constructed, executor construction fails | provider retired exactly once |
| cancellation/KeyboardInterrupt after provider acquisition | internally owned provider retired before live process returns control |
| two concurrent cold prepares for same cache key | one inference owner; contender rechecks/reuses winner |
| cold-build owner dies/fails | no valid partial cache; later contender can safely rebuild |
| labeled source passed to pseudo inference | provider receives geometry-only structures; source truth cannot leak into prediction |
| target-size publish succeeds then replay prepare fails | target-size generation survives; public prepare/status remains failed/incomplete |
| `advance` after that partial failure | routes to existing prepare owner; no hidden replay construction |
| replay-only config edit | public prepare stage becomes stale as needed; target-size generation identity unchanged |
| explicit true/pseudo campaign after routing/lifetime-only repair | no gratuitous P5 method-recipe/schema invalidation |

## 9. Additional validation and falsification

Before implementation review readiness, add the following to the parent's required evidence:

1. **Config counterfactuals:** unsupported selector, conflicting alias, exact-integer malformed values, and invalid method/replay topology all fail before provider/source-wide work.
2. **In-memory masquerade test:** a process-local replay context cannot survive semantic source/foundation mutation at the same locator through a cache-key shortcut.
3. **Storage-lineage test:** prove an authenticated pseudo training view can remain scientifically usable under an allowed reclaim of reconstructable prediction payload, while a missing view cannot regenerate missing prediction values in P5.
4. **Grouped-state race test:** force overlap/failure around replay record publication and prove no hybrid old/new record set becomes current.
5. **Single-flight cold-build test:** two concurrent prepares share one logical prediction-cache build; prove the second rechecks after fencing rather than merely waiting then recomputing.
6. **Ownership-transfer failpoint:** provider construction succeeds and executor construction/transfer fails; close count is exactly one. Repeat with caller-supplied provider to prove close count remains zero at this owner.
7. **Cancellation cleanup:** bounded cancellation/KeyboardInterrupt after acquisition cannot leave owned provider residency in a surviving process.
8. **Label-blind pseudo input:** source true labels/calculator results do not reach the foundation provider after executor refactor.
9. **Lifecycle projection:** `status` and `advance` distinguish public prepare incompleteness from independently valid target-size state.
10. **Version/identity perturbation:** routing/lifetime-only code change does not churn explicit true/pseudo method identity; changing effective label mode does.
11. **Documentation falsification:** current docs contain no statement that can reasonably be read as making post-selection replay-label choice a scientific parent of the current target-only target-size screen.

For structural absence claims, search all production call sites on the final assembled candidate, not only the functions edited. For real CUDA lifetime, the parent's in-process target-host requirement remains mandatory.

## 10. Final combined PASS criteria

The parent PASS criteria remain binding and are supplemented by the following. Implementation cannot pass until:

1. single-source defaulting never causes an explicit unsupported/contradictory selector to be ignored;
2. replay split/config values modified at this owner obey exact-domain validation rather than Python coercion;
3. only valid replay-enabled method topology can authorize replay-wide preparation;
4. process-local replay caching cannot bypass authenticated source/foundation/current-policy identity;
5. P5 authenticates sufficient replay lineage without turning reconstructable prediction-shard retention into accidental authority;
6. prepared replay compact state publishes as a coherent group and concurrent readers cannot consume mixed generations;
7. one internally acquired pseudo provider has exactly one retirement owner across success, ordinary failure, cancellation and the provider->executor handoff gap;
8. a same-key concurrent cold pseudo build has one expensive inference owner and rechecks after the existing/generalized artifact fence;
9. pseudo inference remains label-blind to source truth;
10. `status`/`advance` reflect corrected prepare-stage currentness without a new lifecycle state machine;
11. a replay retry does not roll back target-size authority but also does not introduce an unapproved bypass/optimization of the target-size prepare owner;
12. scientific/schema/version identities are changed only where semantic representation genuinely changes, never as blanket cache invalidation;
13. current documentation—not historical notes—carries the final accepted replay/target-size/stage ownership, with semantic history remaining explanatory only;
14. all parent acceptance, target-host qualification, affected regression, generated-documentation, P5 evidence-remap and unavailable-is-blocking obligations still pass on the final assembled candidate.

## 11. Reopen / simplification triggers

Remain D4-local for ordinary misses against this combined contract. Reopen D3 only if implementation evidence establishes that one of the following is genuinely required:

- replay science must become part of target-size prepared-generation identity;
- P5 must retain/live-read full prediction payload to authenticate an already-materialized current replay view;
- safe concurrent pseudo cache construction cannot be achieved using a narrow existing/generalized artifact publication fence plus recheck;
- replay grouped publication requires a genuinely new durable currentness authority rather than existing compact record transaction/revalidation;
- an upstream method/numerical invariant forces a different replay-label topology.

Before any such addition, attempt the simpler reduction: separate preparation from consumption, narrow cache authority, reuse content identities, make ownership single-valued, and remove duplicate construction paths. Do not respond to another resource/currentness symptom by adding a scheduler hook, fallback builder, cache-flush wrapper, replay-ready database, provider registry, or broad target-size invalidation.
