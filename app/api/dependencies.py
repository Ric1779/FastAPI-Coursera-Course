from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.services.seller import SellerService
from app.services.shipment import ShipmentService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_shipment_service(session: SessionDep):
    return ShipmentService(session)


ShipmentServiceDep = Annotated[ShipmentService, Depends(get_shipment_service)]


def get_seller_service(session: SessionDep):
    return SellerService(session)


SellerServiceDep = Annotated[SellerService, Depends(get_seller_service)]
