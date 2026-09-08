---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R14
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
amended_date: 2026-09-01
reviewed_authority_head: 33bcc888a3582b6f0cb5bfc4ba90f2a1f5e82cb5
reviewed_authority_tree: dadee83d237741c65e5c2d3437f3b24c565c7809
reviewed_executable_commit: 53edc1c75c5b7c9df8f414914534ce915c34f303
reviewed_executable_tree: 8d24e6326b67c38e69a1fe1383be7b975788cac5
scope: final independent closure challenge of the revision-13 repair contract; close recursive subtree-ownership and restore-directory-metadata gaps without reopening the accepted storage architecture or P1-P7 science
precedence: this amendment composes with STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md, STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md, AUTHORITY_REVISION_11.md, STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md, and STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md; where this amendment makes subtree ownership and restore-container requirements more specific, it controls; all unaffected requirements remain binding
---

# Storage/I-O reset final repair-design closure amendment

## 0. Final Design challenge disposition

Revision 13 remains directionally correct and implementation-ready, but one last independent source-to-contract challenge found two material gaps that could still allow a locally conforming implementation to widen authority or mutate unrelated metadata.

The executable candidate remains unchanged from the original implementation review. This amendment therefore changes no acceptance verdict for code: the storage implementation remains **NO-PASS / reopened** until the repair is implemented and tested.

No target-size, P2, P3/P4, P5 scientific, P7 qualification/release, or frozen parent V7 decision is reopened.

---

## 1. IR14-1 — directory owner views do not automatically grant recursive authority over unexpected descendants

### Concern and evidence

Current storage owner views may represent a material family as one directory artifact. For example, a superseded P5 generation exposes `post-selection/gN/runs` as one historical reproducibility-bulk artifact and marks the root archive/dedup eligible.

Current archive enumeration then recursively walks every descendant of an authorized root and accepts each ordinary file/directory when it merely passes the physical campaign boundary. A regular unexpected file inserted below an otherwise eligible directory can therefore inherit archive/hot-removal authority even though no semantic owner explicitly certified that descendant.

This is distinct from R12 archive-root widening and R13 unknown top-level-family handling. A root may be correctly selected yet still contain a descendant outside the owner's closed artifact set.

### Frozen end state

A directory-level owner view has one of two explicit coverage semantics:

1. **closed subtree** — the real owner certifies that all traversable descendants belong to that artifact under an authenticated owner contract/layout, including the rules for allowed files/directories; or
2. **container/open subtree** — the directory itself is owner-known but descendants require individual owner views/reclamation units. Unknown descendants remain ambiguous/retained.

Required consequences:

- lexical containment beneath an owner path is never by itself semantic ownership;
- recursive cleanup, archive collection/hot reclamation, dedup enumeration, legacy-storage cleanup, and restore planning may recurse destructively only through a closed-subtree owner contract;
- if the owner cannot certify the subtree as closed, enumerate only positively owner-certified descendants and leave every extra child untouched;
- a closed-subtree contract must come from the real owner or its authenticated manifest/state, not from filename extension, age, stage name, or storage-authored pathname folklore;
- symlink, nested-mount, external-input, dependency-closure, currentness and liveness checks remain additional reductions of authority;
- an unexpected descendant discovered after planning invalidates/reduces the planned recursive action. Do not silently absorb it into the action merely because it appeared under the root;
- a recursive delete is permitted only when every descendant that would disappear is covered by the same freshly revalidated closed-subtree authority. Otherwise delete only independently authorized children and retain the container as needed;
- archive manifests record only owner-certified members. Unexpected retained descendants do not enter the cold representation and are never removed as a side effect.

### Acceptance boundary

Use real owner views/inventory/planner/executor. Synthetic numerical producers may remain below those owners.

Mandatory cases:

1. create an otherwise archive/dedup-eligible historical P5 `runs/` tree, then insert an unexpected regular file beneath it that no P5 record/manifest owns; archive/dedup/cleanup must retain the file and may not claim the parent as wholly reclaimed;
2. insert an unexpected directory with ordinary files; no recursive `rmtree`/archive traversal may absorb it into destructive authority;
3. the same test with an unexpected symlink or modeled nested mount continues to fail closed under the existing stronger boundaries;
4. a genuinely closed owner-certified fixture with exactly the expected descendant set remains archive/dedup eligible;
5. add an unexpected child after planning but before apply; fresh revalidation detects the changed subtree and refuses/reduces the action rather than deleting the new child;
6. source inspection proves no consequential recursive path equates `is under owner root` with `owner certified every descendant`.

### Stage mapping

Add the coverage-semantics decision to **R12-S0** owner recensus and owner graph closure. Implement the common recursive-authorization rule in **R12-S1/S2** alongside archive/dedup/cleanup authorization. Include the unexpected-descendant counterfactual in **R12-S4** assembled real-owner integration.

---

## 2. IR14-2 — restore may not mutate pre-existing directory/container metadata implicitly

### Concern and evidence

The current restore implementation validates an existing directory only by checking that it is a directory, then later executes `chmod` using the archived mode for every directory member. Thus a restore can change the mode of an already-existing historical/shared container even when no owner authorized a metadata transition.

R13 correctly requires an exact restore plan and member metadata contract, but it does not state the required behavior for a directory that already exists. Without an explicit rule, an implementation could satisfy the restore-plan requirement while still treating directory mode as implicitly overwriteable.

### Frozen end state

Restore distinguishes **newly created archive-owned directories** from **pre-existing container directories**.

- A directory created by this restore may receive the archived owner-certified mode/metadata after its parent path is authorized.
- A pre-existing directory is never `chmod`, `chown`, ACL/xattr-mutated, replaced, or otherwise materially metadata-mutated merely because an archive contains a directory entry with the same path.
- For a pre-existing directory, the restore plan records its exact relevant metadata/identity and the owner determines whether current metadata is compatible with installing descendants.
- If exact archived directory metadata is semantically required and the existing directory is incompatible, restore fails closed or requires an explicit owner-authorized metadata repair; it does not silently normalize the directory.
- If directory metadata is not semantically required, reuse the compatible existing container without changing it.
- Parent-chain ownership, symlink/mount containment and filesystem identity are revalidated under the restore synchronization immediately before child installation. A changed parent identity/path invalidates installation.
- Existing file destinations retain the R13 exact-identical-or-conflict rule; no implicit overwrite is introduced.
- Final restore authentication covers every installed file plus the required directory/container postconditions, not file bytes alone.

### Acceptance boundary

Mandatory cases:

1. restore into an already-existing owner-compatible historical directory whose mode differs from the archive but is not semantically required: child files restore and the directory mode remains byte-for-byte/stat-equivalent to its pre-restore value;
2. when the owner declares exact directory metadata required, incompatible existing metadata causes refusal with no partial metadata normalization;
3. a missing directory created by restore receives the required archived metadata and is durably published before terminal receipt;
4. a shared/pre-existing parent used by unrelated retained artifacts remains unchanged after restore;
5. change a parent directory identity or model a symlink/mount substitution between plan and apply; final under-synchronization path revalidation refuses before installing through the changed parent;
6. injected interruption cannot leave a terminal restore receipt while required directory/container postconditions are unverified.

### Stage mapping

Fold this into **R12-S1 restore-plan semantics** and **R12-S2 archive/restore lifecycle**. Add directory-metadata and changed-parent counterfactuals to **R12-S4** final integration.

---

## 3. Durable storage-control schemas remain versioned fail-closed authority

The final review also challenged long-lived archive/control-plane compatibility. No new redesign is required because the candidate already uses explicit schemas and rejects unsupported manifest/catalog/journal schemas, and the Protocol 5.10 storage contract already requires durable-state compatibility to be READ/MIGRATE/REJECT rather than silently reinterpreted.

Implementation must preserve that behavior while performing the R12-R14 repairs:

- retained archive manifest/catalog/nonterminal-journal formats keep explicit schema/version identity;
- unsupported or corrupt durable storage authority is rejected before consequential mutation and retained for recovery/diagnosis;
- a future migration, if needed, is transactional/create-new-and-validate rather than destructive in-place reinterpretation of the only retained archive;
- no R14 change may downgrade schema/integrity checks to make old fixtures pass.

This is a preservation constraint, not a new migration feature or separate stage.

---

## 4. Final implementation authority additions

### Frozen

In addition to all current R11-R13 repair authority:

- directory containment does not imply recursive semantic ownership;
- every consequential recursive action requires a real-owner closed-subtree certification or per-descendant positive authorization;
- unexpected descendants always reduce authority and are retained;
- restore cannot implicitly mutate metadata of a pre-existing directory/container;
- directory/container compatibility and parent identity are part of restore revalidation and terminal authentication;
- durable storage-control schemas remain versioned and fail closed on unsupported/corrupt authority.

### Delegated

- exact representation of closed-subtree versus open-container coverage in owner views;
- whether a closed owner uses an explicit manifest, authenticated run plan, generated expected-member set, or another equivalent real-owner mechanism;
- exact directory metadata fields considered material by each owner, provided unknown/material differences are never silently overwritten;
- exact fd/path implementation used for final parent identity revalidation, provided symlink/mount/identity changes cannot be silently followed.

### Reopen only on evidence

Reopen only the affected storage surface if:

- an owner cannot express a safe closed-subtree or per-descendant contract without material lifecycle redesign; or
- a supported restore use case genuinely requires metadata mutation of a shared pre-existing directory and that transition cannot be delegated to the owning lifecycle safely.

Until then, ambiguity retains.

---

## 5. Final handoff closure

The current supplied repair contract is now:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md`;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md`;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md`;
6. this `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md`;
7. the current authority pointer naming the set.

The R12-S0 -> R12-S4 sequence remains unchanged; these requirements fold into the existing stages as mapped above. No new lifecycle or P1-P7 rework is introduced.

**Design disposition:** with IR14-1 and IR14-2 added, the repair contract is final-closure reviewed and implementation-ready. The executable workplan remains reopened until a new implementation candidate satisfies the full composed authority and provides executed stage-local/final affected regression and real-owner integration evidence.
