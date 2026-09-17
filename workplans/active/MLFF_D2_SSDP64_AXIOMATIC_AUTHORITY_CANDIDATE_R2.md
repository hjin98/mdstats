---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_R2_AWAITING_INDEPENDENT_REVIEW_AND_STAKEHOLDER_RATIFICATION
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
repairs_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R1.md
parent_D1_candidate: workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE_R2.md
supersedes_proposed_candidate_only: workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE.md
would_compose_with:
  - docs/methods/mlff_numerical_algorithmic_method.md
  - docs/methods/mlff_target_training_order_numerical_algorithmic_method.md
---

# Proposed MLFF D2 formal numerical authority kernel — R2

## 1. Authority, exact sources, and numerical interpretation

This file is the repaired Protocol-6.4 D2 formalization overlay for accepted MLFF numerical authority at repository `hjin98/mdstats`, accepted basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. It remains proposed until fresh independent R2 review and stakeholder ratification of the exact D1/D2 pair.

The immutable accepted D2 sources are:

- `D2.SRC.GENERAL` = `hjin98/mdstats@cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824:docs/methods/mlff_numerical_algorithmic_method.md`;
- `D2.SRC.ORDER` = `hjin98/mdstats@cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824:docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

The scoped target-order source owns `TargetCoverageReference -> FEAS1/NEIGHBOR1 -> MVIDX -> MVSEL2 -> REPAIR2 -> MVQUAL`; the general source owns unaffected source/statistical/P1/P2/P3, `pi_eval`, optimizer/evaluation/reducer, P5/replay/CV/production, and role-predicate semantics.

Unless a narrower definition says otherwise:

- scientific scalar decision arithmetic is IEEE-754 binary64;
- counts/indices are exact integers of sufficient range;
- canonical order is the accepted deterministic identity order for the governed object;
- tolerances are fixed numerical-method coordinates unless explicitly classified configurable;
- undefined empty-set, zero-denominator, non-finite, stale, or non-identifiable cases fail closed rather than selecting a fallback;
- an optimized execution path is equivalent only when it reproduces the reference output/decision relation owned below.

## 2. Source numerical conventions and neutral statistical units

### D2.DEF.001 — Canonical source numerical convention

Occurrence, geometry, label-payload, and labeled-configuration identities are distinct. ASE row-vector cell/strain reconstruction, proper polar decomposition, stress normalization/sign/Voigt/shear rules, finite/nonsingular eligibility, and identity quantization are exact specialized imports from `D2.SRC.GENERAL`, Sections 2.1-2.4. A different transpose, sign, shear factor, unit conversion, implicit reference cell, or quantization rule is numerically non-equivalent when it changes a governed identity or observable.

### D2.DEF.002 — Finite-sequence autocorrelation estimator

For finite scalar sequence `(x_0,...,x_{N-1})`, let `xbar` be its arithmetic mean. For lag `k`, the accepted unbiased autocovariance is

$$
\widehat\gamma(k)=\frac{1}{N-k}\sum_{t=0}^{N-k-1}(x_t-\bar x)(x_{t+k}-\bar x),
$$

computed by the accepted fast-Fourier-transform realization without changing this estimator. For positive finite `gamma_hat(0)`,

$$
\widehat\rho(k)=\frac{\widehat\gamma(k)}{\widehat\gamma(0)}.
$$

Geyer's initial-positive-sequence rule accepts adjacent lag pairs while

$$
\widehat\rho(2m-1)+\widehat\rho(2m)>0.
$$

An unpaired final positive lag may be retained. The resulting integrated time is

$$
\widehat\tau_{\mathrm{int}}=\max\left(\frac12,\frac12+\sum_{k\in K_+}\widehat\rho(k)\right),
$$

where `K_+` is the accepted retained-lag set. No autocorrelation is computed across a source gap, continuation reset, or excluded interval. Constant or insufficient sequences use the explicit shared-sampling typed outcome from `D2.SRC.GENERAL` Section 3.1; they are not assigned a fabricated long correlation time.

### D2.DEF.003 — Complete-frame correlation block scale

For each configured observable and contiguous run compute D2.DEF.002, then

$$
\tau_{\max}=\max_{j,r}\widehat\tau_{j,r},
$$

$$
L_{\mathrm{corr}}=\max\left(1,\left\lceil m\tau_{\max}\right\rceil\right),
$$

$$
L=\max(L_{\min},L_{\mathrm{corr}})
$$

unless an explicitly accepted override is active. A short override is recorded as an adequacy limitation, not as decorrelation evidence. The balanced all-frame construction imported from `D2.SRC.GENERAL` Section 3.2 preserves source order and every eligible frame; no remainder/tail is silently dropped.

### D2.DEF.004 — Protected-event merge and relation closure

Protected event windows are constructed at full temporal resolution before ordinary thinning. Any candidate blocks intersecting one protected event window are merged before role allocation. Correlation-unit, exact-geometry, protected-event, condition-scoped replica, and condition-scoped structural-realization edges are then projected to the requested frame universe and transitively closed. P2/P5 consume that closure rather than reconstructing a reduced taxonomy.

## 3. Exact target-size population, split, evaluation order, and policy domain

### D2.DEF.005 — Canonical finite population

For governed population of `n` frames, write

$$
P=(u_0,u_1,\ldots,u_{n-1})
$$

for its canonical ordered tuple. Set membership and tuple order are distinct.

### D2.DEF.006 — Protected-component order for exact M3 allocation

Project D1 protected relation onto exact `U_size` and form connected components. Order components exactly by:

1. group by component cardinality;
2. process larger cardinalities before smaller;
3. within one cardinality, bucket by the lexicographically minimum represented `condition_id`;
4. sort component-member tuples canonically inside each condition bucket;
5. round-robin the nonempty buckets in sorted condition-ID order.

This order is numerical authority because multiple exact reserve subsets may exist.

### D2.DEF.007 — Exact component-preserving M3 subset

Let D2.DEF.006 produce components with positive integer weights `w_1,...,w_C`. For configured reserve cardinality `m_3`,

$$
R_0=\{0\},
$$

$$
R_j=R_{j-1}\cup\{r+w_j:r\in R_{j-1},\ r+w_j\le m_3\}.
$$

Iterate components in D2.DEF.006 order and previous reachable totals in descending order; record only the first predecessor creating each newly reachable total; stop when `m_3` first becomes reachable; reconstruct that predecessor chain. If unreachable, the split is infeasible. `M3` is the selected component union and `P_train` its canonical-order complement. The predecessor/tie rule is part of exact membership identity.

### D2.DEF.008 — Condition-balanced pi_eval

For exact reserve `M3`, group frame UIDs by `condition_id`. Inside each condition bucket sort by descending priority-vector coordinates, equivalently ascending negated coordinates, and then immutable frame UID. Repeatedly visit condition buckets in sorted condition-ID order and take one frame from each nonempty bucket until all frames are exhausted. With no priority evidence, empty vectors tie and UID determines within-condition order. The resulting permutation is `pi_eval`.

Evaluation rung of configured cardinality `m_i` is

$$
M_i=\mathrm{set}(\mathrm{prefix}(\pi_{\mathrm{eval}},m_i)).
$$

### D2.DEF.009 — Current P2 structural policy domain

A valid current automatic target-size policy satisfies all of:

- candidate-size tuple `N_cfg` contains at least three strictly increasing positive powers of two;
- evaluation-size tuple `M_cfg` contains exactly three strictly increasing positive powers of two;
- fidelity tuple `H_cfg` contains exactly three strictly increasing positive epochs;
- optimizer-seed tuple `S_seed` is ordered, unique, and contains nonnegative integers.

Exact numeric defaults remain specification/configuration bindings; these structural restrictions are fixed numerical-method constraints.

### D2.DEF.010 — Exact prefix function

For ordered tuple `pi=(v_1,...,v_n)` and `0<=N<=n`,

$$
\mathrm{prefix}(\pi,N)=(v_1,\ldots,v_N).
$$

Membership consumers use the corresponding set. A stored cardinality without parent-order identity is insufficient.

### D2.DEF.011 — Automatic-screen admission

Let `Q_cfg` be configured sizes whose exact prefixes pass MVQUAL. Automatic numerical screening is defined only when

$$
|Q_{\mathrm{cfg}}|\ge3.
$$

Fewer qualified configured candidates produce `INSUFFICIENT_AUTOMATIC_COMPARISON`; no ladder alteration, rescue size, or membership repair is implied.

## 4. TargetCoverageReference and exact required-family catalog

### D2.DEF.012 — Required-family catalog and applicability

The exact current family catalog is:

**Universal structural families**

```text
pair_distance
radial_environment
coordination
connectivity
chemical_environment
local_density
angular_environment
orientational_order
```

`pair_distance`, `coordination`, and `local_density` are extent-bearing; the others use hard mass coverage only.

**Profile-selection families**

For each active accepted profile-selection provider, every valid nonconstant scalar selection feature is one required one-dimensional extent-bearing family over provider-valid frames. Every represented provider environment-class label creates one required profile-environment hard obligation. If no accepted active profile provider exists, this family class is absent.

**Raw pair-geometry families**

For each applicable accepted pair rule:

- `bond_length_distribution`: minimum pair distance, mean nearest-neighbor distance, maximum nearest-neighbor distance;
- `coordination_distribution`: coordination mean, coordination maximum.

Both are required and extent-bearing.

**Target-development response families**

- `force_distribution`: force-component RMS, mean force norm, maximum force norm, and canonical available force-norm quantile channels;
- one scalar family for each defined nonconstant accepted channel among energy/atom, instantaneous temperature, hydrostatic strain, deviatoric strain norm, pressure, and stress deviatoric norm.

These are required and extent-bearing where defined by the accepted source.

**Foundation-residual families**

Only when the target-size protocol itself uses an authenticated frozen foundation model:

- one required extent-bearing global family containing absolute energy error/atom, force-component RMSE, mean force-vector error, maximum force-vector error;
- one required extent-bearing family per represented atomic species containing component RMSE, mean vector error, maximum vector error.

Foundation checkpoint/head/provider identity participates in selector-evidence identity. Scratch protocols do not acquire foundation families merely because the provider exists elsewhere.

### D2.DEF.013 — Family witness weights: one normalization only

For required family `m`, let `W_m` be its nonempty ordered witness set, `g(w)` the current P1 correlation-unit identity, `G_m={g(w):w in W_m}`, and `n_{m,g}` the witness count in unit `g`. Define preweight

$$
\widetilde\omega_m(w)=\frac{1}{|G_m|\,n_{m,g(w)}}.
$$

Compute the binary64 canonical-order sum

$$
s_m=\sum_{w\in W_m}^{\mathrm{canonical}}\widetilde\omega_m(w)
$$

and store

$$
\omega_m(w)=\frac{\widetilde\omega_m(w)}{s_m}.
$$

This is the single and only normalization of the family weight vector. `|G_m|>0`, every `n_{m,g}>0`, and `s_m` finite/positive are required.

### D2.DEF.014 — Stable weighted quantile over stored weights

For finite values `v_i` paired with the canonical stored weights from D2.DEF.013, stable-sort indices by `(v_i, original_index)`. For `q in [0,1]`, define `Q(q)` as the first sorted value whose cumulative **stored** weight is at least `q`.

The stored weights are not normalized again inside this definition. Their canonical binary64 sum may differ slightly from one after D2.DEF.013, and that finite-precision result is part of the accepted numerical method.

### D2.DEF.015 — Robust feature scale

For family coordinate `j`,

$$
a_j=Q_j(0.75)-Q_j(0.25),
$$

$$
b_j=Q_j(0.99)-Q_j(0.01).
$$

With fixed `delta_s=1e-12`,

$$
s_j=
\begin{cases}
a_j,&a_j>\delta_s,\\
b_j,&a_j\le\delta_s\text{ and }b_j>\delta_s,\\
\max(\sigma_{\mathrm{pop},j},1),&\text{otherwise},
\end{cases}
$$

followed by `s_j=max(s_j,delta_s)`. Non-finite inputs fail preparation.

### D2.DEF.016 — Family metric

For a `d_m`-coordinate family, `d_m>=1`,

$$
d_m(a,b)=\sqrt{\frac1{d_m}\sum_{j=1}^{d_m}\left(\frac{x_{a,j}-x_{b,j}}{s_j}\right)^2}.
$$

Only provider-applicable rows participate. A family requires at least two reference elements. Constant optional scalar families are omitted instead of creating zero-information dimensions.

### D2.DEF.017 — Leave-one-out local radius

Let fixed `beta=1/128`. For witness `w`, remove its self mass, require `1-omega_m(w)>0`, renormalize every other witness weight by `1-omega_m(w)`, stable-sort other witnesses by `(d_m(w,v), canonical_witness_order)`, and define `r_m(w)` as the smallest distance at which cumulative renormalized mass is at least

$$
\beta-10^{-15}.
$$

Failure to reach the requested mass is family infeasibility.

### D2.DEF.018 — Exact adjacency

$$
A_m(w,c)=1
\Longleftrightarrow
d_m(w,c)\le r_m(w)+10^{-12}\max(1,r_m(w)).
$$

Every witness must have at least one exact candidate support edge. Approximate nearest-neighbor substitution is not equivalent authority.

### D2.DEF.019 — Multiplicity and covered mass

For selected set `S subseteq P_train`,

$$
n_m(w;S)=\sum_{c\in S}A_m(w,c),
$$

$$
C_m(S)=\sum_{w\in W_m}\omega_m(w)\mathbf 1[n_m(w;S)>0].
$$

### D2.DEF.020 — Independent qualification coverage predicate

A required family passes membership qualification iff

$$
C_m(S)+10^{-12}\ge0.95.
$$

This `1e-12` comparison belongs to direct coverage/MVQUAL qualification and is not the MVSEL2 Phase-A completion tolerance.

### D2.DEF.021 — Extent predicate

For extent coordinate `j`, define

$$
L_j=Q_j(0.01),\qquad U_j=Q_j(0.99).
$$

Let `V_j(S)` be applicable selected values. Empty `V_j(S)` fails. Otherwise extent passes iff

$$
\min V_j(S)\le L_j+10^{-12}
$$

and

$$
\max V_j(S)\ge U_j-10^{-12}.
$$

Each side also contributes one current hard obligation of minimum one.

## 5. Canonical hard obligations and FEAS1

### D2.DEF.022 — Source obligation

A source obligation is

$$
o=(L_o,A_o,k_o,s_o),
$$

where `L_o` is the D1 semantic locus, `A_o subseteq P_train` exact incidence, `k_o` a positive integer minimum, and `s_o` source/provenance namespace identity.

Automatic obligations are, where applicable: every represented P2 condition; recognized structural-event type; represented active profile environment class; extent lower side; extent upper side; and represented current P1 correlation interval/unit, each with minimum one. Explicit current hard-support obligations are projected through current P2 condition-attribute authority with declared positive minima.

### D2.DEF.023 — Obligation canonicalization

Two source obligations may group only when their accepted D1 semantic loci are equal. Exact incidence must then also be equal; otherwise fail closed. Incidence equality without locus equality never implies aliasing.

For locus class `C`,

$$
A_C=A_o\quad(o\in C),
$$

$$
k_C=\max_{o\in C}k_o.
$$

Assign one deterministic identity-bound canonical record per class; aliases/source minima remain provenance only. Source-ID reuse for different semantics fails. Different loci with identical incidence remain distinct.

### D2.DEF.024 — Obligation count and deficit

For canonical obligation `o`,

$$
q_o(S)=|S\cap A_o|,
$$

$$
d_o(S)=\max(0,k_o-q_o(S)),
$$

$$
D_{\mathrm{hard}}(S)=\sum_o d_o(S).
$$

The obligation is satisfied iff `q_o(S)>=k_o`.

### D2.DEF.025 — FEAS1 configured horizon

For nonempty configured candidate-size set `N_cfg`,

$$
N_{\max}=\max N_{\mathrm{cfg}}.
$$

FEAS1 verifies self-support/domain consistency, canonical-obligation support capacity, and conservative lower bounds for required support using exact `P_train` and the same neighborhood/obligation authority. A proven lower bound above `N_max` means configured-ladder infeasibility. FEAS1 never creates an unconfigured rescue size or relaxes a predicate.

Historical support-degree bins `(2,4,8,16,32)`, own-correlation-unit exclusion, and fragile-zero-mass tolerance `1e-12` remain diagnostics, not new membership rules.

### D2.AX.001 — Exact sparse representation axiom

NEIGHBOR1/MVIDX may use any exact sparse/file-backed representation, but witness-candidate adjacency, canonical obligation incidence, correlation-unit codes, family/obligation order, and identities must equal D2.DEF.018/D2.DEF.023. Storage dtype/layout is non-semantic only under exact representation.

## 6. MVSEL2 state and candidate primitives

### D2.DEF.026 — Selector state

At selected set `S` and available set `P_train\S`, authoritative selector state contains ordered selected prefix, every `n_m(w;S)` and `C_m(S)`, every `q_o(S)`, selected counts `b_g(S)` per current P1 correlation unit, and exact state sufficient to reconstruct representative utility. Lazy heaps, caches, native batches, worker order, and queue state are not scientific state.

### D2.DEF.027 — Hard gain

For available candidate `c`,

$$
O_c(S)=\{o:q_o(S)<k_o\text{ and }c\in A_o\},
$$

$$
H(c;S)=|O_c(S)|.
$$

A stronger `k_o` extends how long one locus remains unsatisfied; it does not multiply its hard-gain vote.

### D2.DEF.028 — New-coverage gains

$$
G_m(c;S)=\sum_{\substack{w\in W_m\\A_m(w,c)=1\\n_m(w;S)=0}}\omega_m(w),
$$

$$
G(c;S)=\sum_m G_m(c;S).
$$

### D2.DEF.029 — Representative gain

$$
R(c;S)=\sum_m\sum_{\substack{w\in W_m\\A_m(w,c)=1}}\frac{\omega_m(w)}{n_m(w;S)+1}.
$$

### D2.DEF.030 — Sparse diversity

For candidate `c`,

$$
W_m(c)=\{w\in W_m:A_m(w,c)=1\},
$$

$$
M(c)=\{m:|W_m(c)|>0\}.
$$

If `M(c)` is empty, `D(c;S)=0`; otherwise

$$
D(c;S)=\frac1{|M(c)|}\sum_{m\in M(c)}\left[\frac1{|W_m(c)|}\sum_{w\in W_m(c)}\frac1{n_m(w;S)+1}\right].
$$

This is the renderer-safe exact finite-sum form of the accepted nested arithmetic means.

### D2.DEF.031 — MVSEL2 Phase-A family-completion predicate

Let fixed selector contender tolerance

$$
\epsilon_{\mathrm{sel}}=10^{-14}.
$$

For required family `m`, selector Phase-A family completion is

$$
P_{\mathrm{sel},m}(S)\Longleftrightarrow C_m(S)\ge0.95-10^{-14}.
$$

Equivalently, family `m` keeps Phase A active exactly while

$$
C_m(S)<0.95-10^{-14}.
$$

This is intentionally distinct from D2.DEF.020.

### D2.DEF.032 — Phase-A predicate and winner

Phase A is active iff at least one canonical obligation is unsatisfied or at least one required family fails D2.DEF.031.

Among available candidates:

1. if any required obligation is unsatisfied, retain maximum integer `H(c;S)`;
2. find the first family in canonical order minimizing `C_m(S)/0.95` among families tied within `1e-14` at the minimum;
3. retain maximum bottleneck-family `G_m(c;S)` within `1e-14`;
4. retain maximum `G(c;S)` within `1e-14`;
5. retain minimum current selected count of candidate's own correlation unit;
6. retain maximum `R(c;S)` within `1e-14`;
7. retain maximum `D(c;S)` within `1e-14`;
8. choose minimum stable current frame UID.

The winner mutates authoritative state exactly once.

### D2.DEF.033 — Phase-B winner

After every obligation is satisfied and every required family passes D2.DEF.031, choose by:

1. maximum current `R(c;S)` within `1e-14`;
2. minimum selected count of candidate's correlation unit;
3. maximum `D(c;S)` within `1e-14`;
4. minimum stable UID.

Selection continues toward a complete permutation subject only to configured-shell REPAIR2.

### D2.DEF.034 — Full-forward reference oracle

At every rank recompute exact current D2.DEF.027-030 for every available candidate, apply D2.DEF.032 or D2.DEF.033, determine the unique winner, and only then mutate state. Every optimized selector must reproduce this rank sequence under identical authoritative state.

### D2.DEF.035 — Certified-lazy Phase-B equivalence

At required rebase compute exact `R_g(c)` for every available candidate and set

$$
B_g(c)=\mathrm{nextafter}(R_g(c),+\infty),
$$

where `nextafter` is the IEEE-754 next binary64 value toward positive infinity. Stale scores are upper bounds only. If refreshed `R` exceeds its earlier exact value by more than `5e-13`, fail the monotonicity invariant.

Refresh every stale candidate whose bound can enter the inclusive contender region. Certification terminates only when

$$
B_{\max}<R_{\mathrm{best}}-10^{-14}.
$$

At termination every candidate with

$$
R(c;S)\ge R_{\mathrm{best}}-10^{-14}
$$

has an exact current score before correlation-balance/diversity/UID tie dimensions are applied. If proof fails, rebuild or use D2.DEF.034.

## 7. Configured-shell REPAIR2

### D2.DEF.036 — Configured shell

For strictly increasing configured sizes `N_1<...<N_K`, set `N_0=0` and shell

$$
S_i=[N_{i-1},N_i).
$$

Only ranks in `S_i` are removable at shell `i`; all lower ranks are immutable.

### D2.DEF.037 — Removal eligibility and shortlist

For selected candidate `c`, unique covered mass is the total `omega_m(w)` over witnesses currently covered by `c` and no other selected candidate. `c` is removable iff unique covered mass `<=1e-14` and removing it increases no canonical obligation deficit.

Order removable candidates by:

1. representative loss ascending;
2. removed candidate correlation-unit selected count descending;
3. removed UID ascending.

Retain at most 64.

### D2.DEF.038 — Replacement frontier

For contemplated removal, evaluate replacements against immutable pre-swap state by:

1. maximum hard gain when obligations remain pending;
2. first canonical bottleneck family;
3. maximum bottleneck-family new coverage;
4. maximum total new coverage;
5. minimum hypothetical replacement correlation-unit count after removal;
6. maximum representative gain after removal;
7. maximum sparse diversity after removal;
8. minimum replacement UID.

All floating contender comparisons use `1e-14` unless a narrower fixed predicate above applies.

### D2.DEF.039 — Representative utility and global repair objective

For integer `k>=1`,

$$
H_k=\sum_{j=1}^{k}\frac1j,\qquad H_0=0,
$$

$$
U_{\mathrm{rep}}(S)=\sum_m\sum_{w\in W_m}\omega_m(w)H_{n_m(w;S)}.
$$

With correlation-unit selected counts `b_g(S)`, define ordered objective

$$
J(S)=\left(D_{\mathrm{hard}}(S),\min_m C_m(S),\sum_m C_m(S),U_{\mathrm{rep}}(S),-\sum_g b_g(S)^2\right).
$$

Comparison minimizes component 1, then maximizes components 2-4 with `1e-14` floating contender tolerance, then maximizes exact integer component 5. A swap is admissible only if it strictly improves `J` and, for every required family,

$$
C_m(S_{\mathrm{after}})+10^{-14}\ge C_m(S_{\mathrm{before}}).
$$

Objective-equivalent admissible proposals use increasing `(representative_loss, removed_rank, removed_UID, replacement_UID)`.

### D2.DEF.040 — Repair limits, rank inheritance, and terminal-shell rule

Per configured shell REPAIR2 permits at most 2 passes and 32 accepted swaps; D2.DEF.037 limits the removal shortlist to 64.

An accepted replacement inherits the removed rank. If the replacement already appears at a future rank, move the removed candidate to that future rank. The master permutation is preserved and every earlier configured prefix remains immutable.

After the final configured shell, continue the same exact optimized MVSEL2 method until every `P_train` frame is ordered. There is no extra/unconfigured repair shell and no UID-only, condition-round-robin, scalar-only, or alternate-selector suffix.

### D2.AX.002 — Post-repair reconstruction

After any accepted swap, all prefix-derived lazy/frontier/marginal/cache/checkpoint/journal state from the pre-swap prefix is stale. Reconstruct exact forward state from authenticated primitive family/obligation/correlation evidence plus exact repaired prefix; Phase-B continuation performs an exact all-candidate rebase. A zero-swap shell may retain authentic state whose exact prefix identity is unchanged.

## 8. Independent MVQUAL

### D2.DEF.041 — Independent configured-prefix qualification

For configured `N`, let `T_N` be exact repaired prefix. Independently recompute from immutable TargetCoverageReference and canonical obligations:

- direct `C_m(T_N)` under D2.DEF.016-019 and pass/fail under D2.DEF.020;
- extent predicates under D2.DEF.021;
- every `q_o(T_N)` under D2.DEF.024;
- training-label usability.

MVIDX may provide an exact secondary cross-check but selector/repair counters are not the sole oracle. Direct family mass and MVIDX family mass must agree with `rtol=0`, `atol=5e-12`; disagreement is an invariant error.

Prefix qualifies iff every required predicate passes. Under fixed nested prefixes/evidence, configured qualification must have form `FAIL* -> PASS*`; later `PASS -> FAIL` fails closed. MVQUAL does not rank qualified sizes.

## 9. Atomic-reference fitting and identifiability

### D2.DEF.042 — Composition matrix

For exact authorized fit membership `D` and atomic-species basis `(z_1,...,z_p)`, define count matrix `C in N_0^{|D| x p}` by atom counts and total-energy target vector `y in R^{|D|}`.

### D2.DEF.043 — Foundation-residual least-squares family

For exact selected foundation identity `Phi`, let `y_fnd` be its predicted total energy on `D` and `e_fnd(Phi)` its head-local elemental-reference vector. Let `r=y-y_fnd`. With accepted regularization/anchor tuple `(lambda,delta e_prior)`, solve

$$
\widehat{\delta\mathbf e}=\arg\min_{\delta\mathbf e}\left(\|C\delta\mathbf e-r\|_2^2+\lambda\|\delta\mathbf e-\delta\mathbf e_{\mathrm{prior}}\|_2^2\right).
$$

Target head reference is

$$
\mathbf e_{\mathrm{target}}(\Phi)=\mathbf e_{\mathrm{fnd}}(\Phi)+\widehat{\delta\mathbf e}.
$$

Element order is atomic-number order. CV uses exact fold gradient membership `G_i`; final production uses exact complete `T_selected`. Monitor and held-out target labels are excluded.

### D2.DEF.044 — Free null space and composition transfer

Let `N_free` be directions left unconstrained by authorized composition equations and explicit accepted anchors; with no accepted anchor, `N_free=ker(C)` under accepted numerical-rank rule. Required composition vector `c` is transfer-feasible iff

$$
\mathbf c^T\mathbf v=0\quad\text{for every }\mathbf v\in N_{\mathrm{free}}.
$$

Tolerance may classify numerical rank but cannot create absent information. Rank, singular values, residual diagnostics, anchor identity, and required-composition tests are interpretation evidence.

## 10. Foundation-P5 robust objective

### D2.DEF.045 — Scalar Huber function

For `delta>0`,

$$
h_\delta(x)=\begin{cases}\frac12x^2,&|x|\le\delta,\\\delta\left(|x|-\frac12\delta\right),&|x|>\delta.\end{cases}
$$

### D2.DEF.046 — Dimensional robust thresholds

The fixed current numeric Huber parameter `0.01` is applied independently in canonical property units:

$$
\delta_E=0.01\ \mathrm{eV/atom},
$$

$$
\delta_{F,0}=0.01\ \mathrm{eV/angstrom},
$$

$$
\delta_S=0.01\ \mathrm{eV/angstrom^3}.
$$

For masked reference-force norm `f` in `eV/angstrom`,

$$
\delta_F(f)=\delta_{F,0}\times\begin{cases}1.0,&f<100,\\0.7,&100\le f<200,\\0.4,&200\le f<300,\\0.1,&f\ge300.\end{cases}
$$

### D2.DEF.047 — Property losses

For configuration `i`, `n_i>0`, masks `m_i^E,m_i^F,m_i^S in {0,1}`, total-energy residual `Delta E_i`, force residuals, and full Cartesian stress residual matrix:

- `L_E` is the arithmetic mean over configurations of `h_deltaE(m_i^E Delta E_i/n_i)`;
- `L_F` is the arithmetic mean over all stored Cartesian force components after applying the binary force mask, using per-atom `delta_F` from the masked reference-force norm;
- `L_S` is the arithmetic mean over all nine stored Cartesian stress entries per admitted configuration of `h_deltaS(m_i^S Delta sigma_iab)`.

The nine-entry stress reduction counts symmetric off-diagonal entries twice. A six-component Voigt mean is not equivalent.

### D2.DEF.048 — Foundation-P5 objective

$$
L_{P5}=L_E+10L_F+L_S.
$$

No independent per-configuration scalar weight and no target/replay training-head scalar occur. A transport field required by a dependency interface must be neutral if present. A phase-dependent loss mutation is a different numerical method unless separately accepted and identity-bound.

## 11. P3 optimizer normalization, estimator, and exact reducer

### D2.DEF.049 — P3 updates per epoch

For target size `N>0` and target batch size `B>0`, with final partial target batch retained,

$$
U_N=\left\lceil\frac{N}{B}\right\rceil.
$$

A runtime realizing `floor(N/B)` updates is a different P3 experiment.

### D2.DEF.050 — First-order optimizer-progress normalization

For reference `(N_ref,LR_ref,beta_ref)` with `U_ref=ceil(N_ref/B)`, define

$$
s_N=\frac{U_{\mathrm{ref}}}{U_N},
$$

$$
LR_N=LR_{\mathrm{ref}}s_N,
$$

$$
beta_N=beta_{\mathrm{ref}}^{s_N}.
$$

Then `LR_N U_N = LR_ref U_ref` and `(beta_N)^{U_N}=beta_ref^{U_ref}` algebraically. This is first-order normalization, not exact optimizer-trajectory equivalence. Values are fixed from full candidate geometry and do not rescale after survivor reduction.

### D2.DEF.051 — P3 target-force estimator

For `K>0` admitted Cartesian force components,

$$
E_{N,s}=1000\sqrt{\frac1K\sum_{k=1}^{K}(\widehat F_k-F_k)^2}
$$

in `meV/angstrom`. Non-finite prediction or metric is typed numerical failure, not `+infinity` substitution.

### D2.DEF.052 — Complete-seed candidate score

For configured ordered seed set `S_seed`, score exists only if every required seed has valid finite metric:

$$
\overline E_N=\frac1{|S_{\mathrm{seed}}|}\sum_{s\in S_{\mathrm{seed}}}E_{N,s}.
$$

No successful-subset mean is defined.

### D2.DEF.053 — Practical-equivalence ranking

For active successful candidate set `A`, let

$$
E_{\min}=\min_{N\in A}\overline E_N,
$$

$$
E_{\mathrm{eq}}=\{N\in A:\overline E_N\le E_{\min}+\epsilon\}.
$$

Choose smallest `N` in `E_eq`, remove it from the ranking pool, and repeat until `A` is ordered. Only the already-accepted tiny fixed floating comparison guard may supplement scientific `epsilon`; it cannot be widened because a backend fails.

### D2.DEF.054 — Structural funnel and success sufficiency

Let `q>=3` be number of qualified candidates admitted by D2.DEF.011. The structural survivor counts are

$$
q\rightarrow\min(q,4)\rightarrow2\rightarrow1.
$$

At boundary 1, successful candidates must number at least `min(|A_1|,4)`; rank them by D2.DEF.053 and retain first `min(q,4)`. At boundary 2 and terminal boundary, at least two successful candidates are required before the corresponding comparison; otherwise return `INSUFFICIENT_COMPARISON`. Boundary 2 retains first two by D2.DEF.053. Exact fidelity epochs and evaluation sizes are the three configured positions of D2.DEF.009, not encoded by the funnel name.

### D2.DEF.055 — Configured-ceiling terminal rule

At terminal comparison, if configured maximum `N_max` is a successful finalist and

$$
\overline E_{N_{\max}}+\epsilon<\overline E_N
$$

for every other successful terminal finalist, recommend `N_max` and record explicit nonconvergence-at-configured-ceiling evidence. Otherwise recommend the first D2.DEF.053-ranked terminal finalist. The reducer never extrapolates a learning curve or creates an unconfigured rescue size.

### D2.AX.003 — Continuous fidelity trajectory and authenticated restart

Each active `(N,seed)` is one continuous training trajectory through configured fidelity boundaries. Model, optimizer, EMA, learning-rate state, and accepted Python/NumPy/Torch RNG lineage continue from authenticated predecessor state. Unaccepted scratch is not continuation authority. Restart cannot change membership, normalization, common preparation, seed, or boundary identity.

## 12. Replay label modes and P5 exposure

### D2.DEF.056 — Replay geometry and label-mode concretization

Let `D_r^geom` be authenticated prepared replay geometry/source membership and split. Replay label mode is exactly the D1 family

```text
TRUE_REFERENCE
FOUNDATION_PSEUDO
```

with `TRUE_REFERENCE` the canonical default when true labels are available and `FOUNDATION_PSEUDO` requiring explicit opt-in plus exact frozen foundation identity `Phi`.

Define labeled replay corpus

$$
D_r(\ell)=\{(x,y_{\ell}(x)):x\in D_r^{\mathrm{geom}}\}.
$$

For `TRUE_REFERENCE`, `y_l` is the canonical true-reference/DFT label. For `FOUNDATION_PSEUDO`, `y_l` is generated by exact frozen `Phi` under the accepted prediction policy. Changing `ell` with the same authenticated prepared source/split must leave `D_r^geom` unchanged.

Pseudo-label mode does not authorize pseudo replay as retention evidence: a distinct authenticated true-reference replay monitor `M_r^true` remains mandatory.

### D2.DEF.057 — Replay lineage identity

Numerical replay lineage binds `D_r^geom`, label mode, true-monitor identity, foundation/head identity where applicable, replay/pretraining-head E0 identity, prediction policy, and realized exposure. A changed component invalidates dependent P5 evidence rather than being reinterpreted in place.

### D2.DEF.058 — Combined corpus order

For current two-head replay, with labeled replay corpus `D_r=D_r(ell)` and target corpus `D_t`, pre-shuffle tuple is

$$
D_{\mathrm{train}}=D_r\Vert D_t.
$$

A fixed seed shuffles integer indices of this ordered tuple. Reversing corpus blocks changes index-to-example mapping and is non-equivalent unless separately qualified. There is no target/replay balancing sampler or intentional target duplication. For naive fine tuning, `|D_r|=0`.

### D2.DEF.059 — Current single-process update geometry

With `N_r=|D_r|`, `N_t=|D_t|`, batch size `B>0`, current foundation-P5 combined loader uses `drop_last=true` and

$$
U=\left\lfloor\frac{N_r+N_t}{B}\right\rfloor.
$$

Exactly `UB` examples of each epoch's seeded shuffled permutation are consumed. Distributed execution is not presumed equivalent without evidence for global property means, exposure, and optimizer trajectory under the accepted envelope.

## 13. Common target monitor

### D2.DEF.060 — Monitor parent and strata

Let usable protected `OUTER_MONITOR` parent be `P_mon`. Required cardinality is fixed `n_mon=256`; `|P_mon|<256` is infeasible. Each parent frame belongs to stratum `<condition_id>:<run_id>` and is ordered within stratum by `(source_frame_index, frame_uid)`.

### D2.DEF.061 — Deterministic quota order

With fixed seed `q=161803`, each nonempty stratum key `s` receives lowercase SHA-256 hex marker of UTF-8 bytes

```text
<q>\0quota\0<s>
```

with `<q>` base-10. Sort strata by `(marker,s)`. Initialize quotas zero and repeatedly sweep this order, incrementing a stratum whose quota is below capacity, until exactly 256 slots are allocated.

### D2.DEF.062 — Deterministic systematic positions

For stratum capacity `n`, quota `k`, `1<=k<=n`, namespace `target:<s>`, hash UTF-8 `<q>\0<namespace>`, take first eight digest bytes as unsigned big-endian integer `I`, and define

$$
u=\frac{I+0.5}{2^{64}},
$$

$$
p_j=\min\left(n-1,\left\lfloor\frac{(j+u)n}{k}\right\rfloor\right),\quad j=0,\ldots,k-1.
$$

Positions must be distinct; duplicates are construction failure. Exact membership plus parent/policy/seed/strata identity defines `M_mon`.

## 14. Post-selection folds

### D2.DEF.063 — Component fold order

For exact frozen `T_N`, let sorted protected-component identities be `C_comp`, fold count `K>=2`, partition seed `s_cv`, algorithm identity `a`, and selected-membership digest `d_T`. If `|C_comp|<K`, CV is infeasible.

For component identity `c`, set `salt=<a>|<d_T>` and marker SHA-256 hex of UTF-8 `<salt>|<s_cv>|<c>`. Sort by `(marker,c)`; ordered position `j` is held out in fold `j mod K`.

### D2.DEF.064 — Purge rule

For fold `i`, let `O_i` be held-out components and `R_i` lexicographically sorted remaining components. With configured nonnegative `p_cfg`,

$$
p_i=\min\left(p_{\mathrm{cfg}},\max(0,|R_i|-2)\right).
$$

If `p_i=0`, purge is empty. If `p_i=1`, choose index `floor(|R_i|/2)`. If `p_i>1`, set `h=(|R_i|-1)/(p_i-1)`, propose nearest-integer ties-to-even indices `round_even(jh)`, deduplicate, append lowest unselected integer indices until `p_i` exist, then sort. Gradient set is complement of held-out plus purge. `M_mon` is external.

## 15. Checkpoint predicates, CV, and production

### D2.DEF.065 — Shared checkpoint constraint

For checkpoint `c`, `S(c)` is conjunction of shared mandatory constraints: finite required metrics; replay degradation within the accepted replay budget using authenticated **true-reference** replay-monitor evidence when replay is active; and required physical/integrity predicates. Pseudo replay training labels cannot satisfy the true-reference retention conjunct.

### D2.DEF.066 — Target-monitor RMSE

`r_mon(c)` is target force-component RMSE of checkpoint `c` on exact `M_mon`, in `eV/angstrom`, using the accepted force estimator. Held-out metric `r_out` is computed on exact fold `O_i` under configured outer metric.

### D2.DEF.067 — Role-effective checkpoint admissibility

For role `rho` with resolved target-monitor ceiling `tau_rho`,

$$
A_\rho(c)=S(c)\wedge r_{\mathrm{mon}}(c)\le\tau_\rho.
$$

Foundation CV uses `tau_CV`; fresh production uses `tau_prod`. Boundaries are inclusive in binary64 against binary64 nearest the resolved decimal value: `r=tau` passes and next representable binary64 above fails.

### D2.DEF.068 — CV outer predicate

For configured outer metric and threshold `theta_CV`, frozen fold representative passes iff exact held-out metric is finite and `<=theta_CV`. Alternative outer metrics retain their own units/threshold and never supply `tau_CV`.

### D2.DEF.069 — All-required-position CV acceptance

Let `P_req` be finite required `(fold,seed)` positions. CV accepts iff for every `p in P_req`: training completed under frozen method/horizon; admissible checkpoint set under D2.DEF.067 is nonempty; one representative is frozen by accepted ranking rule; and that representative satisfies D2.DEF.068. No averaging, majority, best-seed, or dispersion rescue predicate exists.

### D2.AX.004 — Role currentness and selective invalidation

Changing `tau_CV` or `theta_CV` stales dependent CV acceptance and production authorization derived from that acceptance while leaving `tau_prod` and shared method unchanged. Changing `tau_prod` stales production role evidence only. Changing shared `S` can stale both roles. Re-thresholding stored classifications is not current evidence; role evidence is evaluated under resolved current policy identity.

### D2.AX.005 — Fresh production

Fresh production starts a new model/optimizer lineage on exact complete `T_selected`, fits target training-dependent state there only, uses same `M_mon` and shared checkpoint mechanics as CV, and applies production predicate with `tau_prod`. P3 `M3` has no production checkpoint role. Where replay is active, D2.DEF.056-059 and true-reference retention in D2.DEF.065 remain binding.

## 16. Restart, precision, equivalence, and fail-closed semantics

### D2.DEF.070 — Authenticated continuation state

Continuation is admissible only when it binds every numerical/scientific identity needed to prove exact run boundary: population/membership, method/policy parameters, foundation/head, objective/exposure, selector/reference identities where applicable, optimizer/EMA/RNG state, and exact accepted predecessor boundary. Uncommitted scratch is not continuation authority.

### D2.DEF.071 — Numerical equivalence relation

For optimized implementation `A`, reference owner `R`, and declared authoritative output set `O`,

$$
A\equiv_O R
$$

iff throughout declared validity domain they produce every output/decision in `O` under exact owner-required equality/tolerance. `O` may require exact selector rank/repair trace identity or a separately governed metric tolerance. Performance alone never establishes equivalence.

### D2.AX.006 — Execution noninterference

Worker count, queue completion order, block/chunk size, mmap layout, cache residence, native backend, device batching, and restart route are execution-only exactly when they preserve all D2 outputs under D2.DEF.071. Otherwise they are method-affecting and require D2 review.

### D2.DEF.072 — Formal failure set

Fail closed rather than choose a semantic fallback for: non-finite required fitted statistics; invalid/empty required family mass; unreachable exact `M3`; incomplete/malformed policy domain; unsupported family/provider state; zero leave-one-out denominator; unreachable local mass; unsupported witness adjacency; impossible hard obligation; configured-ladder infeasibility; stale lazy certification; repair invariant failure; direct/MVIDX disagreement beyond fixed tolerance; non-identifiable E0 transfer; pseudo replay without exact `Phi` or true-reference monitor; invalid replay lineage; impossible 256-frame monitor; insufficient fold components; missing required fold/seed; no admissible checkpoint; non-finite P3 outcome; insufficient reducer comparison; stale/mismatched continuation; or materially different objective/exposure/method.

Tolerance widening, support relaxation, role substitution, pseudo-label fallback, or rescue-size invention are not error handlers.

## 17. D2 parameter-binding ledger

| Coordinate | Binding class | Current value/domain |
| --- | --- | --- |
| family hard coverage | fixed method coordinate | `0.95` |
| extent quantiles | fixed method coordinate | `0.01, 0.99` |
| family weight normalization count | fixed method coordinate | exactly once |
| robust-scale floor/branch threshold | fixed numerical coordinate | `1e-12` |
| local-radius mass `beta` | fixed numerical coordinate | `1/128` |
| local-radius cumulative guard | fixed numerical coordinate | `1e-15` |
| adjacency tolerance | fixed numerical coordinate | `1e-12*max(1,r)` |
| MVQUAL/coverage comparison tolerance | fixed numerical coordinate | `1e-12` |
| MVSEL2 selector contender/completion tolerance | fixed numerical coordinate | `1e-14` |
| lazy monotonicity guard | fixed numerical coordinate | `5e-13` |
| REPAIR2 unique-mass/floating tolerance | fixed numerical coordinate | `1e-14` |
| REPAIR2 limits | fixed numerical coordinate | `2 passes`, `32 swaps`, shortlist `64` |
| direct-vs-MVIDX mass equality | fixed numerical coordinate | `rtol=0`, `atol=5e-12` |
| candidate/evaluation/fidelity/seed values | configurable family | structural domain D2.DEF.009 |
| practical equivalence `epsilon` | configurable family | finite positive response-unit value |
| foundation Huber dimensional thresholds | fixed method coordinates | `0.01 eV/atom`, `0.01 eV/angstrom`, `0.01 eV/angstrom^3` |
| force Huber factors/boundaries | fixed method coordinates | `1.0/0.7/0.4/0.1` at `100/200/300 eV/angstrom` |
| foundation P5 coefficients | fixed method coordinate | `1:10:1` |
| replay label mode | configurable method family with canonical default | true-reference default; pseudo explicit opt-in |
| P5 corpus order | fixed current stochastic exposure coordinate | replay then target |
| P5 partial-batch policy | fixed current stochastic exposure coordinate | `drop_last=true` |
| common monitor cardinality | fixed method coordinate | `256` |
| common monitor seed | fixed numerical coordinate | `161803` |
| CV fold count | configurable with generated default | integer `K>=2`, default `3` |
| `tau_CV`, `theta_CV`, `tau_prod` | configurable with generated defaults | D1-defined positive families, defaults `45/45/30 meV/angstrom` for default force metric |

## 18. Verification and falsification oracles

R2 qualification/review must include at least:

1. **one-normalization quantile adversary:** two represented correlation units with 37 and 2 witnesses; after D2.DEF.013 the stored vector has binary64 sum `1.0000000000000002`; stable cumulative mass after witness index 36 is `0.5000000000000006`; `Q(0.5)` must select index 36. Any second normalization that selects index 37 is nonconformant;
2. selector-completion fixture inside interval between `0.95-1e-12` and `0.95-1e-14`, proving D2.DEF.031 and D2.DEF.020 remain distinct;
3. exact five-step component-order plus first-predecessor `M3` membership oracle;
4. condition-balanced `pi_eval` oracle with and without priority evidence;
5. structural-policy rejection for non-power-of-two size, wrong evaluation-count, non-increasing horizon, duplicate/negative seed;
6. fewer-than-three-qualified automatic-screen rejection;
7. exact `q -> min(q,4) -> 2 -> 1` funnel, success-sufficiency failures, and configured-ceiling material-superiority cases;
8. autocorrelation/truncation/block/event fixtures from accepted sampling semantics;
9. required-family applicability fixtures for universal/profile/pair/response/foundation modes;
10. direct dense/reference versus exact adjacency at metric boundaries;
11. full-forward versus optimized/lazy MVSEL2 rank equality at every rank;
12. Phase-A first-canonical bottleneck and hard-obligation priority under `1e-14` ties;
13. REPAIR2 replacement-frontier/scalar-optimized proposal and swap-trace equality, 2-pass/32-swap/64-shortlist limits, rank inheritance, future displacement, lower-prefix immutability, and no-extra-shell continuation;
14. direct TargetCoverage versus MVIDX mass equality and independent MVQUAL monotonicity;
15. selected-head E0 null-space transfer counterexamples;
16. robust P5 dimensional-threshold, nine-entry stress, masks, and no-config/head-scalar oracles;
17. true-reference/default replay and pseudo-label opt-in fixtures proving identical replay geometry membership, frozen-`Phi` pseudo targets, and separate true-reference replay retention;
18. replay-first/target-second seeded exposure and `drop_last=true` geometry;
19. deterministic monitor and fold/purge reconstruction;
20. inclusive role-threshold boundaries and selective invalidation;
21. worker/backend/chunk/cache/restart invariance of every governed scientific output.

## 19. D2 -> D3 handoff

D3 must preserve this formal method while owning persistence, concurrency, resource admission, software decomposition, dependency adaptation, build topology, and durable restart representation. D3 may consolidate or simplify implementations but may not create a second numerical owner, weaken fail-closed predicates, encode configurable defaults as universal constants, or reintroduce target/replay/membership routing rejected above.

## 20. Acceptance condition

Independent R2 review must demonstrate lossless equivalence to accepted basis for every unchanged numerical claim, exact resolution of the R1 B1-B8 defects, source availability for every specialized prerequisite, and exact renderer-safe representation. Any changed association affecting a reference result, changed threshold/tolerance, changed failure classification, changed family/applicability set, or changed stochastic/replay lineage is a D2 semantic change and requires explicit adjudication rather than editorial acceptance.