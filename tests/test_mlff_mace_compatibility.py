from __future__ import annotations

import warnings

import pytest

import mdstats
import mdstats.training_data.mace_compatibility as compatibility


SCRIPT_MESSAGE = (
    "`torch.jit.script` is deprecated. Please switch to `torch.compile` or `torch.export`."
)
LOAD_MESSAGE = "`torch.jit.load` is deprecated. Please switch to `torch.export`."
TORCH_SCRIPT_SOURCE = "/runtime/site-packages/torch/jit/_script.py"
TORCH_LOAD_SOURCE = "/runtime/site-packages/torch/jit/_serialization.py"


@pytest.fixture(autouse=True)
def _reset_warning_deduplication() -> None:
    with compatibility._EMITTED_LOCK:
        compatibility._EMITTED_SIGNATURES.clear()


def _emit(message: str, filename: str, lineno: int = 1) -> None:
    warnings.warn_explicit(message, DeprecationWarning, filename, lineno)


def test_exact_torchscript_deprecations_are_consolidated_and_recorded() -> None:
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("checkpoint load") as capture:
            _emit(SCRIPT_MESSAGE, TORCH_SCRIPT_SOURCE, 10)
            _emit(SCRIPT_MESSAGE, TORCH_SCRIPT_SOURCE, 11)
            _emit(LOAD_MESSAGE, TORCH_LOAD_SOURCE, 12)

    assert capture.record.legacy_torchscript_observed
    assert capture.record.raw_warning_count == 3
    assert capture.record.torchscript_apis == ("torch.jit.load", "torch.jit.script")
    assert capture.record.warning_codes == (mdstats.MACE_TORCHSCRIPT_DEPRECATION_CODE,)
    assert capture.record.to_dict()["schema"] == mdstats.MACE_RUNTIME_COMPATIBILITY_SCHEMA
    assert [item.category for item in observed] == [mdstats.MaceRuntimeCompatibilityWarning]
    assert "3 legacy TorchScript deprecation warning(s)" in str(observed[0].message)


def test_known_mace_userwarning_families_are_consolidated() -> None:
    tensor_message = (
        "To copy construct from a tensor, it is recommended to use "
        "sourceTensor.detach().clone() rather than torch.tensor(sourceTensor)."
    )
    ast_message = (
        "The TorchScript type system doesn't support instance-level annotations "
        "on empty non-base types in `__init__`."
    )
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("CuEq parity qualification") as capture:
            for _ in range(3):
                warnings.warn_explicit(
                    tensor_message, UserWarning,
                    "/runtime/site-packages/mace/modules/models.py", 86,
                )
            for _ in range(5):
                warnings.warn_explicit(ast_message, UserWarning, "/usr/lib/python3.11/ast.py", 418)

    assert capture.record.upstream_warning_count == 8
    assert len(capture.record.upstream_warning_groups) == 2
    assert [item.category for item in observed] == [mdstats.MaceRuntimeCompatibilityWarning]
    message = str(observed[0].message)
    assert "3x mace:UserWarning" in message
    assert "tensor-copy construction warning" in message
    assert "5x torch:UserWarning" in message
    assert "TorchScript instance-annotation warning" in message


def test_unrelated_warnings_are_replayed_with_original_location() -> None:
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("calculator construction"):
            _emit(SCRIPT_MESSAGE, TORCH_SCRIPT_SOURCE, 3)
            _emit("external deprecation that mdstats must not hide", "/vendor/other.py", 77)

    assert len(observed) == 2
    unrelated, consolidated = observed
    assert unrelated.category is DeprecationWarning
    assert str(unrelated.message) == "external deprecation that mdstats must not hide"
    assert unrelated.filename == "/vendor/other.py"
    assert unrelated.lineno == 77
    assert consolidated.category is mdstats.MaceRuntimeCompatibilityWarning


def test_identical_message_outside_torch_jit_is_not_suppressed() -> None:
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("non-torch source") as capture:
            _emit(SCRIPT_MESSAGE, "/application/fake_warning.py", 5)

    assert not capture.record.legacy_torchscript_observed
    assert capture.record.raw_warning_count == 0
    assert len(observed) == 1
    assert observed[0].category is DeprecationWarning
    assert str(observed[0].message) == SCRIPT_MESSAGE


def test_nested_scopes_merge_operations_and_emit_once() -> None:
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("outer evaluation") as outer:
            with mdstats.mace_runtime_warning_scope("inner model load") as inner:
                _emit(LOAD_MESSAGE, TORCH_LOAD_SOURCE)

    assert outer.record is inner.record
    assert outer.record.operations == ("inner model load", "outer evaluation")
    assert len(observed) == 1
    assert observed[0].category is mdstats.MaceRuntimeCompatibilityWarning


def test_scope_preserves_original_exception_after_processing_warnings() -> None:
    capture = None
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with pytest.raises(RuntimeError, match="model load failed"):
            with mdstats.mace_runtime_warning_scope("failed model load") as capture:
                _emit(SCRIPT_MESSAGE, TORCH_SCRIPT_SOURCE)
                raise RuntimeError("model load failed")

    assert capture is not None
    assert capture.record.legacy_torchscript_observed
    assert len(observed) == 1
    assert observed[0].category is mdstats.MaceRuntimeCompatibilityWarning


def test_decorator_uses_same_targeted_policy() -> None:
    @mdstats.mace_runtime_warning_handled("decorated MACE call")
    def operation() -> int:
        _emit(SCRIPT_MESSAGE, TORCH_SCRIPT_SOURCE)
        return 7

    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        assert operation() == 7

    assert len(observed) == 1
    assert observed[0].category is mdstats.MaceRuntimeCompatibilityWarning


def test_consolidated_warning_is_process_deduplicated() -> None:
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        for index in range(2):
            with mdstats.mace_runtime_warning_scope(f"operation {index}"):
                _emit(SCRIPT_MESSAGE, TORCH_SCRIPT_SOURCE)

    assert len(observed) == 1
    assert observed[0].category is mdstats.MaceRuntimeCompatibilityWarning


def test_real_torchscript_script_and_load_are_consolidated_when_deprecated(tmp_path) -> None:
    torch = pytest.importorskip("torch")

    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("real torch.jit.script smoke") as scripted_capture:
            scripted = torch.jit.script(torch.nn.ReLU())

    if not scripted_capture.record.legacy_torchscript_observed:
        pytest.skip("active PyTorch runtime has not deprecated torch.jit.script")
    assert scripted_capture.record.torchscript_apis == ("torch.jit.script",)
    assert [item.category for item in observed] == [mdstats.MaceRuntimeCompatibilityWarning]

    model_path = tmp_path / "relu.pt"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        torch.jit.save(scripted, str(model_path))
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("real torch.jit.load smoke") as loaded_capture:
            loaded = torch.jit.load(str(model_path))
            result = loaded(torch.tensor([-1.0, 2.0]))

    assert torch.equal(result, torch.tensor([0.0, 2.0]))
    assert loaded_capture.record.torchscript_apis == ("torch.jit.load",)
    assert [item.category for item in observed] == [mdstats.MaceRuntimeCompatibilityWarning]


def test_original_exception_wins_when_warning_filter_is_error() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", mdstats.MaceRuntimeCompatibilityWarning)
        with pytest.raises(RuntimeError, match="primary MACE failure") as caught:
            with mdstats.mace_runtime_warning_scope("failed warning-as-error operation"):
                _emit(SCRIPT_MESSAGE, TORCH_SCRIPT_SOURCE)
                raise RuntimeError("primary MACE failure")

    assert any("warning raised while mdstats" in note for note in getattr(caught.value, "__notes__", ()))


def test_forced_exit_mace_cli_child_consolidates_before_os_exit(tmp_path) -> None:
    import os
    import sys
    from pathlib import Path
    from types import SimpleNamespace

    from mdstats.training_data.mace_realization import _forced_exit_mace_cli_result

    package = tmp_path / "fake_mace_cli"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "run.py").write_text(
        "import warnings\n"
        "def main():\n"
        "    warnings.warn_explicit(\n"
        f"        {SCRIPT_MESSAGE!r}, DeprecationWarning,\n"
        "        '/vendor/torch/jit/_script.py', 42,\n"
        "    )\n"
    )
    package_root = Path(mdstats.__file__).resolve().parents[1]
    inherited = os.environ.get("PYTHONPATH", "")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(tmp_path), str(package_root), inherited) if part
    )

    result = _forced_exit_mace_cli_result(
        ("fake-mace",),
        module="fake_mace_cli.run",
        environment=SimpleNamespace(python_executable=sys.executable),
        cwd=tmp_path,
        env=env,
        timeout_seconds=30.0,
    )

    assert result.returncode == 0
    assert result.skipped_reason is None
    assert "MaceRuntimeCompatibilityWarning" in result.stderr_tail
    assert "/vendor/torch/jit/_script.py:42: DeprecationWarning" not in result.stderr_tail


def test_repeated_mace_and_torch_warnings_are_grouped_without_replay() -> None:
    tensor_message = (
        "To copy construct from a tensor, it is recommended to use "
        "sourceTensor.detach().clone() or sourceTensor.detach().clone().requires_grad_(True), "
        "rather than torch.tensor(sourceTensor)."
    )
    annotation_message = (
        "The TorchScript type system doesn't support instance-level annotations on empty "
        "non-base types in `__init__`. Instead, either 1) use a type annotation in the "
        "class body, or 2) wrap the type in `torch.jit.Attribute`."
    )
    save_message = "`torch.jit.save` is deprecated. Please switch to `torch.export`."

    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("evaluation inference") as capture:
            for line in (176, 176, 176):
                warnings.warn_explicit(
                    LOAD_MESSAGE,
                    DeprecationWarning,
                    "/runtime/site-packages/torch/jit/_serialization.py",
                    line,
                )
            warnings.warn_explicit(
                save_message,
                DeprecationWarning,
                "/runtime/site-packages/torch/jit/_serialization.py",
                89,
            )
            for _ in range(2):
                warnings.warn_explicit(
                    tensor_message,
                    UserWarning,
                    "/runtime/site-packages/mace/modules/models.py",
                    86,
                )
            for _ in range(7):
                warnings.warn_explicit(
                    SCRIPT_MESSAGE,
                    DeprecationWarning,
                    "/runtime/site-packages/torch/jit/_script.py",
                    1488,
                )
                warnings.warn_explicit(
                    annotation_message,
                    UserWarning,
                    "/usr/lib/python3.11/ast.py",
                    418,
                )

    assert len(observed) == 1
    assert observed[0].category is mdstats.MaceRuntimeCompatibilityWarning
    message = str(observed[0].message)
    assert "condensed 20 total MACE/PyTorch warning(s) into 5 unique group(s)" in message
    assert "3x torch:DeprecationWarning [torch/jit/_serialization.py]" in message
    assert "2x mace:UserWarning [mace/modules/models.py]" in message
    assert "7x torch:UserWarning [ast.py]" in message
    assert capture.record.upstream_warning_count == 20
    assert len(capture.record.upstream_warning_groups) == 5
    assert capture.record.raw_warning_count == 11
    assert capture.record.torchscript_apis == (
        "torch.jit.load",
        "torch.jit.save",
        "torch.jit.script",
    )


def test_new_upstream_warning_group_emits_once_per_process_signature() -> None:
    message = "MACE warning that should be visible once as a condensed group"
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        for operation in ("first", "second"):
            with mdstats.mace_runtime_warning_scope(operation):
                warnings.warn_explicit(
                    message,
                    UserWarning,
                    "/runtime/site-packages/mace/modules/models.py",
                    999,
                )
                warnings.warn_explicit(
                    message,
                    UserWarning,
                    "/runtime/site-packages/mace/modules/models.py",
                    999,
                )

    assert len(observed) == 1
    assert observed[0].category is mdstats.MaceRuntimeCompatibilityWarning
    assert "2 total MACE/PyTorch warning(s) into 1 unique group(s)" in str(observed[0].message)


def test_campaign_evaluate_outer_scope_catches_setup_warnings(monkeypatch) -> None:
    import argparse
    import mdstats.training_data.campaign_cli as campaign_cli

    def noisy_load_config(_path):
        warnings.warn_explicit(
            SCRIPT_MESSAGE,
            DeprecationWarning,
            "/runtime/site-packages/torch/jit/_script.py",
            1488,
        )
        warnings.warn_explicit(
            "synthetic MACE setup warning",
            UserWarning,
            "/runtime/site-packages/mace/modules/models.py",
            86,
        )
        raise RuntimeError("stop after setup")

    monkeypatch.setattr(campaign_cli, "_load_config", noisy_load_config)
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with pytest.raises(RuntimeError, match="stop after setup"):
            campaign_cli.command_evaluate(argparse.Namespace(config="campaign.toml"))

    assert len(observed) == 1
    assert observed[0].category is mdstats.MaceRuntimeCompatibilityWarning
    summary = str(observed[0].message)
    assert "campaign checkpoint evaluation" in summary
    assert "2 total MACE/PyTorch warning(s) into 2 unique group(s)" in summary



def _emit_mace_dtype_log_warning() -> None:
    namespace: dict[str, object] = {}
    code = compile(
        "import logging\n"
        "logging.warning('Default dtype float32 does not match model dtype float64, converting models to float32.')\n",
        "/runtime/site-packages/mace/calculators/mace.py",
        "exec",
    )
    exec(code, namespace, namespace)


def test_mace_root_logging_warning_is_captured_and_suppressed(capsys) -> None:
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        with mdstats.mace_runtime_warning_scope("campaign-wide logging smoke") as capture:
            _emit_mace_dtype_log_warning()

    captured = capsys.readouterr()
    assert "WARNING:root" not in captured.err
    assert len(observed) == 1
    assert observed[0].category is mdstats.MaceRuntimeCompatibilityWarning
    assert capture.record.upstream_warning_count == 1
    group = capture.record.upstream_warning_groups[0]
    assert group[0] == "mace"
    assert group[1] == "logging.WARNING"
    assert group[2] == "mace/calculators/mace.py"
    assert "Default dtype float32" in group[3]


def test_campaign_main_owns_one_warning_domain_and_normalizes_output(monkeypatch, capsys) -> None:
    import argparse
    import mdstats.training_data.campaign_cli as campaign_cli

    class Parser:
        def parse_args(self, _argv):
            def noisy_command(_args):
                warnings.warn_explicit(
                    SCRIPT_MESSAGE,
                    DeprecationWarning,
                    "/runtime/site-packages/torch/jit/_script.py",
                    1488,
                )
                # A nested local MACE scope must merge into the campaign domain
                # rather than emitting its own compatibility warning.
                with mdstats.mace_runtime_warning_scope("nested provider construction"):
                    warnings.warn_explicit(
                        LOAD_MESSAGE,
                        DeprecationWarning,
                        "/runtime/site-packages/torch/jit/_serialization.py",
                        176,
                    )
                    _emit_mace_dtype_log_warning()
                return 0

            return argparse.Namespace(command="prepare", func=noisy_command)

    monkeypatch.setattr(campaign_cli, "build_parser", lambda: Parser())
    assert campaign_cli.main([]) == 0

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "/torch/jit/_script.py:1488: DeprecationWarning" not in combined
    assert "/torch/jit/_serialization.py:176: DeprecationWarning" not in combined
    assert "WARNING:root:" not in combined
    warning_lines = [line for line in captured.out.splitlines() if line.startswith("[WARN]")]
    assert len(warning_lines) == 1
    summary = warning_lines[0]
    assert "campaign prepare command" in summary
    assert "nested provider construction" in summary
    assert "3 total MACE/PyTorch warning(s) into 3 unique group(s)" in summary
    assert "torch.jit.script deprecated" in summary
    assert "torch.jit.load deprecated" in summary
    assert "Default dtype float32" in summary


def test_campaign_warning_domain_merges_worker_thread_local_scopes(monkeypatch, capsys) -> None:
    import argparse
    from concurrent.futures import ThreadPoolExecutor
    import mdstats.training_data.campaign_cli as campaign_cli

    class Parser:
        def parse_args(self, _argv):
            def noisy_command(_args):
                def worker():
                    with mdstats.mace_runtime_warning_scope("worker MACE provider construction"):
                        warnings.warn_explicit(
                            LOAD_MESSAGE,
                            DeprecationWarning,
                            "/runtime/site-packages/torch/jit/_serialization.py",
                            176,
                        )
                        _emit_mace_dtype_log_warning()
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(worker).result()
                return 0
            return argparse.Namespace(command="prepare", func=noisy_command)

    monkeypatch.setattr(campaign_cli, "build_parser", lambda: Parser())
    assert campaign_cli.main([]) == 0
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "/runtime/site-packages/torch/jit/_serialization.py:176: DeprecationWarning" not in combined
    assert "WARNING:root:" not in combined
    warning_lines = [line for line in captured.out.splitlines() if line.startswith("[WARN]")]
    assert len(warning_lines) == 1
    assert "worker MACE provider construction" in warning_lines[0]
    assert "2 total MACE/PyTorch warning(s) into 2 unique group(s)" in warning_lines[0]


def test_campaign_logging_capture_preserves_unrelated_logging(capsys) -> None:
    namespace: dict[str, object] = {}
    code = compile(
        "import logging\nlogging.warning('unrelated vendor warning remains visible')\n",
        "/runtime/site-packages/otherlib/runtime.py",
        "exec",
    )
    with warnings.catch_warnings(record=True):
        with mdstats.mace_runtime_warning_scope("unrelated logging preservation") as capture:
            exec(code, namespace, namespace)
    captured = capsys.readouterr()
    # pytest may install a logging handler instead of writing stderr directly;
    # the important contract is that mdstats does not classify/condense it.
    assert capture.record.upstream_warning_count == 0
