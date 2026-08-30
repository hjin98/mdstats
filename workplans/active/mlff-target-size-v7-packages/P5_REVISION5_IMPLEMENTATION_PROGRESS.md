---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 5
status: implemented-pending-independent-review
package_revision: 5
amended_date: 2026-08-29
contract: P5_POST_SELECTION_CV_FINAL_PRODUCTION.md
entry_p4_closure_commit: 145388e5ad11733be1c19539886e34b82cc7d7d2
implementation_closure: Cumulative revision-2 + revision-3 + revision-4 + revision-5 P5 contract implemented; 77 P5 acceptance tests plus affected P1-P4/CLI/EVAL2 regression pass.
---

# P5 revision 5 — implementation evidence record

This is a coordination/evidence record, not an authority. The frozen parent and
`P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` remain the contract.

## 1. What was built

New current-generation owners under `mdstats/training_data/`:

| Module | Owns |
| --- | --- |
| `campaign_post_selection.py` | the one current selected-training adapter and the immutable `PostSelectionBinding` lineage record |
| `post_selection_identity.py` | shared `PostSelectionMethodIdentity` plus separate `CvValidationPolicyIdentity` / `FinalProductionPolicyIdentity`, all resolved from configuration alone |
| `post_selection_cv_plan.py` | the selected-only P1 split-exclusion projection, the complete K-fold CV plan, and per-fold run plans |
| `post_selection_cv_acceptance.py` | target-only fold/seed/campaign acceptance and the production authorization check |
| `post_selection_production.py` | the fresh final-production plan, its M3 lineage, and its run plans |
| `post_selection_run_identity.py` | collision-proof screen / CV-fold / final-production execution identity |
| `post_selection_execution.py` | fitted preparation, DATA8 materialization, TRAIN2 execution, EVAL2 evidence |
| `post_selection_store.py` | content-addressed evidence storage and commit-time currentness-fenced publication |
| `campaign_post_selection_runtime.py` | the `cross-validate` and `train-production` orchestrators |

Existing owners generalized rather than duplicated:

- `target_size_execution/evaluation.py`: `_authenticate_target_size_provider` became the
  exported `authenticate_train2_checkpoint_provider`, taking the evaluation model state
  instead of a screening trajectory, so post-selection evaluation reuses the same
  checkpoint-provenance owner;
- `target_size_execution/common.py`: `fit_membership_frame_training_weights` exposes the
  shared objective-weighting seam for fold-local and final fits;
- `campaign_control.py`: `inventory_checkpoint_files` takes a run identity directly, so
  screening and post-selection share one checkpoint inventory;
- `storage_accounting.py`: post-selection evidence has its own restart-critical ownership
  family that no storage tier may reclaim;
- `_campaign_cli_core.py`: `cross-validate` / `train-production` subcommands, the
  generated `[post_selection.*]` configuration surface, and the redirected fail-closed
  messages on `materialize` / `train` / `evaluate`.

## 2. Frozen decisions and how they are realized

- **Acyclic hierarchy.** Policy identities are pure functions of resolved configuration
  and stable policy objects; plans bind exact current scientific lineage; evidence binds
  plans. `resolve_post_selection_method_policies` is the single resolution point, so the
  digest that describes the method and the policy objects the runtime executes cannot
  drift apart.
- **CV universe.** Exactly `T_selected`, with roles allocated over whole components from
  `project_split_exclusion_constraint_components` — the same P1 closure owner P2 uses.
  `K >= 2` is enforced in the policy record; an infeasible `K` raises before any DATA7/
  DATA8/TRAIN2 work.
- **Ordering.** A fold's representative is frozen from its own monitor through
  `assess_eval2_checkpoint` + `order_eval2_admissible_candidates` (target-only) before the
  held-out fold is evaluated at all.
- **Acceptance.** `accept_post_selection_cv_campaign` is coverage-first: every required
  fold of every required seed, present exactly once and accepted. Mean, majority,
  best-seed, partial-fold, and `cv_not_performed` outcomes are not representable.
- **Production.** Full exact `T_selected`, `[training].max_num_epochs` as the only horizon
  authority, frozen `M3` on the plan rather than the policy, fresh run state, and run
  identities that hash their role.
- **Currentness.** No mutable post-selection current-state owner. Pointers live inside the
  binding's namespace and are written inside the same `BEGIN IMMEDIATE` transaction that
  re-reads the current campaign revision.
- **Restart.** Completed folds and production runs are reused after re-checking the plan
  and predicate they were produced under; the parent chain is re-authenticated first.

## 3. Acceptance executed

77 P5 tests across seven files, all through real config/CampaignStore/P1-P5 owners with
MACE substituted only below the owner boundary:

| File | Covers |
| --- | --- |
| `test_mlff_target_size_p5a_selected_context.py` | adapter, exact `T_selected`, FAILED_SCIENTIFIC refusal, stale-generation refusal, absence of result-JSON authority |
| `test_mlff_target_size_p5b_identity_hierarchy.py` | pre-execution resolution, no descendant evidence in policies, no reverse authority, the full invalidation DAG, CV-budget independence, `K < 2` refusal |
| `test_mlff_target_size_p5c_cv_plan.py` | exact universe, complete once-each coverage, unselected-sibling and relation-only adversarial fixtures, determinism, infeasible-`K`, omission/duplication refusal, stale relation authority |
| `test_mlff_target_size_p5d_cv_acceptance.py` | target-only predicate, replay ranking-reversal fixture, inadmissible representative, failing/missing/duplicate fold, all-required-seed, dispersion diagnostic-only, method-mismatch refusal |
| `test_mlff_target_size_p5e_production_and_restart.py` | full-`T_selected` production, M3 role, horizon vs `n3`, freshness, namespace disjointness, authorization, the g1-vs-g2 publication race, create-once evidence, held-out visibility ordering, resume, storage ownership, CV-only and production-only invalidation |
| `test_mlff_target_size_p5f_structure.py` | absence of DATA5/label-domain authority, replay-weighted scoring, locked/calibration reach, P4 mutation, screening continuation, `n3` budget edges, and V7-prefixed symbols |
| `test_mlff_target_size_p5g_assembled_integration.py` | the assembled `prepare -> select-target-size -> cross-validate -> train-production -> reload` lifecycle |

Affected regression rerun and passing: P3 execution suites, P3A4, P3A9, P4-A through P4-G,
target-size repair1, neutral substrate, statistical authorities, EVAL2, select2,
locked-test2, audit-eval-perf1, campaign CLI, DATA9B1, evaluation/verification cost policy,
partial-completed verification.

Two pre-existing expectations were reconciled with the accepted change rather than worked
around: `test_mlff_target_size_p3a4_final_review.py` now calls the renamed shared provider
owner, and `test_mlff_campaign_cli.py` / `test_mlff_target_size_p4f_storage_docs_structure.py`
expect the two new commands and the redirected `materialize` narrative.

Because the diff crosses widely shared CLI/execution/storage surfaces, the complete
repository suite was run on the final candidate and on the pre-P5 baseline
(`5bf53c99ce31d1438c21bae81c0f30c79176bdc4`) under identical conditions. The two failure
sets are **identical** — 247 failed / 92 errors on both, with no new failures and none
fixed — while the candidate passes 3814 against the baseline's 3735. Those pre-existing
failures are historical release-version/specification-synchronization assertions and
tests needing external LTA reference data absent from this environment; none of them is
in the P5 affected surface.

## 4. Not done here

- **Independent review** has not run. P5 is implemented, not accepted; P6 stays blocked.
- **Long GPU / full-production qualification** remains deferred as the contract requires.
- **PDF regeneration** for the changed permanent Markdown could not run: `pandoc` is
  absent from this environment, so `docs/build_architecture_pdf.sh` fails before rendering.
  The Markdown sources and the assembled composite manual are current; the PDF and its
  manifest are stale and need one rebuild on a host with the renderer available.
