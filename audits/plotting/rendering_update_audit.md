# mdstats 0.11.1 render tuning

This patch adjusts the visualization defaults in response to visual feedback.

## Changes

1. **3-D metric preservation improved**
   - The default 3-D camera projection is now `orthographic` rather than `perspective`.
   - When `equal_aspect=True`, the scene now uses an explicit manual aspect ratio derived from the rendered x/y/z extents.
   - This reduces apparent skew and better preserves the visual metric implied by the cell matrix.

2. **Thicker default line styling**
   - `GraphStyle.atomic_default()` now uses thicker node outlines and thicker bond/graph edges.
   - `GraphStyle.publication()` was also slightly thickened.
   - `GraphStyle.transition_default()` edge widths were increased slightly for better visibility.

3. **More visible 3-D cell wireframe**
   - `Graph3DRenderOptions.cell_width` default increased from `2.0` to `3.2`.
   - `Graph3DRenderOptions.cell_alpha` default increased from `0.45` to `0.72`.

## Compatibility

- No public API was removed.
- These are default-style and default-rendering adjustments only.
- Existing code can still override all widths, alphas, and camera settings explicitly.

## Validation

Focused visualization regression tests were re-run:

```text
22 passed
```

Files regenerated for inspection:
- `examples/graph_visualization/tuned/na_lta_framework_pca_2d_tuned.png`
- `examples/graph_visualization/tuned/na_lta_framework_canonical_3d_tuned.html`
- `examples/graph_visualization/tuned/na_lta_framework_local_si0_hop4_3d_tuned.html`
- `examples/graph_visualization/tuned/na_lta_framework_expanded_2x2x1_3d_tuned.html`
