import os
from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    """
    Configuration settings for the genuine MCP Server.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_ENV: str = Field(default="development")
    DEMO_FISCAL_YEAR: int = Field(default=2026, description="Central demonstration fiscal year")
    MCP_SERVICE_NAME: str = Field(default="acme-mcp-server")

    # Service Transport
    MCP_HOST: str = Field(default="0.0.0.0")
    MCP_PORT: int = Field(default=8001)

    # Internal Security Secret
    INTERNAL_MCP_SECRET: str = Field(default="dev_insecure_internal_mcp_hmac_secret_min_32")

    # PostgreSQL Connection (MCP service uses Psycopg2 via postgresql+psycopg2://)
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://acme_app:acme_secure_dev_pw_2026@localhost:5432/acme_assistant"
    )
    POSTGRES_HOST: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str = Field(default="acme_assistant")
    POSTGRES_USER: str = Field(default="acme_app")
    POSTGRES_PASSWORD: str = Field(default="acme_secure_dev_pw_2026")

    @model_validator(mode="before")
    @classmethod
    def normalize_database_url(cls, data: dict) -> dict:
        if isinstance(data, dict):
            db_url = data.get("DATABASE_URL")
            if db_url and isinstance(db_url, str):
                if db_url.startswith("postgres://"):
                    data["DATABASE_URL"] = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
                elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg2://"):
                    data["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return data

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "MCPSettings":
        """
        Ensures non-development environments cannot start with default insecure secrets,
        and prevents accidental test mode configuration in production environments.
        """
        # Safeguard: prevent test mode from being used in production deployments
        if self.APP_ENV == "test":
            env_indicator = (os.getenv("ENVIRONMENT") or os.getenv("NODE_ENV") or os.getenv("STAGE") or "").lower()
            if env_indicator in ("production", "prod", "staging", "live"):
                raise ValueError("APP_ENV='test' cannot be used in a production or staging deployment.")

        if self.APP_ENV not in ("development", "test"):
            known_insecure_fragments = ("dev_insecure", "changeme", "replace_me", "example", "placeholder")
            if not self.INTERNAL_MCP_SECRET or len(self.INTERNAL_MCP_SECRET) < 32 or any(frag in self.INTERNAL_MCP_SECRET.lower() for frag in known_insecure_fragments):
                raise ValueError("Insecure, default, or short INTERNAL_MCP_SECRET is forbidden in non-development environments.")
            if not self.POSTGRES_PASSWORD or "acme_secure_dev_pw" in self.POSTGRES_PASSWORD or self.POSTGRES_PASSWORD in ("postgres", "password", "root", "admin"):
                raise ValueError("Default development POSTGRES_PASSWORD is forbidden in non-development environments.")
        return self


@lru_cache
def get_mcp_settings() -> MCPSettings:
    return MCPSettings()
