---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R24
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
amended_date: 2026-09-02
reviewed_authority_revision: 23
reviewed_plan_head: f16c26da1209f72d754367bf530d1dfdd1579cad
reviewed_plan_tree: 18183f911ab2e8c6d5abda45acef1020575f7a1d
reviewed_executable_commit: 9da6525be75c328ffbbf6968cebe773e2dc8921e
reviewed_executable_tree: 7ff82374cbc966795e710f21ba3737d892af57f2
review_verdict: PLAN-CORRECTION-REQUIRED
scope: final independent closure challenge of the Revision-22/23 repair handoff; preserve every accepted repair and close the remaining descriptor-root continuity, generation-scoped released-attempt root identity, namespace-race classification, consequential-consumer, and mutation-boundary gaps
precedence: Revision 21 remains the accepted final repair design. Revisions 22 and 23 remain binding in full except where this amendment makes their descriptor/root-identity and acceptance instructions more precise. This amendment does not reopen parent storage architecture, CampaignStore design, or P1-P7 scientific/currentness semantics.
---

# Storage/I-O reset repair-plan final closure — Revision 24

## 0. Review disposition

A second independent review of the **reopened implementation plan itself** found two material authority gaps and several related acceptance ambiguities that remain after Revisions 22 and 23:

1. Revision 22 closes P7 namespace traversal at the owner reader, but does not explicitly preserve that authenticated directory identity through the common `OwnerArtifactView` / `StorageInventorySnapshot.authorized_members()` / cleanup-mutation path. The current executable can therefore re-enter a pathname walk after strict P7 authentication has already succeeded.
2. Revision 19 requires the v3 released-attempt proof to bind the **exact attempt root identity**, but the composed repair contract never freezes what that identity means. The current executable consequently treats `attempt_root` as only the attempt-directory basename. A whole, internally consistent released attempt copied under another generation can therefore look like P7-owned scratch for that other generation.

Revision 23's malformed-state and diagnostic-serializer findings remain correct. Revision 22's descriptor-based direction remains correct. This amendment makes the repair contract lossless from namespace acquisition through exact certification and the final destructive boundary, and gives `exact attempt root` one canonical generation-scoped meaning.

No target-size, P2/P3/P4/P5/P7 scientific/currentness/publication/qualification/calibration/locked/release behavior is reopened. The executable remains **NO-PASS / reopened** until the combined Revision-22/23/24 repair and exact-candidate functional acceptance are complete.

---

## 1. R24-A — the strict P7 namespace result must own an identity-bearing traversal, not merely recommend safer syscalls

### 1.1 Stable acquisition boundary

Revision 22 requires descriptor-relative no-follow descent but leaves enough freedom for an implementation to authenticate one component and then reconstruct a descendant path from strings. That recreates the same authority gap one level later.

The required end state is one P7 storage-facing namespace acquisition whose authority-bearing descent is continuous:

```text
accepted campaign workspace/internal identity
 -> literal qualification family
 -> canonical g<generation>
 -> literal attempts container
 -> exact attempt directory
 -> attempt-state.json / attempt-members.json / exact descendants
```

Requirements:

1. Establish one already-accepted campaign parent identity, then open every P7 authority-bearing child relative to that authenticated parent with a no-follow directory/file primitive on the supported POSIX/Linux target. The workspace root may itself be a supported mount, as frozen by R13; this repair must not accidentally outlaw that. The campaign-owned `.mdstats`/internal hop must not become a newly followable escape merely because it is used as the parent of the strict P7 walk. If the repository currently promises a path form that cannot be reconciled with this identity-bearing parent contract, trigger the existing Revision-21 platform/path redesign condition rather than silently following it.
2. Directory opens use `O_DIRECTORY|O_NOFOLLOW` (plus ordinary read/close flags) or an equivalent identity-bearing primitive and verify the descriptor with `fstat()`.
3. Child opens are relative to the already authenticated parent descriptor (`dir_fd` / openat-style or equivalent). Do not authenticate a parent, close/forget that identity, and then re-resolve the child's absolute pathname as authority.
4. Enumeration is from the authenticated directory identity. Names discovered by enumeration are **names**, not fresh authority-bearing paths. A `DirEntry.path` or reconstructed `Path` may be retained for bounded diagnostics/display, but it must not be the primitive used to confer state, proof, or descendant ownership.
5. File reads for state/proof are relative no-follow regular-file opens from the authenticated attempt descriptor, followed by `fstat()` and parsing from that descriptor.
6. Exact descendant observation for released-attempt certification descends directories relative to authenticated parent descriptors and never follows symlinks. Symlink/special/wrong-kind nodes remain contradictions exactly as R19 requires.
7. The strict traversal must preserve R13 mount-boundary semantics. A workspace or authorized owner root may itself be mounted; a **nested mount below the authorized attempt/member root is not P7-owned merely because descriptor traversal can enter it**. Reuse the current mount-identity owner or an equivalent check; uncertainty retains.
8. Descriptors are invocation-local observation handles, not persistent authority. Close them deterministically on success, refusal, and exceptions. Do not persist file descriptors, inode ledgers, or a second storage state machine in the plan/control plane.

### 1.2 Canonical result contract

The strict acquisition must return one canonical result (an equivalent representation is acceptable) carrying enough information that downstream storage does not need to rediscover the namespace:

- canonical generation number and canonical `g<generation>` name;
- canonical attempt identity/name;
- lexical/display attempt path;
- the authenticated attempt-root filesystem identity observed from the descriptor (at minimum device/inode/kind for the current snapshot);
- authenticated `QualificationAttemptState`, or an explicit unresolved reason;
- for exact certification only, the authenticated bound proof and typed observed/certified node result.

A long-lived storage plan may serialize ordinary owner state/filesystem identities as it already does, but it must not serialize an open descriptor. Consequential apply rebuilds the strict result under the established owner synchronization before mutation.

### 1.3 Absence versus race/ambiguity is exact

Do not turn arbitrary filesystem errors into absence.

- A qualification family genuinely absent at the authoritative lookup is ordinary "no P7 family".
- The literal `attempts` child genuinely absent at its authoritative lookup is ordinary "no attempts for this generation".
- An entry that was enumerated and then disappears before its authority-bearing open is **namespace changed during observation**, not silently absent.
- `ELOOP`, `ENOTDIR`, `EACCES`, `ESTALE`, `EIO`, unsupported kind, descriptor-identity mismatch, and equivalent inability to authenticate a present/observed authority-bearing component are unresolved owner authority.
- Do not retry an unbounded number of times until a convenient answer appears. A bounded retry may be used only for a documented transient race; exhaustion is unresolved and therefore fail-closed.

### 1.4 Canonical generation names are not aliases

Reuse/extract the repository's production generation parsing rule. A generation namespace that participates in P7 authority must have exactly the canonical spelling produced by the owner (`g` followed by the canonical integer spelling; for example `g1`, not `g01`, `g+1`, or another normalization alias). A malformed reserved `g*` entry is an integrity problem, not a second namespace that may be searched for state.

### 1.5 Revision-23 parser totality is refactor-neutral

Revision 23 names `authenticate_attempt_state()` because that is the current function. The contract is semantic, not a demand to preserve a path-taking helper.

If the descriptor repair splits acquisition from parsing, the **canonical strict storage-facing state parser** must still be total over expected persisted-record corruption exactly as IR23-1 requires: `KeyError`, `TypeError`, `ValueError`, `TrainingDataInputError`, `TrainingDataSerializationError`, and any other narrowly demonstrated record-shape validation exception become explicit unresolved authority. Do not preserve a path-racy storage reader merely to satisfy the old function name, and do not hide programmer/system failures behind blanket `except Exception`.

### Focused acceptance

In addition to every Revision-22/23 case:

- canonical `g1` succeeds, while otherwise valid state under `g01` is unresolved and never contributes P7 authority;
- deterministically enumerate a generation/attempt entry, remove or replace it before the descriptor-relative open, and prove the result is unresolved rather than "absent";
- inject `EACCES`/`ESTALE` at the real directory-open seam and prove report stays available while planability/fence fail closed;
- prove normal report retains its descendant-count bound after the descriptor/result consolidation;
- model a nested mount under released P7 scratch using the existing deterministic mount resolver and prove descriptor traversal does not cross it.

---

## 2. R24-B — `exact attempt root identity` is generation-scoped and portable

### 2.1 Gap

The v3 proof currently carries an `attempt_root` field, but the accepted contract never states whether that means an absolute path, basename, inode, or generation-scoped owner locator. A basename is insufficient because attempt scratch belongs to **one generation namespace**, not to every `qualification/g*/attempts/<same-name>` path.

### 2.2 Frozen root identity

For storage destructive authority, the released-attempt root identity is the canonical, workspace-portable locator relative to the qualification family:

```text
g<campaign_generation>/attempts/<attempt_identity>
```

An equivalent canonical tuple/digest over `(campaign_generation, attempt_identity)` is acceptable, but it must carry the same information and be independently recomputable from the authenticated namespace snapshot. Absolute workspace paths are not part of durable identity because moving/restoring the whole campaign workspace must not change P7 semantics.

Requirements:

1. The v3 released-attempt proof binds this generation-scoped root identity in its self-authenticated payload. R19 already required an exact root identity; this is a clarification/completion of v3, not a new scientific proof system.
2. The P7 **owner publication path** derives the locator from the authoritative `PostSelectionBinding.campaign_generation` and the canonical attempt identity supplied to `release_attempt_reference()`. Do not infer publication authority by parsing whatever parent pathname happens to contain the file.
3. The strict storage reader independently recomputes the expected locator from the descriptor-authenticated generation namespace and attempt name and requires exact equality with the proof.
4. Continue to require the existing state/proof cross-field relations: state digest, attempt identity, released state, qualification binding digest, and publication digest. Root binding is additional; it does not replace them.
5. A proof copied intact to another generation therefore remains self-consistent but is **not bound to that root** and grants no reclamation authority there.
6. The incomplete development v3 form whose `attempt_root` is only a basename may be recognized for diagnosis but grants no new destructive authority under the completed contract. Do not "upgrade" a terminal proof by scanning the current scratch tree.
7. No automatic compatibility migration is required for destructive authority. If a metadata-only migration is implemented, it is permitted only when the old state and old proof already authenticate completely, the real P7 owner has an authoritative binding/generation for that exact attempt, and the typed node set is reused from the authenticated old proof without rescanning current scratch. Otherwise retain and fail closed.
8. Do not change the production qualification `attempt_identity` formula to solve this storage problem. Generation-scoped root identity is a storage-facing ownership binding, not a new scientific attempt identity.

### Required acceptance

- produce a valid released attempt under `g1`, copy the **entire** state + v3 proof + same-shaped scratch tree under `g2/attempts/<same-attempt-name>`, and prove the copied tree is unresolved/not reclaimable specifically because its proof binds the wrong generation-scoped root;
- the original `g1` attempt remains valid/reclaimable if otherwise eligible;
- a basename-only legacy/development v3 proof grants no cleanup authority;
- a correct generation-scoped proof remains idempotent across repeated terminal release and does not rescan/rewrite scratch;
- workspace relocation does not invalidate the portable root locator.

---

## 3. R24-C — descriptor/root authority must survive through common certification and the final mutation boundary

### 3.1 Gap

Revision 22 stops the P7 owner from discovering state through a substituted ancestor, but the current common path can discard that root identity afterwards:

```text
strict P7 owner result
 -> OwnerArtifactView(certified_nodes=...)
 -> StorageInventorySnapshot.authorized_members(view)
      -> observed_node_kind(view.path)
      -> walk_contained(view.path)
 -> remove_certified_subtree(view.path, ...)
      -> pathname/rmtree mutation
```

Typed node names alone do not preserve which directory those names were certified beneath. The same issue exists if a specialized engine takes a descriptor-certified P7 result and then starts a new followable/path-only traversal before acting.

### 3.2 Required end state

1. A released P7 `CLOSED` subtree cannot obtain consequential authority from `certified_nodes` plus a fresh generic pathname walk alone. The common inventory/executor path must either consume a P7 exact-certification result that is bound to the authenticated root identity, or freshly invoke the strict descriptor-bound P7 certification under the owner seams immediately before mutation.
2. `StorageInventorySnapshot.authorized_members()` may remain generic for owners whose accepted authority is safely represented that way, but for P7 released attempts it must not silently downgrade the R24-A result to `walk_contained(root)` through a newly resolved path. A clean owner-specific delegation inside the existing owner adapter/inventory boundary is preferable to creating a second P7 state machine.
3. Consequential apply still follows the accepted order: storage-operation lease -> owner barriers/attempt lock -> fresh strict inventory/certification -> plan/filesystem/admission revalidation -> narrow mutation.
4. The action/root filesystem identity captured by the plan and the freshly descriptor-observed root identity must agree before action. A wrong-generation, replaced, or different-inode root is stale/refused even when its descendant names/kinds look identical.
5. The final removal primitive must not **re-follow an unauthenticated ancestor chain** after exact certification. `shutil.rmtree.avoids_symlink_attacks` remains useful for recursion beneath a root, but it is not by itself proof that an independently authenticated top-level P7 root has not been replaced before the recursive call begins.
6. Acceptable realizations include a descriptor/parent-relative removal sequence that preserves the authenticated root, or a final exact re-open/revalidation at the mutation seam followed by a platform primitive whose top-level identity behavior is proven sufficient. If the platform/runtime cannot preserve root authority for recursive container removal, retain the container and remove only individually authorized regular files using a no-follow identity-preserving operation, or refuse the action. Never choose a weaker traversal merely to obtain reclamation.
7. A symlink/special/unexpected node or nested mount discovered during this final exact check reduces authority exactly as R19/R13 require; it is not an excuse to fall back to path-only deletion.
8. Storage/P7 attempt locking protects against supported P7 writers, not arbitrary namespace replacement. Do not treat possession of the advisory attempt lock as proof that the directory entry itself cannot have changed.

### Required acceptance

Use the real P7 owner, real inventory, real cleanup planner/executor, and production attempt lock.

1. Build a real released-attempt cleanup plan. During apply, allow the under-lock strict resnapshot/certification to finish, then deterministically replace an authority-bearing ancestor/root **before the common member-authorization/final removal seam** with a symlink to a same-shaped foreign tree. Resume execution. The foreign target must remain byte-for-byte untouched and the action must refuse/retain rather than treating the earlier certification as transferable.
2. Repeat with a replacement **plain directory** (not a symlink) having the same expected descendant names/kinds but a different root inode. It must not be recursively removed.
3. If the implementation carries a descriptor through certification into mutation instead, inject the race at the last name-based transition that still exists and prove the same result.
4. Retain the existing nested-symlink/special-node tests and add the P7 nested-mount case from R24-A.
5. Structural inspection must prove no P7 released-attempt cleanup/archive/dedup/reclaim consumer can turn an exact descriptor-bound certification into a path-only recursive authorization before mutation.

---

## 4. R24-D — implementation routing and affected surface

This is still the bounded **R21-E2** repair. Do not reopen CampaignStore R21-E3 unless the final diff actually touches it.

### R24-D1 — namespace primitive and strict state authority

Implement R24-A together with R22 family-root/ancestor traversal and R23 parser totality. Establish one strict result and update P7 storage-facing census, retention, reporting, and views to consume it.

Stage-local closure:

- R22 family-root, generation, attempts-container, attempt-root static and race cases;
- R23 malformed-state/report-availability cases;
- R24 canonical-generation/error-taxonomy/nested-mount cases;
- existing missing/wrong-root/missing-digest/canonical-binding cases.

### R24-D2 — exact root proof binding

Complete the v3 root identity under R24-B and update the owner publication/strict proof reader. Run copied-cross-generation, legacy-basename, repeated-terminal, proof-tamper, and aborted-reopen lifecycle regression before proceeding.

### R24-D3 — consequential continuity

Route exact P7 certification through common `authorized_members()` / cleanup execution without losing root identity, and close the final mutation seam under R24-C. Run the post-resnapshot symlink/plain-directory swap cases through the real executor plus existing P7 cleanup, interruption/retry, mount, and synchronization tests.

### R24-D4 — final affected-surface re-derivation

Expected affected surfaces now include at minimum:

- `mdstats/training_data/qualification/store.py`;
- `mdstats/training_data/qualification/runtime.py` only where owner publication or lock usage must pass authoritative generation/root material;
- `mdstats/training_data/storage/owners.py`;
- `mdstats/training_data/storage/inventory.py`;
- `mdstats/training_data/storage/commands.py` / `storage/executor.py` if required to preserve exact P7 root identity into mutation;
- `mdstats/training_data/storage/lease.py` for the already-required serializer cleanup only unless synchronization mechanics actually change;
- `mdstats/training_data/storage/trust.py` only if descriptor traversal needs a reusable mount check without weakening current semantics;
- `tests/test_mlff_storage_reset_core.py` and `tests/test_mlff_storage_reset_integration.py`;
- affected P7 owner/currentness tests;
- `docs/specs/training_data/mlff_storage_management_spec.md` because the durable released-proof root-identity and fail-closed authority semantics are governed persistence/storage contracts.

Re-derive this list from the **final diff**; it is a floor, not a whitelist.

---

## 5. Documentation / compatibility requirements

1. Update the current storage specification to state the generation-scoped released-attempt root identity and descriptor/root-continuity rule. This is a persisted-proof/destructive-authority contract and therefore belongs in the specification, not only in a workplan.
2. Update architecture/user documentation only if the final implementation materially changes current ownership/components or operator-visible behavior. Do not edit permanent manuals merely to record Revision-24 gate history.
3. Preserve the current supported POSIX/Linux contract already assumed by Revision 22. Do not silently claim portable no-follow semantics on a platform where the required primitives are absent.
4. Legacy/incomplete proof records may remain diagnosable and conservatively retained. No compatibility shim may manufacture new destructive authority by scanning a depleted/tampered tree.
5. No new persistent namespace ledger, inode registry, or recovery database is authorized.

---

## 6. Final acceptance remains candidate-bound

After R24-D1 through D3 are semantically and functionally closed, perform the complete Revision-22/23 final evidence sequence on the **exact final executable commit/tree**, with these additions:

- all R24-A/B/C counterfactuals;
- full `tests/test_mlff_storage_reset_core.py`;
- full `tests/test_mlff_storage_reset_integration.py`;
- affected P1/P3/P4/P5/P7 and P6 destructive-path regression required by Revision 22;
- final affected-surface re-derivation and a fresh affected regression/integration pass;
- CPU-safe broader/full tests when the final impact cannot be confidently bounded;
- static checks plus current specification/document build validation.

Record commands, pass/fail/skip summaries or equivalent, exact executable commit, and executable tree. `not run` is not `pass`. Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

---

## 7. Final plan-closure challenge

After adding R24-A through R24-C, the repair contract now explicitly preserves:

- the trusted namespace identity from the first P7 authority-bearing directory open through state/proof parsing and exact descendant certification;
- exact generation-scoped released-attempt root ownership rather than basename containment;
- typed/symlink/special/mount refusal under the descriptor traversal;
- fail-closed namespace-change/error semantics;
- the same root identity through the common inventory and final destructive boundary;
- Revision-23 malformed-state report availability;
- Revision-22 deterministic concurrency/proxy-proof requirements;
- exact candidate-bound final regression/integration evidence.

No additional architecture, persistent authority, or P1-P7 science change is required.

**Design/workplan disposition after this amendment:** **CLOSED / implementation-ready.** The executable remains **NO-PASS / reopened** until Revisions 22, 23, and 24 are implemented and evidenced.