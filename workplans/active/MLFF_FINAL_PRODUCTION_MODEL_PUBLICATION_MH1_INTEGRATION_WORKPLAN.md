---
kind: implementation-workplan
workplan_id: MLFF-FINAL-PRODUCTION-MODEL-PUBLICATION-MH1-INTEGRATION
protocol_version: 6.4.0
status: active-reopened
created_date: 2026-09-21
revision: 23
reviewed_date: 2026-09-22
workplan_review_status: implementation-review-no-pass-reopened-1
implementation_review_candidate: c9b4a713511329988d26311c8b6bb5ef79f0bed1
implementation_review_domain: D4
branch: design/mlff-final-production-model-publication-mh1-integration
basis_commit: 237448b449b6f8042de5f239e5fefdfd54e3b2c3
highest_affected_domain: D3
d1_d2_change: false
production_gpu_qualification: deferred-to-actual-campaign-and-final-release
---

# MLFF final-production model publication + lightweight MH-1 integration — D3 -> D4 workplan

## 0. Disposition

**IMPLEMENTATION REVIEW NO-PASS / REOPENED FOR D4 REPAIR. Revision-22 D3 remains coherent and frozen; no Serious Challenge is active.**

Independent Review of assembled candidate `c9b4a713511329988d26311c8b6bb5ef79f0bed1` found blocking D4 violations at the publication-currentness, durability/trust, P7 realization/execution, qualification-binding fence, and MH-1 lightweight-evidence boundaries. The implementation must repair the existing owners directly; no new selection rule, currentness database, publication registry, deployment registry, scheduler, trainer, wrapper hierarchy, or cleanup authority is authorized.

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
    artifact_locator_token
    model_relative_path
    model_sha256
    model_size_bytes
serialization_format
serializer identity
torch/MACE/e3nn/Python serialization-runtime metadata where needed for diagnosis/compatibility
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

`artifact_locator_token` is excluded for the same reason. It is a filesystem locator/version token only, never scientific or deployment identity.

This derived digest is not a second scientific member identity. `FinalProductionPublicationDecision.member_digest` remains the sole checkpoint/member-selection identity; `model_artifact_set_digest` identifies only the exact serialized representation consumed by deployment descendants.

`serialization_format`, serializer/runtime version and serializer identity are **representation-compatibility metadata**, not scientific/member identity and not part of `model_artifact_set_digest`. A source-code, Python, Torch, MACE or e3nn runtime change does not by itself force reserialization; it forces a compatibility decision before consequential reuse when the recorded serializer/runtime material no longer proves the current loader boundary.

Reuse the existing MACE runtime-freeze/version/source-compatibility owners where applicable rather than inventing a second dependency probe. `train-production` create-or-verify is the sole producer-side repair owner:

- when recorded runtime/format compatibility is still positively established, SHA/state/architecture/head/dtype authentication is sufficient;
- when the loader/runtime boundary changed or compatibility is otherwise uncertain, descriptor-authenticate + trusted-stage the existing full model, load it through the current supported loader, reconstruct the exact selected checkpoint through the native provider, and require exact state/architecture/head/dtype/inference-mode equality;
- if that proof passes, reuse the exact existing model bytes; no reserialization is justified;
- if the old pickle cannot load but the selected checkpoint still reconstructs the exact same accepted portable state/architecture/head/dtype, publish a **fresh successor representation** at a new immutable locator with zero TRAIN2/EVAL2; preserve the old record/bytes as history;
- if provider reconstruction itself no longer proves the same learned state/architecture semantics, fail closed and route the upstream challenge. Never call that a serialization repair.

Downstream consumers never rewrite P5 product bytes. They fail closed on unsupported/incompatible representation; P7 may proceed only after its own authenticated load/export path proves the exact current source state. Ordinary read-only `status` does not deserialize the pickle and therefore reports durable byte/product currentness, not an independent claim that an arbitrary changed local loader can consume it; when recorded runtime metadata differs from the current supported runtime surface, status may expose that as a compatibility/reclosure advisory rather than pretending the mismatch was tested.

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

    artifact_locator_token is a non-authoritative collision-resistant create-once locator token
    model_relative_path is relative, confined and normalized and contains that locator token
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
        publication.json
        decision-<full-final-decision-digest>/
          seed-<seed>-<full-model-sha>-artifact-<locator-token>.model
```

Exact spelling is delegated D4. The path/identity rules are:

- authoritative immutable paths use collision-proof full digests, or an engineering-equivalent collision-proof encoding; shortened digest prefixes are display-only;
- the immutable model path may depend on already-known parent/member identities such as `FinalProductionPublicationDecision.content_digest`, member id/seed, and the serialized model SHA;

- the final leaf also carries a fresh collision-resistant **artifact locator token** generated before placement; it is not part of scientific/model-artifact-set identity;
- create-once collision handling may choose another fresh locator token, but may never overwrite an occupied locator;
- therefore a current artifact whose recorded pathname was externally corrupted can be replaced by a successor record at a fresh immutable pathname even when reconstruction deterministically reproduces the **same** `model_sha256`;
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

`publication.json` is at the stable `N_<size>/` level, not inside a decision-version directory. Its content points to the current immutable decision/member artifacts; replacing the projection never rewrites those artifacts.

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

A model publication reused across a **predecessor executable/source-tree change**, or encountered by `train-production` after a recorded serializer/runtime compatibility change, receives one additional compatibility proof before it is accepted as directly reusable:

1. descriptor-authenticate the recorded old model bytes/size;
2. stage those authenticated bytes into trusted private scratch;
3. load with the current supported `torch.load(..., map_location="cpu", weights_only=False)` path;
4. reconstruct the exact selected checkpoint through the native provider;
5. require the reloaded object's full-state digest, execution-architecture digest, head inventory/target head, learned dtype and inference mode to equal the selected provider realization and recorded product metadata.

If the old pickle is no longer loadable but the selected checkpoint still reconstructs to the **same** accepted state/architecture/head/dtype, rebuild only the full-model representation into a fresh immutable locator and continue representation reclosure with zero TRAIN2/EVAL2. This applies whether the trigger was mdstats predecessor-source drift or the serialized-model loader/runtime boundary. If current provider reconstruction no longer proves the same state/architecture semantics, fail closed and route the upstream challenge; do not silently call that a serialization repair.

Ordinary read-only `status` does not perform this executable deserialization. For predecessor-source reclosure, it relies on the fact that a new current reclosure could only have been published after the compatibility proof. For a dependency/runtime-only change that does not alter predecessor source identity, status may report the durable product as current while explicitly marking loader compatibility as unverified/advisory until a consequential consumer or `train-production` performs the proof; it must not claim that a changed loader was tested.

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
5. derive the immutable final filename from decision/member identity, full model SHA, and a fresh collision-resistant artifact locator token;
6. publish the final directory entry with **no-clobber/create-once semantics**. `os.replace` is forbidden for immutable model evidence;
7. if the chosen locator already exists, descriptor-authenticate it. Exact expected bytes may be reused for that locator; any mismatch chooses a fresh locator token rather than overwriting or wedging reclosure. Never deserialize an unreceipted pre-existing pickle merely to decide reuse;
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

- On a consequential `train-production` invocation, COMPLETE verification includes the runtime/serialization compatibility rule above whenever recorded compatibility material differs from the current supported loader surface. A byte/SHA match alone may not suppress that proof.
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
2. **model-publication candidate** — if a subordinate pointer exists, load its immutable record without declaring it publicly current, require exact replayed decision/member binding, authenticate every member through the shared descriptor owner, and when predecessor executable identity changed perform the current-runtime load/provider equivalence proof above before byte reuse.

This permits same decision + valid model bytes + stale predecessor source digest -> reuse model bytes, rebuild reclosure, atomically republish pointers, with zero TRAIN2/EVAL2/model reserialization.

The bypass never weakens selected binding, completion, CV/method/monitor lineage, committee replay, checkpoint ancestry, model member set, SHA/size/path trust or model-state identity. P7/public current resolvers stay strict.

### D3-6C — Projection commit and failure semantics

`publication.json` is non-authoritative mutable projection:

- using the authenticated descriptor for the stable `N_<size>` directory, create the private projection temp there without following symlinks, flush/fsync it, perform atomic replace **relative to that same directory descriptor**, then fsync the directory; never resolve/reopen the projection destination through an unchecked pathname;
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

Final-production status and `qualification status` therefore observe the **complete moving P5 parent graph** in the same SQLite read transaction:

```text
target-size revision / binding
current replay lineage/status
CV plan + CV acceptance pointers
final-production plan pointer
every assessment-position locator row for the binding
FinalProductionPublicationDecision pointer
FinalProductionModelPublication pointer
PredecessorReclosureRecord pointer
P7 pointers where single-size qualification is authorized
```

Extend the existing coherent snapshot owner to collect the dynamic
`post_selection:<binding>:assessment_position:*` locator rows inside that same
transaction; do not read them afterwards one-by-one.

After the transaction, observational code authenticates only immutable objects named by the captured values. A final decision is COMPLETE/current only if its exact final plan and every required final-seed run-evidence digest are the values named by the captured current position locators and its CV ancestry agrees with the captured CV pointers. This is a pure replay/lineage check over durable records; status does not reconstruct MACE or rerun EVAL2.

**Do not locate final-seed assessments by searching captured locator values.** For each `FinalPublicationSeedEvidence.run_evidence_digest` in the captured decision:

1. load that exact immutable `PostSelectionRunEvidence`;
2. require `assessment_role == final_seed`, selected binding equality, optimizer seed equality, and `content_digest == run_evidence_digest`;
3. derive the canonical position digest through the existing `assessment_position_digest(...)` owner from the evidence's own `assessment_position_policy_digest`, `training_trajectory_identity`, optimizer seed, and `fold_index=None`;
4. construct the exact binding-scoped `POINTER_ASSESSMENT_POSITION` key through the existing pointer-key owner/helper;
5. require the captured snapshot value at **that exact key** to equal the decision's `run_evidence_digest`.

This keeps currentness attributable to the accepted assessment-position identity itself. A historical/different position that happens to point to the same evidence digest is irrelevant. Do not reconstruct the assessment policy from mutable configuration merely to rediscover the key.

Neither public observer may perform a later independent P5/P7 pointer read.

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
- `component_input_digest` for `deployment_parity` and `dynamics` binds the current `model_artifact_set_digest` **and ordered `deployment_realization_set_digest`** (or exact equivalent member-keyed source + deployed-realization material);
- checkpoint-only components do not acquire the model serialization digest and remain reusable when all of their existing inputs remain unchanged;
- stress/capability evidence that actually depends on deployed runtime remains within the deployment-dependent input identity.

Do not invalidate all P7 evidence merely because the full-model pickle bytes/path changed.

### D3-15 — Preserve irreversible locked disclosure

`LockedActivationRecord` schema, its cohort-generation identity, and the append-only locked-reveal index remain unchanged by this feature. The activation record continues to bind the exact prerequisite component-evidence digests present at first reveal; those prerequisite digests may now transitively bind P5/deployed representation identity for deployment-dependent prerequisites.

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

- an existing authentic locked activation/result remains the immutable history/evidence of the unchanged scientific checkpoint product and the exact prerequisites that authorized its first reveal;
- a changed deployment representation triggers only deployment-dependent requalification;
- if activation occurred but the locked result was interrupted, the same activation may resume under the existing one-shot rules;
- the append-only reveal index continues to block any attempt to manufacture a fresh locked test.

A different learned state cannot be published as a representation-only successor under the same P5 decision; that is lineage corruption and fails closed.

### D3-16 — Terminal/release currentness binds the deployment representation without rebinding the whole attempt

Add explicit `model_artifact_set_digest` **and** `deployment_realization_set_digest` fields to the new terminal `ProductionQualificationRecord` and `ReleaseEvidenceIndex` schemas. The latter is an immutable reduction/provenance identity for the exact deployed realizations exercised by the referenced deployment-dependent component evidence; use a canonical null/not-applicable value only when no enabled component consumes a deployed realization. It is **not** a pointer to mutable attempt scratch.

These terminal owners are current only when:

- their ordinary `QualificationInputBinding` remains current;
- their stored `model_artifact_set_digest` equals the exact current P5 model-publication artifact-set digest;
- their stored `deployment_realization_set_digest` equals the **single common** ordered realization-set identity carried by every enabled immutable deployment-dependent component evidence object they reference;
- every deployment-dependent component outcome has an authenticated component-input digest binding **both** the P5 model-artifact set and the exact deployed-realization set that component actually exercised;
- no exposure-time resolver requires an attempt-local deployment receipt or ML-IAP scratch file to remain present after terminal completion;
- all other existing component/reference/currentness rules remain satisfied.

For `qualification status`, “exact current P5 model publication” means the content-addressed object named by the **captured** model-publication pointer from `campaign_owner_snapshot()`. Observation may authenticate that immutable object and its decision/member/artifact-set relation, but it must not read a later live P5 pointer. The captured predecessor-reclosure pointer is treated identically. Missing/corrupt/mismatched captured P5 objects make the P7 verdict blocked/superseded, never current.

The qualification plan and attempt identity do not need to change.

Schema evolution is explicit:

- new terminal record/release-index schemas are versioned successors (v2 or equivalent);
- old v1 objects remain readable as historical immutable evidence;
- a v1 terminal/release object lacking model-artifact-set **and deployment-realization-set** identity cannot be reported as the current release verdict once the new P5/deployment representation boundary is active;
- **do not manufacture cross-executable compatibility:** this implementation changes the mdstats executable source-tree digest, so pre-implementation P7 component evidence is ordinarily bound to an older `QualificationInputBinding` and cannot become current merely because its scientific checkpoint is unchanged;
- the append-only locked reveal history remains binding across that executable-currentness change, so an old revealed cohort never becomes fresh;
- selective reuse of checkpoint-only/locked component evidence is allowed only for representation-only successors created under the **same current qualification binding** (for example, rebuilding corrupted serialized product bytes without changing source/spec/environment);
- deployment-dependent components are then recomputed under the current model-artifact-set **and deployment-realization-set** identities and a new terminal/release record is reduced without reopening locked evidence.

Do not mutate historical v1 objects in place and do not weaken executable currentness to rescue them.

Released-attempt scratch follows existing P7/storage authority: bulk deployment artifacts/receipts may be reclaimed after the attempt's durable release evidence no longer needs a retention pin. Removing that scratch cannot stale an otherwise-current terminal/release record. Durable component/terminal/release evidence must carry enough identity to explain exactly which realization was exercised without reopening scratch.

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

### D3-17 admission rule — capture one coherent P5 product snapshot

Consequential P7 session construction must not resolve any moving parent of the final product in separate live reads. At session admission:

1. capture one complete P5 parent snapshot with the exact current selected binding, CV plan/acceptance, final plan, **all assessment-position locators**, final decision, predecessor reclosure, and model-publication pointers in one CampaignStore read transaction;
2. require the post-selection context selected binding to equal the captured binding;
3. authenticate only immutable objects named by that snapshot: captured final plan/CV ancestry, exact required final-seed assessment records, final decision replay/member set, predecessor reclosure, and model-publication record + actual model bytes;
4. require the final decision's completion/run-evidence digests to equal the exact captured final-seed position values; no later live assessment lookup may participate;

4a. derive each expected final-seed locator key from the decision-named immutable `PostSelectionRunEvidence` using the existing `assessment_position_digest(...)` + pointer-key owner exactly as above; key identity, not merely value membership, is required;
5. construct the scientific `QualificationInputBinding` from that captured decision/reclosure and resolve the subordinate deployment representation from that captured model publication;
6. if any captured object does not mutually agree, abort/retry session admission before executing a component.

Reuse the expanded `campaign_owner_snapshot(...)` or a narrower helper with identical one-transaction semantics. Do not reread a live P5 pointer/position during session construction. Later representation/scientific drift is handled by terminal/release/first-reveal CAS fences, not by mixing two P5 moments into one attempt.

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

The receipt also records/validates the P5 source execution-architecture digest used by the successor deployment identity.

The **deployed ML-IAP artifact and its receipt are authority-bearing executable inputs too**. Replace the current `Path.is_file()/read_bytes()` reuse check with the same no-follow descriptor discipline used elsewhere:

- open/parse the receipt without following a symlink and authenticate its schema/identity/source-model fields;
- open the deployed artifact no-follow, prove regular by `fstat`, and hash the exact opened bytes against the receipt;
- create deployment roots/scratch/final entries under the attempt owner without following planted intermediate symlinks;
- immediately before LAMMPS execution, authenticate the exact receipt/artifact pair again; if the runtime requires a pathname, stage the authenticated bytes into owner-private execution scratch and launch from that staged copy rather than hash one name and later reopen another.

A mutated/symlinked deployed artifact is lineage failure/rebuild input, never executable evidence.

#### Deployment realization identity and corruption recovery

`deployment_identity(member)` identifies the deterministic source/build contract. The actual ML-IAP bytes are a subordinate **deployment realization** because serialization/build bytes can differ across a legitimate rebuild.

Define one path-independent `deployment_realization_digest` (exact symbol delegated) from only:

```text
deployment_identity
deployed ML-IAP artifact SHA-256
```

Do not duplicate the P5 source model/state/architecture, target head, dtype, resource scope, exporter or builder fields in a second identity algorithm: they are already transitively and authoritatively bound by `deployment_identity`. The receipt may repeat them as authenticated audit fields, but mismatch is an error rather than a second source of truth.

The attempt-local root receipt is a mutable locator for the currently authenticated realization; it is not scientific authority. It records the realization digest, exact immutable realization path, deployed-artifact SHA, and source identities. The ML-IAP artifact itself is published create-once at a fresh immutable locator under the full deployment-identity root. A corrupt/missing current artifact is never overwritten: rebuild to a fresh locator and atomically advance the receipt only after descriptor authentication/durability. Old realization bytes remain inert historical attempt residue.

The mutable receipt update is performed relative to the already-authenticated deployment-identity directory descriptor: private temp, fsync, descriptor-relative atomic replace, directory fsync. A planted symlink at the receipt name or in an intermediate deployment directory cannot redirect either artifact or receipt publication.

Deployment-dependent component identity then binds the **ordered deployment-realization set digest** in addition to the P5 `model_artifact_set_digest`.

For one consequential P7 execution invocation, resolve one **invocation-frozen ordered realization set** before admitting any deployment-dependent component:

- create-or-authenticate every required member deployment realization under its existing per-deployment lock;
- derive the ordered realization-set digest from the exact publication member order and each `deployment_realization_digest`;
- freeze those exact member realization identities/immutable artifact locators in the in-memory session for that invocation;
- require both `deployment_parity` and `dynamics` to use that same frozen set for execution and reuse checks;
- include the set digest in those components' `component_input_digest` / stored evidence currentness;
- checkpoint-only components never acquire it.

Do not re-resolve the mutable receipt independently for each deployment-dependent component in the same invocation. A receipt advance after the session freezes its set cannot rewrite the session's already selected immutable artifacts.

Consequences:

- rebuilding to byte-identical ML-IAP output preserves the realization digest and may reuse otherwise-current deployment-dependent evidence;
- rebuilding to different ML-IAP bytes changes the realization-set digest and forces `deployment_parity` / `dynamics` to rerun before terminal reduction;
- no component evidence can remain current merely because `deployment_identity` stayed the same while the executable deployed bytes changed.

- a terminal/release reduction may reference only one common deployment-realization-set digest across **all** enabled deployment-dependent component evidence;
- if retained `deployment_parity` and `dynamics` evidence bind different realization sets, neither combination is terminally admissible: under the invocation-frozen set, reuse the matching component and rerun the mismatching component(s) before reduction;
- a process restart may reuse a previously exercised set only when all retained deployment-dependent evidence that is being reused agrees on that same set and the active-attempt retention owner still makes the required immutable artifacts available/authentic. Otherwise resolve a fresh invocation set and rerun only the affected deployment-dependent components;
- no new durable currentness registry or attempt identity is introduced; the frozen set is execution coordination derived from existing receipts/artifacts/evidence and is reconstructible on resume.

Implement this by reordering/factoring the existing deployment owner, not by adding a second deployment registry: the existing per-artifact lock, receipt, component-position/currentness owners and component-input digest remain the authority surfaces.

The mutable attempt-local receipt is therefore a **consequential reuse/execution locator only**. It is consulted when a session is about to reuse/build/execute a deployed artifact. It is never consulted by read-only public release currentness after the attempt has terminal durable evidence.

When a new/resumed P7 execution needs any deployment-dependent component, resolve the one invocation-frozen set first and only then ask whether existing component evidence has the matching component-input digest. Missing/reclaimed scratch rebuilds normally; byte-identical rebuild may reuse matching evidence, while different rebuilt bytes force only the mismatching deployment-dependent component(s) to rerun. Terminal reduction is forbidden until every enabled deployment-dependent component binds the same frozen set.

A representation successor for one committee member may reuse another member's deployed artifact when that other member's exact per-member deployment identity is unchanged. Aggregate `deployment_parity` / `dynamics` component input still binds the whole current `model_artifact_set_digest`, so aggregate evidence is rerun when any member representation changes.

### D3-17B — Commit-time P7 representation CAS without rebinding the attempt

Because model representation is deliberately outside `QualificationInputBinding`, an in-flight P7 attempt can overlap a representation-only P5 successor. Its old immutable component objects may remain historical evidence, but it must not publish an already-stale terminal/release pointer after the successor becomes current.

Extend the existing qualification pointer-publication owner with expected-current P5 fences:

- qualification **plan identity/currentness** remains scientific-binding-only and does not acquire model serialization identity;
- do not add a direct `model_artifact_set_digest` or model-path field to the scientific qualification binding, locked cohort-generation identity, or reveal-index key. `LockedActivationRecord.content_digest` nevertheless continues to include its existing `prerequisite_component_digests`; when those prerequisites are deployment-dependent, the activation record therefore **transitively records** the exact P5/deployed representation that authorized first reveal. The D3-17D P5-parent/model-publication CAS is an admission fence, not a new cohort identity, and never makes a revealed cohort fresh again;
- terminal `ProductionQualificationRecord` and `ReleaseEvidenceIndex` publication additionally require the current P5 model-publication pointer to equal the exact model-publication record digest consumed by the session;
- the same transaction requires the current final-publication decision pointer and predecessor-reclosure pointer to equal the session's exact scientific predecessors;
- it also requires the current CV plan/acceptance, final-plan pointer, and the exact derived **final-seed assessment-position key/value pairs** admitted into the session to equal the captured P5 parent snapshot. Do not compare by run-evidence value search. A decision pointer that has not moved does **not** rescue it when one of those exact position locators has advanced.

Before those pointer writes, re-establish the **current `QualificationInputBinding` identity** through the existing identity owners (selected publication/predecessor, executable, environment, specification, evidence roles/resource scope) and require exact equality with the session binding. The identity resolver must authenticate that the current final decision still reproduces from the current final-plan/CV/final-seed assessment parents. Then, inside the same `CampaignStore.exclusive_transaction()` that writes the P7 pointer, compare the exact captured parent-locator set plus decision/reclosure/model pointers before the write.

Factor this as one bounded identity-only resolver shared with first-reveal revalidation. It must reuse the same constructors/identities as `build_qualification_session(...)` but must not publish a reference request, open/modify attempt state, construct a provider/model, or create a second qualification-binding algorithm. Session admission may still build the ordinary full session outside critical sections.

If the qualification binding or any expected P5 pointer changed, the immutable P7 object remains historical but the current pointer write fails. This is a CAS fence, not a new lock or new attempt identity. Reuse/refactor the existing fresh-session/current-binding owner; do not invent a parallel binding algorithm.

Representation change while locked activation is in progress never reopens disclosure. The activation remains bound to the unchanged scientific qualification identity; any later terminal/release reduction must pass the current model-publication CAS.

While a P7 attempt is active, its retention/reference state names both exact representative checkpoint paths and the exact P5 published-model paths it consumes. This does not make the model representation part of `QualificationInputBinding`; it makes storage dependency reporting truthful. Current models remain independently protected by the P5/models-root owners.

### D3-17C — One observational owner for P7 terminal currentness

Current `qualification status` and the general campaign lifecycle do not use the same P7 terminal-currentness logic. The compact lifecycle path can currently report a terminal record from pointer presence while the richer qualification observer applies additional checks. Remove that semantic duplication for the dependencies touched by this cycle.

Extend `observe_current_qualification(...)` (or factor one pure subordinate currentness helper used by it) so, using only the captured `campaign_owner_snapshot()` mapping plus immutable objects, it authenticates:

- captured final-decision pointer/object relation;
- captured predecessor-reclosure pointer/object and current P5/P6 predecessor source-tree digest;
- captured P5 model-publication pointer/object plus descriptor-authenticated model bytes;

- captured final-plan/CV pointers plus every required final-seed assessment-position locator/object; the captured final decision must reproduce from those exact current assessment parents rather than from later live position reads;
- terminal/release `model_artifact_set_digest`;

- terminal/release `deployment_realization_set_digest` reconstructed/checked as one common set across every immutable deployment-dependent component evidence object named by the terminal/release objects; mixed sets are corruption/incomplete reduction. **Do not read attempt-local current realization receipts or ML-IAP scratch bytes for exposure-time currentness**;
- plan/terminal executable digest against current pure `resolve_executable_candidate_identity()`;
- current qualification specification digest when the caller supplies configuration, as `qualification status` already does.

This observer performs no qualification-session construction, no reference-request creation, no locked activation and no provider/model reconstruction. Reading/hash-identifying the current importable executable source surface is observational and is permitted; reading scientific source data or constructing models is not.

Released-attempt deployment scratch may be absent by accepted storage policy. Observation must remain correct after such cleanup; absence of scratch is not product or evidence corruption.

The general campaign lifecycle's single-size P7 step reuses this observation/helper instead of independently interpreting `ProductionQualificationRecord`. Because generic lifecycle intentionally remains config-independent, it may omit the specification comparison, but it MUST never report `release_qualified` when captured predecessor/model publication or current P7 executable identity makes the terminal record stale.

A public `release_qualified` claim additionally requires the captured `ReleaseEvidenceIndex` to authenticate against the exact current terminal record, binding, model-artifact-set digest, deployment-realization-set digest, component set, locked activation (when required), resource scope/observation and verdict. A crash that published the terminal record but not its release index is recoverable/incomplete exposure, not a complete release claim. Historical terminal objects remain immutable.

`status`, `advance` and `qualification status` therefore agree on the product/executable currentness introduced by this cycle without making ordinary observation consequential.

### D3-17D — First locked reveal is fenced by the exact current prerequisite representation

The locked test itself remains checkpoint-based, but **activation** is authorized only after every mandatory nonlocked prerequisite has passed. Those prerequisites can include deployment-dependent components. Therefore the first irreversible reveal may not race a P5 representation successor.

Immediately before a brand-new `record_locked_reveal(...)`, after `execute_nonlocked_components(session)` has returned the prerequisite set:

1. require every prerequisite evidence object to be the exact authenticated evidence admitted by the current session. Deployment-dependent prerequisites must bind the current P5 `model_artifact_set_digest` and **all agree on the same invocation-frozen deployment-realization-set digest** they actually exercised. Do **not** rebuild or reinterpret deployment scratch merely to authorize reveal; the immutable prerequisite evidence is the activation input, and an active attempt's existing retention rules separately protect any scratch still needed for resumed execution;
2. acquire locks in the existing global order:

```text
post_selection_publication_barrier(generation)
    -> qualification_publication_barrier(generation)
        -> CampaignStore.writer_exclusion()
```

3. immediately before the irreversible reveal, re-establish the current `QualificationInputBinding` through the existing owner and require exact equality with `session.binding` (including executable/environment/specification/evidence roles/resource scope);
4. while the writer exclusion is held, transactionally compare the current selected binding, captured CV plan/acceptance, final-plan pointer, the exact derived final-seed assessment-position key/value set, and exact final-decision/predecessor-reclosure/model-publication pointers against the session's admitted P5 parent snapshot;
5. only after that binding + pointer CAS succeeds, append/create-or-verify the reveal record and publish the locked-activation pointer while the same writer exclusion and publication barriers still prevent a competing P5/P7/current-selection writer from invalidating the authorization window;
6. release those locks before running the locked numerical evaluation.

Do not hold the writer gate or publication barriers across the locked test computation.

At minimum, a campaign configuration/specification edit or source/executable change detected at this boundary aborts **before** first reveal. The user can rerun nonlocked qualification under the new binding without consuming the reserved cohort.

Likewise, a successor EVAL2/final-seed assessment or final-plan/CV parent that advanced while the final-decision pointer still names the older decision aborts before reveal. Pointer equality at the decision row alone is never sufficient.

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

A conservative D4 estimator may use authenticated checkpoint size and/or exact in-memory state tensor bytes, but underestimation must not be accepted as success.

For serial committee materialization, recheck the retained free-space reserve **after each member's temporary serialization has consumed its actual bytes and before its create-once final placement**, accounting conservatively for the remaining members. Because the temp lives on the destination filesystem, a no-clobber rename/link-style placement need not double-count those same bytes. Recheck once more after the complete immutable set is durable and before the authoritative pointer transaction. On shortfall remove only the currently owned private temp; already-published immutable leaves remain inert/reusable residue and no pointer changes.

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
    authenticated N-level directory descriptor
    -> private temp in that directory
    -> flush + fsync
    -> descriptor-relative atomic replace
    -> fsync directory
```

An existing immutable destination is descriptor-authenticated and reused only on exact expected bytes; it is never overwritten.

Directory creation is part of durability, not just containment. For every newly created component of `models/production/g<generation>/N_<size>/decision-...`, create/open it descriptor-relative with no-follow semantics and fsync the containing directory after the new directory entry is installed. Before the authoritative P5 pointer commit, the complete directory chain from an already-durable `CampaignPaths.models` anchor through the final model leaf must be durable.

The touched P7 deployment owner applies the same rule to newly created deployment-identity/realization directories, immutable deployed artifacts and the current receipt locator: fsync file content and the relevant parent directory entries before any component evidence that depends on them is published.

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

The new internal P5 model-publication lock namespace is owner-known coordination infrastructure and is never a storage action candidate. Storage integration tests must prove report/cleanup/archive/dedup cannot mutate a live publication lock, private in-flight serialization, current model product, or inert full-SHA+locator orphan.

Because canonical product files are immutable/versioned and `CampaignPaths.models` is a protected campaign container while exact current products are P5-owned child artifacts, superseded model bytes may accumulate. This cycle does **not** add a cleanup/retention authority merely to reclaim them. Retain ambiguous/historical bytes conservatively under that container/P5 boundary; if long-horizon accumulation becomes material, route a separate storage-policy change rather than deleting historical products by pathname heuristics.

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
mdstats/training_data/qualification/deployment.py
mdstats/training_data/qualification/runtime.py
mdstats/training_data/qualification/record.py
mdstats/training_data/qualification/store.py
mdstats/training_data/qualification/observation.py
mdstats/training_data/qualification/locked.py
mdstats/training_data/qualification/commands.py
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
docs/specs/training_data/mlff_storage_management_spec.md
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

- each member path also uses a fresh non-authoritative artifact locator token so same-SHA corruption can be reclosed without overwrite;
- no selection/ranking logic is introduced.

### Stage B — selected checkpoint -> full model materialization

Acceptance:

- nonterminal selected checkpoint materializes through the existing native provider;
- exact returned `evaluated_model_state_digest` is bound to the model member;
- portable CPU e3nn full model is saved at accepted dtype and eval mode;
- reload preserves exact state/architecture/head inventory/mode;
- native path uses `allow_forward_override=False`;
- immutable file placement is create-once/no-clobber and durable;

- newly created model publication directory entries are descriptor-relative/no-follow and fsynced through the complete path chain before pointer publication;
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

- executable-change model reuse requires current-runtime load + exact native-provider state/architecture/head/dtype equivalence; incompatible pickle with unchanged checkpoint semantics is representation-rebuilt only;
- mixed-size collection sends only PRODUCTION_REQUIRED jobs to the accepted global TRAIN wave;
- post-TRAIN revalidation prevents stale early classification from committing;
- every provider/accelerator is retired on success/failure.

### Stage E — observational lifecycle/status

Acceptance:

- coherent snapshot includes CV/final-plan pointers, every dynamic assessment-position locator, final decision, final model publication, predecessor reclosure and authorized P7 pointers; current final-seed parentage is then proven only through exact canonical locator-key derivation from the decision-named immutable run evidence;
- status consumes only captured pointers/immutable records, never later live pointer reads;
- COMPLETE requires descriptor-authenticated SHA/size of every member but no `torch.load`;
- missing/wrong-kind/wrong-size/SHA/unsupported-format model is not COMPLETE;
- status is filesystem-write/source-read/provider neutral;
- multi-size reports every N independently.

- successful `train-production` itself prints the canonical `.model` path/SHA/target head for every committed member; operator discovery does not depend on inspecting internal hashes or running another command.

### Stage F — P7 intake/currentness reconciliation

Acceptance:

- scientific `QualificationInputBinding` remains checkpoint-based;

- P7 session admission captures the complete P5 parent graph (CV/final plan, all assessment positions, decision, predecessor reclosure, model publication) in one coherent CampaignStore snapshot, derives the exact required final-seed position keys from decision-named immutable run evidence, and authenticates only those captured immutable parents;
- current P5 model-publication and predecessor pointers come from the same captured observation snapshot;
- deployment parity/dynamics component identity includes current model-artifact-set **and deployment-realization-set**; checkpoint-only components do not;
- terminal/release successor schemas bind both model-artifact-set and deployment-realization-set digests;
- historical older-executable P7 evidence remains historical and locked reveal remains consumed;
- deployment source is a trusted scratch copy made from descriptor-authenticated P5 model bytes;
- successor `deployment_identity` binds exact P5 source model/state/architecture identities and uses a collision-proof full deployment-root identity;
- deployment receipt records source model/state identities; exporter source artifact/state digests agree with the P5 member;

- deployed ML-IAP receipt/artifact reuse and execution use descriptor/no-follow byte authentication and trusted execution staging;

- each deployed ML-IAP build has a path-independent deployment-realization digest; deployment parity/dynamics bind the ordered realization-set digest;

- one P7 invocation freezes one ordered realization set before deployment-dependent component admission; parity/dynamics reuse/execution and terminal reduction must all agree on that set;

- realization receipts/ML-IAP files remain attempt-local reuse/execution state; terminal/release evidence records the exercised realization identity but public currentness survives legitimate released-scratch cleanup;
- corrupted deployed output rebuilds at a fresh immutable locator and advances only the attempt-local receipt locator; no overwrite of prior deployed bytes;
- terminal/release publication re-establishes exact current `QualificationInputBinding` before pointer CAS;
- terminal/release pointer publication CAS-checks the exact captured CV/final-plan/final-seed assessment parents **and** current final-decision, predecessor-reclosure and model-publication pointers;

- first irreversible locked reveal re-establishes the exact current qualification binding and is CAS-fenced under P5 barrier -> P7 barrier -> CampaignStore writer exclusion against the exact captured CV/final-plan/final-seed assessment parents and current prerequisite model publication;
- active P7 attempt references include exact P5 model paths without adding representation to the scientific attempt identity;
- `release_qualified` observation requires the matching authenticated release-evidence index, not a terminal-record pointer alone;
- `qualification status` and general lifecycle share the same pure P7 terminal-currentness observer for executable/predecessor/P5-model currentness plus internal deployment-evidence/realization consistency; they never promote mutable attempt scratch into public currentness authority;
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

- current model products remain protected by the models-root container **and** exact P5-owned child-artifact views;
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

| planted symlink/intermediate substitution during publication.json repair | anchored descriptor-relative projection write refuses redirect; authoritative product unchanged |
| private temp crash residue | removed/rebuilt without treating it as authority |
| immutable unreferenced full-SHA+locator model | inert, not auto-deleted/deserialized; reusable only after independent expected-SHA reconstruction |
| wrong/corrupt current model bytes | consumers fail closed; train-production may publish immutable successor |

| corrupt deterministic canonical leaf reproducing same model SHA | successor uses fresh artifact locator; no overwrite and no permanent wedge |
| predecessor code change + still-loadable old model | current-runtime load/provider equivalence passes; bytes may be reused with new reclosure |
| predecessor code change + old pickle un-loadable but same checkpoint semantics | rebuild representation only at fresh locator; zero TRAIN2/EVAL2 |

| Torch/MACE/e3nn/Python loader boundary changes, old pickle still loads identically | reuse exact bytes after current-loader/provider equivalence proof; no TRAIN2/EVAL2 |
| loader boundary changes, old pickle no longer loads but checkpoint semantics identical | publish fresh successor representation only; historical bytes preserved; zero TRAIN2/EVAL2 |
| predecessor code change + provider architecture/state drift | fail closed/upstream challenge; never relabel as serialization repair |
| wrong decision/member/order binding | fail closed |
| missing selected checkpoint | fail closed |
| chosen immutable locator collision | exact expected bytes -> reuse; mismatch -> choose fresh locator; never overwrite |
| digest-prefix collision attempt | impossible by canonical full/collision-proof identity |
| intermediate/final symlink substitution | descriptor/no-follow authentication rejects |

| pre-planted intermediate symlink on publication write | anchored descriptor-relative creation refuses redirect; no external write |

| crash after nested model directory creation but before pointer commit | no current product is exposed; fsynced directory chain is safe inert residue/reusable only through authenticated reclosure |
| hash-then-reopen race attempt | same-descriptor source auth / trusted scratch staging prevents substitution |
| status | side-effect-free; SHA/size authenticates current model; reports direct `.model` paths |

| train-production completion output | every committed size/member prints canonical model path, SHA and target head; never trainer terminal model |
| same-byte workspace relocation | product/deployment currentness unchanged |
| P7 reference/deployment split | checkpoint provider remains reference; deployment consumes authenticated P5 model bytes |

| P7 admission pointer race | one captured P5 product snapshot; no hybrid old decision/reclosure + new model-publication session |

| P7 admission assessment-parent race | captured decision must reproduce from captured final-plan/CV/final-seed position locators; no old decision + new assessment hybrid executes |

| same run-evidence digest present at a historical/different assessment position | ignored; only the exact canonical key derived from that run evidence may satisfy currentness |
| forged/value-searched locator implementation | acceptance test plants same digest at wrong position while exact current key differs; status/P7 must reject |
| status during successor EVAL2/assessment publication | reports the exact captured parent graph (or blocked/waiting), never COMPLETE from old decision plus newer assessment positions |
| P7 deployment identity collision | full/collision-proof deployment identity root; no `[:16]` authoritative namespace |

| deployed artifact/receipt symlink or byte mutation | no-follow receipt/artifact authentication rejects before LAMMPS execution |

| planted symlink during deployment receipt advancement | descriptor-relative temp/replace refuses redirect; prior authenticated realization remains authoritative |

| deployed artifact corrupt then rebuilt to identical bytes | fresh immutable locator; same realization digest; otherwise-current deployment evidence may be reused |
| deployed artifact corrupt then rebuilt to different bytes | fresh realization digest; deployment_parity/dynamics rerun before terminal verdict |
| same deployment identity but changed deployed bytes | old deployment-dependent component evidence is stale by realization-set digest |

| parity evidence on realization set R1 + dynamics evidence on R2 | terminal/release reduction refused; rerun mismatching deployment-dependent component(s) under one invocation-frozen set |
| concurrent receipt advance after invocation freezes R1 | current invocation continues from immutable R1 artifacts; receipt advance does not silently switch one later component to R2 |

| terminal/release realization-set field disagrees with its referenced deployment-dependent component evidence | fail closed as corrupt/internally inconsistent evidence |
| deployment receipt/scratch is rebuilt or reclaimed after prerequisite evidence was recorded | does not rewrite prerequisite history; reveal uses exact immutable prerequisite evidence and current P5 product/binding fences, never a mutable receipt as authority |
| unchanged member in changed committee representation | its per-member deployed artifact may be reused; aggregate deployment component evidence reruns |
| representation successor during P7 run | stale terminal/release pointer CAS fails; old object stays historical; locked activation is not reopened |

| successor final-seed assessment advances before terminal/release while final-decision pointer is still old | complete-parent CAS rejects current P7 pointer publication |

| representation successor before first locked reveal | prerequisite/model CAS fails before reveal; cohort remains unopened |

| config/spec/executable/binding drift before first locked reveal | fresh binding check fails before reveal; cohort remains unopened |

| final-plan/CV/final-seed assessment drift before first locked reveal with unchanged decision pointer | complete-parent CAS fails; cohort remains unopened |
| representation successor after locked reveal | reveal remains consumed; deployment prerequisites/terminal are refreshed under current artifact set, no second reveal |
| crash after terminal record before release index | no public `release_qualified`; rerun publishes/repairs release index without reopening locked evidence |

| released attempt deployment scratch cleaned | current release/status remains valid from immutable evidence + current binding/P5 product; no scratch recreation by status |
| qualification rerun after released scratch cleanup | consequential session rebuilds realization; identical bytes may reuse matching component evidence, different bytes rerun deployment-dependent evidence only |
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

P7 coherent P5 product-snapshot admission race tests

coherent dynamic assessment-position snapshot/replay tests for lifecycle + qualification status

exact-assessment-position-key tests: same value at wrong key cannot satisfy status/admission/CAS
P7 old-decision/new-assessment and new-plan/old-decision admission race tests
P7 deployment-identity successor/full-root/receipt migration and per-member reuse

P7 deployed-artifact/receipt no-follow mutation/symlink/trusted-execution-staging tests

P7 deployment-realization identical-byte/different-byte rebuild and component-invalidation tests

P7 mixed parity/dynamics realization-set convergence and concurrent-receipt-advance tests

P7 terminal/release deployment-realization-set **internal evidence-consistency** tests
P7 first-reveal prerequisite-evidence/P5-currentness tests that do not treat mutable deployment receipts as reveal authority
P7 fresh-locator/no-overwrite deployment corruption recovery tests
P7 terminal/release commit-time P5 decision/reclosure/model CAS races

P7 commit-time CV/final-plan/final-seed assessment-parent CAS race tests

P7 first-locked-reveal prerequisite/model CAS and lock-order/crash-resume tests

P7 first-reveal config/spec/executable/full-binding drift-before-reveal tests

P7 first-reveal unchanged-decision-but-changed-assessment-parent race tests
P7 release-qualified terminal/index atomic-exposure recovery tests
P7 qualification-status + general-lifecycle shared currentness observation

P7 released-attempt scratch-cleanup -> status/release-currentness remains valid; status performs zero scratch reconstruction
P7 selective component invalidation and locked one-shot preservation
P7 terminal/release v1->v2 historical readability/currentness without cross-executable evidence promotion
storage owner/protection
MH-1 foundation/head/selected-head tests
generic MACE execution/CuEq parity tests
publication-set-lock / atomic three-pointer transaction / crash-injection tests
descriptor no-follow path-substitution / trusted-staging tests
private-temp vs immutable-orphan recovery tests

same-model-SHA corrupted-leaf -> fresh-locator successor recovery test
code-change reclosure load/reuse vs representation-rebuild vs provider-drift fail-closed tests

serializer/runtime-version drift load-reuse vs representation-only rebuild tests
P5 publication disk-reserve/actual-size-recheck/ENOSPC/fsync-failure tests
status SHA-corruption/coherent-reclosure-pointer/workspace-relocation tests

train-production direct published-model locator/output tests
write-side intermediate-symlink/no-clobber confinement tests

projection and P7 current-receipt descriptor-relative atomic-replace symlink-race tests

nested-directory fsync/failure-injection durability tests for P5 model publication and touched P7 deployment roots
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
57. A corrupted occupied model leaf permanently wedges reclosure because the path is deterministically derived only from model SHA/decision/member and no fresh locator is available.
58. Executable/source-tree reclosure can reuse old full-model bytes without proving they load under the current runtime and equal the exact selected provider state/architecture/head/dtype.
59. P7 re-authenticates the P5 source model safely but still trusts a deployed ML-IAP artifact/receipt via symlink-following or hash-then-reopen pathname checks before LAMMPS execution.
60. Terminal/release or first locked activation can publish/reveal after the current qualification binding (specification/executable/environment/evidence roles/resource scope) has drifted, even when P5 pointers themselves remain unchanged.
61. The normative documentation set omits `mlff_storage_management_spec.md` even though exact P5 product ownership under `models/` changes.
62. P7 session construction can combine P5 decision/reclosure pointers from one CampaignStore moment with a model-publication pointer from another before any component runs.
63. The implementation creates a second qualification-binding/currentness algorithm instead of factoring the existing identity owners for admission/commit/reveal revalidation.
64. The locked **cohort/reveal identity** is made representation-specific, or `LockedActivationRecord` stops recording exact prerequisite component digests, or first reveal is implemented without the D3-17D current P5 parent/model-publication fence.
65. A rebuilt deployed ML-IAP artifact can have different bytes under the same deployment identity while old deployment-parity/dynamics evidence remains current.
66. Corrupt deployed output is repaired by overwriting a previously receipted artifact instead of publishing a fresh immutable realization locator.
67. P5 model files or touched P7 deployed artifacts are fsynced without durably fsyncing newly-created containing directory entries before dependent pointers/evidence become current.
68. Terminal/release evidence cannot prove which deployed-realization set its referenced deployment-dependent component evidence actually exercised, or the stored realization-set identity disagrees with those immutable component records.
69. First locked reveal fails to bind the exact immutable prerequisite component evidence, or incorrectly treats a mutable/reclaimed deployment receipt as the authority that determines whether an already-recorded prerequisite pass exists.
70. Public lifecycle/status or P7 session admission can combine a final decision pointer from one instant with final-plan/CV or final-seed assessment-position locators from another, and still report/execute it as current.
71. The coherent snapshot captures only fixed pointer kinds and leaves dynamic `assessment_position:*` rows to later independent reads.
72. P7 terminal/release publication or first locked reveal CAS-checks the final-decision pointer but not the exact captured CV/final-plan/final-seed assessment parents, allowing a stale decision to survive a parent-locator advance.
73. `train-production` treats a changed Python/Torch/MACE/e3nn serialization-loader boundary as irrelevant merely because model bytes/SHA are unchanged, or downstream code rewrites historical P5 product bytes instead of failing closed / invoking producer-owned representation reclosure.
74. Loader incompatibility is repaired by retraining/re-EVAL2 even though the exact selected checkpoint reconstructs the same accepted state/architecture/head/dtype.
75. `publication.json` or the P7 current-realization receipt is atomically replaced through an unchecked pathname/intermediate symlink rather than relative to an authenticated owner directory descriptor.
76. `deployment_realization_digest` redefines source/head/dtype/exporter fields already owned by `deployment_identity` instead of composing from that identity plus exact deployed bytes.
77. Disk admission either assumes estimates after actual serialization is known or unnecessarily requires all committee temporary serializations to coexist despite accepted serial materialization.
78. Status/P7 determines current final-seed assessment parentage by searching for a matching `run_evidence_digest` anywhere in captured `assessment_position:*` rows rather than deriving and checking the exact canonical locator key from the immutable run-evidence identity.
79. D4 invents a second assessment-position/policy-key algorithm instead of reusing `assessment_position_digest(...)` and the existing binding-scoped pointer-key owner.

80. Public P7 currentness requires attempt-local deployment receipts/ML-IAP scratch to remain present after terminal release, contradicting accepted released-attempt cleanup/retention semantics.
81. `qualification status` rebuilds or re-authenticates deployment scratch as part of ordinary observation instead of resolving durable immutable release evidence.

82. One terminal/release record can combine deployment-dependent component evidence from different deployment-realization-set digests.
83. `deployment_parity` and `dynamics` independently follow a mutable current receipt within one invocation instead of consuming one frozen ordered realization set, allowing a mid-run receipt advance to switch executable bytes.

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

1. Every frozen selected size has exact P5 decision membership plus a reloadable, descriptor-authenticated, no-clobber full MACE `.model` representation for every published member, with a fresh locator mechanism that cannot wedge same-SHA repair.
2. Representation comes from the exact selected checkpoint/provider state, never trainer terminal output, with live/EMA/state/architecture/head/dtype equivalence and bounded supported-consumer usability.
3. One publication-set lock plus one atomic CampaignStore product-pointer transaction makes decision/model/reclosure visibility crash-consistent and restart-safe.
4. Legacy completed campaigns reclose with zero TRAIN2/EVAL2 and independently reuse a still-valid model publication or still-current predecessor reclosure when only the other descendant is stale; serialized-loader/runtime drift is resolved by current-loader equivalence proof or representation-only successor publication, never retraining.
5. Public lifecycle/status reports COMPLETE only after decision + completion + authenticated model publication + current predecessor reclosure for every selected size, from one coherent owner snapshot that also captures CV/final-plan and assessment-position parents; each required final-seed parent is current only at the exact canonical locator key derived from its immutable run evidence.
6. P7 admission starts from one coherent captured **complete P5 parent graph** (including final plan/CV/assessment positions); P7 keeps checkpoint reconstruction as scientific reference, consumes descriptor-authenticated P5 model bytes only for deployment, freezes one authenticated ordered deployment-realization set per consequential invocation, makes every deployment-dependent component and terminal/release provenance agree on that same set without making mutable scratch exposure-time authority, versions the deployment-source identity, invalidates only deployment-dependent evidence for representation changes, and re-establishes both the exact qualification binding **and captured P5 parent-locator set** before CAS-fencing terminal/release publication.
7. `qualification status` and general lifecycle share one observational P7 currentness owner for current executable/predecessor/model-representation dependencies touched by this cycle.
8. One-shot locked disclosure is never reopened; the cohort/reveal identity remains representation-independent while the immutable activation record preserves the exact prerequisite evidence that authorized first reveal; representation-only repair preserves current predecessor reclosure/attempt identity when applicable; historical older-executable P7 evidence remains historical.

8a. A first locked reveal re-establishes the exact current qualification binding and captured CV/final-plan/final-seed assessment parents, and is authorized under a short P5/P7/writer critical section that proves its immutable prerequisite evidence still corresponds to the exact current P5 model publication; the activation records the exact prerequisite evidence digests, including any realization identity those evidence records exercised. Terminal `release_qualified` exposure requires the matching release index and never depends on retained attempt scratch.
9. P5/P7 disk admission, anchored no-follow creation/authentication, descriptor-relative mutable-locator replacement, full directory-entry + file fsync/no-clobber durability, resource retirement and reconciled P5/models-root storage ownership remain within existing owners; the accepted global TRAIN scheduler is unchanged.
10. `train-production` directly prints authoritative usable model paths/SHA/target head, and current documentation consistently distinguishes checkpoint, P5 full model and P7 deployment artifact.
11. MPA-0 affected regression and bounded real-owner selected-checkpoint publication pass; MH-1 passes the lightweight source/head/reconstruction/publication checks, while long campaign/GPU/MD qualification remains deferred.

Any failed item above is an implementation NO-PASS. Local helper names, exact private temp names and equivalent no-clobber primitives remain D4 choices.

> **Review-history note:** Sections 27 onward are chronology of earlier workplan reviews. For the reopened implementation, Sections 0-26 **plus Section 26A** are normative; Revision-23 Section 26A is the mandatory D4 repair delta over the still-binding Revision-22 architecture. Earlier review-history wording is rationale/evidence only.



## 26A. Revision-23 implementation Review reopen — mandatory D4 repair delta

### Review disposition and basis

Reviewed assembled implementation candidate:

```text
c9b4a713511329988d26311c8b6bb5ef79f0bed1
```

Baseline handoff state:

```text
Revision-22 workplan head:
cb2aff3bf42c4cbd3a891a52a1b726f443b3033e
```

**NO-PASS.** The blockers below are violations of the existing Revision-22 architecture. They do not reopen D1/D2 and do not require a D3 redesign.

The core protected outcome remains unchanged:

```text
P5 scientific decision
    -> exact selected checkpoint/provider state
    -> durable authenticated full .model
    -> coherent current P5 parent graph
    -> P7 checkpoint reference + authenticated deployment source
    -> one-shot qualification/release evidence
```

Repair must alter/reuse existing owners. Do not add compensating wrappers, a second pointer/currentness layer, another artifact registry, or family-specific MH-1 machinery.

### IR23-B1 — P5 can commit a stale scientific parent graph after expensive materialization — BLOCKING

Observed implementation:

- `publish_final_production_model_products(...)` acquires the generation `post_selection_publication_barrier`, then immediately persists the decision/model/reclosure objects and publishes the three-pointer set.
- `publish_current_post_selection_pointer_set(...)` atomically writes the three rows and fences the selected target-size binding, but does **not** validate the final plan, CV plan/acceptance, or exact final-seed assessment-position parents.
- recovery replays the decision under the earlier publication-set lock, but expensive serialization/reclosure can occur before the later generation barrier.
- the committed stale-classification test mutates the recovery replay between classification and publication-set-lock acquisition; it does not exercise a final-plan/EVAL2 assessment advance **after** that replay/materialization and **before** the generation-barrier commit.

Counterexample:

```text
old decision/product replay succeeds
    -> expensive materialization/reclosure
    -> another P5 writer acquires generation barrier
       and advances final plan or one required final-seed assessment position
    -> old publisher later acquires generation barrier
    -> selected binding is still current
    -> atomic three-pointer transaction republishes old decision/model/reclosure
```

That violates blocking conditions 31, 70, 72 and the core rule that classification is an admission hint, not commit authority.

Required repair:

1. Reuse/factor the existing exact decision-replay/current-parent machinery; do **not** add another P5 state machine.
2. Inside `publish_final_production_model_products(...)`, immediately after acquiring `post_selection_publication_barrier` and before storing/publishing the authoritative pointer set, replay/re-resolve the exact current P5 parent graph and require the resulting `FinalProductionPublicationDecision.content_digest` to equal the decision being committed.
3. That late check must cover the current CV plan/acceptance, final plan, completion, committee/head/method identities, and the exact final-seed assessment-position keys derived through the existing `assessment_position_digest(...)` + binding-scoped pointer-key owner.
4. If any parent advanced, abort before the three-pointer transaction. Existing immutable model bytes may remain inert/reusable residue; do not delete them and do not move an old pointer set.
5. Keep the selected-binding CAS inside the existing CampaignStore transaction as the final database fence. Do not move expensive reconstruction/serialization into the generation barrier or SQLite transaction.

Required falsification:

- deterministically advance a required final-seed assessment locator after replay/materialization but before generation-barrier commit; old publisher must not change any product pointer;
- repeat with final-plan/CV-parent advance;
- prove the newer current product/parent graph remains current and the old immutable model residue is harmless/reusable.

### IR23-B2 — durable model/deployment publication is not fail-closed at the descriptor/fsync boundary — BLOCKING

Observed implementation:

- `model_artifact_trust._open_or_create_directory(...)` swallows `OSError` from the required parent-directory `fsync`;
- `model_artifact_trust.place_immutable_file(...)` likewise swallows `OSError` from the post-link directory `fsync`;
- `place_member_model(...)` authenticates the destination directory by descriptor but then reconstructs `directory_path / temporary_name` and performs `torch.save` / reload through that pathname instead of creating and using the temp relative to the authenticated directory descriptor;
- P7 deployment-root creation still uses ordinary `Path.mkdir(parents=True, exist_ok=True)`, and the subsequent `fsync_parent_directory(root / receipt)` fsyncs the new root itself rather than proving the newly-created root entry durable in its parent.

This violates blocking conditions 33, 54, 67 and the accepted storage durability rule. A required fsync failure cannot be converted into success followed by authoritative pointer/evidence publication.

Required repair:

1. Change the existing shared trust owner; do not create a parallel durability subsystem.
2. Required publication fsync failures must propagate/fail closed. Best-effort swallowing is allowed only for cleanup/close paths whose failure cannot make an artifact appear durably published.
3. Create P5 private serialization temps relative to the already-authenticated destination-directory fd using no-follow/create-exclusive semantics. Pass the opened file object/fd to `torch.save` and current-loader verification where supported; do not reopen the authoritative temp through a reconstructed pathname.
4. Keep final immutable placement descriptor-relative/no-clobber and require the directory fsync to succeed before the artifact can participate in a model-publication record.
5. Rework the touched P7 deployment-root creation through the same anchored descriptor/no-follow directory owner and fsync the containing directory when a new deployment-identity directory entry is installed. Do not rely on `Path.mkdir` + fsync of the child directory as proof of parent-entry durability.
6. Preserve existing projection semantics: `publication.json` remains post-commit/non-authoritative, so projection failure may remain repairable without undoing the scientific product.

Required falsification:

- inject fsync failure while creating each new P5 directory component and after final immutable link; no product pointer may move;
- inject the equivalent P7 deployment-directory/artifact durability failure; no dependent component evidence may become current;
- race an intermediate-directory substitution between directory authentication and P5 serialization; no bytes may be written outside the authenticated publication directory;
- previous current product/evidence must remain intact.

### IR23-B3 — P7 deployed-artifact trust falls back to pathname reopen/direct execution — BLOCKING

Observed implementation in `qualification/runtime.py`:

- `_reuse_published_artifact(...)` authenticates `deployment-receipt.json` with the descriptor owner, discards that result, then reopens the receipt with `(root / receipt).read_bytes()`;
- the deployment cache fast path `_authenticated_artifact(...)` uses `Path.is_file()` plus `Path.read_bytes()`;
- `evaluate_deployed(...)` and `run_deployed_dynamics(...)` pass the original deployed-artifact pathname to the LAMMPS/runtime owner after earlier authentication rather than staging the exact authenticated bytes immediately before executable consumption.

This is the precise hash/check-then-reopen TOCTOU class prohibited by blocking condition 59 and by the shared executable-artifact trust boundary.

Required repair:

1. Remove the unsafe pathname fallbacks rather than wrapping them.
2. Extend/reuse `model_artifact_trust` so receipt bytes can be read from the same no-follow regular-file descriptor whose kind/identity is authenticated. Parse those exact bytes; do not authenticate one name and read another open.
3. Remove or rewrite `_authenticated_artifact(...)` so cached deployment artifacts are verified descriptor-relative under the authenticated deployment root. A cached `Path` is only a locator, never authority.
4. Before each real deployed static/dynamics execution, copy the exact descriptor-authenticated immutable ML-IAP bytes into attempt-owned execution scratch, fsync/hash-verify the staged copy, and pass only that staged path to LAMMPS/runtime. Reuse/generalize the existing authenticated-staging owner; do not add a second trust implementation.
5. Apply the same anchored rule to deployment build scratch/final placement where the current code can traverse an untrusted intermediate pathname.

Required falsification:

- replace/symlink the receipt after its first authentication but before parse; foreign receipt bytes must never be accepted;
- replace/symlink the cached deployed artifact after caching; the cache path must not bypass descriptor authentication;
- swap the immutable deployed pathname between resolution and LAMMPS launch; the runtime must execute only the staged authenticated bytes or fail before launch.

### IR23-B4 — the declared invocation-frozen deployment realization set does not freeze the exact executable artifacts — BLOCKING

Observed implementation:

- `freeze_deployment_realization_set(...)` records realization digests and populates `_deployment_cache`;
- `_frozen_realizations` does not own/verify the exact frozen artifact locator + SHA for later execution;
- after the set is frozen, `deployed_artifact(...)` may reject a missing cached path and rebuild/re-resolve another artifact while `_frozen_realization_set` remains the old digest;
- the current receipt-advance test leaves the old cached artifact intact, so it does not exercise deletion/corruption/rebuild after freeze.

Therefore component input can say realization set R1 while a later deployment-dependent execution actually runs R2. This violates blocking conditions 65, 68, 82 and 83.

Required repair:

1. Keep this as invocation-local execution coordination; do not add a durable realization registry or change `QualificationInputBinding`.
2. When freezing the set, retain the exact per-member immutable artifact locator/name, SHA, deployment identity and realization digest that constitute the set.
3. Once frozen, every deployment-dependent execution in that invocation must descriptor-authenticate and consume **that exact frozen artifact**. It may not follow a newer receipt or silently rebuild a replacement.
4. If a frozen artifact disappears/corrupts before execution, fail/abort the current invocation's deployment-dependent path. A subsequent invocation may resolve/build a new set and let component-input identity decide which evidence must rerun.
5. Terminal reduction continues to require all deployment-dependent component evidence to bind one common realization-set digest.

Required falsification:

- freeze R1, then delete/corrupt R1 and advance receipt/build R2 before dynamics; the same invocation must not execute R2 under R1's input digest;
- a new invocation may resolve R2 and rerun only mismatching deployment-dependent evidence;
- parity and dynamics can never be reduced from different sets.

### IR23-B5 — exact qualification binding is not re-established at the actual terminal/release/first-reveal fence — BLOCKING

Observed implementation:

- `require_current_qualification_binding(session)` re-resolves executable/environment/evidence roles but reuses `session.binding.specification`, stored resource-scope digest and stored predecessor fields instead of factoring the exact binding constructor used at admission;
- terminal and release publication call that helper before entering the P7 publication barrier/CampaignStore pointer transaction;
- first locked activation calls it before acquiring the required P5 -> P7 -> CampaignStore writer critical section; inside the critical section only the P5 parent pointers are checked;
- the committed test mutates the executable identity while calling the helper directly, but does not exercise drift between the precheck and irreversible/pointer-publication boundary.

This violates blocking conditions 60 and 63 and the one-shot rule in completion criterion 8a.

Required repair:

1. Factor one pure current-binding identity resolver out of the same constructors used by `build_qualification_session(...)`. Do not maintain a second binding algorithm.
2. The shared resolver must re-resolve the current specification from the authoritative command/config mapping, executable identity, environment identity, evidence-role membership and the accepted stable resource-scope material; predecessor identity remains tied to the exact current/captured P5 parent graph.
3. Session construction uses that resolver.
4. Terminal/release publication re-establishes the exact binding at the latest safe point inside the existing P7 publication critical section, immediately before the CampaignStore P5-parent/pointer CAS.
5. First irreversible reveal performs the same binding check **inside** the existing P5 barrier -> P7 barrier -> CampaignStore writer-exclusion critical section, immediately before the current-parent CAS/reveal record. No long numerical work may occur while those locks are held.
6. Preserve locked cohort/reveal identity independence from model representation.

Required falsification:

- mutate qualification specification/executable/evidence-role identity after the old precheck point but before terminal/release pointer publication; current pointers must not move;
- perform the same race before first reveal; the cohort remains unopened;
- ordinary representation-only P5 repair with unchanged scientific binding must still avoid a fresh cohort/reveal identity.

### IR23-B6 — lightweight MH-1 integration does not exercise the current MH-1 post-selection selected-checkpoint provider path — BLOCKING EVIDENCE GAP

Observed tests prove useful pieces but not the workplan's requested family-specific integration seam:

- the real-MH1 tests inspect the foundation `mace-mh-1.model` and serialize/reload that **raw foundation model** with source head `omat_pbe`;
- the canonical `[pt_head, target_head]` publication test uses a generic tiny MACE model;
- the head-order test locally reproduces/sorts a mapping instead of driving the current MH-1 foundation -> post-selection materialization/checkpoint -> `authenticate_post_selection_provider(..., allow_forward_override=False)` owner;
- no current test combines `mace_mh_1 / omat_pbe` with the selected-checkpoint provider reconstruction that P5 publication actually uses.

This is not a request for long TRAIN2/CV/GPU/MD qualification. It is the bounded integration check the stakeholder explicitly requested before the upcoming MH-1 campaign.

Required repair/evidence:

1. Reuse the current foundation/materialization/checkpoint/provider owners; do not add MH-1-specific production code.
2. On a bounded fixture with the real MH-1 foundation when bytes are readily available, drive `mace_mh_1 / omat_pbe` through the current post-selection two-head realization and a current-format bounded checkpoint, then authenticate that checkpoint through the actual selected-checkpoint provider with `allow_forward_override=False`.
3. Require the returned portable model to have canonical `[pt_head, target_head]` order, target-head index 1, exact provider state/architecture/dtype identity, publication save/reload, and—when pinned CPU deployment dependencies are available—the current ML-IAP builder construction.
4. No long training horizon, production campaign, GPU run or MD qualification is required.
5. If real MH-1 bytes/runtime are unavailable on the implementation host, preserve that as explicitly unavailable evidence rather than converting a generic tiny-model test into a claimed real-MH1 pass; the structural owner-path test must still cover the actual MH-1 family configuration/materialization code.

### IR23-E1 — executable acceptance evidence for the assembled candidate is not independently available — BLOCKING FOR CLOSEOUT

GitHub exposes a successful documentation-PDF workflow for an earlier implementation commit, but no test check/run for assembled candidate `c9b4a713511329988d26311c8b6bb5ef79f0bed1`. Committed tests are specifications/evidence producers; repository presence does not prove they executed successfully.

After IR23-B1..B6 are repaired, run and report the exact assembled-candidate acceptance:

```text
tests/test_mlff_p5_model_publication_owners.py
tests/test_mlff_p5_model_publication_acceptance.py
tests/test_mlff_p7_deployment_realization.py
tests/test_mlff_p7_product_currentness_fences.py
tests/test_mlff_mh1_publication_integration.py
```

plus the materially affected current suites for:

```text
P5 publication/reclosure/currentness
production global scheduler / multi-size finalization
campaign lifecycle coherent observation
P7 post-production qualification / locked one-shot / release observation
storage owner graph and storage integration
MACE execution semantics / selected-checkpoint provider
documentation/build validation
```

Also run the maintained affected collection/compile checks required by repository policy. Record pass/fail/skip counts and exact reasons for environment-dependent skips. Do not count the intentionally deferred long MH-1/GPU/MD campaign as a missing test.

### Revision-23 repair acceptance / stop conditions

The reopened implementation is Review-ready only when all of the following are true:

1. the late P5 generation-barrier replay refuses stale final-plan/CV/assessment parents before any authoritative product-pointer change;
2. required publication/deployment fsync failures propagate and descriptor-anchored temp/directory publication cannot write through a substituted path;
3. P7 receipt/cache/execution no longer contains a hash/check-then-path-reopen trust bypass;
4. one P7 invocation consumes exactly the artifact bytes represented by its frozen realization-set digest;
5. terminal/release and first locked reveal re-establish the same canonical qualification binding at their actual commit/reveal fences;
6. the lightweight MH-1 evidence crosses the current family-specific post-selection selected-checkpoint provider seam without long qualification;
7. the focused + affected assembled-candidate regression is executed and reported;
8. no new currentness database, publication/deployment registry, wrapper hierarchy, scheduler, trainer, cleanup authority, or family-specific production path was added to achieve the repair.

If repair evidence shows any of the original Section-25 D3 reopen triggers, stop and route a Serious Challenge to D3. Otherwise these findings remain D4 blockers under the accepted Revision-22 architecture.

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


## 37. Final exhaustive convergence review closure (Revision 10)

Review basis remains current executable repository state `237448b449b6f8042de5f239e5fefdfd54e3b2c3`, with the workplan repeatedly re-read as a fresh candidate after each repair.

The final passes additionally closed:

- deterministic content-addressed-path corruption recovery by separating byte identity from an immutable artifact locator token;
- stable N-level `publication.json` placement from immutable decision-version directories;
- current-runtime load/provider-equivalence proof before reusing a full model across predecessor executable changes;
- exact no-follow write-side confinement, not merely read-side authentication;
- successor P7 deployment identity/root/receipt binding to P5 source model/state/architecture;
- no-follow receipt + deployed ML-IAP byte authentication before LAMMPS execution;
- full current-`QualificationInputBinding` revalidation before P7 terminal/release publication and before first irreversible locked reveal;
- first-reveal serialization under the existing P5 -> P7 -> CampaignStore lock order;
- release-qualified observation requiring the matching release index;
- exact P5 model artifacts in the storage owner graph while retaining the models root as a conservative protected container;
- explicit train-production completion output for canonical model path/SHA/head;
- mandatory reconciliation of the current storage-management specification.

No remaining finding requires a D1/D2 change. No long real MH-1 campaign/GPU qualification is moved into development.

## 38. Revision-10 verdict

Revision 10 was an intermediate convergence candidate. Revision 11 preserves its trust/recovery architecture and closes the final coherent-admission and internal-consistency findings below.
