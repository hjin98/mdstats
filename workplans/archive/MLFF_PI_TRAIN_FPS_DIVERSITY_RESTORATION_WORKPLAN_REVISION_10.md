---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
plan_revision: 10
protocol_version: 6.3.0
status: active
created_date: 2026-09-15
branch: design/mlff-pi-train-fps-diversity-restoration
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
reviewed_assembled_candidate: c76a53476596137aa34ec47bb68b7d1ab4bfe706
prior_review_commit: bb5a3994cbdc92cfd8ea688e95f6a2c893b241ce
highest_affected_domain: D4
challenge_state: D4_NO_PASS_INTEGRATION_REPAIR_REQUIRED
upstream_authority_state: D1_D2_D3_ACCEPTED_UNCHANGED
---

# MLFF `pi_train` MVSEL2-chain restoration — Revision 10 integration and verification audit

## 0. Composition and verdict

Revision 10 composes immutable Revisions 5-9. Revision 9 remains authoritative for B1-B3 except where this audit tightens B3. This revision adds integration findings B4-B6 discovered by tracing actual D4 control/data/storage behavior against the accepted scoped D1/D2 papers, canonical D3, general method papers, prepared-generation/currentness contracts, downstream compatibility routing, and user/specification surfaces.

**Verdict remains NO-PASS.** The main restored topology is sound, but six blocking closure items are now open:

1. **B1 — REPAIR2 semantic drift** from Revision 9.
2. **B2 — representative current-scale complete-path performance evidence missing** from Revision 9.
3. **B3 — normative documentation/static-test drift**, now concretely including contradictory general D1/D2 target-order text.
4. **B4 — same-build concurrent prepares share mutable checkpoint state**, violating accepted pre-adoption attempt isolation.
5. **B5 — required universal structural families can be silently thinned/omitted**, violating frozen D2 applicability/failure semantics.
6. **B6 — corrupt immutable target-order artifacts can be deleted/replaced in place without protected-generation reachability**, contradicting immutable prepared-storage/currentness semantics.

These findings do not authorize a second selector, currentness store, scheduler, wrapper, compatibility router, migration layer, or changed scientific threshold. Repair by deleting unowned behavior and rewiring existing owners/primitives.

## 1. Integration surfaces that are conformant

The audit found the following integrations structurally correct and they should be preserved rather than rewritten:

- current v2 target-size construction requires an explicit target-order builder; no hidden current selector fallback remains in P2;
- the target-order prepared component is published before the aggregate and the full prepared-generation loader verifies the aggregate training-order evidence digest against that component;
- downstream full-generation loading does not reinterpret live source inputs or call the prepare builder;
- `campaign_post_selection._load_p5a6_selected_training_context` is reached only for explicitly detected pre-rework campaign schema and reconstructs the exact v1 aggregate under `TARGET_SIZE_POLICY_V1_SCHEMA`; it is historical ancestry support, not a current old/new selector router;
- MVSEL2 Phase A/B comparator order, exact masked coverage reductions, bottleneck definition, certified lazy Phase B, repaired-prefix cold reconstruction, same-engine suffix continuation, and independent MVQUAL are otherwise aligned with scoped D2;
- manual/automatic selection and post-selection consumers derive exact prefixes from the compact authenticated P2 definition rather than reconstructing selector science;
- target-order build identity binds population/split/raw-feature/structural-input/policy/explicit-obligation/configured-size/method identity and excludes worker width as intended;
- prepared-generation storage exposes target-order heavy artifact paths to the existing protected-path/reachability owner rather than creating a selector-specific GC/currentness database.

These positive findings narrow the repair: the baseline architecture should remain intact.

## 2. B1 and B2 — unchanged Revision-9 blockers

B1 and B2 remain exactly as specified by Revision 9:

- delete the REPAIR2 `proposal_possible` shortcut and let the accepted frontier plus strict global objective decide admissibility;
- produce representative current-scale evidence for the complete real-owner prepare/order/publication/reload path using the existing measurement surfaces and accepted method.

Do not duplicate those instructions here.

## 3. B3 — reconcile all normative documentation and static validation

Revision 9 already requires the eight affected static/documentation failures to be enumerated and reconciled. This audit identifies a concrete source-of-truth contradiction that must be included in that closure.

### 3.1 Contradictory current general D1 text

`docs/methods/mlff_scientific_method.md` §6.2 still says target-size prefix qualification is limited to label usability and explicitly declared hard-support obligations and that coverage/novelty measures do not become qualification gates.

The accepted scoped D1 `docs/methods/mlff_target_training_order_scientific_method.md` instead makes required multi-view mass coverage, required extents, and every canonical hard obligation part of configured-prefix membership qualification.

The scoped paper declares explicit precedence, so runtime authority is not ambiguous; the repository documentation corpus nevertheless contains two simultaneously current documents making incompatible claims about the same surface.

### 3.2 Contradictory current general D2 text

`docs/methods/mlff_numerical_algorithmic_method.md` §6.1 still specifies condition-bucket round-robin as the canonical target-training order and §7 qualifies only prefix existence, labels, and condition hard-support counts.

The accepted scoped D2 supersedes that construction with `TargetCoverageReference -> FEAS1/NEIGHBOR1 -> MVIDX -> MVSEL2 -> REPAIR2 -> MVQUAL`, including coverage/extents/canonical obligations.

### 3.3 Required repair

Do not duplicate the scoped method formulas into multiple owners. Reconcile the general papers by replacing only the superseded target-order construction/qualification passages with explicit delegation to the scoped D1/D2 owners, retaining unaffected split, `pi_eval`, P3, reducer, CV/replay/production material.

Then:

1. enumerate all eight known static failures and map each to current authority;
2. update stale assertions/doc topology/schema/provenance expectations rather than xfail/skip/whitelist;
3. regenerate generated publications from corrected source documents;
4. run the affected documentation/static batch with no unresolved failures;
5. search current user/spec/architecture sources for the retired condition-round-robin/current-qualification wording and reconcile any surviving current claim.

Historical/retired records may retain old semantics when clearly marked historical; they are evidence, not current authority.

## 4. B4 — pre-adoption checkpoint concurrency violates attempt isolation

### 4.1 Accepted D3 contract

Canonical D3 permits concurrent attempts to target the same prospective build identity, but mutable scratch is attempt-owned and simultaneous attempts may not share mutable scratch or cross-adopt another attempt's unfinished state. Stale/corrupt/foreign-attempt continuation must be rejected/rebuilt, while a later retry after a crash may reuse authenticated restart state under the same prospective identity.

### 4.2 Actual D4 behavior

`prepare_target_training_order` creates a unique attempt scratch directory, but `_build` uses checkpoint roots

```text
<target-order>/checkpoints/<pure_selection_identity>
<target-order>/checkpoints/<suffix_selection_identity>
```

with no attempt ownership or execution fence.

Every active attempt may therefore:

- restore the other active attempt's just-published checkpoint;
- `prune_checkpoints(...)` and delete the other attempt's checkpoint;
- have `restore_latest_checkpoint(...)` delete a checkpoint it sees as corrupt/incomplete/incompatible;
- after publishing the completed build, recursively delete both shared checkpoint roots while another same-build attempt is still executing.

`state.py` authenticates scientific identity and checkpoint content, but that is not active-attempt ownership. The dedicated real-owner suite covers ordinary crash resume and corrupt/stale checkpoint rejection, but contains no concurrent-prepare isolation case.

### 4.3 Required repair

Use existing repository fencing rather than adding a new lock/currentness subsystem.

Preferred repair:

1. expose/reuse the existing advisory-lock primitive at an appropriate shared persistence layer rather than importing a downstream P3 owner into target-order science;
2. acquire one execution-only single-flight fence keyed by the target-order prospective `build_identity` before accessing same-build mutable/reusable continuation roots;
3. after acquiring the fence, re-check `builds/<build_identity>` and reuse it if another attempt completed while waiting;
4. only the fenced active builder may restore/write/prune/remove the pure/suffix checkpoint roots for that build identity;
5. retain attempt-private scratch as-is;
6. on process death the OS advisory lock releases, allowing a later invocation to authenticate and reuse crash checkpoints;
7. different build identities remain independently buildable in parallel;
8. lock paths/ownership/timing remain execution-only and out of scientific identity.

If the existing `_FileLock` currently lives in `target_size_execution.persistence`, move/rehome that generic advisory-lock primitive to the lowest shared persistence module and rewire both consumers rather than creating a second implementation or introducing an upward dependency from target-order preparation into P3 execution.

### 4.4 Required falsification

Add real-owner concurrent same-build tests that prove:

- two simultaneously started prepares do not cross-adopt/prune/delete unfinished state;
- the waiter rechecks and reuses the completed build rather than rebuilding after the fence is released;
- a killed/crashed owner releases the fence and a later attempt reuses an authenticated checkpoint;
- different prospective build identities are not globally serialized;
- complete order/repair/MVQUAL/build identity is unchanged relative to serial execution.

## 5. B5 — frozen required structural-family catalog is not fail-closed

### 5.1 Accepted D2 contract

Scoped D2 fixes the universal structural family catalog to:

```text
pair_distance
radial_environment
coordination
connectivity
chemical_environment
local_density
angular_environment
orientational_order
```

and states that a required family requires at least two reference elements. `TargetCoveragePolicy` freezes the same required family tuple.

### 5.2 Actual D4 gap

`coverage_reference._structural_families` constructs only semantic families present in the supplied structural descriptor table. `_build_family` returns `None` when fewer than `minimum_family_elements` participate. The final reference builder checks only that *some* families exist; it does not prove that every applicable required universal structural family exists with sufficient support.

That converts a frozen method-infeasibility condition into silent omission. MVSEL2/MVQUAL can only enforce families that survived reference construction, so later stages cannot detect the missing scientific dimension.

The runtime also derives the structural provider policy from `PhaseGeometrySelectionPlan`. For `MOLECULAR_OR_GAS`, that plan omits `orientational_order`, and `universal_structural_policy_from_plan` passes the thinned set into `UniversalStructuralSelectionPolicy.enabled_feature_families`; the provider then filters columns by that set. The scoped D2 currently defines no molecular/gas exemption for the required universal structural family catalog.

### 5.3 Required repair

Treat this as D4 conformance unless upstream scientific owners explicitly decide that phase-dependent family applicability is intended.

Under the frozen current D2:

1. the target-order structural input path must not use a general phase/geometry policy to disable a D2-required universal target-order family;
2. preserve non-conflicting phase/geometry inputs such as local feature realization, groups, and recognized event applicability, but ensure the target-order provider exposes the full D2-required universal family set;
3. after building the structural reference families, explicitly validate the effective required/applicable family catalog;
4. absence or insufficient support for a required applicable family must raise typed method infeasibility/preparation failure, not return `None` and continue;
5. optional scalar target/profile channels may retain their D2-defined omission rules; do not generalize those rules to required universal families.

If `orientational_order` (or another frozen universal family) is scientifically intended to be inapplicable for a phase, route that contradiction to D1/D2 and define the applicability rule there before changing D4. Do not silently infer a new scientific exemption from the older phase/geometry provider policy.

### 5.4 Required falsification

Add tests proving:

- exact required universal semantic-family coverage for a normal current structural catalog;
- a provider missing one required family fails before FEAS/MVIDX/MVSEL;
- a required family with fewer than two valid reference elements fails rather than disappearing;
- a molecular/gas profile cannot silently thin the frozen target-order catalog;
- worker count/provider materialization choices do not change the retained scientific family catalog.

## 6. B6 — immutable target-order artifact publication can overwrite protected content

### 6.1 Contract conflict

`target_order.artifact_store.publish_artifact_directory` documents immutable create-or-verify publication, but when an existing destination fails authentication it recursively deletes that destination and retries publication in place.

Completed `TargetOrderPreparation` records name the published reference, geometry, MVIDX and build paths. `prepared_generation_protected_paths` explicitly adds those paths to the retention closure of every prepared generation that references them. These paths are therefore not disposable merely because the current builder can reconstruct them.

The campaign CLI specification likewise states that conflicting or corrupt immutable prepared content fails before adoption and is never overwritten because another adopted generation may still depend on the bytes at that identity.

### 6.2 Failure mode

A later prepare encountering corruption at a content-addressed target-order destination can currently remove/replace the path without asking the existing prepared-generation protected-reference owner. This has two problems:

- it mutates a path that may still be part of an adopted/historical-but-retained generation's immutable dependency closure;
- without fencing it can race a same-build or storage reader and turn authenticated identity/reachability into pathname-level mutation.

Reconstructibility is not permission to mutate an already published protected object in place.

### 6.3 Required repair

Converge target-order publication on the repository's existing immutable create-or-verify semantics:

1. publication of a destination that already exists must authenticate it under a destination-scoped fence;
2. exact matching content is reused;
3. conflicting/corrupt existing published content fails closed and is not deleted/replaced by the publishing path;
4. repair/reclamation of corrupt unreachable content belongs to the existing storage/retention owner, which can prove absence of protected references before deletion;
5. attempt-owned temporary directories remain freely discardable;
6. incomplete pre-adoption checkpoint state remains governed by B4 and may be reconstructed under its build fence; do not conflate that state with completed published reference/geometry/MVIDX/build products;
7. fsync/atomic-rename durability should reuse the existing shared persistence primitive rather than retaining two divergent implementations.

Prefer moving/reusing the existing generic locked create-or-verify primitive rather than layering a wrapper around `publish_artifact_directory`.

### 6.4 Required falsification

Prove:

- concurrent equal-content publishers converge without mutation of the accepted destination;
- conflicting/corrupt existing published target-order content fails closed;
- a protected current/historical target-order path is never recursively deleted by `prepare`;
- storage cleanup may remove a corrupt target-order object only after it is unreachable under existing retention rules;
- interruption before atomic publication cannot expose a partial destination.

## 7. Verification matrix for the next implementation round

The repair round must rerun/falsify at least:

- B1 focused REPAIR2 zero-new-coverage/later-objective cases;
- complete real-owner selector/oracle/native/reference equivalence and repair trace;
- required-family catalog/applicability/fail-closed tests from B5;
- same-build and distinct-build prepare concurrency from B4;
- immutable create-or-verify/protected-reference publication from B6;
- checkpoint stale/corrupt/crash-resume and suffix resume beyond `N_max` where applicable;
- OOC/FD/ENOSPC and packed-store behavior;
- fresh-process prepared reload and manual selection without selector reconstruction;
- automatic screen, freeze/CV, and production routing from the same authenticated compact P2 definition;
- legacy v1 post-selection ancestry remains reachable only behind explicit pre-rework schema detection;
- affected static/docs batch after general/scoped method reconciliation;
- representative current-scale complete prepare/order/publication/reload performance from B2.

Large downstream suites that install the test-only target-order substitute remain useful compatibility evidence, but they do not replace owner-level real-path falsification.

## 8. Re-review gate

A fresh independent D4 review may PASS only when all six blockers are closed and the assembled candidate demonstrates:

1. exact scoped D1/D2 behavior with no silent required-family omission and no REPAIR2 objective shortcut;
2. one current target-order owner and one completed-generation currentness owner;
3. no same-active-attempt checkpoint sharing or cross-attempt pruning/adoption;
4. immutable published target-order products cannot be overwritten outside the existing protected-storage owner;
5. complete-order/restart/resource/performance evidence at the accepted current envelope;
6. general/scoped methods, architecture manuals, CLI/spec/user docs, and static assertions are collectively self-consistent about the current target-order method;
7. no wrapper/fallback/router/parallel owner was introduced to repair any item above.

Until then the workplan remains **active / D4 repair required**.
