# Framework-density browser rendering audit

## Scope

This audit diagnoses why valid Plot-D4 framework-density fields were present in
the Plotly document but were not visible in the browser, and records the
0.19.34a0 rendering correction.

## Scientific-field checks

The uploaded 300 K Na-LTA trajectory was sampled every five archived frames,
producing 300 frames. The prepared fields remained scientifically valid:

- projected framework vertices: 48;
- projected framework edges: 96;
- vertex-density integral: 48;
- edge-length-density integral: 308.332217561 angstrom.

At the 88 percent highest-density threshold, the vertex field contains 1,239
selected voxels and the edge field contains 3,150 selected voxels. The missing
visual was therefore not caused by an empty, misregistered, or unnormalized
field.

## Root cause

The 0.19.33a0 renderer encoded each shell as a Plotly `Isosurface` trace over an
almost zero-width scalar interval. The scientific threshold was valid, but
browser-side scalar triangulation could silently produce no surface. Legend
entries still appeared because the traces themselves existed.

## Correction

Two explicit rendering paths are now implemented.

### Browser-safe framework default

`FrameworkDensity3DRenderOptions` defaults to `render_mode="voxel_cloud"`.
The outer highest-density region is converted to deterministic voxel-center
points before serialization. Marker size and shade increase with relative
density. This reuses Plotly `Scatter3d`, the same browser path already proven by
framework nodes and Na trajectories.

For the Na-LTA example:

- vertex-density cloud: 1,239 points;
- edge-density cloud: 3,150 points;
- marker opacity: 0.28;
- marker-size range: approximately 1.92 to 3.92.

### Explicit mesh option

`render_mode="mesh"` extracts periodic probability-mass shells before HTML
serialization using scikit-image's Lewiner marching-cubes implementation. The
browser receives explicit Plotly `Mesh3d` triangles and performs no isosurface
triangulation.

For the Na-LTA example, the four mesh traces contain:

- vertex 88 percent shell: 3,045 vertices, 5,898 faces;
- vertex 55 percent shell: 1,278 vertices, 2,364 faces;
- edge 88 percent shell: 6,519 vertices, 12,786 faces;
- edge 55 percent shell: 3,967 vertices, 7,906 faces.

The renderer also handles highest-density thresholds that round to the float32
field maximum by moving the extraction level to the nearest representable
interior value.

## Attribution

Surface extraction follows:

- W. E. Lorensen and H. E. Cline, "Marching Cubes: A High Resolution 3D
  Surface Construction Algorithm," *Computer Graphics* 21, 163-169 (1987),
  DOI: 10.1145/37401.37422.
- T. Lewiner, H. Lopes, A. W. Vieira, and G. Tavares, "Efficient
  Implementation of Marching Cubes' Cases with Topological Guarantees,"
  *Journal of Graphics Tools* 8, 1-15 (2003),
  DOI: 10.1080/10867651.2003.10487582.

## Validation

- 69 focused graph, periodic-display, framework-topology, framework-dynamics,
  atomic-density, and framework-density tests passed.
- New tests require nonempty explicit mesh vertices/faces, absence of Plotly
  `Isosurface` traces, and a nonempty `Scatter3d` voxel-cloud fallback.
- Both framework density channels retain independent legend groups.
- HTML serialization contains visible nonzero-opacity density traces.
- The execution sandbox's headless Chromium exposes no WebGL context, so a
  rasterized browser screenshot could not be used as a trustworthy visual
  oracle. The serialized geometry and trace contracts were validated directly.
