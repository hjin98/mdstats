---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R13
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
amended_date: 2026-09-01
reviewed_repair_authority_head: e093e607ab64fc7c09da58e0695880081dd51997
reviewed_repair_authority_tree: 3e738894c2e8b49ae03a02eed00888ecfc868331
reviewed_executable_commit: 53edc1c75c5b7c9df8f414914534ce915c34f303
reviewed_executable_tree: 8d24e6326b67c38e69a1fe1383be7b975788cac5
scope: final closure review of the reopened R12 repair contract; add missing explicit-authorization, read-only, owner-graph, historical-generation synchronization, lock-order, restore-plan, archive-self-containment, filesystem-boundary, admission, audit, maintenance, reporting, and documentation obligations; simplify dedup by removing the unnecessary persistent content-store authority
precedence: this amendment composes with STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md, STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md, AUTHORITY_REVISION_11.md, and STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md; where this amendment explicitly corrects or narrows R12 text, this amendment controls; all unaffected frozen requirements remain binding; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset repair-plan closure amendment

## 0. Review disposition

No new executable storage implementation has landed after the R12 independent review. The current branch head contains the R12 Design reopen authority only. This review therefore challenges the **repair contract itself** before Implementation resumes.

The R12 repair direction remains valid, but a second independent challenge found several omitted consequences and one unnecessary product-complexity commitment. These gaps are material because an implementation could satisfy the literal R12 findings while still:

- obtaining apply authority from persistent configuration rather than the current invocation;
- mutate campaign state during a command advertised as read-only or dry-run;
- lock only the current generation while mutating a historical generation;
- deadlock a new P5/frame-cache liveness lease against the existing publication barriers;
- restore from an authenticated archive without an exact owner-bound restore intention;
- retain an unnecessary dedup content-addressed store and its garbage-collection authority;
- traverse a nested mount that is lexically inside the campaign workspace but semantically externally owned;
- underestimate archive/restore peak disk and inode amplification;
- omit the durable storage audit for specialized archive/dedup/restore paths;
- perform unplanned CampaignStore maintenance even after the primary cleanup action was refused;
- leave owner-graph ambiguity or known campaign roots invisible to the inventory;
- let terminal restore journals or mutable catalog fields grow/rewrite without the frozen lifecycle discipline.

This amendment closes those gaps. It does **not** reopen target-size science, P1-P7 currentness semantics, the transitive owner-driven storage architecture, archive-v2 security/durability rules, or the production-qualification boundary.

### Preserved R12 findings

All IR12 findings remain binding except where explicitly corrected below. In particular preserve:

- exact owner-bound planning and fresh semantic revalidation for archive/dedup;
- archive-root narrowing and per-represented-owner authorization;
- frame-cache active-use safety;
- stale-running P5 historical-run liveness;
- immutable archive representations;
- exact relevant owner-currentness binding;
- bounded normal reporting versus explicit deep accounting;
- benefit-gated CampaignStore rewrite;
- executed stage-local/final regression and real-owner integration evidence.

### One explicit R12 design correction

IR12-B5 directed Implementation to add ownership/garbage collection for the implementation's persistent `.mdstats/storage/content-store`. That persistent CAS was an implementation choice, not a frozen requirement of Revision 2, and it creates avoidable durable state, garbage collection, audit, recovery, reporting, and hardlink-ownership complexity.

**This amendment supersedes that portion of IR12-B5.** The accepted default dedup realization is direct hardlink aliasing among owner-certified immutable campaign files, with no persistent dedup content store. Section 6 freezes the corrected realization.

---

## 1. IR13-1 — explicit current-invocation authorization cannot come from persistent configuration

### Concern and evidence

The current policy resolver copies the complete `[storage]` table into the effective policy and then resolves:

```text
action = merged.pop("action", requested_action)
tier   = merged.pop("tier", requested_tier)
apply  = merged.pop("apply", invocation_apply)
```

Therefore a persisted `apply = true` can turn a nominal dry-run into a consequential mutation, and persisted `action`/`tier` can redirect what an explicit CLI/API command means. This defeats the frozen explicit-authorization boundary.

### Required end state

1. **Apply authority is invocation-local only.** `--apply`, or an equivalently explicit API argument supplied by the current caller, is the only source of authorization to mutate.
2. Persistent config, environment, manifests, plans, prior audit records, or stored results can never set `apply=true` for a later invocation.
3. The invoked command/API selects the action. `[storage].action` must not silently redirect it. Remove that persistent key or reject a conflicting value; an exact redundant value may be tolerated only if doing so has a real compatibility benefit.
4. Explicit invocation tier/action arguments take precedence over any supported configuration default. A config default may narrow convenience selection only when the caller did not explicitly select that field; it cannot widen authority.
5. `--dry-run` and absence of `--apply` both remain non-mutating regardless of persistent configuration.
6. Unknown or forbidden authority-bearing configuration keys fail before mutation.
7. Equivalent supported aliases normalize before policy identity; authorization itself remains outside policy identity so planning and later explicit apply can share one semantic intention.

### Acceptance

- `[storage].apply = true` plus a command without `--apply` performs no mutation; preferably the forbidden key is rejected with an actionable error.
- `[storage].action` cannot make `storage archive create` execute cleanup/dedup/report semantics or vice versa.
- explicit CLI tier beats a configured default.
- environment variables cannot widen apply/action/tier authority.
- dry-run and apply resolve the same action-scoped policy identity except for authorization state.

---

## 2. IR13-2 — policy identity must be action-scoped and every public policy knob must be real

### Concern

The current `StoragePolicy.policy_identity` hashes all storage fields for every action. A cleanup plan can therefore be invalidated by a change to archive compression level or deep-audit presentation/resource bounds even though those values cannot affect cleanup. Conversely several current knobs are decorative or incompletely enforced:

- `cache_eviction_maximum_bytes` is not applied to the selected cache actions;
- `deep_audit_entry_limit` is not an actual traversal bound;
- `audit_retention_records` is enforced by cleanup's executor but not by specialized archive/dedup/restore paths.

A canonical policy should bind every material decision and nothing irrelevant.

### Required end state

1. Each consequential plan binds an **action-scoped effective policy identity** containing action/tier plus only values capable of changing that action's candidate set, physical realization, admission, synchronization, or terminal behavior.
2. A material field change for the requested action invalidates apply; an unrelated action's field does not.
3. No public `[storage]` key may be a decorative hashed knob. Implement its stated behavior or remove/reject it.
4. If positive cache eviction remains supported, `cache_eviction_maximum_bytes` bounds the selected owner-certified cache actions deterministically. An atomic owner artifact is either selected whole or retained whole; do not partially delete a cache tree merely to hit the cap unless the cache owner explicitly exposes smaller independent units.
5. `deep_audit_entry_limit` is an actual resource bound. If exact traversal would exceed it, fail or return a clearly incomplete/bounded result; never label incomplete totals as exact.
6. Audit retention is applied consistently to the single storage audit stream after consequential operations, subject to the truthful-audit rules in section 10.
7. Presentation-only fields remain outside consequential plan identity.

### Acceptance

- changing archive codec invalidates an archive plan but not an otherwise unchanged cleanup plan;
- changing deep-audit limit does not stale cleanup/dedup/archive plans unless that action actually consumes it;
- cache eviction never exceeds the configured atomic-unit cap;
- a bounded deep audit reaches its limit without exhausting the machine and does not claim exact completion;
- configuration/API/CLI equivalent forms produce the same effective action-scoped identity.

---

## 3. IR13-3 — read-only and dry-run storage paths must be observational, not state-producing

### Concern and evidence

Several current observation paths mutate the campaign before any apply decision:

- config loading calls `CampaignPaths.ensure()`, creating workspace/internal/data/runs/models/results directories;
- constructing `CampaignStore` creates/initializes SQLite schema and writes schema metadata;
- constructing `StorageCommandContext` opens the storage control plane through an `ensure()` path, creating `.mdstats/storage/*` directories;
- normal/deep report writes JSON files into `results/`;
- cleanup dry-run writes an advisory plan file; dedup dry-run writes a report file;
- P5 read resolution can call `open_post_selection_store()`, which creates the generation root;
- hash-receipt helpers can write acceleration receipts while a nominally read-only owner inventory hashes data.

The current product calls `storage report` read-only and requires planning/dry-run to stop before mutation. Creating or altering managed persistence violates that promise and can also perturb the next inventory/plan identity.

### Frozen corrected end state

**All non-apply storage invocations are side-effect-free with respect to managed campaign state.** This includes:

```text
storage report
storage report --deep
storage archive list
storage archive verify
storage cleanup --dry-run / no --apply
storage deduplicate --dry-run / no --apply
storage archive create --dry-run / no --apply
storage archive reclaim --dry-run / no --apply
storage archive restore --dry-run / no --apply
```

Required consequences:

1. Read-only config/path resolution must not call a create/ensure path merely to inspect a campaign.
2. Existing CampaignStore state is opened read-only for inventory/report/planning. Missing state is reported as missing/uninitialized or unresolved; a report must not create it.
3. Owner adapters used for inventory must have read-only opens/resolvers that do not create P5/P7 generation roots, storage control-plane directories, cache files, receipts, or currentness state.
4. The storage control plane has a non-creating open/view mode for list/verify/report/planning. Apply may create storage-owned control state only after the invocation is explicitly consequential and authorized.
5. Read-only inventory hashing, when unavoidable, bypasses write-through receipt creation or uses a genuinely read-only receipt lookup.
6. By default, report and dry-run output is returned/printed only. Do not persist result/plan JSON merely because the command was invoked.
7. A future explicit `--output`-style diagnostic export may write a user-requested report, but that file is diagnostic output only, never a plan/currentness/deletion authority, and the explicit export itself must not alter owner state.
8. Read-only and dry-run commands may take shared/read locks where needed for coherent observation, but those locks must not create scientific/currentness state.

### Acceptance

For each non-apply command above, capture an exact filesystem tree/byte/mode/mtime snapshot and relevant SQLite state before/after. The managed campaign state is byte-for-byte and topology-equivalent after the command, except for an explicitly requested diagnostic output outside the authority set.

Also prove:

- reporting an uninitialized/missing campaign does not materialize a new workspace or SQLite database;
- inventorying P5/P7 does not create empty generation roots;
- read-only report does not create `.mdstats/storage` merely to say no storage control plane exists;
- repeated report/dry-run does not create SHA receipt writes or other cache churn.

---

## 4. IR13-4 — owner graph integrity is a fail-closed prerequisite to consequential planning

### Concern

The current owner composition uses `artifact_id` as the graph key. A dict conversion can silently overwrite duplicate IDs. A dependency edge naming a missing artifact can be recorded as a textual protection reason without a concrete owner/path, after which the physical protection index cannot actually retain that missing dependency.

An incomplete dependency graph cannot establish deletion/archive/dedup authority.

### Required end state

1. Every owner artifact ID in one inventory is unique. Duplicate IDs are an inventory integrity failure, not last-write-wins data.
2. Every `requires` edge relevant to current/restart protection resolves to exactly one owner view.
3. A missing or ambiguous dependency makes the protection closure incomplete and causes consequential planning to fail closed for any action whose safety could depend on that closure. The simplest acceptable behavior is to refuse all consequential mutation until graph integrity is restored.
4. Read-only reporting remains available and surfaces the exact unresolved/duplicate dependency without mutating state.
5. No synthetic path or guessed owner is invented to make an unresolved dependency look protected.
6. Owner graph validation occurs before candidate eligibility is used to construct a consequential plan.

### Acceptance

- duplicate `artifact_id` from two owner views refuses consequential planning;
- missing dependency target refuses consequential planning;
- report shows the integrity problem read-only;
- a valid graph preserves current transitive P7 -> P5 and P4 -> P3 closure behavior.

---

## 5. IR13-5 — synchronization is derived from every touched owner generation, with one deterministic lock order

### Concern and evidence

The current specialized command context returns only `snapshot.current_generation` as the owner-barrier generation set. Archive/dedup/restore operations can mutate historical `g1` while `g2` is current, yet acquire only g2 publication barriers.

R12 also permits adding a P5 run-activity or frame-cache no-use lease but did not freeze lock ordering against existing P5/P7 publication barriers. A stale P5 writer could hold an activity lease through training and then acquire the publication barrier while storage holds the publication barrier and waits for the activity lease: a classic cycle.

### Required end state

1. The synchronization set is derived from the **exact planned artifacts/members/destinations**, not only the currently selected generation.
2. Any action touching `gN` acquires the relevant gN owner publication/no-use synchronization before final revalidation and mutation.
3. Include the current generation additionally when current-owner advancement must be fenced for the plan's semantic identity; do not substitute it for touched historical generations.
4. Any new P5 run-activity or frame-cache activity mechanism participates in one documented deterministic lock order shared by the real owner and storage.
5. No code path acquires the same common locks in reverse order.
6. Keep expensive hashing/compression/tree scans outside the narrow publication critical section where possible. Precompute/stage outside, then acquire the complete required synchronization set, rebuild/freshly validate semantic state and exact input identity, and publish/mutate.
7. Storage's global operation lease remains storage-vs-storage serialization and does not replace owner synchronization.

A suitable order may be:

```text
storage-operation lease (storage paths only)
 -> owner activity/no-use leases in deterministic owner/generation order
 -> owner publication barriers in deterministic owner/generation order
 -> fresh owner/plan/admission revalidation
 -> narrow mutation/publication
```

The exact order is delegated, but there must be one order and it must be cycle-free.

### Acceptance

- current g2 plus paused historical g1 P5 execution/publication: archive/dedup/restore touching g1 blocks/refuses until the real g1 owner permits mutation;
- a deterministic race where P5 moves from run execution into final publication while storage attempts historical mutation completes/refuses without deadlock;
- structural inspection proves every shared lock acquisition follows the same order;
- no specialized path computes barrier generations solely from `current_generation`.

---

## 6. IR13-6 — simplify dedup: no persistent storage CAS; close external-hardlink ownership

### Design correction

Revision 2 permits same-filesystem hardlink dedup when measured and safe. It does not require a durable content-addressed object store. The implementation's persistent `.mdstats/storage/content-store` is therefore unnecessary product state, and IR12-B5's proposed lifecycle/GC machinery would compound that accidental complexity.

### Frozen corrected realization

Use **direct hardlink aliasing within each freshly authorized immutable dedup group**:

1. Select one deterministic canonical campaign member whose owner certifies immutable content and material metadata.
2. Reauthenticate canonical and replacement members under the plan's owner synchronization.
3. For each duplicate, create a temporary hardlink to the canonical inode and atomically replace the duplicate path.
4. Do not retain a separate canonical object in `.mdstats/storage/content-store`.
5. Later deletion or atomic replacement of any alias naturally drops that name's link. When the final campaign alias disappears, the filesystem releases the inode without a storage garbage collector.
6. Dedup remains representation-only; it creates no scientific/currentness authority and no persistent dedup registry.

### External/unknown hardlink rule

A canonical source inode must have **closed link ownership**. The low-complexity accepted rule is:

- use a canonical source with `st_nlink == 1` before the new group links are created; or
- if the implementation explicitly proves every pre-existing link is a known authorized campaign alias in the exact dedup group, equivalent closed ownership is acceptable.

Never use an inode with unknown pre-existing links as the canonical shared inode: an external writer through an unknown hardlink could mutate all newly deduplicated campaign paths.

A candidate with unknown links may be safely detached by atomic replacement from a known canonical inode if its own owner permits replacement and the external alias is untouched. If no closed-ownership canonical source exists, retain duplicates.

### Consequences for R12-B5

- remove the persistent content-store owner/GC requirement from R12;
- remove or retire the current content-store orphan-pruning helper and current content-store artifacts when owner-proven safe migration/cleanup is possible;
- if an already-produced candidate campaign contains old implementation CAS objects, treat them as legacy storage-owned residue and reclaim them only after proving they have no remaining campaign aliases and no active operation depends on them;
- reintroducing a persistent CAS later requires evidence of a material product benefit that outweighs its lifecycle/GC/recovery complexity and a bounded Design reopen.

### Acceptance

- two or more owner-certified immutable duplicate files become direct hardlink aliases with no persistent content-store object;
- deleting/archiving/replacing every campaign alias causes the inode allocation to disappear naturally;
- replacing one alias atomically leaves the others unchanged;
- a candidate with an external hardlink is never chosen as canonical shared inode; modifying the external alias after dedup cannot affect unrelated campaign files;
- repeated dedup is idempotent;
- cross-device or no-safe-canonical cases retain duplicates without correctness failure.

---

## 7. IR13-7 — restore requires an exact owner-bound restore plan, not only archive verification/conflict checks

### Concern

R12 correctly strengthened archive create/reclaim, but its restore language could still be implemented as:

```text
authenticate old archive -> check destination conflicts -> install
```

That is weaker than the frozen consequential flow. Restore is a representation-changing filesystem mutation and can race an owner that begins writing the same historical path.

### Required end state

Every restore dry-run/apply derives an immutable restore intention from an authenticated catalog/manifest plus a fresh owner inventory.

The restore plan binds, per represented reclamation unit/member as applicable:

- archive representation identity, manifest identity, catalog immutable identity and source plan/lineage identity;
- represented owner artifact identity and generation/lineage identity;
- exact destination path and expected pre-state: absent or exact-identical historical bytes;
- expected member type/mode/size/digest and required metadata contract;
- owner currentness/history classification and proof that restore cannot overwrite a current/restart-owned incompatible artifact;
- resolved action-scoped restore policy and admission observation;
- every owner generation/activity/publication synchronization seam required for installation.

At apply:

1. acquire storage and all touched-owner synchronization;
2. rebuild/freshly validate owner state;
3. reauthenticate catalog/manifest/blob identity;
4. revalidate every destination state and owner/history classification;
5. revalidate peak storage/inode admission;
6. stage/install durably;
7. authenticate final canonical bytes;
8. publish truthful restore terminality/audit.

A restored historical artifact remains historical. Restore does not write current pointers.

### Dry-run requirement

`archive restore` dry-run must compute and show the same semantic restore plan/conflicts that apply would attempt, without creating staging/journals/control-plane state. `archive reclaim` dry-run similarly authenticates the archive and computes the current reclamation plan instead of merely printing that no action was taken.

### Acceptance

- restore planned against a historical destination then owner advancement makes it current without changing path/content: apply refuses/replans;
- concurrent writer to one touched historical generation is fenced;
- dry-run reports exact destination conflicts and leaves the campaign unchanged;
- policy/admission change between plan and apply is revalidated;
- restoration remains non-current after fresh process reopen.

---

## 8. IR13-8 — retained archive authority must be self-contained for future reclaim/restore

### Concern

The current archive manifest records an opaque `source_plan_identity`, while plans are normally ephemeral/advisory. Future `archive reclaim` is required to reconstruct represented owner identities from retained archive authority. A bare digest is not enough if the corresponding plan is not durably retained.

### Required end state

A retained archive representation is self-contained enough for a fresh process to safely verify it and construct current reclaim/restore plans without relying on:

- an advisory file under `results/`;
- an in-memory plan object;
- prior chat/review context;
- Git history;
- a storage plan that was never promised durable retention.

Persist in the immutable manifest/catalog authority, or in an immutable retained storage-plan object explicitly referenced by it, the minimum non-secret material needed to map represented bytes back to owner semantics:

- exact represented owner artifact IDs;
- generation/lineage/currentness identity captured at creation;
- selected owner root/subroot or reclamation-unit mapping;
- member -> represented owner/reclamation-unit mapping sufficient to prevent umbrella authority;
- source plan identity and the material action set it identifies;
- archive representation policy/format/member metadata already required by Revision 2/R11/R12.

Do not persist secrets, transient machine credentials, or dynamic free-space observations as archive identity. Dynamic observations may remain diagnostic.

### Acceptance

After process restart, remove any advisory result/plan files and reconstruct verification + current reclaim/restore planning from only the real campaign owner state and retained archive control-plane authority. Every represented member is still mapped to an owner artifact without guessing from pathname.

---

## 9. IR13-9 — nested mount/filesystem boundaries are ownership boundaries

### Concern

Lexical and `realpath` containment do not prevent traversal into a nested bind mount or other mounted filesystem that appears below the campaign workspace. Recursive `rmtree`, archive collection, deep audit, and dedup traversal could therefore operate on externally owned bytes mounted at a campaign-contained pathname.

### Frozen end state

1. The campaign workspace or an owner artifact root may itself live on a mounted filesystem.
2. Recursive storage traversal **must not cross into a nested mount boundary below the authorized root** unless that nested mount has its own explicit storage-owner authorization. This package introduces no such automatic authorization; default behavior is retain/refuse.
3. Apply this to recursive deletion, archive collection/reclamation, dedup enumeration, deep physical audit where ownership matters, restore destination traversal, and any storage-native legacy cleanup.
4. A different `st_dev` is a useful signal but is not sufficient for same-device bind mounts. Use the platform's supported mount-identity/mount-table mechanism where available; uncertainty fails toward retention.
5. Symlink non-traversal rules remain separately mandatory.

### Acceptance boundary

CI need not require privileged mount creation. It may substitute a deterministic mount-identity resolver **below the real CampaignOwnershipBoundary/path traversal owner** to model nested mounts. The actual authorization/traversal code under acceptance must remain production code.

Acceptance cases:

- nested mount below an otherwise eligible archive/delete/dedup root is not traversed or mutated;
- external bytes visible through that mount remain byte-for-byte unchanged;
- the workspace root itself being a mount remains supported;
- ambiguous mount discovery retains rather than traverses.

---

## 10. IR13-10 — storage admission must bound real peak bytes and inode/entry amplification

### Concern and evidence

The current archive admission equates archive peak bytes to the sum of file payload sizes and requests two inodes. Tar headers/padding, compression framing, manifest/catalog/temp files and directory entries can make the actual additional footprint larger, especially for many tiny files. Restore currently treats `2 * expanded bytes` and approximately one inode per manifest member as sufficient even though staged and installed copies can coexist and directory/journal/temp entries add more.

An admission system that underestimates deterministic container/staging amplification can still hit ENOSPC after it claimed the operation was safe.

### Required end state

For every material storage mutation, admission conservatively bounds **additional peak allocated bytes and inode/directory-entry count** at the target filesystems, including as applicable:

- archive container headers/padding/codec framing and worst-case non-beneficial compression;
- immutable blob/manifest/catalog publication temp files and directory entries;
- restore staging + installed copies that can coexist before staging cleanup;
- staged directories and terminal journal/receipt entries;
- atomic replacement temporary links/files;
- any retained legacy-CAS cleanup work during migration;
- SQLite rewrite amplification;
- filesystem reserve and minimum inode headroom.

If exact pre-computation is impractical, use a conservative upper bound plus a bounded recheck before each material expansion phase. Do not use optimistic compression ratio as safety admission.

Storage on different filesystems/root locations requires admission against every filesystem that receives temporary or durable growth.

### Acceptance

- many-tiny-file archive fixture where tar metadata dominates is refused under simulated near-limit resources before mutation;
- restore with staged+installed coexistence uses the larger inode/byte bound;
- changing free space between planning and protected execution causes admission refusal without scientific/currentness mutation;
- tests inject resource observations rather than exhausting real disk/inodes.

---

## 11. IR13-11 — every applied consequential path participates in one truthful durable storage audit

### Concern

The accepted storage specification and Revision 2 end every consequential path in `StorageAuditRecord`. Cleanup currently appends the control-plane audit through `StorageExecutor`, but specialized archive/dedup/restore paths can mutate without appending the shared audit and therefore also bypass uniform audit retention.

### Required end state

All applied consequential storage mutations contribute to the one storage-owned durable audit contract:

```text
safe/cache cleanup
archive create
archive hot reclaim
archive restore
deduplication
CampaignStore maintenance when actually performed
legacy storage-native residue cleanup when performed
```

Each operation records enough non-secret operational truth to establish:

- action and operation/plan/policy identity;
- complete/partial/refused/failed status as applicable;
- completed and refused reclamation units or equivalent concise counts/identities;
- archive representation / restore / dedup identity where relevant;
- reclaimed/created/restored byte counts where known;
- no scientific-currentness authority.

Rules:

1. A multi-action operation interrupted after some successful mutations is never audited as complete.
2. If an exception occurs after a subset of dedup/archive/restore mutations, record truthful partial state before rethrow when the control plane remains writable.
3. Audit publication occurs downstream of the state it claims, following existing durability ordering.
4. Audit write failure cannot retroactively roll back already-safe filesystem mutation and cannot become scientific failure; surface the operational evidence failure truthfully and never fabricate `complete`.
5. Do not generate durable audit records merely for read-only/dry-run observation.
6. Apply `audit_retention_records` uniformly to this stream after consequential operations without touching retained archive/journal authority.

### Acceptance

Inject failures after multiple distinct action boundaries for cleanup, dedup, archive reclaim/create and restore. Fresh-process audit inspection agrees with actual filesystem terminality. Audit pruning cannot delete catalog/manifest/blob/nonterminal journal authority.

---

## 12. IR13-12 — CampaignStore maintenance is a separately authorized owner action, not an unconditional cleanup tail

### Concern and evidence

R12 correctly found unconditional VACUUM. A deeper issue is that the current command invokes `_compact_campaign_state(...)` after `StorageExecutor.apply(...)` regardless of whether cleanup completed, partially executed, or was refused. That maintenance is not represented in the cleanup plan and can mutate CampaignStore diagnostic state even when the primary plan was stale/refused.

### Required end state

1. Diagnostic event pruning/SQLite optimization/VACUUM is an explicit CampaignStore-owner maintenance action in the operation intention/result, or a separate owner-local maintenance plan invoked by cleanup.
2. A cleanup refused before mutation cannot piggyback unplanned database mutation.
3. Cheap event-retention pruning and expensive file rewrite are separate decisions.
4. VACUUM runs only under the R12 measurable-benefit predicate, owner-supported SQLite serialization, storage admission, and restart-equivalence checks.
5. If no file cleanup candidates exist but database maintenance independently meets its owner policy, it may be the sole explicitly planned owner-maintenance action.
6. Cleanup correctness never depends on maintenance success.
7. Maintenance execution participates in the shared durable audit when it actually changes persistent state.

### Acceptance

- stale/refused cleanup leaves CampaignStore unchanged;
- partial cleanup does not silently perform an unrelated database rewrite unless that maintenance action was independently authorized by the current plan/state;
- compact/no-excess DB skips VACUUM;
- benefit-positive synthetic DB compacts safely under real CampaignStore locking;
- scientific/currentness records remain identical except explicitly bounded diagnostic event history and physical layout.

---

## 13. IR13-13 — normal report must be bounded end-to-end, not merely remove one physical tree walk

### Concern

R12-B8 removes recursive size scans from normal reporting, but normal-report cost also includes semantic owner adapters. A nominally read-only P5/P7 resolver that reconstructs a full session, creates stores, scans checkpoint trees, or invokes expensive validation can still make `storage report` scale with historical bulk and violate the S4 fast-owner-inventory requirement.

### Required end state

1. Normal report's **semantic owner resolution plus physical metadata work** is bounded independently of descendant bulk-file count whenever current owners expose compact pointers/manifests/state sufficient to answer ownership.
2. Use side-effect-free current pointer/object/state reads and compact owner indexes/manifests where available.
3. Normal report must not train, evaluate, rebuild caches, scan all checkpoints, or re-materialize large scientific state merely to describe ownership.
4. Stronger validation required for a consequential mutation may occur during planning/apply; report itself remains advisory and cheap.
5. Exact recursive physical totals remain a deep-audit responsibility.
6. Deep audit obeys the actual entry/resource bound from IR13-2.

### Representative evidence

The revised S4 reporting benchmark must exercise real P3/P4/P5/P7 owner adapters/currentness over bounded numerical fakes below those owners. A fixture containing only an orphan historical directory that bypasses semantic owners cannot establish owner-report scaling.

Record at minimum:

- filesystem-entry visits/read count or another direct work metric;
- cold and warm wall time;
- owner-state identity/fixture size;
- deep-audit traversal count for contrast.

No universal speedup ratio is frozen; the required property is the architectural scaling separation and truthful labeling.

---

## 14. IR13-14 — complete the owner census; known campaign roots cannot disappear from reporting merely because they are non-reclaimable

### Concern

Revision 2 S0 explicitly included results, generated views, shared model/export/runtime helpers, and other campaign roots. The current owner adapters focus on CampaignStore/P1/P2/P3/P4/P5/P7/storage and can omit known campaign-owned `results/`/generated-view/helper families entirely. Omitting a family is safe for deletion only by accident; it is not a complete owner inventory or truthful report.

### Required end state

1. Re-run the S0 census for every known persistent/scratch family produced or consumed by the current campaign/storage implementation, including `results/`, generated current views, wrappers/exports/runtime helpers, historical compatibility residue that still exists in supported campaigns, and storage-owned transient state.
2. Every known campaign-owned family appears as an owner view or an explicit **unclassified/ambiguous retained** family.
3. Absence from owner views is never interpreted as positive reclaimability.
4. Arbitrary unknown files in the workspace are not automatically treated as campaign-owned; report them as ambiguous/unknown where visible and retain them.
5. Path-family labels may support advisory physical accounting but cannot grant mutation.
6. Normal report may say size unknown/bounded for these families; deep audit supplies exact physical accounting when requested and admitted.

### Acceptance

- representative current campaign tree accounts for every known top-level/internal family semantically;
- an injected unknown workspace file/tree is reported ambiguous/retained and never becomes a cleanup/archive/dedup candidate;
- generated results/views remain restart/currentness-neutral unless their real owner says otherwise.

---

## 15. IR13-15 — terminal restore journals and mutable archive catalog fields need bounded/create-once lifecycle semantics

### 15.1 Restore journals

R12 correctly protects nonterminal restore recovery state, but current storage ownership can blanket-protect the entire journal directory. Terminal restore journals are no longer restart authority and would therefore grow without bound across repeated restores.

Required end state:

- nonterminal restore journal/attempt state is recovery-critical;
- after terminal canonical-byte authentication and terminal receipt publication, the journal becomes bounded diagnostic evidence and may be retired under storage-owner policy;
- journal retirement never removes the retained archive catalog/manifest/blob;
- repeated restores cannot create unbounded unreclaimable terminal journal state.

### 15.2 Catalog immutable versus mutable fields

R12-B6 requires immutable archive representations, but the catalog entry also needs field-level monotonicity.

For one retained representation identity, create-once/validate-existing fields include at minimum:

- representation/archive identity;
- immutable manifest identity/locator;
- immutable blob locator/digest/size;
- represented member/lineage identity sufficient to locate the representation.

A later update for the same representation may change only explicitly operational fields such as hot-reclamation status/remaining-hot-member diagnostics and bounded timestamps/status metadata. It must not silently rewrite immutable representation fields.

Attempting to publish the same identity with different immutable fields fails closed and leaves the old catalog entry/archive independently verifiable.

### Acceptance

- repeated successful restores do not grow protected journals without bound;
- a nonterminal journal remains protected and resumable;
- changing blob/manifest digest/locator for an existing representation identity is rejected;
- updating only permitted reclamation status succeeds without altering immutable fields;
- crash during creation of another representation cannot invalidate the old one.

---

## 16. IR13-16 — current documentation/specification must be reconciled to the repaired product, not the old candidate

The current normative storage specification was authored from the implementation candidate and now contains claims invalidated by R12/R13. Final implementation closure requires all current public/durable surfaces to describe the repaired behavior rather than preserve implementation history.

At minimum reconcile:

- `docs/specs/training_data/mlff_storage_management_spec.md`;
- architecture/manual storage sections;
- user guide and built-in guide/help;
- generated/default configuration comments and example config;
- README/current package behavior where storage is described;
- tests that encode current public semantics.

Required corrections include:

1. `apply` is current-invocation authorization only; config cannot authorize mutation or redirect action.
2. All non-apply storage commands are observational/side-effect-free by default.
3. Every consequential dry-run computes the same semantic intention that apply will freshly revalidate.
4. Frame-cache disposition matches the chosen R12 conservative-retain or real activity-lease implementation.
5. Remove the false generic claim that superseded generation alone proves no writer; preserve P3's specific accepted no-stale-write guarantee while documenting P5 liveness separately.
6. Dedup uses no persistent content store under this repair unless Design is explicitly reopened on evidence.
7. Archive representation and catalog immutable fields are create-once/validate-existing; retained authority is self-contained for future reclaim/restore.
8. Restore uses an exact owner-bound plan and touched-owner synchronization.
9. Normal report uses bounded semantic/physical metadata; deep audit is exact only if it completes within its explicit resource bound.
10. Specialized consequential paths participate in the shared durable audit.
11. CampaignStore maintenance is benefit-gated and independently authorized, not an automatic cleanup tail.
12. Current policy keys/action-scoped identity reflect actual behavior; remove dead/decorative policy knobs.
13. Nested mount ambiguity retains.
14. Terminal restore journal retention is bounded.

Documentation compatibility is not a reason to retain contradictory current wording.

---

## 17. Amendments to the R12 implementation stages

Do not add another parallel lifecycle or restart accepted P1-P7 work. Fold these corrections into the existing R12-S0 -> R12-S4 sequence.

### R12-S0 additions — authority, graph, liveness, trust and census closure

Before executable repair proceeds, establish:

- action/tier/apply precedence and invocation-local authorization;
- action-scoped policy field mapping and removal/implementation of dead knobs;
- side-effect-free read-only owner/store/control-plane open paths;
- owner graph uniqueness/dependency-integrity rule;
- touched-generation synchronization derivation and one lock order;
- P5/frame-cache liveness seam or conservative retention;
- direct hardlink dedup realization and closed-hardlink-ownership rule;
- nested mount trust boundary;
- complete known campaign-family census;
- archive retained-authority self-containment;
- terminal journal lifecycle and catalog immutable-field set;
- conservative peak byte/inode admission model;
- CampaignStore maintenance decision owner.

**Gate:** no consequential family/action remains positively mutable while authorization source, graph closure, currentness, active use, touched-owner synchronization, filesystem ownership/mount boundary, or peak-resource feasibility is ambiguous.

### R12-S1 additions — canonical plan/policy/synchronization core

Along with the existing archive/dedup plan repairs:

- make apply invocation-local and action/tier semantics non-redirectable;
- produce action-scoped effective policy identities;
- make every consequential dry-run side-effect-free but plan-equivalent;
- implement exact create/reclaim/**restore**/dedup intentions;
- derive synchronization from every touched owner generation;
- enforce one lock order;
- validate owner graph integrity before positive planning;
- include conservative admission observations/bounds;
- make retained archive action metadata sufficient for future fresh-process planning.

**Stage-local acceptance:** R12 stale-plan/root-widening cases plus config-apply/action-redirect rejection, read-only tree invariance, owner-graph corruption refusal, touched-historical-generation synchronization, restore-plan owner-advance refusal, and resource-bound refusal.

### R12-S2 additions — liveness, dedup simplicity, archive/control-plane lifecycle and trust boundary

Along with R12 P5/frame-cache/archive representation repair:

- use direct hardlink aliasing; remove persistent CAS lifecycle from the target product;
- close unknown external-hardlink canonical-source risk;
- enforce nested-mount non-traversal;
- make archive representation/catalog immutable fields create-once;
- make terminal journal retention bounded and nonterminal journal state protected;
- close incomplete archive residue lifecycle without weakening retained archive authority;
- ensure every specialized mutation emits truthful shared audit and audit retention applies uniformly.

**Stage-local acceptance:** real P5/storage race + lock-order no-deadlock; external-hardlink counterfactual; nested-mount traversal refusal; archive re-encoding crash; journal lifecycle; partial specialized-operation audit; legacy content-store residue migration if present.

### R12-S3 additions — reporting, maintenance and public truth

Along with R12 normal-report/VACUUM repairs:

- normal report is side-effect-free and bounded end-to-end across semantic adapters and physical metadata;
- deep audit enforces actual entry/resource bounds;
- finish the known-family census/reporting contract;
- CampaignStore maintenance is independently planned/authorized and cannot run after a refused primary cleanup merely as a tail call;
- audit DB maintenance when performed;
- rerun representative owner-aware reporting benchmark;
- reconcile specification, architecture, guide/help/config/README to the final semantics.

**Stage-local acceptance:** report/dry-run state-invariance; owner-aware scaling instrumentation; deep-audit limit; complete/ambiguous family reporting; compact/no-op and benefit-positive SQLite maintenance; refused-cleanup-no-DB-mutation; docs/config/help parity.

### R12-S4 additions — assembled real-owner closure

The final assembled candidate must additionally exercise:

- persisted `apply=true`/action redirect cannot authorize or redirect a command;
- all non-apply storage surfaces leave managed state unchanged;
- duplicate/missing owner dependency fails closed;
- historical touched generation receives its own owner synchronization;
- P5 execution -> publication transition races storage without deadlock;
- restore plan becomes stale on owner advancement with unchanged bytes;
- fresh-process archive reclaim/restore planning succeeds without advisory plan/result files;
- direct dedup frees physical storage naturally when the last alias is removed;
- external hardlink cannot become the shared canonical inode;
- nested mount is not traversed;
- many-small-file archive/restore admission is conservative;
- archive/dedup/restore partial audit is truthful;
- refused cleanup does not mutate CampaignStore maintenance state;
- terminal journals are bounded; nonterminal journal remains protected;
- immutable catalog fields reject conflicting rewrite;
- normal report remains bounded through real owner adapters;
- known/unknown campaign families are truthfully accounted/retained.

Then re-derive the complete affected surface and run fresh final affected regression/integration and repository-required checks exactly as R12 already requires.

---

## 18. Implementation authority after this closure review

### Frozen

In addition to all unaffected Revision-2/final-closure/R11/R12 decisions:

- Apply authority exists only in the current explicit invocation; persistent config/state cannot authorize a mutation or redirect the requested action.
- Effective plan policy identity is action-scoped and every public policy knob has real behavior or is removed/rejected.
- Non-apply report/list/verify/planning/dry-run paths are side-effect-free with respect to managed campaign/owner/cache/control-plane state.
- Consequential planning requires a valid unique owner graph with all required dependency edges resolved.
- Owner synchronization covers every touched artifact generation and follows one deadlock-free lock order.
- Dedup uses direct owner-certified same-filesystem hardlink aliasing; no persistent dedup content store is part of the accepted target product.
- A canonical hardlink source cannot carry unknown external hardlink ownership.
- Restore is governed by an exact owner-bound restore plan and fresh under-synchronization revalidation.
- Retained archive authority is self-contained enough for future fresh-process reclaim/restore planning.
- Nested mount boundaries are not traversed implicitly by storage operations.
- Admission conservatively accounts for peak bytes, inode/directory entries, container/staging/atomic-publication amplification on every receiving filesystem.
- Every applied consequential storage mutation participates in one truthful durable storage audit; read-only/dry-run does not.
- CampaignStore maintenance is a separately authorized owner action; refused cleanup cannot trigger unplanned DB mutation.
- Normal report is bounded end-to-end; deep exact accounting is explicit and resource-bounded.
- Known campaign families are represented or explicitly ambiguous/retained; omission never grants mutation.
- Nonterminal restore journals are recovery authority; terminal journals are bounded diagnostic evidence.
- Immutable archive representation/catalog fields are create-once/validate-existing; only explicitly operational status fields may update.
- Current normative documentation must describe these repaired semantics.

### Delegated

- Exact read-only CampaignStore/owner-adapter API shape.
- Exact representation of action-scoped policy subsets.
- Exact deterministic cache-cap selection order among equally eligible owner artifacts.
- Exact owner graph validation implementation.
- Exact lock primitive/order, provided one common cycle-free order is used by storage and owners.
- Exact mount-boundary detection implementation per supported platform, provided ambiguity retains and nested mounts are not crossed.
- Exact conservative tar/container byte/inode upper-bound formula.
- Exact audit record schema/details beyond the required truthful operational facts.
- Exact terminal-journal retention count/time policy, provided it is bounded and nonterminal recovery state is never lost.
- Exact representation of retained archive action/member-to-owner mapping.
- Exact normal-report estimate/unknown presentation.

### Reopen only on evidence

Reopen only the affected storage surface if evidence demonstrates:

1. a supported production requirement genuinely needs a persistent dedup CAS and direct aliasing cannot meet it;
2. a required nested mounted subtree must be storage-managed and therefore needs explicit mount-level ownership semantics;
3. P5/frame-cache liveness cannot be exposed or conservatively retained without a material owner lifecycle redesign;
4. a required archive format cannot provide a conservative feasible admission bound or immutable representation model;
5. side-effect-free owner observation is impossible without changing a frozen currentness owner contract;
6. action-scoped exact owner identity cannot be derived without duplicating scientific authority.

Do not weaken owner/currentness/restart/security/resource semantics to avoid a reopen trigger.

---

## 19. Final handoff closure

The current repair contract is the supplied composed set:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md` for archive locator/crash-durability constraints;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md` for R12 implementation findings;
5. this `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md` for the final repair-plan corrections;
6. the current authority pointer naming this set.

Snapshot-loss counterfactual: loss of Git history, prior conversation, previous review prose, and advisory result files does not remove any still-binding task-specific repair requirement. The composed supplied set states the protected concerns, corrected end states, real-owner acceptance boundaries, delegated mechanics and redesign triggers required to implement the repair.

**Disposition:** the storage workplan remains **reopened**, but the repair design is now closure-reviewed and implementation-ready. Resume at R12-S0 with the additions above. Final PASS/closure still requires a new executable candidate plus executed stage-local/final affected regression and real-owner integration evidence. Full external-DFT, long GPU, and environment-specific HPC/storage qualification remain deferred.