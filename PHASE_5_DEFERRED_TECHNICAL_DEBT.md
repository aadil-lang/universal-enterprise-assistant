# Phase 5 Deferred Technical Debt Register

**Project:** Universal Enterprise HR & IT Assistant — Acme Corporation  
**Repository:** `aadil-lang/universal-enterprise-assistant`  
**Workspace:** `C:\Users\HP\OneDrive\Documents\HR-IT Helpdesk`  
**Standard:** ESR-STD-v2.4  
**Date:** November 20, 2026  
**Status:** Documented & Approved for Post-Phase 5 Milestone  

---

## 1. Overview

In accordance with the **Phase 5 Controlled Implementation Scope**, remediations were strictly focused on high-value correctness, application security, and AI safety fixes. Architectural modifications requiring new infrastructure components, multi-tenant database redesigns, or client-breaking contract changes were intentionally deferred.

This document formally captures all approved deferred technical debt items, their current operational mitigations, residual risk, and triggers for future resolution.

---

## 2. Deferred Technical Debt Registry

### DEBT-01: Multi-Tenant Architecture & Database Isolation
- **Classification:** Architectural Scope Boundary
- **Description:** The system is currently designed and deployed as a single-enterprise assistant for Acme Corporation. Database schemas (`app_users`, `employees`, `documents`) and ChromaDB vector collections (`acme_policy_documents`) do not carry a `tenant_id` column or tenant-level partitioning.
- **Current Operational Mitigation:** Evaluated and verified under employee-level RBAC (`employee` vs `hr_admin`) and employee data isolation. Cross-employee data access is strictly blocked at the MCP tool and SQL query layer.
- **Residual Risk:** Low for Acme Corporation internal deployment; High if commercialized as a multi-tenant SaaS product.
- **Resolution Trigger:** Product roadmap decision to onboard multiple independent tenant companies onto a shared infrastructure cluster.

---

### DEBT-02: Distributed Redis Token Revocation & Blacklisting
- **Classification:** Infrastructure Complexity
- **Description:** JWT access tokens are validated statelessly using HMAC-SHA256 signatures with live PostgreSQL user active status checks (`is_active == True`). Immediate revocation of individual active tokens before their 60-minute expiration is not supported via a distributed Redis blacklist.
- **Current Operational Mitigation:** `get_current_active_user()` performs a live database lookup on every authenticated request. Setting `is_active = False` in the database immediately revokes account access on the very next API call. JWT expiration is limited to 60 minutes.
- **Residual Risk:** Low. Immediate account deactivation is fully operational. Only the specific scenario of invalidating a single active session token while keeping the user account active requires token expiration wait.
- **Resolution Trigger:** Introduction of concurrent multi-device session management or compliance requirements requiring instantaneous session termination.

---

### DEBT-03: HTTP-Only Secure Cookie Storage for JWT Tokens
- **Classification:** Client-Side Storage & Contract
- **Description:** The Next.js frontend currently stores JWT session tokens in browser `localStorage` and transmits them via the standard `Authorization: Bearer <token>` HTTP header.
- **Current Operational Mitigation & Residual Risk:** Content Security Policy and client-side sanitization reduce the attack surface for XSS, but do not eliminate the residual risk of token exfiltration from localStorage in the event of an arbitrary script execution vulnerability or malicious third-party dependency. Storing JWTs in localStorage remains a known trade-off until HTTP-only SameSite cookies are implemented behind a unified reverse proxy.
- **Resolution Trigger:** Production domain deployment with unified reverse proxy (e.g. Nginx/Cloudflare) enabling SameSite=Strict HTTP-only cookie forwarding.

---

### DEBT-04: Upstream API Gateway Rate Limiting
- **Classification:** Ingress Infrastructure
- **Description:** Application-level in-memory rate limiting was excluded to avoid adding Redis or in-process memory leaks across multiple Uvicorn worker processes.
- **Current Operational Mitigation & Residual Risk:** Dummy bcrypt hash verification normalizes execution timing on nonexistent user lookups to mitigate username enumeration via timing analysis. It does NOT provide request-rate limiting or DDoS defense. In fact, executing cost-12 bcrypt checks on every invalid login increases server CPU utilization, making ingress-level rate limiting (e.g. 5 req/s via Nginx/Cloudflare) an essential production requirement.
- **Resolution Trigger:** Deployment of production ingress controller (e.g. Traefik, AWS ALB, Nginx, Cloudflare) with rate limiting rules (e.g. 5 requests/sec per IP on `/api/v1/auth/login`).

---

### DEBT-05: Monorepo Packaging & Shared Python Libraries
- **Classification:** Maintainability & Build Tooling
- **Description:** `apps/api` and `packages/mcp_server` maintain separate `requirements.txt` and duplicated model definitions (e.g. employee models, HMAC verification logic) rather than importing a shared internal wheel or Poetry package.
- **Current Operational Mitigation:** Clear directory boundaries and isolated Docker containers prevent cross-contamination. Both services share identical central configuration keys (`DEMO_FISCAL_YEAR`, `INTERNAL_MCP_SECRET`).
- **Residual Risk:** Low. Minor code duplication across service boundaries.
- **Resolution Trigger:** Introduction of a third backend service or migration to a unified Python monorepo build tool (e.g. uv, Poetry workspaces, or Pants).

---

### DEBT-06: Unified Package Lockfiles
- **Classification:** Deployment Reproducibility
- **Description:** Python dependencies are pinned with version specifiers in `requirements.txt`, but do not utilize fully frozen SHA-256 hash lockfiles (e.g. `pip-compile` / `uv.lock`). Next.js uses `package-lock.json`.
- **Current Operational Mitigation & Residual Risk:** Dependencies in requirements.txt specify version bounds, and Dockerfiles use python:3.12-slim. However, sub-dependencies are not locked with cryptographic SHA-256 hashes (e.g. via pip-compile --generate-hashes or uv.lock). Minor upstream package drift remains possible across clean image rebuilds until fully deterministic lockfiles are adopted.
- **Resolution Trigger:** Enterprise CI/CD pipeline automation requiring deterministic binary artifact hashing.

---

## 3. Summary & Acceptance

All six items above were evaluated during Phase 5 planning and explicitly deemed non-blocking for pre-release acceptance. Their deferral preserves architecture simplicity, avoids premature infrastructure sprawl, and maintains zero external dependency growth.
