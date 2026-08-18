# mdstats 0.20.77a0: deterministic campaign matrix and restart progress

## Restart correction

Training progress is reconstructed from attempt segments and the latest durable checkpoint. Duplicate or abandoned rows are not added to the percentage, and the displayed epoch cannot move backward. For qualified MACE 0.3.16 jobs, `--restart_latest` is source-checked and resumes at `checkpoint_epoch + 1`; a mismatch between the filename epoch and the epoch loaded by MACE fails closed.

## Explicit stochastic configuration

New `campaign.toml` files expose optimizer seed arrays and fold settings independently for `training.naive_fine_tuning` and `training.multihead_replay`. Fold assignment uses a platform-independent SHA-256 ordering. Replay selection, randomized DATA7 projections, Python hash randomization, and verification velocities also have explicit seeds.

The default remains two methods, seeds `[1, 2]`, and three cross-validation folds plus one final-development job per seed: 16 jobs total. Set a method `enabled = false`, shorten its seed array, or set `cross_validation_folds = 0` for final-only training.

Seed control makes every pseudo-random decision reproducible for fixed inputs. Bitwise equality across different CUDA, PyTorch, cuEquivariance, driver, or hardware versions is not promised because floating-point kernel scheduling is not a pseudo-random choice.
