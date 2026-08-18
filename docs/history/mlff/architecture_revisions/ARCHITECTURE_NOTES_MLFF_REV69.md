# MLFF Architecture Revision 69

**Gate:** TARGET-DATA2C-MVSEL1  
**Release:** `mdstats 0.20.202a0`  
**Dependency-graph schema:** 51

Revision 69 implements the deterministic two-phase progressive multi-view selector on the exact MVIDX1 sparse substrate. Required hard obligations are serviced first; Phase A improves the current worst required coverage view and total newly covered reference mass; Phase B uses a density-aware harmonic witness-multiplicity objective with diminishing returns. FP64 gain accumulation, least-selected correlation-unit balance, sparse-neighborhood diversity, and stable frame UID tie-breaking are frozen.

The selector is integrated into `prepare` as `target_multi_view_selection`, but it is pre-migration evidence only. Revision-64 TARGET-DATA2C v4 remains the production selector and DATA8 membership authority.

Next gate: TARGET-DATA2C-REPAIR1.
