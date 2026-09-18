---
kind: d3-d4-review-repair-binding
protocol_version: 6.4.0
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
branch: design/mlff-replay-retention-target-admissibility-rework
repair_date: 2026-09-18
review_r2_target: 5d7c62f803fc8757a4068b7b115fadb7a5ec4636
review_r2_record: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R2.md
repaired_candidate_target: de360579686bd6f06eae8a6a5e26b232d7db847e
repaired_candidate_tree: 51345a5d993235430d52d27ccfb9fdf44fedb0d3
status: PREPARED_FOR_FRESH_GATE_D_REVIEW
---

# MLFF replay-retention / target-admissibility D3/D4 R2 repair binding

This record binds the exact immutable repair candidate produced after independent D3 Review R2 returned NO-PASS with no Serious Challenge to D1/D2 or the repaired D3 architecture.

## R2-D4-1 closure

The repaired D4 handoff makes the D3 training-root / D2 measurement boundary executable without introducing another durable owner.

### Training materialization

Current `PostSelectionMaterialization` advances beyond historical v2 and is training-only. Its current schema/content identity excludes:

- `outer_evaluation_artifact`;
- `outer_evaluation.extxyz` and sidecar/manifest paths;
- held-out label/reference identity;
- EVAL2 provider/metric policy; and
- any equivalent held-out evaluation serialization.

The sealed post-cutover root therefore contains only training-bearing preparation/materialization/runtime/checkpoint state plus completion infrastructure.

### Training-bearing held-out projection

Before TRAIN2, the only held-out-derived coordinate retained is the label-blind required-composition / transfer-consumer projection needed by foundation residual-E0 composition-transfer validation. Held-out labels and evaluation transport remain excluded from training identity and fitted-preparation fitting inputs.

### EVAL2 transport

After D2.DEF.059A freezes the representative, EVAL2 realizes the exact held-out evaluation artifact as bounded attempt-local scratch outside the sealed run root. The scratch pathname has no currentness or reuse authority and may be removed after durable measurement publication.

The existing `PostSelectionEvidenceStore` remains the sole durable P5 evidence store. The immutable measurement record binds exact held-out membership/content, label/reference content, serialized artifact SHA/content identity, checkpoint/model state, metric/reduction, head/prediction semantics, provider realization and numerically material precision/backend semantics. No second evaluation-artifact store, registry, or pointer family is introduced.

### Measurement-role identity

`post_selection_eval_role_digest()` or its successor must also be narrowed: full `run_plan_digest` / assessment-policy ancestry is excluded unless a projected field independently changes the numerical experiment. A policy-only/full-plan-only change cannot move numerical measurement identity.

### Historical v2 roots

Historical materialization/root bytes remain immutable even when they contain embedded held-out evaluation transport. Such bytes may support current measurement reuse only under exact D2.DEF.060B equivalence. Otherwise current EVAL2 transport is regenerated outside the historical root without TRAIN2.

## Required falsification added

The candidate now requires evidence that:

- post-cutover materialization/root topology contains no held-out evaluation artifact;
- held-out label/reference/transport/provider/metric-only changes do not move training identity, preparation, materialization/root or TRAIN2;
- changed required-composition geometry still moves the training-bearing preparation projection;
- EVAL2 scratch is created only after representative freeze and outside the root;
- scratch deletion after durable metric publication does not invalidate measurement reuse or force TRAIN2;
- historical v2 held-out bytes are never rewritten/copied into the new topology; and
- no second persistent evidence/currentness owner is introduced.

## Immutable review target

Fresh independent Gate-D Review must review exact target:

`de360579686bd6f06eae8a6a5e26b232d7db847e`

Canonical repaired D4 P5 specification blob:
`515bb952b8c04780e431261b2a135c1b09013369`

Canonical repaired D3->D4 implementation-workplan blob:
`287037512559eb85a6d268436b0722cd241e4ac4`

The ratified D1/D2 parents and the D3 R1 repairs are unchanged. Treat this binding record, prior reviews, and authoring rationale as evidence to challenge, not authority. Gate E remains blocked until the fresh review returns PASS.
