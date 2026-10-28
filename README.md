# VEXION

**THINK. EXECUTE. VERIFY.**

> A Windows-first, voice-first personal desktop AI assistant with a cinematic holographic UI.

---

## What is VEXION?

VEXION is a personal AI agent that lives on your Windows desktop as a beautiful, minimal interface — a glowing holographic orb you talk to. It can answer questions, open apps, browse the web, search files, create notes, and execute tasks, all controlled by voice or a slim text input.

It uses your own Ollama (local) and Google Gemini (cloud) setup so your data stays yours.

---

## Quick Start (Windows)

```
double-click setup_and_run.bat
```

That script will:
1. Check Python 3.11+
2. Create a virtual environment
3. Install all dependencies
4. Copy `.env.example` → `.env` (first run only)
5. Launch VEXION

---

## Manual Setup

### 1. Requirements

- Windows 10/11
- Python 3.11 or newer → [python.org](https://www.python.org/downloads/)
- (Optional) [Ollama](https://ollama.ai) for local AI

### 2. Clone / Download

```powershell
git clone https://github.com/idhruvx18/VEXION.git
cd VEXION
```

### 3. Create virtual environment

```powershell
py -m venv venv
.\venv\Scripts\activate
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure

```powershell
copy .env.example .env
```

Open `.env` in a text editor and fill in your keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
```

> ⚠️ **Never commit `.env` to Git.** It is already in `.gitignore`.
> If you previously pasted API keys in chat or a public repo, **revoke and rotate them** before using VEXION.

### 6. Run

```powershell
py main.py
```

Or windowed mode (useful for development):

```powershell
py main.py --windowed
```

Print config status without launching the UI:

```powershell
py main.py --diagnostics
```

---

## Local AI Setup (Ollama)

VEXION works best with Ollama for private, offline AI:

```powershell
# Install Ollama from https://ollama.ai
# Then pull a model (check what's available first):
ollama list
ollama pull qwen2.5:3b   # or any model you prefer
ollama serve             # start the server
```

Set `OLLAMA_MODEL` in `.env` to whatever model you pulled.

VEXION will detect if Ollama is not running and tell you what to do.

---

## Cloud AI Setup (Google Gemini)

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Add it to `.env` as `GEMINI_API_KEY`
4. Set `GEMINI_MODEL=gemini-1.5-flash` (or `gemini-1.5-pro`)

Cloud AI is completely optional — VEXION runs fine with Ollama only.

---

## Voice Output (ElevenLabs)

1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Get your API key from the profile page
3. Go to Voice Lab → find your preferred voice → copy the Voice ID
4. Set both in `.env`

VEXION falls back to the system TTS (Windows SAPI) if ElevenLabs is not configured.

---

## Keyboard Shortcuts

| Shortcut    | Action                                 |
|-------------|----------------------------------------|
| `Alt+Space` | Focus VEXION / start listening         |
| `Escape`    | Toggle full-screen ↔ window            |
| `Ctrl+,`    | Open settings panel                    |
| `Ctrl+D`    | Open diagnostics panel                 |
| `Ctrl+Q`    | Quit VEXION                            |
| `Enter`     | Submit text command                    |

---

## What VEXION Can Do

**Voice / text commands:**
- "What time is it?"
- "Open Notepad" / "Open VS Code" / "Open Chrome"
- "Open youtube.com"
- "Search for my resume"
- "Create a note called Meeting Notes: we discussed the project timeline"
- "Show diagnostics"
- "What tools do you have?"

**Approval required (VEXION will show a confirmation):**
- Opening apps or websites
- Creating files
- Any action with external effects

---

## Data & Privacy

- All data is stored locally in `~/VEXION_data/`
- No data is sent to the cloud unless Gemini is configured AND cloud AI is enabled in settings
- No raw audio is stored
- API keys are never logged, printed, or stored in the database

---

## Running Tests

```powershell
.\venv\Scripts\activate
pytest tests\ -v
```

Tests mock all external services — no real API key or running Ollama needed.

---

## Project Structure

```
VEXION/
├── main.py                  # Entry point
├── requirements.txt
├── .env.example             # Config template (copy to .env)
├── setup_and_run.bat        # One-click Windows launcher
├── app/
│   ├── config.py            # Environment config (keys masked)
│   ├── ui/
│   │   ├── main_window.py   # Full-screen window
│   │   ├── orb_widget.py    # Animated holographic orb
│   │   ├── overlays.py      # Waveform, approval, settings, diagnostics
│   │   └── theme.py         # Colours, fonts, timing
│   ├── core/
│   │   ├── assistant.py     # Orchestrator
│   │   ├── router.py        # AI provider routing
│   │   └── state.py         # State machine
│   ├── ai/
│   │   ├── base.py          # Provider interface
│   │   ├── ollama_provider.py
│   │   └── gemini_provider.py
│   ├── voice/
│   │   ├── tts.py           # ElevenLabs + system TTS
│   │   └── stt.py           # Speech recognition
│   ├── tools/
│   │   ├── registry.py      # Tool dispatch + approval
│   │   ├── permissions.py   # Risk model
│   │   ├── open_url.py
│   │   ├── open_app.py
│   │   ├── files.py
│   │   └── system_info.py
│   └── storage/
│       ├── database.py      # SQLite + migrations
│       ├── memory.py        # Settings, history, memories
│       └── audit_log.py     # Tool execution audit
└── tests/
    ├── test_url_validation.py
    ├── test_permissions.py
    ├── test_tool_registry.py
    ├── test_state.py
    ├── test_files.py
    └── test_config.py
```

---

## Troubleshooting

**VEXION won't start:**
- Run `py main.py --diagnostics` to see what's misconfigured
- Make sure PySide6 is installed: `pip install PySide6`

**No voice output:**
- Check ElevenLabs config in `.env`
- Install pyttsx3 for system TTS fallback: `pip install pyttsx3`

**AI not responding:**
- Check Ollama is running: `ollama serve`
- Check `ollama list` includes your configured model

**"No AI provider available":**
- Start Ollama OR add a valid Gemini API key

---

## Limitations (Current Version)

- Browser automation (Playwright), Windows UI automation, and batch file operations are **not yet implemented** — the architecture is ready for them.
- STT uses Google Web Speech API (requires internet); a local Whisper option is planned.
- The global Alt+Space shortcut works within the app window; system-wide hotkey registration requires `keyboard` package (future).

---

## Secrets Reminder

If you ever accidentally committed an API key or pasted it somewhere public:
1. **Revoke it immediately** from the provider's dashboard
2. Generate a new key
3. Add the new key only to your local `.env` file
4. Never add `.env` to git commits
