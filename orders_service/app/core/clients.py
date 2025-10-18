from uuid import UUID
import httpx

from .config import settings


async def fetch_product(product_id: UUID) -> dict:
    """Получаем товар из Catalog Service."""
    async with httpx.AsyncClient(base_url=settings.CATALOG_SERVICE_URL, timeout=5) as client:
        r = await client.get(f"/products/{product_id}")
        r.raise_for_status()
        return r.json()
