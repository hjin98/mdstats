# MLFF MLCV-FINAL1 final-seed selection specification

Status: implemented in mdstats 0.20.137a0 (`MLCV-FINAL1`)

## Purpose

MLCV-FINAL1 converts conventional CV evidence plus full-development MLCV-SELECT1 representatives into the only production-eligible model pool. Fold models are evidence about the training recipe and are permanently excluded from production and committee export.

## Recipe-level CV gate

When CV folds are configured, MLCV-AGG1 must report campaign-level `cv_robust` before FINAL1 may create production or committee authority. A `cv_failed` campaign therefore exports no final seed even if one final-development run has an attractive `D_full` score. This preserves the interpretation that CV validates the training recipe rather than serving as another model leaderboard.

An explicitly configured zero-fold campaign remains supported. It records `cv_not_performed`; FINAL1 may compare its full-development representatives without inventing CV evidence.
The per-seed AGG1 records supplied to FINAL1 must match byte-identical content digests already embedded in the immutable campaign-level AGG1 aggregate; matching seed labels or outcomes are not sufficient authority.

## Final-seed candidate domain

Exactly one final-development run per optimizer seed is expected. For each seed FINAL1 consumes the immutable MLCV-SELECT1 run-selection record and its authenticated representative, if one exists. Comparable final seeds must share:

- one SELECT1 policy identity;
- identical complete target validation `D_full` artifact identity; and
- identical complete TRUE_DFT replay validation `R_full` artifact identity.

A fold selection passed into this layer fails closed.

## Qualification and ranking

A final seed is individually qualified only when its final-development SELECT1 run produced a representative and its seed CV evidence is robust (or explicitly `cv_not_performed` for a zero-fold campaign). Failed final seeds are omitted; committee cardinality is never padded with an inadmissible model.

When the recipe-level CV gate passes, qualified final representatives are ordered deterministically by:

1. lower authoritative full weighted score;
2. lower `D_full` target force RMSE;
3. lower `DeltaR_full` replay degradation;
4. lower absolute `R_full` replay force RMSE;
4. lower optimizer seed;
5. earlier representative checkpoint epoch; and
6. checkpoint SHA-256.

The first item is the single `production_best` **verification candidate**. FINAL1 does not publish a verified production model.

## Committee export

Every qualified final seed is exported as an exact target-head deployment artifact under the FINAL1 committee namespace. Committee members are bound to final-candidate digest, final run identity, SELECT1 record digest, checkpoint SHA/epoch, full score, target-head name, exported model SHA, and byte size.

The committee contains only full-development representatives. Its best member is the same model identified by `production_best`, but that member is still awaiting MLCV-VERIFY1 physical verification.

## Seed modes

Generated campaigns use `seed_mode = "optimizer_only"`. Optimizer seeds change stochastic MACE training while the CV partition seed is shared, preserving separation between optimizer-seed variance and partition variance.

Advanced `seed_mode = "optimizer_and_cv_partition"` derives a different deterministic CV partition seed for each optimizer seed. This broadens robustness sampling only. It does not change the final-development `A+B+C` training membership and therefore must not be described as a final-model diversity mechanism.

## Restart and immutability

Final selection is deterministic from immutable AGG1 and SELECT1 records. Existing FINAL1 selection/committee records must reproduce byte-for-byte identities on restart or fail closed. Authenticated exported committee artifacts may be reused without re-extraction. The selected production model remains unpublished until MLCV-VERIFY1 passes physical verification.


## 0.20.140a0 replay-degradation correction

Only qualified final-development representatives compete, as before, but FINAL1 now ranks their authenticated full score built from absolute target error plus signed full replay degradation. Each final candidate/committee member retains raw `R_full`, matched `R0_full`, `DeltaR_full`, the degradation budget, and baseline model identity for auditability. Fold models remain permanently excluded and failed seeds are never padded into the committee.
