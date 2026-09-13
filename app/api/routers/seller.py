from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import SellerServiceDep, SessionDep
from app.api.schemas.seller import SellerCreate, SellerRead
from app.core.security import oauth2_scheme
from app.database.models import Seller
from app.utils import decode_access_token

router = APIRouter(prefix="/seller", tags=["Seller"])


# Register a Seller
@router.post("/signup", response_model=SellerRead)
async def register_seller(
    seller: SellerCreate,
    service: SellerServiceDep,
):
    return await service.add(seller)


# Login a Seller
# Random Note: a request form is like request body, but it's strictly key-value pair, no nesting
@router.post("/token")
async def login_seller(
    request_form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: SellerServiceDep,
) -> dict[str, Any]:
    token = await service.token(request_form.username, request_form.password)
    return {
        "access_token": token,
        "type": "jwt",
    }


# Random Note: OAuth scheme only picks up the token from the header
@router.get("/dashboard", response_model=SellerRead)
async def get_dashboard(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
):
    data = decode_access_token(token)

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    seller = await session.get(Seller, data["user"]["id"])

    return seller
