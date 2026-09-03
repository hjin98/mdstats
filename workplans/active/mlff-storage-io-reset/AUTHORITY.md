---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 33
status: reopened
current_authority_pointer: AUTHORITY_REVISION_33.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_12.md
reviewed_executable_commit: 2e01d6fa5119ba67088f7c312c44962eba902c8e
reviewed_executable_tree: fe927d28612d411303676fc04d5a9cd7164720b1
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses only:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete accepted final-apply design;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_12.md` — complete current Revision-33 bounded implementation and acceptance contract;
- `AUTHORITY_REVISION_33.md` — concise current disposition/authority summary.

Revision 31 and Revision 32 review/authority files are historical provenance. Revision 33 consolidates every still-binding correction and can be implemented without reconstructing prior review history.

## Preserved architecture and implementation

Revision 30 remains the closed accepted design: P7 owns release/proof/currentness semantics; exact release/root/target identities remain bound to the immutable plan and final live descriptor; proof is an upper bound under monotonic shrink; same-attempt mutation-boundary contradiction invalidates only that attempt capability; proof lookup is once-per-session/read-only; mutation outcomes remain removed/already-absent/refused-no-change/partial-change-refused; Python `>=3.10` and the descriptor-pinned POSIX threat boundary remain frozen.

Preserve conforming Revision-31 implementation: explicit per-action reclaimed-byte evidence, aggregate summation from action evidence, one executor-owned structured post-mutation recorder, retention of unmeasurable P7 files, mandatory complete target identity, and existing action-scoped `MutationLedger` behavior.

## Revision-33 bounded reopen

Current blocking implementation/acceptance work is fully specified in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_12.md`. In summary:

<<<<<<< HEAD
1. use one action-scoped mutation ledger for P7 recursion so mutation truth is independent of positive byte credit;
2. replace custom pathname recursive deletion with a public-API fd-relative/no-follow tracked destructive walker for generic/common cleanup, consuming canonical `storage.trust` mount semantics;
3. preserve mutation truth across every post-mutation observation/descent/durability/descriptor-cleanup failure and avoid fabricating mutation before the first destructive transition;
4. prove generic/default/common failure behavior through real `StorageExecutor.run`, settlement and durable audit;
5. prove same-attempt invalidation versus a genuinely independent P7 attempt in one real cleanup execution, exact deterministic action bytes, and complete target identity for both file and directory targets;
6. consolidate generic removal authority while preserving the exported `remove_durably` compatibility surface unless separately authorized to change it;
7. align traversal documentation with canonical mount-policy versus destructive-descent ownership;
8. execute the snapshot-complete exact-candidate focused/storage/known-affected/final regression and static/document checks.

External DFT, long GPU production, and environment-specific HPC/shared-storage qualification remain deferred and nonblocking. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy.
=======
Independent review of executable `2e01d6fa5119ba67088f7c312c44962eba902c8e`, plus the subsequent Revision-32 gap re-derivation against the same tree, found seven blocking groups in the still-open truthful/safe final-apply surface:

1. P7 recursive mutation truth is still inferred from a positive reclaimed-byte total, so zero-byte file deletion, empty-directory removal, or another zero-credit destructive transition can be reported as `refused_no_change` / `mutated=false` after a later contradiction or failure.
2. R31 replaced symlink-attack-resistant `shutil.rmtree` recursion with a custom pathname walker while retaining only `shutil.rmtree.avoids_symlink_attacks` as a capability check; that flag does not protect the new walker, so a directory-to-symlink substitution can transfer recursive deletion outside the authorized tree.
3. The added R31 generic/common-subtree failure tests drive `record_or_reraise()` directly rather than the required real `StorageExecutor.run` + settlement + durable-audit boundary.
4. The combined real-executor independent-P7-attempt invalidation case, exact deterministic post-mutation byte equality, and explicit file+directory incomplete-target-identity acceptance remain incomplete.
5. No exact-candidate final behavioral regression/integration/static evidence is supplied for executable `2e01d6f...`; connected CI for that SHA contains only the documentation-PDF build.
6. Any exception escaping the engine sets execution status to `partial` with a "strict subset of actions" detail without consulting the recorded mutation evidence, so an execution that changed nothing is audited as a partial mutation.
7. The R30 interruption/retry integration case patches `remove_durably` on the executor and command modules, neither of which the cleanup path calls since R31, leaving the generic-removal half of that counterfactual vacuous while the test still passes.

The precise corrected end states, test-double boundaries, settled acceptance premises, and final evidence requirements are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_11.md`.
>>>>>>> e656345 (storage: mutation truth, safe recursion, truthful interruption (R32))

## Disposition

**Design/workplan:** **CLOSED / implementation-ready under Revision 30 plus the complete Revision-33 bounded corrections.**

**Reviewed executable `2e01d6fa5119ba67088f7c312c44962eba902c8e`: NO-PASS / reopened under Revision 33.**
