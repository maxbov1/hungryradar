"""Runtime configuration for HungryRadar, loaded from the environment / .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_maps_api_key: str = ""
    hungryradar_model_id: str = ""
    hungryradar_default_city: str = "San Francisco, CA"


settings = Settings()
