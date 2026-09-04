# P4 post-DATA4 authority reconstruction performance repair — implementation evidence

Amendment: `P4_POST_DATA4_AUTHORITY_RECONSTRUCTION_PERFORMANCE_REPAIR.md`
Branch: `plan/mlff-storage-io-reset-r37-review-closure`
Environment: conda `mace`, Python 3.11, torch 2.13.0+cu126, mace-torch 0.3.16, 32 CPU threads

---

## 1. What changed, by owner

### `mdstats/training_data/neutral_substrate/frame_authority.py`

Fresh P1 authentication and normalized frame-payload acquisition were one function.
They are now three composable owners:

- `authenticate_vasp_source_authority(...)` — the **single** implementation of the eight
  P1 source/control/ensemble/energy checks. It reads only the control/source metadata
  those checks need and reads **no** frame payload. It returns `AuthenticatedVaspSource`
  records carrying the authenticated energy channel and the temperature-target evidence
  canonical construction requires.
- `read_authenticated_vasp_frame_data(...)` — reads the normalized payload of
  already-authenticated sources.
- `build_vasp_canonical_frame_authority(...)` — unchanged public behavior; it now
  *composes* authentication + source read + `build_canonical_frame_authority(...)`.

No check was moved, weakened, or duplicated. There is no second checklist anywhere.

### `mdstats/training_data/campaign_target_size_runtime.py`

`build_current_target_size_authorities(...)` was reordered from

```text
source authority -> direct VASP canonical rebuild -> neutral/P2 -> load frame cache -> common
```

to

```text
source authority -> fresh P1 authentication (no frames)
  -> one normalized-frame acquisition (_load_or_rebuild_frame_data)
  -> canonical frame authority (same mapping, planned workers, progress)
  -> neutral / P2 -> frame array index -> common preparation (same mapping)
```

Added alongside it:

- `_authority_stage(...)`, a diagnostic begin/end + elapsed reporter for each of the six
  post-DATA4 stages. Nothing it emits enters a digest, persisted state, generation or
  replay identity, or a result schema.
- canonical-frame worker planning through the existing `_resolve_feature_worker_count`
  planner, plus a measured work-size ceiling
  (`CANONICAL_FRAME_PARALLEL_ATOM_FRAME_FLOOR`) so a corpus too small to repay one-shot
  worker startup stays serial. `parallel_workers=1` is no longer an accidental default.
- per-run progress forwarded from the canonical owner's existing `progress_callback`.

### `mdstats/training_data/_campaign_cli_core.py`

`_resolve_feature_worker_count(...)` gained a `maximum_workers` passthrough to the
existing `resolve_worker_count(...)` parameter. No new planner.

---

## 2. Closure checklist

| Requirement | Evidence |
| --- | --- |
| fresh P1 authentication proves all eight facts | `test_p4_authentication_rejects_each_perturbed_source_fact` (7 parametrized negatives) |
| one implementation owns those checks | `test_p4_no_second_frame_cache_or_currentness_authority` asserts the orchestration contains no `certify_vasp_simulation_controls` / `read_vasp_frames` |
| warm cache performs zero full frame reads | `test_p4_warm_cache_authority_reconstruction_reads_no_source_frames` (wraps the real `mdstats.io.read_vasp_frames`) |
| rebuild reads each source at most once | `test_p4_cache_rebuild_reads_each_source_at_most_once` |
| canonical + common share one `FrameData` mapping | `test_p4_canonical_and_common_share_one_frame_data_mapping` (object identity) |
| no new persistence/cache/currentness authority | `test_p4_no_second_frame_cache_or_currentness_authority` |
| parallelism wired through existing resource planning and really uses `>1` | `test_p4_canonical_frame_construction_is_worker_count_invariant[2]` on a real two-run corpus asserts `workers=2` in the owner's own progress lines |
| serial and parallel outputs identical | same test: digest, frame order, eligibility, strain, duplicates all equal the direct-source reference |
| cache-hit / cache-rebuild / direct-source equivalence | benchmark records one `CanonicalFrameAuthority.content_digest` across all three paths |
| corrupt/stale cache cannot mask authentication failure | authentication reads the real files and runs before any cache is consulted; perturbation negatives above |
| post-DATA4 stages expose progress | `[authority] <stage>; status=start/complete; elapsed=…` and `[canonical frames] …` per run, visible in P4-D captured output |
| affected regression | §4 |
| before/after performance evidence | §3 |

---

## 3. Bounded performance evidence

`benchmarks/benchmark_mlff_p4_authority_reconstruction.py`
(results: `benchmarks/benchmark_mlff_p4_authority_reconstruction_results.json`),
6 runs, real VASP corpus, `CPU 28/32 threads; RAM ~33 GiB available`.

| frames/run | phase | wall | source frame reads | workers | peak RSS |
| ---: | --- | ---: | ---: | ---: | ---: |
| 96 | before / direct VASP rebuild, serial | 0.90 s | 6 | – | 216 MiB |
| 96 | after / warm cache, serial | 0.79 s | **0** | 1 | 216 MiB |
| 96 | after / warm cache, planned | 0.70 s | **0** | 1 | 218 MiB |
| 96 | after / warm cache, unbounded workers | 2.53 s | 0 | 6 | 218 MiB |
| 96 | after / cache rebuild, planned | 0.90 s | 6 | 1 | 218 MiB |
| 1024 | before / direct VASP rebuild, serial | 9.82 s | 6 | – | 342 MiB |
| 1024 | after / warm cache, serial | 7.55 s | **0** | 1 | 346 MiB |
| 1024 | after / warm cache, planned | **5.33 s** | **0** | 6 | 346 MiB |
| 1024 | after / cache rebuild, planned | 7.21 s | 6 | 6 | 346 MiB |

`CanonicalFrameAuthority.content_digest` is identical across every phase and both sizes.

**Structural closure** does not depend on wall time: warm-cache reconstruction makes
**zero** `read_vasp_frames(...)` calls where it previously made one per source, and the
rebuild path makes exactly one per source instead of potentially two.

**Investigated slowdown.** The first measurement showed the unbounded worker plan was
~3× *slower* than serial on a small corpus (2.53 s vs 0.79 s): canonical-frame workers
are one-shot subprocesses, so they pay a roughly fixed interpreter/task-serialization
cost of ≈2 s before any per-run work. Break-even was measured between 512 and 1024
frames per run on this fixture. Rather than accept a real regression for small
campaigns, the runtime now bounds the planned worker count by the work available
(`CANONICAL_FRAME_PARALLEL_ATOM_FRAME_FLOOR = 8192` atom-frames, calibrated from these
measurements). Small corpora stay serial and are slightly *faster* than before; a
representative corpus reaches 6 workers and 1.77× faster than the pre-repair path.

Long GPU training and full production qualification remain out of scope: the defect
occurs before any candidate training.

---

## 4. Affected regression executed

Re-derived from the final diff (callers/references of the changed owners), run under
`conda run -n mace python -m pytest -p no:randomly -n 24`:

- `tests/test_mlff_neutral_scientific_substrate.py` (P1 source/canonical-frame authority)
- `tests/test_mlff_target_size_p4_authority_reconstruction_io.py` (new)
- `tests/test_mlff_target_size_p4a…p4g` (campaign state, cutover, adoption, runtime
  cutover, terminal/invalidation, storage/docs structure, assembled integration)
- `tests/test_mlff_target_size_execution_p3a…p3f`, `p3a4`, `p3a9`
- `tests/test_mlff_data4_*`, `tests/test_mlff_data5_partition_roles.py`, `tests/test_vasp.py`
- `tests/test_mlff_parallel_resources.py`, `tests/test_runtime_resources_ld10.py`
- P5/P6/P7 suites that consume the shared owners

---

## 5. Fixture reconciliation (not a scientific change)

The shared P1 test corpus placed its two atoms ~6.9 Å apart in a 10 Å cell. No MACE
cutoff in the accepted architecture describes that corpus, which only became visible
once P3 began fitting a real neighbor normalization (see the P3 evidence record). The
second atom moved to fractional `(0.35, 0.35, 0.35)` so the fixture is a corpus an MLFF
can actually be trained on. Digests in these tests are computed, not hard-coded, so this
changed no assertion's meaning.

One P4-E fixture (`_terminal_failure_campaign`) previously reached terminal *scientific
failure* only because a candidate digest happened to fall a particular way. It now
constructs that verdict deliberately through `_CeilingSuperiorHarness`, which makes the
configured ceiling materially superior by candidate size.
