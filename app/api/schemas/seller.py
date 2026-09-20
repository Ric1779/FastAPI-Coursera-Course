from uuid import UUID

from pydantic import BaseModel, EmailStr


class BaseSeller(BaseModel):
    name: str
    email: EmailStr


class SellerCreate(BaseSeller):
    password: str


class SellerRead(BaseSeller):
    id: UUID
