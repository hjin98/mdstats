from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_foundation_audit1_hf1_release_and_graph_are_current() -> None:
    assert mdstats.__version__ == "0.20.209a0"
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["schema_version"] == 58
    node = next(item for item in graph["nodes"] if item["id"] == "FOUNDATION_AUDIT1_HF1_CFG_PLUMBING")
    assert node["architecture_revision"] == 63
    assert node["implemented_version"] == "0.20.196a0"
    assert node["scientific_identity_changed"] is False


def test_foundation_audit1_helper_has_explicit_cfg_and_call_site_passes_it() -> None:
    assert "cfg" in inspect.signature(campaign_cli._ensure_foundation_target_audit).parameters
    source = inspect.getsource(campaign_cli._prepare_materialization)
    assert "_ensure_foundation_target_audit(" in source
    assert "cfg=cfg" in source


def test_campaign_cli_has_no_top_level_helper_with_unbound_cfg_load() -> None:
    tree = ast.parse((ROOT / "mdstats/training_data/campaign_cli.py").read_text())
    offenders = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        loads = {item.id for item in ast.walk(node) if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Load)}
        args = {item.arg for item in (*node.args.args, *node.args.kwonlyargs)}
        assigned = {item.id for item in ast.walk(node) if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)}
        if "cfg" in loads and "cfg" not in args and "cfg" not in assigned:
            offenders.append(node.name)
    assert offenders == []
