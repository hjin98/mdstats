---
kind: implementation-workplan-authority-entrypoint
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 32
status: reopened
current_authority_pointer: AUTHORITY_REVISION_32.md
current_workplan: STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_11.md
reviewed_executable_commit: 2e01d6fa5119ba67088f7c312c44962eba902c8e
reviewed_executable_tree: fe927d28612d411303676fc04d5a9cd7164720b1
review_verdict: NO-PASS
---

# Storage/I-O reset package authority

This is the sole canonical navigation/status entrypoint for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

## Current normative handoff

Implementation uses only the following current task authorities:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` — broader frozen owner-driven storage architecture and non-goals;
- `STORAGE_IO_MANAGEMENT_RESET_FINAL_APPLY_CLOSURE_REVISION_30.md` — complete accepted final-apply design and preservation boundary;
- `docs/specs/training_data/mlff_storage_management_spec.md` — current storage product contract;
- `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_11.md` — bounded Revision-32 implementation and acceptance corrections, including still-binding Revision-31 acceptance obligations;
- `AUTHORITY_REVISION_32.md` — concise current disposition/authority summary.

Revision-26/28/29/30/31 authority and earlier implementation-review files are historical provenance. Revision 30 remains supplied because it owns the accepted final-apply design. Revision 32 is the current bounded implementation-review delta and is snapshot-complete for all still-binding review corrections. No current requirement depends exclusively on superseded files, Git history, prior conversation, or local Serena/Semgrep state.

## Preserved Revision-30 design and conforming Revision-31 implementation

Preserve the accepted owner-driven storage architecture and final-apply semantics, including:

- exact released-state/proof authority bound into the immutable plan and reauthenticated on the live P7 descriptor;
- retained descriptor continuity through state/proof/topology certification and fd-relative mutation;
- mandatory no-follow final comparison of the complete plan-bound target identity before every P7 member mutation;
- permanently unspendable closed session objects even if fd numbers are reused;
- proof-as-upper-bound monotonic shrink and safe interrupted retry;
- same-attempt capability invalidation after mutation-time contradiction;
- once-per-session non-widenable typed proof lookup;
- structured removed / already-absent / no-change-refused / partial-change-refused outcomes;
- action-local exact reclaimed-byte evidence and aggregate summation from those recorded values;
- one executor-owned structured post-mutation failure recorder for default and CLI cleanup paths;
- retention of unmeasurable P7 files before mutation;
- Python `>=3.10`, descriptor-pinned POSIX threat boundary, bounded reporting, R26 historical test/tool retirement, CampaignStore, P5 proof, archive/dedup/restore/control-plane architecture, and P1-P7 scientific/currentness semantics.

External-DFT, long GPU, and environment-specific HPC/shared-storage production qualification remain deferred and nonblocking. Whole-repository behavioral pytest remains conditional on unbounded final impact or independent repository policy.

## Revision-32 reopen

Independent review of executable `2e01d6fa5119ba67088f7c312c44962eba902c8e`, plus the subsequent Revision-32 gap re-derivation against the same tree, found seven blocking groups in the still-open truthful/safe final-apply surface:

1. P7 recursive mutation truth is still inferred from a positive reclaimed-byte total, so zero-byte file deletion, empty-directory removal, or another zero-credit destructive transition can be reported as `refused_no_change` / `mutated=false` after a later contradiction or failure.
2. R31 replaced symlink-attack-resistant `shutil.rmtree` recursion with a custom pathname walker while retaining only `shutil.rmtree.avoids_symlink_attacks` as a capability check; that flag does not protect the new walker, so a directory-to-symlink substitution can transfer recursive deletion outside the authorized tree.
3. The added R31 generic/common-subtree failure tests drive `record_or_reraise()` directly rather than the required real `StorageExecutor.run` + settlement + durable-audit boundary.
4. The combined real-executor independent-P7-attempt invalidation case, exact deterministic post-mutation byte equality, and explicit file+directory incomplete-target-identity acceptance remain incomplete.
5. No exact-candidate final behavioral regression/integration/static evidence is supplied for executable `2e01d6f...`; connected CI for that SHA contains only the documentation-PDF build.
6. Any exception escaping the engine sets execution status to `partial` with a "strict subset of actions" detail without consulting the recorded mutation evidence, so an execution that changed nothing is audited as a partial mutation.
7. The R30 interruption/retry integration case patches `remove_durably` on the executor and command modules, neither of which the cleanup path calls since R31, leaving the generic-removal half of that counterfactual vacuous while the test still passes.

The precise corrected end states, test-double boundaries, settled acceptance premises, and final evidence requirements are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_11.md`.

## Disposition

**Design/workplan: CLOSED / implementation-ready under Revision 30 plus the bounded Revision-32 corrections.**

**Reviewed executable `2e01d6fa5119ba67088f7c312c44962eba902c8e`: NO-PASS / reopened under Revision 32.**
