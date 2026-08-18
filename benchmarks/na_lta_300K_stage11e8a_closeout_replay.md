# Na-LTA 300 K Stage 11E8a closeout replay

The `0.20.15a0` engineering closeout was replayed through the existing public
Stage 11E8a-S4 example against the supplied 1,500-frame `vasprun.xml` using ASE
3.29.0. The closeout changes do not modify the S0–S4 scientific algorithms or
promote any blocked evidence.

## Result

- overall dossier: `scientifically_partial`
- missing required evidence IDs: none
- blockers: `force_density_agreement`, `transition_paths`
- represented-time joint force samples: 1,440
- PMF-admissible force samples: 0
- force-density status: `pmf_provenance_rejected`
- local refinements rejected by PMF provenance: 24
- provisional passages: 8
- return excursions: 5
- right-censored exits: 3
- provisional inter-attractor jumps: 0
- final segmentation executed: no
- observed transition paths executed: no
- S4 analysis wall time: 23.300 s
- complete process wall time: 28.26 s
- maximum resident set: 535,484 KiB

ASE emitted the expected warning that ionic-step velocities were reconstructed
from unwrapped positions because a complete velocity trajectory is not present
in the source XML.

## Interpretation

Stage 11E8a is implementation-complete and regression-closed. Its real-data
scientific conclusion remains deliberately partial: occupied basin evidence may
be retained, but no PMF force agreement, final transition segmentation, path,
barrier, rate, or kinetic network is admitted.
