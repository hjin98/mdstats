# Method documents

This directory contains human-facing scientific and numerical method documents for mdstats.

The intended authority split is:

- **D1 scientific formulation** defines the scientific question, observables, model assumptions, evidence semantics, validity domain, uncertainty, and claims that the workflow is intended to support.
- **D2 numerical algorithm design** defines the numerical realization of an accepted D1 formulation: deterministic constructions, fitting and reduction algorithms, approximation/error semantics, conditioning, failure handling, and computational equivalence requirements.
- **D3 architecture** under `docs/arch_manuals/` defines software decomposition, dependency direction, ownership boundaries, interfaces, persistence, and integration consequences of D1/D2.
- Current specifications under `docs/specs/` define exact schemas, configuration fields, constants, runtime contracts, and acceptance behavior.

The MLFF D1/D2 documents on this reconstruction branch are **candidate reconstructed authorities pending human review**. Until accepted, the repository's current normative architecture/specification set remains controlling. Acceptance should promote the D1/D2 papers and then reduce the architecture chapters to D3 integration summaries without losing information.

A D3 summary may repeat an accepted D1/D2 consequence for local comprehension, but it must not become an independently tunable scientific or numerical authority. Likewise, implementation code and tests are evidence that an accepted method is realized; they do not silently redefine the method.

## MLFF method set

- [`mlff_scientific_method.md`](mlff_scientific_method.md) — candidate D1 scientific formulation for the MLFF training-data, target-size, fine-tuning, and validation workflow.
- [`mlff_numerical_algorithmic_method.md`](mlff_numerical_algorithmic_method.md) — candidate D2 numerical algorithms that realize that formulation.

Both MLFF papers were reconstructed from the current repository plus accepted historical evidence. Reconstruction provenance and superseded-design exclusions are recorded in `../history/mlff/MLFF_D1_D2_RECONSTRUCTION_EVIDENCE.md`.
