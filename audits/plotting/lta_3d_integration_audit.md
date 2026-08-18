# Relaxed Na-LTA periodic and interactive-3-D integration audit

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

The degree counts satisfy

\[
48\times4 = 96\times2 = 192.
\]

## G4 periodic display integration

The same scientific graph was materialized in three modes:

1. **Canonical cell** - canonical nodes remain in the reference cell, and translated
   boundary endpoints are explicit ghosts.
2. **Local unwrapped** - a deterministic four-hop neighborhood around Si atom 0 is
   embedded continuously; residual winding remains explicit.
3. **Expanded cell** - a 2 x 2 x 1 set of primary cell images is replicated with
   deterministic source/display mappings and boundary ghosts where required.

Scientific node and edge identities remain unchanged. Replicas and ghosts are
rendering objects only.

## G5 interactive outputs

The gallery in `examples/graph_visualization/3d/` contains:

| View | Display nodes | Display edges | Plotly traces |
|---|---:|---:|---:|
| canonical framework | 159 | 192 | 8 |
| orthographic canonical framework | 159 | 192 | 8 |
| local Si-0 four-hop neighborhood | 30 | 32 | 8 |
| expanded 2 x 2 x 1 framework | 619 | 768 | 7 |
| canonical framework plus illustrative Na-O contacts | 205 | 302 | 10 |

Each HTML view supports rotation, zoom, legend toggling, and source-aware hover text.
The orthographic view helps separate perspective distortion from graph anomalies; the
local view is best for inspecting individual T-O-T environments; the expanded view
makes periodic continuation and cage repetition easier to understand.

## Broader Na-O diagnostic

A separate illustrative graph adds

\[
r_{\mathrm{Na-O}} < 3.15\ \text{\AA}.
\]

It has 168 scientific nodes and 302 scientific edges before periodic display
materialization. This threshold is included only to test mixed-species styling and a
denser heterogeneous graph. It is not asserted as a universal Na-O bond definition.

## Interpretation cautions

- Ghost and replica nodes are not additional atoms.
- A canonical-cell display can show multiple display images of one source atom.
- The expanded graph is a visualization replication, not a supercell scientific
  analysis result.
- Straight 3-D edges are visual abstractions; future framework edges may carry
  contracted linker paths and should retain those paths as metadata.
- CDN-based HTML files require access to the Plotly CDN when opened. Regenerating with
  `include_plotlyjs=True` produces larger fully self-contained files if needed.

## Conclusion

The Na-LTA fixture verifies the complete path

\[
\text{POSCAR}
\rightarrow
\text{atomic connectivity}
\rightarrow
\text{DecoratedGraphView}
\rightarrow
\text{PeriodicGraphView}
\rightarrow
\text{interactive Plotly scene}.
\]

No connectivity anomaly was detected in the framework counts or local environments.
