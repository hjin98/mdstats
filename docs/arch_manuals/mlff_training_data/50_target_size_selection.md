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

Candidate rungs execute through the accepted TRAIN2 runtime and are evaluated through the accepted EVAL2 owners. Expensive numerical training has exactly one substitution seam, strictly below the mdstats owner boundary; configuration resolution, authority construction, materialization, provider and checkpoint authentication, publication, reconciliation, and adoption are production code in every invocation.

## The reducer and the terminal decision

One reducer consumes the screen evidence and advances the experiment. Its outcome is one of:

- **selected** - a size `N_selected` is frozen together with the exact membership `T_selected = pi_train[:N_selected]`;
- **typed scientific terminal failure** - the configured candidate ceiling did not converge, too few candidates qualified, or the surviving candidates were not comparable.

A configured-ceiling nonconvergence is a typed result, not an invitation to invent a rescue size outside the configured ladder.

Ranking is owned by the target-side metric and practical-equivalence policy alone. Inside the practical-equivalence band the **smaller** `N` is preferred, because the scientific question is the smallest sufficient training-set size.

## Currentness and the selected set

`CampaignStore` holds one canonical target-size generation. Its durable regimes are `legacy`, `transitioning`, and `current`; only `current` executes target-size work. Every mutation is one compare-and-set transition against the exact predecessor revision, so an interrupted operation is owned by the persisted transition rather than by the process that began it.

The terminal projection binds `N_selected` and the exact `T_selected` membership digest together; neither may be edited independently, and a reload re-derives the projection from the authenticated reducer state and training order rather than trusting the stored copy. Terminal currentness is always established from the current store revision, never from a caller-supplied snapshot, and a public terminal view is re-authenticated at exposure time so a stale object cannot be published after the store advances.

## Invalidation scope

A change to target-size scientific identity - source or frame membership, canonical numerical labels or their interpretation policy, the candidate ladder or configured ceiling, the evaluation-size ladder, fidelity boundaries, the ordered optimizer-seed set, the training-order policy, the `P_train`/`M3` split or `pi_eval` ordering policy, the common preparation, the metric/practical-equivalence policy, or the foundation/replay identity where it is part of the experiment - replaces the generation. The old selected set stays readable as history and can never re-enter current authority.

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

The current lifecycle is exactly:

```text
doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`prepare` reconstructs the current substrate and cannot select a size. `select-target-size` is the only command that trains candidates and decides `N`. `cross-validate` is the only command that accepts the method. `train-production` is the only command that publishes a fresh production model. `status` and `advance` project this lifecycle from the owning authorities rather than from stage markers.
