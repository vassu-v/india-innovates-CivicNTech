# CivicNTech Co-Pilot (Standalone MVP)

This directory contains a viable, independent version of the Co-Pilot application, designed for local deployment and high accountability.

## Architecture

The system is split into specialized "engines" that share a unified data layer:

- **`commitment_engine.py`**: Extracts commitments, questions, and action items from text/transcripts.
- **`issue_engine.py`**: Logs citizen complaints and automatically clusters them into "issue clusters" using vector embeddings.
- **`digest_engine.py`**: Generates daily/weekly summaries, stats, and performance metrics.
- **`main.py`**: A FastAPI server that integrates all engines and serves the dashboard.

## Data Layer
- **`copilot.db`**: A single SQLite database (with `sqlite-vec` support) containing all commitments, issues, and clusters.

## Getting Started

1. **Install Requirements**:
   ```bash
   pip install fastapi uvicorn google-genai python-dotenv sentence-transformers sqlite-vec
   ```

2. **Setup Environment**:
   - Create/Update `.env` with your `GEMINI_API_KEY`.

3. **Seed Data** (Optional):
   ```bash
   python Project/seed.py
   ```

4. **Run Server**:
   ```bash
   python -m uvicorn Project.main:app --reload
   ```

5. **View Dashboard**:
   - [http://localhost:8000](http://localhost:8000)

## Features
- **Dashboard**: Real-time stats and "Today at a glance" reflection.
- **To-Do List**: Unified view of commitments and urgent issue clusters.
- **Issue Logger**: Manual entry for citizen grievances with auto-clustering.
- **Digest**: Weekly breakdown of progress and resolution rates.

---
*Built as part of India Innovates - CivicNTech*
