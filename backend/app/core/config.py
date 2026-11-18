from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str
    AUTO_REFRESH_ENABLED: bool = False
    AUTO_REFRESH_INTERVAL_SECONDS: int = 120
    PARLAYS_ENABLED: bool = False
    MODEL_ODDS_ENABLED: bool = False
    MARKET_MODEL_DIRECTORY: Path = Path(__file__).resolve().parents[3] / "build" / "market-models"
    MODEL_ODDS_MARGIN: float = 0.05
    MODEL_DIRECTORY: Path = Path(__file__).resolve().parents[3] / "build" / "sprint2-models"
    AUTH_ASSESSMENT_ENABLED: bool = False
    LOCAL_DEMO_HTTP: bool = False
    VIRTUAL_BETTING_ENABLED: bool = False

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


settings = Settings()
