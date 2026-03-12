"""
ragcore/engine.py
=================
Core RAG engine: document ingestion, chunking, embedding,
vector storage, two-stage retrieval, and answer synthesis.

Design decisions:
  - RecursiveCharacterTextSplitter-style chunking with sentence
    boundary awareness to avoid cutting mid-thought.
  - Bi-encoder (all-mpnet-base-v2) for recall; cross-encoder
    (ms-marco-MiniLM-L-6-v2) for precision reranking.
  - ChromaDB with cosine distance for persistent vector storage.
  - Abstractive summarisation via facebook/bart-large-cnn for
    meeting/document summaries (separate from QA).
  - Extractive QA via deepset/roberta-base-squad2 for factual
    point lookups.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ragcore.engine")


# ─────────────────────────────────────────────────────────────────────────────
#  Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineConfig:
    # Chunking
    chunk_size: int = 400
    chunk_overlap: int = 80
    min_chunk_length: int = 60          # discard tiny fragments

    # Retrieval
    top_k_retrieve: int = 12
    top_k_rerank: int = 4
    min_confidence: float = 0.10        # below this → "not found"

    # Models
    embed_model: str = "sentence-transformers/all-mpnet-base-v2"
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    qa_model: str = "deepset/roberta-base-squad2"
    summarise_model: str = "facebook/bart-large-cnn"

    # Storage
    persist_dir: str = "./store/chroma"
    collection_name: str = "ragcore_v1"


# ─────────────────────────────────────────────────────────────────────────────
#  Document loading
# ─────────────────────────────────────────────────────────────────────────────

class DocumentLoader:
    """
    Loads raw text from .pdf, .txt, and .md files.
    Strips boilerplate whitespace and normalises Unicode.
    """

    SUPPORTED = {".pdf", ".txt", ".md"}

    @classmethod
    def load(cls, path: str | Path) -> tuple[str, dict]:
        """
        Returns (text, metadata) where metadata contains
        filename, page_count (PDFs), char_count, load_time_ms.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")
        if path.suffix.lower() not in cls.SUPPORTED:
            raise ValueError(
                f"Unsupported format '{path.suffix}'. "
                f"Supported: {cls.SUPPORTED}"
            )

        t0 = time.perf_counter()
        if path.suffix.lower() == ".pdf":
            text, pages = cls._load_pdf(path)
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
            pages = None

        text = cls._clean(text)
        elapsed = round((time.perf_counter() - t0) * 1000, 1)

        meta = {
            "filename": path.name,
            "char_count": len(text),
            "load_time_ms": elapsed,
        }
        if pages is not None:
            meta["page_count"] = pages

        logger.info(
            "Loaded '%s' — %d chars in %.1f ms",
            path.name, len(text), elapsed,
        )
        return text, meta

    @staticmethod
    def _load_pdf(path: Path) -> tuple[str, int]:
        try:
            import PyPDF2
        except ImportError:
            raise ImportError("Install PyPDF2:  pip install PyPDF2")

        parts: list[str] = []
        with open(path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        return "\n".join(parts), len(reader.pages)

    @staticmethod
    def _clean(text: str) -> str:
        # Collapse runs of whitespace / blank lines
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  Chunking
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    id: str
    text: str
    index: int
    start_char: int
    word_count: int
    source: str = ""


class SentenceAwareChunker:
    """
    Splits text on sentence boundaries where possible,
    then merges sentences into chunks of ≈ chunk_size words
    with a sliding overlap window.
    """

    _SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, cfg: PipelineConfig):
        self.chunk_size = cfg.chunk_size
        self.overlap = cfg.chunk_overlap
        self.min_length = cfg.min_chunk_length

    def split(self, text: str, source: str = "") -> list[Chunk]:
        sentences = self._SENTENCE_END.split(text)
        chunks: list[Chunk] = []
        buffer: list[str] = []
        buf_words = 0
        char_offset = 0
        idx = 0

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            words = sent.split()
            if buf_words + len(words) > self.chunk_size and buffer:
                chunk = self._make_chunk(
                    " ".join(buffer), idx, char_offset, source
                )
                if chunk:
                    chunks.append(chunk)
                    idx += 1
                # slide overlap
                overlap_buf = buffer[-self._overlap_words(buffer):]
                char_offset += len(" ".join(
                    buffer[: len(buffer) - len(overlap_buf)]
                ))
                buffer = overlap_buf
                buf_words = sum(len(w.split()) for w in buffer)

            buffer.append(sent)
            buf_words += len(words)

        if buffer:
            chunk = self._make_chunk(
                " ".join(buffer), idx, char_offset, source
            )
            if chunk:
                chunks.append(chunk)

        logger.info(
            "Chunked '%s' → %d chunks (size=%d, overlap=%d)",
            source or "text", len(chunks), self.chunk_size, self.overlap,
        )
        return chunks

    def _make_chunk(
        self, text: str, idx: int, offset: int, source: str
    ) -> Optional[Chunk]:
        text = text.strip()
        if len(text) < self.min_length:
            return None
        uid = hashlib.sha1(
            f"{source}:{idx}:{text[:64]}".encode()
        ).hexdigest()[:16]
        return Chunk(
            id=uid,
            text=text,
            index=idx,
            start_char=offset,
            word_count=len(text.split()),
            source=source,
        )

    def _overlap_words(self, buffer: list[str]) -> int:
        total, count = 0, 0
        for sent in reversed(buffer):
            total += len(sent.split())
            count += 1
            if total >= self.overlap:
                break
        return count


# ─────────────────────────────────────────────────────────────────────────────
#  Vector store wrapper
# ─────────────────────────────────────────────────────────────────────────────

class VectorStore:
    """
    Thin wrapper around ChromaDB with cosine similarity.
    Handles upsert, query, and collection lifecycle.
    """

    def __init__(self, cfg: PipelineConfig):
        import chromadb
        from chromadb.config import Settings

        self._client = chromadb.PersistentClient(
            path=cfg.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._client.get_or_create_collection(
            name=cfg.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "VectorStore ready — collection '%s', %d docs",
            cfg.collection_name, self._col.count(),
        )

    # ── public API ────────────────────────────────────────────────────────────

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]):
        self._col.upsert(
            ids=[c.id for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "source": c.source,
                    "index": c.index,
                    "word_count": c.word_count,
                }
                for c in chunks
            ],
        )
        logger.debug("Upserted %d chunks", len(chunks))

    def query(
        self, embedding: list[float], top_k: int
    ) -> list[tuple[str, dict]]:
        """Returns list of (text, metadata) tuples."""
        n = min(top_k, self._col.count())
        if n == 0:
            return []
        res = self._col.query(
            query_embeddings=[embedding],
            n_results=n,
            include=["documents", "metadatas"],
        )
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        return list(zip(docs, metas))

    def count(self) -> int:
        return self._col.count()

    def reset(self):
        name = self._col.name
        self._client.delete_collection(name)
        self._col = self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Collection '%s' reset", name)


# ─────────────────────────────────────────────────────────────────────────────
#  RAG Pipeline
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class QueryResult:
    query: str
    answer: str
    confidence: float
    passages: list[str]
    sources: list[str]
    latency_ms: float


@dataclass
class SummaryResult:
    summary: str
    source: str
    char_count: int
    latency_ms: float


class RAGPipeline:
    """
    End-to-end RAG pipeline.

    Indexing:
        load → chunk → embed (bi-encoder) → upsert (ChromaDB)

    Querying:
        embed query → retrieve top-K → rerank (cross-encoder)
        → extractive QA over top passages

    Summarising:
        load → abstractive summarisation (BART)
    """

    def __init__(self, cfg: Optional[PipelineConfig] = None):
        self.cfg = cfg or PipelineConfig()
        self._chunker = SentenceAwareChunker(self.cfg)
        self._store = VectorStore(self.cfg)
        self._embedder = None
        self._reranker = None
        self._qa = None
        self._summariser = None

    # ── lazy model loading ────────────────────────────────────────────────────

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading embedder: %s", self.cfg.embed_model)
            self._embedder = SentenceTransformer(self.cfg.embed_model)
        return self._embedder

    def _get_reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            logger.info("Loading reranker: %s", self.cfg.rerank_model)
            self._reranker = CrossEncoder(self.cfg.rerank_model)
        return self._reranker

    def _get_qa(self):
        if self._qa is None:
            from transformers import pipeline as hf_pipeline
            logger.info("Loading QA model: %s", self.cfg.qa_model)
            self._qa = hf_pipeline(
                "question-answering", model=self.cfg.qa_model
            )
        return self._qa

    def _get_summariser(self):
        if self._summariser is None:
            from transformers import pipeline as hf_pipeline
            logger.info("Loading summariser: %s", self.cfg.summarise_model)
            self._summariser = hf_pipeline(
                "summarization",
                model=self.cfg.summarise_model,
                truncation=True,
            )
        return self._summariser

    # ── indexing ──────────────────────────────────────────────────────────────

    def index(self, filepath: str, reset: bool = False) -> int:
        """
        Ingest a document into the vector store.
        Returns number of chunks indexed.
        """
        if reset:
            self._store.reset()

        text, meta = DocumentLoader.load(filepath)
        chunks = self._chunker.split(text, source=meta["filename"])
        if not chunks:
            logger.warning("No usable chunks from '%s'", filepath)
            return 0

        embedder = self._get_embedder()
        texts = [c.text for c in chunks]
        embeddings = embedder.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=True,
        ).tolist()

        self._store.upsert(chunks, embeddings)
        logger.info(
            "Indexed '%s' — %d chunks stored", meta["filename"], len(chunks)
        )
        return len(chunks)

    # ── querying ──────────────────────────────────────────────────────────────

    def query(self, question: str) -> QueryResult:
        """
        Answer a question against the indexed documents.
        Uses two-stage retrieval: dense search + cross-encoder rerank.
        """
        t0 = time.perf_counter()

        if self._store.count() == 0:
            return QueryResult(
                query=question,
                answer="No documents have been indexed yet.",
                confidence=0.0,
                passages=[],
                sources=[],
                latency_ms=0.0,
            )

        # Stage 1 — dense retrieval
        embedder = self._get_embedder()
        q_emb = embedder.encode(
            [question], normalize_embeddings=True
        ).tolist()[0]
        candidates = self._store.query(q_emb, self.cfg.top_k_retrieve)

        # Stage 2 — cross-encoder reranking
        reranker = self._get_reranker()
        pairs = [[question, doc] for doc, _ in candidates]
        scores = reranker.predict(pairs)
        ranked = sorted(
            zip(scores, candidates), key=lambda x: x[0], reverse=True
        )[: self.cfg.top_k_rerank]

        top_passages = [doc for _, (doc, _) in ranked]
        top_sources = [
            meta.get("source", "") for _, (_, meta) in ranked
        ]

        # Stage 3 — extractive QA
        context = " ".join(top_passages)[:4096]
        qa = self._get_qa()
        try:
            result = qa(question=question, context=context)
            answer = result["answer"]
            confidence = round(float(result["score"]), 4)
        except Exception as exc:
            logger.error("QA error: %s", exc)
            answer = "Could not extract an answer from the retrieved context."
            confidence = 0.0

        if confidence < self.cfg.min_confidence:
            answer = (
                "The answer does not appear to be present in the "
                "indexed documents. Try rephrasing or indexing more material."
            )

        latency = round((time.perf_counter() - t0) * 1000, 1)
        logger.info(
            "Query answered in %.1f ms (confidence=%.2f)", latency, confidence
        )

        return QueryResult(
            query=question,
            answer=answer,
            confidence=confidence,
            passages=top_passages,
            sources=list(dict.fromkeys(top_sources)),  # deduplicated
            latency_ms=latency,
        )

    # ── summarisation ─────────────────────────────────────────────────────────

    def summarise(self, filepath: str) -> SummaryResult:
        """
        Produce an abstractive summary of a document.
        Useful for meeting notes, policy briefs, reports.
        """
        t0 = time.perf_counter()
        text, meta = DocumentLoader.load(filepath)

        # BART has a 1024-token input limit; use first ~3000 words
        truncated = " ".join(text.split()[:3000])

        summariser = self._get_summariser()
        out = summariser(
            truncated,
            max_length=220,
            min_length=60,
            do_sample=False,
        )
        summary = out[0]["summary_text"]
        latency = round((time.perf_counter() - t0) * 1000, 1)

        logger.info(
            "Summarised '%s' in %.1f ms", meta["filename"], latency
        )
        return SummaryResult(
            summary=summary,
            source=meta["filename"],
            char_count=meta["char_count"],
            latency_ms=latency,
        )

    # ── convenience ───────────────────────────────────────────────────────────

    @property
    def doc_count(self) -> int:
        return self._store.count()
