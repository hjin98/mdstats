"""Prepared common atomic-reference state must survive canonical JSON order.

Prepared generations are published as content-addressed canonical JSON with
``sort_keys=True``.  ``CommonAtomicReferenceFit`` serializes its fitted E0
values as a mapping keyed by *string* atomic number, so the persisted key
order is lexical (``"13", "14", "8"``) while the owner's ``element_order`` is
numeric (``8, 13, 14``).  The reader used to rebuild the fitted tuple from the
serialized mapping's iteration order, which mis-bound every fitted value to the
wrong element as soon as the element set mixed key widths, and the owner's own
alignment validation then correctly rejected an otherwise valid artifact.

The repair is a reader repair: fitted references are keyed data whose
authoritative order is ``element_order``.  These tests hold that line from both
sides -- order-only differences must load, semantic corruption must not -- and
exercise the real publication/load path rather than only the owner in isolation.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
import random

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from mdstats.training_data.campaign_prepared_generation import (
    load_prepared_generation_components,
    prepared_generation_root,
    read_prepared_generation_manifest,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)
from mdstats.training_data.target_size_execution.common import (
    CommonAtomicReferenceFit,
)

# --- Gate C: owner-level regression ----------------------------------------

# Numeric and lexical order disagree here: sorted JSON keys are "13", "14", "8".
MIXED_WIDTH_ELEMENTS = (8, 13, 14)
MIXED_WIDTH_REFERENCES = ((8, -4.5), (13, -1.25), (14, -6.75))


def _fit(**overrides) -> CommonAtomicReferenceFit:
    payload = {
        "policy_digest": digest({"fixture": "policy"}),
        "membership_digest": digest({"fixture": "membership"}),
        "element_order": MIXED_WIDTH_ELEMENTS,
        "count_matrix_digest": digest({"fixture": "counts"}),
        "target_energies_digest": digest({"fixture": "targets"}),
        "reference_energies_ev": MIXED_WIDTH_REFERENCES,
        "rank": 3,
        "singular_values_digest": digest({"fixture": "singular"}),
        "residual_rmse_ev": 0.01,
        "residual_mae_ev": 0.008,
        "maximum_absolute_residual_ev": 0.02,
        "rank_deficient": False,
        "transfer_warnings": (),
    }
    payload.update(overrides)
    return CommonAtomicReferenceFit(**payload)


def _canonical_roundtrip(payload: dict) -> dict:
    """Exactly the prepared-generation canonicalization boundary."""

    return json.loads(json.dumps(payload, indent=2, sort_keys=True))


def test_canonical_json_roundtrip_preserves_element_bound_fitted_values():
    """The defect: an in-memory `from_dict(to_dict())` cannot see this bug."""

    fit = _fit()
    encoded = _canonical_roundtrip(fit.to_dict())
    # The canonical bytes really do disagree with the semantic order.
    assert tuple(encoded["reference_energies_ev"]) == ("13", "14", "8")

    loaded = CommonAtomicReferenceFit.from_dict(encoded)

    assert loaded.element_order == MIXED_WIDTH_ELEMENTS
    assert loaded.reference_energies_ev == MIXED_WIDTH_REFERENCES
    assert dict(loaded.reference_energies_ev) == dict(MIXED_WIDTH_REFERENCES)
    assert loaded.content_digest == fit.content_digest
    assert loaded == fit


def test_scrambled_mapping_order_with_a_correct_key_set_is_accepted():
    fit = _fit()
    payload = fit.to_dict()
    references = payload["reference_energies_ev"]
    payload["reference_energies_ev"] = {
        key: references[key] for key in ("14", "8", "13")
    }

    loaded = CommonAtomicReferenceFit.from_dict(payload)

    assert loaded.reference_energies_ev == MIXED_WIDTH_REFERENCES
    assert loaded.content_digest == fit.content_digest


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda refs: refs.pop("13"), id="missing-key"),
        pytest.param(lambda refs: refs.update({"11": -2.0}), id="extra-key"),
        pytest.param(lambda refs: refs.update({"iron": -2.0}), id="malformed-key"),
        pytest.param(lambda refs: refs.update({"8.5": -2.0}), id="non-integral-key"),
    ],
)
def test_corrupt_reference_key_sets_are_still_rejected(mutate):
    payload = _fit().to_dict()
    mutate(payload["reference_energies_ev"])
    payload.pop("content_digest")

    with pytest.raises(TrainingDataSerializationError):
        CommonAtomicReferenceFit.from_dict(payload)


def test_key_normalization_collision_is_rejected_rather_than_silently_merged():
    """`8` and `"08"` normalize to the same element; that is corrupt state."""

    payload = _fit().to_dict()
    payload["reference_energies_ev"] = {"8": -4.5, "08": -9.9, "13": -1.25, "14": -6.75}
    payload.pop("content_digest")

    with pytest.raises(TrainingDataSerializationError):
        CommonAtomicReferenceFit.from_dict(payload)


@pytest.mark.parametrize("value", [[(8, -4.5)], "8", 5, None])
def test_a_non_mapping_reference_payload_is_rejected(value):
    payload = _fit().to_dict()
    payload["reference_energies_ev"] = value
    payload.pop("content_digest")

    with pytest.raises(TrainingDataSerializationError):
        CommonAtomicReferenceFit.from_dict(payload)


def test_a_non_numeric_fitted_value_is_rejected():
    payload = _fit().to_dict()
    payload["reference_energies_ev"]["13"] = "not-a-number"
    payload.pop("content_digest")

    with pytest.raises(TrainingDataSerializationError):
        CommonAtomicReferenceFit.from_dict(payload)


def test_a_non_finite_fitted_value_is_rejected_by_owner_validation():
    payload = _fit().to_dict()
    payload["reference_energies_ev"]["13"] = float("nan")
    payload.pop("content_digest")

    with pytest.raises(TrainingDataInputError):
        CommonAtomicReferenceFit.from_dict(payload)


@pytest.mark.parametrize(
    "element_order",
    [
        pytest.param([14, 13, 8], id="non-increasing"),
        pytest.param([8, 8, 13, 14], id="duplicate"),
        pytest.param([0, 13, 14], id="non-positive"),
    ],
)
def test_invalid_element_orders_are_still_rejected(element_order):
    payload = _fit().to_dict()
    payload["element_order"] = element_order
    payload.pop("content_digest")

    with pytest.raises((TrainingDataInputError, TrainingDataSerializationError)):
        CommonAtomicReferenceFit.from_dict(payload)


@pytest.mark.parametrize(
    "elements",
    [
        pytest.param((1, 8), id="single-width"),
        pytest.param((8, 13, 14), id="mixed-1-2-digit"),
        pytest.param((3, 8, 11, 92), id="mixed-1-2-digit-wide"),
        pytest.param((1, 6, 8, 13, 26, 92), id="six-elements"),
        pytest.param((8, 14, 100, 118), id="mixed-1-2-3-digit"),
    ],
)
def test_every_mapping_iteration_order_binds_the_same_fitted_values(elements):
    """Order of the serialized mapping is representation, never semantics.

    Every reachable key ordering -- canonical lexical, numeric, reversed, and
    an exhaustive or sampled permutation sweep -- must reconstruct exactly one
    element-bound result.
    """

    references = tuple((z, -1.0 - 0.5 * index) for index, z in enumerate(elements))
    fit = _fit(
        element_order=elements,
        reference_energies_ev=references,
        rank=len(elements),
    )
    payload = fit.to_dict()
    keys = tuple(payload["reference_energies_ev"])
    orders = [
        keys,
        tuple(sorted(keys, key=int)),
        tuple(reversed(keys)),
        tuple(sorted(keys, key=int, reverse=True)),
    ]
    if len(keys) <= 4:
        orders.extend(itertools.permutations(keys))
    else:
        rng = random.Random(20260905)
        for _ in range(32):
            shuffled = list(keys)
            rng.shuffle(shuffled)
            orders.append(tuple(shuffled))

    for order in orders:
        candidate = dict(payload)
        candidate["reference_energies_ev"] = {
            key: payload["reference_energies_ev"][key] for key in order
        }
        loaded = CommonAtomicReferenceFit.from_dict(_canonical_roundtrip(candidate))
        assert loaded.element_order == elements
        assert loaded.reference_energies_ev == references
        assert loaded.content_digest == fit.content_digest


def test_reordering_never_masks_a_content_digest_mismatch():
    payload = _canonical_roundtrip(_fit().to_dict())
    payload["content_digest"] = digest({"fixture": "wrong"})

    with pytest.raises(TrainingDataSerializationError):
        CommonAtomicReferenceFit.from_dict(payload)


# --- Gates D and E: the real prepared-generation and runtime paths ----------


def _mixed_width_campaign(tmp_path: Path):
    """A real campaign whose element set mixes atomic-number key widths.

    Al/O gives atomic numbers ``(8, 13)``, whose canonical JSON key order
    (``"13", "8"``) disagrees with the owner's numeric ``element_order``.
    """

    config, _workspace = p4d._fixture_campaign(tmp_path, elements=("Al", "O"))
    assert p4d._run(config, "prepare") == 0
    cfg, paths = cli._load_config(config)
    return config, cfg, paths


def _revision(paths):
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


def test_prepared_generation_roundtrip_preserves_common_atomic_reference_semantics(
    tmp_path: Path,
):
    _config, _cfg, paths = _mixed_width_campaign(tmp_path)
    revision = _revision(paths)
    manifest_digest = revision.state.prepared_manifest_digest
    manifest = read_prepared_generation_manifest(paths, manifest_digest)

    root = prepared_generation_root(paths)
    common_path = root / "objects" / f"{manifest.component_digests['common']}.json"
    published = json.loads(common_path.read_text(encoding="utf-8"))
    published_bytes = common_path.read_bytes()
    # The stored bytes are canonical: lexical key order, numeric element order.
    references = published["fitted_atomic_references"]
    assert tuple(references["element_order"]) == (8, 13)
    assert tuple(references["reference_energies_ev"]) == ("13", "8")

    loaded = load_prepared_generation_components(paths, manifest)
    fit = loaded["common"].fitted_atomic_references

    assert fit.element_order == (8, 13)
    assert tuple(z for z, _ in fit.reference_energies_ev) == (8, 13)
    assert dict(fit.reference_energies_ev) == {
        int(z): float(v) for z, v in references["reference_energies_ev"].items()
    }
    assert fit.content_digest == references["content_digest"]
    assert loaded["common"].content_digest == manifest.common_preparation_digest

    # Loading consumes; it never rewrites or republishes.
    assert common_path.read_bytes() == published_bytes
    assert _revision(paths).state.prepared_manifest_digest == manifest_digest


def test_select_target_size_advances_past_prepared_common_state(
    tmp_path: Path, monkeypatch
):
    config, cfg, paths = _mixed_width_campaign(tmp_path)
    revision = _revision(paths)
    before = revision.state.prepared_manifest_digest
    common_before = revision.state.common_preparation_digest

    from mdstats.training_data import campaign_target_size_runtime as runtime
    from mdstats.training_data.target_size_execution import common as common_module

    refits: list[str] = []
    monkeypatch.setattr(
        common_module,
        "fit_common_atomic_reference_energies",
        lambda *args, **kwargs: refits.append("refit"),
    )

    contexts: list[object] = []
    real_build = runtime.build_screen_context

    def _record(*args, **kwargs):
        context = real_build(*args, **kwargs)
        contexts.append(context)
        return context

    monkeypatch.setattr(runtime, "build_screen_context", _record)

    harness = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )

    # The command advanced beyond prepared common-state loading ...
    assert contexts, "select-target-size never reached build_screen_context"
    # ... on the already prepared common authority, with no refit and no
    # regeneration of the prepared substrate.
    assert refits == []
    after = _revision(paths)
    assert after.state.prepared_manifest_digest == before
    assert after.state.common_preparation_digest == common_before
