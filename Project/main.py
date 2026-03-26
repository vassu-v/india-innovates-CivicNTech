from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import os
import asyncio
import commitment_engine
import issue_engine
import digest_engine
import rag_engine
import ai

async def auto_escalate_task():
    while True:
        try:
            print("Auto-escalating items...")
            commitment_engine.escalate()
        except Exception as e:
            print(f"Auto-escalation error: {e}")
        await asyncio.sleep(3600) # Run every hour

@asynccontextmanager
async def lifespan(app: FastAPI):
    commitment_engine.init_db()
    issue_engine.init_db()
    rag_engine.init_db()
    asyncio.create_task(auto_escalate_task())
    yield

app = FastAPI(title="Co-Pilot API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

# Models
class ItemCreate(BaseModel):
    text: Optional[str] = None
    type: str = "commitment"
    source_id: Optional[str] = "manual"
    meeting_date: Optional[str] = None
    # For issue engine format
    cluster_id: Optional[int] = None
    cluster_summary: Optional[str] = None
    ward: Optional[str] = None
    weight: Optional[int] = 1
    urgency: Optional[str] = "normal"

class ComplaintCreate(BaseModel):
    citizen_name: Optional[str] = None
    citizen_contact: Optional[str] = None
    ward: Optional[str] = None
    channel: Optional[str] = "manual"
    complaint_text: str
    date_received: Optional[str] = None
    staff_notes: Optional[str] = None

class CompletionRequest(BaseModel):
    resolution_notes: str = ""

class ExtendRequest(BaseModel):
    new_deadline: str

class ChatRequest(BaseModel):
    query: str
    working_memory: list = []
    strategic_context: Optional[str] = None
    history: List[dict] = [] # List of {role: "user"/"ai", content: "..."}

# API Endpoints
@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        # Working memory from request (if any)
        recent_embeddings = req.working_memory

        # 1. Routing: Instant, Follow-up, or Search
        route = rag_engine.needs_context(req.query, recent_embeddings)

        if route == "instant":
            res_text = ai.call_ai(f"You are Co-Pilot. Answer the user's greeting or general question warmly. Query: {req.query}")
            return {"response": res_text, "sources": [], "routed": "instant"}

        if route == "follow-up":
            # Just call Gemini directly with history (no new search)
            # We skip the heavy retrieval because the context is already "in chat"
            res_data = rag_engine.chat(
                query=req.query,
                profile=commitment_engine.get_profile(),
                strategic_context=req.strategic_context,
                history=req.history
            )
            res_data["routed"] = "follow-up"
            return res_data

        # 2. Full RAG Flow (NEW_DATA_QUERY)
        profile = commitment_engine.get_profile()
        digest = digest_engine.get_digest()
        todo = commitment_engine.get_todo_list()

        db = issue_engine.get_db()
        clusters = db.execute("SELECT * FROM clusters WHERE status = 'open' ORDER BY weight DESC").fetchall()
        db.close()
        cluster_list = [dict(c) for c in clusters]

        res_data = rag_engine.chat(
            query=req.query,
            profile=profile,
            digest=digest,
            top_items=todo["meeting_items"],
            clusters=cluster_list,
            strategic_context=req.strategic_context,
            history=req.history
        )

        # 3. Post-Process: AI Self-Memory
        import re
        mem_match = re.search(r"\[MEMORY:\s*(.*?)\](.*?)\[/MEMORY\]", res_data["response"], re.DOTALL)
        if mem_match:
            topic = mem_match.group(1).strip()
            content = mem_match.group(2).strip()
            rag_engine.store_memory(topic, content)
            # Remove tag from user-facing response
            res_data["response"] = re.sub(r"\[MEMORY:.*?/MEMORY\]", "", res_data["response"], flags=re.DOTALL).strip()
            res_data["memory_stored"] = True

        return res_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Existing API Endpoints
@app.get("/api/digest")
def get_digest():
    return digest_engine.get_digest()

@app.get("/api/todo")
def get_todo(type: Optional[str] = None, urgency: Optional[str] = None, ward: Optional[str] = None):
    return commitment_engine.get_todo_list(type=type, urgency=urgency, ward=ward)

@app.post("/api/item")
def add_item(item: ItemCreate):
    try:
        data = item.dict(exclude_none=True)
        # All items (commitments, questions, issues) flow through commitment_engine
        item_id = commitment_engine.add_item(data)
        return {"id": item_id, "status": "added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/complaint")
def log_complaint(data: ComplaintCreate):
    try:
        # 1. Cluster the complaint via Issue Engine
        cluster_res = issue_engine.process_complaint(data.dict())
        
        # 2. Add/Update the cluster as a trackable item in Commitment Engine
        # This ensures it shows up in the To-Do list
        commitment_engine.add_item(cluster_res)
        
        return cluster_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/issues/clusters")
def get_clusters():
    try:
        db = issue_engine.get_db()
        rows = db.execute("SELECT * FROM clusters WHERE status = 'open' ORDER BY weight DESC").fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/escalate")
def run_escalate():
    commitment_engine.escalate()
    return {"status": "done"}

@app.post("/api/item/{item_id}/complete")
def complete_item(item_id: int, req: CompletionRequest):
    fact = commitment_engine.complete_item(item_id, req.resolution_notes)
    if fact is None:
        raise HTTPException(status_code=404, detail="Item not found or already completed")
    return {"status": "completed", "fact": fact}

@app.post("/api/item/{item_id}/extend")
def extend_item(item_id: int, req: ExtendRequest):
    success = commitment_engine.extend_item(item_id, req.new_deadline)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "extended"}

@app.get("/api/history")
def get_history(limit: int = 50, offset: int = 0):
    return commitment_engine.get_history(limit=limit, offset=offset)

@app.get("/api/profile")
def get_profile():
    print("DEBUG: Hit GET /api/profile")
    return commitment_engine.get_profile()

@app.post("/api/profile")
def update_profile(data: dict):
    print(f"DEBUG: Hit POST /api/profile with data: {data}")
    success = commitment_engine.update_profile(data)
    return {"status": "updated" if success else "failed"}

@app.get("/api/meetings/recent")
def get_recent_meetings():
    return commitment_engine.get_recent_meetings()

@app.get("/api/complaints/recent")
def get_recent_complaints():
    return issue_engine.get_recent_complaints()

@app.get("/api/stats")
def get_stats():
    return commitment_engine.get_stats()

@app.post("/api/upload/meeting")
async def upload_meeting(
    file: UploadFile = File(...),
    meeting_date: str = Form(...),
    meeting_type: str = Form(...),
    participants: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported for transcripts.")

    content = await file.read()
    text = content.decode("utf-8")

    # Process transcript
    count = commitment_engine.batch_extract_from_transcript(text, meeting_date, file.filename)

    return {"status": "success", "extracted_count": count, "filename": file.filename}

@app.post("/api/upload/context")
async def upload_context(
    file: UploadFile = File(...),
    label: str = Form(...),
    category: str = Form(...)
):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported for context.")

    content = await file.read()
    text = content.decode("utf-8")

    commitment_engine.add_context_file(file.filename, label, category, text)

    return {"status": "success", "filename": file.filename}

@app.get("/api/context/files")
def get_context_files():
    return commitment_engine.get_context_files()

class SuggestionsRequest(BaseModel):
    query: Optional[str] = None
    history: Optional[List[dict]] = None

@app.post("/api/suggestions")
def get_suggestions(req: Optional[SuggestionsRequest] = None):
    try:
        query = req.query if req else None
        history = req.history if req else None
        profile = commitment_engine.get_profile()
        digest = digest_engine.get_digest()
        db = issue_engine.get_db()
        clusters = db.execute("SELECT * FROM clusters WHERE status = 'open' ORDER BY weight DESC").fetchall()
        db.close()
        cluster_list = [dict(c) for c in clusters]

        todo = commitment_engine.get_todo_list()
        top_items = todo["meeting_items"] + todo["issue_items"]

        return rag_engine.generate_suggestions(
            profile=profile,
            digest=digest,
            clusters=cluster_list,
            top_items=top_items,
            user_query=query,
            history=history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve Frontend
@app.get("/")
def read_root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
