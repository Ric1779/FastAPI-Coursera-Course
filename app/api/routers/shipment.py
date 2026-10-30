from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request, status
from fastapi.templating import Jinja2Templates

from app.api.tag import APITag
from app.config import app_settings
from app.core.exceptions import EntityNotFound
from app.database.models import Shipment, TagName
from app.utils import TEMPLATE_DIR

from ..dependencies import DeliveryPartnerDep, SellerDep, SessionDep, ShipmentServiceDep
from ..schemas.shipment import (
    ShipmentCreate,
    ShipmentRead,
    ShipmentUpdate,
)

router = APIRouter(prefix="/shipment", tags=[APITag.SHIPMENT])

templates = Jinja2Templates(TEMPLATE_DIR)


@router.get("/", response_model=ShipmentRead)
async def get_shipment(
    id: UUID,
    service: ShipmentServiceDep,
):
    return await service.get(id)


# Random note: response_model is primarily for data validation and serialization,
# while the response_class dictates the actual format of the HTTP response.


# Tracking details of shipment
@router.get("/track")
async def get_tracking(request: Request, id: UUID, service: ShipmentServiceDep):

    # Check of shipment with given id
    shipment = await service.get(id)

    if shipment is None:
        raise EntityNotFound()

    context = shipment.model_dump()
    context["status"] = shipment.status
    context["partner"] = shipment.delivery_partner.name
    context["timeline"] = [
        event.model_dump()
        for event in sorted(
            shipment.timeline,
            key=lambda event: event.created_at,
            reverse=True,
        )
    ]
    return templates.TemplateResponse(
        request=request,
        name="track.html",
        context=context,
    )


@router.post(
    "/",
    response_model=ShipmentRead,
    name="Submit Shipment",
    description="Submit a new **shipment**.",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"description": "Shipment created"},
        status.HTTP_406_NOT_ACCEPTABLE: {
            "description": "Delivery partner not available."
        },
    },
)
async def submit_shipment(
    shipment: ShipmentCreate,
    service: ShipmentServiceDep,
    seller: SellerDep,
) -> Shipment:
    return await service.add(shipment, seller)


@router.patch("/", response_model=ShipmentRead)
async def update_shipment(
    id: UUID,
    shipment_update: ShipmentUpdate,
    service: ShipmentServiceDep,
    partner: DeliveryPartnerDep,
) -> Shipment:
    return await service.update(id, shipment_update, partner)


@router.get("/tagged", response_model=list[ShipmentRead])
async def get_shipments_with_tags(
    tag_name: TagName,
    session: SessionDep,
):
    tag = await tag_name.tag(session)
    if tag is None:
        raise EntityNotFound()
    return tag.shipments


@router.get("/tag", response_model=ShipmentRead)
async def add_tag_to_shipment(
    id: UUID,
    tag_name: TagName,
    service: ShipmentServiceDep,
):
    return await service.add_tag(id, tag_name)


@router.delete("/tag", response_model=ShipmentRead)
async def remove_tag_from_shipment(
    id: UUID,
    tag_name: TagName,
    service: ShipmentServiceDep,
):
    return await service.remove_tag(id, tag_name)


@router.get("/cancel", response_model=ShipmentRead)
async def cancel_shipment(
    id: UUID,
    service: ShipmentServiceDep,
    seller: SellerDep,
):
    return await service.cancel(id, seller)


@router.get("/review")
async def submit_review_page(
    request: Request,
    token: str,
):
    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={
            "review_url": f"http://{app_settings.APP_DOMAIN}{router.prefix}/review?token={token}"
        },
    )


@router.post("/review")
async def submit_review(
    token: str,
    service: ShipmentServiceDep,
    rating: Annotated[int, Form(ge=1, le=5)],
    comment: Annotated[str | None, Form()] = None,
):
    await service.rate(token, rating, comment)
    return {"detail": "Review Submitted"}
