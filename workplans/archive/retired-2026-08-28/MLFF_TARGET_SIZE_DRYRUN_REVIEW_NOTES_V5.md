---
kind: design-review-note
status: folded-into-active-workplan
reviewed_source_head: 6f0d34366ca954eabe21740ddda96357afc12eb1
review_date: 2026-08-28
---

# Target-size architecture implementation dry-run — review notes

This note records the current-state source conflicts that were folded into V5 of the active target-size architecture workplan. It is historical review evidence, not an independent active plan.

The dry-run inspected the real current owners in `target_size_study.py`, `labels.py`, `partition.py`, `data5_bundle.py`, `leakage.py`, `target_data_roles.py`, `difficulty.py`, `target_coverage.py`, `target_multi_view_selector_v2.py`, `target_multi_view_repair_v2.py`, `target_multi_view_qualification_v2.py`, `feature_metric.py`, `data7_bundle.py`, `production_materialization.py`, `data8_bundle.py`, `eval2.py`, `online_monitor.py`, `mlcv_roles.py`, `protocol.py`, `size_fidelity.py`, and the current campaign configuration surface.

Material findings folded into V5:

1. Target-size candidate, MVSEL2, REPAIR2, MVQUAL2, and target-coverage authorities are structurally per-label-domain, not merely reported that way. V5 therefore requires exactly one resolved target label compatibility identity before target allocation and removes domain collections/maps from current target-size persisted authority.
2. DATA5 currently serializes CV plans and its leakage audit binds CV plan digests. V5 splits pre-target DATA5 from post-selection CV so CV-only changes cannot invalidate target-size state.
3. TARGET-DATA2A currently requires the preselection CV lineage. V5 replaces it with a pre-CV allocation authority consuming DATA5 correlation/outer/leakage evidence only.
4. DATA6 currently constructs final-development and CV training-difficulty/prediction domains from DATA5 before target allocation. V5 separates role-independent base evidence from post-allocation target-training residual views and post-selection CV views.
5. DATA7 currently fits feature metrics, atomic E0, and training weights on a whole canonical DATA5 domain before applying a prescribed selected prefix. V5 separates selection-only preparation on `P_train` from gradient-bearing preparation on exact `T_N`, exact fold-training membership, and exact `T_selected`.
6. Existing unit-based CV/DATA7 membership expansion can reintroduce unselected sibling frames from a DATA5 unit. V5 makes exact selected frame membership first-class and uses inherited correlation/equivalence group IDs only for grouping, never for membership expansion.
7. Existing online target monitor uses DATA5 outer-monitor evidence for checkpoint control. V5 reserves outer target evidence for held-out validation; target-size stages use M-rung boundary evidence and final production may use frozen M3 for target-side checkpoint control. Replay true-label evidence remains admissibility-only.
8. Existing `SIZE-FIDELITY1` qualifies older full-development/coarse-monitor semantics. V5 retires or replaces it as production authority for the new M-ladder; new defaults require M-ladder-specific retrospective/reference qualification.
9. Current campaign configuration still treats target sizes as fixed. V5 explicitly includes parser/schema/roundtrip/example/resolved-config work for target/evaluation powers.
10. The MACE protocol carries a target validation artifact. V5 requires any training-time validation/diagnostic artifact used during exact target-size continuation to be provably non-controlling: it may not influence gradients, LR scheduling, early stopping, checkpoint ranking, or survivor selection between exact boundaries.

No executable source was changed by this review.
