---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R37
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-03
reviewed_authority_revision: 36
reviewed_plan_commit: 5aeda43223c921cfcaa675f61234f22678c2dbda
reviewed_executable_commit: 84a2df7779884fa3c0590588366bd139dd6241de
reviewed_executable_tree: 9e57b388a5826ea900edb674decc605605b51fe2
reviewed_repository_head: deaeff0a97a89858694e4f0a31a21a1ad2c8efbb
reviewed_repository_tree: 337c053b1acb4f78f408e3c165dd4342331d0c08
review_verdict: NO-PASS
scope: snapshot-complete bounded implementation and acceptance closure for exact unlink/publication mutation transitions, durable restore-journal truth, continuous descriptor/mount authority through final destructive syscalls, typed common-member authority, all-path descriptor/session close semantics, real-owner counterfactual acceptance, and exact-candidate evidence
precedence: Revision 30 remains the accepted closed final-apply design; conforming implementation through Revision 36 is preserved; this Revision-37 handoff supersedes Revision 36 as the complete current bounded implementation/review contract
---

# Storage/I-O reset implementation review reopen 16 — Revision 37

## Disposition

**Current implementation: NO-PASS.**

Revision 36 captured the principal remaining implementation defects, but a final workplan review found two gaps in the publication-transition contract: manifest/catalog publication lacked explicit symmetric owner-level acceptance, and restore-journal publication was not classified as an execution mutation even though a nonterminal journal is durable recovery authority. This revision closes those plan gaps and otherwise preserves Revision 36.

The reviewed executable remains:

```text
commit  84a2df7779884fa3c0590588366bd139dd6241de
 tree    9e57b388a5826ea900edb674decc605605b51fe2
```

The current repository head reviewed for plan closure is:

```text
commit  deaeff0a97a89858694e4f0a31a21a1ad2c8efbb
 tree    337c053b1acb4f78f408e3c165dd4342331d0c08
```

Revision 30 remains the accepted architecture. Do **not** reopen P1-P7 science/currentness, CampaignStore ownership, P5/P7 proof architecture, archive/dedup/restore product design, the four cleanup outcomes, Python `>=3.10`, or the accepted descriptor-pinned POSIX threat boundary. Repair only the bounded surfaces below.

## Preserved conforming implementation

Preserve unless a local adjustment is necessary to satisfy a requirement below:

- `StorageExecutor.run` settles exceptional execution status from explicit `result.mutated`, not `result.completed`.
- Shared cleanup `MutationLedger` owns action-local mutation truth, exact substantiated bytes, and inode deduplication.
- Opened-directory trust is centralized and fails closed when mount resolution is unavailable/ambiguous.
- Generic/P7 recursive child acquisition is no-follow and descriptor-relative.
- `AuthorizedPath`/certified-node kind evidence carries typed common-member authority.
- Restore destination-directory creation/member replacement, dedup alias replacement, positive maintenance prune, and successful `VACUUM` mark mutation at their actual transitions.
- The public `remove_durably(path) -> bool` surface is a thin compatibility adaptation rather than a second recursive algorithm.
- Complete P7 target identity, two-attempt isolation, zero-credit mutation truth, exact per-action byte accounting, and truthful traversal documentation remain binding.

# R37-1 — every consequential persistent transition must establish mutation truth at the transition

## R37-1A — exact unlink truth

`durable_unlink()` must expose one authoritative fact: whether this invocation's unlink syscall succeeded.

Required end state:

- `on_unlinked` fires **iff** the current unlink succeeds; an absent target with `missing_ok=True` does not fire it.
- `missing_ok=False` absence raises without callback.
- Remove every consequential `TypeError` fallback that calls an old signature and then manually fabricates the callback.
- Remove every post-failure pathname-existence inference used to claim that this execution removed a target.
- If unlink succeeds and parent durability later fails, transport a structured partial outcome with exact substantiated bytes even if another actor has already populated the name again.
- If unlink fails before the transition, later pathname absence does not transfer mutation credit to this execution.

Apply to default single-file cleanup, generic/common cleanup, archive hot reclamation, and every current consequential caller.

## R37-1B — one transition-aware atomic-publication primitive

`durable_publish_bytes()` currently atomically replaces the canonical target before parent fsync and published-byte authentication. `durable_publish_json()` builds on it and can additionally fail while reparsing the already-published target. Therefore callers cannot infer publication truth from helper return.

Required end state:

- Expose atomic publication truth at the successful `os.replace(staging, target)` boundary through an `on_published` callback, typed transition result, structured exception carrying transition state, or an engineering-equivalent mechanism.
- The transition signal fires **iff this invocation's canonical replace succeeded**, and it fires immediately after replace, before parent fsync/readback/reparse.
- A failure before replace produces no publication mutation signal.
- A failure after replace preserves the transition fact and the latest owner phase even if size/digest authentication is incomplete.
- `durable_publish_json()` must preserve the lower-level publication signal rather than hiding it behind its later reparse.
- Do not infer mutation from target existence after helper failure; pre-existing targets and concurrent actors make that inference invalid.

This is an internal durability contract unless implementation evidence proves an incompatible supported external consumer. Do not introduce a parallel publication algorithm merely to avoid changing the helper.

## R37-1C — archive blob, manifest, and catalog phases are transition-exact

Archive create has three durable publication stages. The result must say the latest stage whose atomic publication actually happened, not merely the latest helper that returned cleanly.

Required end state:

1. **Blob:** at blob `os.replace`, immediately set `result.mutated = True` and durable-result evidence sufficient to identify the archive and `publication_phase="blob_published"` before parent fsync/readback or `BOUNDARY_AFTER_BLOB` can escape.
2. **Manifest:** at manifest `os.replace`, advance phase to `manifest_published` before its parent-fsync/reparse can escape.
3. **Catalog:** at catalog-entry `os.replace`, advance phase to `catalog_published` before its parent-fsync/reparse can escape.
4. Phase evidence is monotonic within one execution: a later failure never regresses an already crossed phase.
5. `created_bytes` is credited only when its amount is substantiated. Mutation truth does not depend on positive byte credit.
6. A pre-replace failure for any stage does not claim that stage.
7. Existing create-once catalog identity semantics and retained-representation verification remain unchanged.

## R37-1D — restore journals are execution mutations and recovery-state phase evidence

A restore publishes a nonterminal journal before staging/install. The storage specification makes a nonterminal journal durable recovery authority; therefore its canonical publication is a real storage execution mutation even when no destination member has yet changed.

Required end state:

- At successful atomic publication of the initial nonterminal journal, immediately set `result.mutated = True` and record `restore_phase="journal_staging_published"` (or an equivalent typed phase) plus archive/operation identity before later fsync/reparse/staging failure can escape.
- A failure before that initial journal replace remains nonmutating if no other transition occurred.
- Destination container creation/member `os.replace` continues to record its own transition truth and exact restored-byte evidence independently of journal mutation.
- At successful atomic replacement with the terminal journal/receipt, advance to `restore_phase="journal_terminal_published"` before parent-fsync/reparse can escape. A post-replace helper failure does not regress the phase.
- Journal-only mutation may legitimately have `created_bytes=0`, `restored_bytes=0`, and `mutated=true`.
- The terminal receipt must never be claimed if its atomic replacement did not occur.
- Test fixtures should initialize unrelated control-plane directories before the injected operation when necessary so the counterfactual isolates the journal/publication transition being asserted.

Do not reinterpret restore staging scratch as scientific authority. The requirement is about durable operation/recovery publication truth and any other actual transition already governed by the executor.

### Mandatory R37-1 acceptance

Use real engines and `StorageExecutor.run`/settlement/audit except where the low-level primitive itself is the subject:

1. absent `durable_unlink(..., missing_ok=True, on_unlinked=...)` -> callback does not fire;
2. observed file; this execution's unlink fails; another actor removes the name before error handling -> no mutation/bytes attributed;
3. unlink succeeds; replacement appears; parent durability fails -> exact partial mutation and replacement survives;
4. archive blob replace succeeds then `BOUNDARY_AFTER_BLOB` fails -> partial+mutated, phase `blob_published`;
5. blob replace succeeds then helper parent-fsync/readback fails -> partial+mutated; symmetric pre-replace failure is nonmutating;
6. manifest replace succeeds then its parent-fsync/reparse fails -> partial+mutated, phase at least `manifest_published`; symmetric pre-replace failure does not claim manifest publication;
7. catalog replace succeeds then its parent-fsync/reparse fails -> partial+mutated, phase `catalog_published`; symmetric pre-replace failure does not claim catalog publication;
8. archive hot unlink followed by durability failure -> exact current-action evidence; missing/failed unlink fabricates none;
9. initial restore-journal replace succeeds then durability/readback fails before staging/install -> execution/audit partial+mutated, zero restored bytes, nonterminal journal transition evidenced;
10. initial restore-journal failure before replace -> refused/nonmutating when no other transition occurred;
11. terminal restore-journal replace succeeds then durability/readback fails -> latest phase remains terminal-published; run both an install-mutating case and a reuse/no-destination-mutation case so journal mutation truth is independently proven;
12. phase evidence across blob -> manifest -> catalog and restore journal transitions never regresses after a later injected failure.

# R37-2 — descriptor and mount authority remains continuous through final destructive syscalls

## R37-2A — final `rmdir` must spend the authenticated live capability

For generic recursive cleanup, fully-certified common cleanup, and P7 recursion:

- retain the authenticated parent fd and opened child/root fd through the final directory-removal boundary;
- immediately before `rmdir`, no-follow stat the child name relative to the authenticated parent and compare kind/device/inode with the still-open authenticated child descriptor;
- disappearance, kind/identity mismatch, mount ambiguity, or substitution stops/refuses under the running action ledger and never transfers authority to a replacement;
- execute only `os.rmdir(name, dir_fd=authenticated_parent_fd)` after that immediate comparison;
- consequential recursive roots may not fall back to absolute-path `rmdir` once descriptor authority exists;
- only the irreducible race after the immediate final comparison and before the kernel syscall is outside the accepted POSIX guarantee.

## R37-2B — individually-authorized common descent must be descriptor-relative, mount-checked, and typed

- Acquire/authenticate the common container relative to an authenticated parent descriptor and verify opened-descriptor trust before mutation.
- Every intermediate directory for a nested individually-authorized member is opened no-follow and passed through the canonical opened-descriptor mount decision before descent.
- Final member observation remains no-follow and mutation remains fd-relative.
- A bare path with no owner-certified kind grants no deletion authority; do not default missing type to `"file"`.
- Preserve the action-wide mutation ledger/inode accounting across earlier successful members and later refusal/failure.

### Mandatory R37-2 acceptance

Through real planning/authorization, cleanup owner, `StorageExecutor.run`, settlement, and audit, with only low-level trust/timing injection:

- generic top-level and nested same-device mount substitutions;
- fully-certified common top-level and nested equivalents;
- individually-authorized common nested intermediate becoming a same-device mount;
- P7 released directory mount introduced between initial observation and authority-bearing open;
- resolver unavailable/ambiguous at every shared destructive mechanism;
- generic, fully-certified common, and P7 directory-name replacement after descriptor acceptance but before final rmdir;
- directory-to-symlink swap through generic/common real executor paths;
- individually-authorized member replacement by symlink/directory/special node;
- missing typed member authority refuses rather than assuming a regular file;
- known-prefix mutation followed by a later contradiction preserves exact prefix mutation/bytes.

# R37-3 — descriptor/session finalization is leak-free and terminality-safe

Required end state:

- Every acquired generic/common/P7 descriptor closes exactly once on all success, refusal, partial, and exception paths unless ownership is explicitly transferred to a still-live session.
- P7 recursion may not return from a control-flow shape that bypasses close; use `try/finally`, one explicit outcome path, or an equivalently obvious structure.
- `ReleasedAttemptSession.close()` is one-way: invalidate/clear the stored fd before kernel close so a close failure cannot leave a spendable capability.
- `invalidate()` does not inspect its own caught exception with `sys.exc_info()` to decide whether the close failure is secondary. Primary-vs-secondary policy belongs to the caller that knows whether a primary product failure is already active.
- If a primary post-mutation failure exists, record the structured mutation truth first, preserve that primary cause, and retain/log close failure only as secondary evidence.
- If close is the sole failure after mutation, surface structured partial truth; if it is the sole failure before mutation, surface a no-mutation failure.
- Do not blanket-suppress common intermediate-descriptor or mount-refusal close failures.
- `_cleanup_engine` final session cleanup follows the same policy and cannot fabricate success or erase earlier mutation.

### Mandatory R37-3 acceptance

- P7 observation/DirEntry contradiction branches close handles in pre- and post-prefix cases;
- repeated bounded contradiction runs do not accumulate live fds;
- recursive close failure after mutation -> exact partial;
- primary post-mutation failure + close failure -> primary survives;
- mount-refusal close failure after earlier prefix -> prefix evidence survives;
- `ReleasedAttemptSession.invalidate()` close-only failure is observable and capability permanently unspendable;
- real P7 post-mutation failure + session close failure crosses action/engine/audit boundaries truthfully;
- cleanup final-session close-only failure yields partial after earlier mutation and refused/nonmutating before any mutation;
- individually-authorized common intermediate close failure is not silently converted to success.

# R37-4 — acceptance must prove real semantic owners and live seams

Keep useful helper tests, but they cannot substitute for owner-boundary acceptance.

## Cleanup/default/generic/common

Exercise real planning/authorization, the production cleanup engine, executor settlement, and audit for:

- default `engine=None` single-file unlink then parent-durability failure;
- observed-target/unlink-fails/concurrent-disappearance counterfactual;
- generic recursive known prefix then observation/unlink/rmdir/fsync/close failure;
- fully-certified common equivalent;
- individually-authorized common earlier success then later replacement/refusal/pre-mutation failure;
- every R37-2 mount/substitution/typed-authority case.

## P7

Preserve the real two-attempt fixture and prove:

- typed mutation-time contradiction in attempt A records A's current action, withholds later A work, and permits independent B only where the accepted contract permits continuation;
- exceptional low-level post-mutation failure in A records the action, invalidates A, stops execution, prevents later A/B actions, and preserves the primary cause through finalization;
- observation, mount, final-rmdir, descriptor-close, and session-finalizer counterfactuals from R37-2/R37-3;
- complete target identity and spent capability remain pre-syscall guards.

## Archive/restore/dedup/maintenance

Using real engine owners with named failpoints or the lowest transition seam:

- all blob/manifest/catalog publication counterfactuals from R37-1;
- archive hot reclaim unlink/durability failure;
- restore initial/terminal journal publication counterfactuals from R37-1;
- restore destination container creation/member replacement followed by later chmod/fsync/failpoint failure, plus pre-transition controls;
- dedup alias replace followed by durability failpoint;
- positive event prune followed by later failure and zero-prune pre-mutation control;
- successful `VACUUM` followed by later failure.

## Patch/failpoint liveness

For every acceptance-critical injection:

- assert the seam actually fired with a counter/event/failpoint observation;
- prove the production owner path read/called the patched target rather than only asserting `hasattr(module, name)`;
- prefer the lowest callable actually invoked or a spy around it;
- use structural guards only for structural claims.

Do not construct `StorageExecutionResult(mutated=...)` by hand as evidence for an engine mutation claim.

# R37-5 — exact-candidate regression/integration/static/document closure

After the **last executable or test edit**:

1. record exact executable commit and tree;
2. re-derive the affected surface from that candidate, including callers/consumers of changed durability signatures;
3. run all focused R22-R37 namespace, release/root/target identity, opened-descriptor mount, unlink/publication, restore-journal, typed-common, mutation-outcome, zero-credit, close/session, interruption/retry, concurrency, and cross-engine mutation-truth nodes;
4. run complete:

```text
tests/test_mlff_storage_reset_core.py
tests/test_mlff_storage_reset_integration.py
```

5. run at minimum:

```text
tests/test_mlff_target_size_p4f_storage_docs_structure.py
tests/test_mlff_target_size_p6_destructive_closure.py
tests/test_mlff_p7_r11_repair_acceptance.py
tests/test_mlff_p7_r12_repair_acceptance.py
tests/test_mlff_p7_r13_authority_acceptance.py
tests/test_mlff_campaign_cli.py
```

6. include every maintained module/node discovered from the final candidate that exercises `durable_publish_bytes`, `durable_publish_json`, catalog publication, restore journals, `archive_create_engine`, archive reclaim, restore, `dedup_engine`, maintenance, `durable_unlink`, common/generic cleanup, or the P7 released-attempt remover/session;
7. run maintained-suite `pytest --collect-only -q`;
8. run compile/import checks for every changed Python module, `git diff --check`, repository-required static checks, conflict-marker scan, and structural checks proving:
   - no consequential pathname-recursive bypass;
   - no post-failure pathname-disappearance inference;
   - no signature-incompatible unlink fallback that fabricates transition truth;
   - atomic publication callers that contribute execution truth receive transition-exact publication state;
   - archive phase evidence advances at blob/manifest/catalog atomic publication, not helper return;
   - restore nonterminal/terminal journal publication participates in execution mutation truth;
   - every destructive directory acquisition uses actual-open trust before descent;
   - every consequential directory rmdir retains parent authority and performs the final identity check;
   - acceptance-critical patches/failpoints are live;
9. validate affected permanent Markdown and regenerate/validate committed PDF derivatives if permanent documentation changed; workplan-only Markdown does not require a distributed derivative;
10. run a fresh complete affected regression/integration pass on the exact final executable tree after all fixes are assembled and record command/node selection plus pass/fail/skip counts;
11. a later docs/workplan/PDF-only successor may reuse behavioral evidence only after proving the executable tree is unchanged.

Whole-repository behavioral pytest remains conditional on an unbounded final affected surface or independent repository policy. External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking.

# Implementation sequence

## Stage A — transition-exact durability and publication

Implement R37-1 as one coherent durability-ownership repair:

- exact `durable_unlink` transition semantics;
- remove post-hoc absence inference and mutation-fabricating compatibility fallbacks;
- expose atomic publication transition from `durable_publish_bytes/json`;
- wire archive blob/manifest/catalog phases to that transition;
- wire restore nonterminal/terminal journal phases to that transition;
- preserve byte accounting independently from mutation truth.

Run all focused R37-1 real-owner tests before continuing.

## Stage B — continuous destructive descriptor authority

Implement R37-2 and run real generic/common/P7 mount, replacement, final-rmdir, and typed-member counterfactuals.

## Stage C — finalization semantics

Implement R37-3 across recursion, common intermediate descriptors, P7 session invalidation, and cleanup finalization. Run primary-vs-secondary, close-only, pre-mutation, post-mutation, and leak/lifetime tests.

## Stage D — owner-level acceptance closure

Replace/augment helper/manual-result tests under R37-4, including archive manifest/catalog and restore-journal counterfactuals. Strengthen every acceptance-critical seam's liveness proof.

## Final assembled closure

Execute R37-5 on the exact candidate. Only after all blocking obligations pass may the implementation workplan close.

# Initially affected surface

Expected executable surface is bounded but must be re-derived after implementation:

- `mdstats/training_data/storage/durability.py` — exact unlink and atomic-publication transition contract;
- `mdstats/training_data/storage/executor.py` — no post-hoc inference, generic/common descriptor continuity, final rmdir checks, typed common behavior, structured close transport;
- `mdstats/training_data/storage/control_plane.py` — catalog and restore-journal publication plumbing where transition phase must reach the execution owner;
- `mdstats/training_data/storage/archive.py` — blob/manifest/catalog phase truth, restore-journal phase truth, hot reclaim, restore destination transitions;
- `mdstats/training_data/storage/trust.py` — only minimal helper/identity support if needed; preserve the canonical opened-descriptor mount policy;
- `mdstats/training_data/qualification/store.py` — P7 final-rmdir continuity, all-return descriptor closure, session close/invalidation semantics;
- `mdstats/training_data/storage/commands.py` — P7 primary-vs-secondary invalidation and cleanup session finalization if local adjustment is needed;
- `mdstats/training_data/storage/inventory.py` — only if typed common-member handoff needs a minimal interface adjustment;
- `mdstats/training_data/storage/dedup.py`, `mdstats/training_data/storage/maintenance.py` — preserve conforming transition timing; touch only if real-owner acceptance exposes a local gap;
- storage core/integration tests and every newly implicated maintained owner regression;
- `docs/specs/training_data/mlff_storage_management_spec.md` and PDF derivative only if final implementation changes accepted permanent wording.

Do not silently narrow a named owner or mandatory acceptance path.

# Redesign triggers

This remains bounded implementation rework under Revision 30 unless evidence proves one of the following:

- supported Python `>=3.10`/POSIX primitives cannot maintain parent/child descriptor identity plus final fd-relative rmdir under the accepted threat boundary;
- the durability primitive cannot expose whether unlink/atomic replace crossed its transition without an incompatible supported contract;
- restore-journal mutation truth cannot be represented by the existing shared execution result without an incompatible schema change;
- typed common-member authority cannot be carried from existing owner inventory without changing the frozen owner model;
- the four cleanup outcomes cannot represent the required removal truth without incompatible change;
- a supported external consumer makes removal of a consequential compatibility fallback impossible.

If triggered, reopen only that decision with concrete evidence. Test inconvenience, optional-tool absence, or a difficult race fixture is not a redesign trigger.

# Snapshot-complete handoff

The current normative set after Revision 37 is:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven architecture/non-goals;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — accepted final-apply design and protected trust/outcome semantics;
3. `docs/specs/training_data/mlff_storage_management_spec.md` — current product contract;
4. **this file** — complete current bounded implementation/review obligations;
5. `AUTHORITY_REVISION_37.md` / `AUTHORITY.md` — current disposition/navigation.

Revision 31-36 implementation-review/authority files are historical provenance. No still-open implementation requirement depends exclusively on them, prior conversation, Git archaeology, or optional Serena/Semgrep/Hypothesis state.

**Design/workplan disposition:** Revision 30 plus this bounded correction is **CLOSED / implementation-ready**.

**Reviewed executable disposition:** `84a2df7779884fa3c0590588366bd139dd6241de` / tree `9e57b388a5826ea900edb674decc605605b51fe2` is **NO-PASS / reopened under Revision 37**.
