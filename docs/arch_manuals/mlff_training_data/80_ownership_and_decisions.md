# Part VII - Ownership and extension boundaries

## One current-generation authority model

The current campaign has one semantic generation. A record, policy, or
artifact is either authenticated for that generation or unsupported. Historical
selector, repair, migration, and campaign-generation formats are not alternate
current execution paths.

Architecture owns durable structure and scientific/algorithmic invariants.
Specifications own exact schemas, policy values, tolerances, failure codes,
and module-local behavior. Workplans coordinate proposed transitions and never
become product authority merely because implementation follows them.

The core authority chain is:

```text
source evidence and labels
    -> eligibility / conditions / evidence roles
    -> neutral statistical substrate and protected relations
    -> one P_train / M3 split
    -> one pi_train and nested pi_eval ladder M1 subset M2 subset M3
    -> one common target-size preparation
    -> paired optimizer-seed screen
    -> target-size reducer
    -> N_selected and exact global T_selected
    -> post-selection cross-validation on exactly T_selected
    -> fresh final production on the complete T_selected
    -> currentness-fenced publication
```

There is no branch to a second membership selector, a per-domain target-size
map, a generated-size rescue, or downstream-evidence-driven fallback. Derived
state from an unsupported generation is rejected before semantic reuse and is
quarantined/reprepared rather than translated.

## Scientific decision ownership

| Decision or product | Sole current owner | Consumes | Emits | Explicitly does not own |
|---|---|---|---|---|
| source/label identity | DATA2-family contracts | immutable source material | normalized labelled-record identity | partition, selection, training |
| conditions/eligibility | DATA3-family contracts | source records | eligible frames and conditions | evidence-role assignment |
| raw features/events | DATA4-family contracts | eligible evidence and provider declarations | partition-independent raw evidence | fitted metrics or membership |
| evidence roles and protected relations | DATA5 partition contracts | cohorts, independence evidence, purge rules | development/monitor/CV roles and exclusions | target ranking |
| descriptor/difficulty inputs | DATA6 contracts | authorized evidence and frozen foundation model | raw/blinded descriptors and predictions | target membership |
| common fitted preparation | current P3 preparation owner | neutral substrate and frozen method inputs | transforms, metrics, E0, objective/weights, difficulty inputs | membership or target size |
| target-size split and orders | current target-size experiment owner | frame authority, neutral substrate, configured policy | `P_train`/`M3`, `pi_train`, `pi_eval`, `M1/M2/M3` | method acceptance |
| common target-size preparation | `TargetSizeCommonPreparation` | `P_train` and foundation/training protocol | one shared preparation identity | per-size or per-seed scientific variation |
| scientific target size | one target-size reducer | paired target-side screen evidence | `N_selected` or typed scientific failure | monitor cardinality and CV evidence |
| current selected set | `CampaignStore` terminal projection | authenticated reducer state and `pi_train` | exact `N_selected`/`T_selected` binding | re-deciding size |
| post-selection method acceptance | post-selection CV owner | exactly `T_selected`, protected relations, `K >= 2`, CV seeds | all-required-fold target-only verdict | changing `N_selected` |
| fresh final production | final-production owner | accepted method and complete `T_selected` | current production publication | target-size or CV authority |
| target monitor | current monitor policy | authorized development role | deterministic monitor | target membership |
| replay monitor | replay policy | authorized replay evidence | deterministic replay monitor | target ranking or method acceptance credit |
| execution/provider lifetime | current stage owners | authenticated plans and resource budgets | bounded task/cache/provider state | scientific decisions |
| storage management | orthogonal storage owners | campaign-owned artifact inventory | retention/cleanup/archive actions | lifecycle progression |

A narrow specification may refine a row's realization, but it cannot create a
second semantic owner for the same decision.

## Fitted preparation boundary

The current fitted-preparation owner may publish:

- heterogeneous feature transforms and metrics;
- foundation predictions and training-domain difficulty evidence;
- atomic-reference/E0 fits;
- training objective and configuration/property weight records;
- condition, provenance, event, environment, and diversity inputs;
- immutable identities linking products to their authorized inputs.

These are inputs to the one canonical order. They are not an independent
quota, FPS, membership, target-size, or CV selector. A fold-local transform is
allowed only after selection and only when the post-selection CV owner binds it
to that fold's training partition; it cannot change global `T_selected`.

This boundary preserves useful fitted/statistical information without
reintroducing a domain-specific target-size authority. Materialization and
export records describe consumer views and remain downstream of the selected
binding.

## Target-size authority

Let (N_{\mathrm{available}}=|P_{\mathrm{train}}|). The candidate ladder is a
configured contiguous power range,

$$
\mathcal N_0=\{2^p: p_{\min}\le p\le p_{\max}\},
$$

with materializable population

$$
\mathcal N_M=\{N\in\mathcal N_0:N\le N_{\mathrm{available}}\}.
$$

The qualified population is the subset admitted by the current target-size
policy. The selected size must be a qualified member. There is no hidden
scientific ceiling beyond the configured policy and available population.

Every candidate is an exact prefix:

$$
T_N=\pi_{\mathrm{train}}[:N].
$$

Thus frame membership is global, candidate sets are nested, and
`N_selected`/`T_selected` are frozen together. Increasing `N` only adds frames;
a pass/fail/pass result under a monotone prefix policy is an invariant failure,
not a reason to choose a different order.

The reducer consumes only authorized target-side development/model-selection
evidence. Replay metrics, post-selection CV, calibration, physical-observable,
and locked-test evidence cannot rank, reject, or tie-break a target size. Fewer
than three qualified sizes is a typed failure. A configured ceiling that
remains materially superior at the final comparison produces
`nonconverged_at_configured_ceiling`; no unconfigured rescue size is invented.

## Post-selection ownership

The current post-selection graph is:

```text
current selected binding
    -> shared method identity
    -> CV policy / final-production policy
    -> CV plan / final-production plan
    -> fold/final evidence
```

Cross-validation uses exactly `T_selected`, preserves P1 protected relations,
requires every configured fold and seed, and accepts or rejects the method.
It cannot alter `N_selected`. Final production starts fresh from the accepted
foundation and trains the complete selected set under
`[training].max_num_epochs`; it cannot continue a screen or CV run.

Every current consumer re-resolves the selected binding and current campaign
revision before exposing a descendant. A stale caller-held object, checkpoint,
or provider cannot become current. Publication rechecks currentness in the
same transaction that would install a current pointer.

## Public orchestration and storage boundary

The public scientific lifecycle is exactly:

```text
init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production
```

`prepare` builds the neutral/current substrate and common preparation but
selects nothing. `select-target-size` owns candidate training and the reducer.
`cross-validate` owns selected-only method acceptance. `train-production` owns
fresh final publication. `status` and `advance` project these same owners;
they do not create another state machine. `storage` is orthogonal and manages
reconstructible artifacts without advancing scientific lifecycle.

## Downstream qualification boundary

Deployment parity, physical PES/relaxation/dynamics validation, uncertainty
calibration, and locked testing remain product obligations, but they are not
current P6 campaign owners. A future successor may consume a current final
publication through an explicit downstream contract. It may reject that
publication, but it may not select another seed/checkpoint/member from
downstream evidence and may not feed back into target-size or method authority.

Physical numerical algorithms remain owned by their analysis modules. A
downstream recipe must bind matched collection/frame identity, runtime and
capability identity, analysis-owned results, and a declared statistical role.
P6 does not claim downstream implementation or qualification merely because
its current final-production record is available.

## Unsupported generations and compatibility

Current loaders do not semantically read or migrate obsolete target-size
derived state. The narrow cutover detector may inspect record names or minimal
generation metadata solely to reject before candidate/checkpoint reuse. It may
quarantine the opaque record under a namespace no current loader reads, but it
cannot decode, reconstruct, normalize, or bind that payload into current
authority.

Independent lower-level source/frame/content caches may be reused only after
their current owners revalidate source bytes, recipe, lineage, and integrity.
Compatibility readers for non-target product responsibilities remain
read-only and non-authoritative. Historical schemas and rationale belong under
`docs/history/mlff/`; their presence does not create a current API.

## Extension boundaries and summary

A future extension may enrich neutral feature/preparation inputs, extend the
canonical `pi_train` policy, add an explicitly qualified screen metric, or
change execution representation only when one-owner direction, exactness,
protected evidence roles, and currentness remain intact. A new campaign
generation is not entitled to automatic migration support.

The durable rules are:

1. independent evidence remains independent;
2. fitted preparation and target membership are separate authorities;
3. one canonical order and one common preparation define every candidate;
4. `N_selected` and exact global `T_selected` are frozen together;
5. the reducer alone decides size and post-selection CV alone accepts the method;
6. final production is fresh full-selected-set training;
7. execution/cache/provider choices cannot change scientific semantics;
8. unsupported derived state is rejected before reuse rather than migrated;
9. downstream qualification cannot become a P6 selection fallback.
