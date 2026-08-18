---
title: "Deterministic Density Attractors and Supported Periodic Basins"
subtitle: "Stage 11E2: modes, ridges, unknown-space-safe basin ownership, bandwidth lineage, and provisional cores"
author: "mdstats"
date: "2026-07-25"
version: "0.20.0a0"
status: "implemented baseline; revision-42 candidate terminology clarified"
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

Stage 11E2 converts one immutable Stage-11E1 periodic species-density estimate,
or an ordered covariance ladder of such estimates, into a source-bound catalog of
statistical density attractors and support-restricted periodic basins. The
canonical implementation is:

```python
mdstats.analysis.density.attractors
```

The scientific path is:

```text
PeriodicSpeciesDensityEstimate
    -> complete supported periodic logical-node complex
    -> isolated modes, extended ridges, or unresolved flat components
    -> deterministic support-restricted steepest-ascent ownership
    -> supported transition regions and numerical inter-basin boundary candidates
    -> attractor-local periodic charts
    -> point-specific or manifold-specific provisional cores

PeriodicSpeciesDensityLadder
    -> adjacent-scale attractor correspondence
    -> split/merge lineage
    -> topology-stable scale interval or explicit competing hypotheses
```

This stage does **not** fit conditional mean forces, harmonic stiffness,
temporal dwell persistence, final structural labels, transition events,
barriers, rates, or kinetic networks. Those remain Stage 11E3 and later
responsibilities.

# Scientific ownership and borrowed methods

The following are established external methods or mathematical background:

- density-gradient and mean-shift mode seeking [1];
- nonparametric density-ridge conditions [2];
- discrete Morse theory on cell complexes as a conceptual basis for critical-cell bookkeeping [3];
- hierarchical density clustering as an independent comparison method [4]; and
- k-means as a deliberately limited partitioning baseline [5].

The following are package-specific constructions and are not claimed as direct
implementations of those publications:

- deterministic ordering of periodic logical nodes and plateau components;
- propagation of Stage-11E1 support and unknown-space semantics into topology;
- the canonical support-restricted torus ascent graph;
- the rule that unsupported or omitted sparse blocks cannot create background,
  candidate adjacency, transition-saddle promotion, or free-energy connections;
- source-bound attractor and basin signatures;
- local annular-chart construction from a certified periodic ridge component;
- the provisional-core fallback hierarchy; and
- the exact bandwidth-lineage and scale-consensus record contracts.

# Inputs and source binding

## Required Stage-11E1 estimate

`prepare_density_attractor_catalog` consumes one
`PeriodicSpeciesDensityEstimate`. Its domain, covariance, analysis metric,
logical-grid shape, field-error certificate, support mask, and source catalog
signature are immutable inputs.

The topology catalog records:

```text
density_estimate_signature
domain_signature
covariance_signature
source_catalog_signature
options_signature
```

A shape-compatible field with a different source or registration identity is a
different scientific object.

## Canonical scalar field

Topology is constructed from the Stage-11E1 probability density

$$
\widehat p(\mathbf q),
\qquad
\int_{\mathcal T^3}\widehat p(\mathbf q)\,dV=1,
$$

on the complete logical periodic grid. Number density is not used to change
attractor identity because it differs only by a constant mean-occupancy factor
for one species catalog.

## Derivative fields

Stage 11E2 consumes the separately stored:

- density score covector $d\log\widehat p$;
- metric-raised gradient vector;
- covariant density Hessian; and
- support mask and Stage-11E1 error certificate.

The Hessian and score are transformed into the orthonormal chart of the declared
analysis metric before curvature and ridge tests. The KDE covariance is never
silently reused as a topology metric.

# Supported periodic cell complex

## Complete logical-node complex

For grid shape $(N_1,N_2,N_3)$, logical nodes are

$$
\mathbf q_{ijk}
=
\left(\frac{i}{N_1},\frac{j}{N_2},\frac{k}{N_3}\right),
$$

with explicit periodic wrap adjacency. Neighbor connectivity is one declared
choice among 6, 18, or 26 neighbors. The default ascent complex uses 26-neighbor
comparison, while numerically supported density-boundary edges and topological cycle checks use the
face-adjacent 6-neighbor graph.

Every logical node has exactly one scientific classification:

```text
unsupported_unknown
supported_basin
supported_transition_region
supported_background
numerically_unresolved
```

`unsupported_unknown` is not numerical zero and is not background.

## Support and background

Let $S$ be the Stage-11E1 derivative-support mask. Only nodes in $S$ may
participate in attractor, basin, ridge, or numerical boundary-candidate claims.

A supported node may be declared `supported_background` only when

$$
\widehat p(\mathbf q)
\le
\epsilon_{\mathrm{bg}}\max_{\mathbf r\in S}\widehat p(\mathbf r),
$$

for the explicit option `background_density_fraction`. An unsupported node may
never satisfy this rule by implication.

A block omitted by a block-sparse Stage-11E1 realization remains unknown unless
its support mask explicitly certifies the corresponding nodes.

# Deterministic attractors

## Canonical plateau components

A supported active node is a local-maximum candidate when no declared neighbor
has density larger than its value by more than the plateau tolerance. Equal
candidates are grouped into periodic connected components. Canonical ordering is
by:

1. decreasing component maximum density;
2. attractor-geometry token; and
3. smallest flattened logical-node index.

Tie breaking creates a deterministic identity only inside one already unresolved
plateau. It may not turn a stable extended ridge into a point.

## Isolated modes

At representative node $\mathbf q_i$, transform the density Hessian to the
metric-orthonormal coordinate $\mathbf y$. An isolated point mode requires

$$
\lambda_1< -\kappa_p,
\qquad
\lambda_2< -\kappa_p,
\qquad
\lambda_3< -\kappa_p,
$$

where the eigenvalues are ordered from largest to smallest and $\kappa_p$ is the
explicit minimum point curvature. The first implementation is grid-local: it
retains the representative node, plateau support, eigenvalues, and the numerical
certificate rather than claiming a continuously optimized critical point.

## One-dimensional ridges

For a one-dimensional ridge in three dimensions, let
$V_\perp=[\mathbf v_2,\mathbf v_3]$ span the two normal Hessian eigendirections.
A supported node is a ridge candidate when

$$
\left\|V_\perp^{\mathsf T}\nabla_{\mathbf y}\log\widehat p\right\|
\le \epsilon_{\perp},
$$

$$
\lambda_2< -\kappa_{\perp},
\qquad
\lambda_3< -\kappa_{\perp},
$$

and

$$
\frac{|\lambda_1|}{\max(|\lambda_2|,|\lambda_3|)}
\le r_{\parallel/\perp}.
$$

This criterion adapts the nonparametric ridge definition of Genovese et al. [2]
to the package's declared metric and support contract.

Logical sampling may leave one-node gaps along an otherwise certified ridge.
The implementation may join derivative-certified candidates through at most two
face-adjacent layers of the same supported high-density band. This bounded
joining cannot cross unsupported cells or a density value below the declared
ridge-density floor.

A production extended attractor requires:

- at least `minimum_ridge_nodes` derivative-certified nodes;
- one connected periodic face-adjacent component after bounded joining; and
- a graph cycle in that component.

This preserves an annular state as one extended attractor rather than selecting
an arbitrary maximum sector.

## Flat unresolved components

A local maximum component that fails both the negative-definite point test and
the supported ridge test is retained as
`flat_unresolved_component`. It is not deleted and is not force-fit in later
stages until its intrinsic dimension is resolved.

# Deterministic basin ownership

## Steepest-ascent graph

Every supported active non-seed node selects the neighboring node with greatest
probability density. Exact density ties use the smallest canonical logical-node
index. Repeated ascent terminates at an attractor seed or at an explicit
`numerically_unresolved` cycle/step-limit failure.

This discrete ascent is the canonical Stage-11E2 basin definition. Mean shift is
the theoretical mode-seeking reference [1], but it is not a second authoritative
backend in this release.

## No forced assignment

A node receives no basin owner when it is:

- outside Stage-11E1 support;
- below the explicit supported-background threshold;
- part of an unresolved ascent cycle; or
- excluded by numerical-resource failure.

Nearest-center filling and Voronoi completion are prohibited.

## Transition boundaries

A supported owned node adjacent through a face to another supported basin is
classified as `supported_transition_region` for the declared number of boundary
layers. Its underlying ascent owner remains inspectable, but provisional core
construction excludes transition nodes.

# Numerical density-boundary candidates and adjacency

For two basins $B_i$ and $B_j$, consider only face-adjacent edges whose two
endpoints are supported and owned by different basins. The discrete density-boundary candidate level is

$$
p_{ij}^{\mathrm{boundary}}
=
\max_{(u,v)\in E_{ij}}
\min\{\widehat p(u),\widehat p(v)\}.
$$

The numerical candidate record retains the basin pair, density level, and
canonical logical edge.
No adjacency is created when the connecting neighborhood contains unsupported
space. Disconnected supported components therefore receive no invented relative
free-energy offset.

The retained public class name `SupportedSaddle` is a legacy compatibility name.
Within Stage 11E2 it means only a numerically supported
`density_boundary_candidate`; it is not an observed transition event,
a sampling-supported corridor, a validated transition saddle, or an
activation free-energy estimate. Later SAMP2/E5/E6b stages own those
promotions.

# Attractor-local periodic charts

## Isolated-mode chart

An isolated mode stores a periodic anchor $\boldsymbol\mu_i$ and logical support
nodes. Local displacements use the declared periodic metric and minimum-image
lift around the anchor. The chart validity radius is the maximum retained support
node distance.

## Annular chart

A one-dimensional cyclic ridge stores:

- its periodic support node sequence;
- a circular-mean anchor;
- a best-fit local plane from the periodic lifted support;
- an explicit $[0,2\pi)$ intrinsic parameter; and
- a validity radius.

The intrinsic parameter is a chart coordinate, not a physical sector label. Weak
tangential corrugation does not split the state unless a persistent numerical density-boundary candidate and
bandwidth lineage support the split; later sampling stages must still validate
the transition interpretation.

A general extended component that cannot be given a certified annular chart is
retained as `manifold_chart_unresolved`.

# Provisional cores

## Point core from a numerical inter-basin boundary level

For an isolated mode with maximum $p_i^{\max}$ and highest supported neighboring
boundary candidate $p_i^{\mathrm{boundary}}$, define

$$
\chi_i(\mathbf q)
=
\frac{\log\widehat p(\mathbf q)-\log p_i^{\mathrm{boundary}}}
{\log p_i^{\max}-\log p_i^{\mathrm{boundary}}}.
$$

For $0<\tau_c<1$, the provisional core is

$$
C_i=\{\mathbf q\in B_i:\chi_i(\mathbf q)\ge\tau_c\}.
$$

## Annular normal-depth core

For an annular attractor, each basin node is matched to the closest certified
ridge node under the analysis metric. Its local ridge density
$p_i^{\mathrm{ridge}}$ replaces one global maximum:

$$
\chi_i^{\perp}(\mathbf q)
=
\frac{\log\widehat p(\mathbf q)-\log p_i^{\mathrm{boundary}}}
{\log p_i^{\mathrm{ridge}}(\pi_i(\mathbf q))
 -\log p_i^{\mathrm{boundary}}}.
$$

The authoritative core stores its selected logical nodes and the range of local
density thresholds. Tangential density modulation therefore does not create
arbitrary core sectors.

## Fallback hierarchy

Each core records exactly one depth source:

```text
interbasin_saddle_depth  # legacy compatibility field name
supported_boundary_depth
probability_content_core
core_unresolved
```

The order is:

1. numerically supported inter-basin boundary candidate;
2. supported basin boundary against explicit background or unknown space;
3. declared highest-density probability content; or
4. unresolved.

A fallback never invents a neighbor or barrier.

# Bandwidth lineage

## Pairwise correspondence

Adjacent covariance scales are matched by a deterministic minimum-cost
assignment using:

- periodic anchor distance;
- basin Jaccard overlap on a common logical sampling; and
- an explicit attractor-geometry mismatch penalty.

Different grid shapes are compared by periodic nearest-node resampling into the
source grid. The correspondence retains matched links, births, deaths, overlap,
and periodic distance.

The same generic correspondence function is used for bootstrap replicas,
complete-system time blocks, and independent compatible trajectories. The
caller must retain the provenance of those replicas; Stage 11E2 does not pretend
that they are independent when they are not.

## Survival and split/merge ambiguity

A `DensityAttractorLineage` records a track survival interval over the ordered
covariance ladder. An unmatched source or target marks the lineage ambiguous.
Attractor grid indices are never persistent identities.

# Scale consensus and selection provenance

`SelectionValidationProtocol` records disjoint or overlapping discovery,
selection, and validation block identities. If independent selection or
validation is required, overlap fails closed.

The first operational decision identifies consecutive scales with identical:

- attractor count;
- attractor-geometry multiset; and
- numerical density-boundary adjacency.

A unique interval spanning at least two covariance scales and having complete
adjacent-scale correspondence may select its middle catalog. Otherwise the
result is `scale_ambiguous` and retains all competing catalog signatures.

Temporal or force evidence is not consumed in Stage 11E2. Later stages may
select among the retained hypotheses only under the recorded selection protocol.

# Field error versus topology stability

A Stage-11E1 `DensityFieldErrorCertificate` and a Stage-11E2
`TopologyStabilityCertificate` are separate records.

A topology certificate compares at least two catalogs and reports:

```text
attractor_count_stable
geometry_multiset_stable
saddle_adjacency_stable  # legacy field: numerical boundary adjacency only
minimum matched-basin overlap
stable | unstable | unresolved
```

A small pointwise field error does not imply topological stability. The
`DensityAttractorRefinementSeries` retains ordered grid shapes, catalog
signatures, and the certificate. A single realization is explicitly
`unassessed`.

# Independent comparison adapters

## Periodic k-means

The k-means adapter uses the declared torus metric for assignment and circular
means for center updates. Deterministic farthest-point seeding is used. This is
only a baseline because $K$ is supplied and every sample is forced into a
cluster.

## Periodic HDBSCAN

The HDBSCAN adapter constructs the complete pairwise torus-distance matrix and
calls the optional scikit-learn HDBSCAN implementation when available. Because
that optional backend does not consume arbitrary represented-time weights, a
nonuniform-weight request returns `unsupported_weights` rather than silently
dropping the weights.

Neither adapter may overwrite the canonical periodic-cell basin catalog.

# Resource and determinism contract

`DensityAttractorResourcePolicy` preflights:

```text
max_grid_nodes
max_neighbor_edges
max_attractors
max_lineage_pairs
max_serialized_nodes
```

Failure is transactional. The module performs no rendering, marching cubes,
Plotly construction, browser admission, or HTML serialization.

All authoritative arrays are immutable. Signatures use deterministic SHA-256
over schema-tagged metadata and array digests. Deserialization recomputes every
record signature and rejects tampering.

# Acceptance tests

The focused Stage-11E2 suite must include:

- one point mode crossing a periodic boundary;
- a numerically supported double well with one density-boundary candidate;
- two wells separated by unsupported space with no invented adjacency;
- an annulus retained as one one-dimensional attractor;
- stable and split/merge bandwidth ladders;
- stable and unstable topology-refinement certificates;
- periodic k-means boundary behavior;
- optional HDBSCAN status and weight rejection;
- provisional core depth-source checks;
- strict serialization replay and tamper rejection;
- transactional resource preflight; and
- public API and no-rendering ownership checks.

# References

[1] Fukunaga, K., and Hostetler, L. D. (1975). *The Estimation of the
Gradient of a Density Function, with Applications in Pattern Recognition*.
IEEE Transactions on Information Theory, 21, 32-40. DOI:
[10.1109/TIT.1975.1055330](https://doi.org/10.1109/TIT.1975.1055330).

[2] Genovese, C. R., Perone-Pacifico, M., Verdinelli, I., and Wasserman,
L. (2014). *Nonparametric Ridge Estimation*. Annals of Statistics, 42,
1511-1545. DOI:
[10.1214/14-AOS1218](https://doi.org/10.1214/14-AOS1218).

[3] Forman, R. (1998). *Morse Theory for Cell Complexes*. Advances in
Mathematics, 134, 90-145. DOI:
[10.1006/aima.1997.1650](https://doi.org/10.1006/aima.1997.1650).

[4] Campello, R. J. G. B., Moulavi, D., and Sander, J. (2013).
*Density-Based Clustering Based on Hierarchical Density Estimates*. In PAKDD
2013, Lecture Notes in Computer Science 7819, 160-172. DOI:
[10.1007/978-3-642-37456-2_14](https://doi.org/10.1007/978-3-642-37456-2_14).

[5] Lloyd, S. P. (1982). *Least Squares Quantization in PCM*. IEEE
Transactions on Information Theory, 28, 129-137. DOI:
[10.1109/TIT.1982.1056489](https://doi.org/10.1109/TIT.1982.1056489).
