# MLFF target-subset size-study specification

**Status:** current normative target-size policy  
**Architecture:** revision 105

## 1. Scope and sole ownership

This specification owns the scientific target-training cardinality used by the current MLFF protocol. It defines the nominal size population, materializability, hard qualification, successive-fidelity screening, paired-seed comparison, terminal outcomes, and publication identity of the selected size.

It does not own target-monitor cardinality, replay-monitor cardinality, minibatch size, worker count, descriptor-block size, or arbitrary pool cardinality. Numeric equality between one of those quantities and a target-size rung has no semantic effect.

The policy record is `TargetSizeStudyPolicy`. The terminal record is `TargetSizeDecision`.

## 2. Required inputs and evidence roles

The study consumes only:

- required final-development and cross-validation **gradient-training domain** identities from DATA5;
- one current REPAIR2 repaired master order per required training domain;
- independent MVQUAL evidence for candidate prefixes;
- the common target online monitor defined by `OnlineTargetMonitorPolicy`;
- the replay monitor defined by `ReplayMonitorPolicy` when replay is part of the protocol;
- the frozen foundation, replay, objective, optimizer/LR, exposure, precision/backend, and seed policy used for the size experiment.

The following evidence is forbidden from controlling the target-size decision:

- held-out cross-validation evaluation folds;
- calibration cohorts;
- locked interpolation/challenge tests;
- post-deployment observables or test results.

Cross-validation evaluates the already-frozen protocol containing the selected size; it is not an inner size-selection loop.

## 3. Size populations

The fixed nominal scientific population is exactly

```text
128, 256, 512, 1024, 2048, 4096, 8192, 16384
```

and is represented by

```text
TargetSizeStudyPolicy.nominal_sizes
```

in strictly increasing order.

For required training domain `d`,

```text
N_available[d] = number of eligible candidates in that gradient-training domain
```

The common materializable population is

```text
N_materializable = {
  N in nominal_sizes :
  N <= min_d N_available[d]
}
```

where the minimum is over every required final-development and cross-validation gradient-training domain participating in the protocol.

A materializable rung `N` maps to domain-local membership

```text
D[d,N] = repaired_master_order[d][:N]
```

and therefore requires no independent re-selection or repair at that rung.

## 4. Independent hard qualification

MVQUAL independently evaluates every required materializable prefix under the frozen multi-view hard-coverage and obligation policy.

A size is qualified only when it passes in **every** required training domain:

```text
qualified_sizes = {
  N in N_materializable :
  MVQUAL(d, N).hard_pass for all required d
}
```

Because all rungs are nested prefixes of one repaired order per domain and the hard predicates are positive coverage/obligation predicates, hard satisfaction is monotone with increasing `N`. The qualified population SHALL therefore be a contiguous suffix of the materializable nominal ladder.

A pass/fail/pass pattern is an invariant violation. Preparation SHALL fail closed rather than skip the failure or create a replacement rung.

At least three qualified sizes are required to execute the production fidelity funnel. Otherwise the terminal outcome is `insufficient_qualified_sizes`.

When fewer than three nominal sizes are materializable before hard qualification, the terminal outcome is `insufficient_materializable_sizes`.

## 5. Protocol-controlled fidelity trajectory

Every candidate size uses the same frozen experiment protocol except for domain-local target membership implied by `N`.

The following SHALL be identical across candidate sizes:

- foundation/model initialization identity;
- replay source, replay-monitor identity, and replay exposure semantics;
- objective and configuration/property weights;
- optimizer and learning-rate schedule;
- exposure backend and loader realization policy;
- model precision/backend;
- checkpoint metric definitions used by the study;
- frozen ordered training-seed set.

Each candidate/seed follows one authenticated continuation trajectory:

```text
foundation -> epoch 3 -> epoch 10 -> epoch 30
```

Epoch 10 SHALL continue the exact epoch-3 model, optimizer, RNG, and protocol state. Epoch 30 SHALL continue the exact epoch-10 state. Restart or persistence may change storage realization but not parentage.

Ordinary target-success early stopping is disabled during the target-size study. Candidates must reach the common fidelity boundary to remain comparable. Hard numerical/scientific failures remain admissible rejection events.

## 6. Production successive-fidelity funnel

Let `q = len(qualified_sizes)`.

The production funnel is exactly:

```text
q < 3       -> insufficient_qualified_sizes
q >= 3      -> epoch 3:  q -> min(q,4)
               epoch 10: <=4 -> 2
               epoch 30: 2 -> 1 or typed failure
```

No eliminated candidate is trained to a later fidelity in ordinary production.

### 6.1 Paired-seed aggregation

Every size candidate is evaluated using the same ordered seed set. Screening comparisons SHALL aggregate seed evidence by the policy-defined paired aggregation, preserving the size-to-size pairing by seed.

A comparison SHALL NOT substitute unrelated seeds merely because the number of runs is the same.

### 6.2 Epoch-3 and epoch-10 screens

The primary screening metric is the current target-force metric identified by `TargetSizeStudyPolicy.primary_screen_metric` and evaluated on the common authorized target monitor.

The practical-equivalence width is exactly

```text
1 meV/Angstrom
```

for the epoch-3 and epoch-10 size screens.

When two candidates are within this width under the policy-defined paired aggregate, the smaller target size is preferred.

The early screens rank relative learning behavior. They do not require the final absolute target-force acceptance threshold.

The epoch-3 survivor count is `min(q, 4)`. The epoch-10 survivor count is exactly `2`.

Tie resolution after the practical-equivalence rule SHALL be deterministic and specification-serialized.

### 6.3 Epoch-30 final comparison

The two finalists continue to epoch 30. A winner is eligible only if it satisfies the complete frozen final admissibility policy, including all applicable:

- global target metrics;
- focus-group/species metrics;
- energy/stress constraints;
- replay-retention constraints;
- structural/physical-integrity checks;
- relaxation/deployment-integrity checks;
- other current mandatory checkpoint/model constraints.

Replay retention, physical integrity, and deployment integrity are hard constraints. They are not positive score bonuses unless a future explicit architecture/specification revision changes that rule.

If exactly one finalist is admissible, it wins. If both are admissible, the policy applies its current primary comparison and practical-equivalence/smaller-size preference as serialized in `TargetSizeStudyPolicy`. If neither is admissible, the outcome is `no_admissible_finalist` unless a more specific hard-scientific-failure outcome applies.

## 7. Ceiling and non-convergence semantics

The fixed scientific ceiling is 16,384. The workflow SHALL NOT generate an intermediate or larger rescue size to avoid a non-convergence result.

When the available corpus does not materialize 16,384 and the largest materializable/qualified candidate remains materially superior at the final authorized comparison boundary, the terminal outcome is:

```text
nonconverged_at_available_ceiling
```

When 16,384 is materializable/qualified and remains materially superior such that the policy cannot establish a converged smaller target size, the terminal outcome is:

```text
nonconverged_at_fixed_ceiling
```

A non-convergence result is scientifically meaningful and SHALL be preserved rather than converted to an arbitrary integer.

## 8. Terminal result schema

`TargetSizeDecision` is a tagged result with at least these terminal states:

```text
selected(N)
insufficient_materializable_sizes
insufficient_qualified_sizes
no_admissible_finalist
nonconverged_at_available_ceiling
nonconverged_at_fixed_ceiling
hard_scientific_failure
```

A `selected(N)` result SHALL bind:

- `TargetSizeStudyPolicy` digest;
- nominal/materializable/qualified populations;
- every required training-domain identity;
- repaired-order and MVQUAL identities;
- common target/replay monitor identities;
- foundation/replay/objective/optimizer/LR/exposure/precision/backend identities;
- ordered seed set;
- authenticated 3/10/30 continuation lineage for trained candidates;
- survivor decisions and deterministic comparison evidence;
- selected `N`.

Typed failure results SHALL preserve enough upstream and comparison evidence to explain why no selected size was produced.

## 9. Relationship to cross-validation and final training

Once `selected(N)` is frozen, `N` becomes part of `TrainingProtocolIdentity`.

Every required cross-validation/final training domain uses its own local repaired order prefix of length `N`; membership need not be identical across domains.

Held-out cross-validation then evaluates the complete protocol. Any later change to `N`, target-membership policy, replay, objective, stopping/LR policy, precision/backend, or another protocol-defining field creates a different protocol and invalidates the previous protocol-matched validation claim.

## 10. Production versus screening-policy qualification

Ordinary campaigns use only the successive-fidelity funnel above.

Release/algorithm qualification MAY retrospectively train the complete qualified candidate population to epoch 30 to measure whether the epoch-3/epoch-10 screens retained the eventual finalists. Such exhaustive evidence is qualification-only and SHALL NOT become a default production workload or a reason to persist eight independent product-scale dataset/graph states.

If representative qualification demonstrates inadequate survivor recall, the screening policy must be explicitly revised and requalified.

## 11. Bounded materialization

Candidate sizes are prefix metadata/views over one current REPAIR2 master order per training domain. The implementation SHALL NOT require one independent product-scale descriptor set, MVIDX graph, selector state, or repaired dataset per nominal rung.

Training artifacts are materialized only for candidates authorized to train at the current fidelity stage. Reconstructible caches may be evicted/rebuilt under the current resource/storage specifications without changing the scientific decision.

## 12. Unsupported historical behavior

The current specification has no generated-size rescue policy, adaptive ladder construction, MVMIGRATE path, or legacy campaign-generation fallback.

A persisted artifact from an unsupported generation either validates as a current-generation artifact under the current schema/identity contract or is rejected. It does not gain current meaning through migration aliases.

## 13. Failure conditions

The study fails closed when, among other conditions:

- nominal sizes differ from the frozen current population without a policy revision;
- a required domain lacks a current repaired master order;
- required MVQUAL evidence is missing, stale, or non-monotone;
- a held-out/calibration/locked role enters size selection;
- candidate sizes use different seeds or protocol-defining training semantics;
- epoch continuation parentage cannot be authenticated;
- ordinary success early stopping truncates a required fidelity comparison;
- an implementation invents a non-nominal rescue size;
- target size is inferred from monitor, replay, batch, or pool cardinality;
- duplicated per-rung product-scale state violates bounded-materialization requirements.
