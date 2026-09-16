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

## 1. Authority and semantic roles

This file is a proposed Protocol-6.4 formalization overlay for the accepted MLFF D1 authority at basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. It is not accepted-current authority until fresh independent D1/D2 review passes and the stakeholder ratifies the exact candidate.

If ratified, this file is the formal-first entry point; the two accepted D1 method papers remain explanatory, provenance, uncertainty, application, and historical context. Any material conflict is a review blocker rather than an implicit override.

The terms **definition**, **axiom**, **derived invariant**, **empirical claim**, **policy parameter**, and **default** are distinct. An axiom below is a project-governing scientific premise, not a theorem about nature. A default is a generated parameter value, not a universal constant.

## 2. Foundational objects

### D1.DEF.001 — Atomic configuration

An atomic configuration is

$$
x=(\mathbf Z,\mathbf R,\mathbf H,\mathbf p),
$$

where `Z=(Z_1,...,Z_n)` is the ordered atomic-number vector, `R` the ordered Cartesian position matrix in `angstrom`, `H` the periodic cell under the accepted ASE row-vector convention, and `p` the periodicity/source-occurrence metadata needed to interpret the frame. Occurrence identity and geometry identity are distinct.

Malformed atom counts, non-finite coordinates, or an invalid cell when required make the configuration ineligible under the active source policy.

### D1.DEF.002 — Canonical target label statement

For eligible `x`,

$$
y(x)=\big(E(x),\mathbf F(x),\boldsymbol\sigma(x);\lambda(x)\big),
$$

where `E` is total energy, `F` ordered Cartesian forces, `sigma` symmetric Cartesian Cauchy stress when present, and `lambda` binds theory/electronic-structure identity, energy reference, derivative/stress convention, units, numerical-quality profile, and compatibility-significant provenance. Missing optional properties are absent, not numerically zero.

### D1.DEF.003 — Label compatibility

For canonical label statements,

$$
y_a\sim_{\mathrm{label}}y_b
$$

iff all compatibility-significant coordinates agree under the accepted source-compatibility policy. Differences explicitly declared non-semantic by that policy do not alone break compatibility.

### D1.AX.001 — Compatible target-domain axiom

A target training/evaluation population consumed as one scientific target domain contains only labels from one `~_label` compatibility class. Replay, when enabled, is a separately identified lineage.

### D1.DEF.004 — Energy-conserving model family

The accepted MLFF model family represents

$$
E_\theta(\mathbf Z,\mathbf R,\mathbf H),
$$

with governed derivatives

$$
\mathbf F_i=-\frac{\partial E_\theta}{\partial\mathbf R_i},
$$

$$
\boldsymbol\sigma=-\frac1V\frac{\partial E_\theta}{\partial\boldsymbol\varepsilon}
$$

under the accepted source convention. Implementation of differentiation is downstream; the scientific relation is D1 authority.

## 3. Dependence and evidence roles

### D1.DEF.005 — Protected relation

For finite eligible frame universe `U`, let `R_prot` be the union of accepted primitive inseparability relations: correlation-unit co-membership, exact geometry duplication, protected-event co-membership, condition-scoped replica lineage, and condition-scoped structural-realization lineage where available.

Let `TC(R_prot)` denote the reflexive-symmetric-transitive closure function defined in this paragraph. The protected equivalence relation is

$$
\sim_{\mathrm{prot}}=\mathrm{TC}(R_{\mathrm{prot}}).
$$

### D1.DEF.006 — Evidence-role map

An evidence-role map is

$$
r:U\rightarrow\mathcal R,
$$

where `R` contains accepted development/gradient, checkpoint-monitor, post-selection held-out, calibration, locked/challenge, purge/excluded, and other governed roles. `Perm(role)` is the set of operations authorized to consume labels from that role.

### D1.AX.002 — Protected-role separation axiom

Frames in one `~_prot` class cannot be assigned to roles that the governing method requires to be mutually independent or mutually exclusive.

### D1.AX.003 — Evidence noninterference axiom

If operation `a` is not in `Perm(r(x))`, information from frame `x` cannot influence `a`, directly or through fitted state or descendants. Held-out labels cannot choose checkpoints; monitor labels cannot fit training state; locked evidence cannot choose target/final membership; P3 outcomes cannot feed backward into `pi_train`.

### D1.DEF.007 — Correlation diagnostic

For stationary scalar observable `X_t` with finite variance,

$$
\rho(k)=\frac{\mathrm{Cov}(X_t,X_{t+k})}{\mathrm{Var}(X_t)},
$$

$$
\tau_{\mathrm{int}}=\frac12+\sum_{k=1}^{k^\star}\rho(k),
$$

and

$$
N_{\mathrm{eff}}=\min\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
$$

D2 owns the truncation estimator. `N_eff` diagnoses redundancy for the chosen observable; it is not proof of full slow-state independence.

## 4. Target-size experiment

### D1.DEF.008 — Target-size population and exact split

`U_size` is the exact eligible neutral-development population with canonical training labels. It is partitioned once as

$$
U_{\mathrm{size}}=P_{\mathrm{train}}\mathbin{\dot\cup}M_3,
$$

without splitting an applicable protected component. `P_train` supplies candidate target memberships; `M3` is the largest P3 evaluation reserve.

### D1.AX.004 — Target-size controlled-variable axiom

Within one target-size experiment, candidate cardinality `N` changes only the exact target prefix `T_N` and downstream consequences of adding those frames. Pre-order evidence authority, membership rule, P3-common fitted preparation, seed population, fidelity schedule, evaluation ladder, objective, and reducer policy remain candidate-independent unless an explicitly accepted method coordinate says otherwise.

### D1.DEF.009 — Evaluation ladder

A deterministic permutation `pi_eval` of `M3` defines

$$
M_i=\pi_{\mathrm{eval}}[:m_i].
$$

Thus `m_i<m_j` gives exact prefix nesting `M_i subset M_j`. These are P3 model-selection populations, not post-selection held-out folds or checkpoint monitors.

### D1.DEF.010 — Primary P3 response

For `K>0` admitted Cartesian force components,

$$
\mathrm{RMSE}_F=\sqrt{\frac1K\sum_{k=1}^{K}
\left(F_k^{\mathrm{pred}}-F_k^{\mathrm{ref}}\right)^2}.
$$

The current P3 stored response is in `meV/angstrom`; D2 owns conversion and non-finite failure semantics.

### D1.DEF.011 — Practical-equivalence family

`epsilon>0` is the configured material force-error difference for the reducer, in response units. It is a policy parameter, not machine epsilon. D2 owns the exact reducer relation using `epsilon`.

### D1.AX.005 — Recommendation/decision separation axiom

The P3 reducer produces evidence/recommendation. The operator owns the provisional downstream design within the qualified configured set. Post-selection CV can accept/reject that frozen design but cannot retroactively alter `N`, `T_N`, `pi_train`, or P3 evidence.

## 5. Scoped target-training-order authority

### D1.DEF.012 — Canonical target-training order

For exact finite `P_train={x_1,...,x_n}`, define one deterministic permutation

$$
\pi_{\mathrm{train}}=(x_{(1)},\ldots,x_{(n)}).
$$

For configured `1<=N<=n`,

$$
T_N=\{x_{(1)},\ldots,x_{(N)}\}.
$$

Ordered prefix identity, not cardinality alone, defines candidate membership.

### D1.DER.001 — Exact nestedness

From D1.DEF.012, `N_a<N_b` implies

$$
T_{N_a}\subset T_{N_b}.
$$

An independent per-`N` selector contradicts the definition.

### D1.DEF.013 — Authorized selector information

`I_sel` consists only of exact-`P_train` information or authenticated partition-independent ancestors applicable to those frames that belong to accepted structural/environment, pair-geometry/coordination, target-development response, applicable profile-selection, applicable frozen-foundation weakness, or hard-support evidence.

`I_sel` excludes `M3/M1/M2` labels or predictions, candidate outcomes, reducer outputs, post-selection monitor/CV, calibration/locked/challenge, and downstream deployment evidence.

### D1.AX.006 — Selector measurability axiom

`pi_train` and selector-specific fitted quantities are functions only of `I_sel` and accepted policy parameters. Perturbing excluded evidence while holding those inputs fixed cannot change `pi_train`.

### D1.DEF.014 — Required family and reference measure

Required family `m` consists of finite witness set `W_m`, applicability domain, D2-owned fitted metric/neighborhood relation, and normalized reference measure `mu_m` with

$$
\mu_m(W_m)=1.
$$

Each represented P1 correlation unit receives equal family mass; witnesses inside a unit divide that mass.

### D1.DEF.015 — Family covered mass

For selected `S subseteq P_train` and authorized local witness neighborhood `N_m(w)`,

$$
C_m(S)=\mu_m\big(\{w\in W_m:N_m(w)\cap S\ne\varnothing\}\big).
$$

Current hard coverage family parameter is `gamma_cov=0.95`; the exact comparison tolerance is D2 authority. No named-family override is active in the accepted baseline.

### D1.DEF.016 — Extent support

For an extent-bearing scalar coordinate, selected support must reach both weighted reference quantiles `Q(0.01)` and `Q(0.99)` under the D2 numerical tolerance. These are membership-support requirements, not accuracy/deployment thresholds.

### D1.DEF.017 — Hard-support obligation

A source obligation is

$$
o=(L(o),A(o),k(o)),
$$

where `L(o)` is semantic support locus, `A(o) subseteq P_train` exact incidence, and `k(o)` a positive integer minimum. Source IDs and strength are not locus identity.

Same-locus obligations may canonicalize only when exact incidence and accepted applicability/provider semantics agree; effective minimum is

$$
k_\ast(L)=\max\{k(o):L(o)=L\}.
$$

Same-locus disagreement fails closed. Incidence equality alone does not merge distinct loci.

### D1.DEF.018 — Membership admissibility

For configured `N`, predicate `Q_mem(N)` is true iff exact `T_N` exists, labels are training-usable, every required family passes hard coverage, every required extent passes, and every canonical hard obligation meets its effective minimum.

### D1.DER.002 — Qualification monotonicity

Under fixed evidence/neighborhoods/obligations and positive support predicates, exact prefix nesting implies that once `Q_mem(N)` passes, every larger configured prefix must pass. `PASS -> FAIL` is an invariant violation.

### D1.AX.007 — Qualification/ranking separation axiom

`Q_mem` gates membership before training. Among qualified candidates it has no ranking/tie authority; P3 target-force reducer semantics remain the automatic size-comparison owner.

### D1.AX.008 — Repair continuity axiom

Configured-shell repair may alter only the newly added shell, preserves all completed smaller configured prefixes, preserves canonical hard support, does not regress required-family coverage beyond D2 tolerance, and must strictly improve the D2 repair objective. After the largest configured shell, the same method continues until every `P_train` frame is ranked.

## 6. Foundation adaptation and atomic references

### D1.DEF.019 — Property-availability mask

For property `p in {E,F,S}`, `m_p(x) in {0,1}` denotes availability under the canonical label contract. Zero means unavailable for that term, not physically zero.

### D1.AX.009 — Method-specific objective axiom

P3 target-size screening and post-selection scratch retain their accepted weighted objectives. Foundation post-selection adaptation (`naive_fine_tuning`, `multihead_replay`) uses the D2 robust E/F/S objective with global coefficients `1:10:1`, binary masks, no nontrivial per-configuration loss weight, and no target/replay training-head scalar.

### D1.DEF.020 — Foundation identity

$$
\Phi=(\text{checkpoint identity},\text{head identity},\text{model/version identity}).
$$

Foundation residuals, references, or pseudo-labels are undefined unless exact `Phi` is bound.

### D1.DEF.021 — Composition-weighted E0 correction

For composition-count row vector `c` and elemental correction `delta e`,

$$
\Delta E_0(\mathbf c)=\mathbf c^T\delta\mathbf e.
$$

Let `N_free` be the unanchored null space of the authorized fit after explicit accepted anchors. `Delta E_0(c)` is identifiable iff

$$
\mathbf c^T\mathbf v=0
\quad\text{for every }\mathbf v\in N_{\mathrm{free}}.
$$

Individual elemental corrections need not be unique if every governed composition-weighted correction is unique.

### D1.AX.010 — Authorized E0 fit-domain axiom

Foundation-residual corrections are fitted only from the authorized target gradient domain using exact `Phi`. Monitor/held-out labels cannot resolve null directions. A governed composition that fails D1.DEF.021 makes that run/fold infeasible absent an already accepted anchor.

## 7. Common monitor, CV, and production

### D1.DEF.022 — Common target monitor

For usable protected neutral `OUTER_MONITOR` parent `P_mon`, current foundation adaptation requires deterministic

$$
M_{\mathrm{mon}}\subseteq P_{\mathrm{mon}},
\qquad |M_{\mathrm{mon}}|=n_{\mathrm{mon}},
$$

with current method instance `n_mon=256`. `M_mon` supplies no gradients and is protected-relation-disjoint from every configured target prefix in the frozen experiment. No silent smaller-monitor fallback exists.

### D1.DEF.023 — Post-selection fold partition

For frozen `T_N`, each CV fold `i` partitions

$$
T_N=G_i\mathbin{\dot\cup}O_i\mathbin{\dot\cup}P_i,
$$

into gradient, held-out, and purge/exclusion membership by protected components. `M_mon` is external. Fold count `K` is a policy parameter with family `K>=2` and current generated default `3`.

### D1.DEF.024 — Foundation role-threshold family

$$
\Theta_{\mathrm{role}}=(\tau_{\mathrm{CV}},\theta_{\mathrm{CV}},\tau_{\mathrm{prod}}).
$$

`tau_CV` is target-force checkpoint competence on `M_mon`; `theta_CV` is held-out acceptance on `O_i` in configured outer-metric units; `tau_prod` is target-force checkpoint quality on `M_mon` for production. They are independently configurable finite positive parameters. Current generated defaults for the default force outer metric are

$$
\tau_{\mathrm{CV}}=\theta_{\mathrm{CV}}=45\ \mathrm{meV/angstrom},
\qquad
\tau_{\mathrm{prod}}=30\ \mathrm{meV/angstrom}.
$$

Equal default numeric values do not merge estimands or populations.

### D1.AX.011 — Fixed-budget CV consistency axiom

Every required `(fold,seed)` position trains to the frozen horizon; threshold crossing does not stop training. CV accepts only if every required position has an admissible frozen representative and every representative passes the outer predicate. Mean/majority/best-seed/dispersion cannot rescue a failing required position.

### D1.AX.012 — Fresh-production axiom

Fresh production starts a new model/optimizer lineage from accepted `Phi`, trains on complete exact `T_selected`, fits training-dependent state only on that authorized target membership, uses the same `M_mon` and shared checkpoint mechanics as CV, and applies `tau_prod` rather than `tau_CV`. P3 `M3` has no production checkpoint role.

### D1.AX.013 — Downstream no-feedback axiom

Downstream physical/deployment/calibration/locked/release evidence consumes a frozen final publication and cannot alter target size/membership, training method, checkpoint choice, or final-publication membership after the applicable freeze boundary.

## 8. Parameter family / instance / default ledger

| Coordinate | Family meaning | Current/default instance | Authority |
| --- | --- | --- | --- |
| `gamma_cov` | required-family hard coverage | `0.95` | scoped target-order D1/D2 |
| extent quantiles | target-membership lower/upper support | `0.01, 0.99` | scoped target-order D1/D2 |
| candidate ladder | tested target-size family | configuration-bound strictly increasing admissible sizes | P2/P3 policy |
| practical `epsilon` | material P3 response difference | configuration-bound positive value | P3 reducer |
| CV `K` | fold-count family | default `3`, explicit `K>=2` | CV policy |
| `n_mon` | common monitor size | `256` current method | foundation P5 method |
| `tau_CV` | CV checkpoint competence | default `45 meV/angstrom` | CV role policy |
| `theta_CV` | held-out acceptance | default `45 meV/angstrom` for default force metric | CV role policy |
| `tau_prod` | production checkpoint quality | default `30 meV/angstrom` | production role policy |
| E:F:S coefficients | foundation-P5 property emphasis | `1:10:1` | foundation-P5 method |

A concrete evidence item binds the resolved values material to its claim. Role-parameter changes invalidate dependent role evidence, not unrelated authority by default.

## 9. Validity and typed infeasibility

The method fails/defers instead of redefining itself when required compatible labels cannot be formed; protected allocation would split a protected component; exact required reserve/monitor membership is unrealizable; complete `P_train` cannot satisfy required membership policy; a configured prefix fails `Q_mem`; a governed E0 composition is non-identifiable; a required CV position is missing/fails/has no admissible checkpoint; or runtime realizes a materially different objective/exposure/method.

These cases do not authorize threshold widening, support relaxation, rescue-size invention, role substitution, or fabricated evidence.

## 10. D1 -> D2 contract

D2 must concretize, without changing meaning:

1. source/geometry/stress/strain conventions and protected statistical units;
2. exact `U_size -> P_train + M3` split and `pi_eval`;
3. exact target-order weighted measures, metric/radii/adjacency, coverage/extents, obligations, FEAS1, MVSEL2, REPAIR2, and MVQUAL;
4. P3 optimizer-progress normalization, evaluation estimator, complete-seed reducer, and practical equivalence;
5. selected-head foundation-residual E0 fit and null-space transfer test;
6. robust foundation-P5 loss with dimensional thresholds/reductions and exact exposure semantics;
7. deterministic common-monitor construction/protected separation;
8. deterministic CV folds/purge;
9. shared checkpoint constraints and role-effective threshold predicates/currentness;
10. typed failure, precision/equivalence, continuation, and falsification oracles.

The companion trace `MLFF_D1_D2_SSDP64_DEFINITION_DEPENDENCY_TRACE.md` records direct `USES_DEFINITION` edges. Any D2 need to change an estimand, evidence role, support predicate, parameter-family meaning, or validity regime is an upward D1 Challenge.

## 11. Acceptance condition

Independent review must show every object above is a lossless formalization of accepted basis semantics, or separately identify and route any genuine scientific correction for stakeholder ratification. Newly excluded regimes, changed defaults, changed owner boundaries, or strengthened claims are blockers if they were not explicitly accepted.
