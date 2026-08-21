# Part V - Multi-view target subset and target-size architecture

## Purpose and ownership

This chapter defines how an authorized fold/final training domain becomes one deterministic nested family of target-training subsets and how one protocol-global target size is selected without consuming held-out validation evidence.

The current chain is:

```text
DATA7 fitted selection inputs
    -> FEAS1 full-pool feasibility
    -> MVIDX1 exact sparse neighborhood authority
    -> MVSEL2 progressive target order
    -> REPAIR2 repaired master order / MVSTATE2 continuation state
    -> MVQUAL independent prefix qualification
    -> TargetSizeStudyPolicy
    -> selected target size
```

Each component has one role. MVSEL2 is the only current ordering authority; REPAIR2 is the only current repair authority; MVSTATE2 is the only current continuation-state family; MVQUAL independently verifies hard requirements. Superseded selector/repair/migration generations are historical and are not alternate current paths.

## Why multi-view subset construction is necessary

A target subset must cover several physically meaningful feature views simultaneously. Optimizing one descriptor distance or one average utility can conceal a severe deficit in another required view. The architecture therefore treats each required family as an explicit coverage relation, diagnoses full-pool feasibility before subset optimization, and maintains hard coverage separately from discretionary representative utility.

Four principles control the design:

1. feasibility precedes subset optimization;
2. hard coverage and obligations cannot be traded away by aggregate score;
3. subset ordering is deterministic and nested so size comparisons are not confounded by resampling;
4. selector/repair state and independent qualification evidence are separate authorities.

## Exact multi-view neighborhood authority

For feature family \(m\), let \(x_w^{(m)}\) be witness coordinates, \(x_c^{(m)}\) candidate coordinates, \(D_m\) the frozen scaling transform, and \(r_w^{(m)}\) the authoritative witness radius. Exact adjacency is

$$
A_{wc}^{(m)}=
\mathbf 1\!\left[
\left\|D_m\left(x_w^{(m)}-x_c^{(m)}\right)\right\|_2
\le r_w^{(m)}
\right].
$$

For selected subset \(S\), witness multiplicity is

$$
n_w^{(m)}(S)=\sum_{c\in S}A_{wc}^{(m)},
$$

and weighted family coverage is

$$
C_m(S)=
\frac{\sum_w \omega_w^{(m)}\,\mathbf 1[n_w^{(m)}(S)>0]}
     {\sum_w \omega_w^{(m)}}.
$$

For hard threshold \(\tau_m\) owned by the current coverage policy, family deficit is

$$
D_m(S)=\max(0,\tau_m-C_m(S)),
$$

and the worst-view deficit is

$$
D_{\max}(S)=\max_m D_m(S).
$$

A weighted average across families cannot substitute for a failed required family.

Approximate-neighbor substitutions are not scientifically equivalent to the exact relation unless a future accepted design explicitly changes that contract.

## Full-pool feasibility (FEAS1)

FEAS1 inspects the complete eligible candidate/reference authority before subset ordering begins. It answers whether the frozen hard coverage and obligation predicates are satisfiable at all and how fragile that support is.

For witness \(w\),

$$
d_w^{(m)}=\sum_{c\in\mathcal C}A_{wc}^{(m)}.
$$

Low-support witness mass and mandatory-obligation incidence identify regions where correlation-unit exclusion, provenance restrictions, or subset-size ceilings can destroy feasibility.

FEAS1 may conclude that a requested rung cannot satisfy the frozen predicates. That conclusion is evidence about the data/policy combination, not permission to relax coverage, fabricate candidates, or invent an intermediate target size.

## One exact sparse relation (MVIDX1)

MVIDX1 owns the authenticated exact sparse neighborhood relation used by selection, repair, and qualification. Scientific identity binds at least:

- candidate and witness identity/order;
- feature-family identity;
- scaling/distance/radius semantics;
- exact sparse cardinalities/content;
- policy-relevant schema identity.

Execution-only details such as worker count, query block size, in-memory versus file-backed inversion, mmap placement, queue depth, or NUMA placement do not change scientific identity.

The selector/repair path consumes a forward-oriented projection sufficient to score candidate rows and obligation/correlation incidence. Independent qualification may consume the authenticated primitive relation it needs, but no downstream component recomputes geometry under a competing numerical implementation when the same semantic MVIDX authority already exists.

Large exact inversions may use deterministic out-of-core execution as described in Part VI.

## Progressive target ordering (MVSEL2)

MVSEL2 constructs one deterministic progressive order \(\pi_d\) for training domain \(d\). It consumes DATA7 fitted selection inputs, FEAS1 evidence, MVIDX1, hard obligations, correlation/provenance structure, and the frozen selector policy.

### Scientific priority structure

The exact lexicographic policy is specification-owned. Architecturally it has two classes of responsibility:

1. satisfy hard/worst-view coverage and mandatory obligations first; and
2. once hard requirements permit, improve representative utility/diversity and declared balance objectives without violating the hard state.

Representative density, diversity/FPS, environment coverage, protected events, condition balance, difficulty, and provenance are inputs to this one selector rather than independent target-membership authorities.

### Deterministic exact execution

Rank authority is sequential because the scientific state changes after every accepted candidate. Parallel or vector execution may accelerate preparation and exact candidate scoring, but the authoritative accepted candidate and FP64 scientific decision semantics must remain unchanged.

The current execution architecture uses compact witness/obligation/correlation state and exact on-demand forward-row scoring rather than a product-scale eager inverse marginal array for every candidate. During hard-coverage selection, exact staged filtering may eliminate candidates only when the frozen lexicographic ordering proves they cannot win.

After hard coverage completes, an exact certified lazy representative frontier may avoid full rescoring. Stale upper bounds are conservative; candidates are refreshed until the winner is certified under the frozen tolerance and complete tie hierarchy. A full-forward exact oracle remains a bounded correctness fallback, not a separate scientific policy.

## Exact repaired master order (REPAIR2)

MVSEL2 produces the progressive order; REPAIR2 is the sole authority allowed to perform the declared exact active-shell repair while preserving protected lower prefixes and hard invariants.

For selected candidate \(c\), unique covered mass is

$$
U(c\mid S)=
\sum_m\sum_{w:A_{wc}^{(m)}=1}
\omega_w^{(m)}\,\mathbf 1[n_w^{(m)}(S)=1].
$$

A removal is admissible only when it satisfies the frozen unique-support and hard-obligation safety predicates. Replacement proposals follow the frozen deficit/frontier objective and deterministic tie hierarchy. Accepted swaps cannot regress protected hard coverage.

Proposal scoring within one immutable pre-swap state may execute concurrently; authoritative winner comparison and state mutation remain deterministic.

REPAIR2 publishes **one repaired master order per domain**. Candidate target subsets are prefix views of that order. The architecture forbids independently repairing separate copies of the 128-, 256-, 512-, or other rungs because that would destroy nesting and make size comparisons conflate cardinality with unrelated membership changes.

## Reconstructible continuation state (MVSTATE2)

MVSTATE2 is compact authenticated continuation state for the current selector/repair generation. It binds the dataset/domain identity, UID/family order, MVIDX identity, weights, obligations, correlation units, selector/repair policy, selected prefix, and current schema identity.

It persists only state required to reconstruct the current scientific position, such as witness multiplicity, covered mass, obligation/correlation counts, and representative utility. Product-scale complete candidate marginal arrays and ephemeral lazy-heap contents are not authoritative continuation state.

Publication is atomic. Restoration revalidates the persisted state against the selected prefix and primitive identities. Incompatible historical state is not migrated into MVSTATE2; the current campaign must reconstruct from current authoritative inputs or be re-prepared.

## Independent prefix qualification (MVQUAL)

MVQUAL independently recomputes the hard coverage and obligation evidence required to qualify candidate prefixes. It records policy-defined evidence such as:

- per-family hard deficits;
- uncovered weighted mass and counts;
- redundancy/unique-support diagnostics;
- mandatory-obligation satisfaction;
- provenance/correlation diversity diagnostics;
- exact input and policy identities.

Selector/repair internal counters are not accepted as independent qualification evidence. MVQUAL may share authenticated primitive sparse inputs, but it recomputes the relevant predicates through its independent verification path.

Locked-test data cannot tune radii, weights, hard thresholds, repair budgets, tie rules, or qualification predicates.

## Nested prefixes and hard-coverage monotonicity

Let \(\pi_d\) denote the repaired master order for domain \(d\). The target subset at size \(N\) is

$$
D_{d,N}=\pi_d[:N].
$$

For \(N_2>N_1\),

$$
D_{d,N_1}\subset D_{d,N_2}.
$$

Under fixed exact hard-coverage and obligation predicates, adding candidates cannot remove already-covered witnesses or already-satisfied positive obligations. Therefore hard satisfaction cannot regress solely because \(N\) increases.

A pass/fail/pass qualification pattern across increasing prefixes is an invariant violation. It indicates broken nesting, identity, qualification logic, obligation semantics, or numerical realization and must fail closed.

## Target-size populations

The scientific target-size study uses a fixed nominal population

$$
\mathcal N_0=\{128,256,512,1024,2048,4096,8192,16384\}.
$$

For required training domain \(d\),

$$
N_{\mathrm{available},d}=|\mathcal D_{\mathrm{eligible},d}|.
$$

The common materializable population is

$$
\mathcal N_M=
\left\{N\in\mathcal N_0:
N\le \min_d N_{\mathrm{available},d}
\right\},
$$

where required domains include final development and every required cross-validation gradient-training domain.

Independent MVQUAL evidence defines

$$
\mathcal Q=\left\{N\in\mathcal N_M:
\text{all hard requirements pass in every required domain}
\right\}.
$$

The selected size satisfies

$$
N_{\mathrm{selected}}\in\mathcal Q\subseteq\mathcal N_0.
$$

No dynamic rescue size is created. An arbitrary available-pool cardinality, monitor cardinality, replay cardinality, batch size, or implementation budget can never silently become a scientific target size.

## Domain-local membership, protocol-global size

Each required training domain has its own leakage-safe fitted inputs and repaired master order. Therefore the actual selected frames differ by domain even when the selected cardinality is common.

`N_selected` is one protocol hyperparameter shared across required fold/final jobs. This permits protocol-matched cross-validation without leaking held-out fold evidence into size selection.

Held-out cross-validation folds evaluate the complete already-frozen protocol. If held-out fold performance were used to choose `N_selected`, those folds would no longer be independent protocol-validation evidence unless the entire procedure were wrapped in a separate nested-validation design.

## Target-size study policy

`TargetSizeStudyPolicy` is the sole target-size decision authority. It consumes the qualified size population and authorized development/model-selection evidence, including common target/replay monitors as defined by their own policies.

Monitor policies are type-distinct from target-size policy. A target monitor of 256 configurations and a replay monitor of 512 configurations, if those values are current, remain monitoring evidence sets; their integers do not create target-size rungs.

### Exact continuation fidelity

Each candidate follows one authenticated training continuation:

```text
0 -> 3 epochs -> 10 epochs -> 30 epochs
```

The epoch-10 state authenticates the exact epoch-3 model, optimizer, RNG, and protocol parent. Epoch 30 continues epoch 10. All size candidates use the same foundation, replay semantics, objective, optimizer/LR schedule, exposure policy, precision/backend, and frozen training-seed set.

Ordinary target-success early stopping is disabled during this experiment because size candidates must be compared at common fidelity boundaries. Hard numerical/scientific failure may still reject a candidate. Normal production/CV stopping resumes once the size experiment is complete.

### Successive-fidelity funnel

Let \(q=|\mathcal Q|\). The production decision requires at least three qualified sizes:

```text
q < 3      -> insufficient_qualified_sizes
q >= 3     -> epoch 3:  q -> min(q,4)
              epoch 10: <=4 -> 2
              epoch 30: 2 -> 1
```

Candidate comparison uses paired seed-aggregated evidence: every candidate uses the same frozen seed set, avoiding comparisons between unrelated stochastic realizations.

At epoch 3 and epoch 10, candidates within 1 meV/Angstrom in the primary target-force metric are practically equivalent for the screen and the smaller size is preferred. The early screens rank relative promise; they do not require the final absolute force-accuracy threshold.

At epoch 30, only a candidate satisfying the complete frozen hard-admissibility policy may win. Applicable target/focus-group, replay-retention, energy/stress, physical-integrity, relaxation/deployment, and other mandatory requirements are constraints. Replay retention and integrity are not score bonuses unless a future explicit scientific policy changes that rule.

### Typed terminal outcomes

The size study returns a typed decision, not merely an integer:

```text
selected(N)
insufficient_materializable_sizes
insufficient_qualified_sizes
no_admissible_finalist
nonconverged_at_available_ceiling
nonconverged_at_fixed_ceiling
hard_scientific_failure
```

If the available corpus stops below 16,384 and the largest materializable rung remains materially superior, the outcome is `nonconverged_at_available_ceiling`. If 16,384 is available and remains materially superior, the outcome is `nonconverged_at_fixed_ceiling`.

The architecture never creates an intermediate size merely to avoid reporting non-convergence.

## Production screening versus algorithm qualification

Ordinary production executes the successive-fidelity funnel and stops training eliminated sizes.

A release/algorithm qualification may retrospectively train the complete candidate population to 30 epochs to measure survivor recall or calibrate the screening policy. That exhaustive matrix is qualification evidence, not a permanent production requirement. If representative qualification shows that the early screens do not reliably retain eventual finalists, the screening policy must be revised explicitly rather than forcing every campaign to repay every eliminated candidate.

## Bounded scientific materialization

The fixed eight-size population is a scientific policy, not a storage mandate. Per training domain, the intended product-scale state is:

```text
one fitted selection-input authority
one exact MVIDX authority
one MVSEL2/REPAIR2 master order
prefix metadata for candidate sizes
MVQUAL evidence for required prefixes
training artifacts only for candidates authorized to train
```

The architecture specifically rejects eight independent descriptor, sparse-graph, selector-state, or target-dataset copies. Execution caches are reconstructible and bounded.

## Scientific non-negotiables

Execution optimization cannot authorize:

- approximate neighborhood semantics in place of the exact frozen relation;
- relaxed hard coverage or obligations;
- changed leakage/correlation boundaries;
- a second target-membership selector;
- independently repaired rungs;
- held-out or locked evidence controlling target size;
- generated/intermediate rescue sizes;
- non-deterministic authoritative rank/repair decisions;
- migration of unsupported historical selector/repair state into current authority.

Any change to these semantics requires an explicit architecture/specification revision rather than an execution optimization.
