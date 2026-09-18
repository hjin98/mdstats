---
kind: independent-d3-review
protocol_version: 6.4.0
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
branch: design/mlff-replay-retention-target-admissibility-rework
review_date: 2026-09-18
review_target: de360579686bd6f06eae8a6a5e26b232d7db847e
review_target_tree: 51345a5d993235430d52d27ccfb9fdf44fedb0d3
parent_d1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
parent_d1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
parent_d2_target: 32508991d472c1c6e4bd8b818b38d0880401845f
parent_d2_blob: 30e6e6336cf41a05879650a3a2d7d583c4ef713a
prior_review_r1_target: 119c4067b1852be127134d6b0fb1aae6cace4bd6
prior_review_r2_target: 5d7c62f803fc8757a4068b7b115fadb7a5ec4636
disposition: PASS
serious_challenge: NONE
gate: D
---

# MLFF replay-retention / target-admissibility independent Gate-D Review R3

## 1. Disposition

**PASS.**

**No SERIOUS CHALLENGE** to ratified D1/D2, the repaired D3 architecture, or the D4 handoff/workplan on immutable target `de360579686bd6f06eae8a6a5e26b232d7db847e`.

The prior R1 and R2 review records, repair bindings and authoring rationale were treated as evidence to challenge, not authority. This review independently reconstructed the governing semantics and executable-owner constraints before evaluating closure.

Gate D may close. Gate E implementation may proceed against this exact reviewed target. A later semantic mutation to the reviewed D3/D4 contract reopens the affected review scope.

## 2. Parent reconstruction

Ratified D2 requires, among the material constraints:

- fixed-budget TRAIN2 is independent of warning/hard checkpoint thresholds, outer-CV verdict thresholds and D2.DEF.059A/059B selection policy;
- exact continuation/reuse authenticates every training-bearing coordinate and exact realized fitted/prepared state;
- D2.DEF.060B numerical measurement identity binds exact checkpoint/model state, exact evaluation population/artifact and labels/reference values, metric/reduction, prediction/provider realization and numerically material precision while excluding assessment/publication policy and full role-plan identity;
- D2.DEF.059A freezes a representative from the complete governed hard-admissible checkpoint universe by strict target order before any held-out outer evaluation;
- D2.DEF.059B applies only afterward to aggregate single-best-seed publication;
- policy reassessment never rewrites historical verdicts and recomputes EVAL2 rather than TRAIN2 when exact measurement equivalence cannot be proved.

The repaired D3 correspondingly owns one acyclic pre-fit `TrainingTrajectoryIdentity`, one training-only root sealed at authenticated terminal TRAIN2, assessment-independent measurement evidence, external policy assessments/currentness, one existing CampaignStore locator plane, and the accepted P5 topology/storage exclusion machinery.

## 3. R1 closure re-verified

The four R1 blockers remain closed:

1. `TrainingTrajectoryIdentity` is pre-fit and contains no fitted-preparation/result descendant; fitted preparation/materialization/runtime authenticate realized state downstream.
2. sealed historical roots are read-only; only terminal-but-unsealed legacy roots have the explicit authenticated append-only completion-proof exception.
3. final-seed assessment currentness binds final hard policy + D2.DEF.059A only; current-CV authorization and D2.DEF.059B/publication mode remain separate downstream parents.
4. completion/topology keeps opened-descriptor `O_NOFOLLOW`/`fstat`, non-reclaimable manifest/anchor infrastructure, assessment-file-independent completion, idempotent proof reuse and fail-closed tamper/root-mismatch behavior.

No dependency cycle or persistence contradiction reappears in R3.

## 4. R2-D4-1 closure

**Closed.**

The repaired D4 specification advances current `PostSelectionMaterialization` beyond historical v2 and explicitly excludes `outer_evaluation_artifact`, held-out EXTXYZ paths/sidecars, held-out labels and equivalent EVAL2 transport from training materialization identity and post-cutover run-root topology.

The replacement is architecturally minimal:

- exact held-out membership remains owned by the CV fold/assessment position;
- before TRAIN2, only the label-blind required-composition / transfer-consumer projection needed by composition-transfer feasibility may descend into training preparation;
- after D2.DEF.059A freezes the representative, EVAL2 materializes held-out EXTXYZ only as bounded attempt-local scratch outside the sealed run root;
- exact held-out experiment identity is persisted in the immutable measurement record through the existing `PostSelectionEvidenceStore`;
- scratch path/file existence carries no currentness authority and may be reclaimed after durable measurement publication;
- no second evidence database, artifact registry, pointer family or shadow materialization namespace is introduced;
- historical v2 roots containing outer-evaluation files remain byte-for-byte historical and are reusable only under exact D2.DEF.060B measurement equivalence.

### Executable feasibility check

The current executable owners confirm this split is concretizable without changing the training method:

- the MACE target `valid_file` is the campaign-common checkpoint-monitor artifact, not the held-out outer fold;
- `outer_evaluation_artifact` is currently serialized during materialization but is consumed later only after the representative is frozen for outer CV evaluation;
- the existing composition-transfer helper obtains common-monitor/held-out composition classes from geometry-only atomic numbers and explicitly does not read labels.

Therefore removing the held-out serialization from TRAIN2 materialization does not remove trainer-consumed validation state or alter optimizer updates.

## 5. Measurement identity and persistence challenge

The candidate also closes the related identity back-edge rather than moving the defect:

- `post_selection_eval_role_digest()` or its successor is explicitly forbidden from retaining full `run_plan_digest` / assessment-policy ancestry unless a projected coordinate independently changes the numerical experiment;
- the durable measurement identity binds exact held-out membership/content, label/reference identity, transport-policy/serialized artifact identity, checkpoint/model state, metric/reduction, head/prediction semantics, provider realization and material precision;
- the scratch locator is excluded from identity;
- deleting attempt scratch after durable publication must not invalidate measurement reuse or force TRAIN2.

The existing post-selection evidence store already provides immutable content-addressed JSON evidence and the CampaignStore pointer seam. The repair therefore transfers the required capability without inventing a new retention/currentness owner.

The position pointer remains a locator, not independent semantic authority. Implementation must preserve the D3 rule that a pointer-resolved assessment is current only after its bound measurement and other current parents authenticate; pointer existence alone cannot make stale numerical evidence current. This is an existing D3 currentness consequence, not a new architecture mutation.

## 6. Adjacent-owner and collateral challenge pass

Reviewed adjacent authority/executable surfaces include:

- current CV fold construction and exact held-out membership ownership;
- current MACE post-selection configuration/validation input;
- current P5 materialization recovery/topology ownership;
- current CV representative -> outer-evaluation execution order;
- the existing content-addressed P5 evidence store and publication barrier;
- the cross-cutting training-data stage specification and restored-P5 owner index.

No competing current P5 representative order, outer-evaluation owner, second evidence store or conflicting root topology was found.

P1/P2/P3, P5 scratch, broad DATA8 non-P5 consumers and final-publication semantics remain outside the changed behavior except where the reviewed handoff explicitly binds their protected interfaces.

## 7. Historical applicability / PEM

The implementation workplan's HAS remains applicable. Repository `main` is still exactly `a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`, matching the plan's accepted project-state basis. No later accepted PEM publication needs reconciliation before implementation handoff.

The invoked PEM lessons remain evidence only: fail-closed exact boundaries, immutable expensive-work reuse, one destructive-storage owner, and real-owner integration. None were treated as authority.

## 8. Evidence applicability

This is an authority/workplan review before D4 implementation. Runtime tests cannot prove code that has not yet been changed and are therefore not required for Gate-D closure.

The review used:

- immutable D1/D2/D3/D4 candidate sources at `de360579686bd6f06eae8a6a5e26b232d7db847e`;
- actual current executable materialization, composition-transfer, MACE configuration, CV outer-evaluation and evidence-store owners as feasibility/counterexample evidence;
- current accepted PEM/main basis for HAS applicability;
- prior review records only as non-authoritative falsification hints.

Implementation acceptance still requires the candidate's real-owner falsification matrix, affected regression, recovery/reassessment fixtures, completion/storage concurrency checks and bounded scientific qualification.

## 9. Handoff

**Gate D: CLOSED / PASS.**

**Gate E: implementation authorized.**

The implementer SHALL use immutable reviewed authority target `de360579686bd6f06eae8a6a5e26b232d7db847e` together with the active D3->D4 implementation workplan. Do not substitute the review-binding descendant as a new semantic target.

Reopen Gate D if implementation requires a second persistent owner, cannot keep held-out EVAL2 transport outside the training root, cannot preserve exact measurement currentness without full-plan overbinding, weakens the topology/storage safety contract, or otherwise requires a material D3/D4 contract change.
