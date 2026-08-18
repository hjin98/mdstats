# LD8/LD9 architecture revision audit

Date: 2026-07-21  
Package baseline: `mdstats 0.19.53a0`  
Scope: architecture documentation only; no implementation code changed

## Updated artifacts

- `docs/arch_manuals/mdstats_dynamical_framework_density_architecture_standard.md`
- `docs/arch_manuals/mdstats_dynamical_framework_density_architecture_standard.pdf`

## Review findings incorporated

1. The production `kernel_tail_tolerance=1.0e-8` workload had not been benchmarked directly.
2. The initial atlas record mixed reusable kernel geometry with source-field-specific support, making the proposed cache key incomplete.
3. Block-local direct execution reorganized but did not remove the dominant source-node/stencil arithmetic.
4. A naive local interaction map could itself scale as `block_nodes * stencil_offsets` and become prohibitively large.
5. Terminal partial blocks and periodic wrapping required an explicit exact construction.
6. Dense values inside active blocks retained a large exact-zero fraction.
7. Caching complete HDR sort/permutation arrays would recover much of the memory saved by packed fields.
8. Storage blocks, convolution tiles, and render tiles should not be forced to share one shape.
9. Deterministic direct execution and optimized FFT execution require distinct reproducibility contracts.
10. Visualization cost required a separate plan because LD8 scientific-field optimization alone would not reduce millions of mesh faces.

## Revised normative decisions

- Retain `kernel_tail_tolerance=1.0e-8`, the normalized `discrete_periodized_v1` stencil, and effective CIC-plus-stencil broadening diagnostics.
- Add `LD8-P0` as a production-cutoff benchmark and executor-spike gate.
- Split the architecture into:
  - reusable canonical finite-stencil support;
  - reusable source-independent block-routing templates;
  - field-specific packed CIC source fields;
  - field-specific exact support atlases;
  - packed scientific scalar fields.
- Use packed `16^3` support bitsets for exact periodic dilation and terminal-block handling.
- Forbid global fine-pair arrays and routing records proportional to `block_nodes * stencil_offsets`.
- Build one global source field per requested scientific output.
- Make target-owned compiled/vectorized direct convolution the canonical oracle.
- Make hybrid sparse-direct and tiled overlap-add FFT execution a core production objective rather than an optional late study.
- Separate `storage_block_shape`, `convolution_tile_shape`, and `render_tile_shape`.
- Pack exact-positive scientific values and occupancy masks target-by-target.
- Replace default full HDR sorting with exact weighted multi-selection and deterministic tie handling.
- Correct peak-memory accounting to retained storage plus the maximum mutually exclusive transient workspace.
- Define canonical direct byte reproducibility separately from optimized numerical reproducibility.

## LD9 follow-on plan

The manual now includes an independent display plan covering:

- contour-crossing tile planning;
- component/tile-level marching cubes;
- deterministic logical-grid edge ownership;
- periodic seam-aware quadric-error simplification;
- physical surface and normal error gates;
- compact `float32` display geometry and 32-bit indices;
- removal of repeated vertex metadata;
- species-grouped trajectory traces;
- explicit face-count, HTML-size, and rendering-time targets for the all-species stress scene.

## Revised stage order

1. `LD8-P0` - exact `1e-8` production evidence and executor spike.
2. `LD8-S0` - split contracts, cache ownership, and exact-support proof.
3. `LD8-S1` - bitset support atlas and transactional planning.
4. `LD8-S2` - canonical target-owned direct executor and packed output.
5. `LD8-S3` - hybrid tiled direct/FFT production executor.
6. `LD8-S4` - downstream support reuse and final performance gate.
7. `LD9-V0` through `LD9-V3` - rendering baseline, tiled extraction, simplification, and browser-payload optimization.

The next authorized implementation stage is `LD8-P0`. `LD9-V0` may profile saved scientific fields in parallel, but no simplification path becomes the default before its fidelity gates pass.

## Citation additions

- Oppenheim, Schafer, and Buck for overlap-add linear convolution organization.
- Garland and Heckbert for quadric-error mesh simplification.
- Schroeder, Zarge, and Lorensen for triangle-mesh decimation.

The periodic triclinic routing, bitset support atlas, hybrid executor selection, seam coupling, and density-level fidelity checks remain project-specific integrations.

## Validation performed

- Markdown generation completed successfully.
- Pandoc/XeLaTeX conversion completed successfully.
- PDF preflight reports 54 letter-sized pages with no encryption or structural warnings.
- All 54 PDF pages rendered successfully.
- The LD8 contracts, acceptance tables, LD9 sections, recommended-next-stage section, and references were visually inspected.
- No clipping, overlap, missing glyphs, broken equations, or malformed tables were observed.
- A render comparison against the initial 48-page plan confirmed the intended documentation expansion.
