---
kind: implementation-review-rework-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R17
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
amended_date: 2026-09-01
reviewed_candidate_head: 8561cad5dced86f9c1089f80aa455ce5a381906f
reviewed_candidate_tree: 69f4ab4625876778b29c67edc6752484871e2983
reviewed_executable_commit: 2e6a2768341f75a87430d1313b7d64a1e85dfd04
reviewed_executable_tree: 681ed2b915bb29f05505eef87fcc83cf8e1c4b99
review_verdict: NO-PASS
scope: independent Revision-16 implementation acceptance review; preserve conforming R12-R16 work and repair remaining P5 completion-anchor integrity, CampaignStore maintenance exactness/concurrency, durable-audit truth, dedup crash-residue recovery, bounded-report anchor semantics, and candidate-bound execution-evidence gaps
precedence: this amendment composes with the complete Revision-16 supplied contract; where it gives a more specific repair for the reviewed executable candidate it controls; all unaffected R11-R16 requirements remain binding
---

# Storage/I-O reset implementation review reopen — revision 17

## 0. Verdict and preserved implementation

The assembled executable candidate is **NO-PASS** against the complete Revision-16 authority.

Reviewed executable:

```text
commit 2e6a2768341f75a87430d1313b7d64a1e85dfd04
tree   681ed2b915bb29f05505eef87fcc83cf8e1c4b99
```

Reviewed branch head:

```text
commit 8561cad5dced86f9c1089f80aa455ce5a381906f
tree   69f4ab4625876778b29c67edc6752484871e2983
```

The head-only delta regenerates affected PDFs and does not alter executable behavior.

This candidate closes the large majority of the R15/R16 repair contract. Preserve, unless a local repair below necessarily touches the mechanism:

- protected archive catalog/manifest/blob reauthentication before reclaim/restore mutation;
- exact restore parent-chain device/inode/type binding and revalidation;
- canonical-source dedup synchronization across all touched P5 runs/generations;
- real SQLite read-only observation and invocation-scoped context propagation through current storage fan-out;
- per-call read-only SHA receipt behavior with no observational process-global toggle;
- distinct prune and VACUUM plan action types;
- retained P5 completion anchor excluded from archive hot reclamation;
- shared storage-operation serialization for supported retained-archive writers;
- dedup parent-directory fsync before a replacement action is called complete;
- explicit `*_unaudited` public outcomes when durable audit publication fails;
- the R12-R16 owner graph, currentness, liveness, subtree-coverage, archive-security, reporting/deep-audit, admission, journal, catalog, no-CAS dedup, and documentation repairs that are not contradicted below.

The remaining findings are bounded implementation defects and newly exposed consequences of the R16 realization. They do **not** justify reopening the owner-driven architecture or any P1-P7 scientific/currentness decision.

---

## 1. IR17-1 — the retained P5 completion anchor is not yet immutable/authenticated owner authority

### Evidence and failure mode

`record_post_selection_run_members(...)` now describes `run-members.json` as create-once terminal-completion authority, but the implementation still writes it through the **mutable pointer** primitive `publish_mutable_json_atomic(...)` after a check performed outside that primitive's publication lock. Existing-anchor verification compares only the `members` list. It does not verify the rest of the proof (`run_root`, `terminal_records`, `member_count`) or an integrity/content identity.

The read path accepts any mapping with the current schema and then treats any non-empty `terminal_records` plus the listed `members` as positive closed-subtree authority. The recorded member strings are therefore the direct answer to "what P5 owns" without a self-integrity check or owner-held expected digest.

Consequences:

- a syntactically valid damaged/tampered anchor can add an unexpected descendant to `members`, after which storage may treat that descendant as P5-owned and archive/dedup/reclaim it;
- changing `terminal_records`, `run_root`, or `member_count` while leaving `members` unchanged is not detected by repeated owner publication;
- check-then-mutable-publish is weaker than the frozen create-once/validate-existing contract and can overwrite under an unclosed publication race;
- the semantic role changed from an ordinary member list to retained completion authority while retaining the same schema identity, leaving prior-format state indistinguishable by schema alone.

This is blocking because the anchor grants recursive/destructive authority under IR14/R16; ambiguity or corruption must reduce authority, never widen it.

### Required end state

1. Make the completion anchor a **versioned immutable owner record**, not a mutable pointer. Bump the schema when necessary to distinguish the completion-authority format from the earlier member-list format.
2. Publish through an atomic create-or-verify primitive under the anchor's publication lock. There must be no check-then-overwrite window.
3. Bind and validate the complete canonical proof, at minimum:
   - exact run identity/name expected for this run root;
   - supported schema;
   - non-empty terminal-record set drawn from the owner's actual terminal evidence kinds;
   - terminal record(s) included consistently in the recorded member set when they were hot at completion;
   - unique canonical POSIX-relative member paths with no absolute path, `..`, empty/aliasing component, anchor self-entry, or owner-lock entry;
   - `member_count == len(unique members)`;
   - an integrity/content digest over the canonical proof, or an equivalent owner-held expected identity that every consequential read authenticates.
4. `recorded_post_selection_run_members(...)`, `certify_closed_post_selection_run_root(...)`, the bounded report prefilter, and storage inventory must all go through **one validating reader**. No raw `json.loads(...)["members"]` path may grant positive authority independently.
5. Repeated terminal publication verifies the entire proof byte/semantic identity. Any differing proof under the same run identity is an owner-integrity conflict and remains untouched.
6. A malformed, unsupported, digest-mismatched, self-inconsistent, or copied-for-the-wrong-run anchor makes the run non-certifiable and retained. It never becomes a guessed member set.
7. Compatibility with the earlier anchor format is explicit READ/MIGRATE/REJECT. If migration is retained, it may occur only while the real P5 owner can independently re-prove completion/member ownership (for example while terminal evidence is still hot), and must publish the new authority transactionally. Do not silently reinterpret the old schema as the new proof.
8. The anchor remains small retained P5 infrastructure and is still excluded from archive member hot reclamation.

### Acceptance

Use the real P5 owner reader/inventory/planner.

- alter `members` in an otherwise valid anchor to include a foreign file physically present in the run; certification and all consequential storage planning must refuse that run;
- alter `terminal_records`, `run_root`, `member_count`, digest, and schema independently; every case fails closed without destructive authority;
- duplicate or non-canonical member paths are rejected;
- concurrent/repeated publication of identical proof verifies the same immutable anchor; conflicting proof cannot overwrite it;
- an older supported/pre-repair anchor follows the explicitly chosen READ/MIGRATE/REJECT path and cannot authorize mutation merely because its filename/schema looks familiar;
- the existing terminal-evidence-goes-cold + fresh-process reclaim case remains green with the new anchor.

---

## 2. IR17-2 — event-retention policy and execution disagree below 100 records

### Evidence and failure mode

The canonical storage policy accepts `sqlite_compaction_maximum_events` down to `0` and the maintenance plan binds that exact value, e.g. "keep newest 10". `CampaignStore.prune_events(...)`, however, silently executes:

```text
maximum_events = max(100, int(maximum_events))
```

A resolved policy of `0..99` therefore produces a plan and policy identity for one retention bound and executes a different bound. The current tests use a value at the hidden floor and do not exercise this mismatch.

This violates the R13/R16 rule that every public policy knob is real and that the prune intention binds the actual event-retention policy.

### Required end state

There is one canonical effective event bound and it is identical in policy, plan identity, action reason/binding, execution, result, and documentation.

The preferred low-complexity correction is to **respect the resolved policy value exactly** in `prune_events()`. If the product genuinely requires a minimum retained diagnostic count, canonicalize or reject that minimum in the policy resolver before hashing/planning and document it; do not introduce an execution-only clamp.

The historical `[cleanup].maximum_event_records` alias must normalize to the same effective value as the canonical `[storage]` key.

### Acceptance

- exercise explicit values `0`, `1`, `10`, `99`, `100`, and a normal large value; after apply the retained event count matches the resolved plan contract exactly (allowing only concurrently committed newer events according to the owner transaction semantics);
- equivalent legacy/current config spellings produce the same policy identity and outcome;
- no execution helper contains a hidden retention floor that is absent from canonical resolution.

---

## 3. IR17-3 — VACUUM benefit can become stale while waiting for the real SQLite writer lock

### Evidence and failure mode

The maintenance engine calls `vacuum_is_worthwhile(...)` and storage admission **before** `CampaignStore.vacuum()`. The predicate reads `freelist_count` without acquiring the write serialization that excludes another CampaignStore writer. `vacuum()` then executes `VACUUM`, which may wait on SQLite's exclusive lock/busy timeout.

A real writer can therefore change the database after the benefit check—or hold the write transaction while the check observes the last committed state, then commit while VACUUM waits. When VACUUM finally obtains its lock, the free-page predicate may no longer satisfy the configured threshold, yet the full rewrite still proceeds.

This is the exact race Revision 16 required the fresh owner precondition to close. It is operational rather than scientific, but it is blocking because the expensive whole-file rewrite is allowed only by the benefit predicate and storage admission that justify it.

### Required end state

1. The **final** benefit predicate used to authorize the rewrite is observed after waiting for the serialization boundary that excludes competing CampaignStore writers and remains valid through the transition into VACUUM.
2. Use the simplest SQLite/owner mechanism that can actually provide that property. An SQLite locking mode/connection discipline that retains exclusivity across the final check and rewrite is acceptable; an owner-local serialization lock shared by every product CampaignStore writer is acceptable if SQLite alone cannot provide the needed atomicity. Do not add an unrelated scheduler or second maintenance database.
3. Revalidate temporary-space admission at the same final phase; a changed free-space observation refuses without rewriting.
4. If the implementation cannot keep the benefit observation valid across the SQLite `VACUUM` transaction boundary on supported SQLite/filesystem modes, reopen only this maintenance surface rather than weakening the predicate requirement.
5. Do not hold unrelated P5/P7 scientific publication locks longer than required solely to wait for CampaignStore maintenance.

### Acceptance

Create a deterministic real-writer race:

- plan a benefit-positive VACUUM;
- have another real CampaignStore connection hold/perform a write that consumes enough free pages to make the rewrite no longer benefit-positive while maintenance is waiting for write serialization;
- after maintenance obtains the right to proceed, it must freshly observe the new state and **skip/refuse VACUUM**;
- the converse benefit-positive case still rewrites cleanly;
- concurrent writer + maintenance never corrupt currentness/scientific records and reaches a bounded terminal result.

A test that merely proves SQLite eventually serializes two writes is insufficient; it must prove the **predicate is fresh after the wait**.

---

## 4. IR17-4 — a successfully published durable audit record says `audit_published=false`

### Evidence and failure mode

`StorageExecutionResult.audit_published` starts as `False`. `_audit(...)` serializes `result.to_dict()` into the durable audit record and only **after `append_audit(...)` returns** sets the in-memory result field to `True`.

Therefore a normally successful operation returns `audit_published=true`, while the durable record that proves that same operation was published contains `audit_published=false`. The current success test checks the returned result and record count, but not the stored record's truth value.

This contradicts the frozen truthful-audit contract and makes durable operational evidence internally self-inconsistent.

### Required end state

1. The payload that is durably appended for a normally successful operation states the truth that will hold if that append succeeds: `audit_published=true`, empty audit failure, and the operation's real status.
2. Only after successful append should the returned result be finalized as audited. If append raises, no durable record claiming success exists and the returned result becomes the explicit `*_unaudited` outcome with `audit_published=false`.
3. Do not append a second corrective record merely to fix the flag; publish one truthful record.
4. Audit retention continues to operate only on diagnostic audit state and never changes catalog/manifest/blob/nonterminal-journal authority.

### Acceptance

- for cleanup, archive create/reclaim/restore, dedup, and CampaignStore maintenance, read the **persisted** audit record and assert `audit_published=true`, `audit_failure=""`, correct action/status, and exact operation/plan identity;
- repeat the existing append-failure cases and prove no durable record falsely says true while the returned result is explicitly unaudited;
- partial interrupted operations remain partial, never complete.

---

## 5. IR17-5 — dedup's pre-rename temporary hardlink has no crash-recovery owner

### Evidence and failure mode

Dedup currently creates the temporary alias inside the P5 run directory:

```text
.<member>.dedup-<pid>
```

then replaces the destination and fsyncs the directory. Python exception paths remove the temporary name, but a power loss/SIGKILL after `os.link(canonical, temporary)` and before `os.replace(...)` bypasses that cleanup.

On restart, the hidden hardlink is an **unexpected descendant** of the P5 closed subtree. The P5 completion anchor never recorded it, so IR14 correctly makes the run uncertifiable. It is not storage-owned staging, no owner view positively owns it, and ordinary cleanup cannot safely remove it. The crash can therefore permanently block future archive/dedup certification of that run until manual intervention.

This violates the package's interrupted-operation/fresh-process recovery contract.

### Required end state

The transient hardlink must live in an ownership/recovery domain that survives abrupt termination without poisoning P5's closed subtree.

Preferred low-complexity realization:

1. Reuse the existing `.mdstats/storage/staging` owner for dedup temporary aliases, keyed by operation/plan identity. A stale dedup staging entry with no live operation is then ordinary storage-owned abandoned staging under the already accepted lifecycle.
2. Before staging a hardlink, establish that the staging root and canonical/destination are on the same filesystem required for atomic hardlink+rename. If not, refuse that group rather than falling back to a cross-device copy or an unowned in-run temp.
3. Atomic replacement and parent-directory fsync remain unchanged; after success remove the staging entry/directory durably enough for diagnostic cleanup semantics.
4. A fresh process must be able to classify and remove abandoned dedup staging without consulting a PID or deleting any P5 member.
5. Do not introduce a persistent CAS, dedup registry, or second garbage collector. Reuse the existing storage staging owner/lifecycle.

An equivalent realization is acceptable only if a hard-crash residue is positively storage-owned and recoverable without weakening R14 unexpected-descendant retention.

### Acceptance

- simulate the on-disk state of a crash **after the temporary hardlink exists but before destination replacement**; restart from a fresh process/context;
- the P5 run remains certifiable because the temporary name is not inside its owner subtree, or the equivalent storage owner can prove the residue independently;
- safe storage cleanup/retry retires the abandoned storage staging and dedup can re-plan/idempotently complete;
- canonical/destination bytes and metadata remain unchanged by residue cleanup;
- current exception/failpoint and post-replace directory-durability tests remain green.

---

## 6. IR17-6 — bounded P5 reporting still requires the terminal evidence to remain hot

### Evidence and failure mode

R16 intentionally changed completion semantics: once the retained completion anchor is published, a terminal fold/run evidence file may go cold while the anchor continues to certify the run. Consequential planning uses that repaired rule.

The bounded non-certifying report path `_run_looks_finished(...)` still checks for a **currently hot** fold-acceptance/run-evidence file before accepting the anchor. `post_selection_views(..., certify=False)` therefore reports `archive_eligible=false` for a historical run after an interrupted/successful reclaim has removed its terminal member, even though the same owner under `certify=True` correctly treats the run as completed and eligible.

This is safe but materially false operator-facing state: `storage report` promises owner-driven potential reclaim/retention truth, and the mismatch appears exactly in the recovery state R16 was added to support.

### Required end state

1. The bounded report prefilter uses the **same terminal-completion authority** as consequential certification: the validated retained anchor, not continued hot presence of the terminal member.
2. It may remain cheaper than exact closed-subtree certification: validate only the small anchor/header/integrity fields needed to know that completion/member authority exists; do not walk descendants during normal reporting.
3. `certify=False` may continue to expose coverage as advisory/container rather than granting recursive mutation, but its historical/eligible/potential-reclaim classification must not contradict the owner's terminal state merely because represented evidence is cold.
4. Anchor corruption/unsupported schema still reports unresolved/not eligible rather than guessing.

### Acceptance

- archive/reclaim a historical run so its terminal evidence member is absent but the retained anchor remains;
- normal `storage report` stays bounded and reports the run's historical/cold-replaceable state consistently with the owner authority;
- exact consequential planning still performs full member/subtree certification before mutation;
- filesystem-entry visit count remains independent of descendant bulk count.

---

## 7. IR17-7 — final executable regression/integration execution is still not established

### Evidence

The exact executable commit has one GitHub check run: the documentation job. No storage core, real-owner integration, affected P1/P3/P4/P5/P7 regression, or broader CPU-safe test check is attached to `2e6a2768341f75a87430d1313b7d64a1e85dfd04`.

The repository contains extensive new test source and a refreshed representative benchmark result. Those are useful artifacts but do not establish that the mandatory functional suite actually executed successfully on the assembled executable candidate. Protocol 5.10 explicitly separates source/conformance from execution evidence.

### Required closure evidence

After the IR17 repairs, on the exact final executable candidate:

1. focused tests for IR17-1 through IR17-6 plus all still-binding R15/R16 focused cases;
2. stage-local affected regression after each material executable repair stage;
3. complete `test_mlff_storage_reset_core.py` and `test_mlff_storage_reset_integration.py`;
4. affected P1/P3/P4/P5/P7 currentness/publication/restart/retention suites, including the P6 destructive-closure checks touched by CampaignStore/receipt changes;
5. final affected-surface re-derivation from the assembled candidate, followed by fresh full affected regression and assembled real-owner integration;
6. repository-required CPU-safe broader/full checks when impact cannot be confidently bounded;
7. affected static/docs/build checks;
8. enough command/result/candidate identity for independent review to establish that the checks actually ran on that exact executable tree.

A committed evidence database/report is not required; truthful command/CI output tied to the candidate is sufficient. Test source alone is not.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred.

---

## 8. Repair staging — preserve R12-S0 -> R12-S4

Do not create another lifecycle.

### R12-S0 — owner/policy/recovery contract correction

- freeze the versioned immutable/self-validating P5 completion-anchor contract (IR17-1);
- remove/canonicalize the hidden event-retention floor so one effective policy exists (IR17-2);
- freeze the final serialized VACUUM predicate boundary (IR17-3);
- assign dedup pre-rename scratch to the existing storage staging owner (IR17-5).

**Gate:** no durable owner record or policy value can grant a broader/different action than the canonical owner/policy state, and every prepublication dedup residue has a recovery owner.

### R12-S1 — canonical authority/read paths

- implement one validating P5 anchor reader used by publication, inventory, certification, and bounded reporting;
- make anchor publication atomic create-or-verify and explicit on old-schema compatibility;
- make pruning execute the exact resolved bound;
- implement the chosen final-write serialization primitive needed for VACUUM precondition freshness.

### R12-S2 — durability/recovery/audit realization

- move/rework dedup temporary links into recoverable storage-owned staging and preserve atomic rename+fsync semantics;
- make the persisted successful audit record self-consistently say it was published (IR17-4);
- close the deterministic writer/VACUUM stale-benefit race;
- preserve all R15/R16 archive, restore, dedup synchronization, unaudited-failure, and P5 cold-reclaim behavior.

Run focused + stage-local affected regression before proceeding.

### R12-S3 — report and public-contract reconciliation

- make the bounded P5 report consume the validated completion anchor rather than hot terminal-member presence (IR17-6);
- reconcile storage spec, architecture, user guide/help/config comments if anchor schema/compatibility, event-bound normalization, maintenance serialization, dedup staging, or audit-record semantics are externally observable;
- rerun the bounded report/physical-audit benchmark when reporting code changes.

### R12-S4 — final assembled acceptance

Include explicit counterfactuals for:

- P5 anchor corruption/tamper/self-consistency and old-schema handling;
- low event bounds below 100;
- writer changes freelist while VACUUM waits;
- durable successful audit record contents;
- hard-crash dedup temp residue and fresh-process cleanup/retry;
- report after terminal evidence has gone cold;
- every still-binding R12-R16 acceptance case.

Then perform final contract reconciliation, re-derive the complete affected surface, and run fresh candidate-bound regression/integration evidence.

---

## 9. Implementation authority

### Frozen

All unaffected R11-R16 authority remains frozen. In addition:

- a P5 completion anchor that grants closed-subtree authority is versioned, immutable/create-or-verify, self-consistent, and integrity-authenticated before positive use;
- one resolved event-retention bound means exactly one execution bound—no hidden clamp;
- VACUUM's final benefit predicate remains valid across the writer-serialization wait that leads into the rewrite;
- a durable successful audit record must truthfully encode its own successful publication;
- dedup pre-rename scratch has a storage-owned crash-recovery lifecycle and cannot become an unknown P5 descendant;
- normal bounded reporting uses the retained completion authority after terminal evidence goes cold;
- final PASS requires executed candidate-bound functional evidence, not test source alone.

### Delegated

- exact anchor digest/self-authentication representation and migration helper;
- whether an event minimum is removed or explicitly canonicalized at policy resolution, provided no execution-only floor remains;
- exact SQLite/owner locking primitive that keeps the final VACUUM predicate fresh;
- exact sublayout below existing storage staging for dedup hardlink temporaries;
- exact in-memory ordering used to mark the audit result true before/after one successful append, provided the stored and returned records are both truthful.

### Reopen only on evidence

Reopen only the affected surface if:

1. a P5 completion anchor cannot be made self-authenticating/create-once without changing frozen P5 scientific semantics;
2. supported SQLite behavior cannot keep the benefit predicate valid through the rewrite boundary without a materially broader CampaignStore ownership redesign; or
3. dedup cannot use the existing storage staging filesystem while preserving same-filesystem atomic hardlink replacement on a supported campaign layout.

Do not weaken ownership, currentness, recovery, audit truth, or policy exactness merely to avoid a reopen.

---

## 10. Disposition

The global storage architecture remains accepted. The reviewed implementation is **NO-PASS / reopened** for the bounded findings above. Preserve the substantial conforming R12-R16 implementation, resume from the earliest affected R12-S0/S1 obligations, close each executable stage semantically and functionally, then return one final assembled executable candidate with executed acceptance evidence.
