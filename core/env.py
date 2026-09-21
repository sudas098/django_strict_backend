from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    """Runtime Environment Configuration with Strict Validation"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid"
    )

    django_env: str = Field(
        ...,
        description=(
            "Deployment Environment name, e.g.: 'local', 'staging', 'production'"
        )
    )

    secret_key: str = Field(
        ...,
        description=(
            "Cryptographic secret key for djago session and signing"
        ),
    )

    debug: bool = Field(default=False)
    allowed_hosts: list[str] = Field(default=["127.0.0.1", "localhost"])

@lru_cache
def get_settings() -> EnvSettings:
    """Return cached environment settings singleton."""
    return EnvSettings()
