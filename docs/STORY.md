# The Constituency — Internal Story Document

> Single source of truth for the Co-Pilot demo fictional world.
> All seed data, context files, demo scripts, and judge narratives derive from this.
> Aligned to proto2 codebase — profile defaults, seed.py, and hardcoded dashboard data.

---

## The MLA

**Name:** Shri Rajendra Kumar Verma
**Party:** Indian National Congress
**Designation:** MLA, Delhi Legislative Assembly
**Constituency:** Ward 42 — South Delhi
**Term start:** 2024 (first term)
**Email:** rajendra.verma@mla.delhi.gov.in
**Contact:** +91-11-XXXXXXXX
**Office address:** Plot 12, Sector 4, Ward 42, South Delhi — 110044
**Janata Darbar:** Wednesday, 10:00 AM – 1:00 PM

**Staff:**
- PA: Suresh Yadav — +91-98XXXXXXXX — manages appointments and Janata Darbar queue
- Office Manager: Priya Sharma — +91-99XXXXXXXX — handles paperwork and follow-ups

**Background:** Former schoolteacher. First-time politician. Won the 2024 seat narrowly. Known for being accessible at Janata Darbar. Struggles with the volume of commitments and follow-ups — no system before Co-Pilot.

---

## The Constituency

South Delhi constituency. Covers 6 municipal wards. Population approximately 2,70,000. Registered voters: 1,82,400.

### The Wards

| Ward | Character | Primary Issues |
|------|-----------|----------------|
| Ward 42 | Low income — near drain canal | Drainage overflow, flooding, basic amenities |
| Ward 17 | Mixed — market + residential | Street lights, road repair, encroachment |
| Ward 8 | Denser residential | Water supply, PM Awas Yojana uptake |
| Ward 3 | Older colony | Encroachment, park maintenance |
| Ward 11 | Planned colony | Scheme penetration, general upkeep |
| Ward 6 | Industrial fringe | Sanitation, transport |

### The Drainage Problem — Ward 42
The single biggest recurring issue. Ward 42 sits adjacent to a drain canal that overflows every monsoon. Has flooded 3 consecutive years. Pre-monsoon drain cleaning was done in 2022 — no flooding. Skipped in 2023 — major flooding. PWD is responsible but slow via department channels. Commissioner Singh is the key escalation contact — resolved a similar issue in 18 days when contacted directly in August 2024.

This is the anchor issue for the whole demo narrative.

### PM Awas Yojana — Ward 8
Estimated 340 residents in Ward 8 are eligible but have not applied. Low awareness of eligibility criteria. A camp office visit is being planned. This comes up at Janata Darbar repeatedly.

---

## Key Contacts (Fictional)

| Name | Role | Track Record |
|------|------|-------------|
| Commissioner Singh | South Delhi Municipal Commissioner | 2 of 2 resolved when contacted directly. Slow via department routing. |
| PWD Department | Public Works — roads and drainage | Average 28 days resolution. Routing through department does not work. |
| DJB (Water) | Delhi Jal Board — water supply | Handles Ward 8 water complaints. Moderately responsive. |
| MCD | Municipal Corporation — street lights, sanitation | Handles Ward 17 street lights. Variable response time. |

---

## Active Issues In The System (Seed Data Reference)

These are the items that should exist after running seed.py:

### Meeting Commitments
| Title | Source | Meeting Date | Ward | Status |
|-------|--------|-------------|------|--------|
| Follow up with PWD on Ward 42 drainage | ward_coord_meeting.m4a | ~8 days ago | Ward 42 | Pending — overdue → W5+ critical |
| Check PM Awas Yojana eligibility for Ward 8 | janata_darbar_feb25.txt | Yesterday | Ward 8 | Pending — normal |

### Issue Clusters
| Summary | Ward | Weight | Urgency |
|---------|------|--------|---------|
| Street light outage in Sector 4, Ward 17 | Ward 17 | 5 | Urgent |
| Water supply irregular in Ward 8 | Ward 8 | 2 | Normal |

### Hardcoded Dashboard Items (to match in rich seed)
These appear in the static HTML and should be reflected in real seed data:
- Drainage overflow — Ward 42 — W8 Critical (flagship issue)
- Street light — Ward 17 Sector 4 — W3 Urgent
- Water supply — Ward 8 — W2 Normal
- Encroachment — Ward 3 — Resolved (completed item for history)
- Road repair update — Ward 17 main road — Urgent
- Call Commissioner Singh — road repair escalation — Action item
- Review scheme penetration — Ward 3 and Ward 11 — Low

### Recent Complaints (to replace hardcoded HTML)
| Citizen | Ward | Channel | Issue |
|---------|------|---------|-------|
| Ramesh Kumar | Ward 42 | Walk-in | Nala overflow near plot 34 — 3 days continuous |
| Sunita Devi | Ward 17 Sector 4 | Physical letter | Street light not working outside school — safety concern |
| Mohan Lal | Ward 8 | CPGRAMS | Water supply cut for 2 days — elderly citizen alone |
| RWA Ward 3 | Ward 3 | Walk-in | Illegal encroachment on community park entrance — Resolved |

---

## The Story Judges Will Hear

*"Rajendra Kumar Verma won the Ward 42 South Delhi seat in 2024 — his first election. He had no system. Commitments made at Wednesday Janata Darbar were written in a notebook by his PA Suresh Yadav. Citizen complaints arrived by letter, walk-in, and WhatsApp — tracked in an Excel sheet that was always out of date.*

*Six months in, he had 40+ open commitments with no visibility into which were overdue. A PWD drainage commitment made in January was still open in March — he found out only when the citizen came back to Janata Darbar angrier than before. Ward 42 flooded again that monsoon.*

*His PA was spending 2 hours every morning just trying to reconstruct what was pending. Nothing was escalating automatically. No one knew what was critical.*

*Co-Pilot is what he builds after that."*

---

## Demo Script — 5 Minutes

**Minute 1 — Home page**
Show hero: critical items, overdue count, on-time rate. "This is what Rajendra sees every Wednesday morning before Janata Darbar starts."

**Minute 2 — To-Do page**
Point to Ward 42 drainage at W8 critical — 14 days overdue. "The system escalated this automatically over two weeks. Weight went from 1 to 8. He didn't have to remember. The system remembered."

**Minute 3 — Log Issue live**
Type: "Water has not come for 3 days in Block C, Ward 8. Elderly woman, alone at home." Submit. Switch to To-Do — new cluster or weight increase appears. "That complaint just got embedded, matched to an existing water supply cluster, and added to the accountability list. Automatically."

**Minute 4 — Upload Meeting**
Upload `ward_coord_jan15.txt`. Watch items appear in To-Do. "His PA recorded this meeting. Uploaded the transcript. Gemini extracted 4 commitments. Nobody typed anything into a form."

**Minute 5 — Digest**
Show weekly numbers. Click "Became overdue this week" — overlay appears with items. "This is his Sunday review. What slipped this week. What got done. Where he's falling behind. One page, real numbers, no manual work."

---

## Sample Transcript File

Save as `ward_coord_jan15.txt` for the Upload Meeting demo:

```
Ward Coordinators Meeting — January 15
Attendees: MLA Rajendra Kumar Verma, PWD representative, Ward Councillors

Verma: The drainage situation in Ward 42 has to be resolved before monsoon. I need PWD to commit to pre-monsoon cleaning by March.

PWD: We can do an inspection by February 10th and schedule cleaning within three weeks of that.

Verma: I will follow up with PWD on Ward 42 drain cleaning by February 10th.

Councillor: Three street lights are out on the road near the primary school in Ward 17, Sector 4. Children are walking in the dark after school.

Verma: I will take up the Ward 17 Sector 4 street light issue with MCD within this week.

Councillor: The main market road in Ward 17 has had potholes since October. Shopkeepers have complained multiple times.

Verma: I will ask PWD to inspect Ward 17 market road and give a repair timeline by January 22nd.

Councillor: Two families in Ward 8 came to me asking about PM Awas Yojana. They do not know how to apply.

Verma: Please share their details with Suresh. I will check their eligibility and respond within 3 days.
```

---

## Seed Data Rules

- Ward numbers: only 42, 17, 8, 3, 11, 6
- Departments: PWD, DJB, MCD, Revenue, Education
- Key contacts: Commissioner Singh, Suresh Yadav (PA), Priya Sharma (manager)
- Meeting source_ids: `ward_coord_meeting.m4a`, `janata_darbar_feb25.txt`, `pwd_meeting_feb10.txt`, `dm_meeting_feb22.txt`
- Citizen names: Ramesh Kumar, Sunita Devi, Mohan Lal, Geeta Bai, Abdul Rehman, Priya Singh, RWA Ward 3
- No real phone numbers, no real Delhi pin codes, no real political figures beyond party name

### Target Seed State
- 2 critical items (W5-W8) — overdue
- 3 urgent items (W3) — deadline this week  
- 4 normal items (W1-W2) — future deadlines
- 3 completed items — history page not empty
- 1 extended item — extension_count = 1
- 4 complaint clusters — weights 1, 2, 3, 5
- 8 individual complaints linked to those clusters

---

*Last updated: proto2*
*Do not add real names, real addresses, real phone numbers, or real officials to seed data.*
