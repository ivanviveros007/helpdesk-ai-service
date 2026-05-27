import json
import logging
import re
from typing import Optional
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from app.core.config import get_settings
from app.agent.tools import get_routing_context_tool, current_org_id
from app.agent.prompts import SYSTEM_PROMPT, build_user_prompt
from app.schemas.ai_decision import AiDecision

logger = logging.getLogger(__name__)

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        settings = get_settings()
        llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.1,
        )
        _agent = create_react_agent(
            model=llm,
            tools=[get_routing_context_tool],
            prompt=SYSTEM_PROMPT,
        )
        logger.info("LangGraph ReAct agent initialized with model: %s", settings.groq_model)
    return _agent


def _extract_json(text: str) -> str:
    """Extrae el primer bloque JSON válido de un texto."""
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)

    raise ValueError(f"No valid JSON found in LLM output: {text[:200]}")


async def run_agent(
    ticket_id: str,
    asunto: str,
    descripcion: str,
    rag_context: str,
    similar_tickets: list[dict],
    org_id: Optional[str] = None,
) -> AiDecision:
    """
    Ejecuta el agente ReAct con el ticket y el contexto RAG.
    El org_id se inyecta en un ContextVar para que la herramienta de routing
    filtre técnicos y niveles por organización y devuelva el org_context.
    """
    # Set org_id so the routing tool fetches filtered + org-aware context
    token = current_org_id.set(org_id)

    try:
        agent = get_agent()
        user_message = build_user_prompt(ticket_id, asunto, descripcion, rag_context)

        logger.info("Running agent for ticket %s (org: %s)", ticket_id, org_id or "none")

        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_message}]}
        )
    finally:
        current_org_id.reset(token)

    messages = result.get("messages", [])
    last_ai_message = next(
        (m for m in reversed(messages) if hasattr(m, "content") and m.type == "ai"),
        None,
    )

    if not last_ai_message:
        raise ValueError("Agent returned no AI message")

    raw_content = last_ai_message.content
    logger.debug("Raw agent output: %s", raw_content[:500])

    json_str = _extract_json(raw_content)
    decision_data = json.loads(json_str)

    if not decision_data.get("similar_tickets") and similar_tickets:
        decision_data["similar_tickets"] = [
            {
                "ticket_id": t["ticket_id"],
                "similarity_score": t["similarity_score"],
                "resolution_summary": t["resolution_summary"],
            }
            for t in similar_tickets
        ]

    decision = AiDecision.model_validate(decision_data)
    logger.info(
        "Agent decision for ticket %s: priority=%d, level=%d, tech=%s",
        ticket_id,
        decision.priority,
        decision.suggested_level,
        decision.assigned_tecnico_id,
    )
    return decision
