"""
Audio pipeline: Whisper transcription and TTS generation.

Pure backend — no Streamlit imports. UI widgets live in ``fntnd``.
Includes fallback models so Streamlit Cloud deployments stay resilient when
the primary audio model is unavailable on an API key / tier.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from openai import OpenAI, OpenAIError

from interviewlab_config import (
    TTS_FALLBACK_MODEL,
    TTS_MODEL,
    TTS_VOICE,
    WHISPER_FALLBACK_MODEL,
    WHISPER_MODEL,
)


def save_uploaded_audio(audio_bytes: bytes, suffix: str = ".wav") -> Path:
    """Persist recorded audio bytes to a temp file for the transcription API."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(audio_bytes)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _is_model_unavailable(exc: OpenAIError) -> bool:
    msg = str(exc).lower()
    return "model" in msg and ("not found" in msg or "does not exist" in msg or "invalid" in msg)


def transcribe_audio(client: OpenAI, audio_path: Path) -> str:
    """Send audio to OpenAI and return transcribed text."""
    models = [WHISPER_MODEL, WHISPER_FALLBACK_MODEL]
    last_exc: OpenAIError | None = None

    try:
        for model in models:
            try:
                with open(audio_path, "rb") as audio_file:
                    kwargs: dict = {"model": model, "file": audio_file}
                    if model != WHISPER_FALLBACK_MODEL:
                        kwargs["language"] = "en"
                    response = client.audio.transcriptions.create(**kwargs)
                text = (response.text or "").strip()
                if not text:
                    raise ValueError("Transcription returned empty text. Please try again.")
                return text
            except OpenAIError as exc:
                last_exc = exc
                if model != models[-1] and _is_model_unavailable(exc):
                    continue
                raise RuntimeError(f"Transcription failed: {exc}") from exc

        if last_exc is not None:
            raise RuntimeError(f"Transcription failed: {last_exc}") from last_exc
        raise RuntimeError("Transcription failed: no model succeeded.")
    except OSError as exc:
        raise RuntimeError(f"Could not read audio file: {exc}") from exc
    finally:
        try:
            audio_path.unlink(missing_ok=True)
        except OSError:
            pass


def transcribe_audio_bytes(client: OpenAI, audio_bytes: bytes) -> str:
    """Save bytes to a temp file, transcribe, and clean up."""
    path = save_uploaded_audio(audio_bytes)
    return transcribe_audio(client, path)


def generate_speech(client: OpenAI, text: str) -> bytes:
    """Convert interviewer text to speech; returns raw MP3 bytes."""
    if not text.strip():
        return b""

    models = [TTS_MODEL, TTS_FALLBACK_MODEL]
    last_exc: OpenAIError | None = None

    for model in models:
        try:
            response = client.audio.speech.create(
                model=model,
                voice=TTS_VOICE,
                input=text,
            )
            return response.content
        except OpenAIError as exc:
            last_exc = exc
            if model != models[-1] and _is_model_unavailable(exc):
                continue
            raise RuntimeError(f"Text-to-speech failed: {exc}") from exc

    if last_exc is not None:
        raise RuntimeError(f"Text-to-speech failed: {last_exc}") from last_exc
    raise RuntimeError("Text-to-speech failed: no model succeeded.")


def synthesize_if_enabled(
    client: OpenAI,
    text: str,
    enabled: bool,
) -> bytes | None:
    """Generate TTS audio when the UI toggle is on."""
    if not enabled or not text.strip():
        return None
    return generate_speech(client, text)
