import json
import logging
from contextvars import ContextVar
from langchain_core.tools import tool
from app.clients.backend_client import get_routing_context

logger = logging.getLogger(__name__)

# Thread-safe org_id context — set before invoking the agent, read by the tool
current_org_id: ContextVar[str | None] = ContextVar("current_org_id", default=None)


@tool
async def get_routing_context_tool() -> str:
    """
    Obtiene la configuración actual del sistema de soporte en tiempo real desde el backend.

    Retorna un JSON con:
    - org_context: tipo de empresa e instrucciones específicas del cliente (si aplica).
    - niveles: lista de niveles de soporte con sus responsabilidades, tags y complejidad máxima.
    - tecnicos: lista de técnicos activos con sus skills y carga de trabajo actual.

    SIEMPRE debes llamar esta herramienta antes de asignar un ticket.
    Si org_context contiene company_type o ai_custom_instructions, úsalos para ajustar
    tu evaluación de prioridad, categoría y selección de técnico.
    """
    try:
        org_id = current_org_id.get()
        data = await get_routing_context(org_id=org_id)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to fetch routing context: %s", e)
        return json.dumps({"error": str(e), "org_context": {}, "niveles": [], "tecnicos": []})
