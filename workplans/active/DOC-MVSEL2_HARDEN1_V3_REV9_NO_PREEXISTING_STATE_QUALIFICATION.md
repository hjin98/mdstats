---
kind: qualification-workplan
workplan_id: DOC-MVSEL2-HARDEN1-V3
plan_revision: 9
protocol_version: 3.1.0
status: READY_FOR_TARGET_QUALIFICATION
supersedes: workplans/active/DOC-MVSEL2_HARDEN1_V3_REV8_FINAL_REVIEWED_QUALIFICATION.md
product_candidate_anchor: c7f67572a37c81b8eba05e6cbf601f933d46fbe1
---

# MVSEL2 HARDEN1 REV9 — qualification without pre-existing MVSEL2/MVSTATE2 artifacts

## Why REV9 exists

The target workstation probe on 2026-08-19 established the actual production persistence state for domain `label-domain-5aa1ee5d50cd0b23`:

- final `target_multi_view_selection_v2` record: absent;
- SQLite MVSTATE2 pointer rows: none;
- orphan immutable MVSTATE2 bundle manifests under production `.mdstats`: none;
- bounded directory scan: 43 directories;
- conclusion: `NO_MVSTATE2_ARTIFACTS` for all rungs 128 through 16,384.

Therefore REV8's assumption that a completed production selector plan and an authenticated production MVSTATE2 ladder already existed is false for this campaign. Repeated recovery attempts would be a harness-design defect, not useful qualification.

REV9 corrects only the qualification evidence path. Frozen MVSEL2, MVSTATE2, REPAIR2, MVIDX1, resource-containment, and `>=10x` performance acceptance semantics remain unchanged.

## Candidate boundary

The packaged product/runtime candidate remains anchored at:

`c7f67572a37c81b8eba05e6cbf601f933d46fbe1`

All changes after that anchor through REV9 are confined to qualification scripts and workplans. No packaged `mdstats/` runtime bytes are changed by REV9. Existing materially applicable G5 package/focused-test evidence may therefore be reused under Protocol 3.1 when the declared G5 material surface is byte-identical.

## Revised evidence model

### 1. Production input authority remains full-scale and read-only

The target campaign still supplies the scientific input authority:

- target-coverage reference;
- native forward-only MVIDX1;
- dataset/domain identity;
- candidate UID order;
- family order and witness weights;
- hard-obligation definitions;
- correlation-unit mapping;
- exact frozen MVSEL2 policy.

The production SQLite database is opened `mode=ro`. No REV9 stage creates, repairs, or writes a production record.

Absence of a completed selection plan or MVSTATE2 checkpoint is now recorded as expected campaign state, not a blocker.

### 2. One bounded current selector execution supplies all production-state evidence

REV9 allocates the exact compact mutable state that production uses *after* full feasibility validation, but intentionally skips the expensive complete forward-graph reachability scan during qualification. Structural identity/shape checks remain mandatory.

The qualifier then executes exact current MVSEL2 Phase A from rank 0 until Phase A completes on the authenticated production graph.

This single execution supplies:

- current-candidate Phase-A performance;
- the current deterministic selected prefix;
- qualification-owned exact states at ranks 128 and 256;
- the starting state for the current exact Phase-B rebase/performance sample.

No selector work is duplicated solely to manufacture qualification evidence.

### 3. LQ2 recovery uses qualification-owned MVSTATE2 on the real production transition

At ranks 128 and 256 the qualifier serializes immutable MVSTATE2 bundles into run-owned scratch using the production MVSTATE2 writer and production scientific identity.

It then:

1. records both pointers in a qualification-owned scratch `CampaignStore`;
2. corrupts only the qualification-owned rank-256 pointer row;
3. calls the real runtime `_highest_valid_resume_states(...)` recovery path;
4. requires fallback to rank 128;
5. replays the exact freshly generated ranks 128..255 through production score/select mutation;
6. compares the resulting state exactly against the authenticated qualification-owned rank-256 checkpoint.

The exact comparison remains:

- selected order;
- availability;
- every family multiplicity;
- every family coverage mass;
- obligation counts;
- unsatisfied required-obligation count;
- correlation-unit counts;
- representative utility.

This proves the same recovery transition on the real production graph without claiming that the campaign had pre-existing production checkpoints.

### 4. LQ3 REPAIR2 uses those authenticated bounded states

Mandatory production-graph measurements remain ranks 128 and 256. The shared production `repair_rung_from_authenticated_state(...)` helper is used directly.

Measured material invariants remain:

- proposal count and wall time;
- zero proposal full-state copies;
- no inverse mapping/mutation;
- same-N family coverage non-regression;
- hard-obligation non-regression.

If 128/256 do not exercise proposal cost, the qualifier may extend the already-live Phase-B state to 512 and at most 1024, only while admitted by the operating envelope, stopping immediately once proposal cost is measured.

Accepted-swap future-rank inheritance remains focused-fixture authority unless the generated current selector prefix actually contains the displaced future rank. REV9 never invents an unknown future master-order position.

### 5. The 16,384 requirement is a capability/projection claim, not a fake checkpoint sentinel

Because no production rank-16,384 checkpoint exists, REV9 removes the REV8 mandatory 16,384 checkpoint sentinel.

Large-rung capability is established jointly by:

- frozen `TargetMultiViewSelectorPolicyV2.target_sizes` containing 16,384;
- authenticated production candidate count >= 16,384;
- successful exact current Phase-A -> Phase-B transition on the real graph;
- G5 correctness/oracle/persistence/repair coverage for cardinality-generic runtime semantics;
- current-candidate selector performance projection explicitly through rank 16,384;
- current production-graph REPAIR2 proposal-cost projection over all materializable frozen rungs through 16,384.

Historical 16,384 MVSEL2 execution remains advisory only and is not promoted to current-candidate source-bound acceptance evidence.

### 6. LQ4 current performance projection

Legacy MVSEL1 baseline reuse rules remain unchanged and fail closed:

- exact production graph identity;
- accepted workstation host context;
- unchanged tracked legacy comparator surface from historical source head.

Current MVSEL2 timing now measures *all* Phase-A ranks from 0 to completion. Therefore the former conservative synthetic rank-0..127 prefix surcharge is no longer needed.

The qualifier then performs:

- one exact current family-streaming Phase-B rebase;
- at least 32 exact current Phase-B choice+mutation ranks;
- optional additional Phase-B ranks only when needed to reach 512/1024 REPAIR2 calibration states.

For conservatism, the maximum rank time over every measured current Phase-B rank is used in the 16,384 selector projection.

The frozen outer selector timing margin and REPAIR2 incidence/cache safety factor remain unchanged. PASS still requires:

`combined_speedup_lower >= 10.0`

A current bounded projection below 10x is product/performance FAIL. Missing safely establishable baseline, rebase, or proposal-cost evidence is BLOCKED.

## Resource model

REV8's corrected resource supervisor remains authority:

- effective capacity, hard containment, and smaller operating envelope remain distinct;
- production MVIDX is mapped once by one worker;
- no `RLIMIT_AS`;
- aggregate owned-process RSS, scratch blocks, wall time, and host/cgroup pressure are monitored;
- hard limits are exceptional containment, not execution targets;
- run-owned scratch is cleaned on PASS/FAIL/BLOCKED/exception/signals;
- production identity is checked before/after execution.

The prior workstation run demonstrated the resource correction: peak worker RSS was approximately 35.3 GiB under a 42.8 GiB hard ceiling. The remaining blocker was persistence discovery, now removed by REV9.

## G5 evidence reuse

Qualification-wrapper-only changes do not invalidate packaged-runtime G5 evidence.

A prior G5 PASS may be reused only when:

- the declared G5 material surface is clean in the worktree;
- the prior candidate commit is available;
- Git proves no change between the prior and current commits across `mdstats/`, packaging metadata, the G5 preflight, and the focused/adjacent test files.

Otherwise G5 reruns normally.

## Acceptance

REV9 PASS requires all of:

1. G5 PASS or valid Protocol-3.1 reuse;
2. stable read-only production reference/MVIDX/config identity;
3. expected 36,408 candidates, 165 families, and authenticated MVIDX identity;
4. native forward-only MVIDX path with no inverse arrays mapped;
5. exact current Phase-A execution from rank 0 on the production graph;
6. qualification-owned 128/256 MVSTATE2 persistence and exact 128->256 recovery equivalence;
7. exact shared REPAIR2 production-graph measurements with no full-state proposal copies/inverse mutation and no same-N scientific regression;
8. safely established REPAIR2 proposal-cost upper bound;
9. exact current Phase-B streaming rebase and >=32 measured current Phase-B ranks;
10. compatible historical MVSEL1 baseline;
11. conservative combined selector+REPAIR2 speedup lower bound >=10x through 16,384;
12. clean owned-scratch recovery and unchanged production identity after execution.

Pre-existing production `target_multi_view_selection_v2`, MVSTATE2 pointers, orphan MVSTATE2 bundles, or a rank-16,384 checkpoint are explicitly **not** acceptance prerequisites for this campaign.

## Implementation

REV9 worker:

`scripts/mvsel2_bounded_qualification_noartifacts.py`

REV9 routing/evidence reuse:

`scripts/mvsel2_bounded_qualification_core.py`

The visible entrypoint and resource supervisor remain:

`scripts/mvsel2_bounded_qualification.py`

`scripts/mvsel2_bounded_qualification_engine.py`

## Target command

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

No manual checkpoint probe is required after REV9 is pulled.
