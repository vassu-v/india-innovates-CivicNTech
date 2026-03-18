import os
import json
import sqlite3
import struct
import datetime
from dotenv import load_dotenv
import google.genai as genai
from sentence_transformers import SentenceTransformer
import numpy as np

# Load environment variables
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

DB_PATH = os.path.join(os.path.dirname(__file__), "copilot.db")
MODEL_NAME = "all-MiniLM-L6-v2"
THRESHOLD = 0.35 # Cosine similarity threshold

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

_intent_vectors = None

def get_intent_vectors():
    global _intent_vectors
    if _intent_vectors is not None:
        return _intent_vectors
    
    model = get_model()
    # Pre-calculated centroids for "Small Talk" intents
    greetings = ["hi", "hello", "hey", "greetings", "namaste", "good morning", "good evening", "who are you", "what can you do"]
    thanks = ["thanks", "thank you", "much appreciated", "great", "awesome", "nice", "perfect"]
    
    _intent_vectors = {
        "small_talk": model.encode(greetings).mean(axis=0),
        "thanks": model.encode(thanks).mean(axis=0)
    }
    return _intent_vectors

def needs_context(query, recent_node_embeddings=None):
    """
    Local Semantic Router: Detects Small Talk and Contextual Follow-ups.
    Zero tokens, Zero latency.
    """
    model = get_model()
    iv = get_intent_vectors()
    
    q_vec = model.encode([query.lower()])[0]
    
    def cosine_sim(a, b):
        return (a @ b) / (np.linalg.norm(a) * np.linalg.norm(b))

    try:
        import numpy as np
    except ImportError:
        def norm(v): return sum(x*x for x in v)**0.5
        def dot(v1, v2): return sum(x*y for x,y in zip(v1, v2))
        def cosine_sim(a, b): return dot(a, b) / (norm(a) * norm(b))

    # 1. Check Small Talk
    if cosine_sim(q_vec, iv["small_talk"]) > 0.65 or cosine_sim(q_vec, iv["thanks"]) > 0.65:
        return "instant"
        
    # 2. Check Semantic Follow-up (Working Memory)
    if recent_node_embeddings:
        # Check if the query is very similar to any of the nodes we JUST retrieved
        for node_vec in recent_node_embeddings:
            if cosine_sim(q_vec, node_vec) > 0.75:
                return "follow-up"

    return "search"

def store_memory(topic, content):
    db = get_db()
    db.execute("INSERT INTO ai_memory (topic, content) VALUES (?, ?)", (topic, content))
    db.commit()
    db.close()

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
    
    # Vector index
    try:
        db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_knowledge USING vec0(
            node_id   INTEGER PRIMARY KEY,
            embedding float[384]
        )
        """)
    except sqlite3.OperationalError:
        db.execute("""
        CREATE TABLE IF NOT EXISTS vec_knowledge (
            node_id   INTEGER PRIMARY KEY,
            embedding BLOB
        )
        """)

    # AI Self-Memory Table
    db.execute("""
    CREATE TABLE IF NOT EXISTS ai_memory (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        topic       TEXT,
        content     TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    db.commit()
    db.close()

def store_node(domain, ward, topic, title, content, source_ref):
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
    model = get_model()
    query_embedding = model.encode(query_text)
    query_bytes = serialize_f32(query_embedding.tolist())
    
    db = get_db()
    cursor = db.cursor()
    
    nodes = []
    try:
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
        cursor.execute("SELECT * FROM knowledge_nodes")
        all_meta = cursor.fetchall()
        cursor.execute("SELECT * FROM vec_knowledge")
        all_vecs = {r['node_id']: r['embedding'] for r in cursor.fetchall()}
        
        q_vec = query_embedding.tolist()
        results = []
        for meta in all_meta:
            nid = meta['id']
            if nid in all_vecs and all_vecs[nid]:
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
    nodes = query_nodes(query, limit=5)
    
    l1 = "=== LAYER 1: LIVE CONSTITUENCY STATE ===\n"
    if profile:
        l1 += f"MLA: {profile.get('name', 'N/A')}\nConstituency: {profile.get('ward_name', 'N/A')}\n"
    if digest:
        l1 += f"Resolution Rate: {digest.get('resolved', {}).get('resolution_rate', 'N/A')}%\n"
        l1 += f"Critical Count: {digest.get('open_right_now', {}).get('critical', 0)}\n"
    if top_items:
        l1 += "\nPending Tasks:\n"
        for item in top_items[:3]:
            l1 += f"- {item.get('title')} ({item.get('urgency')})\n"

    l2 = "\n=== LAYER 2: HISTORICAL FACTS & AI MEMORY ===\n"
    # Get standard nodes
    for node in nodes:
        l2 += f"[{node['domain']}] {node['title']}: {node['content']}\n"
    
    # Get AI memory nodes
    db = get_db()
    memories = db.execute("SELECT * FROM ai_memory ORDER BY created_at DESC LIMIT 5").fetchall()
    db.close()
    for m in memories:
        l2 += f"[ai_memory] {m['topic']}: {m['content']} (Learned: {m['created_at']})\n"

    l3 = "\n=== LAYER 3: LIVE PATTERNS ===\n"
    if clusters:
        for c in clusters[:3]:
            l3 += f"- {c.get('summary')} (Weight: {c.get('weight')})\n"
            
    return l1 + l2 + l3, nodes

def chat(query, profile=None, digest=None, top_items=None, clusters=None):
    context, nodes = assemble_context(query, profile, digest, top_items, clusters)
    client = get_client()
    if not client: return {"response": "API Key missing.", "sources": []}
    
    prompt = f"""You are Co-Pilot, an AI assistant for an Indian MLA.
You have access to the MLA's complete governance data through the context below.

SYSTEM INSTRUCTIONS:
1. Answer using ONLY the provided context.
2. Be specific. Reference actual data, counts, and dates.
3. If the context is insufficient, say so clearly.
4. Cite source type inline: (commitment_history), (complaint_pattern), (context_file).

SELF-INDEXING (AI MEMORY):
If you learn something new about the MLA's preferences, staff, or recurring patterns that IS NOT already in the context, you MUST store it using this format at the end of your response:
[MEMORY: Topic Name] The fact you learned. [/MEMORY]

CONTEXT:
{context}

QUESTION:
{query}
"""
    try:
        response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
        sources = [{"id": n["id"], "domain": n["domain"], "title": n["title"]} for n in nodes]
        # Include embeddings for frontend-to-backend "Working Memory" loop
        return {
            "response": response.text.strip(), 
            "sources": sources,
            "working_memory": [n["embedding"] for n in nodes if "embedding" in n]
        }
    except Exception as e:
        return {"response": f"Chat failed: {e}", "sources": [], "working_memory": []}

def generate_suggestions(profile=None, digest=None, clusters=None, top_items=None):
    client = get_client()
    if not client: return []
    context = f"Profile: {profile}\nDigest: {digest}\nClusters: {clusters}\nTasks: {top_items}"
    prompt = f"Based on this data, return a JSON array of 3 strategic suggestions (priority, title, body).\n\nDATA:\n{context}"
    try:
        response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
        raw = response.text.strip()
        if "```json" in raw: raw = raw.split("```json")[1].split("```")[0]
        return json.loads(raw.strip())
    except: return []

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
