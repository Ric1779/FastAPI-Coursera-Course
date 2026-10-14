from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from pydantic import BaseModel

oauth2_scheme_seller = OAuth2PasswordBearer(
    tokenUrl="/seller/token", scheme_name="Seller"
)

oauth2_scheme_partner = OAuth2PasswordBearer(
    tokenUrl="/partner/token", scheme_name="Delivery Partner"
)


class TokenData(BaseModel):
    access_token: str
    token_type: str


class AccessTokenBearer(HTTPBearer):
    async def __call__(self, request) -> HTTPAuthorizationCredentials | None:
        return await super().__call__(request)
