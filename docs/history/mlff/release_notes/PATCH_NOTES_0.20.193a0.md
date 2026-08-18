# mdstats 0.20.193a0

## MLFF CUEQ-DEFAULT1 training-default policy migration

- Make the generated TRAIN2 backend `cueq` while retaining `e3nn` as the generated source/DATA6/pseudolabel/evaluation/verification backend.
- Add explicit `[acceleration].training_backend` to newly generated campaign TOML; historical campaigns without the key retain their original unified-backend semantics.
- Add `TrainingAccelerationRealizationRecord.v1` so a qualified TRAIN2 CuEq realization carries no source-foundation execution authority.
- Qualify source and training realizations independently in `doctor`; CuEq training remains fail-closed when the CuEq stack or pure-training parity is unavailable.
- Bind DATA8/TRAIN2 optimizer identity and one-epoch preflight training to the training realization while keeping DATA6 and all post-training evaluation on the source realization.
- Keep `only_cueq=false` so trained checkpoints are converted back to portable e3nn form.
- Preserve explicit `--training-backend e3nn` reference runs and legacy `--backend` source selection.
- Treat this release as an explicit generated-policy revision requested by the project owner; it does not retroactively change CUEQ-PHASE1, PERF-CERT1, or FINAL-GPU1 evidence records, and it does not claim positive CUDA performance evidence on the CPU development host.
- Advance canonical MLFF architecture to revision 60 and dependency-graph schema 42.
