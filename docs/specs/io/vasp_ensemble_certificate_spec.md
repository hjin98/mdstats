# VASP Ensemble and Force-Provenance Certificate Specification

**Stage:** 11E-ENS1  
**Package target:** `mdstats 0.20.18a0`  
**Status:** implemented

## 1. Purpose

Stage 11E-ENS1 converts the exact source evidence reconstructed by ENS0 into a
signed, source-bound interpretation of the realized molecular-dynamics control
mode. It determines the control-inferred dynamics mode, ensemble, propagator,
thermostat, barostat, cell control, bias/constraint evidence, force-provider
provenance, initial-velocity provenance, and continuation provenance.

ENS1 does not evaluate whether the trajectory actually conserved energy,
reached stationarity, or is thermodynamically admissible for a PMF. Those
questions belong to STAT0-STAT2.

The VASP `SYSTEM` field, file names, directory names, and human labels are
non-authoritative comments. They must never influence the certificate.

## 2. Inputs and source identity

The primary API is:

```python
certify_vasp_simulation_controls(
    source: str | Path | VaspSourceControlBundle,
    *,
    companion_files: Mapping[str, str | Path] | None = None,
) -> SimulationControlCertificate
```

The output is bound to all three ENS0 identities:

- `SourceTrajectoryBundleIdentity.signature`;
- `VaspSourceControlBundle.signature`;
- `VaspRunControls.signature`.

A certificate is invalid if any source signature changes.

## 3. Persistent records

### 3.1 `SimulationControlComponent`

Each component has an independent status:

- `resolved`;
- `unresolved`;
- `conflicting`;
- `not_applicable`.

It records a kind, active state, typed parameters, source evidence, and notes.
Missing companion evidence is never converted into affirmative absence.

### 3.2 `SimulationControlDecision`

Every applied inference rule is recorded with a stable rule identifier,
outcome, decisive control evidence, and explanatory notes.

### 3.3 `SimulationControlCertificate`

The certificate contains:

- control-inferred dynamics mode;
- ensemble and inference status;
- propagator;
- thermostat and friction parameters;
- barostat;
- cell-control mode;
- bias and constraint evidence;
- force-provider and applied-force provenance;
- initial-velocity evidence;
- continuation/restart evidence;
- unresolved reasons and warnings;
- complete decision trace;
- canonical SHA-256 signature.

## 4. VASP inference policy

The initial policy version is
`mdstats.ensemble-inference-policy.v1+vasp-wiki-2026-06`.

### 4.1 Dynamics selection

- `IBRION = 0` selects molecular dynamics.
- Other `IBRION` values are classified as non-MD for this certificate; an MD
  ensemble is then `not_applicable`.

### 4.2 Andersen dynamics

For `MDALGO = 1`:

- `ANDERSEN_PROB = 0` -> NVE, thermostat disabled;
- `ANDERSEN_PROB > 0` -> NVT with Andersen collisions;
- missing or invalid collision probability -> unresolved.

### 4.3 Nose-Hoover family

For `MDALGO = 0 | 2`:

- `SMASS = -3` -> NVE, thermostat disabled;
- `SMASS = -2` -> constant-velocity path, not an equilibrium ensemble;
- `SMASS = -1` -> deterministic velocity-rescaled temperature schedule;
- `SMASS >= 0` -> NVT with Nose-Hoover thermostat;
- missing or unsupported `SMASS` -> unresolved.

When the thermostat is disabled, friction is recorded as `not_applicable`, not
as zero and not as unknown.

### 4.4 Langevin and variable-cell dynamics

For `MDALGO = 3`:

- fixed cell (`ISIF <= 2`) and positive atomic `LANGEVIN_GAMMA` -> NVT;
- fixed cell and all-zero atomic friction -> NVE;
- variable cell (`ISIF = 3`), positive atomic and lattice friction -> NpT;
- variable cell, zero atomic and lattice friction -> NpH;
- mixed or incomplete friction controls -> conflicting/unresolved.

`LANGEVIN_GAMMA` and `LANGEVIN_GAMMA_L` retain their source units of ps^-1.
`PMASS` and `PSTRESS` are retained as control parameters rather than silently
interpreted by ENS1.

### 4.5 Other VASP propagators

- `MDALGO = 4` -> Nose-Hoover-chain NVT;
- `MDALGO = 5` -> CSVR NVT;
- `MDALGO = 13` -> multiple independently thermostatted subsystems and a
  nonstandard multi-thermostat classification;
- unsupported algorithms remain unresolved and do not fall back to a user
  label.

## 5. Cell and barostat provenance

- `ISIF <= 2` -> fixed cell;
- `ISIF = 3` -> variable volume and shape;
- other variable/partial cell modes remain unresolved until a dedicated policy
  exists.

A fixed cell has no active barostat. For `MDALGO = 3`, `ISIF = 3` selects the
Parrinello-Rahman variable-cell family; the lattice friction determines whether
it is thermostatted.

## 6. Bias and constraint provenance

A bound and parsed `ICONST` file is authoritative:

- status `0` -> constrained coordinate;
- status `3`, `4`, `5`, or `8` -> forcefield, step bias, metadynamics, or
  harmonic bias evidence;
- status `7` -> monitoring only.

Metadynamics controls such as `HILLS_H`, `HILLS_W`, and `HILLS_BIN` provide
positive bias evidence but do not replace the collective-variable definition.

If `ICONST`, `REPORT`, `PENALTYPOT`, or related companion evidence is not
provided, ENS1 reports `unresolved`. It does not assert that bias and
constraints were absent.

## 7. Force provenance

ENS1 classifies the force provider from effective source controls:

- standard VASP DFT/Hellmann-Feynman force path;
- VASP MLFF prediction mode;
- VASP on-the-fly hybrid MLFF/DFT training mode;
- unresolved MLFF mode.

Force-array completeness is recorded independently from applied-force
provenance. Complete arrays do not prove that bias or constraint contributions
were absent. Therefore force provenance may remain unresolved even when the
ensemble and source force provider are resolved.

## 8. Initial velocities and continuation

Native velocity records are affirmative evidence. When native velocities are
absent but the first ionic kinetic energy is positive, ENS1 records nonzero
initial kinetic energy while leaving its source unresolved.

A continuation claim requires a bound parent/restart source. A nonzero initial
kinetic energy with default or inconsistent `TEBEG` values may be reported as
consistent with continuation or external initialization, but it is not proof of
lineage.

## 9. Execution policy

An unresolved or conflicting ensemble blocks only methods that require a
resolved ensemble interpretation. Descriptive coordinate, density, and
structural analyses may continue if later STAT0 hard-integrity checks pass.

Bias, constraint, or force-provenance uncertainty does not invalidate the raw
trajectory. It blocks only the scientific interpretation that needs the missing
provenance, such as an unqualified physical mean-force claim.

## 10. Real Na-LTA acceptance fixture

The supplied 1,500-step `vasprun.xml` must resolve as:

- VASP molecular dynamics;
- `MDALGO = 2`, `SMASS = -3`, `ISIF = 2`;
- fixed-cell NVE;
- Nose-Hoover-family propagator with thermostat disabled;
- thermostat friction `not_applicable`;
- no barostat;
- complete DFT force arrays;
- bias and constraint status unresolved without companion evidence;
- nonzero initial kinetic energy with unresolved velocity source;
- continuation/external initialization possible but not proven;
- misleading `SYSTEM = ... NVT ...` ignored.

## 11. Tests

Focused tests must cover:

- misleading `SYSTEM` label rejection;
- Nose/Andersen NVE and NVT branches;
- Langevin NVE, NVT, NpT, and NpH branches;
- `SMASS = -1` and `-2` driven modes;
- bound `ICONST` constraint and bias classification;
- force-provider and force-completeness separation;
- immutable serialization and tamper detection;
- VASP frame-reader metadata integration;
- exact real-source replay.

## 12. Primary VASP references

- VASP Wiki, `MDALGO`: https://vasp.at/wiki/MDALGO
- VASP Wiki, `SMASS`: https://vasp.at/wiki/SMASS
- VASP Wiki, NVE ensemble: https://vasp.at/wiki/NVE_ensemble
- VASP Wiki, NVT ensemble: https://vasp.at/wiki/NVT_ensemble
- VASP Wiki, NpT ensemble: https://vasp.at/wiki/NpT_ensemble
- VASP Wiki, NpH ensemble: https://vasp.at/wiki/NpH_ensemble
- VASP Wiki, `LANGEVIN_GAMMA`: https://vasp.at/wiki/LANGEVIN_GAMMA
- VASP Wiki, `LANGEVIN_GAMMA_L`: https://vasp.at/wiki/LANGEVIN_GAMMA_L
- VASP Wiki, `ICONST`: https://vasp.at/wiki/ICONST
- VASP Wiki, metadynamics calculations:
  https://vasp.at/wiki/Metadynamics_calculations
