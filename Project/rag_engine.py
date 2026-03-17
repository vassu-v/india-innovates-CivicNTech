"""
rag_engine.py
=============
RAGCore integration module for the existing FastAPI backend.
Drop this file into the Project/ directory alongside main.py.

Usage in main.py:
    from rag_engine import router as rag_router
    app.include_router(rag_router)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Add rag-core to path so engine.py can be imported
RAG_CORE_PATH = Path(__file__).parent.parent / "Core" / "rag-core"
sys.path.insert(0, str(RAG_CORE_PATH))

try:
    from engine import RAGPipeline, PipelineConfig
except ImportError as err:
    raise ImportError(
        "Could not import RAGCore engine. "
        "Make sure Core/rag-core/engine.py exists."
    ) from err

logger = logging.getLogger("rag_engine")

# ── Initialise pipeline (shared across all requests) ─────────────────────────
_pipeline: Optional[RAGPipeline] = None

def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        cfg = PipelineConfig()
        _pipeline = RAGPipeline(cfg)
        logger.info("RAGCore pipeline initialised")
    return _pipeline


# ── Request / Response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    confidence: float
    sources: list[str]
    latency_ms: float

class SummaryResponse(BaseModel):
    source: str
    summary: str
    latency_ms: float

class StatusResponse(BaseModel):
    status: str
    indexed_chunks: int


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get("/status", response_model=StatusResponse)
async def rag_status():
    """Health check — returns number of indexed chunks."""
    pipeline = get_pipeline()
    return StatusResponse(
        status="ok",
        indexed_chunks=pipeline.doc_count,
    )


@router.post("/index")
async def index_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload and index a document (PDF, TXT, or MD).
    Indexing runs in the background so the request returns immediately.
    """
    allowed = {".pdf", ".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Use: {allowed}",
        )

    # Save upload to temp location
    upload_dir = Path("./uploads")
    upload_dir.mkdir(exist_ok=True)
    save_path = upload_dir / file.filename

    contents = await file.read()
    save_path.write_bytes(contents)

    # Index in background so API stays responsive
    def _index():
        try:
            pipeline = get_pipeline()
            n = pipeline.index(str(save_path))
            logger.info("Indexed '%s' — %d chunks", file.filename, n)
        except Exception as exc:
            logger.error("Indexing failed for '%s': %s", file.filename, exc)

    background_tasks.add_task(_index)

    return JSONResponse(
        status_code=202,
        content={
            "message": f"Indexing '{file.filename}' started in background.",
            "filename": file.filename,
        },
    )


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Ask a question against all indexed documents.
    Returns answer, confidence score, and source filenames.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    pipeline = get_pipeline()

    if pipeline.doc_count == 0:
        raise HTTPException(
            status_code=404,
            detail="No documents indexed yet. Upload a document first via POST /rag/index",
        )

    result = pipeline.query(request.question)

    return QueryResponse(
        question=result.query,
        answer=result.answer,
        confidence=result.confidence,
        sources=result.sources,
        latency_ms=result.latency_ms,
    )


@router.post("/summarise", response_model=SummaryResponse)
async def summarise_document(file: UploadFile = File(...)):
    """
    Upload a document and get an abstractive summary.
    Useful for meeting notes and policy briefs.
    """
    allowed = {".pdf", ".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Use: {allowed}",
        )

    upload_dir = Path("./uploads")
    upload_dir.mkdir(exist_ok=True)
    save_path = upload_dir / file.filename

    contents = await file.read()
    save_path.write_bytes(contents)

    pipeline = get_pipeline()
    result = pipeline.summarise(str(save_path))

    return SummaryResponse(
        source=result.source,
        summary=result.summary,
        latency_ms=result.latency_ms,
    )
