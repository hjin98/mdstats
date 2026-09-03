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

- exact released P7 authority is derived from authenticated state/proof identities and projected through existing plan owner-state binding;
- `ReleasedAttemptSession` is the live descriptor-bound final P7 capability and retains the certifying attempt descriptor through member mutation;
- one live session is reused per attempt;
- the v3 proof is an upper bound, allowing monotonic absence while refusing live additions/kind changes/foreign topology;
- cleanup has explicit `removed`, `already_absent`, `refused_no_change`, and `partial_change_refused` outcomes, and settlement uses semantic outcomes rather than reason strings;
- already-absent actions earn zero bytes, capability-lifetime tests no longer rely on raw fd-number equality, and the storage specification is aligned.

Do not redo those surfaces.

## Blocking implementation corrections

### 1. Invalidate later same-attempt actions after a mutation-time contradiction

The cleanup engine currently files a P7 member refusal/partial outcome and then continues using the same cached live session. A mutation-time symlink, mount, unrecorded/wrong-kind node, special node, or equivalent contradiction proves the session's topology premise is no longer sufficient to spend further destructive authority.

Required semantics:

```text
removed / already_absent
  -> same session may continue

refused_no_change / partial_change_refused at mutation boundary
  -> record current action truthfully
  -> close/invalidate that attempt capability for this execution
  -> refuse later planned members of the same attempt without mutation
```

Independent attempts may continue. No persistent invalidation state or retry-until-convenient loop.

### 2. Build the authenticated proof-node lookup once per live session

`ReleasedAttemptSession.recorded_kinds()` currently rebuilds the complete `{path: kind}` mapping for every top-level action, creating avoidable `O(N*M)` proof-set traversal/allocation. Materialize this derived mapping once per ephemeral session and reuse it for all member lookups and recursion.

### 3. Propagate exact nested partial-removal bytes

Successful nested `_remove_certified_directory()` calls currently return no measured `removed_bytes`, so a parent that later encounters a refusal omits bytes already removed by that nested subtree. Successful recursion must propagate the exact measured bytes under the existing storage/inode accounting convention; parents accumulate them; already-absent contributes zero; a partial result reports the exact mutated-prefix total, never full planned bytes and never a silent undercount.

### 4. Preserve mutation truth when an exception occurs after a destructive transition

The structured outcome contract currently covers normal returns but not every post-mutation exception. An unlink/rmdir may succeed and a subsequent fsync/durability step may raise before the helper returns `MutationOutcome`; the generic executor exception path can then audit `partial` while the current action still has no recorded mutation/bytes.

Once the first destructive transition occurs, any later failure before clean completion must expose a structured partial-mutation fact to the engine before error propagation can discard it. Preserve existing error propagation where required; do not turn a durability failure into success. Failures before any destructive transition must not fabricate mutation or bytes. Apply this to changed P7 file/recursive paths and common cleanup removal paths where the same sequence is possible.

### 5. Close the remaining real-owner proxy-proof gaps

Keep direct helper tests, but add real cleanup-executor/real-P7-owner counterfactuals for:

- old plan + valid-but-different resealed release authority before final session acquisition;
- final state/proof/topology damage after planning/revalidation but before session certification;
- one success plus later no-change refusal;
- real recursive partial mutation with exact bytes/status/audit;
- same-attempt invalidation after the partial/refusal;
- post-mutation exception after unlink but before clean outcome, plus the pre-mutation failure counterfactual.

Instrumentation may sit below the semantic owners; it may not replace executor authorization, synchronization, P7 owner decisions, or settlement.

### 6. Record exact-candidate functional acceptance after repair

GitHub currently exposes only the successful `docs` check for executable `6423a3f...`; no functional status/check or separate candidate-bound R28 run record was found.

After the last executable edit, bind actual commands/results to the final executable commit/tree for:

1. focused R22-R29 P7 namespace/state/proof/root/release-authority/capability/mutation/outcome/concurrency counterfactuals;
2. full `tests/test_mlff_storage_reset_core.py`;
3. full `tests/test_mlff_storage_reset_integration.py`;
4. affected current-owner P1/P3/P4/P5/P7 plus P6 destructive/current-lifecycle regressions implicated by the common cleanup/result path;
5. clean maintained-suite `pytest --collect-only -q`;
6. final affected-surface re-derivation followed by fresh affected regression/integration on the assembled candidate;
7. repository static checks and affected current specification/document validation.

Whole-repository behavioral pytest remains conditional under Revision 28. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and nonblocking.

## Route

```text
same-attempt contradiction invalidation
 + one proof lookup per session
 + exact nested partial-byte propagation
 + post-mutation exception truth
 -> real-owner proxy-proof tests
 -> stage-local affected regression
 -> final affected-surface re-derivation
 -> exact-candidate regression/integration + static/docs evidence
```

Preserve all conforming R26-R28 architecture and tests not directly affected by these corrections.

**Design/workplan:** **CLOSED / implementation-ready under Revision 28 + bounded Revision-29 implementation corrections.**

**Executable:** **NO-PASS / reopened under Revision 29.**
