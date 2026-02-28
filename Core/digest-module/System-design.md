# Commitment Engine — Additions Spec
## Three functions to add to engine.py

---

## What This Doc Is

The commitment engine is already built. This doc specifies three functions to add to the existing `engine.py` file. Nothing else changes — same database, same structure, just three new functions appended.

---

## Architecture & Modularity

The Digest Module is designed as a **read-heavy extension** of the Commitment Engine. It provides high-level aggregation and filtering capabilities while remaining decoupled from the ingestion logic.

### Structural Overview
- **Independent Schema Access**: Operates directly on `timely.db` (or a specified clone) using standardized SQL queries.
- **Stateless Read Layer**: Functions like `get_digest()` and `get_history()` do not maintain their own state; they compute summaries on-demand, ensuring the UI always reflects the "Ground Truth".
- **Plug-and-Play Integration**: Can be imported into any frontend (CLI, Web Dashboard, or Bot) without side effects.

### How It Works
1. **Escalation Trigger**: Every read call (`get_digest`, `get_todo_list`) internally triggers `escalate()`. This ensures that "Freshness" is guaranteed—if an item became overdue 5 minutes ago, the digest will reflect it immediately as `critical`.
2. **Computed Fields**: Fields like `was_overdue` and `days_taken` are calculated during the `SELECT` phase in Python. This saves database space and avoids data desynchronization.

---

## Function 1 — get_digest()

### One Job
Read the last 7 days of data from timely_items. Return a structured weekly summary. No LLM. No formatting. Just numbers and lists.

### Input
```python
get_digest()
# No parameters needed — always generates for the last 7 days from today
```

### What It Queries

All queries scoped to `created_at >= today - 7 days` unless noted.

```
1. New items logged this week
   COUNT(*) WHERE created_at >= week_start

2. Items resolved this week
   COUNT(*) WHERE status = 'completed' AND date(completed_at) >= week_start

3. Items resolved on time this week
   COUNT(*) WHERE status = 'completed' 
   AND date(completed_at) >= week_start 
   AND date(completed_at) <= deadline

4. Items that became overdue this week
   SELECT id, title, to_whom, deadline, ward
   WHERE status = 'pending' 
   AND deadline >= week_start 
   AND deadline < today
   ORDER BY deadline ASC

5. Total open items right now
   COUNT(*) WHERE status = 'pending'

6. Most overdue open item
   SELECT title, to_whom, deadline, ward
   WHERE status = 'pending' AND deadline < today
   ORDER BY deadline ASC
   LIMIT 1

7. Breakdown by type this week
   SELECT type, COUNT(*) 
   WHERE created_at >= week_start
   GROUP BY type

8. Open items by urgency right now
   SELECT urgency, COUNT(*)
   WHERE status = 'pending'
   GROUP BY urgency
```

### Output
```python
{
  "period": {
    "from": "2026-02-23",   # today - 7
    "to":   "2026-03-01"    # today
  },
  "new_items": {
    "total":       int,
    "commitments": int,
    "questions":   int,
    "actions":     int,
    "issues":      int
  },
  "resolved": {
    "total":        int,
    "on_time":      int,
    "late":         int,
    "resolution_rate": float   # on_time / total * 100, 0 if total is 0
  },
  "became_overdue_this_week": [
    {
      "id":       int,
      "title":    str,
      "to_whom":  str | None,
      "deadline": str,
      "ward":     str | None
    }
  ],
  "open_right_now": {
    "total":    int,
    "normal":   int,
    "urgent":   int,
    "critical": int
  },
  "most_overdue": {
    "id":           int | None,
    "title":        str | None,
    "to_whom":      str | None,
    "deadline":     str | None,
    "days_overdue": int
  }
}
```

### Notes
- Call `escalate()` at the start of `get_digest()` so urgency counts are fresh
- If no items exist for the week — return zeros, not errors
- `resolution_rate` should be 0.0 not a division error when total resolved is 0
- `most_overdue` fields should all be None if nothing is overdue

---

## Function 2 — get_history()

### One Job
Return all completed items sorted by most recently completed. Powers the historical list on the Commitments page.

### Input
```python
get_history(limit=50, offset=0)
# limit  — how many items to return, default 50
# offset — for pagination, default 0
```

### What It Queries
```sql
SELECT id, title, type, to_whom, ward, deadline, 
       completed_at, meeting_date, resolution_notes, 
       extension_count, source, source_id
FROM timely_items
WHERE status = 'completed'
ORDER BY completed_at DESC
LIMIT ? OFFSET ?
```

Also returns total count for pagination:
```sql
SELECT COUNT(*) FROM timely_items WHERE status = 'completed'
```

### Output
```python
{
  "total":  int,    # total completed items ever, for pagination
  "items": [
    {
      "id":               int,
      "title":            str,
      "type":             str,
      "to_whom":          str | None,
      "ward":             str | None,
      "deadline":         str,
      "completed_at":     str,
      "meeting_date":     str | None,
      "resolution_notes": str | None,
      "extension_count":  int,
      "was_overdue":      bool,   # computed: date(completed_at) > deadline
      "days_taken":       int,    # computed: date(completed_at) - meeting_date
      "source":           str,
      "source_id":        str
    }
  ]
}
```

### Notes
- `was_overdue` and `days_taken` are computed on read, not stored — calculate them in Python the same way `complete_item()` does
- If `meeting_date` is None, set `days_taken` to 0
- Empty history returns `{"total": 0, "items": []}`

---

## Function 3 — get_todo_list(filters)

### One Job
Existing function. Add optional filter parameters. Everything else stays identical.

### New Signature
```python
def get_todo_list(type=None, urgency=None, ward=None):
```

All three parameters are optional. If not passed — behaviour is identical to current, returns everything.

### How Filters Apply
```
type    — filter WHERE type = ?
          valid values: "commitment" / "question" / "action" / "issue"

urgency — filter WHERE urgency = ?
          valid values: "normal" / "urgent" / "critical"

ward    — filter WHERE ward = ?
          exact match on ward field
```

Filters apply to both meeting_items and issue_items.

### SQL Change
Current query:
```sql
SELECT * FROM timely_items 
WHERE status = 'pending' 
ORDER BY weight DESC, deadline ASC
```

Updated query with optional filters:
```python
query = "SELECT * FROM timely_items WHERE status = 'pending'"
params = []

if type:
    query += " AND type = ?"
    params.append(type)

if urgency:
    query += " AND urgency = ?"
    params.append(urgency)

if ward:
    query += " AND ward = ?"
    params.append(ward)

query += " ORDER BY weight DESC, deadline ASC"
cursor.execute(query, params)
```

### Output
Same schema as current `get_todo_list()`. No changes to output structure.

### Notes
- Invalid filter values should not crash — if `urgency="invalid"` is passed, query just returns empty list
- `escalate()` still called at start before filtering
- Filters stack — passing both `urgency="critical"` and `type="commitment"` returns only critical commitments

---

## Where These Go In engine.py

Append all three functions after the existing `get_stats()` function. No changes to any existing function. No changes to database schema. Just three new functions at the bottom of the file.

---

## Simplest Possible Test For Each

**get_digest():**
```
Run after test_engine.py has populated some data
Call get_digest()
Verify:
  - period.from is 7 days ago
  - new_items.total matches what was added
  - open_right_now.critical > 0 (item 2 is overdue)
  - most_overdue is item 2 (PM Awas question)
```

**get_history():**
```
Run after completing at least one item
Call get_history()
Verify:
  - total = 1
  - items[0].title = "Follow up with PWD commissioner..."
  - items[0].was_overdue = false (completed on time)
  - items[0].extension_count = 0

Call get_history(limit=1, offset=0) — verify pagination works
```

**get_todo_list(filters):**
```
Call get_todo_list() — verify same result as before (no regression)
Call get_todo_list(urgency="critical") — verify only critical items returned
Call get_todo_list(type="issue") — verify only issue items returned
Call get_todo_list(urgency="critical", type="commitment") — verify stacking works
```

---

*Commitment Engine Additions — CoPilot*
*India Innovates 2026*