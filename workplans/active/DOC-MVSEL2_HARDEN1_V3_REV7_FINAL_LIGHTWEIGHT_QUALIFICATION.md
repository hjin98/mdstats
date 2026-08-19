---
kind: implementation-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 7
status: READY_FOR_IMPLEMENTATION
protocol_version: 3.1.0
supersedes: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV6_LIGHTWEIGHT_AUTONOMOUS_QUALIFICATION.md
qualification_driver: scripts/mvsel2_bounded_qualification.py
---

# MVSEL2 hardening — final lightweight autonomous qualification

## Objective

Qualify the frozen MVSEL2/MVSTATE2/REPAIR2 hardening candidate with a short, autonomous, machine-adaptive benchmark that is cryptographically and structurally bound to the complete production LTA authority while executing only the smallest materially sufficient production-state work.

This revision changes qualification conditions and harness architecture only. MVSEL2/REPAIR2 scientific semantics, persisted identity, MVIDX1 scientific content/schema, REPAIR1/REPAIR2 equivalence, and the frozen combined-chain `>=10x` performance floor remain unchanged.

## Final-review findings resolved by this revision

REV6 had the correct philosophy but left several implementation choices too open:

1. the current `_build_repair_from_checkpoints(...)` allocates/validates a fresh production forward state before using checkpoints, which can scan the full multi-billion-edge forward graph and defeat a lightweight benchmark;
2. the performance sentinel did not freeze an exact same-rank comparison or explicitly include REPAIR2 in the combined-chain `>=10x` bound;
3. the large-rung compatibility sentinel allowed the largest *available* checkpoint below 16,384, which could silently weaken a materializable 16,384-rung requirement;
4. constructing a truncated fake selection authority for benchmarking could blur evidence versus product authority;
5. production SQLite access through `CampaignStore` is not a strong enough read-only boundary for a qualification harness;
6. repeated child stages can remap the same huge MVIDX and consume unnecessary time/page cache;
7. cleanup/evidence retention and automatic recovery after a harness limit incident needed deterministic rules.

REV7 freezes these details.

## Frozen material design

### F1 — full production identity, sampled execution

The qualifier MUST authenticate in place:

- the requested label domain (default production domain `label-domain-5aa1ee5d50cd0b23`);
- 36,408 candidates and 165 families for the current production campaign;
- the exact MVIDX1 content digest and forward-edge count;
- the authenticated MVSEL2 selection authority and materializable ladder through 16,384;
- MVSTATE2 checkpoint lineage for the standard materializable rungs;
- production DB/config identity before and after material execution.

The complete graph remains the authority. No complete selector/repair replay is required merely because the authority is full-scale.

### F2 — strict read-only production boundary

Qualification MUST NOT construct a writable `CampaignStore` on the production database.

Production records are captured through SQLite read-only connections/transactions and deserialized explicitly. Use `mode=ro`; use SQLite `immutable=1` only when the implementation has first established that the database is quiescent and immutable for the run. External native arrays/checkpoints are opened read-only.

The driver MUST establish that the production authority is stable/quiescent enough for qualification. If material DB/config/pointer identity changes during execution, report `EXTERNAL_INPUT_CHANGED`/`BLOCKED`, not product FAIL.

### F3 — one mapped compute worker

Normal execution SHOULD use one parent supervisor plus one serial compute worker for LQ1-LQ4 so the real reference/MVIDX forward view is opened once and reused. Do not remap the 9.5-billion-edge authority once per benchmark stage merely for process separation.

The supervisor owns resource discovery, containment, state/evidence publication, signals, cleanup, and optional restart. The compute worker owns read-only production mapping and bounded measurements. Additional descendants are allowed only when a material code path requires them.

### F4 — machine-adaptive resource model

Distinguish:

1. effective job/machine capacity;
2. hard containment ceilings;
3. a materially smaller planned operating envelope.

Discover affinity, cgroup/job limits when available, host/cgroup memory availability, filesystem free space/quota information that is safely discoverable, and explicit user caps. Explicit CLI caps may only tighten the discovered envelope.

Prefer kernel cgroup-v2 containment for the worker when a writable delegated cgroup is safely available. Otherwise use conservative admission plus process-group watchdog containment. Do not use `RLIMIT_AS` as the default because the native file-backed MVIDX has a very large virtual mapping that is not equivalent to resident memory.

Monitor aggregate owned-process RSS (not only one PID), run-owned physical scratch blocks, wall time, and host/cgroup memory pressure where available. Sum-of-descendant RSS may conservatively overcount shared pages; because normal execution is one compute worker, this is acceptable. Missing secondary telemetry is advisory if a conservative envelope remains possible.

### F5 — short benchmark envelope

Reference-workstation design target: approximately 5-8 minutes end-to-end. Normal planned work MUST remain materially below the chosen hard wall boundary.

The default hard total boundary SHOULD be approximately 15 minutes. The implementation may derive a tighter or modestly larger machine/job-specific boundary from available job time and bounded calibration, but MUST NOT exceed 20 minutes without an explicit user override. This is a qualification containment policy, not a product performance threshold.

Expected scratch is hundreds of MiB. The default hard aggregate scratch cap MUST be no larger than 1 GiB; the admitted planned scratch footprint should be substantially below it.

## Acceptance-critical qualification stages

### LQ0 — admission, ownership, and startup scavenging

Before mapping large production state:

1. validate production paths and establish read-only/stable-input conditions;
2. discover effective CPU/memory/storage/job limits and explicit user caps;
3. create separate compact evidence and disposable scratch areas;
4. write an ownership manifest containing a schema, run ID, qualifier identity, production identity, and scratch-root identity;
5. safely scavenge only abandoned scratch with a valid matching ownership manifest under the expected scratch parent;
6. derive hard containment and a smaller operating envelope;
7. admit only the minimum material plan plus optional work that conservatively fits.

Evidence retention MUST be bounded. Keep the current compact run plus at most a small fixed number/size of prior compact run capsules; never retain checkpoint bundles as historical evidence.

### LQ1 — full production binding, tiny forward probe

Open the real target reference and native forward-only MVIDX once. Authenticate candidate/family/edge/digest identity and the production selection ladder through 16,384.

Verify inverse arrays are not opened/mapped inside the v2 boundary and query a deterministic small sample of forward candidate incidence. No complete candidate sweep and no full forward-state feasibility validation are permitted in this stage.

### LQ2 — exact MVSTATE2 recovery micro-integration

Use the smallest adjacent standard compatible production checkpoint pair, normally 128 -> 256. A valid 128 and 256 pair is expected for the current production policy; if a required checkpoint is missing/corrupt, report missing material evidence rather than silently moving to a much larger expensive pair.

Procedure:

1. copy only the two checkpoint bundles into run-owned scratch;
2. restore/authenticate both checkpoints against the real production reference/forward view;
3. corrupt only the newer scratch record/pointer;
4. require `_highest_valid_resume_states(...)` to choose the older compatible checkpoint;
5. starting from that restored state, replay only the canonical selected candidates in the older->newer delta with the exact production `score_target_multi_view_candidate_v2(...)` / `select_target_multi_view_candidate_v2(...)` mutation primitives; do not run selector search and do not call a fresh full-problem state validator;
6. compare the reconstructed state with the authenticated newer checkpoint.

Required state equivalence is explicit:

- `selected_order` exact;
- `available` exact boolean array;
- each family `multiplicity` exact and `coverage_mass` exact;
- `obligation_counts` exact;
- `unsatisfied_required_obligation_count` exact;
- `correlation_unit_counts` exact;
- `representative_utility` exact.

Static family weights/identities are authenticated separately and need not be duplicated as mutable-state evidence.

Focused tests remain the authority for full selector-search, Phase-B rebase, corrupt-newest-to-rank-zero fallback, and other semantic branches not materially exercised by this one-shell production integration.

### LQ3 — exact REPAIR2 production micro-benchmark without full validation scan

The lightweight benchmark MUST NOT call the current full-domain initialization path that scans the complete graph merely to obtain a state that is immediately replaced by a checkpoint.

Implementation MUST factor/reuse the exact production rung execution so both production and benchmark call the same repair science. Acceptable implementation shape:

- factor a private shared domain/rung helper that accepts an already-authenticated restored state, canonical production order, prior size/divergence state, and an explicit evidence-only rung filter;
- production `_build_repair_from_checkpoints(...)` uses the same helper for the full ladder;
- qualification uses the helper on selected measured rungs.

Do not duplicate `_proposal`, `_better`, mutation, coverage, or obligation logic in the benchmark. Do not construct/persist a modified selection object that masquerades as product authority. The full authenticated production selection plan remains the identity; a benchmark rung filter is evidence-only execution metadata.

Mandatory measured rungs are 128 and 256 under the current standard policy. For each measured rung record wall time, active-shell size, proposal evaluations, swaps, restore/replay mode, zero full-state-copy sentinel, inverse mapping/mutation sentinel, aggregate RSS, and coverage/obligation non-regression.

Adaptive stopping rule:

- 128 and 256 are mandatory;
- add 512 only if the mandatory pair did not exercise any proposal evaluation, did not provide enough timing/work information for the repair upper bound, or left a material assertion unexercised;
- add at most 1024 only if 512 is still insufficient and admission predicts comfortable completion;
- never add a larger rung merely to force an accepted swap; accepted-repair-divergence semantics are owned by focused tests;
- stop as soon as the material production-path/resource claim is established.

Large-rung compatibility sentinel: restore/authenticate the checkpoint for the **highest materializable production rung at or below 16,384**. For the current production ladder this is 16,384 and therefore the 16,384 checkpoint itself is required. Do not silently substitute 8,192 when 16,384 is materializable. The sentinel is read-only; no 16,384 REPAIR2 execution is required solely for qualification.

### LQ4 — deterministic current selector sentinel and combined-chain >=10x bound

A fresh full MVSEL1 replay is forbidden.

Authenticate `benchmarks/mlff_mvsel2_production_density_2026-08-18.json` against the current production MVIDX1 graph. Its accepted same-graph evidence records:

- baseline full-order projection `B_hist`;
- MVSEL2 full-order projection `S_hist`;
- historical per-rank Phase-A rows;
- projected speedup `B_hist / S_hist` (currently about 69x).

Current-candidate timing sentinel:

1. restore the authenticated 128 MVSTATE2 checkpoint;
2. run exact Phase-A choice + mutation for deterministic ranks 128..135 (8 ranks) using serial production settings and the real forward view;
3. require each chosen candidate to equal the authenticated production master order at that rank;
4. compare the sum of current `(choose + mutation)` wall time with the historical sum for the exact same ranks;
5. define `selector_slowdown = max(1, current_sum / historical_sum)` and apply a fixed 1.25 timing-safety multiplier;
6. define `selector_upper = S_hist * selector_slowdown * 1.25`.

If timing noise or a near-threshold result prevents a stable decision, automatically extend the same-rank sample to at most 32 ranks while the operating envelope permits. Do not change ranks opportunistically to obtain a better result.

REPAIR2 must be included in the frozen combined-chain floor. Define a conservative bounded repair projection from LQ3 telemetry:

- for measured rung `i`, `work_i = shell_size_i + proposals_i * candidate_count`;
- let `unit_seconds = max_i(rung_wall_seconds_i / max(1, work_i))`;
- use the conservative policy proposal cap `P_cap = removal_shortlist_limit * (max_swaps_per_shell + max_passes_per_shell)`;
- for every materializable production rung through 16,384, define `work_upper_r = shell_size_r + P_cap * candidate_count`;
- define `repair_upper = 4.0 * unit_seconds * sum(work_upper_r)`.

The factor 4 is a frozen qualification safety margin for incidence/cache variation. The proposal cap deliberately over-bounds the current loop's proposal rounds. If measured rungs contain zero proposal evaluations, add the allowed next rung before using this projection; if no bounded measured rung exercises proposals, the repair-performance component is `BLOCKED` rather than guessed.

Combined conservative speedup lower bound:

`combined_speedup_lower = B_hist / (selector_upper + repair_upper)`.

PASS requires `combined_speedup_lower >= 10.0`.

If the lower bound does not clear 10x, the harness may automatically collect the next already-allowed bounded sample/rung to reduce uncertainty. If it still cannot establish the bound safely, return performance evidence as `BLOCKED`/`RETURN_TO_IMPLEMENTATION` for a new bounded comparator. Never fall back to a full MVSEL1 replay and never lower the 10x threshold.

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

Only the scratch subtree counts toward scratch retention and is disposable. Logs/evidence are independently byte-bounded.

On PASS, product FAIL, BLOCKED, harness exception, SIGINT, and SIGTERM:

1. write/flush a compact diagnostic capsule sufficient to interpret the result;
2. terminate owned descendants;
3. close mapped files/DB handles;
4. remove all owned large transient scratch in `finally`/supervisor cleanup;
5. atomically publish final stage/summary state.

Startup scavenging covers uncatchable prior termination only when ownership is proven. Never delete based only on filename or age.

## Automatic recovery from a harness resource-model incident

A hard-limit hit is exceptional. Do not use watchdog kills as normal adaptation.

If containment activates during optional work, the supervisor MAY make one automatic fresh-worker retry with optional repetitions/larger rungs removed and no limit increase. Preserve the first compact failure capsule and clean its scratch first.

If containment activates during the minimum material LQ1/LQ2/mandatory-LQ3 path, or the reduced retry still cannot execute safely, classify the missing qualification evidence as `BLOCKED`/harness-resource-model issue. Do not classify the product as failed unless a properly designed representative measurement violates a frozen product resource/performance requirement.

Independent checks that remain safe and materially useful may continue after non-fatal advisory failures.

## Material versus advisory results

Acceptance-critical:

- stable full production identity and read-only authority;
- native forward-only production path;
- exact bounded recovery fallback/state equivalence;
- exact shared REPAIR2 runtime path on mandatory production rungs;
- zero proposal full-state clones and no inverse mapping/mutation;
- coverage/hard-obligation non-regression;
- valid 16,384 production checkpoint sentinel for the current ladder;
- conservative combined-chain `>=10x` lower bound;
- safely admitted/contained execution and production non-mutation.

Advisory/nonblocking when safety and interpretation remain sound:

- optional GPU/system/page-cache telemetry;
- optional 512/1024 repair rungs when mandatory evidence is already sufficient;
- extra timing repetitions beyond the bounded decision rule;
- profiler counters;
- cosmetic report metadata.

Do not let an advisory defect disqualify otherwise valid material evidence.

## Expected implementation change surface

- `scripts/mvsel2_bounded_qualification.py` — redesign supervisor/worker, read-only authority capture, resource discovery/admission, aggregate monitoring, adaptive stages, performance bound, cleanup/scavenging.
- `mdstats/training_data/mvsel2_hardening_runtime.py` and/or `target_multi_view_repair_v2.py` — small private refactor only as needed to share exact checkpoint-started rung execution without fresh full-domain validation.
- `benchmarks/benchmark_mlff_mvsel2_harden1_v3_repair2_production.py` — retire fixed-eight default execution in favor of the shared bounded rung helper/evidence mode, or replace it with a dedicated lightweight wrapper that contains no repair science.
- focused tests for read-only DB handling, restored-state repair helper equivalence, process-tree monitoring, admission, exact recovery-state comparison, deterministic timing rank selection, repair upper-bound arithmetic, adaptive stopping/retry, cleanup/scavenging, and failure classification.
- update the qualification run card/evidence schema.

No public/scientific algorithm change is intended.

## Gates

| Gate | Status | Purpose |
|---|---|---|
| R7-G0 | PENDING | Freeze exact read-only authority capture, resource model, state-equivalence fields, timing ranks, and repair-bound arithmetic. |
| R7-G1 | PENDING | Implement one-worker supervisor, aggregate containment, ownership, cleanup/scavenging, and bounded evidence retention. |
| R7-G2 | PENDING | Implement LQ1/LQ2 without full-domain validation scan and add exact state-equivalence tests. |
| R7-G3 | PENDING | Factor exact checkpoint-started REPAIR2 rung helper and implement adaptive 128/256[/512/1024] benchmark plus mandatory 16,384 sentinel. |
| R7-G4 | PENDING | Implement deterministic ranks-128..135 selector sentinel and conservative selector+repair combined-speedup bound. |
| R7-G5 | PENDING | Run focused harness/runtime tests, cleanup/failure tests, and one-command small-fixture dry qualification. |
| R7-G6 | PENDING | Run the autonomous workstation qualification and hand compact evidence to verification. |

## Design-revision triggers

Return to design only if implementation requires changing frozen selector/repair scientific semantics, checkpoint compatibility/identity, MVIDX1 scientific content/schema, REPAIR1/REPAIR2 equivalence, or the `>=10x` combined-chain threshold.

Safe resource-discovery mechanics, equivalent process containment, evidence paths/formatting, optional telemetry, and bounded adaptive sample sizing within the rules above do not require another workplan revision.
