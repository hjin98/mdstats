---
kind: proposed-D2-authority-kernel
protocol_version: 6.4.0
status: PROPOSED_RENEWAL_CANDIDATE_AWAITING_INDEPENDENT_REVIEW
accepted_d2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_d2_source_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
prior_independent_review_target: e827aef9bdceb97aae5be6e89de0585a95dcf71c
prior_independent_review_commit: 2eddd9058beda039e0ff53d4e50a189be469173b
parent_D1_ratified_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
parent_D1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
parent_D1_ratification_record: workplans/active/MLFF_REPLAY_RETENTION_TARGET_ADMISSIBILITY_D1_R3_RATIFICATION.md
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
stakeholder_direction_date: 2026-09-18
---

# mdstats MLFF D2 formal numerical authority kernel — Protocol 6.4 proposed replay/target-policy renewal

## 1. Authority and exact import registry

The accepted-current D2 authority remains the repository state on `main@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2` until this candidate passes fresh independent Protocol-6.4 D2 Review and receives the required stakeholder ratification. This file is the proposed D2 replacement on the replay-retention, foundation role-threshold, foundation-P5 representative-selection, reassessment, and training/measurement-equivalence surface.

Its parent D1 authority is the independently reviewed and stakeholder-ratified immutable target `d761171f3c86c3c79b87a90cfc02ac324c261b1a` with canonical D1 blob `612294ec4680db01a18085e13fbfe5dcfa9fb7ed`.

The accepted D2 numerical meaning reconstructed at basis `cb07d68372f1b6d25f9e8b62a2fb7e31fb82e824` and exact sources pinned at `a4824d28775164aa942fd29fa97ee0957eb87e6f` remain imported for every unaffected surface. The prior assembled-candidate Review passed on `e827aef9bdceb97aae5be6e89de0585a95dcf71c` at `2eddd9058beda039e0ff53d4e50a189be469173b`; that prior PASS is historical evidence, not acceptance of this material renewal.

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

These exact imports are normative roots for accepted details not restated below. Definitions below formalize high-risk semantics. On this candidate only, the local definitions/axioms below supersede conflicting imported clauses on these bounded surfaces:

- `D2.DEF.052`: replay evidence qualification/lineage excludes checkpoint warning/hard thresholds and checkpoint-ordering policy;
- `D2.DEF.057-059B`: signed replay degradation, diagnostic/hard classification, role thresholds `75/75/50 meV/angstrom`, complete-checkpoint strict target ordering, and final single-best-seed ordering;
- `D2.AX.004-005`: assessment-policy currentness and current-CV reauthorization of historically fresh final production;
- `D2.DEF.060-060C`: training-semantic continuation/reuse, measurement equivalence, and policy reassessment;
- the parameter ledger, falsification oracles, D2-to-D3 handoff, and candidate lifecycle statements descending from those changes.

In particular, imported prose that treats replay degradation as one hard budget, gives replay/secondary/uncertainty/maturity evidence authority to outrank a lower foundation-P5 target RMSE, binds assessment-only thresholds/order into training continuation semantics, or fixes foundation role defaults at `45/45/30 meV/angstrom` is superseded here. P3 practical-equivalence ranking and every unaffected numerical method remain imported unchanged.

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

### D2.DEF.052 — Replay lineage and evidence-qualification currentness

Let `Q_r` be the exact replay **evidence-qualification** identity/state required by D1.DEF.022: source/label/provider validity, independent true-reference replay-monitor validity, and other evidence conditions needed to interpret replay training and replay-retention measurements. `Q_r` does not contain `delta_warn`, `delta_hard`, a role target ceiling, or checkpoint-selection ordering.

Replay lineage binds replay geometry/source membership/split, label mode, exact true-reference monitor, `Q_r`, exact foundation checkpoint/head `Phi`, `e_replay(Phi)` where applicable, prediction policy, and realized exposure. Changing any lineage component invalidates dependent replay training/evaluation evidence according to the affected component. Changing label mode over one authenticated prepared source/split does not by itself change replay geometry membership.

Changing only `delta_warn` or `delta_hard` does not change replay geometry, training labels, realized exposure, foundation identity, true-reference measurement identity, or TRAIN2 trajectory. Those thresholds classify already-defined replay measurements later under D2.DEF.057.

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

### D2.DEF.057 — True-reference replay degradation and decision classification

For replay-enabled foundation adaptation and checkpoint `c`, let

$$
R_c=R_{\mathrm{replay}}(c),\qquad R_0=R_{\mathrm{replay}}(\Phi)
$$

be finite canonical binary64 force-component RMSE values in `eV/angstrom` computed on the **same exact** authenticated true-reference replay monitor under the same metric/reduction, label/reference, provider/model-realization, head and precision semantics. A scalar value without this common provenance cannot enter the degradation calculation.

Define the canonical signed degradation by one IEEE-754 binary64 round-to-nearest, ties-to-even subtraction,

$$
\Delta_R(c)=\operatorname{RN}_{64}(R_c-R_0).
$$

No absolute value, ratio, percentage, normalization, clipping, epsilon, or rounding-before-comparison is introduced.

The replay decision-policy family is `(delta_warn,delta_hard)` in internal `eV/angstrom`. Public values expressed in `meV/angstrom` are converted once by

$$
\delta=\operatorname{RN}_{64}(10^{-3}v_{\mathrm{meV/angstrom}}).
$$

The resolved internal values must be finite and positive and must satisfy

$$
0<\delta_{\mathrm{warn}}<\delta_{\mathrm{hard}}.
$$

If conversion collapses two distinct public values to equal binary64 internal values, the policy is invalid rather than silently reordered.

For finite authenticated replay evidence,

$$
W(c)=[\Delta_R(c)>\delta_{\mathrm{warn}}],
$$

$$
F_{\mathrm{replay}}(c)=[\Delta_R(c)>\delta_{\mathrm{hard}}],
$$

with generated defaults `delta_warn = 0.050 eV/angstrom` and `delta_hard = 0.100 eV/angstrom`. Equality at either threshold does not trigger its strict-exceedance predicate. Negative degradation is neither warning nor catastrophic failure.

Let `S(c)` be the shared hard checkpoint-constraint conjunction: every required finite/evidence-validity and physical/integrity condition plus, when replay is enabled, `not F_replay(c)`. Missing, stale, unauthenticated, incompatible or non-finite required replay evidence is a hard evidence-validity failure independent of the numeric degradation class. `W(c)` is diagnostic only and is not an argument of `S(c)`.

The decision is defined on the canonical binary64 measurements and thresholds above. Representation rounding is therefore part of the numerical method; it does not create an uncertainty band or permission to widen either comparison.

### D2.DEF.058 — Role-effective checkpoint predicate

Let `r_mon(c)` be the finite canonical binary64 target force-component RMSE on exact `M_mon` in `eV/angstrom`. For foundation role `rho`,

$$
A_\rho(c)=S(c)\wedge r_{\mathrm{mon}}(c)\le\tau_\rho.
$$

CV uses generated/default `tau_CV = 0.075 eV/angstrom`; production uses generated/default `tau_prod = 0.050 eV/angstrom`. Each resolved threshold is a finite positive canonical binary64 value in `eV/angstrom`; explicit configured values remain their resolved values.

The comparison is direct binary64 `<=` with no epsilon or practical-equivalence band. Exact equality passes. The next representable binary64 value above the resolved ceiling fails. Scratch retains its separately accepted threshold semantics.

### D2.DEF.059 — CV outer predicate and all-position acceptance

Let the frozen representative's configured held-out metric on exact `O_i` be `r_out`. Under the default outer metric `target_force_rmse_ev_per_angstrom`, `r_out` is finite canonical binary64 target force-component RMSE in `eV/angstrom` and generated/default

$$
\theta_{\mathrm{CV}}=0.075\ \mathrm{eV/angstrom}.
$$

The representative passes iff `r_out <= theta_CV`, with the same direct inclusive binary64 boundary rule as D2.DEF.058.

An explicitly different outer metric retains its own accepted units, estimator and threshold-resolution semantics. This renewal does **not** assign `0.075` to another metric merely because its threshold is omitted or numerically resembles the old force-RMSE default; an alternative outer metric never supplies `tau_CV`.

CV accepts iff every required `(fold,seed)` position completes the frozen fixed-budget method/horizon, every governed checkpoint position is assessed as required by D1.DEF.026, the position has a nonempty hard-admissible set under D2.DEF.058, its representative is frozen under D2.DEF.059A, and that representative passes the outer predicate. No mean, majority, best-seed or dispersion rescue exists.

### D2.DEF.059A — Complete-checkpoint strict target representative order

For a realized foundation-P5 role `rho`, let `C_rho` be the governed durable checkpoint universe from D1.DEF.026 and

$$
H_\rho=\{c\in C_\rho:A_\rho(c)\}.
$$

Every member of `C_rho` receives its required assessment; a missing/invalid measurement or evidence item is handled by the applicable hard failure and is never silently removed by shortlist/rescue logic.

If `H_rho` is empty, there is no representative. Otherwise define the deterministic within-run key

$$
K_{\mathrm{run}}(c)=
\bigl(r_{\mathrm{mon}}(c),\operatorname{epoch}(c),\operatorname{sha256}(c)\bigr),
$$

ordered lexicographically ascending, where `r_mon` is the exact canonical binary64 value, `epoch` is the exact checkpoint epoch integer, and `sha256` is the canonical lowercase hexadecimal checkpoint digest.

The representative is

$$
c^*=\arg\min_{c\in H_\rho}K_{\mathrm{run}}(c).
$$

The first coordinate is strict primary authority: a checkpoint with larger finite `r_mon` can never win because of replay margin/warning state, energy/stress/secondary target diagnostics, maturity/refinement phase, practical-equivalence bands, bootstrap uncertainty, historical score weights, or evaluator shortlist status. The epoch/digest coordinates are consulted only when the canonical binary64 target RMSE values are exactly equal.

Quality-dependent thinning of `C_rho` is not equivalent to this algorithm.

### D2.DEF.059B — Final single-best-seed order

Each required production seed first freezes its representative under D2.DEF.059A.

For `all_qualified_final_seeds`, no cross-seed numerical ranking is performed.

For `single_best_final_seed`, for every already-frozen admissible seed representative `c_s`, define

$$
K_{\mathrm{seed}}(s)=
\bigl(r_{\mathrm{mon}}(c_s),\operatorname{optimizer\_seed}(s),\operatorname{sha256}(c_s)\bigr).
$$

The published member is the lexicographic minimum. No new target evaluation is performed. Replay values/warnings, secondary metrics, maturity/refinement, practical-equivalence and bootstrap quantities cannot affect the ordering. Seed and digest are consulted only after exact equality of canonical binary64 target RMSE.

### D2.AX.004 — Assessment-policy currentness and numerical noninterference

The following dependency consequences are normative:

1. changing only `delta_warn` changes warning/report classification only; replay measurements, hard admissibility, `H_rho`, representative identity, outer measurement, CV verdict, production authorization, publication membership and TRAIN2 remain current;
2. changing `delta_hard` changes hard checkpoint assessment, `H_rho`, representative and dependent CV/final verdict/publication, but not authenticated replay numeric measurements or TRAIN2;
3. changing `tau_CV` changes CV hard checkpoint assessment, `H_CV`, representative, and therefore dependent outer evaluation/verdict and production authorization, but not CV TRAIN2 or already-authenticated checkpoint/common-monitor measurements;
4. changing `theta_CV` changes only the CV outer pass/fail decision and dependent production authorization; it does not change `C_CV`, `H_CV`, representative identity, TRAIN2, or an already-authenticated outer numeric measurement;
5. changing `tau_prod` changes production hard checkpoint assessment, representative and dependent publication decision, but not production TRAIN2 or accepted CV evidence;
6. changing the D2.DEF.059A/059B selection algorithm identity changes the corresponding representative/publication descendants, but not TRAIN2 or already-authenticated numeric measurements;
7. changing replay evidence qualification/lineage under D2.DEF.052 invalidates only descendants whose numerical meaning depends on the changed evidence component; decision thresholds are not part of that lineage.

No hard-decision, outer-acceptance or selection-policy edit can change an already-realized TRAIN2 trajectory when every training-bearing numerical input/method coordinate is unchanged.

A stored historical verdict/classification is never made current by monotonic threshold implication. Currentness requires a new assessment under the current decision policy; numeric measurement reuse is governed by D2.DEF.060B-060C.

### D2.AX.005 — Fresh production and current-CV reauthorization

A newly executed final-production trajectory starts a fresh model/optimizer lineage from the accepted foundation checkpoint/head on exact complete `T_selected`, fits training-dependent state there only, uses the same exact `M_mon` and checkpoint mechanics as CV, and applies `tau_prod`. No P3 or CV checkpoint is a warm-start parent; P3 `M3` has no production checkpoint role.

Replay-enabled production retains D2.DEF.051-053, current evidence-valid replay lineage, exact `e_replay(Phi)` where applicable, and D2.DEF.057 true-reference retention classification.

Current accepted CV authorization is required before a current final-production assessment/publication may be issued. A historically fresh completed final-production trajectory may be reassessed under current policy without retraining only when current CV has been reclosed and accepted and D2.DEF.060 proves exact training-semantic equivalence for that production trajectory. If current CV rejects, retained final-production bytes remain historical/nonpublishable under the current authority regardless of checkpoint quality.

## 15. Continuation, equivalence, and fail-closed semantics

## 15. Continuation, equivalence, and fail-closed semantics

### D2.DEF.060 — Authenticated continuation and training-semantic equivalence

Assessment-only policy is not a training-continuation coordinate.

For an interrupted trajectory, continuation is admissible only from the exact authenticated predecessor state with matching trajectory-generating semantics: training/fold role and exact gradient/replay-training memberships; optimizer seed and planned horizon; foundation checkpoint/head and training replay lineage; fitted/prepared training state; objective/loss, exposure/corpus order, optimizer, learning-rate schedule, precision and other numerically material execution semantics; checkpoint cadence; trainer-consumed validation/preparation inputs; optimizer/EMA/RNG state; and accepted predecessor boundary. Uncommitted scratch is never continuation authority.

For reuse of a completed historical TRAIN2 trajectory under a later assessment policy, **training-semantic equivalence** holds only when every numerical input/coordinate capable of changing the realized TRAIN2 trajectory is proven equal under its accepted relation. `delta_warn`, `delta_hard`, `tau_CV`, `theta_CV`, `tau_prod`, D2.DEF.059A/059B selection policy, and later verdict/publication policy are excluded because they are not consumed by fixed-budget training.

A pre-cutover interrupted trajectory continues under its authenticated historical runtime/protocol ancestry after that exact training-equivalence proof; no policy migration rewrites historical optimizer state, summaries, checkpoint bytes, hashes or RNG lineage.

### D2.DEF.060A — Numerical-equivalence relation registry

For authoritative outputs, the comparison relation is source-closed as follows:

1. canonical memberships, UIDs, component/order/rank sequences, discrete decisions, integer counts, lineage identities, checkpoint/model identities and repair traces compare by exact identity/equality under their defining objects;
2. local numerical predicates with explicit fixed tolerances/guards use exactly D2.DEF.018, D2.DEF.020-021, D2.DEF.029-030, D2.DEF.033, D2.DEF.036, D2.DEF.038 and D2.DEF.057-059B as applicable;
3. accepted source-owned metric/equality relations not restated locally are imported only from exact `D2.SRC.GENERAL` or `D2.SRC.ORDER`;
4. every other governed binary64 scientific output whose owner supplies no nonzero tolerance compares by exact canonical binary64 value/reference arithmetic.

No backend-observed discrepancy, performance result, generic "close enough" rule, monotonic-policy implication or unlisted tolerance can create a new equivalence relation.

### D2.DEF.060B — Evaluation-measurement equivalence

Two target or replay numerical measurement records are equivalent for policy reassessment only when the exact numerical experiment is provably the same, including as applicable:

- exact checkpoint/model-state identity;
- exact evaluation population/membership/artifact and labels/reference values;
- metric definition, units, reduction and aggregation policy;
- model/head/provider/prediction realization and numerically material precision semantics.

Assessment thresholds, warning policy, representative-ordering policy, committee/publication policy and a full role-plan digest are not numerical measurement inputs merely because historical schemas hashed them together.

Scalar equality alone is insufficient evidence of measurement equivalence. If historical provenance cannot prove the required equality of numerical inputs, recompute the measurement from the preserved authenticated checkpoint and evaluation evidence rather than copying the scalar.

### D2.DEF.060C — Policy reassessment from immutable measurements

A current checkpoint assessment is produced by applying current D2.DEF.057-059B policy to current or D2.DEF.060B-equivalent immutable measurements. Historical `admissible`, rejection-reason, warning, rank, representative, fold-verdict or production-publication classifications are never mutated or relabeled current in place.

For historical CV:

1. reassess every governed checkpoint under current hard policy and D2.DEF.059A;
2. if the current representative is the same checkpoint and its held-out measurement is D2.DEF.060B-equivalent, that outer measurement may be reused;
3. if the representative changes, evaluate the new representative on the exact held-out population before applying current `theta_CV`;
4. publish a new current fold/seed/campaign assessment.

For historical final production, reassess the complete governed checkpoint universe after current-CV reauthorization. If the old candidate-set provenance is incomplete, recompute required EVAL2 measurements from preserved checkpoints; never infer the current winner from a historical shortlist or content-store scan.

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
| P5 global E:F:S property-loss coefficients | `FIXED_METHOD_COORDINATE` | `1:10:1` |
| replay label mode | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | true-reference default; pseudo explicit opt-in |
| replay evidence qualification/state | `DERIVED` | source/label/provider/true-monitor qualification; excludes checkpoint decision thresholds |
| replay-head E0 | `DERIVED` | exact selected foundation checkpoint/head mapping |
| P5 corpus order/drop policy | `FIXED_METHOD_COORDINATE` | replay then target; `drop_last=true` |
| monitor cardinality/seed | `FIXED_METHOD_COORDINATE` | `256`, `161803` |
| CV fold count | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | integer `K>=2`, default `3` |
| `delta_warn`,`delta_hard` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | `50/100 meV/angstrom`, strict-exceedance replay classification |
| `tau_CV`,`theta_CV`,`tau_prod` | `CONFIGURABLE_WITH_GENERATED_DEFAULT` | `75/75/50 meV/angstrom` for default force outer metric; alternative outer metric keeps own `theta` units/resolution |
| foundation-P5 within-run representative order | `FIXED_METHOD_COORDINATE` | strict `(target RMSE, epoch, checkpoint SHA-256)` |
| `single_best_final_seed` order | `FIXED_METHOD_COORDINATE` | strict `(target RMSE, optimizer seed, checkpoint SHA-256)` |

## 17. Current falsification and reopen oracles

Qualification and any future reopen review must attempt at least: one-normalization governed-quantile adversaries; selector-vs-MVQUAL tolerance interval adversary; exact component-order/first-predecessor `M3`; condition-balanced `pi_eval`; structural-policy rejection; candidate-common-preparation perturbation; minimum-three-qualified admission including an unqualified configured prefix with at least three remaining qualified candidates; exact funnel/sufficiency/ceiling cases; autocorrelation/block/event fixtures; required-family applicability fixtures; exact adjacency boundaries; full-forward/lazy rank equality; Phase-A tie behavior; REPAIR2 frontier/trace/limits/rank inheritance/no-extra-shell; direct/MVIDX mass and MVQUAL monotonicity; E0 null-space transfer; replay-head E0 selected-head binding and target/replay E0 separation; robust P5 dimensional/nine-stress/mask/no-head-scalar; true-vs-pseudo replay geometry invariance; replay evidence-qualification invalidation; replay-first seeded exposure/drop-last; monitor/fold reconstruction; exact replay warning/hard boundaries; role-threshold boundaries/selective invalidation; strict foundation-P5 target ordering and exact ties; measurement/training equivalence; policy reassessment; equivalence-registry source closure; and worker/backend/restart invariance.

The replay oracle must include `Delta_R = delta_warn`, `nextafter(delta_warn,+inf)`, `Delta_R = delta_hard`, `nextafter(delta_hard,+inf)`, negative degradation, and a conversion case proving `50 meV/angstrom -> RN64(0.050 eV/angstrom)` and `100 -> RN64(0.100)`. Equality must not warn/reject; the next representable value above each threshold must trigger the corresponding strict predicate. No epsilon may change those outcomes.

The role-threshold oracle must include exact `0.075` and `nextafter(0.075,+inf)` for default-force CV checkpoint/outer predicates and exact `0.050` plus its next representable value for production. A `0.060 eV/angstrom` common-monitor checkpoint is a required discriminating example: it may pass default foundation CV `tau_CV=0.075` but must fail default production `tau_prod=0.050`. Alternative outer metrics must demonstrate that omission does not import the force-RMSE `0.075` value.

Strict-order adversaries must include a lower-target checkpoint with worse replay margin/warning, worse secondary diagnostics, lower maturity and an unfavorable bootstrap/practical-equivalence status; the lower exact target RMSE must still win when both checkpoints satisfy hard gates. Exact target ties must resolve only by `(epoch,sha256)`, and cross-seed exact ties only by `(optimizer_seed,sha256)`.

Currentness/reassessment oracles must separately perturb `delta_warn`, `delta_hard`, `tau_CV`, `theta_CV`, `tau_prod` and strict-order identity, proving the descendant movement in D2.AX.004 while TRAIN2 remains unchanged for assessment-only edits. Historical scalar reuse must fail when checkpoint/population/provider/metric provenance is incomplete and succeed only under D2.DEF.060B-equivalent numerical inputs.

The weighted-quantile oracle must exercise actual governed quantiles and one-time stored binary64 weights, and it must reproduce the exact prior D4 rescaling quantity `t = cumulative[-1]` with `cumulative = np.cumsum(stored_weights, dtype=np.float64)`. Required discriminating cases generated by the accepted correlation-balanced weight constructor are: counts `(50,1)` at `q=0.01` (direct index 0, residual-terminal-mass-rescaled index 1); `(2,6)` at `q=0.25` (direct index 0, rescaled index 1); `(1,6)` at `q=0.75` (direct index 4, rescaled index 3); and `(1,150)` at `q=0.99` (direct index 148, rescaled index 147). Each case must verify `t != 1.0` and compare cumulative stored mass directly with `q`. `np.sum(stored_weights)` is not a substitute for `t`, because the prior D4 implementation used terminal cumulative mass and binary64 reduction order can make the two residual sums differ.

## 18. D2 -> D3 handoff, candidate status and reopen condition

D3 owns persistence, concurrency, resource admission, software decomposition, dependency adaptation, build topology and durable restart/assessment representation. It may simplify execution but may not create a second numerical owner or weaken/change the method above.

For this renewal D3 must preserve at minimum:

1. replay evidence/measurement identity separately from `delta_warn`/`delta_hard` decision policy;
2. assessment-only thresholds and strict-order identity outside training-trajectory/restart identity;
3. complete governed-checkpoint assessment before foundation-P5 representative selection;
4. exact D2.DEF.059A/059B ordering and tie keys;
5. `tau_CV`, `theta_CV`, and `tau_prod` as distinct currentness coordinates;
6. assessment-independent numerical measurement provenance sufficient to prove D2.DEF.060B reuse or force recomputation;
7. immutable historical evidence with new current reassessment records rather than in-place reclassification;
8. current-CV reauthorization before current assessment/publication of a reusable historically fresh final-production trajectory.

The accepted-current D2 kernel remains `main@a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`. This file is a **proposed material D2 renewal** under ratified D1 target `d761171f3c86c3c79b87a90cfc02ac324c261b1a`. It is not accepted authority until fresh independent Protocol-6.4 D2 Review passes on an immutable candidate target and the stakeholder explicitly ratifies that exact reviewed target.

Fresh D2 Review must challenge at least: binary64 unit conversion and boundary semantics; subtraction/cancellation near replay thresholds; same-monitor/provenance requirements for signed degradation; exclusion of warning from hard admissibility; complete-checkpoint strict ordering; exact tie determinism; separation from P3 practical-equivalence semantics; alternative-outer-metric units/defaults; threshold-specific currentness; training-semantic versus assessment equivalence; historical measurement reuse without scalar-only inference; and current-CV reauthorization of retained final-production trajectories.

Reopen D2 after acceptance if material evidence shows that canonical binary64 comparison/conversion is numerically unstable for the claimed threshold resolution, the strict order cannot be reconstructed deterministically, measurement/training equivalence is insufficient to prevent stale numerical reuse, or another algorithm/precision/stochastic/error semantic needs revision. Pure renderer/editorial repairs remain representation work only when algebraic and decision equivalence are explicitly verified.