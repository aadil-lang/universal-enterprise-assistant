# Universal Enterprise HR & IT Assistant — Pre-Deployment Audit

**Standard:** ESR-STD-v2.4  
**Date:** November 23, 2026  
**Repository:** `aadil-lang/universal-enterprise-assistant`  
**Target Topology:**
- **Frontend:** Vercel Hobby (Next.js 14 Web UI + Archie Voice Assistant)
- **Backend:** Render Free (FastAPI ASGI Orchestrator + Private FastMCP Server)
- **PostgreSQL Database:** Neon Free Serverless PostgreSQL 16
- **Vector Database:** Qdrant Cloud Free (384-dim Dense HNSW + Payload Filtering) / ChromaDB Local
- **LLM Engine:** Google Gemini Integration (`gemini-3.5-flash-lite` / `gemini-1.5-pro`)

---

## 1. Executive Summary & Audit Purpose

This audit evaluates the deployment feasibility of the **Universal Enterprise HR & IT Assistant** under free-tier cloud constraints. The application is an enterprise assistant combining:
1. Multimodal natural voice interaction (Archie with "Hey Archie" wake-phrase and Indian English TTS/STT).
2. LangGraph conversational orchestration with RAG grounding.
3. FastMCP tool execution with strict Human-in-the-Loop (HITL) transactional boundaries across leave, expenses, IT tickets, and asset queries.
4. Role-based access control (RBAC) separating employee self-service (Bob, Carol) from HR administration (Alice).

The primary objective is to transition from local Docker Compose infrastructure to cloud-hosted infrastructure **without** regressing functional behavior, violating security boundaries, losing data persistence, or breaking existing local developer workflows.

---

## 2. Current Architecture & Service Dependencies

```
+-----------------------------------------------------------------------------------+
|                              Local Docker Compose Stack                           |
+-----------------------------------------------------------------------------------+
| 1. web (Port 3000)        : Next.js 14 App Router, Web Speech API, Tailwind CSS   |
| 2. api (Port 8000)        : FastAPI, LangGraph Agent Workflow, Pydantic, Auth JWT |
| 3. mcp-server (Port 8001) : FastMCP, Psycopg2, Parameterized Tools, HMAC Auth     |
| 4. postgres (Port 5432)   : PostgreSQL 16 Alpine, 11 Relational Tables, Seed SQL  |
| 5. chromadb (Port 8000)   : ChromaDB Vector Store (company_policies collection)   |
+-----------------------------------------------------------------------------------+
```

### Runtime Dependency Matrix

| Service | Upstream Dependencies | Network Binding | Storage Requirement | Local Assumption |
|---|---|---|---|---|
| **`web`** | `api` (HTTP/REST) | `0.0.0.0:3000` | Stateless | `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| **`api`** | `postgres`, `chromadb`, `mcp-server`, Gemini API | `0.0.0.0:8000` | Ephemeral + Local docs (`data/uploads`) | Resolves Docker network aliases (`mcp-server:8001`, `chromadb:8000`, `postgres:5432`) |
| **`mcp-server`** | `postgres` | `0.0.0.0:8001` (Internal) | Stateless | Resolves `postgres:5432` |
| **`postgres`** | None | `127.0.0.1:5432` | Persistent Named Volume (`postgres_data`) | Uses local init scripts in `/docker-entrypoint-initdb.d` |
| **`chromadb`** | None | `expose 8000` | Persistent Named Volume (`chroma_data`) | Assumes persistent volume for HNSW index and SQLite index |

---

## 3. Deployment Blockers & Free-Tier Resource Constraints

### 3.1 Render Free Tier Constraints
1. **No Private Services on Free Plan:** Render Free only supports public Web Services and Static Sites. Private internal network services require a paid Starter plan ($7/mo per service).
   * **Resolution:** Co-locate the FastMCP server inside the same container as FastAPI via `scripts/start_render.py`. FastMCP binds strictly to `127.0.0.1:8001` (loopback only), ensuring it is unreachable from the internet and accessible only to the local FastAPI process over signed HMAC headers.
2. **Ephemeral Filesystem:** Render Free Web Services run in ephemeral containers that restart on idle timeout (15 minutes). Any data written to local disk (such as local ChromaDB storage or SQLite) is wiped upon spin-down.
   * **Resolution:** Relocate stateful storage to managed external cloud providers: Relational data to **Neon PostgreSQL** and Vector embeddings to **Qdrant Cloud Free**.
3. **RAM & CPU Allocations:** Render Free provides 512 MB RAM and 0.1 CPU core.
   * **Assessment:** Loading Heavy PyTorch SentenceTransformers inside 512MB RAM risks Out-Of-Memory (OOM) kills. 
   * **Optimization:** Utilize `chromadb.utils.embedding_functions.ONNXMiniLM_L6_V2` (pure ONNX Runtime), which consumes ~45 MB RAM vs ~400 MB for PyTorch.

### 3.2 ChromaDB Persistence & Cloud Availability Blocker
* **Issue:** ChromaDB does not provide a public free-tier hosted SaaS. Hosting ChromaDB on Render Free with ephemeral storage results in immediate data loss upon container hibernation.
* **Resolution:** Evaluated in detail in `artifacts/deployment/vector_database_decision.md`. We introduce a dual-backend vector store abstraction that retains local ChromaDB for development while enabling **Qdrant Cloud Free** (permanent 4GB persistent cluster) for cloud production.

### 3.3 Neon Serverless PostgreSQL Compatibility
* **SSL Requirement:** Neon requires SSL (`sslmode=require`).
* **Connection String:** Neon provides `postgresql://[user]:[password]@[host]/[dbname]?sslmode=require`.
* **Resolution:** Both `apps/api` (Psycopg3) and `packages/mcp_server` (Psycopg2) include `normalize_database_url` validators that automatically adapt Neon connection strings.

### 3.4 Vercel Frontend Constraints
* **Monorepo Root Directory:** The repository is structured as a monorepo (`apps/web`, `apps/api`, `packages/mcp_server`). Vercel must be explicitly configured with Root Directory set to `apps/web`.
* **CORS Origin Filtering:** The FastAPI backend must accept dynamic requests from `https://*.vercel.app` and specific custom domains. (Implemented via `CORS_ORIGINS` and regex in `apps/api/app/main.py`).

---

## 4. Required Environment Variables Matrix

| Variable | Target Service | Purpose | Sensitivity | Default / Example |
|---|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Vercel (`apps/web`) | Target backend REST endpoint | Public | `https://acme-api.onrender.com` |
| `DATABASE_URL` | Render (`api` & `mcp`) | Connection string to Neon PostgreSQL | Secret | `postgresql://acme_app:***@ep-***.neon.tech/acme_assistant?sslmode=require` |
| `INTERNAL_MCP_SECRET` | Render (`api` & `mcp`) | HMAC-SHA256 signing secret for MCP requests | Secret | `64-character random hex string` |
| `JWT_SECRET_KEY` | Render (`api`) | HS256 secret for employee JWT tokens | Secret | `64-character random hex string` |
| `LLM_PROVIDER` | Render (`api`) | LLM provider selection | Plaintext | `gemini` |
| `GEMINI_API_KEY` | Render (`api`) | Google Gemini API key | Secret | Server-side only |
| `GEMINI_MODEL` | Render (`api`) | Model identifier | Plaintext | `gemini-3.5-flash-lite` |
| `VECTOR_STORE_PROVIDER`| Render (`api`) | Vector store engine (`chroma` or `qdrant`) | Plaintext | `qdrant` (prod) / `chroma` (local) |
| `QDRANT_URL` | Render (`api`) | Qdrant Cloud cluster endpoint | Secret | `https://***.gcp.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | Render (`api`) | Qdrant Cloud API key | Secret | Server-side only |
| `CORS_ORIGINS` | Render (`api`) | Allowed origins for cross-domain calls | Plaintext | `http://localhost:3000,https://*.vercel.app` |
| `DEMO_FISCAL_YEAR` | Render (`api` & `mcp`) | Fiscal year baseline for leave | Plaintext | `2026` |
| `APP_ENV` | Render (`api`) | Runtime environment tag | Plaintext | `production` |

---

## 5. Migration Risks & Mitigation Strategies

| Risk | Impact | Likelihood | Mitigation Strategy |
|---|---|---|---|
| Cold start timeout on Render Free | Request latency or initial 504 on cold start | High (after 15 min idle) | Implement lightweight `/health/live` check; configure frontend API retry with exponential backoff. |
| In-memory process race condition during concurrent transactions | State inconsistency | Low (demo load) | PostgreSQL row-level locks (`SELECT ... FOR UPDATE`) in `transaction_manager.py` enforce atomic state transitions across any number of server instances. |
| Local developer workflow disruption | Developer cannot test locally | Low | All cloud adapters (`Qdrant`, `Neon`) are implemented behind fallback environment switches. `docker-compose.yml` remains untouched. |
| Browser Speech Recognition HTTPS failure | Archie microphone refusal | Medium | Vercel provides automatic valid SSL/TLS certificates on all deployments, satisfying browser Web Speech API HTTPS security requirements. |

---

## 6. Recommended Cloud Deployment Topology

```
+--------------------------------------------------------------------+
|                         CLIENT BROWSER                             |
|  - Authenticated Employee / HR Admin                               |
|  - Web Speech API (Microphone / Indian English Voice Archie)       |
+----------------------------------+---------------------------------+
                                   | HTTPS
                                   v
+--------------------------------------------------------------------+
|                         VERCEL HOBBY                               |
|  - Next.js 14 Web Application (apps/web)                           |
|  - Edge CDN Distribution & Static Asset Caching                    |
+----------------------------------+---------------------------------+
                                   | HTTPS / REST (CORS Validated)
                                   v
+--------------------------------------------------------------------+
|                         RENDER FREE (Web Service)                  |
|  Container: Dockerfile.render                                      |
|                                                                    |
|  +---------------------------------------------------------------+ |
|  | FastAPI Gateway (0.0.0.0:$PORT)                               | |
|  | - Auth / JWT Validation                                       | |
|  | - LangGraph Conversational Workflow                           | |
|  | - Policy Retriever & Guardrails                               | |
|  | - Transaction Intent Handler                                  | |
|  +-------------------------------+-------------------------------+ |
|                                  | Internal Loopback (127.0.0.1:8001)
|                                  | Signed HMAC-SHA256 Headers     |
|                                  v                                 |
|  +---------------------------------------------------------------+ |
|  | FastMCP Private Tool Server (127.0.0.1:8001)                  | |
|  | - Strictly loopback bound                                      | |
|  | - get_employee_profile, get_leave_balances                     | |
|  | - apply_leave, cancel_leave, submit_it_ticket, etc.            | |
|  +-------------------------------+-------------------------------+ |
+-------------+--------------------+----------------+----------------+
              |                                     |
              | SSL (TLS 1.3)                       | HTTPS (Port 6333)
              v                                     v
+-----------------------------+       +------------------------------+
|        NEON FREE            |       |      QDRANT CLOUD FREE       |
| - Serverless PostgreSQL 16  |       | - 4GB Persistent Vector DB   |
| - 11 Relational Tables      |       | - 384-dim Dense HNSW Index   |
| - Seed Data & Audit Logs    |       | - Cosine Similarity Metric   |
+-----------------------------+       +------------------------------+
```
