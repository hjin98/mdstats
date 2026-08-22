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
- DATA8 variants currently take TRAIN2 sizes from target-size study state, while
  each DATA7 ladder is independently built from legacy `[selection].sizes`.
- Before a terminal target-size decision, hard-qualified candidates are valid
  stage-authorized training inputs. After `selected(N)`, intermediate candidate
  sets are no longer materialization authorities.

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
validated active TARGET-DATA2D sizes -> DATA7 and DATA8
selected(N)                       -> selected_target_size only
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
