from decimal import Decimal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    bot_token: str

    # Database
    database_url: str

    # App
    debug: bool = False
    log_level: str = "INFO"
    timezone: str = "UTC"

    # Budget thresholds
    budget_warn_threshold: Decimal = Decimal("0.8")
    budget_critical_threshold: Decimal = Decimal("1.0")

    # Export
    exports_dir: str = "exports"


settings = Settings()
