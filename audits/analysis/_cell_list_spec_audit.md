# Cell-List Source and Specification Consistency Audit

## Scope

This audit compares the S1 source implementation against:

- `docs/specs/analysis/_cell_list_spec.md/.pdf`;
- `docs/specs/analysis/_neighbors_spec.md/.pdf`;
- `docs/arch_manuals/periodic_neighbor_search_architecture.md/.pdf`.

## Result

**PASS.** No source/specification mismatch was found in the implemented S1
contract.

## Checked contracts

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

Additional checks:

- backend output preserves the original cell-basis image-shift convention;
- lattice reduction is optional and affects candidate generation only;
- stencil hard limits raise rather than truncate;
- candidate rows restore caller candidate-selection order;
- result arrays remain immutable through `NeighborListResult`;
- dense comparison ignores backend provenance by default;
- S1 documentation does not claim Verlet reuse or automatic policy;
- the staged plan marks S0 and S1 complete and S2-S4 incomplete.

## PDF verification

All three affected PDFs are openable, searchable, and non-scanned. Rendered page
contact sheets were inspected at 120 dpi. No clipping, overlapping text, broken
glyphs, or malformed tables were observed.

## API snapshot

- `NeighborSearchBackend`: `[('DENSE', 'dense'), ('CELL_LIST', 'cell_list')]`
- `CellListOptions` fields: `[('use_lattice_reduction', 'True'), ('max_stencil_candidates', '1000000'), ('max_stencil_offsets', '250000'), ('metric_tolerance', '1e-12'), ('coordinate_tolerance', '1e-12'), ('reduction_rtol', '1e-12'), ('reduction_atol', '1e-12')]`
- `CellListPlan` fields: `['search_cell', 'basis_transform', 'inverse_basis_transform', 'pbc', 'bin_counts', 'bin_origins', 'bin_widths', 'stencil_offsets', 'reduction_applied']`
- `CellListDiagnostics` fields: `['reduction_applied', 'bin_counts', 'stencil_size', 'occupied_candidate_bins', 'bin_visits', 'unique_candidate_pairs', 'exact_pair_evaluations', 'accepted_pairs']`
- `build_neighbor_list`: `['collection', 'frame_index', 'center_indices', 'candidate_neighbor_indices', 'cutoff', 'pair_counting', 'backend', 'block_size', 'cell_list_options']`
- `iter_neighbor_lists`: `['collection', 'frame_indices', 'center_indices', 'candidate_neighbor_indices', 'cutoff', 'pair_counting', 'backend', 'block_size', 'cell_list_options']`
