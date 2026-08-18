# mdstats 0.20.121a0 patch notes

## MLFF adaptive-training revision plan

This release is architecture/documentation only. It records a new gated MLFF revision after the validation-size, FP32/FP64, replay-retention, and checkpoint-selection studies. No production training/evaluation behavior changes in this release.

The new roadmap contains seven ordered gates (`ADAPT-PREC1` through `ADAPT-MIGRATE1`). It plans to:

- reduce learned-model precision to `single` (FP32) or `double` (FP64), remove staged `refine`, and not introduce a user-facing mixed-model mode;
- keep mdstats-owned scientific fitting, reductions, statistics, and persistent simulation bookkeeping hard-coded in FP64;
- use a common deterministic 256-configuration target monitor and a 512-configuration true-label replay monitor for epoch-wise stopping/ranking;
- introduce a default full target force-RMSE criterion of 30 meV/A, stop target adaptation at 80% of that criterion, derive the replay ceiling from target/replay score weights, and stop replay exhaustion at 120% of that derived ceiling;
- score only monitor-admissible epochs, retain one champion per independent run, and reuse monitor metrics without additional inference;
- retire production EVAL-MF successive halving in favor of full evaluation of the top five run champions, with next-five rescue only when the purchased batch contains no admissible candidate; and
- preserve exact `single|double` model dtype through all model inference/verification/export while retaining FP64 analysis arithmetic.

At the default 1:1 target/replay weighting, the planned force-RMSE geometry is 30 meV/A target eligibility, 24 meV/A target-success stop, 30 meV/A replay eligibility, and 36 meV/A replay-exhaustion stop. The 30-epoch limit remains a hard upper bound rather than a required training length.
