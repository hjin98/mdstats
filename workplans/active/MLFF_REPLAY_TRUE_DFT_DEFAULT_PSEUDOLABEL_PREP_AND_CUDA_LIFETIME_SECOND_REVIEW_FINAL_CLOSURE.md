---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-R2-CLOSURE
protocol_version: 6.2
status: active-ready-for-implementation
parent_workplan: workplans/active/MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_REPAIR_WORKPLAN.md
parent_amendment: workplans/active/MLFF_REPLAY_TRUE_DFT_DEFAULT_PSEUDOLABEL_PREP_AND_CUDA_LIFETIME_SECOND_REVIEW_AMENDMENT.md
parent_amendment_commit: e90f8420d499cd029ed70e9c2d23b90201a4d08f
baseline_commit: 2f56df276d022760588aa5fd3ec7bbe5479ad6ea
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
review_disposition: PASS-after-this-closure
serious_challenge: none
precedence: This is the final closure of the second Software Design review. It adds only the residual constraints below. Where it conflicts with the parent workplan or second-review amendment, this closure controls; all non-conflicting obligations remain binding.
---

# Final closure of the second replay Software Design review

## 0. Disposition

A final falsification pass over the second-review amendment found four residual handoff gaps. None requires a new scientific authority or a new runtime subsystem. They are closed here by tightening the existing configuration preflight, CampaignStore replay-record replacement, replay/P5 currentness projection, and target-size/replay separation.

The combined workplan is **PASS / frozen for implementation** after these corrections. No Serious Challenge is active.

The governing simplification remains:

```text
validate configuration before expensive work
  -> target-size owner remains target-only
  -> replay prepare owner publishes exactly one current replay record set
  -> P5 resolves currentness from method/replay identity, never from mere pointer existence
  -> representation-only repair stays cheap
  -> pseudo cold inference stays prepare-only, single-flight, and explicitly retired
```

## 1. Residual gap: invalid replay configuration must fail before unrelated expensive preparation

### R21 - front-load cheap replay/topology validation at the public `prepare` boundary

The second-review amendment requires invalid single-source selectors and invalid replay/training topology to fail before replay-wide inference, but that is not sufficient. `prepare` coordinates both the independent target-size preparation and replay preparation. A malformed replay declaration discovered only after rebuilding the target-size substrate would waste substantial work and could publish a valid target-size generation during an invocation that was doomed by a configuration error known at entry.

Before any source-wide target preparation, replay source scan, model inspection/inference, materialization, or durable publication, `prepare` must run the **cheap canonical configuration/topology preflight** that is sufficient to decide whether the configured replay interface is syntactically and semantically admissible:

- normalize current/legacy replay label selectors through the one canonical resolver;
- validate exact split seed/ratio domains required by R10/R11;
- validate mixed single-source/legacy path prohibition;
- validate that replay configuration is compatible with the resolved training-method topology (`multihead_replay` versus scratch/naive modes);
- validate mutually contradictory selectors/options that are knowable without reading the replay corpus or loading the foundation model;
- reuse the already-required doctor/current-config gate and existing canonical post-selection topology resolver rather than creating a prepare-only replay interpretation.

The preflight is configuration-only. It does **not** move source authentication, prediction-cache inspection, pseudo qualification, or other expensive replay science into a new stage.

If this cheap preflight fails, the invocation must perform zero target-size rebuilding, zero replay source-wide parsing, zero provider construction, and zero new scientific publication.

Runtime/data failures discovered only after valid preflight retain the parent's partial-success rule: an independently valid target-size generation already published before a later replay runtime failure remains valid and is not rolled back.

**Required evidence:** inject an invalid/conflicting replay selector and an invalid scratch/naive+replay topology into a campaign whose target preparation would otherwise perform observable work. Prove rejection occurs before the target-size builder/source reader and before every replay provider/source-wide owner.

## 2. Residual gap: mode transitions must replace the exact current replay alias set

### R22 - publish one exact current replay record set; retire stale mode-specific aliases atomically

Baseline `CampaignStore` already provides `replace_records_atomically(records, delete_keys=...)`, specifically to delete stale aliases and publish a replacement record set in one database transaction. Reuse that owner instead of inventing a replay generation or a new currentness database.

The existing replay persistence path currently writes fixed record keys such as the common source/config/split records plus mode-specific true/pseudo records. A transition from `foundation_pseudolabel` to `true_dft` can otherwise leave old pseudo-only keys in the generic current-record namespace. Even if the new P5 reader ignores them, they remain falsely current-looking to other readers/storage accounting and can pin obsolete external payloads.

For single-source replay preparation, define the bounded union of replay **current aliases** already owned by this pipeline. On successful publication:

- publish exactly the common records plus the records applicable to the effective label mode;
- delete mode-specific current aliases that are not applicable to the newly effective mode in the **same short CampaignStore transaction**;
- use `replace_records_atomically` or an equivalent existing atomic replacement path; do not sequence independent `delete_record` / `put_record` calls;
- perform all source/model/prediction/materialization work before this short transaction;
- commit-time currentness revalidation from R14 still applies so a stale long-running builder cannot replace a newer replay state;
- readers must observe either the old coherent alias set or the new coherent alias set, never a mixture;
- deleting a current alias does not require deleting the underlying content-addressed/reconstructable cache bytes. Physical cache retention/reclamation remains owned by storage and the replay cache owners;
- historical P5 evidence remains immutable in its P5 object store. This requirement retires only mutable **current replay aliases**, not scientific history.

This is a reduction of ambiguity using machinery already present in the baseline.

**Required evidence:** prepare explicit pseudo, then switch to true and prepare again; prove every pseudo-only current alias is absent while reusable physical prediction/cache content may remain. Reverse true -> pseudo and prove one coherent pseudo set appears. Force failure between filesystem build and CampaignStore replacement and prove the old alias set remains intact.

## 3. Residual gap: lifecycle must distinguish pointer existence from current replay/method identity

### R23 - `status` / `advance` must classify P5 descendants against current replay identity after re-prepare

The baseline lifecycle observer reads binding-keyed P5/P7 pointers and authenticates the pointed object's own digest. That proves the record is internally authentic, but it does not by itself prove the record still represents the **current replay method/lineage** when replay configuration or replay source authority changes without changing the target-size binding.

This matters because replay-only re-preparation deliberately preserves the target-size generation and frozen selected `N`. Therefore the P5 pointer namespace does not automatically change as it would after a new target-size generation.

The corrected lifecycle must obey all of the following:

1. **Identity, not prepare timestamp.** Whether old CV/final evidence remains current is decided by the current post-selection method and replay-lineage identities, not by the fact that `prepare` ran again or by a newer stage timestamp.
2. **Scientific replay change.** If effective label mode, source scientific content/true-label authority, pseudo prediction policy, pseudo qualification authority, split authority, or required train/TRUE_DFT-monitor lineage changes such that the current P5 method/replay lineage differs, an old CV acceptance/final publication under the same target binding is historical. `status` must not report it COMPLETE/current, and `advance` must not route through it to production/qualification.
3. **No-op/relocation preservation.** Re-running `prepare` with semantically identical replay state, including an identical-byte replay-source relocation that preserves scientific replay lineage, must **not** stale otherwise valid CV/final evidence merely because the locator or prepare-stage digest changed.
4. **Representation-only preservation.** Deleting/reconstructing an allowed disposable replay view/index/receipt without changing authenticated scientific lineage must not stale CV/final evidence.
5. **Frozen target preservation.** Replay-only re-preparation must not thaw, clear, replace, or regenerate the operator's provisional/frozen target-size design when the target-size generation remains current. After a genuine replay-method/lineage change, the same frozen target collection remains the input to the newly required CV.
6. **Downstream qualification cannot ride a stale final product.** For a single-size campaign, an old P7 qualification/release pointer remains historical if its parent final-production publication is no longer current under the replay method/lineage. `advance` must not route to qualification from a stale final publication.
7. **Currentness is resolved, not manufactured by deletion.** Do not delete immutable P5/P7 evidence or clear pointers merely to make lifecycle output look right. Reuse the existing P5 validation/currentness semantics and compare the pointed plan/acceptance/publication against the compact current method/replay parents. Current pointers may remain historical references; they are simply not accepted as current when their parents differ.

The exact D4 factoring is delegated. Prefer a pure currentness helper shared by consequential P5 resolution and lifecycle observation over a second lifecycle-specific replay interpreter.

### Observation purity is non-negotiable

`status`, `advance` planning, and qualification status remain observational surfaces. They must not:

- parse the full replay ExtXYZ corpus;
- construct/load a MACE inference provider merely to decide status;
- run foundation prediction, pseudo qualification, split construction, or view materialization;
- hash/read all prediction shards or perform model-scale work;
- create evidence roots, cache files, or mutate CampaignStore state.

They may read the campaign TOML, compact CampaignStore record identities/digests, small replay receipts/current records, and immutable P5/P7 object metadata needed to validate lineage. Baseline `CampaignStore.record_digest(...)` and the coherent owner-snapshot/read-transaction pattern are available and should be reused where sufficient.

If a cheap observer cannot establish currentness from existing compact evidence, it must report a blocked/waiting consequential check rather than silently declaring stale evidence current or performing the expensive check itself.

**Required evidence:**

- accepted CV under pseudo -> change qualification threshold so effective replay lineage changes -> re-prepare -> frozen target binding unchanged, old CV/final not reported current, `advance` routes to `cross-validate`;
- accepted CV under true -> relocate identical replay bytes -> re-prepare -> replay scientific lineage unchanged and old CV/final remains current;
- mutate source true labels under a mode where TRUE_DFT monitor lineage changes -> re-prepare -> old CV/final becomes historical without changing selected `N`;
- delete/reconstruct a disposable view with unchanged lineage -> old CV/final remains current;
- instrument `status`/`advance` to prove zero source-wide parse, zero MACE provider construction, zero prediction/materialization, and zero writes.

## 4. Residual gap: lifecycle gating must not contaminate target-size ownership

### R24 - composite prepare currentness does not make replay a target-size selection parent

R18 correctly makes the public `prepare` stage incomplete when configured replay preparation fails. That orchestration fact must not be misimplemented as a new scientific dependency from replay onto target-size selection.

Preserve the distinction:

```text
public lifecycle routing
  init -> doctor -> prepare -> select-target-size -> cross-validate

scientific target-size ownership
  target P1/P2/P3 parents only
  replay exposure = none
```

Therefore:

- `status`/`advance` may wait at `prepare` until all configured preparation prerequisites are complete;
- the target-size generation, screen evidence, recommendation, provisional entries, and frozen entries remain valid across replay-only failure/change when their own target-size parents are unchanged;
- do not add replay label/source/prediction digests to target-size generation, screen, candidate, recommendation, provisional, or frozen-selection identity;
- do not add a replay-ready predicate inside the target-size scientific owners merely to enforce public lifecycle order;
- if a user directly invokes a target-size operation that the existing target-size owner can validly execute on its current generation, this repair must not make replay science a new reason that target-size evidence itself becomes invalid. Any public command-order restriction should remain at the orchestration boundary, not inside target-size scientific identity;
- replay-method changes after the target design is frozen trigger P5 revalidation/CV as governed by R23, not re-selection of `N`.

**Required evidence:** with a frozen or provisional target design, force replay prepare failure and then repair/reprepare replay. Prove target generation and target design digests are unchanged. Change only replay label mode and prove the same. Separately prove P5 replay/method lineage changes when it should.

## 5. Updated affected surface and final falsification

The second-review affected surface is extended by these existing owners/surfaces:

- the beginning of `execute_current_prepare()` (or its existing public prepare orchestration owner) for cheap configuration/topology preflight before expensive target/replay work;
- `_persist_single_source_replay_authority()` and `CampaignStore.replace_records_atomically(...)` for exact replay current-alias replacement;
- the union of currently written single-source replay record keys and storage reachability derived from those aliases;
- `campaign_lifecycle.py` owner snapshot / prepare / per-size P5 / qualification projections;
- existing P5 current plan/acceptance/final-publication validators, only as needed to expose a pure reusable currentness proposition rather than duplicating their semantics;
- lifecycle/status/advance tests covering replay-currentness perturbations under an unchanged target binding.

Before implementation review readiness, perform these additional falsification passes:

1. **No wasted-work preflight:** invalid replay/topology config cannot reach target-size rebuild or replay source/model work.
2. **Exact-alias mode switch:** pseudo -> true and true -> pseudo leave exactly the active replay current-alias set; no stale mode-specific alias remains current.
3. **Replay-only target preservation:** threshold/split/label-mode/source-locator changes never alter target-size generation/design unless an independent target parent also changed.
4. **P5 currentness counterfactual:** under the same frozen target binding, a replay-lineage-changing reprepare makes old CV/final/P7 descendants non-current.
5. **No-op counterfactual:** semantically identical replay reprepare / identical-byte relocation does not invalidate P5 evidence.
6. **Observer purity:** `status`/`advance` make the above distinction using compact/read-only evidence and perform no expensive replay/model work or mutation.

## 6. Final combined PASS criteria

The parent workplan and second-review amendment remain binding. In addition, implementation cannot PASS unless:

1. cheap replay/topology errors fail before any expensive public-prepare sub-operation or publication;
2. current single-source replay persistence uses the existing atomic replacement capability (or an equivalently narrow existing owner) to expose exactly one coherent mode-appropriate alias set;
3. inactive mode-specific replay aliases cannot remain falsely current or pin storage solely because a prior mode used them;
4. replay-only reprepare preserves target-size scientific generation and provisional/frozen design exactly when target parents are unchanged;
5. lifecycle observation treats P5 pointer existence as insufficient: current method/replay lineage must still match;
6. replay-lineage changes under the same frozen target binding retire old CV/final/qualification from current routing without deleting immutable history;
7. identical-byte relocation and representation-only reconstruction preserve applicable P5 evidence when scientific lineage is unchanged;
8. `status`/`advance`/qualification-status remain side-effect-free and do no source-wide or model-scale work;
9. the implementation does not solve lifecycle currentness by adding replay into target-size identity, adding a second state machine, clearing evidence as a substitute for validation, or introducing a replay-ready database;
10. every parent/amendment CUDA-lifetime, single-flight, invalidation, compatibility, documentation, regression, and target-host acceptance requirement still passes on the final assembled candidate.

After these additions, no further D3 gap is established on the reviewed baseline. Ordinary implementation misses remain D4-local; any proposal that needs a new replay generation, target-size replay dependency, scheduler cleanup hook, provider registry, or new scientific identity must be challenged against the reduction paths above before it is admitted.
