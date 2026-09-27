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

    # Mini App / API
    jwt_secret: str = ""
    jwt_ttl_minutes: int = 60
    init_data_max_age_seconds: int = 3600
    webapp_url: str = ""
    cors_origins: str = ""  # comma-separated list
    api_port: int = 8000
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # Budget thresholds
    budget_warn_threshold: Decimal = Decimal("0.8")
    budget_critical_threshold: Decimal = Decimal("1.0")

    # Export
    exports_dir: str = "exports"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
