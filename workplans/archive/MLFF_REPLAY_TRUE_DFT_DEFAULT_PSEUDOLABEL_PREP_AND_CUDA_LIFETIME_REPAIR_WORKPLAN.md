---
kind: implementation-workplan
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
protocol_version: 6.2
status: active-ready-for-implementation
plan_review_state: third-design-review-consolidated
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
implementation_baseline_commit: 2f56df276d022760588aa5fd3ec7bbe5479ad6ea
reviewed_cycle_head: c94fefff43991cd03817a4e40053740de2ad6354
highest_affected_domain: D3 configuration/stage/persistence/currentness/concurrency/resource architecture -> D4 implementation
upstream_policy_constraint: new single-source replay defaults to source TRUE_DFT labels; foundation pseudo-label replay remains explicit opt-in
serious_challenge: none
related_active_workplan: workplans/active/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_REPAIR_WORKPLAN.md
related_review_reopen: workplans/active/MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_FIFTH_REVIEW_REOPEN.md
precedence: This file is the snapshot-complete D3 -> D4 implementation contract for this replay repair. It supersedes earlier representations of this same replay workplan while preserving every non-conflicting accepted requirement. It does not supersede the separate TRAIN2 zero-safe-admission/live-memory-safety workplan, target-size scientific authority, or non-conflicting CV, production, optimizer, precision, backend, checkpoint, publication, storage, restart, or qualification authority.
---

# MLFF replay TRUE_DFT default, prepare ownership, and pseudo-label CUDA lifetime repair

## 0. Third Software Design closure

### Disposition

A third independent Protocol 6.2 Software Design falsification pass reconstructed the actual baseline configuration, replay construction, source/index/materialization, CampaignStore publication, lifecycle observation, P5 replay resolution, cache identity, concurrency, and CUDA-provider paths rather than inheriting the prior PASS conclusion.

The previous consolidated plan was directionally correct but still left six implementation-significant seams under-specified:

1. transitions from single-source replay to no replay or legacy split replay could leave stale single-source current aliases behind;
2. `doctor` currently publishes `replay_plan_doctor` / `replay_qualification` with realized semantics that it can no longer truthfully own once pseudo construction moves to `prepare`;
3. public doctor/prepare replay-currentness could still be driven by raw configuration spelling and execution-only knobs instead of canonical prepared semantics;
4. long replay construction could associate frames read from a concurrently modified external `replay_set` with pre-authenticated old geometry identities;
5. replay receipt writers using fixed temporary names could collide under concurrent prepare/rematerialization;
6. lifecycle could compare replay authority and P5/P7 pointers from different SQLite snapshots even though each sub-read was individually coherent.

These gaps are closed below without introducing a new replay generation, readiness database, provider registry, GPU lease manager, scheduler hook, or target-size dependency. The workplan is **PASS / frozen for implementation** after this consolidation. No Serious Challenge is active.

### Governing simplification

```text
one canonical replay configuration interpretation
  -> doctor: cheap prerequisite validation only
  -> prepare: construct/reuse replay science
       + verify the external content actually consumed
       + publish one exact current interface/mode alias set
  -> post-selection: authenticate/consume current replay lineage
       + reconstruct only disposable representations
  -> one narrow single-flight pseudo cache owner
       + one device-correct OOM-learning lifetime
       + one provider-retirement owner
  -> lifecycle: one coherent read of target + replay + P5/P7 currentness
  -> unchanged TRAIN2 zero-safe/live-memory controller
```

When delegated machinery creates a problem, simplify the existing resolver, persistence owner, cache owner, lifecycle snapshot, or provider lifetime before adding another durable mechanism.

## 1. Governing problem and root-cause family

The observed ~19.9 GiB pre-TRAIN2 CUDA occupancy is consistent with a cold single-source foundation-pseudolabel path entering replay-wide MACE inference before TRAIN2 scheduler admission and retaining the internally constructed CUDA provider / PyTorch allocator high-water after inference. The TRAIN2 scheduler then correctly sees a large live baseline and, under the existing 24-GiB/90%-envelope/estimated-job policy, can resolve zero safe admissions and fail closed. The scheduler is therefore not the owner of the leaked residency and must not be weakened to compensate.

Two defects are distinct and both are covered:

- **label-policy/routing defect:** new single-source omission currently does not implement the required TRUE_DFT default and may enter pseudo semantics unexpectedly;
- **pseudo realization/lifetime defect:** when pseudo mode is explicitly selected, expensive prediction belongs to `prepare`, must be single-flight, must bind the content actually consumed, and must retire the CUDA owner before P5/TRAIN2.

The plan also restores stage/currentness behavior so later refactoring cannot move the same expensive work back into `doctor`, CV, final production, recovery, or lifecycle observation.

## 2. Authority and global invariants

### D1/D2 boundary

No internal scientific or numerical meaning of either existing replay label mode changes. Preserve target/replay head semantics, objective/loss/weights, split algorithm and statistical roles, pseudo prediction numerical identity/qualification semantics, TRUE_DFT monitor meaning, optimizer/LR/precision/backend/checkpoint/CV/final-production science, except that descendants correctly become stale when their replay method/lineage parents change.

If TRUE_DFT replay cannot satisfy the accepted multi-head label-domain/E0/objective method without changing scientific/numerical semantics, stop and route to the earliest D1/D2 owner. Do not architecture-patch around it.

### D3 ownership

D3 owns this cycle's canonical configuration resolution, stage ownership, persistent replay-current alias semantics, currentness/read coherence, cache/recovery boundaries, concurrent publication, external-input stability, resource/provider lifetime, and lifecycle routing. D4 may choose exact helper factoring, lock/helper implementation, temporary-file naming, and in-memory object structure if these invariants hold.

### Target-size independence

The current target-size screen is target-only and carries no replay exposure. Replay-only changes do not by themselves invalidate the immutable target-size prepared generation, screen evidence/recommendation, provisional selection, frozen collection, or exact target membership.

Do not add replay source/mode/prediction/qualification/split/currentness to target-size generation, screen, candidate, recommendation, provisional, or frozen-selection identity merely to enforce public command order.

Public `prepare` coordinates two independent preparation owners; it does not merge them into one scientific generation.

## 3. Canonical replay configuration

### R1 - single-source default and selector normalization

When `[paths].replay_set` is present, normalize every replay label selector exactly once before source/model work:

```text
label_mode omitted + legacy mode omitted       -> TRUE_DFT
label_mode = true_dft                          -> TRUE_DFT
label_mode = foundation_pseudolabel            -> FOUNDATION_PSEUDOLABEL
legacy mode = external_true_label              -> TRUE_DFT compatibility alias
legacy mode = external_pseudolabel             -> FOUNDATION_PSEUDOLABEL compatibility alias
new + legacy selectors normalize identically  -> accept one canonical ReplayLabelMode
new + legacy selectors conflict                -> reject
unsupported legacy mode with replay_set        -> reject; never ignore/default
```

Mixed single-source and legacy split-file replay paths remain rejected. Supported legacy split-file campaigns without `replay_set` retain their existing compatibility semantics, including their historical omitted-mode behavior.

New `campaign init` output and `campaign.toml.example` explicitly emit `label_mode = "true_dft"`. Pseudo is visibly opt-in.

### R2 - exact configuration domains

At the replay/configuration owners touched here:

- `split_seed` is an exact nonnegative integer; booleans/fractions/NaN/Inf/non-integer objects are rejected rather than coerced;
- sequence split-ratio components are exact positive integers; the supported lexical string form such as `"5:1"` remains supported;
- prediction batch/shard controls and qualification booleans/numerics retain their validated owners; do not add truthiness/int-cast shortcuts;
- prediction device/backend/dtype/head come from the canonical foundation/acceleration/prediction authorities rather than independent defaults.

### R3 - method/replay topology preflight before expensive work

At public `prepare` entry, run the cheap canonical configuration/topology validation needed to reject invalid/conflicting selectors, malformed split domains, mixed replay interfaces, and replay declarations incompatible with the resolved training mode before target source-wide rebuilding, replay source-wide parsing, model loading/inference, materialization, or new scientific publication.

Reuse the existing post-selection topology/configuration owner or its normalized result. Do not create a prepare-only interpretation.

A later runtime/data failure may leave an independently valid target-size generation intact; configuration errors knowable at entry must not waste expensive preparation first.

### R4 - canonical-equivalent configuration must remain equivalent for stage currentness

Replay-related doctor/prepare currentness must descend from canonical resolved semantics and operational prerequisites, not raw TOML spelling.

Therefore:

- omitted single-source TRUE_DFT and explicit `label_mode=true_dft` are equivalent;
- agreeing supported compatibility aliases normalize to the same effective semantic choice;
- changing `prediction_batch_size`, physical prediction `prediction_shard_size`, graph-cache realization, logging/progress realization, or a learned OOM-safe width does not stale an already valid prepared replay authority merely because the raw configuration changed;
- a real semantic mode/source/prediction-policy/qualification/split change does stale the materially dependent replay preparation/currentness;
- an identical-byte source locator move may require a cheap operational rebind/current-locator refresh, but it does not change replay scientific lineage or invalidate applicable P5 evidence.

Do not use the baseline broad/raw preparation-config projection as the sole replay-completion identity where it hashes aliases or execution-only fields. Narrow the replay portion or derive replay completion from compact canonical prepared parents. This is not permission to alter the target-size prepared-generation identity.

## 4. Stage ownership

### R5 - doctor validates; it does not prepare single-source replay

For current single-source replay, `doctor` may normalize/validate replay topology, check source accessibility/schema/TRUE_DFT inventory as required by its accepted contract, validate foundation/head/runtime/acceleration prerequisites for explicit pseudo mode, and run its existing bounded accelerator smoke/qualification.

It must not:

- call the replay-wide prediction-cache builder;
- perform full replay pseudo inference;
- run pseudo qualification that depends on replay-wide predictions;
- create mode-specific train/monitor replay materializations merely to qualify the campaign;
- publish the prepared/current single-source replay alias set.

Prediction-dependent pseudo eligibility/cardinality/qualification is deferred to `prepare`. Doctor output says that explicitly.

### R6 - durable doctor replay records keep their meaning or retire

Baseline doctor currently writes `replay_plan_doctor` and `replay_qualification` using a fully realized replay plan/qualification. Removing pseudo construction from doctor must not silently reuse those durable keys with weaker semantics.

For current single-source replay:

- doctor preflight/deferred status belongs in the existing doctor-owned diagnostic payload or another already-governed doctor field; do not create a second replay readiness authority;
- `replay_plan_doctor` must not remain a current single-source alias pretending that doctor built the prepared plan. Retire it from current single-source use unless it can retain its exact historical meaning without construction, which the current baseline cannot;
- `replay_qualification` may remain only if its semantic proposition remains **realized replay qualification**. In that case single-source publication moves to `prepare`; otherwise retire the current alias rather than redefining it as preflight;
- legacy split-file doctor behavior may remain where its existing qualification is actually realizable under its supported legacy contract;
- stale historical records remain readable history but cannot authorize current prepare/P5 readiness.

No immutable historical evidence is rewritten.

### R7 - prepare owns replay construction/reuse

TRUE_DFT prepare authenticates/reuses source/index/true-label cache, builds/reuses the deterministic split under the TRUE_DFT authority, materializes/authenticates required TRUE_DFT train/monitor transports, and performs zero replay foundation inference.

Explicit pseudo prepare authenticates the source/true-label basis, resolves current foundation prediction policy, builds/reuses the foundation prediction cache, qualifies cached predictions, builds/reuses split, materializes/authenticates pseudo training transport and the independent TRUE_DFT monitor, enforces post-qualification minimum counts, and retires prepare-owned accelerator state before returning.

Public `prepare` is COMPLETE only when every configured preparation prerequisite for that invocation is current/authenticated. Replay failure after target-size publication makes public prepare incomplete/failed but does not roll back the valid target-size generation.

### R8 - all P5 replay consumers are scientific-read-only

Cross-validation, final production, restart/continuation, representative re-evaluation/recovery, and future callers of the same P5 owner obtain replay science from authenticated prepared/current records.

No P5 production route may call a construction-capable helper that can build foundation predictions, requalify under a changed policy, create a scientific split, or choose a different replay method. This includes indirect paths through current `_single_source_replay_context`, `_build_replay_plan`, `_resolve_true_label_replay_inputs`, or successors if they remain construction-capable.

P5 may reconstruct a disposable view/index/receipt only when all scientific parents needed for the representation are current/authenticated and reconstruction performs no foundation inference, requalification, or scientific resplit. Missing view + missing/corrupt prediction values routes to `prepare`.

Resolve/authenticate shared replay state once per command/shared method scope where practical; do not replace hidden GPU work with repeated whole-corpus CPU/I/O work per fold/size/run.

## 5. Persistent replay currentness and interface transitions

### R9 - one exact current replay alias set

Build/validate filesystem/cache products first, then atomically publish the exact compact current alias set using the existing `CampaignStore.replace_records_atomically(..., delete_keys=...)` capability or an equivalently narrow existing transactional owner.

The single-source current-alias union includes the existing common and mode-specific records produced by this pipeline (configuration/source/true-label/split plus applicable true or pseudo prediction/qualification/view records). Re-derive the exact union from the final implementation; do not let an unreviewed newly added alias escape replacement.

On successful publication:

- install exactly the aliases applicable to the effective current interface/mode;
- remove inactive mode-specific current aliases in the same short transaction;
- preserve physical content-addressed/reconstructable cache bytes unless their own storage owner later reclaims them;
- preserve immutable P5/history evidence;
- never expose a hybrid old/new replay record generation.

The long build never holds the CampaignStore writer lock.

### R10 - interface transitions retire stale single-source aliases

Exact-current-alias semantics apply not only to pseudo <-> true mode transitions but to replay interface transitions:

```text
single-source -> no replay
single-source -> supported legacy split replay
legacy/no replay -> single-source
```

After a **successful valid prepare/currentness transition**, mutable single-source current aliases that do not belong to the configured interface are retired atomically from the current namespace. Legacy-owned aliases remain governed by the legacy owner; do not delete them merely because a single-source implementation knows their names.

If the new configuration is invalid, do not mutate state merely to clean aliases: lifecycle/currentness must reject the old aliases against the new configuration and report the configuration blockage. If build fails before the new alias transition commits, the previous coherent alias set may remain durable but is not automatically current under the new configured method.

This avoids stale single-source records pinning storage or masquerading as current after the interface has changed without inventing a replay-generation database.

### R11 - compact commit is stale-builder safe

Before atomically replacing current replay aliases, revalidate the canonical source/config/prediction/currentness parents used by the long build under the same short writer/transaction boundary that makes the replacement current, or use equivalent existing compare-and-recheck semantics.

A stale builder that finishes after a newer prepare cannot overwrite the newer current replay authority. Filesystem cache content created by a losing builder remains inert unless its own content identity independently validates.

### R12 - process-local replay caches never authenticate

`_UNIFIED_REPLAY_CONTEXT_CACHE`, if retained, is only an execution optimization. A same-process cache hit cannot bypass source bytes, foundation checkpoint/prediction policy, split/qualification, or current canonical policy authentication.

Same-locator source/model replacement must not return stale replay science through size/mtime/path shortcuts. Identical-byte relocation remains reusable. Prefer narrowing/removing the process cache or keying/revalidating it from already-authenticated identities rather than adding another cache registry.

## 6. Stable external-input construction and cache integrity

### R13 - bind predictions/materializations to the content actually consumed

`replay_set` is external mutable input. Long replay operations must not assume that a SHA/content check performed before iteration proves the bytes later read.

Whenever a live-read replay frame is associated with a pre-authenticated geometry identity, verify the frame's current canonical replay geometry identity (or an exactly equivalent existing owner check) against the expected authenticated identity **before** publishing/associating dependent scientific/cache output.

For cold pseudo prediction in particular, the baseline pattern `identity = source.geometry_identities[source_frame_index]` is insufficient by itself. The frame passed to the prediction owner must reproduce that expected canonical geometry identity before the returned prediction is recorded under it. A geometry mutation during the long read therefore fails before a cache can authenticate under the old geometry key.

TRUE_DFT materialization similarly verifies the geometry identity and its required true-label identity before durable representation publication.

### R14 - end-of-operation source currentness and label-only reuse

Before prepared replay aliases become current, re-authenticate the external source against the source/label parents represented by the snapshot being committed.

If the source changed during construction:

- do not publish the stale prepared alias set as current;
- fail/retry through `prepare` rather than silently combining generations;
- a geometry-verified pseudo prediction cache may remain reusable **only** according to its geometry + prediction-policy identity;
- a TRUE_DFT-label-only source mutation with unchanged geometry must not force foundation reinference. On the next prepare, reuse the geometry-valid prediction cache and refresh/re-authenticate true-label cache/monitor descendants;
- a geometry change selects a different geometry-set prediction identity and cannot reuse the old cache as predictions for the new source.

Do not solve mutable-input races by copying the entire external corpus into a second authoritative source or by adding a snapshot database. Verify at the existing read/publication owners.

### R15 - no malformed old-key cache may survive a geometry race

If any frame read during cold prediction fails the expected canonical geometry identity, the attempt must not publish a prediction manifest/cache that later validates for the old source geometry set. Attempt-local scratch is discarded or left unmistakably non-current/incomplete according to the existing cache owner.

Restoring the old external source bytes later must not make a cache containing predictions from the transient changed geometry appear valid.

## 7. Concurrent replay artifact publication

### R16 - same-key pseudo cold build is single-flight

For one source-geometry + prediction-policy cache key:

```text
acquire narrow existing/generalized artifact fence
  -> recheck authenticated cache after fence
  -> hit: reuse, zero inference
  -> miss/stale: one contender becomes cold owner
  -> predict/validate/publish
  -> retire provider
  -> release fence
```

Two concurrent prepares must not both load model-scale providers for the same logical cache. Do not hold CampaignStore's global writer lock across GPU work and do not create a GPU lease DB/provider registry/replay scheduler.

Waiter-after-winner-failure may safely become the next owner. Fixed scratch names must not allow contenders to delete each other's live work.

### R17 - reconstructible receipts/materializations are concurrency-safe too

The prediction cache is not the only writer touched by concurrent replay preparation. Source-artifact receipts, unified transport-artifact receipts, source indexes, true/pseudo view receipts, and other reconstructible replay metadata that can be written by concurrent prepare/rematerialization paths must use either:

- unique attempt-local temporary files followed by atomic replace/create-or-verify; or
- the already justified narrow owner fence.

Do not use one shared fixed `.tmp` pathname that one contender can replace/unlink while another is writing it. Last-writer-wins is acceptable only for reconstructible receipts when every reader re-authenticates the resulting payload against its parents.

Preserve the existing source-index `mkstemp` style where it already satisfies this rule. Do not broaden serialization to long source parsing/GPU inference merely to protect a small receipt.

## 8. Minimal invalidation and identity

### R18 - preserve the layered invalidation matrix

At minimum:

- identical source bytes relocated -> no scientific invalidation/reinference solely for path;
- geometry change -> reindex and invalidate geometry-dependent pseudo predictions;
- TRUE_DFT-mode source truth change -> refresh truth-dependent split/materializations and P5 lineage as governed;
- pseudo prediction-policy change -> invalidate prediction cache and dependent pseudo qualification/split/view/P5 lineage;
- pseudo qualification-threshold change -> requalify cached prediction/audit evidence without foundation inference;
- split ratio/seed change -> resplit/rematerialize without foundation inference;
- deleted disposable views -> reconstruct from current parents without foundation inference;
- missing/corrupt required prediction state -> cold rebuild only under prepare.

For **pseudo mode + source TRUE_DFT-label-only mutation with unchanged geometry**, preserve valid foundation predictions and preserve pseudo qualification/split when their parents remain unchanged, but refresh/re-authenticate the independent mandatory TRUE_DFT monitor. P5 replay lineage changes when that monitor lineage changes; old dependent CV/final evidence becomes historical.

Do not treat `ReplayInvalidationPlan`'s pseudo-training result as permission to keep a stale true monitor. If the baseline invalidation owner is scientifically wrong in another way, route to its owner rather than coarse-invalidating everything.

### R19 - execution/storage realization stays out of scientific replay identity

Configured prediction batch width, physical shard size/grouping, graph-cache locator/layout, process-local learned OOM-safe batch, progress/logging, and equivalent resource realization remain non-scientific unless current upstream authority explicitly says otherwise.

Changing these fields while a logically valid prediction cache exists must not trigger foundation reinference or alter post-selection replay/method scientific lineage. A future cold build may use the new realization.

Effective mode, source scientific content, split semantics, foundation checkpoint/head/inference policy, qualification policy/result, training transport lineage, and TRUE_DFT monitor lineage participate where their current owners make them scientific.

### R20 - no gratuitous schema/method version churn

Do not bump post-selection method recipe, replay config/invalidation schemas, target-size generation tokens, or unrelated TRAIN2/replay-lineage schemas solely because routing/lifetime/currentness code moved.

Explicit true and explicit pseudo campaigns retain the same scientific method identity when effective semantics are unchanged. Omitted single-source mode is the deliberate policy-resolution change and now resolves to TRUE_DFT; old evidence whose meaning depended on another omitted interpretation is historical/review-required.

## 9. CUDA/provider/resource lifetime

### R21 - exactly one provider-retirement owner

An internally constructed pseudo prediction provider has exactly one terminal retirement owner. Either the builder owns it and the executor is non-owning, or ownership transfers once to the operation-scoped executor. Do not make both owners and rely on idempotent `close()`.

Cleanup covers success, provider validation failure, executor construction/transfer failure, graph-cache setup, source iteration, prediction/OOM failure, shard/audit/materialization I/O failure, publication failure, ordinary exceptions, and catchable cancellation/`KeyboardInterrupt` after acquisition. Caller-supplied providers remain caller-owned unless an existing explicit transfer contract says otherwise.

Returned cache/current records contain no live provider/executor/model reference. Process exit is not proof of explicit retirement.

### R22 - one device-correct OOM-learning lifetime per cold build

Prediction execution binds the effective replay device; synchronization/OOM/cache handling follows the actual CUDA device when applicable. One coherent learned-safe-batch state spans the whole cold prediction build, so later outer batches do not retry a width already shown unsafe because a helper was recreated.

Preserve ordering, prediction values/identity, audit values, and logical cache semantics.

### R23 - pseudo input remains label-blind

Foundation pseudo prediction receives geometry-only copies. Source TRUE_DFT energy/forces/stress, attached calculators, qualification outcomes, and generated train labels never enter the foundation forward graph.

### R24 - prepare-owned model-scale providers do not overlap accidentally

Acquire the replay pseudo provider only after an earlier prepare-owned model-scale provider has reached its final consumer and been retired, unless an existing resource owner explicitly admits concurrent residency under a proven budget. Default to sequencing/release, not a new GPU scheduler.

## 10. Lifecycle and observational currentness

### R25 - public prepare truth is composite without contaminating target-size science

A current target-size generation plus failed/stale configured replay means public `prepare` is not ready for downstream lifecycle routing, while target-size scientific state remains valid. `advance` routes through existing `prepare`; it does not invoke a hidden replay builder.

Replay-only reprepare/mode/source changes do not thaw or regenerate selected target size when target parents are unchanged. Genuine replay-method/lineage changes require new P5 validation/CV under the same frozen target collection.

### R26 - P5/P7 pointer existence is not currentness

Binding-keyed P5/P7 pointers can survive a replay-only change because target binding is unchanged. Current status therefore checks that pointed CV/final/qualification descendants still bind the current post-selection method/replay lineage.

A changed effective replay mode/source scientific authority/pseudo policy/qualification/split/train view/TRUE_DFT monitor that changes current replay lineage makes old CV/final/P7 descendants historical. Identical-byte relocation, semantically identical reprepare, or representation-only reconstruction with unchanged scientific lineage does not stale them.

Do not delete immutable evidence merely to make lifecycle output correct.

### R27 - lifecycle uses one coherent target + replay + P5/P7 snapshot

The existing `campaign_owner_snapshot()` already protects public observation from combining target revision and P5/P7 pointers that never coexisted. Extend that same coherent observation boundary to every compact replay-current alias/digest needed to judge P5/P7 currentness.

It is **not sufficient** to read target/P5/P7 pointers in one transaction and then read replay aliases in a second individually coherent snapshot. A concurrent prepare could otherwise produce a lifecycle answer combining P5 pointers from one instant with replay authority from another.

Use one SQLite read transaction or an exactly equivalent existing coherent-snapshot owner for the relevant compact rows. Do not add a second lifecycle currentness database/registry.

Consequential P5 commands still perform their own full admission/currentness checks after advisory status routing.

### R28 - observation stays cheap and side-effect-free

`status`, `advance` planning, and qualification status must not parse the full replay corpus, construct a MACE replay provider, run prediction/qualification/split construction, materialize views, hash/read all prediction shards, create evidence/cache state, or mutate CampaignStore.

They may read TOML and compact CampaignStore/receipt/P5/P7 metadata. If compact evidence cannot establish currentness, report blocked/waiting rather than doing expensive work or declaring stale evidence current.

## 11. Cache disposition and user-facing diagnostics

At `prepare`, explicit pseudo mode distinguishes at least:

- authenticated prediction-cache hit;
- cold prediction build because no current cache exists;
- rebuild because stored prediction state is invalid/incompatible/corrupt.

Report effective replay mode and enough owning-stage context to explain long/high-VRAM work. P5 describes consumption/authentication of prepared replay state. Doctor distinguishes prerequisite validation from prediction-dependent qualification deferred to prepare. No durable cache-status DB is added.

## 12. Affected implementation surface

Inspect and re-derive at least:

- `mdstats/training_data/replay.py`: canonical single-source resolver, exact split validation, source/true-label/view identity, geometry verification/materialization;
- `mdstats/training_data/replay_index.py`: source/index stability and already-safe unique receipt publication;
- `mdstats/training_data/replay_invalidation.py`: preserve minimal invalidation plus independent TRUE_DFT-monitor branch;
- `mdstats/training_data/replay_pseudolabel.py`: per-frame geometry binding, cache hit/miss/rebuild, single-flight/scratch, provider/executor lifetime/device/OOM, label-blind input, publication;
- `mdstats/training_data/model_features.py` only where existing provider/executor lifecycle primitives need narrowing/factoring;
- `mdstats/training_data/_campaign_cli_core.py`: doctor construction leak, doctor replay-record semantics, construction/read split, process cache, fixed-temp replay receipts, atomic exact-alias/interface replacement, canonical stage replay projection, init/example/messages;
- `mdstats/training_data/campaign_target_size_runtime.py`: public prepare preflight/orchestration only; preserve target-size generation independence;
- `mdstats/training_data/campaign_prepared_generation.py`: verify replay remains absent from target-size generation identity;
- `mdstats/training_data/campaign_post_selection_runtime.py`: all P5 replay consumers become authenticated reads; no pseudo cold build;
- `mdstats/training_data/post_selection_identity.py`: canonical effective mode, path-free replay method/lineage, no gratuitous version bump;
- `mdstats/training_data/campaign_lifecycle.py`: one coherent target + replay + P5/P7 observation snapshot and replay-aware currentness;
- CampaignStore grouped read/replacement transaction seams; reuse existing writer/exclusive-transaction behavior;
- replay storage/retention owners affected by current-alias retirement and reconstructable cache/view retention;
- config example/init generation, README, current Architecture Manual/spec sources, semantic-evolution history;
- replay-unification, post-selection, multi-size, restart/currentness, lifecycle/observation, storage/invalidation, target-size independence, P5 resource and real-provider tests.

Affected-surface growth is not authority growth. Do not opportunistically redesign unrelated subsystems.

## 13. Implementation stages and stage-local evidence

### Stage A - canonical config and doctor ownership

Implement R1-R6. Run focused resolver/default/legacy/conflict/exact-domain tests; invalid-topology preflight; generated config checks; cold explicit-pseudo doctor failpoint proving no prediction/provider/prepared aliases; doctor-record migration semantics; TRUE_DFT zero-pseudo construction with explicit-pseudo prepare liveness control.

### Stage B - prepare/current aliases/read boundary

Implement R7-R12 and R25-R28 as one persistence/currentness stage where practical. Exercise true/pseudo/no/legacy interface transitions, exact alias replacement, failure before compact commit, stale-builder commit race, same-process context masquerade, coherent lifecycle snapshot, representation-only read/rebuild, and repeated-fold no-rescan behavior. Preserve target-size generation/design across replay-only changes.

### Stage C - stable input/cache concurrency/resource lifetime

Implement R13-R17 and R21-R24. Exercise mid-read geometry mutation, label-only mutation control, concurrent receipt writers, same-key two-prepare single-flight, winner failure/waiter takeover, exactly-one provider close, catchable cancellation, device binding/OOM-learning persistence, label-blind input, and provider non-overlap.

### Stage D - invalidation/identity/storage/docs

Implement/verify R18-R20 plus storage/current docs/history. Exercise threshold/split changes, view deletion, prediction cache corruption, identical relocation, batch/shard non-invalidation, pseudo TRUE_DFT-monitor refresh, storage-allowed prediction-payload reclaim, and method/schema identity preservation.

### Stage E - assembled regression and target-host qualification

Re-derive final affected surface; run complete affected replay/P5/lifecycle/storage/target-size/TRAIN2 regression and repository-required lint/type/build/package checks; regenerate tracked documentation derivatives through their owner; reconcile materially affected P5 evidence; then run the real target-host proofs below.

No executable dependent stage closes on only a later full-suite run; stage-local focused + affected regression is required after each coherent executable stage.

## 14. Required falsification matrix

Implementation Review must include counterexamples strong enough that a disconnected/bypassed owner cannot pass:

- omitted, explicit true, explicit pseudo, agreeing legacy alias, conflicting alias, unsupported single-source mode;
- boolean/fractional split seed/ratio and invalid replay/training topology fail before expensive work;
- omitted TRUE_DFT -> explicit TRUE_DFT leaves replay semantic stage currentness equivalent;
- prediction batch/shard edit with valid logical cache causes no reinference/scientific lineage churn;
- cold explicit-pseudo doctor never enters replay-wide prediction and cannot publish prepared replay aliases;
- legacy/current `replay_plan_doctor` / `replay_qualification` cannot be reinterpreted as weaker current proof;
- pseudo -> true -> pseudo leaves the exact mode alias set;
- single-source -> valid no-replay and single-source -> legacy retire single-source current aliases without deleting physical history/cache;
- invalid interface transition leaves old durable aliases non-authorizing under current invalid config;
- failure between filesystem build and alias commit preserves old coherent alias set;
- stale long-running builder cannot overwrite newer replay state;
- two concurrent same-key cold prepares produce exactly one foundation-inference owner;
- winner failure allows one waiter takeover without partial-valid cache;
- concurrent source/view receipt publication cannot fail through fixed-temp collision;
- mutate replay geometry after initial source validation but during cold indexed inference: per-frame identity mismatch prevents any old-key cache from authenticating; restoring old file cannot reuse malformed predictions;
- mutate only source TRUE_DFT labels with geometry unchanged: no foundation reinference; true-label monitor refreshes and dependent P5 evidence stales;
- source/model replacement after process-context cache hit cannot return stale science;
- identical-byte relocation preserves scientific lineage and applicable P5 evidence;
- deleted view + current parents can rematerialize without foundation inference; missing view + missing required prediction values routes to prepare;
- storage-allowed reclamation of bulky prediction payload does not invalidate an independently authenticated retained pseudo training view when compact parents suffice;
- lifecycle reads replay aliases and target/P5/P7 pointers from one coherent observation snapshot; a forced publication race cannot create a status combination that never existed;
- status/advance perform zero whole-source parse/provider/prediction/qualification/materialization/writes;
- provider construction success followed by executor construction failure closes internal provider exactly once; caller provider close count remains zero;
- `KeyboardInterrupt` after provider acquisition retires the internal provider while process stays alive;
- first oversized pseudo batch learns a smaller safe batch and later outer batches do not retry known-unsafe width;
- provider-facing pseudo structures contain no source truth/calculator label payload;
- replay-only change leaves target-size generation/screen/provisional/frozen design digests unchanged but changes P5 replay/method lineage when scientifically required;
- genuine external high VRAM occupancy still blocks TRAIN2 under unchanged zero-safe admission.

Structural absence evidence must search all final production call sites, not only edited helpers. Helper-only or preseeded-context tests cannot close production routing/currentness claims.

## 15. Real target-host resource qualification

### E1 - in-process provider-retirement proof

Using real MACE/CUDA and the production replay prediction/preparation owner, force a cold explicit-pseudo path in a Python process that remains alive after the owner returns. Capture available NVML aggregate/process occupancy and PyTorch allocated/reserved/max metrics around provider acquisition, inference peak, final consumer, close, and post-close.

Required signature:

```text
clean/context-scale baseline
 -> one replay provider resident
 -> bounded inference high-water
 -> final prediction consumer completes
 -> explicit owner cleanup returns
 -> process remains alive
 -> allocator/NVML occupancy returns to ordinary context-scale residency
```

A shell process exiting is not proof of explicit close.

### E2 - assembled CLI stage proof

**TRUE_DFT default:** representative valid labeled `replay_set`, omitted label mode; doctor runs no replay-wide pseudo inference; prepare runs zero pseudo inference; cross-validation reaches TRAIN2 admission without replay-foundation model-scale residue/prediction.

**Explicit pseudo cold:** clean baseline and remove only reconstructable state needed for a cold cache; doctor runs no replay-wide prediction; prepare performs the one legitimate single-flight replay prediction workload and retires the provider; immediately run cross-validation and prove no replay-wide prediction occurs before TRAIN2; no orphan owned provider/process remains after normal completion or controlled interruption.

The pseudo prediction peak need not be small. The claim is correct stage ownership, stable-input cache integrity, bounded/single-flight execution, non-overlap, and retirement before downstream training. If correct pseudo preparation intrinsically exceeds the supported prepare-time resource envelope, route that separate resource issue rather than weakening this contract or TRAIN2 admission.

## 16. Evidence applicability and relation to the active P5 scheduler repair

Still-applicable evidence may be preserved with reason when its executable owner/claim is unchanged, including target-size prepared-generation/screen evidence and TRAIN2 zero-safe/live-memory controller unit evidence.

Review/rerun evidence materially affected by this repair, including default/generated config tests, doctor replay tests, replay prepare/restart/currentness tests, P5 construction/read routes, lifecycle currentness under unchanged target binding, cache publication/concurrency tests, and assembled target-host evidence whose pre-CV path previously constructed replay.

A stale pass is not admissible confirmation. Every affected item is resolved, preserved-with-reason, rerun, or explicitly unavailable/blocking.

The separate active P5 CUDA workplan remains binding. This replay repair removes an owned source of pre-TRAIN2 baseline contamination but does not change its VRAM fraction, per-job estimate, zero-safe/live-memory checks, cancellation/reaping, or fail-before-EVAL2 behavior.

## 17. Documentation and semantic history

Update current config/spec/Architecture Manual sources to state consistently:

- single-source default TRUE_DFT; generated config explicit;
- pseudo replay explicit opt-in;
- doctor validates/defer-realizes but does not prepare pseudo science;
- realized single-source replay qualification/current aliases belong to prepare, not a weakened doctor record;
- public prepare coordinates independent target-size and replay preparation;
- target-size generation/screen remains replay-independent;
- post-selection consumes authenticated replay authority and does not cold-build pseudo science;
- current alias semantics include interface retirement, not only true/pseudo mode switch;
- external replay frames are identity-verified at long-read use/publication boundaries;
- replay cache/receipt concurrency uses atomic/fenced publication;
- canonical-equivalent config and execution-only batch/shard choices do not create scientific/currentness churn;
- provider lifetime ends at the final prepare consumer and model-scale scopes do not accidentally overlap;
- lifecycle currentness is one coherent target+replay+P5/P7 observation;
- replay-only method changes invalidate P5 descendants, not the current target-only target-size experiment.

Reconcile any broad Part IV statement implying every downstream method change requires a new target-size experiment with the precise current target-only screen dependency.

Regenerate tracked assembled/generated docs through repository publication owners; do not hand-edit derivatives.

Record concise semantic evolution for recurrence prevention: source truth is the new single-source default; pseudo stays opt-in; replay-wide pseudo inference belongs only to prepare; provider lifetime ends there; current replay aliases are exact-interface state; long mutable-source reads must verify consumed geometry identities; execution batch/shard realization is not scientific identity; pseudo predictions may survive truth-label-only changes while the independent TRUE_DFT monitor refreshes. History explains why; current owners remain normative.

## 18. Explicit non-goals

Do not:

- weaken TRAIN2 VRAM/admission safety or add scheduler-entry cache flush as the primary fix;
- add a second replay cache family, readiness/currentness database, replay generation, provider registry, GPU lease manager, scheduler, retry DB, or P5 fallback builder;
- make replay a target-size scientific parent;
- copy the external replay corpus into a new authoritative snapshot merely to avoid TOCTOU verification;
- silently fall back from missing TRUE_DFT labels to pseudo;
- remove pseudo support or change its scientific numerical settings merely to reduce VRAM;
- persist learned safe batch as scientific identity;
- make raw config spelling or physical cache layout scientific identity;
- bulk-invalidate target-size/P5 evidence or bump schemas/recipe versions for routing/lifetime fixes;
- delete immutable history or valid physical caches simply to clean mutable current aliases;
- rewrite frozen historical records under the new default;
- hold the campaign-wide SQLite writer lock over source-wide parsing or GPU inference.

## 19. Reopen / Challenge triggers

### D4-local

Keep within this workplan: another doctor/P5 construction route; stale mode/interface alias; doctor record with weakened semantics; stage-currentness false invalidation; input TOCTOU miss; fixed-temp replay writer collision; hybrid lifecycle snapshot; missed provider exit; cache/currentness failure; repeated source scans; observer side effect; stale test/doc/generated artifact.

### D3 reopen

Reopen D3 only if evidence proves the contract cannot be realized without materially changing accepted architecture, for example if replay science must become target-size identity; P5 genuinely needs a live foundation provider; safe currentness requires a new durable authority rather than the existing compact transaction/identity owners; safe same-key cache publication cannot use a narrow existing/generalized fence; or current replay invalidation/storage reconstruction cannot represent the required state.

Before any addition, re-attempt the simpler reduction: normalize once, verify at use, separate construction from consumption, publish one exact alias set, use one coherent snapshot, use content identities, make ownership single-valued, and remove duplicate paths.

### D1/D2 route

Route upstream if the TRUE_DFT default or existing pseudo/true realization exposes a genuine scientific/numerical incompatibility or requires a changed statistical/numerical method.

### Serious Challenge

Raise `SERIOUS CHALLENGE` only if accepted current authorities become materially contradictory, ambiguous, inadequate, or unrealizable. None is established by this review.

## 20. Final PASS criteria

Implementation is Review-ready only when the final assembled candidate satisfies all of the following:

1. omitted single-source label mode resolves to TRUE_DFT and generated config states it explicitly;
2. explicit pseudo and supported legacy meanings remain correct; conflicting/unsupported selectors fail early;
3. replay exact-domain values are validated without coercion shortcuts;
4. invalid replay/training topology fails before expensive public-prepare work;
5. canonical-equivalent true-label spelling and execution-only prediction batch/shard changes do not create false replay stage/scientific invalidation;
6. doctor performs no replay-wide pseudo prediction/materialization/current replay publication and does not silently weaken historical doctor replay-record semantics;
7. realized single-source replay qualification/current state is prepare-owned or redundant current aliases are explicitly retired;
8. TRUE_DFT prepare performs zero pseudo inference/fallback;
9. explicit pseudo prediction/qualification/materialization occurs only under prepare construction ownership;
10. target-size generation/screen/provisional/frozen design remain unchanged under replay-only changes when target parents are unchanged;
11. current replay aliases are one coherent exact **interface- and mode-appropriate** set, including single-source -> no/legacy transitions;
12. stale/concurrent builders cannot overwrite newer current replay state or create hybrid current rows;
13. process-local caches cannot bypass source/foundation/current-policy authentication;
14. frames consumed in long replay construction reproduce the authenticated geometry identity before prediction/materialization output is associated with it;
15. a mid-build geometry mutation cannot leave an old-key malformed prediction cache reusable later;
16. source change before current-alias commit fails/retries coherently; label-only mutation preserves geometry-valid pseudo predictions but refreshes true-label descendants;
17. replay receipts/materialized metadata use concurrency-safe temporary/publication ownership; no shared-temp collision survives;
18. same-key concurrent cold prediction builds are single-flight and recheck after fencing;
19. all P5 replay consumers are scientific-read-only; missing scientific prediction values route only to prepare;
20. disposable representations remain reconstructable from authenticated parents without foundation inference;
21. minimal invalidation/identical-byte relocation are preserved, including the independent TRUE_DFT-monitor branch in pseudo mode;
22. execution/storage cache knobs do not change scientific replay/P5 identity or cause needless reinference;
23. no gratuitous scientific/schema version churn occurs;
24. every internally acquired pseudo provider has exactly one retirement owner across success/failure/transfer-gap/catchable cancellation, while caller-owned providers remain caller-owned;
25. one device-correct OOM-learning lifetime spans a cold build and known-unsafe widths are not retried per outer batch;
26. pseudo prediction input remains source-label-blind;
27. prepare-owned model-scale providers do not accidentally overlap after their final consumers;
28. cache hit/cold/rebuild and doctor-deferred-versus-prepare ownership are user-visible without a second status authority;
29. lifecycle distinguishes composite prepare truth from target-size scientific validity and preserves frozen target selection under replay-only change;
30. old P5/P7 pointers cannot authorize stale replay descendants, while no-op/relocation/representation-only changes preserve applicable evidence;
31. lifecycle captures target revision, replay currentness rows, and P5/P7 pointers in one coherent observation snapshot and remains side-effect-free/model-free;
32. TRAIN2 zero-safe/live-memory semantics remain unchanged and reject genuine unsafe occupancy;
33. current docs/spec/config/generated derivatives and semantic history agree with the final architecture;
34. focused/stage-local/final affected regression and repository-required checks pass;
35. real target-host E1 proves explicit provider retirement while the process remains alive, and E2 proves doctor -> prepare -> P5 routing plus clean pre-TRAIN2 ownership;
36. materially affected evidence from the separate P5 workplan is reconciled, and every required unavailable/unexecuted check remains explicitly blocking.

Independent Software Design Review must reconstruct the assembled behavior rather than accept helper-name compliance. Reject any implementation that still performs replay-wide pseudo work in doctor/P5, leaves stale interface/current records, trusts pre-read source identity across a mutable long read, combines lifecycle snapshots from different instants, over-invalidates execution-only knobs or target-size science, leaves provider/concurrency races, weakens storage reconstruction, or relies on process exit/scheduler cleanup to conceal an unretired owner.
