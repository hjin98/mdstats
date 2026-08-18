---
title: "VASP Source Controls and Energy Catalog Specification"
version: "0.20.61a0"
date: "2026-08-04"
---

# Purpose

This specification owns the first executable Stage 11E-ENS0 boundary. It reconstructs
source controls and exact named energy channels from `vasprun.xml` without inferring the
ensemble, stationarity, trajectory quality, or PMF admissibility.

The implementation is split between:

```text
mdstats.io.source_controls   source-general immutable records
mdstats.io.vasp_controls     versioned VASP XML adapter
mdstats.io.vasp              normalized trajectory integration
```

# Non-authoritative user labels

`SYSTEM`, filenames, directory names, and user descriptions are comments. They are
retained as `UserLabelDiagnostic` records with

```text
authority = comment_only
```

and are excluded from ensemble or method inference. A string such as
`Na-LTA 300K NVT AIMD` must not override `MDALGO`, `SMASS`, `ISIF`, or any later
source-control certificate.

# Source trajectory bundle identity

`SourceTrajectoryBundleIdentity` binds one primary source to:

- exact primary-file SHA-256 and size;
- source program and version;
- atom order and atom count;
- ionic-step count and frame axis;
- streamed coordinate/cell payload digest;
- companion-control manifest signature.

Absolute filesystem paths do not enter the scientific signature. A later C0 adapter must
retain this same bundle signature when it consumes coordinates from the source.

# Companion manifest

`SimulationControlBundleManifest` records the primary source and every recognized
companion role using only:

```text
present_and_bound
known_absent
not_applicable
not_provided
required_missing
```

A companion file is `present_and_bound` only when the caller explicitly supplies it.
Merely finding a same-named file in the source directory is insufficient because it may
belong to another run. Missing `ICONST`, `REPORT`, `PENALTYPOT`, or metadynamics evidence
is therefore `not_provided`, not proof of nonuse.

# Exact controls and precedence

`VaspRunControls` retains every `<incar>` and `<parameters>` `i` or `v` record with:

- original tag name;
- typed value;
- original text;
- source value type;
- section path;
- duplicate occurrence index;
- authority (`explicit_input` or `effective_parameter`).

The precedence contract is:

```text
effective_parameters_for_realized_values
explicit_incar_for_input_provenance
```

Unknown and source-version-specific controls are retained rather than coerced into a
known category. `VaspRunControls` implements the source-general `SimulationRunControls`
protocol. ENS1, not ENS0, interprets the controls.

# Frame energy catalog

`FrameEnergyCatalog` preserves every exact name under each ionic
`calculation/energy` block. No generic field replaces these source channels.

The VASP adapter assigns initial semantic roles to well-known names:

| Source name | Initial semantic role |
|---|---|
| `e_fr_energy` | electronic free energy |
| `e_0_energy` | zero-smearing extrapolated electronic energy |
| `e_wo_entrp` | electronic energy without entropy |
| `kinetic` | ionic kinetic energy |
| `nosepot` | Nose thermostat potential energy |
| `nosekinetic` | Nose thermostat kinetic energy |
| `lattice kinetic` | lattice kinetic energy |
| `total` | source-reported total energy |

Unknown names remain `source_specific_energy`. Every channel records eV units, source
path, frame count, present count, completeness fraction, exact values including missing
entries, and a value digest. The catalog does not decide which combination is conserved;
STAT0 consumes the named channels after ENS1 resolves the dynamics.

# Numerical MD quality controls

`NumericalMDQualityControls` reconstructs evidence needed by later quality analysis:

```text
POTIM
NSW and present ionic-step count
inferred full-output stride when justified by exact count equality
EDIFF
NELM and NELMIN
ALGO and IALGO
explicit and effective PREC
explicit and effective LREAL
ROPT
ENCUT
ISYM
per-step SCF iteration counts
whether the configured electronic iteration limit was reached
position/cell/force/stress completeness
native-velocity frame count
per-energy-channel completeness
source XML parse completeness and interruption diagnostic
whether a complete unclosed final ionic record was recovered
whether an ambiguous incomplete final ionic tail was discarded
```

A step count below `NELM` is recorded only as not reaching the configured limit. ENS0 does
not claim electronic convergence from that fact alone.

# Public API

```python
from mdstats import read_vasp_run_controls

bundle = read_vasp_run_controls(
    "vasprun.xml",
    companion_files={"constraint_definition": "ICONST"},
)
```

The result is `VaspSourceControlBundle`, containing:

```text
source_identity
manifest
run_controls
energy_catalog
numerical_quality_controls
```

All records are immutable, canonical-JSON signed, and support strict `to_dict` / `from_dict`
round trips. Tampered signatures are rejected.

`read_vasp_frames()` reuses the same parser and attaches the source identity, control
record, exact energy catalog, and numerical-quality record to collection metadata. The
legacy normalized potential/kinetic/total arrays remain unchanged for compatibility.

# Interrupted-stream recovery and fail-closed behavior

A `vasprun.xml` may end while VASP is still writing. ENS0 accepts only parser
failures that are both interruption-like and located at the physical end of the
file. Completed `<calculation>` records are retained. If the final
`<calculation>` lacks only its closing tag, it is retained only when its
positions, cell, forces, and energy payload are all complete and finite. An
ambiguous partial final calculation is discarded while prior complete records
remain usable.

Recovery is explicit evidence, not silent repair. `NumericalMDQualityControls`
records `source_parse_complete`, `source_parse_warning`,
`recovered_unclosed_ionic_step`, and `discarded_incomplete_ionic_tail`. The
trajectory-quality layer reports an interrupted source as a soft-quality warning
and separately checks requested-step completion.

ENS0 raises `SourceControlError` for:

- a missing primary XML source;
- malformed XML away from EOF or a non-interruption parser failure;
- an interrupted source lacking control blocks, atom identities, or any complete
  usable ionic calculation;
- non-finite signed energy/control values;
- inconsistent channel lengths;
- invalid manifest binding;
- invalid immutable record construction.

`SourceControlSerializationError` is raised for schema or signature mismatches.
Missing optional controls, companion files, and energy channels are represented
explicitly and do not by themselves reject coordinate parsing or descriptive
analysis.

# Acceptance tests

The permanent synthetic tests require:

- explicit/effective tag preservation and precedence;
- `SYSTEM` retained only as `comment_only`;
- exact named energy channels and partial-channel completeness;
- SCF iteration and quality-control traces;
- explicit-only companion binding;
- deterministic signatures and strict round trips;
- metadata integration through `read_vasp_frames`;
- trailing root-tag interruption recovery;
- complete unclosed final-calculation recovery;
- ambiguous partial-tail discard;
- hard rejection of mid-file structural corruption and critically ambiguous streams;
- public root exports.

The real Na-LTA source replay must reconstruct, without consulting `SYSTEM`:

```text
program/version = VASP 6.4.2
atom count = 168
ionic steps = 1500
MDALGO = 2
SMASS = -3
ISIF = 2
POTIM = 1 fs
EDIFF = 1e-5 eV
NELM = 100
PREC explicit/effective = Accurate/accura
LREAL explicit/effective = Auto/true
ROPT = four values of -2.5e-4
SCF iterations = 3 through 24
native velocity frames = 0
```

It must expose complete `e_fr_energy`, `e_0_energy`, `e_wo_entrp`, `kinetic`,
`nosepot`, `nosekinetic`, `lattice kinetic`, and `total` channels for all 1500 steps.
Ensemble resolution remains the next ENS1 stage.
