"""
Configuration management for MOYA for Research paper co-pilot.

Uses pydantic-settings for environment variable management.
"""

import sys
from pathlib import Path

from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict

CLI_LOG_FORMAT = "<level>{level: <8}</level> <level>{message}</level>"
FILE_LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss zz} {level: <8} | [{name}:{function}:{line}] - {message}"
)
FILE_LOG_NAME = "trace.jsonl"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "MOYA for Research - Paper Co-Pilot"
    DEBUG: bool = False

    # Paths (relative to current working directory)
    DATA_DIR: Path = Path("data")
    LOG_DIR: Path = Path("logs")
    DB_DIR: Path = Path("database")
    PAPERS_DIR: Path = Path("papers")

    # Database
    DATABASE_URL: str = ""

    # Ollama Configuration (local LLM via Docker)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = (
        "gemma3:1b"  # Lightweight model: gemma3:1b, llama3.2:3b, qwen3:4b
    )

    # LLM Settings
    LLM_TEMPERATURE: float = 0.0  # Deterministic for reproducibility
    LLM_MAX_TOKENS: int = 4000

    # MOYA Configuration
    MAX_TOOL_ITERATIONS: int = 5

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Ensure directories exist
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.DB_DIR.mkdir(parents=True, exist_ok=True)
        self.PAPERS_DIR.mkdir(parents=True, exist_ok=True)

        # Set database URL if not provided
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"sqlite:///{self.DB_DIR / 'research.db'}"

    def model_post_init(self, context):
        logger.remove()
        log_file_path = self.LOG_DIR / FILE_LOG_NAME
        config = {
            "handlers": [
                {"sink": sys.stdout, "format": CLI_LOG_FORMAT, "level": "DEBUG"},
                {
                    "sink": str(log_file_path),
                    "format": FILE_LOG_FORMAT,
                    "level": "DEBUG",
                    "serialize": True,
                },
            ]
        }
        logger.configure(**config)
        return super().model_post_init(context)


# Global settings instance
settings = Settings()
