# mdstats 0.20.123a0 patch notes

## ADAPT-MON1 — fixed common online validation monitors

This release implements the second gate of the adaptive MLFF revision.

### Common target monitor

New campaign preparation freezes one target online monitor shared by every competing fold, seed,
method, and final-development job. The default budget is 256 configurations selected only from
the common DATA5 `outer_monitor` domain. Selection balances condition/run strata and uses a
deterministic random-start systematic sample along source time, avoiding fold-dependent monitor
sizes and first-N temporal bias.

### Independent true-label replay monitor

New campaigns also require independent true replay labels during preparation. A default
512-configuration monitor is selected deterministically with chemistry/size-aware coverage and
materialized as `shared/replay/online_true_replay_monitor.xyz`. In multi-head MACE jobs this
artifact becomes `pt_valid_file`; replay gradient training continues to use the configured replay
training artifact, including pseudo labels when selected.

### Immutable identity

The monitor policy, exact memberships, parent evidence, requested/realized sizes, strata, seed,
label mode, and fallback reasons are content-addressed. Production materialization, DATA8, and
training-protocol identities bind these records. Historical schemas remain readable.

### Runtime boundary

ADAPT-STOP1 is intentionally not included. The common monitors are evaluated during normal MACE
validation, but they do not yet stop training early; `max_num_epochs` remains authoritative.
ADAPT-EVAL1 is also pending, so EVAL-MF remains the production evaluator in this release.

### Defaults

```toml
[random]
online_monitor_seed = 161803

[training]
online_target_monitor_configurations = 256
online_replay_monitor_configurations = 512
```

`ADAPT-STOP1` is the next implementation gate.
