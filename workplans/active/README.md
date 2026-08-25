# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior.

Current MLFF workplans:

- `DATA78_POST_IMPLEMENTATION_CLOSEOUT_WORKPLAN.md` — DATA7/DATA8 post-implementation closeout.
- `MLCV_LIFECYCLE_AUTHORITY_FIX_WORKPLAN.md` — blocking MLCV lifecycle authority/provenance reconciliation correction for shared training entry, including TARGET-SIZE-V5.
- `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md` — **controlling target-size design contract** at reviewed head `ea196babecd951491ae4656d3b3e38b8eb866144`. TARGET-SIZE-V5 screening now targets an independent `n3`-horizon successive-fidelity trajectory (default `1 -> 3 -> 10`, horizon 10), while production `n` (default 30) is reserved for a fresh selected-size production campaign. This workplan supersedes conflicting full-`n` screening statements in the Rework-3 files while preserving their nonconflicting candidate-authority, compatibility, continuation, and proxy-proof acceptance requirements.
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_WORKPLAN.md` — retained active historical/implementation context for flexible-fidelity Rework 3. Its target-size scientific statements are subordinate to `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md` wherever they conflict.
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW1_AMENDMENT.md` — retained Rework-3 authority-bridge and acceptance context. Nonconflicting requirements remain applicable; conflicting target-size full-horizon semantics are superseded by the decoupling workplan.
- `MLFF_FLEXIBLE_FIDELITY_CODEBASE_REWORK3_REVIEW2_AMENDMENT.md` — retained implementation-review context, including DATA6 restore optimization and acceptance findings. Its statements that screening uses the production full-`n` schedule, that `(3,10,30)/30` is current-valid, or that `/n` is the screen schedule denominator are superseded.

### Target-size transition precedence

For TARGET-SIZE-V5, read `MLFF_TARGET_SIZE_SCREEN_PRODUCTION_DECOUPLING_WORKPLAN.md` first. Its frozen current design is:

```text
0 < n1 < n2 < n3 < n
screen horizon = n3
production horizon = n
screen continuation = exact n1 -> n2 -> n3
production = fresh post-selection training
```

Nonconflicting Rework-3 requirements remain in force, especially policy-independent DATA7/DATA8 candidate-prefix authority, authenticated predecessor-only compatibility, no historical screen/evaluation relabeling, exact checkpoint/optimizer/RNG screen continuation, real-owner/proxy-proof acceptance, and deferred full GPU/production qualification.

For gate-closing acceptance, expensive external training/evaluation may be faked only below the required production semantic-owner boundary. Configuration normalization, `CampaignStore`, target-size construction/migration, DATA8 compatibility, runtime budget/schedule assembly, orchestration/authorization, evidence reduction, restart/invalidation, and screen-to-production consumers must execute for real when their behavior is the claim.

Historical records remain in `../archive/` except active workplans still governing implementation or closeout. Superseded target-size/full-horizon assumptions must not be used as current implementation authority merely because their files remain active for historical dependency/acceptance context.

Unrelated active performance, lifecycle, scientific, resource, and acceptance workplans remain authoritative. Completed or superseded workplans and retained coordination records belong in `../archive/` when their remaining obligations are closed.
