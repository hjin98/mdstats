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
- Legacy target-size study state can still inject intermediate candidate sizes into DATA8.
- Intermediate survivor sets are not final materialization authorities.

## Scope

Included:

- Trace the producer of DATA8 `selection_size`.
- Replace legacy intermediate target-size propagation with authoritative selected target size.
- Add validation that selected target size exists in the DATA7 ladder.
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

Replace legacy:

```
intermediate survivor sizes -> DATA8
```

with:

```
validated selected_target_size -> DATA8
```

Add hard validation:

```
selected_target_size exists
AND
selected_target_size is present in DATA7 ladder
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
