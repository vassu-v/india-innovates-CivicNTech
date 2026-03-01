import os
import json
import sqlite3
import datetime
from dotenv import load_dotenv
import google.genai as genai

# Load environment variables
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if api_key:
    client = genai.Client(api_key=api_key)
else:
    print("Warning: No Gemini API key found in .env. Extraction will fail gracefully.")
    client = None

DB_PATH = os.path.join(os.path.dirname(__file__), "copilot.db")

# ---------------------------------------------------------------------------
# DB Setup
# ---------------------------------------------------------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timely_items (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            title             TEXT,
            raw_text          TEXT,
            type              TEXT, -- commitment / question / action / issue
            source            TEXT, -- meeting / issue_engine / manual
            source_id         TEXT,
            to_whom           TEXT,
            ward              TEXT,
            deadline          DATE,
            weight            INTEGER DEFAULT 1,
            urgency           TEXT DEFAULT 'normal', -- normal / urgent / critical
            status            TEXT DEFAULT 'pending', -- pending / in_progress / completed / extended
            extension_count   INTEGER DEFAULT 0,
            extraction_failed BOOLEAN DEFAULT FALSE,
            meeting_date      DATE,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at      TIMESTAMP,
            resolution_notes  TEXT,
            injected_to_rag   BOOLEAN DEFAULT FALSE
        )
    """)
    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _infer_deadline(meeting_date_str, item_type):
    try:
        meeting_date = datetime.datetime.strptime(meeting_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        meeting_date = datetime.datetime.now().date()

    days = 7
    if item_type == "question":
        days = 3
    elif item_type == "action":
        days = 5

    return (meeting_date + datetime.timedelta(days=days)).isoformat()

def extract_with_gemini(raw_text, meeting_date, item_type, surrounding_context=""):
    try:
        if not client:
            raise Exception("No client initialized.")

        prompt = f"""
You are extracting structured data from a governance meeting transcript sentence.

Meeting date: {meeting_date}
Sentence: "{raw_text}"
Full context: "{surrounding_context}"

Extract the following as a valid JSON object only.
No explanation. No markdown. No backticks. Just JSON.

{{
  "title": "short actionable title, max 10 words",
  "deadline": "YYYY-MM-DD or null if not mentioned",
  "to_whom": "person or department involved or null",
  "ward": "ward name or number if mentioned or null",
  "type": "commitment or question or action"
}}

Deadline inference rules if not explicit:
  commitment -> 7 days from meeting date
  question   -> 3 days from meeting date
  action     -> 5 days from meeting date
"""
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        raw = response.text.strip()
        # Clean up any potential markdown backticks that Gemini might still output
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        item = json.loads(raw)

        # Ensure fallback rules apply if gemini didn't provide them
        if not item.get("deadline"):
             item["deadline"] = _infer_deadline(meeting_date, item.get("type", item_type))
        return item, False
    except Exception as e:
        print(f"Extraction failed: {e}")
        return {
            "title": raw_text[:80],
            "deadline": _infer_deadline(meeting_date, item_type),
            "to_whom": None,
            "ward": None,
            "type": item_type
        }, True

# ---------------------------------------------------------------------------
# Core write / mutation functions
# ---------------------------------------------------------------------------

def add_item(input_data):
    """
    input_data should be a dict containing standard fields.
    For Source A (meeting): text, type, source_id, meeting_date
    For Source B (issue): cluster_id, cluster_summary, ward, weight, urgency
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if "cluster_summary" in input_data:
        # Source B: Issue Engine
        title = input_data["cluster_summary"]
        raw_text = title
        item_type = "issue"
        source = "issue_engine"
        source_id = str(input_data["cluster_id"])
        to_whom = None
        ward = input_data.get("ward")
        deadline = (datetime.datetime.now().date() + datetime.timedelta(days=7)).isoformat()
        weight = input_data.get("weight", 1)
        urgency = input_data.get("urgency", "normal")
        meeting_date = None
        extraction_failed = False
    else:
        # Source A: Ingestion Engine (meeting)
        raw_text = input_data["text"]
        input_type = input_data.get("type", "commitment")
        source_id = input_data.get("source_id", "manual")
        meeting_date = input_data.get("meeting_date", datetime.datetime.now().date().isoformat())
        source = "meeting"

        extracted, extraction_failed = extract_with_gemini(raw_text, meeting_date, input_type)

        title = extracted.get("title", raw_text[:80])
        item_type = extracted.get("type", input_type)
        to_whom = extracted.get("to_whom")
        ward = extracted.get("ward")
        deadline = extracted.get("deadline")

        weight = 1
        urgency = "normal"

    cursor.execute("""
        INSERT INTO timely_items (
            title, raw_text, type, source, source_id, to_whom, ward, deadline,
            weight, urgency, extraction_failed, meeting_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, raw_text, item_type, source, source_id, to_whom, ward, deadline, weight, urgency, extraction_failed, meeting_date))

    item_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return item_id

def escalate():
    """
    Recalculates weight and urgency based on days overdue for meeting items.
    Issue-engine items are intentionally excluded.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, deadline FROM timely_items WHERE status = 'pending' AND source != 'issue_engine'")
    items = cursor.fetchall()

    today = datetime.datetime.now().date()

    for item_id, deadline_str in items:
        if not deadline_str:
            continue
        try:
            deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        days_overdue = (today - deadline).days

        if days_overdue <= 0:
            weight = 1
            urgency = "normal"
        elif 1 <= days_overdue <= 3:
            weight = 2
            urgency = "normal"
        elif 4 <= days_overdue <= 7:
            weight = 3
            urgency = "urgent"
        elif 8 <= days_overdue <= 14:
            weight = 5
            urgency = "critical"
        else:
            weight = 8
            urgency = "critical"

        cursor.execute("UPDATE timely_items SET weight = ?, urgency = ? WHERE id = ?", (weight, urgency, item_id))

    conn.commit()
    conn.close()

def complete_item(item_id, resolution_notes=""):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM timely_items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return None

    if item["status"] == "completed":
        conn.close()
        return None

    completed_at = datetime.datetime.now()

    was_overdue = False
    days_taken = 0
    if item["deadline"]:
        try:
            deadline = datetime.datetime.strptime(item["deadline"], "%Y-%m-%d").date()
            if completed_at.date() > deadline:
                was_overdue = True
        except ValueError:
            pass

    if item["meeting_date"]:
        try:
            meeting_date = datetime.datetime.strptime(item["meeting_date"], "%Y-%m-%d").date()
            days_taken = (completed_at.date() - meeting_date).days
        except ValueError:
            pass

    cursor.execute("""
        UPDATE timely_items
        SET status = 'completed',
            completed_at = ?,
            resolution_notes = ?,
            injected_to_rag = TRUE
        WHERE id = ?
    """, (completed_at.isoformat(), resolution_notes, item_id))

    conn.commit()
    conn.close()

    return True

def extend_item(item_id, new_deadline):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE timely_items
        SET deadline = ?,
            extension_count = extension_count + 1,
            weight = 1,
            urgency = 'normal',
            status = 'pending'
        WHERE id = ?
    """, (new_deadline, item_id))

    conn.commit()
    conn.close()
    return True

# ---------------------------------------------------------------------------
# Original read functions
# ---------------------------------------------------------------------------

def get_todo_list(type=None, urgency=None, ward=None):
    """
    Returns all pending items, split into meeting_items and issue_items.
    Accepts optional filters: type, urgency, ward.
    escalate() is called first to ensure fresh weights.
    """
    escalate()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

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
    rows = cursor.fetchall()

    response = {
        "meeting_items": [],
        "issue_items": []
    }

    today = datetime.datetime.now().date()

    for row in rows:
        item = dict(row)
        days_overdue = 0
        if item["deadline"]:
            try:
                deadline = datetime.datetime.strptime(item["deadline"], "%Y-%m-%d").date()
                days_overdue = (today - deadline).days
            except ValueError:
                pass
        item["days_overdue"] = days_overdue

        if item["source"] == "issue_engine":
            response["issue_items"].append({
                "id": item["id"],
                "title": item["title"],
                "type": item["type"],
                "ward": item["ward"],
                "weight": item["weight"],
                "urgency": item["urgency"],
                "cluster_id": item["source_id"]
            })
        else:
            response["meeting_items"].append({
                "id": item["id"],
                "title": item["title"],
                "type": item["type"],
                "to_whom": item["to_whom"],
                "ward": item["ward"],
                "deadline": item["deadline"],
                "weight": item["weight"],
                "urgency": item["urgency"],
                "days_overdue": item["days_overdue"],
                "source_id": item["source_id"],
                "meeting_date": item["meeting_date"]
            })

    conn.close()
    return response

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    today = datetime.datetime.now()
    current_month_str = today.strftime("%Y-%m")

    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE strftime('%Y-%m', created_at) = ?", (current_month_str,))
    total_made_this_month = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE status = 'completed' AND date(completed_at) <= deadline AND strftime('%Y-%m', created_at) = ?", (current_month_str,))
    resolved_on_time = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE status = 'pending' AND deadline < ?", (today.strftime("%Y-%m-%d"),))
    currently_overdue = cursor.fetchone()["c"]

    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE status = 'completed' AND strftime('%Y-%m', created_at) = ?", (current_month_str,))
    total_completed_month = cursor.fetchone()["c"]
    resolution_rate = (resolved_on_time / total_completed_month * 100) if total_completed_month > 0 else 0

    cursor.execute("SELECT completed_at, meeting_date FROM timely_items WHERE status = 'completed' AND meeting_date IS NOT NULL")
    completed_items = cursor.fetchall()

    total_days = 0
    valid_completed = 0
    for item in completed_items:
        try:
            c_date = datetime.datetime.fromisoformat(item["completed_at"]).date()
            m_date = datetime.datetime.strptime(item["meeting_date"], "%Y-%m-%d").date()
            total_days += (c_date - m_date).days
            valid_completed += 1
        except: pass

    avg_days_to_resolve = (total_days / valid_completed) if valid_completed > 0 else 0

    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE extension_count > 0")
    extended_count = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM timely_items")
    total_items = cursor.fetchone()["c"]
    extension_rate = (extended_count / total_items * 100) if total_items > 0 else 0

    # Restore by_department and reliable contact logic
    cursor.execute("""
        SELECT to_whom, COUNT(*) as c 
        FROM timely_items 
        WHERE status = 'completed' AND to_whom IS NOT NULL
        GROUP BY to_whom ORDER BY c DESC
    """)
    depts = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT to_whom, COUNT(*) as c
        FROM timely_items
        WHERE status = 'completed' AND date(completed_at) <= deadline AND to_whom IS NOT NULL
        GROUP BY to_whom ORDER BY c DESC LIMIT 1
    """)
    reliable = cursor.fetchone()
    most_reliable = reliable["to_whom"] if reliable else "None"

    conn.close()
    return {
        "this_month": {
            "total_made": total_made_this_month,
            "resolved_on_time": resolved_on_time,
            "currently_overdue": currently_overdue,
            "resolution_rate": resolution_rate
        },
        "all_time": {
            "avg_days_to_resolve": avg_days_to_resolve,
            "extension_rate": extension_rate,
            "most_reliable_contact": most_reliable,
            "by_department": depts
        }
    }

# ---------------------------------------------------------------------------
# NEW — Digest Module Functions
# ---------------------------------------------------------------------------

def get_digest():
    """
    Reads the last 7 days of data from timely_items.
    Returns a structured weekly summary dict. No LLM. No formatting. Just numbers.
    Calls escalate() first to ensure urgency counts are fresh.
    """
    escalate()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    today = datetime.datetime.now().date()
    week_start = today - datetime.timedelta(days=7)
    today_str = today.isoformat()
    week_start_str = week_start.isoformat()

    # 1. New items logged this week
    cursor.execute(
        "SELECT id, title, type, to_whom, ward, deadline FROM timely_items WHERE date(created_at) >= ?",
        (week_start_str,)
    )
    new_rows = cursor.fetchall()
    new_items_list = [dict(row) for row in new_rows]

    type_counts = {}
    for item in new_items_list:
        t = item["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    new_total = len(new_items_list)

    # 2. Items resolved (completed) this week
    cursor.execute(
        "SELECT id, title, type, to_whom, ward, deadline, completed_at FROM timely_items WHERE status = 'completed' AND date(completed_at) >= ?",
        (week_start_str,)
    )
    resolved_rows = cursor.fetchall()
    resolved_items_list = [dict(row) for row in resolved_rows]
    resolved_total = len(resolved_items_list)

    # 3. Items resolved on time this week
    resolved_on_time_list = []
    for item in resolved_items_list:
        try:
            completed_date = datetime.datetime.fromisoformat(item["completed_at"]).date()
            deadline_date = datetime.datetime.strptime(item["deadline"], "%Y-%m-%d").date()
            if completed_date <= deadline_date:
                resolved_on_time_list.append(item)
        except (ValueError, TypeError):
            resolved_on_time_list.append(item)

    resolved_on_time = len(resolved_on_time_list)
    resolved_late = resolved_total - resolved_on_time
    resolution_rate = round(resolved_on_time / resolved_total * 100, 1) if resolved_total > 0 else 0.0

    # 4. Items that became overdue this week
    cursor.execute(
        """SELECT id, title, to_whom, deadline, ward
           FROM timely_items
           WHERE status = 'pending'
           AND deadline >= ?
           AND deadline < ?
           ORDER BY deadline ASC""",
        (week_start_str, today_str)
    )
    became_overdue = [dict(row) for row in cursor.fetchall()]

    # 5. Open items by urgency
    cursor.execute("SELECT urgency, COUNT(*) as c FROM timely_items WHERE status = 'pending' GROUP BY urgency")
    urgency_counts = {row["urgency"]: row["c"] for row in cursor.fetchall()}
    open_total = sum(urgency_counts.values())

    # 6. Most overdue
    cursor.execute("""SELECT id, title, to_whom, deadline, ward FROM timely_items
                      WHERE status = 'pending' AND deadline < ?
                      ORDER BY deadline ASC LIMIT 1""", (today_str,))
    most_overdue_row = cursor.fetchone()
    most_overdue = dict(most_overdue_row) if most_overdue_row else {"title": None, "days_overdue": 0}
    if most_overdue_row:
        try:
            deadline_date = datetime.datetime.strptime(most_overdue_row["deadline"], "%Y-%m-%d").date()
            most_overdue["days_overdue"] = (today - deadline_date).days
        except: most_overdue["days_overdue"] = 0

    conn.close()

    return {
        "period": {"from": week_start_str, "to": today_str},
        "new_items": {
            "total": new_total,
            "commitments": type_counts.get("commitment", 0),
            "questions": type_counts.get("question", 0),
            "actions": type_counts.get("action", 0),
            "issues": type_counts.get("issue", 0),
            "items": new_items_list
        },
        "resolved": {
            "total": resolved_total,
            "on_time": resolved_on_time,
            "late": resolved_late,
            "resolution_rate": resolution_rate,
            "items": resolved_items_list
        },
        "became_overdue_this_week": became_overdue,
        "open_right_now": {
            "total": open_total,
            "normal": urgency_counts.get("normal", 0),
            "urgent": urgency_counts.get("urgent", 0),
            "critical": urgency_counts.get("critical", 0)
        },
        "most_overdue": most_overdue
    }

def get_history(limit=50, offset=0):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE status = 'completed'")
    total = cursor.fetchone()["c"]
    cursor.execute("SELECT * FROM timely_items WHERE status = 'completed' ORDER BY completed_at DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    items = []
    for row in rows:
        item = dict(row)
        # minimal compute for history list
        items.append(item)
    return {"total": total, "items": items}
