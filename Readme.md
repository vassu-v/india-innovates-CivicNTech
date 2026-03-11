# SarkarSathi — AI Co-Pilot for Public Leaders & Administrators

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-database-003B57?logo=sqlite&logoColor=white)
![sentence-transformers](https://img.shields.io/badge/sentence--transformers-embeddings-orange)
![Gemini](https://img.shields.io/badge/Gemini-LLM-4285F4?logo=google&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![India Innovates](https://img.shields.io/badge/India%20Innovates-2026-purple)

> *"Every politician retires. Their experience shouldn't."*

---

## What Is This

SarkarSathi is an AI intelligence platform built for elected representatives and public administrators — MLAs, MPs, municipal councillors, and the staff who support them.

It does something deceptively simple: it gives a public leader a second brain.

One that remembers every commitment made in every meeting. One that sees when seven different citizens have complained about the same drainage problem in the same ward, even if they came in on different days through different channels. One that knows when a promise made six weeks ago is overdue and getting critical. One that can answer "am I ready for tomorrow's meeting?" with actual data about the constituency — not a generic response.

This is not a productivity app. It is institutional memory — the kind that doesn't leave when a PA resigns, doesn't forget when a term ends, and doesn't soften uncomfortable truths about a leader's own track record.

---

## The Problem It Solves

India has 4,120 MLAs. 543 MPs. Thousands of municipal councillors. Every single one of them governs using roughly the same system: a WhatsApp group, a PA with a diary, and an Excel sheet that is always out of date.

The consequences are not abstract:

- Commitments made in meetings are forgotten. Citizens come back angrier.
- The same complaint arrives through five channels and nobody realises it is the same issue.
- When staff changes, institutional knowledge walks out the door.
- The same problems recur in the same wards year after year because nobody is tracking patterns.
- Leaders govern reactively — responding to crises instead of preventing them — because they have no system for seeing what is coming.

Governance isn't failing because leaders don't care. It's failing because they have no infrastructure.

SarkarSathi is that infrastructure.

---

## The Full System

```
┌─────────────────────────────────────────────────┐
│                    DATA IN                      │
│                                                 │
│  Meeting audio / transcripts / Parliament docs  │
│  Complaints — email (auto) or staff form        │
│  Constituency data via plain text injection     │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│               INTELLIGENCE CORE                 │
│                                                 │
│  Ingestion Engine  — segments + classifies      │
│  Issue Engine      — clusters by meaning        │
│  Commitment Engine — tracks promises + weight   │
│  Digest Engine     — surfaces patterns          │
│  RAG Engine        — answers from memory        │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                   DATA OUT                      │
│                                                 │
│  To-Do List     — weighted, live, prioritised   │
│  Commitment Tracker — accountability mirror     │
│  Chat Interface — natural language to all data  │
│  Suggestions    — on-demand strategic advice    │
│  Digest         — weekly reflection, patterns   │
└─────────────────────────────────────────────────┘
```

Full system architecture diagram: [`docs/full-system-mermaid-diagram.png`](docs/full-system-mermaid-diagram.png)

---

## Four Database Architecture

The intelligence layer is built on four independent data stores, each with a single clearly defined responsibility. No single database can answer a complex governance question. All four together can.

**DB1 — Static Constituency**
Permanent ground truth. Ward demographics, infrastructure status, development projects, scheme penetration rates, historical record. Loaded on every query as mandatory base context. Never written to by AI — only staff can update it. This keeps it trustworthy.

**DB2 — RAG Historical Facts**
Institutional memory. Meeting summaries, decisions taken, complaint issue clusters with weights, resolved commitments injected from DB3 on completion. Grows automatically over time with no manual effort. This is the brain that compounds — the longer the system is used, the more useful it becomes.

**DB3 — Timely Commitments**
Time-sensitive items only. Everything here has a deadline. Weight escalates automatically the longer an item is overdue. Nothing silently disappears. On completion, the full record — what was promised, to whom, how long it took, whether it was late — is permanently injected into DB2 as institutional memory.

**DB4 — Static Complaints**
Raw individual complaint records. Permanent audit trail. Linked to the issue clusters in DB2. Never deleted. Used for citizen follow-up, accountability reporting, and pattern analysis over time.

---

## The Hardware Concept

The complete SarkarSathi system includes a proposed physical recording device — a small clip-on unit designed for a lapel or tie during meetings.

**What it is:** Raspberry Pi Zero W + microphone module + 3D printed enclosure. Estimated cost ₹2,000–3,000.

**What it does:** Records audio. That is its entire job.

**What it deliberately does not do:** Process anything. Transmit anything wirelessly. Connect to any network during use. The device is intentionally dumb — a trusted input mechanism, not a surveillance tool.

This design is not accidental. A politician's meetings contain their most sensitive data — private negotiations, constituency intelligence, personal conversations. The privacy of that data cannot depend on a policy or a configuration setting that can be changed. It must depend on physical architecture.

The device has no WiFi transmission capability during recording. Data moves only when the politician physically plugs it into their laptop. The device is incapable of leaking data because it has no mechanism to transmit data.

> Hardware device is a proposed component. The current deployment demonstrates the intelligence layer — the full software pipeline. The device replaces the manual file upload step in production.

---

## Privacy Architecture

```
Audio recordings      →  never leave the device
Meeting transcripts   →  never leave the laptop
Constituency data     →  never leave the laptop
Complaint details     →  never leave the laptop
Commitments           →  never leave the laptop
AI responses          →  generated locally, never sent anywhere
```

This system is architecturally incapable of leaking data during local operation. Not because of a policy. Not because of a setting. Because there is no network connection to leak through.

The external Gemini API used in the current deployment is a deliberate development decision, not a production choice. See Design Decisions for the full reasoning and the production path.

---

## Intelligence Layer — Five Engines

### Ingestion Engine

Takes raw meeting transcript text. Segments it into meaningful chunks. Classifies each chunk using prototype-based embedding similarity against a library of governance-specific intent patterns. Categories: commitment, question, action, context, noise.

Commitments and questions route to the Commitment Engine. Facts and context route to the RAG Engine. Noise is discarded.

**Why prototype-based, not zero-shot:** Zero-shot classification models are trained on generic text. Indian governance meetings are not generic text. Phrases like "PWD commissioner", "Ward 42 drainage", "PM Awas Yojana", "Janata Darbar" are meaningless to a model that has never seen governance context. Prototype matching against a curated library of governance-specific phrases is 20x faster and significantly more accurate for this domain. The prototypes can be updated without retraining anything — just change the phrase list.

Ingestion engine diagram: [`docs/commitment-mermaid-diagram.png`](docs/commitment-mermaid-diagram.png)

### Issue Engine

Takes a citizen complaint in. Embeds the description text using sentence-transformers. Searches existing clusters within the same ward by cosine similarity. Above threshold: adds weight to the existing cluster, updates the summary if the new complaint adds meaningful context. Below threshold: creates a new cluster. Stores the raw complaint permanently regardless.

Ward masking is a deliberate design decision — a drainage complaint in Ward 42 must never match a drainage cluster in Ward 17, even if the language is similar. The ward is part of the identity of the issue, not just metadata.

Issue engine diagram: [`docs/issue-engine.png`](docs/issue-engine.png)

### Commitment Engine

Receives classified chunks from the Ingestion Engine and cluster updates from the Issue Engine. Extracts structured data from meeting text — title, deadline, to whom, ward. Tracks deadlines. Escalates weight automatically as items go overdue.

Weight escalation ladder:
```
Before deadline    →  W1  →  normal
1–3 days overdue   →  W2  →  normal
4–7 days overdue   →  W3  →  urgent
8–14 days overdue  →  W5  →  critical
15+ days overdue   →  W8  →  critical
```

On completion, generates a structured fact string capturing the full history of the commitment — what was promised, when, to whom, whether it was delivered on time, how many extensions were granted — and passes it to the RAG Engine for permanent storage.

Issue engine complaint clusters are intentionally excluded from weight re-escalation. For complaints, weight means number of citizens affected. For commitments, weight means days overdue. These are semantically different uses of the same field. Re-escalating complaint weights by days would corrupt the meaning of the To-Do list.

### Digest Engine

Pure SQL. No LLM. Generates weekly summary: new items by type, resolved vs overdue, on-time resolution rate, most overdue item, urgency breakdown, items that became overdue this week.

The decision to use no LLM here is deliberate. A summary of a leader's own performance data should be numbers, not prose. Numbers do not soften. They do not flatter. They do not editorialize. The politician sees exactly what happened.

### RAG Engine

Hybrid retrieval — vector search for historical facts combined with live SQL for current state.

Pure vector search is insufficient for a governance assistant. A query like "am I ready for tomorrow's meeting?" requires both historical context (what has happened before in this ward, how reliable is this department, what patterns exist) and live data (what is currently overdue, what complaints are open right now). These are different retrieval mechanisms and both are necessary.

Four context layers assembled on every query:
- **Layer 1 — always-on:** profile + live digest snapshot + top open items. No retrieval. Always fresh.
- **Layer 2 — vector search:** top-k semantically relevant facts from completed commitments and injected context files
- **Layer 3 — live SQL:** open complaint clusters + current pending items
- **Layer 4 — chat history:** recent conversation turns for continuity

Chat and Suggestions are currently in active development.

---

## Design Decisions

Every technical choice in this system was made deliberately. This section explains the reasoning.

### SQLite over PostgreSQL in this deployment
PostgreSQL requires a running server, configuration, and credentials — three additional failure points on demo day and three barriers to getting a politician's staff to actually run the system. SQLite is a single portable file. The schema, query patterns, and engine logic are identical between the two. Migrating to PostgreSQL is a one-line configuration change, not an architectural change. pgvector replaces sqlite-vec for embeddings in production.

### Gemini API over local LLM in this deployment
Local LLMs (Ollama + Phi-3 Mini or Llama 3) require 8–16GB RAM and vary in performance across hardware. Gemini gives consistent quality during development without hardware dependency. This is a development convenience and nothing more. Before any deployment involving real political data, this must be replaced with a local model. The entire privacy value proposition of this system depends on data never reaching an external API. Recommended production path: Ollama for easy setup, Sarvam AI for Hindi and regional language support.

### sentence-transformers over heavier embedding models
all-MiniLM-L6-v2 is 80MB, runs entirely on CPU, loads in under 3 seconds, and produces 384-dimensional embeddings that are sufficient for the similarity thresholds used in complaint clustering. Larger models add latency and RAM requirements with no meaningful accuracy improvement for this specific use case.

### No LangChain
The intelligence in this system comes from context assembly and prompt design, not orchestration framework features. LangChain adds abstraction over what are, at this scale, straightforward API calls and SQL queries. Keeping orchestration explicit keeps the codebase readable, debuggable, and accessible to contributors who are not LangChain specialists. This decision is revisable if the agent complexity grows.

### Prototype-based classification over zero-shot
Covered in the Ingestion Engine section above. The short version: generic models fail on domain-specific language. Domain-specific prototypes succeed. The prototypes are editable without retraining. This is a better architecture for a system that needs to work reliably in the field.

### Complaint weight not re-escalated by time
Weight means something different in each engine. In the Issue Engine, weight = number of citizens who raised this complaint. In the Commitment Engine, weight = urgency based on days overdue. Allowing the Commitment Engine to re-escalate complaint weights by days overdue would corrupt the meaning of the weight field and produce incorrect prioritisation in the To-Do list. Urgency ownership stays with the originating engine.

---

## What's Running in This Deployment

The intelligence core — the brain of SarkarSathi — is fully operational.

| Component | Status |
|-----------|--------|
| Ingestion Engine | Live — transcript → classified chunks → To-Do |
| Issue Engine | Live — complaint → embedding → cluster → To-Do |
| Commitment Engine | Live — extraction + weight escalation |
| Digest Engine | Live — weekly summary, pure SQL |
| Auto-Escalation | Live — background task, runs every hour |
| Home Dashboard | Live — real data from all engines |
| To-Do List | Live — weighted, ranked, complete/extend wired |
| Commitment Tracker | Live — active list + resolved history |
| Digest Page | Live — weekly breakdown + drilldown overlays |
| Upload Meeting | Live — .txt transcript → extraction → To-Do |
| Log Issue | Live — complaint → cluster → To-Do |
| Profile | Live — persists to DB |
| Context Injection | Live — .txt files stored for RAG |
| Chat Interface | In active development |
| Suggestions | In active development |

---

## Live Deployment

An earlier version of SarkarSathi is accessible online.

> **Note:** The live deployment reflects an earlier build of the system. It does not include several features present in the current codebase — including the enriched seed data, ward normalisation, recent complaints feed, and various stability improvements made since that deployment. Gemini API extraction is not active in the live deployment. The deployment is provided for reference and to demonstrate the dashboard interface. For the full current system, run locally using the instructions below.

---

## Tech Stack

```
Language        Python 3.11
Backend         FastAPI + uvicorn
Database        SQLite  (production: PostgreSQL + pgvector)
Embeddings      sentence-transformers — all-MiniLM-L6-v2 (offline, CPU)
Vector Search   sqlite-vec  (production: pgvector)
LLM             Gemini API  (production: Ollama + local model)
Frontend        HTML / CSS / JS  (production: React + Tailwind)
Testing         Playwright — automated E2E verification suite
```

---

## Setup

```bash
pip install fastapi uvicorn google-genai python-dotenv sentence-transformers sqlite-vec playwright
```

Create `.env` in the project root:
```
GEMINI_API_KEY=your_key_here
```

Gemini is required only for meeting transcript extraction. The Issue Engine, Digest Engine, escalation logic, and all dashboard reads run fully offline without an API key.

---

## Running

```bash
# Seed the database with demo constituency data
PYTHONPATH=Project python Project/seed.py --reset

# Start the server
PYTHONPATH=Project python -m uvicorn main:app --app-dir Project --port 8000
```

Visit [http://localhost:8000](http://localhost:8000)

---

## Verification

```bash
# Server must be running in a separate terminal first
python Project/verify_dashboard.py
```

The Playwright verification script navigates every page, performs real actions — completing items, extending deadlines, logging complaints, uploading transcripts — and saves screenshots at each step.

---

## Demo Constituency

All seed data is fictional and designed for demonstration purposes. The demo MLA is Shri Rajendra Kumar Verma, Ward 42 South Delhi, Indian National Congress. Six wards, 2,70,000 population, 1,82,400 registered voters.

The anchor demo issue is a recurring drainage canal overflow in Ward 42 — three consecutive years of monsoon flooding, pre-monsoon cleaning skipped, PWD slow via department routing but responsive when escalated directly to Commissioner Singh. This is the story the dashboard tells. Every number on the screen comes from the seeded data, not from hardcoded HTML.

---

## Official Problem Statement

> **Domain:** Digital Democracy — India Innovates 2026

*"Developing a secure hardware-software intelligence assistant that summarizes documents and meetings, drafts speeches and official responses, tracks constituency or community data, manages schedules, and provides real-time insights to support faster and more informed decision-making."*

---

## The Bigger Picture

What is running today is the intelligence layer. The commitment tracking logic, the complaint clustering engine, the weight escalation system, the hybrid RAG design — these are the hard problems. They work identically whether the database is SQLite on a laptop or PostgreSQL on a government server. The deployment stack is an engineering decision. The intelligence is the innovation.

The hardware device, full local LLM pipeline, multilingual support, and production frontend are the next layer built on this foundation. The foundation is solid.

India's governance infrastructure gap is not a political problem or a funding problem. It is a systems problem. Public leaders at the constituency level — the people closest to the citizens — have no intelligent support infrastructure whatsoever. SarkarSathi is a starting point for changing that.

> *"650 MLAs. Millions of constituents. Zero intelligent support."*
>
> SarkarSathi exists to change that.

---

*CivicNTech — github.com/CivicNTech*
*India Innovates 2026 | Digital Democracy Domain*
