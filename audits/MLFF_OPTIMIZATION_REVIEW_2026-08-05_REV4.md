# MLFF Branch Optimization Review — Revision 4

Date: 2026-08-05
Package reviewed: `mdstats-0.20.63a0-complete-source-package-mlff-storage-optimization-rev3.zip`

## Executive conclusion

No additional unbounded all-frame `O(N^2)` or `O(N^3)` production algorithm was found in the normal DATA4–DATA8 path. The earlier checkpoint, selection, scheduling, catalog, and interval-association defects are resolved.

The remaining applicable optimizations are dominated by:

1. redundant full-array validation and digest passes after cryptographic authentication;
2. serialization of complete memory-mapped trajectories into isolated-worker pickle files;
3. duplicate full parsing of `vasprun.xml`;
4. repeated frame-by-frame access to descriptor summaries that are already sharded;
5. per-frame/per-group temporary arrays in universal structural aggregation;
6. eager Python-object restoration for DATA6 JSONL and DATA7 training weights;
7. repeated MACE graph construction during checkpoint evaluation;
8. avoidable copies in hashing and scientific-digest code.

For the production structural matrix of approximately `36,759 × 1,400` float64 values, one full pass touches about **392.6 MiB**. Archive authentication, finite-value validation, and scientific-digest calculation can therefore cause more than **1.15 GiB of memory traffic per restore**, before any fitting work starts.

---

## Priority 1 — High-return, semantics-preserving changes

### 1. Add authenticated fast-restoration constructors

#### Current behavior

Several large artifacts are SHA-256 verified and then immediately scanned again by their public dataclass constructors:

- `training_data/data7_archive.py` → `TransformedFrameFeatureTable`
- `training_data/data6_sharded_store.py` → `UniversalFrameDescriptorTable`
- `training_data/frame_cache.py` → `FrameData`

Representative operations include:

```python
np.any(~np.isfinite(values))
```

and later a complete scientific byte digest over the same matrix.

#### Why it matters

For the universal DATA7 matrix:

- archive SHA-256: one full read;
- finite-value validation: one full scan;
- scientific digest: one full scan.

That is at least three complete passes over a roughly 392.6 MiB matrix.

#### Recommended design

Keep strict public constructors for untrusted data, but add private authenticated restoration methods such as:

```python
TransformedFrameFeatureTable._from_authenticated_arrays(...)
UniversalFrameDescriptorTable._from_authenticated_arrays(...)
FrameData._from_authenticated_arrays(...)
```

The restore layer must prove:

- expected file SHA-256 and byte size;
- expected dtype and shape;
- immutable/read-only array state;
- schema and lineage compatibility;
- stored scientific member digest.

It may then inject the cached content digest and skip redundant finite scans that were already performed before the artifact was committed.

#### Expected benefit

Large reduction in restart and stage-handoff latency, especially when DATA6/DATA7 artifacts are repeatedly reopened in one campaign.

---

### 2. Stop pickling complete `FrameData` objects into isolated workers

#### Current behavior

`training_data/resources.py::isolated_process_map()` writes every task through:

```python
pickle.dump(task, handle, protocol=5)
```

Callers in `raw_features.py`, `lta_profile.py`, and `frame_catalog.py` include complete `FrameData` objects and full run maps in each task.

A NumPy `memmap` does not remain a path reference under ordinary pickle. Its complete array payload is serialized. A direct check showed an approximately 8,000,128-byte mapped NPY array producing an approximately 8,000,163-byte pickle.

#### Why it matters

The normalized positions alone for 36,759 frames × 180 atoms are roughly **151.4 MiB** in float64. Forces are another roughly **151.4 MiB**, before cells, energies, stresses, masks, dictionaries, and result pickle files.

This defeats the mmap-based frame-cache design and generates large scratch-file writes for each stage and worker task.

#### Recommended design

Pass only compact worker descriptors:

```text
frame-cache manifest path
run ID
frame-index range
policy digest
output-shard path
```

Each worker should:

1. restore read-only mmap arrays locally;
2. process the assigned range;
3. write a columnar result shard;
4. return only a small authenticated manifest record.

A fork-inherited mmap pool can be an optional fast path on Linux, but the path-based worker contract is more portable and retains one-shot crash isolation.

#### Expected benefit

Potentially hundreds of MiB less scratch I/O per run and much lower process-start latency.

---

### 3. Parse `vasprun.xml` once

#### Current behavior

`training_data/sources.py::load_vasp_training_source()` calls:

1. `read_vasp_run_controls(path)`;
2. `_extract_static_metadata(path)`;
3. `read_vasp_frames(path)`.

`read_vasp_frames()` uses ASE to parse all ionic frames, while the controls/supplement path separately traverses the XML calculation records. Thus a large `vasprun.xml` is parsed multiple times.

#### Recommended design

Introduce a shared parsed-source object:

```python
ParsedVaspTrainingSource(
    controls,
    static_metadata,
    frame_arrays,
    energy_channels,
    scf_flags,
)
```

Near-term change: allow `read_vasp_frames()` to accept the already parsed control/energy supplement so that at least one full XML calculation pass is removed.

Long-term change: use one streaming XML parser that emits normalized frame arrays and control evidence in the same traversal, with ASE retained as a compatibility fallback.

#### Expected benefit

A major reduction in source-ingestion time and XML memory churn for long AIMD trajectories.

---

### 4. Read MACE descriptor summaries in shard batches, not frame by frame

#### Current behavior

DATA7 calls the MACE summary reader per frame. Although shard arrays are cached, each frame still incurs:

- record and shard lookup;
- species dictionary construction;
- one values-array allocation;
- one missing-mask allocation;
- Python loops across species.

A per-frame summary cache can itself become large across 36,759 frames and overlapping domains.

#### Recommended design

Add a bulk interface:

```python
read_mace_descriptor_summary_rows(records, requested_frame_uids, species_order)
```

It should:

1. group records by shard;
2. open each shard once;
3. gather all requested summary rows vectorially;
4. write directly into preallocated DATA7 block and mask matrices;
5. cache shard member maps rather than one array pair per frame.

#### Expected benefit

Lower Python overhead, fewer allocations, and lower cross-validation cache memory.

---

### 5. Memory-map stored NPY members inside DATA6 NPZ shards

#### Current behavior

Descriptor and prediction shards use uncompressed NPZ containers, but selected members are still loaded through `np.load()`, materializing the complete member array in heap memory.

The DATA7 archive already contains logic for mapping a stored NPY member directly by its ZIP local-header offset.

#### Recommended design

Generalize that helper for DATA6 descriptor and prediction shards. Member arrays such as:

- descriptor summaries;
- descriptor offsets and values;
- energies;
- forces;
- stresses;

can be exposed as read-only `np.memmap` views into the NPZ file.

#### Expected benefit

Lower heap pressure and fewer repeated shard-member copies, especially for descriptor values and forces.

---

## Priority 2 — Structural and numerical kernels

### 6. Remove per-group temporary arrays in universal aggregation

#### Current behavior

`structural_selection.py::_frame_aggregate_from_plan()` repeatedly creates per-group temporaries with:

- fancy indexing / `np.ix_`;
- `np.where` clean arrays;
- centered arrays;
- min/max replacement arrays;
- `np.stack`;
- list append followed by final `np.concatenate`.

This is formally linear in frames but occurs in the hottest structural loop.

#### Recommended design

- Preallocate the final output and missing row using offsets stored in `_FrameAggregationPlan`.
- Use reductions with `where=` and `initial=` instead of materializing NaN/inf replacement arrays.
- Reuse worker-local scratch buffers.
- Calculate sum, count, and sum-of-squares in one traversal.
- Batch groups sharing the same membership topology where practical.

#### Expected benefit

Lower allocation rate, allocator contention, and memory-bandwidth consumption in DATA6 finalization.

---

### 7. Reuse pair geometry across raw-feature rules

#### Current behavior

`raw_features.py` calls `_pair_statistics()` independently for every pair rule. Each call recomputes minimum-image displacement and distance matrices for its center/neighbor species pair.

#### Recommended design

For each frame:

1. group rules by center/neighbor species pair;
2. calculate the exact MIC distance matrix once per unique pair;
3. derive minimum, nearest-neighbor, and multiple coordination-cutoff statistics from that shared matrix.

If several rules share only the neighbor species, a wider union geometry plus masks may also be economical.

#### Expected benefit

Material reduction in DATA4 raw-feature geometry time without changing definitions.

---

### 8. Avoid whole-buffer copies in the DATA6 hashing writer

#### Current behavior

`data6_sharded_store.py::_HashingBinaryWriter.write()` uses:

```python
data = bytes(value)
```

This copies every buffer passed by NumPy before writing and hashing it.

#### Recommended change

Use a memory view, matching the safer implementations elsewhere:

```python
view = memoryview(value)
written = self.handle.write(view)
self.hasher.update(view[:written])
```

#### Expected benefit

Eliminates one complete temporary copy during large NPY shard writes. This is a low-risk immediate change.

---

### 9. Fuse value and missing-indicator randomized-projection passes

The implicit missing-indicator PCA is asymptotically appropriate but revisits large matrices several times. Chunked kernels should calculate value and missing contributions in the same row pass for:

- randomized range construction;
- reduced matrix construction;
- final projection.

This improves cache locality and reduces memory traffic while preserving deterministic algebra.

---

## Priority 3 — Persistence and object materialization

### 10. Store DATA7 training weights columnarly

#### Current behavior

`training-weights.jsonl` is fully parsed into one `FrameTrainingWeight` dataclass per frame. `TrainingWeightCatalog` then sorts records and builds dictionaries and coverage sets.

#### Recommended format

Use native members for:

- frame UID index;
- configuration, energy, force, and stress weights;
- compact reason/flag codes.

Expose lazy compatibility objects only when requested. Retain the JSONL legacy reader.

#### Expected benefit

Lower heap usage and faster loading across multiple DATA7 domains.

---

### 11. Make large DATA6 JSONL catalogs lazy or columnar

`data6_sharded_store._read_jsonl()` eagerly reconstructs all event and optional atomic-environment records. If atomic environments are enabled, this can be extremely large.

Recommended alternatives:

- frame-UID-to-byte-offset index plus lazy decode;
- chunked iterator interfaces;
- native columnar event/environment arrays;
- materialize only requested frames during DATA7 or analysis.

---

### 12. Stream DATA7 domains into DATA8

DATA8 assembly should consume one DATA7 domain at a time and release it when its materialized files and lineage metadata are complete. Even with mmap feature matrices, eager weight catalogs and metadata objects accumulate when every bundle is retained simultaneously.

---

### 13. Stop expanding PCA arrays into Python lists for scientific digests

`FittedFeatureBlockMetric._payload()` converts center, scale, and projection arrays through `.tolist()`. A moderately sized projection then expands into hundreds of thousands of Python floats.

Use a scientific payload containing:

- shape;
- dtype;
- canonical byte digest;
- semantic metadata.

Retain list conversion only for the legacy human-readable serialization path.

---

## Priority 4 — Checkpoint evaluation and deployment

### 14. Cache MACE graph construction across checkpoints

The monitor `Atoms` objects and candidate provider are now reused efficiently, but every checkpoint evaluation still rebuilds MACE `AtomicData` graphs for every configuration.

For checkpoints sharing architecture, element table, cutoff, cell, PBC, and head semantics, graph topology and geometric input tensors can be cached by authenticated monitor identity and model graph signature. Only model parameters need to change.

This can materially improve campaigns that evaluate many checkpoints.

---

### 15. Make monitor caches byte-budgeted

The current LRU cache is bounded by entry count, not memory. Several large target/replay datasets can therefore remain resident unexpectedly.

Use a cache budget in bytes, or cache compact arrays / prebuilt graph datasets rather than full mutable ASE `Atoms` collections.

---

### 16. Stream state-dict hashing and avoid unnecessary tensor clones

Some deployment and replay digest helpers call `.tobytes()`, creating full temporary byte strings. `mace_deployment` can also clone an entire state dictionary to CPU.

Recommended changes:

- update hashers incrementally from contiguous `memoryview` buffers;
- stream tensor comparisons/digests one tensor at a time;
- clone only tensors that must be transformed or retained for the output artifact.

This can save hundreds of MiB for large MACE models.

---

## Lower-priority improvements

- Use mmap access for DATA7 center/scale/projection ZIP members as well as the fitted matrix.
- Cache first successful per-frame descriptor logical-digest verification by record digest and shard file identity.
- Replace Python set construction in authenticated `FrameData` restoration with vectorized monotonic/uniqueness checks when validation cannot be skipped.
- Track worst per-configuration force RMSE as a streaming scalar when no real condition grouping is requested, instead of creating one condition entry per configuration.
- Replace polling all isolated worker processes every 50 ms with event-driven completion or a bounded executor after path-only tasks are implemented.
- Reuse structural thread-autotuning results by atom count, cell class, and feature-policy digest.

---

## Scaling boundary after all completed fixes

No additional campaign-wide unbounded quadratic algorithm was found. The principal intended terms remain:

- exact structural geometry: `O(N A²)`;
- bounded farthest-point selection: `O(N K d)`;
- bounded randomized projection: approximately `O(N p k)`;
- selected-ladder neighbor coverage: `O(K² d)`.

Here `N` is frame count, `A` atom count, `K` the bounded selection ladder, `p` input dimension, and `k` retained projection dimension.

The dominant practical risks are therefore now **redundant full-array passes, serialization of mapped data, source re-parsing, small-object expansion, and memory-bandwidth pressure**, not a newly discovered all-frame `O(N²)` computation.

---

## Recommended implementation order

1. Path/range-only isolated-worker tasks.
2. Authenticated fast restoration for DATA6/DATA7/frame-cache arrays.
3. One-pass VASP source parsing.
4. Bulk shard-level MACE summary extraction and NPZ-member mmap.
5. Structural aggregation scratch/preallocation and shared pair geometry.
6. Columnar DATA7 weights and lazy DATA6 event/environment catalogs.
7. Cached MACE monitor graphs across checkpoints.
8. Streaming scientific/state-dict digests and reduced cloning.

These changes preserve the scientific feature definitions, split semantics, numerical precision, and authentication model when implemented with the stated trust boundaries.
