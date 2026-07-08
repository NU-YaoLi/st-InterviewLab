"""Active interview chat view."""

from __future__ import annotations

import io

import streamlit as st

from bknd.interviewlab_audio import synthesize_if_enabled, transcribe_audio_bytes
from bknd.interviewlab_engine import get_progress_fraction, process_user_response
from bknd.interviewlab_evaluator import run_evaluation
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_state import apply_state_to_session, state_from_session
from interviewlab_config import PER_TURN_EVALUATION


def render_chat_history() -> None:
    for msg in st.session_state.get("chat_history", []):
        role = "assistant" if msg["role"] == "assistant" else "user"
        avatar = "🎤" if role == "assistant" else "👤"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])


def _read_audio_input(key: str = "candidate_audio") -> bytes | None:
    if not hasattr(st, "audio_input"):
        st.warning(
            "Audio recording requires Streamlit >= 1.33. "
            "Upgrade with: `pip install -U streamlit`"
        )
        return None

    audio_value = st.audio_input("Record your answer", key=key)
    if audio_value is None:
        return None
    if hasattr(audio_value, "read"):
        audio_value.seek(0)
        return audio_value.read()
    if isinstance(audio_value, bytes):
        return audio_value
    return None


def _play_tts_once(audio_bytes: bytes | None) -> None:
    if audio_bytes:
        st.audio(io.BytesIO(audio_bytes), format="audio/mp3")


def render_interview_view(api_key: str) -> None:
    state = state_from_session(st.session_state)

    progress = get_progress_fraction(state)
    st.progress(
        progress,
        text=(
            f"Question {min(state.current_question_index, state.total_questions)} "
            f"of {state.total_questions}"
        ),
    )

    render_chat_history()

    if state.last_tts_audio:
        _play_tts_once(state.last_tts_audio)
        st.session_state["last_tts_audio"] = None

    st.divider()
    _render_response_input(api_key)


def _render_response_input(api_key: str) -> None:
    state = state_from_session(st.session_state)
    input_mode = st.session_state.get("input_mode", "Audio + Text")

    text_answer = st.chat_input("Type your answer here…")

    audio_bytes = None
    if input_mode == "Audio + Text":
        audio_bytes = _read_audio_input()

    submit_audio = bool(audio_bytes and input_mode == "Audio + Text" and st.button(
        "Submit Audio Answer", type="primary"
    ))

    if not text_answer and not submit_audio:
        return

    try:
        client = get_openai_client(api_key)
        user_answer = text_answer or ""

        if submit_audio and audio_bytes and not user_answer.strip():
            with st.spinner("Transcribing your response…"):
                user_answer = transcribe_audio_bytes(client, audio_bytes)
            st.info(f"Transcribed: {user_answer}")

        if not user_answer.strip():
            st.error("No answer detected. Please speak clearly or type your response.")
            return

        with st.spinner("Interviewer is thinking…"):
            result = process_user_response(state, client, user_answer)

        if PER_TURN_EVALUATION and result.get("user_answer") and state.responses:
            with st.spinner("Evaluating your response…"):
                run_evaluation(
                    client,
                    state,
                    per_turn=True,
                    latest_question=state.responses[-1]["question"],
                    latest_answer=result["user_answer"],
                )

        if result.get("message"):
            state.last_tts_audio = synthesize_if_enabled(
                client, result["message"], state.ai_voice_enabled
            )

        if result.get("action") == "complete":
            with st.spinner("Generating your evaluation…"):
                run_evaluation(client, state)

        apply_state_to_session(state, st.session_state)
        st.rerun()

    except Exception as exc:
        display_openai_error(exc)
