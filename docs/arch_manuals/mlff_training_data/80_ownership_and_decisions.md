# Part VII - Ownership and extension boundaries

## One-generation authority model

The current MLFF workflow has one semantic generation. A record, policy, or artifact is either compatible with that generation or unsupported. Historical selector, repair, migration, and campaign-generation formats do not form alternate current execution paths.

Architecture owns durable structure and scientific/algorithmic invariants. Narrow specifications own exact schemas, policy values, numerical tolerances, failure codes, and module-local runtime behavior. Workplans coordinate proposed transitions and never become product authority merely because an implementation follows them.

The core authority chain is:

```text
source evidence and labels
    -> eligibility / conditions / evidence roles
    -> fold- or final-training domain
    -> DATA7 fitted selection inputs
    -> FEAS1
    -> MVIDX1
    -> MVSEL2
    -> REPAIR2 / MVSTATE2
    -> MVQUAL
    -> TargetSizeStudyPolicy
    -> selected protocol-global target size
    -> domain-local selected target prefixes
    -> training / checkpoint selection
    -> held-out protocol validation
    -> final committee / deployment
    -> calibration / activated locked tests / observable validation
```

There is no branch from this graph to MVSEL1, REPAIR1, MVSTATE-REUSE1, MVMIGRATE, ADAPT-MIGRATE, generated-size rescue, or a second DATA7 membership selector.

## Scientific decision ownership

| Decision or product | Sole current owner | Consumes | Emits | Explicitly does not own |
|---|---|---|---|---|
| source/label identity | DATA2-family source and label contracts | immutable source material | normalized labeled-record identity | partition, selection, training |
| conditions/eligibility | DATA3-family contracts | source records | eligible frames and physical conditions | evidence-role assignment |
| raw features/events | DATA4-family contracts | eligible evidence, profile/provider declarations | partition-independent raw evidence | fitted metrics or target membership |
| evidence roles and fold domains | DATA5 partition contracts | cohorts, independence evidence, purge rules | development/monitor/CV/calibration/test roles and authorized training domains | target ranking |
| descriptors/difficulty inputs | DATA6 contracts | authorized domain evidence, frozen foundation model where applicable | raw/blinded descriptor and prediction products | target membership |
| fitted selection inputs | DATA7 contracts | one authorized fold/final training domain | fitted transforms/metrics, E0 fits, objective/weights, difficulty and condition/provenance inputs | target-membership order or target size |
| full-pool feasibility | FEAS1 | eligible candidates, hard obligations, exact coverage primitives | feasibility/fragility evidence | subset ranking |
| exact sparse neighborhood relation | MVIDX1 | authenticated feature families, scaling, radii, candidate/reference identities | exact sparse relation and forward runtime projection | selector policy |
| target ordering | MVSEL2 | DATA7 inputs, FEAS1/MVIDX1, selector policy | one deterministic progressive order per domain | independent qualification, target size |
| repaired target ordering | REPAIR2 | MVSEL2 order/state, hard obligations, repair policy | one authoritative repaired master order per domain | target-size choice |
| continuation state | MVSTATE2 | authoritative selected prefix and primitive identities | reconstructible compact continuation state | complete candidate marginal arrays, migration |
| independent hard qualification | MVQUAL | authenticated primitive sparse inputs and requested prefixes | independently recomputed hard coverage/obligation evidence | scientific ranking or size choice by itself |
| scientific target size | `TargetSizeStudyPolicy` | common qualified size population and authorized development/model-selection evidence | typed target-size decision | monitor cardinalities, held-out CV evaluation, locked tests |
| target online monitor | `OnlineTargetMonitorPolicy` | DATA5-authorized monitor domain | deterministic common target monitor | target-size population |
| replay monitor | `ReplayMonitorPolicy` | authorized replay evidence | deterministic replay monitor | target-size population |
| training/checkpoint selection | current training/checkpoint specifications | frozen protocol, selected domain-local target prefix, replay, monitors | selected checkpoints and complete evidence | held-out fold as checkpoint controller |
| protocol validation | DATA5/CV + evaluation specifications | frozen protocol and held-out folds | out-of-fold protocol evidence | target-size selection |
| deployment/committee | deployment specifications | admissible final checkpoints, frozen protocol | deployment artifacts and committee identity | post-hoc policy changes |
| uncertainty calibration | calibration owner | predictions from the actual final committee and authorized calibration role | applicability/calibration evidence | refitting the frozen training protocol |
| locked-test activation | activation/evaluation owner | frozen protocol/committee plus explicit activation | locked-test evidence | training, selection, checkpointing, calibration-policy choice |

A narrow specification may refine how its row is realized, but it cannot create a second semantic owner for the decision.

## DATA7 boundary: fitted preparation, not membership

DATA7 is the last fitted-preparation authority before multi-view subset construction. For each authorized fold/final training domain it may fit and publish:

- heterogeneous feature transforms and metrics;
- atomic-reference/E0 fits where applicable;
- training objective and configuration/property weight records;
- training-domain difficulty evidence;
- condition, provenance, event, environment, and diversity inputs needed by subset construction;
- immutable identities linking those products to the domain and protocol.

DATA7 does **not** publish an independent quota/FPS `TrainingSelectionPlan`, a second target-membership ladder, or a target-size decision. Representative coverage, diversity/FPS, environment coverage, protected events, difficulty, and condition balance are expressed as inputs, hard obligations, or objective terms of the one MVSEL2 policy.

This boundary prevents two selectors from producing incompatible notions of the target set while preserving the useful fitted/statistical information accumulated in DATA7.

## One current multi-view chain

### FEAS1 and MVIDX1

FEAS1 diagnoses whether the complete authorized candidate pool can satisfy the frozen hard support and obligation predicates. It does not weaken those predicates to make a requested size feasible.

MVIDX1 owns the exact sparse neighborhood relation used by the selector/repair/qualification family. Scientific identity binds candidate/reference order, feature-family/scaling/radius semantics, and exact sparse content. Execution choices such as worker count, chunking, inversion strategy, mmap layout, or queue depth are reconstructible realization details and cannot change scientific identity.

### MVSEL2

MVSEL2 is the sole current target-ordering authority. It produces one deterministic progressive order per training domain under the frozen lexicographic scientific policy. The implementation may use exact forward/lazy acceleration, but any acceleration must preserve the same authoritative candidate choices and FP64 scientific decision semantics.

### REPAIR2 and MVSTATE2

REPAIR2 is the sole current repair authority. It produces one authoritative repaired order per domain. Candidate rungs are prefix views of that one order; separate rungs are not independently repaired datasets.

MVSTATE2 is authenticated, compact, reconstructible continuation state. It binds the dataset/domain, candidate and family order, MVIDX identity, weights, obligations, correlation units, selector/repair policy, selected prefix, and schema/version identity. It is not a migration envelope for superseded selector state.

### MVQUAL

MVQUAL independently verifies hard coverage and obligation predicates for required prefixes. Selector/repair internal counters are not accepted as independent qualification evidence. MVQUAL may reuse authenticated primitive sparse inputs while recomputing the relevant predicates through its own verification path.

## Target-size authority

### Distinct size concepts

For required training domain \(d\),

$$
N_{\mathrm{available},d}=|\mathcal D_{\mathrm{eligible},d}|.
$$

The nominal scientific target-size population is

$$
\mathcal N_0=\{128,256,512,1024,2048,4096,8192,16384\}.
$$

The common materializable population across all required final-development and cross-validation gradient-training domains is

$$
\mathcal N_M=\left\{N\in\mathcal N_0: N\le \min_d N_{\mathrm{available},d}\right\}.
$$

Independent MVQUAL evidence defines

$$
\mathcal Q=\{N\in\mathcal N_M:\text{all frozen hard requirements pass in every required domain}\}.
$$

The selected target-training size must satisfy

$$
N_{\mathrm{selected}}\in\mathcal Q\subseteq\mathcal N_0.
$$

`N_available`, a monitor cardinality, a replay cardinality, or an implementation batch/budget count can never become `N_selected` through numeric coincidence.

### Domain-local membership and protocol-global size

Each fold/final training domain constructs its own leakage-safe repaired order \(\pi_d\) from only evidence authorized for that domain. For a materializable rung,

$$
D_{d,N}=\pi_d[:N].
$$

The actual frame membership is therefore domain-local. The final `N_selected` is one protocol hyperparameter shared across every required training domain. Cross-validation validates the complete protocol containing that already-frozen size; held-out fold performance does not choose it.

### Hard-coverage monotonicity

Because all rungs are prefixes of one repaired order, increasing \(N\) only adds candidates. Under a fixed exact hard-coverage predicate, satisfaction cannot regress solely because \(N\) grows. Qualified sizes therefore form a contiguous suffix of the materializable ladder.

A pass/fail/pass sequence is an invariant violation in nesting, identity, qualification, or numerical realization. The size funnel must fail closed rather than work around such a pattern.

## Target-size study

`TargetSizeStudyPolicy` is the sole scientific target-size owner. It consumes only authorized development/model-selection evidence and the common target/replay monitoring evidence defined for that role. Held-out CV evaluation folds and locked tests remain unavailable to the size decision.

### Exact fidelity continuation

Each candidate follows one authenticated continuation trajectory:

```text
foundation -> epoch 3 -> epoch 10 -> epoch 30
```

Epoch 10 authenticates the exact epoch-3 model/optimizer/RNG parent; epoch 30 authenticates epoch 10. Candidates use the same foundation, replay semantics, objective, optimizer/LR schedule, exposure policy, precision/backend, and frozen seed set.

Ordinary target-success early stopping is disabled during the size experiment because candidates must reach comparable fidelity boundaries. Hard numerical or scientific failure may still reject a candidate. Normal production/CV stopping resumes after target size is frozen.

### Successive-fidelity funnel

Let \(q=|\mathcal Q|\). Fewer than three qualified sizes is a typed failure. Otherwise the production funnel is:

```text
q >= 3
  epoch 3:  q -> min(q,4)
  epoch 10: <=4 -> 2
  epoch 30: 2 -> 1
```

All candidates use the same frozen training-seed set, and comparisons aggregate paired seed evidence rather than unrelated stochastic realizations.

At epoch 3 and epoch 10, candidates within the frozen practical-equivalence width of 1 meV/Angstrom in the primary target-force metric prefer the smaller size. Early screens need not satisfy the final absolute force-accuracy threshold.

At epoch 30, the two finalists are ranked only by the target-size study metric under the frozen practical-equivalence rule. MVQUAL remains the sole hard target-size eligibility gate; target-threshold, replay, physical-integrity, relaxation, deployment, and other model/protocol acceptance evidence is downstream of the immutable size choice. Numerically invalid trajectories may be excluded because they cannot supply comparable ranking evidence.

### Typed terminal outcomes

The target-size decision is a typed result, at minimum:

```text
selected(N)
insufficient_qualified_sizes
nonconverged_at_fixed_ceiling
```

If 16,384 reaches the final comparison and remains materially better than every smaller numerically valid finalist by more than the frozen practical-equivalence width, the result is `nonconverged_at_fixed_ceiling`. No generated/intermediate rescue size is synthesized.

Exhaustively training all sizes to the final fidelity to measure survivor recall is release/algorithm qualification, not the ordinary scientific production path.

## Bounded materialization and execution ownership

The fixed scientific ladder does not imply eight independent product-scale copies. Per training domain, the intended materialization model is:

```text
one fitted selection-input authority
one exact neighborhood authority
one MVIDX authority
one MVSEL2/REPAIR2 master order
prefix metadata for candidate rungs
MVQUAL evidence for required prefixes
training artifacts only for candidates authorized to train
```

Descriptor, sparse-graph, selector, and repair caches are reconstructible and resource-bounded. Out-of-core inversion, memory mapping, chunking, work queues, NUMA placement, and concurrency are execution strategies. They may change work/span, RSS, VRAM, scratch, or wall time; they may not change scientific membership, hard coverage, rank order, paired-seed comparison, or decision authority.

This bounded representation is an architectural requirement because duplicating product-scale state per rung makes the fixed ladder scale roughly with rung count and is not an acceptable realization of the scientific policy.

## Superseded campaign generations

Current architecture does not provide MVMIGRATE/ADAPT-MIGRATE state machines, legacy construction modes, or alternate v1 selector/repair execution. Artifacts from unsupported generations fail clearly and require campaign re-preparation under the current architecture.

Historical schemas may remain under `docs/history/mlff/` when needed to interpret durable evidence. Their presence never creates current product compatibility requirements.

## Physical-observable validation ownership boundary

Physical-observable calculation is not owned by `mdstats.training_data`. RDF, coordination, neighbor-angle statistics, connectivity, topology statistics, MSD, VACF, spectra, VDOS, diffusion, displacement distributions, current correlations, ionic conductivity, and related physical observables remain authoritative in their respective `mdstats.analysis` modules, specifications, and architecture manuals.

The MLFF layer owns only:

1. choosing an advisory observable-recommendation profile and explicit recipe;
2. constructing an immutable recipe of analysis call IDs and parameters;
3. running the same recipe on matched reference and MLFF collections;
4. preserving verified collection/frame-selection identity, symmetric reference/candidate trajectory-generation identity, runtime/capability identity, warnings, and analysis-owned result identities;
5. binding execution to an explicit statistical role and, where required, a predeclared comparison policy, protocol freeze, and test-activation record;
6. applying comparison and acceptance policies only after those policies are frozen and independently identified.

The MLFF layer does not own the physical numerical algorithms, normalization, neighbor definitions, plateau estimators, spectral transforms, or graph statistics.

Compact structural descriptors used for partitioning or subset construction are workflow inputs. Full physical observables used to judge a trained model remain analysis products. Expensive trajectory observables such as diffusion, VDOS, conductivity, or residence statistics are validation jobs rather than ordinary frame-selection features.

Physical-observable evidence has one explicit role such as `training_diagnostic`, `checkpoint_monitor`, `outer_validation`, `calibration`, `locked_test`, or `external_benchmark`. The role is never inferred from filenames. Realized observables cannot choose their own acceptance policy, and locked-test evidence cannot alter fitting, subset construction, target-size choice, training protocol, checkpoint selection, calibration policy, or acquisition.

## Extension boundaries

A future extension is compatible with this architecture only when it preserves the ownership graph above or explicitly revises it. In particular:

- a new feature/provider may enrich DATA4/DATA6/DATA7 inputs but cannot create a second membership selector;
- a new subset objective may extend MVSEL2 policy only through an explicit scientific design revision that preserves deterministic single-owner ranking;
- a new size-screen metric may enter `TargetSizeStudyPolicy` only with an explicit evidence role and leakage analysis;
- a new acceleration may change execution representation only after exactness/resource qualification against the same scientific semantics;
- a new campaign generation is not entitled to automatic migration support;
- a custom atomwise/auxiliary loss defines a different `TrainingProtocolIdentity` and requires its own qualification rather than silently modifying the current protocol.

## Decision summary

The current MLFF subsystem follows these durable rules:

1. independent evidence remains independent;
2. the complete training protocol is the comparison unit;
3. fitted preparation and target membership are separate authorities;
4. MVSEL2/REPAIR2/MVSTATE2/MVQUAL are the only current multi-view chain;
5. target size and monitor cardinalities are typed, distinct policy families;
6. frame membership is domain-local while selected target size is protocol-global;
7. one repaired master order defines every candidate prefix and hard coverage is monotone with increasing prefix size;
8. the target-size experiment uses development/model-selection evidence, fixed 3/10/30 continuation, paired seeds, and typed non-convergence/failure outcomes;
9. MVQUAL is the sole hard target-size eligibility authority; downstream model/protocol acceptance cannot alter the immutable size choice;
10. locked tests remain sealed until the frozen protocol/committee activation boundary;
11. unsupported old campaigns are re-prepared rather than migrated;
12. execution is resource-bounded and may not alter scientific semantics.
