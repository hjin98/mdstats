---
title: "Periodic Species-Density Estimation"
subtitle: "Stage 11E1: registered triclinic Gaussian measures, derivatives, support, uncertainty, and bandwidth ladders"
author: "mdstats"
date: "2026-07-25"
version: "0.19.99a0"
status: "implemented"
toc: true
toc-depth: 3
numbersections: true
geometry: margin=0.82in
fontsize: 10pt
colorlinks: true
header-includes:
  - |
    \usepackage{amsmath}
    \usepackage{amssymb}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
---

# Purpose and stage boundary

Stage 11E1 converts one immutable Stage-11E0b species sample catalog into a
periodic, time-weighted density measure on one certified registered triclinic
domain. The canonical implementation is:

```python
mdstats.analysis.density.species
```

The scientific path is:

```text
FrameworkAlignedIonSampleCatalog
    + PeriodicDensityDomain
    + explicit GaussianKernelCovariance ladder
    + SpeciesDensityOptions
        -> normalized triclinic lattice-image KDE
        -> number and probability density
        -> score covector and metric-raised gradient vector
        -> density Hessian and local support
        -> image-tail and normalization certificate
        -> optional complete-system block uncertainty
```

This stage does **not** identify modes, ridges, basins, saddles, site labels,
transition events, free energies, barriers, or rates. Those remain Stage 11E2
and later responsibilities.

# Source and coordinate contract

## One source-bound species catalog

The input catalog contains one atomic number and one registration signature.
Let its accepted position evidence be

$$
\{(s_j,w_j,f_j,a_j)\}_{j=1}^{N},
$$

where:

- $s_j\in[0,1)^3$ is the registered wrapped fractional coordinate;
- $w_j\ge 0$ is the represented-time weight;
- $f_j$ and $a_j$ retain source frame and atom identities.

Stage 11E1 accepts the `position` or exact `joint` evidence channel. It never
reconstructs a different temporal, structural, or force subset.

`PeriodicDensityDomain.registration_signature` must equal the catalog
registration signature. Shape-compatible data from another registration fail
closed.

## Physical and reference-material measures

One domain declares exactly one coordinate-volume measure:

```text
physical_cartesian
reference_material
```

For a fixed registered cell $H$, both measures use the Cartesian volume

$$
V=\det H>0.
$$

`physical_cartesian` means the cell is physically fixed over the pooled
samples. It is rejected when the declared registered-cell variation exceeds
the fixed-cell tolerance.

`reference_material` means every sample has already been mapped into one fixed
reference-material cell by Stage C0. Variable source cells are allowed, but the
result is explicitly a reference-material density rather than a pooled physical
Cartesian density.

The package requires three-dimensional full periodicity. Lower-dimensional or
partially periodic density estimation is outside this stage.

# Kernel covariance and analysis geometry

## Separate contracts

The Gaussian covariance and analysis geometry metric are independent objects.

`GaussianKernelCovariance` stores the positive-definite fractional covariance

$$
C_s\in\mathbb R^{3\times3}.
$$

`AnalysisGeometryMetric` stores the covariant triclinic metric

$$
G=HH^{\mathsf T}
$$

and its inverse $G^{-1}$.

Changing the topology-analysis metric must not silently change the KDE
bandwidth. Changing the KDE covariance must not silently change the metric used
to raise a score covector.

## Cartesian-to-fractional covariance transformation

Under the row-vector convention

$$
x=sH,
$$

a Cartesian covariance $C_x$ is transformed to fractional coordinates by

$$
C_s=H^{-\mathsf T}C_xH^{-1}.
$$

This rule is implemented by `GaussianKernelCovariance.from_cartesian` and
`isotropic_cartesian`. The source covariance, basis, domain signature, and
transformed covariance remain inspectable.

Under an equivalent fixed lattice-coordinate change

$$
H'=UH,
\qquad
s'=sU^{-1},
$$

the covariance transforms as

$$
C'_s=U^{-\mathsf T}C_sU^{-1}.
$$

The physical kernel is therefore invariant when positions, cell, and
covariance are transformed consistently.

# Normalized periodized Gaussian

## Infinite lattice sum

For $u=s-s_j$, the fractional Gaussian is

$$
\phi_{C_s}(u)
=
\frac{
\exp\!\left(-\tfrac12u^{\mathsf T}C_s^{-1}u\right)
}{
(2\pi)^{3/2}\sqrt{\det C_s}
}.
$$

The periodic kernel is the full lattice sum

$$
K_{C_s}^{\mathrm{per}}(s-s_j)
=
\sum_{n\in\mathbb Z^3}
\phi_{C_s}(s-s_j+n).
$$

It satisfies

$$
K_{C_s}^{\mathrm{per}}(s+m-s_j)
=
K_{C_s}^{\mathrm{per}}(s-s_j),
\qquad m\in\mathbb Z^3,
$$

and

$$
\int_{[0,1)^3}K_{C_s}^{\mathrm{per}}(s-s_j)\,ds=1.
$$

The implementation never replaces this operator with a minimum-image
Gaussian. The direct evaluator is

```python
evaluate_periodized_gaussian_oracle(...)
```

and every grid realization uses the same finite image sum and certificate.

The use of a kernel density estimate follows the classical Rosenblatt--Parzen
construction [E1-1, E1-2]. The explicit triclinic fractional lattice sum,
source binding, and error-certificate construction below are package-specific
derivations.

## Finite image enumeration

The realized sum uses

$$
n_i\in\{-R,\ldots,R\}
$$

with $(2R+1)^3$ image vectors. `GaussianImageTruncation` records:

- $R$ and the image count;
- the requested relative peak-density tolerance;
- a uniform omitted-density bound;
- uniform omitted first-derivative and Hessian bounds; and
- the exact covariance signature.

Let $\lambda_{\max}$ be the largest eigenvalue of $C_s$. For
$\delta_i\in(-1,1)$,

$$
|n_i+\delta_i|
\ge
\max(|n_i|-1,0).
$$

The implementation bounds the anisotropic Gaussian by a separable isotropic
envelope with variance $\lambda_{\max}$, then evaluates zeroth, first, and
second lattice-moment envelopes. The one-dimensional infinite tails are bounded
by the first omitted term plus analytic Gaussian integrals. This yields
conservative uniform bounds for the density, gradient, and Hessian outside the
finite image cube.

The radius is the smallest nonnegative integer satisfying the requested
relative density bound, subject to `max_image_radius`. Failure to reach the
requested tolerance is a resource error, not an implicit approximation.

# Time-weighted density measures

Let the included observation measure be

$$
T=\sum_t W_t,
$$

where $W_t$ are Stage-11E0b frame weights, and let the ion-time measure be

$$
\mathcal I=\sum_j w_j.
$$

The mean occupancy is

$$
\bar N=\frac{\mathcal I}{T}.
$$

The fractional number-density kernel sum is

$$
\widetilde\rho_N(s)
=
\sum_j\frac{w_j}{T}
K_{C_s}^{\mathrm{per}}(s-s_j).
$$

The Cartesian-volume number density is

$$
\rho_N(s)=\frac{\widetilde\rho_N(s)}{V},
$$

with target integral

$$
\int_V\rho_N\,dV=\bar N.
$$

The probability density is

$$
\rho_P(s)=\frac{\rho_N(s)}{\bar N},
$$

with

$$
\int_V\rho_P\,dV=1.
$$

`SpeciesDensityIntegrals` stores $T$, $\mathcal I$, $\bar N$, the weight units,
and the probability target separately. Ion-time and mean occupancy are never
conflated.

## Logical-node quadrature and exact discrete normalization

For grid shape $(N_1,N_2,N_3)$, nodes are

$$
s_{ijk}=\left(\frac{i}{N_1},\frac{j}{N_2},\frac{k}{N_3}\right)
$$

with voxel volume

$$
\Delta V=\frac{V}{N_1N_2N_3}.
$$

After the finite image sum, one common scalar correction enforces

$$
\sum_{ijk}\rho_N(s_{ijk})\Delta V=\bar N
$$

exactly to floating-point roundoff. The same correction is applied to the
first and second density derivatives. Probability density is obtained by the
exact scalar relation $\rho_P=\rho_N/\bar N$.

The normalization residuals are retained in the field-error certificate.

# Differential fields

## Density score covector

The fractional density derivative is a covector. For one image displacement
$u$ and precision $P=C_s^{-1}$,

$$
\partial_s\phi(u)=-(uP)\phi(u).
$$

The score covector is

$$
\alpha(s)=d\log\rho_N(s)
=
\frac{d\rho_N(s)}{\rho_N(s)}.
$$

It is stored as `density_score_covector_values` and is not labeled a vector.
The classical density-gradient use of KDE is related to mean-shift analysis
[E1-3], but Stage 11E1 does not perform mode seeking.

## Metric-raised gradient vector

The geometric gradient vector is obtained only by raising the covector index:

$$
\nabla_G\log\rho_N
=G^{-1}\alpha.
$$

It is stored separately as `metric_gradient_vector_values`. Force comparison in
later PMF work uses the score covector in the same coordinate measure, not the
metric-raised vector by accident.

## Density Hessian

The covariant fractional Hessian of one Gaussian image is

$$
\partial_s^2\phi(u)
=
\left[(Pu)(Pu)^{\mathsf T}-P\right]\phi(u).
$$

Stage 11E1 stores the Hessian of the number density, not the Hessian of
$\log\rho$. Stage 11E2 owns critical-point and ridge interpretation.

# Local support and error certificate

## Effective local sample size

At each node, define the weighted kernel contributions

$$
c_j(s)=\frac{w_j}{T}K_{C_s}^{\mathrm{per}}(s-s_j).
$$

The local effective sample size is

$$
n_{\mathrm{eff}}(s)
=
\frac{\left(\sum_jc_j(s)\right)^2}{\sum_jc_j(s)^2}.
$$

A node is in the declared support only when:

1. its lower density bound exceeds the configured density floor; and
2. $n_{\mathrm{eff}}$ meets the configured minimum.

The lower bound subtracts the image-tail density certificate multiplied by the
configured safety factor.

Density values remain available on the full grid, but score, metric-gradient,
and Hessian claims are authoritative only where `support_mask_values` is true.
Unsupported derivative storage is finite zero; the support mask, not a sentinel
NaN, controls scientific interpretation and strict JSON replay.

## Error fields

`DensityFieldErrorCertificate` records:

- a uniform absolute density image-tail bound;
- a support-restricted score-covector norm bound;
- the corresponding metric-gradient norm bound;
- a uniform density-Hessian bound;
- exact-discrete-normalization residuals;
- supported and total node counts; and
- the image-truncation signature.

For truncated density $\widetilde\rho$, gradient $\widetilde g$, and uniform
bounds $\epsilon_\rho$, $\epsilon_g$, the score bound uses

$$
\left\|
\frac{g}{\rho}
-
\frac{\widetilde g}{\widetilde\rho}
\right\|
\le
\frac{\epsilon_g}{\widetilde\rho-\epsilon_\rho}
+
\frac{\|\widetilde g\|\epsilon_\rho}
{\widetilde\rho(\widetilde\rho-\epsilon_\rho)}
$$

only where $\widetilde\rho>\epsilon_\rho$. The metric-gradient bound multiplies
this result by $\|G^{-1}\|_2$.

# Dense and block-packed realizations

`PeriodicSpeciesDensityRealization` has two storage backends:

```text
dense
block_sparse
```

Both evaluate the same logical nodes with the same lattice-image operator.
The dense backend stores complete arrays. The block backend stores fixed-size
blocks identified by integer block coordinates and reconstructs the same
periodic logical field through its accessors.

At the canonical exact setting

```python
sparse_block_density_threshold = 0.0
```

all nonempty logical blocks are retained, and dense/block values agree exactly.
A positive threshold is an explicit storage approximation; omitted mass is
visible through the discrete normalization residual and is not silently treated
as scientific zero. Stage 11E2 may not use omitted blocks to create or delete
connectivity.

# Complete-system block uncertainty

When `uncertainty_blocks >= 2`, represented frames are divided into contiguous
blocks. Every block contains all selected ions from all frames assigned to that
block; ions are never divided into pseudo-independent per-particle blocks.

For block $b$, the number density is recomputed with that block's complete
observation measure and exact mean occupancy. The standard error field is

$$
\operatorname{SE}[\rho_N(s)]
=
\frac{
\operatorname{SD}\left(ho_N^{(1)}(s),\ldots,
\rho_N^{(B)}(s)\right)
}{\sqrt B}.
$$

This is an adaptation of standard blocking analysis for correlated simulation
data [E1-4]. It is a complete-system uncertainty diagnostic, not a claim that
ions within one frame are independent.

# Bandwidth ladder

`prepare_periodic_species_density_ladder` accepts an ordered sequence of
explicit `GaussianKernelCovariance` records. Every estimate shares:

- one catalog signature;
- one domain signature;
- one options signature; and
- one resource-policy signature.

Each bandwidth retains a unique covariance signature and label. The ladder does
not select an operational scale. Stage 11E2 owns attractor lineage, scale
consensus, and competing scale hypotheses.

# Resource preflight

`SpeciesDensityResourcePolicy` bounds, before allocation:

- logical grid nodes;
- accepted samples;
- grid-node/sample/image terms;
- query/sample batch workspace;
- dense-equivalent output bytes; and
- stored block count.

Resource failure is transactional. The implementation does not lower image
radius, coarsen the grid, omit a bandwidth, or change a backend silently.

# Serialization and provenance

Every persistent contract has a schema tag and deterministic SHA-256 signature.
Array signatures include dtype, shape, and C-order bytes. Estimate signatures
bind:

- catalog and registration identities;
- coordinate measure and cell;
- kernel covariance and analysis metric;
- image truncation;
- integrals;
- field realization;
- error certificate;
- block uncertainty; and
- immutable metadata.

Strict JSON output contains finite values only. Source mismatch and tampering
fail closed.

# Public API

The Stage-11E1 public surface includes:

```python
PeriodicDensityDomain
AnalysisGeometryMetric
GaussianKernelCovariance
GaussianImageTruncation
SpeciesDensityResourcePolicy
SpeciesDensityOptions
SpeciesDensityIntegrals
DensityFieldErrorCertificate
CompleteSystemBlockUncertainty
PeriodicSpeciesDensityRealization
PeriodicSpeciesDensityEstimate
PeriodicSpeciesDensityLadder
prepare_gaussian_image_truncation
prepare_periodic_species_density
prepare_periodic_species_density_ladder
evaluate_periodized_gaussian_oracle
```

These names are exported through `mdstats.analysis.density`,
`mdstats.analysis`, and `mdstats`.

# Acceptance tests

The focused gate must verify:

- exact number- and probability-density normalization;
- periodic invariance of density, gradient, and Hessian;
- explicit bounded image truncation;
- no minimum-image Gaussian path;
- Cartesian-to-fractional covariance transformation;
- invariance under an equivalent right-handed lattice-axis permutation;
- exact dense/block agreement under one operator;
- distinct score-covector and metric-gradient fields;
- support masking and finite strict serialization;
- mean occupancy versus ion-time accounting;
- complete-system block uncertainty;
- bandwidth-ladder identity;
- physical variable-cell rejection;
- resource preflight;
- source-binding and tamper rejection; and
- public API availability.

# Method provenance

## External standard background

The following ideas are standard external background:

- kernel density estimation and Gaussian smoothing [E1-1, E1-2];
- density-gradient interpretation related to mean shift [E1-3]; and
- blocking analysis for correlated simulation averages [E1-4].

## Package-specific constructions

The following are package-specific constructions or derivations:

- the Stage-C0/E0b source and registration binding;
- the explicit physical-versus-reference-material measure contract;
- the separate kernel-covariance and analysis-metric records;
- the triclinic fractional lattice-sum implementation;
- the separable uniform image-tail envelope and derivative certificates;
- exact represented-time number/probability normalization;
- the separate score-covector and metric-raised-vector storage contract;
- support-gated derivative claims;
- dense/block realization signatures; and
- complete-system, rather than per-ion, block uncertainty ownership.

# References

[E1-1] Rosenblatt, M. (1956). *Remarks on Some Nonparametric Estimates of a
Density Function*. Annals of Mathematical Statistics, 27, 832-837. DOI:
[10.1214/aoms/1177728190](https://doi.org/10.1214/aoms/1177728190).

[E1-2] Parzen, E. (1962). *On Estimation of a Probability Density Function and
Mode*. Annals of Mathematical Statistics, 33, 1065-1076. DOI:
[10.1214/aoms/1177704472](https://doi.org/10.1214/aoms/1177704472).

[E1-3] Fukunaga, K., and Hostetler, L. D. (1975). *The Estimation of the
Gradient of a Density Function, with Applications in Pattern Recognition*.
IEEE Transactions on Information Theory, 21, 32-40. DOI:
[10.1109/TIT.1975.1055330](https://doi.org/10.1109/TIT.1975.1055330).

[E1-4] Flyvbjerg, H., and Petersen, H. G. (1989). *Error Estimates on Averages
of Correlated Data*. Journal of Chemical Physics, 91, 461-466. DOI:
[10.1063/1.457480](https://doi.org/10.1063/1.457480).
