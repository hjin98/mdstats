---
title: "Periodic Density-Mesh Simplification Specification"
subtitle: "QEM reduction with periodic seams, topology checks, and scalar-field fidelity"
author: "mdstats"
date: "2026-07-22"
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

# Purpose and status

**Module:** `mdstats.plotting.density_mesh_simplify`  
**Status:** normative and implemented through `mdstats 0.19.78a0`.

This module reduces one periodic density mesh toward a requested canonical face target. It owns simplification mechanics and fidelity checks; it does not own scene-wide allocation or final browser compliance.

# Public contracts

```python
MeshSimplificationOptions
MeshSimplificationComponentReport
ImplicitMeshFidelityReport
PeriodicMeshSimplificationResult
simplify_periodic_density_mesh(...)
```

Options define target behavior, bounded attempt count, component policy, displacement and scalar-residual tolerances, normal agreement, and whether the target is hard or advisory.

# Algorithm

1. Validate input mesh and canonical periodic representation.
2. Classify connected components and periodic winding behavior.
3. Apply tile-local presimplification only to components proven interior.
4. Allocate component targets deterministically.
5. Run bounded QEM attempts.
6. Project accepted vertices back toward the implicit contour when configured.
7. Recanonicalize the periodic quotient.
8. Validate seams, incidence, scalar residual, displacement, normals, and component topology.
9. Return the best valid candidate and a complete report.

# Tile-local presimplification boundary

Tile-local presimplification is an optional transient-memory optimization, not an
accepted final geometry boundary. A component may be simplified locally only when
all of its vertices are interior to one render tile. Even then, the assembled
canonical mesh must be validated globally after cross-tile welding.

`density_sparse_mesh` owns the retry policy when assembled incidence is invalid:

1. discard the locally presimplified extraction;
2. repeat the same tiled contour with `local_presimplification=False`;
3. if the exact tiled surface is still invalid, recontour the same scalar field and
   contour level on a bounded coarser display grid;
4. use the declared node-cloud fallback only when no valid mesh repair is available.

A global simplification candidate that fails periodic seam or incidence checks may
never replace a previously validated input mesh. Advisory simplification restores
the validated input and delegates further reduction to `density_scene_fit`.

# Periodic constraints

The simplifier must preserve:

- paired canonical-cell seams;
- valid periodic edge and face incidence;
- component count except where the explicit component policy permits otherwise;
- winding information for protected components;
- finite, nondegenerate triangle geometry.

Winding or invalid quotient components are handled conservatively.

# Scalar-field fidelity

The scientific contour is the zero set of

$$
f(\mathbf x)=\rho(\mathbf x)-\rho_{\mathrm{HDR}}.
$$

Accepted geometry is checked using periodic trilinear sampling of the original scalar field. Reports include scalar residual, implicit displacement, and normal agreement.

# Hard and advisory targets

With a hard target, failure to reach a topology- and fidelity-valid result raises `GraphComplexityError`.

With an advisory target, the module returns the lowest valid count reached. Scene rendering uses advisory behavior and delegates final compliance to `density_scene_fit`.

# Resource behavior

- Scientific fields are queried sparsely and are not densified.
- Components are simplified independently when possible.
- Raw temporary arrays are released between stages.
- Peak and retained geometry estimates are reported.
- The module is safe to call inside an isolated shell worker.

# Focused validation

Tests must cover:

- option and result serialization;
- interior and periodic components;
- winding-component protection;
- target failure below a topology-safe minimum;
- seam pairing across faces, edges, and corners;
- scalar residual, displacement, normal, and incidence gates;
- deterministic output;
- advisory target misses passed to the scene fitter.

# External method

The reduction kernel follows Garland and Heckbert’s quadric-error metric method. Periodic quotient reconstruction, implicit-field checks, and the conservative winding policy are mdstats-specific adaptations.
