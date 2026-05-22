from pydantic import BaseModel, Field


class TicketInput(BaseModel):
    ticket_id: str = Field(..., description="UUID del ticket generado por NestJS")
    asunto: str = Field(..., min_length=5, max_length=200)
    descripcion: str = Field(..., min_length=10, max_length=5000)
