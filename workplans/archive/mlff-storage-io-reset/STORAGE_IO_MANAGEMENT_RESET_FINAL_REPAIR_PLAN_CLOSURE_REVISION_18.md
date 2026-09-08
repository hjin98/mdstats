---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R18
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
amended_date: 2026-09-01
reviewed_authority_head: a5f5d1c3d721df2e0ca3a6bd06745c129c8b7e72
reviewed_authority_tree: c9e098e54299e252e93a30aee956bc89081f6c6c
reviewed_executable_commit: 2e6a2768341f75a87430d1313b7d64a1e85dfd04
reviewed_executable_tree: 681ed2b915bb29f05505eef87fcc83cf8e1c4b99
scope: final independent challenge of the Revision-17 repair contract; close P5 completion-proof/report-scaling and directory-topology contradictions, cross-process VACUUM serialization, audit-stream publication/retention races and realistic failure semantics, and dedup staging liveness/cleanup authority without reopening the owner-driven storage architecture or P1-P7 science
precedence: this amendment composes with the complete Revision-17 supplied contract; where it tightens P5 completion-proof representation, closed-subtree topology, CampaignStore maintenance serialization, audit publication/retention, dedup staging recovery, or final evidence identity, this amendment controls; all unaffected R11-R17 requirements remain binding
---

# Storage/I-O reset repair-plan final closure — revision 18

## 0. Final plan-challenge disposition

Revision 17 correctly reopens the executable candidate and identifies the remaining source defects, but one more independent **workplan** challenge found four material handoff gaps plus one acceptance-identity clarification. They are contract defects: an implementation could follow Revision 17 literally and still violate the bounded-report scaling contract, R14 recursive-ownership semantics, supported cross-process CampaignStore concurrency, or truthful durable-audit retention.

No new storage architecture is required. The fixes below are bounded refinements of the already accepted P5 owner proof, CampaignStore maintenance owner, storage audit owner, and storage staging owner.

The executable candidate remains NO-PASS:

```text
commit 2e6a2768341f75a87430d1313b7d64a1e85dfd04
tree   681ed2b915bb29f05505eef87fcc83cf8e1c4b99
```

No target-size, P2 statistical, P3/P4 currentness, P5 CV/final-production scientific, P7 qualification/locked/release, or frozen parent V7 decision is reopened.

---

## 1. IR18-1 — P5 completion authority must be both bounded for reporting and complete for destructive certification

### Gap in Revision 17

Revision 17 correctly requires the retained P5 completion anchor to be immutable, validated, and authoritative after terminal evidence goes cold. It also requires normal `storage report` to consume that validated anchor while preserving the earlier invariant that normal report cost is bounded independently of descendant bulk.

Those requirements conflict if the same JSON anchor contains the complete `members` list and its integrity digest. The member list is O(number of run descendants); reading/parsing/hashing it in every normal report makes report cost scale with run bulk even without a filesystem walk.

A second closure hole remains from R14: the current member concept is file-only. A recursive delete removes directory nodes too. An unexpected **empty directory** can therefore disappear under `rmtree` even though no recorded file path proves that directory was owner-created. R14 requires every disappearing descendant to be covered.

Finally, repeated publication after cold reclamation needs explicit semantics: once immutable completion authority exists, the owner must not recompute the original member set from a deliberately depleted hot tree and then call the legitimate cold absence a conflicting publication.

### Frozen end state

P5 exposes one logical terminal-completion proof with two cost classes:

1. a **compact retained completion anchor** whose size and validation work are O(1) in descendant count; and
2. an **immutable full member/topology manifest** used only where exact closed-subtree authority is required.

A separate small anchor file plus full manifest is the preferred realization. An equivalent representation is acceptable only if normal reporting can validate completion without reading/hashing O(member-count) data.

Required semantics:

1. **Publication order:** real terminal evidence durable -> full member/topology manifest durable and authenticated -> compact completion anchor durably published last. The compact anchor is the completion commit point.
2. Both records are versioned, create-once/create-or-verify P5 owner infrastructure. Neither is an archive member or safe/cache cleanup target while a retained archive/recovery path can need it.
3. The compact anchor binds at minimum the run identity, supported schema, terminal evidence kind(s), full-manifest content identity, member/topology count, and its own canonical integrity identity.
4. The full manifest records enough node topology to authorize recursive disappearance, not only regular-file names. It must distinguish at least regular files and directories; legitimate empty owner-created directories therefore have explicit ownership representation. Symlink/mount objects remain governed by the stronger existing refusal rules and are never absorbed merely by manifest membership.
5. Paths are unique canonical POSIX-relative paths with no absolute path, `..`, empty/aliasing component, anchor/manifest self-entry, or owner-lock entry. Parent/child topology is self-consistent.
6. Exact closed-subtree certification validates the compact anchor, authenticates the full manifest against the anchor, then compares the observed traversable node set against that manifest under R14. Any unexpected file **or directory**, including an empty directory, reduces/refuses recursive authority. Recorded nodes may be absent because represented members legitimately went cold.
7. Normal bounded reporting validates only the compact anchor plus O(1) existence/identity metadata needed to know the bound full manifest is present. It must not read/hash the full member manifest or walk the run. Reporting may describe exact destructive eligibility as provisional/potential until consequential certification; it must not imply the unexamined full manifest has been certified.
8. If the full manifest is missing or obviously mismatched by the compact metadata available at bounded cost, report surfaces unresolved/not-currently-certifiable state. A corruption requiring a full digest read may be detected only by consequential certification; report must not claim that such certification already happened.
9. **Repeated publication:** if a valid anchor+manifest already exist for the run, P5 verifies and reuses that immutable proof. It does not rescan the current hot tree to reconstruct the original member set after storage has legitimately moved members cold. First publication is the only point that derives the terminal member/topology set from the completed live run.
10. The completion proof grants only owner-completion/member-topology authority. It grants no scientific currentness/result verdict.

### Compatibility decision

The pre-acceptance single-file Revision-16/17 development anchor is **not** a released durable compatibility authority. The low-complexity default is therefore:

- old/superseded anchor schemas may be recognized for read-only diagnosis;
- they do **not** grant new consequential storage authority under the accepted product;
- do not add a migration subsystem merely to preserve NO-PASS development artifacts.

If repository/stakeholder evidence establishes that a supported persisted campaign using the old format must be preserved, reopen only this compatibility surface and define a transactional migration with an independent proof source. Do not invent a weak migration from pathname/existence inference.

### Acceptance

Use the real P5 owner reader/inventory/planner/executor.

- create a large closed run manifest and prove normal report does not open/read/hash the full member manifest and its cost/bytes touched remain bounded as descendant/member count grows;
- consequential planning does read/authenticate the full manifest and still catches member-manifest corruption;
- add an unexpected empty directory after terminal publication: exact certification refuses/reduces recursive authority and no `rmtree` removes it;
- add unexpected ordinary files/directories, symlink, and modeled mount: all existing R14 stronger cases remain green;
- a legitimate empty P5-owned directory recorded in the manifest remains certifiable;
- after one or more recorded members, including terminal evidence, go cold, call the P5 completion-publication/ensure path again: it validates the existing proof rather than deriving a smaller conflicting member set from the depleted tree;
- copied-for-wrong-run, digest-mismatched, malformed-path, duplicate-node, count-mismatch, and conflicting-publication cases fail closed;
- an old development-schema anchor cannot authorize archive/dedup/reclaim.

---

## 2. IR18-2 — the final VACUUM exclusion must be cross-process and must not leak beyond maintenance

### Gap in Revision 17

Revision 17 requires a final benefit observation after waiting for writer serialization, but it delegates the serialization primitive without freezing the concurrency scope. A process-local mutex could satisfy a same-process test while a second CLI/process still writes the same SQLite database between the final predicate and `VACUUM`.

Conversely, an SQLite `locking_mode=EXCLUSIVE` realization can accidentally persist on the CampaignStore's long-lived thread-local connection and block later legitimate writers after maintenance completes or fails.

### Frozen end state

1. The exclusion that protects the final VACUUM benefit predicate is **cross-process** for every supported CampaignStore writer of the same database. A Python/thread-only mutex is insufficient by itself.
2. Preferred realizations are either:
   - an SQLite locking/connection sequence that obtains and retains the required OS/database exclusion from the final predicate through `VACUUM`; or
   - one small process-safe owner lock shared by all product CampaignStore write transactions and VACUUM.
3. If an owner lock is used, every real CampaignStore write path that can race maintenance participates through a common owning primitive; do not patch only `event()` or only maintenance. The lock order relative to SQLite transactions is single and cycle-free.
4. If SQLite exclusive locking mode is used, use an operation-scoped/dedicated maintenance connection or explicitly restore/close it so exclusivity cannot leak into later ordinary CampaignStore use.
5. Under the acquired cross-process exclusion, perform the final benefit recheck and temporary-space admission recheck, then execute VACUUM without releasing the exclusion between them.
6. The exclusion is released on success, refusal, exception, cancellation, or simulated I/O failure. No stale process state may permanently block future writers.
7. Keep the critical section narrow: no archive hashing/compression/subtree scan or unrelated P5/P7 publication work while CampaignStore writers are excluded.

### Acceptance

- use a **second OS process** running a real CampaignStore writer, not only a second thread/connection, to invalidate a previously benefit-positive predicate while maintenance waits; maintenance rechecks after acquiring exclusion and skips/refuses the now-unworthy VACUUM;
- converse benefit-positive cross-process case rewrites successfully;
- after successful VACUUM and after injected VACUUM/predicate/admission failure, a fresh process can immediately obtain the normal CampaignStore writer path and commit;
- structural inspection proves no supported writer bypasses an introduced owner lock, if that realization is chosen;
- no process-local-only synchronization can make the acceptance test pass while cross-process behavior remains broken.

---

## 3. IR18-3 — audit publication and bounded retention are one serialized diagnostic-owner lifecycle

### Gap in Revision 17

Revision 17 fixes the stored `audit_published` flag but does not close the audit stream's own concurrency/recovery behavior. The current executor releases the storage-operation lease before normal `_audit()` and `prune_audit()`. `prune_audit()` reads the whole JSONL stream, rewrites a temporary file, and `os.replace()`s it without synchronization against another operation's append.

Two supported storage operations can therefore interleave as:

```text
A reads audit stream for pruning
B appends and fsyncs its successful record
A replaces audit stream from its stale snapshot
```

B can return `audit_published=true` and then immediately lose its newest record. Retention failure after an otherwise successful mutation can also currently escape as an unclassified exception. These violate the frozen truthful/consistently bounded audit contract.

Revision 17 also overstates what can be promised after a low-level append/fsync error: if the write reached the kernel but `fsync` reports failure, a complete record may later exist or may not. Diagnostic audit semantics must not pretend the caller can prove absence in that uncertainty window.

### Frozen end state

1. Audit **append plus retention** execute under one process-safe storage diagnostic-owner serialization boundary. Reuse/extend the existing storage-operation lease through audit publication and retention where practical; do not add a second audit lock hierarchy unless evidence shows the existing lease cannot cleanly own the lifecycle.
2. A normal consequential operation does not release that serialization before publishing its terminal audit record and applying bounded retention. Refused/partial outcomes follow one documented equivalent path; lock acquisition order remains cycle-free.
3. Retention cannot drop a concurrently/newly appended record that belongs within the newest `N` records. `audit_retention_records` has the same effective meaning under concurrency as it has serially.
4. Retention rewrite is crash-safe diagnostic maintenance: stage a complete retained stream, validate it, atomically replace, and persist the directory entry when supported. On retention failure, preserve the last valid stream rather than replacing it with a partial/empty rewrite.
5. Audit-retention failure does **not** roll back the primary mutation and does not turn a successfully published audit into `*_unaudited`. Surface the retention failure separately in the returned diagnostic detail/field and retry retention on a later operation; no second recovery database is required.
6. Successful append publishes one record whose stored payload says `audit_published=true`, empty audit failure, and the real terminal operation status/identity. Returned state is marked audited only after the append confirms success.
7. If append reports failure, the returned result is pessimistically `*_unaudited` with `audit_published=false`. Do **not** require proof that no complete line exists after an arbitrary post-write/fsync failure: a complete digest-valid tail record may or may not have survived. Such a record is diagnostic only and never scientific/recovery authority.
8. Audit readers/retention validate record framing/schema/event digest before using a record. A malformed/truncated/corrupt tail or stream prevents destructive retention rewrite of that stream and is surfaced diagnostically; it never affects P1-P7 currentness or archive authority.
9. Read-only commands still publish/prune no audit.

### Acceptance

- for every successful consequential action, persisted newest record and returned result agree on `audit_published=true`, status, plan/operation identity, and action;
- inject failure **before any audit bytes are written**: no record is added and returned result is unaudited;
- inject a post-write/pre-or-during-fsync failure: returned result remains unaudited; acceptance permits either a complete digest-valid tail record or no durable record, and neither outcome changes product state;
- deliberately interleave two real storage operations at append/retention boundaries with retention low enough to force pruning; no newest in-bound record is lost and final stream ordering/retention is deterministic under the chosen serialization order;
- inject retention rewrite failure after a successful append: primary mutation and published audit remain truthful, caller receives a retention warning/failure detail, and a later operation can retry pruning;
- corrupt/truncate an audit tail: report/read surfaces the diagnostic problem and pruning refuses to rewrite over it; consequential scientific/storage-owner decisions remain unaffected.

---

## 4. IR18-4 — dedup staging cleanup needs explicit liveness authority, not a new age/PID heuristic

### Gap in Revision 17

Revision 17 correctly moves the pre-rename hardlink out of the P5 subtree into storage-owned staging, but it says only that a fresh process can remove an abandoned entry with "no live operation." It does not freeze how that fact is established. An implementation could accidentally reintroduce PID/age/pathname heuristics that the storage reset explicitly retired, or race cleanup against a live dedup operation.

### Frozen end state

1. A dedup operation stages temporary hardlinks only inside an operation-identity subdirectory of the existing `.mdstats/storage/staging` owner, after same-filesystem validation.
2. That operation staging subtree is storage-owned temporary/scratch state under the control-plane exclusive-writer contract. No new persistent CAS, registry, or GC authority is introduced.
3. Supported storage operations remain serialized by the storage-operation lease. Therefore cleanup/recovery may call a dedup staging subtree abandoned only **after acquiring that lease** and establishing that no nonterminal storage journal/other existing storage recovery owner claims the subtree. No PID, age, mtime, process-table, or pathname-stage folklore grants reclamation authority.
4. A live dedup operation cannot race its staging subtree's cleanup because both use the same storage-operation serialization.
5. Cleanup of a stranded hardlink only unlinks/removes storage-owned staging names. It must never chmod/chown/xattr/write through the staging hardlink, because metadata/content mutation through a hardlink would mutate the canonical P5 inode.
6. Cleanup is idempotent and safe after a hard crash at any point before or after destination rename. If the destination was already replaced, removing a remaining staging alias simply drops the extra link.
7. Normal reporting accounts for abandoned/retained storage staging as storage-owned scratch rather than ambiguous P5 state; it does not need PID/age probing.

### Acceptance

- hold a real storage-operation lease in one process while another tries safe cleanup of dedup staging: cleanup waits/refuses and does not remove live staging;
- simulate fresh-process crash residue with no live lease; safe cleanup under the lease removes only storage staging and leaves canonical/destination bytes, mode, ownership and xattrs unchanged;
- simulate crash after destination replacement but before staging cleanup; retry/cleanup is idempotent and leaves the intended hardlink relation valid;
- assert no dedup-staging reclamation path reads PID/age/mtime as authority;
- cross-device staging refuses before creating an in-run fallback temp.

---

## 5. Final acceptance identity and evidence reuse

Revision 17's candidate-bound evidence rule remains correct, with this clarification:

- focused/stage/final functional evidence must correspond to the exact **final executable tree** after all R18 executable changes;
- a later generated-document/PDF-only successor commit does not invalidate already-green executable regression when a compare proves it changes no executable/config/test/runtime contract dimension, but affected docs/static checks must correspond to the final documented head;
- any executable/config/persistence/test-harness change that can affect a claim invalidates that claim's prior functional evidence and requires the appropriate rerun;
- source tests or benchmark JSON without executed command/CI results remain insufficient.

R18 adds these focused cases to the final set:

1. bounded compact P5 completion anchor versus full manifest scaling;
2. unexpected empty-directory topology closure;
3. repeated completion-publication after members have gone cold;
4. cross-process VACUUM predicate race and lock-release-after-failure;
5. concurrent audit append/retention plus retention-failure recovery;
6. audit post-write/fsync uncertainty semantics;
7. live-vs-abandoned dedup staging under the storage-operation lease.

All still-binding R12-R17 focused, affected-regression, real-owner integration, broader CPU-safe, static/docs/build, and final affected-surface requirements remain mandatory.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.

---

## 6. Stage mapping — keep R12-S0 -> R12-S4

Do not create another lifecycle.

### R12-S0

- freeze the compact completion-anchor + full member/topology-manifest contract and default old-schema REJECT posture;
- freeze cross-process VACUUM exclusion and operation-scoped release semantics;
- freeze one serialized audit append+retention lifecycle and realistic append-failure semantics;
- freeze dedup staging abandonment authority from the storage-operation lease, not PID/age.

### R12-S1

- implement/version the compact P5 anchor and full topology manifest with create-or-verify publication order;
- make exact P5 certification cover files **and directories** while bounded report reads only compact authority;
- implement the cross-process final CampaignStore maintenance exclusion;
- centralize dedup staging ownership/classification under the storage control-plane owner.

### R12-S2

- close VACUUM predicate/admission under the final exclusion and prove lock release on every terminal path;
- serialize successful/partial/refused audit publication and bounded retention, fix stored/returned truth, and make retention failure non-destructive/non-authoritative;
- move dedup pre-rename aliases to storage staging and close fresh-process cleanup/retry;
- preserve every conforming R15-R17 archive/restore/dedup/currentness/observation repair.

Run focused and stage-local affected regression before proceeding.

### R12-S3

Reconcile storage specification, architecture, user guide/help/config comments for:

- compact P5 completion authority versus exact topology certification;
- bounded report's provisional-versus-exact certification semantics;
- cross-process CampaignStore maintenance serialization;
- serialized audit publication/retention and pessimistic append-failure semantics;
- storage-owned dedup staging recovery.

Rerun bounded report/deep-audit benchmark with a sufficiently large member manifest to demonstrate report work remains independent of member count.

### R12-S4

Run every R12-R18 counterfactual, final contract reconciliation, final affected-surface derivation, fresh final affected regression, assembled real-owner integration, and required broader/static/docs checks on the final candidate identity described above.

---

## 7. Implementation authority

### Frozen

In addition to all unaffected R11-R17 authority:

- P5 terminal completion has a bounded compact commit record plus exact immutable topology authority; normal reporting never pays O(member-count) validation cost;
- recursive closed-subtree authority covers directory nodes as well as regular files, so an unexpected empty directory can never disappear under an authorized `rmtree`;
- an existing valid P5 completion proof is verified/reused after cold movement rather than recomputed from the depleted hot tree;
- pre-acceptance old P5 anchor schemas do not grant consequential authority by default;
- VACUUM's final predicate exclusion is cross-process and operation-scoped;
- audit append and retention are serialized as one diagnostic-owner lifecycle, retention cannot race away a newer accepted record, and arbitrary fsync failure is handled pessimistically rather than with an impossible proof-of-absence promise;
- dedup staging abandonment is established by the existing storage-operation/recovery ownership contract, never PID/age heuristics;
- final acceptance remains candidate-bound and proxy-proof at the real owner/process boundaries above.

### Delegated

- exact filenames/JSON layouts for compact anchor and full topology manifest;
- exact representation of topology entries, provided empty directories and every recursively disappearing node are coverable;
- exact SQLite versus owner-lock mechanism for cross-process maintenance exclusion;
- exact diagnostic field used to surface audit-retention failure;
- exact storage-staging subdirectory naming below operation identity;
- implementation-local refactoring needed to keep common CampaignStore writer/audit paths centralized without changing frozen P1-P7 semantics.

### Reopen only on evidence

Reopen only the affected surface if:

1. P5 cannot expose O(1)-cost completion authority separately from O(member-count) exact topology without changing scientific semantics;
2. supported cross-process SQLite behavior cannot provide a bounded final VACUUM exclusion without a materially broader CampaignStore ownership redesign;
3. the existing storage-operation lease cannot serialize audit append/retention without a new material lock hierarchy; or
4. storage-owned same-filesystem staging cannot support crash-recoverable hardlink replacement on a supported campaign layout.

Do not weaken bounded reporting, R14 recursive ownership, writer-race correctness, durable-audit truth, or crash recovery merely to avoid a reopen.

---

## 8. Handoff closure

With this amendment incorporated into the current supplied contract, the **repair plan is final-closure reviewed and implementation-ready**. The executable package remains **NO-PASS / reopened** until Implementation satisfies the complete composed R11-R18 authority and provides the required executed candidate-bound evidence.

No production-qualification expansion is introduced.