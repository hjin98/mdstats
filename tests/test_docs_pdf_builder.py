from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE_BUILDER = Path(__file__).resolve().parents[1] / "docs" / "build_pdfs.py"
SOURCE_CONFIG = Path(__file__).resolve().parents[1] / "docs" / "pdf_publications.json"


def run(repo: Path, *args: str, env=None, check=True):
    return subprocess.run(args, cwd=repo, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=check, env=env)


class DocsPdfBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "docs").mkdir()
        (self.repo / ".github/workflows").mkdir(parents=True)
        (self.repo / "tools").mkdir()
        shutil.copy2(SOURCE_BUILDER, self.repo / "docs/build_pdfs.py")
        config = {
            "schema_version": 1,
            "renderer": {
                "from": "markdown", "pdf_engine": "typst",
                "papersize": "us-letter", "margin": "0.75in"
            },
            "direct": [], "composite": []
        }
        (self.repo / "docs/pdf_publications.json").write_text(json.dumps(config))
        (self.repo / ".github/workflows/docs-build.yml").write_text("name: test\n")
        (self.repo / "tools/build_mlff_architecture_manual.py").write_text("pass\n")
        run(self.repo, "git", "init", "-q")
        run(self.repo, "git", "config", "user.email", "test@example.invalid")
        run(self.repo, "git", "config", "user.name", "Test")
        self._pair("a", "A")
        self._pair("b", "B")
        (self.repo / "docs/README.md").write_text("index\n")
        self._commit("base")
        self.base = run(self.repo, "git", "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self.tmp.cleanup()

    def _pair(self, stem, text):
        (self.repo / f"docs/{stem}.md").write_text(f"# {text}\n")
        (self.repo / f"docs/{stem}.pdf").write_bytes(b"old-pdf")

    def _commit(self, msg):
        run(self.repo, "git", "add", "-A")
        run(self.repo, "git", "commit", "-qm", msg)
        return run(self.repo, "git", "rev-parse", "HEAD").stdout.strip()

    def _plan(self, before, after="HEAD"):
        out = run(self.repo, "python3", "docs/build_pdfs.py", "plan",
                  "--before", before, "--after", after).stdout
        return json.loads(out)

    def test_one_direct_change_selects_one_target(self):
        (self.repo / "docs/a.md").write_text("# A2\n")
        head = self._commit("a")
        plan = self._plan(self.base, head)
        self.assertEqual([x["target"] for x in plan["targets"]], ["docs/a.pdf"])

    def test_two_direct_changes_select_two_targets(self):
        (self.repo / "docs/a.md").write_text("# A2\n")
        (self.repo / "docs/b.md").write_text("# B2\n")
        head = self._commit("ab")
        plan = self._plan(self.base, head)
        self.assertEqual({x["target"] for x in plan["targets"]}, {"docs/a.pdf", "docs/b.pdf"})

    def test_unpaired_markdown_is_noop(self):
        (self.repo / "docs/README.md").write_text("index changed\n")
        head = self._commit("readme")
        self.assertEqual(self._plan(self.base, head)["targets"], [])

    def test_explicit_new_publication_builds_first_pdf(self):
        config = json.loads((self.repo / "docs/pdf_publications.json").read_text())
        config["direct"].append({"source": "docs/new.md", "target": "docs/new.pdf"})
        (self.repo / "docs/pdf_publications.json").write_text(json.dumps(config))
        (self.repo / "docs/new.md").write_text("# New\n")
        head = self._commit("new publication")
        plan = self._plan(self.base, head)
        self.assertIn("docs/new.pdf", {x["target"] for x in plan["targets"]})

    def test_deleted_publication_removes_stale_pdf(self):
        (self.repo / "docs/a.md").unlink()
        head = self._commit("delete source")
        plan = self._plan(self.base, head)
        self.assertIn("docs/a.pdf", plan["deletions"])
        self.assertEqual(plan["deletion_records"][0]["source"], "docs/a.md")

    def test_rename_removes_old_and_selects_new_pair(self):
        run(self.repo, "git", "mv", "docs/a.md", "docs/c.md")
        run(self.repo, "git", "mv", "docs/a.pdf", "docs/c.pdf")
        head = self._commit("rename pair")
        plan = self._plan(self.base, head)
        self.assertIn("docs/a.pdf", plan["deletions"])
        self.assertIn("docs/c.pdf", {x["target"] for x in plan["targets"]})

    def test_rename_source_without_new_pdf_deletes_old_only(self):
        run(self.repo, "git", "mv", "docs/a.md", "docs/note.md")
        head = self._commit("rename source")
        plan = self._plan(self.base, head)
        self.assertIn("docs/a.pdf", plan["deletions"])
        self.assertNotIn("docs/note.pdf", {x["target"] for x in plan["targets"]})

    def test_zero_before_is_conservative_full_build(self):
        plan = self._plan("0" * 40)
        self.assertEqual(plan["reason"], "full-zero-before")
        self.assertEqual({x["target"] for x in plan["targets"]}, {"docs/a.pdf", "docs/b.pdf"})

    def test_nonancestor_range_uses_final_tree_delta(self):
        run(self.repo, "git", "checkout", "-qb", "left", self.base)
        (self.repo / "docs/a.md").write_text("# left\n")
        left = self._commit("left")
        run(self.repo, "git", "checkout", "-qb", "right", self.base)
        (self.repo / "docs/b.md").write_text("# right\n")
        right = self._commit("right")
        plan = self._plan(left, right)
        self.assertEqual({x["target"] for x in plan["targets"]}, {"docs/a.pdf", "docs/b.pdf"})

    def test_composite_dependency_selects_composite_only(self):
        config = json.loads((self.repo / "docs/pdf_publications.json").read_text())
        (self.repo / "docs/parts").mkdir()
        (self.repo / "docs/parts/chapter.md").write_text("chapter\n")
        (self.repo / "docs/book.md").write_text("book\n")
        (self.repo / "docs/book.pdf").write_bytes(b"old")
        config["composite"].append({
            "id": "book", "source": "docs/book.md", "target": "docs/book.pdf",
            "dependencies": ["docs/parts/chapter.md"], "assembler": [],
            "generated_sources": ["docs/book.md"]
        })
        (self.repo / "docs/pdf_publications.json").write_text(json.dumps(config))
        base2 = self._commit("composite setup")
        (self.repo / "docs/parts/chapter.md").write_text("changed\n")
        head = self._commit("chapter")
        plan = self._plan(base2, head)
        self.assertEqual([x["target"] for x in plan["targets"]], ["docs/book.pdf"])

    def test_renderer_failure_preserves_tracked_pdf(self):
        original = (self.repo / "docs/a.pdf").read_bytes()
        (self.repo / "docs/a.md").write_text("# changed\n")
        self._commit("source")
        bindir = self.repo / "bin"; bindir.mkdir()
        fake = bindir / "pandoc"
        fake.write_text("#!/bin/sh\nexit 17\n")
        fake.chmod(0o755)
        env = os.environ.copy(); env["PATH"] = f"{bindir}:{env['PATH']}"
        cp = run(self.repo, "python3", "docs/build_pdfs.py", "build",
                 "--changed-path", "docs/a.md", env=env, check=False)
        self.assertNotEqual(cp.returncode, 0)
        self.assertEqual((self.repo / "docs/a.pdf").read_bytes(), original)

    def test_renderer_uses_structured_margin_and_fixed_epoch(self):
        (self.repo / "docs/a.md").write_text("# changed\n")
        self._commit("source")
        bindir = self.repo / "bin"; bindir.mkdir()
        fake = bindir / "pandoc"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            "args = sys.argv[1:]\n"
            "outfile = pathlib.Path(args[args.index('-o') + 1])\n"
            "metadata = pathlib.Path(args[args.index('--metadata-file') + 1])\n"
            "pathlib.Path('pandoc-observed.json').write_text(json.dumps({\n"
            "    'epoch': os.environ.get('SOURCE_DATE_EPOCH'),\n"
            "    'metadata': json.loads(metadata.read_text()),\n"
            "}))\n"
            "outfile.write_bytes(b'%PDF-1.7\\n%%EOF\\n')\n"
        )
        fake.chmod(0o755)
        env = os.environ.copy(); env["PATH"] = f"{bindir}:{env['PATH']}"
        run(self.repo, "python3", "docs/build_pdfs.py", "build",
            "--changed-path", "docs/a.md", env=env)
        observed = json.loads((self.repo / "pandoc-observed.json").read_text())
        self.assertEqual(observed["epoch"], "0")
        self.assertEqual(observed["metadata"], {"margin": {"x": "0.75in", "y": "0.75in"}})

    def test_fingerprint_ignores_unrelated_code_but_tracks_source(self):
        first = run(self.repo, "python3", "docs/build_pdfs.py", "fingerprint",
                    "--target", "docs/a.pdf", "--ref", "HEAD").stdout.strip()
        (self.repo / "unrelated.py").write_text("x=1\n")
        unrelated = self._commit("unrelated")
        second = run(self.repo, "python3", "docs/build_pdfs.py", "fingerprint",
                     "--target", "docs/a.pdf", "--ref", unrelated).stdout.strip()
        self.assertEqual(first, second)
        (self.repo / "docs/a.md").write_text("# changed\n")
        changed = self._commit("source")
        third = run(self.repo, "python3", "docs/build_pdfs.py", "fingerprint",
                    "--target", "docs/a.pdf", "--ref", changed).stdout.strip()
        self.assertNotEqual(second, third)


if __name__ == "__main__":
    unittest.main()
