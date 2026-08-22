# DOC-MLFF-TARGET-SIZE-AUTHORITY-BRIDGE-FIX1

## Objective

Repair the MLFF campaign preparation failure caused by an old/new target-size authority mismatch during migration to the MVSEL2/MVQUAL architecture.

Failure signature:

```
Requested DATA8 selection size X is not present in DATA7 ladder [...]
```

This is a control-plane authority bridge fix only. Do not redesign existing scientific machinery.

## Design diagnosis

Required ownership:

```
DATA7
 |
 v
MVSEL2 nested target ladder
 |
 v
REPAIR2 / MVSTATE2
 |
 v
MVQUAL + TargetSizeStudy
 |
 v
DATA8 materialization
```

Current issue:

- DATA7/MVSEL2 owns the materializable ladder.
- DATA8 correctly validates requested sizes against that ladder.
- DATA8 variants currently take TRAIN2 sizes from target-size study state, while each DATA7 ladder is independently built from legacy `[selection].sizes`.
- Before a terminal target-size decision, hard-qualified candidates are valid stage-authorized training inputs. After `selected(N)`, intermediate candidate sets are no longer materialization authorities.

## Scope

Included:

- Trace the producer of DATA8 `selection_size`.
- Use one validated target-size tuple for both DATA7 and DATA8 materialization.
- Narrow that tuple to the authoritative selected target size after `selected(N)`.
- Add validation that every requested size exists in the active TARGET-DATA2C ladder.
- Add regression coverage.

Excluded:

- MVSEL2 algorithm changes.
- MVQUAL predicate changes.
- DATA7 selection redesign.
- DATA8 format changes.
- Training/evaluation redesign.

## Implementation Gates

### Gate 1: Authority trace

Identify:

- target ladder producer
- target-size convergence output
- DATA8 selection-size consumer
- legacy size injection path

Acceptance:

Document exact producer-consumer chain.

### Gate 2: Control-plane patch

Replace split authority:

```
target-size study state -> DATA8 variants
[selection].sizes       -> DATA7 ladder
```

with:

```
validated active TARGET-DATA2C sizes -> DATA7 and DATA8
selected(N)                        -> selected_target_size only
```

Add hard validation:

```
every requested size is present in active TARGET-DATA2C
AND selected(N) has selected_target_size
```

### Gate 3: Regression

Test:

1. Valid selected rung passes.
2. Legacy intermediate rung does not bypass DATA7 authority.
3. Invalid authority mismatch produces actionable error.
4. Original DATA8 preparation failure no longer occurs.

### Gate 3 Revision Requirements from Design Review

The first Codex patch introduced a regression test that preserved the old authority model:

```
stage_a_survivor_sizes -> DATA8 materialization
```

This is incompatible with the new architecture and must be removed or rewritten.

Required test revisions:

1. Replace any test asserting that `stage_a_survivor_sizes` drives DATA7/DATA8 materialization.
2. Add a regression test explicitly proving that intermediate candidates cannot override `selected_target_size`.
3. Add a production-bug reproduction case:

```
legacy candidate:
    13568

active DATA7 ladder:
    [512]

selected target size:
    512
```

Expected:

```
DATA8 receives 512
13568 cannot enter materialization
```

4. Verify terminal failed convergence cannot fall back to intermediate candidate sizes.

## Review Criteria

Before merge:

- `selected_target_size` is the only terminal materialization authority.
- DATA7 and DATA8 consume the same validated target-size tuple.
- Intermediate convergence states remain evidence only, not materialization authority.
- MVSEL2, MVQUAL, DATA7 algorithms, and DATA8 format remain unchanged.

## Commit Requirements

Branch:

```
fix/mlff-target-size-authority-bridge
```

Commit message:

```
Fix MLFF target-size authority bridge
```

Keep changes limited to control-plane authority wiring.
