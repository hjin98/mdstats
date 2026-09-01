# Part VI - Bounded execution, restart, and performance architecture

## Purpose and authority

Execution optimization is acceptable only when it preserves the scientific and
statistical authorities in Parts I-V and improves measured throughput, memory,
storage, or restart cost. Utilization is diagnostic; authenticated records,
deterministic decisions, and exact scientific digests decide correctness.

Worker count, queue depth, query-block size, cache location, file-backing
threshold, storage path, and similar execution choices do not enter scientific
identity unless a current specification explicitly makes them part of the
algorithm.

The central rule is:

> change how exact work is scheduled or represented, not what evidence is
> consumed or what authoritative decision is produced.

## Work/span and single-level parallelism

For serial work (T_1), critical path (T_\infty), and (P) admitted CPU
lanes,

$$
T_P\ge\max\!\left(\frac{T_1}{P},T_\infty\right).
$$

Independent work is exposed at the highest useful level. Nested numerical
parallelism is suppressed while outer work fills the resource budget:

$$
P_{\mathrm{outer}}P_{\mathrm{native}}\le P_{\mathrm{budget}}.
$$

The resource scope controls cKDTree, BLAS, OpenMP, PyTorch, and other native
threads. A process or worker does not independently oversubscribe the host.
The implementation may use exact kernels such as `query_ball_point`,
`numpy.bincount`, bounded indexed reductions, or `threadpoolctl`; these are
execution realizations and do not change evidence roles or canonical order.

## Preparation and execution boundaries

The source/frame and numerical-label authorities are built once and validated
through their current owners. The neutral statistical substrate supplies the
one `P_train`/`M3` split and the two canonical orders. The current P3 common
preparation is then computed once and shared by all authorized candidate
sizes and optimizer seeds.

```text
source/frame/label authorities
  -> neutral statistical substrate and protected relations
  -> one P_train/M3 split and pi_train/pi_eval
  -> one common target-size preparation
  -> paired-seed candidate screen
  -> selected binding
  -> selected-only CV and fresh final production
```

The common preparation is a single authenticated authority, not one independent
copy per candidate or fold. A post-selection CV fold may create a fold-local
fitted view from its own training partition when its owner requires it, but it
cannot create a target-size ladder or alter `T_selected`.

Foundation-model providers and large accelerator references are released as
soon as their final preparation consumer completes. Derived file
materialization and target-size candidate views run on CPU/I/O resources unless
their current owner explicitly admits an accelerator task. Heavy caches are
restored lazily only when a validated artifact is needed.

## Candidate execution and continuation

The target-size screen executes only the cells authorized by the reducer's
funnel:

```text
qualified candidates
  -> coarse n1/M1
  -> at most four short n2/M2 continuations
  -> two final n3/M3 continuations
  -> one selected size or typed scientific failure
```

Each `(candidate size, optimizer seed)` cell runs through the accepted TRAIN2
runtime and current EVAL2 owner. A bounded numerical fake may sit below the
accepted MACE seam in tests; configuration resolution, target authorities,
materialization, checkpoint/provider authentication, persistence, and reducer
publication remain production code.

At a fidelity boundary, continuation restores model, optimizer, EMA, LR, and
Python/NumPy/Torch CPU/CUDA RNG state. It does not restart from the foundation
or substitute an earlier checkpoint. Atomic content-addressed publication
means an interrupted boundary either has a complete authenticated endpoint or
has no current endpoint. The execution head is reconciled before new work is
scheduled, and compare-and-set adoption prevents two workers from becoming
current simultaneously.

Eliminated candidates receive no later ordinary-production authorization.
Exhaustive full-fidelity training of every configured size is a separate
algorithm/decision-preservation qualification, not a default campaign artifact
generator.

## Deterministic resource-bounded work queue

CPU-heavy independent tasks use a shared queue with explicit CPU, memory, and
I/O ownership. Its responsibilities are to:

- bound executing, ready, in-flight, and buffered work;
- reserve persistent memory before admitting temporaries;
- propagate deterministic task identities and exceptions;
- permit arbitrary completion order where scientific order is irrelevant;
- restore canonical reduction and commit order where FP64 arithmetic or record
  order is authoritative;
- expose progress and resource telemetry without placing telemetry in scientific
  identity.

Submission may run ahead to hide hand-off latency, but simultaneous execution
remains within the declared resource scope. On NUMA systems, node-local queues,
affinity, local stealing, and bounded cross-node stealing are valid execution
extensions after measurement; they cannot change canonical membership or
reduction order.

## Staged evaluation and provider lifetime

Current staged evaluation uses bounded CPU preparation, one admitted accelerator
owner when applicable, and bounded CPU finalization. The parent execution owner
enumerates the authenticated endpoints, workers perform only their assigned
preparation/inference/finalization, and the parent validates run, checkpoint,
selected-binding, prediction, and metric identities before durable publication.
Fresh and cache-backed endpoints converge through the same parent validation.

Provider scopes are explicit and non-overlapping:

```text
candidate provider acquire -> candidate inference/replay consumers
  -> candidate close in exception-safe cleanup
  -> foundation or next provider acquire only after closure
  -> foundation close in exception-safe cleanup
```

Post-selection CV and final-production providers are likewise closed at their
owner boundary, including failure paths. A replay cache stores scalar/content
evidence, not a live provider. Garbage-collection timing or allocator cleanup
does not replace provider retirement.

A worker-private provider shell may be reused only when checkpoint bytes,
model class, state keys/shapes/dtype, weight-independent runtime architecture,
geometry workload, device, and backend policy all authenticate as compatible.
Weight-dependent calculator state is invalidated on replacement. Corruption or
authority mismatch is fatal rather than a fallback to an unqualified shell.

## One authority per semantic input

The bounded execution representation is:

```text
one canonical frame/feature authority
one neutral statistical substrate
one P_train/M3 split and pi_train/pi_eval
one common preparation
prefix views for candidate rungs
training and CV artifacts only for authorized work
```

Memory/storage must not scale as one product-sized descriptor, graph, or
membership copy per target-size rung. Descriptor shards, fixed-file views,
replay indexes, and frame caches are reconstructible only when their content
and recipe identities authenticate. A cache hit is never a substitute for the
selected binding or another scientific authority.

## Memory, storage, and scratch admission

Long stages account for

$$
M_{\mathrm{stage}}=
M_{\mathrm{persistent}}+M_{\mathrm{inflight}}+M_{\mathrm{buffered}}+
M_{\mathrm{sparse}}+M_{\mathrm{result}}+M_{\mathrm{scratch}}.
$$

New work is admitted only when CPU, RAM, accelerator, disk, and scratch
reservations fit the stage plan. The live ledger is authoritative: a
prospective target-size or evaluation reservation replaces only the exact
modeled reservation it supersedes and preserves all other live owners. When
retained growth is not bounded, sequencing is conservative rather than relying
on an optimistic projection.

Large reconstructible arrays may use mmap/file-backed persistence. Atomic
publish-or-validate-winner rules protect concurrent fixed-file and materialized
cache creation. Stale, corrupt, or mismatched caches are rebuilt; they are not
silently accepted as evidence.

Persistent campaign state uses a compact SQLite store, append-only event
history where needed, content-addressed files for large payloads, and
completion records written only after required artifacts are durable. A restart
distinguishes complete, incomplete, stale, corrupt, and superseded state and
re-authenticates currentness before reuse. Cleanup removes only known
campaign-owned reconstructible state and preserves external inputs, selected
scientific records, restart checkpoints, and diagnostics needed for recovery.

## Storage and I/O management

Storage is a first-class resource plane and never a second scientific
authority. `mdstats.training_data.storage` turns each accepted current owner
into a uniform *owner view* and composes those views into one cross-owner
inventory. Semantics come from the owning API; pathnames, report labels, stage
names, process ids, and file ages carry no authority at all.

Every consequential mutation follows one path:

```text
real P1-P7 owners -> owner views -> cross-owner inventory snapshot
 -> resolved storage policy -> immutable owner-bound plan
 -> owner publication barrier + revalidation -> executor -> durable audit
```

**Retention is a transitive closure, not a per-owner question.** The current P7
publication is a read-only descendant of the accepted P5 publication and
re-authenticates the exact P5 checkpoint bytes at their canonical hot paths, so
those bytes stay pinned after the P7 attempt retention reference is released.
P4's current terminal authority pins the P3 evidence its canonical loader needs.
A truthful `waiting_for_reference` pins the whole predecessor lineage. Protection
is monotone: no owner's cache or history classification overrides another current
owner's requirement, and the closure is rebuilt from live owner records rather
than persisted as a second registry.

**Mutation is race-safe, not merely recent.** P5 and P7 both publish an
immutable object and then the pointer that makes it current, so there is a real
window in which the object exists and nothing references it. Each owner exposes
a per-generation publication barrier that the publisher holds across both steps
and that any storage mutation acquires across revalidation and mutation. The
storage-operation lease serializes storage against storage only, and is never
mistaken for serialization against the owners.

**Archive is representation, not resolution.** Hot bytes are replaceable only
for owner-declared historical bulk with no current or restartable hot
dependency; no P1-P7 loader is given an implicit cold-read fallback. Archive
verification and restore bound member paths, member types, member count, total
expansion, per-member size while streaming, and decompression amplification
before writing anything, and a manifest carries an identity-owned relative
locator resolved only inside the storage-owned archive root. Terminal catalog
and restore receipts are published only downstream of flush, atomic publish,
directory-entry persistence, and authentication of the published bytes.

**Deduplication is inode sharing under an owner contract.** Exact byte equality
is necessary but never sufficient: file type and owner-required metadata must
match, the family must have no accepted in-place writer, and cross-device or
unsupported filesystems retain duplicate bytes without a correctness failure.

Storage owns durable state of its own - an identity-keyed archive catalog,
manifests and blobs, restore journals, a bounded execution audit, and
operation-serialization state - under an explicit control-plane root. None of it
carries a currentness decision, and none of it can be reclaimed while a retained
cold representation still needs it.

## GPU/VRAM and host admission

GPU jobs are admitted against explicit device availability, free memory, and
configured budget evidence. A one-job calibration establishes whether the
applicable serial workload is viable; it does not by itself authorize parallel
expansion. Soft utilization and fractional-VRAM envelopes regulate additional
jobs, while a hard live-VRAM guard protects against OOM. Missing telemetry at
calibration startup selects conservative serial execution when the device is
otherwise usable; it does not create parallel evidence.

An execution controller may lower concurrency after measured resource pressure,
but it cannot change scientific batch/exposure semantics, precision policy,
checkpoint evidence, or target/replay membership to fit memory. OOM recovery is
valid only when the retry is protocol-equivalent and the changed parameter is
non-semantic.

## Replay indexing and bounded parsing

The selected replay source remains external scientific authority. A
reconstructible index may store source-byte identity, frame offsets/lengths,
atom counts, and source-order geometry identity for sparse monitor access and
bounded chunk parsing. Source mutation or index corruption causes safe
reconstruction. Parser concurrency is added only when representative
measurement shows benefit and exact replay bytes/identities remain unchanged.

## Progress and observability

Every long-running stage exposes scientific progress and executor state:

1. completed/total work and percent where meaningful;
2. elapsed time and ETA when estimable;
3. throughput with an explicit stable unit;
4. active, pending, or buffered work;
5. resource pressure or the current hot item where relevant.

Heartbeats are emitted during long periods without task completion. ETA is based
on globally committed work. User-facing elapsed and known ETA use fixed
`HH:MM:SS`; unavailable ETA is `--:--:--`. Presentation state never enters
scientific digests.

## Performance qualification boundary

Performance changes are compared on representative work with equivalent
scientific inputs and runtime conditions. Evidence records wall/CPU time,
throughput, RSS/VRAM, scratch/storage, queue/backpressure, and output digests
when material. A speedup obtained by changing precision, evidence population,
ordering, or output is not a conforming optimization.

Target-machine GPU and long real-production qualification remain separate from
P6 functional closure. They require their own supported hardware, workload,
backend, and acceptance evidence; the current campaign does not infer those
results from CPU or bounded numerical tests.
