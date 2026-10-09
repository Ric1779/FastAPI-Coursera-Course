from random import randint

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import app_settings
from app.database.models import Shipment, ShipmentEvent, ShipmentStatus
from app.database.redis import add_shipment_verification_code
from app.services.base import BaseService
from app.utils import generate_url_safe_token
from app.worker.tasks import send_email_with_template, send_sms


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

        await self._notify(shipment, status)

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

    async def _notify(self, shipment: Shipment, status: ShipmentStatus | None):

        subject: str
        context: dict = {}
        template_name: str

        match status:
            case ShipmentStatus.placed:
                subject = "Your order is Shipped."
                context["id"] = str(shipment.id)
                context["seller"] = shipment.seller.name
                context["partner"] = shipment.delivery_partner.name
                template_name = "mail_placed.html"

            case ShipmentStatus.out_for_delivery:
                subject = "Your order is Arriving."
                template_name = "mail_out_for_delivery.html"

                code = randint(100_000, 999_999)

                await add_shipment_verification_code(shipment.id, code)
                # Trial SMS cannot include a custom body, so the code goes in the email.
                context["verification_code"] = code

                if shipment.client_contact_phone:
                    send_sms.delay(  # type: ignore[attr-defined]
                        to=shipment.client_contact_phone,
                        body="sms_delivery_updates",
                    )

            case ShipmentStatus.delivered:
                subject = "Your order is Delivered."
                context["seller"] = shipment.seller.name
                token = generate_url_safe_token({"id": str(shipment.id)})
                context["review_url"] = (
                    f"http://{app_settings.APP_DOMAIN}/shipment/review?token={token}"
                )
                template_name = "mail_delivered.html"

            case ShipmentStatus.cancelled:
                subject = "Your order is Cancelled."
                template_name = "mail_cancelled.html"

            case _:
                return

        send_email_with_template.delay(  # type: ignore[attr-defined]
            recipients=[shipment.client_contact_email],
            subject=subject,
            context=context,
            template_name=template_name,
        )
