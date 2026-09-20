from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.shipment import ShipmentCreate, ShipmentUpdate
from app.database.models import Seller, Shipment, ShipmentStatus


class ShipmentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: UUID) -> Shipment | None:  # type: ignore
        return await self.session.get(Shipment, id)

    async def add(self, shipment_create: ShipmentCreate, seller: Seller) -> Shipment:  # type: ignore
        new_shipment = Shipment(
            **shipment_create.model_dump(),
            status=ShipmentStatus.placed,
            estimated_delivery=datetime.now() + timedelta(days=1),  # noqa: DTZ005
            seller_id=seller.id,
        )
        self.session.add(new_shipment)
        await self.session.commit()
        await self.session.refresh(new_shipment)

        return new_shipment

    async def update(self, id: UUID, shipment_update: ShipmentUpdate) -> Shipment:  # type: ignore

        update = shipment_update.model_dump(exclude_none=True)

        if not update:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided to update.",
            )

        shipment = await self.get(id)

        if not shipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipment not found.",
            )

        shipment.sqlmodel_update(update)

        self.session.add(shipment)
        await self.session.commit()
        await self.session.refresh(shipment)

        return shipment

    async def delete(self, id: UUID) -> None:
        await self.session.delete(await self.get(id))
        await self.session.commit()
