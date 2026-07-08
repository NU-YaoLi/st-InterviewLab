"""Modern setup / onboarding view on the main page."""

from __future__ import annotations

import streamlit as st

from interviewlab_config import DURATION_OPTIONS, INPUT_MODES, INTERVIEW_MODES


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
    st.markdown(
        '<div class="setup-card">'
        '<p class="setup-card-title">🧭 Interview Type</p>'
        '<p class="setup-card-desc">Choose the style of practice that matches your upcoming interview.</p>'
        '</div>',
        unsafe_allow_html=True,
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
    st.markdown(
        '<div class="setup-card">'
        '<p class="setup-card-title">⏱️ Interview Duration</p>'
        '<p class="setup-card-desc">Set how long your mock interview will run — just like the real thing.</p>'
        '</div>',
        unsafe_allow_html=True,
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

    st.markdown(
        '<div class="setup-card">'
        '<p class="setup-card-title">🔑 API Key</p>'
        '<p class="setup-card-desc">Your key stays in this browser session only — never stored on our servers.</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.session_state["openai_api_key"] = st.text_input(
        "OpenAI API Key",
        type="password",
        value=st.session_state.get("openai_api_key", ""),
        placeholder="sk-…",
        label_visibility="collapsed",
    )

    st.markdown(
        '<div class="setup-card">'
        '<p class="setup-card-title">💼 Job Details</p>'
        '<p class="setup-card-desc">Tell us about the role you\'re preparing for so questions are tailored to you.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    col_role, col_level = st.columns(2)
    with col_role:
        st.session_state["target_role"] = st.text_input(
            "Job Title",
            value=st.session_state.get("target_role", ""),
            placeholder="e.g. Software Engineer, Data Analyst",
        )
    with col_level:
        st.session_state["target_level"] = st.text_input(
            "Experience Level",
            value=st.session_state.get("target_level", ""),
            placeholder="e.g. Junior, Mid, Senior",
        )

    st.session_state["job_description"] = st.text_area(
        "Job Description",
        value=st.session_state.get("job_description", ""),
        height=120,
        placeholder="Paste the job description here — the more detail, the better the questions…",
    )

    st.session_state["resume"] = st.text_area(
        "Your Resume / Background (optional)",
        value=st.session_state.get("resume", ""),
        height=100,
        placeholder="Paste your resume or a brief summary of your experience…",
    )

    _render_mode_selector()
    _render_duration_selector()

    st.markdown(
        '<div class="setup-card">'
        '<p class="setup-card-title">🎙️ Response Method</p>'
        '<p class="setup-card-desc">How you\'d like to answer during the interview.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    col_input, col_voice = st.columns(2)
    with col_input:
        st.session_state["input_mode"] = st.radio(
            "Input Mode",
            INPUT_MODES,
            index=INPUT_MODES.index(st.session_state.get("input_mode", "Audio + Text")),
            label_visibility="collapsed",
        )
    with col_voice:
        st.session_state["ai_voice_enabled"] = st.toggle(
            "AI speaks questions aloud (TTS)",
            value=st.session_state.get("ai_voice_enabled", True),
        )

    st.markdown("<br>", unsafe_allow_html=True)

    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button("Begin Mock Interview →", type="primary", use_container_width=True):
            st.session_state["_start_requested"] = True


def render_landing_view() -> None:
    """Alias for setup view — kept for backward compatibility."""
    render_setup_view()
