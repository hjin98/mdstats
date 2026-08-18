from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "docs" / "specs"

CANONICAL = (
    "plotting/density_mesh_contracts_spec.md",
    "plotting/density_render_budget_spec.md",
    "plotting/density_scene_budget_spec.md",
    "plotting/density_scene_fit_spec.md",
    "plotting/density_mesh_simplify_spec.md",
    "plotting/density_mesh_execution_spec.md",
    "plotting/density_browser_acceptance_spec.md",
    "plotting/framework_dynamics_spec.md",
    "analysis/topology_catalog_spec.md",
    "performance/interpreter_hotpath_policy.md",
)

RETIRED = (
    "plotting/density_mesh_topology_revision_stage1_spec.md",
    "plotting/density_mesh_topology_revision_stage2_spec.md",
    "plotting/density_mesh_topology_revision_stages2_9_spec.md",
    "plotting/density_render_budget_ld9_v0_spec.md",
    "plotting/density_mesh_simplification_ld9_v2_spec.md",
    "plotting/density_scene_browser_ld9_v3_spec.md",
    "plotting/density_browser_acceptance_ld9_v4_spec.md",
    "performance/interpreter_hotpath_stage2.md",
)


def test_canonical_module_specs_exist():
    for rel in CANONICAL:
        assert (SPECS / rel).is_file(), rel


def test_retired_chronological_specs_are_absent():
    for rel in RETIRED:
        assert not (SPECS / rel).exists(), rel


def test_docs_do_not_reference_retired_spec_names():
    retired_names = tuple(Path(rel).name for rel in RETIRED)
    offenders = []
    for path in (ROOT / "docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for name in retired_names:
            if name in text:
                offenders.append((str(path.relative_to(ROOT)), name))
    assert not offenders, offenders


def test_framework_and_catalog_own_partitioned_topology_contracts():
    framework = (SPECS / "plotting/framework_dynamics_spec.md").read_text(encoding="utf-8")
    catalog = (SPECS / "analysis/topology_catalog_spec.md").read_text(encoding="utf-8")
    assert "FrameworkTopologyCategoryLayer" in framework
    assert 'legendgroup = "framework-topology:<k>"' in framework
    assert "Downstream category-consumer contract" in catalog


def test_scene_fit_owns_closed_loop_and_profiles():
    text = (SPECS / "plotting/density_scene_fit_spec.md").read_text(encoding="utf-8")
    assert "BrowserMeshProfile" in text
    assert "DensityShellGeometry" in text
    assert "301,838" in text and "314,640" in text and "582,375" in text
