---
kind: implementation-review-rework-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R12
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
review_date: 2026-09-01
reviewed_candidate_head: 86ca3aab960c11a97e0c659f13d342c858c41ae8
reviewed_candidate_tree: 195db51777ece1d61141d6f404a776eba92d2bae
reviewed_executable_commit: 53edc1c75c5b7c9df8f414914534ce915c34f303
reviewed_executable_tree: 8d24e6326b67c38e69a1fe1383be7b975788cac5
review_verdict: NO-PASS
scope: bounded repair of consequential storage authorization, owner liveness, storage-native lifecycle, exact plan identity, fast reporting, compaction policy, and functional acceptance; no P1-P7 scientific redesign
precedence: this amendment reopens only the implementation surfaces named below and composes with STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md, STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md, and AUTHORITY_REVISION_11.md; all unaffected frozen requirements remain binding
---

# Storage/I-O reset implementation review — reopen 1

## 0. Independent review disposition

The reviewed implementation is **NO-PASS**. The global owner-driven design remains valid and is not reopened. The candidate implemented several accepted mechanisms correctly, but consequential archive/dedup/cache paths still contain authority and liveness gaps that can mutate bytes without satisfying the frozen owner-bound plan/revalidation contract.

This is implementation rework, not a new storage architecture. Preserve the accepted implementation wherever it already satisfies the contract.

### Reviewed source identity

```text
implementation commit  53edc1c75c5b7c9df8f414914534ce915c34f303
implementation tree    8d24e6326b67c38e69a1fe1383be7b975788cac5
reviewed branch head    86ca3aab960c11a97e0c659f13d342c858c41ae8
reviewed head tree      195db51777ece1d61141d6f404a776eba92d2bae
```

The branch-head delta after the executable commit is documentation/PDF regeneration and does not repair the executable findings below.

### Accepted implementation that must be preserved

Do not discard or replace these working pieces unless a repair demonstrably requires a local refactor:

- `StorageInventorySnapshot` and its transitive current/restart dependency closure;
- post-attempt P7 -> P5 publication checkpoint retention and `waiting_for_reference` lineage retention;
- existing P5 and P7 object/pointer publication barriers;
- cleanup's `StoragePlan` -> storage lease -> owner barrier -> fresh resnapshot -> `revalidate_plan` -> physical boundary -> truthful audit shape;
- external-input containment, symlink safety, P3 retention fence, and P7 retention fence in `CampaignOwnershipBoundary`;
- canonical `StoragePolicy` resolution and policy identity;
- bounded archive member/path/type/expanded-byte verification and restore staging;
- archive locator containment beneath the storage-owned archive root;
- durable file/JSON publication helpers and parent-directory durability discipline;
- hardlink byte/metadata verification and atomic replacement mechanics;
- storage-native archive catalog/journal/audit ownership already implemented;
- deferred production-qualification boundary: no real external-DFT, long GPU, or HPC-scale qualification is added by this rework.

The frozen parent V7 workplan and accepted P1-P7 scientific/currentness semantics remain the verdict.

---

## 1. IR12-B1 — archive create/reclaim bypass the owner-bound plan and fresh semantic revalidation

### Blocking evidence

The current archive CLI derives an owner inventory and owner-declared archive candidates, but then constructs a `StoragePlan` with **zero actions**. The selected roots and archive members are not represented as plan actions and therefore are not bound to their exact filesystem identities or owner artifact identities.

`create_cold_archive(...)` then:

1. recursively collects and hashes selected members before acquiring the storage-operation lease or owner barriers;
2. performs admission before the mutation barrier;
3. acquires storage/P5/P7 barriers;
4. writes the archive and, after catalog publication, removes hot members using only the physical `CampaignOwnershipBoundary` plus size/hash checks.

It does **not** perform a fresh owner inventory, `revalidate_plan(...)`, or fresh archive-eligibility/dependency-closure check under the mutation barrier. `reclaim_archived_hot_members(...)` similarly replays an old manifest member set and physically authorizes those paths without re-establishing current semantic eligibility.

This violates the frozen sequence:

```text
owner inventory -> immutable owner-bound plan
 -> fresh owner/currentness/dependency/filesystem revalidation
 -> mutation
```

A member can become current/restart-required after the initial archive snapshot while retaining identical bytes. A size/hash check cannot detect that semantic change.

### Required end state

Every archive representation-changing step uses an exact owner-bound intention and fresh semantic authorization.

For **archive create**:

- bind every selected owner artifact/reclamation unit to an archive plan action or an equivalently exact immutable member-set plan;
- bind exact owner artifact identity, currentness/lineage identity, selected path/root, relevant filesystem identity, resolved policy identity, and admission observation;
- under the storage-operation lease and every required owner synchronization/no-use seam, rebuild the owner inventory and revalidate plan owner identity, dependency closure, archive eligibility, hot-path requirements, filesystem identity, and admission immediately before the point at which the archive/catalog can authorize hot removal;
- hashing/compression may occur outside a narrow owner barrier for economy only if the resulting archive remains non-authorizing until the fresh barrier-protected revalidation succeeds and the exact staged/published bytes reauthenticate against the bound plan;
- if eligibility or owner identity changed, keep hot bytes and require re-plan; never silently substitute a new candidate set.

For **archive reclaim**:

- an old archive/catalog proves only that cold bytes exist and authenticate;
- reconstruct the represented owner artifact identities from the archive manifest/catalog, derive a fresh owner inventory, and create/revalidate a current reclamation plan for the still-hot members;
- if a represented member is now current, restart-required, hot-path-required, owner-ambiguous, or otherwise no longer archive-reclaimable, retain it hot and report that refusal truthfully;
- catalog state alone never grants renewed deletion authority.

For **restore**:

- retain the existing bounded archive verification and conflict checks;
- before installing bytes, freshly establish that the destination identity remains a compatible historical/noncurrent owner location and acquire any owner execution/publication seam needed to prevent a concurrent writer from racing installation;
- restoration never promotes currentness.

### Acceptance evidence

Required real-owner tests:

1. plan an eligible historical archive; before apply, make a real descendant/current owner require one selected member without changing its bytes; apply/reclaim must refuse that member and leave it hot;
2. create an authenticated archive with some hot members remaining, advance owner state so one remaining member becomes protected, then `archive reclaim --apply`; protected member survives;
3. owner advancement that changes only semantic identity/currentness but not path/size/content invalidates archive apply;
4. archive/restore policy/admission changes are revalidated at the protected execution boundary;
5. source inspection proves archive create/reclaim/restore no longer treat the physical boundary or an old catalog as sufficient semantic authorization.

The real inventory/currentness owners may not be mocked for these claims. Expensive numerical producers remain replaceable below the owner boundary.

---

## 2. IR12-B2 — `archive create --root` can widen an eligible child into an ineligible parent

### Blocking evidence

The current root selector accepts a requested path when it is:

- exactly an eligible root;
- a descendant of an eligible root; **or**
- an ancestor/parent of an eligible root.

The last case widens authority. Example:

```text
owner-eligible: .mdstats/post-selection/g1/runs
requested:      .mdstats/post-selection/g1
```

The request is accepted because the eligible `runs` root lies under the requested parent. Archive collection then recursively walks the requested parent and can include `objects/`, even though the P5 owner did not mark those durable scientific-evidence objects archive-eligible. The later archive path does not re-check each member against the owner inventory, so this is a concrete destructive-authority escape.

### Required end state

- an operator-selected root may equal an eligible owner root or narrow to a descendant **inside** one eligible owner root;
- a requested ancestor of an eligible root is rejected;
- every collected archive member must map back to the exact eligible owner artifact/reclamation unit represented by the plan; physical containment alone is insufficient;
- a root spanning multiple owner artifacts is accepted only if the planner explicitly expands it into those individually owner-authorized artifacts; do not infer umbrella authority from one eligible descendant;
- selected archive lineage records only the artifact identities actually represented, not all globally eligible artifact IDs from the initial inventory.

### Acceptance evidence

- eligible `.../g1/runs` + requested `.../g1` rejects before archive creation;
- eligible root exact match succeeds;
- a safe descendant selection succeeds and cannot escape its eligible owner root;
- sibling/parent scientific evidence is byte-for-byte unchanged after attempted widened selection;
- manifest lineage lists only represented owner artifact identities.

---

## 3. IR12-B3 — dedup apply uses a stale snapshot instead of an immutable plan plus fresh owner revalidation

### Blocking evidence

`storage deduplicate` takes one `StorageInventorySnapshot`, scans and hashes owner-declared candidates, and constructs groups outside the mutation barrier. `deduplicate(...)` does not construct a `StoragePlan` or equivalent exact plan. Under the storage lease/barrier, `_apply_group(...)` calls `snapshot.path_protection(...)` on the **old snapshot**, then checks the physical boundary and current file bytes/metadata.

The old snapshot remains the semantic authorization. A candidate can become current/restart-required or otherwise lose dedup eligibility after grouping without changing its bytes or metadata.

### Required end state

Dedup has the same semantic authorization strength as cleanup:

```text
owner inventory
 -> exact immutable dedup plan/group plan
 -> storage lease + required owner no-write/publication barrier
 -> fresh owner inventory
 -> plan/closure/eligibility/filesystem revalidation
 -> exact byte + metadata reauthentication
 -> atomic hardlink replacement
```

The plan must bind every member of each group, its owner artifact identity, exact owner/currentness state identity, filesystem identity, expected content identity, and metadata contract.

Do not reuse an old snapshot's `path_protection()` result as apply-time authority.

### Acceptance evidence

- plan a dedup group, then advance a real owner so one member becomes protected while bytes remain identical; apply must refuse/re-plan rather than hardlink it;
- a same-generation owner pointer/head change that affects currentness invalidates the plan even when candidate paths do not change;
- mutation-time byte/metadata changes still fail closed;
- existing equal-bytes/incompatible-metadata and atomic-replace tests remain green;
- source inspection proves every dedup replacement is downstream of fresh owner/closure revalidation.

---

## 4. IR12-B4 — positive frame-cache eviction and historical P5 mutation lack a real non-use/liveness seam

### 4.1 Frame cache

The implementation correctly proves when `.mdstats/frame-cache` is exactly reconstructible from the authenticated DATA2 source authority, but then equates reconstructibility with `cache_evictable=True`.

No storage-shared active-consumer/rebuild lease was added. The owner mutation barrier currently covers P5/P7 publication barriers, not frame-cache readers/builders. A cache-tier cleanup can therefore remove the frame cache while another process is building or consuming it.

This is the exact liveness gap P6 intentionally deferred to this storage successor: reconstructibility proves capability recovery, not concurrent non-use.

### Required frame-cache end state

Choose the lowest-complexity engineering-valid option:

**Preferred conservative option:** keep frame-cache reconstructibility reporting but set positive eviction authority false until the existing runtime exposes a clean consumer/build liveness seam. `cache` may legitimately be a no-op for this family.

**Alternative only if cleanly justified:** add one owner-local frame-cache activity/publication mechanism shared by every reader/builder whose lifetime is actually material and by storage eviction. Storage must acquire exclusive eviction authority only when no active consumer/builder can require the files. Do not infer non-use from `prepare` completion, path age, PID disappearance, or stage names.

If mmap/file handles can outlive a narrow helper call, the liveness lifetime must cover the actual consumer lifetime; otherwise use the conservative option.

### 4.2 Historical P5 `runs/`

The implementation marks every superseded-generation P5 `runs/` root immediately `immutable=True`, `archive_eligible=True`, and `dedup_eligible=True`.

That is not a valid liveness proof. P5 explicitly permits long work to run under an older binding and only rejects stale publication when a newer target-size campaign revision has become current. The run materialization/checkpoint/training work occurs before that final currentness publication fence. Therefore a process that began while `g1` was current can still be writing `g1/runs/...` after `prepare` has made `g2` current.

Generation supersession alone does not prove the old run tree has no writer.

### Required P5 end state

- expose/reuse the smallest real P5 run-execution ownership seam that can prove a historical run tree has no active writer/consumer before archive or dedup mutation;
- if no clean seam exists, retain the affected P5 historical run family rather than inventing a pathname/PID/age heuristic;
- an owner-local run/generation activity lease is acceptable when it is acquired by the actual P5 execution path for the write/use lifetime and by storage for exclusive mutation;
- do not hold CampaignStore transactions across training, hashing, archive compression, or other long I/O/compute;
- P5 object->pointer publication barriers remain required but do not substitute for run-root liveness.

P3 is **not** reopened by this finding. Accepted P4/P3 evidence already establishes that a stale-generation P3 writer cannot mutate/touch P3 history. Preserve that owner contract and add only enough storage integration coverage to prove archive/dedup do not bypass it.

### Acceptance evidence

- frame-cache: race a real cache builder/consumer seam against cache eviction; eviction must block/refuse, or if conservative retention is chosen, the real cache tier must report it retained and perform no deletion;
- P5: pause real P5 work after it has begun writing a `g1` run root, advance the campaign to `g2`, invoke real archive/dedup planning/apply against `g1`; storage must not mutate the run tree while the stale P5 work remains active;
- after the owner truthfully proves the old run inactive/terminal and no current descendant requires it, historical eligibility may become positive;
- structural inspection proves superseded generation alone is not the no-writer predicate.

---

## 5. IR12-B5 — dedup content-store and incomplete archive representations lack a complete storage-native lifecycle

### Blocking evidence

Hardlink dedup creates a storage-native CAS beneath:

```text
.mdstats/storage/content-store/sha256/...
```

but the storage control-plane layout/owner views do not classify `content-store` at all. A `prune_orphan_content_objects(...)` helper exists, but the normal command/executor paths do not wire it into lifecycle cleanup.

Consequences:

- after canonical aliases are archived, deleted, or atomically replaced, the CAS object can become the only remaining hardlink and retain the full disk allocation indefinitely;
- archive may report a hot path removed while the unique inode bytes remain retained solely by the unowned CAS;
- storage-native cache/index growth is unbounded and invisible to owner-driven retention policy.

A related storage-native leak exists for failed archive publication: archive blobs/manifests created before catalog terminality are not individually classified for reclamation, while the whole archive directory is blanket protected as recovery-critical. An interrupted non-cataloged representation can therefore remain permanently retained.

### Required end state

Add explicit storage-owner lifecycle semantics for all storage-native bytes that are not durable retained archive authority.

**Content store:**

- explicit `storage:content_store` owner view;
- class it as storage-owned reusable representation/cache state, never scientific/currentness authority;
- retain objects while any deduplicated canonical alias needs them as a shared inode realization;
- when an object has no canonical alias and is not needed by an in-flight storage operation, reclaim it under the storage-operation lease using exact inode/link-count and ownership checks;
- wire orphan pruning into the operations that can remove final aliases (dedup retry/cleanup as appropriate, archive hot reclamation, restore/replacement lifecycle) rather than leaving a dead helper;
- report logical and unique physical bytes truthfully after dedup/archive interactions.

**Incomplete archive state:**

- distinguish cataloged retained archives from uncommitted blob/manifest staging or abandoned publication residue;
- an authenticated catalog/manifest/blob set is durable archive authority and retained;
- a blob/manifest with no catalog and no active archive operation may become owner-certified safe scratch after the storage owner's crash/publication ambiguity window or deterministic recovery check;
- never delete an artifact that could still complete a live archive publication.

### Acceptance evidence

- dedup two canonical files -> remove/archive both canonical aliases -> storage-owned CAS orphan is reclaimed and unique physical bytes actually fall;
- retain at least one canonical alias -> CAS object remains valid;
- interruption after archive blob publication but before catalog terminality never authorizes hot deletion and leaves state that a later invocation deterministically reuses/cleans without indefinite growth;
- retained cataloged archive remains discoverable/verifiable through safe/cache cleanup and fresh restart;
- no storage-native CAS/staging record can promote scientific currentness.

---

## 6. IR12-B6 — archive representation identity is not immutable across codec/serialization variants

### Blocking evidence

The current `archive_identity` is derived from member inventory + lineage, but not from codec/compression realization or the final archive digest. Archive blob/manifest paths are keyed by that identity. `durable_publish_bytes(...)` uses `os.replace`, so recreating the same logical archive identity can overwrite an already retained blob before its new manifest/catalog state is committed.

The benchmark itself creates the same logical member set under multiple codec/level choices. For same-suffix variants such as gzip levels, this can target the same identity/path. A crash after replacing a previously cataloged blob but before replacing/re-authenticating its manifest/catalog can make an already terminal retained archive fail verification.

A retained archive must not be invalidated by an attempted re-encoding of the same logical content.

### Required end state

Use an immutable representation identity.

Acceptable realizations include:

1. one final representation identity that binds the exact owner/member lineage plus schema/format/codec/level and final blob digest, with catalog entries pointing to immutable blob+manifest objects; or
2. separate logical-content identity and immutable representation identity, where a small crash-safe catalog pointer may select among already-authenticated immutable representations.

Regardless of realization:

- never overwrite the blob/manifest of a cataloged retained archive in place;
- repeated create of the exact same authenticated representation reuses/verifies it or creates a distinct immutable representation;
- different codec/level/serialization bytes cannot transiently corrupt an existing terminal representation;
- catalog pointer/status updates occur only after the new immutable representation is fully durable and independently authenticated.

### Acceptance evidence

- create and catalog archive A; attempt same logical member set with another codec/level and inject failure after new blob publication; archive A remains independently verifiable and restorable;
- repeat identical create is idempotent and does not rewrite a valid retained representation unnecessarily;
- catalog identity and manifest representation identity mismatch rejects.

---

## 7. IR12-B7 — `StoragePlan` owner binding does not bind the exact currentness identities required by the workplan

### Blocking evidence

`owner_binding_for(...)` hashes artifact IDs and classification flags/edges, but it does not bind the actual current P3 state/head identity, P4 selected binding/revision, P5 current publication/pointer digest, P7 current qualification/release pointer/record digest, or an equivalent owner-exposed state identity.

Same-generation owner advancement can therefore leave all artifact IDs, paths, classification flags, and dependency topology unchanged while the semantic currentness identity changed. The plan can remain apparently current even though the frozen contract requires owner advancement/currentness change to invalidate apply.

### Required end state

Add a derived, non-authoritative exact state identity to owner views or the owner-binding composition.

For each consequential owner surface, bind the real owner's canonical identity sufficient to detect relevant currentness advancement, for example as applicable:

- P3 current campaign revision/head/reconciliation identity;
- P4 selected/current-terminal binding/revision identity;
- P5 selected binding + current CV/final plan/publication pointer/content identities relevant to storage decisions;
- P7 current qualification/release/locked/waiting pointer/content identities and active-attempt retention identity relevant to storage decisions;
- storage control-plane catalog/journal identities when a plan depends on them.

Rules:

- derive these values from the real owner; do not create a second scientific registry;
- include only identities materially relevant to a plan so ordinary presentation/diagnostic changes do not create gratuitous staleness;
- exact dependency-closure and filesystem revalidation remain separate checks.

### Acceptance evidence

- same-generation P3/P5/P7 owner advancement with unchanged candidate path topology invalidates an unapplied plan when the change is relevant to that plan;
- irrelevant report formatting/audit append does not invalidate it;
- source inspection confirms owner identity comes from current owner records/pointers, not a storage-authored reconstruction of scientific state.

---

## 8. IR12-B8 — normal `storage report` still performs exact recursive subtree scans; deep audit is not the unique exact physical path

### Blocking evidence

The accepted design requires:

```text
normal report -> owner semantics + bounded/cheap physical metadata
deep audit    -> explicit exact recursive physical accounting
```

Current `build_owner_storage_report(...)` calls `_bounded_size(...)` for every owner view. For a directory, `_bounded_size(...)` recursively walks the complete subtree, inode-deduplicates it, and computes exact logical/allocated/unique bytes. Overlapping owner views cause the same physical tree to be rescanned and can double-count the same bytes across conceptual owners.

The committed S4 benchmark does not establish the required optimization. Its own result shows the nominal fast report slower than deep audit on the fixture:

```text
fast_owner_report_seconds = 0.032996...
deep_physical_audit_seconds = 0.022005...
ratio_deep_over_fast = 0.6669...
```

and explicitly states that no physical speedup is claimed.

That is a direct implementation drift from F9/S4, not merely benchmark noise.

### Required end state

Normal reporting must not recursively restat large owner trees merely to show semantics.

- derive semantic owner/current/restart/cache/archive status entirely from owner views;
- use only O(1), manifest/index-backed, stat-on-root, already-known owner metadata, or otherwise explicitly bounded physical measurements in normal report;
- if exact recursive logical/allocated/unique-inode bytes are requested, route to explicit `--deep` audit;
- do not present approximate/bounded numbers as exact physical totals; label estimate/known/unknown scope truthfully;
- avoid repeated recursive scans of overlapping owner roots;
- deep audit remains the exact recursive physical accounting path.

### Acceptance evidence

- structural check: normal-report code does not call recursive `rglob`, full `scandir` tree traversal, or `build_campaign_storage_report` over material owner trees;
- instrumented campaign-shaped fixture with large file count demonstrates normal report filesystem-entry visits are bounded independently of total descendant count, while deep audit visits the tree;
- owner semantic results remain correct when physical size is unknown/estimated;
- rerun representative S4 measurement and record cold/warm wall time plus filesystem-entry/read work; do not require a specific universal speedup ratio, but prove the architectural scaling separation.

---

## 9. IR12-B9 — CampaignStore VACUUM is unconditional after cleanup rather than benefit-gated

### Blocking evidence

After every applied safe/cache cleanup, `_compact_campaign_state(...)` admits temporary space and calls `CampaignStore.compact(...)`. `compact(...)` always bounds events, runs `PRAGMA optimize`, and then executes `VACUUM`.

The accepted plan requires CampaignStore compaction/VACUUM only under measurable benefit, lock safety, temporary-space admission, and restart equivalence. A full SQLite rewrite after every cleanup can dominate I/O even when there are no excess diagnostic events and no material reclaimable database space.

The policy contains a maximum event count but no implemented benefit predicate for whether VACUUM is worthwhile.

### Required end state

- separate cheap diagnostic event-retention maintenance from expensive file-rewrite/VACUUM;
- run VACUUM only when an owner-derived measurable predicate establishes material benefit (for example freelist/reclaimable-page ratio/bytes or an equivalent SQLite-owned signal) and storage admission succeeds;
- serialize/coordinate the rewrite through the CampaignStore owner's supported database locking semantics; do not rely on the obsolete assumption that the campaign parent is the sole writer;
- no cleanup correctness depends on VACUUM succeeding;
- report whether compaction was skipped and why.

### Acceptance evidence

- cleanup on a compact/no-excess database does not VACUUM;
- a synthetic database with material reclaimable pages/events crosses the configured/owner-derived threshold and compacts successfully under admission;
- concurrent CampaignStore activity produces safe SQLite serialization/refusal, never corruption;
- restart/currentness records remain identical before/after compaction aside from bounded diagnostic history and physical DB layout.

---

## 10. Acceptance blocker — executable regression/integration evidence is not established for the reviewed candidate

### Evidence state

The reviewed implementation commit has a successful GitHub Actions **docs** check only. No remote test/regression check is attached to the executable commit, and the documentation regeneration head intentionally skips CI. The repository contains substantial new test source, but test existence is not execution evidence.

The S4 benchmark result is useful bounded performance evidence; it is not functional regression/integration acceptance and in one area (normal-report scaling) actually exposes a remaining gap.

### Required closure evidence after repair

After the blocking source repairs above:

1. run focused tests for each IR12 repair;
2. run stage-local affected regression after the material authorization/liveness repair stage and after the archive/dedup/control-plane repair stage;
3. rerun all storage-reset core/integration tests on the assembled candidate;
4. rerun every affected P1/P3/P4/P5/P7 owner/restart/publication test surface touched by the repair;
5. run the repository-required CPU-safe broader/full suite when the final affected surface cannot be bounded confidently;
6. run docs/build/static checks required by the repository;
7. execute the real-owner assembled storage integration on the same final executable candidate;
8. record enough command/result identity that an independent reviewer can establish what actually ran. CI is acceptable; a concise committed implementation-evidence record is also acceptable if CI does not execute these suites.

A required check that did not execute is not a pass. Existing source-only tests do not satisfy this gate.

Full external-DFT, long GPU, and HPC production qualification remain deferred.

---

## 11. Additional corrections to close during the same repair

These do not require a wider redesign but must not remain as known drift:

### 11.1 Fail-closed downstream owner composition

If upstream current P3/P4 selected authority is unreadable, do not classify all P5 generations positively as historical/archive/dedup merely because `current_generation` became `None`. Record the downstream owner as unresolved/retained explicitly. Do not rely on an unrelated physical fence to rescue an incorrect semantic inventory.

### 11.2 Archive provenance for selected subsets

Archive lineage currently records all globally eligible artifact IDs even when the operator selects only a subset. Bind only the owner identities actually represented by the selected plan/member set.

### 11.3 Truthful architecture/docs

Current storage command documentation says every consequential command applies through the same `StorageExecutor`, while archive/dedup use specialized executors. After repair, document the invariant rather than a class name:

```text
all consequential paths share the same owner-bound plan,
fresh revalidation, synchronization, physical-boundary, admission,
and truthful-terminal semantics
```

Specialized low-level archive/dedup engines are acceptable beneath that shared authorization contract.

### 11.4 Reporting overlap

Normal report must not imply global additive physical totals by summing overlapping conceptual owner views. If an artifact is intentionally represented by multiple semantic views, either expose per-view logical attribution explicitly or use a deduplicated physical accounting source; do not silently double-count the same inode as independent storage consumption.

---

## 12. Reopened implementation stages

Do not restart accepted P1-P7 work. Reopen only the earliest storage stages affected by the findings.

### R12-S0 — owner liveness and exact identity recensus

Revisit only the new uncertainties exposed by implementation:

- exact currentness identity needed in plan binding for P3/P4/P5/P7;
- frame-cache active consumer/builder seam or explicit conservative retention;
- P5 run-root execution liveness after generation supersession;
- P3 accepted stale-generation no-write proof, incorporated as storage evidence rather than redesigned;
- storage content-store/incomplete-archive lifecycle owner;
- normal-report cheap metadata sources;
- SQLite measurable compaction predicate.

**Gate:** no family remains positively mutable while exact currentness or active-use synchronization is ambiguous.

### R12-S1 — unify consequential authorization

Repair `StoragePlan` owner identity and give archive create/reclaim/restore and dedup exact owner-bound plans/equivalent immutable action sets with fresh under-barrier resnapshot/revalidation and admission recheck.

Fix archive root narrowing in the same stage.

**Stage-local acceptance:** focused stale-plan/root-widening/dedup-owner-advance/archive-owner-advance tests plus affected storage plan/inventory/executor regression.

### R12-S2 — liveness and storage-native lifecycle

Close frame-cache and P5 run-root liveness; preserve P3's accepted stale-generation no-write contract. Add explicit content-store and incomplete-archive lifecycle/pruning. Make archive representations immutable across re-encoding.

**Stage-local acceptance:** real concurrent owner/storage counterfactuals, CAS physical-release tests, archive re-encoding crash test, and affected P3/P5/storage regression.

### R12-S3 — reporting and CampaignStore I/O correction

Make normal report nonrecursive/bounded and deep audit uniquely exact-recursive. Gate VACUUM on measurable owner-derived benefit and safe DB locking/admission.

**Stage-local acceptance:** scaling/instrumentation fixture, corrected bounded benchmark, compaction no-op/positive cases, CampaignStore restart regression.

### R12-S4 — assembled real-owner integration and final regression

On one final executable candidate:

- post-attempt P7 -> P5 checkpoint retention;
- `waiting_for_reference` lineage;
- P5 object-before-pointer race;
- stale-running historical P5 run vs archive/dedup;
- P3 stale-generation storage integration preserving its accepted no-write/history guarantee;
- frame-cache active-use/refusal or conservative-retention behavior;
- archive root-parent rejection;
- archive candidate becoming protected after planning;
- archive reclaim after owner protection changes;
- dedup candidate becoming protected after planning;
- content-store final-alias physical reclamation;
- archive re-encoding interruption preserving old retained representation;
- historical archive explicit restore without currentness promotion;
- policy/currentness stale-plan refusal;
- partial-operation retry truthfulness;
- fresh-process archive catalog discovery/verification.

Then re-derive the complete affected surface and run fresh final affected regression/integration plus repository-required checks.

---

## 13. Implementation authority

### Frozen

- The parent V7 scientific/architectural verdict and all accepted P1-P7 semantics.
- Revision-2 + final-closure + revision-11 storage design decisions not explicitly corrected here.
- Transitive cross-owner retention closure.
- External input/symlink containment and fail-toward-retention semantics.
- No current scientific/currentness loader becomes transparently archive-aware.
- Every consequential mutation is owner-bound, exact-state-bound, race/liveness-safe, freshly revalidated, physically guarded, resource-admitted, and truthfully terminal.
- Physical identity/content equality never substitutes for current semantic authorization.
- Superseded generation alone is not a generic active-writer/liveness proof; use the real owner's guarantee or retain.
- Archive representations already cataloged as retained may not be destructively overwritten in place.
- Storage-native caches/CAS/staging have explicit lifecycle ownership and cannot grow without bound.
- Normal report is operationally cheap/bounded; exact recursive physical accounting belongs to explicit deep audit.
- VACUUM is benefit-gated rather than unconditional cleanup overhead.
- Functional acceptance requires executed regression/integration evidence; production qualification remains separate and deferred.

### Delegated

- Exact data structure used for archive/dedup action plans, provided it carries all frozen identity/revalidation semantics.
- Exact owner-local P5 run liveness primitive.
- Whether frame cache receives a clean activity lease or remains non-evictable.
- Exact storage CAS/incomplete-archive grace/recovery representation.
- Logical archive identity versus separate immutable representation identity.
- Exact owner-state identity fields, provided they come from real owners and detect relevant currentness advancement.
- Exact nonrecursive physical-size presentation in normal report.
- Exact SQLite measurable-benefit threshold, provided it is owner-derived/configurable as appropriate and validated by representative evidence.

### Reopen only on evidence

Reopen only the affected design surface if implementation evidence proves that:

- P5 run liveness cannot be exposed without a material P5 lifecycle redesign;
- current storage feasibility requires transparent cold resolution beneath current P1-P7 owners;
- immutable archive representation cannot be supported on a required filesystem/format;
- meaningful frame-cache eviction requires a materially different cache ownership model;
- exact currentness binding cannot be derived without duplicating scientific authority.

Until such evidence exists, retain ambiguous artifacts rather than weakening owner safety.

---

## 14. Handoff closure

The current rework contract is the composed supplied set:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md` for the final archive locator/durability corrections;
4. this `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md`;
5. the current authority pointer that names this amendment.

The snapshot-loss counterfactual is closed for this rework: the blocking defects, required corrected end states, real-owner acceptance boundaries, preserved accepted implementation, and redesign triggers are all present in the supplied current authority set. Prior conversation/review history is not required to implement the repair.

**Disposition:** reopen the storage workplan at R12-S0. Do not close until R12-S4 functional/conformance evidence passes independent review.