"""Package-wide structured progress-port tests."""

from __future__ import annotations

import io
import logging

import pytest

from mdstats import (
    CallbackProgressPort,
    LoggingProgressPort,
    ProgressEmitter,
    ProgressError,
    ProgressEvent,
    TextProgressPort,
    format_progress_event,
    resolve_progress_port,
)


def test_progress_event_is_structured_and_immutable() -> None:
    event = ProgressEvent(
        source="analysis.example",
        stage="frame_loop",
        message="processing frames",
        current=3,
        total=10,
        unit="frames",
        metadata={"backend": "cell_list", "threads": 4},
    )
    assert event.fraction == pytest.approx(0.3)
    assert event.to_dict()["metadata"] == {"backend": "cell_list", "threads": 4}
    with pytest.raises(TypeError):
        event.metadata["threads"] = 8  # type: ignore[index]


def test_progress_event_rejects_inconsistent_counts_and_large_metadata() -> None:
    with pytest.raises(ProgressError, match="current requires total"):
        ProgressEvent(source="x", stage="y", message="z", current=1)
    with pytest.raises(ProgressError, match="cannot exceed"):
        ProgressEvent(source="x", stage="y", message="z", current=2, total=1)
    with pytest.raises(ProgressError, match="scalar"):
        ProgressEvent(
            source="x",
            stage="y",
            message="z",
            metadata={"array": [1, 2, 3]},  # type: ignore[dict-item]
        )


def test_text_port_formats_elapsed_stage_and_count() -> None:
    stream = io.StringIO()
    port = TextProgressPort(
        label="test",
        stream=stream,
        show_source=True,
    )
    port.emit(
        ProgressEvent(
            source="plotting.atomic_density",
            stage="field_realization",
            message="completed Na density",
            status="completed",
            current=1,
            total=4,
            unit="fields",
        )
    )
    rendered = stream.getvalue()
    assert rendered.startswith("[test |")
    assert "plotting.atomic_density: field_realization [1/4 fields]" in rendered
    assert "completed Na density" in rendered


def test_callback_and_logging_ports_receive_structured_events(caplog) -> None:
    events: list[ProgressEvent] = []
    callback_port = CallbackProgressPort(events.append)
    emitter = ProgressEmitter(callback_port, source="analysis.synthetic")
    emitter.started("solve", "starting")
    emitter.completed("solve", "done", current=5, total=5, unit="steps")
    assert [event.status for event in events] == ["started", "completed"]
    assert events[-1].current == 5

    logger = logging.getLogger("mdstats-test-progress")
    logging_port = LoggingProgressPort(logger)
    with caplog.at_level(logging.INFO, logger=logger.name):
        logging_port.emit(events[-1])
    assert "analysis.synthetic: solve [5/5 steps]: done" in caplog.text


def test_legacy_text_callback_is_supported_but_deprecated() -> None:
    messages: list[str] = []
    with pytest.warns(DeprecationWarning):
        port = resolve_progress_port(progress_callback=messages.append)
    ProgressEmitter(port, source="analysis.synthetic").update(
        "loop",
        "working",
        current=2,
        total=7,
        unit="items",
    )
    assert messages == ["loop [2/7 items]: working"]


def test_progress_and_legacy_callback_are_mutually_exclusive() -> None:
    port = TextProgressPort(stream=io.StringIO())
    with pytest.raises(ProgressError, match="not both"):
        resolve_progress_port(port, progress_callback=lambda _message: None)


def test_environment_fallback_uses_text_port(monkeypatch) -> None:
    stream = io.StringIO()
    monkeypatch.setenv("MDSTATS_TEST_PROGRESS", "1")
    port = resolve_progress_port(
        environment_variable="MDSTATS_TEST_PROGRESS",
        environment_label="environment-test",
        environment_stream=stream,
    )
    ProgressEmitter(port, source="analysis.synthetic").update("stage", "message")
    assert "[environment-test |" in stream.getvalue()
    assert "analysis.synthetic: stage: message" in stream.getvalue()


def test_format_progress_event_does_not_add_global_logger_state() -> None:
    event = ProgressEvent(source="io.reader", stage="parse", message="loaded input")
    assert format_progress_event(event) == "io.reader: parse: loaded input"
    assert format_progress_event(event, include_source=False) == "parse: loaded input"
