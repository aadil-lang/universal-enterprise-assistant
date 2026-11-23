# Acme HR & IT Assistant — Product Walkthrough Summary

**Video File:** `artifacts/demo/acme_hr_it_assistant_walkthrough.mp4`  
**Standard:** ESR-STD-v2.4  
**Date:** November 23, 2026  
**Auditor / Presenter:** Autonomous Verification Lead (DeepMind / Antigravity)  
**Narration Persona:** Indian Software Engineer (Indian English accent, confident, conversational, technically grounded)  

---

## 1. Video Specifications

| Metric | Target Requirement | Measured Output | Status |
|---|---|---|---|
| **Duration** | 3:00 – 4:00 minutes (180 – 240s) | **3:23.47 minutes (203.47s)** | **PASSED** |
| **Resolution** | 1920×1080 (16:9 Full HD) | **1920×1080** | **PASSED** |
| **Frame Rate** | 30 fps | **30.0 fps** | **PASSED** |
| **Video Codec** | H.264 / AVC1 (High Profile, YUV420p) | `libx264` (CRF 18) | **PASSED** |
| **Audio Codec** | AAC (Clear narration, no background hum) | `AAC` (144 kbps, 24 kHz) | **PASSED** |
| **File Size** | Web-optimized (< 50 MB) | **12.23 MB** | **PASSED** |
| **Presenter Cursor** | Visible, smooth Loom-style pointer | Active circular pointer with click-scaling | **PASSED** |

---

## 2. Walkthrough Scene Breakdown

### Scene 1 — Introduction (0:00 – 0:28)
- **Visual:** Clean Acme Corporation login page (`http://localhost:3000`) showing the unified portal branding, corporate email/password fields, and quick-access role cards.
- **Presenter Focus:** Introduces the Universal Enterprise HR & IT Assistant built for Acme Corporation, explaining the single conversational interface for company policy RAG, employee self-service workflows, and authorized HR administration.
- **Evidence Snapshot:** `artifacts/demo/snapshots/scene1_intro.png`

### Scene 2 — Employee Login & Policy Assistant (0:28 – 0:59)
- **Visual:** Authenticates as Bob Jones (`bob@acme.com` / `E102`). Asks policy question: *"What is the annual vacation entitlement, and how many unused days can I carry forward?"*.
- **Presenter Focus:** Demonstrates retrieval-augmented generation grounded in Acme's indexed policy documents rather than general LLM speculation. Highlights the displayed document citation and active version pointer.
- **Evidence Snapshot:** `artifacts/demo/snapshots/scene2_policy_citation.png`

### Scene 3 — Leave Application & Explicit Confirmation (0:59 – 1:35)
- **Visual:** Submits leave request for December 10–12. Assistant computes 3 days, checks available balance (8.0 days), and renders the interactive **Confirmation Card**. Click **Confirm Submission**, receiving persisted Request ID `LV-2026-0003`. Asks *"What is the status of my latest leave request?"*, showing persisted status.
- **Presenter Focus:** Emphasizes human-in-the-loop transaction boundaries, balance reservation, and request persistence.
- **Evidence Snapshots:** `artifacts/demo/snapshots/scene3_leave_card.png`, `artifacts/demo/snapshots/scene3_leave_status.png`

### Scene 4 — IT Support Ticket Creation (1:35 – 2:00)
- **Visual:** Submits ticket: *"My laptop screen is flickering constantly, please raise an IT ticket"*. Assistant categorizes issue as **Hardware**, sets Priority to Medium, renders structured confirmation card, and persists ticket `IT-1043`.
- **Presenter Focus:** Reviews automated issue categorization and explicit confirmation before write.
- **Evidence Snapshot:** `artifacts/demo/snapshots/scene4_it_ticket.png`

### Scene 5 — Expense Reimbursement Workflow (2:00 – 2:23)
- **Visual:** Requests $150 ergonomic chair reimbursement. Assistant validates category against the annual $300 ergonomic stipend policy, renders the review card, and confirms transaction.
- **Presenter Focus:** Explains policy-aware validation and persistent financial accounting.
- **Evidence Snapshot:** `artifacts/demo/snapshots/scene5_reimbursement.png`

### Scene 6 — HR Administrator Access (2:23 – 2:52)
- **Visual:** Signs out of Bob's account and logs in as Alice Smith (`alice@acme.com` / `E101` - HR Admin). Submits query: *"Show me the leave balance and open tickets for employee E102"*. Assistant returns authorized cross-employee records.
- **Presenter Focus:** Demonstrates backend-enforced RBAC (regular employees restricted to self-records; HR admins permitted cross-employee lookups).
- **Evidence Snapshot:** `artifacts/demo/snapshots/scene6_hr_admin.png`

### Scene 7 — Architecture & Milestone Conclusion (2:52 – 3:23)
- **Visual:** Smooth scroll through the rich conversation transcript, highlighting category badges, execution timing metadata, citations, and confirmation history.
- **Presenter Focus:** Summarizes underlying tech stack (FastAPI, Next.js 14, LangGraph, PostgreSQL 16, ChromaDB, FastMCP HTTP). Summarizes prototype status and acknowledges deferred distributed hardening roadmap.
- **Evidence Snapshot:** `artifacts/demo/snapshots/scene7_conclusion.png`

---

## 3. Workflows Successfully Demonstrated

1. **Authentication & Session Management** (Employee Bob Jones `E102` & HR Admin Alice Smith `E101`).
2. **Policy RAG with Citations** (`Employee_Handbook_2026.pdf v2.1`).
3. **Leave Request Submission & Balance Check** (Annual Leave 3.0 days).
4. **Interactive Confirmation Cards** (Human-in-the-loop verification before write).
5. **Real-Time Request Status Lookup** (PostgreSQL-backed query).
6. **IT Support Ticket Creation** (Hardware category, priority, ticket ID).
7. **Expense Reimbursement Claim** (Ergonomic chair $150, stipend policy check).
8. **HR Administrator Cross-Employee Access** (Authorized profile, leave, and ticket inspection).

## 4. Omitted Scenes or Workflows

- **Omitted Scenes:** **None**. All 7 planned scenes were fully executed and recorded live.
- **Synthetic Shortcuts:** **None**. All interactions occurred against the live running Next.js web application and FastAPI backend.

---
*Verified under ESR-STD-v2.4 on November 23, 2026.*
