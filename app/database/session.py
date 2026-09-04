from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

# Can think of engine as a connection with more features
engine = create_engine(
    url="sqlite:///sqlite.db",
    echo=True,
    connect_args={"check_same_thread": False},
)


def create_db_tables():
    from .models import Shipment  # noqa: F401

    SQLModel.metadata.create_all(bind=engine)


# in the following code, yield is used along with 'with' (Session is already context managed) since the
# content inside 'with' block is accessed from somewhere else
# yield can also be used to convert a function to understand context using @contextmanager decorator
def get_session():
    with Session(bind=engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
