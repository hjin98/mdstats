---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-REV6-LIGHTWEIGHT
protocol_version: 3.1.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 6
status: DESIGN_READY_FOR_IMPLEMENTATION
---

# MVSEL2 hardening — lightweight autonomous workstation qualification

## Objective

The workstation qualification must be a short benchmark, not a production replay. It binds to the complete LTA production graph while computing only the smallest materially sufficient recovery, repair, and performance probes.

REV5 fixed the unsafe full-tree copying design but is now superseded. Do not use the old fixed 40 GiB / 4 GiB / 90-minute Q5/Q6 execution as the target design.

## Intended one-command interface

After R6-G1 through R6-G5 are implemented, the normal workstation command should require only material inputs:

```bash
set -euo pipefail
PROD_DB='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/mlff-campaign/.mdstats/campaign.sqlite3'
CONFIG='$HOME/QE/lammps-proj/zeolite/05_mace_training/LTA/mpa0/FP32/campaign.toml'
DOMAIN='label-domain-5aa1ee5d50cd0b23'

conda run -n mace python scripts/mvsel2_bounded_qualification.py \
  --production-db "$PROD_DB" \
  --config "$CONFIG" \
  --domain "$DOMAIN"
```

The script owns its bounded evidence/scratch roots, resource discovery, calibration, benchmark sizing, cleanup, and final summary. Codex/ChatGPT does not need to remain connected.

Explicit `--max-rss-*`, `--max-scratch-*`, or stricter wall limits may remain available as user caps, but ordinary execution must not require workstation-specific numbers.

## Resource-bounded execution

The implemented driver must discover the effective machine allocation and derive:

- hard safety containment;
- a smaller planned operating envelope;
- a short-work admission model.

Reference-workstation target:

- normal total wall time: approximately 5–8 minutes;
- default hard total wall boundary: approximately 15 minutes;
- expected final evidence: small JSON/state/log-tail files;
- expected scratch: hundreds of MiB, with a default hard maximum no larger than 1 GiB unless a future material requirement proves otherwise;
- CPU benchmark execution: normally serial/single-worker unless a material production-path claim requires otherwise.

The driver must reduce optional benchmark work before approaching the hard boundary. Watchdog termination is emergency containment, not normal control flow.

Monitor aggregate owned-process RSS and host/cgroup memory pressure where available, not only one child PID. Missing secondary telemetry is nonblocking if the safe envelope remains conservatively established.

## Automatic stages

### LQ0 — admission

Discover CPU/memory/storage/cgroup/job constraints, establish owned evidence/scratch directories, perform safe startup scavenging, and choose the initial benchmark plan.

### LQ1 — production binding

Read the real production reference and native forward-only MVIDX in place. Authenticate the 36,408-candidate / 165-family production graph, MVIDX digest/edge count, production selection ladder through 16,384, and inverse-unmapped v2 path. Query only a small deterministic candidate sample.

### LQ2 — recovery micro-integration

Automatically choose the smallest adjacent compatible production MVSTATE2 checkpoint pair, normally 128 -> 256.

Copy only those checkpoint bundles to scratch, corrupt the newer scratch record, require runtime fallback to the older checkpoint, replay only the canonical selected-prefix delta, and compare the reconstructed forward state exactly with the authenticated newer checkpoint.

Do not run selector search to 16,384.

### LQ3 — REPAIR2 micro-benchmark

Run the exact REPAIR2 runtime path against an evidence-only prefix of the authenticated production ladder.

Start at 128 and 256. Add 512 or another modest rung only when needed and only if calibration predicts comfortable completion. Stop when the representative claim is established.

Require zero rejected-proposal full-state copies, no inverse mapping/mutation, default policy, and no coverage/hard-obligation regression.

Separately restore/authenticate the largest valid production MVSTATE2 checkpoint at or below 16,384 as a read-only large-rung compatibility sentinel. Do not compute REPAIR2 at 16,384 merely to qualify it.

### LQ4 — performance sentinel

Authenticate the existing same-production conservative performance evidence. Never launch a fresh full MVSEL1 replay.

Run only a small deterministic current MVSEL2 timing sample on the real forward view when needed to bind the current candidate and detect a gross regression. Derive a conservative degradation-adjusted lower bound from the historical production evidence; the frozen threshold remains >=10x.

If the bound cannot be established safely, report the performance check `BLOCKED` for a new bounded comparator rather than launching an unbounded baseline.

### LQ5 — cleanup/report

Write one compact summary plus per-material-check evidence. Preserve a bounded failure capsule/log tail. Remove all run-owned large scratch on PASS, product FAIL, BLOCKED, exceptions, SIGINT, and SIGTERM.

At startup, safely scavenge abandoned prior scratch only when an ownership manifest proves it belongs to this qualifier.

## Material versus advisory results

Acceptance-critical:

- correct production graph/authority binding;
- native forward-only production path;
- exact bounded recovery fallback/prefix-state equivalence;
- representative REPAIR2 no-copy/no-inverse/no-regression behavior;
- large-rung checkpoint compatibility;
- conservative >=10x performance bound;
- production inputs remain unchanged;
- execution is safely admitted and bounded.

Advisory/nonblocking when interpretation remains sound:

- optional CPU/GPU/system telemetry;
- extra benchmark repetitions or larger optional rungs;
- detailed page-cache statistics;
- cosmetic/report metadata;
- optional profiling counters.

An unexpected hard-limit hit caused by the qualification harness is not a product FAIL. Preserve compact evidence, clean scratch, continue independent safe checks when useful, and classify the missing required evidence as harness/resource-model defect or `BLOCKED` as appropriate.

A properly designed representative check that violates a frozen product resource/performance requirement remains a product failure.

## Existing evidence reuse

Focused v2 correctness, adjacent v1 regressions, broad non-slow tests, and wheel/install/import qualification remain reusable while their material code/package surfaces remain unchanged.

The current production-density performance evidence may be reused only under the REV6 LQ4 compatibility rule.

## Implementation handoff

Governing design:

`workplans/active/DOC-MVSEL2_HARDEN1_V3_REV6_LIGHTWEIGHT_AUTONOMOUS_QUALIFICATION.md`

Implementation should proceed through R6-G0 -> R6-G6 automatically unless a genuine material blocker or design contradiction emerges.
