---
title: "mdstats MLFF Scientific Method — post-selection foundation-adaptation revision candidate"
artifact_level: "D1 scientific formulation"
status: "candidate D1 authority on fix/mlff-post-selection-method-restoration; review blockers repaired 2026-09-14; independent D1/D2 re-review required before integration"
baseline_accepted_date: "2026-09-13"
candidate_revision_date: "2026-09-14"
candidate_against_commit: "421e23aaed0a13443e984327bc903fc4cf4bc82e"
---

# mdstats MLFF Scientific Method

## 1. Purpose, scope, and authority state

This paper states the scientific formulation of the machine-learned force-field (MLFF) branch of mdstats: the scientific questions, evidence roles, physical conventions, target-size experiment, foundation-model adaptation, replay semantics, cross-validation, fresh final production, validity limits, and falsification conditions that downstream numerical and software layers must preserve.

This 2026-09-14 candidate revises only the scientific semantics materially implicated by the post-selection restoration. It preserves the accepted target-size population, order, evaluation ladder, reducer, replay geometry lineage, target/replay acceptance thresholds, downstream qualification separation, and all other unaffected P1/P2/P3 scientific semantics. In particular, it does **not** change the P2/P3 target-size method or silently broaden the restoration to post-selection training from scratch.

The candidate changes the scientific method for **foundation-model post-selection adaptation**—`naive_fine_tuning` and `multihead_replay`—in four coupled respects:

1. foundation adaptation uses a robust energy/force/stress training objective whose exact numerical definition is delegated to D2, rather than the previously universal weighted-quadratic requirement;
2. nontrivial per-configuration loss weighting and target-versus-replay training-head scalar weighting are not part of this foundation-adaptation method;
3. checkpoint control uses one protected campaign-common target monitor outside every target-size training prefix, shared across post-selection cross-validation and fresh final production; and
4. the default post-selection cross-validation design uses three folds while preserving explicit override, all-required-fold acceptance, and the existing held-out evidence semantics.

Foundation-residual elemental reference-energy fitting remains mandatory and is strengthened here to require the exact selected foundation checkpoint **and foundation head**. The scientifically required identifiability condition is imposed on the composition-weighted reference-energy correction actually used by each governed target configuration; individual elemental correction coefficients need not be uniquely identifiable when their relevant composition-weighted sums are unique. Checkpoint-monitor or held-out labels may not be used to resolve an otherwise unidentifiable correction.

The numerical method is delegated to `mlff_numerical_algorithmic_method.md`. D3 architecture and D4 specifications/implementation own software decomposition, persisted schemas, runtime control, dependency adaptation, caches, and interfaces. They may not redefine the scientific semantics below.

This branch document is a candidate replacement authority. The 2026-09-13 accepted paper remains the integrated baseline until this candidate passes the required independent D1/D2 re-review and integration acceptance. Repository presence alone does not promote the candidate.

## 2. Scientific background

### 2.1 Potential-energy-surface learning

For atomic numbers `Z`, Cartesian positions `R`, and periodic cell `H`, an energy-conserving interatomic model represents a scalar potential-energy surface

$$
E_\theta(Z,R,H).
$$

Forces are energy derivatives,

$$
\mathbf F_i=-\frac{\partial E_\theta}{\partial \mathbf R_i},
$$

and, when stress is part of the accepted label contract, the Cauchy stress is the corresponding cell/strain derivative under the declared source convention,

$$
\boldsymbol\sigma=-\frac{1}{V}\frac{\partial E_\theta}{\partial \boldsymbol\varepsilon}.
$$

The sign, tensor, shear, unit, and strain conventions are part of label identity. Energy, force, and stress values produced under incompatible derivative or reference conventions are not interchangeable observations.

The current mdstats workflow adapts an accepted MACE foundation model for foundation-based post-selection modes rather than proposing a new neural-network ansatz. MACE supplies the equivariant model family; mdstats owns the scientific evidence design, target-size experiment, adaptation objective, replay semantics, validation boundaries, and provenance needed to interpret the fitted result. Training-from-scratch remains a supported but separately governed mode and is not altered by this restoration merely because it shares infrastructure.

### 2.2 Why trajectory frames are not independent samples

Molecular-dynamics (MD) trajectories contain serial correlation. Adjacent structures may be nearly identical, event windows may contain many frames generated by one physical transition, and a slowly evolving site, defect, phase, or structural coordinate may remain correlated for much of a run. A random frame split can therefore place near-replicates on both sides of an evaluation boundary and underestimate generalization error.

For a stationary scalar observable `x_t`, the normalized autocorrelation is

$$
\rho(k)=\frac{\operatorname{Cov}(x_t,x_{t+k})}{\operatorname{Var}(x_t)},
$$

and the integrated autocorrelation time is represented in stored-frame units as

$$
\tau_{\mathrm{int}}=\frac12+\sum_{k=1}^{k^\star}\rho(k).
$$

The associated diagnostic effective sample count is

$$
N_{\mathrm{eff}}=\min\!\left(N,\frac{N}{2\tau_{\mathrm{int}}}\right).
$$

This quantity measures serial redundancy under the chosen observable and truncation rule. It is not proof that every slow variable has decorrelated or that distinct temporal blocks are independent metastable-state realizations. mdstats therefore carries categorical independence evidence and limitation codes in addition to numerical autocorrelation evidence.

### 2.3 Why target size is an experiment

Target-training cardinality `N` is a scientific independent variable, not a storage knob. If changing `N` also changes the sampling rule, fitted preprocessing, optimizer progress, evaluation population, training objective, or hidden loader exposure, the observed difference cannot be interpreted cleanly as a target-data-size effect.

The target-size method therefore uses one deterministic training order, exact nested prefixes, one target-size evaluation ladder, common candidate-independent training preparation, paired optimizer seeds, and an explicit short-horizon comparison policy. The automatic screen is diagnostic evidence that can recommend a size. The operator owns the provisional downstream design, and post-selection cross-validation evaluates that frozen design rather than feeding backward into it.

The post-selection restoration in this paper does not retroactively change that target-size experiment. P3 remains target-only and retains its separately accepted objective, optimizer-progress normalization, reducer, and complete-batch exposure semantics.

## 3. Source evidence, label compatibility, and physical conventions

### 3.1 Source occurrence, geometry, and label identity

mdstats distinguishes several identities that answer different scientific questions:

- **source-content identity** — whether source bytes/control content are the same;
- **source-occurrence identity** — whether a record represents the same declared run occurrence;
- **frame occurrence identity** — a particular source-frame occurrence;
- **geometry identity** — the atom-ordered structure, cell, periodicity, and coordinates independent of labels;
- **label identity** — the energy/force/stress payload together with its units and scientific conventions; and
- **labeled-configuration identity** — the combined geometry-plus-label statement.

A copied file may have identical content but represent a distinct declared occurrence. Conversely, distinct occurrences may contain the same geometry and must not automatically be treated as independent evidence. Geometry identity deliberately excludes labels and provenance fields so duplicate geometry remains visible rather than hidden inside a combined record key.

### 3.2 Label-domain compatibility remains current science

Compatibility of target labels remains scientific authority. Current source authority distinguishes at least theory/electronic-structure identity, energy-reference identity, derivative and stress convention, numerical-quality profile, and software/provenance evidence.

A compatibility policy may recognize non-semantic provenance differences, but it must not silently merge incompatible theory levels, energy references, or derivative conventions. A target training bundle contains one compatible target label domain plus a separately identified replay lineage when replay is enabled.

What remains retired is using `label_domain_id` as a pre-target-size partition axis that creates separate target-size selectors, separate target-size cross-validation authorities, or per-domain target-size maps. Source-label compatibility is resolved upstream; target-size construction then operates on accepted canonical evidence without reintroducing another target-size authority.

### 3.3 Energy channel

The target energy is an explicit named channel. Its units, completeness, electronic/reference convention, and relationship to derivative labels are preserved. An energy value selected from one convention cannot be silently paired with forces or stress from another convention.

### 3.4 Ensemble and temperature evidence

Nominal thermodynamic control and realized observations are distinct. A source may specify a target temperature, a ramp, or no target temperature, while also carrying instantaneous-temperature observations. Realized temperature statistics do not overwrite source-control semantics.

Temperature, composition, strain, regime, phase, defect state, surface/interface state, preparation history, and user-declared scientific axes may all matter to applicability. These axes are hierarchical and material-dependent rather than an automatically complete Cartesian product.

### 3.5 Cell, deformation, and strain

ASE-style source geometry uses row-vector cells,

$$
\mathbf r_{\mathrm{row}}=\mathbf s_{\mathrm{row}}\mathbf H.
$$

For reference cell `H_0` and current cell `H_t`, the Cartesian column-vector deformation gradient is

$$
\mathbf F=\left(\mathbf H_0^{-1}\mathbf H_t\right)^T.
$$

The scientific strain context includes a proper polar decomposition

$$
\mathbf F=\mathbf R\mathbf U,
$$

and may report linearized, Green-Lagrange, and logarithmic strain measures, volume ratio, rotation, principal logarithmic strains, hydrostatic/deviatoric measures, and engineering shear. Reference-cell selection is explicit; an ambiguous or physically unsuitable reference cell is not silently inferred.

### 3.6 Stress convention

The canonical target stress is a symmetric Cartesian Cauchy stress in the accepted ASE/MACE sign convention and canonical internal units. Tensor shear components and engineering shear are not interchangeable. Virial-like quantities remain distinct from stress unless a current owner explicitly defines a valid conversion.

Unit, sign, Voigt-order, and shear-factor round trips are scientific correctness conditions, not display formatting.

### 3.7 Eligibility is not typicality

Eligibility answers whether a labeled frame may enter the scientific evidence base. Hard failures include missing or non-finite required labels, malformed geometry/cell state, incompatible atom counts, unrecoverable incomplete source records, disallowed electronic-convergence failures, or other conditions that make the reference observation unusable under the active policy.

High but finite forces, unusual strain, rare coordination, event frames, and difficult model residuals are not rejected merely for being unusual. Such evidence can be scientifically valuable precisely because it probes difficult regions. Quality, rarity, difficulty, and applicability evidence remain separate from eligibility.

## 4. Evidence roles, leakage, and statistical independence

### 4.1 Strongest-supported independence, not invented independence

mdstats prefers the strongest evidence available, in descending order when the data support it:

1. independent replica or independently prepared realization;
2. independent structural or chemical ordering;
3. independent thermodynamic run; and
4. purged temporal blocks within a run.

Temporal distance alone does not establish an independent slow-state realization. When only weaker independence is supportable, the evidence must say so.

### 4.2 Correlation units and protected relations

Before incompatible roles are allocated, the workflow constructs correlation-aware complete-frame units and preserves relations that make frames scientifically unsafe to separate. Current protected relations include:

- membership in the same correlation unit;
- exact geometry duplicates;
- membership in the same protected event window;
- condition-scoped replica lineage across distinct runs; and
- condition-scoped structural-realization lineage across distinct runs.

The transitive closure is material. If `a` is inseparable from `b` and `b` from `c`, then `a,b,c` form one indivisible relation component for incompatible-role allocation even if no direct `a-c` relation was stored.

### 4.3 Event detection precedes thinning

Rare events are identified at full temporal resolution before ordinary-frame thinning that could erase event shape or split one event into apparently independent samples. Protected event windows remain indivisible across incompatible evidence roles.

### 4.4 Evidence roles

The MLFF evidence model distinguishes:

- development evidence that may supply gradients or development/model-selection evidence according to a narrower role;
- checkpoint/model-control monitor evidence that supplies no gradients;
- post-selection held-out cross-validation evidence;
- uncertainty-calibration evidence where applicable;
- locked interpolation-test evidence activated only after the required freeze boundary; and
- purged or excluded evidence.

A frame that supplied a gradient is not independent validation evidence for that model. A held-out fold cannot choose the checkpoint at which it is evaluated. Calibration cannot tune the protocol it is supposed to calibrate. Locked evidence cannot affect membership, target size, fitting, stopping, checkpoint choice, calibration-policy design, acquisition, or final-product membership.

The target-size `M1/M2/M3` populations are development/model-selection evidence specific to P3. They are not post-selection held-out CV, not locked final tests, and—under this revision—not the P5 checkpoint-monitor parent.

### 4.5 Feasibility and deferral

Requested evidence roles may be scientifically infeasible. The method preserves explicit outcomes such as temporal-block-only support, calibration deferral, insufficient locked-test support, insufficient requested roles, or an infeasible requested monitor/fold design. A percentage target, desired fold count, or desired monitor budget does not justify fabricating independent evidence from short or correlated trajectories, splitting a protected relation, using a held-out label for fitting, or falling back to a semantically incompatible role.

### 4.6 Feature blinding and fitted evidence

Raw structural and event facts may be computed before final role assignment when their provider is genuinely partition-independent. Label-derived or dataset-fitted quantities obey a stricter rule: scaling, whitening/principal-component analysis (PCA), fitted metrics, foundation residuals/difficulty, atomic-reference corrections, and related quantities may be fitted only on the authorized domain for the operation that consumes them.

Checkpoint-monitor, held-out, calibration, and locked labels may be observed only for their authorized evidence role. They cannot leak backward into target membership, fitted transforms, checkpoint selection, target-size decisions, or a training-domain fit.

## 5. Two distinct candidate-independent fitted stages

The accepted method distinguishes two semantically different stages that older architecture prose sometimes called “common preparation”; they must remain separate.

### 5.1 Pre-order selection evidence

Candidate-independent descriptors, feature metrics, foundation predictions, difficulty evidence, condition/event/environment evidence, representative-density/diversity evidence, and provenance/correlation evidence may contribute to the ordering evidence from which the one canonical target-training order is built. Any fitted quantity in this stage is bound to its authorized pre-candidate development domain.

These inputs do not create a second selector. They contribute evidence to one target-size ordering owner.

### 5.2 Target-size common training preparation

After the current target-size split and canonical orders exist, one target-size common training preparation is fitted over exact `P_train` under the frozen P3 candidate-training method. It is shared unchanged by all target-size candidates and optimizer seeds. It includes the training-side fitted state required by P3, including the target atomic-reference fit, P3 configuration/property weights, foundation/head identity where applicable, and common MACE normalization/model-construction inputs.

This later common training preparation is not an input used to decide `pi_train`. Candidate projection selects exact `T_N` rows from already fitted state; it does not refit or renormalize them by candidate size. The distinction prevents a circular dependency and keeps `N` as the intended experimental variable.

P5 foundation adaptation has a different fitted-preparation scope after target selection: cross-validation fits training-dependent quantities independently inside each fold training domain, while fresh final production fits them on exact `T_selected`. This distinction is required by held-out-label exclusion and does not reopen P3.

## 6. Target-size scientific experiment

### 6.1 Population and development split

The target-size population `U_size` contains currently eligible, canonically labeled frames from the neutral **development** role. Physical-only frames without the required canonical training labels do not enter the target-size experiment.

`U_size` is split exactly once into `P_train`, the pool from which candidate target-training memberships are drawn, and `M3`, the largest development/model-selection reserve for the target-size diagnostic. The split preserves all inherited protected relations. Failure to construct the exact requested reserve while retaining sufficient training support is a scientific infeasibility result, not permission to split a protected relation or silently alter the reserve.

### 6.2 One canonical training order

One deterministic order

$$
\pi_{\mathrm{train}}=(x_1,x_2,\ldots,x_{|P_{\mathrm{train}}|})
$$

is constructed before candidate training. Candidate membership is

$$
T_N=\pi_{\mathrm{train}}[:N].
$$

For `N_a<N_b`, the smaller candidate is therefore a prefix of the larger candidate. Increasing `N` only adds frames; it does not swap to a different selection solution.

Ordering evidence may favor representative, difficult, diverse, or otherwise relevant frames while maintaining condition support. Candidate qualification is separate: a prefix is admitted only by label usability and explicitly declared hard-support obligations over frozen pre-candidate condition evidence. Diagnostic novelty or coverage measures do not silently become additional qualification gates.

### 6.3 Evaluation ladder

One deterministic evaluation order over `M3` defines nested direct populations

$$
M_1\subset M_2\subset M_3.
$$

Each rung is evaluated on exactly the frames it names; the rungs are not complements of one another. The ladder is P3 target-size model-selection evidence only.

### 6.4 Controlled stochastic replicate dimension

The optimizer-seed set is explicit and common to all candidate sizes. A candidate score is formed only from a complete comparable seed population. A numerical failure is not silently discarded to make a candidate mean look better. Paired seeds reduce avoidable comparison noise but do not make the seed mean a confidence interval or represent every scientific uncertainty.

### 6.5 Successive short-horizon fidelity

Candidates proceed through exact ordered training boundaries and exact `M1/M2/M3` evaluation populations. A surviving `(N,seed)` trajectory continues through later boundaries with the same model/optimizer/random-number-generator lineage rather than restarting as an unrelated rung-local experiment.

The automatic stage measures one configured short-horizon screening protocol. It is not a universal learning curve and cannot establish long-horizon or deployment behavior by itself.

### 6.6 Primary response and practical equivalence

The primary automatic-screen response is target-force root-mean-square error (RMSE) on the exact target-side model-selection population,

$$
\operatorname{RMSE}_F=\sqrt{\frac{1}{K}\sum_{k=1}^{K}\left(F_k^{\mathrm{pred}}-F_k^{\mathrm{ref}}\right)^2},
$$

where `k` indexes admitted Cartesian force components of the exact evaluation membership. The current screen stores the result in meV/Å. Energy and stress may remain part of training/checkpoint semantics but do not silently replace this frozen ranking response.

Candidate means use the complete configured seed population. A declared practical-equivalence threshold `epsilon` expresses the smallest force-error difference treated as material for the reducer; it is not machine epsilon.

Within an equivalence set, smaller `N` is preferred. At the terminal comparison, a configured maximum candidate that is materially superior to all other successful finalists remains the best tested permitted size and may be recommended while explicitly recording that a plateau was not demonstrated inside the configured ladder. The configured ceiling is a practical budget boundary, not an asymptotic-convergence claim.

If too few complete comparable candidates remain, the automatic result is no recommendation. This is a statement about the diagnostic, not a claim that the campaign has no usable target size; it does not erase an existing qualified operator proposal.

### 6.7 Recommendation versus operator decision

The reducer produces evidence. The operator owns the provisional downstream design and may accept, ignore, or override the recommendation within the qualified configured candidate set, including selecting more than one size for comparative downstream work. Each provisional entry owns its CV and production horizons.

`cross-validate` admission is the freeze boundary. It binds every selected `N` to exact `T_N` and its role-specific horizons. Post-selection evidence cannot retrospectively choose another target membership.

## 7. Training objectives, atomic references, and checkpoint control

### 7.1 Objective semantics are method-specific

Three concepts must remain distinguishable wherever they are active:

1. **global energy/force/stress coefficients**, expressing relative property emphasis;
2. **per-configuration weighting**, expressing configuration-level emphasis when the accepted method actually uses it; and
3. **local property-availability masks**, normally `1` when a canonical property is available and `0` when absent.

A missing property contributes zero through its local mask rather than redefining the global objective. Per-configuration weighting likewise does not redefine the relative energy/force/stress coefficients.

P3 target-size screening retains the accepted P3 weighted energy+forces+stress objective, including its configuration-weight policy. Post-selection training from scratch retains its separately accepted weighted objective. This restoration changes neither method merely to make its loss family match foundation-model P5.

For **foundation-model P5 adaptation** (`naive_fine_tuning` and `multihead_replay`), the scientific objective is instead the robust D2-defined energy/force/stress objective with global coefficients

```text
energy : forces : stress = 1 : 10 : 1
```

and binary local property-availability masks. Nontrivial per-configuration weighting is not part of the current P5 foundation-adaptation objective. A transport field required by a file format may be numerically neutral, but it has no independent scientific weighting meaning in this method.

There is also **no target-versus-replay training-head scalar weight** in current multi-head foundation adaptation. Relative aggregate exposure arises from authenticated target and replay memberships plus the accepted stochastic loader semantics. A larger replay corpus may therefore contribute more training examples than the target corpus; the method does not claim equal target/replay loss mass or a hidden 1:1 balance.

Checkpoint/adaptive-stop `target_score_weight` and `replay_score_weight`, when used by the checkpoint-control policy, are a separate model-selection concept. Retiring training-head scalar weighting does not retire those score weights or the replay-degradation admissibility constraint.

### 7.2 Foundation-residual elemental reference energies

Elemental reference energies (`E0`) are fitted numerical quantities, not universal elemental constants. For foundation-model adaptation, target-head elemental references are fitted as **corrections** to the exact selected foundation checkpoint and foundation head from the authorized target gradient-training domain. The fitted target-head references are the foundation-head references plus the fitted corrections.

In post-selection CV, the correction fit uses only that fold's target gradient-training membership. The campaign-common checkpoint monitor and held-out fold do not contribute labels to the fit. Fresh final production fits the corresponding corrections on complete exact `T_selected`.

The scientific identity of the fit includes the selected foundation head. A multi-head foundation checkpoint may not silently substitute its first, default, or another available head merely because dependency code permits such a fallback.

The scientifically required quantity for a target configuration with composition-count vector `c` is the total elemental correction `c^T delta_e`, not necessarily every elemental component of `delta_e` separately. Let `N_free` denote the unanchored null space of the authorized composition fit after accounting for any explicitly accepted prior/anchor. The correction needed for composition `c` is scientifically identifiable exactly when

$$
c^T v=0\qquad\text{for every }v\in N_{\mathrm{free}}.
$$

Thus a rank-deficient elemental decomposition may still support a unique total correction for some compositions, while another composition using only represented elements can remain unidentifiable. An element absent from the fitting domain but required by a governed composition is a sufficient failure case when no accepted anchor fixes that direction, but absence is not the only possible identifiability failure.

The current restoration introduces no new absent-element correction prior. If the required composition-weighted correction for target training, checkpoint monitoring, or held-out evaluation is not identifiable from the authorized fit plus already-accepted anchors, the run/fold is scientifically infeasible. Checkpoint-monitor or held-out labels may not be used to fill the gap, an arbitrary minimum-norm or solver-chosen decomposition does not create scientific identification, and an unfitted zero correction is not silently assumed.

Rank, singular values/null-space evidence, residuals, and any accepted prior/anchor dependence remain part of the scientific interpretation.

Replay/pretraining-head reference energies remain head-local. When multi-head replay starts from a multi-head foundation checkpoint, the replay/pretraining-head foundation reference mapping must correspond to the same explicitly selected foundation head/lineage required by the accepted replay method; an arbitrary first-head fallback is not equivalent.

### 7.3 Checkpoint admissibility is constrained model selection

Checkpoint choice is not “lowest one scalar at any cost.” The active policy may combine a primary target-monitor metric with mandatory target, focus/species/condition/property, replay-retention, and integrity constraints. A checkpoint violating a mandatory constraint is inadmissible even if its target metric is lower.

Held-out CV evidence does not participate in checkpoint choice. A required run with no admissible checkpoint is a methodological failure, not a reason to evaluate whichever checkpoint happens to exist.

## 8. Foundation-model adaptation and replay

### 8.1 Target-size screen is target-only

The target-size screen measures the target method without replay exposure. Replay evidence cannot rank, reject, or tie-break a target size. A replay-only lineage or method change does not retroactively change P2/P3 target-size evidence or frozen target membership.

### 8.2 Post-selection replay lineage

Post-selection multi-head adaptation may include a separately identified replay source and replay head. The canonical default label mode is true reference/density-functional-theory (DFT) replay when the source provides those labels. Foundation pseudo-label replay is explicit opt-in, not a fallback for missing true labels.

When pseudo-label replay is used, pseudo targets are bound to the frozen foundation checkpoint/head, while a separate mandatory true-reference replay monitor remains independent evidence about physical retention. Changing replay mode, source content, split, prediction policy, foundation identity, or qualification changes replay lineage and invalidates affected post-selection evidence.

Replay remains scientifically distinct from the target dataset:

- replay configurations are not counted in target-size independent variable `N`;
- replay evidence is not a target-size ranking population;
- target and replay checkpoint/retention evidence remain distinct;
- replay retention is an admissibility constraint, not positive target-size ranking credit;
- there is no current target/replay training-head scalar; and
- hidden dependency-driven duplication of target frames is not allowed to redefine effective target exposure.

## 9. Campaign-common target checkpoint monitor

### 9.1 Role and parent population

Current foundation-model P5 uses one target checkpoint/model-control monitor, denoted `M_mon`, selected once from the protected neutral `OUTER_MONITOR` evidence role. It supplies no gradients. It is development/model-control evidence, not a P3 target-size evaluation rung and not a held-out CV fold.

The requested and current required monitor cardinality is **256 configurations**. The fact that `256` can also appear as a power-of-two target-size candidate has no semantic meaning. `M_mon` is not a target-size prefix, complement, evaluation rung, or folded-off portion of `T_selected`.

The target-size ladder is constructed exclusively from neutral `DEVELOPMENT` evidence. `M_mon` is constructed exclusively from protected `OUTER_MONITOR` evidence. For every configured target prefix `T_N`, the monitor must be separated not only by exact frame identity but by the complete P1 protected-relation authority. If a monitor frame and a target frame lie in the same correlation/duplicate/event/replica/structural-realization closure component, the allocation is invalid even when the frame UIDs differ.

The monitor must carry the canonical target labels required by the accepted checkpoint metrics. Protected membership without usable target labels is insufficient.

If the protected parent cannot realize 256 usable configurations with scientifically adequate condition/run/time coverage and the required separation, current P5 is infeasible. The method does not silently shrink the monitor, fall back to `DEVELOPMENT`, or split a protected relation merely to continue.

### 9.2 Coverage interpretation

The monitor is deliberately **coverage-oriented model-control evidence**, not an empirical-frequency estimator of the target distribution. Its accepted construction balances available condition/run strata and spreads observations through source time. The resulting checkpoint criterion therefore answers whether the fitted model remains acceptably accurate across the represented protected monitor coverage; it must not be interpreted as a frequency-weighted population risk estimate unless another accepted owner establishes that interpretation.

No generic minimum number of runs or units is invented here. Parent adequacy is assessed from the actual material/profile evidence, represented conditions/runs, independence grades, effective support, and temporal spread. The sampling algorithm cannot manufacture diversity absent from its protected parent.

### 9.3 One monitor across CV and final production

Exact `M_mon` membership is shared across every selected size, required CV fold, CV seed, and fresh final-production seed/run using this foundation-adaptation method. A fold-specific, selected-size-specific, final-specific, or M3-specific target checkpoint parent would define a different checkpoint method.

Sharing one monitor makes checkpoint/model-control decisions across folds statistically correlated. This is an explicit limitation, not independent replicate evidence. Post-selection held-out folds remain the evidence used for cross-validation acceptance after each fold representative is frozen.

## 10. Post-selection cross-validation

### 10.1 Question being answered

Post-selection cross-validation (CV) asks whether the **complete frozen foundation-adaptation method** associated with an admitted target membership performs acceptably on held-out development evidence whose independence strength and limitations are explicit.

“Held out” does not guarantee the strongest possible physical independence. A fold may rely on purged temporal evidence when stronger replicas/runs are unavailable; the associated limitation remains part of the claim.

### 10.2 Fold semantics

For every required selected size, fold, and seed:

- the CV universe is exact frozen `T_N`;
- inherited protected relations and purge constraints are preserved;
- `T_N` is allocated among gradient-training, held-out outer-evaluation, and accepted purge/exclusion roles; the external `M_mon` is not counted as a fold member;
- a fresh model/optimizer lineage is trained on the fold-authorized gradient domain;
- all fold-local fitted quantities, including foundation-residual target-head E0 corrections, are fitted without checkpoint-monitor or held-out labels;
- every target composition whose energy is consumed by training, monitor control, or held-out evaluation must have an identifiable composition-weighted E0 correction under the fold-authorized fit and accepted anchors;
- the same campaign-common `M_mon` supplies target checkpoint/model-control evidence;
- checkpoint choice is frozen before the held-out fold is evaluated; and
- every required fold/seed must satisfy the acceptance rule.

The current default design is **three folds**. Explicit policy may choose another `K>=2`; a fold-count change is a change in validation geometry and must be recorded. No missing/failed required fold or seed is discarded merely to obtain a favorable aggregate.

CV can accept or reject the frozen method. It cannot change `N`, `T_N`, the target-size order, or earlier P3 evidence.

## 11. Fresh final production and product membership

Acceptance does not promote a target-size or CV checkpoint into production. Final production starts a fresh model/optimizer lineage from the accepted foundation checkpoint/head and trains complete exact `T_selected` under the frozen production horizon and same shared foundation-adaptation/checkpoint method validated by CV.

Final production therefore uses the same campaign-common `M_mon` for target checkpoint control and the same independent true-reference replay-retention semantics where replay is enabled. P3 `M3` remains target-size model-selection evidence and is **not** repurposed as the final-production checkpoint monitor.

All final-training fitted quantities use the complete authorized final target-training membership only. Monitor, held-out, calibration, locked, and downstream qualification labels cannot enter those fits. Every governed target composition whose energy is consumed by final training or monitor control must satisfy the same composition-level E0 identifiability rule.

When multiple final seeds are available, the final-production owner decides the published member set before downstream qualification. Current policies may publish all already-qualified final seeds or one deterministic best already-frozen admissible representative under the accepted target-side production metric. Downstream physical, calibration, or locked evidence cannot add, remove, reorder, or choose committee members after the fact.

## 12. Downstream qualification is a separate scientific layer

Interpolation-style CV is necessary but insufficient evidence for an interatomic potential intended for molecular simulation. Downstream qualification may evaluate deployment/runtime parity, local potential-energy-surface response against matched references, relaxation topology and geometry fidelity, finite-temperature stability and protected structural behavior, uncertainty calibration where applicable, and an explicitly activated locked interpolation test.

These downstream analyses consume a frozen final publication. They do not feed backward into target size, training method, checkpoint choice, or final-product membership.

The numerical definitions of structural, dynamical, topological, and transport observables are owned by the corresponding `mdstats.analysis` method/architecture families. The MLFF branch invokes them; it does not redefine those analysis algorithms.

Current post-production qualification/release is defined for a single-size frozen experiment. A multi-size frozen design remains a comparative completed experiment but is not silently promoted into a release-qualified product family.

## 13. Material/profile applicability

The generic MLFF method permits material/profile contracts to define scientifically meaningful condition axes, required focus groups, environment classes, and applicability rules. These extensions may affect evidence interpretation and separately accepted weighting methods but cannot create a second target-size selector or silently rewrite the global target order.

For the historical Li/Na/K-LTA motivating application, important limitations include framework atoms numerically dominating global metrics even when mobile-ion behavior is scientifically important; hierarchical rather than complete Cartesian support over composition, temperature, strain, and regime; limited independence when only one trajectory exists per condition; fixed framework stoichiometry producing poorly identifiable elemental reference directions; and short trajectories or rare migration/site transitions creating explicit coverage limitations rather than synthetic evidence.

These application facts motivate focus-group, condition, correlation, composition-level E0 identifiability, and monitor-coverage evidence. They are not universal defaults for every material.

## 14. Validity domain and uncertainty

### 14.1 Target-size diagnostic

Within the exact configured candidate ladder, canonical target population, pre-order evidence, common P3 preparation, objective/weights, target-size optimizer-normalization policy, seed population, fidelity schedule, evaluation ladder, and practical-equivalence threshold, the diagnostic supports a comparative short-horizon statement about target-force error for the tested target memberships.

It supports an operator decision among qualified configured memberships. It does not prove monotonic behavior for an untested size or transferability to a different scientific method.

### 14.2 Post-selection CV

Post-selection CV supports a separate statement about the frozen foundation-adaptation method over the specific held-out folds and recorded independence regime. The checkpoint monitor is not part of the held-out estimand. Because the same `M_mon` is reused across folds, checkpoint decisions are correlated; fold evaluation remains the required held-out evidence after representative freeze.

### 14.3 What the method does not establish by itself

The core workflow does not by itself establish asymptotic training-size convergence, complete independence or exploration of all slow states, transfer to unsupported physical regimes, correct phase-transition temperatures or rare-event kinetics, long-time MD stability, calibrated predictive uncertainty, equivalence between interpolation CV and external challenge tests, universal atomic-reference identifiability, or a universal target size transferable to another foundation model, objective, optimizer protocol, replay method, or data-generation process.

The robust foundation-adaptation objective also does not imply equal target and replay influence. Aggregate influence depends on corpus membership, accepted stochastic exposure, residual magnitudes, and the nonlinear robust loss. No hidden target/replay scalar is inferred from a nominal “head ratio.”

### 14.4 Principal uncertainty and sensitivity sources

Material sources include density-functional-theory (DFT)/electronic-structure systematic error; energy/reference/derivative convention mismatch; temporal correlation and unresolved slow states; finite condition/rare-event/outer-monitor support; imperfect independence of held-out cohorts; shared-monitor model-selection correlation; candidate-ladder discretization; optimizer-seed and minibatch-order variation; short-horizon screening bias; practical-equivalence threshold; foundation checkpoint/head dependence; robust-objective/Huber-regime dependence; corpus-size-dependent target/replay exposure; atomic-reference conditioning, null spaces, prior/anchor dependence, and composition-level transfer; target/replay applicability mismatch; and numerical/runtime failure to realize the authenticated method.

These remain structured limitations/evidence rather than being compressed into one unsupported scalar uncertainty estimate.

## 15. Scientific falsification and reopen conditions

Evidence that forces reconsideration of the scientific formulation or its applicability includes:

- incompatible target labels treated as one training domain;
- incorrect stress/strain/sign/unit semantics;
- systematic exclusion of rare but valid configurations merely for atypicality;
- protected-relation leakage across incompatible evidence roles;
- candidate memberships that are not exact prefixes of the canonical order;
- candidate-dependent refitting of state that is supposed to be P3-common;
- checkpoint-monitor, held-out, calibration, or locked labels influencing training-domain fitting;
- a P5 target monitor drawn from `DEVELOPMENT`, `T_N`, `T_selected`, or P3 `M3` rather than protected `OUTER_MONITOR` evidence;
- monitor membership that overlaps any configured `T_N` exactly or through the canonical protected-relation closure;
- an under-supported monitor silently shrinking below the required 256 or silently changing role;
- fold/final-specific target checkpoint parents replacing the one common monitor;
- a foundation-model P5 objective carrying nontrivial `config_weight` or target/replay training-head scalar weighting;
- hidden replay/loader behavior duplicating target samples or overwriting authenticated optimizer semantics;
- foundation-residual E0 fitting that uses the wrong foundation head, uses monitor/held-out labels, silently assumes an unsupported correction, or yields a required composition-weighted correction that varies along an unanchored fit null direction;
- an executed mathematical loss/optimizer/exposure method materially different from the authenticated method;
- too few comparable target-size outcomes for the declared diagnostic;
- strong ceiling improvement showing that the target-size ladder did not demonstrate a plateau;
- post-selection CV failure under the frozen method; or
- downstream physical/deployment qualification contradicting intended use.

Scientific evidence is not repaired by relabeling old records. A material method change creates a new applicable method identity and requires bounded reconsideration of dependent evidence; independent P1/P2/P3 and frozen membership evidence remains reusable where its semantics did not change.

## 16. Reproducibility and provenance

A reproducible claim binds, as applicable:

- source occurrence/content and canonical label identity;
- energy/derivative/stress/reference conventions;
- physical conditions, reference-cell/strain context, quality and eligibility decisions;
- raw/event evidence and protected statistical relations;
- outer evidence roles and independence limitations;
- pre-order fitted selection evidence;
- exact `P_train/M3`, `pi_train`, `pi_eval`, `T_N`, and `M_i` identities;
- P3 common training preparation and screening/reducer policy;
- frozen selected memberships and role horizons;
- foundation checkpoint and exact selected foundation head;
- P5 robust objective family and global E:F:S coefficients;
- absence of P5 configuration/head-scalar weighting;
- authenticated target/replay memberships and exposure semantics;
- foundation-residual target-head E0 fit identity, accepted anchors if any, null-space evidence, and composition-level identifiability evidence;
- protected common target-monitor parent, policy, exact 256-frame membership, condition/run/time coverage evidence, and protected-relation separation;
- replay training/true-monitor lineage;
- CV fold/seed evidence; and
- fresh final-publication identity for downstream claims.

Content digests bind exact content and ancestry. They are identity/provenance mechanisms, not substitutes for scientific adequacy.

### 16.1 Revision provenance

The 2026-09-13 baseline was reconstructed against repository commit `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0`. This 2026-09-14 candidate revision was prepared on `fix/mlff-post-selection-method-restoration` after reconstruction showed that historically successful foundation multi-head adaptation used native MACE `UniversalLoss`, while current P5 forced a different loss family and had replaced the earlier common protected monitor with fold/final-local monitor constructions. The branch workplan records the triggering replay-forgetting evidence, historical applicability set, and dependent D2-D4 impact closure.

The first independent review of the candidate found two authority defects: composition-level E0 identifiability had been overstated as individual elemental identifiability, and compression of unchanged baseline prose had hidden several still-current P1/P2/P3 constraints. This revision repairs those defects while leaving the intended P5 restoration unchanged. Provenance motivates and scopes the revision; it does not itself prove scientific adequacy, so independent re-review remains required before integration.

## 17. D1 to D2 handoff

D2 shall concretize, without silently strengthening or weakening, at least these revised invariants:

1. P1/P2/P3 target-size and broader evidence-role semantics remain unchanged by this restoration, including explicit infeasibility/deferral outcomes and all existing protected-relation requirements.
2. Foundation-model P5 uses the robust energy/force/stress objective with global coefficients `1:10:1`, binary property masks, no nontrivial configuration-weight layer, and no target/replay training-head scalar.
3. D2 must define the robust loss mathematically, including property-specific units of every Huber threshold, residual normalization, nonlinear regimes, reduction, and stochastic exposure needed to distinguish a materially different objective.
4. Foundation-model P5 atomic references are selected-head foundation-residual fits over the authorized target gradient domain only. For every governed target composition vector `c`, D2 must require invariance of `c^T delta_e` over the unanchored fit null space or an explicitly accepted anchor for the relevant direction; failure is run/fold infeasibility. Individual elemental coefficients need not be unique when all required composition-weighted corrections are unique.
5. Replay geometry/source/label lineage remains separate from target membership; true-reference replay is the default, pseudo-label replay remains opt-in, and replay retention remains an admissibility constraint.
6. One deterministic coverage-oriented 256-frame target checkpoint monitor is drawn only from protected neutral `OUTER_MONITOR` evidence, is separated from every configured `T_N` by the full P1 relation authority, is common across CV/final runs, and has no gradient/fitting role.
7. Post-selection CV folds partition only frozen `T_N` among gradient, held-out evaluation, and accepted purge/exclusion roles. The current default is three folds, with explicit `K>=2` override permitted.
8. Fresh final production uses complete `T_selected`, the same common target monitor/checkpoint method, and fresh fitted/training state; P3 `M3` is not its checkpoint monitor.
9. Failure to realize required monitor support, composition-level E0 identifiability, protected separation, or the authenticated objective/exposure is a method infeasibility/nonconformance result, not permission for a silent fallback.

## 18. References

1. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, “MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields,” *Advances in Neural Information Processing Systems* **35**, 11423–11436 (2022), arXiv:2206.07697.
2. I. Batatia, P. Benner, Y. Chiang, et al., “A Foundation Model for Atomistic Materials Chemistry,” *Journal of Chemical Physics* **163**, 184110 (2025). DOI: 10.1063/5.0297006.
3. M. Kulichenko, B. Nebgen, N. Lubbers, J. S. Smith, et al., “Data Generation for Machine Learning Interatomic Potentials and Beyond,” *Chemical Reviews* **124**, 13681–13714 (2024). DOI: 10.1021/acs.chemrev.4c00572.
4. H. Flyvbjerg and H. G. Petersen, “Error Estimates on Averages of Correlated Data,” *Journal of Chemical Physics* **91**, 461–466 (1989). DOI: 10.1063/1.457480.
5. C. J. Geyer, “Practical Markov Chain Monte Carlo,” *Statistical Science* **7**, 473–483 (1992). DOI: 10.1214/ss/1177011137.
6. J. Racine, “Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation,” *Journal of Econometrics* **99**, 39–61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
7. D. R. Roberts, V. Bahn, S. Ciuti, et al., “Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure,” *Ecography* **40**, 913–929 (2017). DOI: 10.1111/ecog.02881.
8. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, “How to Validate Machine-Learned Interatomic Potentials,” *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.
9. C. Schran, K. Brezina, and O. Marsalek, “Committee Neural Network Potentials Control Generalization Errors and Enable Active Learning,” *Journal of Chemical Physics* **153**, 104105 (2020). DOI: 10.1063/5.0016004.
10. A. R. Tan, S. Urata, S. Goldman, J. C. B. Dietschreit, and R. Gomez-Bombarelli, “Single-Model Uncertainty Quantification in Neural Network Potentials Does Not Consistently Outperform Model Ensembles,” *npj Computational Materials* **9**, 225 (2023). DOI: 10.1038/s41524-023-01180-8.
