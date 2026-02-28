import os
import json
import datetime
from engine import (
    init_db, add_item, escalate,
    get_todo_list, complete_item,
    extend_item, get_stats, DB_PATH
)

def sep(char="─", width=65):
    print(char * width)

def header(title):
    print()
    sep("═")
    print(f"  {title}")
    sep("═")

def urgency_icon(urgency):
    return {"normal": "🟢", "urgent": "🟡", "critical": "🔴"}.get(urgency, "⚪")

# ─── ADD MEETING ITEM ─────────────────────────────────────────────────────────

def add_meeting_item():
    header("ADD MEETING ITEM (Gemini will extract structure)")
    print("Type  : commitment / question / action")
    item_type = input("Type  : ").strip().lower() or "commitment"
    text = input("Raw text : ").strip()
    if not text:
        print("❌ Text cannot be empty.")
        return
    meeting_date = input("Meeting date (YYYY-MM-DD) [today]: ").strip()
    if not meeting_date:
        meeting_date = datetime.datetime.now().strftime("%Y-%m-%d")
    source_id = input("Source ID / filename [manual]: ").strip() or "manual"

    print("\n⏳ Sending to Gemini for extraction...")
    item_id = add_item({
        "text": text,
        "type": item_type,
        "meeting_date": meeting_date,
        "source_id": source_id
    })
    print(f"\n✅ Stored! Item ID: {item_id}")

# ─── ADD ISSUE CLUSTER ────────────────────────────────────────────────────────

def add_issue_cluster():
    header("ADD ISSUE CLUSTER (from Issue Engine)")
    cluster_id = input("Cluster ID : ").strip()
    if not cluster_id:
        print("❌ Cluster ID required.")
        return
    summary = input("Cluster summary : ").strip()
    ward = input("Ward : ").strip()
    try:
        weight = int(input("Weight (1-8) : ").strip())
    except ValueError:
        weight = 1
    urgency = input("Urgency (normal/urgent/critical) [normal]: ").strip() or "normal"

    item_id = add_item({
        "cluster_id": cluster_id,
        "cluster_summary": summary,
        "ward": ward,
        "weight": weight,
        "urgency": urgency
    })
    print(f"\n✅ Issue cluster stored! Item ID: {item_id}")

# ─── VIEW TODO LIST ───────────────────────────────────────────────────────────

def view_todo_list():
    header("TO-DO LIST  (escalation applied fresh)")
    data = get_todo_list()

    # Meeting items
    m_items = data["meeting_items"]
    print(f"\n📋 MEETING ITEMS  ({len(m_items)} open)\n")
    if not m_items:
        print("  ─ No open meeting items.")
    else:
        print(f"  {'ID':<4} {'W':<3} {'Urg':<3} {'Type':<12} {'Deadline':<12} {'Overdue':<10} {'To Whom':<18} {'Title'}")
        sep()
        for i in m_items:
            overdue_str = f"{i['days_overdue']}d overdue" if i['days_overdue'] > 0 else f"{abs(i['days_overdue'])}d left"
            icon = urgency_icon(i['urgency'])
            to_whom = (i['to_whom'] or "–")[:17]
            title = (i['title'] or "")[:50]
            print(f"  {i['id']:<4} {i['weight']:<3} {icon}{i['urgency'][0].upper():<2} {i['type']:<12} {i['deadline']:<12} {overdue_str:<10} {to_whom:<18} {title}")

    # Issue items
    i_items = data["issue_items"]
    print(f"\n🚨 ISSUE-ENGINE ITEMS  ({len(i_items)} open)\n")
    if not i_items:
        print("  ─ No open issue items.")
    else:
        print(f"  {'ID':<4} {'W':<3} {'Urg':<3} {'Ward':<12} {'Cluster':<10} {'Title'}")
        sep()
        for i in i_items:
            icon = urgency_icon(i['urgency'])
            ward = (i['ward'] or "–")[:11]
            title = (i['title'] or "")[:50]
            print(f"  {i['id']:<4} {i['weight']:<3} {icon}{i['urgency'][0].upper():<2} {ward:<12} {str(i['cluster_id']):<10} {title}")
    sep()

# ─── COMPLETE ITEM ────────────────────────────────────────────────────────────

def complete_an_item():
    header("MARK ITEM COMPLETED")
    try:
        item_id = int(input("Item ID to complete: ").strip())
    except ValueError:
        print("❌ Invalid ID.")
        return
    notes = input("Resolution notes (optional): ").strip()
    fact_str = complete_item(item_id, notes)
    if fact_str:
        print("\n✅ Item marked completed!")
        print("\n📄 RAG Fact String (would be sent to RAG Engine):")
        sep()
        print(fact_str)
        sep()
    else:
        print("❌ Item not found.")

# ─── EXTEND ITEM ──────────────────────────────────────────────────────────────

def extend_an_item():
    header("EXTEND ITEM DEADLINE")
    try:
        item_id = int(input("Item ID to extend: ").strip())
    except ValueError:
        print("❌ Invalid ID.")
        return
    new_deadline = input("New deadline (YYYY-MM-DD): ").strip()
    if not new_deadline:
        print("❌ Deadline required.")
        return
    extend_item(item_id, new_deadline)
    print(f"\n✅ Deadline extended! Weight reset to 1 (fresh start from {new_deadline}).")

# ─── ESCALATE ─────────────────────────────────────────────────────────────────

def run_escalate():
    header("MANUAL ESCALATION")
    print("Running escalate() on all pending items...")
    escalate()
    print("✅ Done! Weights and urgency updated.")
    print("   (Tip: Use 'View To-Do List' to see new weights)")

# ─── STATS ────────────────────────────────────────────────────────────────────

def view_stats():
    header("COMMITMENT TRACKER STATS")
    s = get_stats()

    m = s["this_month"]
    a = s["all_time"]

    print("\n📅 THIS MONTH")
    sep()
    print(f"  Total items logged      : {m['total_made']}")
    print(f"  Resolved on time        : {m['resolved_on_time']}")
    print(f"  Currently overdue       : {m['currently_overdue']}")
    print(f"  Resolution rate         : {m['resolution_rate']:.1f}%")

    print("\n📊 ALL TIME")
    sep()
    print(f"  Avg days to resolve     : {a['avg_days_to_resolve']:.1f}")
    print(f"  Extension rate          : {a['extension_rate']:.1f}%")
    print(f"  Most reliable contact   : {a['most_reliable_contact'] or '─'}")

    depts = s["by_department"]
    if depts:
        print("\n🏢 BY DEPARTMENT / CONTACT")
        sep()
        print(f"  {'Name':<25} {'Total':<7} {'On-Time':<9} {'Avg Days'}")
        sep()
        for d in depts:
            print(f"  {d['name']:<25} {d['total']:<7} {d['on_time']:<9} {d['avg_days']:.1f}")
    sep()

# ─── RESET ────────────────────────────────────────────────────────────────────

def reset_database():
    header("RESET DATABASE")
    confirm = input("⚠️  Delete ALL commitment data? (yes/no): ").strip().lower()
    if confirm == "yes":
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        print("✅ Database reset. Fresh start.")
    else:
        print("Reset cancelled.")

# ─── MAIN MENU ────────────────────────────────────────────────────────────────

MENU = [
    ("Add meeting item (Gemini extracts structure)",  add_meeting_item),
    ("Add issue cluster (from Issue Engine)",          add_issue_cluster),
    ("View To-Do list (escalation applied live)",      view_todo_list),
    ("Complete an item",                               complete_an_item),
    ("Extend an item's deadline",                      extend_an_item),
    ("Run escalation manually (demo mode)",            run_escalate),
    ("View commitment tracker stats",                  view_stats),
    ("Reset database",                                 reset_database),
    ("Exit",                                           None),
]

def main():
    if not os.path.exists(DB_PATH):
        init_db()

    print()
    print("╔" + "═"*63 + "╗")
    print("║       COMMITMENT ENGINE — CoPilot Interactive CLI          ║")
    print("║       India Innovates 2026                                  ║")
    print("╚" + "═"*63 + "╝")

    while True:
        print("\n" + "─"*65)
        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {i}. {label}")
        print("─"*65)

        choice = input("\nChoice: ").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(MENU)):
            print("❌ Invalid choice.")
            continue

        idx = int(choice) - 1
        label, fn = MENU[idx]
        if fn is None:
            print("\nGoodbye! 👋\n")
            break
        try:
            fn()
        except KeyboardInterrupt:
            print("\n(Cancelled)")
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGoodbye! 👋\n")
