from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from fastapi.security.http import HTTPAuthorizationCredentials

oauth2_scheme_seller = OAuth2PasswordBearer(tokenUrl="/seller/token")

oauth2_scheme_partner = OAuth2PasswordBearer(tokenUrl="/partner/token")


class AccessTokenBearer(HTTPBearer):
    async def __call__(self, request) -> HTTPAuthorizationCredentials | None:
        return await super().__call__(request)
