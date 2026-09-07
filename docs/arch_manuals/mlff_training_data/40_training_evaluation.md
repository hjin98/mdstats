# Part IV - Training, evaluation, and downstream qualification boundary

## Purpose and ownership

This chapter defines the training-protocol identity, replay boundary,
checkpoint admissibility, post-selection cross-validation, and fresh final
production consumed by the current campaign. Target membership and target size
are already frozen by Part V; this chapter never creates a second size or
membership authority.

Deployment, physical-observable comparison, uncertainty calibration, and
locked testing remain product capabilities, but their downstream qualification
consumers are outside the P6 public lifecycle. They may consume a current
final-production publication only through a separately implemented and
explicitly activated successor contract. They cannot feed selection or choose
another final model.

## Complete training-protocol identity

Multi-head replay fine-tuning trains a shared MACE backbone on target data and
an authorized foundation replay corpus with separate output heads. Replay can
constrain forgetting while the target head adapts, but replay evidence is not a
target-size ranking signal.

Every compared run binds a complete `TrainingProtocolIdentity`, including as
applicable:

```text
foundation checkpoint / model family / selected foundation head
protocol-global N_selected and exact T_selected binding
replay source, split, and replay-monitor identity
training objective and configuration/property weights
executable loss family
target/replay head weights and realized exposure policy
checkpoint metric and admissibility policy
optimizer, LR schedule, epoch cap, stopping policy, and seed policy
model precision, acceleration backend, and MACE adapter/runtime lock
```

## Objective and weighting layers

Three weighting owners are applied at three different layers and are never
merged:

- **global loss coefficients** - `[objective]` (`TrainingObjectivePolicy`),
  default `energy : forces : stress = 1 : 10 : 1`. They are emitted explicitly
  into every generated MACE configuration, so MACE's own `forces_weight = 100`
  default never applies to an mdstats run;
- **per-configuration weight** - `[weighting]` (`ConfigurationWeightPolicy`),
  exported as `config_weight`;
- **local property weights** - availability masks, `1.0` when the canonical
  label is present and `0.0` when it is absent. They are not per-frame copies of
  the global ratio.

The executable loss family is MACE's weighted energy+force+stress loss
(`loss = "stress"`, `WeightedEnergyForcesStressLoss`), whose native reductions
consume `ref.weight` and the local property weights linearly while applying the
global coefficients once. MACE's `UniversalLoss` is not used: it scales
residuals inside a Huber evaluation - so its per-config property weights are not
linearly equivalent to global coefficients - and it does not consume
`config_weight`. The loss family is part of method identity, so historical
checkpoints trained under different loss semantics are not prefixes or
equivalents of corrected trajectories.

Target-size screening, post-selection cross-validation, and fresh final
production resolve these owners through the same configuration resolvers, so
"the same objective" means the same resolved policy on every path.

The identity contains no unbound caller-held model or fold result. A change to
replay semantics, objective, selected membership, checkpoint policy,
precision/backend, stopping/LR policy, or another protocol field creates a new
method identity and invalidates the descendants that depend on it.

## Target and replay evidence

Target and replay retain separate source/label identities, split and exposure
accounting, weights, and monitors. Replay preparation never silently acquires
an external corpus. True-label replay is compared against its authorized
labels; pseudo-label replay, when explicitly supported by the method contract,
measures drift from the bound foundation model on an unseen monitor.

`ReplayRetentionPolicy` binds its metric, baseline, permitted degradation,
aggregation, and failure semantics. A checkpoint that violates a mandatory
replay-retention requirement is inadmissible even when its target metric
improves. Replay values receive no target-size ranking, tie-break, fold, or
seed credit.

## Monitoring and checkpoint choice

The common target monitor is development/model-selection evidence. It supplies
no gradients and is distinct from post-selection held-out fold evidence and
from future locked-test evidence. Monitor cardinality is never target-size
authority.

`CheckpointMetricPolicy` defines the primary target objective and every
mandatory target, focus-group/species, condition, property, replay, and
integrity constraint applicable to checkpoint admission. A typical constrained
choice is

$$
\min_c L_{\mathrm{target\ monitor}}(c)
$$

subject to requirements such as

$$
L_{F,g}(c)\le\delta_g,
\qquad
\Delta L_{\mathrm{replay}}(c)\le\delta_{\mathrm{replay}}.
$$

Exact thresholds and aggregation are specification-owned serialized policy.
Checkpoint choice is deterministic over the complete authorized candidate set
and fails closed when no candidate satisfies a mandatory constraint.

## MACE adapter and data boundary

The MACE adapter binds package/source identity, head ordering, loader
realization, scheduler/stopping behavior, checkpoint retention,
precision/backend realization, and any current runtime lock. Documentation URLs
are not a runtime contract. Material upstream behavior changes fail closed
until the adapter contract is revised and requalified.

Extended XYZ contains only MACE-readable labels, weights, and compact stable
identities. Sidecar manifests carry long provenance, policy identities, and
audit reasons. Target export includes the declared energy channel, forces,
authorized stress, configuration/property weights, cell/PBC, atom order, and
exact label/E0 provenance. Export precision and round-trip behavior are
checked through the current reader path.

An `AtomicReferenceFitRecord` becomes the explicit numerical representation
accepted by the MACE runtime, normally an atomic-number mapping. A record name
or path is not an E0 payload. Target and replay label domains are checked for
compatibility rather than silently merged.

The current MACE execution lock extends this boundary through dependency
argument mutation. Parser-facing configurations explicitly carry
`multiheads_finetuning = false` for ordinary one-head runs and
`multiheads_finetuning = true`, `loss = "stress"`,
`force_mh_ft_lr = true`, and `real_pt_data_ratio_threshold = 0.0` for replay.
The one source-qualified mdstats wrapper
prevents pinned MACE 0.3.16 from replacing that loss with `UniversalLoss`, then
records the native resolved `WeightedEnergyForcesStressLoss`, LR/EMA settings,
replay exposure, source-probe identity, and method/config digests in the
existing TRAIN2 runtime evidence. Target-size executions additionally retain
the final target batch, realize `ceil(N / B)` batches with complete target UID
coverage, and fail closed for an unqualified distributed sampler. This is an
execution realization of the existing method identity, not a second trainer or
loss owner.

## Controlled target-size screen versus ordinary training

The target-size experiment is the special Part V protocol-comparison control.
It uses authenticated `n1 -> n2 -> n3` continuation, paired optimizer seeds,
direct `M1/M2/M3` endpoint populations, and no ordinary target-success early
stopping before a required screen boundary. An earlier checkpoint cannot
replace the prescribed endpoint merely because its metric is better.

The current public screen owns the complete restartable continuation. Generated
campaigns default to `(n1,n2,n3) = (1,3,10)`; fresh final production has its
independent `[training].max_num_epochs` horizon. Screen checkpoints and CV
checkpoints are never production parents.

After selection, CV and final production run under the accepted method. CV
uses fold partitions of exactly `T_selected`, with fresh model/optimizer
lineage per required fold/seed. Final production starts fresh from the
accepted foundation and trains the complete `T_selected`; it continues no
screen or fold trajectory. Its run namespace remains disjoint even when a
numeric seed or target size coincides.

## Post-selection method acceptance

The dependency graph is acyclic:

```text
current selected binding
  -> shared post-selection method identity
  -> CV policy and final-production policy
  -> CV plan and final-production plan
  -> fold/final execution and evidence
```

The shared method identity binds preparation/objective recipe, executable loss
family, foundation and initialization family, optimizer family, LR schedule,
checkpoint semantics, precision, and backend. It does not contain fold membership or a second target
size.

### One canonical optimizer-setting resolution

The shared scientific optimizer semantics a campaign may configure - general
learning rate, batch size, validation batch size, evaluation interval, EMA
enable/disable, EMA decay, AMSGrad, weight decay, gradient clipping, and the
permitted optimizer family - are resolved exactly once, by
`mdstats.training_data.training_settings.resolve_shared_optimizer_settings`.
The learned-model dtype is likewise resolved once, by the binary
learned-model-precision contract in the same module. The method identity, the
executable `MaceOptimizerPolicy`, the generated MACE configuration, and the
TRAIN2 runtime all descend from those single resolutions:

```text
configuration
  -> one canonical resolved value
      -> P5 method identity
      -> executable MaceOptimizerPolicy
      -> generated MACE config
      -> TRAIN2 runtime
```

There is no second, independently defaulted route. P5 method identity is
therefore literally the method that executes: an explicitly configured shared
optimizer field changes both the recorded identity and actual training, and an
omitted field resolves to the same default on both sides. The optimizer seed,
role-specific epoch budgets, and worker counts stay outside these shared
settings, because they are per-run identity, role policy, and pure resource
choice respectively.

The resolver is also the place where the configuration domain is enforced, so
that a malformed setting cannot become either a recorded identity or an executed
method: learning rate, EMA decay, weight decay, and gradient clipping must be
finite reals in their declared ranges; batch sizes and evaluation interval must
be exact positive integers, never booleans or truncated floats; and the EMA and
AMSGrad flags must be actual booleans rather than truth-normalized values.
`MaceOptimizerPolicy` repeats those invariants in its constructor, because it is
independently constructible and independently deserialized.

The same fail-closed, validate-before-canonicalization rule applies to the
target-size normalization reference policy, `TrainingObjectivePolicy`, and
`ConfigurationWeightPolicy`, including their current-schema readers. Real
values must be finite and in their declared ranges, integer values must be
actual integers, boolean values must be actual booleans, and collection
elements must satisfy their declared domains. A malformed current-schema value
is rejected before it can affect identity, export, or execution; only an
explicitly supported historical reader may preserve a historical representation.

Because historical evidence could previously record an identity whose defaults
were never the ones execution applied, the method recipe carries an explicit
version. Evidence produced under the earlier resolution cannot authorize
corrected cross-validation or final production; it remains readable as history
and is never rewritten in place.

The CV policy owns `K >= 2`, partition seed, fold algorithm, CV budget,
monitor/purge allocation, target-only acceptance, and the all-required-fold /
all-required-seed rule. The final-production policy owns the production epoch
horizon, production seed matrix, and committee policy. Neither policy can
rewrite the other or the selected binding.

The CV plan records the current selected binding, protected P1 relations,
selected-only fold memberships, and required run matrix. The final-production
plan records the complete `T_selected` and accepted CV authorization. Evidence
descends from a plan and binds it; corrupted evidence invalidates itself and
never rewrites its authorizing plan.

CV freezes each fold representative on its authorized target monitor before
evaluating the held-out fold. A required fold or seed failure is a
methodological failure: it leaves `N_selected` and its evidence unchanged and
does not authorize final production. A materially different method requires a
new target-size experiment because the measured method has changed.

## Final production and currentness

Final production publishes only after reauthenticating the current campaign
revision, selected binding, accepted method, and complete production plan.
`ProtocolFreezeRecord` binds the method, selected membership, replay/monitor
identities, checkpoint/committee identities, and upstream evidence needed by
the current production consumer.

Every current read resolves the selected binding again from the store; it does
not trust a stale caller object. Publication rechecks currentness in the same
transaction that would make a descendant current. A superseded run can retain
diagnostics, but it cannot publish a current final model.

## Downstream product boundary

Physical observables such as RDF, coordination, topology, MSD, VACF, spectra,
VDOS, diffusion, and conductivity remain owned by their analysis modules and
their own specifications. A future downstream qualification recipe must bind
matched reference/candidate collection identity, runtime/capability identity,
analysis-owned result identity, and an explicit statistical role.

Calibration is valid only for predictions from the actual frozen final
committee. Locked-test evidence remains sealed until its explicit activation
boundary. Neither calibration nor locked evidence may alter fitting, target
membership, target size, training protocol, checkpoint selection, or final
publication. P6 does not claim that these downstream consumers are implemented
or qualified.

## Failure and reproducibility semantics

The workflow fails closed for incompatible label domains, missing foundation or
replay identity, unsupported loader exposure, missing required fold/seed,
stale selected binding, invalid checkpoint constraints, corrupt checkpoint
state, or a downstream result offered as selection authority.

Reproducibility binds source/label and protected-role identities, the neutral
substrate, target-size experiment and orders, common preparation, selected
binding, method/policy/plan identities, replay/monitor identities,
optimizer/LR/stopping/seed policy, precision/backend, checkpoint evidence, and
published final identity. Worker count, queue order, cache path, and other
execution-only choices remain outside scientific identity unless a current
specification explicitly says otherwise.
