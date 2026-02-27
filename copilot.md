# AI Co-Pilot for Public Leaders & Administrators
## Complete Technical Masterplan
### India Innovates 2026 | Digital Democracy Domain
### Problem Statement: AI Co-Pilot for Public Leaders & Administrators
**Version:** 1.0 | **Last Updated:** February 2026

---

## Table of Contents
1. [Product Vision](#1-product-vision)
2. [The Problem](#2-the-problem)
3. [What This System Is NOT](#3-what-this-system-is-not)
4. [Target User](#4-target-user)
5. [System Overview](#5-system-overview)
6. [Input Layer](#6-input-layer)
7. [Extraction Layer](#7-extraction-layer)
8. [Four Database Architecture](#8-four-database-architecture)
9. [Intelligence Layer](#9-intelligence-layer)
10. [Complaint Layer — Full Design](#10-complaint-layer--full-design)
11. [Data Out Layer](#11-data-out-layer)
12. [Complete System Architecture Diagram](#12-complete-system-architecture-diagram)
13. [Privacy & Security Architecture](#13-privacy--security-architecture)
14. [Tech Stack](#14-tech-stack)
15. [Database Schemas](#15-database-schemas)
16. [API Contracts](#16-api-contracts)
17. [Build Order & Prioritization](#17-build-order--prioritization)
18. [What To Build vs Simulate](#18-what-to-build-vs-simulate)
19. [Demo Flow](#19-demo-flow)
20. [Four Week Build Plan](#20-four-week-build-plan)
21. [Tools Used — Honest Acknowledgement](#21-tools-used--honest-acknowledgement)
22. [Stage Talking Points](#22-stage-talking-points)
23. [Competition Details](#23-competition-details)
24. [Immediate Next Steps](#24-immediate-next-steps)

---

## 1. Product Vision

**"Every politician retires. Their experience shouldn't."**

A secure, fully offline AI intelligence assistant built specifically for politicians and public administrators. It captures everything — meetings, complaints, promises, constituency data — organizes it intelligently, and helps the leader govern with memory, accountability, and clarity.

Not a generic chatbot. Not a cloud service. A second brain that knows everything the politician knows, remembers everything they forget, and never gossips.

---

## 2. The Problem

### What A Politician's Day Actually Looks Like
- Dozens of meetings with different people — bureaucrats, constituents, party workers, ministers
- Hundreds of complaints arriving through multiple disconnected channels
- Commitments made verbally that staff may or may not track
- Constituency data spread across government portals nobody can easily query
- No unified system — everything is scattered across WhatsApp groups, paper files, Excel sheets, email inboxes, and memory

### The Consequences of This Chaos
- Promises made in meetings forgotten or dropped without follow-up
- Same constituent complaining multiple times through different channels — nobody realizes it's the same issue
- No institutional memory — when staff changes, knowledge walks out the door
- No pattern recognition — same problems recurring in same wards year after year without systemic fix
- Reactive governance — problems addressed after they explode, not before

### What Currently Exists
- CPGRAMS — complaint portal nobody uses properly
- Generic productivity tools like Notion, Excel — not built for governance context
- ChatGPT — cloud-based, no constituency knowledge, no memory, no privacy
- Nothing that ties meetings + complaints + constituency data + promises into one intelligent system

---

## 3. What This System Is NOT

- NOT a generic AI chatbot
- NOT a cloud service — zero data leaves the laptop
- NOT built for every politician — specifically for constituency-level leaders (MLAs, MPs, municipal councillors) who have direct constituent interaction
- NOT a replacement for staff — a tool that makes the politician and staff more effective
- NOT trying to replace CPGRAMS or government portals — it ingests from them

---

## 4. Target User

**Primary:** MLA, MP, or senior municipal administrator
- Has a physical constituency office
- Receives complaints from multiple channels
- Attends multiple meetings daily
- Has staff who assist with office management
- Deals with government departments for project delivery

**NOT for:**
- Cabinet ministers who operate at policy level with no direct constituent interaction
- Politicians in Parliament only — though Parliament transcripts are partially supported
- Every level of government — scoped to constituency-level leaders

---

## 5. System Overview

The system has five distinct layers:

```
INPUT LAYER
↓
EXTRACTION LAYER
↓
FOUR DATABASE LAYER
↓
INTELLIGENCE LAYER
↓
DATA OUT LAYER
```

Each layer is explained in full detail below.

---

## 6. Input Layer

### 6.1 Meeting Audio Input

**Phase 1 (Demo — Simulated):**
A laptop microphone or any external microphone records meeting audio. Pre-recorded audio can also be used for demo purposes. This simulates the hardware device.

**Phase 2 (Production — Hardware Device):**
A small physical device clipped to tie or pocket:
- Records audio continuously during meetings
- Does ZERO processing on the device itself
- No WiFi transmission
- No Bluetooth transmission
- No internet connection ever
- Just a microphone + local SD card storage
- One LED: recording indicator
- USB-C port for connection to laptop only
- Hardware: Raspberry Pi Zero W + microphone module + 3D printed case
- Estimated cost: ₹2,000-3,000

**Why air-gapped hardware matters:**
A politician's meetings contain the most sensitive possible data — cabinet discussions, constituency negotiations, private conversations. The device never transmits wirelessly. Data moves only when the politician physically plugs it into their laptop. This is a fundamental trust architecture, not just a feature.

**When plugged into laptop:**
- Audio file transfers from SD card to laptop
- Transcription begins immediately on laptop
- Nothing is sent to any external server

### 6.2 Parliament / Formal Meeting Transcripts

Parliament sessions cannot be captured by the device — audio is not accessible, the environment is too large and noisy.

**Solution:**
- Lok Sabha and Rajya Sabha publish official transcripts on sansad.in
- Staff downloads relevant session transcripts
- Filters sections where the politician spoke or was addressed
- Uploads via USB or manual file import
- Same extraction pipeline processes it identically to meeting audio

### 6.3 Complaint Input — Email (Automated)

- Gmail API polls the politician's official email continuously
- Every incoming email is auto-parsed: sender name, contact, content, timestamp
- System identifies if it is a complaint or general communication
- Complaint is extracted and passed to Complaint Layer for processing
- No manual staff effort needed for email

### 6.4 Complaint Input — Staff Manual Form (Everything Else)

All other complaint channels are handled through a simple staff-facing form:

**Channels that feed into manual form:**
- Physical letters received at constituency office
- Walk-in complaints from constituents
- Portal complaints (CPGRAMS, state grievance portals) — staff copies these in
- Any other channel staff wants to log

**The form fields:**
```
Citizen name
Contact number
Ward / Area
Brief description of complaint
Channel received through (letter / walk-in / portal / other)
Date received
Attachments (photo if any)
```

Staff fills this in 30 seconds. System handles everything else.

**What is NOT included in complaint intake:**
- WhatsApp — not integrated (scope decision, adds API complexity)
- Twitter/X — not integrated
- Phone calls — not integrated
- These can be added in future versions

---

## 7. Extraction Layer

### 7.1 Meeting Transcript Processing

After audio is recorded and transferred to laptop:

**Step 1 — Transcription (Whisper)**
```
Audio file → Whisper (runs completely offline)
→ Raw text transcript
```

**Step 2 — Speaker Diarization (WhisperX)**
```
Raw transcript → WhisperX
→ Diarized transcript with speaker labels:
   Speaker A: "I will look into the drainage issue by Friday"
   Speaker B: "What about the road repair in Ward 17?"
   Speaker A: "That is already with PWD, should be done by month end"
```

**Important note on diarization:**
Speaker diarization is a hard technical problem. Accuracy depends heavily on audio quality, number of speakers, and background noise. This is acknowledged as best-effort. Demo uses clean pre-recorded audio. Production improves over time as the system learns the politician's voice.

**Step 3 — Extraction AI (Separate model from transcription)**
A separate AI model reads the diarized transcript and extracts structured information:

```
Input: Full diarized transcript with Speaker A = politician, Speaker B/C/D = others

Extraction AI identifies and routes:

FROM POLITICIAN (Speaker A):
→ Commitments made: "I will look into X by Friday" → DB 3 (Timely)
→ Questions asked by politician: logged in DB 2 (RAG)
→ Statements and positions taken: DB 2 (RAG)
→ Approvals given: DB 3 if time-sensitive, DB 2 if historical

FROM OTHERS (Speaker B, C, D):
→ Questions directed at politician: DB 3 (needs answer — timely)
→ Requests made: DB 3 if commitment expected, DB 2 if informational
→ Information shared: DB 2 (RAG)
→ Complaints raised: routed to Complaint Layer

GENERAL DISCUSSION:
→ Context and factual information: DB 2 (RAG)
→ Historical references made: cross-checked with DB 1
→ Decisions taken: DB 2 (RAG)
→ Action items with implied deadlines: DB 3
```

**Structured output from Extraction AI:**
```json
{
  "commitments": [
    {
      "text": "Look into drainage issue Ward 42",
      "implied_deadline": "Friday",
      "to_whom": "Speaker B",
      "confidence": 0.92
    }
  ],
  "questions_to_answer": [
    {
      "text": "What is status of road repair Ward 17?",
      "from_whom": "Speaker C",
      "urgency": "medium"
    }
  ],
  "facts_learned": [
    {
      "text": "PWD has been assigned road repair Ward 17",
      "source": "meeting_2026_02_26",
      "relevance": "ward_17_infrastructure"
    }
  ],
  "action_items": [
    {
      "text": "Follow up with PWD commissioner",
      "deadline": "2026-02-28",
      "department": "PWD"
    }
  ]
}
```

### 7.2 Complaint Processing

Every new complaint (from email or manual form) goes through:

```
New complaint text arrives
        ↓
Generate text embedding (sentence-transformers, runs offline)
        ↓
Similarity search in DB 2 vector store
(find existing issue clusters above similarity threshold)
        ↓
        ├── SIMILAR FOUND (similarity > 0.75)
        │   → Add weight to existing issue cluster (+1)
        │   → Link this complaint ID to that cluster
        │   → Update cluster summary text
        │   → If weight crosses urgency threshold → flag
        │   → Store raw complaint in DB 4 (Static Complaints)
        │
        └── NOT SIMILAR (similarity < 0.75)
            → Create new issue cluster in DB 2
            → Weight starts at 1
            → Store raw complaint in DB 4 (Static Complaints)
            → Tag as new emerging issue
```

**Similarity threshold:** 0.75 is starting point, can be tuned based on how the system performs in practice.

---

## 8. Four Database Architecture

### DB 1 — Static Constituency Database (PostgreSQL)

**Purpose:** Permanent ground truth of the constituency. Always called on every query regardless of what is being asked. This is the base context layer — every AI response is grounded in real constituency data.

**What it contains:**
```
Ward demographics:
→ Population per ward
→ Age distribution (youth, working age, elderly)
→ Gender ratio
→ Occupation breakdown (farmers, workers, businessmen, etc.)
→ Literacy rate

Infrastructure status:
→ Roads — total km, good condition, repair needed
→ Schools — count, capacity, utilization
→ Hospitals/health centers — count, beds, doctors
→ Water supply coverage %
→ Electricity coverage %
→ Drainage infrastructure status

Development projects:
→ Ongoing projects — name, budget, expected completion
→ Completed projects — name, cost, date
→ Pending projects — name, budget allocated, status

Government schemes:
→ Which schemes active in constituency
→ Beneficiary count per scheme per ward
→ Pending applications count
→ Unclaimed scheme potential (estimated eligible vs actual beneficiaries)

Historical record:
→ Promises made in previous elections
→ Delivery status of those promises
→ Issues that recurred across years
→ Development budget allocation vs actual spending by year
```

**How it gets populated:**
- One-time setup by staff
- Data sourced from: Census data, municipal corporation reports, government portals, state government publications, MLA/MP local area development reports
- Updated periodically (quarterly or when major changes happen) by staff manually
- Never modified automatically by AI

**Key design decision:** DB 1 is never written to by the AI. Only staff can update it. This keeps it trustworthy and accurate.

---

### DB 2 — RAG Historical Facts Database (ChromaDB — Vector Store)

**Purpose:** Institutional memory. What has happened, what was promised, what was delivered, complaint issue clusters. This grows automatically over time and gets smarter with use.

**What it contains:**
```
Meeting summaries and key facts:
→ What was discussed in each meeting
→ Decisions taken
→ Information learned
→ Context of interactions with different people/departments

Historical commitment records:
→ Commitments that were completed → injected from DB 3 on resolution
→ Includes: what was promised, when, to whom, how long it took, outcome
→ Builds a track record over time

Complaint issue clusters:
→ Each cluster represents a type of issue in a ward/area
→ Cluster summary: "Drainage overflow Ward 42 — near plot 34"
→ Weight: number of complaints linked to this cluster
→ Urgency flag: if weight crosses threshold
→ Status: open / in-progress / resolved
→ Linked complaint IDs from DB 4

Pattern data:
→ Which issues recur in which wards
→ Which departments deliver on time vs delay
→ Which time periods generate most complaints
→ Seasonal patterns
```

**What it does NOT contain:**
- Raw individual complaints (those are in DB 4)
- Time-sensitive items (those are in DB 3)
- Constituency ground truth (that is in DB 1)

**How it grows:**
- Every meeting extraction adds facts
- Every resolved commitment from DB 3 is injected here on completion
- Every new complaint cluster is created here
- Every resolved complaint cluster is updated here
- Grows automatically with no manual effort after initial setup

---

### DB 3 — Timely Commitments Database (PostgreSQL with weights)

**Purpose:** Time-sensitive items only. Everything here has a deadline. Everything here has a weight that increases if overdue. Nothing ever silently disappears.

**What it contains:**
```
Each record has:
→ commitment_id
→ text: what was committed or what question needs answering
→ type: commitment_made / question_to_answer / action_item
→ to_whom: who this was committed to
→ source: meeting_id or complaint_cluster_id
→ deadline: explicit or implied deadline
→ weight: starts at 1, increases if overdue
→ status: pending / in-progress / extended / completed
→ extension_count: how many times deadline was extended
→ created_at
→ completed_at (null until resolved)
→ resolution_notes
```

**Weight escalation logic:**
```
On time (before deadline): weight = 1
1-3 days overdue: weight = 2
4-7 days overdue: weight = 3, flag as urgent
8-14 days overdue: weight = 5, flag as critical
15+ days overdue: weight = 8, flag as severely overdue
```

**On completion:**
```
Item marked complete in DB 3
→ Resolution details logged (on time / overdue / extended how many times)
→ Entire record injected into DB 2 as historical fact:
   "Commitment: Drainage Ward 42 follow-up
    Made: Jan 15 2026
    Completed: Feb 12 2026
    Duration: 28 days
    Was overdue: Yes (7 days)
    Via: PWD Commissioner"
→ Record deleted from DB 3 (no longer timely)
→ Institutional memory in DB 2 grows
```

**Key design decision:** When a deadline is extended, weight increases AND extension count increases. Three extensions on the same item is a strong signal of a systemic problem worth flagging to the politician.

---

### DB 4 — Static Complaints Database (PostgreSQL)

**Purpose:** Raw individual complaint records. Permanent audit trail. Individual citizen follow-up. Never deleted.

**What it contains:**
```
complaint_id (unique)
citizen_name
citizen_contact
channel: email / manual
ward
raw_description (full original text)
received_at (timestamp)
status: pending / in-progress / resolved
linked_cluster_id (points to issue cluster in DB 2)
resolution_notes
resolved_at (null until resolved)
was_overdue (boolean — filled on resolution)
staff_notes (internal notes from staff)
attachments (file paths to any photos submitted)
```

**Relationship to DB 2:**
- Every complaint links to one issue cluster in DB 2
- When a cluster is resolved → all linked complaints in DB 4 are marked resolved
- Staff can look up individual complaints for citizen follow-up
- AI can query DB 4 for "who complained about this issue?" when politician needs to follow up

**What DB 4 is used for:**
- Finding individual citizens to notify when their issue is resolved
- Audit trail for accountability
- Staff reference for case-by-case follow-up
- Historical record that cannot be altered

---

### How The Four DBs Work Together — Example Query

**Politician asks:** "Am I ready for tomorrow's Ward 42 meeting?"

```
Intelligence layer calls simultaneously:

DB 1 (Static Constituency):
→ Ward 42 demographics, infrastructure status, current projects
→ "Ward 42: population 45,000, drainage coverage 60%, 2 ongoing road projects"

DB 2 (RAG Historical):
→ Past issues in Ward 42, patterns, interaction history
→ "Drainage complaints spike every Feb-March in Ward 42
   Last resolved Aug 2024 via PWD, took 18 days
   Commissioner Singh was involved, delivered on time that instance"

DB 3 (Timely):
→ Open commitments related to Ward 42
→ "Drainage follow-up promised Jan 15 — 12 days overdue — weight 3
   Road repair update pending — 4 days left on deadline"

DB 4 (Static Complaints):
→ Individual complaints linked to Ward 42 clusters
→ "7 individual complaints about drainage — oldest from Jan 10"

Synthesized response:
"Ward 42 briefing for tomorrow:

URGENT: Drainage commitment from Jan 15 is 12 days overdue.
7 citizens have complained. Last time this was resolved in 18 days
via PWD Commissioner Singh — he delivered on time previously.
Recommend: Lead with this, give a specific resolution date.

Road repair: Deadline in 4 days. 2 complaints linked.
PWD has been assigned — check status before meeting.

Ward context: 40% of ward lacks drainage coverage —
residents are sensitive to this issue historically.
Drainage complaints appear every Feb-March — this is seasonal pattern.

Suggested agenda:
1. Drainage status — commit to specific date
2. Road repair timeline from PWD
3. New scheme awareness — 340 residents potentially eligible
   for PM Awas Yojana who haven't applied yet"
```

No single database could produce this. All four together create genuine intelligence.

---

## 9. Intelligence Layer

### Local LLM Setup
```
Ollama running locally on politician's laptop
Model: Phi-3 Mini (runs on CPU, 8GB RAM sufficient)
       OR Llama 3 8B (better quality, needs more RAM)
Zero internet connection required
Zero data leaves the laptop
```

### LangChain Orchestration
```
Every query goes through LangChain pipeline:

1. Query received from data out interface
2. DB 1 always loaded as base context (mandatory)
3. Query analyzed — which other DBs are relevant?
4. Relevant DBs queried
5. Retrieved context assembled
6. Local LLM generates response grounded in retrieved context
7. Response returned to interface
```

### Why Local LLM Not Cloud LLM
- A politician's data cannot go to OpenAI servers
- No subscription cost in production
- Works with zero internet after setup
- Government can audit and control the model
- Deployable on NIC or government infrastructure

### RAG Pipeline
```
User query
        ↓
Query embedding generated (sentence-transformers, offline)
        ↓
DB 1: full constituency context loaded (always)
        ↓
DB 2: similarity search → top K relevant facts retrieved
        ↓
DB 3: filter by relevance to query → timely items retrieved
        ↓
DB 4: queried only if individual complaint details needed
        ↓
All retrieved context assembled into prompt
        ↓
Local LLM generates response
        ↓
Response returned
```

---

## 10. Complaint Layer — Full Design

### Full Flow Diagram
```
Email arrives at official inbox
        ↓
Gmail API detects new email
        ↓
Parser extracts: sender, content, timestamp
        ↓
Classifier: is this a complaint? (yes/no)
        ↓
If yes → Complaint Processing Pipeline
If no → Ignored or logged separately

Staff receives physical letter / portal complaint
        ↓
Staff opens manual complaint form
        ↓
Fills: name, contact, ward, description, channel, date
        ↓
Submits form
        ↓
Same Complaint Processing Pipeline

COMPLAINT PROCESSING PIPELINE:
        ↓
Generate embedding of complaint description text
(sentence-transformers model, runs offline)
        ↓
Search DB 2 for similar existing issue clusters
(cosine similarity search)
        ↓
Similarity > 0.75 threshold?
        ↓
YES — Similar cluster found:
→ Weight of cluster += 1
→ Link complaint_id to cluster_id
→ Update cluster summary if new detail adds context
→ Check if weight crossed urgency threshold
   (configurable, default: 5 = urgent, 10 = critical)
→ Store raw complaint in DB 4 with cluster_id linked
→ Add to To-Do list if cluster urgency changed

NO — No similar cluster:
→ Create new cluster in DB 2
→ Cluster summary = complaint description
→ Weight = 1
→ Store raw complaint in DB 4 with new cluster_id
→ Tag as emerging issue in To-Do list
```

### How Complaints Surface In Each Data Out Channel

**In To-Do List:**
```
Complaint clusters ranked by weight, not individual complaints
Format:
[URGENT] Drainage overflow — Ward 42 — 7 complaints — 14 days old
[HIGH]   Street light outage — Ward 17 — 3 complaints — 6 days old
[NEW]    Water supply — Ward 8 — 1 complaint — today
```

**In Chat:**
```
Natural language queries about complaints:
"What are the top issues in Ward 42?"
→ Pulls clusters from DB 2 linked to Ward 42
→ Ranked by weight
→ Cross-referenced with DB 1 for constituency context
→ Historical pattern from DB 2

"Who complained about the drainage issue?"
→ Pulls individual complaints from DB 4 linked to drainage cluster
→ Lists citizen names and contacts for follow-up
→ Shows timeline of when each complaint came in

"Is the drainage issue in Ward 42 a recurring problem?"
→ DB 2 searched for historical drainage issues in Ward 42
→ "Yes — similar issue raised Aug 2023 and Jun 2024
   Both resolved via PWD in 15-20 days
   This is the third occurrence — pattern recognized"
```

**In Commitment Tracker:**
```
When politician commits to resolving a complaint cluster:
→ Entry created in DB 3 with deadline
→ All linked complaints in DB 4 marked "in-progress"
→ When resolved:
   → All linked DB 4 complaints marked resolved + timestamp
   → Cluster in DB 2 updated as resolved
   → Resolution injected into DB 2 as historical fact
   → Staff can notify citizens via their original channel
```

**In Digest:**
```
Daily:
→ New complaints received today: count by channel
→ New issue clusters created today: count + summary
→ Clusters with weight increase today: which ones grew
→ Issues resolved today: which ones closed

Weekly Sunday:
→ Complaint resolution rate this week vs last week
→ Which wards generated most complaints this week
→ Oldest unresolved issue and its current weight
→ Emerging patterns: any cluster growing faster than normal
→ Total open issues count
```

---

## 11. Data Out Layer

### 11.1 To-Do List

**What it is:** Live, continuously updated task list pulled from DB 3 (timely commitments) and complaint clusters from DB 2.

**What it shows:**
```
Priority ranked by weight
Format for each item:
[WEIGHT] [TYPE] Description | Due: date | Source: meeting/complaint
[8] COMMITMENT: Follow up PWD on drainage Ward 42 | Due: Jan 15 | OVERDUE 12 days
[5] COMPLAINT CLUSTER: Street light Ward 17 — 3 complaints | 6 days old
[3] QUESTION: Answer constituent query on PM Awas Yojana | Due: tomorrow
[1] ACTION: Call Commissioner Singh re: road repair | Due: this week
```

**Simple design decision:** No department categorization in to-do — kept simple as requested. Politician sees what needs to be done in priority order. That's it.

**Updates:** Automatically — every time a new commitment is extracted from a meeting, every time a new complaint cluster is created or weight increases, every time a deadline passes and weight escalates.

---

### 11.2 Commitment Tracker

**What it is:** Personal accountability mirror. Shows the politician's track record with their own commitments over time.

**What it shows:**

```
OPEN COMMITMENTS:
[List of pending commitments from DB 3 — same as To-Do but filtered to commitments only]

COMPLETED COMMITMENTS (historical, from DB 2):
Timeline of resolved commitments with:
→ What was promised
→ To whom
→ When committed
→ When resolved
→ Was it on time or overdue?
→ How many extensions?

PATTERNS RECOGNIZED:
→ "You have made 23 commitments this month. 14 resolved on time (61%)"
→ "Commitments involving PWD average 28 days to resolve"
→ "Ward 42 receives the most commitments — 8 open currently"
→ "3 commitments have been extended more than twice — systemic issue?"
→ "Your on-time resolution rate has improved from 45% to 61% over 3 months"
```

**Why this matters:** No staff member can tell a politician their own track record honestly. This system does it without politics or fear.

---

### 11.3 Suggestions (On Demand Only)

**What it is:** AI thinks proactively about the politician's situation and generates strategic suggestions. Only generated when the politician explicitly requests it — never automatic.

**How it works:**
```
Politician taps "Get Suggestions"
        ↓
AI calls all four DBs
        ↓
Cross-references:
→ Open commitments vs constituency context
→ Complaint patterns vs seasonal/historical data
→ Pending action items vs department track records
→ Upcoming events or deadlines vs current workload
        ↓
Generates 3-5 specific, actionable suggestions
```

**Example output:**
```
Suggestions for you today (generated on demand):

1. URGENT — Ward 42 drainage commitment is 12 days overdue.
   Historically PWD resolves this in 18 days when escalated directly.
   Commissioner Singh delivered last time. Recommend direct call today.

2. PATTERN — Monsoon is 8 weeks away.
   Last 3 years, Ward 42 and Ward 17 flooded.
   Pre-monsoon drain cleaning was done in 2023 but not 2024 — 2024 flooded worse.
   Recommend: Schedule PWD inspection this week before monsoon prep window closes.

3. OPPORTUNITY — 340 residents in Ward 8 are potentially eligible for
   PM Awas Yojana but haven't applied.
   You have a camp office visit to Ward 8 next week — timing is perfect
   to run a scheme awareness drive.

4. ACCOUNTABILITY — You made 4 commitments in the January 20 meeting
   with the Ward Councillors. 2 are unresolved with no update logged.
   Staff may not be tracking these. Review before next interaction.
```

**Why on-demand not automatic:** Automatic suggestions would become noise. When the politician chooses to ask, they are in a mindset to receive and act on suggestions. Output is always contextually relevant to right now.

---

### 11.4 Chat Interface

**What it is:** Natural language conversation with the Co-Pilot. The day-to-day workhorse. Everything the politician needs that isn't in the other four interfaces lives here.

**What it can do:**
```
Query any combination of the four DBs in natural language:
→ "What did I promise in the February 10 meeting with PWD?"
→ "Which ward has the most unresolved complaints?"
→ "Draft a response to the drainage complaints in Ward 42"
→ "What is my track record with water supply issues?"
→ "Has Commissioner Singh delivered on time before?"
→ "Prepare me for tomorrow's meeting with the DM"
→ "What schemes is Ward 17 underutilizing?"
→ "How many open commitments do I have right now?"
→ "What happened the last time we had flooding in Ward 42?"

Draft communications:
→ "Draft a letter to PWD about the Ward 42 drainage issue"
→ "Write a speech for the Ward 17 community meeting tomorrow"
→ "Draft a response email to the constituent who complained about water supply"

The pre-meeting brief lives here:
→ "Brief me on my 3pm meeting with Commissioner Singh"
→ System pulls: last interaction history, open items with him,
   his track record of follow-through, relevant constituency context,
   suggested agenda points, questions to ask based on pending items
```

**What it cannot do:**
- Browse the internet
- Access any external system
- Update DB 1 (only staff can do that)
- Send emails or communications on its own

---

### 11.5 Digest

**What it is:** Structured daily/weekly compilation for reflection. Not an action tool — a reflection tool. The politician reviews it to understand what happened and what the picture looks like.

**Daily Digest (Monday to Saturday):**
```
Generated: end of day or on demand

TODAY'S MEETINGS:
→ [Meeting name/person] — Key points: ... — Commitments made: X — Action items: Y

TODAY'S COMPLAINTS:
→ Received: X new complaints
→ New issue clusters created: X (list them)
→ Issue clusters with weight increase: X (which ones)
→ Issues resolved: X

TODAY'S COMMITMENTS:
→ New commitments logged: X
→ Commitments resolved: X
→ Commitments that became overdue today: X (which ones)

OVERALL SNAPSHOT:
→ Total open commitments: X
→ Total open issue clusters: X
→ Oldest unresolved complaint: X days old
```

**Weekly Digest (Sunday only — replaces daily):**
```
THIS WEEK IN SUMMARY:

MEETINGS: X meetings held, X commitments made, X resolved

COMPLAINTS:
→ Total received this week: X
→ Resolution rate: X% (vs last week X%)
→ Top ward by complaint volume: Ward X
→ Oldest unresolved cluster: X days

COMMITMENTS:
→ On-time resolution rate: X% (vs last week X%)
→ Average days to resolve: X days
→ Most overdue: [description] — X days

PATTERNS THIS WEEK:
→ [Any emerging patterns the AI noticed]
→ [Any seasonal patterns approaching]

NEXT WEEK HEADS UP:
→ Commitments due next week: X
→ Commitments at risk of becoming overdue: X
```

---

## 12. Complete System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          INPUT LAYER                                 │
│                                                                      │
│  [Mic / Pi Zero device] ──USB──→ Audio file on laptop              │
│  [Parliament transcript] ──Staff upload──→ Text file on laptop      │
│  [Email] ──Gmail API──→ Auto parsed complaint                       │
│  [Physical/Portal] ──Staff form──→ Structured complaint             │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────────┐
│                       EXTRACTION LAYER                               │
│                                                                      │
│  Audio/Transcript:                                                   │
│  Whisper (transcription) → WhisperX (diarization)                  │
│  → Extraction AI (separate model)                                   │
│  → Routes: Commitments → DB3 | Facts → DB2 | Questions → DB3       │
│                                                                      │
│  Complaint:                                                         │
│  Text embedding → Similarity search DB2                             │
│  → Similar: add weight to cluster                                   │
│  → New: create cluster                                              │
│  → Always: store raw in DB4                                         │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────────┐
│                      FOUR DATABASE LAYER                             │
│                                                                      │
│  DB1 — Static Constituency (PostgreSQL)                             │
│  ─────────────────────────────────────                              │
│  Ward demographics, infrastructure, schemes, history                │
│  ALWAYS called on every query — base context layer                  │
│  Updated only by staff manually                                     │
│  Never written to by AI                                             │
│                                                                      │
│  DB2 — RAG Historical Facts (ChromaDB vector store)                │
│  ─────────────────────────────────────                              │
│  Meeting facts, decisions, context                                  │
│  Complaint issue clusters with weights                              │
│  Resolved commitments injected from DB3 on completion              │
│  Grows automatically — institutional memory                         │
│                                                                      │
│  DB3 — Timely Commitments (PostgreSQL with weights)                │
│  ─────────────────────────────────────                              │
│  Time-sensitive items only — all have deadlines                     │
│  Weight increases as overdue (1→2→3→5→8)                          │
│  Never silently disappears                                          │
│  On completion → full record injected into DB2 → deleted from DB3  │
│                                                                      │
│  DB4 — Static Complaints (PostgreSQL)                              │
│  ─────────────────────────────────────                              │
│  Raw individual complaint records — never deleted                   │
│  Linked to DB2 clusters via cluster_id                             │
│  Used for citizen follow-up and audit trail                         │
│  When cluster resolved → all linked complaints marked resolved      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────────┐
│                      INTELLIGENCE LAYER                              │
│                                                                      │
│  Local LLM: Ollama + Phi-3 Mini or Llama 3 8B                      │
│  Orchestration: LangChain                                           │
│  Embeddings: sentence-transformers (offline)                        │
│                                                                      │
│  Every query:                                                       │
│  1. DB1 loaded as mandatory base context                            │
│  2. DB2 similarity searched for relevant historical facts           │
│  3. DB3 filtered for relevant timely items                         │
│  4. DB4 queried only if individual complaint details needed         │
│  5. All context assembled → Local LLM generates response           │
│                                                                      │
│  Zero internet. Zero cloud. Zero data leaves laptop.               │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────────┐
│                       DATA OUT LAYER                                 │
│                                                                      │
│  1. TO-DO LIST                                                      │
│     Live, weighted, simple                                          │
│     From DB3 commitments + DB2 complaint clusters                  │
│     Ranked by weight — highest priority first                       │
│     Updates automatically as weights change                         │
│                                                                      │
│  2. COMMITMENT TRACKER                                              │
│     Open commitments + completed history                            │
│     Personal accountability mirror                                  │
│     Patterns in resolution rate and department performance          │
│                                                                      │
│  3. SUGGESTIONS (ON DEMAND ONLY)                                   │
│     AI thinks proactively across all four DBs                      │
│     Only generated when politician explicitly requests              │
│     3-5 specific actionable suggestions                             │
│                                                                      │
│  4. CHAT INTERFACE                                                  │
│     Natural language to all four DBs                               │
│     Query anything, draft anything                                  │
│     Pre-meeting prep lives here                                     │
│     Day-to-day workhorse                                            │
│                                                                      │
│  5. DIGEST                                                          │
│     Daily (Mon-Sat): meetings + complaints + commitments of that day│
│     Weekly (Sunday): patterns, rates, trends, next week heads-up   │
│     Reflection tool — not action tool                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 13. Privacy & Security Architecture

### Core Principle
**Zero data leaves the laptop. Ever.**

### What This Means In Practice
```
Local LLM (Ollama) — runs on laptop CPU/GPU
Local vector store (ChromaDB) — files on laptop disk
Local relational DB (PostgreSQL) — runs on laptop
Local embeddings (sentence-transformers) — runs on laptop
No API calls to OpenAI, Anthropic, Google, or any external service
No telemetry, no analytics sent anywhere
No cloud sync
No backup to external storage (politician manages their own backup)
```

### Air-Gap Design For Hardware Device
```
Recording device (Pi Zero):
→ No WiFi chip activated
→ No Bluetooth transmission during recording
→ No network connectivity of any kind during use
→ Data transfer ONLY via physical USB connection
→ Politician controls when data moves
→ No data moves without deliberate physical action
```

### Data Audit Table

| Data Type | Stays on Device | Goes Anywhere |
|-----------|----------------|---------------|
| Meeting audio | ✅ | ❌ Never |
| Meeting transcripts | ✅ | ❌ Never |
| Commitments and promises | ✅ | ❌ Never |
| Complaint details | ✅ | ❌ Never |
| Constituency data | ✅ | ❌ Never |
| AI responses generated | ✅ | ❌ Never |
| Chat history | ✅ | ❌ Never |

### On Stage Statement
*"This system is architecturally incapable of leaking data. Not because of a policy or a setting — because there is no network connection to leak through. A politician's most sensitive conversations stay exactly where they should — with the politician."*

---

## 14. Tech Stack

### Core Intelligence
```
Local LLM:          Ollama (runtime)
LLM Model:          Phi-3 Mini (CPU-friendly) or Llama 3 8B (better quality)
Orchestration:      LangChain (Python)
Embeddings:         sentence-transformers (all-MiniLM-L6-v2, runs offline)
Vector Store:       ChromaDB (local, file-based)
```

### Transcription & Diarization
```
Transcription:      Whisper (OpenAI open source, runs offline)
Diarization:        WhisperX (combines Whisper + pyannote speaker separation)
Language:           Python
```

### Databases
```
Relational:         PostgreSQL (DB1 constituency + DB3 timely + DB4 complaints)
Vector:             ChromaDB (DB2 RAG historical facts)
```


### Hardware Device (Phase 2)
```
Processor:          Raspberry Pi Zero W
Microphone:         USB or I2S microphone module
Storage:            MicroSD card (32GB+)
Connection:         USB-C to laptop
Enclosure:          3D printed clip-on case
Indicator:          Single LED (recording status)
Cost:               ₹2,000-3,000
```




## 16. API Contracts

### POST /api/complaints/submit
Staff manual complaint submission

**Request:**
```json
{
  "citizen_name": "Ramesh Kumar",
  "citizen_contact": "98XXXXXXXX",
  "ward_id": 42,
  "description": "Nala overflow near plot 34 since 3 days",
  "channel": "manual",
  "received_at": "2026-02-26T09:23:00",
  "staff_notes": "Citizen very distressed, elderly"
}
```

**Response:**
```json
{
  "complaint_id": "CMP-2026-0234",
  "cluster_action": "added_to_existing",
  "cluster_id": "cluster_ward42_drainage_001",
  "cluster_weight": 8,
  "urgency_flag": true,
  "message": "Added to existing drainage cluster — now URGENT"
}
```

### POST /api/meetings/upload
Upload audio or transcript for processing

**Request:** multipart/form-data
```
file: audio.wav or transcript.txt
meeting_date: 2026-02-26
meeting_type: constituency / department / parliament
participants: "Commissioner Singh, Ward Councillor Sharma"
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "processing",
  "estimated_time_seconds": 120,
  "message": "Transcription and extraction started"
}
```

### GET /api/todo
Get prioritized to-do list

**Response:**
```json
{
  "items": [
    {
      "id": "timely_001",
      "text": "Follow up PWD on drainage Ward 42",
      "type": "commitment_made",
      "weight": 8,
      "deadline": "2026-01-15",
      "days_overdue": 12,
      "urgency": "critical",
      "source": "Meeting with Ward Councillors Jan 10"
    }
  ],
  "total_pending": 14,
  "critical_count": 2,
  "urgent_count": 4
}
```

### POST /api/chat
Chat with the Co-Pilot

**Request:**
```json
{
  "message": "Am I ready for tomorrow's Ward 42 meeting?",
  "context_hint": "meeting_prep"
}
```

**Response:**
```json
{
  "response": "Ward 42 briefing for tomorrow:\n\nURGENT: ...",
  "sources_used": ["db1_ward42", "db2_drainage_history", "db3_open_commitments"],
  "generated_at": "2026-02-26T14:30:00"
}
```

### GET /api/digest/daily
Get today's digest

**GET /api/digest/weekly**
Get this week's digest

---

## 17. Build Order & Prioritization

### Phase 1 — Intelligence Layer First (Priority)

Build this first because it is the core innovation. Everything else is input/output around it.

```
Step 1: Three DB setup (DB1 + DB3 + DB4 in PostgreSQL, DB2 in ChromaDB)
Step 2: Pre-load DB1 with real Delhi ward data from public sources
Step 3: LangChain + Ollama connected to all DBs
Step 4: Basic chat interface working end to end
Step 5: Complaint processing pipeline (embedding → similarity → cluster)
Step 6: Extraction AI for commitments from text input
Step 7: To-Do list pulling from DB3
Step 8: Commitment tracker with pattern detection
Step 9: Digest generation
Step 10: Suggestions engine
```

### Phase 2 — Input Layer (After Intelligence Works)

```
Step 11: Whisper transcription pipeline
Step 12: WhisperX diarization
Step 13: Gmail API complaint intake
Step 14: Staff manual complaint form UI
Step 15: Full meeting → transcript → extraction → DB pipeline
```

### Phase 3 — Hardware (If Time Allows)

```
Step 16: Pi Zero recording device setup
Step 17: USB transfer mechanism
Step 18: Integration with laptop pipeline
```

**Demo day if Phase 2/3 not perfect:**
*"Currently simulating audio input via pre-recorded transcript. Hardware device and live transcription replace this in production."*

Judges evaluate the intelligence layer. That's the innovation.

---

## 18. What To Build vs Simulate

### Actually Build — Everything Works For Real
```
✅ All four databases with real schema
✅ ChromaDB complaint clustering with real embeddings
✅ LangChain + Ollama RAG pipeline
✅ Chat interface — real queries, real responses
✅ To-Do list — real data from DB3
✅ Commitment tracker — real patterns
✅ Digest generation — real compilation
✅ Suggestions engine — real cross-DB reasoning
✅ Complaint similarity search — real vector comparison
✅ Staff complaint manual form
✅ DB3 → DB2 injection on completion
✅ Weight escalation logic
```

### Simulate Honestly With Clear Label
```
⚠️ Audio transcription → use pre-recorded meeting audio
   Label: "Simulating live recording — hardware device replaces this"

⚠️ Speaker diarization → may be imperfect on demo audio
   Label: "Best-effort speaker separation — improves with audio quality"

⚠️ Gmail API → can demo with pre-loaded email complaints
   Label: "Email auto-intake configured — showing pre-loaded example"

⚠️ Pi Zero hardware → show the physical device
   Even if it just records audio, plugging it in is the demo moment
   The transcription pipeline on laptop is what matters
```

---

## 19. Demo Flow

### Pre-Demo Setup (Night Before)
```
□ Pre-load DB1 with real Delhi ward data
□ Pre-load DB2 with sample historical facts and meeting summaries
□ Create realistic complaint clusters in DB2 with weights
□ Create realistic open commitments in DB3 with various weights/overdue states
□ Record a clean 3-minute fake "constituency meeting" audio
□ Run Whisper + WhisperX on that audio — verify transcript quality
□ Run extraction AI — verify commitments extracted correctly
□ Test full chat with 10 sample queries — verify good responses
□ Test complaint submission — verify clustering works
□ Prepare daily digest — verify it compiles correctly
□ Charge all devices
□ Test on presentation laptop specifically
```

## 22. Stage Talking Points

### On Privacy
*"This system is architecturally incapable of leaking data. Not because of a setting or a policy — because there is no network connection to leak through. The local LLM runs on the laptop. The databases live on the laptop. The device transmits nothing wirelessly. A politician's most sensitive conversations stay exactly where they should."*

### On Differentiation From ChatGPT
*"ChatGPT knows nothing about your constituency. It forgets every conversation. Your data trains their model. This system knows your Ward 42 flooding history. It remembers every commitment you made six months ago. Your data never leaves your laptop. That's not the same product."*

### On The Hardware Device
*"The device is intentionally dumb. It records. That's it. No processing. No transmission. The intelligence lives on the laptop where the politician controls it. The device is a trusted input mechanism, not a surveillance tool."*

### On Institutional Memory
*"When a politician's PA leaves after 5 years, institutional knowledge walks out the door. New staff starts from zero. This system doesn't retire. Doesn't forget. Doesn't get political. The experience compounds over years regardless of staff changes."*

### On Accountability
*"No staff member will honestly tell a politician their on-time commitment rate is 45%. This system does. Not to embarrass — to improve. The politician who governs with accurate self-knowledge governs better."*

### On The Complaint Architecture
*"We don't dump complaints into an AI and hope for the best. We cluster them intelligently — 47 raw complaints become 12 clear issues with weights and histories. The politician sees what needs attention, not a firehose of noise."*

---

DAY 1:
□ Set up PostgreSQL locally
□ Create all four DB schemas
□ Install Ollama + Phi-3 Mini
□ Verify Ollama responds to a basic query

DAY 2:
□ Install LangChain + sentence-transformers + ChromaDB
□ Connect LangChain to Ollama + ChromaDB
□ Run one end-to-end RAG query — this proves the core works

DAY 3:
□ Pre-load DB1 with real Delhi ward data
□ Public sources: Census 2011, Delhi municipal corporation reports,
  MLA local area development fund reports (public)

DAY 7:
□ Full intelligence layer working — chat gives real answers
□ This is your go/no-go milestone

DAY 10:
□ All five data out interfaces working with test data

DAY 14:
□ PPT first draft ready
□ Submit before March 10 deadline



---

---

*AI Co-Pilot for Public Leaders — Built for India Innovates 2026*
*"Every politician retires. Their experience shouldn't."*
*Contact: shoryavardhaan@gmail.com*
