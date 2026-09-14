---
title: "mdstats MLFF Numerical Algorithmic Method — post-selection foundation-adaptation revision candidate"
artifact_level: "D2 numerical algorithm design"
status: "candidate D2 authority on fix/mlff-post-selection-method-restoration; constrained by candidate D1; independent D1/D2 review required before integration"
baseline_accepted_date: "2026-09-13"
candidate_revision_date: "2026-09-14"
candidate_against_commit: "421e23aaed0a13443e984327bc903fc4cf4bc82e"
---

# mdstats MLFF Numerical Algorithmic Method

## 1. Purpose, scope, and authority state

This paper specifies the numerical and algorithmic method that concretizes `mlff_scientific_method.md`. It separates numerically meaningful invariants from replaceable software realization so that implementation, dependency adaptation, optimization, or restart logic cannot silently change the scientific experiment.

This candidate preserves the accepted P1/P2/P3 target-size algorithm and revises only the materially dependent post-selection foundation-adaptation method. The revised D2 scope covers:

- the robust foundation-adaptation loss functional and its exact parameterization;
- post-selection target/replay exposure semantics;
- selected-head foundation-residual elemental reference-energy fitting;
- the protected common target checkpoint monitor and its deterministic sampling rule;
- post-selection fold construction with the monitor external to `T_N`;
- the default three-fold validation geometry;
- fresh final production using the same common checkpoint method; and
- numerical failure/falsification rules needed to prevent silent fallback to the superseded method.

P3 target-size screening retains its accepted weighted objective, complete-batch update geometry, optimizer-progress normalization, candidate/evaluation orders, and reducer. Post-selection training from scratch also retains its accepted weighted energy+forces+stress objective, configuration-weight semantics, and local property masks; it is not changed merely because foundation-model P5 is restored to a different robust objective.

The branch document is a candidate replacement D2 authority. It does not become integrated current authority until the candidate D1/D2 pair receives independent review and integration acceptance. D3/D4 work must not proceed as though the new method were accepted before that gate closes.

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

A different transpose convention, implicit reference cell, or shear-factor convention is not numerically equivalent.

### 2.3 Stress normalization

Source stress is normalized to the canonical symmetric Cartesian Cauchy-stress representation and internal unit convention. Conversions preserve sign, Voigt ordering, and tensor-versus-engineering shear semantics. Virial-like quantities remain a distinct channel unless explicitly converted by an accepted owner.

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

unless an explicitly accepted override is in force. A short override is recorded as an adequacy limitation. For a contiguous run longer than `L`, the balanced all-frame split retains every eligible frame; no tail is silently dropped.

### 3.3 Protected relation closure

Full-resolution event windows are constructed before ordinary thinning. Current split-exclusion evidence contains five relation families:

1. correlation-unit membership;
2. exact geometry-duplicate membership;
3. protected-event membership;
4. condition-scoped replica lineage across distinct runs; and
5. condition-scoped structural-realization lineage across distinct runs.

The canonical P1 relation owner projects those relations to a requested frame universe and computes transitive connected components. P2 and P5 consume this authority; neither may reconstruct a reduced relation taxonomy from raw provenance or model evidence.

### 3.4 Neutrality of the target-size substrate

The neutral condition key contains reduced formula, temperature condition, strain class, regime, and optional user labels. It has no retired `label_domain_id` partition axis and constructs no pre-target-size CV plan. Upstream label compatibility still exists; compatibility-domain and preselection-CV fan-out do not.

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

Current order:

1. group components by cardinality;
2. process larger components before smaller components;
3. within one cardinality, group by the lexicographically minimum `condition_id` represented by the component;
4. sort component-member tuples canonically inside each condition bucket; and
5. round-robin buckets in sorted condition-ID order.

Given this sequence, solve exact 0/1 subset sum for target `M3`. Abstractly, with component weights `w_j`,

$$
R_0=\{0\},\qquad
R_j=R_{j-1}\cup\{r+w_j:r\in R_{j-1},\ r+w_j\le M_3\}.
$$

If `M3` is unreachable, construction fails. If reachable, selected complete components form `M3`; the complement in canonical population order forms `P_train`. An alternative implementation is equivalent only if it reproduces the same deterministic selected membership under the same policy.

## 6. Canonical training and evaluation orders

### 6.1 Condition-balanced priority order

For the relevant membership:

1. group frame UIDs by `condition_id`;
2. inside each bucket, sort by descending priority-vector coordinates with immutable frame UID as final tie-breaker; and
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

Hard-support selectors refer only to frozen pre-candidate condition evidence. They cannot inspect optimizer outcomes, evaluation scores, CV state, or runtime accidents. Qualification does not reorder, swap, repair, or expand `T_N`. Because prefixes are nested, support counts are monotone nondecreasing in `N`; contradictory qualification lineage indicates corrupt policy/evidence.

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

### 8.4 Element-support feasibility

Let `Z_req` be the set of elements whose target-head E0 values are required by target training, target checkpoint monitoring, or held-out target evaluation for one run. For each `z\in Z_{\mathrm{req}}`, the correction direction must be identifiable from the authorized fit problem or explicitly anchored by an accepted prior.

The current restoration introduces no absent-element correction prior. Therefore a zero column for required element `z` in the authorized fit matrix is a method infeasibility result. D2 does not silently set `\delta e_z=0`, borrow monitor/held-out labels, use another fold's fitted correction, or substitute an unrelated head.

Represented-element rank deficiency remains governed by the accepted rank/null-space policy. The solver records rank, singular values, null-space dimension where applicable, residual root-mean-square error (RMSE), mean absolute error (MAE), maximum error, and transfer warnings. Floating-point tolerance cannot identify a composition direction absent from `C`.

## 9. Objective and loss semantics

### 9.1 P3 and post-selection scratch remain unchanged

P3 target-size screening retains the accepted weighted energy+forces+stress objective, including global coefficients, positive per-configuration weights, and binary local property masks. Those P3 configuration weights are fitted once over exact common `P_train`, normalized to mean one, and never renormalized on candidate prefixes.

Post-selection `scratch` remains on the previously accepted weighted energy+forces+stress family with its accepted configuration-weight and local-mask semantics. This restoration does not change either P3 or P5 scratch merely to make their loss family match foundation-model P5.

### 9.2 Foundation-model P5 robust objective

For foundation-model P5 (`naive_fine_tuning` and `multihead_replay`), define the scalar Huber function

$$
H_\delta(x)=
\begin{cases}
\frac12 x^2, & |x|\le\delta,\\
\delta\left(|x|-\frac12\delta\right), & |x|>\delta.
\end{cases}
$$

The current robust threshold is

$$
\delta=0.01.
$$

For configuration `i` with `n_i` atoms, total-energy residual `\Delta E_i`, Cartesian force residuals `\Delta \mathbf F_{ia}`, Cartesian stress-tensor residuals `\Delta\sigma_{i\alpha\beta}`, and binary property masks

$$
m_i^E,m_i^F,m_i^S\in\{0,1\},
$$

the energy term is the arithmetic mean over configurations of

$$
H_\delta\!\left(m_i^E\frac{\Delta E_i}{n_i}\right).
$$

The stress term uses the canonical symmetric `3\times3` Cartesian stress representation but, matching the current reference realization, reduces **all nine stored tensor entries** rather than only the six algebraically independent components:

$$
L_S=\operatorname{mean}_{i,\alpha,\beta\in\{x,y,z\}}
H_\delta\!\left(m_i^S\Delta\sigma_{i\alpha\beta}\right).
$$

Thus off-diagonal entries of a symmetric tensor occur twice in the elementwise mean. Replacing this with a six-component Voigt reduction is a different numerical objective even when the physical tensor is symmetric.

For forces, the binary force mask is applied to reference and predicted force vectors before the robust force transform. For each atom, define the masked reference-force norm

$$
f_{ia}=\left\|m_i^F\mathbf F^{\mathrm{ref}}_{ia}\right\|_2.
$$

The per-component Huber threshold is

$$
\delta_F(f)=\delta\times
\begin{cases}
1.0, & f<100,\\
0.7, & 100\le f<200,\\
0.4, & 200\le f<300,\\
0.1, & f\ge300,
\end{cases}
$$

with force in canonical `eV/Å`. The force term is the arithmetic mean over all stored Cartesian force components of `H_{\delta_F}` applied to the masked force residual.

The total foundation-adaptation loss is

$$
L_{P5}=1\,L_E+10\,L_F+1\,L_S.
$$

The global coefficients are applied once, after the three property reductions. Binary masks express property availability, not copies of the global ratio.

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

This preserves the first-order per-epoch products `LR_N U_N` and `(beta_N)^{U_N}`. Normalized values are computed once from full candidate geometry and remain unchanged through later fidelity rungs.

### 10.3 Complete target batches

P3 ceiling update geometry is valid only when the final partial target batch is retained: `drop_last=false`, every exported target UID is exposed once per epoch, no duplicate padding completes a partial batch, and any distributed sampler must prove exact equivalent coverage/update geometry. A runtime producing `floor(N/B)` updates is a different P3 experiment.

This complete-batch rule is **not** transferred to foundation-model P5 by this restoration.

## 11. P3 continuous fidelity trajectories and restart

For active `(N,s)` with optimizer seed `s`, P3 training is one continuous trajectory through configured fidelity boundaries. The exact predecessor state includes model, optimizer, EMA where enabled, learning-rate state, and accepted Python/NumPy/Torch random-number-generator lineage. A later rung restores its authenticated predecessor rather than restarting from foundation state.

Recovery cannot change candidate membership, normalization, common preparation, seed, or boundary identity.

## 12. P3 EVAL2 target-force estimator

At boundary `j`, the exact checkpoint is evaluated on exact `M_j`. If `K` Cartesian force components are admitted,

$$
\operatorname{RMSE}_{F,\mathrm{eV/Å}}=
\sqrt{\frac1K\sum_{k=1}^K(\widehat F_k-F_k)^2},
$$

and stored target-size metric is `1000` times this value in `meV/Å`.

Inference batching is execution-only only if membership, model state, prediction semantics, and aggregate metric remain equivalent. Non-finite prediction or target metric is typed numerical failure, not an invented infinite score.

## 13. Pure target-size reducer

At each boundary, expected outcome order is size-major then seed-minor over active candidates times configured ordered seeds. Every outcome binds exact experiment definition, execution context, boundary, and evaluation-membership identity. Missing, duplicate, reordered, foreign, or lineage-incompatible evidence yields insufficient comparison rather than silent rearrangement.

A candidate gets a finite score only when **all** configured seeds have finite valid target metrics,

$$
\bar E_N=\frac1{|S|}\sum_{s\in S}E_{N,s}.
$$

The mean is never computed over a successful subset.

Given practical-equivalence tolerance `epsilon`, repeatedly define

$$
\mathcal E=\{N:E_N\le E_{\min}+\epsilon\}
$$

and choose the smallest `N` in the equivalent set. Current structural funnel is `q -> min(q,4) -> 2 -> 1`. At the terminal comparison, if configured maximum `N_max` satisfies

$$
E_{N_{\max}}+\epsilon<E_N
$$

for every other successful finalist, `N_max` is recommended and carries explicit nonconvergence-at-ceiling evidence. The reducer does not extrapolate an unconfigured size.

## 14. Foundation-model P5 sample exposure

### 14.1 Combined dataset

For multi-head replay, let target training dataset contain `N_t` configurations and replay training dataset contain `N_r`. Current P5 exposure is the unweighted concatenated dataset

$$
D_{\mathrm{train}}=D_t\Vert D_r
$$

with no target/replay balancing sampler and no intentional duplication. The authenticated training seed governs stochastic shuffle/order.

The dependency's ratio-driven target-duplication behavior is disabled. Any realized duplication factor other than one is method nonconformance.

### 14.2 Batch geometry

For the current qualified single-process, non-LBFGS foundation-adaptation path, the combined loader uses `drop_last=true`. With batch size `B`, each nominal epoch executes

$$
U=\left\lfloor\frac{N_t+N_r}{B}\right\rfloor
$$

optimizer updates and consumes exactly `UB` examples from that epoch's shuffled permutation. If `(N_t+N_r)\bmod B\ne0`, the final remainder of the shuffled permutation is omitted for that epoch.

Authenticated membership therefore does not imply that every P5 configuration is observed in every epoch. Runtime evidence must distinguish corpus membership from realized exposure and record target/replay counts, combined count, batch size, `drop_last`, seed/shuffle/sampler policy, and batches per epoch.

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

where `\0` denotes one NUL byte and `<q>` is the base-10 seed text. Sort strata by `(marker, s)`. Initialize every quota to zero and repeatedly sweep this fixed order, incrementing a stratum by one whenever its quota remains below its available frame count, until exactly 256 total slots have been assigned. This is equal-allocation subject to capacity with deterministic remainder resolution; it is not empirical-frequency weighting.

### 15.3 Deterministic time-systematic sample

For a stratum key `s` with capacity `n` and quota `k`, `1\le k\le n`, define namespace

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

Project the canonical P1 relation authority onto exact frozen `T_N` and use the canonical digest of each connected component as its component identity. Let `C` be the sorted set of component identities, `K` the fold count, `s_cv` the nonnegative partition seed, `a` the fold-construction algorithm identity, and `d_T` the selected-membership digest. If `|C|<K`, CV is infeasible.

For each component identity `c`, define

```text
salt   = <a> "|" <d_T>
marker = SHA256_HEX( UTF8( <salt> "|" <s_cv> "|" <c> ) )
```

with `<s_cv>` written in base 10. Sort components by `(marker,c)`. Assign ordered position `j` to held-out fold `j mod K`. This preserves the existing deterministic held-out membership algorithm; every protected component is held out in exactly one outer fold.

The current default is `K=3`; an explicit policy may choose any `K\ge2`. Fold count, partition seed, algorithm identity, CV horizon, required optimizer seeds, acceptance rule, and purge policy remain CV-policy identity.

### 16.2 Preserved purge selection, retired selected-only monitor

For fold `i`, let `O_i` be its held-out component set and let `R_i` be the lexicographically sorted components in `C\setminus O_i`. The accepted purge-count rule is preserved from the prior generation so monitor restoration does not cause unrelated purge drift:

$$
p_i=\min\left(p_{\mathrm{cfg}},\max(0,|R_i|-2)\right),
$$

where `p_cfg` is the configured nonnegative purge-component count.

When `p_i=0`, purge is empty. When `p_i=1`, select the middle entry `R_i[\lfloor |R_i|/2\rfloor]`. When `p_i>1`, define

$$
h=\frac{|R_i|-1}{p_i-1}
$$

and candidate indices `round_even(jh)` for `j=0,...,p_i-1`, where `round_even` is nearest-integer rounding with exact half ties to the even integer. Sort and deduplicate those indices; if fewer than `p_i` remain, append the lowest unselected integer indices until `p_i` distinct positions exist, then sort again. The purge set `P_i` contains the corresponding components.

The prior selected-only checkpoint-monitor reservation is **not performed**. Current gradient-training components are simply

$$
G_i=C\setminus(O_i\cup P_i).
$$

Thus the restoration preserves the previous outer-evaluation and purge sets and returns what would formerly have been reserved as fold-local checkpoint-monitor components to gradient training. The retired `checkpoint_monitor_components_per_fold` quantity is not a current CV-policy field.

Every selected frame is accounted for by exactly one of gradient training, held-out evaluation, or purge within each fold. No external common-monitor frame is a member of this partition.

### 16.3 Fold fitting and execution

For each fold:

1. verify exact common `M_mon` remains externally bound and relation-disjoint from the target ladder;
2. verify `G_i` can realize the required selected-head foundation-residual E0 mapping for every target element required by that run;
3. fit all fold-local E0 and other fitted training state from `G_i` only;
4. initialize a fresh model/optimizer lineage under the frozen method;
5. train for frozen CV horizon and choose an admissible checkpoint using common target monitor plus authorized replay/integrity evidence; and
6. only after representative freeze, evaluate once on held-out `O_i`.

Every configured fold and seed is required. Missing fold, failed required seed, no-admissible-checkpoint outcome, E0 support infeasibility, or method-identity mismatch is not ignored to obtain favorable acceptance.

Historical fold schemas that partitioned `T_N` into training + selected-only checkpoint monitor + held-out + purge remain historical and cannot authorize current common-monitor runs.

## 17. Checkpoint selection as constrained optimization

The post-selection checkpoint owner first filters candidates through mandatory constraints, including target-monitor admissibility, integrity, and replay-retention requirements where enabled. If the admissible set is empty, the run has no admissible checkpoint; the algorithm cannot fall back to best target error among inadmissible checkpoints.

Only after admissibility is established does deterministic target-side ranking/tie policy choose a representative. Held-out fold data are unavailable to this decision.

The same exact `M_mon` membership and checkpoint method are used for every selected size, CV fold, CV seed, and fresh final-production run. Optional lightweight target evaluation used only for stopping must be a deterministic subset of `M_mon`, never a separately sampled fold/final parent. With current 256-light/256-full budget it may equal the complete common monitor.

Replay checkpoint/retention evidence remains a distinct true-reference lineage. Existing target/replay score weights and the accepted replay-degradation budget remain separate from training-head weighting and are unchanged by this revision.

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

Final foundation-residual target E0 corrections are fitted on complete exact `T_selected` against the authenticated selected foundation checkpoint/head. The same common target checkpoint monitor `M_mon` and same replay-retention/checkpoint method used by CV control final checkpoint selection. P3 `M3` has no final checkpoint role.

For each required final seed, the representative is frozen under the accepted checkpoint/admissibility owner. Product membership is then decided before downstream qualification. Current publication may publish every required admissible final seed or one deterministic best already-frozen admissible representative under accepted target-side final ordering. Qualification/physical/locked evidence never enters cross-seed publication ranking.

## 20. Dependency realization boundary

The current qualified execution dependency is `mace-torch==0.3.16`. Dependency names and source markers are D3/D4 conformance mechanisms, but the following observed upstream semantics define the reference realization against which this D2 candidate is written:

- multi-head fine-tuning sets the dependency loss to `universal`;
- native `UniversalLoss` uses per-atom energy Huber, conditional force Huber, full `3x3` stress Huber, the configured global E/F/S coefficients, and local property masks, and does not consume the general configuration scalar `ref.weight`;
- multi-head fine-tuning can overwrite requested learning-rate/EMA semantics unless the qualified control preserves them;
- a target/replay ratio heuristic can duplicate target data unless its threshold is disabled; and
- ordinary combined single-process training uses a shuffled concatenated dataset and drops the last partial batch for non-LBFGS optimization.

Under this restoration the native forced `UniversalLoss` is **desired** for `multihead_replay`, not something mdstats should rewrite to weighted stress. `naive_fine_tuning`, which does not activate native multi-head routing, must nevertheless execute the same D2 robust functional explicitly. P3 and post-selection scratch retain their separately accepted weighted objectives.

A future dependency version may replace MACE 0.3.16 only by proving the same accepted numerical semantics or after explicit D2 revision. A source signature or Python class name is evidence of realization, not the timeless authority itself.

## 21. Numerical failure, precision, and uncertainty

### 21.1 Typed failure

Non-finite model/optimizer state, non-finite prediction/metric, invalid monitor relation overlap, impossible exact monitor size, unsupported required E0 element, stale/mismatched method identity, missing required fold/seed, or no admissible checkpoint are typed failure/infeasibility states. They are not silently converted to arbitrary scores or repaired by changing the method.

### 21.2 Atomic-reference conditioning

Rank/null-space evidence describes identifiability, not merely solver accuracy. A null direction in element-count space persists at infinite arithmetic precision unless new independent compositional information or an accepted prior changes the mathematical problem.

### 21.3 Stochasticity

Optimizer seeds are explicit replicates. P5 shuffle order under a fixed seed is part of realized stochastic exposure. Reproducibility requires preservation of accepted seed/method lineage and numerical compatibility, not unsupported bitwise identity across arbitrary hardware/library regimes.

### 21.4 Precision and backend

Learned-model dtype, critical-precision policy, acceleration/backend behavior, reduction semantics, and other trajectory-changing settings belong to method/execution identity. Worker count, queue order, cache path, and exact-evaluation device-batch width are execution-only only when they preserve accepted numerical output.

## 22. Complexity and scaling

Ignoring neural-network training cost, principal control-plane operations scale approximately as:

- autocorrelation estimation: fast-Fourier-transform dominated per observable/run plus linear block construction;
- relation closure: near-linear in frame/relation edges with union-find-style closure;
- exact `M3` allocation: pseudo-polynomial `O(C M3)` reachability work;
- condition-balanced order: at most `O(N log N)` due to sorting;
- hard-support qualification: linear in inspected prefix/obligations in the direct implementation;
- common-monitor construction: sorting plus linear quota/systematic selection over protected parent frames;
- CV component ordering/allocation: `O(C log C)` for ordering plus linear fold assignment, excluding relation closure;
- EVAL2 and target-monitor RMSE: linear in admitted components with bounded device memory through chunking; and
- reducer: `O(boundaries * candidates * seeds)` with tiny control state relative to training.

Training dominates total cost. Performance changes are admissible only when they preserve authoritative memberships, fits, trajectories, loss reductions, monitor membership, exposure semantics, and decisions.

## 23. Verification and falsification oracles

Independent D2 review should attempt at least the following counterexamples/oracles.

### 23.1 Preserved P1/P2/P3

- verify strain/stress round trips under declared conventions;
- verify autocorrelation parity and complete-frame block coverage;
- re-derive protected relation closure and reject stale split descendants;
- prove neutral target-size condition key has no compatibility-domain/CV fan-out;
- independently verify exact `M3` subset feasibility and deterministic selected membership;
- prove `pi_train`/`pi_eval` are exact permutations and every `T_N`/`M_i` exact prefixes;
- prove P3 candidate projection does not refit/renormalize common E0/weights/model normalization;
- verify P3 target batches equal `ceil(N/B)` with no duplicate padding; and
- replay reducer history and require identical decision.

### 23.2 Robust loss

- hand-evaluate energy, force, and stress toy residuals on both sides of each Huber threshold and compare to the reference realization;
- verify stress reduction uses all nine stored `3x3` entries rather than six independent tensor components;
- verify force threshold factors `1.0/0.7/0.4/0.1` and `100/200/300 eV/Å` regime boundaries exactly;
- verify global `1:10:1` coefficients are applied once outside property reductions;
- verify binary masks remove unavailable properties without introducing non-binary weighting;
- vary transport `config_weight` while holding true method fields fixed and require unchanged foundation-P5 robust loss/trajectory or reject non-neutral values before execution;
- reject any live target/replay training-head scalar;
- prove no stage-two phase silently changes the loss; and
- reject a distributed P5 route until global reduction and exposure equivalence are independently qualified.

### 23.3 Foundation residuals

- verify `y_fnd` and `e_fnd` come from exact selected checkpoint/head;
- construct a multi-head checkpoint whose first head differs from selected head and prove wrong-head fallback is rejected;
- verify CV E0 fit membership equals gradient-training target membership and excludes common monitor/held-out labels;
- construct a fold missing a required element and prove fail-closed behavior absent an accepted prior; and
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

- verify multi-head training concatenates exact authenticated target/replay corpora with no balancing scalar and duplication factor one;
- verify single-process combined `drop_last=true` batch/update geometry and distinguish membership from realized per-epoch exposure;
- verify authenticated learning-rate/EMA values survive dependency routing;
- verify true-versus-pseudo replay label changes leave replay geometry split unchanged; and
- prove old weighted-stress/fold-local-monitor continuation state cannot authenticate as the restored method.

A failure of these oracles is D2 or lower-layer nonconformance. If repair requires changing the scientific objective, monitor role, estimator, normalization, exposure, E0 identifiability rule, or validation interpretation, reopen D1/D2 rather than compensating in D3/D4.

## 24. D2 to D3 handoff

After this candidate passes independent review and becomes accepted, D3 must preserve at least:

1. separate P3/post-selection-scratch versus foundation-P5 objective/exposure owners;
2. exact foundation-P5 robust-loss identity `delta=0.01`, global `1:10:1`, nine-entry stress reduction, binary masks, and no P5 configuration/head scalar;
3. selected-head foundation-residual E0 fitting and fail-closed required-element support;
4. exact target/replay corpus lineage, no implicit target duplication, authenticated optimizer/EMA semantics, and current single-process exposure unless a distributed-equivalence qualification is accepted;
5. one current target-monitor owner over neutral protected `OUTER_MONITOR`, exact deterministic 256 membership, exact SHA-256 sampling semantics, and no current DATA5/label-domain monitor parent;
6. P5 CV schema whose fold membership excludes checkpoint monitor, preserves the deterministic outer/purge allocation above, and defaults to three folds with `K>=2` override;
7. one common target checkpoint membership shared by CV and final production, with P3 `M3` excluded from checkpoint control;
8. independent true-reference replay-monitor/retention evidence and preserved score/admissibility semantics;
9. method/currentness generations that make superseded weighted-stress/fold-local/head-scalar artifacts stale while preserving independent P1/P2/P3 and frozen membership evidence; and
10. runtime evidence sufficient to reconstruct actual loss, E0, monitor, exposure, seed, precision/backend, and fold/final lineage.

D3 remains free to choose the simplest architecture that satisfies these constraints. Existing machinery should be rewired, reduced, or retired rather than wrapped by a second competing method owner.

## 25. Reproducibility contract

A numerical reproduction binds, as applicable, exact source/frame conventions; correlated-sampling/protected-relation authority; pre-order evidence; `U_size`, `P_train/M3`, split/order/prefix identities; P3 common preparation/objective/optimizer-normalization; P3 seed/fidelity/evaluation/reducer history; frozen selected memberships and horizons; selected foundation checkpoint/head; foundation-P5 robust-loss parameters; target/replay memberships and combined exposure semantics; foundation-residual E0 fit and conditioning evidence; common target-monitor neutral parent, SHA-256 quota/systematic policy, seed, strata, and exact 256 membership; CV component-order, outer-fold, purge, seed, and exact memberships; replay training/true-monitor lineage; and fresh final-production/publication identity.

Runtime caches and scratch state need not be preserved when exactly reconstructible and non-authoritative.

## 26. References and realization evidence

1. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, “MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields,” *Advances in Neural Information Processing Systems* **35**, 11423–11436 (2022), arXiv:2206.07697.
2. H. Flyvbjerg and H. G. Petersen, “Error Estimates on Averages of Correlated Data,” *Journal of Chemical Physics* **91**, 461–466 (1989). DOI: 10.1063/1.457480.
3. C. J. Geyer, “Practical Markov Chain Monte Carlo,” *Statistical Science* **7**, 473–483 (1992). DOI: 10.1214/ss/1177011137.
4. J. Racine, “Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation,” *Journal of Econometrics* **99**, 39–61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
5. D. R. Roberts, V. Bahn, S. Ciuti, et al., “Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,” *Ecography* **40**, 913–929 (2017). DOI: 10.1111/ecog.02881.
6. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, “How to Validate Machine-Learned Interatomic Potentials,” *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.
7. ACEsuit `mace-torch==0.3.16`, `mace.modules.loss.UniversalLoss` and `conditional_huber_forces`, used as current reference realization evidence for the candidate robust functional.
8. ACEsuit `mace-torch==0.3.16`, `mace.cli.run_train`, used as current reference realization evidence for multi-head loss routing, target-duplication heuristic, selected dataset construction, loader geometry, and head-local atomic-energy behavior.

Exact current schema names, source-probe markers, package paths, persistence formats, and wrapper patch mechanics remain D3/D4 concerns except where changing them changes the numerical method above.
