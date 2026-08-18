# MLFF Architecture Revision 37 - MLCV-FINAL1 implementation

`mdstats 0.20.137a0` implements MLCV-FINAL1, the seventh gate of the conventional cross-validation redesign accepted in revision 32.

FINAL1 restores conventional production-model authority. Fold representatives are CV evidence only and can never enter production or committee export. When configured CV is used, the campaign-level AGG1 result is a recipe-level gate: `cv_failed` blocks all production comparison. An explicit zero-fold campaign remains supported as `cv_not_performed` without fabricating robustness evidence.

Only full-development SELECT1 representatives compete. Comparable seeds must share the same SELECT1 policy and identical complete `D_full` and TRUE_DFT `R_full` validation artifacts. FINAL1 also authenticates that the per-seed AGG1 records supplied to the gate are exactly those embedded in the immutable campaign-level AGG1 aggregate. Qualified final seeds are ranked deterministically by full weighted score, target RMSE, replay RMSE, seed, checkpoint epoch, and checkpoint SHA-256.

Exactly one best final seed is frozen as the production verification candidate. FINAL1 deliberately does not publish a verified production model. Every qualified final seed is exported separately as an exact target-head committee artifact for active-learning use; failed seeds are omitted rather than padded, and all exports are byte-identity/restart checked.

Generated campaigns retain `seed_mode = "optimizer_only"`: optimizer randomness varies while the CV partition is shared. Optional `optimizer_and_cv_partition` deterministically varies CV partitions per seed for broader robustness sampling, but does not alter the full-development training membership and is not presented as a final-model diversity mechanism.

The configurable lightweight STOP1 margins remain derived from the authoritative criteria. Generated defaults are `target_stop_fraction = 0.80` and `replay_stop_multiplier = 1.20`; users may change those TOML values subject to the policy bounds, without changing the full-validation thresholds themselves.

MLCV-VERIFY1 is the next gate. It will physically verify only qualified final-seed representatives, publish the first allowed verification result under the new MLCV authority, and activate locked `E` only after a production candidate is frozen.
