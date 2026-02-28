import os
from datetime import datetime
from issue_engine import init_db, process_complaint, get_db, DB_PATH

def print_separator():
    print("-" * 60)

def file_complaint():
    print("\n--- File a New Complaint ---")
    text = input("Complaint Description: ").strip()
    if not text:
        print("Description cannot be empty.")
        return
        
    ward = input("Ward (e.g., Ward 42): ").strip()
    name = input("Citizen Name (optional): ").strip()
    
    complaint_data = {
        "complaint_text": text,
        "ward": ward if ward else "Unknown",
        "citizen_name": name if name else "Anonymous",
        "channel": "cli",
        "date_received": datetime.now().strftime("%Y-%m-%d")
    }
    
    print("\nProcessing... (generating embeddings and searching clusters)")
    try:
        result = process_complaint(complaint_data)
        print("\n✅ Complaint Processed Successfully!")
        print(f"Action Taken : {result['action']}")
        print(f"Cluster ID   : {result['cluster_id']}")
        print(f"Cluster Theme: {result['cluster_summary']}")
        print(f"Total Weight : {result['weight']}")
        print(f"Urgency      : {result['urgency'].upper()}")
    except Exception as e:
        print(f"\n❌ Error processing complaint: {e}")

def view_clusters():
    print("\n--- Current Issue Clusters ---")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, summary, ward, weight, urgency, status 
        FROM clusters 
        ORDER BY weight DESC, id ASC
    """)
    clusters = cursor.fetchall()
    
    if not clusters:
        print("No clusters found. The database is empty.")
        db.close()
        return
        
    print(f"{'ID':<4} | {'Ward':<10} | {'Weight':<6} | {'Urgency':<10} | {'Status':<10} | {'Summary'}")
    print_separator()
    for c in clusters:
        summary_short = c['summary'][:50] + "..." if len(c['summary']) > 50 else c['summary']
        print(f"{c['id']:<4} | {c['ward']:<10} | {c['weight']:<6} | {c['urgency']:<10} | {c['status']:<10} | {summary_short}")
    print_separator()
    db.close()

def view_complaints():
    print("\n--- All Complaints ---")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT id, cluster_id, ward, citizen_name, raw_description 
        FROM complaints 
        ORDER BY id DESC
        LIMIT 20
    """)
    complaints = cursor.fetchall()
    
    if not complaints:
        print("No complaints found.")
        db.close()
        return
        
    print(f"{'ID':<4} | {'Cluster':<7} | {'Ward':<10} | {'Citizen':<15} | {'Description'}")
    print_separator()
    for c in complaints:
        desc_short = c['raw_description'][:40] + "..." if c['raw_description'] and len(c['raw_description']) > 40 else c['raw_description']
        cluster_val = str(c['cluster_id']) if c['cluster_id'] else "None"
        print(f"{c['id']:<4} | {cluster_val:<7} | {c['ward']:<10} | {c['citizen_name']:<15} | {desc_short}")
    print_separator()
    print("Showing up to 20 most recent complaints.")
    db.close()

def reset_database():
    confirm = input("\nAre you sure you want to delete all data? (yes/no): ").strip().lower()
    if confirm == 'yes':
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        print("✅ Database reset successfully.")
    else:
        print("Reset cancelled.")

def main_menu():
    # Ensure DB exists
    if not os.path.exists(DB_PATH):
        init_db()
        
    while True:
        print("\n" + "="*40)
        print("      ISSUE ENGINE INTERACTIVE CLI      ")
        print("="*40)
        print("1. File a New Complaint")
        print("2. View All Clusters (Grouped Issues)")
        print("3. View Recent Complaints")
        print("4. Reset Database (Delete All Data)")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            file_complaint()
        elif choice == '2':
            view_clusters()
        elif choice == '3':
            view_complaints()
        elif choice == '4':
            reset_database()
        elif choice == '5':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting...")
