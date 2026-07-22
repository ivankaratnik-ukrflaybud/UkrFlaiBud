import json
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UKRFLYBUD Manager API"
    app_env: str = "local"
    app_locale: str = "uk-UA"
    app_timezone: str = "Europe/Kyiv"
    database_url: str = "postgresql+asyncpg://ukrflybud:change-me@postgres:5432/ukrflybud"
    cors_origins_raw: str = Field(
        default="http://localhost:8080,http://localhost:5173",
        validation_alias="CORS_ORIGINS",
    )
    log_level: str = "INFO"
    logging_config_path: str = "logging.yaml"
    auth_secret_key: str = "change-this-local-development-secret"
    auth_access_token_minutes: int = 15
    auth_refresh_token_days: int = 30
    auth_failed_login_limit: int = 5
    auth_lock_minutes: int = 15
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    bootstrap_admin_email: str | None = "admin@gmail.com"
    bootstrap_admin_name: str | None = "Administrator"
    bootstrap_admin_password: str | None = "ChangeMe12345"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins_raw")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        cls.parse_cors_origins(value)
        return value

    @property
    def cors_origins(self) -> list[str]:
        return self.parse_cors_origins(self.cors_origins_raw)

    @staticmethod
    def parse_cors_origins(value: str) -> list[str]:
        stripped_value = value.strip()
        if not stripped_value:
            return []

        if stripped_value.startswith("["):
            parsed_value = json.loads(stripped_value)
            if not isinstance(parsed_value, list) or not all(
                isinstance(origin, str) for origin in parsed_value
            ):
                raise ValueError("CORS_ORIGINS JSON value must be an array of strings")
            return [origin.strip() for origin in parsed_value if origin.strip()]

        return [origin.strip() for origin in stripped_value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
