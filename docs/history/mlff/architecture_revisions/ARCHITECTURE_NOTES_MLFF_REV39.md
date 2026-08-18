# MLFF architecture revision 39 - MLCV-MIGRATE1 closure

`mdstats 0.20.139a0` closes MLCV-MIGRATE1 and therefore the nine-gate conventional cross-validation correction introduced in 0.20.130a0.

## Lifecycle identity

New MLCV campaigns now use the canonical evaluator identity `mlcv_nested_cv`. The immutable `mdstats.mlcv-lifecycle-authority.v1` record binds the campaign digest, ROLE1 role catalogs, MON1 monitor catalogs, and run-local top-five contract. Mutable TOML cannot redirect that scientific campaign into historical ADAPT-EVAL1, fold-winner deployment, or legacy bounded/multi-fidelity evaluators.

Historical pre-MLCV adaptive campaigns remain `adaptive_topk` campaigns. Transitional conventional-CV campaigns carrying both ROLE1 and MON1 authority from the incremental 0.20.131-0.20.138 period may retain the old `adaptive_topk` spelling as a recorded alias, but their canonical evaluator family is MLCV and their scientific evidence is never reranked during migration.

## Production freeze and storage authority

After verified publication, `mdstats.mlcv-protocol-freeze.v1` authenticates the complete ROLE1-through-VERIFY1 evidence graph, including all top-five RANK1 records, SELECT1 representatives, AGG1 campaign CV evidence, FINAL1 selection/committee, VERIFY1 physical evidence, one-shot locked E, production-model identity, protected checkpoint SHAs, and protected model SHAs.

Generic storage/restart code receives a schema-neutral `protocol_freeze` adapter with `authority_kind = mlcv_deployment`. The original scientific freeze remains separately stored. STOR2 conservatively retains MLCV top-five checkpoints and frozen representatives.

## Transitional completed campaigns

A campaign already completed under 0.20.138a0 is migrated on its first 0.20.139a0 `verify` touch. Existing production bytes and passing locked-E evidence are authenticated and reused. No checkpoint ranking, full validation, outer-fold evaluation, NVE verification, or locked-test inference is repeated.

## Revision status

MLCV-ROLE1, MON1, STOP1, RANK1, SELECT1, AGG1, FINAL1, VERIFY1, and MIGRATE1 are all closed. Historical evaluator evidence remains readable under its original authority.
