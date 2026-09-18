---
kind: d3-to-d4-implementation-workplan
protocol_version: 6.4.0
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-D3-D4-1
parent_workplan: workplans/active/MLFF_REPLAY_RETENTION_AND_TARGET_ADMISSIBILITY_REWORK_WORKPLAN.md
branch: design/mlff-replay-retention-target-admissibility-rework
status: D4_REVIEW_NO_PASS_REPAIR_ACTIVE
parent_d1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
parent_d1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
parent_d2_target: 32508991d472c1c6e4bd8b818b38d0880401845f
parent_d2_blob: 30e6e6336cf41a05879650a3a2d7d583c4ef713a
r1_review_target: 119c4067b1852be127134d6b0fb1aae6cace4bd6
r1_repaired_candidate_target: 5d7c62f803fc8757a4068b7b115fadb7a5ec4636
r1_repair_binding: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_R1_REPAIR_BINDING.md
r2_review_target: 5d7c62f803fc8757a4068b7b115fadb7a5ec4636
r2_review_record: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R2.md
r2_repaired_candidate_target: de360579686bd6f06eae8a6a5e26b232d7db847e
r2_repair_binding: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_R2_REPAIR_BINDING.md
gate_d_r3_review_target: de360579686bd6f06eae8a6a5e26b232d7db847e
gate_d_r3_review_record: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R3.md
gate_d_r3_disposition: PASS
implementation_base: afe6cb50dc6840799e86e1183c071761dab4e246e
semantic_authority_target: de360579686bd6f06eae8a6a5e26b232d7db847e
reviewed_implementation_target: b657460c088957bde28fb2a3800ba4e6699900a5
reviewed_branch_tip: dfe9a53cbf3fc45046b73270063841e83391cd61
reviewed_branch_tip_delta: generated documentation PDFs only
independent_d4_review_disposition: NO-PASS
independent_d4_review_date: 2026-09-18
independent_d4_review_highest_affected_domain: D4 implementation/evidence/lifecycle closure
independent_d4_review_serious_challenge: none
repair_base: dfe9a53cbf3fc45046b73270063841e83391cd61
repair_candidate_target: pending
initial_implementation_candidate_tracked_diff_sha256_excluding_this_workplan: 80f0d07231b4c30a0f34f9a47a14cdd1be317f9f2b3afd2c1e7889d208b5330c
initial_implementation_candidate_untracked_test_content_sha256: 9649c44b016e0cc7a4124a70f5ae5ffa51b32bb9084ab7e2cfba0a2d5095509f
---

# MLFF replay retention / target admissibility D3 -> D4 implementation workplan

## 0. Independent D3 Review R1/R2/R3 disposition

Immutable candidate `119c4067b1852be127134d6b0fb1aae6cace4bd6` is **NO-PASS**. Review record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R1.md`.

Do not hand this plan to the implementer yet. The D3/D4 authority must first be repaired so that:

- `TrainingTrajectoryIdentity` contains no descendant fitted-preparation/result and therefore has no cycle;
- already sealed legacy roots remain read-only, while any one-time seal of an unsealed terminal legacy root has one explicit append-only authority and cannot rewrite historical bytes;
- per-seed final assessment currentness excludes D2.DEF.059B/publication mode, which belongs only to aggregate publication;
- the prior P5 completion/topology security and cold-storage invariants are preserved losslessly.

The R1 repairs are frozen in candidate `5d7c62f803fc8757a4068b7b115fadb7a5ec4636`: pre-fit acyclic trajectory identity, one append-only terminal-unsealed legacy sealing path, final-seed hard+059A assessment projection with 059B aggregate-only, and full retained completion/storage safety.

Independent R2 Review confirmed those D3 repairs but returned **NO-PASS** on the assembled D3->D4 handoff because current `PostSelectionMaterialization` still owned held-out `outer_evaluation_artifact` inside the run root. Exact repair target `de360579686bd6f06eae8a6a5e26b232d7db847e` removes that coupling: current training materialization excludes held-out evaluation transport, EVAL2 realizes it only as attempt-local scratch outside the root, and the durable metric record in the existing P5 evidence store owns measurement identity.

Fresh independent Gate-D Review R3 of `de360579686bd6f06eae8a6a5e26b232d7db847e` returns **PASS with no SERIOUS CHALLENGE**. This workplan is now implementation-authorizing. The implementer must preserve the reviewed target semantics exactly; any material D3/D4 contract mutation reopens Gate D.

## 1. Governing outcome and implementation gate

Implement the ratified D1/D2 replay-retention, foundation target-admissibility, strict P5 representative-selection, reassessment, and training/measurement-equivalence semantics through the canonical MLFF P5 owners.

This plan is **implementation-authorizing** after Gate-D R3 PASS of exact immutable target `de360579686bd6f06eae8a6a5e26b232d7db847e`. The implementer must treat that reviewed D3/D4 candidate as the architectural/specification parent; this workplan coordinates concretization and does not replace D1-D4 authority.

The required end state is smaller than the current over-bound system:

```text
training-only method/trajectory identity
  -> one training-only run root sealed at terminal TRAIN2

assessment-independent measurement identity
  -> reusable immutable target/replay measurements

current hard/outer/selection policy
  -> external immutable reassessment records + existing pointers

warning policy
  -> diagnostics only
```

No parallel trainer/evaluator/policy/currentness/storage graph is authorized.

## 2. Parent invariants, cycle-frozen D3 decisions, and delegated D4 space

### Parent D1/D2 invariants

- replay degradation is signed candidate-minus-foundation TRUE_DFT force RMSE;
- default warning/hard limits are 50/100 meV/angstrom, both strict-exceedance; warning is diagnostic only;
- default foundation `tau_CV/theta_CV/tau_prod` are 75/75/50 meV/angstrom with direct inclusive target comparisons;
- every governed durable P5 checkpoint is assessed;
- within-run representative key is exactly `(target RMSE, epoch, checkpoint SHA-256)`;
- `single_best_final_seed` key is exactly `(target RMSE, optimizer seed, checkpoint SHA-256)`;
- fixed-budget TRAIN2 is independent of assessment-only thresholds/order;
- measurement reuse requires exact D2.DEF.060B equivalence;
- historical verdicts are never relabeled current in place;
- current CV acceptance is required before current assessment/publication of reusable historical final production.

### Cycle-frozen D3 decisions

1. `PostSelectionMethodIdentity` is training-only.
2. One `TrainingTrajectoryIdentity` is the singular root/restart owner derived from already-available training-bearing inputs. `PostSelectionFittedPreparation` is its descendant, not an input to it; continuation separately authenticates the exact fitted-preparation/result evidence required by D2.DEF.060.
3. CV fold assessment binds hard policy + D2.DEF.059A + outer metric/`theta_CV`; final-seed assessment binds final hard policy + D2.DEF.059A only. Current-CV authorization is a separate precondition and D2.DEF.059B/publication mode is aggregate-publication-only. Warning policy is diagnostic-only.
4. Numeric EVAL2 measurement identity excludes assessment thresholds/full role-plan ancestry.
5. Post-cutover P5 run roots are training-only and seal at authenticated terminal TRAIN2 before EVAL2 using the existing completion/topology owner while preserving all accepted topology/anchor race-safety, non-reclaimability, idempotent-republication, and tamper-fail-closed invariants.
6. Current CV/final assessments live outside sealed roots in the existing immutable evidence/currentness plane.
7. The existing CampaignStore pointer seam gains one position-addressed assessment locator keyed by a role-specific assessment-position-policy projection; the final-seed projection excludes current-CV authorization and D2.DEF.059B/publication mode. No second registry/store.
8. Root-consuming EVAL2/reassessment reuses the existing P5 run-activity exclusion; lock order with publication is run-activity first, publication barrier second.
9. Historical reuse is a narrow source-preserving equivalence derivation at the existing recovery/currentness owner; no root rename/copy/symlink/scan or general compatibility translator. Already sealed historical roots remain strictly read-only. A terminal-but-unsealed legacy root may receive exactly one append-only topology manifest + completion anchor under the existing P5 run-activity owner after exact terminal/root-node authentication, with no pre-existing byte rewrite; conflicting partial proof state fails closed.
10. Existing configuration owners remain singular; global campaign schema stays v2 and a narrow `post_selection_checkpoint_policy_generation` marker owns migration.

### Delegated D4 space

Exact helper names, dataclass decomposition, private function placement, serializer field ordering, local validation helpers, test fixture organization, and schema token spelling beyond required unambiguous generation separation remain delegated. Prefer removing/reusing old paths over wrappers. New durable machinery requires a governing capability that existing owners cannot supply.

## 3. Material implementation obligations

### I1 - Narrow P5 training identity

Remove assessment-only hard/warning thresholds and P5 representative-selection policy from `PostSelectionMethodIdentity`. Define `TrainingTrajectoryIdentity` only from pre-fit training-bearing inputs and policies that are already available when the trajectory position is created. Do **not** include `PostSelectionFittedPreparation`, its fitted E0 result, or another descendant digest in the identity. The fitted preparation binds the trajectory identity; materialization/runtime bind the fitted-preparation digest; restart/continuation authenticates both the root identity and the exact fitted-preparation/result evidence required by D2.

Acceptance:
- warning/hard/target/selection edits do not move training identity;
- each tested training-bearing edit does;
- no "ignore digest" continuation bypass remains.

Shortcut forbidden: retaining full plan/method digest and adding a compatibility exception around recovery.

### I2 - Move policy composition after TRAIN2

`_prepare_post_selection_run()` or its successor resolves replay execution from training method/replay lineage only. Build hard checkpoint admissibility only for EVAL2 assessment after authenticated fixed-budget training.

Acceptance: a policy-only change can reach existing terminal TRAIN2 without launching training and without requiring the old hard-policy digest.

### I3 - Seal training root before assessment

Evolve the existing completion/topology owner so terminal `Train2RuntimeSummary` + checkpoint/runtime boundary is sufficient to seal the root while the existing run-activity lease is held. Remove current assessment-file requirements from new root completion.

Stop writing current `fold-acceptance.json` / `run-evidence.json` into post-cutover roots. Keep every already sealed historical root strictly read-only. For a legacy root whose TRAIN2 is terminal but which lacks the old assessment-coupled completion proof, authenticate terminal summary/checkpoints/runtime boundary and every existing root node, hold the existing run-activity lease, then publish exactly one append-only topology manifest + completion anchor under existing create-once/verify semantics. No pre-existing byte may be rewritten; conflicting partial proof state fails closed.

Acceptance:
- root is closed/certifiable immediately after terminal TRAIN2;
- EVAL2/reassessment does not mutate root topology;
- topology/anchor authority files use `O_NOFOLLOW` + opened-descriptor `fstat` regular-file authentication;
- manifest/anchor are non-reclaimable owner infrastructure and completion does not depend on terminal assessment-file presence;
- existing proof is verified/reused after cold movement rather than reconstructed from a depleted tree;
- tampered/copied/root-mismatched/partial-conflict proof state fails closed;
- storage report/archive/dedup semantics remain owner-correct.

### I3A - Remove held-out evaluation bytes from the training root

Advance post-cutover `PostSelectionMaterialization` beyond historical schema v2 and remove `outer_evaluation_artifact` from the current schema/content digest. Remove `outer_evaluation.extxyz` and its sidecar from the current run-owned materialization file set and from every post-cutover completion topology.

Do not replace that field with another durable evaluation-artifact store. After the representative is frozen, the EVAL2 owner SHALL materialize exact held-out evaluation transport in bounded attempt-local scratch outside `runs/<training_trajectory_identity>`, evaluate it, bind its exact content identity into the immutable EVAL2 measurement record, publish that record in the existing `PostSelectionEvidenceStore`, and clean/reclaim the attempt scratch. Scratch path/existence is never currentness.

The training/preparation path retains only the label-blind held-out geometry projection actually consumed before TRAIN2: the canonical required-composition / transfer-consumer identity. It must be derived without serializing or reading held-out labels into training materialization.

Historical v2 materialization and roots remain readable, immutable history. Their embedded `outer_evaluation_artifact` may be used only after exact D2.DEF.060B equivalence; otherwise EVAL2 rematerializes current held-out input outside the historical root.

Acceptance:
- current `PostSelectionMaterialization.to_dict()` has no `outer_evaluation_artifact` or equivalent held-out transport field;
- current materialization/recovery allowlist and sealed topology contain no `outer_evaluation.extxyz*`;
- held-out transport is created only after representative freeze, outside the sealed root, through the existing EVAL2 owner;
- the durable measurement record binds exact held-out membership/content, label/reference content, transport artifact SHA/content digest, checkpoint/model state, metric/reduction, provider and precision semantics;
- deleting EVAL2 attempt scratch after metric publication neither invalidates the measurement record nor forces TRAIN2;
- changing only held-out labels/reference/transport/provider/metric changes measurement descendants, not training identity/preparation/materialization/root/TRAIN2;
- changing required-composition / transfer-consumer geometry changes the training-bearing projection as required;
- no second evidence store, filesystem registry, currentness pointer family, or shadow materialization namespace is introduced;
- historical root bytes are never rewritten or copied into the new training-root topology.

### I4 - Assessment-independent measurement identity

Advance target/replay/held-out metric role/prediction schemas so future records directly bind checkpoint/model state, exact evaluation artifact/membership, metric/reduction/units, head/prediction/provider semantics, and numerically material precision. Rework `post_selection_eval_role_digest()` or its successor so full `run_plan_digest` / assessment-policy ancestry is absent unless a projected field independently changes the numerical experiment. Exclude thresholds/full assessment-plan digest.

Acceptance:
- policy-only/full-plan-only edit preserves measurement and evaluation-role identity;
- materially changed evaluation input moves it;
- historical scalar-only equivalence is rejected.

### I5 - Split replay hard decision from warning diagnostics

Hard policy uses default 100 meV/angstrom catastrophic limit. Diagnostic warning uses default 50 meV/angstrom and has no hard-currentness edge. Preserve missing/nonfinite TRUE_DFT evidence as hard failure.

Acceptance includes exact threshold equality, `nextafter` above both thresholds, negative degradation, and independent warning-only invalidation.

### I6 - Resolve foundation role defaults and migration

Keep campaign schema v2. Implement marker `p5_target_replay_v2` and the exact migration table in the D4 spec: foundation CV 75/75, production 50, replay 50/100; scratch remains 30. Reject ambiguous mixed/new-marker/custom legacy replay states.

Acceptance includes generated template/init/example/CLI/guide parity and alternative-outer-metric isolation.

### I7 - Strict P5 checkpoint and seed selection

Remove uncertainty/practical-equivalence/secondary/maturity authority from P5 selection. Reuse old generic ordering only for separately current non-P5 consumers after a consumer census; otherwise simplify/retire it.

Acceptance:
- complete checkpoint universe assessed;
- exact within-run and cross-seed tie keys;
- quality-dependent thinning impossible;
- `all_qualified_final_seeds` unchanged.

### I8 - External policy assessment records and locators

Persist every candidate assessment first. Evolve final `PostSelectionRunEvidence` into a tagged selected/no-admissible assessment binding the complete ordered candidate set. Keep `CvFoldAcceptance` as CV assessment owner.

Extend the existing CampaignStore pointer seam with the canonical assessment-position key. CV folds use a projection containing hard policy + D2.DEF.059A + outer metric/`theta_CV`; final production seeds use final hard policy + D2.DEF.059A only. Exclude current-CV authorization, publication mode and D2.DEF.059B from the final-seed assessment identity. Current CV is re-authenticated before final assessment/publication can be used; aggregate publication binds publication mode/059B plus the exact frozen seed assessments/representatives.

Acceptance:
- idempotent same-position publication;
- hard or D2.DEF.059A edits derive a new affected assessment position over the same trajectory;
- warning-only, current-CV-authorization-only, and D2.DEF.059B/publication-mode-only edits do not move a final-seed assessment position;
- a 059B/publication-mode-only edit moves aggregate final publication and nothing upstream of it;
- no store scan/second pointer DB/second evidence store.

### I9 - Historical training and measurement reuse

For legacy completed/interrupted roots, derive source location only from authenticated historical plan/run evidence. Prove exact training equivalence. Continue interrupted work only under exact historical fitted-preparation/materialization/runtime/protocol/optimizer/EMA/RNG ancestry. Already sealed roots remain read-only. If an old root is terminal-but-unsealed, use only the one authenticated append-only topology/anchor route under the run-activity owner; do not rewrite any pre-existing historical byte.

Reassess every affected historical CV fold. Recompute EVAL2 only where measurement equivalence is unprovable. Historical final production is eligible only after current CV reclosure accepts.

Acceptance: zero TRAIN2 launches for policy-only-equivalent complete trajectories, and no pathname scanning/renaming/copy/symlink/hash rewriting.

### I10 - Root-read/storage exclusion

Every root-dependent EVAL2/reassessment holds `post_selection_run_activity_lease()` through all checkpoint/materialization numerical reads. If publication barrier is also needed, enforce lease -> publication-barrier order.

Acceptance uses bounded concurrency/failure injection proving archive/dedup/reclamation cannot move bytes under assessment and proving no deadlock-inducing reverse order.

### I11 - User-visible diagnostic separation

For replay-enabled checkpoints make target RMSE/ceiling/margin, candidate/foundation replay RMSE, signed degradation, warning threshold/margin, hard limit/margin, warning codes, hard failure reasons, checkpoint identity, and selected flag reconstructable. A selected representative warning is visibly a warning, not a failed run.

## 4. Historical applicability and capability transfer

```yaml
pem_basis:
  accepted_project_state: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
  accepted_pem: hjin98/mdstats@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: FF-002
    disposition: APPLICABLE
    reason: continuation remains fail-closed at an authenticated exact training boundary
  - id: FF-003
    disposition: APPLICABLE
    reason: sealed-root read/storage mutation must remain under existing real owners
  - id: SP-001
    disposition: APPLICABLE
    reason: reduce overbinding and reuse current owners instead of wrappers/shadow registries
  - id: SP-002
    disposition: APPLICABLE
    reason: authenticated identity/currentness disagreement must fail closed
  - id: SP-003
    disposition: APPLICABLE
    reason: immutable TRAIN2/measurement evidence should be reused when exact authority permits
  - id: SP-004
    disposition: APPLICABLE
    reason: closure requires real P5 owner paths and recovery/reassessment integration
```

Capability-transfer map:

| Historical capability/evidence | Current authority binding | New mechanism | Acceptance route |
|---|---|---|---|
| authenticated restart boundary (FF-002/SP-002) | D2.DEF.060 + D3 training trajectory | `TrainingTrajectoryIdentity` + historical exact-equivalence derivation | restart/corruption/policy-only counterfactuals |
| immutable expensive-work reuse (SP-003) | D2.DEF.060/060B/060C | sealed training root + clean measurement identity | old-workspace CV/final reassessment |
| one destructive storage owner (FF-003/SP-001) | current D3 storage ownership | existing run-activity exclusion + publication/storage barriers | concurrency + structural absence of second lock/store |
| real-owner qualification (SP-004) | D3/D4 acceptance contract | assembled cross-validate/train-production path | real-owner integration and bounded scientific qualification |

No historical mechanism is mandatory merely because PEM records it; the table binds only capabilities independently required by current D2/D3.

## 5A. Independent D4 implementation Review state (2026-09-18)

Independent Review examined executable candidate `b657460c088957bde28fb2a3800ba4e6699900a5`. Branch tip `dfe9a53cbf3fc45046b73270063841e83391cd61` is a generated-documentation descendant only and does not change executable behavior. The disposition is **NO-PASS / D4 REPAIR ACTIVE**, with **no SERIOUS CHALLENGE** to ratified D1, ratified D2, or Gate-D-PASS D3 target `de360579686bd6f06eae8a6a5e26b232d7db847e`.

The implementation is directionally conforming and the following accepted structure SHALL be preserved during repair: acyclic training-only `TrainingTrajectoryIdentity`; training-only post-cutover run roots; assessment-independent measurement identity; 50/100 meV/angstrom replay warning/hard split; 75/75/50 meV/angstrom foundation CV/outer/production target defaults; complete checkpoint assessment; D2.DEF.059A/059B strict target-RMSE ordering; external assessment-position currentness; authenticated historical TRAIN2 reuse; one CampaignStore pointer plane; one post-selection evidence store; and the retained completion/topology/storage safety contract.

| Obligation | Review state | Required disposition |
|---|---|---|
| I1 | provisionally conforming | Preserve; re-run identity counterfactuals after repair. |
| I2 | provisionally conforming | Preserve; no repair may move hard assessment before authenticated terminal TRAIN2. |
| I3 | provisionally conforming | Preserve training-only seal and legacy append-only exception. |
| I3A | **BLOCKED (R1)** | Fresh held-out scratch is reclaimed before its newly computed measurement is durable; repair exact publication/cleanup order below. |
| I4 | provisionally conforming | Preserve assessment-independent measurement ancestry and exact D2.DEF.060B inputs. |
| I5 | P5 semantics conforming; acceptance open | Preserve current P5 50/100 behavior; reconcile the shared exported TRAIN2 policy API without globalizing P5 defaults. |
| I6 | P5 config/migration path conforming; acceptance open | Preserve marker/migration semantics; close shared-policy regression break under R2. |
| I7 | provisionally conforming | Preserve complete candidate universe and exact 059A/059B keys. |
| I8 | provisionally conforming | Preserve external assessment records/currentness projections and one pointer plane. |
| I9 | provisionally conforming | Preserve authenticated historical reuse and no historical-byte rewrite. |
| I10 | provisionally conforming | Preserve run-activity exclusion and lease -> publication-barrier order where both are required. |
| I11 | provisionally conforming | Preserve diagnostic-only warning authority. |

Evidence recorded for the reviewed candidate remains evidence **for `b657460c...` only**:

- package/test `compileall`: pass;
- replay policy/identity/migration tests: 55 passed;
- replay/target real-owner tests: 8 passed;
- no-admissible/typed-outcome/recovery tests: 37 passed;
- complete P5 production/restart module: 27 passed;
- complete storage-core module: 291 passed;
- directly affected storage-integration subset: 15 passed.

The unfiltered 167-test storage-integration invocation was inconclusive and is not green evidence. None of these counts may be inherited as final evidence after executable repair without applicability review; every directly affected check and the final assembled regression below must execute against the final repair candidate.

## 5B. D4 Review reopen — exact repair instructions

### R1 — held-out EVAL2 transport lifetime ends before durable measurement publication

**Finding.** In `campaign_post_selection_runtime.py`, `_evaluate_held_out_representative()` owns the attempt-local `TemporaryDirectory`. A freshly computed held-out measurement is returned only after that context exits, so `outer_evaluation.extxyz*` has already been reclaimed. The corresponding `EvaluationMeasurementIdentity` and metric record are not written to `PostSelectionEvidenceStore` until the later caller invokes `publish_post_selection_run_measurements()`. This violates I3A / D4 spec section 15.1, whose required order is evaluate -> durably publish measurement -> reclaim scratch.

**Repair the existing EVAL2/evidence-store owner; do not add a registry, durable held-out artifact namespace, pointer family, or shadow store.**

Required behavior:

1. Keep representative freeze before any held-out transport creation.
2. Keep held-out transport outside every training root and keep its pathname absent from identity/currentness.
3. For a **newly computed** held-out measurement, keep the attempt scratch alive until both the immutable `EvaluationMeasurementIdentity` and its metric record have successfully committed through the existing `PostSelectionEvidenceStore`.
4. Only after that durable commit may the attempt scratch be reclaimed.
5. A reusable held-out metric whose exact measurement identity already resolves from durable evidence may be returned without a new durable write; its temporary regenerated transport may then be reclaimed because durability predates the attempt.
6. Preserve `post_selection_run_activity_lease()` through every checkpoint/materialization/model read from the training root. Do **not** move CampaignStore assessment/currentness pointer publication under that lease. If an immutable evidence-store write is performed while the lease is held, it must use the existing owner and must not introduce reverse lock order; if the implementation instead releases the lease before the immutable measurement write, the scratch lifetime must span that release without exposing a persistent owner.
7. On evidence-store publication failure, no assessment/current pointer may be published. Attempt scratch may be cleaned by exception unwinding; retry must regenerate it from authoritative upstream evidence.
8. Remove or reduce redundant later outer-measurement publication if practical. An idempotent verification write is acceptable only if it remains the same content-addressed owner; do not add a second “published” marker.

Required falsification:

- fresh held-out evaluation: instrument the existing evidence-store write and prove the scratch directory/artifact still exists when the outer `EvaluationMeasurementIdentity` and metric record are committed;
- after successful commit: prove the scratch is absent and the durable measurement remains reusable with zero TRAIN2 and zero numerical EVAL2 forward;
- inject failure on the outer measurement store write: prove no fold assessment/current pointer is published and retry recomputes/reuses correctly without retraining;
- prove the scratch never appears beneath `runs/<training_trajectory_identity>`;
- preserve the held-out-label-only invalidation test: only measurement/verdict descendants move; training identity/root/TRAIN2 do not.

### R2 — shared exported TRAIN2 policy API was changed beyond the authorized P5 surface

**Finding.** The reviewed implementation changes the shared exported `CheckpointAdmissibilityPolicy` constructor/property surface from `replay_degradation_budget_ev_per_angstrom` to `replay_degradation_hard_limit_ev_per_angstrom`, changes its no-argument replay default from 0.030 to 0.100, and removes the old exported default constant. Existing generic TRAIN2/EVAL2/target-size regressions still consume the prior public surface and fail before reaching their protected semantics. The renewed 100 meV/angstrom default is a **foundation-P5 resolved policy default**, not authority to silently change unrelated generic TRAIN2/P3/P5-scratch behavior.

**Repair in the existing `train2_policy.py` / export owners. Do not create a compatibility service, wrapper policy class, or parallel evaluator.**

Required behavior:

1. Current foundation-P5 effective policy remains schema v2 and receives the resolved replay hard limit **explicitly** from the P5 configuration/method-policy owner. Generated P5 default remains 0.100 eV/angstrom; warning remains separately 0.050.
2. Do not rely on the generic no-argument `CheckpointAdmissibilityPolicy()` constructor to inject the P5 default. Preserve the pre-existing generic/default 0.030 hard-constraint behavior for unaffected TRAIN2 consumers unless a separately accepted public-contract authority explicitly changes it.
3. Preserve source compatibility for the already exported legacy spelling `replay_degradation_budget_ev_per_angstrom` inside the same class/owner as a compatibility alias to the hard-limit value. It must not become a second stored authority. If both old and new constructor spellings are supplied with incompatible values, fail closed as ambiguous.
4. Preserve a read-only compatibility property for `replay_degradation_budget_ev_per_angstrom` and the exported `TRAIN2_DEFAULT_REPLAY_DEGRADATION_EV_PER_ANGSTROM = 0.030` alias so existing public consumers do not fail by attribute/import absence. Marking these as compatibility/deprecated is D4-local; do not let them re-enter current P5 identity.
5. Preserve exact historical schema-v1 deserialization/reserialization and its historical `replay_retention_ceiling_exceeded` reason. Tests that specifically assert the v1 reason must construct/read a v1 policy explicitly rather than accidentally using current P5 v2.
6. Current schema-v2 P5 hard failure remains `replay_catastrophic_forgetting_limit_exceeded`; exact 0.100 passes and `nextafter(0.100,+inf)` fails. No old alias may change this current P5 behavior.
7. `replay_enabled=False` must remain valid through both legacy-compatible and current call surfaces with no replay limit.
8. P5 scratch remains at its accepted 0.030 target semantics and no replay topology. P3/target-size and generic EVAL2 ordering semantics remain unchanged.
9. Update tests by semantic ownership, not by blind search/replace. A historical-v1 oracle stays historical; a current-P5 oracle moves to the v2 field/reason; an unaffected generic TRAIN2 oracle retains its prior behavior.

At minimum reconcile and execute:

- `tests/test_mlff_train2a_policy.py`;
- `tests/test_mlff_train2a_specification.py`;
- `tests/test_mlff_eval2.py`;
- `tests/test_mlff_audit_eval_perf1.py`;
- `tests/test_mlff_target_size_p5d_cv_acceptance.py`;
- `tests/test_mlff_target_size_p5_r6_guards.py`;
- `tests/test_mlff_target_size_p5_r7_guards.py`;
- all new replay/target policy and migration tests introduced by this rework.

Add explicit discrimination proving in one suite that generic/default compatibility remains 0.030 while the resolved current foundation-P5 effective hard limit is 0.100; this prevents the compatibility repair from accidentally reverting the ratified P5 method.

### R3 — immutable candidate binding, evidence closure, and lifecycle representation are stale

The reviewed executable candidate is now committed, but this workplan previously described a dirty worktree, and `workplans/active/README.md` still says runtime implementation has not begun. The reviewed candidate also lacks a complete final affected-regression result: `tests/test_mlff_storage_reset_integration.py` was only partially evidenced and its full 167-test invocation was inconclusive.

Required closeout sequence:

1. Implement R1/R2 without changing D1/D2/D3 semantics and commit the **last executable/test mutation** as one immutable repair candidate.
2. Run final affected regression against that exact executable SHA. Required minimum:
   - `python -m compileall` over package and affected tests;
   - all R2 modules listed above;
   - `tests/test_mlff_p5_replay_target_policy_identity.py`;
   - `tests/test_mlff_p5_replay_target_real_owner.py`;
   - `tests/test_mlff_p5_cv_no_admissible_outcome.py`;
   - `tests/test_mlff_target_size_p5e_production_and_restart.py`;
   - `tests/test_mlff_storage_reset_core.py`;
   - the **complete collected set** of `tests/test_mlff_storage_reset_integration.py`;
   - any additional repository-required package/lint/type tests that cover files changed by R1/R2.
3. The storage-integration suite may be split into bounded invocations only if the recorded node-id collection proves every collected test executed exactly once. A runner disappearance/no-result state is inconclusive and blocks closure; it cannot be called pass.
4. Record exact command, executable candidate SHA, collected/pass/fail/skip counts, and any environment limitation. Production-scale GPU qualification remains deferred under project policy; do not use that deferral to skip CPU/available-device semantic regression.
5. After executable evidence exists, create a **documentation/evidence-only descendant** that updates this front matter with the executable `repair_candidate_target`, replaces the provisional obligation states with evidence-backed states, and records the final commands/results. This avoids self-SHA recursion.
6. In that same lifecycle closeout, update `workplans/active/README.md` and the parent workplan’s lifecycle prose so they no longer claim implementation has not begun or is blocked before Gate D. Do not alter their scientific/numerical authority.
7. Perform the required PEM closeout learning assessment against the existing HAS. Add or modify PEM only if the admission threshold is met or an existing entry materially changes; ordinary repair chronology belongs here/Git, not as a manufactured new family.
8. Submit the executable repair SHA plus its evidence-only binding descendant for fresh independent D4 Review. Do not archive or mark this plan complete before that Review passes.

### Explicit non-repair

The D4 Review did **not** establish that mixed admissible/no-admissible final-production seeds require partial aggregate publication. Do not change final-production aggregate success/failure semantics in this repair. Any such change requires an explicit upstream authority decision; R1-R3 do not authorize it.

## 5. Evidence and dependency plan

Run focused checks after each coherent executable stage, then final affected regression after assembly. Required evidence classes:

- structural source checks proving assessment-only fields are absent from training identity, `PostSelectionMaterialization` contains no held-out evaluation transport, sealed roots contain no `outer_evaluation.extxyz*`, and no second store/registry/selector exists;
- exact D2 boundary/tie/currentness tests;
- current config and migration counterfactuals;
- completion/topology and storage concurrency/failure-injection tests;
- legacy completed/interrupted workspace reuse fixtures;
- full current CV and final-production no-admissible/success paths;
- real-owner `campaign cross-validate` and `campaign train-production` recovery/reassessment;
- documentation/generated-config parity;
- repository build/lint/type/package/test requirements.

Production-scale GPU qualification is deferred to the final complete release package. This cycle still requires CPU/available-device functional and bounded real scientific qualification sufficient to establish the changed policy/currentness behavior.

## 6. Affected surface

Re-derive from the final candidate. Expected affected owners include:

- P5 method/policy identity and config resolution;
- CV/final plan and run identity/currentness;
- fitted preparation/training-only materialization;
- TRAIN2 runtime/completion/topology and checkpoint catalog;
- EVAL2 target/replay/held-out transport, metric identity and evaluation;
- checkpoint assessment/selection and final publication;
- CampaignStore pointer/currentness;
- post-selection storage owner views, archive/dedup/reclamation exclusion;
- generated configuration, CLI/user documentation and diagnostics;
- historical workspace migration/recovery tests and semantic dependency/history records.

P1/P2/P3 and target-order semantics are protected collateral surfaces, not intended behavior-change targets.

## 7. Non-goals

- no LR/exposure retuning;
- no target-order or target-size algorithm change;
- no global campaign-schema bump;
- no distributed foundation-P5 enablement;
- no new assessment/evidence database, shadow policy registry, second selector, or compatibility service;
- no rewriting historical checkpoints/runtime summaries/policy records or legacy v2 held-out evaluation materialization;
- no production-scale GPU qualification before the final complete release package.

## 8. Reopen / Challenge triggers

Reopen D3 if implementation requires a second persistent owner, cannot make terminal TRAIN2 sufficient for the existing completion/topology owner, cannot externalize current assessments through the existing pointer plane, or cannot prove historical reuse without weakening authentic restart/currentness.

Reopen D2 if exact threshold/order/measurement/training equivalence cannot be implemented under the ratified definitions, complete-checkpoint assessment requires a new numerical approximation, or provider/precision changes need a new equivalence relation.

Reopen D1 if the resulting hard/warning/target criteria prove scientifically inadequate for the claimed deployment.

Raise SERIOUS CHALLENGE rather than patch around any contradiction among ratified D1/D2, accepted D3 after Review, and unavoidable implementation constraints.

## 9. Final handoff criteria

The implementer SHALL use exact reviewed authority target `de360579686bd6f06eae8a6a5e26b232d7db847e`, reviewed implementation target `b657460c088957bde28fb2a3800ba4e6699900a5`, and the R1-R3 repair contract in section 5B as the handoff basis. Closeout requires R1 and R2 repaired without upstream semantic drift, R3 immutable evidence/lifecycle binding complete, every I1-I11 obligation revalidated on the final executable candidate, the complete affected regression resolved rather than inconclusive, real-owner integration complete, and a fresh independent Protocol 6.4 D4 Review PASS.
