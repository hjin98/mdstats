# mdstats 0.20.71a0 production training runtime-path fix

## Symptom

Every production training job failed immediately with a missing staged foundation model, for example:

```text
FileNotFoundError: ../../shared/foundation/mace-mpa-0-medium.model
```

The required preflight had passed with the same DATA8 configuration.

## Cause

DATA8 intentionally emits portable paths relative to each immutable job directory:

- `foundation_model = ../../shared/foundation/...`
- local target `train_file` and `valid_file` entries
- replay `pt_train_file` and `pt_valid_file` entries under `../../shared/...`

Preflight launched MACE with the DATA8 job directory as its working directory, so these paths were valid. Production `train` instead launched from `runs/<run-id>`. MACE resolves configuration paths against the process working directory rather than the YAML file location, so the foundation path pointed outside the promoted DATA8 tree. Target and replay paths would have failed next.

## Correction

- Production MACE now runs from the immutable DATA8 job directory.
- `--model_dir`, `--checkpoints_dir`, `--log_dir`, and `--results_dir` are supplied as absolute paths under `runs/<run-id>`, keeping generated files out of DATA8.
- All referenced foundation, target, and replay files are validated for every selected run before any child process is launched.
- The runtime layout is versioned. Failed records produced by the obsolete layout are archived under `runs/<run-id>/obsolete-runtime-<digest>/` and a fresh bounded attempt sequence starts automatically.
- `--restart_latest` is used only when a checkpoint exists, avoiding a second deterministic failure after a pre-checkpoint launch error.

## Restart behavior

Install 0.20.71a0 and rerun `train`. Do not rerun `prepare` or `preflight`. Existing prepared DATA8 trees and successful runs remain valid. Failed 0.20.70a0 attempts are preserved in an archive and do not consume the new runtime policy's retry budget.
