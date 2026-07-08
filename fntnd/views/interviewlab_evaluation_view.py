"""Post-interview evaluation dashboard view."""

from __future__ import annotations

import streamlit as st

from bknd.interviewlab_evaluator import get_dimension_labels, run_evaluation
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_state import apply_state_to_session, get_api_key_from_session, state_from_session
from fntnd.views.interviewlab_interview_view import render_chat_history
from interviewlab_config import TOTAL_QUESTIONS


def render_evaluation_view() -> None:
    results = st.session_state.get("evaluation_results")
    if not results:
        st.warning("Evaluation results are not available yet.")
        if st.button("Run Evaluation Now"):
            _run_retroactive_evaluation()
        return

    mode = st.session_state.get("interview_mode", "Behavioral")
    labels = get_dimension_labels(mode)

    st.subheader("Evaluation Dashboard")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.metric("Overall Score", f"{results.get('overall_score', 0)} / 100")
    with col2:
        st.metric("Questions Completed", TOTAL_QUESTIONS)
    with col3:
        st.caption(
            f"Mode: **{mode}** · Role: **{st.session_state.get('target_role', 'N/A')}**"
        )

    st.divider()

    st.markdown("### Dimension Scores")
    dims = results.get("dimension_scores", {})
    d_cols = st.columns(3)
    for i, (key, label) in enumerate(labels.items()):
        with d_cols[i]:
            st.metric(label, f"{dims.get(key, 0)} / 10")

    st.divider()

    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        st.markdown("### What went well")
        for item in results.get("strengths", []):
            st.markdown(f"- {item}")

    with fb_col2:
        st.markdown("### Areas for improvement")
        for item in results.get("improvements", []):
            st.markdown(f"- {item}")

    st.divider()

    sample = results.get("sample_answer", "")
    if sample:
        st.markdown("### Sample Optimized Answer")
        st.info(sample)

    turn_evals = st.session_state.get("turn_evaluations", [])
    if turn_evals:
        with st.expander("Per-turn evaluations"):
            for i, te in enumerate(turn_evals, start=1):
                st.markdown(f"**Turn {i}** — Score: {te.get('overall_score', 'N/A')}/100")


def _run_retroactive_evaluation() -> None:
    try:
        client = get_openai_client(get_api_key_from_session())
        state = state_from_session(st.session_state)
        run_evaluation(client, state)
        apply_state_to_session(state, st.session_state)
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)
