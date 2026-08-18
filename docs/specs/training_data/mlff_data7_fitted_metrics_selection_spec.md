---
title: "MLFF-DATA7: Fitted Metrics, Atomic References, Objectives, and Selection"
author: "mdstats project"
date: "2026-07-28"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    ```{=latex}
    \usepackage{microtype}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{enumitem}
    \setlist{nosep}
    ```
---

# MLFF-DATA7: Fitted metrics, E0 fits, objectives, and deterministic selection

## Status and scope

MLFF-DATA7 is the first stage that may fit statistics to an authorized training
domain and reduce that domain to a selected training subset. It consumes the
immutable DATA4-DATA6 evidence catalogs and introduces no MACE training file,
replay dataset, checkpoint, or test evaluation.

Every fitted object is local to exactly one canonical DATA5 training domain:

- the final development domain of one label domain; or
- the gradient-training domain of one cross-validation fold.

Outer checkpoint monitors, uncertainty-calibration cohorts, cross-validation
checkpoint monitors, held-out evaluation folds, locked tests, purge units, and
excluded frames SHALL NOT contribute to feature fitting, E0 fitting, difficulty
ranking, or selection.

The focused implementation tests use the supplied ASE 3.29.0 source distribution. ASE remains an external runtime dependency and is not bundled.

## Public contracts

DATA7 SHALL provide the following immutable records.

### `FeatureFitDomain`

Binds a final-development or cross-validation-training domain to its DATA5
partition, unit IDs, frame UIDs, label domain, and optional fold index.
Canonical domains are derived from DATA5 rather than supplied ad hoc.

### `FeatureMetricPolicyTemplate`

Defines the static metric algorithm without fitted values:

- enabled feature blocks;
- robust or standard centering/scaling;
- missing-value indicators;
- per-block weight;
- dimension normalization;
- optional per-block principal-component cap;
- deterministic SVD sign convention and tie rules.

The initial implementation supports the blocks `raw_physical`, `lta_frame`,
`mace_summary`, and `difficulty`. Model-derived blocks are optional and require
the matching checkpoint-bound DATA6 artifacts.

### `FittedFeatureMetric`

Stores fold-local or final-domain fitted block transforms and one transformed
frame vector for every frame in the fit domain. Robust scaling uses

$$
 z_j = \frac{x_j-\operatorname{median}(x_j)}{
              \max(\operatorname{IQR}(x_j), s_{\min})}.
$$

Standard scaling may instead use the mean and population standard deviation.
After optional PCA, each block is multiplied by

$$
  \sqrt{w_b/d_b},
$$

where \(w_b\) is the declared block weight and \(d_b\) the retained block
dimension. This prevents a high-dimensional descriptor block from dominating
solely because it has more coordinates.

PCA is fit by deterministic SVD. Each retained component is sign-normalized so
its largest-magnitude loading is positive. Ties are resolved by the smallest
feature index.

### `AtomicReferenceFitRecord`

Fits explicit elemental reference energies only on the authorized training
domain. For count matrix \(A\) and total-energy vector \(y\), the default fit is
the minimum-norm least-squares solution

$$
 \hat{\mathbf e}_0 = A^+ y.
$$

Optional nonnegative ridge regularization solves

$$
 \min_{\mathbf e_0}
 \lVert A\mathbf e_0-y\rVert_2^2
 + \lambda\lVert\mathbf e_0-\mathbf e_{0,\mathrm{prior}}\rVert_2^2.
$$

The record stores element order, explicit atomic-number mapping, rank, singular
values, null-space dimension, residual statistics, and transfer warnings.
Rank-deficient fits are allowed only when the policy explicitly permits a
fixed-composition-domain minimum-norm fit. Numerical E0 values are not assigned
physical meaning in the null space.

### Training objective and weight contracts

`TrainingObjectivePolicy` defines energy, force, and stress loss weights and
records the absence or presence of a species-aware custom force objective.
`ConfigurationWeightPolicy` defines condition balancing, event emphasis, and
quality modifiers. `TrainingWeightCatalog` stores per-frame configuration,
energy, force, and stress weights. Weights are normalized to a mean
configuration weight of one within each training domain.

Selection, exposure, and loss weight remain separate decisions.

### `CheckpointMetricPolicy`

Defines the metrics and constraints later used by DATA8-DATA9 checkpoint
selection. The initial record includes global target force RMSE, Li/Na/K force
constraints, energy, stress, worst-condition limits, and replay-retention
limits. DATA7 defines the reproducible policy but does not evaluate a trained
checkpoint.

### `SelectionBudgetPolicy`

Defines target training sizes and quota fractions for:

- mandatory condition anchors;
- representative anchors;
- Li/Na/K environment coverage;
- protected rare events;
- global fitted-metric FPS;
- foundation-model difficulty enrichment.

Fractions are interpreted as a deterministic weighted scheduling policy, not as
independent post-hoc selections. Mandatory anchors are inserted first. The
remaining category queues are interleaved by largest quota deficit. Duplicate
frames are skipped without consuming a category quota.

### `TrainingSelectionPlan`

Stores one deterministic master ordering with per-frame selection reasons. Each
requested training set is a strict prefix:

$$
 \mathcal T_{n_1}\subset\mathcal T_{n_2}\subset\cdots.
$$

The smallest legal target size is at least the mandatory-anchor count. An
infeasible requested size fails closed rather than silently dropping a required
condition.

### `SelectionCoverageReport`

For every ladder level, reports:

- selected frame count;
- represented condition strata;
- represented Li/Na/K environment classes;
- protected-event coverage;
- nearest-selected fitted-metric distance quantiles;
- maximum covering radius;
- selected-to-selected redundancy quantiles.

Coverage is descriptive evidence, not a guarantee of MLFF accuracy. The ladder
must later be evaluated through protocol-matched MACE learning curves.

### `Data7PreparationBundle`

Binds the DATA4-DATA6 lineages, canonical training domain, fitted metric, E0
fit, objective/weight policies, checkpoint policy, selection plan, and coverage
reports. One bundle is produced per final development domain and per
cross-validation training fold.

## Feature construction

`raw_physical` includes finite DATA4 thermodynamic, force, stress, cell, and
strain scalars with explicit missing indicators. Total energy is excluded from
the default distance metric because composition-dependent offsets can dominate
geometry coverage; energy per atom may be enabled explicitly.

`lta_frame` uses DATA6 named frame descriptors and their missing mask.

`mace_summary` reads the checkpoint-bound per-atom descriptor sidecar and
constructs deterministic configuration summaries: global mean and standard
deviation plus per-Li, per-Na, and per-K means when present. Missing species are
represented by zeros and explicit presence indicators.

`difficulty` uses only DATA6 training-domain residuals. It SHALL never be
materialized from blinded monitor, calibration, evaluation, or locked-test
records.

## Selection algorithm

1. Derive one canonical `FeatureFitDomain` from DATA5.
2. Assemble raw feature blocks only for that domain.
3. Fit the block-local scalers and optional PCA using that domain only.
4. Fit the domain-local atomic reference mapping.
5. Construct condition strata from DATA5 partition conditions.
6. Add one mandatory deterministic anchor per represented stratum.
7. Build representative, species-environment, rare-event, fitted-metric FPS,
   and difficulty queues.
8. Interleave queues according to `SelectionBudgetPolicy` while preserving
   deterministic tie ordering by frame UID.
9. Fill any residual budget by global FPS, then stable frame-UID order.
10. Define every requested dataset as a prefix of the one master order.
11. Compute coverage reports without inspecting any held-out evidence.

Farthest-point sampling selects

$$
 i^*=\arg\max_{i\notin S}\min_{j\in S}d(\mathbf z_i,\mathbf z_j).
$$

Ties within floating-point tolerance are resolved by lexicographically smallest
frame UID.

The implementation SHALL NOT construct a complete ordering when the largest
requested ladder contains only $K$ frames. It maintains one nearest-selected
distance per candidate, updates that vector after every accepted point, and
stops after the largest requested prefix is complete. For $N$ candidates and
fitted dimension $d$, exact deterministic FPS therefore costs

$$
 O(NKd),
$$

not the $O(N^3d)$ cost of repeatedly rebuilding all candidate-to-selected
distances while ranking every candidate. Candidate-distance updates are
chunked to a bounded temporary-memory budget.

Atomic-environment selection is frame-valued. Provider-owned atom descriptors
are therefore aggregated to one frame summary before bounded FPS; no complete
atom-level ordering may be constructed. Coverage updates reuse the same
incremental nearest-distance vector across ladder prefixes. Selected-neighbor
diagnostics operate only on the bounded $K\times K$ selected matrix.

Production orchestration may cache checkpoint-bound MACE descriptor summaries
across final and fold-local domains. A descriptor sidecar is read and reduced
at most once per frame/species-signature within one invocation. Domain-local
scaling and PCA remain independently fitted and are never shared across folds.

## Failure rules

DATA7 fails closed when:

- a requested domain is not canonical DATA5 training evidence;
- a fitted feature block is unavailable or checkpoint-incompatible;
- a fitted transform receives a monitor, calibration, evaluation, purge, or
  locked-test frame;
- an E0 fit lacks energy labels or elemental support;
- rank deficiency is disallowed by policy;
- a requested ladder size is smaller than mandatory coverage;
- sidecar digests or lineage records do not match;
- target sizes are not strictly increasing;
- selection cannot produce the requested largest size.

## Non-goals

DATA7 does not write extended XYZ, select replay data, run MACE, choose a
checkpoint, rotate epoch datasets, activate tests, or perform active learning.
Those remain DATA8-DATA10 responsibilities.

# DATA9A7d amendment: focus groups and generic extension coverage

DATA7 selection and decision policies no longer define cations as a universal
material class. Atom groups marked with `mlff_focus`, `training_focus`, or
`validation_focus` may receive explicit difficulty, environment-coverage,
objective, or checkpoint treatment. If no focus group is declared, all species
present in the authorized domain are treated uniformly.

`TrainingObjectivePolicy` and `CheckpointMetricPolicy` use generic focus-group
and focus-atomic-number fields. Historical cation-named fields are accepted only
when restoring v1 evidence and are exposed as deprecated Python aliases.

Selection coverage records generic `represented_environment_classes` supplied
by optional profile providers. LTA site classes are one namespaced provider
output, not a core coverage schema.

## DATA9A9b production orchestration

DATA9A9b does not alter DATA7 fitting or selection mathematics. It freezes every
canonical final-development and fold-training `FeatureFitDomain` plus the exact
DATA7 policy set, writes one native `Data7PreparationBundle` per domain, and
binds each file through a `ProductionData7ArtifactRecord`. Restart may reuse a
bundle only when its file SHA-256, bundle digest, domain digest, DATA6 lineage,
and native serialization all verify. Any invalid DATA7 artifact invalidates the
production DATA8 tree.

Lineage-identical DATA7 scientific artifacts are shared across optimizer seeds,
training modes, and process restarts through a recipe-keyed cache. The recipe
includes all DATA7 inputs and policies but excludes DATA8-only controls. A
shared artifact is reused only after file SHA-256, native bundle parsing,
domain identity, and complete DATA4-DATA6 lineage verification. This changes
multi-variant orchestration from repeated $O(VDN)$ DATA7 work to one $O(DN)$
build plus variant-specific DATA8 construction, where $V$ is the number of
training variants and $D$ the fixed domain count.
