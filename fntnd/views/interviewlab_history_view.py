"""Interview history panel and report download controls."""

from __future__ import annotations

import html

import streamlit as st

from bknd.interviewlab_history import history_score_series
from bknd.interviewlab_report import (
    build_markdown_report,
    build_pdf_report,
    report_filename,
)


def render_report_downloads(payload: dict, *, key_prefix: str) -> None:
    """Markdown + PDF download buttons for one report payload."""
    markdown = build_markdown_report(payload)
    try:
        pdf_bytes = build_pdf_report(payload)
    except Exception:
        pdf_bytes = b""

    md_col, pdf_col = st.columns(2)
    with md_col:
        st.download_button(
            "Download Markdown",
            data=markdown,
            file_name=report_filename(payload, "md"),
            mime="text/markdown",
            use_container_width=True,
            key=f"{key_prefix}_md",
        )
    with pdf_col:
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=report_filename(payload, "pdf"),
            mime="application/pdf",
            use_container_width=True,
            key=f"{key_prefix}_pdf",
            disabled=not pdf_bytes,
        )


def render_history_panel(*, title: str = "Your interview history") -> None:
    """Past runs in this browser session (role, mode, duration, score)."""
    history = list(st.session_state.get("interview_history") or [])
    if not history:
        return

    st.markdown(f"#### {title}")
    st.caption(
        "Saved in this browser session only. Download a report if you want a lasting copy."
    )

    scores = history_score_series(history)
    if len(scores) >= 2:
        st.line_chart({"Overall score": scores}, height=180)

    for entry in reversed(history):
        when = str(entry.get("completed_at") or "")[:16].replace("T", " ")
        role = html.escape(str(entry.get("role_label") or "Mock Interview"))
        mode = html.escape(str(entry.get("mode") or "Behavioral"))
        duration = int(entry.get("duration_minutes") or 0)
        score = int(entry.get("overall_score") or 0)
        answers = int(entry.get("answer_count") or 0)
        flag = " · ended for misuse" if entry.get("security_terminated") else ""
        st.markdown(
            f"""
            <div class="history-card">
                <div class="history-score">{score}</div>
                <div class="history-meta">
                    <div class="history-role">{role}</div>
                    <div class="history-sub">{mode} · {duration} min · {answers} responses · {html.escape(when)} UTC{flag}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander(f"Report · {entry.get('role_label') or 'Interview'} ({score}/100)"):
            render_report_downloads(entry, key_prefix=f"hist_{entry.get('id') or when}")

    if st.button("Clear history", key="clear_interview_history"):
        st.session_state["interview_history"] = []
        st.rerun()
