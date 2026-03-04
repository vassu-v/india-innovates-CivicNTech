import sqlite3
import sqlite_vec
from datetime import datetime
from sentence_transformers import SentenceTransformer
import struct
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "copilot.db")
MODEL_NAME = "all-MiniLM-L6-v2"
THRESHOLD = 0.5 # Cosine similarity threshold (1.0 - distance). Lower is more flexible

def normalize_ward(ward_str):
    """
    Normalizes ward string: lowercase, remove spaces, extract number if possible.
    'Ward 8' -> '8', 'ward8' -> '8', 'South Delhi' -> 'southdelhi'
    """
    if not ward_str:
        return "general"
    s = str(ward_str).lower().replace(" ", "").replace("ward", "")
    return s if s else "general"

def cosine_similarity(v1, v2):
    """Simple in-memory cosine similarity calculation."""
    import math
    sumxx, sumyy, sumxy = 0, 0, 0
    for i in range(len(v1)):
        x = v1[i]; y = v2[i]
        sumxx += x*x
        sumyy += y*y
        sumxy += x*y
    if sumxx == 0 or sumyy == 0:
        return 0
    return sumxy / (math.sqrt(sumxx) * math.sqrt(sumyy))

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
    try:
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
    except AttributeError:
        # Fallback for systems where enable_load_extension is not available
        # or sqlite-vec is not needed for basic operations
        pass
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
    try:
        db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_clusters USING vec0(
            cluster_id INTEGER PRIMARY KEY,
            embedding float[384]
        )
        """)
    except sqlite3.OperationalError:
        print("Warning: sqlite-vec not available. Vector features will be limited.")
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
        
    try:
        embedding = model.encode(text)
        embedding_bytes = serialize_f32(embedding.tolist())
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        embedding_bytes = None
    
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
    
    # 3. Search for similar clusters
    match = None
    max_distance = 1.0 - THRESHOLD
    normalized_ward = normalize_ward(complaint_data.get('ward'))

    if embedding_bytes:
        try:
            # A. Try sqlite-vec first
            cursor.execute("""
                SELECT v.cluster_id, vec_distance_cosine(v.embedding, ?) as distance
                FROM vec_clusters v
                INNER JOIN clusters c ON v.cluster_id = c.id
                WHERE LOWER(REPLACE(REPLACE(c.ward, ' ', ''), 'ward', '')) = ?
                ORDER BY distance ASC
                LIMIT 1
            """, (embedding_bytes, normalized_ward))
            match = cursor.fetchone()
        except sqlite3.OperationalError:
            # B. Fallback to in-memory similarity if sqlite-vec is missing
            cursor.execute("""
                SELECT c.id, v.embedding 
                FROM clusters c
                JOIN vec_clusters v ON c.id = v.cluster_id
                WHERE LOWER(REPLACE(REPLACE(c.ward, ' ', ''), 'ward', '')) = ?
            """, (normalized_ward,))
            all_clusters = cursor.fetchall()
            
            best_sim = -1
            best_id = None
            
            if all_clusters:
                current_v = embedding.tolist()
                for cluster_id, eb in all_clusters:
                    if eb:
                        cluster_v = struct.unpack(f"{len(current_v)}f", eb)
                        sim = cosine_similarity(current_v, cluster_v)
                        if sim > best_sim:
                            best_sim = sim
                            best_id = cluster_id
            
            if best_id and best_sim >= THRESHOLD:
                match = {'cluster_id': best_id, 'distance': 1.0 - best_sim}
        
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
        target_summary = text[:100] + "..." if len(text) > 100 else text
        cursor.execute("""
            INSERT INTO clusters (summary, ward, weight, urgency, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (target_summary, complaint_data.get('ward'), 1, "normal", now))
        
        target_cluster_id = cursor.lastrowid
        
        if embedding_bytes:
            try:
                cursor.execute("""
                    INSERT INTO vec_clusters (cluster_id, embedding)
                    VALUES (?, ?)
                """, (target_cluster_id, embedding_bytes))
            except sqlite3.OperationalError:
                pass
        
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

def get_recent_complaints(limit=5):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM complaints
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    db.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
