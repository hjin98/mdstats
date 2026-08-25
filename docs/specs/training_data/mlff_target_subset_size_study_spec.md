# MLFF target-subset size-study specification

**Status:** current normative target-size policy  
**Architecture:** revision 106

## 1. Scope and sole ownership

This specification owns the scientific target-training cardinality used by the current MLFF protocol. It defines the nominal size population, materializability, hard qualification, successive-fidelity screening, paired-seed comparison, terminal outcomes, and publication identity of the selected size.

It does not own target-monitor cardinality, replay-monitor cardinality, minibatch size, worker count, descriptor-block size, or arbitrary pool cardinality. Numeric equality between one of those quantities and a target-size rung has no semantic effect.

The policy record is `TargetSizeStudyPolicy`. The derived study/terminal authority is `TargetSizeStudyPlan`.

## 2. Required inputs and evidence roles

The study consumes only:

- required final-development and cross-validation **gradient-training domain** identities from DATA5;
- one current REPAIR2 repaired master order per required training domain;
- independent MVQUAL evidence for candidate prefixes;
- the common target online monitor defined by `OnlineTargetMonitorPolicy`;
- replay semantics/monitor identity when replay is part of the frozen training protocol; replay metric values are diagnostic only and are not consumed by size ranking;
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
TargetSizeStudyPolicy.candidate_sizes
```

in strictly increasing order.

For required training domain `d`,

```text
N_available[d] = number of eligible candidates in that gradient-training domain
```

The common materializable population is

```text
N_materializable = {
  N in candidate_sizes :
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

Materializability is part of membership in `Q`; there is no separate materializability terminal class. Any case with fewer than three materializable-and-MVQUAL-qualified sizes terminates as `insufficient_qualified_sizes`.

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

Each candidate/seed follows one authenticated continuation trajectory controlled
by the serialized fidelity tuple `(n1, n2, n3)` and independent full TRAIN2
horizon `n`:

```text
foundation -> epoch n1 -> epoch n2 -> epoch n3
                              \-> selected production training to n
```

`n1 < n2 < n3 <= n` is required. Epoch `n2` SHALL continue the exact
`n1` model, optimizer, RNG, and protocol state; epoch `n3` SHALL continue the
exact `n2` state. The full horizon `n` is the frozen TRAIN2 schedule horizon,
not a fourth ordinary size-screen. Restart or persistence may change storage
realization but not parentage.

Ordinary target-success early stopping is disabled during the target-size study. Candidates must reach the common fidelity boundary to remain comparable. A successful endpoint is represented only by strict finite `TargetSizeTrainingEvidence`; positively identified candidate-specific TRAIN2/EVAL2 numerical invalidity is represented separately by authenticated `TargetSizeTrajectoryFailureEvidence`. Generic execution, resource, input, schema, lineage, timeout, interruption, launch, and programming failures remain campaign errors rather than scientific size evidence.

## 6. Production successive-fidelity funnel

Let `q = len(qualified_sizes)`.

`[target_data.size_convergence].fidelity_epochs` supplies `(n1, n2, n3)`;
`[training].max_num_epochs` supplies `n`. The generated current default is
`(1, 3, 10) / 30`, but these are configuration values authenticated by
`TargetSizeStudyPolicy` and the TRAIN2 schedule authority, not public numeric
API names or fixed schema behavior.

The production funnel is exactly:

```text
q < 3       -> insufficient_qualified_sizes
q >= 3      -> epoch n1: q -> min(q,4)
               epoch n2: <=4 -> 2
               epoch n3: 2 -> 1 or typed failure
```

No eliminated candidate is trained to a later fidelity in ordinary production.

### 6.1 Paired-seed aggregation

Every size candidate is evaluated using the same ordered seed set. The current seed authority is the ordered `seeds` field of the **sole enabled training method** in the campaign training protocol. Current generated campaigns default that owning field to `[1, 2]`; the target-size subsystem does not define a second seed list. If multiple training methods are enabled, target-size study construction fails closed rather than choosing one implicitly.

`TargetSizeStudyPolicy.screening_optimizer_seeds` authenticates that ordered owning-method seed set. Screening comparisons SHALL aggregate seed evidence by the policy-defined paired aggregation, preserving the size-to-size pairing by seed. The current aggregation is the arithmetic mean of the complete paired seed population for each size.

Every persisted TRAIN2 endpoint evidence item also authenticates the complete target-size-study policy digest. Therefore evidence generated under one seed set, equivalence width, ranking policy, or other study-policy identity cannot be rebound to a different target-size study merely by recomputing the outer plan digest.

A comparison SHALL NOT substitute unrelated seeds merely because the number of runs is the same. Missing seeds, duplicates, seed reordering, or candidate-specific seed populations invalidate the comparison/restart state.

### 6.2 Coarse and short screens

The primary screening metric is the current target-force metric identified by `TargetSizeStudyPolicy.primary_screen_metric` and evaluated on the common authorized target monitor.

The default coarse practical-equivalence width is

```text
1 meV/Angstrom
```

for the `n1` coarse and `n2` short size screens. It is a configurable positive
finite `TargetSizeStudyPolicy.coarse_practical_equivalence_mev_per_a` field,
not a schema constant. A non-default configured value changes policy identity
and therefore invalidates reuse of target-size evidence produced under another
value.

When two candidates are within this width under the policy-defined paired aggregate, the smaller target size is preferred.

The early screens rank relative learning behavior. They do not require the final absolute target-force acceptance threshold.

The coarse survivor count is `min(q, 4)`. The short-screen finalist count is
exactly `2`.

Tie resolution after the practical-equivalence rule SHALL be deterministic and specification-serialized.

### 6.3 Final-screen comparison at `n3`

The two finalists continue to `n3` on their authenticated trajectories. MVQUAL
is the sole hard target-size eligibility authority. The final-screen comparison
SHALL NOT re-apply target-threshold, replay-retention, energy/stress,
structural/physical-integrity, relaxation, deployment, or other downstream
model/protocol acceptance gates as a second size qualification stage.

Each expected `(size, seed)` contributes exactly one stage outcome: a strict successful endpoint or authenticated candidate-specific trajectory-failure evidence. Only candidates with complete paired successful seeds are rankable. Among complete finalists, the winner is determined by the policy-defined target-size metric and practical-equivalence/smaller-size rule serialized in `TargetSizeStudyPolicy`. Replay scores and other model-quality metrics may be recorded as diagnostics only; they cannot qualify, reject, rank, or tie-break target sizes.

The final practical-equivalence width defaults to `1 meV/Angstrom` and is
independently configurable through
`TargetSizeStudyPolicy.practical_equivalence_mev_per_a`. Like the coarse
width, it is positive, finite, serialized, and part of the policy digest. It
controls the `n3` smaller-size equivalence rule and the fixed-ceiling
material-superiority test.

If authenticated numerical/scientific trajectory failures leave too few complete
paired-seed candidates to perform a required coarse, short, or final-screen
comparison, the study terminates as `insufficient_comparable_candidates`. The
terminal state records the failed fidelity stage and authenticated `(candidate
size, seed)` failure reasons. Ordinary input, programming, or lineage errors
remain exceptions rather than being absorbed into this scientific terminal
class.

After `selected_target_size` is frozen, ordinary production/CV model acceptance, replay-retention, held-out evaluation, and physical/deployment verification may accept or reject the resulting model/protocol but SHALL NOT change the selected target size.

## 7. Ceiling and non-convergence semantics

The fixed scientific ceiling is 16,384. The workflow SHALL NOT generate an intermediate or larger rescue size to avoid a non-convergence result.

When 16,384 reaches the `n3` final comparison and remains materially superior to
every smaller complete finalist by more than the configured final
practical-equivalence width, the terminal outcome is:

```text
nonconverged_at_fixed_ceiling
```

A non-convergence result is scientifically meaningful and SHALL be preserved rather than converted to an arbitrary integer.

## 8. Terminal result schema

`TargetSizeStudyPlan.outcome` is a tagged derived result with at least these terminal states:

```text
selected(N)
insufficient_qualified_sizes
insufficient_comparable_candidates
nonconverged_at_fixed_ceiling
```

A selected `TargetSizeStudyPlan` SHALL bind:

- `TargetSizeStudyPolicy` digest;
- nominal/materializable/qualified populations;
- every required training-domain identity;
- repaired-order and MVQUAL identities;
- common target/replay monitor identities;
- foundation/replay/objective/optimizer/LR/exposure/precision/backend identities;
- ordered seed set;
- authenticated `n1/n2/n3` continuation lineage for trained candidates and
  the independent full-horizon `n` schedule identity;
- survivor decisions and deterministic comparison evidence;
- selected `N`.

Typed failure results SHALL preserve enough upstream and comparison evidence to explain why no selected size was produced. No generated or intermediate rescue size is permitted.

## 9. Relationship to cross-validation and final training

Once `selected(N)` is frozen, `N` becomes part of `TrainingProtocolIdentity`.

Every required cross-validation/final training domain uses its own local repaired order prefix of length `N`; membership need not be identical across domains.

For target-size-controlled final-development and CV-training materialization, DATA7 consumes the authenticated prescribed prefix `R_d[:N]`. It SHALL NOT invoke its independent quota/FPS membership selector to choose a different target set. DATA7 may still construct the fitted preparation/materialization records required by training; the REPAIR2 prefix remains the sole membership authority.

Held-out cross-validation then evaluates the complete protocol. Any later change to `N`, target-membership policy, replay, objective, stopping/LR policy, precision/backend, or another protocol-defining field creates a different protocol and invalidates the previous protocol-matched validation claim.

## 10. Production versus screening-policy qualification

Ordinary campaigns use only the successive-fidelity funnel above.

Release/algorithm qualification MAY retrospectively train the complete qualified
candidate population to full horizon `n` to measure whether the `n1`, `n2`, and
`n3` screens preserve the eventual finalists and winner. Such exhaustive
evidence is qualification-only and SHALL NOT become a default production
workload or a reason to persist eight independent product-scale dataset/graph
states.

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
- a seed population is missing, duplicated, reordered, or candidate-specific;
- epoch continuation parentage cannot be authenticated;
- ordinary success early stopping truncates a required fidelity comparison;
- an implementation invents a non-nominal rescue size;
- target size is inferred from monitor, replay, batch, or pool cardinality;
- duplicated per-rung product-scale state violates bounded-materialization requirements.
