from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlalchemy import ARRAY, INTEGER
from sqlalchemy.dialects import postgresql
from sqlmodel import Column, Field, Relationship, SQLModel


class ShipmentStatus(str, Enum):
    placed = "placed"
    in_transit = "in_transit"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"


# A SQLModel is a pydantic model as well, so it comes with all the data validation and other checks
class Shipment(SQLModel, table=True):
    __tablename__ = "shipment"  # type: ignore

    id: UUID = Field(
        sa_column=Column(
            postgresql.UUID,
            default=uuid4,
            primary_key=True,
        )
    )
    content: str
    weight: float = Field(le=25)
    destination: int
    status: ShipmentStatus
    estimated_delivery: datetime

    seller_id: UUID = Field(foreign_key="seller.id")
    seller: "Seller" = Relationship(
        back_populates="shipments",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    delivery_partner_id: UUID = Field(foreign_key="delivery_partner.id")
    delivery_partner: "DeliveryPartner" = Relationship(
        back_populates="shipments",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


# a non-table base (mixin)
# Do not use sa_column=Column(...) here: Column objects can't be shared across
# Seller and DeliveryPartner tables ("Column object 'id' already assigned...").
class User(SQLModel):
    name: str
    email: EmailStr
    password_hash: str = Field(exclude=True)

    # In the course the person had used sa_column inside Field, he said that's required
    # because UUID/datetime is not a native type supported by postgres. But cursor suggested
    # the below implementation with default_factory and sharing these attributes by having them
    # in User, rather than having it in Seller and DeliveryPartner separately.

    # The below two attributes were present in both Seller and DeliveryPartner separately.

    # id: UUID = Field(
    #     sa_column=Column(
    #         postgresql.UUID,
    #         default=uuid4,
    #         primary_key=True,
    #     )
    # )
    # created_at: datetime = Field(
    #     sa_column=Column(
    #         postgresql.TIMESTAMP,
    #         default=datetime.now,
    #     )
    # )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)


class Seller(User, table=True):
    __tablename__ = "seller"  # type: ignore

    shipments: list[Shipment] = Relationship(
        back_populates="seller",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class DeliveryPartner(User, table=True):
    __tablename__ = "delivery_partner"  # type: ignore

    serviceable_zip_codes: list[int] = Field(
        sa_column=Column(ARRAY(INTEGER)),
    )

    max_handling_capacity: int

    shipments: list[Shipment] = Relationship(
        back_populates="delivery_partner",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    @property
    def active_shipments(self):
        return [
            shipment
            for shipment in self.shipments
            if shipment.status != ShipmentStatus.delivered
        ]

    @property
    def current_handling_capacity(self):
        return self.max_handling_capacity - len(self.active_shipments)
