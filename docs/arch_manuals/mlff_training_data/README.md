# MLFF D3 architecture canonical sources

The current D3 architecture is headed by `../mlff_training_data_architecture.md`. The numbered Markdown files in this directory are its **canonical detailed D3 sources**.

The upstream method authorities are:

- `docs/methods/mlff_scientific_method.md` - general current D1 scientific/mathematical authority;
- `docs/methods/mlff_numerical_algorithmic_method.md` - general current D2 numerical/algorithmic authority;
- `docs/methods/mlff_target_training_order_scientific_method.md` - accepted scoped D1 owner for `TargetTrainingOrder` / `pi_train`;
- `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md` - accepted scoped D2 owner for target-training-order numerics.

The scoped target-order papers supersede conflicting target-order passages in the general papers while leaving unrelated MLFF method authority unchanged. This chapter set is intentionally narrower than the retired pre-SSDP mixed architecture: it owns software decomposition, dependency/control flow, lifecycle, persistence, concurrency/resources, deployment structure, and integration consequences. It may restate D1/D2 consequences for local comprehension but cannot create a second independently tunable scientific or numerical authority.

The retired mixed architecture, including its old assembled Markdown/PDF publication chain and assembler, is preserved under `docs/history/mlff/architecture_snapshots/pre_d1_d2_promotion_2026-09-13/`.

| Order | Chapter | D3 purpose |
|---:|---|---|
| 00 | `00_front_matter.md` | D1-D4 authority boundary, architectural pipeline, package ownership |
| 01 | `10_foundations.md` | layering and structural D3 invariants |
| 02 | `20_data_contracts.md` | canonical evidence, identity, adapter, and artifact boundaries |
| 03 | `30_statistical_design.md` | evidence-flow, fitted-product, and invalidation integration |
| 04 | `40_training_evaluation.md` | training/replay/CV/production integration and currentness |
| 04B | `45_target_training_order.md` | canonical restored target-training-order ownership, persistence, restart, resource and D4 handoff |
| 05 | `50_target_size_selection.md` | target-size lifecycle, operator ownership, freeze, restart/currentness |
| 06 | `60_execution_performance.md` | bounded execution, restart, storage, resource, and performance architecture |
| 07 | `80_ownership_and_decisions.md` | ownership table, qualification/storage handoff, extension boundaries |
| 08 | `90_references.md` | supporting technical references retained from the pre-promotion architecture |

`70_status_and_gates.md` is not a current architecture chapter and must not be recreated as a task/status surface. Release/gate chronology is non-normative.

The current dependency/data-flow companion is `../mlff_training_data_dependency_graph.json`. D4 specifications remain indexed by `../../specs/training_data/README.md`.
