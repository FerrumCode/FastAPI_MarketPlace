from uuid import UUID
import httpx

from .config import settings


async def fetch_product(product_id: UUID) -> dict:
    """Берёт товар из Catalog Service. Ожидается JSON с полями как минимум id и price."""
    async with httpx.AsyncClient(base_url=settings.CATALOG_SERVICE_URL, timeout=5) as client:
        r = await client.get(f"/products/{product_id}")
        r.raise_for_status()
        return r.json()
