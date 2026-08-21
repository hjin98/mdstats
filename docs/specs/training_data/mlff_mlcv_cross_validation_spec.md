# MLFF protocol-matched cross-validation specification

**Status:** current normative held-out protocol-validation contract  
**Architecture:** revision 105

## 1. Purpose

Cross-validation estimates robustness of one already-frozen `TrainingProtocolIdentity`. It does not choose target size, tune membership policy, stop training, rank epochs, or replace a checkpoint after seeing held-out evidence.

The protocol entering cross-validation already contains the selected protocol-global target size and all protocol-defining training semantics.

## 2. Fold roles

For fold `i`, DATA5 provides three explicit role domains:

```text
fold_training_domain_i
fold_checkpoint_monitor_i
held_out_evaluation_fold_i
```

The fitted preparation and target membership used by fold `i` are reconstructed from `fold_training_domain_i` only:

1. DATA6/DATA7 fit fold-local descriptors/metrics/E0/difficulty/objective inputs;
2. MVSEL2/REPAIR2 produce that fold's repaired master order;
3. the already-frozen protocol-global `N_selected` defines the fold target prefix;
4. a fresh model/optimizer lineage trains under the frozen protocol;
5. checkpoint choice freezes using only the authorized checkpoint/common monitor evidence;
6. only then is `held_out_evaluation_fold_i` exposed for protocol evaluation.

The held-out fold cannot trigger fallback to another epoch/checkpoint or a different target size.

## 3. Protocol identity requirement

Every fold job SHALL bind the complete current `TrainingProtocolIdentity`, including at least the selected target size, fold-local target-prefix identity, foundation/model/head, replay source/monitor, objective/weights, exposure realization, checkpoint policy, optimizer/LR/stopping policy, seeds, precision/backend, and runtime lock.

CV evidence applies only to the identity actually evaluated. If final training changes a protocol-defining field, the old CV evidence is not validation of the new protocol.

## 4. Held-out result

The held-out evaluation computes the current policy-defined target/focus/property metrics on the frozen representative checkpoint. A fold with no admissible representative records an explicit failure and does not use the held-out fold to search for a rescue checkpoint.

Replay retention used for checkpoint admissibility remains separately authenticated development/model-control evidence. Cross-validation does not turn replay into a rotating target fold.

Replay metrics are reported as constraints/diagnostics under their owning policy. They are not added as a positive bonus to a combined target score by default.

## 5. Per-seed / cross-fold aggregation

For each configured optimizer seed, all configured folds are represented exactly once. Aggregate evidence reports the current metrics required by the protocol-validation policy, including conventional mean and sample standard deviation where at least two folds exist, plus min/max/range/worst-fold diagnostics as appropriate.

Cross-fold dispersion is evidence about protocol robustness. Any hard dispersion threshold must be an explicit current policy value rather than inferred post hoc.

A protocol passes CV only when every mandatory fold-level and aggregate robustness predicate defined by the current policy passes.

## 6. Production boundary

Fold models are permanently production-ineligible. Cross-validation publishes protocol evidence only.

Production-eligible models are trained on the final-development domain under the same frozen protocol after CV acceptance (or under an explicitly configured no-CV protocol when that mode is permitted).

A campaign configured with zero folds records `cv_not_performed`; it does not manufacture robustness evidence.

## 7. Restart and immutability

Held-out evaluation records bind the campaign/protocol identity, selected-size decision, fold-local target-prefix identity, representative checkpoint digest/epoch, held-out artifact identity, runtime identity, and evaluation policy.

Authenticated compatible evaluation artifacts may be reused. A record cannot be rebound to different held-out evidence or a different checkpoint under the same identity.

## 8. Prohibited dependencies

Cross-validation SHALL fail closed if:

- a held-out fold contributed to DATA6/DATA7 fitting or MVSEL2/REPAIR2 membership;
- held-out performance selected or revised `N_selected`;
- held-out performance selected another checkpoint after representative freeze;
- fold and final jobs claim protocol equivalence while protocol-defining identities differ;
- fold models are promoted to production/committee membership;
- a historical migration/compatibility path changes current evidence roles.

Unsupported old CV aggregate schemas are historical evidence only and do not define current protocol-validation behavior.
