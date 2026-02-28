# Ingestion Engine — System Design (Final MVP)

## One Job
Take raw text from Indian governance meetings. Segment, classify, and route chunks to the correct engine (Commitment vs RAG). Discard noise and ensure human review for uncertain items.

This module is a **pure processing pipeline** — it handles the transition from unstructured transcript to structured actionable and historical data.

---

## Final Architecture: Embedding Similarity
The engine shifted from heavy zero-shot models (BART) to a **Prototype-Based Embedding Similarity** approach.

### 1. Classification Strategy
- **Base Model**: `sentence-transformers/all-MiniLM-L6-v2` (Lightweight ~80MB, CPU efficient).
- **Prototype Matching**: Text chunks are compared against a curated set of **Intent Prototypes** (Commitment, Question, Action, Context, Noise, Answer).
- **Scoring**: Highest average cosine similarity determines the label.
- **Threshold**: `0.45` (tuned for Indian English/Governance context).

### 2. Processing Pipeline
1. **Pre-processing**: Metadata stripping (skips Title/Date headers) until the first speaker tag is found.
2. **Speaker Persistence**: Splitting by newline first to catch speaker tags, then splitting by sentence. Every sub-sentence inherits the speaker tag from its parent line.
3. **Sliding Window**: Each chunk carries the previous and next sentence for context.
4. **Sentinel Check**: Regex-based pre-filtering for acknowledgements ("Noted", "I know") and common noise.
5. **Two-Pass Routing**:
   - **Pass 1**: Classify all chunks individually.
   - **Pass 2**: Sequential analysis (2-chunk look-ahead) to link **Questions** to **Answers/Commitments/Context**.

---

## Modularity & Flexibility
The engine is designed to be **highly modular**:
- **Intent Expansion**: Add new categories by simply adding a new key and prototype list to `SimilarityClassifier.prototypes`.
- **Domain Adaptation**: Swap prototypes to adapt the engine for non-governance meetings (e.g., Corporate, Legal) without retraining.
- **Model Swap**: The `model_name` parameter in `IngestionEngine` allows swapping different Sentence-Transformer models (e.g., `multi-qa-mpnet-base-dot-v1` for higher precision).

---

## Integration Guide

### 1. As a Python Module
Integrate the engine into any product by importing the `IngestionEngine` class:

```python
from Core.ingestion_engine import IngestionEngine

# Initialize
engine = IngestionEngine(user_name="Rajendra Verma")

# Process text
transcript = "User: I will fix the road repair by Friday."
results = engine.process_text(transcript, source_id="meeting_v1")

# Use results
for item in results["items"]:
    if item["routed_to"] == "commitment_engine":
        print(f"New Commitment: {item['chunk_text']}")
```

### 2. CLI Usage
Run the engine directly on a transcript file for verification or batch processing:

```bash
python Core/ingestion-engine/cli.py --file "Core/ingestion-engine/sample2.txt" --user "User"
```

---

## Routing Destinations
- **Commitment Engine**: For User commitments, actions, and open questions directed at the User.
- **RAG Engine**: For factual context, answered questions (archived knowledge), and general background.
- **Discarded**: Conversational noise, greetings, closures, and acknowledgements.
- **Flagged**: Low-confidence items or ambiguous intents requiring human review.

---

*Ingestion Engine — CoPilot System Design*
*India Innovates 2026*