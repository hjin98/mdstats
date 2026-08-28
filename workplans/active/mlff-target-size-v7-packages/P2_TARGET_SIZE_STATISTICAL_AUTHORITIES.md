---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P2
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
sequence: 2
status: blocked-on-p1
---

# P2 — Target-size statistical authorities

## Purpose

Build the complete V7 target-size **statistical problem definition** on top of the accepted P1 neutral substrate, while keeping it unreachable from current production commands until P4.

P2 owns data populations, configuration resolution, deterministic orders, candidate membership, evaluation ladder and pure study/reducer state. It does **not** own DATA7/MACE/TRAIN2 materialization or current runtime persistence cutover.

## Entry conditions

- P1 exit gate accepted and committed.
- Neutral frame/statistical identities are deterministic and compatibility-domain independent.
- Parent V7 workplan remains unchanged in authority.

## Pass P2-A — size/evaluation/fidelity configuration authority

Implement one resolver for:

```text
candidate_sizes = [2^p for pmin..pmax]
Nmax = max(candidate_sizes)
M sizes = [2^q for evaluation_size_powers]
fidelity boundaries = [n1,n2,n3]
ordered screening optimizer seeds = sole enabled method seeds
```

Required behavior:

- default current values reproduce V7 defaults;
- non-default valid powers/boundaries work;
- production `[training].max_num_epochs` is independent of `n3`;
- no hidden fixed-eight/fixed-16384 scientific guard remains in V7 objects;
- exactly one ordered optimizer-seed set belongs to the study; unrelated seed namespaces are excluded.

### Verification cycle

1. focused config normalization/boundary/error tests;
2. affected config/template/spec regression;
3. identity tests showing CV-only seed/fold changes do not change target-size policy identity, while target-size seed-set edits do.

## Pass P2-B — one deterministic `P_train/M3` split

Implement the V7 split owner over neutral `U_size`.

Required invariants:

```text
P_train intersect M3 = empty
|P_train| >= Nmax
|M3| = m3
```

Training support has priority; duplicate/correlation groups prevent leakage but do not create domains or multiply cardinality.

Nominal capacity is `Nmax + m3`, subject to actual correlation feasibility.

### Verification cycle

1. focused allocation/cardinality/disjointness tests;
2. adversarial correlation-group fixtures proving impossible allocations fail explicitly;
3. deterministic reconstruction test;
4. affected neutral-statistical regression.

## Pass P2-C — one current target-training order

Implement one V7 owner:

```text
P_train + frozen selection evidence/policy -> pi_train + diagnostics
```

Reuse/refactor optimized MVSEL2/REPAIR2 numerical kernels only behind this owner when semantically justified. Do not persist/publicly expose FEAS/MVIDX/MVSEL/REPAIR/MVQUAL as current V7 scientific authorities.

Every candidate is exactly:

```text
T_N = pi_train[:N]
```

Required qualification is intentionally small: prefix exists, labels are usable, explicit hard support constraints are satisfied.

### Verification cycle

1. exact-prefix/nested-membership tests for all configured N;
2. deterministic tie/order tests;
3. reference/oracle equivalence for reused optimized kernels;
4. bounded CPU/RAM/I/O/performance checks where the kernel path changed;
5. structural inspection proving no per-provenance/per-CV master-order fanout exists in the V7 owner.

## Pass P2-D — one evaluation order and exact M ladder

Freeze `pi_eval` using only candidate-independent evidence before any candidate result exists:

```text
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
```

Required invariants:

- `M1 subset M2 subset M3` exactly;
- all M configurations are disjoint from every `T_N` because M3 is disjoint from P_train;
- no complement subtraction/fallback exists;
- candidate predictions/survival/results cannot influence `pi_eval`.

### Verification cycle

1. exact nested-membership/disjointness tests;
2. deterministic ordering/restart tests;
3. negative test proving candidate evidence cannot be supplied to the ordering owner;
4. correlation/support diagnostic checks.

## Pass P2-E — pure V7 target-size study/reducer state

Implement the target-size study state machine/evidence model without executing training.

It must represent:

- configured candidate sizes and ordered two-seed replicate set;
- exact `T_N` identities;
- exact M1/M2/M3 identities;
- n1/n2/n3 boundaries;
- survivor transitions `q -> min(q,4) -> 2 -> 1`;
- practical-equivalence/smaller-N rule;
- typed `nonconverged_at_configured_ceiling`;
- incomplete/unrankable evidence for missing/duplicate/reordered seed populations;
- terminal immutable `N_selected/T_selected`.

It must not contain label-domain maps, CV plans, complement roles or per-domain prefix digests.

### Verification cycle

1. reducer/state-transition unit/property tests with synthetic metrics;
2. paired-seed aggregation/equivalence tests;
3. numerical-failure versus execution-failure classification tests;
4. serialization/restart tests;
5. structural schema assertions for forbidden old fields.

## Pass P2-F — package closure

Required integrated path, using real P1/P2 owners and bounded data:

```text
neutral U_size
 -> config
 -> P_train/M3
 -> pi_train/pi_eval
 -> T_N and M1/M2/M3
 -> pure target-size study ready for first boundary
```

Acceptance requires:

- exactly one target-size study regardless of provenance-group count;
- capacity has no provenance/CV/seed multiplier;
- all candidate/evaluation memberships are exact and deterministic;
- P2 objects are independently serializable/restartable;
- no DATA7/CV/current-runtime dependency is needed to construct the study;
- complete P2 affected regression passes.

## Exit gate

P2 is accepted only when:

> The entire V7 statistical experiment can be deterministically constructed and reduced without executing training and without any dependency on label domains, CV plans, complement populations, or old multi-authority target-size topology.

Commit/tag the accepted P2 checkpoint before P3.
