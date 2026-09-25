from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import any_, select

from app.api.schemas.delivery_partner import (
    DeliveryPartnerCreate,
)
from app.database.models import DeliveryPartner, Shipment
from app.services.user import UserService


class DeliveryPartnerService(UserService[DeliveryPartner]):
    def __init__(self, session: AsyncSession):
        super().__init__(DeliveryPartner, session)

    async def add(self, partner_create: DeliveryPartnerCreate) -> DeliveryPartner:
        return await self._add_user(partner_create.model_dump())

    async def update(self, partner: DeliveryPartner) -> DeliveryPartner:
        return await self._update(partner)

    async def get_partners_by_zipcode(self, zipcode: int) -> Sequence[DeliveryPartner]:
        return (
            await self.session.scalars(
                select(self.model).where(
                    zipcode == any_(self.model.serviceable_zip_codes)
                )
            )
        ).all()

    async def assign_shipment(self, shipment: Shipment) -> DeliveryPartner | None:
        eligible_partners = await self.get_partners_by_zipcode(shipment.destination)

        # Relationship sync is in-memory for this object only (same session);
        # not all copies by id. Persist on commit.
        for partner in eligible_partners:
            if partner.current_handling_capacity > 0:
                partner.shipments.append(shipment)
                return partner

        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="No delivery partner available",
        )

    async def token(self, email, password) -> str:
        return await self._generate_token(email, password)
