from dataclasses import dataclass
import os


@dataclass
class Settings:
    """Global application configuration."""

    app_name: str = "AURA"
    full_name: str = "Automated User Response Assistant"

    environment: str = os.getenv(
        "APP_ENV",
        "development"
    )

    default_mode: str = "DO_IT_FOR_ME"

    screenshot_directory: str = "data/screenshots"
    log_directory: str = "data/logs"
    temp_directory: str = "data/temp"


settings = Settings()