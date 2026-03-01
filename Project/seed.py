import commitment_engine
import issue_engine
import datetime

def seed():
    commitment_engine.init_db()
    issue_engine.init_db()
    
    # Current date for reference
    today = datetime.datetime.now().date()
    yesterday = (today - datetime.timedelta(days=1)).isoformat()
    last_week = (today - datetime.timedelta(days=8)).isoformat()
    
    # 1. Add some meeting items
    commitment_engine.add_item({
        "text": "I will follow up with PWD on Ward 42 drainage issue by next Monday",
        "type": "commitment",
        "meeting_date": last_week,
        "source_id": "ward_coord_meeting.m4a"
    })
    
    commitment_engine.add_item({
        "text": "Need to check PM Awas Yojana eligibility for Ward 8 residents",
        "type": "question",
        "meeting_date": yesterday,
        "source_id": "janata_darbar_feb25.txt"
    })
    
    # 2. Add some issue clusters
    commitment_engine.add_item({
        "cluster_id": 101,
        "cluster_summary": "Street light outage in Sector 4, Ward 17",
        "ward": "Ward 17",
        "weight": 5,
        "urgency": "urgent"
    })
    
    commitment_engine.add_item({
        "cluster_id": 102,
        "cluster_summary": "Water supply irregular in Ward 8",
        "ward": "Ward 8",
        "weight": 2,
        "urgency": "normal"
    })
    
    print("Database seeded with sample data in 'copilot.db'")

if __name__ == "__main__":
    seed()
