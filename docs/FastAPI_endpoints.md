# FastAPI Backend Endpoints

This document provides a comprehensive overview of the available API endpoints in the CivicNTech Co-Pilot backend.

## Quick Reference List

- `GET  /api/digest` - Fetch the weekly accountability summary.
- `GET  /api/todo` - Retrieve pending commitments and issue clusters.
- `POST /api/item` - Manually add a new trackable item (commitment/question).
- `POST /api/complaint` - Log a citizen complaint (automatically triggers clustering).
- `GET  /api/issues/clusters` - Fetch all active (open) complaint clusters.
- `POST /api/escalate` - Manually trigger the weight/urgency escalation engine.
- `POST /api/item/{id}/complete` - Mark a specific item as completed with notes.
- `POST /api/item/{id}/extend` - Extend the deadline for a specific item.
- `GET  /api/history` - Fetch a paginated list of resolved items.
- `GET  /api/profile` - Retrieve the current MLA profile details.
- `POST /api/profile` - Update the MLA profile details.
- `GET  /api/meetings/recent` - Fetch details of recently processed meeting transcripts.
- `GET  /api/complaints/recent` - Fetch the most recent individual citizen complaints.
- `GET  /api/stats` - Fetch overall system statistics (monthly/all-time).
- `POST /api/upload/meeting` - Upload and process a .txt meeting transcript.
- `POST /api/upload/context` - Inject a .txt file into the RAG permanent context (DB1).
- `GET  /api/context/files` - List all injected context files.
- `POST /api/chat` - Interactive RAG-powered chat with constituency data and strategic context.
- `POST /api/suggestions` - Generate agentic strategic suggestions using governance tools.

---

## Detailed Endpoint Documentation

### 1. Governance & Tasks

#### `GET /api/digest`
- **Description**: Returns a summary of governance performance over the last 7 days, including new items, resolution rates, and most overdue tasks.
- **Response**: `DigestResponse` (JSON object with period, new_items, resolved, open_now, and most_overdue).

#### `GET /api/todo`
- **Description**: Returns a ranked list of pending items, split into `meeting_items` (commitments/questions) and `issue_items` (complaint clusters).
- **Parameters**:
    - `type` (Optional[str]): Filter by 'commitment', 'question', or 'issue'.
    - `urgency` (Optional[str]): Filter by 'normal', 'urgent', or 'critical'.
    - `ward` (Optional[str]): Filter by specific ward name.

#### `POST /api/item`
- **Description**: Manually adds a trackable item to the database.
- **Request Body**: `ItemCreate` (text, type, source_id, meeting_date, ward, weight, urgency).

#### `POST /api/item/{item_id}/complete`
- **Description**: Marks an item as resolved. Generates a 'fact string' that can be indexed for future RAG retrieval.
- **Request Body**: `CompletionRequest` (resolution_notes).

#### `POST /api/item/{item_id}/extend`
- **Description**: Pushes the deadline of a pending item.
- **Request Body**: `ExtendRequest` (new_deadline).

#### `POST /api/escalate`
- **Description**: Recalculates weights and urgency for all open items based on their age and current status.

---

### 2. Citizen Complaints & Clustering

#### `POST /api/complaint`
- **Description**: Logs an individual citizen's complaint. The backend automatically calculates vector embeddings, finds the most similar existing cluster, and updates its weight. If no similar cluster exists, a new one is created.
- **Request Body**: `ComplaintCreate` (citizen_name, citizen_contact, ward, channel, complaint_text, date_received, staff_notes).

#### `GET /api/issues/clusters`
- **Description**: Retrieves all currently open complaint clusters ranked by their calculated weight (impact).

#### `GET /api/complaints/recent`
- **Description**: Returns the latest individual complaints logged in the system.

---

### 3. AI & RAG (Retrieval-Augmented Generation)

#### `POST /api/chat`
- **Description**: The primary interaction point for the Co-Pilot AI. Uses a 4-layer context assembly (Strategic, Live State, Historical Facts, Patterns).
- **Request Body**: `ChatRequest`
    - `query` (str): User's question.
    - `working_memory` (list): Recent vector embeddings for semantic routing.
    - `strategic_context` (Optional[str]): Thinking trace from the Suggestions agent.
- **Routing**: Automatically routes between 'instant' (small talk), 'follow-up' (uses working memory), and 'search' (full RAG).

#### `POST /api/suggestions`
- **Description**: Runs an agentic loop (up to 3 rounds) using specialized governance tools (e.g., `get_ward_history`, `get_department_track_record`) to generate strategic recommendations.
- **Request Body**: `SuggestionsRequest`
    - `query` (Optional[str]): Focused inquiry for the agent.
    - `history` (Optional[List[dict]]): Previous thinking trace for follow-up refinement.

#### `POST /api/upload/context`
- **Description**: Injects permanent background knowledge into the RAG system.
- **Request (Multipart/Form-Data)**:
    - `file`: The .txt file to index.
    - `label`: Human-readable name (e.g., "Ward 42 Census").
    - `category`: Category for source attribution.

---

### 4. MLA Profile & System

#### `GET /api/profile` | `POST /api/profile`
- **Description**: Manages the identity and constituency details of the elected representative.

#### `POST /api/upload/meeting`
- **Description**: Uploads a raw meeting transcript. The backend uses Gemini to batch-extract specific commitments and questions, which are then added to the To-Do list.

#### `GET /api/stats`
- **Description**: Returns high-level metrics used for dashboard cards (Resolution rates, reliable contacts, etc.).
