One DB With Two Parts — Yes, Absolutely
sqlite-vec is an SQLite extension that adds vector storage directly inside SQLite. So your static tables and your vector embeddings live in the same local database file, same queries.
SQLite (one database file)
├── static tables — normal rows and columns
└── vector virtual tables — embeddings stored with vector math capabilities
One connection string. One database file to manage. No ChromaDB needed separately. Much simpler for a solo builder.
This is exactly what you want for the issue engine — one table that has both the raw complaint data AND the embedding vector in the same row.

Issue Engine — System Design
What This Module Does
One job only. Takes a complaint in. Returns either — this matches an existing issue cluster, here's which one — or — this is new, create a new cluster.

What Goes In
complaint_text     — the description in citizen's words
citizen_name       — who filed it
citizen_contact    — how to reach them
ward               — which ward or area
channel            — how it arrived (letter/walk-in/portal/email)
date_received      — when it came in
staff_notes        — any extra context from staff

What The Module Does Internally
Step 1 — Receive complaint
         All fields stored immediately into complaints table
         Nothing is lost even if next steps fail

Step 2 — Generate embedding
         complaint_text is converted to a vector
         Using sentence-transformers (offline, free)
         Model: all-MiniLM-L6-v2 (small, fast, good enough)
         Result: a list of 384 numbers representing the meaning

Step 3 — Search for similar clusters
         Compare new embedding against all existing cluster embeddings
         Using cosine similarity via sqlite-vec
         Returns top 3 most similar clusters with their scores

Step 4 — Decision
         Score above 0.75 → similar cluster found
         Score below 0.75 → no match, treat as new

Step 5A — Similar found
          Add weight to existing cluster (+1)
          Link complaint_id to cluster_id in complaints table
          Recalculate cluster summary if new detail adds context
          Check if weight crossed urgency threshold
          Return: matched cluster details + new weight

Step 5B — New issue
          Create new cluster
          Set weight to 1
          Generate cluster summary from complaint text
          Store cluster embedding
          Link complaint to new cluster
          Return: new cluster created confirmation

The Two Tables Inside SQLite + sqlite-vec
Table 1 — complaints (static)
id                 auto increment
citizen_name       text
citizen_contact    text
ward               text
channel            text
raw_description    text
date_received      date
status             text — pending / in_progress / resolved
cluster_id         foreign key to clusters table
staff_notes        text
resolved_at        date, nullable
created_at         timestamp
Table 2 — vec_clusters (vector virtual table)
id                 auto increment primary key
embedding          float[384] — sqlite-vec column
One row in clusters holds the human-readable summary, and the linked vec_clusters holds the vector embedding. That is the sqlite-vec advantage — no separate vector DB needed.

Urgency Thresholds
weight 1-2    →    normal
weight 3-4    →    urgent
weight 5+     →    critical
These are configurable. Builder should make them easy to change — not hardcoded.

What Comes Out
Every time the module runs it returns a clean response:
For existing cluster match:
  action         — "added_to_existing"
  cluster_id     — which cluster
  cluster_summary — what the issue is
  new_weight     — updated weight
  urgency        — normal / urgent / critical
  complaint_id   — the new complaint that was filed

For new cluster:
  action         — "new_cluster_created"
  cluster_id     — newly created cluster
  cluster_summary — generated from complaint text
  weight         — 1
  urgency        — normal
  complaint_id   — the complaint that triggered it

How It Connects To The Rest Of The System
Issue Engine is a self-contained module
Exposes one function: process_complaint(complaint_data)
Returns one structured response

To-Do List reads from clusters table directly
Chat queries clusters table directly
Digest counts from clusters table directly
Commitment Tracker links to cluster_id when a commitment is made

Nothing else needs to know HOW the engine works
Everything else just reads the output tables
This is the modularity — the engine owns the complaints and clusters tables. Everything else just reads from them.

What The Builder Needs To Set Up
sentence-transformers library installed (Python, offline)
sqlite-vec library installed
Two tables created with the schemas above
One Python function that takes complaint data and runs the five steps
That is the entire module. No API, no server, no LLM, no internet. Just Python + SQLite + sqlite-vec.

Simplest Possible Test
Builder can verify it works by:

Filing 6 complaints about drainage in Ward 42 with slightly different wording
Checking that all 6 link to the same cluster
Checking that cluster weight is now 6
Checking urgency shows critical
Filing one complaint about street lights in Ward 17
Verifying a new cluster was created

If that works, the module is done and ready to connect to everything else.

---

## MVP Usage & Testing

This MVP is implemented using **SQLite** + **`sqlite-vec`**. It has exactly the capabilities described above and operates on a single local file (`issues.db`).

### 1. Prerequisites
Ensure you have the required Python packages installed:
```bash
pip install sentence-transformers sqlite-vec
```

### 2. Interactive CLI
You can test the engine interactively using the included CLI script:
```bash
python cli.py
```
This opens a menu where you can:
- **File a complaint:** Type in a custom complaint description.
- **View clusters:** See how complaints have been grouped, including weight and urgency.
- **View complaints:** See the raw complaints and the cluster they were assigned to.

### 3. Using as an Independent Module
The engine is completely self-contained. To use it in any other part of your system (like a portal backend or bot), you just need to import and call `process_complaint`:

```python
from issue_engine import process_complaint

# 1. Structure your incoming data
new_complaint = {
    "complaint_text": "The main drain in Ward 42 is completely blocked.",
    "ward": "Ward 42",
    "citizen_name": "John Doe",
    "channel": "web_portal"
}

# 2. Pass it to the engine
result = process_complaint(new_complaint)

# 3. The engine handles all DB storage, embedding, grouping, and urgency updates. 
# It returns a clean action dictionary:
print(result)
# {
#    "action": "new_cluster_created" or "added_to_existing",
#    "cluster_id": 1,
#    "cluster_summary": "The main drain in Ward 42 is completely blocked....",
#    "weight": 1,
#    "urgency": "normal",
#    "complaint_id": 1
# }
```
Everything else in your system can simply query the `issues.db` to read the state of `clusters` and `complaints` without needing to know how the vector matching works.