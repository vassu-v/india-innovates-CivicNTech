# CivicNTech Co-Pilot — Proto3

AI-powered governance assistant for Indian elected representatives. Tracks commitments made in meetings, clusters citizen complaints by similarity, escalates overdue items automatically, and surfaces a weekly accountability digest. Now with full RAG integration for intelligent chat and strategic suggestions.

---

## What Works (Proto3)

### Engines
- **Commitment Engine** — Extracts commitments, questions, and action items from meeting transcripts using Gemini. Falls back gracefully if API key is missing — stores raw text, never crashes. Tracks deadlines, extensions, and resolution history.
- **Issue Engine** — Logs citizen complaints and clusters similar ones using vector embeddings (sentence-transformers, all-MiniLM-L6-v2). Runs fully locally using `sqlite-vec`.
- **Digest Engine** — Generates weekly summaries: new items by type, resolved vs overdue, resolution rate, most overdue item. Pure SQL, no LLM.
- **Auto-Escalation** — Runs every hour in the background. Recalculates weight and urgency for all pending items based on days overdue (W1 → W2 → W3 → W5 → W8).
- **RAG Engine** — Provides intelligent retrieval-augmented generation. Indexes context files, commitment history, and complaint patterns to power Chat and Suggestions. Uses local embeddings and Gemini for reasoning.

### Dashboard Pages
| Page | Status |
|------|--------|
| Home | Live — real data from all engines with dynamic greeting |
| To-Do | Live — ranked by weight, complete/extend wired |
| Commitments | Live — active list + resolved history |
| Chat | Live — RAG powered assistant grounded in your data |
| Suggestions | Live — AI-generated strategic insights based on live state |
| Digest | Live — weekly breakdown with drilldown overlays |
| Upload Meeting | Live — .txt transcript → Gemini batch extraction → To-Do |
| Log Issue | Live — complaint → vector cluster → To-Do |
| Profile | Live — persists to DB, loads on start. Cleaned of stale options. |

### API Endpoints
```
GET  /api/todo                    — pending items, filterable by type/urgency/ward
GET  /api/digest                  — weekly summary
GET  /api/stats                   — this month + all time + by department
GET  /api/history                 — completed items, paginated
GET  /api/issues/clusters         — open complaint clusters
GET  /api/meetings/recent         — recent processed meetings
GET  /api/complaints/recent       — latest citizen complaints
GET  /api/context/files           — injected context files
GET  /api/profile                 — MLA profile
GET  /api/suggestions             — AI-generated strategic suggestions
POST /api/chat                    — intelligent RAG chat
POST /api/complaint               — log citizen complaint → auto-cluster
POST /api/item                    — add manual item
POST /api/item/{id}/complete      — mark done
POST /api/item/{id}/extend        — push deadline
POST /api/escalate                — manual escalation trigger
POST /api/upload/meeting          — upload .txt transcript → batch extract
POST /api/upload/context          — upload .txt context file → store in DB
POST /api/profile                 — update profile
```

---

## Setup

```bash
pip install fastapi uvicorn google-genai python-dotenv sentence-transformers sqlite-vec pysqlite3-binary
```

*Note: `pysqlite3-binary` is recommended for environments where the system `sqlite3` does not support extension loading.*

Create `.env` in the project root:
```
GEMINI_API_KEY=your_key_here
```

Gemini is used for transcript extraction, chat, and suggestions. Everything else runs without it.

---

## Running

### 1. Seed the database
Populate the database with sample MLA profile, commitments, and citizen complaints.
```bash
PYTHONPATH=Project python Project/seed.py --reset
```

### 2. Start the server
```bash
PYTHONPATH=Project python -m uvicorn main:app --app-dir Project --port 8000
```

### 3. Open the dashboard
Visit [http://localhost:8000](http://localhost:8000) in your browser.

---

## Verification

To verify that all features are connected and working correctly (backend + frontend), you can run the automated Playwright verification script.

### 1. Install Playwright (if not already installed)
```bash
pip install playwright
playwright install chromium
```

### 2. Run verification
Ensure the server is running in a separate terminal, then execute:
```bash
python Project/verify_dashboard.py
```
This script will navigate through all major pages, perform actions, and save screenshots as `verify_*.png`.

---

## Data Layer

Single SQLite file: `copilot.db`

| Table | Owned by | Purpose |
|-------|----------|---------|
| timely_items | Commitment Engine | All commitments, questions, actions, issues |
| clusters | Issue Engine | Complaint clusters with urgency |
| complaints | Issue Engine | Individual citizen complaints |
| vec_clusters | Issue Engine | Vector embeddings for similarity search |
| profile | Commitment Engine | MLA details |
| context_files | Commitment Engine | Injected context for RAG |
| knowledge_nodes | RAG Engine | Metadata for vector search |
| vec_knowledge | RAG Engine | Vector embeddings for RAG nodes |
| ai_memory | RAG Engine | Persistent AI-learned patterns |

---

*Built for India Innovates 2026 — CivicNTech*

---

*Built for India Innovates 2026 — CivicNTech*
