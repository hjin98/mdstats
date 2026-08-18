# mdstats 0.20.128a0 patch notes

## ADAPT-MIGRATE1 - adaptive campaign migration and compatibility closure

This release implements the seventh and final gate of the post-0.20.120 MLFF adaptive revision.
It changes no target/replay thresholds, monitor sizes, ranking weights, evaluation scoring, or
verification physics established by ADAPT-PREC1 through ADAPT-VERIFY1. It closes the schema,
restart, storage-authority, and historical-compatibility boundaries around those policies.

### Schema-neutral freeze authority

Generic lifecycle/storage code now consumes `ProtocolFreezeAuthorityRecord` instead of assuming the
`protocol_freeze` database key contains one historical scientific record type. The adapter points to
the original historical or adaptive scientific freeze and protects its deployed model SHA-256
identities; it does not rewrite the scientific freeze.

Adaptive deployments also receive an immutable `AdaptiveMigrationRecord` binding the full EVAL1,
VERIFY1, deployment-model, adaptive-freeze, and generic-authority lineage together with the
`single|double` learned-model inference dtype and invariant FP64 scientific-analysis dtype.

### 0.20.127 compatibility and stale-evidence closure

Completed 0.20.127 adaptive campaigns can be reconciled by rerunning `verify`. Existing inference,
full-evaluation, NVE, deployment, and adaptive-freeze evidence is reused; only the generic freeze
alias is upgraded and the migration receipt is added. The operation is idempotent and historical
EVAL-MF/committee records are preserved.

Adaptive campaigns cannot be switched back to historical evaluators by editing TOML, and historical
campaigns cannot be switched to `adaptive_topk` without a new scientific campaign identity. Once an
adaptive deployment is frozen, later `evaluate` calls reuse the frozen EVAL1 authority instead of
creating a second selection history.

### Storage safety

STOR4/STOR5 consequential actions now require a schema-valid protocol-freeze authority rather than
mere record-key presence. `storage report` remains non-mutating and reads authority/history summary
through a read-only SQLite connection. No migration rule broadens ownership or deletion authority.

### Revision closure

ADAPT-PREC1, MON1, STOP1, RANK1, EVAL1, VERIFY1, and MIGRATE1 are now implemented end to end for new
campaigns. Historical staged `refine`, EVAL-MF, and committee records remain readable for the
campaigns that created them but no longer control adaptive production identities.
