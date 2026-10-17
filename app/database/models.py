from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import EmailStr
from sqlalchemy import MetaData
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Column, Field, Relationship, SQLModel, select

# Must be set before table models are defined so Alembic autogenerate
# gets stable constraint names (avoids create_foreign_key(None, ...)).
SQLModel.metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class ShipmentStatus(str, Enum):
    placed = "placed"
    in_transit = "in_transit"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


class TagName(str, Enum):
    EXPRESS = "express"
    STANDARD = "standard"
    FRAGILE = "fragile"
    HEAVY = "heavy"
    INTERNATIONAL = "international"
    DOMESTIC = "domestic"
    TEMPERATURE_CONTROLLED = "temperature_controlled"
    GIFT = "gift"
    RETURN = "return"
    DOCUMENTS = "documents"

    async def tag(self, session: AsyncSession):
        return await session.scalar(select(Tag).where(Tag.name == self.value))


class ShipmentTag(SQLModel, table=True):
    __tablename__ = "shipment_tag"  # type: ignore

    shipment_id: UUID = Field(
        foreign_key="shipment.id",
        primary_key=True,
    )
    tag_id: UUID = Field(
        foreign_key="tag.id",
        primary_key=True,
    )


class Tag(SQLModel, table=True):
    __tablename__ = "tag"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    name: TagName
    instruction: str

    shipments: list["Shipment"] = Relationship(
        back_populates="tags",
        link_model=ShipmentTag,
        sa_relationship_kwargs={"lazy": "immediate"},
    )


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
    created_at: datetime = Field(default_factory=datetime.now)
    client_contact_email: EmailStr
    client_contact_phone: str | None

    content: str
    weight: float = Field(le=25)
    destination: int
    estimated_delivery: datetime

    timeline: list["ShipmentEvent"] = Relationship(
        back_populates="shipment",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

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

    review: "Review" = Relationship(
        back_populates="shipment",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    tags: list[Tag] = Relationship(
        back_populates="shipments",
        link_model=ShipmentTag,
        sa_relationship_kwargs={"lazy": "immediate"},
    )

    @property
    def status(self) -> ShipmentStatus | None:
        """Current status = latest timeline event (status no longer on shipment row)."""
        if not self.timeline:
            return None
        return max(self.timeline, key=lambda event: event.created_at).status


# UUID primary key (PK) patterns:
# A) Field(default_factory=uuid4, primary_key=True) — Pydantic sets id on construct; safe for mixins.
# B) Field(sa_column=Column(postgresql.UUID, default=uuid4, primary_key=True)) — SQLAlchemy sets id on flush;
# don't reuse Column on multiple tables.


class ShipmentEvent(SQLModel, table=True):
    __tablename__ = "shipment_event"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    location: int | None = Field(default=None)
    status: ShipmentStatus | None = Field(default=None)
    description: str | None = Field(default=None)

    # previous implementation: shipment_id: UUID = Field(foreign_key="shipment.id")
    # ShipmentEvent requires shipment_id, but it's filled by the relationship on flush.
    # So, type checker throws an error -> {Argument missing for parameter "shipment_id"}
    # ShipmentEvent required shipment_id, but on create the FK isn’t known yet — SQLAlchemy
    # fills it when you append to timeline and flush.

    # Fix: shipment_id is now optional (default=None) so you can build the event first;
    # the relationship sets the FK on save. On update, we pass shipment_id=shipment.id
    # explicitly since the shipment already exists.
    shipment_id: UUID | None = Field(default=None, foreign_key="shipment.id")
    shipment: Shipment | None = Relationship(
        back_populates="timeline",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


# a non-table base (mixin)
# Do not use sa_column=Column(...) here: Column objects can't be shared across
# Seller and DeliveryPartner tables ("Column object 'id' already assigned...").
class User(SQLModel):
    name: str
    email: EmailStr
    email_verified: bool = Field(default=False)
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

    address: str | None = Field(default=None)
    zip_code: int | None = Field(default=None)

    shipments: list[Shipment] = Relationship(
        back_populates="seller",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class ServiceableLocation(SQLModel, table=True):
    __tablename__ = "serviceable_location"  # type: ignore

    partner_id: UUID = Field(
        foreign_key="delivery_partner.id",
        primary_key=True,
    )

    location_id: UUID = Field(
        foreign_key="location.zip_code",
        primary_key=True,
    )


class DeliveryPartner(User, table=True):
    __tablename__ = "delivery_partner"  # type: ignore

    serviceable_locations: list["Location"] = Relationship(
        back_populates="delivery_partners",
        link_model=ServiceableLocation,
        sa_relationship_kwargs={"lazy": "selectin"},
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
            or shipment.status != ShipmentStatus.cancelled
        ]

    @property
    def current_handling_capacity(self):
        return self.max_handling_capacity - len(self.active_shipments)


class Location(SQLModel, table=True):
    __tablename__ = "location"  # type: ignore

    zip_code: int = Field(primary_key=True)

    delivery_partners: list[DeliveryPartner] = Relationship(
        back_populates="serviceable_location",
        link_model=ServiceableLocation,
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Review(SQLModel, table=True):
    __tablename__ = "review"  # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None)

    shipment_id: UUID = Field(foreign_key="shipment.id")
    shipment: Shipment = Relationship(
        back_populates="review",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
