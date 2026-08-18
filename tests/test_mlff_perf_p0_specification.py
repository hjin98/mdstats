from __future__ import annotations

import json
from pathlib import Path

import mdstats


SCIENTIFIC_DIGEST = "2f04aba96b876a10e62b7b0c22f26b544836005d11bc893177d4b29cbe4a3f82"
REFERENCE_DIGEST = "4f46dfaa6c366ede1cd4d19cf5fb8be65cfe49067b5aff85d668e0078915f9b8"
MIGRATION_DIGEST = "bbe21f1c20beaefb7c837ec20330365853727366f07e4b8a795745aa048bfd88"
BENCHMARK_SCIENTIFIC_DIGEST = "ab5e57750a06a3895d6349846238073a7bdca40a1c5270409999bfd6507a1d05"
BENCHMARK_EXECUTION_DIGEST = "4265881375205beb954222ac8d0b1372221c4779dcbc5567e9ff3a64d82681a1"
BENCHMARK_CONTENT_DIGEST = "cd9240e5c4936e1ac22409df8d56b06f487debd78f150bc3a45f7423d0917db0"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _evidence() -> dict[str, object]:
    path = _root() / "audits/analysis/mlff_perf_p0_lta_cloud_cpu_2026-08-15.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_perf_p0_is_public_versioned_and_documented() -> None:
    assert mdstats.__version__ == "0.20.185a0"
    assert mdstats.TARGET_COVERAGE_REFERENCE_SCHEMA == "mdstats.target-coverage-reference.v2"
    assert (
        mdstats.TARGET_COVERAGE_PERSISTENCE_VERSION
        == "mdstats.target-data2b.native-persistence.2026-08.v2"
    )
    for name in (
        "TARGET_COVERAGE_ARRAY_SCHEMA",
        "TARGET_COVERAGE_FAMILY_LEGACY_SCHEMA",
        "TARGET_COVERAGE_FAMILY_SCHEMA",
        "TARGET_COVERAGE_DOMAIN_LEGACY_SCHEMA",
        "TARGET_COVERAGE_DOMAIN_SCHEMA",
        "TARGET_COVERAGE_REFERENCE_LEGACY_SCHEMA",
        "TARGET_COVERAGE_REFERENCE_SCHEMA",
        "TARGET_COVERAGE_MIGRATION_SCHEMA",
        "TARGET_COVERAGE_NATIVE_MANIFEST_SCHEMA",
        "TARGET_COVERAGE_NATIVE_POINTER_SCHEMA",
        "TARGET_COVERAGE_NATIVE_WEIGHT_PROFILE_SCHEMA",
        "TargetCoverageMigrationReport",
        "TargetCoverageNativeStoreError",
        "compare_target_coverage_references_exact",
        "write_target_coverage_native_record",
        "read_target_coverage_native_record",
    ):
        assert hasattr(mdstats, name)

    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(
        encoding="utf-8"
    )
    specification = (
        root / "docs/specs/training_data/mlff_perf_p0_native_target_coverage_spec.md"
    ).read_text(encoding="utf-8")
    assert "PERF-P0 implementation record - 2026-08-15" in manual
    assert "Implementation status (`0.20.179a0`): complete" in manual
    assert "PERF-P1 implementation record - 2026-08-15" in manual
    assert "**VRAM1 + PERF-P4** is the next implementation gate" in manual
    assert "Release:** `mdstats 0.20.179a0`" in specification
    assert "Exact historical v1 compatibility and migration" not in specification
    assert "Historical v1 compatibility and migration" in specification
    assert "# References" in specification


def test_perf_p0_matched_evidence_freezes_exact_equivalence() -> None:
    evidence = _evidence()
    assert evidence["schema"] == "mdstats.mlff-perf-p0-benchmark.v1"
    assert evidence["source_version"] == "0.20.179a0"
    assert evidence["target_frames"] == 37_633
    assert evidence["target_atoms"] == 6_322_344
    assert evidence["source_units"] == 27
    assert evidence["family_element_count"] == 263_398
    assert evidence["scientific_digest"] == BENCHMARK_SCIENTIFIC_DIGEST
    assert evidence["execution_digest"] == BENCHMARK_EXECUTION_DIGEST
    assert evidence["content_digest"] == BENCHMARK_CONTENT_DIGEST

    comparison = evidence["comparison"]
    assert comparison["baseline_array_exact"] is True
    assert comparison["legacy_p0_exact"] is True
    assert comparison["legacy_scientific_digest"] == SCIENTIFIC_DIGEST
    assert comparison["p0_scientific_digest"] == SCIENTIFIC_DIGEST
    assert comparison["matched_wall_improvement_percent"] == 17.29576198455614

    runs = evidence["runs"]
    assert len(runs["legacy"]) == 5
    assert len(runs["p0"]) == 5
    for run in (*runs["legacy"], *runs["p0"]):
        assert run["scientific_digest"] == SCIENTIFIC_DIGEST
        assert run["family_element_count"] == 263_398
        assert len(run["fingerprints"]) == 48

    summaries = evidence["summaries"]
    assert summaries["legacy"]["wall_seconds"]["median"] == 7.5406899110003
    assert summaries["p0"]["wall_seconds"]["median"] == 6.23647013200025
    assert summaries["p0"]["wall_seconds"]["median"] < summaries["legacy"]["wall_seconds"]["median"]


def test_perf_p0_persistence_evidence_is_exact_and_materially_better() -> None:
    persistence = _evidence()["persistence"]
    migration = persistence["exact_migration"]
    legacy = persistence["legacy_v1"]
    native = persistence["native_v2"]

    assert persistence["reference_content_digest"] == REFERENCE_DIGEST
    assert migration["exact_match"] is True
    assert migration["difference_paths"] == []
    assert migration["content_digest"] == MIGRATION_DIGEST
    assert migration["target_content_digest"] == REFERENCE_DIGEST
    assert legacy["restored_digest"] == REFERENCE_DIGEST
    assert native["restored_digest"] == REFERENCE_DIGEST
    assert native["pointer"]["schema"] == mdstats.TARGET_COVERAGE_NATIVE_POINTER_SCHEMA
    assert native["pointer"]["persistence_version"] == mdstats.TARGET_COVERAGE_PERSISTENCE_VERSION
    assert native["write"]["wall_seconds"] < legacy["write"]["wall_seconds"]
    assert native["read"]["wall_seconds"] < legacy["read"]["wall_seconds"]
    assert native["size_bytes"] < legacy["size_bytes"]
    assert native["read"]["rss_increment_mib"] < legacy["read"]["rss_increment_mib"]


def test_perf_p0_release_indexes_and_dependency_graph_are_synchronized() -> None:
    root = _root()
    release = (root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.179a0.md").read_text(
        encoding="utf-8"
    )
    revision = (root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV45.md").read_text(
        encoding="utf-8"
    )
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    graph = json.loads(
        (root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text(
            encoding="utf-8"
        )
    )

    assert "PERF-P0 exact native TARGET-DATA2B" in release
    assert SCIENTIFIC_DIGEST in release
    assert REFERENCE_DIGEST in release
    assert "PERF-P0 exact native TARGET-DATA2B closure" in revision
    assert "## 0.20.179a0 - 2026-08-15" in changelog
    assert "`mdstats 0.20.179a0` completes bounded" in readme
    assert graph["schema_version"] == 34
    assert graph["architecture_revision"] == 52
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    assert node_by_id["PERF_BASE0_NUMERICAL_ORACLE"]["implemented_version"] == "0.20.178a0"
    assert node_by_id["TARGET_DATA2B_NATIVE_ARRAY_STORE"]["implemented_version"] == "0.20.179a0"
    assert node_by_id["PERF_P0_QUALIFICATION_EVIDENCE"]["implementation_status"] == "implemented"
    assert node_by_id["PERF_P1_EXACT_SELECTION_WORKSPACE"]["implementation_status"] == "implemented"
    assert node_by_id["PERF_P1_EXACT_SELECTION_WORKSPACE"]["implemented_version"] == "0.20.180a0"


def test_perf_p0_rendered_documents_are_packaged() -> None:
    root = _root()
    paths = (
        root / "docs/arch_manuals/mlff_training_data_architecture.pdf",
        root / "docs/specs/training_data/mlff_perf_p0_native_target_coverage_spec.pdf",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV45.pdf",
        root / "audits/analysis/mlff_perf_p0_lta_cloud_cpu_2026-08-15.pdf",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.179a0.pdf",
    )
    for path in paths:
        assert path.is_file(), path
        assert path.stat().st_size > 10_000, path
