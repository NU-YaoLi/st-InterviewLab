"""Streamlit custom component for OpenAI Realtime WebRTC interviews."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

realtime_interview: Callable[..., Any] | None = None


def component_dir() -> Path:
    return Path(__file__).resolve().parent / "components" / "realtime_interview"


def set_realtime_component(recorder: Callable[..., Any]) -> None:
    global realtime_interview
    realtime_interview = recorder


def render_realtime_interview(
    *,
    ephemeral_key: str,
    session_id: int,
    disconnect: bool,
    key: str,
) -> dict | None:
    """Render the Realtime WebRTC client and return transcript / status updates."""
    if realtime_interview is None:
        raise RuntimeError(
            "Realtime component is not registered. "
            "interviewlab_main.py must call set_realtime_component() after bootstrap."
        )
    return realtime_interview(
        ephemeral_key=ephemeral_key,
        session_id=session_id,
        disconnect=disconnect,
        key=key,
        default=None,
    )
