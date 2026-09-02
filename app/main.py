from fastapi import FastAPI, HTTPException, status
from scalar_fastapi import get_scalar_api_reference

from .database import save, shipments
from .schemas import ShipmentCreate, ShipmentRead, ShipmentUpdate

app = FastAPI()

# shipments = {
#     12001: {
#         "weight": 1.5,
#         "content": "clothing",
#         "destination": 11298,
#         "status": "placed",
#     },
#     12002: {
#         "weight": 2.3,
#         "content": "electronics",
#         "destination": 11300,
#         "status": "in_transit",
#     },
#     12003: {
#         "weight": 1.5,
#         "content": "books",
#         "destination": 11301,
#         "status": "delivered",
#     },
#     12004: {
#         "weight": 5.0,
#         "content": "furniture",
#         "destination": 11302,
#         "status": "placed",
#     },
#     12005: {
#         "weight": 1.3,
#         "content": "documents",
#         "destination": 11303,
#         "status": "in_transit",
#     },
#     12006: {
#         "weight": 3.8,
#         "content": "kitchen items",
#         "destination": 11304,
#         "status": "placed",
#     },
#     12007: {
#         "weight": 1.2,
#         "content": "toys",
#         "destination": 11305,
#         "status": "delivered",
#     },
# }


@app.get("/shipment", response_model=ShipmentRead)
def get_shipment(id: int | None = None):

    if id not in shipments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Given id does not exist.",
        )

    return shipments[id]


@app.post("/shipment")
def submit_shipment(shipment: ShipmentCreate) -> dict[str, int]:
    # Create and assign shipment a new id
    new_id = max(shipments.keys()) + 1
    # Add to shipment dict
    shipments[new_id] = {
        **shipment.model_dump(),
        "id": new_id,
        "status": "placed",
    }
    save()
    # Return id for later use
    return {"id": new_id}


@app.patch("/shipment", response_model=ShipmentRead)
def update_shipment(id: int, body: ShipmentUpdate):
    # Update data with given fields
    shipments[id].update(body.model_dump(exclude_none=True))
    return shipments[id]


@app.delete("/shipment")
def delete_shipment(id: int) -> dict[str, str]:
    shipments.pop(id)
    return {"detail": f"Shipment with #{id} is deleted!"}


# Scalar Endpoint


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Scalar API",
    )
