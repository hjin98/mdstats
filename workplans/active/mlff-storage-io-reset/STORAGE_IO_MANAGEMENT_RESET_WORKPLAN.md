---
kind: implementation-workplan
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: planned
created_date: 2026-08-30
entry_condition: independent PASS for CODE-MLFF-TARGET-SIZE-V7-P6 revision 6 and CODE-MLFF-TARGET-SIZE-V7-P7 revision 2
baseline_binding: bind implementation to the independently accepted post-P7 commit/tree at implementation intake
compatibility_policy: current-generation-owner-driven; retired STOR1-STOR5 semantic policy is historical, not migrated as current authority
---

# MLFF campaign storage and I/O management reset workplan

## Objective and protected concerns

Renew the MLFF campaign storage subsystem after the P6/P7 architectural reset so storage management, cleanup, cache retention, deduplication, archival, recovery, disk/scratch admission, and large-artifact I/O are aligned with the accepted current P1-P7 owner model rather than the obsolete STOR1-STOR5 lifecycle topology.

The current storage implementation contains valuable low-level primitives, but its policy layer was designed around older `evaluate` / `verify` / DATA7-DATA8 / checkpoint-selection / verification-replay assumptions. Subsequent architecture revisions moved the authoritative high-volume state into P3 target-size execution, P5 selected-only post-selection, and the planned P7 final-publication/qualification graph. Current storage partially recognizes those roots but largely blanket-protects them, while continuing to optimize and reclaim artifact families from the retired topology.

The durable product outcome is:

```text
current P1-P7 semantic owners
        |
        | declare identity/currentness/restartability/immutability/root ownership
        v
owner-driven campaign storage inventory
        |
        v
validated storage policy + resource admission
        |
        v
immutable revalidated storage plan
        |
        v
safe cleanup / cache eviction / dedup / archive / restore
        |
        v
bounded audit evidence + restart-equivalent current product
```

Protected concerns:

- storage never becomes a second authority for scientific identity, selected membership, checkpoint/member choice, CV acceptance, publication membership, or qualification verdict;
- external user/source/reference inputs remain non-destructible regardless of path location, symlink, config reference, or record reference;
- current/restartable/in-flight evidence is not deleted because a pointer has not yet been adopted, a process temporarily disappeared, or a pathname looks stale;
- retired STOR-era stage names and path families never regain current authority under renamed predicates;
- cache/index deletion changes only recomputation/performance, never scientific meaning;
- durable scientific evidence remains reproducible and currentness-authenticatable after cleanup/archive/restore;
- storage, inode, scratch, metadata, and I/O bandwidth are treated as first-class execution resources rather than an afterthought to CPU/GPU scheduling;
- restart cost and cold-load I/O are optimized together with steady-state throughput;
- the renewed subsystem has the minimum justified number of policies/state machines and does not duplicate P3/P5/P7 persistence/currentness logic.

## Entry gate and non-goals

Implementation must **not** begin until:

1. P6 revision 6 receives independent cleanup/cutover PASS;
2. P7 revision 2 receives independent publication/qualification PASS;
3. the accepted post-P7 commit/tree is frozen as the implementation baseline.

At implementation intake, record the accepted baseline identity in the active package or implementation evidence. Do not invent an expected future commit in this planned workplan.

Non-goals:

- no change to target-size selection science, `N_selected/T_selected`, paired-seed reducer semantics, post-selection CV semantics, publication membership rules, physical qualification algorithms, calibration, or locked-test semantics;
- no migration of retired V5/V6/STOR-era derived scientific state into current authority;
- no requirement to retain the labels `STOR1` through `STOR5` in the current product;
- no production-scale DFT campaign, long GPU training qualification, or target-HPC storage benchmark as a prerequisite for ordinary functional acceptance;
- no speculative distributed object store, database service, or cloud storage layer unless actual repository/deployment evidence later creates that requirement.

## Engineering envelope and product design

### 1. Storage semantics come from the owner

The central architectural rule is:

> Storage may discover bytes and optimize their representation, but it may not infer scientific meaning, currentness, restartability, or deletion eligibility from a pathname when a semantic owner exists.

Every material persistent artifact is classified conceptually as one of:

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

Exact enum/class names are delegated. The semantic distinctions are frozen.

Each nontrivial artifact descriptor supplied to storage must provide, as applicable:

- semantic owner;
- owner generation/revision/selected-binding/publication identity;
- artifact identity and canonical root/path;
- mutability/publication state;
- current versus historical/stale status;
- restart/recovery role;
- authoritative dependencies or exact regeneration recipe;
- whether exact reconstruction is possible and its cost class;
- dedup eligibility;
- archive eligibility;
- active attempt/lease protection where applicable;
- logical/allocated size and file/inode count when known or cheaply measurable.

A descriptor is storage input, not duplicated scientific authority. P3/P5/P7 remain the source of the facts they own.

### 2. Owner adapters, not pathname policy

The renewed storage subsystem consumes explicit current owners. Suggested adapter names are nonbinding; the owner boundaries are binding:

```text
CampaignStore / base-persistence storage view
P3 target-size storage view
P5 post-selection storage view
P7 publication/qualification storage view
cache/index storage view(s)
```

The adapters must call the real owner APIs delivered by P6/P7 for generation, roots, reconciliation, currentness, immutable record resolution, run/attempt completion, publication, and terminal qualification.

The central storage layer must not contain a replacement scientific state machine for P3/P5/P7.

### 3. Inventory -> plan -> revalidate -> execute

Replace direct ad hoc cleanup decisions with one cross-owner flow:

```text
owner views
 -> StorageInventorySnapshot
 -> StoragePolicyResolver
 -> immutable StoragePlan
 -> explicit authorization when consequential
 -> reauthenticate bound owner/currentness/lease identities
 -> StorageExecutor
 -> StorageAuditRecord
```

Exact record/API names are delegated.

A plan binds enough owner/currentness and filesystem identity that an intervening generation/publication/attempt change invalidates it. Apply must never silently recompute a different candidate set after the operator inspected/authorized a previous plan. If the bound state changed, stop and require a new plan.

Automatic safe cleanup may plan and apply in one invocation only when it still performs the same owner/currentness revalidation immediately before mutation.

### 4. Retention policy simplification

Retire the old generic current meanings of:

```text
recompute
compact
```

Those tiers encode obsolete DATA7/DATA8/evaluation/verification capability assumptions and are too semantically broad for the current architecture.

The renewed ordinary policy surface should have three conceptual behaviors:

- **safe** — zero scientific/restart capability loss; remove proven abandoned scratch, unreachable publication residue, stale staging, and other state whose owner confirms disposability;
- **cache** — evict exact reconstructible caches/indexes; future execution may be slower but scientific/restart semantics remain intact;
- **archive** — replace owner-approved large reproducibility bulk with an authenticated reversible cold representation after the owner no longer requires the hot representation for active restart.

Exact CLI spelling is delegated. A future intentionally lossy history-pruning feature, if genuinely needed, requires an explicit product decision describing the exact reproducibility loss; it must not be smuggled back through a generic `compact` tier.

### 5. Currentness and reachability

P3's existing publication-race retention principle is generalized, not reimplemented centrally: absence of a CampaignStore pointer is not proof that freshly published content is orphaned.

The renewed subsystem must handle at least:

- P3 publish-before-adopt/reconciliation windows;
- P5 immutable-object-before-current-pointer windows and in-progress run state;
- P7 immutable publication/qualification component publication windows;
- stale historical generations that are no longer current but remain valid evidence;
- corrupt/unreadable owner state, which fails toward retention;
- provably unreachable content-addressed residue, which may become `safe` cleanup.

Owner reconciliation/reachability should provide the fast semantic path. Filesystem graph scans remain a fail-closed fallback only when the owner cannot provide a cheaper authenticated answer.

### 6. Execution and storage-operation leases

Introduce robust liveness protection where current attempt semantics are insufficient to prevent cleanup races.

An execution lease, when needed, must bind enough identity to distinguish an active attempt from PID reuse or stale remote-host residue; typical fields may include owner/attempt identity, host/session/process-start nonce, protected roots, and heartbeat/expiry policy.

Introduce one storage-operation lease/serialization owner so cleanup, dedup, archive and restore cannot concurrently mutate overlapping campaign storage.

Do not build broad lock-file machinery when owner partitioning/immutable publication is sufficient. Leases reduce deletion authority; ambiguity fails closed.

### 7. Storage admission and I/O resource planning

Storage becomes a first-class resource dimension in long-stage execution.

A material stage/operation must estimate or bound, where applicable:

```text
current free bytes / quota
inode or file-count headroom
expected durable growth
checkpoint/restart growth
scratch/staging peak
atomic replacement/copy amplification
archive/dedup temporary amplification
required safety reserve
I/O concurrency and storage location/class
```

Static `minimum_free_disk_gib` may remain an input but is insufficient as the complete admission model.

Integrate disk/scratch/I/O reservations with the existing resource-budget architecture without letting storage pressure change scientific membership, precision, timestep, epoch/fidelity boundaries, evidence populations, or acceptance thresholds.

I/O worker/concurrency count is separate from CPU worker count. Avoid checkpoint/hash/serialization thundering herds from independently admitted compute jobs.

### 8. Current artifact and cache policy

#### 8.1 Frame cache

The normalized frame cache is a current mmap-oriented performance representation, not preparation garbage. Its lifetime must be based on remaining current consumers and regeneration cost, not `remove_frame_cache_after_prepare` stage folklore.

Retain it while P3/P5/P7 current consumers benefit unless storage pressure and policy choose a valid cache eviction. Eviction must preserve exact rebuild from authenticated source authority.

#### 8.2 DATA4/DATA6 sharded persistence

Preserve current sharded/mmap representations where they remain owner-valid, but remove avoidable double I/O. JSONL restore should hash while parsing in one sequential pass and make the reconstructed result visible only after count/content validation closes. NPY mmap semantics remain preferred for large homogeneous numerical arrays.

#### 8.3 SHA/validation receipts

Use the shared durable SHA/validation receipt machinery as an optimization across storage accounting, dedup, archive verification, and large immutable restore where safe. Receipt loss/corruption must remain a cache miss, never a correctness failure or scientific-state loss.

Reclassify the receipt database as a reusable cache/index rather than protected scientific provenance.

#### 8.4 SQLite state

CampaignStore remains authoritative currentness/state. Do not perform routine whole-database `VACUUM` merely because cleanup ran. Compact only when measurable fragmentation/size benefit and temporary-space admission justify it; preserve transaction/restart semantics.

### 9. Storage reporting

Normal `storage report` should prefer owner inventories and bounded filesystem metadata instead of recursively rediscovering scientific meaning from the entire workspace.

Provide an explicit deep physical audit mode for exact tree accounting, symlink/ownership inspection, or debugging when useful. A fast report never grants deletion authority; destructive plans directly revalidate every candidate/root.

Report at minimum when available:

- logical and allocated bytes;
- deduplicated physical/inode-aware size;
- file/inode counts;
- owner/artifact class;
- current/historical/restart/cache/archive state;
- largest families/artifacts;
- potential reclaim by safe/cache/archive action;
- unresolved/ambiguous paths that remain protected.

### 10. Immutable deduplication

Deduplication is an execution representation optimization only.

Admit files only when their semantic owner declares them immutable and the storage layer reauthenticates exact byte identity. Never infer immutability from `.json`, `.pt`, `.model`, path location, age, or lack of an active process.

Same-filesystem content-addressed hardlinks may be retained if they remain the simplest measured implementation. Any linked file must be written by create-new/atomic-replace discipline; no accepted writer may mutate shared-inode content in place.

Reuse existing content digests or shared SHA receipts before rereading full files. Cross-device and unsupported filesystems fail to non-deduplicated retention, not correctness failure.

### 11. Cold archive v2

Preserve the proven byte-integrity principles of the existing archive primitive, but replace stale candidate selection and lineage.

The renewed archive manifest must bind, directly or through owner descriptors:

```text
archive identity/schema
owner identities and generation/selected-binding/publication lineage
artifact semantic identities/classes
source currentness snapshot / plan identity
archive policy identity
member path, mode, size, digest
archive format/codec
archive byte digest
```

Archive creation sequence:

```text
owner-approved candidates
 -> storage peak-space/inode admission
 -> immutable storage plan
 -> revalidate owner/currentness/lease identities
 -> create cold representation
 -> independently read back and authenticate
 -> publish archive record/catalog
 -> only then remove represented hot bytes
```

The archive catalog is keyed by archive identity. A `latest` pointer may exist only as convenience, not as the sole usable archive locator.

Restore must:

- verify archive + manifest before installing;
- stage under a campaign-owned attempt root;
- reject unsafe paths/symlinks/conflicting bytes;
- authenticate staged content;
- install transactionally or through a resumable journal/root publication so interruption cannot masquerade as a completed restore;
- reauthenticate the final hot representation;
- never make restored historical evidence current merely because its bytes reappeared.

Compression/codec is execution policy. Benchmark representative local data before changing the current gzip choice; retain the simplest supported codec that gives the best end-to-end engineering result. Do not add a dependency solely for a small synthetic compression win.

### 12. Documentation/current-history split

Move the old “STOR1-STOR5 roadmap complete” specification and release qualification assertions out of current normative storage authority where they still remain. Preserve them as historical implementation evidence if useful.

Current architecture/spec/user documentation should describe one generation-neutral storage subsystem with owner-driven semantics. Release chronology stays in history/release notes.

## Implementation obligations and stages

### S0 — bind post-P7 baseline and perform current artifact authority census

**Concern / rationale:** The previous subsystem became stale because artifact families were encoded centrally and later architectural revisions moved the real owners.

**Required end state:** Against the exact accepted post-P7 baseline, inventory every persistent/scratch family produced or consumed by:

- CampaignStore/base persistence;
- P1/preparation and current caches;
- P3 target-size execution;
- P4 selected binding/currentness;
- P5 cross-validation/final production;
- P7 final publication and qualification;
- shared model/export/deployment/runtime helpers relevant to durable artifacts.

For each material family record owner, root/locator, mutability, completion/currentness evidence, restart role, regeneration dependencies/cost, typical scaling dimension, and current storage policy.

**Required consequences:** Use this census to validate the workplan's initial affected surface. If post-P7 implementation materially differs from the assumed owner boundaries, reconcile locally when semantics are equivalent; reopen Design only if the frozen owner-driven architecture cannot be satisfied.

S0 is analysis/source reconciliation, not a new permanent artifact registry unless the product independently needs one.

### S1 — retire stale STOR semantic authority and establish owner-driven inventory

**Required end state:**

- old current STOR1-STOR5 specification/roadmap semantics become historical;
- central path-name classification is no longer the semantic source of deletion/retention authority;
- owner adapters expose the conceptual artifact descriptor set;
- normal storage report consumes the owner-driven inventory;
- current CLI/config/docs no longer describe retired `evaluate`/`verify`/DATA7-DATA8 retention rules.

**Acceptance:** focused owner-adapter tests; structural absence of retired current predicates; P3/P5/P7 current/historical/in-progress classification through real owners; external/symlink protections unchanged.

### S2 — transactional safe cleanup, cache eviction, and lease/admission core

**Required end state:**

- immutable/revalidated `StoragePlan` flow;
- safe/cache policy only for owner-authorized candidates;
- storage-operation serialization and execution-liveness protection where needed;
- storage/scratch/inode admission helpers integrated with long operations;
- cleanup audit records retain only useful action/identity/capability evidence;
- threshold-driven CampaignStore compaction rather than unconditional `VACUUM`.

**Acceptance boundary:** Real storage planner/executor plus real P3/P5/P7 currentness owners must execute. Faking the inventory/owner answers is not sufficient for the assembled deletion-safety claim. Filesystem failures/ENOSPC may be injected below the executor.

**Mandatory counterfactuals:**

- P3 published-but-not-adopted evidence survives;
- P5 immutable-object-before-pointer evidence survives;
- P7 in-flight publication/qualification evidence survives;
- owner generation/currentness change after planning invalidates apply;
- active/ambiguous lease protects;
- stale proven scratch may be reclaimed;
- cache eviction changes only rebuild work and reproduces exact owner result;
- external input/symlink target is never deleted.

### S3 — deduplication and cold archive v2

**Required end state:**

- owner-certified immutable dedup inventory replaces old hard-coded roots;
- current P3/P5/P7 reproducibility bulk can participate only when owners declare it immutable and no active restart needs the hot representation;
- archive-v2 owner lineage/catalog and storage admission are implemented;
- restore is resumable/transactional and cannot promote historical state to current;
- old `recompute`/`compact` archive-source selection is gone from current authority.

**Acceptance:** exact-byte dedup equivalence; in-place-mutation guard/atomic-replace behavior; cross-device safe fallback; archive round-trip; manifest/member/archive corruption; interrupted archive before receipt; interrupted restore; conflicting destination; historical restore remains historical; archive plan invalidated by owner advancement.

### S4 — I/O and persistence optimization pass

Apply the optimization order: remove redundant I/O first, improve representation/reuse second, then concurrency.

Required investigated/implemented surfaces include:

1. frame-cache lifetime based on actual current consumers/cost rather than `after_prepare`;
2. DATA4/DATA6 one-pass hash+parse restore where it reduces cold reads without weakening integrity;
3. shared SHA/validation receipt reuse in archive/dedup/report paths;
4. owner-inventory fast report versus explicit deep audit;
5. P3/P5/P7 reachability fast paths that avoid repeated whole-tree parsing when current owner evidence already proves the result;
6. bounded file/shard counts and metadata operations on large campaigns;
7. archive codec/compression and shard size only after representative measurement;
8. I/O concurrency separated from CPU worker count and bounded at observed storage saturation;
9. checkpoint/publication write staggering/batching where it improves I/O without changing durability or scientific ordering.

**Performance acceptance:** For each accepted optimization, compare equivalent baseline/candidate on representative bounded workloads and record cold/warm wall time, bytes read/written, final/peak footprint, file count when material, CPU overhead, and output identity. Do not accept a speedup obtained by weakening checks, skipping evidence, moving work outside timing, or using only warm page-cache behavior when cold restart is the material path.

### S5 — assembled P1-P7 storage/restart integration

Exercise one bounded real-owner chain:

```text
prepare
 -> select-target-size
 -> cross-validate
 -> train-production
 -> freeze FinalProductionPublication
 -> bounded nonlocked qualification
 -> terminal/waiting qualification state as appropriate
```

Inject storage operations at meaningful boundaries:

```text
report
safe cleanup
cache eviction + exact rebuild
plan then owner advancement -> refusal
close/reopen
archive eligible historical/reproducibility bulk
restore + reopen
```

The semantic owners and storage planner/executor remain real. Expensive MACE/DFT numerical work may use the already accepted bounded seams below those owners. Do not seed post-decision state or replace CampaignStore/P3/P5/P7 persistence with a proxy.

### S6 — final closure and current documentation

Re-derive the full affected surface from the assembled implementation. Complete:

- focused storage/accounting/ownership/archive/dedup/cache/persistence checks;
- affected P1-P7 regression for every owner/storage integration touched;
- concurrency/restart/failure tests;
- public CLI/config compatibility and deprecation checks;
- current architecture/spec/user-guide rewrite and history separation;
- repository-required static/build/docs/PDF checks;
- broader/full CPU-safe suite when the affected surface cannot be bounded more narrowly;
- final independent Software Design review.

A required current-owner integration test that does not execute is not a pass.

## Task-specific failure/recovery acceptance

At minimum cover:

- truncated/partial owner artifact;
- content digest or manifest mismatch;
- stale cache identity;
- unsupported current storage schema;
- concurrent immutable cache/object creation;
- publication interrupted before owner pointer/adoption;
- cleanup interrupted after some safe actions;
- archive interrupted before/after archive bytes but before catalog publication;
- restore interrupted mid-install;
- simulated `ENOSPC` / quota/admission failure before destructive action;
- inode/file-count admission failure where supported by the test seam;
- missing scratch path;
- stale/ambiguous execution lease;
- storage-operation contention;
- deterministic close/reopen after every completed action.

## Initially expected affected surface

This list is provisional and must be re-derived at S0 and final S6:

- `mdstats/training_data/storage_accounting.py`;
- `mdstats/training_data/storage_reclamation.py`;
- `mdstats/training_data/storage_archive.py`;
- central campaign CLI storage parser/commands and cleanup hooks;
- `campaign_target_size_retention.py` and P3 root/reconciliation integration;
- P5 post-selection store/runtime root/currentness integration;
- P7 publication/qualification persistence introduced by the accepted P7 baseline;
- frame-cache and current cache/index owners;
- DATA4/DATA6 sharded persistence;
- shared SHA/validation receipt infrastructure;
- CampaignStore compaction/event retention where affected;
- execution resource/admission configuration;
- storage-specific tests, campaign lifecycle regression, docs/spec/history and generated docs.

Deleted historical V5/V6 modules are not automatically affected merely because old storage code once referenced them.

## Implementation authority

### Frozen

- Implementation starts only after accepted P6 and P7 baselines.
- Scientific/currentness meaning comes from P1-P7 semantic owners, not path names or central storage stage aliases.
- No current `evaluate`/`verify`/DATA7-DATA8/SELECT2/STOR-era policy resurrection.
- External inputs and ambiguous ownership fail closed.
- Safe/cache ordinary reclamation has zero scientific/restart capability loss.
- Archive is reversible representation change and never currentness promotion.
- Generic `recompute`/`compact` consequential-loss tiers are retired from current authority.
- Storage plans bind owner/currentness state and are revalidated before mutation.
- Current/in-flight publication races are protected.
- Dedup operates only on owner-certified immutable bytes.
- Storage/scratch/inode/I/O admission is a first-class resource concern.
- P3/P5/P7 currentness/reconciliation logic is reused, not duplicated.
- Functional acceptance must exercise real semantic owners with only expensive numerical/filesystem failure seams below them.

### Delegated

- Exact module/class/function/schema names for storage inventory/plan/executor/adapters.
- Whether owner adapters use protocols, registration, explicit composition, or direct construction, provided ownership remains clear and dependencies point from storage to owners.
- Exact CLI spelling for `safe`, `cache`, `archive`, report/deep-report, and deprecation behavior.
- Archive codec/level after representative benchmark and dependency-cost review.
- Hardlink versus another exact same-filesystem dedup realization when measured behavior and immutability guarantees justify it.
- Exact execution-lease fields/heartbeat mechanics when existing owner attempt semantics already provide equivalent protection.
- Exact thresholds for SQLite compaction and cache eviction as configuration/execution policy, not scientific semantics.

### Reopen only on evidence

Reopen only the affected design surface if:

- the accepted post-P7 implementation lacks a clean owner/currentness boundary despite the P6/P7 handoff amendments;
- a material current artifact cannot be classified without duplicating scientific state into storage;
- representative storage measurement proves the proposed owner-inventory or archive design cannot meet target scale/resource constraints;
- a supported filesystem cannot provide required atomicity/hardlink/rename semantics and the failure materially affects correctness/recovery;
- preserving exact restartability requires a materially different checkpoint/archive boundary;
- a genuine product requirement for intentionally lossy history pruning emerges.

Do not reopen target-size, CV, publication, or qualification science merely because storage implementation is inconvenient.

## Production qualification disposition

Routine implementation requires bounded representative storage/I/O benchmarks and complete functional/restart/integrity acceptance.

Long target-GPU/real-data qualification remains outside this workplan. Hardware/filesystem-specific production qualification on large NVMe, network/shared HPC storage, quota-constrained clusters, or large real campaigns is **deferred unless explicitly requested or required to claim support/performance on that environment**. The implementation must not claim such production-scale throughput from local bounded tests.

## Handoff closure

This planned package is snapshot-complete for the accepted storage design while intentionally leaving the future post-P7 commit identity unresolved until its entry gate exists.

The binding product sequence is:

```text
P6 revision 6 implementation + independent PASS
 -> P7 revision 2 implementation + independent PASS
 -> freeze exact accepted post-P7 baseline
 -> S0 baseline/census
 -> S1 owner-driven retirement/inventory
 -> S2 safe cleanup/cache/lease/admission
 -> S3 dedup/archive v2
 -> S4 I/O optimization
 -> S5 assembled P1-P7 integration
 -> S6 final regression/docs/review
```

Snapshot-loss counterfactual: given this workplan, the current accepted P1-P7 architecture/specification set, and the exact post-P7 source baseline supplied at implementation intake, Implementation must not require prior chat history, the obsolete STOR1-STOR5 roadmap, or Git archaeology to recover any still-binding task-specific storage requirement.
