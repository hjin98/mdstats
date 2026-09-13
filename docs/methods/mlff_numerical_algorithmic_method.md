---
title: "mdstats MLFF Numerical Algorithmic Method"
artifact_level: "D2 numerical algorithm design"
status: "reconstructed current method - proposed for human review"
reconstructed_against_commit: "9fd82b0ed40990d56716a393aa3f7db0a2ff44d0"
date: "2026-09-13"
---

# mdstats MLFF Numerical Algorithmic Method

## 1. Purpose and authority

This paper specifies the D2 numerical algorithms used to realize the scientific formulation in `mlff_scientific_method.md`. It reconstructs numerical authority that historically lived partly in the MLFF architecture manual, implementation specifications, accepted workplans, and executable owners.

D1 determines what scientific comparison is meaningful. D2 determines how that comparison is computed without changing its meaning. D3 architecture determines where these algorithms live, how records depend on one another, and how execution is orchestrated. Exact schema names, configuration defaults, runtime paths, and versioned serialization rules remain specification-owned.

The core numerical invariants are:

- target-size candidates are exact nested prefixes of one deterministic order;
- protected statistical relations are resolved before the target-training/evaluation split;
- one common fitted preparation is shared across candidate sizes and optimizer seeds;
- target-size optimizer progress is normalized by realized target updates per epoch;
- each `(N, optimizer_seed)` follows one continuous trajectory through exact fidelity boundaries;
- target-force RMSE is evaluated on exact nested evaluation memberships;
- the reducer consumes complete authenticated seed matrices and never silently averages a successful subset;
- practical equivalence prefers the smaller candidate, while a materially superior configured ceiling remains selectable with an explicit nonconvergence diagnostic; and
- post-selection cross-validation and final production are new training lineages rather than continuations of screening checkpoints.

## 2. Inputs and deterministic identity

The numerical pipeline consumes accepted current-generation source/frame authority, the neutral statistical substrate and its protected split relations, target-size policy, fitted-preparation policy, foundation-model identity, objective/weight policies, and experiment configuration.

Every authoritative derived object has deterministic content identity. Content hashes authenticate exact inputs and descendants; they do not make a stochastic numerical operation deterministic by themselves. When stochastic optimization is part of the method, its seed population is explicit scientific input and every result remains bound to its seed and protocol identity.

Historical records may be readable for diagnosis but cannot authorize current execution when their numerical semantics differ from the current method.

## 3. Construction of the target-size population and split

### 3.1 Eligible population

Let `U_size` be the ordered set of current development frames that are both eligible and backed by usable canonical labels. Frames without usable training labels are excluded from the target-size experiment before candidate construction.

### 3.2 Protected-relation graph

Current P1 authority supplies pairwise or grouped relations representing observations that must not be divided across `P_train` and the model-selection reserve. The target-size split owner forms the transitive connected components of this relation graph.

If a protected relation connects `a` to `b` and `b` to `c`, all three belong to one indivisible component even if no direct `a-c` relation was stored. This avoids pairwise-only leakage checks that can miss transitive dependence.

### 3.3 Exact reserve allocation

The requested largest evaluation reserve has cardinality `M3`. Components are deterministically ordered using current redundancy/condition evidence, and an exact subset of complete components is chosen whose total cardinality is exactly `M3`.

The implementation uses exact subset-sum dynamic programming rather than a greedy approximation. In abstract form, for component sizes `w_1,...,w_C`, define reachable sums

$$
R_0=\{0\}, \qquad R_j=R_{j-1}\cup\{r+w_j:r\in R_{j-1}\},
$$

with states above `M3` discarded. Predecessor information is retained to reconstruct the deterministic accepted subset when `M3` is reachable.

If no protected-component allocation sums exactly to `M3`, construction fails. D2 does not split a protected component or silently change the requested scientific reserve.

A straightforward bounded implementation costs `O(C M3)` state transitions and `O(M3)` to `O(C M3)` storage depending on predecessor representation; the current realization is constrained by exactness rather than by an approximate bin-packing objective.

The complement is `P_train`, and exact disjointness is revalidated after construction.

## 4. Canonical training and evaluation orders

### 4.1 Priority evidence normalization

Optional ordering evidence is a mapping from every frame UID in the relevant population to a finite scalar or finite vector. Coverage must be exact: missing, foreign, malformed, or non-finite evidence fails construction rather than receiving an implicit default.

Priority evidence affects order only. It does not itself create candidate eligibility constraints.

### 4.2 Condition-balanced deterministic ordering

For either the training pool or evaluation reserve, frames are grouped by the current condition key. Inside each condition bucket, larger priority coordinates sort first and the immutable frame UID is the final deterministic tie breaker. The global order is then formed by round-robin traversal of the sorted condition buckets.

This produces one stable permutation while preventing a large represented condition from occupying the entire front of the order merely because it contains more frames.

The target training order is

$$
\pi_{train}=(x_1,\ldots,x_{|P_{train}|}),
$$

and each candidate is the exact prefix

$$
T_N=(x_1,\ldots,x_N).
$$

The evaluation order `pi_eval` is an exact permutation of `M3`; configured evaluation memberships are likewise exact prefixes. Consequently `M1 subset M2 subset M3` by construction.

Membership digests include the parent-order identity, requested cardinality, and ordered frame identities so that a membership cannot be silently substituted under the same `N` or `M`.

### 4.3 Candidate qualification

For each configured candidate size `N`, qualification is derived from the exact prefix and the declared hard-support policy:

$$
Q(N)=\mathrm{prefix\ exists}\land\mathrm{labels\ usable}\land
\bigwedge_j c_j(T_N)\ge q_j,
$$

where `q_j` is the required minimum for hard-support obligation `j` and `c_j` is its exact matched count.

Qualification never reorders, repairs, swaps, or expands the prefix. Coverage, novelty, residual, balance, or other diagnostic quantities can influence the canonical priority order only through their declared ordering role; they do not become hidden qualification gates.

Because prefixes are nested, any hard-support count defined by membership inclusion is monotone nondecreasing with `N`. A contradictory non-monotone qualification lineage is therefore an invariant failure.

The automatic funnel requires at least three qualified candidates before numerical training begins.

## 5. Common fitted preparation

### 5.1 Candidate-independent fit

One `TargetSizeCommonPreparation` is computed before any `(N,seed)` trajectory begins. It is `N`-neutral and seed-neutral. All candidate preparations are projections of that common fitted state onto exact `T_N` memberships.

This is a numerical control against confounding: fitted preprocessing cannot change merely because `N` changed.

### 5.2 Atomic reference-energy fit

Let `C` be the configuration-by-element count matrix and `y` the authorized energy target. For a from-scratch fit the elemental reference vector `e` is estimated by the configured least-squares policy, conceptually

$$
\hat e=\arg\min_e \|Ce-y\|_2^2 + \lambda\|e-e_{prior}\|_2^2,
$$

with the prior term present only when the configured policy requests it.

For foundation-model fine-tuning, the production scientific mode fits the residual energy relative to the foundation model. If `y_fnd` is the foundation prediction and `e_fnd` its elemental reference vector, solve for a correction `delta e` using

$$
r=y-y_{fnd},\qquad
\widehat{\delta e}=\arg\min_{\delta e}\|C\delta e-r\|_2^2+\lambda\|\delta e-\delta e_{prior}\|_2^2,
$$

then use

$$
e_{target}=e_{fnd}+\widehat{\delta e}.
$$

The implementation records rank, singular-value evidence, null-space dimension, residual RMSE/MAE/maximum error, and rank-deficiency state. A rank-deficient fit is therefore not silently presented as fully identifiable. Whether a fixed-domain rank deficiency is admissible is explicit policy.

Fold-local post-selection fits use only the fold training domain; final production obtains a separate final-training fit.

### 5.3 Objective realization

The numerical loss preserves three multiplicative/selection layers rather than collapsing them:

- global coefficients for energy, force, and stress residual families;
- a positive per-configuration weight; and
- local property masks, normally `1` for present and `0` for absent.

The current MACE realization uses the native weighted energy+forces+stress loss family. A missing property is masked locally; it must not be simulated by changing a global coefficient.

## 6. Target-size optimizer-progress normalization

### 6.1 Problem

With batch size `B`, one nominal epoch contains a different number of target optimizer updates for different candidate sizes. Keeping identical optimizer hyperparameters would therefore change the amount of optimizer evolution per epoch as `N` changes and contaminate the target-size comparison.

### 6.2 Update-count normalization

For reference target size `N_ref`, reference learning rate `LR_ref`, and reference exponential-moving-average decay `beta_ref`, define

$$
U_{ref}=\left\lceil\frac{N_{ref}}{B}\right\rceil,
\qquad
U_N=\left\lceil\frac{N}{B}\right\rceil,
$$

$$
s_N=\frac{U_{ref}}{U_N}.
$$

The target-size screen uses

$$
LR_N=LR_{ref}s_N,
$$

and, when exponential moving average (EMA) is enabled,

$$
\beta_N=\beta_{ref}^{s_N}.
$$

The first relation scales per-update parameter motion inversely with the number of updates in an epoch. The second preserves the intended decay over comparable reference progress because repeated application over `U_N` updates gives

$$
(\beta_N)^{U_N}=\beta_{ref}^{U_{ref}}.
$$

This normalization is specific to the target-size experiment. Ordinary post-selection optimizer defaults are separate protocol authority.

There is no survivor-dependent rescaling, hidden floor/cap, or rung-local reconstruction of the normalized trajectory.

### 6.3 Complete-batch requirement

The ceiling update count is scientifically meaningful only if the execution actually retains the final partial target batch. Target-size execution therefore requires `drop_last=False`, no padding by duplicate target frames, and no distributed sampler path that silently truncates membership. Realized target updates must equal `ceil(N/B)`.

Batch partitioning may be an execution detail only when it preserves the exact target membership, ordering semantics required by the training loader, and the declared update geometry.

## 7. Continuous fidelity trajectories

For every active cell `(N,s)` where `s` is an optimizer seed, training is one continuous model/optimizer trajectory through the configured fidelity boundaries

$$
n_1 < n_2 < n_3.
$$

A survivor at `n_1` continues from the exact authenticated `n_1` state to `n_2`, and likewise to `n_3`. It is not restarted from the foundation model at every rung and is never continued from another candidate size or seed.

The exact completed epoch, model state, optimizer state, normalization policy, common preparation, candidate membership, and execution context are authenticated. A restart resumes only an accepted predecessor state. Unaccepted attempt scratch may be recreated, but accepted scientific progress is immutable evidence.

This distinction is essential: filesystem liveness and cache state are execution concerns; exact model/optimizer trajectory identity is numerical-method authority.

## 8. EVAL2 target-force estimator

At a boundary, the exact checkpoint is evaluated on the exact configured evaluation prefix `M_i`. Let the set contain `K` admitted force components. The estimator is

$$
\mathrm{RMSE}_{F,eV/A}=\sqrt{\frac{1}{K}\sum_{k=1}^{K}(\hat F_k-F_k)^2},
$$

and the stored screen metric is

$$
\mathrm{RMSE}_{F,meV/A}=1000\,\mathrm{RMSE}_{F,eV/A}.
$$

Evaluation may be partitioned into deterministic device batches to bound memory. Chunk width is not scientific identity: exact membership, model state, prediction semantics, and aggregate reduction must be invariant to the chosen valid batch size up to the accepted floating-point equivalence contract.

Non-finite prediction or non-finite target metric is a typed numerical failure, not an infinite score invented after the fact.

## 9. Pure target-size reducer

### 9.1 Boundary evidence matrix

At boundary `j`, the reducer expects one ordered outcome for every pair

$$
(N,s)\in A_j\times S,
$$

where `A_j` is the active candidate set and `S` the configured optimizer-seed set.

Every outcome is bound to the same experiment definition, execution context, exact boundary epoch, and exact evaluation-membership digest. Duplicate, missing, reordered, or foreign evidence makes the comparison insufficient rather than being normalized away.

### 9.2 Per-candidate score

A candidate receives a scalar score only when all required seeds produce valid `TargetSizeBoundaryMetric` outcomes. Its score is the arithmetic mean

$$
\bar E_N=\frac{1}{|S|}\sum_{s\in S}E_{N,s}.
$$

If any seed has an authenticated numerical failure, that candidate is excluded from successful comparison at the boundary; mdstats never computes a favorable mean over the successful subset of seeds.

Typed numerical failure classes include non-finite training model state, non-finite optimizer state, non-finite evaluation prediction, and non-finite target metric.

### 9.3 Practical-equivalence ordering

Given scores `E_N` and tolerance `epsilon`, the reducer repeatedly finds the current best score `E_min`, collects all candidates satisfying

$$
E_N\le E_{min}+\epsilon,
$$

and chooses the smallest `N` among that equivalent set. It then removes that winner and repeats to obtain a total practical-equivalence ordering.

A small floating-point guard is used at the numerical comparison boundary, but the scientific tolerance is the configured `epsilon`, not machine epsilon.

### 9.4 Funnel transitions

The current funnel has a version-independent structural transition:

1. first boundary: retain at most four best practically ordered successful candidates;
2. second boundary: retain the two best successful candidates;
3. terminal boundary: select one candidate.

The exact epoch/evaluation values attached to these three boundaries are policy, not encoded in the transition name.

At the first boundary, the successful comparison count must be sufficient for the configured active set (up to four); later comparisons require two successful finalists. Otherwise the reducer terminates as `insufficient_comparison` rather than fabricating a result.

### 9.5 Terminal configured-ceiling rule

Let `N_max` be the configured maximum size. If it is a successful terminal finalist and

$$
E_{N_{max}}+\epsilon < E_N
$$

for every other successful finalist `N`, then `N_max` is materially superior. It is selected and the terminal result carries the diagnostic that convergence was not demonstrated at the configured ceiling.

Otherwise the first entry in practical-equivalence order is selected, which naturally chooses the smaller finalist whenever its error is within `epsilon` of the best.

This rule is intentionally not a numerical root-finding or asymptotic extrapolation procedure. The algorithm only compares tested candidates.

## 10. Post-selection cross-validation algorithm

After the operator freezes one or more selected `T_N` memberships, each selected size is validated independently.

For each fold:

1. construct the fold training/evaluation split while preserving inherited protected relations and purge rules;
2. derive a checkpoint-monitor subset only from fold-training-eligible evidence;
3. fit all fold-local fitted quantities from the fold training domain;
4. initialize a fresh model/optimizer lineage under the frozen post-selection method;
5. train for the selected cross-validation horizon;
6. choose an admissible checkpoint using only authorized checkpoint-monitor evidence and mandatory integrity/retention constraints; and
7. after checkpoint freeze, evaluate once on the held-out fold.

The held-out fold never supplies an optimization gradient or checkpoint-selection signal. Cross-validation can accept or reject the frozen method but cannot alter `N` or `T_N`.

The complete cross-validation plan, method identity, fold identities, seed policy, checkpoint policy, and effective horizon are authenticated so that a result from a numerically different method cannot authorize final production.

## 11. Final production and replay realization

Final production creates a fresh model/optimizer lineage on the complete selected target membership. Screening and cross-validation checkpoints are evidence, not warm starts for final production.

When true-label replay is enabled, target and replay memberships retain separate identities. Current execution explicitly prevents MACE's hidden target duplication and forces authenticated learning-rate/EMA values through multihead fine-tuning. The executed loss remains the native weighted energy+forces+stress loss.

The current adapter is qualified against `mace-torch==0.3.16`. Because that upstream version contains behavior that would otherwise mutate the declared method—forced `UniversalLoss` in multihead fine-tuning, learning-rate/EMA overrides, implicit target duplication, and target-batch truncation—the mdstats qualified wrapper source-checks the expected upstream shape and narrowly repairs/guards those branches. A different upstream source shape fails closed until requalified.

These version-specific guards are implementation realization of D2 invariants; they are not independent scientific choices.

## 12. Numerical failure, conditioning, and uncertainty semantics

### 12.1 Failure is evidence

The numerical method distinguishes a failed comparison from a poor finite model. Non-finite model/optimizer state and non-finite evaluation results have typed failure identities. Missing or lineage-inconsistent boundary outcomes produce `insufficient_comparison`. Neither class is silently replaced with an arbitrary large error.

### 12.2 Atomic-reference conditioning

Atomic-reference fits report rank and singular-value information because elemental counts may not identify every reference independently. The numerical uncertainty is structural: null-space directions cannot be recovered merely by using a tighter solver tolerance. The policy either admits the fixed-domain rank deficiency with explicit warning/evidence or rejects the fit.

### 12.3 Floating-point and batching equivalence

Device batching, worker count, cache placement, and file-backed storage are execution-realization choices. They are permitted to vary only under an exact or explicitly bounded numerical-equivalence contract. They may not alter membership, sample exposure, candidate ordering, fitted inputs, target-size ranking, or checkpoint admissibility.

### 12.4 Stochastic optimization

Optimizer seeds are explicit samples of training stochasticity. Paired seeds improve comparative control but do not eliminate stochastic uncertainty. Reproducibility therefore means reproducing the same method and seed lineage, not claiming bitwise identity across unsupported hardware/library regimes.

## 13. Complexity and scaling

Ignoring neural-network training cost, principal control-plane operations scale as follows:

- protected-relation connected components: approximately linear in population plus relation edges;
- exact reserve subset-sum: pseudo-polynomial in component count times `M3`;
- canonical ordering: dominated by per-condition sorting, at most `O(N log N)`;
- qualification: linear in the sum of candidate-prefix/obligation inspections in the direct implementation, with monotonic structure available for optimization only if exact semantics are preserved;
- reducer: `O(Boundaries * Candidates * Seeds)` with tiny state relative to training;
- EVAL2: linear in evaluated force components, with bounded device-batch memory; and
- training: dominates computational cost and follows the model's graph/message-passing complexity and configured epoch/update counts.

Performance optimizations are admissible only when they preserve the D1/D2 identities above.

## 14. Verification and falsification oracles

The numerical method is testable through independent invariants rather than only end-to-end success:

- re-derive protected relations from accepted source authority and reject a stale split;
- prove `pi_train` and `pi_eval` are exact permutations of their parent memberships;
- prove every `T_N` and `M_i` is the exact authenticated prefix;
- recompute qualification from the exact prefix and hard-support policy;
- replay reducer history through the pure transition function and require the same final digest;
- prove incomplete/reordered seed matrices fail comparison;
- prove a mixed success/failure seed set is not subset-averaged;
- counterfactually change one scientific identity and require stale descendants to be rejected;
- verify target-size realized batches equal `ceil(N/B)` without target duplication;
- source-qualify the pinned MACE dependency behaviors relied upon by the wrapper;
- verify the native resolved loss and optimizer settings rather than only the requested configuration;
- prove held-out fold labels cannot reach fitted preparation or checkpoint selection; and
- demonstrate chunk-size/resource changes leave scientific outputs invariant under the accepted numerical equivalence contract.

A failure of these oracles is evidence of a D2 or lower-layer conformance defect. If the algorithm itself must change to restore scientific adequacy, D2 is reopened and downstream evidence applicability must be reconsidered.

## 15. Reproducibility contract

A numerical reproduction of a target-size result requires the exact:

- current source/frame and protected-relation authorities;
- `P_train/M3` split;
- `pi_train` and `pi_eval` identities;
- candidate and evaluation prefix memberships;
- common fitted preparation;
- objective, configuration-weight, and atomic-reference policies;
- candidate ladder, hard-support obligations, optimizer seeds, fidelity epochs, and evaluation sizes;
- optimizer normalization reference policy;
- foundation model/head and compatible MACE execution semantics;
- boundary metrics/failures and reducer history; and
- post-selection method/fold identities for any validation claim.

Runtime caches need not be preserved when they are exactly reconstructible from these authorities.

## 16. References

1. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, "MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields," *Advances in Neural Information Processing Systems* **35** (2022); arXiv:2206.07697.
2. H. Flyvbjerg and H. G. Petersen, "Error Estimates on Averages of Correlated Data," *Journal of Chemical Physics* **91**, 461-466 (1989). DOI: 10.1063/1.457480.
3. J. Racine, "Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation," *Journal of Econometrics* **99**, 39-61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
4. D. R. Roberts, V. Bahn, S. Ciuti, et al., "Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure," *Ecography* **40**, 913-929 (2017). DOI: 10.1111/ecog.02881.
5. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, "How to Validate Machine-Learned Interatomic Potentials," *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.

The exact mdstats algorithmic constants and runtime contracts remain in current specifications and authenticated experiment configuration rather than being duplicated as independently tunable values here.
