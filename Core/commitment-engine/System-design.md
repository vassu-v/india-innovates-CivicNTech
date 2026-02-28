# Commitment Engine — System Design (Final MVP)

## One Job

Receive raw classified chunks from the Ingestion Engine and complaint clusters from the Issue Engine. Extract structured to-do items using Gemini. Store them. Escalate their weight over time. Serve a clean prioritised to-do list. Track commitment patterns.

This module is a **pure processing engine** — it handles the full lifecycle of actionable commitments from raw meeting text through to completion, with no external dependencies beyond SQLite and the Gemini API.

---

## Repository Structure

```
commitment-engine/
├── engine.py          ← Core logic — all six functions + DB + Gemini extraction
├── cli.py             ← Interactive CLI for manual use and demo
├── test_engine.py     ← Verification script (the "Simplest Possible Test")
├── timely.db          ← SQLite database (auto-created on first run)
├── .env               ← API key (never committed to git)
└── System-design.md   ← This file
```

---

## Architecture — Two Layers

```
LAYER 1 — Extraction       (needs Gemini)
  Raw text in
  Structured item out       gemini-3-flash-preview

LAYER 2 — Management       (no LLM, pure SQL)
  Store  →  Escalate  →  Serve  →  Track
```

**These two layers are independent.** Layer 2 works even if Layer 1 fails — it stores raw text as the title and infers a deadline from the item type. The engine never crashes on a bad API response.

---

## The Database — `timely.db`

One table. Everything lives here.

```
TABLE timely_items

  id                integer   primary key autoincrement
  title             text      clean short title (from Gemini or raw fallback)
  raw_text          text      original sentence always preserved
  type              text      commitment / question / action / issue
  source            text      meeting / issue_engine / manual
  source_id         text      meeting filename or cluster id
  to_whom           text      person or department, nullable
  ward              text      nullable
  deadline          date
  weight            integer   default 1
  urgency           text      normal / urgent / critical
  status            text      pending / in_progress / completed
  extension_count   integer   default 0
  extraction_failed boolean   default false
  meeting_date      date      when the meeting happened
  created_at        timestamp
  completed_at      timestamp nullable
  resolution_notes  text      nullable
  injected_to_rag   boolean   default false
```

---

## The Six Functions

All six functions are importable individually. Each does exactly one thing.

### `init_db()`
Creates `timely.db` and the `timely_items` table if they don't exist. Safe to call multiple times.

### `add_item(input_data: dict) → item_id`
Accepts two input shapes:

**Meeting item (from Ingestion Engine):**
```python
{
  "text":         "I will personally follow up with PWD commissioner today",
  "type":         "commitment",          # commitment / question / action
  "meeting_date": "2026-03-01",
  "source_id":    "ward8_meeting.m4a"
}
```
Calls Gemini to extract `title`, `deadline`, `to_whom`, `ward`. Falls back gracefully if API fails.

**Issue cluster (from Issue Engine):**
```python
{
  "cluster_id":      42,
  "cluster_summary": "Drainage overflow Ward 42",
  "ward":            "Ward 42",
  "weight":          6,
  "urgency":         "critical"
}
```
No Gemini call needed — summary is already clean. Weight and urgency are preserved as-is.

### `escalate()`
Recalculates `weight` and `urgency` for all pending meeting items based on days overdue:

```
Before deadline        →  weight 1  →  normal
1–3 days overdue       →  weight 2  →  normal
4–7 days overdue       →  weight 3  →  urgent
8–14 days overdue      →  weight 5  →  critical
15+ days overdue       →  weight 8  →  critical
```

> **Design decision:** Issue-engine items are excluded from escalation. Their weight is owned by the Issue Engine at ingestion time. `timely.db` defers urgency back to the source.

### `get_todo_list() → dict`
Calls `escalate()` first, then returns all pending items sorted by weight descending. Two separate lists — meeting items and issue items — in one response:

```python
{
  "meeting_items": [ { id, title, type, to_whom, ward, deadline,
                       weight, urgency, days_overdue, source_id, meeting_date } ],
  "issue_items":   [ { id, title, type, ward, weight, urgency, cluster_id } ]
}
```

### `complete_item(item_id, resolution_notes="") → fact_string`
Marks the item completed. Generates a structured string for the RAG Engine:

```
Commitment: Follow up with PWD commissioner to start work
To: PWD commissioner
Made: 2026-03-01
Deadline: 2026-03-05
Completed: 2026-03-01T14:32:00
Days taken: 0
Was overdue: no
Extensions: 0
```

Sets `injected_to_rag = true`. Item stays in DB forever — never deleted. Guards against double-completion (returns `None` if already completed).

### `extend_item(item_id, new_deadline)`
Updates the deadline. Increments `extension_count`. Resets weight to 1 (fresh escalation from new deadline). Status stays `pending` — item remains in the to-do list.

### `get_stats() → dict`
Pure SQL. No LLM. Powers the Commitment Tracker dashboard page:

```python
{
  "this_month": {
    "total_made":        int,
    "resolved_on_time":  int,
    "currently_overdue": int,
    "resolution_rate":   float
  },
  "all_time": {
    "avg_days_to_resolve":   float,
    "extension_rate":        float,
    "most_reliable_contact": str
  },
  "by_department": [ { name, total, on_time, avg_days } ]
}
```

---

## Gemini Extraction

**Model:** `gemini-3-flash-preview`
**One call per meeting item.** Issue items never need extraction.

**Prompt extracts:** `title`, `deadline`, `to_whom`, `ward`, `type`

**Deadline inference if not explicit:**
- `commitment` → 7 days from meeting date
- `question` → 3 days from meeting date
- `action` → 5 days from meeting date

**Fallback on any failure** (API error, bad JSON, quota exceeded): raw text is stored as the title, deadline is inferred from type, `extraction_failed` flag is set to `true`. The engine never crashes.

---

## Setup

### Requirements

```
google-genai       — Gemini API (new SDK)
python-dotenv      — load API key from .env
sqlite3            — built into Python, no install
```

```bash
pip install google-genai python-dotenv
```

### `.env`

```
GEMINI_API_KEY=your_key_here
```

API key loaded from `.env` via `python-dotenv`. Never hardcoded. Never committed.

---

## Usage

### Interactive CLI

```bash
python cli.py
```

Menu options:
1. Add meeting item → Gemini extracts structure live
2. Add issue cluster → Direct store from Issue Engine format
3. View To-Do list → Escalation applied live, two clean lists
4. Complete an item → Generates RAG fact string
5. Extend deadline → Resets weight to 1
6. Run escalation manually → For demo: show weight jump live
7. View stats → Dashboard-ready numbers
8. Reset database

### Run the verification test

```bash
python test_engine.py
```

Runs the full "Simplest Possible Test" from the system design:
- Adds a meeting commitment, a backdated question (to trigger critical escalation), and a fake issue cluster
- Calls `escalate()`, verifies sorting and grouping
- Completes item 1, verifies the RAG fact string
- Prints stats

---

## Integration — How to Connect This to Other Engines

### From the Ingestion Engine

```python
from engine import add_item

# Called for every commitment / question / action chunk classified
item_id = add_item({
    "text":         chunk["text"],
    "type":         chunk["type"],        # "commitment" / "question" / "action"
    "meeting_date": chunk["meeting_date"],
    "source_id":    chunk["source_id"]
})
```

### From the Issue Engine

```python
from engine import add_item

# Called when a cluster crosses the weight threshold for escalation
item_id = add_item({
    "cluster_id":      cluster["id"],
    "cluster_summary": cluster["summary"],
    "ward":            cluster["ward"],
    "weight":          cluster["weight"],
    "urgency":         cluster["urgency"]
})
```

### From the Dashboard (To-Do page)

```python
from engine import get_todo_list

todo = get_todo_list()
# todo["meeting_items"] → render commitment cards
# todo["issue_items"]   → render issue cards
```

### From the Dashboard (Tracker page)

```python
from engine import get_stats

stats = get_stats()
# stats["this_month"]    → KPI cards
# stats["by_department"] → department table
```

### From the Dashboard (Mark Complete button)

```python
from engine import complete_item

fact_string = complete_item(item_id, resolution_notes="Completed follow-up.")
# Pass fact_string to RAG Engine: rag_engine.store_fact(fact_string)
```

### From the Digest Engine (direct SQL read)

The Digest Engine reads `timely_items` directly via SQL — no function call needed:

```python
import sqlite3

conn = sqlite3.connect("path/to/timely.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM timely_items WHERE status = 'pending' ORDER BY weight DESC")
items = cursor.fetchall()
```

---

## Modularity

The engine is fully self-contained:

- **No shared state** — everything is in `timely.db`, a single portable file
- **No required integrations** — works standalone via CLI with no other engine running
- **Swappable LLM** — change the model name in `extract_with_gemini()` to use any Gemini model
- **Swappable DB path** — change `DB_PATH` constant to point to any location
- **Each function is independently importable** — use only what you need; `get_todo_list` doesn't require `add_item` to have been called through the engine
- **Crash-safe extraction** — the Gemini layer failing never affects the storage layer

---

*Commitment Engine — CoPilot System Design*
*India Innovates 2026*