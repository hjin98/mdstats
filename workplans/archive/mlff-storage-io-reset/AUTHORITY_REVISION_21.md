---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 21
status: reopened
amended_date: 2026-09-02
current_authority_pointer: true
supersedes_authority_revision: 20
reviewed_executable_commit: 869ae1b6e9211faa1873d47e7850050cd85b5ff7
reviewed_executable_tree: a5e6c8868bdec9e88a877e6ca84aa6ef6d609286
review_verdict: NO-PASS
precedence: Revision 21 is the final design-closure amendment to the bounded Revision-20 implementation repair. Revision 19 remains the accepted storage architecture. Revision 20 remains binding except where this revision strengthens P7 attempt-state identity, namespace traversal, single-reader authority, retention-fence defense in depth, acceptance counterfactuals, and authority routing. AUTHORITY.md is the sole canonical navigation entrypoint; current_authority_pointer fields in superseded revision artifacts are historical metadata only.
---

# Storage/I-O reset package authority — Revision 21 final repair-plan closure

## 0. Disposition

**DESIGN CLOSED / IMPLEMENTATION REOPENED.**

Revision 20 correctly bounded the remaining implementation work to CampaignStore observational purity, strict P7 attempt-state census and terminal proof validation, and candidate-bound acceptance evidence. A final independent challenge found four plan-level gaps in the P7 storage-authority contract. This amendment closes those gaps without reopening Revision-19 architecture or any P1-P7 scientific behavior.

The executable remains **NO-PASS / reopened** until the combined Revision-20 + Revision-21 repair and exact-candidate functional acceptance are complete.

The accepted architecture remains:

```text
semantic P1-P7 owners
  -> authenticated owner views
  -> owner-derived inventory and cross-owner protection closure
  -> policy/admission
  -> immutable owner-bound storage plan
  -> shared owner synchronization
  -> fresh owner/inventory revalidation
  -> physical ownership boundary
  -> narrow mutation
  -> restart-equivalent product
```

Storage never becomes a second scientific authority. Unknown ownership/liveness reduces destructive authority; it is never reconstructed by pathname guessing.

## 1. Current supplied implementation contract

Implementation must read these artifacts together:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md`;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md`;
3. `AUTHORITY_REVISION_11.md`;
4. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_1.md`;
5. `STORAGE_IO_MANAGEMENT_RESET_REPAIR_PLAN_CLOSURE_AMENDMENT.md`;
6. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_DESIGN_CLOSURE_AMENDMENT.md`;
7. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_2.md`;
8. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_16.md`;
9. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_3.md`;
10. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_18.md`;
11. `STORAGE_IO_MANAGEMENT_RESET_FINAL_REPAIR_PLAN_CLOSURE_REVISION_19.md`;
12. `STORAGE_IO_MANAGEMENT_RESET_IMPLEMENTATION_REVIEW_REOPEN_4.md` (Revision 20);
13. this Revision-21 authority.

`AUTHORITY.md` is the sole canonical navigation entrypoint. Earlier `current_authority_pointer: true` fields in superseded revision files are historical metadata and do not compete with `AUTHORITY.md` or this revision.

Revision 21 **adds to and narrows** Revision 20. It does not remove any Revision-20 obligation unless explicitly stated below.

## 2. Frozen preservation / non-goals

Preserve all conforming R12-R19 implementation and all Revision-20 requirements not explicitly strengthened here.

Do not redesign or reopen:

- target-size selection science, statistical rules, or V7 parent verdict;
- P3/P4 currentness semantics;
- P5 CV/final-production science or publication membership;
- P7 qualification, calibration, locked-test, reference, verdict, or release science;
- P5 typed topology representation already accepted;
- P7 v3 typed released-attempt proof representation and proof-first/state-second publication ordering;
- storage/archive/dedup/restore architecture;
- CampaignStore RLock/flock writer-gate architecture;
- storage audit/control-plane architecture.

The only newly frozen design surface is how storage authenticates and conservatively consumes P7 attempt-state authority.

## 3. R21-A — canonical P7 attempt identity is a three-way invariant

### Protected concern

A state file that is self-digest-valid and stored under a matching directory name is still not necessarily the state of the qualification binding it claims to represent. P7 attempt identity is canonically derived from the qualification binding digest. Storage must authenticate that semantic relation before accepting liveness or release authority.

### Required end state

For every storage-facing P7 attempt state, all of the following must agree:

```text
attempt_root.name
== state.attempt_identity
== canonical_attempt_identity(state.binding_digest)
```

`canonical_attempt_identity(binding_digest)` means the exact production identity rule already owned by qualification (`mdstats.qualification-attempt-identity.v1` over the qualification binding digest). Reuse/extract the production helper rather than duplicating a second hashing convention where practical.

This check is in addition to, not instead of:

- current state schema validation;
- persisted `content_digest` presence and exact recomputation;
- valid `binding_digest` and `publication_digest` fields;
- no-follow regular-file authority reads;
- proof/state cross-field checks for released attempts.

A mismatch is unresolved owner state and therefore a global consequential-planning failure. Do not repair or rename the state automatically, infer a new binding, or trust the directory name as independent semantic authority.

### Required acceptance

Add a real-owner counterfactual where:

1. the attempt directory name is a valid digest;
2. `state.attempt_identity` exactly equals that directory name;
3. `state.content_digest` is recomputed and valid;
4. `state.binding_digest` is changed so the canonical binding-derived attempt identity is different.

The strict reader/census must reject it, reporting must name the identity inconsistency, `require_planable()` must fail, and no external P5 reference may be released from protection because of that state.

Repairing the exact canonical relation must restore normal planning without any migration-by-guessing.

## 4. R21-B — one strict storage-facing P7 state authority, not parallel permissive readers

### Protected concern

Revision 19 requires one strict P7 state/proof authority for storage-facing decisions. A strict census paired with a weaker `read_attempt_state_at()` or direct `from_dict()` path can create contradictory owner views: the global graph says "unknown" while a local classifier still derives release/reclaimability from the same state.

### Required end state

Create or consolidate one **root-bound strict attempt-state result** that is the sole authority for all storage-facing P7 semantics. It must return either:

- one authenticated state bound to its exact attempt root; or
- an explicit unresolved/integrity result with path/root and reason.

All storage-facing consumers must use that result or a result derived directly from it, including:

1. attempt census and active external-reference collection;
2. `qualification_views()` active/aborted/terminal classification;
3. exact released-attempt proof certification;
4. `build_qualification_retention_fence()`;
5. storage-facing reporting of attempt state/ambiguity;
6. synchronization/touched-attempt derivation wherever state classification is material.

The generic `QualificationAttemptState.from_dict()` may remain permissive only as a lower-level compatibility parser for an independently justified non-destructive runtime path. It must not independently confer storage liveness, release, reclaim, archive, dedup, or cleanup authority.

Do not implement a second storage-specific state machine. This is consolidation of authentication at the P7 owner boundary.

### Required acceptance

For every Revision-20 malformed/missing/wrong-root/missing-digest case, assert both:

- global planning fails; and
- the P7 owner view exposes **no reclaimable/released scratch authority derived from the rejected state**.

A test that proves only `require_planable()` is red is insufficient; it could remain green while a parallel local reader continues to classify the attempt as released.

## 5. R21-C — no-follow namespace traversal applies to every P7 authority-bearing ancestor

### Protected concern

`O_NOFOLLOW` on `attempt-state.json` protects only the final component. Storage must not reach an otherwise valid state through a symlinked/special generation directory or `attempts` container.

### Required end state

The strict census descends the P7 owner namespace without following substituted authority-bearing directory components.

For each candidate generation/attempt namespace:

1. classify the qualification family root according to the already accepted workspace/owner boundary;
2. enumerate candidate `g*` entries without following symlink targets;
3. require a generation entry used for P7 state authority to be a plain directory;
4. require its literal `attempts` child, if present and used as an attempt namespace, to be a plain directory;
5. enumerate attempt entries no-follow;
6. require each actual attempt entry to be a plain directory;
7. require `attempt-state.json` to be a strict no-follow regular file;
8. never traverse a symlink/special/unreadable required namespace component to discover state or proof behind it.

A symlink, special node, unreadable node, or wrong-kind node in an authority-bearing namespace is an integrity failure. It may be reported, but its target does not contribute P7 state, reference, proof, or reclamation authority.

Do not rely on `Path.glob(...).is_dir()`/`Path.is_dir()` semantics where those operations can follow the very symlink being classified.

Normal bounded reporting must remain bounded; this change must not make it hash or walk released attempt descendants merely to classify namespace components.

### Required acceptance

In addition to Revision-20 state-file and attempt-root symlink tests:

- replace a `g<generation>` directory entry with a symlink to a directory containing otherwise valid P7 attempt state;
- separately replace `g<generation>/attempts` with such a symlink;
- include a safely modeled special/wrong-kind namespace component where feasible.

In each case, the target bytes must not be consumed as P7 authority; reporting must identify the namespace corruption; consequential planning must fail closed; external P5 artifacts must remain untouched.

## 6. R21-D — unknown P7 state imposes a workspace-wide retention reduction

### Protected concern

Unknown P7 state is globally blocking precisely because the lost `referenced_paths` may name managed artifacts **outside the P7 tree**, especially P5 publication checkpoints. Widening the retention fence only to `.mdstats/qualification` does not protect the asset whose identity is unknown.

### Required end state

`build_qualification_retention_fence()` consumes the same strict census from R21-B.

If **any** attempt state/authority-bearing namespace is unresolved such that its external reference set cannot be authenticated, the P7 retention fence enters an explicit ambiguity mode that denies destructive authorization for every campaign-managed path in the workspace until the ambiguity is repaired.

Preferred representation is an explicit field/state such as:

```text
ambiguous_attempt_state = true
```

with a bounded reason set, rather than synthesizing the workspace root into `referenced_paths`. Equivalent implementation is acceptable if it preserves the semantics cleanly.

The fence remains a **reduction only**: it cannot grant ownership or deletion authority. It is defense in depth behind the mandatory `StorageInventorySnapshot.require_planable()` owner-graph gate.

Do not guess the unknown reference set, scan P5 for likely checkpoints, or invent synthetic owner edges.

Once every P7 attempt state is again strictly authenticated, the blanket ambiguity reduction disappears and the fence returns to exact active `referenced_paths` plus durable P7 evidence protection.

### Required acceptance

Use the real retention fence and real `CampaignOwnershipBoundary`:

1. create a real P7 attempt that references an exact P5 publication checkpoint;
2. corrupt/remove its state so the strict census cannot authenticate the reference set;
3. prove normal owner-graph consequential planning fails;
4. **independently call the real physical destructive authorization boundary for the P5 checkpoint while bypassing the inventory planner in the test**;
5. prove the boundary still refuses destructive authorization due to P7 ambiguity;
6. prove an unrelated campaign-managed path is likewise denied while ambiguity exists;
7. repair the exact state and prove the blanket ambiguity disappears; normal eligibility is again decided by exact owner graph and exact references.

This direct boundary test is intentional defense-in-depth acceptance. It does not replace the real planner/executor integration test required by Revision 20.

## 7. Revision-20 obligations retained verbatim in effect

Implementation must still satisfy all Revision-20 source repairs and acceptance obligations, including:

### CampaignStore observational purity

- `_require_writable("replace campaign records")` is the first executable action in `replace_records_atomically()`;
- remove the accidental duplicate/misnamed `put_records()` guard;
- re-derive every CampaignStore mutator for pre-side-effect observational refusal;
- test a forced-external or >4 MiB replacement and prove no record, writer-lock, WAL/SHM/journal, receipt, DB, or other managed mutation occurs.

### P7 strict current-state requirements

- enumerate actual attempt directories rather than only state files;
- missing/symlinked/unreadable/malformed/unsupported state is explicit unresolved authority;
- require persisted current `content_digest` and exact recomputation;
- require root/state identity agreement, now strengthened by R21-A canonical binding-derived identity;
- propagate unresolved authority into owner integrity/global `require_planable()`;
- use the same strict census for retention, now strengthened by R21-D workspace-wide ambiguity.

### Terminal released-attempt proof

- repeated terminal release validates and reuses the retained v3 proof under the attempt lock;
- never rebuild terminal proof by rescanning a possibly depleted tree;
- missing/v2/malformed/self-invalid/state-mismatched/root/attempt conflict fails closed;
- validate proof `binding_digest` and `publication_digest` against the exact state;
- preserve aborted -> active -> released lifecycle.

### Concurrency and typed authority

- preserve touched-attempt synchronization and established lock order;
- add deterministic aborted-reopen versus real storage cleanup races in both lock orderings;
- preserve typed/no-follow P5/P7 authority through common inventory/executor;
- retain special-node, symlink, file/directory substitution, unexpected-node, and bounded-report tests.

## 8. Implementation stages and gates

This remains bounded implementation repair, not redesign.

### Gate R21-E2 — P7 owner authority closure

Implement Revision-20 P7 census/proof repairs plus R21-A through R21-D as one coherent owner-authority stage.

Before dependent final acceptance:

- perform semantic/conformance inspection that there is one strict storage-facing state authority and no remaining permissive storage consumer;
- run the complete focused P7 state/proof/namespace/retention counterfactual set;
- run affected P5/P7 storage-owner regression, including the existing attempt-state synchronization race.

### Gate R21-E3 — CampaignStore observational closure

Implement Revision-20 CampaignStore guard repair and rerun the writer/mutator affected regression, including real externalization-side-effect absence.

R21-E2 and R21-E3 may be implemented in either order because neither depends semantically on the other, but each must achieve stage-local semantic + functional closure before final acceptance.

### Gate R21-E5/F — assembled final acceptance

After all executable repair is complete:

1. reconcile the full Revision-19 + Revision-20 + Revision-21 accepted contract against source;
2. focused Revision-20/21 counterfactuals plus all still-binding R19-A through R19-D focused tests;
3. every still-binding R17/R18 focused storage test affected by the repair;
4. full `tests/test_mlff_storage_reset_core.py`;
5. full `tests/test_mlff_storage_reset_integration.py`;
6. affected P1/P3/P4/P5/P7 currentness, publication, restart, retention, qualification-owner tests and P6 destructive closure where common owner-proof/executor behavior is affected;
7. re-derive final affected surface from the **completed repair diff**;
8. run a fresh final affected regression/integration set after re-derivation;
9. run CPU-safe broader/full repository tests if impact cannot be confidently bounded;
10. run static checks and affected docs/spec/build validation.

Record commands, results, exact executable commit, and executable tree. `not run` is not `pass`. A docs/generated-artifact-only successor may reuse evidence only after exact compare establishes that no executable/configuration/persistence/test-harness contract changed.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not functional-acceptance blockers.

## 9. Required proxy-proof counterfactual inventory

The final candidate must include evidence capable of failing if the real owner is broken for at least these cases:

- read-only `replace_records_atomically()` crossing a real externalization boundary;
- missing P7 state;
- state symlink;
- attempt-root symlink;
- generation-root symlink;
- `attempts`-container symlink;
- wrong-root copied but self-digest-valid state;
- state/root names agreeing while canonical binding-derived attempt identity disagrees;
- missing persisted current-state digest with modified liveness/reference fields;
- malformed/corrupt current state;
- global planner blocker plus independent workspace-wide retention-fence refusal for an external P5 checkpoint;
- valid repeated terminal release without proof rewrite/rescan;
- missing terminal proof;
- corrupt proof self digest;
- recomputed self digest with conflicting proof binding/publication fields;
- released attempt with foreign top-level/nested file or empty directory;
- same-path file/directory substitution;
- symlink and special-node substitution;
- deterministic aborted-attempt reopen versus real cleanup in both lock orderings.

Use the real P7 owner, real storage inventory/planner/executor/physical boundary, real CampaignStore persistence, and real production attempt-state lock wherever those semantics are under acceptance. Bounded scientific/ML/external-service dependencies below those owners may remain faked or reduced.

## 10. Structural/absence acceptance

Source/conformance review must establish:

- no storage-facing P7 consumer obtains attempt release/liveness authority through a permissive raw JSON/deserializer path beside the strict owner result;
- no P7 census traverses symlinked authority-bearing namespace ancestors;
- no unknown-state retention implementation merely protects the P7 tree while leaving other campaign-managed paths authorizable;
- no path-only P5/P7 recursive authority has reappeared;
- no lock-order reversal was introduced;
- no CampaignStore public mutator can reach filesystem/receipt/lock/SQLite write side effects before observational writability validation.

These absence claims complement tests and are not replaced by them.

## 11. Final snapshot-loss and design-closure check

The supplied current artifact set now recovers, without Git history or prior conversation:

- the parent storage architecture and scientific non-goals;
- typed/no-follow P5/P7 ownership;
- P7 v3 proof publication and lifecycle;
- P7 attempt-state/storage synchronization;
- strict unknown-state global planning semantics;
- canonical binding-derived attempt identity;
- single strict storage-facing P7 state authority;
- no-follow ancestor traversal requirements;
- workspace-wide ambiguous-state retention defense in depth;
- CampaignStore writer/observational requirements;
- exact candidate-bound regression/integration acceptance and production-qualification deferral.

No additional persistent ledger or parallel authority system is required.

## 12. Redesign triggers

Reopen Design only if implementation evidence establishes one of the following:

1. the production qualification binding cannot provide the canonical attempt-identity relation without changing P7 scientific/currentness semantics;
2. strict no-follow P7 namespace enumeration cannot be implemented on the supported target platform while preserving existing owner layout, requiring a platform-contract decision;
3. a workspace-wide ambiguity reduction cannot be expressed as a pure retention denial without introducing a second ownership authority;
4. the accepted lock order cannot accommodate the consolidated strict owner reader without a real deadlock/inversion;
5. representative final affected testing exposes an architecture-level conflict outside this bounded repair.

Otherwise implementation has authority to reconcile local mechanics while preserving the frozen requirements above.

## 13. Final design disposition

**Revision 21 closes the repair plan.** No known plan-level blocking gap remains after the snapshot-loss, proxy-proof, ownership, path-traversal, recovery, concurrency, and acceptance challenge.

Implementation resumes only at the bounded R21-E2/R21-E3 repair surface and then completes R21-E5/F acceptance. The executable remains **NO-PASS until implemented and evidenced**; the **design/workplan itself is closed and implementation-ready**.
