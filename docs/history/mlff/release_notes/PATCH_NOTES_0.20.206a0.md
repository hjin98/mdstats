# mdstats 0.20.206a0

## SIZE-HALVE2

This release implements the pre-migration fixed-eight target-size funnel. The possible cardinalities are exactly 128, 256, 512, 1024, 2048, 4096, 8192, and 16,384. Only sizes independently hard-qualified by MVQUAL1 may purchase TRAIN2, and fewer than four qualifiers blocks the future MV funnel.

The new `SizeHalve2Plan` supports exact 3-, 10-, and 30-epoch endpoint evidence with `q -> min(q,4) -> 2 -> 1` survivor counts, exact checkpoint/optimizer/RNG continuation ancestry, early largest-boundary tie protection, and final fixed-ceiling nonconvergence diagnosis. `build_size_halve2_execution_stage_plan` maps the authority onto the existing PERF-P2R incremental work boundaries.

Campaign `prepare` now stores the record and binds it into restart receipts. Current production TARGET-DATA2C v4/TARGET-DATA2D v2 semantics are unchanged; generated-policy migration remains deferred to MVMIGRATE1 after SIZE-FIDELITY2.
