"""Modern post-interview evaluation dashboard."""

from __future__ import annotations

import html

import streamlit as st

from bknd.interviewlab_evaluator import get_dimension_labels, run_evaluation
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_state import (
    apply_state_to_session,
    get_api_key_from_session,
    get_job_display_label,
    state_from_session,
)


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
    role = get_job_display_label(st.session_state)
    duration = st.session_state.get("interview_duration_minutes", 20)
    responses = [
        r
        for r in (st.session_state.get("responses") or [])
        if (r.get("answer") or "").strip()
    ]
    answer_count = len(responses)
    if answer_count == 0:
        answer_count = sum(
            1
            for m in (st.session_state.get("chat_history") or [])
            if m.get("role") == "user" and (m.get("content") or "").strip()
        )

    st.markdown(
        f"""
        <div class="eval-hero">
            <div class="eval-score-big">{html.escape(str(overall))}</div>
            <div class="eval-score-label">Overall Score out of 100</div>
            <p style="color:#64748b;margin-top:1rem;font-size:0.9rem">
                {html.escape(str(mode))} · {html.escape(str(role))} · {duration} min session · {answer_count} responses
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if answer_count == 0:
        st.info(
            "No spoken answers were recorded in this live session, so the score is 0. "
            "Complete a few question-and-answer turns before ending the interview."
        )

    dims = results.get("dimension_scores", {})
    d_cols = st.columns(3)
    for i, (key, label) in enumerate(labels.items()):
        with d_cols[i]:
            score = dims.get(key, 0)
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value">{html.escape(str(score))}<span style="font-size:1rem;color:#94a3b8">/10</span></div>
                    <div class="metric-label">{html.escape(str(label))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        strengths_html = "".join(
            f"<li>{html.escape(str(item))}</li>" for item in results.get("strengths", [])
        )
        st.markdown(
            f"""
            <div class="feedback-card strengths-card">
                <h4>What went well</h4>
                <ul>{strengths_html or "<li>No strengths recorded.</li>"}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with fb_col2:
        improvements_html = "".join(
            f"<li>{html.escape(str(item))}</li>" for item in results.get("improvements", [])
        )
        st.markdown(
            f"""
            <div class="feedback-card improvements-card">
                <h4>Areas to improve</h4>
                <ul>{improvements_html or "<li>No improvements recorded.</li>"}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    sample = results.get("sample_answer", "")
    if sample:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Sample Optimized Answer")
        st.info(sample)

    turn_evals = st.session_state.get("turn_evaluations", [])
    if turn_evals:
        with st.expander("Per-turn evaluations"):
            for i, te in enumerate(turn_evals, start=1):
                st.markdown(f"**Turn {i}** — Score: {te.get('overall_score', 'N/A')}/100")

    st.markdown("<br>", unsafe_allow_html=True)
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
