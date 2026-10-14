from contextlib import asynccontextmanager
from datetime import datetime
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from app.api.router import master_router
from app.api.tag import APITag
from app.core.exceptions import add_exception_handlers
from app.database.session import create_db_tables
from app.worker.tasks import add_log, background_task


@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    await create_db_tables()
    yield


description = """
Delivery Management system for seller and delivery agents

### Seller
- Submit shipment effortlessly
- Share tracking links with the customers

### Delivery Agent
- Auto accept shipment
- Track and update shipment status
- Email and sms notification
"""

app = FastAPI(
    title="FastShip",
    description=description,
    docs_url=None,
    redoc_url=None,
    version="0.1.0",
    openapi_tags=[
        {
            "name": APITag.SHIPMENT,
            "description": "Operations related to shipments.",
        },
        {
            "name": APITag.SELLER,
            "description": "Operations related to users.",
        },
        {
            "name": APITag.PARTNER,
            "description": "Operations related to delivery partner.",
        },
    ],
    lifespan=lifespan_handler,
)

add_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)


@app.middleware("http")
async def custom_middleware(request: Request, call_next) -> Response:
    start = perf_counter()
    response: Response = await call_next(request)
    end = perf_counter()
    time_taken = round(end - start, 2)

    add_log.delay(  # type: ignore[attr-defined]
        f"{request.method} {request.url} ({response.status_code}) {time_taken} s"
    )

    return response


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
@app.get("/docs", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Scalar API",
    )
