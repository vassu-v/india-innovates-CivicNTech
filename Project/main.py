from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from contextlib import asynccontextmanager
import os
import commitment_engine
import issue_engine
import digest_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    commitment_engine.init_db()
    issue_engine.init_db()
    yield

app = FastAPI(title="Co-Pilot API", lifespan=lifespan)

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

# API Endpoints
@app.get("/api/digest")
def get_digest():
    return digest_engine.get_digest()

@app.get("/api/todo")
def get_todo(type: Optional[str] = None, urgency: Optional[str] = None, ward: Optional[str] = None):
    return digest_engine.get_todo_list(type=type, urgency=urgency, ward=ward)

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
    return digest_engine.get_history(limit=limit, offset=offset)

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

@app.get("/api/stats")
def get_stats():
    return digest_engine.get_stats()

# Serve Frontend
@app.get("/")
def read_root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
