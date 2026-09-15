---
title: "mdstats MLFF Numerical Algorithmic Method — foundation role-predicate separation revision"
artifact_level: "D2 numerical algorithm design"
status: "accepted-current D2 authority. The configurable foundation role-predicate revision on fix/mlff-cv-competence-threshold-separation, constrained by the accepted D1 threshold revision, passed independent D2 re-review and was stakeholder-ratified on 2026-09-15, against the post-selection restoration revision accepted 2026-09-14 and integrated at 8553ebe9ed86b24dfe910c9e43acc6230d3ece90."
baseline_accepted_date: "2026-09-14"
baseline_integrated_commit: "8553ebe9ed86b24dfe910c9e43acc6230d3ece90"
threshold_revision_accepted_date: "2026-09-15"
threshold_revision_against_commit: "8553ebe9ed86b24dfe910c9e43acc6230d3ece90"
---

# mdstats MLFF Numerical Algorithmic Method

## 1. Purpose, scope, and authority state

This paper specifies the numerical and algorithmic method that concretizes `mlff_scientific_method.md`. It separates numerically meaningful invariants from replaceable software realization so that implementation, dependency adaptation, optimization, or restart logic cannot silently change the scientific experiment.

The integrated restoration revision preserves the accepted P1/P2/P3 target-size algorithm and revises only the materially dependent post-selection foundation-adaptation method. Its D2 scope covers:

- the robust foundation-adaptation loss functional and its exact parameterization;
- post-selection target/replay exposure semantics;
- selected-head foundation-residual elemental reference-energy fitting;
- the protected common target checkpoint monitor and its deterministic sampling rule;
- post-selection fold construction with the monitor external to `T_N`;
- the default three-fold validation geometry;
- fresh final production using the same common checkpoint method (selection/admissibility mechanics; role target ceilings are separated by Section 17.1); and
- numerical failure/falsification rules needed to prevent silent fallback to the superseded method.

P3 target-size screening retains its accepted weighted objective, complete-batch update geometry, optimizer-progress normalization, candidate/evaluation orders, deterministic exact `M3` membership rule, qualification and reducer sufficiency rules, and restart semantics. Post-selection training from scratch also retains its accepted weighted energy+forces+stress objective, configuration-weight semantics, and local property masks; it is not changed merely because foundation-model P5 is restored to a different robust objective.

The restoration revision was independently reviewed, ratified on 2026-09-14, and integrated at `8553ebe9ed86b24dfe910c9e43acc6230d3ece90`.

**Accepted revision (configurable role predicates).** Section 17.1 and the associated handoff/oracle items concretize the accepted D1 separation of foundation-CV competence from fresh-production checkpoint quality, with `τ_CV`, `θ_CV`, and `τ_prod` as independently configurable policy parameters (stakeholder-ratified 2026-09-15 after independent D2 re-review). This paper is the single D2 owner of those numerical semantics.

## 2. Canonical source numerical conventions

### 2.1 Occurrence and numerical identity

Source occurrence, geometry, label payload, and labeled-configuration identities are constructed separately. Quantized fingerprints use explicit tolerances owned by current source/frame specifications. Geometry fingerprints include ordered species, periodic flags, cell, and wrapped fractional coordinates but exclude target labels, so duplicate geometry remains detectable across source occurrences or label payloads.

A different quantization/tolerance policy changes identity behavior and requires explicit compatibility treatment; floating-point object equality or path identity is not a substitute.

### 2.2 Row-vector cells and deformation gradient

For ASE row-vector cells,

$$
\mathbf r_{\mathrm{row}}=\mathbf s_{\mathrm{row}}\mathbf H.
$$

With reference cell `H_0` and current cell `H_t`, the current strain reconstruction uses

$$
\mathbf F=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

A proper polar decomposition

$$
\mathbf F=\mathbf R\mathbf U
$$

is computed by singular-value decomposition. Reflections, singular cells, or nonpositive stretch singular values are rejected. Derived strain measures include

$$
\boldsymbol\varepsilon_{\mathrm{lin}}=\frac12(\mathbf F+\mathbf F^T)-\mathbf I,
$$

$$
\mathbf E=\frac12(\mathbf F^T\mathbf F-\mathbf I),
$$

and logarithmic strain

$$
\mathbf L=\log\mathbf U.
$$

The numerical record also derives `det(F)`, rotation angle, principal logarithmic strains, hydrostatic/deviatoric measures, and engineering shear from the declared tensor convention. A different transpose convention, implicit reference cell, or shear-factor convention is not numerically equivalent.

### 2.3 Stress normalization

Source stress is normalized to the canonical symmetric Cartesian Cauchy-stress representation and internal unit convention. Conversions preserve sign, Voigt ordering, and tensor-versus-engineering shear semantics. Virial-like quantities remain a distinct channel unless explicitly converted by an accepted owner.

Stress round-trip checks are numerical falsification oracles: a sign reversal, shear-factor error, or Voigt permutation is a D1/D2 correctness failure, not a formatting issue.

### 2.4 Eligibility numerical checks

Eligibility validates finite/nonsingular geometry, atom-count consistency, required label completeness, finite force/energy fields, stress symmetry/finite values when present, and active electronic-convergence/source-quality gates. Unusual but finite values remain data; the numerical eligibility method must not introduce an implicit “typical-value” filter.

## 3. Correlated-sampling primitives and neutral statistical units

### 3.1 Exact autocorrelation estimator

The neutral substrate reuses the shared `mdstats.sampling` autocorrelation method. For a finite scalar sequence it computes unbiased fast-Fourier-transform autocovariance, normalizes to `rho(k)`, and uses Geyer's initial-positive-sequence truncation. Adjacent lag pairs are accumulated while

$$
\rho(2m-1)+\rho(2m)>0.
$$

An unpaired final positive lag may be retained. Integrated time has the canonical floor `1/2` stored frame and remains inside the accepted policy range. Constant or insufficient sequences are represented explicitly rather than assigned a fabricated long correlation time.

The effective count is

$$
N_{\mathrm{eff}}=\min\!\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
$$

No autocorrelation is computed across a source gap, continuation reset, or excluded interval.

### 3.2 Complete-frame block length

For every configured observable and contiguous run, estimate `tau`. Let

$$
\tau_{\max}=\max_{j,r}\tau_{j,r},
$$

$$
L_{\mathrm{corr}}=\max\!\left(1,\left\lceil m\tau_{\max}\right\rceil\right),
$$

and

$$
L=\max(L_{\min},L_{\mathrm{corr}})
$$

unless an explicitly accepted override is in force. A short override is recorded as an adequacy limitation rather than silently treated as decorrelated support. For a contiguous run longer than `L`, the balanced all-frame split retains every eligible frame; no remainder or tail is silently dropped.

### 3.3 Protected-event merge and relation closure

Full-resolution event windows are constructed before ordinary thinning. When a protected event crosses candidate block boundaries, the affected blocks are merged before role allocation so the protected event remains indivisible.

Current split-exclusion evidence contains five relation families:

1. correlation-unit membership;
2. exact geometry-duplicate membership;
3. protected-event membership;
4. condition-scoped replica lineage across distinct runs; and
5. condition-scoped structural-realization lineage across distinct runs.

The canonical P1 relation owner projects those relations to a requested frame universe and computes transitive connected components. P2 and P5 consume this authority; neither may reconstruct a reduced relation taxonomy from raw provenance or model evidence.

### 3.4 Neutrality of the target-size substrate

The neutral condition key contains reduced formula, temperature condition, strain class, regime, and optional user labels. It has no retired `label_domain_id` partition axis and constructs no pre-target-size cross-validation (CV) plan. Upstream label compatibility still exists; compatibility-domain and preselection-CV fan-out do not.

## 4. Pre-order selection evidence versus P3 common training preparation

### 4.1 Pre-order evidence

The canonical target order may consume candidate-independent priority vectors derived from authorized descriptor, difficulty, diversity, condition, event, environment, or other accepted selection evidence. Fitted transforms used to produce this evidence are fitted before the order on their authorized development domain and cannot inspect downstream held-out/calibration/locked labels.

The ordering owner receives either no priority evidence, represented by an empty vector per frame, or an exact finite mapping covering every bound frame. Missing, foreign, or non-finite priority values are errors.

### 4.2 P3 common candidate-training preparation

P3 common preparation is built after the exact `P_train/M3` split and canonical P2 orders exist, over exact `P_train`, and is shared by every candidate `N` and optimizer seed. Its accepted numerical state includes, as applicable, the common target atomic-reference fit, mean-one P3 configuration weights, binary property masks, foundation/head identity, target objective, and common model-construction normalization.

Candidate projection selects frozen P3 values for `T_N`. It does not renormalize configuration weights, refit E0, or recompute common model normalization on each prefix.

This P3 owner is not reused wholesale as post-selection method identity after P3/P5 objective semantics diverge. P5 may reuse individual still-applicable component policies, but an inert P3 configuration-weight digest cannot become a foundation-P5 method invariant.

## 5. Exact target-size population and development split

### 5.1 `U_size`

`U_size` is the set of exact neutral `DEVELOPMENT` frames that are currently eligible and have canonical training labels. The population must support both configured largest candidate `N_max` and largest evaluation reserve `M3`.

### 5.2 Constraint components

Project the canonical P1 protected-relation authority onto `U_size` and compute connected components. These are indivisible allocation units.

### 5.3 Deterministic exact `M3` allocation

The P3 split requires exact reserve cardinality. Component ordering is part of deterministic membership because multiple exact subsets may exist.

Current component order:

1. group components by cardinality;
2. process larger components before smaller components;
3. within one component size, group by the lexicographically minimum `condition_id` represented by the component;
4. sort component-member tuples canonically inside each condition bucket; and
5. round-robin buckets in sorted condition-ID order.

Given this ordered component sequence, solve the 0/1 exact subset-sum problem for target `M3`. The accepted dynamic program iterates components in that order and existing reachable totals in descending order; it stores the **first predecessor** by which each new reachable cardinality is obtained, stops once `M3` first becomes reachable, and reconstructs that predecessor chain. Abstractly, with component weights `w_j`,

$$
R_0=\{0\},\qquad
R_j=R_{j-1}\cup\{r+w_j:r\in R_{j-1},\ r+w_j\le M_3\}.
$$

If `M3` is unreachable, construction fails. If reachable, the predecessor chain selected under the rule above defines exact `M3`; the complement in canonical population order defines `P_train`. Exact cardinality alone is insufficient if another subset/tie rule would select different frames. An alternative implementation is equivalent only if it reproduces the same deterministic selected membership under the same policy.

The state bound is pseudo-polynomial, approximately `O(C M3)` reachability work and `O(M3)` predecessor state for `C` components.

## 6. Canonical training and evaluation orders

### 6.1 Condition-balanced priority order

For the relevant membership:

1. group frame UIDs by `condition_id`;
2. inside each bucket, sort by descending priority-vector coordinates, equivalently ascending negated coordinates, with immutable frame UID as final tie-breaker; and
3. repeatedly visit condition buckets in sorted condition-ID order, taking one frame from each nonempty bucket.

With no priority evidence, empty vectors tie and frame UID supplies within-condition order. The same deterministic rule is used for target-training and evaluation-reserve orders with their respective evidence maps.

### 6.2 Nested memberships

The target candidate is

$$
T_N=\pi_{\mathrm{train}}[:N],
$$

and evaluation rung

$$
M_i=\pi_{\mathrm{eval}}[:m_i].
$$

Membership identity binds parent-order identity, requested cardinality, and ordered frame UIDs. A stored `N` without exact parent order/prefix identity is insufficient authority.

### 6.3 Structural policy domain

The current P2 policy requires at least three strictly increasing positive power-of-two candidate sizes and exactly three strictly increasing positive power-of-two evaluation sizes. It also requires three strictly increasing positive fidelity epochs and one ordered unique nonnegative optimizer-seed population. Exact default values remain specification/configuration authority. These are current algorithm restrictions, not universal theorems.

## 7. Prefix qualification

For configured candidate size `N`, derive qualification from exact prefix:

$$
Q(N)=\text{prefix exists}\land\text{labels usable}(T_N)\land\bigwedge_j c_j(T_N)\ge q_j.
$$

Hard-support selectors refer only to frozen pre-candidate condition evidence. They cannot inspect optimizer outcomes, evaluation scores, CV state, or runtime accidents. Qualification does not reorder, swap, repair, or expand `T_N`. Because prefixes are nested and hard-support counts are membership counts, support counts are monotone nondecreasing in `N`; contradictory qualification lineage indicates corrupt policy/evidence.

The current automatic funnel requires at least **three qualified candidates** before numerical screening begins. Fewer qualified candidates yield insufficient automatic comparison rather than an altered ladder or repaired membership.

## 8. Atomic-reference fitting

### 8.1 General least-squares owner

For exact fit membership `D`, construct count matrix `C` whose row contains the number of atoms of each element in one frame, and target total-energy vector `y`.

For from-scratch fitting, the accepted regularized problem is

$$
\widehat e=\arg\min_e\left[\|Ce-y\|_2^2+\lambda\|e-e_{\mathrm{prior}}\|_2^2\right]
$$

when the corresponding prior policy is active.

For foundation-model adaptation, let `h_fnd` be the explicitly selected foundation head, `y_fnd` its predicted target-domain total energy on the authorized fit membership, and `e_fnd(h_fnd)` its elemental reference mapping. Define

$$
r=y-y_{\mathrm{fnd}},
$$

$$
\widehat{\delta e}=\arg\min_{\delta e}\left[\|C\delta e-r\|_2^2+\lambda\|\delta e-\delta e_{\mathrm{prior}}\|_2^2\right],
$$

and

$$
e_{\mathrm{target}}(h_{\mathrm{fnd}})=e_{\mathrm{fnd}}(h_{\mathrm{fnd}})+\widehat{\delta e}.
$$

Element order is keyed by atomic number, never serialized mapping order.

### 8.2 Post-selection fit domains

For foundation-model post-selection CV, `D` is exactly the fold gradient-training target membership. Neither common target checkpoint monitor nor held-out evaluation membership participates in `C`, `y`, `y_fnd`, priors fitted from target labels, or residual evaluation used to fit E0.

Fresh final production fits on exact complete `T_selected` and likewise excludes the common monitor and downstream evidence.

### 8.3 Selected-head binding

`y_fnd` and `e_fnd` must come from the same authenticated selected foundation checkpoint/head that initializes the accepted foundation-adaptation run. A dependency fallback to its first or default checkpoint head is not numerically equivalent unless that head is exactly the selected head.

For multi-head replay, replay/pretraining-head foundation E0s are likewise extracted from the authenticated selected foundation head/lineage required by the method. Target corrected E0s and replay/pretraining-head foundation E0s remain separate head-local mappings.

### 8.4 Composition-level identifiability and transfer feasibility

Individual elemental correction coefficients are not the scientific estimand. The quantity consumed by a target configuration with composition-count row vector `c` is

$$
\Delta E_0(c)=c^T\delta e.
$$

Let `N_free` be the **unanchored null space** of the authorized foundation-residual fit: directions `v` that leave all authorized training-composition equations unchanged and are not fixed by an explicitly accepted prior/anchor. With no such accepted anchor, `N_free=ker(C)`. When an accepted anchor exists, its identity and effect on the free directions are part of fit/method lineage.

The required composition correction is identifiable if and only if

$$
c^T v=0\qquad\forall v\in N_{\mathrm{free}}.
$$

Equivalently, for an unanchored least-squares fit, `c` must lie in the row space of `C` to the accepted numerical-rank tolerance. Therefore:

- a rank-deficient elemental decomposition may still give a unique correction for a governed composition;
- an element absent from `C` and present in `c` is a sufficient failure case when no accepted anchor fixes that direction; and
- a composition using only represented elements can still be infeasible if it has a component along an unanchored null direction.

For every target composition whose energy participates in gradient training, target checkpoint monitoring, or held-out target evaluation for a run, the criterion above must hold. D2 does not borrow checkpoint-monitor/held-out labels, use another fold's fitted correction, substitute an unrelated foundation head, silently set an unfitted coefficient to zero, or treat an arbitrary minimum-norm/solver-selected decomposition as scientific identification.

The solver records numerical rank, singular values, null-space basis/dimension where applicable, residual root-mean-square error (RMSE), mean absolute error (MAE), maximum error, accepted prior/anchor identity, and the composition-transfer check for each required composition class. Floating-point tolerance cannot create information absent from the authorized fit.

## 9. Objective and loss semantics

### 9.1 P3 and post-selection scratch remain unchanged

P3 target-size screening retains the accepted weighted energy+forces+stress objective, including global coefficients, positive per-configuration weights, and binary local property masks. Those P3 configuration weights are fitted once over exact common `P_train`, normalized to mean one, and never renormalized on candidate prefixes.

Post-selection `scratch` remains on the previously accepted weighted energy+forces+stress family with its accepted configuration-weight and local-mask semantics. This restoration does not change either P3 or P5 scratch merely to make their loss family match foundation-model P5.

### 9.2 Foundation-model P5 robust objective

For foundation-model P5 (`naive_fine_tuning` and `multihead_replay`), define the scalar Huber form

$$
H_\delta(x)=
\begin{cases}
\frac12 x^2, & |x|\le\delta,\\
\delta\left(|x|-\frac12\delta\right), & |x|>\delta.
\end{cases}
$$

Pinned MACE exposes one numerical `huber_delta` configuration value, currently `0.01`, but it is applied independently inside property channels with different physical units. The authoritative dimensional thresholds are therefore

$$
\delta_E=0.01\ \mathrm{eV/atom},\qquad
\delta_{F,0}=0.01\ \mathrm{eV/\mathring A},\qquad
\delta_S=0.01\ \mathrm{eV/\mathring A^3}.
$$

The shared numeric value `0.01` does **not** mean that energy, force, and stress residuals share one physical dimension. A unit conversion that changes the canonical numeric residual without converting the corresponding threshold is a different objective.

For configuration `i` with `n_i` atoms, total-energy residual `\Delta E_i`, Cartesian force residuals `\Delta \mathbf F_{ia}`, Cartesian stress-tensor residuals `\Delta\sigma_{i\alpha\beta}`, and binary property masks

$$
m_i^E,m_i^F,m_i^S\in\{0,1\},
$$

the energy term is the arithmetic mean over configurations of

$$
H_{\delta_E}\!\left(m_i^E\frac{\Delta E_i}{n_i}\right).
$$

The stress term uses the canonical symmetric `3\times3` Cartesian stress representation but, matching the reference realization, reduces **all nine stored tensor entries** rather than only the six algebraically independent components:

$$
L_S=\mathrm{mean}_{i,\alpha,\beta\in\{x,y,z\}}
H_{\delta_S}\!\left(m_i^S\Delta\sigma_{i\alpha\beta}\right).
$$

Thus off-diagonal entries of a symmetric tensor occur twice in the elementwise mean. Replacing this with a six-component Voigt reduction is a different numerical objective even when the physical tensor is symmetric.

For forces, the binary force mask is applied to reference and predicted force vectors before the robust force transform. For each atom, define the masked reference-force norm

$$
f_{ia}=\left\|m_i^F\mathbf F^{\mathrm{ref}}_{ia}\right\|_2,
$$

in `eV/Å`. The per-component force Huber threshold is

$$
\delta_F(f)=\delta_{F,0}\times
\begin{cases}
1.0, & f<100\ \mathrm{eV/\mathring A},\\
0.7, & 100\le f<200\ \mathrm{eV/\mathring A},\\
0.4, & 200\le f<300\ \mathrm{eV/\mathring A},\\
0.1, & f\ge300\ \mathrm{eV/\mathring A}.
\end{cases}
$$

The force term is the arithmetic mean over all stored Cartesian force components of `H_{delta_F}` applied to the masked force residual.

The total foundation-adaptation training objective is

$$
L_{P5}=1\,L_E+10\,L_F+1\,L_S.
$$

The `1:10:1` coefficients are method weights joining numerically different property channels; they are not a claim that the channel losses share physical units. The global coefficients are applied once, after the three property reductions. Binary masks express property availability, not copies of the global ratio.

### 9.3 No P5 `config_weight` or training-head scalar

The foundation-adaptation functional contains no independent per-configuration scalar `w_i`. A transport-level `config_weight` field, if required by a fixed-file interface, is numerically neutral and fixed to one for current P5; a nontrivial configuration-weight policy is not a current foundation-P5 method field.

There is likewise no target-versus-replay training-head scalar. The multi-head objective is produced by the authenticated target and replay examples encountered under accepted combined-loader exposure. A nominal “1:1 head weight” field is not retained as an inert knob.

Checkpoint/adaptive-stop target/replay score weights are outside this training loss and remain separately governed.

### 9.4 Reduction semantics

For the currently qualified single-process foundation-P5 path, each property reduction is the arithmetic mean of its elementwise loss tensor before application of the global property coefficient. The stress mean covers nine stored Cartesian entries per configuration and the force mean covers three entries per admitted atom.

A distributed training path is not assumed numerically equivalent merely because it invokes the same loss class. It is admissible only after qualification demonstrates the same global property means, target/replay exposure semantics, no unintended sample duplication/truncation beyond the accepted combined-batch rule, and an optimizer trajectory inside the accepted numerical-equivalence envelope. Until then, the current foundation-P5 exposure method is the qualified single-process loader described in Section 14.

### 9.5 Fixed objective across training

A stage-two/stochastic-weight-averaging phase or dependency option that changes the loss family, Huber threshold, or E/F/S coefficients defines a different numerical method. The current foundation-adaptation method therefore has no unbound phase-dependent loss mutation. Such a phase must be disabled or its exact trajectory-changing objective must be separately accepted and identity-bound before use.

## 10. P3 target-size optimizer-progress normalization

### 10.1 Confound being controlled

With target batch size `B`, candidate `N` exposes

$$
U_N=\left\lceil\frac{N}{B}\right\rceil
$$

target optimizer updates per nominal epoch when the final partial target batch is retained. Fixed per-update learning rate and exponential-moving-average (EMA) decay would therefore couple larger `N` to larger optimizer progress.

### 10.2 Current normalization

For reference size `N_ref`, reference learning rate `LR_ref`, and reference EMA decay `beta_ref`, define

$$
U_{\mathrm{ref}}=\left\lceil\frac{N_{\mathrm{ref}}}{B}\right\rceil,\qquad
s_N=\frac{U_{\mathrm{ref}}}{U_N}.
$$

P3 uses

$$
\mathrm{LR}_N=\mathrm{LR}_{\mathrm{ref}}s_N,
$$

and, when EMA is enabled,

$$
\beta_N=\beta_{\mathrm{ref}}^{s_N}.
$$

This preserves the first-order per-epoch products

$$
\mathrm{LR}_N U_N=\mathrm{LR}_{\mathrm{ref}}U_{\mathrm{ref}},
$$

and

$$
(\beta_N)^{U_N}=\beta_{\mathrm{ref}}^{U_{\mathrm{ref}}}.
$$

Normalized values are computed once from full candidate geometry and remain unchanged through later fidelity rungs. Survivor count does not rescale them.

### 10.3 Not exact optimizer-path equivalence

This is a **first-order optimizer-progress normalization**, not a theorem that candidate trajectories have identical optimization dynamics. Residual differences include minibatch stochasticity, order-dependent gradients, Adam/AMSGrad moment history, finite discretization of the learning-rate schedule, and candidate-dependent loss landscape/data composition. The intended estimand is the current normalized screening method, not an imaginary optimizer-invariant learning curve.

### 10.4 Complete target batches

P3 ceiling update geometry is valid only when the final partial target batch is retained: `drop_last=false`, every exported target UID is exposed once per epoch, no duplicate padding completes a partial batch, and any distributed sampler must prove exact equivalent coverage/update geometry. A runtime producing `floor(N/B)` updates is a different P3 experiment.

This complete-batch rule is **not** transferred to foundation-model P5 by this restoration.

## 11. P3 continuous fidelity trajectories and restart

For active `(N,s)` with optimizer seed `s`, P3 training is one continuous trajectory through configured fidelity boundaries. The exact predecessor state includes model, optimizer, EMA where enabled, learning-rate state, and accepted Python/NumPy/Torch random-number-generator lineage. A later rung restores its authenticated predecessor rather than restarting from foundation state.

Accepted progress is immutable evidence. Unaccepted first-rung materialization/checkpoint state is attempt-local scratch and may become continuation authority only after the exact accepted D3/D4 authentication boundary is established. Recovery cannot change candidate membership, normalization, common preparation, seed, or boundary identity.

## 12. P3 EVAL2 target-force estimator

At boundary `j`, the exact checkpoint is evaluated on exact `M_j`. If `K` Cartesian force components are admitted,

$$
\mathrm{RMSE}_{F,\mathrm{eV/Å}}=
\sqrt{\frac1K\sum_{k=1}^K(\widehat F_k-F_k)^2},
$$

and stored target-size metric is

$$
\mathrm{RMSE}_{F,\mathrm{meV/Å}}=1000\,\mathrm{RMSE}_{F,\mathrm{eV/Å}}.
$$

Inference batching is execution-only only if membership, model state, prediction semantics, and aggregate metric remain equivalent. Non-finite prediction or target metric is typed numerical failure, not an invented infinite score.

## 13. Pure target-size reducer

### 13.1 Ordered boundary matrix and complete-seed score

At each boundary, expected outcome order is size-major then seed-minor over active candidates times configured ordered seeds. Every outcome binds exact experiment definition, execution context, boundary, and evaluation-membership identity. Missing, duplicate, reordered, foreign, or lineage-incompatible evidence yields insufficient comparison rather than silent rearrangement.

A candidate gets a finite score only when **all** configured seeds have finite valid target metrics,

$$
\bar E_N=\frac1{|S|}\sum_{s\in S}E_{N,s}.
$$

The mean is never computed over a successful subset. Current typed target-size failures include non-finite training model state, non-finite optimizer state, non-finite evaluation prediction, and non-finite target metric.

### 13.2 Practical-equivalence order

Given practical-equivalence tolerance `epsilon`, repeatedly find current best score `E_min`, define

$$
\mathcal E=\{N:E_N\le E_{\min}+\epsilon\},
$$

choose the smallest `N` in the equivalent set, remove it, and repeat. The implementation may use only the accepted tiny fixed floating-point comparison guard in addition to scientific `epsilon`; machine epsilon is not the practical-equivalence policy and a backend failure cannot justify widening the guard.

### 13.3 Funnel and comparison sufficiency

The structural funnel is

$$
q\rightarrow\min(q,4)\rightarrow2\rightarrow1,
$$

where `q` is the number of qualified candidates entering the first boundary. At the first boundary, the number of successful candidates must be at least `min(|A_1|,4)`; the second and terminal comparisons require two successful candidates. Otherwise the reducer terminates with insufficient comparison. The exact fidelity epochs and evaluation sizes are policy values attached to these three positions, not encoded in the structural funnel name.

### 13.4 Configured-ceiling rule

If configured maximum `N_max` is a successful terminal finalist and

$$
E_{N_{\max}}+\epsilon<E_N
$$

for every other successful terminal finalist, `N_max` is materially superior, is recommended, and carries explicit nonconvergence-at-configured-ceiling evidence. Otherwise the first practical-equivalence-ranked finalist is recommended. The reducer does not extrapolate a learning curve, solve for an asymptotic root, or invent an unconfigured rescue size.

## 14. Foundation-model P5 sample exposure

### 14.1 Combined dataset and pre-shuffle corpus order

For multi-head replay, let target training dataset contain `N_t` configurations and replay/pretraining-head dataset contain `N_r`. In the pinned current two-head MACE realization, `pt_head` is ordered first and the combined dataset is constructed in head order. With `D_r` denoting the authenticated replay/pretraining-head corpus and `D_t` the authenticated target corpus, current P5 therefore uses

$$
D_{\mathrm{train}}=D_r\Vert D_t.
$$

This pre-shuffle corpus/index layout is numerically material under fixed-seed stochastic training. The loader shuffles integer indices of the combined dataset; swapping the two corpus blocks while keeping the same seed changes the mapping from shuffled indices to examples, and therefore can change minibatch composition, gradient order, and the optimizer trajectory. Replay-first/target-second is not asserted as a universally preferable ordering; it is the current accepted exposure semantics inherited from the pinned native realization. D3/D4 must not add a target-first reorder wrapper merely to reproduce superseded prose.

There is no target/replay balancing sampler and no intentional duplication. The authenticated training seed governs stochastic shuffle/order over this ordered combined index space.

The dependency's ratio-driven target-duplication behavior is disabled. Any realized duplication factor other than one is method nonconformance.

### 14.2 Batch geometry

For the current qualified single-process, non-LBFGS foundation-adaptation path, the combined loader uses `drop_last=true`. With batch size `B`, each nominal epoch executes

$$
U=\left\lfloor\frac{N_t+N_r}{B}\right\rfloor
$$

optimizer updates and consumes exactly `UB` examples from that epoch's shuffled permutation. If `(N_t+N_r)\bmod B\ne0`, the final remainder of the shuffled permutation is omitted for that epoch.

Authenticated membership therefore does not imply that every P5 configuration is observed in every epoch. Runtime evidence must distinguish corpus membership from realized exposure and record target/replay counts, combined count, the ordered pre-shuffle head/corpus layout, batch size, `drop_last`, seed/shuffle/sampler policy, and batches per epoch.

For `naive_fine_tuning`, `N_r=0`: the same robust objective and target-only shuffled loader semantics apply, with

$$
U=\left\lfloor\frac{N_t}{B}\right\rfloor.
$$

For current P5, a distributed sampler is not silently substituted for this exposure rule; distributed execution requires the separate equivalence qualification stated in Section 9.4.

### 14.3 Optimizer mutation is forbidden

The accepted post-selection learning-rate/EMA semantics are resolved by mdstats and must not be silently overwritten by dependency multi-head defaults. The current qualified dependency control that preserves those values is an implementation mechanism; D2's invariant is that the authenticated optimizer schedule and EMA parameters remain the executed values.

## 15. Common target checkpoint monitor construction

### 15.1 Parent and exact size

Let `P_mon` be the exact protected neutral `OUTER_MONITOR` target frame population after canonical label usability is applied. Current foundation-model P5 requires one exact common target monitor `M_mon` of size

$$
|M_{\mathrm{mon}}|=256.
$$

If fewer than 256 usable protected parent frames exist, current P5 is infeasible. There is no smaller-monitor fallback in the current method.

The canonical P1 split-exclusion authority must show that no selected monitor frame shares a protected relation component with any frame in every configured `T_N` relevant to the frozen experiment. Exact frame disjointness alone is insufficient.

### 15.2 Condition/run strata and exact quota order

Each parent frame is assigned to the string key

```text
<condition_id>:<run_id>
```

and frames inside a stratum are ordered by `(source_frame_index, frame_uid)`.

Let the current monitor seed be

$$
q=161803.
$$

For each nonempty stratum key `s`, define its quota-order marker as the lowercase hexadecimal SHA-256 digest of the UTF-8 byte string

```text
<q>\0quota\0<s>
```

where `\0` denotes one NUL byte and `<q>` is the base-10 seed text. Sort strata by `(marker, s)`. Initialize every quota to zero and repeatedly sweep this fixed order, incrementing a stratum by one whenever its quota remains below its available frame count, until exactly 256 total slots have been assigned. This is equal allocation subject to capacity with deterministic remainder resolution; it is not empirical-frequency weighting.

### 15.3 Deterministic time-systematic sample

For a stratum key `s` with capacity `n` and quota `k`, `1<=k<=n`, define namespace

```text
target:<s>
```

and compute

```text
raw = SHA256( UTF8( <q> "\0" <namespace> ) )
I   = unsigned big-endian integer represented by raw[0:8]
u   = (I + 0.5) / 2^64
```

where `raw[0:8]` means the first eight digest bytes. If `k=n`, select all positions. Otherwise select

$$
p_j=\min\!\left(n-1,\left\lfloor\frac{(j+u)n}{k}\right\rfloor\right),
\qquad j=0,\ldots,k-1.
$$

The resulting positions must be distinct; duplicate positions are construction failure. Selected monitor records may be persisted in canonical `(run_id, source_frame_index, frame_uid)` order after membership has been fixed.

The numerical identity binds current neutral parent identity, exact selected membership, requested/realized size, seed, strategy, and per-stratum available/selected counts. A different deterministic sampler producing another 256-frame set is a different monitor identity even if it appears similarly balanced.

### 15.4 Parent adequacy is not created by sampling

The sampler cannot manufacture missing conditions, runs, independence, or time coverage. Qualification must therefore report actual parent support, represented condition/run strata, available-to-selected counts, temporal spread, and upstream independence/effective-support evidence. D2 introduces no arbitrary new generic minimum-run or minimum-unit constant.

## 16. Post-selection fold construction and fitting

### 16.1 Preserved deterministic outer-fold geometry

After operator selection is frozen, each admitted `T_N` is validated separately. Current P5 fold construction remains downstream of target-size selection and is not a revived DATA5 preselection-CV authority.

Project the canonical P1 relation authority onto exact frozen `T_N` and use the canonical digest of each connected component as its component identity. Let `C_comp` be the sorted set of component identities, `K` the fold count, `s_cv` the nonnegative partition seed, `a` the fold-construction algorithm identity, and `d_T` the selected-membership digest. If `|C_comp|<K`, CV is infeasible.

For each component identity `c`, define

```text
salt   = <a> "|" <d_T>
marker = SHA256_HEX( UTF8( <salt> "|" <s_cv> "|" <c> ) )
```

with `<s_cv>` written in base 10. Sort components by `(marker,c)`. Assign ordered position `j` to held-out fold `j mod K`. This preserves the existing deterministic held-out membership algorithm; every protected component is held out in exactly one outer fold.

The current default is `K=3`; an explicit policy may choose any `K>=2`. Fold count, partition seed, algorithm identity, CV horizon, required optimizer seeds, acceptance rule, and purge policy remain CV-policy identity.

### 16.2 Preserved purge selection, retired selected-only monitor

For fold `i`, let `O_i` be its held-out component set and let `R_i` be the lexicographically sorted components in `C_comp\setminus O_i`. The accepted purge-count rule is preserved from the prior generation so monitor restoration does not cause unrelated purge drift:

$$
p_i=\min\left(p_{\mathrm{cfg}},\max(0,|R_i|-2)\right),
$$

where `p_cfg` is the configured nonnegative purge-component count.

When `p_i=0`, purge is empty. When `p_i=1`, select the middle entry `R_i[floor(|R_i|/2)]`. When `p_i>1`, define

$$
h=\frac{|R_i|-1}{p_i-1}
$$

and candidate indices `round_even(jh)` for `j=0,...,p_i-1`, where `round_even` is nearest-integer rounding with exact half ties to the even integer. Sort and deduplicate those indices; if fewer than `p_i` remain, append the lowest unselected integer indices until `p_i` distinct positions exist, then sort again. The purge set `P_i` contains the corresponding components.

The prior selected-only checkpoint-monitor reservation is **not performed**. Current gradient-training components are simply

$$
G_i=C_{\mathrm{comp}}\setminus(O_i\cup P_i).
$$

Thus the restoration preserves the previous outer-evaluation and purge sets and returns what would formerly have been reserved as fold-local checkpoint-monitor components to gradient training. The retired `checkpoint_monitor_components_per_fold` quantity is not a current CV-policy field.

Every selected frame is accounted for by exactly one of gradient training, held-out evaluation, or purge within each fold. No external common-monitor frame is a member of this partition.

### 16.3 Fold fitting and execution

For each fold:

1. verify exact common `M_mon` remains externally bound and relation-disjoint from the target ladder;
2. build the selected-head foundation-residual E0 fit from `G_i` only and verify `c^T v=0` for every required target composition `c` and every unanchored null direction `v`;
3. fit all other fold-local training state from `G_i` only;
4. initialize a fresh model/optimizer lineage under the frozen method;
5. train for the frozen CV horizon (fixed budget; crossing any ceiling does not stop training) and choose an admissible checkpoint using the common target monitor under the CV role-effective admissibility predicate of Section 17.1 plus authorized replay/integrity evidence; and
6. only after representative freeze, evaluate once on held-out `O_i` and apply the CV outer acceptance predicate of Section 17.1.

Every configured fold and seed is required. Missing fold, failed required seed, no-admissible-checkpoint outcome, composition-transfer E0 infeasibility, or method-identity mismatch is not ignored to obtain favorable acceptance.

Historical fold schemas that partitioned `T_N` into training + selected-only checkpoint monitor + held-out + purge remain historical and cannot authorize current common-monitor runs.

## 17. Checkpoint selection as constrained optimization

The post-selection checkpoint owner first filters candidates through mandatory constraints, including target-monitor admissibility, integrity, and replay-retention requirements where enabled. If the admissible set is empty, the run has no admissible checkpoint; the algorithm cannot fall back to best target error among inadmissible checkpoints.

Only after admissibility is established does deterministic target-side ranking/tie policy choose a representative. Held-out fold data are unavailable to this decision.

The same exact `M_mon` membership and checkpoint method are used for every selected size, CV fold, CV seed, and fresh final-production run. Optional lightweight target evaluation used only for stopping must be a deterministic subset of `M_mon`, never a separately sampled fold/final parent. With current 256-light/256-full budget it may equal the complete common monitor.

Replay checkpoint/retention evidence remains a distinct true-reference lineage. Existing target/replay score weights and the accepted replay-degradation budget remain separate from training-head weighting and are unchanged by this revision.

### 17.1 Role-effective predicates

Let `r_mon(c)` be the target force-component RMSE of checkpoint `c` on `M_mon` and `r_out` the target force-component RMSE of a frozen fold representative on held-out `O_i`, both in `eV/Å` as defined by the accepted EVAL2 target-force estimator. Let `S(c)` be the conjunction of the **shared** mandatory constraints: finite metrics; replay degradation `<=` the accepted budget with authenticated true-reference evidence where replay is enabled; and required physical/integrity gates. `S` is part of the shared method and is identical for every role.

A run of role `ρ` uses exactly one effective admissibility predicate

$$
A_\rho(c) \;=\; S(c) \;\wedge\; r_{\mathrm{mon}}(c) \le \tau_\rho ,
$$

with inclusive boundaries, compared in IEEE-754 double precision against the double nearest the resolved decimal ceiling. For foundation adaptation (`naive_fine_tuning`, `multihead_replay`), the role thresholds are independently resolved finite positive policy parameters; no numerical rule requires an explicitly configured value to equal its generated default:

| Role | Predicate | Resolved ceiling / default |
|---|---|---|
| CV checkpoint competence | `r_mon(c) <= τ_CV` | `τ_CV`, default `0.045 eV/Å` |
| CV outer acceptance, default metric `target_force_rmse_ev_per_angstrom` | `r_out <= θ_CV` | `θ_CV`, default `0.045 eV/Å` |
| Production checkpoint quality | `r_mon(c) <= τ_prod` | `τ_prod`, default `0.030 eV/Å` |

Required properties:

1. **Boundary.** `r = τ` passes; the next representable double above `τ` fails.
2. **Dimensional separation.** `τ_CV` is always a target-force RMSE ceiling in `eV/Å`. An explicitly configured alternative outer metric (energy, quantile, species or stratum metric) carries its own units and `θ`, and never supplies `τ_CV`. `τ_CV` is reconstructable without reference to the outer metric.
3. **Population separation.** `τ_CV` is evaluated on `M_mon` and `θ_CV` on `O_i`. Equal numeric values do not make the estimators interchangeable.
4. **Aggregation.** CV accepts only if every required `(fold, seed)` position has a non-empty admissible set under `A_CV` and its representative satisfies the outer predicate. No mean/majority/best-seed aggregate exists; dispersion statistics are recorded but never enter the decision.
5. **No reinterpretation.** A candidate classification computed under one `A_ρ` is evidence only for that predicate. Re-thresholding stored metrics under a different `τ` does not produce current evidence; the run is re-evaluated under the current role authority.
6. **Fixed budget.** No predicate alters the training horizon or terminates training.
7. **Scratch.** Post-selection scratch keeps its pre-separation criteria: checkpoint target ceiling from the accepted target acceptance value (currently `0.030 eV/Å`) for both roles and default outer ceiling `0.030 eV/Å`.
8. **Selective invalidation.** A threshold change moves only its role lineage. A `τ_CV` or `θ_CV` change moves the CV role policy, plan/run positions and CV acceptance, stales production authorization derived from that acceptance, and leaves the shared method and `τ_prod` unchanged. A `τ_prod` change moves only the production role policy and plan/run positions; applicable accepted CV evidence and the shared method remain current. A change to `S` (replay budget, physical/integrity gates) is a shared-method change and can invalidate both roles.
9. **Resolution equivalence.** Explicitly configuring a threshold at its default is equivalent to omitting it when every other policy input is equal; identity binds the resolved value.

Pre-separation records, in which one `τ` was represented as part of the shared method, remain historical and do not authorize work under Section 17.1.

## 18. Replay semantics

### 18.1 Separation from P3

P3 target-size execution has zero replay training samples. P5 replay cannot alter P2/P3 evidence or frozen target membership.

### 18.2 Replay label modes

Current post-selection architecture supports true-reference/density-functional-theory (DFT) replay as canonical default when labels are available and foundation pseudo-label replay only under explicit opt-in bound to frozen foundation checkpoint/head. Pseudo-label replay still requires a separate true-reference replay-monitor lineage.

Replay source membership, geometry split, label mode, true-monitor membership, head identity, foundation identity, and realized exposure belong to P5 lineage. Switching true versus pseudo training labels over one prepared source/split must not change replay geometry membership.

### 18.3 No head scalar and no hidden duplication

No target/replay training-head scalar participates in current robust P5 loss. No dependency ratio heuristic may duplicate target examples. Any future intentional resampling/balancing is a different D2 method and requires explicit reopening.

## 19. Fresh final production and publication selection

Fresh final production starts a new lineage on complete exact `T_selected`; P3 and CV checkpoints are never warm-start parents.

Final foundation-residual target E0 corrections are fitted on complete exact `T_selected` against the authenticated selected foundation checkpoint/head. Every target composition whose energy is consumed by final training or target monitor control must satisfy the same composition-level null-space identifiability test. The same common target checkpoint monitor `M_mon` and same replay-retention/checkpoint-selection method used by CV control final checkpoint selection, under the production role ceiling `τ_prod` of Section 17.1 rather than `τ_CV`. P3 `M3` has no final checkpoint role.

For each required final seed, the representative is frozen under the accepted checkpoint/admissibility owner. Product membership is then decided before downstream qualification. Current publication may publish every required admissible final seed or one deterministic best already-frozen admissible representative under accepted target-side final ordering. Qualification/physical/locked evidence never enters cross-seed publication ranking.

## 20. Dependency realization boundary

The current qualified execution dependency is `mace-torch==0.3.16`. Dependency names and source markers are D3/D4 conformance mechanisms, but the following observed upstream semantics define the reference realization against which this D2 revision is written:

- multi-head fine-tuning sets the dependency loss to `universal`;
- native `UniversalLoss` uses per-atom energy Huber, conditional force Huber, full `3x3` stress Huber, configured global E/F/S coefficients, and local property masks, and does not consume the general configuration scalar `ref.weight`;
- the single numeric `huber_delta` is applied separately to energy, force, and stress numeric residuals in their canonical property units;
- multi-head fine-tuning can overwrite requested learning-rate/EMA semantics unless the qualified control preserves them;
- a target/replay ratio heuristic can duplicate target data unless its threshold is disabled;
- current two-head multi-head fine-tuning orders `pt_head` first and concatenates datasets in that head order, so the replay/pretraining corpus precedes the target corpus in the combined index space before seeded shuffle; and
- ordinary combined single-process training uses a shuffled concatenated dataset and drops the last partial batch for non-LBFGS optimization.

Under this restoration the native forced `UniversalLoss` is **desired** for `multihead_replay`, not something mdstats should rewrite to weighted stress. `naive_fine_tuning`, which does not activate native multi-head routing, must nevertheless execute the same D2 robust functional explicitly. P3 and post-selection scratch retain their separately accepted weighted objectives.

A future dependency version may replace MACE 0.3.16 only by proving the same accepted numerical semantics or after explicit D2 revision. A source signature or Python class name is evidence of realization, not the timeless authority itself.

## 21. Numerical failure, conditioning, precision, and uncertainty

### 21.1 Typed failure

Non-finite model/optimizer state, non-finite prediction/metric, invalid monitor relation overlap, impossible exact monitor size, non-identifiable required composition correction, stale/mismatched method identity, missing required fold/seed, or no admissible checkpoint are typed failure/infeasibility states. They are not silently converted to arbitrary scores or repaired by changing the method.

### 21.2 Atomic-reference conditioning

Rank/null-space evidence describes identifiability, not merely solver accuracy. A null direction in element-count space persists at infinite arithmetic precision unless new independent compositional information or an accepted prior/anchor changes the mathematical problem. Rank deficiency alone is not a transfer failure: the relevant failure occurs when a required composition vector is not orthogonal to the unanchored null space.

### 21.3 Stochasticity

Optimizer seeds are explicit replicates. P5 shuffle order under a fixed seed is part of realized stochastic exposure, including the mapping from combined-dataset indices to replay/target examples before the permutation is drawn. P3 pairing controls one source of comparative variation but does not remove minibatch, finite-horizon, or model-training uncertainty. Reproducibility requires preservation of accepted seed/method lineage and numerical compatibility, not unsupported bitwise identity across arbitrary hardware/library regimes.

### 21.4 Precision and backend

Learned-model dtype, critical-precision policy, acceleration/backend behavior, reduction semantics, numerical-rank tolerance, and other trajectory- or identifiability-changing settings belong to method/execution identity. Worker count, queue order, cache path, and exact-evaluation device-batch width are execution-only only when they preserve accepted numerical output.

## 22. Complexity and scaling

Ignoring neural-network training cost, principal control-plane operations scale approximately as:

- autocorrelation estimation: fast-Fourier-transform dominated per observable/run plus linear block construction;
- relation closure: near-linear in frame/relation edges with union-find-style closure;
- exact `M3` allocation: pseudo-polynomial `O(C M3)` reachability work with `O(M3)` predecessor state;
- condition-balanced order: at most `O(N log N)` due to sorting;
- hard-support qualification: linear in inspected prefix/obligations in the direct implementation;
- composition-level E0 transfer checks: dominated by the fit's singular-value/null-space factorization plus matrix products over required composition classes;
- common-monitor construction: sorting plus linear quota/systematic selection over protected parent frames;
- CV component ordering/allocation: `O(C log C)` for ordering plus linear fold assignment, excluding relation closure;
- EVAL2 and target-monitor RMSE: linear in admitted components with bounded device memory through chunking; and
- reducer: `O(boundaries * candidates * seeds)` with tiny control state relative to training.

Training dominates total cost. Performance changes are admissible only when they preserve authoritative memberships, fits, trajectories, loss reductions, monitor membership, exposure semantics, and decisions.

## 23. Verification and falsification oracles

D2 review and verification should attempt at least the following counterexamples/oracles.

### 23.1 Preserved P1/P2/P3

- verify strain/stress round trips under declared conventions and derived strain quantities;
- verify autocorrelation parity, complete-frame block coverage without dropped tails, and block merging when protected events cross candidate boundaries;
- re-derive protected relation closure and reject stale split descendants;
- prove neutral target-size condition key has no compatibility-domain/CV fan-out;
- independently verify exact `M3` subset feasibility and reproduce the accepted first-predecessor/descending-reachable-state selected membership when multiple exact subsets exist;
- prove `pi_train`/`pi_eval` are exact permutations and every `T_N`/`M_i` exact prefixes;
- verify fewer than three qualified candidates cannot enter automatic screening;
- prove P3 candidate projection does not refit/renormalize common E0/weights/model normalization;
- verify P3 target batches equal `ceil(N/B)` with no duplicate padding;
- verify LR/EMA normalization preserves the stated first-order products without claiming exact optimizer-path equivalence;
- verify first/second/terminal reducer sufficiency rules, the tiny comparison guard, configured-ceiling rule, and incomplete/reordered matrix failure; and
- replay reducer history and require identical decision.

### 23.2 Robust loss and dimensions

- hand-evaluate energy, force, and stress toy residuals on both sides of each property-specific Huber threshold and compare to the reference realization;
- verify `delta_E=0.01 eV/atom`, base `delta_F=0.01 eV/Å`, and `delta_S=0.01 eV/Å^3` while all derive from the same configured numeric value;
- verify a unit conversion without corresponding threshold conversion is rejected as non-equivalent;
- verify stress reduction uses all nine stored `3x3` entries rather than six independent tensor components;
- verify force threshold factors `1.0/0.7/0.4/0.1` and `100/200/300 eV/Å` regime boundaries exactly;
- verify global `1:10:1` coefficients are applied once outside property reductions;
- verify binary masks remove unavailable properties without introducing non-binary weighting;
- vary transport `config_weight` while holding true method fields fixed and require unchanged foundation-P5 robust loss/trajectory or reject non-neutral values before execution;
- reject any live target/replay training-head scalar;
- prove no stage-two phase silently changes the loss; and
- reject a distributed P5 route until global reduction and exposure equivalence are independently qualified.

### 23.3 Foundation residuals and identifiability

- verify `y_fnd` and `e_fnd` come from exact selected checkpoint/head;
- construct a multi-head checkpoint whose first head differs from selected head and prove wrong-head fallback is rejected;
- verify CV E0 fit membership equals gradient-training target membership and excludes common monitor/held-out labels;
- for a rank-deficient fit with composition rows proportional to `[1,1]`, verify another `[1,1]` target composition is admissible even though individual elemental coefficients are not unique;
- under that same fit, verify a `[2,1]` target composition is rejected because its correction varies along the null direction;
- construct a required composition containing an element absent from the fit and verify fail-closed behavior absent an accepted anchor;
- verify an accepted prior/anchor changes identifiability only when its identity and constrained direction are explicitly method-bound; and
- verify final fit uses complete `T_selected` only.

### 23.4 Common monitor

- independently reconstruct the 256-frame monitor from protected parent, exact SHA-256 quota order, seed, strata, and systematic positions;
- prove exact membership is identical across selected sizes, folds, seeds, and final production;
- prove exact and protected-component disjointness from every configured `T_N`;
- reject parent support below 256 or unusable target labels rather than shrink/fallback;
- verify available-to-selected condition/run counts and time spread are recorded; and
- reject any fold-local/final-local/M3 target checkpoint parent.

### 23.5 CV geometry

- reconstruct seeded component order independently from `(algorithm identity, selected-membership digest, partition seed, component identity)`;
- prove every component is held out exactly once across `K` outer folds;
- prove purge components exactly match the preserved spaced-selection rule;
- prove removal of selected-only monitor reservation changes neither outer nor purge membership and returns all non-outer/non-purge components to gradient training; and
- prove current CV policy has no live `checkpoint_monitor_components_per_fold` field.

### 23.6 Exposure/currentness

- verify multi-head training concatenates the exact authenticated replay/pretraining corpus **first** and target corpus **second** in the pre-shuffle combined index space, matching native `pt_head`-first head order;
- with the same fixed seed and memberships, demonstrate that swapping those corpus blocks changes the example mapping of the shuffled index permutation and is therefore non-equivalent unless separately qualified;
- verify there is no balancing scalar and realized duplication factor is one;
- verify single-process combined `drop_last=true` batch/update geometry and distinguish membership from realized per-epoch exposure;
- verify authenticated learning-rate/EMA values survive dependency routing;
- verify true-versus-pseudo replay label changes leave replay geometry split unchanged; and
- prove old weighted-stress/fold-local-monitor/target-first-order continuation state cannot authenticate as the restored method.

### 23.7 Role predicates

Default-policy oracles (generated defaults `τ_CV=θ_CV=0.045 eV/Å`, `τ_prod=0.030 eV/Å`; they test the defaults, not a fixed-threshold invariant):

- foundation CV: `r_mon=0.042` admissible and `r_out=0.042` accepted; `r=0.045` passes and `nextafter(0.045, +inf)` fails;
- foundation production: `r_mon=0.042` inadmissible; `r=0.030` passes and `nextafter(0.030, +inf)` fails;
- default scratch: `r_mon=0.042` remains inadmissible in both roles;
- a non-target-force outer metric with a large `θ` leaves `τ_CV` at its resolved value (default `0.045 eV/Å`);

Configured-policy oracles (any finite positive resolved value):

- for each resolved target-force ceiling `τ`, `r=τ` passes and `nextafter(τ, +inf)` fails;
- an explicit non-default `τ_CV` changes only the CV role-policy lineage and is honored by CV checkpoint assessment; the shared method and `τ_prod` are unchanged, and CV acceptance under the prior `τ_CV` no longer authorizes production;
- an explicit non-default `θ_CV` changes only the CV outer-policy lineage and is honored in held-out acceptance without changing checkpoint target-force units;
- an explicit non-default `τ_prod` changes only the production role-policy lineage and is honored by production checkpoint assessment;
- an explicit default is equivalent to omission;
- one failing required position rejects CV even when the mean outer metric is below `θ_CV`;
- a shared-constraint change (e.g. replay budget) changes shared method identity; a role-ceiling change changes only that role's policy; and
- stored candidate classifications under one `τ` are not reused under another.

A failure of these oracles is D2 or lower-layer nonconformance. If repair requires changing the scientific objective, monitor role, estimator, normalization, exposure, composition-level E0 identifiability rule, or validation interpretation, reopen D1/D2 rather than compensating in D3/D4.

## 24. D2 to D3 handoff

D3 must preserve at least:

1. the unchanged P1/P2/P3 numerical method, including event/block closure, exact deterministic `M3` membership, minimum qualified-candidate admission, first-order optimizer-normalization interpretation, reducer comparison sufficiency, and target-size restart semantics;
2. separate P3/post-selection-scratch versus foundation-P5 objective/exposure owners;
3. exact foundation-P5 robust-loss identity: property-specific dimensional thresholds corresponding to configured numeric `huber_delta=0.01`, global `1:10:1`, nine-entry stress reduction, binary masks, and no P5 configuration/head scalar;
4. selected-head foundation-residual E0 fitting plus composition-level null-space transfer validation for every governed target composition, with accepted anchors identity-bound and no monitor/held-out leakage;
5. exact target/replay corpus lineage, native two-head replay/`pt_head`-first then target-second pre-shuffle index layout, no implicit target duplication, authenticated optimizer/EMA semantics, and current single-process exposure unless a distributed-equivalence qualification is accepted;
6. one current target-monitor owner over neutral protected `OUTER_MONITOR`, exact deterministic 256 membership, exact SHA-256 sampling semantics, and no current DATA5/label-domain monitor parent;
7. P5 CV schema whose fold membership excludes checkpoint monitor, preserves the deterministic outer/purge allocation above, and defaults to three folds with `K>=2` override;
8. one common target checkpoint membership shared by CV and final production, with P3 `M3` excluded from checkpoint control;
9. independent true-reference replay-monitor/retention evidence and preserved score/admissibility semantics, with the shared constraints `S` owned by the shared method and the independently configurable role thresholds `τ_CV`, `θ_CV`, `τ_prod` of Section 17.1 owned by the role policies (each identity-bearing only for its own role, never for the shared method, with exactly one configuration source each and no synchronized alias or second checkpoint-policy engine), one role-effective predicate bound per run before its checkpoints are evaluated;
10. method/currentness generations that make superseded weighted-stress/fold-local/head-scalar/target-first artifacts stale while preserving independent P1/P2/P3 and frozen membership evidence; and
11. runtime evidence sufficient to reconstruct actual loss, dimensional thresholds, E0 fit/null-space transfer result, monitor, ordered combined-corpus layout, realized exposure, seed, precision/backend, and fold/final lineage.

D3 remains free to choose the simplest architecture that satisfies these constraints. Existing machinery should be rewired, reduced, or retired rather than wrapped by a second competing method owner.

## 25. Reproducibility contract

A numerical reproduction binds, as applicable, exact source/frame conventions; correlated-sampling/block/event-merge and protected-relation authority; pre-order evidence; `U_size`, deterministic `P_train/M3` split including predecessor/tie semantics, split/order/prefix identities; P3 common preparation/objective/optimizer-normalization and its first-order interpretation; P3 candidate admission, seed/fidelity/evaluation/reducer sufficiency/history; frozen selected memberships and horizons; selected foundation checkpoint/head; foundation-P5 robust-loss parameters and dimensional thresholds; target/replay memberships, ordered pre-shuffle combined-corpus/head index layout, and realized exposure semantics; foundation-residual E0 fit, accepted anchors, rank/null-space evidence, required composition set, and composition-transfer identifiability result; common target-monitor neutral parent, SHA-256 quota/systematic policy, seed, strata, and exact 256 membership; CV component-order, outer-fold, purge, seed, and exact memberships; replay training/true-monitor lineage; and fresh final-production/publication identity.

Runtime caches and scratch state need not be preserved when exactly reconstructible and non-authoritative.

## 26. Revision provenance and realization evidence

The 2026-09-13 accepted D2 baseline remains the source of all unaffected P1/P2/P3 semantics. The first independent review found that the initial rewrite had accidentally compressed out several still-current baseline invariants and had conflated elemental-coefficient identifiability with composition-energy identifiability. That review repair restored the baseline invariants explicitly, narrowed the new E0 feasibility rule to the scientifically consumed composition-weighted corrections, and made the shared numeric Huber parameter dimensionally explicit per property channel. A subsequent re-review found one remaining D2 reproducibility defect: the candidate had written the combined multi-head corpus as target-first/replay-second even though pinned MACE orders `pt_head` first and shuffles the resulting replay-first/target-second combined index space. That ordering was corrected and bound to exposure identity/oracles. Final independent re-review then passed the repaired D1/D2 pair, and the stakeholder ratified the branch authority on 2026-09-14 by directing D3/D4 closure to proceed. It was integrated at `8553ebe9ed86b24dfe910c9e43acc6230d3ece90`.

The role-predicate parameterization (Sections 17.1, 23.7, handoff item 9) was accepted after independent D2 re-review and the stakeholder's 2026-09-15 ratification that all three foundation post-selection thresholds are configurable policy parameters. It establishes foundation defaults `τ_CV=θ_CV=0.045 eV/Å` and `τ_prod=0.030 eV/Å` from a stakeholder-authorized calibration premise (D1 §10.3) and leaves scratch unchanged. The cycle is recorded in `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_ALIGNMENT.md` and `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_D1_D2_REREVIEW.md`.

Reference realization evidence:

1. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, “MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields,” *Advances in Neural Information Processing Systems* **35**, 11423–11436 (2022), arXiv:2206.07697.
2. H. Flyvbjerg and H. G. Petersen, “Error Estimates on Averages of Correlated Data,” *Journal of Chemical Physics* **91**, 461–466 (1989). DOI: 10.1063/1.457480.
3. C. J. Geyer, “Practical Markov Chain Monte Carlo,” *Statistical Science* **7**, 473–483 (1992). DOI: 10.1214/ss/1177011137.
4. J. Racine, “Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation,” *Journal of Econometrics* **99**, 39–61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
5. D. R. Roberts, V. Bahn, S. Ciuti, et al., “Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,” *Ecography* **40**, 913–929 (2017). DOI: 10.1111/ecog.02881.
6. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, “How to Validate Machine-Learned Interatomic Potentials,” *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.
7. ACEsuit `mace-torch==0.3.16`, `mace.modules.loss.UniversalLoss` and `conditional_huber_forces`, used as current reference realization evidence for the robust functional.
8. ACEsuit `mace-torch==0.3.16`, `mace.cli.run_train`, used as current reference realization evidence for multi-head loss routing, target-duplication heuristic, selected dataset/head ordering, loader geometry, and head-local atomic-energy behavior.

Exact current schema names, source-probe markers, package paths, persistence formats, and wrapper patch mechanics remain D3/D4 concerns except where changing them changes the numerical method above.
