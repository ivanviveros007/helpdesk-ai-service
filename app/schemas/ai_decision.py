from pydantic import BaseModel, Field
from typing import Optional


class SimilarTicket(BaseModel):
    ticket_id: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    resolution_summary: str


class AiDecision(BaseModel):
    ticket_id: str
    category: str = Field(..., description="Categoría del ticket: mobile_crash, network, access, etc.")
    priority: int = Field(..., ge=1, le=10, description="Prioridad de 1 (baja) a 10 (crítica)")
    complexity_score: int = Field(..., ge=1, le=10, description="Complejidad técnica del problema")
    suggested_level: int = Field(..., ge=1, description="Número de nivel de soporte sugerido")
    assigned_tecnico_id: Optional[str] = Field(None, description="UUID del técnico asignado, null si no hay disponible")
    reasoning: str = Field(..., description="Explicación detallada de la decisión en español")
    similar_tickets: list[SimilarTicket] = Field(default_factory=list)
