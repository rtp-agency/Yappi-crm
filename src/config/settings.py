"""
Application settings loaded from .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Union
from functools import lru_cache


class Settings(BaseSettings):
    """Main application settings."""

    # Telegram Bot
    BOT_TOKEN: str = Field(..., description="Telegram Bot API token")
    ADMIN_IDS: List[int] = Field(default_factory=list, description="List of admin Telegram IDs (whitelist)")

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, int, List[int]]) -> List[int]:
        """Parse ADMIN_IDS from string, int, or list."""
        if isinstance(v, list):
            return v
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return []

    # Google Sheets
    SPREADSHEET_ID: str = Field(..., description="Google Spreadsheet ID")
    CREDENTIALS_FILE: str = Field(default="credentials.json", description="Path to Google API credentials")

    # Cache
    CACHE_DB_PATH: str = Field(default="data/cache.db", description="Path to SQLite cache database")
    CACHE_SYNC_INTERVAL: int = Field(default=300, description="Cache sync interval in seconds (default: 5 min)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def admin_ids_set(self) -> set[int]:
        """Return admin IDs as a set for fast lookup."""
        return set(self.ADMIN_IDS)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
