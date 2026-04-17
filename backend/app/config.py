"""
Application configuration loaded from environment variables.
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nivesh_db"
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    ENCRYPTION_KEY: str = "change_me_to_a_base64_encoded_32_byte_key"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
