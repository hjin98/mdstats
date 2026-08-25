---
kind: implementation-workplan-amendment
parent_workplan_id: CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK3
protocol_version: 5.6.0
status: active
reviewed_candidate: 5d8363517743c6072c6002342561c8629275b659
review_date: 2026-08-25
supersedes_local_realizations: true
---

# Flexible-Fidelity Rework 3 - Post-Implementation Review Amendment 1

## 1. Authority and scope

This is a **controlling amendment to** `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md`, not a new scientific redesign and not Rework 4. It records the independent Software Design review of implementation candidate `5d8363517743c6072c6002342561c8629275b659` and tightens the already-frozen Rework 3 implementation/acceptance contract where the implementation exposed concrete ownership and proxy-proof failures.

The parent Rework 3 workplan remains authoritative except where this amendment is more specific. Where a local implementation choice or prior gate interpretation conflicts with this amendment, this amendment controls. All parent scientific decisions remain frozen, including configurable `0 < n1 < n2 < n3 <= n`, default `(1,3,10)/30`, same-trajectory full-`n` continuation, policy-independent DATA7/DATA8 candidate-prefix scientific identity, immediate-predecessor-only historical compatibility, no historical screen/TRAIN2 evidence relabeling, and deferred full GPU/production qualification.

The reviewed candidate is **not accepted**. The findings below are implementation nonconformances under the existing design; no current evidence fires a scientific redesign trigger.

## 2. Review findings that reopen implementation gates

### R1 - Production-materialization schema was incorrectly used as candidate-authority generation

Observed real failure:

```text
mdstats-mlff-campaign: DATA8 bundle multihead_replay-n1024-seed1 has unsupported predecessor authority generation 'mdstats.production-materialization-plan.v10'.
```

The candidate bridge identifies the fixed-fidelity predecessor by requiring `ProductionMaterializationPlan.plan_schema == mdstats.production-materialization-plan.v9`. This is invalid. Production-materialization serialization generation and target-size candidate-authority generation are independent semantic dimensions. A v10 materialization may legitimately carry a predecessor target-size authority, while a v9 materialization does not by itself prove predecessor target-size semantics.

**Required correction:** remove production-plan v9/v10 as the candidate-authority generation discriminator. Production-plan schema may still participate in normal materialization deserialization/integrity compatibility, but predecessor admission must be decided by the authenticated target-size authority lineage and semantic-equivalence proof.

**Forbidden shortcut:** broadening the check from `v9` to `{v9,v10}` while retaining plan schema as the predecessor-generation proof. That would fix the observed exception while preserving the ownership bug.

### R2 - The implemented legacy authority digest reconstruction is not the authentic predecessor digest

The candidate helper `fixed_predecessor_candidate_authority_digest(study)` constructs a **current flexible-fidelity v7 `TargetSizeStudyPolicy`** with epochs `(3,10,30)` and hashes its `policy_digest`. The authentic immediate predecessor instead persisted the fixed-generation **v6 policy payload and fixed-generation authority version**. The parent migration path already distinguishes and authenticates that historical v8-study/v6-policy representation.

Therefore an authentic predecessor digest must not be reconstructed by substituting `(3,10,30)` into the current policy class. That creates a self-consistent test oracle but not the historical digest that real DATA8 carries.

**Required correction:** derive or preserve the predecessor candidate-authority digest from the authenticated historical target-size authority itself. The owning path must validate the raw predecessor study/policy generation before migration/normalization destroys the historical identity information needed for the bridge. Acceptable realizations include an authenticated predecessor authority receipt/value captured during the supported v8/v6 migration/restart path or an equivalent exact reconstruction from the authenticated raw v6 payload. The exact representation is delegated; using current v7 policy serialization as the legacy digest oracle is forbidden.

The exact historical candidate-authority formula remains the predecessor formula:

```text
H(
  legacy candidate-authority schema,
  dataset identity,
  REPAIR2 authority,
  MVQUAL authority,
  authentic legacy v6 policy_digest,
  admitted candidate digests,
  qualified-size set
)
```

No current flexible-fidelity schema/authority token may be substituted into the legacy `policy_digest`.

### R3 - Candidate-authority populations must be classified explicitly

The reviewed implementation introduced a current candidate-authority v2 schema while the immediately preceding flexible-fidelity candidate before this commit already emitted policy-independent v1 authority. The persisted ecosystem can therefore contain at least:

1. authentic fixed-fidelity policy-bound candidate authority v1;
2. transitional flexible-fidelity policy-independent v1 emitted by the pre-review flexible branch;
3. current flexible-fidelity policy-independent v2 if the v2 design is retained.

These populations must not be inferred from a bare digest or from production-plan schema. The product must explicitly distinguish them at the owning authority/compatibility boundary.

**Frozen compatibility requirement:** the historical fixed-fidelity predecessor remains the only compatibility class guaranteed by the parent product contract. Transitional flexible-v1 artifacts may be accepted only if direct evidence establishes a bounded, unambiguous compatibility rule that preserves the same current scientific authority; otherwise they must fail closed with an actionable generation-specific error. They must never be misclassified as fixed-fidelity predecessors.

If retaining candidate-authority v2 creates avoidable transition complexity with no semantic benefit beyond explicit generation labeling, implementation should prefer the lowest-complexity engineering-sufficient representation. Any simplification must still leave fixed predecessor, transitional flexible generation, and current authority semantically distinguishable wherever persisted compatibility depends on that distinction.

### R4 - O24R-G2 positive acceptance remained a proxy

The new bridge test creates a single synthetic `SimpleNamespace` n512 entry, stamps it as production-plan v9, generates its alleged legacy digest through the same reconstruction helper under test, and calls the bridge helper directly. It does not execute the required real path through historical store/restart, real DATA8 discovery, complete expected matrix, target-study construction, `_validate_train2_data8_matrix`, preflight/next-operation authorization, and configured `n1` screening authorization.

This evidence cannot close O24R-G2 because it remained green while the real campaign failed.

**Required replacement acceptance path:**

```text
real CampaignStore containing authenticated immediate-predecessor state
 -> real historical prepare/preflight compatibility
 -> real current DATA8 discovery from persisted production materializations
 -> real authenticated predecessor target-size authority extraction/classification
 -> real current target-size study construction
 -> real predecessor/current candidate-authority compatibility owner
 -> real _validate_train2_data8_matrix (or successor)
 -> real preflight/next-operation authorization
 -> configured n1 target-size screening authorization
```

The bounded fixture must contain the **complete expected candidate matrix**, not one selected variant. At minimum it must contain both the previously observed n512 shape and the currently failing n1024 shape naturally as members of that real matrix; no variant-specific exceptions are permitted.

Physical MACE training/evaluation may be faked only after the real owner authorizes it. Reduced scientific payloads are allowed when they preserve the same serialization, persistence, topology, authority, and restart contracts.

### R5 - O24R-G3 negative matrix remains incomplete

The final acceptance must independently prove fail-closed behavior for at least:

- wrong/authentically changed REPAIR2 authority;
- wrong/authentically changed MVQUAL authority;
- candidate/prefix content mutation;
- qualified-size-set mutation;
- missing candidate variant;
- extra candidate variant;
- wrong target size / optimizer seed / training-mode topology;
- wrong selection authority role;
- unsupported fixed-generation study/policy schema;
- ambiguous or missing predecessor authority evidence;
- predecessor digest inconsistent with its authenticated raw v6 authority;
- transitional flexible-v1 data misclassified as fixed predecessor;
- current-generation authority mismatch;
- corrupted DATA8 bundle digest;
- corrupted DATA8 tree/integrity metadata;
- mixed matrix containing current and predecessor bindings when such mixing is not explicitly supported.

Every row must traverse the real compatibility/matrix-validation owner far enough that the semantic mismatch, not fixture construction, is what causes rejection.

### R6 - O24R-G4 persistence/idempotence must exercise a real reopen

Directly invoking the bridge twice against one in-process store is insufficient. Required acceptance must close and reopen the real `CampaignStore`, rediscover the persisted DATA8/materialization state, re-run the owning compatibility/validation path, and prove:

- no scientific DATA7/DATA8 files or tree digests change;
- any compatibility receipt is single-owner, durable, deterministic, integrity-bound, and reused idempotently;
- no duplicate receipt/state accumulates;
- current-generation strict mismatch remains rejected after reopen;
- a corrupted or conflicting stored compatibility receipt fails closed rather than being overwritten silently.

### R7 - O23R anti-bypass coverage is incomplete

The current AST guard protects only tests whose names begin with `test_real_owner_`. Renaming old proxy tests to `test_supplemental_*` correctly removes their acceptance authority but does not create the required genuine replacements. Material A/B/frontier/D acceptance paths are therefore outside the guard.

**Required correction:** define the acceptance set structurally rather than by a naming prefix that omits required claims. The guard must cover the actual tests designated to close O18R, all four O20R frontiers, A/B/C/D1/D2/D3, and O24R G2-G4. It must fail if those acceptance tests:

- replace `_require_train2_preflight_authorization`;
- replace `_historical_prepare_inputs_match_current`;
- replace `_prepare_contract_signature` or preparation identity owner where that owner is under acceptance;
- replace `_current_data8_entries`;
- replace `_target_size_materialization_variants`;
- replace `_ensure_target_size_study`;
- replace predecessor-authority extraction/classification/bridge ownership;
- replace `_validate_train2_data8_matrix` or schedule validator;
- replace `_stage_config_digest` where restart identity is the claim;
- replace `_next_public_operation`/normal restart-status owner;
- replace `CampaignStore` where persistence/restart is the claim;
- directly invoke `_invalidate_train2_downstream_state` as the O20 frontier acceptance mechanism.

Supplemental/helper/unit tests may continue to use mocks when they are not claimed as acceptance evidence.

### R8 - O20R frontiers are still not accepted

The candidate's real-store frontier test still constructs/replaces the study and then directly invokes `_invalidate_train2_downstream_state`. That violates the parent O20R boundary.

**Required correction:** each n1/n2/n3/n row must begin from one authenticated persisted baseline, edit actual TOML, close/reopen, and invoke the **normal restart/reconciliation/next-operation consumer** that detects the configuration change and reaches invalidation itself. Assert exact preserved/invalidated durable records, forensic retention, fresh study tuple/horizon, next authorized screen epoch, and full schedule horizon. Direct invalidation-helper tests remain useful unit coverage only.

### R9 - O21R A/B/C/D integration remains open

The reviewed candidate still has the following acceptance gaps:

- A/B patch `_require_train2_preflight_authorization`; they are not accepted until real preflight authorization executes.
- C still proves `build_size_fidelity_execution_plan(...)` directly; it must flow from persisted selected target-size authority into the real SIZE-FIDELITY execution/checkpoint consumer.
- D1/D2 still rely on custom migration stores and patched historical/DATA8/study/matrix/stage owners; they must be replaced by genuine real-store persisted predecessor cases consuming the corrected O24 bridge.
- D3 still relies on a reduced custom store and patched preparation identity owners; it must use real preparation digest/signature/receipt/restart ownership.

Renamed `supplemental` tests may remain as focused/unit regression but have zero gate-closing authority.

### R10 - O18R remains partial

Digest/projection and prepare-marker tests do not satisfy the parent requirement for authenticated completed prepare + preflight + DATA7/DATA8 reuse through the normal durable reuse consumer for every listed downstream/execution/presentation change.

Required acceptance remains unchanged: one bounded real baseline with actual persisted prepare receipt, preflight state, and DATA7/DATA8 current products; independently mutate the required downstream fields through real config normalization; prove normal restart/reuse retains upstream science; prove one true preparation-scientific mutation reopens at the narrowest correct boundary.

### R11 - O19R and final O22R remain open

The reviewed implementation did not establish the full architecture/spec regression restoration required by O19R, and no final same-candidate affected-surface regression/integration evidence was recorded. The runtime failure itself independently blocks O22R.

Do not archive Rework 3 or claim completion until the corrected final candidate passes all reopened gates below.

## 3. Revised O24R implementation contract

The parent O24R remains authoritative with these additional frozen consequences:

1. **Authority owner separation:** `ProductionMaterializationPlan.plan_schema` is a serialization/materialization contract, not the target-size candidate-authority generation owner. Never use v9/v10 alone to classify predecessor/current candidate authority.
2. **Authentic predecessor source:** the compatibility bridge must consume authenticated historical target-size generation evidence carrying or exactly reproducing the predecessor v8-study/v6-policy identity. The raw historical policy digest must be validated before use.
3. **No current-policy legacy oracle:** constructing a current `TargetSizeStudyPolicy` with `(3,10,30)` is insufficient and forbidden as the predecessor authority oracle.
4. **Semantic equivalence proof:** admission still requires identical dataset, REPAIR2, MVQUAL, candidate-prefix content, qualified sizes, complete expected variant topology, selection role, and intact DATA8 artifact lineage/integrity.
5. **Complete matrix atomicity:** bridge acceptance is a matrix-level decision. Do not persist a successful compatibility receipt after validating only a prefix/subset of the expected matrix. Validate the whole expected matrix first, then publish the one idempotent receipt.
6. **No scientific rewrite:** successful compatibility must not rewrite DATA7/DATA8 scientific bytes or regenerate them merely to acquire a new authority token.
7. **Fresh downstream evidence:** historical target-size screen evidence and TRAIN2 schedule/checkpoint/evaluation state remain invalid for the new flexible study unless separately authenticated by an existing current contract; no bridge action may relabel them.
8. **Strict current behavior:** fresh current-generation mismatches remain hard errors. Compatibility logic must not become a general mismatch bypass.
9. **Transition classification:** any transitional flexible-v1 population must be explicitly classified; it cannot fall through the fixed-predecessor branch by accident.
10. **Actionable diagnostics:** errors must identify the actual failed semantic generation/compatibility invariant. Do not report production-plan schema as a target-size authority generation.

## 4. Revised gate sequence

### R3R-W2A.1 - Correct authority ownership and authentic legacy identity

- remove production-plan v9 as the fixed-predecessor generation discriminator;
- trace the exact authenticated raw fixed-generation v8-study/v6-policy state available during historical prepare/restart migration;
- establish one owner that exposes the exact predecessor candidate-authority identity needed by DATA8 re-authentication without retaining a second scientific authority;
- decide and document explicit treatment of transitional flexible-v1 authority if present;
- preserve current policy-independent candidate-prefix identity.

**Gate:** an authentic real predecessor's candidate-authority digest can be validated from historical authority evidence without consulting production-plan schema for generation identity and without constructing a current v7 policy as the legacy oracle. Unknown/ambiguous generations fail closed.

### R3R-W2A.2 - Real full-matrix bridge acceptance

Build the bounded persisted predecessor fixture through real production serialization/persistence. Exercise real DATA8 discovery, real current study construction, corrected authority classifier, full matrix validator, and next-operation/preflight authorization.

**Gate:** the real v10 predecessor matrix, including n1024 and the rest of the expected candidate variants, is re-authenticated without scientific DATA8 rewrite and proceeds to configured `n1`; no old screen/TRAIN2 evidence is made current.

### R3R-W2A.3 - Negative semantic compatibility matrix

Execute every R5 negative row through the real owner path.

**Gate:** all material upstream/content/topology/generation/integrity mismatches fail closed for the correct semantic reason; no wildcard or schema-based bypass remains.

### R3R-W2A.4 - Durable reopen/idempotence

Close/reopen after successful bridge publication and repeat real discovery/validation/restart. Exercise conflicting/corrupt receipt and current-generation strictness.

**Gate:** compatibility receipt is deterministic and single-instance; scientific DATA8 is byte-identical; restart does not redo migration work; corrupt/conflicting evidence fails closed.

### R3R-W2A.5 - Stage-local affected regression and anti-bypass

Run focused authority tests plus affected target-size migration, production materialization, DATA8 integrity, historical prepare/preflight reuse, campaign restart/status/advance, TRAIN2 schedule/matrix, and O23 guard tests.

**Gate:** W2A.1-W2A.4 are green on the same commit and O23 covers the actual gate-closing tests, not only a naming subset.

### R3R-W2B - Genuine O20/O21 acceptance

Only after W2A passes, replace the remaining proxy frontier and A/B/C/D acceptance with real persisted owner paths exactly as required by the parent workplan and R8/R9 above.

**Gate:** all n1/n2/n3/n frontiers and A/B/C/D1/D2/D3 pass through their required semantic owners; supplemental mocked/helper tests are not counted as acceptance.

### R3R-W1, W3, W4, W5

These remain as in the parent plan, with current state updated below. W1 may be completed before or alongside W2A only if its own stage-local regression is independent of the failing bridge. W3 follows assembled behavior stabilization. W4 requires fresh final affected-surface derivation and same-candidate execution. W5 remains blocked until W4 passes.

## 5. Revised current gate state after review of `5d836351...`

- R3R-W0: **contract clarified; no scientific redesign required**.
- R3R-W1 / O18R: **partial, not accepted**; digest/marker coverage exists but genuine completed prepare+preflight+DATA7/DATA8 reuse acceptance is missing.
- R3R-W2A.1: **failed**; implementation conflates production-plan schema with candidate-authority generation and reconstructs legacy authority from current v7 policy semantics.
- R3R-W2A.2: **failed**; real v10 predecessor errors at n1024 and synthetic one-entry helper acceptance is insufficient.
- R3R-W2A.3: **not passed**; required semantic negative matrix incomplete.
- R3R-W2A.4: **not passed**; no genuine close/reopen full-owner idempotence acceptance.
- R3R-W2A.5: **not passed**; anti-bypass does not cover the full acceptance set and stage-local affected regression is not established.
- R3R-W2B / O20R + O21R: **blocked and independently nonconformant**; frontiers still call invalidation helper directly; A/B/C/D genuine owner-boundary acceptance remains missing.
- R3R-W3 / O19R: **partial, not accepted**.
- R3R-W4 / O22R: **not passed**; runtime failure and missing same-candidate final evidence block closure.
- R3R-W5: **blocked**.

## 6. Required regression/acceptance surface for the correction

At minimum re-run on the final corrected candidate:

- `tests/test_mlff_flexible_fidelity.py` plus any dedicated genuine real-owner acceptance module;
- target-size study serialization and immediate-predecessor v8/v6 migration tests;
- candidate-authority digest/generation/version tests, including authentic legacy digest oracle and transition classification;
- production materialization v9/v10 read compatibility and target-size-controlled materialization tests;
- DATA7/DATA8 persistence, tree integrity, discovery, matrix topology, and materialization reuse tests;
- prepare receipt / historical prepare / preflight smoke and re-authentication tests;
- campaign config/status/restart/advance/next-operation tests;
- TRAIN2 schedule, continuation, cross-horizon rejection, and matrix-validation tests;
- SIZE-FIDELITY coincident final/reference consumer tests;
- PERF-P2R production authorization tests;
- architecture/dependency/specification tests required by O19R;
- structural O23 anti-bypass guard;
- genuine A/B/C/D1/D2/D3 and four O20 frontier integrations.

Re-derive the final affected surface from the actual correction diff before W4. Any changed caller/consumer not listed above becomes affected and must be included. Full production/GPU qualification remains deferred.

## 7. Frozen correction principle

> **Do not repair the observed v10 exception by accepting another production-plan schema. Candidate-authority generation must be authenticated from the target-size authority that actually created the binding. The immediate fixed predecessor must use its authentic v8-study/v6-policy identity, not a current flexible policy object wearing `(3,10,30)`. Reuse immutable DATA7/DATA8 only after full-matrix semantic re-authentication through real persistence/restart owners; otherwise fail closed. Supplemental helper tests may remain, but they cannot satisfy Rework 3 gates.**
