from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class BaseSeller(BaseModel):
    name: str
    email: EmailStr


class SellerCreate(BaseSeller):
    password: str
    address: str | None = Field(default=None)
    zip_code: int | None = Field(default=None)


class SellerRead(BaseSeller):
    id: UUID
