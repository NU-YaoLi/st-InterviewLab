"""Streamlit custom component for hands-free interview microphone capture."""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

_COMPONENT_PATH = Path(__file__).resolve().parent / "components" / "auto_mic"

auto_mic_recorder = components.declare_component(
    "interviewlab_auto_mic",
    path=str(_COMPONENT_PATH),
)


def render_auto_mic(
    *,
    auto_start: bool,
    stop_now: bool,
    silence_seconds: int,
    key: str,
) -> dict | str | None:
    """Render the auto-start mic recorder and return captured audio metadata."""
    return auto_mic_recorder(
        auto_start=auto_start,
        stop_now=stop_now,
        silence_seconds=silence_seconds,
        key=key,
        default=None,
    )
