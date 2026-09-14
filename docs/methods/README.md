# Method documents

This directory contains human-facing current method authority for mdstats.

The MLFF authority split is:

- **D1 scientific formulation** defines the scientific question, observables, assumptions, evidence semantics, validity domain, uncertainty, and claims the workflow supports.
- **D2 numerical algorithm design** defines the numerical realization of D1: deterministic constructions, fitting/reduction algorithms, normalization, conditioning, stochastic semantics, failure handling, and numerical-equivalence requirements.
- **D3 architecture** under `docs/arch_manuals/` defines software decomposition, dependency direction, ownership boundaries, lifecycle, persistence, concurrency/resources, and integration consequences of D1/D2.
- **D4 specifications and implementation** under `docs/specs/` and source code define exact schemas, configuration fields, constants, source adapters, dependency/runtime contracts, and concrete realization.

The dependency direction is `D1 -> D2 -> D3 -> D4`. A downstream layer may challenge an upstream contract with evidence but may not silently redefine it.

## MLFF method set

- [`mlff_scientific_method.md`](mlff_scientific_method.md) — current normative D1 scientific/mathematical authority for the MLFF training-data, target-size, fine-tuning, validation, and production method.
- [`mlff_numerical_algorithmic_method.md`](mlff_numerical_algorithmic_method.md) — current normative D2 numerical/algorithmic authority that realizes the D1 formulation.

These papers were reconstructed losslessly from the accepted pre-promotion architecture/specification/code evidence, independently reviewed, and explicitly accepted by the human owner on 2026-09-13. Reconstruction provenance and review evidence remain under `../history/mlff/`; they explain how the authority was recovered but do not compete with the accepted current papers.

The current D3 architecture may restate an upstream consequence where local comprehension requires it, but such restatement is not independently tunable authority. Exact D4 contracts likewise realize D1-D3 rather than overriding them.
