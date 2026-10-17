from httpx import AsyncClient

from app.tests import example
from app.utils import print_label

base_url = "/shipment/"


async def test_submit_shipment_auth(client: AsyncClient):
    response = await client.post(
        base_url,
        json={},
    )

    assert response.status_code == 401

    print_label(response.json())


async def test_submit_shipment(client: AsyncClient, seller_token: str):
    response = await client.post(
        base_url,
        json=example.SHIPMENT,
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert response.status_code == 201

    response = await client.get(
        base_url,
        params={"id": response.json()["id"]},
        headers={"Authorization": f"Bearer {seller_token}"},
    )

    assert response.status_code == 200
    print_label(response.json())
