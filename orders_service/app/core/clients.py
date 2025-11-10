from uuid import UUID
import httpx
from fastapi import HTTPException
from env import CATALOG_SERVICE_URL


async def fetch_product(product_id: UUID, auth_header: str | None = None) -> dict:
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    async with httpx.AsyncClient(
        base_url=CATALOG_SERVICE_URL,
        timeout=5.0,
    ) as client:
        try:
            resp = await client.get(f"/products/{product_id}", headers=headers)
        except httpx.RequestError as e:
            raise RuntimeError(f"connection error to Catalog Service: {e}") from e

    if resp.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} not found in Catalog Service",
        )

    if resp.status_code >= 400:
        raise RuntimeError(
            f"Catalog Service error {resp.status_code}: {resp.text}"
        )

    try:
        data = resp.json()
    except ValueError as e:
        raise RuntimeError(
            f"Catalog Service returned invalid JSON for product {product_id}"
        ) from e

    return data
