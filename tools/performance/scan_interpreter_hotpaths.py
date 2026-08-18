#!/usr/bin/env python3
"""Static triage for Python loops in potentially large mdstats functions.

This is a review aid, not a profiler.  It ranks loops whose iterator/target names
suggest scaling with frames, atoms, nodes, faces, blocks, tiles, pairs, samples,
or graph candidates.  Human review must decide whether the loop is a coarse
orchestration boundary, an irregular graph algorithm, or an unjustified dense
numerical loop.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

TOKENS = (
    "frame", "atom", "node", "voxel", "grid", "face", "edge", "pair",
    "sample", "point", "triangle", "block", "tile", "offset", "ring",
    "candidate", "source", "target", "position", "vertex",
)


def enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
    return "<module>"


def scan(root: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.While)):
                continue
            iterator = ast.unparse(node.iter) if isinstance(node, ast.For) else ast.unparse(node.test)
            target = ast.unparse(node.target) if isinstance(node, ast.For) else ""
            text = f"{target} {iterator}".lower()
            matched = sorted(token for token in TOKENS if token in text)
            nested_loop_count = sum(
                isinstance(child, (ast.For, ast.While)) for child in ast.walk(node)
            ) - 1
            if not matched and nested_loop_count == 0:
                continue
            findings.append(
                {
                    "path": str(path.relative_to(root)),
                    "line": int(node.lineno),
                    "function": enclosing_function(node, parents),
                    "kind": type(node).__name__,
                    "target": target,
                    "iterator_or_test": iterator,
                    "matched_tokens": matched,
                    "nested_loop_count": int(nested_loop_count),
                    "ast_node_count": int(sum(1 for _ in ast.walk(node))),
                }
            )
    findings.sort(
        key=lambda item: (
            int(item["nested_loop_count"]),
            len(item["matched_tokens"]),
            int(item["ast_node_count"]),
        ),
        reverse=True,
    )
    return findings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("mdstats"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    findings = scan(args.root)
    payload = {"root": str(args.root), "finding_count": len(findings), "findings": findings}
    text = json.dumps(payload, indent=2) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
        print(args.output)


if __name__ == "__main__":
    main()
