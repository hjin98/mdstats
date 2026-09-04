"""Parser-boundary evidence for the mdstats -> pinned MACE executable config.

mdstats keeps candidate and post-selection configuration as typed JSON-safe
scientific data.  Pinned MACE 0.3.16 declares ``atomic_numbers``, ``E0s``,
``radial_MLP`` and ``heads`` as scalar ``type=str`` configargparse actions and
interprets the string itself with :func:`ast.literal_eval`.  These tests drive
the **real** projection owners and the **real** pinned parser: a dictionary
shape assertion alone cannot prove the boundary works.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data.campaign_target_size_runtime import (
    MaceTargetSizeBoundaryTrainer,
    mace_run_configuration,
)
from mdstats.training_data.mace_compatibility import (
    MACE_ARCHITECTURE_EXTERNAL_KEYS,
    MACE_ARCHITECTURE_INTERNAL_KEYS,
    project_mace_architecture_arguments,
)
from mdstats.training_data.model_features import (
    canonicalize_mace_candidate_architecture,
    mace_candidate_architecture_defaults,
)
from mdstats.training_data.post_selection_execution import (
    POST_SELECTION_MACE_CONFIG_SCHEMA,
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    post_selection_mace_run_configuration,
)
from mdstats.training_data.target_size_execution import (
    TARGET_SIZE_MACE_CONFIG_SCHEMA,
)

_TRAINING_DATA = Path(__file__).resolve().parents[1] / "mdstats" / "training_data"

# The exact atomic numbers of the production LTA campaign whose Boundary-1
# TRAIN2 launch exited 2 in configargparse.
PRODUCTION_ATOMIC_NUMBERS = [3, 8, 11, 13, 14, 19]
PRODUCTION_E0S = {
    "3": -0.29631546,
    "8": -1.90731404,
    "11": -0.24327911,
    "13": -0.21942875,
    "14": -0.87083412,
    "19": -0.18804199,
}


def _parser():
    from mace.tools import build_default_arg_parser

    return build_default_arg_parser()


def _parser_option_names() -> set[str]:
    names: set[str] = set()
    for action in _parser()._actions:
        for option in action.option_strings:
            names.add(option.lstrip("-"))
    return names


def _parse_config(tmp_path: Path, config, *, name: str = "mace_run_config.yaml"):
    """Feed a generated executable config to the exact pinned MACE parser."""

    path = tmp_path / name
    path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
    return _parser().parse_args(["--config", str(path)])


def _canonical_target_size_config() -> dict:
    return {
        "schema": TARGET_SIZE_MACE_CONFIG_SCHEMA,
        "name": "target-size-n128-seed1",
        "seed": 1,
        "target_train_file": "target_train.extxyz",
        "target_valid_file": "harness_validation.extxyz",
        "atomic_numbers": sorted(PRODUCTION_ATOMIC_NUMBERS),
        "E0s": dict(PRODUCTION_E0S),
        "energy_key": "REF_energy",
        "forces_key": "REF_forces",
        "stress_key": "REF_stress",
        "lr": 0.01,
        "batch_size": 4,
        "valid_batch_size": 4,
        "num_workers": 0,
        "max_num_epochs": 1,
        "ema": True,
        "ema_decay": 0.99,
        "amsgrad": True,
        "weight_decay": 5.0e-07,
        "clip_grad": 10.0,
        "default_dtype": "float64",
        "device": "cpu",
        "foundation_model": None,
        "foundation_head": None,
        "multiheads_finetuning": False,
        "mace_architecture": canonicalize_mace_candidate_architecture(
            mace_candidate_architecture_defaults()
        ),
    }


def _canonical_post_selection_config(*, multihead: bool) -> dict:
    architecture = canonicalize_mace_candidate_architecture(
        mace_candidate_architecture_defaults()
    )
    config: dict = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "post-selection-fixture",
        "seed": 1,
        "target_train_file": "target-train.extxyz",
        "target_valid_file": "target-valid.extxyz",
        "atomic_numbers": sorted(PRODUCTION_ATOMIC_NUMBERS),
        "E0s": dict(PRODUCTION_E0S),
        "energy_key": "REF_energy",
        "forces_key": "REF_forces",
        "stress_key": "REF_stress",
        "lr": 0.01,
        "batch_size": 4,
        "valid_batch_size": 4,
        "num_workers": 0,
        "max_num_epochs": 1,
        "ema": True,
        "ema_decay": 0.99,
        "amsgrad": True,
        "weight_decay": 5.0e-07,
        "clip_grad": 10.0,
        "default_dtype": "float64",
        "device": "cpu",
        "target_head_name": POST_SELECTION_TARGET_HEAD_NAME,
        "replay_head_name": POST_SELECTION_REPLAY_HEAD_NAME,
        "mace_architecture": architecture,
    }
    if multihead:
        config["foundation_model"] = "foundation.model"
        config["multiheads_finetuning"] = True
        config["pt_train_file"] = "replay-train.extxyz"
        config["pt_valid_file"] = "replay-monitor.extxyz"
        config["heads"] = {
            POST_SELECTION_TARGET_HEAD_NAME: {
                "train_file": "target-train.extxyz",
                "valid_file": "target-valid.extxyz",
                "atomic_numbers": sorted(PRODUCTION_ATOMIC_NUMBERS),
                "E0s": dict(PRODUCTION_E0S),
                "energy_key": "REF_energy",
                "forces_key": "REF_forces",
                "stress_key": "REF_stress",
            },
            POST_SELECTION_REPLAY_HEAD_NAME: {
                "energy_key": "REF_energy",
                "forces_key": "REF_forces",
                "stress_key": "REF_stress",
            },
        }
    return config


# --- C1: exact target-size parser reproducer -------------------------------


def test_c1_production_candidate_config_is_accepted_by_the_pinned_parser(
    tmp_path: Path,
) -> None:
    """The exact configuration whose TRAIN2 launch exited 2 now parses."""

    source = _canonical_target_size_config()
    config = mace_run_configuration(source)

    args = _parse_config(tmp_path, config)

    # MACE reads each of these with ast.literal_eval; the logical value must
    # survive the external spelling exactly.
    assert ast.literal_eval(args.atomic_numbers) == sorted(PRODUCTION_ATOMIC_NUMBERS)
    assert ast.literal_eval(args.E0s) == {
        int(z): value for z, value in PRODUCTION_E0S.items()
    }
    assert ast.literal_eval(args.radial_MLP) == source["mace_architecture"]["radial_MLP"]
    # Internal metadata never crosses the boundary.
    assert "schema" not in config
    # Scratch target-size execution must not inherit MACE dataset heads from the
    # internal architecture head list.
    assert "heads" not in config
    assert args.heads is None
    # A canonical ``None`` means "no override": the parser default stands.
    assert "distance_transform" not in config
    assert args.distance_transform == "None"
    assert "embedding_specs" not in config
    assert args.embedding_specs is None
    # Every emitted key is a real MACE option.
    assert set(config) <= _parser_option_names()


def test_c1_projection_leaves_the_canonical_configuration_untouched() -> None:
    """Only the derived executable text changes; canonical identity does not."""

    source = _canonical_target_size_config()
    before = json.dumps(source, sort_keys=True)
    before_digest = mdstats.training_data._common.digest(source)

    mace_run_configuration(source)

    assert json.dumps(source, sort_keys=True) == before
    assert mdstats.training_data._common.digest(source) == before_digest
    assert source["atomic_numbers"] == sorted(PRODUCTION_ATOMIC_NUMBERS)
    assert source["E0s"] == PRODUCTION_E0S
    assert isinstance(source["mace_architecture"]["radial_MLP"], list)


# --- C2: P5 non-multihead parser regression --------------------------------


@pytest.mark.parametrize("foundation", [None, "foundation.model"])
def test_c2_post_selection_non_multihead_config_parses(
    tmp_path: Path, foundation
) -> None:
    """Scratch and naive-fine-tuning post-selection runs reach the parser."""

    source = _canonical_post_selection_config(multihead=False)
    if foundation is not None:
        source["foundation_model"] = foundation
    config = post_selection_mace_run_configuration(source)

    args = _parse_config(tmp_path, config)

    assert ast.literal_eval(args.atomic_numbers) == sorted(PRODUCTION_ATOMIC_NUMBERS)
    assert ast.literal_eval(args.E0s) == {
        int(z): value for z, value in PRODUCTION_E0S.items()
    }
    assert ast.literal_eval(args.radial_MLP) == source["mace_architecture"]["radial_MLP"]
    # The internal architecture head list never becomes MACE's --heads.
    assert "heads" not in config
    assert args.heads is None
    assert "schema" not in config
    assert set(config) <= _parser_option_names()
    if foundation is None:
        assert "foundation_model" not in config
    else:
        assert config["foundation_model"] == foundation
        assert args.foundation_model == foundation


# --- C3: P5 multihead parser regression ------------------------------------


def test_c3_post_selection_multihead_heads_literal_round_trips(
    tmp_path: Path,
) -> None:
    """``--heads`` is one scalar dictionary literal MACE itself can read."""

    source = _canonical_post_selection_config(multihead=True)
    config = post_selection_mace_run_configuration(source)

    args = _parse_config(tmp_path, config)

    assert isinstance(config["heads"], str)
    heads = ast.literal_eval(args.heads)
    assert set(heads) == {
        POST_SELECTION_TARGET_HEAD_NAME,
        POST_SELECTION_REPLAY_HEAD_NAME,
    }
    target = heads[POST_SELECTION_TARGET_HEAD_NAME]
    # MACE consumes nested head atomic_numbers/E0s exactly as it consumes the
    # top-level ones, so they are scalar literals too.
    assert ast.literal_eval(target["atomic_numbers"]) == sorted(
        PRODUCTION_ATOMIC_NUMBERS
    )
    assert ast.literal_eval(target["E0s"]) == {
        int(z): value for z, value in PRODUCTION_E0S.items()
    }
    assert target["train_file"] == "target-train.extxyz"
    assert target["valid_file"] == "target-valid.extxyz"
    assert heads[POST_SELECTION_REPLAY_HEAD_NAME]["energy_key"] == "REF_energy"
    # Replay paths and the canonical head namespace are unchanged.
    assert args.pt_train_file == "replay-train.extxyz"
    assert args.pt_valid_file == "replay-monitor.extxyz"
    assert set(config) <= _parser_option_names()
    # The internal architecture head list cannot merge into the dataset heads.
    assert POST_SELECTION_TARGET_HEAD_NAME in heads
    assert "target_head" not in source["mace_architecture"]["heads"] or heads[
        POST_SELECTION_TARGET_HEAD_NAME
    ] is not source["mace_architecture"]["heads"]
    assert source["heads"][POST_SELECTION_TARGET_HEAD_NAME]["E0s"] == PRODUCTION_E0S


# --- C4: production trainer subprocess seam --------------------------------


_PARSER_PROBE_WRAPPER = '''#!{python}
import json
import sys
from pathlib import Path

sys.path.insert(0, {source_root!r})

import argparse

probe = argparse.ArgumentParser(add_help=False)
probe.add_argument("--config", required=True)
probe.add_argument("--model_dir", required=True)
probe.add_argument("--checkpoints_dir", required=True)
probe.add_argument("--log_dir", required=True)
probe.add_argument("--results_dir", required=True)
probe.add_argument("--restart_latest", action="store_true")
known, _rest = probe.parse_known_args()

# The real pinned MACE parser is the compatibility authority for the config.
from mace.tools import build_default_arg_parser

args = build_default_arg_parser().parse_args(["--config", known.config])
Path({record!r}).write_text(
    json.dumps(
        {{
            "cwd": str(Path.cwd()),
            "config": known.config,
            "atomic_numbers": args.atomic_numbers,
            "E0s": args.E0s,
            "radial_MLP": args.radial_MLP,
            "heads": args.heads,
            "name": args.name,
            "seed": args.seed,
            "max_num_epochs": args.max_num_epochs,
        }},
        sort_keys=True,
    ),
    encoding="utf-8",
)
raise SystemExit(0)
'''


def test_c4_production_trainer_config_reaches_the_real_parser(tmp_path: Path) -> None:
    """The real trainer's config emission, argv and cwd cross the real parser.

    Only MACE's numerical training is substituted; the projection, the written
    ``--config`` file, the subprocess argv/cwd, and the dependency parser are
    all production behaviour.
    """

    materialization_dir = tmp_path / "candidate"
    materialization_dir.mkdir()
    (materialization_dir / "mace_config.json").write_text(
        json.dumps(_canonical_target_size_config(), sort_keys=True), encoding="utf-8"
    )
    record = tmp_path / "parsed.json"
    wrapper = tmp_path / "mdstats-mace-train"
    wrapper.write_text(
        _PARSER_PROBE_WRAPPER.format(
            python=sys.executable,
            source_root=str(Path(mdstats.__file__).resolve().parents[1]),
            record=str(record),
        ),
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    checkpoint_dir = tmp_path / "run" / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    request = SimpleNamespace(
        plan=SimpleNamespace(
            to_dict=lambda: {"schema": "probe"}, execution_epoch_limit=1
        ),
        trajectory=SimpleNamespace(optimizer_seed=1, target_size=128),
        materialization=SimpleNamespace(mace_config_relative_path="mace_config.json"),
        materialization_directory=materialization_dir,
        checkpoint_directory=checkpoint_dir,
        start_epoch=0,
        optimizer_policy=None,
    )
    trainer = MaceTargetSizeBoundaryTrainer(wrapper_path=wrapper)

    # The trainer returns the TRAIN2 summary, which this bounded program does
    # not write; the parser boundary is what is under test here.
    with pytest.raises(Exception):
        trainer(request)

    assert record.is_file(), "the wrapper never reached the pinned MACE parser"
    parsed = json.loads(record.read_text(encoding="utf-8"))
    assert parsed["cwd"] == str(materialization_dir)
    assert ast.literal_eval(parsed["atomic_numbers"]) == sorted(
        PRODUCTION_ATOMIC_NUMBERS
    )
    assert ast.literal_eval(parsed["E0s"]) == {
        int(z): value for z, value in PRODUCTION_E0S.items()
    }
    assert ast.literal_eval(parsed["radial_MLP"]) == [64, 64, 64]
    assert parsed["heads"] is None
    assert parsed["seed"] == 1
    # The generated config file remains next to the run root, as before.
    written = json.loads(
        (checkpoint_dir.parent / "mace_run_config.yaml").read_text(encoding="utf-8")
    )
    assert "schema" not in written
    assert "heads" not in written


# --- structural / negative acceptance --------------------------------------


def test_architecture_projection_is_explicit_and_fails_on_unknown_fields() -> None:
    architecture = canonicalize_mace_candidate_architecture(
        mace_candidate_architecture_defaults()
    )
    projected = project_mace_architecture_arguments(architecture)

    assert MACE_ARCHITECTURE_INTERNAL_KEYS == {"schema", "heads"}
    assert not (MACE_ARCHITECTURE_EXTERNAL_KEYS & MACE_ARCHITECTURE_INTERNAL_KEYS)
    assert set(projected) <= MACE_ARCHITECTURE_EXTERNAL_KEYS
    assert set(projected) <= _parser_option_names()
    # A field with no declared projection is a boundary failure, never a leak.
    with pytest.raises(mdstats.TrainingDataInputError):
        project_mace_architecture_arguments({**architecture, "future_knob": 1})


def test_no_production_config_writer_bypasses_the_projection_owners() -> None:
    """Every production ``mace_run_config`` writer goes through a projection."""

    import ast as _ast

    writers: list[tuple[str, str]] = []
    for path in sorted(_TRAINING_DATA.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "mace_run_config" not in text:
            continue
        tree = _ast.parse(text)
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.FunctionDef):
                continue
            body = _ast.get_source_segment(text, node) or ""
            if "mace_run_config" not in body:
                continue
            writers.append((path.name, node.name))
            assert (
                "mace_run_configuration(" in body
            ), f"{path.name}:{node.name} writes a MACE config without the projection"
    assert writers, "no production MACE config writer was found"


def test_projection_owners_do_not_retry_or_fall_back() -> None:
    """No owner catches a parser/spelling failure and retries a second config.

    The repair is a corrected projection, not a compatibility path: neither the
    projection functions nor the production trainers may rebuild a MACE run
    configuration from inside an exception handler.
    """

    import ast as _ast

    projections = {
        "campaign_target_size_runtime.py": "mace_run_configuration",
        "post_selection_execution.py": "post_selection_mace_run_configuration",
    }
    trainers = {
        "campaign_target_size_runtime.py": "MaceTargetSizeBoundaryTrainer",
        "post_selection_execution.py": "MacePostSelectionTrainer",
    }
    for name, function_name in projections.items():
        text = (_TRAINING_DATA / name).read_text(encoding="utf-8")
        tree = _ast.parse(text)
        function = next(
            node
            for node in _ast.walk(tree)
            if isinstance(node, _ast.FunctionDef) and node.name == function_name
        )
        calls = [
            node.func.id
            for node in _ast.walk(function)
            if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name)
        ]
        # Exactly one external spelling is produced, by the one shared owner.
        assert calls.count("encode_mace_executable_configuration") == 1
        assert calls.count("project_mace_architecture_arguments") == 1
        assert function_name not in calls
        for handler in (
            node
            for node in _ast.walk(function)
            if isinstance(node, _ast.ExceptHandler)
        ):
            handler_calls = {
                node.func.id
                for node in _ast.walk(handler)
                if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Name)
            }
            assert not handler_calls & {
                "encode_mace_executable_configuration",
                "project_mace_architecture_arguments",
                function_name,
            }
        # No second, hand-maintained spelling of the same options.
        trainer = next(
            node
            for node in _ast.walk(tree)
            if isinstance(node, _ast.ClassDef) and node.name == trainers[name]
        )
        for handler in (
            node
            for node in _ast.walk(trainer)
            if isinstance(node, _ast.ExceptHandler)
        ):
            source = _ast.get_source_segment(text, handler) or ""
            assert function_name not in source
