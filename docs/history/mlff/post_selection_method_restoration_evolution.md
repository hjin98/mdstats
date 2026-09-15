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

## Foundation CV competence / production quality separation

**Lifecycle state:** proposed on `fix/mlff-cv-competence-threshold-separation`
against integrated `8553ebe9ed86b24dfe910c9e43acc6230d3ece90`. The D1/D2
revision is pending independent review and stakeholder ratification; this entry
records the candidate delta and does not make it current.

The restoration above preserved the target/replay thresholds because threshold
revision was outside its scope. That preservation is not evidence that CV and
production ceilings must be equal. A later review found the target-force
ceiling owned too broadly: it was part of shared method identity, so foundation
CV paid the late slow-convergence cost of the production criterion.

| Previous semantic | Replacement semantic | Currentness consequence |
|---|---|---|
| One `[acceptance]` target-force ceiling (nominally `0.030 eV/angstrom`) gated checkpoints for both foundation CV and fresh production, and the full target-bearing `CheckpointAdmissibilityPolicy` digest was bound by `PostSelectionMethodIdentity`. | Method identity v3 binds only the shared checkpoint constraints (replay retention/TRUE_DFT, finite metrics, physical/integrity gates). CV policy v3 owns the foundation-CV checkpoint competence ceiling `0.045`; final-production policy v2 owns the production checkpoint ceiling (`[acceptance]`, `0.030`). One owner composes the effective policy per run after authenticating the run plan's method and role-policy digests, before training and before candidate assessment. | **One-time cutover:** v2 method, v2 CV and v1 production policy records no longer deserialize, so pre-cutover P5 CV/final descendants are stale once even where production still uses `0.030`; P1/P2/P3, frozen selection, common monitor, replay and source evidence keep their own identities. No threshold-equivalence translation exists: a prior 30 pass is not current under 45, and a prior 30–45 failure is not retroactively a pass. |
| Foundation CV held-out default `acceptance_maximum = 0.030`, mode-agnostic. | Foundation CV (`naive_fine_tuning`, `multihead_replay`) defaults to `0.045` in the units of `acceptance_metric`; scratch keeps `0.030` and its `[acceptance]` checkpoint ceiling. Explicit values are kept as written; an alternate outer metric never supplies the checkpoint ceiling. | **Steady state:** a CV-only edit moves the CV policy, plan and run positions only; a production-only ceiling edit moves the production policy and run positions only; a shared replay/physical/integrity edit moves the method and both roles. |

CV consistency remains every required fold/seed passing both predicates, with
dispersion diagnostic-only; training remains fixed-budget. The ceiling split
permits a deliberately shorter fixed CV horizon without weakening production.

**Calibration provenance.** `45 meV/angstrom` is a stakeholder-authorized
calibration from recalled foundation-adaptation learning curves (fast initial
decrease, markedly slower convergence through roughly 40–20 meV/angstrom, with
the 30 meV/angstrom production criterion inside that slow regime). It is not a
recovered repository study.

**Downstream boundary.** Neither the 45 meV/angstrom CV criteria nor the
30 meV/angstrom production common-monitor criterion is external adequacy, a
locked test, or release qualification; downstream qualification is unchanged.

**Rejected concretization.** An intermediate workplan amendment required binding
the effective policy through a per-run DATA8 `TrainingProtocolIdentity` and a
generic EVAL2 plan. Accepted D3 already excludes both from P5 authority; the
requirement was superseded in favor of the existing role-plan/run-plan lineage
rather than adding a parallel protocol graph.
