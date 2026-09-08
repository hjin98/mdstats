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
    -> +-- optional: paired optimizer-seed automatic diagnostic
    |   |             (screen + reducer -> a *recommended* size)
    |   |
    |   +-> operator-owned provisional design
    |         N_provisional, H_cv, H_prod   (mutable, freezes nothing)
    |
    -> cross-validate admission
         -> frozen N_selected, T_selected = pi_train[:N_selected],
            and both effective role horizons
    -> post-selection cross-validation on exactly T_selected
    -> fresh final production on the complete T_selected
    -> currentness-fenced publication
```

Each element has exactly one owner. The **operator** decides the target size and the two role horizons; the automatic screen's reducer produces evidence and, when its comparison is valid, a *recommendation*; **`cross-validate` admission** is the only authority that freezes a downstream design; `CampaignStore` is the only authority that holds the current provisional or frozen design; post-selection cross-validation is the only authority that accepts or rejects the training *method*; and final production is the only authority that publishes a production model.

### Why the screen recommends rather than decides

The screen measures target-force RMSE at three short epoch boundaries under one configured protocol. Fixed-optimizer and normalized-optimizer experiments on this campaign showed that candidate size and short-horizon optimizer progress are strongly coupled, and that reasonable optimizer controls can materially change the ranking across sizes. That evidence does not establish which control was closer to long-horizon truth, that the size/error relationship is linear, that an early ranking predicts a long training trajectory, or that force RMSE predicts the stability of the resulting potential in molecular dynamics.

So the product does not let a short-horizon proxy masquerade as a conclusive target-size authority. The screen is retained because its empirical content is genuinely useful; its *scientific interpretation* is narrowed to what it measured. Evidence strength increases monotonically downstream:

```text
automatic screening   -> target-size heuristic / diagnostic evidence
post-selection CV     -> validation of the training method on the chosen data
full production       -> long-horizon realization of the chosen design
MD qualification      -> evidence about actual potential behavior
```

No target-size screening metric is evidence of final MD quality.

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

## The reducer and the diagnostic outcome

One reducer consumes the screen evidence and advances the diagnostic. Its outcome is one of:

- **recommendation** - a size `N` together with the exact membership identity of `pi_train[:N]`;
- **typed scientific no-recommendation** - too few candidates qualified, or the surviving candidates were not comparable.

Neither outcome freezes anything, and neither is campaign-terminal. A diagnostic that cannot make its configured comparison is a conclusion about *the diagnostic*; it leaves any existing provisional choice untouched and does not prohibit choosing a qualified candidate explicitly. Its evidence is persisted, rendered, and reused by a later `--auto`.

Ranking is owned by the target-side metric and practical-equivalence policy alone. Inside the practical-equivalence band the **smaller** `N` is preferred, because the scientific question is the smallest sufficient training-set size.

The configured ladder ceiling is a **practical budget limit**, not a requirement that convergence occur below it. The terminal decision therefore distinguishes two selected outcomes:

- **evidence-supported truncation** - a smaller size is practically equivalent to, or better than, the larger finalist, so there is direct evidence to stop below the ceiling. This is an ordinary selection with no warning;
- **practical-ceiling recommendation** - the largest configured candidate remains materially superior to every other successful terminal finalist by more than the practical-equivalence threshold. `Nmax` is then recommended, and the result carries the non-blocking warning code `nonconverged_at_configured_ceiling`: the configured practical ceiling is the best evaluated permitted size, while target-size convergence was not demonstrated within the configured ladder. It does not claim that `Nmax` is asymptotically converged, and no unconfigured rescue size is invented.

The warning is diagnostic metadata on a valid recommendation, carried in `terminal_reason_codes`. There is no separate recommended-with-warning status: a ceiling recommendation commits through the ordinary diagnostic-completion transition and, if it is adopted, becomes the provisional `N` like any other. CLI status, the derived result view, and the portable report surface the warning alongside the recommendation.

Genuinely insufficient comparison stays blocking. Too few complete comparable terminal candidates, malformed/missing/duplicated/reordered/lineage-incompatible boundary evidence, and authenticated numerical failures that leave the reducer unable to make the required comparison remain typed failures; the reducer never fabricates a ceiling recommendation from an incomplete terminal comparison.

The terminal-decision rule participates in P2 policy identity (`practical_equivalence_then_practical_ceiling.v2`). Evidence reduced under the retired blocking-ceiling rule stays historical and is never relabelled in place.

## The provisional design, and the freeze

The prepared generation is expensive and deliberately reusable, so the operator may want several longer-horizon experiments from it - the same method and the same training order at different amounts of target data. The provisional design is therefore an **ordered collection of distinct qualified sizes**, not a single choice:

```text
D_provisional = [ entry_1, entry_2, ..., entry_k ]     unique by N, first-insertion order

entry_i:
  N_provisional      a configured qualified candidate size
  T_provisional      never stored; always pi_train[:N_provisional], with its digest
  selection_source   manual | auto_recommendation   (provenance, not a variable)
  H_cv               cross-validation max epochs for this size
  H_prod             final-production max epochs for this size
```

`select-target-size <N>` merges one complete entry through the ordinary CampaignStore compare-and-set boundary: a size not yet in the design is **appended**, and a size already in it has its **complete entry replaced in place**, keeping its list position. A second distinct `N` therefore adds an experiment rather than erasing the one already requested. Two entries for one `N` in authoritative state are corruption, not something to deduplicate. The empty collection is the canonical unselected state - there is no `N = undefined` placeholder - and `select-target-size --reset` returns to it pre-freeze without touching the prepared generation or any valid diagnostic evidence.

Each entry is *complete when it is set*: both horizons are resolved to explicit values at that moment from `[post_selection.cv].max_num_epochs` and `[training].max_num_epochs`, or from the invocation's own `--horizon-cv` / `--horizon` overrides. Later edits to `campaign.toml` therefore cannot silently mutate an entry that already exists, untouched sibling entries never drift, and a CLI override never becomes a sticky default. Reselecting a size deliberately re-resolves every omitted horizon for the new invocation. The CLI never writes `campaign.toml`.

An adopted automatic recommendation goes through that same merge owner. The automatic path has no collection authority of its own: it cannot clear, reorder, or overwrite a sibling entry the operator chose by hand.

`cross-validate` admission is the freeze, and it freezes the **whole collection atomically**. It reloads and authenticates the one prepared generation, revalidates every proposed `N` against the current qualified candidate set, re-derives every `T_N = pi_train[:N]` from the P2 training order, and publishes the complete ordered design - every `N_selected`, its exact membership, and both effective role horizons - as immutable ancestry in one transition, before any numerical CV work. One unauthenticatable member rejects the entire admission; there is no partial freeze and no quiet reduction to the subset that still validated. No automatic-screen execution head or reducer participates: a campaign that never ran the diagnostic freezes by exactly the same path as one that did. After the freeze, `select-target-size` in any form refuses to change the design.

### The full frozen entry, and the target binding

The operator chooses `(N, H_cv, H_prod)` together, but identity does not collapse them - and the separation has to survive being written down, not just being intended.

The **full frozen entry** is the immutable design and audit record: `N`, exact membership and training-order identity, both role horizons, and selection provenance. It may carry its own digest for state authentication, and that digest is what detects a tampered horizon or forged provenance.

The **target binding** is its role-neutral scientific projection, and it is what every P5/P7 descendant descends from:

```text
TargetBinding_i   = generation + accepted P1/P2 prepared lineage + N_i + exact T_i + training-order identity
CV_i              = TargetBinding_i + method identity + CV policy (which contains H_cv_i) + CV plan/evidence ancestry
Production_i      = TargetBinding_i + method identity + accepted CV_i ancestry + production policy (which contains H_prod_i)
```

So editing the production budget cannot invalidate accepted cross-validation evidence; editing the CV budget does not move the production policy itself, and reaches final production only through the accepted CV ancestry it names, which is correct. Selection provenance is excluded from every numerical identity: the same `N` on the same substrate is the same experiment whether it was chosen by hand or adopted from the screen. Sibling sizes, list position, and any whole-collection digest are excluded too - a per-size identity that moved when another size joined the design would make the multi-size feature self-defeating.

The binding must therefore not be derived from the full frozen entry's digest, because that digest contains exactly the fields the binding is defined to exclude. This was a real defect in the scalar-selection predecessor, whose binding embedded the whole frozen record and so let `H_prod` and provenance contaminate every descendant transitively. Descendants published under that predecessor schema keep their own bytes and stay current under their own exact ancestry; new designs use the corrected decomposition, and no compatibility argument reintroduces the coupling.

## Currentness

`CampaignStore` holds one canonical target-size generation. Its durable regimes are `legacy`, `transitioning`, and `current`; only `current` executes target-size work. Every mutation is one compare-and-set transition against the exact predecessor revision, so an interrupted operation is owned by the persisted transition rather than by the process that began it.

The diagnostic projection binds the recommended `N` and the exact membership digest it names together; neither may be edited independently, and a reload re-derives the projection from the authenticated reducer state and training order rather than trusting the stored copy. Diagnostic currentness is always established from the current store revision, never from a caller-supplied snapshot, and a public diagnostic view is re-authenticated at exposure time so a stale object cannot be published after the store advances. The same holds for a frozen selection: its membership is re-derived from the P2 training order on every exposure.

An automatic diagnostic may run for hours. It captures the selection state it intends to update before it starts, and installs its recommendation only if that state is unchanged when it finishes. If a human made an explicit choice, or `cross-validate` froze the design, in the meantime, the newer decision wins: the diagnostic evidence and its report are still committed and reusable, and the CLI says the recommendation was computed but not installed.

## The portable diagnostic report

Every completed automatic diagnostic - with or without a recommendation - writes one self-contained Markdown report under the campaign `results/` tree at a stable per-generation filename. It records the generation and experiment/execution/head/reducer identities; the candidate sizes, evaluation populations, fidelity boundaries and optimizer seeds; the ranking metric and unit, the seed aggregation, the practical-equivalence rule and the funnel rule; the optimizer-normalization reference policy and each candidate's updates per epoch, effective learning rate and effective EMA decay; every completed boundary's per-seed RMSE, paired mean, success/failure and survive/eliminate outcome; the filtering decision tree projected from the reducer's committed outcome history; the recommendation or explicit no-recommendation result with any warning codes; and the scientific-limitation statement above.

The report is derived, rebuildable and non-authoritative. It never re-ranks anything, and no code reads a recommendation or a selected size back out of it.

## Invalidation scope

A change to target-size scientific identity - source or frame membership, canonical numerical labels or their interpretation policy, the candidate ladder or configured ceiling, the evaluation-size ladder, fidelity boundaries, the ordered optimizer-seed set, the training-order policy, the `P_train`/`M3` split or `pi_eval` ordering policy, the common preparation, the metric/practical-equivalence policy, the terminal-decision policy, the training objective and its weighting ownership, or the foundation/replay identity where it is part of the experiment - replaces the generation. The old selected set stays readable as history and can never re-enter current authority.

Changes that are *not* target-size identity invalidate only their own descendants:

- advisory provenance grouping or report presentation invalidates only the advisory evidence that depends on it, and never the frame UID, the canonical label identity, the neutral partition, or the target-size result;
- cross-validation-only settings such as fold count and partition seed invalidate cross-validation and its descendants, and leave every `N_selected`/`T_N` byte-identical;
- adding, revising, or removing one size before the freeze changes only that entry; after the freeze the design is immutable, and a sibling size never participates in another size's numerical identity;
- neither provisional nor frozen role horizon participates in automatic target-size diagnostic identity, so steering them never invalidates screen evidence;
- production-only budget or runtime policy invalidates only final-production descendants.

## Post-selection cross-validation

Cross-validation performs the whole-collection freeze at its own admission boundary and then runs the existing methodology once per frozen size, in frozen selection order, each consuming exactly its own `T_N` - complete coverage, no unselected sibling frame, no held-out outer frame, and no frame borrowed from another selected size.

The size dimension sits *outside* everything below it: fold construction, seeds, evaluation, and the acceptance predicate are unchanged, and there is no cross-size reducer. Outer iteration over sizes is serial and shares the one effective resource allocation the existing fold/seed/MACE/library concurrency already owns; no new scheduler exists and no size claims the machine independently. Campaign cross-validation is accepted only when **every** frozen size is accepted; a rejected size stays visibly rejected and no selected size is ever silently dropped.

It validates the **training method**, not the size:

- the configured fold count `K >= 2` and every required fold of every required CV seed must pass the configured target-only acceptance predicate; there is no mean, majority, best-seed, partial, `K = 0` or `K = 1` authorization;
- the full P1 split-exclusion and correlation-family constraints continue to hold inside fold assignment;
- fold-local preparation, training, checkpoint selection, and replay admissibility may never see that fold's held-out outer target set, and the fold representative freezes before held-out outer evaluation;
- replay training exposure and the TRUE_DFT replay admissibility monitor remain distinct concerns, and TRUE_DFT replay contributes no ranking, tie-break, fold, or seed credit;
- a cross-validation failure is a methodological result: the frozen design and its evidence are unchanged, and final production is simply not authorized for any size. If cross-validation shows that a materially different training method is required, that changed method needs a **new** target-size experiment, because the method whose convergence was measured has changed;
- valid completed sibling evidence stays reusable on retry under the existing currentness and restart rules.

Supported training modes remain exactly `scratch`, `naive_fine_tuning`, and `multihead_replay`; the canonical post-selection heads remain `target_head` and `pt_head`; and the foundation checkpoint head remains a separate foundation-owned concept. Method, foundation, replay, and content identity all fail closed.

## Fresh final production

Admission is a **collection-wide barrier**. Before any new production job starts, the complete frozen design is authenticated and every selected size must hold current accepted cross-validation ancestry under its own binding and its own `H_cv`. If any size is missing, stale, corrupt, incomplete, or rejected there, the invocation starts no production job for *any* size and names every known blocker. Immutable evidence from an earlier attempt keeps whatever currentness its own identity earns; the barrier exists so that an all-sizes experiment cannot quietly become the subset that happened to succeed.

After preflight, each frozen size starts fresh from the accepted foundation/initialization with fresh optimizer, RNG, and run state. It trains on that size's complete exact `T_N`, under the cross-validation-accepted method for *that* size, for **its own** frozen production horizon - an independent budget that is deliberately unrelated to the screen's `n3` and to the frozen CV horizon. Each size publishes one binding-scoped final-production decision. No size may consume another size's membership, horizons, CV plan or acceptance, run evidence, pointer, final plan, or publication, and there is no cross-size final-publication committee.

Frozen `M3` evidence may remain development/model-selection evidence. Final authorization and publication remain currentness-fenced and restart-authenticatable: a reopened campaign reauthenticates each selected binding, its cross-validation acceptance, and its final publication identity before exposing any of them as current. If one size is complete and another fails or is interrupted, the frozen design is unchanged, the complete size's evidence stays reusable, only work the existing restart owners deem incomplete or stale is recomputed, and campaign production stays incomplete until every size closes.

### Where the multi-size experiment ends

Once every selected size has a current final publication, a multi-size training experiment is **complete and not release-qualified**. Several final products exist and this revision authorizes no rule for choosing one, so `advance` offers no further consequential command, `qualification status` reports the boundary read-only, and consequential qualification commands fail closed before any attempt or locked evidence is created or revealed. A one-size design keeps the existing qualification path unchanged. Choosing between sizes is a release decision that needs its own explicit design authority; it is deliberately not made here by defaulting to the first, the last, the recommended, or the best-scoring size.

## Public command surface

The current lifecycle, including configuration initialization, is exactly:

```text
init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`prepare` reconstructs the current substrate and cannot select a size. `select-target-size <N>` sets the provisional design and trains nothing; `select-target-size --auto` runs or reuses the optional automatic diagnostic and adopts its recommendation; a bare `select-target-size` is invalid, and `<N>` and `--auto` are mutually exclusive. `cross-validate` freezes the design and is the only command that accepts the method. `train-production` is the only command that publishes a fresh production model. `status` and `advance` project this lifecycle from the owning authorities rather than from stage markers, and `advance` stops at the target-size decision boundary rather than inventing a choice or silently running the diagnostic.
