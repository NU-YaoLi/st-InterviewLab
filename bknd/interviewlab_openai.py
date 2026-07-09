"""
OpenAI client factory for InterviewLab.

The API key is read from Streamlit secrets (``OPENAI_API_KEY`` or
``openai.api_key``) and passed into backend calls.
"""

from __future__ import annotations

import re
from typing import Any

from openai import OpenAI


def model_supports_temperature(model: str) -> bool:
    """Return False for GPT-5+ chat models that only accept the default temperature."""
    match = re.match(r"^gpt-(\d+)", model.strip())
    if match:
        return int(match.group(1)) < 5
    return True


def create_chat_completion(
    client: OpenAI,
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float | None = None,
    **kwargs: Any,
):
    """Create a chat completion, omitting temperature when the model rejects it."""
    params: dict[str, Any] = {"model": model, "messages": messages, **kwargs}
    if temperature is not None and model_supports_temperature(model):
        params["temperature"] = temperature
    return client.chat.completions.create(**params)


def get_openai_client(api_key: str) -> OpenAI:
    """Create an OpenAI client from the configured API key."""
    key = (api_key or "").strip()
    if not key:
        raise ValueError("Interview service is not configured.")
    return OpenAI(api_key=key)
