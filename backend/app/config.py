from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ClipSave API"
    app_version: str = "1.0.0"

    api_key: str = ""
    public_base_url: str = ""

    temp_dir: Path = Path("/tmp/clipsave")
    file_ttl_seconds: int = 600
    max_file_size_mb: int = 500
    request_timeout_seconds: int = 90

    ytdlp_cookies_file: str = ""
    rate_limit_per_minute: int = 30
    enable_web_ui: bool = True

    shortcut_version: str = "1.0.0"
    shortcut_icloud_url: str = ""


settings = Settings()
