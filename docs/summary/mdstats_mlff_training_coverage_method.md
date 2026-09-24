# Multi-View Coverage Construction of MLFF Training-Set Size Ladders in `mdstats`

*A concise method paper for a physics audience*

**Central idea.** The `mdstats` MLFF workflow does not treat stored molecular-dynamics (MD) frames as independent observations and does not choose training configurations by uniform subsampling. It first converts eligible trajectories into autocorrelation-aware **correlation units**, protects additional relations that would make a train/evaluation split leak information, constructs the exact target-training population, and only then builds one deterministic multi-view ordering whose prefixes progressively cover the physically relevant variation of that population.

## 1. End-to-end preparation of the target-training population

The target-size experiment is downstream of several preparation steps. Conceptually,

```text
source trajectories + canonical labels
        -> eligible canonical frames
        -> autocorrelation-aware correlation units
        -> protected-relation closure and outer evidence roles
        -> neutral DEVELOPMENT population U_size
        -> exact protected split U_size = P_train dot-union M3
        -> multi-view feature reference on exact P_train
        -> one complete order pi_train
        -> nested training sets T_N = pi_train[:N].
```

This ordering matters scientifically. Evaluation, calibration, locked-test, and later cross-validation evidence are separated before target membership is constructed, so they cannot leak backward into the training-set ladder.

Let

\[
U_{\mathrm{size}}=P_{\mathrm{train}}\mathbin{\dot\cup}M_3
\]

be the exact target-size development split. Here, \(M_3\) is the largest P3 model-selection reserve and \(P_{\mathrm{train}}\) is the sole domain from which target-training subsets are constructed. The target-size ladder is therefore not a resampling of the entire trajectory archive.

## 2. Why MD frames must first be grouped statistically

Adjacent MD frames are serially correlated. If a trajectory is saved much more frequently than its slow physical degrees of freedom decorrelate, then many stored configurations describe essentially the same local state. Treating those frames as independent would cause densely sampled trajectory segments to dominate both data splitting and feature-space coverage.

For a stationary scalar observable \(X_t\), the normalized autocorrelation is

\[
\rho(k)=
\frac{\operatorname{Cov}(X_t,X_{t+k})}
     {\operatorname{Var}(X_t)},
\]

and the integrated autocorrelation time is

\[
\tau_{\mathrm{int}}
=\frac{1}{2}+\sum_{k=1}^{k^\star}\rho(k).
\]

The corresponding diagnostic effective number of samples is

\[
N_{\mathrm{eff}}
=\min\!\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
\]

For an uncorrelated sequence under this convention, \(\tau_{\mathrm{int}}=1/2\), so \(N_{\mathrm{eff}}=N\). A larger \(\tau_{\mathrm{int}}\) indicates increasing temporal redundancy. Importantly, this is a **diagnostic of serial correlation in the chosen observables**, not proof that all slow structural variables have become independent.

### 2.1 How `mdstats` estimates the correlation time

For a finite sequence \(x_0,\ldots,x_{N-1}\) with mean \(\bar x\), `mdstats` uses the unbiased finite-sequence autocovariance

\[
\widehat\gamma(k)=
\frac{1}{N-k}
\sum_{t=0}^{N-k-1}
(x_t-\bar x)(x_{t+k}-\bar x),
\]

and

\[
\widehat\rho(k)=\frac{\widehat\gamma(k)}{\widehat\gamma(0)}.
\]

The noisy long-lag tail is truncated using Geyer's initial-positive-sequence rule: adjacent lag pairs are retained while

\[
\widehat\rho(2m-1)+\widehat\rho(2m)>0.
\]

If \(K_+\) is the retained lag set,

\[
\widehat\tau_{\mathrm{int}}
=
\max\!\left(
\frac12,
\frac12+\sum_{k\in K_+}\widehat\rho(k)
\right).
\]

No autocorrelation is computed across a source gap, a continuation reset, or an excluded interval. Thus an apparently adjacent frame number does not create correlation evidence across a discontinuity in the physical trajectory record.

### 2.2 From correlation time to a complete-frame block length

For each source run and each contiguous eligible segment, the configured correlation observables are analyzed. Let \(j\) index observables and \(r\) index contiguous segments. The most conservative accepted time is

\[
\tau_{\max}=\max_{j,r}\widehat\tau_{j,r}.
\]

With correlation multiplier \(m_{\mathrm{corr}}>0\) and minimum block length \(L_{\min}\), the nominal correlation-aware block length is

\[
L_{\mathrm{corr}}
=
\max\!\left(1,\left\lceil m_{\mathrm{corr}}\tau_{\max}\right\rceil\right),
\qquad
L=\max(L_{\min},L_{\mathrm{corr}}).
\]

All lengths are in **stored-frame units**. If frames are written every \(\Delta t_{\mathrm{save}}\), a block of \(L\) frames corresponds approximately to \(L\Delta t_{\mathrm{save}}\) of trajectory time.

For a contiguous eligible run of \(n>L\) frames, `mdstats` does not drop a remainder. Instead,

\[
B=\max\!\left(1,\left\lfloor\frac{n}{L}\right\rfloor\right)
\]

blocks are formed. Writing \(n=qB+r\), the first \(r\) blocks contain \(q+1\) frames and the remaining blocks contain \(q\). Every eligible frame is retained exactly once.

> **Current default policy binding.** The current neutral implementation uses \(m_{\mathrm{corr}}=2\) and \(L_{\min}=32\) stored frames. Its default autocorrelation channels are energy per atom, force-component RMS, pressure, instantaneous temperature, and cell volume, when each channel is available for the run; if none of those channels is complete, cell volume is used as the fallback observable. These are current configurable policy/default bindings, not universal physical constants.

### 2.3 What exactly is a correlation unit?

The block plan is only the first step. The neutral data-preparation layer then enforces the current physical **condition identity**

\[
\kappa(x)=
(\text{composition},\text{temperature condition},\text{strain class},
\text{regime},\text{user labels}).
\]

A final unit cannot cross a condition boundary. Blocks are therefore split where this identity changes. Conversely, if a recognized protected event spans neighboring blocks, those blocks are merged so the entire event remains indivisible. A protected event that itself crosses a declared condition boundary is treated as inconsistent input rather than silently split.

The resulting **correlation unit** is therefore an indivisible, contiguous, complete-frame interval tied to one source run and one condition, constructed from autocorrelation-aware block evidence and enlarged when necessary to preserve a protected event. Each eligible frame belongs to exactly one such unit.

A correlation unit is **not automatically claimed to be an independent physical realization**. `mdstats` separately records the strongest available independence evidence: independent replicas, independent structural realizations, independent thermodynamic runs, purged temporal blocks, slow-state-not-decorrelated evidence, or insufficient-independence evidence. This distinction prevents a finite temporal spacing rule from being mistaken for proof of full phase-space decorrelation.

## 3. Correlation units are not the same as protected components

Correlation-unit membership is only one way that two frames can be scientifically unsafe to separate. Let the protected relation be the union

\[
R_{\mathrm{prot}}
=R_{\mathrm{corr}}
\cup R_{\mathrm{dup}}
\cup R_{\mathrm{event}}
\cup R_{\mathrm{replica}}
\cup R_{\mathrm{realization}},
\]

where the terms represent, respectively,

1. membership in the same correlation unit;
2. exact-geometry duplication;
3. membership in the same protected event window;
4. condition-scoped replica lineage across distinct runs; and
5. condition-scoped structural-realization lineage across distinct runs.

The actual no-split relation is the transitive closure

\[
\sim_{\mathrm{prot}}
=\operatorname{TC}(R_{\mathrm{prot}}).
\]

Thus, if frame \(a\) shares a correlation unit with \(b\), and \(b\) is an exact duplicate of \(c\), then \(a,b,c\) belong to one indivisible protected component even if no direct \(a\)-\(c\) relation was recorded.

> **Two different objects are used later.** The **correlation unit** is the autocorrelation-aware temporal/statistical block and is the unit balanced by the coverage measure. The larger **protected component** is the connected component of all accepted no-split relations and is the object that cannot be divided across incompatible evidence roles or across the \(P_{\mathrm{train}}/M_3\) boundary.

## 4. From protected units to the exact `P_train` population

### 4.1 Outer evidence roles are assigned before target selection

The neutral statistical substrate assigns complete units to protected outer roles rather than splitting individual frames. These roles include development, outer monitor, uncertainty calibration, locked interpolation test, purge, and exclusion.

The current construction deterministically places monitor/calibration/locked anchors where the available conditions support them, purges neighboring same-run units according to the role policy, and leaves the remaining admissible units as **DEVELOPMENT** evidence. This ensures that outer evidence is separated before target-size membership is selected.

Only exact eligible DEVELOPMENT frames with canonical training labels enter

\[
U_{\mathrm{size}}.
\]

The target-training selector never draws from the outer monitor, calibration, locked-test, purged, or excluded populations.

### 4.2 Exact protected split into `P_train` and `M3`

The protected relation is projected onto \(U_{\mathrm{size}}\), and its connected components are computed. Those components are indivisible allocation units.

`mdstats` must construct an evaluation reserve containing **exactly** \(M_3\) frames. If protected component \(j\) contains \(w_j\) frames, the allocation is an exact 0/1 subset-sum problem. With reachable cardinalities \(R_j\),

\[
R_0=\{0\},
\qquad
R_j
=
R_{j-1}
\cup
\{r+w_j:r\in R_{j-1},\ r+w_j\le M_3\}.
\]

Components are processed in a deterministic order that balances component size and represented condition identity; the accepted first-predecessor rule fixes one exact membership when several solutions exist. If exact \(M_3\) cardinality is impossible without splitting a protected component, preparation fails rather than weakening the protection rule.

The selected components form \(M_3\); their complement forms

\[
P_{\mathrm{train}}=U_{\mathrm{size}}\setminus M_3.
\]

This is the frozen target-order domain. From this point onward, all selector-specific feature fitting, scaling, neighborhoods, coverage, and ordering are constructed on exact \(P_{\mathrm{train}}\) only.

## 5. One nested training-set ladder

Let

\[
P_{\mathrm{train}}=\{x_1,\ldots,x_n\}.
\]

`mdstats` constructs one deterministic permutation

\[
\pi_{\mathrm{train}}
=
\bigl(x_{(1)},x_{(2)},\ldots,x_{(n)}\bigr),
\]

and defines the training set of size \(N\) as

\[
T_N=\pi_{\mathrm{train}}[:N].
\]

Therefore,

\[
N_a<N_b
\quad\Longrightarrow\quad
T_{N_a}\subset T_{N_b}.
\]

The learning-curve experiment is nested: increasing \(N\) retains all earlier configurations and adds new ones chosen to improve physical representation. No independent per-\(N\) selector is run.

## 6. Multi-view construction of the physical feature space

For atomistic data there is no unique scalar notion of "distance between configurations." Two structures can be similar in pair distances but different in angular order; they can have similar geometry but very different forces, pressure, or strain. A single concatenated descriptor can also mix quantities with unrelated physical meanings and scales.

`mdstats` therefore uses a **multi-view representation**. For each required feature family \(m\), a configuration \(x\) is mapped to its own feature vector

\[
\mathbf f_m(x)
=
\bigl(f_{m1}(x),\ldots,f_{md_m}(x)\bigr).
\]

| Physical view | Representative information |
| --- | --- |
| Local structure | Pair distance, radial environment, coordination, connectivity, chemical environment, local density, angular environment, and orientational order. |
| Pair geometry | Minimum pair distance, mean and maximum nearest-neighbor distance, and coordination statistics for applicable pair rules. |
| Target response | Force statistics, energy per atom, temperature, hydrostatic/deviatoric strain, pressure, and stress-deviator magnitude when defined. |
| Profile-specific evidence | Accepted continuous selection features and discrete environment classes supplied by an active material/profile provider. |
| Foundation-model weakness | Energy and force residuals only when target-size training itself uses an authenticated frozen foundation model. |

Each family is interpreted independently; one well-covered physical view cannot compensate for a poorly covered one.

### 6.1 Robust scaling inside each family

For feature coordinate \(j\), a robust scale \(s_j\) is taken from the interquartile range when non-degenerate,

\[
s_j=Q_j(0.75)-Q_j(0.25),
\]

with broader-quantile and variance-based fallbacks for nearly constant coordinates. The normalized family distance is

\[
d_m(a,b)=
\sqrt{
\frac{1}{d_m}
\sum_{j=1}^{d_m}
\left(
\frac{f_{mj}(a)-f_{mj}(b)}{s_j}
\right)^2
}.
\]

The factor \(1/d_m\) prevents a family from gaining influence merely by having more coordinates.

## 7. Coverage as a local covering problem

For a witness \(w\) in feature family \(m\), `mdstats` defines an adaptive local radius \(r_m(w)\): the smallest distance containing approximately

\[
\beta=\frac{1}{128}
\]

of the remaining correlation-balanced reference mass. Dense regions therefore receive smaller neighborhoods and sparse regions larger ones.

A candidate configuration \(c\) represents witness \(w\) when

\[
A_m(w,c)=1
\quad\Longleftrightarrow\quad
d_m(w,c)\le r_m(w),
\]

up to the prescribed numerical tolerance. For selected set \(S\),

\[
n_m(w;S)=\sum_{c\in S}A_m(w,c).
\]

The witness is covered when \(n_m(w;S)>0\).

### 7.1 Correlation-balanced reference mass

Now the earlier correlation-unit construction becomes directly relevant. Let \(g(w)\) be the P1 correlation-unit identity of witness \(w\), let \(G_m\) be the represented units in family \(m\), and let \(n_{m,g}\) be the number of participating witnesses from unit \(g\). The witness weight is

\[
\omega_m(w)
=
\frac{1}{|G_m|\,n_{m,g(w)}}.
\]

Hence every represented correlation unit receives exactly the same total mass in that feature family, regardless of how many stored frames it contains. Frames inside a unit divide that mass.

The covered mass is

\[
C_m(S)
=
\sum_{w\in W_m}
\omega_m(w)\,
\mathbf 1\!\left[n_m(w;S)>0\right].
\]

The hard baseline is

\[
\boxed{
C_m(S)\ge 0.95
\qquad
\text{for every required feature family}
}.
\]

Thus 95% coverage means that at least 95% of the **correlation-balanced reference mass** in each physical view has a selected representative inside its local neighborhood. It does not mean 95% model accuracy, 95% confidence, or 95% of raw trajectory frames.

### 7.2 Protecting physically important tails and discrete support

High mass coverage alone can miss important extremes. For an extent-bearing channel \(j\), define

\[
L_j=Q_j(0.01),
\qquad
U_j=Q_j(0.99).
\]

The selected set must satisfy

\[
\min_{x\in S}f_j(x)\le L_j,
\qquad
\max_{x\in S}f_j(x)\ge U_j.
\]

Discrete **hard support obligations** additionally require representation of applicable thermodynamic conditions, structural-event classes, active profile environment classes, both extent sides, and each represented current P1 correlation unit. These requirements cannot be traded away for better average coverage elsewhere.

## 8. How coverage is achieved algorithmically

The selector builds \(\pi_{\mathrm{train}}\) one configuration at a time. For candidate \(c\), the newly covered mass in family \(m\) is

\[
G_m(c)
=
\sum_{\substack{w:\,A_m(w,c)=1\\n_m(w;S)=0}}
\omega_m(w).
\]

A large \(G_m(c)\) means that \(c\) fills a genuine hole in the current representation.

### 8.1 Stage 1: satisfy obligations and fill the weakest-covered view

While any hard obligation is unsatisfied or any required family has \(C_m<0.95\), candidates are prioritized lexicographically to:

1. satisfy as many currently missing hard obligations as possible;
2. maximize new coverage in the least-covered required feature family;
3. maximize new coverage summed over all families;
4. favor correlation units currently underrepresented in the prefix;
5. prefer broader representative utility and sparse diversity; and
6. use stable frame identity only as the final deterministic tie-breaker.

The algorithm is therefore **bottleneck driven**: a well-covered family cannot compensate for a poorly covered family.

### 8.2 Stage 2: densify the covered manifold

After all hard requirements and family thresholds pass, selection continues using diminishing-return representative utility

\[
R(c)
=
\sum_m\sum_{w:A_m(w,c)=1}
\frac{\omega_m(w)}{n_m(w;S)+1}.
\]

The first representative of a region is most valuable; the second is still useful; additional representatives contribute progressively less. Selection therefore changes smoothly from filling missing regions to increasing sampling density over the already covered physical manifold.

## 9. Configured sizes, qualification, and physical interpretation

Requested target sizes \(N_1<N_2<\cdots<N_K\) are prefixes of the same master order. Limited deterministic repair may alter only the newly added shell near a configured boundary; earlier configured prefixes remain immutable.

Each configured prefix is then independently qualified. It may enter target-size model training only if the exact prefix exists, required labels are usable, every required feature family passes coverage, all required lower/upper extents are represented, and all hard support obligations reach their minima.

The method therefore constructs an increasingly fine **cover of the accessible training population** while preserving leakage control upstream. A useful configuration does at least one of three things: supplies mandatory support, covers a previously unrepresented region, or increases representation density in a sparsely represented region.

Three quantities must remain distinct:

\[
\boxed{
\text{number of configurations}
\;\neq\;
\text{coverage of physical variation}
\;\neq\;
\text{MLFF prediction accuracy}
}.
\]

Coverage is a property of training-set membership. Prediction accuracy is measured later on independent evaluation evidence. The resulting experiment is therefore:

> *As the number of training configurations increases, while protected dependence is respected and multi-view physical coverage remains balanced, how much additional predictive accuracy does the MLFF gain?*

## 10. Authority and external scientific context

This summary is explanatory and non-authoritative. The upstream statistical/data-preparation semantics and the target-order semantics are owned by the accepted/current authority chain, principally:

- `docs/methods/mlff_scientific_method.md` and `docs/methods/mlff_numerical_algorithmic_method.md` for correlation, protected dependence, evidence roles, and the exact \(U_{\mathrm{size}}\to P_{\mathrm{train}}+M_3\) split;
- `docs/methods/mlff_target_training_order_scientific_method.md` and `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md` for multi-view coverage, obligations, ordering, repair, and qualification;
- `docs/specs/sampling/shared_sampling_primitives_spec.md` and `docs/specs/training_data/mlff_data5_partition_roles_spec.md` for the implemented sampling/partition contracts summarized here.

External literature provides scientific context but does **not** define the project-specific `mdstats` thresholds, feature families, split rules, or ordering semantics.

1. H. Flyvbjerg and H. G. Petersen, "Error Estimates on Averages of Correlated Data," *Journal of Chemical Physics* **91**, 461-466 (1989). https://doi.org/10.1063/1.457480
2. C. J. Geyer, "Practical Markov Chain Monte Carlo," *Statistical Science* **7**, 473-483 (1992). https://doi.org/10.1214/ss/1177011137
3. J. Behler and M. Parrinello, "Generalized Neural-Network Representation of High-Dimensional Potential-Energy Surfaces," *Physical Review Letters* **98**, 146401 (2007). https://doi.org/10.1103/PhysRevLett.98.146401
4. A. P. Bartok, R. Kondor, and G. Csanyi, "On representing chemical environments," *Physical Review B* **87**, 184115 (2013). https://doi.org/10.1103/PhysRevB.87.184115
5. V. L. Deringer, M. A. Caro, and G. Csanyi, "Machine Learning Interatomic Potentials as Emerging Tools for Materials Science," *Advanced Materials* **31**, 1902765 (2019). https://doi.org/10.1002/adma.201902765
6. E. V. Podryabinkin and A. V. Shapeev, "Active learning of linearly parametrized interatomic potentials," *Computational Materials Science* **140**, 171-180 (2017). https://doi.org/10.1016/j.commatsci.2017.08.031