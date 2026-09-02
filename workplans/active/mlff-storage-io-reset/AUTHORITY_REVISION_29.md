---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 29
status: reopened
supersedes_revision: 28
reviewed_executable_commit: 6423a3f33a36c09ca1b89f5740f42c402b1993d2
reviewed_executable_tree: a40bdf7cbd4bc1e2a2de4ec41ccb77fede4dc926
reviewed_branch_head: 106081269735c27c862c174e18cb1ffaa3820382
implementation_review: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_9.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
---

# Storage/I-O reset authority — Revision 29

Revision 29 is a **bounded implementation-review reopen** of the Revision-28 implementation. Revision 28 remains the accepted closed design/workplan. No P1-P7 science, owner-driven storage architecture, historical-test retirement, or descriptor-pinned threat model is reopened.

## Conforming Revision-28 implementation to preserve

Executable `6423a3f33a36c09ca1b89f5740f42c402b1993d2` materially implements the central Revision-28 design:

- certified released P7 scratch now carries an exact derived released-authority identity from the authenticated attempt state and authenticated v3 proof, bound to generation/attempt and projected through the existing plan owner-state identity;
- `ReleasedAttemptSession` is a live descriptor-bound final P7 capability; session acquisition strictly reacquires the attempt, reauthenticates state, validates proof/topology, checks root/release identity, and retains the certifying descriptor through member mutation;
- one live session is reused per attempt rather than reopening the namespace for each member;
- final certification treats the v3 proof as an upper bound, permitting monotonic absence while refusing live additions/kind changes/foreign nodes;
- the cleanup mutation contract now has explicit `removed`, `already_absent`, `refused_no_change`, and `partial_change_refused` outcomes, with `record_removal()` and settlement driven by those semantics rather than reason strings;
- already-absent actions credit zero bytes, and capability-lifetime instrumentation is stronger than raw descriptor-number equality;
- the current storage specification was updated consistently.

Do not redo those surfaces.

## Blocking implementation corrections

### 1. A mutation-time P7 contradiction must invalidate later same-attempt destructive actions

The current cleanup engine records a refused/partial `remove_released_attempt_member()` result and then continues iterating with the same cached `ReleasedAttemptSession`. Once a member mutation reports a symlink, mount, unrecorded/wrong-kind node, special node, or other mutation-time contradiction, the session's previously certified topology is known not to describe the live attempt completely enough to spend further destructive authority.

Required semantics:

```text
P7 member outcome = removed/already_absent
  -> same session may continue

P7 member outcome = refused_no_change/partial_change_refused at mutation boundary
  -> record current outcome truthfully
  -> close/invalidate that attempt's live capability for this execution
  -> later planned members of the same attempt are refused without mutation
```

Other independently authorized attempts may continue. No retry-until-convenient loop or persistent invalidation state is authorized.

### 2. Materialize the authenticated proof-node lookup once per live attempt session

`ReleasedAttemptSession.recorded_kinds()` currently rebuilds the complete `{path: kind}` mapping from `certified_nodes` for every top-level member action. This converts the one-session realization into an avoidable `O(N*M)` proof-set traversal/allocation for `N` recorded nodes and `M` planned members.

Build/cache the derived typed-node lookup once per ephemeral session and reuse it for member lookup and recursive descent. This is derived in-memory capability state, not a new authority or persistent cache.

### 3. Propagate exact nested partial-removal byte accounting

A successful `_remove_certified_directory()` currently returns `removed` without its measured `freed` byte count. When a parent has already removed that complete nested subtree and later encounters a refusing sibling, the parent's `partial_change_refused` omits the nested bytes because it can only add `nested.removed_bytes or 0`.

Required semantics:

- successful recursive directory removal propagates the exact measured removed bytes;
- parents accumulate those exact values;
- already-absent contributes zero;
- a later partial refusal reports the sum of every successfully removed file in the mutated prefix under the existing storage byte metric;
- no partial outcome may default to full planned bytes, and no successfully removed nested subtree may disappear from the credited total.

### 4. Close the remaining real-owner proxy-proof gaps

Keep the useful direct helper tests, but add real cleanup-executor tests for the claims Revision 28 froze at the real semantic boundary:

- an old real plan followed by a valid-but-different resealed state/proof authority refuses/stales without destructive transfer;
- final state/proof/topology damage injected after ordinary plan/revalidation but before final session certification is refused by the real executor before mutation;
- one successful action plus a later no-change refusal settles `partial` with correct completed/refused collections and byte accounting;
- a real recursive P7 action that removes a certified prefix then encounters a contradiction yields `partial_change_refused`, `mutated=true`, exact partial bytes, `status=partial`, and matching durable audit evidence;
- the same partial/refusal invalidates later same-attempt actions as required by correction 1.

Instrumentation may sit below the real executor/synchronization/P7 owner; it may not replace their decisions.

### 5. Record exact-candidate functional acceptance after the repair

GitHub currently exposes only the successful `docs` check for executable `6423a3f...`; no functional check/status or separate candidate-bound R28 test record was found.

After the last executable edit, bind actual command/results to the final executable commit/tree for:

1. focused R22-R29 P7 namespace/state/proof/root/release-authority/capability/mutation/outcome/concurrency counterfactuals;
2. full `tests/test_mlff_storage_reset_core.py`;
3. full `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions implicated by the changed common cleanup/result path;
5. clean maintained-suite `pytest --collect-only -q`;
6. final affected-surface re-derivation followed by a fresh affected regression/integration pass on the assembled candidate;
7. repository static checks and affected current specification/document validation.

Whole-repository behavioral pytest remains conditional under Revision 28. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and nonblocking.

## Route

Treat the remaining executable repair as one coherent final-apply correction stage:

```text
same-attempt contradiction invalidation
 + one proof-node lookup per session
 + exact nested partial-byte propagation
 -> real-owner proxy-proof counterfactuals
 -> stage-local affected regression
 -> final affected-surface re-derivation
 -> exact-candidate affected regression/integration + static/docs evidence
```

Preserve all conforming R26-R28 architecture and tests not directly affected by these corrections.

**Design/workplan:** **CLOSED / implementation-ready under Revision 28 + bounded Revision-29 implementation corrections.**

**Executable:** **NO-PASS / reopened under Revision 29.**
