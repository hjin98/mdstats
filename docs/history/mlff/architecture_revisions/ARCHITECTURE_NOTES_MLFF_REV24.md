# MLFF architecture revision 24 planning notes

This source-tree note records the adaptive-training and evaluation-simplification revision opened after mdstats 0.20.120a0. The original seven-gate plan is preserved below; implementation is now complete through ADAPT-PREC1 (0.20.122a0), ADAPT-MON1 (0.20.123a0), ADAPT-STOP1 (0.20.124a0), ADAPT-RANK1 (0.20.125a0), ADAPT-EVAL1 (0.20.126a0), ADAPT-VERIFY1 (0.20.127a0), and ADAPT-MIGRATE1 (0.20.128a0).

Ordered gates:

1. `ADAPT-PREC1` - collapse learned-model precision to `single|double`; retire staged `refine` and do not add a user-facing `mixed` model mode. Model dtype follows all MACE inference; mdstats-owned scientific arithmetic remains FP64.
2. `ADAPT-MON1` - replace variable fold-local production monitors with a fixed common 256-configuration target monitor and fixed 512-configuration true-label replay monitor, with deterministic coverage-aware sampling.
3. `ADAPT-STOP1` - add a 30 meV/A default full target force-RMSE criterion, derive replay ceiling from target/replay score weights, and stop training at 80% of the target ceiling, 120% of the replay ceiling, or 30 epochs.
4. `ADAPT-RANK1` - use already-computed epoch monitor metrics for zero-new-inference weighted scoring and retain exactly one champion per independent run.
5. `ADAPT-EVAL1` - retire production EVAL-MF successive halving; fully evaluate the top five run champions on common full target and true-label replay domains, with deterministic next-five rescue only when no purchased candidate is admissible.
6. `ADAPT-VERIFY1` - select the minimum weighted full score among candidates that pass target, replay, and retained physical gates; preserve model dtype through verification/export while keeping scientific bookkeeping FP64.
7. `ADAPT-MIGRATE1` - close schema, restart, historical EVAL-MF/refine readability, storage interactions, and end-to-end qualification.

Canonical defaults recorded by this revision:

- target full force-RMSE ceiling: 30 meV/A;
- target online stop fraction: 0.80 (24 meV/A at the default ceiling);
- target online monitor: 256 configurations;
- replay online monitor: 512 true-label configurations;
- target:replay score weights: 1:1;
- replay ceiling: `(target_weight / replay_weight) * target_ceiling` (30 meV/A at 1:1, 60 meV/A at 2:1);
- replay online stop multiplier: 1.20 (36 meV/A at default 1:1);
- maximum epochs: 30;
- initial full-evaluation finalists: 5;
- rescue batch size: 5.

The canonical details are in `docs/arch_manuals/mlff_training_data_architecture.md`. Binary precision, common monitors, adaptive stopping, and run-local lightweight ranking now follow the ADAPT contracts above. EVAL-MF remains runtime-authoritative only for campaign-wide evaluation until ADAPT-EVAL1 closes; historical staged-precision/EVAL-MF evidence remains readable.
