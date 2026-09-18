---
kind: semantic-definition-dependency-trace
protocol_version: 6.4.0
status: PROPOSED_D2_RENEWAL_R1_NONAUTHORITATIVE_TRACE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
parent_D1_ratified_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
parent_D1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
accepted_D2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
d2_candidate_blob: 894b2f5b6fe16ae483bb98dcc9af4910ccd3b311
scope:
  - docs/methods/mlff_numerical_algorithmic_method.md
---

# D2 replay/target renewal R1 dependency trace

This trace is a Protocol-6.4 review aid, not D2 authority.

## Direct D1 -> D2 edges

| D2 subject | Direct D1 prerequisites | Renewal relevance |
| --- | --- | --- |
| `D2.DEF.052` | `D1.DEF.022` | Replay evidence qualification is separated from checkpoint decision thresholds. |
| `D2.DEF.057` | `D1.DEF.022A` | Exact same-monitor signed replay degradation, 50/100 warning/hard predicates and strict exceedance. |
| `D2.DEF.058` | `D1.DEF.025-026` | Inclusive role checkpoint predicate; foundation defaults CV 75, production 50 meV/angstrom. |
| `D2.DEF.059` | `D1.DEF.024-026`; `D1.AX.009` | Default-force held-out 75 meV/angstrom, population/metric separation and all-position CV. |
| `D2.DEF.059A` | `D1.DEF.026` | Complete governed checkpoint universe and strict minimum target-RMSE representative; non-quality exact tie only. |
| `D2.DEF.059B` | `D1.DEF.027` | Strict target-RMSE `single_best_final_seed`; no ranking for `all_qualified_final_seeds`. |
| `D2.AX.004` | `D1.AX.010A` | Warning/hard/role-threshold/selection currentness split with TRAIN2 noninterference. |
| `D2.AX.005` | `D1.AX.010`; `D1.AX.010A` | Fresh final production, current-CV authorization and bounded reuse of historically fresh production. |
| `D2.DEF.060-060C` | `D1.AX.010A`; `D1.DEF.026` | Exact training-semantic reuse, measurement equivalence and immutable reassessment. |

## Challenge questions

Fresh independent D2 Review must challenge:

1. whether `RN64(R_c-R_0)` plus strict binary64 comparisons faithfully concretizes D1 without an implicit tolerance;
2. whether binary64 division by exact `1000` can collapse configured warning/hard thresholds and whether fail-closed handling is sufficient;
3. whether the training-versus-retention replay projections and same-monitor evaluator/provider/metric provenance are complete enough to prevent either false TRAIN2 invalidation or invalid replay degradation subtraction;
4. whether warning-only state is fully excluded from hard admissibility and ranking;
5. whether `(target RMSE, epoch, SHA)` and `(target RMSE, optimizer seed, SHA)` are total deterministic non-quality tie orders;
6. whether any practical-equivalence/bootstrap/secondary/maturity path can still alter foundation-P5 representative identity under the authority;
7. whether `theta_CV` is correctly outer-verdict-only while `tau_CV` can alter representative identity;
8. whether alternative outer metrics are protected from accidental 0.075 force-unit default migration;
9. whether training-semantic equivalence and measurement equivalence are sufficiently strong for historical reuse without weakening restart or allowing scalar-only provenance;
10. whether current-CV reauthorization permits reassessment without changing the numerical meaning of a genuinely fresh retained final-production trajectory.

P3 practical-equivalence semantics are outside the reopened surface and must remain unchanged.
