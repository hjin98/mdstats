#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

POLICY = "mdstats.mvsel2-harden1-v3.q3-diff.v1"


def _norm_message(text: str, roots: list[str]) -> str:
    s = (text or "").strip().replace("\\", "/")
    for root in roots:
        if root:
            s = s.replace(str(Path(root).resolve()).replace("\\", "/"), "<CHECKOUT>")
    s = re.sub(r"/tmp/(?:pytest-of-[^/]+/pytest-\d+|tmp[^/\s]+)", "/tmp/<TMP>", s)
    s = re.sub(r"(?<=:)(\d+)(?::\d+)?\b", "<LINE>", s)
    s = re.sub(r"\b\d+(?:\.\d+)?s\b", "<TIME>", s)
    s = re.sub(r"\s+", " ", s)
    return s[:2000]


def _nodeid(tc: ET.Element) -> str:
    file_attr = (tc.get("file") or "").replace("\\", "/")
    classname = tc.get("classname") or ""
    name = tc.get("name") or ""
    if file_attr:
        module = file_attr[:-3].replace("/", ".") if file_attr.endswith(".py") else file_attr.replace("/", ".")
        suffix = classname[len(module):].lstrip(".") if classname.startswith(module) else ""
        parts = [file_attr]
        if suffix:
            parts.extend(suffix.split("."))
        parts.append(name)
        return "::".join(p for p in parts if p)
    return f"{classname}::{name}"


def parse(path: Path, roots: list[str]) -> dict:
    tree = ET.parse(path)
    root = tree.getroot()
    tests = {}
    counts = Counter()
    failures = []
    for tc in root.iter("testcase"):
        nodeid = _nodeid(tc)
        outcome = "pass"
        child = None
        for kind in ("failure", "error", "skipped"):
            child = tc.find(kind)
            if child is not None:
                outcome = kind
                break
        if child is not None and outcome in {"failure", "error"}:
            failures.append({
                "nodeid": nodeid,
                "outcome": outcome,
                "exception_type": child.get("type") or "",
                "normalized_primary_message": _norm_message(child.get("message") or (child.text or ""), roots),
            })
        tests[nodeid] = outcome
        counts[outcome] += 1
    return {"tests": tests, "counts": dict(counts), "failures": failures}


def sig(item: dict) -> tuple[str, str, str, str]:
    return (item["nodeid"], item["outcome"], item["exception_type"], item["normalized_primary_message"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-xml", required=True)
    ap.add_argument("--candidate-xml", required=True)
    ap.add_argument("--baseline-root", required=True)
    ap.add_argument("--candidate-root", required=True)
    ap.add_argument("--baseline-commit", required=True)
    ap.add_argument("--candidate-commit", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    roots = [args.baseline_root, args.candidate_root]
    try:
        baseline = parse(Path(args.baseline_xml), roots)
        candidate = parse(Path(args.candidate_xml), roots)
    except Exception as exc:
        print(f"Q3 differential comparator malformed input: {exc}", file=sys.stderr)
        return 2

    bset = {sig(x) for x in baseline["failures"]}
    cset = {sig(x) for x in candidate["failures"]}
    candidate_only = sorted(cset - bset)
    baseline_only = sorted(bset - cset)
    common = sorted(cset & bset)
    btests = baseline["tests"]
    ctests = candidate["tests"]
    new_candidate_bad = sorted(n for n, outcome in ctests.items() if n not in btests and outcome in {"failure", "error"})
    baseline_pass_regressions = sorted(n for n, outcome in ctests.items() if n in btests and btests[n] == "pass" and outcome in {"failure", "error"})
    candidate_collection_errors = sorted(x for x in candidate_only if x[1] == "error" and ("collect" in x[0].lower() or "collection" in x[3].lower()))
    passed = not candidate_only and not new_candidate_bad and not baseline_pass_regressions and not candidate_collection_errors

    payload = {
        "policy": POLICY,
        "baseline_commit": args.baseline_commit,
        "candidate_commit": args.candidate_commit,
        "baseline_counts": baseline["counts"],
        "candidate_counts": candidate["counts"],
        "baseline_failure_signatures": [list(x) for x in sorted(bset)],
        "candidate_failure_signatures": [list(x) for x in sorted(cset)],
        "candidate_only_signatures": [list(x) for x in candidate_only],
        "baseline_only_signatures": [list(x) for x in baseline_only],
        "common_signatures": [list(x) for x in common],
        "new_candidate_bad_tests": new_candidate_bad,
        "baseline_pass_regressions": baseline_pass_regressions,
        "candidate_only_collection_errors": [list(x) for x in candidate_collection_errors],
        "pass": passed,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"policy": POLICY, "pass": passed, "baseline_failures": len(bset), "candidate_failures": len(cset), "candidate_only": len(candidate_only), "baseline_pass_regressions": len(baseline_pass_regressions)}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
