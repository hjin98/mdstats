"""Current selected-training entry for all post-selection work.

Everything downstream of the target-size decision - cross-validation of the
training method and the fresh final-production run - starts here.  This module
owns exactly one thing: projecting the frozen target selection admitted at
``cross-validate`` into the small set of facts downstream owners need, and
recording that projection as an immutable lineage record.

It is deliberately not an authority.  ``N_selected`` and the exact
``T_selected`` membership are re-established on every current exposure through
the accepted P4 freeze owner, which re-derives them from the authenticated P2
training order.  The automatic screen's execution head and reducer are *not*
part of this ancestry: a campaign that never ran the diagnostic reaches
post-selection work by exactly the same path as one that did.

A persisted binding is a dependency snapshot that lets a descendant prove
*which* selection it descends from; it can never make a retired generation
current again.  Descendants published before the operator-owned freeze existed
carry the retired binding schema, so they stay historical rather than being
re-parented onto a new frozen selection that merely happens to share ``N``.
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
POST_SELECTION_BINDING_SCHEMA = "mdstats.post-selection-binding.v2"


class PostSelectionError(TrainingDataError):
    """A post-selection owner refused to treat state as current or valid."""


class PostSelectionStaleBindingError(PostSelectionError):
    """A persisted post-selection binding no longer descends from current P4 state."""


@dataclass(frozen=True, slots=True)
class PostSelectionBinding:
    """Immutable lineage of the exact selected training data a descendant used.

    The record is content-addressed and carries no mutable state.  Comparing it
    against a freshly resolved current context is the only supported way to ask
    "is this descendant still current?"; the record never answers that itself.
    """

    campaign_generation: int
    frozen_selection_digest: str
    experiment_definition_digest: str
    training_order_digest: str
    frame_authority_digest: str
    neutral_statistical_base_digest: str
    split_exclusion_digest: str
    target_size_policy_digest: str
    aggregate_digest: str
    n_selected: int
    selected_membership_digest: str

    def __post_init__(self) -> None:
        for name in (
            "frozen_selection_digest",
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

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_BINDING_SCHEMA,
            "campaign_generation": self.campaign_generation,
            # The frozen selection is the stable ancestry token.  The campaign
            # *state revision* deliberately is not: publishing later diagnostic
            # evidence advances that revision without changing one fact about
            # the frozen experiment, and must not orphan accepted descendants.
            "frozen_selection_digest": self.frozen_selection_digest,
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

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionBinding":
        if payload.get("schema") != POST_SELECTION_BINDING_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection binding schema."
            )
        result = cls(
            campaign_generation=int(payload["campaign_generation"]),
            frozen_selection_digest=str(payload["frozen_selection_digest"]),
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


def build_post_selection_binding(admitted: Any) -> PostSelectionBinding:
    """Project one authenticated frozen target selection into descendant lineage.

    Selection *provenance* - manual choice or adopted automatic recommendation -
    is deliberately absent.  The same ``N`` on the same substrate is the same
    downstream scientific experiment however the operator arrived at it, and a
    binding that disagreed with that would fork one architecture into two.
    """

    state = admitted.revision.state
    frozen = admitted.frozen
    if frozen is None or state.frozen is None:
        raise PostSelectionError(
            "A post-selection binding requires a frozen target selection."
        )
    return PostSelectionBinding(
        campaign_generation=state.generation,
        frozen_selection_digest=frozen.content_digest,
        experiment_definition_digest=state.experiment_definition_digest,
        training_order_digest=frozen.training_order_digest,
        frame_authority_digest=state.frame_authority_digest,
        neutral_statistical_base_digest=state.neutral_statistical_base_digest,
        split_exclusion_digest=state.split_exclusion_digest,
        target_size_policy_digest=state.policy_digest,
        aggregate_digest=state.aggregate_digest,
        n_selected=int(frozen.n_selected),
        selected_membership_digest=str(frozen.selected_membership_digest),
    )


def load_current_selected_training_context(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    admit: bool = False,
) -> CurrentSelectedTrainingContext:
    """Resolve the current frozen training design through the accepted P4 owner.

    This is the one entry every current post-selection path takes.  It calls the
    canonical freeze owner in the same invocation, so currentness is established
    from the live CampaignStore rather than from anything a caller or a persisted
    descendant carries.

    ``admit`` is the freeze authority and belongs to ``cross-validate`` alone.
    Every other consumer requires a freeze that already happened, so merely
    describing or continuing downstream work can never commit the experiment.
    """

    from .campaign_target_size_selection import resolve_frozen_target_selection

    admitted = resolve_frozen_target_selection(cfg, paths, store, admit=admit)
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


__all__ = [
    "POST_SELECTION_BINDING_SCHEMA",
    "CurrentSelectedTrainingContext",
    "PostSelectionBinding",
    "PostSelectionError",
    "PostSelectionStaleBindingError",
    "build_post_selection_binding",
    "load_current_selected_training_context",
]
