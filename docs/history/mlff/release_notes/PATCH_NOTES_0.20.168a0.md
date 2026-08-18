# mdstats 0.20.168a0 patch notes

## TARGET-DATA2E - production target-corpus decision/provenance

This release implements the TARGET-DATA2E authority that freezes the final target corpus only after TARGET-DATA2D has demonstrated bounded-ladder convergence and selected one target size.

### Runtime authority

- Add immutable `TargetProductionCorpusDecision`, `TargetProductionDomainDecision`, rung-provenance, and practical-equivalence records.
- Freeze the exact winning frame membership independently for every target label domain and authenticate it as the selected TARGET-DATA2C rung.
- Bind TARGET-DATA2A role/partition lineage, FOUNDATION-AUDIT1 identity, TARGET-DATA2B policy/reference-family/stratum identities, TARGET-DATA2C ladder/rung identities, and the complete TARGET-DATA2D Stage-A/B/C evidence graph.
- Embed the winning TARGET-DATA2B coverage report so empirical-mass coverage, extent, mandatory support, and distribution-fidelity diagnostics remain auditable without rerunning selection.
- Record explicit 1 meV/A practical-equivalence comparisons and the selected decision reason.

### Fail-closed lifecycle

- No TARGET-DATA2E record is valid while TARGET-DATA2D is waiting for Stage-B or Stage-C evidence.
- `failed` and `nonconverged_at_ladder_boundary` outcomes cannot be converted into a production target-size claim.
- Existing premature/stale TARGET-DATA2E records are removed while the funnel is waiting or completed unsuccessfully.
- A materialized record is rebuilt and compared against all live upstream authorities on restart.
- TARGET-DATA2E is intentionally not part of the ordinary `prepare` receipt because `prepare` legitimately completes before TRAIN2/EVAL2/VERIFY generate Stage-B/C evidence; later gates must materialize/authenticate TARGET-DATA2E before the fixed-size production campaign.

### Compatibility

- Historical campaign evidence and legacy training policies are unchanged.
- The intentional two-seed production geometry introduced in 0.20.167a0 remains unchanged.
- No Stage-B/Stage-C training is executed by this gate; TRAIN2/EVAL2/VERIFY remain responsible for generating the evidence consumed by TARGET-DATA2D/TARGET-DATA2E.

### Qualification

- Gate-focused and regression suite: 161 passed, 1 expected skip.
- Known historical DATA0 specification debt remains: one test still hard-codes package version `0.20.140a0`.
- Architecture PDF regenerated and visually inspected around TARGET-DATA2E; render comparison completed against the 0.20.167a0 manual.
