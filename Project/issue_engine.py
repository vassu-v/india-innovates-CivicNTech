import sqlite3
import sqlite_vec
from datetime import datetime
from sentence_transformers import SentenceTransformer
import struct
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "copilot.db")
MODEL_NAME = "all-MiniLM-L6-v2"
THRESHOLD = 0.5 # Cosine similarity threshold (1.0 - distance). Lower is more flexible

# Load model lazily
_model = None
def get_model():
    global _model
    if _model is None:
        print(f"Loading SentenceTransformer model {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    db.row_factory = sqlite3.Row
    return db

def serialize_f32(vector):
    """serializes a list of floats into a compact format sqlite-vec expects"""
    return struct.pack(f"{len(vector)}f", *vector)

def init_db():
    db = get_db()
    
    # Static tables
    db.execute("""
    CREATE TABLE IF NOT EXISTS clusters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        summary TEXT,
        ward TEXT,
        weight INTEGER DEFAULT 1,
        status TEXT DEFAULT 'open',
        urgency TEXT DEFAULT 'normal',
        created_at TIMESTAMP,
        resolved_at DATE
    )
    """)
    
    db.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        citizen_name TEXT,
        citizen_contact TEXT,
        ward TEXT,
        channel TEXT,
        raw_description TEXT,
        date_received DATE,
        status TEXT DEFAULT 'pending',
        cluster_id INTEGER,
        staff_notes TEXT,
        resolved_at DATE,
        created_at TIMESTAMP,
        FOREIGN KEY(cluster_id) REFERENCES clusters(id)
    )
    """)
    
    # Vector table (virtual table in sqlite-vec)
    db.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS vec_clusters USING vec0(
        cluster_id INTEGER PRIMARY KEY,
        embedding float[384]
    )
    """)
    db.commit()
    db.close()

def determine_urgency(weight):
    if weight <= 2:
        return "normal"
    elif weight <= 4:
        return "urgent"
    else:
        return "critical"

def process_complaint(complaint_data):
    """
    Takes a complaint dict and returns matched or new cluster info.
    """
    model = get_model()
    db = get_db()
    cursor = db.cursor()
    
    # 1. Generate embedding
    text = complaint_data.get('complaint_text', '')
    if not text:
        raise ValueError("complaint_text is required")
        
    embedding = model.encode(text)
    embedding_bytes = serialize_f32(embedding.tolist())
    
    now = datetime.now().isoformat()
    
    # 2. Store complaint temporarily without cluster_id to get its ID
    cursor.execute("""
        INSERT INTO complaints (
            citizen_name, citizen_contact, ward, channel, 
            raw_description, date_received, staff_notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        complaint_data.get('citizen_name'),
        complaint_data.get('citizen_contact'),
        complaint_data.get('ward'),
        complaint_data.get('channel'),
        text,
        complaint_data.get('date_received'),
        complaint_data.get('staff_notes'),
        now
    ))
    complaint_id = cursor.lastrowid
    
    # 3. Search for similar clusters using cosine distance
    # sqlite-vec distance_cosine: 0.0=identical, 2.0=opposite.
    # similarity 0.75 means distance <= 0.25 (as 1 - 0.75 = 0.25)
    max_distance = 1.0 - THRESHOLD
    
    cursor.execute("""
        SELECT v.cluster_id, vec_distance_cosine(v.embedding, ?) as distance
        FROM vec_clusters v
        INNER JOIN clusters c ON v.cluster_id = c.id
        WHERE c.ward = ?
        ORDER BY distance ASC
        LIMIT 1
    """, (embedding_bytes, complaint_data.get('ward')))
    
    match = cursor.fetchone()
        
    action = ""
    target_cluster_id = None
    target_summary = ""
    new_weight = 1
    urgency = "normal"
    
    if match and match['distance'] <= max_distance:
        # 5A - Similar found
        target_cluster_id = match['cluster_id']
        
        # update cluster weight & summary
        cursor.execute("SELECT summary, weight FROM clusters WHERE id = ?", (target_cluster_id,))
        cluster_row = cursor.fetchone()
        
        current_summary = cluster_row['summary']
        
        # Only update summary if the new complaint adds structural or semantic new context.
        # We use the distance score as a heuristic: if distance > 0.15, it's phrased differently 
        # enough (or has new keywords) to justify appending it to the summary.
        target_summary = current_summary
        if match['distance'] > 0.15 and len(target_summary) < 150:
            addition = text[:50].strip()
            if addition.lower() not in target_summary.lower():
                target_summary += " | " + addition
                
        new_weight = cluster_row['weight'] + 1
        urgency = determine_urgency(new_weight)
        
        cursor.execute("""
            UPDATE clusters 
            SET weight = ?, urgency = ?, summary = ?
            WHERE id = ?
        """, (new_weight, urgency, target_summary, target_cluster_id))
        
        action = "added_to_existing"
    else:
        # 5B - New issue
        # Create new cluster
        target_summary = text[:100] + "..." if len(text) > 100 else text # simple summary
        cursor.execute("""
            INSERT INTO clusters (summary, ward, weight, urgency, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (target_summary, complaint_data.get('ward'), 1, "normal", now))
        
        target_cluster_id = cursor.lastrowid
        
        # Store embedding
        cursor.execute("""
            INSERT INTO vec_clusters (cluster_id, embedding)
            VALUES (?, ?)
        """, (target_cluster_id, embedding_bytes))
        
        action = "new_cluster_created"
        
    # Link complaint to cluster
    cursor.execute("""
        UPDATE complaints SET cluster_id = ? WHERE id = ?
    """, (target_cluster_id, complaint_id))
    
    db.commit()
    db.close()
    
    return {
        "action": action,
        "cluster_id": target_cluster_id,
        "cluster_summary": target_summary,
        "weight": new_weight,
        "urgency": urgency,
        "complaint_id": complaint_id
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
