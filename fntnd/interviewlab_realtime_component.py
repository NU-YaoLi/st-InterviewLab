"""Streamlit custom component for OpenAI Realtime WebRTC interviews."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from bknd.interviewlab_security import security_bridge_config

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
    silence_seconds: int = 5,
) -> dict | None:
    """Render the Realtime WebRTC client and return transcript / status updates."""
    if realtime_interview is None:
        raise RuntimeError(
            "Realtime component is not registered. "
            "interviewlab_main.py must call set_realtime_component() after bootstrap."
        )
    cfg = security_bridge_config()
    return realtime_interview(
        ephemeral_key=ephemeral_key,
        session_id=session_id,
        disconnect=disconnect,
        silence_seconds=silence_seconds,
        max_security_strikes=int(cfg["max_strikes"]),
        security_redirect_spoken=str(cfg["redirect_spoken"]),
        security_termination_spoken=str(cfg["termination_spoken"]),
        key=key,
        default=None,
    )
