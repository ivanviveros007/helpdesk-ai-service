import json
import logging
from langchain_core.tools import tool
from app.clients.backend_client import get_routing_context

logger = logging.getLogger(__name__)


@tool
async def get_routing_context_tool() -> str:
    """
    Obtiene la configuración actual del sistema de soporte en tiempo real desde el backend.

    Retorna un JSON con:
    - niveles: lista de niveles de soporte con sus responsabilidades, tags y complejidad máxima.
    - tecnicos: lista de técnicos activos con sus skills y carga de trabajo actual.

    SIEMPRE debes llamar esta herramienta antes de asignar un ticket.
    """
    try:
        data = await get_routing_context()
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to fetch routing context: %s", e)
        return json.dumps({"error": str(e), "niveles": [], "tecnicos": []})
