# Universal Enterprise HR & IT Assistant — Environment Variables Checklist

**Standard:** ESR-STD-v2.4  
**Date:** November 23, 2026  
**Document ID:** `SEC-ENV-CONFIG-001`  
**Security Classification:** RESTRICTED — Template Only (Zero Secrets Stored)

---

## 1. Important Security Principles
> [!IMPORTANT]
> - **Never commit secrets** (passwords, JWT secrets, HMAC keys, API tokens) into Git or source repositories.
> - **Never pass secrets to client-side frontend code**; only variables prefixed with `NEXT_PUBLIC_` are bundled into the browser application, and these must remain strictly public (e.g. backend host URL).
> - All production secrets must be generated using cryptographically secure pseudorandom generators (e.g. `openssl rand -hex 32`).

---

## 2. Vercel Frontend Environment Variables (`apps/web`)

| Variable Name | Required | Default / Format | Description & Guidance |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Yes** | `https://<render-service-name>.onrender.com` | The public base URL of the deployed FastAPI backend. Must NOT include a trailing slash. All browser HTTP requests (login, chat, document management) are dispatched to this endpoint. |

---

## 3. Render Backend Environment Variables (`apps/api` & `packages/mcp_server`)

### 3.1 Core Application & Runtime Settings
| Variable Name | Required | Example / Recommended Setting | Description & Guidance |
|---|---|---|---|
| `APP_ENV` | **Yes** | `production` | Runtime mode. Must be set to `production` in cloud environments to activate production secret guards. |
| `PORT` | Auto | `10000` | Injected dynamically by Render. The entrypoint script binds FastAPI to `0.0.0.0:$PORT`. |
| `DEMO_FISCAL_YEAR` | **Yes** | `2026` | Central demonstration fiscal year (single source of truth for all leave accrual and balance calculations). |
| `CORS_ORIGINS` | **Yes** | `http://localhost:3000,https://*.vercel.app` | Comma-separated list of allowed origins. Supports wildcard regex matching for Vercel preview and production domains. |

### 3.2 Security Tokens & Cryptographic Secrets
| Variable Name | Required | Recommended Generation Command | Description & Guidance |
|---|---|---|---|
| `JWT_SECRET_KEY` | **Yes** | `openssl rand -hex 32` | Cryptographic secret for signing and verifying employee authentication JWTs. Must be $\ge 32$ characters. |
| `JWT_ALGORITHM` | No | `HS256` | Cryptographic algorithm used for JWT token signing. |
| `JWT_EXPIRATION_MINUTES` | No | `60` | Token lifetime before re-authentication is required. |
| `INTERNAL_MCP_SECRET` | **Yes** | `openssl rand -hex 32` | Shared secret between FastAPI and FastMCP for signing internal tool invocation headers with HMAC-SHA256. |

### 3.3 Relational Database (Neon Serverless PostgreSQL 16)
| Variable Name | Required | Format Specification | Description & Guidance |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | `postgresql://[user]:[password]@[host]/[dbname]?sslmode=require` | The full connection URI provided by Neon. The application automatically normalizes this string for Psycopg3 (`postgresql+psycopg://`) and Psycopg2 (`postgresql+psycopg2://`). |

### 3.4 Vector Database Settings (Qdrant Cloud / ChromaDB)
| Variable Name | Required | Default / Example | Description & Guidance |
|---|---|---|---|
| `VECTOR_STORE_PROVIDER` | **Yes** | `qdrant` (in cloud) / `chroma` (local) | Selects the vector store backend implementation. |
| `QDRANT_URL` | Conditional | `https://[cluster-id].[region].cloud.qdrant.io:6333` | Required if `VECTOR_STORE_PROVIDER=qdrant`. The HTTPS cluster endpoint from Qdrant Cloud. |
| `QDRANT_API_KEY` | Conditional | Cryptographic API key from Qdrant console | Required if `VECTOR_STORE_PROVIDER=qdrant`. Used to authenticate vector insert and query operations. |
| `CHROMA_HOST` | Local only | `localhost` or `chromadb` | Fallback hostname for local ChromaDB instance. |
| `CHROMA_PORT` | Local only | `8000` | Fallback port for local ChromaDB instance. |
| `CHROMA_COLLECTION` | No | `company_policies` | Collection / cluster index name for policy vectors. |
| `EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | Dense embedding model (384 dimensions). |

### 3.5 LLM Gateway (Google Gemini Integration)
| Variable Name | Required | Example Setting | Description & Guidance |
|---|---|---|---|
| `LLM_PROVIDER` | **Yes** | `gemini` | Configures the central reasoning and intent engine. |
| `GEMINI_API_KEY` | **Yes** | Server-side API key from Google AI Studio | Authorizes conversational orchestration, policy grounding, and natural conversational responses. |
| `GEMINI_MODEL` | No | `gemini-3.5-flash-lite` | Target model identifier. High speed, low latency, and cost-efficient. |
| `GEMINI_BASE_URL` | No | `https://generativelanguage.googleapis.com/v1beta/openai/` | OpenAI-compatible endpoint URL for Google Gemini. |

### 3.6 Internal FastMCP Server Configuration
| Variable Name | Required | Default | Description & Guidance |
|---|---|---|---|
| `MCP_HOST` | No | `127.0.0.1` | Local loopback binding. Must strictly remain `127.0.0.1` so tool execution is never accessible externally. |
| `MCP_PORT` | No | `8001` | Local port dedicated to FastMCP service within the container. |
