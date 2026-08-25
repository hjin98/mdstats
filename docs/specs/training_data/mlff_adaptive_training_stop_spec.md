# MLFF adaptive training stop specification

Status: ADAPT-STOP1 implemented in mdstats 0.20.124a0; MLCV replay-degradation semantics corrected in mdstats 0.20.140a0.

## Scope

ADAPT-STOP1/MLCV-STOP1 converts lightweight validation metrics into training-control boundaries only. It does not perform authoritative full-validation acceptance, rank across runs, select a production model, or alter locked-test semantics. Learned-model inference uses the configured model dtype; mdstats-owned metric accumulation and policy arithmetic remain FP64.

## Current MLCV replay-degradation policy (schema v3)

Let the absolute target full-validation criterion be

`T_max = 0.030 eV/A = 30 meV/A` by default.

For positive target/replay score weights `w_T` and `w_R`, replay is constrained in **degradation space**:

`DeltaR_max = (w_T / w_R) * T_max`,

unless `[training].replay_degradation_budget_mev_per_a` explicitly overrides that derived budget.

For a candidate replay RMSE `R` and the frozen foundation replay RMSE `R0` on the exact same domain,

`DeltaR = R - R0`.

Negative `DeltaR` is preserved: fine-tuning that improves replay accuracy is beneficial evidence and is never clamped to zero.

At default 1:1 weighting, `DeltaR_max = 30 meV/A`. If `R0_full = 75.281 meV/A`, the diagnostic equivalent full absolute ceiling is `105.281 meV/A`; the foundation itself has `DeltaR = 0` and is feasible by definition.

### Matched foundation baselines

MLCV freezes two separate authenticated foundation replay baseline zero points before epoch 0:

- `R0_light = RMSE(foundation, R_light)` for STOP1/RANK1;
- `R0_full = RMSE(foundation, R_full)` for SELECT1/AGG1/FINAL1.

They are tied to the foundation model SHA-256 and exact replay-domain SHA/lineage. Cross-domain substitution is invalid. Exact restart reuses authenticated baseline evidence rather than recomputing it.

The historical foundation-feasibility condition `replay threshold < foundation RMSE` is **not** a current MLCV failure. The foundation evaluation establishes the zero point; it is not an acceptance gate.

## Lightweight stopping

The configurable target-success and replay-exhaustion factors remain training-control heuristics:

`T_stop = target_stop_fraction * T_max`,

`DeltaR_stop = replay_stop_multiplier * DeltaR_max`.

Generated defaults are `target_stop_fraction = 0.80` and `replay_stop_multiplier = 1.20`, therefore at the default 30 meV/A, 1:1 geometry:

| Boundary | Default |
|---|---:|
| target authoritative full criterion | 30 meV/A |
| target-success stop | 24 meV/A |
| replay degradation budget | 30 meV/A |
| replay-degradation exhaustion stop | 36 meV/A |
| hard epoch ceiling | configured `max_num_epochs` (default 30 epochs) |

The equivalent lightweight absolute replay exhaustion line is `R0_light + 36 meV/A`; it is **not** `1.20 * (R0_light + DeltaR_max)`.

Adaptive margin stops cannot fire before `minimum_epochs_before_adaptive_stop` completed epochs (default 3). `max_num_epochs` is an independent hard ceiling and may terminate a shorter configured budget. A complete finite lightweight checkpoint remains rankable even when it lies beyond either full-validation criterion; STOP1 does not apply full acceptance gates.

If target success and replay exhaustion become true on the same epoch, the terminal reason remains `target_success_and_replay_exhaustion`. The stop epoch is not automatically the selected checkpoint.

## Runtime integration

MLCV-STOP1 launches no per-epoch full replay inference. MACE evaluates `V_i_light`/`D_light` and `R_light` each evaluation interval. A one-time foundation `R_full` loader is used only when matched full baseline evidence is not already authenticated, then removed before the epoch loop.

The source-qualified training-loop integration keeps this order:

1. train the epoch;
2. evaluate lightweight target and TRUE_DFT replay monitors;
3. append MACE validation JSONL rows;
4. save the epoch checkpoint durably;
5. record STOP1 epoch evidence, including absolute replay RMSE, `R0_light`, and signed `DeltaR_light`;
6. break cleanly if a terminal condition applies; and
7. allow normal MACE final-model publication.

The parent does not kill MACE to implement a scientific stop, and a clean adaptive stop is not charged as a failed retry. Deterministic policy/schema/lineage/preflight failures are marked non-retryable inside one `train` invocation; transient process/GPU/I/O failures retain bounded retry.

## Durable evidence and exact restart

Each adaptive run owns `adaptive_training_stop.json`. Current v3 evidence binds the policy digest and records, at minimum:

- foundation model SHA-256;
- exact `R_light` and `R_full` artifact SHA-256 values;
- `R0_light` and `R0_full`;
- replay degradation budget and lightweight degradation stop boundary;
- diagnostic equivalent absolute replay ceilings;
- every completed epoch's target RMSE, absolute replay RMSE, foundation replay RMSE, and signed replay degradation;
- terminal epoch/reason and run outcome.

Re-recording an already durable epoch is idempotent only when the metrics are identical. If the parent is interrupted after terminal evidence is durable but before normal MACE finalization, `--restart_latest` skips the epoch loop. No extra training epoch is permitted.

## Current scoring relationship

STOP1 itself does not freeze the representative, but it persists the values consumed by MLCV-RANK1. Current MLCV lightweight scoring is

`S_light = (w_T*T_light + w_R*DeltaR_light)/(w_T+w_R)`.

Full acceptance/scoring occurs later in SELECT1 using the matched full baseline:

`DeltaR_full = R_full - R0_full`,

with component gates `T_full <= T_max` and `DeltaR_full <= DeltaR_max` before

`S_full = (w_T*T_full + w_R*DeltaR_full)/(w_T+w_R)`.

## Generated configuration

```toml
[training]
max_num_epochs = 30
target_stop_fraction = 0.80
replay_stop_multiplier = 1.20
minimum_epochs_before_adaptive_stop = 3
# Optional explicit override; otherwise derived from score weights and T_max.
# replay_degradation_budget_mev_per_a = 30.0

[acceptance]
maximum_target_force_rmse_ev_per_angstrom = 0.030

[evaluation]
target_score_weight = 1.0
replay_score_weight = 1.0
```

`allow_replay_threshold_below_foundation_baseline` is obsolete for new MLCV campaigns and is not generated. Historical payloads containing it remain parseable.

## Historical compatibility

Historical ADAPT/MLCV schemas preserve the semantics and digest that created them. In particular, v1/v2 absolute replay ceilings are never silently deserialized as replay-degradation budgets. Transitional 0.20.131a0-0.20.139a0 MLCV DATA8 authority is detected explicitly; current `train` refuses to reinterpret it and requires replay-dependent authority to be regenerated under the v3 policy while preserving historical evidence.

This compatibility rule is one-way: old evidence remains readable for provenance, while current MLCV STOP1/RANK1/SELECT1 authority requires the replay-degradation schemas.
