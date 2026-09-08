---
kind: implementation-review-reopen
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1-R23
parent_workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: reopened
reviewed_date: 2026-09-02
reviewed_authority_revision: 22
reviewed_executable_commit: 9da6525be75c328ffbbf6968cebe773e2dc8921e
reviewed_executable_tree: 7ff82374cbc966795e710f21ba3737d892af57f2
reviewed_branch_head: 071387cb21c1a046f4ffa7b641bcdd3ad2da1699
review_verdict: NO-PASS
scope: final independent closure amendment to Revision 22; preserve all Revision-22 findings and add the remaining strict-state error-totality/report-availability requirement plus correction of the still-duplicated OwnerSynchronization diagnostic serializer
precedence: Revision 22 remains binding in full. This amendment adds requirements where Revision 22 was incomplete and corrects one factual closure note; it does not reopen Revision-21 design, accepted storage architecture, CampaignStore repair, or P1-P7 science.
---

# Storage/I-O reset implementation review reopen 6 — Revision 23

## 0. Disposition

**NO-PASS / reopened.**

Revision 22 correctly identifies and routes the remaining P7 namespace traversal/TOCTOU defect, deficient proxy-proof fixtures, and missing exact-candidate functional evidence. Those findings and repair instructions remain binding without dilution.

One additional source-level closure defect remains in executable `9da6525be75c328ffbbf6968cebe773e2dc8921e` / tree `7ff82374cbc966795e710f21ba3737d892af57f2`: the strict P7 attempt-state authority is not total over structurally malformed JSON objects. In addition, Revision 22's non-blocking note incorrectly states that `OwnerSynchronization.to_dict()` now exposes `attempt_roots`; the source contains a later duplicate method that overrides the new serializer and still omits that field.

This is bounded implementation repair. Preserve all conforming Revision-20/21 source work and all Revision-22 requirements.

---

## 1. IR23-1 — strict attempt-state authentication must convert record-shape failures into unresolved authority, not escape parser exceptions

### Finding

`authenticate_attempt_state()` correctly converts invalid JSON, schema/input errors, missing persisted digest, digest mismatch, and identity mismatch into `AttemptStateAuthority(..., state=None, reason=...)`. However it calls `QualificationAttemptState.from_dict(payload)` under an exception list that does not include ordinary structural failures raised by that deserializer.

The deserializer indexes required fields such as `attempt_identity`, `binding_digest`, `publication_digest`, `state`, `opened_at`, and `updated_at`; a syntactically valid JSON object missing one of those fields raises `KeyError`. Invalid container values such as `referenced_paths: null` can raise `TypeError`. These exceptions currently escape the strict authority instead of becoming its explicit unresolved result.

This matters beyond error presentation. `build_qualification_retention_fence()` consumes `iter_attempt_state_census()` directly while the storage command context is being constructed. An escaping record-shape exception can therefore make ordinary observational `storage report` unavailable before the owner graph has a chance to report the damaged attempt. Revision 20/21 require the opposite: malformed/unusable attempt state is unknown cross-owner liveness, consequential planning is unavailable, the workspace-wide retention reduction is active, and normal reporting remains available so the operator can identify the exact broken state.

### Required repair

1. Make `authenticate_attempt_state()` **total over expected persisted-record corruption**. Convert structural/deserialization failures that a malformed JSON object can legitimately trigger into one explicit unresolved `AttemptStateAuthority` naming the attempt root and reason.
2. At minimum handle `KeyError`, `TypeError`, `ValueError`, `TrainingDataInputError`, and `TrainingDataSerializationError` around state reconstruction. Retain the existing JSON decode handling. If another narrowly defined parser/validation exception is demonstrably reachable from current `QualificationAttemptState.from_dict()`, include it.
3. Do **not** hide arbitrary programming defects, resource failures, or unrelated system exceptions behind a blanket `except Exception`. The owner boundary should be total for malformed persisted state, not opaque to bugs.
4. The persisted `content_digest` requirement remains mandatory. Do not repair malformed state by synthesizing missing fields, dropping bad references, or accepting a recomputed in-memory truth.
5. The unresolved result must flow through the same Revision-22 descriptor/root-bound census, `qualification_views()`, `StorageInventorySnapshot.require_planable()`, and workspace-wide `QualificationRetentionFence` ambiguity. Do not add a parallel recovery parser.
6. `storage report` must remain observational and available for this condition, naming the affected attempt/root and a bounded reason. Cleanup, dedup, archive creation/reclaim, and any other consequential storage planning must remain unavailable until the exact state is repaired.
7. Repairing the exact persisted state must clear both the owner-integrity blocker and the blanket retention-fence ambiguity without migration-by-guessing.

### Required focused acceptance

Use a real P7 attempt and real storage command/boundary paths.

1. Start from an authenticated attempt state that pins an exact P5 publication checkpoint.
2. Replace it with a syntactically valid JSON object that still carries a `content_digest` field but is missing one required field such as `binding_digest` or `opened_at`. The strict authority must return unresolved rather than raising `KeyError` out of the owner boundary.
3. Separately use a parseable object with an invalid field container/type that exercises the current `TypeError` path (for example `referenced_paths: null`, if that remains the production deserializer behavior).
4. In both cases prove:
   - `storage report` completes successfully and identifies the unresolved P7 attempt/root;
   - the owner graph has an integrity failure and `require_planable()` refuses;
   - the P7 retention fence enters workspace-wide ambiguity;
   - direct real `CampaignOwnershipBoundary.destructive_authorization()` refuses the previously referenced P5 checkpoint and an unrelated campaign-managed path;
   - the P7 owner view exposes no released/reclaimable scratch authority from the rejected state.
5. Restore the exact authenticated state and prove reporting remains healthy, planability returns, and the blanket ambiguity disappears.
6. These tests supplement, not replace, Revision-22 family-root/ancestor-race, wrong-root, special-node, and concurrency counterfactuals.

---

## 2. IR23-2 — correct the duplicated `OwnerSynchronization.to_dict()` implementation while the affected synchronization file is already in scope

### Finding

Revision 22 says the prior diagnostic note is closed because `OwnerSynchronization.to_dict()` exposes `attempt_roots`. The candidate actually contains **two** `to_dict()` methods in the class. The first serializes `generations`, `run_roots`, and `attempt_roots`; the later pre-existing definition overrides it and serializes only `generations` and `run_roots`.

Runtime locking still uses `attempt_roots` correctly, so this is not independently a destructive-safety blocker. It is nevertheless concrete implementation drift and makes diagnostics/evidence misrepresent the synchronization contract at exactly the P7 seam under review.

### Required repair

1. Remove the duplicate obsolete serializer.
2. Keep exactly one `OwnerSynchronization.to_dict()` implementation containing `generations`, `run_roots`, and `attempt_roots`.
3. Do not change runtime lock ordering or synchronization derivation merely to fix serialization.
4. Add a focused test constructing a synchronization with a non-empty `attempt_roots` set and asserting the serialized contract contains the exact path(s).

### Test cleanup while touched

The new CampaignStore externalization test contains a trailing assertion rendered tautological by `or True`. The earlier whole-workspace signature comparison is already the strong acceptance proof, so this does not independently invalidate the candidate. Remove the dead assertion when the test file is touched and retain an exact before/after external-record or workspace signature assertion with no unconditional escape.

---

## 3. Revision-22 requirements remain fully binding

Do not compress or substitute away any Revision-22 obligation. In particular, the final implementation must still close:

1. qualification-family root absence-versus-ambiguity;
2. descriptor/identity-bound no-follow traversal at the actual directory-open/enumeration boundary, including ancestor-swap TOCTOU cases;
3. one strict storage-facing P7 namespace result used by attempt reporting/views rather than parallel followable `Path.is_dir()/iterdir()` traversal;
4. proof/root binding through released-attempt certification after state authentication;
5. a genuinely self-digest-valid wrong-root/copy counterfactual;
6. a released-attempt scratch FIFO/special-node counterfactual independent of state-file special-node tests;
7. deterministic proof of both **actual** aborted-reopen/storage-cleanup lock acquisition orderings through the real production seam, with outcome assertions that would fail if active scratch were removed;
8. family-root substitution/unreadability and concurrent ancestor-swap tests;
9. exact candidate-bound Revision-21 E5/F regression/integration evidence.

Revision-22's preservation boundary remains unchanged.

---

## 4. Final acceptance and evidence

After IR22 + IR23 source/test repair, run the complete Revision-22 final evidence sequence on the **exact final executable candidate**. At minimum this includes:

- all IR22/IR23 focused counterfactuals;
- all still-binding Revision-20/21 CampaignStore/P7 proof/state/fence/concurrency cases;
- affected R17/R18 and R19-A through R19-D storage tests;
- full `tests/test_mlff_storage_reset_core.py`;
- full `tests/test_mlff_storage_reset_integration.py`;
- affected P1/P3/P4/P5/P7 currentness/publication/restart/retention/qualification-owner and P6 destructive-path regression;
- final affected-surface re-derivation from the completed diff followed by a fresh affected regression/integration pass;
- CPU-safe broader/full tests if impact cannot be bounded confidently;
- static checks and affected docs/spec/build validation.

Record actual commands, result summaries, exact executable commit, and executable tree. The current reviewed executable exposes only a successful `docs` check; that is not functional acceptance. Benchmarks do not substitute for regression/integration evidence.

Generated-document-only successors may reuse functional evidence only after compare proves they change no executable/configuration/persistence/test-harness contract.

Full external-DFT, long GPU production, and environment-specific HPC/storage qualification remain deferred and are not blockers.

---

## 5. Exit criteria

A next implementation review may return PASS only when Revision 22 is fully satisfied **and**:

1. structurally malformed but parseable current P7 state always becomes explicit unresolved authority rather than escaping `KeyError`/`TypeError` from the strict owner boundary;
2. observational `storage report` remains available and diagnostic under those malformed-state cases while all consequential planning/physical authorization remains fail-closed;
3. exact repair clears owner integrity and workspace-wide ambiguity without inferred/migrated state;
4. exactly one `OwnerSynchronization.to_dict()` remains and it serializes `attempt_roots`;
5. the dead `or True` test escape is removed if that test file is touched;
6. all Revision-22 proxy-proof and exact-candidate evidence requirements pass on the final executable commit/tree.

**Disposition:** executable `9da6525be75c328ffbbf6968cebe773e2dc8921e` / tree `7ff82374cbc966795e710f21ba3737d892af57f2` remains **NO-PASS / reopened**. Revision-21 design and Revision-22 rework design remain accepted; this amendment only makes the remaining implementation contract lossless.