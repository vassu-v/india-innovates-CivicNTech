# CivicNTech Co-Pilot — Proto2

AI-powered governance assistant for Indian elected representatives. Tracks commitments made in meetings, clusters citizen complaints by similarity, escalates overdue items automatically, and surfaces a weekly accountability digest.

---

## What Works (Proto2)

### Engines
- **Commitment Engine** — Extracts commitments, questions, and action items from meeting transcripts using Gemini. Falls back gracefully if API key is missing — stores raw text, never crashes. Tracks deadlines, extensions, and resolution history.
- **Issue Engine** — Logs citizen complaints and clusters similar ones using vector embeddings (sentence-transformers, all-MiniLM-L6-v2). Runs fully locally, no API needed.
- **Digest Engine** — Generates weekly summaries: new items by type, resolved vs overdue, resolution rate, most overdue item. Pure SQL, no LLM.
- **Auto-Escalation** — Runs every hour in the background. Recalculates weight and urgency for all pending items based on days overdue (W1 → W2 → W3 → W5 → W8).

### Dashboard Pages
| Page | Status |
|------|--------|
| Home | Live — real data from all engines |
| To-Do | Live — ranked by weight, complete/extend wired |
| Commitments | Live — active list + resolved history |
| Digest | Live — weekly breakdown with drilldown overlays |
| Upload Meeting | Live — .txt transcript → Gemini batch extraction → To-Do |
| Log Issue | Live — complaint → vector cluster → To-Do |
| Profile | Live — persists to DB, loads on start |
| Context Injection | Live — .txt files stored in DB for RAG (proto3) |
| Chat | Mockup — RAG engine not yet built |
| Suggestions | Mockup — RAG engine not yet built |

### API Endpoints
```
GET  /api/todo                    — pending items, filterable by type/urgency/ward
GET  /api/digest                  — weekly summary
GET  /api/stats                   — this month + all time + by department
GET  /api/history                 — completed items, paginated
GET  /api/issues/clusters         — open complaint clusters
GET  /api/meetings/recent         — recent processed meetings
GET  /api/context/files           — injected context files
GET  /api/profile                 — MLA profile
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
pip install fastapi uvicorn google-genai python-dotenv sentence-transformers sqlite-vec
```

Create `.env` in the project root:
```
GEMINI_API_KEY=your_key_here
```

Gemini is only needed for meeting transcript extraction. Everything else runs without it.

---

## Running

```bash
# Seed sample data (first time)
python Project/seed.py

# Start server
python -m uvicorn Project.main:app --reload

# Open dashboard
http://localhost:8000
```

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
| context_files | Commitment Engine | Injected context for RAG (proto3) |

---

## What's Next (Proto3)

- RAG Engine — embed context files + commitment history, power Chat and Suggestions pages
- Richer seed data for demo
- `/api/complaints/recent` endpoint for Log Issue page live entries

---

*Built for India Innovates 2026 — CivicNTech*
