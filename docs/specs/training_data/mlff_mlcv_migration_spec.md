# MLCV-MIGRATE1 lifecycle migration specification

**Implemented:** mdstats 0.20.139a0  
**Authority:** `mdstats.mlcv-nested-cv.2026-08.v1`  
**Canonical checkpoint strategy:** `mlcv_nested_cv`

## Purpose

MLCV-MIGRATE1 closes the conventional cross-validation revision by making its evaluator family, restart semantics, storage ownership, and historical compatibility explicit. It changes no scientific score or checkpoint decision made by ROLE1 through VERIFY1.

The principal requirement is that conventional nested-CV authority is distinct from the historical `adaptive_topk` evaluator. A TOML spelling is not allowed to reinterpret an already-prepared campaign after its scientific identity has been frozen.

## Lifecycle authority

New MLCV campaigns persist `mdstats.mlcv-lifecycle-authority.v1`. The record binds:

- the immutable training-campaign digest;
- all DATA8 ROLE1 role-catalog digests;
- all DATA8 MON1 monitor-catalog digests;
- canonical `checkpoint_strategy = "mlcv_nested_cv"`;
- the run-local top-five checkpoint candidate limit; and
- the versioned lifecycle authority identifier.

ROLE1/MON1 lineage, not mutable TOML alone, determines whether a campaign belongs to the MLCV evaluator family.

## Transitional 0.20.131-0.20.138 campaigns

The conventional-CV gates were introduced incrementally while generated TOML still used the historical string `adaptive_topk`. Such campaigns are recognized only when their immutable DATA8 bundles contain both MLCV ROLE1 and MON1 catalogs.

For these campaigns:

- `adaptive_topk` is recorded as a transitional source alias;
- the canonical lifecycle remains `mlcv_nested_cv`;
- reopening with either the recorded alias or the canonical spelling is permitted;
- checkpoint ranking, top-five membership, SELECT1 representatives, outer-fold results, FINAL1 selection, physical verification, and locked-E evidence are reused exactly; and
- no migration operation may rerank or re-evaluate scientific evidence.

Historical pre-MLCV adaptive campaigns that lack MLCV ROLE1/MON1 authority remain historical `adaptive_topk` campaigns and are never silently converted.

## Protocol freeze

After VERIFY1 has physically frozen a candidate, evaluated locked E exactly once, and published `production_best.model`, MIGRATE1 writes `mdstats.mlcv-protocol-freeze.v1`.

The freeze authenticates the complete production evidence graph:

1. production-corpus qualification;
2. MLCV lifecycle authority;
3. every run-local top-five lightweight ranking record;
4. every SELECT1 run-selection record and representative;
5. campaign-level conventional-CV aggregate;
6. FINAL1 seed selection;
7. qualified final-seed committee;
8. physical-verification record;
9. one-shot locked-E record;
10. production-model record;
11. protected top-five/representative checkpoint SHA-256 values; and
12. protected committee/production model SHA-256 values.

A schema-neutral `protocol_freeze` adapter exposes this as `authority_kind = "mlcv_deployment"` for generic storage/restart code without replacing the scientific MLCV freeze.

## Restart and idempotence

MIGRATE1 is idempotent. Exact restart must reproduce the same lifecycle authority, scientific freeze, generic freeze authority, and migration receipt. The original freeze timestamp is reused.

A campaign completed under 0.20.138a0 is migrated on the first 0.20.139a0 verification touch. The already-published model and passing locked-E evidence are authenticated first. No NVE, model inference, full validation, outer-fold evaluation, or locked-test inference is repeated.

If any digest or published model SHA differs, migration fails closed.

## TOML redirection guard

After lifecycle authority exists, mutable configuration cannot redirect the same campaign into another evaluator family.

- Canonical new campaigns permit `mlcv_nested_cv` only.
- Transitional MLCV campaigns may retain their recorded `adaptive_topk` alias or use `mlcv_nested_cv`.
- `bounded`, `exhaustive`, `multi_fidelity`, or an unrelated evaluator is rejected.
- Historical adaptive campaigns remain bound to historical `adaptive_topk`.
- Historical non-adaptive campaigns cannot acquire MLCV semantics by editing TOML.

This guard prevents restoration of fold-winner deployment or historical lightweight hard-gating under an already-frozen MLCV campaign identity.

## Storage authority

MIGRATE1 keeps MLCV checkpoint retention conservative. STOR2 does not compact MLCV run checkpoints while lifecycle authority is present, so top-five candidates and frozen representatives remain restart/audit capable. The generic `mlcv_deployment` freeze protects qualified committee and production-model bytes.

Results, logs, monitor histories, diagnostic JSON/CSV/PNG, outer-fold evidence, locked-test evidence, and migration receipts remain retained according to their evidence classes. No migration operation deletes historical evaluator evidence.

Future reclamation of protected MLCV checkpoint bytes requires a separately versioned lifecycle rule; it must not be inferred from historical STOR2 behavior.

## Historical compatibility

Completed ADAPT-MON1/STOP1/RANK1/EVAL1/VERIFY1 evidence remains readable and ownership-safe. Historical committee and multi-fidelity evidence also remains read-only.

MIGRATE1 refuses dual production authority: if an incompatible historical/adaptive generic protocol freeze already owns the state DB, MLCV migration fails rather than overwriting it.

## Acceptance tests

The gate is closed only when tests demonstrate:

1. a new MLCV campaign freezes `mlcv_nested_cv` authority;
2. MLCV authority is distinct from historical `adaptive_topk`;
3. transitional MLCV aliases reopen without changing ROLE1/MON1 identity;
4. mixed pre-MLCV/MLCV DATA8 authority fails closed;
5. the protocol freeze round-trips exactly and produces `mlcv_deployment` generic storage authority;
6. historical evidence keys survive in the migration receipt;
7. top-five checkpoint and run-representative retention cannot be compacted by STOR2;
8. TOML cannot redirect a frozen new MLCV campaign to another evaluator family;
9. completed VERIFY1 evidence can migrate without repeating locked E or physical verification; and
10. repeated migration is idempotent and digest-stable.


## 0.20.140a0 replay-degradation migration

The current lifecycle authority is versioned separately from the 0.20.139a0 absolute-replay authority. Historical payloads round-trip with their original schema/digest and are never algebraically reinterpreted. Transitional STOP1/RANK1/SELECT1/AGG1/FINAL1 derived evidence is stale under current replay semantics. `train` fails closed on historical MLCV DATA8 stop policies and requires replay-dependent authority regeneration; a prior lifecycle authority is archived under its original content digest before the current authority is installed. Raw authenticated absolute validation metrics may be reused only when exact checkpoint/domain/baseline identities allow recomputation. Physical VERIFY1/locked-E work is reusable only if the corrected FINAL1 selects the exact same production checkpoint; otherwise verification follows the newly selected model.
