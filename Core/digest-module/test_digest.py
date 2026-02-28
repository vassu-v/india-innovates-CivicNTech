"""
Digest Module — Test Suite
Tests all 3 new functions: get_digest(), get_history(), get_todo_list(filters)
Run from digest-module directory:  python test_digest.py
"""

import os
import sys
import json
import datetime

# Ensure we import from this directory
sys.path.insert(0, os.path.dirname(__file__))

from engine import (
    init_db, add_item, escalate, complete_item, extend_item,
    get_todo_list, get_stats,
    get_digest, get_history,
    DB_PATH
)

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"

def check(label, condition, hint=""):
    status = PASS if condition else FAIL
    print(f"  {status} {label}" + (f"  ({hint})" if hint else ""))
    return condition

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup():
    """Fresh database + seed data that covers all test scenarios."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()

    today = datetime.date.today()
    # Date anchors
    recent_date     = (today - datetime.timedelta(days=3)).isoformat()   # within this week
    old_date        = (today - datetime.timedelta(days=30)).isoformat()  # last month
    overdue_date    = (today - datetime.timedelta(days=10)).isoformat()  # meeting 10d ago → question deadline 7d ago

    # Item A — recent commitment, will complete on time
    id_a = add_item({
        "text": "Follow up with PWD commissioner and ensure work begins by 5th March",
        "type": "commitment",
        "meeting_date": recent_date,
        "source_id": "meet_001"
    })

    # Item B — old question with past deadline → will be overdue / critical after escalate
    id_b = add_item({
        "text": "Can you check PM Awas Yojana applications from Ward 8?",
        "type": "question",
        "meeting_date": overdue_date,
        "source_id": "meet_002"
    })

    # Item C — recent action (pending, urgency normal)
    id_c = add_item({
        "text": "Prepare monthly road repair status report for Ward 12",
        "type": "action",
        "meeting_date": recent_date,
        "source_id": "meet_003"
    })

    # Item D — issue from Issue Engine
    id_d = add_item({
        "cluster_summary": "Drainage overflow Ward 42",
        "weight": 6,
        "urgency": "critical",
        "ward": "Ward 42",
        "cluster_id": 999
    })

    # Item E — old commitment in a different ward (for filter tests)
    id_e = add_item({
        "text": "Organize street light repair drive in Ward 5",
        "type": "commitment",
        "meeting_date": old_date,
        "source_id": "meet_004"
    })

    # Complete item A to populate get_history
    complete_item(id_a, resolution_notes="PWD commissioner confirmed, work started on time.")

    print(f"Seeded items: A={id_a}, B={id_b}, C={id_c}, D={id_d}, E={id_e}")
    print(f"Completed: A={id_a}")
    return id_a, id_b, id_c, id_d, id_e


# ---------------------------------------------------------------------------
# Test: get_digest()
# ---------------------------------------------------------------------------

def test_get_digest(id_a, id_b, id_c, id_d, id_e):
    section("TEST 1 — get_digest()")
    digest = get_digest()
    print("\nRaw digest:")
    print(json.dumps(digest, indent=2))

    today = datetime.date.today()
    week_start = (today - datetime.timedelta(days=7)).isoformat()

    all_pass = True

    all_pass &= check(
        "period.from is 7 days ago",
        digest["period"]["from"] == week_start,
        f"expected {week_start}, got {digest['period']['from']}"
    )
    all_pass &= check(
        "period.to is today",
        digest["period"]["to"] == today.isoformat(),
        f"expected {today.isoformat()}, got {digest['period']['to']}"
    )
    all_pass &= check(
        "new_items.total >= 3 (A, C, D were created this week; B and E may be older)",
        digest["new_items"]["total"] >= 3,
        f"got {digest['new_items']['total']}"
    )
    all_pass &= check(
        "resolved.total >= 1 (item A completed)",
        digest["resolved"]["total"] >= 1,
        f"got {digest['resolved']['total']}"
    )
    all_pass &= check(
        "resolved.on_time >= 1 (item A was completed on time)",
        digest["resolved"]["on_time"] >= 1,
        f"got {digest['resolved']['on_time']}"
    )
    all_pass &= check(
        "resolved.resolution_rate > 0",
        digest["resolved"]["resolution_rate"] > 0,
        f"got {digest['resolved']['resolution_rate']}"
    )
    all_pass &= check(
        "open_right_now.total >= 1",
        digest["open_right_now"]["total"] >= 1,
        f"got {digest['open_right_now']['total']}"
    )
    all_pass &= check(
        "open_right_now.critical >= 1 (item B is overdue after escalate)",
        digest["open_right_now"]["critical"] >= 1,
        f"got {digest['open_right_now']['critical']}"
    )
    all_pass &= check(
        "most_overdue is not None (item B overdue)",
        digest["most_overdue"]["id"] is not None,
        f"got {digest['most_overdue']}"
    )
    all_pass &= check(
        "most_overdue.days_overdue > 0",
        digest["most_overdue"]["days_overdue"] > 0,
        f"got {digest['most_overdue']['days_overdue']}"
    )
    # Edge: no crash on keys
    all_pass &= check(
        "new_items has all 4 type keys",
        all(k in digest["new_items"] for k in ["commitments", "questions", "actions", "issues"]),
    )
    all_pass &= check(
        "open_right_now has normal/urgent/critical keys",
        all(k in digest["open_right_now"] for k in ["normal", "urgent", "critical"]),
    )

    return all_pass


# ---------------------------------------------------------------------------
# Test: get_history()
# ---------------------------------------------------------------------------

def test_get_history(id_a):
    section("TEST 2 — get_history()")
    history = get_history()
    print("\nRaw history:")
    print(json.dumps(history, indent=2))

    all_pass = True

    all_pass &= check(
        "total >= 1",
        history["total"] >= 1,
        f"got {history['total']}"
    )
    all_pass &= check(
        "items is a list with >= 1 entry",
        isinstance(history["items"], list) and len(history["items"]) >= 1,
    )

    if history["items"]:
        first = history["items"][0]
        all_pass &= check(
            "items[0] has required keys",
            all(k in first for k in [
                "id", "title", "type", "to_whom", "ward", "deadline",
                "completed_at", "meeting_date", "resolution_notes",
                "extension_count", "was_overdue", "days_taken", "source", "source_id"
            ]),
        )
        all_pass &= check(
            "items[0].was_overdue is bool",
            isinstance(first["was_overdue"], bool),
            f"got {type(first['was_overdue'])}"
        )
        all_pass &= check(
            "items[0].was_overdue = False (item A was on time)",
            first["was_overdue"] is False,
            f"got {first['was_overdue']}"
        )
        all_pass &= check(
            "items[0].extension_count = 0",
            first["extension_count"] == 0,
            f"got {first['extension_count']}"
        )
        all_pass &= check(
            "items[0].days_taken >= 0",
            first["days_taken"] >= 0,
            f"got {first['days_taken']}"
        )

    # Pagination test
    paged = get_history(limit=1, offset=0)
    all_pass &= check(
        "get_history(limit=1) returns exactly 1 item",
        len(paged["items"]) == 1,
        f"got {len(paged['items'])}"
    )
    all_pass &= check(
        "get_history(limit=1) total still reflects real total",
        paged["total"] == history["total"],
        f"paged.total={paged['total']} vs full.total={history['total']}"
    )

    # Empty offset beyond total
    beyond = get_history(offset=9999)
    all_pass &= check(
        "get_history(offset=9999) returns empty items list",
        len(beyond["items"]) == 0,
        f"got {len(beyond['items'])}"
    )

    return all_pass


# ---------------------------------------------------------------------------
# Test: get_todo_list(filters)
# ---------------------------------------------------------------------------

def test_get_todo_list_filters():
    section("TEST 3 — get_todo_list(filters)")

    # No filters — baseline (should work like before)
    full = get_todo_list()
    all_pass = True

    all_pass &= check(
        "get_todo_list() (no filter) returns dict with meeting_items and issue_items",
        "meeting_items" in full and "issue_items" in full,
    )

    all_pending_count = len(full["meeting_items"]) + len(full["issue_items"])
    all_pass &= check(
        "No-filter returns >= 1 pending item",
        all_pending_count >= 1,
        f"got {all_pending_count}"
    )

    # Filter by urgency=critical
    critical = get_todo_list(urgency="critical")
    crit_items = critical["meeting_items"] + critical["issue_items"]
    all_pass &= check(
        "get_todo_list(urgency='critical') returns only critical items",
        all(i.get("urgency") == "critical" for i in crit_items),
        f"items: {[i.get('urgency') for i in crit_items]}"
    )
    all_pass &= check(
        "get_todo_list(urgency='critical') >= 1 result (item B is critical)",
        len(crit_items) >= 1,
        f"got {len(crit_items)}"
    )

    # Filter by type=question
    questions = get_todo_list(type="question")
    q_items = questions["meeting_items"] + questions["issue_items"]
    all_pass &= check(
        "get_todo_list(type='question') returns only question-type items",
        all(i.get("type") == "question" for i in q_items),
        f"types: {[i.get('type') for i in q_items]}"
    )

    # Filter by type=issue
    issues_only = get_todo_list(type="issue")
    iss_items = issues_only["meeting_items"] + issues_only["issue_items"]
    all_pass &= check(
        "get_todo_list(type='issue') returns only issue-type items",
        all(i.get("type") == "issue" for i in iss_items),
        f"types: {[i.get('type') for i in iss_items]}"
    )

    # Stacked filters: urgency=critical + type=commitment
    stacked = get_todo_list(urgency="critical", type="commitment")
    stacked_items = stacked["meeting_items"] + stacked["issue_items"]
    all_pass &= check(
        "Stacked filter (critical + commitment) — all items are critical commitments",
        all(i.get("urgency") == "critical" and i.get("type") == "commitment" for i in stacked_items),
        f"got {[(i.get('urgency'), i.get('type')) for i in stacked_items]}"
    )

    # Invalid filter — should not crash, just return empty
    invalid = get_todo_list(urgency="invalid_value")
    inv_items = invalid["meeting_items"] + invalid["issue_items"]
    all_pass &= check(
        "get_todo_list(urgency='invalid_value') does not crash and returns 0 items",
        len(inv_items) == 0,
        f"got {len(inv_items)}"
    )

    return all_pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("\n" + "="*60)
    print("  DIGEST MODULE — FULL TEST SUITE")
    print("="*60)

    id_a, id_b, id_c, id_d, id_e = setup()

    results = {}
    results["get_digest"]         = test_get_digest(id_a, id_b, id_c, id_d, id_e)
    results["get_history"]        = test_get_history(id_a)
    results["get_todo_list_filters"] = test_get_todo_list_filters()

    section("SUMMARY")
    all_ok = True
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status} {name}")
        all_ok = all_ok and passed

    print()
    if all_ok:
        print("  \033[92mAll tests passed.\033[0m")
    else:
        print("  \033[91mSome tests failed — see above.\033[0m")
    print()

if __name__ == "__main__":
    main()
