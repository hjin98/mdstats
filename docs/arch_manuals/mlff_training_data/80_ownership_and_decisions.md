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
    -> P_train / M3 target-size development split
    -> canonical training order pi_train and evaluation ladder M1 subset M2 subset M3
    -> one common target-size preparation
    -> paired optimizer-seed screen
    -> target-size reducer
    -> N_selected and T_selected
    -> post-selection cross-validation on exactly T_selected
    -> fresh final production on the complete T_selected
    -> currentness-fenced publication
```

There is no branch from this graph to a retired per-domain multi-view selection
chain, a generated-size rescue, or a second membership selector. Retired derived
target-size state is rejected with an actionable destructive reset requirement
rather than migrated.

## Scientific decision ownership

| Decision or product | Sole current owner | Consumes | Emits | Explicitly does not own |
|---|---|---|---|---|
| source/label identity | DATA2-family source and label contracts | immutable source material | normalized labeled-record identity | partition, selection, training |
| conditions/eligibility | DATA3-family contracts | source records | eligible frames and physical conditions | evidence-role assignment |
| raw features/events | DATA4-family contracts | eligible evidence, profile/provider declarations | partition-independent raw evidence | fitted metrics or target membership |
| evidence roles and fold domains | DATA5 partition contracts | cohorts, independence evidence, purge rules | development/monitor/CV/calibration/test roles and authorized training domains | target ranking |
| descriptors/difficulty inputs | DATA6 contracts | authorized domain evidence, frozen foundation model where applicable | raw/blinded descriptor and prediction products | target membership |
| fitted selection inputs | DATA7 contracts | one authorized fold/final training domain | fitted transforms/metrics, E0 fits, objective/weights, difficulty and condition/provenance inputs | target-membership order or target size |
| target-size development split | target-size experiment definition | canonical frame authority, neutral substrate, target-size policy | one `P_train`/`M3` split | training order, size choice |
| canonical training order | `pi_train` owner | the split plus the configured training-order policy | one deterministic order whose prefixes are candidate subsets | evaluation populations, size choice |
| canonical evaluation ladder | `pi_eval` owner | the split plus the configured evaluation-order policy | nested direct populations `M1 subset M2 subset M3` | training membership, size choice |
| common target-size preparation | `TargetSizeCommonPreparation` | `P_train` and the frozen foundation/training protocol | one preparation identity shared by every size and seed | any per-size or per-seed variation |
| scientific target size | the one target-size reducer | paired optimizer-seed screen evidence at matched fidelity | typed terminal outcome: `N_selected` or typed scientific failure | monitor cardinalities, held-out CV evaluation, locked tests |
| current selected set | `CampaignStore` terminal projection | authenticated reducer state and training order | `N_selected` bound to the exact `T_selected` membership digest | re-deciding the size, post-selection acceptance |
| post-selection method acceptance | post-selection cross-validation owner | exactly `T_selected`, protected relations, configured `K >= 2` and CV seeds | all-required-fold target-only acceptance verdict | choosing or changing `N_selected` |
| fresh final production | final-production owner | the accepted method and the complete exact `T_selected` | published production run under `[training].max_num_epochs` | target-size or CV authority |
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

DATA7 does **not** publish an independent quota/FPS membership decision, a second target-membership ladder, or a target-size decision. Representative coverage, diversity/FPS, environment coverage, protected events, difficulty, and condition balance are expressed as inputs to the one canonical training order.

After the target size is frozen, post-selection materialization consumes exactly `T_selected = pi_train[:N_selected]`. A `TrainingSelectionPlan` used to record that materialization is a consumer record, not an independent selector.

This boundary prevents two selectors from producing incompatible notions of the target set while preserving the useful fitted/statistical information accumulated in DATA7.

## Target-size authority

### Distinct size concepts

Let \(N_{\mathrm{available}}=|P_{\mathrm{train}}|\) be the size of the target-training pool. The candidate ladder is configured, not frozen in schema: a contiguous power range with an explicit configured ceiling,

$$
\mathcal N_0=\{2^{p}: p_{\min}\le p\le p_{\max}\}.
$$

The materializable population is

$$
\mathcal N_M=\{N\in\mathcal N_0: N\le N_{\mathrm{available}}\},
$$

and the qualified population \(\mathcal Q\subseteq\mathcal N_M\) is the subset admitted by the configured target-size policy for the current experiment definition. The selected size must satisfy \(N_{\mathrm{selected}}\in\mathcal Q\).

`N_available`, a monitor cardinality, a replay cardinality, or an implementation batch/budget count can never become `N_selected` through numeric coincidence. There is no hidden scientific ceiling: the ladder and its ceiling are configuration.

### One membership, one protocol-global size

Every candidate is an exact prefix of the one canonical training order,

$$
T_N=\pi_{\mathrm{train}}[:N],
$$

so frame membership is a global property of the experiment rather than a per-domain construction. `N_selected` is one protocol hyperparameter, and the exact membership `T_selected` is frozen with it. Post-selection cross-validation validates the training method on that already-frozen set; held-out fold performance does not choose it.

Because all candidates are prefixes of one order, increasing `N` only adds frames. A qualification predicate evaluated on those prefixes therefore cannot regress solely because `N` grows, and a pass/fail/pass sequence is an invariant violation that must fail closed.

## Target-size screen

The reducer is the sole scientific target-size owner. It consumes only authorized target-side development/model-selection evidence. Replay semantics and monitor identity may remain bound through the frozen training protocol, but replay metric values are diagnostics and cannot rank, qualify, reject, or tie-break target sizes. Post-selection cross-validation folds and locked tests remain unavailable to the size decision.

### Exact fidelity continuation

Each candidate follows one authenticated continuation trajectory:

```text
foundation -> n1 / M1 -> n2 / M2 -> n3 / M3
```

Each boundary authenticates the exact model/optimizer/RNG parent of its predecessor. `0 < n1 < n2 < n3` are the screening boundaries, while fresh production uses an independent positive `[training].max_num_epochs` with no required ordering against `n3`. Candidates share the same foundation, replay semantics, objective, optimizer/LR schedule, exposure policy, precision/backend, common preparation, and ordered seed set. That seed set comes from the `seeds` field of the sole enabled training method; current generated campaigns default it to `[1, 2]`. The target-size policy serializes the ordered set and does not invent a second seed convention.

At every boundary the endpoint itself is authoritative: `S(N,n1)`, `S(N,n2)`, and `S(N,n3)` are evaluated at matched fidelity on the direct rung population `M1`, `M2`, `M3`. A better earlier checkpoint cannot replace the prescribed endpoint. This is distinct from post-selection production checkpoint selection, where `N_selected` is fixed and the checkpoint epoch may be optimized over the admissible trajectory.

Ordinary target-success early stopping is disabled during the size experiment because candidates must reach comparable fidelity boundaries. Every expected candidate/seed produces exactly one stage outcome: strict successful endpoint evidence, or explicit authenticated candidate-specific numerical/scientific failure evidence. Generic execution/resource/input/schema/lineage failures remain campaign errors. Normal production stopping resumes after the target size is frozen.

### Public orchestration boundary

The campaign CLI is a projection of existing scientific/execution authorities, not an additional persistent lifecycle authority. Its stable lifecycle is:

```text
doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`prepare` reconstructs the current substrate and cannot select a size, train a candidate, run the reducer, or rank anything. `select-target-size` is the sole public owner of the restartable `n1/n2/n3` controlled-fidelity loop.

Once `N_selected` is frozen, `cross-validate` and `train-production` are the two public post-selection owners. Both re-establish the current selection through the canonical terminal loader in the same invocation, so neither a caller-held object nor a persisted descendant is ever current authority. `cross-validate` owns the complete selected-only K-fold plan and the target-only acceptance verdict; `train-production` owns fresh full-`T_selected` training under the method that verdict accepted. Each materializes exactly the workload its own plan authorizes, so there is no separate `materialize` step and no second preflight boundary. `status` and `advance` derive the lifecycle from those same owners and never write a second scientific state machine.

### Successive-fidelity funnel

Let \(q=|\mathcal Q|\). Fewer than three qualified sizes is a typed failure. Otherwise the production funnel is:

```text
q >= 3
  n1 / M1: q -> min(q,4)
  n2 / M2: <=4 -> 2
  n3 / M3: 2 -> 1
```

All candidates use the same authenticated ordered training-seed set, and comparisons aggregate paired seed evidence rather than unrelated stochastic realizations. Missing, duplicated, reordered, or candidate-specific seed populations invalidate the state.

At `n1` and `n2`, the configurable coarse practical-equivalence width defaults to 1 meV/Angstrom in the primary target-force metric, and candidates inside that band prefer the smaller size. The independently configurable final width also defaults to 1 meV/Angstrom for `n3` ranking and configured-ceiling material superiority. Both positive finite values are policy-identity fields, not frozen schema constants. Early screens need not satisfy the final absolute force-accuracy threshold.

At `n3`, the two finalists are ranked only by the target-side metric under the frozen practical-equivalence rule. Target-threshold, replay, physical-integrity, relaxation, deployment, and other model/protocol acceptance evidence is downstream of the immutable size choice. Only complete paired successful candidates are rankable; authenticated trajectory failures remain explicit evidence and replay scores cannot affect ranking or tie-breaking.

### Typed terminal outcomes

The target-size decision is a typed result, at minimum:

```text
selected(N)
insufficient_qualified_sizes
insufficient_comparable_candidates
nonconverged_at_configured_ceiling
```

`insufficient_comparable_candidates` records the failed fidelity stage and authenticated candidate/seed failure reasons when authenticated numerical/scientific trajectory failure leaves too few complete paired candidates for a required comparison. Input/lineage/programming defects remain fail-closed exceptions.

If the configured ceiling reaches the final comparison and remains materially better than every smaller complete finalist by more than the configured final practical-equivalence width, the result is `nonconverged_at_configured_ceiling`. No generated or intermediate rescue size is synthesized.

Exhaustively training all sizes to the final fidelity to measure survivor recall is release/algorithm qualification, not the ordinary scientific production path.

## Bounded materialization and execution ownership

The configured candidate ladder does not imply one independent product-scale copy per rung. Per training domain, the intended materialization model is:

```text
one fitted selection-input authority
one canonical training order pi_train
one common target-size preparation
prefix metadata for candidate rungs
training artifacts only for candidates authorized to train
```

Descriptor, feature, and preparation caches are reconstructible and resource-bounded. Out-of-core inversion, memory mapping, chunking, work queues, NUMA placement, and concurrency are execution strategies. They may change work/span, RSS, VRAM, scratch, or wall time; they may not change scientific membership, hard coverage, rank order, paired-seed comparison, or decision authority.

This bounded representation is an architectural requirement because duplicating product-scale state per rung makes the fixed ladder scale roughly with rung count and is not an acceptable realization of the scientific policy.

## Superseded campaign generations

Current architecture does not provide migration state machines, legacy construction modes, or alternate retired selection execution. A workspace holding retired derived target-size state is detected before any semantic deserialization, candidate or checkpoint reuse, or descendant publication, and is refused with an explicit destructive reset/reprepare requirement. Retired records are quarantined under a namespace no current loader reads rather than translated.

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
- a new training-order feature may extend the `pi_train` policy only through an explicit scientific design revision that preserves one deterministic order;
- a new size-screen metric may enter the target-size policy only with an explicit evidence role and leakage analysis;
- a new acceleration may change execution representation only after exactness/resource qualification against the same scientific semantics;
- a new campaign generation is not entitled to automatic migration support;
- a custom atomwise/auxiliary loss defines a different `TrainingProtocolIdentity` and requires its own qualification rather than silently modifying the current protocol.

## Decision summary

The current MLFF subsystem follows these durable rules:

1. independent evidence remains independent;
2. the complete training protocol is the comparison unit;
3. fitted preparation and target membership are separate authorities;
4. one canonical training order and one common preparation define every candidate;
5. target size and monitor cardinalities are typed, distinct policy families;
6. frame membership and the selected target size are both protocol-global and frozen together;
7. every candidate is an exact prefix of the one training order, so candidate sets are nested by construction;
8. the target-size experiment uses development/model-selection evidence, configured `n1/n2/n3` continuation on a screen-local horizon `n3`, paired seeds, and typed non-convergence/failure outcomes; fresh selected-size production owns the independent horizon `n`;
9. the reducer is the sole target-size authority; post-selection cross-validation accepts the method and can never re-choose the size;
10. locked tests remain sealed until the frozen protocol/committee activation boundary;
11. retired derived target-size state is rejected before reuse and re-prepared rather than migrated;
12. execution is resource-bounded and may not alter scientific semantics.
