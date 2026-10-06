from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TicketFlow"
    database_url: str = "sqlite:///./ticketflow.db"
    redis_url: str | None = None
    secret_key: str = "dev-only-secret-change-me-before-deploying"
    access_token_expire_minutes: int = 60
    agent_emails: str = ""
    model_path: str = "ml/artifacts/classifier.joblib"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def agent_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.agent_emails.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
