# mdstats 0.20.139a0 patch notes

## MLCV-MIGRATE1

This release closes the conventional cross-validation redesign. New campaigns now use the distinct `mlcv_nested_cv` lifecycle authority rather than sharing the historical `adaptive_topk` evaluator identity.

- Freeze lifecycle identity from the campaign plus ROLE1/MON1 DATA8 catalogs and top-five selection contract.
- Preserve historical adaptive and legacy evaluator campaigns under their original authorities.
- Recognize 0.20.131-0.20.138 transitional MLCV campaigns and migrate them without reranking or reevaluating scientific evidence.
- Freeze all RANK1 top-five records, SELECT1 representatives, AGG1 CV evidence, FINAL1 selection/committee, VERIFY1 physical evidence, locked E, production-model identity, protected checkpoint SHAs, and protected model SHAs after publication.
- Add schema-neutral `mlcv_deployment` protocol-freeze authority for generic storage/restart code.
- Keep MLCV top-five checkpoints and representatives protected from STOR2 compaction.
- Make migration idempotent and allow already-completed 0.20.138 VERIFY1 campaigns to close MIGRATE1 on the first new `verify` invocation without repeating physical verification or locked E.

The nine-gate MLCV-ROLE1 through MLCV-MIGRATE1 conventional-CV correction is complete.
