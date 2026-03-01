import sqlite3
import os

DB_PATH = "copilot.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("--- Tables ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for t in tables:
        print(t[0])
        
    print("\n--- Profile Table Content ---")
    try:
        cursor.execute("SELECT * FROM profile")
        rows = cursor.fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Error reading profile: {e}")
        
    print("\n--- Profile Table Schema ---")
    try:
        cursor.execute("PRAGMA table_info(profile)")
        cols = cursor.fetchall()
        for c in cols:
            print(c)
    except Exception as e:
        print(f"Error reading schema: {e}")
        
    conn.close()

if __name__ == "__main__":
    check_db()
