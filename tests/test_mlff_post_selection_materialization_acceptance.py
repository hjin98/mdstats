"""Real-owner acceptance for post-selection optimizer authority and role parity.

These tests intentionally observe the MACE configuration files written by the
production P3/P5 materializers. The existing bounded numerical harnesses remain
below those owners, so a wiring defect between configuration resolution and the
actual trainer request cannot hide behind helper-level equality.
"""
from __future__ import annotations

import json
from pathlib import Path

import tests._mlff_post_selection_fixture as fx

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data.target_size_execution import (
    resolve_target_size_optimizer_normalization_policy,
)


def _screen_optimizer_configs(workspace: Path) -> dict[str, tuple[float, bool, float]]:
    result: dict[str, tuple[float, bool, float]] = {}
    for path in sorted(workspace.rglob("mace_config_n*_seed*.yaml")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        result[path.name] = (
            float(payload["lr"]),
            bool(payload["ema"]),
            float(payload["ema_decay"]),
        )
    assert result, "target-size screen wrote no MACE configurations"
    return result


def _post_selection_configs(
    harness: fx.PostSelectionHarness,
) -> list[tuple[object, dict]]:
    result: list[tuple[object, dict]] = []
    for request in harness.requests:
        path = (
            request.materialization_directory
            / request.materialization.mace_config_relative_path
        )
        assert path.is_file()
        result.append((request, json.loads(path.read_text(encoding="utf-8"))))
    assert result, "post-selection owner wrote no MACE configurations"
    return result


def _shared_method_values(
    items: list[tuple[object, dict]],
) -> set[tuple[float, bool, float, str]]:
    return {
        (
            float(payload["lr"]),
            bool(payload["ema"]),
            float(payload["ema_decay"]),
            str(payload["method_identity_digest"]),
        )
        for _request, payload in items
    }


def _load_context(config: Path):
    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_contexts,
    )

    cfg, paths = cli._load_config(config)
    store = cli.CampaignStore(paths.state_db)
    try:
        contexts = build_post_selection_contexts(cfg, paths, store)
        assert len(contexts) == 1
        return contexts[0]
    finally:
        store.close()


def _run_post_selection(config: Path):
    cv = fx.PostSelectionHarness()
    assert fx.run_cross_validate(config, cv) == 0
    production = fx.PostSelectionHarness()
    assert fx.run_train_production(config, production) == 0
    return _post_selection_configs(cv), _post_selection_configs(production)


def test_real_materialization_keeps_screen_and_post_selection_optimizer_authorities_independent(
    tmp_path: Path,
) -> None:
    """T6/T7: counterfactual authority split through actual P3/P5 materialization."""

    base_text = fx.fixture_config_text()
    screen_text = base_text + """

[target_data.size_convergence.optimizer_normalization]
reference_target_size = 4
reference_learning_rate = 8.0e-4
reference_ema_decay = 0.95
"""
    method_text = base_text.replace(
        "num_workers = 0",
        "num_workers = 0\nlearning_rate = 3.0e-4\nema = true\nema_decay = 0.999",
    )
    assert method_text != base_text

    base_config, base_workspace = fx.build_selected_campaign(
        tmp_path / "base", config_text=base_text
    )
    screen_config, screen_workspace = fx.build_selected_campaign(
        tmp_path / "screen", config_text=screen_text
    )
    method_config, method_workspace = fx.build_selected_campaign(
        tmp_path / "method", config_text=method_text
    )

    base_context = _load_context(base_config)
    screen_context = _load_context(screen_config)
    method_context = _load_context(method_config)

    # Establish that all compared campaigns share identical frozen target lineage:
    # 1. Identical selected target size N
    assert base_context.selected.n_selected == 8
    assert screen_context.selected.n_selected == base_context.selected.n_selected
    assert method_context.selected.n_selected == base_context.selected.n_selected

    # 2. Identical exact prefix membership T_N in order
    assert len(base_context.selected.selected_membership) == 8
    assert screen_context.selected.selected_membership == base_context.selected.selected_membership
    assert method_context.selected.selected_membership == base_context.selected.selected_membership
    assert screen_context.selected.selected_membership_digest == base_context.selected.selected_membership_digest
    assert method_context.selected.selected_membership_digest == base_context.selected.selected_membership_digest

    # 3. Identical training-order identity
    assert screen_context.selected.binding.training_order_digest == base_context.selected.binding.training_order_digest
    assert method_context.selected.binding.training_order_digest == base_context.selected.binding.training_order_digest

    # 4. Identical role-neutral TargetBinding identity
    assert screen_context.selected.binding.content_digest == base_context.selected.binding.content_digest
    assert method_context.selected.binding.content_digest == base_context.selected.binding.content_digest
    assert screen_context.selected.binding == base_context.selected.binding
    assert method_context.selected.binding == base_context.selected.binding

    base_screen = _screen_optimizer_configs(base_workspace)
    changed_screen = _screen_optimizer_configs(screen_workspace)
    method_screen = _screen_optimizer_configs(method_workspace)

    # Screen-only policy really moves the executable screen, while changing the
    # post-selection [training] method does not leak into the screen optimizer.
    assert changed_screen != base_screen
    assert method_screen == base_screen
    # Realized P3 normalized optimizer values for N=8 and reference N=4
    assert base_screen["mace_config_n8_seed1.yaml"] == (0.0128, True, 0.9987208124587365)
    assert changed_screen["mace_config_n8_seed1.yaml"] == (0.0004, True, 0.9746794344808963)
    assert changed_screen["mace_config_n4_seed1.yaml"] == (0.0008, True, 0.95)

    base_cv, base_prod = _run_post_selection(base_config)
    screen_cv, screen_prod = _run_post_selection(screen_config)
    method_cv, method_prod = _run_post_selection(method_config)

    base_cv_method = _shared_method_values(base_cv)
    base_prod_method = _shared_method_values(base_prod)
    assert len(base_cv_method) == 1
    assert base_prod_method == base_cv_method

    # T7: CV and production receive the same shared optimizer/method through the
    # real materializer; only their frozen role budgets differ.
    assert {request.run_plan.planned_epochs for request, _ in base_cv} == {2}
    assert {request.run_plan.planned_epochs for request, _ in base_prod} == {3}

    # T6, screen-only direction: changing only the P3 normalization authority
    # leaves actual P5 CV and production optimizer/method materialization alone.
    assert _shared_method_values(screen_cv) == base_cv_method
    assert _shared_method_values(screen_prod) == base_prod_method

    # T6, post-selection direction: changing [training] LR/EMA changes the P5
    # method and actual MACE configs, while the executable P3 screen stayed put.
    changed_method = _shared_method_values(method_cv)
    assert len(changed_method) == 1
    assert changed_method != base_cv_method
    assert _shared_method_values(method_prod) == changed_method
    changed_lr, changed_ema, changed_decay, _changed_digest = next(iter(changed_method))
    assert changed_lr == 3.0e-4
    assert changed_ema is True
    assert changed_decay == 0.999

    # Resolver identities agree with what the materializers demonstrated: the
    # screen table moves only in the screen-mutated campaign.
    base_cfg, _ = cli._load_config(base_config)
    screen_cfg, _ = cli._load_config(screen_config)
    method_cfg, _ = cli._load_config(method_config)
    base_policy = resolve_target_size_optimizer_normalization_policy(base_cfg)
    assert resolve_target_size_optimizer_normalization_policy(method_cfg) == base_policy
    assert resolve_target_size_optimizer_normalization_policy(screen_cfg) != base_policy
