---
kind: independent-d3-review
protocol_version: 6.4.0
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
branch: design/mlff-replay-retention-target-admissibility-rework
review_date: 2026-09-18
review_target: 5d7c62f803fc8757a4068b7b115fadb7a5ec4636
review_target_tree: a22bc8fd7d270f49f2a6962b80ba4f159b0fac8d
parent_d1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
parent_d1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
parent_d2_target: 32508991d472c1c6e4bd8b818b38d0880401845f
parent_d2_blob: 30e6e6336cf41a05879650a3a2d7d583c4ef713a
prior_review_target: 119c4067b1852be127134d6b0fb1aae6cace4bd6
prior_review_record: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R1.md
disposition: NO_PASS
serious_challenge: NONE
earliest_blocker_owner: D4_HANDOFF
---

# MLFF replay-retention / target-admissibility D3 independent Review R2

## 1. Disposition

**NO-PASS.**

**No SERIOUS CHALLENGE** to the ratified D1/D2 authority or to the repaired D3 ownership/currentness architecture.

The four R1 blockers are closed on immutable target `5d7c62f803fc8757a4068b7b115fadb7a5ec4636`. One new blocking defect remains in the D3->D4 handoff: the candidate does not explicitly remove held-out outer-evaluation materialization from the training-only run root, even though the current executable D4 concretization stores and hashes it there.

This review treats the R1 review, repair binding, workplans and authoring rationale as evidence to challenge, not authority.

## 2. Parent semantics reconstructed independently

Ratified D2 requires:

- assessment-only policy cannot change an already-realized fixed-budget TRAIN2 trajectory;
- continuation authenticates exact training-bearing semantics including fitted/prepared state, while assessment-only coordinates are excluded;
- D2.DEF.060B makes exact evaluation population/artifact, labels/reference values, metric/reduction, head/prediction semantics, evaluator/provider realization and numerically material precision the identity of one numerical measurement;
- a full role-plan digest, assessment threshold and publication policy are explicitly not numerical-measurement inputs;
- D2.DEF.059A freezes each run representative before D2.DEF.059B performs aggregate cross-seed publication ordering;
- current CV authorization gates current final assessment/publication without becoming TRAIN2 semantics.

The accepted/repaired D3 candidate correspondingly requires a post-cutover run root keyed by `TrainingTrajectoryIdentity` and described as **training-only**, sealed at terminal TRAIN2 before EVAL2. Assessment-independent `EvaluationMeasurementIdentity` owns numerical target/replay/held-out measurement ancestry outside that training identity.

## 3. R1 blocker closure

### R1-D3-1 - closed

`TrainingTrajectoryIdentity` is now explicitly a pre-fit projection over already-available training-bearing inputs. `PostSelectionFittedPreparation` is a descendant and exact fitted-preparation/result/materialization/runtime ancestry is authenticated separately for continuation. No cycle remains.

### R1-D3-2 - closed

Already sealed historical roots are strictly read-only. A terminal-but-unsealed historical root has one explicit append-only topology/anchor publication path under the existing run-activity owner after terminal/root-node authentication; pre-existing historical bytes cannot be rewritten and conflicting partial proof fails closed.

### R1-D3-3 - closed

Final-seed assessment position binds final hard policy + D2.DEF.059A only. Current-CV authorization is separately re-authenticated and D2.DEF.059B/publication mode is aggregate-publication-only. A 059B-only edit therefore cannot move per-seed assessment identity.

### R1-D3-4 - closed

The repaired execution/storage authority restores the accepted completion-proof invariants: `O_NOFOLLOW` plus opened-descriptor `fstat`, non-reclaimable topology/anchor infrastructure, completion independent of hot terminal assessment files, idempotent proof reuse after cold movement, and fail-closed copied/tampered/self-inconsistent proof handling.

## 4. Blocking finding

### R2-D4-1 - held-out evaluation materialization still aliases the training root

**Earliest owner:** proposed D4 specification/workplan handoff. The repaired D3 invariant itself is coherent.

The repaired D3 states that post-cutover run roots are **training-only**, keyed by `TrainingTrajectoryIdentity`, and sealed before EVAL2. The D4 candidate states that `PostSelectionMaterialization`/TRAIN2 evidence binds the training trajectory and separately defines exact evaluation artifact/membership and labels/reference values as `EvaluationMeasurementIdentity` ancestry.

However, the current executable owner that this workplan hands to the implementer still does all of the following:

- `PostSelectionMaterialization` contains `outer_evaluation_artifact`;
- that field participates in `PostSelectionMaterialization.content_digest`;
- `materialize_post_selection_run()` writes the held-out artifact before TRAIN2;
- `outer_evaluation.extxyz` and its manifest are classified as run-owned materialization files under the run root;
- later EVAL2 reads `materialization.outer_evaluation_artifact` from that root.

The implementation workplan has no obligation or falsification case that removes or relocates this coupling.

This is not merely stale code awaiting obvious rewiring. The omission matters to the authority boundary. A held-out label/reference correction, evaluation-transport change, or other D2.DEF.060B-only measurement change can leave every training-bearing input and `TrainingTrajectoryIdentity` unchanged while changing `outer_evaluation_artifact`. If that artifact remains in immutable `PostSelectionMaterialization` under the root keyed only by training identity, the system must either:

1. reject reuse because materialization bytes/digest disagree;
2. mutate a sealed training root;
3. create a duplicate training root for an evaluation-only change; or
4. weaken materialization authentication.

Every option violates the repaired D2/D3 split.

The needed architecture is already implied by D3; the D4 handoff must make it explicit because the baseline concretization is the opposite.

**Required repair:**

1. remove `outer_evaluation_artifact` and `outer_evaluation.extxyz*` from post-cutover training `PostSelectionMaterialization`, its content identity and sealed run-root topology;
2. realize/authenticate held-out evaluation input through the existing external EVAL2/assessment evidence plane (or another already accepted P5 evidence owner), binding it to `EvaluationMeasurementIdentity` rather than creating another store/registry;
3. keep only the training-bearing held-out geometry projection actually consumed by preparation: the required composition/transfer-consumer identity. Held-out labels/reference values and evaluation transport remain measurement-only;
4. preserve legacy roots with historical outer-evaluation files byte-for-byte; reuse those held-out bytes only through exact D2.DEF.060B proof, otherwise regenerate EVAL2 input outside the root;
5. add real-owner falsification showing an outer-label/reference/artifact-only edit keeps `TrainingTrajectoryIdentity`, fitted preparation, training materialization/root and TRAIN2 current while invalidating only measurement/EVAL2/outer-verdict descendants.

## 5. Adjacent-owner challenge pass

I inspected the generic checkpoint/adaptive-stop and DATA8 specifications rather than assuming the renewed P5 spec was isolated. They remain subordinate for restored P5 through the specification index / narrow P5 owner boundary; their historical replay-weighted ranking and adaptive-stop machinery is not promoted into the renewed P5 method by this candidate. No second current P5 ordering owner was found on the reviewed authority surface.

The existing CampaignStore evidence/pointer plane, P5 run-activity lease and completion/topology owner are sufficient for the required repair. No new persistent subsystem is justified.

## 6. Evidence and applicability

Executed/reconstructed evidence:

- immutable candidate authority/specification at `5d7c62f803fc8757a4068b7b115fadb7a5ec4636`;
- ratified D1/D2 definitions and axioms governing replay policy, 059A/059B ordering, currentness, continuation and D2.DEF.060B measurement equivalence;
- current executable `PostSelectionMaterialization` and run-root materialization/recovery/EVAL2 consumers in:
  - `mdstats/training_data/post_selection_execution.py`;
  - `mdstats/training_data/campaign_post_selection_runtime.py`;
- adjacent current D4 specs for checkpoint control, adaptive stop, online monitors and broad DATA8 scope;
- R1 review/repair records only as non-authoritative falsification hints.

No runtime execution is required to establish R2-D4-1: the blocker is a directly observable ownership/identity contradiction between the proposed D4 handoff and the baseline executable object it instructs the implementer to evolve. Runtime evidence becomes necessary after the D4 contract is repaired and implemented.

## 7. Impact closure

The repaired D3 architecture itself is now coherent on the R1 surfaces, but Gate D cannot close because the D4 child contract/workplan is not lossless enough to prevent an implementation that violates the training-root / measurement-identity separation.

Gate E remains blocked. Repair only the narrow held-out-materialization boundary and its acceptance tests; do not reopen ratified D1/D2, do not undo the R1 D3 repairs, and do not add a second evidence store or compatibility registry.

A new immutable candidate requires fresh independent review.
