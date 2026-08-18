"""Browser localStorage persistence for setup fields (job details, resume, history).

Streamlit session state is wiped on a full page refresh (F5). This module stores
setup data on the parent page origin and hydrates session state before widgets
mount, so the form comes back filled.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import streamlit as st

STORAGE_KEY = "interviewlab_setup_v1"

# Fields that should survive F5. Do not include live-interview secrets or flags.
PERSIST_KEYS: tuple[str, ...] = (
    "job_description",
    "target_role",
    "target_level",
    "resume",
    "resume_typed",
    "resume_file_text",
    "resume_file_name",
    "resume_file_hash",
    "interview_mode",
    "interview_duration_minutes",
    "interview_history",
)

setup_persist: Callable[..., Any] | None = None


def component_dir() -> Path:
    return Path(__file__).resolve().parent / "components" / "setup_persist"


def set_setup_persist_component(recorder: Callable[..., Any]) -> None:
    global setup_persist
    setup_persist = recorder


def snapshot_setup(session: dict[str, Any] | Any) -> dict[str, Any]:
    """JSON-safe snapshot of setup fields."""
    payload: dict[str, Any] = {"v": 1}
    for key in PERSIST_KEYS:
        payload[key] = copy.deepcopy(session.get(key))
    return payload


def apply_setup_snapshot(session: dict[str, Any] | Any, payload: dict[str, Any] | None) -> bool:
    """Copy persisted fields into session. Returns True if anything was applied."""
    if not isinstance(payload, dict):
        return False
    applied = False
    for key in PERSIST_KEYS:
        if key not in payload:
            continue
        session[key] = copy.deepcopy(payload[key])
        applied = True
    return applied


def _render_persist(*, op: str, payload: dict[str, Any] | None, key: str) -> dict | None:
    if setup_persist is None:
        raise RuntimeError(
            "Setup persist component is not registered. "
            "interviewlab_main.py must call set_setup_persist_component() after bootstrap."
        )
    return setup_persist(
        op=op,
        payload=payload or {},
        storage_key=STORAGE_KEY,
        key=key,
        default=None,
    )


def save_setup_snapshot(session: dict[str, Any] | Any | None = None) -> None:
    """Write current setup fields to the browser. Safe to call on every rerun."""
    if session is None:
        session = st.session_state
    if not st.session_state.get("_setup_hydrated"):
        return
    _render_persist(
        op="save",
        payload=snapshot_setup(session),
        key="il_setup_persist_save",
    )


def ensure_setup_hydrated() -> bool:
    """
    Restore setup from localStorage before the landing form mounts.

    Returns False while the component has not reported yet (caller should
    skip widget creation so ``value=`` / widget keys pick up restored text).
    """
    if st.session_state.get("_setup_hydrated"):
        return True

    result = _render_persist(op="load", payload=None, key="il_setup_persist_load")
    if result is None:
        return False

    payload = result.get("payload") if isinstance(result, dict) else None
    apply_setup_snapshot(st.session_state, payload)
    st.session_state["_setup_hydrated"] = True
    st.rerun()
    return False
