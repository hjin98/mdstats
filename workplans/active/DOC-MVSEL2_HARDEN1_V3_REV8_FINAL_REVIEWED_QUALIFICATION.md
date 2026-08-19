---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 8
status: READY_FOR_IMPLEMENTATION
protocol_version: 3.1.0
supersedes: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV7_FINAL_LIGHTWEIGHT_QUALIFICATION.md
qualification_driver: scripts/mvsel2_bounded_qualification.py
---

# MVSEL2 hardening — final reviewed lightweight qualification

## Objective

Qualify the frozen MVSEL2/MVSTATE2/REPAIR2 hardening candidate with a short, autonomous, machine-adaptive benchmark that is bound to the complete production LTA authority but avoids complete selector/repair replay, production-tree cloning, and full-domain validation scans.

The frozen scientific/persistence semantics and the combined-chain `>=10x` performance floor do not change.

## Final-review corrections incorporated

The final review identified and resolves the remaining material ambiguities from REV6/REV7:

1. the current `_build_repair_from_checkpoints(...)` fresh-state initialization can scan the complete multi-billion-edge graph before a checkpoint replaces that state;
2. a benchmark-only truncated selection object could blur evidence versus product authority;
3. the 16,384 compatibility requirement must not silently degrade to an 8,192 checkpoint when 16,384 is materializable;
4. production database access through a normal writable `CampaignStore` is not a strong enough read-only qualification boundary;
5. repeated child stages would unnecessarily remap the huge MVIDX;
6. cleanup/evidence retention and resource-model recovery needed deterministic all-terminal rules;
7. the historical MVSEL2 production-density benchmark is not sufficiently source-bound to the rescued candidate: it embeds `source.git_head = f23426d426af21a54914f4e62181ce09e864330b`, while the branch history shows the v2 implementation files were committed after that Git head; the release-status record explicitly classifies prior performance records as historical evidence rather than Protocol-v3 acceptance of the rescued candidate;
8. any private runtime refactor needed to share checkpoint-started REPAIR2 execution may create a new product candidate and therefore changes which earlier evidence may be reused.

REV8 freezes the corresponding corrections below.

## Frozen execution architecture

### E1 — production identity is full-scale; execution is bounded

Authenticate in place:

- requested domain, normally `label-domain-5aa1ee5d50cd0b23`;
- 36,408 candidates / 165 families for the current production campaign;
- exact MVIDX1 digest and forward-edge count;
- authenticated MVSEL2 authority and materializable ladder through 16,384;
- required MVSTATE2 checkpoint lineage;
- stable production DB/config identity before and after material execution.

The production graph is authoritative. Full production computation is not automatically required.

### E2 — strict read-only production boundary

Do not construct a writable `CampaignStore` on the production database. Capture records through SQLite `mode=ro` connections/transactions and explicit deserialization. Use `immutable=1` only after proving the DB is quiescent/immutable for the run. Open native arrays/checkpoints read-only.

If production identity changes, classify `EXTERNAL_INPUT_CHANGED`/`BLOCKED`, not product FAIL.

### E3 — one mapped compute worker

Use one parent supervisor plus one serial compute worker for LQ1-LQ4 by default. Open/map the real reference and forward-only MVIDX once and reuse them. Avoid repeated process-stage remapping of the 9.5-billion-edge authority.

The supervisor owns resource discovery, hard containment, state publication, signals, cleanup/scavenging, and bounded retry. The compute worker owns read-only mapping and measurements.

### E4 — resource model

Distinguish effective capacity, hard containment, and a smaller planned operating envelope. Discover affinity, cgroup/job limits, host/cgroup memory availability, filesystem free space/quota information that is safely available, and stricter explicit user caps.

Prefer delegated cgroup-v2 containment when safely available; otherwise use conservative admission plus process-group watchdog containment. Do not default to `RLIMIT_AS` because large file-backed mappings make virtual address space a poor proxy for resident memory.

Monitor aggregate owned-process RSS, physical scratch blocks, wall time, production identity, and host/cgroup pressure where available. Missing secondary telemetry is advisory when a conservative envelope remains possible.

### E5 — short-run envelope

Reference-workstation normal target: approximately 5-8 minutes end-to-end.

Default hard wall containment should be about 15 minutes and must not exceed 20 minutes without explicit user override. Normal planned execution must remain materially below the selected hard boundary.

Scratch is expected in the hundreds of MiB; default hard aggregate scratch cap <=1 GiB. Logs/evidence have their own small byte/count retention limits.

## Candidate boundary and evidence reuse

REV8 distinguishes harness-only work from product-runtime work.

- If implementation changes only `scripts/`, `benchmarks/`, workplans, tests, or qualification evidence and does **not** change packaged/runtime product behavior, the existing frozen product candidate remains applicable; affected harness checks may be rerun without inventing a new product candidate.
- If implementation refactors any packaged `mdstats/` runtime source (for example to factor the exact checkpoint-started REPAIR2 rung helper), freeze a **new Git candidate commit** after that refactor and before final qualification. The Git commit plus a clean/non-shadowed working tree is the default candidate identity under Protocol 3.1; do not recreate redundant candidate-content hashing unless a real external/generated boundary requires it.
- After a product-runtime refactor, rerun the focused v2 correctness tests that exercise the helper/runtime path. Rerun adjacent v1 regressions when the changed import/runtime surface could affect them. Rerun wheel/build/install/import because packaged bytes changed. Broad-suite reruns follow repository policy and attribution: unrelated known failures do not become an artificial zero-failure oracle.
- Previously passed evidence whose material code/package surface is unchanged remains reusable.
- Production MVIDX/reference/config/checkpoint digests remain separate material external-input identities regardless of the Git candidate boundary.

This prevents the qualification-harness redesign from silently qualifying a different runtime candidate under stale evidence.

## Qualification stages

### LQ0 — admission, ownership, cleanup recovery

Before large mapping:

1. establish read-only/stable production inputs;
2. discover effective resources and stricter user caps;
3. create separate evidence and disposable scratch roots;
4. write a scratch ownership manifest with run ID, qualifier identity, production identity, and root identity;
5. safely scavenge abandoned prior scratch only when ownership is proven;
6. derive hard containment and a smaller operating envelope;
7. admit the minimum material plan plus optional work that fits conservatively.

Do not launch work that calibration already predicts will collide with containment.

### LQ1 — production binding and tiny forward probe

Open the real reference and native forward-only MVIDX. Authenticate production counts/digests/edge count and the production ladder through 16,384. Query only a deterministic tiny candidate-incidence sample and verify inverse arrays are not mapped/opened in the v2 boundary.

No complete candidate sweep and no fresh full-problem feasibility/state validation scan are permitted.

### LQ2 — exact 128 -> 256 MVSTATE2 recovery micro-integration

Under the current standard production policy, require valid 128 and 256 checkpoints. Do not silently jump to a larger pair if one is missing.

1. copy only those two checkpoint bundles to owned scratch;
2. restore/authenticate both against the real production reference/forward view;
3. corrupt only the newer scratch record/pointer;
4. require `_highest_valid_resume_states(...)` to fall back to 128;
5. from the restored 128 state, replay only the canonical selected candidates at ranks 128..255 using the exact production score/select mutation primitives;
6. do not run selector search and do not construct a fresh full-domain state;
7. compare reconstructed state to the authenticated 256 checkpoint exactly.

Exact mutable-state comparison includes:

- selected order;
- availability bitmap;
- every family multiplicity array and coverage mass;
- obligation counts;
- unsatisfied-required count;
- correlation-unit counts;
- representative utility.

Focused tests remain authority for full search/rebase/rank-zero-fallback semantic branches not exercised here.

### LQ3 — exact checkpoint-started REPAIR2 micro-benchmark

The qualification path MUST NOT enter the current fresh-state initialization that performs complete production validation before checkpoint replacement.

Factor/reuse one exact private production rung helper that can start from an authenticated checkpoint state. Production full-ladder execution and qualification must share this helper. Qualification passes an evidence-only rung filter; it must not create/persist a truncated fake selection authority.

Do not duplicate `_proposal`, `_better`, mutation, coverage, or obligation logic in benchmark code.

Mandatory measured rungs: 128 and 256.

Record per rung:

- wall time;
- active-shell size;
- proposal evaluations;
- swaps;
- checkpoint restore/replay mode;
- proposal full-state-copy sentinel;
- inverse mapping/mutation sentinel;
- coverage/hard-obligation non-regression;
- aggregate RSS/resource telemetry needed for projection.

Adaptive rule:

- add 512 only if 128/256 do not exercise proposal evaluation, cannot calibrate the repair upper bound, or leave a material runtime assertion unexercised;
- add at most 1024 if still needed and safely admitted;
- never enlarge the benchmark merely to force an accepted swap;
- stop as soon as the material claim is established.

Accepted-swap divergence semantics remain owned by focused tests.

Large-rung sentinel: restore/authenticate the highest materializable production checkpoint <=16,384. For the current ladder, the 16,384 checkpoint itself is mandatory. Do not substitute 8,192 when 16,384 is materializable. No 16,384 REPAIR2 computation is required solely for qualification.

### LQ4 — fresh current-candidate selector projection plus combined-chain bound

Do not use the historical MVSEL2 projection as current-candidate PASS evidence and never run a full MVSEL1 or full 16,384 MVSEL2 replay.

#### Legacy baseline reuse

The historical production evidence provides the legacy MVSEL1 same-host baseline `B_hist = baseline_full_order_seconds`.

Reuse `B_hist` only when:

- current production MVIDX digest/counts match the historical benchmark;
- execution is on the intended original workstation context (`local-user-ProBuild`) or an explicitly accepted same-host equivalent;
- the tracked legacy MVSEL1 comparator surface used by the baseline is unchanged from the historical benchmark source Git head, verified by Git blob/diff identity.

The legacy comparator existed as tracked code at the historical Git head, so this compatibility check is meaningful even though the then-uncommitted v2 implementation is not source-bound by that SHA.

If baseline compatibility fails, the baseline component is `BLOCKED`; do not launch a full legacy replay automatically.

#### Current-candidate Phase A measurement

Start from the authenticated 128 checkpoint so qualification avoids ranks 0..127 and avoids fresh full-state validation.

Run the exact current production Phase-A choice + mutation loop from rank 128 until Phase A completes. For every measured rank require the chosen candidate to equal the authenticated production master order.

Record:

- `phase_a_start = 128`;
- `phase_a_end` (expected about 452 for the current production authority);
- total measured Phase-A wall time from 128 to completion;
- maximum current per-rank `(choose + mutation)` time.

Conservatively upper-bound unmeasured ranks 0..127:

`phase_a_prefix_upper = 128 * max_current_phase_a_rank_seconds`.

No historical MVSEL2 algorithm timing is used for this term.

#### Current-candidate Phase B measurement

From the exact current state at Phase-A completion:

1. build the current exact lazy frontier once with `build_target_multi_view_lazy_frontier_v2(...)` and measure rebase wall time;
2. treat the rebase as a material memory event and do not start it unless admission predicts safe headroom;
3. run exactly 32 current Phase-B choice + mutation ranks (or all remaining ranks if fewer than 32);
4. require every chosen candidate to match the authenticated production master order;
5. record the maximum current sampled Phase-B `(choose + mutation)` rank time.

This recreates the conservative projection method with the **current candidate** while executing only a few hundred production ranks, not the remaining ~15k.

#### Current selector upper bound

Use the historical cold-preflight measurement only as a deliberately inflated setup-cost guard, never as current candidate algorithm timing:

`setup_upper = max(2.0 * current_LQ1_reference_plus_forward_restore_seconds, 4.0 * historical_cold_preflight_total_seconds)`.

Let:

- `A_measured` = current measured Phase-A time from rank 128 to completion;
- `A_prefix` = `phase_a_prefix_upper`;
- `R_current` = current exact frontier rebase seconds;
- `B_rank_max` = maximum current sampled Phase-B rank seconds;
- `N_target = 16384`;
- `N_phase_a = phase_a_end`.

Then:

`selector_upper = 1.25 * (setup_upper + A_prefix + A_measured + R_current + max(0, N_target - N_phase_a) * B_rank_max)`.

The outer 1.25 is the frozen qualification timing margin. All selector hot-path timing terms are current-candidate measurements; the historical setup number is multiplied by 4 solely to avoid undercharging unmeasured fresh-state setup.

#### REPAIR2 upper bound

Use LQ3 telemetry:

- `work_i = shell_size_i + proposals_i * candidate_count`;
- `unit_seconds = max_i(rung_wall_seconds_i / max(1, work_i))`;
- `P_cap = removal_shortlist_limit * (max_swaps_per_shell + max_passes_per_shell)`;
- `work_upper_r = shell_size_r + P_cap * candidate_count` for each materializable production rung through 16,384;
- `repair_upper = 4.0 * unit_seconds * sum(work_upper_r)`.

The factor 4 is a frozen safety margin for incidence/cache variation and the proposal cap intentionally over-bounds current proposal rounds.

If no measured rung executes any proposal, add the allowed next rung. If proposal cost still cannot be measured within the bounded plan, the repair-performance component is `BLOCKED`; do not guess.

#### Combined floor

`combined_speedup_lower = B_hist / (selector_upper + repair_upper)`.

PASS requires `combined_speedup_lower >= 10.0`.

The old historical MVSEL2 `~69x` projection may be reported only as an advisory diagnostic cross-check. It is not an acceptance input for the rescued candidate.

If the current bounded projection executes successfully but fails the frozen 10x floor, return a product/performance failure to implementation. If required baseline/rebase evidence cannot be established safely, report `BLOCKED` for a new bounded comparator. Never lower the threshold and never fall back to an unbounded replay.

### LQ5 — all-terminal cleanup and compact evidence

Use a structure equivalent to:

```text
qualification/bounded-mvsel2/
  evidence/<run-id>/...
  scratch/<run-id>/OWNER.json
  scratch/<run-id>/...
  state.json
  summary.json
```

On PASS, product FAIL, BLOCKED, harness exception, SIGINT, and SIGTERM:

1. retain/flush a compact diagnostic capsule;
2. terminate owned descendants;
3. close DB/mmap handles;
4. remove all owned large scratch in supervisor/finally cleanup;
5. atomically publish terminal state/summary.

Startup scavenging handles uncatchable prior termination only when ownership is proven. Evidence/log retention itself must be bounded. Large checkpoint bundles and temporary SQLite files are never final evidence.

## Automatic resource-model recovery

A hard-limit event is exceptional containment.

If it occurs during optional work, the supervisor may make one fresh-worker retry after cleaning prior scratch and removing optional larger rungs/repetitions. Never raise limits automatically.

If it occurs during minimum LQ1/LQ2/128+256 LQ3 or during the required current Phase-B rebase after admission incorrectly predicted safety, classify the missing evidence as a harness/resource-model `BLOCKED` condition, not product FAIL. Do not repeatedly collide with the ceiling.

A properly designed current measurement that exceeds a frozen product resource/performance requirement remains a product failure.

## Material versus advisory

Acceptance-critical:

- stable read-only full production identity;
- native forward-only path;
- exact 128->256 recovery-state equivalence;
- exact shared REPAIR2 path on mandatory measured rungs;
- zero proposal full-state clones/no inverse mapping or mutation/no regression;
- valid 16,384 checkpoint sentinel;
- compatible legacy same-host baseline;
- fresh current-candidate Phase-A-from-128 + exact rebase + 32 Phase-B projection;
- conservative current selector + repair combined `>=10x` lower bound;
- safely admitted/contained execution and production non-mutation;
- correct candidate/evidence invalidation if packaged runtime code changes during R8 implementation.

Advisory/nonblocking when material interpretation remains sound:

- historical MVSEL2 ~69x projection;
- optional GPU/page-cache/profiler telemetry;
- optional 512/1024 repair rungs once required evidence is sufficient;
- cosmetic report metadata.

Do not let advisory evidence defects disqualify valid material results.

## Expected implementation change surface

- `scripts/mvsel2_bounded_qualification.py` — supervisor/worker redesign, read-only capture, resource discovery/admission, aggregate monitoring, current selector projection, repair bound, cleanup/scavenging.
- `mdstats/training_data/mvsel2_hardening_runtime.py` and/or `target_multi_view_repair_v2.py` — small private refactor only if necessary to share exact checkpoint-started repair rung execution without fresh full-domain validation.
- production repair benchmark wrapper — bounded selected-rung mode with no duplicated repair science.
- focused tests for read-only DB handling, resource admission/monitoring, exact recovery-state equality, repair helper equivalence, proposal-bound arithmetic, current selector projection arithmetic, legacy baseline compatibility, candidate invalidation, cleanup/scavenging, retry/failure classification.
- qualification run card/evidence schema.

No public/scientific algorithm change is intended.

## Gates

| Gate | Status | Purpose |
|---|---|---|
| R8-G0 | PENDING | Freeze read-only authority capture, legacy-baseline compatibility surface, candidate invalidation, resource model, and projection arithmetic. |
| R8-G1 | PENDING | Implement one-worker supervisor, aggregate containment, ownership, cleanup/scavenging, bounded evidence retention. |
| R8-G2 | PENDING | Implement LQ1/LQ2 without full-domain validation scan and exact state-equivalence tests. |
| R8-G3 | PENDING | Factor checkpoint-started REPAIR2 helper if needed; implement 128/256[/512/1024] benchmark and mandatory 16,384 sentinel. |
| R8-G4 | PENDING | Implement fresh current Phase-A-from-128 + exact rebase + 32 Phase-B projection and combined selector+repair >=10x bound. |
| R8-G5 | PENDING | Freeze the resulting candidate boundary; rerun affected focused/package checks; run harness/cleanup/failure tests and one-command small-fixture dry qualification. |
| R8-G6 | PENDING | Autonomous workstation qualification and compact evidence handoff to verification. |

## Design-revision triggers

Return to design only if implementation requires changing frozen selector/repair semantics, checkpoint identity/compatibility, MVIDX1 scientific content/schema, REPAIR1/REPAIR2 equivalence, or the combined `>=10x` threshold.

Equivalent resource-discovery/containment mechanics, evidence paths, optional telemetry, and bounded adaptive sizing inside this design do not require another revision.
