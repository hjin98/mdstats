---
title: "LD9-V0 Mesh Fidelity and Topology Validation Specification"
subtitle: "Sampled surface distance, normal error, scalar residual, and indexed-mesh topology"
author: "mdstats development specification"
date: "2026-07-21"
geometry: margin=0.78in
fontsize: 10pt
toc: true
toc-depth: 3
numbersections: true
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
    \usepackage{fvextra}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
    \RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\small}
---

# LD9-V0 - Mesh Fidelity and Topology Metrics

**Package target:** `mdstats 0.19.54a0`  
**Status:** implemented calibration metrics; simplification is not implemented here  
**Module:** `mdstats.plotting.density_mesh_validation`

## Purpose

This module defines deterministic validation metrics for comparing a candidate browser mesh with a raw reference mesh or, when supplied, the underlying scientific scalar field.

The module does not modify either mesh and does not perform mesh simplification.

## Input constraints

Vertices are finite arrays with shape `(n_vertices, 3)`. Faces are integer arrays with shape `(n_faces, 3)`. Every face index must be valid, and a face may not repeat a vertex index. Zero-area triangles are rejected for geometric comparison.

## Topology summary

```python
MeshTopologySummary(
    vertex_count,
    edge_count,
    face_count,
    connected_component_count,
    boundary_edge_count,
    nonmanifold_edge_count,
    euler_characteristic,
)
```

Undirected edge incidence is counted from indexed triangles. The Euler characteristic is

$$
\chi=V-E+F.
$$

A mesh is reported as a closed two-manifold when every used edge has incidence two.

This summary is a validation diagnostic. Periodic seam pairing remains a separate LD9-V1/V2 requirement.

## Surface sampling

Triangles are sampled proportionally to area. For a selected triangle with vertices $(\mathbf a,\mathbf b,\mathbf c)$, two deterministic pseudorandom variates are reflected into the unit simplex and the point is

$$
\mathbf x=\mathbf a+u(\mathbf b-\mathbf a)+v(\mathbf c-\mathbf a).
$$

The seed and maximum sample count are explicit. Identical meshes sampled with the same seed produce identical point sets.

## Symmetric sampled distance

Let $P$ and $Q$ be the sampled reference and candidate point sets. The sampled symmetric distance collection is

$$
D(P,Q)=
\{\min_{q\in Q}\lVert p-q\rVert:p\in P\}
\cup
\{\min_{p\in P}\lVert q-p\rVert:q\in Q\}.
$$

The report stores median, 99th percentile, and maximum values. This is a bounded calibration approximation to symmetric surface distance; later production validation may add adaptive refinement near high-error regions.

## Normal error

Triangle normals accompany every sampled point. Each sample is paired with its nearest opposite-mesh sample. Orientation-independent angular error is

$$
\theta=\cos^{-1}\left(|\mathbf n_1\cdot\mathbf n_2|\right).
$$

The report stores median, 99th percentile, and maximum angles in degrees.

## Scientific scalar residual

When a scalar sampler and contour level $\rho_q$ are supplied, candidate samples are checked using

$$
r(\mathbf x)=|\rho(\mathbf x)-\rho_q|.
$$

The sampler must return one finite value per candidate sample. Scalar residual validation is optional in V0 but becomes required for LD9-V2 acceptance against the scientific field.

## Fidelity policy

```python
MeshFidelityOptions(
    max_samples=50_000,
    random_seed=0,
    max_surface_error=0.02,
    max_normal_error_degrees=8.0,
    max_scalar_residual=None,
    require_component_count=True,
    require_euler_characteristic=True,
    require_closed_two_manifold_match=True,
)
```

The report is passing only when every enabled requirement passes.

## Schemas

```text
mdstats.mesh-topology-summary.v1
mdstats.mesh-fidelity-options.v1
mdstats.mesh-fidelity-report.v1
```

## Focused tests

Tests must include:

- a closed octahedron with $V=6$, $E=12$, $F=8$, and $\chi=2$;
- identical-mesh zero-distance comparison;
- translated-mesh surface-error rejection with preserved topology;
- scalar-residual evaluation against an explicit contour function;
- malformed face and zero-area rejection;
- canonical JSON round trips for topology, options, and fidelity reports.

## Limitations and next stage

The V0 nearest-sample metric is suitable for calibration and regression tests but is not a formal exact Hausdorff computation. LD9-V2 should supplement it with adaptive field-based sampling, periodic seam checks, and protected-component validation.
