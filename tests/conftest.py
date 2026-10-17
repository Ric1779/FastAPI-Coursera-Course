from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.database.session import get_session
from app.main import app, get_id

engine = create_async_engine(url="sqlite+aiosqlite:///:memory:")

test_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session_override():
    async with test_session() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://test",
    ) as client:
        yield client


def get_id_override():
    return UUID("ac5024e9-fb46-45a4-b1d5-51931657796a")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_and_teardown():

    print("🧪 starting tests...")
    app.dependency_overrides[get_id] = get_id_override
    app.dependency_overrides[get_session] = get_session_override

    async with engine.begin() as connection:
        from app.database.models import (
            DeliveryPartner,
            Seller,
            Shipment,
            ShipmentEvent,
        )

        await connection.run_sync(SQLModel.metadata.create_all)

    yield

    async with engine.begin() as connection:
        from app.database.models import (  # noqa: F401
            DeliveryPartner,
            Seller,
            Shipment,
            ShipmentEvent,
        )

        await connection.run_sync(SQLModel.metadata.drop_all)

    app.dependency_overrides.clear()
    print("...finished!")
