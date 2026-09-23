# Multi-View Coverage Construction of MLFF Training-Set Size Ladders in `mdstats`

*A concise method paper for a physics audience*

**Central idea.** Molecular-dynamics trajectories contain many correlated and physically redundant frames. `mdstats` therefore does not choose training configurations by uniform subsampling. It describes the frozen training population through several complementary physical feature spaces and constructs one deterministic ordering whose prefixes progressively cover those spaces. A configuration is useful when it represents a region that is not yet adequately represented.

## 1. Purpose and notation

Let

[
P_{mathrm{train}}={x_1,ldots,x_n}
]

be the complete population of configurations already assigned to target-model training by the upstream data split. This population is frozen before target-size model training begins. Held-out evaluation data, later cross-validation results, and outcomes of candidate model training do not influence membership selection.

The size ladder is not produced by running a separate selector for every requested size. Instead, `mdstats` constructs one deterministic permutation

[
pi_{mathrm{train}}=igl(x_{(1)},x_{(2)},ldots,x_{(n)}igr),
]

and defines the training set of size (N) as the prefix

[
T_N=pi_{mathrm{train}}[:N].
]

Hence, for (N_a<N_b),

[
T_{N_a}subset T_{N_b}.
]

The learning-curve experiment is therefore nested: increasing (N) retains all earlier configurations and adds new ones chosen to improve representation of the available training population.

## 2. Why one geometric descriptor is not enough

For atomistic data there is no unique scalar notion of "distance between configurations." Two structures can be similar in pair distances but different in angular order; they can have similar geometry but very different forces, pressure, or strain. A single concatenated descriptor can also mix quantities with unrelated physical meanings and scales.

`mdstats` therefore uses a **multi-view representation**. For each required feature family (m), a configuration (x) is mapped to its own feature vector

[
mathbf f_m(x)=igl(f_{m1}(x),ldots,f_{md_m}(x)igr).
]

Each family is interpreted independently.

| Physical view | Representative information |
| --- | --- |
| Local structure | Pair distance, radial environment, coordination, connectivity, chemical environment, local density, angular environment, and orientational order. |
| Pair geometry | Minimum pair distance, mean nearest-neighbor distance, maximum nearest-neighbor distance, and coordination statistics for applicable pair rules. |
| Target response | Force statistics, energy per atom, temperature, hydrostatic and deviatoric strain, pressure, and stress-deviator magnitude when defined. |
| Profile-specific evidence | Accepted continuous selection features and discrete environment classes when an active material/profile provider supplies them. |
| Foundation-model weakness | Energy and force residuals when the target-size protocol itself uses an authenticated frozen foundation model. |

This separation is important: the selector asks whether the chosen subset represents the population in **each physically meaningful view**, rather than assuming that one global Euclidean distance captures all relevant variation.

### 2.1 Robust scaling inside each feature family

Coordinates within a family may have different magnitudes and units. For feature coordinate (j), `mdstats` determines a robust scale (s_j), using the interquartile range when it is non-degenerate,

[
s_j=Q_j(0.75)-Q_j(0.25),
]

with broader-quantile and variance-based fallbacks for nearly constant coordinates.

The normalized distance within family (m) is

[
d_m(a,b)=
sqrt{
rac{1}{d_m}
sum_{j=1}^{d_m}
left(
rac{f_{mj}(a)-f_{mj}(b)}{s_j}
ight)^2
}.
]

The factor (1/d_m) prevents a family from becoming more influential merely because it contains more coordinates. Constant optional scalar features are omitted because they contain no discriminatory information.

## 3. Coverage as a local covering problem

The key question is not whether the selected configurations are globally far apart. It is whether the selected set supplies a representative for most of the physical states present in (P_{mathrm{train}}).

For a reference configuration, or **witness**, (w) in feature family (m), `mdstats` defines a local radius (r_m(w)). The radius is adaptive: it is the smallest distance that contains approximately

[
eta=rac{1}{128}
]

of the remaining correlation-balanced reference mass around (w). Dense regions therefore receive smaller neighborhoods and sparse regions larger ones.

A candidate configuration (c) represents witness (w) in family (m) when

[
A_m(w,c)=1
quadLongleftrightarrowquad
d_m(w,c)le r_m(w),
]

up to the prescribed small numerical tolerance. For a selected set (S), define the number of selected representatives of (w) as

[
n_m(w;S)=sum_{cin S}A_m(w,c).
]

The witness is covered whenever (n_m(w;S)>0).

### 3.1 Correlation-balanced reference mass

Molecular-dynamics trajectories often oversample slowly evolving regions simply because many adjacent frames were saved there. Counting every frame equally would make those regions dominate the coverage measure.

The upstream data preparation therefore assigns frames to correlation units. Let (g(w)) denote the correlation unit of witness (w), let (G_m) be the represented correlation units in family (m), and let (n_{m,g}) be the number of participating witnesses from unit (g). The witness weight is

[
omega_m(w)=rac{1}{|G_m|,n_{m,g(w)}}.
]

Thus every represented correlation unit receives the same total mass, while its frames share that mass. This turns coverage into a measure of represented physical population rather than stored-frame frequency.

The covered mass of selected set (S) in family (m) is

[
C_m(S)=
sum_{win W_m}
omega_m(w),mathbf 1!left[n_m(w;S)>0ight].
]

The required baseline is

[
oxed{C_m(S)ge 0.95qquad	ext{for every required feature family}.}
]

In words, at least 95% of the correlation-balanced reference population in every physical view must have a selected representative inside its local neighborhood.

> **What 95% coverage does and does not mean.** It means that 95% of the weighted training population is locally represented in a given feature family. It does **not** mean 95% model accuracy, 95% confidence, or 95% of raw trajectory frames.

### 3.2 Protecting the tails of important distributions

High mass coverage alone can miss physically important extremes. For selected extent-bearing channels, `mdstats` therefore also requires support of the lower and upper tails.

For channel (j),

[
L_j=Q_j(0.01),
qquad
U_j=Q_j(0.99).
]

The selected set must satisfy

[
min_{xin S} f_j(x)le L_j,
qquad
max_{xin S} f_j(x)ge U_j.
]

The method therefore protects, for example, rare short or long distances, unusual coordination, large-force states, or extreme strain/stress values when those channels are part of the active evidence.

Discrete requirements are handled by analogous **hard support obligations**: represented thermodynamic conditions, structural-event classes, profile environment classes, protected correlation units, and explicit project-defined categories can require one or more selected members. These obligations cannot be traded away in exchange for better average coverage elsewhere.

## 4. How coverage is achieved algorithmically

The selector builds (pi_{mathrm{train}}) one configuration at a time. At each step, it evaluates what each remaining candidate would add to the current prefix (S).

For candidate (c), the amount of previously uncovered mass that it would newly cover in family (m) is

[
G_m(c)=
sum_{substack{w:,A_m(w,c)=1\n_m(w;S)=0}}
omega_m(w).
]

A large (G_m(c)) means that (c) fills a genuine hole in the current representation of that family.

### 4.1 Stage 1: satisfy missing requirements and fill the weakest-covered view

While any hard obligation is unsatisfied or any required family has (C_m<0.95), candidates are prioritized lexicographically:

1. satisfy as many currently missing hard obligations as possible;
2. identify the least-covered required feature family and maximize new coverage in that family;
3. maximize new coverage summed over all families;
4. favor correlation units that are currently underrepresented in the selected prefix;
5. prefer broader representative utility and sparse diversity;
6. use a stable frame identity only as the final deterministic tie-breaker.

The important point is that the algorithm is **bottleneck driven**: it preferentially improves the physical view that is currently furthest from adequate coverage. A family that is already well represented cannot compensate for another family that remains poorly represented.

### 4.2 Stage 2: densify the already covered manifold

After all hard requirements and 95% family-coverage thresholds are satisfied, selection continues using a diminishing-returns representative utility

[
R(c)=
sum_msum_{w:A_m(w,c)=1}
rac{omega_m(w)}{n_m(w;S)+1}.
]

The denominator gives the intended behavior:

- representing an uncovered witness is maximally useful;
- providing a second representative is still useful, but less so;
- adding another representative to an already dense region contributes progressively less.

Thus the ordering naturally changes from *covering missing regions* to *increasing sampling density across the covered physical manifold*.

Conceptually, the construction is

```text
Frozen P_train
    -> physical feature families f_m(x)
    -> adaptive local neighborhoods A_m(w,c)
    -> coverage and hard-support state C_m(S)
    -> coverage-progressive candidate selection
    -> one complete master order pi_train
    -> nested training sets T_N = pi_train[:N].
```

## 5. Configured size ladder and independent qualification

The requested target sizes (N_1<N_2<cdots<N_K) are read from the same master order. Near a configured boundary, a limited deterministic repair may replace a configuration only within the newly added shell. Earlier configured prefixes remain immutable. A replacement is admissible only if it preserves hard obligations, does not reduce required-family coverage, and improves the accepted global representation objective.

Each configured prefix is then independently re-evaluated from the underlying coverage definitions. A prefix may enter the target-size learning experiment only if:

- the exact prefix exists and its training labels are usable;
- every required feature family satisfies (C_mge0.95);
- every required lower/upper extent is represented; and
- every hard support obligation satisfies its minimum count.

Because the prefixes are nested and these criteria are positive support conditions, qualification is monotone under fixed definitions: a larger prefix cannot legitimately lose coverage that a smaller prefix already possessed.

## 6. Physical interpretation

The procedure can be viewed as constructing an increasingly fine **cover of the accessible training manifold**. The word *manifold* here should not be read as implying one exact low-dimensional mathematical surface. Rather, the population is examined through several complementary projections corresponding to distinct physically meaningful observables and structural descriptors.

A useful training configuration therefore does at least one of three things:

1. supplies mandatory support for a physical condition or rare category;
2. covers a region of one or more feature spaces that has no adequate representative yet; or
3. increases representation density in regions that are covered but still sparsely represented.

This construction deliberately keeps three quantities separate:

[
oxed{
	ext{number of configurations}
;
eq;
	ext{coverage of physical variation}
;
eq;
	ext{MLFF prediction accuracy}
}
]

Coverage is a property of the *training-set membership*. It asks whether the available training population is physically represented. Prediction accuracy is measured later, after training, using the independent evaluation procedure. The coverage selector therefore does not decide which target size gives the best machine-learned force field (MLFF); it ensures that the learning-curve comparison is scientifically meaningful.

The resulting experiment can be stated succinctly:

> *As the number of training configurations increases, while maintaining nested membership and balanced multi-view coverage of the available physical population, how much additional predictive accuracy does the MLFF gain?*

That is the role of the `mdstats` target-training ordering: to make increasing (N) correspond primarily to adding new physical information and progressively finer representation, rather than merely adding more correlated trajectory frames.

## 7. Authority and external context

This summary is explanatory and non-authoritative. The exact `mdstats` scientific and numerical definitions are owned by:

- `docs/methods/mlff_target_training_order_scientific_method.md`;
- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`.

The following external sources provide broader scientific context for machine-learned interatomic potentials, atomic-environment representations, and data-selection strategies. They do **not** define the project-specific `mdstats` coverage threshold, adaptive-neighborhood mass, hard obligations, or ordering rules.

1. J. Behler and M. Parrinello, "Generalized Neural-Network Representation of High-Dimensional Potential-Energy Surfaces," *Physical Review Letters* **98**, 146401 (2007). https://doi.org/10.1103/PhysRevLett.98.146401
2. A. P. Bartok, R. Kondor, and G. Csanyi, "On representing chemical environments," *Physical Review B* **87**, 184115 (2013). https://doi.org/10.1103/PhysRevB.87.184115
3. V. L. Deringer, M. A. Caro, and G. Csanyi, "Machine Learning Interatomic Potentials as Emerging Tools for Materials Science," *Advanced Materials* **31**, 1902765 (2019). https://doi.org/10.1002/adma.201902765
4. E. V. Podryabinkin and A. V. Shapeev, "Active learning of linearly parametrized interatomic potentials," *Computational Materials Science* **140**, 171-180 (2017). https://doi.org/10.1016/j.commatsci.2017.08.031
