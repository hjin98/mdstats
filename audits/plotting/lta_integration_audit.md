# Relaxed Na-LTA graph-visualization integration audit

Validation date: 2026-07-13

## Input

- Source fixture: `tests/data/Na_LTA_relaxed.POSCAR`
- Total population: 168 atoms
- Species: Si24 Al24 O96 Na24
- Boundary conditions: fully periodic triclinic cell

## Authoritative framework connectivity

Persistent framework scope: atom indices 0-143 (Si, Al, and O).

Strict pair rules:

\[
r_{\mathrm{Si-O}} < 2.0\ \text{\AA},\qquad
r_{\mathrm{Al-O}} < 2.0\ \text{\AA}.
\]

Result:

- 144 active atoms;
- 192 T-O edges;
- all 48 Si/Al atoms have degree 4;
- all 96 framework oxygen atoms have degree 2;
- one canonical connectivity state.

These counts are internally consistent because

\[
48\times 4 = 96\times 2 = 192.
\]

## Visualization integration

The state was adapted into `DecoratedGraphView`, projected in PCA and Cartesian
planes, and rendered through `plot_atomic_connectivity_2d()`.

The integration checks:

- species metadata and default palette;
- stable atom and edge keys;
- canonical-to-frame display-shift reconstruction;
- deterministic local periodic unwrapping;
- residual winding preservation;
- display-only periodic ghost endpoints;
- focus neighborhoods;
- physical and schematic layouts;
- PNG and SVG output.

Pale endpoints in physical views are periodic ghost images. They are not extra
atoms and are excluded from graph identity and node counts.

## Broader Na-O diagnostic

A separate gallery graph includes all 168 atoms and the additional illustrative
rule

\[
r_{\mathrm{Na-O}} < 3.15\ \text{\AA}.
\]

This display graph has 302 edges. The Na-O threshold is included only to exercise
mixed-species styling and dense graph rendering; it is not asserted as a universal
chemical-bond definition.

## Human inspection guidance

Use the orthographic contact sheet first. A connection that looks anomalous in one
projection but not the other two is likely a projection overlap rather than a graph
error. Use the local Si-centered views to inspect individual T-O neighborhoods.
Use the full framework-plus-Na view only as a dense global diagnostic.
