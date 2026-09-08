---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-IMPLEMENTATION-REVIEW-REOPEN
parent_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING-FINAL-CONVERGENCE
root_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING
protocol_version: 5.14.0
status: active
created_date: 2026-09-04
branch: plan/mlff-storage-io-reset-r37-review-closure
reviewed_head: 919f848d7f301c50c9341c45106dd862239e165d
reviewed_executable_head: 60edb67bb05a49560b2e0201ab2ab940a867b236
verdict: NO-PASS / IMPLEMENTATION-REOPENED
scope: independent implementation review closure for immutable-publication verification, prepare source/currentness/idempotence, observation integrity/coherence, direct-inference evidence semantics, and assembled P7 acceptance
precedence: this amendment does not redesign frozen science or high-level architecture; it records implementation nonconformance and bounded acceptance corrections discovered by independent review. Every non-conflicting root, R2, final-convergence, active P4, P5/P7, and Storage R38 requirement remains binding.
---

# MLFF assembled integration — implementation review reopen

## 0. Independent review verdict

**NO-PASS / IMPLEMENTATION-REOPENED.**

The implementation at executable commit `60edb67bb05a49560b2e0201ab2ab940a867b236` contains substantial correct work against the composed integration authority. In particular, it establishes a durable prepared-generation loader, generation-safe content-bound normalized frame representation, bounded direct inference through the real P3 owner, strict first-boundary/later-boundary restart semantics, stale-P3 CAS rejection, read-only status capability, P7 presence in the public lifecycle, and conservative owner-driven storage retention.

Those gains are retained. This review does **not** reopen the target-size scientific question, P1/P2/P3 algorithms, P5 science, P7 qualification science, CampaignStore-as-current-authority, or Storage Revision 38's destructive architecture.

Independent source review nevertheless found blocking implementation nonconformances at Frozen owner boundaries. They are not justified away by the affected-suite baseline having the same failing-test set, because the composed workplan explicitly requires these behaviors on the final assembled candidate. A pre-existing defect that violates a newly composed acceptance boundary still blocks closure when that boundary is part of the product being accepted.

The repair strategy is deliberately reductive:

- strengthen existing immutable publishers to create-or-verify rather than adding registries;
- correct `prepare` admission/currentness rather than adding downstream fallbacks;
- use one existing SQLite snapshot and typed owner reads rather than adding lifecycle state;
- remove/redefine one stale P3 evidence field rather than adding chunk provenance machinery;
- correct the bounded P7 test model rather than weakening production qualification.

No new workflow engine, freshness database, checkpoint registry, reference-count database, second frame cache, status registry, batch policy, or storage mutation path is authorized by this reopen.

---

## 1. Global invariant analysis

The original product problem remains:

```text
prepare freezes one exact scientific generation once
 -> downstream P3/P5/P7 consume that frozen generation
 -> restart/currentness is exact and fail-closed
 -> scientific population is independent of execution batching
 -> observation is truthful and non-mutating
 -> storage preserves owner capability without becoming scientific authority
 -> the public lifecycle continues through qualification
```

The blocking findings below matter because they violate the Frozen high-level architecture, not because a helper or test happens to be inconvenient.

### Frozen architecture still controlling this review

1. `CampaignStore` is the sole mutable current-generation/lifecycle authority.
2. Durable stage publication is `construct -> publish immutable object(s) -> verify -> CAS/pointer/store adoption`.
3. `prepare` is the sole upstream construction/advance boundary for the prepared target-size substrate.
4. Downstream commands consume the adopted immutable prepared generation without live-source reconstruction.
5. Future construction may not damage current-generation dependencies before adoption.
6. Competing/stale writers lose at the commit-time currentness boundary; long numerical work is not protected by a coarse global lock.
7. Observation is read-only **and** integrity/coherency aware; cheap does not mean unauthenticated.
8. Scientific population (`M`, `T_N`, folds, cohorts) is distinct from execution partition (`valid_batch_size`, chunks, workers).
9. Storage remains owner-driven and conservative; unsupported cold transformation is a legitimate no-op, not a reason to invent archive capability.
10. P7 qualification science and one-shot locked disclosure remain as previously accepted; the integration fixture must be capable of exercising their passing path honestly.

---

## 2. Blocking findings

### IR1 — immutable prepared/frame publication reuses existing content identities without verifying their bytes before adoption

#### Evidence / concern

`campaign_prepared_generation._publish_bytes()` returns immediately when the content-addressed path already exists. `publish_prepared_generation()` then returns the expected manifest object and `prepare` may bind that digest into `CampaignStore`. The existing path is authenticated only later by a downstream reader.

The normalized frame publisher has the analogous weakness: when `entries/<identity>/arrays.json` exists, the newly staged entry is discarded and the old entry is reused. `finalize_frame_data_cache()` verifies the entry manifest hash but does not re-authenticate every NPY member that manifest names. A parseable/unchanged entry manifest can therefore coexist with a corrupt array member until downstream load.

This violates the Frozen publication boundary:

```text
construct -> publish -> VERIFY -> adopt
```

The content-addressed name proves what bytes *should* exist; it does not prove that existing on-disk bytes still match that identity.

#### Required repair

Alter the existing immutable publication primitives to **create-or-verify** semantics.

- If a prepared component/manifest path already exists, verify the exact expected bytes/hash and deserialize through the accepted owner before treating it as reusable.
- If a normalized frame entry already exists, authenticate its entry manifest **and every required member hash/shape/dtype** before reuse/finalization. Reuse the existing authenticated loader/member-validation logic rather than duplicating a validator.
- Conflicting/corrupt content must fail before `CampaignStore` adoption. Do not silently overwrite a current protected object merely to make the expected digest true.
- If an explicit `prepare` is later given a deliberately supported owner-local repair path, it may recreate exact expected immutable bytes only under the existing content owner and only when this cannot damage another protected generation. Do not add a recovery registry or alternate namespace.

#### Acceptance

Through the real prepare publisher/adopter:

1. preseed/corrupt an existing prepared component while leaving the expected content-addressed filename;
2. preseed/corrupt a prepared manifest at its expected identity;
3. corrupt one NPY member of an existing frame entry while leaving `arrays.json` unchanged;
4. run ordinary `prepare`;
5. prove the current campaign revision is not advanced/bound to unverified content;
6. prove the previously current valid generation remains usable where applicable.

A test that calls only the downstream loader after adoption does not establish this claim.

---

### IR2 — ordinary repeated `prepare` does not own changed-source detection/rebuild, and unchanged terminal `prepare` is not idempotent

#### Evidence / concern

`execute_current_prepare()` rebuilds DATA2-DATA5 only when `--rebuild-catalog` is supplied or `data5` is absent. Otherwise it invokes fresh P1 authentication using the already stored source catalog. If source/companion bytes changed after g1, ordinary `prepare` reaches stale catalog identity and fails instead of routing the change through the existing prepare-owned catalog rebuild path and publishing g2.

This leaves half of the intended generation semantics implemented:

- downstream g1 is correctly immutable against live source edits;
- but the **next explicit `prepare`**, which is the sole authorized place to detect those edits, does not convert a valid changed input set into a fresh prepared generation unless the operator supplies an implementation-specific rebuild flag.

A second idempotence defect occurs after target-size terminal state. With unchanged preparation inputs, `ensure_current_target_size_authorities()` correctly returns the same terminal revision, but `execute_current_prepare()` then sends that terminal revision through the nonterminal result-view writer, which rejects it. Derived result-view publishing turns a scientifically valid no-op into command failure.

#### Required repair

Keep both corrections inside the existing `prepare` owner.

1. Correct the reuse/admission decision before expensive reconstruction:
   - compare preparation-owned exact source/companion/catalog input identities using existing manifest/catalog/receipt identities;
   - unchanged inputs may reuse the existing lower-level catalog/prepared content;
   - materially changed valid inputs route through the **existing** `_prepare_catalog` reconstruction path, then normal prepared publication and generation CAS;
   - malformed/unapproved changed inputs still fail under their existing owners.
2. Do not add a freshness database, mtime authority, downstream source fallback, or new source registry.
3. For unchanged terminal generation, make result-view publication idempotent by using the existing terminal/current result-view owner or by preserving the already-correct terminal view as a no-op. Do not alter campaign scientific state merely to satisfy a derived file writer.

#### Acceptance

- g1 prepared; mutate one valid source/companion byte set; g1 downstream load still means exactly g1;
- run ordinary `prepare` **without** a rebuild-only escape flag; it reauthenticates/rebuilds through existing source owners and commits g2;
- unchanged run/frame members are reused by content identity where their source identity genuinely matches;
- terminal g1 + unchanged `prepare` succeeds, stays at the same generation/revision/terminal P3 evidence, and preserves a valid terminal result view;
- terminal g1 + changed preparation-scientific input produces a fresh nonterminal g2 rather than editing g1.

---

### IR3 — concurrent `prepare` adoption is not fenced to the revision under which the expensive build began

#### Evidence / concern

The final workplan requires two differing prepares to have one winner while the other rebases/retries at the owner boundary or fails cleanly. Current tests cover sequential repeated preparation and a synthetic generation transition, but they do not let two real expensive prepare attempts overlap through final adoption.

The current adoption API loads whatever campaign revision is current **at the moment adoption begins**. It is not passed the revision/expectation from which the expensive snapshot was constructed. Therefore this race remains possible:

```text
g1 current
A starts prepare under input set A and builds snapshot A
B builds snapshot B and adopts g2
A finishes later
A loads g2 at adoption time, sees different identity, and advances to g3 using stale snapshot A
```

That is last-finisher-wins, not stale-writer rejection/rebase.

#### Required repair

Alter the existing prepare/adoption boundary; do not serialize the whole build under the campaign writer lock.

- Capture the exact `TargetSizeCampaignRevision.expectation()` (or equivalent currentness token already owned by `CampaignStore`) before the expensive prepare construction whose result depends on it.
- Final adoption of that constructed snapshot must CAS against that starting expectation.
- On conflict, re-read current campaign/input identity and either:
  - converge/idempotently accept if the winner adopted the same exact prepared identity; or
  - re-evaluate/retry from current owner state when explicitly safe; or
  - fail cleanly and require a fresh prepare.
- A stale snapshot built against superseded inputs may not blindly advance the newer generation.

#### Acceptance

Use real two-writer synchronization barriers with real prepared publication and real CampaignStore adoption:

1. identical concurrent prepares -> same immutable content, at most one generation transition;
2. differing concurrent prepares -> one current winner; stale loser cannot overwrite/advance the winner without a fresh rebase decision;
3. interruption/loser residue remains unreachable and cannot damage current/previous protected generation dependencies;
4. no coarse campaign lock is held over long P1/P2 construction.

---

### IR4 — public lifecycle observation is non-mutating but not yet a coherent authenticated snapshot

#### Evidence / concern

The new lifecycle projection correctly avoids providers, DATA4 reconstruction, write-capable stores, and directory creation. That satisfies the **capability** half of the observation invariant.

Two correctness gaps remain.

**Coherence:** `_meta()` opens a fresh SQLite connection for each descendant pointer read. `project_campaign_lifecycle()` rechecks only the target-size `state_revision` after reading P5/P7 rows. P5/P7 pointer publications mutate `meta` rows without changing that target-size revision. A concurrent writer can therefore make one response combine a pre-publication P5 view with a post-publication P7 view while the target revision remains unchanged. The returned ancestry may never have existed atomically.

**Integrity:** the compact `_read_object()` helper only `json.loads()` the path named by a content digest. It does not verify that the parseable object reproduces that digest/typed owner identity before interpreting fields such as `accepted` or `verdict`. Parseable corruption can therefore be reported as a valid CV acceptance or terminal qualification state instead of `BLOCKED`.

Cheap observation is allowed to skip full model/source reauthentication; it is not allowed to trust unauthenticated mutable bytes.

#### Required repair

Reduce the projection onto existing owner primitives.

1. Take one SQLite read transaction/snapshot for the target revision plus every P5/P7 pointer/meta row needed for one lifecycle answer. Do not add a lifecycle revision counter or snapshot table.
2. Capture the exact pointer digests in that DB snapshot, then authenticate those exact small immutable objects through existing read-only typed stores (`PostSelectionEvidenceStore.get`, `QualificationEvidenceStore.get`, or equivalently narrow digest-validating readers with `create=False`).
3. Missing, malformed, or digest-inconsistent referenced objects map to the existing typed `BLOCKED` observation state.
4. Do not construct `CurrentSelectedTrainingContext`, `QualificationSession`, providers, wrappers, reference bundles, prepared arrays, or write-capable evidence roots merely to report status.
5. `advance` remains advisory routing only; the selected consequential command still performs full admission/currentness validation.

#### Acceptance

Race real status projection with barriers around:

- prepare adoption;
- P5 pointer publication;
- P7 pointer publication.

Every answer must correspond to a valid all-before or all-after owner graph, never a hybrid.

Also exercise pointer -> missing object, malformed JSON, and parseable-but-content-digest-invalid object for both P5 and P7; each must report `BLOCKED` without changing any managed byte or DB row.

---

### IR5 — durable P3 prediction evidence still conflates scientific population `M` with execution batch size

#### Evidence / concern

The runtime defect that caused CUDA OOM is correctly repaired at execution: `run_target_size_direct_boundary_inference()` now partitions the exact ordered M-frame population using `valid_batch_size` before native device materialization.

But the durable `TargetSizePredictionEvidence` is still constructed with:

```text
evaluation_size = M
batch_size       = len(atoms_list) = M
```

and replay currently requires `prediction.batch_size == eval_data.evaluation_size`.

Thus the persisted/replayed evidence still claims that the full scientific population is the batch, even when the real device forwards were smaller. This is exactly the conceptual conflation the Frozen architecture was introduced to remove.

#### Required repair

Prefer deletion/narrowing over adding new provenance.

- `evaluation_size` remains the exact scientific `M`.
- Stop using `batch_size` to mean `M` in current V7 prediction evidence.
- Preferred if compatibility permits: remove the redundant legacy field from the current schema/evidence contract and derive the deterministic execution partition from already-authenticated execution policy (`valid_batch_size`) plus `M`.
- Otherwise redefine the field precisely as the accepted maximum execution batch width and update replay/validation accordingly.
- Do **not** add per-chunk size arrays, a second evaluation-batch policy, auto-tuning state, or another provenance registry unless real evidence proves the deterministic `M + valid_batch_size` representation insufficient.
- Preserve exact role/membership/order/model/device/dtype/backend identities and tolerance-appropriate floating equivalence.

#### Acceptance

For `M > valid_batch_size`:

- real owner forwards obey the bound;
- durable evidence does not claim `batch_size == M` as execution provenance;
- restart/replay authenticates the same deterministic partition policy;
- changing `valid_batch_size` changes the P3 execution context/evidence currentness but not prepared P1/P2 science;
- no old full-batch shortcut becomes current V7 authority.

---

### IR6 — the required P7 assembled passing path is blocked by a non-conservative bounded test potential, not by production qualification

#### Evidence / concern

The final assembled lifecycle and R2 locked-history acceptance require:

```text
qualification run -> waiting_for_reference
 -> authenticated reference supplied
 -> nonlocked qualification succeeds
 -> explicit locked activation
 -> terminal release verdict
 -> generation/storage transition preserves irreversible reveal history
```

The current bounded P7 fixture cannot reach the passing relaxation path. Its analytic pair term is conservative, but `attach_labels()` then adds a per-frame constant **force** offset while adding only a constant **energy** offset. The resulting energy and force no longer derive from one potential-energy surface; translational/net-force modes can have no reachable stationary point. Production `relax_fixed_cell()` correctly runs ASE FIRE and truthfully rejects nonconvergence.

Increasing step budget or weakening the force threshold would manufacture a pass and would violate the test's own premise that it supplies a genuine PES with a reachable minimum.

#### Required repair

Repair only the bounded numerical fixture below the already accepted P7 owner boundary.

- Replace the force-offset construction with one analytically conservative potential whose reported energy and force are derivatives of the same expression and which has a reachable minimum near the canonical/reference geometry used by the passing fixture.
- A simple harmonic/tethered reference construction is preferable to layering additional correction terms if it exercises the same production relaxation mathematics with less fixture machinery.
- If a linear energy term is used to represent a constant force shift, prove the resulting constrained/free modes still possess the intended minimum; do not merely make energy bookkeeping syntactically consistent.
- Do not change FIRE, scientific thresholds, required components, locked semantics, or production qualification code to accommodate the fixture.

#### Acceptance

Re-run the real P7 owners through:

1. waiting-for-reference;
2. authenticated reference supply;
3. passing nonlocked deployment/PES/relaxation/dynamics/calibration as applicable;
4. explicit locked activation with confirmation;
5. terminal `RELEASE_QUALIFIED` or the accepted fixture terminal verdict;
6. close/reopen exact terminal reauthentication;
7. locked activation -> fresh generation -> applicable storage operations -> same/overlapping locked cohort remains historically revealed and cannot become fresh.

The fake remains below the numerical forward/deployment seams; it may not directly manufacture component verdicts.

---

## 3. Non-blocking clarifications from this review

### 3.1 Do not invent archive/restore support for prepared state merely to make the matrix non-empty

The R2 storage contract applies archive/verify/restore **where the owner declares the representation eligible/supported**. The current prepared-generation owner marks the current prepared root as restart-required and hot-path-required; the normalized frame cache is conservatively non-evictable because no liveness seam proves concurrent non-use.

Therefore a real archive plan that finds **no prepared/frame object eligible for cold replacement** is a valid owner result. Closure should prove that archive planning/execution refuses/no-ops those objects without mutating them and that downstream consumption still works. Do not create a prepared cold representation, fake archive candidate, or extra lifecycle state solely to satisfy a test matrix.

Archive verify/restore remains required for actual owner-eligible families affected by the final implementation.

### 3.2 Baseline failures require ownership triage, not blanket repair or blanket waiver

The recorded affected-suite baseline and final candidate have identical failing-test sets, while the candidate adds many passing integration tests. That is useful non-regression evidence.

It does **not** waive:

- any failure that exercises a composed acceptance requirement in this plan (notably P7 passing/locked lifecycle and terminal prepare idempotence);
- project-required checks whose missing fixture/specification is itself on the affected/documentation surface.

Conversely, do not repair unrelated pre-existing documentation/spec fixtures under this integration plan merely because they fail in the broad selection. For each persistent baseline failure, record whether it maps to an affected owner/INT-H/project-required final check. Only mapped failures block this plan.

### 3.3 Conservative whole-family frame/prepared retention is safe for this closure

The current storage owner conservatively retains the prepared root and frame-cache family. That may leave reclaimable historical bytes on disk, but it does not violate the core capability/safety invariant. Selective historical-member garbage collection is not required unless storage/product authority already requires it. Do not introduce reference counting or a new GC registry as an optimization during this repair.

---

## 4. Required repair sequence

### Stage R1 — close `prepare` ownership/publication/currentness as one coherent boundary

Implement IR1-IR3 plus terminal idempotence together because they are all consequences of one owner boundary:

```text
capture current expectation
 -> decide reuse/rebuild from exact prepare-owned inputs
 -> build/publish immutable prepared + frame content
 -> create-or-VERIFY every reused identity
 -> short CAS adoption against starting expectation
 -> publish correct derived result view
```

Required outcomes:

- changed source is handled by ordinary explicit `prepare` through existing source/catalog owners;
- unchanged terminal prepare is a successful no-op;
- existing immutable bytes are verified before reuse/adoption;
- concurrent stale prepare cannot last-writer-win over a newer generation.

Do not split these into independent wrappers around the current flow; simplifying the current prepare admission/adoption sequence is preferred.

### Stage R2 — repair durable execution semantics, not the bounded inference implementation

Implement IR5 by removing/redefining the stale `batch_size=M` evidence semantics and corresponding replay assertion. The existing `run_bounded_inference` owner remains the execution realization. No second batch policy.

### Stage R3 — make observation both coherent and authenticated

Implement IR4 using one DB read snapshot plus existing typed read-only P5/P7 object stores. Preserve all current no-create/no-provider/no-DATA4 tests and add race/corruption tests.

### Stage R4 — repair the P7 acceptance model and close the real lifecycle

Implement IR6 only in the bounded fixture/test model unless evidence shows a production defect. Then execute the full reference/nonlocked/locked/terminal/history path through real P7 owners.

### Stage R5 — exact-candidate final acceptance

After all executable changes:

- rerun each focused repair suite;
- rerun the full root/R2/final-convergence assembled lifecycle matrices;
- rerun Storage R38 applicable-operation/interleaving checks;
- rerun P3 first-boundary/continuation corruption and stale-writer matrices;
- rerun observation purity **and** coherence/integrity matrices;
- rerun bounded CPU inference and the existing real CUDA multi-chunk smoke where hardware is available;
- re-derive the affected surface and run affected regression/integration/project-required checks on the exact final candidate;
- compare persistent baseline failures by exact node ID/test and classify them by affected ownership rather than count alone;
- run the required structural/semantic checks for retired V5 authority absence and hidden full-population inference paths.

Long production-scale GPU/scientific qualification remains deferred to the established final-release phase; this review does not change that policy.

---

## 5. Closure criteria

This review amendment may close only when one exact candidate demonstrates all previously binding closure criteria plus:

1. Existing content-addressed prepared objects/manifests/frame members are authenticated before reuse/adoption; corrupted existing content cannot become current merely because its pathname exists.
2. Ordinary `prepare` detects valid changed source/companion identity and routes through the existing rebuild owner to a fresh generation without a special operator recovery flag.
3. Unchanged terminal `prepare` succeeds idempotently without altering terminal scientific state.
4. Two real concurrent prepares are CAS-safe from the revision they began from; a stale constructed snapshot cannot blindly supersede the winner.
5. One lifecycle projection uses a coherent CampaignStore snapshot spanning target state and P5/P7 pointers.
6. Compact P5/P7 records are content/owner authenticated before their fields affect status; parseable corruption is `BLOCKED`.
7. Current P3 durable evidence no longer records the exact-M scientific population as if it were one accelerator batch; replay authenticates the accepted execution partition semantics.
8. The bounded P7 fixture supplies a conservative reachable PES and the full nonlocked -> explicit locked -> terminal lifecycle passes through real owners.
9. Locked disclosure remains irreversible after generation advance and applicable storage operations.
10. Prepared/frame archive absence is accepted only when real owner policy says there is no cold-replaceable candidate; no new archive machinery is added to manufacture one.
11. No repair introduces a second currentness/freshness/cache/checkpoint/reference-count/batch-policy/storage authority.
12. Final affected regression and project-required checks are run on the exact executable candidate, with every persistent baseline failure mapped to affected ownership or explicitly excluded as unrelated evidence.

## 6. Review disposition

The implementation has moved materially toward the correct architecture and should be repaired in place. The correct strategy is not another patch stack around the product; it is to finish the ownership reductions already underway:

```text
verify before adopt
prepare owns source change and its own CAS
observation reads one authenticated snapshot
M is not batch size anywhere, including durable evidence
qualification fixture models a real PES
```

**Design remains PASS. Current implementation remains NO-PASS / reopened until the bounded items above close.**
