# Pre-Flight Runtime Verification & Failure Handling Report

**Standard:** ESR-STD-v2.4  
**Date:** November 22, 2026  
**Auditor:** Independent Product Dogfooding Agent  
**Mandate:** Critical Runtime and Authenticity Requirements (§3 Failure Handling)

---

## 1. Executive Summary & Audit Mandate

Section 3 of the prompt mandates strict runtime authenticity:
> *"Launch or connect to the actual project application. Use the real frontend and backend. Use the actual configured Gemini integration. Use the real PostgreSQL, ChromaDB, and MCP services. Do not substitute mock mode. If Gemini or MCP still fails: 1. Stop the affected demonstration. 2. Capture the actual error and relevant logs. 3. Do not fake the expected response. 4. Do not silently switch to mock mode. 5. Report which portions of the video can genuinely be recorded. 6. Request authorization before making any application changes. A technically honest partial recording is preferable to a fabricated complete demonstration."*

In accordance with this requirement, a pre-flight verification was executed against the actual production/development configuration specified in `.env` and `docker-compose.yml`.

---

## 2. Empirical Pre-Flight Diagnostic Results

### 2.1 Docker Daemon & Container Infrastructure Check
* **Command:** `docker ps`
* **Execution Mode:** Unsandboxed host execution (`BypassSandbox: true`)
* **Observed Result:**
  ```text
  failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine;
  check if the path is correct and if the daemon is running:
  open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
  ```
* **Status:** **BLOCKED (Host Environmental Limitation)**
* **Diagnosis:** The Docker Desktop Linux daemon is not running on this Windows host. Consequently, the multi-container topology defined in `docker-compose.yml` (`acme-postgres`, `acme-chromadb`, `acme-mcp-server`, `acme-api`) is offline.

---

### 2.2 Live PostgreSQL Database Connectivity Check
* **Configuration Target:** `DATABASE_URL=postgresql+psycopg://acme_app:acme_secure_dev_pw_2026@postgres:5432/acme_assistant` (from `.env`)
* **Verification Script:**
  ```python
  from app.core.auth import get_auth_session_factory
  f = get_auth_session_factory()
  sess = f()
  sess.execute(text('SELECT 1'))
  ```
* **Observed Error Traceback:**
  ```text
  psycopg.OperationalError: failed to resolve host 'postgres': [Errno 11001] getaddrinfo failed
  sqlalchemy.exc.OperationalError: (psycopg.OperationalError) failed to resolve host 'postgres'
  ```
* **Status:** **FAILED**
* **Diagnosis:** Without Docker networking or a native PostgreSQL Windows service, the Docker internal DNS name `postgres` cannot be resolved on the host network.

---

### 2.3 Live Model Context Protocol (MCP) Server Connectivity Check
* **Configuration Target:** `MCP_HOST=mcp-server`, `MCP_PORT=8001` (from `.env`)
* **Observed Result:**
  ```text
  TransportError: Failed to connect to FastMCP Streamable HTTP endpoint at http://mcp-server:8001/mcp
  [Errno 11001] getaddrinfo failed
  ```
* **Status:** **FAILED**
* **Diagnosis:** The external FastMCP server process is configured to run inside a container (`mcp-server`), which is offline due to the Docker daemon being stopped.

---

### 2.4 Google Gemini LLM API Connectivity Check
* **Configuration Target:** 
  - `LLM_PROVIDER=gemini`
  - `GEMINI_API_KEY=<REDACTED_GEMINI_API_KEY>`
  - `GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`
  - `GEMINI_MODEL=gemini-3.5-flash-lite`
* **Verification Execution:** Direct HTTPS payload dispatch with `httpx` outside sandbox.
* **Observed Response:**
  ```json
  HTTP 200 OK
  {
    "choices": [{
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      }
    }],
    "model": "gemini-3.5-flash-lite"
  }
  ```
* **Status:** **LIVE & OPERATIONAL** (when executed with network access).
* **Diagnosis:** The Gemini API credentials and model endpoints are valid and functioning. However, during live in-browser queries, if the backend cannot retrieve employee records from PostgreSQL/MCP, the conversational state machine aborts before LLM synthesis can complete.

---

## 3. Adherence to Failure Handling Rules

Per Section 3 instructions:

1. **Stopped Affected Demonstration:**  
   The recording of the live chat interaction against the offline PostgreSQL/MCP container backend was stopped rather than proceeding with fabricated responses.
2. **Captured Actual Errors:**  
   The actual socket errors (`[Errno 11001] getaddrinfo failed` for `postgres:5432` and `mcp-server:8001`) and frontend error notification (`⚠️ I encountered an error while processing your request`) were recorded.
3. **Did Not Fake Expected Responses:**  
   We strictly refused to intercept HTTP requests or alter DOM nodes to simulate fictitious database responses.
4. **Did Not Silently Switch to Mock Mode:**  
   We have not switched `.env` to `LLM_PROVIDER=mock` or replaced the production database with an in-memory SQLite store without user authorization.
5. **Report of Genuine Recording Scope:**  
   See Section 4 below.
6. **Authorization Request:**  
   See Section 5 below.

---

## 4. Portions of the Video That Can Genuinely Be Recorded

Under the current host environment:

| Video Section | Content | Current Feasibility | Method / Limitations |
|---|---|:---:|---|
| **PART 1** | Architecture Introduction | **100% FEASIBLE** | Interactive visual architecture flow in browser. |
| **PART 2** | Application Intro & Login UI | **100% FEASIBLE** | Live Chromium navigation to `http://localhost:3000`, interface branding, role inspection. |
| **PART 3** | Employee Journey (Live Chat) | **PARTIALLY FEASIBLE (Live Error State)** | Live browser submits chat queries; UI displays authentic API error banner due to offline PostgreSQL/MCP containers. Real conversational data requires runtime authorization (Section 5). |
| **PART 4** | HR Administrator Journey | **100% FEASIBLE** | Alice Smith authentication, role badge verification, Document Upload modal interaction, format validation, and local PC Windows file picker demonstration. |
| **PART 5** | Security & Engineering Decisions | **100% FEASIBLE** | First-person technical explanation of RBAC, MCP read-only boundaries, and guardrails. |
| **PART 6** | Closing | **100% FEASIBLE** | Natural first-person conclusion. |

---

## 5. Formal Authorization Request

To enable a full 8–10 minute end-to-end recording with successful conversational query resolutions (Journeys A–F) and complete document ingestion retrieval:

**Proposed Standalone Demonstration Runtime:**
1. Start the local backend using an in-process SQLite instance pre-seeded with the authoritative Acme Corporation records (Bob `E102`, Alice `E101`, Carol `E103`) and an in-process FastMCP tool dispatcher.
2. Connect the LangGraph agent to the **live Google Gemini API** (`gemini-3.5-flash-lite`) via `GEMINI_API_KEY`, using the verified 14-chunk active ChromaDB policy index.
3. Execute the full browser recording with Playwright Chromium, including local Windows file picker interaction, policy ingestion, and grounded Gemini answer synthesis.

*Please confirm whether you authorize running the demonstration under this standalone live-Gemini runtime, or if you prefer a partial recording showcasing the authentic container failure state.*
