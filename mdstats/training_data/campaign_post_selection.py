"""Current selected-training entry for all post-selection work.

Everything downstream of the target-size decision - cross-validation of the
training method and the fresh final-production run - starts here.  This module
owns exactly one thing: projecting the frozen target-size design admitted at
``cross-validate`` into the small set of facts downstream owners need, and
recording that projection as immutable per-size lineage records.

The frozen design is an ordered collection of distinct sizes, so this owns an
ordered collection of contexts.  The size dimension is one more post-selection
experiment dimension over one shared prepared generation: there is one context
per selected ``N``, and nothing here is per-campaign scalar any more.

It is deliberately not an authority.  Each ``N_selected`` and its exact
``T_selected`` membership are re-established on every current exposure through
the accepted P4 freeze owner, which re-derives them from the authenticated P2
training order.  The automatic screen's execution head and reducer are *not*
part of this ancestry: a campaign that never ran the diagnostic reaches
post-selection work by exactly the same path as one that did.

A persisted binding is a dependency snapshot that lets a descendant prove
*which* selected target it descends from; it can never make a retired
generation current again.  Descendants published by the scalar-selection
predecessor carry that predecessor's binding schema, so they stay valid under
their own exact ancestry rather than being re-parented onto a design that
merely happens to share ``N``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ._common import (
    TrainingDataError,
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
#: The corrected binding schema.  It names the *target* the descendant trained
#: on and nothing else: no role horizon, no selection provenance, and no digest
#: of a record that carries them.  See :class:`PostSelectionBinding`.
POST_SELECTION_BINDING_SCHEMA = "mdstats.post-selection-binding.v3"
#: The scalar-selection predecessor schema.  It additionally hashed the whole
#: frozen selection record, which transitively pulled the production horizon and
#: the manual/auto provenance into every descendant identity.  Rows written
#: under it are still read and stay current under their exact legacy ancestry;
#: no new binding is ever written under it.
POST_SELECTION_BINDING_V2_SCHEMA = "mdstats.post-selection-binding.v2"


class PostSelectionError(TrainingDataError):
    """A post-selection owner refused to treat state as current or valid."""


class PostSelectionStaleBindingError(PostSelectionError):
    """A persisted post-selection binding no longer descends from current P4 state."""


@dataclass(frozen=True, slots=True)
class PostSelectionBinding:
    """The *target* a descendant trained on: one per-size scientific lineage.

    This record answers exactly one question - which selected training target,
    under which prepared scientific substrate, does this evidence descend from -
    and it is deliberately incapable of answering any other.  It names the
    canonical generation, the accepted P1/P2 lineage, ``N_selected`` and the
    exact ``T_selected`` membership identity.

    What it does **not** name is as load-bearing as what it does.  The
    cross-validation horizon belongs to the CV policy, the production horizon
    belongs to the final-production policy, and manual-versus-automatic
    provenance belongs to the audit record.  None of them describes the target,
    so none of them may change this identity - directly *or* through a digest of
    a record that happens to carry them.  Editing the production budget must not
    invalidate accepted CV evidence, and choosing the same size by hand rather
    than by diagnostic must not fork one experiment into two.

    Sibling sizes are equally absent.  A per-size identity that hashed the whole
    frozen collection would change every size's evidence whenever another size
    was added, which is exactly the contamination a multi-size design must not
    have.

    The record is content-addressed and carries no mutable state.  Comparing it
    against a freshly resolved current context is the only supported way to ask
    "is this descendant still current?"; the record never answers that itself.

    ``legacy_frozen_selection_digest`` exists only for reading descendants
    published by the scalar-selection predecessor, whose binding did hash the
    whole frozen record.  Such a binding keeps its own bytes and its own
    identity so evidence accepted under it stays current; nothing new is ever
    constructed with it set.
    """

    campaign_generation: int
    experiment_definition_digest: str
    training_order_digest: str
    frame_authority_digest: str
    neutral_statistical_base_digest: str
    split_exclusion_digest: str
    target_size_policy_digest: str
    aggregate_digest: str
    n_selected: int
    selected_membership_digest: str
    legacy_frozen_selection_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "training_order_digest",
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "target_size_policy_digest",
            "aggregate_digest",
            "selected_membership_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.legacy_frozen_selection_digest is not None:
            object.__setattr__(
                self,
                "legacy_frozen_selection_digest",
                validate_digest(
                    self.legacy_frozen_selection_digest,
                    name="legacy_frozen_selection_digest",
                ),
            )
        generation = int(self.campaign_generation)
        if generation < 0:
            raise TrainingDataInputError(
                "A post-selection binding requires a nonnegative canonical generation."
            )
        object.__setattr__(self, "campaign_generation", generation)
        n_selected = int(self.n_selected)
        if n_selected <= 0:
            raise TrainingDataInputError(
                "A post-selection binding requires a positive selected size."
            )
        object.__setattr__(self, "n_selected", n_selected)

    @property
    def is_legacy_schema(self) -> bool:
        return self.legacy_frozen_selection_digest is not None

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": (
                POST_SELECTION_BINDING_V2_SCHEMA
                if self.is_legacy_schema
                else POST_SELECTION_BINDING_SCHEMA
            ),
            "campaign_generation": self.campaign_generation,
            "experiment_definition_digest": self.experiment_definition_digest,
            "training_order_digest": self.training_order_digest,
            "frame_authority_digest": self.frame_authority_digest,
            "neutral_statistical_base_digest": self.neutral_statistical_base_digest,
            "split_exclusion_digest": self.split_exclusion_digest,
            "target_size_policy_digest": self.target_size_policy_digest,
            "aggregate_digest": self.aggregate_digest,
            "n_selected": self.n_selected,
            "selected_membership_digest": self.selected_membership_digest,
        }
        if self.is_legacy_schema:
            # Reproduced in the predecessor's exact bytes, so a descendant
            # published under it still authenticates and stays reachable.
            payload["frozen_selection_digest"] = self.legacy_frozen_selection_digest
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionBinding":
        schema = payload.get("schema")
        if schema not in (
            POST_SELECTION_BINDING_SCHEMA,
            POST_SELECTION_BINDING_V2_SCHEMA,
        ):
            raise TrainingDataSerializationError(
                "Unsupported post-selection binding schema."
            )
        result = cls(
            campaign_generation=int(payload["campaign_generation"]),
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            training_order_digest=str(payload["training_order_digest"]),
            frame_authority_digest=str(payload["frame_authority_digest"]),
            neutral_statistical_base_digest=str(
                payload["neutral_statistical_base_digest"]
            ),
            split_exclusion_digest=str(payload["split_exclusion_digest"]),
            target_size_policy_digest=str(payload["target_size_policy_digest"]),
            aggregate_digest=str(payload["aggregate_digest"]),
            n_selected=int(payload["n_selected"]),
            selected_membership_digest=str(payload["selected_membership_digest"]),
            legacy_frozen_selection_digest=(
                str(payload["frozen_selection_digest"])
                if schema == POST_SELECTION_BINDING_V2_SCHEMA
                else None
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection binding digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class CurrentSelectedTrainingContext:
    """The authenticated frozen selection, projected for downstream owners.

    Only ``binding`` and ``selected_membership`` carry the *target* identity.
    ``frozen`` additionally carries the two effective role horizons that were
    admitted with it, which is how a CV or production policy resolver reads a
    budget the operator fixed rather than whatever the config file says today.
    The reconstructed authority bundle travels along as an opaque reference so
    downstream owners can reach real P1/P2 data without this adapter duplicating
    any of their validation.
    """

    binding: PostSelectionBinding
    selected_membership: tuple[str, ...]
    frozen: Any = field(compare=False, repr=False)
    authorities: Any = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        membership = tuple(str(v) for v in self.selected_membership)
        if len(membership) != self.binding.n_selected or len(set(membership)) != len(
            membership
        ):
            raise TrainingDataInputError(
                "T_selected must contain exactly N_selected unique frames."
            )
        object.__setattr__(self, "selected_membership", membership)

    @property
    def n_selected(self) -> int:
        return self.binding.n_selected

    @property
    def selected_membership_digest(self) -> str:
        return self.binding.selected_membership_digest

    @property
    def campaign_generation(self) -> int:
        return self.binding.campaign_generation

    @property
    def content_digest(self) -> str:
        return self.binding.content_digest

    @property
    def definition(self) -> Any:
        return self.authorities.aggregate.definition

    @property
    def split_exclusion(self) -> Any:
        return self.authorities.split_exclusion

    def require_binding(self, binding: PostSelectionBinding) -> None:
        """Fail closed unless *binding* is the current selection lineage.

        Descendant evidence proves currency by matching the freshly resolved
        binding.  It is never enough for a stored binding to be internally
        consistent: an earlier generation's binding is perfectly well formed
        and is exactly what must be rejected here.
        """

        if not isinstance(binding, PostSelectionBinding):
            raise TrainingDataInputError(
                "A post-selection currentness check requires a PostSelectionBinding."
            )
        if binding.content_digest != self.binding.content_digest:
            raise PostSelectionStaleBindingError(
                "This post-selection evidence descends from target-size generation "
                f"{binding.campaign_generation} (binding "
                f"{binding.content_digest[:12]}...), but the current authenticated "
                f"selection is generation {self.binding.campaign_generation} (binding "
                f"{self.binding.content_digest[:12]}...). Stale descendants are never "
                "republished as current."
            )


def target_size_binding(state: Any, frozen_entry: Any) -> PostSelectionBinding:
    """Project one frozen per-size entry into its descendant target lineage.

    This is the single owner of that projection.  Freeze admission, P5 pointer
    publication, storage reachability and public observation all derive their
    bindings here, so no second, weaker derivation can exist beside it and drift.

    Selection *provenance* - manual choice or adopted automatic recommendation -
    and both role horizons are deliberately absent.  The same ``N`` on the same
    substrate is the same downstream scientific target however the operator
    arrived at it and whatever budgets its roles were given.
    """

    return PostSelectionBinding(
        campaign_generation=state.generation,
        experiment_definition_digest=state.experiment_definition_digest,
        training_order_digest=frozen_entry.training_order_digest,
        frame_authority_digest=state.frame_authority_digest,
        neutral_statistical_base_digest=state.neutral_statistical_base_digest,
        split_exclusion_digest=state.split_exclusion_digest,
        target_size_policy_digest=state.policy_digest,
        aggregate_digest=state.aggregate_digest,
        n_selected=int(frozen_entry.n_selected),
        selected_membership_digest=str(frozen_entry.selected_membership_digest),
        legacy_frozen_selection_digest=(
            frozen_entry.content_digest if state.legacy_scalar_binding else None
        ),
    )


def current_target_size_bindings(state: Any) -> tuple[PostSelectionBinding, ...]:
    """Every current per-size descendant binding, in frozen selection order.

    Before the freeze there are none, which is exactly right: a provisional
    design has no descendants.
    """

    if not getattr(state, "frozen_entries", None):
        return ()
    return tuple(target_size_binding(state, entry) for entry in state.frozen_entries)


def build_post_selection_binding(admitted: Any) -> PostSelectionBinding:
    """Project one authenticated admitted per-size selection into its lineage."""

    frozen = admitted.frozen
    if frozen is None:
        raise PostSelectionError(
            "A post-selection binding requires a frozen target selection."
        )
    state = admitted.revision.state
    if not state.frozen_entries:
        raise PostSelectionError(
            "A post-selection binding requires a frozen target-size design."
        )
    return target_size_binding(state, frozen)


def load_current_selected_training_contexts(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    admit: bool = False,
) -> tuple[CurrentSelectedTrainingContext, ...]:
    """Resolve every current per-size training context, in frozen order.

    This is the one production-owned enumeration of the frozen design.  Callers
    - including test harnesses - iterate what this returns rather than
    reassembling a loop out of raw campaign state, so the membership, order and
    authentication every size receives are the ones the product actually
    applies.

    ``admit`` is the freeze authority and belongs to ``cross-validate`` alone.
    Every other consumer requires a freeze that already happened, so merely
    describing or continuing downstream work can never commit the experiment.
    """

    from .campaign_target_size_selection import resolve_frozen_target_design

    admitted_design = resolve_frozen_target_design(cfg, paths, store, admit=admit)
    return tuple(
        _selected_training_context(admitted)
        for admitted in admitted_design.per_size
    )


def _selected_training_context(admitted: Any) -> CurrentSelectedTrainingContext:
    binding = build_post_selection_binding(admitted)
    definition = admitted.definition
    membership = definition.training_order.candidate_membership(binding.n_selected)
    if (
        definition.training_order.candidate_digest(binding.n_selected)
        != binding.selected_membership_digest
    ):
        raise PostSelectionError(
            "The exact pi_train prefix does not reproduce the authenticated "
            "T_selected membership digest."
        )
    return CurrentSelectedTrainingContext(
        binding=binding,
        selected_membership=membership,
        frozen=admitted.frozen,
        authorities=admitted.authorities,
    )


def load_current_selected_training_context(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    admit: bool = False,
    n_selected: int | None = None,
) -> CurrentSelectedTrainingContext:
    """Resolve exactly one current per-size training context.

    It is a *selector* over :func:`load_current_selected_training_contexts`, not
    a second authority: the collection owner does all the resolution and this
    only picks the requested member.  ``n_selected`` may be omitted only when
    the frozen design has exactly one size, because for a multi-size design
    "the campaign's selected size" is not a fact and guessing one would silently
    turn an all-sizes experiment into a single-size one.
    """

    contexts = load_current_selected_training_contexts(
        cfg, paths, store, admit=admit
    )
    return select_selected_training_context(contexts, n_selected=n_selected)


def select_selected_training_context(
    contexts: "tuple[CurrentSelectedTrainingContext, ...]",
    *,
    n_selected: int | None = None,
) -> CurrentSelectedTrainingContext:
    """Pick one member of an already-resolved ordered per-size collection."""

    if n_selected is None:
        if len(contexts) == 1:
            return contexts[0]
        raise PostSelectionError(
            "The frozen target-size design contains "
            f"{len(contexts)} selected sizes "
            f"{[item.n_selected for item in contexts]}; name the size explicitly. "
            "There is no single 'the' selected size for a multi-size experiment."
        )
    size = int(n_selected)
    for context in contexts:
        if context.n_selected == size:
            return context
    raise PostSelectionError(
        f"Target size {size} is not part of the current frozen design "
        f"{[item.n_selected for item in contexts]}."
    )


__all__ = [
    "POST_SELECTION_BINDING_SCHEMA",
    "POST_SELECTION_BINDING_V2_SCHEMA",
    "CurrentSelectedTrainingContext",
    "PostSelectionBinding",
    "PostSelectionError",
    "PostSelectionStaleBindingError",
    "build_post_selection_binding",
    "current_target_size_bindings",
    "load_current_selected_training_context",
    "load_current_selected_training_contexts",
    "select_selected_training_context",
    "target_size_binding",
]
