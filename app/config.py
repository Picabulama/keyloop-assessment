from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+psycopg2://inventory:inventory@localhost:5432/inventory"
    aging_threshold_days: int = 90
    log_level: str = "INFO"
    environment: str = "development"


settings = Settings()
