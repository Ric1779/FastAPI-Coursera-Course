from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr

from app.api.dependencies import (
    DeliveryPartnerDep,
    DeliveryPartnerServiceDep,
    get_partner_access_token_data,
)
from app.api.schemas.delivery_partner import (
    DeliveryPartnerCreate,
    DeliveryPartnerRead,
    DeliveryPartnerUpdate,
)
from app.api.tag import APITag
from app.config import app_settings
from app.core.exceptions import NothingToUpdate
from app.database.redis import add_jti_to_blacklist
from app.utils import TEMPLATE_DIR

router = APIRouter(prefix="/partner", tags=[APITag.PARTNER])


# verify Seller email
@router.get("/verify")
async def verify_delivery_partner_email(
    token: str,
    service: DeliveryPartnerServiceDep,
) -> dict:
    await service.verify_email(token)
    return {"detail": "Account Verified!"}


@router.get("/me", response_model=DeliveryPartnerRead)
async def get_delivery_partner_profile(partner: DeliveryPartnerDep):
    return partner


###################################################
#                passwrod reset
###################################################


# Email password reset link
@router.get("/forgot_password")
async def forgot_password(
    email: EmailStr,
    service: DeliveryPartnerServiceDep,
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
    service: DeliveryPartnerServiceDep,
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


# Register a Delivery Partner
@router.post("/signup", response_model=DeliveryPartnerRead)
async def register_delivery_partner(
    partner_create: DeliveryPartnerCreate,
    service: DeliveryPartnerServiceDep,
):
    return await service.add(partner_create)


# Login a Delivery Partner
# Random Note: a request form is like request body, but it's strictly key-value pair, no nesting
@router.post("/token")
async def login_delivery_partner(
    request_form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: DeliveryPartnerServiceDep,
) -> dict[str, Any]:
    token = await service.token(request_form.username, request_form.password)
    return {
        "access_token": token,
        "type": "jwt",
    }


# Update the delivery partner
@router.post("/update")
async def update_delivery_partner(
    partner_update: DeliveryPartnerUpdate,
    partner: DeliveryPartnerDep,
    service: DeliveryPartnerServiceDep,
):
    update = partner_update.model_dump(exclude_none=True)

    if not update:
        raise NothingToUpdate()

    return await service.update(partner.sqlmodel_update(update))


# Logout the Delivery Partner
@router.get("/logout")
async def logout_delivery_partner(
    token_data: Annotated[dict, Depends(get_partner_access_token_data)],
):
    await add_jti_to_blacklist(token_data["jti"])

    return {"detail": "Succesfully logged out!"}
