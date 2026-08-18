# mdstats 0.20.176a0 patch notes

## SELECT2 — physics-qualified lexicographic production selection

This release implements SELECT2, the final pre-locked-test production-selection gate for the TRAIN2 campaign.

### Production-seed selection

- Consumes only the selected-size `FINAL_DEVELOPMENT` seed representatives already frozen by EVAL2.
- Reuses EVAL2's target-only ordering contract: full target force RMSE, 1 meV/A practical equivalence, paired correlation-block bootstrap, then worst-stratum RMSE, species-macro RMSE, P95, P99, checkpoint maturity, and stable identity.
- Freezes the static target-first seed order before consulting DEPLOY/PES/RELAX/DYN outcomes.
- Treats DEPLOY-VERIFY1, PES-VERIFY1, RELAX-VERIFY1, and DYN-VERIFY2 strictly as eligibility gates. Physical metrics never become ranking rewards.
- Treats replay strictly as an admissibility constraint. Replay margin never becomes ranking or tie-break credit.
- Walks the frozen target order until the first fully physics-qualified seed is found and records `fallback_count` for any higher-ranked candidates eliminated by physical qualification.
- Keeps run/seed lineage in stable comparison identities even if two candidates happen to contain byte-identical checkpoint/model artifacts.

### Frozen candidate publication boundary

- Copies the selected target-only MACE model and exact DEPLOY-authenticated ML-IAP artifact into `models/select2-frozen/`.
- Authenticates the selection policy, TARGET-DATA2E production-corpus authority, EVAL2 evidence, and complete DEPLOY/PES/RELAX/DYN chain.
- Removes stale frozen-candidate artifacts if authenticated upstream evidence changes and SELECT2 resolves to a different candidate.
- Publishes a **pre-locked-test frozen candidate**, not final post-test production evidence.
- Leaves `verify` in `WAITING`: the one-shot locked post-freeze test remains the next gate and has zero authority to re-rank or fall back to another seed/checkpoint.

### Compatibility

Historical adaptive/MLCV campaign semantics are unchanged. SELECT2 is active only for the TRAIN2 policy generation.

### Qualification

- Primary SELECT2/cross-gate regression: 254 passed, 1 expected external-data skip.
- Additional checkpoint/storage/materialization hardening: 43 passed.
- Focused SELECT2/current-gate specification suite: 30 passed (included within the broader qualification coverage).
- Python `compileall` and public import checks pass.
- Architecture PDF preflight passes at 134 pages; SELECT2 pages were rendered and visually inspected, and a full low-DPI before/after comparison showed only expected documentation reflow.

## Next gate

The remaining gate is the one-shot **locked post-freeze test and final production publication**. It may accept or reject the SELECT2-frozen candidate, but it may not choose a different checkpoint, seed, target size, or policy.
