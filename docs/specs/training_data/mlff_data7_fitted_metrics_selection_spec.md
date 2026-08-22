---
title: "MLFF-DATA7: Fitted Metrics and Target-Subset Inputs"
author: "mdstats project"
date: "2026-08-21"
geometry: margin=0.8in
fontsize: 10pt
---

# MLFF-DATA7: fitted metrics, atomic references, objectives, and subset inputs

## Scope

DATA7 is the first layer allowed to fit statistics to one canonical DATA5 training domain. It prepares fitted products consumed by the current multi-view target-subset chain; it does **not** choose target membership or target size.

Every fitted object is local to exactly one canonical training domain:

- the final-development gradient-training domain for one label domain; or
- the gradient-training domain of one cross-validation fold.

Outer/common monitors, cross-validation checkpoint monitors, held-out evaluation folds, uncertainty-calibration cohorts, purge-only units, locked tests, and excluded frames SHALL NOT contribute to feature fitting, E0 fitting, label-derived difficulty evidence, or other fitted target-subset inputs.

## Public records

### `FeatureFitDomain`

Binds one canonical final-development or cross-validation training domain to its DATA5 partition identity, unit IDs, ordered frame UIDs, label domain, and optional fold index. Domains are derived from DATA5 and are not caller-supplied ad hoc.

### `FeatureMetricPolicyTemplate`

Defines static metric behavior without fitted values, including:

- enabled feature blocks;
- centering/scaling method;
- missing-value indicators;
- per-block weights;
- dimension normalization;
- optional principal-component caps;
- deterministic SVD sign/tie rules;
- distance dtype/tolerance semantics.

Material/profile-specific blocks are optional and require the corresponding current provider contracts.

### `FittedFeatureMetric`

Stores one domain-local fitted transform and transformed coordinates for the frames authorized by that fit domain. Robust scaling may use

$$
z_j=\frac{x_j-\operatorname{median}(x_j)}{\max(\operatorname{IQR}(x_j),s_{\min})}.
$$

Standard scaling may use mean and population standard deviation. After optional PCA, block \(b\) is weighted by

$$
\sqrt{w_b/d_b},
$$

where \(w_b\) is the declared block weight and \(d_b\) the retained dimension. PCA uses deterministic SVD and deterministic component-sign/tie normalization.

### `AtomicReferenceFitRecord`

Fits elemental reference-energy corrections only on the authorized training domain. For count matrix \(A\) and energy vector \(y\), the default fit is the minimum-norm least-squares solution

$$
\hat{\mathbf e}_0=A^+y.
$$

When policy permits regularized transfer toward prior values,

$$
\min_{\mathbf e_0}\lVert A\mathbf e_0-y\rVert_2^2+\lambda\lVert\mathbf e_0-\mathbf e_{0,\mathrm{prior}}\rVert_2^2.
$$

The record stores element order, explicit atomic-number mapping, rank, singular values, null-space dimension, residual statistics, solver/tolerance identity, and transfer limitations. Rank-deficient fits are permitted only under an explicit policy; null-space components are not assigned physical meaning.

### Training objective and weight records

`TrainingObjectivePolicy` owns loss family, energy/force/stress weights, head weights, normalization, robust-loss behavior, and missing-label handling.

`ConfigurationWeightPolicy` and `PropertyWeightPolicy` own condition/regime/event/quality and property-specific weights. `TrainingWeightCatalog` stores realized per-frame/per-property weights for the fit domain.

Target membership, loss weighting, and runtime exposure are separate decisions.

### `CheckpointMetricPolicy`

Defines the checkpoint metrics and hard admissibility constraints later used by the training/evaluation layer. It may include global target force error, focus-group/species errors, energy/stress, worst-condition, replay-retention, and physical-integrity constraints.

DATA7 defines/serializes the policy identity but does not evaluate trained checkpoints.

### `TargetSubsetInputBundle`

The current DATA7 terminal product. It binds:

- the canonical `FeatureFitDomain`;
- DATA4-DATA6 source/feature/prediction lineage;
- fitted feature metric;
- atomic-reference fit where applicable;
- objective and weight policies/catalogs;
- checkpoint metric policy;
- condition/provenance/correlation identities;
- event/environment/focus-group evidence;
- representative-density/utility inputs;
- diversity inputs;
- training-domain difficulty evidence;
- hard-obligation/applicability inputs required by the current multi-view selector.

The bundle SHALL contain no target order, selected-frame list, requested target-size ladder, or selected target size.

## Feature construction

`raw_physical`-class inputs may contain finite DATA4 thermodynamic, force, stress, cell, and strain scalars with explicit missing indicators. Total energy is excluded from a distance metric by default when composition offsets would dominate geometry; energy-per-atom use requires explicit policy.

Structural/profile blocks consume current provider outputs and remain namespaced. Material-specific concepts such as LTA sites, rings, or cation groups are extensions rather than universal core schema.

Foundation-model descriptor summaries may be computed where current DATA6 contracts authorize them. Label-derived difficulty uses only predictions and DFT labels from the current `FeatureFitDomain`; monitor, held-out, calibration, and locked-test residuals remain blinded.

## Domain-local fitted preparation algorithm

For each canonical training domain:

1. validate the DATA5 domain and forbidden-role exclusions;
2. assemble raw/provider feature blocks authorized for that domain;
3. fit scalers and optional PCA on that domain only;
4. fit the atomic-reference mapping where applicable;
5. derive condition/provenance/event/environment/focus-group evidence from authorized upstream products;
6. derive training-domain-only difficulty evidence;
7. construct representative/diversity/hard-obligation inputs under their current policies;
8. serialize `TargetSubsetInputBundle` with deterministic lineage/digests.

No step chooses target membership. The next scientific membership authority is MVSEL2/REPAIR2.

## Focus groups and material extensions

Atom groups marked for training or validation focus may receive explicit environment, difficulty, objective, or checkpoint treatment. If no focus group is declared, species present in the authorized domain follow the generic policy.

Current records use generic group/atomic-number fields. LTA-specific cation/site/environment classes are profile/provider outputs, not core DATA7 types.

## Production sharing and restart

Lineage-identical DATA7 fitted products may be shared across optimizer seeds or training variants when every input/policy identity matches. Domain-local scalers, PCA, E0 fits, and other fitted quantities SHALL NOT be shared across different fold/final training domains merely for performance.

A persistent DATA7 artifact is reusable only after its content digest, native serialization/schema, domain identity, and complete upstream lineage verify. Corrupt, stale, or incompatible artifacts are reconstructed; they are not migration authorities for obsolete campaign generations.

## Failure rules

DATA7 fails closed when:

- the requested domain is not canonical DATA5 gradient-training evidence;
- a fitted feature/provider block is unavailable or incompatible;
- a fitted operation receives monitor, held-out, calibration, purge-only, or locked-test frames;
- an E0 fit lacks required labels/support or violates its rank policy;
- provider/prediction sidecar digests do not match;
- a policy attempts to encode target membership or target size inside DATA7;
- persisted fitted artifacts fail lineage/schema/content validation.

## Explicit non-ownership

DATA7 does not:

- produce `TrainingSelectionPlan` or any alternative master target ordering;
- apply a quota/FPS selector to choose final target membership;
- choose target-training size;
- write final MACE target/replay training bundles;
- run training, checkpoint evaluation, sealed tests, or active learning.

Representative coverage, diversity/FPS, environment coverage, protected events, condition balance, and difficulty remain valid scientific inputs, but their membership effect is resolved only by the sole current multi-view selector policy.
