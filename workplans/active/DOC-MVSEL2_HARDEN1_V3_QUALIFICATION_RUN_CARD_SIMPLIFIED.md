---
kind: qualification-handoff
handoff_id: DOC-MVSEL2-HARDEN1-V3-REV8-LIGHTWEIGHT
protocol_version: 3.1.0
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 8
status: DESIGN_READY_FOR_IMPLEMENTATION
---

# MVSEL2 hardening — final reviewed lightweight workstation qualification

## Governing design

`workplans/active/DOC-MVSEL2_HARDEN1_V3_REV8_FINAL_REVIEWED_QUALIFICATION.md`

REV5-REV7 execution designs are superseded. Qualification is a short current-candidate benchmark bound to the complete production graph, not a production replay.

## Candidate boundary before execution

R8 implementation may change qualification-only code or may require a small packaged-runtime refactor to share exact checkpoint-started REPAIR2 rung execution.

- If only `scripts/`, `benchmarks/`, workplans, tests, or qualification/evidence code changes and packaged `mdstats/` runtime behavior is unchanged, the existing frozen product candidate remains applicable; rerun only materially affected harness checks.
- If any packaged `mdstats/` runtime source changes, freeze a **new Git candidate commit** after the refactor and before final workstation qualification. Use that Git commit plus a clean/non-shadowed working tree as the default candidate identity.
- After a packaged-runtime change, rerun affected focused v2 tests, adjacent v1 regressions when the changed runtime/import surface can affect them, and wheel/build/install/import because packaged bytes changed. Broad-suite reruns follow repository policy and attribution rather than an artificial universal zero-failure requirement.
- Previously executed evidence remains reusable when its material code/package surface did not change.
- Production MVIDX/reference/config/checkpoint digests remain separate material external-input identities.

Do not qualify a runtime-refactored candidate under stale evidence from the earlier candidate.

## Intended one-command interface

After R8-G1 through R8-G5 are implemented:

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

The script owns resource discovery/admission, one supervised compute worker, benchmark sizing, compact evidence/state, cleanup/scavenging, and final summary. No Codex/ChatGPT session is required after launch.

Explicit resource/time flags may only tighten discovered limits.

## Expected envelope

- normal end-to-end target on `local-user-ProBuild`: about 5-8 minutes;
- default hard total containment: about 15 minutes, never >20 minutes without explicit override;
- scratch: normally hundreds of MiB, hard aggregate cap <=1 GiB;
- one serial mapped compute worker by default;
- normal planned work materially below hard containment.

Containment activation is exceptional, not ordinary flow.

## Production safety

- production DB/config/native arrays are read-only;
- do not construct writable `CampaignStore` on production DB;
- read records using SQLite `mode=ro` and explicit deserialization;
- use `immutable=1` only after proving quiescence;
- map the native forward-only MVIDX once and reuse it;
- never copy/mirror complete `.mdstats`;
- verify production identity remains stable;
- production identity change => `EXTERNAL_INPUT_CHANGED`/`BLOCKED`, not product FAIL.

## Automatic stages

### LQ0 — admission/ownership

Discover effective affinity/cgroup/job/memory/storage limits and stricter user caps. Create separate evidence/scratch roots with an ownership manifest and safely scavenge only abandoned scratch proven to belong to this qualifier.

Prefer delegated cgroup-v2 containment when available; otherwise use conservative admission plus process-group watchdog. Monitor aggregate owned RSS, scratch blocks, wall time, and host/cgroup pressure where available.

### LQ1 — production binding

Authenticate the real 36,408-candidate / 165-family graph, MVIDX1 digest/edge count, MVSEL2 ladder through 16,384, and native forward-only path. Query only a tiny deterministic incidence sample.

No full candidate sweep and no fresh full-domain feasibility/state validation scan.

### LQ2 — exact 128 -> 256 recovery

Require real valid 128 and 256 MVSTATE2 checkpoints.

Copy only those two bundles to scratch; restore both; corrupt only the 256 scratch record; require fallback to 128; replay canonical candidates 128..255 using exact production score/select mutations; compare reconstructed state exactly with authenticated 256 state.

Compare selected order, availability, all family multiplicities/coverage masses, obligation counts, unsatisfied-required count, correlation-unit counts, and representative utility.

Do not run selector search or rebuild a fresh production state.

### LQ3 — REPAIR2 micro-benchmark

Share the exact production checkpoint-started rung helper; do not duplicate repair science and do not enter the current fresh-state full-validation path.

Mandatory measured rungs: 128 and 256. Add 512 only if proposal/timing/material evidence is insufficient; add at most 1024 if still needed and safely admitted. Never enlarge merely to force a swap.

Require default policy, zero proposal full-state clones, no inverse mapping/mutation, no coverage/hard-obligation regression, and correct checkpoint restore/replay mode.

The highest materializable checkpoint <=16,384 must restore. For the current ladder the **16,384 checkpoint itself is mandatory**. This is a read-only sentinel; no 16,384 repair run is required.

### LQ4 — fresh current-candidate performance projection

The old `~69x` MVSEL2 projection is historical diagnostic evidence only; it is not current-candidate PASS evidence.

Reuse only the legacy MVSEL1 full-order baseline from historical production evidence, and only if:

- current MVIDX identity matches;
- current host is the original `local-user-ProBuild` context (or explicitly accepted same-host equivalent);
- the tracked legacy MVSEL1 comparator surface is unchanged from the historical benchmark source Git head.

Otherwise baseline evidence is `BLOCKED`; do not run full MVSEL1 automatically.

For current MVSEL2:

1. restore the real 128 checkpoint;
2. run exact current Phase-A choice+mutation from rank 128 until Phase A completes, requiring every chosen candidate to match production master order;
3. measure total Phase-A time and maximum measured Phase-A rank time;
4. conservatively bound unmeasured ranks 0..127 as `128 * max_phase_a_rank_seconds`;
5. from current Phase-A completion state, perform exactly one current lazy-frontier exact rebase;
6. only start the rebase if resource admission predicts safe headroom;
7. run exactly 32 current Phase-B choice+mutation ranks, requiring production-order identity;
8. use the maximum current Phase-B sampled rank time to project remaining ranks to 16,384.

Selector bound:

```text
setup_upper = max(
    2.0 * current_reference_plus_forward_restore_seconds,
    4.0 * historical_cold_preflight_total_seconds
)
phase_a_prefix_upper = 128 * max_current_phase_a_rank_seconds
selector_upper = 1.25 * (
    setup_upper
    + phase_a_prefix_upper
    + current_phase_a_128_to_completion_seconds
    + current_exact_rebase_seconds
    + (16384 - phase_a_end) * max_current_phase_b_rank_seconds
)
```

The historical cold-preflight value is used only as a deliberately inflated setup-cost guard; all selector hot-path timing terms are current-candidate measurements.

REPAIR2 bound from LQ3:

```text
work_i = shell_size_i + proposals_i * candidate_count
unit_seconds = max(rung_wall_seconds_i / max(1, work_i))
P_cap = removal_shortlist_limit * (max_swaps_per_shell + max_passes_per_shell)
work_upper_r = shell_size_r + P_cap * candidate_count
repair_upper = 4.0 * unit_seconds * sum(work_upper_r over rungs <=16384)
combined_speedup_lower = historical_mvsel1_baseline_seconds / (selector_upper + repair_upper)
```

If no measured repair rung evaluates proposals, add the allowed next rung; if proposal cost remains unmeasurable inside the bounded plan, mark performance `BLOCKED` rather than guessing.

PASS requires `combined_speedup_lower >= 10.0`.

If the bounded current-candidate projection executes successfully but falls below 10x, return product/performance failure to implementation. If required legacy-baseline compatibility or safe rebase evidence cannot be established, return `BLOCKED` for a new bounded comparator.

Never lower the threshold or fall back to a full MVSEL1/MVSEL2 replay.

### LQ5 — cleanup/report

Use separate compact evidence and disposable scratch:

```text
qualification/bounded-mvsel2/
  evidence/<run-id>/...
  scratch/<run-id>/OWNER.json
  scratch/<run-id>/...
  state.json
  summary.json
```

On PASS, product FAIL, BLOCKED, exception, SIGINT, or SIGTERM: retain a compact diagnostic capsule, terminate descendants, close DB/mmap handles, delete all owned large scratch, then atomically publish terminal state.

Startup scavenging handles uncatchable prior termination only when ownership is proven. Evidence/log retention is byte/count bounded.

## Resource-model recovery

If containment activates during optional work, one automatic fresh-worker retry is allowed after cleaning prior scratch and removing optional work. Do not increase limits.

If minimum LQ1/LQ2/128+256 LQ3 or the required admitted Phase-B rebase cannot execute safely, classify missing evidence as `BLOCKED`/harness-resource-model issue, not product FAIL. Do not repeatedly hit the ceiling.

A properly designed current measurement that violates a frozen product resource/performance threshold remains a product failure.

## Material versus advisory

Acceptance-critical:

- full stable read-only production identity;
- native forward-only path;
- exact 128->256 recovery-state equivalence;
- shared exact REPAIR2 path on mandatory measured rungs;
- zero full-state proposal clones/no inverse mapping or mutation/no regression;
- valid 16,384 checkpoint sentinel;
- compatible legacy same-host baseline;
- fresh current Phase-A-from-128 + exact rebase + 32 Phase-B projection;
- conservative current selector+repair combined >=10x lower bound;
- safe admission/containment and production non-mutation;
- correct candidate/evidence invalidation if packaged runtime code changes during R8 implementation.

Advisory/nonblocking:

- historical MVSEL2 ~69x projection;
- GPU/page-cache/profiler telemetry;
- optional 512/1024 repair rungs once evidence is sufficient;
- cosmetic metadata.

## Implementation handoff

Proceed R8-G0 -> R8-G6 automatically unless a genuine material blocker or frozen-design contradiction emerges. Equivalent safe containment mechanics, evidence paths, and optional telemetry do not require another design revision.
