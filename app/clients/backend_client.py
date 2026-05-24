import logging
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings

logger = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
)
async def get_routing_context(org_id: Optional[str] = None) -> dict:
    """
    Llama al endpoint privado de NestJS /api/internal/routing-context
    y retorna el JSON con niveles, técnicos activos y contexto de la org.
    """
    settings = get_settings()
    url = f"{settings.backend_url}/api/internal/routing-context"
    headers = {"X-Internal-Secret": settings.internal_api_secret}
    params = {"org_id": org_id} if org_id else {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()

    data = response.json()
    org_context = data.get("org_context", {})
    logger.info(
        "Routing context fetched: %d levels, %d active techs, org_type=%s",
        len(data.get("niveles", [])),
        len(data.get("tecnicos", [])),
        org_context.get("company_type", "none"),
    )
    return data
