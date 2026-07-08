"""
OpenAI client factory for InterviewLab.

The API key is supplied by the Streamlit UI (``st.session_state``) and passed
into every backend call — it is never read from code, secrets, or env vars.
"""

from __future__ import annotations

from openai import OpenAI


def get_openai_client(api_key: str) -> OpenAI:
    """Create an OpenAI client from a user-provided key."""
    key = (api_key or "").strip()
    if not key:
        raise ValueError(
            "OpenAI API key is required. Enter your key in the sidebar to continue."
        )
    return OpenAI(api_key=key)
