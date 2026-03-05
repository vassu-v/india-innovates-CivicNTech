import commitment_engine
import issue_engine
import datetime
import sys

def seed(reset=False):
    if reset:
        print("Resetting databases...")
        commitment_engine.truncate_db()
        issue_engine.truncate_db()

    print("Initializing databases...")
    commitment_engine.init_db()
    issue_engine.init_db()

    print("Seeding MLA profile...")
    # Profile is initialized with defaults in init_db, but let's update it to be sure
    commitment_engine.update_profile({
        "name": "Shri Rajendra Kumar Verma",
        "party": "Indian National Congress",
        "designation": "MLA",
        "ward_name": "Ward 42 — South Delhi"
    })

    print("Seeding commitments and actions...")
    today = datetime.datetime.now().date().isoformat()
    past_date = (datetime.datetime.now() - datetime.timedelta(days=10)).date().isoformat()

    # 1. A critical overdue commitment
    commitment_engine.add_item({
        "text": "Fix the broken streetlights in Sector 4",
        "type": "commitment",
        "meeting_date": past_date,
        "source_id": "meeting_transcript_feb_20.txt"
    })

    # 2. A normal pending action
    commitment_engine.add_item({
        "text": "Review the budget for monsoon preparation",
        "type": "action",
        "meeting_date": today,
        "source_id": "manual"
    })

    # 3. A question
    commitment_engine.add_item({
        "text": "Status of the new park construction in Ward 42?",
        "type": "question",
        "meeting_date": today,
        "source_id": "meeting_transcript_today.txt"
    })

    print("Seeding citizen complaints...")
    complaints = [
        {
            "citizen_name": "Amit Shah",
            "citizen_contact": "9876543210",
            "ward": "Ward 42",
            "channel": "Walk-in visit",
            "complaint_text": "Severe water logging in front of my house due to blocked drains.",
            "date_received": today
        },
        {
            "citizen_name": "Sita Ram",
            "citizen_contact": "9123456789",
            "ward": "Ward 42",
            "channel": "Physical letter",
            "complaint_text": "The drains in Sector 4 are completely blocked and causing overflow.",
            "date_received": today
        },
        {
            "citizen_name": "John Doe",
            "citizen_contact": "8888888888",
            "ward": "Ward 8",
            "channel": "CPGRAMS portal",
            "complaint_text": "Garbage collection has not happened for 3 days in our area.",
            "date_received": today
        }
    ]

    for comp in complaints:
        # Cluster via Issue Engine
        cluster_res = issue_engine.process_complaint(comp)
        # Add to Commitment Engine to show in To-Do
        commitment_engine.add_item(cluster_res)

    print("Seeding completed items for history...")
    item_id = commitment_engine.add_item({
        "text": "Send thank you note to the residents of Ward 42",
        "type": "action",
        "meeting_date": past_date,
        "source_id": "manual"
    })
    commitment_engine.complete_item(item_id, "Sent successfully via email.")

    print("Seeding complete!")

if __name__ == "__main__":
    reset_db = "--reset" in sys.argv
    seed(reset=reset_db)
