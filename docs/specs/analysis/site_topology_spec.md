---
title: "Species-Dependent Site-State Topology Specification"
subtitle: "Legacy/Manual Stage 11E-M1: Ring-Side Anchors, Explicit Geometric Site Hypotheses, and Structural Candidate Networks"
author: "mdstats"
date: "2026-07-24 (documentation reclassification only)"
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

# Species-dependent site-state topology specification

Version: 0.19.90a0  
Stage: 11E-M1 (historically labeled 11E1)

## Scope

Legacy/manual Stage 11E-M1 converts certified natural-tiling geometry, persistent ring geometry,
and framework semantics into a **species-specific geometric hypothesis graph**.
It does not infer free-energy minima, barriers, rates, or trajectory assignments.
Every physical-state hypothesis must be supplied explicitly through a
`SpeciesSiteTopologyProfile`.

This specification describes the implemented explicit/manual branch. It is not
the new data-driven Stage 11E1 periodic species-density estimator defined by the
Stage 11 architecture manual. Public module names and release behavior are
unchanged by this documentation reclassification.

This supplied-model stage is split into:

- `ring_site.py`: persistent ring-side anchors and geometric site microstates;
- `site_kinetic_network.py`: structurally admissible directed candidate paths.

## Source contract

The builder requires one mutually consistent:

- `TilingGeometryCatalog`;
- `ReferenceRingGeometryCatalog`;
- `FrameworkSemanticCatalog`;
- `SpeciesSiteTopologyProfile`.

The three catalogs must carry the same tiling-geometry digest. A profile is
species-specific and matches semantic interface labels and optional semantic
tile labels. Unmatched ring interfaces are rejected. Absence of a bound state
must be represented explicitly by `NO_BOUND_STATE`; uncertainty must be
represented explicitly by `UNRESOLVED`.

## Persistent ring-side anchors

Every natural-tiling window owns two topological anchors, one for each oriented
ring--tile incidence. The anchors remain distinct even when a physical
plane-centered state merges them. A resolved anchor retains:

- persistent window and side identity;
- adjacent tile identity and semantic label;
- ring-interface family;
- geometric O-area center;
- inward normal and right-handed in-plane axes;
- image shift relative to the canonical side-a representative.

Side-a has image shift `(0,0,0)`. Side-b has the window's
`relative_tile_translation`.

## Landscape taxonomy

`SiteLandscapeRegime` contains:

- `NO_BOUND_STATE`;
- `ONE_SIDED`;
- `BILATERAL_DOUBLE_WELL`;
- `PLANE_CENTERED`;
- `PLANE_OFF_CENTER_DISCRETE`;
- `PLANE_ANNULAR`;
- `GENERAL_MULTIWELL`;
- `UNRESOLVED`.

The regime is a declared geometric hypothesis, not an energetic certification.

### One-sided

One state is placed a positive distance along the inward normal of the side
whose adjacent tile has `active_tile_label`.

### Bilateral

Two states are placed independently along the two inward normals. They remain
separate physical nodes and retain their own tile exposure and image shift.

### Plane-centered

One state is placed at the O-area center and references both side anchors. No
false side-to-side edge is created.

### Off-center discrete

`angular_count >= 2` states are placed at radius `radial_offset` in the ring
plane using the canonical side-a in-plane axes and `angular_phase`. They form a
cyclic set; each state retains both tile exposures.

### Annular

One continuous-state placeholder is centered at the ring center and stores its
annular radius. It is not discretized into artificial angular sites.

### General multiwell

The profile supplies explicit `GeneralSiteTemplate` records in local
`(z, rho, theta)` coordinates and a side affinity (`a`, `b`, or `plane`). No
additional minima are inferred.

## Optional cage-interior hypotheses

A `CageInteriorRule` may create one geometric candidate at the exact natural-
tile volume centroid for every matching semantic tile. Declaring this candidate
does not certify that the centroid is a metastable basin.

## State placement and tile exposure

Each state stores a stable key, a Cartesian reference position, local
coordinates, anchor references, and one or two `SiteTileExposure` records. An
exposure records the adjacent tile index and the periodic image shift of that
tile relative to the state's canonical representative.

## Structural candidate network

`build_site_kinetic_network()` creates a periodic directed multigraph. Edges are
structural candidates only and have no rate or barrier.

Generated edge classes are:

- `INTRA_RING_CROSSING`: the two states of a bilateral model;
- `INTRA_RING_ANGULAR`: neighboring states of a discrete angular cycle;
- `RING_TO_CAGE`: a ring-associated state and an explicitly declared cage state
  exposed to the same tile image;
- `INTRA_TILE_TRANSFER`: only when enabled by an explicit `TileTransferRule`.

Sharing a tile never creates an edge unless a cage rule or tile-transfer rule
explicitly requests it. Directed reverse edges are stored separately. The edge
translation equals target exposure shift minus source exposure shift.

## Immutability and replay

All records are frozen. Mutable arrays are not exposed. Catalog and network
payloads use canonical JSON and SHA-256 digests. `from_dict()` rebuilds from the
supplied source catalogs and profile and rejects tampering.

## Resource limits

Preflight limits bound anchors, states, edges, rules, and angular variants before
bulk object construction.

## Required validation

Focused tests must cover:

- two anchors per ring and opposite side geometry;
- explicit unmatched-interface rejection;
- no-bound and unresolved regimes;
- one-sided side selection by semantic tile label;
- bilateral image-labelled crossing edges;
- merging both anchors into one centered state;
- discrete angular cyclic states and edges;
- annular non-discretization;
- optional cage states and ring-to-cage paths;
- explicit-only intra-tile transfers;
- LTA profile counts derived from 24/12/16/6 semantic families;
- generic profile operation without LTA names;
- resource preflight, deterministic ordering, serialization replay, tamper
  rejection, and public exports.
