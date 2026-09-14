# Post-selection (P5) method restoration — replaced semantics

This file is **non-normative history**. Current behavior is owned by
`docs/methods/mlff_numerical_algorithmic_method.md`, the MLFF training-data
architecture, and `docs/specs/training_data/mlff_post_selection_p5_spec.md`.

## Why the pre-restoration P5 was replaced

The pre-restoration implementation realized several descendants of a
superseded method. Each is listed with what replaced it and why an old record of
that kind cannot become current.

| Superseded P5 semantic | Restored semantic | Currentness consequence |
|---|---|---|
| Foundation fine-tuning trained with MACE's weighted energy+forces+stress loss; the multi-head `UniversalLoss` selector was rewritten to `stress`. | `naive_fine_tuning` and `multihead_replay` execute native `UniversalLoss` with `huber_delta = 0.01` and E:F:S 1:10:1; the rewrite was removed and the loss is authenticated after every MACE mutation region. P3 and P5 `scratch` keep the weighted family (`MACE_WEIGHTED_LOSS_FAMILY`, renamed from `MACE_EXECUTABLE_LOSS_FAMILY`). | MACE execution authority v2 carries the training mode and loss parameters; post-selection execution evidence records loss parameters and loader geometry. |
| `PostSelectionMethodIdentity` bound the whole P3 `TargetSizeCommonTrainingPolicy` digest. | Identity v2 binds a mode-specific objective digest, a P5 preparation-policy digest, and an exposure-policy token (recipe `2026-09.v5`). | P3-only objective/weighting/harness edits no longer move foundation P5; a v1 identity does not deserialize. |
| Foundation preparations fitted from-scratch E0 plus configuration weights. | Mode-disjoint `PostSelectionFittedPreparation` v3: foundation modes fit selected-head foundation-residual E0 through the existing fitter, persist the selected-head prediction/reference-E0 inputs with the run's materialization, and require exact-rational composition transfer (`c^T v = 0`) for every training, common-monitor, and held-out composition. | v2 preparations are history; cross-mode fields fail deserialization. |
| Target/replay training-head scalar weights (`[training].target_head_weight`, `replay_head_weight`) were read into the replay plan. | Retired. P5 configuration rejects them; `ReplayPreparationPlan` v5 carries no head weights (v1/v3/v4 remain readable history); the uncalled DATA8 weighted-replay staging helpers were deleted. | Checkpoint/adaptive-stop score weights are unchanged. |
| Split-file replay silently defaulted an omitted `[replay].mode` to foundation pseudo-labels. | Omission fails closed; single-source `replay_set` resolves omitted `label_mode` to `true_dft`. | — |
| Each CV fold reserved selected-only checkpoint-monitor components (`checkpoint_monitor_components_per_fold`); final production monitored on P3 `M3`. | One exact 256-frame common target monitor from the neutral `OUTER_MONITOR` role (D2 section 15 sampler), proven relation-disjoint from every frozen selected set, bound by every CV and final plan. Folds are training + held-out + purge only; default `K = 3`. | CV policy v2, fold/plan v2, final plan v2 (no M3 fields), publication decision v2 all advanced. |
| `single_best_final_seed` ranked final seeds over M3 metric records; a missing representative record triggered re-evaluation. | Ranking reuses the accepted EVAL2 ordering over the frozen common-monitor records; missing records fail closed. The downstream deployment probe reads M3 directly from the P2/P3 definition. | Qualification publication view v2 binds the common-monitor digest. |
| Legacy selected bindings substituted their stored historical method identity, and pre-fix materializations could be reused. | Removed: every current P5 context executes the restored method; historical run roots fail currentness and are preserved for diagnosis. | — |

Production-scale GPU qualification of the restored method is deferred to the
final release package.
