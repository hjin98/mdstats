---
title: "Metric Geometry and Certified Periodic Images"
subtitle: "Stage C0A2: immutable fit/analysis metrics and fail-closed triclinic closest-image geometry"
date: "2026-07-24"
version: "0.19.93a0"
status: "implemented"
---

# Scope

This specification owns the metric-bearing geometric contracts used by Stage C0A2.
It does not own statistical kernel covariance, density topology, or site basins.

Three objects remain distinct:

- `RegistrationFitMetric`: geometry used only to fit reference-group translation;
- `AnalysisGeometryMetric`: geometry exposed to downstream periodic analysis;
- statistical kernel metrics, which remain outside this stage.

Neither Stage C0 metric is silently inherited from the other.

# Row-vector metric convention

For a Cartesian row displacement $\delta$,

$$
\|\delta\|_P^2=\delta P\delta^{\mathsf T},
$$

where $P$ is finite, symmetric, and positive definite. Under the fixed row-coordinate
change $q'=qA$, the same geometry is represented by

$$
P'=A^{-1}PA^{-\mathsf T}.
$$

Every metric records units, coordinate-frame meaning, transformation provenance, schema,
and an immutable SHA-256 signature.

# Certified triclinic closest image

For full-periodic cell $G$, solve

$$
 n_* = \arg\min_{n\in\mathbb Z^3}\|\delta-nG\|_P.
$$

Componentwise fractional rounding is only a seed; it is not accepted as a proof for a
skewed cell. Let $P=LL^{\mathsf T}$, $B=GL$, and $f=\delta G^{-1}$. From any seed
with residual radius $r$, every improving integer vector satisfies

$$
\|f-n\|_2 \le \frac{r}{\sigma_{\min}(B)}.
$$

The implementation exhaustively enumerates the resulting finite integer box. This bound is
derived directly from the smallest-singular-value inequality; no external approximate
nearest-plane result is treated as the scientific solver. The result records the selected
integer shift, closest vector, distance, second-best distance, separation, tie status,
examined-candidate count, and certification status.

A search exceeding the declared candidate budget fails before returning an uncertified
answer. Distances within the combined absolute/relative tie tolerance are ambiguous.

# Acceptance requirements

- orthorhombic results agree with ordinary wrapping;
- skew cells may disagree with componentwise rounding, and the exhaustive result wins;
- a metric coordinate change preserves distance when both cell and metric are transformed;
- exact and near ties are reported rather than broken silently;
- serialization round trips preserve signatures;
- fit and analysis metrics remain independently configurable.
