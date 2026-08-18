#!/usr/bin/env python3
"""One-shot, lossless G3 split of mixed MLFF specification authority."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs" / "specs" / "training_data"
HIST = ROOT / "docs" / "history" / "mlff" / "manual_snapshots"
HIST.mkdir(parents=True, exist_ok=True)

stage = SPEC_DIR / "mlff_data_stage_plan_spec.md"
readme = SPEC_DIR / "README.md"
stage_snapshot = HIST / "mlff_data_stage_plan_spec_pre_doc_gov1.md"
readme_snapshot = HIST / "training_data_spec_index_pre_doc_gov1.md"

stage_text = stage.read_text(encoding="utf-8")
readme_text = readme.read_text(encoding="utf-8")

if not stage_snapshot.exists():
    stage_snapshot.write_text(stage_text, encoding="utf-8")
if not readme_snapshot.exists():
    readme_snapshot.write_text(readme_text, encoding="utf-8")

marker = "\n# Stage gates\n"
current = stage_text.split(marker, 1)[0].rstrip() + "\n" if marker in stage_text else stage_text
current = current.replace(
    'title: "MLFF-DATA Stage and Data-Contract Specification"',
    'title: "MLFF Training-Data System Contract Specification"',
    1,
)

scope_start = current.find("# Scope\n")
principles_start = current.find("# Normative principles\n")
if scope_start < 0 or principles_start < 0 or principles_start <= scope_start:
    raise SystemExit("could not locate Scope/Normative principles boundary")
new_scope = """# Scope\n\nThis document is the cross-cutting current system contract for the mdstats MLFF training-data and fine-tuning workflow. It owns invariants that span multiple narrower module specifications: evidence-role separation, identity and lineage boundaries, leakage prevention, protocol identity, target/replay separation, MACE realization, calibration applicability, and append-only active-learning lineage.\n\nThe legacy filename is retained for stable repository references. It is **not** an implementation stage plan. Developer sequencing and future gates belong in `workplans/`; completed implementation chronology belongs in `docs/history/mlff/`. Narrower current specifications under this directory own module-local API, schema, algorithm, persistence, and runtime details.\n\n"""
current = current[:scope_start] + new_scope + current[principles_start:]
current = current.replace(
    "The first adapter may rely on MACE only for the behavior explicitly verified by its version lock and compatibility smoke tests:",
    "The MACE adapter may rely on MACE only for behavior explicitly verified by its current version lock and compatibility smoke tests:",
)
current = current.replace("The first adapter uses:", "The current adapter contract uses:")
current = current.rstrip() + """

# Authority and supersession

This specification owns only the cross-cutting invariants stated above. The dedicated current specifications listed in `README.md` own their module-local behavior and may refine implementation details without weakening these invariants. Runtime/product gates remain normative where they define current software behavior; developer implementation gates are non-normative coordination artifacts under `workplans/`.

The complete pre-DOC-GOV1 mixed specification, including completed stage chronology and historical/future developer planning, is preserved at `docs/history/mlff/manual_snapshots/mlff_data_stage_plan_spec_pre_doc_gov1.md` and is non-normative.
"""
stage.write_text(current, encoding="utf-8")

hier = "## Current specification hierarchy\n"
pos = readme_text.find(hier)
if pos < 0:
    raise SystemExit("could not locate current specification hierarchy")
remainder = readme_text[pos:]
new_readme = """# MLFF training-data specifications

This directory is the normative current-behavior layer for the MLFF training-data, fine-tuning, evaluation, deployment, and active-learning workflow. Specifications describe accepted behavior implemented by the current code; they are not implementation roadmaps or release chronologies.

## Authority model

- `mlff_data_stage_plan_spec.md` retains its legacy filename for stable links but is the **cross-cutting MLFF system contract**, not a stage plan. It owns workflow-wide invariants that are not usefully duplicated across narrower modules.
- Narrower specifications own module-local APIs, schemas, numerical behavior, persistence, runtime semantics, and compatibility contracts.
- Architecture under `docs/arch_manuals/` owns accepted current structure and ownership boundaries.
- Developer transitions and implementation gates live under `workplans/`.
- Completed chronology is non-normative and lives under `docs/history/mlff/`, `CHANGELOG.md`, release evidence, audits, or benchmarks as appropriate.

When a narrow specification refines a cross-cutting rule, both must remain compatible: the narrow document owns the detailed realization, while the system contract owns the invariant it serves.

""" + remainder
readme.write_text(new_readme, encoding="utf-8")

print(stage)
print(readme)
print(stage_snapshot)
print(readme_snapshot)
