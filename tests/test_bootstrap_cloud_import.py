"""Verify SourceFileLoader bootstrap exposes view modules for Cloud imports."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _stub_deps() -> None:
    openai = types.ModuleType("openai")

    class OpenAI:
        pass

    class OpenAIError(Exception):
        pass

    openai.OpenAI = OpenAI
    openai.OpenAIError = OpenAIError
    for name in (
        "APIConnectionError",
        "APITimeoutError",
        "AuthenticationError",
        "BadRequestError",
        "PermissionDeniedError",
        "RateLimitError",
    ):
        setattr(openai, name, type(name, (OpenAIError,), {}))
    sys.modules["openai"] = openai

    httpx = types.ModuleType("httpx")

    class Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, *a, **k):
            return types.SimpleNamespace(
                status_code=200, text="{}", json=lambda: {"value": "x"}
            )

    httpx.Client = Client
    sys.modules["httpx"] = httpx

    st = types.ModuleType("streamlit")

    class _Frag:
        def __call__(self, *a, **k):
            if a and callable(a[0]):
                return a[0]

            def deco(fn):
                return fn

            return deco

    st.fragment = _Frag()
    st.dialog = lambda *a, **k: (lambda f: f)
    st.session_state = {}
    st.markdown = lambda *a, **k: None
    st.button = lambda *a, **k: False
    st.columns = lambda *a, **k: [
        types.SimpleNamespace(__enter__=lambda s: s, __exit__=lambda *x: None)
        for _ in range(2)
    ]
    st.spinner = lambda *a, **k: types.SimpleNamespace(
        __enter__=lambda s: s, __exit__=lambda *x: None
    )
    st.error = st.warning = st.info = st.success = st.caption = st.divider = (
        lambda *a, **k: None
    )
    st.rerun = lambda *a, **k: None
    st.expander = lambda *a, **k: types.SimpleNamespace(
        __enter__=lambda s: s, __exit__=lambda *x: None
    )
    st.set_page_config = lambda *a, **k: None
    st.secrets = {}
    st.file_uploader = lambda *a, **k: None
    st.text_area = lambda *a, **k: ""
    st.container = lambda *a, **k: types.SimpleNamespace(
        __enter__=lambda s: s, __exit__=lambda *x: None
    )
    sys.modules["streamlit"] = st
    sys.modules["streamlit.components"] = types.ModuleType("streamlit.components")
    c1 = types.ModuleType("streamlit.components.v1")
    c1.declare_component = lambda *a, **k: (lambda **kw: None)
    c1.html = lambda *a, **k: None
    sys.modules["streamlit.components.v1"] = c1


class BootstrapCloudImportTests(unittest.TestCase):
    def test_ftnd_resolves_evaluation_view_from_sys_modules(self) -> None:
        _stub_deps()
        # Clear prior app modules so bootstrap runs fresh.
        for key in list(sys.modules):
            if key == "interviewlab_config" or key.startswith(("bknd", "fntnd")):
                sys.modules.pop(key, None)

        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))

        path = ROOT / "interviewlab_main.py"
        loader = SourceFileLoader("interviewlab_main_test", str(path))
        spec = importlib.util.spec_from_file_location(
            "interviewlab_main_test", str(path), loader=loader
        )
        self.assertIsNotNone(spec)
        mod = importlib.util.module_from_spec(spec)
        # Avoid running page config / component declare by only calling bootstrap.
        # Execute module normally; stubs make side effects safe.
        sys.modules["interviewlab_main_test"] = mod
        loader.exec_module(mod)

        ftnd = sys.modules.get("fntnd.interviewlab_ftnd")
        self.assertIsNotNone(ftnd)
        self.assertTrue(hasattr(ftnd, "main"))
        self.assertTrue(hasattr(ftnd, "_mod"))

        evaluation = ftnd._mod("fntnd.views.interviewlab_evaluation_view")
        self.assertTrue(hasattr(evaluation, "render_evaluation_view"))

        # Parent package attribute attachment (dotted import support).
        views_pkg = sys.modules.get("fntnd.views")
        self.assertIsNotNone(views_pkg)
        self.assertTrue(hasattr(views_pkg, "interviewlab_evaluation_view"))


if __name__ == "__main__":
    unittest.main()
