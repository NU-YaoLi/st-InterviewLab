"""Modern post-interview evaluation dashboard."""

from __future__ import annotations

import html
import sys

import streamlit as st

from bknd.interviewlab_evaluator import get_dimension_labels, run_evaluation
from bknd.interviewlab_report import payload_from_session
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_state import (
    apply_state_to_session,
    get_api_key_from_session,
    get_job_display_label,
    record_completed_interview,
    state_from_session,
)
from fntnd.views.interviewlab_history_view import (
    render_history_panel,
    render_report_downloads,
)


def get_openai_client(api_key: str):
    """Resolve the bootstrapped client factory without a Cloud-fragile dotted import."""
    helper = sys.modules.get("bknd.interviewlab_openai")
    fn = getattr(helper, "get_openai_client", None) if helper is not None else None
    if not callable(fn):
        raise ImportError("bknd.interviewlab_openai.get_openai_client is not available")
    return fn(api_key)


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

    if results.get("security_terminated") or st.session_state.get("security_terminated"):
        st.error(
            results.get("improvements", [None])[0]
            or "Interview ended due to repeated misuse attempts."
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

    _render_turn_evaluations(labels)

    st.markdown("#### Download your report")
    st.caption("Includes overall score, rubric, strengths, improvements, per-question scores, and transcript.")
    render_report_downloads(
        payload_from_session(st.session_state, role_label=role),
        key_prefix="current_eval",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Start New Interview", type="primary", use_container_width=True):
        from fntnd.interviewlab_state import reset_runtime_session

        reset_runtime_session()
        st.rerun()

    render_history_panel(title="Progress")


def _render_turn_evaluations(labels: dict[str, str]) -> None:
    turn_evals = list(st.session_state.get("turn_evaluations") or [])
    if not turn_evals:
        return

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Per-question scores")
    for i, te in enumerate(turn_evals, start=1):
        kind = "Follow-up" if te.get("is_follow_up") else f"Q{te.get('question_index') or i}"
        scored = te.get("scored", True)
        score_label = f"{te.get('overall_score', 0)}/100" if scored else "unavailable"
        question = html.escape(str(te.get("question") or ""))
        answer = html.escape(str(te.get("answer") or ""))
        feedback = html.escape(str(te.get("feedback") or ""))
        dims = te.get("dimension_scores") or {}
        dim_html = ""
        if scored:
            dim_html = "".join(
                f'<span class="turn-dim">{html.escape(labels[key])} {html.escape(str(dims.get(key, 0)))}/10</span>'
                for key in labels
            )
        st.markdown(
            f"""
            <div class="turn-eval-card">
                <div class="turn-eval-head">
                    <span class="turn-eval-label">{html.escape(str(kind))}</span>
                    <span class="turn-eval-score">{html.escape(score_label)}</span>
                </div>
                <p class="turn-q"><strong>Interviewer:</strong> {question}</p>
                <p class="turn-a"><strong>You:</strong> {answer}</p>
                <div class="turn-dims">{dim_html}</div>
                {f'<p class="turn-feedback">{feedback}</p>' if feedback else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )


def _run_retroactive_evaluation() -> None:
    try:
        client = get_openai_client(get_api_key_from_session())
        state = state_from_session(st.session_state)
        run_evaluation(
            client,
            state,
            security_terminated=bool(st.session_state.get("security_terminated")),
            security_strikes=int(st.session_state.get("security_consecutive_strikes") or 0),
        )
        apply_state_to_session(state, st.session_state)
        record_completed_interview(st.session_state)
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)
