---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 1
status: READY_FOR_IMPLEMENTATION
protocol_version: 3.0.0
lineage:
  source_workplan_id: DOC-MVSEL2-HARDEN1
  source_plan_revision: 1
  source_protocol_version: 2.0.1
analysis_base_ref: feat/mvsel2-forward-lazy
analysis_base_commit: e24d5168ce01bf2d773339e1a91d5ded4871a57f
assumption_paths:
  - workplans/active/DOC-MVSEL2_HARDEN1.md
  - workplans/archive/DOC-MVSEL2_forward_lazy_selector.md
  - release/MLFF_MVSEL2_QUALIFICATION_0.20.242a0.json
  - mdstats/training_data/target_multi_view_selector_v2.py
  - mdstats/training_data/target_multi_view_repair_v2.py
  - mdstats/training_data/target_multi_view_selection_state_v2.py
  - mdstats/training_data/target_coverage_sparse_index_store.py
  - mdstats/training_data/campaign_cli.py
  - tests/test_mlff_mvsel2_forward.py
  - tests/test_mlff_mvstate2.py
  - tests/test_mlff_repair2.py
  - tests/test_mlff_mvmigrate2.py
architecture_refs:
  - docs/arch_manuals/mlff_training_data_architecture.md
  - docs/arch_manuals/mlff_training_data/50_target_multiview.md
  - docs/arch_manuals/mlff_training_data/60_execution_performance.md
spec_refs:
  - docs/specs/training_data/mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md
expected_change_paths:
  - mdstats/training_data/target_multi_view_repair_v2.py
  - mdstats/training_data/target_multi_view_selector_v2.py
  - mdstats/training_data/target_multi_view_selection_state_v2.py
  - mdstats/training_data/target_coverage_sparse_index_store.py
  - mdstats/training_data/campaign_cli.py
  - tests/test_mlff_repair2.py
  - tests/test_mlff_mvstate2.py
  - tests/test_mlff_mvmigrate2.py
  - tests/test_mlff_mvsel2_forward.py
  - benchmarks/
  - release/MLFF_MVSEL2_QUALIFICATION_0.20.242a0.json
  - docs/specs/training_data/
  - docs/arch_manuals/mlff_training_data/
  - docs/arch_manuals/mlff_training_data_architecture.md
  - docs/history/mlff/
  - CHANGELOG.md
default_gate_approval: AUTO
candidate_identity_policy: include all tracked product/runtime source, tests, specifications, architecture, package/build/config/schema, release metadata, and tracked generated product artifacts; exclude only workplans, qualification/verification coordination artifacts, and benchmark/evidence logs that cannot affect build/runtime/scientific/package behavior
---

# DOC-MVSEL2-HARDEN1-V3 — MVSEL2 Post-Implementation Conformance Hardening

## 1. Migration authority

This is the Protocol v3 continuation of `DOC-MVSEL2-HARDEN1` revision 1. The source workplan's diagnosis, frozen scientific/algorithmic design, invariants, non-goals, acceptance thresholds, and design-revision triggers are incorporated by reference and remain unchanged. The source workplan remains historical lineage and MUST NOT be rewritten to hide review findings.

The analyzed implementation commit remains an ancestor of the current feature branch. Changes after that commit at migration time are coordination/workplan-only and do not invalidate the source diagnosis.

## 2. Objective

Harden the completed `feat/mvsel2-forward-lazy` implementation so it conforms to the frozen DOC-MVSEL2 revision-4 architecture and becomes a source-complete candidate suitable for independent qualification and verification.

The implementation authority MUST NOT redesign MVSEL2 scoring/lazy certification, REPAIR1 scientific semantics, MVIDX1 scientific identity/schema, target-data policy, or unrelated MLFF training/evaluation behavior.

## 3. Frozen correction design

Implementation MUST preserve and realize the source workplan sections 4.1 through 4.6 exactly:

1. REPAIR2 policy/default/validation is a semantic mirror of REPAIR1 except v2 authority/schema identity.
2. Complete persisted REPAIR2 swap records and terminal order match REPAIR1 for shared fixtures/policies.
3. Production MVSEL2/REPAIR2 execution obtains MVIDX runtime state through the native forward-only reader without inverse-array mapping inside the v2 execution boundary.
4. Campaign interrupted selection resumes from the highest valid compatible MVSTATE2 checkpoint, reconstructs historical entries by selected-candidate-only forward replay, and performs one exact Phase-B frontier rebase after restore when needed.
5. REPAIR2 consumes MVSTATE2 at selector-to-repair boundaries, uses selected-prefix forward replay only as fallback, and never restores later pure-selector state after the first accepted repair divergence.
6. REPAIR2 rejected proposals use no full forward-state clones; proposal scoring is the exact analytical hypothetical defined by source section 4.6, and accepted mutation happens exactly once after the winner is chosen.

## 4. Gate state and qualification barriers

All implementation gates are AUTO. H0-H4 have `qualification_barrier: no`; implementation may prepare them sequentially using local/source checks. H5 contains mandatory qualification checks and therefore has `qualification_barrier: yes` before release closeout acceptance. H6 may be prepared only to the extent that tracked candidate documentation/generated product artifacts can be finalized before qualification; final acceptance/archive remains verification-owned.

| Gate | Implementation | Qualification | Acceptance | Barrier |
|---|---|---|---|---|
| H0 REVIEW-BASELINE | PENDING | NOT_REQUIRED | PENDING | no |
| H1 REPAIR2-SEM1 | PENDING | NOT_RUN | PENDING | no |
| H2 MVIDX-FWD-RUNTIME1 | PENDING | NOT_RUN | PENDING | no |
| H3 MVSTATE2-RESUME1 | PENDING | NOT_RUN | PENDING | no |
| H4 REPAIR2-SCALE1 | PENDING | NOT_RUN | PENDING | no |
| H5 QUAL-HARDEN1 | PENDING | NOT_RUN | PENDING | yes |
| H6 CLOSEOUT-HARDEN1 | PENDING | NOT_RUN | PENDING | yes |

## 5. Gate acceptance

### H0 REVIEW-BASELINE

Prepare focused regression/sentinel coverage for every diagnosed blocker: REPAIR2 default-policy mismatch, complete trace fidelity, campaign native-forward runtime use, interrupted-selection resume, REPAIR2 checkpoint reuse, and proposal-copy/replay behavior. Baseline failures must be attributable to the diagnosed contracts rather than environment state.

### H1 REPAIR2-SEM1

V1/V2 default policy fields and validation semantics match except authority/schema identity; default-policy non-empty repair fixtures produce identical complete swap records and terminal orders; explicit-policy fixtures remain schedule invariant; bottleneck/objective fields preserve historical semantics; no MVSEL1 eager/inverse dependency is reintroduced.

### H2 MVIDX-FWD-RUNTIME1

Production v2 selection/repair uses the native forward-only reader; inverse-array open/map sentinels stay untouched during the measured v2 execution boundary; MVIDX1 digests/content and legacy readers remain unchanged; forward-only restore evidence records inverse arrays unmapped.

### H3 MVSTATE2-RESUME1

Interrupted campaigns resume from the highest compatible valid checkpoint; resumed and uninterrupted entries/rungs/final digest are identical; corrupt newest checkpoint falls back to an earlier valid checkpoint and then exact rank-zero rebuild; Phase-B restore performs one exact rebase; REPAIR2 consumes MVSTATE2 before divergence and never later restores pure-selector state after divergence; fallback is selected-prefix forward replay only.

### H4 REPAIR2-SCALE1

Rejected proposals perform zero full forward-state clones; proposal evaluation implements the exact no-copy analytical hypothetical; accepted trace remains H1-equivalent; production repair is measurable through all materializable rungs up to 16,384 on the 36,408-candidate/165-family graph or remains BLOCKED with exact external prerequisite; evidence records wall time, proposals/shortlist, swaps, restore/replay mode, RSS, and inverse-array status; execution remains bounded by StageResourceScope; combined chain retains the frozen >=10x floor versus same-host MVSEL1 baseline/projection.

### H5 QUAL-HARDEN1

Prepare and hand off focused v2 tests, adjacent v1 regressions, full non-slow suite, production selector/state/repair benchmarks, clean wheel/install/import qualification, code-under-test SHA binding, distribution exclusion of workplans, and explicit GPU `DEFERRED_NOT_RUN` unless genuinely executed. Resolve repository-local collection blockers without unrelated dependency churn before handoff.

### H6 CLOSEOUT-HARDEN1

Before qualification, stage candidate specification/architecture/history/changelog/release metadata and tracked generated product artifacts so the exact candidate is what qualification will test. Final evidence claims, verification decision, workplan COMPLETE state, and archive move remain downstream responsibilities. No evidence-only commit may alter candidate content identity.

## 6. Design-revision triggers

Return `DESIGN_REVISION_REQUIRED` for any trigger listed in source workplan section 14, including changes to frozen MVSEL2/REPAIR1 scientific semantics, weakened complete repair-trace equivalence, MVIDX1 scientific schema/content change, restoring pure-selector state after repair divergence, approximate/stochastic repair, or inability to retain the frozen >=10x performance floor without a different algorithmic design.

Use `BLOCKED: STALE_WORKPLAN` if product-relevant assumption/current-authority/target-interface changes move beyond the analyzed implementation before implementation begins.

## 7. Candidate and qualification handoff

Implementation must establish `candidate_ref`, `candidate_commit`, deterministic `candidate_content_identity`, and the candidate identity policy above before target qualification. Product source mutation is forbidden during qualification. The Qualification Handoff must enumerate exact checks, commands/cwd, capability requirements, inputs, expected results, evidence/output paths/classes, evidence dependencies, and retry modes.

Implementation may end at `PREPARED_FOR_QUALIFICATION`; it MUST NOT self-declare the workplan COMPLETE or the candidate MERGE_READY.
