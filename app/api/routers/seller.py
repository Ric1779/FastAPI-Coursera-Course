from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr

from app.api.dependencies import SellerServiceDep, get_seller_access_token_data
from app.api.schemas.seller import SellerCreate, SellerRead
from app.config import app_settings
from app.database.redis import add_jti_to_blacklist
from app.utils import TEMPLATE_DIR

router = APIRouter(prefix="/seller", tags=["Seller"])


# verify Seller email
@router.get("/verify")
async def verify_seller_email(
    token: str,
    service: SellerServiceDep,
) -> dict:
    await service.verify_email(token)
    return {"detail": "Account Verified!"}


###################################################
#                passwrod reset
###################################################


# Email password reset link
@router.get("/forgot_password")
async def forgot_password(
    email: EmailStr,
    service: SellerServiceDep,
) -> dict:
    await service.send_password_reset_link(email, router.prefix)
    return {"detail": "Check email for password reset link"}


# Password reset form
@router.get("/reset_password_form")
async def get_reset_password_form(request: Request, token: str):
    templates = Jinja2Templates(TEMPLATE_DIR)

    return templates.TemplateResponse(
        request=request,
        name="password/reset.html",
        context={
            "reset_url": f"http://{app_settings.APP_DOMAIN}{router.prefix}/reset_password?token={token}"
        },
    )


# verify Seller email
@router.post("/reset_password")
async def reset_password(
    request: Request,
    token: str,
    password: Annotated[str, Form()],
    service: SellerServiceDep,
):
    is_success = await service.reset_password(token, password)

    templates = Jinja2Templates(TEMPLATE_DIR)

    return templates.TemplateResponse(
        request=request,
        name="password/reset_success.html"
        if is_success
        else "password/reset_failed.html",
    )


###################################################
#           seller register, login, logout
###################################################


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
