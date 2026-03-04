import sqlite3
import datetime
import commitment_engine

DB_PATH = commitment_engine.DB_PATH

# ---------------------------------------------------------------------------
# NEW — Digest Module Functions
# ---------------------------------------------------------------------------

def get_digest():
    """
    Reads the last 7 days of data from timely_items.
    Returns a structured weekly summary dict. No LLM. No formatting. Just numbers.
    Calls escalate() first to ensure urgency counts are fresh.
    """
    commitment_engine.escalate()

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

