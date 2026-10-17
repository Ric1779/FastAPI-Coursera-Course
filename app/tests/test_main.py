from httpx import AsyncClient

from app.tests.example import SELLER
from app.utils import print_label


async def test_app(client: AsyncClient):
    response = await client.get("/")
    print_label(response.json())
    assert response.status_code == 200
    assert response.json() == {"detail": "ac5024e9-fb46-45a4-b1d5-51931657796a"}


async def test_seller_login(client: AsyncClient):
    response = await client.post(
        "/seller/token",
        data={
            "grant_type": "password",
            "username": SELLER["email"],
            "password": SELLER["password"],
        },
    )

    print_label(response.json())
