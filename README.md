# InterviewLab (Streamlit) — AI Mock Interviewer

InterviewLab is a Streamlit web app for **behavioral** and **technical** mock interviews. It uses OpenAI for conversational interviewing, optional audio transcription/TTS, and a post-interview evaluation dashboard with scores and feedback.

Each user supplies their **own OpenAI API key in the app UI** — nothing is stored in code or server secrets.

## What it does

- **Interview modes**
  - **Behavioral** — STAR-method follow-ups from an HR-style interviewer
  - **Technical** — role-specific questions with depth/accuracy follow-ups
- **Personalization** — target role, level, job description, and resume drive question selection
- **Input modes**
  - **Audio + Text** — record answers (Streamlit `audio_input`) + optional typed replies
  - **Text Only** — chat-style text answers
- **Optional AI voice** — TTS playback for interviewer questions
- **5-question flow** — progress bar, follow-ups, opening/closing messages
- **Evaluation dashboard** — overall score, dimension breakdown, strengths, improvements, sample answer

## Quick start (local)

### Prerequisites

- Python 3.11+ (3.14 supported; entrypoint uses the same loader pattern as [st-Quizzly](https://github.com/NU-YaoLi/st-Quizzly))
- An OpenAI API key

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
streamlit run interviewlab_main.py
```

Enter your OpenAI API key in the **sidebar** when the app loads.

## Deploy to Streamlit Community Cloud

### 1. Push to GitHub

Commit the repo (do **not** commit `.streamlit/secrets.toml`).

### 2. Create the app

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app** → connect your GitHub repo
3. Set **Main file path** to:

   ```
   interviewlab_main.py
   ```

4. **Advanced settings → Python version:** 3.11 or newer recommended
5. Click **Deploy**

### 3. Secrets (optional)

No secrets are required for normal operation — users enter their API key in the sidebar.

Optional debug logging only:

```toml
# .streamlit/secrets.toml (Streamlit Cloud → App settings → Secrets)
DEBUG = true
```

See `.streamlit/secrets.toml.example`.

### 4. After deploy

- Share the public URL with users
- Each user pastes their own OpenAI API key in the sidebar
- For **Audio + Text** mode, users must allow microphone access in the browser (HTTPS is provided by Streamlit Cloud)

## Configuration knobs

Edit `interviewlab_config.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `INTERVIEWLAB_MODEL` | `gpt-5-mini` | Chat + evaluation |
| `WHISPER_MODEL` | `gpt-4o-transcribe` | Speech-to-text |
| `WHISPER_FALLBACK_MODEL` | `whisper-1` | Transcription fallback |
| `TTS_MODEL` | `gpt-4o-mini-tts` | Interviewer voice |
| `TTS_FALLBACK_MODEL` | `tts-1` | TTS fallback |
| `TOTAL_QUESTIONS` | `5` | Interview length |
| `PER_TURN_EVALUATION` | `False` | Score after each answer |

## Project layout

```
interviewlab_main.py       # Streamlit entrypoint (Cloud main file)
interviewlab_config.py     # Models, prompts, rubrics, constants
bknd/                      # Backend (OpenAI, engine, audio, evaluator)
fntnd/                     # Frontend (UI, session state, views)
  interviewlab_ftnd.py     # main() router
  interviewlab_state.py    # Session defaults + state mapping
  interviewlab_errors.py   # Cloud-friendly OpenAI error messages
  views/                   # Landing, interview chat, evaluation dashboard
.streamlit/config.toml     # Theme + headless server settings for Cloud
```

## Notes / caveats

- **API keys:** Stored only in the user's browser session (`st.session_state`). They are sent to OpenAI with each request and are not persisted on the server.
- **Session lifetime:** On Streamlit Cloud, session state resets when the app cold-starts or the user opens a new session.
- **Audio:** Requires Streamlit ≥ 1.33 and browser microphone permission. If transcription fails, switch to **Text Only** mode.
- **Costs:** All OpenAI usage is billed to the API key entered by the user.
