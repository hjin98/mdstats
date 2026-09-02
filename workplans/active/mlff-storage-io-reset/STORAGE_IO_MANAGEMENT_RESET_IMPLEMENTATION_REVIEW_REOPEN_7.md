---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R25
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-02
reviewed_authority_revision: 24
reviewed_executable_commit: 8e87bc863be2470fb602a9cbb2ac411b7bc83bc4
reviewed_executable_tree: 7becdd8918f4125ed69442fa07e95ed412560566
reviewed_branch_head: 8c96180617e5ce38c476d68804155c5bf2a85501
review_verdict: NO-PASS
scope: independent implementation review of Revision 24; preserve the conforming descriptor state census, parser totality, generation-scoped proof publication, synchronization repair, and specification update; reopen only the remaining parallel pathname P7 view/proof route, final identity-to-mutation TOCTOU, proxy-proof gaps, and exact-candidate evidence
precedence: Revision 21 remains the accepted final repair design; Revisions 22 and 23 remain binding; Revision 24 remains the closed implementation-ready repair-plan authority. This review does not reopen parent architecture or P1-P7 science. It adds precise implementation/evidence corrections where executable 8e87bc8... does not yet realize the frozen Revision-24 invariants.
---

# Storage/I-O reset implementation review reopen 7 — Revision 25

## 0. Verdict and reviewed candidate

**NO-PASS / reopened.**

Reviewed executable:

```text
commit  8e87bc863be2470fb602a9cbb2ac411b7bc83bc4
tree    7becdd8918f4125ed69442fa07e95ed412560566
```

Branch head `8c96180617e5ce38c476d68804155c5bf2a85501` is a generated-PDF-only successor; functional review remains bound to executable `8e87bc8...`.

Substantial Revision-24 work is conforming and must be preserved:

- `iter_attempt_state_authorities()` now descends `qualification -> canonical gN -> attempts -> attempt -> attempt-state.json` through descriptor-relative no-follow opens and distinguishes ordinary absence from an enumerated-then-changed namespace;
- strict state parsing is total over the expected malformed-record `KeyError`/`TypeError`/validation classes and returns unresolved authority instead of killing observational reporting;
- the v3 release proof is published with a generation-scoped portable root locator derived from the authoritative P7 binding generation;
- cross-generation copied attempts are rejected by the new root locator;
- `OwnerSynchronization.to_dict()` is single and includes `attempt_roots`;
- the read-only CampaignStore guard/test cleanup from earlier revisions remains conforming;
- the current storage specification was updated for continuous P7 authority and generation-scoped release-root semantics.

Four blocking groups remain.

---

## 1. IR25-1 — the strict descriptor census is not yet the single P7 storage-facing namespace/proof authority

### 1.1 `qualification_views()` re-enters the state-bearing hierarchy by pathname

Revision 22 and Revision 24 require storage-facing attempt enumeration/reporting/certification to derive from the strict namespace result rather than rediscovering the same hierarchy through followable path APIs.

The candidate first calls `iter_attempt_state_authorities(paths)`, but then independently does the equivalent of:

```text
for root in _generation_roots(family_root):
    (root / "objects").is_dir()
    attempts_root.is_dir()
    attempts_root.iterdir()
    attempt.iterdir()
```

This is not merely diagnostic formatting. It traverses the state-bearing `generation/attempts/attempt` hierarchy a second time and can observe the target of an ancestor substituted after the strict census. The current fail-closed owner graph often prevents that observation from becoming deletion authority, but the frozen contract deliberately forbids the parallel path rather than depending on a later gate to neutralize it.

### 1.2 Exact released-attempt proof certification is still path-based

`qualification_views(..., certify=True)` invokes `certified_attempt_nodes(attempt, state)`. That path calls path-based `validate_bound_attempt_proof()` / `read_attempt_member_proof()` and `_observe_attempt_nodes(root)` after the descriptor-bound state census has already completed.

`O_NOFOLLOW` on the proof's final filename does not preserve the authenticated generation/attempt ancestors. Nor does a typed node set recovered from that second path prove it was recovered from the same attempt directory whose state authority supplied `root_identity`.

This directly violates Revision 24's requirement that proof reads and exact descendant observation remain relative to the authenticated attempt identity or freshly reacquire the complete strict hierarchy before certification.

### Required repair

Consolidate the P7 storage-facing owner path. Do not add a third reader.

1. `qualification_views()` obtains generation/attempt namespace facts from the strict P7 namespace result. It must not use `_generation_roots()`, `Path.is_dir()`, `Path.iterdir()`, `Path.glob()`, or equivalent followable rediscovery to enumerate the `qualification/gN/attempts/<attempt>` state-bearing hierarchy.
2. It is acceptable for bounded reporting of **non-attempt durable P7 evidence** to use a separate safe owner mechanism, but that mechanism must not descend a substituted generation/`attempts` target to discover attempt state or scratch.
3. Exact released-attempt proof validation must read `attempt-members.json` descriptor-relative from a freshly authenticated attempt descriptor, or consume a descriptor-bound snapshot returned by the strict owner. The expected generation/root locator comes from that authenticated namespace result, not from `Path.parent.parent.name` as an independent authority lookup.
4. Exact typed descendant observation must be descriptor-relative beneath the same authenticated attempt root and must preserve the existing symlink/special/wrong-kind/nested-mount refusal semantics.
5. The storage-facing `certified_attempt_nodes()` API may be refactored, split, or retired. Do not preserve a path-taking helper merely for source compatibility if it would remain an authority bypass. Non-storage diagnostic/runtime callers may keep a lower-level path API only if it grants no storage destructive authority.
6. The owner view should be built directly from the strict result/certification. Top-level scratch member names/kinds must not be discovered by `attempt.iterdir()` after certification.
7. Ordinary `storage report` remains bounded and does not parse/walk the O(node-count) proof.

### Acceptance boundary

Use the real P7 owner and storage owner adapter. Filesystem-race instrumentation may wrap the real descriptor/open primitive below those owners but may not replace the P7 classification.

Required checks:

- structural/absence inspection proves the P7 attempt-facing part of `qualification_views()` no longer contains a followable generation/attempts/attempt rediscovery path;
- after the strict state census authenticates an attempt, replace the generation, `attempts`, or attempt entry before view construction/exact proof certification; the substituted target is never enumerated as P7 scratch and contributes no member/proof authority;
- the proof file itself is replaced or its ancestor is swapped between state authentication and proof open; the target proof bytes are not consumed;
- existing static symlink, wrong-kind, malformed-state, bounded-report, generation-spelling, and cross-generation root-binding tests remain green.

---

## 2. IR25-2 — final P7 mutation is still check-then-act rather than identity-preserving

### 2.1 Directory removal retains a last TOCTOU window

The candidate improves `remove_certified_subtree()` by `lstat()`-checking the attempt root and member container against the expected `(device,inode)` immediately before removal. It then calls path-based `remove_durably(path)`, which performs new `Path.is_*()` lookups and eventually `shutil.rmtree(path)`.

Therefore the identity proof and the destructive lookup are still separate syscalls. A same-shaped plain directory can replace the checked name after the final `lstat()` and before `rmtree` starts. `shutil.rmtree.avoids_symlink_attacks` protects its own traversal from symlink attacks; it does **not** make its top-level pathname conditional on the `(device,inode)` Revision 24 authenticated earlier.

The existing new race test swaps **before** entering `remove_certified_subtree()`, so the candidate's final `lstat()` catches it. It does not exercise the remaining check -> `remove_durably()`/`rmtree()` window.

### 2.2 Top-level released regular files bypass the new root-continuity check

`qualification_views()` can expose a proof-certified top-level released regular file as `safe_reclaimable=True`. `_cleanup_engine()` applies `view.root_identity` / `view.path_identity` only in the `action.path.is_dir()` branch. A regular-file P7 action falls through to `remove_durably(action.path)` after generic plan revalidation and therefore does not preserve the P7 attempt-root identity at the final mutation seam.

Revision 24's root-continuity invariant applies to the released-attempt destructive authority, not only to directories.

### Required repair

1. Route every P7 released-attempt destructive action, regular file or directory, through an owner-specific final mutation boundary that retains or freshly re-establishes the authenticated attempt-root identity.
2. Do not claim a finite `lstat(expected) -> path mutation` sequence is identity-preserving merely because the check is close in source. The actual name consumed by the destructive syscall must be tied to the authenticated object strongly enough that a replacement at the last transition cannot inherit authority.
3. Prefer an existing supported descriptor/dir-fd mutation primitive if it can enforce the invariant. If the platform primitive cannot condition the destructive action on the expected root/member identity, follow Revision 24's explicit fallback: **retain/refuse rather than weaken authority**, and invoke the Revision-24 redesign trigger if preserving useful P7 released-scratch reclamation would require a material new platform/ownership contract.
4. Do not add an unbounded retry loop. Namespace instability is a refusal, not a reason to race until one attempt succeeds.
5. Preserve durable unlink/fsync behavior and truthful audit semantics for actions that do execute.

### Acceptance boundary

The test must inject at the **last name-based transition that still exists**, after the production final identity revalidation but before the actual unlink/rmtree/rename/delete primitive consumes the name.

Required cases through the real cleanup executor and production attempt lock:

- same-shaped plain-directory replacement;
- symlink replacement;
- proof-certified top-level regular-file replacement;
- nested special/symlink/mount refusal remains unchanged.

The replacement object's bytes and topology remain untouched. If the accepted implementation must refuse the action on this platform, assert that refusal truthfully rather than weakening the test.

---

## 3. IR25-3 — several new tests are not proxy-proof for the invariant they name

### 3.1 Wrong-root state still has an independent canonical-identity failure

The revised fixture recomputes `content_digest`, which fixes the old self-digest shortcut. But it sets `attempt_identity = "c" * 64` while leaving the original `binding_digest`. That means the record also violates the independent binding-derived canonical-attempt invariant.

Today the implementation checks root mismatch first, so the test happens to exercise the intended branch. If the root check regressed while the canonical check remained, the test would stay green.

Repair the fixture so **state self-digest and canonical binding-derived attempt identity are both valid**, while only the state/root relation is wrong. For example choose a different valid 64-byte binding digest, derive its canonical attempt identity with the production identity helper/rule, place that state under the original attempt root, then recompute/persist the state digest. Assert the reported failure is specifically the root/state relation.

### 3.2 Basename-only proof test is self-digest-invalid

The test mutates `payload["attempt_root"]` to the basename and writes it without recomputing the proof `content_digest`. The strict reader can therefore reject the fixture at generic proof self-digest validation even if the basename-only guard disappears.

Recompute the proof self digest after changing only the root locator. Assert the failure reason is the incomplete/basename root identity and retain the real cleanup refusal.

### 3.3 Nested-mount test currently fails earlier as an unrecorded proof node

The test creates `mounted/` **after** the released proof already exists. That new directory is foreign/unrecorded, so exact proof certification is withdrawn before the descriptor authorizer's mount-boundary check is required. The test can remain green if the mount check inside the exact P7 authorizer is broken.

Construct a proof-valid released attempt whose recorded topology already contains the directory that the deterministic mount resolver will classify as a nested mount, then run exact authorization. The only reason traversal stops must be the mount boundary, not an unexpected-node contradiction.

### 3.4 The final-removal swap test fires too early

The current `final_removal` test monkeypatches `remove_certified_subtree()` and swaps the root before delegating to the real function. That proves the function's entry check, not the check-to-mutation seam described in IR25-2.

Move the instrumentation below the final production identity check and immediately before the actual destructive primitive, while still delegating to the real mutation path. A hidden failpoint or wrapper below the semantic owner is acceptable; a fake deletion result is not.

### 3.5 Structural test does not forbid the actual parallel path

`test_the_strict_state_authority_is_the_only_storage_facing_reader()` checks that `QualificationAttemptState` is not reparsed in `owners.py` and that `iter_attempt_state_authorities` is referenced. It does not fail on the still-present `_generation_roots()/Path.is_dir()/iterdir()` P7 attempt rediscovery or on path-based released-proof certification.

Strengthen the structural/absence check around the actual forbidden mechanism. Keep it narrow to the P7 attempt-facing owner path; do not create a repository-wide AST bureaucracy.

---

## 4. IR25-4 — exact executable candidate functional evidence is still absent

Revision 22/24 require candidate-bound command/result evidence after the final affected-surface re-derivation.

For executable `8e87bc863be2470fb602a9cbb2ac411b7bc83bc4`, GitHub exposes one successful check run named **`docs`** and no functional status checks. The commit contains substantial new tests, but source presence is not evidence that they executed.

This remains independently blocking even after source repair.

After IR25-1 through IR25-3 are complete on the final executable candidate:

1. run every focused Revision-22/23/24/25 P7 namespace/state/proof/root/mutation/concurrency counterfactual;
2. run the complete still-binding Revision-20/21 CampaignStore/P7 set and R19 affected proof/topology tests;
3. run full `tests/test_mlff_storage_reset_core.py`;
4. run full `tests/test_mlff_storage_reset_integration.py`;
5. run affected P1/P3/P4/P5/P7 currentness/publication/restart/retention/qualification-owner tests plus P6 destructive closure where the common owner/inventory/executor path is affected;
6. re-derive the affected surface from the completed repair diff;
7. run a fresh final affected regression/integration set after that re-derivation;
8. run CPU-safe broader/full repository tests if impact cannot be confidently bounded;
9. run static checks and affected current specification/document build validation.

Record actual commands, pass/fail/skip summaries or equivalent, exact executable commit, and executable tree. A docs/generated-only successor may reuse evidence only after compare proves no executable/configuration/persistence/test-harness contract changed.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

---

## 5. Preservation boundary

Do not redesign or reimplement conforming work merely because the candidate is reopened.

Preserve:

- the descriptor-relative strict attempt-state census and its absence/ambiguity taxonomy;
- Revision-23 malformed-state totality/report availability;
- generation-scoped release-root publication and cross-generation proof refusal;
- v3 proof/state binding/publication/released-state checks;
- workspace-wide unknown-state retention reduction;
- deterministic attempt-state synchronization and established lock order;
- the single `OwnerSynchronization.to_dict()` including `attempt_roots`;
- CampaignStore writer gate/observational purity repairs;
- existing P5 typed proof, archive/dedup/restore/audit/admission/control-plane architecture;
- updated current storage specification except where wording must be reconciled to the actual final mutation realization;
- all frozen P1-P7 scientific/currentness/publication/qualification semantics.

No persistent inode/path authority ledger or second P7 state machine is authorized.

---

## 6. Rework route and exit criteria

Resume at the already bounded **R21-E2** surface:

```text
IR25-1  single descriptor-bound P7 view + exact proof/certification authority
   -> focused namespace/proof regression
IR25-2  identity-preserving/refusing final P7 mutation for directories + files
   -> real-executor last-transition race regression
IR25-3  proxy-proof fixture corrections + structural absence guard
   -> full focused Revision-22/23/24/25 counterfactual set
IR25-4  R21-E5/F exact-candidate final acceptance
```

Stage-local semantic/conformance and affected regression closure are required before dependent work proceeds.

### Redesign trigger

If the supported POSIX/Linux runtime cannot provide a mutation realization that preserves the Revision-24 expected-root identity through the destructive syscall **and** unconditional refusal would materially defeat the accepted released-scratch product capability, stop and reopen only that mutation-boundary design surface. Do not accumulate additional check-then-act wrappers and call them race closure.

### Exit

A future PASS requires all of the following on one exact executable candidate:

- no parallel followable P7 attempt namespace/proof path remains in storage-facing view/certification;
- generation-scoped proof and strict state authority remain intact;
- every P7 released-scratch mutation preserves expected root/member identity to the actual destructive boundary or truthfully refuses;
- corrected proxy-proof tests fail if those protections are removed;
- exact-candidate focused + affected regression + integration evidence passes.

**Disposition:** Revision-24 design remains closed. Executable `8e87bc8...` is **NO-PASS / reopened under Revision 25**.