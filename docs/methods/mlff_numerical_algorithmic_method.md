---
kind: accepted-D2-authority-kernel
protocol_version: 6.4.0
status: ACCEPTED_CURRENT
accepted_date: 2026-09-17
accepted_basis: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
independent_review_target: e827aef9bdceb97aae5be6e89de0585a95dcf71c
independent_review_commit: 2eddd9058beda039e0ff53d4e50a189be469173b
ratified_candidate_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
parent_D1_authority: docs/methods/mlff_scientific_method.md
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
---

# mdstats MLFF D2 formal numerical authority kernel — Protocol 6.4 accepted current

## 1. Authority and exact import registry

This file is the canonical current D2 authority kernel for the mdstats MLFF numerical method. It formalizes, without changing, the accepted numerical meaning reconstructed at basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824` and exact-imports the detailed pre-Protocol-6.4 source papers pinned at stakeholder-ratified target `a4824d28775164aa942fd29fa97ee0957eb87e6f`.

Independent assembled-candidate Review passed on immutable target `e827aef9bdceb97aae5be6e89de0585a95dcf71c` at review commit `2eddd9058beda039e0ff53d4e50a189be469173b`. The stakeholder then identified a renderer-only notation defect in D2.DEF.027. Target `a4824d28775164aa942fd29fa97ee0957eb87e6f` replaces the two `\\substack` restricted sums with algebraically identical single-line restricted-index sums, changes no numerical decision or tolerance, and was explicitly ratified for canonical promotion on 2026-09-17.

Exact accepted sources are:

- `D2.SRC.GENERAL` = `hjin98/mdstats@a4824d28775164aa942fd29fa97ee0957eb87e6f:docs/methods/mlff_numerical_algorithmic_method.md`;
- `D2.SRC.ORDER` = `hjin98/mdstats@a4824d28775164aa942fd29fa97ee0957eb87e6f:docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

`D2.SRC.ORDER` is sole accepted owner for `TargetCoverageReference -> FEAS1/NEIGHBOR1 -> MVIDX -> MVSEL2 -> REPAIR2 -> MVQUAL`; `D2.SRC.GENERAL` owns unaffected numerical semantics.

Exact specialized imports are:

- `D2.IMP.SOURCE` = `D2.SRC.GENERAL`, Sections 2.1-2.4;
- `D2.IMP.STAT` = `D2.SRC.GENERAL`, Sections 3.1-3.4;
- `D2.IMP.P3_PREP` = `D2.SRC.GENERAL`, Sections 4.1-4.2;
- `D2.IMP.SPLIT_EVAL` = `D2.SRC.GENERAL`, Sections 5-7;
- `D2.IMP.E0` = `D2.SRC.GENERAL`, Section 8;
- `D2.IMP.E0_HEADS` = `D2.SRC.GENERAL`, Section 8.3: selected-head binding and the separate replay/pretraining-head foundation E0 mapping;
- `D2.IMP.OBJECTIVE` = `D2.SRC.GENERAL`, Section 9;
- `D2.IMP.P3` = `D2.SRC.GENERAL`, Sections 10-13;
- `D2.IMP.P5_EXPOSURE` = `D2.SRC.GENERAL`, Section 14;
- `D2.IMP.MONITOR` = `D2.SRC.GENERAL`, Section 15;
- `D2.IMP.CV` = `D2.SRC.GENERAL`, Sections 16-17.1;
- `D2.IMP.REPLAY` = `D2.SRC.GENERAL`, Section 18;
- `D2.IMP.PRODUCTION` = `D2.SRC.GENERAL`, Sections 19-23;
- `D2.IMP.ORDER` = `D2.SRC.ORDER`, Sections 2-16.

These exact imports are normative roots for accepted details not restated below. Definitions below formalize high-risk semantics but cannot change imported meaning.

Unless narrowed below: scientific scalar decision arithmetic is IEEE-754 binary64; counts/indices are exact integers of sufficient range; canonical ordering is accepted deterministic identity order; non-finite/undefined/stale/impossible cases fail closed; and optimized execution is admissible only under the accepted equivalence relation. Binding classes are those of the current accepted D1 authority.

## 2. Primitive numerical objects and statistical units

### D2.DEF.001 — Canonical ordered population

For finite governed frame population of cardinality `n`,

$$
P=(u_0,u_1,\ldots,u_{n-1})
$$

is its canonical ordered tuple. Set membership and tuple order are distinct.

### D2.DEF.002 — Prefix operator

For ordered tuple `pi=(v_1,...,v_n)` and integer `0<=N<=n`,

$$
\mathrm{prefix}(\pi,N)=(v_1,\ldots,v_N).
$$

A membership consumer uses the corresponding set. Cardinality alone never reconstructs prefix identity.

### D2.DEF.003 — Source numerical convention

Occurrence/geometry/label identities, row-cell/deformation convention, proper polar decomposition, stress normalization/sign/Voigt/shear rules, finite/nonsingular eligibility and identity quantization are exact imports from `D2.IMP.SOURCE`. Any changed convention that changes a governed identity/observable is non-equivalent.

### D2.DEF.004 — Finite-sequence autocorrelation estimator

For finite scalar sequence `(x_0,...,x_{N-1})` with mean `xbar`,

$$
\widehat\gamma(k)=\frac{1}{N-k}\sum_{t=0}^{N-k-1}(x_t-\bar x)(x_{t+k}-\bar x).
$$

For finite positive `gamma_hat(0)`,

$$
\widehat\rho(k)=\frac{\widehat\gamma(k)}{\widehat\gamma(0)}.
$$

Geyer's initial-positive-sequence truncation accepts adjacent lag pairs while

$$
\widehat\rho(2m-1)+\widehat\rho(2m)>0.
$$

An unpaired final positive lag may be retained. With accepted retained-lag set `K_+`,

$$
\widehat\tau_{\mathrm{int}}=\max\left(\frac12,\frac12+\sum_{k\in K_+}\widehat\rho(k)\right).
$$

The accepted FFT realization may accelerate the same estimator. No autocorrelation crosses a source gap, continuation reset or excluded interval. Constant/insufficient sequences use the typed outcome imported from `D2.IMP.STAT`, not a fabricated long correlation time.

### D2.DEF.005 — Complete-frame correlation blocks

Let `m_corr>0` be the configured correlation multiplier and `L_min>=1` the configured minimum complete-frame block length of `D2.IMP.STAT`. For every configured observable/run compute D2.DEF.004 and define

$$
\tau_{\max}=\max_{j,r}\widehat\tau_{j,r},
$$

$$
L_{\mathrm{corr}}=\max\left(1,\left\lceil m_{\mathrm{corr}}\tau_{\max}\right\rceil\right),
$$

$$
L=\max(L_{\min},L_{\mathrm{corr}})
$$

unless an explicitly accepted override is in force. The balanced all-frame split imported from `D2.IMP.STAT` preserves every eligible frame; no tail is discarded. A shorter accepted override is an adequacy limitation, not decorrelation proof.

### D2.DEF.006 — Protected-event merge and relation closure

Protected event windows are constructed at full temporal resolution before ordinary thinning. Candidate blocks intersecting one protected event are merged before role allocation. Correlation-unit, exact-geometry, protected-event, condition-scoped replica and condition-scoped structural-realization relations are projected to the requested frame universe and transitively closed. P2/P5 consume this closure rather than reconstructing a reduced relation taxonomy.

## 3. Target-size policy, exact split, evaluation order, and common preparation

### D2.DEF.007 — Current P2 structural policy domain

A valid automatic target-size policy has:

- `N_cfg`: at least three strictly increasing positive powers of two;
- `M_cfg`: exactly three strictly increasing positive powers of two;
- `H_cfg`: exactly three strictly increasing positive fidelity epochs;
- `S_seed`: ordered unique nonnegative integer optimizer seeds.

Exact numeric values are configuration bindings; these structural restrictions are fixed method constraints.

### D2.DEF.008 — Protected-component order for exact M3 allocation

Project the D1 protected relation onto exact `U_size`, form connected components, and order exactly by:

1. component cardinality group;
2. larger cardinality before smaller;
3. within one cardinality, bucket by lexicographically minimum represented `condition_id`;
4. canonical sort of component-member tuples inside each condition bucket;
5. round-robin nonempty buckets in sorted condition-ID order.

### D2.DEF.009 — Exact first-predecessor M3 allocation

Let D2.DEF.008 yield positive integer component weights `w_1,...,w_C`. Let `m_3=max(M_cfg)`. Define

$$
R_0=\{0\},
$$

$$
R_j=R_{j-1}\cup\{r+w_j:r\in R_{j-1},\ r+w_j\le m_3\}.
$$

Iterate components in D2.DEF.008 order and existing reachable totals descending; store only the first predecessor creating each new total; stop when `m_3` first becomes reachable; reconstruct that chain. Unreachable `m_3` is infeasible. Selected component union is exact `M3`; canonical-order complement is exact `P_train`. Tie/predecessor identity is numerical authority.

### D2.DEF.010 — Condition-balanced evaluation order

For exact `M3`, group UIDs by `condition_id`. Inside each bucket sort by descending priority-vector coordinates, equivalently ascending negated coordinates, then immutable UID. Repeatedly visit condition buckets in sorted condition-ID order taking one frame from each nonempty bucket. With no priority evidence, empty vectors tie and UID orders each bucket. This permutation is `pi_eval`.

For configured evaluation size `m_i`,

$$
M_i=\mathrm{set}(\mathrm{prefix}(\pi_{\mathrm{eval}},m_i)).
$$

### D2.DEF.011 — P3 common candidate-training preparation

After exact split and canonical orders are bound, fit one P3-common training state on exact `P_train` as imported by `D2.IMP.P3_PREP`, including as applicable target atomic-reference state, mean-one P3 configuration weights, binary masks, exact foundation/head identity, target objective and common model normalization/construction inputs.

Candidate projection selects frozen state for exact `T_N`; it does not refit E0, renormalize P3 weights or recompute common model normalization by candidate size. P3 common preparation is not wholesale P5 authority after method divergence.

## 4. TargetCoverageReference and required-family catalog

### D2.DEF.012 — Required-family catalog and applicability

Universal structural families are exactly:

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

`pair_distance`, `coordination`, and `local_density` are extent-bearing.

For each active accepted profile-selection provider, each valid nonconstant scalar selection feature is a required one-dimensional extent-bearing family over provider-valid frames and each represented provider environment class contributes a hard obligation. No active provider means no profile family.

For each applicable accepted pair rule, required extent-bearing raw pair families are `bond_length_distribution` over minimum pair distance, mean nearest-neighbor distance, maximum nearest-neighbor distance; and `coordination_distribution` over coordination mean and maximum.

Target-development response families include extent-bearing `force_distribution` over force-component RMS, mean force norm, maximum force norm and canonical available force-norm quantile channels; plus one scalar family for each defined nonconstant accepted channel among energy/atom, instantaneous temperature, hydrostatic strain, deviatoric strain norm, pressure, and stress deviatoric norm.

Only when target-size protocol itself uses authenticated frozen foundation identity: one required extent-bearing global residual family contains absolute energy error/atom, force-component RMSE, mean force-vector error, maximum force-vector error; and one required extent-bearing family per represented species contains component RMSE, mean vector error, maximum vector error. Foundation identity is selector-evidence identity; scratch does not acquire foundation families merely because a provider exists elsewhere.

### D2.DEF.013 — Family witness weights with one normalization only

For required family `m`, nonempty ordered witness set `W_m`, current correlation-unit identity `g(w)`, represented unit set `G_m`, and witness count `n_{m,g}` in unit `g`, define

$$
\widetilde\omega_m(w)=\frac{1}{|G_m|\,n_{m,g(w)}}.
$$

Compute canonical-order binary64 sum

$$
s_m=\sum_{w\in W_m}\widetilde\omega_m(w)
$$

and store

$$
\omega_m(w)=\frac{\widetilde\omega_m(w)}{s_m}.
$$

This is the single and only family-weight normalization. `|G_m|>0`, every `n_{m,g}>0`, and finite positive `s_m` are required.

### D2.DEF.014 — Stable weighted quantile over stored weights

For finite values `v_i` with D2.DEF.013 stored weights, stable-sort by `(v_i, original_index)`. For governed `q in [0,1)`, `Q(q)` is the first sorted value whose cumulative stored weight is at least `q`; if no such value exists, preparation fails. The stored weights are never normalized again inside this definition. The binary64 comparison threshold is `q` itself: residual post-normalization mass `sum_i omega_i` must not rescale `q`.

### D2.DEF.015 — Robust scale

For coordinate `j`, let

$$
a_j=Q_j(0.75)-Q_j(0.25),\qquad b_j=Q_j(0.99)-Q_j(0.01).
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

then `s_j=max(s_j,delta_s)`. Non-finite input fails preparation.

### D2.DEF.016 — Family metric

For dimension `d_m>=1`,

$$
d_m(a,b)=\sqrt{\frac1{d_m}\sum_{j=1}^{d_m}\left(\frac{x_{a,j}-x_{b,j}}{s_j}\right)^2}.
$$

Only applicable rows participate. A family requires at least two reference elements. Constant optional scalar families are omitted.

### D2.DEF.017 — Leave-one-out local radius

Let `beta=1/128`. For witness `w`, remove self mass, require `1-omega_m(w)>0`, divide each remaining stored weight by `1-omega_m(w)`, stable-sort other witnesses by `(d_m(w,v), canonical_witness_order)`, and choose smallest distance where cumulative renormalized mass reaches `beta-1e-15`. Failure to reach it is family infeasibility.

### D2.DEF.018 — Exact adjacency

$$
A_m(w,c)=1\Longleftrightarrow d_m(w,c)\le r_m(w)+10^{-12}\max(1,r_m(w)).
$$

Every witness must retain at least one exact candidate support edge. Approximate-neighbor substitution is non-equivalent.

### D2.DEF.019 — Multiplicity and covered mass

For selected `S subseteq P_train`,

$$
n_m(w;S)=\sum_{c\in S}A_m(w,c),
$$

$$
C_m(S)=\sum_{w\in W_m}\omega_m(w)\mathbf 1[n_m(w;S)>0].
$$

### D2.DEF.020 — Independent qualification coverage predicate

Family `m` passes direct coverage/MVQUAL iff

$$
C_m(S)+10^{-12}\ge0.95.
$$

This tolerance is not the selector Phase-A tolerance.

### D2.DEF.021 — Extent predicate

For extent coordinate `j`,

$$
L_j=Q_j(0.01),\qquad U_j=Q_j(0.99).
$$

For nonempty applicable selected values `V_j(S)`, pass iff

$$
\min V_j(S)\le L_j+10^{-12}
$$

and

$$
\max V_j(S)\ge U_j-10^{-12}.
$$

Empty `V_j(S)` fails. Each side also contributes a hard obligation of minimum one.

## 5. Canonical obligations and FEAS1

### D2.DEF.022 — Source obligation

A source obligation is

$$
o=(L_o,A_o,k_o,s_o),
$$

with D1 semantic locus `L_o`, exact current-`P_train` incidence `A_o`, positive integer minimum `k_o`, and source/provenance namespace `s_o`.

Automatic obligations are every applicable represented P2 condition, structural-event type, active profile environment class, extent lower side, extent upper side and current P1 correlation interval/unit, each minimum one. Explicit current hard-support obligations are projected through current P2 authority with declared positive minima.

### D2.DEF.023 — Obligation canonicalization

Source obligations group only when accepted D1 locus is equal. Exact incidence inside a purported same-locus group must also agree or construction fails. Incidence equality without locus equality never aliases obligations. Effective minimum is maximum source minimum within one valid locus group. Source-ID reuse for different semantics fails; different loci with identical incidence remain distinct.

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

Obligation is satisfied iff `q_o(S)>=k_o`.

### D2.DEF.025 — FEAS1 configured horizon

For configured sizes,

$$
N_{\max}=\max N_{\mathrm{cfg}}.
$$

FEAS1 verifies exact-domain/self-support consistency, obligation support capacity, and conservative lower-bound evidence under the same family/obligation authority. A lower bound above `N_max` proves configured-ladder infeasibility; FEAS1 never creates rescue sizes or relaxes predicates. Historical support-degree bins, own-correlation exclusion and fragile-zero-mass tolerance remain diagnostics as imported by `D2.IMP.ORDER`.

### D2.AX.001 — Exact sparse representation

NEIGHBOR1/MVIDX may use any exact representation only if witness-candidate adjacency, canonical-obligation incidence, current correlation-unit codes, canonical ordering and identities equal the definitions above.

## 6. MVSEL2

### D2.DEF.026 — Selector state

Authoritative selector state contains ordered selected prefix, family witness multiplicities and covered masses, canonical obligation counts, correlation-unit selected counts, and exact representative state sufficient for current gains. Lazy heaps, caches, native batches, workers and queue completion order are execution state.

### D2.DEF.027 — Candidate gains

For available candidate `c`,

$$
O_c(S)=\{o:q_o(S)<k_o\text{ and }c\in A_o\},\qquad H(c;S)=|O_c(S)|,
$$

$$
G_m(c;S)=\sum_{w\in W_m:\,A_m(w,c)=1,\,n_m(w;S)=0}\omega_m(w),\qquad G(c;S)=\sum_mG_m(c;S),
$$

$$
R(c;S)=\sum_m\sum_{w\in W_m:\,A_m(w,c)=1}\frac{\omega_m(w)}{n_m(w;S)+1}.
$$

A stronger minimum extends one locus's unsatisfied duration; it never multiplies its hard-gain vote.

### D2.DEF.028 — Sparse diversity

Define

$$
W_m(c)=\{w\in W_m:A_m(w,c)=1\},\qquad M(c)=\{m:|W_m(c)|>0\}.
$$

If `M(c)` is empty, `D(c;S)=0`; otherwise

$$
D(c;S)=\frac1{|M(c)|}\sum_{m\in M(c)}\left[\frac1{|W_m(c)|}\sum_{w\in W_m(c)}\frac1{n_m(w;S)+1}\right].
$$

### D2.DEF.029 — Phase-A family-completion predicate

With fixed selector tolerance `epsilon_sel=1e-14`, family `m` is Phase-A complete iff

$$
C_m(S)\ge0.95-10^{-14}.
$$

Equivalently it keeps Phase A active while `C_m(S)<0.95-1e-14`. This is intentionally distinct from D2.DEF.020.

### D2.DEF.030 — Phase-A winner

Phase A is active iff any canonical obligation is unsatisfied or any required family fails D2.DEF.029. Filter available candidates lexicographically:

1. if an obligation is unsatisfied, maximum integer `H`;
2. first canonical family minimizing `C_m/0.95` among families tied within `1e-14` at the minimum;
3. maximum bottleneck `G_m` within `1e-14`;
4. maximum total `G` within `1e-14`;
5. minimum selected count of candidate's correlation unit;
6. maximum `R` within `1e-14`;
7. maximum `D` within `1e-14`;
8. minimum stable UID.

Winner mutates authoritative state exactly once.

### D2.DEF.031 — Phase-B winner

After all obligations and D2.DEF.029 family predicates pass, choose by maximum `R` within `1e-14`, minimum correlation-unit selected count, maximum `D` within `1e-14`, then minimum stable UID. Continue toward a complete permutation subject only to configured-shell repair.

### D2.DEF.032 — Full-forward oracle

At every rank recompute exact current D2.DEF.027-028 for every available candidate, apply D2.DEF.030 or D2.DEF.031, choose one winner, then mutate state. Optimized execution must reproduce this rank sequence.

### D2.DEF.033 — Certified-lazy Phase-B equivalence

At required rebase compute exact `R_g(c)` for every available candidate and

$$
B_g(c)=\mathrm{nextafter}(R_g(c),+\infty).
$$

Stale values are upper bounds only. Refreshed representative gain exceeding earlier exact value by more than `5e-13` fails. Refresh every stale candidate whose bound can enter inclusive contender region. Certification terminates only when

$$
B_{\max}<R_{\mathrm{best}}-10^{-14}.
$$

Every candidate with `R(c;S)>=R_best-1e-14` must have exact current score before downstream tie dimensions. If certification cannot be proved, rebuild or use D2.DEF.032.

## 7. REPAIR2

### D2.DEF.034 — Configured shell and removal eligibility

For strictly increasing `N_1<...<N_K`, set `N_0=0`; shell `i` is `[N_{i-1},N_i)`. Only that shell is removable; lower ranks are immutable.

Candidate is removable only if unique covered mass `<=1e-14` and removal increases no canonical obligation deficit. Sort removable candidates by representative loss ascending, removed-candidate correlation-unit selected count descending, then removed UID ascending; keep at most 64.

### D2.DEF.035 — Replacement frontier

For contemplated removal evaluate replacement against immutable pre-swap state by maximum hard gain when obligations remain pending, first canonical bottleneck family, maximum bottleneck new coverage, maximum total new coverage, minimum hypothetical correlation-unit count after removal, maximum representative gain, maximum sparse diversity, then minimum replacement UID. Floating contender comparisons use `1e-14` unless another fixed predicate applies.

### D2.DEF.036 — Global repair objective

For integer `k>=1`,

$$
H_k=\sum_{j=1}^{k}\frac1j,\qquad H_0=0,
$$

$$
U_{\mathrm{rep}}(S)=\sum_m\sum_{w\in W_m}\omega_m(w)H_{n_m(w;S)}.
$$

Define

$$
J(S)=\left(D_{\mathrm{hard}}(S),\min_mC_m(S),\sum_mC_m(S),U_{\mathrm{rep}}(S),-\sum_gb_g(S)^2\right).
$$

Minimize component 1; maximize components 2-4 with `1e-14` tolerance; then maximize exact integer component 5. A swap is admissible only if it strictly improves `J` and every family satisfies

$$
C_m(S_{\mathrm{after}})+10^{-14}\ge C_m(S_{\mathrm{before}}).
$$

Objective-equivalent admissible proposals use ascending `(representative_loss, removed_rank, removed_UID, replacement_UID)`.

### D2.DEF.037 — Repair limits, rank inheritance, terminal continuation

Per configured shell: at most 2 passes, 32 accepted swaps, removal shortlist 64. Accepted replacement inherits removed rank; if replacement already occurs at future rank, move removed candidate to that future rank. Master permutation and earlier configured prefixes remain intact.

After final configured shell, continue same exact optimized MVSEL2 until all `P_train` is ordered. There is no extra repair shell or alternate suffix method.

### D2.AX.002 — Post-repair reconstruction

After accepted swap, all prefix-derived lazy/frontier/marginal/cache/checkpoint/journal state from pre-swap prefix is stale. Reconstruct exact forward state from authenticated primitive family/obligation/correlation evidence and repaired prefix; Phase-B continuation performs exact all-candidate rebase. Zero-swap shell may retain authentic state whose prefix identity is unchanged.

## 8. Independent MVQUAL and automatic admission

### D2.DEF.038 — Independent configured-prefix qualification

For configured `N`, independently recompute direct family masses/predicates under D2.DEF.016-020, required extents under D2.DEF.021, canonical obligation counts under D2.DEF.024, and required training-label usability from immutable reference evidence.

MVIDX is only an exact secondary cross-check; direct and MVIDX family mass must agree with `rtol=0`, `atol=5e-12`. Prefix qualifies iff every predicate passes. Under fixed nested prefixes/evidence qualification is `FAIL* -> PASS*`; later `PASS -> FAIL` fails closed. MVQUAL does not rank sizes.

### D2.DEF.039 — Automatic-screen admission

$$
Q_{\mathrm{cfg}}=\{N\in N_{\mathrm{cfg}}:T_N\text{ passes D2.DEF.038}\}.
$$

Automatic P3 screening requires `|Q_cfg|>=3`; otherwise `INSUFFICIENT_AUTOMATIC_COMPARISON`. An unqualified configured prefix is excluded from `Q_cfg` and cannot be admitted manually; it does not invalidate other qualified configured prefixes. No membership or ladder is changed.

## 9. Atomic-reference fitting and identifiability

### D2.DEF.040 — Composition matrix

For exact authorized fit membership and atomic-species basis ordered by atomic number, define configuration-by-species count matrix `C` and total-energy vector `y`.

### D2.DEF.041 — Foundation-residual fit

For exact selected foundation identity `Phi`, predicted energy `y_fnd`, head-local reference vector `e_fnd(Phi)`, residual `r=y-y_fnd`, and accepted regularization/anchor tuple `(lambda,delta e_prior)`, solve

$$
\widehat{\delta e}=\arg\min_{\delta e}\left(\|C\delta e-r\|_2^2+\lambda\|\delta e-\delta e_{\mathrm{prior}}\|_2^2\right),
$$

and set

$$
e_{\mathrm{target}}(\Phi)=e_{\mathrm{fnd}}(\Phi)+\widehat{\delta e}.
$$

CV fit domain is exact fold gradient membership; final production uses exact `T_selected`; monitor and held-out labels are excluded.

### D2.DEF.042 — Free null space and composition transfer

Let `N_free` be directions unconstrained by authorized composition equations and accepted anchors; without accepted anchor, `N_free=ker(C)` under accepted numerical-rank rule. Required composition `c` is transfer-feasible iff

$$
c^Tv=0\quad\text{for every }v\in N_{\mathrm{free}}.
$$

Numerical rank tolerance cannot create absent information.

## 10. Foundation-P5 robust objective

### D2.DEF.043 — Scalar Huber function

For `delta>0`,

$$
h_\delta(x)=\begin{cases}
\frac12x^2,&|x|\le\delta,\\
\delta\left(|x|-\frac12\delta\right),&|x|>\delta.
\end{cases}
$$

### D2.DEF.044 — Dimensional thresholds

$$
\delta_E=0.01\ \mathrm{eV/atom},\qquad
\delta_{F,0}=0.01\ \mathrm{eV/angstrom},\qquad
\delta_S=0.01\ \mathrm{eV/angstrom^3}.
$$

For masked reference-force norm `f` in `eV/angstrom`,

$$
\delta_F(f)=\delta_{F,0}\times\begin{cases}
1.0,&f<100,\\
0.7,&100\le f<200,\\
0.4,&200\le f<300,\\
0.1,&f\ge300.
\end{cases}
$$

### D2.DEF.045 — Property reductions and total objective

`L_E` is arithmetic mean over configurations of per-atom masked energy Huber loss; `L_F` is arithmetic mean over all stored Cartesian force components after binary force masking using D2.DEF.044 conditional threshold; `L_S` is arithmetic mean over all nine stored Cartesian stress entries per admitted configuration. Symmetric off-diagonals therefore occur twice; six-component Voigt mean is different.

$$
L_{P5}=L_E+10L_F+L_S.
$$

No nontrivial per-configuration scalar and no target/replay training-head scalar occur. A phase-dependent loss mutation is another method unless separately accepted.

## 11. P3 normalization, estimator, reducer, and restart

### D2.DEF.046 — Updates per epoch and first-order normalization

For target size `N>0`, target batch size `B>0`, with final partial target batch retained,

$$
U_N=\left\lceil\frac NB\right\rceil.
$$

For reference `N_ref`, `U_ref=ceil(N_ref/B)`,

$$
s_N=\frac{U_{\mathrm{ref}}}{U_N},\qquad LR_N=LR_{\mathrm{ref}}s_N.
$$

When EMA is enabled,

$$
\beta_N=\beta_{\mathrm{ref}}^{s_N}.
$$

This is first-order normalization, not exact trajectory equivalence. Values remain fixed through later fidelity boundaries. `floor(N/B)` updates is another experiment.

### D2.DEF.047 — P3 estimator and complete-seed score

For `K>0` admitted force components,

$$
E_{N,s}=1000\sqrt{\frac1K\sum_{k=1}^{K}(\widehat F_k-F_k)^2}
$$

in `meV/angstrom`; non-finite output is typed failure.

A candidate score exists only when every required seed is valid:

$$
\overline E_N=\frac1{|S_{\mathrm{seed}}|}\sum_{s\in S_{\mathrm{seed}}}E_{N,s}.
$$

### D2.DEF.048 — Practical-equivalence ranking

For active successful candidate set `A`,

$$
E_{\min}=\min_{N\in A}\overline E_N,
$$

$$
E_{\mathrm{eq}}=\{N\in A:\overline E_N\le E_{\min}+\epsilon\}.
$$

Choose smallest `N` in `E_eq`, remove it, repeat. Only accepted tiny fixed floating guard may supplement scientific `epsilon`.

### D2.DEF.049 — Structural funnel and success sufficiency

Let `A_j` be active candidate set entering fidelity boundary `j`, and `S_j subseteq A_j` the candidates with valid complete-seed score at that boundary. With `q=|Q_cfg|>=3`, structural survivor counts are

$$
q\rightarrow\min(q,4)\rightarrow2\rightarrow1.
$$

At boundary 1 require

$$
|S_1|\ge\min(|A_1|,4),
$$

then rank `S_1` by D2.DEF.048 and retain first `min(q,4)`. At boundary 2 and terminal boundary require at least two successful candidates before comparison; otherwise `INSUFFICIENT_COMPARISON`. Boundary 2 retains first two. Exact epochs and evaluation sizes are the three configured positions of D2.DEF.007.

### D2.DEF.050 — Configured-ceiling terminal rule

If configured maximum `N_max` is a successful terminal finalist and

$$
\overline E_{N_{\max}}+\epsilon<\overline E_N
$$

for every other successful terminal finalist, recommend `N_max` with explicit nonconvergence-at-configured-ceiling evidence. Otherwise recommend first D2.DEF.048-ranked terminal finalist. No extrapolation or rescue size exists.

### D2.AX.003 — Continuous trajectory and authenticated restart

Each active `(N,seed)` is one continuous trajectory through fidelity boundaries. Model, optimizer, EMA where enabled, learning-rate state and accepted Python/NumPy/Torch RNG lineage restore from authenticated predecessor. Unaccepted scratch is not continuation authority. Restart cannot change membership, common preparation, normalization, seed or boundary identity.

## 12. Replay label modes and P5 exposure

### D2.DEF.051 — Replay geometry and label mode

Let `D_r^geom` be authenticated prepared replay geometry/source membership and split. Replay label mode is `TRUE_REFERENCE` or `FOUNDATION_PSEUDO`; true reference is canonical default when labels exist, pseudo requires explicit opt-in and exact frozen `Phi`.

$$
D_r(\ell)=\{(x,y_\ell(x)):x\in D_r^{\mathrm{geom}}\}.
$$

For true mode use canonical true-reference/DFT label; for pseudo use exact frozen `Phi` and accepted prediction policy. Switching label mode over one prepared source/split must not change `D_r^geom`. Pseudo replay still requires a distinct authenticated true-reference replay monitor.

### D2.DEF.051A — Replay/pretraining-head foundation E0 mapping

For exact authenticated foundation identity `Phi`, let

$$
e_{\mathrm{replay}}(\Phi)
$$

denote the replay/pretraining-head foundation elemental-reference mapping imported exactly from `D2.IMP.E0_HEADS`. It must be extracted from the same authenticated selected foundation checkpoint/head/lineage that initializes the accepted replay method. It is distinct from the fitted target correction `e_target(Phi)` of D2.DEF.041. A first/default/other-head fallback is non-equivalent. If the exact replay-head mapping cannot be established for the selected lineage, replay preparation is undefined and fails closed.

### D2.DEF.052 — Replay lineage and qualification currentness

Let `Q_r` be the exact replay qualification-policy/evidence identity and current qualification state required by D1.DEF.022 and the accepted replay/checkpoint owners. It includes the independent true-reference retention qualification applicable to the configured replay method and is separate from training label mode.

Replay lineage binds replay geometry/source membership/split, label mode, true-reference monitor, `Q_r`, foundation/head where applicable, `e_replay(Phi)` where applicable, prediction policy, and realized exposure. Changing any component, including replay qualification policy/evidence/state, invalidates dependent P5 evidence. Changing label mode over the same authenticated prepared source/split does not by itself change replay geometry membership.

### D2.DEF.053 — Combined corpus and update geometry

For current two-head replay,

$$
D_{\mathrm{train}}=D_r\Vert D_t.
$$

Seeded loader shuffles integer indices of this replay-first/target-second tuple. There is no balancing sampler or intentional target duplication. For current qualified single-process non-LBFGS path with batch size `B`, `drop_last=true` and

$$
U=\left\lfloor\frac{|D_r|+|D_t|}{B}\right\rfloor.
$$

Exactly `UB` examples are consumed per nominal epoch. Distributed path is not presumed equivalent without qualification.

## 13. Common monitor and folds

### D2.DEF.054 — Monitor quota

For usable protected `OUTER_MONITOR` parent `P_mon`, required cardinality is 256; smaller parent is infeasible. Frame stratum is `<condition_id>:<run_id>` and within-stratum order `(source_frame_index,frame_uid)`.

With fixed seed `q=161803`, stratum `s` marker is lowercase SHA-256 hex of UTF-8 `<q>\0quota\0<s>`, with decimal `q`. Sort `(marker,s)`, initialize zero quotas, repeatedly sweep increasing any stratum below capacity until exactly 256 slots are allocated.

### D2.DEF.055 — Monitor systematic positions

For stratum capacity `n`, quota `k`, `1<=k<=n`, namespace `target:<s>`, hash UTF-8 `<q>\0<namespace>`, take first eight digest bytes unsigned big-endian integer `I`, define

$$
u=\frac{I+0.5}{2^{64}},
$$

$$
p_j=\min\left(n-1,\left\lfloor\frac{(j+u)n}{k}\right\rfloor\right),\quad j=0,\ldots,k-1.
$$

Positions must be distinct. Parent/policy/seed/stratum identities plus exact membership define monitor identity.

### D2.DEF.056 — Fold order and purge

For frozen `T_N`, sorted protected-component identities `C_comp`, fold count `K>=2`, partition seed `s_cv`, algorithm identity `a`, membership digest `d_T`: if `|C_comp|<K`, CV is infeasible. Marker for component `c` is SHA-256 hex of UTF-8 `<a>|<d_T>|<s_cv>|<c>`; sort `(marker,c)` and assign position `j` to held-out fold `j mod K`.

For fold `i`, let held-out set `O_i` and lexicographically sorted remaining `R_i`. With configured nonnegative `p_cfg`,

$$
p_i=\min\left(p_{\mathrm{cfg}},\max(0,|R_i|-2)\right).
$$

If zero purge is empty; if one choose middle; if greater than one use ties-to-even systematic indices of spacing `h=(|R_i|-1)/(p_i-1)`, deduplicate, fill lowest unused indices to cardinality, then sort. Gradient set is complement of held-out and purge. `M_mon` is external.

## 14. Checkpoint predicates, CV, and production

### D2.DEF.057 — Shared checkpoint constraint

For checkpoint `c`, `S(c)` is exact shared mandatory constraint conjunction imported from `D2.IMP.CV`: finite required metrics, replay degradation within accepted budget using authenticated true-reference replay monitor when replay active, plus required physical/integrity gates. Pseudo labels cannot satisfy true-reference retention. Replay-active evidence must belong to the current `Q_r` lineage of D2.DEF.052.

### D2.DEF.058 — Role-effective checkpoint predicate

Let `r_mon(c)` be target force-component RMSE on exact `M_mon` in `eV/angstrom`. For role `rho`,

$$
A_\rho(c)=S(c)\wedge r_{\mathrm{mon}}(c)\le\tau_\rho.
$$

CV uses `tau_CV`, production `tau_prod`. Inclusive binary64 boundary: equality passes, next representable double above resolved ceiling fails.

### D2.DEF.059 — CV outer predicate and all-position acceptance

Frozen fold representative passes outer criterion iff exact configured held-out metric is finite and `<=theta_CV`. Alternative outer metrics retain own units/threshold and never supply `tau_CV`.

CV accepts iff every required `(fold,seed)` position completes frozen method/horizon, has nonempty admissible checkpoint set under D2.DEF.058, freezes a representative under imported accepted target-side ranking, and that representative passes outer predicate. No mean/majority/best-seed/dispersion rescue exists.

### D2.AX.004 — Role currentness

Changing `tau_CV` or `theta_CV` stales dependent CV evidence and production authorization derived from it while leaving `tau_prod` and shared method unchanged. Changing `tau_prod` stales production role evidence only. Changing shared `S` can stale both. A replay-qualification change stales replay-dependent P5 evidence through D2.DEF.052 without changing replay geometry membership solely because label mode changed. Re-thresholding stored classifications does not create current evidence.

### D2.AX.005 — Fresh production

Fresh production starts new model/optimizer lineage on exact complete `T_selected`, fits training-dependent state there only, uses same `M_mon` and shared checkpoint mechanics as CV, and applies `tau_prod`. P3 `M3` has no production checkpoint role. Replay-enabled production retains D2.DEF.051-053, current `Q_r`, exact `e_replay(Phi)` where applicable, plus true-reference retention.

## 15. Continuation, equivalence, and fail-closed semantics

### D2.DEF.060 — Authenticated continuation

Continuation is admissible only when all identities needed to prove exact run boundary match: population/membership, method/policy parameters, foundation/head, objective/exposure, selector/reference where applicable, optimizer/EMA/RNG state and accepted predecessor boundary. Uncommitted scratch is not continuation authority.

### D2.DEF.060A — Numerical-equivalence relation registry

For authoritative outputs, the comparison relation is source-closed as follows:

1. canonical memberships, UIDs, component/order/rank sequences, discrete decisions, integer counts, lineage identities and repair traces compare by exact identity/equality under their defining objects;
2. local numerical predicates with explicit fixed tolerances/guards use exactly D2.DEF.018, D2.DEF.020-021, D2.DEF.029-030, D2.DEF.033, D2.DEF.036, D2.DEF.038 and D2.DEF.058-059 as applicable;
3. accepted source-owned metric/equality relations not restated locally are imported only from exact `D2.SRC.GENERAL` or `D2.SRC.ORDER`;
4. every other governed binary64 scientific output whose owner supplies no nonzero tolerance compares by exact canonical binary64 value/reference arithmetic.

No backend-observed discrepancy, performance result, generic “close enough” rule, or unlisted tolerance can create a new equivalence relation.

### D2.DEF.061 — Numerical equivalence

For optimized realization `A`, accepted reference `R`, and authoritative output set `O`,

$$
A\equiv_O R
$$

iff throughout the declared validity domain every output/decision in `O` satisfies the exact relation selected by D2.DEF.060A. Performance does not establish equivalence.

### D2.AX.006 — Execution noninterference

Worker count, queue completion order, chunk/block size, mmap layout, cache residence, native backend, device batching and restart route are execution-only iff D2.DEF.061 holds for all governed outputs.

### D2.DEF.062 — Typed failure set

Fail closed for non-finite fitted statistics; invalid/empty required family mass; unreachable exact `M3`; malformed structural policy; unsupported provider/family; zero leave-one-out denominator; unreachable local mass; missing witness support; impossible hard obligation; configured-ladder infeasibility; stale lazy certification; repair invariant failure; direct/MVIDX mismatch; non-identifiable E0 transfer; pseudo replay without exact `Phi` or true monitor; missing/mismatched replay-head E0; invalid or stale replay qualification/lineage; impossible 256-monitor; insufficient fold components; missing required fold/seed; no admissible checkpoint; non-finite P3 outcome; insufficient reducer comparison; stale/mismatched continuation; materially different objective/exposure/method. Tolerance widening, support relaxation, role substitution, pseudo fallback, or rescue-size invention are not error handlers.

## 16. Parameter binding ledger

| Coordinate | Binding class | Current value/domain |
| --- | --- | --- |
| family hard coverage | `FIXED_METHOD_COORDINATE` | `0.95` |
| extent quantiles | `FIXED_METHOD_COORDINATE` | `0.01,0.99` |
| family-weight normalization count | `FIXED_METHOD_COORDINATE` | exactly once |
| robust-scale floor/branch | `FIXED_METHOD_COORDINATE` | `1e-12` |
| local-radius mass/guard | `FIXED_METHOD_COORDINATE` | `1/128`, `1e-15` |
| adjacency tolerance | `FIXED_METHOD_COORDINATE` | `1e-12*max(1,r)` |
| MVQUAL coverage tolerance | `FIXED_METHOD_COORDINATE` | `1e-12` |
| MVSEL2 tolerance | `FIXED_METHOD_COORDINATE` | `1e-14` |
| lazy monotonicity guard | `FIXED_METHOD_COORDINATE` | `5e-13` |
| REPAIR2 tolerance/limits | `FIXED_METHOD_COORDINATE` | `1e-14`, 2 passes, 32 swaps, shortlist 64 |
| direct-vs-MVIDX mass | `FIXED_METHOD_COORDINATE` | `rtol=0`, `atol=5e-12` |
| candidate/evaluation/fidelity/seed values | `CONFIGURABLE_FAMILY` | D2.DEF.007 |
| practical `epsilon` | `CONFIGURABLE_FAMILY` | finite positive response-unit value |
| Huber thresholds/factors | `FIXED_METHOD_COORDINATE` | D2.DEF.044 |
| P5 coefficients | `FIXED_METHOD_COORDINATE` | `1:10:1` |
| replay label mode | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | true-reference default; pseudo explicit opt-in |
| replay qualification identity/state | `DERIVED` | configured replay policy/evidence/current qualification |
| replay-head E0 | `DERIVED` | exact selected foundation checkpoint/head mapping |
| P5 corpus order/drop policy | `FIXED_METHOD_COORDINATE` | replay then target; `drop_last=true` |
| monitor cardinality/seed | `FIXED_METHOD_COORDINATE` | `256`, `161803` |
| CV fold count | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | integer `K>=2`, default `3` |
| `tau_CV`,`theta_CV`,`tau_prod` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | current defaults `45/45/30 meV/angstrom` for default force metric |

## 17. Current falsification and reopen oracles

Qualification and any future reopen review must attempt at least: one-normalization governed-quantile adversaries; selector-vs-MVQUAL tolerance interval adversary; exact component-order/first-predecessor `M3`; condition-balanced `pi_eval`; structural-policy rejection; candidate-common-preparation perturbation; minimum-three-qualified admission including an unqualified configured prefix with at least three remaining qualified candidates; exact funnel/sufficiency/ceiling cases; autocorrelation/block/event fixtures; required-family applicability fixtures; exact adjacency boundaries; full-forward/lazy rank equality; Phase-A tie behavior; REPAIR2 frontier/trace/limits/rank inheritance/no-extra-shell; direct/MVIDX mass and MVQUAL monotonicity; E0 null-space transfer; replay-head E0 selected-head binding and target/replay E0 separation; robust P5 dimensional/nine-stress/mask/no-head-scalar; true-vs-pseudo replay geometry invariance and true retention; replay qualification-lineage invalidation; replay-first seeded exposure/drop-last; monitor/fold reconstruction; role-threshold boundaries/selective invalidation; equivalence-registry source closure; and worker/backend/restart invariance.

The weighted-quantile oracle must exercise actual governed quantiles and one-time stored binary64 weights, and it must reproduce the exact prior D4 rescaling quantity `t = cumulative[-1]` with `cumulative = np.cumsum(stored_weights, dtype=np.float64)`. Required discriminating cases generated by the accepted correlation-balanced weight constructor are: counts `(50,1)` at `q=0.01` (direct index 0, residual-terminal-mass-rescaled index 1); `(2,6)` at `q=0.25` (direct index 0, rescaled index 1); `(1,6)` at `q=0.75` (direct index 4, rescaled index 3); and `(1,150)` at `q=0.99` (direct index 148, rescaled index 147). Each case must verify `t != 1.0` and compare cumulative stored mass directly with `q`. `np.sum(stored_weights)` is not a substitute for `t`, because the prior D4 implementation used terminal cumulative mass and binary64 reduction order can make the two residual sums differ.

## 18. D2 -> D3 handoff, acceptance and reopen condition

D3 owns persistence, concurrency, resource admission, software decomposition, dependency adaptation, build topology, and durable restart representation. It may simplify execution but may not create a second numerical owner or weaken/change the method above.

This kernel is accepted-current under Protocol 6.4 after independent Review PASS of `e827aef9bdceb97aae5be6e89de0585a95dcf71c`, the renderer-only D2.DEF.027 correction bound at `a4824d28775164aa942fd29fa97ee0957eb87e6f`, and stakeholder ratification on 2026-09-17. The correction preserves the exact candidate-gain sets and sums and therefore changes no numerical result, decision, tolerance, failure classification, family/applicability set, stochastic exposure, or replay lineage.

Any future change to one of those governed semantics requires D2 adjudication. Pure renderer/editorial repairs remain representation work only when algebraic and decision equivalence are explicitly verified.