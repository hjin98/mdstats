# mdstats 0.20.140a0 patch notes

## MLCV replay-degradation semantic correction

Conventional-CV MLCV now treats target force RMSE as an absolute criterion and replay as signed degradation relative to the frozen foundation model on the exact same replay domain.

- MLCV-STOP1 freezes authenticated, domain-matched `R0_light` and `R0_full` foundation baselines. The foundation defines zero degradation and is no longer rejected because its raw TRUE_DFT replay RMSE exceeds the derived retention budget.
- The replay budget is `DeltaR_max = (w_T / w_R) T_max` unless `training.replay_degradation_budget_mev_per_a` explicitly overrides it. The lightweight exhaustion margin is `replay_stop_multiplier * DeltaR_max`.
- MLCV-RANK1 uses signed `R_light - R0_light`; negative degradation is retained as replay improvement.
- MLCV-SELECT1 gates component-wise on `T_full <= T_max` and `R_full - R0_full <= DeltaR_max`, while persisting raw replay RMSE, foundation baseline, degradation, budget, and the human-readable absolute ceiling.
- MLCV-AGG1 and MLCV-FINAL1 propagate degradation-aware combined scores and separate raw/degradation summaries.
- Current replay-dependent schemas and MLCV lifecycle/freeze authority are versioned. Historical absolute-RMSE evidence remains deserializable with its historical payload/digest and is never silently reinterpreted.
- Deterministic policy/authority/preflight failures are classified non-retryable so the training scheduler does not launch a redundant second MACE attempt.
- Per-run diagnostics now distinguish absolute replay quality, the frozen foundation baseline, and signed replay degradation.

Transitional 0.20.131a0--0.20.139a0 MLCV evidence derived under absolute replay semantics is stale from the earliest replay-dependent gate. Raw authenticated validation measurements remain reusable only where their exact checkpoint/domain identity is still valid.
