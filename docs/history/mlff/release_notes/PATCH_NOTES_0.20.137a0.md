# mdstats 0.20.137a0 patch notes

This release closes **MLCV-FINAL1**, the seventh gate of the conventional-CV correction roadmap.

## Final-seed production authority

Only `FINAL_DEVELOPMENT` MLCV-SELECT1 representatives may enter production comparison. Fold representatives remain evidence-only and cannot be exported into the final committee or selected as a production candidate.

For configured CV campaigns, an AGG1 `cv_failed` outcome blocks FINAL1 production authority at the recipe level. If CV is robust, final representatives are compared using their already-authoritative complete `D_full + R_full` validation score. Deterministic tie-breaking is full score, target RMSE, replay RMSE, optimizer seed, representative epoch, then checkpoint SHA-256.

FINAL1 freezes exactly one `production_best` **verification candidate** and exports all qualified final-seed target heads as an active-learning committee. A failed final seed is omitted rather than replaced by an inadmissible model. Physical verification and verified production publication remain owned by MLCV-VERIFY1.

## Seed modes

Generated campaigns now include:

```toml
seed_mode = "optimizer_only"
```

This keeps one shared CV partition across optimizer seeds so optimization stochasticity and partition sensitivity remain separable. Advanced:

```toml
seed_mode = "optimizer_and_cv_partition"
```

derives a deterministic fold-partition seed for each optimizer seed. This broadens CV robustness sampling but does not change the final-development training membership and is not a committee-diversity mechanism.
