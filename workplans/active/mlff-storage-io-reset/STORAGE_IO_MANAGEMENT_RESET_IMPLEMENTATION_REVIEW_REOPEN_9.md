---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R29
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-02
reviewed_authority_revision: 28
reviewed_executable_commit: 6423a3f33a36c09ca1b89f5740f42c402b1993d2
reviewed_executable_tree: a40bdf7cbd4bc1e2a2de4ec41ccb77fede4dc926
reviewed_branch_head: 106081269735c27c862c174e18cb1ffaa3820382
review_verdict: NO-PASS
scope: independent implementation review of Revision 28; preserve the conforming released-authority identity, live descriptor session, upper-bound proof semantics, structured mutation-outcome model, corrected R26/R28 counterfactuals, and specification updates; reopen only same-attempt post-contradiction invalidation, attempt-scoped proof-map reuse, exact nested partial-byte propagation, missing real-owner proxy-proof cases, and exact-candidate functional evidence
precedence: Revision 28 remains the accepted closed implementation-ready design. This review does not reopen P1-P7 science, owner-driven storage architecture, R26 test-retirement policy, or the accepted descriptor-pinned threat model. It adds bounded implementation corrections where executable 6423a3f... still does not fully realize Revision 28.
---

# Storage/I-O reset implementation review reopen 9 — Revision 29

## 0. Verdict and reviewed candidate

**NO-PASS / bounded implementation reopen.**

Reviewed executable:

```text
commit  6423a3f33a36c09ca1b89f5740f42c402b1993d2
tree    a40bdf7cbd4bc1e2a2de4ec41ccb77fede4dc926
```

Branch head `106081269735c27c862c174e18cb1ffaa3820382` is a generated-PDF-only successor (`docs/specs/training_data/mlff_storage_management_spec.pdf`) and does not change the executable review target.

Substantial Revision-28 work is conforming and must be preserved:

- `released_authority_identity()` derives the exact released P7 authority from generation, attempt identity, authenticated state digest, and authenticated v3 proof digest; certified released scratch projects it through `OwnerArtifactView.state_identity`, so the existing plan owner-state binding sees a resealed-but-still-valid release;
- `ReleasedAttemptSession` reacquires the strict P7 namespace, authenticates state, reads/binds proof, certifies topology, checks root/release identity, and returns with the certifying attempt descriptor still open;
- `_cleanup_engine()` reuses one live session per attempt and `remove_released_attempt_member()` mutates through that session rather than reopening the namespace or consuming a closed-descriptor certification snapshot;
- `_certify_attempt_from_descriptor()` correctly treats the released v3 proof as an upper bound: all live nodes must be proof-recorded with exact kind, while proof-recorded nodes already absent remain legitimate monotonic shrinkage;
- the new `MutationOutcome` model distinguishes `removed`, `already_absent`, `refused_no_change`, and `partial_change_refused`; `record_removal()` and `_settle()` no longer classify every normal return as completion and already-absent work earns zero bytes;
- the specification and focused tests were materially updated, including capability-lifetime rather than raw-fd-number instrumentation.

Five blocking groups remain.

---

## 1. IR29-1 — a mutation-time P7 contradiction does not invalidate the live attempt session before later actions

### Finding

The implementation deliberately shares one `ReleasedAttemptSession` across all planned released members in an attempt. That is the accepted bounded realization. However `_cleanup_engine()` currently executes each P7 action as:

```text
record_removal(result, action, remove_released_attempt_member(session, ...))
continue
```

and leaves the same session cached regardless of the returned terminal outcome.

If the member remover discovers a symlink, special/unrecorded node, nested mount, wrong kind, or another mutation-time topology contradiction, `_remove_certified_directory()` may return `refused_no_change` or `partial_change_refused`. At that point the implementation has positive evidence that the live attempt no longer matches the topology certified when the session opened. Continuing to spend the same session on later actions in that attempt silently ignores the contradiction.

Revision 28 explicitly froze the opposite rule: a mutation-time contradiction indicating external namespace/topology interference must not widen authority or be retried until convenient; affected remaining action(s) must stop/refuse.

### Required repair

1. Capture the P7 member `MutationOutcome` before filing it.
2. File the current action truthfully through `record_removal()`.
3. If that action returns a refusal outcome (`refused_no_change` or `partial_change_refused`) caused at the member/mutation boundary, invalidate the attempt-scoped capability for the remainder of this execution: close it and replace the cached entry with a refusal sentinel/reason, or use an engineering-equivalent terminal-attempt marker.
4. Subsequent planned released actions for that same attempt must not mutate through the already-invalidated session. Record them as no-change refusals explaining that an earlier contradiction invalidated the attempt-scoped destructive capability.
5. Successful `removed` and `already_absent` outcomes remain valid monotonic shrink and may continue under the same session.
6. An independent attempt need not be stopped solely because another attempt was invalidated; preserve the existing owner locks and global fail-closed rules.

No new persistent state or retry loop is authorized.

### Acceptance boundary

Through the real cleanup executor and real P7 owner, construct a released attempt with at least two planned members. Inject a foreign/mount/wrong-kind contradiction into the first action only after the final session certification. Prove:

- action 1 is a truthful no-change or partial-change refusal;
- action 2 in the same attempt is not mutated and is refused because the attempt capability was invalidated;
- if action 1 already mutated bytes, execution is `partial`, `mutated=true`, and the audit carries the same terminal truth;
- an unrelated independently authorized attempt can still proceed when the test includes one.

---

## 2. IR29-2 — the attempt session rebuilds the complete proof-node map for every released member

### Finding

`ReleasedAttemptSession.recorded_kinds()` currently constructs a new dictionary from every `certified_nodes` tuple entry on every call. `remove_released_attempt_member()` calls it once per top-level action. Therefore an attempt with `N` proof nodes and `M` planned top-level members performs an avoidable `O(N*M)` proof-node traversal/allocation after certification even though Revision 28 chose one attempt-scoped session specifically to avoid repeated full-topology work.

This is not a filesystem recertification and does not weaken authority, but it is still an avoidable full proof-set pass per member and violates Revision 28's bounded attempt-session cost requirement.

### Required repair

- Materialize the typed proof-node lookup exactly once per `ReleasedAttemptSession` (eagerly at session construction or lazily once and cached).
- Reuse that immutable/session-owned mapping for every member lookup and recursive descent.
- Do not create persistent cache/state and do not add a second authority representation outside the ephemeral session; the mapping is a derived in-memory view of the already-authenticated proof.

### Acceptance evidence

A focused structural/instrumented test with multiple top-level members must show that the complete proof-node mapping is materialized at most once for the attempt session, not once per member. No production-scale benchmark is required.

---

## 3. IR29-3 — successful nested directory removals lose their byte contribution if a later sibling causes partial refusal

### Finding

`_remove_certified_directory()` tracks `freed` and correctly measures regular-file bytes before unlink. For a nested directory it currently does:

```text
nested = _remove_certified_directory(...)
freed += int(nested.removed_bytes or 0)
```

but a fully successful nested recursion returns `removed("removed")` with `removed_bytes=None`. Thus the parent adds zero for all files that were just removed inside that successful nested directory. If a later sibling then exposes a contradiction, the parent returns `partial_change_refused(removed_bytes=freed)` with a strict undercount of bytes already removed.

The current R28 integration test permits that defect by asserting only `0 < removed_bytes <= expected_freed`.

Revision 28 requires partial branches to report the bytes actually substantiated under the existing storage metric and explicitly says to collect the information before unlink rather than inventing it afterwards.

### Required repair

1. A successful recursive directory removal must propagate the `freed` bytes it actually measured, e.g. `removed(..., removed_bytes=freed)` or an equivalent exact internal representation.
2. Parent recursion must accumulate that exact nested byte value before continuing.
3. `already_absent` contributes zero.
4. If a later contradiction yields `partial_change_refused`, its `removed_bytes` must equal the sum of every successfully removed file in the already-mutated prefix under the existing storage byte metric; it must neither over-credit the planned target nor silently drop a successfully removed nested subtree.
5. Preserve hard-link/accounting conventions already defined by the common storage metric; do not invent a new disk-usage metric in this repair.

### Acceptance evidence

Arrange a directory where a complete nested subtree is removed first and a later sibling then causes refusal. Compute the expected bytes from the files actually removed under the same metric and assert exact equality, not merely a positive lower bound or `<=` relationship. Through the real executor, verify aggregate `reclaimed_bytes` and durable action evidence match that exact partial amount.

---

## 4. IR29-4 — several R28 counterfactuals still prove helpers rather than the required real executor/owner boundary

### Finding

The new tests improve mechanism coverage, but the following material R28 claims still bypass the acceptance boundary:

- the valid-but-different resealed release test directly calls `open_released_attempt_session()` instead of building an old plan and driving it through `StorageExecutor.run()`;
- the final corrupted state/proof/topology test directly calls the session opener instead of proving the real cleanup executor refuses at final apply;
- the partial recursive-removal test directly calls `_remove_certified_directory()` and never proves `record_removal()`, `_settle()`, returned execution payload, and durable audit classify the partial mutation correctly;
- no real-executor case proves one successful action plus a later no-change refusal settles `partial` with each action in the correct collection.

These helper tests remain useful focused evidence, but under Revision 28 they cannot close the real-owner acceptance claim by themselves.

### Required repair

Retain focused helper tests and add bounded real-executor counterfactuals with instrumentation only below the semantic owner:

1. Build an old real cleanup plan, then reseal state+proof to a different valid release before final apply/session acquisition; the real executor refuses/stales it with no destructive transfer.
2. Inject final state/proof/topology damage after ordinary planning/revalidation but before session certification; the real executor refuses before mutation.
3. One action succeeds and a later action receives a no-change refusal: execution is `partial`; completed/refused collections and aggregate bytes are correct.
4. A real P7 recursive action mutates a certified prefix and then hits a contradiction: execution is `partial`, `mutated=true`, exact partial bytes are credited, action evidence says `partial_change_refused`, and the durable audit reports the same truth.
5. Combine the last case with IR29-1 where practical: later same-attempt actions are withheld after the contradiction.

Do not replace `StorageExecutor`, synchronization, P7 owner authorization, or `record_removal/_settle` with a test-side reconstruction.

---

## 5. IR29-5 — exact-candidate functional acceptance is still not recorded

### Finding

GitHub exposes only one successful check run for executable `6423a3f...`, named `docs`. There are no functional check/status results bound to the executable commit, and repository search found no separate R28 candidate-bound command/result evidence.

Source inspection can establish semantic conformance and expose the blockers above; it cannot substitute for the mandatory executable evidence.

### Required evidence after IR29-1 through IR29-4 are repaired

On the **final executable commit/tree after the last executable edit**, record actual commands and outcomes for:

1. focused Revision-22 through Revision-29 P7 namespace/state/proof/root/release-authority/capability/mutation/outcome/concurrency counterfactuals;
2. complete `tests/test_mlff_storage_reset_core.py`;
3. complete `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 regressions and P6 destructive/current-lifecycle consumers implicated by the common cleanup/result path;
5. clean maintained-suite `pytest --collect-only -q`;
6. a final affected-surface re-derivation followed by a fresh final affected regression/integration pass on the assembled executable candidate;
7. repository static checks plus affected current specification/document validation.

Whole-repository behavioral pytest remains conditional exactly as Revision 28 states: run it if the final affected surface cannot be bounded confidently or independent repository/release policy requires it. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and nonblocking.

---

## 6. Preservation boundary

Do not reopen or redo conforming work:

- R26 historical test/tool retirement and restored current fixtures;
- the single descriptor-relative `observe_qualification_namespace()` authority and `qualification_views()` consolidation;
- parser totality, canonical generation spelling, generation-scoped released-root binding, cross-generation copy refusal, workspace-wide ambiguity fence;
- exact released-authority derivation and plan projection introduced by R28;
- `ReleasedAttemptSession` as the live descriptor-bound final P7 capability;
- proof-as-upper-bound monotonic shrink semantics;
- the four-outcome `MutationOutcome` model and zero-byte `already_absent` semantics;
- fd-relative no-follow mutation primitives and Python >=3.10 support;
- established P5/P7/storage synchronization order;
- CampaignStore, archive/dedup/restore/control-plane architecture;
- P1-P7 scientific/currentness/publication/qualification semantics;
- current storage specification except wording genuinely required by the bounded repairs above.

No new persistent descriptor/inode ledger, release registry, retry state machine, or platform-specific kernel extension is authorized.

---

## 7. Rework route and exit

Treat the code repair as one coherent final-apply correction stage:

```text
IR29-1 invalidate same-attempt capability after mutation-time contradiction
 + IR29-2 cache the authenticated proof-node lookup once per live session
 + IR29-3 propagate exact nested partial bytes
 -> IR29-4 real-owner proxy-proof counterfactuals
 -> stage-local affected regression
 -> final affected-surface re-derivation
 -> IR29-5 exact-candidate affected regression/integration + static/docs evidence
```

**Design/workplan disposition:** Revision 28 remains **CLOSED / implementation-ready**; Revision 29 is bounded implementation rework only.

**Executable disposition:** **NO-PASS / reopened under Revision 29** until all five blocking groups close.
