from httpx import AsyncClient

from app.utils import print_label


async def test_app(client: AsyncClient):
    response = await client.get("/")
    print_label(response.json())
    assert response.status_code == 200
    assert response.json() == {"detail": "ac5024e9-fb46-45a4-b1d5-51931657796a"}
