# MLFF MACE TorchScript warning compatibility specification

## Scope

PyTorch 2.10 deprecates public `torch.jit` entry points that remain exercised by the version-locked MACE 0.3.16 checkpoint and deployment paths. mdstats does not replace MACE serialization locally. It instead provides targeted warning handling around explicit MACE operations.

## Required behavior

1. Interception is active only inside an explicit MACE compatibility scope.
2. A warning is classified as the known legacy TorchScript warning only when all of the following hold:
   - its category is `DeprecationWarning`;
   - its complete message matches the PyTorch `torch.jit.<api>` deprecation form; and
   - its source path is inside `torch/jit`.
3. Matching warnings are counted and deduplicated by API name.
4. One `MaceRuntimeCompatibilityWarning` is emitted per process for each PyTorch version, MACE version, and observed API set.
5. All unrelated warnings are replayed with their original category, filename, and line number.
6. Nested scopes share one capture and merge their operation names.
7. Warning processing must not swallow or replace an exception from the wrapped MACE operation.
8. The scope exposes a `MaceRuntimeCompatibilityRecord` containing the operation names, PyTorch and MACE versions, observed APIs, raw warning count, and stable warning code.

## Covered MLFF paths

The shared policy wraps checkpoint precision inspection and evaluation, MACE calculator and descriptor construction, acceleration qualification, CLI execution, deployment export, checkpoint validation, critical-precision subprocess auditing, and bounded NVE verification.

## Non-goals

This change does not convert native MACE checkpoints to `torch.export`, enable `torch.compile` by default, suppress all deprecation warnings, or alter numerical precision, model heads, forces, energies, stresses, virials, or LAMMPS artifacts.

## Acceptance tests

The gate requires:

- exact `torch.jit.script` and `torch.jit.load` consolidation;
- source-path discrimination for identical messages outside `torch/jit`;
- preservation of unrelated warning category and location;
- nested-scope consolidation;
- process-level deduplication;
- unchanged return values and exception propagation;
- real PyTorch 2.10 `torch.jit.script` and `torch.jit.load` smoke coverage when that runtime is available;
- successful package compilation and wheel construction.
