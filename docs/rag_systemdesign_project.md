# RAG Engine: System Design (Finalé)

The RAG (Retrieval-Augmented Generation) Engine is the intelligence core of Co-Pilot Finalé. It enables grounded, data-driven conversations and strategic insights by synthesizing live governance state with historical facts.

## 1. Architectural Overview

The RAG Engine follows a "Multi-Layer Context" pattern, where the LLM prompt is constructed from three distinct data tiers: live state, historical retrieval, and real-time patterns.

### Vector Storage
- **Model:** `all-MiniLM-L6-v2` (Sentence-Transformers) runs locally to generate 384-dimension embeddings.
- **Database:** SQLite with the `sqlite-vec` extension for high-performance vector search.
- **Fallback:** In environments without `sqlite-vec`, the engine uses a pure-Python cosine similarity fallback over BLOB-stored embeddings.

## 2. The 3-Layer Context Model

When a query is processed, the engine assembles context from these layers:

| Layer | Source | Contents |
|-------|--------|----------|
| **Layer 1: Live State** | `commitment_engine`, `digest_engine` | MLA Profile, Weekly resolution rates, Critical task counts, Top 3 pending items. |
| **Layer 2: History & Memory** | `rag_engine` (Vector Search) | Retrieved snippets from `context_files`, completed `timely_items`, and `ai_memory`. |
| **Layer 3: Live Patterns** | `issue_engine` | Top 3 citizen complaint clusters (weighted by volume and urgency). |

## 3. Semantic Routing

To minimize LLM tokens and latency, the system uses a local **Semantic Router** before hitting the RAG pipeline.

### Routing Logic:
1.  **Instant Route:** Compares the query against pre-encoded "Small Talk" centroids (greetings, thanks). If similarity > 0.65, it responds immediately.
2.  **Follow-up Route:** Uses "Working Memory" (the embeddings of nodes retrieved in the *previous* turn). If the new query is highly similar to previous context, it skips the expensive database search.
3.  **Search Route:** The default path for data queries. Executes full vector search and 3-Layer assembly.

## 4. AI Self-Memory Loop

The RAG Engine implements a "Self-Indexing" feature. The LLM is instructed to identify new patterns or preferences not present in its context.

- **Extraction:** If the AI learns a new fact (e.g., "The MLA prefers PWD escalations via email"), it appends a `[MEMORY: Topic] Content [/MEMORY]` tag to its response.
- **Persistence:** The `main.py` API handler parses this tag and calls `rag_engine.store_memory()`.
- **Retrieval:** These memory nodes are included in Layer 2 for all future queries.

## 5. Strategic Suggestion System

The Suggestion System is implemented in `rag_engine.generate_suggestions()`. Unlike Chat, it performs **Snapshot Synthesis**:
1.  **Context Pull:** It pulls the entire `profile`, `digest`, `clusters`, and `top_items`.
2.  **Strategic Persona:** It sends this massive state to Gemini with a "Strategic Advisor" persona.
3.  **Synthesis:** Gemini identifies gaps (e.g., "Resolution rate is low in Ward 17 despite few complaints") and return 3 structured JSON suggestions.
4.  **Actionability:** Each suggestion is prioritized (red/amber/blue) and contains a concrete body of text for the MLA to act on.

## 6. Database Schema

### `knowledge_nodes`
Stores the metadata and text for retrieved snippets.
- `domain`: `commitment_history` | `context_file` | `complaint_pattern`
- `source_ref`: Reference to the original table/ID (e.g., `timely_items:42`).

### `vec_knowledge` (Virtual)
Stores the 384-f32 embeddings for each node.

### `ai_memory`
Stores facts learned by the AI during chat sessions.

---
*Document Version: 1.0.0 (Finalé)*
