# Stage 11E8a-S2 — 300 K Na-LTA spatial refinement benchmark

- Status: `blocked_missing_required_evidence`
- Raw trajectory SHA-256: `ad54b98c5d927d722ac1cb8a4a3b1fe472a50603a6e8ece5497b06e55a8679eb`
- Frames / atoms: 1500 / 168
- Force array: `(1500, 168, 3)`
- Velocity source: `finite_difference`
- Represented duration: 1.499 ps
- S2 wall time after parsing: 21.964 s

## Bandwidth lineage

| Cartesian sigma (Å) | Attractors | Saddles |
|---:|---:|---:|
| 0.40 | 24 | 53 |
| 0.50 | 24 | 100 |
| 0.60 | 24 | 145 |

All adjacent bandwidth catalogs match 24/24 basin identities with no unmatched
attractors. The lineage is not assignment-ambiguous. Scale selection nevertheless
remains `scale_ambiguous` because the supported saddle topology differs at
each bandwidth; the candidate intervals are `[[0, 0], [1, 1], [2, 2]]`.

## Grid refinement

- Grids: `[[12, 12, 12], [16, 16, 16]]`
- Status: `unstable`
- Minimum matched-basin overlap: `0.56`
- Unresolved reasons: `['saddle_adjacency_changes']`

The basin count and geometry multiset persist, but saddle adjacency changes
between the 12-cubed and 16-cubed central-bandwidth realizations. The result is
retained as an unstable topology certificate rather than promoted to a converged
catalog.

## Reference-cell sensitivity

The comparison source frame is 762. The NVT
cell matrix is exactly identical to the selected S1 reference cell, so the signed
identity shortcut is valid:

- accepted: `True`;
- relative cell difference: `0.0`;
- relative volume difference: `0.0`;
- fractional probability L1: `0.0`;
- matched/unmatched attractors: `24` / `0`;
- maximum anchor displacement: `0.0 Å`.

## Remaining gates

The source-bound dossier now has four missing required evidence families:

- structural mapping;
- temporal support;
- force-density agreement; and
- transition paths.

Stage 11E8b remains closed.
