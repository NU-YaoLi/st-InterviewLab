"""Modern setup / onboarding view on the main page."""

from __future__ import annotations

import streamlit as st

from interviewlab_config import DURATION_OPTIONS, INPUT_MODES


def _section_title(title: str, subtitle: str = "") -> None:
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def _render_hero() -> None:
    st.markdown(
        """
        <div class="hero-section">
            <div class="hero-badge">AI-Powered Practice</div>
            <h1 class="hero-title">Mock Interview Lab</h1>
            <p class="hero-subtitle">
                Prepare for your next opportunity with a realistic, timed mock interview
                tailored to your target role — behavioral or technical.
            </p>
            <div class="feature-row">
                <div class="feature-item">
                    <div class="feature-icon">🎯</div>
                    <div class="feature-text">Role-specific questions</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">⏱️</div>
                    <div class="feature-text">Timed sessions</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">🎙️</div>
                    <div class="feature-text">Voice or text answers</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">📊</div>
                    <div class="feature-text">Instant feedback</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_mode_selector() -> None:
    _section_title(
        "Interview Type",
        "Choose the style of practice that matches your upcoming interview.",
    )

    current_mode = st.session_state.get("interview_mode", "Behavioral")
    col1, col2 = st.columns(2)

    modes = [
        ("Behavioral", "💬", "STAR-method stories, leadership & teamwork"),
        ("Technical", "⚙️", "System design, coding concepts & problem solving"),
    ]

    for col, (mode, icon, desc) in zip((col1, col2), modes):
        with col:
            is_active = current_mode == mode
            card_class = "mode-card mode-card-active" if is_active else "mode-card"
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="mode-icon">{icon}</div>
                    <div class="mode-label">{mode}</div>
                    <div class="mode-desc">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            label = f"{'✓ ' if is_active else ''}{mode}"
            if st.button(label, key=f"mode_{mode.lower()}", use_container_width=True):
                st.session_state["interview_mode"] = mode
                st.rerun()


def _render_duration_selector() -> None:
    _section_title(
        "Interview Duration",
        "How long your mock interview will run.",
    )

    current_duration = st.session_state.get("interview_duration_minutes", 20)
    cols = st.columns(len(DURATION_OPTIONS))

    for col, duration in zip(cols, DURATION_OPTIONS):
        with col:
            is_active = current_duration == duration
            label = f"{'✓ ' if is_active else ''}{duration} min"
            if st.button(label, key=f"dur_{duration}", use_container_width=True):
                st.session_state["interview_duration_minutes"] = duration
                st.rerun()


def render_setup_view() -> None:
    """Render the full setup form on the main page."""
    _render_hero()

    with st.container():
        _section_title(
            "Job Details",
            "Paste the job title, level, and description — anything that helps tailor your questions.",
        )
        job_details = st.text_area(
            "Job details",
            value=st.session_state.get("job_description", ""),
            height=140,
            placeholder=(
                "e.g. Senior Software Engineer (Mid-Senior)\n\n"
                "We are looking for a backend engineer experienced in Python, "
                "distributed systems, and cloud infrastructure…"
            ),
            label_visibility="collapsed",
        )
        st.session_state["job_description"] = job_details
        st.session_state["target_role"] = ""
        st.session_state["target_level"] = ""

        st.session_state["resume"] = st.text_area(
            "Your background (optional)",
            value=st.session_state.get("resume", ""),
            height=80,
            placeholder="Paste your resume or a brief summary of your experience…",
        )

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        _render_mode_selector()

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        _render_duration_selector()

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        _section_title("Response Method", "How you'd like to answer during the interview.")
        st.session_state["input_mode"] = st.radio(
            "Input mode",
            INPUT_MODES,
            index=INPUT_MODES.index(st.session_state.get("input_mode", "Audio + Text")),
            horizontal=True,
            label_visibility="collapsed",
        )

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        if st.button("Begin Mock Interview →", type="primary", use_container_width=True):
            st.session_state["_start_requested"] = True


def render_landing_view() -> None:
    """Alias for setup view — kept for backward compatibility."""
    render_setup_view()
