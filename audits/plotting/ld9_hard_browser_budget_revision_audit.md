# LD9 hard browser-budget revision audit

Date: 2026-07-21

## Scope

Documentation-only revision of the mdstats dynamical framework and density plotting architecture standard. No Python source, API implementation, numerical behavior, or tests were changed.

## Problem closed

The previous LD9 draft specified mesh simplification and an approximate stress-scene target, but it did not make the final browser face count an unconditional post-replication export contract. It also did not clearly separate raw tile geometry, transient simplification workspace, and final serialized payload.

## Normative changes

- Added explicit `interactive_browser` and `raw_reference` render profiles.
- Added a mandatory `BrowserMeshBudget` for interactive export.
- Set the initial all-species stress-scene limits to 300,000 serialized density faces, 200,000 serialized density vertices, 64 Plotly traces, and 40 MiB self-contained HTML.
- Required all final counts after periodic display replication and complete scene assembly.
- Split raw per-tile, peak transient, and final retained browser limits.
- Replaced all-at-once raw mesh retention with bounded tiled extraction and streaming local presimplification.
- Added deterministic logical-grid-edge merging followed by global periodic seam-aware simplification.
- Required geometric validation directly against the scientific scalar field, with raw full meshes retained only as optional test oracles.
- Added scene-wide shell/component budget allocation under one hard face cap.
- Added structured `BrowserMeshBudgetFailure` semantics: no oversized HTML is written and no scientific parameter or requested channel is silently changed.
- Made compact display dtypes, removal of repeated mesh metadata, and species-grouped trajectories normative.
- Added automated Chromium/WebGL load, orbit, toggle, memory, trace-limit, and context-loss validation.
- Added LD9-V4 as the production-default authorization gate.
- Removed manual numeric prefixes from the LD7-LD9 headings so the generated PDF uses one consistent automatic numbering system.

## Readiness result

LD8 remains ready to begin at LD8-P0. LD9 is now complete enough to begin at LD9-V0 using saved scientific fields. Production interactive rendering is not authorized until LD9-V0 through LD9-V4 pass.

## PDF validation

- PDF generated through Pandoc/XeLaTeX.
- 59 pages; readable and unencrypted.
- Fonts are embedded.
- All pages rendered successfully for visual inspection.
- The revised LD9 section and its tables/code blocks were inspected on rendered pages 42-48; no clipping or overlap was found.
