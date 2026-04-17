"""
Application configuration loaded from environment variables.
"""
from pydantic_settings import BaseSettings
from pydantic import model_validator


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nivesh_db"

    # ── Supabase ──────────────────────────────────────────────────────────
    SUPABASE_URL: str = ""

    # Supports both SUPABASE_SERVICE_KEY (original) and SUPABASE_KEY (anon/publishable)
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_KEY: str = ""          # anon / publishable key from Supabase dashboard

    # ── Encryption ────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str = "change_me_to_a_base64_encoded_32_byte_key"

    @model_validator(mode="after")
    def _resolve_supabase_key(self):
        """
        If SUPABASE_SERVICE_KEY is not set but SUPABASE_KEY is,
        fall back to using SUPABASE_KEY for the service key.
        This lets .env files use either variable name.
        """
        if not self.SUPABASE_SERVICE_KEY and self.SUPABASE_KEY:
            self.SUPABASE_SERVICE_KEY = self.SUPABASE_KEY
        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",          # silently ignore unknown env vars
    }


settings = Settings()
