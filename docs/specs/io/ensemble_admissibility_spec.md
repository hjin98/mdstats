# Stage 11E-STAT2 ensemble-admissibility specification

## Status and ownership

This specification owns the first runtime implementation of **Stage 11E-STAT2**.
The implementation owners are:

- `mdstats.io.admissibility`;
- `mdstats.io.vasp_admissibility`;
- full-source metadata integration in `mdstats.io.vasp`.

STAT2 consumes the signed ENS1 `SimulationControlCertificate`, STAT0
`TrajectoryQualityVerdict`, and STAT1 `ProductionRegimeCatalog`. It does not infer an
ensemble from filenames, `SYSTEM`, target-temperature comments, or mean kinetic
energy. It does not discover sites, select density bandwidths, or certify held-out
sampling adequacy.

## Purpose

STAT2 answers two related questions for each STAT1 regime:

1. Which source interpretations are presently permitted, conditional, diagnostic-only,
   or blocked by the inferred ensemble and tested regime evidence?
2. Which immutable E0b position/force samples belong to one selected regime under those
   permissions?

The stage is deliberately preliminary. It authorizes interpretation classes and builds
an initial source-bound mask overlay; later SAMP, GR, STAT3, and thermodynamic stages
must still establish feature-level support, numerical convergence, and independent
validation.

## Public APIs

The source-general certificate API is:

```python
assess_pmf_admissibility(
    *,
    simulation_control_certificate,
    trajectory_quality_verdict,
    production_regime_catalog,
    source_identity_signature,
    policy=None,
    reweighting_provenance=None,
    approximation_provenance=None,
)
```

The E0b overlay API is:

```python
prepare_evidence_admissibility_overlay(
    sample_catalog,
    *,
    certificate,
    production_regime_catalog,
    regime_id,
)
```

The VASP convenience API is:

```python
assess_vasp_pmf_admissibility(...)
```

Every source, control, quality, production-regime, reweighting, approximation, and
sample-catalog identity used by one result must match exactly. Source mixing is a hard
contract error.

## Persistent records

STAT2 defines immutable, signed records:

- `EnsembleAdmissibilityPolicy`;
- `ReweightingProvenance`;
- `EnsembleApproximationProvenance`;
- `AdmissibilityPermission`;
- `RegimeAdmissibility`;
- `PmfAdmissibilityCertificate`;
- `EvidencePermissionMask`;
- `EvidenceAdmissibilityOverlay`.

All records support deterministic JSON serialization and signature verification.
Boolean sample masks are serialized explicitly and also enter the object signature by
content digest.

## Permission vocabulary

The first implementation reports one decision for each regime and evidence use:

```text
descriptive_density
microcanonical_occupancy
canonical_landscape
npt_landscape
reweighted_landscape
conditional_force
diagnostic_only
```

Decision status is one of:

```text
permitted
conditional
diagnostic_only
blocked
not_applicable
unresolved
```

The associated measure is explicit:

```text
descriptive_spatial_measure
microcanonical_energy_shell
canonical_helmholtz
isothermal_isobaric_gibbs
reweighted_target_measure
mechanical_or_ensemble_conditional_force
none
```

A permission is not a statement that a basin, saddle, PMF, or rate is numerically or
statistically converged.

## Regime separation

STAT1 may emit multiple contiguous regimes. STAT2 evaluates each separately and never
pools them implicitly. Every permission stores the exact `regime_id`, frame interval,
stationarity result, selection-conditioning state, quality outcome, and source-bound
provenance.

The E0b overlay selects exactly one regime. A cross-regime analysis requires an explicit
later policy and a new signature.

## Descriptive spatial evidence

A STAT1 scientific candidate from a non-unqualified source receives
`descriptive_density=permitted`.

An ambiguous or insufficient regime may retain descriptive position evidence as
`diagnostic_only` when the policy allows it. This preserves spatial evidence without
promoting equilibrium, stationarity, or thermodynamic claims.

A rejected regime and an unqualified source do not receive scientific descriptive
permission. Raw parsing records may still exist outside the STAT2 scientific overlay.

## NVE and microcanonical semantics

A stationary NVE regime with affirmative inactive-bias evidence may receive:

```text
microcanonical_occupancy = permitted
measure = microcanonical_energy_shell
```

The permission records the conserved-energy channel and STAT0 energy-conservation
signature. Active constraints make the microcanonical measure conditional and unresolved
constraint evidence remains unresolved. The mean ionic temperature is provenance only;
it is not inserted into `-kBT ln p` to create a canonical PMF.

A canonical approximation from NVE is blocked by default. It may become only
`conditional` when an explicit source-bound `EnsembleApproximationProvenance` is
accepted for that regime and bias nonuse is affirmatively resolved. The approximation
kind, target temperature, evidence digest, constraint state, and limitations are
serialized. An accepted approximation never overrides active or unresolved bias.

## NVT canonical semantics

A stationary, resolved NVT regime with an affirmative inactive-bias result may receive:

```text
canonical_landscape = permitted
measure = canonical_helmholtz
```

The temperature value and uncertainty provenance come from the STAT0 equipartition
record. Active constraints retain a conditional constrained-measure interpretation.
Unresolved bias or constraint evidence blocks thermodynamic promotion rather than being
silently treated as absence.

## NpT semantics

A stationary, resolved NpT regime with active thermostat and barostat and affirmative
inactive-bias evidence may receive:

```text
npt_landscape = permitted
measure = isothermal_isobaric_gibbs
```

The result is explicitly Gibbs/isothermal-isobaric in semantics. STAT2 does not label
an NpT position distribution as a Helmholtz PMF. Active constraints produce a
conditional constrained-measure interpretation.

NpH, multi-thermostat, driven, ramped, and unresolved ensembles remain blocked or
unresolved for these preliminary equilibrium landscape permissions unless a later
specialized policy is implemented.

## Bias and reweighting

Active bias blocks direct canonical, NpT, and microcanonical landscape promotion.
`reweighted_landscape` is permitted only when a source-bound
`ReweightingProvenance` is `verified` and records:

- the method and target measure;
- applicable regime IDs;
- normalized weight availability;
- finite-weight diagnostics;
- effective sample size when available; and
- an external evidence SHA-256 digest.

A declaration without verified weight evidence is retained as `declared_only` and does
not authorize reweighted thermodynamics.

## Conditional-force permission

STAT2 evaluates source-level force provenance but does not bypass Stage C0 force-coordinate
admissibility. A resolved complete source force provider in a scientific regime may
receive `conditional_force=conditional`; the permission remains conditional because the
E0b registration, raw joint mask, PMF force-admissibility status, matched support, and
later partition contracts must also pass.

The overlay intersects this source-level permission with the exact E0b `joint_mask`.
Its replayable `pmf_force_mask` is nonempty only when:

- the regime has an accepted thermodynamic interpretation;
- the STAT2 conditional-force branch is available; and
- E0b reports `PMF_FORCE_ADMISSIBLE` for the exact registered sample catalog.

Mechanical or diagnostic transformed-force evidence may remain visible without becoming
PMF evidence.

## Initial E0b overlay

For one selected regime, let `R` be the sample-aligned regime mask and let E0b provide
immutable raw masks `P0`, `F0`, and `J0=P0&F0`. The E0b catalog must also carry a signed
`source_identity_signature` equal to ENS1/STAT0/STAT1/STAT2. VASP-derived E0b catalogs
inherit this binding from the normalized collection; absent or cross-source bindings fail
closed.

STAT2 constructs permission-specific masks by exact intersection:

```text
descriptive_position = P0 & R & descriptive_permission
microcanonical_position = P0 & R & microcanonical_permission
canonical_position = P0 & R & canonical_permission
npt_position = P0 & R & npt_permission
reweighted_position = P0 & R & reweighted_permission
conditional_force = J0 & R & conditional_force_permission
pmf_force = conditional_force & accepted_thermodynamic_permission
            & E0b_PMF_FORCE_ADMISSIBLE
diagnostic_position = P0 & R & diagnostic_permission
```

The overlay never mutates E0b. Every mask records its base channel and decision status.
A blocked, unresolved, or not-applicable permission produces an empty mask.

## Quality behavior

`strictly_qualified` and `degraded_quality` sources may both receive STAT2 permissions.
Degraded flags remain immutable in every result and are never repaired by STAT2.

`unqualified` blocks scientific permissions. The initial policy does not create a
scientific overlay from a catastrophically failed source.

## Reader behavior

For a complete, unstrided `vasprun.xml` trajectory, `read_vasp_frames(...)` may attach:

```text
pmf_admissibility_certificate
pmf_admissibility_certificate_signature
```

when `assess_admissibility=True`. STAT2 requires the ENS1, STAT0, and STAT1 products;
the reader computes missing upstream products internally for the assessment while
attaching only the products requested by their corresponding flags.

Subselected sources receive:

```text
pmf_admissibility_assessment_status =
    not_evaluated_for_subselected_source_segment
```

and must be assessed as their own immutable source segment.

## Acceptance tests

The focused acceptance boundary includes:

1. stationary NVE -> microcanonical occupancy permitted and canonical landscape blocked;
2. accepted explicit NVE approximation -> canonical landscape conditional, never exact;
3. stationary unbiased NVT -> canonical Helmholtz landscape permitted;
4. stationary unbiased NpT -> Gibbs/NpT landscape permitted, canonical Helmholtz blocked;
5. active bias without verified weights -> direct thermodynamics blocked;
6. verified source-bound reweighting -> reweighted target landscape permitted;
7. ambiguous/insufficient stationarity -> descriptive diagnostic mask retained and
   thermodynamic masks empty;
8. E0b overlay exact regime and raw-mask intersections;
9. PMF-force mask requires both STAT2 thermodynamic permission and E0b PMF-force
   admissibility;
10. deterministic record round trips, tamper rejection, source-signature rejection,
    public exports, and reader metadata behavior;
11. regression of ENS0, ENS1, STAT0, STAT1, E0b, and adjacent Stage 11 modules.

## Non-goals

STAT2 does not:

- prove ergodicity or complete equilibration;
- build SAMP0 crossfit partitions;
- validate basin or corridor recurrence;
- choose density bandwidth, grid, candidate count, or feature correspondence;
- compute a PMF, occupancy free energy, or force-integrated landscape;
- validate reweighting overlap beyond supplied preliminary provenance;
- estimate transition events, barriers, rates, or transport coefficients.
