# 🐝 OPENBEE — Multimodal Business Process Intelligence

> **Transform raw documents into structured BPMN workflows — automatically.**  
> Audio meetings, PDFs, images and text files are transcribed, analysed and converted into ready-to-use workflow JSON that can be visualised or injected directly into the OpenBEE portal.

---

## ✨ Features

| Capability | Detail |
|---|---|
| 🎙 **Audio Transcription** | Groq Whisper Large v3 — French & multilingual |
| 🖼 **OCR / Vision** | Llama 4 Scout 17B via Groq API |
| 📄 **Text & PDF Ingestion** | PDF-to-image conversion + plain text pipeline |
| 🤖 **BPMN Extraction** | Few-shot prompt → structured JSON (actors, nodes, edges) |
| 📊 **Diagram Generation** | HTML/SVG swimlane, Mermaid `.mmd`, Graphviz `.dot` |
| 🌐 **OpenBEE Automation** | Browser-use agent auto-creates the workflow in the portal |
| ⚡ **Local Inference** | Using local GPU and cpu |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      USER BROWSER                       │
│                  Streamlit UI :8501                     │
└─────────────┬──────────────────────────┬────────────────┘
              │  REST /ingest            │  /status polling
              ▼                          ▼
┌─────────────────────────────────────────────────────────┐
│              BACKEND  FastAPI :5000  (Ngrok tunnel)     │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │  Audio   │  │   PDF    │  │  Image   │  │  Text  │  │
│  │ Whisper  │  │pdf2image │  │  Vision  │  │  Raw   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       └─────────────┴─────────────┴─────────────┘       │
│                    Raw Context (text)                    │
│                          │                              │
│                          ▼                              │
│              BPMN Extraction Prompt (few-shot)          │
│              Llama 4 Scout 17B — Groq API               │
│                          │                              │
│                          ▼                              │
│         { actors, nodes[], edges[] }  JSON BPMN         │
└─────────────────────────────────────────────────────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
┌─────────┐    ┌──────────────┐
│Diagrams │    │  OpenBEE     │
│HTML/SVG │    │  Portal      │
│Mermaid  │    │  browser-use │
│Graphviz │    │  agent       │
└─────────┘    └──────────────┘
```

---

## 📂 Project Structure

```
solution/
├── backend/
│   └── agents/
│       └── openbee_backend.py      # FastAPI server — ingestion pipeline
├── frontend/
│   ├── app_OPENBEE.py              # Streamlit UI
│   ├── generate_workflow_cerebras.py  # Diagram generator (pure Python, no LLM)
│   └── generate_workflow_openbee.py   # Browser-use agent → OpenBEE portal
├── diagram_output/                 # Generated diagrams (HTML, .mmd, .dot)
├── .env                            # API keys (never commit this)
├── requirements.txt
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── start.ps1                       # One-shot Windows launcher
```

---

## 🚀 Quick Start

### Option A — Docker (recommended)

```bash
# 1. Clone & configure
git clone 
cd solution
cp .env.example .env          # Fill in your API keys

# 2. Build & run
docker compose up --build

# 3. Open the UI
open http://localhost:8501
```

### Option B — Local (Windows / PowerShell)

```powershell
# 1. Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Configure environment
copy .env.example .env        # Edit with your keys

# 4. Launch everything (auto-loads .env)
.\start.ps1
```

Or manually in two terminals:

```powershell
# Terminal 1 — Backend
python backend\agents\openbee_backend.py

# Terminal 2 — Frontend
streamlit run frontend\app_OPENBEE.py
```

---

## ⚙️ Configuration

Create a `.env` file at the root of `solution/`:

```env
GROQ_API_KEY=gsk_...          # https://console.groq.com
NGROK_TOKEN=2...              # https://dashboard.ngrok.com
```


---

## 🔄 Pipeline Walkthrough

### 1 · Upload Documents
Go to the **📤 Ingestion** tab and upload one or more files:

| Format | Processing |
|---|---|
| `.wav / .mp3 / .ogg` | Whisper Large v3 transcription |
| `.pdf` | Converted to images → OCR via Llama 4 Scout |
| `.png / .jpg / .webp` | Direct OCR via Llama 4 Scout |
| `.txt / .md / .csv` | Read as plain text |

### 2 · Monitor in Real Time
Switch to **📋 Logs** — the pipeline runs sequentially and streams live logs.

### 3 · Explore Results
The **📊 Résultats** tab shows:
- Metrics: actor count, node count, edge count
- The full BPMN JSON (collapsible)
- Download button for `workflow_bpmn.json`

### 4 · Generate Diagrams
Click **🔲 Générer les Diagrammes** to instantly produce:
- `workflow.html` — SVG swimlane diagram (download & open in browser)
- `workflow.mmd` — Mermaid source
- `workflow.dot` — Graphviz DOT source

### 5 · Push to OpenBEE (optional)
Click **🌐 Créer le Workflow dans OpenBEE** — a real Chrome browser opens and the AI agent navigates the portal to create the workflow automatically.

---

## 🧠 BPMN Extraction — How It Works

The pipeline uses a **few-shot prompt** with explicit BPMN rules to guide `llama-4-scout-17b-16e-instruct`:

| Shape | Detection Rule |
|---|---|
| `Oval` | Process start / terminal state (archiving, classification) |
| `Rectangle` | Action verb + subject (who does what) |
| `Diamond` | Conditional language: "si", "selon", résultat binaire |

The `FIN` swimlane is always injected as the last actor to receive all terminal Oval nodes.

---

## 🐳 Docker Details

| Service | Port | Image |
|---|---|---|
| `openbee_backend` | `5000` | Python 3.11-slim + poppler |
| `openbee_frontend` | `8501` | Python 3.11-slim + Chromium |

```bash
docker compose logs -f backend    # Watch backend logs
docker compose logs -f frontend   # Watch frontend logs
docker compose down               # Stop everything
docker compose up --build -d      # Rebuild & run in background
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| LLM / Vision |  `llama-4-scout-17b-16e-instruct` |
| Audio |  `whisper-large-v3` |
| Backend | FastAPI + Uvicorn |
| Tunneling | pyngrok (Ngrok free tier) |
| Frontend | Streamlit |
| PDF Processing | pdf2image + Poppler |
| Browser Automation | browser-use + Playwright + Chromium |
| Diagram Rendering | Pure Python (SVG, Mermaid, Graphviz DOT) |

---

## 📝 License

MIT — see [LICENSE](LICENSE)
