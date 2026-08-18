# MLFF-DATA9A3 development and production qualification report

## Release

- Package: `mdstats`
- Version: `0.20.40a0`
- Stage: MLFF-DATA9A3, production bulk-LTA target-corpus qualification
- DATA9B status: gated; no DATA9B training was started

## Scope

DATA9A3 qualifies the actual 27-source bulk-LTA target corpus through DATA5.
Uploaded filenames are retained only as opaque source labels. Composition,
ensemble, thermostat target, reference cell, finite strain, and trajectory
conditions are inferred from VASP metadata and ionic data.

The implementation adds restartable source-isolated trajectory materialization,
interrupted-XML normalization with byte-level provenance, metadata-derived
condition/reference inference, linear-time DATA5 strain lookup, immutable
production resource and qualification records, and verified-digest reuse for
large DATA3-DATA5 artifacts.

## Corpus result

- 27 fixed-cell Langevin NVT trajectories
- 37,632 complete ionic frames
- 168 atoms per frame
- Seven inferred compositions
- Thermostat targets: 300, 600, 700, and 800 K
- Strain classes:
  - unstrained: 29,332 frames
  - hydrostatic: 2,700 frames
  - orthorhombic/mixed: 2,800 frames
  - shear: 2,800 frames
- Protected events:
  - force-threshold: 1,365
  - temperature-deviation: 26
- No exact geometry-duplicate groups
- No exact labeled-duplicate groups

Two interrupted VASP XML streams were normalized without changing the original
sources. Only fully closed `<calculation>` records were retained:

- `LTA_K.700K.init.xml`: 1,378 frames retained; 25,362 incomplete suffix bytes discarded
- `LTA_K.800K.init.xml`: 1,354 frames retained; 27 incomplete suffix bytes discarded

Original, normalized, retained, and discarded-content hashes are recorded.

## DATA5 result

- DATA5 content digest:
  `89dac878625aa194072171a12dbeaa0f9e5d47a97c7510f8cd4ee2d7aa8868a0`
- 97 partition units
- 25 conditions
- One label domain
- Three cross-validation folds
- Leakage audit: passed
- Feasibility: `supported_with_temporal_blocks_only`
- Reason: not every condition supports every requested outer role

Independence evidence by unit:

- `independent_thermodynamic_run`: 14
- `purged_temporal_block`: 79
- `insufficient_independence`: 4

Outer-role unit counts:

- development: 74
- outer monitor: 4
- uncertainty calibration: 4
- locked interpolation test: 4
- purged: 11

Outer-role frame counts:

- development: 32,070
- outer monitor: 1,040
- uncertainty calibration: 749
- locked interpolation test: 1,122
- purged: 2,651

## Production qualification record

- Status: `conditionally_ready`
- Target corpus qualified: true
- Full DATA9A passed: false
- Qualification digest:
  `bccdfb5fd06be186d58555d2b1b8c695c843411ea1bbb4bccc24f778300ea15a`

Remaining fail-closed blockers:

1. `lta_site_coverage_not_materialized`
2. `foundation_features_not_materialized`
3. `foundation_residual_e0_not_materialized`
4. `data8_artifacts_not_materialized`
5. `production_replay_corpus_not_bound`

These are not DATA5 defects. They require the LTA ring/site catalog,
checkpoint-bound production DATA6/DATA7 realization, executable production
DATA8 jobs, and the exact replay corpus if replay fine-tuning is selected.
No missing artifact was inferred or fabricated.

## Resource evidence

| Stage | Wall time | Peak RSS | Artifact size |
|---|---:|---:|---:|
| XML normalization | 18.279 s | 371.88 MiB | 19,832 B |
| DATA2 controls/catalog | 14.688 s | 235.83 MiB | 137,175 B |
| Source-isolated trajectory audit | 4.392 s parent | 617.39 MiB | 31,077 B |
| Condition/reference inference | 0.162 s | 546.53 MiB | 162,117 B |
| DATA3 frame catalog | 153.715 s | 1,333.5 MiB | 19,263,100 B |
| DATA4 full-resolution features | 949.038 s | 2,154.0 MiB | 50,903,439 B |
| DATA5 partition qualification | 332.855 s | 2,133.50 MiB | 1,535,777 B |

## Implementation changes

- Replaced DATA5's per-frame linear strain-record scan with a frame-UID index.
- Added `ProductionGateStatus`, `ProductionStageResourceRecord`, and
  `ProductionCorpusQualificationRecord`.
- Added `build_production_corpus_qualification_record` with fail-closed DATA5
  usability checks and explicit temporal-block/independence warnings.
- Added verified serialized digest inputs so validated large artifacts are not
  repeatedly canonicalized merely to recover already-verified digests.
- Added `tools/finalize_lta_data9a3_qualification.py`.
- Added canonical DATA9A3 specification and updated the stage plan,
  architecture manual, dependency graph, README, and changelog.
- Regenerated the relevant PDF specifications and architecture manual.

## Focused verification

- DATA5 and DATA9A3 implementation: 17 passed
- Final architecture/specification checks: 15 passed
- DATA8/DATA9A non-slow regression group: 37 passed, 1 expected skip
- Real MACE v0.3.16 naive/replay parser and loader dry run: passed
- Real MACE v0.3.16 one-epoch two-head replay training, checkpoint inventory,
  head enumeration, target-head extraction, and finite evaluation round trip:
  passed
- Wheel clean-target import: passed
- Python `compileall`: passed

The attempted single-process aggregate of every non-slow MLFF test was stopped
by an order-dependent external MACE subprocess shutdown stall after substantial
progress. The same real-MACE parser/dry-run test and training smoke both pass in
isolated release-gate runs. Scientific artifacts were produced before shutdown;
the evidence bundle records the isolated passing runs rather than claiming the
aggregate run passed.

## Restart provenance

The execution sandbox restarted after the initial production qualification.
The release was reconstructed from the archived `0.20.39a0` source package and
rebound to the retained immutable source catalog, DATA3 digest, and DATA4
digest. DATA5 was regenerated and reproduced the previously obtained digest
exactly. No filename-derived scientific condition was introduced during
reconstruction.
