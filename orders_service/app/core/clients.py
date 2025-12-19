from uuid import UUID

import httpx
from fastapi import HTTPException
from loguru import logger

from env import CATALOG_SERVICE_URL, SERVICE_NAME
from app.core.metrics import CATALOG_FETCH_PRODUCT_TOTAL



async def fetch_product(product_id: UUID, auth_header: str | None = None) -> dict:
    CATALOG_FETCH_PRODUCT_TOTAL.labels(service=SERVICE_NAME, status="attempt").inc()
    logger.info(
        "Fetching product '{product_id}' from Catalog Service",
        product_id=str(product_id),
    )

    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header
        logger.debug(
            "Using Authorization header while fetching product '{product_id}'",
            product_id=str(product_id),
        )

    async with httpx.AsyncClient(
        base_url=CATALOG_SERVICE_URL,
        timeout=5.0,
    ) as client:
        try:
            resp = await client.get(f"/products/{product_id}", headers=headers)
            logger.info(
                "Received response from Catalog Service for product '{product_id}' with status_code={status_code}",
                product_id=str(product_id),
                status_code=resp.status_code,
            )
        except httpx.RequestError as e:
            logger.error(
                "Connection error while fetching product '{product_id}' from Catalog Service: {error}",
                product_id=str(product_id),
                error=str(e),
            )
            CATALOG_FETCH_PRODUCT_TOTAL.labels(
                service=SERVICE_NAME,
                status="connection_error",
            ).inc()
            raise RuntimeError(f"connection error to Catalog Service: {e}") from e

    if resp.status_code == 404:
        logger.warning(
            "Product '{product_id}' not found in Catalog Service",
            product_id=str(product_id),
        )
        CATALOG_FETCH_PRODUCT_TOTAL.labels(
            service=SERVICE_NAME,
            status="not_found",
        ).inc()
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} not found in Catalog Service",
        )

    if resp.status_code >= 400:
        logger.error(
            "Error response from Catalog Service for product '{product_id}': status_code={status_code}, body='{body}'",
            product_id=str(product_id),
            status_code=resp.status_code,
            body=resp.text,
        )
        CATALOG_FETCH_PRODUCT_TOTAL.labels(
            service=SERVICE_NAME,
            status="error",
        ).inc()
        raise RuntimeError(
            f"Catalog Service error {resp.status_code}: {resp.text}"
        )

    try:
        data = resp.json()
        logger.info(
            "Successfully decoded JSON from Catalog Service for product '{product_id}'",
            product_id=str(product_id),
        )
    except ValueError as e:
        logger.error(
            "Invalid JSON from Catalog Service for product '{product_id}': {error}",
            product_id=str(product_id),
            error=str(e),
        )
        CATALOG_FETCH_PRODUCT_TOTAL.labels(
            service=SERVICE_NAME,
            status="invalid_json",
        ).inc()
        raise RuntimeError(
            f"Catalog Service returned invalid JSON for product {product_id}"
        ) from e

    CATALOG_FETCH_PRODUCT_TOTAL.labels(
        service=SERVICE_NAME,
        status="success",
    ).inc()
    return data
