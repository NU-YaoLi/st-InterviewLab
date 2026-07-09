"""Streamlit custom component for hands-free interview microphone capture."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

auto_mic_recorder: Callable[..., Any] | None = None


def component_dir() -> Path:
    """Return the frontend directory for the auto-mic component."""
    return Path(__file__).resolve().parent / "components" / "auto_mic"


def set_auto_mic_recorder(recorder: Callable[..., Any]) -> None:
    """Bind the component function registered by the Streamlit entrypoint."""
    global auto_mic_recorder
    auto_mic_recorder = recorder


def render_auto_mic(
    *,
    auto_start: bool,
    stop_now: bool,
    silence_seconds: int,
    key: str,
) -> dict | str | None:
    """Render the auto-start mic recorder and return captured audio metadata."""
    if auto_mic_recorder is None:
        raise RuntimeError(
            "Auto-mic component is not registered. "
            "interviewlab_main.py must call set_auto_mic_recorder() after bootstrap."
        )
    return auto_mic_recorder(
        auto_start=auto_start,
        stop_now=stop_now,
        silence_seconds=silence_seconds,
        key=key,
        default=None,
    )
