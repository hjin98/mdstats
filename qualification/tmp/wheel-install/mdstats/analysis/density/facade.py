"""Canonical Stage-11E0a facade around current density producers.

The functions in this module construct scientific fields only.  They neither
accept nor resolve rendering options, meshes, browser budgets, Plotly traces,
or HTML output.  Numerical ownership remains in the established plotting-era
modules until Stage 11E0b; every result records that compatibility boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ...collection import AtomisticFrameCollection
from ...coordinates.consumer_adapters import ConsumerCoordinateView
from ...progress import ProgressPortLike
from .protocols import (
    SCIENTIFIC_DENSITY_FACADE_STAGE,
    ScientificDensityFieldBundle,
    ScientificDensityInputError,
    adapt_scientific_density_fields,
)
from .resources import (
    ScientificDensityResourcePolicy,
    resolve_scientific_density_resources,
)

FloatArray = NDArray[np.float64]

ATOMIC_DENSITY_NUMERICAL_OWNER = "mdstats.plotting.atomic_density"
FRAMEWORK_DENSITY_NUMERICAL_OWNER = "mdstats.plotting.framework_density"
SCIENTIFIC_DENSITY_OWNER = "mdstats.analysis.density"


def _resource_policy(
    resources: ScientificDensityResourcePolicy | None,
) -> ScientificDensityResourcePolicy:
    return resolve_scientific_density_resources(resources)


def prepare_atomic_density_fields(
    collection: AtomisticFrameCollection,
    *,
    frame_indices: Sequence[int],
    frame_weights: FloatArray,
    display_cell: FloatArray,
    registration_mode: str,
    framework_drift: FloatArray,
    selections: Sequence[Any],
    options: Any,
    registration_view: ConsumerCoordinateView | None = None,
    resources: ScientificDensityResourcePolicy | None = None,
    planning_metadata_by_field: Mapping[str, Mapping[str, Any]] | None = None,
    progress: ProgressPortLike | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> ScientificDensityFieldBundle:
    """Prepare atomic scientific fields through the canonical analysis facade.

    ``selections`` and ``options`` are the existing compatible
    ``AtomicDensitySelection`` and ``AtomicDensityOptions`` objects.  They are
    intentionally accepted without importing rendering classes into this
    module.  Stage 11E0b will move their numerical contracts.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be AtomisticFrameCollection.")
    if not selections:
        raise ScientificDensityInputError(
            "At least one atomic density selection is required."
        )
    policy = _resource_policy(resources)

    # Lazy compatibility import: the analysis facade itself remains independent
    # of all plotting/rendering APIs.
    from ...plotting.atomic_density import (
        AtomicDensityOptions,
        AtomicDensitySelection,
        prepare_atomic_density_fields as _prepare_legacy_atomic_density_fields,
    )

    if not isinstance(options, AtomicDensityOptions):
        raise TypeError("options must be AtomicDensityOptions.")
    if any(not isinstance(item, AtomicDensitySelection) for item in selections):
        raise TypeError("selections must contain AtomicDensitySelection objects.")

    legacy_fields = _prepare_legacy_atomic_density_fields(
        collection,
        frame_indices=frame_indices,
        frame_weights=np.asarray(frame_weights, dtype=np.float64),
        display_cell=np.asarray(display_cell, dtype=np.float64),
        registration_mode=str(registration_mode),
        framework_drift=np.asarray(framework_drift, dtype=np.float64),
        registration_view=registration_view,
        selections=selections,
        options=options,
        planning_metadata_by_field=planning_metadata_by_field,
        progress=progress,
        progress_callback=progress_callback,
        **policy.to_legacy_keyword_arguments(),
    )
    return adapt_scientific_density_fields(
        legacy_fields,
        source_kind="atomic_occupancy",
        numerical_owner=ATOMIC_DENSITY_NUMERICAL_OWNER,
        resource_signature=policy.signature,
        metadata={
            "facade_stage": SCIENTIFIC_DENSITY_FACADE_STAGE,
            "scientific_owner": SCIENTIFIC_DENSITY_OWNER,
            "numerical_owner": ATOMIC_DENSITY_NUMERICAL_OWNER,
            "rendering_policy_consumed": False,
            "mesh_constructed": False,
            "browser_budget_consumed": False,
            "registration_mode": str(registration_mode),
            "field_count": len(legacy_fields),
        },
    )


def prepare_framework_density_fields(
    *,
    vertex_fractional_by_frame: FloatArray,
    vertex_atom_indices: tuple[int, ...],
    edge_segments_fractional_by_frame: FloatArray,
    edge_atom_indices: tuple[int, ...],
    frame_weights: FloatArray,
    display_cell: FloatArray,
    registration_mode: str,
    options: Any,
    consumer_registration_signature: str | None = None,
    scientific_drift_owner: str | None = None,
    resources: ScientificDensityResourcePolicy | None = None,
    planning_metadata_by_field: Mapping[str, Mapping[str, Any]] | None = None,
    vertex_source_keys: tuple[Any, ...] | None = None,
    edge_source_keys: tuple[Any, ...] | None = None,
    progress: ProgressPortLike | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> ScientificDensityFieldBundle:
    """Prepare framework vertex/edge scientific fields without rendering."""

    policy = _resource_policy(resources)
    from ...plotting.framework_density import (
        FrameworkDensityOptions,
        prepare_framework_density_fields as _prepare_legacy_framework_density_fields,
    )

    if not isinstance(options, FrameworkDensityOptions):
        raise TypeError("options must be FrameworkDensityOptions.")

    legacy_container = _prepare_legacy_framework_density_fields(
        vertex_fractional_by_frame=np.asarray(
            vertex_fractional_by_frame, dtype=np.float64
        ),
        vertex_atom_indices=tuple(int(value) for value in vertex_atom_indices),
        edge_segments_fractional_by_frame=np.asarray(
            edge_segments_fractional_by_frame, dtype=np.float64
        ),
        edge_atom_indices=tuple(int(value) for value in edge_atom_indices),
        frame_weights=np.asarray(frame_weights, dtype=np.float64),
        display_cell=np.asarray(display_cell, dtype=np.float64),
        registration_mode=str(registration_mode),
        options=options,
        consumer_registration_signature=consumer_registration_signature,
        scientific_drift_owner=scientific_drift_owner,
        planning_metadata_by_field=planning_metadata_by_field,
        vertex_source_keys=vertex_source_keys,
        edge_source_keys=edge_source_keys,
        progress=progress,
        progress_callback=progress_callback,
        **policy.to_legacy_keyword_arguments(),
    )
    return adapt_scientific_density_fields(
        legacy_container.fields,
        source_kind="framework_geometry",
        numerical_owner=FRAMEWORK_DENSITY_NUMERICAL_OWNER,
        resource_signature=policy.signature,
        metadata={
            "facade_stage": SCIENTIFIC_DENSITY_FACADE_STAGE,
            "scientific_owner": SCIENTIFIC_DENSITY_OWNER,
            "numerical_owner": FRAMEWORK_DENSITY_NUMERICAL_OWNER,
            "rendering_policy_consumed": False,
            "mesh_constructed": False,
            "browser_budget_consumed": False,
            "registration_mode": str(registration_mode),
            "edge_source": legacy_container.edge_source,
            "legacy_container_metadata": (
                legacy_container.metadata.to_json_dict()
                if callable(
                    getattr(legacy_container.metadata, "to_json_dict", None)
                )
                else dict(legacy_container.metadata)
            ),
            "field_count": len(legacy_container.fields),
        },
    )


__all__ = [
    "ATOMIC_DENSITY_NUMERICAL_OWNER",
    "FRAMEWORK_DENSITY_NUMERICAL_OWNER",
    "SCIENTIFIC_DENSITY_OWNER",
    "prepare_atomic_density_fields",
    "prepare_framework_density_fields",
]
