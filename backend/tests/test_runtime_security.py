import pytest

from app.core.config import Settings
from app.core.security import verify_token


def test_production_rejects_missing_or_weak_signing_secret():
    missing = Settings(_env_file=None, APP_ENV='production', SECRET_KEY=None)
    weak = Settings(_env_file=None, APP_ENV='production', SECRET_KEY='development-secret')

    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        _ = missing.jwt_secret_key
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        _ = weak.jwt_secret_key


def test_production_requires_strong_database_password_and_disables_demo_seeding():
    valid_key = 'JWT-random-192bit-Cli3nt-Key-7a9Z-xP4v-M2q8'
    missing_db_password = Settings(_env_file=None, APP_ENV='production', SECRET_KEY=valid_key,
                                   POSTGRES_PASSWORD=None, SEED_DEMO_USERS=False)
    weak_db_password = Settings(_env_file=None, APP_ENV='production', SECRET_KEY=valid_key,
                                POSTGRES_PASSWORD='pilotproof', SEED_DEMO_USERS=False)
    demo_seed = Settings(_env_file=None, APP_ENV='production', SECRET_KEY=valid_key,
                         POSTGRES_PASSWORD='DB-random-Salt-0q9W-3n7E-8p1K-6t4R', SEED_DEMO_USERS=True)

    for config in (missing_db_password, weak_db_password):
        with pytest.raises(RuntimeError, match='POSTGRES_PASSWORD'):
            config.validate_runtime_configuration()
    with pytest.raises(RuntimeError, match='SEED_DEMO_USERS'):
        demo_seed.validate_runtime_configuration()


def test_browser_demo_token_is_never_a_backend_jwt():
    assert verify_token('eyJhbGciOiJub25lIn0.eyJyb2xlIjoib2ZmaWNlciJ9.local-demo') is None


def test_browser_demo_token_cannot_open_protected_route(client):
    token = 'eyJhbGciOiJub25lIn0.eyJyb2xlIjoib2ZmaWNlciJ9.local-demo'
    response = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


def test_local_secret_is_ephemeral_when_environment_secret_is_weak():
    config = Settings(_env_file=None, APP_ENV='development', SECRET_KEY='development-secret')
    assert config.jwt_secret_key != 'development-secret'
    assert len(config.jwt_secret_key) >= 32
