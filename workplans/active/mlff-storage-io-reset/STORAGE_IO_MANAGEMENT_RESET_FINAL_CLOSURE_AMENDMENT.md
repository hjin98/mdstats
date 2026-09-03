---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R10
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: active
amended_date: 2026-09-01
reviewed_base_workplan: STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md
reviewed_intake_commit: 45b85e5dfb98bed4abbfee47cdb020bb2bd401c8
reviewed_intake_tree: 3efc6297c31c1d233a733ec792f0fba08aea10a1
scope: final independent closure review; tighten cross-owner dependency retention, race-safe mutation, archive eligibility/recovery security, storage-native metadata ownership, policy identity, dedup metadata safety, and interrupted-operation semantics without reopening the accepted owner-driven architecture
precedence: this amendment tightens and completes revision 2 where stated; all revision-2 requirements remain binding unless explicitly narrowed here
---

# Storage/I-O reset final closure amendment

## 0. Independent review verdict

The revision-2 owner-driven architecture is accepted. No evidence requires reopening the frozen parent V7 science, the P1-P7 scientific/currentness architecture, or the central storage design:

```text
real semantic owners
 -> owner-derived inventory
 -> resolved storage policy
 -> immutable owner-bound plan
 -> race-safe revalidation/fencing
 -> storage mutation
 -> restart-equivalent product
```

The final challenge review found several **workplan-level omissions/tightening needs**, not a need for a different global architecture. They matter because a literal revision-2 implementation could otherwise preserve each local owner while breaking a downstream owner, or could preserve archive bytes while making the accepted public owner APIs unusable.

This amendment closes those gaps. After this amendment, the current implementation handoff is the composed pair:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`.

The pair is snapshot-complete for current task-local storage semantics and requires no superseded storage revision or Git archaeology.

---

## 1. Final finding R10-1 — retention is cross-owner dependency closure, not independent per-owner classification

### Evidence and concern

Current P7 publication is a read-only descendant of the accepted P5 publication. `checkpoint_path_for_member(...)` resolves the representative checkpoint directly under the P5 run root, and `authenticate_member_bytes(...)` fails closed if those P5 bytes are absent or changed. P7 therefore does **not** contain an independent replacement copy of the product checkpoint.

P7 active-attempt retention correctly protects referenced P5 checkpoints while an attempt is active. However, terminal/aborted attempt references are intentionally released. That does not mean the current P5 checkpoint becomes disposable: the current frozen publication and future P7 authentication still depend on it.

Equivalent cross-owner dependencies exist elsewhere, notably P4 current-terminal authentication over P3 evidence and P5 descendants over the selected/current P4 authority.

### Frozen corrected end state

Storage eligibility is computed over the **transitive dependency closure of all current/restartable owners**, not by asking each path's nominal owner in isolation.

Conceptually:

```text
owner artifact A
    <- required by current/restartable descendant B
    <- required by current/restartable descendant C

A remains protected if any reachable B/C requires A,
even when A's own producing stage is terminal.
```

Required rules:

1. Owner views must expose enough dependency identity/path information to determine downstream retention without copying scientific decisions into storage.
2. The cross-owner inventory must compose those edges into one protection closure before any safe/cache/archive hot-removal decision.
3. Protection is monotone across owners: if any current/restartable owner requires an artifact, another owner's cache/history classification cannot override that requirement.
4. P7 current publication explicitly pins the exact P5 published member checkpoint bytes while that publication can still be resolved/authenticated as current.
5. P4 current terminal/selected authority continues to pin the P3 immutable evidence required by its canonical loader/reconciliation chain.
6. `waiting_for_reference` pins every predecessor artifact required to resume the exact frozen publication and qualification lineage, including published P5 member checkpoints.
7. Historical evidence may become archive/reclamation eligible only after no current/restartable descendant depends on its hot representation and the owning semantics permit the proposed action.
8. Do not solve this with a second persistent dependency database. Derive edges from current owner records/views; persist only ordinary storage plans/catalogs/audits when independently required.

### Mandatory acceptance

Add real-owner counterfactuals that would fail if dependency closure is absent:

- complete P5 publication -> construct/resolve current P7 publication -> finish/release the P7 attempt reference -> safe/cache/archive planning still protects the exact P5 representative checkpoint;
- `waiting_for_reference` after the attempt reference is terminal still protects the exact P5 publication bytes and exact external-reference request/resume lineage;
- advancing to a genuinely newer selected/publication lineage invalidates the old current dependency, after which historical eligibility is decided by the old owner's explicit history/archive policy rather than by stale descendant pointers;
- P4 current terminal reload remains valid after every allowed storage operation because required P3 evidence closure is preserved.

A test that keeps an active P7 attempt lease throughout the assertion is insufficient for the first two claims; the point is durable **post-attempt** descendant dependency.

---

## 2. Final finding R10-2 — check-then-unlink is not sufficient race safety

### Concern

Revision 2 requires immediate owner/currentness/filesystem revalidation before mutation, but a naked snapshot check can still race with an owner publication occurring immediately afterward.

The current P5 publication pattern is especially important:

```text
publish immutable object
 -> later publish CampaignStore current pointer under commit-time stale-generation fence
```

There is therefore a legitimate object-before-pointer window. Deleting an apparently unreachable P5 object between those two steps could allow the pointer publication to succeed while its referenced immutable object has disappeared.

### Frozen corrected end state

Every destructive or representation-changing action must have a **race-safe mutation authorization**, not merely a recent snapshot.

For a candidate that can race with its semantic owner, implementation must use the simplest existing/owner-local mechanism that closes the race, such as:

- an owner-owned reclamation API that performs eligibility + mutation under its publication/reconciliation synchronization;
- an existing per-artifact publication lock acquired by both publisher and storage mutation;
- an owner retention/publication-window protocol whose grace/reachability invariant is formally sufficient for the exact race;
- another equivalent owner-local synchronization mechanism.

Rules:

1. The central storage-operation lease serializes storage operations with each other; it does **not** by itself serialize storage against P1-P7 writers.
2. Do not hold a broad CampaignStore transaction across hashing, compression, recursive scans, or other slow filesystem I/O solely to close this race.
3. If an owner has no race-safe reclamation seam, the affected artifact remains retained until such a seam is exposed or Design is reopened under the existing trigger.
4. P5 immutable object-before-pointer publication must be explicitly protected before any P5 immutable-object garbage collection is enabled.
5. P3's accepted publication-window/evidence-graph retention mechanism remains valid substrate; do not replace it merely for architectural symmetry.
6. P7 durable `objects/` remain ordinary safe/cache protected under the accepted owner and are not an orphan-GC target simply because a current pointer is temporarily absent.
7. Archive hot deletion and dedup replacement are mutations for this rule and require equivalent race safety against owner writers/readers.

### Mandatory acceptance

- pause a real P5 publication after immutable object publication and before the CampaignStore pointer; run the real public storage operation; resume publication; the object remains and the current pointer resolves successfully;
- race plan/apply against owner advancement/publication at the narrowest supported test seam and prove either storage loses/refuses or the owner still resolves a complete valid state;
- structural/source inspection proves central storage does not implement a generic `is_current(); unlink()` path for owner-published evidence without an owner-local race barrier.

---

## 3. Final finding R10-3 — archive replacement may not make current owner APIs archive-aware by accident

### Concern

Revision 2 permits archive to replace owner-approved hot reproducibility bulk. Current P1-P7 loaders generally dereference canonical hot paths directly. For example, current P7 publication re-authenticates P5 checkpoints at their canonical P5 run paths. Merely preserving those bytes inside a tar archive would not preserve the accepted public/current owner behavior.

### Frozen corrected end state

For this package, **archive is not a transparent virtual filesystem and storage does not insert a new cold-read dependency underneath scientific/currentness owners merely to reclaim current bytes**.

Hot-byte removal is allowed only when all of the following are true:

1. the owning artifact is historical/reproducibility bulk or otherwise explicitly owner-declared cold-replaceable;
2. no current or restartable dependency closure requires its canonical hot representation;
3. no current owner resolver/currentness validator directly requires the canonical hot file;
4. explicit restore is sufficient to regain the historical/reanalysis capability promised for that artifact;
5. the archive is authenticated and cataloged before hot deletion.

Consequences:

- current P5 representative checkpoints required by the current P7 publication are **not** hot-removable by archive;
- current P3 evidence required by P4 current-terminal validation is not hot-removable;
- current P7 release/locked/qualification objects that current public resolvers directly load are not hot-removable;
- an archive may still contain backup copies of such current artifacts, but creating a backup does not authorize deletion of the canonical hot copy;
- historical owner evidence may be replaced by an archive when the owner and cross-owner closure prove no current/restart consumer requires hot access.

If representative measurements later show that meaningful storage targets cannot be met without transparent cold resolution of current owner artifacts, that is a **Design reopen trigger**. Do not silently add storage-aware fallback loaders to P1-P7.

### Mandatory acceptance

- archive planning refuses hot removal of a P5 checkpoint while current P7 publication authentication depends on it;
- archive planning refuses hot removal of any P3/P7 object directly required by a current public resolver;
- an eligible historical artifact can be archived, removed hot, explicitly restored, and then authenticated by its historical owner without becoming current;
- source inspection confirms no P1-P7 current loader was given an implicit `if missing: read storage archive` fallback under this package.

---

## 4. Final finding R10-4 — storage has its own control-plane artifacts and must own them explicitly

### Concern

Revision 2 classifies P1-P7 artifacts but under-specifies storage-native state. The renewed subsystem necessarily creates some durable or semi-durable state of its own: archive catalog/manifest/receipt, restore journal/receipt, cleanup/dedup execution audit, and storage-operation serialization state. Without an explicit owner, storage could recursively classify or reclaim its own recovery authority incorrectly.

### Frozen corrected end state

S0/S1 must include **storage-native control-plane state** as a first-class storage owner surface.

Required semantics:

- `StoragePlan`: may be ephemeral when planning+apply occur in one invocation; if persisted for later authorization/apply, it is immutable and content-identified, but it never grants scientific authority;
- cleanup/cache/dedup audit: diagnostic/operational evidence with bounded retention; loss must not invalidate scientific currentness, but an incomplete operation must never be recorded as complete;
- archive catalog + archive manifest/receipt: durable storage authority required to locate/authenticate cold representations and must survive for as long as the corresponding archive is retained;
- restore journal/attempt state: recovery state until restore reaches a verified terminal result, then bounded/retirable according to storage owner policy;
- storage-operation serialization state: operational liveness only, not scientific currentness; stale/crashed ownership must recover fail-closed without a permanent deadlock;
- storage cache/indexes, if any: reconstructible and never a second archive or scientific authority.

The storage control plane must be inside the campaign-owned boundary or another explicitly authorized storage root. It may not include raw secrets or machine-specific credentials in plans/audits/manifests.

Safe/cache/archive/dedup must not delete or archive away the only catalog/journal required to locate, authenticate, resume, or restore an existing cold representation.

### Mandatory acceptance

- a retained archive remains discoverable/verifiable after ordinary safe/cache cleanup and fresh-process restart;
- interrupted restore reopens from the storage owner's journal or deterministically restarts without accepting partial installation;
- stale storage-operation ownership is recoverable without PID/pathname inference granting deletion authority;
- cleanup of old audit/plan records cannot delete archive catalog state still needed by a retained archive;
- storage-native records contain no scientific currentness decision and cannot cause a historical owner artifact to become current.

---

## 5. Final finding R10-5 — storage policy/configuration must have one resolved identity

### Concern

`StoragePolicyResolver` is named in revision 2, but the accepted handoff does not yet require one canonical effective-policy representation. A plan inspected under one reserve/codec/threshold/concurrency policy must not execute later under silently different defaults, CLI overrides, or auto-selected values.

### Frozen corrected end state

Implement one canonical resolved storage policy used by CLI/config/API paths.

It must normalize and bind, as applicable:

- requested action/tier and apply/dry-run semantics;
- storage/scratch safety reserve policy;
- cache eviction limits/thresholds;
- SQLite compaction thresholds;
- archive codec/level/shard policy;
- dedup realization policy;
- I/O worker/concurrency limits;
- deep-audit/resource bounds;
- operational time/size thresholds materially affecting candidate selection.

Dynamic measurements such as current free bytes/quota/inodes and observed saturation are **execution observations**, not permanent policy defaults. The plan records the resolved policy identity plus the material admission observation used for that plan.

Rules:

1. Changing storage policy invalidates/requires re-planning of an unapplied storage plan.
2. Storage policy changes do not invalidate P1-P7 scientific identities merely because storage execution policy changed.
3. CLI/config/default aliases normalize before policy hashing; equivalent forms produce equivalent policy identity.
4. No hidden environment variable may silently widen deletion/archive authority.
5. User-facing diagnostics report the resolved consequential action and material automatic choices without persisting secrets.

### Mandatory acceptance

- equivalent CLI/config forms normalize identically;
- a material policy change between plan and apply refuses stale apply;
- irrelevant presentation/report formatting changes do not invalidate the plan;
- dynamic free-space changes cause admission revalidation, not scientific invalidation;
- unsupported combinations fail before mutation.

---

## 6. Final finding R10-6 — archive verification/restore must bound hostile or corrupt expansion before writing it

### Concern

The historical archive primitive is useful, but its current restore streams a tar member to disk and verifies expected size afterward. A corrupt/tampered compressed archive can therefore expand far beyond its manifest-declared member size before rejection, consuming disk or time. Path verification also needs canonical-collision protection, not only `absolute`/`..` checks.

### Frozen corrected end state

Treat archive bytes/manifests as authenticated-but-untrusted content until all relevant checks pass. Archive-v2 verify/restore must enforce before/during extraction:

1. supported schema/codec only;
2. canonical workspace-relative member paths with no absolute path, `..`, empty component, path-normalization alias, or duplicate/collision after canonical normalization;
3. regular files/directories only unless a future explicit design permits more; reject symlink, hard-link, device, FIFO, socket, sparse/special entries that violate the approved representation;
4. manifest member-count and total-expanded-byte admission before extraction;
5. per-member exact expected size bound during streaming: never write/read unbounded member data and only discover oversize after the fact;
6. cumulative extracted-byte bound during restore and verify;
7. archive compressed-size / expected-expansion sanity bound sufficient to prevent decompression-amplification exhaustion without relying on actual resource exhaustion tests;
8. campaign-owned staging root with no traversal through archive-created symlinks;
9. exact digest/size authentication before install;
10. no implicit overwrite of conflicting authoritative/current bytes.

The exact safe tar-reading implementation is delegated; reuse standard-library safety facilities where they fit rather than creating an incomplete custom extractor.

### Mandatory acceptance

Use bounded synthetic archives to prove rejection of:

- absolute and `../` paths;
- canonical path aliases/collisions;
- symlink/hard-link/special members;
- duplicate members;
- member content longer than manifest size;
- total expansion beyond admitted manifest/policy limit;
- corrupt archive/member digest;
- conflicting destination.

The oversize tests must use small bounded fixtures/test seams; do not exhaust real disk/RAM.

---

## 7. Final finding R10-7 — hardlink deduplication must preserve owner-required inode metadata semantics

### Concern

Exact byte equality is necessary but not sufficient for hardlink deduplication. Hardlinked names share one inode's mode/ownership/xattrs and any later in-place metadata mutation. Two files with equal bytes but materially different owner-required filesystem metadata are not interchangeable hardlink candidates.

### Frozen corrected end state

Dedup eligibility requires:

```text
owner-certified immutability
+ exact content identity
+ owner-certified metadata compatibility
+ filesystem realization support
+ race-safe replacement
```

Rules:

1. File type and required mode/permission semantics must remain correct.
2. If owner semantics require xattrs/ACLs/other metadata, compatibility must be established or the file excluded.
3. Every deduplicated owner must prohibit both **content and material metadata mutation in place** for the linked artifact. Later update is create-new/atomic-replace or the artifact is not eligible for hardlink dedup.
4. `chmod`, `chown`, truncate/write, or equivalent in-place mutation of a shared inode is forbidden unless all aliases intentionally share that metadata contract, which must be explicitly owner-certified.
5. Dedup may change inode/ctime and therefore invalidate stat-keyed acceleration receipts; that is acceptable only as a cache miss/revalidation, never as scientific state change.
6. Cross-owner dedup is allowed only when both owners independently satisfy the same immutable/metadata contract; otherwise retain duplicate bytes.

### Mandatory acceptance

- equal bytes with incompatible modes/owner metadata do not hardlink;
- a deduplicated path survives a later atomic-replace update to another alias without changing the first path;
- any in-place metadata/content writer on an eligible family is structurally removed/refactored or the family is excluded;
- receipt/cache behavior after inode replacement remains correctness-neutral.

---

## 8. Final finding R10-8 — interrupted cleanup/dedup/archive execution needs explicit idempotent terminality

### Concern

Revision 2 lists interruption cases but leaves room for an audit/receipt to report success after only a strict subset of actions, or for retry to infer completion from partially mutated files.

### Frozen corrected end state

Every multi-action storage operation has an explicit terminality/recovery contract.

**Safe/cache cleanup**

- each removal is independently owner-authorized and race-safe;
- a crash after a subset of removals is allowed because completed removals were individually safe;
- retry re-inventories/re-plans current state rather than assuming the old remaining set;
- no terminal `complete` audit is published until all actions in that execution have reached verified terminal disposition;
- rollback of already-safe deletions is not required.

**Dedup**

- each replacement is exact and idempotent;
- interruption cannot leave a temporary path accepted as canonical;
- retry reauthenticates both canonical member and content object before linking.

**Archive**

- archive bytes without an authenticated catalog/manifest do not authorize hot deletion;
- authenticated archive/catalog may safely coexist with some still-hot members after interruption;
- retry reconciles which hot members remain and removes only those still authorized under a fresh owner-bound plan/fence;
- a terminal archive record means archive authentication is complete, not necessarily that every optional hot byte was already reclaimed unless the record explicitly distinguishes those states.

**Restore**

- partial staged/install state is never accepted as complete;
- terminal receipt follows final canonical-byte authentication;
- retry is idempotent for already-present identical bytes and fails closed on conflicts.

### Mandatory acceptance

Inject failure after multiple distinct action boundaries, not only before the first operation. After restart, prove current owner state is valid, operation status is truthful, and rerun either completes safely or refuses a changed plan without manual filesystem surgery.

---

## 9. Required stage amendments

The following tighten revision-2 S0-S6 and are mandatory.

### S0 additions

The artifact-authority census must also produce, as analysis/implementation knowledge rather than a duplicate scientific registry:

- cross-owner dependency edges needed for retention closure;
- owner publication/reconciliation synchronization seam for every family that may be mutated;
- direct-hot-path requirements of current public resolvers;
- storage-native control-plane artifacts and their recovery/retention roles;
- owner-required filesystem metadata for any proposed hardlink-dedup family;
- canonical storage policy/configuration surfaces.

No destructive family leaves S0 as positively eligible while any of those facts remains ambiguous.

### S1 additions

Owner views must expose dependency and race/fencing information needed by the planner. The inventory resolver computes transitive current/restart protection. Storage-native control-plane state becomes an explicit owner view. Canonical storage policy resolution is established before S2 plan persistence/execution.

### S2 additions

Before enabling positive P5 object reclamation, close the real P5 immutable-object-before-pointer race. Add post-terminal P7 -> P5 dependency retention tests. Executor actions use owner-local race barriers rather than naked check-then-unlink.

### S3 additions

Archive hot removal follows R10-3 and may not make current P1-P7 loaders storage-aware by fallback. Archive-v2 restore implements R10-6 expansion/path/type bounds. Dedup implements R10-7 metadata/aliasing constraints. Archive/catalog/restore journal follow R10-4 and R10-8.

### S4 additions

Optimization measurements must include the cost of dependency-closure construction, owner synchronization, archive bounded verification, and cold historical restore where those paths become material. Do not optimize them away by weakening validation.

### S5 additions

The assembled real-owner chain must include:

1. current P7 publication/release state after its attempt retention reference has been released;
2. a storage plan proving the exact P5 publication checkpoint remains protected through cross-owner closure;
3. `waiting_for_reference` in the same post-attempt condition;
4. a real P5 object-before-pointer publication race against storage planning/apply;
5. one eligible historical archive whose hot bytes are removed and require explicit restore for historical owner use;
6. fresh-process archive-catalog discovery/verification and restored historical-owner authentication;
7. storage policy change between plan and apply causing refusal;
8. interruption after a strict subset of multi-action cleanup/archive/restore work.

### S6 additions

Final structural review must prove:

- no current scientific/currentness loader gained an implicit archive fallback;
- no mutation path uses only snapshot revalidation when the owner can concurrently publish/use the artifact;
- no cross-owner current dependency is lost by local cache/history classification;
- no storage control-plane record can promote scientific currentness;
- no hardlink-dedup family has an accepted in-place content/material-metadata writer;
- archive restore enforces bounded canonical-member extraction.

---

## 10. Implementation authority amendment

### Additional frozen decisions

- Retention is the union/transitive closure of all current/restartable owner dependencies.
- Current P7 publication pins its exact P5 publication checkpoints after active attempt retention has ended.
- Destructive/representation mutation is synchronized against semantic-owner publication/use; storage-operation serialization alone is insufficient.
- Current owner APIs are not made transparently archive-aware merely to improve reclamation. Hot removal is restricted to owner-declared cold-replaceable state with no current/restart hot dependency.
- Storage-native archive/catalog/journal/audit/operation state has explicit ownership and cannot become scientific authority.
- Storage plans bind one canonical resolved operational policy identity.
- Archive verification/restore is bounded against path/type/expansion abuse before dangerous writes.
- Hardlink dedup preserves owner-required inode metadata semantics and forbids in-place mutation of shared inode content/material metadata.
- Multi-action operation completion is explicit and crash/retry idempotent; partial execution cannot masquerade as terminal success.

### Additional delegated mechanics

- Exact representation of dependency edges and protection closure.
- Exact owner-local synchronization API when existing publication locks/fences are insufficient.
- Exact storage-control-plane root/file/schema names.
- Exact safe tar parsing/extraction API and conservative expansion-ratio thresholds.
- Exact filesystem metadata set beyond mode when an owner demonstrates it is material.
- Exact audit/journal status schema and bounded retention limits.

### Additional reopen triggers

Reopen only the affected storage design if evidence proves:

1. current product footprint cannot meet material storage feasibility without transparently cold-resolving artifacts that current P1-P7 loaders presently require hot;
2. an owner cannot expose race-safe reclamation without a material lifecycle/ownership redesign;
3. cross-owner dependency closure requires duplicating scientific state instead of deriving it from current owner records;
4. a supported filesystem's link/rename/locking semantics make the selected dedup/archive recovery model materially unsafe;
5. bounded safe archive verification cannot support a required archive format at target scale.

Do not weaken currentness/restart/publication/qualification semantics to avoid these triggers.

---

## 11. Final closure disposition

With this amendment, the storage successor is **Design-closed / implementation-ready** subject to the composed current authority. No unresolved design blocker is known at the reviewed intake baseline.

The implementation sequence remains S0 -> S6, with the amendments above folded into their corresponding stages. Full external-DFT scientific qualification, long GPU production qualification, and environment-specific HPC storage qualification remain deferred exactly as already governed; they are not reintroduced by this final closure.