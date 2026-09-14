---
title: "mdstats MLFF Numerical Algorithmic Method"
artifact_level: "D2 numerical algorithm design"
status: "current normative D2 numerical/algorithmic authority"
reconstructed_against_commit: "9fd82b0ed40990d56716a393aa3f7db0a2ff44d0"
review_date: "2026-09-13"
accepted_date: "2026-09-13"
---

# mdstats MLFF Numerical Algorithmic Method

## 1. Purpose and authority status

This paper reconstructs the D2 numerical method that realizes the scientific formulation in `mlff_scientific_method.md`. It separates numerically meaningful invariants from replaceable software realization so that optimization or refactoring cannot silently change the experiment.

D1 determines what scientific comparison is meaningful. D2 owns estimators, deterministic constructions, fitted numerical models, normalization, reduction, conditioning, stochastic semantics, and numerical-equivalence requirements. D3/D4 own module placement, persistence, process control, dependency adaptation, caches, and runtime scheduling.

**Authority status.** This document is the current normative D2 numerical/algorithmic authority for the MLFF method. It was reconstructed losslessly from the cited current and historical evidence, independently reviewed, and explicitly accepted by the human owner on 2026-09-13. D1 constrains the scientific meaning of this document; D3 architecture and D4 specifications/implementation must realize these numerical semantics without redefining them. Exact schema names, file layouts, configuration defaults, runtime dependency locks, and serialization forms remain D3/D4 authority except where their value changes the numerical method itself.

The core current D2 invariants are:

- canonical geometry/label/condition evidence preserves the declared physical conventions;
- correlated trajectories are blocked with the shared deterministic autocorrelation primitive and protected relations are closed before incompatible allocations;
- pre-order selection evidence and post-order common candidate-training preparation are distinct stages;
- `P_train/M3`, `pi_train`, `pi_eval`, and every candidate/evaluation prefix have one deterministic identity;
- target-size candidates are nested exact prefixes and qualification never repairs membership;
- target-size fitted training state is common across sizes/seeds and candidate projection never refits or renormalizes it;
- optimizer progress is normalized by realized target update count, with the final partial target batch retained;
- each `(N, optimizer_seed)` is one continuous authenticated trajectory through the three configured fidelity boundaries;
- EVAL2 uses exact target-force RMSE over exact evaluation membership;
- the reducer consumes one complete ordered seed matrix and does not average only successful seeds;
- practical equivalence prefers smaller `N`, while a materially superior configured ceiling remains recommendable with explicit nonconvergence evidence;
- post-selection CV and final production are fresh lineages, not continuations of screening trajectories; and
- post-selection replay/checkpoint constraints are method semantics distinct from the target-size screen.

## 2. Canonical source numerical conventions

### 2.1 Occurrence and numerical identity

Source occurrence, geometry, label payload, and labeled-configuration identities are constructed separately. Quantized fingerprints use explicit tolerances owned by the current source/frame specifications. Geometry fingerprints include ordered species, periodic flags, cell, and wrapped fractional coordinates but exclude target labels, so duplicate geometry remains detectable across different source occurrences or label payloads.

A numerically different quantization/tolerance policy changes identity behavior and therefore requires explicit compatibility treatment; an implementation may not silently use floating-point object equality or path identity instead.

### 2.2 Row-vector cells and deformation gradient

For ASE row-vector cells,

$$
\mathbf r_{\text{row}}=\mathbf s_{\text{row}}\mathbf H.
$$

With reference cell `H_0` and current cell `H_t`, the current MLFF strain reconstruction uses

$$
\mathbf F=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

A proper polar decomposition

$$
\mathbf F=\mathbf R\mathbf U
$$

is computed by singular-value decomposition. Reflections, singular cells, or nonpositive stretch singular values are rejected. Derived strain measures include

$$
\boldsymbol\varepsilon_{\text{lin}}=\frac12(\mathbf F+\mathbf F^T)-\mathbf I,
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

Source stress is normalized to the canonical symmetric Cartesian Cauchy-stress representation and internal unit convention. Conversions must preserve sign, Voigt ordering, and tensor-vs-engineering shear semantics. Virial-like quantities remain a distinct channel unless explicitly converted by an accepted owner.

Stress round-trip checks are numerical falsification oracles: a sign reversal, shear-factor error, or Voigt permutation is a D1/D2 correctness failure, not a formatting issue.

### 2.4 Eligibility numerical checks

Eligibility validates finite/nonsingular geometry, atom-count consistency, required label completeness, finite force/energy fields, stress symmetry/finite values when present, and the active electronic-convergence/source-quality gates. Unusual but finite values remain data; the eligibility algorithm must not implement an implicit “typical value” filter.

## 3. Correlated-sampling primitives and neutral statistical units

### 3.1 Exact autocorrelation estimator

The current MLFF neutral substrate reuses the shared `mdstats.sampling` autocorrelation algorithm. For a finite one-dimensional scalar sequence it computes unbiased FFT autocovariance, normalizes to `rho(k)`, and uses Geyer's initial-positive-sequence truncation. Adjacent lag pairs are accumulated while

$$
\rho(2m-1)+\rho(2m)>0.
$$

An unpaired final positive lag may be retained. The integrated time is bounded to the current policy range, with the canonical floor `1/2` stored frame. Constant or insufficient sequences are represented explicitly rather than generating a fabricated long correlation time.

The effective count is

$$
N_{\text{eff}}=\min\left(N,\frac{N}{2\tau_{\text{int}}}\right).
$$

No autocorrelation is computed across a source gap, continuation reset, or excluded interval.

### 3.2 Complete-frame block length

For every configured observable and contiguous run, estimate `tau`. Let

$$
\tau_{\max}=\max_{j,r}\tau_{j,r}.
$$

The correlation-derived block target is

$$
L_{\text{corr}}=\max\left(1,\left\lceil m\tau_{\max}\right\rceil\right),
$$

and the resolved target is

$$
L=\max(L_{\min},L_{\text{corr}}),
$$

unless an explicit accepted override is in force. A short override is recorded as an adequacy limitation rather than silently treated as decorrelated support.

For a contiguous run longer than `L`, the balanced all-frame split retains every eligible frame. No remainder or tail is dropped.

### 3.3 Protected event merge and relation closure

Full-resolution event windows are constructed before ordinary thinning. When an event crosses candidate block boundaries, the affected blocks are merged before role allocation so the protected event remains indivisible.

Current split-exclusion evidence contains five relation families:

1. correlation-unit membership;
2. exact geometry-duplicate membership;
3. protected-event membership;
4. condition-scoped replica lineage across distinct runs; and
5. condition-scoped structural-realization lineage across distinct runs.

The canonical P1 relation owner projects these relations to a requested frame universe and computes their transitive connected components. P2 consumes those components; it does not reconstruct protected relations from raw provenance or model evidence.

### 3.4 Neutrality of the target-size substrate

The current neutral condition key contains reduced formula, temperature condition, strain class, regime, and optional user labels. It does not contain the retired `label_domain_id` partition axis, and the neutral statistical base constructs no pre-target-size cross-validation plan.

This does not remove upstream label compatibility. It removes compatibility-domain and preselection-CV fan-out from the target-size algorithm.

## 4. Pre-order selection evidence versus common training preparation

### 4.1 Pre-order evidence

The canonical target order may consume candidate-independent priority vectors derived from authorized descriptor, difficulty, diversity, condition, event, environment, or other accepted selection evidence. Any fitted transform or metric used to produce this evidence is fitted before the order on its authorized development domain and must not inspect downstream held-out/calibration/locked labels.

Numerically, the P2 ordering owner receives either:

- no priority evidence, represented by the empty vector for every frame; or
- an exact mapping covering every bound frame with one finite scalar/vector.

Missing or foreign keys are errors. Non-finite priority coordinates are errors.

### 4.2 Post-order common candidate-training preparation

`TargetSizeCommonPreparation` is a separate later object. It is built after the exact `P_train/M3` split and canonical P2 orders exist, over exact `P_train`, and is shared by every candidate `N` and optimizer seed.

Its current fitted numerical state includes, as applicable:

- the common target atomic-reference fit;
- mean-one normalized configuration weights over exact `P_train`;
- per-frame property availability masks;
- the current foundation/head identity and target training objective;
- one common MACE neighbor/model-construction normalization fitted over `P_train`; and
- the canonical realized candidate architecture/method inputs that must be identical across sizes except for explicitly N-dependent execution quantities.

Candidate projection selects frozen common values for `T_N`. It does **not** renormalize configuration weights, refit `E0`, or recompute common model normalization on each prefix.

This separation is a numerical anti-confounding requirement and removes the circular statement that a P3 common preparation could be an input to the P2 order that precedes it.

## 5. Exact target-size population and development split

### 5.1 `U_size`

`U_size` is the set of exact DEVELOPMENT frames from the accepted neutral substrate that are currently eligible and have canonical training labels. The implementation additionally requires enough population to support both the configured largest candidate `N_max` and the largest evaluation reserve `M3`.

### 5.2 Constraint components

Project the P1 protected-relation authority onto `U_size` and compute connected components. These components are indivisible allocation units.

### 5.3 Deterministic exact `M3` allocation

The current split policy requires **exact** reserve cardinality, not a near-size approximation. Component ordering is part of current deterministic membership because more than one exact component subset may exist.

The current order is:

1. group components by component cardinality;
2. process larger components before smaller components;
3. within one component size, group by the lexicographically minimum `condition_id` represented by that component;
4. sort component member tuples canonically inside each condition bucket; and
5. round-robin the buckets in sorted condition-ID order.

Given this ordered component sequence, solve the 0/1 exact subset-sum problem for target `M3`. The current dynamic program stores the first predecessor by which each reachable cardinality is obtained while iterating components in order and existing reachable totals in descending order. It stops after `M3` first becomes reachable and reconstructs that predecessor chain.

Abstractly, with component weights `w_j`,

$$
R_0=\{0\},\qquad
R_j=R_{j-1}\cup\{r+w_j:r\in R_{j-1},\ r+w_j\le M_3\}.
$$

If `M3` is unreachable, split construction fails. If reachable, the selected complete components form `M3`; the complement in canonical population order forms `P_train`.

The dynamic-programming data structure is replaceable only by an implementation that reproduces the same deterministic selected membership under the same policy. Exact cardinality alone is insufficient if an alternate tie-breaking scheme changes which frames enter `M3`.

The current state bound is pseudo-polynomial, approximately `O(C M3)` reachability work with `O(M3)` predecessor state, where `C` is component count.

## 6. Canonical training and evaluation orders

### 6.1 Condition-balanced priority order

For the relevant membership:

1. group frame UIDs by `condition_id`;
2. inside each bucket, sort by descending priority-vector coordinates (implemented as ascending negated coordinates) with immutable frame UID as the final tie-breaker; and
3. repeatedly visit condition buckets in sorted condition-ID order, taking one frame from each nonempty bucket.

With no priority evidence, the empty priority vectors tie and UID supplies the within-condition order.

This produces one exact permutation. The same deterministic rule is used for the target-training order and evaluation-reserve order with their respective evidence maps.

### 6.2 Nested memberships

The target candidate is

$$
T_N=\pi_{\text{train}}[:N].
$$

The evaluation rung is

$$
M_i=\pi_{\text{eval}}[:m_i].
$$

Membership identity binds parent-order identity, requested cardinality, and ordered frame UIDs. A stored `N` without the exact order/prefix identity is insufficient authority.

### 6.3 Current structural policy domain

The current P2 policy requires at least three strictly increasing positive power-of-two candidate sizes and exactly three strictly increasing positive power-of-two evaluation sizes. It also requires three strictly increasing positive fidelity epochs and one ordered unique nonnegative optimizer-seed population. Exact default values remain specification/configuration authority.

These structural restrictions are part of the current algorithm, not a general scientific theorem. Changing them creates a different target-size policy identity.

## 7. Prefix qualification

For configured candidate size `N`, derive qualification from the exact prefix:

$$
Q(N)=
\text{prefix exists}
\land\text{labels usable}(T_N)
\land\bigwedge_j c_j(T_N)\ge q_j.
$$

Hard-support selectors may refer only to frozen pre-candidate condition evidence: condition identity, reduced formula, temperature condition, strain class, regime, or declared user labels. They cannot inspect optimizer outcomes, evaluation scores, CV state, or runtime accidents.

Qualification does not reorder, swap, repair, or expand `T_N`. Because prefixes are nested and hard-support counts are membership counts, support counts are monotone nondecreasing in `N`. A contradictory qualification lineage indicates corrupt policy/evidence rather than a reason to mutate the order.

The current funnel requires at least three qualified candidates before automatic numerical screening.

## 8. Common atomic-reference and weight fitting

### 8.1 Count matrix and total-energy target

For exact fit membership `D`, construct a count matrix `C` whose row `i` contains the number of atoms of each element in frame `i`. Let `y` be the selected total-energy vector.

For from-scratch fitting, the configured regularized least-squares problem is conceptually

$$
\widehat e=\arg\min_e
\left[\|Ce-y\|_2^2+\lambda\|e-e_{\text{prior}}\|_2^2\right],
$$

with the prior term active only under the corresponding policy.

For foundation-model fine-tuning, the current production method fits the residual against the bound foundation prediction. With foundation predicted total energy `y_fnd` and foundation elemental references `e_fnd`,

$$
r=y-y_{\text{fnd}},
$$

$$
\widehat{\delta e}=\arg\min_{\delta e}
\left[\|C\delta e-r\|_2^2+
\lambda\|\delta e-\delta e_{\text{prior}}\|_2^2\right],
$$

and

$$
e_{\text{target}}=e_{\text{fnd}}+\widehat{\delta e}.
$$

The result binds element order by semantic atomic-number key, not serialized mapping iteration order.

### 8.2 Conditioning evidence

The solver records rank/singular-value information, null-space dimension where applicable, residual RMSE/MAE/maximum error, and rank-deficiency/transfer warnings. Rank deficiency is structural identifiability evidence; tightening a floating-point tolerance cannot recover a composition direction absent from `C`.

### 8.3 Configuration weights and masks

Common per-configuration weights are fitted once over the exact common membership and normalized to mean one. The current policy may equalize represented condition strata and then apply its configured bounds/multipliers.

Candidate projection never recomputes the mean on `T_N`, because doing so would make the loss scale candidate-dependent.

Local energy/force/stress property weights are availability masks derived from canonical label presence. They are not copies of the global objective ratio.

## 9. Objective and dependency-facing loss semantics

The numerical loss preserves three layers:

- global energy/force/stress coefficients;
- positive per-configuration weights; and
- local property availability masks.

The accepted current MACE method realizes these with the native weighted energy+forces+stress loss. The global coefficients are applied once. Configuration weights and local masks are consumed at their intended local layers.

A different mathematical loss family is not numerically equivalent merely because coefficients can be manipulated to resemble one another. In particular, a robust loss that inserts weights inside a nonlinear residual transformation cannot be made equivalent by naively rescaling the global coefficients.

The exact pinned MACE dependency and source-shape guards are **D3/D4 conformance mechanisms**. D2's invariant is that the executed dependency must realize the authenticated weighted objective, optimizer values, sample exposure, and batch geometry. A future dependency version may replace the current adapter only after proving these same numerical semantics or explicitly reopening D2.

## 10. Target-size optimizer-progress normalization

### 10.1 Confound being controlled

With target batch size `B`, candidate `N` exposes

$$
U_N=\left\lceil\frac{N}{B}\right\rceil
$$

target optimizer updates per nominal epoch when the final partial batch is retained. A fixed per-update learning rate and EMA decay would therefore couple larger `N` to larger optimizer progress.

### 10.2 Current normalization

For reference size `N_ref`, reference learning rate `LR_ref`, and reference EMA decay `beta_ref`, define

$$
U_{\text{ref}}=\left\lceil\frac{N_{\text{ref}}}{B}\right\rceil,
\qquad
s_N=\frac{U_{\text{ref}}}{U_N}.
$$

The target-size screen uses

$$
\text{LR}_N=\text{LR}_{\text{ref}}s_N,
$$

and, when EMA is enabled,

$$
\beta_N=\beta_{\text{ref}}^{s_N}.
$$

This preserves the first-order per-epoch products

$$
\text{LR}_N U_N=\text{LR}_{\text{ref}}U_{\text{ref}},
$$

and

$$
(\beta_N)^{U_N}=\beta_{\text{ref}}^{U_{\text{ref}}}.
$$

The normalized values are computed once from the full candidate geometry and remain unchanged through later fidelity rungs. Survivor count does not rescale them.

### 10.3 Not exact optimizer-path equivalence

This is a first-order progress normalization, **not** a theorem that candidate trajectories have identical optimization dynamics. Residual differences include minibatch stochasticity, order-dependent gradients, Adam/AMSGrad moment history, finite discretization of the learning-rate schedule, and candidate-dependent loss landscape/data composition.

The intended estimand is therefore the current normalized screening method, not an imaginary optimizer-invariant learning curve.

### 10.4 Complete target batches

The ceiling update geometry is valid only when the final partial target batch is retained. Target-size execution therefore requires:

- `drop_last = false` for the target path;
- every exported target UID exposed once per epoch under the accepted loader semantics;
- no duplicate padding merely to complete the last batch; and
- no distributed sampler that truncates the target population unless it proves exact equivalent coverage/update geometry.

A runtime that produces `floor(N/B)` updates is a different numerical experiment.

## 11. Continuous fidelity trajectories and restart

For active `(N,s)` with optimizer seed `s`, training is one continuous trajectory through configured boundaries

$$
n_1<n_2<n_3.
$$

The exact predecessor state includes model, optimizer, EMA where enabled, learning-rate state, and the Python/NumPy/Torch RNG lineage required by the accepted runtime. A later rung restores its authenticated predecessor rather than restarting from the foundation model.

Accepted progress is immutable evidence. Unaccepted first-rung materialization/checkpoint state is attempt-local scratch and may be reclaimed only under the D3 execution-ownership rules that prevent concurrent writers from deleting live work.

Recovery cannot change candidate membership, normalization, common preparation, seed, or boundary identity.

## 12. EVAL2 target-force estimator

At boundary `j`, the exact checkpoint is evaluated on exact evaluation membership `M_j`. If `K` Cartesian force components are admitted,

$$
\text{RMSE}_{F,\text{eV}/\text{Å}}=
\sqrt{\frac{1}{K}\sum_{k=1}^{K}
(\widehat F_k-F_k)^2},
$$

and the target-size stored metric is

$$
\text{RMSE}_{F,\text{meV}/\text{Å}}=
1000\,\text{RMSE}_{F,\text{eV}/\text{Å}}.
$$

Device batching may partition inference to bound memory. Batch width is execution-only only if exact membership/model state/prediction semantics are preserved and the aggregate metric agrees under the accepted floating-point equivalence contract.

A non-finite model prediction or non-finite target metric is a typed numerical failure, not an invented infinite score.

## 13. Pure target-size reducer

### 13.1 Ordered boundary matrix

At boundary `j`, with active candidates `A_j` and configured ordered seeds `S`, the expected outcome sequence is size-major then seed-minor over

$$
A_j\times S.
$$

Every outcome binds the exact experiment definition, execution context, boundary epoch, and evaluation-membership identity. Missing, duplicate, reordered, foreign, or lineage-incompatible evidence produces an insufficient-comparison terminal result rather than being silently rearranged.

### 13.2 Complete-seed score

A size receives a finite score only when **all** configured seeds have finite valid target metrics:

$$
\bar E_N=\frac{1}{|S|}\sum_{s\in S}E_{N,s}.
$$

If any seed has an authenticated numerical failure, that candidate is removed from successful comparison. The mean is never computed over only the successful subset.

Current typed failures include non-finite training model state, non-finite optimizer state, non-finite evaluation prediction, and non-finite target metric.

### 13.3 Practical-equivalence order

Given successful scores and tolerance `epsilon`, repeatedly find the current best score `E_min`, define the equivalent set

$$
\mathcal E=\{N:E_N\le E_{\min}+\epsilon\},
$$

choose the smallest `N` in `E`, remove it, and repeat. The current implementation uses only a tiny fixed floating-point comparison guard beyond the scientific `epsilon`; machine epsilon is not the practical-equivalence policy.

### 13.4 Funnel

The structural funnel is

$$
q\rightarrow\min(q,4)\rightarrow2\rightarrow1,
$$

where `q` is the number of qualified candidates entering the first boundary.

At the first boundary the number of successful candidates must be at least `min(|A_1|,4)`; the second and terminal comparisons require two successful candidates. Otherwise the reducer terminates with insufficient comparison.

The exact fidelity epochs and evaluation sizes are policy values attached to these three positions, not encoded in the structural funnel name.

### 13.5 Configured-ceiling rule

Let `N_max` be the configured maximum candidate and suppose it is a successful terminal finalist. If

$$
E_{N_{\max}}+\epsilon<E_N
$$

for every other successful terminal finalist, `N_max` is materially superior, is recommended, and carries the explicit nonconvergence-at-configured-ceiling diagnostic.

Otherwise the first practical-equivalence-ranked finalist is recommended. This naturally selects the smaller finalist when its score is within `epsilon` of the best.

The reducer does not extrapolate a learning curve, solve for an asymptotic root, or invent an unconfigured rescue size.

## 14. Post-selection fold construction and fitting

After the operator's collection is frozen, each admitted `T_N` is validated separately. Current post-selection fold construction is downstream of target-size selection and is **not** the retired DATA5 preselection CV authority.

For each required fold:

1. partition only the exact frozen `T_N` while preserving inherited protected relations and purge requirements;
2. derive a checkpoint-monitor role from training-eligible evidence, disjoint from held-out evaluation;
3. fit all fold-local transforms/atomic references/other fitted training inputs from the fold training domain only;
4. initialize a fresh model/optimizer lineage under the frozen post-selection method;
5. train for the selected CV horizon;
6. choose an admissible representative using only authorized monitor/integrity/replay-retention evidence; and
7. after representative freeze, evaluate once on the held-out fold.

Every configured fold and seed required by the policy must be represented. A missing fold, failed required seed, no-admissible-checkpoint outcome, or method-identity mismatch is not ignored to obtain a favorable acceptance statistic.

## 15. Checkpoint selection as constrained optimization

The post-selection checkpoint owner filters candidates through mandatory constraints before ranking. The current constraint family can include target/focus/condition/property integrity and replay-retention requirements.

If the admissible set is empty, the run has no admissible checkpoint. The algorithm must not fall back to “best target error among inadmissible checkpoints.”

Only after admissibility is established does the policy apply its deterministic target-side ranking/tie semantics. Held-out fold data are unavailable to this decision.

## 16. Replay and post-selection exposure

### 16.1 Separation from target-size screening

Target-size execution has zero replay training samples. Its numerical identity is target-only. Post-selection replay therefore cannot alter P2/P3 target-size evidence or target membership.

### 16.2 Replay label modes

The current post-selection architecture supports:

- true-reference/DFT replay as the canonical default when canonical replay labels are available; and
- foundation pseudo-label replay only under explicit opt-in policy bound to the frozen foundation model/head.

Pseudo-label replay is not an automatic substitution for missing DFT labels. A pseudo-label training path still requires a separate true-reference replay-monitor lineage under current policy.

Replay source membership, label mode, monitor membership, head identity, exposure policy, and realized counts belong to post-selection method identity.

### 16.3 No hidden target duplication

Current replay-enabled execution explicitly disables the dependency behavior that would duplicate target examples to satisfy a target/replay ratio heuristic. Effective target membership/count must equal the authenticated target exposure. Any intentional future resampling would need its own accepted D2/D3 policy.

## 17. Fresh final production and publication selection

Final production starts a new lineage on complete exact `T_N`; screen and CV checkpoints are never warm-start parents.

For each required final seed, the final-production run freezes its representative using the accepted checkpoint/admissibility owner and exact target evaluation evidence. The final publication decision is then made **before** downstream qualification.

The current architecture supports two publication modes:

- publish every required final seed whose frozen representative is admissible; or
- among already-frozen admissible representatives, publish one deterministic best representative using the accepted target-only final-production ordering/tie material.

These modes are upstream product-membership algorithms. Qualification/physical/locked evidence never enters the cross-seed publication ranking.

## 18. Current dependency realization boundary

The accepted current adapter is qualified against `mace-torch==0.3.16`. That exact upstream version contains behaviors that would violate the D2 invariants if allowed to control the method: forced `UniversalLoss` under multihead fine-tuning, LR/EMA mutation, ratio-driven target duplication, and target-batch truncation.

mdstats currently source-qualifies and narrowly guards/repairs those behaviors in its existing qualified execution seam. Those source markers, package version, and patch mechanics are **not timeless D2 requirements**. They are current D3/D4 evidence that the dependency realizes the D2 method. A future dependency can replace them only after demonstrating the same resolved loss, optimizer, exposure, and batch semantics or after an explicit D2 revision.

## 19. Numerical failure, conditioning, precision, and uncertainty

### 19.1 Failure is typed evidence

A failed numerical comparison is different from a poor but finite model. Non-finite model/optimizer state and non-finite evaluation evidence carry typed failure identities. Missing or contradictory boundary evidence produces insufficient comparison. Neither is silently converted into an arbitrary finite/infinite ranking value.

### 19.2 Atomic-reference conditioning

Rank and null-space evidence characterize an identifiability problem, not merely solver accuracy. A null direction in element-count space persists at infinite arithmetic precision unless additional independent compositional information or an accepted prior changes the mathematical problem.

### 19.3 Optimizer stochasticity

Optimizer seeds are explicit stochastic replicates. Pairing controls one source of comparative variation but does not remove minibatch, finite-horizon, or model-training uncertainty. Reproducibility means preserving the accepted seed/method lineage and numerical compatibility contract, not claiming bitwise identity across unsupported hardware/library regimes.

### 19.4 Precision and backend

Learned-model dtype, critical-precision policy, acceleration/backend behavior, and other numerically trajectory-changing settings belong to method/execution identity. Worker count, queue order, cache path, device-batch width for exact evaluation, and file-backed representation are execution-only only when they preserve the accepted numerical result.

## 20. Complexity and scaling

Ignoring neural-network training cost, principal control-plane operations scale approximately as:

- autocorrelation estimation: FFT-dominated per observable/run plus linear block construction;
- relation closure: near-linear in frame/relation edges with union-find-style closure;
- exact `M3` component allocation: pseudo-polynomial `O(C M3)` reachability work;
- canonical condition-balanced order: dominated by per-condition sorting, at most `O(N log N)`;
- hard-support qualification: linear in inspected prefix/obligation membership in the direct implementation;
- EVAL2: linear in evaluated force components, with bounded device memory through chunking; and
- reducer: `O(boundaries * candidates * seeds)` with tiny state relative to training.

Training dominates total computational cost. Performance changes are admissible only when they preserve the authoritative memberships, fits, trajectories, reductions, and decisions above.

## 21. Verification and falsification oracles

The D2 method should be falsified through independent invariants rather than only by successful end-to-end execution:

- verify cell/strain/stress round trips under the declared conventions;
- verify autocorrelation parity against the shared sampling oracle and complete-frame block coverage without dropped tails;
- re-derive P1 protected relations and reject stale split descendants;
- prove the neutral target-size condition key has no compatibility-domain/CV fan-out;
- independently verify exact `M3` subset feasibility for bounded fixtures;
- prove the deterministic component-order/DP policy reproduces exact `M3` membership;
- prove `pi_train` and `pi_eval` are exact parent permutations;
- prove every `T_N`/`M_i` is the exact authenticated prefix;
- prove hard-support qualification is re-derived from the exact prefix and pre-candidate obligation policy;
- prove candidate projection does not refit/renormalize common weights, `E0`, or model normalization;
- verify realized target batches equal `ceil(N/B)` with no target duplication;
- verify normalized LR/EMA identity is fixed across the surviving rungs of one candidate;
- replay reducer history through the pure transition owner and require the same result;
- prove incomplete/reordered matrices fail rather than being reordered or subset-averaged;
- prove held-out CV labels cannot reach fold fitting or checkpoint selection;
- verify a no-admissible-checkpoint outcome does not fall back to an inadmissible checkpoint;
- verify replay-only changes invalidate post-selection descendants but do not mutate the frozen target-size evidence;
- verify final-product member selection is complete before downstream qualification; and
- prove execution resource/chunk/cache changes preserve outputs under the accepted exact/bounded numerical-equivalence contract.

A failure of these oracles is evidence of D2 or lower-layer nonconformance. If the only repair requires changing the mathematical estimator, ordering/tie rule, normalization, or scientific decision semantics, D2 must be reopened and descendant evidence applicability re-evaluated.

## 22. Reproducibility contract

A numerical reproduction requires, as applicable, the exact:

- source/frame numerical conventions and eligibility policies;
- correlated-sampling/block policy and protected-relation authority;
- pre-order selection-evidence identity;
- `U_size`, exact `P_train/M3` split, and deterministic split policy;
- `pi_train`, `pi_eval`, candidate/evaluation prefix identities, and hard-support policy;
- common target-size training preparation, including fitted `E0`, weights/masks, and common model normalization;
- target objective and executable mathematical loss family;
- candidate ladder, seed population, fidelity/evaluation ladder, and practical-equivalence policy;
- target-size optimizer-normalization reference policy and target batch geometry;
- exact boundary metrics/failures and reducer history;
- frozen selected memberships and role horizons;
- post-selection replay/monitor/checkpoint/fold method identity; and
- final-production/publication membership identity for production claims.

Runtime caches and scratch need not be preserved when they are exactly reconstructible and are not scientific evidence.

## 23. References

1. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, “MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields,” *Advances in Neural Information Processing Systems* **35**, 11423–11436 (2022), arXiv:2206.07697.
2. H. Flyvbjerg and H. G. Petersen, “Error Estimates on Averages of Correlated Data,” *Journal of Chemical Physics* **91**, 461–466 (1989). DOI: 10.1063/1.457480.
3. C. J. Geyer, “Practical Markov Chain Monte Carlo,” *Statistical Science* **7**, 473–483 (1992). DOI: 10.1214/ss/1177011137.
4. J. Racine, “Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation,” *Journal of Econometrics* **99**, 39–61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
5. D. R. Roberts, V. Bahn, S. Ciuti, et al., “Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,” *Ecography* **40**, 913–929 (2017). DOI: 10.1111/ecog.02881.
6. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, “How to Validate Machine-Learned Interatomic Potentials,” *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.
7. ACEsuit, MACE training and multihead fine-tuning documentation, version-qualified by the current mdstats adapter where execution semantics depend on it.
8. ACEsuit, `mace-torch` 0.3.16 source (`mace.cli.run_train` and `mace.tools.train`), used by current dependency-conformance qualification; the dependency version is a current D3/D4 realization, not a timeless numerical axiom.

Exact current configuration constants, schemas, source-probe markers, persistence records, and module paths remain with the current specifications/architecture and are not duplicated here as independently tunable D2 values.
