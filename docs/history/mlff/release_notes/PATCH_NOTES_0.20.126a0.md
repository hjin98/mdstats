# mdstats 0.20.126a0 patch notes

## ADAPT-EVAL1 — top-K authoritative full evaluation

This release implements the fifth gate of the post-0.20.120 adaptive MLFF revision and retires
EVAL-MF successive halving from newly generated production campaigns.

### Zero-partial-round finalist screening

New configs use `checkpoint_strategy = "adaptive_topk"`, `finalist_count = 5`, and
`finalist_rescue_batch_size = 5`. ADAPT-EVAL1 consumes one immutable ADAPT-RANK1 champion per run,
orders those champions by their already-paid lightweight target/true-replay score, and initially
purchases authoritative full evaluation for at most five models. No 10% or 33% EVAL-MF inference
is launched.

### Separate lightweight and full domains

DATA8 now materializes the complete DATA5 outer-monitor domain as
`shared/target/full_target_evaluation.xyz`; the 256-frame online target monitor remains only a
training/screening subset. Full replay evaluation uses the complete configured independent TRUE_DFT replay monitor domain
resolved from `[paths].replay_true_labels`, rather than the 512-frame online replay subset. It does
not silently expand to the replay-training corpus. Every adaptive run therefore receives the same
common full target and replay domains.

### Comparable naive and replay-trained scores

Naive fine-tuning remains a one-head model and receives no replay gradients. For adaptive training,
mdstats injects the fixed TRUE_DFT replay monitor as an auxiliary validation-only loader evaluated
through the target head. It is inserted before the ordinary target loader so MACE's historical
last-loader checkpoint/patience scalar remains target-driven. Multi-head replay continues to obtain
its replay metric from `pt_head`. STOP1/RANK1 target+replay scores are therefore comparable across
methods before campaign-wide finalist ordering.

### Full acceptance and rescue

Each finalist is evaluated in its own learned-model dtype (`single` FP32 or `double` FP64). mdstats
uses FP64 reductions/statistics after inference. Target and weight-derived replay RMSE ceilings plus
retained energy/focus/stress/worst-condition safety gates are applied before weighted ranking. The
historical foundation-relative replay degradation is retained as a diagnostic, not the default hard
selector. If the first batch contains no admissible model, the next five champions are evaluated;
rescue stops once an admissible candidate appears or the pool is exhausted.

### Gate boundary

ADAPT-EVAL1 freezes the ordered fully admissible candidate set but does not yet perform deployment
verification, verification-failure fallback, or final export. Those responsibilities remain
ADAPT-VERIFY1. Historical `bounded`, `exhaustive`, and `multi_fidelity` evaluator behavior remains
available for compatible old campaigns.
