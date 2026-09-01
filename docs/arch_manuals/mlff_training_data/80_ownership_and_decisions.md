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
| evidence roles and protected relations | DATA5 partition contracts | cohorts, independence evidence, purge rules | neutral roles (development/monitor/calibration/locked) and split exclusions | post-selection CV folds or target ranking |
| descriptor/difficulty inputs | DATA6 contracts | authorized evidence and frozen foundation model | raw/blinded descriptors and predictions | target membership |
| common fitted preparation | current P3 preparation owner | neutral substrate and frozen method inputs | transforms, metrics, E0, objective/weights, difficulty inputs | membership or target size |
| target-size split and orders | current target-size experiment owner | frame authority, neutral substrate, configured policy | `P_train`/`M3`, `pi_train`, `pi_eval`, `M1/M2/M3` | method acceptance |
| common target-size preparation | `TargetSizeCommonPreparation` | `P_train` and foundation/training protocol | one shared preparation identity | per-size or per-seed scientific variation |
| scientific target size | one target-size reducer | paired target-side screen evidence | `N_selected` or typed scientific failure | monitor cardinality and CV evidence |
| current selected set | `CampaignStore` terminal projection | authenticated reducer state and `pi_train` | exact `N_selected`/`T_selected` binding | re-deciding size |
| post-selection method acceptance | post-selection CV owner | exactly `T_selected`, protected relations, `K >= 2`, CV seeds | all-required-fold target-only verdict | changing `N_selected` |
| fresh final production | final-production owner | accepted method, complete `T_selected`, required final seeds | complete executed run evidence / model artifacts | target-size or CV authority (publication is P7) |
| target monitor | current monitor policy | authorized development role | deterministic monitor | target membership |
| replay monitor | replay policy | authorized replay evidence | deterministic replay monitor | target ranking or method acceptance credit |
| execution/provider lifetime | current stage owners | authenticated plans and resource budgets | bounded task/cache/provider state | scientific decisions |
| storage and I/O management | `mdstats.training_data.storage` | owner views over every current P1-P7 owner | owner-bound plan, safe/cache cleanup, cold archive, dedup, admission, read-only reporting | any scientific or currentness decision |

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
and locked-test evidence cannot rank, reject, or tie-break a target size.
Fewer than three qualified sizes is a typed failure. A configured ceiling that
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
    -> final-production publication decision
```

Cross-validation uses exactly `T_selected`, preserves P1 protected relations,
requires every configured fold and seed, and accepts or rejects the method.
It cannot alter `N_selected`. Final production starts fresh from the accepted
foundation and trains the complete selected set under
`[training].max_num_epochs`; it cannot continue a screen or CV run.

### The final-production publication decision

Deciding *which* completed production seeds constitute the released product is
the last pre-qualification act, and it is owned here rather than downstream.
`train-production` takes it immediately after the required seeds complete, when
every input it needs already exists and no downstream release evidence does. If
the decision were taken later, "the committee" would silently become "the
members that survived qualification" - member selection on release evidence.

Each completed run durably publishes the exact records that chose its
representative: the representative EVAL2/admissibility record and its M3 target
metric record. Those were previously referenced by digest only, which left no
authenticatable basis for any cross-seed decision. A run root written before
they were durable is *re-evaluated* through the real EVAL2/provider owner on its
exact authenticated checkpoints and must reproduce the digests its run evidence
already bound; nothing is ever synthesized from a digest.

The decision record binds the selected binding, the final plan and policy, the
accepted CV/method lineage, the frozen M3 membership, every required seed's run
evidence and representative identity, the canonical target head, the committee
policy, the exact ordered published member set, and a deterministic
decision-policy identity. Both configured policies are supported:

- `all_qualified_final_seeds` publishes every required seed whose already-frozen
  representative is admissible under the accepted checkpoint policy;
- `single_best_final_seed` ranks only those already-frozen representatives with
  the accepted target-only EVAL2 ordering over the common frozen M3 evidence,
  with tie material descending from the final-production plan identity, and
  publishes the first canonical admissible representative.

No downstream metric, target-size statistic, physical score, or locked score
participates, replay evidence remains admissibility-only, and there is no API
that adds, removes, or reorders a member afterwards. A decision that no longer
binds the current lineage stays on disk as historical evidence and is
unreachable as the current product.

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
they do not create another state machine. `storage` is orthogonal: it manages
representation, retention, caching, archival, and admission, and it advances no
scientific lifecycle.

Post-production qualification is a separate downstream family and is
deliberately not part of that lifecycle:

```text
qualification status | qualification run | qualification activate-locked
```

`advance` never runs qualification and never opens locked evidence.

## Downstream qualification ownership

Deployment parity, physical PES/relaxation/dynamics validation, uncertainty
calibration, and locked testing are owned by `mdstats.training_data.qualification`.
That package is a *consumer* of the accepted final-production publication, never
a second product authority. Its owner graph is:

```text
accepted current selected binding (P4)
    -> accepted post-selection CV (P5)
    -> accepted fresh final production and its currentness-fenced completion (P5)
         |  immutable and read-only to qualification
         v
    QualificationInputBinding
      exact publication + ordered members
      + executable candidate identity
      + target-machine environment fingerprint
      + frozen qualification specification
      + frozen neutral evidence-role membership
         |
         v
    ProductionQualificationPlan  (+ candidate-independent PhysicalValidationPlan)
         |
         +-> deployment parity through the supported ML-IAP/LAMMPS runtime
         +-> local PES response against matched external references
         +-> fixed-cell relaxation topology and geometry fidelity
         +-> finite-temperature dynamics stability
         +-> uncertainty calibration, or an explicit not_applicable
         +-> explicit one-shot locked interpolation test
         |
         v
    ProductionQualificationRecord -> ReleaseEvidenceIndex
```

The publication resolver is the accepted P5 publication-decision owner;
qualification copies that decision's own ordered member set and adds no
publication, membership registry, or member-selection rule of its own. Both
committee policies are decided upstream, so qualification contains no cross-seed
ranking at all.

The exact canonical P5 target head travels with every published member and is
part of both the member identity and the deployment identity, so an artifact
exported from the replay or foundation head is a different product rather than
the same product serialized differently. The deployment export and the ML-IAP
builder are both called with that head; neither accepts `None` for a
multihead-capable product. Deployed artifacts are published create-once under an
advisory per-artifact lock and are re-authenticated from a durable receipt and
their bytes before every reuse, including after a process restart - a full
PyTorch model pickle is not byte-deterministic, so identity is carried by the
receipt rather than inferred from the bytes.

Every public qualification resolver re-establishes the current
`QualificationInputBinding` at exposure time and validates the located object
against it. The campaign-store pointer is a locator only: a terminal verdict
published under an older specification, executable, environment, or product is
historical, never current, and `qualification status` cannot print it as a
current release verdict. Locked disclosure history is deliberately kept outside
that fence, in an append-only reveal index, so a currentness change can make a
verdict historical but can never make a revealed cohort fresh again.

Reference-dependent components are keyed by a component-input identity that
includes the exact frozen request and the exact authenticated bundle, so
replacing a bundle under the same request stales local PES, relaxation, and
dynamics while leaving deployment and calibration evidence reusable. Dynamics
runs from the authenticated reference-relaxed coordinates of each physical base,
never from the unrelaxed base geometry, and its reducer - not the runtime worker
- decides NVT/NVE temperature behaviour, energy drift, safety bounds, and
protected topology, displacement, bond, and angle degradation under thresholds
frozen before execution, including an explicit consecutive-sample persistence
rule that separates transient noise from real damage.

Locked activation is an irreversible *open* event rather than proof the
evaluation completed. A crash between opening the cohort and publishing the
result is resumable onto the same activation identity; only a genuinely terminal
result makes a second activation a rejected duplicate.

Qualification concurrency and nested thread budgets come from the accepted
campaign resource owner, and the resolved resource scope is bound to the attempt
separately from the numerical environment identity, so machine capacity is
recorded without making a deterministic numerical claim machine-specific while a
materially different resource scope still cannot silently reuse a
performance claim.

That scope digest is identity, not measurement. Each attempt also publishes one
immutable resource observation - total and per-component elapsed time, workspace
filesystem total/free bytes and the attempt's own footprint at start and end, the
configured `[execution].minimum_free_disk_gib` reserve and whether it held, peak
process RSS, and accelerator model/VRAM where an existing owner reports them -
which the terminal record and release index both point at. Those observations are
evidence and never stale numerical results; their one operational role is that an
attempt which cannot satisfy the existing disk reserve aborts before materializing
work rather than changing any scientific input. Reading that reserve is an
owner-local safety check, not the storage admission plane.

Stress applicability is likewise a capability decision rather than a
configuration switch: it is resolved before execution from the accepted training
objective's stress weight, reference stress labels, whether the authenticated
model returns a stress tensor, periodicity, and runtime support. Policy may
require stress or record a justified inapplicability reason, but it cannot
relabel an available trained channel as `not_applicable`. Each source converts to
canonical ASE/MACE Cauchy stress in eV/Angstrom^3, positive in tension, exactly
once; units and sign belong to the source adapter, so LAMMPS `units metal` thermo
pressure - bar, positive in compression - is converted only by its own named
adapter and is never parameterized by a caller.

The exact three-axis periodicity vector is carried through every deployed
request, the LAMMPS boundary command, the raw observations, and the dynamics case
identity. A mixed boundary is executed as itself or fails closed; it is never
coerced to fully periodic or fully open, and minimum-image reductions wrap only
the axes that genuinely have images.

Downstream evidence has pass, reject, and waiting authority for the exact
frozen product and nothing else. A failure never changes `N_selected`,
`T_selected`, CV acceptance, a production checkpoint or seed, publication
membership, or an upstream threshold. A missing external reference is
`waiting_for_reference` with an actionable request on disk, never a fabricated
pass. An absent supported deployment runtime is reported as unavailable and
blocking, never as either a pass or a scientific rejection.

The locked interpolation test is opened only by `qualification activate-locked
--confirm`, only after every mandatory nonlocked component has passed, and only
once for a given publication and locked cohort. After activation the revealed
cohort is never a fresh locked test again, whatever the policy is changed to.

Physical numerical algorithms remain owned by their analysis modules. A
downstream recipe must bind matched collection/frame identity, runtime and
capability identity, analysis-owned results, and a declared statistical role.

### Qualification persistence and the successor-storage handoff

Qualification evidence lives under one canonical generation-scoped root,
`<workspace>/.mdstats/qualification/g<N>/`, with `objects/` holding immutable
create-once release evidence and `attempts/<attempt-identity>/` holding
attempt-local state and bulk scratch. Currentness is never persisted as a second
truth: it is re-established through the P4/P5/P7 owners and published as a
generation-fenced pointer in the campaign store, exactly as P5 descendants are.

The storage subsystem consumes these owner entry points and needs no pathname
inference:

```text
CampaignStore                          current campaign state owner
P3 target-size generation/root owner   execution evidence and reconciliation
P4 selected binding owner              current selection authority
P5 post-selection root/store           CV, final plan, run completion
P7 publication resolver                resolve_authenticated_final_publication
P7 qualification root/store            qualification_root, QualificationEvidenceStore
P7 terminal result owner               ProductionQualificationRecord, ReleaseEvidenceIndex
P7 attempt/retention owner             QualificationAttemptState, QualificationRetentionFence
P1 frame-cache owner                   the one exact-reconstruction cache seam
CampaignStore receipt cache            stat-keyed SHA-256 acceleration only
```

Qualification adds no cache authority, no second cleanup policy engine, no
global retention registry, and no part of the storage inventory, archive,
deduplication, or admission plane. Its retention reference is
coordination metadata only: it says that one already authoritative artifact is
actively referenced by an in-flight attempt, it is released on terminal
completion or explicit abort, and it can never make a stale publication current.

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
5. the reducer is the sole target-size authority; post-selection
   cross-validation accepts the method and can never re-choose the size;
6. final production is fresh full-selected-set training;
7. execution/cache/provider choices cannot change scientific semantics;
8. unsupported derived state is rejected before reuse rather than migrated;
9. downstream qualification cannot become a selection fallback: it validates
   one already frozen product and has no path back into selection, CV,
   production, or publication membership.
