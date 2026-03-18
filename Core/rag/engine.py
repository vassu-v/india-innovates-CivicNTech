import os
import json
import sqlite3
import struct
import datetime
from dotenv import load_dotenv
import google.genai as genai
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env")) # Standalone RAG .env
load_dotenv() # Fallback to CWD .env
api_key = os.environ.get("GEMINI_API_KEY")

DB_PATH = os.path.join(os.path.dirname(__file__), "rag.db")
MODEL_NAME = "all-MiniLM-L6-v2"
THRESHOLD = 0.35 # Cosine similarity threshold (lower is more flexible)

# Load model lazily
_model = None
def get_model():
    global _model
    if _model is None:
        print(f"Loading SentenceTransformer model {MODEL_NAME}...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def get_client():
    if api_key:
        return genai.Client(api_key=api_key)
    return None

def get_db():
    db = sqlite3.connect(DB_PATH)
    try:
        import sqlite_vec
        db.enable_load_extension(True)
        sqlite_vec.load(db)
    except (AttributeError, sqlite3.OperationalError, ImportError):
        pass
    finally:
        try:
            db.enable_load_extension(False)
        except Exception:
            pass
    db.row_factory = sqlite3.Row
    return db

def serialize_f32(vector):
    """Serializes a list of floats into a format sqlite-vec expects"""
    return struct.pack(f"{len(vector)}f", *vector)

def init_db():
    db = get_db()
    
    # Metadata storage
    db.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_nodes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        domain      TEXT,       -- 'commitment_history' | 'context_file' | 'complaint_pattern'
        ward        TEXT,       -- 'Ward 42' | null for general
        topic       TEXT,       -- 'drainage' | 'water' | etc
        title       TEXT,       -- short label for source attribution
        content     TEXT,       -- the actual text sent to LLM
        source_ref  TEXT,       -- 'timely_items:42' | 'context_files:3'
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Vector index (virtual table if sqlite-vec is available)
    try:
        db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_knowledge USING vec0(
            node_id   INTEGER PRIMARY KEY,
            embedding float[384]
        )
        """)
    except sqlite3.OperationalError:
        print("Warning: sqlite-vec not available. Using normal table for embeddings fallback.")
        db.execute("""
        CREATE TABLE IF NOT EXISTS vec_knowledge (
            node_id   INTEGER PRIMARY KEY,
            embedding BLOB
        )
        """)
    db.commit()
    db.close()

def store_node(domain, ward, topic, title, content, source_ref):
    """
    Ingests a new knowledge node.
    """
    model = get_model()
    embedding = model.encode(content)
    embedding_bytes = serialize_f32(embedding.tolist())
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO knowledge_nodes (domain, ward, topic, title, content, source_ref)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (domain, ward, topic, title, content, source_ref))
    
    node_id = cursor.lastrowid
    
    try:
        cursor.execute("INSERT INTO vec_knowledge (node_id, embedding) VALUES (?, ?)", (node_id, embedding_bytes))
    except sqlite3.OperationalError:
        pass
        
    db.commit()
    db.close()
    return node_id

def cosine_similarity(v1, v2):
    import math
    sumxx, sumyy, sumxy = 0, 0, 0
    for x, y in zip(v1, v2):
        sumxx += x*x
        sumyy += y*y
        sumxy += x*y
    if sumxx == 0 or sumyy == 0: return 0
    return sumxy / (math.sqrt(sumxx) * math.sqrt(sumyy))

def query_nodes(query_text, limit=5, ward_filter=None):
    """
    Searches for semantically relevant nodes.
    """
    model = get_model()
    query_embedding = model.encode(query_text)
    query_bytes = serialize_f32(query_embedding.tolist())
    
    db = get_db()
    cursor = db.cursor()
    
    nodes = []
    try:
        # A. Try sqlite-vec first
        sql = """
            SELECT n.*, vec_distance_cosine(v.embedding, ?) as distance
            FROM vec_knowledge v
            JOIN knowledge_nodes n ON v.node_id = n.id
        """
        params = [query_bytes]
        if ward_filter:
            sql += " WHERE n.ward = ? OR n.ward IS NULL"
            params.append(ward_filter)
        sql += " ORDER BY distance ASC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        for r in rows:
            node = dict(r)
            node['similarity'] = 1.0 - r['distance']
            nodes.append(node)
            
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        # B. Fallback to in-memory similarity
        cursor.execute("SELECT * FROM knowledge_nodes")
        all_meta = cursor.fetchall()
        
        cursor.execute("SELECT * FROM vec_knowledge")
        all_vecs = {r['node_id']: r['embedding'] for r in cursor.fetchall()}
        
        q_vec = query_embedding.tolist()
        results = []
        
        for meta in all_meta:
            nid = meta['id']
            if nid in all_vecs and all_vecs[nid]:
                # Filter by ward if requested
                if ward_filter and meta['ward'] and meta['ward'] != ward_filter:
                    continue
                    
                v_bytes = all_vecs[nid]
                v_vec = struct.unpack(f"{len(q_vec)}f", v_bytes)
                sim = cosine_similarity(q_vec, v_vec)
                if sim >= THRESHOLD:
                    node = dict(meta)
                    node['similarity'] = sim
                    results.append(node)
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        nodes = results[:limit]
        
    db.close()
    return nodes

def assemble_context(query, profile=None, digest=None, top_items=None, clusters=None):
    """
    Assembles the 3-layer context for Gemini.
    Returns (context_string, retrieved_nodes).
    """
    # LAYER 2: Vector Retrieval (Perform first to avoid double calls)
    nodes = query_nodes(query, limit=5)
    
    # LAYER 1: Always-on (Profile + Digest)
    l1 = "=== LAYER 1: LIVE CONSTITUENCY STATE ===\n"
    if profile:
        l1 += f"MLA: {profile.get('name', 'N/A')} ({profile.get('party', 'N/A')})\n"
        l1 += f"Constituency: {profile.get('ward_name', 'N/A')}\n"
        l1 += f"Janata Darbar: {profile.get('janata_darbar_day', 'N/A')} at {profile.get('janata_darbar_time', 'N/A')}\n"
    
    if digest:
        l1 += f"Resolution Rate: {digest.get('resolved', {}).get('resolution_rate', 'N/A')}%\n"
        l1 += f"Critical Items: {digest.get('open_right_now', {}).get('critical', 0)}\n"
        l1 += f"Urgent Items: {digest.get('open_right_now', {}).get('urgent', 0)}\n"
        
    if top_items:
        l1 += "\nTop Pending Items:\n"
        for item in top_items[:3]:
            l1 += f"- {item.get('title')} ({item.get('urgency')}, {item.get('days_overdue', 0)} days overdue)\n"

    l2 = "\n=== LAYER 2: HISTORICAL FACTS & CONTEXT ===\n"
    if nodes:
        for node in nodes:
            l2 += f"[{node['domain']}] {node['title']}: {node['content']}\n"
            l2 += f"(Ref: {node['source_ref']})\n\n"
    else:
        l2 += "No relevant historical facts found.\n"

    # LAYER 3: Live SQL (Complaints)
    l3 = "\n=== LAYER 3: CURRENT COMPLAINT PATTERNS ===\n"
    if clusters:
        for c in clusters[:3]:
            l3 += f"- {c.get('summary')} (Ward: {c.get('ward')}, Weight: {c.get('weight')}, Urgency: {c.get('urgency')})\n"
    else:
        l3 += "No active complaint clusters.\n"
        
    return l1 + l2 + l3, nodes

def chat(query, profile=None, digest=None, top_items=None, clusters=None):
    """
    Main entry point for chat.
    """
    context, nodes = assemble_context(query, profile, digest, top_items, clusters)
    
    client = get_client()
    if not client:
        return {"response": "Error: Gemini API key not found in .env.", "sources": []}
        
    prompt = f"""
You are Co-Pilot, an AI assistant for an Indian MLA.
You have access to the MLA's complete governance data through the context below.

SYSTEM INSTRUCTIONS:
1. Answer using ONLY the provided context.
2. Be specific. Reference actual data, counts, and dates from the context.
3. If the context is insufficient, say so clearly.
4. End with one actionable recommendation where relevant.
5. Keep responses to 3-5 sentences unless a breakdown is needed.
6. Cite source type inline: (commitment_history), (complaint_pattern), (context_file).

CONTEXT:
{context}

QUESTION:
{query}
"""
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
        )
        
        # Reuse nodes from assemble_context
        sources = [{"id": n["id"], "domain": n["domain"], "title": n["title"]} for n in nodes]
        
        return {
            "response": response.text.strip(),
            "sources": sources,
            "raw_context": context # Helpful for debugging standalone
        }
    except Exception as e:
        return {
            "response": f"Error calling Gemini: {e}", 
            "sources": [],
            "raw_context": context
        }

def generate_suggestions(profile=None, digest=None, clusters=None, top_items=None):
    """
    Generates strategic suggestions based on live state.
    """
    client = get_client()
    if not client:
        return []

    # Assemble simplified context for suggestions
    context = ""
    if profile:
        context += f"MLA: {profile.get('name')}, Ward: {profile.get('ward_name')}\n"
    if digest:
        context += f"Stats: {digest.get('resolved', {}).get('resolution_rate')}% resolved. "
        context += f"{digest.get('open_right_now', {}).get('critical')} critical items.\n"
    if clusters:
        context += "\nActive Complaint Clusters:\n"
        for c in clusters[:3]:
            context += f"- {c.get('summary')} (Weight: {c.get('weight')})\n"
    if top_items:
        context += "\nTop Pending Items:\n"
        for item in top_items[:3]:
            context += f"- {item.get('title')} ({item.get('urgency')})\n"

    prompt = f"""
You are a strategic advisor for an Indian MLA. 
Based on the live constituency data below, provide 3-4 actionable suggestions.

DATA:
{context}

OUTPUT FORMAT:
Return a JSON array of objects only. Each object must have:
- priority: "critical" | "urgent" | "normal"
- title: concise heading (max 8 words)
- body: 2-3 sentences explaining the "why" and "how" based on the data.

No markdown. No explanation. Just JSON.
"""
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
        )
        raw = response.text.strip()
        if raw.startswith("```json"): raw = raw[7:]
        if raw.startswith("```"): raw = raw[3:]
        if raw.endswith("```"): raw = raw[:-3]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"Suggestions error: {e}")
        return []

def truncate_db():
    db = get_db()
    db.execute("DELETE FROM knowledge_nodes")
    try:
        db.execute("DELETE FROM vec_knowledge")
    except sqlite3.OperationalError:
        pass
    db.execute("DELETE FROM sqlite_sequence WHERE name='knowledge_nodes'")
    db.commit()
    db.close()
