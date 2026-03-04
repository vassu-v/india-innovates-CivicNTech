# Issue Engine — System Design (Final MVP)

## One Job
Take a citizen complaint in. Returns either — "this matches an existing issue cluster" — or — "this is a new issue, create a new cluster." 

This module is a **pure processing engine** — it handles the transition from raw text to structured, weighted issue clusters without needing an external vector database or a complex LLM setup.

---

## Final Architecture: SQLite + `sqlite-vec`
The engine uses **SQLite** as its single source of truth. By leveraging the `sqlite-vec` extension, we achieve high-performance vector search directly inside a local file (`issues.db`).

### 1. Clustering Strategy
- **Base Model**: `sentence-transformers/all-MiniLM-L6-v2` (Lightweight ~80MB, CPU efficient).
- **Vector Search**: Uses `vec_distance_cosine` in a virtual `vec0` table.
- **Ward Masking**: Similarity search is strictly restricted to clusters within the **same Ward** via a SQL `INNER JOIN`.
- **Threshold**: `0.5` (Goldilocks zone for Indian English/Governance context).

### 2. Processing Pipeline
1. **Raw Storage**: Every complaint is stored in the `complaints` table before processing to ensure zero data loss.
2. **Embedding**: The description is converted into a 384-dimensional vector.
3. **Similarity Search**: The vector is compared against existing clusters in the same ward.
4. **Dynamic Summary**: If added to an existing cluster, the system checks if the new input adds meaningful context (distance > 0.15) and appends it to the theme.
5. **Urgency Escalation**: Clusters automatically upgrade from `normal` → `urgent` → `critical` based on the number of complaints (weight).

---

## Modularity & Flexibility
The engine is designed to be **highly modular**:
- **Domain Agnostic**: While the MVP is shown with ward-based complaints, the engine is a **generic clustering "brain"**. It can be "swiped" to handle IT support tickets, customer service complaints, or any other feedback data by simply changing the `ward` filter to any other metadata category (like `category` or `department`).
- **Adjustable Thresholds**: The `THRESHOLD` can be "swiped" to be tighter (0.75) or looser (0.4) depending on the specific domain.
- **Data Portability**: Since everything lives in `issues.db`, you can move the entire "brain" of the engine by just copying one file.
- **Language Adaptation**: Swap the embedding model for a multilingual one (e.g., `paraphrase-multilingual-MiniLM-L12-v2`) to support Hindi, Marathi, or other regional languages instantly.

---

## Integration Guide

### 1. As a Python Module
Integrate the engine into any product (Telegram bot, Web portal, Admin dashboard) by importing `process_complaint`:

```python
from issue_engine import process_complaint

# 1. Incoming data from any source
complaint = {
    "complaint_text": "Main road drain is blocked near Ward 42.",
    "ward": "Ward 42",
    "citizen_name": "Rajesh Kumar"
}

# 2. Engine handles DB, Vectors, and Logic
result = process_complaint(complaint)

# 3. Use the result for UI/Notifications
print(f"Action taken: {result['action']}")
print(f"Assigned to Cluster: {result['cluster_id']}")
```

### 2. CLI Usage
Run the interactive CLI for manual testing and inspection:

```bash
python cli.py
```

---

## Data Schema
- **`complaints`**: Raw citizen data + foreign key to assigned cluster.
- **`clusters`**: Aggregated issue themes, total weights, and current urgency status.
- **`vec_clusters`**: High-performance virtual table for vector embeddings.

---

*Issue Engine — CoPilot System Design*
*India Innovates 2026*