from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.shipment import ShipmentCreate, ShipmentUpdate
from app.database.models import (
    DeliveryPartner,
    Seller,
    Shipment,
    ShipmentStatus,
)
from app.services.base import BaseService
from app.services.delivery_partner import DeliveryPartnerService
from app.services.shipment_event import ShipmentEventService


class ShipmentService(BaseService[Shipment]):
    def __init__(
        self,
        session: AsyncSession,
        partner_service: DeliveryPartnerService,
        event_service: ShipmentEventService,
    ):
        super().__init__(Shipment, session)
        self.partner_service = partner_service
        self.event_service = event_service

    async def get(self, id: UUID) -> Shipment | None:
        return await self._get(id)

    async def add(self, shipment_create: ShipmentCreate, seller: Seller) -> Shipment:
        new_shipment = self.model(
            **shipment_create.model_dump(),
            estimated_delivery=datetime.now() + timedelta(days=1),  # noqa: DTZ005
            seller_id=seller.id,
        )

        # Assign delivery partner to the shipment
        partner = await self.partner_service.assign_shipment(new_shipment)

        if partner:
            # Maybe the manual FK assignment is redundant.
            # When this runs (in assign_shipment method of DeliveryPartnerService in the above line):
            # partner.shipments.append(shipment)
            # with back_populates between DeliveryPartner.shipments and Shipment.delivery_partner, SQLAlchemy syncs both sides in the same session:
            # .
            # shipment.delivery_partner = partner
            # shipment.delivery_partner_id = partner.id

            new_shipment.delivery_partner_id = partner.id
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Currently we don't have any delivery partner available.",
            )

        shipment = await self._add(new_shipment)

        if seller.zip_code is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seller zip code is required to create a shipment event.",
            )

        await self.event_service.add(
            shipment=shipment,
            location=seller.zip_code,
            status=ShipmentStatus.placed,
            description=f"Assigned to {partner.name}",
        )
        # Event is already committed in event_service._add; reload timeline so
        # the response isn't the stale empty collection from the first refresh.
        # The stale empty collection is solved in another way in the below update method
        await self.session.refresh(shipment, attribute_names=["timeline"])

        return shipment

    async def update(
        self,
        id: UUID,
        shipment_update: ShipmentUpdate,
        partner: DeliveryPartner,
    ) -> Shipment:
        # Make sure at least one value is provided
        update = shipment_update.model_dump(exclude_none=True)

        if not update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided to update.",
            )

        # Get the relevant shipment and validate it against the current delivery partner
        shipment = await self.get(id)

        if not shipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found.",
            )
        # validate the delivery partner
        if shipment.delivery_partner_id != partner.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized",
            )

        if shipment_update.estimated_delivery:
            shipment.estimated_delivery = shipment_update.estimated_delivery

        # Create the new event
        if len(update) > 1 or not shipment_update.estimated_delivery:
            await self.event_service.add(
                shipment=shipment,
                **update,
            )

        return await self._update(shipment)

    async def cancel(self, id: UUID, seller: Seller) -> Shipment:
        # validate the seller
        shipment = await self.get(id)
        if not shipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found.",
            )
        if shipment.seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized",
            )

        event = await self.event_service.add(
            shipment=shipment,
            status=ShipmentStatus.cancelled,
        )

        shipment.timeline.append(event)

        return shipment

    async def delete(self, id: UUID, seller: Seller) -> None:
        shipment = await self.get(id)
        if not shipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found.",
            )
        # validate the seller
        if shipment.seller_id != seller.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized",
            )
        if shipment is not None:
            await self._delete(shipment)
