from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://goag:goag@localhost:5432/goag"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"
    device_hash_secret: str = ""
    goag_test_worksite_lat: float = 0.0
    goag_test_worksite_lon: float = 0.0
    goag_test_geofence_radius_m: float = 150.0
    goag_max_gps_accuracy_m: float = 100.0
    goag_shift_start: str = "09:00"
    goag_shift_end: str = "18:00"
    goag_late_grace_minutes: int = 15
    goag_test_proxy_delay_ms: int = 0
    goag_gmail_client_id: str = ""
    goag_gmail_client_secret: str = ""
    goag_gmail_redirect_uri: str = ""
    goag_gmail_mailbox_address: str = ""
    goag_gmail_token_encryption_key: str = ""
    goag_web_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def gmail_oauth_configured(self) -> bool:
        return bool(self.goag_gmail_client_id and self.goag_gmail_client_secret and self.goag_gmail_redirect_uri)


@lru_cache
def get_settings() -> Settings:
    return Settings()
