---
kind: semantic-definition-dependency-trace
protocol_version: 6.4.0
status: PROPOSED_R4_FINAL_NONAUTHORITATIVE_TRACE
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
scope:
  - workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md
  - workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R3_REPAIRED.md
supersedes_trace_drafts:
  - workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE.md
  - workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R2.md
  - workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R2_FINAL.md
  - workplans/active/MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE_R3_FINAL.md
---

# MLFF D1/D2 Protocol-6.4 R4 definition dependency trace — final candidate

## 1. Trace semantics and exact roots

This file is a bounded review/impact aid, not D1/D2 authority. Each stored edge has direction

```text
SUBJECT USES_DEFINITION -> DIRECT_PREREQUISITE
```

A prerequisite change is propagated by reverse traversal. Transitive edges, prose citations, call graphs, and evidence execution dependencies are omitted.

Exact root locators are those declared by the two scoped R3 candidate files. Short names `D1.IMP.*`, `D2.IMP.*`, `D1.SRC.*`, and `D2.SRC.*` resolve only through those basis-pinned registries. No free-text policy/provider/equality/tolerance endpoint is permitted.

Authority direction is acyclic: D1 objects depend only on D1 objects or exact D1 imports; D2 objects may depend on D1 objects and D2 objects/imports. No D1 object obtains meaning from its D2 concretization. The reviewed two-file graph has no intended strongly connected component.

## 2. D1 formal objects

| Subject | Direct prerequisites |
| --- | --- |
| `D1.DEF.001` | `D1.IMP.PHYSICAL` |
| `D1.DEF.002` | `D1.DEF.001`; `D1.IMP.PHYSICAL` |
| `D1.DEF.003` | `D1.DEF.002`; `D1.SRC.GENERAL§3.2` |
| `D1.AX.001` | `D1.DEF.003` |
| `D1.DEF.004` | `D1.DEF.001`; `D1.DEF.002`; `D1.IMP.PHYSICAL` |
| `D1.DEF.005` | `D1.DEF.001`; `D1.IMP.ROLES` |
| `D1.DEF.006` | `D1.DEF.001`; `D1.IMP.ROLES` |
| `D1.AX.002` | `D1.DEF.005`; `D1.DEF.006` |
| `D1.AX.003` | `D1.DEF.006` |
| `D1.DEF.007` | `D1.IMP.STAT` |
| `D1.DEF.008` | `D1.DEF.001`; `D1.DEF.002`; `D1.DEF.003`; `D1.DEF.005`; `D1.DEF.006`; `D1.AX.001`; `D1.AX.002`; `D1.IMP.P3` |
| `D1.DEF.009` | `D1.IMP.P3` |
| `D1.AX.004` | `D1.DEF.008`; `D1.DEF.009`; `D1.IMP.P3` |
| `D1.DEF.010` | `D1.DEF.008`; `D1.DEF.009`; `D1.IMP.P3` |
| `D1.DEF.011` | `D1.DEF.002`; `D1.DEF.009`; `D1.DEF.010`; `D1.IMP.P3` |
| `D1.DEF.012` | `D1.DEF.008`; `D1.IMP.ORDER` |
| `D1.DEF.013` | `D1.DEF.006`; `D1.DEF.008`; `D1.IMP.ORDER` |
| `D1.AX.005` | `D1.DEF.012`; `D1.DEF.013` |
| `D1.DEF.014` | `D1.DEF.005`; `D1.DEF.013`; `D1.IMP.ORDER` |
| `D1.DEF.015` | `D1.DEF.014`; `D1.IMP.ORDER` |
| `D1.DEF.016` | `D1.DEF.012`; `D1.DEF.014`; `D1.IMP.ORDER` |
| `D1.DEF.017` | `D1.DEF.002`; `D1.DEF.012`; `D1.DEF.015`; `D1.DEF.016`; `D1.IMP.ORDER` |
| `D1.AX.006` | `D1.DEF.011`; `D1.DEF.017`; `D1.IMP.P3`; `D1.IMP.ORDER` |
| `D1.AX.007` | `D1.DEF.012`; `D1.DEF.015`; `D1.DEF.016`; `D1.IMP.ORDER` |
| `D1.DEF.018` | `D1.DEF.009`; `D1.DEF.017`; `D1.IMP.P3`; `D1.IMP.ORDER` |
| `D1.AX.008` | `D1.DEF.011`; `D1.DEF.018`; `D1.IMP.P3` |
| `D1.DEF.019` | `D1.DEF.002`; `D1.IMP.P5` |
| `D1.DEF.020` | `D1.IMP.P5` |
| `D1.DEF.021` | `D1.DEF.020`; `D1.IMP.P5` |
| `D1.DEF.022` | `D1.DEF.020`; `D1.DEF.021`; `D1.IMP.P5` |
| `D1.DEF.023` | `D1.DEF.005`; `D1.DEF.006`; `D1.IMP.P5` |
| `D1.DEF.024` | `D1.DEF.005`; `D1.DEF.012`; `D1.DEF.023`; `D1.IMP.P5` |
| `D1.DEF.025` | `D1.DEF.023`; `D1.DEF.024`; `D1.IMP.P5` |
| `D1.AX.009` | `D1.DEF.024`; `D1.DEF.025`; `D1.IMP.P5` |
| `D1.AX.010` | `D1.DEF.012`; `D1.DEF.020`; `D1.DEF.022`; `D1.DEF.023`; `D1.DEF.025`; `D1.IMP.P5` |
| `D1.AX.011` | `D1.AX.008`; `D1.AX.010`; `D1.IMP.DOWNSTREAM` |

`D1.DEF.007` is deliberately bound to `D1.IMP.STAT` (general D1 §2.2), not the evidence-role import.

## 3. D2 formal objects

| Subject | Direct prerequisites |
| --- | --- |
| `D2.DEF.001` | `D1.DEF.001` |
| `D2.DEF.002` | `D2.DEF.001` |
| `D2.DEF.003` | `D1.DEF.001`; `D1.DEF.002`; `D1.DEF.004`; `D2.IMP.SOURCE` |
| `D2.DEF.004` | `D1.DEF.007`; `D2.IMP.STAT` |
| `D2.DEF.005` | `D2.DEF.004`; `D2.IMP.STAT` |
| `D2.DEF.006` | `D1.DEF.005`; `D2.DEF.005`; `D2.IMP.STAT` |
| `D2.DEF.007` | `D1.DEF.009`; `D2.IMP.SPLIT_EVAL` |
| `D2.DEF.008` | `D1.DEF.005`; `D1.DEF.008`; `D2.IMP.SPLIT_EVAL` |
| `D2.DEF.009` | `D1.DEF.008`; `D2.DEF.007`; `D2.DEF.008` |
| `D2.DEF.010` | `D1.DEF.010`; `D2.DEF.002`; `D2.DEF.009`; `D2.IMP.SPLIT_EVAL` |
| `D2.DEF.011` | `D1.AX.004`; `D1.DEF.012`; `D2.DEF.009`; `D2.DEF.010`; `D2.IMP.P3_PREP` |
| `D2.DEF.012` | `D1.DEF.013`; `D1.DEF.014`; `D2.IMP.ORDER` |
| `D2.DEF.013` | `D1.DEF.014`; `D2.DEF.012`; `D2.IMP.ORDER` |
| `D2.DEF.014` | `D2.DEF.013`; `D2.IMP.ORDER` |
| `D2.DEF.015` | `D2.DEF.012`; `D2.DEF.014` |
| `D2.DEF.016` | `D2.DEF.012`; `D2.DEF.015` |
| `D2.DEF.017` | `D2.DEF.013`; `D2.DEF.016`; `D2.IMP.ORDER` |
| `D2.DEF.018` | `D2.DEF.016`; `D2.DEF.017` |
| `D2.DEF.019` | `D2.DEF.013`; `D2.DEF.018` |
| `D2.DEF.020` | `D1.DEF.015`; `D2.DEF.019` |
| `D2.DEF.021` | `D1.DEF.015`; `D2.DEF.012`; `D2.DEF.014` |
| `D2.DEF.022` | `D1.DEF.016`; `D2.DEF.012`; `D2.DEF.021` |
| `D2.DEF.023` | `D1.DEF.016`; `D2.DEF.022` |
| `D2.DEF.024` | `D2.DEF.023` |
| `D2.DEF.025` | `D2.DEF.007`; `D2.DEF.012`; `D2.DEF.018`; `D2.DEF.023`; `D2.IMP.ORDER` |
| `D2.AX.001` | `D2.DEF.018`; `D2.DEF.023`; `D2.IMP.ORDER` |
| `D2.DEF.026` | `D1.DEF.012`; `D2.AX.001`; `D2.DEF.019`; `D2.DEF.024` |
| `D2.DEF.027` | `D2.DEF.013`; `D2.DEF.018`; `D2.DEF.019`; `D2.DEF.024`; `D2.DEF.026` |
| `D2.DEF.028` | `D2.DEF.018`; `D2.DEF.019`; `D2.DEF.026` |
| `D2.DEF.029` | `D1.DEF.015`; `D2.DEF.019` |
| `D2.DEF.030` | `D2.DEF.019`; `D2.DEF.024`; `D2.DEF.026`; `D2.DEF.027`; `D2.DEF.028`; `D2.DEF.029`; `D2.IMP.ORDER` |
| `D2.DEF.031` | `D2.DEF.024`; `D2.DEF.026`; `D2.DEF.027`; `D2.DEF.028`; `D2.DEF.029`; `D2.IMP.ORDER` |
| `D2.DEF.032` | `D2.DEF.026`; `D2.DEF.027`; `D2.DEF.028`; `D2.DEF.030`; `D2.DEF.031` |
| `D2.DEF.033` | `D2.DEF.027`; `D2.DEF.031`; `D2.DEF.032`; `D2.IMP.ORDER` |
| `D2.DEF.034` | `D1.AX.007`; `D2.DEF.019`; `D2.DEF.024`; `D2.DEF.026`; `D2.IMP.ORDER` |
| `D2.DEF.035` | `D2.DEF.019`; `D2.DEF.026`; `D2.DEF.027`; `D2.DEF.028`; `D2.DEF.034`; `D2.IMP.ORDER` |
| `D2.DEF.036` | `D2.DEF.013`; `D2.DEF.019`; `D2.DEF.024`; `D2.DEF.026`; `D2.DEF.034`; `D2.DEF.035` |
| `D2.DEF.037` | `D1.AX.007`; `D2.DEF.032`; `D2.DEF.033`; `D2.DEF.034`; `D2.DEF.035`; `D2.DEF.036`; `D2.IMP.ORDER` |
| `D2.AX.002` | `D2.DEF.026`; `D2.DEF.032`; `D2.DEF.033`; `D2.DEF.037` |
| `D2.DEF.038` | `D1.DEF.017`; `D2.AX.001`; `D2.DEF.016`; `D2.DEF.017`; `D2.DEF.018`; `D2.DEF.019`; `D2.DEF.020`; `D2.DEF.021`; `D2.DEF.024` |
| `D2.DEF.039` | `D1.DEF.018`; `D2.DEF.007`; `D2.DEF.038` |
| `D2.DEF.040` | `D1.DEF.002`; `D1.DEF.020`; `D2.IMP.E0` |
| `D2.DEF.041` | `D1.DEF.020`; `D2.DEF.040`; `D2.IMP.E0` |
| `D2.DEF.042` | `D1.DEF.020`; `D2.DEF.040`; `D2.DEF.041`; `D2.IMP.E0` |
| `D2.DEF.043` | `D1.DEF.019`; `D2.IMP.OBJECTIVE` |
| `D2.DEF.044` | `D1.DEF.019`; `D2.DEF.043`; `D2.IMP.OBJECTIVE` |
| `D2.DEF.045` | `D1.DEF.019`; `D2.DEF.043`; `D2.DEF.044`; `D2.IMP.OBJECTIVE` |
| `D2.DEF.046` | `D1.AX.004`; `D2.DEF.007`; `D2.DEF.011`; `D2.IMP.P3` |
| `D2.DEF.047` | `D1.DEF.011`; `D2.DEF.007`; `D2.IMP.P3` |
| `D2.DEF.048` | `D1.DEF.011`; `D2.DEF.047`; `D2.IMP.P3` |
| `D2.DEF.049` | `D1.DEF.018`; `D2.DEF.007`; `D2.DEF.039`; `D2.DEF.047`; `D2.DEF.048`; `D2.IMP.P3` |
| `D2.DEF.050` | `D1.AX.008`; `D1.DEF.011`; `D2.DEF.047`; `D2.DEF.048`; `D2.DEF.049`; `D2.IMP.P3` |
| `D2.AX.003` | `D2.DEF.007`; `D2.DEF.011`; `D2.DEF.046`; `D2.IMP.P3` |
| `D2.DEF.051` | `D1.DEF.020`; `D1.DEF.021`; `D1.DEF.022`; `D2.IMP.REPLAY` |
| `D2.DEF.051A` | `D1.DEF.020`; `D2.DEF.041`; `D2.IMP.E0_HEADS` |
| `D2.DEF.052` | `D1.DEF.022`; `D2.DEF.051`; `D2.DEF.051A`; `D2.IMP.REPLAY` |
| `D2.DEF.053` | `D1.DEF.019`; `D1.DEF.022`; `D2.DEF.051`; `D2.DEF.052`; `D2.IMP.P5_EXPOSURE` |
| `D2.DEF.054` | `D1.DEF.023`; `D2.IMP.MONITOR` |
| `D2.DEF.055` | `D2.DEF.054`; `D2.IMP.MONITOR` |
| `D2.DEF.056` | `D1.DEF.005`; `D1.DEF.024`; `D2.IMP.CV` |
| `D2.DEF.057` | `D1.DEF.022`; `D2.DEF.051`; `D2.DEF.052`; `D2.IMP.CV` |
| `D2.DEF.058` | `D1.DEF.023`; `D1.DEF.025`; `D2.DEF.055`; `D2.DEF.057`; `D2.IMP.CV` |
| `D2.DEF.059` | `D1.AX.009`; `D1.DEF.024`; `D1.DEF.025`; `D2.DEF.056`; `D2.DEF.058`; `D2.IMP.CV` |
| `D2.AX.004` | `D1.DEF.025`; `D2.DEF.052`; `D2.DEF.057`; `D2.DEF.058`; `D2.DEF.059`; `D2.IMP.CV` |
| `D2.AX.005` | `D1.AX.010`; `D2.DEF.041`; `D2.DEF.042`; `D2.DEF.051`; `D2.DEF.051A`; `D2.DEF.052`; `D2.DEF.053`; `D2.DEF.055`; `D2.DEF.057`; `D2.DEF.058`; `D2.IMP.PRODUCTION` |
| `D2.DEF.060` | `D1.DEF.009`; `D1.DEF.012`; `D1.DEF.020`; `D1.DEF.024`; `D1.DEF.025`; `D2.AX.002`; `D2.AX.003`; `D2.DEF.007`; `D2.DEF.011`; `D2.DEF.012`; `D2.DEF.038`; `D2.DEF.041`; `D2.DEF.045`; `D2.DEF.052`; `D2.DEF.053`; `D2.DEF.058`; `D2.DEF.059`; `D2.IMP.CV`; `D2.IMP.PRODUCTION` |
| `D2.DEF.060A` | `D2.SRC.GENERAL`; `D2.SRC.ORDER`; `D2.DEF.018`; `D2.DEF.020`; `D2.DEF.021`; `D2.DEF.029`; `D2.DEF.030`; `D2.DEF.033`; `D2.DEF.036`; `D2.DEF.038`; `D2.DEF.058`; `D2.DEF.059` |
| `D2.DEF.061` | `D2.DEF.060A` |
| `D2.AX.006` | `D2.DEF.061` |
| `D2.DEF.062` | `D2.DEF.003`; `D2.DEF.004`; `D2.DEF.005`; `D2.DEF.006`; `D2.DEF.007`; `D2.DEF.009`; `D2.DEF.012`; `D2.DEF.013`; `D2.DEF.014`; `D2.DEF.017`; `D2.DEF.018`; `D2.DEF.019`; `D2.DEF.020`; `D2.DEF.023`; `D2.DEF.025`; `D2.DEF.033`; `D2.DEF.037`; `D2.DEF.038`; `D2.DEF.039`; `D2.DEF.041`; `D2.DEF.042`; `D2.DEF.045`; `D2.DEF.047`; `D2.DEF.049`; `D2.DEF.051`; `D2.DEF.051A`; `D2.DEF.052`; `D2.DEF.053`; `D2.DEF.054`; `D2.DEF.056`; `D2.DEF.057`; `D2.DEF.058`; `D2.DEF.059`; `D2.DEF.060`; `D2.DEF.060A`; `D2.DEF.061`; `D2.IMP.PRODUCTION` |

The `D2.DEF.062` row enumerates only definitions that directly contribute one of the typed failure members; it is not a global dependency shortcut.

## 4. R4 direct-edge closure audit

R3 independent review falsified the prior bounded-completeness claim using `D2.DEF.062`. The R4 author-side repair therefore re-walked every one of the 106 formal D1/D2 subjects rather than patching only that witness. This audit is repair evidence, not acceptance authority.

The re-walk added direct edges where a local definition is consumed in the subject itself rather than only through a transitive descendant. Material repairs include:

- selector decision/oracle closure: `D2.DEF.030-032` now bind covered mass/state and the exact gain/diversity definitions they directly consume;
- repair closure: `D2.DEF.035-037` and `D2.AX.002` now bind current coverage/state, exact representative weights, full-forward/lazy continuation and the Phase-B rebase they directly consume;
- independent qualification: `D2.DEF.038` now binds the metric/radius/adjacency definitions explicitly named by its `D2.DEF.016-020` recomputation contract;
- P3 reducer/restart: `D2.DEF.049-050` and `D2.AX.003` now bind configured positions and complete-seed score owners directly;
- replay/production: `D2.DEF.051A` binds the target-head mapping it explicitly distinguishes, and `D2.AX.005` binds the true-reference retention constraint it explicitly retains;
- authenticated continuation: `D2.DEF.060` now binds the population/membership, policy, foundation, objective/exposure, selector/reference, CV-role and restart owners needed to prove the exact continuation boundary;
- typed failure: `D2.DEF.062` now reaches the previously omitted P5 objective, P3 finite-outcome/reducer, P5 exposure and checkpoint-admissibility owners, and the equivalence registry used to classify materially different execution.

Two challenged rows intentionally remain otherwise unchanged:

1. `D2.AX.004` already names every local object that can directly change its selective-currentness partition: role thresholds, replay qualification/currentness, shared checkpoint constraint, role-effective predicate and all-position CV acceptance.
2. `D2.DEF.060A` selects the **comparison relation**, not the value-generating definitions being compared. Exact-identity/value owners are operands of that relation and therefore are not direct prerequisites merely because their output values can change. All locally owned nonzero tolerances/guards that can change relation selection remain explicit direct prerequisites, together with the two exact basis-pinned source roots. This preserves the distinction that R2 required between an exact relation registry and a generic “each object's equality/tolerance” endpoint.

Mechanical author checks on the repaired graph establish only structural properties: all 106 candidate subjects occur exactly once; every prerequisite resolves to a candidate object or basis-pinned import; and the object-to-object graph is acyclic. Fresh review must still challenge semantic completeness and reverse-impact adequacy.


## 5. High-risk D2 -> D1 concretization edges

```text
D2.DEF.004 -> D1.DEF.007
D2.DEF.009 -> D1.DEF.008
D2.DEF.010 -> D1.DEF.010
D2.DEF.011 -> D1.AX.004
D2.DEF.012 -> D1.DEF.014
D2.DEF.020 -> D1.DEF.015
D2.DEF.021 -> D1.DEF.015
D2.DEF.022 -> D1.DEF.016
D2.DEF.038 -> D1.DEF.017
D2.DEF.039 -> D1.DEF.018
D2.DEF.041 -> D1.DEF.020
D2.DEF.042 -> D1.DEF.020
D2.DEF.045 -> D1.DEF.019
D2.DEF.047 -> D1.DEF.011
D2.DEF.049 -> D1.DEF.018
D2.DEF.050 -> D1.AX.008
D2.DEF.051 -> D1.DEF.021
D2.DEF.051A -> D1.DEF.020
D2.DEF.052 -> D1.DEF.022
D2.DEF.055 -> D1.DEF.023
D2.DEF.056 -> D1.DEF.024
D2.DEF.058 -> D1.DEF.025
D2.DEF.059 -> D1.AX.009
D2.AX.005 -> D1.AX.010
```

These are D2 subject -> D1 prerequisite edges and preserve abstraction direction. An attempted D2 change that cannot preserve its D1 prerequisite is an upward D1 Challenge.

## 6. Parameter/source impact anchors

| Prerequisite | Immediate consumers | Binding class/effect |
| --- | --- | --- |
| target-order `0.95` | `D1.DEF.015`; `D2.DEF.020`; `D2.DEF.029`; `D2.DEF.038` | fixed method coordinate |
| extent `(0.01,0.99)` | `D1.DEF.015`; `D2.DEF.014`; `D2.DEF.021`; obligations | fixed method coordinate |
| one-time family normalization / direct `q` comparison | `D2.DEF.013`; `D2.DEF.014`; quantile/coverage descendants | fixed numerical method |
| MVQUAL tolerance `1e-12` | `D2.DEF.020`; `D2.DEF.038` | fixed numerical coordinate |
| MVSEL2 tolerance `1e-14` | `D2.DEF.029-037` | fixed numerical coordinate |
| candidate/evaluation/fidelity/seed values | `D1.DEF.009`; `D2.DEF.007`; split/funnel/repair | configurable family under fixed structural domain |
| practical `epsilon` | `D1.DEF.011`; `D2.DEF.048`; `D2.DEF.050` | configurable response-unit family |
| replay label mode | `D1.DEF.021`; `D1.DEF.022`; `D2.DEF.051-053` | configurable with true-reference default under validity rule |
| replay qualification identity/state | `D1.DEF.022`; `D2.DEF.052`; `D2.DEF.057`; `D2.AX.004-005` | derived/currentness-bearing lineage coordinate |
| replay-head E0 | `D1.DEF.020`; `D2.DEF.051A`; `D2.DEF.052`; `D2.AX.005` | derived exact selected-head mapping |
| monitor `256`, seed `161803` | `D1.DEF.023`; `D2.DEF.054-055` | fixed method/numerical coordinates |
| CV `K` | `D1.DEF.024`; `D2.DEF.056`; `D2.DEF.059` | configurable with generated default 3 |
| `tau_CV`, `theta_CV`, `tau_prod` | `D1.DEF.025`; `D2.DEF.058-059`; `D2.AX.004-005` | independently configurable with generated defaults |
| equivalence relation registry | `D2.DEF.060A`; `D2.DEF.061`; `D2.AX.006` | exact/source-owned comparison semantics |

## 7. Topological and reverse-impact review order

Review source availability and definitions in this order: D1 exact imports -> D1 foundational/statistical/roles -> target-size -> target-order -> P5/replay -> monitor/CV/production; then D2 exact imports -> numerical/statistical primitives -> split/evaluation/common preparation -> TargetCoverage -> obligations -> selector -> repair -> MVQUAL/admission -> E0 -> P5 objective -> P3 reducer -> replay/E0/exposure -> monitor/folds/checkpoint/production -> continuation/equivalence/failure.

Reverse-impact tests begin at every fixed/configurable/derived currentness parameter row above and exact import roots. The declared graph is intended to be acyclic; a discovered SCC or unresolved endpoint is a candidate blocker rather than something resolved by file order.

## 8. Completion rule

This trace may accompany R4 only if independent review confirms: every material formal object in the two scoped R3 candidate files appears exactly once; every prerequisite resolves to an exact candidate object or basis-pinned import; no material direct edge is missing; no edge inverts D1/D2 ownership; reverse traversal reaches all materially affected descendants; and no completeness claim escapes the declared two-file scope.