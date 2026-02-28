# CoPilot
### AI Intelligence System for Public Leaders & Administrators
> **Status: Under Active Development** — India Innovates 2026

---

```
Every politician retires.
Their experience shouldn't.
```

---

## The Problem

India has 4,120 MLAs. 543 MPs. Thousands of municipal councillors.

Every single one of them walks into office each morning facing the same chaos —

Complaints arriving through five different channels with no unified view. Meetings happening back to back with commitments made verbally that nobody tracks. Constituency data scattered across government portals that nobody can easily query. Staff that changes, taking institutional knowledge with them. Promises made in January forgotten by March.

**Governance isn't failing because leaders don't care. It's failing because they have no system.**

A politician's most critical tool today is a WhatsApp group and a PA with a diary.

---

## Official Problem Statement

> *"Developing a secure hardware-software intelligence assistant that summarizes documents and meetings, drafts speeches and official responses, tracks constituency or community data, manages schedules, and provides real-time insights to support faster and more informed decision-making."*

**Domain:** Digital Democracy — India Innovates 2026  
**Track:** AI Co-Pilot for Public Leaders & Administrators

---



## The Idea

A fully offline, privacy-first AI intelligence platform that gives public leaders the one thing they've never had —

**A second brain that knows everything they know, remembers everything they forget, and never gossips.**

CoPilot captures meetings. Clusters complaints intelligently. Tracks every commitment made with weight and deadline. Lets a leader query their entire constituency history in plain language. And does all of it without a single byte leaving their laptop.

Not a chatbot. Not a dashboard. An institutional memory that compounds over time.

---

## What It Does

```
┌─────────────────────────────────────────────────────┐
│                   DATA IN                           │
│                                                     │
│  Meeting audio / transcripts / Parliament docs      │
│  Complaints via email (auto) or staff form          │
│  Constituency data via plain text injection         │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                INTELLIGENCE CORE                    │
│                                                     │
│  Issue Engine      — clusters complaints by meaning │
│  Commitment Engine — tracks promises with weight    │
│  Extraction Engine — pulls structure from meetings  │
│  RAG Engine        — answers from institutional mem │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   DATA OUT                          │
│                                                     │
│  To-Do List        — weighted, prioritized, live    │
│  Commitment Tracker — personal accountability mirror│
│  Chat Interface    — natural language to all data   │
│  Suggestions       — on-demand strategic advice     │
│  Digest            — daily reflection, weekly review│
└─────────────────────────────────────────────────────┘
```

---

## Why This Is Different

| Problem | Generic AI Tools | CoPilot |
|---------|-----------------|---------|
| Data privacy | Cloud-based, your data trains their models | Fully offline, zero data leaves laptop |
| Constituency context | Knows nothing about your ward | Pre-loaded with your specific data |
| Memory | Forgets every session | Permanent institutional memory |
| Meeting capture | Manual input only | Audio → transcript → structured extraction |
| Complaint management | Not built for this | Semantic clustering with weight escalation |
| Accountability | None | Commitment tracking with pattern recognition |

---

## Architecture — Four Database Design

```
DB1  PostgreSQL   Static constituency ground truth
                  Always loaded on every query
                  Never written to by AI — staff controlled

DB2  pgvector     RAG historical facts + complaint clusters
(inside           What happened, patterns, resolved history
PostgreSQL)       Grows automatically over time

DB3  PostgreSQL   Timely commitments with deadlines
                  Weight escalates when overdue
                  Injects into DB2 on resolution

DB4  PostgreSQL   Raw individual complaints
                  Permanent audit trail
                  Linked to DB2 clusters
```

One PostgreSQL instance. pgvector extension handles embeddings inline. No separate vector database needed.

---

## Repository Structure

```
copilot/
│
├── core/                        # All intelligence modules — independent, testable
│   ├── issue_engine/            # Complaint intake, embedding, clustering, weighting
│   ├── commitment_engine/       # Timely items, deadlines, weight escalation
│   ├── extraction_engine/       # Meeting transcript → structured commitments + facts
│   ├── rag_engine/              # Query handler across all four databases
│   └── digest_engine/           # Daily and weekly digest generation
│
├── project/                     # Packaged final product — uses core modules
│   ├── api/                     # FastAPI backend
│   ├── dashboard/               # React frontend
│   └── config/                  # Environment, thresholds, model config
│
└── docs/                        # To be populated
    ├── system_design.md         # Full architecture decisions
    ├── module_contracts.md      # Input/output specs per module
    └── setup.md                 # Local setup guide
```

### `core/`
Each folder is a standalone module with a single responsibility. Designed so any module can be tested in isolation, replaced, or upgraded without touching anything else. The issue engine doesn't know the commitment engine exists. The RAG engine doesn't care how complaints were clustered. Clean boundaries.

### `project/`
The assembled product. Imports from `core/`, exposes the API, serves the dashboard. This is what gets demoed and deployed. Think of `core/` as the engine parts and `project/` as the assembled car.

### `docs/`
To be populated as modules stabilise. System design document and module contracts will live here.

---

## Build Order

Modules are being built in order of independence — simplest and most self-contained first.

```
Phase 1 — Issue Engine          ← starting here
Phase 2 — Commitment Engine
Phase 3 — Extraction Engine
Phase 4 — RAG Engine
Phase 5 — Digest Engine
Phase 6 — API + Dashboard integration
```

Each phase produces a working, testable module before the next begins.

---

## Tech Stack

```
Language          Python 3.11
Database          PostgreSQL + pgvector extension
Embeddings        sentence-transformers — all-MiniLM-L6-v2 (offline)
Orchestration     LangChain
Frontend          React + Tailwind CSS
API               FastAPI
```

---

## ⚠️ Production Note — LLM

Currently using an **external LLM API** for language generation during development. This is a temporary decision for build speed only.

**Before any production or sensitive deployment, this must be replaced with a local model.**

Recommended paths:
- **Ollama** — easiest local setup, runs Phi-3 Mini or Llama 3 on CPU
- **vLLM** — better performance, needs GPU
- **Sarvam AI** — Indian LLM, ideal for Hindi + regional language support at scale

No politician's data should ever touch an external LLM endpoint. The entire value proposition of this system is that data stays local. The external API is a development convenience and nothing more.

This will be replaced before the final build is complete.

---

## Privacy By Design

```
Audio recordings    →   never leave the laptop
Meeting transcripts →   never leave the laptop
Constituency data   →   never leave the laptop
Complaint details   →   never leave the laptop
Commitments         →   never leave the laptop
AI responses        →   generated locally, never sent anywhere
```

The system is architecturally incapable of leaking data during local operation. There is no network connection to leak through. This is not a policy or a setting — it is a structural property of the system.

---

## ⚠️ Scope — This Version

This iteration is a **pure software build.** The following are explicitly out of scope and will be considered in a future version:

- No voice recording hardware device
- No wearable or physical attachment
- No audio capture of any kind
- No real-time transcription from microphone

Meeting intelligence in this version works via **manual file upload only** — audio files, text transcripts, or Parliament session documents uploaded by staff. The intelligence layer is the focus. Hardware is a future layer on top of it.

---

## Context

Built for **India Innovates 2026** — Domain: Digital Democracy  
Problem statement: AI Co-Pilot for Public Leaders & Administrators  
Venue: Bharat Mandapam, New Delhi — 28 March 2026

---

*Under active development. Contributions and feedback welcome.*