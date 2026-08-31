from typing import Any

from fastapi import FastAPI
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
        return {"detail": "Given id doesn't exist."}

    return shipments[id]


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Scalar API",
    )
