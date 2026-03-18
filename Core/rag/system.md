# RAG Engine — System Design (Standalone)

The RAG (Retrieval-Augmented Generation) Engine is a standalone module designed to provide grounded, data-backed answers to queries about the MLA's constituency. It assembles context from three distinct layers — live state, historical facts, and current complaint patterns — to provide a comprehensive "second brain" for the MLA.

---

## Directory Structure

Standardized to match other engines in the project:
```text
Core/rag/
├── engine.py        # Core RAG logic, vector search, and context assembly
├── cli.py           # Command-line interface for testing and management
├── test_engine.py   # Unit tests for the engine
├── .env             # Environment variables (GEMINI_API_KEY)
├── rag.db           # SQLite database for knowledge nodes and vectors
└── system.md        # This documentation
```

---

## The Three Layers of Context

The engine ensures Gemini has a complete view of the constituency by assembling a 3-layer context for every query:

### Layer 1: Always-On (Live State)
**Type:** Passed as data structures (Profile/Digest).
Captured directly from the project's live databases. It includes MLA details, ward information, resolution rates, and current pending item counts. This ensures the model is never "stale" on the current reality.

### Layer 2: Vector Retrieval (Historical Facts)
**Type:** Semantic search on `knowledge_nodes`.
Uses `sentence-transformers` (all-MiniLM-L6-v2) to embed facts from completed commitments and injected context files. Performs cosine similarity search to find the top 5 most relevant historical snippets.

### Layer 3: Live Patterns (Complaints)
**Type:** Dynamic SQL fetch.
Injected as a list of current complaint clusters (ward, urgency, summary). This provides a snapshot of "what citizens are saying right now" without requiring stale embeddings.

---

## Technical Implementation

### Vector Search & Fallback
The engine uses `sqlite-vec` for native vector search inside SQLite.
- **Success Case**: Uses `vec_distance_cosine` for fast, indexed retrieval.
- **Fallback Case**: If `sqlite-vec` is missing, the engine performs an in-memory cosine similarity calculation across all stored nodes, ensuring zero-crash reliability.

### Authentication
The module loads `GEMINI_API_KEY` from its local `.env` file or the project root, using a dual-path `load_dotenv` strategy.

---

## CLI Usage

The `cli.py` tool allows for full management of the standalone module.

### Initialization
```powershell
python cli.py init
```

### Adding Knowledge Nodes
Manual ingestion for testing or manual context injection:
```powershell
python cli.py add --domain context_file --title "Ward 42 Census" --content "Population is 45k" --ref "manual"
```

### Semantic Search
Test the vector retrieval layer independently:
```powershell
python cli.py query "population of ward 42"
```

### Grounded Chat
Run the full RAG pipeline (requires Gemini API key):
```powershell
python cli.py chat "How many people live in Ward 42?" --debug
```
*Note: The `--debug` flag displays the full assembled context string before sending it to Gemini.*

---

## Testing
Comprehensive verification is provided via `test_engine.py`:
```powershell
python test_engine.py
```
Covers database initialization, vector storage, similarity calculations, and 3-layer assembly logic.