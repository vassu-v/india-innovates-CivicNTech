"""
Rich seed script for Co-Pilot demo.
Aligned to STORY.md - Shri Rajendra Kumar Verma, Ward 42 South Delhi.

Usage:
    python Project/seed.py           # Add seed data on top of existing
    python Project/seed.py --reset   # Wipe everything, seed fresh (use before demo)

Target state after seeding:
    - 2 critical items (W5/W8)  - overdue 15+ and 10 days
    - 2 urgent items (W3)       - overdue 5 days
    - 4 normal items (W1/W2)    - future or barely overdue
    - 3 completed items         - history page not empty
    - 1 extended item           - extension_count = 1
    - 4 complaint clusters      - weights 5, 3, 2, 1
    - 11 individual complaints  - linked to those clusters
"""

import commitment_engine
import issue_engine
import datetime
import sqlite3
import rag_engine
import sys

today      = datetime.datetime.now().date()
_d = lambda days: (today - datetime.timedelta(days=days)).isoformat()
_f = lambda days: (today + datetime.timedelta(days=days)).isoformat()

# -- helpers ------------------------------------------------------------------

def _add_meeting_item(text, title, item_type, source_id, meeting_date,
                      deadline, to_whom=None, ward=None):
    """Add a meeting item with pre-set extracted fields (bypasses Gemini)."""
    return commitment_engine.add_item({
        "text": text,
        "type": item_type,
        "source_id": source_id,
        "meeting_date": meeting_date,
        "_extracted": {
            "title": title,
            "type": item_type,
            "to_whom": to_whom,
            "ward": ward,
            "deadline": deadline,
        }
    })


def _backdate_completion(item_id, completed_date_str, resolution_notes="Resolved."):
    """
    Mark an item completed with a specific backdated timestamp.
    complete_item() always uses now(), so we patch via SQL after.
    """
    conn = sqlite3.connect(commitment_engine.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE timely_items
           SET status='completed', completed_at=?, resolution_notes=?, injected_to_rag=TRUE
           WHERE id=?""",
        (completed_date_str + "T10:00:00", resolution_notes, item_id)
    )
    conn.commit()
    cursor.execute("SELECT * FROM timely_items WHERE id=?", (item_id,))
    item = cursor.fetchone()
    conn.close()

    if not item: return

    # Ingest to RAG
    try:
        rag_engine.store_node(
            domain='commitment_history',
            ward=item['ward'],
            topic=None,
            title=item['title'],
            content=f"Commitment: {item['title']}\nResolution: {resolution_notes}\nCompleted: {completed_date_str}",
            source_ref=f"timely_items:{item_id}"
        )
    except Exception as e:
        print(f"Seed RAG injection failed: {e}")


def _log_complaint(citizen_name, ward, channel, text, date_received):
    """Log a complaint through the full issue engine pipeline."""
    cluster_res = issue_engine.process_complaint({
        "citizen_name": citizen_name,
        "citizen_contact": None,
        "ward": ward,
        "channel": channel,
        "complaint_text": text,
        "date_received": date_received,
        "staff_notes": None,
    })
    commitment_engine.add_item(cluster_res)
    return cluster_res


# -- main seed ----------------------------------------------------------------

def seed(reset=False):
    print("Initialising databases...")
    commitment_engine.init_db()
    issue_engine.init_db()
    rag_engine.init_db()

    if reset:
        print("Resetting databases...")
        commitment_engine.truncate_db()
        issue_engine.truncate_db()
        rag_engine.truncate_db()

    # -- PROFILE --------------------------------------------------------------
    print("Setting MLA profile...")
    commitment_engine.update_profile({
        "name":              "Shri Rajendra Kumar Verma",
        "party":             "Indian National Congress",
        "designation":       "MLA",
        "term_start":        "2024",
        "email":             "rajendra.verma@mla.delhi.gov.in",
        "contact":           "+91-11-XXXXXXXX",
        "ward_name":         "Ward 42 - South Delhi",
        "state":             "Delhi",
        "district":          "South Delhi",
        "wards_covered":     "6",
        "population":        "2,70,000",
        "registered_voters": "1,82,400",
        "office_address":    "Plot 12, Sector 4, Ward 42, South Delhi - 110044",
        "janata_darbar_day":  "Wednesday",
        "janata_darbar_time": "10:00 AM – 1:00 PM",
        "pa_name":           "Suresh Yadav",
        "pa_contact":        "+91-98XXXXXXXX",
        "manager_name":      "Priya Sharma",
        "manager_contact":   "+91-99XXXXXXXX",
    })

    # -- PENDING - CRITICAL (will escalate to W8 / W5) ------------------------
    print("Seeding critical overdue items...")

    # W8 - 16 days overdue - flagship issue
    _add_meeting_item(
        text        = "I will follow up with PWD on Ward 42 pre-monsoon drain cleaning by February 10th.",
        title       = "Follow up with PWD - Ward 42 drain cleaning",
        item_type   = "commitment",
        source_id   = "ward_coord_jan15.txt",
        meeting_date= _d(23),
        deadline    = _d(16),
        to_whom     = "PWD",
        ward        = "Ward 42",
    )

    # W5 - 10 days overdue
    _add_meeting_item(
        text        = "I will take up street light outage in Ward 17 Sector 4 with MCD within this week.",
        title       = "Escalate Ward 17 Sector 4 street light outage to MCD",
        item_type   = "commitment",
        source_id   = "ward_coord_jan15.txt",
        meeting_date= _d(17),
        deadline    = _d(10),
        to_whom     = "MCD",
        ward        = "Ward 17",
    )

    # -- PENDING - URGENT (will escalate to W3) -------------------------------
    print("Seeding urgent items...")

    # 5 days overdue
    _add_meeting_item(
        text        = "I will ask PWD to inspect Ward 17 market road and give repair timeline by January 22nd.",
        title       = "PWD inspection - Ward 17 market road repair timeline",
        item_type   = "commitment",
        source_id   = "ward_coord_jan15.txt",
        meeting_date= _d(12),
        deadline    = _d(5),
        to_whom     = "PWD",
        ward        = "Ward 17",
    )

    # 4 days overdue
    _add_meeting_item(
        text        = "Schedule a DJB review for water pressure issues in Ward 23 Block C.",
        title       = "DJB review - Ward 23 water pressure",
        item_type   = "action",
        source_id   = "pwd_meeting_feb10.txt",
        meeting_date= _d(11),
        deadline    = _d(4),
        to_whom     = "DJB",
        ward        = "Ward 23",
    )

    # -- PENDING - NORMAL (future or barely overdue) ---------------------------
    print("Seeding normal pending items...")

    # Due in 5 days
    _add_meeting_item(
        text        = "Check PM Awas Yojana eligibility for 340 Ward 8 residents and prepare camp visit.",
        title       = "PM Awas eligibility check - Ward 8 camp visit prep",
        item_type   = "question",
        source_id   = "janata_darbar_feb25.txt",
        meeting_date= _d(8),
        deadline    = _f(5),
        to_whom     = "Revenue",
        ward        = "Ward 8",
    )

    # Due in 9 days
    _add_meeting_item(
        text        = "Coordinate with MCD on encroachment removal at Ward 3 community park entrance.",
        title       = "MCD coordination - Ward 3 park encroachment",
        item_type   = "commitment",
        source_id   = "dm_meeting_feb22.txt",
        meeting_date= _d(5),
        deadline    = _f(9),
        to_whom     = "MCD",
        ward        = "Ward 3",
    )

    # Due in 14 days
    _add_meeting_item(
        text        = "Review school infrastructure report for Ward 6 and respond to Education department.",
        title       = "Review Ward 6 school infrastructure report",
        item_type   = "action",
        source_id   = "dm_meeting_feb22.txt",
        meeting_date= _d(3),
        deadline    = _f(14),
        to_whom     = "Education",
        ward        = "Ward 6",
    )

    # Due in 21 days
    _add_meeting_item(
        text        = "Arrange sanitation inspection for Ward 31 migrant worker settlements before summer.",
        title       = "Ward 31 sanitation inspection - migrant settlements",
        item_type   = "commitment",
        source_id   = "janata_darbar_feb25.txt",
        meeting_date= _d(2),
        deadline    = _f(21),
        to_whom     = "MCD",
        ward        = "Ward 31",
    )

    # -- COMPLETED - backdated so history is populated -------------------------
    print("Seeding completed items...")

    # Completed on time - Commissioner Singh escalation worked
    id1 = _add_meeting_item(
        text        = "Direct call to Commissioner Singh re: Ward 42 road repair after department routing failed.",
        title       = "Direct escalation to Commissioner Singh - Ward 42 road repair",
        item_type   = "commitment",
        source_id   = "ward_coord_jan15.txt",
        meeting_date= _d(40),
        deadline    = _d(33),
        to_whom     = "Commissioner Singh",
        ward        = "Ward 42",
    )
    _backdate_completion(id1, _d(34),
        "Contacted Commissioner Singh directly. PWD team deputed within 48 hours. Road repaired.")

    # Completed on time - DJB water complaint resolved
    id2 = _add_meeting_item(
        text        = "Follow up with DJB on water supply disruption in Ward 8.",
        title       = "DJB follow-up - Ward 8 water supply disruption",
        item_type   = "commitment",
        source_id   = "pwd_meeting_feb10.txt",
        meeting_date= _d(30),
        deadline    = _d(23),
        to_whom     = "DJB",
        ward        = "Ward 8",
    )
    _backdate_completion(id2, _d(25),
        "DJB restored supply within 2 days. Citizen confirmed resolution at next Janata Darbar.")

    # Completed late - extended once, still eventually done
    id3 = _add_meeting_item(
        text        = "Send written response to RWA Ward 3 on park maintenance schedule.",
        title       = "Written response to RWA Ward 3 - park maintenance",
        item_type   = "action",
        source_id   = "dm_meeting_feb22.txt",
        meeting_date= _d(45),
        deadline    = _d(38),
        to_whom     = "RWA Ward 3",
        ward        = "Ward 3",
    )
    # Extend it first, then complete late
    commitment_engine.extend_item(id3, _d(28))
    _backdate_completion(id3, _d(20),
        "Letter drafted and dispatched. Park cleaning scheduled for first Saturday of each month.")

    # -- EXTENDED PENDING - one item with extension_count = 1 -----------------
    print("Seeding extended item...")

    id4 = _add_meeting_item(
        text        = "Inspect Ward 11 drainage network before monsoon season and submit report to PWD.",
        title       = "Ward 11 drainage inspection before monsoon",
        item_type   = "commitment",
        source_id   = "pwd_meeting_feb10.txt",
        meeting_date= _d(20),
        deadline    = _d(13),    # was overdue
        to_whom     = "PWD",
        ward        = "Ward 11",
    )
    # Extend to a future date - resets weight to 1
    commitment_engine.extend_item(id4, _f(7))

    # -- COMPLAINT CLUSTERS - built up via real embeddings --------------------
    print("Seeding complaint clusters (running embeddings - takes ~30s)...")

    # CLUSTER A - Ward 42 drainage - 5 complaints → weight 5, critical
    print("  Cluster A: Ward 42 drainage...")
    _log_complaint("Ramesh Kumar",   "Ward 42", "Walk-in visit",
        "Nala near plot 34 is completely blocked. Water overflowing into homes during rain.",
        _d(14))
    _log_complaint("Geeta Bai",      "Ward 42", "Physical letter",
        "Drain behind our colony wall has not been cleaned for months. Flooding every time it rains.",
        _d(10))
    _log_complaint("Abdul Rehman",   "Ward 42", "Walk-in visit",
        "Sewage drain overflow on main road Ward 42. Very bad smell and health risk for children.",
        _d(7))
    _log_complaint("Priya Singh",    "Ward 42", "CPGRAMS portal",
        "Water logging due to blocked storm drain. Reported three times already, no action taken.",
        _d(4))
    _log_complaint("Mohan Lal",      "Ward 42", "Walk-in visit",
        "Canal drain overflow near school. Parents afraid to send children. Please act urgently.",
        _d(2))

    # CLUSTER B - Ward 17 street lights - 3 complaints → weight 3, urgent
    print("  Cluster B: Ward 17 street lights...")
    _log_complaint("Sunita Devi",    "Ward 17", "Physical letter",
        "Three street lights outside primary school in Sector 4 not working for two weeks.",
        _d(9))
    _log_complaint("RWA Sector 4",   "Ward 17", "Walk-in visit",
        "Street light poles in Sector 4 near school gate dark since last month. Children unsafe.",
        _d(6))
    _log_complaint("Kishore Lal",    "Ward 17", "State grievance portal",
        "No street lighting on main road Ward 17 after 7pm. Two accidents already happened.",
        _d(3))

    # CLUSTER C - Ward 8 water supply - 2 complaints → weight 2, normal
    print("  Cluster C: Ward 8 water supply...")
    _log_complaint("Deepa Sharma",   "Ward 8",  "CPGRAMS portal",
        "Water supply completely cut in Block C Ward 8 for three days. Elderly woman alone at home.",
        _d(5))
    _log_complaint("Suresh Gupta",   "Ward 8",  "Walk-in visit",
        "DJB water tanker not coming to Ward 8 sector B. No water supply since Monday.",
        _d(3))

    # CLUSTER D - Ward 3 encroachment - 1 complaint → weight 1, normal
    print("  Cluster D: Ward 3 encroachment...")
    _log_complaint("RWA Ward 3",     "Ward 3",  "Walk-in visit",
        "Illegal shop encroaching on community park entrance. Park access blocked for residents.",
        _d(8))

    # -- PENDING - CRITICAL Expansion -----------------------------------------
    # W29 - 25 days overdue - High Urgency Health Risk
    _add_meeting_item(
        text        = "Coordinate with Health Dept and MCD for massive anti-dengue drive in Ward 29 slums.",
        title       = "Ward 29 Dengue Prevention Mega-Drive",
        item_type   = "commitment",
        source_id   = "health_alert_feb01.txt",
        meeting_date= _d(50),
        deadline    = _d(25),
        to_whom     = "MCD & Health Dept",
        ward        = "Ward 29",
    )

    # W15 - 12 days overdue - Ghost Resolution Conflict
    _add_meeting_item(
        text        = "Verify if the Ward 15 park redevelopment was actually finished as reported by PWD.",
        title       = "Audit Ward 15 PWD 'Ghost' Resolution",
        item_type   = "action",
        source_id   = "citizen_feedback_feb15.txt",
        meeting_date= _d(15),
        deadline    = _d(12),
        to_whom     = "PWD",
        ward        = "Ward 15",
    )

    # -- PENDING - URGENT Expansion -------------------------------------------
    # Ward 1 - 6 days overdue - Infrastructure Dependency
    id_pwd_ward1 = _add_meeting_item(
        text        = "PWD to relay main artery in Ward 1 once DJB pipe repairs are complete (waiting for DJB).",
        title       = "Ward 1 Main Road - Post-DJB Repair Relaying",
        item_type   = "commitment",
        source_id   = "infra_coord_feb10.txt",
        meeting_date= _d(20),
        deadline    = _d(6),
        to_whom     = "PWD (pending DJB)",
        ward        = "Ward 1",
    )

    # -- COMPLAINT CLUSTERS Expansion -----------------------------------------
    # CLUSTER E - Ward 29 Trash - 8 complaints → weight 8, CRITICAL
    print("  Cluster E: Ward 29 Garbage management...")
    for i in range(8):
        _log_complaint(f"Resident {i+1}", "Ward 29", "WhatsApp",
            f"Garbage heap at point {i*5} in Ward 29. Not cleared for 10 days. Massive stench.",
            _d(12-i))

    # CLUSTER F - Ward 15 Water logging - 4 complaints → weight 4, URGENT
    print("  Cluster F: Ward 15 Water logging...")
    _log_complaint("Anita", "Ward 15", "Walk-in", "Street flooding near the temple.", _d(5))
    _log_complaint("Vikram", "Ward 15", "Walk-in", "Water entering basements in Block B.", _d(4))
    _log_complaint("RWA W15", "Ward 15", "Letter", "Temple road unusable after rain.", _d(3))
    _log_complaint("Police Beat", "Ward 15", "Phone", "Traffic diverted due to flooding at Ward 15 triangle.", _d(2))

    # -- ESCALATE - ensure weights reflect overdue days correctly --------------
    print("Running escalation to set correct weights...")
    commitment_engine.escalate()

    # -- HISTORICAL RAG CONTEXT -----------------------------------------------
    print("Seeding historical knowledge for RAG (Stories)...")
    rag_engine.store_node(
        domain='governance_history',
        ward='Ward 15',
        topic='corruption',
        title='Contractor Review: PWD Zone 4',
        content="Zone 4 PWD contractors have a history of marking items 'Resolved' in the system while work is only 40% complete. Requires physical audit before closing.",
        source_ref='audit_report_2023'
    )
    rag_engine.store_node(
        domain='context_file',
        ward='Ward 42',
        topic='demographics',
        title='Ward 42 Factsheet 2024',
        content="Ward 42 (South Delhi) has a population of 45,000. Drainage coverage is 60%. Major flooding occurs every February-March. 340 residents are currently eligible for PM Awas Yojana but haven't applied.",
        source_ref='seed_static_context'
    )
    rag_engine.store_node(
        domain='context_file',
        ward='Ward 29',
        topic='demographics',
        title='Ward 29 Slum Redevelopment Profile',
        content="Ward 29 contains 12 major slum clusters. High density makes sanitation drives critical. 0% sewage coverage in Sectors 1-5. Prime breeding ground for Dengue.",
        source_ref='health_impact_survey'
    )
    rag_engine.store_node(
        domain='contact_file',
        ward=None,
        topic='directory',
        title='Department Liaisons 2024',
        content="MCD: Commissioner Saxena (+91-11-2321XXXX), DJB: CE Verma (+91-11-2356XXXX), PWD: SE Gupta (+91-11-2389XXXX).",
        source_ref='internal_directory'
    )

    # -- 2023 Historical Resolutions (Trend Data) ----------------------------
    print("Seeding historical trend data (2023)...")
    for i in range(5):
        id_hist = _add_meeting_item(
            text=f"Historical resolution {i+1} for infrastructure tracking.",
            title=f"Completed Task 2023-{i+1}",
            item_type="commitment",
            source_id="archive_2023.txt",
            meeting_date="2023-01-01",
            deadline="2023-01-15",
            to_whom="PWD",
            ward=f"Ward {i*7 + 1}"
        )
        _backdate_completion(id_hist, "2023-01-14", "Resolved efficiently in 2023.")

    # -- SUMMARY --------------------------------------------------------------
    conn = sqlite3.connect(commitment_engine.DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT urgency, COUNT(*) as c FROM timely_items WHERE status='pending' GROUP BY urgency")
    urgency = {r["urgency"]: r["c"] for r in cur.fetchall()}

    cur.execute("SELECT COUNT(*) as c FROM timely_items WHERE status='completed'")
    completed = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM timely_items WHERE extension_count > 0")
    extended = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM clusters")
    clusters = cur.fetchone()["c"]

    cur.execute("SELECT COUNT(*) as c FROM complaints")
    complaints = cur.fetchone()["c"]

    conn.close()

    print("\n-- Seed complete ----------------------------------")
    print(f"  Critical pending : {urgency.get('critical', 0)}")
    print(f"  Urgent pending   : {urgency.get('urgent', 0)}")
    print(f"  Normal pending   : {urgency.get('normal', 0)}")
    print(f"  Completed        : {completed}")
    print(f"  Extended items   : {extended}")
    print(f"  Complaint clusters: {clusters}")
    print(f"  Individual complaints: {complaints}")
    print("---------------------------------------------------")
    print("Dashboard at http://localhost:8000 should look alive.")


if __name__ == "__main__":
    reset_db = "--reset" in sys.argv
    seed(reset=reset_db)
