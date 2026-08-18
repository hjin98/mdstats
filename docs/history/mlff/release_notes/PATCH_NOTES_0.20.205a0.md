# mdstats 0.20.205a0 patch notes

This release implements **TARGET-DATA2C-MVQUAL1**, the independent scientific A/B qualification gate for the optimized multi-view target-data selector.

Both legacy and MV subsets are rescored through TARGET-DATA2B at identical cardinality. MVQUAL1 additionally checks DATA2A/MVIDX1 hard obligations and records `D_max`, `D_sum`, common-size `N95`, uncovered mass/count, unique-contribution, and provenance-diversity diagnostics. A legacy hard pass cannot become an MV fail, the MV worst-view deficit cannot worsen, and common-size `N95` cannot increase.

All MV rungs are independently rescored for bounded-capacity diagnosis, including the 16,384 ceiling when materializable. One or two common hard-qualified sizes are frozen for later legacy-vs-MV learning controls; positive TRAIN2/GPU execution remains deferred to the final consolidated GPU qualification.

TARGET-DATA2C v4 remains the production selector. No DATA8 membership, TARGET-DATA2D survivor policy, e3nn/CuEq phase split, or generated default changes in this release.
