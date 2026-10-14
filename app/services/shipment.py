from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.shipment import ShipmentCreate, ShipmentUpdate
from app.core.exceptions import (
    ClientNotAuthorized,
    DeliveryPartnerCapacityExceeded,
    EntityNotFound,
    InvalidToken,
    NothingToUpdate,
)
from app.database.models import (
    DeliveryPartner,
    Review,
    Seller,
    Shipment,
    ShipmentStatus,
    TagName,
)
from app.database.redis import get_shipment_verification_code
from app.services.base import BaseService
from app.services.delivery_partner import DeliveryPartnerService
from app.services.shipment_event import ShipmentEventService
from app.utils import decode_url_safe_token


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

    async def get(self, id: UUID) -> Shipment:
        shipment = await self._get(id)
        if shipment is None:
            raise EntityNotFound()
        return shipment

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
            raise DeliveryPartnerCapacityExceeded()

        shipment = await self._add(new_shipment)

        if seller.zip_code is None:
            raise NothingToUpdate()

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
        update = shipment_update.model_dump(
            exclude_none=True, exclude={"verification_code"}
        )

        if not update:
            raise NothingToUpdate()

        # Get the relevant shipment and validate it against the current delivery partner
        shipment = await self.get(id)

        # validate the delivery partner
        if shipment.delivery_partner_id != partner.id:
            raise ClientNotAuthorized()

        # send OTP
        if shipment_update.status == ShipmentStatus.delivered:
            code = await get_shipment_verification_code(shipment.id)

            if code != shipment_update.verification_code:
                raise ClientNotAuthorized()

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
            raise EntityNotFound()

        if shipment.seller_id != seller.id:
            raise ClientNotAuthorized()

        event = await self.event_service.add(
            shipment=shipment,
            status=ShipmentStatus.cancelled,
        )

        shipment.timeline.append(event)

        return shipment

    async def delete(self, id: UUID, seller: Seller) -> None:
        shipment = await self.get(id)
        if not shipment:
            raise EntityNotFound()

        # validate the seller
        if shipment.seller_id != seller.id:
            raise ClientNotAuthorized()

        if shipment is not None:
            await self._delete(shipment)

    async def add_tag(self, id: UUID, tag_name: TagName):
        shipment = await self.get(id)

        if not shipment:
            raise EntityNotFound()

        tag = await tag_name.tag(self.session)
        if tag is None:
            raise EntityNotFound()

        shipment.tags.append(tag)

        return await self._update(shipment)

    async def remove_tag(self, id: UUID, tag_name: TagName):
        shipment = await self.get(id)

        if not shipment:
            raise EntityNotFound()

        tag = await tag_name.tag(self.session)
        if tag is None:
            raise EntityNotFound()
        try:
            shipment.tags.remove(tag)
        except ValueError:
            raise EntityNotFound()

        return await self._update(shipment)

    async def rate(self, token: str, rating: int, comment: str | None):
        token_data = decode_url_safe_token(token)

        if token_data is None:
            raise InvalidToken()

        shipment = await self.get(UUID(token_data["id"]))

        if shipment is None:
            raise EntityNotFound()
        new_review = Review(
            rating=rating,
            comment=comment if comment else None,
            shipment_id=shipment.id,
        )

        self.session.add(new_review)
        await self.session.commit()
