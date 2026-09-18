---
kind: d3-review-repair-binding
protocol_version: 6.4.0
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
branch: design/mlff-replay-retention-target-admissibility-rework
repair_date: 2026-09-18
review_r1_target: 119c4067b1852be127134d6b0fb1aae6cace4bd6
review_r1_record: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D3_INDEPENDENT_REVIEW_R1.md
repaired_candidate_target: 5d7c62f803fc8757a4068b7b115fadb7a5ec4636
repaired_candidate_tree: a22bc8fd7d270f49f2a6962b80ba4f159b0fac8d
status: PREPARED_FOR_INDEPENDENT_D3_REVIEW_R2
---

# MLFF replay-retention / target-admissibility D3 R1 repair binding

This record binds the exact immutable D3/D4 repair candidate prepared after independent D3 Review R1 returned NO-PASS.

## R1 blocker closure map

### R1-D3-1 - training-identity / fitted-preparation cycle

Closed by making `TrainingTrajectoryIdentity` a pre-fit position derived only from already-available training-bearing inputs and policies. `PostSelectionFittedPreparation` is a descendant and binds that position. Materialization/runtime/continuation separately authenticate the exact realized fitted-preparation/result ancestry required by D2.DEF.060. No reverse edge, placeholder, wrapper, or second identity graph was introduced.

Canonical repaired blobs:
- `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`: `38ba7f1b6a228a53d85fd23d1e53e964a1d4c559`
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`: `4fae60054d0440049c5c0bb8652f3f82555aee2b`
- `docs/specs/training_data/mlff_post_selection_p5_spec.md`: `614bb12a2464fbf3277beab9a4655c359e41a4d2`

### R1-D3-2 - contradictory legacy-root mutability

Closed with one explicit migration rule: already sealed historical roots are strictly read-only; a terminal-but-unsealed historical root may receive exactly one append-only topology manifest + compact completion anchor under the existing P5 run-activity owner after exact terminal/runtime/root-node authentication. No pre-existing historical byte may be rewritten; conflicting partial proof state fails closed.

### R1-D3-3 - per-seed final assessment over-bound to D2.DEF.059B

Closed by separating the full final control-plane plan from narrow currentness projections:
- final-seed assessment position binds final hard checkpoint policy + D2.DEF.059A only;
- current-CV authorization is re-authenticated separately as a precondition;
- publication mode and D2.DEF.059B bind only aggregate final publication over frozen seed representatives.

A 059B/publication-mode-only edit therefore does not move per-seed assessment identity.

### R1-D3-4 - weakened completion/storage safety

Closed by restoring equal-or-stronger accepted invariants:
- topology/anchor authority files use `O_NOFOLLOW` and opened-descriptor `fstat` regular-file verification;
- topology manifest and compact anchor are non-reclaimable owner infrastructure;
- completion does not depend on a hot terminal assessment file;
- an existing valid proof is verified/reused rather than reconstructed from a storage-depleted tree; and
- tampered, copied/root-mismatched, partial-conflict, or self-inconsistent proof state fails closed.

Canonical repaired execution/storage blob:
- `docs/arch_manuals/mlff_training_data/60_execution_performance.md`: `45f41cbb87e60bac8d8c6ca864808f75b4be9c9d`

## Lifecycle reconciliation

The candidate architecture/specification files explicitly identify themselves as proposed renewal candidates. The accepted-current pre-renewal D3/D4 baseline remains authoritative until independent R2 Review and the owning acceptance gate promote the repaired candidate.

Additional candidate blobs:
- D3 front matter: `2f5f5075ef1614925082b80fc95db1179abf6948`
- assembled D3 manual: `e762cf919df2dcd6a6d928b8d843fa78bab1ecd3`
- cross-cutting D4 P5 system contract: `965547377b5011f310a11217c8bf5aace8448e32`
- parent active workplan at candidate: `452fd6e6528f40d4f092c394a0cc736a04ae79b3`
- D3->D4 implementation workplan at candidate: `34b1c645627ad000838c61a1616f2b550c22bf59`

The generated `mlff_data_stage_plan_spec.pdf` was regenerated on descendant `33909621cc599ff515cb2510f215a166e35b41c3` from the same repaired Markdown semantics before the final lifecycle-only clarification; no semantic D3/D4 authority changed in that PDF-only commit.

## Review handoff

Fresh independent D3 Review R2 must review immutable target:

`5d7c62f803fc8757a4068b7b115fadb7a5ec4636`

Treat this binding record, R1 review record, workplans, and prior authoring rationale as evidence to challenge, not authority. Gate E remains blocked until R2 returns PASS.
