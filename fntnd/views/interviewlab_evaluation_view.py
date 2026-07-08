"""Modern post-interview evaluation dashboard."""

from __future__ import annotations

import streamlit as st

from bknd.interviewlab_evaluator import get_dimension_labels, run_evaluation
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_state import apply_state_to_session, get_api_key_from_session, state_from_session
from fntnd.views.interviewlab_interview_view import render_chat_history


def render_evaluation_view() -> None:
    results = st.session_state.get("evaluation_results")
    if not results:
        st.warning("Evaluation results are not available yet.")
        if st.button("Run Evaluation Now"):
            _run_retroactive_evaluation()
        return

    mode = st.session_state.get("interview_mode", "Behavioral")
    labels = get_dimension_labels(mode)
    overall = results.get("overall_score", 0)
    role = st.session_state.get("target_role", "N/A")
    duration = st.session_state.get("interview_duration_minutes", 20)
    responses = st.session_state.get("responses", [])

    st.markdown(
        f"""
        <div class="eval-hero">
            <div class="eval-score-big">{overall}</div>
            <div class="eval-score-label">Overall Score out of 100</div>
            <p style="color:#64748b;margin-top:1rem;font-size:0.9rem">
                {mode} · {role} · {duration} min session · {len(responses)} responses
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    dims = results.get("dimension_scores", {})
    d_cols = st.columns(3)
    for i, (key, label) in enumerate(labels.items()):
        with d_cols[i]:
            score = dims.get(key, 0)
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value">{score}<span style="font-size:1rem;color:#94a3b8">/10</span></div>
                    <div class="metric-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        strengths_html = "".join(
            f"<li>{item}</li>" for item in results.get("strengths", [])
        )
        st.markdown(
            f"""
            <div class="feedback-card strengths-card">
                <h4>✅ What went well</h4>
                <ul>{strengths_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with fb_col2:
        improvements_html = "".join(
            f"<li>{item}</li>" for item in results.get("improvements", [])
        )
        st.markdown(
            f"""
            <div class="feedback-card improvements-card">
                <h4>📈 Areas to improve</h4>
                <ul>{improvements_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    sample = results.get("sample_answer", "")
    if sample:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 💡 Sample Optimized Answer")
        st.info(sample)

    turn_evals = st.session_state.get("turn_evaluations", [])
    if turn_evals:
        with st.expander("Per-turn evaluations"):
            for i, te in enumerate(turn_evals, start=1):
                st.markdown(f"**Turn {i}** — Score: {te.get('overall_score', 'N/A')}/100")

    st.markdown("<br>", unsafe_allow_html=True)
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("Start New Interview", type="primary", use_container_width=True):
            from fntnd.interviewlab_state import reset_runtime_session
            reset_runtime_session()
            st.rerun()


def _run_retroactive_evaluation() -> None:
    try:
        client = get_openai_client(get_api_key_from_session())
        state = state_from_session(st.session_state)
        run_evaluation(client, state)
        apply_state_to_session(state, st.session_state)
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)
