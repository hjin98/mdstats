# Stage S1 Cell-List Implementation Audit

## Release scope

- Package version: `0.14.0a1`
- Stage: `S1 - Exact triclinic cell-list backend`
- Dense oracle retained: **yes**
- Cell-list backend enabled by explicit request: **yes**
- Automatic backend policy: **no**
- Verlet caching: **no**
- Scientific cutoff, MIC, image-shift, and CSR semantics changed: **no**

## Implemented source changes

- `mdstats/analysis/_neighbors.py`
  - added `NeighborSearchBackend.CELL_LIST`;
  - added immutable `CellListOptions`;
  - added `CellListComplexityError`;
  - extended `build_neighbor_list()` and `iter_neighbor_lists()` with opt-in cell-list dispatch.
- `mdstats/analysis/_cell_list.py`
  - optional Minkowski-reduced search basis;
  - integer unimodular transform validation;
  - perpendicular-height fractional bins;
  - exact metric-box active-set stencil;
  - mixed-PBC and nonperiodic traversal;
  - deterministic candidate deduplication and order restoration;
  - authoritative original-cell MIC evaluation;
  - immutable plan and diagnostic objects.
- `tests/test_cell_list.py`
  - dense-equivalence and edge-case matrix, including the relaxed Na-LTA fixture.
- `benchmarks/cell_list_benchmark.py`
  - deterministic equivalence-first timing and candidate-pruning records.

## Source API facts

- `NeighborSearchBackend`: `[('DENSE', 'dense'), ('CELL_LIST', 'cell_list')]`
- `CellListOptions` fields: `[('use_lattice_reduction', 'True'), ('max_stencil_candidates', '1000000'), ('max_stencil_offsets', '250000'), ('metric_tolerance', '1e-12'), ('coordinate_tolerance', '1e-12'), ('reduction_rtol', '1e-12'), ('reduction_atol', '1e-12')]`
- `CellListPlan` fields: `['search_cell', 'basis_transform', 'inverse_basis_transform', 'pbc', 'bin_counts', 'bin_origins', 'bin_widths', 'stencil_offsets', 'reduction_applied']`
- `CellListDiagnostics` fields: `['reduction_applied', 'bin_counts', 'stencil_size', 'occupied_candidate_bins', 'bin_visits', 'unique_candidate_pairs', 'exact_pair_evaluations', 'accepted_pairs']`
- `build_neighbor_list`: `['collection', 'frame_index', 'center_indices', 'candidate_neighbor_indices', 'cutoff', 'pair_counting', 'backend', 'block_size', 'cell_list_options']`
- `iter_neighbor_lists`: `['collection', 'frame_indices', 'center_indices', 'candidate_neighbor_indices', 'cutoff', 'pair_counting', 'backend', 'block_size', 'cell_list_options']`

## Correctness gate

- Full regression suite: **244 passed**
- Focused cell-list tests: **21 passed**
- Focused neighbor/oracle/cell-list group: **44 passed**
- Existing expected warnings: **24**
- Ruff full-tree lint: **passed**
- Python compileall: **passed**
- Installed-wheel dense/cell-list equivalence smoke test: **passed**

The acceptance matrix includes orthogonal, moderately triclinic, highly skewed,
fully periodic, two-dimensional periodic, one-dimensional periodic, fully
nonperiodic, boundary-crossing, dense-cluster, zero/one-pair, permuted-order,
multiple-cutoff, near-safe-cutoff, and Na-LTA cases.

## Benchmark summary

- Records: **18**
- Candidate fraction range: **0.0537 - 0.3691**
- Median timing speedup range on this machine: **0.04x - 4.15x**
- Small restricted searches can remain faster with dense search; no automatic crossover is claimed.
- Every benchmark record passed dense equivalence before timing.

## Specification and PDF facts

- S1 specification Markdown SHA-256: `37d7e928e2681ae6e730b38f4616dce572042be126f8ee0cf1046b82a4fb8ea7`
- S1 specification PDF SHA-256: `35f2237fd3dff2f738d142e5ea201d3c12db7207639571588d3b1c688b39290c`
- S1 specification PDF pages/searchable characters: `13` / `20730`
- Internal neighbor Markdown SHA-256: `ce3f5de44c39a8965ef0a885f16e712a803b37e8057879fef778b52d87c6ae9b`
- Internal neighbor PDF SHA-256: `876dd1337f567713a0bf93705af6fc9ef80d64499e88abaeb2aa141e56ccd542`
- Internal neighbor PDF pages/searchable characters: `12` / `21795`
- Staged plan Markdown SHA-256: `907868a57d4f9203e303076d0819caadf845a52041050a7c504805009e95f366`
- Staged plan PDF SHA-256: `d1d254cee061e6c2741c68ada11833253242e44409c88ce5b04cf936b611c7af`
- Staged plan PDF pages/searchable characters: `26` / `45361`

## Alignment checks

- PASS: CELL_LIST enum
- PASS: CellListOptions defaults
- PASS: search transform formula
- PASS: perpendicular height
- PASS: metric stencil
- PASS: original basis MIC
- PASS: strict cutoff
- FAIL: no cache
- PASS: S1 complete
- PASS: next S2

## Deliberate deferrals

- No candidate reuse across frames.
- No Verlet skin or request-keyed cache.
- No fixed-cell or deformation-aware cache validity rule.
- No automatic dense/cell-list selection.
- No public consumer-module backend parameters.
- No combined pair-registry search in one call.

These remain stages S2-S4.
