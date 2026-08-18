---
title: "Density Mesh Face-Contract Specification"
subtitle: "Normative ownership of raw extraction limits, visual targets, and standalone final limits"
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

**Module:** `mdstats.plotting.density_mesh_contracts`  
**Status:** normative and implemented in `mdstats 0.19.76a0`; consolidated in `0.19.77a0`.

This module owns the meaning and validation of face-count limits for one density shell. It exists because the historical `max_mesh_faces` option mixed three different responsibilities and caused avoidable failures in scene rendering.

# Normative ownership

The module owns:

- the immutable `DensityMeshFaceContract`;
- the immutable `DensityMeshFaceReport`;
- validation of raw, target, and standalone-final face counts;
- conversion of a final face count into an auditable report;
- the distinction between a visual-target miss and a terminal failure.

It does not own:

- marching-cubes extraction;
- mesh simplification;
- scene-wide target allocation;
- browser-budget fitting;
- Plotly serialization.

Those responsibilities belong respectively to `density_sparse_mesh`, `density_mesh_simplify`, `density_scene_budget`, `density_scene_fit`, and `density_render_budget`/`framework_dynamics`.

# Public contracts

```python
DensityMeshFaceContract(
    raw_extraction_face_limit: int | None,
    visual_target_faces: int | None,
    standalone_final_face_limit: int | None,
    mode: Literal["standalone", "scene_controller"],
    metadata: Mapping[str, JSONScalar],
)
```

```python
DensityMeshFaceReport(
    final_face_count: int,
    contract: DensityMeshFaceContract,
    visual_target_met: bool | None,
    visual_target_overage_faces: int,
    standalone_final_limit_met: bool | None,
)
```

The schema identifiers are:

```text
mdstats.density-mesh-face-contract.v1
mdstats.density-mesh-face-report.v1
```

# Three distinct face quantities

## Raw extraction limit

`raw_extraction_face_limit` is a computational-safety limit. It protects memory and wall time during contour extraction and initial geometry assembly. The runtime-derived resource limit is authoritative; an explicit contract may only reduce it:

$$
F_{\mathrm{raw,resolved}}
=
\min(F_{\mathrm{runtime}},F_{\mathrm{contract}}).
$$

Exceeding this limit is terminal because the requested extraction cannot be completed safely under the declared resources.

## Visual target

`visual_target_faces` is a preferred final count for one canonical shell. It is a fitting target, not a safety limit. Exceeding it produces

```python
report.requires_scene_refit is True
```

and must not raise merely because the target was missed.

## Standalone final limit

`standalone_final_face_limit` is a terminal limit for callers that request one mesh without a scene controller. The historical default remains 250,000 faces for this standalone mode only.

# Modes

## Standalone mode

```python
DensityMeshFaceContract.standalone(
    final_face_limit=250_000,
    raw_extraction_face_limit=None,
    visual_target_faces=None,
)
```

The final shell is rejected when it exceeds `standalone_final_face_limit`.

## Scene-controller mode

```python
DensityMeshFaceContract.scene_controller(
    raw_extraction_face_limit=runtime_limit,
    visual_target_faces=allocated_target,
)
```

This mode requires `standalone_final_face_limit=None`. A target miss is retained for `density_scene_fit`; only raw-work violations remain terminal at the shell level.

# Evaluation semantics

```python
evaluate_density_mesh_face_contract(final_face_count, contract)
require_density_mesh_face_contract(final_face_count, contract)
```

Evaluation is side-effect free. Requirement raises only when a terminal contract is violated. The following implications are normative:

| Condition | Standalone | Scene controller |
|---|---:|---:|
| raw extraction exceeds limit | fail | fail |
| final count exceeds visual target | report | report and refit |
| final count exceeds standalone final limit | fail | not applicable |
| final browser scene exceeds budget | not owned | handled after scene fitting |

# Deterministic regression fixtures

The package retains count-only fixtures for the historical failures:

- 582,375 faces against the historical 250,000 standalone limit;
- 301,838 scene faces against a 300,000 browser limit;
- 314,640 scene faces against a 300,000 browser limit.

The first verifies standalone failure and scene-controller routing. The latter two belong to `density_scene_fit` and must enter closed-loop fitting rather than fail before fitting.

# Input constraints

- Counts are integers and nonnegative or positive as specified by each field.
- `scene_controller` requires a positive `visual_target_faces`.
- `scene_controller` forbids `standalone_final_face_limit`.
- `standalone` requires a positive final limit.
- Metadata must be JSON compatible and immutable after construction.

# Failure semantics

Use `GraphStyleError` for invalid option values, `GraphAdapterError` for inconsistent serialized state, and `GraphComplexityError` for a terminal standalone or raw-work violation.

A visual-target miss is never represented as an exception.

# Focused validation

Tests must cover:

- both constructors;
- runtime raw-limit resolution;
- target-miss reporting without failure;
- standalone terminal failure;
- JSON round trips;
- the 582,375-face regression in both modes;
- integration with dense and sparse mesh paths.
