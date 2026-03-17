"""
tests/test_engine.py
====================
Unit tests for RAGCore engine components.
Run with:  pytest tests/ -v
"""

import pytest
from src.engine import (
    DocumentLoader,
    PipelineConfig,
    SentenceAwareChunker,
    Chunk,
)


# ─────────────────────────────────────────────────────────────────────────────
#  PipelineConfig
# ─────────────────────────────────────────────────────────────────────────────

class TestPipelineConfig:
    def test_defaults(self):
        cfg = PipelineConfig()
        assert cfg.chunk_size == 400
        assert cfg.chunk_overlap == 80
        assert cfg.top_k_retrieve == 12
        assert cfg.top_k_rerank == 4
        assert 0 < cfg.min_confidence < 1

    def test_custom_chunk_size(self):
        cfg = PipelineConfig(chunk_size=256, chunk_overlap=32)
        assert cfg.chunk_size == 256
        assert cfg.chunk_overlap == 32


# ─────────────────────────────────────────────────────────────────────────────
#  SentenceAwareChunker
# ─────────────────────────────────────────────────────────────────────────────

class TestSentenceAwareChunker:

    @pytest.fixture
    def chunker(self):
        cfg = PipelineConfig(chunk_size=50, chunk_overlap=10, min_chunk_length=10)
        return SentenceAwareChunker(cfg)

    def test_returns_list_of_chunks(self, chunker):
        text = "The committee met on Monday. They discussed budget allocation. No resolution was reached."
        result = chunker.split(text, source="test.txt")
        assert isinstance(result, list)
        assert all(isinstance(c, Chunk) for c in result)

    def test_chunk_ids_are_unique(self, chunker):
        words = " ".join(f"word{i}." for i in range(200))
        chunks = chunker.split(words, source="doc.txt")
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_short_text_yields_single_chunk(self, chunker):
        text = "A short document. It has two sentences."
        chunks = chunker.split(text, source="short.txt")
        assert len(chunks) == 1

    def test_empty_text_yields_no_chunks(self, chunker):
        chunks = chunker.split("", source="empty.txt")
        assert chunks == []

    def test_source_propagated(self, chunker):
        text = "Parliament passed the bill. The vote was unanimous. All parties agreed."
        chunks = chunker.split(text, source="parliament.txt")
        for c in chunks:
            assert c.source == "parliament.txt"

    def test_word_count_reasonable(self, chunker):
        text = " ".join(f"sentence{i} has words." for i in range(100))
        chunks = chunker.split(text)
        for c in chunks:
            assert c.word_count > 0
            assert c.word_count <= chunker.chunk_size + 20  # allow sentence spillover


# ─────────────────────────────────────────────────────────────────────────────
#  DocumentLoader (without real files)
# ─────────────────────────────────────────────────────────────────────────────

class TestDocumentLoader:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            DocumentLoader.load(tmp_path / "nonexistent.txt")

    def test_unsupported_format_raises(self, tmp_path):
        f = tmp_path / "file.docx"
        f.write_text("content")
        with pytest.raises(ValueError, match="Unsupported format"):
            DocumentLoader.load(f)

    def test_load_txt(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("Hello world. This is a test document.")
        text, meta = DocumentLoader.load(f)
        assert "Hello world" in text
        assert meta["filename"] == "doc.txt"
        assert meta["char_count"] > 0
        assert "load_time_ms" in meta

    def test_load_md(self, tmp_path):
        f = tmp_path / "notes.md"
        f.write_text("# Meeting Notes\n\nPoint one. Point two.")
        text, meta = DocumentLoader.load(f)
        assert "Meeting Notes" in text
        assert meta["filename"] == "notes.md"

    def test_metadata_structure(self, tmp_path):
        f = tmp_path / "report.txt"
        f.write_text("Some report content here.")
        _, meta = DocumentLoader.load(f)
        assert set(meta.keys()) >= {"filename", "char_count", "load_time_ms"}
