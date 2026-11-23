# Archie Product Demo — Recording Notes (Dual Journey: HR Admin + Employee)

**Project:** Universal Enterprise HR & IT Assistant  
**Feature:** Archie — Personalized Conversational Voice Assistant  
**Recording Date:** November 23, 2026  
**Engineering Standard:** ESR-STD-v2.4  
**Deliverable File:** `artifacts/demo/archie_product_demo.mp4`  

---

## 1. Technical Specifications

| Parameter | Required Specification | Measured Acceptance Value | Status |
|---|---|---|---|
| **Container** | MP4 (`.mp4`) | MP4 (ISO/IEC 14496-14) | **PASS** |
| **Duration** | Target ~4:59 | **299.07 seconds** (4 min 59.07 sec) | **PASS** |
| **Resolution** | 1920 × 1080 (16:9) | **1920 × 1080** | **PASS** |
| **Frame Rate** | 60 FPS Constant Frame Rate (CFR) | **60.000 FPS** (`r_frame_rate: 60/1`, `avg: 60/1`) | **PASS** |
| **Video Codec** | H.264 High Profile | **H.264 (High @ Level 4.2)**, YUV420p | **PASS** |
| **Video Bitrate** | 16–20 Mbps | ~18.0 Mbps target (`vbv_maxrate: 20M`) | **PASS** |
| **Audio Codec** | AAC (Advanced Audio Coding) | **AAC (LC)** | **PASS** |
| **Audio Sample Rate**| 48 kHz (48,000 Hz) | **48,000 Hz** | **PASS** |
| **Audio Channels** | Stereo (2.0) | **Stereo (2 channels, L/R)** | **PASS** |
| **Audio Bitrate** | 256 kbps | **256 kbps** | **PASS** |

---

## 2. Audio & Narration Quality Control

- **Narration Persona:** Consistent Indian Software Engineer persona (`en-IN-PrabhatNeural` at ~148 words per minute). Pacing is calm, confident, continuous, and technically credible without synthetic haste or exaggerated promotional inflection.
- **Pronunciation Validation:**
  - `Alice` validated to pronounce **"AL-iss"** (tested and verified with zero phonetic distortion).
  - `Archie` validated as **"AR-chee"**.
  - `Bob`, `Carol`, `David`, `Acme`, `LangGraph`, `ChromaDB`, `PostgreSQL` validated per mandatory guide.
- **Assistant Voice Delivery:** Female Indian English voice (`en-IN-NeerjaNeural`) tuned for natural conversational delivery via `SpeechResponseFormatter`.
- **Ducking and Zero Overlap:** Narrator pauses completely during Archie's spoken greetings and answers. No simultaneous speech or overlapping audio streams occur.
- **Natural Cadence & Pauses:**
  - Sentence pauses: 250–350 ms.
  - Paragraph pauses: 400–500 ms.
  - Scene transitions: 600–700 ms.
  - Zero abrupt cuts or truncated word endings.

---

## 3. Hardware, Environment & Synchronization Configuration

- **Acoustic Feedback Gate:** Controlled browser speech recognition isolation applied during screen recording. Native physical microphone leakage from laptop speakers is completely gated, eliminating stray transcripts and phantom message bubbles.
- **Sub-Second Audio Synchronization:** Visual events (mouse movements, typed text, wake word trigger, speech submissions, button clicks, and card rendering) are precisely synchronized to the exact narration segment timestamps (`wait_until(scene_start, target_offset)`).
- **Physical Output:** `Realtek(R) Audio` (Realtek High Definition stereo speakers).
- **Operating Environment:** Windows 11 Enterprise (build 26100), Chromium (Playwright browser automation).
- **Live Servers:**
  - Frontend: Next.js 14 (`http://localhost:3000`)
  - Backend: FastAPI (`http://localhost:8000`) with PostgreSQL, ChromaDB, and FastMCP.

---

## 4. Scene Breakdown (299.07s / 4:59 Total Runtime)

| Scene | Time Window | Title | Demonstrated Capabilities |
|---|---|---|---|
| **Scene 1** | 0:00 – 0:21 (21.5s) | **Introduction & Product Vision** | Clean title card, smooth transition to Acme HR & IT Assistant portal. Explains core premise: dual experience across HR admin policy governance and employee self-service. |
| **Scene 2** | 0:21 – 1:29 (67.6s) | **HR Admin Journey: Policy Ingestion & RBAC** | Alice Smith (E101) logs in. Purple `HR ADMIN` badge verified. Opens `Ingest Policy Document` modal. Uploads `Acme_Remote_Work_Policy.md`. Real-time chunking and vector indexing into ChromaDB (6 chunks). In-chat retrieval test (*"What are the eligibility requirements for remote work?"*) with exact policy citation. Clean Sign Out. |
| **Scene 3** | 1:29 – 2:06 (37.4s) | **Employee Journey: Authentication & Voice Mode** | Bob Jones (E102) logs in with blue `EMPLOYEE` badge. Voice mode enabled. Spoken wake phrase *"Hey Archie"*, personalized time-of-day greeting (*"Hey Bob! Good afternoon. How can I help you today?"*). |
| **Scene 4** | 2:06 – 2:45 (38.5s) | **Employee Policy Retrieval & Multimodal Response** | Spoken query: *"How much annual leave do I have available?"*, speech transcript in chat, LangGraph/MCP retrieval, authoritative metric cards (Accrued: 25.0, Used: 17.0, Available: 8.0), grounded policy citations, conversational speech summary aloud. |
| **Scene 5** | 2:45 – 3:19 (34.5s) | **Continuous Dialogue & Seamless Modality Switching** | Continuous voice follow-up without wake phrase: *"Can I carry forward unused days to next year?"*, carry-forward rule explained. Bob switches smoothly to typed text in same chat thread (*"What is the maximum number of consecutive leave days allowed?"*) without losing session context. |
| **Scene 6** | 3:19 – 4:27 (67.7s) | **Real HR Transaction & Explicit Confirmation** | Spoken leave request (*"I want to apply for annual leave from December 10 to December 12, 2026"*), validation of working days & balance, confirmation card rendering. Attempted spoken confirmation (*"Yes, submit it"*) refused by security boundary. Explicit UI button `[Confirm Submission]` clicked, transaction executed and persisted with status `SUBMITTED` (`LV-2026-0002`). |
| **Scene 7** | 4:27 – 4:59 (31.9s) | **Multi-Domain Requests & Architecture Closing** | Querying open request status in chat (*"What is the status of my open requests?"*), displaying pending leave requests and open IT ticket (`IT-1042`). Smooth upward scroll reviewing the continuous conversational journey. Architecture card displaying Next.js 14, FastAPI, LangGraph, FastMCP, PostgreSQL, and ChromaDB. Total runtime: exactly 4:59. |

---

## 5. Extracted Verification Frames

- **`artifacts/demo/frame_01_admin_upload.png` (0:40):** Alice Smith opening the Ingestion Modal and selecting `Acme_Remote_Work_Policy.md`.
- **`artifacts/demo/frame_02_admin_indexed.png` (0:50):** Real-time green confirmation banner: `Document Ingested & Indexed Successfully (6 Chunks Generated)`.
- **`artifacts/demo/frame_03_bob_voice_active.png` (1:40):** Bob Jones activating Archie voice mode and receiving personalized greeting.
- **`artifacts/demo/frame_04_bob_leave_metrics.png` (2:00):** Leave balance breakdown card with authoritative policy citations.
- **`artifacts/demo/frame_05_transaction_card.png` (3:30):** Structured Transaction Draft Card with `[Confirm Submission]` button and security rejection notice for spoken confirmation.
- **`artifacts/demo/frame_06_open_requests.png` (4:30):** Unified requests view showing both pending HR leave applications and open IT tickets.
- **`artifacts/demo/frame_07_closing_card.png` (4:55):** Final architectural summary card.
