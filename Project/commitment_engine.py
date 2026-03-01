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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id                INTEGER PRIMARY KEY CHECK (id = 1),
            name              TEXT DEFAULT 'Shri Rajendra Kumar Verma',
            party             TEXT DEFAULT 'Indian National Congress',
            designation       TEXT DEFAULT 'MLA',
            term_start        TEXT DEFAULT '2024',
            email             TEXT DEFAULT 'rajendra.verma@mla.delhi.gov.in',
            contact           TEXT DEFAULT '+91-11-XXXXXXXX',
            ward_name         TEXT DEFAULT 'Ward 42 — South Delhi',
            state             TEXT DEFAULT 'Delhi',
            district          TEXT DEFAULT 'South Delhi',
            wards_covered     TEXT DEFAULT '6',
            population        TEXT DEFAULT '2,70,000',
            registered_voters TEXT DEFAULT '1,82,400',
            office_address    TEXT DEFAULT 'Plot 12, Sector 4, Ward 42, South Delhi — 110044',
            janata_darbar_day TEXT DEFAULT 'Wednesday',
            janata_darbar_time TEXT DEFAULT '10:00 AM – 1:00 PM',
            pa_name           TEXT DEFAULT 'Suresh Yadav',
            pa_contact        TEXT DEFAULT '+91-98XXXXXXXX',
            manager_name      TEXT DEFAULT 'Priya Sharma',
            manager_contact   TEXT DEFAULT '+91-99XXXXXXXX'
        )
    """)
    # Migration for existing databases
    try:
        cursor.execute("ALTER TABLE profile ADD COLUMN manager_contact TEXT DEFAULT '+91-99XXXXXXXX'")
    except sqlite3.OperationalError:
        pass # Already exists
    # Insert default if not exists
    cursor.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")
    conn.commit()
    conn.close()

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
            model='gemini-3-flash-preview',
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

        # Optimized check: If this cluster is already in to-do, just update details
        cursor.execute("SELECT id FROM timely_items WHERE source = 'issue_engine' AND source_id = ?", (source_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE timely_items 
                SET title = ?, weight = ?, urgency = ?, status = 'pending'
                WHERE id = ?
            """, (title, weight, urgency, existing[0]))
            conn.commit()
            conn.close()
            return existing[0]

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
    NOTE: Issue-engine items are intentionally excluded — their weight is set
    by the Issue Engine at ingestion time and is not re-escalated here. This
    is a conscious design decision: timely.db defers urgency ownership of issue
    items back to the Issue Engine. Revisit if independent escalation is needed.
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

def get_todo_list():
    escalate() # Ensure weights are fresh
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM timely_items WHERE status = 'pending' ORDER BY weight DESC, deadline ASC")
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
            # Adjust to schema
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

def complete_item(item_id, resolution_notes=""):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM timely_items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        conn.close()
        return None

    # Guard: prevent double-completion and duplicate RAG fact generation
    if item["status"] == "completed":
        conn.close()
        return None

    completed_at = datetime.datetime.now()
    
    # Calculate was_overdue
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
            
    # Build RAG fact string
    fact_string = f"""Commitment: {item['title']}
To: {item['to_whom']}
Made: {item['meeting_date']}
Deadline: {item['deadline']}
Completed: {completed_at.isoformat()}
Days taken: {days_taken}
Was overdue: {'yes' if was_overdue else 'no'}
Extensions: {item['extension_count']}"""

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
    
    # In a real app, you would call RAG Engine here: rag_engine.store_fact(fact_string)
    return fact_string

def extend_item(item_id, new_deadline):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Status stays 'pending' so the item remains visible in get_todo_list.
    # extension_count tracks how many times the deadline has been pushed.
    # Weight resets to 1 — fresh escalation from the new deadline.
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

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    today = datetime.datetime.now()
    current_month_str = today.strftime("%Y-%m")
    
    # This month stats
    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE strftime('%Y-%m', created_at) = ?", (current_month_str,))
    total_made_this_month = cursor.fetchone()["c"]
    
    # Use date(completed_at) to strip the time component before comparing to
    # deadline (which is stored as plain YYYY-MM-DD). Without this, a full
    # ISO timestamp like '2026-03-04T14:32:00' compares incorrectly to '2026-03-04'.
    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE status = 'completed' AND date(completed_at) <= deadline AND strftime('%Y-%m', created_at) = ?", (current_month_str,))
    resolved_on_time = cursor.fetchone()["c"]
    
    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE status = 'pending' AND deadline < ?", (today.strftime("%Y-%m-%d"),))
    currently_overdue = cursor.fetchone()["c"]
    
    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE status = 'completed' AND strftime('%Y-%m', created_at) = ?", (current_month_str,))
    total_completed_month = cursor.fetchone()["c"]
    resolution_rate = (resolved_on_time / total_completed_month * 100) if total_completed_month > 0 else 0
    
    # All time stats
    # avg_days_to_resolve
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
        except Exception:
            pass
            
    avg_days_to_resolve = (total_days / valid_completed) if valid_completed > 0 else 0
    
    cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE extension_count > 0")
    extended_count = cursor.fetchone()["c"]
    cursor.execute("SELECT COUNT(*) as c FROM timely_items")
    total_items = cursor.fetchone()["c"]
    
    extension_rate = (extended_count / total_items * 100) if total_items > 0 else 0
    
    # by department stats
    cursor.execute("SELECT to_whom, COUNT(*) as c FROM timely_items WHERE to_whom IS NOT NULL GROUP BY to_whom")
    departments = cursor.fetchall()
    
    dept_stats = []
    
    for dept in departments:
        name = dept["to_whom"]
        total = dept["c"]
        
        cursor.execute("SELECT COUNT(*) as c FROM timely_items WHERE to_whom = ? AND status = 'completed' AND date(completed_at) <= deadline", (name,))
        on_time = cursor.fetchone()["c"]
        
        cursor.execute("SELECT completed_at, meeting_date FROM timely_items WHERE to_whom = ? AND status = 'completed' AND meeting_date IS NOT NULL", (name,))
        dept_completed = cursor.fetchall()
        
        dt_days = 0
        dt_valid = 0
        for item in dept_completed:
            try:
                c_date = datetime.datetime.fromisoformat(item["completed_at"]).date()
                m_date = datetime.datetime.strptime(item["meeting_date"], "%Y-%m-%d").date()
                dt_days += (c_date - m_date).days
                dt_valid += 1
            except:
                pass
                
        avg_days = (dt_days / dt_valid) if dt_valid > 0 else 0
        
        dept_stats.append({
            "name": name,
            "total": total,
            "on_time": on_time,
            "avg_days": avg_days
        })
        
    most_reliable_contact = None
    best_rate = -1
    for dept in dept_stats:
        rate = dept["on_time"] / dept["total"]
        if rate > best_rate and dept["total"] > 0:
            best_rate = rate
            most_reliable_contact = dept["name"]
            
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
            "most_reliable_contact": most_reliable_contact
        },
        "by_department": dept_stats
    }
def get_profile():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profile WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def update_profile(data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    fields = []
    values = []
    for k, v in data.items():
        if k != "id":
            fields.append(f"{k} = ?")
            values.append(v)
    values.append(1)
    query = f"UPDATE profile SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return True
def get_recent_meetings(limit=5):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # We group by source_id (meeting filename) to show unique meetings processed
    cursor.execute("""
        SELECT source_id, meeting_date, COUNT(*) as commitments, 
               MAX(created_at) as last_activity
        FROM timely_items 
        WHERE source = 'meeting'
        GROUP BY source_id
        ORDER BY last_activity DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
