from typing import Any

from fastapi import FastAPI, HTTPException, status
from scalar_fastapi import get_scalar_api_reference

app = FastAPI()

shipments = {
    12001: {
        "weight": 0.5,
        "content": "clothing",
        "status": "placed",
    },
    12002: {
        "weight": 2.3,
        "content": "electronics",
        "status": "in transit",
    },
    12003: {
        "weight": 1.5,
        "content": "books",
        "status": "delivered",
    },
    12004: {
        "weight": 5.0,
        "content": "furniture",
        "status": "placed",
    },
    12005: {
        "weight": 0.3,
        "content": "documents",
        "status": "in transit",
    },
    12006: {
        "weight": 3.8,
        "content": "kitchen items",
        "status": "placed",
    },
    12007: {
        "weight": 1.2,
        "content": "toys",
        "status": "delivered",
    },
}


@app.get("/shipment/latest")
def get_latest_shipment() -> dict[str, Any]:
    id = max(shipments.keys())
    return shipments[id]


@app.get("/shipment")
def get_shipment(id: int | None = None) -> dict[str, Any]:

    if id not in shipments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Given id does not exist.",
        )

    return shipments[id]


@app.post("/shipment")
def submit_shipment(data: dict[str, Any]) -> dict[str, Any]:

    weight = data["weight"]
    content = data["content"]

    if weight > 25:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="Maximum weight is 25 kgs.",
        )

    new_id = max(shipments.keys()) + 1

    shipments[new_id] = {
        "content": content,
        "weight": weight,
        "status": "placed",
    }

    return {"id": new_id}


@app.put("/shipment")
def shipment_update(
    id: int,
    content: str,
    weight: float,
    status: str,
) -> dict[str, Any]:
    shipments[id] = {
        "content": content,
        "weight": weight,
        "status": status,
    }

    return shipments[id]


@app.patch("/shipment")
def patch_shipment(id: int, body: dict) -> dict[str, Any]:

    shipment = shipments[id]

    shipment.update(body)

    shipments[id] = shipment

    return shipment


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
