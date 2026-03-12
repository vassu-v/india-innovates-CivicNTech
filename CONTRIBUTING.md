# Contributing to SarkarSathi

Hey — glad you're here.

SarkarSathi is a local-first governance intelligence system built on the belief that public leaders deserve better infrastructure. If you're reading this, you're already part of that.

> **Even if you're just thinking about contributing — that matters.** Browse the issues, poke around the codebase, ask a question. You don't need to ship code to be useful.

This document exists to make sure contributions are useful, not just well-intentioned. Worth a read before opening a PR.

---

## What This Project Is

An AI co-pilot for elected representatives and public administrators. Commitment tracking, complaint clustering, institutional memory. Fully offline. No cloud dependency in production.

The intelligence layer is the core innovation — not the frontend, not the deployment stack.

---

## What Needs Work

These are the real gaps. Pick one.

**Good first issues**
- Add multilingual support for complaint input (Hindi, Tamil, Bengali) - least priority right now
- Write unit tests for the weight escalation ladder in the Commitment Engine
- Add a `docker-compose.yml` for one-command local setup
- Improve ward normalisation — currently basic string matching, needs fuzzy matching - would be a great issue to solve

**Harder problems**
- Replace Gemini API with a fully local LLM via Ollama (this is the production path — see Design Decisions in README)
- Migrate from SQLite + sqlite-vec to PostgreSQL + pgvector
- Build the Chat Interface (RAG Engine is under-development, frontend is not)
- Add Hindi/regional language support via Sarvam AI

---

## Before You Start

- Open an issue first if you are building something non-trivial. Avoid duplicate work.
- Check existing issues and PRs before starting.
- If you are fixing a bug, describe what caused it, not just what you changed.

---

## How to Run Locally

```bash
pip install fastapi uvicorn google-genai python-dotenv sentence-transformers sqlite-vec playwright

# Create .env in project root
echo "GEMINI_API_KEY=your_key_here" > .env

# Seed demo data
PYTHONPATH=Project python Project/seed.py --reset

# Start server
PYTHONPATH=Project python -m uvicorn main:app --app-dir Project --port 8000
```

Gemini API key is only required for meeting transcript extraction. Everything else runs offline.

Run the verification suite after any change:

```bash
python Project/verify_dashboard.py
```

---

## Code Standards

This codebase has no LangChain, no unnecessary abstraction, and no magic. Keep it that way.

- Every technical decision should be explainable. If you cannot explain why you made a choice, reconsider the choice.
- Explicit over implicit. The orchestration logic is intentionally readable.
- If you add a dependency, justify it. The current stack is lean on purpose.
- Domain-specific language matters here. Read the Design Decisions section in the README before touching the engine logic.

---

## PR Guidelines

- One problem per PR. Do not bundle unrelated changes.
- Update the README if your change affects architecture or design decisions.
- Screenshots or test output for any frontend or engine changes.
- Keep commit messages factual. What changed and why, not just what.

---

## What Not to Build

- A cloud sync feature — this would break the entire privacy model
- A React rewrite of the frontend before the Chat and Suggestions engines are complete
- Abstractions over the database layer that obscure what queries are actually running

If you think one of these is wrong, open an issue and argue for it. The design decisions are deliberate but not sacred.

---

## Questions

Open an issue with the `question` label. No question is too small if it is genuine — genuinely. Some of the best design conversations start with "wait, why does this work this way?"

---

*SarkarSathi — because governance infrastructure should exist.*
