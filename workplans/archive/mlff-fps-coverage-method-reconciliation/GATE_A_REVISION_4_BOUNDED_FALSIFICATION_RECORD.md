# Gate A Revision 4 bounded falsification record

Date: 2026-09-13
Candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 4
Status: author-side bounded evidence; **not independent acceptance evidence**.

## 1. Scope and provenance

This record realizes only the cheapest mathematical/static falsification targets needed to check the Revision-4 repairs before another independent review. It does not claim production-path, current-provider runtime, or resource qualification because the remote repository is available here through the GitHub connector rather than as an executable checkout.

Executable reference fixtures were run with a standalone Python 3 scalar script using only the equations written in the candidate. The production implementation was not imported, so these fixtures avoid a self-confirming production/reference oracle but cannot prove D4 conformance.

Static provider evidence was inspected from accepted project state `hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d`.

## 2. F1 — mutual-redundancy counterexample

Fixture: four singleton protected components at one-dimensional coordinates

```text
0.0, 10.0, 100.0, 100.001
```

with reserve cardinality 2 and equal condition cost.

The rejected Revision-3 static component score `min distance to U_size \ g` gives squared nearest distances

```text
100, 100, 1e-6, 1e-6
```

so an additive static objective removes both `100.0` and `100.001`, eliminating that structural mode from P_train.

Revision-4 retained-set recomputation produced:

```text
step 1: remove 100.0, H_max ~= 1.0e-6
retained: 0.0, 10.0, 100.001
step 2 candidate scores:
  0.0      -> 100
  10.0     -> 100
  100.001  -> about 8100.18
selected removal: 0.0 by deterministic tie
final retained: 10.0, 100.001
```

Result: the mutually redundant pair cannot both continue to certify one another after the first removal. **PASS for the specific R3 counterexample.** This does not claim global covering-radius optimality, which Revision 4 explicitly does not promise.

## 3. F2 — hard neutral-condition feasibility

A bounded exact enumeration used protected singleton components with condition counts A=3, B=2 and exact M3 size 2. Every hard-feasible subset was enumerated. The minimum condition-depletion value was

```text
J* = 2/3
```

and every J*-optimal subset removed two A frames rather than depleting the scarcer B condition.

A second fixture with A=2, B=1 and exact M3 size 2 has no split that both preserves at least one frame of every condition and removes exactly two frames. The exhaustive reference returns no feasible subset. **PASS:** the intended result is scientific split infeasibility, not condition extinction.

## 4. F3 — scale-conditioning counterexamples

Binary64 unit roundoff is `u=2^-53`; Revision 4 uses `tau=sqrt(u)` and `rho=tau*max_abs`.

### Near-machine-scale jitter

```text
[1.0, 1.0+2u, 1.0+4u, 1.0+6u]
```

Reference type-7 values gave approximately:

```text
IQR = 2.220446049250313e-16
rho = 1.0536712127723515e-08
max deviation < rho
```

The coordinate is therefore classified `numerically unresolved` and contributes zero numerical variation instead of amplifying binary64-scale jitter to order-one metric distance. **PASS.**

### Rare genuine excursion

```text
[1,1,1,1,1,1,1,1,1,2]
```

Here `IQR=0`, but `max deviation=1 >> rho`. Revision 4 selects the max-deviation fallback scale `1.0`, preserving the rare excursion instead of dropping the coordinate. **PASS.**

The `rho=tau*M` rule is positively unit-rescaling invariant by construction: multiplying every coordinate by positive `a` multiplies IQR, max deviation, M, and rho by the same `a` and leaves branch decisions unchanged (modulo the separately governed canonical binary64 reference).

## 5. F4 — Fisher-Yates exact small-n reference

For n=4, exhaustive enumeration of the accepted Fisher-Yates choices

```text
r_3 in {0,1,2,3}
r_2 in {0,1,2}
r_1 in {0,1}
```

produced exactly 24 distinct permutations, each once. This matches the analytical product `4*3*2=24`; rejection sampling of unbiased bits makes each accepted `r_i` uniform on its required range. **PASS for the numerical construction.**

This fixture does not establish a production entropy source or restart persistence; those are still required real-owner evidence.

## 6. F5 — variable-atom-count EVAL2 estimand

A four-frame finite population used component counts

```text
C = [300,3,3,3]
```

and frame component-MSE values

```text
[4,1,9,16].
```

The exact full-M3 ratio is

```text
r_M3 = 4.135922330097087
R_M3 = 2.03369671536763.
```

Enumerating all size-2 SRSWOR subsets gave ratio estimates

```text
3.9703, 4.0495, 4.1188, 5.0, 8.5, 12.5
```

with a mean different from the full ratio. This confirms the candidate's deliberately limited claim: the finite-prefix ratio estimator is not exactly unbiased, while the full M3 prefix recovers the exact component-weighted estimand. **PASS against the previous false-unbiasedness risk.**

## 7. F6 — accepted provider substrate audit

Accepted code at `e8d04144...` shows:

- `UniversalStructuralSelectionPolicy` defaults `include_declared_atom_groups=True` and `include_element_groups=True`;
- frame aggregation names coordinates as `group:<group_id>:...`;
- declared groups can come from material-profile contracts or a membership provider;
- the low-level `LocalStructureFeaturePolicy` itself is material-neutral and exposes the exact local feature names and numerical policy values;
- current `_feature_family` maps those local feature names into the eight generic families used by Revision 4.

Therefore directly importing the current default universal frame catalog would violate Revision 4's material-neutral membership claim. Revision 4 instead freezes an element-only, no-declared-group aggregation view over the low-level provider and excludes frame `atom_count`/`atom_fraction` plus raw material-specific pair-rule coordinates. **Static design repair supported.**

This is an authority/design audit, not runtime proof that the future D3/D4 owner publishes the new neutral view correctly.

## 8. Evidence still unavailable / required before promotion

The following Revision-4 requirements did not execute and remain blockers to Gate A promotion:

1. real current neutral-provider construction and lineage authentication;
2. complete produced coordinate/family table on representative current data;
3. equal-family-mass sensitivity/ablation on real feature families;
4. optimized-versus-canonical scalar discrete-order equivalence;
5. exact J*/completion-admissibility solver comparison against the future real implementation;
6. UID/source/input/feature-column metamorphic checks through the actual owner;
7. randomization-source and restart/no-redraw integration;
8. old-generation fail-closed admission through persistence/currentness;
9. representative CPU/RAM benchmark for neutral descriptor construction, retained-set split search, and K-bounded FPS;
10. D3/D4 prepare -> publish -> consume integration and affected regression.

A required unavailable realization is not counted as a pass. This record supports another independent D1/D2 review of the proposed mathematics; it does not close Gate A by itself.