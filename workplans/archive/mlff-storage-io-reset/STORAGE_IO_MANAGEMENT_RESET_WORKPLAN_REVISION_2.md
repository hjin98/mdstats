---
kind: implementation-workplan
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 2
status: active
amended_date: 2026-09-01
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
parent_authority_rule: frozen parent remains the scientific and architectural verdict
entry_condition: satisfied by independent P6 revision 13 PASS and P7 revision 13.7 software/functional closure PASS
implementation_intake_commit: 45b85e5dfb98bed4abbfee47cdb020bb2bd401c8
implementation_intake_tree: 3efc6297c31c1d233a733ec792f0fba08aea10a1
accepted_p7_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
accepted_p7_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
compatibility_policy: current-generation-owner-driven; retired STOR1-STOR5 semantic policy is historical and is not migrated into current authority
supersedes_substantive_workplan: STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md
---

# MLFF campaign storage and I/O management reset — revision 2

## 0. Authority, baseline, and disposition

The frozen parent target-size V7 workplan remains the sole scientific and architecture verdict. This storage successor may change storage representation, retention, cleanup, caching, deduplication, archival, recovery, admission, and I/O execution mechanics only while preserving all accepted P1-P7 scientific/currentness semantics.

The predecessor gate is now satisfied:

- P6 revision 13 is independently completed/PASS;
- P7 revision 13.7 is closed/PASS for software implementation and functional acceptance;
- actual real-campaign external-DFT scientific qualification and long production GPU/resource qualification remain deferred exactly as the parent and P7 revision 13.7 require and **do not block this storage workplan**.

Implementation intake is bound to merged `main` commit `45b85e5dfb98bed4abbfee47cdb020bb2bd401c8`, tree `3efc6297c31c1d233a733ec792f0fba08aea10a1`. The accepted P7 executable source is commit `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`; the intervening merged commits are P7 authority/evidence/workplan changes rather than executable product changes.

This revision is **active / implementation-ready**. It supersedes the original substantive storage workplan and all earlier storage authority revisions for current task-local semantics. Historical files remain provenance only.

## 1. Objective and protected product outcome

Renew the MLFF campaign storage subsystem around the accepted current P1-P7 semantic owners instead of the retired STOR1-STOR5 lifecycle topology.

The durable product flow is:

```text
P1-P7 semantic owners
  -> authenticated owner storage views
  -> cross-owner inventory snapshot
  -> storage policy + resource admission
  -> immutable owner-bound StoragePlan
  -> immediate owner/currentness/lease/filesystem revalidation
  -> safe cleanup / cache eviction / dedup / archive / restore
  -> bounded audit evidence
  -> restart-equivalent current product
```

Protected concerns:

- storage is never a second authority for scientific identity, target membership, selected size, CV acceptance, representative checkpoint/member choice, final publication membership, qualification component outcome, locked activation, or release verdict;
- external source/replay/reference/DFT inputs are non-destructible regardless of path, symlink, configuration, or record references;
- current, restartable, in-flight, publish-before-adopt, or otherwise owner-protected evidence is never deleted because a pointer is absent, a PID disappeared, a pathname looks stale, or advisory accounting labels it reclaimable;
- retired `workspace/runs`, `active_process.json`, PID/age/pathname rules, old `evaluate`/`verify` stages, DATA7/DATA8 stage folklore, SELECT2, and STOR1-STOR5 policy never regain destructive authority;
- cache/index eviction changes only recomputation/performance and never scientific meaning or restart authorization;
- durable scientific/release evidence remains authenticatable after cleanup, archive, restore, close/reopen, and fresh process restart;
- storage bytes, inodes, scratch, metadata operations, and I/O bandwidth are first-class resources;
- restart/cold-load cost is optimized together with steady-state throughput;
- the renewed subsystem minimizes total product complexity by reusing current owner APIs and existing retention/publication locks rather than creating parallel registries or state machines.

## 2. Reconciliation findings against implemented P1-P7

This section is current-state authority for the successor. It records implementation consequences that were not fully knowable when revision 1 was written.

### F1 — predecessor gate and acceptance-layer drift

The old storage authority stopped at P6 revision 13 / P7 revision 9 and described a P7 publication/qualification PASS gate. P7 later reached revision 13.7 and explicitly corrected acceptance drift: external DFT and long real-production qualification are deferred release activities, not software-package closure prerequisites.

**Required correction:** storage entry is based on P6 revision 13 PASS plus P7 revision 13.7 software/functional closure PASS. Storage implementation must never reintroduce external DFT or a pre-existing operator campaign as its own entry gate.

### F2 — S0 owner census omitted P2

P2 now owns persistent/restart-authenticated target-size statistical authorities: resolved policy, `U_size`, `P_train/M3`, `pi_train`, `pi_eval`, `M1/M2/M3`, exact `T_N`, qualification state, and reducer definition/state. These are distinct from P3 execution evidence.

**Required correction:** P2 is an explicit storage owner/consumer surface. Storage may archive/report its evidence only through P2 semantics and must not infer P2 currentness from P3 files or paths.

### F3 — P4/P3 already provide a real publication-race retention owner

P4 implemented CampaignStore adoption of authenticated immutable P3 heads and `build_target_size_retention_fence(...)`. The fence protects the publish-before-adopt window from the filesystem evidence graph and is already threaded through the common campaign ownership boundary.

**Required correction:** this mechanism is accepted current owner functionality to reuse and consolidate. Do not replace it with a central pathname registry, CampaignStore-only pointer test, or a second P3 reachability algorithm.

### F4 — current P5 is a distinct restart/evidence owner, but not a proven cache-eviction owner

P5 current evidence lives under its current post-selection owner and authenticates CV/final-production lineage, run evidence, checkpoints/materializations, replay/foundation identity, and restart/currentness. P6 deliberately refused to invent a positive cache-deletion contract for P5 simply from path names.

**Required correction:** the successor may enable P5 cache/reproducibility reclamation only when the real P5 owner exposes or can cleanly provide exact reconstructibility/immutability/currentness semantics. If an artifact cannot be positively classified without synthetic ownership, retain it. A `cache` action is allowed to be a no-op for such families.

### F5 — P7 now has a concrete canonical storage owner

P7 durable persistence is rooted at `.mdstats/qualification/g<generation>` and exposes one owner API around:

- immutable content-addressed `objects/` release evidence;
- attempt-scoped state/scratch under `attempts/`;
- CampaignStore current pointers that are locators/fences rather than a second scientific truth;
- create-once/validate-existing object publication;
- `QualificationAttemptState` and referenced-path retention;
- `build_qualification_retention_fence(...)`.

The P7 fence protects durable release evidence outright and protects active-attempt dependencies; terminal/aborted attempts do not keep ordinary attempt scratch pinned forever.

**Required correction:** consume this real owner. Do not create a parallel qualification registry, duplicate qualification currentness, or blanket-retain every qualification attempt directory indefinitely.

### F6 — current deletion boundary already composes lifecycle fences

`CampaignOwnershipBoundary` already enforces workspace containment, protected external inputs, symlink non-traversal, and a retention fence that can only reduce deletion authority. `_campaign_ownership_boundary(...)` composes the P3 and P7 fences through `CompositeRetentionFence`.

**Required correction:** preserve this safety boundary or cleanly refactor it into the new planner/executor; do not introduce a second independent destructive path. Owner views determine semantic eligibility, while the physical ownership boundary remains a final mandatory mutation guard.

### F7 — SHA receipt accounting is semantically misclassified today

P6 established the SHA-256 receipt store as an acceleration cache that safe/cache cleanup must not prune. Current accounting still groups `hash-receipts.sqlite3` with CampaignStore state/provenance in places, while the accepted successor design classifies receipts as reusable cache/index state.

**Required correction:** split receipt-cache accounting/ownership from authoritative CampaignStore state. Receipt loss/corruption/eviction must only cause rehash/revalidation. Receipt values may accelerate report/dedup/archive/restore but never establish validity without the receipt owner's checks.

### F8 — P7 waiting-for-reference lineage is a durable storage obligation

P7 may truthfully remain `waiting_for_reference` until independent external DFT exists. The request, publication, binding, component evidence, resource observation, and currentness lineage required to resume later are product state, not disposable scratch.

**Required correction:** safe/cache/archive decisions must preserve resumability of `waiting_for_reference`. A storage action may never manufacture pass/reject, lose the exact request identity, or force regeneration that changes the frozen qualification lineage. External DFT source bundles remain authoritative external inputs; any campaign-owned imported/authenticated representation is separate owner-declared durable evidence.

### F9 — current transitional reporting is advisory and still path-heavy

`storage report` is intentionally read-only and current family labels cannot grant mutation authority. It still performs physical/path-family accounting that is useful for byte totals but is not a sufficient semantic inventory.

**Required correction:** normal report moves to owner views for semantics plus bounded physical metadata. Exact recursive tree accounting becomes an explicit deep physical audit mode. Neither report path grants deletion authority.

### F10 — current consequential STOR operations are quarantined, not current implementations

The current transitional specification fails closed for current-generation `recompute`/`compact`, consequential archive, dedup apply, and archive restore. Historical primitives remain useful, but their candidate-selection and protocol-freeze/stage gates are obsolete.

**Required correction:** reuse low-level integrity primitives only after replacing their authority/selection layer with the owner-bound inventory/plan/revalidation design below.

## 3. Material engineering envelope and frozen design

### 3.1 Owner semantics are authoritative

Every material persistent artifact is conceptually classified as one of:

```text
AUTHORITATIVE_EXTERNAL_INPUT
DURABLE_SCIENTIFIC_EVIDENCE
CURRENTNESS_STATE
RESTART_STATE
REPRODUCIBILITY_BULK
REUSABLE_CACHE_INDEX
TEMPORARY_SCRATCH
DIAGNOSTIC_EVIDENCE
ARCHIVE_REPRESENTATION
```

Exact code names are delegated. Each owner view supplies, where applicable: semantic owner, exact generation/binding/publication/qualification identity, artifact identity/root, mutability/publication state, current/historical state, restart role, exact regeneration dependencies/cost, dedup/archive eligibility, active-attempt protection, and physical-accounting hints.

Descriptors are derived storage inputs. They are not persisted as a competing scientific registry unless a genuinely independent product need is demonstrated.

### 3.2 Required owner surfaces

The storage composition must account for these real current owners:

```text
CampaignStore/base persistence and external-record owner
P1 neutral substrate + canonical low-level cache owners
P2 statistical experiment/reducer owner
P3 execution/reconciliation/head/restart owner
P4 CampaignStore current generation/selected/current-terminal exposure owner
P5 post-selection CV/final-production persistence/currentness owner
P7 QualificationEvidenceStore / publication / attempt / release owner
shared frame, shard, SHA/validation receipt, model/export/runtime cache owners
```

Storage depends on those owners. Owners do not depend on a storage-authored scientific state machine.

### 3.3 Inventory -> immutable plan -> revalidate -> execute

All consequential storage mutation converges on one flow:

```text
owner views
 -> StorageInventorySnapshot
 -> StoragePolicyResolver
 -> immutable StoragePlan
 -> explicit authorization where consequential
 -> owner/currentness/attempt/operation-lease + filesystem identity revalidation
 -> StorageExecutor
 -> StorageAuditRecord
```

A plan binds the exact owner identities and relevant filesystem identities inspected. If generation, selected binding, P3 head/reachability, P5 lineage/currentness, P7 publication/qualification pointer/attempt state, external-input boundary, or relevant filesystem identity changes before apply, apply refuses and requires re-plan. It must not silently substitute a new candidate set.

Safe automatic cleanup may plan and apply within one invocation only if it crosses the same owner and physical revalidation immediately before mutation.

### 3.4 Retention policy

The current ordinary policy has three semantics:

- **safe** — zero scientific/restart/qualification/locked capability loss; owner-proven abandoned scratch, unreachable residue, stale staging, safe orphan records, and similar zero-capability-loss state only;
- **cache** — safe plus exact owner-certified reconstructible cache/index eviction; scientific and restart semantics unchanged, only recomputation/performance cost changes;
- **archive** — reversible authenticated cold representation of owner-approved reproducibility bulk after hot bytes are no longer required for active restart.

Generic current `recompute` and `compact` loss tiers are retired. Intentionally lossy history pruning requires a future explicit product decision and is outside this workplan.

### 3.5 Currentness, reachability, and retention fences

Reuse owner-specific mechanisms:

- P3 filesystem evidence-graph fence for publish-before-adopt/reconciliation;
- P5 currentness/restart owner and any clean owner-level reachability API established during S0/S1;
- P7 durable object + active-attempt retention fence;
- CampaignStore transaction/current-generation owner.

Filesystem scans are a fail-closed physical fallback, not a semantic replacement. Corrupt or unreadable owner state retains affected bytes until ownership is repaired or independently proven disposable.

### 3.6 Execution and storage-operation liveness

Do not create a universal PID registry. Existing owner attempt/publication locks and immutable publication semantics remain authoritative where sufficient.

Introduce exactly the additional liveness mechanism needed for storage mutations:

- one storage-operation serialization/lease owner preventing overlapping cleanup/dedup/archive/restore mutations;
- owner-specific execution lease/state only where an accepted owner lacks sufficient current attempt semantics and evidence proves a race otherwise exists.

Lease ambiguity reduces deletion authority. A stale PID, missing marker, hostname, or pathname alone never grants deletion.

### 3.7 Storage admission and resource planning

Before material storage operations estimate/bound as applicable:

```text
free bytes / quota
inode/file-count headroom
durable growth
checkpoint/restart growth
scratch/staging peak
atomic replace/copy amplification
archive/dedup temporary amplification
SQLite VACUUM/compaction temporary amplification
safety reserve
I/O concurrency
storage location/class
```

Integrate with the existing resource architecture. Storage pressure cannot change target membership, precision, epochs/fidelity, seed population, qualification population, timestep, acceptance threshold, locked policy, or any scientific decision.

I/O concurrency is independently controlled from CPU worker count and must not create metadata/checkpoint/hash thundering herds.

### 3.8 Cache and persistence specifics

**Frame cache.** Treat as current mmap-oriented performance state. Evict only when the owner proves exact reconstruction from authenticated source authority and no active consumer requires it. Remove `after_prepare` lifetime folklore.

**P1/DATA4/DATA6-style sharded state.** Preserve validated sharded/mmap representations and remove redundant cold reads. Hash while parsing in a single sequential pass where semantics permit; publish reconstructed state only after integrity/count validation.

**SHA/validation receipts.** Reclassify as reusable cache/index state with its own owner. Reuse for large immutable hashing where safe. Missing/corrupt/evicted receipts become cache misses. Never use receipt existence as completion/currentness authority.

**CampaignStore SQLite.** Remains authoritative state/currentness. Never dedup/archive it as an ordinary file family. Compact/VACUUM only under measurable benefit, lock safety, temporary-space admission, and restart equivalence. Diagnostic event retention is separate from scientific state and receipt-cache retention.

**P7 qualification.** Immutable `objects/`, current release/locked evidence, current pointers, and `waiting_for_reference` resume lineage are durable evidence. Active attempt references are protected. Terminal/aborted attempt scratch may be safe-reclaimable only through the P7 owner and after exact reference/restart checks.

### 3.9 Reporting

Normal report consumes owner inventories for semantics and bounded physical metadata. It reports, when available: logical/allocated/unique-inode bytes, file/inode count, owner/artifact class, current/historical/restart/cache/archive state, largest families, potential reclaim by action, and unresolved protected paths.

An explicit deep audit performs recursive exact physical accounting, symlink/ownership inspection, and debugging. Fast report and deep audit remain read-only and cannot grant mutation authority.

### 3.10 Immutable deduplication

Dedup is representation optimization only. An artifact participates only if its owner declares it immutable and storage reauthenticates exact byte identity. File extension, age, path, missing process, or historical stage state are insufficient.

Same-filesystem content-addressed hardlinks may be reused if measured and safe. Every participating writer must use create-new/atomic-replace discipline; no linked inode may later be mutated in place. Mutable SQLite, active attempt scratch, and any owner-ambiguous file are excluded. Cross-device/unsupported filesystems retain duplicate bytes without correctness failure.

### 3.11 Cold archive v2

Archive candidates are owner-approved, no-longer-hot-restart-required reproducibility bulk. Manifest identity binds owner/generation/selected/publication/qualification lineage, semantic artifact identities, source plan/currentness snapshot, archive policy, member path/mode/size/digest, archive format/codec, and archive digest.

Creation is:

```text
owner-approved candidates
 -> peak-space/inode admission
 -> immutable StoragePlan
 -> revalidate owner/currentness/leases
 -> create archive
 -> independently read back/authenticate
 -> publish archive catalog record
 -> only then remove represented hot bytes
```

Restore verifies archive+manifest, stages under campaign-owned attempt state, rejects unsafe paths/symlinks/conflicting bytes, authenticates staged content, installs transactionally/resumably, authenticates final hot representation, and never promotes historical evidence to current merely because bytes reappear.

A `latest` archive pointer is convenience only; catalog is identity-keyed. Codec is delegated to representative measurement and dependency cost.

## 4. Implementation stages

### S0 — baseline binding and complete P1-P7 artifact-authority census

Against the exact intake commit/tree, enumerate every material persistent/scratch family produced or consumed by CampaignStore, P1, **P2**, P3, P4, P5, P7, shared model/export/runtime helpers, frame/shard caches, receipt stores, archive/content stores, results, and generated views.

For each family determine: real semantic owner/API, locator/root, mutability, completion/currentness/reachability evidence, restart role, reconstruction recipe/cost, current consumers, scaling dimension, cache/dedup/archive eligibility, current P6/P7 transitional policy, and failure behavior.

Required explicit S0 decisions:

1. identify the actual P5 owner seam for any positive reconstructibility/currentness claim; retain families with no such seam;
2. map P7 `objects/`, `attempts/`, current pointers, external reference imports, locked/release evidence, resource observations, and waiting state separately;
3. split CampaignStore authoritative state from SHA/validation receipt cache;
4. distinguish derived current views/results from authoritative owner records;
5. re-derive the initially affected source/test/docs surface.

S0 is analysis/reconciliation, not a permanent duplicate artifact registry.

**S0 closure:** source-level owner census is complete enough that no material family entering a destructive action is classified solely by pathname. Any irreconcilable owner gap that prevents the frozen owner-driven design triggers a bounded Design reopen; simple missing adapter/API exposure is implementation work.

### S1 — establish owner-driven inventory and retire current STOR authority

Implement owner views and the cross-owner inventory snapshot. Preserve existing P3/P7 retention owners and `CampaignOwnershipBoundary` safety; refactor only to remove duplication.

Required end state:

- no current deletion/retention authority comes from STOR1-STOR5 stage names, retired evaluate/verify state, `workspace/runs`, PID markers, or old protocol-freeze predicates;
- path-family accounting may remain for physical totals but cannot create semantic eligibility;
- normal report consumes owner views; deep physical audit is explicit;
- P1/P2/P3/P4/P5/P7 current/historical/in-progress/waiting states are represented by real owner semantics;
- receipt cache is reported separately from CampaignStore authority;
- current CLI/config/spec/guide describe current owner-driven semantics; historical STOR documentation stays historical.

**Acceptance:** focused owner-view tests plus real-owner classification across P3 publish-before-adopt, P5 plan/partial/complete, P7 active/waiting/terminal states, external inputs, symlink boundaries, and corrupt-owner fail-toward-retention. Structural inspection proves no mutation consumes advisory report labels as authorization.

Run S1 stage-local affected regression before S2.

### S2 — transactional safe/cache cleanup, operation serialization, and admission

Implement immutable/revalidated StoragePlan, policy resolution, executor, audit, operation serialization, and storage/scratch/inode admission.

Safe/cache candidate eligibility requires a real owner. Preserve current P6 guarantees while expanding only from positive current owner contracts.

Mandatory real-owner counterfactuals:

- P3 published-but-not-adopted evidence survives;
- P3 current/restart graph survives close/reopen;
- P5 plan-only, partial multi-seed, completed production, and corrupt/mismatch states are not misclassified;
- P7 immutable release objects always survive ordinary safe/cache cleanup;
- P7 active attempt dependencies survive;
- terminal/aborted P7 attempt residue is reclaimed only when the P7 owner releases it and no durable/current record references it;
- P7 `waiting_for_reference` remains resumable with the exact request/publication/binding identity;
- owner advancement after planning invalidates apply;
- storage-operation contention does not interleave overlapping mutations;
- stale/ambiguous liveness reduces deletion authority;
- external input/symlink targets are never deleted;
- a cache eviction, where positively authorized, causes only exact rebuild work and reproduces the same authenticated owner result;
- safe/cache still preserve SHA receipts unless/until the receipt owner explicitly classifies a cache-tier eviction in this successor; safe itself never performs acceleration-cache eviction.

Filesystem/ENOSPC failures may be injected below the real planner/executor. Inventory/currentness owners may not be mocked for assembled deletion-safety acceptance.

Run S2 stage-local affected regression before S3.

### S3 — owner-certified deduplication and cold archive v2

Replace old hard-coded roots and retired freeze/stage gates with owner-certified immutable candidates and the same plan/revalidation/admission/serialization core.

P3/P5/P7 reproducibility bulk participates only when the owner proves immutability and hot representation is not required by active restart. P7 durable release objects remain durable evidence; archival may provide an authenticated alternate representation only if P7 owner semantics and resume/currentness remain exact.

Acceptance includes:

- exact-byte dedup equivalence;
- post-dedup in-place-mutation protection/atomic replace;
- cross-device fallback;
- archive round trip;
- manifest/member/archive corruption;
- interrupted archive before catalog publication;
- interrupted restore;
- conflicting destination;
- historical restore remains historical;
- owner advancement invalidates plan;
- waiting-for-reference archive/restore preserves exact resume lineage;
- active attempt cannot be archived out from under P7/P3/P5;
- mutable SQLite/attempt scratch cannot enter dedup merely by byte equality.

Run S3 stage-local affected regression before S4.

### S4 — I/O and persistence optimization

Apply optimization in order: eliminate redundant I/O, improve representation/reuse, then add bounded concurrency.

Required investigated surfaces:

1. frame-cache lifetime from actual consumers/rebuild cost;
2. P1/DATA4/DATA6 one-pass hash+parse and mmap/shard access;
3. shared SHA/validation receipt reuse across report/dedup/archive/restore;
4. owner-inventory fast reporting vs deep audit;
5. P3/P5/P7 owner reachability fast paths that avoid repeated whole-tree parsing;
6. P7 immutable-object and attempt-state reads/writes where batching/indexing can reduce metadata work without adding authority;
7. CampaignStore connection/transaction/compaction behavior and diagnostic event retention;
8. bounded file/shard counts and metadata operations;
9. archive codec/shard size after representative measurement;
10. I/O concurrency separate from CPU workers and bounded at observed storage saturation;
11. stagger/batch checkpoint/publication/hash operations where durability/scientific ordering are unchanged.

For each accepted optimization record representative bounded cold/warm wall time, bytes read/written, peak/final footprint, file/inode count where material, CPU overhead, and output identity. A speedup that weakens integrity/currentness checks or measures only warm page cache for a cold-restart claim is invalid.

Run S4 stage-local affected regression before S5.

### S5 — assembled real-owner P1-P7 storage/restart integration

Exercise a bounded assembled lifecycle through real owners:

```text
prepare
 -> select-target-size
 -> cross-validate
 -> train-production
 -> freeze FinalProductionPublication
 -> bounded qualification
 -> terminal or waiting_for_reference as appropriate
```

Inject report, safe cleanup, positive cache eviction+exact rebuild where an owner supports it, plan-then-owner-advance refusal, close/reopen, archive of eligible historical/reproducibility bulk, restore, and fresh-process reauthentication.

Required P7 branch: exercise `waiting_for_reference`, retain exact request/currentness lineage through storage operations, then where feasible use bounded reference fixtures below the accepted external-DFT semantic owner to prove that storage did not prevent the real P7 owner from resuming. This is functional integration, not a claim of actual production DFT qualification.

Real CampaignStore/P2/P3/P4/P5/P7 persistence/currentness owners and storage planner/executor must execute. Expensive MACE, LAMMPS, and DFT numerical work may use the already accepted bounded seams below those owners. Do not seed post-decision state or substitute an in-memory persistence proxy.

### S6 — final assembled closure

After all executable edits:

1. reconcile every obligation in this revision against the assembled candidate;
2. structurally confirm obsolete mutation paths/authorities are absent or unreachable;
3. re-derive the complete affected surface from the final source;
4. run fresh complete affected-surface regression, including every touched P1-P7 owner and storage consumer;
5. run assembled real-owner integration from S5 on the same candidate;
6. run repository-required static/build/docs/PDF checks;
7. use the broader/full CPU-safe suite when impact cannot be confidently bounded;
8. perform independent Software Design review.

No required real-owner integration that did not execute counts as a pass. Production-scale DFT/GPU/HPC qualification remains separate.

## 5. Failure/recovery acceptance

At minimum cover:

- truncated/partial owner artifact;
- digest/manifest mismatch;
- stale cache identity and receipt corruption;
- unsupported storage/archive schema;
- concurrent immutable object/cache publication;
- P3 publication interrupted before adoption;
- P7 component/object publication interrupted before current pointer;
- cleanup interrupted after a strict subset of safe actions;
- archive interrupted before/after archive bytes but before catalog publication;
- restore interrupted mid-install;
- simulated ENOSPC/quota/admission failure before destructive action;
- inode/file-count admission failure when supported by the seam;
- missing/renamed scratch path;
- stale/ambiguous execution liveness;
- storage-operation contention;
- current owner corruption causing fail-toward-retention;
- waiting-for-reference close/reopen and later resume;
- deterministic fresh-process reauthentication after every completed operation.

## 6. Initially expected affected surface

Re-derive at S0 and S6. Initial scope includes:

- `mdstats/training_data/storage_accounting.py`;
- `mdstats/training_data/storage_reclamation.py`;
- `mdstats/training_data/storage_archive.py`;
- campaign CLI storage parser/commands and `_campaign_ownership_boundary`;
- CampaignStore external-record, event/compaction, and currentness integration;
- P1 neutral/cache/shard persistence owners;
- P2 statistical experiment/reducer persistence;
- `campaign_target_size_retention.py`, P3 execution/reconciliation/head roots;
- P4 CampaignStore selected/current-terminal exposure integration;
- P5 post-selection store/run/currentness owners;
- `mdstats/training_data/qualification/store.py`, publication/reference/locked/release/currentness/attempt retention owners;
- frame cache and shared cache/index owners;
- SHA/validation receipt infrastructure;
- resource/admission configuration and I/O concurrency;
- storage, owner, restart, qualification, campaign-lifecycle tests;
- current storage specification/user guide/architecture docs and generated PDFs.

Historical V5/V6/STOR modules/docs are not automatically affected solely because old storage once referenced them.

## 7. Implementation authority

### Frozen

- The parent V7 scientific/architectural verdict and accepted P1-P7 semantics.
- Implementation intake commit/tree stated above.
- P6 transitional safety invariants remain the minimum baseline until this successor positively replaces them through current owner contracts.
- Scientific/currentness meaning comes from real semantic owners, not path names, report labels, stages, PIDs, or storage-generated state.
- External inputs and ambiguous ownership fail closed.
- Safe has zero scientific/restart/qualification/locked and acceleration-cache capability loss.
- Cache may evict only exact owner-certified reconstructible state.
- Archive is reversible representation change, not currentness promotion or lossy pruning.
- `recompute`/`compact` consequential-loss tiers are not current product authority.
- Storage plans bind exact inspected owner/currentness state and revalidate before mutation.
- Existing P3 and P7 retention owners are reused; P5 semantics are not fabricated to obtain reclamation.
- Dedup only owner-certified immutable bytes.
- Storage/scratch/inode/I/O admission is first-class and cannot alter science.
- P7 waiting/reference/locked/release evidence remains resumable and exact.
- Functional acceptance crosses real semantic owners; expensive numerical and failure seams may be replaced only below them.

### Delegated

- Exact inventory/plan/executor/adapter module and schema names.
- Protocol/registration/direct-composition implementation style, provided dependency/authority direction remains clear.
- Exact CLI spelling and deprecation surface for safe/cache/archive/deep-report.
- Archive codec/level and shard size after representative measurement.
- Hardlinks vs another exact dedup realization under the immutability/resource envelope.
- Exact storage-operation lease mechanism and any owner-specific liveness extension genuinely required after S0.
- Configurable thresholds for compaction/cache eviction and storage reserve.
- Exact bounded benchmark fixtures and worker counts.

### Reopen only on evidence

Reopen only the affected surface if:

- a current P1-P7 artifact cannot be safely classified without duplicating scientific state into storage;
- a required positive cache/archive operation cannot be expressed through the real owner without a material ownership redesign;
- representative measurement invalidates the owner-inventory/archive/admission design at target scale;
- supported filesystem semantics cannot provide required crash consistency or exact dedup/restore correctness;
- exact restartability requires a materially different persistence/archive boundary;
- an explicit product requirement for intentionally lossy history pruning emerges.

Do not reopen target-size, CV, publication, qualification, calibration, locked-test, or release science because storage implementation is inconvenient.

## 8. Production qualification disposition

Routine implementation requires bounded functional/restart/integrity tests and representative storage/I/O measurements. It does **not** require a real long DFT campaign, long target-GPU training, or HPC-scale storage benchmark.

Actual campaign external-DFT qualification and long target-machine production/resource/performance qualification remain deferred under the frozen parent/P7 authority. Environment-specific throughput/support claims require later representative qualification on that environment.

## 9. Snapshot-complete handoff

This revision contains all still-binding task-specific successor semantics needed for implementation. Earlier storage workplans and authority revisions are historical provenance and are not needed to recover the current contract.

Binding sequence:

```text
P6 revision 13 PASS [closed]
 -> P7 revision 13.7 software/functional PASS [closed]
 -> baseline 45b85e5... / tree 3efc629...
 -> S0 complete P1-P7 owner census
 -> S1 owner-driven inventory/current-authority retirement
 -> S2 transactional safe/cache + serialization/admission
 -> S3 dedup/archive v2
 -> S4 I/O optimization
 -> S5 assembled real-owner P1-P7 integration
 -> S6 final regression/docs/review
```

Snapshot-loss counterfactual: with this file, the frozen parent/current P1-P7 product artifacts, and the bound source baseline, implementation does not require prior chat, superseded storage revisions, obsolete STOR documents, or Git archaeology to recover any still-binding storage requirement.