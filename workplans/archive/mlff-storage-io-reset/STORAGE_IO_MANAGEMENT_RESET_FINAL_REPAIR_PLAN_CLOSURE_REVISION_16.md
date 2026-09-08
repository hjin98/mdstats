---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R16
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
amended_date: 2026-09-01
reviewed_authority_head: 4fd0931933a5a57cbc1ed480b6f93a492169a844
reviewed_authority_tree: 8054eac7f883ec3f82403710c7e04bd43b4fecce
reviewed_executable_commit: e7cd824070a6bd7fb3fb83751d2dde185acf0c16
reviewed_executable_tree: 51bab072d871c9bcef8271b01def1f82c2cad3c5
scope: final independent closure challenge of the revision-15 repair contract; remove authority-entrypoint ambiguity and close remaining observational-concurrency, maintenance-intention, P5 terminal-proof lifecycle, retained-archive synchronization, and audit-publication semantics without reopening the accepted owner-driven storage architecture
precedence: this amendment composes with the complete revision-15 supplied contract; where it tightens observational propagation, CampaignStore maintenance planning, P5 terminal-proof retention, retained-archive synchronization, audit evidence-failure semantics, or authority navigation, this amendment controls; all unaffected R11-R15 requirements remain binding
---

# Storage/I-O reset repair-plan final closure — revision 16

## 0. Design challenge disposition

Revision 15 correctly identifies the remaining executable blockers and remains the primary implementation-repair contract. A final independent plan challenge found five material handoff/contract gaps plus one stale canonical authority entrypoint. None requires a new storage architecture or changes the NO-PASS verdict for the reviewed executable candidate.

The executable candidate remains:

```text
commit e7cd824070a6bd7fb3fb83751d2dde185acf0c16
tree   51bab072d871c9bcef8271b01def1f82c2cad3c5
```

This revision is Design-only. It closes the repair contract so Implementation can proceed without inventing semantics around concurrency propagation, SQLite maintenance phases, P5 cold-reclaim completion evidence, retained-archive race ownership, or audit-write failure.

No target-size science, P1-P7 scientific/currentness rule, P7 qualification/release rule, or frozen parent V7 verdict is reopened.

---

## 1. IR16-1 — the canonical authority entrypoint must agree with the current revision

### Gap

`workplans/active/mlff-storage-io-reset/AUTHORITY.md` still describes the package as merely `planned`, names the original `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` as authoritative, and says implementation must not begin until predecessor gates complete. That text is historical and directly conflicts with the current Revision-15 `reopened` authority.

A current revision file declaring itself the authority does not fully repair a contradictory canonical `AUTHORITY.md`; an implementation agent reasonably entering through the conventional path could receive the wrong lifecycle state and wrong contract set.

### Frozen end state

1. `AUTHORITY.md` is the canonical navigation entrypoint for this active package and must name the current authority revision and supplied contract set.
2. It must not carry stale predecessor entry conditions, `planned` status, or an obsolete single-workplan pointer once the package is already active/reopened.
3. Revision files remain immutable provenance/semantic amendments; older authority revisions are provenance only unless the current pointer explicitly includes one as normative (Revision 11 remains included for its task-specific closure corrections).
4. Every future authority revision that changes the current contract must update the canonical pointer in the same repository change or otherwise atomically preserve one unambiguous entrypoint.
5. `AUTHORITY.md` is navigation/authority state, not a duplicate scientific/storage specification; the task-specific semantics remain in the listed supplied contract artifacts.

### Acceptance

- opening only `AUTHORITY.md` is sufficient to discover that the package is reopened under Revision 16 and to locate the complete supplied current contract;
- no current authority file simultaneously claims the package is both pre-intake/planned and reopened/active;
- the snapshot-loss counterfactual succeeds without relying on Git history or prior conversation to discover which files are normative.

---

## 2. IR16-2 — observational authority must propagate across nested opens and worker threads without process-global write-mode races

### Gap

Revision 15 correctly requires `CampaignStore(create=False)` to use SQLite read-only access, but the side-effect-free storage guarantee is invocation-wide, not limited to the first store object. The reviewed candidate uses a thread-local observational flag while owner work can fan into worker threads, and it temporarily changes a process-global SHA-receipt destination. A child thread does not inherit an ordinary thread-local flag, while a process-global receipt toggle can interfere with a concurrent consequential operation.

A literal fix that only changes `CampaignStore(create=False)` to `mode=ro` can therefore leave nested helpers or worker threads able to open writable stores/receipts, or can make one observational command perturb another legitimate writer.

### Frozen end state

1. The observational capability is an **invocation-scoped execution property** propagated to every nested owner/store/cache access below that storage command, including worker threads and helper-created stores.
2. A nested helper cannot escape observation by calling an ordinary default-creating `CampaignStore(...)`; the observation context must force or explicitly supply a read-only owner open throughout the invocation.
3. Do not rely solely on an ordinary thread-local flag unless every spawned worker is explicitly entered into the same observation capability before it can open managed state.
4. Read-only receipt lookup/hashing must not require changing a process-global writable receipt destination in a way that races another operation. Prefer per-call/per-context receipt behavior; an equivalent synchronized mechanism is acceptable if it preserves independent concurrent commands.
5. An observational command may coexist with a legitimate consequential/writer operation without causing the observation to write and without disabling/corrupting the writer's own persistence behavior.
6. The SQLite `mode=ro` boundary from IR15-6 remains mandatory and is defense in depth, not a substitute for propagating the observation capability to all nested opens.

### Acceptance

Use the real public storage dispatch/owner adapters.

- Force a nested owner helper to open `CampaignStore` from a worker thread using its normal default constructor while a report/dry-run is active; the effective open must be read-only and managed state remains unchanged.
- Exercise a worker-thread hashing path and prove no receipt row/file is created by the observational invocation.
- Run an observational report concurrently with a legitimate owner writer/receipt-producing operation; the report remains side-effect-free and does not globally disable or redirect the writer's receipt/store behavior.
- Existing uninitialized-campaign and tree/SQLite invariance cases remain green.

---

## 3. IR16-3 — event pruning and VACUUM need distinct planned authority, not only distinct helper branches

### Gap

IR15-5 requires event pruning and VACUUM to be separate decisions, but it still permits an implementation to represent them as one broad `maintain_campaign_state` action and decide at runtime to VACUUM after pruning. That would reintroduce the original authority problem in a subtler form: a plan that authorized cheap diagnostic pruning could become authorization for an expensive full database rewrite because the prune itself created free pages.

### Frozen end state

1. Event pruning and database rewrite are distinct **planned owner actions or distinct freshly authorized owner-local subplans**. A prune action alone never authorizes VACUUM.
2. The prune intention binds the event-retention policy and owner/schema/path preconditions needed to bound diagnostic history. It may evaluate the current qualifying event set under the owner's serialized transaction; it need not freeze event row IDs if owner semantics define retention as "keep the newest N diagnostics".
3. A VACUUM intention exists only when a fresh owner observation already satisfies the configured reclaimable-byte/fraction predicate and storage admission covers the rewrite.
4. If event pruning itself creates enough free pages to make VACUUM worthwhile, the lowest-complexity default is to leave the rewrite for the **next fresh maintenance plan/invocation**. An implementation may instead construct a second explicit owner-local subplan after pruning, but that second subplan must be freshly measured, independently admitted, explicitly authorized, and auditable before VACUUM starts.
5. No hidden conditional inside the prune executor may widen the action into VACUUM.
6. Both actions use real SQLite serialization. Owner data changes while waiting for SQLite access are handled by fresh action precondition checks; do not hold slow filesystem/archive locks around ordinary database waiting merely to preserve a stale measurement.
7. Result/audit truth distinguishes `events_pruned` from `vacuum_performed`.

### Acceptance

- A plan with `maximum_events + 1` and freelist below rewrite thresholds contains/authorizes pruning only. Apply prunes and provably does not VACUUM even if the delete creates newly free pages.
- A subsequent fresh plan may authorize VACUUM if the post-prune freelist now meets policy.
- A database already above the rewrite threshold produces an explicit VACUUM action/subplan; execution rechecks the predicate and admission under real SQLite serialization.
- Structural inspection shows no prune-only action can call an unconditional `compact()`/VACUUM tail.

---

## 4. IR16-4 — the P5 terminal-completion proof must be a retained owner anchor, not another reclaimable archive member

### Gap

IR15-4 correctly requires P5 closed-run certification to survive removal of terminal evidence and prefers a strengthened retained member manifest or minimal terminal marker. The lifecycle of that proof is still implicit. A literal implementation could strengthen the manifest yet include it in the archive member set or otherwise make it safe/cache reclaimable, recreating the same fresh-process recovery failure one level later.

### Frozen end state

1. The P5 terminal-completion/closed-member proof is small **owner infrastructure**, create-once/validate-existing after the real terminal evidence has been durably published.
2. It is excluded from the archive-represented hot-member set whose removal it authorizes. Archive creation/reclaim cannot remove the only proof required to certify that run for future reclaim/restore.
3. It is not safe/cache cleanup residue while a retained archive or incomplete hot-reclaim operation can still require it.
4. Repeated terminal publication verifies the same proof rather than silently rewriting member/completion authority. A different claimed member set under the same terminal run identity is an owner-integrity conflict and fails closed.
5. Unexpected descendants still invalidate/reduce closed-subtree authority; the retained proof is not a blanket pathname grant.
6. The proof carries no scientific/currentness verdict beyond owner completion/member-set certification.
7. Retaining this compact owner anchor is preferred to adding a second persistent archive/dedup authority. Its eventual retirement may be designed only when no retained archive/recovery path needs it; no new garbage collector is required for this repair.

### Acceptance

- The archive manifest for a historical P5 run does not include the retained terminal/member-certification anchor as a reclaimable member.
- Interrupt reclamation after removing the scientific terminal-evidence member; fresh-process owner certification still succeeds from the retained anchor and reclaim completes.
- After all represented hot members are gone, ordinary safe/cache cleanup still preserves the anchor while the retained archive exists.
- Attempting to republish a different terminal member set for the same run identity is rejected rather than overwriting the anchor.

---

## 5. IR16-5 — protected archive reauthentication needs a closed supported-writer synchronization contract

### Gap

IR15-1 says to reauthenticate catalog/manifest/blob inside the protected consequential window. That is sufficient only if every **supported product writer** capable of changing those retained representation paths participates in the same storage serialization discipline. Otherwise reauthentication is another check-before-mutation race against a storage-native writer.

The product need not claim protection against an adversarial process that bypasses all package ownership/locking and rewrites campaign files concurrently, but its own storage commands must not race each other.

### Frozen end state

1. Retained archive blob and manifest representations remain create-once/immutable under one representation identity; immutable catalog fields remain create-once/validate-existing as already frozen.
2. Every supported consequential path that can create, replace, remove, retire, migrate, or operationally update retained archive control state acquires the storage-operation lease before that change. Read-only list/verify/report need not acquire it.
3. Reclaim/restore protected reauthentication occurs while that lease is held, so no supported storage operation can replace/delete the representation between final authentication and the dependent mutation.
4. Owner publication/activity seams remain separately required for scientific-owner races; the storage lease does not replace them.
5. Unsupported/manual concurrent tampering is treated as corruption: integrity checks detect it at the next protected authentication point, but this package does not pretend an advisory lock is an OS security boundary against a process that intentionally ignores it.
6. Do not add a second archive-lock hierarchy if the existing storage-operation lease plus immutable representation rules close the supported race.

### Acceptance

- Race two real public storage operations such that one reclaim/restore has entered protected reauthentication while another operation attempts to change/retire the same retained representation state; the second cannot interleave the consequential write.
- Structural inspection accounts for every product write/remove path under `.mdstats/storage/catalog` and `.mdstats/storage/archives` and proves it is reachable only beneath the storage-operation lease (or an equivalent already-held serialization owner).
- Existing corrupt-after-plan counterfactuals from IR15-1 remain mandatory.

---

## 6. IR16-6 — audit publication failure needs explicit completion semantics and direct acceptance

### Gap

R13 already says audit publication is downstream of the state it claims, an audit write failure cannot roll back an already-safe mutation, the operational evidence failure must be surfaced, and no `complete` audit may be fabricated. Revision 15 did not make direct audit-write-failure injection part of its final repair acceptance, leaving room for an implementation to append best-effort audit, swallow the failure into a detail string, and still report the command as an ordinary fully audited success.

The audit is diagnostic/operational evidence, not scientific authority. Guaranteeing an audit record under arbitrary ENOSPC/I/O failure would require unnecessary write-ahead authority machinery. The correct contract is truthful degraded completion, not rollback or a second recovery database.

### Frozen end state

1. A successfully completed filesystem/database mutation is never rolled back merely because the diagnostic audit append failed.
2. If durable audit publication fails, the public result/CLI/API must **distinguish that outcome from normal fully audited success** and surface the operational evidence failure. It may report the mutation itself as complete only if the result separately and unambiguously reports audit failure; it must not return an undifferentiated success whose contract implies a durable audit exists.
3. No durable audit record may claim `complete` unless that record itself was durably published downstream of the claimed state.
4. Read-only commands still write no audit.
5. Retry/reconciliation starts from actual current filesystem/owner state. Do not replay a destructive action solely to manufacture the missing audit record.
6. Normative documentation must avoid the impossible absolute claim that every applied mutation always has a durable audit even when audit storage itself fails. The accurate contract is: every **normally successful applied operation** publishes one truthful durable audit; audit-publication failure is an explicit operationally degraded outcome and never scientific authority.

### Acceptance

- Inject audit append failure after an otherwise successful cleanup, archive, restore, dedup, and CampaignStore-maintenance mutation using bounded fixtures. The mutated state remains truthful, no false complete audit exists, and the caller observes audit failure rather than ordinary success.
- Inject failure while recording a partial interrupted operation; no complete record appears and the next fresh inventory can safely re-plan from actual state.
- Successful operations continue to produce one durable record and uniform retention without touching retained catalog/manifest/blob/nonterminal-journal authority.

---

## 7. Stage mapping

Do not create another lifecycle. Fold these closure corrections into the existing R12-S0 -> R12-S4 repair sequence.

### R12-S0

- make the canonical authority entrypoint unambiguous (Design artifact; no executable gate);
- freeze invocation-wide observational capability propagation and concurrency-safe receipt behavior (IR16-2);
- freeze distinct prune versus VACUUM action semantics (IR16-3);
- freeze the retained P5 terminal-proof lifecycle (IR16-4);
- freeze the supported-writer serialization contract for retained archive state (IR16-5).

### R12-S1

- carry observational/read-only capability through the actual owner/store construction paths;
- represent prune and VACUUM as distinct planned authority or distinct freshly authorized owner subplans;
- bind retained P5 terminal proof as owner infrastructure rather than archive member;
- ensure retained archive plan identities and supported writer paths compose with the one storage lease.

### R12-S2

- realize protected archive reauthentication under the closed storage-writer lease contract;
- implement P5 anchor create-once/retention semantics and partial-reclaim recovery;
- implement split CampaignStore maintenance and SQLite serialization;
- preserve IR15 dedup durability and restore-parent repairs;
- surface audit-publication failure truthfully without rollback or false complete evidence.

### R12-S3

Reconcile current normative spec/architecture/guide/help/config/README claims for:

- invocation-wide/thread-safe observational behavior;
- explicit prune versus VACUUM planning;
- retained P5 terminal proof as owner infrastructure;
- supported storage-writer serialization around retained archives;
- normally-successful audit versus explicit audit-publication failure.

### R12-S4

In addition to every R12-R15 acceptance case, require:

- nested/worker-thread observational store and receipt attempts remain read-only;
- concurrent observational command does not perturb a legitimate writer's store/receipt behavior;
- prune-only plan cannot turn into VACUUM; a fresh follow-up plan can;
- P5 retained terminal anchor itself cannot be archived/reclaimed while its archive remains retained;
- supported concurrent storage writers cannot alter a representation across reclaim/restore protected reauthentication;
- direct audit-publication failure is surfaced for each consequential action family without false complete audit.

Then perform the existing fresh final affected-surface regression and assembled real-owner integration on the final executable candidate.

---

## 8. Implementation authority

### Frozen

All unaffected R11-R15 authority remains frozen. In addition:

- `AUTHORITY.md` is the unambiguous current package entrypoint;
- observation is invocation-scoped across nested calls and worker threads and cannot race through process-global write-mode toggles;
- prune and VACUUM are separate planned authorities; prune never implicitly widens into rewrite;
- the P5 terminal/member-set certification anchor is retained owner infrastructure outside the reclaimable archive member set;
- all supported writers of retained archive control state participate in one storage-operation serialization contract;
- audit-publication failure is an explicit degraded operational outcome, not rollback, scientific failure, or ordinary fully audited success.

### Delegated

- exact propagation mechanism for observational capability, provided worker/nested opens cannot escape it;
- exact per-call receipt-cache API versus synchronized context realization;
- exact names/types of prune and VACUUM plan actions;
- member-manifest versus separate marker realization of the P5 terminal anchor;
- exact internal representation of audit-write status/error, provided the public outcome is unambiguous.

### Reopen only on evidence

Reopen only the affected surface if implementation proves that:

1. observational semantics cannot coexist with current owner worker concurrency without materially redesigning CampaignStore/cache ownership;
2. real SQLite locking cannot support independently authorized pruning/VACUUM without a material owner-lifecycle change;
3. retaining a compact P5 terminal anchor cannot close partial archive reclaim without changing frozen P5 scientific semantics;
4. the current storage-operation lease cannot close supported retained-archive writer races without a new lock hierarchy; or
5. audit evidence is discovered to be recovery/scientific authority rather than diagnostic evidence, invalidating the degraded-audit model.

Do not weaken side-effect-free observation, owner currentness, archive recoverability, or mutation truth to avoid a reopen.

---

## 9. Handoff closure

With this amendment and the synchronized canonical authority pointer, the repair contract is **final-closure reviewed and implementation-ready**. The executable package remains **NO-PASS / reopened** until Implementation satisfies the complete composed R11-R16 authority and supplies executed stage-local/final affected regression plus assembled real-owner integration evidence.

The current supplied contract is:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md`;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md`;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md`;
6. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md`;
7. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md`;
8. this `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md`;
9. `AUTHORITY_REVISION_16.md` as the current revision pointer.

`AUTHORITY.md` is the canonical navigation entrypoint to that supplied set. Earlier authority revisions other than the explicitly included Revision 11 are provenance only.

Production qualification remains deferred exactly as before: no external-DFT, long GPU-production, or environment-specific HPC/storage qualification is added to this repair gate.
