# Universal Enterprise HR & IT Assistant — Cloud Deployment Runbook

**Standard:** ESR-STD-v2.4  
**Date:** November 23, 2026  
**Document ID:** `OPS-RUNBOOK-DEPLOY-001`  
**Execution Time:** ~20–30 Minutes  
**Target Total Cost:** **$0.00 / month (100% Free Tiers)**

---

## 1. Required Accounts & Credentials Checklist

Before starting, confirm access to the following 5 free cloud providers:
- [ ] **GitHub Account:** Access to repository `aadil-lang/universal-enterprise-assistant`.
- [ ] **Neon Account:** [neon.tech](https://neon.tech) (Free tier: 0.5 GB Serverless Postgres 16).
- [ ] **Qdrant Cloud Account:** [cloud.qdrant.io](https://cloud.qdrant.io) (Free tier: 1 permanent cluster, 4GB storage).
- [ ] **Google AI Studio Account:** [aistudio.google.com](https://aistudio.google.com) (Free tier Gemini API key).
- [ ] **Render Account:** [render.com](https://render.com) (Free tier: 1 web service, 512MB RAM).
- [ ] **Vercel Account:** [vercel.com](https://vercel.com) (Free Hobby tier: unlimited Next.js edge deploys).

---

## 2. Step 1: Provision & Migrate Neon PostgreSQL

### 2.1 Create Database in Neon Console
1. Log in to [console.neon.tech](https://console.neon.tech).
2. Click **Create Project**.
   * **Project Name:** `acme-assistant-prod`
   * **Postgres Version:** `16`
   * **Cloud Region:** Select closest region (e.g., US East / AWS Oregon).
3. On the project dashboard, copy the connection string under **Connection Details**:
   ```
   postgresql://[user]:[password]@[host].neon.tech/acme_assistant?sslmode=require
   ```

### 2.2 Initialize Schema & Seed Data
From your local project workspace, run the automated migration tool:
```bash
python scripts/init_remote_db.py --url "<PASTE_NEON_CONNECTION_STRING>"
```
**Verification Check:**
The script connects over SSL, executes `001_schema.sql`, `002_seed.sql`, and `003_transactional_schema.sql`, and verifies the 11 tables and demo users (Alice E101, Bob E102, Carol E103).

---

## 3. Step 2: Provision Qdrant Cloud Vector Database

1. Log in to [cloud.qdrant.io](https://cloud.qdrant.io).
2. Click **Create Cluster**.
   * **Cloud Provider:** Google Cloud or AWS.
   * **Tier:** Select **Free Tier (1 GB RAM, 0.5 vCPU, 4GB Disk)**.
   * **Cluster Name:** `acme-policies-cluster`.
3. Under **Cluster Details**, copy your cluster HTTPS endpoint:
   * Example: `https://[cluster-id].gcp.cloud.qdrant.io:6333`
4. Under **Data Access Control / API Keys**, click **Create API Key** and copy the secret key.

---

## 4. Step 3: Deploy Backend on Render Free

1. Log in to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Connect your repository: `aadil-lang/universal-enterprise-assistant`.
4. Configure the service parameters:
   * **Name:** `acme-assistant-api`
   * **Region:** Same general geographic region as Neon and Qdrant.
   * **Branch:** `main`
   * **Runtime:** **Docker**
   * **Dockerfile Path:** `Dockerfile.render`
   * **Instance Type:** **Free (512 MB RAM / 0.1 CPU)**
5. Expand the **Environment Variables** section and configure:

| Environment Variable | Value | Notes |
|---|---|---|
| `APP_ENV` | `production` | Enables production security guards |
| `DEMO_FISCAL_YEAR` | `2026` | Central demonstration fiscal year |
| `DATABASE_URL` | `<Your Neon Connection URI>` | Includes `?sslmode=require` |
| `INTERNAL_MCP_SECRET` | *(Click 'Generate' or 64 hex characters)* | Shared secret for FastMCP HMAC |
| `JWT_SECRET_KEY` | *(Click 'Generate' or 64 hex characters)* | Secret for auth JWT tokens |
| `LLM_PROVIDER` | `gemini` | Gemini LLM gateway |
| `GEMINI_API_KEY` | `<Your Google AI Studio Gemini API Key>` | Server-side only |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | High speed, cost-effective |
| `VECTOR_STORE_PROVIDER` | `qdrant` | Cloud persistent vector store |
| `QDRANT_URL` | `<Your Qdrant Cluster HTTPS URL>` | Port 6333 |
| `QDRANT_API_KEY` | `<Your Qdrant API Key>` | Secure cloud token |
| `CORS_ORIGINS` | `http://localhost:3000,https://*.vercel.app` | Allows Vercel frontend |

6. Click **Deploy Web Service**.
7. Render will build the container from `Dockerfile.render`, start FastMCP on `127.0.0.1:8001`, and expose FastAPI on the public web port.
8. Once healthy, copy the assigned URL:
   * Example: `https://acme-assistant-api.onrender.com`
9. Verify health in browser or curl:
   ```bash
   curl https://acme-assistant-api.onrender.com/health/live
   # Expected response: {"status":"live","service":"acme-api"}
   ```

---

## 5. Step 4: Ingest Corporate Policies into Cloud Vector Store

To populate the cloud Qdrant cluster with the initial authoritative corporate policies (`Acme Leave Policy`, `Acme Remote Work Policy`, `Acme IT Equipment Policy`):
```bash
python scripts/seed_cloud_policies.py --api-url "https://acme-assistant-api.onrender.com"
```
This logs in as HR Admin Alice (E101) and indexes the markdown/PDF policy files into Qdrant Cloud.

---

## 6. Step 5: Deploy Frontend on Vercel Hobby

1. Log in to [vercel.com](https://vercel.com).
2. Click **Add New…** → **Project**.
3. Import **`aadil-lang/universal-enterprise-assistant`**.
4. Configure Project Settings:
   * **Framework Preset:** Next.js
   * **Root Directory:** Click **Edit** → select **`apps/web`** (Crucial).
5. Under **Environment Variables**, add:
   * **Key:** `NEXT_PUBLIC_API_URL`
   * **Value:** `https://acme-assistant-api.onrender.com` *(Your Render backend URL)*
6. Click **Deploy**.
7. Vercel builds and publishes the production Next.js frontend across global edge nodes with automated HTTPS.

---

## 7. Step 6: Live Smoke Test & Acceptance Verification

Once deployed, visit your Vercel URL in Chromium / Chrome:

1. **Test Authentication:**
   * Log in with employee ID `E102` (Bob Jones).
   * Confirm Bob's name, department (Engineering), and FY 2026 balance dashboard load.
2. **Test Archie Natural Voice:**
   * Click **Voice Mode**, grant microphone access.
   * Say: *"Hey Archie"* → Verify personalized voice greeting.
   * Ask: *"What is my remaining annual leave balance?"* → Verify spoken and text answer (8.0 days).
3. **Test Transactional Workflow & HITL:**
   * Say or type: *"I want to book 2 days annual leave from 2026-12-15 to 2026-12-16"*.
   * Verify Archie displays the **Confirmation Card**.
   * Click **Confirm** → Verify status changes to `confirmed` and pending balance updates.
4. **Test Peer Security Boundary:**
   * Ask: *"What is Carol's leave balance?"*
   * Verify Archie returns an access refusal (*"Employees are only authorized to access their own records"*).
5. **Test HR Admin Privileges:**
   * Sign out and log in with employee ID `E101` (Alice Smith).
   * Verify HR Admin controls and cross-employee record access are active.
