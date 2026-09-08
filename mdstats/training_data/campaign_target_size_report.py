"""Portable human-readable report for one automatic target-size diagnostic.

The automatic screen is expensive, and the decision it informs is now an
operator decision.  So its evidence has to be *readable* by a human who was not
present when it ran - including the human who will override it - and readable
without the campaign database, the campaign store, or this package.

This module renders exactly that: one self-contained Markdown document under the
campaign ``results/`` tree, derived from the authenticated diagnostic bundle.

It is a projection and nothing else.  It never re-ranks, re-aggregates, or
re-decides: the survivor progression it draws is read back out of the reducer's
own committed outcome history, and the recommendation it prints is the one the
reducer committed.  A report is therefore rebuildable and disposable, and it is
never authority: no code reads a recommendation or a frozen N out of this file.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any
import os
import tempfile

AUTO_DIAGNOSTIC_REPORT_SCHEMA = "mdstats.target-size-auto-diagnostic-report.v1"

#: Every report says this, in these words, wherever it is read.
SCIENTIFIC_LIMITATION = (
    "This is a short-horizon diagnostic, not proof of an optimal target size. "
    "It measures target-force component RMSE at three configured epoch "
    "boundaries under one screening protocol. It does not establish asymptotic "
    "target-size convergence, long-horizon training quality, final potential "
    "quality, or molecular-dynamics stability. Post-selection cross-validation, "
    "full production, and post-production physical qualification are "
    "progressively stronger evidence than anything in this report. The "
    "recommendation below may be accepted, ignored, or overridden with "
    "`select-target-size <N>` at any time before `cross-validate` freezes the "
    "downstream design."
)


def auto_diagnostic_report_path(paths: Any, generation: int) -> Path:
    """The stable per-generation report location inside the campaign results."""

    return Path(paths.results) / f"target-size-auto-diagnostic-gen{int(generation)}.md"


def _candidate_realization(validated: Any, target_size: int) -> Any | None:
    """Ask the real P3 owner for one candidate's execution realization.

    This is derivation through the owning API, not a second implementation: the
    same call, with the same authenticated definition/context/schedule, is what
    produced the geometry the screen actually ran under.  It performs no
    training and no evaluation.
    """

    from .target_size_execution import build_target_size_candidate_trajectory

    if validated.context is None or validated.schedule is None:
        return None
    definition = validated.authorities.aggregate.definition
    seed = int(definition.policy.optimizer_seeds[0])
    try:
        trajectory = build_target_size_candidate_trajectory(
            definition,
            validated.context,
            validated.authorities.common,
            validated.schedule,
            target_size=int(target_size),
            optimizer_policy=replace(validated.optimizer_policy, seed=seed),
            optimizer_seed=seed,
        )
    except Exception:  # noqa: BLE001 - a report never blocks on presentation
        return None
    return trajectory.realization


def _boundary_rows(head: Any, definition: Any) -> list[dict[str, Any]]:
    """Group the reducer's own committed outcome history by boundary."""

    from .target_size_experiment import TargetSizeBoundaryMetric

    policy = definition.policy
    history = tuple(head.post_state.outcome_history)
    rows: list[dict[str, Any]] = []
    for index, epoch in enumerate(policy.fidelity_epochs):
        outcomes = [item for item in history if int(item.boundary_epoch) == int(epoch)]
        if not outcomes:
            continue
        sizes: list[int] = []
        for item in outcomes:
            if int(item.target_size) not in sizes:
                sizes.append(int(item.target_size))
        per_size: dict[int, list[Any]] = {size: [] for size in sizes}
        for item in outcomes:
            per_size[int(item.target_size)].append(item)
        # Survivors are read from the *next* boundary the reducer actually ran,
        # or from the terminal recommendation. Nothing here re-ranks.
        next_epoch = (
            policy.fidelity_epochs[index + 1]
            if index + 1 < len(policy.fidelity_epochs)
            else None
        )
        if next_epoch is None:
            survivors = tuple(
                size
                for size in sizes
                if head.post_state.selected_target_size == size
            )
        else:
            survivors = tuple(
                sorted(
                    {
                        int(item.target_size)
                        for item in history
                        if int(item.boundary_epoch) == int(next_epoch)
                    }
                )
            )
        entries = []
        for size in sizes:
            per_seed = per_size[size]
            metrics = [
                item for item in per_seed if isinstance(item, TargetSizeBoundaryMetric)
            ]
            complete = len(metrics) == len(per_seed)
            entries.append(
                {
                    "target_size": size,
                    "per_seed": [
                        (
                            int(item.optimizer_seed),
                            (
                                float(item.target_force_rmse_mev_per_a)
                                if isinstance(item, TargetSizeBoundaryMetric)
                                else None
                            ),
                            (
                                None
                                if isinstance(item, TargetSizeBoundaryMetric)
                                else str(item.kind.value)
                            ),
                        )
                        for item in per_seed
                    ],
                    "paired_mean": (
                        sum(
                            item.target_force_rmse_mev_per_a for item in metrics
                        )
                        / len(metrics)
                        if complete and metrics
                        else None
                    ),
                    "complete": complete,
                    "survived": size in survivors,
                }
            )
        rows.append(
            {
                "index": index,
                "boundary_epoch": int(epoch),
                "evaluation_size": int(policy.evaluation_sizes[index]),
                "entries": entries,
                "survivors": survivors,
            }
        )
    return rows


def _format_score(value: float | None, failure: str | None) -> str:
    if value is None:
        return f"FAILED ({failure})" if failure else "FAILED"
    return f"{value:.4f}"


def render_auto_diagnostic_report(validated: Any) -> str:
    """Render the complete Markdown report for one authenticated diagnostic."""

    from .target_size_experiment import CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE

    state = validated.revision.state
    definition = validated.authorities.aggregate.definition
    policy = definition.policy
    projection = validated.projection
    head = validated.head
    normalization = (
        None if validated.schedule is None else validated.schedule.normalization_policy
    )

    lines: list[str] = []
    add = lines.append
    add(f"# Automatic target-size diagnostic - generation {state.generation}")
    add("")
    add(f"<!-- {AUTO_DIAGNOSTIC_REPORT_SCHEMA} -->")
    add("")
    add(
        "**Derived, non-authoritative, rebuildable.** Campaign state plus immutable "
        "P3 evidence are the only authority; nothing reads a recommendation or a "
        "selected size back out of this file."
    )
    add("")

    add("## Scientific limitation")
    add("")
    add(SCIENTIFIC_LIMITATION)
    add("")

    add("## Result")
    add("")
    add(f"- Reducer status: `{projection.reducer_status}`")
    if projection.has_recommendation:
        add(f"- **Recommended target size: N = {projection.recommended_target_size}**")
        add(
            "- Recommended membership identity: "
            f"`{projection.recommended_membership_digest}`"
        )
    else:
        add(
            "- **No recommendation.** The automatic comparison could not be made "
            "under this protocol. This is a diagnostic outcome, not a campaign "
            "failure: a qualified candidate may still be chosen manually with "
            "`select-target-size <N>`."
        )
    codes = tuple(projection.terminal_reason_codes)
    if codes:
        add(f"- Reason/warning codes: {', '.join(f'`{code}`' for code in codes)}")
    if CONFIGURED_CEILING_NONCONVERGENCE_REASON_CODE in codes:
        add(
            "- Warning: the configured practical ceiling was the best evaluated "
            "permitted size. Convergence below the ceiling was **not** "
            "demonstrated; the recommendation is budget-limited."
        )
    add("- Frozen: no. This diagnostic freezes nothing.")
    add("")

    add("## Identity")
    add("")
    add(f"- Canonical generation: `{state.generation}`")
    add(f"- Campaign state revision: `{validated.revision.state_revision}`")
    add(f"- P2 experiment definition: `{definition.content_digest}`")
    add(f"- P2 training order: `{definition.training_order.content_digest}`")
    add(f"- P3 execution context: `{state.execution_context_digest}`")
    add(f"- P3 execution head: `{head.content_digest}`")
    add(f"- Reducer state: `{head.post_state.content_digest}`")
    add(f"- Execution root: `{state.execution_root}`")
    add("")

    add("## Protocol")
    add("")
    add(f"- Configured candidate sizes: {list(policy.candidate_sizes)}")
    add(f"- Qualified candidate sizes: {list(definition.qualified_candidate_sizes)}")
    add(f"- Fidelity boundaries (completed epochs): {list(policy.fidelity_epochs)}")
    add(f"- Evaluation populations per boundary: {list(policy.evaluation_sizes)}")
    add(f"- Paired optimizer seeds: {list(policy.optimizer_seeds)}")
    add("- Ranking metric: target-force component RMSE, meV/A (lower is better)")
    add("- Seed aggregation: arithmetic mean over the complete paired seed set")
    add(
        "- Practical equivalence: "
        f"{policy.practical_equivalence_mev_per_a} meV/A (ties prefer the smaller N)"
    )
    add(
        "- Funnel rule: successive halving - all qualified candidates at boundary 1, "
        "at most four survivors at boundary 2, at most two finalists at boundary 3"
    )
    add(
        "- A candidate with any authenticated numerical failure in its seed set is "
        "eliminated; a partial seed set is never averaged."
    )
    add("")

    add("## Optimizer-progress normalization")
    add("")
    if normalization is None:
        add("- Normalization policy unavailable in this projection.")
    else:
        add(f"- Algorithm: `{normalization.algorithm}`")
        add(f"- Reference target size: {normalization.reference_target_size}")
        add(f"- Reference learning rate: {normalization.reference_learning_rate}")
        add(f"- Reference EMA decay: {normalization.reference_ema_decay}")
        add("")
        add("| N | updates/epoch | progress scale s_N | effective LR | effective EMA decay |")
        add("|---|---|---|---|---|")
        for size in definition.qualified_candidate_sizes:
            realization = _candidate_realization(validated, size)
            if realization is None:
                add(f"| {size} | - | - | - | - |")
                continue
            ema = realization.effective_ema_decay
            add(
                f"| {size} | {realization.updates_per_epoch} | "
                f"{realization.optimizer_progress_scale:.6g} | "
                f"{realization.effective_base_learning_rate:.6g} | "
                f"{'none' if ema is None else format(ema, '.6g')} |"
            )
    add("")

    add("## Per-boundary evidence")
    add("")
    rows = _boundary_rows(head, definition)
    if not rows:
        add("No boundary evidence was committed for this generation.")
    for row in rows:
        add(
            f"### Boundary {row['index'] + 1}: {row['boundary_epoch']} completed "
            f"epoch(s), EVAL2 population M = {row['evaluation_size']}"
        )
        add("")
        seeds = list(policy.optimizer_seeds)
        add(
            "| N | "
            + " | ".join(f"seed {seed} RMSE" for seed in seeds)
            + " | paired mean | outcome |"
        )
        add("|---" * (len(seeds) + 3) + "|")
        for entry in row["entries"]:
            scores = " | ".join(
                _format_score(value, failure)
                for _seed, value, failure in entry["per_seed"]
            )
            mean = (
                f"{entry['paired_mean']:.4f}"
                if entry["paired_mean"] is not None
                else "-"
            )
            terminal = row["index"] + 1 == len(policy.fidelity_epochs)
            if entry["survived"]:
                outcome = "recommended" if terminal else "survived"
            elif not entry["complete"]:
                outcome = "eliminated (authenticated numerical failure)"
            elif terminal:
                outcome = "not recommended (ranked lower at the terminal boundary)"
            else:
                outcome = "eliminated (ranked outside the funnel cut)"
            add(f"| {entry['target_size']} | {scores} | {mean} | {outcome} |")
        add("")

    add("## Filtering decision tree")
    add("")
    if rows:
        for row in rows:
            entered = [entry["target_size"] for entry in row["entries"]]
            terminal = row["index"] + 1 == len(policy.fidelity_epochs)
            add(
                f"- Boundary {row['index'] + 1} ({row['boundary_epoch']} epoch(s)): "
                f"entered {entered} -> "
                + (
                    f"recommended {list(row['survivors'])}"
                    if terminal
                    else f"survived {list(row['survivors'])}"
                )
            )
    if projection.has_recommendation:
        add(f"- Recommendation: N = {projection.recommended_target_size}")
    else:
        add("- Recommendation: none established")
    add("")
    return "\n".join(lines) + "\n"


def write_auto_diagnostic_report(paths: Any, validated: Any) -> Path:
    """Atomically (re)write the portable report; safe to repeat after any crash."""

    destination = auto_diagnostic_report_path(
        paths, validated.revision.state.generation
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = render_auto_diagnostic_report(validated)
    handle, temporary_name = tempfile.mkstemp(
        prefix=destination.name, suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return destination


__all__ = [
    "AUTO_DIAGNOSTIC_REPORT_SCHEMA",
    "SCIENTIFIC_LIMITATION",
    "auto_diagnostic_report_path",
    "render_auto_diagnostic_report",
    "write_auto_diagnostic_report",
]
