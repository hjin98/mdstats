# mdstats 0.20.120a0 patch notes

## PAR-DENS0 - basin-aware spread qualification

This release implements the first long-trajectory density gate. Adaptive positional spread is now defined as a pooled **within-basin** second moment rather than a single-global-mean mixture variance. Transition/passages, unknown/unresolved membership, conflicts, and retained excursions are excluded from the vibrational-width estimator.

Production density resolution uses a conservative hierarchy: authoritative Stage-11E6 or geometry-based site labels may be translated into spread labels; otherwise `basin_mode=auto` runs a density-independent provisional residence prepass so density resolution does not depend circularly on the high-resolution density it is planning.

The default convergence protocol separates two jobs that were previously conflated. Four independent 128-stratum random replicates estimate sampling uncertainty, while deterministic represented-time midpoint anchors at 256 and 512 effective samples establish the production point estimate and convergence. Coverage escalates in bounded groups, up to eight replicate-equivalent levels by default, when the anchor has not converged to 1%.

Compact periodic basins now use an O(N)-per-iteration circular/Karcher fast path and only fall back to the historical quadratic weighted-medoid multi-start path when compactness cannot be certified. This makes full-trajectory validation practical for localized ions.

On the supplied 10,001-frame 300 K Na-LTA trajectory, the full reference is 0.0746688146 A and the 512-effective-frame production anchor is 0.0746859880 A (+0.023%). The identified two-basin Na ion is 0.195859 A under the old global-mixture definition, 0.079601 A under the full within-basin definition, and 0.078787 A under the production estimator; 156 passage-boundary samples are excluded. The random-replicate 95% relative confidence half-width is 3.95% and is reported separately from the 0.52% 256-to-512 deterministic convergence change.

PAR-DENS1 (execution-faithful direct/FFT calibration) is next. No density parallel scheduler or GPU backend is enabled by this release.
