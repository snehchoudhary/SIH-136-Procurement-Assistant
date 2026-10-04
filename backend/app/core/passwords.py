"""Small PBKDF2 password helpers for demo credentials and OIDC migration readiness."""
import hashlib
import hmac
import secrets

_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, _ITERATIONS)
    return f'pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    if not encoded.startswith('pbkdf2_sha256$'):
        # Backward compatibility for databases seeded by the first demo scaffold.
        return hmac.compare_digest(password, encoded)
    try:
        _, iterations, salt_hex, digest_hex = encoded.split('$', 3)
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False
