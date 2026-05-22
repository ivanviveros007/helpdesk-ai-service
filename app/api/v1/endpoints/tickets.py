import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.ticket_input import TicketInput
from app.schemas.ai_decision import AiDecision
from app.pipeline.cleaner import clean_ticket
from app.pipeline.embedder import embed_text
from app.rag.retriever import retrieve_similar_tickets, format_rag_context
from app.rag.vector_store import add_ticket_to_store
from app.agent.agent import run_agent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/analyze-ticket",
    response_model=AiDecision,
    status_code=status.HTTP_200_OK,
    summary="Analiza un ticket con IA y retorna la decisión de asignación",
)
async def analyze_ticket(payload: TicketInput) -> AiDecision:
    """
    Pipeline completo:
    1. Limpieza del texto con Pandas
    2. Generación de embedding con Gemini
    3. RAG: búsqueda de tickets históricos similares en ChromaDB
    4. Agente LangChain ReAct: consulta routing context + razona + decide
    5. Retorna JSON de decisión validado con Pydantic
    """
    logger.info("Received ticket %s for analysis", payload.ticket_id)

    # 1. Clean
    cleaned = clean_ticket(payload.asunto, payload.descripcion)
    asunto = cleaned["asunto"]
    descripcion = cleaned["descripcion"]
    full_text = f"{asunto}\n\n{descripcion}"

    # 2. Embed
    try:
        embedding = embed_text(full_text)
    except Exception as e:
        logger.error("Embedding failed for ticket %s: %s", payload.ticket_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding service error: {e}",
        )

    # 3. RAG retrieval
    similar_tickets = retrieve_similar_tickets(embedding)
    rag_context = format_rag_context(similar_tickets)

    # 4. Run agent
    try:
        decision = await run_agent(
            ticket_id=payload.ticket_id,
            asunto=asunto,
            descripcion=descripcion,
            rag_context=rag_context,
            similar_tickets=similar_tickets,
        )
    except Exception as e:
        logger.error("Agent failed for ticket %s: %s", payload.ticket_id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI agent error: {e}",
        )

    # 5. Store ticket in ChromaDB for future RAG
    try:
        add_ticket_to_store(
            ticket_id=payload.ticket_id,
            text=full_text,
            metadata={
                "asunto": asunto,
                "category": decision.category,
                "priority": decision.priority,
                "suggested_level": decision.suggested_level,
                "resolution_summary": "Pendiente de resolución.",
            },
            embedding=embedding,
        )
    except Exception as e:
        # Non-fatal: log and continue
        logger.warning("Failed to store ticket in ChromaDB: %s", e)

    return decision
