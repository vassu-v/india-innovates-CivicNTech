# Suggestions Agent — System Design
## SarkarSathi Finalé
---

## One Job

When the MLA clicks "Generate Suggestions", run a 3-round agentic analysis loop across all governance data, call read-only database tools autonomously when needed, and return 3-4 specific data-backed recommendations with a full reasoning trace the user can inspect.

This is not a single Gemini call with a good prompt. It is a lightweight agent with tool-calling capability and transparent reasoning.

---

## What Makes This Different From Chat

| Chat | Suggestions Agent |
|------|------------------|
| Responds to a user question | Proactively analyses the full situation |
| Single Gemini call | Up to 3 rounds with tool calls between |
| Returns an answer | Returns structured recommendations + reasoning trace |
| User drives the query | Agent decides what data it needs |
| Fast (~2-3s) | Slower by design (~10-15s) |

---

## The Agent Loop

```
User clicks Generate Suggestions
        │
        ▼
CONTEXT ASSEMBLY (always-on, no retrieval)
  → Profile
  → Digest snapshot
  → ALL critical + urgent pending items
  → Top 5 complaint clusters by weight
  → AI memory notes (ai_memory table)
        │
        ▼
ROUND 1 — ANALYSIS
  Gemini receives: always-on context + tool descriptions
  Gemini responds with either:
    → TOOL_CALL: tool_name | argument
    → READY: sufficient context, proceed to generate
  Thinking captured → trace entry added
        │
        ▼
ROUND 2 — TOOL RESULT + OPTIONAL SECOND CALL
  If Round 1 called a tool:
    → Execute DB query (read-only)
    → Feed result back to Gemini
    → Gemini responds: TOOL_CALL or READY
  If Round 1 was READY:
    → Skip to Round 3
  Thinking captured → trace entry added
        │
        ▼
ROUND 3 — FINAL GENERATION (hard cap)
  Regardless of agent state — this is always final
  No more tool calls accepted
  Gemini generates structured JSON suggestions
  Thinking captured → trace entry added
        │
        ▼
RESPONSE RETURNED
  suggestions + thinking_trace + rounds_used + tools_called
```

Maximum 3 Gemini calls. Maximum 3 tool calls. Hard caps, no exceptions.

---

## Always-On Context

Assembled once before Round 1. Injected into every round unchanged.

```
=== MLA PROFILE ===
Name, party, constituency, Janata Darbar schedule

=== LIVE DIGEST ===
Resolution rate this week
Critical items: N
Urgent items: N
Most overdue: [title] — N days

=== ALL CRITICAL + URGENT ITEMS ===
[For each item, sorted by weight DESC]
- [URGENCY] Title | Ward | To: Dept | N days overdue | Extensions: N

=== TOP COMPLAINT CLUSTERS ===
[Top 5 by weight]
- Summary | Ward | Weight | Urgency | Days open

=== AI MEMORY NOTES ===
[All entries from ai_memory table, newest first]
- [topic]: content (learned: timestamp)
```

This is the base. Every round sees this. Tool results are added on top.

---

## Read-Only Tools

Six tools available to the agent. All are read-only SQL queries. No INSERT, UPDATE, or DELETE ever. Each result is capped at 10 rows.

```
TOOL 1: get_ward_history(ward)
  PURPOSE: Full commitment + issue history for a specific ward
  QUERY:   SELECT title, type, status, deadline, completed_at,
                  urgency, to_whom, extension_count
           FROM timely_items
           WHERE ward = ?
           ORDER BY created_at DESC LIMIT 10
  WHEN USED: Agent wants ward-specific historical context

TOOL 2: get_department_track_record(department)
  PURPOSE: How reliable is a specific department/contact
  QUERY:   SELECT title, status, deadline, completed_at,
                  extension_count, urgency
           FROM timely_items
           WHERE to_whom = ?
           ORDER BY created_at DESC LIMIT 10
  WHEN USED: Agent wants to assess if escalating to a dept
             is likely to work

TOOL 3: get_overdue_items(urgency)
  PURPOSE: Full list of overdue items at a specific urgency
  QUERY:   SELECT title, ward, to_whom, deadline, weight,
                  extension_count
           FROM timely_items
           WHERE status = 'pending' AND urgency = ?
           ORDER BY weight DESC LIMIT 10
  WHEN USED: Agent wants deeper look at critical or urgent pile

TOOL 4: get_complaint_cluster_detail(cluster_id)
  PURPOSE: Full detail on a specific complaint cluster
           including individual complaint count and age
  QUERY:   SELECT c.summary, c.ward, c.weight, c.urgency,
                  c.created_at, COUNT(co.id) as complaint_count
           FROM clusters c
           LEFT JOIN complaints co ON co.cluster_id = c.id
           WHERE c.id = ?
           GROUP BY c.id
  WHEN USED: Agent wants to understand depth of a specific issue

TOOL 5: get_ai_memory(topic_keyword)
  PURPOSE: Search AI memory notes by topic
  QUERY:   SELECT topic, content, created_at
           FROM ai_memory
           WHERE topic LIKE ?
           ORDER BY created_at DESC LIMIT 5
  WHEN USED: Agent wants to recall a specific past observation

TOOL 6: get_resolved_history(limit)
  PURPOSE: Recent completion history — pattern signal
  QUERY:   SELECT title, to_whom, ward, deadline,
                  completed_at, extension_count
           FROM timely_items
           WHERE status = 'completed'
           ORDER BY completed_at DESC LIMIT 10
  WHEN USED: Agent wants to understand resolution patterns
```

---

## Prompt Structure

### Round 1 Prompt

```
You are a strategic advisor analysing governance data for an Indian MLA.
You have access to read-only database tools.
Maximum tool calls across all rounds: 3.

AVAILABLE TOOLS:
get_ward_history(ward) — full history for a ward
get_department_track_record(department) — dept reliability data
get_overdue_items(urgency) — full overdue list by urgency level
get_complaint_cluster_detail(cluster_id) — detail on a complaint cluster
get_ai_memory(topic_keyword) — search AI memory notes
get_resolved_history() — recent resolution patterns

CURRENT DATA:
{always_on_context}

TASK:
Analyse the current situation. Identify the most pressing issues.
If you need specific historical data to give a better recommendation,
call a tool. If you have enough to proceed, say READY.

Respond with EXACTLY one of these formats:

TOOL_CALL: tool_name | argument
THINKING: [your reasoning for calling this tool]

OR

READY
THINKING: [your analysis summary]
```

### Round 2 Prompt

```
PREVIOUS ANALYSIS:
{round_1_thinking}

TOOL RESULT ({tool_name} | {argument}):
{tool_result}

CURRENT DATA:
{always_on_context}

You may call one more tool if needed, or proceed.
Respond with TOOL_CALL or READY as before.
```

### Round 3 Prompt (always final)

```
ANALYSIS COMPLETE. Generate suggestions now.

{always_on_context}

TOOL RESULTS FROM ANALYSIS:
{all_tool_results_so_far}

ANALYSIS SUMMARY:
{all_thinking_so_far}

Generate 3-4 specific, actionable suggestions.
Every suggestion must reference actual data from the context above.
No generic advice. No hallucinated statistics.

Return a JSON array only. No markdown. No explanation.
Each object must have:
  priority: "critical" | "urgent" | "normal"
  title: max 8 words, specific and actionable
  body: 2-3 sentences referencing real data above
```

---

## Thinking Trace Schema

Every agent action produces a trace entry. All entries collected and returned with the response.

```python
thinking_trace = [
    {
        "round": 1,
        "type": "analysis",        # analysis | tool_call | tool_result | final
        "content": str,            # the agent's reasoning text
        "tool": str | None,        # tool name if type is tool_call
        "args": str | None,        # tool argument if type is tool_call
        "timestamp": str           # ISO timestamp
    }
]
```

---

## API Response Schema

```python
{
    "suggestions": [
        {
            "priority": "critical" | "urgent" | "normal",
            "title": str,   # max 8 words
            "body": str     # 2-3 sentences, data-referenced
        }
    ],
    "thinking_trace": [ ...trace entries... ],
    "rounds_used": int,         # 1, 2, or 3
    "tools_called": [str],      # list of tool names used
    "context_summary": str      # one-line summary for dropdown header
                                # e.g. "2 rounds · 1 tool call · PWD track record fetched"
}
```

---

*SarkarSathi Suggestions Agent — Finalé System Design*
