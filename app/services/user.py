from datetime import timedelta
from typing import Generic, TypeVar
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from passlib.context import CryptContext  # type: ignore
from pydantic import EmailStr, NameEmail
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import app_settings
from app.database.models import User
from app.services.base import BaseService
from app.services.notification import NotificationService
from app.utils import (
    decode_url_safe_token,
    generate_access_token,
    generate_url_safe_token,
)

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

UserType = TypeVar("UserType", bound=User)


class UserService(BaseService[UserType], Generic[UserType]):
    def __init__(
        self, model: type[UserType], session: AsyncSession, tasks: BackgroundTasks
    ):
        super().__init__(model, session)
        self.notification_service = NotificationService(tasks)

    async def _add_user(
        self,
        user_create_data: dict,
        router_prefix: str,
    ) -> UserType:  # user_create_data contains the password!
        user = self.model(
            **{k: v for k, v in user_create_data.items() if k != "password"},
            password_hash=password_context.hash(user_create_data["password"]),
        )

        user = await self._add(user)

        token = generate_url_safe_token(
            {
                "email": user.email,
                "id": str(user.id),
            }
        )

        await self.notification_service.send_email_with_template(
            recipients=[NameEmail(name="", email=user.email)],
            subject="Verify your account with Fastship",
            context={
                "username": user.name,
                "verification_url": f"http://{app_settings.APP_DOMAIN}/{router_prefix}/verify?token={token}",
            },
            template_name="mail_email_verify.html",
        )

        return user

    async def verify_email(self, token: str):
        token_data = decode_url_safe_token(
            token,
            expiry=timedelta(days=1),
        )

        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token",
            )

        user = await self._get(UUID(token_data["id"]))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.email_verified = True
        await self._update(user)

    async def _get_by_email(self, email: EmailStr) -> UserType | None:
        # select from SQLModel is needed rather than from sqlalchemy because
        # User isn't table=True, so `.email == ...` looks like bool to the type checker.
        return await self.session.scalar(
            select(self.model).where(self.model.email == email)
        )

    async def _generate_token(self, email, password) -> str:
        # validate the credentials
        user = await self._get_by_email(email)

        if user is None or not password_context.verify(
            password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email or password is incorrect!",
            )

        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified!",
            )

        token = generate_access_token(
            data={
                "user": {
                    "name": user.name,
                    "id": str(user.id),
                }
            }
        )

        return token

    async def send_password_reset_link(self, email: EmailStr, router_prefix: str):
        user = await self._get_by_email(email)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        token = generate_url_safe_token(
            data={
                "id": str(user.id),
            },
            salt="password-reset",
        )

        await self.notification_service.send_email_with_template(
            recipients=[NameEmail(name="", email=user.email)],
            subject="FastShip account password reset",
            context={
                "username": user.name,
                "reset_url": f"http://{app_settings.APP_DOMAIN}{router_prefix}/reset_password_form?token={token}",
            },
            template_name="mail_password_reset.html",
        )

    async def reset_password(self, token: str, password: str) -> bool:
        token_data = decode_url_safe_token(
            token,
            salt="password-reset",
            expiry=timedelta(days=1),
        )

        if not token_data:
            return False

        user = await self._get(UUID(token_data["id"]))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.password_hash = password_context.hash(password)

        await self._update(user)

        return True
