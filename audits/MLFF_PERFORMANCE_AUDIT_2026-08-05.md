# MLFF performance audit — 2026-08-05

## Scope

This audit follows the production campaign path from normalized source arrays through DATA3–DATA8, including restart state, MACE descriptor/prediction inference, universal and LTA structural features, DATA7 fitting/selection/coverage, persistence, and variant materialization. It focuses on asymptotic growth in frame count, repeated whole-corpus passes, Python object expansion, avoidable I/O/hash passes, peak memory, and parallel execution.

## Root cause of the reported DATA6-finalize stall

`[DATA6 finalize] building universal structural selection features` formerly combined several expensive behaviors:

1. Per-frame local geometry evaluated a full `A x A` triclinic minimum-image tensor, including both `(i,j)` and `(j,i)` and integer image shifts that DATA6 never consumes.
2. Angular/orientational invariants were evaluated atom by atom in Python.
3. Approximately 1,400 frame aggregate columns were expanded into Python name/value tuples. For 36,759 frames this is roughly 52 million scalar objects before serialization.
4. Per-atom descriptors were materialized by default even though production DATA7 selects frames.
5. Aggregation groups/statistics were replanned repeatedly.
6. Transition evidence could be globally sorted after construction.
7. The completed catalog was expanded again into nested JSON during persistence.

The operation was compute-bound and allocation-bound rather than deadlocked.

## Implemented corrections

### DATA6 universal structural kernel

- Columnar `float64`/boolean frame tables replace tens of millions of Python feature tuples.
- Production disables unused per-atom environment materialization.
- Static per-run aggregation plans, element/group memberships, and chemistry arrays are reused.
- Scalar/radial features and repeated-coordination angular kernels run in vectorized NumPy/SciPy batches.
- Exact fixed-cell triclinic MIC setup is cached.
- When all atoms are centers, only the upper triangle `i < j` is evaluated and mirrored exactly.
- The vectors-only MIC path skips integer image-shift reconstruction and its two matrix products.
- Same-atom displacement events use `A` vectors rather than constructing an `A x A` tensor.
- Events are emitted in canonical frame order, avoiding an `O(E log E)` global sort.
- Structural workers are selected by a short runtime autotune because memory-bandwidth-heavy kernels often slow down with excessive threads.
- Progress reports include recent/average throughput, ETA, event count, and peak RSS.

For fixed atom count and feature policy, the stage is now `O(N)` in frame count. Its unavoidable exact local-geometry term remains `O(N A^2)` in atom count.

### DATA6 model sweep

- Append-only recovery records replace a growing full-checkpoint rewrite after every frame; checkpoint bookkeeping is amortized `O(N)` rather than `O(N^2)`.
- Set membership replaces repeated tuple scans.
- Descriptor-only MACE calls explicitly disable all derivative outputs under `torch.no_grad()`.
- Frames requiring both descriptors and predictions now use one derivative-enabled MACE graph pass and reuse `node_feats`; the former two-pass path remains as a compatibility fallback.
- CUDA OOM batch halving and resource-bounded initial batching remain enabled.

### DATA6 persistence and restoration

- Universal arrays are stored as checksummed `.npy` shards and long record sequences as streamed JSONL.
- Large arrays are hashed while written rather than reread immediately.
- Restored sharded records verify the actual scientific digest.
- The campaign database stores compact content-addressed pointers instead of duplicate giant JSON records.

### DATA7 fitting and selection

- Full farthest-point ordering was replaced with bounded incremental maximin selection: `O(N K d)` instead of effective `O(N^3 d)`.
- Coverage distances are updated in bounded vectorized chunks.
- Large PCA uses deterministic randomized projection, approximately `O(N P K)`, instead of full SVD.
- Missing-indicator PCA is evaluated as an implicit block matrix, avoiding an additional `N x P` float64 allocation.
- Feature blocks are consumed one at a time and large caches are released before DATA8.
- MACE descriptor summaries are reused across overlapping final/fold-local domains without sharing fitted transforms.
- Species discovery now reads one atomic-number array per run, `O(R A)`, rather than every atom in every frame, `O(N A)`.
- Group scaling computes all column medians/IQRs in compiled NumPy kernels.
- LTA coverage labels inspect only selected frames through the provider index.
- Lineage-identical DATA7 results are cached across seeds, modes, and restarts.

### LTA and DATA4 paths

- Serial LTA partition construction now uses the same compact columnar kernel as multiprocessing rather than the legacy object-heavy implementation.
- Raw feature species/pair indices and force quantiles are precomputed/vectorized.
- Event interval and partition scans use merged intervals, indexes, and boundary-difference methods rather than repeated full-run scans.

### DATA7/DATA8 artifacts

- DATA7 is persisted as a deterministic ZIP64 container with native NumPy arrays and streamed JSONL rather than one enormous JSON tree.
- Newly written/verified artifacts are retained in memory for immediate DATA8 assembly instead of reparsed.
- Foundation energies are reconstructed once from compact authenticated DATA6 summaries and reused by every variant.
- DATA8 remains variant-specific; scientific DATA7 work does not repeat for seed-only or training-mode variants.

## Measured regression evidence

On a 12-frame, 180-atom triclinic LTA-like synthetic workload, the optimized exact local-structure kernel had a median speedup of approximately 3.66x over the package that produced the reported stall. Aggregate output sums and sums of squares were identical. A real MACE 0.3.16 two-structure smoke showed a median 1.63x speedup when descriptors and predictions shared one forward pass, with serial-equivalent descriptors, energies, forces, and stresses.

See `benchmarks/mlff_data6_finalize_optimization_2026-08-05.json` for raw timings.

## Remaining intentional scaling terms

These are not hidden larger-than-linear growth in frame count:

- Exact universal local geometry is `O(A^2)` per frame because declared radial/density features use all periodic pair distances. A sparse cutoff backend would alter feature semantics unless a truncation tolerance becomes part of the frozen policy.
- Exact/robust column quantiles may have worst-case superlinear internal sorting behavior, but run in compiled NumPy and are performed once per fitted domain, not once per selected frame.
- Selection is `O(N K d)`; `K` is the largest requested ladder and is intentionally bounded (normally 512), not `N`.
- Cross-validation repeats fold-local fitting by design. Fold count is fixed and identical scientific DATA7 products are reused across training variants.
- Integrity verification requires linear byte reads. Repeated verification passes were removed, but one authenticated read per restored artifact remains deliberate.
- Event evidence is `O(E)` in the number of threshold crossings. Extremely permissive thresholds can legitimately create a large evidence population; production no longer creates unused atomic environment objects.
- Model training scales with selected configurations, epochs, and model cost; this is expected workload rather than preparation overhead.

## Audit conclusion

No remaining production path constructs a complete all-frame pairwise distance matrix, repeatedly rewrites a growing whole-campaign checkpoint, computes a full farthest-point ordering when only a bounded ladder is needed, or serializes the 36,759-frame structural matrix as nested Python/JSON scalars. For fixed structure size, feature dimension, fold count, and selection ladder, the preparation pipeline is linear in the number of frames, with bounded-memory matrix kernels and explicit progress at long stages.
