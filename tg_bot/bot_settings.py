from pathlib import Path
from pydantic import SecretStr

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    bot_token: SecretStr
    admin_id: int

    backend_url: str

    redis_url: str

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


settings = Settings()
