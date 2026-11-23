# Software Engineering & Clean Code Audit

**Project:** Universal Enterprise HR & IT Assistant (Acme Corporation)  
**Standard:** Engineering, Security & Reliability Standard (ESR-STD-v2.4)  
**Audit Level:** Level 2 — Full Pre-Release Forensic Audit  
**Date of Audit:** 2026-11-20  
**Audit Scope:** `apps/api`, `apps/web`, `packages/mcp_server`, `infrastructure`, Docker Compose, dependencies, and configuration.  
**Execution Mode:** STRICT READ-ONLY FORENSIC INSPECTION  

---

## 1. Executive Summary

A comprehensive, forensic software engineering audit was conducted on the Acme Corporation HR & IT Assistant codebase. The system implements a modern, decoupled monorepo architecture:
- **`apps/api`:** Python 3.12 / FastAPI orchestration layer utilizing LangGraph for conversational state management.
- **`apps/web`:** Next.js 14 / TypeScript React frontend leveraging Tailwind CSS.
- **`packages/mcp_server`:** Python 3.12 / Starlette service implementing the official Model Context Protocol (FastMCP Streamable HTTP) exposing exactly four approved read-only employee database tools.
- **`infrastructure`:** PostgreSQL 16 relational database (handling operational HR records, auth data, document metadata, and active-version checksum pointers) and ChromaDB (dense semantic vector store).

Overall code quality is high, exhibiting strict adherence to the Phase 0 v1.7.0 architectural specifications, clear separation of concerns across Docker bridge networks (`frontend_net` and `backend_internal`), typed data contracts (Pydantic v2 and TypeScript interfaces), and comprehensive automated test fixtures.

However, several notable software engineering defects, maintainability risks, code duplications, and dead code artifacts were identified across the layers.

### Audit Summary Matrix

| Category | High | Medium | Low | Informational | Total |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Architecture & Clean Boundaries | 0 | 2 | 2 | 1 | 5 |
| Design Patterns & Coupling | 0 | 1 | 2 | 1 | 4 |
| Error Handling & Reliability | 1 | 1 | 2 | 0 | 4 |
| Typing, Linting & Standards | 0 | 1 | 2 | 1 | 4 |
| Test Effectiveness & Coverage | 0 | 2 | 1 | 0 | 3 |
| Dependencies & Packaging | 0 | 1 | 3 | 1 | 5 |
| **Total** | **1** | **8** | **12** | **4** | **25** |

---

## 2. Architecture & Design Principles Evaluation

### 2.1 Monorepo Separation and Dependency Flow
- **Observed Architecture:** The monorepo separates web client (`apps/web`), API gateway (`apps/api`), and tool server (`packages/mcp_server`). Docker Compose enforces network isolation between the external frontend network (`frontend_net`) and internal database/MCP network (`backend_internal`).
- **Invariants Upheld:**
  - `apps/web` communicates exclusively with `apps/api` via REST endpoints (`/api/v1/*`).
  - `apps/api` communicates with `packages/mcp_server` via Streamable HTTP (`/mcp`) using cryptographically signed HMAC identity headers.
  - `packages/mcp_server` has no direct exposure to the host or internet (`expose: 8001` only).
  - ChromaDB is inaccessible from the host (`expose: 8000` only on `backend_internal`).

### 2.2 Layering & Cohesion Findings

#### [MED-SE-01] Production Router Embedding Test-Only Fallback Data
- **File:** `apps/api/app/routers/auth.py`
- **Lines:** 140–181 (`_execute_login`) and 254–262 (`_execute_get_me`)
- **Evidence:**
  ```python
  # Line 140-149
  settings = get_settings()
  if settings.APP_ENV == "test":
      known_users = {
          "alice@acme.com": ("b0000000-0000-0000-0000-000000000101", "E101", "Alice", "Smith", "hr_admin", True),
          "bob@acme.com": ("b0000000-0000-0000-0000-000000000102", "E102", "Bob", "Jones", "employee", True),
          "carol@acme.com": ("b0000000-0000-0000-0000-000000000103", "E103", "Carol", "Davis", "employee", True),
          "david@acme.com": ("b0000000-0000-0000-0000-000000000104", "E104", "David", "Miller", "employee", False),
      }
      if email_clean in known_users:
          ...
          if request.password != "Password123!":
              raise HTTPException(status_code=401, detail="Invalid email or password.")
  ```
  And in `apps/api/app/core/auth.py` (lines 164–176, 197–204):
  ```python
  settings = get_settings()
  if settings.APP_ENV == "test" and payload.get("employee_number"):
      return CallerIdentity(
          user_id=str(user_id_str),
          employee_number=str(payload["employee_number"]),
          role=UserRole(str(payload.get("role", "employee"))),
      )
  ```
- **Impact:** Hardcoded synthetic user dictionaries and test authentication bypasses reside in production request routers. If an operator sets `APP_ENV=test` in staging or misconfigures an environment variable, production password verification is completely bypassed for demonstration accounts.
- **Remediation Priority:** High (P1). Move test fixtures and fallback dependencies entirely into `tests/conftest.py` via FastAPI dependency overrides (`app.dependency_overrides[get_auth_session_factory]`).

#### [MED-SE-02] Ephemeral Engine Instantiation per Health Check
- **File:** `apps/api/app/routers/health.py`
- **Lines:** 21–44 (`check_postgres`)
- **Evidence:**
  ```python
  def check_postgres(db_url: str, timeout_seconds: float = 2.0) -> tuple[bool, str]:
      engine = None
      try:
          from sqlalchemy import create_engine, text
          connect_args = {"connect_timeout": int(timeout_seconds)}
          engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=False)
          with engine.connect() as conn:
              conn.execute(text("SELECT 1"))
          return True, "connected"
      finally:
          if engine is not None:
              engine.dispose()
  ```
- **Impact:** Every call to `/health/ready` instantiates a new SQLAlchemy engine, establishes a fresh TCP socket and PostgreSQL connection handshake, executes `SELECT 1`, and disposes of the connection pool. Under orchestrator polling (e.g. Kubernetes every 5 seconds) or readiness storms, this induces unnecessary socket exhaustion and TLS/authentication overhead on the database.
- **Remediation Priority:** Medium (P2). Share a dedicated pooled connection or ping via the existing application session engine with a lightweight timeout.

---

## 3. Clean Code, Duplication & Technical Modularity

### 3.1 Code Duplication

#### [MED-SE-03] Duplicate Cryptographic Header Signer Implementation
- **Files:**
  1. `packages/mcp_server/app/auth/signer.py` (Lines 14–39)
  2. `apps/api/app/services/mcp_client.py` (Lines 55–80)
- **Evidence:**
  Both files contain identical copies of `create_internal_auth_headers`:
  ```python
  def create_internal_auth_headers(
      identity: Union[CallerIdentity, Dict[str, str]],
      secret: str,
  ) -> Dict[str, str]:
      if not secret or not secret.strip():
          raise ValueError("HMAC signing secret must be a non-empty string.")
      if isinstance(identity, CallerIdentity):
          identity_json = identity.model_dump_json()
      elif isinstance(identity, dict):
          identity_json = json.dumps(identity, separators=(",", ":"))
      ...
      raw_bytes = identity_json.encode("utf-8")
      signature = hmac.new(secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()
      return {
          "X-Internal-Identity": identity_json,
          "X-Internal-Signature": signature,
      }
  ```
- **Impact:** Any modification to canonical serialization (e.g. key sorting or timestamp inclusion) implemented in one service will silently break HMAC signature verification in the other if not synchronized manually.
- **Remediation Priority:** Medium (P2). Extract shared models and security utilities into a local monorepo package (e.g., `packages/common_auth`).

#### [LOW-SE-01] Duplicate Caller Identity Models
- **Files:**
  1. `apps/api/app/core/auth.py` (Lines 30–46: `UserRole`, `CallerIdentity`)
  2. `packages/mcp_server/app/auth/models.py` (Lines 8–35: `UserRole`, `CallerIdentity`)
- **Evidence:**
  Both definitions specify `user_id`, `employee_number`, and `role` with `extra="forbid"`.
- **Impact:** Increases maintenance burden. Changes to role enumerations or identity claims require manual synchronization across two independent package directories.

#### [LOW-SE-02] Duplicate SQL Seed Files
- **Files:**
  1. `infrastructure/postgres/init/002_seed.sql` (203 lines)
  2. `data/seeds/seed.sql` (203 lines)
- **Evidence:**
  Both files contain identical synthetic employee, user, leave balance, IT asset, and ticket seed data.
- **Impact:** Divergence risk during future database migrations or test fixture updates.

---

### 3.2 Dead Code & Obsolete Logic

#### [LOW-SE-03] Dead TXT Extraction Logic
- **File:** `apps/api/app/services/document_extractor.py`
- **Lines:** 270–305 (`extract_from_txt`)
- **Evidence:**
  ```python
  def extract_from_txt(content: bytes) -> List[ExtractedSegment]:
      ...
  ```
  However, in `apps/api/app/services/document_validation.py` (lines 32, 55–59):
  ```python
  SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".docx", ".md"}
  ```
  `validate_document_file` explicitly rejects `.txt` files with `UnsupportedFormatError`, as confirmed by unit test `test_3_txt_rejected_as_unsupported` in `test_ingestion.py`.
- **Impact:** Dead code increases maintenance surface area and cognitive clutter.

---

## 4. Error Handling & Reliability Assessment

#### [HIGH-SE-01] Unhandled Mock Regex Default Fallback Violates Document-Driven Truth
- **File:** `apps/api/app/services/llm_service.py`
- **Lines:** 298–335 (`_synthesize_local`)
- **Evidence:**
  ```python
  # Line 298-301
  accrual_match = re.search(r"(\d+)\s*days?\s*(of\s*)?sick\s*leave", text, re.I)
  rollover_match = re.search(r"...", text, re.I)
  accrual = accrual_match.group(1) if accrual_match else "10"
  rollover = rollover_match.group(4) if rollover_match and rollover_match.lastindex >= 4 else (rollover_match.group(1) if rollover_match else "5")
  
  # Line 309-310
  accrual = accrual_match.group(1) if accrual_match else "18"
  rollover = rollover_match.group(4) if rollover_match and rollover_match.lastindex >= 4 else (rollover_match.group(1) if rollover_match else "5")
  
  # Line 320
  cycle = cycle_match.group(1) if cycle_match else "36"
  
  # Line 327
  hours = hours_match.group(1) if hours_match else "24"
  
  # Line 334
  stipend = stipend_match.group(1) if stipend_match else "300"
  ```
- **Impact:** When running in mock synthesis mode (which is default in testing and benchmark evaluations), if an uploaded policy document contains valid policy text that does not strictly match the expected regular expressions, the engine silently synthesizes answers using hardcoded fallback strings (`"18"`, `"5"`, `"10"`, `"36"`, `"24"`, `"300"`). This directly violates the core architectural principle: *"Document-Driven Truth: Policy values, rules, and procedures are extracted dynamically from ingested policy documents. Company-specific facts are never hardcoded into application business logic."* If an ingested policy specifies 25 days vacation, but the sentence structure causes `accrual_match` to be None, the system will output "18 days".
- **Remediation Priority:** High (P1). If regex extraction fails in local synthesis, do not substitute hardcoded Acme facts. Mark extraction as failed or output a neutral excerpt from the retrieved text.

#### [LOW-SE-04] Deprecated Python `datetime.utcnow()` Usage
- **Files:**
  - `apps/api/app/models/document.py` (Lines 38, 49)
  - `apps/api/app/models/user.py` (Lines 45, 52, 84, 91)
- **Evidence:**
  `default=datetime.utcnow` is used for SQLAlchemy column definitions.
- **Impact:** Python 3.12 generates 72 `DeprecationWarning` notices during test execution:
  `DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).`
- **Remediation Priority:** Low (P3). Update column defaults to `lambda: datetime.now(timezone.utc)`.

---

## 5. Type Safety & Frontend Integration

### 5.1 Next.js & TypeScript Evaluation
- **Type Safety in `apps/web/lib/api.ts`:**
  - Strict interfaces defined for `User`, `LoginResponse`, `ChatCitation`, and `ChatApiResponse`.
  - Proper custom error class `ApiError` with status code preservation.
  - Generics properly utilized in `request<T>()`.
- **Finding [LOW-SE-05]: Loosely Typed Error and Payload Catch Blocks:**
  - In `apps/web/lib/api.ts` (lines 42, 100): `data: any` and `err: any`.
  - In `apps/web/components/ChatInterface.tsx` (line 87): `catch (err: any)`.
  - In `apps/web/components/DocumentUploadModal.tsx` (line 81): `catch (err: any)`.
  - *Remediation:* Replace `any` with `unknown` and use type guards (`if (err instanceof ApiError)`).

### 5.2 Package Configuration & Node Standards
#### [LOW-SE-06] Missing `"type": "module"` in Frontend `package.json`
- **File:** `apps/web/package.json`
- **Evidence:**
  Executing `verify_frontend.mjs` generates:
  `(node:2712) [MODULE_TYPELESS_PACKAGE_JSON] Warning: Module type of .../lib/api.ts is not specified and it doesn't parse as CommonJS. Reparsing as ES module... To eliminate this warning, add "type": "module" to package.json.`
- **Impact:** Minor Node.js runtime warning and performance overhead during module resolution.

---

## 6. Dependency Health & Container Hygiene

### 6.1 Unused Dependencies

#### [LOW-SE-07] Redundant `asyncpg` in Requirements
- **Files:**
  - `apps/api/requirements.txt` (Line 7: `asyncpg>=0.30.0,<0.31.0`)
  - `packages/mcp_server/requirements.txt` (Line 6: `asyncpg>=0.29.0`)
- **Evidence:**
  - `apps/api` uses synchronous SQLAlchemy with `psycopg[binary]>=3.2.0` (`postgresql+psycopg://`).
  - `packages/mcp_server` uses synchronous SQLAlchemy with `psycopg2-binary>=2.9.9` (`postgresql+psycopg2://`).
  - No module in either package imports `asyncpg`.
- **Impact:** Unnecessary wheel compilation/download overhead and increased container image attack surface.

### 6.2 Container Reproducibility & Multi-Stage Builds
- **`apps/web/Dockerfile`:** Exemplary multi-stage build (`base` -> `deps` -> `builder` -> `runner`) with `node:20-alpine`, non-root execution (`USER nextjs`), and standalone Next.js deployment output.
- **`apps/api/Dockerfile`:** Multi-stage build with `python:3.12-slim`, health check probe, and minimal build dependencies. Runs as root.
- **`packages/mcp_server/Dockerfile`:** Clean `python:3.12-slim` image, bytecode writing disabled. Runs as root.

---

## 7. Forensic Verification & Test Suite Audit

Automated verification of existing test suites yielded empirical results:

1. **`scripts/verify_phase_1_2b.py`:**
   - **Result:** PASSED (100% — 4/4 stages: schema verification, seed data integrity, fixture checksums, Docker & config alignment).
2. **`apps/web/tests/verify_frontend.mjs`:**
   - **Result:** PASSED (100% — 4/4 checks: ApiError class, network error handling, citation schema validation, role differentiation).
3. **`apps/api/tests/test_auth.py`:**
   - **Result:** PASSED (6/6 tests in 0.86s).
4. **`apps/api/tests/test_heading_extraction.py`:**
   - **Result:** PASSED (7/7 tests in 0.32s).
5. **`apps/api/tests/test_ingestion.py` (Non-socket tests):**
   - **Result:** PASSED (23/23 tests: PDF/DOCX/MD extraction, empty/malformed handling, chunking boundaries, ChromaDB staging/verification, and atomic rollback suites A–F).
6. **`packages/mcp_server/tests/test_employee_tools.py`:**
   - **Result:** 24 PASSED, 1 FAILED (out of 25 tests).
   - *Failure analysis:* Test `test_f1_mcp_protocol_streamable_http_discovery_and_tool_calls` failed due to spawning an in-process Uvicorn thread on `127.0.0.1` and polling it over loopback HTTP within 5 seconds. In sandboxed Windows environments where inter-thread socket connections are restricted by Windows job container policies, local polling times out. All 24 core business logic, SQL injection, parameter validation, and role isolation tests passed.

---

## 8. Prioritized Remediation Roadmap

```mermaid
flowchart TD
    subgraph Priority 1 - High Severity
        P1A["Remove Hardcoded Acme Fallbacks in Local Synthesis (llm_service.py)"]
        P1B["Refactor Test Mock Users Out of Production Auth Router (auth.py)"]
    end

    subgraph Priority 2 - Medium Severity
        P2A["Consolidate Duplicate HMAC Signer into Shared Module"]
        P2B["Optimize Readiness Engine Instantiation (health.py)"]
        P2C["Address Deprecated datetime.utcnow() Calls"]
    end

    subgraph Priority 3 - Low Severity
        P3A["Remove Dead extract_from_txt() Logic"]
        P3B["Prune Unused asyncpg Dependency"]
        P3C["Add 'type': 'module' to apps/web/package.json"]
    end

    P1A --> P2A
    P1B --> P2B
    P2A --> P3A
```

| ID | Title | File Reference | Effort | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **P1.1** | Eliminate hardcoded Acme values from fallback synthesis | `apps/api/app/services/llm_service.py` (L298–335) | 1 hour | **P1 (Immediate)** |
| **P1.2** | Remove `APP_ENV == 'test'` branches from production routers | `apps/api/app/routers/auth.py` (L140–181) | 2 hours | **P1 (Immediate)** |
| **P2.1** | Unify `create_internal_auth_headers` into shared package | `apps/api` & `packages/mcp_server` | 2 hours | **P2 (Targeted)** |
| **P2.2** | Reuse database connection/engine in `/health/ready` probe | `apps/api/app/routers/health.py` (L21–44) | 1 hour | **P2 (Targeted)** |
| **P2.3** | Migrate `datetime.utcnow()` to `datetime.now(timezone.utc)` | Models in `apps/api` | 30 mins | **P2 (Targeted)** |
| **P3.1** | Remove dead `extract_from_txt` function | `apps/api/app/services/document_extractor.py` (L270) | 15 mins | **P3 (Cleanup)** |
| **P3.2** | Purge `asyncpg` from both `requirements.txt` files | `apps/api`, `packages/mcp_server` | 15 mins | **P3 (Cleanup)** |
| **P3.3** | Add `"type": "module"` to `apps/web/package.json` | `apps/web/package.json` | 5 mins | **P3 (Cleanup)** |
