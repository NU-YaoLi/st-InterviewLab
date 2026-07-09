# InterviewLab (Streamlit) — AI Mock Interviewer

InterviewLab is a Streamlit web app for **behavioral** and **technical** mock interviews. Live interviews use OpenAI’s **Realtime API** (WebRTC speech-to-speech). Post-interview scoring uses a chat model. The app owner configures the AI service via Streamlit secrets — interviewees do not enter credentials in the UI.

## What it does

- **Interview modes**
  - **Behavioral** — natural follow-ups from an HR-style interviewer
  - **Technical** — role-specific questions with depth/accuracy follow-ups
- **Personalization** — job details and resume/background drive the live interviewer
- **Live Realtime voice** — browser WebRTC session (`gpt-realtime-2.1`); speak naturally, no Whisper/TTS turn loop
- **Timed sessions** — 15 / 20 / 30 / 45 minute interviews with End Interview confirmation
- **Evaluation dashboard** — overall score, dimension breakdown, strengths, improvements, sample answer

## Quick start (local)

### Prerequisites

- Python 3.11+ (3.14 supported; entrypoint uses the same loader pattern as [st-Quizzly](https://github.com/NU-YaoLi/st-Quizzly))
- Streamlit secrets with `OPENAI_API_KEY` (see `.streamlit/secrets.toml.example`)

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
streamlit run interviewlab_main.py
```

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set `OPENAI_API_KEY` before running locally.

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

### 3. Secrets

Set the AI service credentials in Streamlit Cloud (**App settings → Secrets**):

```toml
# .streamlit/secrets.toml
OPENAI_API_KEY = "sk-your-key-here"

# Optional debug logging:
# DEBUG = true
```

See `.streamlit/secrets.toml.example`.

### 4. After deploy

- Share the public URL with users
- For voice practice, users must allow microphone access in the browser (HTTPS is provided by Streamlit Cloud)

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

- **Session lifetime:** On Streamlit Cloud, session state resets when the app cold-starts or the user opens a new session.
- **Audio:** Requires Streamlit ≥ 1.33 and browser microphone permission.
