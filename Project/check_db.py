import sqlite3
import os
import commitment_engine

DB_PATH = "c:/Users/Shorya/Desktop/II26-CNT-CoPilot/Project/copilot.db"

def check():
    commitment_engine.init_db() # Force initialization
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='profile'")
        if not cursor.fetchone():
            print("Table 'profile' DOES NOT EXIST")
            return
        
        cursor.execute("PRAGMA table_info(profile)")
        cols = cursor.fetchall()
        print("Columns in 'profile' table:")
        for col in cols:
            print(f" - {col[1]} ({col[2]})")
            
        cursor.execute("SELECT * FROM profile")
        row = cursor.fetchone()
        if row:
            print(f"Data in row 1: {row}")
        else:
            print("No data in 'profile' table")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check()
