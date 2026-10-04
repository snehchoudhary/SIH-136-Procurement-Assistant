import secrets
from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default='development', alias='APP_ENV')
    backend_host: str = Field(default='0.0.0.0', alias='BACKEND_HOST')
    backend_port: int = Field(default=8000, alias='BACKEND_PORT')
    postgres_db: str = Field(default='pilotproof', alias='POSTGRES_DB')
    postgres_user: str = Field(default='pilotproof', alias='POSTGRES_USER')
    postgres_password: str | None = Field(default=None, alias='POSTGRES_PASSWORD')
    postgres_host: str = Field(default='postgres', alias='POSTGRES_HOST')
    postgres_port: int = Field(default=5432, alias='POSTGRES_PORT')
    seed_demo_users: bool = Field(default=False, alias='SEED_DEMO_USERS')
    database_url_override: str | None = Field(default=None, alias='DATABASE_URL')
    secret_key: str | None = Field(default=None, alias='SECRET_KEY')
    oidc_issuer: str | None = Field(default=None, alias='OIDC_ISSUER')
    _ephemeral_secret: str = PrivateAttr(default_factory=lambda: secrets.token_urlsafe(48))

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False)

    @property
    def is_local(self) -> bool:
        return self.app_env.lower() in {'development', 'dev', 'local', 'test'}

    @staticmethod
    def _strong_secret(value: str | None, minimum: int = 32) -> bool:
        if not value or len(value) < minimum:
            return False
        lowered = value.lower()
        if lowered in {'pilotproof', 'changeme', 'change-me', 'secret', 'password'}:
            return False
        if len(set(value)) < 16:
            return False
        # Reject short repeating patterns even when they happen to contain a
        # reasonable character count (for example, a 12-character phrase repeated).
        for period in range(1, min(16, len(value) // 2) + 1):
            if value == (value[:period] * ((len(value) + period - 1) // period))[:len(value)]:
                return False
        return True

    @property
    def jwt_secret_key(self) -> str:
        if self.is_local:
            return self.secret_key if self._strong_secret(self.secret_key) else self._ephemeral_secret
        if not self._strong_secret(self.secret_key):
            raise RuntimeError('Startup blocked: set SECRET_KEY to a random value of at least 32 characters outside local development.')
        return self.secret_key

    def validate_runtime_configuration(self) -> None:
        # Accessing the property validates the signing key.
        _ = self.jwt_secret_key
        if not self.is_local:
            if self.seed_demo_users:
                raise RuntimeError('Startup blocked: SEED_DEMO_USERS must be false outside local development.')
            if self.database_url_override:
                from sqlalchemy.engine import make_url
                url = make_url(self.database_url_override)
                database_password = url.password or ''
                if url.get_backend_name() != 'postgresql' or not self._strong_secret(database_password, 24):
                    raise RuntimeError('Startup blocked: DATABASE_URL must use PostgreSQL with a random password of at least 24 characters.')
            elif not self._strong_secret(self.postgres_password, 24):
                raise RuntimeError('Startup blocked: set POSTGRES_PASSWORD to a random value of at least 24 characters outside local development.')

    @property
    def database_url(self) -> str:
        if self.database_url_override and self.database_url_override.strip():
            return self.database_url_override.strip()
        if self.app_env.lower() in {'development', 'dev', 'local'}:
            return 'sqlite:///./pilotproof-dev.db'
        from sqlalchemy.engine import URL
        return URL.create(
            'postgresql+psycopg', username=self.postgres_user,
            password=self.postgres_password or '', host=self.postgres_host,
            port=self.postgres_port, database=self.postgres_db,
        ).render_as_string(hide_password=False)


settings = Settings()
