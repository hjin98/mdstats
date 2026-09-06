# Part V - Target-size selection and post-selection validation

## Purpose and ownership

This chapter defines how the campaign decides **how much labelled data a training method needs**, and how that decision is validated afterwards without contaminating it.

The current chain is:

```text
canonical frame authority (Part II)
    -> neutral statistical substrate (Part III)
    -> one P_train / M3 target-size development split
    -> one canonical training order pi_train
    -> one canonical evaluation order pi_eval with nested M1 subset M2 subset M3
    -> one common deterministic target-size preparation
    -> paired optimizer-seed screen over candidate sizes
    -> one target-size reducer
    -> N_selected and T_selected = pi_train[:N_selected]
    -> post-selection cross-validation on exactly T_selected
    -> fresh final production on the complete T_selected
    -> currentness-fenced publication
```

Each element has exactly one owner. The reducer is the only authority that may declare a selected size; `CampaignStore` is the only authority that holds the current selected set; post-selection cross-validation is the only authority that accepts or rejects the training *method*; and final production is the only authority that publishes a production model.

There is no alternate selection path. The retired per-domain multi-view chain (compatibility-domain role freezes, full-pool feasibility, exact sparse neighborhood indices, progressive multi-view ordering, repaired master orders, continuation-state families, and independent prefix qualification) is not a current architecture, is not migrated, and is not reachable from any current runtime owner. Workspaces holding that derived state are rejected with an actionable destructive-reset requirement rather than translated; see Part VII.

## Why target size is decided by a screen, not by coverage

The scientific question is empirical: *at what training-set cardinality does the accepted training method stop improving materially on a representative held-in evaluation population?* That is a property of the method, the data distribution, and the optimizer - not of a geometric covering argument over descriptor neighborhoods.

Four principles control the design:

1. one deterministic training order, so candidate sizes are exact nested prefixes and size comparisons are never confounded by resampling;
2. one common preparation shared by every candidate size and optimizer seed, so preparation cannot become a hidden per-size variable;
3. only the ordered optimizer-seed set is the stochastic replicate dimension of the screen;
4. the decision consumes target-side metric evidence alone, and downstream replay, cross-validation, physical, or deployment evidence can never rank or tie-break a size.

## The development split and the two canonical orders

The neutral statistical substrate supplies protected relations - duplicate groups, correlation families, and split exclusions - before any target-size object exists. From it the architecture derives exactly one split:

```text
eligible labelled frames -> P_train (target-training pool) + M3 (evaluation pool)
```

`P_train` is ordered once into `pi_train`. A candidate of nominal size `N` is the exact prefix

$$
T_N = \pi_{\text{train}}[:N].
$$

`M3` is ordered once into `pi_eval`, and the evaluation ladder is the nested family

$$
M_1 \subset M_2 \subset M_3,
$$

taken as direct prefixes of `pi_eval`. Rungs are direct populations, never complements of one another: a rung is evaluated on exactly the frames it names.

Both orders are deterministic functions of the canonical frame authority, the neutral substrate, and the configured target-size policy. Neither depends on any compatibility grouping, label-domain identity, or cross-validation plan.

## The common preparation

One `TargetSizeCommonPreparation` identity is frozen before any candidate trajectory starts. It derives from `P_train` and the configured foundation/training protocol, and it is shared unchanged by every candidate size and every optimizer seed.

It MUST NOT derive from `M1`, `M2`, `M3`, held-out evidence, calibration evidence, locked evidence, or any cross-validation plan. A change to the common preparation is a change to the target-size scientific identity and produces a new generation rather than an in-place edit.

## The paired optimizer-seed screen

For every candidate size `N`, the screen runs the same ordered optimizer-seed set - by current policy the two seeds `[1, 2]` - through the same fidelity ladder:

```text
n1 / M1  ->  n2 / M2  ->  n3 / M3
```

Fidelity boundaries are continuation points, not restarts: model, optimizer, and RNG state continue exactly across `n1 -> n2 -> n3`. Ordinary early stopping may not truncate a required screen boundary, and the seed set is identical at every `N` so a size comparison is never a seed comparison.

### Optimizer-progress normalization

Under a fixed number of dataset passes and a fixed batch size `B`, candidate `N` performs `U_N = ceil(N/B)` optimizer updates per epoch. Holding the nominal learning rate and EMA decay fixed would therefore give larger candidates strictly more optimizer progress - a second independent variable the target-size question never asked about. The screen removes that confound by normalizing amplitude against one configurable reference size:

```text
U_ref   = ceil(N_ref / B)
U_N     = ceil(N / B)
s_N     = U_ref / U_N
lr(N)   = reference_learning_rate * s_N
beta(N) = reference_ema_decay ** s_N
```

so `lr(N) * U_N` and `beta(N) ** U_N` are invariant in `N`. An exact doubling of update geometry halves the learning rate and takes the square root of the EMA decay. Defaults are `N_ref = 1024`, `reference_learning_rate = 1.0e-4`, `reference_ema_decay = 0.99999`, configured under `[target_data.size_convergence.optimizer_normalization]`. The reference size need not be a candidate and need not lie inside the configured ladder. No cap, floor, clipping, survivor-dependent rescaling, or candidate-specific override is applied.

EMA is normalized because EVAL2 evaluates the authenticated configured model state, which is the EMA state whenever EMA is enabled; leaving the decay fixed would compare EMA windows of different effective lengths.

The normalized clock is also the executable loader contract. The qualified
target-size MACE path retains the final partial target batch, uses no
truncating target sampler, and realizes exactly `ceil(N / B)` target batches.
Every exported target `frame_uid` must occur once in that epoch; target frames
are never duplicated merely to fill a batch. A distributed target-size path
that cannot prove the same coverage fails closed rather than silently changing
the frozen `ceil` geometry to floor semantics. Resolved loss, optimizer,
replay, batch, membership, and source-probe facts are recorded in the existing
runtime evidence and are required for continuation/currentness.

Only those two update clocks are normalized. Epoch and fidelity boundaries, the number of dataset passes, the batch size, the LR phase fractions and normalized-progress multiplier shape, Adam/AMSGrad settings, weight decay, gradient clipping, model precision and architecture, acceleration policy, the optimizer-seed set, and the objective/weighting policy are all held fixed across candidates. This is a first-order optimizer-progress normalization, not a claim of exact optimizer-path equivalence: minibatch noise, Adam moment history, and the finite discretization of the analytic LR curve remain accepted residuals.

Each `(N, optimizer_seed)` derives its scale, effective learning rate, and effective EMA decay **once**, from the full candidate geometry, and binds them into the candidate realization. The same realized values are replayed through every rung of `n1 -> n2 -> n3`; they are never recomputed from the active rung or the survivor set, so eliminating a candidate cannot alter a surviving candidate's schedule. Restart validation re-derives the normalization identity and rejects drift, so a stale fixed-LR or differently-normalized checkpoint cannot be resumed.

This normalization is a control of the size-comparison **screen** only. Post-selection cross-validation and fresh final production start from their own optimizer state under their own accepted method policy; screen checkpoints are never production parents.

The normalization policy is the screen's *only* learning-rate and EMA-decay authority. General `[training].learning_rate` and `[training].ema_decay` are post-selection/general training settings; they never reach screen training and are not part of target-size scientific identity. Editing them cannot retire an otherwise identical screen.

The normalization resolver and current-schema reader enforce the reference
domain before digesting or projecting a candidate: `reference_target_size` is a
positive integer, `reference_learning_rate` is a finite real greater than zero,
`reference_ema_decay` is a finite real strictly between zero and one, and the
algorithm identifier is the specification-owned string. Strings, booleans,
fractional values, and non-finite values are rejected rather than coerced.

### What is, and is not, target-size scientific identity

The target-size screen projects the generic optimizer carrier down to the fields that actually change a candidate trajectory. That projection is built once and is used identically by fresh screen construction, restart-authority construction, active-candidate resume validation, and terminal/currentness reconstruction, so those four paths cannot disagree about what the screen's method is.

Target-size scientific identity **retains** the training `batch_size` (which fixes the `ceil(N/B)` update geometry), EMA enabled/disabled, AMSGrad, weight decay, gradient clipping, learned-model dtype and critical precision, device/acceleration policy, and the full-screen `n3` horizon taken from the screen schedule.

It **excludes** the optimizer seed and the candidate-local acceleration realization (both rebound per candidate), general `[training].learning_rate` and `[training].ema_decay` (replaced by the normalization policy), `num_workers` (pure resource realization), the harness-validation `valid_batch_size` (fixed, non-controlling validation geometry that moves no gradient trajectory, LR schedule, checkpoint admissibility, or ranking), and `eval_interval` (not emitted into the candidate MACE configuration at all).

General `[training].ema_decay` is inert for the screen in both EMA states, and the candidate configuration reflects that. With EMA enabled the configuration carries the size-normalized realized beta, which is strongly authenticated. With EMA disabled there is no EMA state to decay, so no decay key is emitted at all - writing the generic value there would put an inert number into scientific replay and let a post-selection-only edit reject an accepted trajectory. Toggling EMA on or off is, by contrast, genuine screen science, because EVAL2 consumes the EMA state whenever EMA is enabled.

Before any of this is resolved, the shared optimizer configuration domain is checked exactly: non-finite learning rates or decays, fractional or boolean batch sizes, and non-boolean EMA/AMSGrad flags are rejected at the canonical owner, before they can reach method identity, a candidate trajectory, a materialization, or a trainer launch.

Consequently a mid-screen worker-count or harness validation batch-width change is not scientific invalidation: a published candidate materialization keeps the exact execution values it was launched with as historical execution provenance, restart re-derives and compares only the scientific configuration content, and `n1 -> n2 -> n3` continuation ancestry stays exact. Real method drift - batch size, dtype, EMA enable, AMSGrad, weight decay, gradient clipping, or the normalization reference LR/EMA - still rejects before training resumes.

Training batch size and the learned-model dtype are P3 *execution* identity, not common-preparation identity. The common preparation fits atomic references, configuration weights, and the fixed harness membership; it consumes neither value, so a batch or precision edit must not retire prepared P1/P2/common science, while it does still retire the P3 execution descendants whose trajectory it changes.

### Objective and weighting ownership

Three weighting owners are kept distinct and are applied at different layers:

- `[objective]` (`TrainingObjectivePolicy`) owns the **global** loss-component coefficients, by default `energy : forces : stress = 1 : 10 : 1`. They are emitted explicitly into every generated MACE configuration - target-size candidate, post-selection CV, and fresh final production - so MACE's own `forces_weight = 100` default is never in effect. It does not own the executable loss *family*, which belongs to the canonical MACE method/architecture owner;
- `[weighting]` (`ConfigurationWeightPolicy`) owns the **per-configuration** weight, exported as `config_weight`;
- per-frame property weights are **local availability masks**: `1.0` when the canonical label is present, `0.0` when it is absent. They are never per-frame copies of the global ratio.

Target-size common preparation and post-selection resolve all three through the same config resolvers, so a user override cannot be honoured by one path and silently ignored by the other. Changing `[objective]` changes common/prepared-generation identity and invalidates its descendants; changing the optimizer-normalization reference values does not, because normalization is P3 execution identity rather than a preparation input.

The executable loss family is MACE's weighted energy+force+stress loss (`loss = "stress"`, `WeightedEnergyForcesStressLoss`), whose native reductions consume `ref.weight` and the local property weights linearly while applying the global coefficients once. MACE's `UniversalLoss` is not used: it scales residuals inside a Huber evaluation, so its per-config property weights are not linearly equivalent to global objective coefficients, and it does not consume `config_weight` at all. The loss family is part of method identity - a checkpoint trained under a different family is not a prefix of a corrected trajectory.

Candidate rungs execute through the accepted TRAIN2 runtime and are evaluated through the accepted EVAL2 owners. Expensive numerical training has exactly one substitution seam, strictly below the mdstats owner boundary; configuration resolution, authority construction, materialization, provider and checkpoint authentication, publication, reconciliation, and adoption are production code in every invocation.

An unaccepted first-rung materialization is execution-local scratch. Cleanup
and first-rung execution for a logical `(N, optimizer_seed)` cell acquire one
exclusive execution-local fence, then recheck authenticated progress before
reclaiming scratch. A concurrent writer therefore cannot have its live
workspace deleted or launch duplicate training; once accepted progress exists,
the waiter reuses that immutable evidence. The fence is not scientific state
and releases when its process exits, so a later retry may reclaim stale scratch
from an interrupted attempt without changing the campaign identity.

## The reducer and the terminal decision

One reducer consumes the screen evidence and advances the experiment. Its outcome is one of:

- **selected** - a size `N_selected` is frozen together with the exact membership `T_selected = pi_train[:N_selected]`;
- **typed scientific terminal failure** - too few candidates qualified, or the surviving candidates were not comparable.

Ranking is owned by the target-side metric and practical-equivalence policy alone. Inside the practical-equivalence band the **smaller** `N` is preferred, because the scientific question is the smallest sufficient training-set size.

The configured ladder ceiling is a **practical budget limit**, not a requirement that convergence occur below it. The terminal decision therefore distinguishes two selected outcomes:

- **evidence-supported truncation** - a smaller size is practically equivalent to, or better than, the larger finalist, so there is direct evidence to stop below the ceiling. This is an ordinary selection with no warning;
- **practical-ceiling selection** - the largest configured candidate remains materially superior to every other successful terminal finalist by more than the practical-equivalence threshold. `Nmax` is then selected, and the result carries the non-blocking warning code `nonconverged_at_configured_ceiling`: the configured practical ceiling is the best evaluated permitted size, while target-size convergence was not demonstrated within the configured ladder. It does not claim that `Nmax` is asymptotically converged, and no unconfigured rescue size is invented.

The warning is diagnostic metadata on a valid selection, carried in `terminal_reason_codes`. There is no separate selected-with-warning status: a selected-at-ceiling result commits through the ordinary `TERMINAL_SELECTED` transition, binds `N_selected`/`T_selected` exactly once, admits post-selection cross-validation, and leaves `cross-validate` as the next admissible command. CLI status and the derived result view surface the warning alongside the frozen size.

Genuinely insufficient comparison stays blocking. Too few complete comparable terminal candidates, malformed/missing/duplicated/reordered/lineage-incompatible boundary evidence, and authenticated numerical failures that leave the reducer unable to make the required comparison remain typed failures; the reducer never fabricates a ceiling selection from an incomplete terminal comparison.

The terminal-decision rule participates in P2 policy identity (`practical_equivalence_then_practical_ceiling.v2`). Evidence reduced under the retired blocking-ceiling rule stays historical and is never relabelled in place as a selection.

## Currentness and the selected set

`CampaignStore` holds one canonical target-size generation. Its durable regimes are `legacy`, `transitioning`, and `current`; only `current` executes target-size work. Every mutation is one compare-and-set transition against the exact predecessor revision, so an interrupted operation is owned by the persisted transition rather than by the process that began it.

The terminal projection binds `N_selected` and the exact `T_selected` membership digest together; neither may be edited independently, and a reload re-derives the projection from the authenticated reducer state and training order rather than trusting the stored copy. Terminal currentness is always established from the current store revision, never from a caller-supplied snapshot, and a public terminal view is re-authenticated at exposure time so a stale object cannot be published after the store advances.

## Invalidation scope

A change to target-size scientific identity - source or frame membership, canonical numerical labels or their interpretation policy, the candidate ladder or configured ceiling, the evaluation-size ladder, fidelity boundaries, the ordered optimizer-seed set, the training-order policy, the `P_train`/`M3` split or `pi_eval` ordering policy, the common preparation, the metric/practical-equivalence policy, the terminal-decision policy, the training objective and its weighting ownership, or the foundation/replay identity where it is part of the experiment - replaces the generation. The old selected set stays readable as history and can never re-enter current authority.

Changes that are *not* target-size identity invalidate only their own descendants:

- advisory provenance grouping or report presentation invalidates only the advisory evidence that depends on it, and never the frame UID, the canonical label identity, the neutral partition, or the target-size result;
- cross-validation-only settings such as fold count and partition seed invalidate cross-validation and its descendants, and leave `N_selected`/`T_selected` byte-identical;
- production-only budget or runtime policy invalidates only final-production descendants.

## Post-selection cross-validation

Cross-validation starts only after the terminal selection is frozen, and it consumes exactly `T_selected` - complete coverage, no unselected sibling frame, no held-out outer frame.

It validates the **training method**, not the size:

- the configured fold count `K >= 2` and every required fold of every required CV seed must pass the configured target-only acceptance predicate; there is no mean, majority, best-seed, partial, `K = 0` or `K = 1` authorization;
- the full P1 split-exclusion and correlation-family constraints continue to hold inside fold assignment;
- fold-local preparation, training, checkpoint selection, and replay admissibility may never see that fold's held-out outer target set, and the fold representative freezes before held-out outer evaluation;
- replay training exposure and the TRUE_DFT replay admissibility monitor remain distinct concerns, and TRUE_DFT replay contributes no ranking, tie-break, fold, or seed credit;
- a cross-validation failure is a methodological result: `N_selected` and its evidence are unchanged, and final production is simply not authorized. If cross-validation shows that a materially different training method is required, that changed method needs a **new** target-size experiment, because the method whose convergence was measured has changed.

Supported training modes remain exactly `scratch`, `naive_fine_tuning`, and `multihead_replay`; the canonical post-selection heads remain `target_head` and `pt_head`; and the foundation checkpoint head remains a separate foundation-owned concept. Method, foundation, replay, and content identity all fail closed.

## Fresh final production

Final production starts fresh from the accepted foundation/initialization with fresh optimizer, RNG, and run state. It trains on the complete exact `T_selected`, under the cross-validation-accepted method, for the configured `[training].max_num_epochs` - an independent production horizon that is deliberately unrelated to the screen's `n3`.

Frozen `M3` evidence may remain development/model-selection evidence. Final authorization and publication remain currentness-fenced and restart-authenticatable: a reopened campaign reauthenticates the selected binding, the cross-validation acceptance, and the final publication identity before exposing any of them as current.

## Public command surface

The current lifecycle, including configuration initialization, is exactly:

```text
init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`prepare` reconstructs the current substrate and cannot select a size. `select-target-size` is the only command that trains candidates and decides `N`. `cross-validate` is the only command that accepts the method. `train-production` is the only command that publishes a fresh production model. `status` and `advance` project this lifecycle from the owning authorities rather than from stage markers.
