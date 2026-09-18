---
kind: proposed-D1-authority-kernel
protocol_version: 6.4.0
status: PROPOSED_RENEWAL_REPAIR_CANDIDATE_AWAITING_INDEPENDENT_REVIEW
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_baseline_date: 2026-09-17
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
prior_independent_review_target: e827aef9bdceb97aae5be6e89de0585a95dcf71c
prior_independent_review_commit: 2eddd9058beda039e0ff53d4e50a189be469173b
prior_ratified_candidate_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
stakeholder_direction_date: 2026-09-18
repaired_from_reviewed_candidate: 06f1255ed39f41d178daf73985829a2190a2bee8
repair_basis_review_commit: a1e086645708b273382ed3742a8788ce01592b80
---

# mdstats MLFF D1 axiomatic authority kernel — Protocol 6.4 proposed replay/target-policy renewal

## 1. Authority and exact import registry

The accepted current D1 authority remains the repository state on `main` at `a759e81aa1b4c70c8fb513c569ddce57e99cbdb2` until this branch candidate passes fresh independent Protocol-6.4 D1 Review and is explicitly stakeholder-ratified. This file is the proposed canonical replacement for that D1 kernel on the replay-retention / checkpoint-admissibility / P5 representative-selection surface.

The accepted baseline formalizes the scientific meaning reconstructed at basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824` and exact-imports the detailed pre-Protocol-6.4 source papers pinned at stakeholder-ratified target `a4824d28775164aa942fd29fa97ee0957eb87e6f`.

The prior assembled-candidate Review passed on immutable target `e827aef9bdceb97aae5be6e89de0585a95dcf71c` at review commit `2eddd9058beda039e0ff53d4e50a189be469173b`. The stakeholder then identified one renderer-only D2.DEF.027 notation defect; target `a4824d28775164aa942fd29fa97ee0957eb87e6f` changed only those two restricted-sum renderings, preserved the reviewed mathematics exactly, and was ratified for canonical promotion on 2026-09-17. The present 2026-09-18 candidate is a new material D1 amendment and inherits none of that prior Review as acceptance proof.

Exact accepted imports are:

- `D1.SRC.GENERAL` = `hjin98/mdstats@a4824d28775164aa942fd29fa97ee0957eb87e6f:docs/methods/mlff_scientific_method.md`;
- `D1.SRC.ORDER` = `hjin98/mdstats@a4824d28775164aa942fd29fa97ee0957eb87e6f:docs/methods/mlff_target_training_order_scientific_method.md`.

`D1.SRC.ORDER` is the sole accepted owner for target-training-order membership design and supersedes conflicting general-paper prose on that bounded surface. `D1.SRC.GENERAL` remains owner for every unaffected D1 claim.

The following exact specialized imports are treated as already-defined roots rather than copied into a second owner:

- `D1.IMP.PHYSICAL` = `D1.SRC.GENERAL`, Sections 2.1 and 3.1-3.7: potential-energy-surface observables, source occurrence/geometry/label identities, label compatibility, row-cell/deformation/strain, stress, eligibility;
- `D1.IMP.STAT` = `D1.SRC.GENERAL`, Section 2.2: stationary autocorrelation estimand, integrated autocorrelation time, effective-count diagnostic and scientific interpretation;
- `D1.IMP.ROLES` = `D1.SRC.GENERAL`, Sections 4.1-4.6: independence grades, protected relations, event-before-thinning, evidence roles, feasibility/deferral, feature blinding;
- `D1.IMP.P3` = `D1.SRC.GENERAL`, Sections 2.3, 5, 6, 14.1 and 15: target-size controlled experiment, common preparation, target-size evidence/limitations and falsification;
- `D1.IMP.ORDER` = `D1.SRC.ORDER`, Sections 2-8: exact `P_train`, authorized pre-order evidence, one master order, family roles, correlation-balanced coverage, canonical hard support, ranking intent, repair meaning and qualification;
- `D1.IMP.P5` = `D1.SRC.GENERAL`, Sections 7-11: foundation objective/E0, checkpoint semantics, replay, common monitor, CV and fresh production;
- `D1.IMP.DOWNSTREAM` = `D1.SRC.GENERAL`, Sections 12-16: downstream qualification, applicability, uncertainty, reproducibility and reopen conditions.

A definition below may refine the representation of one imported object, but cannot change its accepted meaning except on the explicitly reopened surface below. Definitions stipulate meaning; axioms are project premises proposed for renewed acceptance, not empirical proofs.

For this candidate only, the local D1 objects below supersede conflicting clauses of `D1.IMP.P5` on these bounded surfaces:

- `D1.DEF.022/022A`: replay-retention observable, diagnostic warning, catastrophic hard failure, and the separation of replay evidence from training lineage;
- `D1.DEF.025-027`: foundation role target defaults, strict target-RMSE P5 checkpoint ordering, and final single-best-seed ordering;
- `D1.AX.009-010A`: fixed-budget CV, fresh-production/current-CV authorization, and assessment-policy noninterference with an already-realized training trajectory;
- the parameter ledger, D1-to-D2 handoff and reopen conditions that descend from those amendments.

In particular, imported prose that calls replay degradation a single hard admissibility budget, gives replay positive checkpoint-ranking credit, imports practical-equivalence/bootstrap/secondary/maturity ordering into foundation-P5 representative choice, fixes the production generated default at `30 meV/angstrom`, or assumes that production must be numerically stricter than CV is superseded on this candidate surface. Every unaffected P1-P4/P5/downstream claim remains exactly imported.

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

Historical checkpoint-control `target_score_weight`/`replay_score_weight` remain provenance for consumers that still legitimately own them, but they have no authority in current foundation-P5 checkpoint representative or final single-best-seed ordering under `D1.DEF.026-027`. They remain distinct from training-head loss weights.

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

Let `Q_r` denote the exact replay **evidence-qualification** identity and current qualification state required to make replay training and retention evidence scientifically interpretable. `Q_r` may bind source/label/provider validity and the independent true-reference retention qualification applicable to the configured replay method; it does **not** contain checkpoint warning thresholds, catastrophic-forgetting thresholds, target ceilings, or checkpoint-ordering policy.

Replay lineage is

$$
\Lambda_{\mathrm{replay}}=(D_r^{\mathrm{geom}},\ell_{\mathrm{replay}},M_r^{\mathrm{true}},\Phi,Q_r,\Pi_r),
$$

where `D_r^geom` is authenticated replay geometry/source membership and split, `M_r^true` is mandatory independent true-reference replay-monitor lineage, `Phi` is the exact frozen foundation checkpoint/head/model identity whose inherited capability is being retained, `Q_r` binds replay evidence qualification/current state, and `Pi_r` is governed realized exposure identity. Whenever replay-retention assessment is enabled for foundation adaptation, exact `Phi` is a mandatory replay-lineage parent regardless of replay training-label mode. `FOUNDATION_PSEUDO` additionally uses that same exact `Phi` as the pseudo-label provider.

Switching label mode over the same authenticated prepared source/split must not change `D_r^geom`. Pseudo replay still requires `M_r^true`. Replay configurations are not target-size `N`, replay does not rank target sizes, and hidden target duplication is outside the method. Changing source/split, label mode, prediction policy, foundation/head, true monitor, replay evidence qualification, or governed exposure changes replay lineage and invalidates dependent evidence. A label-mode change alone does not authorize a replay-geometry membership change.

### D1.DEF.022A — TRUE_REFERENCE replay-retention observable and decision roles

For a fully evaluated foundation-adaptation checkpoint `c`, let

$$
R_{\mathrm{replay}}(c)
$$

be the authoritative force-component RMSE on the exact independent true-reference replay monitor $M_r^{\mathrm{true}}$ (currently realized by project DFT / `true_dft` evidence), and let

$$
R_{\mathrm{replay}}(\Phi)
$$

be the same observable on the same exact replay membership under the authenticated frozen foundation identity $\Phi$. Define signed replay degradation

$$
\Delta_{\mathrm{replay}}(c)=R_{\mathrm{replay}}(c)-R_{\mathrm{replay}}(\Phi).
$$

The replay decision-policy family is

$$
\Psi_{\mathrm{replay}}=(\delta_{\mathrm{warn}},\delta_{\mathrm{hard}}),
$$

where both coordinates are finite positive `CONFIGURABLE_WITH_GENERATED_DEFAULT` values satisfying $\delta_{\mathrm{warn}}<\delta_{\mathrm{hard}}$. Current generated defaults are

$$
\delta_{\mathrm{warn}}=50\ \mathrm{meV/angstrom},
\qquad
\delta_{\mathrm{hard}}=100\ \mathrm{meV/angstrom}.
$$

Their scientific roles are distinct:

1. replay degradation not exceeding $\delta_{\mathrm{warn}}$ carries no replay-degradation warning;
2. degradation above $\delta_{\mathrm{warn}}$ but not above $\delta_{\mathrm{hard}}$ is a **diagnostic retention warning only** and does not by itself make the checkpoint inadmissible;
3. degradation above $\delta_{\mathrm{hard}}$ is classified as catastrophic forgetting and is a mandatory hard checkpoint failure.

Missing, stale, unauthenticated, incompatible or non-finite required true-reference replay evidence remains a hard evidence-validity failure independently of the numeric degradation class.

True-reference replay is an auxiliary inherited-capability retention observable for foundation adaptation. It is not the target-domain quality estimand, is not a deployment/release-adequacy metric, receives no positive checkpoint-ranking or tie-break credit, and cannot rank target sizes. The current default thresholds are stakeholder-selected policy calibrations, not universal physical constants; external adequacy remains downstream.

The force-error dimension and the scientific boundary relations above are D1 authority: equality at `delta_warn` does not create a warning, equality at `delta_hard` does not create catastrophic failure, and only strict exceedance changes the corresponding class. D2 owns the numerical realization of these relations, including canonical unit representation/conversion, finite machine representation, comparison implementation, boundary oracles and typed numerical failure; D2 may not change the dimension or strict/inclusive scientific relation.

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
45,45,50\ \mathrm{meV/angstrom},
$$

respectively.

The three coordinates are role-specific policy claims. Their numerical ordering has no independent scientific meaning: `tau_prod > tau_CV` under the current defaults does not merge their evidence roles, does not make held-out CV evidence a production checkpoint substitute, and does not assert that production is globally less demanding than CV. Production target admission remains checkpoint/model-control evidence rather than external adequacy; downstream qualification remains separate.

### D1.DEF.026 — Foundation-P5 checkpoint universe and representative

For role `rho`, let `C_rho` be the **governed checkpoint universe** of the realized fixed-budget TRAIN2 trajectory: every checkpoint position required by the accepted checkpoint cadence that was durably committed by that trajectory and is therefore required to enter checkpoint assessment. A quality-dependent shortlist, refinement subset, rescue subset or evaluator-purchased subset cannot replace `C_rho`.

Every member of `C_rho` must receive the required checkpoint assessment. Failure to authenticate, reconstruct or evaluate a required member is handled through the applicable hard evidence/integrity failure semantics; it is not permission to silently remove that checkpoint position from the scientific alternative set.

Let

$$
H_\rho=\{c\in C_\rho : c\text{ satisfies every current hard checkpoint requirement}\},
$$

where the hard requirements include evidence validity, finite/integrity/physical constraints, the role-effective target ceiling, and catastrophic replay protection where replay is enabled.

For `c in H_rho`, let `r_mon(c)` be authoritative target force-component RMSE on exact `M_mon`. If `H_rho` is nonempty, the foundation-P5 representative is selected from

$$
\mathop{\mathrm{argmin}}_{c\in H_\rho} r_{\mathrm{mon}}(c).
$$

A checkpoint with strictly worse `r_mon` cannot be promoted by replay margin or warning state, secondary target metrics, energy/stress diagnostics, maturity/refinement phase, practical-equivalence bands, bootstrap uncertainty, or historical checkpoint score weights. Replay receives no positive ranking or tie-break credit. If more than one checkpoint has exactly equal authoritative target RMSE, D2 supplies a deterministic non-quality tie rule that cannot depend on replay or another quality metric.

If `H_rho` is empty, the run has no representative. Diagnostic replay warning alone can never make `H_rho` empty. D2 owns exact durable enumeration/authentication mechanics for `C_rho` but may not reduce the governed universe by a quality-dependent evaluation policy.

### D1.DEF.027 — Final-production publication ordering

Each required fresh production seed first freezes its own representative under `D1.DEF.026`.

Under `all_qualified_final_seeds`, every already-qualified required seed representative is published without cross-seed quality ranking.

Under `single_best_final_seed`, the published member is selected from the already-frozen admissible seed representatives by minimum authoritative common-monitor target force-component RMSE. A strictly worse target RMSE cannot be promoted by replay retention, warning status, secondary metrics, maturity or uncertainty diagnostics. Exact target-RMSE ties use a deterministic D2 non-quality tie rule.

No second target evaluation, held-out fold, P3 `M3`, downstream qualification or replay metric may choose publication membership after these representatives are frozen.

### D1.AX.009 — Fixed-budget all-position CV

Every required `(fold,seed)` trains to frozen horizon; target or replay threshold crossing does not stop training. Each position freezes its representative under `D1.DEF.026`, and a replay warning below the catastrophic hard limit is non-vetoing. CV accepts only if every required position has an admissible representative and every representative passes its outer predicate. Mean, majority, best-seed and dispersion cannot rescue a failing position.

### D1.AX.010 — Fresh production

Current final production requires current accepted CV authorization for the frozen method/design. Fresh production starts a new model/optimizer lineage from accepted `Phi`, trains complete exact `T_selected`, fits training-dependent state only on that authorized target membership, uses the same `M_mon` and checkpoint mechanics as CV, and applies `tau_prod` rather than `tau_CV`. Where replay is enabled, `Lambda_replay`, mandatory independent true-reference replay evidence (currently realized by project DFT / `true_dft` evidence) and the catastrophic protection of `D1.DEF.022A` remain binding. P3 `M3` has no production checkpoint role.

### D1.AX.010A — Assessment-policy noninterference and reassessment

A change only to replay warning/hard policy, a role target ceiling, or foundation-P5 representative/publication ordering cannot alter an already-realized training trajectory when every training-affecting scientific input and training method coordinate is unchanged.

The assessment-currentness consequences are intentionally asymmetric:

1. changing only `delta_warn` changes replay-warning/diagnostic classification only; it cannot by itself change `H_rho`, the representative, outer-evaluation membership, CV pass/fail, production authorization or publication membership;
2. changing `delta_hard`, a role-effective target ceiling, or the foundation-P5 representative/publication ordering may change the corresponding hard checkpoint assessment, representative and dependent CV/final decision according to its role;
3. neither class of assessment-policy change changes the realized training trajectory when all training-bearing scientific semantics are unchanged.

A historical verdict is never silently relabeled current under a changed hard-decision or selection policy. A historically fresh final-production trajectory may support a new current production assessment only after the current CV authority has been reclosed and accepted and exact training-semantic equivalence is established. If current CV rejects, retained historical final-training evidence cannot authorize current publication. D2/D3 own the exact equivalence and durable currentness realization without weakening these scientific dependencies.

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
| replay qualification identity/state | `DERIVED` | replay source/label/provider/evidence qualification excluding checkpoint decision thresholds | lineage-bound | P5 replay evidence |
| replay degradation | `DERIVED` | signed true-reference replay force-RMSE change relative to exact foundation baseline `Phi` on the same monitor | computed | P5 replay evidence |
| `delta_warn` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive replay-degradation warning threshold | `50 meV/angstrom` | replay diagnostic policy |
| `delta_hard` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive catastrophic-forgetting threshold with `delta_warn < delta_hard` | `100 meV/angstrom` | hard checkpoint policy |
| CV `K` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | integer `K>=2` | `3` | CV policy |
| `n_mon` | `FIXED_METHOD_COORDINATE` | current foundation-P5 method | `256` | P5 method |
| `tau_CV` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive force ceiling | `45 meV/angstrom` | CV role |
| `theta_CV` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive outer-metric threshold | `45 meV/angstrom` for default force metric | CV role |
| `tau_prod` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | finite positive force ceiling | `50 meV/angstrom` | production role |
| P5 checkpoint representative ordering | `FIXED_METHOD_COORDINATE` | minimum authoritative target force RMSE over hard-admissible checkpoints; non-quality exact-tie rule only | target-only | P5 checkpoint selection |
| `single_best_final_seed` ordering | `FIXED_METHOD_COORDINATE` | minimum authoritative target force RMSE over frozen admissible seed representatives; non-quality exact-tie rule only | target-only | final publication |
| P5 E:F:S coefficients | `FIXED_METHOD_COORDINATE` | current foundation-P5 method | `1:10:1` | P5 method |
| `T_N`, `M_i`, `Q_mem`, `Q_cfg` | `DERIVED` | governing definitions above | computed | D1/D2 |

## 9. Validity, uncertainty and D1 -> D2 handoff

The method fails/defers rather than redefining itself when required compatible labels cannot be formed; protected allocation is impossible; exact reserve/monitor cannot be realized; complete `P_train` cannot satisfy support; fewer than the required qualified candidates exist for automatic comparison; governed E0 transfer is non-identifiable; pseudo replay lacks exact foundation or true-reference monitor; required true-reference replay evidence is missing/stale/incompatible/non-finite; replay degradation violates the current catastrophic hard policy; required CV position fails/missing/no admissible checkpoint; current CV authorization is absent for current final production; or runtime realizes a materially different objective/exposure/method. Replay warning below the catastrophic hard limit is explicitly not a method failure. An individual configured prefix with `Q_mem(N)=false` is excluded from `Q_cfg` and cannot be manually admitted, but is not by itself whole-method failure when the remaining qualified set satisfies automatic-comparison sufficiency. No threshold widening, support relaxation, rescue-size invention, role substitution, pseudo-label fallback, warning-to-failure promotion or fabricated evidence is authorized.

Uncertainty/limitations and downstream adequacy remain exact imports from `D1.IMP.DOWNSTREAM`; this kernel does not convert them into a scalar uncertainty claim.

D2 must concretize, without changing meaning:

1. physical/source/eligibility conventions and protected statistical units, including finite autocorrelation truncation, block/event rules;
2. exact `U_size -> P_train + M3`, component ordering, `pi_eval`, policy structural domain and automatic-screen sufficiency;
3. exact target-order family catalog/applicability, one-time correlation-balanced weights, metrics/radii/adjacency, distinct selector/qualification coverage predicates, extents, obligations, FEAS1, MVSEL2, REPAIR2 and MVQUAL;
4. P3 common preparation, optimizer normalization, evaluator, complete-seed score, practical-equivalence ranking, exact funnel/success-sufficiency/configured-ceiling rule and authenticated continuation;
5. selected-head foundation-residual E0 fit, replay/pretraining-head foundation E0 binding, and composition transfer;
6. replay label-mode/lineage concretization, geometry invariance, evidence-qualification currentness, true-reference replay retention observable (currently DFT / `true_dft`), exact foundation-relative signed degradation, configurable diagnostic-warning/catastrophic-hard policy with generated defaults `50/100 meV/angstrom`, robust P5 objective and exposure;
7. deterministic monitor/folds/purge; independent role target policies with generated defaults `tau_CV = 45`, `theta_CV = 45`, `tau_prod = 50 meV/angstrom`; strict minimum-target-RMSE foundation-P5 checkpoint and `single_best_final_seed` ordering; deterministic non-quality exact ties; fixed-budget semantics; assessment-policy currentness; fresh production and current-CV reauthorization;
8. typed numerical failure, precision/equivalence, exact reassessment/reuse conditions and falsification oracles.

Any needed change to a scientific estimand, role, support predicate, replay interpretation, parameter-family meaning or validity regime is an upward D1 Challenge.

## 10. Candidate status, challenge disposition and reopen condition

The accepted current D1 kernel remains `main@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`. This branch file is a **proposed material D1 renewal** responding to the 2026-09-18 stakeholder direction and the replay/target-admissibility workplan. It is not accepted authority until a fresh independent Protocol-6.4 D1 Review passes on an immutable candidate target and the stakeholder explicitly ratifies that exact reviewed target.

Independent D1 Review R1 of immutable candidate `06f1255ed39f41d178daf73985829a2190a2bee8` returned **NO-PASS with no SERIOUS CHALLENGE** to the intended scientific policy. This repaired candidate closes the six R1 authority/representation findings while preserving the same policy direction. The material scientific cautions remain part of the validity regime:

1. the `100 meV/angstrom` catastrophic replay default is not established as a universal inherited-capability safety boundary; the motivating production trajectory shows that the old `30 meV/angstrom` hard budget can reject target-competent checkpoints, but it does not prove `100` universally adequate;
2. current defaults `tau_CV=45` and `tau_prod=50 meV/angstrom` reverse the imported historical rationale that production is numerically stricter than CV. This candidate deliberately removes any required ordering between the role ceilings; their adequacy is role-specific, and production admission remains distinct from downstream physical/release qualification;
3. strict target-RMSE ordering can intentionally select a checkpoint carrying a replay-retention warning when its degradation remains below the catastrophic hard limit. That is acceptable here only because replay is defined as auxiliary inherited-capability evidence with no positive target-quality ranking role and downstream qualification remains independent;
4. `single_best_final_seed` now chooses strictly by the same authoritative target metric rather than practical-equivalence/bootstrap/secondary/maturity semantics. This narrows publication selection and must be independently falsified as a material D1 publication change.

The generated defaults `50/100 meV/angstrom` replay and `50 meV/angstrom` foundation-production target are therefore current stakeholder-selected policy calibrations, not externally validated universal constants and not substitutes for downstream adequacy evidence.

Fresh independent D1 Review must attempt to falsify at least: replay-domain/target-domain role separation; warning non-veto semantics; catastrophic hard protection; absence of replay ranking credit; target-only checkpoint and single-best publication ordering; the lack of a required numerical ordering between CV and production target ceilings; scratch/P3 isolation; fixed-budget training; current-CV authorization for current final publication; and the claim that assessment-policy-only revision does not scientifically redefine an otherwise identical realized training trajectory.

If Review passes, explicit stakeholder ratification of the exact immutable candidate is still required before this file becomes accepted-current and before Gate C may treat these D1 semantics as authority.

Reopen D1 after acceptance when material evidence indicates that the catastrophic replay default permits scientifically unacceptable inherited-capability loss relevant to claimed use; the production target default conflicts with downstream adequacy; replay must receive positive ranking credit; target-only checkpoint/publication ordering is scientifically inadequate; role-threshold independence is contradicted by evidence; or another scientific estimand, evidence role, support predicate, parameter-family meaning, validity regime or source import requires semantic change. Editorial/rendering repairs that preserve governed meaning do not reopen scientific authority.