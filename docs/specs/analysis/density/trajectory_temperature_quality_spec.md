---
title: "Trajectory Ionic Temperature and Quality Verdict Specification"
version: "0.20.19a0"
date: "2026-07-27"
---

# Purpose

This planning-parent specification owns the revision-43 contracts. The implemented runtime contract is `../../io/trajectory_quality_spec.md`.

This specification owns the revision-43 contracts for source-derived ionic
temperature, deep numerical-MD control extraction, and execution behavior for
strictly qualified, degraded-quality, and unqualified trajectories.

# Ionic temperature

For every frame with a valid ionic kinetic energy,

$$
T_t = \frac{2K_{\mathrm{ion}}(t)}{f_{\mathrm{ion}}k_{\mathrm B}}.
$$

`IonicTemperatureDefinition` records the exact kinetic channel and active ionic
degree-of-freedom count. `IonicTemperatureStatistics` records the represented-time
mean, standard deviation, autocorrelation time, effective sample count, confidence
interval, block means, and drift. Adjacent frames are not treated as independent.

# Numerical control extraction

The VASP adapter reads explicit `<incar>` and effective `<parameters>` values from
`vasprun.xml` and preserves their source precedence. At minimum it extracts `POTIM`,
`EDIFF`, `PREC`, `LREAL`, `ROPT`, `NELM`, `NELMIN`, `ALGO`/`IALGO`, `ENCUT`, `ISYM`,
requested and present ionic-step counts, and per-step electronic iteration counts and
convergence outcomes. User `SYSTEM` text has no scientific authority.

# Verdicts

The only top-level quality outcomes are:

```text
strictly_qualified
degraded_quality
unqualified
```

- `strictly_qualified`: all hard integrity and active soft quality checks pass.
- `degraded_quality`: the trajectory is finite and quantitatively usable but has one
  or more manageable numerical-quality violations. Analysis proceeds, one warning is
  emitted, and every result retains the verdict and failed checks.
- `unqualified`: catastrophic integrity failure. Production scientific APIs raise
  `TrajectoryIntegrityError`; diagnostic-only parsing may return the failure record.

The deterministic aggregation rule is hard failure -> unqualified; otherwise any soft
failure -> degraded quality; otherwise strictly qualified.

# Separation from scientific admissibility

The quality verdict decides whether the trajectory can be analyzed. It does not decide
whether a particular thermodynamic estimator is mathematically applicable. Ensemble,
stationarity, reweighting, PMF, and kinetic gates remain separate signed certificates.

# Acceptance

The real Na-LTA NVE continuation fixture must expose the source controls and complete
1,500-step trace without consulting its misleading `SYSTEM` label. Its measurable NVE
energy drift may produce `degraded_quality`; it must not be rejected unless an
independent hard integrity check fails.
