"""Bounded synthetic selector-evidence fixtures for target-order owner tests.

The fixtures construct real P2 population/split records and duck-typed raw and
universal-structural catalogs with controlled geometry.  They supply *inputs*
to the real target-order owners; no production builder is imported to compute
expected values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Sequence

import numpy as np

from mdstats.training_data._common import digest
from mdstats.training_data.target_size_experiment import (
    TargetSizePopulation,
    TargetSizePopulationFrame,
    TargetSizePopulationSplit,
)


def uid(tag: str) -> str:
    return digest({"fixture-frame": tag})


@dataclass
class _RawCatalog:
    records: dict[str, Any]
    content_digest: str

    def for_frame(self, frame_uid: str) -> Any:
        return self.records[frame_uid]

    @property
    def _by_frame_uid(self) -> dict[str, Any]:
        return self.records


@dataclass
class _StructuralCatalog:
    frame_descriptor_table: Any
    provider_identity: Any
    events: tuple[Any, ...]
    content_digest: str


@dataclass
class SelectorFixture:
    population: TargetSizePopulation
    split: TargetSizePopulationSplit
    raw_features: _RawCatalog
    structural_catalog: _StructuralCatalog
    training_uids: tuple[str, ...]
    units_by_uid: dict[str, str] = field(default_factory=dict)


def build_selector_fixture(
    *,
    frames: int = 48,
    units: int = 6,
    conditions: int = 2,
    seed: int = 7,
    structural_dim: int = 3,
    event_frames: Sequence[int] = (3, 17),
    duplicate_pairs: Sequence[tuple[int, int]] = (),
    pair_rules: int = 1,
) -> SelectorFixture:
    """A small exact-P_train fixture with structural, pair and label evidence."""

    rng = np.random.default_rng(seed)
    uids = tuple(sorted(uid(f"{seed}:{index}") for index in range(frames)))
    unit_ids = tuple(digest({"fixture-unit": f"{seed}:{k}"}) for k in range(units))
    unit_of = {frame_uid: unit_ids[index * units // frames] for index, frame_uid in enumerate(uids)}
    condition_ids = tuple(digest({"fixture-condition": f"{seed}:{k}"}) for k in range(conditions))
    condition_of = {frame_uid: condition_ids[index % conditions] for index, frame_uid in enumerate(uids)}
    population = TargetSizePopulation(
        dataset_id="target-order-fixture",
        frame_authority_digest=digest({"fixture": "authority", "seed": seed}),
        neutral_statistical_base_digest=digest({"fixture": "base", "seed": seed}),
        neutral_unit_catalog_digest=digest({"fixture": "units", "seed": seed}),
        frames=tuple(
            TargetSizePopulationFrame(
                frame_uid=frame_uid,
                unit_id=unit_of[frame_uid],
                condition_id=condition_of[frame_uid],
                geometry_fingerprint=digest({"geometry": frame_uid}),
                canonical_label_payload_digest=digest({"labels": frame_uid}),
                frame_record_digest=digest({"record": frame_uid}),
                condition_attributes=(
                    ("condition_id", condition_of[frame_uid]),
                    ("reduced_formula", "LiO" if index % 2 else "Li2O"),
                    ("regime", "production"),
                    ("strain_class", "unstrained"),
                    ("temperature_condition", "300K"),
                ),
            )
            for index, frame_uid in enumerate(uids)
        ),
    )
    split = TargetSizePopulationSplit(
        population_digest=population.content_digest,
        policy_digest=digest({"fixture": "policy"}),
        split_exclusion_evidence_digest=digest({"fixture": "exclusion"}),
        training_frame_uids=uids,
        evaluation_reserve_frame_uids=(),
        constraint_component_digests=(),
        allocation_diagnostics=(),
    )
    coordinates = rng.normal(size=(frames, 2))
    for left, right in duplicate_pairs:
        coordinates[right] = coordinates[left]
    pair_rule_count = max(1, int(pair_rules))
    records: dict[str, Any] = {}
    for index, frame_uid in enumerate(uids):
        x, y = coordinates[index]
        pairs = tuple(
            SimpleNamespace(
                rule_id=(
                    "Li-O"
                    if pair_rule_count == 1
                    else f"Li-O-{rule_index:03d}"
                ),
                minimum_pair_distance_angstrom=1.8 + 0.1 * x,
                mean_nearest_neighbor_distance_angstrom=2.0 + 0.1 * y,
                maximum_nearest_neighbor_distance_angstrom=2.4 + 0.05 * (x + y),
                coordination_mean=4.0 + 0.3 * y,
                coordination_maximum=6.0 + np.floor(abs(x)),
            )
            for rule_index in range(pair_rule_count)
        )
        records[frame_uid] = SimpleNamespace(
            pair_geometry_statistics=pairs,
            force_component_rms_ev_per_angstrom=0.5 + 0.2 * abs(x),
            force_norm_mean_ev_per_angstrom=0.8 + 0.2 * abs(y),
            force_norm_max_ev_per_angstrom=2.0 + 0.5 * abs(x - y),
            force_norm_quantiles_ev_per_angstrom=(("q50", 0.7 + 0.1 * abs(x)),),
            energy_per_atom_ev=-4.0 + 0.01 * x,
            instantaneous_temperature_kelvin=300.0 + 10.0 * y,
            hydrostatic_strain=None,
            deviatoric_strain_norm=None,
            pressure_ev_per_angstrom3=0.001 * (x + y),
            stress_deviatoric_norm_ev_per_angstrom3=None,
        )
    raw = _RawCatalog(records=records, content_digest=digest({"fixture-raw": seed, "frames": frames}))
    feature_names: list[str] = []
    columns: list[np.ndarray] = []
    for base in ("nearest_neighbor_distance_angstrom", "smooth_coordination", "local_number_density_angstrom^-3"):
        for stat in ("mean", "std")[: max(1, min(2, structural_dim - 1))]:
            feature_names.append(f"group:Li:{base}:{stat}")
            columns.append(coordinates[:, len(columns) % 2] * (1.0 + 0.25 * len(columns)))
    table = SimpleNamespace(
        frame_uids=uids,
        feature_names=tuple(feature_names),
        values=np.stack(columns, axis=1),
        missing_mask=np.zeros((frames, len(feature_names)), dtype=bool),
    )
    events = tuple(
        SimpleNamespace(event_type="coordination_change", current_frame_uid=uids[index]) for index in event_frames
    )
    structural = _StructuralCatalog(
        frame_descriptor_table=table,
        provider_identity=SimpleNamespace(content_digest=digest({"fixture-provider": "universal"})),
        events=events,
        content_digest=digest({"fixture-structural": seed, "frames": frames}),
    )
    return SelectorFixture(
        population=population,
        split=split,
        raw_features=raw,
        structural_catalog=structural,
        training_uids=uids,
        units_by_uid=unit_of,
    )
