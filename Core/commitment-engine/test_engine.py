from engine import init_db, add_item, escalate, get_todo_list, complete_item, get_stats
import json
import os

def run_simplest_possible_test():
    print("--- Starting Simplest Possible Test ---")
    
    # 1. Init DB (ensure fresh for testing, remove if exists)
    if os.path.exists("timely.db"):
        os.remove("timely.db")
    init_db()
    
    print("\n1. Adding Meeting Commitment...")
    input_1 = {
        "text": "I will personally follow up with PWD commissioner today and ensure work begins by 5th March",
        "type": "commitment",
        "meeting_date": "2026-03-01",
        "source_id": "test_meeting.m4a"
    }
    item_1_id = add_item(input_1)
    print(f"Added item 1 with ID: {item_1_id}")
    
    print("\n2. Adding Meeting Question (Past deadline to test escalation)...")
    input_2 = {
        "text": "Can you check PM Awas Yojana applications from Ward 8?",
        "type": "question",
        "meeting_date": "2026-02-01",
        "source_id": "test_meeting.m4a"
    }
    item_2_id = add_item(input_2)
    print(f"Added item 2 with ID: {item_2_id}")
    
    print("\n3. Adding Fake Issue Cluster...")
    input_3 = {
        "cluster_summary": "Drainage overflow Ward 42",
        "weight": 6,
        "urgency": "critical",
        "ward": "Ward 42",
        "cluster_id": 999
    }
    item_3_id = add_item(input_3)
    print(f"Added item 3 with ID: {item_3_id}")
    
    print("\n4. Calling escalate()...")
    escalate()
    
    print("\n5. Fetching To-Do List...")
    todo_list = get_todo_list()
    print("Meeting Items:")
    print(json.dumps(todo_list["meeting_items"], indent=2))
    print("\nIssue Items:")
    print(json.dumps(todo_list["issue_items"], indent=2))
    
    print("\n6. Completing Item 1...")
    fact_string = complete_item(item_1_id, resolution_notes="Completed the follow up and work started.")
    print("Generated Fact String for RAG:")
    print(fact_string)
    
    print("\n7. Fetching Stats...")
    stats = get_stats()
    print(json.dumps(stats, indent=2))
    
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    run_simplest_possible_test()
