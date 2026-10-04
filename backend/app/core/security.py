from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.config import settings
from pydantic import BaseModel

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

class OIDCUserInfo(BaseModel):
    sub: str
    email: str
    name: str
    role: str
    org_id: str | None = None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> OIDCUserInfo | None:
    try:
        # The explicitly marked demo session is only used by the browser
        # prototype when the API is unreachable. It is not accepted as a
        # backend bearer token and cannot access protected API operations.
        # Browser-only local demo tokens are never backend credentials.
        if token.endswith('.local-demo'):
            return None
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            return None
        return OIDCUserInfo(
            sub=sub,
            email=payload.get("email"),
            name=payload.get("name"),
            role=payload.get("role"),
            org_id=payload.get("org_id")
        )
    except JWTError:
        return None
