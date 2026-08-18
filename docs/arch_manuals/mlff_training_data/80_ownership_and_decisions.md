# Part VIII - Ownership boundaries and decision summary

## Physical-observable validation ownership boundary

Physical observable calculation is not owned by `mdstats.training_data`. RDF,
coordination, neighbor-angle statistics, connectivity, topology statistics,
MSD, VACF, spectra, VDOS, diffusion, displacement distributions, current
correlations, and ionic conductivity remain authoritative in their respective
`mdstats.analysis` modules and architecture manuals.

The MLFF branch owns only:

1. choosing an advisory observable-recommendation profile and an explicit recipe;
2. constructing an immutable recipe of analysis call IDs and parameters;
3. running the same recipe on matched reference and MLFF collections;
4. preserving verified collection and frame-selection identity, symmetric reference
   and candidate trajectory-generation identity, runtime/capability identity,
   warning records, and analysis-owned result identities;
5. binding every execution to an explicit statistical role and, where required,
   to a predeclared comparison policy, protocol freeze, and test-activation record;
6. applying comparison and acceptance policies only after those policies are
   frozen and independently identified.

It does not own the numerical algorithms, normalization, neighbor definitions,
plateau estimators, spectral transforms, or graph statistics.

The analysis-owned standardized facade is `mdstats.analysis.observable_validation`. The MLFF-owned bridge delegates to that facade and stores no duplicate scientific arrays or algorithms.

The initial ObservableRecommendationProfile values are:

- `generic_condensed`, `crystalline_solid`, and `amorphous_solid`;
- `liquid` and `interface`.

These are advisory call sets, not automatic material classifiers. The user still supplies
species/groups, cutoffs, projections, trajectory windows, thermodynamic
conditions, and any interface coordinate. Ionic transport is an explicit
extension. Porous, zeolite, ring, cage, and site calls are optional extensions
and must never be activated merely because the reference application is LTA.

### Selection features versus validation observables

Compact structural descriptors used for partitioning or frame selection are
MLFF workflow inputs. Full physical observables used to judge a trained model
remain analysis products. An MLFF feature provider may call a lower-level
analysis primitive when that primitive has an explicit per-frame contract, but
it must record the owner API and cannot redefine the observable. Expensive
trajectory observables such as diffusion, VDOS, conductivity, or residence
statistics are validation jobs, not ordinary frame-selection features.

### Implemented call boundary in 0.20.44a0 and consistency closure in 0.20.45a0

The first standardized recipe registry covers the implemented general
structural and dynamical calls, including RDF, coordination, bond angles,
atomic connectivity/statistics, MSD, VACF, velocity spectra, VDOS, VACF
diffusion, diffusion plateau selection, van Hove, non-Gaussian dynamics,
self-intermediate scattering, charge current, current correlation, ionic
conductivity, and Nernst-Einstein comparison. Native result dataclasses remain
owned by the analysis modules.

The 0.20.45a0 closure validates recipe dependencies at construction, preflights
machine-readable collection requirements, records versioned capability/codec
identity, captures warnings, per-call durations, and runtime versions, and binds
candidate model and MD protocol identity to paired evidence. DATA9A6c in
0.20.46a0 strengthens this contract: supplied collection identities are
recomputed and verified; location hints do not alter scientific identity;
reference and candidate generation records must both bind the output collection;
each native result receives an analysis-owned canonical digest; statistical role
and locked-test activation are explicit; and comparison-policy identity is
upstream of realized evidence. Comparison metrics and scientific acceptance
thresholds remain a future MLFF policy layer; call execution alone is not a
pass/fail judgment. Static EOS, elasticity, finite-temperature response,
viscosity, phonons, surfaces, interfaces, defects, and migration barriers are
owned by `thermomechanical_energetic_validation_architecture.md`.


### Statistical role, policy ordering, and locked-test leakage

Physical-observable evidence is assigned one explicit role:
`training_diagnostic`, `checkpoint_monitor`, `outer_validation`, `calibration`,
`locked_test`, or `external_benchmark`. The role is not inferred from a filename
or caller context.

A comparison policy is a predeclared object. The allowed dependency order is:

```text
ObservableComparisonPolicy
    +
ObservableValidationActivationRecord
    +
Reference/Candidate Collection and Generation Identities
    -> ObservableValidationEvidence
    -> ObservableComparisonResult
    -> ObservableAcceptanceDecision
```

The reverse edge is forbidden. Realized RDFs, diffusion coefficients, phonons,
or other physical results must not be inspected to choose their own acceptance
thresholds. A locked-test activation record additionally requires the frozen
training protocol, partition assignment, and explicit evaluation activation.
Locked-test observable evidence cannot alter feature fitting, selection,
training protocol, checkpoint selection, calibration policy, or acquisition.
The dependency graph represents this role specialization explicitly as `LOCKED_TEST_OBSERVABLE_EVIDENCE`; ordinary checkpoint-monitor evidence is not globally forbidden from later policy-governed checkpoint assessment.

`ObservableValidationEvidence` stores analysis-owned result identities, not a
second scientific result schema. The authoritative analysis module remains
responsible for serializing or identifying its native result. The MLFF layer
references that identity when comparing reference and candidate outputs.

## Required module specifications

Before each runtime stage, write or revise specifications for:

```text
sampling/autocorrelation
sampling/blocks
sampling/assignment
training_data/sources
training_data/label_domains
training_data/reference_energies
training_data/feature_metric
training_data/identity
training_data/eligibility
training_data/conditions
training_data/strain
training_data/events
training_data/features/base
training_data/material_profiles
training_data/atom_groups
training_data/profile_features
training_data/profile_events
training_data/features/lta  # optional compatibility profile
training_data/observable_comparisons
training_data/features/mace
training_data/partition
training_data/cross_validation
training_data/checkpoint_selection
training_data/independence
training_data/selection
training_data/exposure
training_data/replay
training_data/replay_retention
training_data/active_learning
training_data/role_inheritance
training_data/export/extxyz
training_data/export/mace
training_data/workflow
```

## Decision summary

The branch follows ten scientific rules.

1. **Independent evidence remains independent.** Cross-validation uses fresh
   models, nested checkpoint monitors, and evaluation folds that never control
   checkpoint choice.
2. **The complete training protocol is the comparison unit.** Replay, objective,
   checkpoint, and exposure choices are part of cross-validation identity.
3. **Selection and E0 fitting are training-domain local.** Transforms, fitted
   metrics, selection, residual difficulty, and atomic-reference corrections do
   not inspect held-out evidence.
4. **Physical facts and workflow decisions are separate.** Occurrence,
   geometry, labels, policies, fitted products, and runtime realizations remain
   distinct.
5. **Data and deformation conventions are explicit.** Label domains, stress,
   energy channels, E0 limitations, and ASE cell-matrix conventions are audited.
6. **Declared focus physics receives explicit coverage.** Profile events,
   atom-group environment quotas, group-resolved metrics, and rare transitions
   cannot be hidden by abundant host statistics. LTA/mobile-ion semantics are an
   optional specialization.
7. **Weights and exposure are audited.** Selection, property loss, head balance,
   and actual MACE loader duplication are separate records.
8. **Locked tests are operationally sealed.** Activation requires frozen
   protocol and committee identities.
9. **Replay and uncertainty policies are enforced.** Candidate checkpoints obey
   target/group/replay constraints, and calibration is bound to the actual final
   committee and an applicability domain.
10. **Expansion is append-only by default.** Active-learning children inherit
    existing roles and add new cohorts without silently rewriting old evidence.
