---
kind: implementation-workplan
workplan_id: MLFF-FINAL-PRODUCTION-MODEL-PUBLICATION-MH1-INTEGRATION
protocol_version: 6.4.0
status: active-reviewed
created_date: 2026-09-21
revision: 9
reviewed_date: 2026-09-22
workplan_review_status: pass-after-exhaustive-convergence-review
branch: design/mlff-final-production-model-publication-mh1-integration
basis_commit: 237448b449b6f8042de5f239e5fefdfd54e3b2c3
highest_affected_domain: D3
d1_d2_change: false
production_gpu_qualification: deferred-to-actual-campaign-and-final-release
---

# MLFF final-production model publication + lightweight MH-1 integration — D3 -> D4 workplan

## 0. Disposition

**PASS AS IMPLEMENTATION WORKPLAN AFTER EXHAUSTIVE CONVERGENCE REVIEW / FROZEN FOR D4. No Serious Challenge is active.**

This cycle closes two adjacent product-readiness gaps without changing D1 scientific or D2 numerical authority:

1. P5 already decides the correct final-production member set and selected representative checkpoint(s), but `train-production` does not materialize those selected representatives as explicit user-consumable full MACE `.model` products. Run-local MACE terminal `.model` output can instead represent the last TRAIN2 epoch.
2. The current machinery has extensive real use on MPA-0. MH-1 remains architecturally supported, but before the next MH-1 campaign the current assembled candidate needs a bounded compatibility pass for obvious family/head/shape/reconstruction drift. Long real MH-1 qualification is explicitly deferred to the user's actual campaign.

No new selection rule, target-size reducer, qualification rule, scheduler, trainer, or scientific method is authorized.

## 1. Governing current state

Current P5 authority already owns:

```text
FinalProductionPlan
  -> completed required seed runs
  -> EVAL2 representative per seed
  -> FinalProductionPublicationDecision
       target head
       exact seed evidence
       exact representative checkpoint SHA-256
       exact representative checkpoint relative path
       exact ordered published_member_ids
```

`FinalProductionPublicationDecision.member_digest` currently identifies the selected product members by:

```text
target_head_name
+ ordered (member_id, representative_checkpoint_sha256)
```

Current P5 currentness resolution replays the exact decision procedure and rejects stale method/CV/completion/committee/head lineage.

Current P7 derives its member set from that P5 decision and authenticates the selected representative checkpoint bytes before downstream use.

Current storage architecture already recognizes:

```text
<workspace>/models
artifact_id = campaign_store:models
class       = DURABLE_SCIENTIFIC_EVIDENCE
detail      = current production model evidence
```

That existing durable owner shall be reused.

## 2. Observed defect

The trainer-owned run tree can contain a normal MACE `.model` produced from the terminal checkpoint, while P5 later selects a different representative checkpoint.

The motivating N=512 run demonstrated:

```text
P5 selected representative: epoch 17
MACE terminal save/compile: epoch 29
```

Therefore:

```text
run-root trainer .model != necessarily P5-published model
```

The scientific selection is not corrupted. The product materialization/operator interface is incomplete.

## 3. Protected outcome

For every current P5-published member, successful `train-production` completion shall imply the existence of one authenticated, reloadable full MACE `.model` artifact representing exactly the portable model state of that selected representative checkpoint.

Formally:

```text
current P5 publication member
    -> authenticate exact representative checkpoint
    -> reconstruct exact accepted portable model state
    -> serialize full MACE model
    -> reload + authenticate serialized product
    -> publish subordinate model-product record
    -> report train-production publication complete
```

The materialization step is a representation of an already-decided P5 product. It has no authority to add/remove/reorder members or rerank checkpoints.

## 4. D3 ownership decision: keep selection and representation separate

### D3-1 — Preserve `FinalProductionPublicationDecision` as the scientific/member decision owner

Do **not** fold serialized `.model` metadata into `FinalProductionPublicationDecision`.

Reasons:

- the current decision is already the stable pre-qualification owner of member selection;
- existing valid v3 decisions must remain usable as scientific selection evidence;
- serialized product creation occurs after member selection and should not change the decision policy identity;
- making the decision depend on a serialized artifact that itself needs to bind the decision creates an avoidable causal/cyclic identity problem.

The current decision schema/policy semantics remain unchanged unless implementation finds an unavoidable compatibility defect and reopens D3.

### D3-2 — Add one subordinate P5 materialized-product record

Introduce one immutable P5 record, provisional architectural name:

```text
FinalProductionModelPublication
```

Exact D4 symbol name is delegated.

It MUST bind:

```text
selected_binding_digest
final_publication_decision_digest
final_publication_member_digest
target_head_name
ordered published members:
    member_id
    optimizer_seed
    run_identity
    representative_checkpoint_relative_path
    representative_checkpoint_sha256
    evaluation_model_state
    evaluated_model_state_digest
    model_execution_architecture_digest
    model_state_sha256
    model_dtype
    model_relative_path
    model_sha256
    model_size_bytes
serialization_format
serialization/exporter identity
torch/runtime serialization identity where needed for diagnosis
```

Do not invent these state identities. Reuse the current owners:

- `authenticate_post_selection_provider(...)` already returns the exact `evaluated_model_state_digest`;
- the current MACE deployment owner already computes an exact deterministic full-`state_dict` digest over names, dtypes, shapes and tensor bytes;
- `mace_model_execution_architecture_digest(...)` already owns the weight-independent execution architecture.

If the full-state digest helper must be shared, extract/refactor the existing implementation into one common MACE serialization/state-identity owner. Do not copy its algorithm into P5.

The record also defines one derived, path-independent `model_artifact_set_digest` for downstream representation currentness. It is a digest over the parent decision identity, canonical target head, and the ordered published members' exact deployment-source identities:

```text
final_publication_decision_digest
target_head_name
ordered:
    member_id
    representative_checkpoint_sha256
    evaluation_model_state
    evaluated_model_state_digest
    model_execution_architecture_digest
    model_state_sha256
    model_dtype
    model_sha256
    model_size_bytes
```

It deliberately excludes `model_relative_path`, timestamps, the operator projection path, and diagnostic exporter metadata. A workspace relocation or equivalent locator repair therefore does not invalidate numerical/deployment evidence, while any changed executable model bytes do.

This derived digest is not a second scientific member identity. `FinalProductionPublicationDecision.member_digest` remains the sole checkpoint/member-selection identity; `model_artifact_set_digest` identifies only the exact serialized representation consumed by deployment descendants.

`serialization_format`, serializer/runtime version and exporter identity are provenance/compatibility metadata, not automatic currentness tokens. A source-code or Torch/MACE version change does not by itself force reserialization of an already-authenticated full model whose bytes, state, architecture, dtype, heads and supported format remain valid. If the current loader/exporter can no longer consume that format safely, downstream use is unavailable/blocking; do not silently rewrite historical product bytes merely to make the old record look current.

The record is subordinate to the existing decision:

```text
FinalProductionPublicationDecision
       |
       v
FinalProductionModelPublication
```

It is not a second member-selection authority.

The record constructor/deserializer and current resolver must enforce, rather than merely document, these invariants:

```text
selected_binding_digest == decision.binding.content_digest
final_publication_decision_digest == decision.content_digest
final_publication_member_digest == decision.member_digest
target_head_name == decision.target_head_name

ordered model members
    == decision.published_member_ids exactly
    == same cardinality/order, no missing/extra/duplicate member ids

for each member:
    optimizer_seed / run_identity / checkpoint path / checkpoint SHA
        == exact published seed evidence in the decision

    evaluation_model_state / evaluated_model_state_digest
    model_execution_architecture_digest / model_state_sha256 / model_dtype
        == exact authenticated provider realization for that checkpoint

    model_relative_path is relative, confined and normalized
    model_sha256 is a valid full digest
    model_size_bytes > 0
```

A subordinate record may represent the decision but may never redefine committee membership, order, checkpoint ancestry, target head or learned state. Its deserializer recomputes its own content digest and rejects malformed or duplicate member identities.

### D3-3 — One current subordinate pointer

Add the minimum binding-scoped current pointer required to resolve the current model materialization, e.g. a new P5 pointer kind such as:

```text
final_production_model_publication
```

The pointer is valid only when its record binds the exact current `FinalProductionPublicationDecision.content_digest` and `member_digest`.

Do not create another database, registry, release index, or cross-size product selector.

## 5. Canonical product paths

Materialized P5 model products live under the already-owned:

```text
<workspace>/models/
```

Use a human-readable generation/size layout with an **immutable publication/member product path**, for example:

```text
models/
  production/
    g<generation>/
      N_<size>/
        decision-<full-final-decision-digest>/
          seed-<seed>-<full-model-sha>.model
        publication.json
```

Exact spelling is delegated D4. The identity rule is not:

- authoritative immutable paths use collision-proof full digests, or an engineering-equivalent collision-proof encoding; shortened digest prefixes are display-only;
- the immutable model path may depend on already-known parent/member identities such as `FinalProductionPublicationDecision.content_digest`, member id/seed, and the serialized model SHA;
- it MUST NOT depend on `FinalProductionModelPublication.content_digest` when that record itself contains `model_relative_path`, because that would create a self-referential identity cycle;
- a bare mutable `seed-1.model` MUST NOT be the canonical durable artifact;
- this cycle creates no mutable `.model` symlink/copy alias that could be mistaken for authority. `publication.json` and CLI output are the stable operator locators.

For an all-qualified committee every published member gets its own immutable model artifact.

Durable model paths are relative to `CampaignPaths.models`. Reject absolute paths, `..` traversal, symlink substitution, wrong-kind nodes, or any path that escapes the campaign model root. Workspace relocation must not change scientific or model-artifact-set identity.

The N-level `publication.json` is an operator-facing projection only. It MUST:

- carry the current decision digest, model-publication record digest, model-artifact-set digest, target head, and member model paths/SHAs;
- be written atomically only **after** the authoritative CampaignStore/P5 pointer writes for that publication succeed;
- perform that short projection refresh while still holding the same generation P5 publication barrier, or equivalently re-check the exact current pointers under that barrier immediately before replacement;
- never participate in scientific/currentness decisions;
- be safely regenerated when absent or stale by `train-production`.

This prevents an older concurrent publisher from overwriting the convenience projection after a newer publication became current.

A crash after authoritative pointer publication but before projection refresh may leave the projection absent/stale; official `status` still resolves the canonical P5 records and must report the correct product. A failed/stale-generation pointer commit must not publish a convenience projection claiming the uncommitted product is current.

Do not write selected product files into sealed trainer run roots.

Do not use the run-local MACE terminal model as the product source.

## 6. Product construction owner

The source of truth for each product is the exact selected member:

```text
run_identity
checkpoint_relative_path
representative_checkpoint_sha256
target_head_name
```

Reuse the existing authenticated P5/P7 checkpoint-provider path. The product materializer must inherit current semantics for:

- exact checkpoint-byte SHA authentication;
- TRAIN2 runtime-summary/boundary authentication;
- historical nonterminal checkpoint loading;
- live versus EMA evaluation state;
- model architecture authentication;
- foundation reconstruction;
- target/replay multihead construction;
- transient CuEq TRAIN2 realization;
- CuEq -> portable e3nn restoration;
- target-head identity.

Do not implement another checkpoint loader or MACE reconstruction path.

If a small refactor is needed so publication and inference share one exact model reconstruction owner, prefer that refactor over a wrapper or duplicate helper tree.

Production product materialization MUST use the native authenticated MACE reconstruction path with `allow_forward_override=False`. The bounded `inference_evaluator`/parameter-shell testing seam is not a valid source of a published `.model`. Tests may substitute expensive numerical forwards below an accepted owner, but real-owner publication acceptance must serialize an actual reconstructed MACE model object.

The materializer must retain the `evaluated_model_state_digest` returned by the shared checkpoint-provider owner and bind that exact digest into the model-publication member. Do not infer live/EMA state from filenames or recompute a different state convention in the serializer. The same authenticated provider instance/state that supplies the publication digest is the model object serialized.

## 7. Product serialization contract

Each published file shall be a full MACE model reloadable by:

```python
torch.load(path, map_location="cpu", weights_only=False)
```

It shall not be:

- a TRAIN2 checkpoint dictionary;
- a state dict only;
- continuation state;
- a symlink to an internal checkpoint;
- an ML-IAP artifact;
- the trainer's terminal model copied or renamed.

The published full model shall represent the same accepted portable model state exposed by the authenticated provider for the representative checkpoint.

The base publication representation is the **portable e3nn model on CPU at the accepted learned-model dtype**. Moving the already-authenticated portable model from its inference device to CPU is representation/device relocation only; it MUST NOT change learned tensor values, dtype, head inventory, buffers, or execution architecture. Do not serialize a transient CuEq/OEq/compiled training realization as the P5 product.

Before serialization, put the portable model into inference mode with `eval()`. After reload, require the root and all serializable submodules to remain in inference mode where the framework exposes that state. Training/eval mode is behavioral object state not represented by the tensor `state_dict`, so it must be checked explicitly rather than assumed from tensor equivalence.

Before save, capture the existing exact full-`state_dict` digest and canonical execution-architecture digest. After `torch.load(..., map_location="cpu")`, require exact equality of:

```text
state keys
tensor dtypes
tensor shapes
tensor values / existing full-state digest
execution-architecture digest
head inventory
published target head presence
uniform learned-model dtype
```

The provider's existing `evaluated_model_state_digest` must also be recorded so the product stays bound to the live/EMA state that P5 actually evaluated.

Do not silently change precision during base P5 publication.

Deployment/dtype conversion remains downstream P7/deployment ownership.

### D3-4A — One descriptor-authenticated published-model byte owner

A full PyTorch model is executable serialized content. P5, status and P7 must share one published-model artifact authenticator rather than reimplement path checks.

The authenticator preserves the repository's existing no-follow trust discipline:

- start from an authenticated campaign-owned `CampaignPaths.models` anchor;
- descend components relative to already-opened directory descriptors, refusing symlink/special-node substitution in intermediate components;
- open the final model with `O_NOFOLLOW` or the accepted platform-equivalent;
- prove regular-file type with `fstat()` on the opened descriptor;
- stream expected byte count and SHA-256 from that same descriptor;
- compare recorded `model_size_bytes` and `model_sha256`;
- never establish authority with `lstat(path)` followed by a separate normal open;
- never hash one pathname and then reopen an independently resolved pathname for executable deserialization.

Prefer factoring/reusing the existing descriptor-relative qualification/storage trust primitives over creating another traversal implementation.

The same owner serves P5 current resolution, train-production create-or-verify/reclosure, lifecycle/status, and P7 intake/staging. When a downstream library requires a pathname, copy authenticated bytes from the trusted descriptor into attempt-owned private scratch, fsync/hash-verify that copy, then execute from the trusted copy.

Publication uses the same anchored trust discipline on the **write side**: create/descend `production/g.../N.../decision...` relative to an opened campaign-owned models-root descriptor; reject symlink/special-node intermediate components; create private temps and the no-clobber final entry relative to the authenticated destination-directory descriptor; and fsync that directory descriptor. A pre-planted `models/production` symlink must not redirect product bytes outside the campaign models root.

## 8. Publication atomicity and restart

### D3-4 — Create-or-verify and representation reclosure

For each expected product relation:

- no current model-publication record -> materialize;
- current record + valid exact artifact set -> reuse;
- current record + missing/SHA-mismatched/wrong-kind/unsupported-format artifact -> consequential consumers fail closed, while `train-production` may explicitly reclose representation from the authenticated selected checkpoint into a new immutable artifact set + successor model-publication record;
- never overwrite or repair in place an artifact named by an immutable historical/current record.

File existence is never validity. Corrupt, missing or unsupported representation bytes are recoverable only when exact selected-checkpoint lineage remains authentic; they grant no authority to retrain, rerank or mutate the old decision.

At minimum authenticate decision/member/order, representative checkpoint SHA, evaluation state + returned evaluated-state digest, target head, architecture digest, exact full-state digest, model SHA/size and serialization-format compatibility. Reuse existing state-digest owners; define no third tensor hash.

### D3-5 — Crash-safe publication, committee transactionality, concurrency and residue

Do not hold the generation-wide P5 publication barrier or a SQLite write transaction across model reconstruction/serialization.

A multi-member committee is one logical P5 model publication. Full PyTorch model serialization is not byte-deterministic, so publication uses one stable decision/publication-set lock, not independent member locks.

The lock reuses `artifact_publication_lock` over an internal P5 coordination path derived from the **full** decision identity, for example:

```text
.mdstats/post-selection/g<generation>/
    model-publication-locks/
        <full-final-decision-digest>
```

Do not leave coordination locks in the operator-facing models tree. Lock order is fixed:

```text
decision/publication-set lock
    -> generation P5 publication barrier
        -> CampaignStore exclusive transaction
```

No path in this feature may acquire those in reverse order.

Under the publication-set lock:

1. re-read/re-authenticate the exact replayable/current decision, completion, predecessor reclosure and model-publication state;
2. if one current model-publication record names a fully valid ordered artifact set, reuse it;
3. otherwise process published members serially in canonical decision order, bounding provider/model residency;
4. for each missing/successor member, reconstruct through the native provider, retain its returned evaluated-state digest, move the exact portable model to CPU/eval mode, serialize to a private destination-filesystem temp, flush/fsync, reload/verify, compute byte SHA/size, then retire the provider in `finally`;
5. derive the immutable collision-proof final filename from decision/member identity and full model SHA;
6. publish the final directory entry with **no-clobber/create-once semantics**. `os.replace` is forbidden for immutable model evidence;
7. if the final path already exists, descriptor-authenticate size/SHA and reuse only on exact expected bytes; otherwise fail closed. Never deserialize an unreceipted pre-existing pickle merely to decide reuse;
8. after the whole ordered set is durable, build/store one immutable `FinalProductionModelPublication`;
9. enter the short generation P5 publication barrier and perform the atomic pointer-set commit in D3-6;
10. refresh the mutable operator projection only after the authoritative pointer transaction commits.

Only private attempt temps may be deleted automatically. A full-SHA immutable final model not referenced by the current pointer may be historical or pre-pointer crash residue; leave it inert. A later trusted reconstruction may byte-reuse it only when it independently derives the same expected SHA.

### D3-6 — One atomic P5 product pointer-set commit

Revision 6's ordered sequence of three independent pointer transactions is insufficient. A crash after changing model/reclosure pointers but before `FINAL_PUBLICATION` can strand the previous current product behind a hybrid pointer set.

Refactor the existing `post_selection_store` owner with the minimum batch helper required to publish these rows in **one** `CampaignStore.exclusive_transaction()`:

```text
POINTER_FINAL_MODEL_PUBLICATION
POINTER_PREDECESSOR_RECLOSURE
POINTER_FINAL_PUBLICATION
```

The helper reuses the existing pointer-key/current-frozen-design logic, performs the binding/generation stale-writer check once inside the same `BEGIN IMMEDIATE`, validates all digests before the transaction, writes all three rows atomically or none, and is idempotent when the exact set already exists. It is not a second currentness database or transaction subsystem.

Fresh-publication flow:

```text
1. decide/reproduce FinalProductionPublicationDecision
2. acquire publication-set lock
3. reauthenticate current/replayable lineage
4. materialize + verify + durably place complete model set
5. persist immutable decision / reclosure / model-publication objects
6. acquire generation P5 publication barrier
7. re-resolve/revalidate exact final plan/completion/decision
8. one CampaignStore transaction atomically publishes all 3 product pointers
9. refresh publication.json while still under generation barrier
10. release barriers/lock; only then report size complete
```

The generation barrier protects the immutable-object -> pointer window from storage mutation; the SQLite transaction protects pointer-set atomicity. Expensive work remains outside both.

For a legacy v3 decision, reclosure may atomically republish the same decision digest together with current model/reclosure pointers; it never reranks or rewrites the decision object. Fault injection must prove exceptions at every logical pointer-write position leave the visible pointer set wholly old or wholly new.

### D3-6A — Recovery classification before expensive work

After the collection-wide CV/currentness barrier and before new TRAIN/EVAL admission classify each selected size:

```text
PRODUCT_COMPLETE
    exact replayable/current final decision + completion
    + fully authenticated model publication
    + current predecessor reclosure

PRODUCT_RECLOSURE
    exact replayable final decision + completion exist
    but model publication and/or predecessor reclosure is missing, stale, corrupt or representation-incompatible

PRODUCTION_REQUIRED
    no exact replayable final decision exists for current completion/evidence
```

- COMPLETE admits no TRAIN2/EVAL2 and verifies/reuses the product.
- RECLOSURE admits no TRAIN2/EVAL2.
- If only predecessor reclosure is stale, reuse valid model bytes and build only a new reclosure.
- If only representation is stale/corrupt/incompatible while predecessor reclosure remains current, preserve the exact predecessor-reclosure object/digest and rebuild only the representation. This keeps `QualificationInputBinding` / attempt identity unchanged for a representation-only successor.
- If both are stale, repair each from its own authority, then atomically republish the product pointer set.
- PRODUCTION_REQUIRED enters the accepted final-plan/global-TRAIN/serial-EVAL2/publication machinery.
- only PRODUCTION_REQUIRED trajectories enter the global TRAIN wave;
- reclosure/materialization remains serial post-TRAIN finalization in frozen selected-size order;
- provider/accelerator residency is retired on every terminal path;
- no publication change alters the accepted adaptive TRAIN scheduler.

Classification is an admission hint, not commit authority. Every later COMPLETE/RECLOSURE action re-resolves current state under the publication-set lock, and pointer commit repeats exact upstream validation under the generation barrier. Drift aborts/reclassifies; no stale pre-TRAIN snapshot may publish.

### D3-6B — Narrow migration resolvers without weakening public currentness

This implementation changes predecessor executable source-tree identity, so strict public resolvers may reject old reclosure before migration.

`train-production` owns two narrow candidate/reclosure-only readers:

1. **decision candidate** — load the pointed final decision, authenticate current binding/final plan/completion/policy/CV/common monitor, replay `decide_final_production_publication(...)` from persisted evidence, and require exact decision digest equality while bypassing only stale predecessor executable-tree currentness;
2. **model-publication candidate** — if a subordinate pointer exists, load its immutable record without declaring it publicly current, require exact replayed decision/member binding, and authenticate every model member through the shared descriptor-authenticated owner.

This permits same decision + valid model bytes + stale predecessor source digest -> reuse model bytes, rebuild reclosure, atomically republish pointers, with zero TRAIN2/EVAL2/model reserialization.

The bypass never weakens selected binding, completion, CV/method/monitor lineage, committee replay, checkpoint ancestry, model member set, SHA/size/path trust or model-state identity. P7/public current resolvers stay strict.

### D3-6C — Projection commit and failure semantics

`publication.json` is non-authoritative mutable projection:

- write private temp + flush/fsync + atomic `os.replace` + parent-directory fsync;
- refresh only after atomic three-pointer commit while still under generation barrier;
- if projection refresh fails after DB commit, the product remains authoritative/current; later `train-production` repairs only the projection, without TRAIN2/EVAL2/model rebuild;
- status/currentness never consumes the projection;
- stale projection can never override DB/content-addressed authority.

## 9. Existing completed campaign reclosure

Existing valid P5 publication decisions that predate the new materialized-product record are not invalid scientific selections.

When `train-production` finds:

```text
current valid FinalProductionPublicationDecision
+ authentic representative checkpoint(s)
+ missing current model-product record
```

it shall perform publication-only reclosure:

```text
authenticate current decision
authenticate selected checkpoint(s)
materialize/verify full model(s)
publish subordinate model-product record
report completion
```

It MUST NOT:

- relaunch TRAIN2;
- rerun EVAL2 merely to regenerate product serialization;
- change member selection;
- change representative checkpoint;
- choose a different target size.

The current N=512/N=8192 MPA-0 campaign is an acceptance fixture for this path.

## 10. Public lifecycle semantics

### D3-7 — `train-production` completion means usable product publication

After this repair, the public final-production stage is COMPLETE for a selected size only when:

```text
current final-production plan/completion
+ current FinalProductionPublicationDecision
+ current authenticated FinalProductionModelPublication
+ current predecessor-reclosure record
```

all agree.

The predecessor-reclosure requirement is operational lineage/readiness, not a new scientific decision. It prevents `train-production` from reporting a fully published product that the strict P7 exposure boundary must immediately reject as stale.

A decision-only historical/current state with no materialized model is a recoverable WAITING/reclosure state, not COMPLETE.

This is an intentional strengthening of the operator-visible D3 lifecycle, not a change in scientific selection.

Successful `train-production` finalization must make the product explicit **in that command's own output**, not only through a later `status` call. After the authoritative product pointer-set commit, print one deterministic line per published member, in frozen size then decision-member order, containing at least:

```text
N
member id / optimizer seed
target head
canonical published .model path
model SHA-256
```

The completion summary must use `FinalProductionModelPublication`, never the trainer run-root terminal `.model`. In a multi-size campaign it prints every independently published size without selecting a winner. If a later size fails, already committed earlier-size product lines remain truthful durable results even though the collection command exits incomplete.

### D3-8 — Status remains observational

Extend the existing lifecycle/status projection rather than inventing a second product-status command unless current CLI ownership proves that extension impossible.

Per selected size, expose enough information to locate the product:

```text
N
publication state
member(s)
seed(s)
representative checkpoint/epoch where available
published .model path(s)
target head
```

Status MUST NOT:

- create directories/evidence stores;
- load/reconstruct MACE merely to display state;
- rerun selection;
- choose between sizes.

Use durable product-record data. A selected size may be reported COMPLETE only after status validates the record/binding/decision relation and, for every current published member, the confined regular non-symlink file's recorded byte size and streaming SHA-256. Status still MUST NOT `torch.load` or reconstruct MACE. Missing, wrong-kind, wrong-size or SHA-mismatched product bytes are BLOCKED/WAITING as appropriate, never COMPLETE.

The member count is bounded by the frozen production committee, so this integrity read is intentionally preferred over a cheap but potentially false COMPLETE result.

Both `POINTER_FINAL_MODEL_PUBLICATION` and the already-existing `POINTER_PREDECESSOR_RECLOSURE` MUST be added to `campaign_lifecycle._post_selection_prefix(...)` / `campaign_owner_snapshot(...)`. Current implementation snapshots the final-publication pointer but omits predecessor reclosure; that is no longer admissible once reclosure participates in COMPLETE.

Final-production status and `qualification status` therefore observe in the same SQLite read transaction:

```text
target-size revision / binding
current replay lineage/status
final plan
FinalProductionPublicationDecision
FinalProductionModelPublication
PredecessorReclosureRecord
P7 pointers where single-size qualification is authorized
```

Neither public observer may perform a later independent pointer read.

Concurrency acceptance must force pointer transitions and prove a status answer is always one real snapshot: before publication, an intermediate recoverable state, or after publication — never a hybrid decision/model pair.

## 11. Multi-size behavior

For selected sizes such as:

```text
[512, 8192]
```

publish independent product groups for both.

This does not authorize a cross-size winner or release choice.

Preserve the current multi-size terminal/qualification boundary:

- every size can have a complete P5 `.model` publication;
- P7 qualification remains unavailable when current authority supplies no release-product choice across sizes.

## 12. P7 consumption, selective representation currentness, and locked-evidence preservation

P7 remains downstream and cannot alter P5 membership.

### D3-13 — Keep the scientific qualification binding checkpoint-based

Revision 3 overreached by putting the new model-publication digest into `QualificationInputBinding` / `attempt_identity`.

Do **not** do that.

The current binding intentionally identifies the frozen scientific product, executable, environment, specification, evidence roles and predecessor reclosure. The new full `.model` is a subordinate representation of the same already-frozen checkpoint state. Making representation bytes part of the whole binding would stale every component, including the one-shot locked test, when only serialization changed.

Therefore preserve:

```text
QualificationInputBinding
    selected binding
    FinalProductionPublicationDecision / member digest
    executable
    environment
    specification
    evidence roles
    resource scope / predecessor reclosure
```

and keep `attempt_identity` stable for a representation-only successor that proves the same P5 decision/member/state.

P7 resolves the current `FinalProductionModelPublication` separately as an authenticated subordinate input.

### D3-14 — Invalidate only components that consume deployment representation

Current component ownership shows:

```text
deployment_parity    consumes deployed artifact
dynamics             consumes deployed artifact

physical_pes         checkpoint/member_provider
relaxation           checkpoint/member_provider
calibration          checkpoint/member_provider
locked test          checkpoint/member_provider
```

Accordingly:

- `deployment_identity(member)` binds that member's exact P5 `model_sha256`, full-state digest, target head and deployment policy;
- `component_input_digest` for `deployment_parity` and `dynamics` binds the current `model_artifact_set_digest` (or the exact equivalent per-member deployment-source identity);
- checkpoint-only components do not acquire the model serialization digest and remain reusable when all of their existing inputs remain unchanged;
- stress/capability evidence that actually depends on deployed runtime remains within the deployment-dependent input identity.

Do not invalidate all P7 evidence merely because the full-model pickle bytes/path changed.

### D3-15 — Preserve irreversible locked disclosure

`LockedActivationRecord`, its cohort-generation identity, and the append-only locked-reveal index remain unchanged by this feature.

The selective-reuse rules in D3-14/D3-15 apply only while the ordinary `QualificationInputBinding` itself is unchanged — including the executable source-tree digest, environment, specification, evidence roles and predecessor reclosure.

A representation-only successor under the same P5 decision is admissible only if the model-publication owner proves the same:

```text
member/checkpoint
evaluation state
evaluated-model-state digest
full model-state digest
execution architecture
target head
dtype
```

Therefore an already-revealed locked cohort is never opened again:

- an existing authentic locked activation/result remains evidence for the unchanged scientific checkpoint product;
- a changed deployment representation triggers only deployment-dependent requalification;
- if activation occurred but the locked result was interrupted, the same activation may resume under the existing one-shot rules;
- the append-only reveal index continues to block any attempt to manufacture a fresh locked test.

A different learned state cannot be published as a representation-only successor under the same P5 decision; that is lineage corruption and fails closed.

### D3-16 — Terminal/release currentness binds the deployment representation without rebinding the whole attempt

Add an explicit `model_artifact_set_digest` to the new terminal `ProductionQualificationRecord` and `ReleaseEvidenceIndex` schemas.

These terminal owners are current only when:

- their ordinary `QualificationInputBinding` remains current;
- their stored `model_artifact_set_digest` equals the exact current P5 model-publication artifact-set digest;
- every deployment-dependent component outcome has the expected current component-input digest;
- all other existing component/reference/currentness rules remain satisfied.

For `qualification status`, “exact current P5 model publication” means the content-addressed object named by the **captured** model-publication pointer from `campaign_owner_snapshot()`. Observation may authenticate that immutable object and its decision/member/artifact-set relation, but it must not read a later live P5 pointer. The captured predecessor-reclosure pointer is treated identically. Missing/corrupt/mismatched captured P5 objects make the P7 verdict blocked/superseded, never current.

The qualification plan and attempt identity do not need to change.

Schema evolution is explicit:

- new terminal record/release-index schemas are versioned successors (v2 or equivalent);
- old v1 objects remain readable as historical immutable evidence;
- a v1 terminal/release object lacking model-artifact-set identity cannot be reported as the current release verdict once the new P5 product boundary is active;
- **do not manufacture cross-executable compatibility:** this implementation changes the mdstats executable source-tree digest, so pre-implementation P7 component evidence is ordinarily bound to an older `QualificationInputBinding` and cannot become current merely because its scientific checkpoint is unchanged;
- the append-only locked reveal history remains binding across that executable-currentness change, so an old revealed cohort never becomes fresh;
- selective reuse of checkpoint-only/locked component evidence is allowed only for representation-only successors created under the **same current qualification binding** (for example, rebuilding corrupted serialized product bytes without changing source/spec/environment);
- deployment-dependent components are then recomputed under the current model-artifact-set identity and a new terminal/release record is reduced without reopening locked evidence.

Do not mutate historical v1 objects in place and do not weaken executable currentness to rescue them.

### D3-17 — Deployment source and parity remain independent

Current P7 has two materially different model consumers:

1. `member_provider(...)` reconstructs the selected representative from the authenticated TRAIN2 checkpoint. Keep this checkpoint-based reference path.
2. `_build_deployment_artifact(...)` changes from `checkpoint_path_for_member(...)` to the authenticated P5 full `.model`.

Target architecture:

```text
selected checkpoint
   -> authenticated member_provider
   -> reference predictions

same selected checkpoint
   -> P5 full .model publication
   -> P7 deployment exporter
   -> deployed/ML-IAP artifact

reference predictions <-> deployed predictions
```

This preserves a discriminating deployment-parity oracle.

Before deployment, verify:

```text
exact current decision
exact current model-publication record
exact member/member order
exact representative checkpoint ancestry
exact target head
confined regular P5 model path
exact P5 model SHA
exact P5 full-state digest
```

Because full PyTorch model loading is executable deserialization, P7 MUST use the shared descriptor-authenticated published-model owner from D3-4A. It may not implement an `lstat`/hash/reopen pathname sequence. When the exporter needs a pathname, stage bytes from the already-authenticated descriptor into attempt-owned private scratch, fsync + SHA-verify the staged copy, then export from that trusted copy.

The existing `MaceDeploymentArtifact` already reports `source_artifact_sha256` and `source_state_sha256`; require both to agree with the P5 model-publication member after export.

Deployment/component currentness is intentionally path-independent: `model_relative_path` and absolute workspace location are locators only and MUST NOT enter `deployment_identity`, deployment-dependent `component_input_digest`, terminal `model_artifact_set_digest`, or release currentness. Moving an intact campaign workspace with identical authenticated product bytes must not force numerical requalification. Any durable deployment receipt field that records a source path is diagnostic only.

Update P7 disk-headroom estimation by actual dependency: `deployment_parity` and `dynamics` budget authenticated P5 model staging plus deployment/ML-IAP scratch; checkpoint-only physical/relaxation/calibration/locked components retain their appropriate checkpoint/reference footprint rather than inheriting unrelated model-staging cost.

Do not duplicate P5 selection or checkpoint reconstruction logic inside P7.

### D3-17A — Version the deployment-source identity and eliminate truncated authoritative roots

`deployment_identity(member)` advances to a successor schema because its executable source changes from the representative checkpoint file to the P5 full model. The identity binds the exact per-member deployment source:

```text
scientific final publication/member/checkpoint identity
P5 source model SHA
P5 source full-state SHA
P5 source execution-architecture digest
target head
deployment dtype
resource scope
exporter identity
ML-IAP builder identity
```

The deployment-artifact root uses the **full deployment identity** (or another collision-proof encoding), not the current `[:16]` truncation. Historical v1 deployment roots/receipts remain immutable historical attempt evidence and are not rewritten.

Advance the deployment receipt schema as needed so it explicitly records the authenticated P5 source model SHA and source-state SHA in addition to deployment identity and deployed-artifact SHA. After export, `MaceDeploymentArtifact.source_artifact_sha256` must equal the P5 model SHA and `source_state_sha256` must equal the P5 model-state SHA before ML-IAP publication.

A representation successor for one committee member may reuse another member's deployed artifact when that other member's exact per-member deployment identity is unchanged. Aggregate `deployment_parity` / `dynamics` component input still binds the whole current `model_artifact_set_digest`, so aggregate evidence is rerun when any member representation changes.

### D3-17B — Commit-time P7 representation CAS without rebinding the attempt

Because model representation is deliberately outside `QualificationInputBinding`, an in-flight P7 attempt can overlap a representation-only P5 successor. Its old immutable component objects may remain historical evidence, but it must not publish an already-stale terminal/release pointer after the successor becomes current.

Extend the existing qualification pointer-publication owner with expected-current P5 fences:

- qualification **plan** and locked-activation publication continue to fence the scientific P5 decision + predecessor reclosure, not model bytes;
- terminal `ProductionQualificationRecord` and `ReleaseEvidenceIndex` publication additionally require the current P5 model-publication pointer to equal the exact model-publication record digest consumed by the session;
- the same transaction also requires the current final-publication decision pointer and predecessor-reclosure pointer to equal the session's exact scientific predecessors.

These comparisons occur inside the same `CampaignStore.exclusive_transaction()` that writes the P7 pointer. If any expected P5 pointer changed, the immutable P7 object remains historical but the current pointer write fails. This is a CAS fence, not a new lock or new attempt identity.

Representation change while locked activation is in progress never reopens disclosure. The activation remains bound to the unchanged scientific qualification identity; any later terminal/release reduction must pass the current model-publication CAS.

While a P7 attempt is active, its retention/reference state names both exact representative checkpoint paths and the exact P5 published-model paths it consumes. This does not make the model representation part of `QualificationInputBinding`; it makes storage dependency reporting truthful. Current models remain independently protected by the P5/models-root owners.

### D3-17C — One observational owner for P7 terminal currentness

Current `qualification status` and the general campaign lifecycle do not use the same P7 terminal-currentness logic. The compact lifecycle path can currently report a terminal record from pointer presence while the richer qualification observer applies additional checks. Remove that semantic duplication for the dependencies touched by this cycle.

Extend `observe_current_qualification(...)` (or factor one pure subordinate currentness helper used by it) so, using only the captured `campaign_owner_snapshot()` mapping plus immutable objects, it authenticates:

- captured final-decision pointer/object relation;
- captured predecessor-reclosure pointer/object and current P5/P6 predecessor source-tree digest;
- captured P5 model-publication pointer/object plus descriptor-authenticated model bytes;
- terminal/release `model_artifact_set_digest`;
- plan/terminal executable digest against current pure `resolve_executable_candidate_identity()`;
- current qualification specification digest when the caller supplies configuration, as `qualification status` already does.

This observer performs no qualification-session construction, no reference-request creation, no locked activation and no provider/model reconstruction. Reading/hash-identifying the current importable executable source surface is observational and is permitted; reading scientific source data or constructing models is not.

The general campaign lifecycle's single-size P7 step reuses this observation/helper instead of independently interpreting `ProductionQualificationRecord`. Because generic lifecycle intentionally remains config-independent, it may omit the specification comparison, but it MUST never report `release_qualified` when captured predecessor/model publication or current P7 executable identity makes the terminal record stale.

A public `release_qualified` claim additionally requires the captured `ReleaseEvidenceIndex` to authenticate against the exact current terminal record, binding, model-artifact-set digest, component set, locked activation (when required), resource scope/observation and verdict. A crash that published the terminal record but not its release index is recoverable/incomplete exposure, not a complete release claim. Historical terminal objects remain immutable.

`status`, `advance` and `qualification status` therefore agree on the product/executable currentness introduced by this cycle without making ordinary observation consequential.

### D3-17D — First locked reveal is fenced by the exact current prerequisite representation

The locked test itself remains checkpoint-based, but **activation** is authorized only after every mandatory nonlocked prerequisite has passed. Those prerequisites can include deployment-dependent components. Therefore the first irreversible reveal may not race a P5 representation successor.

Immediately before a brand-new `record_locked_reveal(...)`, after `execute_nonlocked_components(session)` has returned the prerequisite set:

1. require every prerequisite evidence object to have the exact current component-input digest for this session, including the current `model_artifact_set_digest` for deployment-dependent components;
2. acquire locks in the existing global order:

```text
post_selection_publication_barrier(generation)
    -> qualification_publication_barrier(generation)
        -> CampaignStore.writer_exclusion()
```

3. while the writer exclusion is held, transactionally compare the current selected binding plus exact final-decision, predecessor-reclosure and model-publication pointers against the session's inputs;
4. only after that CAS succeeds, append/create-or-verify the reveal record and publish the locked-activation pointer while the same writer exclusion and publication barriers still prevent a competing P5/P7/current-selection writer from invalidating the authorization window;
5. release those locks before running the locked numerical evaluation.

Do not hold the writer gate or publication barriers across the locked test computation.

If the cohort was already revealed, resume the existing activation under the accepted one-shot rules; never create a second reveal merely because model representation changed. A later representation successor may stale deployment-dependent prerequisites/terminal evidence, but it cannot undo or repeat the historical reveal. Resume reruns/reuses nonlocked components under the then-current model artifact set before reducing a new terminal verdict.

Lock ordering matches the existing storage mutation order (P5 barrier before P7 barrier before CampaignStore writer gate); no reverse acquisition is introduced.

### D3-18 — Executable-evolution consequence is explicit

Because the accepted P7 executable identity covers the importable mdstats source surface, this implementation itself will stale any pre-existing P7 terminal verdict produced by an older executable candidate. That is existing accepted P7 behavior, not a defect to paper over.

Consequences:

- older release/terminal/component objects remain historical and readable;
- an already-opened locked cohort remains irreversibly revealed through the global reveal index;
- this workplan does not authorize transferring an old locked PASS across executable identities;
- if a previously release-qualified single-size campaign must be qualified under the new executable, existing P7 authority governs what new independent locked evidence is required;
- the current stakeholder MPA-0 multi-size campaign is unaffected at P7 because multi-size qualification is intentionally unavailable and no release winner/locked activation exists.

Tests must prove the feature does not accidentally make historical P7 evidence current or reopen a revealed cohort.

### D3-19 — P5 publication storage admission and durability

The new full-model publication is a durable-output write path and must honor the campaign's existing disk-safety policy. Do not create a second global storage scheduler.

Before serializing a missing/successor publication set, reuse the current execution/storage reserve owner and `[execution].minimum_free_disk_gib` semantics to require enough incremental space for:

```text
verified temporary full-model serialization for every member
+ one new immutable full-model artifact per member
  where atomic rename cannot avoid coexistence with an old current artifact
+ immutable JSON evidence/projection overhead
+ configured retained free-space reserve
```

A conservative D4 estimator may use authenticated checkpoint size and/or exact in-memory state tensor bytes, but underestimation must not be accepted as success. Recheck the configured retained free-space reserve after actual serialized member sizes are known and before final placement/commit; on shortfall remove only private temp state and abort with no pointer change.

Record each final `model_size_bytes` in the product record; P7 disk admission uses those authenticated published-model sizes rather than the old checkpoint-only estimate.

Durability distinguishes immutable evidence from mutable projection:

```text
immutable .model:
    private temp on destination filesystem
    -> flush + fsync
    -> validate/reload
    -> create-once/no-clobber final directory entry
    -> fsync parent directory

publication.json:
    private temp
    -> flush + fsync
    -> atomic replace
    -> fsync parent directory
```

An existing immutable destination is descriptor-authenticated and reused only on exact expected bytes; it is never overwritten.

Use the shared persistence `fsync_parent_directory` owner. A simulated write/ENOSPC/fsync failure before authoritative pointer commit must leave the previous current publication intact and the command failed/recoverable; it must never mark a partial model set current.

## 13. Storage ownership

`CampaignPaths.models` is already current durable scientific evidence under `campaign_store:models`.

Reuse that owner.

Current storage already reports the entire `paths.models` root as current, restart-required, `DURABLE_SCIENTIFIC_EVIDENCE`, with open-container semantics. Do not add per-file storage machinery merely to restate that protection.

Update storage integration only if implementation changes what the existing owner can truthfully certify. Preserve:

- current published products remain protected by the existing models-root owner;
- unexpected descendants remain conservatively retained under the existing container semantics;
- model-publication P5 records remain under the existing post-selection evidence owner;
- no new cleanup/archive authority is introduced.

Do not introduce another model root.

Publication coordination locks live under the internal post-selection owner, not the public models tree. Attempt-private serialization temps remain publication-owner scratch and are removed only when ownership is certain. This cycle does not grant generic storage per-file reclaim/archive authority over model products or orphan full-SHA products.

If future storage work wants product-level archive/dedup/reclaim, it must derive authority from the P5 model-publication owner and synchronize with its publication seam; that is outside this cycle.

### D3-12A — Reconcile storage owner views with the new P5 product boundary

The existing `campaign_store:models` view currently blanket-labels `paths.models` as durable production-model evidence, while P5 will now be the semantic producer/owner of exact current model files. Preserve safety but remove owner ambiguity:

- keep the models-root view only as a protected campaign layout/container boundary; it grants no product identity/currentness and no recursive deletion authority;
- make the P5 storage owner expose one exact durable/current/immutable/hot-path artifact view per current published `.model` member, authenticated from `FinalProductionModelPublication`;
- make the P5 publication owner view depend on both the representative checkpoint artifacts and the exact published-model artifacts, and include the model-publication/artifact-set identity in its `state_identity` so same-decision representation advancement invalidates stale storage plans;
- before model-publication reclosure of a legacy decision, unresolved product representation causes retention/fail-closed storage classification, never inference that old model files are disposable;
- active P7 attempt references include the exact P5 model paths as well as checkpoints;
- unrelated legacy files already under `models/` remain ambiguous/protected unless another real owner certifies them; this cycle adds no cleanup authority.

The new internal P5 model-publication lock namespace is owner-known coordination infrastructure and is never a storage action candidate. Storage integration tests must prove report/cleanup/archive/dedup cannot mutate a live publication lock, private in-flight serialization, current model product, or inert full-SHA orphan.

Because canonical product files are immutable/versioned and `CampaignPaths.models` is already durable scientific evidence, superseded model bytes may accumulate. This cycle does **not** add a cleanup/retention authority merely to reclaim them. Preserve them under the existing models-root owner; if long-horizon accumulation becomes material, route that as a separate storage-policy change rather than deleting historical products by pathname heuristics.

## 14. Trainer terminal artifacts

Do not patch upstream MACE merely to suppress its normal terminal `.model`.

Document and expose the distinction:

```text
.mdstats/post-selection/.../runs/<id>/models
    trainer terminal/byproduct

<workspace>/models/production/...
    P5 selected production product
```

The operator-facing completion output must point at the latter.

## 15. Lightweight MH-1 integration scope

The objective is to detect clear integration defects before the next real MH-1 campaign, not to perform production qualification.

Current supported instance:

```text
family = mace_mh_1
source head = omat_pbe
source backend = e3nn
TRAIN2 backend = cueq
only_cueq = false
MACE = 0.3.16
```

Real long MH-1 qualification is explicitly deferred to the user's actual campaign.

### D3-9 — Static current-path audit

Trace exact family/head identity through:

```text
config
 -> foundation inspection/resolution
 -> source provider
 -> P5 method/materialization
 -> executable MACE config
 -> TRAIN2 checkpoint/provider reconstruction
 -> EVAL2
 -> P5 publication/model materialization
```

Reject obvious drift such as:

- hardcoded `default` foundation head;
- singleton-head assumptions;
- MPA-0-specific architecture assumptions in shared owners;
- silent fallback from `omat_pbe`;
- family-specific state handling that bypasses shared authority;
- publication serialization that only works for MPA-0-shaped models.

### D3-10 — Current lightweight regression

Run current applicable MH-1/foundation suites covering at least:

- foundation family/head resolution;
- explicit multi-head fail-closed behavior;
- head-aware inference/provider behavior;
- selected-head extraction;
- MH-1 campaign initialization;
- P5 foundation/head propagation guards;
- generic TRAIN2/EVAL2 reconstruction/CuEq regression relevant to shared owners.

Historical real-MH1 passes are regression oracles only, not current proof.

### D3-11 — Real-model smoke when readily available

If the locked real `mace-mh-1.model` and pinned environment are readily available without substantial qualification setup, run bounded:

- checkpoint inspection/SHA;
- exact `mace_mh_1 / omat_pbe` resolution;
- tiny source inference;
- selected-head extraction/parity;
- P5 foundation-provider/model-construction smoke;
- prove the post-selection output head inventory/order is exactly the current canonical `[pt_head, target_head]`, so the existing ML-IAP target-head index-1 contract is valid for MH-1 just as for MPA-0;
- exercise the new full-model publication save/reload owner on that bounded MH-1 path;
- when pinned CPU deployment/export dependencies are readily available, exercise publication -> target-head deployment exporter -> ML-IAP builder construction without a long LAMMPS/MD run.

If the real bytes/runtime are unavailable in the development host, that is not a blocker by itself.

Do not manufacture a long campaign merely to close this work.

### D3-12 — CuEq evidence boundary

Do not require real long MH-1 CuEq qualification.

Establish by source/current tests that MH-1 uses the same accepted CuEq realization/restoration owners and that no explicit family restriction or obvious incompatible assumption exists.

Existing bounded generic/tiny CuEq regression must remain green.

Real MH-1 CUDA/CuEq runtime behavior is deferred to the actual campaign.

## 16. Explicitly deferred MH-1 evidence

Not required for this workplan:

- real MH-1 CV;
- real MH-1 production training;
- long TRAIN2;
- production VRAM/concurrency qualification;
- MH-1 CuEq endurance;
- production RMSE/model quality;
- full P7 physical qualification;
- LAMMPS/ML-IAP production qualification;
- external physical/locked evidence.

Lack of those results is not a workplan blocker.

Any obvious incompatibility found by lightweight tests is a blocker.

## 17. Historical applicability set

PEM basis for this cycle:

```text
repository state reviewed: 237448b449b6f8042de5f239e5fefdfd54e3b2c3
accepted PEM file: PROJECT-ENGINEERING-MEMORY.md
PEM accepted/reconciled base recorded by that file: 4eabe2ae9783c7ff92f3a1093c37502a01380812
coverage: PARTIAL
same-branch semantic PEM overlay: NONE
```

PEM remains non-authoritative learning support. Because its coverage is partial, absence is not evidence that no historical analogue exists.

| PEM entry | Disposition | Cycle consequence |
|---|---|---|
| SP-001 duplicate-owner reduction | APPLICABLE | reuse checkpoint/provider, trust, persistence and CampaignStore owners; no wrapper registry/second transaction system |
| SP-002 authenticated identity boundaries | APPLICABLE | model bytes/state/path/member set and pointer currentness fail closed before executable consumption |
| SP-003 immutable durable restart/reuse | APPLICABLE | completed decision/checkpoint/model work reclose without TRAIN2/EVAL2; model products are create-once |
| SP-004 real-owner integration | APPLICABLE | selected-checkpoint != terminal real-MACE publication test and bounded MH-1 real-owner smoke |
| FF-001 realized-model identity drift | APPLICABLE | exact existing provider/architecture owner; no duplicate MACE reconstruction |
| FF-002 premature continuation authority | APPLICABLE | temp/unreceipted pickle is never durable authority; restart distinguishes temp/orphan/current |
| FF-003 duplicated destructive storage authority | APPLICABLE TO TRUST/RETENTION BOUNDARY | publication cleans only owned private temp; generic storage does not infer orphan disposability; reuse no-follow trust primitives |
| FF-004 resource ownership drift | APPLICABLE, BOUNDED | retire provider/accelerator at real owner boundary; no scheduler change |
| FF-005 downstream reconstruction leakage | APPLICABLE | status/qualification consume immutable product evidence and never reconstruct MACE/source state |
| NT-001 CuEq recurrence notice | RETIRED / NON-AUTHORITATIVE | no active challenge; closed lesson remains represented by FF-001/current owners |

Historical MH-1 qualification remains an oracle for expected family/head shape, not current proof after later P5/TRAIN2/EVAL2 changes.

Refresh this HAS if accepted PEM or branch authority materially advances before implementation closeout.

## 18. Expected implementation surface

Inspect ownership before editing; this is an affected-surface guide, not a requirement to touch every file.

Likely primary owners:

```text
mdstats/training_data/post_selection_publication.py
mdstats/training_data/post_selection_store.py
mdstats/training_data/post_selection_reclosure.py
mdstats/training_data/campaign_post_selection_runtime.py
mdstats/training_data/target_size_execution/evaluation.py
mdstats/training_data/model_features.py / mace_deployment.py as shared identity owners require
mdstats/training_data/persistence.py and/or the existing descriptor-trust helper owner
mdstats/training_data/qualification/publication.py
mdstats/training_data/qualification/providers.py
mdstats/training_data/qualification/runtime.py
mdstats/training_data/qualification/record.py
mdstats/training_data/qualification/store.py
mdstats/training_data/qualification/observation.py
mdstats/training_data/storage/owners.py
mdstats/training_data/campaign_lifecycle.py
mdstats/training_data/_campaign_cli_core.py
mdstats/training_data/__init__.py / qualification/__init__.py only where public exports require update
```

Potential shared model serialization/reconstruction owner may live in current MACE realization/model-feature modules. Prefer sharing existing owner over adding another subsystem.

## 19. Documentation surface

Reconcile current authoritative/current-user documentation, at minimum:

```text
docs/specs/training_data/mlff_post_selection_p5_spec.md
docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
docs/specs/training_data/mlff_p7_post_production_qualification_spec.md
docs/guides/mlff_campaign_cli_user_guide.md
docs/arch_manuals/mlff_training_data_architecture.md
docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md
README.md
current storage spec only if its models-root/publication description is affected
```

Document the three representations distinctly:

```text
representative TRAIN2 checkpoint
    scientific/restart lineage

P5 published full .model
    selected usable production product

P7 deployment artifact
    downstream converted/qualified representation
```

Current prose that says `train-production` finishes merely by publishing `FinalProductionPublicationDecision` must be reconciled: the decision remains the scientific membership owner, while successful final-production completion additionally publishes the subordinate usable full-model representation. Historical release notes/snapshots remain historical and are not rewritten.

## 20. Implementation stages

### Stage A — product schema, invariants, resolver and trust owner

Acceptance:

- immutable `FinalProductionModelPublication` binds exact decision/member/order/checkpoint lineage and rejects duplicates/malformed paths;
- `model_artifact_set_digest` is path-independent and includes exact member byte/state identities;
- `model_size_bytes` is recorded;
- one descriptor/no-follow published-model authenticator is shared by P5/status/P7;
- canonical model paths use collision-proof full identities;
- no selection/ranking logic is introduced.

### Stage B — selected checkpoint -> full model materialization

Acceptance:

- nonterminal selected checkpoint materializes through the existing native provider;
- exact returned `evaluated_model_state_digest` is bound to the model member;
- portable CPU e3nn full model is saved at accepted dtype and eval mode;
- reload preserves exact state/architecture/head inventory/mode;
- native path uses `allow_forward_override=False`;
- immutable file placement is create-once/no-clobber and durable;
- no terminal-model copy path.

### Stage C — atomic P5 publication-set integration

Acceptance:

- one stable decision/publication-set lock covers the complete ordered committee;
- immutable objects are persisted before pointer visibility;
- one CampaignStore transaction atomically changes model-publication + predecessor-reclosure + final-publication pointers;
- commit-time stale binding/currentness fence remains inside that transaction;
- fault injection at each logical pointer write proves all-old/all-new visibility;
- `publication.json` is refreshed only after authoritative commit and is never currentness authority.

### Stage D — `train-production` recovery classification/reclosure

Acceptance:

- COMPLETE requires decision + completion + authenticated model publication + current predecessor reclosure;
- RECLOSURE handles missing/stale model or reclosure with zero TRAIN2/EVAL2;
- valid model bytes are reused when only predecessor reclosure is stale;
- exact current predecessor-reclosure object/digest is preserved when only model representation is repaired;
- narrow decision/model candidate readers bypass only stale predecessor executable-tree currentness;
- mixed-size collection sends only PRODUCTION_REQUIRED jobs to the accepted global TRAIN wave;
- post-TRAIN revalidation prevents stale early classification from committing;
- every provider/accelerator is retired on success/failure.

### Stage E — observational lifecycle/status

Acceptance:

- coherent snapshot includes final model publication and predecessor reclosure pointers;
- status consumes only captured pointers/immutable records, never later live pointer reads;
- COMPLETE requires descriptor-authenticated SHA/size of every member but no `torch.load`;
- missing/wrong-kind/wrong-size/SHA/unsupported-format model is not COMPLETE;
- status is filesystem-write/source-read/provider neutral;
- multi-size reports every N independently.

- successful `train-production` itself prints the canonical `.model` path/SHA/target head for every committed member; operator discovery does not depend on inspecting internal hashes or running another command.

### Stage F — P7 intake/currentness reconciliation

Acceptance:

- scientific `QualificationInputBinding` remains checkpoint-based;
- current P5 model-publication and predecessor pointers come from the same captured observation snapshot;
- deployment parity/dynamics component identity includes current model-artifact-set; checkpoint-only components do not;
- terminal/release successor schemas bind model-artifact-set digest;
- historical older-executable P7 evidence remains historical and locked reveal remains consumed;
- deployment source is a trusted scratch copy made from descriptor-authenticated P5 model bytes;
- successor `deployment_identity` binds exact P5 source model/state/architecture identities and uses a collision-proof full deployment-root identity;
- deployment receipt records source model/state identities; exporter source artifact/state digests agree with the P5 member;
- terminal/release pointer publication CAS-checks exact current final-decision, predecessor-reclosure and model-publication pointers;

- first irreversible locked reveal is CAS-fenced under P5 barrier -> P7 barrier -> CampaignStore writer exclusion against the exact current prerequisite model publication;
- active P7 attempt references include exact P5 model paths without adding representation to the scientific attempt identity;
- `release_qualified` observation requires the matching authenticated release-evidence index, not a terminal-record pointer alone;
- `qualification status` and general lifecycle share the same pure P7 terminal-currentness observer for executable/predecessor/model-artifact staleness;
- P7 disk admission uses authenticated `model_size_bytes` only on deployment-dependent paths;
- workspace relocation with identical bytes does not invalidate numerical evidence.

### Stage G — bounded real-owner publication/usability + MH-1 integration

Acceptance:

- real current selected checkpoint != trainer terminal checkpoint case publishes the selected model;
- published file loads through the supported MACE target-head consumption path and performs bounded finite inference on non-locked known data; reuse an existing parity oracle/tolerance if one already owns that comparison, otherwise do not invent a D2 tolerance;
- MPA-0 regression remains green;
- MH-1 `mace_mh_1 / omat_pbe` resolution, reconstruction and `[pt_head, target_head]` order are proved;
- bounded MH-1 publication save/reload runs when real bytes are readily available;
- bounded CPU deployment/ML-IAP construction runs when pinned dependencies are readily available;
- no long MH-1 TRAIN/CV/production/MD/GPU qualification is required.

### Stage H — storage/docs/assembled closure

Acceptance:

- current model products remain protected by existing models-root owner;

- storage ownership distinguishes protected models-root layout from exact P5-owned current model artifacts; P5 publication state identity advances with the model-artifact set;
- publication private temp/lock paths have explicit owners and no generic cleanup authority is added;
- current docs describe decision/checkpoint/full-model/deployment boundaries consistently;
- public collection stage COMPLETE is written only after every frozen selected size satisfies the strengthened product-complete contract;
- failure at a later selected size may leave earlier products durable/current for restart, but the collection stage is not COMPLETE;
- existing frozen-size serial EVAL2/finalization fail-fast order and multi-size non-release terminal boundary remain unchanged;
- full affected regression/build checks pass.

## 21. Required acceptance cases

| Case | Required result |
|---|---|
| selected checkpoint == final epoch | published model matches selected checkpoint |
| selected checkpoint != final epoch | published model matches selected earlier checkpoint, never trainer terminal model |
| EMA-selected representative | exact provider-returned evaluated state/digest serialized |
| transient CuEq TRAIN2 | portable accepted e3nn model serialized |
| single-best committee | exactly selected member product |
| all-qualified committee | exact ordered decision member set, one publication-set transaction |
| committee concurrent builders | one decision-set lock; no mixed/interleaved artifact set |
| multi-size | independent products for every N; no cross-size winner |
| later-size publication failure | earlier durable size products reusable; collection stage not COMPLETE |
| legacy decision with no model | publication-only reclosure, zero TRAIN2/EVAL2 |
| stale predecessor + valid existing model | reuse exact model bytes; rebuild reclosure only; zero reserialization |
| repeat reclosure | no retraining/re-EVAL/rewrite when valid |
| stale pre-TRAIN classification | late revalidation aborts/reclassifies before commit |
| pointer-set fault at write 1/2/3 | all old pointers or all new pointers, never hybrid |
| projection failure after DB commit | product remains authoritative/current; projection later repairable |
| private temp crash residue | removed/rebuilt without treating it as authority |
| immutable unreferenced full-SHA model | inert, not auto-deleted/deserialized; reusable only after independent expected-SHA reconstruction |
| wrong/corrupt current model bytes | consumers fail closed; train-production may publish immutable successor |
| wrong decision/member/order binding | fail closed |
| missing selected checkpoint | fail closed |
| immutable destination collision | exact bytes -> reuse; mismatch -> fail; never overwrite |
| digest-prefix collision attempt | impossible by canonical full/collision-proof identity |
| intermediate/final symlink substitution | descriptor/no-follow authentication rejects |

| pre-planted intermediate symlink on publication write | anchored descriptor-relative creation refuses redirect; no external write |
| hash-then-reopen race attempt | same-descriptor source auth / trusted scratch staging prevents substitution |
| status | side-effect-free; SHA/size authenticates current model; reports direct `.model` paths |

| train-production completion output | every committed size/member prints canonical model path, SHA and target head; never trainer terminal model |
| same-byte workspace relocation | product/deployment currentness unchanged |
| P7 reference/deployment split | checkpoint provider remains reference; deployment consumes authenticated P5 model bytes |
| P7 deployment identity collision | full/collision-proof deployment identity root; no `[:16]` authoritative namespace |
| unchanged member in changed committee representation | its per-member deployed artifact may be reused; aggregate deployment component evidence reruns |
| representation successor during P7 run | stale terminal/release pointer CAS fails; old object stays historical; locked activation is not reopened |

| representation successor before first locked reveal | prerequisite/model CAS fails before reveal; cohort remains unopened |
| representation successor after locked reveal | reveal remains consumed; deployment prerequisites/terminal are refreshed under current artifact set, no second reveal |
| crash after terminal record before release index | no public `release_qualified`; rerun publishes/repairs release index without reopening locked evidence |
| representation-only repair with current predecessor reclosure | exact predecessor-reclosure digest preserved; qualification attempt identity unchanged |
| general lifecycle after stale model/executable P7 evidence | does not report current `release_qualified`; agrees with shared observation owner |
| same checkpoint/state, different serialized bytes under same P7 binding | deployment_parity/dynamics stale; checkpoint-only evidence reusable; terminal binds successor model-artifact-set |
| pre-change P7 evidence under older executable | historical only; no compatibility laundering; locked reveal remains consumed |
| already-revealed locked cohort | never reactivated for representation-only successor |
| interrupted locked activation | resumes same activation under existing rules; no fresh reveal |
| P7 terminal/release v1 | readable historical evidence; never promoted across executable cutover |
| P5 publication ENOSPC/write/fsync failure before pointer commit | previous current pointer set intact; partial set not current |
| actual size exceeds preflight estimate | reserve recheck aborts before commit without deleting authority |
| P7 disk admission | authenticated P5 model sizes + deployment/ML-IAP scratch |
| published model object mode | CPU portable e3nn, accepted dtype, eval/inference mode after reload |
| bounded published-model usability | supported MACE target-head consumer loads model and finite bounded inference succeeds |
| MH-1 explicit source head | `mace_mh_1 / omat_pbe` preserved end-to-end |
| MH-1 output head order | exactly `[pt_head, target_head]`; target-head index-1 deployment contract valid |
| MH-1 bounded publication | save/reload new P5 full-model representation when real bytes readily available |
| bounded inference override | cannot source a production published `.model` |
| mixed PRODUCT_RECLOSURE + PRODUCTION_REQUIRED | accepted global TRAIN wave remains isolated; serial reclosure/finalization follows it |

| storage owner graph after publication | models root remains protected container; exact P5 model artifacts and artifact-set state are owner-certified; no new reclamation authority |

## 22. Real-owner integration

At least one bounded real-owner publication test must make:

```text
selected checkpoint != terminal checkpoint
```

and prove that the published full model follows the selected representative.

Use real current checkpoint/provider/model serialization owners. A toy `torch.nn.Linear`-only test is insufficient for this claim.

After publication, open the resulting file through the supported MACE target-head consumption path and execute one bounded finite inference on non-locked known geometry. If an accepted existing reference-vs-published parity oracle/tolerance already exists, reuse it; otherwise this stage proves structural/operational usability only and does not invent a numerical threshold.

For MH-1, lightweight source/provider/head/publication checks are sufficient for this cycle. A full real TRAIN2/CV/production/MD campaign is deliberately not required.

## 23. Affected regression

Run the current affected suites spanning:

```text
P5 production/restart
publication decision/currentness
checkpoint authentication/provider reconstruction
multi-size integration
campaign lifecycle/status coherence
P7 publication/provider/deployment intake
P7 deployment-identity successor/full-root/receipt migration and per-member reuse
P7 terminal/release commit-time P5 decision/reclosure/model CAS races

P7 first-locked-reveal prerequisite/model CAS and lock-order/crash-resume tests
P7 release-qualified terminal/index atomic-exposure recovery tests
P7 qualification-status + general-lifecycle shared currentness observation
P7 selective component invalidation and locked one-shot preservation
P7 terminal/release v1->v2 historical readability/currentness without cross-executable evidence promotion
storage owner/protection
MH-1 foundation/head/selected-head tests
generic MACE execution/CuEq parity tests
publication-set-lock / atomic three-pointer transaction / crash-injection tests
descriptor no-follow path-substitution / trusted-staging tests
private-temp vs immutable-orphan recovery tests
P5 publication disk-reserve/actual-size-recheck/ENOSPC/fsync-failure tests
status SHA-corruption/coherent-reclosure-pointer/workspace-relocation tests

train-production direct published-model locator/output tests
write-side intermediate-symlink/no-clobber confinement tests
P5/P7/storage owner-graph exact model-path and publication-lock protection tests
collection stage COMPLETE/fail-fast multi-size restart tests
bounded real-MACE published-model usability tests
documentation structural/build checks
```

Run broader repository-required checks where affected-surface confidence is insufficient.

Production-scale GPU qualification remains deferred.

## 24. Blocking conditions

NO-PASS if any remains true:

1. `train-production` can report final production COMPLETE without a usable authenticated full model for every P5-published member.
2. A product can be sourced from the trainer terminal epoch instead of the selected representative.
3. The operator must query SQLite/hash directories to locate the current product.
4. Product reconstruction duplicates the accepted checkpoint/provider reconstruction machinery.
5. Existing valid completed campaigns require retraining only to obtain product serialization.
6. Multi-size publication chooses or implies a cross-size winner.
7. Status creates state or reconstructs MACE.
8. P7 can consume a model not bound to the current P5 decision/member/checkpoint.
9. Current product artifacts are treated as disposable cache.
10. Lightweight current MH-1 audit exposes an obvious family/head/shape incompatibility and it remains unresolved.
11. Missing long MH-1 production qualification is incorrectly treated as implementation failure.
12. A valid successor publication for the same N/seed must overwrite an existing canonical seed-only model path.
13. P7 deployment-dependent identity ignores the current P5 model-artifact-set/model SHA, or representation bytes are incorrectly injected into the whole QualificationInputBinding/attempt identity.
14. A published full-model pickle can reach `torch.load` before its expected SHA/path kind is authenticated.
15. Existing completed publications cannot be reclosed solely because the previous predecessor source-tree digest became stale after this implementation.
16. The new model-publication pointer is read outside the shared coherent status snapshot.
17. Crash residue at an uncommitted product path permanently wedges reclosure.
18. A representation-only P5 model successor causes a fresh locked activation or makes already-revealed locked evidence appear fresh.
19. Historical P7 v1 terminal/release evidence is either silently treated as current under the new product boundary or made unreadable/deleted rather than preserved as historical.
20. A canonical model path depends circularly on the subordinate model-publication record digest that contains that path.
21. Product materialization can serialize the bounded forward-override/parameter-shell fixture path instead of a native reconstructed MACE model.
22. `train-production` reports final production COMPLETE while predecessor reclosure is stale/missing.
23. Mixed reclosure/new-production flow leaves model-publication accelerator residency alive into the global TRAIN scheduler wave.
24. Concurrent builders can bypass one another because the publication lock is derived only after non-deterministic serialization/model SHA exists.
25. Unreceipted/private full-model pickle residue is deserialized as authority.
26. An older publisher can overwrite `publication.json` after a newer model publication becomes authoritative.
27. Historical P7 evidence from an older executable is promoted to current by weakening executable currentness or compatibility-shimming a locked result.
28. Product serialization preserves tensor state but leaves the module in training mode.
29. MH-1 lightweight coverage fails to prove canonical `[pt_head, target_head]` needed by the ML-IAP target-head index contract.
30. Multi-member publication can be assembled from independently locked member builds rather than one decision-set transaction.
31. A stale PRODUCT_RECLOSURE/PRODUCT_COMPLETE classification can commit after currentness changes during another size's TRAIN wave.
32. Status can report COMPLETE for a same-size SHA-corrupted current model.
33. P5 publication bypasses configured disk reserve, actual-size reserve recheck, or file/parent fsync durability.
34. Deployment/P7 currentness depends on workspace/model path rather than exact model bytes/state identity.
35. Model-publication, predecessor-reclosure and final-publication pointers can commit in separate SQLite transactions and expose a hybrid/stranded product.
36. PRODUCT_COMPLETE can be reached with missing/stale predecessor reclosure.
37. Public status/qualification reads model-publication or predecessor pointers outside `campaign_owner_snapshot()`.
38. Model byte authentication uses `lstat`/hash followed by independent reopen, or follows an intermediate symlink, before executable deserialization.
39. Immutable model publication uses overwrite-capable placement such as `os.replace`, or canonical authority depends on a truncated digest without collision resolution.
40. The subordinate model-publication record can omit/reorder/add members or disagree with exact decision seed/run/checkpoint evidence.
41. Code-change reclosure unnecessarily reserializes a valid model because migration has no narrow authenticated model-publication candidate reader.
42. Collection-level `post_selection_final_production` is COMPLETE before every frozen size has authenticated model publication + current predecessor reclosure.
43. Projection failure after authoritative commit is treated as scientific product loss or causes selection/training rerun instead of projection-only repair.
44. P7 terminal/release observation compares against a later live P5 pointer rather than the captured coherent owner snapshot.
45. Current docs still describe the decision/checkpoint as the only complete P5 product boundary and leave usable-model publication undiscoverable.
46. Bounded real-owner evidence proves only `torch.load`/state equality but never exercises the published file through a supported MACE target-head consumer.
47. A representation-only model repair rebuilds an otherwise-current predecessor reclosure and thereby changes P7 attempt identity unnecessarily.
48. Touched P7 deployment roots continue to use a truncated deployment-identity prefix, or deployment identity omits exact P5 source model/state/architecture identity.
49. A terminal/release P7 pointer can be published after its consumed P5 decision, predecessor reclosure, or model-publication pointer has changed.
50. `qualification status`, general campaign lifecycle, and consequential P7 current resolvers can disagree about terminal currentness for the exact predecessor/model representation or executable identity touched by this cycle.
51. A representation successor forces unrelated checkpoint-only P7 components to reserve full-model deployment scratch or otherwise changes their resource semantics.
52. A first locked reveal can occur after deployment-dependent prerequisites became stale because the current P5 model publication is not CAS-fenced across the irreversible reveal.
53. A public `release_qualified` state can be reported from a terminal record whose matching release-evidence index is absent, stale or belongs to another model-artifact set.
54. Publication write-side directory creation/final placement can follow an intermediate symlink even though later reads use no-follow authentication.
55. `train-production` can succeed without directly printing the authoritative published `.model` path/target head/SHA, leaving the user dependent on internal-tree inspection.
56. Storage continues to treat the whole models root as the only semantic product owner while P5 publishes exact model artifacts, or a storage action can target current/in-flight/orphan publication artifacts without P5 authority.

## 25. D3 reopen triggers

Reopen rather than patch D4 if evidence shows:

- existing authenticated provider cannot expose the exact selected portable state;
- full-model serialization necessarily changes target-head/precision/scientific semantics;
- a subordinate product record cannot be bound acyclically to current P5 publication;
- `CampaignPaths.models` cannot safely remain the durable product owner;
- P7 fundamentally requires a product representation incompatible with P5's accepted portable model;
- current MH-1 support requires a different scientific/numerical fine-tuning method rather than an implementation correction;
- the existing CampaignStore cannot provide one atomic P5 product-pointer transaction without changing accepted campaign-currentness architecture;
- supported platform/path semantics cannot provide the already-required no-follow descriptor trust boundary for executable model bytes.

Otherwise local serialization helpers, exact basenames, temporary-file mechanics, and bounded smoke-fixture choices remain D4.

## 26. Completion criteria

Implementation is complete only when the assembled candidate proves all of the following simultaneously:

1. Every frozen selected size has exact P5 decision membership plus a reloadable, descriptor-authenticated, collision-proof/no-clobber full MACE `.model` representation for every published member.
2. Representation comes from the exact selected checkpoint/provider state, never trainer terminal output, with live/EMA/state/architecture/head/dtype equivalence and bounded supported-consumer usability.
3. One publication-set lock plus one atomic CampaignStore product-pointer transaction makes decision/model/reclosure visibility crash-consistent and restart-safe.
4. Legacy completed campaigns reclose with zero TRAIN2/EVAL2 and independently reuse a still-valid model publication or still-current predecessor reclosure when only the other descendant is stale.
5. Public lifecycle/status reports COMPLETE only after decision + completion + authenticated model publication + current predecessor reclosure for every selected size, from one coherent owner snapshot.
6. P7 keeps checkpoint reconstruction as scientific reference, consumes descriptor-authenticated P5 model bytes only for deployment, versions the deployment-source identity, invalidates only deployment-dependent evidence for representation changes, and CAS-fences terminal/release publication against concurrent P5 successors.
7. `qualification status` and general lifecycle share one observational P7 currentness owner for current executable/predecessor/model-representation dependencies touched by this cycle.
8. One-shot locked disclosure is never reopened; representation-only repair preserves current predecessor reclosure/attempt identity when applicable; historical older-executable P7 evidence remains historical.

8a. A first locked reveal is authorized under a short P5/P7/writer critical section that proves its deployment-dependent prerequisites still correspond to the exact current model publication; terminal `release_qualified` exposure requires the matching release index.
9. P5/P7 disk admission, anchored no-follow creation/authentication, fsync/no-clobber durability, resource retirement and reconciled P5/models-root storage ownership remain within existing owners; the accepted global TRAIN scheduler is unchanged.
10. `train-production` directly prints authoritative usable model paths/SHA/target head, and current documentation consistently distinguishes checkpoint, P5 full model and P7 deployment artifact.
11. MPA-0 affected regression and bounded real-owner selected-checkpoint publication pass; MH-1 passes the lightweight source/head/reconstruction/publication checks, while long campaign/GPU/MD qualification remains deferred.

Any failed item above is an implementation NO-PASS. Local helper names, exact private temp names and equivalent no-clobber primitives remain D4 choices.

> **Review-history note:** Sections 27 onward are chronology of earlier workplan reviews. Where historical wording conflicts with Sections 0-26, the current Revision-8 normative contract above controls. Earlier findings remain useful only as superseded rationale/evidence.


## 27. Current-implementation review closure (Revision 2)

Review basis: `237448b449b6f8042de5f239e5fefdfd54e3b2c3`.

### R2-F1 — Decision schema must not absorb serialized artifact identity — CLOSED

Current `FinalProductionPublicationDecision` v3 already owns the pre-qualification scientific/member decision, and `resolve_current_final_production_publication()` replays that decision exactly. Embedding the later serialized `.model` into this object would conflate selection with representation and make legacy reclosure awkward. Revision 2 freezes the subordinate-record design instead.

### R2-F2 — Fresh publication pointer ordering was under-specified — CLOSED / SUPERSEDED BY R7 ATOMIC POINTER-SET COMMIT

Current `publish_final_production_publication()` stores the decision/reclosure and publishes the final pointer before any full selected model exists. Revision 2 now requires the final-publication pointer to be the last current-pointer commit for fresh publication, after model materialization and subordinate product pointer publication.

### R2-F3 — Existing-campaign reclosure needed an explicit pre-EVAL fast path — CLOSED

Current `execute_current_train_production()` ordinarily plans the whole collection and later calls serial `_finalize_final_production()`. Merely saying “zero unnecessary EVAL2” did not identify the owning control-flow change. Revision 2 adds the explicit three-state recovery classification before new TRAIN/EVAL admission.

### R2-F4 — P7 full-model consumption could destroy the deployment-parity oracle — CLOSED

Current P7 `member_provider` authenticates/reconstructs the selected checkpoint, while deployment currently sources `checkpoint_path_for_member()`. Revision 1 said broadly that P7 should consume the full model; that was too coarse. Revision 2 keeps the checkpoint provider as the independent reference and changes only deployment-export source to the P5 full model.

### R2-F5 — Proposed new “portable model-state digest” would duplicate current owners — CLOSED / STRENGTHENED IN R3

Revision 2 correctly rejected inventing a new tensor identity, but its wording missed two existing owners. Current provider authentication already returns an `evaluated_model_state_digest`, and the deployment owner already computes an exact full-`state_dict` SHA over names/dtypes/shapes/bytes. Revision 3 requires reuse/refactoring of those existing identities rather than either omitting full-state identity or defining a third digest.

### R2-F6 — Product path trust/relocation rules were incomplete — CLOSED

Revision 2 now requires model-root-relative paths, confinement beneath `CampaignPaths.models`, regular non-symlink files, and no absolute/`..` traversal. Absolute workspace paths remain outside durable identity.

### R2-F7 — Status integrity cost needed a bounded rule — CLOSED / SUPERSEDED BY R6-R8 BYTE-AUTHENTICATED STATUS

Current `status` is explicitly observational and must stay cheap/pure. Revision 2 requires record/currentness/path-kind validation in normal status but reserves full large-model SHA authentication for consequential/reclosure/P7 consumers.

### R2-F8 — Storage work was over-broad — CLOSED

Current storage already protects the whole `paths.models` root as current durable scientific evidence. Revision 2 no longer requires a new per-model storage dependency graph unless implementation changes the existing owner's truthful coverage.

### R2-F9 — MH-1 evidence boundary — CLOSED

Current source still explicitly supports `mace_mh_1 / omat_pbe`; historical real-model coverage exists but predates later P5 changes. The stakeholder explicitly defers real qualification to the upcoming campaign. Revision 2 therefore requires only source audit, current affected regressions, and cheap real-model smoke when readily available. Missing long/GPU MH-1 evidence is not a blocker.

## 28. Workplan review verdict

**PASS AS WORKPLAN / D3->D4 HANDOFF READY.**

No Serious Challenge to D1/D2 is active. The plan now matches the current implementation's actual ownership boundaries:

```text
P5 decision remains checkpoint/member authority
P5 subordinate record owns usable full-model representation
train-production owns explicit completion/reclosure
campaign lifecycle owns read-only operator projection
P7 checkpoint provider remains the independent reference
P7 deployment consumes the P5 model product
CampaignPaths.models remains the durable model root
```

Implementation must preserve the recently accepted global production TRAIN scheduler: no publication change may reintroduce per-size TRAIN schedulers or disturb the collection-wide admission/currentness fences.


## 29. Second current-implementation review closure (Revision 3)

Review basis: `237448b449b6f8042de5f239e5fefdfd54e3b2c3`; reviewed active-plan head before repair: `a1b79f8aa64339026b24d7106f7f9c1b7646bb33`.

### R3-F1 — P7 representation currentness needed an explicit owner — SUPERSEDED BY R4-F1

Revision 3 correctly identified that deployed-artifact currentness must bind the new P5 model representation, but incorrectly placed that dependency in the whole `QualificationInputBinding` / attempt identity. Revision 4 narrows it to the deployment-dependent component and terminal/release boundaries so one-shot locked evidence is preserved.

### R3-F2 — Qualification observation needed coherent P5 model-publication currentness — CLOSED / NARROWED IN R4

`campaign_owner_snapshot()` still must capture the new P5 model-publication pointer in the same atomic snapshot. Revision 4 compares terminal/release `model_artifact_set_digest` against that current P5 record rather than staling the entire qualification plan/attempt.

### R3-F3 — Existing predecessor reclosure becomes stale when this implementation changes P5 source — CLOSED

`resolve_current_final_production_publication()` requires `resolve_current_predecessor_reclosure()`, whose executable source-tree digest will change under this implementation. Revision 2's “resolve current decision then reclose” wording was circular for the current campaign. Revision 3 defines a narrow train-production-only candidate resolver: replay the exact decision from current persisted completion/evidence, compare decision digest, then rebuild predecessor reclosure without rerunning EVAL2.

### R3-F4 — Seed-only canonical product path cannot represent valid successors — CLOSED

The same selected binding/generation/N/seed can receive a legitimate successor final decision. A canonical `seed-1.model` path would force either overwrite of historical bytes or permanent conflict. Revision 3 requires immutable/versioned model paths and keeps only `publication.json` as a replaceable operator projection.

### R3-F5 — Crash residue and current artifact were conflated — CLOSED

Revision 2's unconditional “existing mismatch -> fail closed” could wedge recovery after a crash between model placement and record publication. Revision 3 distinguishes authenticated current artifacts from uncommitted owner residue and foreign/ambiguous paths, with existing artifact-publication locking and confinement.

### R3-F6 — Executable model deserialization trust boundary was under-specified — CLOSED

A full PyTorch MACE model is executable pickle-style deserialization. Revision 3 requires SHA and regular/non-symlink confinement authentication before any `torch.load`/MACE inspection, with same-descriptor loading or authenticated staging so path substitution cannot occur between hashing and load.

### R3-F7 — Revision 2 overlooked existing exact state-digest owners — CLOSED

`authenticate_post_selection_provider()` returns the exact evaluated live/EMA state digest, and `mace_deployment` already hashes the complete state_dict. Revision 3 binds both existing identities and requires exact pre/post serialization state + architecture equality. No new tensor digest is introduced.

### R3-F8 — P7 resource admission still modeled checkpoint-only scratch — CLOSED

Current qualification headroom estimates are based on representative checkpoint size. Once deployment starts from the P5 full model, the resource owner must budget actual published-model/deployment/ML-IAP scratch size. Revision 3 makes that an explicit D4 acceptance obligation.

### R3-F9 — Product serialization device representation was implicit — CLOSED

Revision 3 freezes the P5 product as portable e3nn CPU representation at the accepted learned-model dtype. Transient CuEq/OEq/compiled training realizations are not valid P5 product artifacts. Device relocation must preserve exact state, buffers, heads and architecture.

## 30. Revision-3 workplan verdict

Revision 3 was an intermediate reviewed design. Its P7 whole-binding invalidation rule is superseded by Revision 4 because it conflicted with accepted one-shot locked-evidence semantics. All unaffected Revision-3 closures remain applicable.


## 31. Third current-implementation review closure (Revision 4)

Review basis: `237448b449b6f8042de5f239e5fefdfd54e3b2c3`; reviewed active-plan head before repair: `7d3e63f5ca3bc0e1b6350ceaf40d966fddec3d0a`.

### R4-F1 — Whole-attempt model-publication invalidation conflicted with one-shot locked evidence — CLOSED

Current locked qualification is intentionally checkpoint/provider based, and locked disclosure is globally irreversible through the append-only cohort reveal index. Revision 3 would have changed `QualificationInputBinding` and `attempt_identity` for serialization-only changes, making every component stale while the revealed locked cohort could not legally be opened again. Revision 4 preserves the scientific binding and makes model-artifact currentness component-scoped: deployment parity and dynamics depend on the serialized model; physical PES, relaxation, calibration and locked evidence remain checkpoint-based.

### R4-F2 — Terminal verdict needed representation currentness without forcing a new attempt — CLOSED

A stable attempt alone is insufficient because a release verdict must still describe the exact deployment representation. Revision 4 adds `model_artifact_set_digest` to successor terminal/release schemas. Exposure-time currentness compares that digest to the current P5 model-publication record and revalidates deployment-dependent component inputs.

### R4-F3 — P7 schema migration/preservation was missing — CLOSED / NARROWED IN R5

Revision 4 correctly required explicit successor schemas and historical readability, but overstated component reuse across the implementation cutover. Revision 5 preserves old v1 evidence as historical and allows selective checkpoint-only reuse only when the ordinary qualification binding — including executable identity — is unchanged.

### R4-F4 — Canonical product-path example admitted a self-reference cycle — CLOSED

Revision 3 allowed `<decision-or-product-identity>` even though the subordinate product record itself contains `model_relative_path`. Revision 4 forbids subordinate-record digest in its own canonical path and derives immutable locations only from already-known parent/member/model identities.

### R4-F5 — Product publication could accidentally serialize the test forward-override seam — CLOSED

Current `member_provider` permits a bounded forward override when a test inference evaluator is present. That seam is valid for bounded numerical testing but not for publishing a user model. Revision 4 requires native authenticated MACE reconstruction with `allow_forward_override=False` for product materialization.

### R4-F6 — Model-publication record digest was too coarse for downstream invalidation — CLOSED

Path or diagnostic-metadata changes do not alter deployment semantics, while model bytes do. Revision 4 defines a path-independent `model_artifact_set_digest` from the parent decision and exact ordered serialized member identities. P7 deployment descendants bind that digest rather than the whole subordinate record content digest.

### R4-F7 — Operator projection ordering was ambiguous — CLOSED

`publication.json` is now explicitly written only after authoritative pointer commit and remains reconstructable/non-authoritative. A stale-generation failure cannot publish a convenience file that claims to be current.

### R4-F8 — Mixed reclosure/new-production sequencing could perturb the global TRAIN scheduler — CLOSED

Revision 4 separates classification from execution. Recovery classification happens before admission, but product materialization/reclosure is serial post-TRAIN finalization with explicit provider/accelerator retirement. Only genuine `PRODUCTION_REQUIRED` trajectories enter the accepted global TRAIN wave.

### R4-F9 — Final-production COMPLETE omitted current predecessor reclosure — CLOSED

The strict P7 exposure boundary requires current predecessor reclosure. Revision 4 adds it to operator-visible final-production completion so a product cannot be reported fully published while immediately unusable downstream.

## 32. Revision-4 workplan verdict

Revision 4 was an intermediate reviewed design. Its dependency split remains accepted, but Revision 5 corrects concurrency, executable-migration, projection-race, object-mode and MH-1 head-layout details.


## 33. Fourth current-implementation review closure (Revision 5)

Review basis: `237448b449b6f8042de5f239e5fefdfd54e3b2c3`; reviewed active-plan head before repair: `a32bf7a489ccbf165bd14e4150b076861b8db381`.

### R5-F1 — Publication lock identity was too late/non-deterministic — CLOSED

The shared `artifact_publication_lock` documentation explicitly calls out full PyTorch model pickles as non-byte-deterministic and requires concurrent builders of the same logical artifact to serialize. Revision 4 locked the eventual artifact path, but that path may include a model SHA unavailable until after serialization. Two builders could therefore produce different SHAs and bypass one another. Revision 5 freezes a stable pre-serialization decision/member logical lock and re-authenticates after acquiring it.

### R5-F2 — Uncommitted pickle residue could cross an executable-deserialization trust boundary — CLOSED

A crash can leave model bytes without an authenticated product record. Such residue has no trusted expected SHA and must not be `torch.load`ed merely to test reuse. Revision 5 allows deletion/rebuild of owner-proven confined residue without deserialization and preserves fail-closed treatment for ambiguous paths.

### R5-F3 — Current product corruption had no safe recovery path — CLOSED

A missing or SHA-mismatched artifact named by an authentic immutable record now fails consumers closed but can be representation-reclosed by `train-production` from the authenticated selected checkpoint into a new immutable artifact/record. Historical paths/records are never overwritten.

### R5-F4 — Operator projection had a stale-writer race — CLOSED

Writing `publication.json` merely “after pointer commit” allowed an older concurrent publisher to overwrite a newer projection after releasing the publication barrier. Revision 5 keeps the short projection refresh inside the same generation publication barrier (or exact equivalent re-check under it), after authoritative pointer writes.

### R5-F5 — Revision 4 overstated P7 component reuse across this implementation cutover — CLOSED

P7 executable currentness includes the mdstats source-tree digest. Implementing this work changes that digest, so pre-change P7 component/terminal evidence is historical regardless of unchanged checkpoint state. Revision 5 preserves historical readability and irreversible reveal history but forbids compatibility laundering. Selective checkpoint-only evidence reuse applies only to representation changes under the same ordinary qualification binding.

### R5-F6 — Locked-evidence consequence of executable evolution is now explicit — CLOSED

Any pre-existing release verdict under an older executable becomes historical according to accepted P7 semantics, while a revealed cohort remains revealed. This work does not transfer an old locked PASS across executable identities. The stakeholder's current multi-size campaign is unaffected because P7 is intentionally unavailable there.

### R5-F7 — Tensor equality omitted module training/eval state — CLOSED

`state_dict` equality does not encode `Module.training`. Revision 5 requires the published portable model to be in inference/eval mode before save and after reload.

### R5-F8 — MH-1 lightweight pass did not explicitly cover the downstream target-head index contract — CLOSED

Current P5 execution authority requires canonical replay-first head layout `[pt_head, target_head]`, while the ML-IAP builder validates target head index 1. Revision 5 requires the bounded MH-1 construction smoke to prove that exact post-selection layout, closing the family-specific integration seam without a long run.

### R5-F9 — Immutable product accumulation is acknowledged rather than silently delegated — CLOSED

Versioned model products are durable scientific evidence under the existing whole-models-root owner. Revision 5 explicitly preserves superseded products and routes any future reclamation requirement to a separate storage-policy change rather than pathname cleanup.

### R5-F10 — Workplan representation defects — CLOSED

Revision 4 contained duplicated `## 6` and `## 13` headings from the prior composition pass. Revision 5 removes them and restores one unambiguous owner section each.

## 34. Revision-5 workplan verdict

Revision 5 was an intermediate reviewed design. Revision 6 keeps its identity/trust conclusions and strengthens committee transactionality, late currentness revalidation, status integrity, storage admission/durability, and locator independence.


## 35. Fifth current-implementation review closure (Revision 6)

Review basis: `237448b449b6f8042de5f239e5fefdfd54e3b2c3`; reviewed active-plan head before repair: `a5e8099498097e773192e2ae8cef837c1c91d808`.

### R6-F1 — Per-member publication locks did not make a committee one transaction — CLOSED

Revision 5 serialized same-member builders but an all-qualified committee could still be assembled by two processes from different non-deterministic member serializations before either product record was current. Revision 6 replaces per-member locks with one stable decision/publication-set lock covering the complete ordered member set through authoritative commit.

### R6-F2 — Recovery classification could become stale during the global TRAIN wave — CLOSED

The accepted scheduler may run genuine production work for other sizes after early PRODUCT_RECLOSURE classification. Revision 6 makes classification advisory and requires decision/completion/product re-resolution under the publication-set lock plus a second upstream currentness check under the generation publication barrier immediately before pointer commit.

### R6-F3 — Product status could falsely report COMPLETE after byte corruption — CLOSED

Revision 5 intentionally avoided large-file hashing in status, but COMPLETE now means a usable published model. Revision 6 requires bounded streaming SHA/size verification of the current published member files while still forbidding `torch.load` or model reconstruction in observational status.

### R6-F4 — P5 model publication lacked a storage-admission/durability contract — CLOSED

The new product is durable output and can be tens/hundreds of MiB per member. Revision 6 reuses the existing minimum-free-disk policy, adds conservative incremental-headroom admission, records `model_size_bytes`, and requires temp-file fsync + atomic placement + parent-directory fsync. No new storage scheduler is introduced.

### R6-F5 — Immutable orphan handling could delete historical evidence unnecessarily — CLOSED

Revision 6 deletes only private attempt temporary files. SHA-bearing final model files without a current record are left inert and are never deserialized automatically; a trusted fresh reconstruction may byte-reuse one only if it independently derives the same SHA. This removes the need to prove global historical-reference absence before cleanup.

### R6-F6 — Model publication needed exact evaluated-state provenance from the provider owner — CLOSED

The serializer now binds the exact `evaluated_model_state_digest` returned by the native authenticated checkpoint provider that supplies the serialized model object. Live/EMA state is never re-inferred in the publication layer.

### R6-F7 — Path-independent P7 identity needed an explicit compatibility assertion — CLOSED

Current deployed-artifact receipts do not need source filesystem path as identity. Revision 6 explicitly excludes product locators from deployment/component/terminal currentness and adds workspace-relocation acceptance with identical authenticated bytes.

### R6-F8 — P7 resource admission needs durable product size, not checkpoint proxy — CLOSED

Revision 6 adds `model_size_bytes` to each P5 published member and requires P7 storage admission to use those authenticated sizes when estimating staging/deployment scratch.

## 36. Revision-6 workplan verdict

**PASS AS WORKPLAN / D3->D4 HANDOFF READY AFTER FIFTH REVIEW.**

No Serious Challenge to D1/D2 is active.

The publication boundary is now transactionally complete:

```text
one P5 decision
    -> one stable publication-set lock
    -> one ordered authenticated full-model member set
    -> durable/fsynced immutable model bytes
    -> one FinalProductionModelPublication
    -> late lineage revalidation
    -> one authoritative pointer commit
    -> byte-authenticated observational status
```

The work remains intentionally narrow: selection science, the accepted global TRAIN scheduler, P7 one-shot locked semantics, and the deferred real MH-1 campaign qualification are unchanged.
