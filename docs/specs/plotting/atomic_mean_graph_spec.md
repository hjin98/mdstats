---
title: "Atomic Mean Connectivity Overlay Specification"
subtitle: "Plot-D5 averaged atomic net with density overlays"
author: "mdstats"
geometry: margin=0.82in
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
    \usepackage{microtype}
    \usepackage{xcolor}
    \usepackage{enumitem}
    \setlist{nosep}
    \setlength{\emergencystretch}{3em}
---

# Purpose and status

This document is the normative specification for Plot-D5, introduced in
`mdstats` 0.19.35a0 and corrected in 0.19.37a0. Plot-D5 extends the existing framework-dynamics scene with
an **averaged atomic connectivity net** rendered in the same 3-D display cell
as the mean framework, atomic trajectories, atomic density fields, and framework
 density fields.

The goal is diagnostic and structural:

1. show the mean atomic bonded geometry in the same registered coordinates used
   by the density fields;
2. color atomic nodes by chemical species;
3. retain periodic bond connectivity through canonical image shifts; and
4. allow users to toggle species nodes, atomic bonds, and density channels
   independently in the interactive legend.

# Scientific model

## Registered atomic positions

Let $H_t$ be the instantaneous cell of frame $t$ and $H_{\mathrm d}$ the scene
display cell. Atomic vertex positions use the **same registered atomic
coordinates as the density fields**. They are not taken from a connectivity-tree
lift, because a time-varying spanning tree can change an atom's equivalent
periodic image without changing the physical configuration.

For raw fractional atomic coordinate $\mathbf f_i(t)$, define

$$
\tilde{\mathbf f}_i(t)=
\begin{cases}
\mathbf f_i(t), & \text{material coordinates},\\
\mathbf f_i(t)-\mathbf d(t), & \text{framework-registered coordinates},\\
\mathbf f_i(t)H_tH_{\mathrm d}^{-1}, & \text{laboratory coordinates},
\end{cases}
$$

where $\mathbf d(t)$ is the mean-framework translational drift used by the
framework-dynamics scene.

Because the display cell is periodic and may be triclinic, an ordinary
Cartesian average of arbitrarily chosen lattice images is not gauge invariant.
The atomic vertex is therefore the weighted periodic Fréchet mean

$$
\bar{\mathbf x}_i
=
\operatorname*{arg\,min}_{\mathbf x\in\mathbb R^3/\Lambda}
\sum_t w_t\,d_{\mathrm{MIC}}
\!\left(\mathbf x,\tilde{\mathbf f}_i(t)H_{\mathrm d}\right)^2,
\qquad
\sum_t w_t=1,
$$

where $d_{\mathrm{MIC}}$ is the Euclidean minimum-image distance induced by
$H_{\mathrm d}$. The implemented iteration averages the minimum-image
Cartesian displacement vectors and updates the point until convergence. This is
a flat-torus specialization of the Fréchet/Karcher center-of-mass construction
[1,2].

This definition has two required properties:

1. translating any frame coordinate by an integer lattice vector leaves the
   result unchanged; and
2. the atomic vertex is centered on the same periodic sample distribution used
   by the corresponding atomic density field.


## Edge occupancy

For an unordered atomic pair $e=(i,j)$ and normalized frame weights $w_t$,
define the bond occupancy

$$
p_e = \sum_t w_t\,\mathbf 1_{e\in E_t}.
$$

Two preparation modes are supported.

### Persistent mode

Keep bond $e$ iff it is present in every selected frame,

$$
p_e = 1.
$$

### Occupancy mode

Keep bond $e$ iff

$$
p_e \ge p_{\min},
$$

where $p_{\min}\in[0,1]$ is a user-supplied occupancy threshold.

The rendered bond hover text reports the retained occupancy value. The displayed
periodic image shift is recomputed from the corrected mean vertex positions by
the Euclidean minimum-image convention. Thus connectivity gauge changes cannot
create a long or runaway displayed bond.

# Public API

## New preparation options

```python
AtomicMeanGraphOptions(
    mode="occupancy",          # or "persistent"
    occupancy_threshold=0.95,
)
```

## New prepared scene payload

```python
AtomicMeanGraph(
    atom_indices=...,
    atomic_numbers=...,
    display_positions=...,
    edge_endpoints=...,
    edge_image_shifts=...,
    edge_occupancies=...,
    display_cell=...,
    pbc=...,
    mode=...,
)
```

This object is attached to `FrameworkDynamicsScene.atomic_mean_graph`.

## New rendering options

```python
AtomicMeanGraph3DRenderOptions(
    node_size=5.5,
    node_opacity=0.95,
    edge_width=2.2,
    edge_opacity=0.55,
    edge_color="rgb(120, 120, 120)",
    show_legend=True,
)
```

## Extended scene-preparation entry point

```python
prepare_framework_dynamics_scene(
    collection,
    topology,
    *,
    atomic_connectivity=...,            # AtomicConnectivityState or Result
    atomic_mean_graph_options=...,      # AtomicMeanGraphOptions or None
    ...
)
```

If `atomic_mean_graph_options` is provided, then `atomic_connectivity` is
required.

## Extended renderer

```python
plot_framework_dynamics_3d(
    scene,
    *,
    atomic_mean_graph_options=AtomicMeanGraph3DRenderOptions(),
    ...
)
```

# Input constraints

1. The selected scene frames must be covered by the supplied atomic
   connectivity object.
2. The current implementation requires a **consistent active atom scope** and
   **consistent atomic numbers** across the selected frames.
3. The current implementation requires a **consistent PBC mask** across the
   selected frames.
4. The scene display cell must be nonsingular.
5. The connectivity object may be either a single `AtomicConnectivityState`
   (uniform graph) or an `AtomicConnectivityResult` (time-varying graph).

# Rendering policy

## Species nodes

One Plotly trace is emitted per atomic species. Species colors are taken from
ASE's Jmol-style element color table. Each species trace is legend-toggleable.

## Bonds

All retained bonds are emitted in one line trace with `None` separators. Bonds
keep their periodic image shift, so cross-boundary bonds remain visible as bonds
connecting into neighboring images of the display cell.

## Legend behavior

The composite scene layout sets

```python
legend={"groupclick": "togglegroup"}
```

so grouped overlays remain easy to toggle in the browser.

# Edge cases and limitations

1. The current implementation does not yet support changing active scope across
   frames, such as atom insertion or removal.
2. The averaged atomic net is most meaningful for relatively persistent bonded
   structures. Highly reactive trajectories may be better visualized with a more
   restrictive occupancy threshold.
3. For a strongly multimodal mobile-ion distribution, a single Fréchet mean is
   still only one summary point and need not represent every occupied site. Use
   the density cloud and trajectories for transport interpretation.
4. Species toggles and density toggles are independent by design.

# Focused validation

The focused tests for Plot-D5 verify the following.

1. occupancy thresholds remove or retain transient edges as expected;
2. a single uniform `AtomicConnectivityState` is accepted as input;
3. the renderer emits separate species traces plus one bond trace; and
4. Plot-D5 remains compatible with the Plot-D3 and Plot-D4 density tests;
5. connectivity-tree changes cannot move an unchanged atom to another periodic
   image before averaging; and
6. real Na-LTA validation places all 168 atomic vertices within $0.0011$ Å of
   their periodic registered trajectory means.

# References

1. M. Fréchet, "Les éléments aléatoires de nature quelconque dans un espace
   distancié," *Annales de l'Institut Henri Poincaré* **10** (1948), 215-310.
2. H. Karcher, "Riemannian center of mass and mollifier smoothing,"
   *Communications on Pure and Applied Mathematics* **30** (1977), 509-541.
   DOI: `10.1002/cpa.3160300502`.
