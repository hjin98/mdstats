# MLFF OPT-CTRL1 control-plane and telemetry optimization specification

Status: implemented in mdstats 0.20.103a0.

## Scope

OPT-CTRL1 is the final stage of the staged MLFF optimization roadmap. It changes
orchestration, persistence, telemetry, and staging I/O only. It does not change any
scientific record identity, model weights, DATA6/DATA7/DATA8 content definition,
evaluation metric, selection threshold, verification threshold, prediction cache
schema, graph cache schema, or verification-case scientific identity.

The frozen MLFF scientific compatibility token remains `0.20.99a0`; the verification
runtime compatibility token remains `0.20.85a0`.

## 1. CampaignStore connection ownership

Each `CampaignStore` owns one persistent SQLite connection per calling thread. The
connection is never shared between threads. This removes repeated `sqlite3.connect()`
and PRAGMA setup from tiny orchestration operations while preserving sqlite3's default
thread-affinity contract.

`CampaignStore.close()` closes the current thread's connection explicitly. Process
exit remains a valid final cleanup path.

## 2. Single-query optional record access

`get_payload_optional()` and `get_record_optional()` return `None` for a missing key.
They perform one SQL payload lookup and one JSON decode. `get_record()` no longer
performs an initial record lookup followed by a second call to `get_payload()` for
ordinary records.

Hot restart/evaluation/verification paths use the optional accessors rather than
`has_record()` followed by `get_record()`/`get_payload()` where the missing-record
case is expected and nonexceptional.

## 3. Batched durable writes

`CampaignStore.put_records()` serializes all filesystem-backed payloads before opening
the SQLite transaction, then persists the compact SQLite rows with one `executemany()`
transaction. It is used only for naturally grouped parent-side records where all rows
belong to one orchestration transition, including training execution + checkpoint
catalog and protocol-comparison + selected-family publication.

Large external/sharded payload creation must never hold the SQLite write lock.

## 4. Durable immutable-file SHA-256 receipts

The campaign configures `<workspace>/.mdstats/hash-receipts.sqlite3` as an optional
restart cache for SHA-256 authentication. A receipt is keyed by:

- resolved absolute path;
- device id;
- inode;
- byte size;
- `mtime_ns`;
- `ctime_ns`.

The receipt only eliminates repeated byte reads when this entire strong stat identity
matches. A changed identity forces a fresh hash. A post-hash stat comparison remains
binding, so a file modified while hashing is retried exactly as before. Receipt-DB
errors are performance-only failures and fall back to the in-process byte hash.

The receipt table is bounded during campaign compaction; pruning receipts never
invalidates scientific state because receipts are reconstructable acceleration data.

## 5. NVML telemetry and fallback

GPU telemetry first uses a process-persistent direct `libnvidia-ml.so.1` backend via
`ctypes`. Device handles are cached per GPU index and the NVML library is initialized
once per process. No additional Python package is required.

If NVML cannot be loaded, initialized, or queried, mdstats falls back to the existing
`nvidia-smi --query-gpu=...` subprocess path. If neither mechanism is available,
telemetry remains unavailable exactly as before and resource planning uses the
existing fallback estimates.

## 6. Reduced post-calibration inference polling

During the one-time CUDA calibration, evaluation/verification retain their existing
high-frequency `parallel_inference_monitor_interval_seconds` telemetry cadence.
After calibration, GPU-utilization samples no longer influence admission; only the
hard live-VRAM guard remains. Therefore live GPU telemetry defaults to a 30-second
cadence after calibration:

`parallel_inference_post_calibration_monitor_interval_seconds = 30.0`

The effective interval is never shorter than the normal monitor interval. Any
concurrency transition forces the next live sample immediately. This optimization is
limited to evaluation/verification inference scheduling; training keeps its original
telemetry cadence because training admission continues to depend on live epoch-window
resource observations.

## 7. Streaming replay-weight realization

Replay configuration-weight scaling no longer loads the complete ExtXYZ corpus into a
Python list. It streams ASE `iread()` frames, applies `config_weight` scaling one
configuration at a time, and writes the destination through the existing high-precision
ExtXYZ writer to an atomic temporary file. Resident configuration count is therefore
O(1) with corpus length.

## 8. Cleanup scan reuse

Campaign cleanup snapshots the run-directory list once and reuses that snapshot for
active-child detection, obsolete-runtime cleanup, and checkpoint-model-cache cleanup.
It no longer repeats the same top-level `runs/` directory scan for each sub-cleaner.

Completed preflight cleanup also fetches the preflight payload once instead of
performing separate existence and payload reads.

## 9. Compatibility and failure behavior

All new caches and pooling behavior are reconstructable. Failure of a receipt cache,
NVML backend, optional-record fast path, or grouped-write optimization must either
fall back to the previous qualified behavior or raise before scientific state is
silently altered.

No existing campaign must rerun prepare, train, evaluate, or verify merely because it
is upgraded from 0.20.102a0 to 0.20.103a0.

## 10. Qualification

Required focused tests cover:

- one persistent SQLite connection per thread;
- one-query optional record restoration;
- one-transaction grouped record publication;
- durable SHA-256 reuse after process-local cache reset;
- stat-identity invalidation of stale SHA-256 receipts;
- NVML preference and `nvidia-smi` fallback;
- reduced post-calibration telemetry cadence and unchanged calibration cadence;
- streamed ExtXYZ replay-weight scaling;
- existing campaign restart/evaluation/verification/cache regressions.

Representative release-host microbenchmarks measured:

- 3000 tiny SQLite metadata reads: about 0.028 s with the persistent connection vs
  0.687 s when reopening SQLite for each read (~24.5x less connection overhead);
- restart authentication of a 64 MiB immutable file: about 0.255 s for a fresh SHA-256
  byte scan vs 0.010 s from a durable strong-stat receipt (~25.6x faster).

These are isolated control-plane microbenchmarks, not end-to-end campaign speedup
claims. NVML was not live-benchmarked on the release host when no NVIDIA driver device
was available; preference/fallback behavior is covered deterministically.
