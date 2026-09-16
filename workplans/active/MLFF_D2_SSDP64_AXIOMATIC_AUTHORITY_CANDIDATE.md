---
kind: proposed-D2-authority-overlay
protocol_version: 6.4.0
status: PROPOSED_AWAITING_INDEPENDENT_REVIEW_AND_STAKEHOLDER_RATIFICATION
workplan_id: MLFF-D1-D2-SSDP64-AXIOMATIC-FORMALIZATION-1
basis_commit: cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824
parent_D1_candidate: workplans/active/MLFF_D1_SSDP64_AXIOMATIC_AUTHORITY_CANDIDATE.md
would_compose_with:
  - docs/methods/mlff_numerical_algorithmic_method.md
  - docs/methods/mlff_target_training_order_numerical_algorithmic_method.md
---

# Proposed MLFF D2 formal numerical authority kernel

## 1. Authority and numerical interpretation

This file is the proposed Protocol-6.4 D2 formalization overlay for the accepted MLFF numerical authority at basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824`. It concretizes the D1 candidate without changing accepted numerical outputs. It is not accepted-current authority until fresh independent review and stakeholder ratification of the exact D1/D2 pair.

The current general and scoped D2 method papers remain explanatory/provenance/context owners unless this overlay explicitly replaces an imprecise expression with an equivalent formal definition. A material conflict is a review blocker, not a license to choose the candidate silently.

Unless stated otherwise:

- scientific scalar decision arithmetic is IEEE-754 binary64;
- exact counts/indices are integers with enough range for the governed population;
- canonical order means the accepted deterministic identity order for that object;
- tolerances are part of the numerical method, not suggestions to implementations;
- empty-set/zero-denominator cases are defined explicitly or fail closed;
- an optimized path is equivalent only when it reproduces the reference decision/output required by the owning definition.

## 2. Exact population and prefix objects

### D2.DEF.001 — Canonical finite population

For a governed population with `n` frames, write

$$
P=(u_0,u_1,\ldots,u_{n-1})
$$

for its canonical ordered tuple. Set membership and tuple order are distinct: identity-sensitive algorithms may consume the tuple order even when a scientific predicate depends only on the set.

### D2.DEF.002 — Exact component-preserving `M3` split

Let protected components of `U_size` be ordered by the accepted D2 component-order rule and have positive integer weights `w_1,...,w_C`. For configured reserve cardinality `m_3`, define reachable totals recursively by

$$
R_0=\{0\},
$$

$$
R_j=R_{j-1}\cup\{r+w_j:r\in R_{j-1},\ r+w_j\le m_3\}.
$$

The accepted implementation iterates components in canonical order and previous reachable totals in descending order, records only the first predecessor creating each new total, stops when `m_3` first becomes reachable, and reconstructs that predecessor chain. If `m_3` is unreachable, the split is infeasible. `M3` is the selected component union; `P_train` is its canonical-order complement.

The predecessor/tie semantics are part of exact membership identity.

### D2.DEF.003 — Exact prefix function

For ordered tuple `pi=(v_1,...,v_n)` and integer `N` with `0<=N<=n`,

$$
\mathrm{prefix}(\pi,N)=(v_1,\ldots,v_N).
$$

When membership rather than order is consumed, `set(prefix(pi,N))` is the selected set. A stored cardinality without the parent-order identity is insufficient to reconstruct membership.

## 3. TargetCoverageReference

### D2.DEF.004 — Family witness weights

For required family `m`, let `W_m` be its nonempty ordered witness set, `g(w)` the current P1 correlation-unit identity, `G_m={g(w):w in W_m}`, and

$$
n_{m,g}=|\{w\in W_m:g(w)=g\}|.
$$

Before final normalization define

$$
\widetilde\omega_m(w)=\frac{1}{|G_m|\,n_{m,g(w)}}.
$$

Let `s_m` be the binary64 canonical-order sum of these values. The stored weight is

$$
\omega_m(w)=\frac{\widetilde\omega_m(w)}{s_m}.
$$

Requirements: `|G_m|>0`, every `n_{m,g}>0`, `s_m` finite and positive. Otherwise the family is invalid. The normalization makes the stored binary64 vector authoritative even if the exact algebraic preweights sum to one analytically.

### D2.DEF.005 — Stable weighted quantile

For finite values `v_1,...,v_n` and nonnegative finite normalized weights `omega_i` with positive total, stable-sort indices by `(v_i, original_index)`. After normalizing weights by their binary64 sum, define for `q in [0,1]`

$$
Q(q)=v_{i_j},
$$

where `j` is the least sorted position whose cumulative normalized weight is at least `q`. This definition owns selector weighted quantiles unless a narrower accepted owner states otherwise.

### D2.DEF.006 — Robust feature scale

For family coordinate `j`, let

$$
a_j=Q_j(0.75)-Q_j(0.25),
$$

$$
b_j=Q_j(0.99)-Q_j(0.01).
$$

With `delta_s=10^{-12}`, define

$$
s_j=
\begin{cases}
a_j,&a_j>\delta_s,\\
b_j,&a_j\le\delta_s\text{ and }b_j>\delta_s,\\
\max(\sigma_{\mathrm{pop},j},1),&\text{otherwise},
\end{cases}
$$

followed by `s_j=max(s_j,delta_s)`. Here `sigma_pop,j` is the binary64 population standard deviation over applicable family values. Non-finite inputs fail preparation.

### D2.DEF.007 — Family metric

For a `d_m`-coordinate family with `d_m>=1`,

$$
d_m(a,b)=
\sqrt{\frac{1}{d_m}\sum_{j=1}^{d_m}
\left(\frac{x_{a,j}-x_{b,j}}{s_j}\right)^2}.
$$

Only rows applicable to family `m` participate.

### D2.DEF.008 — Leave-one-out local radius

Let `beta=1/128`. For witness `w`, remove its self mass, require `1-omega_m(w)>0`, renormalize every other witness weight by that quantity, stable-sort other witnesses by `(d_m(w,v), canonical_witness_order)`, and define `r_m(w)` as the smallest distance at which cumulative renormalized weight is at least

$$
\beta-10^{-15}.
$$

Failure to reach this mass is family infeasibility.

### D2.DEF.009 — Exact adjacency

For witness `w` and candidate `c`, define

$$
A_m(w,c)=
\begin{cases}
1,&d_m(w,c)\le r_m(w)+10^{-12}\max(1,r_m(w)),\\
0,&\text{otherwise}.
\end{cases}
$$

Every witness must have at least one candidate with `A_m(w,c)=1`; otherwise preparation fails. Approximate nearest-neighbor substitution is not equivalent authority.

### D2.DEF.010 — Multiplicity and covered mass

For selected set `S subseteq P_train`,

$$
n_m(w;S)=\sum_{c\in S}A_m(w,c),
$$

$$
C_m(S)=\sum_{w\in W_m}\omega_m(w)\,\mathbf 1[n_m(w;S)>0].
$$

The current family hard-coverage predicate is

$$
C_m(S)+10^{-12}\ge0.95.
$$

The `10^-12` here is the qualification comparison tolerance; it is distinct from selector contender tolerances below.

### D2.DEF.011 — Extent predicate

For scalar extent coordinate `j`, let `L_j=Q_j(0.01)` and `U_j=Q_j(0.99)`. Let `V_j(S)` be applicable selected values. If `V_j(S)` is empty, extent support fails. Otherwise it passes iff

$$
\min V_j(S)\le L_j+10^{-12}
$$

and

$$
\max V_j(S)\ge U_j-10^{-12}.
$$

Each side also contributes one hard-support obligation of minimum one in the current method.

## 4. Canonical hard obligations

### D2.DEF.012 — Source obligation

A source obligation is

$$
o=(L_o,A_o,k_o,s_o),
$$

where `L_o` is D1 semantic locus, `A_o subseteq P_train` is exact incidence, `k_o` is a positive integer, and `s_o` is provenance/source-namespace identity.

### D2.DEF.013 — Canonicalization relation

For source obligations `o_1,o_2`, define

$$
o_1\equiv_L o_2
$$

iff their accepted semantic loci are equal. Within each equivalence class, exact incidences must also be equal; otherwise canonicalization fails closed. Incidence equality without locus equality never implies `equiv_L`.

For class `C`, define

$$
A_C=A_o\quad(o\in C),
$$

$$
k_C=\max_{o\in C}k_o.
$$

The canonical obligation set contains one deterministic identity-bound record per class; aliases and source minima remain provenance only.

### D2.DEF.014 — Obligation count and deficit

For canonical obligation `o` and selected set `S`,

$$
q_o(S)=|S\cap A_o|,
$$

$$
d_o(S)=\max(0,k_o-q_o(S)).
$$

The obligation is satisfied iff `q_o(S)>=k_o`.

Total hard deficit is

$$
D_{\mathrm{hard}}(S)=\sum_{o\in O_{\mathrm{canonical}}}d_o(S).
$$

## 5. FEAS1 and sparse incidence authority

### D2.DEF.015 — Configured feasibility horizon

For nonempty configured candidate-size set `N_cfg`,

$$
N_{\max}=\max N_{\mathrm{cfg}}.
$$

FEAS1 may prove that no configured candidate can satisfy accepted hard support/coverage. Such proof returns configured-ladder infeasibility. It never creates an unconfigured rescue size or weakens a predicate.

### D2.AX.001 — Exact sparse representation axiom

MVIDX/NEIGHBOR1 may use any exact sparse/file-backed representation, but its witness-candidate adjacency, obligation-candidate incidence, correlation-unit codes, and canonical identity must equal the definitions above. Storage dtype/layout is non-semantic only under exact representation.

## 6. MVSEL2 reference state and candidate primitives

### D2.DEF.016 — Selector state

At selected set `S` and available set `P_train\S`, authoritative selector state consists of:

- ordered selected prefix;
- every `n_m(w;S)` and `C_m(S)`;
- every `q_o(S)`;
- selected counts `b_g(S)` per current P1 correlation unit `g`;
- exact quantities sufficient to reconstruct representative utility.

Lazy heaps, cached marginals, native batches, queue order, and worker state are not scientific state.

### D2.DEF.017 — Candidate hard gain

For available candidate `c`, define the unsatisfied-obligation support set

$$
O_c(S)=\{o:q_o(S)<k_o\text{ and }c\in A_o\}.
$$

Then

$$
H(c;S)=|O_c(S)|.
$$

A stronger `k_o` extends how long one locus remains unsatisfied; it does not multiply its hard-gain vote.

### D2.DEF.018 — Candidate new-coverage gains

For family `m`,

$$
G_m(c;S)=
\sum_{\substack{w\in W_m\\A_m(w,c)=1\\n_m(w;S)=0}}
\omega_m(w),
$$

and

$$
G(c;S)=\sum_m G_m(c;S).
$$

### D2.DEF.019 — Representative gain

Define

$$
R(c;S)=
\sum_m\sum_{\substack{w\in W_m\\A_m(w,c)=1}}
\frac{\omega_m(w)}{n_m(w;S)+1}.
$$

The denominator is always positive.

### D2.DEF.020 — Sparse diversity

For available `c`, define family-neighborhood witness set

$$
W_m(c)=\{w\in W_m:A_m(w,c)=1\},
$$

and active family set

$$
M(c)=\{m:|W_m(c)|>0\}.
$$

If `M(c)` is empty, define `D(c;S)=0`. Otherwise define the exact nested arithmetic mean

$$
D(c;S)=
\frac{1}{|M(c)|}
\sum_{m\in M(c)}
\left[
\frac{1}{|W_m(c)|}
\sum_{w\in W_m(c)}
\frac{1}{n_m(w;S)+1}
\right].
$$

This is the renderer-safe exact replacement for the previous nested `operatorname{mean}` notation; it changes no numerical semantics.

## 7. MVSEL2 selection relation

Let `epsilon_sel=10^-14`.

### D2.DEF.021 — Phase-A predicate

Phase A is active iff at least one canonical hard obligation is unsatisfied or at least one required family fails its current coverage predicate under selector tolerance.

### D2.DEF.022 — Phase-A winner

Among available candidates, choose by the following lexicographic filtering relation:

1. if any obligation is unsatisfied, retain candidates with maximum integer `H(c;S)`;
2. find the first canonical family minimizing `C_m(S)/0.95` among families tied within `epsilon_sel` at the minimum;
3. retain maximum bottleneck-family `G_m(c;S)` within `epsilon_sel`;
4. retain maximum `G(c;S)` within `epsilon_sel`;
5. retain minimum current selected count of the candidate's own correlation unit;
6. retain maximum `R(c;S)` within `epsilon_sel`;
7. retain maximum `D(c;S)` within `epsilon_sel`;
8. choose minimum stable current frame UID.

The winner mutates authoritative state exactly once.

### D2.DEF.023 — Phase-B winner

Once every obligation and hard family threshold is satisfied, choose by:

1. maximum current `R(c;S)` within `epsilon_sel`;
2. minimum selected count of the candidate's correlation unit;
3. maximum `D(c;S)` within `epsilon_sel`;
4. minimum stable UID.

Selection continues to a complete permutation, subject only to accepted configured-shell repair.

### D2.DEF.024 — Full-forward oracle

The reference algorithm recomputes exact current candidate primitives for every available candidate at every rank, applies D2.DEF.022 or D2.DEF.023, and mutates only after the unique winner is determined. Any optimized implementation is accepted only if every selected rank equals this oracle for identical authoritative state.

### D2.DEF.025 — Certified-lazy Phase-B equivalence

At a required rebase, compute exact `R_g(c)` for every available candidate and set the conservative binary64 upper bound

$$
B_g(c)=\mathrm{nextafter}(R_g(c),+\infty),
$$

where `nextafter` denotes the IEEE-754 next representable binary64 value toward positive infinity.

A stale score is never treated as current. If a refreshed `R` exceeds its earlier exact score by more than `5*10^-13`, fail the monotonicity invariant. Certification may terminate only when every candidate whose bound can enter the inclusive contender region has been refreshed and

$$
B_{\max}<R_{\mathrm{best}}-10^{-14}.
$$

Then every candidate satisfying `R(c;S)>=R_best-10^-14` has exact current score before lower tie dimensions are applied. If this cannot be proved, rebuild or use D2.DEF.024.

## 8. REPAIR2

### D2.DEF.026 — Configured shell

For strictly increasing configured sizes `N_1<...<N_K`, define `N_0=0` and shell

$$
\mathcal S_i=[N_{i-1},N_i).
$$

At shell `i`, only ranks in `S_i` are removable; all lower ranks are immutable.

### D2.DEF.027 — Removal admissibility

For selected candidate `c`, define its unique covered mass as the total `omega_m(w)` over witnesses currently covered by `c` and by no other selected candidate. `c` is removal-eligible iff unique covered mass `<=10^-14` and removing `c` increases no canonical obligation deficit.

The accepted shortlist order is increasing representative loss, decreasing selected count of the removed candidate's correlation unit, then increasing removed UID; retain at most 64.

### D2.DEF.028 — Representative utility

For integer `k>=1`, define harmonic number

$$
H_k=\sum_{j=1}^{k}\frac1j,
$$

and `H_0=0`. For selected set `S`,

$$
U_{\mathrm{rep}}(S)=
\sum_m\sum_{w\in W_m}\omega_m(w)H_{n_m(w;S)}.
$$

### D2.DEF.029 — Repair objective

Define balance counts `b_g(S)` by correlation unit and tuple

$$
J(S)=
\left(
D_{\mathrm{hard}}(S),
\min_m C_m(S),
\sum_m C_m(S),
U_{\mathrm{rep}}(S),
-\sum_g b_g(S)^2
\right).
$$

Comparison minimizes component 1, maximizes components 2-4 with `10^-14` floating contender tolerance, then maximizes exact integer component 5. A swap is admissible only if it strictly improves this ordered objective and, for every required family `m`,

$$
C_m(S_{\mathrm{after}})+10^{-14}\ge C_m(S_{\mathrm{before}}).
$$

Objective-equivalent admissible proposals use increasing `(representative_loss, removed_rank, removed_UID, replacement_UID)`.

### D2.AX.002 — Repair reconstruction axiom

After any accepted swap, all prefix-derived lazy/frontier/marginal/cache/checkpoint/journal state from the pre-swap prefix is stale. Continuation reconstructs exact forward state from authenticated primitive evidence plus the exact repaired prefix; a Phase-B continuation performs an exact all-candidate rebase. A zero-swap shell may retain authentic state whose prefix identity is unchanged.

## 9. MVQUAL

### D2.DEF.030 — Independent configured-prefix qualification

For configured `N`, let `T_N` be the exact repaired prefix. Independently recompute from immutable TargetCoverageReference and canonical obligations:

- direct `C_m(T_N)` under D2.DEF.007-D2.DEF.010;
- extent predicates under D2.DEF.011;
- every `q_o(T_N)` under D2.DEF.014;
- training-label usability.

MVIDX may provide an exact secondary cross-check, but selector/repair counters are not the sole oracle.

Direct family mass and MVIDX family mass must agree with `rtol=0`, `atol=5*10^-12`; disagreement is an invariant error.

The prefix qualifies iff all required predicates pass. Under fixed nested prefixes/evidence, observed configured qualification must have form `FAIL* -> PASS*`; a later `PASS -> FAIL` fails closed.

## 10. Atomic-reference fitting and identifiability

### D2.DEF.031 — Composition matrix

For exact authorized fit membership `D` and atomic species basis `(z_1,...,z_p)`, define count matrix `C in N_0^{|D| x p}` by atom counts and total-energy target vector `y in R^{|D|}`.

### D2.DEF.032 — Foundation-residual least-squares family

For exact selected foundation identity `Phi`, let `y_fnd` be its predicted total energy on `D`, let `e_fnd(Phi)` be its head-local elemental reference vector, and define residual `r=y-y_fnd`.

With accepted regularization/anchor tuple `(lambda,delta e_prior)`, solve

$$
\widehat{\delta\mathbf e}
=\arg\min_{\delta\mathbf e}
\left(
\|C\delta\mathbf e-r\|_2^2
+\lambda\|\delta\mathbf e-\delta\mathbf e_{\mathrm{prior}}\|_2^2
\right).
$$

The target head reference is

$$
\mathbf e_{\mathrm{target}}(\Phi)=
\mathbf e_{\mathrm{fnd}}(\Phi)+\widehat{\delta\mathbf e}.
$$

Element order is atomic-number order. CV uses exact fold gradient membership `G_i`; final production uses exact complete `T_selected`. Monitor and held-out target labels are excluded.

### D2.DEF.033 — Free null space and composition-transfer test

Let `N_free` be the null directions left unconstrained by the authorized composition equations and explicit accepted anchors. With no accepted anchor, `N_free=ker(C)` under the accepted numerical-rank rule.

For required composition vector `c`, define transfer-feasible iff

$$
\mathbf c^T\mathbf v=0
\quad\text{for every }\mathbf v\in N_{\mathrm{free}}.
$$

Tolerance may classify numerical rank; it cannot create information absent from the authorized problem. Rank, singular values, residual diagnostics, anchor identity, and required-composition tests are evidence required for interpretation.

## 11. Foundation-P5 robust objective

### D2.DEF.034 — Scalar Huber function

For `delta>0`,

$$
h_\delta(x)=
\begin{cases}
\frac12x^2,&|x|\le\delta,\\
\delta\left(|x|-\frac12\delta\right),&|x|>\delta.
\end{cases}
$$

### D2.DEF.035 — Dimensional robust thresholds

The current pinned numeric Huber parameter is `0.01`, applied independently in canonical property units:

$$
\delta_E=0.01\ \mathrm{eV/atom},
$$

$$
\delta_{F,0}=0.01\ \mathrm{eV/angstrom},
$$

$$
\delta_S=0.01\ \mathrm{eV/angstrom^3}.
$$

For masked reference force norm `f`,

$$
\delta_F(f)=\delta_{F,0}
\begin{cases}
1.0,&f<100,\\
0.7,&100\le f<200,\\
0.4,&200\le f<300,\\
0.1,&f\ge300,
\end{cases}
$$

where force values in this piecewise rule are in `eV/angstrom`.

### D2.DEF.036 — Property losses

For configuration `i` with `n_i>0`, masks `m_i^E,m_i^F,m_i^S in {0,1}`, total-energy residual `Delta E_i`, atomic force residuals, and full Cartesian stress residual matrix:

- `L_E` is the arithmetic mean over configurations of `h_deltaE(m_i^E Delta E_i/n_i)`;
- `L_F` is the arithmetic mean over all stored Cartesian force components after applying the binary force mask, using per-atom `delta_F(f_ia)` from the masked reference force norm;
- `L_S` is the arithmetic mean over all **nine** stored Cartesian stress entries per admitted configuration of `h_deltaS(m_i^S Delta sigma_iab)`.

The nine-entry stress reduction intentionally counts symmetric off-diagonal entries twice; a six-component Voigt mean is not numerically equivalent.

### D2.DEF.037 — Foundation-P5 objective

$$
L_{P5}=L_E+10L_F+L_S.
$$

No independent per-configuration scalar weight and no target/replay training-head scalar occur in this objective. A transport field required by a dependency interface must be neutral if present.

## 12. P3 optimizer normalization and estimator

### D2.DEF.038 — P3 updates per epoch

For target size `N>0` and batch size `B>0`, with complete final partial target batch retained,

$$
U_N=\left\lceil\frac{N}{B}\right\rceil.
$$

### D2.DEF.039 — First-order progress normalization

For reference `(N_ref,LR_ref,beta_ref)` with `U_ref=ceil(N_ref/B)`, define

$$
s_N=\frac{U_{\mathrm{ref}}}{U_N},
$$

$$
LR_N=LR_{\mathrm{ref}}s_N,
$$

and, when exponential moving average is enabled,

$$
\beta_N=\beta_{\mathrm{ref}}^{s_N}.
$$

Then `LR_N U_N = LR_ref U_ref` and `(beta_N)^{U_N}=beta_ref^{U_ref}` algebraically. This is first-order normalization, not exact optimizer-trajectory equivalence.

### D2.DEF.040 — P3 target-force estimator

For `K>0` admitted Cartesian force components,

$$
E_{N,s}=
1000\sqrt{\frac1K\sum_{k=1}^{K}
(\widehat F_k-F_k)^2}
$$

in `meV/angstrom`. Non-finite prediction or metric is a typed numerical failure, not `+infinity` score substitution.

### D2.DEF.041 — Complete-seed candidate score

For configured seed set `S_seed`, candidate score exists only if every required seed has a valid finite metric:

$$
\overline E_N=\frac{1}{|S_{\mathrm{seed}}|}
\sum_{s\in S_{\mathrm{seed}}}E_{N,s}.
$$

No successful-subset mean is defined.

### D2.DEF.042 — Practical-equivalence reducer step

For surviving candidate set `A`, let `E_min=min_{N in A} Ebar_N` and configured `epsilon>0`. Define

$$
\mathcal E=\{N\in A:\overline E_N\le E_{\min}+\epsilon\}.
$$

The next reducer choice is the smallest `N` in `E`; remove it and repeat according to the accepted funnel. The accepted tiny floating comparison guard may be applied only as already governed; it is not a substitute for scientific `epsilon`.

## 13. P5 exposure

### D2.DEF.043 — Combined corpus order

For current two-head multihead replay with authenticated replay corpus `D_r` and target corpus `D_t`, the pre-shuffle combined tuple is

$$
D_{\mathrm{train}}=D_r\Vert D_t.
$$

A fixed seed shuffles integer indices of this ordered tuple. Reversing corpus blocks changes index-to-example mapping and is non-equivalent unless separately qualified.

### D2.DEF.044 — Current single-process update geometry

With `N_r=|D_r|`, `N_t=|D_t|`, and batch size `B>0`, current foundation-P5 combined loader uses `drop_last=true` and

$$
U=\left\lfloor\frac{N_r+N_t}{B}\right\rfloor.
$$

Exactly `UB` examples of each epoch's shuffled permutation are consumed. There is no intentional target duplication or balancing sampler. For naive fine-tuning, `N_r=0`.

Distributed execution is not presumed equivalent; it requires evidence that global property means, corpus exposure, and optimizer trajectory satisfy the accepted equivalence envelope.

## 14. Common monitor construction

### D2.DEF.045 — Monitor parent and strata

Let usable protected `OUTER_MONITOR` parent be `P_mon`. Current required monitor cardinality is `n_mon=256`; `|P_mon|<256` is infeasible. Each parent frame belongs to stratum string `<condition_id>:<run_id>` and is ordered within its stratum by `(source_frame_index, frame_uid)`.

### D2.DEF.046 — Deterministic quota order

With seed `q=161803`, each nonempty stratum key `s` receives marker equal to lowercase hexadecimal SHA-256 of UTF-8 bytes

```text
<q>\0quota\0<s>
```

where `<q>` is base-10 seed text and each `\0` is one NUL byte. Sort strata by `(marker,s)`. Initialize quotas to zero and repeatedly sweep this order, incrementing a stratum whose quota is below capacity, until exactly 256 slots are allocated.

### D2.DEF.047 — Deterministic systematic positions

For stratum capacity `n` and quota `k` with `1<=k<=n`, namespace `target:<s>`, compute SHA-256 of UTF-8 `<q>\0<namespace>`, take first eight digest bytes as unsigned big-endian integer `I`, and define

$$
u=\frac{I+0.5}{2^{64}}.
$$

If `k=n`, select all. Otherwise, for `j=0,...,k-1`,

$$
p_j=
\min\left(n-1,
\left\lfloor\frac{(j+u)n}{k}\right\rfloor\right).
$$

Positions must be distinct; duplicates are construction failure. Exact selected membership plus parent/policy/seed/strata identity defines `M_mon`.

## 15. Post-selection folds

### D2.DEF.048 — Component fold order

For exact frozen `T_N`, let sorted protected-component identities be `C_comp`, fold count `K>=2`, partition seed `s_cv`, algorithm identity `a`, and selected-membership digest `d_T`. If `|C_comp|<K`, CV is infeasible.

For component identity `c`, let `salt=<a>|<d_T>` and marker be SHA-256 hex of UTF-8 `<salt>|<s_cv>|<c>`. Sort by `(marker,c)`; ordered position `j` is held out in fold `j mod K`.

### D2.DEF.049 — Purge rule

For fold `i`, let `O_i` be held-out components and `R_i` the lexicographically sorted remaining components. With configured nonnegative `p_cfg`,

$$
p_i=\min\left(p_{\mathrm{cfg}},\max(0,|R_i|-2)\right).
$$

If `p_i=0`, purge is empty. If `p_i=1`, choose index `floor(|R_i|/2)`. If `p_i>1`, let `h=(|R_i|-1)/(p_i-1)` and propose indices by nearest-integer ties-to-even rounding of `jh`; deduplicate, append lowest unselected integer indices until `p_i` positions exist, then sort. `G_i` is the component complement of held-out plus purge. `M_mon` is external.

## 16. Checkpoint predicates and role policy

### D2.DEF.050 — Shared checkpoint constraint

For checkpoint `c`, `S(c)` is the conjunction of current shared mandatory constraints: finite required metrics, replay degradation within accepted budget using authenticated true-reference evidence when replay is active, and required physical/integrity predicates. These constraints are shared-method semantics, not role thresholds.

### D2.DEF.051 — Target-monitor RMSE

`r_mon(c)` is target force-component RMSE of checkpoint `c` on exact `M_mon`, in `eV/angstrom`, using the accepted force estimator. Held-out metric `r_out` is computed on exact fold `O_i` under the configured outer metric.

### D2.DEF.052 — Role-effective checkpoint admissibility

For role `rho` with resolved target-monitor ceiling `tau_rho`,

$$
A_\rho(c)=S(c)\wedge r_{\mathrm{mon}}(c)\le\tau_\rho.
$$

Foundation CV uses `tau_CV`; fresh production uses `tau_prod`. Boundaries are inclusive in binary64 against the binary64 value nearest the resolved decimal configuration. `r=tau` passes; the next representable binary64 above it fails.

### D2.DEF.053 — CV outer predicate

For resolved configured outer metric and threshold `theta_CV`, a frozen fold representative passes outer evaluation iff its exact held-out metric is finite and `<=theta_CV`. If the outer metric is not target-force RMSE, its units/threshold remain independent of `tau_CV`.

### D2.DEF.054 — All-required-position CV acceptance

Let `P_req` be the finite set of required `(fold,seed)` positions. CV accepts iff, for every `p in P_req`, training completed under the frozen method, the admissible checkpoint set under D2.DEF.052 is nonempty, one representative is frozen by the accepted ranking rule, and that representative satisfies D2.DEF.053. No averaging or majority predicate is defined.

### D2.AX.003 — Role-currentness axiom

A threshold classification is evidence only under the resolved role-policy identity that produced it. Changing `tau_CV` or `theta_CV` stales dependent CV acceptance and any production authorization derived from it while leaving `tau_prod` and shared method unchanged. Changing `tau_prod` stales production role evidence only. Changing shared `S` can stale both roles.

## 17. Restart, precision, and equivalence

### D2.DEF.055 — Authenticated continuation state

A continuation state is admissible only when it binds every scientific/numerical identity needed to prove it belongs to the exact run boundary being resumed: population/membership, method/policy parameters, foundation/head, objective/exposure, selector/reference identities where applicable, optimizer/EMA/RNG state, and exact accepted predecessor boundary. Uncommitted scratch is not continuation authority.

### D2.DEF.056 — Numerical equivalence relation

For an optimized implementation `A` and reference owner `R`, write

$$
A\equiv_{\mathcal O}R
$$

iff for the declared validity domain they produce every authoritative observable/decision in output set `O` under the exact owner-required equality/tolerance relation. `O` may require bitwise equality for selector ranks/gains or numerical tolerance for an independently governed metric. Performance alone never establishes equivalence.

### D2.AX.004 — Execution noninterference axiom

Worker count, queue completion order, block/chunk size, mmap layout, cache residence, native backend, and restart route are execution-only exactly when they preserve all D2 authoritative outputs under D2.DEF.056. Otherwise they are method-affecting and require D2 review.

## 18. Formal undefined/failure cases

The numerical method fails closed rather than selecting a fallback when any required definition is undefined, including:

- non-finite/invalid input to a required fitted statistic;
- zero represented family/correlation mass;
- impossible leave-one-out radius or missing support edge;
- same-locus obligation disagreement in exact incidence/applicability;
- infeasible configured ladder proven by accepted hard constraints;
- inability to certify lazy exactness;
- post-repair state whose exact prefix identity is not reconstructible;
- MVQUAL direct/sparse disagreement beyond accepted tolerance;
- non-identifiable governed E0 composition correction;
- non-finite model/prediction/metric;
- monitor parent support below required cardinality or protected overlap;
- missing required fold/seed or no admissible checkpoint;
- stale/mismatched continuation or method identity.

Threshold/tolerance widening, evidence-role substitution, or rescue-size invention is not a numerical error handler.

## 19. Direct D2 definition dependencies

The companion dependency trace records every direct edge. Core order:

```text
D2.DEF.004 weights
 -> D2.DEF.005 quantile
 -> D2.DEF.006 scale
 -> D2.DEF.007 metric
 -> D2.DEF.008 radius
 -> D2.DEF.009 adjacency
 -> D2.DEF.010 coverage
 -> D2.DEF.011 extent

D2.DEF.012 source obligation
 -> D2.DEF.013 canonicalization
 -> D2.DEF.014 count/deficit

D2.DEF.009 + D2.DEF.013
 -> D2.AX.001 MVIDX exact representation
 -> D2.DEF.016 selector state
 -> D2.DEF.017..020 candidate primitives
 -> D2.DEF.022/023 selection
 -> D2.DEF.024 reference oracle
 -> D2.DEF.025 lazy equivalence
 -> D2.DEF.026..029 repair
 -> D2.DEF.030 qualification

D2.DEF.031 composition matrix + D1.DEF.020 foundation identity
 -> D2.DEF.032 residual fit
 -> D2.DEF.033 composition transfer

D2.DEF.034 Huber + D2.DEF.035 thresholds
 -> D2.DEF.036 property losses
 -> D2.DEF.037 P5 objective

D2.DEF.045 monitor parent
 -> D2.DEF.046 quota
 -> D2.DEF.047 positions
 -> D2.DEF.051 r_mon
 -> D2.DEF.052 role admissibility

D2.DEF.048 folds + D2.DEF.049 purge
 -> D2.DEF.053 outer predicate
 -> D2.DEF.054 CV acceptance
```

## 20. Required verification oracles

Promotion requires preserving the existing accepted oracle suite and adding explicit formal-definition checks:

1. every D1/D2 identifier used as a prerequisite exists before substantive use or is an exact imported owner;
2. the direct dependency graph has no unexplained cycle; any legitimate mutually recursive definition must be declared as one composite object;
3. all renderer-facing MLFF D1/D2 formulas contain no unsupported `operatorname` macros and no raw `#` cardinality macro;
4. D2.DEF.017 equals the previous hard-gain cardinality for adversarial obligation sets;
5. D2.DEF.020 equals the previous nested arithmetic mean bit-for-bit under the same iteration association where the reference algorithm requires it;
6. dense adjacency versus NEIGHBOR1 exactness at boundaries;
7. direct TargetCoverage versus MVIDX mass equality;
8. full-forward versus lazy MVSEL2 rank equality at every rank;
9. obligation alias/stronger-minimum/source-ID invariance and conflict fail-closed cases;
10. repair scalar/optimized trace equality and lower-prefix immutability;
11. primitive replay versus post-repair reconstruction equality;
12. complete-order continuation beyond configured `N_max`;
13. direct MVQUAL versus optimized qualification equality and monotonicity;
14. selected-head E0 fit and rank-deficient transfer counterexamples;
15. robust-loss hand calculations at all dimensional threshold boundaries;
16. deterministic monitor reconstruction and protected disjointness;
17. deterministic fold/purge reconstruction;
18. exact role-threshold boundary and selective-currentness tests;
19. worker/backend/chunk/cache/restart invariance of all scientific outputs.

## 21. D2 -> D3 handoff

D3 must preserve the formal objects and equivalence requirements above while owning persistence, concurrency, resource admission, software decomposition, dependency adaptation, build topology, and durable restart representation. D3 may consolidate or simplify implementations but may not create a second numerical owner, weaken fail-closed predicates, or encode defaults as universal scientific constants.

## 22. Acceptance condition for this overlay

Independent review must demonstrate that this kernel is losslessly equivalent to the accepted basis for every unchanged scientific/numerical claim and that the renderer-safe formula rewrites are exact. Any newly excluded numerical regime, changed association affecting a reference result, changed threshold/tolerance, or changed failure classification is a D2 semantic change and requires explicit adjudication rather than being accepted as editorial formalization.
