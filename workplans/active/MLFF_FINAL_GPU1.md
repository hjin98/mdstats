# MLFF FINAL-GPU1 — workstation qualification workplan

**Status:** active / deferred until a supported GPU workstation run is performed  
**Current authority:** MLFF architecture, current accelerator/runtime specifications, and `docs/guides/mlff_final_gpu1_workstation_runbook.{md,pdf}`  

## Objective

Coordinate the unfinished workstation qualification without treating an unexecuted developer gate as current architecture or completed evidence.

## Invariants

- Do not change scientific target-data, checkpoint-selection, replay, precision, backend, or deployment semantics merely to obtain a passing qualification.
- Do not claim positive accelerator evidence before the prescribed real-hardware run completes.
- Exact/current runtime promotion requirements remain owned by their current specifications and runbook; this workplan does not override them.
- Qualification evidence belongs in the established audit/release/benchmark locations, not in the architecture manual.

## Gate

### FINAL-GPU1 — supported-workstation qualification

Execute the current runbook and owning specifications on supported GPU hardware. Capture the required runtime/dependency identity, accelerator/backend evidence, numerical/determinism checks, resource behavior, and release-qualification artifacts.

### Acceptance

PASS only when the current runbook/specification acceptance criteria are satisfied and the resulting evidence is persisted in its permanent evidence location. On PASS, update current documentation only if the accepted software structure or behavior actually changes; otherwise record completion in history/release evidence and archive this workplan.
