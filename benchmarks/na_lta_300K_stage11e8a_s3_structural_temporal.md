# Na-LTA 300 K Stage 11E8a-S3 structural and temporal benchmark

## Source and runtime

- Package: `mdstats 0.20.13a0`
- Stage: `11E8a-S3`
- Raw trajectory SHA-256: `ad54b98c5d927d722ac1cb8a4a3b1fe472a50603a6e8ece5497b06e55a8679eb`
- ASE: `3.29.0`, installed from the supplied local archive
- Frames: 1,500
- Atoms: 168
- Force array: `(1500, 168, 3)`
- Represented duration: 1.499 ps
- ASE parse: 2.647 s
- S0--S3 analysis: 22.415 s
- Parse plus analysis: 25.062 s

The VASP XML does not carry a complete ionic-step velocity trajectory. The
production reader therefore reconstructs velocities by finite differences and
emits the expected `VelocityReconstructionWarning`. Coordinates and forces are
read directly.

## Framework and primitive-ring replay

The packaged persistent framework topology replays 192 mean T--O bonds:

| Diagnostic | Value |
|---|---:|
| Minimum T--O distance | 1.593825 Å |
| Mean T--O distance | 1.685158 Å |
| Maximum T--O distance | 1.794157 Å |

The packaged primitive-ring catalog contains 82 rings:

| Ring size | Count |
|---:|---:|
| 4 | 36 |
| 6 | 40 |
| 8 | 6 |

Ordered oxygen polygons are locally unwrapped with the triclinic minimum-image
metric. The maximum plane-fit RMS is 0.207652 Å, below the 0.50 Å gate. The
mapping records explicitly certify `serrated_polygon_mapping=true` and
`circle_or_ellipse_substitution=false`.

## Attractor-to-ring association

All 24 central exploratory attractors have unique best ring candidates:

| Best-candidate ring size | Attractors |
|---:|---:|
| 4 | 2 |
| 6 | 16 |
| 8 | 6 |

- Median best association distance: 0.419451 Å
- Maximum best association distance: 2.142396 Å
- Minimum winner-to-runner-up margin: 0.359464 Å

The association record remains `partial`, not `resolved`, because the upstream
S2 scale consensus is `scale_ambiguous` and the 12³→16³ saddle topology is
`unstable`. Unique geometric association does not override that spatial-model
uncertainty.

## Full-trajectory provisional temporal support

The S2 partition was transferred from the represented-time discovery catalog to
the full E0b catalog under
`exact_registered_coordinate_identity`. All 36,000 Na samples were classified:

| Raw membership | Samples |
|---|---:|
| Core | 28,221 |
| Basin | 396 |
| Transition region | 7,383 |
| Other explicit classes | 0 |

The provisional Stage 11E4 result is:

- temporal support: `persistent`;
- evidence pattern: `excursions_only`;
- core visits: 29;
- preliminary residences: 26;
- passages: 8;
- return excursions: 5;
- right-censored exits: 3;
- jumps: 0;
- unresolved gaps: 0; and
- stride factors 1, 2, and 4 reproduce zero jumps and five return excursions,
  so the result is not stride-sensitive under the declared diagnostic.

Temporal evidence remains `partial` because it is conditioned on the unresolved
central S2 spatial hypothesis. S3 does not publish final E6 events or E6b paths.

## Dossier result

- Overall status: `blocked_missing_required_evidence`
- Remaining required evidence:
  - `force_density_agreement`
  - `transition_paths`
- Structural mapping signature:
  `23234df4e3325b7c77f85cdd1a6703bee27fc429803b05692befb0e1f5e96e58`
- Temporal assignment signature:
  `7e7fe98677dccb9f8ca157fea5664e4f3fe139663d97b312ae27d5281a9bd03e`
- Report signature:
  `ef8de8822646e271b3571b20b9ed5c8b824ac41942bce9508ee30c9d9e57aaa5`

The next mandatory boundary is Stage 11E8a-S4: source-bound force-density
agreement and observed transition-path preparation.
