---
kind: implementation-workplan
workplan_id: MLFF-FINAL-PRODUCTION-MODEL-PUBLICATION-MH1-INTEGRATION
protocol_version: 6.4.0
status: active-reviewed
created_date: 2026-09-21
revision: 5
reviewed_date: 2026-09-22
workplan_review_status: pass-after-fourth-current-implementation-review
branch: design/mlff-final-production-model-publication-mh1-integration
basis_commit: 237448b449b6f8042de5f239e5fefdfd54e3b2c3
highest_affected_domain: D3
d1_d2_change: false
production_gpu_qualification: deferred-to-actual-campaign-and-final-release
---

# MLFF final-production model publication + lightweight MH-1 integration — D3 -> D4 workplan

## 0. Disposition

**PASS AS IMPLEMENTATION WORKPLAN AFTER FOURTH CURRENT-IMPLEMENTATION REVIEW / FROZEN FOR D4. No Serious Challenge is active.**

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
        decision-<final-decision-prefix>/
          seed-<seed>-<model-sha>.model
        publication.json
```

Exact spelling is delegated D4. The identity rule is not:

- the immutable model path may depend on already-known parent/member identities such as `FinalProductionPublicationDecision.content_digest`, member id/seed, and the serialized model SHA;
- it MUST NOT depend on `FinalProductionModelPublication.content_digest` when that record itself contains `model_relative_path`, because that would create a self-referential identity cycle;
- a bare mutable `seed-1.model` MUST NOT be the canonical durable artifact.

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

## 8. Publication atomicity and restart

### D3-4 — Create-or-verify

For each expected product relation:

- no current model-publication record -> materialize;
- current record + valid matching artifact -> reuse;
- current record + missing/SHA-mismatched/wrong-kind artifact -> consumers fail closed immediately, while `train-production` may perform representation-only reclosure from the authenticated selected checkpoint into a **new immutable artifact + successor model-publication record**;
- never overwrite or “repair in place” an artifact named by an immutable historical/current record.

File existence alone is never validity. Corrupt or missing product bytes are recoverable representation failure when the selected checkpoint lineage still authenticates; they are not authority to retrain, rerank, or mutate the old record.

At minimum authenticate:

```text
decision digest
member digest
member identity
representative checkpoint SHA
evaluation model state
existing evaluated_model_state_digest
target head
existing canonical execution-architecture digest
existing exact full-state/state_dict digest
serialized model SHA
```

Revision 2 was too restrictive here: the repository already has both the TRAIN2 evaluated-state digest and an exact deterministic MACE `state_dict` digest implementation in the deployment owner. Reuse or factor those current identities; do not define a third competing tensor hash.

### D3-5 — Crash-safe publication, concurrency and residue

Do **not** hold the generation-wide P5 publication barrier across model reconstruction or serialization; that work may be expensive and would unnecessarily block unrelated P5/storage publication.

Full PyTorch model serialization is not byte-deterministic. Therefore the existing `artifact_publication_lock` MUST guard a **stable logical publication key known before serialization**, not the eventual byte-SHA-derived model filename.

For each selected member derive a deterministic lock target from already-known authority, for example:

```text
CampaignPaths.models/
  production/g<generation>/N_<size>/
  decision-<final-decision-digest>/
  .member-<member-id>.publish
```

Exact spelling is D4-delegated. Under that lock:

1. re-read/re-authenticate any current model-publication record for this exact decision/member;
2. if it names a valid artifact, reuse those exact bytes;
3. otherwise reconstruct the native selected model, move it to CPU/eval mode, serialize to a private temporary file, reload/verify it, compute the byte SHA, derive the immutable SHA-bearing final filename, and atomically place it;
4. publish no current pointer yet.

This stable logical lock is required because two concurrent builders could otherwise serialize semantically identical models to different byte SHAs and bypass one another's path-specific locks.

Use run-owned/private temporary output in the destination filesystem and the shared persistence owner. Do not add a new lock implementation.

Uncommitted full-model residue is executable serialized content. If no authenticated product record/receipt names it, **do not `torch.load` it to decide whether it is reusable**. Under the stable logical lock, owner-proven confined regular non-symlink residue in the exact decision/member publication directory may be deleted as incomplete output and rebuilt from the authenticated checkpoint. Ambiguous/foreign paths fail closed.

Distinguish:

```text
AUTHENTIC CURRENT ARTIFACT
    named by authentic product record -> verify SHA/kind/path; reuse exact bytes

RECOVERABLE CURRENT-ARTIFACT FAILURE
    authentic record exists but artifact missing/corrupt
    -> fail consumers closed
    -> train-production may publish a new immutable successor from the checkpoint

UNCOMMITTED OWNER RESIDUE
    no authentic record names it
    -> never deserialize
    -> owner may remove under stable logical lock after confinement/type proof

FOREIGN / AMBIGUOUS PATH
    ownership or confinement not proven -> fail closed
```

Use the P5 generation publication barrier only for the short immutable-object/current-pointer/projection commit window.

A crash must never make a partial or unauthenticated model appear current, and a crashed lock holder must not strand recovery.

### D3-6 — Publication ordering and visibility

The current implementation publishes the P5 decision and predecessor-reclosure pointers inside `publish_final_production_publication()`. That ordering must be refactored narrowly so a **fresh** product cannot become publicly COMPLETE while its selected full model is still absent.

Required logical ordering for fresh publication:

```text
1. decide/reproduce FinalProductionPublicationDecision in memory
2. materialize + reload + verify every selected full model
3. persist decision object, predecessor-reclosure object, and model-publication object
4. under the existing P5 publication barrier, publish:
       a. subordinate model-publication pointer
       b. predecessor-reclosure pointer
       c. FINAL_PUBLICATION pointer LAST
5. report the size complete
```

Putting `FINAL_PUBLICATION` last gives the existing public decision pointer its natural commit-marker role: an observer may temporarily see a subordinate product pointer that does not yet match a current decision and must ignore it, but it must never see a newly current decision and infer completion before the required model publication is current.

For **legacy/current v3 decisions that already predate this feature**, the existing final-publication pointer remains valid scientific selection evidence. Lifecycle observation deliberately reports such a decision as product-reclosure WAITING until the subordinate product record exists. Reclosure adds only the subordinate product pointer and never rewrites/reranks the decision.

The implementation MAY factor the current `decide_final_production_publication()` and pointer-writing path to achieve this, but must not create a second publication transaction/lock subsystem.

### D3-6A — Recovery classification before expensive work

Current `execute_current_train_production()` plans every selected size, normalizes TRAIN recovery, and later enters serial EVAL2/finalization. For an already-complete valid decision, using that ordinary route merely to create a `.model` can needlessly revisit EVAL2 machinery.

After the collection-wide CV/currentness barrier and before new TRAIN/EVAL admission, classify each selected size:

```text
PRODUCT_COMPLETE
    current decision + current authenticated model publication

PRODUCT_RECLOSURE
    current decision + current completion + missing/stale model publication

PRODUCTION_REQUIRED
    no current final decision
```

Rules:

- `PRODUCT_COMPLETE`: verify/reuse product state; admit no TRAIN2/EVAL2.
- `PRODUCT_RECLOSURE`: authenticate the existing decision/checkpoint(s), materialize product only; admit no TRAIN2/EVAL2.
- `PRODUCTION_REQUIRED`: proceed through the existing final-plan/global-TRAIN/serial-EVAL2/publication machinery.
- The existing collection-wide CV barrier and collection-signature admission/currentness fences still govern any new production work.
- Classification occurs before TRAIN admission, but model reclosure/materialization is performed in the existing serial post-TRAIN finalization phase in frozen selected-size order. Only `PRODUCTION_REQUIRED` positions enter the global TRAIN wave. This avoids model reconstruction/serialization retaining accelerator state while new production training is admitted.
- Every publication/reclosure materialization must retire its provider and release transient accelerator residency before the next size/finalization step or any later TRAIN admission. No publication change may alter the accepted global TRAIN scheduler.

This is the required mechanism behind the “zero unnecessary EVAL2” acceptance claim.

### D3-6B — Reclosure bootstrap must bypass stale predecessor reclosure without weakening decision authentication

A code change in this cycle changes the P5/P6 executable source-tree digest. Therefore the existing strict `resolve_current_final_production_publication()` can reject the old publication **before** model reclosure, because that resolver intentionally requires a current `PredecessorReclosureRecord`.

Publication-only migration needs one narrow internal recovery seam owned by `train-production`:

```text
read the pointed FinalProductionPublicationDecision object
    -> authenticate current binding/final plan/completion/policy/CV/monitor
    -> recompute decide_final_production_publication(...) from already-persisted evidence
    -> require recomputed decision digest == pointed decision digest
    -> DO NOT require the old predecessor-reclosure source-tree digest to match
    -> materialize selected model(s)
    -> build the new current PredecessorReclosureRecord
    -> commit model-publication + reclosure pointers
```

This is not a weaker public publication resolver. P7 and ordinary current-product consumers continue to require the strict current predecessor reclosure. Only the production reclosure/migration owner may use this candidate resolver, and only after exact decision replay proves that no selection changed.

No EVAL2 numerical inference is rerun: `decide_final_production_publication(...)` re-authenticates the already-persisted representative/metric evidence.



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

Use durable product-record data. The normal observational projection should validate the record/binding/decision relation and cheaply require each advertised product path to be a confined regular non-symlink file. It need not SHA-256 rehash every large model on every `status` call; consequential consumers and `train-production` reclosure perform full byte authentication. Missing/wrong-kind product files are BLOCKED/WAITING as appropriate, never COMPLETE.

The new P5 model-publication pointer MUST be included in `campaign_lifecycle._post_selection_prefix(...)` / `campaign_owner_snapshot(...)`, so final-production status and `qualification status` observe the target revision, decision pointer, model-publication pointer and P7 pointers in the same SQLite read transaction. Do not add a second independent pointer read in either status command.

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

Because full PyTorch model loading is executable deserialization, authenticate expected SHA, confinement and regular/non-symlink type **before** `torch.load` / MACE inspection and avoid hash-then-reopen TOCTOU. Prefer one shared P5 model-artifact authenticator; when the downstream exporter must reopen by pathname, copy the authenticated bytes into attempt-owned scratch and export from that trusted copy.

The existing `MaceDeploymentArtifact` already reports `source_artifact_sha256` and `source_state_sha256`; require both to agree with the P5 model-publication member after export.

Update P7 disk-headroom estimation to account for the authenticated published model size plus deployment and ML-IAP scratch, not only the TRAIN2 checkpoint.

Do not duplicate P5 selection or checkpoint reconstruction logic inside P7.

### D3-18 — Executable-evolution consequence is explicit

Because the accepted P7 executable identity covers the importable mdstats source surface, this implementation itself will stale any pre-existing P7 terminal verdict produced by an older executable candidate. That is existing accepted P7 behavior, not a defect to paper over.

Consequences:

- older release/terminal/component objects remain historical and readable;
- an already-opened locked cohort remains irreversibly revealed through the global reveal index;
- this workplan does not authorize transferring an old locked PASS across executable identities;
- if a previously release-qualified single-size campaign must be qualified under the new executable, existing P7 authority governs what new independent locked evidence is required;
- the current stakeholder MPA-0 multi-size campaign is unaffected at P7 because multi-size qualification is intentionally unavailable and no release winner/locked activation exists.

Tests must prove the feature does not accidentally make historical P7 evidence current or reopen a revealed cohort.

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
- prove the post-selection output head inventory/order is exactly the current canonical `[pt_head, target_head]`, so the existing ML-IAP target-head index-1 contract is valid for MH-1 just as for MPA-0.

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

Use the repository's accepted `PROJECT-ENGINEERING-MEMORY.md` as non-authoritative learning support.

Material current lessons:

- reuse existing semantic owners rather than introducing parallel wrappers/registries;
- fail closed on checkpoint/product identity mismatch;
- restart expensive completed work from durable evidence rather than rerunning;
- real-owner integration is needed for claims synthetic fixtures cannot discriminate;
- storage actions depend on owner-certified currentness, not pathname heuristics;
- status/observation must remain side-effect free.

Historical MH-1 qualification remains useful for expected head inventory, SHA, and failure-regression shape, but later P5/TRAIN2/EVAL2 changes mean it cannot alone close current integration.

## 18. Expected implementation surface

Inspect ownership before editing; this is an affected-surface guide, not a requirement to touch every file.

Likely primary owners:

```text
mdstats/training_data/post_selection_publication.py
mdstats/training_data/post_selection_store.py
mdstats/training_data/campaign_post_selection_runtime.py
mdstats/training_data/target_size_execution/evaluation.py
mdstats/training_data/qualification/publication.py
mdstats/training_data/qualification/providers.py
mdstats/training_data/qualification/runtime.py
mdstats/training_data/storage/owners.py
mdstats/training_data/campaign_lifecycle.py
mdstats/training_data/_campaign_cli_core.py
```

Potential shared model serialization/reconstruction owner may live in current MACE realization/model-feature modules. Prefer sharing existing owner over adding another subsystem.

## 19. Documentation surface

Reconcile current authoritative/current-user documentation, at minimum:

```text
docs/specs/training_data/mlff_post_selection_p5_spec.md
docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md
docs/specs/training_data/mlff_p7_post_production_qualification_spec.md
docs/guides/mlff_campaign_cli_user_guide.md
current MLFF architecture manual chapter source(s)
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

## 20. Implementation stages

### Stage A — subordinate product schema/resolver

Implement immutable materialized-product record + current resolver/pointer.

Acceptance:

- record binds exact decision/member digest;
- record carries existing evaluated-state, architecture and full-state identities plus model SHA;
- canonical artifact path is immutable/versioned, not seed-only mutable;
- wrong/stale decision rejected;
- ordered member set preserved;
- multi-member committees supported;
- no selection/ranking logic introduced.

### Stage B — selected checkpoint -> full model materialization

Use existing authenticated provider/reconstruction owner.

Acceptance:

- nonterminal selected checkpoint can be materialized;
- reloadable full MACE model produced;
- selected state/head/architecture equivalence verified;
- native MACE reconstruction uses `allow_forward_override=False`; synthetic parameter-shell/test forward seams cannot become published products;
- published/reloaded model is portable CPU e3nn at accepted dtype and recursively in inference/eval mode;
- no terminal-model copy path.

### Stage C — integrate `train-production`

A size is complete only after product materialization.

Acceptance:

- normal fresh run publishes products;
- failure to materialize prevents COMPLETE;
- output prints usable paths;
- no cross-size choice.

### Stage D — existing-campaign reclosure and recovery classification

Implement the `PRODUCT_COMPLETE / PRODUCT_RECLOSURE / PRODUCTION_REQUIRED` classification before expensive production execution, plus the narrow decision-candidate replay seam that can repair a stale predecessor-reclosure record without weakening the strict public P5 resolver.

Acceptance:

- current old decision + missing model -> publication-only materialization;
- zero TRAIN2 jobs;
- zero EVAL2 for PRODUCT_RECLOSURE;
- mixed-size collections send only PRODUCTION_REQUIRED trajectories into the existing global TRAIN wave;
- repeated invocation verifies/reuses exact current bytes;
- corrupted/missing current product fails consumers closed but `train-production` can create a new immutable successor product without TRAIN2/EVAL2 or in-place overwrite;
- uncommitted pickle residue is never deserialized without an authenticated record.

### Stage E — observational lifecycle/status

Acceptance:

- new model-publication pointer participates in the shared coherent CampaignStore snapshot;
- decision-only legacy/current state reports reclosure needed;
- complete product state reports model paths;
- missing/wrong-kind product is not COMPLETE;
- forced publication/status races never yield a hybrid decision/model ancestry;
- status is byte/side-effect neutral;
- multi-size reports every N independently.

### Stage F — P7 intake reconciliation

Acceptance:

- P7 resolves the exact current model-publication record separately from the unchanged scientific qualification binding;
- `QualificationInputBinding` / `attempt_identity` do not change for representation-only successors;
- `deployment_parity` and `dynamics` input identities include current model-artifact-set identity and are recomputed when it changes;
- checkpoint-only physical/relaxation/calibration/locked evidence remains reusable when its own inputs are unchanged;
- irreversible locked activation/reveal history is preserved and never reopened;
- terminal/release v2 currentness binds the current model-artifact-set digest; historical v1 records remain readable but are not promoted across the changed executable binding;
- checkpoint-based `member_provider` remains the independent reference path;
- deployment exporter source changes from raw checkpoint path to authenticated P5 full model path;
- product SHA is authenticated before executable model deserialization with no hash/reopen race;
- exporter source artifact/state digests match the P5 product record;
- disk admission accounts for model/deployment scratch size;
- member order unchanged;
- wrong/mutated product fails before downstream execution;
- a deliberately corrupted serialized model is detected even when the source checkpoint still authenticates.

### Stage G — lightweight MH-1 audit/regression

Acceptance:

- no obvious MPA-0-only assumption;
- current MH-1/head tests pass;
- bounded real model checks run if readily available;
- no long production qualification required.

### Stage H — storage/docs/assembled closure

Acceptance:

- current products protected;
- docs distinguish terminal trainer output from P5 product;
- full affected regression passes;
- publication + MH-1 compatibility changes assessed together.

## 21. Required acceptance cases

| Case | Required result |
|---|---|
| selected checkpoint == final epoch | published model matches selected checkpoint |
| selected checkpoint != final epoch | published model matches selected earlier checkpoint, never trainer terminal model |
| EMA-selected representative | exact accepted provider state serialized |
| transient CuEq TRAIN2 | portable accepted model serialized |
| single-best committee | exactly selected member product |
| all-qualified committee | every published member product |
| multi-size | independent products for every N |
| legacy/current decision with no model | publication-only reclosure |
| repeat reclosure | no retraining and no rewrite when valid |
| partial write/interruption | not observable as current; restart repairs |
| wrong existing model bytes | fail closed |
| wrong decision/member binding | fail closed |
| missing selected checkpoint | fail closed |
| status | observational and reports product path |
| P7 reference/deployment split | checkpoint provider remains reference; deployment consumes exact P5 model publication |
| MH-1 explicit `omat_pbe` | preserved through current path |
| MH-1 omitted/invalid head | fail closed |
| MPA-0 regression | remains supported with `default` head |
| same N/seed, successor publication | immutable new model path; historical product not overwritten |
| crash after file placement before record | uncommitted residue recoverable under owner lock |
| source-tree change stales predecessor reclosure | decision replay reclosure succeeds with zero TRAIN2/EVAL2 |
| same checkpoint/state, different serialized model bytes | same P7 attempt; deployment_parity/dynamics stale, checkpoint-only and locked evidence reusable; new terminal binds new model-artifact-set |
| tampered/symlink product | rejected before `torch.load` |
| model pointer/status publication race | one coherent before/intermediate/after snapshot, never hybrid |
| P7 disk admission | accounts for published model + deployment scratch |
| concurrent same-member publication | stable decision/member lock serializes non-deterministic Torch saves; exactly one logical product is adopted |
| crash leaves uncommitted model pickle | residue is removed/rebuilt without deserializing untrusted/unreceipted pickle |
| current product bytes missing/corrupt | consumers fail closed; train-production creates immutable successor from same authenticated checkpoint |
| projection publication race | older publisher cannot overwrite `publication.json` after newer pointer commit |
| pre-change P7 release evidence | remains historical under new executable; locked reveal remains consumed; no compatibility laundering |
| published model object mode | CPU portable e3nn, accepted dtype, eval/inference mode before and after reload |
| MH-1 post-selection head layout | exactly `[pt_head, target_head]`; existing target-head index-1 deployment contract remains valid |
| locked already revealed, representation-only successor | reveal remains consumed; no reactivation; reuse locked evidence and rerun deployment-dependent components only |
| interrupted locked activation, representation-only successor | resume same activation; never create a fresh locked event |
| historical P7 v1 terminal/release record | readable historical evidence; not current until v2 terminal reduction binds current model-artifact-set |
| canonical product locator | derived only from parent/member/model identities; no subordinate-record self-digest cycle |
| bounded inference override | cannot source a production published `.model` |
| mixed PRODUCT_RECLOSURE + PRODUCTION_REQUIRED | global TRAIN wave remains isolated; serial publication/reclosure occurs post-TRAIN with accelerator retirement |

## 22. Real-owner integration

At least one bounded real-owner publication test must make:

```text
selected checkpoint != terminal checkpoint
```

and prove that the published full model follows the selected representative.

Use real current checkpoint/provider/model serialization owners. A toy `torch.nn.Linear`-only test is insufficient for this claim.

For MH-1, lightweight source/provider/head tests are sufficient for this cycle. A full real TRAIN2 campaign is deliberately not required.

## 23. Affected regression

Run the current affected suites spanning:

```text
P5 production/restart
publication decision/currentness
checkpoint authentication/provider reconstruction
multi-size integration
campaign lifecycle/status coherence
P7 publication/provider/deployment intake
P7 selective component invalidation and locked one-shot preservation
P7 terminal/release v1->v2 historical readability/currentness without cross-executable evidence promotion
storage owner/protection
MH-1 foundation/head/selected-head tests
generic MACE execution/CuEq parity tests
publication-lock concurrency/crash-residue/projection-race tests
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
25. Uncommitted full-model pickle residue is deserialized without an authenticated receipt/record.
26. An older publisher can overwrite the convenience `publication.json` after a newer model publication becomes authoritative.
27. Historical P7 evidence from an older executable is promoted to current by weakening executable currentness or compatibility-shimming a locked result.
28. Product serialization preserves tensor state but leaves the module in training mode.
29. MH-1 lightweight coverage fails to prove the canonical two-head `[pt_head, target_head]` post-selection layout needed by the existing ML-IAP target-head index contract.

## 25. D3 reopen triggers

Reopen rather than patch D4 if evidence shows:

- existing authenticated provider cannot expose the exact selected portable state;
- full-model serialization necessarily changes target-head/precision/scientific semantics;
- a subordinate product record cannot be bound acyclically to current P5 publication;
- `CampaignPaths.models` cannot safely remain the durable product owner;
- P7 fundamentally requires a product representation incompatible with P5's accepted portable model;
- current MH-1 support requires a different scientific/numerical fine-tuning method rather than an implementation correction.

Otherwise local serialization helpers, exact basenames, temporary-file mechanics, and bounded smoke-fixture choices remain D4.

## 26. Completion criteria

Ready for independent implementation Review when:

```text
P5 decision
  -> exact selected representative checkpoint(s)
  -> authenticated full .model product(s)
  -> direct operator locator
  -> P7 authenticated consumption
```

is complete and restart-safe, and the current MH-1 path has passed the bounded compatibility audit/regression with no clear unresolved issue.

Long real MH-1 campaign qualification remains intentionally deferred to the stakeholder's actual upcoming campaign.


## 27. Current-implementation review closure (Revision 2)

Review basis: `237448b449b6f8042de5f239e5fefdfd54e3b2c3`.

### R2-F1 — Decision schema must not absorb serialized artifact identity — CLOSED

Current `FinalProductionPublicationDecision` v3 already owns the pre-qualification scientific/member decision, and `resolve_current_final_production_publication()` replays that decision exactly. Embedding the later serialized `.model` into this object would conflate selection with representation and make legacy reclosure awkward. Revision 2 freezes the subordinate-record design instead.

### R2-F2 — Fresh publication pointer ordering was under-specified — CLOSED

Current `publish_final_production_publication()` stores the decision/reclosure and publishes the final pointer before any full selected model exists. Revision 2 now requires the final-publication pointer to be the last current-pointer commit for fresh publication, after model materialization and subordinate product pointer publication.

### R2-F3 — Existing-campaign reclosure needed an explicit pre-EVAL fast path — CLOSED

Current `execute_current_train_production()` ordinarily plans the whole collection and later calls serial `_finalize_final_production()`. Merely saying “zero unnecessary EVAL2” did not identify the owning control-flow change. Revision 2 adds the explicit three-state recovery classification before new TRAIN/EVAL admission.

### R2-F4 — P7 full-model consumption could destroy the deployment-parity oracle — CLOSED

Current P7 `member_provider` authenticates/reconstructs the selected checkpoint, while deployment currently sources `checkpoint_path_for_member()`. Revision 1 said broadly that P7 should consume the full model; that was too coarse. Revision 2 keeps the checkpoint provider as the independent reference and changes only deployment-export source to the P5 full model.

### R2-F5 — Proposed new “portable model-state digest” would duplicate current owners — CLOSED / STRENGTHENED IN R3

Revision 2 correctly rejected inventing a new tensor identity, but its wording missed two existing owners. Current provider authentication already returns an `evaluated_model_state_digest`, and the deployment owner already computes an exact full-`state_dict` SHA over names/dtypes/shapes/bytes. Revision 3 requires reuse/refactoring of those existing identities rather than either omitting full-state identity or defining a third digest.

### R2-F6 — Product path trust/relocation rules were incomplete — CLOSED

Revision 2 now requires model-root-relative paths, confinement beneath `CampaignPaths.models`, regular non-symlink files, and no absolute/`..` traversal. Absolute workspace paths remain outside durable identity.

### R2-F7 — Status integrity cost needed a bounded rule — CLOSED

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

**PASS AS WORKPLAN / D3->D4 HANDOFF READY AFTER FOURTH REVIEW.**

No Serious Challenge to D1/D2 is active.

The final design now distinguishes four independent identities correctly:

```text
P5 scientific member identity
    FinalProductionPublicationDecision/member_digest

P5 serialized deployment-source identity
    FinalProductionModelPublication/model_artifact_set_digest

P7 scientific qualification binding
    checkpoint product + executable/environment/spec/evidence roles

P7 deployment-dependent component identity
    scientific binding + exact current model_artifact_set
```

A model-byte change under one unchanged qualification binding re-executes only deployment-dependent evidence. A source-code/executable change follows existing P7 currentness and makes older qualification evidence historical; locked reveal history still cannot be reset.

The implementation must preserve the accepted global TRAIN scheduler, exact P5 selection science, one-shot P7 locked semantics, and the lightweight-only MH-1 evidence boundary.
