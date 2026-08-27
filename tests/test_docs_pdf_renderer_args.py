from __future__ import annotations

import json
from pathlib import Path
import runpy
import tempfile
import unittest


BUILDER = Path(__file__).resolve().parents[1] / "docs" / "build_pdfs.py"


class DocsPdfRendererArgsTests(unittest.TestCase):
    def test_typst_margin_is_structured_metadata_not_scalar_variable(self):
        namespace = runpy.run_path(str(BUILDER))
        renderer_args = namespace["_renderer_args"]
        config = {
            "renderer": {
                "from": "markdown+tex_math_single_backslash+tex_math_dollars",
                "pdf_engine": "typst",
                "papersize": "us-letter",
                "margin": "0.75in",
            }
        }
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "out.pdf"
            args = renderer_args(config, Path("docs/README.md"), output)
            self.assertIn("papersize:us-letter", args)
            self.assertNotIn("margin:0.75in", args)
            metadata_index = args.index("--metadata-file") + 1
            metadata_path = Path(args[metadata_index])
            self.assertEqual(
                json.loads(metadata_path.read_text(encoding="utf-8")),
                {"margin": {"x": "0.75in", "y": "0.75in"}},
            )


if __name__ == "__main__":
    unittest.main()
