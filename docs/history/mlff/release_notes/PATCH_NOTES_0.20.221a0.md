# mdstats 0.20.221a0 - TARGET-DATA2B-FEAS1-PERF1

This patch addresses the observed long TARGET-DATA2B-FEAS1 wall time with low average CPU utilization.

- FEAS1 now reduces each exact cKDTree neighborhood block with compiled NumPy operations instead of a Python loop over witnesses.
- Candidate-frame deduplication is canonical and preserves the historical row-major/candidate-major FP64 accumulation order.
- Support-degree masses are accumulated once per family in original witness order, preserving block-size-invariant scientific output.
- Independent coverage families execute concurrently within `StageResourceScope`; automatic scheduling divides the CPU budget between family workers and native cKDTree workers.
- New execution-only override: `[performance].target_coverage_feasibility_family_workers`.
- MVIDX1 uses the same vectorized exact row-compression kernel to avoid immediately repeating the per-witness bottleneck.
- GPU utilization remains intentionally low/zero in FEAS1/MVIDX1 because exact SciPy cKDTree CPU neighborhoods remain the scientific authority; no unqualified CUDA distance backend was introduced.
- Focused FEAS1/MVIDX1/MVSEL1/REPAIR1/MVPERF1 regression tests pass with exact worker/block/family-parallel invariance.

On the 8-thread development host, a four-family 8,192-candidate synthetic exact-equivalence benchmark improved from about 1.63 s to about 0.99 s (1.65x) with identical family reports. Real gains depend on family count, neighborhood density, and the host CPU budget.
