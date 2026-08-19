"""Exact action of validated PeriodicNetView automorphisms on primitive rings.

This module validates an explicitly supplied periodic multigraph action against
one immutable :class:`~mdstats.analysis.PeriodicNetView`.  The action must
preserve the view's declared vertex and edge signatures as well as exact periodic
incidence.  It can then be applied to lifted vertices, physical edge instances,
and translated primitive-ring occurrences.

The module does *not* discover symmetry or assemble an automorphism group.
Automatic discovery, representative gauge normalization, composition tables,
and orbit/stabilizer catalogs remain responsibilities of the later
``net_symmetry.py`` stage.

Periodic quotient edges and integer image shifts follow the labelled finite-graph
(vector) representation of Chung, Hahn, and Klee (1984).  Exact combinatorial
periodic-net automorphisms follow Delgado-Friedrichs and O'Keeffe (2003).
mdstats adds view-signature enforcement, explicit multiedge action, source-safe
ring placement, and occurrence-level primitive-ring alignment.

References
----------
S. J. Chung, Th. Hahn, and W. E. Klee, "Nomenclature and generation of
three-periodic nets: the vector method", Acta Cryst. A 40, 42-50 (1984),
doi:10.1107/S0108767384000088.
O. Delgado-Friedrichs and M. O'Keeffe, "Identification of and symmetry
computation for crystal nets", Acta Cryst. A 59, 351-360 (2003),
doi:10.1107/S0108767303012017.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from numbers import Integral
from typing import Any, Literal, Mapping, Sequence

from ._periodic_graph import (
    add_shift,
    coerce_int_matrix3,
    determinant3,
    matvec_shift,
    subtract_shift,
)
from .periodic_cycle import CycleParameterization, RingPlacement
from .periodic_net_view import PeriodicNetView
from .primitive_ring import (
    LatticeShift,
    LiftedVertexRef,
    PrimitiveRingEdgeToken,
    PrimitiveRingKey,
    PrimitiveRingStep,
    canonicalize_primitive_ring_tokens,
)
from .primitive_ring_index import LiftedEdgeInstanceRef, PrimitiveRingIndex


class PeriodicRingActionError(ValueError):
    """Base exception for validated periodic actions and ring occurrence maps."""


class PeriodicRingActionInputError(PeriodicRingActionError):
    """Raised when an action input is malformed or source/view-mismatched."""


class PeriodicRingActionValidationError(PeriodicRingActionError):
    """Raised when a proposed action violates view signatures or graph incidence."""


class RingOccurrenceMappingError(PeriodicRingActionError):
    """Raised when a validated action cannot map a represented ring exactly."""


def _coerce_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise PeriodicRingActionInputError(f"{name} must be an integer.")
    return int(value)


def _nonnegative_int(value: Any, *, name: str) -> int:
    result = _coerce_int(value, name=name)
    if result < 0:
        raise PeriodicRingActionInputError(f"{name} must be nonnegative.")
    return result


def _matrix_preserves_pbc_subspace(
    matrix: tuple[tuple[int, int, int], ...],
    pbc: tuple[bool, bool, bool],
) -> bool:
    """Return whether active lattice translations remain in active PBC axes.

    A lifted image shift has zero coordinates on nonperiodic axes.  Therefore the
    columns of ``matrix`` associated with periodic axes must have zero entries on
    nonperiodic rows.  Together with full integer unimodularity this makes the
    active translation sublattice invariant and bijective.
    """

    active = tuple(axis for axis, periodic in enumerate(pbc) if periodic)
    inactive = tuple(axis for axis, periodic in enumerate(pbc) if not periodic)
    return all(matrix[row][column] == 0 for row in inactive for column in active)


@dataclass(frozen=True, order=True, slots=True)
class PeriodicEdgeImage:
    """Image of one source net-view edge position under a periodic action.

    ``target_edge_index`` is a **position in the owning PeriodicNetView edge
    sequence**, not a primitive-ring catalog-local edge index.  The view digest on
    :class:`ValidatedPeriodicAutomorphism` makes that dense position source-safe.

    ``orientation`` describes the image of the source edge in canonical ``+1``
    traversal: ``+1`` means target canonical orientation and ``-1`` target reverse
    orientation.  Explicit edge action is required because parallel edge orbits
    cannot be distinguished from vertex action alone.
    """

    target_edge_index: int
    orientation: Literal[-1, 1]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_edge_index",
            _nonnegative_int(self.target_edge_index, name="target_edge_index"),
        )
        if self.orientation not in (-1, 1):
            raise PeriodicRingActionInputError("orientation must be +1 or -1.")

    @property
    def target_edge_position(self) -> int:
        """Alias emphasizing that the dense value belongs to a net view."""

        return self.target_edge_index


@dataclass(frozen=True, slots=True)
class ValidatedPeriodicAutomorphism:
    """Exact periodic multigraph automorphism validated for one net view.

    The representative acts on lifted quotient vertices as

    ``(i, n) -> (pi(i), A n + tau_i)``.

    The record is bound to both the source framework graph and one exact
    ``PeriodicNetView.digest``.  Thus an action validated under an unlabeled view
    cannot be silently reused under a chemically decorated view of the same
    topology.
    """

    periodic_net_view_digest: str
    topology_graph_digest: str
    lattice_matrix: tuple[tuple[int, int, int], ...]
    vertex_atom_indices: tuple[int, ...]
    vertex_images: tuple[LiftedVertexRef, ...]
    edge_images: tuple[PeriodicEdgeImage, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.periodic_net_view_digest, str)
            or len(self.periodic_net_view_digest) != 64
        ):
            raise PeriodicRingActionInputError(
                "periodic_net_view_digest must be a SHA-256 digest."
            )
        if (
            not isinstance(self.topology_graph_digest, str)
            or len(self.topology_graph_digest) != 64
        ):
            raise PeriodicRingActionInputError(
                "topology_graph_digest must be a SHA-256 digest."
            )
        try:
            matrix = coerce_int_matrix3(self.lattice_matrix, name="lattice_matrix")
        except ValueError as exc:
            raise PeriodicRingActionInputError(str(exc)) from exc
        if abs(determinant3(matrix)) != 1:
            raise PeriodicRingActionInputError(
                "lattice_matrix must be unimodular with determinant +1 or -1."
            )
        vertices = tuple(
            _nonnegative_int(x, name="vertex_atom_indices entry")
            for x in self.vertex_atom_indices
        )
        if vertices != tuple(sorted(vertices)) or len(set(vertices)) != len(vertices):
            raise PeriodicRingActionInputError(
                "vertex_atom_indices must be sorted and unique."
            )
        images = tuple(self.vertex_images)
        if len(images) != len(vertices) or any(
            not isinstance(image, LiftedVertexRef) for image in images
        ):
            raise PeriodicRingActionInputError(
                "vertex_images must align one-to-one with vertex_atom_indices."
            )
        if sorted(image.atom_index for image in images) != list(vertices):
            raise PeriodicRingActionInputError(
                "vertex_images must define a permutation of source framework vertices."
            )
        edge_images = tuple(self.edge_images)
        if any(not isinstance(image, PeriodicEdgeImage) for image in edge_images):
            raise PeriodicRingActionInputError(
                "edge_images must contain PeriodicEdgeImage records."
            )
        if sorted(image.target_edge_index for image in edge_images) != list(
            range(len(edge_images))
        ):
            raise PeriodicRingActionInputError(
                "edge_images must define a permutation of source net-view edge positions."
            )
        object.__setattr__(self, "lattice_matrix", matrix)
        object.__setattr__(self, "vertex_atom_indices", vertices)
        object.__setattr__(self, "vertex_images", images)
        object.__setattr__(self, "edge_images", edge_images)

    def vertex_image(self, atom_index: int) -> LiftedVertexRef:
        """Return ``(pi(i), tau_i)`` for one base-cell source vertex."""

        atom = _nonnegative_int(atom_index, name="atom_index")
        position = bisect_left(self.vertex_atom_indices, atom)
        if (
            position >= len(self.vertex_atom_indices)
            or self.vertex_atom_indices[position] != atom
        ):
            raise PeriodicRingActionInputError(
                f"atom_index={atom} is absent from this automorphism."
            )
        return self.vertex_images[position]


@dataclass(frozen=True, slots=True)
class RingOccurrenceMap:
    """Exact occurrence-level image of one translated primitive-ring placement.

    Explicit source-position -> target-position permutations are authoritative.
    ``parameterization`` is the compact cyclic/reversed description and is
    independently validated against those permutations.
    """

    periodic_net_view_digest: str
    topology_graph_digest: str
    source_placement: RingPlacement
    target_placement: RingPlacement
    source_vertex_position_to_target_position: tuple[int, ...]
    source_step_position_to_target_position: tuple[int, ...]
    parameterization: CycleParameterization

    def __post_init__(self) -> None:
        if (
            not isinstance(self.periodic_net_view_digest, str)
            or len(self.periodic_net_view_digest) != 64
        ):
            raise PeriodicRingActionInputError(
                "periodic_net_view_digest must be a SHA-256 digest."
            )
        if (
            not isinstance(self.topology_graph_digest, str)
            or len(self.topology_graph_digest) != 64
        ):
            raise PeriodicRingActionInputError(
                "topology_graph_digest must be a SHA-256 digest."
            )
        if not isinstance(self.source_placement, RingPlacement) or not isinstance(
            self.target_placement, RingPlacement
        ):
            raise PeriodicRingActionInputError(
                "source_placement and target_placement must be RingPlacement records."
            )
        if (
            self.source_placement.topology_graph_digest != self.topology_graph_digest
            or self.target_placement.topology_graph_digest
            != self.topology_graph_digest
        ):
            raise PeriodicRingActionInputError(
                "RingOccurrenceMap placements must share topology_graph_digest."
            )
        vertices = tuple(
            _nonnegative_int(
                x, name="source_vertex_position_to_target_position entry"
            )
            for x in self.source_vertex_position_to_target_position
        )
        steps = tuple(
            _nonnegative_int(
                x, name="source_step_position_to_target_position entry"
            )
            for x in self.source_step_position_to_target_position
        )
        if not vertices or len(vertices) != len(steps):
            raise PeriodicRingActionInputError(
                "Occurrence maps require equally sized nonempty vertex and step permutations."
            )
        expected = list(range(len(vertices)))
        if sorted(vertices) != expected or sorted(steps) != expected:
            raise PeriodicRingActionInputError(
                "Occurrence maps must contain complete vertex and step permutations."
            )
        if not isinstance(self.parameterization, CycleParameterization):
            raise PeriodicRingActionInputError(
                "parameterization must be a CycleParameterization."
            )
        if vertices != self.parameterization.vertex_permutation(len(vertices)):
            raise PeriodicRingActionInputError(
                "Vertex permutation disagrees with cycle parameterization."
            )
        if steps != self.parameterization.step_permutation(len(steps)):
            raise PeriodicRingActionInputError(
                "Step permutation disagrees with cycle parameterization."
            )
        object.__setattr__(
            self, "source_vertex_position_to_target_position", vertices
        )
        object.__setattr__(self, "source_step_position_to_target_position", steps)

    @property
    def orientation(self) -> Literal[-1, 1]:
        return self.parameterization.orientation

    @property
    def start_vertex_index(self) -> int:
        return self.parameterization.start_vertex_index


def build_validated_periodic_automorphism(
    view: PeriodicNetView,
    *,
    lattice_matrix: Sequence[Sequence[int]],
    vertex_images: Mapping[int, LiftedVertexRef],
    edge_images: Sequence[PeriodicEdgeImage],
) -> ValidatedPeriodicAutomorphism:
    """Validate one explicit periodic multigraph automorphism against a net view.

    This constructor validates exact graph incidence *and* the deterministic
    ``NetViewPolicy`` signatures.  It is not a symmetry-discovery algorithm.

    The quotient-graph representation and integer edge translations follow Chung,
    Hahn & Klee (1984).  Exact combinatorial periodic-net action follows
    Delgado-Friedrichs & O'Keeffe (2003).  Explicit edge permutation is retained
    because equal signatures permit exchange but never collapse parallel edges.
    """

    if not isinstance(view, PeriodicNetView):
        raise PeriodicRingActionInputError("view must be a PeriodicNetView.")
    try:
        matrix = coerce_int_matrix3(lattice_matrix, name="lattice_matrix")
    except ValueError as exc:
        raise PeriodicRingActionInputError(str(exc)) from exc
    if not _matrix_preserves_pbc_subspace(matrix, view.pbc):
        raise PeriodicRingActionValidationError(
            "lattice_matrix mixes active periodic translations into nonperiodic axes."
        )

    source_vertices = view.vertex_atom_indices
    supplied: dict[int, LiftedVertexRef] = {}
    for raw_vertex, image in dict(vertex_images).items():
        vertex = _nonnegative_int(raw_vertex, name="vertex_images key")
        if vertex in supplied:
            raise PeriodicRingActionInputError(
                "vertex_images contains duplicate normalized source vertices."
            )
        if not isinstance(image, LiftedVertexRef):
            raise PeriodicRingActionInputError(
                "vertex_images values must be LiftedVertexRef records."
            )
        supplied[vertex] = image
    if set(supplied) != set(source_vertices):
        missing = sorted(set(source_vertices) - set(supplied))
        extra = sorted(set(supplied) - set(source_vertices))
        raise PeriodicRingActionInputError(
            "vertex_images must define every net-view vertex exactly once; "
            f"missing={missing}, extra={extra}."
        )
    normalized_images = tuple(supplied[vertex] for vertex in source_vertices)
    inactive_axes = tuple(axis for axis, periodic in enumerate(view.pbc) if not periodic)
    if any(
        image.image_shift[axis] != 0
        for image in normalized_images
        for axis in inactive_axes
    ):
        raise PeriodicRingActionValidationError(
            "vertex image shifts must vanish along nonperiodic axes."
        )
    action = ValidatedPeriodicAutomorphism(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        lattice_matrix=matrix,
        vertex_atom_indices=source_vertices,
        vertex_images=normalized_images,
        edge_images=tuple(edge_images),
    )
    if len(action.edge_images) != view.n_edges:
        raise PeriodicRingActionInputError(
            "edge_images must align with every source net-view edge position."
        )

    # A decorated graph automorphism must preserve the exact signature policy.
    # Ignoring a field permits exchange; it never merges records.
    for source_atom in source_vertices:
        target_atom = action.vertex_image(source_atom).atom_index
        if view.vertex_signature(source_atom) != view.vertex_signature(target_atom):
            raise PeriodicRingActionValidationError(
                "Vertex action violates the PeriodicNetView signature policy for "
                f"source atom {source_atom}."
            )

    # Validate exact endpoint/image-shift incidence and edge signatures.  For
    # source edge e=(i,j,Delta), the representative maps lifted vertices by
    # (v,n)->(pi(v), A n + tau_v).  The target edge position and orientation are
    # explicit because a multigraph vertex action alone cannot distinguish
    # parallel edges.  This follows the exact periodic-net action model of
    # Chung-Hahn-Klee (1984) and Delgado-Friedrichs-O'Keeffe (2003).
    for source_edge_position, source_key in enumerate(view.edge_keys):
        edge_image = action.edge_images[source_edge_position]
        target_key = view.edge_keys[edge_image.target_edge_index]
        if view.edge_signatures[source_edge_position] != view.edge_signatures[
            edge_image.target_edge_index
        ]:
            raise PeriodicRingActionValidationError(
                "Edge action violates the PeriodicNetView signature policy for "
                f"source edge position {source_edge_position}."
            )
        left = action.vertex_image(source_key.vertex_i)
        right = action.vertex_image(source_key.vertex_j)
        mapped_delta_end = add_shift(
            matvec_shift(action.lattice_matrix, source_key.image_shift),
            right.image_shift,
        )

        if edge_image.orientation == 1:
            endpoints_ok = (
                left.atom_index == target_key.vertex_i
                and right.atom_index == target_key.vertex_j
            )
            shifts_ok = mapped_delta_end == add_shift(
                left.image_shift, target_key.image_shift
            )
        else:
            endpoints_ok = (
                left.atom_index == target_key.vertex_j
                and right.atom_index == target_key.vertex_i
            )
            shifts_ok = mapped_delta_end == subtract_shift(
                left.image_shift, target_key.image_shift
            )
        if not endpoints_ok or not shifts_ok:
            raise PeriodicRingActionValidationError(
                "Edge action is inconsistent with the supplied vertex/lattice action "
                f"for source edge position {source_edge_position}."
            )
    return action


def map_lifted_vertex(
    automorphism: ValidatedPeriodicAutomorphism,
    vertex: LiftedVertexRef,
) -> LiftedVertexRef:
    """Apply one validated view-bound action to one lifted framework vertex."""

    if not isinstance(automorphism, ValidatedPeriodicAutomorphism):
        raise PeriodicRingActionInputError(
            "automorphism must be a ValidatedPeriodicAutomorphism."
        )
    if not isinstance(vertex, LiftedVertexRef):
        raise PeriodicRingActionInputError("vertex must be a LiftedVertexRef.")
    base = automorphism.vertex_image(vertex.atom_index)
    return LiftedVertexRef(
        base.atom_index,
        add_shift(
            matvec_shift(automorphism.lattice_matrix, vertex.image_shift),
            base.image_shift,
        ),
    )


def _validate_view_sources(
    view: PeriodicNetView,
    automorphism: ValidatedPeriodicAutomorphism,
) -> None:
    if not isinstance(view, PeriodicNetView):
        raise PeriodicRingActionInputError("view must be a PeriodicNetView.")
    if not isinstance(automorphism, ValidatedPeriodicAutomorphism):
        raise PeriodicRingActionInputError(
            "automorphism must be a ValidatedPeriodicAutomorphism."
        )
    if automorphism.periodic_net_view_digest != view.digest:
        raise PeriodicRingActionInputError(
            "Automorphism belongs to a different PeriodicNetView digest."
        )
    if automorphism.topology_graph_digest != view.source_graph_digest:
        raise PeriodicRingActionInputError(
            "Automorphism and PeriodicNetView have different topology graph digests."
        )
    if len(automorphism.edge_images) != view.n_edges:
        raise PeriodicRingActionInputError(
            "Automorphism edge action is incompatible with the source net view."
        )


def _validate_ring_sources(
    index: PrimitiveRingIndex,
    view: PeriodicNetView,
    automorphism: ValidatedPeriodicAutomorphism,
) -> None:
    if not isinstance(index, PrimitiveRingIndex):
        raise PeriodicRingActionInputError("index must be a PrimitiveRingIndex.")
    _validate_view_sources(view, automorphism)
    if index.topology_graph_digest != view.source_graph_digest:
        raise PeriodicRingActionInputError(
            "PrimitiveRingIndex and PeriodicNetView have different topology graph digests."
        )
    index_edge_keys = tuple(search.edge_key for search in index.catalog.edge_searches)
    if set(index_edge_keys) != set(view.edge_keys):
        raise PeriodicRingActionInputError(
            "PrimitiveRingIndex and PeriodicNetView do not expose the same edge orbit set."
        )


def map_lifted_edge_instance(
    view: PeriodicNetView,
    automorphism: ValidatedPeriodicAutomorphism,
    edge_instance: LiftedEdgeInstanceRef,
) -> LiftedEdgeInstanceRef:
    """Map one exact physical edge instance under a view-bound automorphism."""

    _validate_view_sources(view, automorphism)
    if not isinstance(edge_instance, LiftedEdgeInstanceRef):
        raise PeriodicRingActionInputError(
            "edge_instance must be a LiftedEdgeInstanceRef."
        )
    if edge_instance.topology_graph_digest != view.source_graph_digest:
        raise PeriodicRingActionInputError(
            "LiftedEdgeInstanceRef belongs to a different topology graph digest."
        )
    try:
        source_edge_position = view.edge_position(edge_instance.edge_key)
    except ValueError as exc:  # pragma: no cover - PeriodicNetView normalizes error
        raise PeriodicRingActionInputError(str(exc)) from exc
    source_key = edge_instance.edge_key
    image = automorphism.edge_images[source_edge_position]
    left = automorphism.vertex_image(source_key.vertex_i)
    transformed_anchor = matvec_shift(
        automorphism.lattice_matrix, edge_instance.anchor_shift
    )
    if image.orientation == 1:
        target_anchor = add_shift(transformed_anchor, left.image_shift)
    else:
        right = automorphism.vertex_image(source_key.vertex_j)
        target_anchor = add_shift(
            transformed_anchor,
            add_shift(
                matvec_shift(automorphism.lattice_matrix, source_key.image_shift),
                right.image_shift,
            ),
        )
    return LiftedEdgeInstanceRef(
        view.source_graph_digest,
        view.edge_keys[image.target_edge_index],
        target_anchor,
    )


def _mapped_step_sequence(
    index: PrimitiveRingIndex,
    view: PeriodicNetView,
    automorphism: ValidatedPeriodicAutomorphism,
    ring_key: PrimitiveRingKey,
) -> tuple[PrimitiveRingStep, ...]:
    ring = index.ring_for_key(ring_key)
    mapped: list[PrimitiveRingStep] = []
    for step in ring.steps:
        source_key = index.edge_key_for_index(step.edge_index)
        source_view_position = view.edge_position(source_key)
        edge_image = automorphism.edge_images[source_view_position]
        target_key = view.edge_keys[edge_image.target_edge_index]
        try:
            target_ring_edge_index = index.edge_index_for_key(target_key)
        except ValueError as exc:
            raise PeriodicRingActionInputError(str(exc)) from exc
        mapped.append(
            PrimitiveRingStep(
                target_ring_edge_index,
                step.orientation * edge_image.orientation,
            )
        )
    return tuple(mapped)


def _key_for_mapped_steps(
    index: PrimitiveRingIndex,
    steps: tuple[PrimitiveRingStep, ...],
) -> PrimitiveRingKey:
    tokens = tuple(
        PrimitiveRingEdgeToken(
            index.edge_key_for_index(step.edge_index),
            step.orientation,
        )
        for step in steps
    )
    return PrimitiveRingKey(canonicalize_primitive_ring_tokens(tokens))


def map_ring_placement(
    index: PrimitiveRingIndex,
    view: PeriodicNetView,
    automorphism: ValidatedPeriodicAutomorphism,
    placement: RingPlacement,
) -> RingOccurrenceMap:
    """Map one translated primitive-ring occurrence exactly under an automorphism.

    The result records the target stable ring key and translation together with
    explicit source-position -> target-position permutations for both vertices
    and edge steps.  The ordered lifted occurrence is transformed first.  Token
    canonicalization identifies only the target ring key; exact lifted vertices
    and physical edge instances determine the unique cyclic/reversed alignment.
    """

    _validate_ring_sources(index, view, automorphism)
    if not isinstance(placement, RingPlacement):
        raise PeriodicRingActionInputError("placement must be a RingPlacement.")
    if placement.topology_graph_digest != index.topology_graph_digest:
        raise PeriodicRingActionInputError(
            "RingPlacement belongs to a different topology graph digest."
        )
    source_ring = index.ring_for_key(placement.ring_key)
    mapped_steps = _mapped_step_sequence(index, view, automorphism, placement.ring_key)
    target_key = _key_for_mapped_steps(index, mapped_steps)
    try:
        target_ring = index.ring_for_key(target_key)
    except ValueError as exc:
        raise RingOccurrenceMappingError(
            "The transformed ring is absent from the represented source catalog; "
            "the catalog may be incomplete/truncated or the action may not preserve "
            "the declared ring graph."
        ) from exc

    mapped_vertices = tuple(
        map_lifted_vertex(
            automorphism,
            LiftedVertexRef(
                vertex.atom_index,
                add_shift(vertex.image_shift, placement.image_shift),
            ),
        )
        for vertex in source_ring.vertex_walk
    )

    matches: list[RingOccurrenceMap] = []
    n = source_ring.size
    for orientation in (1, -1):
        for start in range(n):
            parameterization = CycleParameterization(
                start_vertex_index=start,
                orientation=orientation,  # type: ignore[arg-type]
            )
            vertex_permutation = parameterization.vertex_permutation(n)
            step_permutation = parameterization.step_permutation(n)
            first_target = target_ring.vertex_walk[vertex_permutation[0]]
            if mapped_vertices[0].atom_index != first_target.atom_index:
                continue
            target_shift = subtract_shift(
                mapped_vertices[0].image_shift, first_target.image_shift
            )

            vertices_ok = all(
                mapped_vertices[k].atom_index
                == target_ring.vertex_walk[vertex_permutation[k]].atom_index
                and mapped_vertices[k].image_shift
                == add_shift(
                    target_ring.vertex_walk[vertex_permutation[k]].image_shift,
                    target_shift,
                )
                for k in range(n)
            )
            if not vertices_ok:
                continue

            steps_ok = all(
                mapped_steps[k].edge_index
                == target_ring.steps[step_permutation[k]].edge_index
                and mapped_steps[k].orientation
                == orientation * target_ring.steps[step_permutation[k]].orientation
                for k in range(n)
            )
            if not steps_ok:
                continue

            exact_edges_ok = True
            for k in range(n):
                source_instance = index.canonical_edge_instance(source_ring.key, k)
                source_instance = LiftedEdgeInstanceRef(
                    index.topology_graph_digest,
                    source_instance.edge_key,
                    add_shift(source_instance.anchor_shift, placement.image_shift),
                )
                mapped_instance = map_lifted_edge_instance(
                    view, automorphism, source_instance
                )
                target_instance = index.canonical_edge_instance(
                    target_ring.key, step_permutation[k]
                )
                expected_target = LiftedEdgeInstanceRef(
                    index.topology_graph_digest,
                    target_instance.edge_key,
                    add_shift(target_instance.anchor_shift, target_shift),
                )
                if mapped_instance != expected_target:
                    exact_edges_ok = False
                    break
            if not exact_edges_ok:
                continue

            matches.append(
                RingOccurrenceMap(
                    periodic_net_view_digest=view.digest,
                    topology_graph_digest=index.topology_graph_digest,
                    source_placement=placement,
                    target_placement=RingPlacement(
                        index.topology_graph_digest, target_key, target_shift
                    ),
                    source_vertex_position_to_target_position=vertex_permutation,
                    source_step_position_to_target_position=step_permutation,
                    parameterization=parameterization,
                )
            )

    if not matches:
        raise RingOccurrenceMappingError(
            "Validated automorphism produced no exact target ring-occurrence alignment."
        )
    unique = tuple(dict.fromkeys(matches))
    if len(unique) != 1:
        raise RingOccurrenceMappingError(
            "Validated automorphism produced multiple exact occurrence alignments; "
            "the ring occurrence identity is ambiguous."
        )
    return unique[0]


__all__ = [
    "PeriodicEdgeImage",
    "PeriodicRingActionError",
    "PeriodicRingActionInputError",
    "PeriodicRingActionValidationError",
    "RingOccurrenceMap",
    "RingOccurrenceMappingError",
    "ValidatedPeriodicAutomorphism",
    "build_validated_periodic_automorphism",
    "map_lifted_edge_instance",
    "map_lifted_vertex",
    "map_ring_placement",
]
