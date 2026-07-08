"""Landing / pre-interview instructions."""

from __future__ import annotations

import streamlit as st


def render_landing_view() -> None:
    st.markdown(
        """
        Welcome to **AI Mock Interviewer** — practice behavioral and technical
        interviews with real-time AI feedback.

        ### How it works
        1. Enter your **OpenAI API key** in the sidebar (stored only in this browser session — never on the server).
        2. Configure your **role**, **level**, **job description**, and **resume**.
        3. Choose **Behavioral** (STAR-focused) or **Technical** mode.
        4. Select **Audio + Text** or **Text Only** for your responses.
        5. Click **Start Interview** — you'll answer **5 questions** with optional follow-ups.
        6. Review your **evaluation dashboard** when the interview concludes.

        > **Streamlit Cloud:** Allow microphone access in your browser for audio mode.
        > Interview answers are sent to OpenAI using **your** API key.
        """
    )
