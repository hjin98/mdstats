---
kind: semantic-definition-dependency-trace
protocol_version: 6.4.0
status: PROPOSED_R2_NONAUTHORITATIVE_TRACE
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
scope:
  - workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R2_REPAIRED.md
  - workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R2_REVIEW_CANDIDATE.md
---

# MLFF D1/D2 Protocol-6.4 R2 definition dependency trace

## 1. Trace semantics and exact roots

This file is a bounded review/impact aid, not D1/D2 authority. Each stored edge has direction

```text
SUBJECT USES_DEFINITION -> DIRECT_PREREQUISITE
```

A prerequisite change is propagated by reverse traversal. Transitive edges, prose citations, call graphs, and evidence execution dependencies are omitted.

Exact root locators are those declared by the two scoped candidate files. In this trace the short root names `D1.IMP.*`, `D2.IMP.*`, `D1.SRC.*`, and `D2.SRC.*` resolve only through those exact basis-pinned registries. There are no floating “accepted policy/provider” endpoints.

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
| `D1.DEF.007` | `D1.IMP.ROLES`; `D2.DEF.004`; `D2.DEF.005` |
| `D1.DEF.008` | `D1.DEF.001`; `D1.DEF.002`; `D1.DEF.003`; `D1.DEF.005`; `D1.DEF.006`; `D1.AX.001`; `D1.AX.002` |
| `D1.DEF.009` | `D1.IMP.P3` |
| `D1.AX.004` | `D1.DEF.008`; `D1.DEF.009`; `D1.DEF.012`; `D2.DEF.011` |
| `D1.DEF.010` | `D1.DEF.008`; `D1.DEF.009`; `D2.DEF.010` |
| `D1.DEF.011` | `D1.DEF.002`; `D1.DEF.010`; `D1.DEF.009` |
| `D1.DEF.012` | `D1.DEF.008`; `D1.IMP.ORDER` |
| `D1.DEF.013` | `D1.DEF.008`; `D1.DEF.006`; `D1.IMP.ORDER` |
| `D1.AX.005` | `D1.DEF.012`; `D1.DEF.013` |
| `D1.DEF.014` | `D1.DEF.005`; `D1.DEF.013`; `D1.IMP.ORDER` |
| `D1.DEF.015` | `D1.DEF.014`; `D2.DEF.014`; `D2.DEF.018`; `D2.DEF.019` |
| `D1.DEF.016` | `D1.DEF.012`; `D1.DEF.014`; `D1.IMP.ORDER` |
| `D1.DEF.017` | `D1.DEF.012`; `D1.DEF.015`; `D1.DEF.016`; `D1.DEF.002` |
| `D1.AX.006` | `D1.DEF.017`; `D1.DEF.011`; `D2.DEF.048` |
| `D1.AX.007` | `D1.DEF.012`; `D1.DEF.015`; `D1.DEF.016`; `D2.DEF.036`; `D2.DEF.037` |
| `D1.DEF.018` | `D1.DEF.009`; `D1.DEF.017`; `D2.DEF.039` |
| `D1.AX.008` | `D1.DEF.018`; `D1.DEF.011`; `D2.DEF.048`; `D2.DEF.049`; `D2.DEF.050` |
| `D1.DEF.019` | `D1.DEF.002`; `D1.IMP.P5`; `D2.DEF.043`; `D2.DEF.044`; `D2.DEF.045` |
| `D1.DEF.020` | `D1.IMP.P5`; `D2.IMP.E0` |
| `D1.DEF.021` | `D1.DEF.020`; `D1.IMP.P5` |
| `D1.DEF.022` | `D1.DEF.020`; `D1.DEF.021`; `D1.IMP.P5` |
| `D1.DEF.023` | `D1.DEF.005`; `D1.DEF.006`; `D1.IMP.P5`; `D2.DEF.054`; `D2.DEF.055` |
| `D1.DEF.024` | `D1.DEF.005`; `D1.DEF.012`; `D1.DEF.023`; `D1.IMP.P5` |
| `D1.DEF.025` | `D1.DEF.023`; `D1.DEF.024`; `D1.IMP.P5` |
| `D1.AX.009` | `D1.DEF.024`; `D1.DEF.025`; `D2.DEF.058`; `D2.DEF.059` |
| `D1.AX.010` | `D1.DEF.012`; `D1.DEF.020`; `D1.DEF.022`; `D1.DEF.023`; `D1.DEF.025`; `D2.AX.005` |
| `D1.AX.011` | `D1.AX.008`; `D1.AX.010`; `D1.IMP.DOWNSTREAM` |

## 3. D2 formal objects

| Subject | Direct prerequisites |
| --- | --- |
| `D2.DEF.001` | `D1.DEF.001` |
| `D2.DEF.002` | `D2.DEF.001` |
| `D2.DEF.003` | `D2.IMP.SOURCE`; `D1.DEF.001`; `D1.DEF.002`; `D1.DEF.004` |
| `D2.DEF.004` | `D1.DEF.007`; `D2.IMP.STAT` |
| `D2.DEF.005` | `D2.DEF.004`; `D2.IMP.STAT` |
| `D2.DEF.006` | `D1.DEF.005`; `D2.DEF.005`; `D2.IMP.STAT` |
| `D2.DEF.007` | `D1.DEF.009`; `D2.IMP.SPLIT_EVAL` |
| `D2.DEF.008` | `D1.DEF.005`; `D1.DEF.008`; `D2.IMP.SPLIT_EVAL` |
| `D2.DEF.009` | `D2.DEF.007`; `D2.DEF.008`; `D1.DEF.008` |
| `D2.DEF.010` | `D2.DEF.002`; `D2.DEF.009`; `D1.DEF.010`; `D2.IMP.SPLIT_EVAL` |
| `D2.DEF.011` | `D1.AX.004`; `D1.DEF.012`; `D2.DEF.009`; `D2.DEF.010`; `D2.IMP.P3_PREP` |
| `D2.DEF.012` | `D1.DEF.013`; `D1.DEF.014`; `D2.IMP.ORDER` |
| `D2.DEF.013` | `D1.DEF.014`; `D2.DEF.012`; `D2.IMP.ORDER` |
| `D2.DEF.014` | `D2.DEF.013`; `D2.IMP.ORDER` |
| `D2.DEF.015` | `D2.DEF.014`; `D2.DEF.012` |
| `D2.DEF.016` | `D2.DEF.015`; `D2.DEF.012` |
| `D2.DEF.017` | `D2.DEF.013`; `D2.DEF.016`; `D2.IMP.ORDER` |
| `D2.DEF.018` | `D2.DEF.016`; `D2.DEF.017` |
| `D2.DEF.019` | `D2.DEF.013`; `D2.DEF.018` |
| `D2.DEF.020` | `D1.DEF.015`; `D2.DEF.019` |
| `D2.DEF.021` | `D1.DEF.015`; `D2.DEF.014`; `D2.DEF.012` |
| `D2.DEF.022` | `D1.DEF.016`; `D2.DEF.012`; `D2.DEF.021` |
| `D2.DEF.023` | `D2.DEF.022`; `D1.DEF.016` |
| `D2.DEF.024` | `D2.DEF.023` |
| `D2.DEF.025` | `D2.DEF.007`; `D2.DEF.012`; `D2.DEF.018`; `D2.DEF.023`; `D2.IMP.ORDER` |
| `D2.AX.001` | `D2.DEF.018`; `D2.DEF.023`; `D2.IMP.ORDER` |
| `D2.DEF.026` | `D2.DEF.019`; `D2.DEF.024`; `D1.DEF.012`; `D2.AX.001` |
| `D2.DEF.027` | `D2.DEF.013`; `D2.DEF.018`; `D2.DEF.019`; `D2.DEF.024`; `D2.DEF.026` |
| `D2.DEF.028` | `D2.DEF.018`; `D2.DEF.019`; `D2.DEF.026` |
| `D2.DEF.029` | `D1.DEF.015`; `D2.DEF.019` |
| `D2.DEF.030` | `D2.DEF.024`; `D2.DEF.027`; `D2.DEF.028`; `D2.DEF.029`; `D2.IMP.ORDER` |
| `D2.DEF.031` | `D2.DEF.027`; `D2.DEF.028`; `D2.DEF.029`; `D2.IMP.ORDER` |
| `D2.DEF.032` | `D2.DEF.026`; `D2.DEF.030`; `D2.DEF.031` |
| `D2.DEF.033` | `D2.DEF.027`; `D2.DEF.031`; `D2.DEF.032`; `D2.IMP.ORDER` |
| `D2.DEF.034` | `D1.AX.007`; `D2.DEF.019`; `D2.DEF.024`; `D2.DEF.026`; `D2.IMP.ORDER` |
| `D2.DEF.035` | `D2.DEF.027`; `D2.DEF.028`; `D2.DEF.034`; `D2.IMP.ORDER` |
| `D2.DEF.036` | `D2.DEF.019`; `D2.DEF.024`; `D2.DEF.026`; `D2.DEF.034`; `D2.DEF.035` |
| `D2.DEF.037` | `D1.AX.007`; `D2.DEF.034`; `D2.DEF.035`; `D2.DEF.036`; `D2.IMP.ORDER` |
| `D2.AX.002` | `D2.DEF.026`; `D2.DEF.032`; `D2.DEF.037` |
| `D2.DEF.038` | `D1.DEF.017`; `D2.DEF.019`; `D2.DEF.020`; `D2.DEF.021`; `D2.DEF.024`; `D2.AX.001` |
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
| `D2.DEF.049` | `D1.DEF.018`; `D2.DEF.039`; `D2.DEF.048`; `D2.IMP.P3` |
| `D2.DEF.050` | `D1.AX.008`; `D2.DEF.048`; `D2.DEF.049`; `D2.IMP.P3` |
| `D2.AX.003` | `D2.DEF.011`; `D2.DEF.046`; `D2.IMP.P3` |
| `D2.DEF.051` | `D1.DEF.020`; `D1.DEF.021`; `D1.DEF.022`; `D2.IMP.REPLAY` |
| `D2.DEF.052` | `D1.DEF.022`; `D2.DEF.051`; `D2.IMP.REPLAY` |
| `D2.DEF.053` | `D1.DEF.019`; `D1.DEF.022`; `D2.DEF.051`; `D2.DEF.052`; `D2.IMP.P5_EXPOSURE` |
| `D2.DEF.054` | `D1.DEF.023`; `D2.IMP.MONITOR` |
| `D2.DEF.055` | `D2.DEF.054`; `D2.IMP.MONITOR` |
| `D2.DEF.056` | `D1.DEF.005`; `D1.DEF.024`; `D2.IMP.CV` |
| `D2.DEF.057` | `D1.DEF.022`; `D2.DEF.051`; `D2.IMP.CV` |
| `D2.DEF.058` | `D1.DEF.023`; `D1.DEF.025`; `D2.DEF.055`; `D2.DEF.057`; `D2.IMP.CV` |
| `D2.DEF.059` | `D1.DEF.024`; `D1.DEF.025`; `D1.AX.009`; `D2.DEF.056`; `D2.DEF.058`; `D2.IMP.CV` |
| `D2.AX.004` | `D1.DEF.025`; `D2.DEF.057`; `D2.DEF.058`; `D2.DEF.059`; `D2.IMP.CV` |
| `D2.AX.005` | `D1.AX.010`; `D2.DEF.041`; `D2.DEF.042`; `D2.DEF.051`; `D2.DEF.053`; `D2.DEF.055`; `D2.DEF.058`; `D2.IMP.PRODUCTION` |
| `D2.DEF.060` | `D2.AX.002`; `D2.AX.003`; `D2.DEF.052`; `D2.DEF.053`; `D2.IMP.PRODUCTION` |
| `D2.DEF.061` | `D2.SRC.GENERAL`; `D2.SRC.ORDER`; each object's owned equality/tolerance relation |
| `D2.AX.006` | `D2.DEF.061` |
| `D2.DEF.062` | `D2.DEF.003-061`; `D2.IMP.SOURCE`; `D2.IMP.STAT`; `D2.IMP.ORDER`; `D2.IMP.PRODUCTION` |

`D2.DEF.062 -> D2.DEF.003-061` is a declared aggregate direct dependency of the typed failure union on the individual failure-generating definitions; it is not shorthand for a hidden global dependency claim.

## 4. High-risk cross-domain concretization edges

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
D2.DEF.052 -> D1.DEF.022
D2.DEF.055 -> D1.DEF.023
D2.DEF.056 -> D1.DEF.024
D2.DEF.058 -> D1.DEF.025
D2.DEF.059 -> D1.AX.009
D2.AX.005 -> D1.AX.010
```

Any proposed D2 mutation unable to preserve its D1 prerequisite is an upward D1 Challenge.

## 5. Parameter/source impact anchors

| Prerequisite | Immediate consumers | Binding class/effect |
| --- | --- | --- |
| target-order `0.95` | `D1.DEF.015`; `D2.DEF.020`; `D2.DEF.029`; `D2.DEF.038` | fixed method coordinate |
| extent `(0.01,0.99)` | `D1.DEF.015`; `D2.DEF.014`; `D2.DEF.021`; obligations | fixed method coordinate |
| one-time family normalization | `D2.DEF.013`; `D2.DEF.014`; all quantile/coverage descendants | fixed method coordinate |
| MVQUAL tolerance `1e-12` | `D2.DEF.020`; `D2.DEF.038` | fixed numerical coordinate |
| MVSEL2 tolerance `1e-14` | `D2.DEF.029-037` | fixed numerical coordinate |
| candidate/evaluation/fidelity/seed values | `D1.DEF.009`; `D2.DEF.007`; split/funnel/repair | configurable family under fixed structural domain |
| practical `epsilon` | `D1.DEF.011`; `D2.DEF.048`; `D2.DEF.050` | configurable response-unit family |
| replay label mode | `D1.DEF.021`; `D1.DEF.022`; `D2.DEF.051-053` | configurable with true-reference default under validity rule |
| monitor `256`, seed `161803` | `D1.DEF.023`; `D2.DEF.054-055` | fixed method/numerical coordinates |
| CV `K` | `D1.DEF.024`; `D2.DEF.056`; `D2.DEF.059` | configurable with generated default 3 |
| `tau_CV`, `theta_CV`, `tau_prod` | `D1.DEF.025`; `D2.DEF.058-059`; `D2.AX.004-005` | independently configurable with generated defaults |

## 6. Definition-order and reverse-impact review order

A competent review should traverse source availability and then definitions in this order: D1 exact imports -> D1 foundational/roles -> target-size -> target-order -> P5/replay -> monitor/CV/production; then D2 exact imports -> numeric/statistical primitives -> split/evaluation/common preparation -> TargetCoverage -> obligations -> selector -> repair -> MVQUAL/admission -> E0 -> P5 objective -> P3 reducer -> replay/exposure -> monitor/folds/checkpoint/production -> continuation/equivalence/failure.

Reverse-impact tests should begin at every fixed/configurable parameter row above and at exact import roots. No semantic cycle is intended. If review finds an SCC other than a deliberately atomic imported root, the candidate must be repaired rather than topologically sorted by file order.

## 7. Completion rule

This trace may accompany R2 only if independent review confirms: every material formal object in the two scoped candidate files appears exactly once above; every listed prerequisite resolves to an exact candidate object or basis-pinned import; no material direct edge is missing; no edge inverts D1/D2 ownership; reverse traversal reaches all materially affected descendants; and no completeness claim escapes the two-file bounded scope.