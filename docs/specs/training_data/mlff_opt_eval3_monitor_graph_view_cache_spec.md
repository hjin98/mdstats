# OPT-EVAL3: monitor graph and immutable evaluation-view cache specification

Status: implemented in mdstats 0.20.99a0.

## Purpose

OPT-EVAL3 removes repeated CPU-side monitor preparation from checkpoint evaluation.
It does not change training data, reference labels, prediction identity, checkpoint
selection thresholds, or scientific acceptance semantics.

The stage has two independent caches:

1. a MACE graph cache for model inference; and
2. an immutable pre-indexed evaluation view for metric reduction.

Both are reconstructable execution evidence. The frozen target/replay monitor files
remain the scientific source of truth.

## MACE monitor graph identity

A prepared graph shard is reusable across candidate checkpoints only when all graph
construction inputs match. The content-addressed key binds:

- ordered monitor geometry identities for the shard;
- calculator class;
- MACE cutoff (`r_max`);
- calculator/default dtype;
- active head;
- atomic-number/species table;
- available head table;
- MACE info/array key mappings, including charge mapping;
- MACE graph-cache policy version; and
- runtime dependency identity for MACE, PyTorch, ASE, e3nn, matscipy, NumPy, and
  torch-geometric.

The key deliberately excludes checkpoint/model weights. Graph topology and graph input
construction are model-independent when the graph policy above is identical, allowing
fold/epoch models to share the same prepared monitor graph.

## Graph cache tiers

### In-memory tier

Stable monitor shards are cached as CPU graph batches under a byte budget controlled by
`MDSTATS_MACE_MONITOR_GRAPH_CACHE_BYTES` (default 1 GiB). Small monitor graph sets that
fit within this envelope remain resident across checkpoint providers. Cache hits clone
the CPU graph and perform one transfer to the calculator device.

The older object-identity batch LRU remains available for DATA6/other callers that do
not provide stable monitor geometry identities.

### Persistent tier

Campaign evaluation passes `<internal>/evaluation-graphs` as the persistent cache root.
Each stable shard is serialized as a CPU PyTorch-geometric batch plus atom counts, with
a JSON metadata record and SHA-256-authenticated `.pt` bytes.

On restart or after in-memory eviction:

- metadata/key mismatch -> cache miss;
- dependency/policy mismatch -> distinct key/cache miss;
- SHA mismatch/corrupt bytes -> cache miss;
- malformed graph/count payload -> cache miss;
- valid shard -> load on CPU, repopulate memory cache, transfer to active device.

A cache miss rebuilds from the authenticated source geometry and atomically replaces the
persistent shard. The graph cache may never substitute for source monitor identity or
bypass target/replay artifact SHA validation.

Parallel workers single-flight the same stable shard miss. Different graph keys may be
prepared independently.

## Host/device ownership

Graph construction now occurs on CPU. The pre-OPT-EVAL3 path built a device batch and
then cloned it back to CPU solely for caching. OPT-EVAL3 instead stores the original CPU
batch and performs one CPU-to-device transfer for the inference call.

For a single-model MACE calculator, prediction no longer clones the just-materialized
device batch before forward evaluation. Ensemble calculators retain per-model clone
isolation.

Pinned-memory/nonblocking transfers are intentionally not enabled by default. They are
reserved for a later measured optimization if profiling demonstrates a benefit.

## Immutable evaluation dataset view

Repeated checkpoint metrics no longer re-extract labels and grouping metadata from ASE
objects. One authenticated monitor/policy view precomputes:

- configuration and atom counts;
- flat force offsets;
- reference energies and forces;
- atomic numbers;
- per-focus-species local atom indices;
- condition IDs and sorted condition labels;
- reference stress values and stress-valid masks.

The view is read-only and cached by authenticated monitor file identity plus the label,
focus-species, and condition-key policy. Its byte budget is controlled by
`MDSTATS_MLFF_EVALUATION_VIEW_CACHE_BYTES` (default 512 MiB).

Metric formulas are unchanged from the pre-OPT-EVAL3 implementation:

- energy MAE per atom averaged over configurations;
- force-component RMSE;
- focus-species force-component RMSE;
- optional stress-component RMSE;
- condition-group RMSE or worst-configuration RMSE; and
- the same configured combined-loss weights.

## OOM backoff and batch boundaries

Evaluation retains the existing batch-size policy and recursive OOM backoff. Stable
geometry identities are split in exactly the same way as atom batches, so a smaller
backoff batch gets its own correctly bound graph shard.

Single-frame remainder batches also use the stable graph path when geometry identities
are supplied.

## Backward compatibility

- No TOML keys are required.
- Existing 0.20.98a0 campaign databases, prediction artifacts, checkpoint caches, and
  replay artifacts remain valid.
- Prediction-artifact schema remains unchanged.
- Checkpoint-evaluation record schema remains unchanged.
- Callers that do not provide `graph_cache_directory` retain non-persistent behavior.
- Third-party/test prediction providers exposing the older `predict_batch(atoms)`
  surface remain supported.

## Qualification gates

Focused tests require:

1. metric output equivalence to the pre-OPT-EVAL3 definitions;
2. immutable evaluation-view cache hits reuse the same extracted arrays;
3. real MACE graph persistence survives an in-memory cache clear with zero new
   `AtomicData.from_config` calls;
4. cached and rebuilt real-MACE predictions agree exactly for energy and forces on the
   fixture;
5. corrupt persistent graph bytes are rejected and rebuilt from source geometry;
6. changed geometry identities create a distinct graph shard;
7. concurrent graph misses are single-flight;
8. OPT-EVAL1/OPT-EVAL2, true-label replay, CuEq guard, checkpoint control, and native
   MACE batching regressions remain green.

## Representative local timing evidence

On the release test host using a real MACE 0.3.16 CPU fixture and a 64-frame H2O
monitor, graph preparation for one stable shard measured approximately:

- first `AtomicData.from_config` build: 0.054 s;
- authenticated persistent-shard load after clearing the memory cache: 0.0081 s;
- graph-preparation speedup: about 6.7x.

This timing isolates graph preparation rather than MACE forward inference and is not a
claim about end-to-end GPU speedup on production LTA systems.

For a synthetic 2000-frame/96-atom labelled monitor, construction of the immutable
metric view measured about 0.067 s while a repeated in-memory view lookup measured
about 15 microseconds. The purpose of this cache is to eliminate repeated ASE label,
species-mask, and condition extraction; individual metric reduction remains bounded by
processing the prediction values themselves.

## Next stage

The next recorded optimization stage is OPT-EVAL4: split heterogeneous evaluation jobs
into a bounded CPU preparation -> serialized accelerator conversion -> GPU inference ->
CPU reduction/persistence pipeline while retaining the fixed post-calibration resource
model and hard memory guards.
