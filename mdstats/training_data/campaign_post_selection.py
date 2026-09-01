"""Current selected-training entry for all post-selection work.

Everything downstream of target-size selection - cross-validation of the
training method and the fresh final-production run - starts here.  This module
owns exactly one thing: projecting the authenticated current P4 terminal
selection into the small set of facts downstream owners need, and freezing that
projection as an immutable lineage record.

It is deliberately not an authority.  ``N_selected`` and the exact
``T_selected`` membership are re-established on every current exposure through
the accepted P4 loader, which itself re-derives them from authenticated P2/P3
state.  A persisted binding is a dependency snapshot that lets a descendant
prove *which* selection it descends from; it can never make a retired
generation current again.
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
from .campaign_target_size_state import TargetSizeLifecycle

POST_SELECTION_BINDING_SCHEMA = "mdstats.post-selection-binding.v1"


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
    campaign_state_revision: str
    experiment_definition_digest: str
    training_order_digest: str
    frame_authority_digest: str
    neutral_statistical_base_digest: str
    split_exclusion_digest: str
    target_size_policy_digest: str
    aggregate_digest: str
    adopted_execution_head_digest: str
    adopted_reducer_state_digest: str
    n_selected: int
    selected_membership_digest: str

    def __post_init__(self) -> None:
        for name in (
            "campaign_state_revision",
            "experiment_definition_digest",
            "training_order_digest",
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "target_size_policy_digest",
            "aggregate_digest",
            "adopted_execution_head_digest",
            "adopted_reducer_state_digest",
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
            "campaign_state_revision": self.campaign_state_revision,
            "experiment_definition_digest": self.experiment_definition_digest,
            "training_order_digest": self.training_order_digest,
            "frame_authority_digest": self.frame_authority_digest,
            "neutral_statistical_base_digest": self.neutral_statistical_base_digest,
            "split_exclusion_digest": self.split_exclusion_digest,
            "target_size_policy_digest": self.target_size_policy_digest,
            "aggregate_digest": self.aggregate_digest,
            "adopted_execution_head_digest": self.adopted_execution_head_digest,
            "adopted_reducer_state_digest": self.adopted_reducer_state_digest,
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
            campaign_state_revision=str(payload["campaign_state_revision"]),
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            training_order_digest=str(payload["training_order_digest"]),
            frame_authority_digest=str(payload["frame_authority_digest"]),
            neutral_statistical_base_digest=str(
                payload["neutral_statistical_base_digest"]
            ),
            split_exclusion_digest=str(payload["split_exclusion_digest"]),
            target_size_policy_digest=str(payload["target_size_policy_digest"]),
            aggregate_digest=str(payload["aggregate_digest"]),
            adopted_execution_head_digest=str(
                payload["adopted_execution_head_digest"]
            ),
            adopted_reducer_state_digest=str(payload["adopted_reducer_state_digest"]),
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
    """The authenticated current selection, projected for downstream owners.

    Only ``binding`` and ``selected_membership`` carry identity.  The validated
    terminal result and the reconstructed authority bundle travel along as
    opaque references so downstream owners can reach real P1/P2 data without
    this adapter duplicating any of their validation.
    """

    binding: PostSelectionBinding
    selected_membership: tuple[str, ...]
    validated_terminal_result: Any = field(compare=False, repr=False)
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


def build_post_selection_binding(validated_result: Any) -> PostSelectionBinding:
    """Freeze the lineage of one authenticated current SELECTED terminal result."""

    state = validated_result.revision.state
    if state.terminal is None or not validated_result.is_selection:
        raise PostSelectionError(
            "A post-selection binding requires a terminal target-size selection."
        )
    return PostSelectionBinding(
        campaign_generation=state.generation,
        campaign_state_revision=validated_result.revision.state_revision,
        experiment_definition_digest=state.experiment_definition_digest,
        training_order_digest=state.terminal.training_order_digest,
        frame_authority_digest=state.frame_authority_digest,
        neutral_statistical_base_digest=state.neutral_statistical_base_digest,
        split_exclusion_digest=state.split_exclusion_digest,
        target_size_policy_digest=state.policy_digest,
        aggregate_digest=state.aggregate_digest,
        adopted_execution_head_digest=state.adopted_execution_head_digest,
        adopted_reducer_state_digest=state.adopted_reducer_state_digest,
        n_selected=int(validated_result.selected_target_size),
        selected_membership_digest=str(validated_result.selected_membership_digest),
    )


def load_current_selected_training_context(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    expected_revision: Any = None,
) -> CurrentSelectedTrainingContext:
    """Resolve the current selected training data through the accepted P4 owner.

    This is the one entry every current post-selection path takes.  It calls
    the canonical P4 exposure boundary in the same invocation, so currentness is
    established from the live CampaignStore rather than from anything a caller
    or a persisted descendant carries.  ``FAILED_SCIENTIFIC`` is a legitimate
    terminal target-size result but is not a valid downstream entry, so it fails
    closed here, before any post-selection state exists.
    """

    from .campaign_target_size_view import expose_current_target_size_terminal_result

    validated = expose_current_target_size_terminal_result(
        cfg, paths, store, expected_revision=expected_revision
    )
    state = validated.revision.state
    if state.lifecycle is not TargetSizeLifecycle.TERMINAL_SELECTED:
        raise PostSelectionError(
            "Post-selection work requires a current SELECTED target-size terminal "
            f"result; canonical generation {state.generation} is "
            f"{state.lifecycle.value}. A terminal scientific failure is a result, "
            "not an entry point: no cross-validation or production state is created."
        )
    if not validated.is_selection or validated.selected_target_size is None:
        raise PostSelectionError(
            "The current terminal target-size result carries no selected size."
        )

    binding = build_post_selection_binding(validated)
    definition = validated.authorities.aggregate.definition
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
        validated_terminal_result=validated,
        authorities=validated.authorities,
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
