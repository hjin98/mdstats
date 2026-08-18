from __future__ import annotations

import json
from pathlib import Path
import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_perf_p3_release_manual_graph_and_spec_are_synchronized() -> None:
    root=_root()
    manual=(root/'docs/arch_manuals/mlff_training_data_architecture.md').read_text()
    spec=(root/'docs/specs/training_data/mlff_perf_p3_cpu_structural_reduction_spec.md').read_text()
    graph=json.loads((root/'docs/arch_manuals/mlff_training_data_dependency_graph.json').read_text())
    node={item['id']:item for item in graph['nodes']}['PERF_P3_CPU_STRUCTURAL_REDUCTION']
    assert mdstats.__version__ == '0.20.187a0'
    assert 'revision 54' in manual
    assert 'PERF-P3 implementation record (`0.20.185a0`)' in manual
    assert '**Authority Class E**' in spec
    assert 'pair/radial scratch' in spec
    assert 'numpy.memmap' in spec and 'threadpoolctl' in spec
    assert graph['architecture_revision'] == 54
    assert graph['schema_version'] == 36
    assert node['implementation_status'] == 'implemented_cpu_qualified'
    assert node['implemented_version'] == '0.20.185a0'
    assert (root/'CHANGELOG.md').read_text().startswith('## 0.20.187a0 - 2026-08-15')
    assert '`mdstats 0.20.185a0` implements CPU structural/reduction hardening' in (root/'README.md').read_text()


def test_perf_p3_markdown_sources_exist_before_pdf_render() -> None:
    root=_root()
    for path in (root/'docs/specs/training_data/mlff_perf_p3_cpu_structural_reduction_spec.md', root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV52.md", root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.185a0.md", root/'benchmarks/mlff_perf_p3_cloud_cpu_2026-08-15.md'):
        assert path.is_file(), path
        assert path.stat().st_size > 1000, path
