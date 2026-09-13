---
title: "mdstats MLFF Scientific Method"
artifact_level: "D1 scientific formulation"
status: "reconstructed current method - proposed for human review"
reconstructed_against_commit: "9fd82b0ed40990d56716a393aa3f7db0a2ff44d0"
date: "2026-09-13"
---

# mdstats MLFF Scientific Method

## 1. Purpose and scope

This paper states the scientific method implemented by the machine-learned force-field (MLFF) branch of mdstats. It reconstructs the scientific formulation that historically accumulated across the MLFF architecture manual, current specifications, accepted workplans, implementation evidence, and code.

The method concerns four linked questions:

1. how atomistic reference configurations and labels are admitted as scientific evidence;
2. how correlated molecular-dynamics data are separated into development and independent evaluation roles without fabricating independence;
3. how a target training-set size is studied under a controlled fine-tuning protocol; and
4. how the selected training method is independently validated before fresh final production.

This is a D1 document. It owns the scientific question, observables, assumptions, evidence semantics, validity domain, uncertainty, and permitted scientific claims. Numerical realization is delegated to `mlff_numerical_algorithmic_method.md`. Software ownership, persistence, orchestration, and runtime architecture are delegated to the MLFF architecture manual and current specifications.

## 2. Background

### 2.1 Machine-learned interatomic potentials

An atomistic machine-learned potential approximates a potential-energy surface for a configuration consisting of chemical species, atomic positions, periodic cell information, and boundary conditions. The learned scalar energy is used to obtain forces by differentiation with respect to atomic positions and, when supported, stress by the corresponding cell/strain derivative under the adopted source convention.

For a configuration `x`, mdstats treats the reference energy `E(x)`, atomic forces `F_i(x)`, and stress `sigma(x)` as related labels from one accepted numerical convention. Labels with incompatible electronic-structure, energy-reference, derivative, stress-sign, unit, or tensor conventions are not silently combined. The exact source-label contract is specification-owned.

The present workflow fine-tunes a MACE foundation model rather than defining a new interatomic-potential architecture. MACE is an equivariant message-passing model designed to represent atomistic energies and their derivatives. The scientific contribution of mdstats is therefore principally the evidence design, data-size experiment, fine-tuning protocol, validation logic, and provenance around the underlying model rather than a new neural-network ansatz.

### 2.2 Correlated atomistic trajectories

Frames drawn from molecular dynamics (MD) are not independent and identically distributed observations. Adjacent structures may be nearly identical, rare events may occupy extended windows, and slowly evolving structural states may remain correlated over a large fraction of a run. A random frame split can consequently put near-replicates on both sides of an evaluation boundary and understate generalization error.

mdstats therefore treats correlation, duplicate geometry, protected event windows, replica/run relationships, and slow structural state as evidence constraints. Autocorrelation-derived effective-sample estimates are diagnostics, not proofs of independence. When the available evidence cannot establish strong independence, the workflow records that limitation instead of promoting temporal separation into a stronger scientific claim.

### 2.3 Why target size is an experiment

Training-set cardinality is not treated as a storage parameter. It is a scientific independent variable in a controlled comparative experiment. If changing `N` also changes the data-selection rule, preparation fit, optimizer progress, evaluation population, or hidden loader exposure, an observed error difference cannot be cleanly interpreted as a data-size effect.

The current design therefore defines candidate sets as nested prefixes of one deterministic training order and shares one common fitted preparation across candidates. The optional automatic screen is a diagnostic experiment that recommends a size; it does not itself decide the final experimental design.

## 3. Scientific objects and observables

### 3.1 Configuration and label evidence

A usable reference frame comprises at least:

- atomic species and coordinates;
- periodic cell and boundary-condition information;
- an accepted target energy channel;
- forces when required by the training objective;
- stress when required and scientifically compatible;
- source provenance and numerical-quality evidence;
- immutable occurrence, geometry, and label identities.

Occurrence identity, geometry identity, and label identity are distinct. Two records may be different source occurrences yet represent duplicate geometry; conversely, identical geometry associated with incompatible label conventions must not be treated as interchangeable training evidence.

The current pre-target statistical substrate is compatibility-neutral with respect to the retired per-domain target-size architecture: it does not create separate target-size or cross-validation authorities keyed by a historical `label_domain_id`. This does **not** mean incompatible physical labels may be mixed. Compatibility is resolved at source/label acceptance; once canonical usable evidence has been accepted, target-size construction does not introduce a second compatibility-domain partition axis.

### 3.2 Primary target-size observable

The primary response used by the automatic target-size diagnostic is target-force root-mean-square error (RMSE), reported in meV/Angstrom, on an exact development/model-selection evaluation population. Conceptually,

$$
\mathrm{RMSE}_F = \sqrt{\frac{1}{K}\sum_{k=1}^{K}\left(F^{\mathrm{pred}}_k-F^{\mathrm{ref}}_k\right)^2},
$$

where `k` indexes the admitted force components in the exact evaluation membership. The numerical algorithm and unit conversion are D2 concerns.

Energy and stress remain part of the physical training method when enabled, and downstream physical/structural qualification remains essential, but neither substitutes for the frozen target-force response used by the automatic target-size comparison.

### 3.3 Training objective layers

The scientific training objective separates three meanings that must not be conflated:

1. **global property coefficients** expressing the relative energy/force/stress objective;
2. **per-configuration weights** expressing configuration-level sampling importance; and
3. **local property availability masks** indicating whether a property is present for a frame.

A missing property contributes zero through its local availability mask. It is not represented by changing the global scientific objective. Configuration weighting likewise does not redefine the relative meaning of energy, force, and stress residuals.

### 3.4 Atomic reference energies

Elemental reference energies (`E0`) are fitted quantities, not universal source constants. For foundation-model fine-tuning, mdstats fits corrections to the foundation model's reference-energy baseline from authorized training evidence rather than replacing that baseline with a globally refitted unrelated decomposition. This preserves the distinction between the foundation model's learned energy reference and the target-data correction required by the current training domain.

Every fold-local or final-training fit is restricted to its authorized gradient-training domain. Held-out evaluation, calibration, and locked-test labels cannot contribute to the fit.

## 4. Evidence roles and independence

### 4.1 Role separation

The workflow separates evidence used to construct a method from evidence used to judge it. At a high level the roles are:

- development/training evidence;
- checkpoint-monitor evidence authorized to control model selection within a training job;
- held-out cross-validation evidence;
- uncertainty-calibration evidence where configured;
- locked final-test evidence; and
- purged or excluded evidence.

A frame that supplied a gradient is not independent validation evidence for that model. A held-out fold cannot choose the checkpoint at which it is evaluated. Locked-test evidence cannot influence data membership, target size, fitted preparation, stopping, checkpoint choice, calibration-policy choice, or acquisition decisions.

### 4.2 Protected relations

Before allocating incompatible evidence roles, mdstats preserves relations that make observations scientifically unsafe to split independently. Current protected relations include the applicable correlation units, exact geometry duplicates, protected event windows, and accepted replica/structural-realization relations. Their transitive closure is treated as indivisible for the target-size development split.

This rule is intentionally stronger than checking pairwise overlap after allocation: all inherited relations are resolved before any component is assigned to training or evaluation.

### 4.3 Effective sample size and slow states

For a stationary scalar observable with integrated autocorrelation time `tau_int` measured in stored-frame units, the familiar diagnostic

$$
N_{\mathrm{eff}} \approx \frac{N}{2\tau_{\mathrm{int}}}
$$

is useful for estimating the loss of independent information caused by serial correlation. mdstats does not interpret this number as proof that a slow structural coordinate, rare-event process, or metastable state has decorrelated. Independence grades and limitation codes therefore remain part of the scientific evidence.

## 5. Target-size experiment

### 5.1 Population

The target-size population `U_size` is built from currently eligible, canonically labeled development evidence. Physical-only frames without the required canonical labels do not enter the target-size training experiment.

`U_size` is partitioned once into:

- `P_train`, the target-training pool from which every candidate set is drawn; and
- `M3`, the largest target-size model-selection evaluation reserve.

The split must preserve all inherited protected relations and exact disjointness. Failure to construct the requested reserve without violating those constraints is a scientific infeasibility outcome, not permission to weaken the split.

### 5.2 One training order and nested candidates

One deterministic training order

$$
\pi_{\mathrm{train}} = (x_1,x_2,\ldots,x_{|P_{train}|})
$$

is constructed before candidate training. The candidate of size `N` is exactly

$$
T_N = \pi_{\mathrm{train}}[:N].
$$

Thus for `N_a < N_b`, `T_{N_a}` is a strict prefix of `T_{N_b}` whenever both candidates exist. Increasing target size only adds configurations; it never swaps one data-selection solution for another. This nested design makes `N` the intended target-data-cardinality variable.

Priority information may order the pool, and deterministic condition balancing may preserve support across represented conditions, but candidate qualification is governed only by declared hard-support obligations and label usability. Diagnostic coverage or novelty quantities cannot silently become additional gates.

### 5.3 Nested evaluation ladder

A single deterministic evaluation order over `M3` defines nested evaluation populations

$$
M_1 \subset M_2 \subset M_3.
$$

The staged screen may therefore increase both training fidelity and evaluation support while preserving membership ancestry. The evaluation ladder is model-selection evidence only; it is not post-selection cross-validation and is not an independent final-test cohort.

### 5.4 Common preparation

Before candidate trajectories begin, the experiment freezes one common fitted preparation over the authorized target-size preparation domain. Candidate size and optimizer seed do not refit this common state. The intent is to prevent candidate-dependent preprocessing from becoming a hidden independent variable.

The common preparation includes the scientific ingredients needed by all candidates, such as the objective definition, configuration weighting, atomic-reference fit, selected foundation model/head identity, and other accepted fitted inputs. Candidate projection changes membership; it does not invent a second fitted method.

## 6. Automatic target-size diagnostic

### 6.1 Scientific interpretation

The automatic target-size stage asks a deliberately limited question:

> Under the frozen short-horizon fine-tuning method, paired optimizer-seed design, nested candidate memberships, and staged target-only evaluation populations, which configured target size is practically preferred by target-force error?

It does **not** estimate a universal learning curve, prove asymptotic convergence, establish long-time molecular-dynamics stability, or determine that larger datasets have no scientific value.

### 6.2 Paired optimizer seeds

Every active candidate is evaluated under the same configured optimizer-seed population. A candidate score is formed only when all required seeds at the boundary produce valid comparable outcomes. A numerical failure is not silently dropped to improve the mean.

Using paired seeds reduces avoidable comparison noise because candidates experience the same seed set, but the seed mean is a comparative estimator, not a conventional confidence interval or a claim that optimizer randomness is the only source of uncertainty.

### 6.3 Successive fidelity

Candidates are screened through an ordered sequence of exact training horizons and evaluation memberships. Early stages reduce the candidate set; surviving trajectories continue to later boundaries. The scientific trajectory for one `(N, optimizer_seed)` is continuous across boundaries rather than being reconstructed as unrelated rung-local trainings.

The exact horizon values, evaluation sizes, seed set, and candidate ladder are experiment configuration/specification data. Changing them changes the target-size diagnostic protocol.

### 6.4 Practical equivalence and the configured ceiling

At a comparison boundary, errors within a configured practical-equivalence tolerance `epsilon` are treated as scientifically indistinguishable for target-size ranking, and the smaller `N` is preferred. The policy expresses a parsimony judgment: do not pay for more target data when the observed improvement is smaller than the declared material difference.

At the terminal boundary, if the largest configured size `N_max` is materially better than every other successful finalist by more than `epsilon`, the diagnostic still recommends `N_max` because it is the best tested option. It simultaneously records that the experiment did **not** demonstrate a plateau within the configured ladder. The configured ceiling is therefore a practical budget boundary, not an asymptotic-convergence claim.

If too few complete comparable candidates remain, the correct outcome is no automatic recommendation.

### 6.5 Recommendation versus decision

The automatic reducer produces evidence and a recommendation. The operator owns the provisional scientific design and may select one or more qualified configured sizes, with explicit cross-validation and production horizons. This distinction is deliberate: a short-horizon force-error diagnostic is informative but does not contain all scientific judgment relevant to the final experiment.

At `cross-validate` admission, the chosen collection is frozen. Each selected `N` is bound to its exact `T_N` membership and its role-specific training horizons. Post-selection evidence cannot retrospectively alter that target-size decision.

## 7. Post-selection validation

### 7.1 Purpose

Post-selection cross-validation (CV) answers a different question from the target-size diagnostic. It asks whether the complete frozen training method associated with a selected target membership generalizes across protected held-out development evidence.

It does not rerun target-size selection.

### 7.2 Fold semantics

For each selected size and each CV fold:

- a fresh model/optimizer lineage is trained on the fold-authorized gradient-training partition;
- a distinct nested checkpoint monitor is drawn only from training-eligible evidence;
- the held-out evaluation fold is not used for fitting, stopping, checkpoint selection, or target-size decisions;
- fold-local fitted quantities, including applicable atomic-reference corrections, are fitted without held-out labels; and
- evaluation occurs only after checkpoint choice for that fold is frozen.

Protected relations and purge constraints remain part of fold construction. The resulting fold errors are evidence about the frozen method, not additional optimizer feedback.

### 7.3 Fresh final production

Acceptance of a selected method does not promote a screening or CV checkpoint into the final model. Final production is a fresh training lineage on the exact selected target membership under the accepted production protocol. Where multiple seeds are published as a committee, committee membership is frozen before downstream qualification; qualification does not rank seeds backward into model construction.

## 8. Replay and foundation-model fine-tuning

The production fine-tuning method may include a separately identified true-label replay lineage from the foundation model's pretraining domain. Replay serves retention/stability purposes and is scientifically distinct from the target dataset whose size is being studied.

For this reason:

- replay frames are not counted as `N` in the target-size independent variable;
- replay evidence is not a target-size ranking population;
- target and replay monitoring roles remain distinct;
- replay balancing must not silently duplicate target samples and thereby change effective target exposure; and
- the native weighted energy/force/stress objective must remain the method actually executed.

The exact replay construction and execution realization are D2/D3 concerns.

## 9. Validity domain and uncertainty

### 9.1 What the target-size result supports

Within the configured candidate ladder, data source, foundation model/head, objective, optimizer-normalization rule, seed population, common preparation, fidelity schedule, evaluation reserve, and practical-equivalence threshold, the diagnostic supports a comparative statement about target-force error for the tested candidates.

It supports an operator decision among qualified configured target memberships. Post-selection CV then supports a separate statement about the frozen method's predictive behavior over its protected held-out development folds.

### 9.2 What it does not support

The method does not by itself establish:

- asymptotic convergence with respect to training-set size;
- independence of all MD frames or complete exploration of slow states;
- transfer to compositions, thermodynamic states, defect classes, strains, or reaction mechanisms absent from the evidence;
- long-time MD stability;
- calibrated predictive uncertainty;
- correct phase-transition temperatures or rare-event kinetics;
- equivalence between interpolation CV and external challenge tests; or
- a universal `N` transferable to a different foundation model, objective, or data-generation process.

These require separate evidence.

### 9.3 Principal uncertainty sources

Important uncertainty and sensitivity sources include:

- temporal correlation and unresolved slow structural states;
- finite and condition-limited evaluation support;
- discretization of the candidate-size ladder;
- optimizer-seed variation;
- the short-horizon nature of the automatic screen;
- the chosen practical-equivalence tolerance;
- foundation-model and selected-head dependence;
- training-objective and configuration-weight choices;
- atomic-reference identifiability;
- DFT/source-label systematic error;
- incomplete support for rare events or deployment conditions; and
- downstream numerical/runtime fidelity to the declared method.

The workflow records these through role/independence evidence, rank and residual diagnostics, typed numerical failures, exact protocol identities, post-selection CV, and downstream qualification rather than compressing them into one scalar uncertainty number.

## 10. Falsification and scientific failure semantics

Evidence that should force scientific reconsideration includes:

- protected-relation leakage across incompatible evidence roles;
- candidate membership that is not an exact prefix of the canonical order;
- a candidate-dependent fitted preparation that was supposed to be common;
- held-out labels influencing fitting or checkpoint choice;
- hidden replay or loader behavior that changes target exposure;
- a materially different executed loss/optimizer method than the authenticated method;
- inability to construct enough comparable candidate outcomes;
- strong ceiling improvement showing no observed plateau inside the tested ladder;
- post-selection CV failure under the frozen method; or
- downstream physical validation demonstrating behavior incompatible with intended deployment.

Such evidence is not repaired by relabeling old results. A scientific-method change creates a new protocol identity and requires new applicable evidence.

## 11. Reproducibility and provenance

A reproducible MLFF scientific claim binds at minimum the accepted source/label evidence, protected statistical relations, target-size experiment definition, canonical training/evaluation orders, candidate memberships, common preparation, optimizer-seed/fidelity policy, executed training protocol, post-selection fold design, and final-production identity.

Content digests are used throughout mdstats to bind these objects. A digest is an identity mechanism, not a substitute for scientific validation: it proves which exact content was used, while the scientific method determines whether that content is appropriate evidence.

This reconstruction is based on the current repository at commit `9fd82b0ed40990d56716a393aa3f7db0a2ff44d0`. The accompanying reconstruction-evidence note identifies current and historical sources and explicitly excludes retired target-size designs.

## 12. References

1. I. Batatia, D. P. Kovacs, G. N. C. Simm, C. Ortner, and G. Csanyi, "MACE: Higher Order Equivariant Message Passing Neural Networks for Fast and Accurate Force Fields," *Advances in Neural Information Processing Systems* **35** (2022); arXiv:2206.07697.
2. H. Flyvbjerg and H. G. Petersen, "Error Estimates on Averages of Correlated Data," *Journal of Chemical Physics* **91**, 461-466 (1989). DOI: 10.1063/1.457480.
3. J. Racine, "Consistent Cross-Validatory Model-Selection for Dependent Data: hv-Block Cross-Validation," *Journal of Econometrics* **99**, 39-61 (2000). DOI: 10.1016/S0304-4076(00)00030-0.
4. D. R. Roberts, V. Bahn, S. Ciuti, et al., "Cross-Validation Strategies for Data with Temporal, Spatial, Hierarchical, or Phylogenetic Structure," *Ecography* **40**, 913-929 (2017). DOI: 10.1111/ecog.02881.
5. J. D. Morrow, J. L. A. Gardner, and V. L. Deringer, "How to Validate Machine-Learned Interatomic Potentials," *Journal of Chemical Physics* **158**, 121501 (2023). DOI: 10.1063/5.0139611.

Repository specifications and the MLFF architecture manual provide implementation-specific provenance beyond these external scientific references.
