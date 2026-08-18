# Trajectory temperature, integrity, and quality specification

**Stage:** 11E-STAT0  
**First implementation:** `mdstats 0.20.19a0`  
**Status:** normative

## Purpose

STAT0 converts the immutable ENS0 source evidence and ENS1 control certificate into
an equally immutable source-segment quality assessment. It reconstructs ionic
temperature from ionic kinetic energy, tests catastrophic integrity separately from
manageable numerical degradation, evaluates the ensemble-appropriate conserved
quantity when one is available, and produces one of exactly three execution verdicts:

```text
strictly_qualified
degraded_quality
unqualified
```

Only `unqualified` blocks production scientific analysis by default.
`degraded_quality` emits one warning and remains available to downstream analyses with
all failed checks, effect sizes, assumptions, and source signatures attached.

STAT0 does not select a production interval, certify stationarity, or authorize a PMF.
Those responsibilities remain in STAT1 and STAT2.

## Inputs

The source-general evaluator consumes:

- one normalized `AtomisticFrameCollection` with trajectory semantics;
- one exact `FrameEnergyCatalog` aligned to the evaluated frames;
- one `NumericalMDQualityControls` record;
- one signed `SimulationControlCertificate`;
- the matching `SourceTrajectoryBundleIdentity` signature;
- one versioned `TrajectoryQualityPolicy`.

The source identity, control bundle, coordinate payload, and frame axis must describe the
same source trajectory bundle. A user comment such as VASP `SYSTEM` is never an input to
quality inference.

## Ionic temperature

The instantaneous ionic temperature is

$$
T_t = \frac{2K_{\mathrm{ion}}(t)}{f_{\mathrm{ion}}k_{\mathrm B}}.
$$

The `IonicTemperatureDefinition` records:

- the exact kinetic-energy channel and source path;
- atom count and active ionic coordinate count;
- fixed-coordinate and constraint evidence;
- whether center-of-mass translation is excluded;
- the resulting ionic degrees of freedom;
- any source-default or approximation note.

The first VASP implementation uses the documented periodic-system convention
`3N - 3` when all atoms are represented, the cell is periodic, and no affirmative
fixed-coordinate count is available. The approximation is retained in metadata rather
than hidden. Bound constraint evidence will supersede this default in later adapters.

`IonicTemperatureStatistics` retains:

- the complete derived temperature series;
- represented-time mean and standard deviation;
- minimum and maximum;
- integrated autocorrelation time and effective sample count;
- block length, block means, and block count;
- standard error and confidence interval of the mean;
- drift slope and confidence interval;
- a temperature-stability outcome.

The standard deviation is a physical fluctuation. Confidence in the mean and trend is
computed from autocorrelation-aware complete-system blocks; adjacent frames are never
counted as independent observations.

## Integrity and numerical-quality checks

Each check is an immutable `TrajectoryQualityCheck` with:

```text
check_id
severity = hard_integrity | soft_quality | diagnostic
requirement = hard_integrity_required | verdict_critical | method_specific | optional
status = pass | fail | warning | unavailable | insufficient | not_applicable
measured_value
threshold
units
message
evidence
```

### Hard integrity

The first implementation checks at least:

- positive frame and atom counts;
- complete source positions and cells;
- finite normalized coordinates, cells, forces, and energy channels;
- positive nonsingular cell determinants;
- strictly increasing and uniformly spaced source steps and physical times;
- persistent atom identity through the normalized collection contract;
- no catastrophic periodic atomic overlap;
- no runaway force, speed, energy jump, or energy drift;
- no internal source-frame gaps.

A hard failure produces `unqualified` and `TrajectoryIntegrityError` unless diagnostic
mode explicitly requests the certificate without continuation.

### Soft quality

Soft checks include:

- electronic convergence reaching `NELM`;
- `EDIFF` relative to the policy target for precision MD;
- `PREC`, `LREAL`, `ROPT`, and timestep diagnostics;
- requested-versus-present ionic-step mismatch;
- temperature-mean confidence and temperature trend;
- ensemble-appropriate energy conservation;
- source energy-identity consistency.

A soft failure or material warning produces `degraded_quality`, emits exactly one
`TrajectoryDegradedQualityWarning`, and does not block downstream execution.
A genuinely optional and method-irrelevant missing channel is `unavailable` and does
not degrade the trajectory.


## Diagnostic requirement matrix

`DiagnosticRequirement` is the persistent classification for each check. Severity and requirement are independent metadata. Severity controls the top-level
execution verdict; requirement states how a downstream method may use the evidence:

| Requirement | Meaning | Missing or failed evidence |
|---|---|---|
| `hard_integrity_required` | Mandatory for any production trajectory analysis | Produces `unqualified` when the hard check fails |
| `verdict_critical` | Required for the general quality verdict | Produces `degraded_quality` when soft evidence fails or is materially insufficient |
| `method_specific` | Required only by a named downstream estimator | Does not change the general execution verdict; that method must fail closed or downgrade its own certificate |
| `optional` | Informative diagnostic only | Remains `unavailable` without degrading the trajectory |

The requirement field prevents optional absent data from degrading an otherwise usable
trajectory and prevents the general quality verdict from silently authorizing a method
whose own required evidence is absent.

## Realized ensemble consistency

STAT0 creates a signed `RealizedEnsembleConsistency` record separate from the ENS1
control-inferred ensemble. The first implementation checks the realized fixed-cell NVE
behavior using:

- observed cell-volume range and full cell-matrix deviation;
- inactive Nosé-energy channels, when present;
- source-reported NVE total-energy drift.

Its status is one of:

```text
consistent
degraded
insufficient
inconsistent
```

A degraded NVE consistency record contributes evidence to method-specific admissibility
but does not redefine the ENS1 ensemble and does not by itself block structural analysis.
The first implementation is explicitly diagnostic-only for non-NVE ensembles; source-
specific extended-Hamiltonian checks belong to later adapters.

## NVE energy conservation

For a resolved NVE source with a complete source-reported `total` channel, STAT0 records:

- initial, final, mean, and standard deviation;
- linear drift in eV/ps and eV/(atom ps);
- observation-span change;
- detrended residual standard deviation;
- maximum adjacent-frame energy jump;
- source identity residual, when `total`, ionic kinetic, and the relevant electronic
  energy channel are all available.

The current policy separates a strict conservation tolerance from a hard drift threshold. The hard value corresponds to approximately one room-temperature kT per atom over a 1 ps reference interval. A smooth, measurable drift may therefore yield `degraded_quality` without
becoming `unqualified`.

For thermostat or variable-cell ensembles, STAT0 records available energy diagnostics
but does not pretend that the NVE `total` channel is the conserved quantity. Extended
Hamiltonian handling remains source- and ensemble-specific.

## Default policy v2

The initial default policy is versioned and serializable. Its principal values are:

```text
confidence_level = 0.95
minimum_independent_blocks = 4
minimum_block_frames = 16
strict_ediff_eV = 1e-6
warning_ediff_eV = 1e-4
strict_NVE_drift = 1e-3 eV/(atom ps)
hard_NVE_drift = 2.6e-2 eV/(atom ps)
catastrophic_energy_jump = 1 eV/atom/frame
catastrophic_force_norm = 100 eV/Angstrom
catastrophic_speed = 1000 Angstrom/ps
catastrophic_overlap = 0.35 Angstrom
strict_temperature_CI_half_width = max(5 K, 5% of mean)
strict_temperature_span_drift = max(5 K, 0.5 standard deviations)
strict_fixed_cell_relative_deviation = 1e-10
inactive_thermostat_energy_tolerance = 1e-8 eV
NVE_hard_reference_temperature = 300 K
NVE_hard_reference_time = 1 ps
```

These are policy values, not universal physical constants. Every result stores the
policy signature and measured effect sizes so later versions can be replayed.

## Public APIs

```python
assess_trajectory_quality(...)
assess_vasp_trajectory_quality(...)
```

`read_vasp_frames` may attach a source-wide STAT0 verdict automatically when the full
unstrided `vasprun.xml` trajectory is read. Subselected reads do not silently inherit a
full-source verdict; their metadata records that a dedicated segment assessment is
required.

## Real-source acceptance

For the supplied 1,500-step Na-LTA source, the first implementation must:

- reconstruct ionic temperature from the complete `kinetic` channel;
- use 501 ionic degrees of freedom for 168 periodic atoms;
- report a mean near 320 K and a standard deviation near 14 K;
- resolve fixed-cell NVE from the ENS1 certificate;
- detect the approximately `-0.205 eV/ps` total-energy drift;
- classify the source as `degraded_quality`, not `unqualified`;
- continue to permit compatible structural and occupancy analyses;
- retain the misleading `SYSTEM` text only as a non-authoritative diagnostic.

## Non-goals

STAT0 does not:

- infer a production interval;
- prove equilibrium or ergodicity;
- construct a canonical PMF;
- validate basin or saddle sampling;
- repair or detrend source data before downstream use;
- hide degraded evidence by replacing source channels with fitted values.
