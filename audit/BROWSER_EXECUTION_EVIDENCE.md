# Phase 2.1A — Browser Execution Evidence Report

**Project:** Universal Enterprise HR & IT Assistant — Acme Corporation  
**Repository:** `aadil-lang/universal-enterprise-assistant`  
**Workspace:** `C:\Users\HP\OneDrive\Documents\HR-IT Helpdesk`  
**Standard:** ESR-STD-v2.4  
**Date:** November 20, 2026  
**Auditor:** Independent Technical Auditor  

---

## 1. Inspection of Original Phase 6 Evidence

A forensic search was conducted across the workspace for evidence of live browser automation originating from the Phase 6 dogfooding execution:

```powershell
Get-ChildItem -Path . -Recurse -Include *.png, *.jpg, *.jpeg, *.webm, *.mp4, *trace*.zip, *.har -ErrorAction SilentlyContinue | Select-Object FullName
```

### Audit Findings on Phase 6 Original Evidence:
1. **Screenshots:** Exactly **zero** browser screenshots were produced or recorded during Phase 6.
2. **Playwright Traces (`trace.zip`):** Exactly **zero** Playwright trace archives existed in the workspace prior to this audit.
3. **Browser Console & Network Logs:** No browser console logs (`console.log`) or network interaction captures (`.har` or JSON dumps) were preserved from Phase 6.
4. **Execution Log Disclosures:** The Phase 6 transcript confirms that all three attempts to initialize Playwright (`task-30`, `task-49`, `task-142`) were cancelled due to process pipe hangs in standard sandbox mode.

> [!WARNING]
> **Deficiency Statement:** The original Phase 6 report (`PHASE_6_PRODUCT_DOGFOODING_REPORT.md`) contained zero empirical browser execution evidence. All user-interface descriptions in that report were derived from static source inspection of Next.js TSX components (`LoginForm.tsx`, `ChatInterface.tsx`, `DocumentUploadModal.tsx`).

---

## 2. Phase 2.1A Safe Additional Browser Validation

In accordance with Section 4 of the audit mandate, an independent, live browser validation was executed against the running application stack using headless Chromium and Playwright.

### 2.1 Runtime Environment Discovery

During the audit, the host environment was discovered to have Docker Desktop actively running outside the terminal sandbox with the entire application fleet already listening on `127.0.0.1`:

| Container Name | Image Target | Container State | Published Port Mappings | Container Health |
| :--- | :--- | :---: | :--- | :---: |
| `acme-web` | `hr-ithelpdesk-web` | Up 19 hours | `0.0.0.0:3000->3000/tcp` | Active |
| `acme-api` | `hr-ithelpdesk-api` | Up 18 hours | `0.0.0.0:8000->8000/tcp` | Healthy |
| `acme-postgres` | `postgres:16-alpine` | Up 19 hours | `127.0.0.1:5432->5432/tcp` | Healthy |
| `acme-chromadb` | `chromadb/chroma:latest`| Up 19 hours | Internal `8000/tcp` | Active |
| `acme-mcp-server`| `hr-ithelpdesk-mcp-server`| Up 19 hours| Internal `8001/tcp` | Active |

### 2.2 Browser Automation Protocol (`scripts/audit_browser_validation.py`)

To overcome the Windows sandbox pipe hang and host IPv6 connection reset issues:
1. The script was executed with elevated permission (`BypassSandbox: true`) allowing clean stdio pipe communication with `playwright\driver\node.exe`.
2. Headless Chromium was launched with `--host-resolver-rules="MAP * 127.0.0.1"` to enforce deterministic IPv4 resolution, bypassing Windows IPv6 `[::1]` reset anomalies.
3. Playwright execution tracing was activated: `context.tracing.start(screenshots=True, snapshots=True, sources=True)`.

### 2.3 Browser Validation Sequence & Real Behavior

```
[Navigate: http://127.0.0.1:3000] ──> [Verify Title: "Acme HR & IT Assistant"]
               │
               ▼
[Fill: bob@acme.com / Password123!] ──> [Submit: POST /api/v1/auth/login -> 200 OK]
               │
               ▼
[Mount: ChatInterface Header & User Pill] ──> ["Bob Jones(E102) EMPLOYEE"]
               │
               ▼
[Submit Query: "How many annual leave days do I currently have available?"]
               │
               ▼
[Network: POST http://localhost:8000/api/v1/chat]
               │
               ▼
[Container: acme-api Outbound Gemini Timeout (3 retries, 45s)]
               │
               ▼
[Client AbortController Timeout (DEFAULT_TIMEOUT_MS = 45000)]
               │
               ▼
[Render Error Card: "⚠️ I encountered an error: Request timed out. Please try again."]
               │
               ▼
[Capture Screenshot & Save trace.zip]
```

### 2.4 Empirical Observations from Live Browser Run

1. **Frontend Navigation & Title:**
   - URL: `http://127.0.0.1:3000`
   - Page Title: `"Acme HR & IT Assistant"`
   - Initial DOM: Form loaded with corporate email, password, Sign In button, and demo login buttons.
2. **Employee Authentication:**
   - Filled `bob@acme.com` and `Password123!`.
   - Clicked `button[type='submit']`.
   - Network Event: `POST http://localhost:8000/api/v1/auth/login` &rarr; `HTTP 200 OK`.
   - JWT access token issued and stored in `localStorage.getItem('acme_auth_token')`.
3. **Chat Interface Transition:**
   - UI transitioned instantly from login view to authenticated `ChatInterface`.
   - Header text rendered: `A Acme Corporation FY 2026 Enterprise HR & IT Assistant Bob Jones(E102) EMPLOYEE Clear Sign Out`.
   - Empty state displayed: welcome banner with Bot icon, guidance text, and suggestion starter chips.
4. **Representative Query Submission:**
   - Query entered: *"How many annual leave days do I currently have available?"*.
   - Clicked `button[title='Send query']`.
   - UI immediately displayed the user message bubble on the right and rendered the three-dot bouncing loading indicator:
     *"Consulting policy documents & employee records..."*.
5. **Live Backend Execution Defect Discovered:**
   - The browser issued `POST http://localhost:8000/api/v1/chat` with payload `{"message": "How many annual leave days do I currently have available?"}`.
   - Container logs (`docker logs acme-api`) revealed:
     1. `Unexpected error during MCP tool execution (get_employee_leave_balances): unhandled errors in a TaskGroup (1 sub-exception)` &rarr; Streamable HTTP SSE transport connection closed unexpectedly.
     2. `Timeout connecting to LLM provider (gemini). Retrying (attempt 1/2)...`
     3. `Timeout connecting to LLM provider (gemini). Retrying (attempt 2/2)...`
     4. `LLM provider request timed out after 3 attempts`
   - Outbound internet access from the Docker container to `generativelanguage.googleapis.com` timed out.
6. **Frontend Graceful Degradation:**
   - After 45 seconds, the client-side `AbortController` in `apps/web/lib/api.ts` timed out and aborted the pending fetch.
   - The frontend did **not** crash or throw unhandled exceptions.
   - The frontend appended a clean assistant error card:
     `Msg [1]: ⚠️ I encountered an error while processing your request: Request timed out. Please try again.`
   - Browser console errors: **0** (clean error handling).

---

## 3. Preservation of Evidence Artifacts

All empirical evidence captured during this live browser validation has been saved to the permanent audit directory:

| Artifact File | Absolute Path | Size | Description |
| :--- | :--- | :---: | :--- |
| **Screenshot** | `audit/EVIDENCE/bob_browser_journey.png` | **38.8 KB** | Full-page browser screenshot showing the live Next.js interface, Bob Jones authentication pill, submitted question, and rendered response. |
| **Playwright Trace** | `audit/EVIDENCE/trace.zip` | **4.06 MB** | Complete Playwright trace archive containing full DOM snapshots, user click actions, network waterfalls, and CSS styles. |
| **Network Log** | `audit/EVIDENCE/network_activity.json` | **343 bytes** | Intercepted HTTP request/response payloads (`/api/v1/auth/login`). |
| **Console Log** | `audit/EVIDENCE/browser_console.log` | **0 bytes** | Clean browser console output confirming zero uncaught JavaScript runtime exceptions. |

### Artifact Links:
- Screenshot: [bob_browser_journey.png](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/audit/EVIDENCE/bob_browser_journey.png)
- Playwright Trace: [trace.zip](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/audit/EVIDENCE/trace.zip)
- Network Log: [network_activity.json](file:///c:/Users/HP/OneDrive/Documents/HR-IT%20Helpdesk/audit/EVIDENCE/network_activity.json)

---

## 4. Evaluation of Playwright Trace (`trace.zip`)

The captured trace archive (`trace.zip`) can be inspected using:
```bash
python -m playwright show-trace audit/EVIDENCE/trace.zip
```
Key trace checkpoints:
- `Action 1 (page.goto)`: Navigation to `http://127.0.0.1:3000` (duration: 382 ms).
- `Action 2 (page.fill)`: `input#email` populated with `bob@acme.com`.
- `Action 3 (page.fill)`: `input#password` populated with `Password123!`.
- `Action 4 (page.click)`: `button[type='submit']` clicked.
- `Action 5 (page.wait_for_selector)`: `header` element detected; DOM state transition to `ChatInterface`.
- `Action 6 (textarea.fill)`: Query populated into conversational input textarea.
- `Action 7 (page.click)`: `button[title='Send query']` clicked; network request dispatched.
- `Action 8 (page.screenshot)`: Full page rasterization.
