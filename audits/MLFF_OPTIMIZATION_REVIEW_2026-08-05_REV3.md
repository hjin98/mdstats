# MLFF Branch Optimization Review — Revision 3

Date: 2026-08-05
Package reviewed: `mdstats-0.20.63a0-complete-source-package-mlff-scaling-audit-v2.zip`

## Executive conclusion

The prior revisions removed the known unbounded frame-count quadratic and cubic paths. This review did not find another active production algorithm that is intrinsically `O(N^2)` in the number of frames under the normal fixed-policy workflow. The remaining high-impact costs are dominated by repeated disk passes, tens of thousands of small files, large-array copies, eager object reconstruction, and repeated model/dataset loading. These can still cause swap, metadata-server saturation, and wall-time behavior that appears nonlinear.

The highest-return next work is:

1. Replace per-frame DATA6 descriptor/prediction sidecars with immutable batch shards and compute frame-level MACE summaries during DATA6.
2. Make DATA7 large arrays independently memory-mappable and store PCA parameters as native arrays rather than nested JSON floats.
3. Remove duplicate copies of the universal structural and transformed feature matrices.
4. Batch checkpoint evaluation, reuse parsed monitor datasets, and cache fixed baseline metrics.
5. Replace NPZ frame caches and process pickles with shared read-only array shards/memory maps.

## Priority A — likely dominant wall-time or peak-memory costs

### A1. DATA6 sidecar write/hash/read amplification

**Location:** `mdstats/training_data/production_model_sweep.py`

`_atomic_npy()` and `_atomic_npz()` write each frame artifact, after which `_sha256_file()` reopens and rereads the complete file. `_array_digest()` separately calls `values.tobytes(order="C")`, allocating a complete bytes copy. Later DATA7 reopens every descriptor sidecar to derive MACE summary features.

For 36,759 frames, a campaign that stores both descriptors and predictions can create up to 73,518 scientific sidecars. The operating system must create, stat, open, close, hash, and later reopen each one.

**Recommended redesign:**

- Write immutable shards of 128–512 frames.
- Store frame UID, offset, shape, dtype, and per-array digest in a shard index.
- Hash each shard while writing it, avoiding an immediate reread.
- Use `memoryview(contiguous).cast("B")` for array-content hashing instead of `tobytes()`.
- Repair only the final incomplete shard on restart.
- Keep compatibility readers for existing per-frame sidecars.

**Expected result:** substantially lower filesystem metadata traffic, fewer full-file rereads, faster restart verification, and fewer inode-heavy artifacts.

### A2. MACE summaries are recomputed from every descriptor sidecar

**Location:** `mdstats/training_data/feature_metric.py`, `_mace_summary()`

DATA7 reads each per-frame descriptor matrix and recomputes global mean/std and species means. The cache avoids repeat reads across fold domains within one process, but it holds a large Python dictionary of arrays and is lost on restart.

**Recommended redesign:**

During DATA6, while each descriptor matrix is already resident:

- compute the compact global/species summary once;
- append it to a columnar summary shard;
- persist frame UID → row index;
- let DATA7 memory-map and gather summary rows directly.

This preserves the complete descriptor artifact while eliminating one small-file open and one set of reductions per frame during DATA7.

### A3. Universal structural block still has large copy amplification

**Locations:**

- `mdstats/training_data/structural_selection.py`, `UniversalFrameDescriptorTable.matrix_for_uids()`
- `mdstats/training_data/feature_metric.py`, `_iter_raw_blocks()` and `_fit_block()`

`self.values[indices]` and `self.missing_mask[indices]` use NumPy advanced indexing and therefore always allocate copies. `_fit_block()` then creates another writable standardized matrix.

At 36,759 frames and about 1,400 float64 features:

- one values matrix is about 392.6 MiB;
- one Boolean missing mask is about 49.1 MiB;
- values + copied values + mask already approach 0.82 GiB before PCA temporaries and other blocks.

**Recommended redesign:**

- Detect identity and contiguous row order and return a view/slice.
- Add a row-index API that can write directly into a preallocated destination via `np.take(..., out=...)`.
- For very large domains, compute statistics and projections from row chunks instead of materializing a gathered raw matrix.
- Bit-pack the missing mask or represent it sparsely if missingness is rare.

### A4. DATA7 metric arrays and PCA parameters are expanded into Python/JSON

**Locations:**

- `mdstats/training_data/feature_metric.py`, `_fit_block()`
- `mdstats/training_data/data7_archive.py`, `_manifest_for_bundle()`

Projection matrices, centers, and scales are converted to nested tuples of Python floats and serialized into the DATA7 manifest. A 128 × 2,800 projection is only about 2.73 MiB as float64, but expands to hundreds of thousands of Python objects plus a large JSON representation.

**Recommended redesign:**

Store each numerical parameter as a checksummed `.npy` member:

- `block-<id>-center.npy`
- `block-<id>-scale.npy`
- `block-<id>-projection.npy`

The manifest should retain only names, shapes, dtypes, member paths, and scientific digests.

### A5. The DATA7 ZIP container prevents memory mapping

**Location:** `mdstats/training_data/data7_archive.py`

Although the ZIP members are uncompressed, `np.load()` receives a `ZipExtFile`, so the fitted matrix is fully loaded into RAM. Training weights are also eagerly decoded into one dataclass per frame.

**Recommended redesign:**

Use an atomically promoted checksummed directory artifact:

```text
<domain>.data7/
  manifest.json
  fitted-frame-features.npy
  training-weights.npy or training-weights.jsonl
  block-*-center.npy
  block-*-scale.npy
  block-*-projection.npy
```

This permits `np.load(..., mmap_mode="r")`, lazy weights, and independent member validation. Preserve the ZIP reader for backward compatibility.

### A6. Checkpoint evaluation repeatedly reloads models and datasets

**Location:** `mdstats/training_data/campaign_execution.py`

For each checkpoint, `evaluate_mace_checkpoint()`:

- parses the target extxyz into a complete `list[Atoms]`;
- constructs a new `MACECalculator`;
- evaluates one structure at a time;
- reparses the replay extxyz;
- loads and evaluates the fixed replay baseline model again;
- loads the candidate model a second time for replay evaluation.

This is likely the largest remaining campaign-runtime hotspot after preparation.

**Recommended redesign:**

- Parse or stream target/replay monitors once per evaluation campaign.
- Cache baseline replay metrics by `(baseline model SHA, replay artifact SHA, policy digest, head)`.
- Load each candidate checkpoint once and evaluate target and replay heads from the same native MACE model where supported.
- Reuse DATA6 native graph batching with adaptive GPU/CPU batch sizing and OOM backoff.
- Keep streaming sufficient statistics; do not retain all ASE objects or predictions.

## Priority B — substantial but secondary improvements

### B1. Frame cache NPZ files cannot be memory-mapped

**Location:** `mdstats/training_data/frame_cache.py`

Each run is stored as one NPZ. Loading reconstructs all arrays and every `FrameData` object eagerly. NPZ also prevents direct read-only sharing across worker processes.

**Recommendation:** per-run array directories or a sharded array store with `.npy` members and manifests. Workers can memory-map the same immutable arrays.

### B2. Isolated workers pickle full frame arrays and result graphs

**Location:** `mdstats/training_data/resources.py`, `isolated_process_map()`

Tasks are pickled to disk and results are pickled back. Several callers include complete `FrameData` arrays. This duplicates data, consumes scratch I/O, and prevents efficient shared memory.

**Recommendation:** pass only cache paths, run IDs, frame ranges, and policy digests. Workers memory-map shared frame arrays and write columnar result shards, returning a small manifest record.

### B3. VASP sources are still parsed in multiple passes

**Location:** `mdstats/training_data/sources.py`, `load_vasp_training_source()`

The source path is read by:

1. `read_vasp_run_controls()`;
2. `_extract_static_metadata()`;
3. `read_vasp_frames()`.

The static metadata pass stops before the first ionic calculation, so it is bounded, but controls and frames still traverse overlapping XML content.

**Recommendation:** a unified streaming VASP reader that emits controls, static metadata, energy channels, SCF evidence, and frame arrays from one parse event stream.

### B4. DATA8 extxyz generation repeats per-frame reconstruction and full-file reads

**Location:** `mdstats/training_data/mace_export.py`, `write_mace_extxyz_artifact()`

`prepare_atoms(uid)` is called during writing and again during round-trip validation. The completed extxyz is then reread for validation and reread again for SHA-256. The sidecar is retained as a large in-memory tuple and pretty-printed JSON.

**Recommendation:**

- compute a compact expected per-frame digest during the write pass;
- validate observed frames against those digests instead of rebuilding `Atoms`;
- calculate the extxyz SHA during the validation read, eliminating the third pass;
- stream the sidecar as JSONL;
- content-address identical seed-independent artifacts and hardlink/reflink them into job directories.

### B5. Identical DATA8 datasets are rebuilt across random seeds

Training data and validation data are seed-independent for a fixed selection/mode recipe. The current per-variant materialization can rewrite identical extxyz files for each seed.

**Recommendation:** identify each artifact by a recipe digest and build it once in a shared immutable store. Use hardlinks, reflinks, or verified copies for each campaign job.

### B6. Robust scaling creates temporary NaN matrices

**Location:** `mdstats/training_data/feature_metric.py`, `_column_location_scale()`

Every chunk runs `np.where(missing, np.nan, X)`, allocating a float64 copy. Exact `nanpercentile` can make additional work arrays.

**Recommendation:**

- mean/std: masked sums, sums of squares, and counts without NaN materialization;
- robust IQR: exact partition-based quantiles grouped by valid count;
- optionally add an explicitly configured approximate quantile policy for extremely large domains.

### B7. Missing-indicator PCA makes multiple full memory-bandwidth passes

**Location:** `feature_metric.py`, `_implicit_missing_indicator_projection()`

The algorithm is asymptotically appropriate but revisits the value and missing arrays several times.

**Recommendation:** process value and missing contributions together in row chunks, reuse converted missing blocks, and use a block `LinearOperator`-style randomized range finder.

### B8. Structural quantiles fully sort each feature column

**Location:** `structural_selection.py`, `_column_percentiles_with_missing()`

Only a small fixed set of quantiles is required, but the code performs a full sort of every column for every atom group in every frame.

**Recommendation:** group columns by valid count and use `np.partition()` for only the required order statistics. Keep a benchmark-controlled sort fallback for very small groups.

### B9. DATA4/DATA6 JSONL restoration is eager

**Locations:** `data4_sharded_store.py`, `data6_sharded_store.py`

JSONL is streamed on disk but decoded into complete tuples of dataclasses. Optional atomic-environment/event catalogs can therefore create millions of Python objects.

**Recommendation:** offset-indexed lazy catalogs or columnar numerical arrays. Materialize only requested records.

### B10. Scientific digest construction still expands large payloads

**Location:** `mdstats/training_data/_common.py` and large catalog `_payload()` methods

The first canonical digest can construct a complete nested Python value tree and a complete JSON string before hashing.

**Recommendation:** streaming canonical hashing and digest composition from child digests plus array-byte digests. Large immutable records should cache their digest; tiny records should not be burdened with extra cache fields.

## Priority C — safe smaller improvements

1. In `selection._frame_group_queue()` and `_environment_fps_frames()`, pass assembled matrices directly to `_fps_order_matrix()` instead of creating UID→array dictionaries and restacking them.
2. In `selection._quantiles()`, calculate q50/q90/q95 in one `np.quantile()` call.
3. Reuse the candidate matrix and row positions between selection-plan and coverage-report construction.
4. Cache the winning structural-worker autotune sample outputs rather than recomputing those sample frames in the real pass.
5. Persist one campaign-level immutable frame-array index and pass it across DATA4–DATA8 rather than rebuilding equivalent maps in multiple stages.
6. Group raw physical pair rules that share the same neighbor species so minimum-image distances are calculated once and row-sliced for each center species.
7. Enforce inner BLAS/OpenMP thread count of one whenever outer frame-level threading is active, preventing nested oversubscription.
8. Add a chunked selected-neighbor implementation if users raise the maximum ladder far above the normal 512-frame bound.

## Scaling boundary after these changes

No additional unbounded all-frame pairwise path was found. The remaining scientifically intentional terms are:

- exact structural geometry: `O(N A^2)`;
- bounded maximin selection: `O(N K d)`;
- selected-ladder neighbor coverage: `O(K^2 d)`;
- randomized projection/PCA: approximately `O(N p k)`;
- explicitly configured fold/member/temperature products.

The practical risk is now less about asymptotic frame scaling and more about **I/O amplification and peak-memory amplification**. Those can cause page-cache eviction, swapping, and metadata-server contention that make a nominally linear algorithm appear to slow down as the campaign proceeds.

## Recommended implementation sequence

### Stage OPT3-A — DATA6 storage and summaries

- sharded descriptor/prediction store;
- one-pass hashing;
- persistent MACE summary table;
- legacy sidecar reader and migration tests.

### Stage OPT3-B — DATA7 memory model

- view-aware row extraction;
- direct-to-destination standardization;
- memory-mappable directory artifact;
- native-array PCA parameters;
- lazy/columnar weights.

### Stage OPT3-C — campaign evaluation

- stream monitor data;
- batch MACE inference;
- one candidate model load per checkpoint;
- persistent baseline metric cache.

### Stage OPT3-D — shared frame storage and workers

- mmap frame cache;
- path/range-only worker tasks;
- columnar worker outputs;
- unified campaign indexes.

### Stage OPT3-E — remaining kernels and export

- partition-based structural quantiles;
- fused robust statistics/PCA passes;
- extxyz validation/hash fusion;
- content-addressed seed-independent artifacts.

