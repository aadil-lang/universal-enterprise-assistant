from typing import Dict
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from app.config.settings import get_settings

router = APIRouter(prefix="/health", tags=["Health"])


class LivenessResponse(BaseModel):
    status: str
    app: str
    version: str
    demo_fiscal_year: int


class ReadinessResponse(BaseModel):
    status: str
    dependencies: Dict[str, str]


def check_postgres(db_url: str, timeout_seconds: float = 2.0) -> tuple[bool, str]:
    """
    Checks actual PostgreSQL reachability with bounded connection timeout.
    Disposes of the temporary SQLAlchemy engine cleanly to prevent connection leaks.
    """
    engine = None
    try:
        from sqlalchemy import create_engine, text
        # Set bounded connect timeout for psycopg
        connect_args = {"connect_timeout": int(timeout_seconds)}
        engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=False,
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as e:
        return False, f"disconnected ({type(e).__name__})"
    finally:
        if engine is not None:
            engine.dispose()


def check_chromadb(host: str, port: int, timeout_seconds: float = 2.0) -> tuple[bool, str]:
    """
    Checks actual ChromaDB vector store reachability with bounded HTTP timeout.
    Supports both Chroma v2 (/api/v2/heartbeat) and legacy v1 (/api/v1/heartbeat).
    """
    try:
        import httpx
        for endpoint in ["/api/v2/heartbeat", "/api/v1/heartbeat"]:
            try:
                url = f"http://{host}:{port}{endpoint}"
                with httpx.Client(timeout=timeout_seconds) as client:
                    resp = client.get(url)
                    if resp.status_code == 200:
                        return True, "connected"
            except Exception:
                continue
        return False, "unhealthy"
    except Exception as e:
        return False, f"disconnected ({type(e).__name__})"


@router.get("/live", response_model=LivenessResponse, status_code=status.HTTP_200_OK)
def liveness_check():
    """
    Process liveness probe.
    Must never depend on downstream databases or vector store dependencies.
    """
    settings = get_settings()
    return LivenessResponse(
        status="ok",
        app=settings.API_APP_NAME,
        version="0.1.0",
        demo_fiscal_year=settings.DEMO_FISCAL_YEAR,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "All dependencies reachable"},
        503: {"description": "One or more dependencies unreachable"},
    },
)
def readiness_check(response: Response):
    """
    Honest dependency readiness probe.
    Verifies actual connectivity to PostgreSQL and ChromaDB before returning 200 OK.
    Returns HTTP 503 Service Unavailable if any required dependency fails.
    """
    settings = get_settings()

    # Verify actual PostgreSQL connectivity
    db_ok, db_msg = check_postgres(settings.DATABASE_URL, timeout_seconds=2.0)

    # Verify actual ChromaDB connectivity
    chroma_ok, chroma_msg = check_chromadb(settings.CHROMA_HOST, settings.CHROMA_PORT, timeout_seconds=2.0)

    all_ready = db_ok and chroma_ok
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            dependencies={
                "database": db_msg,
                "chromadb": chroma_msg,
            },
        )

    return ReadinessResponse(
        status="ready",
        dependencies={
            "database": db_msg,
            "chromadb": chroma_msg,
        },
    )
