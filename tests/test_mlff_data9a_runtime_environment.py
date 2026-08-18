from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

import mdstats


MACE_SOURCE = Path(os.environ.get("MDSTATS_MACE_SOURCE", "/mnt/data/work_data9a/mace_src"))
MACE_ARCHIVE = Path(os.environ.get("MDSTATS_MACE_ARCHIVE", "/mnt/data/mace_torch-0.3.16.tar.gz"))
ASE_ARCHIVE = Path(os.environ.get("MDSTATS_ASE_ARCHIVE", "/mnt/data/ase-3.29.0.tar.gz"))
SETUPTOOLS_WHEEL = Path("/usr/share/python-wheels/setuptools-78.1.1-py3-none-any.whl")
DEPENDENCY_WHEELHOUSE = Path(os.environ.get("MDSTATS_MACE_WHEELHOUSE", "/mnt/data/mlff_realtest/deps/wheelhouse"))
HOSTLIST_ARCHIVE = Path(os.environ.get("MDSTATS_HOSTLIST_ARCHIVE", "/mnt/data/mlff_realtest/deps/sources/python_hostlist-2.3.0.tar.gz"))
ASE_SOURCE = Path(os.environ.get("MDSTATS_ASE_SOURCE", "/mnt/data/work_data9a/ase_src"))
QUALIFIED_RUNTIME_RECORD = Path(os.environ.get("MDSTATS_MACE_RUNTIME_RECORD", "/mnt/data/mlff_realtest/results/mdstats_offline_runtime_record.json"))
QUALIFIED_CLI_SMOKE_RECORD = Path(os.environ.get("MDSTATS_MACE_CLI_SMOKE_RECORD", "/mnt/data/mlff_realtest/results/mdstats_cli_smoke_record.json"))
ROOT = Path(__file__).resolve().parents[1]


def test_mace_dependency_manifest_matches_setup_cfg() -> None:
    if not MACE_SOURCE.is_dir():
        pytest.skip("supplied MACE source tree is not mounted")
    manifest = mdstats.read_mace_dependency_manifest(MACE_SOURCE)
    assert manifest.mace_version == "0.3.16"
    by_name = {item.distribution_name: item for item in manifest.requirements}
    assert by_name["e3nn"].specifier == "==0.4.4"
    assert by_name["torch-ema"].import_name == "torch_ema"
    assert by_name["python-hostlist"].import_name == "hostlist"
    assert by_name["gitpython"].import_name == "git"
    assert by_name["pyyaml"].import_name == "yaml"
    assert "lmdb" in by_name
    assert len(manifest.requirements) == 19
    assert mdstats.MaceDependencyManifest.from_dict(manifest.to_dict()) == manifest


def test_complete_supplied_runtime_and_cli_records_are_qualified() -> None:
    if not QUALIFIED_RUNTIME_RECORD.is_file() or not QUALIFIED_CLI_SMOKE_RECORD.is_file():
        pytest.skip("qualified supplied MACE runtime records are not mounted")
    environment = mdstats.MaceRuntimeEnvironmentRecord.from_dict(
        json.loads(QUALIFIED_RUNTIME_RECORD.read_text())
    )
    smoke = mdstats.MaceCliSmokeRecord.from_dict(
        json.loads(QUALIFIED_CLI_SMOKE_RECORD.read_text())
    )
    assert environment.installation_passed
    assert environment.mace_version == "0.3.16"
    assert environment.ase_version == "3.29.0"
    assert environment.torch_version is not None
    assert environment.base_python_executable
    assert environment.inherited_python_paths
    assert not environment.missing_required_distributions
    assert not environment.version_mismatches
    assert environment.qualified_for_cli_smoke
    assert smoke.environment_digest == environment.content_digest
    assert smoke.passed, smoke.to_dict()
    assert all(item.passed for item in smoke.command_results)


@pytest.mark.slow
def test_offline_runtime_builder_complete_stack_isolated(tmp_path: Path) -> None:
    if os.environ.get("MDSTATS_RUN_OFFLINE_BUILDER_TEST") != "1":
        pytest.skip("set MDSTATS_RUN_OFFLINE_BUILDER_TEST=1 for isolated rebuild")
    required = (
        MACE_SOURCE, MACE_ARCHIVE, ASE_ARCHIVE, SETUPTOOLS_WHEEL,
        DEPENDENCY_WHEELHOUSE, HOSTLIST_ARCHIVE,
    )
    if not all(path.exists() for path in required):
        pytest.skip("complete supplied offline MACE stack is not mounted")
    dependencies = (
        *mdstats.discover_mace_dependency_artifacts(DEPENDENCY_WHEELHOUSE),
        HOSTLIST_ARCHIVE,
    )
    environment = mdstats.create_mace_runtime_environment(
        tmp_path / "mace-env",
        mace_source_root=MACE_SOURCE,
        mace_archive=MACE_ARCHIVE,
        ase_archive=ASE_ARCHIVE,
        dependency_artifacts=dependencies,
        build_tool_artifacts=(SETUPTOOLS_WHEEL,),
        policy=mdstats.MaceRuntimeInstallPolicy(
            system_site_packages=True,
            offline=True,
            force_recreate=True,
            timeout_seconds=180.0,
        ),
    )
    assert environment.qualified_for_cli_smoke
    assert not environment.missing_required_distributions
    assert mdstats.run_mace_cli_smoke(environment).passed


def test_runtime_policy_and_smoke_policy_round_trip() -> None:
    install = mdstats.MaceRuntimeInstallPolicy(
        system_site_packages=False,
        offline=True,
        force_recreate=False,
        timeout_seconds=10.0,
    )
    assert mdstats.MaceRuntimeInstallPolicy.from_dict(install.to_dict()) == install
    smoke = mdstats.MaceCliSmokePolicy(
        commands=(("mace_run_train", "--help"),), timeout_seconds=10.0
    )
    assert mdstats.MaceCliSmokePolicy.from_dict(smoke.to_dict()) == smoke


def test_existing_source_qualification_accepts_complete_supplied_environment(tmp_path: Path) -> None:
    if not MACE_SOURCE.exists() or not ASE_SOURCE.exists():
        pytest.skip("supplied MACE/ASE source trees are not mounted")
    output = tmp_path / "source_qualification.json"
    code = """
import json
import os
import sys
from pathlib import Path
import mdstats
record = mdstats.qualify_mace_source_environment(
    Path(sys.argv[2]),
    ase_source_root=Path(sys.argv[3]),
)
Path(sys.argv[1]).write_text(json.dumps(record.to_dict()))
os._exit(0)
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    stdout_log = tmp_path / "source.stdout.log"
    stderr_log = tmp_path / "source.stderr.log"
    with stdout_log.open("wb") as stdout_handle, stderr_log.open("wb") as stderr_handle:
        completed = subprocess.run(
            [sys.executable, "-c", code, str(output), str(MACE_SOURCE), str(ASE_SOURCE)],
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            check=False,
            timeout=180.0,
        )
    assert completed.returncode == 0, stderr_log.read_text(errors="replace")[-4000:]
    record = mdstats.InstalledMaceQualificationRecord.from_dict(json.loads(output.read_text()))
    assert not record.missing_optional_dependencies
    assert not record.missing_required_dependencies
    assert record.run_train_import_passed
    assert record.qualified_for_training_smoke


def test_wheelhouse_discovery_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "b.tar.gz").write_bytes(b"b")
    (tmp_path / "a.whl").write_bytes(b"a")
    (tmp_path / "ignore.txt").write_text("x")
    observed = mdstats.discover_mace_dependency_artifacts(tmp_path)
    assert [path.name for path in observed] == ["a.whl", "b.tar.gz"]


def test_runtime_qualification_rejects_declared_version_mismatch() -> None:
    if not MACE_SOURCE.exists():
        pytest.skip("supplied MACE source tree is not mounted")
    manifest = mdstats.read_mace_dependency_manifest(MACE_SOURCE)
    status = tuple(
        (
            requirement.distribution_name,
            requirement.import_name,
            True,
            "0.3.0"
            if requirement.distribution_name == "e3nn"
            else "2.10.0"
            if requirement.distribution_name == "torch"
            else "1.0.0",
        )
        for requirement in manifest.requirements
    )
    mismatched = mdstats.MaceRuntimeEnvironmentRecord(
        dependency_manifest=manifest,
        install_policy=mdstats.MaceRuntimeInstallPolicy(),
        environment_root="/tmp/mace",
        base_python_executable="/usr/bin/python",
        python_executable="/tmp/mace/bin/python",
        python_version="3.11.0",
        inherited_python_paths=("/opt/base/site-packages",),
        supplied_artifacts=(),
        install_commands=(),
        dependency_status=status,
        mace_version="0.3.16",
        ase_version="3.29.0",
        torch_version="2.10.0",
        run_train_import_passed=True,
        eval_configs_import_passed=True,
        blocking_error_type=None,
        blocking_error_message=None,
    )
    assert ("e3nn", "==0.4.4", "0.3.0") in mismatched.version_mismatches
    assert not mismatched.qualified_for_cli_smoke
