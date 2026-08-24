from __future__ import annotations

import inspect

from mdstats.training_data import _campaign_cli_core


def test_evaluated_model_publication_is_synchronous_and_durable() -> None:
    source = inspect.getsource(_campaign_cli_core._execute_evaluate_current_authority)
    # Regression for 0.20.95a0: publication was delegated to a single async
    # export pool and its SQLite receipt was committed only after the complete
    # campaign-wide evaluation queue drained.
    assert "export_pool" not in source
    assert "incremental_export_futures" not in source
    assert "def publish_evaluated_model" in source
    assert "store.put_record(record_key, member)" in source
    assert "publish_evaluated_model(context, selection)" in source


def test_cached_only_runs_reconcile_before_new_inference_queue() -> None:
    source = inspect.getsource(_campaign_cli_core._execute_evaluate_current_authority)
    prequeue = source.index("# Cached-only runs can be selected and exported")
    finalize = source.index("finalize_evaluated_run(context)", prequeue)
    scheduler = source.index("_run_staged_evaluation_tasks(", finalize)
    assert prequeue < finalize < scheduler


def test_publication_failure_remains_retryable_on_restart() -> None:
    source = inspect.getsource(_campaign_cli_core._execute_evaluate_current_authority)
    publish = source.index("publish_evaluated_model(context, selection)")
    finalized = source.index('context["selection_finalized"] = True', publish)
    # Do not mark the transient in-memory state complete until the atomic export
    # and evaluated_model receipt have both succeeded.
    assert publish < finalized
