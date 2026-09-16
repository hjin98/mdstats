---
kind: semantic-definition-dependency-trace
protocol_version: 6.4.0
status: PROPOSED_NONAUTHORITATIVE_TRACE
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
scope:
  - workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE.md
  - workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE.md
---

# MLFF D1/D2 Protocol-6.4 definition dependency trace

## 1. Semantics

This file is a bounded review and impact-analysis aid, not D1-D4 semantic authority. Each row records a direct material edge

```text
SUBJECT USES_DEFINITION PREREQUISITE
```

meaning that changing the prerequisite's definition can change the subject's denotation, validity domain, units, admissibility, or interpretation. Transitive edges are intentionally omitted. Purely explanatory citations, implementation calls, and coincidental data flow are not dependency edges.

A reviewer performs impact analysis in reverse: if prerequisite `P` changes, visit every subject with edge `subject -> P`, then continue to their dependents.

## 2. D1 nodes and direct prerequisites

| Subject | Kind | Direct `USES_DEFINITION` prerequisites | Why direct |
| --- | --- | --- | --- |
| `D1.DEF.001` atomic configuration | definition | external ASE row-cell convention; source occurrence schema | establishes object domain/shape |
| `D1.DEF.002` canonical target label | definition | `D1.DEF.001` | label dimensions and atom order depend on configuration |
| `D1.DEF.003` label compatibility | definition | `D1.DEF.002`; accepted source-compatibility policy | relation is over canonical label statements |
| `D1.AX.001` compatible target domain | axiom | `D1.DEF.003` | target-domain premise is stated in compatibility classes |
| `D1.DEF.004` energy-conserving model | definition | `D1.DEF.001`; `D1.DEF.002` | observables and conventions are configuration/label defined |
| `D1.DEF.005` protected relation | definition | `D1.DEF.001`; accepted P1 relation providers | relation vertices and primitive edges must exist |
| `D1.AX.002` protected-role separation | axiom | `D1.DEF.005`; `D1.DEF.006` | separation acts on protected classes and roles |
| `D1.DEF.006` evidence-role map | definition | `D1.DEF.001`; accepted role vocabulary/policy | role map is defined over frame universe |
| `D1.AX.003` evidence noninterference | axiom | `D1.DEF.006`; role permission policy | permitted operations determine leakage boundary |
| `D1.DEF.007` correlation diagnostic | definition | scalar observable/process; D2 truncation definition | estimand needs observable and truncation |
| `D1.DEF.008` `U_size/P_train/M3` split | definition | `D1.DEF.001`; `D1.DEF.002`; `D1.DEF.005`; `D1.DEF.006`; `D1.AX.001`; `D1.AX.002` | eligibility, labels, development role, compatibility, and protected allocation determine the universe/split |
| `D1.AX.004` target-size controlled-variable axiom | axiom | `D1.DEF.008`; target-size policy family | specifies what may vary with `N` |
| `D1.DEF.009` evaluation order/rungs | definition | `D1.DEF.008`; configured evaluation sizes | order domain is exact `M3` |
| `D1.DEF.010` P3 primary response | definition | `D1.DEF.002`; `D1.DEF.009` | exact target force labels/membership define estimator |
| `D1.DEF.011` practical equivalence | definition | `D1.DEF.010`; configured `epsilon` | units/meaning come from response |
| `D1.AX.005` recommendation/decision separation | axiom | `D1.DEF.011`; operator freeze boundary | separates automatic evidence from operator design |
| `D1.DEF.012` `pi_train/T_N` | definition | `D1.DEF.008` | exact `P_train` is permutation domain |
| `D1.DER.001` exact nestedness | derived invariant | `D1.DEF.012` | prefix definition implies nesting |
| `D1.DEF.013` authorized selector information | definition | `D1.DEF.008`; `D1.DEF.006`; applicable selector providers | allowed/excluded information is role/domain dependent |
| `D1.AX.006` selector measurability | axiom | `D1.DEF.013`; `D1.DEF.012` | constrains order to authorized information |
| `D1.DEF.014` required family/reference measure | definition | `D1.DEF.013`; `D1.DEF.005` | family evidence and correlation-unit mass come from authorized selector evidence/protected units |
| `D1.DEF.015` family covered mass | definition | `D1.DEF.014`; D2 family neighborhood; `gamma_cov` family | coverage needs measure, neighborhood, threshold family |
| `D1.DEF.016` extent support | definition | `D1.DEF.014`; D2 weighted quantile; extent parameter family | tail support is family/quantile defined |
| `D1.DEF.017` hard-support obligation | definition | `D1.DEF.012`; applicable condition/event/profile/extent/correlation providers | incidence is on exact `P_train`; loci come from providers |
| `D1.DEF.018` membership admissibility | definition | `D1.DEF.012`; `D1.DEF.015`; `D1.DEF.016`; `D1.DEF.017`; label-usability policy | conjunction defines qualification |
| `D1.DER.002` qualification monotonicity | derived invariant | `D1.DER.001`; `D1.DEF.015`; `D1.DEF.016`; `D1.DEF.017`; `D1.DEF.018` | nesting plus positive predicates gives monotonicity |
| `D1.AX.007` qualification/ranking separation | axiom | `D1.DEF.018`; `D1.DEF.010`; P3 reducer policy | separates admission from model-error ranking |
| `D1.AX.008` repair continuity | axiom | `D1.DEF.012`; `D1.DEF.015`; `D1.DEF.017`; D2 repair objective | states allowed scientific effect of repair |
| `D1.DEF.019` property mask | definition | `D1.DEF.002` | availability is label-contract property |
| `D1.AX.009` method-specific objective | axiom | `D1.DEF.019`; target-size/P5 method mode | objective family depends on method role |
| `D1.DEF.020` foundation identity | definition | accepted foundation provider/model identity | binds checkpoint/head/model lineage |
| `D1.DEF.021` composition-weighted E0 correction | definition | `D1.DEF.020`; authorized target-gradient domain; composition-count basis | residual reference estimand depends on foundation and fit domain |
| `D1.AX.010` authorized E0 fit domain | axiom | `D1.DEF.021`; `D1.AX.003` | enforces fit-domain and leakage rule |
| `D1.DEF.022` common monitor | definition | `D1.DEF.005`; `D1.DEF.006`; OUTER_MONITOR parent; `n_mon` family | monitor role/membership/separation are jointly defined |
| `D1.DEF.023` post-selection fold partition | definition | `D1.DEF.012`; `D1.DEF.005`; CV `K`/purge policy | folds partition frozen `T_N` by protected components |
| `D1.DEF.024` role-threshold family | definition | `D1.DEF.022`; `D1.DEF.023`; configured outer metric | each threshold has population/metric role |
| `D1.AX.011` fixed-budget CV consistency | axiom | `D1.DEF.023`; `D1.DEF.024`; D2 role predicates | acceptance quantifies over required fold/seed positions |
| `D1.AX.012` fresh production | axiom | `D1.DEF.012`; `D1.DEF.020`; `D1.DEF.021`; `D1.DEF.022`; `D1.DEF.024` | production binds selected membership/foundation/E0/monitor/role policy |
| `D1.AX.013` downstream no-feedback | axiom | `D1.AX.005`; `D1.AX.012`; downstream qualification role | defines freeze boundary and direction of evidence flow |

## 3. D2 nodes and direct prerequisites

| Subject | Kind | Direct `USES_DEFINITION` prerequisites | Why direct |
| --- | --- | --- | --- |
| `D2.DEF.001` canonical population | definition | `D1.DEF.001` | numeric tuple contains D1 frames |
| `D2.DEF.002` exact `M3` split | definition | `D1.DEF.008`; `D1.DEF.005`; `D2.DEF.001`; configured `m3` | concretizes protected exact split |
| `D2.DEF.003` prefix | definition | `D2.DEF.001` | prefix is over ordered tuples |
| `D2.DEF.004` family witness weights | definition | `D1.DEF.014`; P1 correlation-unit identity | concretizes equal unit mass |
| `D2.DEF.005` weighted quantile | definition | `D2.DEF.004` when used for selector family | selector quantile consumes family weights |
| `D2.DEF.006` robust scale | definition | `D2.DEF.005`; family feature values | scale branches use quantiles/std |
| `D2.DEF.007` family metric | definition | `D2.DEF.006`; family coordinate vectors | normalized coordinates define distance |
| `D2.DEF.008` local radius | definition | `D2.DEF.004`; `D2.DEF.007` | leave-one-out mass is ordered by metric |
| `D2.DEF.009` exact adjacency | definition | `D2.DEF.007`; `D2.DEF.008` | neighborhood predicate uses metric/radius |
| `D2.DEF.010` multiplicity/coverage | definition | `D2.DEF.004`; `D2.DEF.009` | coverage sums weights over adjacency-supported witnesses |
| `D2.DEF.011` extent predicate | definition | `D2.DEF.005`; selected family values | tail thresholds are weighted quantiles |
| `D2.DEF.012` source obligation | definition | `D1.DEF.017` | numerical record concretizes D1 locus/incidence/minimum |
| `D2.DEF.013` obligation canonicalization | definition | `D2.DEF.012` | groups source obligations |
| `D2.DEF.014` obligation count/deficit | definition | `D2.DEF.013` | counts canonical incidence/minimum |
| `D2.DEF.015` feasibility horizon | definition | configured candidate-size family | FEAS1 horizon is max configured size |
| `D2.AX.001` exact sparse representation | axiom | `D2.DEF.009`; `D2.DEF.013`; P1 correlation codes | sparse authority must reproduce primitive relations |
| `D2.DEF.016` selector state | definition | `D2.DEF.010`; `D2.DEF.014`; `D1.DEF.012` | state stores selected prefix and primitive counts/masses |
| `D2.DEF.017` hard gain | definition | `D2.DEF.014`; `D2.DEF.016` | identifies unsatisfied loci supported by candidate |
| `D2.DEF.018` new-coverage gain | definition | `D2.DEF.004`; `D2.DEF.009`; `D2.DEF.016` | gain is uncovered adjacent witness mass |
| `D2.DEF.019` representative gain | definition | `D2.DEF.004`; `D2.DEF.009`; `D2.DEF.016` | utility uses adjacency/multiplicity |
| `D2.DEF.020` sparse diversity | definition | `D2.DEF.009`; `D2.DEF.016` | nested means use candidate witness neighborhoods/multiplicity |
| `D2.DEF.021` Phase-A predicate | definition | `D2.DEF.010`; `D2.DEF.014`; `D2.DEF.016` | phase depends on hard satisfaction state |
| `D2.DEF.022` Phase-A winner | definition | `D2.DEF.017`; `D2.DEF.018`; `D2.DEF.019`; `D2.DEF.020`; `D2.DEF.021`; canonical family/correlation/UID order | lexicographic rule consumes all primitives |
| `D2.DEF.023` Phase-B winner | definition | `D2.DEF.019`; `D2.DEF.020`; `D2.DEF.021`; correlation/UID order | Phase B starts after hard predicates satisfied |
| `D2.DEF.024` full-forward oracle | definition | `D2.DEF.022`; `D2.DEF.023`; `D2.DEF.016` | reference rank sequence applies winner rule to state |
| `D2.DEF.025` certified-lazy equivalence | definition | `D2.DEF.019`; `D2.DEF.023`; `D2.DEF.024`; IEEE-754 `nextafter` | lazy bounds certify equality to oracle |
| `D2.DEF.026` configured shell | definition | configured candidate-size family; `D1.AX.008` | shell boundaries constrain repair |
| `D2.DEF.027` removal admissibility | definition | `D2.DEF.009`; `D2.DEF.014`; `D2.DEF.016`; `D2.DEF.026` | unique mass/deficit act on active shell state |
| `D2.DEF.028` representative utility | definition | `D2.DEF.004`; `D2.DEF.016` | harmonic utility uses weights/multiplicity |
| `D2.DEF.029` repair objective | definition | `D2.DEF.010`; `D2.DEF.014`; `D2.DEF.028`; correlation counts; `D2.DEF.027` | ordered objective combines hard/coverage/utility/balance |
| `D2.AX.002` repair reconstruction | axiom | `D2.DEF.029`; `D2.DEF.016`; `D2.DEF.024` | repaired prefix invalidates derived state |
| `D2.DEF.030` MVQUAL | definition | `D1.DEF.018`; `D2.DEF.010`; `D2.DEF.011`; `D2.DEF.014`; `D2.AX.001` | independent numerical qualification concretizes D1 admissibility |
| `D2.DEF.031` composition matrix | definition | `D1.DEF.002`; atomic species basis; authorized fit membership | count/energy system needs labels/composition |
| `D2.DEF.032` foundation residual fit | definition | `D1.DEF.020`; `D2.DEF.031`; accepted anchor/regularization policy | exact foundation/head and count system define fit |
| `D2.DEF.033` composition-transfer test | definition | `D1.DEF.021`; `D2.DEF.032`; numerical-rank rule | null-space test concretizes D1 identifiability |
| `D2.DEF.034` scalar Huber | definition | positive dimensional threshold | primitive robust loss |
| `D2.DEF.035` dimensional thresholds | definition | D1 foundation-P5 objective family; canonical property units | binds one numeric configuration to physical channels |
| `D2.DEF.036` property losses | definition | `D1.DEF.019`; `D2.DEF.034`; `D2.DEF.035`; canonical residuals | reductions consume masks/residuals/thresholds |
| `D2.DEF.037` foundation-P5 objective | definition | `D1.AX.009`; `D2.DEF.036` | weighted sum concretizes accepted 1:10:1 objective |
| `D2.DEF.038` P3 updates/epoch | definition | candidate `N`; target batch size; complete-batch rule | update count defines progress normalization |
| `D2.DEF.039` P3 progress normalization | definition | `D2.DEF.038`; reference LR/EMA policy | scaling is update-count relative |
| `D2.DEF.040` P3 target-force estimator | definition | `D1.DEF.010`; exact evaluation membership | numerical/unit concretization of response |
| `D2.DEF.041` complete-seed score | definition | `D2.DEF.040`; configured seed set | candidate score requires all replicates |
| `D2.DEF.042` practical-equivalence step | definition | `D1.DEF.011`; `D2.DEF.041` | reducer applies epsilon to complete-seed scores |
| `D2.DEF.043` combined P5 corpus | definition | authenticated target/replay memberships; foundation method mode | pre-shuffle order defines stochastic exposure |
| `D2.DEF.044` P5 update geometry | definition | `D2.DEF.043`; batch size; drop-last policy | consumed examples/updates depend on corpus size/order |
| `D2.DEF.045` monitor parent/strata | definition | `D1.DEF.022`; usable OUTER_MONITOR data | numerical sampler input |
| `D2.DEF.046` monitor quota | definition | `D2.DEF.045`; SHA-256; monitor seed | deterministic quota order |
| `D2.DEF.047` monitor positions | definition | `D2.DEF.046`; ordered stratum frames; SHA-256 | deterministic exact membership |
| `D2.DEF.048` component fold order | definition | `D1.DEF.023`; protected-component identities; CV seed/algorithm/membership digest | deterministic outer-fold allocation |
| `D2.DEF.049` purge rule | definition | `D2.DEF.048`; configured purge count | gradient membership is complement of outer+purge |
| `D2.DEF.050` shared checkpoint constraint | definition | shared P5 method policy; replay/integrity evidence | role-independent admissibility conjunct |
| `D2.DEF.051` monitor RMSE | definition | `D2.DEF.047`; target-force estimator semantics | checkpoint target metric needs exact monitor membership |
| `D2.DEF.052` role checkpoint predicate | definition | `D1.DEF.024`; `D2.DEF.050`; `D2.DEF.051` | combines shared constraints and role ceiling |
| `D2.DEF.053` CV outer predicate | definition | `D1.DEF.024`; `D2.DEF.048`; configured outer metric | held-out metric/threshold live on exact outer fold |
| `D2.DEF.054` CV acceptance | definition | `D2.DEF.052`; `D2.DEF.053`; configured required fold/seed set | universal quantification over required positions |
| `D2.AX.003` role currentness | axiom | `D1.DEF.024`; `D2.DEF.052`; `D2.DEF.053`; `D2.DEF.054` | invalidation scope follows changed role predicate |
| `D2.DEF.055` authenticated continuation | definition | exact run/method/membership/optimizer/RNG identities | continuation authority requires exact boundary identity |
| `D2.DEF.056` numerical equivalence | definition | owning reference definition; declared output set/equality relation | formalizes replaceable execution criterion |
| `D2.AX.004` execution noninterference | axiom | `D2.DEF.056` | execution knobs are non-semantic only under equivalence |

## 4. Cross-domain D2 -> D1 dependencies

These edges are repeated here because they are the critical abstraction/concretization bindings reviewers should challenge first.

```text
D2.DEF.002  -> D1.DEF.008
D2.DEF.004  -> D1.DEF.014
D2.DEF.010  -> D1.DEF.015
D2.DEF.011  -> D1.DEF.016
D2.DEF.012  -> D1.DEF.017
D2.DEF.030  -> D1.DEF.018
D2.DEF.032  -> D1.DEF.020
D2.DEF.033  -> D1.DEF.021
D2.DEF.037  -> D1.AX.009
D2.DEF.040  -> D1.DEF.010
D2.DEF.042  -> D1.DEF.011
D2.DEF.045  -> D1.DEF.022
D2.DEF.048  -> D1.DEF.023
D2.DEF.052  -> D1.DEF.024
D2.DEF.053  -> D1.DEF.024
D2.DEF.054  -> D1.AX.011
```

An attempted D2 change that cannot preserve the referenced D1 object is an upward D1 Challenge.

## 5. Parameter-family dependencies

| Parameter family | Direct consumers | Default versus invariant rule |
| --- | --- | --- |
| family coverage `gamma_cov` | `D1.DEF.015`, `D2.DEF.010`, Phase-A satisfaction, MVQUAL | current instance `0.95`; changing it is D1/D2 policy change |
| extent quantiles | `D1.DEF.016`, `D2.DEF.005`, `D2.DEF.011` | current instance `(0.01,0.99)`; not an implementation knob |
| selector metric tolerance | `D2.DEF.009` | `1e-12`; D2 numerical authority |
| selector contender tolerance | `D2.DEF.022`, `D2.DEF.023`, `D2.DEF.029` | `1e-14` except explicitly distinct predicates |
| lazy monotonicity guard | `D2.DEF.025` | `5e-13`; invariant/fail-closed guard, not rank tolerance |
| configured target ladder | `D2.DEF.015`, `D2.DEF.026`, P3 funnel | concrete configuration instance; historical fixed ladder is not authority |
| P3 practical `epsilon` | `D1.DEF.011`, `D2.DEF.042` | configuration-bound policy |
| P5 Huber numeric parameter | `D2.DEF.035-D2.DEF.037` | current `0.01` with property-specific units |
| monitor size/seed | `D1.DEF.022`, `D2.DEF.045-D2.DEF.047` | current method `256`, seed `161803`; no silent fallback |
| CV fold count/seed/purge | `D1.DEF.023`, `D2.DEF.048-D2.DEF.049` | default `K=3`, explicit `K>=2` override permitted |
| `tau_CV` | `D1.DEF.024`, `D2.DEF.052` | configurable; default `0.045 eV/angstrom` |
| `theta_CV` | `D1.DEF.024`, `D2.DEF.053` | configurable in outer-metric units; default force metric `0.045 eV/angstrom` |
| `tau_prod` | `D1.DEF.024`, `D2.DEF.052` | configurable; default `0.030 eV/angstrom` |

## 6. Topological review order

Ignoring external imported primitives, the graph should be reviewed approximately in this order:

1. D1 configuration/label/compatibility/protected relation/evidence roles;
2. D1 target-size universe and split;
3. D1 target-order objects, coverage/support/admissibility;
4. D1 foundation identity/E0 estimand;
5. D1 monitor/folds/role policies;
6. D2 population/split primitives;
7. D2 TargetCoverage metric chain;
8. D2 obligation chain;
9. D2 selector/repair/qualification chain;
10. D2 E0 fit/transfer chain;
11. D2 loss/objective chain;
12. D2 P3 optimizer/estimator/reducer chain;
13. D2 P5 exposure chain;
14. D2 monitor/fold/checkpoint/CV chain;
15. D2 restart/equivalence semantics.

No intended semantic cycle exists. If review finds a cycle, either a hidden owner duplication exists or the mutually recursive definitions must be replaced by one explicit composite definition before promotion.

## 7. Impact-query examples

- Changing `D1.DEF.005` protected relation directly impacts `D1.AX.002`, `D1.DEF.008`, `D1.DEF.014`, `D1.DEF.022`, `D1.DEF.023`; reverse traversal then reaches split, target order, monitor, and CV descendants.
- Changing `D2.DEF.009` adjacency directly impacts coverage, MVIDX exactness, selector gains/diversity, repair eligibility, and MVQUAL; it therefore has broad D2 and D1 membership-admissibility impact.
- Changing `tau_CV` impacts `D1.DEF.024`, `D2.DEF.052`, `D2.DEF.054`, and CV-derived production authorization, but does not directly change shared `D2.DEF.050` or `tau_prod`.
- Changing `D2.DEF.043` corpus order changes stochastic exposure and therefore P5 training evidence, but does not change P2/P3 target-size memberships.

## 8. Completion rule

Before this trace can accompany accepted authority, independent review must verify that every material formal object in the D1/D2 candidate appears exactly once as a node, all material prerequisites are represented as direct edges, no edge inverts abstraction ownership, and no missing edge could hide a materially affected descendant during change review.
