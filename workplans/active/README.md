# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior.

Current MLFF workplans:

- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — blocking MLCV lifecycle authority/provenance reconciliation correction for shared training entry, including TARGET-SIZE-V5.
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK_WORKPLAN.md` — accepted Part 2 transition from fixed target-size fidelity to configurable `(n1,n2,n3)` screening with an independent full TRAIN2 horizon; remains the base contract for unchanged obligations.
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK1_WORKPLAN.md` — Rework 1 overlay after independent review of the first Part 2 implementation; remains authoritative for unchanged rework obligations.
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK2_WORKPLAN.md` — governing closure overlay after final independent review; repairs preparation semantic identity/invalidation, closes the missing horizon-perturbation evidence, removes current fixed-fidelity semantic leakage, and requires final assembled A/B/C+D1/D2/D3 regression/integration before closeout.

### Flexible-fidelity transition precedence

When implementation under `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1` begins, that workplan supersedes older active-workplan requirements only on the target-size fidelity epoch/state/schema/configuration surface. `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK1` strengthens/reconciles its parent on the first reviewed implementation-rework surface. `CODE-MLFF-FLEXIBLE-FIDELITY-EPOCH-REWORK-V1-REWORK2` is now the governing closure overlay and takes precedence over Rework 1 only where it explicitly strengthens or reconciles the remaining reviewed closure findings. All unchanged parent and Rework 1 obligations remain authoritative. Unrelated performance, lifecycle, scientific, resource, and acceptance requirements remain authoritative.

Completed or superseded workplans and retained coordination records belong in `../archive/`.
