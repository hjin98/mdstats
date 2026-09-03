---
kind: implementation-review-rework-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R15
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
amended_date: 2026-09-01
reviewed_candidate_head: 0d91ce50d7ca7cad65657c90ba17a9ecfd0ad4ee
reviewed_candidate_tree: 81b314680f7333160081c07b08afc64025d22ba4
reviewed_executable_commit: e7cd824070a6bd7fb3fb83751d2dde185acf0c16
reviewed_executable_tree: 51bab072d871c9bcef8271b01def1f82c2cad3c5
review_verdict: NO-PASS
scope: independent implementation acceptance review against the complete revision-14 storage authority; preserve conforming R12-R14 work and repair only the remaining archive reauthentication, dedup synchronization/durability, restore parent identity, P5 partial-reclaim certification, CampaignStore maintenance/read-only enforcement, and final acceptance-evidence gaps
precedence: this amendment composes with STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md, STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md, AUTHORITY_REVISION_11.md, STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md, STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md, and STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md; where this amendment gives a more specific repair for the reviewed executable candidate it controls; all unaffected requirements remain binding
---

# Storage/I-O reset implementation review reopen — revision 15

## 0. Verdict and review identity

The implementation is **NO-PASS** against the complete Revision-14 authority. The global owner-driven architecture remains accepted and most earlier blockers are now substantially closed; the remaining defects are bounded implementation nonconformances and affected-surface consequences rather than a reason to redesign the subsystem.

Reviewed executable candidate:

```text
commit e7cd824070a6bd7fb3fb83751d2dde185acf0c16
tree   51bab072d871c9bcef8271b01def1f82c2cad3c5
```

Reviewed branch head:

```text
commit 0d91ce50d7ca7cad65657c90ba17a9ecfd0ad4ee
tree   81b314680f7333160081c07b08afc64025d22ba4
```

The head-only delta is regenerated documentation/PDF material and does not close the executable findings below.

### Conforming work to preserve

Do not reimplement the storage subsystem wholesale. Preserve unless a local compatible repair requires touching the mechanism:

- invocation-local `--apply` authority and rejection of persistent `apply`/`action` authority;
- action-scoped effective policy identity and policy/config normalization;
- observational command routing, non-creating control-plane open, and no default report/plan artifact deposition;
- transitive cross-owner dependency closure and owner-graph integrity checks;
- exact P3/P4/P5/P7 currentness identities in storage owner views;
- P5 run-activity lease on the real P5 execution path and common lock order;
- conservative frame-cache retention while no P1 consumer/builder liveness seam exists;
- Revision-14 closed-subtree versus container ownership and unexpected-descendant retention;
- archive root narrowing, per-member owner mapping, hostile archive bounds, locator containment, immutable representation identity, and create-once catalog immutable fields;
- direct hardlink deduplication with no persistent CAS and with closed external-link ownership checks;
- bounded normal owner report, explicit bounded deep audit, nonadditive accounting, and complete/ambiguous family census;
- terminal/nonterminal restore-journal distinction and uncataloged archive-residue ownership;
- pre-existing restore containers not being silently chmod-normalized;
- the extensive new core/integration regression source, subject to the missing cases and execution-evidence requirements below.

---

## 1. IR15-1 — reclaim and restore must reauthenticate the retained cold representation inside protected execution

### Concern and evidence

The current reclaim/restore commands authenticate the archive while constructing the plan, before `StorageExecutor.run(...)` acquires the storage-operation lease and owner synchronization. The already-read manifest is then passed into `archive_reclaim_engine(...)` or `archive_restore_engine(...)`.

Inside the protected executor window, the implementation fresh-resnapshots owners, revalidates the plan and admission, but does not reauthenticate the exact catalog/manifest/blob pair. In particular, `archive_reclaim_engine(...)` can delete still-hot files using the old manifest after the retained blob has disappeared or become corrupt between planning and execution.

The generic storage owner views for `storage:catalog` and `storage:archives` do not bind the exact retained representation bytes strongly enough to make ordinary owner-binding revalidation detect this corruption/removal.

This violates the frozen restore/reclaim order requiring current retained archive authority to be authenticated immediately before consequential mutation.

### Required end state

For archive hot reclaim and restore:

1. The plan binds the exact retained representation authority it intends to consume: representation identity plus immutable catalog/manifest identity and the expected blob digest/size/locator, or an equivalent immutable storage-owner identity.
2. After acquiring the storage-operation lease and every required owner synchronization seam, but before deleting any hot member or installing any restored member, re-read and reauthenticate the exact catalog entry, manifest, and blob from their canonical retained locations.
3. Confirm the reauthenticated member/owner mapping and immutable representation fields are the same ones the plan bound. Never substitute a different representation or updated member set silently.
4. Reclaim must perform **zero hot deletion** if the cold representation is missing, changed, unsupported, corrupt, or cannot be authenticated at this protected boundary.
5. Restore must perform **zero installation/staging publication that could become terminal** if the bound representation fails protected reauthentication.
6. Keep expensive archive verification outside broad scientific locks where possible only if an equivalent immutable storage-owner lease/identity makes the preverified representation unchangeable. In the current design no such separate immutable-file lease exists, so the final authentication must occur inside the protected consequential window.
7. Archive creation's already-correct authenticate-before-catalog-before-hot-delete ordering remains intact.

### Acceptance

Use the real storage planner/executor/control plane and owner synchronization.

- Build a valid reclaim plan while hot files and an authenticated archive exist; after planning but before executor application, delete or corrupt the archive blob. Apply must refuse and every still-hot file must remain byte-for-byte present. Catalog state must not be advanced to `complete`.
- Repeat with manifest or immutable catalog corruption/removal.
- Perform the equivalent restore race: plan successfully, corrupt/delete the retained representation before protected execution, and prove nothing is installed and no terminal restore receipt exists.
- Fresh-process retry after repairing/restoring valid cold authority may re-plan and proceed normally.

---

## 2. IR15-2 — dedup synchronization must include the canonical source owner/run, not only replacement destinations

### Concern and evidence

`build_dedup_plan(...)` creates one planned action per replacement path. The canonical source path and canonical owner identity live only inside the action binding. `synchronization_for(...)` derives P5 run-activity leases from each action path and its nominal owner view; it does not derive synchronization from the canonical source binding.

A dedup group may span multiple historical P5 run roots. If the canonical source is in run A and the replacement is in run B, storage can therefore hold B's run-activity lease while holding no lease for A. P5 explicitly permits a run started under an older selected binding to continue writing, so historical-generation status alone is not a no-writer proof.

The dedup engine hashes the canonical under the executor window and then hardlinks it. Without the canonical owner's liveness seam, the canonical can still be an active writer and the newly aliased replacement can inherit that writer.

### Required end state

1. Every filesystem object whose inode/content becomes authoritative for a dedup action participates in plan authorization and synchronization, including the canonical source.
2. The plan carries canonical owner artifact identity/currentness identity and enough source-path identity for `synchronization_for(...)` (or an equivalent canonical synchronization builder) to derive the canonical generation and P5 run-activity lease.
3. If canonical and replacements span several runs/generations, acquire all relevant activity/publication seams in the existing common deterministic order.
4. Under those seams, fresh-resnapshot and revalidate both canonical and replacement owner eligibility/currentness plus exact byte/metadata/link ownership before linking.
5. If any canonical source owner is active/unresolved/protected, retain duplicates rather than falling back to a different unplanned canonical silently.

### Acceptance

- Construct two real owner-certified historical P5 run roots with byte-identical eligible files, forcing the deterministic canonical into run A and a replacement into run B.
- Hold the real P5 run-activity lease for run A while launching public dedup apply. Dedup must block/refuse until A releases; it must not create the B alias while A is active.
- Exercise the reverse deterministic ordering and multiple replacements to prove all source/destination run seams are acquired without deadlock.
- Structural inspection must show canonical bindings feed synchronization derivation, not merely mutation-time byte hashing.

---

## 3. IR15-3 — restore must bind and revalidate exact existing parent-chain filesystem identity

### Concern and evidence

Revision 14 requires parent-chain ownership, symlink/mount containment, and **filesystem identity** to be revalidated under synchronization. The current restore plan records a directory action's parent only as a pathname and records no device/inode identity for the parent chain. For an absent destination the ordinary planned filesystem identity describes only the absence of that destination.

At mutation time the implementation checks that a parent is still a directory, is not a symlink, and does not cross a mount boundary. Replacing the planned parent directory with a new ordinary directory at the same path can therefore evade stale-plan detection.

The current changed-parent acceptance test substitutes a symlink. It does not establish the required same-type inode-replacement case.

### Required end state

1. The restore intention binds the exact relevant identity of every existing parent/container through which it will create/install a member. At minimum bind `(st_dev, st_ino, file type)` for the nearest existing parent; bind the relevant parent chain to the authorized owner/workspace root where a parent swap can redirect or change ownership semantics.
2. Bind mount identity/containment observations where material; do not replace the existing nested-mount checks.
3. Under the protected executor window, immediately before any `mkdir`, `os.replace`, reuse, or metadata application, verify the planned existing parent/container identities still match.
4. Same-path replacement by a different ordinary directory stales/refuses the restore even when mode, device, pathname, and non-symlink status look acceptable.
5. A parent created by this same restore is validated through the restore plan's own creation/postcondition chain rather than treated as an unknown pre-existing parent.
6. Continue to leave compatible pre-existing container metadata unchanged.

### Acceptance

- Plan a restore into an absent file/container beneath an existing directory; replace that parent with a new real directory at the same path and same mode before apply. The plan must refuse before installation and the replacement parent remains empty.
- Repeat for an intermediate parent in a deeper chain.
- Existing symlink and modeled nested-mount substitutions must continue to refuse.
- A restore-created parent followed by child installation succeeds and the created-parent postcondition is authenticated before terminal receipt.

---

## 4. IR15-4 — P5 closed-run certification must survive removal of any archived terminal member

### Concern and evidence

P5 now records a retained run-member manifest and correctly allows an individual recorded member to be absent because it may have moved into a cold archive. However, `certify_closed_post_selection_run_root(...)` first requires a hot `fold-acceptance.json` or `run-evidence.json` terminal record before it consults the retained member manifest.

Those terminal records are ordinary owner-recorded archive members. A partial archive hot reclamation can remove the terminal record while leaving other represented members hot. On a fresh process the next owner inventory then declares the run uncertified/not archive-eligible, so `archive reclaim` cannot resume the remaining hot-member deletion. This defeats the frozen interrupted-reclaim/fresh-process recovery contract.

### Required end state

After P5 terminal publication, the minimal hot owner infrastructure used to prove that a run is a completed closed subtree must remain valid after **any strict subset** of archive-represented members has been removed.

Choose the lower-complexity owner-correct realization:

- **preferred:** strengthen the retained P5 run-member manifest so it is immutable/authenticated terminal-completion authority written only after the actual terminal evidence is durable; certification may then use that manifest to prove completion even if the terminal evidence member itself has gone cold; or
- retain a minimal immutable P5 terminal marker as non-archiveable owner infrastructure, with a clear owner/schema/lifecycle.

Constraints:

1. Do not infer completion from generation, age, missing process, or pathname.
2. The retained terminal proof must not become a second scientific result; it certifies only that the owner finished and recorded the closed member set.
3. Unexpected descendants must still invalidate/reduce closed-subtree authority.
4. Restoring the archived terminal evidence must remain historical and must not alter currentness.

### Acceptance

- Build a historical P5 run with at least two archive-represented members, including the terminal fold/run evidence.
- Interrupt hot reclamation specifically **after the terminal evidence member has been deleted** while another represented hot member remains.
- Close/reopen the campaign in a fresh process; P5 must still certify the run from retained owner infrastructure and `archive reclaim --apply` must safely complete the remaining member(s).
- Perform explicit restore afterward and prove the historical owner evidence authenticates while remaining non-current.

---

## 5. IR15-5 — diagnostic-event pruning and SQLite VACUUM are still not separate maintenance decisions

### Concern and evidence

Revision 13 explicitly required cheap diagnostic-event retention and expensive SQLite rewrite to be separate decisions. Current `plan_campaign_state_maintenance(...)` considers maintenance worthwhile when **any** excess event exists. The maintenance engine then calls `CampaignStore.compact(...)`, whose implementation always performs:

```text
DELETE excess events
PRAGMA optimize
VACUUM
```

Thus one excess diagnostic event can cause a full database rewrite even when free-page bytes/fraction are below the configured rewrite thresholds. `CampaignStore.compact()` also still documents VACUUM as safe because “the campaign parent is the sole database writer”, precisely the concurrency assumption the repair authority prohibited relying on.

### Required end state

Separate the CampaignStore owner's maintenance decisions:

1. **event retention/pruning** — a cheap owner-local transaction when event count exceeds its configured bound;
2. **database rewrite/VACUUM** — an independently benefit-gated operation after the relevant pruning state is known.

Required consequences:

- Excess events alone authorize pruning, not VACUUM.
- After/independent of pruning, measure reclaimable pages/bytes/fraction through SQLite's owner state.
- VACUUM runs only when the configured reclaimable-byte or reclaimable-fraction threshold is met and temporary-space admission succeeds.
- Use explicit SQLite serialization/locking appropriate to the real CampaignStore owner. Do not rely on one parent process being the only writer; real campaign code can have concurrent owner readers/writers.
- A refused/stale file-cleanup plan cannot piggyback either maintenance mutation unless that maintenance action itself remains freshly authorized.
- Cleanup correctness is independent of pruning/VACUUM success.
- Plan/result/audit must truthfully distinguish whether events were pruned and whether VACUUM occurred.

### Acceptance

- Create `maximum_events + 1` (or another small excess) with reclaimable pages below both rewrite thresholds. Maintenance prunes events but proves VACUUM did not run.
- Create a synthetic DB with material reclaimable pages above the threshold; VACUUM executes under admitted owner serialization.
- Race maintenance against a real CampaignStore writer and prove clean serialization/refusal without corruption or scientific/currentness loss.
- Existing stale/refused-cleanup-no-maintenance test remains green.
- Update normative docs so “excess events” does not imply the rewrite itself is benefit-positive.

---

## 6. IR15-6 — observational CampaignStore must be enforced by SQLite read-only access, not convention

### Concern and evidence

`CampaignStore(create=False)` correctly avoids directory/schema creation and disables write-through receipt setup, but `_connect()` still opens the SQLite file through a normal read/write `sqlite3.connect(path)` connection. The `read_only` flag is not enforced by the connection and ordinary write methods do not reject observational stores.

Revision 13 required existing CampaignStore state to be opened **read-only** for inventory/report/planning. Relying on every nested owner resolver never accidentally calling a write path is weaker than that owner boundary and leaves a future regression able to mutate authoritative state during a command advertised as observational.

### Required end state

1. `CampaignStore(create=False)` uses a genuinely read-only SQLite connection, such as a correctly escaped SQLite URI with `mode=ro` and `uri=True`; `PRAGMA query_only=ON` may be used as an additional defense where appropriate.
2. The read-only open must not create the database, WAL/journal, schema rows, receipt cache, directories, or other managed state.
3. Writing methods invoked through a read-only store fail before committing any mutation. A clear CampaignStore error is preferable to a low-level ambiguous failure where practical.
4. Normal read semantics needed by owner inspection remain available; do not snapshot stale state in a way that defeats fresh currentness reads.
5. Consequential execution continues using the real writable owner store under the accepted synchronization.

### Acceptance

- Open a populated CampaignStore with `create=False`, then attempt representative writes (`set_stage`, `event`, `put_record`, transactional currentness update). Each must fail and authoritative database contents/currentness remain unchanged.
- Re-run every observational storage command and verify no managed topology/bytes/mtime/currentness/receipt changes.
- Reporting an uninitialized campaign still creates nothing.

---

## 7. IR15-7 — dedup hardlink replacement must reach the directory-entry durability boundary before completion/audit

### Concern and evidence

Current dedup apply creates a temporary hardlink and atomically replaces the duplicate path with `os.replace(...)`, then immediately records the action completed. Unlike durable unlink/archive/restore publication paths, it does not fsync the destination parent directory after the rename.

The frozen storage durability/audit contract requires downstream terminal/audit evidence to describe state that has crossed the required filesystem publication boundary. A power loss after the audit append but before the directory entry is durable can otherwise leave durable operational evidence disagreeing with the recovered filesystem representation.

### Required end state

1. After creating the temporary hardlink and atomically replacing the destination, persist the destination directory entry with the repository's established parent-directory fsync helper where supported.
2. Mark the dedup action complete and count reclaimed bytes only after that durability boundary succeeds.
3. Temporary-link cleanup is deterministic on failure and never removes the canonical or an unrelated alias.
4. A durability failure/interruption is truthful `partial`/failed operational evidence, never a fabricated complete action.
5. Idempotent retry still recognizes an already-aliased inode correctly.

### Acceptance

- Inject a failure at/around the parent-directory durability boundary after the atomic replace. The operation must not emit a durable `complete` audit claiming an unconfirmed action.
- Retry from the recovered/observed filesystem state and prove idempotent completion.
- Structural inspection verifies every dedup `os.replace()` publication is followed by the same directory durability discipline used elsewhere in the storage subsystem.

---

## 8. IR15-8 — final functional acceptance evidence is not established for the reviewed candidate

### Evidence

The executable candidate `e7cd824070a6bd7fb3fb83751d2dde185acf0c16` has extensive storage test source, but review of the commit's visible GitHub checks found only the successful documentation-PDF workflow. No storage/P1-P7 regression or assembled integration status/check is attached to the executable candidate, and no durable command/result evidence establishing execution of the required final suite was found in the reviewed repository state.

A test file existing in source is not execution evidence under Protocol 5.10.

### Required closure evidence after IR15 repair

On the exact final executable candidate:

1. run focused tests for IR15-1 through IR15-7;
2. run the complete storage reset core and real-owner integration suites;
3. run affected P1/P3/P4/P5/P7 currentness/publication/restart/retention tests touched by the repair;
4. run stage-local affected regression after each material executable repair stage before dependent work proceeds;
5. re-derive the final affected surface and execute the complete final affected regression and assembled real-owner integration suite after all executable edits;
6. run repository-required CPU-safe broader/full checks when impact cannot be bounded confidently;
7. run affected static/docs/build checks;
8. record enough command/result/candidate identity to establish that these checks actually executed on the same candidate under review.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are **not** reintroduced as repair gates.

---

## 9. Repair staging under the existing R12 sequence

Do not create another lifecycle. Preserve the R12-S0 -> R12-S4 sequence and fold these repairs into it.

### R12-S0 — owner/access/lifecycle correction

- make observational `CampaignStore(create=False)` genuinely SQLite read-only (IR15-6);
- choose the minimal durable P5 terminal-completion certification that survives archived terminal-member removal (IR15-4);
- split CampaignStore event-prune versus VACUUM owner semantics and real serialization contract (IR15-5).

**Gate:** no observational path can write CampaignStore, P5 retains a valid closed-run proof after any represented member goes cold, and maintenance has separate cheap-prune versus rewrite decisions.

### R12-S1 — exact plan and synchronization closure

- bind exact retained archive representation authority for protected reclaim/restore reauthentication (IR15-1);
- include dedup canonical source owners/run roots/generations in plan synchronization (IR15-2);
- bind exact existing restore parent-chain filesystem identities (IR15-3).

**Gate:** protected apply can detect archive corruption/removal, every dedup source/destination owner is fenced, and a same-path parent inode replacement stales restore.

### R12-S2 — recovery/durability and owner integration

- implement protected archive reauthentication immediately before reclaim/restore mutation;
- make P5 partial hot-reclaim resumable after terminal-member removal;
- make dedup rename publication directory-durable before completion/audit (IR15-7);
- implement split/serialized CampaignStore pruning and benefit-gated VACUUM.

Run focused + affected regression before proceeding.

### R12-S3 — reporting/public contract and maintenance truth

- reconcile storage specification, architecture manual, user guide/help/config comments with the final maintenance semantics and any observable recovery/read-only behavior changed by IR15;
- ensure diagnostics/audit distinguish prune from VACUUM and protected archive reauthentication refusal truthfully.

### R12-S4 — final assembled acceptance

Include explicit real-owner counterfactuals for:

- cold blob/manifest/catalog corruption after plan but before reclaim/restore apply;
- cross-run P5 dedup canonical-source liveness;
- same-type ordinary-directory parent replacement before restore apply;
- partial reclaim after P5 terminal evidence itself has gone cold, followed by fresh-process resume;
- one/few excess events pruned without VACUUM, plus benefit-positive VACUUM and concurrent CampaignStore writer serialization;
- direct write attempts through observational CampaignStore failing;
- dedup directory-entry durability failure and idempotent retry.

Then perform final contract reconciliation, re-derive affected surface, and execute fresh final regression/integration on the exact assembled candidate.

---

## 10. Implementation authority

### Frozen

All unaffected Revision-14 authority remains frozen. In addition, for this repair:

- hot reclaim/restore may consume only a retained archive representation reauthenticated inside the protected consequential window;
- dedup synchronization covers canonical source owners as well as replacements;
- restore binds real parent/container filesystem identity, not just pathname/type/mode;
- P5 terminal closed-run certification remains valid after any archive-represented member, including terminal evidence, has gone cold;
- event pruning and VACUUM are separate CampaignStore decisions; excess events alone do not authorize a rewrite;
- observational CampaignStore access is technically read-only at the SQLite owner boundary;
- dedup atomic replacement is directory-entry durable before the action/audit is complete.

### Delegated

- exact immutable storage-owner identity representation for archive reauthentication;
- exact shape by which canonical dedup source paths feed synchronization derivation;
- exact parent-chain identity data structure, provided ordinary-directory inode swaps are detected;
- whether P5 terminal completion is encoded into the retained member manifest or a separate minimal immutable owner marker;
- exact CampaignStore API split between prune/optimize/vacuum and exact SQLite lock helper;
- exact SQLite read-only URI/query-only implementation;
- exact dedup failpoint/test seam around directory fsync.

### Reopen only on evidence

Reopen only the affected surface if implementation proves that:

1. retained archive reauthentication cannot be made race-safe without a new storage-owner locking/representation model;
2. P5 cannot preserve terminal closed-run proof across cold movement without changing a frozen scientific owner contract;
3. real CampaignStore concurrency cannot support a safe independently benefit-gated VACUUM without a material owner-lifecycle redesign; or
4. the target filesystem class cannot provide the required durable rename/link publication semantics and the product needs a different supported guarantee.

Do not weaken currentness, liveness, recovery, or audit truth to avoid a reopen.

---

## 11. Handoff closure

The global design remains unchanged. This amendment is deliberately bounded to source-backed implementation defects discovered in the Revision-14 acceptance review. It preserves the substantial conforming R12-R14 implementation and adds the exact corrected end states and real-owner evidence needed to close the remaining gaps.

**Disposition:** executable implementation **NO-PASS / reopened**. Resume at the earliest affected R12-S0 obligations above, proceed through R12-S4 with stage-local dual closure, and return one final assembled executable candidate for independent Software Design acceptance.