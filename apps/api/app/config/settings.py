import os
from functools import lru_cache
from typing import Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings for Acme HR & IT Assistant API.
    All variables are loaded from environment variables or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application & Central Demonstration Fiscal Year (Single Source of Truth)
    APP_ENV: str = Field(default="development", description="Runtime environment")
    DEMO_FISCAL_YEAR: int = Field(default=2026, description="Authoritative demonstration fiscal year")

    # Security & Tokens
    JWT_SECRET_KEY: str = Field(default="dev_insecure_jwt_secret_key_min_32_chars_12345")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_MINUTES: int = Field(default=60)
    INTERNAL_MCP_SECRET: str = Field(default="dev_insecure_internal_mcp_hmac_secret_min_32")

    # CORS Configuration for Frontend Deployments (e.g. Vercel)
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,https://*.vercel.app",
        description="Comma-separated allowed CORS origins or wildcards"
    )

    # PostgreSQL Database (API uses Psycopg 3 via postgresql+psycopg://)
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://acme_app:acme_secure_dev_pw_2026@localhost:5432/acme_assistant"
    )
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="acme_assistant")
    POSTGRES_USER: str = Field(default="acme_app")
    POSTGRES_PASSWORD: str = Field(default="acme_secure_dev_pw_2026")

    # Vector Store & Ingestion Pipeline (ChromaDB / Qdrant)
    VECTOR_STORE_PROVIDER: str = Field(default="chroma", description="Vector store provider: 'chroma' or 'qdrant'")
    CHROMA_HOST: str = Field(default="localhost")
    CHROMA_PORT: int = Field(default=8000)
    CHROMA_COLLECTION: str = Field(default="company_policies")
    QDRANT_URL: Optional[str] = Field(default=None, description="Qdrant Cloud cluster endpoint")
    QDRANT_API_KEY: Optional[str] = Field(default=None, description="Qdrant Cloud API Key")
    QDRANT_COLLECTION: str = Field(default="company_policies", description="Target Qdrant collection name")
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    DOCUMENTS_DIR: str = Field(default="data/uploads", description="Base directory for uploaded enterprise policy documents")
    CHUNK_SIZE: int = Field(default=800, description="Target character length per text chunk")
    CHUNK_OVERLAP: int = Field(default=150, description="Character overlap between consecutive chunks")

    # API Gateway
    API_APP_NAME: str = Field(default="Acme HR & IT Assistant API")
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_RELOAD: bool = Field(default=True)

    # Internal MCP Server
    MCP_HOST: str = Field(default="localhost")
    MCP_PORT: int = Field(default=8001)

    # LLM Provider Configuration
    LLM_PROVIDER: str = Field(default="mock", description="LLM provider: 'gemini', 'openai', 'custom', or 'mock'")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    GEMINI_BASE_URL: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai/",
        description="Gemini OpenAI-compatible endpoint base URL"
    )
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash-lite", description="Gemini model identifier")

    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    OPENAI_API_BASE: str = Field(default="https://api.openai.com/v1", description="OpenAI base URL")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI model identifier")

    @property
    def mcp_base_url(self) -> str:
        return f"http://{self.MCP_HOST}:{self.MCP_PORT}"

    @model_validator(mode="before")
    @classmethod
    def normalize_database_url(cls, data: dict) -> dict:
        if isinstance(data, dict):
            db_url = data.get("DATABASE_URL")
            if db_url and isinstance(db_url, str):
                if db_url.startswith("postgres://"):
                    data["DATABASE_URL"] = db_url.replace("postgres://", "postgresql+psycopg://", 1)
                elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg://"):
                    data["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

                # Sync POSTGRES_PASSWORD from DATABASE_URL if available
                from urllib.parse import urlparse
                try:
                    clean_for_parse = db_url.replace("postgresql+psycopg://", "http://").replace("postgres://", "http://").replace("postgresql://", "http://")
                    parsed = urlparse(clean_for_parse)
                    if parsed.password and data.get("POSTGRES_PASSWORD") in (None, "acme_secure_dev_pw_2026"):
                        data["POSTGRES_PASSWORD"] = parsed.password
                except Exception:
                    pass
        return data

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """
        Ensures non-development environments cannot start with default insecure secrets,
        and prevents accidental test mode configuration in production environments.
        """
        if self.LLM_PROVIDER == "gemini" and not self.GEMINI_API_KEY:
            # When gemini provider is explicitly enabled, API key must be present
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER is configured as 'gemini'.")

        # Safeguard: prevent test mode from being used in production deployments
        if self.APP_ENV == "test":
            env_indicator = (os.getenv("ENVIRONMENT") or os.getenv("NODE_ENV") or os.getenv("STAGE") or "").lower()
            if env_indicator in ("production", "prod", "staging", "live"):
                raise ValueError("APP_ENV='test' cannot be used in a production or staging deployment.")

        if self.APP_ENV not in ("development", "test"):
            known_insecure_fragments = ("dev_insecure", "changeme", "replace_me", "example", "placeholder")
            if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY) < 32 or any(frag in self.JWT_SECRET_KEY.lower() for frag in known_insecure_fragments):
                raise ValueError("Insecure, default, or short JWT_SECRET_KEY is forbidden in non-development environments.")
            if not self.INTERNAL_MCP_SECRET or len(self.INTERNAL_MCP_SECRET) < 32 or any(frag in self.INTERNAL_MCP_SECRET.lower() for frag in known_insecure_fragments):
                raise ValueError("Insecure, default, or short INTERNAL_MCP_SECRET is forbidden in non-development environments.")

            has_prod_db = self.DATABASE_URL and ("acme_secure_dev_pw" not in self.DATABASE_URL) and ("localhost" not in self.DATABASE_URL)
            if not has_prod_db:
                if not self.POSTGRES_PASSWORD or "acme_secure_dev_pw" in self.POSTGRES_PASSWORD or self.POSTGRES_PASSWORD in ("postgres", "password", "root", "admin"):
                    raise ValueError("Default development POSTGRES_PASSWORD is forbidden in non-development environments.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Compatibility alias for shared MCP modules in demo mode
get_mcp_settings = get_settings
