import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mlff_python_sources_parse_with_python311_grammar():
    paths = sorted((ROOT / "mdstats" / "training_data").rglob("*.py"))
    paths += sorted((ROOT / "tools").glob("mdstats-mlff-*.py"))
    assert paths
    for path in paths:
        source = path.read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=str(path), feature_version=(3, 11))
        except SyntaxError as exc:
            raise AssertionError(f"Python 3.11 syntax failure in {path}: {exc}") from exc
