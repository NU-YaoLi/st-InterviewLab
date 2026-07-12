"""
Streamlit entrypoint for InterviewLab.

Loads ``interviewlab_config``, the ``bknd`` package, and the ``fntnd`` package
explicitly via ``SourceFileLoader`` and registers them in ``sys.modules`` before
invoking ``fntnd.interviewlab_ftnd.main()``. Mirrors the loader pattern used in
st-Quizzly to avoid Python 3.14 dotted-import issues on Streamlit Cloud.

Modules are loaded once per server process — subsequent Streamlit reruns skip
re-execution to keep button clicks responsive.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

_root = Path(__file__).resolve().parent
_root_str = str(_root)
if sys.path[0] != _root_str:
    try:
        sys.path.remove(_root_str)
    except ValueError:
        pass
    sys.path.insert(0, _root_str)

_REQUIRED_CONFIG_NAMES = (
    "APP_TITLE",
    "INTERVIEWLAB_MODEL",
    "REALTIME_MODEL",
    "REALTIME_VOICE",
    "REALTIME_TRANSCRIPTION_MODEL",
    "REALTIME_SILENCE_DURATION_MS",
    "REALTIME_INTERRUPT_RESPONSE",
    "REALTIME_VAD_THRESHOLD",
    "REALTIME_VAD_PREFIX_PADDING_MS",
    "TOTAL_QUESTIONS",
    "DURATION_OPTIONS",
    "DEFAULT_DURATION_MINUTES",
    "MINUTES_PER_QUESTION",
    "INTERVIEW_MODES",
    "SUPPORTED_INTERVIEW_LANGUAGE",
    "SESSION_DEFAULTS",
    "get_system_prompt",
    "get_rubric",
    "questions_for_duration",
)

_CONFIG_SNAPSHOT: dict[str, object] = {}
_BOOTSTRAPPED = False


def _attach_to_parent(name: str, mod: object) -> None:
    """Expose SourceFileLoader modules as package attributes for dotted imports."""
    if "." not in name:
        return
    parent_name, attr = name.rsplit(".", 1)
    parent = sys.modules.get(parent_name)
    if parent is not None:
        setattr(parent, attr, mod)


def _load_module(name: str, file_path: Path) -> None:
    if name in sys.modules:
        _attach_to_parent(name, sys.modules[name])
        return
    path_str = str(file_path.resolve())
    if not file_path.is_file():
        raise ImportError(f"Required module missing: {path_str}")
    loader = SourceFileLoader(name, path_str)
    spec = importlib.util.spec_from_file_location(name, path_str, loader=loader)
    if spec is None:
        raise ImportError(f"Could not create spec for module {name} from {path_str}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        loader.exec_module(mod)
    except Exception:
        sys.modules.pop(name, None)
        raise
    _attach_to_parent(name, mod)


def _verify_config() -> None:
    mod = sys.modules.get("interviewlab_config")
    if mod is None or any(not hasattr(mod, n) for n in _REQUIRED_CONFIG_NAMES):
        sys.modules.pop("interviewlab_config", None)
        importlib.invalidate_caches()
        _load_module("interviewlab_config", _root / "interviewlab_config.py")
        mod = sys.modules.get("interviewlab_config")
    if mod is None:
        raise ImportError("interviewlab_config was not registered in sys.modules.")
    missing = [n for n in _REQUIRED_CONFIG_NAMES if not hasattr(mod, n)]
    if missing:
        raise ImportError(
            f"interviewlab_config is missing names {missing}. "
            "Confirm interviewlab_config.py is committed."
        )


def _snapshot_config() -> None:
    mod = sys.modules["interviewlab_config"]
    for name in _REQUIRED_CONFIG_NAMES:
        _CONFIG_SNAPSHOT[name] = getattr(mod, name)


def _reinforce_config() -> None:
    mod = sys.modules.get("interviewlab_config")
    if mod is None or not _CONFIG_SNAPSHOT:
        _verify_config()
        return
    for name, value in _CONFIG_SNAPSHOT.items():
        if not hasattr(mod, name):
            setattr(mod, name, value)


def _load_package(name: str, init_path: Path) -> None:
    if name in sys.modules:
        _attach_to_parent(name, sys.modules[name])
        return
    if not init_path.is_file():
        raise ImportError(f"Required package init missing: {init_path}")
    pkg_dir = str(init_path.parent)
    path_str = str(init_path.resolve())
    loader = SourceFileLoader(name, path_str)
    spec = importlib.util.spec_from_file_location(
        name,
        path_str,
        loader=loader,
        submodule_search_locations=[pkg_dir],
    )
    if spec is None:
        raise ImportError(f"Could not load spec for package {name}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        loader.exec_module(mod)
    except Exception:
        sys.modules.pop(name, None)
        raise
    _attach_to_parent(name, mod)


def _bootstrap() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        _reinforce_config()
        return

    _load_module("interviewlab_config", _root / "interviewlab_config.py")
    _verify_config()
    _snapshot_config()
    _load_package("bknd", _root / "bknd" / "__init__.py")

    _reinforce_config()
    _load_module("bknd.interviewlab_openai", _root / "bknd" / "interviewlab_openai.py")
    _load_module("bknd.interviewlab_language", _root / "bknd" / "interviewlab_language.py")
    _load_module("bknd.interviewlab_resume", _root / "bknd" / "interviewlab_resume.py")
    _load_module("bknd.interviewlab_engine", _root / "bknd" / "interviewlab_engine.py")
    _reinforce_config()
    _load_module("bknd.interviewlab_evaluator", _root / "bknd" / "interviewlab_evaluator.py")
    _load_module("bknd.interviewlab_realtime", _root / "bknd" / "interviewlab_realtime.py")

    _load_package("fntnd", _root / "fntnd" / "__init__.py")
    _reinforce_config()
    _load_module("fntnd.interviewlab_state", _root / "fntnd" / "interviewlab_state.py")
    _load_module("fntnd.interviewlab_errors", _root / "fntnd" / "interviewlab_errors.py")
    _load_module("fntnd.interviewlab_styles", _root / "fntnd" / "interviewlab_styles.py")
    _load_module(
        "fntnd.interviewlab_realtime_component",
        _root / "fntnd" / "interviewlab_realtime_component.py",
    )
    _load_module(
        "fntnd.interviewlab_transcript",
        _root / "fntnd" / "interviewlab_transcript.py",
    )

    _load_package("fntnd.views", _root / "fntnd" / "views" / "__init__.py")
    _load_module(
        "fntnd.views.interviewlab_landing_view",
        _root / "fntnd" / "views" / "interviewlab_landing_view.py",
    )
    _load_module(
        "fntnd.views.interviewlab_interview_view",
        _root / "fntnd" / "views" / "interviewlab_interview_view.py",
    )
    _load_module(
        "fntnd.views.interviewlab_evaluation_view",
        _root / "fntnd" / "views" / "interviewlab_evaluation_view.py",
    )

    _reinforce_config()
    _load_module("fntnd.interviewlab_ftnd", _root / "fntnd" / "interviewlab_ftnd.py")
    _ftnd_mod = sys.modules.get("fntnd.interviewlab_ftnd")
    if _ftnd_mod is None or not hasattr(_ftnd_mod, "main"):
        sys.modules.pop("fntnd.interviewlab_ftnd", None)
        importlib.invalidate_caches()
        _reinforce_config()
        _load_module("fntnd.interviewlab_ftnd", _root / "fntnd" / "interviewlab_ftnd.py")
        _ftnd_mod = sys.modules.get("fntnd.interviewlab_ftnd")

    if _ftnd_mod is None or not hasattr(_ftnd_mod, "main"):
        raise ImportError("Failed to load fntnd.interviewlab_ftnd.main")

    _BOOTSTRAPPED = True


_bootstrap()

import streamlit as st
import streamlit.components.v1 as components

from interviewlab_config import APP_TITLE

_realtime_component_dir = (_root / "fntnd" / "components" / "realtime_interview").resolve()
if not (_realtime_component_dir / "index.html").is_file():
    raise FileNotFoundError(f"Realtime component frontend missing: {_realtime_component_dir}")

_interviewlab_realtime = components.declare_component(
    "interviewlab_realtime",
    path=str(_realtime_component_dir),
)
sys.modules["fntnd.interviewlab_realtime_component"].set_realtime_component(
    _interviewlab_realtime
)

st.set_page_config(page_title=APP_TITLE, page_icon="🎙️", layout="wide")

_ftnd_mod = sys.modules["fntnd.interviewlab_ftnd"]
main = _ftnd_mod.main  # type: ignore[assignment]

if __name__ == "__main__":
    main()
