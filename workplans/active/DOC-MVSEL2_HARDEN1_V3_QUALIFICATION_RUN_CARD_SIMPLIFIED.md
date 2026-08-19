---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-REV7-LIGHTWEIGHT
protocol_version: 3.1.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 7
status: DESIGN_READY_FOR_IMPLEMENTATION
---

# MVSEL2 hardening — final lightweight autonomous workstation qualification

## Governing design

`workplans/active/DOC-MVSEL2_HARDEN1_V3_REV7_FINAL_LIGHTWEIGHT_QUALIFICATION.md`

REV5/REV6 execution designs are superseded. The workstation check is a short qualification benchmark bound to the complete production authority, not a production replay.

## Intended one-command interface

After R7-G1 through R7-G5 are implemented, ordinary workstation execution should require only material inputs:

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

The script owns resource discovery, machine-adaptive admission, one supervised compute worker, benchmark sizing, compact state/evidence, cleanup/scavenging, and final summary. Codex/ChatGPT does not need to remain connected.

Explicit resource/time options may remain as stricter user caps. They must not be required for normal execution and must never silently raise discovered safe limits.

## Expected execution envelope

Reference-workstation target:

- normal wall time: approximately 5-8 minutes;
- default hard wall containment: approximately 15 minutes; never above 20 minutes without explicit user override;
- scratch: normally hundreds of MiB, hard aggregate scratch cap <=1 GiB;
- serial/single compute worker unless a material production path requires otherwise;
- normal planned workload materially below hard containment.

Hard-limit activation is exceptional containment, not ordinary benchmark control flow.

## Production safety boundary

The qualifier must:

- authenticate the full 36,408-candidate / 165-family production graph and exact MVIDX1 digest/edge count;
- keep production DB/config/native state read-only;
- avoid constructing a writable `CampaignStore` on the production DB;
- use read-only SQLite capture and explicit deserialization;
- verify production identity remains stable across material execution;
- never copy/mirror the complete `.mdstats` tree;
- map the production reference/MVIDX once in the normal compute worker and reuse it across material checks.

If production identity changes during the run, report `EXTERNAL_INPUT_CHANGED`/`BLOCKED`; do not classify the candidate as failed.

## Automatic stages

### LQ0 — admission and ownership

Discover effective CPU/memory/storage/cgroup/job constraints, apply stricter user caps, derive hard containment and a smaller operating envelope, create separate evidence/scratch roots with an ownership manifest, and safely scavenge only abandoned scratch proven to belong to this qualifier.

Prefer delegated cgroup-v2 memory containment when safely available; otherwise use conservative admission plus process-group watchdog containment. Monitor aggregate owned-process RSS and host/cgroup pressure where available.

### LQ1 — production binding

Open the real reference and native forward-only MVIDX. Authenticate production counts/digests/edge count and the materializable ladder through 16,384. Query only a tiny deterministic forward-incidence sample and prove the v2 boundary does not open/map inverse arrays.

No full candidate sweep or fresh full-problem feasibility validation is allowed.

### LQ2 — recovery micro-integration

Use the real 128 -> 256 production MVSTATE2 checkpoint pair under the current standard policy.

Copy only those two checkpoint bundles to scratch. Restore both, corrupt only the newer scratch record, require runtime fallback to 128, and replay only canonical selected candidates 128..255 using the exact production score/select mutation primitives.

Do not run selector search and do not rebuild a fresh production forward state.

Compare reconstructed versus authenticated 256 state exactly for:

- selected order;
- availability bitmap;
- every family multiplicity array and coverage mass;
- obligation counts and unsatisfied-required count;
- correlation-unit counts;
- representative utility.

### LQ3 — REPAIR2 micro-benchmark

The benchmark must share the exact production REPAIR2 rung implementation and start from authenticated checkpoint state. It must not enter the current fresh-state path that performs a complete production validation scan.

Mandatory measured rungs: 128 and 256.

Add 512 only when proposal/timing/material evidence is insufficient; add at most 1024 if still needed and safely admitted. Do not escalate merely to force an accepted swap.

Measured-rung requirements:

- default REPAIR2 policy;
- exact shared production repair logic;
- zero proposal full-state clones;
- no inverse mapping/mutation;
- no coverage/hard-obligation regression;
- correct checkpoint restore/replay mode;
- wall/proposal/shell/resource telemetry needed for the bounded performance projection.

Separately restore/authenticate the highest materializable production checkpoint <=16,384. For the current ladder that means the **16,384 checkpoint itself is mandatory**. Do not substitute 8,192 when 16,384 is materializable. This is a read-only sentinel; no 16,384 repair computation is required solely for qualification.

### LQ4 — deterministic performance sentinel and combined-chain floor

Never run a fresh full MVSEL1 production replay.

Authenticate `benchmarks/mlff_mvsel2_production_density_2026-08-18.json` against the current MVIDX1 graph.

Restore the 128 checkpoint and execute exact Phase-A choice+mutation for ranks 128..135. Every chosen candidate must match the authenticated production master order. Compare current summed `(choose + mutation)` time with the historical exact same-rank sum.

Define:

```text
selector_slowdown = max(1, current_sum / historical_sum)
selector_upper = historical_mvsel2_full_order_seconds * selector_slowdown * 1.25
```

If decision noise matters, extend the same deterministic sample up to 32 ranks; do not cherry-pick ranks.

Include REPAIR2 in the combined chain. From LQ3:

```text
work_i = shell_size_i + proposals_i * candidate_count
unit_seconds = max(rung_wall_seconds_i / max(1, work_i))
P_cap = removal_shortlist_limit * (max_swaps_per_shell + max_passes_per_shell)
work_upper_r = shell_size_r + P_cap * candidate_count
repair_upper = 4.0 * unit_seconds * sum(work_upper_r over production rungs <=16384)
combined_speedup_lower = historical_baseline_full_order_seconds / (selector_upper + repair_upper)
```

The factor 4 is the frozen qualification safety margin for incidence/cache variation. If no bounded measured rung evaluates any repair proposal, add the allowed next rung; if proposal cost still cannot be measured safely, the repair-performance component is `BLOCKED`, not guessed.

PASS requires `combined_speedup_lower >= 10.0`.

If the conservative lower bound cannot be established inside the bounded plan, return `BLOCKED`/`RETURN_TO_IMPLEMENTATION` for a new bounded comparator. Never lower the threshold or fall back to an unbounded V1 replay.

### LQ5 — cleanup and compact evidence

Use separate compact evidence and disposable scratch, e.g.:

```text
qualification/bounded-mvsel2/
  evidence/<run-id>/...
  scratch/<run-id>/OWNER.json
  scratch/<run-id>/...
  state.json
  summary.json
```

On PASS, product FAIL, BLOCKED, harness exception, SIGINT, and SIGTERM, retain a compact diagnostic capsule, terminate owned children, close mappings/DB handles, and remove all owned large transient scratch before atomically publishing terminal state.

Startup scavenging may delete abandoned scratch only when the ownership manifest proves it belongs to this qualifier. Evidence/log retention must itself be byte/count bounded.

## Automatic resource-model recovery

If containment unexpectedly activates during optional work, the supervisor may make one fresh-worker retry after cleaning prior scratch and removing optional repetitions/larger rungs. **Do not increase limits.**

If containment activates during the minimum LQ1/LQ2/128+256 LQ3 path, or the reduced retry still cannot execute safely, classify the missing evidence as `BLOCKED`/harness-resource-model issue rather than product FAIL.

A properly designed representative product measurement that violates a frozen resource/performance requirement remains a product failure.

## Material versus advisory

Acceptance-critical:

- stable full production identity/read-only authority;
- native forward-only path;
- exact 128->256 recovery-state equivalence;
- exact shared REPAIR2 path on mandatory measured rungs;
- zero full-state proposal clones/no inverse mapping or mutation/no regression;
- valid 16,384 checkpoint sentinel;
- conservative combined-chain >=10x lower bound;
- safely admitted/contained execution and production non-mutation.

Advisory/nonblocking when safety and interpretation remain adequate:

- optional GPU/page-cache/system telemetry;
- optional 512/1024 repair rungs once evidence is sufficient;
- extra timing repetitions beyond the decision rule;
- profiler counters and cosmetic metadata.

Do not disqualify valid material evidence for an advisory defect.

## Implementation handoff

Implementation should proceed automatically through R7-G0 -> R7-G6 unless a genuine material blocker or frozen-design contradiction emerges. Safe harness corrections, resource discovery details, evidence paths, and optional telemetry do not require another design revision.
