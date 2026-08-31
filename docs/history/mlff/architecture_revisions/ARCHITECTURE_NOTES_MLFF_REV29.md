# MLFF architecture revision 29 - ADAPT-EVAL1 implementation

This release implements `ADAPT-EVAL1` on top of the binary model-precision, common-monitor,
adaptive-stop, and run-local champion evidence established by ADAPT-PREC1 through ADAPT-RANK1.

Implemented contract:

- newly generated campaigns use `adaptive_topk`, with at most five initial full finalists and
  deterministic next-five rescue;
- no 10%/33% EVAL-MF partial rounds are purchased in the new production path;
- DATA8 materializes the complete common DATA5 outer-monitor target domain separately from the
  256-frame online target monitor;
- authoritative replay evaluation uses the complete configured independent TRUE_DFT replay monitor domain rather than
  the 512-frame online replay subset;
- naive runs obtain validation-only true-replay metrics through their target head, without replay
  gradients or an added trainable head, so STOP1/RANK1 scores are comparable to multi-head replay;
- each finalist is inferred in its own binary learned-model dtype while mdstats-owned reductions and
  scoring remain FP64;
- target/replay hard RMSE ceilings and retained energy/focus/stress/worst-condition gates execute
  before weighted full-score ranking;
- foundation-relative replay degradation remains a diagnostic rather than the default hard selector;
- full prediction/evaluation records are content-addressed and restartable;
- historical EVAL-MF strategies remain readable/selectable for pre-adaptive evidence;
- final deployment verification/fallback/export remains ADAPT-VERIFY1.

The canonical contract is documented in
`docs/history/mlff/retired_specs/mlff_adaptive_full_evaluation_spec.{md,pdf}` and the MLFF architecture
manual.
