#!/usr/bin/env python3
"""One-shot G4 split of MLFF architectural dependencies from development state."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_dependency_graph.json"
HIST = ROOT / "docs" / "history" / "mlff" / "manual_snapshots"
HIST.mkdir(parents=True, exist_ok=True)
SNAP = HIST / "mlff_training_data_dependency_graph_pre_doc_gov1.json"

raw = GRAPH.read_text(encoding="utf-8")
if not SNAP.exists():
    SNAP.write_text(raw, encoding="utf-8")
g = json.loads(raw)

for key in ("architecture_revision", "branch", "documentation_gate", "next_gate"):
    g.pop(key, None)
g["description"] = (
    "Current MLFF training-data product/data/runtime dependency architecture. "
    "Developer implementation sequencing and completed engineering status are non-normative and live in workplans/history."
)
g["authority_model"] = "current_dependency_architecture"

# Development-only sequencing edges are not product architecture. Generic legacy
# edge names that express current product behavior are normalized to the current
# architectural vocabulary.
normalize = {
    "requires": "execution_requires",
    "gates": "promotion_requires",
    "qualification_requires": "release_qualification_requires",
}
drop_types = {"implementation_requires", "documentation_requires"}
new_edges = []
for edge in g.get("edges", []):
    et = edge.get("type")
    if et in drop_types:
        continue
    edge = dict(edge)
    edge["type"] = normalize.get(et, et)
    new_edges.append(edge)
g["edges"] = new_edges

defs = dict(g.get("edge_type_definitions", {}))
defs.pop("implementation_requires", None)
defs.pop("documentation_requires", None)
defs.update({
    "execution_requires": "The upstream current product/interface must exist before downstream execution.",
    "promotion_requires": "The upstream current product/evidence must satisfy the declared predicate before downstream promotion.",
    "release_qualification_requires": "The upstream qualification must pass before the applicable production release/promotion boundary.",
    "produces": "The upstream current execution or policy produces the downstream record/product.",
})
g["edge_type_definitions"] = defs

# Strip node-local development chronology/status while retaining scientific,
# runtime, schema, persistence, qualification-policy and compatibility fields.
exact_drop = {
    "architecture_revision", "gate_name", "implementation_status",
    "implemented_version", "implemented_release", "planned_release", "next_gate",
    "next_implementation_gate", "latest_implemented_gate", "latest_implemented_release",
    "current_status", "activation_status", "learning_control_status",
    "regenerated_release", "regeneration_gate", "superseded_handoff_release",
    "positive_runtime_evidence", "positive_accelerator_evidence", "positive_gpu_execution",
    "real_mace_gpu_execution_status", "final_gpu1_revision82_bundle_status",
    "workstation_bundle_current", "cpu_benchmark", "qualification_evidence",
    "basis", "failure_mode", "repair_scope", "regression_requirement",
    "optimization_program_closed", "final_gpu1_qualification_deferred",
    "final_gpu1_bundle_regenerated", "final_gpu1_bundle_regeneration_required",
    "runtime_behavior_changed", "production_authority_changed",
    "scientific_authority_change", "scientific_digest_changed", "scientific_schema_changed",
    "gpu_authority_change", "acceleration_policy_changed", "selection_identity_changed",
    "scientific_identity_changed", "runtime_selector_changed", "model_inference_change",
    "prediction_authority_changed", "pseudolabel_authority_changed", "true_label_authority_changed",
}

def is_dev_field(k: str) -> bool:
    return (
        k in exact_drop
        or k.startswith("planned_")
        or k.startswith("development_cpu_")
        or k.startswith("observed_")
        or k.startswith("final_gpu1_revision")
    )

nodes = []
for node in g.get("nodes", []):
    node = {k: v for k, v in node.items() if not is_dev_field(k)}
    nodes.append(node)

# Remove unreferenced nodes whose declared role is only a historical planning or
# non-authorizing diagnostic artifact. Historical authorities that participate
# in an explicit `supersedes` relation remain represented.
refs = {e.get("from") for e in new_edges} | {e.get("to") for e in new_edges}
filtered = []
for node in nodes:
    cls = str(node.get("authority_class", ""))
    project_only = (
        cls in {"architecture_plan", "architecture_plan_hardening", "documentation_architecture_freeze"}
        or cls.startswith("non_authorizing_diagnostic")
    )
    if project_only and node.get("id") not in refs:
        continue
    filtered.append(node)
g["nodes"] = filtered

# Structural validation.
node_ids = {n["id"] for n in g["nodes"]}
for e in g["edges"]:
    if e.get("from") not in node_ids or e.get("to") not in node_ids:
        raise SystemExit(f"edge endpoint missing after migration: {e}")
used_types = {e["type"] for e in g["edges"]}
undefined = used_types - set(g["edge_type_definitions"])
if undefined:
    raise SystemExit(f"undefined edge types after migration: {sorted(undefined)}")
if used_types & drop_types:
    raise SystemExit("development sequencing edge survived")
for n in g["nodes"]:
    bad = [k for k in n if is_dev_field(k)]
    if bad:
        raise SystemExit(f"development status survived on {n['id']}: {bad}")

GRAPH.write_text(json.dumps(g, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"edges: {len(g['edges'])}; nodes: {len(g['nodes'])}; types: {sorted(used_types)}")
