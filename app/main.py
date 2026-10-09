from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

from app.api.router import master_router
from app.database.session import create_db_tables
from app.worker.tasks import background_task


@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    await create_db_tables()
    yield


app = FastAPI(lifespan=lifespan_handler)

app.include_router(master_router)


@app.get("/test")
def test():
    now = datetime.now()  # noqa: DTZ005
    background_task.delay(  # type: ignore[attr-defined]
        f"Background Taks {now.second}",
        data={
            "min": now.minute,
            "sec": now.second,
        },
    )


# Scalar Endpoint
@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Scalar API",
    )
