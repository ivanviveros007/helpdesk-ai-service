import logging
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_embeddings_model: GoogleGenerativeAIEmbeddings | None = None


def get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    global _embeddings_model
    if _embeddings_model is None:
        settings = get_settings()
        _embeddings_model = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
        )
        logger.info("Embeddings model initialized: %s", settings.gemini_embedding_model)
    return _embeddings_model


def embed_text(text: str) -> list[float]:
    """Genera un embedding para un texto usando Gemini text-embedding-004."""
    model = get_embeddings_model()
    embedding = model.embed_query(text)
    logger.debug("Embedding generated: %d dimensions", len(embedding))
    return embedding
