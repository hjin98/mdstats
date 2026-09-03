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
scope: independent implementation review of Revision 28; preserve conforming released-authority identity, live descriptor session, upper-bound proof semantics, structured mutation outcomes, corrected R26/R28 counterfactuals, and specification updates; reopen only same-attempt post-contradiction invalidation, attempt-scoped proof-map reuse, exact partial-byte propagation, post-mutation exception truth, missing real-owner proxy-proof cases, and exact-candidate functional evidence
precedence: Revision 28 remains the accepted closed implementation-ready design. This review does not reopen P1-P7 science, owner-driven storage architecture, R26 test-retirement policy, or the accepted descriptor-pinned threat model.
---

# Storage/I-O reset implementation review reopen 9 — Revision 29

## 0. Verdict and reviewed candidate

**NO-PASS / bounded implementation reopen.**

Reviewed executable:

```text
commit  6423a3f33a36c09ca1b89f5740f42c402b1993d2
tree    a40bdf7cbd4bc1e2a2de4ec41ccb77fede4dc926
```

Branch head `106081269735c27c862c174e18cb1ffaa3820382` is a generated-PDF-only successor and does not change the executable review target.

Substantial Revision-28 work is conforming and must be preserved:

- exact released P7 authority is derived from generation/attempt plus authenticated state/proof digests and projected through the existing owner-state plan binding;
- `ReleasedAttemptSession` performs strict reacquisition, state/proof/topology authentication, root/release checks, and retains the certifying descriptor through member mutation;
- `_cleanup_engine()` reuses one live session per attempt and the remover mutates through that session instead of reopening the namespace or spending a closed-descriptor snapshot;
- released proof topology is correctly interpreted as an upper bound: live additions/kind changes are contradictions, while proof-recorded nodes already absent are legitimate monotonic shrinkage;
- `MutationOutcome` distinguishes `removed`, `already_absent`, `refused_no_change`, and `partial_change_refused`; settlement is no longer driven by reason-string interpretation and already-absent actions earn zero bytes;
- the specification and focused tests were materially updated, including capability-lifetime rather than raw-fd-number instrumentation.

Six blocking groups remain.

---

## 1. IR29-1 — a mutation-time P7 contradiction does not invalidate the live attempt session before later actions

### Finding

The accepted one-session-per-attempt realization is implemented, but `_cleanup_engine()` records the outcome of `remove_released_attempt_member(session, ...)` and immediately continues without inspecting whether the action discovered a mutation-time contradiction.

A `refused_no_change` or `partial_change_refused` from the member boundary can mean the live attempt now contains a symlink, special/unrecorded node, nested mount, wrong kind, or another topology contradiction that was not present when the session certified the attempt. Continuing to spend the same session on later planned members ignores positive evidence that its topology premise is no longer valid.

Revision 28 explicitly requires stopping/refusing affected remaining actions after mutation-time external namespace/topology interference.

### Required repair

- Capture and record the current P7 member outcome first.
- `removed` and `already_absent` are accepted monotonic terminal outcomes and may continue under the same session.
- A mutation-boundary `refused_no_change` or `partial_change_refused` invalidates that attempt's destructive capability for the rest of this execution: close the session and cache an explicit refusal sentinel/reason (or an engineering-equivalent terminal marker).
- Later planned members of the same attempt are recorded as no-change refusals and are not mutated.
- Other independent attempts may continue; no retry-until-convenient loop or persistent invalidation state is authorized.

### Acceptance

Through the real cleanup executor, inject a contradiction into action 1 only after final session certification in an attempt with at least two planned members. Prove action 1 is truthful, action 2 is not mutated and is refused because the same-attempt capability was invalidated, and if action 1 mutated bytes the execution/audit are `partial` with `mutated=true`. An unrelated attempt may still proceed.

---

## 2. IR29-2 — the attempt session rebuilds the complete proof-node lookup for every member

### Finding

`ReleasedAttemptSession.recorded_kinds()` reconstructs `{path: kind}` from the complete `certified_nodes` tuple on every call, while `remove_released_attempt_member()` calls it once per planned top-level member. An attempt with `N` proof nodes and `M` released actions therefore performs an avoidable `O(N*M)` proof-set traversal/allocation despite choosing one attempt-scoped session to make final authority work bounded.

### Required repair

Materialize the typed proof-node lookup exactly once per ephemeral `ReleasedAttemptSession` (eagerly or lazy-once) and reuse the same derived mapping for every member lookup and recursive descent. This is in-memory derived capability state, not new persistent authority.

### Acceptance

A focused structural/instrumented multi-member test proves the complete proof-node mapping is materialized at most once per session. No production benchmark is required.

---

## 3. IR29-3 — successful nested removals disappear from a later partial action's byte accounting

### Finding

`_remove_certified_directory()` accumulates direct file sizes in `freed`. For a nested directory it adds `nested.removed_bytes or 0`, but a fully successful nested call returns `removed` with `removed_bytes=None`. If a later sibling then causes refusal, the parent's `partial_change_refused` omits the bytes already removed by that successful nested subtree.

The current test permits this loss by accepting `0 < removed_bytes <= expected_freed` rather than exact accounting.

### Required repair

- A successful recursive removal propagates the bytes it actually measured before unlink under the existing storage accounting metric.
- Parent recursion accumulates those values; already-absent contributes zero.
- A later partial refusal reports the exact substantiated byte total for the mutated prefix, neither the full planned target nor an undercount that drops a successfully removed nested subtree.
- Preserve the existing inode/hard-link accounting convention; do not invent a new storage metric locally. If the current per-file accumulator cannot represent that metric exactly across nested recursion, carry the minimum attempt/action-local accounting state needed to do so.

### Acceptance

Arrange a complete nested subtree that is removed before a later sibling contradiction. Assert the exact expected bytes under the same production metric, not only a positive/upper-bound relationship, and assert real-executor aggregate `reclaimed_bytes` matches.

---

## 4. IR29-4 — destructive transitions followed by an exception can escape before any structured outcome records the mutation

### Finding

The structured outcome model closes normal-return ambiguity, but destructive helpers still contain sequences such as:

```text
unlink/rmdir succeeds
 -> fsync or later destructive/durability step raises
 -> helper never returns MutationOutcome
```

Examples include top-level P7 file unlink followed by `os.fsync(attempt_fd)`, recursive child removals followed by directory fsync/rmdir, and generic `durable_unlink()` where unlink precedes parent-directory fsync. `StorageExecutor.run()` catches any escaping `BaseException` and sets `status=partial`, but the current action was never passed to `record_removal()`. If it was the first action, the durable record may consequently contain `mutated=false`, zero reclaimed bytes, and no partial action even though bytes were already removed.

This violates Revision 28's protected requirement that returned/audited mutation truth distinguish no-change failure from mutation-before-failure.

### Required repair

- Once a helper performs its first destructive transition, any later failure before clean completion must expose a structured partial-mutation fact to the engine before the exception can erase that knowledge.
- Preserve exception/error propagation where the existing operation contract requires it; do not turn a durability failure into clean success merely to obtain a return value.
- Equivalent realizations are allowed: a structured exception carrying `MutationOutcome`, a helper-level catch that returns/records a partial outcome then re-raises through an engine-owned mechanism, or another design that guarantees the result/audit sees the mutation and exact substantiated bytes before propagation.
- Failures before any destructive transition must remain no-mutation failures and must not fabricate reclaimed bytes.
- Apply the rule to the changed P7 recursive/file paths and the common cleanup removal path wherever a post-mutation exception can escape without a recorded outcome.

### Acceptance

Inject a deterministic failure after a successful unlink but before the helper can report clean completion (for example at the relevant fsync/durability seam). Through the real executor, prove the operation may still raise as designed, but its durable execution record reports `partial`, `mutated=true`, the affected action as partial mutation, and the exact substantiated removed bytes. Add the counterfactual failure before the destructive transition and prove no mutation/byte credit is fabricated.

---

## 5. IR29-5 — several R28 counterfactuals still prove helpers rather than the required real executor/owner boundary

### Finding

The new mechanism tests are useful but do not close all accepted owner claims:

- the resealed release-authority test directly calls `open_released_attempt_session()` instead of driving an old plan through the real cleanup executor;
- final corrupted state/proof/topology directly calls the session opener;
- the partial recursive-removal test directly invokes `_remove_certified_directory()` and therefore does not prove `record_removal()`, `_settle()`, returned execution payload, and durable audit;
- no real-executor case proves one success plus a later no-change refusal settles `partial` with correct collections and bytes.

### Required repair

Keep focused helper tests and add bounded real-owner tests with instrumentation only below the semantic owner:

1. old real cleanup plan + valid-but-different resealed release before final apply/session acquisition -> real executor refuses/stales without destructive transfer;
2. state/proof/topology damage after ordinary planning/revalidation but before session certification -> real executor refuses before mutation;
3. one success + later no-change refusal -> `partial`, correct completed/refused collections and bytes;
4. real recursive P7 partial mutation -> `partial_change_refused`, `mutated=true`, exact bytes, `status=partial`, matching durable audit;
5. combine the partial/refusal with IR29-1 to prove later same-attempt actions are withheld;
6. cover IR29-4 post-mutation and pre-mutation exception counterfactuals at the real executor boundary.

Do not replace `StorageExecutor`, synchronization, P7 authorization, or settlement with test-side reconstruction.

---

## 6. IR29-6 — exact-candidate functional acceptance is still not recorded

GitHub exposes only the successful `docs` check for executable `6423a3f...`; no functional status/check or separate candidate-bound R28 test record was found. Source inspection cannot substitute for required execution evidence.

After the final executable edit, bind actual commands/results to the exact executable commit/tree for:

1. focused R22-R29 P7 namespace/state/proof/root/release-authority/capability/mutation/outcome/concurrency counterfactuals;
2. complete `tests/test_mlff_storage_reset_core.py`;
3. complete `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions implicated by the common cleanup/result path;
5. clean maintained-suite `pytest --collect-only -q`;
6. final affected-surface re-derivation followed by a fresh final affected regression/integration pass on the assembled candidate;
7. repository static checks and affected current specification/document validation.

Whole-repository behavioral pytest remains conditional exactly as Revision 28 states. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and nonblocking.

---

## 7. Preservation boundary and route

Do not reopen R26 historical test/tool retirement, the single descriptor-relative P7 observation/view authority, parser/canonical-generation/cross-generation/ambiguity behavior, exact released-authority derivation and plan projection, `ReleasedAttemptSession` ownership, proof-as-upper-bound monotonic shrink semantics, the four-outcome model, fd-relative no-follow primitives, Python >=3.10 support, established synchronization, CampaignStore, archive/dedup/restore/control-plane machinery, P5 typed proof, or P1-P7 scientific/currentness semantics.

Treat the remaining executable repair as one coherent correction stage:

```text
IR29-1 same-attempt contradiction invalidation
 + IR29-2 one proof lookup per session
 + IR29-3 exact nested partial-byte propagation
 + IR29-4 post-mutation exception truth
 -> IR29-5 real-owner proxy-proof counterfactuals
 -> stage-local affected regression
 -> final affected-surface re-derivation
 -> IR29-6 exact-candidate regression/integration + static/docs evidence
```

No new persistent descriptor/inode ledger, release registry, retry state machine, or platform-specific kernel extension is authorized.

**Design/workplan disposition:** Revision 28 remains **CLOSED / implementation-ready**; Revision 29 is bounded implementation rework only.

**Executable disposition:** **NO-PASS / reopened under Revision 29** until all six groups close.
