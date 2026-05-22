import logging
from typing import Any
from app.rag.vector_store import get_collection
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def retrieve_similar_tickets(
    embedding: list[float],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    Consulta ChromaDB con el embedding del ticket nuevo y retorna
    los tickets históricos más similares que superen el umbral de similitud.

    Returns una lista de dicts con:
        - ticket_id: str
        - similarity_score: float   (1 - distancia coseno)
        - resolution_summary: str   (del metadata)
        - document: str             (texto original)
    """
    settings = get_settings()
    k = top_k or settings.rag_top_k
    collection = get_collection()

    if collection.count() == 0:
        logger.info("ChromaDB collection is empty — skipping RAG retrieval")
        return []

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    similar: list[dict[str, Any]] = []

    ids = results.get("ids", [[]])[0]
    distances = results.get("distances", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    documents = results.get("documents", [[]])[0]

    for tid, dist, meta, doc in zip(ids, distances, metadatas, documents):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity: 1 - (distance / 2)
        similarity = 1.0 - (dist / 2.0)

        if similarity < settings.rag_similarity_threshold:
            continue

        similar.append({
            "ticket_id": tid,
            "similarity_score": round(similarity, 4),
            "resolution_summary": meta.get("resolution_summary", "Sin resolución documentada."),
            "category": meta.get("category", ""),
            "priority": meta.get("priority", 0),
            "document": doc,
        })

    logger.info("RAG retrieved %d similar tickets (threshold=%.2f)", len(similar), settings.rag_similarity_threshold)
    return similar


def format_rag_context(similar_tickets: list[dict[str, Any]]) -> str:
    """Formatea los tickets similares como texto para inyectar en el prompt."""
    if not similar_tickets:
        return "No se encontraron tickets históricos similares relevantes."

    lines = ["## Tickets históricos similares encontrados:\n"]
    for i, t in enumerate(similar_tickets, 1):
        lines.append(
            f"### Ticket histórico {i} (similitud: {t['similarity_score']:.0%})\n"
            f"- **Descripción**: {t['document'][:300]}...\n"
            f"- **Categoría**: {t.get('category', 'N/A')}\n"
            f"- **Prioridad previa**: {t.get('priority', 'N/A')}\n"
            f"- **Resolución documentada**: {t['resolution_summary']}\n"
        )
    return "\n".join(lines)
