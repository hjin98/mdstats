# Gate A Revision 5 bounded falsification record

Date: 2026-09-13
Candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 5
Status: author-side bounded mathematical/static evidence; **not independent acceptance evidence**.

## 1. Scope

This record checks the new Revision-5 repair semantics cheaply before independent review. It does not claim production D3/D4 conformance. The real repository is available through the GitHub connector rather than an executable checkout, so no claim is made that future production paths already implement the proposal.

A standalone scalar Python reference fixture was executed from the equations in the candidate. It did not import the production target-order implementation.

## 2. Missing/constant coordinate state reference

The reference transform used the Revision-5 state rules.

### All missing

```text
[missing, missing, missing]
-> numerical state ALL_MISSING_INACTIVE
-> numerical active = false
-> missing-indicator active = false
-> active dimension contribution = 0
```

This prevents an all-one missing indicator from diluting an otherwise informative family.

### Partial missing, constant observed value

```text
[1.0, missing, 1.0]
-> numerical state CONSTANT_INACTIVE
-> numerical active = false
-> varying missing-indicator active = true
-> active dimension contribution = 1
```

Only the genuinely discriminating missingness pattern contributes distance.

### Partial missing, varying observed value

```text
[1.0, missing, 2.0]
-> numerical active = true
-> median = 1.5
-> IQR scale = 0.5
-> varying missing-indicator active = true
-> active dimension contribution = 2
```

### Fully observed constant

```text
[1.0,1.0,1.0]
-> numerical state CONSTANT_INACTIVE
-> missing-indicator inactive
-> active dimension contribution = 0
```

These cases close the ambiguity identified in R4-B1 at the mathematical reference level.

## 3. Removal of the Revision-4 resolution floor

The Revision-4 review used:

```text
[1, 1+1e-9, 1+2e-9, 1+3e-9]
```

Revision 5 produced an active numerical coordinate with approximately:

```text
median = 1.0000000015000001
IQR = 1.4999999020659516e-09
scale = IQR
```

The nonzero variation is no longer suppressed by an unrelated `sqrt(u)` threshold. **PASS against the specific R4-B2 counterexample.**

Rare-excursion fixture:

```text
[1,1,1,1,1,1,1,1,1,2]
```

has collapsed IQR but nonzero maximum median deviation and therefore uses:

```text
scale = 1.0
```

The rare excursion remains represented.

Revision 5 deliberately makes no claim that every finite provider difference is physically meaningful. It only refuses to invent a generic target-order resolution threshold without an accepted upstream error model.

## 4. Full-M3 evaluation invariance to diagnostic order

Variable-atom fixture:

```text
component counts C = [300,3,3,3]
frame component MSE = [4,1,9,16]
SSE = [1200,3,27,48]
```

Exact M3 ratio and RMSE are:

```text
r_M3 = 4.135922330097087
R_M3 = 2.03369671536763
```

Reordering the same four frames through tested permutations leaves both totals and the exact M3 estimator unchanged. Therefore a diagnostic `pi_eval` realization cannot change the Revision-5 reducer input when the reducer evaluates full M3.

This directly removes the Revision-4 failure mode in which a random M1/M2 realization could eliminate a candidate before full-M3 evaluation.

## 5. Previously applicable Revision-4 evidence retained

The following bounded Revision-4 fixtures remain applicable because Revision 5 preserves the governed semantics:

- mutual-redundancy counterexample: retained-set rescoring prevents two mutually redundant components from both disappearing on stale static scores;
- hard neutral-condition infeasibility: exact reserve cardinality that would extinguish a condition fails rather than relaxing the invariant;
- Fisher-Yates small-n construction: under independent unbiased bits the diagnostic permutation is exactly uniform;
- variable-atom-count finite-prefix result: a ratio estimator over a sample is not falsely claimed exactly unbiased.

The Revision-4 `sqrt(u)` fixture is superseded because that rule was removed.

## 6. Static provider-contract evidence

Accepted project state identifies the local-structure numerical owner as `mdstats.analysis.local_structure` and binds:

```text
LOCAL_STRUCTURE_POLICY_SCHEMA = mdstats.local-structure-feature-policy.v1
LOCAL_STRUCTURE_RESULT_SCHEMA = mdstats.local-structure-feature-result.v1
LOCAL_STRUCTURE_POLICY_VERSION = mdstats.analysis.local-structure.2026-07.v1
```

Accepted specification:

```text
hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d:
docs/specs/analysis/local_structure_features_spec.md
blob cc5be8d4f31d9168e09f2baa07711d5c37cf9b62
```

The spec owns the minimum-image, smooth-connectivity, radial, angular, orientational, density, missing-mask, and complexity semantics and explicitly states that MLFF may aggregate the rows but may not redefine those numerical kernels. Revision 5 now binds this contract directly instead of treating current feature names as sufficient identity.

## 7. Evidence still required at Gate A

This author-side record does **not** close:

1. real-feature equal-family sensitivity/ablation on representative current data;
2. provider/aggregation precision sensitivity on representative real features;
3. independent exhaustive/reference checks of J* and completion admissibility beyond the existing bounded fixtures;
4. representative CPU/RAM feasibility of the exact completion oracle plus retained-set scoring and K-bounded FPS;
5. independent method-level identity/input-order/feature-coordinate metamorphics feasible without production persistence; or
6. a genuinely separate-context independent D1/D2 review.

These remain Gate-A promotion requirements.

## 8. Evidence moved to downstream gates, not removed

The following are intentionally not claimed here because they require a D3/D4 concretization that Gate A has not yet authorized:

- production neutral-provider publication;
- production optimized-vs-reference equivalence;
- persistence/restart of diagnostic `pi_eval`;
- current-generation storage admission and old-generation rejection;
- real `prepare -> publish -> consume` integration;
- target-order descendant invalidation/regression.

They remain mandatory Gates B-E conformance evidence after upstream acceptance.