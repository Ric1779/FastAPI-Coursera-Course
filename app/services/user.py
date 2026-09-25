from typing import Generic, TypeVar

from fastapi import HTTPException, status
from passlib.context import CryptContext  # type: ignore
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database.models import User
from app.services.base import BaseService
from app.utils import generate_access_token

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

UserType = TypeVar("UserType", bound=User)


class UserService(BaseService[UserType], Generic[UserType]):
    def __init__(self, model: type[UserType], session: AsyncSession):
        super().__init__(model, session)

    async def _add_user(
        self, user_create_data: dict
    ) -> UserType:  # user_create_data contains the password!
        user = self.model(
            **{k: v for k, v in user_create_data.items() if k != "password"},
            password_hash=password_context.hash(user_create_data["password"]),
        )

        return await self._add(user)

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

        token = generate_access_token(
            data={
                "user": {
                    "name": user.name,
                    "id": str(user.id),
                }
            }
        )

        return token
