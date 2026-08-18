# Stage 11E8a-S4 real-source force-density and path-readiness benchmark

- Package: `mdstats 0.20.14a0`
- Source SHA-256: `ad54b98c5d927d722ac1cb8a4a3b1fe472a50603a6e8ece5497b06e55a8679eb`
- Frames: 1,500
- Atoms: 168
- Forces: complete `(1500, 168, 3)`
- Represented duration: 1.499 ps
- ASE parse: 3.301 s
- S0--S4 analysis: 22.184 s

## Force-density boundary

- Status: `pmf_provenance_rejected`
- Represented-time joint position/force samples: 1,440
- PMF-admissible samples: 0
- Local refinements: 24 `pmf_provenance_rejected`
- Matched mean-force field: not constructed
- Density-score comparison: not claimed

The source contains complete physical forces, but the S1/S4 sample catalog does not declare equilibrium, tested stationarity, and constant-temperature PMF provenance. The strict Stage-11E3 intersection is therefore empty.

## Transition-path boundary

- Status: `spatial_hypothesis_unresolved`
- Preliminary passages: 8
- Return excursions: 5
- Right-censored exits: 3
- Preliminary inter-attractor jumps: 0
- Final Stage-11E6 segmentation: not executed
- Stage-11E6b observed paths: not executed

S2 remains `scale_ambiguous` with `unstable` saddle adjacency, so the spatial hypothesis is not authoritative. No source-compatible E5 validated frozen-state catalog was supplied.

## Dossier result

- Overall status: `scientifically_partial`
- Missing required evidence: none
- Explicit blockers: `force_density_agreement`, `transition_paths`
- Report signature: `58919241cd00c1c1b1e8f9a44f5612c8368db0a9a3abd5203b78e27a43530a21`

No PMF, barrier, representative path, transition rate, Markov model, or observed network is inferred.
