# Framework dynamics canonical-display and density-rendering fix audit

Version: `0.19.33a0`

## Defects corrected

1. The registered mean framework was retained in an unwrapped spanning-forest gauge while the generic canonical-cell renderer interpreted it as a canonical source-cell graph.
2. An example-side rewrapping attempt used the edge-label transformation with the wrong sign, producing spurious long periodic edges.
3. Composite trajectory range updates did not recompute the manual equal-aspect ratio, so triclinic cells could be distorted.
4. Multiple density shells were encoded through alpha values inside one colorscale, which was not reliably visible across Plotly/WebGL implementations.
5. One legend item was emitted per selected trajectory atom rather than one toggle for the complete selected trajectory group.

## Corrections

For node translations `q_i`, canonical rewrapping now applies

`n'_e = n_e + q_target - q_source`.

This preserves every physical edge vector. Composite ranges include materialized periodic graph nodes and unit-cell wireframe coordinates, and the manual aspect ratio is recomputed from the final ranges. Density mass shells are emitted as explicit grouped isosurface traces with per-trace opacity. Trajectory traces share one legend group and only one visible legend item.

## Na-LTA acceptance result

For the 300 K Na-LTA example:

- 48/48 mean framework vertices are inside the canonical fractional cell;
- 12/96 framework edges have nonzero canonical image shifts;
- edge lengths span approximately 2.999--3.356 angstrom;
- vertex-density integral is 48;
- projected edge-density integral is 308.332217561 angstrom.

## Tests

The focused graph/framework/density boundary completed with 66 passing tests. Two new tests directly guard canonical mean placement, short periodic edge vectors, grouped trajectory legends, and final equal-aspect consistency.
