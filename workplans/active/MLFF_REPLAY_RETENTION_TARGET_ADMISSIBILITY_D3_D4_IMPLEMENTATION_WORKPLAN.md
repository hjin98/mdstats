---
kind: d3-to-d4-implementation-workplan
protocol_version: 6.4.0
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-D3-D4-1
parent_workplan: workplans/active/MLFF_REPLAY_RETENTION_AND_TARGET_ADMISSIBILITY_REWORK_WORKPLAN.md
branch: design/mlff-replay-retention-target-admissibility-rework
status: R1_REPAIRED_CANDIDATE_PENDING_INDEPENDENT_D3_REVIEW
parent_d1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
parent_d1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
parent_d2_target: 32508991d472c1c6e4bd8b818b38d0880401845f
parent_d2_blob: 30e6e6336cf41a05879650a3a2d7d583c4ef713a
---

# MLFF replay retention / target admissibility D3 -> D4 implementation workplan

## 0. Independent D3 Review R1 disposition

Immutable candidate `119c4067b1852be127134d6b0fb1aae6cace4bd6` is **NO-PASS**. Review record: `workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R1.md`.

Do not hand this plan to the implementer yet. The D3/D4 authority must first be repaired so that:

- `TrainingTrajectoryIdentity` contains no descendant fitted-preparation/result and therefore has no cycle;
- already sealed legacy roots remain read-only, while any one-time seal of an unsealed terminal legacy root has one explicit append-only authority and cannot rewrite historical bytes;
- per-seed final assessment currentness excludes D2.DEF.059B/publication mode, which belongs only to aggregate publication;
- the prior P5 completion/topology security and cold-storage invariants are preserved losslessly.

The R1 repairs are now frozen in the candidate authority: pre-fit acyclic trajectory identity, one append-only terminal-unsealed legacy sealing path, final-seed hard+059A assessment projection with 059B aggregate-only, and full retained completion/storage safety. Fresh independent D3 Review is still required before Gate E can open.

## 1. Governing outcome and implementation gate

Implement the ratified D1/D2 replay-retention, foundation target-admissibility, strict P5 representative-selection, reassessment, and training/measurement-equivalence semantics through the canonical MLFF P5 owners.

This plan is implementation-ready but **not implementation-authorizing yet**. A fresh independent D3 Review must PASS the immutable architecture candidate before code edits begin. The implementer must treat that reviewed D3 as the architectural parent; this workplan coordinates the concretization and does not replace D1-D4 authority.

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

### I4 - Assessment-independent measurement identity

Advance target/replay metric role/prediction schemas as needed so future records directly bind checkpoint/model state, exact evaluation artifact/membership, metric/reduction/units, head/prediction/provider semantics, and numerically material precision. Exclude thresholds/full assessment-plan digest.

Acceptance:
- policy-only edit preserves measurement identity;
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

## 5. Evidence and dependency plan

Run focused checks after each coherent executable stage, then final affected regression after assembly. Required evidence classes:

- structural source checks proving assessment-only fields are absent from training identity and no second store/registry/selector exists;
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
- fitted preparation/materialization;
- TRAIN2 runtime/completion/topology and checkpoint catalog;
- EVAL2 target/replay metric identity and evaluation;
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
- no rewriting historical checkpoints/runtime summaries/policy records;
- no production-scale GPU qualification before the final complete release package.

## 8. Reopen / Challenge triggers

Reopen D3 if implementation requires a second persistent owner, cannot make terminal TRAIN2 sufficient for the existing completion/topology owner, cannot externalize current assessments through the existing pointer plane, or cannot prove historical reuse without weakening authentic restart/currentness.

Reopen D2 if exact threshold/order/measurement/training equivalence cannot be implemented under the ratified definitions, complete-checkpoint assessment requires a new numerical approximation, or provider/precision changes need a new equivalence relation.

Reopen D1 if the resulting hard/warning/target criteria prove scientifically inadequate for the claimed deployment.

Raise SERIOUS CHALLENGE rather than patch around any contradiction among ratified D1/D2, accepted D3 after Review, and unavoidable implementation constraints.

## 9. Final handoff criteria

The implementer receives this plan only after independent D3 Review PASS identifies the exact reviewed architecture target. Implementation closeout then requires every I1-I11 obligation resolved, final affected-surface regression complete, real-owner integration complete, required evidence/dependency/documentation impact closed, and the assembled candidate ready for independent Protocol 6.4 Review.
