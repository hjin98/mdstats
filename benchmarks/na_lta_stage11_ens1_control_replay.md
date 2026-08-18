# Na-LTA Stage 11E-ENS1 real-source replay

- Source: `vasprun(1).xml`
- Policy: `mdstats.ensemble-inference-policy.v1+vasp-wiki-2026-06`
- Dynamics: `molecular_dynamics`
- Ensemble: `NVE` (`resolved`)
- Propagator: `nose_hoover_family`
- Thermostat: `none`, active=False, friction=not_applicable
- Cell: `fixed_cell`
- Barostat: `none`
- Bias: `unresolved`
- Constraints: `unresolved`
- Force provenance: `unresolved` / `vasp_dft_hellmann_feynman`
- Initial velocity provenance: `unresolved` / `nonzero_initial_kinetic_energy_source_unknown`
- Continuation provenance: `unresolved` / `continuation_or_external_initialization_possible`
- Frames / atoms: 1500 / 168
- Signature: `36dc5f6f51e0d3ee2d4fa1ea6d210e7f1536cca1085cb0049b251a9e8bcbb919`
- ENS1 parse time: 1.576 s
- Full reader time: 6.115 s

## Interpretation

The source controls resolve fixed-cell NVE. The misleading `SYSTEM` label is not consulted. Bias, constraint, and complete applied-force provenance remain unresolved because no affirmative companion evidence was supplied. Continuation is consistent with nonzero initial kinetic energy but is not proven without a bound parent/restart source.
