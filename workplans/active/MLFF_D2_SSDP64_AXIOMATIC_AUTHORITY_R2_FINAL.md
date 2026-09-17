---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_R2_FINAL_AWAITING_INDEPENDENT_REVIEW
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
repairs_review: workplans/active/MLFF_D1_D2_SSDP64_INDEPENDENT_REVIEW_R1.md
parent_D1_candidate: workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_R2_REPAIRED.md
supersedes_proposed_candidates:
  - workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE.md
  - workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE_R2.md
  - workplans/active/MLFF_D2_SSDP64_AXIOMATIC_AUTHORITY_R2_REPAIRED.md
---

# Proposed MLFF D2 formal numerical authority kernel — R2 final

## 1. Authority and exact import registry

This is the sole D2 file in the repaired R2 semantic candidate. Earlier D2 candidate files listed in front matter are authoring history only and do not compose with this candidate.

The candidate formalizes, without changing, accepted MLFF D2 at repository `hjin98/mdstats` basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. It remains proposed until a fresh independent R2 review passes and the stakeholder ratifies the exact reviewed candidate.

Exact accepted sources are:

- `D2.SRC.GENERAL` = `hjin98/mdstats@cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824:docs/methods/mlff_numerical_algorithmic_method.md`;
- `D2.SRC.ORDER` = `hjin98/mdstats@cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824:docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

`D2.SRC.ORDER` is sole accepted owner for `TargetCoverageReference -> FEAS1/NEIGHBOR1 -> MVIDX -> MVSEL2 -> REPAIR2 -> MVQUAL`. `D2.SRC.GENERAL` remains owner for unaffected source/statistical/P1/P2/P3, `pi_eval`, atomic-reference, objective, replay, monitor/CV/production, threshold, restart, precision, and falsification semantics.

Exact specialized imports are:

- `D2.IMP.SOURCE` = `D2.SRC.GENERAL`, Sections 2.1-2.4;
- `D2.IMP.STAT` = `D2.SRC.GENERAL`, Sections 3.1-3.4;
- `D2.IMP.P3_PREP` = `D2.SRC.GENERAL`, Sections 4.1-4.2;
- `D2.IMP.SPLIT_EVAL` = `D2.SRC.GENERAL`, Sections 5-7;
- `D2.IMP.E0` = `D2.SRC.GENERAL`, Section 8;
- `D2.IMP.OBJECTIVE` = `D2.SRC.GENERAL`, Section 9;
- `D2.IMP.P3` = `D2.SRC.GENERAL`, Sections 10-13;
- `D2.IMP.P5_EXPOSURE` = `D2.SRC.GENERAL`, Section 14;
- `D2.IMP.MONITOR` = `D2.SRC.GENERAL`, Section 15;
- `D2.IMP.CV` = `D2.SRC.GENERAL`, Sections 16-17.1;
- `D2.IMP.REPLAY` = `D2.SRC.GENERAL`, Section 18;
- `D2.IMP.PRODUCTION` = `D2.SRC.GENERAL`, Sections 19-23;
- `D2.IMP.ORDER` = `D2.SRC.ORDER`, Sections 2-16.

These imports are normative roots for accepted details not restated below. A definition below makes high-risk semantics formal-first but cannot change imported accepted meaning.

Unless a narrower definition states otherwise: scientific scalar decision arithmetic is IEEE-754 binary64; counts and indices are exact integers of sufficient range; canonical ordering is the accepted deterministic identity order of the governed object; non-finite, undefined, stale, or impossible cases fail closed; and optimized execution is admissible only when equivalent to the accepted reference relation.

Binding classes are `FIXED_METHOD_COORDINATE`, `CONFIGURABLE_FAMILY`, `CONFIGURABLE_WITH_GENERATED_DEFAULT`, and `DERIVED` with the meanings given by the repaired D1 parent.

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

Occurrence/geometry/label identities, row-cell/deformation convention, proper polar decomposition, stress normalization/sign/Voigt/shear rules, finite/nonsingular eligibility and source-identity quantization are imported exactly from `D2.IMP.SOURCE`. A changed transpose, sign, shear factor, unit conversion, implicit reference cell or identity quantization that changes a governed output is numerically non-equivalent.

### D2.DEF.004 — Finite-sequence autocorrelation estimator

For finite scalar sequence `(x_0,...,x_{N-1})` with arithmetic mean `xbar`, define unbiased lag-`k` autocovariance

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

An unpaired final positive lag may be retained. The integrated time is

$$
\widehat\tau_{\mathrm{int}}=\max\left(\frac12,\frac12+\sum_{k\in K_+}\widehat\rho(k)\right),
$$

with `K_+` the accepted retained lags. The accepted fast-Fourier-transform implementation may accelerate the same estimator. No autocorrelation crosses a source gap, continuation reset or excluded interval. Constant or insufficient sequences use the typed shared-sampling outcome of `D2.IMP.STAT`; no fabricated long correlation time is substituted.

### D2.DEF.005 — Complete-frame correlation blocks

For each configured observable and contiguous run compute D2.DEF.004, then

$$
\tau_{\max}=\max_{j,r}\widehat\tau_{j,r},
$$

$$
L_{\mathrm{corr}}=\max\left(1,\left\lceil m\tau_{\max}\right\rceil\right),
$$

$$
L=\max(L_{\min},L_{\mathrm{corr}})
$$

unless an explicitly accepted override is in force. The balanced all-frame split of `D2.IMP.STAT` preserves every eligible frame; no remainder/tail is discarded. A shorter accepted override is an adequacy limitation, not proof of decorrelation.

### D2.DEF.006 — Protected-event merge and relation closure

Protected event windows are constructed at full temporal resolution before ordinary thinning. Candidate blocks intersecting one protected event are merged before role allocation. The five accepted relation families—correlation-unit, exact geometry, protected-event, condition-scoped replica, and condition-scoped structural-realization—are projected to the requested frame universe and transitively closed. P2/P5 consume that closure rather than reconstructing a reduced relation taxonomy.

## 3. Target-size policy, exact split, evaluation order, and common preparation

### D2.DEF.007 — Current P2 structural policy domain

A valid automatic target-size policy instance satisfies:

- `N_cfg`: at least three strictly increasing positive powers of two;
- `M_cfg`: exactly three strictly increasing positive powers of two;
- `H_cfg`: exactly three strictly increasing positive fidelity epochs;
- `S_seed`: ordered unique nonnegative integer optimizer seeds.

Exact numeric values are configuration bindings. These structural restrictions are fixed numerical-method constraints.

### D2.DEF.008 — Protected-component order for exact M3 allocation

Project D1 protected relation onto exact `U_size`, form connected components, then order them exactly by:

1. group by component cardinality;
2. larger cardinality before smaller;
3. within one cardinality, bucket by lexicographically minimum represented `condition_id`;
4. sort component-member tuples canonically inside each condition bucket;
5. round-robin nonempty buckets in sorted condition-ID order.

This order is method authority because multiple exact reserve subsets can exist.

### D2.DEF.009 — Exact first-predecessor M3 allocation

Let D2.DEF.008 yield positive integer component weights `w_1,...,w_C`. Let `m_3` be the largest configured evaluation cardinality from D2.DEF.007. Define

$$
R_0=\{0\},
$$

$$
R_j=R_{j-1}\cup\{r+w_j:r\in R_{j-1},\ r+w_j\le m_3\}.
$$

Iterate components in D2.DEF.008 order and existing reachable totals in descending order. Store only the first predecessor creating each new total, stop when `m_3` first becomes reachable, and reconstruct that chain. Unreachable `m_3` is infeasible. The selected component union is exact `M3`; the canonical-order complement is exact `P_train`. A different tie/predecessor rule is non-equivalent when it changes membership.

### D2.DEF.010 — Condition-balanced evaluation order

For exact `M3`, group frame UIDs by `condition_id`. Within each bucket sort by descending priority-vector coordinates, equivalently ascending negated coordinates, then immutable UID. Repeatedly visit buckets in sorted condition-ID order and take one frame from each nonempty bucket. With no priority evidence, empty vectors tie and UID orders each bucket. The resulting permutation is `pi_eval`.

For configured evaluation size `m_i`,

$$
M_i=\mathrm{set}(\mathrm{prefix}(\pi_{\mathrm{eval}},m_i)).
$$

### D2.DEF.011 — P3 common candidate-training preparation

After exact `P_train/M3`, `pi_train`, and `pi_eval` are bound, fit one P3-common candidate-training state over exact `P_train` as imported by `D2.IMP.P3_PREP`. It includes, when applicable, target atomic-reference state, mean-one P3 configuration weights, binary property masks, exact foundation/head identity, target objective and common MACE normalization/model-construction inputs.

For candidate `N`, projection selects the already-fitted rows/state for exact `T_N`. It does not refit E0, renormalize P3 configuration weights, or recompute common model normalization by candidate size. This preparation is P3-specific and is not wholesale P5 method authority after objective semantics diverge.

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

**Profile-selection families.** For each active accepted profile-selection provider, every valid nonconstant scalar selection feature is one required one-dimensional extent-bearing family over provider-valid frames; every represented provider environment-class label creates one required profile hard obligation. If no accepted active profile provider exists, this class is absent.

**Raw pair-geometry families.** For each applicable accepted pair rule, required extent-bearing families are `bond_length_distribution` over minimum pair distance, mean nearest-neighbor distance and maximum nearest-neighbor distance; and `coordination_distribution` over coordination mean and coordination maximum.

**Target-development response families.** Required extent-bearing `force_distribution` contains force-component RMS, mean force norm, maximum force norm and canonical available force-norm quantile channels. Each defined nonconstant accepted channel among energy/atom, instantaneous temperature, hydrostatic strain, deviatoric strain norm, pressure and stress deviatoric norm contributes one scalar required family.

**Foundation-residual families.** Only when the target-size protocol itself uses an authenticated frozen foundation model: one required extent-bearing global family contains absolute energy error/atom, force-component RMSE, mean force-vector error and maximum force-vector error; and one required extent-bearing family per represented species contains component RMSE, mean vector error and maximum vector error. Foundation checkpoint/head/provider identity is selector-evidence identity. Scratch protocols do not acquire foundation families merely because a provider exists elsewhere.

### D2.DEF.013 — Family witness weights with one normalization only

For required family `m`, let nonempty ordered witnesses be `W_m`, current P1 correlation-unit identity be `g(w)`, represented units `G_m`, and witness count in unit `g` be `n_{m,g}`. Define

$$
\widetilde\omega_m(w)=\frac{1}{|G_m|\,n_{m,g(w)}}.
$$

Compute canonical-order binary64 sum

$$
s_m=\sum_{w\in W_m}\widetilde\omega_m(w),
$$

and store

$$
\omega_m(w)=\frac{\widetilde\omega_m(w)}{s_m}.
$$

This is the single and only normalization of the family weight vector. `|G_m|>0`, each `n_{m,g}>0`, and finite positive `s_m` are required.

### D2.DEF.014 — Stable weighted quantile over stored weights

For values `v_i` paired with the stored weights from D2.DEF.013, stable-sort by `(v_i, original_index)`. For `q in [0,1]`, `Q(q)` is the first sorted value whose cumulative **stored** weight is at least `q`.

The stored vector is not normalized again. Its binary64 sum after D2.DEF.013 may differ slightly from one; that finite-precision result is part of the accepted numerical method.

### D2.DEF.015 — Robust scale

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

For family dimension `d_m>=1`,

$$
d_m(a,b)=\sqrt{\frac1{d_m}\sum_{j=1}^{d_m}\left(\frac{x_{a,j}-x_{b,j}}{s_j}\right)^2}.
$$

Only applicable rows participate. A family requires at least two reference elements. Constant optional scalar families are omitted instead of creating zero-information dimensions.

### D2.DEF.017 — Leave-one-out local radius

Let fixed `beta=1/128`. For witness `w`, remove self mass, require `1-omega_m(w)>0`, renormalize remaining weights by `1-omega_m(w)`, stable-sort other witnesses by `(d_m(w,v), canonical_witness_order)`, and choose the smallest distance where cumulative renormalized mass is at least

$$
\beta-10^{-15}.
$$

Failure to reach requested mass is family infeasibility.

### D2.DEF.018 — Exact adjacency

$$
A_m(w,c)=1
\Longleftrightarrow d_m(w,c)\le r_m(w)+10^{-12}\max(1,r_m(w)).
$$

Every witness must have at least one exact candidate support edge. Approximate-neighbor substitution is not equivalent.

### D2.DEF.019 — Multiplicity and covered mass

For selected `S subseteq P_train`,

$$
n_m(w;S)=\sum_{c\in S}A_m(w,c),
$$

$$
C_m(S)=\sum_{w\in W_m}\omega_m(w)\mathbf 1[n_m(w;S)>0].
$$

### D2.DEF.020 — Independent qualification coverage predicate

Family `m` passes direct coverage/MVQUAL qualification iff

$$
C_m(S)+10^{-12}\ge0.95.
$$

The `1e-12` tolerance is not the selector Phase-A tolerance.

### D2.DEF.021 — Extent predicate

For extent coordinate `j`,

$$
L_j=Q_j(0.01),\qquad U_j=Q_j(0.99).
$$

For nonempty applicable selected values `V_j(S)`, extent passes iff

$$
\min V_j(S)\le L_j+10^{-12}
$$

and

$$
\max V_j(S)\ge U_j-10^{-12}.
$$

Empty `V_j(S)` fails. Each side is also one hard obligation of minimum one.

## 5. Canonical hard obligations and FEAS1

### D2.DEF.022 — Source obligation

A source obligation is

$$
o=(L_o,A_o,k_o,s_o),
$$

with D1 semantic locus `L_o`, exact current-`P_train` incidence `A_o`, positive integer minimum `k_o`, and source namespace/provenance `s_o`.

Automatic obligations are, where applicable, every represented P2 condition, recognized represented structural-event type, represented active profile environment class, extent lower side, extent upper side, and represented current P1 correlation interval/unit, each with minimum one. Explicit current hard-support obligations are projected through current P2 condition-attribute authority with declared positive minima.

### D2.DEF.023 — Obligation canonicalization

Source obligations group only when accepted semantic locus is equal. Incidence inside one purported locus must also be exactly equal or construction fails. Incidence equality without locus equality never aliases obligations.

For one locus class `C`,

$$
A_C=A_o\quad(o\in C),
$$

$$
k_C=\max_{o\in C}k_o.
$$

Assign one deterministic canonical identity binding locus, effective minimum, incidence, applicability, provenance and governing policy. Source-ID reuse for different semantics fails closed. Different loci with identical incidence remain distinct.

### D2.DEF.024 — Obligation count and deficit

For canonical obligation `o`,

$$
q_o(S)=|S\cap A_o|,
$$

$$
d_o(S)=\max(0,k_o-q_o(S)),
$$

$$
D_{\mathrm{hard}}(S)=\sum_od_o(S).
$$

The obligation is satisfied iff `q_o(S)>=k_o`.

### D2.DEF.025 — FEAS1 configured horizon

For configured sizes `N_cfg`,

$$
N_{\max}=\max N_{\mathrm{cfg}}.
$$

FEAS1 uses exact `P_train` and the same family/obligation authority to verify domain/self-support consistency, obligation support capacity and conservative lower bounds. A proven lower bound above `N_max` establishes configured-ladder infeasibility. FEAS1 does not create a rescue size or relax the method. Historical support-degree bins `(2,4,8,16,32)`, own-correlation exclusion and fragile-zero-mass tolerance `1e-12` remain diagnostics only.

### D2.AX.001 — Exact sparse representation

NEIGHBOR1/MVIDX may use any exact sparse/file-backed representation provided witness-candidate adjacency, canonical obligation incidence, current correlation-unit codes, canonical family/obligation order and identities equal D2.DEF.018/D2.DEF.023. Persistence layout is non-semantic only under exact representation.

## 6. MVSEL2

### D2.DEF.026 — Selector state

At selected set `S` and available set `P_train minus S`, authoritative state contains the ordered selected prefix, every `n_m(w;S)` and `C_m(S)`, every `q_o(S)`, selected counts `b_g(S)` per current P1 correlation unit, and exact state sufficient to reconstruct representative utility. Lazy heaps, caches, native batches, workers and queue completion order are not scientific state.

### D2.DEF.027 — Candidate gains

For available candidate `c`,

$$
O_c(S)=\{o:q_o(S)<k_o\text{ and }c\in A_o\},
$$

$$
H(c;S)=|O_c(S)|,
$$

$$
G_m(c;S)=\sum_{\substack{w\in W_m\\A_m(w,c)=1\\n_m(w;S)=0}}\omega_m(w),
$$

$$
G(c;S)=\sum_mG_m(c;S),
$$

$$
R(c;S)=\sum_m\sum_{\substack{w\in W_m\\A_m(w,c)=1}}\frac{\omega_m(w)}{n_m(w;S)+1}.
$$

A stronger minimum extends how long one canonical locus stays unsatisfied; it does not multiply hard-gain votes.

### D2.DEF.028 — Sparse diversity

For candidate `c`, define

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

This is the renderer-safe finite-sum form of the accepted nested arithmetic means.

### D2.DEF.029 — Phase-A family-completion predicate

Let fixed selector tolerance be `epsilon_sel=1e-14`. Required family `m` is complete for Phase A iff

$$
C_m(S)\ge0.95-10^{-14}.
$$

Equivalently it keeps Phase A active exactly while

$$
C_m(S)<0.95-10^{-14}.
$$

This is intentionally distinct from D2.DEF.020.

### D2.DEF.030 — Phase-A winner

Phase A is active iff any canonical obligation is unsatisfied or any required family fails D2.DEF.029. Among available candidates filter lexicographically:

1. if any obligation is unsatisfied, maximum integer `H(c;S)`;
2. first canonical family minimizing `C_m(S)/0.95` among families tied within `1e-14` at the minimum;
3. maximum bottleneck-family `G_m(c;S)` within `1e-14`;
4. maximum total `G(c;S)` within `1e-14`;
5. minimum selected count of candidate's own correlation unit;
6. maximum `R(c;S)` within `1e-14`;
7. maximum `D(c;S)` within `1e-14`;
8. minimum stable current UID.

The winner mutates authoritative state exactly once.

### D2.DEF.031 — Phase-B winner

After every obligation is satisfied and every required family passes D2.DEF.029, choose by:

1. maximum current `R(c;S)` within `1e-14`;
2. minimum selected count of candidate's correlation unit;
3. maximum `D(c;S)` within `1e-14`;
4. minimum stable UID.

Selection continues toward a complete permutation subject only to configured-shell REPAIR2.

### D2.DEF.032 — Full-forward oracle

At every rank, recompute exact current D2.DEF.027-028 for every available candidate, apply D2.DEF.030 or D2.DEF.031, determine the unique winner, then mutate state. Every optimized selector must reproduce the same rank sequence under identical authoritative state.

### D2.DEF.033 — Certified-lazy Phase-B equivalence

At required Phase-B rebase compute exact `R_g(c)` for every available candidate and set

$$
B_g(c)=\mathrm{nextafter}(R_g(c),+\infty),
$$

where `nextafter` is the IEEE-754 next binary64 value toward positive infinity. Stale scores are upper bounds only. A refreshed `R` exceeding its prior exact value by more than `5e-13` fails the monotonicity invariant.

Refresh every stale candidate whose bound can enter the inclusive contender region. Certification terminates only when

$$
B_{\max}<R_{\mathrm{best}}-10^{-14}.
$$

At termination every candidate with

$$
R(c;S)\ge R_{\mathrm{best}}-10^{-14}
$$

has an exact current score before correlation-balance/diversity/UID tie dimensions. If certification cannot be proved, rebuild or use D2.DEF.032.

## 7. REPAIR2

### D2.DEF.034 — Configured shell and removal eligibility

For strictly increasing `N_1<...<N_K`, set `N_0=0`; shell `i` contains ranks `[N_{i-1},N_i)`. Only that shell is removable; lower ranks are immutable.

For selected candidate `c`, unique covered mass is total family reference mass of witnesses currently covered only by `c`. `c` is removable iff unique mass `<=1e-14` and removal increases no canonical obligation deficit. Order removable candidates by representative loss ascending, removed candidate correlation-unit selected count descending, then removed UID ascending; retain at most 64.

### D2.DEF.035 — Replacement frontier

For contemplated removal evaluate replacements against immutable pre-swap state by:

1. maximum hard gain when obligations remain pending;
2. first canonical bottleneck family;
3. maximum bottleneck-family new coverage;
4. maximum total new coverage;
5. minimum hypothetical correlation-unit count after removal;
6. maximum representative gain after removal;
7. maximum sparse diversity after removal;
8. minimum replacement UID.

Floating contender comparisons use `1e-14` unless a distinct fixed predicate already applies.

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

Comparison minimizes component 1, maximizes components 2-4 with `1e-14` floating tolerance, then maximizes exact integer component 5. A swap is admissible only if it strictly improves `J` and every required family satisfies

$$
C_m(S_{\mathrm{after}})+10^{-14}\ge C_m(S_{\mathrm{before}}).
$$

Objective-equivalent admissible proposals use ascending `(representative_loss, removed_rank, removed_UID, replacement_UID)`.

### D2.DEF.037 — Repair limits, rank inheritance, and terminal-shell rule

Per configured shell: at most 2 passes, 32 accepted swaps, and removal shortlist 64.

An accepted replacement inherits the removed rank. If that replacement already appears at a future rank, move the removed candidate to that future rank. The master permutation is preserved and every earlier configured prefix remains immutable.

After the final configured shell, continue the same exact optimized MVSEL2 method until every `P_train` frame is ordered. There is no extra repair shell and no UID-only, condition-round-robin, scalar-only, or alternate-selector suffix.

### D2.AX.002 — Post-repair reconstruction

After an accepted swap, every prefix-derived lazy/frontier/marginal/cache/checkpoint/journal state from the pre-swap prefix is stale. Reconstruct exact forward state from authenticated primitive family/obligation/correlation evidence and exact repaired prefix; Phase-B continuation performs an exact all-candidate rebase. A zero-swap shell may retain authentic state whose exact prefix identity is unchanged.

## 8. Independent MVQUAL and automatic-screen admission

### D2.DEF.038 — Independent configured-prefix qualification

For configured `N`, let `T_N` be exact repaired prefix. Independently recompute from immutable TargetCoverageReference and canonical obligations:

- direct `C_m(T_N)` using D2.DEF.016-019 and D2.DEF.020;
- required extent predicates under D2.DEF.021;
- every `q_o(T_N)` under D2.DEF.024;
- required training-label usability.

MVIDX may be an exact secondary cross-check but selector/repair counters are not the sole oracle. Direct family mass and MVIDX family mass must agree with `rtol=0`, `atol=5e-12`; disagreement is invariant failure.

Prefix qualifies iff every required predicate passes. Under fixed nested prefixes/evidence, configured qualification must have form `FAIL* -> PASS*`; `PASS -> FAIL` fails closed. MVQUAL does not rank qualified sizes.

### D2.DEF.039 — Automatic-screen admission

Define

$$
Q_{\mathrm{cfg}}=\{N\in N_{\mathrm{cfg}}:T_N\text{ passes D2.DEF.038}\}.
$$

Automatic P3 screening is defined only when

$$
|Q_{\mathrm{cfg}}|\ge3.
$$

Fewer qualified configured candidates yield `INSUFFICIENT_AUTOMATIC_COMPARISON`; no ladder alteration, rescue size, or membership repair is implied.

## 9. Atomic-reference fitting and composition identifiability

### D2.DEF.040 — Composition matrix

For exact authorized fit membership `D` and atomic-species basis `(z_1,...,z_p)`, define count matrix `C` by atom counts and total-energy vector `y`; element order is atomic-number order.

### D2.DEF.041 — Foundation-residual fit

For exact selected foundation identity `Phi`, let `y_fnd` be predicted total energy on `D`, `e_fnd(Phi)` its head-local elemental reference vector, and `r=y-y_fnd`. With accepted regularization/anchor tuple `(lambda,delta e_prior)`, solve

$$
\widehat{\delta e}=\arg\min_{\delta e}\left(\|C\delta e-r\|_2^2+\lambda\|\delta e-\delta e_{\mathrm{prior}}\|_2^2\right).
$$

Then

$$
e_{\mathrm{target}}(\Phi)=e_{\mathrm{fnd}}(\Phi)+\widehat{\delta e}.
$$

CV uses exact fold gradient membership; final production uses exact complete `T_selected`. Monitor and held-out labels are excluded.

### D2.DEF.042 — Free null space and composition transfer

Let `N_free` be directions unconstrained by authorized composition equations and accepted anchors; without an anchor, `N_free=ker(C)` under accepted numerical-rank rule. Required composition vector `c` is transfer-feasible iff

$$
c^Tv=0\quad\text{for every }v\in N_{\mathrm{free}}.
$$

Rank tolerance may classify numerical rank but cannot create absent information. Rank, singular values, null-space evidence, residual diagnostics, anchor identity and required-composition checks remain bound to fit lineage.

## 10. Foundation-P5 robust objective

### D2.DEF.043 — Scalar Huber function

For `delta>0`,

$$
h_\delta(x)=\begin{cases}
\frac12x^2,&|x|\le\delta,\\
\delta\left(|x|-\frac12\delta\right),&|x|>\delta.
\end{cases}
$$

### D2.DEF.044 — Dimensional robust thresholds

Fixed current dimensional thresholds are

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
\delta_F(f)=\delta_{F,0}\times\begin{cases}
1.0,&f<100,\\
0.7,&100\le f<200,\\
0.4,&200\le f<300,\\
0.1,&f\ge300.
\end{cases}
$$

### D2.DEF.045 — Property reductions and total objective

For configuration `i` with binary property masks, total-energy residual `Delta E_i`, Cartesian force residuals and full `3x3` Cartesian stress residuals:

- `L_E` is arithmetic mean over configurations of `h_deltaE(m_i^E Delta E_i/n_i)`;
- `L_F` is arithmetic mean over all stored Cartesian force components after binary force masking, using per-atom D2.DEF.044 threshold;
- `L_S` is arithmetic mean over all nine stored Cartesian stress entries per admitted configuration of `h_deltaS(m_i^S Delta sigma_iab)`.

The nine-entry stress reduction counts symmetric off-diagonal entries twice. A six-component Voigt reduction is different.

Current foundation-P5 objective is

$$
L_{P5}=L_E+10L_F+L_S.
$$

No independent per-configuration scalar and no target/replay training-head scalar occur. A dependency transport field must be neutral if present. A phase-dependent loss family/threshold/coefficient mutation is another method unless separately accepted.

## 11. P3 optimizer normalization, estimator, reducer, and restart

### D2.DEF.046 — Updates per nominal epoch and normalization

For target size `N>0`, batch size `B>0`, and retained final partial target batch,

$$
U_N=\left\lceil\frac NB\right\rceil.
$$

For reference size `N_ref`, `U_ref=ceil(N_ref/B)`, define

$$
s_N=\frac{U_{\mathrm{ref}}}{U_N},
$$

$$
LR_N=LR_{\mathrm{ref}}s_N,
$$

$$
beta_N=beta_{\mathrm{ref}}^{s_N}.
$$

This preserves first-order per-epoch LR and EMA products but is not a theorem of optimizer-path equivalence. Values are fixed from full candidate geometry and do not rescale after survivor reduction. A runtime realizing `floor(N/B)` target updates is a different P3 experiment.

### D2.DEF.047 — P3 target-force estimator and complete-seed score

For `K>0` admitted Cartesian force components,

$$
E_{N,s}=1000\sqrt{\frac1K\sum_{k=1}^{K}(\widehat F_k-F_k)^2}
$$

in `meV/angstrom`. Non-finite prediction/metric is typed failure, not `+infinity` substitution.

For configured ordered seed set `S_seed`, candidate score exists only if every required seed has valid finite metric:

$$
\overline E_N=\frac1{|S_{\mathrm{seed}}|}\sum_{s\in S_{\mathrm{seed}}}E_{N,s}.
$$

No successful-subset mean exists.

### D2.DEF.048 — Practical-equivalence ranking

For active successful set `A`, define

$$
E_{\min}=\min_{N\in A}\overline E_N,
$$

$$
E_{\mathrm{eq}}=\{N\in A:\overline E_N\le E_{\min}+\epsilon\}.
$$

Choose smallest `N` in `E_eq`, remove it, and repeat until ordered. Only the accepted tiny fixed floating comparison guard may supplement scientific `epsilon`; backend failure cannot justify widening it.

### D2.DEF.049 — Structural funnel and success sufficiency

Let `q=|Q_cfg|>=3`. The structural funnel is

$$
q\rightarrow\min(q,4)\rightarrow2\rightarrow1.
$$

At first boundary, successful candidates must number at least `min(|A_1|,4)`; D2.DEF.048 ranks them and first `min(q,4)` survive. At second and terminal comparisons, at least two successful candidates are required before comparison; otherwise return `INSUFFICIENT_COMPARISON`. The second comparison retains first two. Fidelity epochs and evaluation sizes are the three configured positions of D2.DEF.007, not encoded in funnel name.

### D2.DEF.050 — Configured-ceiling terminal rule

If configured maximum `N_max` is a successful terminal finalist and

$$
\overline E_{N_{\max}}+\epsilon<\overline E_N
$$

for every other successful terminal finalist, recommend `N_max` and record explicit nonconvergence-at-configured-ceiling evidence. Otherwise recommend the first D2.DEF.048-ranked terminal finalist. The reducer never extrapolates or invents an unconfigured rescue size.

### D2.AX.003 — Continuous trajectory and authenticated restart

Each active `(N,seed)` is one continuous trajectory through configured fidelity boundaries. Model, optimizer, EMA when enabled, learning-rate state and accepted Python/NumPy/Torch RNG lineage restore from authenticated predecessor state. Unaccepted scratch is not continuation authority. Restart cannot change membership, D2.DEF.011 common preparation, normalization, seed or boundary identity.

## 12. Replay label modes and P5 exposure

### D2.DEF.051 — Replay geometry and label-mode concretization

Let `D_r^geom` be authenticated prepared replay geometry/source membership and split. Label mode is exactly

```text
TRUE_REFERENCE
FOUNDATION_PSEUDO
```

with `TRUE_REFERENCE` canonical default when true labels are available and `FOUNDATION_PSEUDO` requiring explicit opt-in plus exact frozen `Phi`.

Define labeled replay corpus

$$
D_r(\ell)=\{(x,y_\ell(x)):x\in D_r^{\mathrm{geom}}\}.
$$

For `TRUE_REFERENCE`, `y_l` is canonical true-reference/DFT label. For `FOUNDATION_PSEUDO`, `y_l` is generated by exact frozen `Phi` under accepted prediction policy. Changing `ell` over the same authenticated prepared source/split must leave `D_r^geom` unchanged.

Pseudo replay never supplies its own retention evidence: a distinct authenticated true-reference replay monitor remains mandatory.

### D2.DEF.052 — Replay lineage identity

Replay lineage binds replay geometry/source membership and split, label mode, true-reference monitor identity, foundation/head identity where applicable, replay/pretraining-head E0 identity, prediction policy and realized exposure. A changed component invalidates dependent P5 evidence rather than being reinterpreted in place.

### D2.DEF.053 — Combined corpus order and update geometry

For current two-head replay, with labeled replay corpus `D_r` and target corpus `D_t`, pre-shuffle order is

$$
D_{\mathrm{train}}=D_r\Vert D_t.
$$

A fixed seed shuffles integer indices of this ordered tuple. Reversing corpus blocks changes the seed-to-example trajectory. There is no target/replay balancing sampler or intentional target duplication. For naive fine tuning, replay corpus is empty.

For current qualified single-process non-LBFGS foundation-P5 path with batch size `B`,

$$
U=\left\lfloor\frac{|D_r|+|D_t|}{B}\right\rfloor
$$

and `drop_last=true`; exactly `UB` examples from each seeded shuffled permutation are consumed. Distributed execution is not presumed equivalent without required qualification of global reductions, exposure and optimizer trajectory.

## 13. Common target monitor and post-selection folds

### D2.DEF.054 — Monitor parent and quota order

Let usable protected `OUTER_MONITOR` parent be `P_mon`; required cardinality is fixed `256`, so `|P_mon|<256` is infeasible. Each parent frame belongs to stratum `<condition_id>:<run_id>` and is ordered inside stratum by `(source_frame_index, frame_uid)`.

With fixed seed `q=161803`, each nonempty stratum key `s` receives lowercase SHA-256 hex marker of UTF-8 bytes

```text
<q>\0quota\0<s>
```

with `q` decimal. Sort strata by `(marker,s)`. Initialize quotas zero and repeatedly sweep this order, incrementing a stratum whose quota is below capacity, until exactly 256 slots are allocated.

### D2.DEF.055 — Monitor systematic positions

For stratum capacity `n`, quota `k`, `1<=k<=n`, namespace `target:<s>`, hash UTF-8 `<q>\0<namespace>`, take first eight digest bytes as unsigned big-endian integer `I`, define

$$
u=\frac{I+0.5}{2^{64}},
$$

$$
p_j=\min\left(n-1,\left\lfloor\frac{(j+u)n}{k}\right\rfloor\right),\qquad j=0,\ldots,k-1.
$$

Positions must be distinct or construction fails. Parent identity, exact selected membership, cardinality, seed, strategy and per-stratum availability/selection define monitor identity.

### D2.DEF.056 — Component fold order and purge

For exact frozen `T_N`, let sorted protected-component identities be `C_comp`, fold count `K>=2`, partition seed `s_cv`, algorithm identity `a`, and selected-membership digest `d_T`. If `|C_comp|<K`, CV is infeasible.

For component `c`, set `salt=<a>|<d_T>` and marker to SHA-256 hex of UTF-8 `<salt>|<s_cv>|<c>`. Sort by `(marker,c)`; ordered position `j` is held out in fold `j mod K`.

For fold `i`, let `O_i` be held-out components and `R_i` lexicographically sorted remaining components. With configured nonnegative `p_cfg`,

$$
p_i=\min\left(p_{\mathrm{cfg}},\max(0,|R_i|-2)\right).
$$

If zero, purge is empty. If one, choose middle index. If greater than one, set `h=(|R_i|-1)/(p_i-1)`, propose nearest-integer ties-to-even indices `round_even(jh)`, deduplicate, append lowest unselected indices until `p_i` distinct positions exist, then sort. Gradient components are complement of held-out and purge. `M_mon` is external.

## 14. Checkpoint predicates, CV acceptance, and production

### D2.DEF.057 — Shared checkpoint constraint

For checkpoint `c`, `S(c)` is conjunction of shared mandatory constraints imported from `D2.IMP.CV`: finite required metrics; replay degradation within accepted budget using authenticated true-reference replay-monitor evidence where replay is active; and required physical/integrity gates. Pseudo replay labels cannot satisfy the true-reference retention conjunct.

### D2.DEF.058 — Role-effective checkpoint predicate

Let `r_mon(c)` be target force-component RMSE on exact `M_mon` in `eV/angstrom`. For role `rho` with resolved target ceiling `tau_rho`,

$$
A_\rho(c)=S(c)\wedge r_{\mathrm{mon}}(c)\le\tau_\rho.
$$

Foundation CV uses `tau_CV`; fresh production uses `tau_prod`. Boundaries are inclusive in binary64 against binary64 nearest the resolved decimal ceiling: exact equality passes and next representable binary64 above fails.

### D2.DEF.059 — CV outer predicate and all-position acceptance

For configured outer metric and `theta_CV`, frozen fold representative passes iff exact held-out metric on `O_i` is finite and `<=theta_CV`. Alternative outer metrics retain own units/threshold and never supply `tau_CV`.

For finite required `(fold,seed)` set `P_req`, CV accepts iff every position completed frozen method/horizon, has nonempty admissible checkpoint set under D2.DEF.058, freezes one representative by accepted target-side ranking rule, and that representative passes the outer predicate. No averaging, majority, best-seed or dispersion rescue exists.

### D2.AX.004 — Role currentness and selective invalidation

Changing `tau_CV` or `theta_CV` stales dependent CV acceptance and production authorization derived from it while leaving `tau_prod` and shared method unchanged. Changing `tau_prod` stales production role evidence only. Changing shared `S` can stale both. Re-thresholding historical classifications does not create current evidence.

### D2.AX.005 — Fresh production

Fresh production starts a new model/optimizer lineage on exact complete `T_selected`, fits target-dependent training state there only, uses same `M_mon` and shared checkpoint mechanics as CV, and applies production predicate with `tau_prod`. P3 `M3` has no production checkpoint role. Where replay is active, D2.DEF.051-053 plus true-reference retention remain binding.

## 15. Continuation, precision, equivalence, and failure

### D2.DEF.060 — Authenticated continuation state

Continuation is admissible only when it binds every identity needed to prove the exact run boundary: governed population/membership, method/policy parameters, foundation/head, objective/exposure, selector/reference identities where applicable, optimizer/EMA/RNG state and exact accepted predecessor boundary. Uncommitted scratch is not continuation authority.

### D2.DEF.061 — Numerical equivalence relation

For optimized implementation `A`, accepted reference owner `R`, and declared authoritative output set `O`,

$$
A\equiv_O R
$$

iff throughout declared validity domain they produce every output/decision in `O` under the exact equality/tolerance owned by that object. `O` may require exact selector rank/repair-trace identity or a separately governed metric tolerance. Performance does not establish equivalence.

### D2.AX.006 — Execution noninterference

Worker count, queue completion order, block/chunk size, mmap layout, cache residence, native backend, device batching and restart route are execution-only exactly when they preserve all governed D2 outputs under D2.DEF.061. Otherwise they are method-affecting and require D2 review.

### D2.DEF.062 — Typed failure set

Fail closed rather than choose a semantic fallback for non-finite required fitted statistics; invalid/empty required family mass; unreachable exact `M3`; malformed structural policy; unsupported family/provider state; zero leave-one-out denominator; unreachable local mass; missing witness support; impossible hard obligation; configured-ladder infeasibility; stale lazy certification; repair invariant failure; direct/MVIDX disagreement beyond fixed tolerance; non-identifiable E0 transfer; pseudo replay without exact `Phi` or true-reference monitor; invalid replay lineage; impossible 256-frame monitor; insufficient fold components; missing required fold/seed; no admissible checkpoint; non-finite P3 outcome; insufficient reducer comparison; stale/mismatched continuation; or materially different objective/exposure/method.

Tolerance widening, support relaxation, role substitution, pseudo-label fallback or rescue-size invention are not error handlers.

## 16. Parameter-binding ledger

| Coordinate | Binding class | Current value/domain |
| --- | --- | --- |
| family hard coverage | `FIXED_METHOD_COORDINATE` | `0.95` |
| extent quantiles | `FIXED_METHOD_COORDINATE` | `0.01, 0.99` |
| family-weight normalization count | `FIXED_METHOD_COORDINATE` | exactly once |
| robust-scale floor/branch threshold | `FIXED_METHOD_COORDINATE` | `1e-12` |
| local-radius mass `beta` | `FIXED_METHOD_COORDINATE` | `1/128` |
| local-radius cumulative guard | `FIXED_METHOD_COORDINATE` | `1e-15` |
| adjacency tolerance | `FIXED_METHOD_COORDINATE` | `1e-12*max(1,r)` |
| qualification coverage tolerance | `FIXED_METHOD_COORDINATE` | `1e-12` |
| MVSEL2 contender/completion tolerance | `FIXED_METHOD_COORDINATE` | `1e-14` |
| lazy monotonicity guard | `FIXED_METHOD_COORDINATE` | `5e-13` |
| REPAIR2 tolerance/limits | `FIXED_METHOD_COORDINATE` | `1e-14`, 2 passes, 32 swaps, shortlist 64 |
| direct-vs-MVIDX mass agreement | `FIXED_METHOD_COORDINATE` | `rtol=0`, `atol=5e-12` |
| candidate/evaluation/fidelity/seed values | `CONFIGURABLE_FAMILY` | D2.DEF.007 structural domain |
| practical `epsilon` | `CONFIGURABLE_FAMILY` | finite positive response-unit value |
| P5 Huber thresholds/factors | `FIXED_METHOD_COORDINATE` | D2.DEF.044 |
| foundation-P5 coefficients | `FIXED_METHOD_COORDINATE` | `1:10:1` |
| replay label mode | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | true-reference default; pseudo explicit opt-in |
| P5 corpus order | `FIXED_METHOD_COORDINATE` | replay then target |
| P5 partial-batch policy | `FIXED_METHOD_COORDINATE` | `drop_last=true` |
| common monitor cardinality/seed | `FIXED_METHOD_COORDINATE` | `256`, `161803` |
| CV fold count | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | integer `K>=2`, default `3` |
| `tau_CV`, `theta_CV`, `tau_prod` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | D1 positive families, current defaults `45/45/30 meV/angstrom` for default force metric |

## 17. R2 verification and falsification oracles

Fresh R2 review must attempt at least:

1. one-normalization adversary: two represented correlation units with 37 and 2 witnesses; after D2.DEF.013 stored weight sum is `1.0000000000000002`, cumulative after witness index 36 is `0.5000000000000006`, and `Q(0.5)` selects index 36; a second normalization selecting index 37 is nonconformant;
2. selector-completion fixture in the interval between `0.95-1e-12` and `0.95-1e-14`, proving D2.DEF.020 and D2.DEF.029 are distinct;
3. exact component order + first-predecessor `M3` membership;
4. condition-balanced `pi_eval` with and without priority evidence;
5. structural-policy rejection of non-power-of-two sizes, wrong evaluation count, non-increasing horizons, duplicate/negative seeds;
6. candidate-dependent-refit counterexample for D2.DEF.011;
7. fewer-than-three-qualified automatic-screen rejection;
8. exact `q -> min(q,4) -> 2 -> 1` funnel, success-sufficiency failures and configured-ceiling cases;
9. autocorrelation/truncation/block/event fixtures from accepted sampling semantics;
10. required-family applicability fixtures for universal/profile/pair/response/foundation modes;
11. direct dense/reference adjacency at metric boundaries;
12. full-forward vs optimized/lazy MVSEL2 rank equality at every rank;
13. Phase-A first-canonical bottleneck and hard-obligation priority under `1e-14` ties;
14. REPAIR2 replacement-frontier/scalar-optimized proposal and swap-trace equality; 2-pass/32-swap/64-shortlist limits; rank inheritance/future displacement; lower-prefix immutability; no-extra-shell continuation;
15. direct TargetCoverage vs MVIDX mass equality and MVQUAL monotonicity;
16. selected-head E0 null-space transfer counterexamples;
17. robust P5 dimensional thresholds, nine-entry stress, masks and no-config/head-scalar checks;
18. true-reference replay default and pseudo-label opt-in proving identical replay geometry, frozen-`Phi` pseudo labels and separate true-reference retention;
19. replay-first/target-second seeded exposure and `drop_last=true` geometry;
20. deterministic monitor and fold/purge reconstruction;
21. inclusive role-threshold boundaries and selective invalidation;
22. worker/backend/chunk/cache/restart invariance of governed outputs.

## 18. D2 -> D3 handoff and acceptance condition

D3 owns persistence, concurrency, resource admission, software decomposition, dependency adaptation, build topology and durable restart representation. It may consolidate or simplify execution but may not create another numerical owner, weaken fail-closed predicates, encode configurable defaults as universal constants, or change accepted membership/replay/exposure semantics.

Fresh independent R2 review must demonstrate lossless equivalence to accepted basis, exact resolution of R1 B1-B8, exact source availability for every specialized prerequisite, definition-before-substantive-use closure, acyclic direct dependency trace, and renderer-safe formulas. Any changed floating association that changes a reference result, threshold/tolerance, failure classification, family/applicability set, stochastic exposure, or replay lineage is a semantic change requiring adjudication rather than editorial acceptance.
