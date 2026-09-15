from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_path: str = "./data/farmacia.db"
    temperature_min_c: float = 2.0
    temperature_max_c: float = 8.0
    consecutive_out_of_range: int = 5
    heartbeat_timeout_seconds: int = 600
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


settings = Settings()
