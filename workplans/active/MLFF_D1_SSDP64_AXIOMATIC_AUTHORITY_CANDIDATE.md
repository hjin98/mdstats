---
kind: proposed-D1-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_AWAITING_INDEPENDENT_REVIEW_AND_STAKEHOLDER_RATIFICATION
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
would_compose_with:
  - docs/methods/mlff_scientific_method.md
  - docs/methods/mlff_target_training_order_scientific_method.md
---

# Proposed MLFF D1 axiomatic authority kernel

## 1. Authority and interpretation

This file is a **proposed Protocol-6.4 D1 formalization overlay** for the accepted MLFF scientific authority at basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. It is not accepted-current authority until a fresh independent D1/D2 review passes and the stakeholder ratifies the exact candidate.

If ratified, this kernel becomes the formal-first entry point for the MLFF D1 authority family. The accepted prose in `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_target_training_order_scientific_method.md` remains the explanatory, provenance, validity, uncertainty, and application context except where this overlay explicitly replaces an imprecise statement with an equivalent formal definition. Conflicts are not resolved by silently choosing this candidate: any material conflict is a review blocker and must be adjudicated before promotion.

Semantic roles used below are explicit:

- **Definition** introduces notation or a semantic object.
- **Axiom** is a project-governing scientific premise/invariant accepted for this method; it is not a theorem about nature.
- **Derived invariant** follows from the definitions and axioms stated here.
- **Empirical claim** requires evidence and is not established by being placed next to a definition.
- **Policy parameter** is a family coordinate whose resolved value defines a concrete method/policy instance.
- **Default** is a generated value used when no explicit binding overrides it; it is not a universal constant.

The intended competent reader is a computational materials scientist or scientific-software reviewer familiar with atomistic simulation, supervised interatomic-potential fitting, basic probability/statistics, linear algebra, and cross-validation. Project-specific objects are defined below.

## 2. Foundational scientific signature

### D1.DEF.001 — Atomic configuration

An atomic configuration is

$$
x=(\mathbf Z,\mathbf R,\mathbf H,\mathbf p),
$$

where `Z=(Z_1,...,Z_n)` is the ordered atomic-number vector, `R` is the ordered Cartesian position matrix in `angstrom`, `H` is the periodic cell matrix under the accepted ASE row-vector convention, and `p` contains periodicity flags and source-occurrence identity needed to interpret the frame. Two source occurrences may represent the same geometry; occurrence identity and geometry identity are distinct.

Undefined/failure cases: malformed atom counts, non-finite coordinates, singular/invalid cell state where a cell is required, or inconsistent periodic metadata make the configuration ineligible under the active source policy.

### D1.DEF.002 — Canonical target label statement

For an eligible configuration `x`, a canonical target-label statement is the partial tuple

$$
y(x)=\big(E(x),\mathbf F(x),\boldsymbol\sigma(x);\lambda(x)\big),
$$

where `E` is total energy, `F` is the ordered Cartesian force field, `sigma` is symmetric Cartesian Cauchy stress when present, and `lambda` binds theory/electronic-structure identity, energy reference, derivative/stress convention, units, and numerical-quality/provenance semantics.

A missing optional property is not numerically equal to zero. Property availability is represented separately and later becomes a D2 mask where the governing objective permits it.

### D1.DEF.003 — Label compatibility relation

For canonical label statements `y_a,y_b`, define

$$
y_a\sim_{\mathrm{label}}y_b
$$

iff their theory level, energy-reference semantics, derivative convention, stress convention, units, and all other current compatibility-significant coordinates agree under the accepted source-compatibility policy. Provenance differences declared non-semantic by that policy do not alone make labels incompatible.

### D1.AX.001 — Compatible target-domain axiom

Every target training/evaluation population consumed as one scientific target domain contains only labels in one compatible `~_label` class. A separately identified replay lineage may coexist but does not become target-domain evidence by concatenation.

### D1.DEF.004 — Energy-conserving interatomic model family

For parameters `theta`, atomic numbers `Z`, positions `R`, and cell `H`, the accepted MLFF model represents a scalar potential-energy surface

$$
E_\theta(\mathbf Z,\mathbf R,\mathbf H).
$$

When the corresponding labels are governed, forces and Cauchy stress are derivative observables under the accepted source convention:

$$
\mathbf F_i=-\frac{\partial E_\theta}{\partial \mathbf R_i},
$$

$$
\boldsymbol\sigma=-\frac{1}{V}\frac{\partial E_\theta}{\partial\boldsymbol\varepsilon}.
$$

These equations define the scientific relation to be preserved; dependency-specific automatic-differentiation realization is downstream.

## 3. Statistical dependence and evidence roles

### D1.DEF.005 — Protected relation

Let `U` be a finite eligible frame universe. The primitive protected relation `R_prot` is the union of accepted inseparability relations on `U`, including correlation-unit co-membership, exact geometry duplication, protected-event co-membership, condition-scoped replica lineage, and condition-scoped structural-realization lineage where available.

Define the protected equivalence relation

$$
\sim_{\mathrm{prot}}=\operatorname{TC}(R_{\mathrm{prot}}),
$$

where `TC` denotes reflexive-symmetric-transitive closure. In prose/renderers that disallow named-operator macros, `TC` is the closure function named here, not a LaTeX operator command.

### D1.AX.002 — Protected-role separation axiom

No two frames in one `~_prot` equivalence class may be assigned to evidence roles that the governing method declares mutually independent or mutually exclusive.

### D1.DEF.006 — Evidence-role map

An evidence-role map on universe `U` is a function

$$
r:U\rightarrow\mathcal R,
$$

where `R` contains at least development/gradient-capable, checkpoint-monitor/model-control, post-selection held-out, calibration, locked/challenge, purge/excluded, and other explicitly accepted roles.

The permission set `Perm(role)` states which operations may consume labels from that role.

### D1.AX.003 — Evidence noninterference axiom

If operation `a` is not in `Perm(r(x))`, then the label/prediction information of frame `x` must not influence `a`, directly or through a fitted transform, reference distribution, checkpoint choice, membership choice, threshold calibration, or descendant state.

Consequences include: held-out labels do not choose checkpoints; monitor labels do not fit training state; locked evidence does not choose target membership or final-product membership; target-size evaluation outcomes do not feed backward into `pi_train`.

### D1.DEF.007 — Correlation diagnostic

For a stationary scalar observable `X_t` with finite variance, normalized lag correlation and the accepted truncated integrated correlation time are

$$
\rho(k)=\frac{\mathrm{Cov}(X_t,X_{t+k})}{\mathrm{Var}(X_t)},
$$

$$
\tau_{\mathrm{int}}=\frac12+\sum_{k=1}^{k^\star}\rho(k),
$$

with truncation `k*` defined by D2. The diagnostic effective count is

$$
N_{\mathrm{eff}}=\min\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
$$

`N_eff` quantifies serial redundancy for the chosen observable/truncation; it is not a proof of full slow-state independence.

## 4. Target-size experiment

### D1.DEF.008 — Target-size universe and exact split

`U_size` is the exact eligible neutral-development frame universe with canonical training labels used for the target-size experiment. It is partitioned exactly once as

$$
U_{\mathrm{size}}=P_{\mathrm{train}}\mathbin{\dot\cup}M_3,
$$

where `P_train` is the target-membership source population and `M3` is the largest target-size evaluation reserve. The split preserves every applicable protected component; no component is divided between the two sets.

### D1.AX.004 — Target-size controlled-variable axiom

Within one target-size experiment, changing candidate cardinality `N` may change only the exact training prefix `T_N` and consequences causally downstream of adding those frames. The pre-order evidence authority, membership rule, P3 common fitted preparation, optimizer-seed population, fidelity schedule, evaluation ladder, training objective, and reducer policy remain candidate-independent unless an explicitly accepted method coordinate says otherwise.

### D1.DEF.009 — Evaluation order and rungs

A deterministic permutation `pi_eval` of `M3` defines configured nested evaluation memberships

$$
M_i=\pi_{\mathrm{eval}}[:m_i],
$$

so `m_i<m_j` implies `M_i subset M_j` with exact prefix identity. These are P3 model-selection populations, not post-selection held-out folds or checkpoint monitors.

### D1.DEF.010 — Primary P3 response

For an exact evaluation membership with `K>0` admitted Cartesian force components, the primary target-size response is

$$
\mathrm{RMSE}_F=
\sqrt{\frac{1}{K}\sum_{k=1}^{K}
\left(F_k^{\mathrm{pred}}-F_k^{\mathrm{ref}}\right)^2}.
$$

Current stored target-size values use `meV/angstrom`; D2 owns the exact unit conversion and failure semantics.

### D1.DEF.011 — Practical equivalence family

Let `epsilon>0` be the configured practical-equivalence threshold in the same units as the P3 response. Two candidate scores `e_a,e_b` are scientifically practically equivalent for reducer purposes when

$$
|e_a-e_b|\le\epsilon
$$

under the accepted reducer's directional selection semantics. `epsilon` is a policy parameter, not machine epsilon.

### D1.AX.005 — Recommendation/decision separation axiom

The automatic reducer produces target-size evidence/recommendation only. The operator owns the provisional post-selection design within the qualified configured set; post-selection CV may accept or reject that frozen design but may not retroactively alter `N`, `T_N`, `pi_train`, or P3 evidence.

## 5. Scoped target-training-order scientific authority

The definitions in this section formalize the accepted scoped owner `mlff_target_training_order_scientific_method.md`.

### D1.DEF.012 — Canonical target-training order

Given exact finite `P_train={x_1,...,x_n}`, the target-training order is one deterministic permutation

$$
\pi_{\mathrm{train}}=(x_{(1)},\ldots,x_{(n)}).
$$

For every configured candidate size `N` satisfying `1<=N<=n`, define

$$
T_N=\{x_{(1)},\ldots,x_{(N)}\}.
$$

The ordered prefix identity, not cardinality alone, defines candidate membership.

### D1.DER.001 — Exact nestedness

From D1.DEF.012, for `N_a<N_b`,

$$
T_{N_a}\subset T_{N_b}.
$$

No independent per-`N` membership selector is compatible with this definition.

### D1.DEF.013 — Authorized selector-evidence sigma-algebra

Let `E_train` denote information belonging to exact `P_train` plus authenticated partition-independent ancestors applicable to those frames. Define the authorized selector information set `I_sel` as the subset of `E_train` containing accepted structural/environment, pair-geometry/coordination, target-development response, applicable profile-selection, applicable frozen-foundation weakness, and hard-support evidence.

By definition, `I_sel` excludes `M3/M1/M2` labels or predictions, candidate outcomes, reducer outputs, post-selection CV/monitor, calibration/locked/challenge, and downstream deployment evidence.

### D1.AX.006 — Selector measurability axiom

`pi_train` and every selector-specific fitted quantity are measurable functions only of `I_sel` and accepted policy parameters. In particular, perturbing excluded evidence while holding `I_sel` and policy fixed must not change `pi_train`.

### D1.DEF.014 — Required family and reference measure

A required selector family `m` consists of a finite witness set `W_m`, an applicability domain, a fitted family metric/neighborhood relation supplied by D2, and normalized reference measure `mu_m` satisfying

$$
\mu_m(W_m)=1.
$$

Within each represented P1 correlation unit, witness masses sum to an equal unit share; witnesses within one unit divide that share.

### D1.DEF.015 — Family covered mass

For selected set `S subseteq P_train`, let `N_m(w)` be the authorized local neighborhood of witness `w`. Define

$$
C_m(S)=\mu_m\big(\{w\in W_m:N_m(w)\cap S\ne\varnothing\}\big).
$$

The accepted hard family-coverage parameter is currently `gamma_cov=0.95`. The family passes iff D2's exact numerical predicate for `C_m(S)>=gamma_cov` passes.

`gamma_cov` is a method-family parameter whose accepted current instance is `0.95`; no family-specific override is active in the accepted baseline.

### D1.DEF.016 — Extent support

For an extent-bearing scalar family coordinate with weighted reference quantiles `Q(0.01)` and `Q(0.99)`, selected set `S` has required extent support iff it contains applicable selected representatives reaching both the lower and upper reference sides under the D2 numerical tolerance.

### D1.DEF.017 — Hard-support obligation

A source hard-support obligation is the triple

$$
o=(L(o),A(o),k(o)),
$$

where `L(o)` is semantic support locus, `A(o) subseteq P_train` is exact candidate incidence, and `k(o)` is a positive integer minimum.

Locus identity excludes source-local IDs and minimum strength. Two source obligations may canonicalize into one obligation only if their accepted locus semantics are equal and their exact incidence sets are equal. The effective minimum for one locus `L` is

$$
k_\ast(L)=\max\{k(o):L(o)=L\}.
$$

A same-locus incidence/applicability disagreement is undefined authority and preparation must fail closed.

### D1.DEF.018 — Membership admissibility

For configured `N`, `T_N` is membership-admissible iff all of the following hold under one unchanged authority instance:

1. exact prefix `T_N` exists;
2. required training labels are usable;
3. every required family satisfies its hard coverage predicate;
4. every extent-bearing requirement passes;
5. every canonical hard-support obligation reaches its effective minimum.

Call this predicate `Q_mem(N)`.

### D1.DER.002 — Monotone membership qualification

Under fixed evidence, fixed neighborhoods, fixed obligations, and positive support/coverage predicates, if `N_a<N_b` and `Q_mem(N_a)` is true, then `Q_mem(N_b)` must also be true. Therefore `PASS -> FAIL` over increasing configured nested prefixes is a method-invariant violation.

### D1.AX.007 — Qualification/ranking separation axiom

`Q_mem` may reject inadmissible target memberships before training. Among memberships with `Q_mem=true`, it has no target-size ranking or tie-break authority; P3 target-force reducer semantics remain the sole automatic comparison authority.

### D1.AX.008 — Repair continuity axiom

Configured-shell repair may modify only the current newly added shell; every completed smaller configured prefix remains invariant. A repair is admissible only when it preserves canonical hard support, does not regress required-family coverage beyond D2 tolerance, and strictly improves the D2 repair objective. After the largest configured shell, the same target-order method continues until every `P_train` frame has a rank.

## 6. Training objectives and foundation adaptation

### D1.DEF.019 — Property-availability mask

For configuration `x` and property `p in {E,F,S}`, define `m_p(x) in {0,1}` as the local property-availability indicator under the canonical label contract. A zero mask means the property is unavailable for that objective term; it does not assert a zero physical property.

### D1.AX.009 — Method-specific objective axiom

P3 target-size screening and post-selection scratch retain their separately accepted weighted energy/force/stress objectives. Foundation-model post-selection adaptation (`naive_fine_tuning`, `multihead_replay`) uses the D2 robust energy/force/stress objective with global coefficient ratio `1:10:1`, binary property masks, no nontrivial per-configuration loss weight, and no target-versus-replay training-head scalar.

### D1.DEF.020 — Foundation identity

A foundation identity is

$$
\Phi=(\text{checkpoint identity},\text{head identity},\text{model family/version identity}).
$$

Any scientific quantity called a foundation residual, foundation reference, or pseudo-label is undefined unless its exact `Phi` is bound.

### D1.DEF.021 — Composition-weighted elemental correction estimand

For a target composition-count row vector `c` and elemental correction vector `delta e`, the scientifically consumed elemental-reference correction is

$$
\Delta E_0(c)=\mathbf c^T\delta\mathbf e.
$$

Let `N_free` be the unanchored null space of the authorized target-gradient-domain fit after applying any explicitly accepted prior/anchor. The correction for composition `c` is identifiable iff

$$
\mathbf c^T\mathbf v=0\quad\text{for every }\mathbf v\in N_{\mathrm{free}}.
$$

Individual elemental coefficients need not be unique when every governed `Delta E_0(c)` is unique.

### D1.AX.010 — Authorized E0 fit-domain axiom

Foundation-residual elemental corrections are fitted only from the authorized target gradient-training domain using the exact selected `Phi`. Monitor or held-out labels cannot resolve a null direction. If any governed target composition fails D1.DEF.021, the run/fold is scientifically infeasible absent an already accepted anchor.

## 7. Common monitor, cross-validation, and production

### D1.DEF.022 — Protected common target monitor

Let `P_mon` be the exact usable neutral `OUTER_MONITOR` parent population. Current foundation adaptation requires one deterministic common monitor

$$
M_{\mathrm{mon}}\subseteq P_{\mathrm{mon}},\qquad |M_{\mathrm{mon}}|=n_{\mathrm{mon}},
$$

with current default/required instance `n_mon=256` for this accepted method. `M_mon` supplies no gradients and must be protected-relation-disjoint from every configured `T_N` in the frozen experiment.

There is no silent smaller-monitor fallback in the accepted current instance.

### D1.DEF.023 — Post-selection fold partition

For frozen `T_N` and configured fold count `K>=2`, each fold `i` partitions `T_N` into disjoint gradient-training, held-out, and purge/exclusion subsets

$$
T_N=G_i\mathbin{\dot\cup}O_i\mathbin{\dot\cup}P_i,
$$

subject to protected-component allocation. `M_mon` is external to this partition. The current generated default is `K=3`; an explicit accepted policy may bind another `K>=2`.

### D1.DEF.024 — Foundation role-threshold family

Define the parameter family

$$
\Theta_{\mathrm{role}}=(\tau_{\mathrm{CV}},\theta_{\mathrm{CV}},\tau_{\mathrm{prod}}),
$$

where:

- `tau_CV` is the target-force checkpoint competence ceiling on `M_mon` during foundation CV;
- `theta_CV` is the held-out acceptance ceiling on `O_i` in the units of the configured outer metric;
- `tau_prod` is the target-force checkpoint-quality ceiling on `M_mon` during fresh production.

All three are independently configurable finite positive policy parameters. Current generated defaults for the default target-force outer metric are

$$
\tau_{\mathrm{CV}}=\theta_{\mathrm{CV}}=45\ \mathrm{meV/angstrom},
\qquad
\tau_{\mathrm{prod}}=30\ \mathrm{meV/angstrom}.
$$

Equality of the first two default numbers does not merge their estimands, populations, or evidence roles.

### D1.AX.011 — Fixed-budget CV consistency axiom

For every required `(fold, seed)` position, training runs to the frozen CV horizon; threshold crossing does not stop training. CV accepts only if every required position has an admissible frozen representative under the D2 checkpoint predicate and every representative satisfies the role's held-out predicate. Mean, majority, best-seed, or dispersion statistics cannot rescue a failing required position.

### D1.AX.012 — Fresh-production axiom

Fresh production starts a new model/optimizer lineage from the accepted foundation identity, trains on complete exact `T_selected`, fits training-dependent state on that complete authorized target membership, uses the same `M_mon` and shared checkpoint mechanics as CV, and applies `tau_prod` rather than `tau_CV`. P3 `M3` is not a production checkpoint monitor.

### D1.AX.013 — Downstream no-feedback axiom

Downstream deployment/runtime, physical-response, finite-temperature, calibration, locked-test, or release-qualification evidence consumes a frozen final publication. It cannot alter target size, target membership, training method, checkpoint choice, or final-publication membership after the applicable freeze boundary.

## 8. Parameter-family / instance / default ledger

The following material coordinates must never be represented as universal constants merely because the current default is stable:

| Family coordinate | Semantic role | Admissible family | Current/default instance | Owner |
| --- | --- | --- | --- | --- |
| `gamma_cov` | required-family hard coverage | `(0,1]` subject to accepted D1 change control | `0.95` | scoped D1/D2 target order |
| extent quantiles | lower/upper target-membership support | ordered quantile pair | `0.01, 0.99` | scoped D1/D2 target order |
| configured candidate ladder | tested target-size family | strictly increasing admissible sizes satisfying D2 structural policy | configuration-bound | P2/P3 policy |
| practical `epsilon` | target-size score equivalence | positive response-unit value | configuration-bound | P3 reducer policy |
| `K` | post-selection fold count | integer `>=2` | `3` | post-selection CV policy |
| `n_mon` | common target monitor size | positive integer supportable by `P_mon` | `256` in current method | foundation P5 method |
| `tau_CV` | CV checkpoint competence | finite positive target-force RMSE | `45 meV/angstrom` | CV role policy |
| `theta_CV` | CV held-out acceptance | finite positive value in configured outer-metric units | `45 meV/angstrom` for default force metric | CV role policy |
| `tau_prod` | production checkpoint quality | finite positive target-force RMSE | `30 meV/angstrom` | production role policy |
| robust global E:F:S | foundation-P5 property emphasis | accepted positive coefficient triple | `1:10:1` | foundation P5 D1 method |

A concrete run/evidence realization binds the resolved parameter values that affect its claim. Changing a role parameter invalidates only the evidence whose role policy materially depends on it unless a shared-method coordinate also changes.

## 9. Validity and undefined cases

The method returns a typed infeasibility/nonconformance rather than silently redefining itself when, among other accepted cases:

- compatible target labels cannot be formed;
- requested protected role allocation would split a protected component;
- exact required `M3` or `M_mon` membership cannot be realized;
- complete `P_train` cannot satisfy required target-order family/support policy;
- a configured target prefix fails `Q_mem`;
- a required composition-weighted elemental correction is non-identifiable;
- a required CV fold/seed is missing, fails, or has no admissible checkpoint;
- dependency/runtime behavior realizes a materially different objective, exposure, or method identity;
- non-finite required model/prediction/metric state prevents the declared estimand from being evaluated.

These cases do not authorize threshold widening, support relaxation, rescue-size invention, evidence-role substitution, or fabricated provider evidence.

## 10. Direct D1 definition dependencies

The authoritative bounded dependency trace is proposed in `MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE.md`. The principal D1 ordering is:

```text
D1.DEF.001 configuration
 -> D1.DEF.002 target label
 -> D1.DEF.003 label compatibility
 -> D1.AX.001 compatible target domain

D1.DEF.001 + project relation providers
 -> D1.DEF.005 protected relation
 -> D1.AX.002 protected-role separation
 -> D1.DEF.006 evidence-role map
 -> D1.AX.003 noninterference

D1.DEF.001 + D1.DEF.002 + D1.DEF.005 + D1.DEF.006
 -> D1.DEF.008 U_size/P_train/M3
 -> D1.DEF.012 pi_train/T_N
 -> D1.DEF.013 selector information
 -> D1.DEF.014 family/reference measure
 -> D1.DEF.015 coverage
 -> D1.DEF.017 hard obligation
 -> D1.DEF.018 membership admissibility

D1.DEF.020 foundation identity + authorized gradient domain
 -> D1.DEF.021 composition-weighted E0 correction

D1.DEF.005 + OUTER_MONITOR role
 -> D1.DEF.022 M_mon
D1.DEF.012 + D1.DEF.005
 -> D1.DEF.023 folds
D1.DEF.022 + D1.DEF.023
 -> D1.DEF.024 role-threshold family
```

## 11. D1 -> D2 handoff

D2 must provide a well-defined numerical concretization for every D1 object whose truth depends on numeric realization, including:

1. source/geometry/stress/strain numerical conventions and compatibility-sensitive normalization;
2. correlation estimator/truncation and protected-component realization;
3. exact `U_size -> P_train + M3` allocation and exact evaluation order;
4. exact `TargetCoverageReference`, weighted quantiles/scales, metric, radii, neighborhoods, coverage mass, extents, canonical obligations, FEAS1, MVSEL2, REPAIR2, and MVQUAL;
5. exact P3 optimizer-progress normalization, training/evaluation estimator, seed completeness, reducer, and practical-equivalence comparisons;
6. selected-head foundation-residual E0 least-squares problem, numerical rank/null-space interpretation, and composition-transfer test;
7. exact robust foundation-P5 Huber objective, dimensional thresholds, reductions, masks, and target/replay exposure;
8. deterministic `M_mon` sampler and exact protected-separation checks;
9. deterministic CV component partition/purge semantics;
10. shared checkpoint constraints, role-effective `tau_CV/theta_CV/tau_prod` predicates, boundary behavior, and all-required-position aggregation;
11. typed numerical failure, precision, equivalence, restart/reconstruction, and verification oracles.

D2 may optimize implementation only within numerical equivalence to these D1 semantics. Any D2 need to change an estimand, evidence role, policy-family meaning, support predicate, or validity regime is a D1 Challenge rather than a downstream repair.

## 12. Acceptance condition for this overlay

This overlay is acceptable only if independent review demonstrates that every definition/axiom above is either (a) a lossless formalization of accepted basis semantics or (b) an explicitly identified scientific correction separately ratified by the stakeholder. Unreviewed strengthening, newly excluded regimes, changed defaults, or changed owner boundaries are blockers.
