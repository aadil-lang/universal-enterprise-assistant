from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import get_settings
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router

settings = get_settings()

app = FastAPI(
    title="Acme HR & IT Assistant API",
    description="Backend orchestration gateway for Acme Corporation's HR and IT conversational assistant.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Security response headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    if request.url.path in ("/docs", "/redoc", "/openapi.json"):
        response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; frame-ancestors 'none'"
    else:
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"

    # Enforce HSTS only when HTTPS is actively used or terminated by reverse proxy
    is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    if is_https:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response

# CORS Middleware configuration
cors_origins_raw = getattr(settings, "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip() and "*" not in o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins else ["*"],
    allow_origin_regex=r"^https://.*\.vercel\.app$" if "vercel.app" in cors_origins_raw else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/", tags=["Root"])
def root_info():
    """Root info endpoint providing basic application metadata."""
    active_model = settings.GEMINI_MODEL if settings.LLM_PROVIDER == "gemini" else (settings.OPENAI_MODEL if settings.LLM_PROVIDER in ("openai", "custom") else "deterministic-mock")
    return {
        "service": "Acme HR & IT Assistant API",
        "status": "online",
        "demo_company": "Acme Corporation",
        "demo_fiscal_year": settings.DEMO_FISCAL_YEAR,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": active_model,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
    )
