#!/usr/bin/env python3
"""Incrementally build tracked documentation PDFs from authoritative Markdown.

The planner discovers ordinary tracked ``X.md``/``X.pdf`` publication pairs and
combines them with explicit composite/new-publication declarations from
``docs/pdf_publications.json``.  It is intentionally Git-aware so deletions,
renames, force-push ranges, and stale-write checks can reason about both trees.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "docs" / "pdf_publications.json"
ZERO_SHA = "0" * 40
REPRODUCIBLE_EPOCH = "0"
INFRA_PATHS = {
    ".github/workflows/docs-build.yml",
    "docs/build_pdfs.py",
    "docs/pdf_publications.json",
    "docs/build_architecture_pdf.sh",
    "tools/build_mlff_architecture_manual.py",
}


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class Publication:
    id: str
    source: str
    target: str
    dependencies: tuple[str, ...]
    assembler: tuple[str, ...] = ()
    generated_sources: tuple[str, ...] = ()
    manifest: str | None = None
    kind: str = "direct"

    @property
    def inputs(self) -> tuple[str, ...]:
        return self.dependencies or (self.source,)

    @property
    def outputs(self) -> tuple[str, ...]:
        values = [self.target, *self.generated_sources]
        if self.manifest:
            values.append(self.manifest)
        return tuple(dict.fromkeys(values))


def _run(args: Sequence[str], *, check: bool = True, text: bool = True, cwd: Path = ROOT, **kwargs):
    return subprocess.run(args, cwd=cwd, check=check, text=text, **kwargs)


def _git(*args: str, text: bool = True) -> str | bytes:
    cp = _run(("git", *args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text)
    return cp.stdout


def _load_config() -> dict:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise BuildError("unsupported docs/pdf_publications.json schema_version")
    return data


def _tracked_paths(ref: str) -> set[str]:
    if not ref or ref == ZERO_SHA:
        return set()
    out = _git("ls-tree", "-r", "--name-only", ref, "--", "docs")
    return {line for line in str(out).splitlines() if line}


def _explicit_publications(config: dict) -> list[Publication]:
    result: list[Publication] = []
    for raw in config.get("direct", []):
        source = raw["source"]
        target = raw.get("target") or str(PurePosixPath(source).with_suffix(".pdf"))
        result.append(Publication(
            id=raw.get("id", target), source=source, target=target,
            dependencies=tuple(raw.get("dependencies", [source])), kind="direct-explicit"
        ))
    for raw in config.get("composite", []):
        result.append(Publication(
            id=raw["id"], source=raw["source"], target=raw["target"],
            dependencies=tuple(raw["dependencies"]),
            assembler=tuple(raw.get("assembler", [])),
            generated_sources=tuple(raw.get("generated_sources", [])),
            manifest=raw.get("manifest"), kind="composite"
        ))
    return result


def publications_at(ref: str, config: dict | None = None) -> dict[str, Publication]:
    config = config or _load_config()
    explicit = _explicit_publications(config)
    paths = _tracked_paths(ref)
    reserved_sources = {p.source for p in explicit if p.kind == "composite"}
    by_target: dict[str, Publication] = {
        p.target: p for p in explicit
        if p.kind == "composite" or p.source in paths
    }
    for source in sorted(p for p in paths if p.endswith(".md")):
        if source in reserved_sources:
            continue
        target = str(PurePosixPath(source).with_suffix(".pdf"))
        if target in paths and target not in by_target:
            by_target[target] = Publication(
                id=target, source=source, target=target,
                dependencies=(source,), kind="direct"
            )
    return by_target


def _diff_name_status(before: str, after: str) -> list[tuple[str, str, str | None]]:
    raw = _git("diff", "--name-status", "-M", "-z", before, after, "--", ".", text=False)
    fields = bytes(raw).split(b"\0")
    if fields and not fields[-1]:
        fields.pop()
    result = []
    i = 0
    while i < len(fields):
        status = fields[i].decode(); i += 1
        code = status[0]
        if code in {"R", "C"}:
            old = fields[i].decode(); new = fields[i + 1].decode(); i += 2
            result.append((code, old, new))
        else:
            path = fields[i].decode(); i += 1
            result.append((code, path, None))
    return result


def _changed_paths(changes: Iterable[tuple[str, str, str | None]]) -> set[str]:
    result: set[str] = set()
    for _, old, new in changes:
        result.add(old)
        if new:
            result.add(new)
    return result


def plan_range(before: str, after: str) -> dict:
    config = _load_config()
    if not before or before == ZERO_SHA:
        pubs = publications_at(after, config)
        return _plan_payload("full-zero-before", pubs.values(), (), changed_paths=())
    _git("cat-file", "-e", f"{before}^{{commit}}")
    _git("cat-file", "-e", f"{after}^{{commit}}")
    changes = _diff_name_status(before, after)
    changed = _changed_paths(changes)
    after_pubs = publications_at(after, config)
    before_pubs = publications_at(before, config)
    if changed & INFRA_PATHS:
        return _plan_payload("full-infrastructure-change", after_pubs.values(), (), changed_paths=sorted(changed))

    selected: dict[str, Publication] = {}
    deletions: set[str] = set()
    deletion_records: dict[str, dict] = {}
    for target, pub in after_pubs.items():
        if changed.intersection(pub.inputs):
            selected[target] = pub
    for target, pub in after_pubs.items():
        if pub.source in changed:
            selected[target] = pub
    for target, old_pub in before_pubs.items():
        if target not in after_pubs and (old_pub.source in changed or changed.intersection(old_pub.inputs)):
            deletions.update(old_pub.outputs)
            deletion_records[old_pub.target] = {"source": old_pub.source, "target": old_pub.target, "outputs": list(old_pub.outputs)}
    for code, old, new in changes:
        if code == "R" and old.endswith(".md"):
            for old_pub in before_pubs.values():
                if old_pub.source == old and old_pub.target not in after_pubs:
                    deletions.update(old_pub.outputs)
                    deletion_records[old_pub.target] = {"source": old_pub.source, "target": old_pub.target, "outputs": list(old_pub.outputs)}
            if new:
                for pub in after_pubs.values():
                    if pub.source == new:
                        selected[pub.target] = pub
    return _plan_payload("incremental", selected.values(), deletions, changed_paths=sorted(changed), deletion_records=deletion_records.values())


def plan_paths(paths: Sequence[str], ref: str = "HEAD") -> dict:
    pubs = publications_at(ref)
    changed = set(paths)
    if changed & INFRA_PATHS:
        return _plan_payload("full-infrastructure-change", pubs.values(), (), changed_paths=sorted(changed))
    selected = [p for p in pubs.values() if p.source in changed or changed.intersection(p.inputs)]
    return _plan_payload("explicit-paths", selected, (), changed_paths=sorted(changed))


def _plan_payload(reason: str, pubs: Iterable[Publication], deletions: Iterable[str], *, changed_paths: Iterable[str], deletion_records: Iterable[dict] = ()) -> dict:
    unique = {p.target: p for p in pubs}
    return {
        "schema_version": 1,
        "reason": reason,
        "changed_paths": list(changed_paths),
        "targets": [publication_to_dict(unique[k]) for k in sorted(unique)],
        "deletions": sorted(set(deletions)),
        "deletion_records": sorted(deletion_records, key=lambda item: (item["target"], item["source"])),
    }


def publication_to_dict(pub: Publication) -> dict:
    return {
        "id": pub.id, "kind": pub.kind, "source": pub.source,
        "target": pub.target, "dependencies": list(pub.dependencies),
        "assembler": list(pub.assembler), "generated_sources": list(pub.generated_sources),
        "manifest": pub.manifest, "outputs": list(pub.outputs),
    }


def _publication_by_target(target: str, ref: str = "HEAD") -> Publication:
    pubs = publications_at(ref)
    if target in pubs:
        return pubs[target]
    matches = [p for p in pubs.values() if p.id == target]
    if len(matches) == 1:
        return matches[0]
    raise BuildError(f"unknown publication target: {target}")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _command_version(name: str) -> str:
    cp = _run((name, "--version"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return cp.stdout.splitlines()[0].strip()


def _renderer_metadata(config: dict, output: Path) -> Path:
    margin = config["renderer"].get("margin")
    metadata = output.with_name(output.name + ".metadata.json")
    data = {"margin": {"x": margin, "y": margin}} if margin else {}
    metadata.write_text(json.dumps(data), encoding="utf-8")
    return metadata


def _renderer_args(config: dict, source: Path, output: Path) -> list[str]:
    r = config["renderer"]
    return [
        "pandoc", str(source), "-o", str(output),
        "--from", r["from"], "--pdf-engine", r["pdf_engine"],
        "--resource-path", os.pathsep.join((str(source.parent), str(ROOT / "docs"), str(ROOT))),
        "-V", f"papersize:{r['papersize']}",
        "--metadata-file", str(_renderer_metadata(config, output)),
    ]


def _renderer_env() -> dict[str, str]:
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = REPRODUCIBLE_EPOCH
    return env


def _write_manifest(pub: Publication, config: dict, pdf: Path) -> None:
    if not pub.manifest:
        return
    source = ROOT / pub.source
    renderer = config["renderer"]
    renderer_config = {
        "from": renderer["from"], "margin": renderer["margin"],
        "papersize": renderer["papersize"], "pdf_engine": renderer["pdf_engine"],
        "source_date_epoch": REPRODUCIBLE_EPOCH,
    }
    if renderer.get("typst_binary"):
        renderer_config["typst_binary"] = renderer["typst_binary"]
    config_sha = hashlib.sha256(json.dumps(renderer_config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    data = {
        "schema_version": 1,
        "source": {"name": source.name, "sha256": _sha256(source)},
        "pdf": {"name": pdf.name, "sha256": _sha256(pdf)},
        "renderer": {
            "driver": "pandoc-local", "policy_version": "pandoc-typst-local-v2",
            "pandoc_version": _command_version("pandoc"),
            "typst_version": _command_version("typst"),
            "config": renderer_config,
            "config_sha256": config_sha,
        },
        "resources": [],
    }
    dest = ROOT / pub.manifest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, dest)


def build_publication(pub: Publication, config: dict) -> dict:
    if pub.assembler:
        _run(pub.assembler)
    source = ROOT / pub.source
    if not source.is_file():
        raise BuildError(f"publication source is missing: {pub.source}")
    target = ROOT / pub.target
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mdstats-doc-pdf-") as td:
        tmp_pdf = Path(td) / target.name
        _run(_renderer_args(config, source, tmp_pdf), env=_renderer_env())
        if not tmp_pdf.is_file() or tmp_pdf.stat().st_size == 0:
            raise BuildError(f"renderer did not create a nonempty PDF for {pub.target}")
        tmp_target = target.with_name(target.name + ".tmp")
        shutil.copyfile(tmp_pdf, tmp_target)
        os.replace(tmp_target, target)
    _write_manifest(pub, config, target)
    return {"target": pub.target, "sha256": _sha256(target), "outputs": list(pub.outputs)}


def execute_plan(plan: dict) -> dict:
    config = _load_config()
    built = []
    for raw in plan["targets"]:
        pub = Publication(
            id=raw["id"], kind=raw["kind"], source=raw["source"], target=raw["target"],
            dependencies=tuple(raw["dependencies"]), assembler=tuple(raw["assembler"]),
            generated_sources=tuple(raw["generated_sources"]), manifest=raw["manifest"]
        )
        built.append(build_publication(pub, config))
    deleted = []
    for rel in plan["deletions"]:
        path = ROOT / rel
        if path.exists():
            path.unlink()
            deleted.append(rel)
    return {**plan, "built": built, "deleted": deleted}


def fingerprint(target: str, ref: str) -> str:
    pub = _publication_by_target(target, ref)
    inputs = set(pub.inputs)
    inputs.update({"docs/build_pdfs.py", "docs/pdf_publications.json", ".github/workflows/docs-build.yml"})
    if pub.assembler:
        inputs.add(pub.assembler[-1])
    h = hashlib.sha256()
    for rel in sorted(inputs):
        try:
            blob = str(_git("rev-parse", f"{ref}:{rel}")).strip()
        except subprocess.CalledProcessError:
            blob = "<missing>"
        h.update(rel.encode()); h.update(b"\0"); h.update(blob.encode()); h.update(b"\0")
    return h.hexdigest()


def _write_json(data: dict, path: str | None) -> None:
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--before")
    p_plan.add_argument("--after", default="HEAD")
    p_plan.add_argument("--changed-path", action="append", default=[])
    p_plan.add_argument("--all", action="store_true")
    p_plan.add_argument("--target", action="append", default=[])
    p_plan.add_argument("--output")
    p_build = sub.add_parser("build")
    p_build.add_argument("--before")
    p_build.add_argument("--after", default="HEAD")
    p_build.add_argument("--changed-path", action="append", default=[])
    p_build.add_argument("--all", action="store_true")
    p_build.add_argument("--target", action="append", default=[])
    p_build.add_argument("--report")
    p_fp = sub.add_parser("fingerprint")
    p_fp.add_argument("--target", required=True)
    p_fp.add_argument("--ref", default="HEAD")
    args = parser.parse_args(argv)
    if args.cmd == "fingerprint":
        print(fingerprint(args.target, args.ref))
        return 0
    if args.all:
        plan = _plan_payload("full-explicit", publications_at(args.after).values(), (), changed_paths=())
    elif args.target:
        pubs = [_publication_by_target(t, args.after) for t in args.target]
        plan = _plan_payload("explicit-targets", pubs, (), changed_paths=())
    elif args.changed_path:
        plan = plan_paths(args.changed_path, args.after)
    elif args.before:
        plan = plan_range(args.before, args.after)
    else:
        parser.error("one of --all, --target, --changed-path, or --before is required")
    if args.cmd == "plan":
        _write_json(plan, args.output)
    else:
        result = execute_plan(plan)
        _write_json(result, args.report)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, subprocess.CalledProcessError) as exc:
        print(f"documentation PDF build failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
