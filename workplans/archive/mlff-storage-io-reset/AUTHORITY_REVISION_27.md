---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 27
status: reopened
supersedes_revision: 26
reviewed_executable_commit: f8bd22fcb5d1b5b62246b0ca17653e6b31191a51
reviewed_executable_tree: 928e9507ecac84040e1604ed5949f03440044740
reviewed_branch_head: 60b29f6992f088dd42f78b01424a9054c14e46a0
implementation_review: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_8.md
design_disposition: closed-implementation-ready
executable_disposition: no-pass-reopened
---

# Storage/I-O reset authority — Revision 27

Revision 27 is a **bounded implementation-review reopen** of the Revision-26 implementation. Revision 26 remains the accepted closed design/workplan. No P1-P7 science or owner-driven storage architecture is reopened.

## Conforming Revision-26 implementation to preserve

The reviewed candidate `f8bd22f...` successfully closes substantial prior work:

- R26-T1 historical-only test/benchmark retirement is accepted; current fixtures and live compatibility/current-owner coverage were preserved or consolidated rather than blanket-skipped;
- `observe_qualification_namespace()` is now the single descriptor-relative no-follow P7 storage-facing namespace/state/proof/topology observation consumed by `qualification_views()`;
- exact released proof validation and descendant certification are descriptor-relative and generation-scoped;
- released top-level files and directories route through a P7-specific fd-relative no-follow mutation realization compatible with Python >=3.10;
- the wrong-root, basename-only-proof, nested-mount, and public-path-swap counterfactuals are materially repaired;
- current storage specification text reflects descriptor-pinned ancestry rather than an impossible inode compare-and-delete guarantee.

Do not redo those surfaces.

## Blocking implementation corrections

### 1. Final P7 apply must certify and mutate on the same retained attempt descriptor

The current apply resnapshot certifies state/proof/topology on an attempt descriptor which is closed before the snapshot returns. `_cleanup_engine()` later invokes `remove_released_attempt_member()`, which reacquires a new attempt descriptor, compares its root identity, and mutates using `certified_nodes` carried from the earlier closed snapshot.

Revision 26 requires the final owner-specific apply primitive, under the already-held storage/P5/P7 synchronization, to:

```text
fresh strict attempt reacquisition
  -> retain attempt descriptor
  -> authenticate current state on that descriptor
  -> read/bind exact released proof on that descriptor
  -> observe/certify exact typed topology on that descriptor
  -> verify planned target/identity still matches
  -> fd-relative file/directory mutation from that descriptor
  -> close descriptor
```

The planning/resnapshot result may constrain expected identity and target, but a certification produced from a descriptor already closed may not be the final destructive authority. Refuse on any fresh mismatch; do not retry until convenient.

### 2. Refused P7 mutations must be recorded as refused, not completed

`remove_released_attempt_member()` returns `False` for genuine refusal conditions, but `_cleanup_engine()` currently appends that outcome to `completed`. Since `StorageExecutor._settle()` reports `complete` when `result.refused` is empty, a no-op refusal can be reported as a successful complete execution.

Required semantics:

- `removed=False` because the owner withheld mutation -> `refused_actions`;
- no successes + refusal(s) -> execution `refused`;
- successes + refusal(s) -> execution `partial`;
- only actual/already-terminal successful removal -> `completed_actions` and reclaimed-byte accounting.

Apply the same truth rule to another common certified-subtree helper if it currently records a normal `(False, reason)` refusal as completed.

### 3. Final proxy-proof tests and exact-candidate evidence

Add real-executor acceptance that proves:

- final apply state/proof/topology certification and the first destructive transition share the same retained attempt descriptor/capability;
- mutation after a final public-path swap remains pinned to that capability and never touches the replacement;
- stale proof/state/topology discovered at final apply is refused;
- unsupported dir-fd platform and root/state/proof mismatch appear in `refused_actions` with truthful `refused`/`partial` status;
- both top-level regular-file and directory actions are covered.

After the last executable edit, record exact candidate-bound command/result evidence for all focused R22-R27 P7 tests, full storage core/integration, affected current-owner P1/P3/P4/P5/P7 + P6 current-lifecycle regressions, clean collection, final re-derived affected regression/integration, and static/affected current-doc validation.

GitHub currently exposes only the successful `docs` check for executable `f8bd22f...`; source test presence and commit-message assertions are not execution evidence.

Whole-repository behavioral pytest remains conditional exactly as Revision 26 states. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and nonblocking.

## Route

```text
IR27-1 same-descriptor final P7 certification + mutation
 -> IR27-2 truthful refusal accounting
 -> IR27-3 final proxy-proof tests
 -> exact-candidate affected regression/integration evidence
```

**Design/workplan:** **CLOSED / implementation-ready under Revision 26.**

**Executable:** **NO-PASS / reopened under Revision 27.**
