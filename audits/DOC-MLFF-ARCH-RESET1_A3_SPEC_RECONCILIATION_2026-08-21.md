# DOC-MLFF-ARCH-RESET1 A3 — current specification reconciliation

**Status:** PASS — current normative index frozen; superseded unindexed residue assigned to A4  
**Branch:** `docs/mlff-architecture-reset`  
**Architecture:** revision 105

## Reconciled current owners

A3 establishes these exact current owners for the redesigned surfaces:

| Decision / contract | Current specification owner |
|---|---|
| cross-cutting evidence/identity/leakage/protocol invariants | `mlff_data_stage_plan_spec.md` |
| fold/final-domain fitted metrics, E0, objective/weights, difficulty and subset inputs | `mlff_data7_fitted_metrics_selection_spec.md` |
| common target/replay monitor construction | `mlff_online_monitor_spec.md` |
| FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL integrated target-subset chain | `mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md` plus narrow FEAS/MVIDX/MVQUAL runtime specs |
| independent hard prefix qualification | `mlff_target_data2c_mvqual1_same_n_qualification_spec.md` |
| scientific target-size population, 3/10/30 fidelity funnel, selected size / typed failure | `mlff_target_subset_size_study_spec.md` |
| protocol-matched held-out cross-validation | `mlff_mlcv_cross_validation_spec.md` |
| final-development hard admissibility, ranking, committee construction | `mlff_mlcv_final_selection_spec.md` |

## Major conflicts removed

1. DATA7 no longer owns `SelectionBudgetPolicy`, `TrainingSelectionPlan`, or a second target-membership ladder. It terminates at `TargetSubsetInputBundle`.
2. Target-monitor/replay-monitor sizes are type-distinct from target-training sizes.
3. MVQUAL no longer compares a legacy selector/ladder to a current one; it independently verifies current repaired prefixes.
4. The multi-view contract no longer requires MVSEL1/REPAIR1/MVSTATE-REUSE1 readability or migration equivalence as current behavior.
5. Cross-validation validates a protocol whose target size is already frozen; held-out folds cannot choose size or checkpoints.
6. Final selection no longer rewards replay degradation/integrity in a combined score; mandatory replay/integrity requirements are hard constraints by default.
7. The cross-cutting system contract no longer contains a separate quota/FPS target selector or stage/gate chronology.

## Target-size exact policy

The new single `TargetSizeStudyPolicy` owns:

- nominal population `{128,256,512,1024,2048,4096,8192,16384}`;
- common materializability across required fold/final gradient-training domains;
- MVQUAL-defined qualified population;
- minimum three qualified sizes;
- exact continuation `0 -> 3 -> 10 -> 30` epochs;
- frozen paired seed set and common protocol semantics;
- ordinary success early-stop disablement during size comparison;
- `q -> min(q,4) -> 2 -> 1` production funnel;
- 1 meV/Angstrom early-screen practical-equivalence width with smaller-size preference;
- final hard admissibility;
- typed insufficient/non-convergence/failure outcomes;
- no generated/intermediate rescue size;
- production-versus-exhaustive-qualification distinction;
- bounded prefix-view materialization.

## Current specification index

`docs/specs/training_data/README.md` is now concept-oriented and current-only. It explicitly states that only listed specifications are current normative owners.

Release/gate/migration-era documents that remain physically present but are **not listed** are non-current residue pending A4 consolidation/removal. Their presence cannot override the current index or architecture.

## A3 review findings

### Complexity

The redesign lowers semantic path count: one fitted-preparation path, one target-membership chain, one target-size policy, one held-out CV interpretation, and no compatibility state machine. No adapter/precedence layer was added to reconcile obsolete owners.

### Statistical correctness

The current specification set preserves training-domain fitted isolation, keeps held-out CV outside target-size/checkpoint control, keeps locked tests sealed, and treats replay/integrity as constraints rather than target-score rewards.

### Resource correctness

The target-size specification requires prefix views over one repaired order per domain and prohibits product-scale per-rung duplication. Exhaustive survivor-recall training is explicitly qualification-only.

## Acceptance

- **PASS:** every revised material decision has one current specification owner.
- **PASS:** the current spec index contains no migration-only or historical entry.
- **PASS:** architecture and revised exact specifications agree on DATA7, MVSEL2/REPAIR2/MVSTATE2/MVQUAL, target size, CV, and final selection.
- **PASS:** superseded unindexed files are explicitly non-current and assigned to A4 rather than treated as fallback authority.

A4 may proceed.
