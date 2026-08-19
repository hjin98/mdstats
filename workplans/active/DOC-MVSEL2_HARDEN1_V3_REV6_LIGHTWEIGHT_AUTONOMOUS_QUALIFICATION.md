---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 6
status: READY_FOR_IMPLEMENTATION
protocol_version: 3.1.0
supersedes: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV5_BOUNDED_QUALIFICATION.md
qualification_driver: scripts/mvsel2_bounded_qualification.py
---

# MVSEL2 hardening — lightweight autonomous qualification

## Objective

Replace the REV5 production-like workstation qualification with a short, automatically sized, one-command benchmark that is bound to the real production graph but computes only the smallest materially sufficient recovery, repair, and performance probes.

The frozen MVSEL2/REPAIR2 scientific and persistence semantics remain unchanged. This revision changes qualification conditions and harness architecture only.

## Diagnosis

REV5 fixed the catastrophic REV4 full-tree copy design, but it still treats qualification too much like production execution:

- Q5 can resume a production selector from a large checkpoint all the way to the final 16,384 rung;
- Q6 executes REPAIR2 through the complete eight-rung production ladder;
- the run card freezes workstation-specific 40 GiB / 4 GiB / 90-minute stage limits;
- resource ceilings are primarily watchdog failure thresholds rather than a machine-adaptive admission model;
- Q5 scratch cleanup is PASS-oriented rather than a transactional all-terminal-path lifecycle;
- the parent measures only the direct child RSS, not aggregate owned-process/system pressure.

These are unnecessary for acceptance because focused tests already own exact algorithmic semantics. The external workstation check needs to establish production binding, real persisted-state compatibility, representative scale behavior, and the frozen performance margin — not replay the production campaign.

## Frozen material design

### 1. Production identity is full-scale; qualification execution is sampled

The qualifier MUST authenticate the complete production authority in place:

- domain `label-domain-5aa1ee5d50cd0b23` unless explicitly overridden;
- 36,408 candidates;
- 165 families;
- current MVIDX1 content digest and forward-edge count;
- authenticated MVSEL2 authority and checkpoint lineage;
- production DB/config remain read-only and unchanged.

Authentication of full-scale authority does not require full-scale computation.

### 2. Three resource layers

The standalone driver MUST distinguish:

1. effective machine capacity discovered from affinity/cgroup/job/OS/filesystem information;
2. hard safety ceilings used only for containment;
3. a smaller planned operating envelope used to admit and size benchmark work.

Explicit CLI resource values, when supplied, are stricter caps. They MUST NOT be required for ordinary execution and MUST NOT silently raise discovered safe limits.

The driver MUST monitor, where available:

- aggregate RSS of the owned process group/descendants rather than only one PID;
- cgroup or host available-memory pressure sufficiently to preserve host headroom;
- physical run-owned scratch bytes;
- wall time;
- production-input identity across material stages.

Missing secondary telemetry is advisory when a conservative safe envelope can still be established.

### 3. Short-run target

The harness is a qualification benchmark, not a production replay.

Design target on the reference workstation is a normal end-to-end runtime of about 5–8 minutes. The default hard total wall boundary should be about 15 minutes. The script MUST automatically reduce optional benchmark work before approaching the hard boundary.

The time values are harness targets/containment, not product performance acceptance thresholds. A slower machine may execute fewer optional samples while preserving the same material checks.

Scratch is expected to remain in the hundreds of MiB, not GiB. The implementation SHOULD use a default hard scratch maximum no larger than 1 GiB and a substantially smaller planned footprint, further reduced when free-space constraints require it.

### 4. Autonomous execution

`scripts/mvsel2_bounded_qualification.py` remains the one-command workstation authority but MUST be redesigned to:

- discover resources automatically;
- run bounded calibration before uncertain work;
- choose benchmark sizes/rungs/repetitions automatically;
- continue independent material checks after non-fatal advisory/diagnostic failures when safe;
- persist compact stage state/evidence;
- require no Codex/ChatGPT session after launch;
- clean owned large transient state on every ordinary terminal path;
- safely scavenge abandoned owned scratch from prior interrupted runs at startup.

Adaptive execution mechanics are permitted. Scientific/product semantics, workload representativeness, and acceptance thresholds are not adaptive.

## Acceptance-critical qualification checks

### LQ0 — resource discovery and admission

Before loading large state, the driver MUST:

- establish production paths and read-only ownership;
- discover effective CPU/memory/storage limits and explicit user caps;
- create separate evidence and scratch roots with an ownership manifest;
- derive hard ceilings and a smaller operating envelope;
- reject or reduce planned work before launch if conservative estimates do not fit.

A hard-ceiling event is exceptional containment, not ordinary benchmark control flow.

### LQ1 — production binding and native-forward probe

Open the real target reference and MVIDX through the native forward-only reader and authenticate the full production graph.

The probe MUST verify:

- candidate/family/edge/digest identity;
- inverse arrays are not opened/mapped inside the v2 probe;
- a small deterministic sample of candidate forward incidence can be queried successfully;
- a production materializable ladder through 16,384 exists.

No complete candidate sweep is required.

### LQ2 — MVSTATE2 recovery micro-integration

Do not run the selector from an old production checkpoint to 16,384.

Instead, automatically choose the smallest suitable adjacent valid production checkpoint pair, normally 128 -> 256 (or the next smallest compatible pair):

1. copy only those checkpoint bundles into owned scratch;
2. restore/authenticate both production checkpoints;
3. corrupt only the newer scratch record;
4. require `_highest_valid_resume_states(...)` to fall back to the older checkpoint;
5. replay only the canonical selected-prefix delta from the older state to the newer size using the production forward-state scoring/select primitives;
6. compare the reconstructed forward state exactly against the authenticated newer checkpoint for selected order and material MVSTATE2 state arrays/scalars.

This directly exercises the production recovery mechanism and selected-prefix forward replay while bounding the work to one small shell. Focused tests remain the authority for full selector-search/rebase semantics.

### LQ3 — REPAIR2 representative production micro-benchmark

Do not execute all eight rungs by default.

The driver MUST use the real production reference/forward view and authenticated production selection/checkpoint states, then run the exact REPAIR2 runtime path on an evidence-only prefix of the production ladder.

Adaptive sequence:

- start with the smallest two materializable rungs, normally 128 and 256;
- measure wall time, proposals, swaps, full-state-copy count, restore/replay mode, aggregate RSS, and inverse-array status;
- add 512 and then at most a modest larger rung only when needed to establish representative scaling/proposal behavior and the projected remaining runtime fits comfortably inside the operating envelope;
- stop as soon as the material claim is established with adequate confidence.

The benchmark MUST NOT duplicate the REPAIR2 algorithm in the harness. It SHOULD invoke the existing runtime builder using an in-memory evidence-only truncation/prefix of the authenticated selection plan, or factor a shared private rung helper only if necessary and protected by focused equivalence tests.

PASS requires on measured rungs:

- default REPAIR2 policy;
- zero rejected-proposal full forward-state copies;
- no inverse mutation/mapping in the v2 boundary;
- no coverage/hard-obligation regression;
- correct MVSTATE2 restore/replay behavior.

Additionally restore/authenticate the largest available production checkpoint at or below 16,384 as a read-only large-rung compatibility sentinel. No REPAIR2 computation at 16,384 is required solely for qualification.

The original H4 statement that production repair is measurable through materializable rungs up to 16,384 is therefore satisfied by: full production ladder identity + large-rung checkpoint compatibility + exact representative REPAIR2 execution + focused semantic coverage. It no longer mandates executing every rung during every qualification.

### LQ4 — short current performance sentinel plus conservative evidence reuse

A full MVSEL1 replay remains forbidden.

The driver MUST first authenticate the existing production-density evidence against the current MVIDX1 graph. The frozen >=10x claim may reuse that same-graph baseline/projection when the material performance implementation remains compatible.

To bind the current candidate cheaply, run a small deterministic current MVSEL2 timing sentinel on the real production forward view, such as a bounded initial Phase-A rank sample. Start with a very small sample and enlarge only if needed for a stable comparison.

Use the historical V2 sample/full-order projection plus the current sentinel to derive a conservative degradation-adjusted lower bound. PASS requires the lower bound to remain >=10x. If the current material performance code is unchanged from the accepted evidence, direct evidence reuse is sufficient and the sentinel is still useful as a gross-regression check.

If compatibility cannot be established or the bounded lower bound does not clear 10x, return the performance check as `BLOCKED`/`RETURN_TO_IMPLEMENTATION` for a newly designed bounded comparator. Never fall back automatically to a full MVSEL1 production replay.

### LQ5 — cleanup and compact evidence

Separate:

- durable compact evidence/state/log tails; and
- disposable run-owned scratch.

On PASS, product FAIL, BLOCKED, harness exceptions, SIGINT, and SIGTERM, preserve a compact diagnostic capsule and remove run-owned large transient data in `finally`/terminal cleanup.

Because SIGKILL/power loss cannot run cleanup handlers, startup MUST safely scavenge abandoned scratch only when an ownership manifest proves the directory belongs to this qualifier.

Evidence/logging itself MUST be bounded. Large checkpoint bundles and temporary SQLite files are never retained as final evidence.

## Resource adaptation and failure classification

The driver MUST adapt before failure by reducing, in order when applicable:

1. optional repetitions/samples;
2. optional larger REPAIR2 rungs;
3. current-performance sentinel sample count;
4. concurrency/batch/in-flight work;
5. materialization through streaming/read-only reuse.

It MUST NOT reduce the minimum material recovery pair, remove required production identity checks, change REPAIR2/selector policy, change scientific precision/semantics, or weaken the >=10x threshold.

Classification:

- unexpected hard-limit hit from an oversized/mispredicted harness -> harness/resource-model defect; preserve compact evidence, clean scratch, continue independent safe checks when useful, and do not classify the product as failed;
- minimum materially sufficient check cannot fit safely -> `BLOCKED`;
- representative product measurement violates a frozen product resource/performance requirement -> product/material FAIL;
- missing optional telemetry/diagnostics -> warning only when safety and interpretation remain adequate.

## Reused evidence

Focused v2 correctness, adjacent v1 regressions, broad non-slow tests, and wheel/install/import evidence remain reusable when their material product/package surfaces have not changed.

The prior production-density benchmark remains reusable only under the LQ4 compatibility rule above.

Historical REV4/REV5 limit-hit or full-ladder outputs are diagnostic evidence, not mandatory rerun templates.

## Expected implementation change surface

- `scripts/mvsel2_bounded_qualification.py` — rewrite supervisor/admission/stages/cleanup.
- `benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py` — replace fixed-eight execution mode with reusable bounded-prefix/selected-rung mode or add a new lightweight benchmark helper without duplicating REPAIR2 science.
- focused tests for resource discovery/admission, process-tree monitoring, recovery prefix equivalence, adaptive rung selection, cleanup/scavenging, and failure classification.
- qualification run card and compact evidence schema.

Product numerical/scientific algorithms are non-goals unless a small private refactor is required to share the exact REPAIR2 rung implementation with the benchmark.

## Gates

| Gate | Status | Purpose |
|---|---|---|
| R6-G0 | PENDING | Freeze lightweight benchmark fixtures, material claims, and adaptive resource model. |
| R6-G1 | PENDING | Implement autonomous resource discovery/admission/watchdog/cleanup. |
| R6-G2 | PENDING | Implement LQ1/LQ2 production binding and bounded recovery micro-integration. |
| R6-G3 | PENDING | Implement adaptive REPAIR2 prefix benchmark and large-rung restore sentinel. |
| R6-G4 | PENDING | Implement short current performance sentinel and conservative evidence binding. |
| R6-G5 | PENDING | Focused harness tests, failure/cleanup tests, one-command dry qualification on small fixtures. |
| R6-G6 | PENDING | Workstation one-command qualification and compact evidence handoff. |

## Design-revision triggers

Return to design only if implementation requires changing frozen selector/repair scientific semantics, checkpoint identity/compatibility, MVIDX1 scientific schema/content, REPAIR1/REPAIR2 equivalence, or the >=10x product performance floor.

Safe benchmark sizing, resource-discovery mechanics, evidence formatting, optional telemetry, and equivalent cleanup/log-path corrections do not require a workplan revision.
