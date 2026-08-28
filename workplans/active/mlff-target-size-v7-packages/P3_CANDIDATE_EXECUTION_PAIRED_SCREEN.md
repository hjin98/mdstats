---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 3
status: blocked-on-p2
---

# P3 — Candidate execution and paired-seed screen

## Purpose

Connect the accepted P2 statistical experiment to the existing shared DATA7/DATA8/MACE/TRAIN2/EVAL2 machinery without inheriting old per-domain/CV/complement semantics.

P3 proves that one V7 candidate trajectory can be prepared, trained, continued and evaluated end-to-end. The new path remains non-current/unreachable from normal production commands until P4.

## Entry conditions

- P1 and P2 accepted and committed.
- Exact `T_N`, `M1/M2/M3`, target-size study state and ordered optimizer-seed set exist independently of training.
- Shared DATA8/TRAIN2/EVAL2 execution machinery is still the preferred execution substrate; no second training engine may be introduced.

## Pass P3-A — common deterministic preparation

Implement one common target-size preparation/training-math identity shared across every N and optimizer seed.

As applicable it owns/fixes:

- feature/projection policy and any fixed numerical projection seed;
- common E0/reference policy and fitted result;
- normalization/objective/property/configuration weights;
- replay source/exposure policy;
- foundation/model/head identity;
- training protocol/LR/precision/backend/batch/exposure policy excluding optimizer seed;
- target-size metric/evaluation policy.

It may derive from `P_train` or another V7-authorized common preparation population, but may not consume M1/M2/M3, CV, outer held-out, calibration or locked evidence.

Do not fit a new E0/normalization/objective per N merely because old APIs are domain-local.

### Verification cycle

1. focused DATA7/preparation identity tests;
2. same common-preparation digest asserted across all N and both optimizer seeds;
3. negative tests preventing M/CV/held-out evidence from entering fit inputs;
4. affected DATA7/reference-fit/objective regression;
5. reopen design rather than hide an N-dependent fit if the training engine positively proves one is mathematically required.

## Pass P3-B — exact V7 candidate materialization

Refactor materialization so a candidate is bound directly to:

```text
N
T_N digest + exact frame membership
common preparation digest
optimizer seed
screen policy / active boundary
shared training protocol/replay identity
continuation ancestry
```

Required end state:

- no prescribed prefix per DATA7 domain;
- no CV training-domain list;
- no per-label evaluation cohort;
- no complement population;
- one target-size trajectory per required `(N, optimizer_seed)`.

Reuse existing fixed-file cache, replay staging, foundation staging, MACE configuration generation, atomic promotion and resource-safe materialization.

### Verification cycle

1. exact membership materialization tests;
2. cache/restart/serialization tests;
3. structural assertions that V7 candidate objects contain no old per-domain target-size fields;
4. affected DATA8/materialization regression.

## Pass P3-C — paired optimizer-seed TRAIN2 execution and exact continuation

For every active candidate N, execute the same ordered optimizer seeds, currently `[1,2]`.

Required stochastic semantics:

- optimizer seed is passed to the real MACE/TRAIN2 config;
- seed identity is the same across N for paired comparison;
- deterministic preparation is unchanged by seed;
- n2 continues exact surviving n1 model/optimizer/RNG/schedule state;
- n3 continues exact surviving n2 state;
- later boundaries do not restart from epoch zero;
- ordinary generic early stopping cannot truncate the required screening boundary.

Do not require byte-identical RNG consumption across different N; require same seed and same stochastic policy.

### Verification cycle

1. schedule/variant-identity tests;
2. real TRAIN2 owner tests using bounded/faked expensive training below the scheduler/state-machine boundary;
3. persisted checkpoint/optimizer/RNG ancestry tests;
4. restart-after-boundary and interrupted-resume tests;
5. affected training scheduler/resource regression.

## Pass P3-D — exact-M EVAL2 population authority

Replace only EVAL2's target-size population/role authority. Retain the metric engine, block reductions, bootstrap/comparison logic, numerical guards, caches and optimized inference path.

Each screening evaluation role binds the exact active M rung and its correlation-block evidence. It does not derive a complement from T_N and does not use CV monitor roles.

Any target-validation file required by the MACE training harness must be fixed and explicitly non-controlling: no gradients, LR mutation, generic stop authority, ranking, or survivor control.

### Verification cycle

1. exact M_i role/membership tests;
2. reference-equivalence tests for retained EVAL2 reductions;
3. negative tests against complement/coarse/CV-role fallback;
4. proof that training-harness validation cannot control screening decisions;
5. affected EVAL2/inference/cache regression and bounded resource checks.

## Pass P3-E — assembled successive-fidelity reducer

Connect authenticated TRAIN2 boundary results from both paired seeds to the P2 target-size reducer:

```text
n1/M1: q -> min(q,4)
n2/M2: <=4 -> 2
n3/M3: 2 -> 1 or typed ceiling nonconvergence
```

Required behavior:

- arithmetic/policy aggregation uses the complete ordered seed population;
- missing/duplicate/reordered seed evidence is unrankable;
- practical equivalence prefers smaller N;
- replay/CV/physical/deployment evidence cannot rank/tie-break N;
- eliminated candidates receive no later normal screen work;
- terminal state freezes exact `N_selected/T_selected`.

### Verification cycle

1. synthetic metric reducer/property tests;
2. real-owner boundary tests connecting actual candidate records to reducer state;
3. eliminated-no-later-work scheduling test;
4. typed scientific numerical failure versus ordinary execution failure tests;
5. restart reproducibility across all boundaries.

## Pass P3-F — package closure

Run one bounded end-to-end V7 candidate screen path through the real P1/P2/P3 semantic owners:

```text
neutral data
 -> P_train/M3 + pi_train/pi_eval
 -> common preparation
 -> candidate DATA8 materialization
 -> TRAIN2 n1
 -> EVAL2 M1
 -> reducer/survivors
 -> exact continuation n2/M2
 -> exact continuation n3/M3
 -> freeze selected N/T_selected
```

Expensive ML calculations may be reduced/faked below the real orchestration/training/evaluation owner boundaries, but the owner logic itself may not be monkeypatched or reimplemented in the harness.

Acceptance requires complete affected DATA7/DATA8/TRAIN2/EVAL2/target-size regression and no current production-runtime switch yet.

## Exit gate

P3 is accepted only when:

> A complete V7 paired-seed target-size screen can execute on the new statistical authorities using the shared production training/evaluation machinery, with exact membership and continuation, while remaining unreachable from the old current CLI/runtime until the atomic P4 cutover.

Commit/tag the accepted P3 checkpoint before P4.
