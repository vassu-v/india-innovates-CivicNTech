# CivicNTech Co-Pilot — Finalé ![Finalé](https://img.shields.io/badge/Status-Finalé-brightgreen)

AI-powered governance assistant for Indian elected representatives. Tracks commitments made in meetings, clusters citizen complaints by similarity, escalates overdue items automatically, and surfaces a weekly accountability digest. Now with full RAG integration for intelligent chat and strategic suggestions.

---

## What Works (Finalé)

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

---

## RAG & Intelligence Layer

Finalé introduces a sophisticated RAG (Retrieval-Augmented Generation) architecture and an Agentic Suggestion system that grounds AI intelligence in live governance data.

### 1. 3-Layer Context Assembly (The "Second Brain")
The RAG Engine doesn't just "search for text." It assembles a comprehensive snapshot for every query, functioning as an institutional memory that compounds over time. This architecture ensures the AI is grounded in both static facts and the dynamic, evolving state of the constituency.

*   **Layer 1: Live Constituency State:** Pulls real-time stats from the Digest (resolution rates, critical counts), the MLA's Profile, and top pending To-Do items. This provides immediate situational awareness, ensuring the AI knows what is happening *right now*.
*   **Layer 2: Historical Facts & AI Memory:** Utilizes high-performance vector retrieval (powered by `sqlite-vec` with a pure-Python cosine similarity fallback) to search through completed commitment history, injected context files (census data, scheme details), and "AI Memory" nodes. This provides the *long-term institutional memory*.
*   **Layer 3: Live Patterns:** Integrates real-time citizen complaint clusters from the Issue Engine. This enables the system to detect *emerging trends* and recurring issues before they escalate into crises.

### 2. Local Semantic Router (Zero-Token Intelligence)
To ensure high responsiveness and cost-efficiency, a zero-latency router is built into the backend. It classifies incoming queries locally using embeddings before any external LLM is invoked:
*   **Instant Route:** Recognizes greetings, small talk, or general identity questions (e.g., "Namaste", "Who are you?") and responds immediately using a warmth-optimized system prompt. This saves tokens and reduces latency to near-zero.
*   **Follow-up Route:** Detects if a query is a contextual follow-up by comparing its embedding to the "Working Memory" (the vector embeddings of the previously retrieved knowledge nodes). If a match is found, it leverages the existing context for a seamless conversation.
*   **Search Route:** Triggers the full 3-Layer RAG pipeline for deep, data-driven analysis when the user asks for new information or complex insights.

### 3. AI Self-Memory (Recursive Learning)
The system features a recursive feedback loop where the AI can "learn" and store new facts. If the LLM identifies a new pattern, staff member, or preference (e.g., "The MLA prefers PWD issues escalated directly to Commissioner Singh"), it emits a specialized `[MEMORY]` tag. The backend parses these tags and persists the information in the `ai_memory` table, making the "second brain" smarter with every interaction.

### 4. Agentic Suggestion System (Strategic Advisor)
The Suggestion system is a multi-round autonomous agent designed for high-level strategic analysis. Unlike standard chat, it doesn't just respond; it *investigates*:
*   **Snapshot Synthesis:** Triggered on-demand, the agent performs a comprehensive "Snapshot Synthesis" of the entire governance state.
*   **Tool-Calling Loop:** The agent operates in a 3-round loop. It can autonomously decide to call read-only database tools (e.g., `get_department_track_record`, `get_ward_history`, `get_overdue_items`) to gather historical evidence and track records before formulating a recommendation.
*   **Transparent Reasoning:** Every suggested intervention is accompanied by a full "Thinking Trace." This collapsible dropdown in the UI reveals the agent's step-by-step logic, the tools it called, and the data it used.
*   **Data-Backed Output:** Generates 3-4 specific, actionable strategic interventions prioritized by urgency (Critical, Urgent, Normal), each referencing actual constituency data.

## AI Infrastructure — Centralized LLM Wrapper

To ensure architectural consistency and ease of maintenance, all interaction with Large Language Models (LLMs) is channeled through a centralized wrapper:

### The `ai.py` Module
All Project-level engines (`main.py`, `rag_engine.py`, `commitment_engine.py`) no longer call the Gemini SDK directly. instead, they use the `ai.call_ai(prompt)` function.
*   **Decoupled Logic:** Application logic is separated from provider-specific SDKs. If the model needs to be swapped (e.g., from `gemini-2.5-flash-lite` to a local LLM or another provider), it only needs to be changed in one file: `Project/ai.py`.
*   **Uniform Configuration:** Ensures that model parameters (temperature, top_p, etc.) and model versions are consistent across all features (Chat, Suggestions, Extraction).
*   **Global Model:** Currently standardized on `gemini-2.5-flash-lite` for an optimal balance of speed, reasoning capability, and cost-efficiency.

---

## API Endpoints
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
