from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.dependencies.depend import permission_required


# CHANGED: prefix="/" убран, чтобы не получить //metrics
# CHANGED: include_in_schema=False чтобы не светить /metrics в Swagger
router = APIRouter(tags=["Metrics"], include_in_schema=True)


@router.get("/metrics", dependencies=[Depends(permission_required("can_patch_order_status"))])
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
