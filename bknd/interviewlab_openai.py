"""
OpenAI client factory for InterviewLab.

The API key is read from Streamlit secrets (``OPENAI_API_KEY`` or
``openai.api_key``) and passed into backend calls.
"""

from __future__ import annotations

from openai import OpenAI


def get_openai_client(api_key: str) -> OpenAI:
    """Create an OpenAI client from the configured API key."""
    key = (api_key or "").strip()
    if not key:
        raise ValueError(
            "OpenAI API key is required. Add OPENAI_API_KEY to Streamlit secrets."
        )
    return OpenAI(api_key=key)
