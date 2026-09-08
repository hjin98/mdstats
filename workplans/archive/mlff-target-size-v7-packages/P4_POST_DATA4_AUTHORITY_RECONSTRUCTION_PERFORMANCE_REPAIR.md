---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P4-POST-DATA4-PERFORMANCE-REPAIR
parent_package: P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
status: active
created_date: 2026-09-04
branch: plan/mlff-storage-io-reset-r37-review-closure
branch_baseline: c72969a3e3496b7fd47b229da820c0d99c6a2017
scope: bounded-runtime-performance-and-observability-repair
compatibility_policy: no-scientific-or-persistence-identity-change
---

# P4 post-DATA4 authority reconstruction performance repair

## 0. Authority, problem statement, and verdict

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and high-level architectural authority. Accepted P1-P7 scientific, execution, persistence, currentness, storage-retention, final-production, and qualification semantics remain preserved except for the narrow P4 runtime implementation surface reopened below.

This repair addresses a production-scale operational regression in current `prepare` / `select-target-size` authority reconstruction. The observed runtime reaches the end of DATA4 restoration and then appears stuck because the current P4 orchestration silently performs an expensive direct VASP canonical-frame rebuild before it later restores the already-existing normalized frame cache.

The blocking implementation shape is:

```text
DATA4 restore completes
  -> build_current_target_size_authorities(...)
       -> build_source_authority_from_data2_catalog(...)
       -> build_vasp_canonical_frame_authority(...)
            -> fresh VASP source/control authentication
            -> full read_vasp_frames(...) for every run
            -> FrameData reconstruction
            -> canonical-frame construction, default parallel_workers=1
       -> neutral feature/base/split/aggregate reconstruction
       -> _load_or_rebuild_frame_data(...)
            -> only now restore normalized frame cache
       -> common preparation
```

On a valid warm cache this performs a full VASP frame re-read that is unnecessary for frame-payload acquisition. On a cache miss it may read the VASP frames once for canonical authority and then a second time to rebuild the frame cache. The lower-level canonical owner already supports per-run process parallelism and progress reporting, but the current P4 caller does not pass either, so the expensive phase is also serial and silent.

This is a **Tier-2 implementation/performance defect**, not a reason to reopen target-size science or the frozen architecture. The repair order is mandatory:

1. remove redundant full-frame I/O and reconstruction;
2. reuse the existing authenticated normalized-frame cache through one acquisition path;
3. preserve fresh P1 source/control/ensemble/energy authentication independently of frame-payload reuse;
4. restore bounded resource-aware parallelism for irreducible canonical-frame computation;
5. make the post-DATA4 phase observable.

Adding a second cache, a new persistent authority, a wrapper around the duplicate work, or unbounded shared-filesystem I/O concurrency is not an acceptable repair.

**Implementation verdict: NO-PASS until this workplan closes.** The current runtime remains scientifically valid but is not production-fit at the post-DATA4 authority-construction boundary because it retains redundant full-source I/O, drops preserved canonical-frame parallelism, and provides no progress during the expensive phase.

---

## 1. Frozen invariants

### 1.1 Tier-1 scientific invariants

The repair must preserve exactly the accepted P1-P3/P4 scientific identities and semantics. In particular, fresh VASP authentication before downstream canonical use must continue to establish all eight P1 source/frame facts:

1. primary source identity signature;
2. source-control digest;
3. exact persisted companion role/locator bindings;
4. ensemble-certificate digest;
5. reconstructed certificate ensemble value equals persisted `SourceRecord.ensemble`;
6. selected energy channel name;
7. selected energy units;
8. selected energy semantic role.

The repair must not replace these checks with cache metadata, timestamps, file existence, a DATA2 row alone, or a previously validated Python object.

The following scientific products must remain semantically and digest-equivalent for unchanged inputs:

- `SourceAuthority`;
- `CanonicalFrameAuthority` including frame ordering, canonical labels, eligibility, strain, temperature, duplicate and geometry semantics;
- neutral feature evidence;
- `NeutralStatisticalBase`;
- split-exclusion evidence;
- target-size statistical aggregate / experiment definition;
- common preparation and the downstream P3 execution identity it feeds.

### 1.2 Tier-1 architectural invariants

Preserve the accepted high-level architecture:

```text
source files + originating manifest
  -> P1 source authentication / canonical frame authority
  -> neutral statistical substrate
  -> P2 statistical aggregate
  -> P3 common preparation / execution
  -> CampaignStore current-generation authority
```

The normalized frame cache remains a **derived performance artifact**, never a scientific source of truth or a new currentness authority.

Do not reopen or redesign:

- CampaignStore generation/CAS semantics;
- P3 root, publication, replay, reducer, checkpoint, or adoption semantics;
- P4 current-terminal validation/exposure semantics;
- STOR ownership/retention/reclamation architecture;
- P5 post-selection CV/final-production science;
- P7 qualification/release semantics.

### 1.3 Determinism and resource invariants

- Worker count must not change any scientific product, ordering, digest, terminal result, or failure classification.
- Cache hit, cache miss/rebuild, and direct source reconstruction must converge to the same scientific identities for the same valid source corpus.
- Memory and process counts must remain bounded by the existing resource-planning machinery and actual task count.
- Shared-filesystem source I/O must not be parallelized merely because CPU parallelism is available. Remove duplicate source reads first; introduce bounded source-read concurrency only if measurement on the target environment demonstrates a net benefit without I/O saturation.

---

## 2. Current owners and repair boundary

The implementation agent must begin by re-confirming these owners on the branch rather than creating parallel machinery:

- `mdstats/training_data/campaign_target_size_runtime.py`
  - production `build_current_target_size_authorities(...)` orchestration;
- `mdstats/training_data/neutral_substrate/frame_authority.py`
  - P1 VASP authentication and canonical-frame construction;
  - existing `build_canonical_frame_authority(..., parallel_workers=..., progress_callback=...)`;
- `mdstats/training_data/frame_cache.py`
  - existing v2 normalized frame cache using authenticated per-array `.npy` members and mmap restore;
- `mdstats/training_data/_campaign_cli_core.py`
  - `_load_or_rebuild_frame_data(...)` and existing resource/progress helpers;
- `mdstats/training_data/data4_bundle.py`
  - existing VASP normalized-frame loading behavior and temperature-target evidence;
- P1/P4 tests and workplan evidence that establish the eight authentication facts, per-run deterministic parallel construction, current runtime cutover, and restart behavior.

The preferred repair is a **refactor of these owners**, not a new subsystem.

---

## 3. Required end state

For unchanged valid inputs, current target-size authority construction must have the following logical shape:

```text
manifest + DATA2 source catalog
  -> SourceAuthority

SourceAuthority + actual source/control/companion files
  -> fresh P1 VASP authentication
       source identity
       control interpretation
       companion bindings
       ensemble certificate/value
       selected energy semantics
       temperature-target evidence

source catalog + existing normalized frame cache
  -> authenticate cache manifest/members against DATA2 identities
  -> mmap FrameData once
       OR
     if cache is missing/stale/corrupt according to the existing rebuild contract:
       -> read each VASP frame payload at most once
       -> rebuild the existing frame cache
       -> retain/reuse that same normalized FrameData

fresh VASP authentication + one normalized FrameData mapping
  -> build_canonical_frame_authority(...)
       bounded resource-aware per-run parallelism
       progress reporting

same normalized FrameData mapping
  -> frame array index
  -> common preparation
```

There must be one normalized-frame acquisition per command invocation, and both canonical-frame construction and common preparation must consume that same authenticated mapping.

A warm-cache `prepare`, `select-target-size`, terminal reload, or resume must not call `read_vasp_frames(...)` merely to reconstruct a frame payload that is already available from the authenticated frame cache. Fresh source/control authentication remains mandatory and may still read the control/source metadata required to establish the eight P1 facts.

---

## 4. Stage P4-PERF-A — establish measurement and stage observability

### 4.1 Instrument the existing orchestration boundary

Before changing execution topology, add coarse, non-scientific timing/progress around the existing P4 authority-construction stages. Reuse existing progress/timing helpers where practical.

At minimum expose begin/end or elapsed reporting for:

1. current P1 source authentication;
2. normalized frame-cache restore or rebuild;
3. canonical-frame construction;
4. neutral feature/base/split reconstruction;
5. P2 aggregate construction;
6. common preparation.

Canonical-frame construction must emit existing per-run completion progress when it is materially long.

Progress/timing output is diagnostic only and must not participate in scientific digests, persisted campaign state, generation identity, replay identity, or result schemas.

### 4.2 Baseline evidence

Record, on one representative multi-run fixture and when available the user's production campaign:

- wall time by stage;
- whether normalized frame cache was a hit or rebuild;
- number of `read_vasp_frames(...)` calls;
- canonical-frame worker count;
- peak RSS or a defensible process-level memory observation;
- total command wall time through common preparation.

The implementation is not required to introduce a permanent telemetry database. Test instrumentation, existing progress output, and bounded benchmark scripts/commands are sufficient.

---

## 5. Stage P4-PERF-B — separate fresh P1 authentication from frame-payload reconstruction

### 5.1 Refactor the existing P1 owner, do not duplicate it

`build_vasp_canonical_frame_authority(...)` currently combines two conceptually different operations:

- fresh source/control/ensemble/energy authentication;
- normalized frame-payload reconstruction from `vasprun.xml`.

Refactor the accepted P1 owner so the authentication portion is reusable independently of frame loading. The exact local helper/type design is delegated, but the ownership rules are not:

- there must be one implementation of the eight P1 checks, not a copied second checklist in `campaign_target_size_runtime.py`;
- exact companion-file resolution and certification behavior must remain owned by the neutral-substrate/P1 layer;
- the refactored direct `build_vasp_canonical_frame_authority(...)` must compose the same authentication owner plus source frame loading plus `build_canonical_frame_authority(...)`, preserving its public behavior;
- authentication must yield or make available the temperature-target evidence required by canonical-frame construction without forcing a full frame re-read;
- failure types/messages may be normalized locally, but genuine source/control/ensemble/energy mismatches must still fail before downstream canonical authority is accepted.

Do not weaken authentication to whatever fields happen to exist in `frame-cache.json`.

### 5.2 Exact semantic preservation tests

Add focused tests that independently perturb each of the eight required facts and prove the refactored authentication path rejects the same invalid source conditions as the current direct VASP owner.

Where an existing P1 test already proves a fact through the same owner, extend/reuse it rather than duplicating a large fixture.

---

## 6. Stage P4-PERF-C — one normalized-frame acquisition and cache reuse

### 6.1 Reorder current authority construction

Change `build_current_target_size_authorities(...)` so normalized frame data is acquired **before** canonical-frame construction and only once.

The preferred orchestration is:

```text
source_catalog
  -> source_authority
  -> fresh P1 VASP authentication
  -> _load_or_rebuild_frame_data(...)
  -> build_canonical_frame_authority(
         source_authority,
         frame_data_by_run,
         temperature_targets_by_run=<fresh authenticated targets>,
         ...
     )
  -> neutral/P2 reconstruction
  -> frame_array_index from the same frame_data_by_run
  -> common preparation from the same frame_data_by_run
```

Equivalent local factoring is allowed if it retains one scientific owner and one frame-data acquisition.

### 6.2 Cache-hit contract

On a valid existing v2 frame cache:

- authenticate the cache through the existing `load_frame_data_cache(...)` checks;
- preserve mmap-backed arrays where the existing cache owner provides them;
- do not perform a full `read_vasp_frames(...)` pass;
- use the same returned `FrameData` mapping for canonical authority and common preparation.

### 6.3 Cache-miss / corrupt / stale contract

Preserve the existing fail/rebuild policy of `_load_or_rebuild_frame_data(...)` unless review finds a genuine correctness defect in that policy.

When rebuilding is allowed:

- read each source frame payload no more than once for that command invocation;
- rebuild the existing frame cache, not a new P4-specific cache;
- reuse the newly loaded normalized `FrameData` for canonical authority and common preparation rather than reloading or reparsing it;
- preserve atomic cache publication and existing hash/source binding behavior.

If a cache condition is scientifically ambiguous rather than safely rebuildable, fail closed instead of treating the cache as authority.

### 6.4 No schema expansion by default

The existing frame-cache v2 schema is already bound to the DATA2 source catalog, source identity/control signatures, run set, dimensions, entry hashes, member hashes, shapes, and dtypes. Do not create a new cache schema merely to record that fresh source authentication occurred in the current process.

A cache-schema change is permitted only if an implementation proof demonstrates that a scientific invariant cannot otherwise be preserved. Such a finding must reopen this plan for review before implementation proceeds with new persistence machinery.

---

## 7. Stage P4-PERF-D — restore bounded canonical-frame parallelism

### 7.1 Use the existing canonical owner

Wire `build_canonical_frame_authority(..., parallel_workers=..., progress_callback=...)` through the current runtime instead of adding a second parallel builder.

Worker selection must reuse the repository's existing resource-planning primitives or a directly compatible helper. It must account for:

- available CPU count;
- number of independent runs/tasks;
- available memory;
- worker-process overhead and frame-array payload size;
- existing mmap-backed cache representation where applicable.

The exact worker heuristic remains delegated to implementation, but `parallel_workers=1` must no longer be an accidental production default when multiple independent runs exist and the resource planner determines parallel execution is viable.

### 7.2 Parallelize CPU work before filesystem I/O

The canonical per-frame fingerprint/eligibility/strain construction is the primary approved parallel domain because it is run-independent CPU work and already has a deterministic process-map implementation.

Do **not** automatically parallelize full VASP source reads or fresh control authentication on a shared filesystem. If later measurement shows authentication I/O itself dominates after duplicate full-frame reads are removed, a bounded I/O-concurrency change may be proposed as a follow-on only with target-filesystem evidence and memory/open-file limits.

### 7.3 Deterministic merge

Parallel completion order must not alter canonical output order. Preserve the existing owner’s deterministic run ordering/merge semantics or repair them if a test exposes worker-order dependence.

---

## 8. Stage P4-PERF-E — regression and acceptance suite

### 8.1 Scientific identity equivalence

For the same representative valid corpus, prove equality of at least:

- `CanonicalFrameAuthority.content_digest` between the pre-refactor direct VASP path and the refactored authenticated-frame-data path;
- neutral statistical base digest;
- split-exclusion digest;
- target-size policy / experiment-definition / aggregate digests;
- common-preparation digest;
- any P3 execution-context identity directly derived from the common preparation in affected integration tests.

Run the equivalence on both cache-hit and cache-rebuild paths.

### 8.2 Worker-count equivalence

For at least worker counts `1` and `>1` on a multi-run fixture, prove identical:

- canonical frame ordering;
- frame/eligibility/strain/duplicate products;
- canonical authority digest;
- downstream neutral/P2/common digests.

### 8.3 Exact source-authentication negatives

Preserve or add tests that fail on each of:

- changed primary source identity;
- changed persisted companion binding or companion content affecting authenticated controls;
- source-control digest mismatch;
- ensemble-certificate digest mismatch;
- reconstructed ensemble value mismatch;
- selected energy channel missing/name mismatch;
- selected energy units mismatch;
- selected energy semantic-role mismatch.

A valid cache must not mask any of these failures.

### 8.4 Cache integrity/rebuild negatives

Cover:

- missing cache;
- stale source-catalog binding;
- changed source identity/control signature;
- missing entry/member;
- hash mismatch/corruption;
- run-set or dimension mismatch.

Each case must either rebuild through the existing safe policy or fail closed. No corrupted/unbound cached frame payload may reach canonical authority construction.

### 8.5 Structural I/O acceptance

Instrument the real owners and prove:

- warm-cache current authority construction makes **zero** `read_vasp_frames(...)` calls;
- cache rebuild makes at most **one** full frame read per source for the command invocation;
- canonical and common preparation receive the same normalized-frame mapping rather than independently loading it;
- no second P4-specific frame cache, authentication registry, or currentness authority exists.

Call-count tests must wrap the real source/frame owners; do not satisfy this gate by testing a fake orchestration path.

### 8.6 Runtime observability acceptance

A representative `select-target-size` invocation that has completed DATA4 restoration must visibly enter and leave the subsequent authority-construction stages. A long canonical build must show meaningful progress rather than a silent interval that appears hung.

Do not emit one line per frame. Coarse stage and per-run progress is the intended granularity.

---

## 9. Stage P4-PERF-F — affected regression and performance qualification

### 9.1 Mandatory affected suites

After the final executable edit, re-derive the exact affected surface. At minimum run:

- P1 source/canonical-frame authority tests;
- frame-cache read/write/integrity tests;
- DATA4 VASP/frame-loading tests that exercise the shared normalized-frame owner;
- `tests/test_mlff_target_size_p4d_runtime_cutover.py`;
- `tests/test_mlff_target_size_p4e_terminal_and_invalidation.py` because terminal reload reconstructs current authorities;
- `tests/test_mlff_target_size_p4g_assembled_integration.py`;
- any P3 common-preparation/restart tests whose input identity is touched;
- resource/parallelism tests covering worker planning and isolated process execution.

Run broader P4/P5/P7 or storage suites only if impact analysis shows their owners changed. This repair must not use unrelated full-suite success as a substitute for the specific I/O, authentication, and determinism gates above.

### 9.2 Bounded performance evidence

Record before/after measurements on the same representative multi-run fixture and environment:

- post-DATA4 authority-construction wall time;
- number of full VASP frame reads;
- cache restore/rebuild time;
- canonical-frame construction time and worker count;
- peak RSS or comparable memory observation;
- total time through common preparation.

Closure requires structural elimination of the redundant warm-cache full-frame read regardless of noisy wall-time measurements.

For a multi-run CPU-capable environment, canonical-frame construction should also demonstrate actual multi-worker execution when the resource planner selects it. Do not encode a universal fixed percentage speedup as scientific acceptance; filesystem/cache state and hardware differ. Instead record the measured speedup/regression and investigate any material slowdown before closure.

Long GPU training and complete production qualification remain outside this repair because the defect occurs before candidate training. A bounded production-size authority-construction run is desirable when available, but scientific closure does not depend on completing the full target-size screen.

---

## 10. Simplification and forbidden repair patterns

The implementation must prefer reduction/consolidation over addition.

### Required simplifications

- one implementation of fresh P1 VASP authentication;
- one normalized-frame acquisition per command;
- one existing normalized frame cache;
- one canonical-frame construction owner;
- one existing resource planner / process-map mechanism;
- one frame-data mapping shared by canonical construction and common preparation.

### Explicitly forbidden

Do not close this defect by:

- adding a new P4 cache, memo table, generation registry, freshness database, or sidecar authority;
- treating the frame cache as proof that current source/control/ensemble/energy semantics are still valid;
- skipping any of the eight P1 fresh authentication facts on cache hit;
- retaining the direct full VASP frame rebuild and merely adding more workers around it;
- adding a boolean such as `trust_cache`, `fast_mode`, or `skip_validation` that selects weaker science;
- introducing a second canonical-frame builder or copied authentication checklist;
- parallelizing shared-filesystem VASP reads without bounded measurement and resource controls;
- swallowing cache/authentication failures and continuing with partially trusted arrays;
- persisting progress/timing as scientific state;
- changing target-size science, reducer thresholds, partition policy, training order, or CampaignStore identity to make tests pass.

---

## 11. Documentation and evidence update

When implementation closes:

1. update the P4 implementation/evidence record with the final commands, test counts, benchmark measurements, and the exact source-read call-count evidence;
2. supersede the revision-4 note that the once-per-command full VASP frame reparse is deliberately left unoptimized, explaining that fresh P1 authentication is preserved while normalized payload acquisition now reuses the accepted frame cache;
3. document any user-visible post-DATA4 progress lines if they materially change CLI expectations;
4. do not rewrite historical implemented baselines; preserve them as evidence of the state that motivated this repair.

---

## 12. Closure checklist and Pass / No-Pass rule

This amendment may return to **PASS / CLOSED** only when all boxes are satisfied on one assembled candidate:

- [ ] fresh P1 authentication still proves all eight required source/control/ensemble/energy facts;
- [ ] one implementation owns those checks;
- [ ] warm-cache authority reconstruction performs zero full `read_vasp_frames(...)` calls;
- [ ] rebuild path performs no more than one full frame read per source per command;
- [ ] canonical authority and common preparation consume the same normalized `FrameData` mapping;
- [ ] no new persistence/cache/currentness authority was introduced;
- [ ] canonical-frame parallelism is wired through existing resource planning and actually uses `>1` workers when viable;
- [ ] serial and parallel scientific outputs are identical;
- [ ] cache-hit, cache-rebuild, and direct-source equivalence tests preserve all affected scientific digests;
- [ ] corrupted/stale cache cannot mask a source-authentication failure;
- [ ] post-DATA4 stages expose bounded progress/timing and no long silent canonical-build interval remains;
- [ ] affected P1/frame-cache/P4/P3-common/resource regressions pass;
- [ ] before/after bounded performance evidence is recorded;
- [ ] no duplicated validation logic, compatibility wrapper, new cache, or unbounded source-I/O concurrency remains;
- [ ] final independent review finds no blocking scientific, architectural, persistence, determinism, resource, or operational regression.

Any unresolved failure of fresh source authentication, scientific digest equivalence, cache integrity, worker-count determinism, single-acquisition I/O structure, or bounded resource behavior is a genuine blocker and keeps the workplan **NO-PASS / ACTIVE**.

A merely faster run is not sufficient if validation was weakened. Conversely, retaining redundant full VASP frame reads is not acceptable merely because the resulting science is correct. The accepted end state must satisfy both scientific authority and production-fit execution with the minimum justified machinery.
