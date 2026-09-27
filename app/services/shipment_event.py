from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Shipment, ShipmentEvent, ShipmentStatus
from app.services.base import BaseService


class ShipmentEventService(BaseService[ShipmentEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(ShipmentEvent, session)

    async def add(
        self,
        shipment: Shipment,
        location: int | None = None,
        status: ShipmentStatus | None = None,
        description: str | None = None,
    ) -> ShipmentEvent:
        if not location or not status:
            last_event = await self.get_latest_event(
                shipment
            )  # maybe this method doesn't have to be a coroutine function
            if last_event:
                location = location if location else last_event.location
                status = status if status else last_event.status
        # Link via relationship so shipment.timeline is updated in-memory
        # (shipment_id alone does not sync back_populates).
        new_event = ShipmentEvent(
            location=location,
            status=status,
            description=description
            if description
            else self._generate_description(status, location),
            shipment=shipment,
        )

        return await self._add(new_event)

    # maybe this method doesn't have to be an async function
    async def get_latest_event(self, shipment: Shipment) -> ShipmentEvent | None:
        timeline = shipment.timeline or []
        if not timeline:
            return None
        return max(timeline, key=lambda event: event.created_at)

    def _generate_description(
        self, status: ShipmentStatus | None, location: int | None
    ) -> str:
        if status is None or location is None:
            return "_generate_description method error"
        match status:
            case ShipmentStatus.placed:
                return "Assigned Delivery Partner"
            case ShipmentStatus.out_for_delivery:
                return "Shipment out for delivery"
            case ShipmentStatus.delivered:
                return "Succesfully delivered"
            case ShipmentStatus.cancelled:
                return "Cancelled by the seller"
            case _:  # also includes ShipmentStatus.in_transit
                return f"Scanned at {location}"
