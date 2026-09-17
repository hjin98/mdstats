---
kind: proposed-D1-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_R2_AWAITING_INDEPENDENT_REVIEW_AND_STAKEHOLDER_RATIFICATION
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
repairs_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R1.md
supersedes_proposed_candidate_only: workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE.md
would_compose_with:
  - docs/methods/mlff_scientific_method.md
  - docs/methods/mlff_target_training_order_scientific_method.md
---

# Proposed MLFF D1 axiomatic authority kernel — R2

## 1. Authority, exact sources, and semantic roles

This file is a repaired Protocol-6.4 formalization overlay for the accepted MLFF D1 authority at repository `hjin98/mdstats`, accepted basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. It remains proposed until a fresh independent D1/D2 R2 review passes and the stakeholder ratifies the exact reviewed candidate.

The immutable accepted D1 sources are:

- `D1.SRC.GENERAL` = `hjin98/mdstats@cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824:docs/methods/mlff_scientific_method.md`;
- `D1.SRC.ORDER` = `hjin98/mdstats@cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824:docs/methods/mlff_target_training_order_scientific_method.md`.

A section-qualified reference to one of those sources is an exact specialized import. The scoped target-order owner `D1.SRC.ORDER` supersedes conflicting target-order construction/qualification prose in the general paper; all unaffected scientific semantics remain owned by `D1.SRC.GENERAL`.

Definitions stipulate meaning. Axioms below are project-governing scientific premises already present in accepted authority, not empirical theorems. Derived invariants follow from definitions/axioms. Defaults are parameter bindings owned by policy/configuration and do not become universal constants by appearing here.

For material parameterization, use the binding classes:

- `FIXED_METHOD_COORDINATE`: changing the value changes the accepted method;
- `CONFIGURABLE_FAMILY`: an admissible value is explicitly supplied under the stated domain;
- `CONFIGURABLE_WITH_GENERATED_DEFAULT`: the family is configurable and a current generated default is separately owned;
- `DERIVED`: computed from other governed objects and not independently configurable.

## 2. Foundational scientific objects

### D1.DEF.001 — Atomic configuration

An atomic configuration is

$$
x=(\mathbf Z,\mathbf R,\mathbf H,\mathbf p),
$$

where `Z=(Z_1,...,Z_n)` is the ordered atomic-number vector, `R` is the ordered Cartesian position matrix, `H` is the periodic cell under the accepted ASE row-vector convention, and `p` contains periodicity and source-occurrence metadata required to interpret the frame. Occurrence identity and geometry identity are distinct.

Malformed atom counts, non-finite coordinates, or an invalid required cell make the configuration ineligible under the active source policy.

### D1.DEF.002 — Canonical target label statement

For eligible `x`,

$$
y(x)=\big(E(x),\mathbf F(x),\boldsymbol\sigma(x);\lambda(x)\big),
$$

where `E` is total energy, `F` ordered Cartesian forces, `sigma` symmetric Cartesian Cauchy stress when present, and `lambda` binds theory/electronic-structure identity, energy reference, derivative/stress convention, units, numerical-quality profile, and compatibility-significant provenance. Missing optional properties are absent, not numerical zero.

### D1.DEF.003 — Label compatibility

For canonical label statements,

$$
y_a\sim_{\mathrm{label}}y_b
$$

iff all compatibility-significant coordinates agree under `D1.SRC.GENERAL`, Section 3.2, including theory/electronic-structure identity, energy-reference identity, derivative/stress convention, and numerical-quality profile, modulo differences explicitly declared non-semantic by that accepted source policy.

### D1.AX.001 — Compatible target-domain axiom

A target training/evaluation population consumed as one scientific target domain contains only labels from one `~_label` compatibility class. Replay, when enabled, is a separately identified lineage.

### D1.DEF.004 — Energy-conserving model and physical convention

The accepted MLFF model family represents

$$
E_\theta(\mathbf Z,\mathbf R,\mathbf H),
$$

with

$$
\mathbf F_i=-\frac{\partial E_\theta}{\partial\mathbf R_i},
$$

and, when stress is governed,

$$
\boldsymbol\sigma=-\frac{1}{V}\frac{\partial E_\theta}{\partial\boldsymbol\varepsilon}.
$$

The row-cell, deformation/strain, stress sign, tensor/shear, Voigt, unit, and reference-cell meanings are exact specialized imports from `D1.SRC.GENERAL`, Sections 3.5 and 3.6. They are part of label/model interpretation rather than downstream software preference.

## 3. Protected dependence, roles, and statistical interpretation

### D1.DEF.005 — Protected relation

For finite eligible frame universe `U`, let `R_prot` be the union of accepted primitive inseparability relations: correlation-unit co-membership, exact geometry duplication, protected-event co-membership, condition-scoped replica lineage, and condition-scoped structural-realization lineage when available.

Let `TC` be the reflexive-symmetric-transitive closure on binary relations over `U`. Define

$$
\sim_{\mathrm{prot}}=\mathrm{TC}(R_{\mathrm{prot}}).
$$

### D1.DEF.006 — Evidence-role and permission system

Let `R_role` be the finite governed role vocabulary containing at least development/gradient, P3 model-selection evaluation, checkpoint/model-control monitor, post-selection held-out evaluation, uncertainty calibration when active, locked/challenge evidence when active, purge/excluded, and replay-specific roles where enabled.

Let `A_op` be the governed operation universe containing at least target-membership construction, gradient fitting, fitted-transform construction, atomic-reference fitting, checkpoint choice, held-out evaluation, calibration design/application, locked evaluation, final-publication membership choice, and downstream qualification.

The role map and permission map are

$$
r:U\rightarrow R_{\mathrm{role}},
$$

$$
\mathrm{Perm}:R_{\mathrm{role}}\rightarrow 2^{A_{\mathrm{op}}}.
$$

The exact role meanings and permissions are specialized imports from `D1.SRC.GENERAL`, Sections 4.4-4.6. A role name alone does not authorize an operation; authorization is membership in `Perm(r(x))` under the applicable accepted method.

### D1.AX.002 — Protected-role separation axiom

Frames in one `~_prot` class cannot be assigned to roles that the governing method requires to be mutually independent or mutually exclusive.

### D1.AX.003 — Evidence noninterference axiom

For frame `x` and operation `a`, if

$$
a\notin\mathrm{Perm}(r(x)),
$$

then information from `x` cannot influence `a`, directly or through fitted state or descendants. In particular: held-out labels cannot choose checkpoints; monitor labels cannot fit training state; locked evidence cannot choose target/final membership; calibration cannot tune the protocol it evaluates; and P3 outcomes cannot feed backward into `pi_train`.

### D1.DEF.007 — Correlation diagnostic estimand

For stationary scalar observable `X_t` with finite variance,

$$
\rho(k)=\frac{\mathrm{Cov}(X_t,X_{t+k})}{\mathrm{Var}(X_t)},
$$

$$
\tau_{\mathrm{int}}=\frac12+\sum_{k=1}^{k^\star}\rho(k),
$$

$$
N_{\mathrm{eff}}=\min\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
$$

D2 owns the finite-sequence autocorrelation estimator and truncation rule. `N_eff` diagnoses serial redundancy for the chosen observable; it is not proof of independence of every slow state.

## 4. Target-size experiment

### D1.DEF.008 — Target-size population and exact split

`U_size` is the exact eligible neutral `DEVELOPMENT` population with canonical training labels. It is partitioned once as

$$
U_{\mathrm{size}}=P_{\mathrm{train}}\mathbin{\dot\cup}M_3,
$$

without splitting an applicable `~_prot` component. `P_train` supplies target candidates; `M3` is the largest P3 evaluation reserve.

### D1.DEF.009 — Target-size policy family

A target-size screening policy binds:

- configured candidate sizes `N_cfg`;
- configured evaluation sizes `M_cfg`;
- configured fidelity boundaries `H_cfg`;
- one ordered optimizer-seed population `S_seed`;
- practical-equivalence parameter `epsilon`;
- the accepted reducer/funnel family and optimizer-normalization policy.

The current admissible structural domain is exact-imported from `D1.SRC.GENERAL` target-size semantics and concretized by D2: at least three strictly increasing candidate sizes, exactly three evaluation sizes, exactly three fidelity boundaries, and one ordered seed population. D2 owns the current numerical power-of-two/positivity/uniqueness restrictions and exact funnel.

### D1.AX.004 — Target-size controlled-variable axiom

Within one target-size experiment, candidate cardinality `N` changes only exact target prefix `T_N` and downstream consequences of adding those frames. Pre-order evidence authority, membership rule, P3-common fitted preparation, seed population, fidelity schedule, evaluation ladder, objective, and reducer policy remain candidate-independent unless an explicitly accepted method coordinate says otherwise.

### D1.DEF.010 — Evaluation ladder

A deterministic permutation `pi_eval` of exact `M3` defines

$$
M_i=\pi_{\mathrm{eval}}[:m_i].
$$

Thus `m_i<m_j` implies exact prefix nesting `M_i subset M_j`. These are P3 model-selection populations, not post-selection held-out folds or checkpoint monitors. D2 owns the condition-balanced construction of `pi_eval`.

### D1.DEF.011 — Primary P3 response

For `K>0` admitted Cartesian force components,

$$
\mathrm{RMSE}_F=\sqrt{\frac1K\sum_{k=1}^{K}
\left(F_k^{\mathrm{pred}}-F_k^{\mathrm{ref}}\right)^2}.
$$

The stored P3 response is `meV/angstrom`; D2 owns conversion, aggregation, and non-finite failure semantics.

### D1.DEF.012 — Practical-equivalence family

`epsilon>0` is the configured material P3 force-error difference in response units. It is a `CONFIGURABLE_FAMILY` parameter, not machine epsilon. D2 owns the exact practical-equivalence and reducer relation using `epsilon`.

### D1.AX.005 — Automatic-comparison sufficiency and recommendation separation

Automatic screening requires the accepted minimum number of qualified configured candidates and then produces diagnostic evidence/recommendation under the accepted reducer. The operator owns the provisional downstream design within the qualified configured set. Post-selection CV can accept/reject that frozen design but cannot retroactively alter `N`, `T_N`, `pi_train`, or P3 evidence.

## 5. Scoped target-training-order authority

### D1.DEF.013 — Canonical target-training order

For exact finite `P_train={x_1,...,x_n}`, define one deterministic permutation

$$
\pi_{\mathrm{train}}=(x_{(1)},\ldots,x_{(n)}).
$$

For configured `1\le N\le n`,

$$
T_N=\{x_{(1)},\ldots,x_{(N)}\}.
$$

Ordered prefix identity, not cardinality alone, defines candidate membership.

### D1.DER.001 — Exact nestedness

From D1.DEF.013, `N_a<N_b` implies

$$
T_{N_a}\subset T_{N_b}.
$$

An independent per-`N` selector contradicts the method.

### D1.DEF.014 — Authorized selector information

`I_sel` consists only of exact-`P_train` information or authenticated partition-independent ancestors applicable to those frames belonging to accepted structural/environment, pair-geometry/coordination, target-development response, applicable profile-selection, applicable frozen-foundation weakness, and hard-support evidence.

`I_sel` excludes `M3/M1/M2` labels or predictions, target-size candidate outcomes, reducer outputs, post-selection monitor/CV, calibration/locked/challenge evidence, and downstream deployment evidence.

### D1.AX.006 — Selector measurability axiom

`pi_train` and selector-specific fitted quantities are functions only of `I_sel` and accepted policy parameters. Perturbing excluded evidence while holding those inputs fixed cannot change `pi_train`.

### D1.DEF.015 — Required target-order family roles and applicability

Required family roles are the union, under the applicability rules of `D1.SRC.ORDER`, Sections 3-4, of:

1. universal local structure/environment families;
2. pair geometry and coordination families;
3. target-development force/energy/thermodynamic/strain/stress response families defined by accepted training evidence;
4. profile-selection families only when an accepted active profile provider explicitly supplies selection-stage features/environment classes;
5. foundation residual/weakness families only when the target-size protocol itself uses an authenticated frozen foundation checkpoint.

A provider absent from the current protocol contributes no family and is not acquired merely to populate the selector. D2 owns the exact family names, coordinates, extent flags, and provider-valid-row rules.

For required family `m`, let `W_m` be its finite witness set and `mu_m` its normalized empirical reference measure. Each represented P1 correlation unit receives equal total family mass and witnesses inside that unit divide that mass.

### D1.DEF.016 — Family covered mass

For selected `S subseteq P_train` and authorized local witness neighborhood `N_m(w)`,

$$
C_m(S)=\mu_m\big(\{w\in W_m:N_m(w)\cap S\ne\varnothing\}\big).
$$

The hard coverage coordinate is

$$
\gamma_{\mathrm{cov}}=0.95,
$$

with binding class `FIXED_METHOD_COORDINATE`. There is no active named-family override in the accepted baseline. D2 owns the distinct selector and qualification floating comparison tolerances.

### D1.DEF.017 — Extent support

For every extent-bearing scalar coordinate, selected support must reach both weighted reference quantiles

$$
q_{\mathrm{lo}}=0.01,
\qquad
q_{\mathrm{hi}}=0.99,
$$

under D2 numerical tolerances. The quantile coordinates are `FIXED_METHOD_COORDINATE`. They are membership-support requirements, not accuracy/deployment thresholds.

### D1.DEF.018 — Hard-support obligation

A source obligation is

$$
o=(L(o),A(o),k(o)),
$$

where `L(o)` is semantic support locus, `A(o) subseteq P_train` exact incidence, and `k(o)` a positive integer minimum. Source IDs and strength are not locus identity.

Automatic obligations apply, where relevant, to represented P2 conditions, P1 correlation units, recognized structural-event types, active profile environment classes, and both sides of every required extent-bearing channel. Explicit current hard-support policy may strengthen an automatic locus.

Same-locus obligations canonicalize only when accepted locus/applicability/provider semantics and exact incidence agree. Their effective minimum is

$$
k_\ast(L)=\max\{k(o):L(o)=L\}.
$$

Same-locus disagreement fails closed. Incidence equality alone does not merge distinct loci.

### D1.DEF.019 — Membership admissibility

For configured `N`, predicate `Q_mem(N)` is true iff exact `T_N` exists, labels are training-usable, every required family passes hard coverage, every required extent passes, and every canonical hard obligation meets its effective minimum.

### D1.DER.002 — Qualification monotonicity

Under fixed evidence/neighborhoods/obligations and positive support predicates, exact prefix nesting implies that once `Q_mem(N)` passes, every larger configured prefix must pass. `PASS -> FAIL` is an invariant violation.

### D1.AX.007 — Qualification/ranking separation axiom

`Q_mem` gates membership before training. Among qualified candidates it has no ranking/tie authority; P3 target-force reducer semantics remain the automatic size-comparison owner.

### D1.AX.008 — Repair continuity axiom

Configured-shell repair may alter only the newly added shell, preserves all completed smaller configured prefixes, preserves canonical hard support, does not regress required-family coverage beyond D2 tolerance, and must strictly improve the D2 repair objective. After the largest configured shell, the same multi-view method continues until every `P_train` frame is ranked; there is no unconfigured repair shell or alternate suffix selector.

## 6. Foundation adaptation, atomic references, and replay

### D1.DEF.020 — Property-availability mask

For property `p in {E,F,S}`, `m_p(x) in {0,1}` denotes availability under the canonical label contract. Zero means unavailable for that term, not physically zero.

### D1.AX.009 — Method-specific objective axiom

P3 target-size screening and post-selection scratch retain their accepted weighted objectives. Foundation post-selection adaptation (`naive_fine_tuning`, `multihead_replay`) uses the D2 robust E/F/S objective with fixed global coefficients `1:10:1`, binary masks, no nontrivial per-configuration loss weight, and no target/replay training-head scalar.

### D1.DEF.021 — Foundation identity

$$
\Phi=(\text{checkpoint identity},\text{head identity},\text{model/version identity}).
$$

Foundation residuals, references, or pseudo-labels are undefined unless exact `Phi` is bound.

### D1.DEF.022 — Composition-weighted E0 correction

For composition-count row vector `c` and elemental correction `delta e`,

$$
\Delta E_0(\mathbf c)=\mathbf c^T\delta\mathbf e.
$$

Let `N_free` be the unanchored null space of the authorized fit after explicit accepted anchors. `Delta E_0(c)` is identifiable iff

$$
\mathbf c^T\mathbf v=0
\quad\text{for every }\mathbf v\in N_{\mathrm{free}}.
$$

Individual elemental corrections need not be unique when every governed composition-weighted correction is unique.

### D1.AX.010 — Authorized E0 fit-domain axiom

Foundation-residual corrections are fitted only from the authorized target gradient domain using exact `Phi`. Monitor/held-out labels cannot resolve null directions. A governed composition that fails D1.DEF.022 makes that run/fold infeasible absent an already accepted anchor.

### D1.DEF.023 — Replay label-mode family

For post-selection `multihead_replay`, define replay label mode

$$
\ell_{\mathrm{replay}}\in\{\mathrm{TRUE\_REFERENCE},\mathrm{FOUNDATION\_PSEUDO}\}.
$$

`TRUE_REFERENCE` is the canonical default when the replay source supplies canonical true-reference/DFT labels. `FOUNDATION_PSEUDO` is permitted only by explicit opt-in; it is never an automatic fallback for missing true labels. In pseudo mode, every pseudo target is generated from and bound to exact frozen `Phi`.

### D1.DEF.024 — Replay lineage

Replay lineage is the tuple

$$
\Lambda_{\mathrm{replay}}=(D_r^{\mathrm{geom}},\ell_{\mathrm{replay}},M_r^{\mathrm{true}},\Phi,\Pi_r),
$$

where `D_r^geom` is authenticated replay geometry/source membership and split, `M_r^true` is the mandatory independent true-reference replay-monitor lineage, `Phi` is required whenever pseudo labels or head-local foundation references are used, and `Pi_r` denotes the governed realized exposure identity.

Changing source content, geometry split, label mode, pseudo-label prediction policy, foundation/head identity, true-monitor membership, or governed exposure changes replay lineage and invalidates dependent post-selection evidence.

### D1.AX.011 — Replay separation and geometry invariance axiom

Replay is scientifically distinct from target membership: replay configurations do not contribute to target-size `N`, do not rank target sizes, and replay retention is an admissibility constraint rather than positive target-size ranking credit. Switching between `TRUE_REFERENCE` and `FOUNDATION_PSEUDO` over the same authenticated prepared replay source/split must not change `D_r^geom`. Pseudo-label replay still requires the separate true-reference monitor `M_r^true`. Hidden target duplication and target/replay training-head scalar weighting are not part of the accepted method.

## 7. Common target monitor, CV, and production

### D1.DEF.025 — Common target monitor

For usable protected neutral `OUTER_MONITOR` parent `P_mon`, foundation adaptation requires deterministic

$$
M_{\mathrm{mon}}\subseteq P_{\mathrm{mon}},
\qquad |M_{\mathrm{mon}}|=n_{\mathrm{mon}},
$$

with

$$
n_{\mathrm{mon}}=256.
$$

`n_mon` is `FIXED_METHOD_COORDINATE`. `M_mon` supplies no gradients and is protected-relation-disjoint from every configured target prefix in the frozen experiment. No silent smaller-monitor fallback exists.

### D1.DEF.026 — Post-selection fold partition

For frozen `T_N`, each CV fold `i` partitions

$$
T_N=G_i\mathbin{\dot\cup}O_i\mathbin{\dot\cup}P_i,
$$

into gradient, held-out, and purge/exclusion membership by protected components. `M_mon` is external. Fold count `K` is `CONFIGURABLE_WITH_GENERATED_DEFAULT` with admissible domain `K>=2` and current generated default `K=3`.

### D1.DEF.027 — Foundation role-threshold family

$$
\Theta_{\mathrm{role}}=(\tau_{\mathrm{CV}},\theta_{\mathrm{CV}},\tau_{\mathrm{prod}}).
$$

All three coordinates are `CONFIGURABLE_WITH_GENERATED_DEFAULT`, finite and positive. `tau_CV` is target-force checkpoint competence on `M_mon`; `theta_CV` is held-out acceptance on `O_i` in configured outer-metric units; `tau_prod` is target-force checkpoint quality on `M_mon` for production. Current generated defaults for the default force outer metric are

$$
\tau_{\mathrm{CV}}=\theta_{\mathrm{CV}}=45\ \mathrm{meV/angstrom},
\qquad
\tau_{\mathrm{prod}}=30\ \mathrm{meV/angstrom}.
$$

Equal numeric defaults do not merge estimands, populations, or evidence roles.

### D1.AX.012 — Fixed-budget CV consistency axiom

Every required `(fold,seed)` position trains to the frozen horizon; threshold crossing does not stop training. CV accepts only if every required position has an admissible frozen representative and every representative passes the outer predicate. Mean/majority/best-seed/dispersion cannot rescue a failing required position.

### D1.AX.013 — Fresh-production axiom

Fresh production starts a new model/optimizer lineage from accepted `Phi`, trains on complete exact `T_selected`, fits training-dependent state only on that authorized target membership, uses the same `M_mon` and shared checkpoint mechanics as CV, and applies `tau_prod` rather than `tau_CV`. Where replay is enabled it retains the same replay-lineage and true-reference-retention semantics under the production role. P3 `M3` has no production checkpoint role.

### D1.AX.014 — Downstream no-feedback axiom

Downstream physical/deployment/calibration/locked/release evidence consumes a frozen final publication and cannot alter target size/membership, training method, checkpoint choice, or final-publication membership after the applicable freeze boundary.

## 8. Parameter binding ledger

| Coordinate | Binding class | Admissible family/domain | Current value/default | Owner |
| --- | --- | --- | --- | --- |
| target-order hard coverage `gamma_cov` | `FIXED_METHOD_COORDINATE` | one current method coordinate | `0.95` | scoped target-order D1/D2 |
| target-order extent quantiles | `FIXED_METHOD_COORDINATE` | one lower/upper pair | `0.01, 0.99` | scoped target-order D1/D2 |
| target-size candidate ladder | `CONFIGURABLE_FAMILY` | D2 structural domain; at least three strictly increasing positive power-of-two sizes | configuration-bound | P2/P3 policy |
| evaluation-size ladder | `CONFIGURABLE_FAMILY` | D2 structural domain; exactly three strictly increasing positive power-of-two sizes | configuration-bound | P2/P3 policy |
| fidelity boundaries | `CONFIGURABLE_FAMILY` | exactly three strictly increasing positive epochs | configuration-bound | P2/P3 policy |
| optimizer seeds | `CONFIGURABLE_FAMILY` | ordered unique nonnegative integer population | configuration-bound | P2/P3 policy |
| practical `epsilon` | `CONFIGURABLE_FAMILY` | finite positive response-unit value | configuration-bound | P3 reducer |
| CV fold count `K` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | integer `K>=2` | default `3` | CV policy |
| common monitor size `n_mon` | `FIXED_METHOD_COORDINATE` | one current foundation-P5 value | `256` | foundation-P5 method |
| `tau_CV` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive force-RMSE ceiling | default `45 meV/angstrom` | CV role policy |
| `theta_CV` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive threshold in configured outer-metric units | default `45 meV/angstrom` for default force metric | CV role policy |
| `tau_prod` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive force-RMSE ceiling | default `30 meV/angstrom` | production role policy |
| foundation P5 E:F:S coefficients | `FIXED_METHOD_COORDINATE` | one current coefficient tuple | `1:10:1` | foundation-P5 method |
| `T_N`, `M_i`, `Q_mem` | `DERIVED` | defined by governing memberships/orders/predicates | computed | D1/D2 |

D2 separately classifies its fixed numerical coordinates and tolerances. A concrete evidence item binds the resolved values material to its claim. A configurable-role parameter change invalidates dependent role evidence, not unrelated method authority by default.

## 9. Validity, uncertainty, and typed infeasibility

The method fails/defers instead of redefining itself when required compatible labels cannot be formed; protected allocation would split a protected component; exact required reserve/monitor membership is unrealizable; complete `P_train` cannot satisfy required membership policy; a configured prefix fails `Q_mem`; too few qualified configured candidates exist for the automatic target-size diagnostic; a governed E0 composition is non-identifiable; pseudo replay lacks its required foundation or true-reference monitor binding; a required CV position is missing/fails/has no admissible checkpoint; or runtime realizes a materially different objective/exposure/method.

These cases do not authorize threshold widening, support relaxation, rescue-size invention, role substitution, implicit pseudo-label fallback, or fabricated evidence.

Material interpretation limitations remain those of the accepted D1 sources, including temporal correlation/unresolved slow states, finite condition/rare-event/monitor support, shared-monitor selection correlation, candidate-ladder discretization, optimizer/minibatch variation, practical-equivalence calibration, foundation identity dependence, robust-loss/exposure dependence, composition-level E0 conditioning, target/replay applicability mismatch, and numerical/runtime nonconformance. This formal kernel does not convert those limitations into a single scalar uncertainty.

## 10. D1 -> D2 contract

D2 must concretize, without changing meaning:

1. source/geometry/stress/strain conventions and protected statistical units;
2. the exact finite-sequence autocorrelation/truncation and block/event numerical rules used by D1.DEF.007/D1.DEF.005;
3. exact `U_size -> P_train + M3` split, component ordering, `pi_eval`, structural policy domain, and automatic-comparison sufficiency;
4. exact target-order family catalog, weighted measures, metric/radii/adjacency, separate selector/qualification coverage predicates, extents, obligations, FEAS1, MVSEL2, REPAIR2, and MVQUAL;
5. P3 optimizer-progress normalization, evaluation estimator, complete-seed reducer, exact funnel/sufficiency/configured-ceiling rules, and practical equivalence;
6. selected-head foundation-residual E0 fit and null-space transfer test;
7. replay label-mode/lineage concretization, geometry-membership invariance, true-monitor binding, robust foundation-P5 loss, and exact exposure semantics;
8. deterministic common-monitor construction/protected separation;
9. deterministic CV folds/purge;
10. shared checkpoint constraints and role-effective threshold predicates/currentness;
11. typed failure, precision/equivalence, continuation, and falsification oracles.

Any D2 need to change an estimand, evidence role, support predicate, replay interpretation, parameter-family meaning, or validity regime is an upward D1 Challenge.

## 11. Acceptance condition

Independent R2 review must show every object above is a lossless formalization of accepted basis semantics or exact specialized import, every direct material prerequisite is source-resolvable, and no newly excluded regime, changed default, changed owner boundary, or strengthened scientific claim has been introduced. This proposed overlay does not self-promote accepted D1 authority.