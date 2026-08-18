# Na-LTA Stage 11E-ENS0 source replay

This replay exercises the public `read_vasp_run_controls` API against the supplied 1,500-step `vasprun.xml`.

ENS0 reconstructs exact source controls and named channels. It deliberately does **not** infer the ensemble, trajectory quality, stationarity, or PMF admissibility.

## Source identity

- mdstats version: `0.20.17a0`
- source program: `vasp 6.4.2`
- atom count: `168`
- ionic steps: `1500`
- source identity signature: `92fd811b47ff6d3ff7408a19fe3cb786599827465066075b2615a9cc67c37774`
- full ENS0 bundle signature: `787b2cfb3029266ac401702bbe8cf625fc2a43129f36f79cf275f44d416adc9d`
- parse wall time: `1.546 s`
- maximum RSS: `229036 KiB`

## Reconstructed controls

| Control | Reconstructed value |
|---|---:|
| `MDALGO` | `2` |
| `SMASS` | `-3.0` |
| `ISIF` | `2` |
| `POTIM` | `1.0` |
| `EDIFF` | `1e-05` |
| `NELM` | `100` |
| `NELMIN` | `2` |
| `IALGO` | `38` |
| `PREC_explicit` | `Accurate` |
| `PREC_effective` | `accura` |
| `LREAL_explicit` | `Auto` |
| `LREAL_effective` | `True` |
| `ROPT` | `(-0.00025, -0.00025, -0.00025, -0.00025)` |
| `NSW` | `1500` |

The user-provided `SYSTEM` text is retained only as a `comment_only` diagnostic and has no authority over later ensemble inference.

## Named energy channels

| Channel | Role | Present | Complete |
|---|---|---:|---:|
| `e_0_energy` | `electronic_zero_smearing_extrapolation` | 1500/1500 | true |
| `e_fr_energy` | `electronic_free_energy` | 1500/1500 | true |
| `e_wo_entrp` | `electronic_energy_without_entropy` | 1500/1500 | true |
| `kinetic` | `ionic_kinetic_energy` | 1500/1500 | true |
| `lattice kinetic` | `lattice_kinetic_energy` | 1500/1500 | true |
| `nosekinetic` | `nose_thermostat_kinetic_energy` | 1500/1500 | true |
| `nosepot` | `nose_thermostat_potential_energy` | 1500/1500 | true |
| `total` | `source_reported_total_energy` | 1500/1500 | true |

## Numerical evidence reconstructed for later stages

- SCF iterations per ionic step: `3` through `24`.
- ionic steps reaching `NELM`: `0`.
- native velocity frames: `0`.
- positions complete: `True`.
- cells complete: `True`.
- forces complete: `True`.
- stresses complete: `True`.

## Boundary

No ensemble, thermostat, conservation, equilibrium, quality, or PMF verdict is produced in ENS0. Those interpretations begin in ENS1 and STAT.
