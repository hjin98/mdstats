---
kind: semantic-definition-dependency-trace
protocol_version: 6.4.0
status: PROPOSED_D1_AMENDMENT_R3_NONAUTHORITATIVE_TRACE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
prior_r2_reviewed_candidate: 2549dee709fb8bb383341ee3aebca7c71973a903
prior_r2_review_commit: 8bf25f37e74667ff897e938a9b17830ea9fee225
d1_candidate_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
scope:
  - docs/methods/mlff_scientific_method.md
---

# D1 replay/target renewal R3 dependency trace

This trace is a Protocol-6.4 review aid, not D1 authority. It preserves the R2 direct-dependency closure and adds the post-R2 stakeholder amendment to the CV threshold family plus the non-semantic UniversalLoss coefficient clarification.

## Direct edges

| Subject | Direct prerequisites | R3 relevance |
| --- | --- | --- |
| `D1.DEF.019` | `D1.IMP.P5` | Clarifies that `1:10:1` is the global E/F/S property-loss coefficient tuple of the accepted foundation-P5 robust objective, not target/replay balance or per-frame weighting. The native `UniversalLoss` class remains a D2/D4 realization rather than the D1 coordinate. No coefficient changed. |
| `D1.DEF.022` | `D1.DEF.020`; `D1.DEF.021`; `D1.IMP.P5` | Unchanged R2 replay-lineage semantics. |
| `D1.DEF.022A` | `D1.DEF.020`; `D1.DEF.022`; `D1.IMP.P5` | Unchanged R2 replay-degradation semantics. |
| `D1.DEF.025` | `D1.DEF.023`; `D1.DEF.024`; `D1.IMP.P5` | Material R3 amendment: generated/default role thresholds become `75/75/50 meV/angstrom`. |
| `D1.DEF.026` | `D1.DEF.022A`; `D1.DEF.023`; `D1.DEF.025`; `D1.IMP.P5` | CV hard-admissible set now consumes the amended 75-meV checkpoint ceiling. |
| `D1.DEF.027` | `D1.DEF.026`; `D1.IMP.P5` | Publication ordering unchanged. |
| `D1.AX.009` | `D1.DEF.024`; `D1.DEF.025`; `D1.DEF.026`; `D1.IMP.P5` | CV acceptance consumes the amended checkpoint and held-out ceilings. |
| `D1.AX.010` | `D1.DEF.012`; `D1.DEF.020`; `D1.DEF.022`; `D1.DEF.022A`; `D1.DEF.023`; `D1.DEF.025`; `D1.DEF.026`; `D1.IMP.P5` | Production remains 50 meV/angstrom and current-CV authorization remains required. |
| `D1.AX.010A` | `D1.DEF.022A`; `D1.DEF.025`; `D1.DEF.026`; `D1.DEF.027`; `D1.AX.009`; `D1.AX.010` | `tau_CV` changes CV hard assessment/representative; `theta_CV` changes outer verdict only; neither changes TRAIN2. Dependent production authorization stales in either case. |

## R3 review questions

Fresh review must challenge:

1. whether `tau_CV=75 meV/angstrom` is appropriately more permissive than production `tau_prod=50 meV/angstrom` without making common-monitor CV competence vacuous, given that historical `45` was itself a stakeholder calibration rather than an externally proved boundary;
2. whether `theta_CV=75 meV/angstrom` remains meaningful held-out force-RMSE authorization across every required fold/seed;
3. whether making both CV ceilings looser can authorize a method whose fresh production cannot meet the 50-meV target ceiling, and whether the explicit meaning 'CV authorizes an attempt but does not guarantee production success' is scientifically coherent;
4. whether `tau_CV` and `theta_CV` have correctly separated currentness (`tau_CV` may change representative; `theta_CV` may not) and both remain assessment-only with respect to TRAIN2;
5. whether the `1:10:1` clarification faithfully represents the accepted D2 relation `L_{P5}=L_E+10L_F+L_S` without introducing target/replay, per-configuration or per-frame weighting semantics;
6. whether scratch, P3 and downstream qualification remain unchanged.

No R2 PASS conclusion is inherited for the amended threshold values.
