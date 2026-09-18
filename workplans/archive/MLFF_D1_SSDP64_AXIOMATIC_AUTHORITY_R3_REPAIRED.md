---
kind: proposed-D1-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_R3_REPAIRED_AWAITING_INDEPENDENT_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
repairs_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R2.md
supersedes_proposed_candidates:
  - workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE.md
  - workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE_R2.md
  - workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R2_REPAIRED.md
---

# Proposed MLFF D1 axiomatic authority kernel — repaired R3

## 1. Authority and exact import registry

This is the sole D1 file in the repaired R3 semantic candidate. Earlier candidate files listed in front matter are authoring history only and do not compose with this candidate.

The candidate formalizes, without changing, accepted MLFF D1 at repository `hjin98/mdstats` basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. It remains proposed until a fresh independent R3 review passes and the stakeholder ratifies the exact reviewed candidate.

Exact accepted imports are:

- `D1.SRC.GENERAL` = `hjin98/mdstats@cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824:docs/methods/mlff_scientific_method.md`;
- `D1.SRC.ORDER` = `hjin98/mdstats@cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824:docs/methods/mlff_target_training_order_scientific_method.md`.

`D1.SRC.ORDER` is the sole accepted owner for target-training-order membership design and supersedes conflicting general-paper prose on that bounded surface. `D1.SRC.GENERAL` remains owner for every unaffected D1 claim.

The following exact specialized imports are treated as already-defined roots rather than copied into a second owner:

- `D1.IMP.PHYSICAL` = `D1.SRC.GENERAL`, Sections 2.1 and 3.1-3.7: potential-energy-surface observables, source occurrence/geometry/label identities, label compatibility, row-cell/deformation/strain, stress, eligibility;
- `D1.IMP.STAT` = `D1.SRC.GENERAL`, Section 2.2: stationary autocorrelation estimand, integrated autocorrelation time, effective-count diagnostic and scientific interpretation;
- `D1.IMP.ROLES` = `D1.SRC.GENERAL`, Sections 4.1-4.6: independence grades, protected relations, event-before-thinning, evidence roles, feasibility/deferral, feature blinding;
- `D1.IMP.P3` = `D1.SRC.GENERAL`, Sections 2.3, 5, 6, 14.1 and 15: target-size controlled experiment, common preparation, target-size evidence/limitations and falsification;
- `D1.IMP.ORDER` = `D1.SRC.ORDER`, Sections 2-8: exact `P_train`, authorized pre-order evidence, one master order, family roles, correlation-balanced coverage, canonical hard support, ranking intent, repair meaning and qualification;
- `D1.IMP.P5` = `D1.SRC.GENERAL`, Sections 7-11: foundation objective/E0, checkpoint semantics, replay, common monitor, CV and fresh production;
- `D1.IMP.DOWNSTREAM` = `D1.SRC.GENERAL`, Sections 12-16: downstream qualification, applicability, uncertainty, reproducibility and reopen conditions.

A definition below may refine the representation of one imported object, but cannot change its accepted meaning. Definitions stipulate meaning; axioms are already-accepted project premises, not empirical proofs.

Parameter binding classes are:

- `FIXED_METHOD_COORDINATE`: changing the value changes the method;
- `CONFIGURABLE_FAMILY`: an admissible instance is explicitly configured;
- `CONFIGURABLE_WITH_GENERATED_DEFAULT`: configurable family plus separately owned current default;
- `DERIVED`: determined by other governed objects.

## 2. Foundational objects

### D1.DEF.001 — Atomic configuration

An atomic configuration is

$$
x=(\mathbf Z,\mathbf R,\mathbf H,\mathbf p),
$$

where ordered atomic numbers `Z`, Cartesian positions `R`, row-vector periodic cell `H`, periodic flags and source-occurrence metadata `p` have the exact meanings of `D1.IMP.PHYSICAL`. Occurrence identity and geometry identity are distinct. Invalid required geometry makes the frame ineligible under the imported source policy.

### D1.DEF.002 — Canonical target label statement

For eligible `x`,

$$
y(x)=\big(E(x),\mathbf F(x),\boldsymbol\sigma(x);\lambda(x)\big),
$$

where `lambda` binds all compatibility-significant theory, energy-reference, derivative/stress, unit, numerical-quality and provenance coordinates defined by `D1.IMP.PHYSICAL`. Missing optional properties are absent, not zero.

### D1.DEF.003 — Label compatibility

$$
y_a\sim_{\mathrm{label}}y_b
$$

iff `y_a` and `y_b` are compatible under `D1.SRC.GENERAL`, Section 3.2. Incompatible theory, energy-reference or derivative conventions cannot be merged by provenance similarity.

### D1.AX.001 — Compatible target-domain axiom

Every target training/evaluation population consumed as one scientific target domain belongs to one `~_label` compatibility class. Replay, when enabled, is separately identified.

### D1.DEF.004 — Energy-conserving model

The accepted model represents

$$
E_\theta(\mathbf Z,\mathbf R,\mathbf H),
$$

with

$$
\mathbf F_i=-\frac{\partial E_\theta}{\partial\mathbf R_i},
\qquad
\boldsymbol\sigma=-\frac1V\frac{\partial E_\theta}{\partial\boldsymbol\varepsilon},
$$

under `D1.IMP.PHYSICAL`. Cell, strain, sign, tensor/shear and unit conventions are part of this scientific object.

## 3. Protected dependence and evidence permissions

### D1.DEF.005 — Protected relation

For finite eligible frame universe `U`, let `R_prot` be the union of the five accepted primitive inseparability relations in `D1.IMP.ROLES`: correlation-unit co-membership, exact-geometry duplication, protected-event co-membership, condition-scoped replica lineage, and condition-scoped structural-realization lineage where available.

Let `TC` be reflexive-symmetric-transitive closure on binary relations over `U`. Define

$$
\sim_{\mathrm{prot}}=\mathrm{TC}(R_{\mathrm{prot}}).
$$

### D1.DEF.006 — Evidence-role permission system

Let `R_role` be the role vocabulary and `A_op` the operation vocabulary supplied by `D1.IMP.ROLES`. They include, as applicable, development/gradient, P3 model selection, checkpoint monitor, held-out CV, calibration, locked/challenge, purge/excluded, replay roles and the operations membership construction, fitting, fitted-transform construction, E0 fitting, checkpoint choice, held-out evaluation, calibration, locked evaluation, final-publication choice and downstream qualification.

Define

$$
r:U\rightarrow R_{\mathrm{role}},
\qquad
\mathrm{Perm}:R_{\mathrm{role}}\rightarrow 2^{A_{\mathrm{op}}},
$$

where `Perm` is exactly the authorization relation of `D1.IMP.ROLES` rather than a name-based default.

### D1.AX.002 — Protected-role separation

One `~_prot` class cannot be split across roles required by the governing method to be independent or mutually exclusive.

### D1.AX.003 — Evidence noninterference

For `x in U` and `a in A_op`, if

$$
a\notin\mathrm{Perm}(r(x)),
$$

information from `x` cannot influence `a` directly or through fitted descendants. In particular held-out labels cannot choose checkpoints, monitor labels cannot fit training state, locked evidence cannot choose target/final membership, calibration cannot tune its own protocol, and P3 outcomes cannot feed backward into `pi_train`.

### D1.DEF.007 — Correlation diagnostic estimand

For stationary scalar `X_t` with finite variance,

$$
\rho(k)=\frac{\mathrm{Cov}(X_t,X_{t+k})}{\mathrm{Var}(X_t)},
\qquad
\tau_{\mathrm{int}}=\frac12+\sum_{k=1}^{k^\star}\rho(k),
$$

$$
N_{\mathrm{eff}}=\min\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
$$

These scientific quantities and their interpretation are exact imports from `D1.IMP.STAT`. D2 owns the finite-sequence estimator/truncation and complete-frame block construction. `N_eff` is a redundancy diagnostic, not proof that every slow state is independent.

## 4. Target-size experiment

### D1.DEF.008 — Target-size population and split

`U_size` is exact eligible neutral `DEVELOPMENT` evidence with canonical training labels. It is partitioned once without splitting `~_prot` components:

$$
U_{\mathrm{size}}=P_{\mathrm{train}}\mathbin{\dot\cup}M_3.
$$

`P_train` is the target-order domain; `M3` is the largest P3 evaluation reserve.

### D1.DEF.009 — Target-size policy family

A target-size policy instance binds candidate-size tuple `N_cfg`, evaluation-size tuple `M_cfg`, fidelity tuple `H_cfg`, ordered optimizer-seed population `S_seed`, practical-equivalence parameter `epsilon`, the accepted optimizer-normalization family and reducer/funnel family. Its scientific role is the controlled comparative experiment of `D1.IMP.P3`; D2 owns the exact structural/numerical admissibility of those tuples.

### D1.AX.004 — Controlled-variable axiom

Within one target-size experiment, changing candidate cardinality `N` changes only exact target prefix `T_N` and consequences of adding those frames. Pre-order authority, membership rule, P3-common fitted preparation, seeds, fidelity schedule, evaluation ladder, objective and reducer remain candidate-independent unless an accepted method coordinate states otherwise.

### D1.DEF.010 — Evaluation ladder

D2 constructs one deterministic `pi_eval` over `M3`. For configured `m_i`,

$$
M_i=\pi_{\mathrm{eval}}[:m_i].
$$

`m_i<m_j` implies exact nested membership. `M_i` are P3 model-selection populations, not post-selection held-out or checkpoint-monitor evidence.

### D1.DEF.011 — Primary P3 response and practical equivalence

For `K>0` admitted Cartesian force components,

$$
\mathrm{RMSE}_F=\sqrt{\frac1K\sum_{k=1}^{K}(F_k^{\mathrm{pred}}-F_k^{\mathrm{ref}})^2}.
$$

The stored response is in `meV/angstrom`. Practical-equivalence parameter `epsilon>0` is a `CONFIGURABLE_FAMILY` value in those response units; it is not machine epsilon.

## 5. Target-training order and qualification

### D1.DEF.012 — Canonical target-training order

For finite exact `P_train={x_1,...,x_n}`, the method constructs one deterministic complete permutation

$$
\pi_{\mathrm{train}}=(x_{(1)},\ldots,x_{(n)}),
$$

and

$$
T_N=\{x_{(1)},\ldots,x_{(N)}\},\qquad 1\le N\le n.
$$

Hence `N_a<N_b` implies `T_{N_a} subset T_{N_b}`. Independent per-`N` selectors are not the method.

### D1.DEF.013 — Authorized selector information

`I_sel` is exactly the pre-candidate information class in `D1.IMP.ORDER`: exact-`P_train` or authenticated partition-independent ancestors providing universal structure/environment, pair geometry/coordination, target-development response, applicable profile-selection, applicable frozen-foundation weakness and hard-support evidence. `M3/M1/M2`, candidate outcomes/reducer, post-selection monitor/CV/replay-monitor, calibration/locked/challenge and downstream evidence are excluded.

### D1.AX.005 — Selector measurability

`pi_train` and selector-fitted quantities are functions only of `I_sel` plus accepted policy parameters. Perturbing excluded evidence while holding those inputs fixed cannot change `pi_train`.

### D1.DEF.014 — Required family role and reference measure

The required scientific family roles are exactly `D1.SRC.ORDER`, Sections 4.2-4.3: universal local structure/environment; pair geometry/coordination; target-development response; profile selection only under an active accepted provider; foundation weakness/residual only when target-size training itself uses an authenticated frozen foundation model.

For family `m`, finite witness set `W_m` carries normalized measure `mu_m` assigning equal total mass to every represented P1 correlation unit and equal mass to witnesses within that unit. D2 owns exact family names, coordinates, applicability rows, metric/neighborhood and extent flags.

### D1.DEF.015 — Covered mass and fixed target-order coordinates

For selected `S subseteq P_train` and authorized neighborhood `N_m(w)`,

$$
C_m(S)=\mu_m\big(\{w\in W_m:N_m(w)\cap S\ne\varnothing\}\big).
$$

The hard family coordinate is fixed:

$$
\gamma_{\mathrm{cov}}=0.95.
$$

Extent-bearing coordinates use fixed weighted quantiles

$$
q_{\mathrm{lo}}=0.01,
\qquad q_{\mathrm{hi}}=0.99.
$$

All three are `FIXED_METHOD_COORDINATE`; D2 owns their distinct floating comparison tolerances. No named-family coverage override is active.

### D1.DEF.016 — Canonical hard-support obligation

A source obligation is

$$
o=(L(o),A(o),k(o)),
$$

with semantic locus `L`, exact current-`P_train` incidence `A`, and positive minimum `k`. Automatic loci cover represented P2 conditions, P1 correlation units, recognized structural events, active profile environment classes and both sides of required extent channels where applicable. Explicit policy may strengthen a locus.

Only same accepted locus/applicability/provider semantics plus identical incidence may canonicalize. Effective minimum is

$$
k_\ast(L)=\max\{k(o):L(o)=L\}.
$$

Disagreement at purported same locus fails closed; incidence equality alone never aliases distinct loci.

### D1.DEF.017 — Membership admissibility

For configured `N`, `Q_mem(N)` is true iff exact `T_N` exists, its required labels are training-usable, every required family passes hard coverage, every required extent passes, and every canonical hard obligation reaches effective minimum.

Under fixed evidence/neighborhood/obligations, nested positive-support predicates imply qualification pattern `FAIL* -> PASS*`; `PASS -> FAIL` is an invariant failure.

### D1.AX.006 — Qualification/ranking separation

`Q_mem` gates membership before training. It has no ranking/tie authority among qualified candidates; P3 target-force reducer owns automatic size comparison.

### D1.AX.007 — Repair continuity

Configured-shell repair may modify only the newly added shell, preserves every completed lower configured prefix, preserves hard support, does not regress required-family coverage beyond D2 tolerance and strictly improves the D2 repair objective. After the final configured shell, the same multi-view method completes all `P_train`; there is no unconfigured repair shell or alternate suffix selector.

### D1.DEF.018 — Automatic-screen admitted set and sufficiency

For one configured policy instance define

$$
Q_{\mathrm{cfg}}=\{N\in N_{\mathrm{cfg}}:Q_{\mathrm{mem}}(N)\}.
$$

An unqualified configured prefix is excluded from `Q_cfg`; its presence in the configured ladder does not by itself invalidate the experiment. An unqualified prefix cannot be manually/operator-admitted to target training or post-selection CV. Automatic P3 screening is defined only when the D2 current sufficiency predicate holds on `Q_cfg`; in the accepted current method that requires at least three qualified configured candidates. Fewer qualified candidates yield insufficient automatic comparison rather than changed membership, whole-method failure, or an invented size.

### D1.AX.008 — Recommendation/decision separation

The P3 reducer produces diagnostic evidence/recommendation. The operator owns the provisional downstream design within qualified configured memberships. Post-selection CV may accept/reject that frozen design but cannot retroactively alter `N`, `T_N`, `pi_train` or P3 evidence.

## 6. Foundation adaptation, atomic references and replay

### D1.DEF.019 — Property availability and foundation objective

For `p in {E,F,S}`, `m_p(x) in {0,1}` denotes property availability. P3 and post-selection scratch retain their imported accepted weighted objectives. Foundation P5 (`naive_fine_tuning`, `multihead_replay`) uses the D2 robust E/F/S objective with fixed global coefficients `1:10:1`, binary property masks, no nontrivial per-configuration loss weight and no target/replay **training-head** scalar.

Checkpoint-control `target_score_weight`/`replay_score_weight`, where enabled by `D1.IMP.P5`, are a separate model-selection concept and are not training-head loss weights.

### D1.DEF.020 — Foundation identity and composition correction

Foundation identity is

$$
\Phi=(\text{checkpoint identity},\text{head identity},\text{model/version identity}).
$$

Foundation residuals, head-local references and pseudo labels are undefined without exact `Phi`.

For composition row `c` and elemental correction `delta e`,

$$
\Delta E_0(c)=c^T\delta e.
$$

If `N_free` is the unanchored null space of the authorized residual fit after accepted anchors, the correction is identifiable iff

$$
c^Tv=0\quad\text{for every }v\in N_{\mathrm{free}}.
$$

Individual coefficients need not be unique. Target residual corrections are fitted only from the authorized target-gradient domain; monitor/held-out labels cannot resolve null directions.

### D1.DEF.021 — Replay label-mode family

For post-selection `multihead_replay`,

$$
\ell_{\mathrm{replay}}\in\{\mathrm{TRUE\_REFERENCE},\mathrm{FOUNDATION\_PSEUDO}\}.
$$

`TRUE_REFERENCE` is the canonical default when canonical true-reference/DFT replay labels exist. `FOUNDATION_PSEUDO` requires explicit opt-in and every pseudo target is bound to exact frozen `Phi`; it is not a missing-label fallback.

### D1.DEF.022 — Replay lineage and geometry invariance

Let `Q_r` denote the exact replay qualification-policy/evidence identity and current qualification state required by `D1.IMP.P5`, including the independent true-reference retention qualification applicable to the configured replay method. Replay lineage is

$$
\Lambda_{\mathrm{replay}}=(D_r^{\mathrm{geom}},\ell_{\mathrm{replay}},M_r^{\mathrm{true}},\Phi,Q_r,\Pi_r),
$$

where `D_r^geom` is authenticated replay geometry/source membership and split, `M_r^true` is mandatory independent true-reference replay-monitor lineage, `Phi` is material when pseudo labels or head-local foundation references are used, `Q_r` binds replay qualification policy/evidence/current state, and `Pi_r` is governed realized exposure identity.

Switching label mode over the same authenticated prepared source/split must not change `D_r^geom`. Pseudo replay still requires `M_r^true`. Replay configurations are not target-size `N`, replay does not rank target sizes, replay retention is an admissibility constraint, and hidden target duplication is outside the method. Changing source/split, label mode, prediction policy, foundation/head, true monitor, replay qualification, or governed exposure changes replay lineage and invalidates dependent evidence. A label-mode change alone does not authorize a replay-geometry membership change.

## 7. Common monitor, CV and production

### D1.DEF.023 — Common target monitor

For protected neutral `OUTER_MONITOR` parent `P_mon`, foundation P5 requires deterministic

$$
M_{\mathrm{mon}}\subseteq P_{\mathrm{mon}},
\qquad |M_{\mathrm{mon}}|=256.
$$

The cardinality `256` is `FIXED_METHOD_COORDINATE`. `M_mon` supplies no gradients, is protected-relation-disjoint from every configured target prefix and is shared across selected sizes, CV folds/seeds and fresh production. No smaller-monitor or role fallback exists.

### D1.DEF.024 — Post-selection folds

For frozen `T_N`, fold `i` partitions

$$
T_N=G_i\mathbin{\dot\cup}O_i\mathbin{\dot\cup}P_i
$$

by protected components into gradient, held-out and purge/exclusion roles; `M_mon` is external. Fold count `K` is `CONFIGURABLE_WITH_GENERATED_DEFAULT`, domain integer `K>=2`, current default `3`.

### D1.DEF.025 — Foundation role-threshold family

$$
\Theta_{\mathrm{role}}=(\tau_{\mathrm{CV}},\theta_{\mathrm{CV}},\tau_{\mathrm{prod}})
$$

are independent finite positive `CONFIGURABLE_WITH_GENERATED_DEFAULT` coordinates. `tau_CV` is target-force checkpoint competence on `M_mon`; `theta_CV` is held-out acceptance on `O_i` in configured outer-metric units; `tau_prod` is production target-force checkpoint quality on `M_mon`. Current defaults for the default force outer metric are

$$
45,45,30\ \mathrm{meV/angstrom},
$$

respectively. Equal default values do not merge estimands or populations.

### D1.AX.009 — Fixed-budget all-position CV

Every required `(fold,seed)` trains to frozen horizon; threshold crossing does not stop training. CV accepts only if every required position has an admissible frozen representative and every representative passes its outer predicate. Mean, majority, best-seed and dispersion cannot rescue a failing position.

### D1.AX.010 — Fresh production

Fresh production starts a new model/optimizer lineage from accepted `Phi`, trains complete exact `T_selected`, fits training-dependent state only on that authorized target membership, uses the same `M_mon` and shared checkpoint mechanics as CV, and applies `tau_prod` rather than `tau_CV`. Where replay is enabled, `Lambda_replay`, its qualification identity/state, and true-reference retention remain binding. P3 `M3` has no production checkpoint role.

### D1.AX.011 — Downstream no-feedback

Downstream physical/deployment/calibration/locked/release evidence consumes frozen final publication and cannot alter target size/membership, training method, checkpoint choice or final-publication membership after the applicable freeze boundary.

## 8. Parameter binding ledger

| Coordinate | Binding class | Admissible family/domain | Current value/default | Owner |
| --- | --- | --- | --- | --- |
| `gamma_cov` | `FIXED_METHOD_COORDINATE` | current target-order method | `0.95` | scoped D1/D2 |
| extent quantiles | `FIXED_METHOD_COORDINATE` | lower/upper pair | `0.01,0.99` | scoped D1/D2 |
| candidate ladder | `CONFIGURABLE_FAMILY` | D2 structural domain | configuration-bound | P2/P3 |
| evaluation ladder | `CONFIGURABLE_FAMILY` | D2 structural domain | configuration-bound | P2/P3 |
| fidelity boundaries | `CONFIGURABLE_FAMILY` | D2 structural domain | configuration-bound | P2/P3 |
| optimizer seeds | `CONFIGURABLE_FAMILY` | D2 structural domain | configuration-bound | P2/P3 |
| practical `epsilon` | `CONFIGURABLE_FAMILY` | finite positive response-unit value | configuration-bound | P3 reducer |
| replay label mode | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | true or pseudo under validity conditions | true-reference default when labels exist | P5 replay |
| replay qualification identity/state | `DERIVED` | configured replay policy/evidence/current qualification | lineage-bound | P5 replay |
| CV `K` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | integer `K>=2` | `3` | CV policy |
| `n_mon` | `FIXED_METHOD_COORDINATE` | current foundation-P5 method | `256` | P5 method |
| `tau_CV` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive force ceiling | `45 meV/angstrom` | CV role |
| `theta_CV` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive outer-metric threshold | `45 meV/angstrom` for default force metric | CV role |
| `tau_prod` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive force ceiling | `30 meV/angstrom` | production role |
| P5 E:F:S coefficients | `FIXED_METHOD_COORDINATE` | current foundation-P5 method | `1:10:1` | P5 method |
| `T_N`, `M_i`, `Q_mem`, `Q_cfg` | `DERIVED` | governing definitions above | computed | D1/D2 |

## 9. Validity, uncertainty and D1 -> D2 handoff

The method fails/defers rather than redefining itself when required compatible labels cannot be formed; protected allocation is impossible; exact reserve/monitor cannot be realized; complete `P_train` cannot satisfy support; fewer than the required qualified candidates exist for automatic comparison; governed E0 transfer is non-identifiable; pseudo replay lacks exact foundation or true-reference monitor; replay qualification is invalid/stale; required CV position fails/missing/no admissible checkpoint; or runtime realizes a materially different objective/exposure/method. An individual configured prefix with `Q_mem(N)=false` is excluded from `Q_cfg` and cannot be manually admitted, but is not by itself whole-method failure when the remaining qualified set satisfies automatic-comparison sufficiency. No threshold widening, support relaxation, rescue-size invention, role substitution, pseudo-label fallback or fabricated evidence is authorized.

Uncertainty/limitations and downstream adequacy remain exact imports from `D1.IMP.DOWNSTREAM`; this kernel does not convert them into a scalar uncertainty claim.

D2 must concretize, without changing meaning:

1. physical/source/eligibility conventions and protected statistical units, including finite autocorrelation truncation, block/event rules;
2. exact `U_size -> P_train + M3`, component ordering, `pi_eval`, policy structural domain and automatic-screen sufficiency;
3. exact target-order family catalog/applicability, one-time correlation-balanced weights, metrics/radii/adjacency, distinct selector/qualification coverage predicates, extents, obligations, FEAS1, MVSEL2, REPAIR2 and MVQUAL;
4. P3 common preparation, optimizer normalization, evaluator, complete-seed score, practical-equivalence ranking, exact funnel/success-sufficiency/configured-ceiling rule and authenticated continuation;
5. selected-head foundation-residual E0 fit, replay/pretraining-head foundation E0 binding, and composition transfer;
6. replay label-mode/lineage concretization, geometry invariance, qualification currentness, true-reference retention, robust P5 objective and exposure;
7. deterministic monitor/folds/purge, shared checkpoint constraints, role predicates/currentness and fresh production;
8. typed numerical failure, precision/equivalence and falsification oracles.

Any needed change to a scientific estimand, role, support predicate, replay interpretation, parameter-family meaning or validity regime is an upward D1 Challenge.

## 10. Acceptance condition

Fresh independent R3 review must show this file plus the repaired R3 D2 kernel is losslessly equivalent to accepted basis, exact-import paths resolve, definitions are available before substantive use, and no accepted regime/default/owner boundary has drifted. This proposal does not self-promote.