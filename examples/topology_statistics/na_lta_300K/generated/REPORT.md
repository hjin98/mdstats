# Na-LTA TS5 Statistics Figure Report

This example applies the TS5 plotting and export layer to the existing 2,000-frame, 300 K Na-LTA atomic-connectivity and framework-topology catalogs.

## Main results

- Atomic connectivity states: **72**
- Framework topology classes: **1**
- Changed atomic boundaries: **71**
- Changed framework boundaries: **0**
- Cross-layer boundaries: **1928 stable**, **71 atomic-only**, **0 framework-only**, **0 coupled**
- Na-O count: support **110-121**, mean **115.8735**, population SD **2.8563**
- Si-O count: **96 in all 2,000 frames**
- Al-O count: **96 in all 2,000 frames**
- Projected framework edges: **96 in all frames**
- Framework cycle-space rank: **49**

## Figure set

The directory contains 12 PNG/PDF pairs:

1. Na-O contact-count distribution
2. Na-O contact-count time series
3. Si-O contact-count distribution
4. Al-O contact-count distribution
5. Atomic-state occupancy
6. Atomic-state timeline
7. Atomic transition raster
8. Atomic residence-length distribution
9. Framework edge-count series
10. Framework-class timeline
11. Cross-layer boundary counts
12. Atomic-state/framework-class contingency

The `tables/` directory contains the canonical combined JSON payload and 23 deterministic CSV tables.
