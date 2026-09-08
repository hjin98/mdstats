---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 25
status: reopened
amended_date: 2026-09-02
current_authority_pointer: true
supersedes_authority_revision: 24
reviewed_authority_revision: 24
reviewed_executable_commit: 8e87bc863be2470fb602a9cbb2ac411b7bc83bc4
reviewed_executable_tree: 7becdd8918f4125ed69442fa07e95ed412560566
reviewed_branch_head: 8c96180617e5ce38c476d68804155c5bf2a85501
review_verdict: NO-PASS
design_disposition: revision-24 design remains closed; bounded implementation rework only
precedence: Revision 21 remains the accepted final repair design. Revisions 22 and 23 remain binding. Revision 24 remains the accepted final repair-plan closure. Revision 25 is an implementation-review reopen that adds precise corrections where executable 8e87bc8... still violates the Revision-24 end-to-end authority and acceptance requirements. AUTHORITY.md is the sole canonical navigation entrypoint.
---

# Storage/I-O reset package authority — Revision 25 implementation review reopen

## Disposition

The implementation at executable commit `8e87bc863be2470fb602a9cbb2ac411b7bc83bc4` / tree `7becdd8918f4125ed69442fa07e95ed412560566` is **NO-PASS / reopened**.

Revision 24's design/workplan remains **closed**. No P1-P7 science or storage architecture is reopened. The required rework is bounded to four implementation/evidence failures:

1. storage-facing P7 views/proof certification still rediscover the attempt hierarchy by pathname after the strict descriptor census;
2. final released-attempt deletion still has a check-to-destructive-syscall TOCTOU and top-level released regular files bypass the P7 root-continuity mutation check;
3. several new tests are not proxy-proof for the invariants they name;
4. exact-candidate functional regression/integration evidence is not supplied.

The exact repair and acceptance instructions are in `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_7.md`.

## Current supplied implementation contract

Read the current `AUTHORITY.md` plus the still-binding supplied authority set through Revision 24, then this Revision-25 reopen and `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_7.md`.

Revision 25 does not replace the detailed Revision-22/23/24 obligations. It narrows their remaining implementation consequences.

## Preserve as conforming

Do not regress:

- descriptor-relative strict attempt-state census and canonical generation parsing;
- absent-versus-namespace-change/ambiguity distinction;
- malformed-state parser totality and observational report availability;
- generation-scoped v3 released-root locator published from authoritative P7 generation state;
- cross-generation copied-attempt refusal;
- workspace-wide unknown-attempt retention reduction;
- repeated-terminal proof/state/binding/publication validation;
- P7 attempt-state synchronization and existing lock order;
- one `OwnerSynchronization.to_dict()` including `attempt_roots`;
- CampaignStore writer gate and observational-purity closure;
- existing P5 typed proof and archive/dedup/restore/audit/admission architecture;
- the updated current storage specification, subject only to reconciliation with the final mutation realization.

## Remaining implementation authority

### A. One strict P7 attempt-facing owner path

`qualification_views()` and exact released-attempt certification derive the `generation -> attempts -> attempt` namespace and top-level scratch members from the descriptor-bound owner result. They do not independently re-enter that hierarchy through `_generation_roots`, `Path.is_dir`, `Path.iterdir`, `Path.glob`, or equivalent followable discovery.

The exact released proof is opened no-follow relative to the freshly authenticated attempt descriptor, and exact descendant observation remains descriptor-relative under the same authenticated root. A path-taking helper may remain for non-storage diagnostics only if it cannot confer storage destructive authority.

### B. Root/member identity reaches the destructive primitive

Every P7 released-scratch action, regular file or directory, uses an owner-specific final mutation path that preserves or freshly re-establishes the authenticated attempt-root/member identity at the actual destructive boundary.

A finite `lstat -> path unlink/rmtree` sequence is not accepted as race closure when another namespace lookup consumes the name after the check. If the supported runtime cannot preserve the identity through a safe mutation primitive, retain/refuse rather than weaken the authority guarantee; reopen only this mutation-boundary design surface if unconditional refusal would materially defeat the accepted product.

### C. Proxy-proof corrections

Required corrected evidence includes:

- wrong-root state with valid self digest **and** valid binding-derived canonical attempt identity, so only the state/root relation is wrong;
- basename-only released proof with recomputed valid proof self digest;
- nested-mount released scratch where the mount directory is already present in the authenticated released proof, so the mount check—not an unexpected-node contradiction—is what refuses traversal;
- last-transition mutation race injected after final identity validation and immediately before the real destructive primitive;
- a narrow structural absence check that catches the forbidden parallel P7 path/proof rediscovery.

### D. Exact-candidate functional acceptance

On the final executable commit/tree, execute all focused Revision-22/23/24/25 counterfactuals, full storage core/integration suites, the affected P1/P3/P4/P5/P7/P6 owner/destructive regression surface, fresh final affected-surface regression after re-derivation, CPU-safe broader/full tests when impact cannot be bounded, and static/spec/document validation.

Source test files and a successful docs workflow are not functional evidence. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not acceptance blockers.

## Exit

A future PASS requires:

- no storage-facing parallel pathname P7 attempt/proof discovery;
- no P7 released file/directory action whose destructive primitive can inherit authority after the authenticated root/member is replaced;
- proxy-proof counterfactuals that fail when each protection is removed;
- exact-candidate regression/integration evidence passing.

**Design/workplan:** Revision 24 remains **CLOSED**.

**Executable:** **NO-PASS / reopened under Revision 25**.