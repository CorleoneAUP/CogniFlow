# OPENBEE — Multimodal Business Process Intelligence

> Transform raw documents into structured BPMN workflows — automatically.  
> Audio meetings, PDFs, images and text files are transcribed, analysed and converted into ready-to-use workflow JSON that can be visualised or injected directly into the OpenBEE portal.

---

## Technology Stack

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Cloud_API-F55036?style=flat&logo=groq&logoColor=white)
![Llama](https://img.shields.io/badge/Llama_4_Scout-17B-0467DF?style=flat&logo=meta&logoColor=white)
![Whisper](https://img.shields.io/badge/Whisper-Large_v3-412991?style=flat&logo=openai&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Chromium-2EAD33?style=flat&logo=playwright&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)
![Ngrok](https://img.shields.io/badge/Ngrok-Tunnel-1F1F1F?style=flat&logo=ngrok&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

---

## Features

| Capability | Detail |
|---|---|
| Audio Transcription | Groq Whisper Large v3 — French and multilingual |
| OCR / Vision | Llama 4 Scout 17B via Groq API |
| Text and PDF Ingestion | PDF-to-image conversion + plain text pipeline |
| BPMN Extraction | Few-shot prompt — structured JSON (actors, nodes, edges) |
| Diagram Generation | HTML/SVG swimlane, Mermaid `.mmd`, Graphviz `.dot` |
| OpenBEE Automation | Browser-use agent auto-creates the workflow in the portal |
| Local or Cloud Inference | Works with local GPU/CPU or via Groq cloud API |

---

## Architecture

```
+----------------------------------------------------------+
|                      USER BROWSER                        |
|                  Streamlit UI :8501                      |
+---------------------+--------------------+---------------+
                      |  REST /ingest      |  /status polling
                      v                    v
+----------------------------------------------------------+
|              BACKEND  FastAPI :5000  (Ngrok tunnel)      |
|                                                          |
|  +----------+  +----------+  +----------+  +----------+  |
|  |  Audio   |  |   PDF    |  |  Image   |  |  Text    |  |
|  | Whisper  |  |pdf2image |  |  Vision  |  |  Raw     |  |
|  +-----+----+  +-----+----+  +-----+----+  +----+-----+  |
|        +-------------+--------------+----------+          |
|                    Raw Context (text)                     |
|                          |                               |
|                          v                               |
|              BPMN Extraction Prompt (few-shot)           |
|              Llama 4 Scout 17B                           |
|                          |                               |
|                          v                               |
|         { actors, nodes[], edges[] }  JSON BPMN          |
+----------------------------------------------------------+
                      |
             +--------+--------+
             v                 v
        +---------+    +---------------+
        |Diagrams |    |  OpenBEE      |
        |HTML/SVG |    |  Portal       |
        |Mermaid  |    |  browser-use  |
        |Graphviz |    |  agent        |
        +---------+    +---------------+
```

---

## Project Structure

```
solution/
├── backend/
│   └── agents/
│       └── openbee_backend.py         # FastAPI server — ingestion pipeline
├── frontend/
│   ├── app_OPENBEE.py                 # Streamlit UI
│   ├── generate_workflow_cerebras.py  # Diagram generator (pure Python, no LLM)
│   └── generate_workflow_openbee.py   # Browser-use agent — OpenBEE portal
├── diagram_output/                    # Generated diagrams (HTML, .mmd, .dot)
├── .env                               # API keys (never commit this)
├── .env.example                       # Template for new contributors
├── requirements.txt
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── start.ps1                          # One-shot Windows launcher
```

---

## Quick Start

### Option A — Docker (recommended)

```bash
# 1. Clone and configure
git clone https://github.com/CorleoneAUP/solution.git
cd solution
cp .env.example .env          # Fill in your API keys

# 2. Build and run
docker compose up --build

# 3. Open the UI
# http://localhost:8501
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

## Configuration

Create a `.env` file at the root of `solution/`:

```env
GROQ_API_KEY=gsk_...          # https://console.groq.com
NGROK_TOKEN=2...              # https://dashboard.ngrok.com
```

---

## Pipeline Walkthrough

### 1. Upload Documents
Go to the **Ingestion** tab and upload one or more files:

| Format | Processing |
|---|---|
| `.wav / .mp3 / .ogg` | Whisper Large v3 transcription |
| `.pdf` | Converted to images then OCR via Llama 4 Scout |
| `.png / .jpg / .webp` | Direct OCR via Llama 4 Scout |
| `.txt / .md / .csv` | Read as plain text |

### 2. Monitor in Real Time
Switch to the **Logs** tab — the pipeline runs sequentially and streams live logs.

### 3. Explore Results
The **Results** tab shows:
- Metrics: actor count, node count, edge count
- The full BPMN JSON (collapsible)
- Download button for `workflow_bpmn.json`

### 4. Generate Diagrams
Click **Generate Diagrams** to instantly produce:
- `workflow.html` — SVG swimlane diagram (download and open in browser)
- `workflow.mmd` — Mermaid source
- `workflow.dot` — Graphviz DOT source

### 5. Push to OpenBEE (optional)
Click **Create Workflow in OpenBEE** — a real Chrome browser opens and the AI agent navigates the portal to create the workflow automatically.

---

## BPMN Extraction — How It Works

The pipeline uses a **few-shot prompt** with explicit BPMN rules to guide `llama-4-scout-17b-16e-instruct`:

| Shape | Detection Rule |
|---|---|
| Oval | Process start or terminal state (archiving, classification) |
| Rectangle | Action verb + subject (who does what) |
| Diamond | Conditional language: "si", "selon", binary result |

The `FIN` swimlane is always injected as the last actor to receive all terminal Oval nodes.

---

## Docker Details

| Service | Port | Image base |
|---|---|---|
| `openbee_backend` | `5000` | Python 3.11-slim + poppler |
| `openbee_frontend` | `8501` | Python 3.11-slim + Chromium |

```bash
docker compose logs -f backend    # Watch backend logs
docker compose logs -f frontend   # Watch frontend logs
docker compose down               # Stop everything
docker compose up --build -d      # Rebuild and run in background
```

---

## Tech Stack Details

| Layer | Technology |
|---|---|
| LLM / Vision | `llama-4-scout-17b-16e-instruct` |
| Audio | `whisper-large-v3` |
| Backend | FastAPI + Uvicorn |
| Tunneling | pyngrok (Ngrok free tier) |
| Frontend | Streamlit |
| PDF Processing | pdf2image + Poppler |
| Browser Automation | browser-use + Playwright + Chromium |
| Diagram Rendering | Pure Python (SVG, Mermaid, Graphviz DOT) |

---

## License

MIT — see [LICENSE](LICENSE)
