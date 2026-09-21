---
kind: implementation-workplan
workplan_id: MLFF-FINAL-PRODUCTION-MODEL-PUBLICATION-MH1-INTEGRATION
protocol_version: 6.4.0
status: active-reviewed
created_date: 2026-09-21
revision: 2
reviewed_date: 2026-09-21
workplan_review_status: pass-after-current-implementation-review
branch: design/mlff-final-production-model-publication-mh1-integration
basis_commit: 237448b449b6f8042de5f239e5fefdfd54e3b2c3
highest_affected_domain: D3
d1_d2_change: false
production_gpu_qualification: deferred-to-actual-campaign-and-final-release
---

# MLFF final-production model publication + lightweight MH-1 integration — D3 -> D4 workplan

## 0. Disposition

**PASS AS IMPLEMENTATION WORKPLAN AFTER CURRENT-IMPLEMENTATION REVIEW / FROZEN FOR D4. No Serious Challenge is active.**

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
    model_relative_path
    model_sha256
    evaluation_model_state (live/EMA as already owned by the trajectory/runtime)
    model_execution_architecture_digest (existing canonical architecture owner)
    model_relative_path (relative to CampaignPaths.models)
    model_sha256
serialization/exporter identity
```

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

Use a human-readable generation/size/member layout, e.g.:

```text
models/
  production/
    g<generation>/
      N_<size>/
        seed-<seed>.model
        publication.json
```

For an all-qualified committee every published member gets its own model.

Exact punctuation/basenames are delegated D4, but the operator must be able to identify generation, selected N, and member without decoding run hashes.

Durable model paths MUST be relative to `CampaignPaths.models`. Reject absolute paths, `..` traversal, symlink substitution, wrong-kind nodes, or any path that escapes the campaign model root. Workspace relocation must not change scientific/product identity.

The sibling `publication.json` is an operator-facing projection of the canonical P5 records. It MUST NOT become a second currentness or selection authority and may be rebuilt from authenticated owner state.

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

Do not silently change precision during base P5 publication.

Deployment/dtype conversion remains downstream P7/deployment ownership.

## 8. Publication atomicity and restart

### D3-4 — Create-or-verify

For each expected product path:

- absence -> materialize;
- valid matching existing product -> reuse;
- existing but mismatched/unverifiable product -> fail closed.

File existence alone is never validity.

At minimum authenticate:

```text
decision digest
member digest
member identity
representative checkpoint SHA
evaluation model state (existing live/EMA authority)
target head
existing canonical execution-architecture digest
serialized model SHA
```

Do not invent a second persistent canonical tensor/state digest merely for this feature. The source checkpoint/runtime already own exact numerical-state authentication. During materialization, compare the reconstructed provider model to the post-save reloaded model through exact state-key/shape/dtype/value equivalence (or an already-existing canonical state-hash owner if one is directly reusable); persist only identities that already have a current owner plus the serialized product SHA.

### D3-5 — Crash-safe publication

Use run-owned temporary output, validate/reload, then atomically place the product and subordinate record where supported.

The P5 publication barrier already coordinates object/current-pointer publication against storage mutation. Integrate model-record publication with the same ownership/barrier semantics rather than adding an independent lock domain.

A crash must never make a partial model appear current.

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
- A mixed collection may reclose/verify completed sizes while only `PRODUCTION_REQUIRED` positions enter the existing TRAIN wave. This must not create a second scheduler or change frozen-size finalization order for genuinely new work.

This is the required mechanism behind the “zero unnecessary EVAL2” acceptance claim.

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
```

all agree.

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

## 12. P7 consumption and independence

P7 remains downstream and cannot alter P5 membership.

Current P7 has two materially different consumers and they must remain independent:

1. `member_provider(...)` reconstructs the selected representative from the authenticated TRAIN2 checkpoint. **Keep this checkpoint-based reference path.** It is the independent in-framework reference used to detect serialization/deployment drift.
2. `_build_deployment_artifact(...)` currently passes `checkpoint_path_for_member(...)` into the MACE deployment exporter even though the exporter contract is a full MACE model path. **Change this deployment-source path to the authenticated P5 full `.model`.**

Therefore the target architecture is:

```text
selected checkpoint
   -> existing authenticated member_provider
   -> reference predictions

same selected checkpoint
   -> P5 full .model publication
   -> P7 deployment exporter
   -> deployed/ML-IAP artifact

reference predictions <-> deployed predictions
```

This preserves a discriminating deployment-parity oracle. Do not make `member_provider` load the same serialized `.model` used by deployment, because a serialization defect could then become common-mode and escape parity testing.

The P7 read-only publication view may be extended with subordinate product path/SHA fields, but its member ordering and decision/member digest must still reproduce the existing P5 decision exactly.

Before deployment, verify:

```text
exact current decision
exact member/member order
exact representative checkpoint ancestry
exact target head
confined regular P5 model path
exact P5 model SHA
```

Do not duplicate P5 selection logic inside P7.

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
- P5 foundation-provider/model-construction smoke.

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
- no terminal-model copy path.

### Stage C — integrate `train-production`

A size is complete only after product materialization.

Acceptance:

- normal fresh run publishes products;
- failure to materialize prevents COMPLETE;
- output prints usable paths;
- no cross-size choice.

### Stage D — existing-campaign reclosure and recovery classification

Implement the `PRODUCT_COMPLETE / PRODUCT_RECLOSURE / PRODUCTION_REQUIRED` classification before expensive production execution.

Acceptance:

- current old decision + missing model -> publication-only materialization;
- zero TRAIN2 jobs;
- zero EVAL2 for PRODUCT_RECLOSURE;
- mixed-size collections send only PRODUCTION_REQUIRED trajectories into the existing global TRAIN wave;
- repeated invocation verifies/reuses;
- corrupted existing product fails closed.

### Stage E — observational lifecycle/status

Acceptance:

- decision-only legacy/current state reports reclosure needed;
- complete product state reports model paths;
- status is byte/side-effect neutral;
- multi-size reports every N independently.

### Stage F — P7 intake reconciliation

Acceptance:

- P7 resolves exact product record;
- checkpoint-based `member_provider` remains the independent reference path;
- deployment exporter source changes from raw checkpoint path to authenticated P5 full model path;
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
storage owner/protection
MH-1 foundation/head/selected-head tests
generic MACE execution/CuEq parity tests
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

### R2-F5 — Proposed persistent “portable model-state digest” lacked a current owner — CLOSED

Current code has canonical execution-architecture identity and authenticated TRAIN2 live/EMA/checkpoint state ownership, but no need was established for another durable tensor-state identity. Revision 2 removes that invention: publication persists existing state/architecture lineage plus model-file SHA, while materialization acceptance proves exact pre/post serialization state equivalence.

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
