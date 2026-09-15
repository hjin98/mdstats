# Method documents

This directory contains human-facing current method authority for mdstats.

The MLFF authority split is:

- **D1 scientific formulation** defines the scientific question, observables, assumptions, evidence semantics, validity domain, uncertainty, and claims the workflow supports.
- **D2 numerical algorithm design** defines the numerical realization of D1: deterministic constructions, fitting/reduction algorithms, normalization, conditioning, stochastic semantics, failure handling, and numerical-equivalence requirements.
- **D3 architecture** under `docs/arch_manuals/` defines software decomposition, dependency direction, ownership boundaries, lifecycle, persistence, concurrency/resources, and integration consequences of D1/D2.
- **D4 specifications and implementation** under `docs/specs/` and source code define exact schemas, configuration fields, constants, source adapters, dependency/runtime contracts, and concrete realization.

The dependency direction is `D1 -> D2 -> D3 -> D4`. A downstream layer may challenge an upstream contract with evidence but may not silently redefine it.

## MLFF method set

The current MLFF method authority is a scoped method-paper family:

- [`mlff_scientific_method.md`](mlff_scientific_method.md) — general current normative D1 authority for MLFF training-data, target-size experiment, fine-tuning, validation, and production semantics outside the specialized target-order surface below.
- [`mlff_numerical_algorithmic_method.md`](mlff_numerical_algorithmic_method.md) — general current normative D2 authority realizing the general D1 formulation outside the specialized target-order surface below.
- [`mlff_target_training_order_scientific_method.md`](mlff_target_training_order_scientific_method.md) — sole current D1 owner for `TargetTrainingOrder` / `pi_train` membership design, multi-view coverage/support, configured-shell repair meaning, complete-order continuation, and membership qualification.
- [`mlff_target_training_order_numerical_algorithmic_method.md`](mlff_target_training_order_numerical_algorithmic_method.md) — sole current D2 owner for TargetCoverage/FEAS1/NEIGHBOR1/MVIDX1/MVSEL2/REPAIR2/MVQUAL numerical semantics and exact-equivalent optimized execution.

### Scoped precedence

The target-training-order papers were independently reviewed and stakeholder-ratified on 2026-09-15 under `MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1`. For their explicitly declared target-order scope, they supersede conflicting older target-order passages in the two general papers. The general papers remain current for every unaffected contract.

This is a permanent subject-matter decomposition of the current method family, not an amendment replay chain. Workplan reconstruction/addendum/review artifacts remain provenance and evidence only after promotion.

The original general papers were reconstructed losslessly from accepted pre-promotion architecture/specification/code evidence and accepted by the human owner on 2026-09-13, with later accepted revisions recorded in their own provenance. The target-order papers record the later 2026-09-15 MVSEL2 restoration separately so that earlier reviews are not retroactively represented as having covered it.

The current D3 architecture may restate an upstream consequence where local comprehension requires it, but such restatement is not independently tunable authority. Exact D4 contracts likewise realize D1-D3 rather than overriding them.
