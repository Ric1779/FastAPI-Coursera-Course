from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.config import settings

# Can think of engine as a connection with more features
engine = create_async_engine(url=settings.POSTGRES_URL, echo=True)


async def create_db_tables():
    async with engine.begin() as connection:
        from .models import Shipment  # noqa: F401

        await connection.run_sync(SQLModel.metadata.create_all)


# in the following code, yield is used along with 'with' (Session is already context managed) since the
# content inside 'with' block is accessed from somewhere else
# yield can also be used to convert a function to understand context using @contextmanager decorator
async def get_session():
    async_session = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
