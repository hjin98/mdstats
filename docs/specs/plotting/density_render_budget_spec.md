---
title: "Browser Mesh-Budget Specification"
subtitle: "Exact post-replication accounting and pre-write hard export validation"
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

**Module:** `mdstats.plotting.density_render_budget`  
**Status:** normative and implemented.

This module owns exact browser-bound accounting. It does not adapt geometry. It evaluates an already prepared set of density traces after every display replica is counted and raises before HTML writing when a hard budget is exceeded.

# Normative ownership

The module owns:

- `BrowserMeshBudget`;
- `BrowserMeshTraceUsage`;
- `BrowserMeshUsage`;
- `BrowserMeshBudgetReport`;
- `BrowserMeshBudgetFailure`;
- exact post-replication face, vertex, trace, retained-array, and HTML-byte accounting.

It does not own shell target allocation, simplification, recontouring, scheduling, or browser timing.

# Public contracts

```python
BrowserMeshBudget(
    max_final_density_faces: int,
    max_final_density_vertices: int,
    max_final_html_bytes: int,
    max_plotly_traces: int,
    apply_after_display_replication: bool = True,
    hard_limit: bool = True,
)
```

```python
BrowserMeshTraceUsage(
    trace_key: str,
    face_count: int,
    vertex_count: int,
    display_replication: int = 1,
    retained_array_bytes: int = 0,
)
```

```python
BrowserMeshUsage(
    density_traces: tuple[BrowserMeshTraceUsage, ...],
    non_density_trace_count: int = 0,
    final_html_bytes: int | None = None,
)
```

# Exact accounting

For trace $i$ with canonical faces $F_i$, vertices $V_i$, and display multiplicity $m_i$:

$$
F_{\mathrm{scene}}=\sum_i m_iF_i,
\qquad
V_{\mathrm{scene}}=\sum_i m_iV_i.
$$

The trace count includes density and non-density traces:

$$
T_{\mathrm{scene}}=N_{\mathrm{density}}+N_{\mathrm{other}}.
$$

Deferred trajectory, sample, graph, and point-cloud traces must be included before the final requirement is evaluated.

# Evaluation and failure

```python
evaluate_browser_mesh_budget(budget, usage)
require_browser_mesh_budget(budget, usage)
```

Evaluation returns an immutable report. Requirement raises `BrowserMeshBudgetFailure` only after scene fitting has had the opportunity to adapt geometry. The exception contains the full report and a JSON-compatible diagnostic payload.

The final requirement must run before self-contained HTML is written. `write_html()` must additionally compare the observed byte count with `max_final_html_bytes` and avoid leaving a partial artifact after failure.

# Partitioned topology trace accounting

Partitioned framework scenes must not multiply the general graph renderer's style
buckets by the number of topology classes. `framework_dynamics` uses a compact
category adapter with at most four traces per class:

1. framework edges;
2. framework nodes with per-point colors;
3. atomic mean-connectivity edges;
4. atomic mean positions with per-point colors.

All four traces share one topology legend group. The exact resulting count is passed
as `non_density_trace_count`; the budget is not raised merely because a trajectory
contains several topology classes.

# Browser profiles

Named quality profiles are not owned by this module. `BrowserMeshProfile` in `density_scene_fit` supplies package presets by constructing a `BrowserMeshBudget`. Direct callers may construct a custom budget here.

# Scientific invariants

Budget accounting is observational. It may not change:

- fields or normalization;
- Gaussian bandwidth;
- scientific grid;
- HDR threshold or mass fraction;
- frames, species, trajectories, or topology categories.

# Serialization

Normative schema identifiers:

```text
mdstats.browser-mesh-budget.v1
mdstats.browser-mesh-trace-usage.v1
mdstats.browser-mesh-usage.v1
mdstats.browser-mesh-budget-report.v1
```

# Focused validation

Tests must cover:

- exact post-replication counts;
- unique trace keys;
- simultaneous face, vertex, trace, and byte violations;
- structured failure serialization;
- inclusion of deferred non-density traces;
- failure before HTML writing;
- the 301,838- and 314,640-face regression reports.
