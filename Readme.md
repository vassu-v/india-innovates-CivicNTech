# RAGCore

**Local retrieval-augmented generation — no API keys, no cloud dependency.**

RAGCore is a self-contained RAG pipeline built for document-heavy workflows: research retrieval, meeting summarisation, and policy Q&A. It runs entirely on-device using open-weight models.

---

## How it works

```
                     ┌─────────────────────────────────┐
  Document ──────────►  Sentence-aware chunker          │
                     │  (overlap window, min-length     │
                     │   filter, SHA-1 chunk IDs)       │
                     └────────────────┬────────────────┘
                                      │
                     ┌────────────────▼────────────────┐
                     │  Bi-encoder (all-mpnet-base-v2) │
                     │  Normalised embeddings           │
                     └────────────────┬────────────────┘
                                      │
                     ┌────────────────▼────────────────┐
                     │  ChromaDB  (cosine, persistent) │
                     └────────────────┬────────────────┘
                                      │
  Query ─────────────► Embed query   │
                     │               ▼
                     │  Top-12 candidates (dense ANN)
                     │               │
                     │  Cross-encoder rerank → Top-4
                     │  (ms-marco-MiniLM-L-6-v2)
                     │               │
                     │  Extractive QA (roberta-squad2)
                     │               │
                     └──────► Answer + confidence score
```

Bi-encoders are fast but approximate. Cross-encoders are precise but slow. RAGCore uses both: retrieve broadly with the bi-encoder, then rerank with the cross-encoder for precision.

---

## Quickstart

```bash
git clone https://github.com/yourusername/RAGCore.git
cd RAGCore
pip install -r requirements.txt
```

**Index a document**
```bash
python main.py index path/to/document.pdf
```

**Ask a question**
```bash
python main.py query "What decisions were made about the infrastructure bill?"
```

**Summarise a document**
```bash
python main.py summarise path/to/meeting_notes.pdf
```

**Interactive session**
```bash
python main.py chat
```

---

## CLI reference

| Command | Description |
|---------|-------------|
| `index <file>` | Ingest a `.pdf`, `.txt`, or `.md` file |
| `index <file> --reset` | Wipe index, then ingest |
| `query "<question>"` | Answer a question from indexed docs |
| `query "<question>" --verbose` | Include top source passage |
| `query "<question>" --json` | Machine-readable output |
| `summarise <file>` | Abstractive summary via BART |
| `chat` | Interactive Q&A loop |

---

## Configuration

`PipelineConfig` in `src/engine.py`:

```python
@dataclass
class PipelineConfig:
    chunk_size: int = 400          # words per chunk
    chunk_overlap: int = 80        # sliding window overlap
    top_k_retrieve: int = 12       # candidates from ChromaDB
    top_k_rerank: int = 4          # passages after cross-encoder
    min_confidence: float = 0.10   # threshold below which answer is suppressed
```

---

## Models used

| Role | Model | Size |
|------|-------|------|
| Embedding | `all-mpnet-base-v2` | ~420 MB |
| Reranking | `ms-marco-MiniLM-L-6-v2` | ~90 MB |
| Extractive QA | `roberta-base-squad2` | ~500 MB |
| Summarisation | `facebook/bart-large-cnn` | ~1.6 GB |

All weights download automatically on first run and cache locally.

---

## Running tests

```bash
pytest tests/ -v
```

---

## Project structure

```
RAGCore/
├── main.py               # CLI entry point
├── requirements.txt
├── src/
│   ├── __init__.py
│   └── engine.py         # pipeline: loader, chunker, store, RAG
├── tests/
│   ├── __init__.py
│   └── test_engine.py
├── data/                 # drop documents here
├── store/                # ChromaDB persists here (auto-created)
└── docs/
```

---

## License

MIT
