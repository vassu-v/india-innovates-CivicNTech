import os
from issue_engine import init_db, process_complaint, DB_PATH

def run_tests():
    # clean old db
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    init_db()
    print("Running Tests...\n")
    
    print("1. Filing 6 complaints about drainage in Ward 42...")
    complaints = [
        "The drainage on main street is overflowing into the road.",
        "Overflowing drains near the park in ward 42, please fix.",
        "Sewage water from blocked drain on main road.",
        "Drainage is completely clogged and spilling dirty water.",
        "Please unblock the drainage system, it is overflowing again.",
        "Road is flooded because of blocked drainage pipes."
    ]
    
    first_cluster_id = None
    res = None
    
    for i, text in enumerate(complaints):
        res = process_complaint({
            "complaint_text": text,
            "ward": "Ward 42",
            "citizen_name": f"Citizen {i}",
            "channel": "portal",
            "date_received": "2023-10-01"
        })
        print(f"Complaint {i+1} -> Action: {res['action']}, Cluster: {res['cluster_id']}, Weight: {res['weight']}, Urgency: {res['urgency']}")
        
        if i == 0:
            assert res['action'] == "new_cluster_created"
            first_cluster_id = res['cluster_id']
        else:
            assert res['action'] == "added_to_existing"
            assert res['cluster_id'] == first_cluster_id
            
    assert res is not None
    assert res['weight'] == 6
    assert res['urgency'] == "critical"
    print("\nSUCCESS: Drainage complaints successfully clustered together to Critical weight!\n")
    
    print("2. Filing a new complaint about street lights in Ward 17...")
    res2 = process_complaint({
        "complaint_text": "The street light in front of my house in Ward 17 is broken and it's completely dark.",
        "ward": "Ward 17",
        "citizen_name": "Citizen 7",
        "channel": "portal",
        "date_received": "2023-10-02"
    })
    
    print(f"Streetlight Complaint -> Action: {res2['action']}, Cluster: {res2['cluster_id']}, Weight: {res2['weight']}, Urgency: {res2['urgency']}")
    assert res2['action'] == "new_cluster_created"
    assert res2['cluster_id'] != first_cluster_id
    
    print("\nSUCCESS: Streetlight complaint successfully formed a new cluster!")
    print("\nAll tests passed successfully! MVP is working as expected.")

if __name__ == "__main__":
    run_tests()
