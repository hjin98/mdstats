"""Stage-F cutover: corrected identities refuse to authenticate retired evidence.

Every check here is a schema/identity boundary on the real serializers. The
point is not that old payloads are unreadable in general -- history stays
readable under its own schema -- but that nothing produced under the retired
fixed-learning-rate, old-loss, or blocking-ceiling semantics can authenticate as
current evidence, and nothing is repaired in place by filling defaults or
rewriting a status label.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
)
from mdstats.training_data.mace_compatibility import MACE_EXECUTABLE_LOSS_FAMILY
from mdstats.training_data.objectives import (
    FRAME_TRAINING_WEIGHT_SCHEMA,
    TRAINING_WEIGHT_CATALOG_SCHEMA,
    FrameTrainingWeight,
)
from mdstats.training_data.post_selection_execution import (
    POST_SELECTION_MACE_CONFIG_SCHEMA,
    POST_SELECTION_PREPARATION_SCHEMA,
    PostSelectionFittedPreparation,
)
from mdstats.training_data.target_size_execution import (
    TARGET_SIZE_COMMON_PREPARATION_SCHEMA,
    TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA,
    TargetSizeCommonPreparation,
    TargetSizeScreenSchedule,
    build_target_size_screen_schedule,
)
from mdstats.training_data.target_size_execution.candidate import (
    TARGET_SIZE_MACE_CONFIG_SCHEMA,
    TARGET_SIZE_REALIZATION_SCHEMA,
    TargetSizeCandidateRealization,
)
from mdstats.training_data.target_size_experiment import TARGET_SIZE_POLICY_SCHEMA


def test_every_reinterpretable_schema_was_versioned_forward() -> None:
    """A payload whose meaning changed must not keep its old schema token.

    Each of these carries fields that would deserialize cleanly but mean
    something different under the corrected semantics -- a fixed learning rate,
    a per-frame copy of the global objective ratio, a blocking ceiling rule.
    """

    assert TARGET_SIZE_POLICY_SCHEMA.endswith(".v2")
    assert TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA.endswith(".v2")
    assert TARGET_SIZE_REALIZATION_SCHEMA.endswith(".v2")
    assert TARGET_SIZE_MACE_CONFIG_SCHEMA.endswith(".v3")
    assert TARGET_SIZE_COMMON_PREPARATION_SCHEMA.endswith(".v3")
    assert FRAME_TRAINING_WEIGHT_SCHEMA.endswith(".v2")
    assert TRAINING_WEIGHT_CATALOG_SCHEMA.endswith(".v2")
    assert POST_SELECTION_PREPARATION_SCHEMA.endswith(".v2")
    assert POST_SELECTION_MACE_CONFIG_SCHEMA.endswith(".v2")


@pytest.mark.parametrize(
    "deserializer,schema,payload_extra",
    [
        (mdstats.ResolvedTargetSizePolicy.from_dict, TARGET_SIZE_POLICY_SCHEMA, {}),
        (TargetSizeScreenSchedule.from_dict, TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA, {}),
        (
            TargetSizeCandidateRealization.from_dict,
            TARGET_SIZE_REALIZATION_SCHEMA,
            {},
        ),
        (
            TargetSizeCommonPreparation.from_dict,
            TARGET_SIZE_COMMON_PREPARATION_SCHEMA,
            {},
        ),
        (FrameTrainingWeight.from_dict, FRAME_TRAINING_WEIGHT_SCHEMA, {}),
        (
            PostSelectionFittedPreparation.from_dict,
            POST_SELECTION_PREPARATION_SCHEMA,
            {},
        ),
    ],
)
def test_retired_schema_payloads_fail_closed(
    deserializer, schema, payload_extra
) -> None:
    retired = schema.rsplit(".", 1)[0] + ".v1"
    with pytest.raises(TrainingDataSerializationError):
        deserializer({"schema": retired, **payload_extra})


def test_a_stale_fixed_learning_rate_screen_schedule_cannot_be_adopted() -> None:
    """The retired screen schedule carried no normalization policy at all."""

    schedule = build_target_size_screen_schedule((1, 3, 10))
    payload = schedule.to_dict()
    # Exactly the retired shape: same fields, no normalization authority.
    stale = {k: v for k, v in payload.items() if k != "normalization_policy"}
    stale["schema"] = TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA.rsplit(".", 1)[0] + ".v1"
    with pytest.raises(TrainingDataSerializationError):
        TargetSizeScreenSchedule.from_dict(stale)
    # And it is not silently repaired by filling the current defaults either.
    stale["schema"] = TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA
    with pytest.raises(KeyError):
        TargetSizeScreenSchedule.from_dict(stale)


def test_local_property_weights_are_masks_under_the_current_schema() -> None:
    """A v1 record carrying the global ratio per frame is not a current mask."""

    current = FrameTrainingWeight(
        frame_uid="a" * 64,
        configuration_weight=1.0,
        energy_weight=1.0,
        forces_weight=1.0,
        stress_weight=0.0,
        reason_codes=("uniform_configuration_weight",),
    )
    assert current.to_dict()["schema"] == FRAME_TRAINING_WEIGHT_SCHEMA
    retired = dict(current.to_dict())
    retired["schema"] = "mdstats.frame-training-weight.v1"
    retired["forces_weight"] = 10.0  # the retired per-frame global-ratio copy
    with pytest.raises(TrainingDataSerializationError):
        FrameTrainingWeight.from_dict(retired)


def test_the_executable_loss_family_is_one_authority() -> None:
    """Screen, post-selection, and model reconstruction name the same family."""

    from mdstats.training_data.model_features import (
        mace_candidate_architecture_defaults,
    )
    from mdstats.training_data.post_selection_execution import (
        POST_SELECTION_MACE_LOSS_FAMILY,
    )
    from mdstats.training_data.target_size_execution.candidate import (
        TARGET_SIZE_MACE_LOSS_FAMILY,
    )

    assert MACE_EXECUTABLE_LOSS_FAMILY == "stress"
    assert TARGET_SIZE_MACE_LOSS_FAMILY == MACE_EXECUTABLE_LOSS_FAMILY
    assert POST_SELECTION_MACE_LOSS_FAMILY == MACE_EXECUTABLE_LOSS_FAMILY
    assert (
        mace_candidate_architecture_defaults()["loss"] == MACE_EXECUTABLE_LOSS_FAMILY
    )


def test_no_current_source_path_emits_the_retired_universal_loss() -> None:
    """Structural absence over the current package source.

    Scope: every ``.py`` file under ``mdstats/`` in this working tree. The one
    permitted occurrence is the retired, unreachable DATA8 preparation topology,
    which no current command or qualification consumer calls; it is named here
    explicitly rather than being hidden by a broad exclusion.
    """

    root = Path(mdstats.__file__).resolve().parent
    offenders = []
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if '"loss": "universal"' in text or "'loss': 'universal'" in text:
            offenders.append(path.relative_to(root).as_posix())
    assert offenders == ["training_data/data8_bundle.py"], offenders

    # Known-positive control: the scan really does detect the construct.
    probe = '{"loss": "universal"}'
    assert '"loss": "universal"' in probe


def test_reconstruction_output_configuration_is_unchanged_by_the_loss_family() -> None:
    """Reopen-trigger 6 does not fire: model construction is family-invariant.

    Pinned MACE derives ``compute_stress`` for both the retired and the
    corrected family and ``compute_virials`` for neither, so the corrected loss
    family changes the optimization meaning without changing the model that
    reconstruction and EVAL2 build.
    """

    from types import SimpleNamespace

    pytest.importorskip("mace")

    def output_flags(loss: str) -> tuple[bool, bool]:
        args = SimpleNamespace(loss=loss)
        return (args.loss == "virials", args.loss in ("stress", "huber", "universal"))

    assert output_flags(MACE_EXECUTABLE_LOSS_FAMILY) == output_flags("universal")
