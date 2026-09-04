from contextlib import asynccontextmanager

from fastapi import FastAPI
from rich import panel, print


@asynccontextmanager
async def lifespan_handler(app: FastAPI):
    print(panel.Panel("Server started...", border_style="green"))
    yield
    print(panel.Panel("...Server stopped!", border_style="red"))


app = FastAPI(lifespan=lifespan_handler)


@app.get("/")
def read_root():
    return {"detail": "server running..."}
