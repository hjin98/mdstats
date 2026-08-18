---
title: "Browser Acceptance Specification"
subtitle: "Functional interaction metrics and physical-WebGL production authorization"
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

**Module:** `mdstats.plotting.density_browser_acceptance`  
**Status:** normative and implemented; production authorization requires evidence from a physical WebGL renderer.

This module evaluates browser-runner evidence after a valid HTML artifact has been generated. It does not alter geometry or budgets.

# Public contracts

```python
classify_webgl_renderer(vendor, renderer)
BrowserAcceptancePolicy
BrowserAcceptanceReport
evaluate_browser_acceptance(validation, policy=None)
```

Renderer classes are:

```text
physical
software
unavailable
```

# Functional policy

The default policy evaluates:

- first complete frame time;
- scripted camera-orbit rate;
- representative trace-toggle latency;
- WebGL context loss;
- JavaScript heap use when available.

A functional pass and production-default authorization are separate. A managed or software renderer may provide useful functional evidence without authorizing the profile as a production default.

# Production authorization

When `require_physical_webgl_for_production=True`, the validation payload must expose a physical renderer and pass every functional threshold. Missing vendor/renderer information yields `unavailable`, not an inferred physical pass.

# Input payload

The evaluator consumes the JSON-compatible output of the browser-validation runner. Malformed `browser` or `metrics` sections raise `GraphAdapterError`.

# Determinism and safety

Acceptance evaluation is pure and does not modify:

- geometry;
- trace order;
- legend groups;
- density fields;
- budgets;
- HTML artifacts.

# Focused validation

Tests must cover:

- renderer classification;
- threshold boundaries;
- context-loss behavior;
- missing heap and renderer data;
- functional pass with production failure;
- full production authorization;
- report serialization.
