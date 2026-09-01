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
target/replay head weights and realized exposure policy
checkpoint metric and admissibility policy
optimizer, LR schedule, epoch cap, stopping policy, and seed policy
model precision, acceleration backend, and MACE adapter/runtime lock
```

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

The shared method identity binds preparation/objective recipe, foundation and
initialization family, optimizer family, LR schedule, checkpoint semantics,
precision, and backend. It does not contain fold membership or a second target
size.

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
