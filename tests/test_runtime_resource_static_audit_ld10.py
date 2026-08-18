"""Static regression checks for LD10 resource-policy boundaries.

The test intentionally distinguishes host-compute admission from browser-output
profiles. Historical DEFAULT_MAX_* names remain importable for compatibility,
but compute modules must not use those values as active public defaults.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLOTTING = ROOT / "mdstats" / "plotting"

# These modules define client/output profiles rather than host compute admission.
BROWSER_PROFILE_MODULES = {
    "density_render_budget.py",
    "density_browser_acceptance.py",
}


def _module_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(), filename=str(path))


def test_historical_compute_caps_are_compatibility_only() -> None:
    violations: list[str] = []
    for path in sorted(PLOTTING.glob("density_*.py")):
        if path.name in BROWSER_PROFILE_MODULES:
            continue
        tree = _module_tree(path)
        historical: set[str] = set()
        for statement in tree.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name) and target.id.startswith("DEFAULT_MAX_"):
                        historical.add(target.id)
            elif isinstance(statement, ast.AnnAssign):
                target = statement.target
                if isinstance(target, ast.Name) and target.id.startswith("DEFAULT_MAX_"):
                    historical.add(target.id)
        if not historical:
            continue
        loads = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        for name in sorted(historical & loads):
            violations.append(f"{path.name}:{name}")
    assert not violations, (
        "Historical fixed compute caps became active again: " + ", ".join(violations)
    )


def test_primary_scene_compute_controls_are_optional_runtime_inputs() -> None:
    path = PLOTTING / "framework_dynamics.py"
    tree = _module_tree(path)
    resource_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FrameworkDynamicsResources"
    )
    defaults: dict[str, object] = {}
    for statement in resource_class.body:
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            if isinstance(statement.value, ast.Constant):
                defaults[statement.target.id] = statement.value.value
    assert defaults["max_memory_bytes"] is None
    assert defaults["max_threads"] is None
    assert defaults["max_wall_time_seconds"] is None
    assert defaults["memory_fraction"] == 0.8
    assert defaults["thread_fraction"] == 0.9


def test_all_species_example_has_no_fixed_host_compute_caps() -> None:
    source = (ROOT / "examples" / "plot_na_lta_300k_all_species_density.py").read_text()
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    resource_calls = [
        node
        for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "FrameworkDynamicsResources"
    ]
    assert len(resource_calls) == 1
    keywords = {keyword.arg: keyword.value for keyword in resource_calls[0].keywords}
    for name in ("max_memory_bytes", "max_threads", "max_wall_time_seconds"):
        assert name in keywords
        # The example passes CLI values (which default to None), not scene-fitted literals.
        assert isinstance(keywords[name], ast.Attribute)
