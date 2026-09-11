from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import ServiceDep
from app.api.schemas.shipment import ShipmentCreate, ShipmentRead, ShipmentUpdate
from app.database.models import Shipment

router = APIRouter()


@router.get("/shipment", response_model=ShipmentRead)
async def get_shipment(id: int, service: ServiceDep):

    shipment = await service.get(id)

    if shipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Given id does not exists.",
        )

    return shipment


@router.post("/shipment")
async def submit_shipment(shipment: ShipmentCreate, service: ServiceDep) -> Shipment:
    return await service.add(shipment)


@router.patch("/shipment")
async def update_shipment(
    id: int, shipment_update: ShipmentUpdate, service: ServiceDep
) -> Shipment:
    return await service.update(id, shipment_update)


@router.delete("/shipment")
async def delete_shipment(id: int, service: ServiceDep) -> dict[str, str]:
    await service.delete(id)
    return {"detail": f"Shipment with #{id} is deleted!"}
