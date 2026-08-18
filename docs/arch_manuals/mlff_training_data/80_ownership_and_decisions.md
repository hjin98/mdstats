# Part VII - Ownership boundaries and decision summary

## Physical-observable validation ownership boundary

Physical observable calculation is not owned by `mdstats.training_data`. RDF, coordination, neighbor-angle statistics, connectivity, topology statistics, MSD, VACF, spectra, VDOS, diffusion, displacement distributions, current correlations, ionic conductivity, and related physical observables remain authoritative in their respective `mdstats.analysis` modules, specifications, and architecture manuals.

The MLFF layer owns only:

1. choosing an advisory observable-recommendation profile and an explicit recipe;
2. constructing an immutable recipe of analysis call IDs and parameters;
3. running the same recipe on matched reference and MLFF collections;
4. preserving verified collection/frame-selection identity, symmetric reference/candidate trajectory-generation identity, runtime/capability identity, warning records, and analysis-owned result identities;
5. binding execution to an explicit statistical role and, where required, a predeclared comparison policy, protocol freeze, and test-activation record;
6. applying comparison and acceptance policies only after those policies are frozen and independently identified.

It does not own physical numerical algorithms, normalization, neighbor definitions, plateau estimators, spectral transforms, or graph statistics.

The standardized analysis facade is `mdstats.analysis.observable_validation`. The MLFF-owned bridge delegates to that facade and stores no duplicate scientific arrays or competing result schemas.

Advisory recommendation profiles include generic condensed, crystalline-solid, amorphous-solid, liquid, and interface use cases. They are call-set recommendations, not automatic material classifiers. Users still supply applicable groups/species, cutoffs, projections, trajectory windows, thermodynamic conditions, and geometry-specific inputs. Ionic-transport and porous/zeolite/ring/cage/site analyses are explicit extensions and are never activated merely because a reference application uses those concepts.

### Selection features versus validation observables

Compact structural descriptors used for partitioning or frame selection are MLFF workflow inputs. Full physical observables used to judge a trained model remain analysis products. An MLFF feature provider may call a lower-level analysis primitive only under that primitive's explicit contract and records the owner API; it cannot redefine the observable. Expensive trajectory observables such as diffusion, VDOS, conductivity, or residence statistics are validation jobs rather than ordinary frame-selection features.

### Observable execution identity and evidence

Observable recipes validate declared dependencies before execution, preflight collection requirements, and bind versioned capability/codec identity. Supplied collection identities are recomputed and verified; location hints do not alter scientific identity. Reference and candidate trajectory-generation records bind their output collections symmetrically. Native analysis results receive analysis-owned identities; MLFF evidence stores those identities plus paired roles, warnings, durations, runtime identity, and upstream lineage.

Static equation-of-state, elasticity, finite-temperature thermomechanical response, viscosity, phonon, surface/interface, defect, and migration analyses remain owned by their dedicated analysis architecture/specification families.

### Statistical role, policy ordering, and locked-test leakage

Physical-observable evidence has one explicit role such as `training_diagnostic`, `checkpoint_monitor`, `outer_validation`, `calibration`, `locked_test`, or `external_benchmark`. The role is not inferred from filenames or caller context.

The allowed dependency order is:

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

The reverse edge is forbidden. Realized observables must not be inspected to choose their own acceptance policy. Locked-test activation additionally requires the frozen training protocol, partition assignment, and explicit evaluation activation. Locked-test observable evidence cannot alter feature fitting, selection, training protocol, checkpoint selection, calibration policy, or acquisition.

## Documentation and module ownership

The current multi-view production chain assigns scientific selection to MVSEL2, reconstructible continuation state to MVSTATE2, exact active-shell exchange to REPAIR2, and independent acceptance evidence to MVQUAL. MVIDX1 continues to own the exact sparse graph and exposes a forward-only runtime projection to v2 consumers. MVSEL1, MVSTATE-REUSE1, and REPAIR1 retain their historical schemas and readers but do not own new-campaign execution.

Cross-cutting architecture defines ownership and data/control relationships. Detailed current behavior belongs in the corresponding module specifications under `docs/specs/`. A current module specification may strengthen a local contract but may not contradict the cross-cutting scientific invariants in this manual.

Proposed new module behavior, migrations, or developer sequencing is coordinated in `workplans/` until implemented and accepted. Completed implementation chronology belongs in history/release notes; qualification evidence belongs in audits/release evidence; performance evidence belongs in benchmarks.

## Decision summary

The MLFF subsystem follows ten scientific rules.

1. **Independent evidence remains independent.** Cross-validation uses fresh models, nested checkpoint monitors, and evaluation folds that never control checkpoint choice.
2. **The complete training protocol is the comparison unit.** Replay, objective, checkpoint, exposure, backend, and other protocol-defining choices are part of comparison identity.
3. **Selection and E0 fitting are training-domain local.** Transforms, fitted metrics, selection, residual difficulty, and atomic-reference corrections do not inspect held-out evidence.
4. **Physical facts and workflow decisions are separate.** Occurrence, geometry, labels, policies, fitted products, and runtime realizations remain distinct record responsibilities.
5. **Data and deformation conventions are explicit.** Label domains, stress, energy channels, E0 limitations, and ASE cell-matrix conventions are declared and audited.
6. **Declared focus physics receives explicit coverage.** Profile events, atom-group environment quotas, group-resolved metrics, and rare transitions cannot be hidden by abundant host statistics; material-specific semantics are explicit optional specializations.
7. **Weights and exposure are audited.** Selection, property loss, head balance, and realized loader duplication are separate records.
8. **Locked tests are operationally sealed.** Activation requires frozen protocol and committee identities plus the applicable explicit activation decision.
9. **Replay and uncertainty policies are enforced.** Candidate checkpoints obey target/group/replay constraints, while calibration is bound to the actual final committee and declared applicability domain.
10. **Expansion is append-only by default.** Active-learning children inherit existing roles and add new cohorts without silently rewriting prior evidence unless a new evaluation lineage is explicitly created.
