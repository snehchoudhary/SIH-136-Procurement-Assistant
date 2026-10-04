from pydantic import BaseModel, ConfigDict
from uuid import UUID

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    sub: str | None = None
