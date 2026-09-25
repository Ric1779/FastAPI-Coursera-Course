from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependencies import SellerServiceDep, get_seller_access_token_data
from app.api.schemas.seller import SellerCreate, SellerRead
from app.database.redis import add_jti_to_blacklist

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


# Logout the seller
@router.get("/logout")
async def logout_seller(
    token_data: Annotated[dict, Depends(get_seller_access_token_data)],
):
    await add_jti_to_blacklist(token_data["jti"])

    return {"detail": "Succesfully logged out!"}
