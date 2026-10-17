from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.schemas.delivery_partner import (
    DeliveryPartnerCreate,
)
from app.core.exceptions import DeliveryPartnerCapacityExceeded
from app.database.models import DeliveryPartner, Location, ServiceableLocation, Shipment
from app.services.user import UserService


class DeliveryPartnerService(UserService[DeliveryPartner]):
    def __init__(self, session: AsyncSession):
        super().__init__(DeliveryPartner, session)

    async def add(self, partner_create: DeliveryPartnerCreate) -> DeliveryPartner:
        partner: DeliveryPartner = await self._add_user(
            partner_create.model_dump(exclude={"serviceable_zip_codes"}),
            "partner",
        )

        for zip_code in partner_create.serviceable_zip_codes:
            location = await self.session.get(Location, zip_code)
            partner.serviceable_locations.append(
                location if location else Location(zip_code=zip_code)
            )

        return await self._update(partner)

    async def update(self, partner: DeliveryPartner) -> DeliveryPartner:
        return await self._update(partner)

    async def get_partners_by_zipcode(self, zipcode: int) -> Sequence[DeliveryPartner]:
        return (
            await self.session.scalars(
                select(self.model)
                .join(ServiceableLocation)
                .join(Location)
                .where(Location.zip_code == zipcode)
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

        raise DeliveryPartnerCapacityExceeded()

    async def token(self, email, password) -> str:
        return await self._generate_token(email, password)
